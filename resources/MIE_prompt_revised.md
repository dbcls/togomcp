# Create a Compact Yet Comprehensive MIE File for an RDF Database
**Target Database: __DBNAME__**

## Core Philosophy

**Conciseness:** 400-600 lines typical, 700-900 max for complex databases.

**Query Strategy:** Use specific IRIs and structured predicates first. Text search (bif:contains or FILTER(CONTAINS())) only when no structured alternative exists.

**Quality:** Comprehensive discovery, verified statistics, tested queries, actionable documentation.

---

## Critical Query Strategy (MUST READ)

### Query Design Hierarchy

**1. Specific IRIs (Best - Fast, Stable, Unambiguous)**
```sparql
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .  # Human
?protein up:classifiedWith <http://purl.obolibrary.org/obo/GO_0016301> .  # Kinase
```

**2. VALUES with Multiple IRIs**
```sparql
VALUES ?goTerm { 
  <http://purl.obolibrary.org/obo/GO_0016301>  # kinase activity
  <http://purl.obolibrary.org/obo/GO_0004672>  # protein kinase activity
}
?protein up:classifiedWith ?goTerm .
```

**3. Typed Predicates**
```sparql
?molecule cco:organismName "Homo sapiens" .
?activity cco:standardType "IC50" .
```

**4. Graph Navigation**
```sparql
?organism rdfs:subClassOf+ ?phylum .
?phylum up:rank "phylum" .
```

**5. bif:contains (Virtuoso - Indexed Text Search)**
```sparql
# Use for unstructured text when backend is Virtuoso
?comment bif:contains "'apoptosis' AND 'caspase'"
```

**6. FILTER(CONTAINS()) (Last Resort - Unindexed)**
```sparql
# Use only when:
# - No specific IRIs exist
# - No typed predicates available
# - bif:contains not available (non-Virtuoso) or doesn't work for the pattern
# - Genuinely searching unstructured text
FILTER(CONTAINS(LCASE(?text), "pattern"))
```

### Decision Tree

```
1. Can you find specific IRI for this concept?
   YES → Use the IRI directly (organism, GO term, EC number, etc.)
   NO → Continue

2. Is there a controlled vocabulary or typed predicate?
   YES → Use the predicate (cco:organismName, cco:standardType)
   NO → Continue

3. Can you navigate the graph structure?
   YES → Use relationships (rdfs:subClassOf, up:annotation, etc.)
   NO → Continue

4. Is this genuinely unstructured text?
   YES → Continue to text search
   NO → Re-examine - there's usually a structured approach

5. Is the backend Virtuoso (supports bif:contains)?
   YES → Use bif:contains (indexed)
   NO → Use FILTER(CONTAINS()) (unindexed, but necessary)

6. Does bif:contains work for your pattern?
   YES → Use bif:contains
   NO → Use FILTER(CONTAINS()) as fallback
```

### Performance Comparison

| Approach | Speed | When to Use |
|----------|-------|-------------|
| Specific IRIs | ★★★★★ | Always prefer when available |
| VALUES with IRIs | ★★★★★ | Multiple known concepts |
| Typed predicates | ★★★★☆ | Controlled vocabularies |
| Graph navigation | ★★★☆☆ | Hierarchical queries |
| bif:contains | ★★☆☆☆ | Unstructured text (Virtuoso) |
| FILTER(CONTAINS()) | ★☆☆☆☆ | Last resort when nothing else works |

### How to Find Specific IRIs

**Exploratory workflow:**
```python
# Step 1: Use search API to find examples
results = search_uniprot_entity("kinase", limit=20)

# Step 2: Inspect one protein to find GO terms
run_sparql("uniprot", """
  SELECT ?goTerm ?label
  WHERE {
    <http://purl.uniprot.org/uniprot/P12345> up:classifiedWith ?goTerm .
    ?goTerm rdfs:label ?label .
  }
""")
# Extract: GO_0016301, GO_0004672, etc.

# Step 3: Use specific IRIs in comprehensive query
run_sparql("uniprot", """
  VALUES ?goTerm { <GO_0016301> <GO_0004672> }
  SELECT (COUNT(DISTINCT ?protein) as ?count)
  WHERE {
    ?protein up:reviewed 1 ;
             up:classifiedWith ?goTerm .
  }
""")
```

### Comprehensive vs Exploratory Queries

**Exploratory (Search APIs → ~20 results):**
- Purpose: Find patterns, examples, IRIs, values
- Workflow: Use search tools → extract IRIs/values → use in comprehensive queries

**Comprehensive (SPARQL → complete dataset):**
- Purpose: Definitive answers to "how many", "which organisms", "are there any"
- **Prefer specific IRIs or VALUES with known IRIs**
- **Text search only when no IRIs/predicates exist**
- **If text search needed: bif:contains (Virtuoso) > FILTER(CONTAINS()) (fallback)**

### Circular Reasoning Trap ⚠️

**WRONG:**
```sparql
# 1. Search API returns 10 proteins
# 2. Query only those 10:
VALUES ?protein { uniprot:P1 uniprot:P2 ... }
SELECT (COUNT(?protein) as ?count) WHERE { ... }
# → Only counted what you already found!
```

**CORRECT - Use Discovered IRIs:**
```sparql
# 1. Search finds kinase examples
# 2. Inspect to find GO terms: GO_0016301, GO_0004672
# 3. Query ALL proteins with those GO terms:
VALUES ?goTerm { 
  <http://purl.obolibrary.org/obo/GO_0016301>
  <http://purl.obolibrary.org/obo/GO_0004672>
}
SELECT (COUNT(DISTINCT ?protein) as ?count)
WHERE {
  ?protein up:reviewed 1 ;
           up:classifiedWith ?goTerm .
}
```

**ACCEPTABLE - Text Search if No IRIs:**
```sparql
# Use when no specific IRIs exist (e.g., searching free text)
SELECT (COUNT(DISTINCT ?protein) as ?count)
WHERE {
  ?protein up:reviewed 1 ;
           up:annotation ?annot .
  ?annot a up:Function_Annotation ;
         rdfs:comment ?comment .
  # Virtuoso: use bif:contains (indexed)
  ?comment bif:contains "'kinase' OR 'phosphorylation'"
  # Non-Virtuoso or if bif:contains fails: use FILTER(CONTAINS())
  # FILTER(CONTAINS(LCASE(?comment), "kinase"))
}
```

---

## Workflow

### 1. Discovery Phase

**Step 1: Existing Documentation (2 min)**
```python
get_sparql_endpoints()  # Endpoint + keyword search APIs
get_graph_list(dbname)  # Named graphs (look for ontology graphs)
get_MIE_file(dbname)    # Existing MIE (check compliance)
get_shex(dbname)        # Shape expressions
get_sparql_example(dbname)
```

**Step 2: Schema Discovery (5 min)**
```sparql
# Find classes and instance counts
SELECT DISTINCT ?class (COUNT(?instance) as ?count)
WHERE { ?instance a ?class }
GROUP BY ?class ORDER BY DESC(?count) LIMIT 50

# Find properties and usage
SELECT DISTINCT ?property (COUNT(?usage) as ?count)
WHERE { ?s ?property ?o }
GROUP BY ?property ORDER BY DESC(?count) LIMIT 50

# Inspect ontology graphs for controlled vocabularies
SELECT DISTINCT ?class ?label FROM <ontology_graph>
WHERE { 
  ?class a owl:Class ;
         rdfs:label ?label .
} LIMIT 100
```

**Step 3: Find Specific IRIs for Key Concepts (10 min)**
```python
# Use search APIs to find examples
proteins = search_uniprot_entity("kinase", limit=5)

# Inspect first result to find structured properties
run_sparql("uniprot", """
  SELECT ?p ?o
  WHERE {
    <first_protein_iri> ?p ?o .
  } LIMIT 50
""")

# Extract: organism IRIs, GO term IRIs, EC numbers
# Document these for use in query examples
```

### 2. Statistics Verification

**Every statistic requires:**
1. Value (count/percentage)
2. **Verification query OR methodology**
3. Verified date
4. Scope definition
5. Staleness warning (if frequently updated)

### 3. Cross-Database Queries (Shared Endpoint Only)

**Include when:** Shared endpoint + clear links exist + queries complete <20s

**MANDATORY: Read Co-Located MIE Files First**
```python
for co_db in shared_databases:
    if co_db != dbname:
        mie_content = get_MIE_file(co_db)
```

**Use Structured Linking Predicates:**
```sparql
# Link via IRIs (EC numbers, UniProt IDs, etc.)
GRAPH <uniprot_graph> {
  ?protein up:enzyme ?ecNumber .
}
GRAPH <rhea_graph> {
  ?reaction rhea:ec ?ecNumber .
}
```

### 4. YAML Validation (CRITICAL)

**After saving:**
```python
save_MIE_file(dbname, content)
result = get_MIE_file(dbname)
if "error" in result.lower():
    print("✗ Fix YAML errors")
```

---

## MIE File Structure

### Required Sections

1. **schema_info** - Metadata, graphs, endpoints
2. **shape_expressions** - ShEx for ALL entity types
3. **sample_rdf_entries** - Exactly 5 diverse examples
4. **sparql_query_examples** - Exactly 7 queries
5. **cross_database_queries** - 2-3 examples IF shared endpoint
6. **cross_references** - Pattern-based
7. **architectural_notes** - Query strategy, schema, performance
8. **data_statistics** - Verified counts, coverage
9. **anti_patterns** - 2-3 examples
10. **common_errors** - 2-3 scenarios

### SPARQL Query Requirements (7 queries: 2/3/2)

**Required Patterns (prioritize structured approaches):**
1. At least TWO using **specific IRIs or VALUES with IRIs**
2. At least ONE using **typed predicates** or **graph navigation**
3. At most ONE using **text search** (bif:contains preferred, FILTER(CONTAINS()) if necessary)

**Query Balance:**
- 2 basic (simple patterns, direct lookups)
- 3 intermediate (joins, filtering, aggregation)
- 2 advanced (complex multi-type, cross-graph, analytical)

**Text Search Guidelines:**
- **Prefer:** Specific IRIs > Typed predicates > Graph navigation
- **If text search needed:** bif:contains (Virtuoso) > FILTER(CONTAINS()) (fallback)
- **Document:** If using text search, add comment explaining why no structured alternative

**Database-Specific Patterns:**

**Proteins/Genes:** Specific taxonomy IRIs, GO term IRIs, domain types
**Chemicals:** Activity type predicates, target IRIs, value ranges
**Ontologies:** Hierarchical navigation (rdfs:subClassOf), term IRIs
**Pathways/Reactions:** EC number IRIs, participant IRIs
**Cross-Database:** Structured linking predicates (EC numbers, UniProt IRIs)

---

## Template

```yaml
schema_info:
  title: [DATABASE_NAME]
  description: |
    [2-3 sentences: contents, entity types, use cases]
  endpoint: https://rdfportal.org/example/sparql
  base_uri: http://example.org/
  graphs:
    - http://example.org/dataset
    - http://example.org/ontology
  kw_search_tools:
    - [api_name]
  version:
    mie_version: "1.0"
    mie_created: "YYYY-MM-DD"
    data_version: "Release YYYY.MM"
    update_frequency: "Monthly"
  license:
    data_license: "License name"
    license_url: "https://..."
  access:
    rate_limiting: "100 queries/min"
    max_query_timeout: "60 seconds"
    backend: "Virtuoso"

shape_expressions: |
  PREFIX ex: <http://example.org/>
  
  <EntityShape> {
    a [ ex:Type ] ;
    ex:required xsd:string ;
    ex:optional xsd:string ?
  }

sample_rdf_entries:
  - title: [Title]
    description: One sentence.
    rdf: |
      @prefix ex: <http://example.org/> .
      ex:entity a ex:Type ;
                ex:property "value" .

sparql_query_examples:
  - title: [Action]
    description: Context.
    question: Question?
    complexity: basic
    sparql: |
      PREFIX ex: <http://example.org/>
      
      # Prefer specific IRIs
      SELECT ?s ?label
      WHERE {
        ?s ex:type <http://example.org/SpecificConcept> ;
           rdfs:label ?label .
      }
      LIMIT 10
  
  - title: [Another query]
    description: Context.
    question: Question?
    complexity: intermediate
    sparql: |
      PREFIX ex: <http://example.org/>
      
      # Use typed predicates
      SELECT ?s ?name
      WHERE {
        ?s ex:organismName "Homo sapiens" ;
           ex:name ?name .
      }
      LIMIT 10
  
  - title: [Text search if needed]
    description: Context.
    question: Question?
    complexity: intermediate
    sparql: |
      PREFIX ex: <http://example.org/>
      
      SELECT ?s ?description
      WHERE {
        ?s ex:type ex:Entity ;
           ex:description ?description .
        # Text search only because description is unstructured free text
        # Prefer bif:contains (Virtuoso):
        ?description bif:contains "'keyword'"
        # Or use FILTER(CONTAINS()) if bif:contains unavailable:
        # FILTER(CONTAINS(LCASE(?description), "keyword"))
      }
      LIMIT 10

cross_database_queries:
  shared_endpoint: ebi
  co_located_databases: [db1, db2]
  examples:
    - title: [Integration]
      description: |
        Why useful. Optimization strategies.
      databases_used: [db1, db2]
      complexity: intermediate
      sparql: |
        PREFIX db1: <http://db1.org/>
        PREFIX db2: <http://db2.org/>
        
        # Link via structured properties
        SELECT ?x ?y
        WHERE {
          GRAPH <db1_graph> { 
            ?x db1:hasIdentifier ?sharedIRI .
          }
          GRAPH <db2_graph> { 
            ?y db2:linkedTo ?sharedIRI .
          }
        }
        LIMIT 10
      notes: |
        - Strategies: 1, 2, 8, 10
        - Performance: ~Ns (Tier X)

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      Brief explanation.
    databases:
      category:
        - "Database: coverage"
    sparql: |
      SELECT ?entity ?xref
      WHERE {
        ?entity rdfs:seeAlso ?xref .
        FILTER(CONTAINS(STR(?xref), "database"))
      } LIMIT 10

architectural_notes:
  query_strategy:
    - "Exploratory: Use [search_api] to find examples and extract IRIs"
    - "Comprehensive: Use specific IRIs in VALUES or direct predicates"
    - "Ontology: Use [ontology_graph] for controlled vocabularies"
    - "Text search: bif:contains (Virtuoso) > FILTER(CONTAINS()) (fallback)"
    - "Priority: IRIs > Typed predicates > Graph navigation > Text search"
  
  schema_design:
    - "Entity structure"
    - "Key controlled vocabularies"
    - "IRI patterns"
  
  performance:
    - "Key optimizations"
    - "Critical filters"
  
  data_integration:
    - "Cross-reference patterns"
    - "Linking predicates"
  
  data_quality:
    - "Data quirks"

data_statistics:
  total_entities: [count]
  verified_date: "YYYY-MM-DD"
  verification_query: |
    SELECT (COUNT(DISTINCT ?e) as ?count) WHERE { ?e a <Type> }
  
  coverage:
    key_property: "XX%"
    verified_date: "YYYY-MM-DD"

anti_patterns:
  - title: "Text Search When Structured Property Exists"
    problem: "String search when specific IRI or typed predicate available."
    wrong_sparql: |
      # Slow: Text search for organism
      ?name bif:contains "'Homo sapiens'"
    correct_sparql: |
      # Fast: Use organism IRI
      ?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .
    explanation: "Find and use specific IRIs instead of text search."
  
  - title: "Unindexed Text Search When Indexed Available"
    problem: "Using FILTER(CONTAINS()) when bif:contains available (Virtuoso)."
    wrong_sparql: |
      FILTER(CONTAINS(LCASE(?comment), "text"))  # Unindexed
    correct_sparql: |
      ?comment bif:contains "'text'"  # Indexed
    explanation: "Use bif:contains for better performance on Virtuoso backends."
  
  - title: "Circular Reasoning"
    problem: "Using search results in VALUES for comprehensive questions."
    wrong_sparql: |
      VALUES ?entity { ex:1 ... ex:20 }  # Only 20 from search
      SELECT (COUNT(?entity) as ?count) WHERE { ... }
    correct_sparql: |
      VALUES ?goTerm { <GO_0016301> }  # GO term IRI from search
      SELECT (COUNT(DISTINCT ?protein) as ?count)
      WHERE { ?protein up:classifiedWith ?goTerm }
    explanation: "Extract IRIs from search, then query all matching entities."

common_errors:
  - error: "Slow query performance"
    causes:
      - "Using text search when IRIs available"
      - "Missing critical filters"
      - "Using FILTER(CONTAINS()) when bif:contains available"
    solutions:
      - "Find specific IRIs via exploratory search"
      - "Use VALUES with IRIs"
      - "Add database-specific filters"
      - "Use bif:contains on Virtuoso"
  
  - error: "Empty comprehensive results"
    causes:
      - "Used VALUES with search results instead of concept IRIs"
    solutions:
      - "Extract concept IRIs (GO terms, etc.) from examples"
      - "Use those IRIs to query entire dataset"
```

---

## Quality Checklist

**Discovery:**
- ☐ Queried ontology graphs
- ☐ Extracted specific IRIs for key concepts
- ☐ Documented IRI patterns

**Query Design:**
- ☐ ≥2 queries use specific IRIs or VALUES
- ☐ ≥1 query uses typed predicates or graph navigation
- ☐ ≤1 query uses text search (with justification)
- ☐ Text search uses bif:contains when available (Virtuoso)
- ☐ No circular reasoning

**Structure:**
- ☐ Valid YAML
- ☐ Exactly 5 RDF samples
- ☐ Exactly 7 SPARQL queries (2/3/2)

**Quality:**
- ☐ All queries tested
- ☐ Statistics verified
- ☐ 2-3 anti-patterns

---

## Available Tools

**Discovery:**
- `get_sparql_endpoints()`, `get_graph_list()`, `get_MIE_file()`, `get_shex()`, `get_sparql_example()`

**Execution:**
- `run_sparql(dbname, query)` or `run_sparql(endpoint_name=X, query)`
- `save_MIE_file(dbname, content)`, `test_MIE_file(dbname)`

**Keyword Search (for finding IRIs/patterns):**
- UniProt: `search_uniprot_entity()`
- ChEMBL: `search_chembl_molecule/target()`
- PDB: `search_pdb_entity()`
- Reactome: `search_reactome_entity()`
- Rhea: `search_rhea_entity()`
- MeSH: `search_mesh_descriptor()`
- OLS4: `search()` or `searchClasses()`
- NCBI: `ncbi_esearch()`

---

## Text Search: When and How

### When Text Search is Appropriate

**✓ Legitimate uses:**
- Unstructured text fields (rdfs:comment, dcterms:description)
- Free text annotations (function descriptions, disease descriptions)
- No controlled vocabulary exists
- Reaction equations (chemical formulas as strings)

**✗ Avoid when:**
- Specific IRIs available (organisms, GO terms, EC numbers)
- Typed predicates exist (cco:organismName, cco:standardType)
- Graph navigation possible (rdfs:subClassOf hierarchies)

### Which Text Search to Use

**On Virtuoso backends:**
```sparql
# Prefer bif:contains (indexed, faster)
?text bif:contains "'term1' OR 'term2'"

# Split property paths:
?entity ex:path ?intermediate .
?intermediate ex:label ?text .
?text bif:contains "'keyword'"
```

**On non-Virtuoso or when bif:contains fails:**
```sparql
# Use FILTER(CONTAINS()) as fallback
FILTER(CONTAINS(LCASE(?text), "term"))

# Or for multiple terms:
FILTER(CONTAINS(LCASE(?text), "term1") || CONTAINS(LCASE(?text), "term2"))
```

---

## Success Criteria

✓ Compact (400-600 lines)
✓ ALL entity types documented
✓ **Queries prioritize specific IRIs and typed predicates**
✓ **Text search used sparingly with justification**
✓ **bif:contains preferred over FILTER(CONTAINS()) on Virtuoso**
✓ No circular reasoning
✓ Valid YAML
✓ Actionable for researchers
