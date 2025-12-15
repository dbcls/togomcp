# Create a compact yet comprehensive MIE file for __DBNAME__ RDF database.

## Philosophy: Essential over Exhaustive
Create documentation that is **compact, clear, and complete** - sufficient for researchers to effectively query the database without unnecessary bloat.

## 1. Discovery Phase (CRITICAL: Follow Systematically)

**⚠️ WARNING: Avoid Sampling Bias and Premature Conclusions**
- The first 50 results from a SPARQL query may NOT represent the entire database
- Always verify comprehensively using multiple query patterns before drawing conclusions
- Check ontology graphs for class definitions BEFORE sampling data
- Never assume timeouts mean "data doesn't exist"

### 1.1 Systematic Discovery Workflow

**Step 1: Check for Existing Documentation** (2 minutes)
- Use `get_sparql_endpoints()` to identify available endpoints
- Use `get_graph_list(dbname)` to find ALL named graphs (data + ontology graphs)
- Attempt `get_shex(dbname)` to retrieve existing shape expressions
- Attempt `get_MIE_file(dbname)` to retrieve existing MIE files
  - **If an existing MIE file is found**: Perform compliance check (see section 1.2 below)
  - **If compliant**: Update/improve the file as needed
  - **If non-compliant**: Create a new MIE file from scratch
- Attempt `get_sparql_example(dbname)` to retrieve an example SPARQL query

**Step 2: Discover Schema/Ontology Definitions** (5 minutes)
```sparql
# Query 1: Get all RDF classes from ontology graphs
SELECT DISTINCT ?class
FROM <ontology_graph_uri>
WHERE {
  ?class a owl:Class .
}
LIMIT 100

# Query 2: Get all properties from ontology graphs
SELECT DISTINCT ?property ?type
FROM <ontology_graph_uri>
WHERE {
  ?property a ?type .
  FILTER(?type IN (owl:ObjectProperty, owl:DatatypeProperty, rdf:Property))
}
LIMIT 100

# Query 3: Sample property domains and ranges
SELECT ?property ?domain ?range
FROM <ontology_graph_uri>
WHERE {
  ?property rdfs:domain ?domain ;
            rdfs:range ?range .
}
LIMIT 100
```

**Why this matters**: Ontology graphs reveal what SHOULD exist, preventing you from missing entire entity types.

**Step 3: Explore URI Patterns** (5 minutes)

Test multiple URI namespace patterns to discover different entity types:

```sparql
# Pattern 1: identifiers.org/[namespace]
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
  FILTER(STRSTARTS(STR(?s), "http://identifiers.org/"))
}
LIMIT 50

# Pattern 2: Database-specific namespace
SELECT ?s ?p ?o  
WHERE {
  ?s ?p ?o .
  FILTER(STRSTARTS(STR(?s), "http://[database-specific-uri]/"))
}
LIMIT 50

# Pattern 3: Sample different prefixes found in ontology
SELECT ?s ?type
WHERE {
  ?s a ?type .
}
LIMIT 100
```

**Why this matters**: Different URI patterns often indicate different data layers (e.g., identifiers vs full records vs features).

**Step 4: Systematic Class Instance Sampling** (10 minutes)

For EACH class discovered in Step 2, sample actual instances:

```sparql
# For each class found:
SELECT ?instance ?p ?o
WHERE {
  ?instance a <ClassURI> .
  ?instance ?p ?o .
}
LIMIT 50
```

**Why this matters**: Prevents assuming the database only contains what you see first. Some classes may have millions of instances, others only a few.

**Step 5: Verify and Cross-Check** (5 minutes)

If queries timeout or return no results:
- ✅ Try with smaller LIMIT values
- ✅ Try without FROM clauses
- ✅ Try with different FILTER patterns
- ✅ Sample from different graph URIs
- ✅ Use `^^xsd:string` for string type restriction or `STR()` to make a plain string.
- ❌ DON'T assume "no results = doesn't exist"

### 1.2 MIE File Compliance Check

When an existing MIE file is retrieved, verify it complies with these instructions:

**Structure & Format:**
- [ ] Properly formatted YAML
- [ ] Contains all required sections: schema_info, shape_expressions, sample_rdf_entries, sparql_query_examples, cross_references, architectural_notes, data_statistics, anti_patterns, common_errors
- [ ] Schema_info includes version/license/access metadata

**Sample RDF Entries:**
- [ ] Exactly 5 examples covering diverse categories
- [ ] Each has concise 1-2 sentence description

**SPARQL Query Examples:**
- [ ] Exactly 7 queries (2 basic, 3 intermediate, 2 advanced)
- [ ] Includes: keyword filtering + biological annotations
- [ ] No cross-reference queries (those in cross_references section)
- [ ] All tested and working

**Shape Expressions:**
- [ ] Minimal comments (only non-obvious properties)
- [ ] Covers ALL major entity types

**Other Sections:**
- [ ] Cross-references organized by RDF pattern with all databases
- [ ] Architectural notes in YAML bullet format (not prose)
- [ ] Data statistics with coverage, cardinality, performance
- [ ] 2-3 anti-patterns with wrong/correct versions
- [ ] 2-3 common errors with solutions

**Decision:**
- If ≥90% pass: Update existing file
- If <90% pass: Create new from scratch

## 2. Schema Analysis (DO NOT SKIP)

**Critical First Step: Get Complete Class Inventory**
```sparql
# From ontology graph
SELECT ?class (COUNT(?instance) as ?count)
WHERE {
  ?instance a ?class .
}
GROUP BY ?class
ORDER BY DESC(?count)
```

**If the above times out, try sampling:**
```sparql
SELECT DISTINCT ?class
WHERE {
  ?s a ?class .
}
LIMIT 100
```

Then for each class:
- Query for sample instances
- Examine property patterns
- Identify required vs optional properties
- Check for hierarchical relationships

## 3. Deep Dive Investigation

For EACH major entity type discovered:

### 3.1 Property Analysis
```sparql
# Get all properties used by this entity type
SELECT DISTINCT ?property (COUNT(?value) as ?usage)
WHERE {
  ?entity a <EntityType> .
  ?entity ?property ?value .
}
GROUP BY ?property
ORDER BY DESC(?usage)
LIMIT 50
```

### 3.2 Relationship Mapping
```sparql
# Find relationships between entity types
SELECT ?type1 ?property ?type2 (COUNT(*) as ?count)
WHERE {
  ?entity1 a ?type1 .
  ?entity1 ?property ?entity2 .
  ?entity2 a ?type2 .
}
GROUP BY ?type1 ?property ?type2
ORDER BY DESC(?count)
LIMIT 50
```

### 3.3 Cross-Reference Discovery
```sparql
# Pattern 1: rdfs:seeAlso links
SELECT ?entity ?externalDB
WHERE {
  ?entity rdfs:seeAlso ?externalDB .
}
LIMIT 100

# Pattern 2: owl:sameAs links (or database-specific properties)
SELECT ?entity ?externalDB
WHERE {
  ?entity owl:sameAs ?externalDB .
}
LIMIT 100
```

### 3.4 Data Quality Assessment
```sparql
# Check property completeness (for coverage statistics)
SELECT 
  (COUNT(DISTINCT ?entity) as ?total)
  (COUNT(DISTINCT ?withProperty) as ?withProperty)
WHERE {
  ?entity a <EntityType> .
  OPTIONAL { 
    ?entity <PropertyToCheck> ?value .
    BIND(?entity as ?withProperty)
  }
}
```

**While testing queries, note patterns that fail (timeouts, errors, empty results) to document as anti-patterns.**

## 4. MIE File Construction

### Required Sections (in order):

1. **schema_info** - Database metadata + version/license/access info
2. **shape_expressions** - ShEx schemas for all entity types (minimal comments)
3. **sample_rdf_entries** - 5 diverse examples (core entity, related entity, sequence/molecular, cross-ref, geographic/temporal)
4. **sparql_query_examples** - 7 tested queries (2 basic, 3 intermediate, 2 advanced)
5. **cross_references** - Pattern-based organization with all external databases
6. **architectural_notes** - schema_design, performance, data_integration, data_quality (YAML bullets, not prose)
7. **data_statistics** - Counts, coverage, cardinality, performance_characteristics, data_quality_notes
8. **anti_patterns** - 2-3 common mistakes with wrong/correct versions
9. **common_errors** - 2-3 error scenarios with solutions

### Key Constraints:
- RDF examples: Exactly 5, each 1-2 sentence description
- SPARQL queries: Exactly 7, must include keyword filtering + biological annotations
- Anti-patterns: 2-3 examples showing wrong query → correct query
- Common errors: 2-3 scenarios with causes and solutions
- Keep everything concise - if it doesn't help query writing, omit it

## 5. Quality Assurance Checklist

Before finalizing, verify:

**Discovery:**
- [ ] Queried ontology graphs for all entity types
- [ ] Explored multiple URI patterns
- [ ] Documented ALL major entity types

**Structure:**
- [ ] Valid YAML with all 9 required sections
- [ ] Schema_info includes version/license/access
- [ ] ShEx minimal comments, covers all types
- [ ] Exactly 5 diverse RDF examples
- [ ] Exactly 7 SPARQL queries (2/3/2 distribution)
- [ ] Required queries: keyword filtering + biological annotations
- [ ] Cross-references by pattern (not by individual DB)
- [ ] Architectural notes in YAML bullets

**Quality:**
- [ ] All SPARQL queries tested and work
- [ ] 2-3 anti-patterns with wrong/correct versions
- [ ] 2-3 common errors with solutions
- [ ] Statistics: counts, coverage, cardinality, performance
- [ ] Everything concise - no unnecessary content

## Common Pitfalls to Avoid

**❌ Sampling Bias**: First 50 results may not represent entire database → Check ontology graphs, explore multiple URI patterns

**❌ Premature Conclusions**: Query timeout ≠ "data doesn't exist" → Try smaller LIMITs, different patterns, alternative graphs

**❌ Incomplete Coverage**: Documenting only obvious entity types → Query ontology graphs first, create shapes for ALL types

**❌ Missing Error Guidance**: Not testing what fails → Note failing patterns during testing to document as anti-patterns

## Available Tools
- `get_sparql_endpoints()` - Get available SPARQL endpoints
- `get_graph_list(dbname)` - List named graphs in database
- `get_sparql_example(dbname)` - Get an example SPARQL query
- `run_sparql(dbname, sparql_query)` - Execute SPARQL queries
- `get_shex(dbname)` - Retrieve ShEx schema if available
- `get_MIE_file(dbname)` - Retrieve existing MIE file if available
- `save_MIE_file(dbname, mie_content)` - Save the final MIE file

## Using `bif:contains` for the Virtuoso backend.
If the backend database is Virtuoso, **DO use `bif:contains` for string filtering whenever possible.**
```sparql
SELECT ?label
WHERE {
  ?s rdfs:label ?label .
  label bif:contains "('amyloid' AND NOT 'precursor') OR 'alzheimer'" option (score ?sc)
}
ORDER BY DESC (?sc)
LIMIT 50
```
You can sort the results by `?sc` (keyword relevance score).　
**DON'T use `?score` for the variable name** That would result in an error.

## MIE File Structure Template
```yaml
schema_info:
  title: [DATABASE_NAME]
  description: |
    [3-5 sentences: what it contains, main entity types (ALL), use cases, key features]
  endpoint: https://rdfportal.org/example/sparql
  base_uri: http://example.org/
  graphs:
    - http://example.org/dataset
    - http://example.org/ontology
  # Metadata (integrated into schema_info)
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

shape_expressions: |
  # Minimal comments - only for non-obvious properties
  # Cover ALL major entity types
  PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  
  <EntityShape> {
    a [ schema:Type ] ;
    schema:property xsd:string ;
    schema:optional xsd:string ?     # Comment only if needed
  }

sample_rdf_entries:
  # Exactly 5: core entity, related entity, molecular, cross-ref, temporal/geo
  - title: [Descriptive title]
    description: [1-2 sentences]
    rdf: |
      # Real RDF from database

sparql_query_examples:
  # Exactly 7: 2 basic, 3 intermediate, 2 advanced
  # Must include: keyword filtering + biological annotations
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: basic
    sparql: |
      # Tested working query

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      [How external links work]
    databases:
      category:
        - Database: coverage
    sparql: |
      # Representative query

architectural_notes:
  schema_design:
    - [Bullet: entity relationships]
  performance:
    - [Bullet: optimization tips]
  data_integration:
    - [Bullet: cross-references]
  data_quality:
    - [Bullet: data quirks]

data_statistics:
  total_entity_type: count
  coverage:
    property_coverage: "~XX%"
  cardinality:
    avg_per_entity: X.X
  performance_characteristics:
    - "Tested observation"
  data_quality_notes:
    - "Data issue"

anti_patterns:
  # 2-3 examples
  - title: "Common mistake"
    problem: "Why wrong"
    wrong_sparql: |
      # Bad query
    correct_sparql: |
      # Fixed query
    explanation: "What changed"

common_errors:
  # 2-3 scenarios
  - error: "Error type"
    causes:
      - "Cause 1"
    solutions:
      - "Solution 1"
    example_fix: |
      # Before/after (optional, if helpful)
```

## Success Criteria
- Ontology graphs checked for complete class inventory
- Multiple URI patterns explored
- All SPARQL queries tested and working
- Shape expressions cover ALL major entity types with minimal comments
- Sample RDF: exactly 5, covering different types
- SPARQL queries: exactly 7 (2 basic, 3 intermediate, 2 advanced) including required ones
- Cross-references by RDF pattern, all databases listed
- Architectural notes in YAML bullets
- Statistics: counts, coverage, cardinality, performance
- 2-3 anti-patterns with wrong/correct versions
- 2-3 common errors with solutions
- Metadata in schema_info (version, license, access)
- File is valid YAML, compact yet complete

## Remember
**The goal: Compact, Complete, Clear, Correct, Actionable**
- Document ALL entity types, not just some
- 2-3 anti-patterns prevent common mistakes  
- If it doesn't help query writing, omit it
- NEVER assume first results represent entire database