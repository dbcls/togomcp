# ChEMBL Exploration Report

**Date**: January 31, 2026
**Session**: 1

## Executive Summary

ChEMBL is a comprehensive database of bioactive molecules containing 2.4M+ compounds, 21M+ bioactivity measurements, 1.6M assays, and 13,000+ targets. This exploration identified key patterns for:
- Complex bioactivity queries requiring understanding of the molecule-activity-assay-target model
- Cross-database integration with ChEBI (chemical ontology) and UniProt (protein data)
- Performance-critical queries requiring pre-filtering on development phase and organism
- Drug discovery research questions involving kinase inhibitors, drug mechanisms, and clinical indications

Key findings:
- ChEMBL-ChEBI integration works reliably with 1-2 second response times when properly pre-filtered
- ChEMBL-Reactome integration is complex and may timeout; simpler approaches via UniProt IDs work better
- Activity measurements require careful attention to units (nM vs uM) and activity types (IC50, EC50, Ki)
- pChembl provides normalized potency values for cross-assay comparison

## Database Overview

- **Purpose**: Drug discovery and development - bioactive molecules with drug-like properties
- **Key data types**: 
  - SmallMolecule (2.4M+ compounds)
  - Activity (21M+ bioactivity measurements)
  - Assay (1.6M assays)
  - Target (13K+ targets, primarily human proteins)
  - DrugIndication (disease indications with MeSH terms)
  - DrugMechanism (mechanism of action data)
- **Dataset size**: Large (2.4M molecules, 21M activities - some queries may timeout)
- **Endpoint**: https://rdfportal.org/ebi/sparql
- **Graph URI**: http://rdf.ebi.ac.uk/dataset/chembl
- **Co-located databases on EBI endpoint**: ChEBI, Reactome, Ensembl

## Structure Analysis

### Performance Strategies

**Strategy 1: Always use FROM/GRAPH clause**
- Why: Prevents cross-contamination between databases on shared endpoint
- When: All ChEMBL queries
- Impact: Essential for correctness; also helps query optimizer

**Strategy 2: Pre-filtering on development phase**
- Why: 2.4M molecules → ~3,700 marketed drugs (phase=4) = 99.8% reduction
- When: Any drug-focused query
- Impact: Reduces query time from timeout to sub-second

**Strategy 3: Use bif:contains for text search**
- Why: Virtuoso-optimized full-text search with relevance scoring
- When: Searching by target name, molecule name, or any text field
- Impact: Much faster than FILTER/REGEX; provides relevance ranking

**Strategy 4: Filter by organism for targets**
- Why: Reduces human protein queries from 13K targets to relevant subset
- When: Human-focused drug discovery queries
- Impact: Significant performance improvement

**Strategy 5: Specify activity type and units**
- Why: Without filtering, comparing IC50 < 100 could mix nM and uM
- When: All activity value comparisons
- Impact: Essential for correctness

**Strategy 6: Use LIMIT appropriately**
- Why: Large result sets can overwhelm response
- When: All exploratory queries
- Impact: Prevents timeouts and memory issues

### Common Pitfalls

**Pitfall 1: Mixing activity units**
- Cause: ~97% of IC50 values are in nM, but some use ug/mL or other units
- Symptoms: Incorrect potency comparisons
- Solution: Always filter by `cco:standardUnits "nM"` (or appropriate unit)
- Example: `FILTER(?units = "nM")` required when filtering by IC50 value

**Pitfall 2: FILTER/REGEX instead of bif:contains**
- Cause: Using REGEX for text matching
- Symptoms: Slow queries, no relevance ranking
- Solution: Use bif:contains for Virtuoso-optimized search
- Example:
  ```sparql
  # Wrong:
  FILTER(REGEX(?label, "kinase", "i"))
  # Correct:
  ?label bif:contains "'kinase'" option (score ?sc)
  ```

**Pitfall 3: Missing pre-filtering in cross-database queries**
- Cause: Filtering after join instead of before
- Symptoms: Timeout (>60 seconds)
- Solution: Apply FILTER within source GRAPH before cross-database join
- Example: Filter `cco:highestDevelopmentPhase >= 3` INSIDE ChEMBL GRAPH block

**Pitfall 4: Cross-database query without explicit GRAPH clauses**
- Cause: Omitting GRAPH specification in cross-endpoint queries
- Symptoms: Empty results or cross-contamination
- Solution: Always use explicit GRAPH clauses for cross-database queries

### Data Organization

**Core Entity Model**:
- SmallMolecule → Activity → Assay → Target → TargetComponent → UniProt
- This path connects drugs to their protein targets

**Drug Data**:
- `cco:highestDevelopmentPhase`: 0 (preclinical) to 4 (marketed)
- `cco:atcClassification`: ATC drug classification codes
- DrugIndication: Links to MeSH disease terms with development phase
- DrugMechanism: Action type (INHIBITOR, AGONIST, etc.) with target

**Bioactivity Data**:
- `cco:standardType`: IC50, EC50, Ki, etc.
- `cco:standardValue`: Numeric value
- `cco:standardUnits`: nM, uM, etc.
- `cco:pChembl`: Normalized potency (-log10 of molar value)

**Cross-References**:
- `cco:moleculeXref`: Links to PubChem, DrugBank, ChEBI, etc.
- `skos:exactMatch`: Used for ChEBI chemical ontology links
- TargetComponent uses `skos:exactMatch` for UniProt links

### Cross-Database Integration Points

**Integration 1: ChEMBL → ChEBI (Chemical Ontology)**
- Connection: `skos:exactMatch` from SmallMolecule to ChEBI class
- Graph URIs: chembl + chebi graphs on EBI endpoint
- Pre-filtering: `cco:highestDevelopmentPhase >= 3` reduces 2.4M to ~10K
- Information from each:
  - ChEMBL: Drug name, development phase, activities
  - ChEBI: Chemical formula, mass, InChI, ontology classification
- Performance: 1-2 seconds with proper pre-filtering (Tier 1)
- Tested: Yes - works reliably

**Integration 2: ChEMBL → UniProt (Protein Targets)**
- Connection: `cco:hasTargetComponent/skos:exactMatch` to UniProt URI
- Information from each:
  - ChEMBL: Target name, organism, activity data
  - UniProt: Protein sequence, function, structure, pathway data
- Pre-filtering: Filter by organism and target type in ChEMBL first
- Performance: Fast when querying just IDs
- Tested: Yes - 20 UniProt links for Imatinib targets retrieved

**Integration 3: ChEMBL → PubChem (via cco:moleculeXref)**
- Connection: `cco:moleculeXref` to PubChem compound URI
- Pre-filtering: Filter by development phase first
- Tested: Yes - direct cross-reference links work

**Integration 4: ChEMBL → DrugBank (via cco:moleculeXref)**
- Connection: `cco:moleculeXref` to DrugBank drug URI
- Pre-filtering: Filter by phase=4 for approved drugs
- Tested: Yes - direct cross-reference links work

**Integration 5: ChEMBL → MeSH (Disease Indications)**
- Connection: `cco:hasMesh` from DrugIndication to MeSH disease terms
- `cco:hasMeshHeading`: Human-readable disease name
- Pre-filtering: Filter by development phase
- Tested: Yes - works reliably

**Integration 6: ChEMBL → Reactome (Pathways) - COMPLEX**
- Connection: Via UniProt as bridge protein
- Complexity: Requires matching UniProt IDs between ChEMBL and Reactome
- Issues: Complex property paths, may timeout
- Tested: Attempted but timed out; simpler approach using just UniProt IDs works

## Complex Query Patterns Tested

### Pattern 1: Potent Inhibitor Discovery (Performance-Critical)

**Purpose**: Find compounds with high potency against a specific target

**Category**: Performance-Critical, Structured Query

**Naive Approach (without proper knowledge)**:
Query all activities then filter by value

**What Knowledge Made This Work**:
- Key Insights:
  * Must specify `cco:standardType "IC50"` for comparable measurements
  * Must filter by `cco:standardUnits "nM"` to avoid unit mixing
  * Pre-filter by target ID for performance
- Performance: ~2-3 seconds
- Why it works: Direct target ID filtering eliminates need to search all activities

**Results Obtained**:
- Found very potent EGFR inhibitors
- Sample: TAK-020 (5e-9 nM), OSIMERTINIB (0.002 nM), AFATINIB (0.01 nM), MOBOCERTINIB (0.01 nM)
- All are known clinical EGFR inhibitors

**Natural Language Question Opportunities**:
1. "What are the most potent inhibitors of the EGFR receptor?" - Category: Structured Query
2. "Which approved drugs target the epidermal growth factor receptor with IC50 below 10 nM?" - Category: Precision
3. "Find the top kinase inhibitors by potency against human EGFR" - Category: Completeness

---

### Pattern 2: Marketed Drug Search with Text Filter (bif:contains)

**Purpose**: Find approved drugs by target name using text search

**Category**: Performance-Critical, Structured Query

**Naive Approach**:
Using FILTER(REGEX()) which is slow

**Correct Approach**:
```sparql
?targetName bif:contains "'kinase'" option (score ?sc)
ORDER BY DESC(?sc)
```

**What Knowledge Made This Work**:
- Key Insights:
  * bif:contains is Virtuoso-specific and much faster
  * Provides relevance scoring for result ranking
  * Supports Boolean operators (AND, OR, NOT)
- Performance: ~1-2 seconds vs potential timeout with REGEX

**Results Obtained**:
- Found 20+ human kinase targets
- Includes MAP kinases, thymidine kinases, adenylate kinases
- Relevance scoring orders results by keyword frequency

**Natural Language Question Opportunities**:
1. "What human kinase proteins are drug targets in ChEMBL?" - Category: Completeness
2. "Find protein targets whose names contain 'kinase'" - Category: Structured Query
3. "How many human kinases have been targeted by drugs in clinical trials?" - Category: Completeness

---

### Pattern 3: Cross-Database ChEMBL-ChEBI Integration

**Purpose**: Enrich drug data with chemical ontology information

**Category**: Integration, Cross-Database

**Naive Approach (without proper knowledge)**:
Filter after join - causes timeout

**What Happened Without MIE Knowledge**:
- Query processes 2.4M molecules before filtering
- Joins to ChEBI for all molecules
- Times out (>60 seconds)

**Correct Approach (using MIE Strategy 2)**:
```sparql
GRAPH <http://rdf.ebi.ac.uk/dataset/chembl> {
  ?molecule skos:exactMatch ?chebiId ;
            cco:highestDevelopmentPhase ?phase .
  FILTER(?phase >= 3)  # Pre-filter BEFORE join!
}
GRAPH <http://rdf.ebi.ac.uk/dataset/chebi> {
  ?chebiId rdfs:label ?chebiLabel .
}
```

**What Knowledge Made This Work**:
- Key Insights:
  * GRAPH clauses isolate databases
  * Pre-filtering reduces 2.4M → ~10K (99.5% reduction)
  * ChEBI provides formula, mass via chebi: namespace
- Performance: 1-2 seconds (Tier 1)

**Results Obtained**:
- 20+ marketed drugs with ChEBI chemical data
- Examples: ABACAVIR (C14H18N6O), ACETAMINOPHEN/paracetamol (C8H9NO2)
- Formula and mass available via OPTIONAL

**Natural Language Question Opportunities**:
1. "What is the molecular formula of FDA-approved kinase inhibitors?" - Category: Integration
2. "Find marketed drugs with their chemical structures from ChEBI" - Category: Integration
3. "Which approved drugs have ChEBI chemical ontology information available?" - Category: Completeness

---

### Pattern 4: Drug-Disease Indication Query

**Purpose**: Find drugs indicated for specific diseases

**Category**: Structured Query, Precision

**Naive Approach**:
Text search on disease names without structure

**Correct Approach**:
```sparql
?indication a cco:DrugIndication ;
            cco:hasMolecule ?molecule ;
            cco:hasMeshHeading ?disease ;
            cco:highestDevelopmentPhase ?phase .
FILTER(CONTAINS(LCASE(?disease), "diabetes"))
FILTER(?phase >= 3)
```

**What Knowledge Made This Work**:
- Key Insights:
  * DrugIndication is separate entity linking molecule to disease
  * hasMeshHeading provides human-readable disease name
  * hasMesh provides MeSH URI for integration
  * Phase filtering reduces result set

**Results Obtained**:
- Found 30+ drugs for diabetes indications
- Includes METFORMIN, GLIPIZIDE, INSULIN GLARGINE, LINAGLIPTIN
- Both Type 1 and Type 2 diabetes distinguished

**Natural Language Question Opportunities**:
1. "What approved drugs are indicated for Type 2 diabetes?" - Category: Structured Query
2. "Find all marketed medications for diabetes treatment" - Category: Completeness
3. "Which drugs have clinical trial evidence for diabetes mellitus?" - Category: Currency

---

### Pattern 5: Drug Mechanism of Action Analysis

**Purpose**: Find drugs by their mechanism (inhibitor, agonist, etc.)

**Category**: Structured Query

**Correct Approach**:
```sparql
?mechanism a cco:Mechanism ;
           cco:mechanismActionType ?mechanismType ;
           cco:hasMolecule ?molecule ;
           cco:hasTarget ?target .
FILTER(?mechanismType = "INHIBITOR")
FILTER(?phase = 4)
```

**What Knowledge Made This Work**:
- Key Insights:
  * DrugMechanism entity connects molecule → target with action type
  * Mechanism types: INHIBITOR (3506), ANTAGONIST (968), AGONIST (942)
  * Human target filtering via cco:organismName

**Results Obtained**:
- Found 20+ approved inhibitor drugs
- Examples: SIMVASTATIN (HMG-CoA reductase), ERLOTINIB (EGFR), COLCHICINE (Tubulin)
- Clear mechanism-target-drug relationships

**Natural Language Question Opportunities**:
1. "What are the protein targets of FDA-approved inhibitor drugs?" - Category: Structured Query
2. "Find all marketed kinase inhibitors and their mechanisms" - Category: Integration
3. "Which approved drugs act as enzyme inhibitors?" - Category: Completeness

---

### Pattern 6: pChembl Normalized Potency Search

**Purpose**: Find ultra-potent compounds using normalized potency

**Category**: Structured Query, Performance-Critical

**Correct Approach**:
```sparql
?activity cco:pChembl ?pChembl .
FILTER(xsd:decimal(?pChembl) > 9)  # Very potent
```

**What Knowledge Made This Work**:
- Key Insights:
  * pChembl = -log10(molar IC50/EC50/Ki value)
  * pChembl > 9 means sub-nanomolar potency
  * Allows comparison across different activity types

**Results Obtained**:
- Found compounds with pChembl > 14 (femtomolar potency!)
- Examples: RITTERAZINE B (pChembl 14.92), CEPHALOSTATIN 1 (14.82)
- These are natural product cytotoxins

**Natural Language Question Opportunities**:
1. "What are the most potent bioactive compounds in ChEMBL?" - Category: Precision
2. "Find compounds with sub-nanomolar potency against any target" - Category: Structured Query
3. "Which molecules have pChembl values above 10?" - Category: Completeness

---

### Pattern 7: Marketed Kinase Inhibitors with ChEBI (Advanced Cross-Database)

**Purpose**: Find FDA-approved kinase inhibitors with chemical structure data

**Category**: Integration, Advanced

**What Knowledge Made This Work**:
- Key Insights:
  * Double pre-filtering: phase=4 AND kinase text search
  * Property path optimization: hasActivity/hasAssay/hasTarget
  * Cross-database join to ChEBI for formulas
- Performance: 2-3 seconds (Tier 1-2)

**Results Obtained**:
- Found kinase-targeted approved drugs
- Examples: SORAFENIB, SUNITINIB, MIDOSTAURIN
- Chemical formulas from ChEBI

**Natural Language Question Opportunities**:
1. "What FDA-approved drugs target kinase proteins and what are their chemical formulas?" - Category: Integration
2. "List marketed kinase inhibitors with their molecular structures" - Category: Completeness
3. "Find approved cancer drugs that inhibit kinases" - Category: Structured Query

---

### Pattern 8: Target-UniProt Mapping

**Purpose**: Link ChEMBL targets to UniProt protein identifiers

**Category**: Integration

**Correct Approach**:
```sparql
?target cco:hasTargetComponent ?component .
?component skos:exactMatch ?uniprot .
FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
```

**What Knowledge Made This Work**:
- Key Insights:
  * TargetComponent bridges Target to UniProt
  * skos:exactMatch for semantic equivalence
  * URI pattern filtering for UniProt links specifically

**Results Obtained**:
- Found 20 UniProt IDs for Imatinib targets
- Includes BCR-ABL (main target), plus off-targets like EGFR, KIT
- Enables further integration with UniProt data

**Natural Language Question Opportunities**:
1. "What are the UniProt IDs for proteins targeted by Imatinib?" - Category: Integration
2. "Find all protein targets of a drug with their UniProt accessions" - Category: Completeness
3. "Link ChEMBL drug targets to UniProt for sequence analysis" - Category: Integration

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "imatinib"
   - Found: CHEMBL941 - IMATINIB (also CHEMBL1642 - IMATINIB MESYLATE)
   - Usage: Drug mechanism, target mapping, cross-database questions

2. Search: "EGFR human"
   - Found: CHEMBL203 - Epidermal growth factor receptor (Homo sapiens)
   - Usage: Target-based queries, potent inhibitor searches

3. Query: Marketed drugs count
   - Found: 3,678 molecules with phase=4
   - Usage: Understand dataset scope

4. Query: Total molecules
   - Found: 1,920,809 small molecules
   - Usage: Understand need for filtering

5. Query: Activity types
   - Found: Potency (4.4M), IC50 (2.8M), GI50 (2.6M), Inhibition (1.5M), Ki (775K)
   - Usage: Understanding what activity types to query

6. Query: Mechanism types
   - Found: INHIBITOR (3506), ANTAGONIST (968), AGONIST (942)
   - Usage: Mechanism-based drug queries

7. Query: IC50 units distribution
   - Found: 97% in nM (2.5M), small amounts in ug/mL and other units
   - Usage: Confirms need for unit filtering

8. Cross-reference: PubChem
   - Found: CHEMBL1000 (CETIRIZINE) → PubChem CID 2678
   - Usage: ID conversion questions

9. Cross-reference: DrugBank
   - Found: CHEMBL1380 (ABACAVIR) → DB01048
   - Usage: Drug database integration

10. TogoID conversion: CHEMBL941 → PubChem 5291
    - Usage: ID conversion questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What is the molecular formula of the kinase inhibitor Imatinib according to ChEBI?"
   - Databases: ChEMBL, ChEBI
   - Knowledge Required: skos:exactMatch pattern, chebi:formula property
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

2. "Which FDA-approved drugs targeting EGFR have ChEBI chemical structure information available?"
   - Databases: ChEMBL, ChEBI
   - Knowledge Required: Pre-filtering by phase=4 and target ID, cross-database join
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 7

3. "What are the UniProt protein IDs for all targets of the cancer drug Sorafenib?"
   - Databases: ChEMBL, (indirect to UniProt)
   - Knowledge Required: Target → TargetComponent → skos:exactMatch path
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 8

4. "Find marketed kinase inhibitors and their chemical formulas from ChEBI"
   - Databases: ChEMBL, ChEBI
   - Knowledge Required: Double pre-filtering, bif:contains, cross-database join
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 7

5. "What approved drugs have indications for both cancer and inflammatory diseases?"
   - Databases: ChEMBL (DrugIndication entity)
   - Knowledge Required: DrugIndication model, MeSH integration
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

**Performance-Critical Questions**:

1. "How many compounds in ChEMBL have IC50 values below 10 nM against any human kinase?"
   - Database: ChEMBL
   - Knowledge Required: Unit filtering, activity type filtering, target text search
   - Category: Completeness
   - Difficulty: Hard
   - Pattern Reference: Pattern 1, Pattern 2

2. "What are the top 10 most potent inhibitors of human EGFR by IC50?"
   - Database: ChEMBL
   - Knowledge Required: Pre-filter by target ID, unit specification, ordering
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

3. "Count the number of FDA-approved drugs that target each major drug target class"
   - Database: ChEMBL
   - Knowledge Required: Early filtering by phase=4, GROUP BY optimization
   - Category: Completeness
   - Difficulty: Hard
   - Pattern Reference: Requires aggregation patterns

4. "Find all drugs indicated for diabetes with activity data against any target"
   - Database: ChEMBL
   - Knowledge Required: DrugIndication + Activity join, pre-filtering
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 4, Pattern 5

**Error-Avoidance Questions**:

1. "Compare the potency (IC50) of different EGFR inhibitors in nanomolar units"
   - Database: ChEMBL
   - Knowledge Required: MUST filter by cco:standardUnits "nM"
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 1, Pitfall 1

2. "Find proteins in ChEMBL whose names contain 'receptor' using efficient search"
   - Database: ChEMBL
   - Knowledge Required: bif:contains vs REGEX, relevance scoring
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 2, Pitfall 2

3. "Search for drugs by their mechanism text description"
   - Database: ChEMBL
   - Knowledge Required: bif:contains with proper quoting
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

**Complex Filtering Questions**:

1. "What approved kinase inhibitors have mechanism of action data in ChEMBL?"
   - Database: ChEMBL
   - Knowledge Required: DrugMechanism entity, phase filtering, target text search
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 5

2. "Find compounds with pChembl > 9 (sub-nanomolar potency) against human targets"
   - Database: ChEMBL
   - Knowledge Required: pChembl for normalized potency comparison
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

3. "What drugs are both marketed (phase 4) and have IC50 < 100 nM against their primary target?"
   - Database: ChEMBL
   - Knowledge Required: Multiple filters, activity + molecule join
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

4. "Find all antagonist drugs targeting G protein-coupled receptors"
   - Database: ChEMBL
   - Knowledge Required: DrugMechanism filtering, target text search
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 5, Pattern 2

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the ChEMBL ID for the drug Imatinib?"
   - Method: search_chembl_molecule("imatinib")
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

2. "What is the ChEMBL target ID for human EGFR?"
   - Method: search_chembl_target("EGFR human")
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "Find the ChEMBL ID for the antihistamine cetirizine"
   - Method: search_chembl_molecule("cetirizine")
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

4. "What is the development phase of Osimertinib in ChEMBL?"
   - Method: Simple SPARQL lookup by name
   - Knowledge Required: Minimal
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

1. "What is the PubChem compound ID for ChEMBL compound CHEMBL941 (Imatinib)?"
   - Method: togoid_convertId or cco:moleculeXref query
   - Knowledge Required: TogoID route or cross-reference pattern
   - Category: Integration
   - Difficulty: Easy

2. "Convert the ChEMBL compound ID CHEMBL25 to its DrugBank identifier"
   - Method: SPARQL query for cco:moleculeXref
   - Knowledge Required: Cross-reference URI pattern
   - Category: Integration
   - Difficulty: Easy

3. "What is the UniProt ID for ChEMBL target CHEMBL203?"
   - Method: TargetComponent → skos:exactMatch query
   - Knowledge Required: Basic cross-reference pattern
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**ChEMBL as Source**:
- → ChEBI: Via skos:exactMatch (chemical ontology)
- → UniProt: Via cco:hasTargetComponent/skos:exactMatch (protein targets)
- → PubChem: Via cco:moleculeXref (compound data)
- → DrugBank: Via cco:moleculeXref (drug database)
- → MeSH: Via cco:hasMesh from DrugIndication (disease terms)
- → NCBI Taxonomy: Via cco:taxonomy (organism data)

**ChEMBL as Target**:
- Reactome → ChEMBL: Via UniProt as bridge (pathway context)
- UniProt → ChEMBL: Via target cross-references

**Complex Multi-Database Paths**:
- ChEMBL → ChEBI → PubChem: Drug → Chemical ontology → Chemical database
- ChEMBL → UniProt → Reactome: Drug target → Protein → Pathway context
- ChEMBL → MeSH → Other disease resources: Drug indication → Disease ontology

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Pre-filtering is essential**: The 2.4M molecule dataset requires early filtering (by development phase) to avoid timeouts
2. **Activity units matter**: 97% of IC50 values are in nM, but without explicit filtering, results could mix incompatible units
3. **bif:contains for text search**: Virtuoso-specific but much faster than REGEX with relevance scoring
4. **Cross-database GRAPH clauses**: Essential for correctness when querying EBI shared endpoint
5. **Entity model understanding**: Molecule → Activity → Assay → Target path is key to navigating data

### Common Pitfalls Discovered

1. **Cross-database queries can timeout**: ChEMBL-Reactome integration is complex; simpler approaches work better
2. **Missing unit checks**: Activity comparisons without unit filtering give wrong results
3. **Post-join filtering**: Always filter INSIDE GRAPH blocks before cross-database joins
4. **Large result sets**: Always use LIMIT to prevent memory issues

### Recommendations for Question Design

1. **Drug discovery focus**: Questions about kinase inhibitors, cancer drugs, mechanism of action
2. **Cross-database integration**: ChEMBL-ChEBI integration works well and demonstrates MIE value
3. **Potency queries**: IC50, pChembl comparisons require unit/type awareness
4. **Disease indications**: DrugIndication entity enables disease-drug questions
5. **Avoid**: Three-way database joins (may timeout); queries without any filtering

### Performance Notes

- Simple lookups: <1 second
- Single-database filtered queries: 1-3 seconds
- ChEMBL-ChEBI cross-database: 1-2 seconds with pre-filtering
- Complex multi-condition queries: 2-5 seconds
- Unfiltered large dataset queries: May timeout (>60s)

---

## Notes and Observations

1. **ChEMBL is drug discovery focused**: Most data relates to bioactive compounds with potential therapeutic applications
2. **Activity data is comprehensive**: 21M+ measurements with standardized types and units
3. **Development phase is valuable**: Enables filtering to clinically relevant drugs
4. **pChembl enables cross-assay comparison**: Normalized potency values allow ranking across different assay types
5. **Human-focused**: Most queries will filter on organism = "Homo sapiens"
6. **MeSH integration through DrugIndication**: Enables disease-drug relationship queries
7. **UniProt integration through TargetComponent**: Enables connection to protein databases

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions:
  1. Kinase inhibitor discovery queries
  2. ChEMBL-ChEBI integration queries
  3. Drug mechanism/indication queries
  4. Activity potency comparison queries
  5. Drug-target mapping queries

- Avoid:
  - Three-way cross-database joins (timeout risk)
  - Unfiltered aggregation queries over entire database
  - ChEMBL-Reactome complex integration (timeout risk)

- Focus areas:
  - Drug development phase filtering
  - Activity unit awareness
  - bif:contains text search optimization
  - Cross-database pre-filtering strategies

**Further Exploration Needed** (if any):
- Reactome integration may need simpler approaches
- Document cross-reference coverage (which molecules have ChEBI links)
- Test more complex aggregation queries with optimization

---

**Session Complete - Ready for Next Database**
