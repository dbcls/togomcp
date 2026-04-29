---
name: mie-generator
description: Generate or update MIE (Metadata Interoperability Exchange) YAML files that describe RDF databases for TogoMCP. Use this skill whenever the user asks to create, write, regenerate, update, or improve an MIE file for any RDF database (UniProt, ChEMBL, Reactome, Rhea, PubChem, MeSH, PDB, or any new bio/chem database being added to TogoMCP), or mentions anything about the `togo_mcp/data/mie/` directory, MIE schema documentation, database onboarding for TogoMCP, or describing an RDF endpoint's schema/ShEx/SPARQL examples for LLM consumption. Trigger even if the user says things like "document this database", "add Reactome to our MIE collection", "the ChEMBL metadata file is out of date", or "I need to describe this SPARQL endpoint for Claude" — as long as the context is TogoMCP or an RDF database being described in YAML.
---

# MIE File Generator

An MIE file is a compact YAML document that describes an RDF database well enough for an LLM to write correct, efficient SPARQL against it on the first try. Good MIE files are the difference between "Claude writes a working query" and "Claude times out the endpoint with a `FILTER(CONTAINS())` over 244M triples".

This skill lives in a Claude Code environment with filesystem access and SPARQL execution tools (from the `togomcp_local` MCP server). Use filesystem tools freely — that is the normal mode of operation here.

## The Two Hard Rules

**1. No blind SPARQL retry loops.** Schema discovery legitimately requires many queries, but if a query fails twice in a row, stop and diagnose — wrong predicate, wrong graph, wrong IRI pattern — before retrying. More retries without diagnosis do not fix a structurally wrong query.

**2. Nothing in the MIE file is invented.** Every RDF triple in `sample_rdf_entries` must be retrievable from the endpoint. Every SPARQL query in `sparql_query_examples` and `cross_database_queries` must execute successfully against the real endpoint before the file is written. Fake examples are worse than missing examples because they train the downstream LLM to write queries that look right but fail silently.

## File locations in this environment

| Asset                      | Path                                       | Tool to use            |
|----------------------------|--------------------------------------------|------------------------|
| Existing MIE files         | `./togo_mcp/data/mie/<db>.yaml`            | Read / Write / Edit    |
| Endpoint registry          | `./togo_mcp/data/resources/endpoints.csv`  | Read / Edit            |

`./shex/<db>.shex` and `./togo_mcp/data/sparql-examples/<db>/` may exist as legacy prior art for some databases, but they are **optional**, not required, and may be stale. Phase 2 (live discovery) is the canonical source of truth — never let a local file override what the endpoint actually exposes.

The MCP tools `get_MIE_file`, `save_MIE_file`, `get_shex`, and `get_sparql_example` are **not** used in this environment — read and write these files directly. The remaining TogoMCP tools (`run_sparql`, `find_databases`, `list_databases`, `get_sparql_endpoints`, `get_graph_list`, the search APIs) ARE used; they hit live endpoints and cannot be replaced by filesystem access. `WebFetch` is used in Phase 0 to look up unregistered endpoints on rdfportal.org.

## Workflow

### Phase 0 — Register the endpoint (skip if already in `endpoints.csv`)

Before discovery, the target database must exist as a row in `./togo_mcp/data/resources/endpoints.csv`. The columns are `database,endpoint_url,endpoint_name,keyword_search_api`. If the user supplies only a dataset name, derive the rest from rdfportal.org.

1. **Check the registry first.** Read `./togo_mcp/data/resources/endpoints.csv`. If `<db>` is already a row, skip Phase 0 entirely — registration is done.

2. **Look up the dataset on rdfportal.org.** Call `WebFetch` on `https://rdfportal.org/access_methods/sparql_endpoints/` with a prompt asking which endpoint provider lists `<db>` and what its canonical slug is. The page is nested bullet lists grouped by provider; canonical dataset slugs match the names already used in the CSV (e.g. `uniprot`, `chembl`, `pdb`).

3. **Derive the row:**
   - `database` — canonical slug from the page (lowercase; strip spaces, dots, dashes).
   - `endpoint_url` — the parent provider's SPARQL URL (e.g. anything under "EBI" gets `https://rdfportal.org/ebi/sparql`).
   - `endpoint_name` — the URL path component (e.g. `https://rdfportal.org/ebi/sparql` → `ebi`).
   - `keyword_search_api` — **default to `sparql`**. Other valid values: a dedicated tool like `search_uniprot_entity`, an OLS4 path like `OLS4:searchClasses`, or `ncbi_esearch`. This requires human knowledge of which client tool fits — *tell the user the default and offer to override*. If unsure, leave as `sparql`; the user can edit later.

4. **Append** the row to `endpoints.csv` with `Edit` (preserve trailing newline; do not reorder existing rows).

5. **If the dataset isn't on the rdfportal.org page**, do **not** invent values. Tell the user, ask them for the SPARQL endpoint URL directly, then return to step 3 with their input.

After registration, proceed to Phase 1.

### Phase 1 — Orient (1–2 minutes)

Before touching the endpoint:

1. `Read ./togo_mcp/data/mie/<db>.yaml` — is there an existing MIE? If yes, this is an update, not a fresh build. Note which sections are weak; preserve verified content; refresh statistics.
2. Call `get_sparql_endpoints()` — confirm the endpoint URL is what you expect (it should already be in `endpoints.csv` after Phase 0).

That's it. Phase 2 is where the real work happens. Local prior art (legacy `./shex/<db>.shex`, `./togo_mcp/data/sparql-examples/<db>/`) is optional context; **do not let it shape the MIE without re-verification against the live endpoint**.

### Phase 2 — Discover (10–20 minutes)

Goal: extract the named graph(s), classes, typed predicates, IRI patterns, and representative entities you'll need so that `sparql_query_examples` can prefer structured lookups over text search. This is the canonical source of truth — every fact in the MIE comes from queries you ran here.

#### 2a. Identify the data graph(s)

Endpoints often host multiple databases (SIB hosts UniProt + Rhea + Bgee + OMA; the primary endpoint hosts ~30 ontologies and datasets). Picking the right graph(s) is step zero.

```python
get_graph_list("<db>")
```

`get_graph_list` filters out Virtuoso/OpenLink internal graphs and **ranks graphs whose URI contains the database slug at the top** — so `get_graph_list("bgee")` puts `<http://bgee.org>` first; `get_graph_list("supercon")` puts `<http://rdfportal.org/dataset/supercon>` first. Common URI conventions in RDF Portal: `http://<db>.org` (Bgee, Rhea, JCM), `http://rdfportal.org/dataset/<db>` (OMA, BRENDA, ChEBI, Reactome), `http://sparql.<db>.org/<db>` (UniProt). Browse the ranked list, pick the graph(s).

**Multi-graph databases** (UniProt, Bgee with subgraphs, etc.): if several graphs share the same prefix (e.g. `sparql.uniprot.org/{core,taxonomy,go,keywords,…}`), the database spans all of them — list them all in `schema_info.graphs` and document the role of each in `architectural_notes.schema_design`.

**No name match**: if no graph URI contains the slug, the data graph URI is unconventional. Fall back to running quick `COUNT(*)` queries on candidate graphs to find the largest data-bearing one, or inspect the dataset's documentation. This is rare on RDF Portal.

#### 2b. Enumerate classes and predicates

Once you know the graph(s), scope every discovery query with `GRAPH <…>`:

```sparql
# Classes and instance counts
SELECT ?class (COUNT(?s) AS ?n)
WHERE { GRAPH <http://example.org/dataset> { ?s a ?class } }
GROUP BY ?class ORDER BY DESC(?n) LIMIT 50

# Predicate usage (anchor on a major class to keep cardinality bounded)
SELECT ?p (COUNT(*) AS ?n)
WHERE { GRAPH <http://example.org/dataset> { ?s a <MajorClass> ; ?p ?o } }
GROUP BY ?p ORDER BY DESC(?n) LIMIT 50
```

Counts give you a feel for which classes are central (top 5 typically carry 90%+ of the data) and which predicates form the backbone of the schema. Skip BFO / CDAO / framework upper-types when documenting in `shape_expressions` — pick the canonical class.

#### 2c. DESCRIBE 3–5 representative entities

Pick entities that span the taxonomy of the database — a "central" entity (most-frequent class), a "linker" entity (something that joins multiple classes), and a "leaf" entity (terminal annotation):

```sparql
SELECT ?p ?o WHERE { GRAPH <…> { <iri-of-entity> ?p ?o } } LIMIT 200
```

(Plain `DESCRIBE` works on most endpoints but truncates unpredictably; the SELECT form above is more reliable.)

Use these inspections to nail down: IRI patterns (`http://<base>/<class>/<id>`), denormalized predicates (one predicate that serves multiple roles — e.g. Bgee's `genex:isExpressedIn` mixing anatomy IRIs and condition IRIs), measurement scaffolds (bnode chains for typed-value triples), and parallel namespace traps (the same NCBI taxon ID minted under two different IRI schemes — Bgee, see its critical_warnings).

#### 2d. Anchor IRIs via search tools

If the database has a dedicated search tool (`search_uniprot_entity`, `search_chembl_molecule`, `search_chembl_target`, `search_pdb_entity`, `search_reactome_entity`, `search_rhea_entity`, `search_mesh_descriptor`, `OLS4:searchClasses`, `ncbi_esearch`), use it to turn human-readable terms ("TP53", "tumor protein p53", "kinase activity") into specific IRIs. Then DESCRIBE those IRIs to learn the canonical predicate names. This is the fastest path from "I know what concept I'm looking for" to "I have a structured-IRI query that works."

If no search tool exists (BRENDA, BacDive, MediaDive, SuperCon, Glycosmos, NIMS): generate a short `bif:contains` (Virtuoso) probe to find one example, DESCRIBE it, and pivot to typed-predicate queries from there. Document this as the only legitimate text-search use, and note in `architectural_notes.text_search_justification` why no structured alternative existed.

### Phase 3 — Design the query set

You are going to write **exactly 7 SPARQL examples**: 2 basic, 3 intermediate, 2 advanced. The distribution across strategies should look like:

- ≥ 2 queries use specific IRIs or `VALUES` with IRIs
- ≥ 2 queries use typed predicates or graph navigation (`rdfs:subClassOf+`, `skos:broader+`)
- ≤ 1 query uses text search, and only if the Gate Check in `references/query-strategy.md` passes

If you find yourself reaching for `bif:contains` or `FILTER(CONTAINS(...))` more than once, stop and re-read `references/query-strategy.md`. Almost every field that looks "free text" in an RDF database is actually backed by a controlled vocabulary or IRI somewhere.

Read `references/query-strategy.md` now if you haven't — it contains the decision tree, the circular-reasoning trap, and the Virtuoso-specific `bif:contains` pitfalls (especially around property paths).

### Phase 4 — Write the file

Use `references/template.yaml` as your scaffold. Copy it to the target path, then fill it in. Required sections, in order:

1. `schema_info`
2. `critical_warnings` (use `[]` only if there are genuinely none — most real databases have at least one silent-failure trap)
3. `shape_expressions`
4. `sample_rdf_entries` — exactly 3, shared prefix block
5. `sparql_query_examples` — exactly 7, distribution 2/3/2
6. `cross_database_queries` — 1–2 if a shared endpoint exists, `examples: []` with explanatory `notes` otherwise
7. `cross_references`
8. `architectural_notes`
9. `data_statistics`
10. `anti_patterns` — 3–4, must include "schema check before text search"
11. `common_errors` — 2–3

Line budget: 400–600 lines typical, up to 700–900 for genuinely complex databases. If you're over 900, you are probably duplicating between `shape_expressions` and `architectural_notes` — consolidate.

`references/mie-structure.md` has the detailed requirements per section, and `references/template.yaml` is the fillable skeleton.

### Phase 5 — Validate (this is the non-negotiable part)

This phase is where most MIE files go wrong, and it's where this skill diverges most from a casual "just generate the YAML" approach.

**5a. Validate every RDF example.** For each of the 3 entries in `sample_rdf_entries`, write a SELECT that retrieves exactly those triples from the endpoint and confirm it returns results. If a triple can't be retrieved, either fix it (likely the IRI or predicate is wrong) or replace the entry with one you can retrieve. **No fabricated RDF ever reaches the final file.** The downstream LLM will copy these patterns — if they're wrong, every query it writes will inherit the error.

A practical check:

```sparql
ASK WHERE {
  <http://example.org/entity1> a ex:Type ;
                               ex:required "value" .
}
```

If `ASK` returns false, the triple as written does not exist in the endpoint. Do not include it.

**5b. Test every SPARQL query.** Run all 7 of `sparql_query_examples`, every example in `cross_database_queries`, and any SPARQL embedded in `cross_references`. Every single one. If a query times out or errors, fix it or replace it — do not ship queries that don't run. If a query runs but returns zero rows when it shouldn't, that's also a failure (usually a namespace trap — investigate and document in `critical_warnings`).

**5c. Verify statistics.** Every count or coverage percentage in `data_statistics` must come from a real query you ran, and must have a `verified_date`. If you can't verify a number, omit it rather than guessing.

**5d. Validate the YAML.** Load the file with PyYAML to confirm it parses:

```bash
python3 -c "import yaml; yaml.safe_load(open('./togo_mcp/data/mie/<db>.yaml'))"
```

If this fails, fix the YAML before calling the work done.

### Phase 6 — Final declaration

Only after Phases 1–5 are complete, report to the user:

```
✓ MIE file written to ./togo_mcp/data/mie/<db>.yaml
  - Sample RDF entries validated: 3/3 retrievable from endpoint
  - SPARQL queries tested: N/N executed successfully (N = 7 + cross-DB + cross-ref)
  - Statistics verified: [date]
  - YAML parses cleanly
  - Lines: [count]
```

If any bullet can't be checked off honestly, say so and explain what's left.

## Quality bar

A complete MIE file satisfies:

- Compact (400–600 lines typical, ≤ 900 for complex)
- `critical_warnings` documents every silent-failure trap (typos in predicates, IRI namespace mismatches, mandatory performance filters)
- All entity types appear in `shape_expressions` with inline counts
- Exactly 3 `sample_rdf_entries` with a single shared `rdf_prefixes` block — **all 3 validated against the endpoint**
- 7 SPARQL queries (2/3/2), 6–7 prioritising structured lookups, ≤ 1 using text search — **all tested**
- `bif:contains` preferred over `FILTER(CONTAINS())` on Virtuoso (check `access.backend`); property paths split before `bif:contains`
- No circular reasoning (never `VALUES ?x { <results-of-search-api> }` inside a COUNT)
- Cross-DB: 1–2 examples if shared endpoint, otherwise `examples: []` + explanatory notes
- `data_statistics` contains only verified counts/coverage — no `verification_queries`, `cardinality`, or `performance_characteristics` subfields
- Valid YAML
- Anti-patterns: 3–4, including "schema check before text search"
- Common errors: 2–3

## Reference files

- `references/query-strategy.md` — query design hierarchy, circular-reasoning trap, text-search Gate Check, Virtuoso pitfalls. **Read this before designing the query set.**
- `references/mie-structure.md` — per-section requirements, what goes where, what to omit.
- `references/template.yaml` — fillable YAML skeleton with inline comments.
- `references/anti-patterns.md` — worked examples of the four mandatory anti-patterns, plus common errors.

## One more thing about text search

Text search (`bif:contains`, `FILTER(CONTAINS())`) is seductive because it always "works" in the sense of not erroring out. It is almost never the right choice. Before using it, confirm:

- You have read the full `shape_expressions` and checked for specific IRIs
- You have checked for typed predicates with controlled vocabularies
- You have checked for hierarchical relationships (`rdfs:subClassOf`, `skos:broader`)
- You have used any available search API to find and DESCRIBE example entities
- You can write a sentence explaining why no structured alternative exists

If you cannot write that sentence, the structured alternative exists — keep looking.

Good luck. These files are a lot of work to get right, but a well-made MIE turns an unfamiliar RDF database into something the next LLM can actually query.
