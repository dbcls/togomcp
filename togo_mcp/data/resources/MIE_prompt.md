# Create a Compact Yet Comprehensive MIE (Metadata Interoperability Exchange) File for an RDF Database
**Target Database: __DBNAME__**

---

## Two Hard Rules for MIE Generation

**1. No scripting or filesystem tools.**
Never use Bash, Write, Edit, Read, or any filesystem/scripting tool during MIE generation.
All data access must go through TogoMCP tools (`run_sparql`, `get_MIE_file`, search APIs, etc.).

**2. No blind SPARQL retry loops.**
Schema discovery legitimately requires many queries, but if a query fails twice in a row,
stop and diagnose — wrong predicate, wrong graph, wrong IRI pattern — before retrying.
More retries without diagnosis do not fix a structurally wrong query.

---

## Core Philosophy

**Conciseness:** 400–600 lines typical, 700–900 max for complex databases.

**Query Strategy:** Use specific IRIs and structured predicates first. Text search (`bif:contains` or `FILTER(CONTAINS())`) only when no structured alternative exists.

**Quality:** Comprehensive discovery, verified statistics, tested queries, actionable documentation.

---

## Critical Query Strategy (MUST READ)

### Query Design Hierarchy

**1. Specific IRIs (Best — Fast, Stable, Unambiguous)**
```sparql
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .  # Human
?molecule cco:atcClassification <http://www.whocc.no/atc/J01> .  # Antibacterials
?term rdfs:subClassOf <http://purl.obolibrary.org/obo/GO_0006915> .  # Apoptosis
```

**2. VALUES with Multiple IRIs**
```sparql
VALUES ?concept {
  <http://purl.obolibrary.org/obo/GO_0016301>  # kinase activity
  <http://purl.obolibrary.org/obo/GO_0004672>  # protein kinase activity
}
?entity classificationPredicate ?concept .
```

**3. Typed Predicates**
```sparql
?molecule cco:organismName "Homo sapiens" .
?activity cco:standardType "IC50" .
?entity status "approved" .
```

**4. Graph Navigation**
```sparql
?organism rdfs:subClassOf+ ?phylum .
?term skos:broader+ ?parentTerm .
```

**5. `bif:contains` (Virtuoso — Indexed Text Search)**
```sparql
# Use for unstructured text when backend is Virtuoso
?comment bif:contains "'keyword1' AND 'keyword2'"
```

**6. `FILTER(CONTAINS())` (Last Resort — Unindexed)**
```sparql
# Use only when no structured alternative exists AND bif:contains not available
FILTER(CONTAINS(LCASE(?text), "pattern"))
```

### Decision Tree

```
1. Specific IRI for this concept?         YES → Use IRI directly
2. Controlled vocabulary or typed pred?   YES → Use the predicate
3. Graph structure to navigate?           YES → Use rdfs:subClassOf / skos:broader
4. Genuinely unstructured free text?      NO  → Re-examine the schema
5. Virtuoso backend?                      YES → bif:contains   NO → FILTER(CONTAINS())
```

### Performance Comparison

| Approach              | Speed     | When to Use                              |
|-----------------------|-----------|------------------------------------------|
| Specific IRIs         | ★★★★★ | Always prefer when available             |
| VALUES with IRIs      | ★★★★★ | Multiple known concepts                  |
| Typed predicates      | ★★★★☆ | Controlled vocabularies                  |
| Graph navigation      | ★★★☆☆ | Hierarchical queries                     |
| `bif:contains`        | ★★☆☆☆ | Unstructured text (Virtuoso)             |
| `FILTER(CONTAINS())`  | ★☆☆☆☆ | Last resort when nothing else works      |

### Circular Reasoning Trap ⚠️

**WRONG — counts only what you already found:**
```sparql
VALUES ?entity { ex:1 ex:2 ... ex:20 }   # 20 results from search API
SELECT (COUNT(?entity) as ?count) WHERE { ... }
```

**CORRECT — use discovered concept IRIs to query the full dataset:**
```sparql
VALUES ?classificationTerm {
  <http://example.org/classification/TypeA>
  <http://example.org/classification/TypeB>
}
SELECT (COUNT(DISTINCT ?entity) as ?count)
WHERE { ?entity hasClassification ?classificationTerm . }
```

---

## Workflow

### 1. Discovery Phase

**Step 1: Existing Documentation (2 min)**
```python
get_sparql_endpoints()
get_graph_list(database)
get_MIE_file(database)   # check for existing MIE and compliance
```

**Step 2: Schema Discovery (5–10 min)**

First enumerate classes:
```sparql
# Classes and instance counts
SELECT DISTINCT ?class (COUNT(?instance) as ?count)
WHERE { GRAPH <…> { ?instance a ?class } }
GROUP BY ?class ORDER BY DESC(?count) LIMIT 50
```

Then **run a dedicated predicate survey for every class you plan to document in `shape_expressions`** — not only the top-level anchor class. Annotation classes, measurement classes, and cross-reference classes are just as likely to have missing or misnamed predicates:

```sparql
# Per-class predicate survey (run for every class in shape_expressions)
SELECT ?p (COUNT(*) AS ?n)
WHERE { GRAPH <…> { ?s a <TargetClass> ; ?p ?o } }
GROUP BY ?p ORDER BY DESC(?n) LIMIT 50
```

A predicate absent from the survey has no business in the shape; a predicate present with COUNT > 0 must be either documented or explicitly excluded with a note.

**Trace every blank node chain.** For each predicate whose object is a blank node, retrieve the bnode's full predicate set anchored on the parent class — the same predicate name can resolve to differently-shaped bnodes on different parent classes (e.g. `faldo:location` → `ExactPosition` on one class, `Region` on another):

```sparql
SELECT DISTINCT ?bPred ?bObj WHERE {
  GRAPH <…> {
    ?parent a <ParentClass> ; <bnodePredicate> ?bnode .
    ?bnode ?bPred ?bObj .
  }
} LIMIT 50
```

An undiscovered bnode schema means an incomplete shape and a missing `@<ShapeName>` definition.

**Step 3: Find Specific IRIs for Key Concepts (10 min)**
```python
examples = search_entity("keyword", limit=10)   # use database-specific API
# Inspect examples to discover structured properties and IRIs
run_sparql(database, """
  SELECT ?p ?o WHERE { <example_entity_iri> ?p ?o . } LIMIT 100
""")
```

**Step 4: Cardinality Verification (one query per predicate)**

For every class–predicate pair you intend to document in `shape_expressions`, determine the actual multiplicity with a cardinality distribution query. **Never assign `?`, `+`, or `*` based on intuition.**

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

This step is cheap (one query per predicate) and catches a large class of silent errors in the finished MIE.

### 2. Statistics Verification

Every statistic requires a verified count (query or methodology) and a verified date. Mark frequently-updated databases with an update warning.

### 3. Cross-Database Queries (Shared Endpoint Only)

Include when a shared endpoint exists, clear links are present, and queries complete in < 20 s.

**BEFORE writing any cross-database query:**
1. Call `get_MIE_file(db)` for every database in the query and read `shape_expressions`
2. Look for shared IRI namespaces (EC numbers, taxonomy, ChEBI, GO, UniProt)
3. Document which structured predicates link the databases
4. Use text search only when documented structured links do not exist

### 4. YAML Validation (CRITICAL)

```python
save_MIE_file(database, content)
result = get_MIE_file(database)
if "error" in result.lower():
    print("✗ Fix YAML errors")
```

---

## Text Search Gate Check

**⚠️ MANDATORY before using `bif:contains` or `FILTER(CONTAINS())` in any comprehensive query:**

- [ ] Read entire MIE file including `shape_expressions`
- [ ] Checked for specific IRIs (ontology, taxonomy, classification codes)
- [ ] Checked for typed predicates with controlled vocabularies
- [ ] Checked for hierarchical relationships (rdfs:subClassOf, skos:broader)
- [ ] Used search API (if available) to find and inspect example entities
- [ ] Can document why no structured alternative exists

**Never use text search for:** organisms (use taxonomy IRIs), ontology terms (GO/MeSH/ChEBI IRIs), EC numbers, drug classifications (ATC IRIs), any field with a controlled vocabulary.

**Guideline:** 6–7 queries using structured properties, 0–1 using text search. If you are using text search frequently, re-examine the schema — most RDF databases have structured alternatives.

---

## MIE File Structure

### Required Sections (in order)

1. **schema_info** — Endpoint, graphs, search tools, backend, versioning, plus `keywords` (8–15 lowercase discovery terms incl. synonyms) and `categories` (1–3 from controlled taxonomy) for `find_databases()` discovery
2. **critical_warnings** — Schema pathologies that cause silent failures (typos in IRIs, non-obvious namespace traps, critical performance filters). Use `[]` if none.
3. **shape_expressions** — ShEx for ALL entity types with inline counts and caveats
4. **sample_rdf_entries** — Exactly 3 diverse, illustrative examples (shared prefix block)
5. **sparql_query_examples** — Exactly 7 queries (2 basic / 3 intermediate / 2 advanced)
6. **cross_database_queries** — 1–2 examples IF shared endpoint; `examples: []` with `notes` otherwise
7. **cross_references** — Pattern descriptions with database coverage; SPARQL snippet optional
8. **architectural_notes** — Query strategy, schema design, performance, data integration, data quality, text search justification
9. **data_statistics** — Verified counts and coverage percentages
10. **anti_patterns** — 3–4 examples (must include the "schema check before text search" pattern)
11. **common_errors** — 2–3 scenarios

### Shape Expressions Discipline

Two structural rules `shape_expressions` must obey:

- **Every `@<ShapeRef>` must have a corresponding defined block.** Search the `shape_expressions` string for every `@<…>` reference and confirm each resolves to a `<…Shape> { … }` definition in the same section. A referenced-but-undefined shape is a structural error — the downstream LLM will generate property-path queries that silently return nothing.

- **Mark optional co-types explicitly.** When a class is sometimes (but not always) additionally typed with a second class, write each sub-type as a separate optional constraint rather than grouping them in a single `a [ T1 T2 T3 ] +` block. The grouped form is correct ShEx but visually implies all types are always co-present:

  ```shex
  # Avoid — looks like all three are always expected:
  a [ ex:MainType ex:SubTypeA ex:SubTypeB ] + ;

  # Prefer — cardinality is explicit and verifiable:
  a [ ex:MainType ] ;
  a [ ex:SubTypeA ] ?   # ~80% of instances — confirmed by COUNT
  a [ ex:SubTypeB ] ?   # ~80% of instances — confirmed by COUNT
  ```

  Annotate the percentage in an inline comment so the figure is traceable to Step 4 (Cardinality Verification).

### SPARQL Query Requirements (7 queries: 2 / 3 / 2)

| Complexity    | Count | Typical patterns                                       |
|---------------|-------|--------------------------------------------------------|
| basic         | 2     | Direct IRI lookup, VALUES with known IRIs              |
| intermediate  | 3     | Typed predicates, joins, graph navigation, aggregation |
| advanced      | 2     | Complex multi-type, cross-graph, analytical            |

- ≥ 2 queries use specific IRIs or VALUES with IRIs
- ≥ 2 queries use typed predicates or graph navigation
- ≤ 1 query uses text search — only if Gate Check is complete and justification is documented inline

---

## Template

```yaml
schema_info:
  title: [DATABASE_NAME]
  description: |
    [2–3 sentences: contents, entity types, primary use cases]
  # 8-15 lowercase keywords for find_databases() discovery. Include synonyms a user
  # might type instead of the canonical term (variant ↔ mutation ↔ polymorphism;
  # drug ↔ compound ↔ chemical). Skip stopwords and incidental vocabulary.
  keywords:
    - [keyword1]
    - [keyword2]
  # 1-3 entries from the controlled taxonomy: protein, gene, variant, compound,
  # drug_target, pathway, reaction, ontology, structure, literature, taxonomy,
  # microbe, glycan, antimicrobial, sequence, disease, materials, physics,
  # enzymology, genomics.
  # USE THE TOKEN VERBATIM: lowercase, underscores for multi-word (e.g.
  # drug_target). Do not Title Case, pluralize, space-separate, or invent
  # variants — list_categories() is case-sensitive and unknown tokens fragment
  # the index into single-DB buckets.
  # Tag only categories that genuinely characterize the database.
  categories:
    - [category1]
  endpoint: https://rdfportal.org/example/sparql
  base_uri: http://example.org/
  graphs:
    - http://example.org/dataset
    - http://example.org/ontology
  kw_search_tools:
    - [api_name]   # or [] if none
  version:
    mie_version: "2.0"
    mie_created: "YYYY-MM-DD"
    data_version: "Release YYYY.MM"
    update_frequency: "Monthly"
  access:
    backend: "Virtuoso"   # or "Blazegraph", etc. — determines bif:contains availability

# Critical warnings: schema pathologies, IRI traps, mandatory performance filters.
# These are the first things Claude reads — document anything that causes silent failures.
# Use [] if there are no critical warnings.
critical_warnings: |
  - [Example] MANDATORY FILTER: Always add ?entity up:reviewed 1 — omitting it queries
    244M instead of 589K entries and causes all COUNT queries to time out.
  - [Example] IRI NAMESPACE TRAP: GO terms in up:classifiedWith use OBO IRIs
    (http://purl.obolibrary.org/obo/GO_XXXXXXX), NOT http://purl.uniprot.org/go/.
    The wrong namespace silently returns 0 results.
  - [Example] TYPO (required verbatim): dct:referecens (not dct:references).
    Using the corrected spelling returns zero results.

shape_expressions: |
  PREFIX ex: <http://example.org/>

  <EntityShape> {
    a [ ex:Type ] ;
    ex:required xsd:string ;
    ex:optional xsd:string ?
  }
  # Include inline comments documenting:
  # - Instance counts for major entity types
  # - Non-obvious predicate semantics
  # - IRI patterns and namespace gotchas
  # - Measurement scaffolds or indirect value access patterns

# Exactly 3 RDF examples. Use a shared prefix block at the top; do NOT repeat
# @prefix declarations in every entry.
sample_rdf_entries:
  rdf_prefixes: |
    @prefix ex: <http://example.org/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  entries:
    - title: [Title — most representative entity type]
      description: One sentence on what this illustrates.
      rdf: |
        ex:entity1 a ex:Type ;
                   ex:required "value" .
    - title: [Title — illustrates a non-obvious pattern]
      description: One sentence.
      rdf: |
        ex:entity2 a ex:Type ;
                   ex:optional "value" .
    - title: [Title — cross-reference or measurement scaffold]
      description: One sentence.
      rdf: |
        ex:entity3 a ex:Type ;
                   rdfs:seeAlso <http://external.org/123> .

sparql_query_examples:
  - title: [Action Using Specific IRIs]
    description: Context.
    question: Question?
    complexity: basic
    sparql: |
      PREFIX ex: <http://example.org/>

      # Uses specific concept IRI
      SELECT ?entity ?label
      WHERE {
        ?entity ex:classification <http://example.org/concepts/SpecificType> ;
                rdfs:label ?label .
      }
      LIMIT 20

  - title: [Query with Typed Predicate]
    description: Context.
    question: Question?
    complexity: intermediate
    sparql: |
      PREFIX ex: <http://example.org/>

      SELECT ?entity ?value
      WHERE {
        ?entity ex:status "approved" ;
                ex:measurementValue ?value .
      }
      LIMIT 20

  - title: [Text Search — Only If Justified]
    description: Context.
    question: Question?
    complexity: intermediate
    sparql: |
      PREFIX ex: <http://example.org/>

      SELECT ?entity ?description
      WHERE {
        ?entity a ex:Entity ;
                ex:description ?description .
        # Text search justified: ex:description is unstructured free text;
        # checked MIE schema and inspected examples — no controlled vocabulary exists.
        # Virtuoso backend: bif:contains (indexed).
        ?description bif:contains "'keyword1' OR 'keyword2'"
      }
      LIMIT 20

cross_database_queries:
  shared_endpoint: example_endpoint
  co_located_databases: [db1, db2]
  examples:
    - title: [Structured Cross-Database Link]
      description: |
        Purpose and use case.

        Linking strategy:
        - DB1: predicate X links to shared IRI namespace (e.g. EC numbers)
        - DB2: predicate Y links to same IRI namespace
        - Direct IRI matching; no text search required
      databases_used: [db1, db2]
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
        - Linking via: [IRI type, e.g. EC numbers, taxonomy]
        - Performance: ~Ns (Tier X)
        - MIE files checked: db1, db2

  # If no cross-database queries are possible (isolated endpoint), use:
  # examples: []
  # notes: |
  #   [DATABASE] is the only database on this endpoint. Cross-database SPARQL is
  #   not possible. To link externally: [describe manual bridging strategies].

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      Brief explanation of cross-reference pattern and what it links to.
    databases:
      category:
        - "Database name: coverage percentage"
    # sparql: optional — include only if the pattern is non-trivial
    # sparql: |
    #   SELECT ?entity ?xref WHERE {
    #     ?entity rdfs:seeAlso ?xref .
    #   } LIMIT 20

architectural_notes:
  query_strategy:
    - "MANDATORY FIRST STEP: read get_MIE_file('dbname') and examine shape_expressions"
    - "Exploratory: use [search_api or exploratory SPARQL] to find examples and extract IRIs"
    - "Comprehensive: use specific IRIs in VALUES or direct predicates for complete results"
    - "Text search: bif:contains (Virtuoso) > FILTER(CONTAINS()) — only when no structured alternative"
    - "Priority: Specific IRIs > Typed predicates > Graph navigation > Text search"

  schema_design:
    - "Central entity types and their relationships"
    - "Key controlled vocabularies and their predicates"
    - "IRI patterns and namespaces; any namespace gotchas"
    - "Indirect value access patterns (e.g. measurement scaffolds)"

  performance:
    - "Critical filters that must appear in every query (document as CRITICAL)"
    - "Key optimizations and best practices"
    - "bif:contains usage — split property paths when on Virtuoso"

  data_integration:
    - "Cross-reference patterns and coverage"
    - "Linking predicates to external databases"

  data_quality:
    - "Data coverage and completeness notes"
    - "Known anomalies, duplicates, or data entry artifacts"

  text_search_justification:
    - "Number of the 7 example queries that use text search: N"
    - "Fields where text search IS legitimate: [list]"
    - "Reason structured alternatives were confirmed absent for each"

data_statistics:
  total_entities: [count]
  verified_date: "YYYY-MM-DD"
  verification_method: "Direct COUNT query / sampling methodology"

  coverage:
    key_property: "XX%"
    calculation: "[numerator / denominator]"
    verified_date: "YYYY-MM-DD"
  # Add further coverage sub-fields as needed.
  # Omit cardinality averages (avg_X_per_entity) — rarely useful during query generation.
  # Omit performance_characteristics — document in architectural_notes.performance instead.
  # Omit verification_queries — they are auditing artefacts, not needed at query time.

anti_patterns:
  - title: "Text Search When Structured Property Exists"
    problem: "Using string search when a specific IRI or typed predicate is available."
    wrong_sparql: |
      # Inefficient: text search for a controlled vocabulary value
      ?description bif:contains "'specific term'"
    correct_sparql: |
      # Efficient: use specific IRI from controlled vocabulary
      ?entity classification <http://example.org/terms/SpecificTerm> .
    explanation: "Use search tools to find examples, inspect to extract IRIs, then use those IRIs."

  - title: "Skipping Schema Check Before Text Search"
    problem: "Using text search without examining MIE shape_expressions for structured alternatives."
    wrong_sparql: |
      # No schema checked — jumps straight to text search
      ?text bif:contains "'keyword'"
    correct_sparql: |
      # Correct workflow:
      # 1. get_MIE_file(db) → read shape_expressions
      # 2. search_entity("keyword") → inspect examples → extract IRIs
      # 3. Use discovered IRIs:
      VALUES ?term { <http://example.org/term/123> <http://example.org/term/456> }
      ?entity classificationPredicate ?term .
    explanation: "Always check MIE schema and inspect examples before defaulting to text search."

  - title: "Circular Reasoning with Search Results"
    problem: "Using search API results in VALUES for comprehensive questions."
    wrong_sparql: |
      VALUES ?entity { ex:1 ex:2 ... ex:20 }  # only the 20 results from search
      SELECT (COUNT(?entity) as ?count) WHERE { ... }
    correct_sparql: |
      # Extract concept IRIs from examples, then query the full dataset:
      VALUES ?classification { <term:A> <term:B> }
      SELECT (COUNT(DISTINCT ?entity) as ?count)
      WHERE { ?entity hasClassification ?classification . }
    explanation: "Search finds examples to discover IRIs. Use those IRIs to query the complete dataset."

  - title: "Unindexed Text Search When Indexed Is Available"
    problem: "Using FILTER(CONTAINS()) when bif:contains is available (Virtuoso backend)."
    wrong_sparql: |
      FILTER(CONTAINS(LCASE(?text), "keyword"))  # unindexed, slow
    correct_sparql: |
      ?text bif:contains "'keyword'"  # indexed, faster
    explanation: "Use bif:contains for better performance on Virtuoso backends."

common_errors:
  - error: "Slow query / timeout"
    causes:
      - "Using text search when structured IRIs or predicates are available"
      - "Missing critical filters (e.g. reviewed status, graph clause)"
      - "Using FILTER(CONTAINS()) when bif:contains available"
    solutions:
      - "Check MIE critical_warnings and schema for mandatory filters"
      - "Check shape_expressions for structured properties"
      - "Use bif:contains on Virtuoso; split property paths before bif:contains"
      - "Add LIMIT to every query"

  - error: "Empty or incomplete results"
    causes:
      - "Used VALUES with search results instead of concept IRIs"
      - "Wrong IRI namespace (silent failure — returns 0 rows, no error)"
      - "Missing broader synonyms or hierarchical terms"
    solutions:
      - "Read critical_warnings for known namespace traps"
      - "Inspect example entities to confirm IRI patterns"
      - "Use rdfs:subClassOf+ / skos:broader+ for hierarchical coverage"

  - error: "Cross-database query timeout or empty results"
    causes:
      - "Did not read MIE files for all databases in the query"
      - "Missing GRAPH clauses"
      - "Missing pre-filtering within each GRAPH block before joining"
    solutions:
      - "Read MIE files for ALL databases; check shape_expressions for linking predicates"
      - "Use explicit GRAPH clauses for each database"
      - "Apply restrictive filters within each GRAPH block before the cross-database join"
      - "Add LIMIT at every query level"
```

---

## Quality Checklist

**Discovery:**
- ☐ Queried ontology graphs for controlled vocabularies
- ☐ Extracted specific IRIs for key concepts
- ☐ Documented IRI patterns and namespaces in `shape_expressions`
- ☐ **For cross-DB queries: read ALL co-located MIE files**
- ☐ **Verified no structured alternatives before using text search**

**`critical_warnings`:**
- ☐ Documented any IRI traps, typos, or mandatory performance filters
- ☐ Placed before `shape_expressions` for fast scanning

**`shape_expressions`:**
- ☐ Per-class predicate survey run for every class that appears in the shape
- ☐ Every blank-node-valued predicate traced via the parent-anchored bnode query
- ☐ Every cardinality modifier (`?`, `+`, `*`, or absent) backed by a cardinality distribution query
- ☐ Every `@<ShapeRef>` resolves to a defined `<…Shape>` block in the same section
- ☐ Optional co-types written as separate `a [ T ] ?` lines, not grouped in a single `a [ T1 T2 … ] +` block

**Query Design:**
- ☐ ≥ 2 queries use specific IRIs or VALUES with IRIs
- ☐ ≥ 2 queries use typed predicates or graph navigation
- ☐ ≤ 1 query uses text search (with Gate Check complete)
- ☐ All text-search queries include justification comments
- ☐ `bif:contains` preferred over `FILTER(CONTAINS())` on Virtuoso
- ☐ No circular reasoning (no VALUES with search results for comprehensive queries)
- ☐ All 7 queries have a LIMIT clause

**`sample_rdf_entries`:**
- ☐ Exactly 3 entries
- ☐ Single shared `rdf_prefixes` block — prefixes NOT repeated per entry
- ☐ At least one entry illustrates a non-obvious access pattern

**`cross_database_queries`:**
- ☐ 1–2 examples maximum (not 3)
- ☐ Isolated endpoints: `examples: []` with explanatory `notes`

**`data_statistics`:**
- ☐ Counts and coverage percentages present with verified dates
- ☐ No `verification_queries` sub-fields (auditing artefact — omit)
- ☐ No `cardinality` sub-section (avg-per-entity values — omit)
- ☐ No `performance_characteristics` sub-section (belongs in `architectural_notes`)

**Structure:**
- ☐ Valid YAML (load with `get_MIE_file` and check for errors)
- ☐ All 11 required sections present in order
- ☐ `schema_info` includes `keywords` (8–15) and `categories` (1–3 from taxonomy)
- ☐ 3–4 anti-patterns (including "schema check before text search")
- ☐ 2–3 common errors

**Quality:**
- ☐ All queries tested and verified
- ☐ Statistics verified with queries or methodology
- ☐ `architectural_notes.text_search_justification` documents text-search decisions

---

## 🚨 MANDATORY FINAL VALIDATION 🚨

### Step 1: Self-Verification Against This Prompt
Work through every checkbox in the Quality Checklist above.

### Step 2: Validate YAML
```python
result = get_MIE_file(database)
# If result contains "error" or YAML parsing issues → fix them
```

### Step 3: Test Queries
Run at least 3 of the 7 SPARQL queries to verify execution.

### Step 4: Audit `shape_expressions`
For each shape block:

1. Re-run the per-class predicate survey from Step 2 and compare against the documented predicates. Any predicate with COUNT > 0 that is absent from the shape must be either added or explicitly noted as intentionally excluded.
2. Confirm every `@<ShapeRef>` has a defined `<…Shape>` block.
3. For every predicate marked `?` (optional), confirm with a cardinality query that at least one subject has 0 values for it. For every predicate with no modifier (required), confirm its COUNT equals the class instance count.

This step is not optional. `shape_expressions` is the section a downstream LLM relies on most heavily for query construction. An unaudited shape is equivalent to an untested SPARQL example.

### Step 5: Final Declaration

**ONLY after Steps 1–4:**

"✓ MIE file validation complete. All requirements satisfied:
- Quality Checklist: [X/X] items checked
- YAML valid: Yes
- Queries tested: [N] queries executed successfully
- shape_expressions audited: all shapes verified against live predicate surveys, all @<ShapeRef>s resolved, all cardinality modifiers confirmed
- Ready for production use."

---

## Available Tools

**Discovery:**
`get_sparql_endpoints()`, `get_graph_list()`, `get_MIE_file()`

**Execution:**
`run_sparql(database, query)` or `run_sparql(endpoint_name=X, query)`
`save_MIE_file(database, content)`

**Keyword Search (check availability per database):**
UniProt: `search_uniprot_entity()` · ChEMBL: `search_chembl_molecule()`, `search_chembl_target()`
PDB: `search_pdb_entity()` · Reactome: `search_reactome_entity()` · Rhea: `search_rhea_entity()`
MeSH: `search_mesh_descriptor()` · OLS4: `search()`, `searchClasses()`
NCBI: `ncbi_esearch()` · PubChem: `get_pubchem_compound_id()`

---

## Text Search: When and How

**✓ Legitimate uses:** Unstructured free-text fields (rdfs:comment, dcterms:description, synthesis notes) with no controlled vocabulary or IRI equivalent.

**✗ Avoid when:** Specific IRIs, typed predicates, or graph navigation exist.

**On Virtuoso:**
```sparql
# Prefer bif:contains (indexed, faster)
?text bif:contains "'term1' OR 'term2'"

# CRITICAL: split property paths before bif:contains
# WRONG:   ?entity ex:path/ex:label ?text . ?text bif:contains "'kw'"
# CORRECT:
?entity ex:path ?intermediate .
?intermediate ex:label ?text .
?text bif:contains "'kw'"
```

**On non-Virtuoso or when bif:contains fails:**
```sparql
FILTER(CONTAINS(LCASE(?text), "term"))
```

---

## Success Criteria

A complete MIE file must satisfy ALL of these:

✓ Compact (400–600 lines typical)
✓ `critical_warnings` documents all schema pathologies and silent-failure traps
✓ ALL entity types documented in `shape_expressions` (with inline counts and caveats)
✓ Exactly 3 `sample_rdf_entries` with a shared `rdf_prefixes` block
✓ Queries prioritise specific IRIs and typed predicates (6–7 of 7)
✓ Text search used sparingly (0–1 queries) with documented justification
✓ `bif:contains` preferred over `FILTER(CONTAINS())` on Virtuoso
✓ No circular reasoning
✓ Cross-database queries document structured linking strategy; isolated endpoints use `examples: []`
✓ `data_statistics` contains counts/coverage only — no `verification_queries`, `cardinality`, or `performance_characteristics`
✓ Valid YAML (verified by loading with `get_MIE_file`)
✓ All queries tested; statistics verified

**Failure to meet ANY criterion = MIE file is incomplete.**
