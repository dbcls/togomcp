#!/usr/bin/env python3
"""
Example-query checker for TogoMCP MIE files.

The 2026-07 co-tenancy sweep re-verified every MIE's `co_hosted_graphs` and
`critical_warnings` — but NOT the example queries agents actually copy. An audit
then found several `anti_patterns.correct_sparql` and `architectural_notes`
templates that silently return 0 rows or error against the live endpoint
(oma/supercon/taxonomy/chebi), each contradicting the file's own verified schema.
A "correct" example that returns 0 is worse than no example: it teaches a broken
query.

This script closes that gap for the runnable part. It is FORMAT-AGNOSTIC: a generic
recursive walk yields every value under a `sparql`, `correct_sparql`, or `query` key,
so it covers both v3 (`examples[].sparql` — the queries a reader copies) and any
lingering v2 files (`sparql_query_examples` / `cross_database_queries` `.sparql` and
`anti_patterns.correct_sparql`). It runs each against the database's own endpoint
(resolved from endpoints.csv) and flags ZERO-row and ERROR results. It deliberately
SKIPS `wrong_sparql` (those are meant to fail). In v3 there are no `correct_sparql`
blocks, so the "high confidence" bucket below is simply empty for a v3 file — every
example query is judged on the same ZERO/ERROR gate.

This is the runnable half of MIE v3 spec §4.1 ("a CI job can execute every example
and assert its `verified` result").

Asserting `verified:` (added 2026-09-14)
----------------------------------------
Until then this script did NOT compare the result to the file's `verified:` block. It
could not: across 334 examples that block used 198 different key sets — prose like
`first_row: "GL_002303 'Concanavalin-A' -> uniprot/P02866"`, figures under ad hoc names,
`result_rows` equal to the query's own LIMIT. So "a re-run that disagrees is a drift
signal" (§4.1) was true only for a human reading both. A few reserved keys make it
machine-decidable; every other key in `verified:` stays free-form annotation:

  n           a single-cell result (one row, one variable) — numeric, within `tolerance`
  row_count   number of result rows, within `tolerance`. Must be BELOW the query's LIMIT:
              a count that equals the cap says only that the cap was reached (min_rows)
  min_rows    at least this many rows — the honest assertion for a LIMIT-capped query
  has_values  list of values that must each appear as some cell of the result. A string
              matches a cell's full value or an IRI's local name (after the last / or #),
              exactly; a YAML number matches a numeric cell within `tolerance` (quote a
              number to make it exact). On a LIMIT-capped query it needs ORDER BY — without
              it the endpoint may return any N rows and the assertion fails at random
  tolerance   fractional, default 0.02 (same as a gotcha `count` check); applies to n,
              row_count and numeric has_values

Every v3 example must carry at least one of n / row_count / min_rows / has_values
(`expect_empty: true` examples are exempt). A wrong or missing assertion is MALFORMED; a
well-formed one the live result no longer satisfies is DRIFT. Both count toward the exit
code. `--lint-only` runs the MALFORMED half offline, without touching an endpoint.

Limits — this catches only the runnable-and-empty failure mode:
  - A query that returns the WRONG rows (e.g. taxonomy's bare-namespace-rank
    example returning botanical sections, or a join to the wrong graph that still
    yields plausible rows) passes here. Semantic correctness still needs a human /
    the co-tenancy audit.
  - Prose defects (a `data_integration` bullet prescribing a dead join, a stale
    graph-count) are invisible here.
So a clean run is necessary, not sufficient. ZERO/ERROR on a `correct_sparql` is a
near-certain defect; ZERO on a `sparql` example is a strong flag to review.

Network/timeout failures are reported as ERROR but called out separately so a flaky
endpoint is not mistaken for a broken query.

Exit code = ZERO + ERROR count over ALL example blocks (not just `correct_sparql`).
An earlier version gated only on `correct_sparql`, which let a broken `sparql`
example (pubmed's cross-DB join, wrong predicate → 0 rows) slip through triage — so
now every zero-row example fails the gate. A genuinely-empty example (rare — one that
demonstrates "no results is the answer") must be marked in the MIE with a sibling
`expect_empty: true` on that example dict; the checker then treats its 0 rows as OK,
and if such an example later STARTS returning rows it prints a "stale expect_empty"
note so the marker gets removed. Net-fail (5xx / timeout) never counts.

Usage:
    uv run python scripts/check_mie_examples.py                 # all MIEs
    uv run python scripts/check_mie_examples.py oma taxonomy    # specific DBs
    uv run python scripts/check_mie_examples.py --timeout 120
    uv run python scripts/check_mie_examples.py --lint-only     # offline: verified: shape only
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
    print("ERROR: PyYAML not installed. Run: uv sync")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
MIE_DIR = ROOT / "togo_mcp" / "data" / "mie"
ENDPOINTS_CSV = ROOT / "togo_mcp" / "data" / "resources" / "endpoints.csv"

# Keys whose value is a query the reader is meant to COPY. `wrong_sparql` is
# excluded on purpose — anti-pattern "wrong" queries are supposed to misbehave, and
# so is everything under a `check:` (see walk_queries).
COPY_KEYS = {"sparql", "correct_sparql", "query"}

_FORM_RE = re.compile(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", re.IGNORECASE)


def load_endpoint_map():
    m = {}
    with open(ENDPOINTS_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            db = (row.get("database") or "").strip()
            url = (row.get("endpoint_url") or "").strip()
            if db and url:
                m[db] = url
    return m


def is_runnable_sparql(q):
    body = "\n".join(l for l in q.splitlines() if not l.lstrip().startswith("#"))
    return bool(_FORM_RE.search(body))


_PREFIX_DECL = re.compile(r"^\s*PREFIX\s+([A-Za-z][\w.-]*)\s*:\s*(<[^>]+>)", re.MULTILINE | re.IGNORECASE)


def harvest_prefixes(file_text):
    """Union of every PREFIX declared anywhere in the MIE file. Anti-pattern
    snippets often omit their PREFIX lines (relying on the file's shared vocab);
    prepending the missing ones lets the checker judge query LOGIC (wrong class →
    0 rows) instead of flagging every prefix-less fragment as an ERROR."""
    out = {}
    for name, iri in _PREFIX_DECL.findall(file_text):
        out.setdefault(name, iri)  # first declaration wins
    return out


def complete_query(query, file_prefixes):
    """Prepend any harvested PREFIX the query uses but does not itself declare."""
    declared = {m.group(1) for m in _PREFIX_DECL.finditer(query)}
    body = "\n".join(l for l in query.splitlines() if not l.lstrip().startswith("#"))
    used = set(re.findall(r"(?<![<\w])([A-Za-z][\w.-]*)\s*:", body))
    add = [f"PREFIX {n}: {file_prefixes[n]}"
           for n in used if n not in declared and n in file_prefixes]
    return ("\n".join(add) + "\n" + query) if add else query


def walk_queries(node, path=""):
    """Yield (jsonpath, key, query_text, expect_empty, node) for every COPY_KEYS value.

    `node` is the dict holding the query — for a v3 example, the example itself, which is
    where its `verified:` block lives.

    `expect_empty` is the sibling `expect_empty: true` flag on the dict holding the
    query — the allowlist marker for an example that legitimately returns 0 rows.

    `check:` subtrees are skipped wholesale. A gotcha's check (MIE_v3_spec.md §3.6) is
    owned by `check_mie_gotchas.py`, and half its kinds hold a query written to FAIL —
    `zero_rows`, `absent` and `error` are all PASSES there and would every one of them
    be reported here as a broken example. Same reason `wrong_sparql` is excluded above:
    this script judges queries a reader is meant to COPY."""
    if isinstance(node, dict):
        expect_empty = bool(node.get("expect_empty"))
        for k, v in node.items():
            if k == "check":
                continue
            if k in COPY_KEYS and isinstance(v, str):
                yield f"{path}/{k}", k, v, expect_empty, node
            else:
                yield from walk_queries(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_queries(v, f"{path}[{i}]")


def run(endpoint, query, timeout):
    """Returns (bindings, error). `bindings` is a list of {var: value} string dicts; an ASK
    answer is returned as one row {"boolean": "true"|"false"}."""
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "togomcp-mie-example-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
            detail = re.sub(r"\s+", " ", body)[:140]
        except Exception:  # noqa: BLE001
            detail = ""
        # 5xx is a server/infra failure (gateway down, transaction timeout), NOT a
        # query defect — classify as net so a flaky endpoint isn't read as a broken
        # template. A genuine query error is a 400 (SPARQL compile) or 4xx.
        prefix = "net" if e.code in (500, 502, 503, 504) else f"HTTP {e.code}"
        return None, f"{prefix}: {detail}"
    except (urllib.error.URLError, TimeoutError) as e:
        return None, f"net: {getattr(e, 'reason', e)}"
    except json.JSONDecodeError:
        return None, "non-JSON response"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {str(e)[:80]}"
    if "boolean" in payload:
        return [{"boolean": "true" if payload["boolean"] else "false"}], None
    try:
        bindings = payload["results"]["bindings"]
    except (KeyError, TypeError):
        return None, "unexpected result shape"
    return [{var: cell.get("value", "") for var, cell in row.items()} for row in bindings], None


def effective_rows(rows):
    """Row count for the ZERO gate. A lone scalar aggregate — SELECT (COUNT(...) AS ?n) —
    returns ONE row even when it counts nothing. Treat a single-cell numeric 0 as "zero
    rows": that is exactly how oma/supercon's broken COUNT templates hide (1 row, value 0).
    An ASK answering false is zero rows too."""
    if len(rows) == 1 and len(rows[0]) == 1:
        val = next(iter(rows[0].values()))
        if val == "false":
            return 0
        try:
            if float(val) == 0:
                return 0
        except (TypeError, ValueError):
            pass
    return len(rows)


# ---------------------------------------------------------------------------
# verified: assertions (see module docstring)
# ---------------------------------------------------------------------------

ASSERT_KEYS = ("n", "row_count", "min_rows", "has_values")
DEFAULT_TOLERANCE = 0.02

_LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)\s*$", re.IGNORECASE)
_ORDER_RE = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)


def _query_body(query):
    """The query without comment lines or trailing `# ...` comments (IRIs keep their #)."""
    out = []
    for line in query.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(re.sub(r"\s#\s.*$", "", line))
    return "\n".join(out).strip()


def outer_limit(query):
    """The LIMIT that caps the whole result (a trailing LIMIT), or None. A LIMIT inside a
    subquery does not cap the rows the reader gets back, so only the final one counts."""
    m = _LIMIT_RE.search(_query_body(query))
    return int(m.group(1)) if m else None


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _as_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def lint_verified(example):
    """Offline shape check of one example's `verified:`. Returns a list of problems."""
    v = example.get("verified")
    if not isinstance(v, dict):
        return ["verified: must be a mapping with a date:"]
    problems = []
    if not v.get("date"):
        problems.append("verified: has no date:")
    present = [k for k in ASSERT_KEYS if k in v]
    if not present and not example.get("expect_empty"):
        problems.append("verified: asserts nothing — add n / row_count / min_rows / has_values")
    limit = outer_limit(example.get("sparql") or "")
    if "n" in v and not _is_number(v["n"]):
        problems.append(f"n must be a number, got {v['n']!r}")
    if "row_count" in v:
        rc = v["row_count"]
        if not isinstance(rc, int) or isinstance(rc, bool) or rc < 0:
            problems.append(f"row_count must be a non-negative integer, got {rc!r}")
        elif limit is not None and rc >= limit:
            problems.append(f"row_count {rc} reaches the LIMIT {limit} — that only says the cap "
                            "was hit; use min_rows")
    if "min_rows" in v:
        mr = v["min_rows"]
        if not isinstance(mr, int) or isinstance(mr, bool) or mr < 1:
            problems.append(f"min_rows must be a positive integer, got {mr!r}")
        elif limit is not None and mr > limit:
            problems.append(f"min_rows {mr} exceeds the LIMIT {limit}")
    if "has_values" in v:
        hv = v["has_values"]
        if not isinstance(hv, list) or not hv or any(isinstance(x, (dict, list)) for x in hv):
            problems.append("has_values must be a non-empty list of scalars")
        uncapped = isinstance(v.get("row_count"), int) and limit is not None and v["row_count"] < limit
        if limit is not None and not uncapped and not _ORDER_RE.search(_query_body(example.get("sparql") or "")):
            problems.append(f"has_values on a LIMIT {limit} query without ORDER BY — the endpoint "
                            "may return any rows; add ORDER BY or assert row_count/min_rows only")
    if "tolerance" in v:
        t = v["tolerance"]
        if not _is_number(t) or not 0 < t < 1:
            problems.append(f"tolerance must be a fraction in (0, 1), got {t!r}")
    return problems


def _cell_matches(expected, cell, tol=0.0):
    """A YAML number matches a numeric cell within `tol` (a count in a multi-column aggregate
    moves every release). A string matches exactly — the full value, or an IRI's local name;
    quote a number to demand an exact match (an identifier like "18390")."""
    if _is_number(expected):
        c = _as_float(cell)
        return c is not None and _within(expected, c, tol) if expected else c == 0
    if str(expected) == cell:
        return True
    return cell.startswith(("http://", "https://")) and str(expected) == re.split(r"[/#]", cell)[-1]


def _within(expected, actual, tol):
    return abs(actual - expected) <= tol * abs(expected)


def assert_verified(verified, rows):
    """Compare a live result with the reserved keys of `verified:`. Returns DRIFT messages."""
    tol = verified.get("tolerance", DEFAULT_TOLERANCE)
    drift = []
    if "n" in verified:
        if len(rows) != 1 or len(rows[0]) != 1:
            drift.append(f"n: expected a single-cell result, got {len(rows)} row(s)"
                         f"{' × ' + str(len(rows[0])) + ' var(s)' if rows else ''}")
        else:
            val = _as_float(next(iter(rows[0].values())))
            if val is None:
                drift.append(f"n: result cell is not numeric ({next(iter(rows[0].values()))!r})")
            elif not _within(verified["n"], val, tol):
                drift.append(f"n: recorded {verified['n']}, live {val:g} (tolerance {tol:g})")
    if "row_count" in verified and not _within(verified["row_count"], len(rows), tol):
        drift.append(f"row_count: recorded {verified['row_count']}, live {len(rows)} (tolerance {tol:g})")
    if "min_rows" in verified and len(rows) < verified["min_rows"]:
        drift.append(f"min_rows: recorded ≥{verified['min_rows']}, live {len(rows)}")
    for expected in verified.get("has_values") or []:
        if not any(_cell_matches(expected, cell, tol) for row in rows for cell in row.values()):
            drift.append(f"has_values: {expected!r} is no longer in the result")
    return drift


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dbs", nargs="*", help="database names to check (default: all)")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--lint-only", action="store_true",
                    help="check verified: shape offline; run no queries")
    args = ap.parse_args()

    endpoints = load_endpoint_map()
    files = sorted(MIE_DIR.glob("*.yaml"))
    if args.dbs:
        want = set(args.dbs)
        files = [f for f in files if f.stem in want]

    zero, errs, netfail, stale, skips, ok = [], [], [], [], 0, 0
    drift, malformed = [], []
    for f in files:
        db = f.stem
        text = f.read_text(encoding="utf-8")
        try:
            d = yaml.safe_load(text)
        except yaml.YAMLError as e:
            print(f"  ⚠  {db}: YAML parse error ({e})")
            continue
        file_prefixes = harvest_prefixes(text)
        ep = endpoints.get(db)
        for jpath, key, q, expect_empty, node in walk_queries(d):
            tag = f"{db} {jpath.lstrip('/')}"
            is_example = key == "sparql" and re.fullmatch(r"/examples\[\d+\]/sparql", jpath)
            if is_example:
                for problem in lint_verified(node):
                    malformed.append((tag, problem))
                    print(f"  ✗  {tag} MALFORMED: {problem}", flush=True)
            if args.lint_only:
                continue
            if not is_runnable_sparql(q) or not ep:
                skips += 1
                continue
            rows, err = run(ep, complete_query(q, file_prefixes), args.timeout)
            n = None if err else effective_rows(rows)
            if args.delay:
                time.sleep(args.delay)
            if err and err.startswith("net"):
                netfail.append((tag, key, err))
                print(f"  ~  {tag} NET-FAIL: {err}", flush=True)
            elif err:
                errs.append((tag, key, err))
                print(f"  ✗  {tag} [{key}] ERROR: {err}", flush=True)
            elif n == 0:
                if expect_empty:  # allowlisted — genuinely-empty example
                    ok += 1
                    print(f"  ✓  {tag} 0 rows (expect_empty)", flush=True)
                else:
                    zero.append((tag, key))
                    print(f"  ✗  {tag} [{key}] ZERO ROWS", flush=True)
            else:
                ok += 1
                if expect_empty:  # marker now lies — example returns rows
                    stale.append((tag, n))
                    print(f"  !  {tag} STALE expect_empty (now {n} rows)", flush=True)
            if is_example and not err and isinstance(node.get("verified"), dict):
                for message in assert_verified(node["verified"], rows):
                    drift.append((tag, message))
                    print(f"  ✗  {tag} DRIFT: {message}", flush=True)

    print("\n" + "=" * 70)
    print(f"MIE EXAMPLE CHECK — {ok} ok, {len(zero)} zero-row, {len(errs)} error, "
          f"{len(drift)} drift, {len(malformed)} malformed, "
          f"{len(netfail)} net-fail, {len(stale)} stale-marker, {skips} skipped")
    print("=" * 70)
    hi = lambda items: [t for t in items if t[1] == "correct_sparql"]  # noqa: E731
    if zero or errs:
        print("\nHIGH CONFIDENCE — anti_pattern correct_sparql that ZERO/ERROR (near-certain defect):")
        for tag, key, *rest in hi(zero) + hi(errs):
            print(f"  {tag}: {rest[0] if rest else 'ZERO ROWS'}")
        others = [(t, k, *r) for t, k, *r in (zero + errs) if k != "correct_sparql"]
        if others:
            print("\nEXAMPLES (sparql_query_examples / cross_database) that ZERO/ERROR"
                  " — disposition each; mark expect_empty only if 0 is genuinely correct:")
            for tag, key, *rest in others:
                print(f"  {tag}: {rest[0] if rest else 'ZERO ROWS'}")
    if stale:
        print("\nSTALE expect_empty (marker says empty but query now returns rows — remove the marker):")
        for tag, n in stale:
            print(f"  {tag}: now {n} rows")
    if drift:
        print("\nDRIFT (live result no longer matches verified: — re-measure; fix the query if it is "
              "wrong, else update the figure AND its date together. Never just widen tolerance):")
        for tag, message in drift:
            print(f"  {tag}: {message}")
    if malformed:
        print("\nMALFORMED verified: blocks (offline problems — see the module docstring):")
        for tag, problem in malformed:
            print(f"  {tag}: {problem}")
    if netfail:
        print("\nNET-FAIL (endpoint unreachable — NOT a query defect):")
        for tag, key, err in netfail:
            print(f"  {tag}: {err}")

    # Gate on EVERY un-allowlisted zero-row/error, stale markers (which lie), drift from
    # verified:, and verified: blocks that assert nothing checkable.
    sys.exit(min(len(zero) + len(errs) + len(stale) + len(drift) + len(malformed), 125))


if __name__ == "__main__":
    main()
