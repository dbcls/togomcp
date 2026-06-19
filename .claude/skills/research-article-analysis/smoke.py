#!/usr/bin/env python3
"""Smoke test for the research-article-analysis workflow.

The workflow (workflows/research_article_analysis.md) validates a paper's claims
by running 2 SPARQL query types against each of 5 RDF databases — ChEBI, Rhea,
Reactome, UniProt, GO — then building a cross-database evidence chain. This
script runs the *corrected* form of all 10 query types against the live RDF
Portal endpoints (the same ones the TogoMCP run_sparql tool routes to), so a
future agent can confirm, offline and without the MCP server, that every query
type still resolves.

Two corrections are baked in vs. the workflow's printed templates (see SKILL.md
Gotchas): ChEBI uses the `chemrof:` namespace (not `chebi:`) for formula/mass/
smiles, and the UniProt function query must NOT join recommendedName with
classifiedWith (it times out) — they go in separate queries.

Stdlib only (urllib); no pip install. Exit 0 = all checks returned data.

    python3 .claude/skills/research-article-analysis/smoke.py
"""
import json
import sys
import urllib.parse
import urllib.request

# database -> endpoint URL (from togo_mcp/data/resources/endpoints.csv)
EP = {
    "uniprot":  "https://rdfportal.org/sib/sparql",
    "rhea":     "https://rdfportal.org/sib/sparql",
    "chebi":    "https://rdfportal.org/ebi/sparql",
    "reactome": "https://rdfportal.org/ebi/sparql",
    "go":       "https://rdfportal.org/primary/sparql",
}
TIMEOUT = 90

Q = {}

# --- ChEBI (CHEBI_16359 cholic acid) -------------------------------------
Q["chebi: structure (chemrof namespace!)"] = ("chebi", """
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX chemrof: <https://w3id.org/chemrof/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?formula ?mass ?smiles ?inchikey
FROM <http://rdf.ebi.ac.uk/dataset/chebi> WHERE {
  obo:CHEBI_16359 rdfs:label ?label ;
    chemrof:generalized_empirical_formula ?formula ; chemrof:mass ?mass .
  OPTIONAL { obo:CHEBI_16359 chemrof:smiles_string ?smiles }
  OPTIONAL { obo:CHEBI_16359 chemrof:inchi_key_string ?inchikey }
}""")

Q["chebi: hierarchy"] = ("chebi", """
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?label ?parent ?parentLabel
FROM <http://rdf.ebi.ac.uk/dataset/chebi> WHERE {
  obo:CHEBI_16359 rdfs:label ?label ; rdfs:subClassOf ?parent .
  ?parent rdfs:label ?parentLabel .
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/CHEBI_"))
} LIMIT 20""")

# --- Rhea (equation search + participants of RHEA:14541) ------------------
Q["rhea: equation search"] = ("rhea", """
PREFIX rhea: <http://rdf.rhea-db.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?reaction ?equation ?status ?ec WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
    rhea:equation ?equation ; rhea:status ?status .
  FILTER(CONTAINS(LCASE(?equation), "cholate"))
  OPTIONAL { ?reaction rhea:ec ?ec }
} LIMIT 10""")

Q["rhea: participants + chebi xref"] = ("rhea", """
PREFIX rhea: <http://rdf.rhea-db.org/>
SELECT ?equation ?side ?compound ?chebi WHERE {
  VALUES ?reaction { <http://rdf.rhea-db.org/14541> }
  ?reaction rhea:equation ?equation .
  OPTIONAL { ?reaction rhea:side ?side . ?side rhea:contains ?p .
    ?p rhea:compound ?compound . ?compound rhea:chebi ?chebi . }
} LIMIT 30""")

# --- Reactome (pathway structure + protein-ligand complex) ----------------
Q["reactome: pathway structure"] = ("reactome", """
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
SELECT DISTINCT ?pathway ?displayName ?component ?componentName
FROM <http://rdf.ebi.ac.uk/dataset/reactome> WHERE {
  ?pathway a bp:Pathway ; bp:displayName ?displayName .
  FILTER(CONTAINS(LCASE(?displayName), "bile acid"))
  OPTIONAL { ?pathway bp:pathwayComponent ?component .
    ?component bp:displayName ?componentName . }
} LIMIT 20""")

Q["reactome: complex"] = ("reactome", """
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
SELECT DISTINCT ?complex ?displayName ?component ?componentName
FROM <http://rdf.ebi.ac.uk/dataset/reactome> WHERE {
  ?complex a bp:Complex ; bp:displayName ?displayName .
  FILTER(CONTAINS(?displayName, "GPBAR1"))
  OPTIONAL { ?complex bp:component ?component .
    ?component bp:displayName ?componentName . }
} LIMIT 15""")

# --- UniProt (Q8TDU6 GPBAR1) — function and GO terms in SEPARATE queries --
Q["uniprot: function (name/EC, NO classifiedWith join)"] = ("uniprot", """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
SELECT ?mnemonic ?fullName ?ecNumber WHERE {
  uniprot:Q8TDU6 up:reviewed 1 ; up:mnemonic ?mnemonic ; up:recommendedName ?name .
  ?name up:fullName ?fullName .
  OPTIONAL { uniprot:Q8TDU6 up:enzyme ?ecNumber }
} LIMIT 10""")

Q["uniprot: GO terms (localization/function)"] = ("uniprot", """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
SELECT DISTINCT ?goTerm WHERE {
  uniprot:Q8TDU6 up:classifiedWith ?goTerm .
  FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
} LIMIT 50""")

# --- GO (definitions + hierarchy) -----------------------------------------
Q["go: definitions"] = ("go", """
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?term ?label ?definition
FROM <http://rdfportal.org/ontology/go> WHERE {
  VALUES ?term { obo:GO_0006954 obo:GO_0014732 }
  ?term rdfs:label ?label .
  OPTIONAL { ?term obo:IAO_0000115 ?definition }
}""")

Q["go: hierarchy"] = ("go", """
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?label ?parent ?parentLabel
FROM <http://rdfportal.org/ontology/go> WHERE {
  obo:GO_0014732 rdfs:label ?label ; rdfs:subClassOf ?parent .
  ?parent rdfs:label ?parentLabel .
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/GO_"))
} LIMIT 20""")


def sparql(endpoint, query):
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={"Accept": "application/sparql-results+json",
                 "User-Agent": "togomcp-article-analysis-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())["results"]["bindings"]


def main():
    passed = 0
    for name, (db, q) in Q.items():
        try:
            n = len(sparql(EP[db], q))
            ok = n > 0
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {n} rows")
            passed += ok
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    total = len(Q)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
