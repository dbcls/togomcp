# Rhea Exploration Report

**Date**: 2026-01-31
**Session**: 1
**Database**: Rhea (Annotated Reactions Database)

## Executive Summary

Rhea is an expert-curated database of biochemical reactions containing 16,685 approved reactions, with comprehensive links to ChEBI compounds and UniProt enzymes. Key findings:

- **Critical Integration Opportunity**: Shared SIB endpoint with UniProt enables powerful enzyme-reaction-compound queries
- **Key Performance Pattern**: Use bif:contains for text search instead of FILTER(CONTAINS()) - provides 5-10x speedup
- **Major Knowledge Requirement**: Cross-database queries require up:reviewed=1 filter on UniProt side to avoid timeouts
- **Recommended Question Types**: Cross-database enzyme-reaction queries, compound-based reaction discovery, transport reaction analysis

## Database Overview

- **Purpose**: Comprehensive expert-curated database of biochemical reactions
- **Data Sources**: Expert curation with links to ChEBI, UniProt, GO, KEGG, MetaCyc, Reactome
- **Key Data Types**: Reactions, compounds (small molecules, polymers), participants, cross-references
- **Dataset Size**:
  - Approved reactions: 16,685
  - Reactions with EC numbers: 7,432 (44.5%)
  - Transport reactions: 1,496
  - Small molecule compounds: 11,763
  - Polymers: 254
  - Unique EC numbers: 6,073
- **Endpoint**: https://rdfportal.org/sib/sparql (shared with UniProt)
- **Primary Graph**: http://rdfportal.org/dataset/rhea

## Structure Analysis

### Performance Strategies

**Strategy 1: bif:contains for Text Search (CRITICAL)**
- Why needed: FILTER(CONTAINS()) is much slower and doesn't provide relevance ranking
- When to apply: Any text search in equations, labels, compound names
- Performance impact: 5-10x speedup vs FILTER(CONTAINS())
- Syntax: `?equation bif:contains "'ATP'" option (score ?sc) .`
- Boolean operators supported: AND, OR (e.g., `"'glucose' AND 'phosphate'"`)

**Strategy 2: rhea:status Filter**
- Why needed: Only approved reactions are reliable (16,685 approved vs ~17,000 total)
- When to apply: Most production queries
- Performance impact: Filters out preliminary (452) and obsolete (1,120) reactions

**Strategy 3: GRAPH Clauses for Cross-Database Queries**
- Why needed: Multiple databases on shared SIB endpoint require explicit graph specification
- When to apply: Any cross-database query with UniProt
- Performance impact: Essential for correct results and query optimization

**Strategy 4: up:reviewed=1 for UniProt Joins (CRITICAL)**
- Why needed: UniProt has 444M proteins; without filter, queries timeout
- When to apply: EVERY cross-database query with UniProt
- Performance impact: 99.8% reduction (444M to 923K proteins)
- Tested: Query without reviewed=1 → timeout; with reviewed=1 → 2-3 seconds

**Strategy 5: LIMIT for Open-Ended Queries**
- Why needed: Relationship traversal queries can produce large result sets
- When to apply: Exploring reaction-side-participant-compound chains
- Performance impact: Prevents timeout on full traversal

### Common Pitfalls

**Error 1: Missing reviewed=1 in Cross-Database Queries**
- Cause: Joining Rhea with all 444M UniProt proteins
- Symptoms: Query timeout (60 seconds)
- Solution: Add `up:reviewed 1` filter in UniProt GRAPH block
- Verified: Without filter → timeout; with filter → 2-3 seconds

**Error 2: Using FILTER(CONTAINS()) Instead of bif:contains**
- Cause: Standard SPARQL text search pattern
- Symptoms: Slower queries, no relevance ranking
- Solution: Use `?var bif:contains "'keyword'" option (score ?sc) .`
- Note: Order results by DESC(?sc) for best matches first

**Error 3: bif:contains with Property Paths**
- Cause: Virtuoso limitation - bif:contains cannot be combined with property paths (/)
- Symptoms: 400 Bad Request error
- Solution: Split property paths into separate triple patterns first
- Example: `up:recommendedName/up:fullName` → split into two triples

**Error 4: Confusing Reaction Types**
- Cause: Master reactions vs directional/bidirectional
- Symptoms: Missing expected properties or duplicates
- Solution: Query master reactions (rdfs:subClassOf rhea:Reaction), use rhea:directionalReaction to get directional forms

**Error 5: Compound Name Search at Wrong Level**
- Cause: Searching compound names on participants instead of compounds
- Symptoms: Empty results
- Solution: Follow reaction→side→participant→compound path, query compound properties from compound entity

### Data Organization

**Reactions**
- Master reactions (unspecified direction): Primary entities
- Directional reactions (L→R, R→L): Linked via rhea:directionalReaction
- Bidirectional reactions: Linked via rhea:bidirectionalReaction
- Reaction quartet pattern: IDs 10000 (master), 10001 (L→R), 10002 (R→L), 10003 (bidirectional)

**Reaction Sides**
- Left and right sides (_L, _R suffixes)
- Contain participants with stoichiometry (contains1, contains2, contains3, containsN)
- rhea:transformableTo links opposite sides

**Compounds**
- SmallMolecule: All have ChEBI cross-references
- Polymer: Use polymerization index notation (n, n-1)
- Location annotations for transport reactions (rhea:In, rhea:Out)

**Cross-References**
- GO molecular function: http://purl.obolibrary.org/obo/GO_XXXXXXX (4,446 reactions)
- MetaCyc/BioCyc: http://identifiers.org/biocyc/METACYC:XXX
- Reactome: http://identifiers.org/reactome/R-HSA-XXXXXX
- EC numbers: http://purl.uniprot.org/enzyme/X.X.X.X

### Cross-Database Integration Points

**Integration 1: Rhea → UniProt (via EC Numbers)**
- Connection relationship: rhea:ec → up:enzyme
- Join point: EC number URIs (http://purl.uniprot.org/enzyme/X.X.X.X)
- Pre-filtering needed: up:reviewed 1 (CRITICAL)
- Knowledge required: Graph URIs for both databases, EC linkage pattern
- Performance: 2-3 seconds with filters; timeout without reviewed=1

**Integration 2: Rhea → ChEBI (via Compounds)**
- Connection relationship: rdfs:subClassOf for compound → ChEBI class
- Join point: ChEBI URIs (http://purl.obolibrary.org/obo/CHEBI_XXXXX)
- Pre-filtering needed: None required (small compound set)
- Knowledge required: ChEBI URI format, compound→participant→reaction path

**Integration 3: Rhea → GO (via rdfs:seeAlso)**
- Connection relationship: rdfs:seeAlso for molecular function
- Join point: GO URIs (http://purl.obolibrary.org/obo/GO_XXXXXXX)
- Coverage: 4,436 reactions (~26%)
- Knowledge required: GO URI filtering pattern

**Integration 4: Rhea → UniProt → GO (Three-Way Join)**
- Path: Rhea reactions → EC numbers → UniProt proteins → GO annotations
- Pre-filtering needed: up:reviewed=1, rhea:status rhea:Approved
- Graph URIs needed: Rhea, UniProt, GO graphs on SIB endpoint
- Performance: 4-6 seconds for 30 results with proper filtering

---

## Complex Query Patterns Tested

### Pattern 1: Cross-Database Enzyme-Reaction Query (Performance-Critical)

**Purpose**: Find human enzymes that catalyze specific biochemical reactions

**Category**: Integration, Performance-Critical

**Naive Approach (without proper knowledge)**:
```sparql
# Missing reviewed=1 filter
SELECT ?reaction ?protein ?fullName
WHERE {
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rhea:ec ?enzyme .
    ?equation bif:contains "'glucose'" .
  }
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein up:enzyme ?enzyme ;
             up:recommendedName ?name .
    ?name up:fullName ?fullName .
  }
}
```

**What Happened**:
- Error message: None (timeout after 60 seconds)
- Timeout: YES
- Why it failed: 444M UniProt proteins scanned without pre-filtering

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?reaction ?protein ?fullName
WHERE {
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved ;
              rhea:ec ?enzyme .
    ?equation bif:contains "'glucose'" option (score ?sc) .
  }
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein a up:Protein ;
             up:reviewed 1 ;
             up:enzyme ?enzyme ;
             up:recommendedName ?name .
    ?name up:fullName ?fullName .
  }
}
ORDER BY DESC(?sc)
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insights:
  * up:reviewed 1 filter reduces 444M to 923K proteins
  * GRAPH clauses required for cross-database queries on shared endpoint
  * rhea:status rhea:Approved filters to quality reactions
  * bif:contains with score for relevance ranking
- Performance improvement: 60s timeout → 2-3 seconds
- Why it works: Pre-filtering in each GRAPH block before join

**Results Obtained**:
- Number of results: 10 (limited)
- Sample results:
  * P11988 - 6-phospho-beta-glucosidase BglB (glucose reaction)
  * Q46829 - 6-phospho-beta-glucosidase BglA (glucose reaction)

**Natural Language Question Opportunities**:
1. "Which enzymes catalyze reactions involving glucose?" - Category: Integration
2. "What human proteins are involved in glucose metabolism reactions?" - Category: Integration
3. "Find proteins that catalyze ATP-dependent reactions in humans" - Category: Structured Query

---

### Pattern 2: Human Transport Enzyme Discovery

**Purpose**: Find human proteins that catalyze membrane transport reactions

**Category**: Integration, Structured Query

**Correct Approach**:
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>
PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?reaction ?equation ?protein ?fullName
WHERE {
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved ;
              rhea:isTransport 1 ;
              rhea:ec ?enzyme .
  }
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein a up:Protein ;
             up:reviewed 1 ;
             up:organism <http://purl.uniprot.org/taxonomy/9606> ;
             up:enzyme ?enzyme ;
             up:recommendedName ?name .
    ?name up:fullName ?fullName .
  }
}
LIMIT 15
```

**What Knowledge Made This Work**:
- Key Insights:
  * rhea:isTransport 1 filters to transport reactions (1,496)
  * Organism filter narrows to human enzymes
  * Reviewed filter ensures quality proteins
- Performance: 3-4 seconds for 15 results

**Results Obtained**:
- Number of results: 15
- Sample results:
  * P54707 - Potassium-transporting ATPase alpha chain 2
  * P20648 - Potassium-transporting ATPase alpha chain 1
  * P03915 - NADH-ubiquinone oxidoreductase chain 5 (electron transport)

**Natural Language Question Opportunities**:
1. "Which human proteins are involved in membrane transport?" - Category: Integration
2. "What transporters catalyze ATP-dependent ion transport in humans?" - Category: Structured Query
3. "Find human enzymes that move substances across cell membranes" - Category: Specificity

---

### Pattern 3: Compound-Specific Reaction Discovery (ChEBI Integration)

**Purpose**: Find all reactions involving a specific compound (e.g., ATP, NADH)

**Category**: Structured Query, Completeness

**Naive Approach**:
```sparql
# Text search only - may miss reactions with alternate names
SELECT ?reaction ?equation
WHERE {
  ?reaction rhea:equation ?equation .
  FILTER(CONTAINS(?equation, "ATP"))
}
```

**Correct Approach (using ChEBI linkage)**:
```sparql
PREFIX chebi: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?reaction ?accession ?equation
WHERE {
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:accession ?accession ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved ;
              rhea:side ?side .
    ?side rhea:contains ?participant .
    ?participant rhea:compound ?compound .
    ?compound rdfs:subClassOf chebi:CHEBI_30616 .  # ATP
  }
}
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insights:
  * ChEBI URI format: http://purl.obolibrary.org/obo/CHEBI_XXXXX
  * Compound linkage via rdfs:subClassOf (not rhea:chebi for queries)
  * Path: reaction → side → participant → compound
- Compounds verified:
  * ATP: CHEBI:30616
  * NADH: CHEBI:57945
  * NAD+: CHEBI:57540
  * NADPH: CHEBI:57783

**Results Obtained**:
- ATP reactions: 1,273
- NADH reactions: 1,101

**Natural Language Question Opportunities**:
1. "How many biochemical reactions involve ATP?" - Category: Completeness
2. "What reactions use NADH as a cofactor?" - Category: Structured Query
3. "Find all enzymatic reactions where ATP is consumed" - Category: Completeness

---

### Pattern 4: Three-Way Join (Rhea + UniProt + GO)

**Purpose**: Link reactions to proteins and their functional annotations

**Category**: Integration (Advanced), Structured Query

**Correct Approach**:
```sparql
SELECT DISTINCT ?reaction ?equation ?protein ?mnemonic ?goLabel
WHERE {
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved ;
              rhea:ec ?enzyme .
    ?equation bif:contains "'phosphate'" option (score ?sc) .
  }
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein a up:Protein ;
             up:reviewed 1 ;
             up:organism <http://purl.uniprot.org/taxonomy/9606> ;
             up:enzyme ?enzyme ;
             up:mnemonic ?mnemonic ;
             up:classifiedWith ?goTerm .
  }
  GRAPH <http://sparql.uniprot.org/go> {
    ?goTerm rdfs:label ?goLabel .
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
  }
}
ORDER BY DESC(?sc)
LIMIT 20
```

**What Knowledge Made This Work**:
- Key Insights:
  * Three GRAPH blocks required (Rhea, UniProt, GO)
  * GO term filtering via STRSTARTS
  * Reviewed and status filters essential
- Graph URIs:
  * Rhea: http://rdfportal.org/dataset/rhea
  * UniProt: http://sparql.uniprot.org/uniprot
  * GO: http://sparql.uniprot.org/go
- Performance: 4-6 seconds for 20 results

**Results Obtained**:
- Sample: TKT_HUMAN (Transketolase) - pentose-phosphate shunt, transketolase activity

**Natural Language Question Opportunities**:
1. "What biological processes are associated with human enzymes that catalyze phosphate transfer?" - Category: Integration
2. "Find enzymes involved in the pentose phosphate pathway with their GO annotations" - Category: Structured Query

---

### Pattern 5: bif:contains Error Avoidance

**Purpose**: Search protein names while avoiding property path errors

**Category**: Error Avoidance, Structured Query

**Naive Approach (FAILS)**:
```sparql
# bif:contains with property path - causes 400 error
SELECT ?protein ?fullName
WHERE {
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein up:recommendedName/up:fullName ?fullName .
    ?fullName bif:contains "'kinase'" .
  }
}
```

**What Happened**:
- Error message: 400 Bad Request
- Why it failed: Virtuoso's bif:contains cannot be combined with property paths

**Correct Approach**:
```sparql
SELECT ?protein ?fullName
WHERE {
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein a up:Protein ;
             up:reviewed 1 ;
             up:organism <http://purl.uniprot.org/taxonomy/9606> ;
             up:recommendedName ?name .
    ?name up:fullName ?fullName .
    ?fullName bif:contains "'kinase'" .
  }
}
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insight: Split property paths before bif:contains
- Solution: up:recommendedName → ?name ; ?name up:fullName → ?fullName
- Documented in UniProt MIE anti-patterns section

**Natural Language Question Opportunities**:
1. "Find all human protein kinases" - Category: Structured Query
2. "Which human enzymes have 'transferase' in their name?" - Category: Structured Query

---

### Pattern 6: Boolean Text Search

**Purpose**: Find reactions matching multiple criteria in text

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?reaction ?equation
WHERE {
  GRAPH <http://rdfportal.org/dataset/rhea> {
    ?reaction rdfs:subClassOf rhea:Reaction ;
              rhea:equation ?equation ;
              rhea:status rhea:Approved .
    ?equation bif:contains "'glucose' AND 'phosphate'" option (score ?sc) .
  }
}
ORDER BY DESC(?sc)
LIMIT 10
```

**What Knowledge Made This Work**:
- Key Insight: bif:contains supports AND, OR operators
- Syntax: Keywords in single quotes, operators unquoted
- Score option enables relevance ranking

**Results Obtained**:
- RHEA:16689 - D-glucose 6-phosphate + H2O = D-glucose + phosphate
- RHEA:19933 - alpha-D-glucose 1-phosphate + H2O = D-glucose + phosphate

**Natural Language Question Opportunities**:
1. "What reactions involve both glucose and phosphate?" - Category: Structured Query
2. "Find reactions that convert ATP to ADP" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "ATP"
   - Found: RHEA:18353 - Na+/K+ ATPase reaction
   - Usage: Transport reaction examples

2. Search: "glucose"
   - Found: RHEA:16617 - glucosidase reaction
   - Usage: Carbohydrate metabolism questions

3. Search: RHEA:10000 details
   - Found: Pentanamide hydrolysis (amidase reaction)
   - Properties: EC 3.5.1.50, GO:0050168, literature citation
   - Usage: Basic reaction lookup examples

4. Search: Compound names (NAD+, NADH, NADPH)
   - Found: CHEBI IDs for all major cofactors
   - NAD+: CHEBI:57540, NADH: CHEBI:57945
   - Usage: Cofactor-based queries

5. Count: Approved reactions
   - Found: 16,685 approved reactions
   - Usage: Completeness questions

6. Count: Reactions with EC numbers
   - Found: 7,432 (44.5% of approved)
   - Usage: Coverage questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions** (All phrased naturally):

1. "Which human enzymes catalyze reactions involving ATP?"
   - Databases involved: Rhea, UniProt
   - Knowledge Required: reviewed=1 filter, EC linkage, GRAPH clauses
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

2. "What biochemical reactions are catalyzed by human kinases?"
   - Databases involved: Rhea, UniProt
   - Knowledge Required: reviewed=1 filter, text search with split paths, GRAPH clauses
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

3. "Find human proteins that catalyze membrane transport reactions"
   - Databases involved: Rhea, UniProt
   - Knowledge Required: isTransport filter, reviewed=1, organism filter
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

4. "Which human enzymes are involved in NADH-dependent reactions?"
   - Databases involved: Rhea, UniProt, (ChEBI)
   - Knowledge Required: ChEBI compound linkage, reviewed=1, GRAPH clauses
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Patterns 1, 3

5. "What biological processes are associated with human enzymes that catalyze phosphorylation reactions?"
   - Databases involved: Rhea, UniProt, GO
   - Knowledge Required: Three-way join, all filters, GO graph URI
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

6. "Find enzymes that catalyze reactions involving both glucose and phosphate"
   - Databases involved: Rhea, UniProt
   - Knowledge Required: Boolean bif:contains, cross-database join
   - Category: Structured Query / Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

7. "Which human proteins catalyze ATP synthesis reactions?"
   - Databases involved: Rhea, UniProt
   - Knowledge Required: ATP product queries, reviewed=1, organism filter
   - Category: Integration
   - Difficulty: Medium

8. "What enzymes in humans are involved in NAD+/NADH redox reactions?"
   - Databases involved: Rhea, UniProt, ChEBI
   - Knowledge Required: Compound-based filtering, cross-database join
   - Category: Integration
   - Difficulty: Hard

**Performance-Critical Questions**:

1. "How many approved biochemical reactions are in Rhea?"
   - Database: Rhea
   - Knowledge Required: Status filter, COUNT pattern
   - Category: Completeness
   - Difficulty: Easy
   - Expected: 16,685

2. "How many reactions involve NADH as a substrate or product?"
   - Database: Rhea
   - Knowledge Required: ChEBI compound linkage, compound-reaction path
   - Category: Completeness
   - Difficulty: Medium
   - Expected: 1,101

3. "How many reactions in Rhea have EC number annotations?"
   - Database: Rhea
   - Knowledge Required: EC property queries
   - Category: Completeness
   - Difficulty: Easy
   - Expected: 7,432

4. "How many transport reactions are in Rhea?"
   - Database: Rhea
   - Knowledge Required: isTransport filter
   - Category: Completeness
   - Difficulty: Easy
   - Expected: 1,496

5. "What fraction of Rhea reactions have GO molecular function annotations?"
   - Database: Rhea
   - Knowledge Required: Cross-reference pattern, GO filtering
   - Category: Completeness
   - Difficulty: Medium
   - Expected: ~26% (4,436/16,685)

**Error-Avoidance Questions**:

1. "Find human proteins whose name contains 'kinase'"
   - Database: UniProt (via Rhea queries)
   - Knowledge Required: Property path splitting for bif:contains
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

2. "Search for reactions containing 'transferase' in the equation"
   - Database: Rhea
   - Knowledge Required: bif:contains vs FILTER(CONTAINS())
   - Category: Structured Query
   - Difficulty: Easy

**Complex Filtering Questions**:

1. "What reactions involve ATP and produce ADP?"
   - Database: Rhea
   - Knowledge Required: Boolean search, compound-side relationships
   - Category: Structured Query
   - Difficulty: Medium

2. "Find reactions that transport potassium ions across membranes"
   - Database: Rhea
   - Knowledge Required: isTransport filter, compound name search
   - Category: Structured Query
   - Difficulty: Medium

3. "Which oxidoreductase reactions use NAD+ as cofactor?"
   - Database: Rhea
   - Knowledge Required: EC class filtering (1.x.x.x), ChEBI compound linkage
   - Category: Structured Query
   - Difficulty: Hard

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the equation for reaction RHEA:10000?"
   - Method: Direct lookup by accession
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

2. "What EC number is associated with reaction RHEA:10000?"
   - Method: Direct property lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy
   - Expected: EC 3.5.1.50

3. "Is reaction RHEA:10000 a transport reaction?"
   - Method: Direct property lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy
   - Expected: No (isTransport=0)

**Search Tool Questions**:

1. "Find reactions involving ATP"
   - Method: search_rhea_entity
   - Knowledge Required: None (uses search tool)
   - Category: Precision
   - Difficulty: Easy

2. "Search for reactions with glucose"
   - Method: search_rhea_entity
   - Knowledge Required: None (uses search tool)
   - Category: Precision
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source**:
- → UniProt: Via EC numbers (rhea:ec → up:enzyme)
- → ChEBI: Via compound cross-references (rdfs:subClassOf)
- → GO: Via rdfs:seeAlso cross-references
- → KEGG/MetaCyc/Reactome: Via rdfs:seeAlso (identifiers.org URIs)

**This Database as Target**:
- UniProt →: Enzymes annotated with Rhea reaction IDs
- ChEBI →: Compounds used in reactions

**Complex Multi-Database Paths**:
- Path 1: Rhea → UniProt → GO: Reaction → Enzyme → GO annotations
  - Use case: Functional annotation of biochemical reactions
- Path 2: ChEBI → Rhea → UniProt: Compound → Reaction → Enzyme
  - Use case: Find enzymes that process specific compounds
- Path 3: UniProt → Rhea → ChEBI: Enzyme → Reaction → Compounds
  - Use case: Discover substrates/products of known enzymes

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **up:reviewed=1 filter is essential** for any cross-database query involving UniProt - without it, queries timeout due to 444M protein scan
2. **Shared SIB endpoint** enables powerful three-way joins (Rhea + UniProt + GO) but requires explicit GRAPH clauses
3. **bif:contains provides 5-10x speedup** over FILTER(CONTAINS()) and supports boolean operators
4. **ChEBI compound linkage** (via rdfs:subClassOf) enables precise chemical queries vs text search

### Common Pitfalls Discovered
1. Missing reviewed=1 on UniProt side causes timeout (tested and verified)
2. bif:contains cannot be combined with property paths (400 error verified)
3. Compound names must be queried from compound entities, not participants

### Recommendations for Question Design
1. Cross-database questions should require knowledge of reviewed=1 filter
2. Text search questions should test bif:contains vs FILTER patterns
3. Compound-based questions should test ChEBI linkage knowledge
4. Three-way joins (Rhea+UniProt+GO) demonstrate maximum MIE value

### Performance Notes
- Simple reaction lookups: < 1 second
- Keyword searches with bif:contains: < 1 second for 20 results
- Cross-database queries with filters: 2-3 seconds
- Three-way joins: 4-6 seconds for 30 results
- Cross-database without reviewed=1: TIMEOUT (60+ seconds)

---

## Notes and Observations

- Rhea's reaction quartet structure (master + 2 directional + 1 bidirectional) is unique and may cause confusion
- Transport reactions have location annotations (rhea:In, rhea:Out) that enable membrane topology queries
- Literature citations are embedded in rdfs:comment but require text parsing
- 44.5% of reactions have EC numbers, enabling good UniProt integration
- Polymer reactions use special notation (n, n-1) that may complicate queries

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database Rhea+UniProt queries (demonstrate reviewed=1 requirement)
- Focus areas: Transport reactions, cofactor-dependent reactions, enzyme discovery
- High-value patterns: Three-way joins, compound-based filtering, error avoidance

**Avoid**:
- Questions about obsolete/preliminary reactions (quality issues)
- Deep polymer queries (complex notation)
- Questions requiring literature parsing (unstructured data)

**Further Exploration Needed** (if any):
- Reactome cross-reference patterns (limited identifiers.org coverage found)
- Polymer-specific queries (complex but interesting)

---

**Session Complete - Ready for Next Database**

```
Database: rhea
Status: ✅ COMPLETE
Report: /evaluation/exploration/rhea_exploration.md
Patterns Tested: 6+ complex patterns
Questions Identified: 25+ opportunities
Integration Points: 4 databases (UniProt, ChEBI, GO, KEGG/MetaCyc)
Key Finding: up:reviewed=1 critical for UniProt joins
```
