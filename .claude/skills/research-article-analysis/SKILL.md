---
name: research-article-analysis
description: >-
  Systematically validate a research article's claims against TogoMCP RDF
  databases — molecular formulas, reaction equations, pathways, protein function,
  GO definitions — instead of trusting the paper's text or keyword-search
  snippets. Use whenever the user asks to "analyze this paper/article", fact-check
  or validate a study's biology, verify claimed metabolites/reactions/pathways/
  proteins/processes against databases, score the evidence for a paper's claims,
  or build a cross-database evidence chain (ChEBI → Rhea → UniProt → Reactome →
  GO). Triggers on "article analysis", "validate this study", "check this paper's
  claims". The full method lives in references/research_article_analysis.md.
---

# Research Article Analysis (claim validation via TogoMCP SPARQL)

Validate a paper claim-by-claim by running structured SPARQL against five RDF
databases — **ChEBI, Rhea, Reactome, UniProt, GO** — and citing the query
results (exact formulas, equations, EC numbers, GO definitions), not the paper's
prose or keyword-search text. The driver is the **TogoMCP MCP tools**
(`run_sparql`, the `search_*` tools, `get_MIE_file`).

The full phased checklist, ID-tracking templates, scoring rubric, and
anti-skipping safeguards live in
[references/research_article_analysis.md](references/research_article_analysis.md)
— read it for the deliverable structure and discipline. **This SKILL.md is the
operational path: the SPARQL that actually works (the printed templates have two
bugs — see Gotchas), the verified tool calls, and the traps.**

## Prerequisites

- The **TogoMCP MCP server** connected to your client (e.g. Claude Desktop,
  Claude Code). Its `run_sparql`, `search_*`, and `get_MIE_file` tools are what
  drive this skill.
- Network access from that server to `rdfportal.org`.

## Warm-up check (confirm connectivity before trusting the templates)

Before relying on the templates, send the ChEBI structure query below through the
`run_sparql` tool and confirm it returns a row — that proves the endpoint is
reachable and the (chemrof-namespace) pattern still resolves. If it returns
nothing, that database's query type is broken (endpoint down or schema drift) —
re-read its MIE via `get_MIE_file` and fix the pattern below before relying on it.

## Run the analysis (phases, with verified queries)

Follow the phase discipline in the reference doc: **2A** select databases (5
rules), **2B** `get_MIE_file(database=...)` for each, **2C** keyword-search to
get IDs, **2D** run 2+ SPARQL per database using those IDs, **3A** reconstruct the
DB-backed logical flow (results → conclusion) + **3B** triage the gaps, **4** score
flow soundness, then deliver the four-part **FINAL SUMMARY** (main claim /
conclusion / DB-backed flow / gap analysis). Drive 2D with the TogoMCP
`run_sparql` tool. The query types below were all
run live (bile-acid example) and returned data — copy these, not the reference
doc's printed templates.

**ChEBI — structure (⚠ uses `chemrof:`, NOT `chebi:`):**
```
run_sparql(database="chebi", sparql_query="""
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
→ cholic acid, C24H40O5, 408.579, SMILES, InChIKey BHQCQFFYRZLCQQ-OELDTZBJSA-N
```
ChEBI hierarchy uses `rdfs:subClassOf` + the `obo/CHEBI_` filter (works as printed
in the reference doc). Definition is `obo:IAO_0000115`; monoisotopic mass is
`chemrof:monoisotopic_mass`; InChI string is `chemrof:inchi_string`.

**Rhea — equation search & participants (work as printed):**
```
run_sparql(database="rhea", sparql_query="""
PREFIX rhea: <http://rdf.rhea-db.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?reaction ?equation ?status ?ec WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ; rhea:equation ?equation ; rhea:status ?status .
  FILTER(CONTAINS(LCASE(?equation), "cholate"))
  OPTIONAL { ?reaction rhea:ec ?ec }
} LIMIT 10""")
→ RHEA:14541 "choloyl-CoA + H2O = cholate + CoA + H(+)", EC 3.1.2.27
```
Participants: `VALUES ?reaction { <http://rdf.rhea-db.org/14541> }` then
`rhea:side → rhea:contains → rhea:compound → rhea:chebi` → links to ChEBI IDs.

**Reactome — pathway structure & complex (work as printed):** always
`FROM <http://rdf.ebi.ac.uk/dataset/reactome>`; `FILTER(CONTAINS(LCASE(?displayName), "bile acid"))`
for pathways, `?complex a bp:Complex` + `bp:component` for complexes (e.g.
"GPBAR1: Bile acids"). For UniProt xrefs inside Reactome use `bp:db "UniProt"^^xsd:string`.

**UniProt — function & GO (⚠ split into TWO queries):**
```
# Query A: name + EC. Do NOT add up:classifiedWith here — the join TIMES OUT.
run_sparql(database="uniprot", sparql_query="""
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
SELECT ?mnemonic ?fullName ?ecNumber WHERE {
  uniprot:Q8TDU6 up:reviewed 1 ; up:mnemonic ?mnemonic ; up:recommendedName ?name .
  ?name up:fullName ?fullName .
  OPTIONAL { uniprot:Q8TDU6 up:enzyme ?ecNumber }
} LIMIT 10""")
→ GPBAR_HUMAN, "G-protein coupled bile acid receptor 1"

# Query B: GO terms in a separate query (fast on its own).
run_sparql(database="uniprot", sparql_query="""
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
SELECT DISTINCT ?goTerm WHERE {
  uniprot:Q8TDU6 up:classifiedWith ?goTerm .
  FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
} LIMIT 50""")
→ GO_0005886, GO_0038182, GO_0097009, ...
```

**GO — definitions & hierarchy (work as printed):** always
`FROM <http://rdfportal.org/ontology/go>`, `DISTINCT`, and the `obo/GO_` filter.
Definitions via `obo:IAO_0000115`; hierarchy via `rdfs:subClassOf`.

**Cross-database evidence chain** (the reference doc's required deliverable) is real
and reproducible: ChEBI cholate (`CHEBI_15378`) appears as a `rhea:chebi`
participant of RHEA:14541, whose EC links to a UniProt enzyme, which appears in
the Reactome "GPBAR1: Bile acids" complex, annotated with GO terms.

Read MIE files first for any database you haven't queried this session:
`get_MIE_file(database="chebi")`, etc. The MIE is the authoritative, freshest
schema source.

## Gotchas (the template bugs and silent-fail traps)

- **ChEBI: the reference doc's printed structure query returns ZERO rows.** It uses
  `chebi:formula` / `chebi:mass` / `chebi:smiles` / `chebi:inchikey`
  (`http://purl.obolibrary.org/obo/chebi/`). RDF Portal's ChEBI stores those under
  the **chemrof** namespace instead: `chemrof:generalized_empirical_formula`,
  `chemrof:mass`, `chemrof:smiles_string`, `chemrof:inchi_key_string`
  (`https://w3id.org/chemrof/`). Use the corrected query above. The hierarchy
  query is fine because it only uses `rdfs:subClassOf`.
- **UniProt: combining `up:recommendedName` + `up:classifiedWith` in one query
  TIMES OUT** (60s) on the SIB endpoint even with a single bound accession. Split:
  name/EC in one query, GO terms (`classifiedWith`) in another. The workflow's
  "Query Type 1" template combines them — don't.
- **`run_sparql` `database=` vs `endpoint_name=`** are different axes (single DB
  key vs endpoint group); a wrong value fails deterministically — don't retry.
- **`FROM` graph is mandatory** and differs per DB: ChEBI/Reactome →
  `http://rdf.ebi.ac.uk/dataset/{chebi,reactome}`; GO → `http://rdfportal.org/ontology/go`.
  Rhea and UniProt take no `FROM`. Wrong/missing graph → empty results, no error.
- **Reactome string xref needs `^^xsd:string`** (`bp:db "UniProt"^^xsd:string`);
  a plain literal silently matches nothing.
- **UniProt: always `up:reviewed 1`**; never put `bif:contains` on a property
  path (split it). **Rhea/Reactome/GO: always `LIMIT`** on exploratory queries.
- **Keyword search ≠ validation.** The whole point of the workflow: every ID from
  a `search_*` call must be fed back into a SPARQL query, and you cite the SPARQL
  result, not the search snippet.

## Troubleshooting

| Symptom | Fix |
|---|---|
| ChEBI structure query returns 0 rows | Confirm chemrof predicates with `SELECT ?p ?o { obo:CHEBI_16359 ?p ?o FILTER(isLiteral(?o)) }`; namespace may have changed again |
| UniProt query `ReadTimeout` | You joined `recommendedName` with `classifiedWith` — split into two queries (see above) |
| `run_sparql` returns empty unexpectedly | Missing/wrong `FROM` graph, dropped `^^xsd:string`, or `chebi:` instead of `chemrof:` — diff against the verified queries here |
| `go: definitions` returns 0 | GO uses the `primary` endpoint and `FROM <http://rdfportal.org/ontology/go>` — not the ebi graph |

## Full method

[references/research_article_analysis.md](references/research_article_analysis.md)
— the full phased checklist, ID-tracking templates, scoring rubric, and
anti-skipping safeguards. This SKILL.md gives the corrected operational queries;
that file gives the discipline and the deliverable structure.
