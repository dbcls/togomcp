# MONDO (Monarch Disease Ontology) Exploration Report

**Date**: January 31, 2026
**Session**: 1 (Complete)

## Executive Summary

MONDO is a comprehensive disease ontology integrating multiple disease databases into a unified classification system. Key findings:

- **Key capabilities requiring deep knowledge**: Cross-database integration with MeSH and NANDO, hierarchical disease classification queries, cross-reference database filtering
- **Major integration opportunities**: MONDO ↔ MeSH (28% coverage), MONDO ↔ NANDO (84% coverage), three-way NANDO → MONDO → MeSH integration
- **Most valuable patterns discovered**: bif:contains for full-text search with relevance scoring, pre-filtering strategies for cross-database queries, URI conversion for MeSH integration
- **Recommended question types**: Cross-database disease mapping, hierarchical classification queries, rare disease lookups, clinical terminology integration

## Database Overview

- **Purpose and scope**: Comprehensive disease ontology providing unified classification across genetic disorders, infectious diseases, cancers, and rare diseases
- **Key data types and entities**: Disease classes (owl:Class), hierarchical relationships (rdfs:subClassOf), cross-references (oboInOwl:hasDbXref), synonyms, definitions
- **Dataset size**: 30,230 disease classes (30,304 total including obsolete)
- **Performance considerations**: Full-text index via bif:contains (10-100x faster than REGEX), transitive hierarchy queries need specific starting points and LIMIT
- **Available access methods**: SPARQL endpoint (primary), OLS4 API for keyword search

## Structure Analysis

### Performance Strategies

1. **Use bif:contains for label searches**
   - Why: Leverages Virtuoso's full-text index and provides relevance scoring
   - When: Any keyword search on labels or definitions
   - Performance impact: 10-100x faster than REGEX/CONTAINS

2. **Pre-filter in source GRAPH before joins**
   - Why: Reduces dataset from 30K diseases → ~10 before cross-database joins
   - When: Any cross-database query with MeSH, NANDO, or GO
   - Performance impact: 99.97% reduction in intermediate results

3. **Add FILTER(isIRI(?parent)) for hierarchy queries**
   - Why: Excludes OWL restriction blank nodes from results
   - When: Any query using rdfs:subClassOf
   - Performance impact: Cleaner results, prevents confusion

4. **Use LIMIT for transitive hierarchy queries**
   - Why: rdfs:subClassOf* without constraints can timeout
   - When: Any query with rdfs:subClassOf* or rdfs:subClassOf+
   - Performance impact: Prevents timeout on unbounded queries

5. **Use URI conversion for MeSH cross-references**
   - Why: MONDO stores MeSH refs as strings ("MESH:D######"), MeSH uses URIs
   - When: Joining MONDO to MeSH database
   - Example: `BIND(URI(CONCAT("http://id.nlm.nih.gov/mesh/", SUBSTR(?meshXref, 6))) AS ?meshDescriptor)`

### Common Pitfalls

1. **Using FILTER CONTAINS instead of bif:contains**
   - Cause: No full-text index, no relevance ranking
   - Symptoms: Slow queries, no scoring
   - Solution: Use `?label bif:contains "'keyword'" option (score ?sc)`

2. **Not filtering blank nodes in hierarchy queries**
   - Cause: OWL restrictions appear as blank nodes
   - Symptoms: Unexpected blank node results
   - Solution: Add `FILTER(isIRI(?parent))`

3. **Unbounded transitive queries**
   - Cause: `rdfs:subClassOf*` without starting point or LIMIT
   - Symptoms: Query timeout
   - Solution: Start from specific parent, add LIMIT

4. **Cross-database query timeout**
   - Cause: Missing pre-filtering, missing GRAPH clauses
   - Symptoms: 60+ second timeout
   - Solution: Apply filters within source GRAPH clause before join

5. **Three-way query 400 errors**
   - Cause: Multiple bif:contains in complex three-way queries
   - Symptoms: 400 Bad Request error
   - Solution: Use simplified CONTAINS instead of bif:contains for third database

### Data Organization

1. **Disease Classes (owl:Class)**
   - Purpose: Core disease entities
   - Content: 30,230 active diseases
   - Usage: Filter by MONDO_ prefix to exclude other ontology terms

2. **Hierarchical Relationships (rdfs:subClassOf)**
   - Purpose: Disease classification tree
   - Content: Directed acyclic graph structure
   - Usage: Use rdfs:subClassOf+ for ancestors, rdfs:subClassOf* includes self

3. **Cross-References (oboInOwl:hasDbXref)**
   - Purpose: Links to external databases
   - Content: ~6.5 references per disease on average
   - Coverage: 90% of diseases have cross-references
   - Databases: OMIM (33%), Orphanet (34%), MeSH (28%), ICD codes, UMLS, etc.

4. **Synonyms**
   - Exact synonyms (oboInOwl:hasExactSynonym): Semantically equivalent
   - Related synonyms (oboInOwl:hasRelatedSynonym): Broader/narrower meaning
   - Coverage: ~85% of diseases have synonyms

5. **Definitions (IAO:0000115)**
   - Purpose: Textual descriptions of diseases
   - Coverage: ~75% of diseases have definitions

### Cross-Database Integration Points

**Integration 1: MONDO → MeSH**
- Connection relationship: oboInOwl:hasDbXref with "MESH:D######" format
- Join point: Convert string to URI with BIND(URI(CONCAT(...)))
- Required information from each: MONDO disease labels, MeSH TopicalDescriptor labels
- Pre-filtering needed: bif:contains on MONDO labels first (Strategy 2)
- Knowledge required: MeSH graph URI, TopicalDescriptor type, URI conversion pattern
- Coverage: ~28% of MONDO diseases (~8,500 mappings)
- Performance: 2-3 seconds with pre-filtering

**Integration 2: MONDO ← NANDO**
- Connection relationship: NANDO's skos:closeMatch links to MONDO URIs
- Join point: Direct URI reference from NANDO to MONDO
- Required information: NANDO multilingual labels (Japanese kanji/English), notification numbers
- Pre-filtering needed: bif:contains on NANDO English labels
- Knowledge required: NANDO graph URI, skos:closeMatch property, language filters
- Coverage: 84% of NANDO diseases (2,341 of 2,777 have MONDO mappings)
- Performance: 2-4 seconds

**Integration 3: NANDO → MONDO → MeSH (Three-way)**
- Path: NANDO skos:closeMatch → MONDO hasDbXref → MeSH
- Pre-filtering: Apply in NANDO GRAPH before joins
- Knowledge required: All three MIE files, URI conversion
- Performance: 3-6 seconds
- Critical: Use CONTAINS instead of multiple bif:contains to avoid 400 errors

**Integration 4: MONDO ↔ GO (Keyword-based)**
- Connection relationship: No direct links; keyword-based integration
- Join point: Matching terms by keyword
- Required information: GO namespace filter, bif:contains patterns
- Pre-filtering needed: bif:contains on both MONDO and GO labels
- Knowledge required: GO graph URI, namespace types, type restrictions
- Performance: 2-4 seconds

## Complex Query Patterns Tested

### Pattern 1: MONDO-MeSH Cross-Database Integration

**Purpose**: Link disease ontology terms to medical literature indexing terminology

**Category**: Cross-Database, Integration

**Naive Approach (without proper knowledge)**:
Filter on MeSH labels after joining all 30K MONDO diseases → timeout

**What Happened**:
- Error message: Query timeout after 60 seconds
- Why it failed: Processing all 30K diseases before filtering

**Correct Approach (using proper pattern)**:
Pre-filter MONDO with bif:contains, then join to MeSH

**What Knowledge Made This Work**:
- Key Insights:
  * Use bif:contains for MONDO label filtering (Strategy 4)
  * Apply filter within MONDO GRAPH clause before join (Strategy 2)
  * Convert MONDO's "MESH:D######" format to MeSH URIs (Strategy 5)
- Performance improvement: 2-3 seconds vs timeout
- Why it works: 99.97% reduction in MONDO diseases before MeSH join

**Results Obtained**:
- Sample results for "diabetes":
  * MONDO:0005015 "diabetes mellitus" → MeSH:D003920
  * MONDO:0005147 "type 1 diabetes mellitus" → MeSH:D003922
  * MONDO:0005148 "type 2 diabetes mellitus" → MeSH:D003924
  * MONDO:0005406 "gestational diabetes" → MeSH:D016640

**Natural Language Question Opportunities**:
1. "What is the MeSH term for type 1 diabetes in the MONDO ontology?" - Category: Integration, Difficulty: Medium
2. "Find all diabetes-related diseases in MONDO and their corresponding MeSH identifiers" - Category: Integration, Difficulty: Medium
3. "Which neurodegenerative diseases have both MONDO and MeSH classifications?" - Category: Integration, Difficulty: Hard

---

### Pattern 2: MONDO-NANDO Japanese Rare Disease Integration

**Purpose**: Connect international disease classification to Japanese intractable disease database

**Category**: Cross-Database, Integration, Specificity

**Naive Approach (without proper knowledge)**:
Query without language filters or proper GRAPH clauses

**What Happened**:
- Issues: Missing Japanese labels, incomplete results
- Why it failed: Need language filters and proper graph specification

**Correct Approach (using proper pattern)**:
Use NANDO's skos:closeMatch, filter by language (ja/en), apply bif:contains in NANDO graph

**What Knowledge Made This Work**:
- Key Insights:
  * NANDO uses skos:closeMatch (not hasDbXref) to link to MONDO
  * Language filters needed: LANG(?label) = "ja" for Japanese, "en" for English
  * NANDO has notification numbers (nando:hasNotificationNumber) for designated diseases
- Performance improvement: 2-4 seconds with pre-filtering

**Results Obtained**:
- Sample results for "Parkinson":
  * NANDO: パーキンソン病 (Parkinson's disease), notification #6 → MONDO:0005180

**Natural Language Question Opportunities**:
1. "What is the Japanese designation number for Parkinson's disease?" - Category: Specificity, Difficulty: Medium
2. "Find Japanese rare diseases related to ALS with their MONDO equivalents" - Category: Integration, Difficulty: Hard
3. "Which Japanese intractable diseases have corresponding entries in the international MONDO ontology?" - Category: Completeness, Difficulty: Hard

---

### Pattern 3: Three-Way NANDO → MONDO → MeSH Integration

**Purpose**: Bridge Japanese rare disease classifications to international medical literature indexing

**Category**: Cross-Database, Advanced Integration

**Naive Approach (without proper knowledge)**:
Use multiple bif:contains across all three databases

**What Happened**:
- Error message: 400 Bad Request
- Why it failed: Query complexity exceeded endpoint limits with multiple bif:contains

**Correct Approach (using proper pattern)**:
Use CONTAINS instead of bif:contains, simplify third database GRAPH clause

**What Knowledge Made This Work**:
- Key Insights:
  * Three-way queries need simplified filters
  * Use CONTAINS(LCASE(?label), "keyword") for third database
  * Keep third GRAPH clause minimal
- Performance improvement: 3-6 seconds vs 400 error

**Results Obtained**:
- Sample results for "amyotrophic":
  * NANDO: 筋萎縮性側索硬化症 (ALS), notification #2 → MONDO → MeSH:Amyotrophic Lateral Sclerosis

**Natural Language Question Opportunities**:
1. "For ALS, what are the Japanese disease name, international classification, and medical literature term?" - Category: Integration, Difficulty: Hard
2. "Find rare diseases that have entries in Japanese NANDO, international MONDO, and medical MeSH databases" - Category: Completeness, Difficulty: Hard

---

### Pattern 4: Disease Hierarchy Traversal

**Purpose**: Navigate the MONDO disease classification tree

**Category**: Structured Query, Completeness

**Naive Approach (without proper knowledge)**:
Use rdfs:subClassOf* without starting point or LIMIT

**What Happened**:
- Error message: Query timeout
- Why it failed: Unbounded transitive query processes entire ontology

**Correct Approach (using proper pattern)**:
Start from specific disease class (e.g., MONDO:0003847 hereditary disease), add LIMIT

**What Knowledge Made This Work**:
- Key Insights:
  * Always specify starting point for transitive queries
  * Add FILTER(isIRI(?parent)) to exclude blank nodes
  * Use LIMIT for exploratory queries
- Performance improvement: 2-5 seconds vs timeout

**Results Obtained**:
- Type 1 diabetes (MONDO:0005147) ancestors: diabetes mellitus, metabolic disease, endocrine system disorder, autoimmune disease, immune system disorder, disease
- Hereditary disease descendants: 11,651+ diseases

**Natural Language Question Opportunities**:
1. "What are all the parent disease categories for type 1 diabetes?" - Category: Structured Query, Difficulty: Medium
2. "How many genetic disorders are classified under hereditary disease in MONDO?" - Category: Completeness, Difficulty: Medium
3. "What is the complete classification path from Huntington disease to the root disease category?" - Category: Structured Query, Difficulty: Medium

---

### Pattern 5: Full-Text Search with Relevance Scoring

**Purpose**: Find diseases by keyword with relevance ranking

**Category**: Precision, Structured Query

**Naive Approach (without proper knowledge)**:
Use FILTER(CONTAINS(LCASE(?label), "keyword"))

**What Happened**:
- Issues: Slow performance, no relevance ranking
- Why it failed: No full-text index usage

**Correct Approach (using proper pattern)**:
Use bif:contains with option (score ?sc), ORDER BY DESC(?sc)

**What Knowledge Made This Work**:
- Key Insights:
  * bif:contains leverages Virtuoso full-text index
  * option (score ?sc) provides relevance ranking
  * Can use boolean operators: "(term1 AND term2)", wildcards with *
- Performance improvement: 10-100x faster

**Results Obtained**:
- "cancer" search returns "cancer" (exact match, score 15), then cancer types ranked by relevance
- "Huntington" search returns Huntington disease variants ordered by relevance

**Natural Language Question Opportunities**:
1. "Find all cancer-related diseases in MONDO" - Category: Completeness, Difficulty: Easy
2. "What Huntington disease variants exist in the MONDO ontology?" - Category: Precision, Difficulty: Easy
3. "Find diseases whose names contain both 'diabetes' and 'mellitus'" - Category: Structured Query, Difficulty: Medium

---

### Pattern 6: Cross-Reference Database Filtering

**Purpose**: Find diseases with specific external database links

**Category**: Completeness, Specificity

**Naive Approach (without proper knowledge)**:
Use REGEX for pattern matching

**What Happened**:
- Issues: Slow performance
- Why it failed: REGEX doesn't use indexes

**Correct Approach (using proper pattern)**:
Use STRSTARTS(?xref, "PREFIX:") for prefix matching

**What Knowledge Made This Work**:
- Key Insights:
  * STRSTARTS is efficient for prefix matching
  * Cross-reference format: "DATABASE:ID" (e.g., "OMIM:143100")
  * Different databases have different coverage: OMIM 33%, Orphanet 34%, MeSH 28%, ICD10 ~10%

**Results Obtained**:
- OMIM-linked diseases: 9,944
- Orphanet-linked diseases: 10,246
- ICD10-linked diseases: 2,611

**Natural Language Question Opportunities**:
1. "How many diseases in MONDO have OMIM references?" - Category: Completeness, Difficulty: Easy
2. "Which diseases have both Orphanet and ICD-10 classifications?" - Category: Structured Query, Difficulty: Medium
3. "Find rare diseases with Orphanet references but no OMIM entry" - Category: Structured Query, Difficulty: Hard

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "Huntington disease"
   - Found: MONDO:0007739 - Huntington disease
   - Cross-refs: OMIM:143100, Orphanet:399, MESH:D006816
   - Usage: Neurodegenerative disease questions, cross-reference questions

2. Search: "diabetes"
   - Found: MONDO:0005015 - diabetes mellitus, MONDO:0005147 - type 1, MONDO:0005148 - type 2
   - Usage: Metabolic disease hierarchy, common disease classification

3. Search: "cancer"
   - Found: MONDO:0004992 - cancer (root), multiple cancer types
   - Usage: Oncology classification, transitive hierarchy questions

4. Search: "Parkinson"
   - Found: MONDO:0005180 - Parkinson disease
   - NANDO: notification #6
   - Usage: Japanese rare disease integration

5. Search: "amyotrophic lateral sclerosis"
   - Found: MONDO equivalent linked to NANDO (notification #2)
   - MeSH: Amyotrophic Lateral Sclerosis
   - Usage: Three-way integration questions

6. Search: "hereditary disease" (class)
   - Found: MONDO:0003847 - hereditary disease
   - Descendants: 11,651+ diseases
   - Usage: Hierarchy traversal questions

7. Search: "Fabry disease"
   - Found: MONDO:0010526 - Fabry disease (lysosomal storage disorder)
   - Usage: Rare disease questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What is the MeSH descriptor for Huntington disease?"
   - Databases involved: MONDO, MeSH
   - Knowledge Required: MONDO graph URI, MeSH graph URI, hasDbXref property, URI conversion pattern, meshv:TopicalDescriptor type
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

2. "Find all diabetes-related diseases and their corresponding MeSH terms"
   - Databases involved: MONDO, MeSH
   - Knowledge Required: bif:contains pattern, pre-filtering strategy, URI conversion
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

3. "What is the Japanese designation number for Parkinson's disease in the NANDO database?"
   - Databases involved: MONDO, NANDO
   - Knowledge Required: NANDO graph URI, skos:closeMatch property, nando:hasNotificationNumber
   - Category: Specificity
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

4. "Which Japanese intractable diseases have corresponding MONDO entries?"
   - Databases involved: NANDO, MONDO
   - Knowledge Required: Language filters, skos:closeMatch, pre-filtering
   - Category: Completeness
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

5. "For amyotrophic lateral sclerosis, provide the Japanese disease name, MONDO identifier, and MeSH term"
   - Databases involved: NANDO, MONDO, MeSH
   - Knowledge Required: Three-way query optimization, simplified CONTAINS for third database
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

6. "Find mitochondrial diseases that have related biological processes in Gene Ontology"
   - Databases involved: MONDO, GO
   - Knowledge Required: Keyword-based integration, both graph URIs
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: MONDO-GO integration tested

**Hierarchy/Classification Questions**:

7. "What are all the parent disease categories for type 1 diabetes mellitus?"
   - Database: MONDO
   - Knowledge Required: rdfs:subClassOf+ property path, FILTER(isIRI()), DISTINCT
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

8. "How many diseases are classified under hereditary disease in MONDO?"
   - Database: MONDO
   - Knowledge Required: rdfs:subClassOf* transitive query, starting point specification, LIMIT strategy
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

9. "List all subtypes of Huntington disease and related disorders"
   - Database: MONDO
   - Knowledge Required: Transitive hierarchy, disease grouping class
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

10. "What cancers are classified as subtypes of the cancer root class?"
    - Database: MONDO
    - Knowledge Required: rdfs:subClassOf* from MONDO:0004992
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Pattern 4

**Cross-Reference Filtering Questions**:

11. "How many diseases in MONDO have OMIM cross-references?"
    - Database: MONDO
    - Knowledge Required: STRSTARTS filter pattern, hasDbXref property
    - Category: Completeness
    - Difficulty: Easy
    - Pattern Reference: Pattern 6

12. "Find rare diseases with Orphanet references but no ICD-10 codes"
    - Database: MONDO
    - Knowledge Required: Combining STRSTARTS filters with NOT EXISTS
    - Category: Structured Query
    - Difficulty: Hard
    - Pattern Reference: Pattern 6

13. "Which neurodegenerative diseases have both OMIM and Orphanet cross-references?"
    - Database: MONDO
    - Knowledge Required: Multiple STRSTARTS filters, keyword search
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 5, Pattern 6

**Full-Text Search Questions**:

14. "Find all diseases whose names contain 'cardiomyopathy'"
    - Database: MONDO
    - Knowledge Required: bif:contains with relevance scoring
    - Category: Precision
    - Difficulty: Easy
    - Pattern Reference: Pattern 5

15. "Search for diseases related to 'lysosomal storage'"
    - Database: MONDO
    - Knowledge Required: bif:contains with boolean operators
    - Category: Precision
    - Difficulty: Easy
    - Pattern Reference: Pattern 5

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the MONDO identifier for Huntington disease?"
   - Method: OLS4:searchClasses or simple SPARQL
   - Knowledge Required: None (straightforward search)
   - Category: Precision
   - Difficulty: Easy

2. "What is the definition of Fabry disease in MONDO?"
   - Method: Direct entity lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "What are the synonyms for Huntington disease?"
   - Method: Simple property retrieval
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

4. "What is the OMIM reference for Huntington disease?"
   - Method: hasDbXref lookup
   - Knowledge Required: None (single entity)
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

5. "What is the Orphanet ID for Huntington disease?"
   - Method: hasDbXref lookup
   - Knowledge Required: None
   - Category: Integration (simple)
   - Difficulty: Easy

**Simple API Queries**:

6. "How many descendant terms does the hereditary disease class have in MONDO?"
   - Method: OLS4:getDescendants
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy

7. "What are the direct parent classes of type 1 diabetes in MONDO?"
   - Method: OLS4 searchClasses returns directParent
   - Knowledge Required: None
   - Category: Structured Query (simple)
   - Difficulty: Easy

---

## Integration Patterns Summary

**MONDO as Source (provides data to)**:
- → MeSH: via hasDbXref "MESH:D######" (28% coverage)
- → (any database): via hasDbXref strings for 39+ databases

**MONDO as Target (receives data from)**:
- NANDO →: via skos:closeMatch (84% of NANDO diseases)

**Complex Multi-Database Paths**:
- Path 1: NANDO → MONDO → MeSH: Japanese rare diseases to medical literature indexing
- Path 2: MONDO ↔ GO: Keyword-based integration for disease-process relationships
- Path 3: MONDO → OMIM/Orphanet: Genetic disease databases (via hasDbXref)

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **Pre-filtering strategy** (Strategy 2): Critical for any cross-database query - reduces 30K diseases to manageable subset before joins
2. **bif:contains pattern** (Strategy 4): Essential for any keyword search - 10-100x performance improvement
3. **URI conversion for MeSH**: MONDO stores strings, MeSH uses URIs - must convert
4. **Three-way query simplification**: Cannot use multiple bif:contains - must use CONTAINS
5. **GRAPH clause isolation**: Each database needs explicit GRAPH clause

### Common Pitfalls Discovered
1. **Timeout on cross-database queries**: Always filter in source GRAPH first
2. **400 error on three-way queries**: Simplify third database clause
3. **Missing blank node filter**: Add FILTER(isIRI()) for hierarchy queries
4. **Wrong URI format for MeSH**: Must construct URI from string reference

### Recommendations for Question Design
1. **Best question types for MONDO**:
   - Cross-database integration (MeSH, NANDO)
   - Hierarchical classification queries
   - Rare disease lookups with Orphanet/OMIM cross-refs
   - Full-text search with relevance ranking

2. **Question complexity sweet spots**:
   - Medium: Two-database integration with pre-filtering
   - Hard: Three-database integration or complex hierarchy traversal
   - Easy: Single-entity lookups via API

3. **Avoid these question types**:
   - Unbounded aggregation over all 30K diseases (timeout risk)
   - Questions requiring complex filters in third GRAPH clause

### Performance Notes
- Simple searches: <1 second
- bif:contains searches: 1-2 seconds
- Two-database cross-queries with pre-filter: 2-3 seconds
- Three-database queries: 3-6 seconds
- Hierarchy traversal with LIMIT: 2-5 seconds
- Unbounded transitive queries: TIMEOUT

---

## Notes and Observations

1. **MONDO integrates 39+ databases** - Extensive cross-reference coverage makes it an excellent hub for disease-related queries
2. **MeSH coverage at 28%** - Not all diseases have MeSH mappings, which is important for setting expectations
3. **NANDO integration is high** - 84% coverage makes MONDO-NANDO queries reliable
4. **No direct GO links** - Disease-to-process integration must be keyword-based
5. **Human vs non-human diseases** - MONDO includes animal disease variants (e.g., Huntington disease, pig)
6. **Obsolete terms marked** - owl:deprecated flag indicates deprecated disease classes

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: MONDO-MeSH integration, MONDO-NANDO integration, hierarchy classification, cross-reference filtering
- Avoid: Unbounded aggregations, questions requiring multiple bif:contains in three-way queries
- Focus areas: Rare disease lookups, disease classification hierarchies, international disease mapping

**Further Exploration Needed** (if any):
- HP (Human Phenotype Ontology) cross-reference exploration - MONDO has some HP:##### references
- More complex three-way integration patterns
- Disease subtype classification depth analysis

---

**Session Complete - Ready for Next Database**

## Session Summary
```
Database: MONDO
Status: ✅ COMPLETE
Report: /evaluation/exploration/mondo_exploration.md
Patterns Tested: 6 major patterns
Questions Identified: 22 (15 complex, 7 simple)
Integration Points: 4 (MeSH, NANDO, GO keyword, OMIM/Orphanet via xref)
Cross-Database Queries Tested: 5 (MONDO-MeSH, MONDO-NANDO, NANDO-MONDO-MeSH three-way, MONDO-GO)
```
