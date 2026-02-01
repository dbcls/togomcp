# Gene Ontology (GO) Exploration Report

**Date**: January 31, 2026
**Session**: 1

## Executive Summary

The Gene Ontology (GO) database is a fundamental controlled vocabulary for describing gene and gene product attributes. It contains approximately 48,165 terms organized into three namespaces: biological_process (30,804 terms), molecular_function (12,793 terms), and cellular_component (4,568 terms).

**Key Capabilities Requiring Deep Knowledge**:
- Cross-database integration with MONDO, MeSH, Taxonomy via keyword-based matching (no direct semantic links)
- Gene annotation queries via TogoID relation graphs (ncbigene-go)
- Performance optimization using bif:contains instead of REGEX
- Critical requirement for STR() function in namespace filtering
- Mandatory FROM clause specification to avoid inconsistent results

**Major Integration Opportunities**:
- GO ↔ NCBI Gene (via TogoID relation graph)
- GO ↔ MONDO (keyword-based, same endpoint)
- GO ↔ MeSH (keyword-based, same endpoint)
- GO ↔ Taxonomy (same endpoint)
- Cross-references to Reactome, KEGG, EC numbers

**Most Valuable Patterns Discovered**:
1. Type restriction (^^xsd:string) required for namespace filters in cross-database queries
2. bif:contains provides 10-100x speedup over REGEX
3. FROM clause prevents duplicate/inconsistent results
4. TogoID graphs enable gene-to-GO annotation queries

**Recommended Question Types**:
- Ontology hierarchy navigation (ancestors, descendants)
- Keyword-based term discovery
- Gene annotation counts and lookups
- Cross-database integration queries

## Database Overview

### Purpose and Scope
The Gene Ontology provides a controlled vocabulary of terms for describing gene and gene product attributes across all organisms. GO enables standardized annotation of gene products and supports computational analysis of biological data.

### Key Data Types and Entities
- **GO Terms**: Unique identifiers in format GO:NNNNNNN
- **Three Namespaces**:
  - biological_process: 30,804 terms (biological objectives)
  - molecular_function: 12,793 terms (molecular activities)
  - cellular_component: 4,568 terms (cellular locations)
- **Deprecated Terms**: ~11,905 (marked with owl:deprecated)
- **Hierarchical Structure**: rdfs:subClassOf (DAG - directed acyclic graph)
- **Synonyms**: Four types (exact, related, narrow, broad)
- **Cross-references**: Links to 20+ external databases

### Dataset Size and Performance Considerations
- Total GO terms: ~48,165
- Deprecated terms: ~25%
- Terms with definitions: ~100%
- Terms with synonyms: ~80%
- Terms with cross-references: ~52%
- Backend: Virtuoso
- Endpoint: https://rdfportal.org/primary/sparql
- Shared with: mesh, taxonomy, mondo, nando, bacdive, mediadive

### Available Access Methods
1. **OLS4 API Tools**:
   - searchClasses: Keyword search with pagination
   - getDescendants: Navigate ontology hierarchy downward
   - getAncestors: Navigate ontology hierarchy upward
   - fetch: Retrieve specific entity by ID

2. **SPARQL Queries**:
   - Direct queries on GO graph
   - Cross-database queries on primary endpoint
   - TogoID relation graphs for gene annotations

3. **TogoID**:
   - ID conversion: ncbigene → go
   - Relation graph: http://rdfportal.org/dataset/togoid/relation/ncbigene-go

---

## Structure Analysis

### Performance Strategies

**Strategy 1: FROM Clause Specification**
- **Why needed**: Without FROM clause, queries may return duplicate or inconsistent results from multiple graphs
- **When to apply**: ALL GO SPARQL queries
- **Performance impact**: Critical - prevents query confusion and improves consistency
- **Example**: `FROM <http://rdfportal.org/ontology/go>`

**Strategy 2: Use bif:contains Instead of REGEX**
- **Why needed**: REGEX is slow on large text fields; bif:contains uses Virtuoso's full-text index
- **When to apply**: All keyword searches on labels and definitions
- **Performance impact**: 10-100x faster than REGEX
- **Example**: `?label bif:contains "'kinase'" option (score ?sc)`

**Strategy 3: STR() for Namespace Filtering**
- **Why needed**: Datatype mismatch causes namespace filters to return empty results
- **When to apply**: All namespace comparisons
- **Performance impact**: Critical - without STR(), filters fail silently
- **Example**: `FILTER(STR(?namespace) = "molecular_function")`

**Strategy 4: Type Restriction for Cross-Database Queries**
- **Why needed**: ^^xsd:string type restriction required for namespace properties in cross-database contexts
- **When to apply**: Cross-database queries filtering by namespace
- **Performance impact**: Critical - empty results without proper typing
- **Example**: `oboinowl:hasOBONamespace "cellular_component"^^xsd:string`

**Strategy 5: STRSTARTS Filter for GO Terms**
- **Why needed**: Database contains many non-GO ontology terms
- **When to apply**: All GO term queries
- **Performance impact**: Reduces result set, avoids processing irrelevant terms
- **Example**: `FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))`

**Strategy 6: LIMIT for Aggregation Queries**
- **Why needed**: Aggregating over 48,000+ terms can timeout
- **When to apply**: COUNT, GROUP BY operations
- **Performance impact**: Prevents timeout
- **Example**: Add `LIMIT` or filter by namespace first

### Common Pitfalls

**Pitfall 1: Missing FROM Clause**
- **Cause**: Queries without FROM clause search all graphs
- **Symptoms**: Duplicate results, inconsistent counts, potential timeout
- **Solution**: Always specify `FROM <http://rdfportal.org/ontology/go>`
- **Example before**: Returns duplicated namespace counts (biological_process: 30804, 8145)
- **Example after**: Returns single correct count per namespace

**Pitfall 2: Namespace Filter Without STR()**
- **Cause**: Datatype mismatch between query string and stored value
- **Symptoms**: Empty results when filtering by namespace
- **Solution**: Use `FILTER(STR(?namespace) = "molecular_function")`
- **Example before**: `FILTER(?namespace = "molecular_function")` → 0 results
- **Example after**: `FILTER(STR(?namespace) = "molecular_function")` → 12,793 results

**Pitfall 3: REGEX Instead of bif:contains**
- **Cause**: REGEX doesn't use full-text indexing
- **Symptoms**: Slow queries, potential timeout for complex patterns
- **Solution**: Use `?label bif:contains "'keyword'" option (score ?sc)`
- **Performance difference**: Seconds vs. potential timeout

**Pitfall 4: Cross-Database Namespace Filter Missing Type**
- **Cause**: Type mismatch in cross-database GRAPH context
- **Symptoms**: Empty results in cross-database queries
- **Solution**: Add `^^xsd:string` to namespace literal
- **Example before**: `oboinowl:hasOBONamespace "cellular_component"` → empty
- **Example after**: `oboinowl:hasOBONamespace "cellular_component"^^xsd:string` → results

**Pitfall 5: Incorrect Boolean Syntax in bif:contains**
- **Cause**: Missing quotes or parentheses in complex search expressions
- **Symptoms**: Syntax errors or unexpected results
- **Solution**: Use `"('term1' AND 'term2')"` syntax
- **Example**: `bif:contains "('phosph*' AND NOT 'kinase')"`

### Data Organization

**Main Graph**: `http://rdfportal.org/ontology/go`
- GO terms with all properties
- Hierarchical relationships (rdfs:subClassOf)
- Synonyms, definitions, cross-references
- Deprecation flags

**GOA Graph**: `http://purl.jp/bio/11/goa`
- Ontology metadata (version info, titles)
- Not primary data storage for annotations

**TogoID Relation Graphs**:
- `http://rdfportal.org/dataset/togoid/relation/ncbigene-go`: Gene-to-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/ensembl_transcript-go`: Ensembl transcript-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/chembl_target-go`: ChEMBL target-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/pdb-go`: PDB structure-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/rhea-go`: Reaction-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/interpro-go`: InterPro-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/reactome_pathway-go`: Reactome pathway-GO mappings
- `http://rdfportal.org/dataset/togoid/relation/reactome_reaction-go`: Reactome reaction-GO mappings

### Cross-Database Integration Points

**Integration 1: GO → NCBI Gene (via TogoID)**
- Connection relationship: Gene annotation with GO terms
- Join point: togoid:TIO_000004 property
- Graph: `http://rdfportal.org/dataset/togoid/relation/ncbigene-go`
- Required information: GO term URI, NCBI Gene ID
- Pre-filtering needed: Filter GO terms by keyword before join
- Knowledge required: TogoID property, graph URI, GO term format
- **Tested**: Successfully counted 29,615 genes annotated with autophagy

**Integration 2: GO → MONDO (keyword-based)**
- Connection relationship: Keyword matching between process/component and disease
- Join point: bif:contains on labels in both databases
- Same endpoint: primary
- Pre-filtering needed: Filter by namespace, use bif:contains
- Knowledge required: MONDO graph URI, owl:Class type, MONDO prefix filter
- **Tested**: Successfully found mitochondria-related GO terms with lysosomal diseases

**Integration 3: GO → MeSH (keyword-based)**
- Connection relationship: Keyword matching between biological terms and medical terminology
- Join point: bif:contains on labels in both databases
- Same endpoint: primary
- Pre-filtering needed: Use bif:contains with specific keywords
- Knowledge required: MeSH graph URI, meshv:TopicalDescriptor type
- **Tested**: Successfully found insulin-related GO terms with MeSH descriptors

**Integration 4: GO Cross-References → External Databases**
- Connection relationship: hasDbXref property links to external resources
- Supported databases: Reactome, KEGG, EC, Wikipedia, NIF_Subcellular, MESH, SNOMEDCT
- Query pattern: Filter xrefs by prefix (e.g., "Reactome:", "EC:")
- **Tested**: Successfully found kinase terms with EC numbers

---

## Complex Query Patterns Tested

### Pattern 1: Namespace Filtering with STR() Function

**Purpose**: Filter GO terms by their namespace (biological_process, molecular_function, cellular_component)

**Category**: Error-Avoidance, Structured Query

**Naive Approach (without proper knowledge)**:
```sparql
FILTER(?namespace = "molecular_function")
```

**What Happened**:
- Error message: None (silent failure)
- Timeout: No
- Results: 0 (empty result set)
- Why it failed: Datatype mismatch between query string literal and stored value

**Correct Approach (using proper pattern)**:
```sparql
FILTER(STR(?namespace) = "molecular_function")
```

**What Knowledge Made This Work**:
- Key Insight: GO MIE documents STR() requirement for namespace comparisons
- Performance improvement: N/A (correctness issue, not performance)
- Why it works: STR() converts namespace value to plain string for comparison

**Results Obtained**:
- Without STR(): 0 results
- With STR(): 12,793 molecular_function terms

**Natural Language Question Opportunities**:
1. "How many molecular function terms exist in Gene Ontology?" - Category: Completeness
2. "Find all GO cellular component terms related to mitochondria" - Category: Structured Query

---

### Pattern 2: FROM Clause Requirement

**Purpose**: Ensure consistent, non-duplicated results from GO database

**Category**: Error-Avoidance, Performance-Critical

**Naive Approach (without proper knowledge)**:
```sparql
SELECT ?namespace (COUNT(?go) as ?count)
WHERE {
  ?go oboinowl:hasOBONamespace ?namespace .
}
GROUP BY ?namespace
```

**What Happened**:
- Error message: None
- Timeout: No
- Results: Duplicated counts (biological_process: 30804, 8145 separately)
- Why it failed: Query searched all graphs, returning results from multiple storage locations

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?namespace (COUNT(?go) as ?count)
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go oboinowl:hasOBONamespace ?namespace .
}
GROUP BY ?namespace
```

**What Knowledge Made This Work**:
- Key Insight: MIE file specifies graph URI is CRITICAL
- Performance improvement: Consistency and correctness
- Why it works: FROM clause restricts query to correct graph

**Results Obtained**:
- Without FROM: Inconsistent duplicated counts
- With FROM: biological_process: 30,804 / molecular_function: 12,793 / cellular_component: 4,568

**Natural Language Question Opportunities**:
1. "How many terms are in each GO namespace?" - Category: Completeness
2. "What is the distribution of GO terms across biological domains?" - Category: Completeness

---

### Pattern 3: bif:contains for Keyword Search

**Purpose**: Efficiently search GO terms by keyword

**Category**: Performance-Critical, Structured Query

**Naive Approach (without proper knowledge)**:
```sparql
FILTER(REGEX(?label, "kinase", "i"))
```

**What Happened**:
- Error message: None
- Timeout: Potential for complex queries
- Performance: Slow (full table scan)
- Why it failed: REGEX doesn't use full-text indexing

**Correct Approach (using proper pattern)**:
```sparql
?label bif:contains "'kinase'" option (score ?sc)
```

**What Knowledge Made This Work**:
- Key Insight: MIE documents bif:contains with Virtuoso full-text index
- Performance improvement: 10-100x faster
- Why it works: Uses indexed full-text search

**Results Obtained**:
- Both approaches return correct results
- bif:contains provides relevance scoring (option score)
- Supports wildcards: `'phosph*'`
- Supports boolean operators: `('kinase' AND 'protein')`

**Natural Language Question Opportunities**:
1. "Find all kinase-related molecular functions in Gene Ontology" - Category: Structured Query
2. "What GO terms are related to apoptosis?" - Category: Specificity

---

### Pattern 4: Cross-Database Query with Type Restriction

**Purpose**: Query GO and MONDO together for biological process-disease relationships

**Category**: Integration, Error-Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
GRAPH <http://rdfportal.org/ontology/go> {
  ?goTerm oboinowl:hasOBONamespace "cellular_component" .
}
```

**What Happened**:
- Error message: None
- Timeout: No
- Results: Empty
- Why it failed: Missing type restriction in cross-database context

**Correct Approach (using proper pattern)**:
```sparql
GRAPH <http://rdfportal.org/ontology/go> {
  ?goTerm oboinowl:hasOBONamespace "cellular_component"^^xsd:string .
}
```

**What Knowledge Made This Work**:
- Key Insight: MIE Strategy 9 - type restriction required for Virtuoso
- Performance improvement: N/A (correctness issue)
- Why it works: Explicit type ensures correct datatype matching

**Results Obtained**:
- Successfully retrieved mitochondria-related GO terms with lysosomal disease terms
- Cross-product requires careful LIMIT to prevent timeout

**Natural Language Question Opportunities**:
1. "Which GO cellular components are related to lysosomal storage diseases?" - Category: Integration
2. "Find autophagy-related biological processes that connect to mitochondrial diseases" - Category: Integration

---

### Pattern 5: TogoID Integration for Gene Annotations

**Purpose**: Find genes annotated with specific GO terms

**Category**: Integration, Structured Query

**Query Pattern**:
```sparql
GRAPH <http://rdfportal.org/dataset/togoid/relation/ncbigene-go> {
  ?geneId togoid:TIO_000004 ?goTerm .
}
```

**What Knowledge Made This Work**:
- Key Insight: TogoID relation graphs provide pre-computed gene-GO mappings
- Required knowledge: Graph URI, togoid:TIO_000004 property
- Performance: Fast (1-2 seconds) due to pre-computed mappings

**Results Obtained**:
- Counted 29,615 genes annotated with autophagy (GO:0006914)
- Can filter GO terms by keyword before join for better performance

**Natural Language Question Opportunities**:
1. "How many genes are annotated with the autophagy GO term?" - Category: Completeness
2. "Which genes are involved in mitochondrial autophagy?" - Category: Integration

---

### Pattern 6: Hierarchical Navigation

**Purpose**: Navigate GO term hierarchy (ancestors/descendants)

**Category**: Structured Query

**OLS4 API Approach**:
- getDescendants: Returns all child terms
- getAncestors: Returns all parent terms
- Provides complete hierarchy information

**SPARQL Approach**:
```sparql
SELECT ?child ?childLabel ?parent ?parentLabel
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?child rdfs:subClassOf ?parent .
  ?child rdfs:label ?childLabel .
  ?parent rdfs:label ?parentLabel .
  FILTER(?child = obo:GO_0006914)
}
```

**Results Obtained**:
- autophagy (GO:0006914) has 2 direct parents: catabolic process, process utilizing autophagic mechanism
- 25 descendant terms of autophagy (macroautophagy, mitophagy, etc.)

**Natural Language Question Opportunities**:
1. "What are the subtypes of autophagy?" - Category: Completeness
2. "What is the parent process of mitophagy?" - Category: Precision

---

### Pattern 7: Cross-Reference Query

**Purpose**: Find GO terms linked to external databases

**Category**: Integration, Specificity

**Query Pattern**:
```sparql
SELECT ?go ?label ?xref
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go rdfs:label ?label ;
      oboinowl:hasDbXref ?xref .
  FILTER(STRSTARTS(?xref, "Reactome:"))
}
```

**Results Obtained**:
- Found GO terms linked to Reactome pathways
- Cross-references include: Reactome, KEGG_REACTION, EC, Wikipedia, NIF_Subcellular, MESH, SNOMEDCT

**Natural Language Question Opportunities**:
1. "Which GO molecular functions have EC (enzyme classification) numbers?" - Category: Integration
2. "What GO biological processes have Reactome pathway cross-references?" - Category: Integration

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. **Search**: "autophagy"
   - Found: GO:0006914 - autophagy (biological_process)
   - Usage: Questions about autophagy hierarchy, descendants, gene annotations

2. **Search**: "kinase"
   - Found: GO:0004672 - protein kinase activity (molecular_function)
   - Usage: Questions about enzyme functions, molecular activities

3. **Search**: "nucleus"
   - Found: GO:0005634 - nucleus (cellular_component)
   - Usage: Questions about cellular locations, synonyms

4. **Search**: "mitochondria"
   - Found: GO:0005741 - mitochondrial outer membrane
   - Usage: Cross-database questions with diseases

5. **Search**: "insulin"
   - Found: Multiple insulin-related terms
   - Usage: MeSH integration questions

6. **Namespace count query**
   - Found: biological_process (30,804), molecular_function (12,793), cellular_component (4,568)
   - Usage: Completeness questions about GO structure

7. **Deprecated term count**
   - Found: 11,905 deprecated terms
   - Usage: Questions about data quality

8. **Gene annotation count**
   - Found: 29,615 genes annotated with autophagy
   - Usage: Integration questions with NCBI Gene

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "How many genes are annotated with the autophagy biological process?"
   - Databases involved: GO, NCBI Gene (via TogoID)
   - Knowledge Required: TogoID graph URI, togoid:TIO_000004 property, GO term URI format
   - Category: Integration / Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

2. "Which genes have mitochondrial autophagy annotations?"
   - Databases involved: GO, NCBI Gene (via TogoID)
   - Knowledge Required: TogoID integration, GO:0000422 (autophagy of mitochondrion)
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

3. "Find GO cellular components that might relate to lysosomal storage diseases"
   - Databases involved: GO, MONDO
   - Knowledge Required: Cross-database GRAPH URIs, ^^xsd:string type restriction, bif:contains
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

4. "Which GO biological processes are related to insulin and also appear in medical terminology databases?"
   - Databases involved: GO, MeSH
   - Knowledge Required: MeSH graph URI, meshv:TopicalDescriptor type, bif:contains
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

5. "Find GO kinase activities that have enzyme classification numbers"
   - Databases involved: GO, EC (via cross-references)
   - Knowledge Required: hasDbXref property, EC: prefix filter
   - Category: Integration
   - Difficulty: Easy
   - Pattern Reference: Pattern 7

**Performance-Critical Questions**:

6. "How many GO terms are in each namespace (biological process, molecular function, cellular component)?"
   - Database: GO
   - Knowledge Required: FROM clause, STRSTARTS filter, namespace values
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

7. "Find all GO molecular function terms that contain 'kinase' in their label"
   - Database: GO
   - Knowledge Required: bif:contains, STR() for namespace filter, FROM clause
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Patterns 1, 2, 3

8. "How many deprecated GO terms exist in the database?"
   - Database: GO
   - Knowledge Required: owl:deprecated property, FROM clause
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 2

**Error-Avoidance Questions**:

9. "List all cellular component terms related to mitochondria"
   - Database: GO
   - Knowledge Required: STR() for namespace filter, bif:contains for keyword
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Patterns 1, 3

10. "Find biological process terms whose definitions mention both 'mitochondria' and 'transport'"
    - Database: GO
    - Knowledge Required: bif:contains boolean syntax, namespace filtering
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

**Complex Filtering Questions**:

11. "What are all the subtypes of autophagy in Gene Ontology?"
    - Database: GO
    - Knowledge Required: Hierarchy navigation, GO:0006914 as parent
    - Category: Completeness
    - Difficulty: Easy
    - Pattern Reference: Pattern 6

12. "Find the parent terms of 'mitophagy' (selective autophagy of mitochondria)"
    - Database: GO
    - Knowledge Required: rdfs:subClassOf relationship, GO term lookup
    - Category: Precision
    - Difficulty: Easy
    - Pattern Reference: Pattern 6

13. "List GO terms that have synonyms including the word 'receptor'"
    - Database: GO
    - Knowledge Required: Synonym properties (hasExactSynonym, etc.), bif:contains
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

14. "What is the GO identifier for the biological process 'autophagy'?"
    - Method: OLS4 searchClasses
    - Knowledge Required: None (straightforward)
    - Category: Precision
    - Difficulty: Easy

15. "What is the definition of the GO term for 'protein kinase activity'?"
    - Method: OLS4 fetch
    - Knowledge Required: None
    - Category: Precision
    - Difficulty: Easy

16. "What are the synonyms for the GO term 'nucleus' (GO:0005634)?"
    - Method: OLS4 fetch or SPARQL
    - Knowledge Required: None
    - Category: Precision
    - Difficulty: Easy

**Hierarchy Questions (via OLS4 API)**:

17. "How many descendant terms does the GO term 'autophagy' (GO:0006914) have?"
    - Method: OLS4 getDescendants
    - Knowledge Required: None
    - Category: Completeness
    - Difficulty: Easy

18. "What is the direct parent term of 'macroautophagy' in Gene Ontology?"
    - Method: OLS4 getAncestors or fetch
    - Knowledge Required: None
    - Category: Precision
    - Difficulty: Easy

**ID Mapping Questions**:

19. "What GO terms is the TP53 gene (NCBI Gene ID 7157) annotated with?"
    - Method: togoid_convertId
    - Knowledge Required: None
    - Category: Integration
    - Difficulty: Easy

20. "What are the GO annotations for human BRCA1?"
    - Method: togoid_convertId with gene ID lookup
    - Knowledge Required: None
    - Category: Integration
    - Difficulty: Easy

---

## Integration Patterns Summary

**GO as Source**:
- → NCBI Gene: via TogoID (togoid:TIO_000004)
- → Ensembl: via TogoID
- → ChEMBL targets: via TogoID
- → PDB structures: via TogoID
- → Reactions (Rhea, Reactome): via TogoID and cross-references

**GO as Target**:
- UniProt →: protein function annotations
- NCBI Gene →: gene function annotations
- InterPro →: domain function annotations
- Reactome →: pathway-to-function links

**Complex Multi-Database Paths**:
- Gene → GO → Disease: NCBI Gene → GO term (via TogoID) → MONDO (keyword match)
- Protein → GO → Pathway: UniProt → GO term → Reactome (via cross-reference)
- Gene → GO → MeSH: For connecting biological functions to medical literature

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **STR() function requirement** - Critical for namespace filtering; without it, queries silently fail
2. **FROM clause** - Prevents duplicate/inconsistent results; essential for all GO SPARQL
3. **Type restriction (^^xsd:string)** - Required for cross-database queries on Virtuoso
4. **bif:contains syntax** - Much faster than REGEX; supports wildcards and boolean operators
5. **TogoID graph URIs** - Enable powerful gene annotation queries

### Common Pitfalls Discovered
1. Namespace filters fail silently without STR()
2. Missing FROM clause causes inconsistent/duplicated results
3. Cross-database queries need explicit type restrictions
4. REGEX is too slow for production queries

### Recommendations for Question Design
1. Questions testing namespace filtering should verify STR() usage
2. Cross-database questions should test proper GRAPH specifications
3. Completeness questions (counts) should verify FROM clause usage
4. Integration questions should test TogoID knowledge
5. Simple questions can use OLS4 API for contrast

### Performance Notes
- Simple label searches: <1 second
- Keyword searches with bif:contains: 1-3 seconds
- Hierarchical queries: 1-5 seconds
- Cross-database queries: 2-4 seconds (Tier 1-2)
- TogoID-mediated queries: 1-2 seconds (Tier 1)
- Aggregation without LIMIT: May timeout

---

## Notes and Observations

1. **GOA graph** (`http://purl.jp/bio/11/goa`) contains ontology metadata, not primary GO annotations - annotations come via TogoID graphs
2. **Deprecated terms** make up ~25% of total terms (11,905 out of ~48,000)
3. **Cross-references** link to 20+ databases but not all terms have them (~52% coverage)
4. **Synonym coverage** is good (~80%) with four types available
5. **Virtuoso backend** has specific requirements (bif:contains, type restrictions) documented in MIE

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database gene annotation queries, namespace filtering, bif:contains usage
- Avoid: Very simple OLS4 lookups (too easy), overly complex cross-products (timeout risk)
- Focus areas: Integration with NCBI Gene, error-avoidance patterns, performance optimization

**Further Exploration Needed** (if any):
- More testing of complex TogoID multi-hop queries
- Testing GOA graph for any usable annotation data
- Exploring integration with other databases not yet explored (Ensembl, PDB)

---

**Session Complete - Ready for Next Database**

---

## Session Summary

```
Database: go (Gene Ontology)
Status: ✅ COMPLETE
Report: /evaluation/exploration/go_exploration.md
Patterns Tested: 7 (namespace filtering, FROM clause, bif:contains, cross-database type restriction, TogoID integration, hierarchical navigation, cross-references)
Questions Identified: 20 (14 complex, 6 simple)
Integration Points: 6+ (NCBI Gene, MONDO, MeSH, Taxonomy, Reactome/EC via xrefs, TogoID graphs)
```
