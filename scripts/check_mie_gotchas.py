#!/usr/bin/env python3
"""
Gotcha-claim checker for TogoMCP MIE files — the prose half of MIE v3 spec §4.1.

`check_mie_examples.py` executes every example a reader might COPY. Nothing executed
the claims a reader is meant to BELIEVE. On 2026-08-25 four MIE headers (uniprot,
rhea, oma, bgee) were cross-checked against the live SIB endpoint and every one of
them carried a factual defect that no gate could see:

  - uniprot `reviewed_filter` prescribed the OPPOSITE of the working literal form;
  - oma  `mandatory_graph_pin` claimed a ×2.00 inflation that measures ×6.29;
  - oma  `entity_counts.proteins_note` and `property_path_timeout`, and bgee
    `huge_call_table`, each warned that an operation "TIMES OUT" — three operations
    that finish in 1–30 seconds.

The examples in those same files were clean, because examples get executed and prose
does not. That asymmetry is what this script removes.

A false "times out" is not a harmless over-warning: it steers the reader away from a
route that works, which is spec §4.4's failure arriving by the opposite door. Hence
`kind: error` — an operation that COMPLETES fails the check.

What it reads
-------------
`global_gotchas[].check` and, on any example, `traps_avoided[]` written as a mapping
`{say: ..., check: {...}}` instead of a bare string. Both live beside the claim they
settle, so the claim and its test cannot drift apart.

Check kinds (spec §3.6)
-----------------------
  count      `query` returns one scalar; must be within `expect.tolerance`
             (fractional, default 0.02) of `expect.value`
  ratio      two queries, each returning one scalar; the quotient must be within
             `expect.tolerance` (fractional, default 0.05) of `expect.ratio`. Spell the
             legs `unpinned:`/`pinned:` for an inflation claim, or `numerator:`/
             `denominator:` for any other comparison (equivalence is ratio 1.0)
  zero_rows  `query` must return 0 rows ("written this way it silently returns nothing")
  absent     `query` must return 0 rows ("this predicate/graph is not on this endpoint")
  error      `query` must FAIL — a SPARQL compile/execution error, or no answer within
             `expect.timeout_s` (default 60). Completing is a FAILURE.

Like `check_mie_examples.py` this harvests the file's PREFIX declarations and prepends
whichever a query uses but does not declare, and it separates infrastructure failure
(gateway 5xx, connection reset) from a real defect so a flaky endpoint never reads as
drift. `kind: error` needs a finer distinction than that: Virtuoso returns HTTP 500 for
a genuine query rejection ("transitive start not given"), which is a PASS, while a 502/
503/504 or a dead socket is infrastructure. `_is_query_error` draws that line on the
response body.

Un-checked falsifiable claims
-----------------------------
Also scans every `say` / `traps_avoided` string WITHOUT a `check:` for the shapes a
falsifiable claim takes (×N, "times out", "0 rows", "never", "no …", a bare figure) and
prints them as WARNINGS. This is deliberately a heuristic presented to a human, not a
gate: it cannot tell "returns 0 rows" from "read 0 rows as a legitimate answer", and
failing the build on a guess would train people to write vaguer prose. Warnings do not
affect the exit code; use `--strict` to make them count during a deliberate sweep.

Usage:
    uv run python scripts/check_mie_gotchas.py oma          # one DB
    uv run python scripts/check_mie_gotchas.py --all        # every MIE
    uv run python scripts/check_mie_gotchas.py --all --coverage-only   # just the warnings, no queries
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

KINDS = {"count", "ratio", "zero_rows", "absent", "error"}
DEFAULT_TOLERANCE = {"count": 0.02, "ratio": 0.05}
DEFAULT_ERROR_TIMEOUT_S = 60.0

_PREFIX_DECL = re.compile(r"^\s*PREFIX\s+([A-Za-z][\w.-]*)\s*:\s*(<[^>]+>)",
                          re.MULTILINE | re.IGNORECASE)

# Shapes a falsifiable claim takes in prose. Tuned to over-report rather than miss:
# a warning costs a human one glance, a missed claim cost this corpus four defects.
_FALSIFIABLE_PATTERNS = [
    (re.compile(r"[×x]\s?\d+(\.\d+)?", re.IGNORECASE), "multiplier"),
    (re.compile(r"\btimes?\s+out\b|\btimeout\b|\bunrunnable\b|\bdoes not (?:finish|complete)\b",
                re.IGNORECASE), "timeout/unrunnable"),
    (re.compile(r"\b(?:returns?|yields?|gives?)\s+(?:0|zero)\s+rows?\b", re.IGNORECASE), "zero-rows"),
    (re.compile(r"\b(?:zero|none|no)\s+(?:in|on|of)\s+(?:any|the)\b", re.IGNORECASE), "absence"),
    (re.compile(r"\bNO\s+[a-z]+:[A-Za-z_]", ), "absence"),
    (re.compile(r"\b\d{1,3}(?:,\d{3})+\b"), "figure"),
]


_FORM_RE = re.compile(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", re.IGNORECASE)


def is_runnable_sparql_like(q):
    """Does this look like an executable query rather than a prose fragment?

    Cheap structural gate so a malformed `check:` is caught by the offline test
    suite rather than at 06:17 on a Monday by the scheduled sweep.
    """
    if not isinstance(q, str):
        return False
    body = "\n".join(l for l in q.splitlines() if not l.lstrip().startswith("#"))
    return bool(_FORM_RE.search(body))


def load_endpoint_map():
    m = {}
    with open(ENDPOINTS_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            db = (row.get("database") or "").strip()
            url = (row.get("endpoint_url") or "").strip()
            if db and url:
                m[db] = url
    return m


def harvest_prefixes(file_text):
    """Union of every PREFIX declared anywhere in the MIE file (first wins)."""
    out = {}
    for name, iri in _PREFIX_DECL.findall(file_text):
        out.setdefault(name, iri)
    return out


def complete_query(query, file_prefixes):
    """Prepend any harvested PREFIX the query uses but does not itself declare."""
    declared = {m.group(1) for m in _PREFIX_DECL.finditer(query)}
    body = "\n".join(l for l in query.splitlines() if not l.lstrip().startswith("#"))
    used = set(re.findall(r"(?<![<\w])([A-Za-z][\w.-]*)\s*:", body))
    add = [f"PREFIX {n}: {file_prefixes[n]}"
           for n in used if n not in declared and n in file_prefixes]
    return ("\n".join(add) + "\n" + query) if add else query


def _is_query_error(code, body):
    """Did the ENDPOINT reject the query, or did the INFRASTRUCTURE fail?

    Only the first counts as a pass for `kind: error`. Virtuoso answers a genuine
    rejection with HTTP 500 and a body naming the engine and its SQLSTATE ("Virtuoso
    37000 Error TR...: transitive start not given"), so 500 alone cannot decide it —
    a gateway that is simply down also answers 500. 4xx is always the query's fault.
    """
    if code is not None and 400 <= code < 500:
        return True
    if code in (502, 503, 504):
        return False
    return bool(re.search(r"Virtuoso\s+\w+\s+Error|SPARQL\s+(?:compil|pars)|"
                          r"^\s*Parse\s+error|syntax error", body or "",
                          re.IGNORECASE | re.MULTILINE))


class Outcome:
    """One query result: rows/scalar, or a failure classified as query vs network."""

    def __init__(self, rows=None, scalar=None, detail="", query_error=False,
                 net_fail=False, elapsed=0.0):
        self.rows = rows
        self.scalar = scalar
        self.detail = detail
        self.query_error = query_error
        self.net_fail = net_fail
        self.elapsed = elapsed

    @property
    def failed(self):
        return self.query_error or self.net_fail


def run(endpoint, query, timeout):
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "togomcp-mie-gotcha-check"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            body = ""
        detail = re.sub(r"\s+", " ", body)[:140]
        el = time.time() - t0
        if _is_query_error(e.code, body):
            return Outcome(detail=f"HTTP {e.code}: {detail}", query_error=True, elapsed=el)
        return Outcome(detail=f"net HTTP {e.code}: {detail}", net_fail=True, elapsed=el)
    except (urllib.error.URLError, TimeoutError) as e:
        el = time.time() - t0
        reason = getattr(e, "reason", e)
        # A read timeout is the endpoint declining to finish — that IS the claim a
        # `kind: error` timeout gotcha makes, so it counts as a query-side failure.
        if isinstance(e, TimeoutError) or "timed out" in str(reason).lower():
            return Outcome(detail=f"timed out after {el:.0f}s", query_error=True, elapsed=el)
        return Outcome(detail=f"net: {reason}", net_fail=True, elapsed=el)
    except json.JSONDecodeError:
        return Outcome(detail="non-JSON response", net_fail=True, elapsed=time.time() - t0)
    except Exception as e:  # noqa: BLE001
        return Outcome(detail=f"{type(e).__name__}: {str(e)[:80]}", net_fail=True,
                       elapsed=time.time() - t0)

    el = time.time() - t0
    if "boolean" in payload:
        return Outcome(rows=1 if payload["boolean"] else 0,
                       scalar=1.0 if payload["boolean"] else 0.0, elapsed=el)
    try:
        bindings = payload["results"]["bindings"]
    except (KeyError, TypeError):
        return Outcome(detail="unexpected result shape", net_fail=True, elapsed=el)

    scalar = None
    if len(bindings) == 1 and len(bindings[0]) == 1:
        val = next(iter(bindings[0].values())).get("value", "")
        try:
            scalar = float(val)
        except (TypeError, ValueError):
            scalar = None
    rows = len(bindings)
    # A lone scalar aggregate returns ONE row even when it counts nothing — the
    # zero_rows/absent kinds mean "found nothing", so read the value, not the row.
    if scalar is not None:
        rows = 0 if scalar == 0 else rows
    return Outcome(rows=rows, scalar=scalar, elapsed=el)


def _tolerance(check, kind):
    exp = check.get("expect") or {}
    if "tolerance" in exp:
        return float(exp["tolerance"])
    return DEFAULT_TOLERANCE.get(kind, 0.05)


def evaluate(check, endpoint, prefixes, timeout, delay):
    """Run one `check:` block. Returns (status, message).

    status is 'ok' | 'fail' | 'net' | 'malformed'.
    """
    kind = check.get("kind")
    if kind not in KINDS:
        return "malformed", f"unknown kind {kind!r} (expected one of {sorted(KINDS)})"
    exp = check.get("expect") or {}

    def go(q, tmo):
        out = run(endpoint, complete_query(q, prefixes), tmo)
        if delay:
            time.sleep(delay)
        return out

    if kind == "ratio":
        # `unpinned`/`pinned` name the dominant case (a graph-pin collapsing union
        # inflation) and read better there; `numerator`/`denominator` are the neutral
        # spelling for a ratio that is not about pinning — e.g. "the transitive form
        # and the single-hop form return the SAME count", which is expect.ratio 1.0.
        num = check.get("unpinned") or check.get("numerator")
        den = check.get("pinned") or check.get("denominator")
        if not num or not den:
            return "malformed", ("kind: ratio needs two queries: `unpinned:`+`pinned:` "
                                 "or `numerator:`+`denominator:`")
        if "ratio" not in exp:
            return "malformed", "kind: ratio needs `expect: {ratio: N}`"
        if not is_runnable_sparql_like(num) or not is_runnable_sparql_like(den):
            return "malformed", "kind: ratio: a leg is not a SPARQL query"
        a = go(num, timeout)
        if a.net_fail:
            return "net", f"numerator leg: {a.detail}"
        if a.query_error:
            return "fail", f"numerator leg errored: {a.detail}"
        b = go(den, timeout)
        if b.net_fail:
            return "net", f"denominator leg: {b.detail}"
        if b.query_error:
            return "fail", f"denominator leg errored: {b.detail}"
        if a.scalar is None or b.scalar is None:
            return "malformed", "both ratio legs must return exactly one scalar (a COUNT)"
        if b.scalar == 0:
            return "fail", "pinned leg returned 0 — the ratio is undefined"
        got = a.scalar / b.scalar
        want = float(exp["ratio"])
        tol = _tolerance(check, kind)
        if abs(got - want) <= abs(want) * tol:
            return "ok", (f"ratio {got:.2f} (= {a.scalar:.0f}/{b.scalar:.0f}) "
                          f"within {tol:.0%} of {want}")
        return "fail", (f"ratio DRIFTED: {got:.2f} (= {a.scalar:.0f}/{b.scalar:.0f}), "
                        f"claim says {want} (±{tol:.0%})")

    query = check.get("query")
    if not query:
        return "malformed", f"kind: {kind} needs a `query:`"
    if not is_runnable_sparql_like(query):
        return "malformed", f"kind: {kind}: `query:` is not a SPARQL query"

    if kind == "error":
        tmo = float(exp.get("timeout_s", DEFAULT_ERROR_TIMEOUT_S))
        out = go(query, tmo)
        if out.net_fail:
            return "net", out.detail
        if out.query_error:
            return "ok", f"failed as claimed ({out.detail})"
        return "fail", (f"claim says this FAILS, but it COMPLETED in {out.elapsed:.1f}s "
                        f"returning {out.rows} row(s) — the warning steers readers off a "
                        f"working route; re-measure and rewrite the claim")

    out = go(query, timeout)
    if out.net_fail:
        return "net", out.detail
    if out.query_error:
        return "fail", f"query errored: {out.detail}"

    if kind in ("zero_rows", "absent"):
        if out.rows == 0:
            return "ok", f"0 rows as claimed ({out.elapsed:.1f}s)"
        return "fail", (f"claim says 0 rows, got {out.rows} "
                        f"(scalar={out.scalar}) — the claim is no longer true")

    # kind: count
    if "value" not in exp:
        return "malformed", "kind: count needs `expect: {value: N}`"
    if out.scalar is None:
        return "malformed", "kind: count needs a query returning exactly one scalar"
    want = float(exp["value"])
    tol = _tolerance(check, kind)
    if abs(out.scalar - want) <= abs(want) * tol:
        return "ok", f"{out.scalar:.0f} within {tol:.0%} of {want:.0f}"
    return "fail", f"count DRIFTED: {out.scalar:.0f}, claim says {want:.0f} (±{tol:.0%})"


def iter_claims(doc):
    """Yield (location, claim_text, check_or_None) for every falsifiable-capable claim.

    Two homes, per spec §3.6: a `global_gotchas` entry (`say` + optional `check`), and a
    `traps_avoided` line, which is a bare string by default and a `{say, check}` mapping
    when it carries one.
    """
    for i, g in enumerate(doc.get("global_gotchas") or []):
        if not isinstance(g, dict):
            continue
        loc = f"global_gotchas[{g.get('id', i)}]"
        yield loc, str(g.get("say", "")), g.get("check")
    for j, ex in enumerate(doc.get("examples") or []):
        if not isinstance(ex, dict):
            continue
        eid = ex.get("id", j)
        for k, tr in enumerate(ex.get("traps_avoided") or []):
            loc = f"examples[{eid}].traps_avoided[{k}]"
            if isinstance(tr, dict):
                yield loc, str(tr.get("say", "")), tr.get("check")
            else:
                yield loc, str(tr), None


def falsifiable_hints(text):
    """Which falsifiable shapes does this un-checked claim contain? (heuristic)"""
    return sorted({label for pat, label in _FALSIFIABLE_PATTERNS if pat.search(text)})


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dbs", nargs="*", help="database names to check")
    ap.add_argument("--all", action="store_true", help="check every MIE file")
    ap.add_argument("--timeout", type=float, default=180.0,
                    help="seconds for a normal check leg (default 180)")
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--coverage-only", action="store_true",
                    help="report un-checked falsifiable claims; run no queries")
    ap.add_argument("--strict", action="store_true",
                    help="count un-checked falsifiable claims toward the exit code")
    args = ap.parse_args()

    if not args.dbs and not args.all:
        ap.error("name at least one database, or pass --all")

    endpoints = load_endpoint_map()
    files = sorted(MIE_DIR.glob("*.yaml"))
    if args.dbs:
        want = set(args.dbs)
        files = [f for f in files if f.stem in want]
        missing = want - {f.stem for f in files}
        if missing:
            print(f"ERROR: no MIE file for: {', '.join(sorted(missing))}")
            return 2

    fails, nets, malformed, unchecked = [], [], [], []
    ok = 0

    for f in files:
        db = f.stem
        text = f.read_text(encoding="utf-8")
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as e:
            print(f"  ⚠  {db}: YAML parse error ({e})")
            malformed.append((db, "YAML parse error"))
            continue
        prefixes = harvest_prefixes(text)
        ep = endpoints.get(db)

        for loc, claim, check in iter_claims(doc):
            tag = f"{db} {loc}"
            if not check:
                hints = falsifiable_hints(claim)
                if hints:
                    unchecked.append((tag, hints, " ".join(claim.split())[:150]))
                continue
            if args.coverage_only:
                continue
            if not ep:
                print(f"  ~  {tag}: no endpoint in endpoints.csv — skipped", flush=True)
                continue
            status, msg = evaluate(check, ep, prefixes, args.timeout, args.delay)
            if status == "ok":
                ok += 1
                print(f"  ✓  {tag} [{check.get('kind')}] {msg}", flush=True)
            elif status == "net":
                nets.append((tag, msg))
                print(f"  ~  {tag} NET-FAIL: {msg}", flush=True)
            elif status == "malformed":
                malformed.append((tag, msg))
                print(f"  ⚠  {tag} MALFORMED CHECK: {msg}", flush=True)
            else:
                fails.append((tag, check.get("kind"), msg, " ".join(claim.split())[:200]))
                print(f"  ✗  {tag} [{check.get('kind')}] DRIFT: {msg}", flush=True)

    print("\n" + "=" * 74)
    print(f"MIE GOTCHA CHECK — {ok} ok, {len(fails)} drift, {len(malformed)} malformed, "
          f"{len(nets)} net-fail, {len(unchecked)} un-checked falsifiable claim(s)")
    print("=" * 74)

    if fails:
        print("\nDRIFT — the file asserts something the endpoint no longer agrees with.\n"
              "Re-measure, then fix the `say` AND the `check.expect`/`date` together:")
        for tag, kind, msg, claim in fails:
            print(f"\n  {tag} [{kind}]\n    {msg}\n    claim: {claim}")
    if malformed:
        print("\nMALFORMED — the check cannot be executed as written (see spec §3.6):")
        for tag, msg in malformed:
            print(f"  {tag}: {msg}")
    if nets:
        print("\nNET-FAIL (endpoint unreachable — NOT a drift; re-run later):")
        for tag, msg in nets:
            print(f"  {tag}: {msg}")
    if unchecked:
        print("\nUN-CHECKED FALSIFIABLE CLAIMS (heuristic — a human decides).\n"
              "Each looks like it asserts something runnable but carries no `check:`.\n"
              "Add one (spec §3.6), or reword so the claim is qualitative:")
        for tag, hints, claim in unchecked:
            print(f"  {tag}  [{', '.join(hints)}]\n      {claim}")

    exit_code = len(fails) + len(malformed) + (len(unchecked) if args.strict else 0)
    return min(exit_code, 125)


if __name__ == "__main__":
    sys.exit(main())
