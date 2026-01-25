# Create a compact yet comprehensive MIE file for an RDF database.
**Target Database: __DBNAME__**

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
- Use `get_sparql_endpoints()` to identify available endpoints and keyword search APIs
  - Returns: SPARQL endpoint URL + recommended keyword search API for each database
  - Keyword search APIs include: dedicated tools (e.g., `search_uniprot_entity`), `OLS4:searchClasses`, `ncbi_esearch`, or "sparql" (SPARQL-only)
- Use `get_graph_list(dbname)` to find ALL named graphs (data + ontology graphs)
- Attempt `get_shex(dbname)` to retrieve existing shape expressions
- Attempt `get_MIE_file(dbname)` to retrieve existing MIE files
  - **If an existing MIE file is found**: Perform compliance check (see section 1.2 below)
  - **If compliant**: Update/improve the file as needed
  - **If non-compliant**: Create a new MIE file from scratch
- Attempt `get_sparql_example(dbname)` to retrieve an example SPARQL query

**Step 1.5: Identify Shared Endpoint Databases** (2 minutes)
- Use `get_sparql_endpoints()` to identify which databases share the same endpoint
- For databases on shared endpoints, explore cross-database integration opportunities
- Check for common cross-reference patterns between co-located databases

Example:
```python
endpoints = get_sparql_endpoints()
# Find databases on same endpoint as current database
my_endpoint = endpoints['databases'][dbname]['endpoint_name']
shared_databases = endpoints['endpoints'][my_endpoint]['databases']
```

**Why this matters**: Databases on the same endpoint can be queried together in a single SPARQL query using multiple GRAPH clauses, enabling powerful cross-database integration.

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
- [ ] Contains all required sections: schema_info, shape_expressions, sample_rdf_entries, sparql_query_examples, cross_database_queries (if applicable), cross_references, architectural_notes, data_statistics, anti_patterns, common_errors
- [ ] Schema_info includes version/license/access metadata

**Sample RDF Entries:**
- [ ] Exactly 5 examples covering diverse categories
- [ ] Each has concise 1-2 sentence description

**SPARQL Query Examples:**
- [ ] Exactly 7 queries (2 basic, 3 intermediate, 2 advanced)
- [ ] Includes: keyword filtering + biological annotations
- [ ] No cross-reference queries (those in cross_references section)
- [ ] All tested and working

**Cross-Database Queries (if applicable):**
- [ ] 2-3 examples if database shares endpoint with others
- [ ] Uses proper GRAPH clauses for each database
- [ ] Includes performance optimization patterns from best practices
- [ ] Includes practical use cases
- [ ] Performance notes documented

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

### 3.5 Cross-Database Link Discovery (For Shared Endpoints Only)

**Only perform this if multiple databases share the same endpoint.**

**Step 1: Retrieve MIE files for co-located databases**
```python
# For each database on the same endpoint
for co_db in shared_databases:
    if co_db != dbname:
        try:
            mie_content = get_MIE_file(co_db)
            # Extract: graph URIs, entity types, linking properties, prefixes
            # Store for reference when creating cross-database queries
        except:
            # MIE file doesn't exist yet - proceed with discovery
            pass
```

**Why this matters**: Existing MIE files provide:
- Correct graph URIs for GRAPH clauses
- Entity type definitions and class URIs
- Property patterns and namespaces
- Known cross-references and linking properties
- Anti-patterns to avoid
- **Performance optimization patterns already tested**

**Step 2: Identify linking properties**
```sparql
# Find properties that reference entities in other databases
SELECT DISTINCT ?property ?targetDB
WHERE {
  GRAPH <current_database_graph> {
    ?entity ?property ?target .
    # Filter for URIs from other databases on same endpoint
    FILTER(STRSTARTS(STR(?target), "http://purl.obolibrary.org/obo/"))  # Example: ChEBI from ChEMBL
  }
  BIND(REPLACE(STR(?target), "^(https?://[^/]+/).*", "$1") AS ?targetDB)
}
LIMIT 100
```

**Step 3: Verify cross-database queries work**

**CRITICAL: Apply Optimization Strategies**

When creating cross-database queries, follow these optimization patterns:

```sparql
# OPTIMIZATION 1: Explicit GRAPH clauses (MANDATORY)
# Use graph URIs from retrieved MIE files
PREFIX db1: <...>
PREFIX db2: <...>

SELECT ?entity1 ?entity2 ?label1 ?label2
WHERE {
  GRAPH <database1_graph> {  # From database1 MIE file
    ?entity1 a <Type1> ;      # From database1 shape expressions
             <link_property> ?entity2 ;
             rdfs:label ?label1 .
    # OPTIMIZATION 2: Pre-filter in source database (CRITICAL)
    FILTER(?restrictive_condition)  # Apply early!
  }
  GRAPH <database2_graph> {  # From database2 MIE file
    ?entity2 a <Type2> ;      # From database2 shape expressions
             rdfs:label ?label2 .
  }
}
LIMIT 10  # OPTIMIZATION 3: Always add LIMIT
```

**Step 4: Apply Cross-Database Optimization Best Practices**

When creating cross-database query examples, apply these proven optimization strategies:

**✓ Strategy 1: Explicit GRAPH Clauses (MANDATORY)**
```sparql
# GOOD - Explicit GRAPH clauses
WHERE {
  GRAPH <http://db1/graph> { ?entity1 ?p1 ?o1 }
  GRAPH <http://db2/graph> { ?entity2 ?p2 ?entity1 }
}

# BAD - No GRAPH clauses (cross-contamination risk)
WHERE {
  ?entity1 ?p1 ?o1 .
  ?entity2 ?p2 ?entity1 .
}
```

**✓ Strategy 2: Pre-Filter in Source Database (10-100x speedup)**
```sparql
# GOOD - Filter before join
WHERE {
  GRAPH <db1> {
    ?entity1 ?p ?o .
    FILTER(?phase >= 3)  # Reduce 2.4M → 10k BEFORE join
  }
  GRAPH <db2> { ?entity2 ?p2 ?entity1 }
}

# BAD - Filter after join
WHERE {
  GRAPH <db1> { ?entity1 ?p ?o }
  GRAPH <db2> { ?entity2 ?p2 ?entity1 }
  FILTER(?phase >= 3)  # Too late!
}
```

**✓ Strategy 3: VALUES Clause for Known Entities**
```sparql
# When you have specific entity URIs
WHERE {
  GRAPH <db1> {
    VALUES ?protein { <uniprot:P04637> <uniprot:P17612> }
    ?protein up:enzyme ?enzyme .
  }
  GRAPH <db2> {
    ?reaction rhea:ec ?enzyme .
  }
}
```

**✓ Strategy 4: bif:contains for Full-Text Search**
```sparql
# CRITICAL: Split property paths when using bif:contains
# WRONG - Causes 400 error
?protein up:recommendedName/up:fullName ?name .
?name bif:contains "'kinase'"

# CORRECT - Split the path
?protein up:recommendedName ?nameObj .
?nameObj up:fullName ?name .
?name bif:contains "'kinase'" option (score ?sc)
ORDER BY DESC(?sc)
```

**✓ Strategy 5: URI Conversion for Cross-Database Linking**
```sparql
# When databases use different URI patterns
WHERE {
  GRAPH <ncbigene> {
    ?gene dct:identifier ?gene_id .
  }
  GRAPH <clinvar> {
    # Convert URI pattern: identifiers.org → ncbi.nlm.nih.gov
    BIND(IRI(CONCAT("http://ncbi.nlm.nih.gov/gene/", ?gene_id)) AS ?cv_uri)
    ?variant med2rdf:gene ?cv_uri .
  }
}
```

**✓ Strategy 6: Property Path Optimization**
```sparql
# Simple paths OK
?activity cco:hasMolecule/rdfs:label ?label .

# Complex paths - break down
# AVOID: ?pathway bp:pathwayComponent/bp:left|bp:right ?protein .
# BETTER:
?pathway bp:pathwayComponent ?component .
{ ?component bp:left ?protein } UNION { ?component bp:right ?protein }
```

**✓ Strategy 7: OPTIONAL Block Ordering**
```sparql
WHERE {
  # Required patterns first
  ?entity required:property ?value1 .
  ?entity required:property2 ?value2 .
  
  # OPTIONAL patterns last
  OPTIONAL { ?entity optional:property ?opt1 }
  OPTIONAL { ?entity optional:property2 ?opt2 }
}
```

**✓ Strategy 8: Database-Specific Optimizations**

Apply database-specific best practices from MIE files:

```sparql
# UniProt: ALWAYS filter by reviewed
?protein up:reviewed 1 ;  # 444M → 923K (99.8% reduction!)
         up:organism <taxonomy_uri> .  # Filter organism early

# Rhea: Filter by status
?reaction rhea:status rhea:Approved .

# ChEMBL: Filter by development phase
?molecule cco:highestDevelopmentPhase ?phase .
FILTER(?phase >= 3)  # Marketed/late-stage drugs

# NCBI Gene: Filter by organism immediately
?gene ncbio:taxid <http://identifiers.org/taxonomy/9606> .
```

**✓ Strategy 9: Handle Type Restrictions**
```sparql
# Some databases require ^^xsd:string for string comparisons
# Example: Reactome bp:db comparisons
?xref bp:db "UniProt"^^xsd:string .  # Required!

# Without type restriction: query fails or returns empty
```

**✓ Strategy 10: Performance Tier Awareness**

Document expected performance for users:
- **Tier 1** (1-3s): Simple 2-database queries, pre-filtered, small results
- **Tier 2** (3-8s): Property paths, text search on one side
- **Tier 3** (8-20s): Three-way joins, multiple searches, URI conversions
- **Tier 4** (20-60s): 4+ databases, complex aggregations

**Step 5: Test Query Optimization Effectiveness**

Before including a cross-database query:
1. Test WITHOUT optimizations (baseline)
2. Test WITH optimizations (compare performance)
3. Document performance improvement in notes
4. If query times out even with optimizations, simplify or exclude

**Step 6: Reference co-located database schemas**

When creating cross-database query examples:
- Use correct entity type URIs from retrieved MIE files
- Apply property patterns documented in co-database MIE files
- Follow prefix conventions from co-database MIE files
- Avoid anti-patterns documented in co-database MIE files
- Use successful query patterns from co-database sparql_query_examples
- **Apply optimization strategies from co-database architectural_notes**

**Step 7: Document optimization strategies used**

In the query notes section, document:
- Which optimization strategies were applied (by number)
- Performance observed (e.g., "~2-3 seconds for 10 results")
- Which MIE files were referenced for schema information
- Any database-specific optimizations applied
- Expected performance tier (1-4)

## 4. MIE File Construction

### Required Sections (in order):

1. **schema_info** - Database metadata + version/license/access info
2. **shape_expressions** - ShEx schemas for all entity types (minimal comments)
3. **sample_rdf_entries** - 5 diverse examples (core entity, related entity, sequence/molecular, cross-ref, geographic/temporal)
4. **sparql_query_examples** - 7 tested queries (2 basic, 3 intermediate, 2 advanced)
5. **cross_database_queries** - 2-3 examples leveraging shared endpoint with optimization patterns (ONLY if applicable)
6. **cross_references** - Pattern-based organization with all external databases
7. **architectural_notes** - schema_design, performance, data_integration, data_quality (YAML bullets, not prose) - **Include cross-database optimization strategies**
8. **data_statistics** - Counts, coverage, cardinality, performance_characteristics, data_quality_notes
9. **anti_patterns** - 2-3 common mistakes with wrong/correct versions - **Include cross-database anti-patterns**
10. **common_errors** - 2-3 error scenarios with solutions - **Include cross-database error patterns**

### Key Constraints:
- RDF examples: Exactly 5, each 1-2 sentence description
- SPARQL queries: Exactly 7, must include keyword filtering + biological annotations
- Cross-database queries: 2-3 examples with optimization strategies applied (ONLY if database shares endpoint with others)
- Anti-patterns: 2-3 examples showing wrong query → correct query (include cross-database anti-patterns if applicable)
- Common errors: 2-3 scenarios with causes and solutions (include cross-database errors if applicable)
- Keep everything concise - if it doesn't help query writing, omit it

## 5. Quality Assurance Checklist

Before finalizing, verify:

**Discovery:**
- [ ] Queried ontology graphs for all entity types
- [ ] Explored multiple URI patterns
- [ ] Documented ALL major entity types
- [ ] Identified co-located databases on shared endpoint (if applicable)

**Structure:**
- [ ] Valid YAML with all required sections (9 or 10 depending on shared endpoint)
- [ ] Schema_info includes version/license/access
- [ ] ShEx minimal comments, covers all types
- [ ] Exactly 5 diverse RDF examples
- [ ] Exactly 7 SPARQL queries (2/3/2 distribution)
- [ ] Required queries: keyword filtering + biological annotations
- [ ] Cross-database queries if database shares endpoint (2-3 examples)
- [ ] Cross-references by pattern (not by individual DB)
- [ ] Architectural notes in YAML bullets

**Quality:**
- [ ] All SPARQL queries tested and work
- [ ] Cross-database queries tested (if included)
- [ ] 2-3 anti-patterns with wrong/correct versions
- [ ] 2-3 common errors with solutions
- [ ] Statistics: counts, coverage, cardinality, performance
- [ ] Everything concise - no unnecessary content

**Cross-Database Optimization (if applicable):**
- [ ] Retrieved MIE files for all co-located databases using get_MIE_file()
- [ ] Extracted graph URIs, entity types, and properties from co-database MIE files
- [ ] Applied explicit GRAPH clause optimization (Strategy 1)
- [ ] Applied pre-filtering optimization (Strategy 2)
- [ ] Used VALUES clause where appropriate (Strategy 3)
- [ ] Used bif:contains with split property paths (Strategy 4)
- [ ] Applied URI conversion where needed (Strategy 5)
- [ ] Optimized property paths (Strategy 6)
- [ ] Ordered OPTIONAL blocks correctly (Strategy 7)
- [ ] Applied database-specific optimizations (Strategy 8)
- [ ] Handled type restrictions properly (Strategy 9)
- [ ] Documented performance tier (Strategy 10)
- [ ] 2-3 cross-database query examples tested and working
- [ ] Cross-database queries use proper GRAPH clauses from co-database MIE files
- [ ] Cross-database queries use correct entity types from co-database shape expressions
- [ ] Avoided anti-patterns documented in co-database MIE files
- [ ] Performance notes for cross-database queries documented
- [ ] Query notes document which MIE files were referenced
- [ ] Query notes document which optimization strategies were applied

## Common Pitfalls to Avoid

**❌ Sampling Bias**: First 50 results may not represent entire database → Check ontology graphs, explore multiple URI patterns

**❌ Premature Conclusions**: Query timeout ≠ "data doesn't exist" → Try smaller LIMITs, different patterns, alternative graphs

**❌ Incomplete Coverage**: Documenting only obvious entity types → Query ontology graphs first, create shapes for ALL types

**❌ Missing Error Guidance**: Not testing what fails → Note failing patterns during testing to document as anti-patterns

**❌ Ignoring Cross-Database Opportunities**: Not exploring shared endpoint databases → Check for co-located databases and linking properties

**❌ Unoptimized Cross-Database Queries**: Not applying optimization strategies → Follow 10 optimization strategies for all cross-database queries

**❌ Missing GRAPH Clauses**: Querying without explicit graphs → Always use GRAPH clauses for cross-database queries

**❌ Late Filtering**: Applying filters after joins → Filter early within GRAPH clauses

**❌ Property Path + bif:contains**: Using together without splitting → Split property paths before using bif:contains

**❌ URI Pattern Mismatch**: Not converting URIs → Use BIND with CONCAT for URI conversion

**❌ Missing Type Restrictions**: String comparisons without ^^xsd:string → Add type restrictions where required

## Available Tools
- `get_sparql_endpoints()` - Get available SPARQL endpoints and keyword search APIs for all databases
- `get_graph_list(dbname)` - List named graphs in database
- `get_sparql_example(dbname)` - Get an example SPARQL query
- `run_sparql(dbname, sparql_query)` - Execute SPARQL queries
- `run_sparql(endpoint_name=endpoint, sparql_query)` - Execute cross-database queries on shared endpoint
- `get_shex(dbname)` - Retrieve ShEx schema if available
- `get_MIE_file(dbname)` - Retrieve existing MIE file if available
- `save_MIE_file(dbname, mie_content)` - Save the final MIE file

### Keyword Search APIs by Database Type:
**Dedicated Search Tools:**
- UniProt: `search_uniprot_entity(query, limit=20)`
- PDB: `search_pdb_entity(db, query, limit=20)` where db="pdb"|"cc"|"prd"
- ChEMBL: `search_chembl_molecule(query, limit=20)` or `search_chembl_target(query, limit=20)`
- Reactome: `search_reactome_entity(query, species=None, types=None, rows=30)`
- Rhea: `search_rhea_entity(query, limit=100)`
- MeSH: `search_mesh_entity(query, limit=10)`

**OLS4 (Ontology Lookup Service):**
- ChEBI, GO, Mondo, NANDO: `OLS4:searchClasses(query, ontologyId=None, pageSize, pageNum)`

**NCBI E-utilities:**
- PubChem, Taxonomy, ClinVar, PubMed, NCBIGene, MedGen: `ncbi_esearch(database, query, max_results=20, start_index=0)`

**SPARQL-Only (use bif:contains for keyword search):**
- BacDive, MediaDive, DDBJ, GlyCosmos, Ensembl, PubTator: Use `run_sparql()` with `bif:contains` pattern

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

**CRITICAL: bif:contains + Property Paths Incompatibility**

When using `bif:contains`, you MUST split property paths:

```sparql
# WRONG - Causes 400 error
?protein up:recommendedName/up:fullName ?name .
?name bif:contains "'kinase'"

# CORRECT - Split the path
?protein up:recommendedName ?nameObj .
?nameObj up:fullName ?name .
?name bif:contains "'kinase'" option (score ?sc)
ORDER BY DESC(?sc)
```

## YAML Formatting Rules

**CRITICAL: Use "|" (pipe) syntax for ALL multiline strings**

For readability and consistency, ALL multiline string values in the MIE file MUST use the pipe (|) syntax:

```yaml
# ✅ CORRECT - Use pipe for multiline strings
description: |
  First line of description.
  Second line of description.
  
sparql: |
  SELECT ?s ?p ?o
  WHERE {
    ?s ?p ?o .
  }
  LIMIT 10

# ❌ WRONG - Don't use quoted strings for multiline content
description: "First line.\nSecond line."
sparql: "SELECT ?s ?p ?o WHERE { ?s ?p ?o . } LIMIT 10"
```

**When to use "|" syntax:**
- description fields
- sparql queries
- rdf examples
- shape_expressions
- explanation fields
- notes fields (especially in cross_database_queries)
- Any string value that spans multiple lines

**Benefits:**
- Better readability
- Preserves formatting and indentation
- Easier to edit SPARQL queries
- Consistent style throughout the file

## Cross-Database Query Guidelines

**When to Include Cross-Database Queries:**
- Database shares SPARQL endpoint with 2+ other databases
- Clear linking properties exist (skos:exactMatch, rdfs:seeAlso, etc.)
- Practical use cases benefit from integration (don't force it)
- **Queries can be optimized to complete in reasonable time (<20 seconds)**

**When NOT to Include:**
- Database is on standalone endpoint (PubChem, PDB, DDBJ, GlyCosmos)
- No clear linking mechanisms exist
- Cross-database queries consistently timeout even with optimizations
- **Performance is poor despite applying all optimization strategies**

**CRITICAL: Reference Co-Located Database MIE Files**

Before creating cross-database query examples:
1. **Retrieve MIE files** for all co-located databases using `get_MIE_file(co_db_name)`
2. **Extract key information** from retrieved MIE files:
   - Graph URIs from `schema_info.graphs`
   - PREFIX definitions from `shape_expressions`
   - Entity type URIs from `shape_expressions`
   - Property patterns from `sample_rdf_entries`
   - Linking properties from `cross_references`
   - Anti-patterns to avoid from `anti_patterns`
   - **Optimization strategies from `architectural_notes`**
   - **Performance characteristics from `data_statistics`**
3. **Apply optimization strategies** from the 10-strategy framework
4. **Use this information** to create accurate, well-formed, performant cross-database queries
5. **Document which MIE files were consulted** in query notes
6. **Document which optimization strategies were applied** in query notes

**Why this matters:**
- Ensures correct graph URIs (avoid query failures)
- Uses proper entity types and properties (avoid empty results)
- Follows established naming conventions (consistency)
- Avoids known anti-patterns (better performance)
- **Applies proven optimization patterns (10-100x speedup)**
- Creates queries that align with existing documentation

**Best Practices (Updated with Optimization Strategies):**

1. **Use explicit GRAPH clauses** (Strategy 1) - MANDATORY for each database
2. **Apply restrictive filters early** (Strategy 2) - Within each GRAPH clause, before joins
3. **Use VALUES for known entities** (Strategy 3) - When entity URIs are known
4. **Use bif:contains with split paths** (Strategy 4) - For text search
5. **Convert URIs when patterns differ** (Strategy 5) - NCBI databases especially
6. **Optimize property paths** (Strategy 6) - Break down complex paths
7. **Order OPTIONAL blocks** (Strategy 7) - Required patterns first
8. **Apply database-specific optimizations** (Strategy 8) - From MIE files
9. **Handle type restrictions** (Strategy 9) - ^^xsd:string where required
10. **Document performance tier** (Strategy 10) - Set user expectations
11. **Start with smaller LIMITs** - Cross-database queries are slower
12. **Test before including** - Verify query completes in <20 seconds
13. **Show practical value** - Examples should solve real research questions
14. **Reference MIE files** - Use correct URIs, types, and patterns from co-database documentation

**Example Pattern with Optimization Strategies:**
```sparql
# OPTIMIZED: ChEMBL + ChEBI integration
# Strategies applied: 1 (GRAPH), 2 (pre-filter), 7 (OPTIONAL ordering), 10 (LIMIT)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>

SELECT DISTINCT ?moleculeLabel ?chebiLabel ?formula ?mass
WHERE {
  GRAPH <http://rdf.ebi.ac.uk/dataset/chembl> {
    ?molecule a cco:SmallMolecule ;
              rdfs:label ?moleculeLabel ;
              skos:exactMatch ?chebiId .
    # Strategy 2: Pre-filter BEFORE join (reduces 2.4M → ~10k)
    FILTER(?moleculeLabel = "ASPIRIN")
  }
  GRAPH <http://rdf.ebi.ac.uk/dataset/chebi> {
    ?chebiId a owl:Class ;
             rdfs:label ?chebiLabel .
    # Strategy 7: OPTIONAL blocks after required patterns
    OPTIONAL { ?chebiId chebi:formula ?formula }
    OPTIONAL { ?chebiId chebi:mass ?mass }
  }
}
LIMIT 10  # Strategy 10: Always limit results
```

**Performance**: <1 second (Tier 1)
**Optimization gain**: 99.5% reduction in join size

**Common Link Patterns by Endpoint:**
- **EBI** (chembl, chebi, reactome, ensembl, amrportal):
  - ChEMBL ↔ ChEBI: `skos:exactMatch` (high performance)
  - ChEMBL targets ↔ UniProt: via `skos:exactMatch` on target components
  - Reactome ↔ UniProt: via `bp:xref` with `bp:db "UniProt"^^xsd:string` (CRITICAL: type restriction!)
  - Ensembl ↔ ChEMBL: protein targets via gene identifiers
  
- **SIB** (uniprot, rhea):
  - UniProt ↔ Rhea: enzyme-catalyzed reactions via `up:enzyme` ↔ `rhea:ec`
  - **Optimization**: ALWAYS filter UniProt by `up:reviewed 1` (99.8% reduction!)
  
- **Primary** (mesh, go, taxonomy, mondo, nando, bacdive, mediadive):
  - MONDO ↔ MeSH: disease concept IDs
  - BacDive ↔ MediaDive: bacterial strain to culture media
  - GO ↔ Taxonomy: gene ontology across species
  
- **NCBI** (clinvar, pubmed, pubtator, ncbigene, medgen):
  - ClinVar ↔ NCBI Gene: variant-to-gene mappings
  - **Optimization**: URI conversion required (identifiers.org ↔ ncbi.nlm.nih.gov)
  - PubMed ↔ NCBI Gene: via keyword matching (text search optimization critical)
  - **Performance**: Expect 5-15 seconds for complex NCBI joins

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
  kw_search_tools:
    # Obtained from get_sparql_endpoints()
    - [keyword_search_api_name]

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
    backend: "Virtuoso" or "Other"

shape_expressions: |
  # Minimal comments - only for non-obvious properties
  # Cover ALL major entity types
  PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  
  <EntityShape> {
    a [ schema:Type ] ;
    schema:property xsd:string ;
    schema:optional xsd:string ?
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

cross_database_queries:
  # Only include if database shares endpoint with others
  # 2-3 examples showing practical integration with optimization strategies
  # CRITICAL: Apply all 10 optimization strategies where applicable
  shared_endpoint: ebi  # or sib, primary, ncbi, etc.
  co_located_databases:
    - database1
    - database2
  examples:
    - title: [What integration achieves]
      description: |
        [Why this cross-database query is useful - 2-3 sentences]
        [Mention which optimization strategies make it performant]
      databases_used:
        - database1
        - database2
      complexity: intermediate  # or advanced
      sparql: |
        # Prefixes from database1 and database2 MIE files
        PREFIX db1: <http://example1.org/>
        PREFIX db2: <http://example2.org/>
        
        SELECT ?entity1 ?entity2 ?property
        WHERE {
          # Strategy 1: Explicit GRAPH clauses
          # Graph URI from database1 MIE file (schema_info.graphs)
          GRAPH <http://example1.org/dataset> {
            # Entity type from database1 MIE file (shape_expressions)
            ?entity1 a db1:Type ;
                     db1:links ?entity2 .
            # Strategy 2: Pre-filter BEFORE join
            FILTER(?restrictive_condition)
          }
          # Graph URI from database2 MIE file (schema_info.graphs)
          GRAPH <http://example2.org/dataset> {
            # Entity type from database2 MIE file (shape_expressions)
            ?entity2 a db2:Type ;
                     db2:property ?property .
            # Strategy 7: OPTIONAL blocks after required
            OPTIONAL { ?entity2 db2:optional ?opt }
          }
        }
        LIMIT 50  # Strategy 10: Always add LIMIT
      notes: |
        - Optimization strategies applied: 1 (GRAPH), 2 (pre-filter), 7 (OPTIONAL), 10 (LIMIT)
        - Query uses graph URIs from database1 and database2 MIE files
        - Entity types and properties verified against co-database shape expressions
        - Pre-filtering reduces result set by [X]% before join
        - Performance: ~[N] seconds for [M] results (Tier [1-4])
        - Performance gain: [description of improvement from optimization]
        - Use case: [practical application]
        - Referenced MIE files: database1, database2
        - Avoided anti-patterns: [specific patterns from co-database MIE files]

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
    # For shared endpoint databases, add cross-database optimization guidance:
    - "Cross-database query optimization: Use explicit GRAPH clauses (Strategy 1)"
    - "Pre-filter within GRAPH blocks before joins (Strategy 2) - 10-100x speedup"
    - "Use VALUES clause for known entity sets (Strategy 3)"
    - "Use bif:contains with split property paths (Strategy 4)"
    - "Convert URIs when linking to [specific database] (Strategy 5)"
  data_integration:
    - [Bullet: cross-references]
    # For shared endpoint databases, add:
    - "Cross-database integration with [co_db1, co_db2] via shared [endpoint_name] endpoint"
    - "Linking via [property_pattern]: [db1] ↔ [db2]"
    - "Expected performance: [Tier 1-4] ([time_range] seconds)"
  data_quality:
    - [Bullet: data quirks]

data_statistics:
  total_entity_type: count
  coverage:
    property_coverage: "~XX%"
  cardinality:
    avg_per_entity: X.X
  performance_characteristics:
    - "Single-database queries: [timing]"
    # For shared endpoint databases, add:
    - "Cross-database queries: Tier 1 (1-3s) with pre-filtering"
    - "Cross-database queries: Tier 2 (3-8s) with property paths"
    - "Cross-database queries: Tier 3 (8-20s) for three-way joins"
    - "Optimization gain: Pre-filtering reduces join size by [X]%"
  data_quality_notes:
    - "Data issue"

anti_patterns:
  # 2-3 examples - Include cross-database anti-patterns if applicable
  - title: "Common mistake"
    problem: "Why wrong"
    wrong_sparql: |
      # Bad query
    correct_sparql: |
      # Fixed query
    explanation: "What changed and optimization strategy applied"
  
  # For shared endpoint databases, add cross-database anti-pattern:
  - title: "Cross-Database Query Without Pre-Filtering"
    problem: "Filtering after join causes timeout by processing millions of intermediate results"
    wrong_sparql: |
      # BAD: Filter after join
      WHERE {
        GRAPH <db1> { ?entity1 db1:property ?value }
        GRAPH <db2> { ?entity2 db2:link ?entity1 }
        FILTER(?value >= 3)  # Too late!
      }
    correct_sparql: |
      # GOOD: Filter before join (Strategy 2)
      WHERE {
        GRAPH <db1> {
          ?entity1 db1:property ?value .
          FILTER(?value >= 3)  # Early filtering!
        }
        GRAPH <db2> { ?entity2 db2:link ?entity1 }
      }
    explanation: "Pre-filtering in source database (Strategy 2) reduces intermediate results by 99.5% before cross-database join, improving performance 10-100x"

  - title: "Property Path + bif:contains Incompatibility"
    problem: "Using bif:contains with property paths causes 400 error"
    wrong_sparql: |
      # FAILS with 400 error
      ?protein up:recommendedName/up:fullName ?name .
      ?name bif:contains "'kinase'"
    correct_sparql: |
      # CORRECT: Split property path (Strategy 4)
      ?protein up:recommendedName ?nameObj .
      ?nameObj up:fullName ?name .
      ?name bif:contains "'kinase'" option (score ?sc)
      ORDER BY DESC(?sc)
    explanation: "bif:contains requires splitting property paths into separate triple patterns (Strategy 4)"

common_errors:
  # 2-3 scenarios - Include cross-database errors if applicable
  - error: "Error type"
    causes:
      - "Cause 1"
    solutions:
      - "Solution 1"
    example_fix: |
      # Before/after (optional)
  
  # For shared endpoint databases, add cross-database error:
  - error: "Cross-database query timeout"
    causes:
      - "Missing pre-filtering (Strategy 2) - processing millions of rows"
      - "Missing GRAPH clauses (Strategy 1) - cross-contamination"
      - "Property path + bif:contains incompatibility (Strategy 4)"
      - "Missing LIMIT clause (Strategy 10)"
    solutions:
      - "Apply restrictive FILTER within source GRAPH clause before join"
      - "Use explicit GRAPH clauses for each database"
      - "Split property paths when using bif:contains"
      - "Add LIMIT to every query level"
      - "Consider using VALUES for known entity sets (Strategy 3)"
    example_fix: |
      # BEFORE (times out):
      WHERE {
        GRAPH <db1> { ?e1 ?p1 ?o1 }
        GRAPH <db2> { ?e2 ?p2 ?e1 }
        FILTER(?condition)
      }
      
      # AFTER (completes in 2s):
      WHERE {
        GRAPH <db1> {
          ?e1 ?p1 ?o1 .
          FILTER(?condition)  # Early filter!
        }
        GRAPH <db2> { ?e2 ?p2 ?e1 }
      }
      LIMIT 100
  
  - error: "Cross-database query returns empty results"
    causes:
      - "URI pattern mismatch between databases"
      - "Missing type restriction (^^xsd:string) for Reactome bp:db"
      - "Wrong graph URIs from co-database"
      - "Wrong entity types from co-database"
    solutions:
      - "Use URI conversion with BIND(IRI(CONCAT(...))) (Strategy 5)"
      - "Add ^^xsd:string type restriction (Strategy 9)"
      - "Retrieve co-database MIE file to get correct graph URIs"
      - "Use entity types from co-database shape expressions"
      - "Test each GRAPH clause independently before combining"
    example_fix: |
      # URI conversion for NCBI databases:
      GRAPH <ncbigene> {
        ?gene dct:identifier ?gene_id .
      }
      GRAPH <clinvar> {
        BIND(IRI(CONCAT("http://ncbi.nlm.nih.gov/gene/", ?gene_id)) AS ?cv_uri)
        ?variant med2rdf:gene ?cv_uri .
      }
```

## Success Criteria
- Ontology graphs checked for complete class inventory
- Multiple URI patterns explored
- All SPARQL queries tested and working
- Cross-database queries included if database shares endpoint (2-3 examples)
- **Cross-database queries apply optimization strategies (document which ones)**
- **Cross-database queries complete in reasonable time (<20 seconds)**
- Shape expressions cover ALL major entity types with minimal comments
- Sample RDF: exactly 5, covering different types
- SPARQL queries: exactly 7 (2 basic, 3 intermediate, 2 advanced) including required ones
- Cross-references by RDF pattern, all databases listed
- Architectural notes in YAML bullets (include cross-database optimization strategies if applicable)
- Statistics: counts, coverage, cardinality, performance (include cross-database performance tiers if applicable)
- 2-3 anti-patterns with wrong/correct versions (include cross-database anti-patterns if applicable)
- 2-3 common errors with solutions (include cross-database errors if applicable)
- Metadata in schema_info (version, license, access)
- File is valid YAML, compact yet complete

## Remember
**The goal: Compact, Complete, Clear, Correct, Actionable, Optimized**
- Document ALL entity types, not just some
- Include cross-database queries if database shares endpoint with others
- **Apply 10 optimization strategies to all cross-database queries**
- **Document which strategies were applied and performance gained**
- 2-3 anti-patterns prevent common mistakes (include cross-database anti-patterns)
- If it doesn't help query writing, omit it
- NEVER assume first results represent entire database
- Cross-database queries should show practical integration value
- **Cross-database queries should demonstrate optimization best practices**
- **Performance should be documented (Tier 1-4) to set user expectations**