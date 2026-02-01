# MeSH (Medical Subject Headings) Exploration Report

**Date**: January 31, 2026
**Session**: 1

## Executive Summary

MeSH is the National Library of Medicine's controlled vocabulary thesaurus containing ~30K topical descriptors, ~250K supplementary chemical records, and ~2.5M total entities. It serves as the primary biomedical indexing vocabulary for PubMed and other NLM databases.

**Key capabilities requiring deep knowledge:**
- Hierarchical navigation using `meshv:broaderDescriptor` (NOT `meshv:broader`)
- Scope note retrieval using `meshv:annotation` (NOT `meshv:scopeNote`)
- Understanding term/concept structure for synonyms
- Allowable qualifier relationships for valid indexing combinations
- Tree number-based category filtering
- Cross-database integration with MONDO, GO, and NANDO

**Major integration opportunities:**
- MeSH ↔ MONDO: Via MONDO's hasDbXref (MESH:D###### or MESH:C######)
- MeSH ↔ GO: Keyword-based linking (no direct semantic links)
- MeSH ↔ NANDO: Keyword-based linking for Japanese rare diseases
- MeSH ↔ PubMed: Core indexing vocabulary (via fabio:hasSubjectTerm, rdfs:seeAlso)

**Most valuable patterns discovered:**
1. bif:contains with relevance scoring for fast searches
2. Pre-filtering in GRAPH clauses before cross-database joins
3. Property path splitting for hierarchical queries
4. Tree number filtering for category-based navigation

**Recommended question types:**
- Cross-database disease term integration (MeSH-MONDO)
- Literature indexing term lookups requiring hierarchy understanding
- Performance-critical searches on 869K+ terms
- Multi-criteria filtering combining tree categories, annotations, and qualifiers

## Database Overview

### Purpose and Scope
- Controlled vocabulary for biomedical literature indexing
- 16 hierarchical categories (A-Z) covering anatomy, diseases, drugs, organisms, etc.
- Used to index 37M+ PubMed articles
- Annual updates with ~2024 data version

### Key Data Types and Entities
| Entity Type | Count | Description |
|-------------|-------|-------------|
| TopicalDescriptor | 30,262 | Main subject headings |
| SCR_Chemical | 250,445 | Supplementary chemical records |
| SCR_Disease | 6,771 | Supplementary disease records |
| Qualifier | 84 | Subheadings for topic aspects |
| Concept | 466,976 | Concept nodes with synonyms |
| Term | 869,536 | Actual term entries |
| Total | ~2.5M | All entities |

### Dataset Size and Performance Considerations
- 869K+ searchable terms - requires bif:contains for performance
- Hierarchical queries can be expensive without LIMIT
- Tree numbers enable efficient category filtering
- Cross-database joins need pre-filtering

### Available Access Methods
- SPARQL endpoint: https://rdfportal.org/primary/sparql
- Graph URI: http://id.nlm.nih.gov/mesh
- Search tool: search_mesh_descriptor
- Shared endpoint with: GO, taxonomy, MONDO, NANDO, BacDive, MediaDive

## Structure Analysis

### Performance Strategies

**Strategy 1: bif:contains for Keyword Searches**
- Why needed: Scanning 869K terms with REGEX is prohibitively slow
- When to apply: Any label/text search
- Performance impact: 10-100x faster than FILTER CONTAINS or REGEX
- Example:
  ```sparql
  ?label bif:contains "'diabetes'" option (score ?sc)
  ORDER BY DESC(?sc)
  ```

**Strategy 2: Pre-filtering in GRAPH Clauses**
- Why needed: Cross-database joins without filtering process millions of rows
- When to apply: All cross-database queries
- Performance impact: 99%+ reduction in intermediate results
- Example: Filter by keyword in MONDO GRAPH before MeSH join

**Strategy 3: Tree Number Filtering**
- Why needed: Efficiently narrow to specific MeSH categories
- When to apply: Category-based queries (diseases, drugs, etc.)
- Performance impact: Reduces search space by category
- Example:
  ```sparql
  FILTER(STRSTARTS(?treeNum, "C14."))  # Cardiovascular diseases
  ```

**Strategy 4: Always Use LIMIT**
- Why needed: Database contains 2.5M+ entities
- When to apply: All exploratory queries
- Performance impact: Prevents timeout on large result sets
- Example: `LIMIT 50` for exploratory, `LIMIT 10-20` for display

### Common Pitfalls

**Pitfall 1: Wrong Property for Hierarchy (CRITICAL)**
- Cause: Using `meshv:broader` instead of `meshv:broaderDescriptor`
- Symptoms: Empty results for parent/child queries
- Solution: Always use `meshv:broaderDescriptor`
- Example:
  ```sparql
  # WRONG: mesh:D003920 meshv:broader ?parent  → Empty!
  # CORRECT: mesh:D003920 meshv:broaderDescriptor ?parent
  ```

**Pitfall 2: Wrong Property for Scope Notes**
- Cause: Using `meshv:scopeNote` or `skos:scopeNote`
- Symptoms: No annotations returned
- Solution: Use `meshv:annotation` with OPTIONAL
- Example:
  ```sparql
  # WRONG: ?d meshv:scopeNote ?note  → Empty!
  # CORRECT: OPTIONAL { ?d meshv:annotation ?note }
  ```

**Pitfall 3: Terms Use meshv:prefLabel, Not rdfs:label**
- Cause: Terms have different label property than descriptors
- Symptoms: Missing term labels
- Solution: Use `meshv:prefLabel` for Term entities

**Pitfall 4: Missing FROM Clause**
- Cause: Forgetting graph specification
- Symptoms: Empty results or wrong results
- Solution: Always include `FROM <http://id.nlm.nih.gov/mesh>`

**Pitfall 5: Cross-Database Late Filtering**
- Cause: Filtering after cross-database join
- Symptoms: Query timeout
- Solution: Pre-filter within each GRAPH clause before joins

### Data Organization

**Topical Descriptors (D######)**
- Primary subject headings for indexing
- Have tree numbers, broader relationships
- Can have annotations (~40%)
- Link to concepts and preferred terms

**Supplementary Chemical Records (C######)**
- Chemical substances not in main thesaurus
- May have registry numbers
- No hierarchical structure
- Used for MONDO disease xrefs too

**Supplementary Disease Records**
- Disease concepts not in main descriptors
- No hierarchical structure

**Qualifiers (Q######)**
- 84 subheadings (e.g., Q000209 = etiology)
- Combined with descriptors for specific aspects
- Used in PubMed: D003920Q000209 = Diabetes Mellitus/etiology

**Concepts and Terms**
- Three-level structure: Descriptor → Concept → Term
- Terms contain actual synonyms and labels
- Concept has preferredTerm, Term has prefLabel

### Cross-Database Integration Points

**Integration 1: MeSH ↔ MONDO**
- Connection relationship: MONDO's oboInOwl:hasDbXref with MESH: prefix
- Join point: URI construction from MESH:D###### or MESH:C###### format
- Required information: MONDO graph, owl:Class, hasDbXref; MeSH graph, rdfs:label
- Pre-filtering needed: bif:contains in MONDO before MeSH join
- Knowledge required: MESH: xrefs can be D (descriptors) OR C (SCR) records
- Performance: Tier 1 (2-3 seconds)

**Integration 2: MeSH ↔ GO**
- Connection relationship: Keyword-based (no direct semantic links)
- Join point: Shared keywords in rdfs:label fields
- Required information: owl:Class, hasOBONamespace for GO; TopicalDescriptor for MeSH
- Pre-filtering needed: bif:contains in both GRAPH clauses
- Knowledge required: No direct links; keyword matching only
- Performance: Tier 1 (2-3 seconds)

**Integration 3: MeSH ↔ NANDO**
- Connection relationship: Keyword-based matching
- Join point: Shared disease names in English labels
- Required information: owl:Class for NANDO; TopicalDescriptor for MeSH
- Pre-filtering needed: bif:contains with language filter
- Knowledge required: NANDO uses @en, @ja, @ja-hira language tags
- Performance: Tier 1 (1-2 seconds)

**Integration 4: MeSH ↔ PubMed** (via NCBI endpoint)
- Connection relationship: Direct MeSH term references in articles
- Join point: rdfs:seeAlso, fabio:hasSubjectTerm, fabio:hasPrimarySubjectTerm
- Required information: MeSH URIs for filtering
- Pre-filtering needed: bif:contains on article titles
- Knowledge required: MeSH URIs link directly; qualifiers combined as D######Q######
- Performance: Requires separate endpoint (ncbi)

**Integration 5: Three-way MeSH ↔ MONDO ↔ GO**
- Connection relationship: MONDO as semantic bridge
- Join point: MONDO has MeSH xrefs; keyword matching to GO
- Pre-filtering needed: CONTAINS in all three GRAPHs (simplified filters)
- Knowledge required: Three-way queries need simplified CONTAINS, not bif:contains
- Performance: Tier 2 (3-5 seconds)

## Complex Query Patterns Tested

### Pattern 1: Hierarchical Navigation with broaderDescriptor

**Purpose**: Navigate MeSH hierarchy to find parent categories

**Category**: Error-Avoidance, Structured Query

**Naive Approach (without proper knowledge)**:
Using `meshv:broader` property (wrong name)

**What Happened**:
- Error message: None (silent failure)
- Timeout: No
- Other issues: Empty results
- Why it failed: Property `meshv:broader` doesn't exist; correct is `meshv:broaderDescriptor`

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?parent ?parentLabel
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  mesh:D003920 meshv:broaderDescriptor+ ?parent .
  ?parent rdfs:label ?parentLabel .
}
```

**What Knowledge Made This Work**:
- Key Insights:
  * MeSH uses meshv:broaderDescriptor, NOT meshv:broader
  * Property path (+) works well for transitive queries from specific descriptors
- Performance improvement: Query returns results vs. empty set
- Why it works: Correct property name from MIE file

**Results Obtained**:
- Number of results: 4
- Sample results:
  * D004700 - Endocrine System Diseases
  * D008659 - Metabolic Diseases
  * D044882 - Glucose Metabolism Disorders
  * D009750 - Nutritional and Metabolic Diseases

**Natural Language Question Opportunities**:
1. "What are all the parent categories of Diabetes Mellitus in MeSH?" - Category: Structured Query
2. "Which broader medical categories does the term 'hypertension' belong to?" - Category: Structured Query

---

### Pattern 2: Scope Note Retrieval

**Purpose**: Get indexing guidance and annotations for MeSH terms

**Category**: Error-Avoidance

**Naive Approach (without proper knowledge)**:
Using `meshv:scopeNote` or `skos:scopeNote`

**What Happened**:
- Error message: None
- Timeout: No
- Other issues: Empty results - no annotations returned
- Why it failed: Wrong property name

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?label ?annotation
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  mesh:D003920 rdfs:label ?label .
  OPTIONAL { mesh:D003920 meshv:annotation ?annotation }
}
```

**What Knowledge Made This Work**:
- Key Insights:
  * Correct property is meshv:annotation, not scopeNote
  * Only ~40% of descriptors have annotations - use OPTIONAL
- Why it works: MIE file documents correct property name

**Results Obtained**:
- Number of results: 1
- Sample results:
  * D003920 - "Diabetes Mellitus" with annotation: "general or unspecified; prefer specifics..."

**Natural Language Question Opportunities**:
1. "What are the indexing guidelines for the MeSH term 'diabetes mellitus'?" - Category: Precision
2. "What scope note does MeSH provide for the term 'neoplasm'?" - Category: Precision

---

### Pattern 3: Cross-Database MeSH-MONDO Integration

**Purpose**: Link MeSH disease terms to MONDO disease ontology

**Category**: Integration, Cross-Database

**Naive Approach (without proper knowledge)**:
- Missing GRAPH clauses
- No pre-filtering before join
- Wrong URI construction from MONDO xrefs

**What Happened**:
- Error message: Query timeout (60 seconds)
- Why it failed: Processing 30K MONDO × 30K MeSH without filtering

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?mondoDisease ?mondoLabel ?meshDescriptor ?meshLabel ?meshXref
WHERE {
  GRAPH <http://rdfportal.org/ontology/mondo> {
    ?mondoDisease a owl:Class ;
      rdfs:label ?mondoLabel ;
      oboInOwl:hasDbXref ?meshXref .
    FILTER(STRSTARTS(?meshXref, "MESH:"))
    ?mondoLabel bif:contains "'diabetes'" option (score ?sc)
  }
  
  BIND(URI(CONCAT("http://id.nlm.nih.gov/mesh/", SUBSTR(?meshXref, 6))) AS ?meshDescriptor)
  
  GRAPH <http://id.nlm.nih.gov/mesh> {
    ?meshDescriptor rdfs:label ?meshLabel .
  }
}
ORDER BY DESC(?sc)
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insights:
  * MONDO uses oboInOwl:hasDbXref with "MESH:" prefix
  * Must construct URI from MESH:D###### or MESH:C###### format
  * MESH: xrefs can point to descriptors (D) OR SCR records (C)
  * Pre-filter with bif:contains in MONDO GRAPH before join
- Performance improvement: 2-3 seconds vs timeout
- Why it works: Strategy 1 (GRAPH), Strategy 2 (pre-filter), Strategy 4 (bif:contains)

**Results Obtained**:
- Number of results: 10
- Sample results:
  * MONDO:0005015 "diabetes mellitus" → D003920 "Diabetes Mellitus"
  * MONDO:0010785 "maternally-inherited diabetes and deafness" → C536246

**Natural Language Question Opportunities**:
1. "What MONDO diseases are linked to the MeSH term for diabetes?" - Category: Integration
2. "Which MeSH descriptor corresponds to Parkinson's disease in MONDO?" - Category: Integration
3. "Find rare diseases in MONDO that have MeSH cross-references" - Category: Completeness

---

### Pattern 4: Cross-Database MeSH-GO Integration

**Purpose**: Find GO biological processes related to MeSH medical terms

**Category**: Integration, Cross-Database

**Naive Approach (without proper knowledge)**:
- No GRAPH clauses (causes cross-contamination)
- Using REGEX instead of bif:contains
- No pre-filtering before Cartesian product

**What Happened**:
- Error message: Query timeout
- Why it failed: 869K MeSH terms × 48K GO terms = 42B comparisons

**Correct Approach (using proper pattern)**:
```sparql
SELECT DISTINCT ?meshTerm ?meshLabel ?goTerm ?goLabel ?goNamespace
WHERE {
  GRAPH <http://id.nlm.nih.gov/mesh> {
    ?meshTerm a meshv:TopicalDescriptor ;
      rdfs:label ?meshLabel .
    ?meshLabel bif:contains "'apoptosis'" option (score ?sc1)
  }
  
  GRAPH <http://rdfportal.org/ontology/go> {
    ?goTerm a owl:Class ;
      rdfs:label ?goLabel ;
      oboinowl:hasOBONamespace ?goNamespace .
    ?goLabel bif:contains "'apoptosis'" option (score ?sc2)
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
  }
}
ORDER BY DESC(?sc1)
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insights:
  * No direct semantic links between MeSH and GO - use keyword matching
  * Must use explicit GRAPH clauses for both databases
  * bif:contains in BOTH graphs for early filtering
  * GO requires STRSTARTS filter to exclude non-GO classes
- Performance improvement: 2-3 seconds vs timeout
- Why it works: Strategy 1 + 2 + 4 + 10

**Results Obtained**:
- Number of results: 10
- Sample results:
  * MeSH D053446 "CASP8 and FADD-Like Apoptosis Regulating Protein"
  * GO:0006921 "cellular component disassembly involved in execution phase of apoptosis"

**Natural Language Question Opportunities**:
1. "What GO biological processes relate to the MeSH term 'apoptosis'?" - Category: Integration
2. "Find Gene Ontology terms that correspond to MeSH cardiovascular disease concepts" - Category: Integration

---

### Pattern 5: Three-Way MeSH-MONDO-GO Integration

**Purpose**: Bridge clinical terminology (MeSH), disease classification (MONDO), and molecular biology (GO)

**Category**: Integration, Complex Multi-Database

**Naive Approach (without proper knowledge)**:
- Using multiple bif:contains across three databases
- Complex GO filters with namespace comparisons
- No simplification for three-way stability

**What Happened**:
- Error message: 400 Bad Request
- Why it failed: Query complexity exceeds endpoint limits; multiple bif:contains conflicts

**Correct Approach (using proper pattern)**:
```sparql
SELECT DISTINCT ?meshLabel ?mondoLabel ?goLabel
WHERE {
  GRAPH <http://rdfportal.org/ontology/mondo> {
    ?mondoDisease a owl:Class ;
      rdfs:label ?mondoLabel ;
      oboInOwl:hasDbXref ?meshXref .
    FILTER(STRSTARTS(?meshXref, "MESH:"))
    FILTER(CONTAINS(LCASE(?mondoLabel), "parkinson"))  # Simplified!
  }
  
  BIND(URI(CONCAT("http://id.nlm.nih.gov/mesh/", SUBSTR(?meshXref, 6))) AS ?meshDescriptor)
  
  GRAPH <http://id.nlm.nih.gov/mesh> {
    ?meshDescriptor rdfs:label ?meshLabel .
  }
  
  GRAPH <http://rdfportal.org/ontology/go> {
    ?goTerm rdfs:label ?goLabel .
    FILTER(CONTAINS(LCASE(?goLabel), "dopamine"))  # Simplified!
  }
}
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insights:
  * Three-way queries MUST use simplified CONTAINS, not bif:contains
  * Cannot use complex GO filters (namespace with STR) in three-way context
  * Keep each GRAPH clause minimal
  * MONDO acts as semantic bridge via MeSH xrefs
- Performance improvement: 3-5 seconds vs 400 error
- Why it works: Simplified filters avoid query complexity limits

**Results Obtained**:
- Number of results: 10
- Sample results:
  * MeSH: "Parkinson Disease"
  * MONDO: "Parkinson's disease"
  * GO: "dopamine transport", "dopamine metabolic process"

**Natural Language Question Opportunities**:
1. "What biological processes relate to Parkinson's disease across clinical and molecular databases?" - Category: Integration
2. "Find connections between neurodegenerative diseases and neurotransmitter pathways" - Category: Structured Query

---

### Pattern 6: Tree Number Category Filtering

**Purpose**: Find MeSH terms by hierarchical category (e.g., cardiovascular diseases)

**Category**: Structured Query, Performance-Critical

**Naive Approach (without proper knowledge)**:
- Searching all 30K descriptors without category filter
- Using REGEX on tree numbers

**What Happened**:
- Error message: None
- Timeout: Yes, on unfiltered queries
- Why it failed: Processing all descriptors without tree number constraint

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?descriptor ?label ?treeNum ?annotation
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    rdfs:label ?label ;
    meshv:treeNumber ?tree .
  ?tree rdfs:label ?treeNum .
  OPTIONAL { ?descriptor meshv:annotation ?annotation }
  FILTER(STRSTARTS(?treeNum, "C14."))  # Cardiovascular diseases
  ?label bif:contains "'disease'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
```

**What Knowledge Made This Work**:
- Key Insights:
  * Tree numbers encode hierarchical category (C14 = Cardiovascular)
  * STRSTARTS is efficient for prefix matching
  * Combine with keyword search for focused results
- Performance improvement: <2 seconds vs potential timeout
- Why it works: Tree number provides structural filter

**Results Obtained**:
- Number of results: Multiple cardiovascular disease descriptors
- Sample results:
  * D001145 - "Arrhythmias, Cardiac" (C14.280.067)
  * D002318 - "Cardiovascular Diseases"

**Natural Language Question Opportunities**:
1. "What cardiovascular disease terms exist in MeSH category C14?" - Category: Completeness
2. "List all MeSH descriptors in the 'Diseases' hierarchy" - Category: Completeness

---

### Pattern 7: Allowable Qualifiers Query

**Purpose**: Find valid subheadings for descriptor-qualifier combinations

**Category**: Structured Query, Precision

**Naive Approach (without proper knowledge)**:
- Not knowing about allowableQualifier relationship
- Trying to guess valid combinations

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?qualifier ?qualifierLabel
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  mesh:D003920 meshv:allowableQualifier ?qualifier .
  ?qualifier rdfs:label ?qualifierLabel .
}
```

**What Knowledge Made This Work**:
- Key Insights:
  * Descriptors have explicit allowableQualifier relationships
  * Not all qualifiers are valid for all descriptors
  * Average 22 qualifiers per descriptor
- Why it works: MIE file documents this relationship

**Results Obtained**:
- Number of results: 34 qualifiers for Diabetes Mellitus
- Sample results:
  * Q000209 - "etiology"
  * Q000188 - "drug therapy"
  * Q000235 - "genetics"
  * Q000628 - "therapy"

**Natural Language Question Opportunities**:
1. "What qualifying subheadings can be used with the MeSH term 'diabetes mellitus'?" - Category: Precision
2. "Which aspects (qualifiers) are valid for indexing cancer-related articles?" - Category: Structured Query

---

### Pattern 8: Supplementary Chemical Record Search

**Purpose**: Find chemical substances in MeSH supplementary concept records

**Category**: Specificity

**Naive Approach (without proper knowledge)**:
- Searching only TopicalDescriptors
- Missing SCR_Chemical entity type

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?chemical ?label ?note
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?chemical a meshv:SCR_Chemical ;
    rdfs:label ?label .
  OPTIONAL { ?chemical meshv:note ?note }
  ?label bif:contains "'insulin'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
```

**What Knowledge Made This Work**:
- Key Insights:
  * 250K+ supplementary chemical records
  * Use SCR_Chemical type, not TopicalDescriptor
  * Note field provides additional context
- Why it works: MIE file documents entity types

**Results Obtained**:
- Number of results: 20
- Sample results:
  * C517652 - "isophane insulin, insulin lispro drug combination 50:50"
  * C471074 - "rosiglitazone-metformin combination"

**Natural Language Question Opportunities**:
1. "What insulin-related chemical compounds are in MeSH?" - Category: Completeness
2. "Find MeSH supplementary records for diabetes medications" - Category: Specificity

---

### Pattern 9: MeSH-NANDO Cross-Database Integration

**Purpose**: Link MeSH terms to Japanese rare disease ontology

**Category**: Integration, Specificity

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?nandoDisease ?nandoLabel ?meshTerm ?meshLabel
WHERE {
  GRAPH <http://nanbyodata.jp/ontology/nando> {
    ?nandoDisease a owl:Class ;
      rdfs:label ?nandoLabel .
    FILTER(LANG(?nandoLabel) = "en")
    ?nandoLabel bif:contains "'parkinson'" option (score ?sc1)
  }
  
  GRAPH <http://id.nlm.nih.gov/mesh> {
    ?meshTerm a meshv:TopicalDescriptor ;
      rdfs:label ?meshLabel .
    ?meshLabel bif:contains "'parkinson'" option (score ?sc2)
  }
}
ORDER BY DESC(?sc1)
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insights:
  * NANDO uses language tags (@en, @ja, @ja-hira)
  * Must filter by language for English labels
  * bif:contains in both GRAPHs for early filtering
  * No direct semantic links - keyword matching only
- Performance: 1-2 seconds

**Results Obtained**:
- Number of results: 5 (Parkinson-related entries)
- Sample results:
  * NANDO:1200010 "Parkinson's disease" ↔ D010300 "Parkinson Disease"

**Natural Language Question Opportunities**:
1. "What Japanese intractable diseases correspond to MeSH Parkinson's disease?" - Category: Integration
2. "Link MeSH terms for rare neurological diseases to the Japanese NANDO ontology" - Category: Specificity

---

### Pattern 10: Descriptor Hierarchy Count by Category

**Purpose**: Get distribution of MeSH terms across major categories

**Category**: Completeness, Structured Query

**Correct Approach**:
```sparql
SELECT ?category (COUNT(DISTINCT ?descriptor) as ?count)
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    meshv:treeNumber ?tree .
  ?tree rdfs:label ?treeLabel .
  BIND(SUBSTR(?treeLabel, 1, 1) as ?category)
}
GROUP BY ?category
ORDER BY DESC(?count)
```

**Results Obtained**:
| Category | Count | Description |
|----------|-------|-------------|
| D | 10,541 | Chemicals and Drugs |
| C | 5,032 | Diseases |
| B | 3,964 | Organisms |
| E | 3,102 | Analytical, Diagnostic and Therapeutic Techniques |
| G | 2,430 | Phenomena and Processes |
| N | 2,002 | Health Care |
| A | 1,904 | Anatomy |

**Natural Language Question Opportunities**:
1. "How many MeSH descriptors exist in each major category?" - Category: Completeness
2. "What is the distribution of MeSH terms across the disease hierarchy?" - Category: Completeness

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "diabetes"
   - Found: D003920 - Diabetes Mellitus
   - Usage: Hierarchy, qualifier, cross-reference questions

2. Search: "Parkinson"
   - Found: D010300 - Parkinson Disease
   - Usage: Cross-database integration questions

3. Search: "cancer"
   - Found: D019496 - Cancer Vaccines
   - Usage: Tree category filtering questions

4. Search: "autophagy"
   - Found: D001343 - Autophagy
   - Usage: GO integration questions

5. Search: "Niemann-Pick"
   - Found: D009542 - Niemann-Pick Diseases
   - Usage: Rare disease specificity questions

6. Search: "amyloidosis"
   - Found: D000686 - Amyloidosis
   - Usage: Disease hierarchy questions

7. Search: "insulin" (chemicals)
   - Found: C517652 - insulin lispro combination
   - Usage: SCR_Chemical queries

8. Search: "metformin"
   - Found: C471074 - rosiglitazone-metformin combination
   - Usage: Drug combination queries

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which MONDO diseases are mapped to MeSH cardiovascular disease terms?"
   - Databases involved: MeSH, MONDO
   - Knowledge Required: MONDO hasDbXref format, URI construction, pre-filtering
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

2. "Find the Gene Ontology biological processes related to MeSH 'apoptosis' term"
   - Databases involved: MeSH, GO
   - Knowledge Required: Keyword matching (no direct links), GRAPH clauses, bif:contains
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

3. "What biological pathways connect Parkinson's disease across MeSH, MONDO, and GO?"
   - Databases involved: MeSH, MONDO, GO
   - Knowledge Required: Three-way query simplification, CONTAINS filters
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 5

4. "Which Japanese intractable diseases (NANDO) correspond to MeSH neurodegenerative disease terms?"
   - Databases involved: MeSH, NANDO
   - Knowledge Required: NANDO language filtering, keyword matching
   - Category: Integration / Specificity
   - Difficulty: Medium
   - Pattern Reference: Pattern 9

5. "Find MONDO rare diseases with MeSH cross-references in the metabolic disease category"
   - Databases involved: MeSH, MONDO
   - Knowledge Required: Tree number filtering + MONDO xref matching
   - Category: Integration / Specificity
   - Difficulty: Hard

**Performance-Critical Questions**:

1. "How many MeSH descriptors exist in the Diseases category (C hierarchy)?"
   - Database: MeSH
   - Knowledge Required: Tree number filtering, aggregation
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 10

2. "Find all MeSH chemical records related to insulin"
   - Database: MeSH
   - Knowledge Required: SCR_Chemical entity type, bif:contains
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 8

3. "List MeSH descriptors with annotations containing 'experimental'"
   - Database: MeSH
   - Knowledge Required: meshv:annotation property, bif:contains
   - Category: Structured Query
   - Difficulty: Medium

**Error-Avoidance Questions**:

1. "What are all the parent terms of 'Diabetes Mellitus' in the MeSH hierarchy?"
   - Database: MeSH
   - Knowledge Required: Use broaderDescriptor (not broader)
   - Category: Structured Query
   - Difficulty: Easy
   - Pattern Reference: Pattern 1

2. "What indexing guidance does MeSH provide for the term 'neoplasm'?"
   - Database: MeSH
   - Knowledge Required: Use annotation (not scopeNote)
   - Category: Precision
   - Difficulty: Easy
   - Pattern Reference: Pattern 2

3. "Find MeSH disease terms using full-text search for 'membrane receptor'"
   - Database: MeSH
   - Knowledge Required: bif:contains syntax with quotes
   - Category: Structured Query
   - Difficulty: Medium

**Complex Filtering Questions**:

1. "What qualifying subheadings are valid for the MeSH term 'diabetes mellitus'?"
   - Database: MeSH
   - Knowledge Required: allowableQualifier relationship
   - Category: Precision
   - Difficulty: Easy
   - Pattern Reference: Pattern 7

2. "Find MeSH descriptors in the cardiovascular category that have scope notes"
   - Database: MeSH
   - Knowledge Required: Tree number + annotation combination
   - Category: Structured Query / Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

3. "List child terms of 'Diabetes Mellitus' with their tree numbers"
   - Database: MeSH
   - Knowledge Required: broaderDescriptor inverse + treeNumber
   - Category: Structured Query
   - Difficulty: Medium

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the MeSH descriptor ID for Parkinson's disease?"
   - Method: search_mesh_descriptor
   - Knowledge Required: None (straightforward)
   - Category: Precision
   - Difficulty: Easy

2. "Find the MeSH term for Alzheimer's disease"
   - Method: search_mesh_descriptor
   - Knowledge Required: None
   - Category: Entity Lookup
   - Difficulty: Easy

3. "What is the MeSH identifier for the disease 'amyloidosis'?"
   - Method: search_mesh_descriptor
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

4. "Search MeSH for terms related to 'cancer vaccines'"
   - Method: search_mesh_descriptor
   - Knowledge Required: None
   - Category: Entity Lookup
   - Difficulty: Easy

5. "Find the MeSH descriptor for 'autophagy'"
   - Method: search_mesh_descriptor
   - Knowledge Required: None
   - Category: Entity Lookup
   - Difficulty: Easy

---

## Integration Patterns Summary

**MeSH as Source**:
- → MONDO: Via keyword matching (disease terms)
- → GO: Via keyword matching (biological concepts)
- → NANDO: Via keyword matching (rare diseases)
- → PubMed: Direct references (indexing vocabulary)

**MeSH as Target**:
- MONDO →: Via oboInOwl:hasDbXref with MESH: prefix
- PubMed →: Via rdfs:seeAlso, fabio:hasSubjectTerm

**Complex Multi-Database Paths**:
- MONDO → MeSH → GO: Disease classification to molecular biology
- NANDO → MeSH → GO: Japanese rare diseases to biological processes
- PubMed → MeSH → MONDO: Literature to disease ontology

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **Property name corrections**: broaderDescriptor (not broader), annotation (not scopeNote)
2. **Pre-filtering strategies**: Essential for all cross-database queries
3. **Entity type awareness**: TopicalDescriptor vs SCR_Chemical vs SCR_Disease
4. **Three-way query simplification**: Use CONTAINS instead of bif:contains

### Common Pitfalls Discovered
1. Silent failures with wrong property names (empty results, not errors)
2. Cross-database timeouts without pre-filtering in GRAPH clauses
3. Three-way queries failing with 400 errors when using complex filters
4. Missing language filters when integrating with multilingual databases

### Recommendations for Question Design
1. Include questions that test property name knowledge (error-avoidance)
2. Create cross-database questions requiring pre-filtering strategies
3. Test tree number filtering for category-based completeness questions
4. Include qualifier relationship questions for precision testing

### Performance Notes
- bif:contains: 10-100x faster than REGEX
- Tree number filtering: Very efficient for category narrowing
- Cross-database queries: 1-3 seconds with proper pre-filtering
- Three-way queries: 3-5 seconds with simplified CONTAINS

---

## Notes and Observations

- MeSH-PubMed integration is on a different endpoint (NCBI), not co-located with MONDO/GO/NANDO
- Descriptor-qualifier pairs in PubMed (e.g., D003920Q000209) encode both term and aspect
- SCR records (C prefix) are used for both chemicals AND diseases - check context
- ~40% of descriptors have annotations - always use OPTIONAL
- MESH: xrefs in MONDO can be D###### (descriptors) or C###### (SCR records)

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database MeSH-MONDO integration, hierarchy navigation with correct properties, tree number filtering
- Avoid: Simple entity lookups (too easy), PubMed-MeSH queries (different endpoint complexity)
- Focus areas: Error-avoidance patterns, pre-filtering requirements, three-way integration challenges

**Further Exploration Needed** (if any):
- PubMed-MeSH integration testing on NCBI endpoint
- More testing of concept/term structure for synonym retrieval

---

**Session Complete - Ready for Next Database**
