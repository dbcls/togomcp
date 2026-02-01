# ChEBI (Chemical Entities of Biological Interest) Exploration Report

**Date**: January 31, 2026
**Session**: 1

## Executive Summary

ChEBI is a comprehensive ontology database containing 217,000+ chemical entities of biological interest with hierarchical classification, molecular data, biological roles, and extensive cross-references to 20+ external databases.

**Key Capabilities Requiring Deep Knowledge**:
- Two different property namespaces (`chebi/` for data vs `chebi#` for relationships) - using wrong namespace causes silent failures
- Biological roles encoded as OWL restrictions, not direct properties
- Cross-database integration with ChEMBL and Reactome requiring specific patterns
- URI conversion needed for Reactome integration
- Type restriction (`^^xsd:string`) required for Reactome queries

**Major Integration Opportunities**:
- ChEMBL: Drug development data via `skos:exactMatch` (high performance)
- Reactome: Metabolic pathway connections via `bp:xref` (moderate performance, requires URI conversion)
- UniProt: Enzyme catalysis (via ChEMBL or Rhea)

**Most Valuable Patterns Discovered**:
1. Namespace-aware property access (critical error avoidance)
2. OWL restriction traversal for biological roles
3. Pre-filtered cross-database joins with ChEMBL
4. URI conversion for Reactome integration

**Recommended Question Types**:
- Cross-database questions linking chemicals to drugs and pathways
- Error-avoidance questions requiring correct namespace selection
- Complex filtering with roles and cross-references

---

## Database Overview

- **Purpose**: Ontology of chemical entities of biological interest
- **Scope**: Small molecules, atoms, ions, functional groups, macromolecules
- **Size**: 217,368 chemical entities
- **Key Entity Types**: Molecular entities (owl:Class) with hierarchical classification
- **Endpoint**: https://rdfportal.org/ebi/sparql
- **Graph URI**: http://rdf.ebi.ac.uk/dataset/chebi
- **Performance**: Virtuoso backend with bif:contains full-text search

---

## Structure Analysis

### Performance Strategies

**Strategy 1: Use bif:contains for keyword search**
- Why needed: FILTER CONTAINS is slower and lacks relevance scoring
- When to apply: Any keyword-based entity search
- Performance impact: 2-5x faster, plus relevance scoring

**Strategy 2: Filter by CHEBI_ URI prefix**
- Why needed: Database contains ontology metadata classes
- When to apply: When listing chemical entities
- Performance impact: Prevents inclusion of non-chemical entries

**Strategy 3: Use LIMIT for large result sets**
- Why needed: 217K+ entities can cause timeouts
- When to apply: Any search or aggregation query
- Performance impact: Prevents timeouts, enables pagination

**Strategy 4: Pre-filter in cross-database queries**
- Why needed: Joining millions of rows causes timeouts
- When to apply: ChEMBL or Reactome integration
- Performance impact: 10-100x speedup (2.4M → ~10k molecules)

### Common Pitfalls

**Error 1: Wrong ChEBI Property Namespace**
- Pattern: Using `chebi#` instead of `chebi/` for data properties
- Cause: ChEBI has TWO namespaces - data properties use `chebi/` and relationship properties use `chebi#`
- Symptoms: Empty results for formula, mass, smiles, inchikey
- Solution: Use `PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>` for data properties
- Example:
  - WRONG: `PREFIX chebi: <http://purl.obolibrary.org/obo/chebi#>` → formula returns null
  - CORRECT: `PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>` → formula returns "C9H8O4"

**Error 2: Direct property access for roles**
- Pattern: `?entity chebi:has_role ?role`
- Cause: Roles encoded as OWL restrictions
- Symptoms: Empty results
- Solution: Traverse through `rdfs:subClassOf` → `owl:onProperty RO_0000087` → `owl:someValuesFrom`

**Error 3: Missing type restriction for Reactome**
- Pattern: `bp:db "ChEBI"` instead of `bp:db "ChEBI"^^xsd:string`
- Cause: Reactome requires explicit string type
- Symptoms: Empty results in cross-database queries
- Solution: Add `^^xsd:string` type restriction

**Error 4: Cross-database query timeout**
- Pattern: Filtering after join
- Cause: Processing millions of intermediate results
- Solution: Apply filters WITHIN source GRAPH clause before join

### Data Organization

**Data Section 1: Chemical Entity Core**
- Purpose: Base entity information
- Properties: rdfs:label, oboInOwl:id, oboInOwl:hasOBONamespace
- URI Pattern: `http://purl.obolibrary.org/obo/CHEBI_NNNN`

**Data Section 2: Molecular Properties**
- Purpose: Chemical structure data
- Properties (chebi/ namespace): formula, mass, charge, smiles, inchi, inchikey
- Coverage: ~86% with molecular data

**Data Section 3: Classification Hierarchy**
- Purpose: Ontology structure
- Property: rdfs:subClassOf
- Average parents per entity: 1.7

**Data Section 4: Biological Roles**
- Purpose: Functional classification
- Property: OWL restrictions via RO_0000087
- Examples: antibiotic, inhibitor, cofactor

**Data Section 5: Chemical Relationships**
- Purpose: Related chemical forms
- Properties (chebi# namespace): is_conjugate_acid_of, is_conjugate_base_of, is_tautomer_of, is_enantiomer_of

**Data Section 6: Cross-References**
- Purpose: External database links
- Property: oboInOwl:hasDbXref
- Format: "PREFIX:ID" literals (e.g., "DrugBank:DB00945")
- Coverage: 3,586 entities linked to DrugBank

### Cross-Database Integration Points

**Integration 1: ChEBI → ChEMBL**
- Connection relationship: `skos:exactMatch` from ChEMBL molecules
- Join point: ChEMBL molecule references ChEBI URI
- Required from ChEBI: Chemical properties, ontology classification
- Required from ChEMBL: Bioactivity data, development phase, target info
- Pre-filtering needed: CRITICAL - filter on `cco:highestDevelopmentPhase` before join
- Knowledge required: 
  - Graph URIs for both databases
  - skos:exactMatch relationship pattern
  - Pre-filtering strategy (99.5% reduction in join size)
- Performance: Tier 1 (1-3s) with proper pre-filtering
- Tested: Yes - successfully retrieved marketed drugs with ChEBI data

**Integration 2: ChEBI → Reactome**
- Connection relationship: `bp:UnificationXref` with `bp:db "ChEBI"^^xsd:string`
- Join point: URI conversion from "CHEBI:15422" → CHEBI_ URI
- Required from ChEBI: Chemical identity, molecular properties
- Required from Reactome: Pathway membership, biological context
- Pre-filtering needed: Filter pathways by name before join
- Knowledge required:
  - Type restriction `^^xsd:string` for bp:db comparisons
  - URI conversion: SUBSTR + BIND(IRI(CONCAT(...)))
  - Graph URIs for both databases
- Performance: Tier 2 (3-8s) due to property paths
- Tested: Yes - successfully linked ATP to metabolic pathways

---

## Complex Query Patterns Tested

### Pattern 1: Namespace-Critical Property Access

**Purpose**: Retrieve molecular properties for a chemical compound

**Category**: Error Avoidance

**Naive Approach (without proper knowledge)**:
Use the wrong namespace `chebi#` for data properties

**What Happened**:
- Result: Label returned correctly, but formula and mass were NULL
- Why it failed: Data properties use `chebi/` namespace, not `chebi#`

**Correct Approach (using proper pattern)**:
Use `PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>` for data properties

**What Knowledge Made This Work**:
- Key Insights:
  - ChEBI uses TWO namespaces - data (`/`) and relationships (`#`)
  - MIE file explicitly documents this in anti_patterns section
- Performance improvement: Not about performance, but correctness
- Why it works: Correct namespace resolves to actual property URIs

**Results Obtained**:
- WRONG namespace: label="acetylsalicylic acid", formula=NULL, mass=NULL
- CORRECT namespace: label="acetylsalicylic acid", formula="C9H8O4", mass="180.15740"

**Natural Language Question Opportunities**:
1. "What is the molecular formula and mass of aspirin?" - Category: Precision
2. "What are the SMILES and InChIKey identifiers for imatinib?" - Category: Precision

---

### Pattern 2: Biological Role Query via OWL Restrictions

**Purpose**: Find chemicals with specific biological roles (e.g., antibiotics)

**Category**: Structured Query

**Naive Approach (without proper knowledge)**:
Directly query `?entity chebi:has_role ?role`

**What Happened**:
- Error: Empty results
- Why it failed: Roles are encoded as OWL restrictions, not direct properties

**Correct Approach (using proper pattern)**:
Traverse through restriction structure:
```
?entity rdfs:subClassOf ?restriction .
?restriction owl:onProperty <RO_0000087> ;
             owl:someValuesFrom ?role .
```

**What Knowledge Made This Work**:
- Key Insights:
  - OWL ontology pattern for relationships
  - RO_0000087 is the "has role" property
- Why it works: OWL restrictions encode complex relationships

**Results Obtained**:
- Found entities like puromycin → nucleoside antibiotic
- Confirmed pattern works for various role types

**Natural Language Question Opportunities**:
1. "Which chemicals are classified as nucleoside antibiotics?" - Category: Completeness
2. "Find all compounds with an antibiotic insecticide role" - Category: Specificity

---

### Pattern 3: ChEMBL-ChEBI Integration for Marketed Drugs

**Purpose**: Link marketed drugs in ChEMBL to ChEBI chemical structure data

**Category**: Integration, Cross-Database

**Naive Approach (without proper knowledge)**:
Query ChEMBL molecules and ChEBI separately, filter after join

**What Happened**:
- Timeout if not pre-filtered
- Processing 2.4M ChEMBL molecules × 217K ChEBI entities

**Correct Approach (using proper pattern)**:
Pre-filter ChEMBL on `cco:highestDevelopmentPhase >= 4` BEFORE cross-database join

**What Knowledge Made This Work**:
- Key Insights:
  - skos:exactMatch links ChEMBL to ChEBI
  - Pre-filtering reduces 2.4M → ~8K molecules (99.7% reduction)
  - GRAPH clauses isolate database contexts
- Performance improvement: From timeout to 1-2 seconds
- Why it works: Early filtering dramatically reduces join size

**Results Obtained**:
- Successfully retrieved: IMATINIB, TAMOXIFEN, DOXORUBICIN, etc.
- Each with formula, mass from ChEBI
- Number of results: 20 marketed drugs in ~2s

**Natural Language Question Opportunities**:
1. "Which FDA-approved drugs have entries in both ChEMBL and ChEBI?" - Category: Integration
2. "What is the molecular formula of marketed kinase inhibitors?" - Category: Structured Query

---

### Pattern 4: ChEBI-Reactome Pathway Integration

**Purpose**: Link ChEBI metabolites to Reactome metabolic pathways

**Category**: Integration, Cross-Database

**Naive Approach (without proper knowledge)**:
Use `bp:db "ChEBI"` without type restriction

**What Happened**:
- Empty results
- Reactome's RDF uses typed literals requiring `^^xsd:string`

**Correct Approach (using proper pattern)**:
1. Use `bp:db "ChEBI"^^xsd:string`
2. Convert URI: SUBSTR(?fullChebiId, 7) → BIND(IRI(CONCAT(...)))

**What Knowledge Made This Work**:
- Key Insights:
  - Reactome requires explicit string type for bp:db
  - ChEBI ID in Reactome is "CHEBI:15422" format, needs conversion
  - URI conversion bridges different ID formats
- Performance improvement: From 0 results to working query
- Why it works: Proper type matching and URI format alignment

**Results Obtained**:
- ATP linked to multiple metabolic pathways
- Found: Phospholipid metabolism, Glycosphingolipid metabolism, etc.
- ~20 pathway connections in ~3-5 seconds

**Natural Language Question Opportunities**:
1. "Which Reactome metabolic pathways involve ATP?" - Category: Integration
2. "What metabolites are shared between glycolysis and TCA cycle pathways?" - Category: Structured Query

---

### Pattern 5: Conjugate Acid/Base Relationship Query

**Purpose**: Find chemical pairs related by acid/base conjugation

**Category**: Structured Query

**Naive Approach (without proper knowledge)**:
Directly query `?acid chebi:is_conjugate_acid_of ?base`

**What Happened**:
- Error: Empty results (if using wrong namespace)
- Or success (if using correct chebi# namespace)

**Correct Approach (using proper pattern)**:
Use `chebi#` namespace AND OWL restriction pattern:
```
?acid rdfs:subClassOf ?restriction .
?restriction owl:onProperty chebi:is_conjugate_acid_of ;
             owl:someValuesFrom ?base .
```

**What Knowledge Made This Work**:
- Key Insights:
  - Relationship properties use chebi# namespace
  - Relationships are encoded as OWL restrictions
- Why it works: Correct namespace + OWL pattern

**Results Obtained**:
- Found pairs like: warfarin ↔ warfarin(1-), nalidixic acid ↔ nalidixic acid anion
- 15+ pairs in initial query

**Natural Language Question Opportunities**:
1. "What is the conjugate base of aspirin?" - Category: Precision
2. "Find all acid-base pairs involving benzoic acid derivatives" - Category: Completeness

---

### Pattern 6: Cross-Reference to External Databases

**Purpose**: Find chemicals with links to specific external databases (e.g., DrugBank)

**Category**: Integration

**Naive Approach (without proper knowledge)**:
Unknown cross-reference format

**Correct Approach (using proper pattern)**:
Filter `oboInOwl:hasDbXref` by prefix string

**What Knowledge Made This Work**:
- Key Insights:
  - Cross-references stored as "PREFIX:ID" literals
  - Use STRSTARTS to filter by database
- Why it works: Simple string matching on standardized format

**Results Obtained**:
- 3,586 ChEBI entities linked to DrugBank
- Examples: ethanol (DB00898), chlorpromazine (DB00477), ibuprofen (DB01050)

**Natural Language Question Opportunities**:
1. "How many ChEBI compounds have DrugBank identifiers?" - Category: Completeness
2. "Which ChEBI entities are cross-referenced in KEGG?" - Category: Integration

---

### Pattern 7: Full-Text Search with Relevance Scoring

**Purpose**: Search for chemicals by keyword with relevance ranking

**Category**: Structured Query

**Naive Approach (without proper knowledge)**:
Use `FILTER(CONTAINS(LCASE(?label), "keyword"))`

**What Happened**:
- Works but slower, no relevance scoring

**Correct Approach (using proper pattern)**:
Use `bif:contains` with `option (score ?sc)` and ORDER BY DESC(?sc)

**What Knowledge Made This Work**:
- Key Insights:
  - Virtuoso backend supports bif:contains
  - Relevance scoring improves result quality
- Performance improvement: 2-5x faster
- Why it works: Full-text index vs string scanning

**Results Obtained**:
- Search for "antibiotic": top results are antibiotic pesticide, antibiotic acaricide
- Relevance scores help prioritize exact matches

**Natural Language Question Opportunities**:
1. "Find chemicals related to 'kinase inhibitor'" - Category: Specificity
2. "Search for compounds with 'anti-inflammatory' in their description" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "aspirin"
   - Found: CHEBI:15365 - acetylsalicylic acid
   - Usage: Precision questions on molecular properties

2. Search: "glucose"
   - Found: CHEBI:17234 - glucose (aldohexose)
   - Found: CHEBI:17634 - D-glucose
   - Usage: Hierarchy navigation, child term counting

3. Search: "antibiotic"
   - Found: CHEBI:39215 - antibiotic pesticide
   - Found: CHEBI:186728 - Antibiotic LA-1
   - Usage: Role-based queries

4. Search: "warfarin"
   - Found: CHEBI:10033 - warfarin
   - Found: CHEBI:50393 - warfarin(1-) (conjugate base)
   - Usage: Conjugate acid/base relationship questions

5. Direct lookup: ATP cross-references
   - Found cross-references to: DrugBank, KEGG, CAS, HMDB, PDBeChem
   - Usage: Cross-reference counting questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which FDA-approved drugs have both ChEMBL bioactivity data and ChEBI chemical classifications?"
   - Databases involved: ChEMBL, ChEBI
   - Knowledge Required: skos:exactMatch pattern, pre-filtering on development phase, GRAPH URIs
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

2. "What metabolic pathways in Reactome involve caffeine or its metabolites?"
   - Databases involved: Reactome, ChEBI
   - Knowledge Required: bp:xref type restriction, URI conversion, pathway navigation
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

3. "Which ChEBI compounds are kinase inhibitors according to ChEMBL target data?"
   - Databases involved: ChEMBL, ChEBI
   - Knowledge Required: ChEMBL activity/target path, bif:contains, pre-filtering
   - Category: Integration / Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

**Error-Avoidance Questions**:

4. "What is the molecular formula and mass of aspirin (acetylsalicylic acid)?"
   - Database: ChEBI
   - Knowledge Required: Correct namespace (chebi/) for data properties
   - Category: Precision
   - Difficulty: Medium (easy concept, tricky execution)
   - Pattern Reference: Pattern 1

5. "What are the SMILES and InChIKey identifiers for imatinib?"
   - Database: ChEBI
   - Knowledge Required: Correct namespace for molecular structure properties
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

6. "Find all compounds that function as nucleoside antibiotics"
   - Database: ChEBI
   - Knowledge Required: OWL restriction pattern for has_role (RO_0000087)
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

**Complex Filtering Questions**:

7. "How many ChEBI compounds have cross-references to DrugBank?"
   - Database: ChEBI
   - Knowledge Required: hasDbXref property, string prefix filtering
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

8. "Which chemicals are conjugate bases of common drug molecules?"
   - Database: ChEBI
   - Knowledge Required: chebi# namespace, OWL restriction pattern
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 5

9. "Find carbon-containing compounds with more than 5 database cross-references"
   - Database: ChEBI
   - Knowledge Required: Formula filtering, aggregation with HAVING, hasDbXref counting
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: MIE SPARQL examples

10. "What are the parent chemical classes of D-glucose in the ChEBI ontology?"
    - Database: ChEBI
    - Knowledge Required: rdfs:subClassOf hierarchy, CHEBI_ URI filtering
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Basic hierarchy query

**Performance-Critical Questions**:

11. "Count the total number of chemical entities with molecular formulas in ChEBI"
    - Database: ChEBI
    - Knowledge Required: Correct namespace, entity filtering
    - Category: Completeness
    - Difficulty: Medium

12. "List all ChEBI entities that are both benzoic acids and have DrugBank references"
    - Database: ChEBI
    - Knowledge Required: Hierarchy + cross-reference combination
    - Category: Structured Query
    - Difficulty: Medium

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the ChEBI identifier for aspirin?"
   - Method: OLS4 searchClasses
   - Knowledge Required: None (straightforward search)
   - Category: Entity Lookup / Precision
   - Difficulty: Easy

2. "What is the ChEBI ID for glucose?"
   - Method: OLS4 searchClasses
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "Find the ChEBI entry for warfarin"
   - Method: OLS4 searchClasses
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

4. "What is the DrugBank ID for ethanol according to ChEBI cross-references?"
   - Method: Simple xref lookup (no complex query)
   - Knowledge Required: Basic xref pattern
   - Category: Integration
   - Difficulty: Easy

5. "What is the KEGG compound ID for water?"
   - Method: Simple xref lookup
   - Knowledge Required: Basic xref pattern
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**ChEBI as Source**:
- → ChEMBL: Chemical identity for drug molecules (via skos:exactMatch)
- → Reactome: Metabolite identity for pathway molecules (via bp:xref)
- → PubChem: Structure matching via InChIKey
- → KEGG: Metabolic compound linking via hasDbXref

**ChEBI as Target**:
- ChEMBL →: Drug activity data linked to chemical structure
- Reactome →: Pathway context for metabolites
- UniProt →: Enzyme substrate/product relationships (indirect)

**Complex Multi-Database Paths**:
- ChEMBL → ChEBI → Reactome: Drug metabolism pathway discovery
- UniProt → Rhea → ChEBI: Enzyme-catalyzed reaction substrates

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **Namespace distinction** (chebi/ vs chebi#) - Critical for ANY data property query
2. **OWL restriction pattern** for roles and relationships - Required for biological role queries
3. **Cross-database type restrictions** - `^^xsd:string` for Reactome is non-obvious
4. **URI conversion patterns** - Bridging different ID formats between databases

### Common Pitfalls Discovered
1. Assuming single namespace for all properties
2. Using direct property access instead of OWL restrictions
3. Missing type restrictions in cross-database queries
4. Filtering after join instead of before

### Recommendations for Question Design
1. Include questions that FAIL with wrong namespace - demonstrates MIE value clearly
2. Cross-database questions should target ChEMBL (reliable integration) more than Reactome
3. OWL restriction queries are excellent for demonstrating structural knowledge value
4. Simple lookups via OLS4 don't need MIE - good for contrast

### Performance Notes
- Single-database queries: <2 seconds typically
- ChEMBL integration with pre-filtering: 1-3 seconds
- Reactome integration: 3-8 seconds due to property paths
- bif:contains significantly faster than FILTER CONTAINS

---

## Notes and Observations

- ChEBI is well-maintained with monthly updates
- ~86% of entities have molecular data
- Cross-references are comprehensive (20+ databases)
- OWL structure adds complexity but enables rich queries
- EBI endpoint is shared with ChEMBL, Reactome, Ensembl

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Namespace-critical queries, ChEMBL integration, role-based queries
- Avoid: Deep recursive hierarchy queries (may timeout)
- Focus areas: Marketed drugs, metabolic compounds, antibiotics

**Further Exploration Needed** (if any):
- Tautomer relationships (not fully tested)
- Enantiomer queries
- Three-way integration patterns (limited testing)

---

**Session Complete - Ready for Next Database**

**Session Summary**:
```
Database: ChEBI
Status: ✅ COMPLETE
Report: /evaluation/exploration/chebi_exploration.md
Patterns Tested: 7 major patterns
Questions Identified: 17 (12 complex, 5 simple)
Integration Points: 4 major (ChEMBL, Reactome, UniProt/indirect, KEGG)
Key Finding: Namespace distinction (chebi/ vs chebi#) is critical error-avoidance pattern
```
