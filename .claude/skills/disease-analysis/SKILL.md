---
name: disease-analysis
description: >-
  Run a multi-scale disease pathophysiology analysis — molecular defects through
  to clinical symptoms — using TogoMCP (RDF Portal SPARQL), TogoID ID conversion,
  OLS4, and PubMed. Use whenever the user asks to "analyze a disease", build a
  disease mechanism model, find disease-associated proteins/pathways/drugs, map a
  disease across biological scales (molecular → pathway → cellular → tissue →
  clinical → treatment), or convert disease/protein/drug IDs across databases for
  a disease. Also triggers on "disease analysis", "pathophysiology of X",
  "what proteins/pathways/drugs are involved in X". The full method lives in
  references/disease_analysis.md.
---

# Disease Analysis (multi-scale, TogoMCP-driven)

Systematic analysis of any disease from molecular defect to clinical symptom,
built from structured queries (not model recall). The driver is the
**TogoMCP MCP tools** (`run_sparql`, `togoid_convertId`, `togoid_countId`) plus
OLS4 and PubMed.

The full prompt template, output format, and per-disease-category customizations
live in [references/disease_analysis.md](references/disease_analysis.md) — read it
for the deliverable structure. This SKILL.md is the *operational* path: verified
queries, the exact tool calls, and the traps.

## Prerequisites

- The **TogoMCP MCP server** connected to your client (e.g. Claude Desktop,
  Claude Code). Its `run_sparql`, `togoid_*`, `search_*`, and `get_MIE_file`
  tools are what drive this skill.
- The **OLS4** and **PubMed** MCP tools (used in Phase 1 and Phase 6).
- Network access from those servers to `rdfportal.org` and `api.togoid.dbcls.jp`.

## Warm-up check (confirm connectivity before trusting the workflow)

Before a full analysis, send one Phase-2 query and one TogoID conversion through
the MCP tools and confirm both return rows — that proves the SPARQL endpoint and
the TogoID API are both reachable and the patterns still resolve:

```
run_sparql(database="uniprot", sparql_query="""
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?protein WHERE {
  ?protein a up:Protein ; up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:annotation ?annot .
  ?annot a up:Disease_Annotation ; rdfs:comment ?c .
  ?c bif:contains "'osteoarthritis'"
} LIMIT 5""")
togoid_convertId(ids="P45452", route="uniprot,pdb")     → structures for MMP13
```

If either returns nothing, that step is broken (endpoint down, schema drift, or
full-text index changed) — diagnose it (re-read the database's MIE via
`get_MIE_file`) before running the analysis.

## Run the analysis (the six phases, with verified tool calls)

Drive these with the TogoMCP MCP tools. Each call below was run live and
returned data.

**Phase 1 — Disease ID & ontology cross-refs.** Resolve the disease to MONDO via
OLS4, then fan out:
```
togoid_convertId(ids="MONDO:0005178", route="mondo,mesh")   → [["0005178","D010003"]]
togoid_convertId(ids="MONDO:0005178", route="mondo,doid")
togoid_convertId(ids="MONDO:0005178", route="mondo,hp_phenotype")
togoid_convertId(ids="MONDO:0005178", route="mondo,omim_phenotype")
```

**Phase 2 — Disease-associated proteins (UniProt SPARQL).** Full-text search over
disease annotations. `bif:contains` must sit on a *plain variable*, never a
property path:
```
run_sparql(database="uniprot", sparql_query="""
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?protein ?mnemonic ?fullName ?diseaseComment WHERE {
  ?protein a up:Protein ; up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:mnemonic ?mnemonic ; up:recommendedName ?name ; up:annotation ?annot .
  ?name up:fullName ?fullName .
  ?annot a up:Disease_Annotation ; rdfs:comment ?diseaseComment .
  ?diseaseComment bif:contains "'osteoarthritis'"
} LIMIT 30""")
→ Q9BXN1 / ASPN_HUMAN (Asporin), D14 allele association
```

**Phase 3 — Cross-link proteins (TogoID).** For each UniProt accession:
```
togoid_convertId(ids="P45452,P16112,O75173,Q9UNA0", route="uniprot,ncbigene")  → 4 pairs
togoid_convertId(ids="P45452,P16112,O75173,Q9UNA0", route="uniprot,pdb")       → 65 structures
togoid_countId(ids="P45452,P16112,O75173", source="uniprot", target="pdb")     → {"source":3,"target":58}
# also: uniprot,hgnc · uniprot,chembl_target · uniprot,go · uniprot,reactome_pathway
```

**Phase 4 — Pathway analysis (Reactome SPARQL).** Always include the `FROM` graph;
score with `bif:contains`. Then get participants — the protein xref **requires
`"UniProt"^^xsd:string`** (see Gotchas):
```
run_sparql(database="reactome", sparql_query="""
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?reactionName ?proteinName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome> WHERE {
  ?reaction a bp:BiochemicalReaction ; bp:displayName ?reactionName ; bp:left ?entity .
  FILTER(CONTAINS(?reactionName, "MMP") || CONTAINS(?reactionName, "collagen"))
  ?entity bp:entityReference ?proteinRef .
  ?proteinRef bp:xref ?xref .
  ?xref a bp:UnificationXref ; bp:db "UniProt"^^xsd:string ; bp:id ?uniprotId .
  OPTIONAL { ?proteinRef bp:name ?proteinName }
  FILTER(STRLEN(?uniprotId) = 6)
} LIMIT 50""")
→ MMP9 (P52176), MMP2 ...
```

**Phase 5 — Drugs & targets.** `search_chembl_molecule` / `search_chembl_target`
to find IDs, then:
```
togoid_convertId(ids="CHEMBL118,CHEMBL139", route="chembl_compound,pubchem_compound") → [["CHEMBL118","2662"],["CHEMBL139","3033"]]
togoid_convertId(ids="CHEMBL118,CHEMBL139", route="chembl_compound,drugbank")
# get_compound_attributes_from_pubchem(...) for properties
```

**Phase 6 — Literature.** `PubMed:search_articles("<disease> <mechanism> <treatment>")`
then `get_article_metadata` / `get_full_text_article`.

Read MIE files first when querying a database you haven't this session:
`get_MIE_file(database="reactome")`, `get_MIE_file(database="uniprot")`. The MIE
is the authoritative schema/warnings source and is fresher than this doc.

## Gotchas (the traps that silently return zero rows)

- **Reactome xref typing — the #1 silent-fail.** `bp:db "UniProt"^^xsd:string`.
  A plain `"UniProt"` literal (no `^^xsd:string`) matches nothing and returns an
  empty result with no error. Same applies to any `VALUES`/literal compared
  against Reactome string-typed data. Pre-flight every quoted literal against the
  database's MIE `critical_warnings` before running.
- **Reactome has two UniProt xref flavors:** `"UniProt"` (~91k) and
  `"UniProt Isoform"` (~374). Filtering on only one can silently drop proteins
  (e.g. NPC1L1 / Q9UHC9 is only reachable via the isoform form). For exhaustive
  coverage match both.
- **`bif:contains` cannot sit on a property path.** `?p up:recommendedName/up:fullName ?n . ?n bif:contains "..."` → 400. Split into two triples and put `bif:contains` on the terminal variable.
- **`run_sparql` `database=` vs `endpoint_name=`** are different axes — `database`
  is a single DB key (`uniprot`, `reactome`); `endpoint_name` is an endpoint group
  (`sib`, `ebi`). Don't mix; a wrong value fails deterministically — don't retry it.
- **Reactome needs `FROM <http://rdf.ebi.ac.uk/dataset/reactome>`** or you get
  wrong/empty results.
- **Always `up:reviewed 1` + `taxonomy/9606`** on UniProt disease queries, and a
  `LIMIT` everywhere, or you get TrEMBL noise / timeouts.
- **TogoID route ordering matters** (`uniprot,ncbigene` ≠ `ncbigene,uniprot`).
  Use `togoid_countId` as a cheap pre-check before a bulk `convertId`.
- **Disease keyword matters more than the MONDO ID** for Phase 2 — "osteoarthritis"
  returns 1 protein, broader keywords return more. Try synonyms if a disease
  returns nothing.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Reactome query returns empty but UniProt works | EBI endpoint down or schema drift; retry, then check `get_MIE_file(database="reactome")` for changed predicates |
| `run_sparql` returns empty unexpectedly | You likely passed an endpoint group to `database=` or dropped `^^xsd:string` / `FROM` — compare against the verified queries above |
| TogoID convert returns `[]` | Route ordering wrong, or IDs in wrong format — check `togoid_getDataset(dataset="...")` and `togoid_getAllRelation()` |
| Query times out | Endpoints are slow under load; add/lower a `LIMIT` and retry |

## Full method

[references/disease_analysis.md](references/disease_analysis.md) — the complete
prompt template, the deliverable/output structure, and the per-disease-category
customizations. This SKILL.md gives the operational queries and traps; that file
gives the shape of the final analysis.
