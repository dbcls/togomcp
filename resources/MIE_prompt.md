# Create a Compact Yet Comprehensive MIE File for an RDF Database
**Target Database: __DBNAME__**

## Philosophy
Create documentation that is **compact, clear, and complete** - sufficient for researchers to effectively query the database without unnecessary bloat.

**Conciseness Guidelines for Generated MIE Files:**
- Descriptions: 2-3 sentences max (not paragraphs)
- Notes: Essential info only (no repetition)
- SPARQL queries: Remove unnecessary comments
- Statistics: Core metrics only (avoid over-documentation)
- Target: 400-600 lines for typical database, 700-900 for complex ones

---

## Critical Requirements Checklist

Before starting, understand these non-negotiable requirements:

- [ ] **Avoid sampling bias:** First 50 results may not represent the entire database
- [ ] **Verify comprehensively:** Check ontology graphs BEFORE sampling data
- [ ] **Document ALL entity types:** Not just the obvious ones
- [ ] **Verify ALL statistics:** Every count needs a query or methodology
- [ ] **Read co-located MIE files FIRST:** Before writing any cross-database queries
- [ ] **Test ALL queries:** Ensure they work before including

---

## 1. Discovery Phase

### 1.1 Systematic Discovery Workflow

**Step 1: Check Existing Documentation** (2 min)
```
get_sparql_endpoints() → endpoint URL + keyword search API
get_graph_list(dbname) → all named graphs (data + ontology)
get_shex(dbname) → existing shape expressions
get_MIE_file(dbname) → existing MIE file
get_sparql_example(dbname) → example query
```

If MIE exists: Check compliance (§1.2). If ≥90% compliant → update; else → create new.

Identify shared endpoint databases for cross-database opportunities.

**CRITICAL:** After generating MIE content, ALWAYS validate YAML syntax (§7) before proceeding.

**Step 2: Schema Discovery** (5 min)
```sparql
# Query ontology graphs for classes and properties
SELECT DISTINCT ?class FROM <ontology_graph> WHERE { ?class a owl:Class } LIMIT 100
SELECT DISTINCT ?property ?type FROM <ontology_graph> 
WHERE { ?property a ?type FILTER(?type IN (owl:ObjectProperty, owl:DatatypeProperty)) } LIMIT 100
```

**Step 3: Data Exploration** (10 min)
- Test URI patterns: identifiers.org, database-specific, different prefixes
- For each class: sample instances, examine properties, identify relationships
- Cross-reference discovery: rdfs:seeAlso, owl:sameAs patterns
- Note failing patterns for anti-pattern documentation

**Verification Tips:**
- If timeout: Try smaller LIMIT, different FILTER, alternative graphs
- Use `^^xsd:string` or `STR()` for string handling
- Don't assume "no results = doesn't exist"

### 1.2 MIE Compliance Check

When existing MIE retrieved, verify:

**Structure:** ☐ Valid YAML ☐ All required sections ☐ Metadata complete

**Content:** ☐ 5 RDF samples (diverse) ☐ 7 SPARQL queries (2/3/2) ☐ 2-3 anti-patterns ☐ 2-3 common errors

**Statistics:** ☐ All verified ☐ Scope defined ☐ Dates included ☐ Staleness warnings

**Cross-DB (if applicable):** ☐ 2-3 examples ☐ Optimization strategies applied ☐ Performance documented

**Decision:** ≥90% pass → update existing; <90% → create new

---

## 2. Schema Analysis

**Get complete class inventory:**
```sparql
SELECT ?class (COUNT(?instance) as ?count)
WHERE { ?instance a ?class }
GROUP BY ?class ORDER BY DESC(?count)
```

For each major entity type:
- Query property patterns and usage frequency
- Map relationships between entity types  
- Check data quality and completeness
- Document coverage statistics (with verification queries)

---

## 3. Statistics Verification (MANDATORY)

**Every statistic requires:**
1. Value (count/percentage)
2. **Verification query** OR **methodology** (how it was obtained)
3. Verified date
4. Scope definition (what's included/excluded)
5. Staleness warning (for frequently updated DBs)

**Keep statistics concise:**
- Include 3-5 core metrics (total counts, key coverage %)
- Avoid exhaustive property-by-property breakdowns
- Avoid over-documenting every possible statistic
- Focus on what helps query planning

**Handling edge cases:**

**Timeouts:** Use sampling + document method
```yaml
total_proteins: 444565015
verification_method: "Database metadata (SPARQL timeout)"
```

**Multi-representation:** Provide breakdown + total
```yaml
reactions:
  master: 1496
  all_variants: 5984
  note: "All variants includes directional representations"
```

**Coverage:** Show calculation (keep concise)
```yaml
with_pdb: "14.2%"
calculation: "COUNT(with PDB) / COUNT(all)"
```

---

## 4. Cross-Database Queries (Shared Endpoint Only)

**Include when:** Database shares endpoint with 2+ others AND clear links exist AND queries complete <20s

### CRITICAL FIRST STEP: Read Co-Located MIE Files

**Before writing ANY cross-database query:**

```python
for co_db in shared_databases:
    if co_db != dbname:
        mie_content = get_MIE_file(co_db)
        # Extract: graph URIs, entity types, properties, namespaces
        # Note: linking mechanisms, optimization patterns, anti-patterns
```

This prevents: wrong URIs → failures, wrong namespaces → empty results, missing optimizations → timeouts

### 10 Optimization Strategies

Apply where applicable (document which ones used):

1. **Explicit GRAPH clauses** (MANDATORY) - specify graph for each database
2. **Pre-filter early** (10-100x speedup) - apply FILTER within GRAPH before joins
3. **VALUES for known entities** - when specific URIs known
4. **Split property paths** - required when using bif:contains
5. **URI conversion** - BIND(IRI(CONCAT(...))) for pattern mismatches
6. **Break complex paths** - avoid long property chains
7. **Order OPTIONAL blocks** - required patterns first
8. **Database-specific optimizations** - from MIE files (e.g., up:reviewed 1 for UniProt)
9. **Type restrictions** - ^^xsd:string where required (e.g., Reactome)
10. **Performance tier** - document expected time (Tier 1-4: 1-3s, 3-8s, 8-20s, 20-60s)

### Key Patterns

**Two-stage aggregation** (avoid cross-GRAPH aggregation):
```sparql
# Stage 1: Aggregate within single database (5s)
SELECT ?key (COUNT(*) as ?count) FROM <db1> WHERE {...} GROUP BY ?key

# Stage 2: Join results to other database (1s)  
SELECT ?key ?count ?otherData WHERE {
  VALUES (?key ?count) { ("key1" 100) ("key2" 50) }  # From stage 1
  GRAPH <db2> { ?entity relates ?key ; hasData ?otherData }
}
```

**Reverse join order** (small → large):
```sparql
# Start with small dataset (ChEMBL: 3 molecules)
GRAPH <chembl> { VALUES ?mol {"MOL1" "MOL2" "MOL3"} ... }
# Then join to large dataset (AMR: 1.7M records)
GRAPH <amr> { ?measurement hasCompound ?mol }
```

---

## 5. MIE File Structure

### Required Sections (in order)

1. **schema_info** - Database metadata, version, license, access, graphs, keyword search tools
2. **shape_expressions** - ShEx for ALL entity types (minimal comments)
3. **sample_rdf_entries** - Exactly 5 diverse examples (1-2 sentence descriptions)
4. **sparql_query_examples** - Exactly 7 queries (2 basic, 3 intermediate, 2 advanced)
5. **cross_database_queries** - 2-3 examples IF shared endpoint (with optimization notes)
6. **cross_references** - Pattern-based organization with all databases
7. **architectural_notes** - YAML bullets: schema_design, performance, data_integration, data_quality
8. **data_statistics** - Verified counts, coverage, cardinality, performance
9. **anti_patterns** - 2-3 examples (wrong → correct)
10. **common_errors** - 2-3 scenarios with solutions

### Key Constraints

- **RDF samples:** Exactly 5 (core entity, related, molecular, cross-ref, temporal/geo)
  - **Descriptions: 1 sentence only** - state what it shows, nothing more
  - RDF: Show essential triples only (5-15 lines ideal)
- **SPARQL queries:** Exactly 7 (must include: keyword filtering + biological annotations)
  - Remove unnecessary comments
  - Keep descriptions to 1 sentence
  - Questions: Clear and direct
- **Cross-DB queries:** 2-3 IF shared endpoint (document optimizations applied)
  - Notes: Bullet points only, no prose
  - Focus on what strategies were used and performance
- **Statistics:** Core metrics only - don't over-document
  - Total counts, key coverage percentages, critical cardinalities
  - Avoid exhaustive breakdowns unless essential
- **Anti-patterns:** Show wrong query → correct query with 1-sentence explanation
- **YAML formatting:** Use `|` for all multiline strings

---

## 6. Template

```yaml
schema_info:
  title: [DATABASE_NAME]
  description: |
    [2-3 sentences MAX: contents, entity types (ALL), key use cases]
  endpoint: https://rdfportal.org/example/sparql
  base_uri: http://example.org/
  graphs:
    - http://example.org/dataset
  kw_search_tools:
    - [api_name]  # from get_sparql_endpoints()
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
  # Minimal - only non-obvious properties need comments
  PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  
  <EntityShape> {
    a [ schema:Type ] ;
    schema:required xsd:string ;
    schema:optional xsd:string ?
  }

sample_rdf_entries:
  - title: [Descriptive title]
    description: Single sentence describing what this example shows.
    rdf: |
      # Essential triples only (5-15 lines ideal)
      @prefix ex: <http://example.org/> .
      ex:entity a ex:Type ;
                ex:property "value" .

sparql_query_examples:
  - title: [What it does - keep brief]
    description: One sentence of context.
    question: Direct natural language question?
    complexity: basic  # or intermediate, advanced
    sparql: |
      # Remove unnecessary comments
      PREFIX ex: <http://example.org/>
      
      SELECT ?s ?p ?o
      WHERE { ?s ?p ?o }
      LIMIT 10

# Include ONLY if database shares endpoint
cross_database_queries:
  shared_endpoint: ebi  # or sib, primary, ncbi
  co_located_databases: [db1, db2]
  examples:
    - title: [Brief integration description]
      description: |
        Why this integration is useful (2 sentences max).
        Mention key optimization strategies applied.
      databases_used: [db1, db2]
      complexity: intermediate
      sparql: |
        # Compact query without excessive comments
        PREFIX db1: <http://db1.org/>
        PREFIX db2: <http://db2.org/>
        
        SELECT ?x ?y
        WHERE {
          GRAPH <db1_graph> { ?x db1:p1 ?y FILTER(?condition) }
          GRAPH <db2_graph> { ?y db2:p2 ?z }
        }
        LIMIT 10
      notes: |
        - Strategies: 1, 2, 10
        - Performance: ~Ns (Tier X)
        - Pre-filtering reduces results by X%
        - MIE files referenced: db1, db2

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      Brief explanation of how this linking pattern works (2 sentences max).
    databases:
      category:
        - "Database: brief coverage note"
    sparql: |
      # Compact representative query

architectural_notes:
  schema_design:
    - Brief bullet on entity structure
    - Brief bullet on key relationships
  performance:
    - Key optimization tips only
    - Cross-DB: Essential strategies (if applicable)
  data_integration:
    - Cross-reference summary
    - Co-located databases note (if applicable)
  data_quality:
    - Critical data quirks only

data_statistics:
  # Core metrics only - avoid over-documentation
  total_entities: [count]
  verified_date: "YYYY-MM-DD"
  verification_query: |
    SELECT (COUNT(DISTINCT ?e) as ?count) WHERE { ?e a <Type> }
  
  coverage:
    # Only essential coverage metrics (2-3 max)
    key_property: "XX%"
    calculation: "Brief calculation description"
    verified_date: "YYYY-MM-DD"
    verification_query: |
      SELECT (COUNT(?with) / COUNT(?all) as ?pct) WHERE {...}
  
  cardinality:
    # Only if important for query planning
    avg_property_per_entity: X.X
    methodology: "Brief method description"
  
  performance_characteristics:
    - "Key timing observation"
    - "Cross-DB timing" (if applicable)
  
  staleness_warning: "Brief update frequency note"

anti_patterns:
  # 2-3 examples max
  - title: [Common mistake - brief]
    problem: Why it's wrong (1 sentence).
    wrong_sparql: |
      # Minimal bad example
    correct_sparql: |
      # Minimal fixed example
    explanation: What changed and why (1 sentence).

common_errors:
  # 2-3 scenarios max
  - error: [Error type]
    causes:
      - Key cause 1
      - Key cause 2
    solutions:
      - Key solution 1
    example_fix: |
      # Compact before/after if needed
```

---

## 7. YAML Syntax Validation (CRITICAL)

**BEFORE saving any MIE file, validate YAML syntax:**

### Common YAML Pitfalls to Avoid

1. **Incorrect multiline string syntax:**
   ```yaml
   # WRONG - causes parse errors
   description: |
   This starts at column 0
   
   # CORRECT - consistent indentation
   description: |
     This is properly indented
     All lines at same level
   ```

2. **Unescaped special characters in strings:**
   ```yaml
   # WRONG - unescaped colons in values
   title: Example: A database
   
   # CORRECT - quote strings with colons
   title: "Example: A database"
   ```

3. **Inconsistent indentation (use 2 spaces, not tabs):**
   ```yaml
   # WRONG - mixed spaces/tabs or wrong spacing
   section:
       subsection: value
     another: value
   
   # CORRECT - consistent 2-space indentation
   section:
     subsection: value
     another: value
   ```

4. **Missing quotes for strings with special chars:**
   - Quote strings containing: `: { } [ ] , & * # ? | - < > = ! % @ \`
   - Quote URLs, dates, version strings with special chars
   - Example: `url: "https://example.org/path"` not `url: https://example.org/path`

5. **Incorrect list syntax:**
   ```yaml
   # WRONG - inconsistent list syntax
   databases:
   - db1
     - db2
   
   # CORRECT - consistent indentation
   databases:
     - db1
     - db2
   ```

### Validation Procedure

**Step 1: Visual inspection**
- Check all multiline strings use `|` or `>` with proper indentation
- Verify all special characters are quoted
- Confirm consistent 2-space indentation throughout

**Step 2: Parse test**
```python
import yaml
try:
    yaml.safe_load(mie_content)
    print("✓ YAML is valid")
except yaml.YAMLError as e:
    print(f"✗ YAML error: {e}")
```

**Step 3: Save and verify**
```python
# Save the MIE file
save_MIE_file(dbname, mie_content)

# Immediately verify it loads correctly
result = get_MIE_file(dbname)
if "error" in result.lower() or "parse" in result.lower():
    print("✗ MIE file has parse errors - fix before proceeding")
else:
    print("✓ MIE file loads correctly")
```

**Common error messages and fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| "mapping values are not allowed here" | Unquoted colon in string | Add quotes around the string |
| "could not find expected ':'" | Indentation error | Check 2-space indentation |
| "found character '\t' that cannot start any token" | Tab character used | Replace tabs with 2 spaces |
| "expected <block end>, but found '<block mapping start>'" | Inconsistent indentation in multiline | Fix indentation after `|` or `>` |

---

## 8. Quality Checklist

**Discovery:**
- ☐ Queried ontology graphs
- ☐ Explored multiple URI patterns  
- ☐ Documented ALL entity types
- ☐ Identified co-located databases (if applicable)

**Structure:**
- ☐ Valid YAML, all sections present
- ☐ Exactly 5 RDF samples (diverse)
- ☐ Exactly 7 SPARQL queries (2/3/2, includes required topics)
- ☐ Cross-DB section if shared endpoint (2-3 examples)

**Quality:**
- ☐ All queries tested and work
- ☐ ALL statistics verified (queries/methodology)
- ☐ 2-3 anti-patterns (wrong→correct)
- ☐ 2-3 common errors with solutions
- ☐ Cross-DB optimizations documented (if applicable)

**YAML Validation (MANDATORY):**
- ☐ Visual inspection passed (indentation, quotes, special chars)
- ☐ YAML parses without errors
- ☐ get_MIE_file() loads successfully after save
- ☐ No parse error messages in result

**Cross-Database (if applicable):**
- ☐ Read ALL co-located MIE files FIRST
- ☐ Applied optimization strategies (documented which)
- ☐ Queries complete <20s
- ☐ Performance tier documented

---

## Available Tools

- `get_sparql_endpoints()` - Endpoints + keyword search APIs
- `get_graph_list(dbname)` - Named graphs
- `get_MIE_file(dbname)` - Existing MIE file (also use for validation after save)
- `get_shex(dbname)` - ShEx schema
- `get_sparql_example(dbname)` - Example query
- `run_sparql(dbname, query)` - Execute queries
- `run_sparql(endpoint_name=X, query)` - Cross-database queries
- `save_MIE_file(dbname, content)` - Save result
- `test_MIE_file(dbname)` - Test saved MIE file for YAML errors

### Keyword Search APIs

**Dedicated:** UniProt, PDB, ChEMBL, Reactome, Rhea, MeSH (see prompt for details)
**OLS4:** ChEBI, GO, Mondo, NANDO
**NCBI:** PubChem, Taxonomy, ClinVar, PubMed, NCBIGene, MedGen
**SPARQL-only:** BacDive, MediaDive, DDBJ, GlyCosmos (use bif:contains)

---

## Using bif:contains (Virtuoso)

```sparql
?label bif:contains "('term1' AND 'term2') OR 'term3'" option (score ?sc)
ORDER BY DESC(?sc)
```

**CRITICAL:** Split property paths when using bif:contains:
```sparql
# WRONG (400 error)
?protein up:name/up:fullName ?n . ?n bif:contains "'kinase'"

# CORRECT
?protein up:name ?nameObj . ?nameObj up:fullName ?n . ?n bif:contains "'kinase'"
```

---

## Success Criteria

✓ Compact yet complete (400-600 lines typical, 700-900 max for complex DBs)
✓ ALL entity types documented  
✓ ALL statistics verified  
✓ ALL queries tested  
✓ Cross-DB queries optimized (if applicable)  
✓ No sampling bias  
✓ **Valid YAML (verified with get_MIE_file after save)**
✓ Actionable for researchers

**Conciseness Achieved:**
✓ Descriptions: 1 sentence for samples, 2-3 for schema_info
✓ SPARQL: Minimal comments, essential code only
✓ Notes: Bullets not prose
✓ Statistics: Core metrics, not exhaustive breakdowns
✓ No repetition across sections