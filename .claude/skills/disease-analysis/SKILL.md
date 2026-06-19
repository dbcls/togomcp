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
  "what proteins/pathways/drugs are involved in X". The workflow source is
  workflows/disease_analysis.md.
---

# Disease Analysis (multi-scale, TogoMCP-driven)

Systematic analysis of any disease from molecular defect to clinical symptom,
built from structured queries (not model recall). The real driver is the
**TogoMCP MCP tools** (`run_sparql`, `togoid_convertId`, `togoid_countId`) plus
OLS4 and PubMed. The committed harness `smoke.py` is the offline canary that
proves the workflow's query patterns still resolve before you rely on them.

Paths below are relative to the repo root (`<unit>/`). The full prompt template,
output format, and per-disease-category customizations live in
[workflows/disease_analysis.md](workflows/disease_analysis.md) — read it for the
deliverable structure. This SKILL.md is the *operational* path: verified queries,
the exact tool calls, and the traps.

## Prerequisites

- A running TogoMCP server. Prefer the **local dev** server (`togomcp-dev` tools)
  — the remote registry can be stale. From the repo: `uv sync && uv run togo-mcp-local`.
- For the offline harness: Python 3 only (stdlib `urllib`; no pip install).
- Network access to `rdfportal.org` and `api.togoid.dbcls.jp`.

## Verify first (agent path — run this before trusting the workflow)

`smoke.py` hits the same SPARQL endpoints and TogoID API the MCP tools wrap, so
it works even with no MCP server running. Run it to confirm every workflow phase
still returns data:

```bash
python3 .claude/skills/disease-analysis/smoke.py
```

Expected (verified this session, ~30–60s):

```
PASS  UniProt disease proteins ('osteoarthritis'): 1 rows
PASS  Reactome pathway search ('collagen degradation'): 10 rows
PASS  Reactome participants (xsd:string xref): 10 rows
PASS  TogoID uniprot,ncbigene: 4 rows
PASS  TogoID uniprot,pdb: 65 rows
PASS  TogoID mondo,mesh: 1 rows
PASS  TogoID chembl_compound,pubchem_compound: 2 rows

7/7 checks passed
```

Point it at any disease keyword (drives only the UniProt full-text check):

```bash
python3 .claude/skills/disease-analysis/smoke.py --disease "Parkinson disease"
```

If a check **FAILS**, the corresponding workflow step is broken (endpoint down,
schema drift, or full-text index changed) — fix that before running the analysis,
and update the query pattern below + in workflows/disease_analysis.md.

## Run the analysis (the six phases, with verified tool calls)

Drive these with the `togomcp-dev` (preferred) or `togomcp` MCP tools. Each call
below was run live this session and returned data.

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
| `smoke.py` Reactome checks FAIL but UniProt passes | EBI endpoint down or schema drift; retry, then check `get_MIE_file(database="reactome")` for changed predicates |
| MCP `run_sparql` returns empty but `smoke.py` passes | You likely passed an endpoint group to `database=` or dropped `^^xsd:string` / `FROM` — compare against the verified queries above |
| TogoID convert returns `[]` | Route ordering wrong, or IDs in wrong format — check `togoid_getDataset(dataset="...")` and `togoid_getAllRelation()` |
| `urllib...timed out` in smoke.py | Endpoints are slow under load; rerun (TIMEOUT is 90s) |

## The harness

[smoke.py](.claude/skills/disease-analysis/smoke.py) — stdlib-only verifier of all
six phases against the live RDF Portal + TogoID services. Run it before an
analysis and whenever a query pattern here is edited. The MCP tools are the real
driver for the analysis itself; smoke.py proves the patterns they send are sound.
