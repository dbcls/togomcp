#!/usr/bin/env python3
"""
Live claim-checker for the TogoMCP Usage Guide.

`check_mie_examples.py` runs the queries agents copy out of MIE files. Nothing ran
the assertions the *Usage Guide* makes — and the guide is the one document served
on every session, so a stale claim there is repeated to every client until someone
notices by hand.

Grepping the guide for ```sparql blocks finds almost nothing (two fragments, neither
runnable). The guide's testable surface is not queries but **empirical claims**:
"without `^^xsd:string` the join silently returns 0", "pinning only .../uniprot
returns empty for a taxon-name leg", "two-argument REGEX() returns 0 for alternation".
Each is a statement about live endpoint behaviour, each is what the surrounding advice
rests on, and each rots silently when an endpoint is reloaded or patched.

So each claim below is encoded as a pair of queries and an expected relationship
between them — usually "the documented-broken form returns 0 AND the documented-good
form does not", which is stronger than either half alone: it fails loudly both when a
trap disappears (endpoint fixed → the guide now scares people off a working pattern)
and when a workaround stops working (→ the guide's fix is wrong).

Two deliberate design choices:

  * **A script, not a pytest test.** These endpoints are genuinely unreliable — a
    single afternoon's work hit 502s, 503s and 90 s timeouts repeatedly — so a live
    test in the suite would go red for reasons unrelated to any change. Same reason
    `check_mie_examples.py` is a script. Run it at release time.
  * **Anchored to the guide text.** Every claim carries an `anchor` — a substring that
    must still appear in the guide. `tests/test_guide_claims_in_sync.py` enforces it
    offline, so a rewrite of the guide cannot leave this script confidently verifying
    a claim the guide no longer makes.

Usage:
    uv run python scripts/check_guide_claims.py            # all claims
    uv run python scripts/check_guide_claims.py --id regex_2arg_alternation
    uv run python scripts/check_guide_claims.py --list

Exit status is the number of failed claims (0 = all good). NET-FAIL (endpoint
unreachable) is reported separately and does NOT count as a failure — same
convention as check_mie_examples.py.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENDPOINTS_CSV = REPO / "togo_mcp" / "data" / "resources" / "endpoints.csv"

XSD = "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"
RDFS = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"


def endpoint_url(name: str) -> str:
    """Resolve an endpoint_name (primary, sib, ebi, …) to its URL from the registry."""
    with open(ENDPOINTS_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["endpoint_name"] == name:
                return row["endpoint_url"]
    raise SystemExit(f"unknown endpoint_name {name!r} in {ENDPOINTS_CSV}")


def _count(body: str) -> int | None:
    """Parse a single-column, single-row CSV count."""
    rows = [r for r in body.strip().split("\n") if r.strip()]
    if len(rows) < 2:
        return None
    try:
        return int(rows[1].strip().strip('"'))
    except ValueError:
        return None


def run(url: str, query: str, tries: int = 4, timeout: int = 90) -> tuple[str | None, str]:
    """Return (body, error). Retries gateway blips, which are endemic on these hosts."""
    last = ""
    for attempt in range(tries):
        data = urllib.parse.urlencode({"query": query}).encode()
        req = urllib.request.Request(url, data=data, headers={"Accept": "text/csv"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
            if "502 Bad Gateway" in body[:300] or "503 Service" in body[:300]:
                raise RuntimeError("gateway 5xx")
            return body, ""
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 — network layer, any failure is a retry
            last = f"{type(exc).__name__}: {exc}"
        if attempt < tries - 1:
            time.sleep(15)
    return None, last


# ---------------------------------------------------------------------------
# The claims. Each `check` receives a callable `q(query) -> body` and returns
# (ok: bool, detail: str). All figures verified live 2026-08-14.
# ---------------------------------------------------------------------------

VALS_ALT = '"Fentanyl" "Sufentanil" "Aspirin"'
VALS_BRACE = '"ab" "aab" "aaab" "xyz"'


def _regex_pair(q, values: str, pattern: str, expected: int):
    two = q(f'SELECT (COUNT(*) AS ?n) WHERE {{ VALUES ?s {{ {values} }} '
            f'FILTER(REGEX(?s, "{pattern}")) }}')
    three = q(f'SELECT (COUNT(*) AS ?n) WHERE {{ VALUES ?s {{ {values} }} '
              f'FILTER(REGEX(?s, "{pattern}", "")) }}')
    a, b = _count(two), _count(three)
    ok = a == 0 and b == expected
    return ok, f"2-arg={a} (guide: 0), 3-arg={b} (guide: {expected})"


CLAIMS: list[dict] = [
    {
        "id": "regex_2arg_alternation",
        "endpoint": "primary",
        "anchor": 'FILTER(REGEX(?s, "Fentanyl|Sufentanil"))',
        "says": "two-argument REGEX() returns 0 for alternation; a third argument fixes it",
        "check": lambda q: _regex_pair(q, VALS_ALT, "Fentanyl|Sufentanil", 2),
    },
    {
        "id": "regex_2arg_brace",
        "endpoint": "primary",
        "anchor": "a{1,2}b",
        "says": "two-argument REGEX() returns 0 for brace quantifiers; a third argument fixes it",
        "check": lambda q: _regex_pair(q, VALS_BRACE, "a{1,2}b", 3),
    },
    {
        "id": "regex_unaffected_constructs",
        "endpoint": "primary",
        "anchor": "Unaffected: plain substrings",
        "says": "character classes and anchors are NOT affected by the two-argument form",
        "check": lambda q: (
            lambda cls, anc: (
                cls == 1 and anc == 1,
                f"[Ff]entanyl={cls} (want 1), ^Aspirin$={anc} (want 1)",
            )
        )(
            _count(q(f'SELECT (COUNT(*) AS ?n) WHERE {{ VALUES ?s {{ {VALS_ALT} }} '
                     f'FILTER(REGEX(?s, "[Ff]entanyl")) }}')),
            _count(q(f'SELECT (COUNT(*) AS ?n) WHERE {{ VALUES ?s {{ {VALS_ALT} }} '
                     f'FILTER(REGEX(?s, "^Aspirin$")) }}')),
        ),
    },
    {
        "id": "reactome_typed_literal",
        "endpoint": "ebi",
        "anchor": "The `^^xsd:string` is mandatory",
        "says": "the Reactome BioPAX xref join needs ^^xsd:string; the plain form returns 0",
        "check": lambda q: (
            lambda typed, plain: (
                typed == 1 and plain == 0,
                f"typed={typed} (want 1), plain={plain} (guide: 0)",
            )
        )(
            _count(q(f'''{XSD}
                PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
                SELECT (COUNT(*) AS ?n) FROM <http://rdf.ebi.ac.uk/dataset/reactome>
                WHERE {{ ?p bp:xref [ bp:db "Reactome"^^xsd:string ;
                                      bp:id "R-HSA-196807"^^xsd:string ] }}''')),
            _count(q(f'''{XSD}
                PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
                SELECT (COUNT(*) AS ?n) FROM <http://rdf.ebi.ac.uk/dataset/reactome>
                WHERE {{ ?p bp:xref [ bp:db "Reactome" ; bp:id "R-HSA-196807" ] }}''')),
        ),
    },
    {
        "id": "uniprot_taxon_needs_taxonomy_graph",
        "endpoint": "sib",
        # NB: anchors are matched against the raw markdown, which is hard-wrapped —
        # keep every anchor within a single source line.
        "anchor": "`scientificName`/`rank` live in `.../taxonomy`",
        "says": "pinning only .../uniprot returns empty for a taxon-name leg; .../taxonomy has it",
        "check": lambda q: (
            lambda up, tax: (
                up == 0 and tax >= 1,
                f"pinned-uniprot={up} (guide: 0), pinned-taxonomy={tax} (want >=1)",
            )
        )(
            _count(q('''PREFIX up: <http://purl.uniprot.org/core/>
                SELECT (COUNT(*) AS ?n) FROM <http://sparql.uniprot.org/uniprot>
                WHERE { <http://purl.uniprot.org/taxonomy/9606> up:scientificName ?x }''')),
            _count(q('''PREFIX up: <http://purl.uniprot.org/core/>
                SELECT (COUNT(*) AS ?n) FROM <http://sparql.uniprot.org/taxonomy>
                WHERE { <http://purl.uniprot.org/taxonomy/9606> up:scientificName ?x }''')),
        ),
    },
    {
        "id": "mixed_literal_forms_need_str",
        "endpoint": "primary",
        "anchor": "Normalize literals with `STR(?label)`",
        "says": "one predicate in one graph carries mixed literal forms, so GROUP BY splits it "
                "(ontology/fma rdfs:label: ~104,919 @en + 17 xsd:string)",
        "check": lambda q: (
            lambda tagged, typed: (
                tagged > 1000 and typed > 0,
                f"@en={tagged} (want >1000), xsd:string={typed} (want >0) — both forms must coexist",
            )
        )(
            _count(q(f'''{RDFS}
                SELECT (COUNT(*) AS ?n) FROM <http://rdfportal.org/ontology/fma>
                WHERE {{ ?s rdfs:label ?l . FILTER(LANG(?l) = "en") }}''')),
            _count(q(f'''{XSD}
                {RDFS}
                SELECT (COUNT(*) AS ?n) FROM <http://rdfportal.org/ontology/fma>
                WHERE {{ ?s rdfs:label ?l . FILTER(DATATYPE(?l) = xsd:string) }}''')),
        ),
    },
]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--id", action="append", help="check only these claim ids (repeatable)")
    ap.add_argument("--list", action="store_true", help="list claim ids and exit")
    args = ap.parse_args()

    if args.list:
        for claim in CLAIMS:
            print(f"{claim['id']:34} [{claim['endpoint']:8}] {claim['says']}")
        return 0

    selected = [c for c in CLAIMS if not args.id or c["id"] in args.id]
    if not selected:
        print(f"no claim matched {args.id}", file=sys.stderr)
        return 2

    ok_n = fail_n = net_n = 0
    failures: list[str] = []
    for claim in selected:
        url = endpoint_url(claim["endpoint"])
        net_error: list[str] = []

        def q(query: str) -> str:
            body, err = run(url, query)
            if body is None:
                net_error.append(err)
                return ""
            return body

        try:
            passed, detail = claim["check"](q)
        except Exception as exc:  # noqa: BLE001 — a malformed claim is a claim failure
            passed, detail = False, f"checker raised {type(exc).__name__}: {exc}"

        if net_error:
            net_n += 1
            print(f"  ~  {claim['id']:34} NET-FAIL ({net_error[0]}) — endpoint unreachable")
        elif passed:
            ok_n += 1
            print(f"  ok {claim['id']:34} {detail}")
        else:
            fail_n += 1
            print(f"  XX {claim['id']:34} {detail}")
            failures.append(f"{claim['id']}: {claim['says']}\n      observed: {detail}")

    print("\n" + "=" * 70)
    print(f"GUIDE CLAIM CHECK — {ok_n} ok, {fail_n} failed, {net_n} net-fail")
    print("=" * 70)
    if failures:
        print("\nFAILED — the guide asserts something the endpoint no longer does:")
        for line in failures:
            print(f"    {line}")
        print("\n  Fix the guide (usage_guide_v6/), not this script — unless the claim was "
              "always wrong, in which case fix both.")
    return min(fail_n, 125)


if __name__ == "__main__":
    sys.exit(main())
