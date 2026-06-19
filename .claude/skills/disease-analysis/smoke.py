#!/usr/bin/env python3
"""Smoke test for the multi-scale disease-analysis workflow.

Exercises the SAME services the TogoMCP tools wrap — the RDF Portal SPARQL
endpoints and the TogoID REST API — so a future agent can confirm, from a clean
machine and WITHOUT the MCP server running, that the workflow's core query
patterns still resolve. Stdlib only (urllib); no pip install needed.

The MCP tools (run_sparql / togoid_convertId) are the real driver when an agent
runs the workflow. This script is the offline canary: if a SPARQL pattern here
returns zero rows, the corresponding step in SKILL.md / the workflow is broken.

Usage:
    python3 .claude/skills/disease-analysis/smoke.py
    python3 .claude/skills/disease-analysis/smoke.py --disease osteoarthritis

Exit code 0 = every check returned data. Non-zero = at least one check failed.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

SIB = "https://rdfportal.org/sib/sparql"        # uniprot
EBI = "https://rdfportal.org/ebi/sparql"        # reactome, chembl
TOGOID = "https://api.togoid.dbcls.jp"

TIMEOUT = 90


def sparql(endpoint, query):
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Accept": "application/sparql-results+json",
                 "User-Agent": "togomcp-disease-analysis-smoke/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())["results"]["bindings"]


def togoid_convert(ids, route):
    params = urllib.parse.urlencode(
        {"ids": ids, "route": route, "report": "pair", "format": "json"})
    req = urllib.request.Request(
        f"{TOGOID}/convert?{params}",
        headers={"User-Agent": "togomcp-disease-analysis-smoke/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read()).get("results", [])


def check(name, fn):
    try:
        rows = fn()
        n = len(rows)
        ok = n > 0
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {n} rows")
        return ok
    except Exception as e:  # noqa: BLE001 - surface any failure as a FAIL line
        print(f"FAIL  {name}: {type(e).__name__}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disease", default="osteoarthritis",
                    help="disease keyword for the UniProt full-text check")
    args = ap.parse_args()
    kw = args.disease.replace("'", "")

    results = []

    # Phase 2 — UniProt disease-associated proteins (bif:contains full-text)
    results.append(check(
        f"UniProt disease proteins ('{kw}')",
        lambda: sparql(SIB, f"""
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?protein ?mnemonic ?diseaseComment WHERE {{
  ?protein a up:Protein ; up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:mnemonic ?mnemonic ; up:annotation ?annot .
  ?annot a up:Disease_Annotation ; rdfs:comment ?diseaseComment .
  ?diseaseComment bif:contains "'{kw}'"
}} LIMIT 10""")))

    # Phase 4 — Reactome pathway search (bif:contains + score, FROM graph)
    results.append(check(
        "Reactome pathway search ('collagen degradation')",
        lambda: sparql(EBI, """
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
SELECT DISTINCT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome> WHERE {
  ?pathway a bp:Pathway ; bp:displayName ?name .
  ?name bif:contains "'collagen degradation'" option (score ?sc)
} ORDER BY DESC(?sc) LIMIT 10""")))

    # Phase 4 — Reactome participants (the ^^xsd:string xref trap)
    results.append(check(
        "Reactome participants (xsd:string xref)",
        lambda: sparql(EBI, """
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?reactionName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome> WHERE {
  ?reaction a bp:BiochemicalReaction ; bp:displayName ?reactionName ; bp:left ?e .
  FILTER(CONTAINS(?reactionName, "MMP"))
  ?e bp:entityReference ?ref . ?ref bp:xref ?x .
  ?x a bp:UnificationXref ; bp:db "UniProt"^^xsd:string ; bp:id ?uniprotId .
} LIMIT 10""")))

    # Phase 3 — TogoID protein cross-linking
    results.append(check(
        "TogoID uniprot,ncbigene",
        lambda: togoid_convert("P45452,P16112,O75173,Q9UNA0", "uniprot,ncbigene")))
    results.append(check(
        "TogoID uniprot,pdb",
        lambda: togoid_convert("P45452,P16112,O75173,Q9UNA0", "uniprot,pdb")))

    # Phase 1 — TogoID disease ontology cross-refs
    results.append(check(
        "TogoID mondo,mesh",
        lambda: togoid_convert("MONDO:0005178", "mondo,mesh")))

    # Phase 5 — TogoID drug cross-linking
    results.append(check(
        "TogoID chembl_compound,pubchem_compound",
        lambda: togoid_convert("CHEMBL118,CHEMBL139", "chembl_compound,pubchem_compound")))

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
