# MIE File Specification v2.1

## 1. Overview

### 1.1 Purpose
Metadata Interoperability Exchange (MIE) files are compact YAML documents that describe an RDF database well enough for an LLM to write correct, efficient SPARQL against it on the first try. A good MIE file is the difference between "the assistant writes a working query" and "the assistant times out the endpoint with `FILTER(CONTAINS())` over 244M triples".

### 1.2 Design Philosophy

**Essential over exhaustive.** Documentation is compact, clear, and complete — sufficient for effective querying without unnecessary content. Target 400–600 lines typical, 700–900 for genuinely complex databases.

**Structured lookups over text search.** Every non-trivial field in an RDF database is backed by a controlled vocabulary or IRI. MIE files train the reader to prefer specific IRIs, typed predicates, and graph navigation, and to reach for text search (`bif:contains`, `FILTER(CONTAINS())`) only when no structured alternative exists.

**Nothing is invented.** Every RDF triple in `sample_rdf_entries` must be retrievable from the endpoint. Every SPARQL query in `sparql_query_examples` and `cross_database_queries` must execute successfully against the real endpoint before the file is written. Fake examples are worse than missing examples because they train the downstream assistant to write queries that look right but fail silently.

### 1.3 Format
- **File Format**: YAML
- **Encoding**: UTF-8
- **Extension**: `.yaml`
- **Location**: `togo_mcp/data/mie/[database].yaml`

### 1.4 Key Updates in v2.1

- **`shape_expressions` discipline**: every `@<ShapeRef>` must resolve to a defined block in the same section; optional co-types written as separate `a [ T ] ?` lines, not grouped in `a [ T1 T2 … ] +`.
- **Phase 2 — Discover, expanded**: per-class predicate survey for *every* class going into `shape_expressions` (not only the anchor class); parent-anchored bnode-tracing query; cardinality distribution query with the modifier-mapping table; flag predicates with surprising COUNT distributions as `critical_warnings` candidates during the survey itself.
- **Phase 5 — Validate, expanded** to four new audit steps: 5e (`shape_expressions` audit), 5f (`critical_warnings` content verification), 5g (`cross_references` IRI form + coverage verification), 5h (non-standard PREFIX base-URI verification). Phase 5b additionally tests every `correct_sparql` block in `anti_patterns` and spot-checks cross-database join validity. Phase 5c additionally cross-checks `data_statistics` arithmetic.
- **`schema_info.categories` enforcement**: after writing categories, call `list_categories()` and confirm exact-match (case + underscores).
- **`data_statistics.by_class`**: documented as a structured per-class count block alongside `total_entities` and `coverage`.
- **LIMIT rule relaxed**: a query must have a *bounded* result set — `LIMIT` is required unless the query is an aggregate (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`), an `ASK`, or anchored on a specific-IRI subject whose cardinality is bounded by the schema.

### 1.5 Key Updates in v2.0

- **New section**: `critical_warnings` — schema pathologies, silent-failure traps, mandatory performance filters. Placed early so a reader scans it first.
- **Sample RDF entries**: reduced from 5 to 3 entries, with a single shared `rdf_prefixes` block instead of repeated `@prefix` declarations per entry.
- **Query strategy hierarchy**: explicit priority order (specific IRIs → typed predicates → graph navigation → text search) and a Gate Check before using any form of text search.
- **Circular reasoning guidance**: don't populate `VALUES` with search-API results and then `COUNT` them.
- **Filesystem-based workflow**: MIE files are read and written directly, not through dedicated MCP tools.
- **Validation requirements strengthened**: every example RDF triple must be retrievable from the endpoint; every example query must execute successfully.
- **`data_statistics` simplified**: removed `verification_queries`, `cardinality`, and `performance_characteristics` sub-sections as auditing clutter.
- **`anti_patterns` expanded**: 3–4 entries (was 2–3), at least one addressing "schema check before text search".

## 2. File Structure

### 2.1 Required Sections

MIE files contain the following sections in order:

1. `schema_info` — database metadata, endpoint, graphs, backend
2. `critical_warnings` — silent-failure traps, mandatory performance filters, IRI namespace traps, required typos
3. `shape_expressions` — ShEx schemas for all entity types
4. `sample_rdf_entries` — 3 validated RDF examples with shared prefix block
5. `sparql_query_examples` — 7 tested queries (2 basic / 3 intermediate / 2 advanced)
6. `cross_database_queries` — cross-database integration (empty with notes if isolated endpoint)
7. `cross_references` — external database links organised by RDF pattern
8. `architectural_notes` — design patterns, query strategy, performance
9. `data_statistics` — verified counts and coverage
10. `anti_patterns` — 3–4 common mistakes with corrections
11. `common_errors` — 2–3 error scenarios with causes and solutions

### 2.2 Section Dependencies

- All 11 sections are required and appear in the specified order.
- `critical_warnings` may be `[]` only if the author has genuinely verified that no silent-failure traps exist (rare — most real databases have at least one).
- `cross_database_queries.examples` may be `[]` if the database is on an isolated endpoint, but the section itself is still present with an explanatory `notes` block.
- No additional top-level sections are permitted.

## 3. Section Specifications

### 3.1 schema_info

#### 3.1.1 Purpose
Provides essential metadata about the RDF database, including access methods, keyword search capabilities, and triple-store backend.

#### 3.1.2 Required Fields

```yaml
schema_info:
  title: string                    # REQUIRED: canonical database name
  description: |                   # REQUIRED: 2-3 sentences covering:
                                   # - what the database contains
                                   # - main entity types
                                   # - primary use cases
    ...
  keywords: array<string>          # REQUIRED: 8-15 lowercase discovery terms (see §3.1.5)
  categories: array<string>        # REQUIRED: 1-3 entries from controlled taxonomy (see §3.1.5)
  endpoint: uri                    # REQUIRED: SPARQL endpoint URL
  base_uri: uri                    # REQUIRED: base namespace URI
  graphs: array<uri>               # REQUIRED: named graph URIs
  kw_search_tools: array<string>   # REQUIRED: keyword search tools (may be [])
  version:                         # REQUIRED: version metadata
    mie_version: string            # REQUIRED: MIE spec version (e.g., "2.0")
    mie_created: date              # REQUIRED: ISO 8601 format (YYYY-MM-DD)
    data_version: string           # REQUIRED: database version/release
    update_frequency: string       # REQUIRED: update schedule
  access:                          # REQUIRED: access metadata
    backend: string                # REQUIRED: triple store (determines bif:contains support)
```

#### 3.1.3 Keyword Search Tools Field

The `kw_search_tools` field enumerates keyword-search methods available for this database. Use `[]` if none are available.

**Dedicated search tools:**
- `search_uniprot_entity`, `search_pdb_entity`, `search_chembl_molecule`, `search_chembl_target`, `search_reactome_entity`, `search_rhea_entity`, `search_mesh_descriptor`

**OLS4 (Ontology Lookup Service):**
- `OLS4:searchClasses` — for ChEBI, GO, Mondo, NANDO, etc.

**NCBI E-utilities:**
- `ncbi_esearch` — for PubChem, Taxonomy, ClinVar, PubMed, NCBIGene, MedGen

**SPARQL-only:**
- `"sparql"` — use `run_sparql()` with `bif:contains` (Virtuoso) or `FILTER(CONTAINS())`

#### 3.1.4 Constraints

- `description` is 2–3 sentences and documents the major entity types.
- All URIs are valid and accessible.
- `mie_created` uses ISO 8601 (`YYYY-MM-DD`).
- `access.backend` is required; it determines whether `bif:contains` is available and therefore drives query-strategy decisions downstream.
- `keywords` are lowercase, single tokens or short phrases; 8–15 entries.
- `categories` come from the controlled taxonomy in §3.1.5; 1–3 entries per database. **Use the exact token verbatim — lowercase, underscores for multi-word slugs (e.g. `drug_target`). Do not Title Case (`Genomics`), pluralize (`proteins`), space-separate (`comparative genomics`), or invent variants (`proteomics`, `gene_annotation`). The token must match an entry in the §3.1.5 table character-for-character.**
- **After writing `categories`, call `list_categories()` and verify each token is an exact match (same case, same underscores) against the returned list.** Off-spec tokens silently exclude the database from `find_databases(category=…)` results — a failure invisible during MIE development.

#### 3.1.5 Keywords and Categories

Both fields drive the `find_databases()` discovery tool — a token-efficient alternative to `list_databases()` that lets a downstream LLM filter the catalog by topic instead of reading every description.

**`keywords`** — 8–15 lowercase terms. Curate to maximize recall:

- Include the canonical entity types and concepts that characterize the database.
- Include common synonyms a user might type instead of the canonical term:
  - variant ↔ mutation ↔ polymorphism
  - drug ↔ compound ↔ chemical
  - transcript ↔ mRNA
  - protein ↔ amino acid sequence
- Skip stopwords and generic filler ("data", "database", "contains", "available").
- Skip terms that appear only incidentally in the description.

**`categories`** — pick 1–3 from the controlled taxonomy below. **Copy the token from the table verbatim** (lowercase, underscores for multi-word slugs). Title-cased, pluralized, space-separated, or invented variants will fragment `list_categories()` into single-DB buckets. Tag only categories that genuinely characterize the database, not every category whose vocabulary appears once.

| Category | Use for |
|---|---|
| `protein` | Protein sequence, function, domains, isoforms |
| `gene` | Gene records, transcripts, gene-level annotations |
| `variant` | SNPs, mutations, polymorphisms, clinical variants |
| `compound` | Small molecules, ligands, chemical entities |
| `drug_target` | Drug–target bioactivity, IC50, binding affinity |
| `pathway` | Biological pathways, signaling cascades |
| `reaction` | Enzyme reactions, biochemical reactions |
| `ontology` | Controlled vocabularies, ontologies (GO, MeSH, MONDO, etc.) |
| `structure` | 3D structures, crystallography, cryo-EM |
| `literature` | Publications, citations, full-text articles |
| `taxonomy` | Organism / species / taxon hierarchies |
| `microbe` | Bacterial / archaeal strains, growth conditions, culture media |
| `glycan` | Glycans, glycosylation, glycomics |
| `antimicrobial` | AMR, antibiotic resistance |
| `sequence` | Nucleotide sequence repositories |
| `disease` | Disease, phenotype, clinical associations |
| `materials` | Materials science — crystal structure, lattice parameters, alloys, oxides, polymers |
| `physics` | Physical properties and measurements — Tc, magnetic fields, conductivity, thermal coefficients |
| `enzymology` | Enzyme function, kinetics, EC numbers, substrates / inhibitors / activators |
| `genomics` | Genome-scale resources, gene nomenclature, cross-genome catalogs |

When adding a new category, update both this taxonomy and the `find_databases` tool documentation.

### 3.2 critical_warnings

#### 3.2.1 Purpose

Schema pathologies, IRI traps, mandatory performance filters, and typos that must be preserved verbatim. A reader scans this section first — anything that causes queries to return 0 rows without erroring, or to time out silently, belongs here.

#### 3.2.2 Structure

```yaml
critical_warnings: |
  - [warning text]
  - [warning text]
```

Use a YAML pipe (`|`) block with bullet-style paragraphs. Use `[]` only if genuinely confirmed no traps exist.

#### 3.2.3 What to include

**Mandatory performance filters.** A status flag or filter that, if omitted, inflates the result set by orders of magnitude and causes COUNT queries to time out.

*Example:* `Always add ?entry up:reviewed 1 — omitting it queries 244M instead of 589K entries.`

**IRI namespace traps.** When the same concept has multiple IRI representations and only one is used as the object of a particular predicate. These fail silently (return 0 rows, no error).

*Example:* `GO terms in up:classifiedWith use OBO IRIs (http://purl.obolibrary.org/obo/GO_XXXXXXX), NOT http://purl.uniprot.org/go/.`

**Typos required verbatim.** Some databases preserve misspelled predicates for backwards compatibility. Using the "correct" spelling returns zero rows.

*Example:* `dct:referecens (not dct:references). Using the corrected spelling returns zero results.`

**Graph-specific patterns.** When a predicate only resolves in a specific named graph, or when the union graph behaves differently from what an SPO query against named graphs would suggest.

#### 3.2.4 Constraints

- Each warning is concise but specific enough to be actionable.
- Prefer concrete failure modes ("returns 0 rows") over abstract advice ("be careful with namespaces").
- Place this section immediately after `schema_info` so readers encounter it before writing any queries.

#### 3.2.5 Verification

Every predicate name and IRI string cited in `critical_warnings` must be confirmed against the live endpoint before publishing (Phase 5f). A warning about a non-existent predicate is worse than no warning — the downstream LLM will avoid the wrong thing while the real trap stays unflagged.

Trap candidates should be identified systematically during Phase 2 by flagging surprising COUNT distributions (per-class predicate surveys) — not reconstructed from memory in Phase 4. See §4.3.

### 3.3 shape_expressions

#### 3.3.1 Purpose

ShEx schemas for every major entity type. Build from DESCRIBE queries against representative entities.

#### 3.3.2 Format

```yaml
shape_expressions: |
  PREFIX declarations

  <EntityShape> {
    property declarations
  }
```

#### 3.3.3 Requirements

- Covers all major entity types discovered during schema exploration.
- Inline comments document: instance counts, non-obvious predicate semantics, IRI patterns and namespace gotchas, measurement scaffolds and indirect value-access patterns (blank nodes, reified statements).
- Uses standard ShEx syntax with relevant `PREFIX` declarations.
- Uses YAML pipe (`|`) syntax.

#### 3.3.4 Constraints

- Comments are minimal but load-bearing — a comment that doesn't change how the reader writes queries is noise.
- Shape names are descriptive (`<ProteinShape>`, `<CompoundShape>`).
- All shapes reflect actual data patterns, not aspirational schemas.

#### 3.3.5 Structural Rules

- **Every `@<ShapeRef>` must resolve to a defined block in the same section.** A referenced-but-undefined shape is a structural error — the downstream LLM generates property-path queries that silently return nothing.
- **Mark optional co-types explicitly.** When a class is sometimes (but not always) additionally typed with a second class, write each sub-type as a separate optional constraint rather than grouping them in a single `a [ T1 T2 T3 ] +` block. The grouped form is correct ShEx but visually implies all types are always co-present:

  ```shex
  # Avoid — looks like all three are always expected:
  a [ ex:MainType ex:SubTypeA ex:SubTypeB ] + ;

  # Prefer — cardinality is explicit and verifiable:
  a [ ex:MainType ] ;
  a [ ex:SubTypeA ] ?   # ~80% of instances — confirmed by COUNT
  a [ ex:SubTypeB ] ?   # ~80% of instances — confirmed by COUNT
  ```

- **Bnode shapes reached via different parent classes can differ.** The same predicate name can resolve to differently-shaped bnodes on different parent classes (e.g. `faldo:location` → `ExactPosition` on one class, `Region` on another). Document each as its own shape; do not assume equivalence.

#### 3.3.6 Verification

Every shape must be backed by Phase 2 discovery: a per-class predicate survey, parent-anchored bnode tracing for every bnode-valued predicate, and a cardinality distribution query for every modifier (`?`, `+`, `*`, or absent). See §4.3 for the queries. The Phase 5e audit re-runs the predicate survey to confirm completeness.

### 3.4 sample_rdf_entries

#### 3.4.1 Purpose

Three representative RDF examples demonstrating data patterns. Every triple is retrievable from the endpoint.

#### 3.4.2 Structure

```yaml
sample_rdf_entries:
  rdf_prefixes: |
    @prefix ex: <http://example.org/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  entries:
    - title: string
      description: string          # 1 sentence
      rdf: |
        Actual RDF from database
```

#### 3.4.3 Requirements

- **Exactly 3 entries.**
- **Single shared `rdf_prefixes` block** at the top of the section. `@prefix` declarations are NOT repeated in each entry.
- The 3 entries collectively:
  1. Cover the most important entity type in the database
  2. Demonstrate at least one non-obvious access pattern (measurement scaffold, blank-node reification, cross-reference scaffold, etc.)
  3. Connect to external resources via cross-references where applicable
- Each entry has a 1-sentence `description` stating what it illustrates.
- RDF content uses YAML pipe (`|`) syntax.

#### 3.4.4 Validation (non-negotiable)

**Every triple in every entry must be retrievable from the endpoint.** Before finalising the file, validate each entry by running a SELECT or ASK query that retrieves the exact triples shown:

```sparql
ASK WHERE {
  ex:entity1 a ex:Type ;
             ex:required "value" .
}
```

If `ASK` returns false, the triple as written does not exist. Fix the entry (likely the IRI or predicate is wrong) or replace it with a triple that can be retrieved. **No fabricated RDF ever reaches the final file.**

#### 3.4.5 Constraints

- Count: exactly 3 entries.
- Description: 1 sentence.
- RDF: valid Turtle consistent with the shared prefix block.

### 3.5 sparql_query_examples

#### 3.5.1 Purpose

Seven tested, working SPARQL queries that teach the schema to a downstream reader. Each query should generalise — a reader should be able to swap in a different IRI and get a different-but-sensible result.

#### 3.5.2 Structure

```yaml
sparql_query_examples:
  - title: string
    description: string            # 1-2 sentences
    question: string               # natural language
    complexity: basic|intermediate|advanced
    sparql: |
      Tested query with LIMIT
```

#### 3.5.3 Requirements

- **Exactly 7 queries**, distribution:
  - 2 queries with `complexity: basic`
  - 3 queries with `complexity: intermediate`
  - 2 queries with `complexity: advanced`
- Across the set:
  - At least 2 queries use specific IRIs or `VALUES` with IRIs.
  - At least 2 queries use typed predicates or graph navigation (`rdfs:subClassOf+`, `skos:broader+`).
  - At most 1 query uses text search, and only if the Gate Check (section 3.5.5) passes.
- Every query produces a bounded result set — `LIMIT` is required unless the query is an aggregate (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`), an `ASK`, or anchored on a specific-IRI subject whose cardinality is bounded by the schema (e.g. `<one-protein> rdfs:label ?label`). In all other cases include `LIMIT`.
- None are cross-database queries (those belong in `cross_database_queries`).
- All use YAML pipe (`|`) syntax.

#### 3.5.4 Validation (non-negotiable)

**Every query must be executed successfully against the endpoint before the file is written.** This is not a sample — test all 7.

Acceptable outcomes:
- Query runs and returns meaningful results.
- Query runs and returns an empty result set that is documented as intentional.

Not acceptable:
- Query times out → fix or replace.
- Query errors → fix or replace.
- Query returns 0 rows when it should return many → investigate (usually a namespace trap) and document the fix in `critical_warnings`.

#### 3.5.5 Query Design Hierarchy and Gate Check

Prefer earlier approaches over later ones:

| Rank | Approach             | When to use                              |
|------|----------------------|------------------------------------------|
| 1    | Specific IRIs        | Always when available                    |
| 2    | `VALUES` with IRIs   | Multiple known concepts                  |
| 3    | Typed predicates     | Controlled-vocabulary literals           |
| 4    | Graph navigation     | Hierarchical queries                     |
| 5    | `bif:contains`       | Unstructured text, Virtuoso backend      |
| 6    | `FILTER(CONTAINS())` | Last resort                              |

**Gate Check — before using `bif:contains` or `FILTER(CONTAINS())`:**

- Read the full `shape_expressions` section.
- Check for specific IRIs (ontology, taxonomy, classification codes).
- Check for typed predicates with controlled vocabularies.
- Check for hierarchical relationships.
- Use any available search API to find and DESCRIBE example entities.
- State in one sentence why no structured alternative exists.

If the sentence cannot be written, the structured alternative exists. Keep looking.

**Never use text search for:** organisms (use taxonomy IRIs), ontology terms (GO/MeSH/ChEBI IRIs), EC numbers, drug classifications (ATC IRIs), or any field with a controlled vocabulary.

**Legitimate text-search targets:** `rdfs:comment` on genes/proteins, abstract text, synthesis notes, experimental remarks — fields that are paragraph prose with no codes.

#### 3.5.6 Complexity Guidelines

- **basic**: single entity type, direct IRI lookup or typed predicate, minimal filtering.
- **intermediate**: multiple entity types or joins, `OPTIONAL` patterns, aggregation, graph navigation, indirect value access (measurement scaffolds).
- **advanced**: multi-type queries with nested patterns, complex filtering, analytical aggregations, cross-graph joins within a single endpoint.

#### 3.5.7 Using `bif:contains` on Virtuoso

If `access.backend: "Virtuoso"`, prefer `bif:contains` over `FILTER(CONTAINS())`:

```sparql
?text bif:contains "'term1' OR 'term2'"
```

**Split property paths before `bif:contains`.** The variable must be bound to a plain string literal at the point `bif:contains` sees it:

```sparql
# WRONG — property path breaks indexing
?entity ex:path/ex:label ?text .
?text bif:contains "'keyword'"

# CORRECT — bind intermediate explicitly
?entity ex:path ?intermediate .
?intermediate ex:label ?text .
?text bif:contains "'keyword'"
```

`bif:contains` syntax uses single quotes for inner terms inside a double-quoted SPARQL literal. Supports `AND`, `OR`, `NOT`, prefix matching with `*`.

**Do not use `?score` as a variable name** in `option (score ?var)` — it collides with Virtuoso internals. Use `?sc` or similar.

### 3.6 cross_database_queries

#### 3.6.1 Applicability

Present in all MIE files. If the database is on an isolated endpoint (no co-located databases), use `examples: []` with an explanatory `notes` block rather than omitting the section.

#### 3.6.2 Purpose

Documents cross-database integration queries that leverage shared SPARQL endpoints.

#### 3.6.3 Structure

```yaml
cross_database_queries:
  shared_endpoint: string          # e.g., ebi, sib, primary, ncbi
  co_located_databases:
    - database1
    - database2
  examples:                        # 1-2 examples (not 3) OR []
    - title: string
      description: |
        Linking strategy with specific mechanism
      databases_used:
        - database1
        - database2
      complexity: intermediate     # or advanced
      sparql: |
        Tested query with GRAPH clauses
      notes: |
        - Linking via: [IRI type]
        - MIE files checked: [list]
        - Performance: [timing]
```

#### 3.6.4 Requirements — Reference Co-Located MIE Files

Before writing any cross-database query, **read the MIE files of every other database involved** (from `togo_mcp/data/mie/<db>.yaml`). Extract from each:

- Graph URIs from `schema_info.graphs`
- `PREFIX` definitions from `shape_expressions`
- Entity type URIs from `shape_expressions`
- Linking properties from `cross_references`
- Anti-patterns from `anti_patterns`

Document which MIE files were consulted in the `notes` field.

**Why this matters:** cross-database queries silently fail when graph URIs are wrong, entity types are misspelled, or linking predicates assume the wrong namespace. Reading the MIE files eliminates this class of failure.

#### 3.6.5 Best Practices

1. Use explicit `GRAPH` clauses for each database.
2. Start with small `LIMIT` values — cross-database queries are slower.
3. Filter within each `GRAPH` block before joining, not after.
4. Prefer structured linking predicates (shared IRI namespaces: EC numbers, taxonomy, ChEBI, UniProt, GO) over text-based matching.
5. Validate that the linking predicate actually populates the IRIs you expect — not every `rdfs:seeAlso` points where you'd assume.

#### 3.6.6 Isolated-Endpoint Form

```yaml
cross_database_queries:
  shared_endpoint: null
  co_located_databases: []
  examples: []
  notes: |
    [DATABASE] is the only database on this endpoint. Cross-database SPARQL
    is not possible. To link externally: [describe manual bridging strategies,
    e.g. using shared identifiers with federated queries or client-side joins].
```

#### 3.6.7 Common Link Patterns by Endpoint

**EBI endpoint** (chembl, chebi, reactome, ensembl, amrportal):
- ChEMBL ↔ ChEBI: `skos:exactMatch`
- ChEMBL target ↔ UniProt: shared UniProt accessions
- Reactome ↔ UniProt/Ensembl: shared gene/protein identifiers

**SIB endpoint** (uniprot, rhea):
- UniProt ↔ Rhea: enzyme-catalysed reactions via EC numbers and Rhea IRIs

**Primary endpoint** (mesh, go, taxonomy, mondo, nando, bacdive, mediadive):
- MONDO ↔ MeSH: disease concept cross-references
- BacDive ↔ MediaDive: strain-to-medium relationships
- GO terms ↔ Taxonomy: annotation distribution

**NCBI endpoint** (clinvar, pubmed, pubtator, ncbigene, medgen):
- ClinVar ↔ NCBI Gene: variant-to-gene
- PubMed ↔ PubTator: article-to-entity annotations

### 3.7 cross_references

#### 3.7.1 Purpose

Documents external database linkages, organised by RDF pattern rather than by database.

#### 3.7.2 Structure

```yaml
cross_references:
  - pattern: string                # e.g., rdfs:seeAlso, skos:exactMatch
    description: |
      How links work
    databases:
      category_name:
        - "Database name: coverage percentage"
    sparql: |                      # optional
      Representative query
```

#### 3.7.3 Requirements

- Groups by RDF pattern, not by database.
- Lists all external databases found in the data.
- Includes coverage percentages from real COUNT queries (see §3.7.4) where measurable.
- `sparql` is optional — include only for non-trivial patterns where the naive query doesn't work.

#### 3.7.4 Verification

- The IRI form documented for each pattern must be **confirmed by DESCRIBEing a real entity** (Phase 5g), not inferred from documentation. If two IRI forms exist for the same concept (e.g. `identifiers.org` form and a canonical purl), document both and specify which is the correct join key for cross-database federation.
- Every coverage percentage must come from a **COUNT query** (Phase 5g), not an estimate.

### 3.8 architectural_notes

#### 3.8.1 Structure

```yaml
architectural_notes:
  query_strategy:
    - bullet                       # priority order for new queries
  schema_design:
    - bullet                       # central entity types, controlled vocabularies
  performance:
    - bullet                       # mandatory filters, bif:contains tips
  data_integration:
    - bullet                       # cross-reference patterns, linking predicates
  data_quality:
    - bullet                       # anomalies, duplicates, entry artefacts
  text_search_justification:
    - bullet                       # count of text-search queries, fields where legitimate
```

#### 3.8.2 Requirements

- All six subsections are present, each with at least one bullet.
- Bullets are concise (1–2 sentences).
- `text_search_justification` states how many of the 7 example queries use text search, which fields it's applied to, and why no structured alternative exists for each. If none of the 7 use text search, state that explicitly.

### 3.9 data_statistics

#### 3.9.1 Purpose

Verified counts and coverage percentages. Every number has a verification date and method.

#### 3.9.2 Structure

```yaml
data_statistics:
  total_entities: integer
  verified_date: date              # ISO 8601
  verification_method: string      # "Direct COUNT query" or "sampling with N=..."
  by_class:                        # OPTIONAL but recommended for multi-class databases
    SomeClass: integer             # COUNT of subjects of that type
    AnotherClass: integer
    verified_date: date
  coverage:
    property_name: "XX%"
    calculation: "[numerator / denominator]"
    verified_date: date
```

Additional `total_*` fields for major entity types are encouraged.

#### 3.9.3 Arithmetic Cross-Check (Phase 5c)

After verifying individual counts, cross-check the figures against each other:

- Does `total_entities` equal (or plausibly approximate) the sum of the major `by_class` counts? Document the relationship if it isn't a clean sum (e.g. shared bnodes, multi-typed entities).
- Does each coverage percentage equal `(subset / class)` to within rounding? E.g. 673,263 / 1,021,677 = 65.9%, not loosely "~66%" or "~70%".

Flag and correct any discrepancy before publishing.

#### 3.9.4 Explicitly Omitted

These sub-sections are auditing clutter and are NOT included:

- `verification_queries` — not useful at query time.
- `cardinality` (avg-X-per-entity) — rarely informative for query authors.
- `performance_characteristics` — belongs in `architectural_notes.performance` instead.

#### 3.9.5 Constraints

- All statistics are based on actual queries run against the endpoint.
- Omit rather than guess — if a number can't be verified, leave it out.

### 3.10 anti_patterns

#### 3.10.1 Purpose

Documents common mistakes with corrected versions. Trains the reader to avoid traps before they fall into them.

#### 3.10.2 Structure

```yaml
anti_patterns:
  - title: string
    problem: string                # 1 sentence
    wrong_sparql: |
      Bad query
    correct_sparql: |
      Fixed query
    explanation: |
      Why wrong version fails, why correct version works
```

#### 3.10.3 Requirements

- **Exactly 3–4 entries.**
- **At least one entry addresses "schema check before text search"** — this is the single most common failure mode.
- Other entries cover database-specific traps discovered during schema exploration, or universal SPARQL anti-patterns (circular reasoning with `VALUES`, unindexed text search, etc.).
- Both `wrong_sparql` and `correct_sparql` are minimal working examples.

#### 3.10.4 Verification

Every `correct_sparql` block must be tested against the live endpoint in Phase 5b. Downstream LLMs copy `correct_sparql` as readily as the example queries — an untested `correct_sparql` actively teaches bad practice.

#### 3.10.5 Mandatory Anti-pattern Topics

At least one of the 3–4 entries must cover each topic area:

1. **Text search when a structured property exists** — using `bif:contains` for a field that has a controlled-vocabulary predicate.
2. **Skipping the schema check** — using text search without first reading `shape_expressions`.
3. **Circular reasoning with search results** — using `VALUES { search_results }` and then `COUNT`ing them.
4. **Unindexed text search when indexed is available** — `FILTER(CONTAINS())` when `bif:contains` works (Virtuoso backend).

Topics 1 and 2 overlap enough that a single entry can cover both.

### 3.11 common_errors

#### 3.11.1 Structure

```yaml
common_errors:
  - error: string                  # symptom or error message
    causes:
      - cause
    solutions:
      - solution
```

#### 3.11.2 Requirements

- **Exactly 2–3 scenarios.**
- Each has at least one cause and one solution.
- Focus on errors actually encountered during MIE creation and testing.
- Good picks: timeout / slow query, empty or incomplete results, cross-database query failure.

## 4. Discovery Workflow

### 4.1 File-based Resources

MIE authoring in this project is filesystem-based. The relevant directories are:

| Resource                   | Path                                     | Access                |
|----------------------------|------------------------------------------|-----------------------|
| Existing MIE files         | `./togo_mcp/data/mie/<db>.yaml`          | Read / Write / Edit   |

The MCP tools `get_MIE_file` and `save_MIE_file` (documented in earlier versions of this spec) are **not** used when authoring MIE files in this repository — these files are read and written directly. The remaining TogoMCP tools (`run_sparql`, `list_databases`, `get_sparql_endpoints`, `get_graph_list`, the search APIs) hit live endpoints and are still used as before.

### 4.2 Phase 1 — Orient (2–3 minutes)

Before touching the endpoint:

1. Read `./togo_mcp/data/mie/<db>.yaml` — is there an existing MIE? If yes, this is an update, not a fresh build. Note which sections need improvement.
2. Call `get_sparql_endpoints()` and `get_graph_list(<db>)` — confirm endpoint URL, named graphs, which graphs hold data vs ontology.

### 4.3 Phase 2 — Discover (10–20 minutes)

The goal is to extract the specific IRIs, typed predicates, and namespace patterns needed so that `sparql_query_examples` can prefer structured lookups, and to record everything the shape audit (Phase 5e) and warning audit (Phase 5f) will later check.

**4.3.1 Class enumeration:**

```sparql
SELECT DISTINCT ?class (COUNT(?instance) AS ?count)
WHERE { GRAPH <…> { ?instance a ?class } }
GROUP BY ?class ORDER BY DESC(?count) LIMIT 50
```

**4.3.2 Per-class predicate survey — run for every class going into `shape_expressions`:**

```sparql
SELECT ?p (COUNT(*) AS ?n)
WHERE { GRAPH <…> { ?s a <TargetClass> ; ?p ?o } }
GROUP BY ?p ORDER BY DESC(?n) LIMIT 50
```

Annotation classes, measurement classes, and cross-reference classes are just as likely to have missing or misnamed predicates as the central entity class. A predicate absent from the survey has no business in the shape; a predicate with COUNT > 0 must be either documented or explicitly excluded with a note.

**While running the survey, flag `critical_warnings` candidates:**

- COUNT equals class instance count but the predicate name has an alias or alternate namespace — confirm only one form is queryable.
- COUNT is much lower than the class instance count for a predicate that looks mandatory — document as a cardinality caveat or as a trap if omitting it causes a silent wrong result.
- COUNT is greater than the class instance count for a predicate that looks singular — document the multi-valued behaviour.
- Two predicates return overlapping results for what appears to be the same concept — document which form is the correct join key.

`critical_warnings` is assembled in Phase 4 from this list, not reconstructed from memory.

**4.3.3 Representative-entity DESCRIBE:**

```sparql
DESCRIBE <iri-of-example-entity>
# or, when DESCRIBE is unhelpful:
SELECT ?p ?o WHERE { GRAPH <…> { <iri-of-example-entity> ?p ?o } } LIMIT 200
```

**Live DESCRIBE is the canonical source for shapes.** Pick 3–5 entities that span the database's taxonomy (e.g. a reviewed protein AND an unreviewed one; a drug molecule AND a target AND an assay) and DESCRIBE each.

Biological intuition matters: if exploring a drug database, look for measurement scaffolds (blank-node activity records); if it's a sequence database, look for feature annotations and organism links; if it's an ontology, look for `rdfs:subClassOf`, `owl:equivalentClass`, and `skos:broader`.

**4.3.4 Bnode tracing — for every bnode-valued predicate found in 4.3.3:**

```sparql
SELECT DISTINCT ?bPred ?bObj WHERE {
  GRAPH <…> {
    ?parent a <ParentClass> ; <bnodePredicate> ?bnode .
    ?bnode ?bPred ?bObj .
  }
} LIMIT 50
```

The same predicate name can resolve to differently-shaped bnodes on different parent classes. Trace each parent independently — never assume two bnode chains with the same predicate name share an internal structure. Each bnode that participates in a shape needs its own `<…BNode>` shape definition.

**4.3.5 Cardinality verification — for every class–predicate pair going into `shape_expressions`:**

```sparql
SELECT ?nValues (COUNT(?s) AS ?nSubjects) WHERE {
  GRAPH <…> {
    { SELECT ?s (COUNT(?o) AS ?nValues) WHERE {
        ?s a <TargetClass> ; <TargetPredicate> ?o .
      } GROUP BY ?s }
  }
}
GROUP BY ?nValues ORDER BY ?nValues
```

Map the result to the correct ShEx cardinality modifier:

| Observed pattern                       | ShEx notation                       |
|----------------------------------------|-------------------------------------|
| All subjects, exactly 1 value          | `IRI` (no modifier — required)      |
| Some subjects have 0, none have > 1    | `IRI ?`                             |
| Some subjects have > 1                 | `IRI *` (if 0 is possible) or `IRI +` |

**Never assign `?`, `+`, or `*` based on intuition.** Every modifier must be justified by a cardinality query result.

**4.3.6 Search-tool anchoring** — when a database has a dedicated search tool (`search_uniprot_entity`, `search_chembl_molecule`, etc.), use it to turn keywords into example IRIs that can then be DESCRIBED. This is the fastest path from "I know what concept I'm looking for" to "I have a structured-IRI query that works".

### 4.4 Phase 3 — Design the query set

Design the 7 example queries following the hierarchy in section 3.5.5. Before writing any query that uses text search, complete the Gate Check. If you find yourself reaching for `bif:contains` more than once across the 7, stop and re-read `shape_expressions` — almost every field that looks "free text" in an RDF database is backed by a controlled vocabulary somewhere.

### 4.5 Phase 4 — Write the file

Use section 13 (Appendix A) as the scaffold. Fill every `[bracketed]` placeholder. Remove scaffolding comments before finalising.

### 4.6 Phase 5 — Validate (non-negotiable)

**This phase is where most MIE files go wrong.** Do not skip it.

**5a. Validate every RDF example.** For each of the 3 entries in `sample_rdf_entries`, run a SELECT or ASK that retrieves those exact triples from the endpoint. Fix any that fail; replace any that can't be fixed. No fabricated RDF reaches the final file.

**5b. Test every SPARQL query — all of them.** Run all 7 of `sparql_query_examples`, every example in `cross_database_queries`, every `correct_sparql` block in `anti_patterns`, and any SPARQL embedded in `cross_references`. "Most of them" is not sufficient. Untested `correct_sparql` blocks actively teach bad practice — downstream LLMs copy them as readily as the example queries.

Queries that time out, error, or return 0 rows when they shouldn't, must be fixed or replaced before the file is written.

For each cross-database query that returns results, additionally **spot-check join validity**: take one join value from the result set and run a quick `ASK` or `SELECT` against the second database to confirm it resolves to a real entity there. A query returning 3 rows when thousands are expected is a join failure, not a passing test — the IRI form used for linking likely differs between the two databases.

**5c. Verify statistics.** Every count or coverage percentage in `data_statistics` comes from a real query with a `verified_date`. Omit rather than guess.

After verifying individual counts, **cross-check arithmetic consistency**: `total_entities` should equal (or plausibly approximate) the sum of major `by_class` counts, and each coverage % must equal `(subset / class)` to within rounding (see §3.9.3).

**5d. Validate the YAML.** Load with PyYAML to confirm it parses:

```bash
python3 -c "import yaml; yaml.safe_load(open('./togo_mcp/data/mie/<db>.yaml'))"
```

**5e. Audit `shape_expressions`.** For each shape block:

1. Re-run the §4.3.2 per-class predicate survey and compare against the documented predicates. Any predicate with COUNT > 0 absent from the shape must be added or explicitly noted as intentionally excluded.
2. Confirm every `@<ShapeRef>` has a defined `<…Shape>` block (§3.3.5).
3. For every predicate marked `?` (optional), confirm with a §4.3.5 cardinality query that at least one subject has 0 values. For every predicate with no modifier (required), confirm its COUNT equals the class instance count.

`shape_expressions` is the section a downstream LLM relies on most heavily for query construction. An unaudited shape is equivalent to an untested SPARQL example.

**5f. Verify `critical_warnings` content.** For every predicate name and IRI string cited, run a minimal query confirming it exists in the endpoint:

```sparql
SELECT ?s WHERE {
  GRAPH <…> { ?s <cited-predicate> ?o }
} LIMIT 1
```

If the query returns no rows, the cited predicate or IRI is wrong — fix it before publishing. Also confirm each warning is still accurate against the current data snapshot: a trap documented in a previous MIE version may have been corrected upstream.

**5g. Verify `cross_references`.** For each cross-reference predicate documented:

1. Confirm the IRI form by DESCRIBEing a real entity and reading the actual object value. If two IRI forms are present (e.g. an `identifiers.org` form and a canonical purl), document both and specify which is the correct join key for federation.
2. Verify the coverage percentage with a COUNT query:

   ```sparql
   SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {
     GRAPH <…> { ?s a <EntityClass> ; <crossRefPredicate> ?o }
   }
   ```

   Divide by the class instance count from `data_statistics`. Document the result as the coverage figure — do not estimate.

**5h. Verify prefix declarations.** For each non-standard prefix defined in `shape_expressions` or `sample_rdf_entries`, confirm the base URI is correct by running a minimal SELECT using that prefix:

```sparql
PREFIX ex: <http://suspected-base-uri/>
SELECT ?s WHERE {
  GRAPH <…> { ?s a ex:KnownClass }
} LIMIT 1
```

If the query returns no rows despite the class being known to exist, the prefix base URI is wrong. Standard W3C prefixes (`rdf:`, `rdfs:`, `owl:`, `xsd:`) do not need checking. Database-specific and ontology-specific prefixes (Unimod, PSI-MS, internal-ontology, etc.) must all be confirmed.

### 4.7 Anti-bias rules

- Do not rely solely on the first 50 results of any query — sample patterns across the database.
- Do not treat timeouts as "data doesn't exist" — reformulate and try a smaller slice.
- Do not skip ontology graph exploration.
- Do not assume older curated examples are still valid — test them against the current endpoint.

## 5. YAML Formatting Rules

### 5.1 Mandatory Pipe Syntax

All multiline string values use the pipe (`|`) syntax:

```yaml
# CORRECT
description: |
  First line.
  Second line.

sparql: |
  SELECT ?s ?p ?o
  WHERE { ?s ?p ?o . }
  LIMIT 10

# WRONG — don't use quoted strings for multiline content
description: "First line.\nSecond line."
```

### 5.2 Where to Use

`description`, `sparql`, `rdf`, `shape_expressions`, `explanation` in anti-patterns, `notes` in cross_database_queries, `critical_warnings`, any value that spans multiple lines.

### 5.3 Benefits

Better readability; preserves formatting and indentation; easier to edit SPARQL; consistent style across the corpus.

## 6. Compliance Checking

### 6.1 Existing MIE File Evaluation

When updating an existing MIE, evaluate against the following checklist and pick a strategy.

#### Structure & Format
- [ ] Valid YAML
- [ ] All 11 required sections present in order
- [ ] `schema_info` includes `backend`, `kw_search_tools`, `keywords`, `categories`
- [ ] Multiline strings use pipe syntax

#### Content Counts
- [ ] `sample_rdf_entries`: exactly 3 entries with shared `rdf_prefixes` block
- [ ] `sparql_query_examples`: exactly 7 queries (2/3/2)
- [ ] `anti_patterns`: 3–4 entries
- [ ] `common_errors`: 2–3 entries

#### Query Strategy
- [ ] At least 2 queries use specific IRIs / `VALUES` with IRIs
- [ ] At least 2 queries use typed predicates or graph navigation
- [ ] At most 1 query uses text search, with justification
- [ ] Every query has a bounded result set (`LIMIT`, aggregate, `ASK`, or specific-IRI subject — see §3.5.3)

#### Validation
- [ ] All 3 RDF example entries validated against endpoint (§4.6 5a)
- [ ] All 7 SPARQL queries tested against endpoint (§4.6 5b)
- [ ] Every `anti_patterns.correct_sparql` block tested (§4.6 5b)
- [ ] All cross-database queries tested + join validity spot-checked (§4.6 5b)
- [ ] All statistics have `verified_date` and pass arithmetic cross-check (§4.6 5c)
- [ ] `shape_expressions` audited (§4.6 5e)
- [ ] `critical_warnings` cited predicates / IRIs verified (§4.6 5f)
- [ ] `cross_references` IRI forms confirmed by DESCRIBE; coverage % from COUNT (§4.6 5g)
- [ ] Non-standard PREFIX base URIs verified with SELECT (§4.6 5h)
- [ ] `schema_info.categories` exact-matched against `list_categories()` (§3.1.4)

#### Critical Warnings
- [ ] Present with at least one entry (or verified `[]`)
- [ ] Documents mandatory performance filters, IRI traps, required typos
- [ ] Trap candidates flagged from §4.3.2 surprising-COUNT signals during discovery (not reconstructed from memory)

#### Threshold
- **≥ 90% pass**: update existing file.
- **< 90% pass**: rewrite from scratch.

## 7. Quality Assurance

### 7.1 Pre-finalisation Checklist

#### Discovery
- [ ] Read existing `togo_mcp/data/mie/<db>.yaml` (if present)
- [ ] Ran per-class predicate survey for every class going into `shape_expressions` (§4.3.2)
- [ ] Ran parent-anchored bnode-tracing query for every bnode-valued predicate (§4.3.4)
- [ ] Ran cardinality distribution query for every class–predicate pair (§4.3.5)
- [ ] Ran DESCRIBE on representative entities to derive shapes (§4.3.3)
- [ ] Flagged `critical_warnings` candidates from surprising COUNT distributions (§4.3.2)
- [ ] Identified co-located databases on shared endpoint
- [ ] Read MIE files for all co-located databases (if cross-database queries planned)

#### Structure
- [ ] Valid YAML, 11 sections in order
- [ ] `schema_info` complete with backend, kw_search_tools, keywords (8-15), categories (1-3)
- [ ] `schema_info.categories` exact-matched against `list_categories()`
- [ ] `critical_warnings` documents silent-failure traps (or verified `[]`)
- [ ] ShEx covers all major entity types with inline counts
- [ ] Every `@<ShapeRef>` resolves to a defined block in the same section (§3.3.5)
- [ ] Optional co-types written as separate `a [ T ] ?` lines (§3.3.5)
- [ ] Exactly 3 RDF entries, shared prefix block
- [ ] Exactly 7 SPARQL queries (2/3/2)
- [ ] Cross-database queries present (or `examples: []` with notes)
- [ ] Cross-references organised by pattern
- [ ] `architectural_notes` includes `text_search_justification`
- [ ] All multiline strings use pipe syntax

#### Validation
- [ ] Every RDF triple in `sample_rdf_entries` validated against endpoint (5a)
- [ ] Every SPARQL query in `sparql_query_examples` tested and working (5b)
- [ ] Every `anti_patterns.correct_sparql` block tested (5b)
- [ ] Every cross-database query tested + join validity spot-checked (5b)
- [ ] Every statistic has `verified_date`; arithmetic cross-check passes (5c)
- [ ] YAML parses cleanly (5d)
- [ ] `shape_expressions` audited — predicate surveys re-run, `@<ShapeRef>`s resolved, cardinalities confirmed (5e)
- [ ] Every `critical_warnings` predicate / IRI verified against endpoint (5f)
- [ ] Every `cross_references` IRI form confirmed by DESCRIBE; coverage % from COUNT (5g)
- [ ] Every non-standard PREFIX base URI confirmed with SELECT (5h)

### 7.2 Content Standards

- Descriptions are actionable and query-focused.
- No redundant information.
- All examples use real data from the database.
- Documentation enables effective querying by a downstream LLM.
- Cross-database queries show practical value, not forced integration.

## 8. Best Practices

### 8.1 Writing Style

- **Concise**: if it doesn't help write a better query, omit it.
- **Clear**: direct language; no throat-clearing.
- **Complete**: cover all entity types and access patterns.
- **Correct**: every triple and every query validated.
- **Consistent**: pipe syntax throughout.

### 8.2 SPARQL Queries

- Always include `LIMIT`.
- Prefer structured lookups (IRIs, typed predicates) over text search.
- Comment non-obvious choices (why this predicate, why this filter).
- For Virtuoso, use `bif:contains`; split property paths before it.
- For cross-database, use explicit `GRAPH` clauses and filter before joining.

### 8.3 Coverage

- Document all entity types, not just the obvious ones.
- Include rare but important patterns (measurement scaffolds, reified statements).
- Document IRI namespace traps and required-typo predicates in `critical_warnings`.
- Note cross-database opportunities where the endpoint is shared.

## 9. Common Pitfalls

### 9.1 Discovery Phase

- ❌ Sampling bias: first 50 results don't represent the whole database.
- ❌ Premature conclusions: timeout ≠ "data doesn't exist".
- ❌ Incomplete coverage: only documenting obvious entity types.

### 9.2 Documentation Phase

- ❌ Fabricated RDF examples (the single worst failure mode).
- ❌ Untested SPARQL queries ("it looks right" is not a test).
- ❌ Cross-database queries in the regular `sparql_query_examples` section.
- ❌ Text search when a structured predicate exists.
- ❌ Prose paragraphs in `architectural_notes`.
- ❌ Missing `kw_search_tools`, `backend`, or `critical_warnings`.
- ❌ Wrong `rdf_prefixes` layout (repeating prefixes in every entry).

### 9.3 Query Design Phase

- ❌ `VALUES { search-API results }` followed by `COUNT` (circular reasoning).
- ❌ `FILTER(CONTAINS())` on Virtuoso when `bif:contains` is available.
- ❌ Property path immediately before `bif:contains`.
- ❌ Skipping the Gate Check before using text search.
- ❌ Using `?score` as a variable name with Virtuoso `option (score ?var)`.

### 9.4 Validation Phase

- ❌ Testing 3 of 7 queries and calling it done.
- ❌ Assuming sample RDF is correct because it was copied from an example file.
- ❌ Documenting an anti-pattern whose "wrong" version actually works.
- ❌ Cross-database queries untested because the author read the co-database MIE instead of running the query.

## 10. Success Criteria

An MIE file is complete and compliant when:

1. Valid YAML with all 11 required sections in correct order.
2. `critical_warnings` documents silent-failure traps (or is verified `[]`).
3. ShEx covers all major entity types, with inline counts and caveats.
4. Exactly 3 `sample_rdf_entries` with shared `rdf_prefixes` block — **all 3 retrievable from the endpoint**.
5. Exactly 7 SPARQL queries (2/3/2), prioritising structured lookups — **all 7 executed successfully**.
6. `cross_database_queries` present (examples or `[]` with notes).
7. `data_statistics` contains only verified counts/coverage, no auditing subsections.
8. 3–4 anti-patterns including "schema check before text search".
9. 2–3 common errors with causes and solutions.
10. All multiline strings use pipe syntax.
11. Line count 400–600 typical, ≤ 900 for complex databases.

## 11. Version History

| Version | Date       | Changes                                                                                                                                                                                                                                                                                                             |
|---------|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1.0     | 2024       | Initial specification.                                                                                                                                                                                                                                                                                              |
| 1.1     | 2025-01-17 | Added `cross_database_queries` section, `kw_search_tools` field, pipe syntax requirement, `backend` field, MIE file reference guidance.                                                                                                                                                                              |
| 2.0     | 2026-04-22 | New `critical_warnings` section; sample RDF reduced from 5 to 3 with shared prefix block; query-strategy hierarchy and Gate Check formalised; filesystem-based workflow (MIE files, ShEx, SPARQL examples as files); stronger validation — all example triples retrievable, all example queries tested; `data_statistics` simplified; anti-patterns expanded to 3–4 entries with mandatory "schema check before text search" topic. |
| 2.1     | 2026-04-30 | `shape_expressions` discipline: every `@<ShapeRef>` resolves; optional co-types as separate `?` lines. Phase 2 Discover expanded with per-class predicate survey, parent-anchored bnode tracing, cardinality distribution query + modifier-mapping table, and `critical_warnings` candidate flagging. Phase 5 Validate gains 5e (shape audit), 5f (critical_warnings verification), 5g (cross_references IRI/coverage verification), 5h (PREFIX verification); 5b extended to `anti_patterns.correct_sparql` + cross-DB join-validity spot-check; 5c extended with arithmetic cross-check. `schema_info.categories` `list_categories()` exact-match enforcement. `data_statistics.by_class` documented. LIMIT rule relaxed to "bounded result set" (aggregate / ASK / specific-IRI subject also acceptable). |

## 12. References

### 12.1 Related Standards

- **ShEx**: Shape Expressions Language (https://shex.io/)
- **SPARQL**: SPARQL 1.1 Query Language (W3C Recommendation)
- **YAML**: YAML Ain't Markup Language (https://yaml.org/)
- **RDF**: Resource Description Framework (W3C Recommendation)

### 12.2 Tools

**Endpoint access** (TogoMCP tools, still in use):
- `get_sparql_endpoints()` — list SPARQL endpoints and keyword-search APIs
- `get_graph_list(database)` — list named graphs
- `run_sparql(database, query)` — execute SPARQL (single database)
- `run_sparql(endpoint_name=endpoint, query)` — execute SPARQL (cross-database)
- `list_databases()` — list supported databases

**Filesystem access** (standard tools; replaces former `get_MIE_file`/`save_MIE_file`):
- Read / Write / Edit for `togo_mcp/data/mie/<db>.yaml`

### 12.3 Keyword Search APIs

**Dedicated tools:**
- `search_uniprot_entity(query, limit=20)`
- `search_pdb_entity(db, query, limit=20)` — `db ∈ {pdb, cc, prd}`
- `search_chembl_molecule(query, limit=20)`, `search_chembl_target(query, limit=20)`
- `search_reactome_entity(query, species=None, types=None, rows=30)`
- `search_rhea_entity(query, limit=100)`
- `search_mesh_descriptor(query, limit=10)`

**OLS4:**
- `OLS4:searchClasses(query, ontologyId=None, pageSize, pageNum)` — ChEBI, GO, Mondo, NANDO

**NCBI:**
- `ncbi_esearch(database, query, max_results=20)` — PubChem, Taxonomy, ClinVar, PubMed, NCBIGene, MedGen

**SPARQL-only:**
- `run_sparql()` with `bif:contains` (Virtuoso) or `FILTER(CONTAINS())`

## 13. Appendix A: Complete Template

```yaml
schema_info:
  title: [DATABASE_NAME]
  description: |
    [2-3 sentences: contents, main entity types, primary use cases]
  keywords:                        # 8-15 lowercase, include synonyms (see §3.1.5)
    - [keyword1]
    - [keyword2]
  categories:                      # 1-3 from controlled taxonomy (see §3.1.5)
    - [category1]
  endpoint: https://rdfportal.org/example/sparql
  base_uri: http://example.org/
  graphs:
    - http://example.org/dataset
    - http://example.org/ontology
  kw_search_tools:
    - [api_name]                   # or []
  version:
    mie_version: "2.1"
    mie_created: "YYYY-MM-DD"
    mie_updated: "YYYY-MM-DD"      # OPTIONAL — set when revising an existing MIE
    data_version: "Release YYYY.MM"
    update_frequency: "Monthly"
  access:
    backend: "Virtuoso"            # or "Blazegraph", etc.

critical_warnings: |
  - [Silent-failure trap, IRI namespace trap, or mandatory performance filter]
  - [Required-typo predicate, if any]

shape_expressions: |
  PREFIX ex: <http://example.org/>

  <EntityShape> {
    a [ ex:Type ] ;                # ~N instances
    ex:required xsd:string ;
    ex:optional xsd:string ?       # ~X% coverage
  }

sample_rdf_entries:
  rdf_prefixes: |
    @prefix ex: <http://example.org/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  entries:
    - title: "[Representative entity]"
      description: One-sentence purpose.
      rdf: |
        ex:entity1 a ex:Type ;
                   ex:required "value" .
    - title: "[Non-obvious pattern]"
      description: One sentence.
      rdf: |
        ex:entity2 a ex:Type ;
                   ex:optional "value" .
    - title: "[Cross-reference or measurement scaffold]"
      description: One sentence.
      rdf: |
        ex:entity3 a ex:Type ;
                   rdfs:seeAlso <http://external.org/123> .

sparql_query_examples:
  - title: "[Basic — specific IRI]"
    description: |
      Context.
    question: "Question?"
    complexity: basic
    sparql: |
      ...
      LIMIT 20

  - title: "[Basic — typed predicate]"
    description: |
      Context.
    question: "Question?"
    complexity: basic
    sparql: |
      ...
      LIMIT 20

  - title: "[Intermediate #1]"
    description: |
      Context.
    question: "Question?"
    complexity: intermediate
    sparql: |
      ...
      LIMIT 20

  - title: "[Intermediate #2]"
    description: |
      Context.
    question: "Question?"
    complexity: intermediate
    sparql: |
      ...
      LIMIT 20

  - title: "[Intermediate #3]"
    description: |
      Context.
    question: "Question?"
    complexity: intermediate
    sparql: |
      ...
      LIMIT 20

  - title: "[Advanced #1]"
    description: |
      Context.
    question: "Question?"
    complexity: advanced
    sparql: |
      ...
      LIMIT 20

  - title: "[Advanced #2]"
    description: |
      Context.
    question: "Question?"
    complexity: advanced
    sparql: |
      ...
      LIMIT 20

cross_database_queries:
  shared_endpoint: [endpoint_name]         # or null
  co_located_databases:
    - [database1]
    - [database2]
  examples:                                # 1-2 examples, or []
    - title: "[Structured cross-database link]"
      description: |
        Linking strategy:
        - db1: predicate X links to shared IRI namespace
        - db2: predicate Y links to same IRI namespace
        - Direct IRI matching; no text search required
      databases_used:
        - [database1]
        - [database2]
      complexity: intermediate
      sparql: |
        PREFIX db1: <http://db1.org/>
        PREFIX db2: <http://db2.org/>

        SELECT ?entity1 ?entity2 ?sharedIRI
        WHERE {
          GRAPH <db1_graph> { ?entity1 db1:hasIdentifier ?sharedIRI . }
          GRAPH <db2_graph> { ?entity2 db2:linkedTo ?sharedIRI . }
        }
        LIMIT 20
      notes: |
        - Linking via: [IRI type, e.g. EC numbers]
        - MIE files checked: [database1, database2]
        - Performance: [timing]

# Isolated-endpoint form:
# cross_database_queries:
#   shared_endpoint: null
#   co_located_databases: []
#   examples: []
#   notes: |
#     [DATABASE] is the only database on this endpoint. Cross-database SPARQL
#     is not possible. To link externally: [manual bridging strategies].

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      [How this cross-reference pattern links to external resources]
    databases:
      category:
        - "Database name: coverage percentage"

architectural_notes:
  query_strategy:
    - "Read the MIE file first; examine shape_expressions and critical_warnings"
    - "Use specific IRIs and typed predicates before text search"
    - "On Virtuoso: bif:contains > FILTER(CONTAINS()); split property paths"
    - "Priority: Specific IRIs > Typed predicates > Graph navigation > Text search"
  schema_design:
    - "[Central entity types and relationships]"
    - "[Key controlled vocabularies and their predicates]"
    - "[IRI patterns and namespace gotchas]"
  performance:
    - "[Mandatory filters]"
    - "[Key optimisations]"
    - "[bif:contains pitfalls on Virtuoso]"
  data_integration:
    - "[Cross-reference patterns and coverage]"
    - "[Linking predicates to external databases]"
  data_quality:
    - "[Known anomalies or data entry artefacts]"
  text_search_justification:
    - "Number of example queries using text search: N"
    - "Fields where text search is legitimate: [list]"
    - "Reason structured alternatives confirmed absent: [per field]"

data_statistics:
  total_entities: [count]
  verified_date: "YYYY-MM-DD"
  verification_method: "Direct COUNT query"
  by_class:                        # OPTIONAL but recommended for multi-class databases
    [Class]: [count]
    [AnotherClass]: [count]
    verified_date: "YYYY-MM-DD"
  coverage:
    key_property: "XX%"
    calculation: "[numerator / denominator]"
    verified_date: "YYYY-MM-DD"

anti_patterns:
  - title: "Text search when a structured property exists"
    problem: "Using string matching when a specific IRI or typed predicate is available."
    wrong_sparql: |
      ?description bif:contains "'antibacterial'"
    correct_sparql: |
      ?molecule cco:atcClassification <http://www.whocc.no/atc/J01> .
    explanation: |
      Controlled vocabularies exist so you don't have to guess spellings.
      The IRI is canonical; the text is not.

  - title: "Skipping schema check before text search"
    problem: "Reaching for bif:contains without reading shape_expressions."
    wrong_sparql: |
      ?text bif:contains "'kinase'"
    correct_sparql: |
      # 1. Read shape_expressions → look for structured predicate
      # 2. search_chembl_target('kinase') → extract concept IRIs
      # 3. Use the IRIs:
      VALUES ?term {
        <http://purl.obolibrary.org/obo/GO_0016301>
        <http://purl.obolibrary.org/obo/GO_0004672>
      }
      ?entity cco:hasGoTerm ?term .
    explanation: |
      RDF databases are curated. If you think you need free-text search,
      you're almost always missing a predicate.

  - title: "Circular reasoning with search results"
    problem: "Using search API results in VALUES and then counting them."
    wrong_sparql: |
      VALUES ?entity { ex:1 ex:2 ... ex:20 }   # 20 results from search
      SELECT (COUNT(?entity) AS ?count) WHERE { ... }
    correct_sparql: |
      VALUES ?classification { <term:A> <term:B> }
      SELECT (COUNT(DISTINCT ?entity) AS ?count)
      WHERE { ?entity hasClassification ?classification . }
    explanation: |
      Search APIs help you discover concept IRIs. Use those IRIs to query
      the full dataset — don't count the filtered search results.

  - title: "Unindexed text search when indexed is available"
    problem: "FILTER(CONTAINS()) on a Virtuoso backend where bif:contains works."
    wrong_sparql: |
      FILTER(CONTAINS(LCASE(?text), "keyword"))
    correct_sparql: |
      ?text bif:contains "'keyword'"
    explanation: |
      bif:contains uses Virtuoso's inverted index. FILTER(CONTAINS()) does
      a full scan and times out on large graphs.

common_errors:
  - error: "Slow query / timeout"
    causes:
      - "Text search used where structured IRIs or predicates are available"
      - "Missing critical filters (reviewed status, graph clause)"
      - "FILTER(CONTAINS()) used when bif:contains is available"
      - "Property path used just before bif:contains"
    solutions:
      - "Check critical_warnings and shape_expressions for mandatory filters"
      - "Replace text search with structured lookups"
      - "Use bif:contains on Virtuoso; split property paths before it"
      - "Add LIMIT to every query"

  - error: "Empty or incomplete results"
    causes:
      - "Used VALUES with search results instead of concept IRIs (circular reasoning)"
      - "Wrong IRI namespace (silent failure — returns 0 rows, no error)"
      - "Missing hierarchical navigation"
    solutions:
      - "Read critical_warnings for known namespace traps"
      - "DESCRIBE an example entity to confirm IRI patterns"
      - "Use rdfs:subClassOf+ / skos:broader+ for hierarchical coverage"

  - error: "Cross-database query timeout or empty results"
    causes:
      - "Did not read MIE files for all databases in the query"
      - "Missing GRAPH clauses"
      - "Joining before filtering"
    solutions:
      - "Read MIE files for all databases; confirm linking predicates"
      - "Use explicit GRAPH clauses for each database"
      - "Apply restrictive filters within each GRAPH block before joining"
```

## 14. Appendix B: Validation Rules

### 14.1 Structural

1. File is valid YAML.
2. All 11 required sections present, in specified order.
3. All required fields populated.
4. All multiline strings use pipe (`|`) syntax.

### 14.2 Content Counts

1. `sample_rdf_entries.entries`: exactly 3.
2. `sparql_query_examples`: exactly 7.
3. SPARQL complexity distribution: 2 basic / 3 intermediate / 2 advanced.
4. `cross_database_queries.examples`: 1–2 if shared endpoint, `[]` with notes if isolated.
5. `anti_patterns`: 3–4 entries including "schema check before text search".
6. `common_errors`: 2–3 entries.

### 14.3 Query Strategy

1. ≥ 2 queries use specific IRIs or `VALUES` with IRIs.
2. ≥ 2 queries use typed predicates or graph navigation.
3. ≤ 1 query uses text search, with inline justification.
4. Every query has a bounded result set (explicit `LIMIT`, aggregate, `ASK`, or specific-IRI subject).

### 14.4 Validation Evidence

1. Every RDF triple in `sample_rdf_entries` retrievable from endpoint (ASK or SELECT).
2. Every SPARQL query in `sparql_query_examples` executes successfully against endpoint.
3. Every query in `cross_database_queries.examples` executes successfully + one join value spot-checked in the second database.
4. Every `correct_sparql` block in `anti_patterns` executes successfully.
5. Every statistic in `data_statistics` has a `verified_date` from an actual query; `total_entities` and coverage % pass arithmetic cross-check.
6. `shape_expressions` audit: every documented predicate present in §4.3.2 survey output; every `@<ShapeRef>` resolves; every cardinality modifier confirmed by §4.3.5.
7. Every predicate / IRI cited in `critical_warnings` confirmed to exist in the endpoint.
8. Every `cross_references` IRI form confirmed by DESCRIBE; every coverage % from a COUNT query.
9. Every non-standard PREFIX base URI confirmed with a SELECT against a known class.
10. `schema_info.categories` tokens confirmed exact-match against `list_categories()`.

### 14.5 Format

1. All dates in ISO 8601 (`YYYY-MM-DD`).
2. All URIs valid.
3. `kw_search_tools` present (may be `[]`).
4. `access.backend` present.
5. `critical_warnings` present (may be `[]` if verified).

### 14.6 Reference Validation (cross-database queries)

1. Co-located database MIE files read before writing query.
2. Graph URIs match those in referenced MIE files.
3. Entity types match those in referenced `shape_expressions`.
4. `notes` field documents which MIE files were consulted.

---

**Document Status**: Specification v2.1
**Compliance**: required for all MIE files in `togo_mcp/data/mie/`
**Principle**: Compact · Complete · Correct · Actionable · Validated
**Core shift in v2.1**: Pre-publication audit pass — `shape_expressions` discipline (every `@<ShapeRef>` resolves; optional co-types explicit); discovery-time signals for `critical_warnings`; section-by-section verification (5e–5h) before publishing.
**Core shift in v2.0**: Filesystem-based workflow; structured lookups over text search; every example validated against the live endpoint.
