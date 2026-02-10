# Create a Compact Yet Comprehensive MIE File for an RDF Database
**Target Database: __DBNAME__**

---

## 🚨 MANDATORY FIRST STEP 🚨

**BEFORE STARTING:** Call `TogoMCP_Usage_Guide()` and read it completely.

**All MIE file generation MUST comply with the TogoMCP Usage Guide.**

This prompt elaborates on the guide's principles with database-specific details. When in conflict, **the TogoMCP Usage Guide takes precedence**.

---

## Core Philosophy

**Conciseness:** 400-600 lines typical, 700-900 max for complex databases.

**Query Strategy:** Use specific IRIs and structured predicates first. Text search (bif:contains or FILTER(CONTAINS())) only when no structured alternative exists.

**Quality:** Comprehensive discovery, verified statistics, tested queries, actionable documentation.

**Compliance:** Every MIE file MUST follow TogoMCP Usage Guide principles.

---

## Critical Query Strategy (MUST READ)

### Query Design Hierarchy

**1. Specific IRIs (Best - Fast, Stable, Unambiguous)**
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

**5. bif:contains (Virtuoso - Indexed Text Search)**
```sparql
# Use for unstructured text when backend is Virtuoso
?comment bif:contains "'keyword1' AND 'keyword2'"
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
   YES → Use the IRI directly (organism, ontology term, classification code, etc.)
   NO → Continue

2. Is there a controlled vocabulary or typed predicate?
   YES → Use the predicate (organism name, type, status, phase)
   NO → Continue

3. Can you navigate the graph structure?
   YES → Use relationships (rdfs:subClassOf, skos:broader, parent/child)
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

**Exploratory workflow (applies to ALL databases):**
```python
# Step 1: Use search API to find examples (if available for this database)
results = search_entity("keyword", limit=20)
# Extract example entity IDs/IRIs

# Step 2: Inspect entities to find structured properties
run_sparql(dbname, """
  SELECT ?p ?o
  WHERE {
    <example_entity_iri> ?p ?o .
  } LIMIT 100
""")
# Look for: classification IRIs, ontology term IRIs, taxonomy IRIs, 
# typed predicates, controlled vocabulary values

# Step 3: Use discovered IRIs/predicates in comprehensive query
run_sparql(dbname, """
  VALUES ?classification { <discovered_iri_1> <discovered_iri_2> }
  SELECT (COUNT(DISTINCT ?entity) as ?count)
  WHERE {
    ?entity classificationPredicate ?classification .
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
# 1. Search API returns 20 entities
# 2. Query only those 20:
VALUES ?entity { ex:1 ex:2 ... ex:20 }
SELECT (COUNT(?entity) as ?count) WHERE { ... }
# → Only counted what you already found!
```

**CORRECT - Use Discovered IRIs:**
```sparql
# 1. Search finds example entities
# 2. Inspect to find classification IRIs or ontology term IRIs
# 3. Query ALL entities with those IRIs:
VALUES ?classificationTerm { 
  <http://example.org/classification/TypeA>
  <http://example.org/classification/TypeB>
}
SELECT (COUNT(DISTINCT ?entity) as ?count)
WHERE {
  ?entity hasClassification ?classificationTerm .
}
```

**ACCEPTABLE - Text Search if No IRIs:**
```sparql
# Use when no specific IRIs exist (e.g., searching free text descriptions)
SELECT (COUNT(DISTINCT ?entity) as ?count)
WHERE {
  ?entity a EntityType ;
          descriptionProperty ?text .
  # Virtuoso: use bif:contains (indexed)
  ?text bif:contains "'keyword1' OR 'keyword2'"
  # Non-Virtuoso or if bif:contains fails: use FILTER(CONTAINS())
  # FILTER(CONTAINS(LCASE(?text), "keyword"))
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
# Use search APIs if available for this database
examples = search_entity("keyword", limit=10)

# Inspect example entities to find structured properties
run_sparql(dbname, """
  SELECT ?p ?o
  WHERE {
    <example_entity_iri> ?p ?o .
  } LIMIT 100
""")

# Look for and extract:
# - Classification/ontology term IRIs
# - Taxonomy/organism IRIs
# - Typed predicates with controlled values
# - Cross-reference IRIs to other databases
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

#### MANDATORY: Cross-Database Query Workflow

**BEFORE writing any cross-database query:**

```python
# Step 1: Get MIE files for ALL databases involved
for db in databases_in_query:
    mie_content = get_MIE_file(db)
    # Read and examine each MIE file carefully
```

**Step 2: Examine Schema for Structured Linking Properties**

For EACH database in the query, check the MIE file's `shape_expressions` section for:
- Classification predicates (e.g., `atcClassification`, `classifiedWith`)
- External database IRIs (e.g., taxonomy, EC numbers, UniProt, ChEBI)
- Typed predicates with controlled vocabularies
- Cross-reference predicates (e.g., `rdfs:seeAlso`, `owl:sameAs`)
- Hierarchical relationships

**Step 3: Use Search Tools to Find Examples**

```python
# Find examples from each database
db1_examples = search_entity_db1("keyword", limit=10)
db2_examples = search_entity_db2("keyword", limit=10)
```

**Step 4: Inspect Examples to Confirm Linking Patterns**

```sparql
# For each database, verify structured properties exist
SELECT * WHERE {
  VALUES ?entity { <example_1> <example_2> ... }
  ?entity ?p ?o .
}
# Look for: IRIs that appear in both databases, typed linking predicates
```

**Step 5: Document Structured Linking Strategy**

In the query description, document:
- Which structured properties are used for linking
- Why this approach was chosen
- If using text search: explicitly state why no structured alternative exists

**Example - Proper Cross-Database Query:**

```yaml
- title: Find Entities with Shared Classification
  description: |
    Links entities from DB1 and DB2 via shared ontology term IRIs.
    
    Structured linking approach:
    - DB1 entities: use classificationPredicate linking to GO term IRIs
    - DB2 entities: use hasGOAnnotation linking to same GO term IRIs
    - Direct IRI matching provides precise, comprehensive results
  databases_used: [db1, db2]
  sparql: |
    # Link via shared ontology term IRIs
    GRAPH <db1_graph> {
      ?entity1 classificationPredicate ?goTerm .
    }
    GRAPH <db2_graph> {
      ?entity2 hasGOAnnotation ?goTerm .
      FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
    }
```

**Example - Text Search in Cross-Database (Only When Justified):**

```yaml
- title: Find Related Entities by Free-Text Descriptions
  description: |
    Links entities from DB1 and DB2 via keyword matching in descriptions.
    
    Text search justification:
    1. Checked both MIE files - no shared classification IRIs
    2. Inspected examples - DB1 has free-text description field only
    3. Verified: No controlled vocabulary for description content
    4. Therefore: bif:contains necessary for unstructured text field
  databases_used: [db1, db2]
  sparql: |
    # Text search justified: description is unstructured free text
    # with no controlled vocabulary or classification predicates
    GRAPH <db1_graph> {
      ?entity1 description ?desc .
      ?desc bif:contains "'keyword'"
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

## Text Search Gate Check

**⚠️ MANDATORY: Complete this checklist BEFORE using text search in any comprehensive query**

### Pre-Flight Checklist

Before using `bif:contains` or `FILTER(CONTAINS())` in a query, answer ALL questions:

- [ ] **Schema Check**: Did I run `get_MIE_file(dbname)` and read the entire file?
- [ ] **Entity Shape**: Did I examine the `shape_expressions` section for relevant entity types?
- [ ] **Structured Properties Check**: Did I look for:
  - [ ] Specific IRIs (ontology terms, classification codes, taxonomy)?
  - [ ] Typed predicates with controlled vocabularies?
  - [ ] Classification/annotation predicates?
  - [ ] Cross-reference predicates (rdfs:seeAlso, external database links)?
  - [ ] Hierarchical relationships (rdfs:subClassOf, skos:broader)?
- [ ] **Search Tools**: Did I use available search APIs to find example entities?
- [ ] **Inspection**: Did I query example entities with `SELECT * WHERE { VALUES ?entity {...} ?entity ?p ?o }`?
- [ ] **Cross-Database**: If cross-database query, did I check ALL involved MIE files?
- [ ] **Documentation**: Can I document why no structured alternative exists?

**If you answered NO to any question → STOP and complete that step**

### Required Documentation for Text Search

When using text search in any query example, **MUST** add a comment explaining:

```sparql
# Text search justified because:
# 1. Checked MIE schema - field "description" is free-form text
# 2. No controlled vocabulary or classification predicate exists
# 3. Inspected 10 example entities - confirmed only unstructured text
# 4. Therefore: bif:contains is the only option for this field
?description bif:contains "'keyword1' OR 'keyword2'"
```

### Never Use Text Search For:

These should ALWAYS have structured alternatives:
- Organisms (use taxonomy IRIs)
- Ontology terms (use GO, MeSH, ChEBI, etc. IRIs)
- Enzyme classifications (use EC number IRIs)
- Chemical compounds (use ChEBI/PubChem IRIs)  
- Diseases (use disease ontology IRIs)
- Drug classifications (use ATC code IRIs)
- Any field with controlled vocabulary or typed predicates

### Text Search is Rare

In well-designed RDF databases, comprehensive queries with text search should be **RARE** (0-1 out of 7 queries). 

If you find yourself using text search frequently:
1. Re-examine the schema more carefully
2. Check ontology graphs for controlled vocabularies
3. Inspect more example entities
4. Verify the database truly lacks structured properties

Most modern RDF databases have structured alternatives - finding them requires careful investigation.

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
9. **anti_patterns** - 3-4 examples (including schema check)
10. **common_errors** - 2-3 scenarios

### SPARQL Query Requirements (7 queries: 2/3/2)

**Required Patterns (prioritize structured approaches):**
1. At least **TWO** using specific IRIs or VALUES with IRIs
2. At least **TWO** using typed predicates or graph navigation
3. At most **ONE** using text search - ONLY if Gate Check completed

**Text Search Requirements (if needed):**
- **Must complete Text Search Gate Check** (see dedicated section above)
- **Must document justification** in query comment
- **Prefer bif:contains** (Virtuoso) over FILTER(CONTAINS())
- **Example documentation:**
  ```sparql
  # Text search justified: checked MIE schema, inspected examples,
  # field contains unstructured free-text descriptions with no
  # controlled vocabulary or classification predicates
  ?text bif:contains "'keyword'"
  ```

**Query Balance:**
- 2 basic (simple patterns, direct lookups)
- 3 intermediate (joins, filtering, aggregation)
- 2 advanced (complex multi-type, cross-graph, analytical)

**Guideline: 6-7 queries using structured properties, 0-1 using text search**

**Database-Specific Patterns:**

**Proteins/Genes:** Specific taxonomy IRIs, GO term IRIs, EC numbers, domain types
**Chemicals:** ATC codes, target IRIs, ChEBI IRIs, activity type predicates
**Ontologies:** Hierarchical navigation (rdfs:subClassOf), term IRIs
**Pathways/Reactions:** EC number IRIs, participant IRIs, pathway component relationships
**Diseases:** Disease ontology IRIs, MeSH term IRIs
**Cross-Database:** Shared IRIs (EC numbers, taxonomy, UniProt, ChEBI), typed linking predicates

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
    - [api_name]  # or empty list [] if none
  version:
    mie_version: "2.0"
    mie_created: "YYYY-MM-DD"
    data_version: "Release YYYY.MM"
    update_frequency: "Monthly"
  license:
    data_license: "License name"
    license_url: "https://..."
  access:
    rate_limiting: "100 queries/min"
    max_query_timeout: "60 seconds"
    backend: "Virtuoso"  # or "Blazegraph", etc.

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
      
      # Uses typed predicate with controlled value
      SELECT ?entity ?value
      WHERE {
        ?entity ex:status "approved" ;
                ex:measurementValue ?value .
      }
      LIMIT 20
  
  - title: [Text Search Only If Justified]
    description: Context.
    question: Question?
    complexity: intermediate
    sparql: |
      PREFIX ex: <http://example.org/>
      
      SELECT ?entity ?description
      WHERE {
        ?entity a ex:Entity ;
                ex:description ?description .
        # Text search justified: checked MIE schema, description field
        # contains unstructured free-text with no controlled vocabulary
        # Virtuoso backend: use bif:contains
        ?description bif:contains "'keyword1' OR 'keyword2'"
        # For non-Virtuoso: FILTER(CONTAINS(LCASE(?description), "keyword"))
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
        - DB1: uses predicate X linking to shared IRI namespace
        - DB2: uses predicate Y linking to same IRI namespace
        - Direct IRI matching ensures comprehensive results
      databases_used: [db1, db2]
      complexity: intermediate
      sparql: |
        PREFIX db1: <http://db1.org/>
        PREFIX db2: <http://db2.org/>
        
        # Link via shared IRIs (e.g., EC numbers, taxonomy, etc.)
        SELECT ?entity1 ?entity2 ?sharedIRI
        WHERE {
          GRAPH <db1_graph> { 
            ?entity1 db1:hasIdentifier ?sharedIRI .
          }
          GRAPH <db2_graph> { 
            ?entity2 db2:linkedTo ?sharedIRI .
          }
        }
        LIMIT 20
      notes: |
        - Linking via: [specific IRI type, e.g., EC numbers, taxonomy]
        - Performance: ~Ns (Tier X)
        - Verified: Both databases use same IRI namespace

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      Brief explanation of cross-reference pattern.
    databases:
      category:
        - "Database name: coverage percentage"
    sparql: |
      SELECT ?entity ?xref
      WHERE {
        ?entity rdfs:seeAlso ?xref .
        FILTER(CONTAINS(STR(?xref), "target_database"))
      } LIMIT 20

architectural_notes:
  query_strategy:
    - "Exploratory: Use [search_api] (or exploratory SPARQL if none) to find examples and extract IRIs"
    - "Comprehensive: Use specific IRIs in VALUES or direct predicates for complete results"
    - "Ontology: Use [ontology_graph] for controlled vocabularies and term hierarchies"
    - "Text search: bif:contains (Virtuoso) > FILTER(CONTAINS()) (fallback) - only when no structured alternative"
    - "Priority: Specific IRIs > Typed predicates > Graph navigation > Text search"
  
  schema_design:
    - "Central entity types and their relationships"
    - "Key controlled vocabularies and their predicates"
    - "IRI patterns and namespaces"
  
  performance:
    - "Critical filters for query optimization"
    - "Key optimizations and best practices"
  
  data_integration:
    - "Cross-reference patterns and coverage"
    - "Linking predicates to external databases"
  
  data_quality:
    - "Data coverage and completeness notes"
    - "Known issues or quirks"

data_statistics:
  total_entities: [count]
  verified_date: "YYYY-MM-DD"
  verification_method: "[Count query OR sampling methodology]"
  verification_query: |
    SELECT (COUNT(DISTINCT ?e) as ?count) WHERE { ?e a <Type> }
  
  coverage:
    key_property: "XX%"
    calculation: "[numerator / denominator]"
    verified_date: "YYYY-MM-DD"
    verification_query: |
      SELECT (COUNT(DISTINCT ?e) as ?count) WHERE { ?e hasProperty ?value }

anti_patterns:
  - title: "Text Search When Structured Property Exists"
    problem: "Using string search when specific IRI or typed predicate is available."
    wrong_sparql: |
      # Inefficient: Text search for controlled vocabulary value
      ?description bif:contains "'specific term'"
    correct_sparql: |
      # Efficient: Use specific IRI from controlled vocabulary
      ?entity classification <http://example.org/terms/SpecificTerm> .
    explanation: "Use search tools to find examples, inspect to extract IRIs, then use those IRIs for comprehensive queries."
  
  - title: "Skipping Schema Check Before Text Search"
    problem: "Using text search without checking MIE schema for structured alternatives."
    wrong_sparql: |
      # Incomplete: No schema checked, no examples inspected
      ?text bif:contains "'keyword'"
    correct_sparql: |
      # Complete workflow:
      # 1. get_MIE_file(dbname) → checked shape_expressions
      # 2. Found: entity has classificationPredicate to ontology terms
      # 3. search_entity("keyword") → found example entities
      # 4. Inspected examples → extracted term IRIs: term:123, term:456
      # 5. Use discovered IRIs:
      VALUES ?term { <http://example.org/term/123> <http://example.org/term/456> }
      ?entity classificationPredicate ?term .
    explanation: "Always check MIE schema and inspect examples before defaulting to text search."
  
  - title: "Circular Reasoning with Search Results"
    problem: "Using search results in VALUES for comprehensive questions."
    wrong_sparql: |
      VALUES ?entity { ex:1 ex:2 ... ex:20 }  # Only 20 from search
      SELECT (COUNT(?entity) as ?count) WHERE { ... }
      # → Only counted what you already found!
    correct_sparql: |
      # Extract concept IRIs from examples, query all matching entities:
      VALUES ?classification { <term:A> <term:B> }  # From inspecting examples
      SELECT (COUNT(DISTINCT ?entity) as ?count)
      WHERE { ?entity hasClassification ?classification }
    explanation: "Search finds examples to discover IRIs. Use those IRIs to query the complete dataset."
  
  - title: "Unindexed Text Search When Indexed Available"
    problem: "Using FILTER(CONTAINS()) when bif:contains is available (Virtuoso backend)."
    wrong_sparql: |
      FILTER(CONTAINS(LCASE(?text), "keyword"))  # Unindexed, slow
    correct_sparql: |
      ?text bif:contains "'keyword'"  # Indexed, faster
    explanation: "Use bif:contains for better performance on Virtuoso backends."

common_errors:
  - error: "Slow query performance"
    causes:
      - "Using text search when structured IRIs or predicates available"
      - "Missing database-specific critical filters"
      - "Using FILTER(CONTAINS()) when bif:contains available (Virtuoso)"
    solutions:
      - "Check MIE schema for structured properties"
      - "Use search tools to find examples and extract IRIs"
      - "Use VALUES with discovered IRIs for comprehensive queries"
      - "Add database-specific optimization filters"
      - "Use bif:contains on Virtuoso backends"
  
  - error: "Empty or incomplete comprehensive results"
    causes:
      - "Used VALUES with search results instead of concept IRIs"
      - "Missing broader synonyms or related terms"
      - "Incorrect IRI namespace or pattern"
    solutions:
      - "Extract classification/ontology IRIs from example entities"
      - "Use those IRIs to query entire dataset"
      - "Inspect hierarchical relationships (rdfs:subClassOf) for parent terms"
      - "Verify IRI patterns match actual data"
  
  - error: "Cross-database query timeout or errors"
    causes:
      - "Did not check MIE files for both databases"
      - "Using text search without verifying no structured linking exists"
      - "Missing GRAPH clauses"
      - "Missing pre-filtering within GRAPH blocks"
    solutions:
      - "Get and read MIE files for ALL databases in the query"
      - "Look for shared IRI namespaces (EC, taxonomy, ChEBI, etc.)"
      - "Use structured linking predicates when available"
      - "Apply restrictive filters within each GRAPH before joining"
```

---

## Quality Checklist

**Discovery:**
- ☐ Queried ontology graphs for controlled vocabularies
- ☐ Extracted specific IRIs for key concepts
- ☐ Documented IRI patterns and namespaces
- ☐ **For cross-DB queries: Read ALL co-located MIE files**
- ☐ **Verified no structured alternatives before using text search**

**Query Design:**
- ☐ ≥2 queries use specific IRIs or VALUES with IRIs
- ☐ ≥2 queries use typed predicates or graph navigation
- ☐ ≤1 query uses text search (with completed Gate Check)
- ☐ **Text search queries include justification comments**
- ☐ Text search uses bif:contains when available (Virtuoso)
- ☐ No circular reasoning (no VALUES with search results for comprehensive queries)

**Cross-Database (if applicable):**
- ☐ Read MIE files for ALL databases involved
- ☐ Examined shape_expressions for linking predicates
- ☐ Documented structured linking properties used
- ☐ **If using text search: documented why no structured alternative exists**

**Structure:**
- ☐ Valid YAML (load with get_MIE_file and check for errors)
- ☐ Exactly 5 RDF samples
- ☐ Exactly 7 SPARQL queries (2/3/2 complexity)
- ☐ 3-4 anti-patterns (including schema check anti-pattern)

**Quality:**
- ☐ All queries tested and verified
- ☐ Statistics verified with queries or methodology
- ☐ All verification queries included

---

## Available Tools

**Discovery:**
- `get_sparql_endpoints()`, `get_graph_list()`, `get_MIE_file()`, `get_shex()`, `get_sparql_example()`

**Execution:**
- `run_sparql(dbname, query)` or `run_sparql(endpoint_name=X, query)`
- `save_MIE_file(dbname, content)`

**Keyword Search (database-specific - check availability):**
- UniProt: `search_uniprot_entity()`
- ChEMBL: `search_chembl_molecule()`, `search_chembl_target()`
- PDB: `search_pdb_entity()`
- Reactome: `search_reactome_entity()`
- Rhea: `search_rhea_entity()`
- MeSH: `search_mesh_descriptor()`
- OLS4: `search()`, `searchClasses()`
- NCBI: `ncbi_esearch()`
- PubChem: `get_pubchem_compound_id()`

---

## Text Search: When and How

### When Text Search is Appropriate

**✓ Legitimate uses:**
- Unstructured text fields (rdfs:comment, dcterms:description)
- Free-text annotations (function descriptions, disease descriptions, abstracts)
- No controlled vocabulary exists for the field
- String-based data with no IRI equivalent (e.g., some reaction equations)

**✗ Avoid when:**
- Specific IRIs available (organisms, ontology terms, classification codes)
- Typed predicates exist (status, type, phase, organismName)
- Graph navigation possible (rdfs:subClassOf, skos:broader, hierarchies)
- Controlled vocabulary or classification predicates exist

### Which Text Search to Use

**On Virtuoso backends:**
```sparql
# Prefer bif:contains (indexed, faster)
?text bif:contains "'term1' OR 'term2'"

# IMPORTANT: Split property paths when using bif:contains
# WRONG: ?entity ex:path/ex:label ?text . ?text bif:contains "'keyword'"
# CORRECT:
?entity ex:path ?intermediate .
?intermediate ex:label ?text .
?text bif:contains "'keyword'"
```

**On non-Virtuoso or when bif:contains fails:**
```sparql
# Use FILTER(CONTAINS()) as fallback (unindexed, slower)
FILTER(CONTAINS(LCASE(?text), "term"))

# For multiple terms:
FILTER(
  CONTAINS(LCASE(?text), "term1") || 
  CONTAINS(LCASE(?text), "term2")
)
```

---

## 🚨 MANDATORY FINAL VALIDATION 🚨

**BEFORE declaring the MIE file complete, you MUST:**

### Step 1: Self-Verification Against This Prompt

Check each requirement in the Quality Checklist above. **Do not skip any checkbox.**

### Step 2: Validate YAML

```python
# Load the saved file and check for errors
result = get_MIE_file(dbname)
# If result contains "error", "invalid", or YAML parsing issues → FIX THEM
```

### Step 3: TogoMCP Usage Guide Compliance Check

**MANDATORY - Call the guide and verify compliance:**

```python
TogoMCP_Usage_Guide()
```

**Then verify each core principle:**

- [ ] **"Get MIE file FIRST"**: Is this documented in query_strategy and anti_patterns?
- [ ] **"Examine schema for structured predicates"**: Did queries prioritize structured properties?
- [ ] **"Structured Properties > bif:contains"**: Are 6-7 queries using structured approaches?
- [ ] **"bif:contains Gate Check"**: If any query uses text search, is it justified in comments?
- [ ] **"No circular reasoning"**: Are queries using discovered IRIs, not search result IDs?
- [ ] **"LIMIT in all queries"**: Do all 7 SPARQL queries have LIMIT clauses?

**If ANY checkbox is unchecked → The MIE file is NOT complete. Fix the issues.**

### Step 4: Test Queries

Run at least 3 of the 7 SPARQL queries to verify they execute without errors.

### Step 5: Final Declaration

**ONLY after completing Steps 1-4, state:**

"✓ MIE file validation complete. All requirements satisfied:
- Quality Checklist: [X/X] items checked
- YAML valid: Yes
- TogoMCP Guide compliance: Verified
- Queries tested: [N] queries executed successfully
- Ready for production use."

**If you cannot make this declaration, the MIE file is incomplete.**

---

## Success Criteria

A complete MIE file must satisfy ALL of these:

✓ Compact (400-600 lines typical)
✓ ALL entity types documented in shape_expressions
✓ **Queries prioritize specific IRIs and typed predicates**
✓ **Text search used sparingly (0-1 queries) with documented justification**
✓ **bif:contains preferred over FILTER(CONTAINS()) on Virtuoso**
✓ **No circular reasoning** (no VALUES with search results for comprehensive queries)
✓ **Cross-database queries document structured linking strategy**
✓ **Valid YAML** (verified by loading with get_MIE_file)
✓ **All queries tested** and statistics verified
✓ **TogoMCP Usage Guide compliance verified** (Step 3 above completed)
✓ Actionable for researchers

**Failure to meet ANY criterion = MIE file is incomplete.**
