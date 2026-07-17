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

This script closes that gap for the runnable part. For every MIE it extracts the
`sparql` blocks (from `sparql_query_examples` and `cross_database_queries`) and the
`correct_sparql` blocks (from `anti_patterns`) — the queries a reader is meant to
COPY — runs each against the database's own endpoint (resolved from endpoints.csv),
and flags ZERO-row and ERROR results. It deliberately SKIPS `wrong_sparql` (those
are meant to fail).

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
# excluded on purpose — anti-pattern "wrong" queries are supposed to misbehave.
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
    """Yield (jsonpath, key, query_text, expect_empty) for every COPY_KEYS value.

    `expect_empty` is the sibling `expect_empty: true` flag on the dict holding the
    query — the allowlist marker for an example that legitimately returns 0 rows."""
    if isinstance(node, dict):
        expect_empty = bool(node.get("expect_empty"))
        for k, v in node.items():
            if k in COPY_KEYS and isinstance(v, str):
                yield f"{path}/{k}", k, v, expect_empty
            else:
                yield from walk_queries(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_queries(v, f"{path}[{i}]")


def run(endpoint, query, timeout):
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
        return (1 if payload["boolean"] else 0), None
    try:
        bindings = payload["results"]["bindings"]
    except (KeyError, TypeError):
        return None, "unexpected result shape"
    # A lone scalar aggregate — SELECT (COUNT(...) AS ?n) — returns ONE row even
    # when it counts nothing. Treat a single-cell numeric 0 as "zero rows": that
    # is exactly how oma/supercon's broken COUNT templates hide (1 row, value 0).
    if len(bindings) == 1 and len(bindings[0]) == 1:
        val = next(iter(bindings[0].values())).get("value", "")
        try:
            if float(val) == 0:
                return 0, None
        except (TypeError, ValueError):
            pass
    return len(bindings), None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dbs", nargs="*", help="database names to check (default: all)")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()

    endpoints = load_endpoint_map()
    files = sorted(MIE_DIR.glob("*.yaml"))
    if args.dbs:
        want = set(args.dbs)
        files = [f for f in files if f.stem in want]

    zero, errs, netfail, stale, skips, ok = [], [], [], [], 0, 0
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
        for jpath, key, q, expect_empty in walk_queries(d):
            tag = f"{db} {jpath.lstrip('/')}"
            if not is_runnable_sparql(q) or not ep:
                skips += 1
                continue
            n, err = run(ep, complete_query(q, file_prefixes), args.timeout)
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

    print("\n" + "=" * 70)
    print(f"MIE EXAMPLE CHECK — {ok} ok, {len(zero)} zero-row, {len(errs)} error, "
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
    if netfail:
        print("\nNET-FAIL (endpoint unreachable — NOT a query defect):")
        for tag, key, err in netfail:
            print(f"  {tag}: {err}")

    # Gate on EVERY un-allowlisted zero-row/error, plus stale markers (which lie).
    sys.exit(min(len(zero) + len(errs) + len(stale), 125))


if __name__ == "__main__":
    main()
