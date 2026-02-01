# UniProt Exploration Report

**Date**: 2026-01-31
**Session**: 1
**Database**: UniProt (Universal Protein Resource)

## Executive Summary

UniProt is the most comprehensive protein database in TogoMCP, containing 444 million proteins with rich functional annotations. Key findings:

- **Critical Performance Requirement**: Always use `up:reviewed 1` filter (reduces 444M to 923K proteins, 99.8% reduction)
- **Major Integration Opportunity**: Shared SIB endpoint with Rhea enables powerful enzyme-reaction queries
- **Key Anti-Patterns**: bif:contains CANNOT be combined with property paths (causes 400 errors)
- **Recommended Question Types**: Cross-database joins, performance-critical counts, text search with error avoidance

## Database Overview

- **Purpose**: Comprehensive protein sequence and functional information
- **Data Sources**: Swiss-Prot (manually curated) and TrEMBL (automatically annotated)
- **Key Data Types**: Proteins, sequences, annotations, GO terms, cross-references
- **Dataset Size**: 
  - Total proteins: 444,565,015
  - Reviewed (Swiss-Prot): 923,147 (quality-curated)
  - Human reviewed: 40,209
- **Endpoint**: https://rdfportal.org/sib/sparql (shared with Rhea)
- **Available Graphs**:
  - http://sparql.uniprot.org/uniprot (main protein data)
  - http://sparql.uniprot.org/go (Gene Ontology)
  - http://sparql.uniprot.org/taxonomy (organism classification)
  - http://sparql.uniprot.org/citations (literature references)
  - http://sparql.uniprot.org/diseases (disease associations)
  - http://sparql.uniprot.org/enzyme (EC classifications)
  - http://sparql.uniprot.org/keywords (controlled vocabulary)
  - http://sparql.uniprot.org/locations (subcellular locations)
  - http://sparql.uniprot.org/pathways (pathway associations)

## Structure Analysis

### Performance Strategies

**Strategy 1: reviewed=1 Filter (CRITICAL)**
- Why needed: 444M vs 923K proteins - prevents timeout
- When to apply: EVERY UniProt query
- Performance impact: 99.8% reduction in search space
- Tested: COUNT with reviewed=1 returned 40,209 human proteins in ~2s

**Strategy 2: bif:contains with Split Property Paths**
- Why needed: bif:contains is incompatible with SPARQL property paths (/)
- When to apply: Any text search in names, annotations, or comments
- Performance impact: 5-10x faster than FILTER(CONTAINS())
- Error avoidance: Prevents 400 Bad Request errors

**Strategy 3: Explicit GRAPH Clauses**
- Why needed: UniProt has multiple graphs at the same endpoint
- When to apply: Cross-database or multi-graph queries
- Performance impact: Prevents cross-contamination and improves optimization

**Strategy 4: Organism Filtering via up:organism**
- Why needed: Mnemonic-based filtering (_HUMAN) is unreliable
- Correct approach: `up:organism <http://purl.uniprot.org/taxonomy/9606>`
- Performance impact: Significant reduction for species-specific queries

### Common Pitfalls

**Error 1: Missing reviewed=1 Filter**
- Cause: Querying 444M proteins instead of 923K
- Symptoms: Query timeout (60s)
- Solution: Add `?protein up:reviewed 1` as FIRST constraint
- Tested: Cross-database query without reviewed=1 timed out

**Error 2: bif:contains with Property Paths**
- Cause: Virtuoso's bif:contains doesn't support property paths
- Symptoms: 400 Bad Request error
- Solution: Split property paths into separate triple patterns
- Example:
  - WRONG: `up:recommendedName/up:fullName ?name . ?name bif:contains 'kinase'`
  - CORRECT: `up:recommendedName ?n . ?n up:fullName ?name . ?name bif:contains 'kinase'`
- Tested: Confirmed 400 error with property path, success with split path

**Error 3: Wrong Organism Filtering**
- Cause: Using mnemonic suffixes (_HUMAN) instead of taxonomy URIs
- Symptoms: Incomplete or incorrect results
- Solution: Use `up:organism <http://purl.uniprot.org/taxonomy/9606>`
- Tested: Verified correct human counts with taxonomy URI

**Error 4: Cross-Database Query Without Pre-Filtering**
- Cause: Late filtering after large cross-database join
- Symptoms: Timeout due to processing millions of intermediate results
- Solution: Apply reviewed=1 and status filters WITHIN GRAPH clauses BEFORE joins
- Tested: Query timed out without early filtering, completed in ~3s with filtering

### Data Organization

**Main Data (uniprot graph)**
- Proteins with identifiers, mnemonics, sequences
- Annotations (Function, Disease, Pathway, etc.)
- Cross-references to 200+ external databases
- Enzyme classifications (EC numbers)
- Gene information

**GO Terms (go graph)**
- Gene Ontology annotations
- Coverage: >85% of reviewed proteins
- Requires STRSTARTS filter for proper identification

**Taxonomy (taxonomy graph)**
- Organism classifications
- Hierarchical relationships via rdfs:subClassOf

**Citations (citations graph)**
- Literature references
- PubMed links

### Cross-Database Integration Points

**Integration 1: UniProt → Rhea (Enzyme-Reaction)**
- Connection relationship: `up:enzyme` ↔ `rhea:ec` (shared EC namespace)
- Join point: EC number URIs (http://purl.uniprot.org/enzyme/X.X.X.X)
- Required information:
  - From UniProt: reviewed=1, organism, enzyme annotation, protein names
  - From Rhea: reaction status, equation, participants
- Pre-filtering needed: reviewed=1 in UniProt GRAPH, rhea:Approved in Rhea GRAPH
- Knowledge required: Graph URIs, split property paths for bif:contains
- Tested: Successfully returned 20 enzymes with ATP-dependent reactions in ~3s

**Integration 2: UniProt → GO (Protein-Function)**
- Connection relationship: `up:classifiedWith` → GO term URIs
- Join point: GO term URIs (http://purl.obolibrary.org/obo/GO_XXXXXXX)
- Pre-filtering needed: reviewed=1, organism filter
- Knowledge required: STRSTARTS filter for GO URIs, two graphs involved
- Tested: Found 146 human proteins with GO:0006914 (autophagy)

**Integration 3: UniProt → PDB (Protein-Structure)**
- Connection relationship: `rdfs:seeAlso` with PDB URI filter
- Join point: PDB URIs (http://rdf.wwpdb.org/pdb/XXXX)
- Pre-filtering needed: reviewed=1, STRSTARTS filter
- Knowledge required: External database URI patterns
- Tested: Found 258 PDB structures for P04637 (TP53)

**Integration 4: Three-Way (UniProt + Rhea + GO)**
- Path: Protein → Enzyme → Reaction + Protein → GO Term
- Three graphs required: uniprot, rhea dataset, go
- Pre-filtering: Essential in ALL graphs
- Knowledge required: All join points, graph URIs, filtering strategies
- Tested: Successfully returned 30 human enzymes with reactions and GO terms

## Complex Query Patterns Tested

### Pattern 1: Cross-Database Enzyme-Reaction Query

**Purpose**: Find proteins that catalyze specific biochemical reactions

**Category**: Cross-Database Integration

**Naive Approach (without proper knowledge)**:
- Query both UniProt and Rhea without GRAPH clauses
- Missing reviewed=1 filter
- Using property path with bif:contains

**What Happened**:
- Error: Timeout (>60 seconds)
- Why it failed: Processing 444M proteins before join, no graph isolation

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?protein ?mnemonic ?fullName ?reaction ?equation
WHERE {
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein a up:Protein ;
             up:reviewed 1 ;
             up:mnemonic ?mnemonic ;
             up:enzyme ?enzyme ;
             up:recommendedName ?name .
    ?name up:fullName ?fullName .
  }
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved ;
              rhea:ec ?enzyme .
    ?equation bif:contains "'ATP'" option (score ?sc) .
  }
}
ORDER BY DESC(?sc)
LIMIT 20
```

**What Knowledge Made This Work**:
- Graph URIs from UniProt and Rhea MIE files
- reviewed=1 filter from UniProt performance guidelines
- Split property path for bif:contains
- rhea:Approved status filter
- Performance improvement: From timeout to ~3 seconds

**Results Obtained**:
- Number of results: 20
- Sample results:
  * P09979 (KHYB_STRHY) - Hygromycin-B 7''-O-kinase - ATP + hygromycin B reaction
  * Q9D5J6 (SHPK_MOUSE) - Sedoheptulokinase - ATP + sedoheptulose reaction
  * P54645 (AAPK1_RAT) - AMP-activated protein kinase - ATP + L-seryl reaction

**Natural Language Question Opportunities**:
1. "Which reviewed proteins catalyze reactions involving ATP?" - Category: Integration
2. "Find human enzymes that catalyze glucose-related biochemical reactions" - Category: Integration
3. "What proteins are involved in phosphorylation reactions?" - Category: Structured Query

---

### Pattern 2: bif:contains with Split Property Path

**Purpose**: Search protein names using full-text search

**Category**: Error Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
SELECT ?protein ?fullName
WHERE {
  ?protein up:reviewed 1 ;
           up:recommendedName/up:fullName ?fullName .
  ?fullName bif:contains "'kinase'"
}
```

**What Happened**:
- Error: 400 Bad Request
- Why it failed: bif:contains cannot process property path output

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?protein ?fullName
WHERE {
  ?protein up:reviewed 1 ;
           up:recommendedName ?name .
  ?name up:fullName ?fullName .
  ?fullName bif:contains "'kinase'"
}
```

**What Knowledge Made This Work**:
- Split property path pattern from UniProt MIE common_errors section
- Understanding of Virtuoso's bif:contains limitations
- Performance improvement: From 400 error to successful query

**Results Obtained**:
- Number of results: Many kinase proteins found
- Sample results:
  * Q9FIZ3 - LRR receptor-like serine/threonine-protein kinase GSO2
  * Q04982 - Serine/threonine-protein kinase B-raf

**Natural Language Question Opportunities**:
1. "Find proteins whose name contains 'kinase'" - Category: Structured Query
2. "Which human proteins are described as membrane receptors?" - Category: Structured Query
3. "Find tumor suppressor proteins based on their functional annotations" - Category: Structured Query

---

### Pattern 3: Three-Way Cross-Database Integration

**Purpose**: Link proteins to reactions AND to GO terms

**Category**: Advanced Integration

**Correct Approach**:
```sparql
SELECT DISTINCT ?protein ?mnemonic ?reaction ?equation ?goLabel
WHERE {
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein a up:Protein ;
             up:reviewed 1 ;
             up:organism <http://purl.uniprot.org/taxonomy/9606> ;
             up:mnemonic ?mnemonic ;
             up:enzyme ?enzyme ;
             up:classifiedWith ?goTerm .
  }
  GRAPH <http://sparql.uniprot.org/go> {
    ?goTerm rdfs:label ?goLabel .
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
  }
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved ;
              rhea:ec ?enzyme .
  }
}
LIMIT 30
```

**What Knowledge Made This Work**:
- Three graph URIs (uniprot, go, rhea)
- Pre-filtering in ALL graphs
- STRSTARTS filter for GO term identification
- rhea:Approved status filter

**Results Obtained**:
- Number of results: 30
- Sample results:
  * P00338 (LDHA_HUMAN) - Lactate dehydrogenase - nucleus - lactate + NAD reaction
  * P17612 (KAPCA_HUMAN) - PKA alpha - cytoplasm - ATP + L-seryl reaction
  * Q8IXJ6 (SIR2_HUMAN) - Sirtuin-2 - nucleus - deacetylation reaction

**Natural Language Question Opportunities**:
1. "Find human enzymes with known subcellular location and catalyzed reactions" - Category: Integration
2. "Which human proteins are both kinases and localized to the cytoplasm?" - Category: Structured Query

---

### Pattern 4: Performance-Critical COUNT Query

**Purpose**: Count human proteins with specific GO annotations

**Category**: Performance-Critical

**Naive Approach (without reviewed=1)**:
```sparql
SELECT (COUNT(*) as ?count)
WHERE {
  ?protein a up:Protein ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> .
}
```

**What Happened**:
- Result: 313,564 (includes TrEMBL)
- Query completed but includes unreliable automated annotations

**Correct Approach (with reviewed=1)**:
```sparql
SELECT (COUNT(*) as ?count)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> .
}
```

**What Knowledge Made This Work**:
- reviewed=1 filter ensures expert-curated quality
- Count reduced from 313K to 40K (quality subset)

**Results Obtained**:
- Human reviewed proteins: 40,209
- Human proteins with autophagy annotation (GO:0006914): 146

**Natural Language Question Opportunities**:
1. "How many reviewed human proteins are in UniProt?" - Category: Completeness
2. "How many human proteins are annotated with autophagy function?" - Category: Completeness
3. "Count the number of human kinases with expert curation" - Category: Completeness

---

### Pattern 5: Text Search in Functional Annotations

**Purpose**: Find proteins by functional description keywords

**Category**: Error Avoidance + Structured Query

**Correct Approach**:
```sparql
SELECT ?protein ?mnemonic ?comment
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:mnemonic ?mnemonic ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:annotation ?annot .
  ?annot a up:Function_Annotation ;
         rdfs:comment ?comment .
  ?comment bif:contains "'tumor suppressor'"
}
LIMIT 20
```

**What Knowledge Made This Work**:
- Annotation type filtering (up:Function_Annotation)
- Split path for annotation access
- bif:contains for efficient text search
- reviewed=1 + organism filter

**Results Obtained**:
- Number of results: 20 tumor suppressor proteins
- Sample results:
  * P0CG12 (DERPC_HUMAN) - "Potential tumor suppressor"
  * Q13227 (GPS2_HUMAN) - "Acts as a tumor-suppressor in liposarcoma"
  * P04637 (P53_HUMAN) - Cellular tumor antigen p53

**Natural Language Question Opportunities**:
1. "Find human proteins annotated as tumor suppressors" - Category: Structured Query
2. "Which proteins have DNA repair in their functional description?" - Category: Structured Query
3. "Find membrane receptor proteins from functional annotations" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "human BRCA1"
   - Found: P38398 - Breast cancer type 1 susceptibility protein
   - Usage: Precision questions, ID lookup

2. Search: "human TP53"
   - Found: P04637 - Cellular tumor antigen p53
   - Usage: Cross-reference questions (258 PDB structures), integration

3. Search: "human insulin receptor"
   - Found: P06213 - Insulin receptor
   - Usage: Function annotation questions

4. ID Conversion: P04637 → NCBI Gene
   - Found: 7157
   - Usage: ID mapping questions

5. ID Conversion: P38398 → NCBI Gene
   - Found: 672
   - Usage: ID mapping questions

6. ID Conversion: P04637 → PDB
   - Found: 258 structures (1A1U, 1AIE, 1C26, etc.)
   - Usage: Structure-related questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which human enzymes catalyze reactions involving ATP?"
   - Databases involved: UniProt, Rhea
   - Knowledge Required: Graph URIs, reviewed=1, rhea:Approved, EC number linking
   - Category: Integration
   - Difficulty: Medium

2. "Find reviewed proteins that catalyze glucose metabolism reactions"
   - Databases involved: UniProt, Rhea
   - Knowledge Required: Cross-database join, bif:contains, pre-filtering
   - Category: Integration
   - Difficulty: Medium

3. "Which human kinases have known biochemical reaction equations?"
   - Databases involved: UniProt, Rhea
   - Knowledge Required: Two-graph query, property path splitting
   - Category: Integration
   - Difficulty: Medium

4. "Find enzymes with both mitochondrial localization and oxidation reactions"
   - Databases involved: UniProt, Rhea, GO
   - Knowledge Required: Three-way join, multiple filtering
   - Category: Integration
   - Difficulty: Hard

5. "What human proteins catalyze reactions involving phosphate transfer?"
   - Databases involved: UniProt, Rhea
   - Knowledge Required: Cross-database, text search in equations
   - Category: Integration
   - Difficulty: Medium

**Performance-Critical Questions**:

1. "How many reviewed human proteins are in UniProt?"
   - Database: UniProt
   - Knowledge Required: reviewed=1 filter (CRITICAL for performance)
   - Category: Completeness
   - Difficulty: Easy (but requires knowledge)

2. "How many human proteins are annotated with autophagy (GO:0006914)?"
   - Database: UniProt, GO
   - Knowledge Required: reviewed=1, GO URI filter, two graphs
   - Category: Completeness
   - Difficulty: Medium

3. "Count human enzymes with EC number annotations"
   - Database: UniProt
   - Knowledge Required: reviewed=1, up:enzyme property
   - Category: Completeness
   - Difficulty: Medium

4. "How many human proteins have 3D structures in PDB?"
   - Database: UniProt
   - Knowledge Required: reviewed=1, rdfs:seeAlso with PDB filter
   - Category: Completeness
   - Difficulty: Hard (needs careful optimization)

**Error-Avoidance Questions**:

1. "Find proteins whose recommended name contains 'kinase'"
   - Database: UniProt
   - Knowledge Required: Split property path for bif:contains
   - Category: Structured Query
   - Difficulty: Medium

2. "Which human proteins are described as tumor suppressors in their function annotation?"
   - Database: UniProt
   - Knowledge Required: Annotation type, split path, bif:contains
   - Category: Structured Query
   - Difficulty: Medium

3. "Find proteins with 'membrane receptor' in their name"
   - Database: UniProt
   - Knowledge Required: bif:contains syntax, property path splitting
   - Category: Structured Query
   - Difficulty: Medium

**Complex Filtering Questions**:

1. "Find reviewed human proteins with GO annotations for DNA repair"
   - Database: UniProt
   - Knowledge Required: Multi-criteria, GO graph, STRSTARTS filter
   - Category: Structured Query
   - Difficulty: Medium

2. "Which human enzymes are both kinases and localized to the nucleus?"
   - Database: UniProt, GO
   - Knowledge Required: Multiple GO filters, two graphs
   - Category: Structured Query
   - Difficulty: Hard

3. "Find proteins involved in autophagy that have PDB structures"
   - Database: UniProt, GO
   - Knowledge Required: GO filtering + cross-reference filtering
   - Category: Structured Query
   - Difficulty: Hard

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the UniProt ID for human BRCA1?"
   - Method: search_uniprot_entity
   - Knowledge Required: None (straightforward search)
   - Category: Precision
   - Difficulty: Easy
   - Expected Answer: P38398

2. "What is the UniProt ID for human TP53?"
   - Method: search_uniprot_entity
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy
   - Expected Answer: P04637

3. "What is the UniProt mnemonic for insulin receptor?"
   - Method: search_uniprot_entity
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy
   - Expected Answer: INSR_HUMAN (P06213)

**ID Mapping Questions**:

1. "What is the NCBI Gene ID for UniProt protein P04637?"
   - Method: togoid_convertId
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy
   - Expected Answer: 7157

2. "What is the NCBI Gene ID for UniProt protein P38398?"
   - Method: togoid_convertId
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy
   - Expected Answer: 672

3. "What PDB structures are available for UniProt protein P04637?"
   - Method: togoid_convertId (or SPARQL)
   - Knowledge Required: None (togoid) or minimal (SPARQL)
   - Category: Integration
   - Difficulty: Easy
   - Expected Answer: 258 structures

---

## Integration Patterns Summary

**This Database as Source**:
- → Rhea: via up:enzyme (EC numbers)
- → PDB: via rdfs:seeAlso (structure links)
- → NCBI Gene: via togoid (ID conversion)
- → GO: via up:classifiedWith (functional annotation)
- → Reactome: via rdfs:seeAlso (pathway links)

**This Database as Target**:
- NCBI Gene →: via togoid (ID conversion)
- PDB →: via rdfs:seeAlso reverse lookup

**Complex Multi-Database Paths**:
- UniProt → Rhea → ChEBI: Proteins to reactions to compounds
- UniProt → GO → MONDO: Proteins to functions to diseases
- UniProt → PDB → ligands: Proteins to structures to bound compounds

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **reviewed=1 filter is non-negotiable** - Every query needs this
2. **bif:contains property path incompatibility** - Must always split paths
3. **Explicit GRAPH clauses** - Essential for multi-graph queries
4. **Pre-filtering before joins** - Dramatically improves cross-database performance
5. **Graph URI locations** - Must know exact URIs from MIE file

### Common Pitfalls Discovered

1. Missing reviewed=1 causes timeout even for simple queries
2. Property path with bif:contains causes silent 400 error
3. Cross-database queries without pre-filtering time out
4. COUNT queries on large datasets need filtering

### Recommendations for Question Design

1. Focus on questions that require reviewed=1 understanding
2. Include text search questions that need property path splitting
3. Cross-database questions with Rhea are most valuable
4. Include simple search questions for contrast (don't need MIE)
5. Performance-critical COUNT questions demonstrate MIE value clearly

### Performance Notes

- Cross-database queries: 2-6 seconds with proper filtering
- Single-database with reviewed=1: <2 seconds
- COUNT with reviewed=1: ~2 seconds
- Three-way joins: 4-6 seconds with LIMIT

---

## Notes and Observations

- UniProt's data quality difference between reviewed (Swiss-Prot) and unreviewed (TrEMBL) is massive
- The shared SIB endpoint with Rhea is extremely valuable for enzyme-reaction queries
- GO term queries require understanding of multiple graphs within UniProt
- Cross-reference patterns (rdfs:seeAlso) are powerful but need URL filtering
- bif:contains with relevance scoring (option score ?sc) enables ranked results

---

## Next Steps

**Recommended for Question Generation**:
- Priority: Cross-database UniProt-Rhea queries (demonstrate MIE value)
- High value: Text search questions requiring property path splitting
- Important: Performance-critical COUNT questions
- For contrast: Simple search tool queries

**Avoid**:
- Questions that work equally well without MIE knowledge
- Overly complex queries that require >10 seconds

**Focus areas**:
- Human proteins (most relevant to researchers)
- Enzyme-reaction relationships
- Functional annotation text search
- GO term integration

---

**Session Complete - Ready for Next Database**

```
Database: UniProt
Status: ✅ COMPLETE
Report: /evaluation/exploration/uniprot_exploration.md
Patterns Tested: 5 major patterns
Questions Identified: ~25 complex, ~10 simple
Integration Points: Rhea (primary), GO, PDB, NCBI Gene
Key Discovery: reviewed=1 and bif:contains property path splitting are critical
```
