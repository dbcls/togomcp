# MIE File Specification v1.1

## 1. Overview

### 1.1 Purpose
Metadata Interoperability Exchange (MIE) files provide compact, comprehensive documentation for RDF databases, enabling researchers to effectively query databases without exhaustive documentation bloat.

### 1.2 Design Philosophy
**Essential over Exhaustive**: Documentation must be compact, clear, and complete—sufficient for effective querying without unnecessary content.

### 1.3 Format
- **File Format**: YAML
- **Encoding**: UTF-8
- **Extension**: `.yaml`
- **Naming Convention**: `mie/[dbname].yaml`

### 1.4 Key Updates in v1.1
- **New Section**: `cross_database_queries` for databases on shared endpoints
- **Enhanced Discovery**: Guidance on using `get_MIE_file()` to reference co-located databases
- **Schema Info**: Added `kw_search_tools` field for keyword search APIs
- **Formatting**: Mandatory use of YAML pipe (|) syntax for multiline strings
- **Backend Support**: Explicit guidance on `bif:contains` for Virtuoso

## 2. File Structure

### 2.1 Required Sections
MIE files MUST contain the following sections in order:

1. `schema_info` - Database metadata including keyword search tools
2. `shape_expressions` - ShEx schemas
3. `sample_rdf_entries` - Example RDF data
4. `sparql_query_examples` - Tested queries
5. `cross_database_queries` - Cross-database integration examples (conditional)
6. `cross_references` - External database links
7. `architectural_notes` - Design patterns
8. `data_statistics` - Quantitative metrics
9. `anti_patterns` - Common mistakes
10. `common_errors` - Error scenarios

### 2.2 Section Dependencies
- Sections 1-4 and 6-10 are REQUIRED for all databases
- Section 5 (`cross_database_queries`) is REQUIRED ONLY if:
  - Database shares a SPARQL endpoint with 2+ other databases
  - Clear linking properties exist between databases
  - Practical use cases benefit from integration
- Sections MUST appear in the specified order
- No additional top-level sections permitted

## 3. Section Specifications

### 3.1 schema_info

#### 3.1.1 Purpose
Provides essential metadata about the RDF database, including access methods and keyword search capabilities.

#### 3.1.2 Required Fields

```yaml
schema_info:
  title: string                    # REQUIRED: Database name
  description: string              # REQUIRED: 3-5 sentences covering:
                                   # - What it contains
                                   # - ALL main entity types
                                   # - Use cases
                                   # - Key features
  endpoint: uri                    # REQUIRED: SPARQL endpoint URL
  base_uri: uri                    # REQUIRED: Base namespace URI
  graphs: array<uri>               # REQUIRED: List of named graph URIs
  kw_search_tools: array<string>   # REQUIRED: Keyword search tools/APIs
                                   # Options: dedicated tools (e.g., search_uniprot_entity),
                                   # OLS4:searchClasses, ncbi_esearch, or "sparql"
  version:                         # REQUIRED: Version metadata
    mie_version: string            # REQUIRED: MIE spec version (e.g., "1.1")
    mie_created: date              # REQUIRED: ISO 8601 format (YYYY-MM-DD)
    data_version: string           # REQUIRED: Database version/release
    update_frequency: string       # REQUIRED: Update schedule
  license:                         # REQUIRED: Licensing information
    data_license: string           # REQUIRED: License name
    license_url: uri               # REQUIRED: License URL
  access:                          # REQUIRED: Access constraints
    rate_limiting: string          # REQUIRED: Query rate limits
    max_query_timeout: string      # REQUIRED: Timeout duration
    backend: string                # REQUIRED: Triple store type (e.g., "Virtuoso")
```

#### 3.1.3 Keyword Search Tools Field
The `kw_search_tools` field specifies available keyword search methods:

**Dedicated Search Tools:**
- `search_uniprot_entity` - UniProt protein search
- `search_pdb_entity` - PDB structure search (requires db parameter)
- `search_chembl_molecule`, `search_chembl_target` - ChEMBL compound/target search
- `search_reactome_entity` - Reactome pathway search
- `search_rhea_entity` - Rhea reaction search
- `search_mesh_entity` - MeSH descriptor search

**OLS4 (Ontology Lookup Service):**
- `OLS4:searchClasses` - For ChEBI, GO, Mondo, NANDO ontologies

**NCBI E-utilities:**
- `ncbi_esearch` - For PubChem, Taxonomy, ClinVar, PubMed, NCBIGene, MedGen

**SPARQL-Only:**
- `"sparql"` - Use `run_sparql()` with `bif:contains` pattern for keyword search

#### 3.1.4 Constraints
- `description` MUST be 3-5 sentences
- `description` MUST document ALL major entity types
- All URIs MUST be valid and accessible
- `mie_created` MUST use ISO 8601 date format
- `backend` field is REQUIRED (important for determining `bif:contains` support)
- `kw_search_tools` MUST contain at least one entry

### 3.2 shape_expressions

#### 3.2.1 Purpose
Defines ShEx (Shape Expressions) schemas for all entity types in the database.

#### 3.2.2 Format
```yaml
shape_expressions: |
  PREFIX declarations
  
  <EntityShape1> {
    property declarations
  }
  
  <EntityShape2> {
    property declarations
  }
```

#### 3.2.3 Requirements
- MUST cover ALL major entity types discovered in the database
- Comments MUST be minimal (only for non-obvious properties)
- MUST use standard ShEx syntax
- MUST include relevant PREFIX declarations
- MUST use YAML pipe (|) syntax for multiline content

#### 3.2.4 Constraints
- No excessive commenting (comment only non-obvious properties)
- Shape names MUST be descriptive (e.g., `<ProteinShape>`, `<CompoundShape>`)
- MUST represent actual data patterns from the database

### 3.3 sample_rdf_entries

#### 3.3.1 Purpose
Provides representative RDF examples demonstrating data patterns.

#### 3.3.2 Structure
```yaml
sample_rdf_entries:
  - title: string                  # REQUIRED: Descriptive title
    description: string            # REQUIRED: 1-2 sentences
    rdf: |                         # REQUIRED: Use pipe syntax
      Actual RDF from database
```

#### 3.3.3 Requirements
- MUST contain EXACTLY 5 examples
- Examples MUST cover diverse categories:
  1. Core entity type
  2. Related entity type
  3. Sequence/molecular data
  4. Cross-reference example
  5. Geographic/temporal data (if applicable)
- Each `description` MUST be 1-2 sentences
- RDF MUST be actual data from the database (not fabricated)
- MUST use YAML pipe (|) syntax for RDF content

#### 3.3.4 Constraints
- Total count: EXACTLY 5 examples
- Description length: 1-2 sentences (not more)
- RDF syntax MUST be valid Turtle or N-Triples

### 3.4 sparql_query_examples

#### 3.4.1 Purpose
Provides tested, working SPARQL queries demonstrating database usage.

#### 3.4.2 Structure
```yaml
sparql_query_examples:
  - title: string                  # REQUIRED: What the query does
    description: string            # REQUIRED: Context and purpose (use pipe syntax)
    question: string               # REQUIRED: Natural language question
    complexity: enum               # REQUIRED: basic | intermediate | advanced
    sparql: |                      # REQUIRED: Tested SPARQL query (use pipe syntax)
      SELECT queries here
```

#### 3.4.3 Requirements
- MUST contain EXACTLY 7 queries with the following distribution:
  - 2 queries with `complexity: basic`
  - 3 queries with `complexity: intermediate`
  - 2 queries with `complexity: advanced`
- MUST include at least one query with keyword filtering
- MUST include at least one query with biological annotations (if applicable)
- MUST NOT include cross-database queries (those belong in `cross_database_queries`)
- ALL queries MUST be tested and confirmed working
- MUST use YAML pipe (|) syntax for SPARQL content

#### 3.4.4 Constraints
- Total count: EXACTLY 7 queries
- Complexity distribution: 2/3/2 (basic/intermediate/advanced)
- All queries MUST execute without errors
- Queries MUST use appropriate LIMIT clauses

#### 3.4.5 Complexity Guidelines
- **Basic**: Simple SELECT, single entity type, basic filters
- **Intermediate**: Multiple entity types, OPTIONAL patterns, aggregations
- **Advanced**: Complex joins, nested queries, sophisticated filtering

#### 3.4.6 Using bif:contains for Virtuoso
If `backend: "Virtuoso"` in schema_info, keyword search queries SHOULD use `bif:contains`:

```sparql
SELECT ?label ?sc
WHERE {
  ?s rdfs:label ?label .
  ?label bif:contains "('amyloid' AND NOT 'precursor') OR 'alzheimer'" 
         option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Important Notes:**
- **CRITICAL**: Do NOT use `?score` as the variable name - this will cause an error
- Use `?sc` or another variable name for the score
- `bif:contains` supports boolean operators: AND, OR, NOT
- Sort results by the score variable (e.g., `?sc`)
- Use appropriate LIMIT to prevent timeouts

### 3.5 cross_database_queries

#### 3.5.1 Applicability
This section is REQUIRED ONLY if:
- Database shares SPARQL endpoint with 2+ other databases
- Clear linking properties exist (e.g., `skos:exactMatch`, `rdfs:seeAlso`)
- Practical use cases benefit from cross-database integration

This section MUST be OMITTED if database is on standalone endpoint.

#### 3.5.2 Purpose
Documents tested cross-database integration queries that leverage shared SPARQL endpoints to combine data from multiple databases in a single query.

#### 3.5.3 Structure
```yaml
cross_database_queries:
  shared_endpoint: string          # REQUIRED: Endpoint name (ebi, sib, primary, ncbi, etc.)
  co_located_databases:            # REQUIRED: List of databases on same endpoint
    - database1
    - database2
  examples:                        # REQUIRED: 2-3 tested examples
    - title: string                # REQUIRED: What integration achieves
      description: |               # REQUIRED: Why useful (2-3 sentences, use pipe)
        Explanation of practical value
      databases_used:              # REQUIRED: Databases involved
        - database1
        - database2
      complexity: enum             # REQUIRED: intermediate | advanced
      sparql: |                    # REQUIRED: Tested query (use pipe syntax)
        PREFIX declarations
        
        SELECT query with GRAPH clauses
      notes: |                     # REQUIRED: Performance and usage notes (use pipe)
        - Graph URIs from referenced MIE files
        - Entity types verified against co-database schemas
        - Performance: timing or considerations
        - Use case: practical application
```

#### 3.5.4 Requirements - CRITICAL: Reference Co-Located Database MIE Files

**Before creating cross-database query examples:**
1. **Retrieve MIE files** for all co-located databases using `get_MIE_file(co_db_name)`
2. **Extract key information** from retrieved MIE files:
   - Graph URIs from `schema_info.graphs`
   - PREFIX definitions from `shape_expressions`
   - Entity type URIs from `shape_expressions`
   - Property patterns from `sample_rdf_entries`
   - Linking properties from `cross_references`
   - Anti-patterns to avoid from `anti_patterns`
3. **Use this information** to create accurate, well-formed cross-database queries
4. **Document which MIE files were consulted** in the `notes` field

**Why this matters:**
- Ensures correct graph URIs (prevents query failures)
- Uses proper entity types and properties (prevents empty results)
- Follows established naming conventions (ensures consistency)
- Avoids known anti-patterns (improves performance)
- Creates queries aligned with existing documentation

#### 3.5.5 Best Practices
1. **Use explicit GRAPH clauses** for each database
2. **Start with smaller LIMITs** (cross-database queries are slower)
3. **Filter early** - apply constraints within each GRAPH clause
4. **Document performance** - note if queries are slow
5. **Show practical value** - examples should solve real research questions
6. **Reference MIE files** - use correct URIs, types, and patterns

#### 3.5.6 Example Pattern
```yaml
examples:
  - title: Link ChEMBL molecules to ChEBI chemical entities
    description: |
      Retrieves ChEMBL molecules with their corresponding ChEBI entities, 
      providing additional chemical classification and ontology information 
      not available in ChEMBL alone.
    databases_used:
      - chembl
      - chebi
    complexity: intermediate
    sparql: |
      PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
      
      SELECT ?molecule ?moleculeLabel ?chebiLabel ?formula
      WHERE {
        GRAPH <http://rdf.ebi.ac.uk/dataset/chembl> {
          ?molecule a cco:SmallMolecule ;
                    rdfs:label ?moleculeLabel ;
                    skos:exactMatch ?chebiId .
          FILTER(?moleculeLabel = "ASPIRIN")
        }
        GRAPH <http://rdf.ebi.ac.uk/dataset/chebi> {
          ?chebiId a owl:Class ;
                   rdfs:label ?chebiLabel ;
                   chebi:formula ?formula .
        }
      }
      LIMIT 10
    notes: |
      - Graph URIs from chembl.yaml and chebi.yaml MIE files
      - Uses skos:exactMatch linking property documented in chembl cross_references
      - Entity types (cco:SmallMolecule, owl:Class) from respective shape expressions
      - Performance: ~2-3 seconds for 10 results
      - Use case: Enriching compound data with chemical ontology classifications
```

#### 3.5.7 Common Link Patterns by Endpoint

**EBI Endpoint** (chembl, chebi, reactome, ensembl, amrportal):
- ChEMBL ↔ ChEBI: `skos:exactMatch`
- ChEMBL targets ↔ Ensembl: via UniProt IDs
- Reactome ↔ Ensembl: gene identifiers

**SIB Endpoint** (uniprot, rhea):
- UniProt ↔ Rhea: enzyme-catalyzed reactions

**Primary Endpoint** (mesh, go, taxonomy, mondo, nando, bacdive, mediadive):
- MONDO ↔ MeSH: disease concept IDs
- BacDive ↔ MediaDive: bacterial strain to culture media
- GO ↔ Taxonomy: gene ontology across species

**NCBI Endpoint** (clinvar, pubmed, pubtator, ncbigene, medgen):
- ClinVar ↔ NCBI Gene: variant-to-gene mappings
- PubMed ↔ PubTator: article-to-entity annotations

### 3.6 cross_references

#### 3.6.1 Purpose
Documents external database linkages organized by RDF pattern.

#### 3.6.2 Structure
```yaml
cross_references:
  - pattern: string                # REQUIRED: RDF property pattern
    description: |                 # REQUIRED: How links work (use pipe syntax)
      Explanation
    databases:                     # REQUIRED: Organized by category
      category_name:
        - database_name: coverage  # Format: "Database (~XX%)" or similar
    sparql: |                      # REQUIRED: Representative query (use pipe)
      SELECT query
```

#### 3.6.3 Requirements
- Group by RDF pattern (e.g., `rdfs:seeAlso`, `owl:sameAs`, `skos:exactMatch`)
- List ALL external databases found
- Include coverage estimates where possible
- Provide working SPARQL query for each pattern
- Use YAML pipe (|) syntax for multiline strings

#### 3.6.4 Constraints
- Do NOT create separate entries for each individual database
- Organize by pattern, then categorize databases
- Include coverage percentages when available
- All SPARQL queries MUST be tested

### 3.7 architectural_notes

#### 3.7.1 Purpose
Documents design patterns, performance characteristics, and data quality issues.

#### 3.7.2 Structure
```yaml
architectural_notes:
  schema_design:
    - bullet point                 # REQUIRED: Design patterns
  performance:
    - bullet point                 # REQUIRED: Optimization tips
  data_integration:
    - bullet point                 # REQUIRED: Cross-reference patterns
    - bullet point                 # Include cross-database if applicable
  data_quality:
    - bullet point                 # REQUIRED: Data quirks and issues
```

#### 3.7.3 Requirements
- MUST use YAML bullet format (not prose paragraphs)
- MUST include all four subsections
- Each subsection MUST have at least one bullet point
- Content MUST be actionable and relevant to query writing
- If `cross_database_queries` section exists, include cross-database opportunities in `data_integration`

#### 3.7.4 Constraints
- No prose paragraphs
- Bullets MUST be concise (1-2 sentences each)
- Focus on information that helps with querying

### 3.8 data_statistics

#### 3.8.1 Purpose
Provides quantitative metrics about database contents and performance.

#### 3.8.2 Structure
```yaml
data_statistics:
  total_[entity_type]: integer     # REQUIRED: Entity counts
  coverage:                        # REQUIRED: Property completeness
    property_name: string          # Format: "~XX%" or ">XX%"
  cardinality:                     # REQUIRED: Relationship metrics
    avg_[relationship]: number     # Average cardinality
  performance_characteristics:     # REQUIRED: Query performance
    - observation                  # Tested observations
    - cross_database_performance   # Include if cross_database_queries section exists
  data_quality_notes:              # OPTIONAL: Data issues
    - note                         # Quality concerns
```

#### 3.8.3 Requirements
- MUST include entity counts for all major types
- MUST include coverage statistics for important properties
- MUST include cardinality metrics for key relationships
- MUST include performance observations from actual testing
- If `cross_database_queries` section exists, include cross-database query performance notes
- MAY include data quality notes if relevant

#### 3.8.4 Constraints
- All statistics MUST be based on actual queries
- Coverage percentages should be approximate ranges
- Performance characteristics MUST be reproducible

### 3.9 anti_patterns

#### 3.9.1 Purpose
Documents common mistakes with corrected versions.

#### 3.9.2 Structure
```yaml
anti_patterns:
  - title: string                  # REQUIRED: Mistake description
    problem: string                # REQUIRED: Why it's wrong
    wrong_sparql: |                # REQUIRED: Incorrect query (use pipe)
      Bad query
    correct_sparql: |              # REQUIRED: Fixed query (use pipe)
      Good query
    explanation: |                 # REQUIRED: What changed (use pipe)
      Explanation
```

#### 3.9.3 Requirements
- MUST contain 2-3 examples
- Each MUST show both wrong and correct versions
- Both queries SHOULD be tested (wrong should fail/timeout, correct should work)
- Focus on mistakes that researchers actually make
- Use YAML pipe (|) syntax for all SPARQL queries and explanations

#### 3.9.4 Constraints
- Count: 2-3 examples (not more, not less)
- Both `wrong_sparql` and `correct_sparql` MUST be provided
- Explanation MUST be clear and educational

### 3.10 common_errors

#### 3.10.1 Purpose
Documents error scenarios with causes and solutions.

#### 3.10.2 Structure
```yaml
common_errors:
  - error: string                  # REQUIRED: Error type/message
    causes:                        # REQUIRED: List of causes
      - cause                      # At least one cause
    solutions:                     # REQUIRED: List of solutions
      - solution                   # At least one solution
    example_fix: |                 # OPTIONAL: Before/after code (use pipe)
      Code examples
```

#### 3.10.3 Requirements
- MUST contain 2-3 error scenarios
- Each MUST have at least one cause and one solution
- Focus on errors researchers actually encounter
- MAY include example fixes if helpful
- Use YAML pipe (|) syntax for example_fix if provided

#### 3.10.4 Constraints
- Count: 2-3 scenarios
- Each MUST have actionable solutions
- Causes MUST be specific and accurate

## 4. Discovery Requirements

### 4.1 Systematic Discovery Process
Before creating an MIE file, creators MUST:

1. Use `get_sparql_endpoints()` to identify:
   - Available SPARQL endpoints
   - Keyword search APIs for the database
   - Databases sharing the same endpoint (for cross-database opportunities)
2. Check for existing documentation (`get_MIE_file()`, `get_shex()`)
3. For shared endpoints: Retrieve MIE files of co-located databases using `get_MIE_file(co_db_name)`
4. Query ontology graphs for ALL entity types
5. Explore multiple URI patterns
6. Sample instances for each discovered entity type
7. Verify findings across different query patterns
8. If on shared endpoint: Identify linking properties to co-located databases

### 4.2 Cross-Database Discovery (For Shared Endpoints)
When database shares endpoint with others:

1. **Retrieve co-located database MIE files**: Use `get_MIE_file()` for each co-database
2. **Extract reference information**:
   - Graph URIs from `schema_info.graphs`
   - Prefixes from `shape_expressions`
   - Entity type definitions from `shape_expressions`
   - Property patterns from `sample_rdf_entries`
   - Linking properties from `cross_references`
3. **Identify linking properties**: Find properties that reference co-database entities
4. **Verify cross-database queries**: Test queries using graph URIs and patterns from MIE files
5. **Document performance**: Note execution times for cross-database queries

### 4.3 Avoiding Bias
- MUST NOT rely solely on first 50 results
- MUST query ontology graphs before sampling data
- MUST NOT assume timeouts mean "data doesn't exist"
- MUST explore multiple query strategies
- For Virtuoso backends: SHOULD use `bif:contains` for keyword searches

### 4.4 Verification
All SPARQL queries in the MIE file MUST be:
- Actually executed against the database
- Confirmed to return valid results
- Tested with appropriate LIMIT values
- For cross-database queries: Verified against referenced MIE file information

## 5. YAML Formatting Rules

### 5.1 Mandatory Pipe Syntax
**CRITICAL: Use "|" (pipe) syntax for ALL multiline strings**

For readability and consistency, ALL multiline string values MUST use the pipe (|) syntax:

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

### 5.2 When to Use Pipe Syntax
- `description` fields in all sections
- `sparql` queries
- `rdf` examples in sample_rdf_entries
- `shape_expressions` content
- `explanation` fields in anti_patterns
- `example_fix` fields in common_errors
- `notes` fields in cross_database_queries
- Any string value that spans multiple lines

### 5.3 Benefits
- Better readability
- Preserves formatting and indentation
- Easier to edit SPARQL queries
- Consistent style throughout the file

## 6. Compliance Checking

### 6.1 Existing MIE File Evaluation
When an existing MIE file is found, evaluate against:

#### Structure & Format
- [ ] Valid YAML syntax
- [ ] All required sections present (9 or 10 depending on shared endpoint)
- [ ] Sections in correct order
- [ ] Version/license/access metadata in schema_info
- [ ] kw_search_tools field present in schema_info
- [ ] Multiline strings use pipe (|) syntax

#### Sample RDF Entries
- [ ] Exactly 5 examples
- [ ] Covers diverse categories
- [ ] Each has 1-2 sentence description
- [ ] Uses pipe syntax for RDF content

#### SPARQL Query Examples
- [ ] Exactly 7 queries
- [ ] Correct complexity distribution (2/3/2)
- [ ] Includes keyword filtering query
- [ ] Includes biological annotations query (if applicable)
- [ ] No cross-database queries
- [ ] All tested and working
- [ ] Uses pipe syntax for SPARQL content

#### Cross-Database Queries (if applicable)
- [ ] Section present if database shares endpoint with others
- [ ] 2-3 tested examples
- [ ] Uses proper GRAPH clauses from referenced MIE files
- [ ] Documents which MIE files were consulted
- [ ] Includes performance notes
- [ ] Uses pipe syntax for SPARQL and notes

#### Shape Expressions
- [ ] Minimal comments (only non-obvious)
- [ ] Covers ALL major entity types
- [ ] Uses pipe syntax

#### Other Sections
- [ ] Cross-references organized by pattern
- [ ] All external databases listed
- [ ] Architectural notes in YAML bullets
- [ ] Data_integration includes cross-database notes (if applicable)
- [ ] Statistics include counts, coverage, cardinality
- [ ] Performance characteristics include cross-database notes (if applicable)
- [ ] 2-3 anti-patterns with both versions
- [ ] 2-3 common errors with solutions
- [ ] Pipe syntax used consistently

#### Compliance Threshold
- **≥90% pass**: Update existing file
- **<90% pass**: Create new file from scratch

## 7. Quality Assurance

### 7.1 Pre-Finalization Checklist

#### Discovery
- [ ] Used `get_sparql_endpoints()` to identify endpoint and keyword search APIs
- [ ] Queried ontology graphs for all entity types
- [ ] Explored multiple URI patterns
- [ ] Documented ALL major entity types
- [ ] Identified co-located databases on shared endpoint (if applicable)
- [ ] Retrieved MIE files for co-located databases (if applicable)

#### Structure
- [ ] Valid YAML with all required sections (9 or 10)
- [ ] Sections in correct order
- [ ] Schema_info includes version/license/access/kw_search_tools/backend
- [ ] ShEx has minimal comments, covers all types
- [ ] Exactly 5 diverse RDF examples
- [ ] Exactly 7 SPARQL queries (2/3/2 distribution)
- [ ] Includes keyword filtering query
- [ ] Includes biological annotations query (if applicable)
- [ ] Cross-database queries section if shared endpoint (2-3 examples)
- [ ] Cross-references organized by pattern
- [ ] Architectural notes in YAML bullets
- [ ] All multiline strings use pipe syntax

#### Quality
- [ ] All SPARQL queries tested and work
- [ ] Cross-database queries tested (if included)
- [ ] Cross-database queries reference co-database MIE files (if included)
- [ ] 2-3 anti-patterns with wrong/correct versions
- [ ] 2-3 common errors with solutions
- [ ] Statistics: counts, coverage, cardinality, performance
- [ ] Cross-database performance documented (if applicable)
- [ ] Everything concise - no unnecessary content
- [ ] No sampling bias in documentation
- [ ] No premature conclusions

#### Cross-Database (if applicable)
- [ ] Identified all databases on same endpoint
- [ ] Retrieved MIE files for all co-located databases using `get_MIE_file()`
- [ ] Extracted graph URIs, entity types, properties from co-database MIE files
- [ ] Found at least 1 linking property to co-located databases
- [ ] 2-3 cross-database query examples tested and working
- [ ] Uses proper GRAPH clauses from co-database MIE files
- [ ] Uses correct entity types from co-database shape expressions
- [ ] Avoided anti-patterns from co-database MIE files
- [ ] Performance notes documented
- [ ] Documents which MIE files were referenced

### 7.2 Content Standards
- Descriptions are actionable and query-focused
- No redundant or excessive information
- All statistics based on actual measurements
- All examples use real data from the database
- Documentation enables effective querying
- Cross-database queries show practical value (if applicable)

## 8. Best Practices

### 8.1 Writing Style
- **Concise**: If it doesn't help query writing, omit it
- **Clear**: Use simple, direct language
- **Complete**: Cover all entity types and patterns
- **Correct**: All queries tested and verified
- **Consistent**: Use pipe syntax for all multiline strings

### 8.2 SPARQL Queries
- Always use appropriate LIMIT clauses
- Test with different LIMIT values if queries timeout
- Include comments for complex patterns
- Use meaningful variable names
- For Virtuoso: Use `bif:contains` for keyword search
- For cross-database: Use explicit GRAPH clauses

### 8.3 Coverage
- Document ALL entity types, not just common ones
- Include rare but important patterns
- Note data quality issues that affect querying
- Provide workarounds for known limitations
- Document cross-database opportunities (if applicable)

### 8.4 Cross-Database Queries
- Reference co-located database MIE files before creating queries
- Use graph URIs exactly as documented in MIE files
- Follow entity type conventions from co-database schemas
- Apply anti-pattern lessons from co-database documentation
- Document practical use cases, not forced integrations

## 9. Common Pitfalls

### 9.1 Discovery Phase
- ❌ Sampling bias: First 50 results don't represent entire database
- ❌ Premature conclusions: Timeout ≠ "data doesn't exist"
- ❌ Incomplete coverage: Only documenting obvious entity types
- ❌ Missing error guidance: Not testing what fails
- ❌ Ignoring cross-database opportunities: Not exploring shared endpoints
- ❌ Not retrieving co-database MIE files: Creating queries without reference information

### 9.2 Documentation Phase
- ❌ Excessive comments in ShEx
- ❌ Wrong number of examples (must be exactly 5 and 7)
- ❌ Untested SPARQL queries
- ❌ Cross-database queries in regular SPARQL examples section
- ❌ Prose paragraphs in architectural_notes
- ❌ Fabricated RDF examples
- ❌ Not using pipe syntax for multiline strings
- ❌ Missing kw_search_tools or backend fields
- ❌ Incorrect graph URIs in cross-database queries

### 9.3 Quality Phase
- ❌ Not verifying all queries work
- ❌ Missing anti-patterns or common errors
- ❌ Incomplete statistics
- ❌ Invalid YAML syntax
- ❌ Cross-database queries not tested
- ❌ Missing cross-database section when endpoint is shared
- ❌ Not documenting MIE file references for cross-database queries

## 10. Success Criteria

An MIE file is considered complete and compliant when:

1. **Valid YAML** with all required sections in correct order (9 or 10 depending on shared endpoint)
2. **Complete discovery**: All entity types documented
3. **Tested queries**: All 7 SPARQL queries work correctly
4. **Cross-database queries**: 2-3 examples if shared endpoint, properly tested and documented
5. **Correct counts**: Exactly 5 RDF examples, exactly 7 queries, 2-3 anti-patterns, 2-3 errors
6. **Comprehensive shapes**: ShEx covers ALL major entity types
7. **Proper organization**: Cross-references by pattern, notes in bullets
8. **Quality metrics**: Counts, coverage, cardinality, performance (including cross-database if applicable)
9. **Error prevention**: Anti-patterns and common errors documented
10. **Metadata complete**: Version, license, access, keyword search tools, backend information
11. **Actionable content**: Everything helps with query writing
12. **Consistent formatting**: All multiline strings use pipe (|) syntax
13. **MIE file references**: Cross-database queries document which MIE files were consulted

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024 | Initial specification |
| 1.1 | 2025-01-17 | Added cross_database_queries section, kw_search_tools field, pipe syntax requirement, backend field, MIE file reference guidance |

## 12. References

### 12.1 Related Standards
- **ShEx**: Shape Expressions Language (https://shex.io/)
- **SPARQL**: SPARQL 1.1 Query Language (W3C Recommendation)
- **YAML**: YAML Ain't Markup Language (https://yaml.org/)
- **RDF**: Resource Description Framework (W3C Recommendation)

### 12.2 Tools
- `get_sparql_endpoints()` - Get available SPARQL endpoints and keyword search APIs
- `get_graph_list(dbname)` - List named graphs
- `get_sparql_example(dbname)` - Get example query
- `run_sparql(dbname, query)` - Execute SPARQL (single database)
- `run_sparql(endpoint_name=endpoint, query)` - Execute SPARQL (cross-database)
- `get_shex(dbname)` - Retrieve ShEx schema
- `get_MIE_file(dbname)` - Retrieve existing MIE (CRITICAL for cross-database queries)
- `save_MIE_file(dbname, content)` - Save MIE file

### 12.3 Keyword Search APIs
**Dedicated Tools:**
- `search_uniprot_entity(query, limit=20)`
- `search_pdb_entity(db, query, limit=20)` - db="pdb"|"cc"|"prd"
- `search_chembl_molecule(query, limit=20)`, `search_chembl_target(query, limit=20)`
- `search_reactome_entity(query, species=None, types=None, rows=30)`
- `search_rhea_entity(query, limit=100)`
- `search_mesh_entity(query, limit=10)`

**OLS4:**
- `OLS4:searchClasses(query, ontologyId=None, pageSize, pageNum)` - For ChEBI, GO, Mondo, NANDO

**NCBI:**
- `ncbi_esearch(database, query, max_results=20)` - For PubChem, Taxonomy, ClinVar, PubMed, NCBIGene, MedGen

**SPARQL-Only:**
- Use `run_sparql()` with `bif:contains` pattern for keyword search (Virtuoso backend)

## 13. Appendix A: Complete Template

```yaml
schema_info:
  title: [DATABASE_NAME]
  description: |
    [3-5 sentences covering: contents, ALL entity types, use cases, features]
  endpoint: https://rdfportal.org/example/sparql
  base_uri: http://example.org/
  graphs:
    - http://example.org/dataset
    - http://example.org/ontology
  kw_search_tools:
    - [search_tool_name]  # e.g., search_uniprot_entity, OLS4:searchClasses, ncbi_esearch, or "sparql"
  version:
    mie_version: "1.1"
    mie_created: "YYYY-MM-DD"
    data_version: "Release YYYY.MM"
    update_frequency: "Monthly"
  license:
    data_license: "License name"
    license_url: "https://..."
  access:
    rate_limiting: "100 queries/min"
    max_query_timeout: "60 seconds"
    backend: "Virtuoso"  # or other triple store

shape_expressions: |
  PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  
  <EntityShape> {
    a [ schema:Type ] ;
    schema:property xsd:string ;
    schema:optional xsd:string ?
  }

sample_rdf_entries:
  - title: [Descriptive title]
    description: [1-2 sentences]
    rdf: |
      [Real RDF from database]
  - title: [Descriptive title]
    description: [1-2 sentences]
    rdf: |
      [Real RDF from database]
  - title: [Descriptive title]
    description: [1-2 sentences]
    rdf: |
      [Real RDF from database]
  - title: [Descriptive title]
    description: [1-2 sentences]
    rdf: |
      [Real RDF from database]
  - title: [Descriptive title]
    description: [1-2 sentences]
    rdf: |
      [Real RDF from database]

sparql_query_examples:
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: basic
    sparql: |
      [Tested query]
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: basic
    sparql: |
      [Tested query]
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: intermediate
    sparql: |
      [Tested query]
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: intermediate
    sparql: |
      [Tested query]
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: intermediate
    sparql: |
      [Tested query]
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: advanced
    sparql: |
      [Tested query]
  - title: [What it does]
    description: |
      [Context]
    question: [Natural language]
    complexity: advanced
    sparql: |
      [Tested query]

# ONLY include this section if database shares endpoint with 2+ others
cross_database_queries:
  shared_endpoint: [endpoint_name]  # e.g., ebi, sib, primary, ncbi
  co_located_databases:
    - [database1]
    - [database2]
  examples:
    - title: [Integration goal]
      description: |
        [Why useful - 2-3 sentences]
      databases_used:
        - [database1]
        - [database2]
      complexity: intermediate  # or advanced
      sparql: |
        # Prefixes from database MIE files
        PREFIX db1: <http://example1.org/>
        PREFIX db2: <http://example2.org/>
        
        SELECT ?entity1 ?entity2
        WHERE {
          # Graph URI from database1 MIE file
          GRAPH <http://example1.org/dataset> {
            ?entity1 a db1:Type ;
                     db1:links ?entity2 .
          }
          # Graph URI from database2 MIE file
          GRAPH <http://example2.org/dataset> {
            ?entity2 a db2:Type .
          }
        }
        LIMIT 10
      notes: |
        - Referenced MIE files: database1.yaml, database2.yaml
        - Graph URIs from respective schema_info.graphs
        - Entity types from respective shape_expressions
        - Performance: [timing]
        - Use case: [application]

cross_references:
  - pattern: rdfs:seeAlso
    description: |
      [How external links work]
    databases:
      category_name:
        - Database1 (~XX%)
        - Database2 (~YY%)
    sparql: |
      [Representative query]

architectural_notes:
  schema_design:
    - [Entity relationships]
    - [Design patterns]
  performance:
    - [Optimization tips]
    - [Query hints]
  data_integration:
    - [Cross-reference patterns]
    - [Cross-database opportunities if applicable]
    - [External links]
  data_quality:
    - [Data quirks]
    - [Known issues]

data_statistics:
  total_entity_type1: count
  total_entity_type2: count
  coverage:
    property1_coverage: "~XX%"
    property2_coverage: ">YY%"
  cardinality:
    avg_relationship1: X.X
    avg_relationship2: Y.Y
  performance_characteristics:
    - "Query type A: <1s for N results"
    - "Query type B: timeout at LIMIT 10000"
    - "Cross-database query performance (if applicable)"
  data_quality_notes:
    - "Issue description"

anti_patterns:
  - title: "Common mistake 1"
    problem: "Why it's wrong"
    wrong_sparql: |
      # Bad query
    correct_sparql: |
      # Fixed query
    explanation: |
      What changed and why
  - title: "Common mistake 2"
    problem: "Why it's wrong"
    wrong_sparql: |
      # Bad query
    correct_sparql: |
      # Fixed query
    explanation: |
      What changed and why

common_errors:
  - error: "Error type 1"
    causes:
      - "Cause 1"
      - "Cause 2"
    solutions:
      - "Solution 1"
      - "Solution 2"
    example_fix: |
      # Before/after (optional)
  - error: "Error type 2"
    causes:
      - "Cause 1"
    solutions:
      - "Solution 1"
```

## 14. Appendix B: Validation Rules

### Structural Validation
1. File MUST be valid YAML
2. All required sections MUST be present (9 or 10 depending on shared endpoint)
3. Sections MUST be in specified order
4. All required fields MUST be populated
5. All multiline strings MUST use pipe (|) syntax

### Content Validation
1. `sample_rdf_entries` count = 5
2. `sparql_query_examples` count = 7
3. SPARQL complexity distribution = 2 basic, 3 intermediate, 2 advanced
4. `cross_database_queries` present if shared endpoint (2-3 examples)
5. `anti_patterns` count = 2 or 3
6. `common_errors` count = 2 or 3
7. All dates in ISO 8601 format
8. All URIs are valid
9. `kw_search_tools` field present
10. `backend` field present

### Query Validation
1. All SPARQL queries execute without syntax errors
2. All SPARQL queries return results (or documented as intentionally empty)
3. All queries have appropriate LIMIT clauses
4. No queries timeout (or timeout is documented)
5. Cross-database queries use correct graph URIs from referenced MIE files
6. Cross-database queries use correct entity types from co-database schemas

### Coverage Validation
1. All major entity types have ShEx shapes
2. Cross-references document all external databases found
3. Statistics include all major entity types
4. Anti-patterns address common real mistakes
5. Cross-database opportunities documented (if applicable)

### Reference Validation (for cross-database queries)
1. Co-located database MIE files were retrieved
2. Graph URIs match those in referenced MIE files
3. Entity types match those in referenced shape expressions
4. Notes document which MIE files were consulted

---

**Document Status**: Specification v1.1  
**Compliance**: REQUIRED for all MIE files  
**Principle**: Compact, Complete, Clear, Correct, Actionable  
**Key Addition**: Cross-database integration support for shared endpoints
