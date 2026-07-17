#!/usr/bin/env python3
"""
Answer-drift checker for TogoMCP benchmark questions.

`verify_questions.py` validates STRUCTURE — it never re-runs the queries, so it
cannot notice when a stored query's live result has drifted away from its
recorded `result_count`. That drift is exactly how the 2026-07 co-tenancy audit
found six stale queries (Q060/Q071/Q073/Q086/Q089/Q100): each was authored
against a correct result and the endpoint moved underneath it — silently.

This script closes that gap. For every `sparql_queries[*]` entry across the
question set it re-executes the query against the database's SPARQL endpoint
(resolved from endpoints.csv, the same registry the server uses) and compares the
live row count to the recorded `result_count`.

It is deliberately a REPORT, not a gate that fails the build:
  - Live endpoints drift for legitimate reasons (a database grew by one entry).
    A DRIFT is a prompt to re-examine the question, not proof it is wrong.
  - Network timeouts / 5xx are NOT drift — they are reported separately and never
    counted as a mismatch.
  - Queries that are not runnable SPARQL (steps recorded as OLS4/PubMed/NCBI notes
    in a comment block) are SKIPPED, not failed.

Exit code = number of DRIFT rows (0 = all recorded counts still reproduce), so it
is usable in a scheduled job; pass --strict to also fail on ERROR rows. Network
errors alone never change the exit code unless --strict is given.

Usage:
    uv run python benchmark/scripts/check_answer_drift.py            # whole set
    uv run python benchmark/scripts/check_answer_drift.py 60 71 100  # specific Qs
    uv run python benchmark/scripts/check_answer_drift.py --timeout 120 --strict
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: uv sync (or pip install pyyaml)")
    sys.exit(2)

# Resolve relative to this script so it works regardless of checkout location.
BASE_PATH = Path(__file__).resolve().parents[1] / "questions"
ENDPOINTS_CSV = (Path(__file__).resolve().parents[2]
                 / "togo_mcp" / "data" / "resources" / "endpoints.csv")

# Endpoint groups out of scope for this life-science benchmark (see
# verify_questions.py). Databases on these endpoints are not checked.
_EXCLUDED_ENDPOINTS = {"nims"}


def load_endpoint_map():
    """database -> endpoint_url, from endpoints.csv, minus excluded groups."""
    m = {}
    with open(ENDPOINTS_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            db = (row.get("database") or "").strip()
            url = (row.get("endpoint_url") or "").strip()
            grp = (row.get("endpoint_name") or "").strip()
            if db and url and grp not in _EXCLUDED_ENDPOINTS:
                m[db] = url
    return m


# A query is runnable SPARQL only if, after stripping comment lines, it contains
# a SELECT / ASK / CONSTRUCT / DESCRIBE form. Question steps performed via OLS4,
# PubMed, or NCBI tools are recorded in the `query` field as comment blocks (every
# line starts with '#') for provenance — those are not runnable and are skipped.
_FORM_RE = re.compile(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", re.IGNORECASE)


def strip_comments(q):
    return "\n".join(line for line in q.splitlines()
                     if not line.lstrip().startswith("#"))


def is_runnable_sparql(q):
    return bool(_FORM_RE.search(strip_comments(q)))


def _scalar_value(bindings):
    """If the result is a single cell (1 row, 1 variable) holding an integer,
    return it, else None.

    This handles the benchmark's dual `result_count` convention: for a lone
    scalar aggregate — `SELECT (COUNT(DISTINCT ?x) AS ?n)` with no GROUP BY —
    the author records the aggregate VALUE (e.g. 284), and the query returns one
    row. For everything else `result_count` is the ROW count. A query with two
    projected aggregates (`... (MAX(..) AS ?a) (COUNT(..) AS ?b)`) has two cells,
    so it is NOT a scalar and its recorded count is the row count (1)."""
    if len(bindings) != 1:
        return None
    row = bindings[0]
    if len(row) != 1:
        return None
    val = next(iter(row.values())).get("value", "")
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else None


def result_size(endpoint, query, timeout):
    """Run the query; return (n_rows, scalar_or_None, None) or (None, None, err).

    ASK -> (1, bool_as_int, None). SELECT -> (len(bindings), scalar, None) where
    `scalar` is the single-cell integer value if the result is one row of one
    variable, else None. The caller accepts a recorded count that matches EITHER
    n_rows or scalar, covering both `result_count` conventions."""
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "togomcp-drift-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        return None, None, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return None, None, f"net: {getattr(e, 'reason', e)}"
    except json.JSONDecodeError:
        return None, None, "non-JSON response (endpoint error page?)"
    except Exception as e:  # noqa: BLE001 - report anything else as an error row
        return None, None, f"{type(e).__name__}: {str(e)[:80]}"
    if "boolean" in payload:
        return 1, int(bool(payload["boolean"])), None
    try:
        bindings = payload["results"]["bindings"]
    except (KeyError, TypeError):
        return None, None, "unexpected result shape"
    return len(bindings), _scalar_value(bindings), None


def iter_queries(targets):
    """Yield (qfile, question_number, sq_dict) for the requested questions."""
    files = sorted(BASE_PATH.glob("question_*.yaml"))
    if targets:
        want = {int(t) for t in targets}
        files = [f for f in files
                 if int(re.search(r"(\d+)", f.stem).group(1)) in want]
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            print(f"  ⚠  {f.name}: YAML parse error ({e}); skipped")
            continue
        qnum = int(re.search(r"(\d+)", f.stem).group(1))
        for sq in (data.get("sparql_queries") or []):
            yield f, qnum, sq


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*",
                    help="question numbers to check (default: all)")
    ap.add_argument("--timeout", type=float, default=90.0,
                    help="per-query timeout in seconds (default: 90)")
    ap.add_argument("--delay", type=float, default=0.3,
                    help="polite delay between queries in seconds (default: 0.3)")
    ap.add_argument("--retries", type=int, default=1,
                    help="retries on network/timeout error (default: 1)")
    ap.add_argument("--strict", action="store_true",
                    help="also count ERROR rows toward a non-zero exit code")
    args = ap.parse_args()

    endpoints = load_endpoint_map()

    drifts, errors, skips, ok = [], [], [], 0
    for f, qnum, sq in iter_queries(args.targets):
        n = sq.get("query_number", "?")
        db = (sq.get("database") or "").strip()
        query = sq.get("query") or ""
        rc = sq.get("result_count")
        tag = f"Q{qnum:03d} q{n} [{db}]"

        if not is_runnable_sparql(query):
            skips.append((tag, "non-SPARQL step (OLS4/PubMed/NCBI note)"))
            continue
        if db not in endpoints:
            skips.append((tag, f"no endpoint for database '{db}'"))
            continue
        if not isinstance(rc, int):
            skips.append((tag, f"result_count not an int ({rc!r})"))
            continue

        rows = scalar = err = None
        for attempt in range(args.retries + 1):
            rows, scalar, err = result_size(endpoints[db], query, args.timeout)
            if err is None or not err.startswith("net"):
                break
            time.sleep(1.0 + attempt)  # brief backoff before a retry
        if args.delay:
            time.sleep(args.delay)

        if err is not None:
            errors.append((tag, err))
            print(f"  ⚠  {tag} ERROR: {err}", flush=True)
        elif rc == rows or rc == scalar:
            ok += 1
            # Show which signal matched, so a COUNT value reads clearly.
            shown = rc if rc == rows else f"{scalar} (scalar; {rows} row)"
            print(f"  ✓  {tag} {shown}", flush=True)
        else:
            live = f"{rows} row" + (f" / scalar={scalar}" if scalar is not None else "")
            drifts.append((tag, rc, live))
            print(f"  ✗  {tag} DRIFT: recorded={rc} live={live}", flush=True)

    print("\n" + "=" * 70)
    print(f"DRIFT CHECK  —  {ok} ok, {len(drifts)} drift, "
          f"{len(errors)} error, {len(skips)} skipped")
    print("=" * 70)
    if drifts:
        print("\nDRIFT (recorded result_count no longer reproduces — re-examine):")
        for tag, rc, got in drifts:
            print(f"  {tag}: recorded={rc} live={got}")
    if errors:
        print("\nERROR (endpoint unreachable / query failed — NOT counted as drift):")
        for tag, err in errors:
            print(f"  {tag}: {err}")

    rc_exit = len(drifts) + (len(errors) if args.strict else 0)
    sys.exit(min(rc_exit, 125))


if __name__ == "__main__":
    main()
