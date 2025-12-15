# MIE File Specification v1.0

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

## 2. File Structure

### 2.1 Required Sections
MIE files MUST contain exactly nine sections in the following order:

1. `schema_info` - Database metadata
2. `shape_expressions` - ShEx schemas
3. `sample_rdf_entries` - Example RDF data
4. `sparql_query_examples` - Tested queries
5. `cross_references` - External database links
6. `architectural_notes` - Design patterns
7. `data_statistics` - Quantitative metrics
8. `anti_patterns` - Common mistakes
9. `common_errors` - Error scenarios

### 2.2 Section Dependencies
- All sections are REQUIRED
- Sections MUST appear in the specified order
- No additional top-level sections permitted

## 3. Section Specifications

### 3.1 schema_info

#### 3.1.1 Purpose
Provides essential metadata about the RDF database.

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
  version:                         # REQUIRED: Version metadata
    mie_version: string            # REQUIRED: MIE spec version (e.g., "1.0")
    mie_created: date              # REQUIRED: ISO 8601 format (YYYY-MM-DD)
    data_version: string           # REQUIRED: Database version/release
    update_frequency: string       # REQUIRED: Update schedule
  license:                         # REQUIRED: Licensing information
    data_license: string           # REQUIRED: License name
    license_url: uri               # REQUIRED: License URL
  access:                          # REQUIRED: Access constraints
    rate_limiting: string          # REQUIRED: Query rate limits
    max_query_timeout: string      # REQUIRED: Timeout duration
    backend: string                # OPTIONAL: Triple store type (e.g., "Virtuoso")
```

#### 3.1.3 Constraints
- `description` MUST be 3-5 sentences
- `description` MUST document ALL major entity types
- All URIs MUST be valid and accessible
- `mie_created` MUST use ISO 8601 date format

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
    rdf: string                    # REQUIRED: Actual RDF from database
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
    description: string            # REQUIRED: Context and purpose
    question: string               # REQUIRED: Natural language question
    complexity: enum               # REQUIRED: basic | intermediate | advanced
    sparql: string                 # REQUIRED: Tested SPARQL query
```

#### 3.4.3 Requirements
- MUST contain EXACTLY 7 queries with the following distribution:
  - 2 queries with `complexity: basic`
  - 3 queries with `complexity: intermediate`
  - 2 queries with `complexity: advanced`
- MUST include at least one query with keyword filtering
- MUST include at least one query with biological annotations (if applicable)
- MUST NOT include cross-reference queries (those belong in `cross_references`)
- ALL queries MUST be tested and confirmed working

#### 3.4.4 Constraints
- Total count: EXACTLY 7 queries
- Complexity distribution: 2/3/2 (basic/intermediate/advanced)
- All queries MUST execute without errors
- Queries MUST use appropriate LIMIT clauses

#### 3.4.5 Complexity Guidelines
- **Basic**: Simple SELECT, single entity type, basic filters
- **Intermediate**: Multiple entity types, OPTIONAL patterns, aggregations
- **Advanced**: Complex joins, nested queries, sophisticated filtering

### 3.5 cross_references

#### 3.5.1 Purpose
Documents external database linkages organized by RDF pattern.

#### 3.5.2 Structure
```yaml
cross_references:
  - pattern: string                # REQUIRED: RDF property pattern
    description: string            # REQUIRED: How links work
    databases:                     # REQUIRED: Organized by category
      category_name:
        - database_name: coverage  # Format: "Database (~XX%)" or similar
    sparql: string                 # REQUIRED: Representative query
```

#### 3.5.3 Requirements
- Group by RDF pattern (e.g., `rdfs:seeAlso`, `owl:sameAs`, `skos:exactMatch`)
- List ALL external databases found
- Include coverage estimates where possible
- Provide working SPARQL query for each pattern

#### 3.5.4 Constraints
- Do NOT create separate entries for each individual database
- Organize by pattern, then categorize databases
- Include coverage percentages when available
- All SPARQL queries MUST be tested

### 3.6 architectural_notes

#### 3.6.1 Purpose
Documents design patterns, performance characteristics, and data quality issues.

#### 3.6.2 Structure
```yaml
architectural_notes:
  schema_design:
    - bullet point                 # REQUIRED: Design patterns
  performance:
    - bullet point                 # REQUIRED: Optimization tips
  data_integration:
    - bullet point                 # REQUIRED: Cross-reference patterns
  data_quality:
    - bullet point                 # REQUIRED: Data quirks and issues
```

#### 3.6.3 Requirements
- MUST use YAML bullet format (not prose paragraphs)
- MUST include all four subsections
- Each subsection MUST have at least one bullet point
- Content MUST be actionable and relevant to query writing

#### 3.6.4 Constraints
- No prose paragraphs
- Bullets MUST be concise (1-2 sentences each)
- Focus on information that helps with querying

### 3.7 data_statistics

#### 3.7.1 Purpose
Provides quantitative metrics about database contents and performance.

#### 3.7.2 Structure
```yaml
data_statistics:
  total_[entity_type]: integer     # REQUIRED: Entity counts
  coverage:                        # REQUIRED: Property completeness
    property_name: string          # Format: "~XX%" or ">XX%"
  cardinality:                     # REQUIRED: Relationship metrics
    avg_[relationship]: number     # Average cardinality
  performance_characteristics:     # REQUIRED: Query performance
    - observation                  # Tested observations
  data_quality_notes:              # OPTIONAL: Data issues
    - note                         # Quality concerns
```

#### 3.7.3 Requirements
- MUST include entity counts for all major types
- MUST include coverage statistics for important properties
- MUST include cardinality metrics for key relationships
- MUST include performance observations from actual testing
- MAY include data quality notes if relevant

#### 3.7.4 Constraints
- All statistics MUST be based on actual queries
- Coverage percentages should be approximate ranges
- Performance characteristics MUST be reproducible

### 3.8 anti_patterns

#### 3.8.1 Purpose
Documents common mistakes with corrected versions.

#### 3.8.2 Structure
```yaml
anti_patterns:
  - title: string                  # REQUIRED: Mistake description
    problem: string                # REQUIRED: Why it's wrong
    wrong_sparql: string           # REQUIRED: Incorrect query
    correct_sparql: string         # REQUIRED: Fixed query
    explanation: string            # REQUIRED: What changed
```

#### 3.8.3 Requirements
- MUST contain 2-3 examples
- Each MUST show both wrong and correct versions
- Both queries SHOULD be tested (wrong should fail/timeout, correct should work)
- Focus on mistakes that researchers actually make

#### 3.8.4 Constraints
- Count: 2-3 examples (not more, not less)
- Both `wrong_sparql` and `correct_sparql` MUST be provided
- Explanation MUST be clear and educational

### 3.9 common_errors

#### 3.9.1 Purpose
Documents error scenarios with causes and solutions.

#### 3.9.2 Structure
```yaml
common_errors:
  - error: string                  # REQUIRED: Error type/message
    causes:                        # REQUIRED: List of causes
      - cause                      # At least one cause
    solutions:                     # REQUIRED: List of solutions
      - solution                   # At least one solution
    example_fix: string            # OPTIONAL: Before/after code
```

#### 3.9.3 Requirements
- MUST contain 2-3 error scenarios
- Each MUST have at least one cause and one solution
- Focus on errors researchers actually encounter
- MAY include example fixes if helpful

#### 3.9.4 Constraints
- Count: 2-3 scenarios
- Each MUST have actionable solutions
- Causes MUST be specific and accurate

## 4. Discovery Requirements

### 4.1 Systematic Discovery Process
Before creating an MIE file, creators MUST:

1. Check for existing documentation (`get_MIE_file()`, `get_shex()`)
2. Query ontology graphs for ALL entity types
3. Explore multiple URI patterns
4. Sample instances for each discovered entity type
5. Verify findings across different query patterns

### 4.2 Avoiding Bias
- MUST NOT rely solely on first 50 results
- MUST query ontology graphs before sampling data
- MUST NOT assume timeouts mean "data doesn't exist"
- MUST explore multiple query strategies

### 4.3 Verification
All SPARQL queries in the MIE file MUST be:
- Actually executed against the database
- Confirmed to return valid results
- Tested with appropriate LIMIT values

## 5. Compliance Checking

### 5.1 Existing MIE File Evaluation
When an existing MIE file is found, evaluate against:

#### Structure & Format
- [ ] Valid YAML syntax
- [ ] All 9 required sections present
- [ ] Sections in correct order
- [ ] Version/license/access metadata in schema_info

#### Sample RDF Entries
- [ ] Exactly 5 examples
- [ ] Covers diverse categories
- [ ] Each has 1-2 sentence description

#### SPARQL Query Examples
- [ ] Exactly 7 queries
- [ ] Correct complexity distribution (2/3/2)
- [ ] Includes keyword filtering query
- [ ] Includes biological annotations query (if applicable)
- [ ] No cross-reference queries
- [ ] All tested and working

#### Shape Expressions
- [ ] Minimal comments (only non-obvious)
- [ ] Covers ALL major entity types

#### Other Sections
- [ ] Cross-references organized by pattern
- [ ] All external databases listed
- [ ] Architectural notes in YAML bullets
- [ ] Statistics include counts, coverage, cardinality
- [ ] 2-3 anti-patterns with both versions
- [ ] 2-3 common errors with solutions

#### Compliance Threshold
- **≥90% pass**: Update existing file
- **<90% pass**: Create new file from scratch

## 6. Quality Assurance

### 6.1 Pre-Finalization Checklist

#### Discovery
- [ ] Queried ontology graphs for all entity types
- [ ] Explored multiple URI patterns
- [ ] Documented ALL major entity types
- [ ] Verified findings with multiple query strategies

#### Structure
- [ ] Valid YAML with all 9 required sections
- [ ] Sections in correct order
- [ ] Schema_info includes version/license/access
- [ ] ShEx has minimal comments, covers all types
- [ ] Exactly 5 diverse RDF examples
- [ ] Exactly 7 SPARQL queries (2/3/2 distribution)
- [ ] Includes keyword filtering query
- [ ] Includes biological annotations query
- [ ] Cross-references organized by pattern
- [ ] Architectural notes in YAML bullets

#### Quality
- [ ] All SPARQL queries tested and work
- [ ] 2-3 anti-patterns with wrong/correct versions
- [ ] 2-3 common errors with solutions
- [ ] Statistics: counts, coverage, cardinality, performance
- [ ] Everything concise—no unnecessary content
- [ ] No sampling bias in documentation
- [ ] No premature conclusions

### 6.2 Content Standards
- Descriptions are actionable and query-focused
- No redundant or excessive information
- All statistics based on actual measurements
- All examples use real data from the database
- Documentation enables effective querying

## 7. Best Practices

### 7.1 Writing Style
- **Concise**: If it doesn't help query writing, omit it
- **Clear**: Use simple, direct language
- **Complete**: Cover all entity types and patterns
- **Correct**: All queries tested and verified

### 7.2 SPARQL Queries
- Always use appropriate LIMIT clauses
- Test with different LIMIT values if queries timeout
- Include comments for complex patterns
- Use meaningful variable names

### 7.3 Coverage
- Document ALL entity types, not just common ones
- Include rare but important patterns
- Note data quality issues that affect querying
- Provide workarounds for known limitations

## 8. Common Pitfalls

### 8.1 Discovery Phase
- ❌ Sampling bias: First 50 results don't represent entire database
- ❌ Premature conclusions: Timeout ≠ "data doesn't exist"
- ❌ Incomplete coverage: Only documenting obvious entity types
- ❌ Missing error guidance: Not testing what fails

### 8.2 Documentation Phase
- ❌ Excessive comments in ShEx
- ❌ Wrong number of examples (must be exactly 5 and 7)
- ❌ Untested SPARQL queries
- ❌ Cross-reference queries in SPARQL examples section
- ❌ Prose paragraphs in architectural_notes
- ❌ Fabricated RDF examples

### 8.3 Quality Phase
- ❌ Not verifying all queries work
- ❌ Missing anti-patterns or common errors
- ❌ Incomplete statistics
- ❌ Invalid YAML syntax

## 9. Success Criteria

An MIE file is considered complete and compliant when:

1. **Valid YAML** with all 9 sections in correct order
2. **Complete discovery**: All entity types documented
3. **Tested queries**: All 7 SPARQL queries work correctly
4. **Correct counts**: Exactly 5 RDF examples, exactly 7 queries, 2-3 anti-patterns, 2-3 errors
5. **Comprehensive shapes**: ShEx covers ALL major entity types
6. **Proper organization**: Cross-references by pattern, notes in bullets
7. **Quality metrics**: Counts, coverage, cardinality, performance included
8. **Error prevention**: Anti-patterns and common errors documented
9. **Metadata complete**: Version, license, and access information provided
10. **Actionable content**: Everything helps with query writing

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | [Date] | Initial specification |

## 11. References

### 11.1 Related Standards
- **ShEx**: Shape Expressions Language (https://shex.io/)
- **SPARQL**: SPARQL 1.1 Query Language (W3C Recommendation)
- **YAML**: YAML Ain't Markup Language (https://yaml.org/)
- **RDF**: Resource Description Framework (W3C Recommendation)

### 11.2 Tools
- `get_sparql_endpoints()` - Get available SPARQL endpoints
- `get_graph_list(dbname)` - List named graphs
- `get_sparql_example(dbname)` - Get example query
- `run_sparql(dbname, query)` - Execute SPARQL
- `get_shex(dbname)` - Retrieve ShEx schema
- `get_MIE_file(dbname)` - Retrieve existing MIE
- `save_MIE_file(dbname, content)` - Save MIE file

## 12. Appendix A: Complete Template

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
    description: [Context]
    question: [Natural language]
    complexity: basic
    sparql: |
      [Tested query]
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: basic
    sparql: |
      [Tested query]
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: intermediate
    sparql: |
      [Tested query]
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: intermediate
    sparql: |
      [Tested query]
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: intermediate
    sparql: |
      [Tested query]
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: advanced
    sparql: |
      [Tested query]
  - title: [What it does]
    description: [Context]
    question: [Natural language]
    complexity: advanced
    sparql: |
      [Tested query]

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
  data_quality_notes:
    - "Issue description"

anti_patterns:
  - title: "Common mistake 1"
    problem: "Why it's wrong"
    wrong_sparql: |
      # Bad query
    correct_sparql: |
      # Fixed query
    explanation: "What changed"
  - title: "Common mistake 2"
    problem: "Why it's wrong"
    wrong_sparql: |
      # Bad query
    correct_sparql: |
      # Fixed query
    explanation: "What changed"

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

## 13. Appendix B: Validation Rules

### Structural Validation
1. File MUST be valid YAML
2. All 9 sections MUST be present
3. Sections MUST be in specified order
4. All required fields MUST be populated

### Content Validation
1. `sample_rdf_entries` count = 5
2. `sparql_query_examples` count = 7
3. SPARQL complexity distribution = 2 basic, 3 intermediate, 2 advanced
4. `anti_patterns` count = 2 or 3
5. `common_errors` count = 2 or 3
6. All dates in ISO 8601 format
7. All URIs are valid

### Query Validation
1. All SPARQL queries execute without syntax errors
2. All SPARQL queries return results (or documented as intentionally empty)
3. All queries have appropriate LIMIT clauses
4. No queries timeout (or timeout is documented)

### Coverage Validation
1. All major entity types have ShEx shapes
2. Cross-references document all external databases found
3. Statistics include all major entity types
4. Anti-patterns address common real mistakes

---

**Document Status**: Specification v1.0  
**Compliance**: REQUIRED for all MIE files  
**Principle**: Compact, Complete, Clear, Correct, Actionable