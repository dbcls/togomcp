# BacDive Exploration Report

**Date**: 2026-01-31
**Session**: 1 (Complete Exploration)

## Executive Summary

BacDive is the Bacterial Diversity Metadatabase containing 97,334 bacterial and archaeal strain records with comprehensive phenotypic, genotypic, and cultivation data. Key findings from this exploration:

**Key Capabilities Requiring Deep Knowledge**:
1. Hub-and-spoke data model with Strain as central entity requires understanding of `describesStrain` relationships
2. bif:contains full-text search with boolean operators (AND, OR, NOT) - specific syntax requirements
3. Phenotype coverage variability (~40% Gram stain, ~35% 16S, ~55% enzyme) necessitates OPTIONAL clauses
4. Cross-database integration with MediaDive via two methods: BacDiveID matching (34% coverage) and MediaLink URI conversion (20% coverage)
5. Taxonomy integration requires URI conversion from TaxID integers to identifiers.org URIs

**Major Integration Opportunities**:
- MediaDive: Growth conditions and media recipes (shared `primary` endpoint)
- NCBI Taxonomy: Phylogenetic context (shared `primary` endpoint)
- MONDO: Disease-pathogen correlations via keyword matching
- MeSH/GO: Conceptual linking via keyword matching

**Most Valuable Patterns Discovered**:
1. OPTIONAL clauses for phenotypes prevent data exclusion (85% data loss without)
2. Reserved variable `?score` causes 400 errors - use `?sc` instead
3. BacDiveID range limitation: MediaDive only contains IDs 1-170,041
4. Pre-filtering by genus/species before cross-database joins essential for performance

**Recommended Question Types**:
- Cross-database questions combining BacDive with MediaDive/Taxonomy
- Phenotype-based filtering questions requiring OPTIONAL knowledge
- Full-text search questions testing bif:contains syntax
- Performance questions on large datasets (97K strains)

---

## Database Overview

**Purpose**: Standardized bacterial and archaeal strain information covering taxonomy, morphology, physiology, cultivation conditions, and molecular data.

**Key Data Types and Entities**:
| Entity Type | Count | Description |
|-------------|-------|-------------|
| Strain | 97,334 | Core bacterial/archaeal strain records |
| Enzyme | 573,112 | Enzyme activity phenotypes with EC numbers |
| CultureCollectionNumber | 149,377 | Links to DSMZ, JCM, KCTC collections |
| Reference | 123,819 | Literature references |
| CultureTemperature | 94,321 | Growth temperature conditions |
| NucleotideSequence | 87,045 | 16S rRNA and genome sequences |
| LocationOfOrigin | 66,067 | Geographic isolation locations |
| GenomeSequence | 50,588 | Complete genome accessions |
| CultureMedium | 47,729 | Culture medium specifications |
| OxygenTolerance | 29,051 | Aerobic/anaerobic requirements |

**Dataset Size**: ~97K strains (95,742 Bacteria + 1,049 Archaea + others)

**Endpoint**: https://rdfportal.org/primary/sparql (shared with mediadive, taxonomy, mesh, go, mondo, nando)

---

## Structure Analysis

### Performance Strategies

**Strategy 1: GRAPH Clause for Cross-Database Queries**
- Why needed: BacDive shares endpoint with 6 other databases
- When to apply: Any cross-database query
- Impact: Required for correct results; wrong graph = empty results

**Strategy 2: Pre-filtering Before Joins**
- Why needed: 97K strains × multiple phenotypes = potential explosion
- When to apply: Cross-database queries, multi-phenotype queries
- Impact: 10-100x speedup; prevents timeouts

**Strategy 3: bif:contains for Full-Text Search**
- Why needed: Keyword search on descriptions, labels
- When to apply: Finding strains by characteristics ("thermophilic", "pathogen")
- Impact: Fast text search with boolean logic (AND, OR, NOT)
- Syntax: `?var bif:contains "'keyword1' AND 'keyword2'" option (score ?sc)`

**Strategy 4: OPTIONAL for Phenotypes**
- Why needed: Phenotype coverage only 35-55%
- When to apply: ALL phenotype queries
- Impact: Without OPTIONAL, lose 60-85% of strains

**Strategy 5: URI Conversion for Cross-References**
- Why needed: Different URI patterns across databases
- When to apply: Taxonomy (TaxID → identifiers.org), MediaDive (web URL → RDF URI)
- Impact: Required for cross-database joins to work

**Strategy 6: LIMIT to Prevent Timeouts**
- Why needed: Large result sets
- When to apply: All exploratory queries
- Impact: Prevents 60-second timeout

### Common Pitfalls

**Error 1: Using `?score` as Variable Name**
- Cause: Reserved keyword in Virtuoso bif:contains
- Symptoms: 400 Bad Request
- Solution: Use `?sc`, `?relevance`, or any non-reserved name
- Example before: `option (score ?score)` → 400 error
- Example after: `option (score ?sc)` → works

**Error 2: Requiring Phenotypes Without OPTIONAL**
- Cause: Assuming complete phenotype coverage
- Symptoms: Dramatically reduced results (14% for multi-phenotype)
- Solution: Wrap ALL phenotype patterns in OPTIONAL
- Data: Bacillus strains: 3,332 total, only 479 (14%) have both Gram stain AND motility

**Error 3: Wrong MediaDive Integration Method**
- Cause: Using MediaLink when BacDiveID more appropriate (or vice versa)
- Symptoms: Empty results or missing data
- Solution: Use BacDiveID for growth conditions (34% coverage), MediaLink for media recipes (20% coverage)
- BacDiveID range: Only IDs 1-170,041 exist in MediaDive

**Error 4: Missing FROM/GRAPH Clause**
- Cause: Single-database query without scope
- Symptoms: Slow queries, potential cross-graph contamination
- Solution: Always use `FROM <http://rdfportal.org/dataset/bacdive>` for single-database

**Error 5: Wrong Taxonomy Namespace**
- Cause: Using UniProt namespace (up:) instead of DDBJ (tax:)
- Symptoms: Empty taxonomy results
- Solution: Use `PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>`

### Data Organization

**Core Entity: Strain**
- Central hub for all data
- Contains full taxonomic hierarchy (domain → species)
- Properties: BacDiveID, TaxID, genus, species, family, order, class, phylum, domain
- isTypeStrain flag for reference strains

**Phenotype Entities** (connect via `schema:describesStrain`):
- GramStain: Gram staining result (positive/negative)
- CellMotility: Motility (boolean)
- OxygenTolerance: Aerobic requirements (aerobe, anaerobe, facultative, etc.)
- Enzyme: Enzyme activity tests with EC numbers

**Cultivation Entities**:
- CultureMedium: Media names and MediaDive links
- CultureTemperature: Temperature ranges (start/end)
- CulturePH: pH ranges (start/end)

**Molecular Data**:
- 16SSequence: Ribosomal RNA sequences with ENA/GenBank accessions
- GenomeSequence: Complete genome accessions

**External Links**:
- CultureCollectionNumber: Links to DSMZ, JCM, KCTC repositories
- LocationOfOrigin: Geographic data (country, coordinates)

### Cross-Database Integration Points

**Integration 1: BacDive → MediaDive (via BacDiveID)**
- Connection: Direct integer matching on `schema:hasBacDiveID`
- Join point: Both databases have strains with same BacDiveID
- Required information: BacDive (strain, genus), MediaDive (growth conditions, media)
- Pre-filtering: Filter by genus BEFORE cross-database join
- Coverage: ~34% of BacDive strains (IDs 1-170,041)
- Performance: ~2-3s (Tier 1)
- Tested and verified ✓

**Integration 2: BacDive → MediaDive (via MediaLink)**
- Connection: URI conversion from web URL to RDF URI
- Pattern: `https://mediadive.dsmz.de/medium/{ID}` → `https://purl.dsmz.de/mediadive/medium/{ID}`
- Required information: BacDive (strain, medium label), MediaDive (ingredients, ChEBI IDs)
- Pre-filtering: Filter by genus, require MediaLink present
- Coverage: ~20% of BacDive strains
- Performance: ~2-3s (Tier 1)
- Tested and verified ✓

**Integration 3: BacDive → NCBI Taxonomy**
- Connection: URI conversion from TaxID integer
- Pattern: TaxID integer → `http://identifiers.org/taxonomy/{ID}`
- Required information: BacDive (strain, TaxID), Taxonomy (scientific name, rank, common name)
- Pre-filtering: Filter by genus
- Coverage: 100% of BacDive strains have TaxID
- Graph: `<http://rdfportal.org/ontology/taxonomy>`
- CRITICAL: Use DDBJ namespace (tax:) not UniProt (up:)
- Tested and verified ✓

**Integration 4: BacDive → MONDO**
- Connection: Keyword-based (no direct RDF links)
- Method: bif:contains on both databases
- Required information: Genus/species from BacDive, disease labels from MONDO
- Example: Mycobacterium strains ↔ tuberculosis diseases
- Pre-filtering: Essential on both sides
- Tested and verified ✓

---

## Complex Query Patterns Tested

### Pattern 1: Full-Text Keyword Search with Score

**Purpose**: Find bacterial strains by phenotypic characteristics mentioned in descriptions

**Category**: Structured Query

**Naive Approach**: Use FILTER(CONTAINS(...)) or FILTER(bif:contains(...))

**What Happened**:
- FILTER(CONTAINS()) works but slow and no relevance score
- FILTER(bif:contains()) works but still no score
- Must use as triple pattern with option clause

**Correct Approach**: 
```sparql
?description bif:contains "'thermophilic' AND 'spore-forming'" option (score ?sc) .
ORDER BY DESC(?sc)
```

**What Knowledge Made This Work**:
- bif:contains as triple pattern, not FILTER
- Single quotes around keywords
- Boolean operators (AND, OR, NOT)
- option (score ?sc) for relevance ranking
- Never use ?score as variable name (reserved)

**Results Obtained**:
- 20+ thermophilic spore-forming bacteria found
- Example: Alicyclobacillus vulcanalis (score 20), Weizmannia coagulans (score 20)

**Natural Language Question Opportunities**:
1. "Which thermophilic bacteria form spores?" - Category: Structured Query, Difficulty: Medium
2. "Find bacterial strains described as human pathogens" - Category: Structured Query, Difficulty: Medium

---

### Pattern 2: Reserved Variable Name Error

**Purpose**: Demonstrate error-avoidance knowledge

**Category**: Error Avoidance

**Naive Approach**: Use `?score` as variable name

**What Happened**:
- Query: `?label bif:contains "'escherichia'" option (score ?score)`
- Result: 400 Bad Request error
- Cause: `score` is reserved keyword in Virtuoso

**Correct Approach**:
```sparql
?label bif:contains "'escherichia'" option (score ?sc)
```

**Results Obtained**:
- Without fix: 400 error, query fails completely
- With fix: 15+ Escherichia strains found with relevance scores

**Natural Language Question Opportunities**:
1. "Find Escherichia strains in the BacDive database" - Category: Structured Query, Difficulty: Easy

---

### Pattern 3: OPTIONAL for Phenotype Queries

**Purpose**: Demonstrate critical importance of OPTIONAL for incomplete data

**Category**: Completeness, Error Avoidance

**Naive Approach**: Require all phenotypes without OPTIONAL

**What Happened**:
- Query requiring both Gram stain AND motility for Bacillus
- Without OPTIONAL: Only 479 strains (14.4%)
- With OPTIONAL: All 3,332 Bacillus strains

**Correct Approach**:
```sparql
OPTIONAL {
  ?gs a schema:GramStain ;
      schema:describesStrain ?strain ;
      schema:hasGramStain ?gramStain .
}
OPTIONAL {
  ?cm a schema:CellMotility ;
      schema:describesStrain ?strain ;
      schema:isMotile ?isMotile .
}
```

**What Knowledge Made This Work**:
- Coverage statistics: ~40% Gram stain, ~35% 16S, ~55% enzyme
- All phenotypes are incomplete → OPTIONAL required
- Use FILTER(BOUND(?var)) if specific data absolutely needed

**Results Obtained**:
- Without OPTIONAL: 479 strains (massive data loss)
- With OPTIONAL: 3,332 strains (complete coverage)

**Natural Language Question Opportunities**:
1. "How many Bacillus strains are in BacDive?" - Category: Completeness, Difficulty: Easy
2. "What are the Gram stain and motility characteristics of Bacillus strains?" - Category: Completeness, Difficulty: Medium

---

### Pattern 4: Cross-Database Query - BacDive to MediaDive

**Purpose**: Find growth conditions for bacterial strains

**Category**: Integration, Cross-Database

**Naive Approach**: Try to join without understanding BacDiveID range

**What Happened**:
- Using high BacDiveID strains (e.g., Escherichia >130,000) → empty results
- MediaDive only has IDs 1-170,041

**Correct Approach**:
```sparql
GRAPH <http://rdfportal.org/dataset/bacdive> {
  ?bacDiveStrain a schema:Strain ;
                 schema:hasBacDiveID ?bacDiveID ;
                 schema:hasGenus "Bacillus" .  # Lower IDs
}
GRAPH <http://rdfportal.org/dataset/mediadive> {
  ?mediaDiveStrain a schema:Strain ;
                   schema:hasBacDiveID ?bacDiveID .
  ?growth a schema:GrowthCondition ;
          schema:relatedToStrain ?mediaDiveStrain .
}
```

**What Knowledge Made This Work**:
- BacDiveID range: MediaDive only has IDs 1-170,041
- Use Bacillus (lower IDs) not Escherichia (high IDs >130K)
- Direct integer matching, no URI conversion needed
- GRAPH clauses instead of FROM for cross-database

**Results Obtained**:
- Bacillus licheniformis: Columbia Blood Medium, 37°C, pH 7.0
- Bacillus mycoides: Trypticase Soy Yeast Extract Medium, 30°C, pH 7.0
- Bacillus subtilis: Nutrient Agar, 30°C

**Natural Language Question Opportunities**:
1. "What growth conditions are used to cultivate Bacillus subtilis?" - Category: Integration, Difficulty: Medium
2. "At what temperature should Bacillus licheniformis be grown?" - Category: Integration, Difficulty: Medium
3. "Which Bacillus strains can be grown on Nutrient Agar?" - Category: Integration, Difficulty: Hard

---

### Pattern 5: Cross-Database Query - BacDive to Taxonomy

**Purpose**: Get taxonomic context for bacterial strains

**Category**: Integration, Cross-Database

**Naive Approach**: Use wrong namespace or no URI conversion

**What Happened**:
- Without URI conversion: No join possible (TaxID is integer, Taxonomy uses URIs)
- Wrong namespace (up: instead of tax:): Empty results

**Correct Approach**:
```sparql
GRAPH <http://rdfportal.org/dataset/bacdive> {
  ?strain a schema:Strain ;
          schema:hasTaxID ?taxID ;
          schema:hasGenus "Escherichia" .
}
BIND(URI(CONCAT("http://identifiers.org/taxonomy/", STR(?taxID))) AS ?taxonURI)
GRAPH <http://rdfportal.org/ontology/taxonomy> {
  ?taxonURI a tax:Taxon ;
            tax:scientificName ?scientificName ;
            tax:rank ?rank .
}
```

**What Knowledge Made This Work**:
- URI conversion: TaxID → identifiers.org URI
- DDBJ namespace: `tax:` not `up:`
- Graph URI: `<http://rdfportal.org/ontology/taxonomy>`
- 100% coverage: All BacDive strains have TaxID

**Results Obtained**:
- Escherichia coli: TaxID 562, rank Species, common name "E. coli"

**Natural Language Question Opportunities**:
1. "What is the common name for E. coli according to NCBI Taxonomy?" - Category: Integration, Difficulty: Medium
2. "What taxonomic rank is assigned to Escherichia coli?" - Category: Integration, Difficulty: Easy

---

### Pattern 6: Cross-Database Query - BacDive to MONDO

**Purpose**: Correlate bacterial genera with diseases

**Category**: Integration, Cross-Database

**Naive Approach**: Look for direct RDF links (none exist)

**What Happened**:
- No direct links between BacDive and MONDO
- Must use keyword-based correlation

**Correct Approach**:
```sparql
GRAPH <http://rdfportal.org/dataset/bacdive> {
  ?strain a schema:Strain ;
          schema:hasGenus ?genus .
  FILTER(?genus = "Mycobacterium")
}
GRAPH <http://rdfportal.org/ontology/mondo> {
  ?disease a owl:Class ;
           rdfs:label ?diseaseLabel .
  ?diseaseLabel bif:contains "'tuberculosis'" option (score ?sc) .
  FILTER(STRSTARTS(STR(?disease), "http://purl.obolibrary.org/obo/MONDO_"))
}
```

**What Knowledge Made This Work**:
- No direct links → keyword-based approach
- MONDO uses owl:Class and rdfs:label
- MONDO URI pattern: `http://purl.obolibrary.org/obo/MONDO_`
- Pre-filter BOTH sides before join

**Results Obtained**:
- Mycobacterium strains correlated with tuberculosis susceptibility diseases

**Natural Language Question Opportunities**:
1. "Which bacterial genera are associated with tuberculosis?" - Category: Integration, Difficulty: Hard
2. "What diseases are linked to Mycobacterium species?" - Category: Integration, Difficulty: Hard

---

### Pattern 7: MediaLink URI Conversion

**Purpose**: Get media ingredient details from MediaDive

**Category**: Integration, Cross-Database

**Naive Approach**: Use web URL directly

**What Happened**:
- BacDive stores: `https://mediadive.dsmz.de/medium/ID`
- MediaDive RDF uses: `https://purl.dsmz.de/mediadive/medium/ID`
- Direct use fails

**Correct Approach**:
```sparql
BIND(REPLACE(STR(?mediaLink), "^https://mediadive\\.dsmz\\.de/medium/", "") AS ?mediumID)
BIND(URI(CONCAT("https://purl.dsmz.de/mediadive/medium/", ?mediumID)) AS ?mediaDiveMedium)
```

**What Knowledge Made This Work**:
- URI pattern conversion required
- Different from BacDiveID method (accesses different data)
- Provides ingredient details with ChEBI cross-references

**Results Obtained**:
- Bacillus acidicola: Alicyclobacillus Medium with detailed ingredients
- Glucose (CHEBI:17234), KH2PO4 (CHEBI:63036), etc.

**Natural Language Question Opportunities**:
1. "What ingredients are in the culture medium for acidophilic Bacillus?" - Category: Integration, Difficulty: Hard
2. "Which media contain glucose according to MediaDive?" - Category: Integration, Difficulty: Medium

---

### Pattern 8: Multi-Phenotype Complex Query

**Purpose**: Find bacteria with specific phenotypic profiles

**Category**: Structured Query

**Correct Approach**:
```sparql
?description bif:contains "'pathogen' OR 'pathogenic'" option (score ?sc) .
OPTIONAL { ?gs schema:hasGramStain ?gramStain }
OPTIONAL { ?ot schema:hasOxygenTolerance ?oxygenTol }
OPTIONAL { ?loc schema:hasCountry ?country }
```

**Results Obtained**:
- Human pathogens: Achromobacter spanius (Gram-negative, aerobe)
- Animal pathogens: Acaricomes phytoseiuli (Gram-positive, aerobe)
- Plant pathogens: Acidovorax cattleyae (Gram-negative, aerobe)

**Natural Language Question Opportunities**:
1. "Which bacteria in BacDive are described as human pathogens?" - Category: Structured Query, Difficulty: Medium
2. "What are the Gram stain characteristics of pathogenic Bacillus species?" - Category: Structured Query, Difficulty: Hard

---

### Pattern 9: Enzyme Activity with EC Numbers

**Purpose**: Find strains with specific enzyme activities

**Category**: Structured Query, Precision

**Correct Approach**:
```sparql
?enzyme a schema:Enzyme ;
        schema:describesStrain ?strain ;
        schema:hasActivity "+" ;
        schema:hasECNumber ?ecNumber .
```

**Results Obtained**:
- Beta-galactosidase (EC 3.2.1.23): 6 positive results in Actinomyces catuli
- Catalase (EC 1.11.1.6): Common in many strains
- Alkaline phosphatase (EC 3.1.3.1): Widely distributed

**Natural Language Question Opportunities**:
1. "Which bacteria have positive catalase activity?" - Category: Structured Query, Difficulty: Easy
2. "What EC numbers are associated with beta-galactosidase in bacterial strains?" - Category: Precision, Difficulty: Medium

---

### Pattern 10: 16S Sequence Retrieval

**Purpose**: Find strains with 16S rRNA sequences and accession numbers

**Category**: Precision, Integration

**Correct Approach**:
```sparql
?seq a schema:16SSequence ;
     schema:describesStrain ?strain ;
     schema:hasSequenceAccession ?accession ;
     schema:fromSequenceDB ?seqDB ;
     schema:hasSequenceLength ?length .
```

**Results Obtained**:
- Bacillus thuringiensis: X89895 (ENA), 2978 bp
- Bacillus subtilis: AB042061 (ENA), 1553 bp
- Bacillus polygoni: AB292819 (nuccore), 1558 bp

**Natural Language Question Opportunities**:
1. "What is the 16S rRNA sequence accession for Bacillus subtilis type strain?" - Category: Precision, Difficulty: Medium
2. "Which Bacillus type strains have the longest 16S sequences?" - Category: Completeness, Difficulty: Medium

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "Bacillus type strains"
   - Found: Bacillus subtilis 1172, Bacillus licheniformis 689, Bacillus thuringiensis 1006
   - Usage: Core entities for phenotype and integration questions

2. Search: "Thermophilic bacteria"
   - Found: Alicyclobacillus vulcanalis 425, Anoxybacillus calidus 23586, Lihuaxuella thermophila 24646
   - Usage: Temperature-related questions

3. Search: "Human pathogens"
   - Found: Achromobacter spanius 323, Achromobacter insolitus 322, Acidovorax wautersii 23868
   - Usage: Pathogen-related questions

4. Search: "Escherichia coli strains"
   - Found: Multiple with TaxID 562
   - Usage: Taxonomy integration questions

5. Search: "Strains with 16S sequences"
   - Found: Many with ENA/GenBank accessions
   - Usage: Sequence data questions

6. Search: "Gram-positive bacteria"
   - Found: Bacillus kexueae, Lihuaxuella thermophila
   - Usage: Phenotype filtering questions

7. Search: "Geographic origins"
   - Found: Strains from Japan, China, USA, Germany, etc.
   - Usage: Geographic query questions

8. Search: "DSMZ culture collections"
   - Found: DSM 21631, DSM 25608, DSM 22148
   - Usage: External cross-reference questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What growth temperature is recommended for Bacillus subtilis in MediaDive?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: BacDiveID matching, GRAPH clauses, pre-filtering
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

2. "What culture media can be used to grow Bacillus type strains according to MediaDive?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: BacDiveID range (1-170,041), GRAPH clauses
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

3. "What is the common name for Escherichia coli in NCBI Taxonomy?"
   - Databases involved: BacDive, Taxonomy
   - Knowledge Required: URI conversion (TaxID → identifiers.org), DDBJ namespace
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

4. "What are the main ingredients in the Alicyclobacillus Medium used for acidophilic bacteria?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: MediaLink URI conversion, MediumComposition structure
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 7

5. "Which bacterial genera in BacDive might be associated with tuberculosis based on disease terminology?"
   - Databases involved: BacDive, MONDO
   - Knowledge Required: Keyword-based correlation, MONDO owl:Class structure
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 6

6. "What ChEBI identifiers correspond to ingredients in bacterial growth media?"
   - Databases involved: BacDive, MediaDive, ChEBI (via IDs)
   - Knowledge Required: MediaLink method, hasChEBI property
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 7

7. "For strains isolated from Japan, what growth temperatures are used in MediaDive?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: LocationOfOrigin + BacDiveID matching
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Patterns 4, 8

**Performance-Critical Questions**:

8. "How many bacterial strains in BacDive have both Gram stain and motility data available?"
   - Database: BacDive
   - Knowledge Required: OPTIONAL clauses, FILTER(BOUND()) for counting
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

9. "How many thermophilic bacteria are described in BacDive?"
   - Database: BacDive
   - Knowledge Required: bif:contains syntax, COUNT optimization
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

10. "What proportion of Bacillus strains have 16S rRNA sequences available?"
    - Database: BacDive
    - Knowledge Required: Coverage statistics (~35%), OPTIONAL + COUNT
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

11. "Which phyla have the most strains represented in BacDive?"
    - Database: BacDive
    - Knowledge Required: GROUP BY optimization, hasPhylum property
    - Category: Completeness
    - Difficulty: Easy
    - Pattern Reference: Tested

**Error-Avoidance Questions**:

12. "Find bacteria described as spore-forming in BacDive"
    - Database: BacDive
    - Knowledge Required: bif:contains syntax, NOT ?score variable name
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Patterns 1, 2

13. "What phenotypic characteristics are known for Bacillus subtilis type strain?"
    - Database: BacDive
    - Knowledge Required: OPTIONAL for all phenotypes (incomplete data)
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

14. "Find bacterial strains that are both Gram-positive and anaerobic"
    - Database: BacDive
    - Knowledge Required: Multi-phenotype query with OPTIONAL
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

**Complex Filtering Questions**:

15. "Which bacteria isolated from extreme environments (hydrothermal vents, hot springs) are thermophilic?"
    - Database: BacDive
    - Knowledge Required: bif:contains with complex boolean, LocationOfOrigin
    - Category: Structured Query
    - Difficulty: Hard
    - Pattern Reference: Pattern 8

16. "What are the enzyme activities (with EC numbers) of Bacillus type strains?"
    - Database: BacDive
    - Knowledge Required: Enzyme entity structure, hasActivity/hasECNumber
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 9

17. "Find human pathogenic bacteria with their Gram stain and oxygen tolerance characteristics"
    - Database: BacDive
    - Knowledge Required: bif:contains + multiple OPTIONAL phenotypes
    - Category: Structured Query
    - Difficulty: Hard
    - Pattern Reference: Pattern 8

18. "Which bacterial strains have genome sequences deposited in NCBI?"
    - Database: BacDive
    - Knowledge Required: GenomeSequence entity, fromSequenceDB filter
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 10

19. "What is the typical pH range for growing Bacillus strains?"
    - Database: BacDive
    - Knowledge Required: CulturePH entity, hasPHRangeStart/End
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern tested

20. "Find bacteria that grow at temperatures above 50°C"
    - Database: BacDive
    - Knowledge Required: CultureTemperature, numeric filtering
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern tested

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the BacDive ID for Bacillus subtilis type strain?"
   - Method: Simple search/query
   - Knowledge Required: None (straightforward)
   - Category: Entity Lookup
   - Difficulty: Easy

2. "How many strains are in the BacDive database?"
   - Method: Simple COUNT query
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy
   - Answer: 97,334

3. "Is Bacillus subtilis DSM 10 a type strain?"
   - Method: Simple property lookup
   - Knowledge Required: None
   - Category: Entity Lookup
   - Difficulty: Easy

4. "What genus does strain 1172 belong to?"
   - Method: Simple query by BacDiveID
   - Knowledge Required: None
   - Category: Entity Lookup
   - Difficulty: Easy
   - Answer: Bacillus (Bacillus subtilis 1172)

5. "How many Archaea strains are in BacDive?"
   - Method: Simple COUNT with domain filter
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy
   - Answer: 1,049

**ID Mapping Questions**:

6. "What is the NCBI Taxonomy ID for Bacillus subtilis in BacDive?"
   - Method: hasTaxID property lookup
   - Knowledge Required: None (direct property)
   - Category: Precision
   - Difficulty: Easy

7. "What DSM collection number is associated with Bacillus altitudinis type strain?"
   - Method: CultureCollectionNumber lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy
   - Answer: DSM 21631

8. "What is the ENA accession number for the 16S sequence of Bacillus subtilis 1172?"
   - Method: 16SSequence lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy
   - Answer: AB042061

---

## Integration Patterns Summary

**BacDive as Source**:
- → MediaDive: Growth conditions, media recipes (via BacDiveID or MediaLink)
- → Taxonomy: Phylogenetic context (via TaxID → URI conversion)
- → ENA/GenBank: Sequence data (via accession numbers, external)
- → DSMZ/JCM/KCTC: Culture collections (via hasLink, external)

**BacDive as Target**:
- Not commonly used as target (hub-centric design)
- Could receive annotations from literature (PubMed via DOI/PMID - but sparse)

**Complex Multi-Database Paths**:
- BacDive → MediaDive → ChEBI: Strains → Media → Ingredient chemical IDs
- BacDive → Taxonomy → (broader taxonomy relations): Strains → Taxa → Phylogenetic trees
- BacDive + MONDO: Pathogen-disease correlation via keywords (no direct path)

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **OPTIONAL is critical**: Phenotype coverage is 35-55%; without OPTIONAL lose 60-85% of data
2. **bif:contains syntax**: Must be triple pattern with single-quoted keywords and score variable
3. **Reserved variables**: `?score` causes 400 error - use `?sc`
4. **BacDiveID range**: MediaDive only has IDs 1-170,041; newer strains won't match
5. **Namespace differences**: Taxonomy uses DDBJ (tax:) not UniProt (up:)

### Common Pitfalls Discovered

1. Using `?score` as variable name → 400 error
2. Requiring phenotypes without OPTIONAL → massive data loss (85%+)
3. Using high BacDiveIDs for MediaDive queries → empty results
4. Wrong namespace for Taxonomy → empty results
5. Missing GRAPH clauses in cross-database queries → wrong results or timeout

### Recommendations for Question Design

1. **Integration questions**: Focus on BacDive ↔ MediaDive and BacDive ↔ Taxonomy
2. **Error-avoidance**: Test bif:contains syntax and OPTIONAL patterns
3. **Coverage questions**: Leverage incomplete phenotype data as test cases
4. **Avoid**: Direct literature references (sparse PubMed/DOI data in BacDive)

### Performance Notes

- Single-database queries: <2s typically
- Cross-database with pre-filtering: 2-3s (Tier 1)
- Multi-phenotype joins: 5-10s possible
- Always use LIMIT to prevent timeout

---

## Notes and Observations

1. BacDive has rich phenotypic data but coverage varies significantly by property
2. Type strains have better data completeness than other strains
3. MediaDive integration is powerful but limited by BacDiveID range
4. No direct PubMed links despite Reference entity type
5. Geographic data quality varies - some have coordinates, many just country names
6. Taxonomic hierarchy embedded in strains is comprehensive (domain → species)
7. Enzyme data includes EC numbers for most entries

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database with MediaDive, OPTIONAL patterns, bif:contains syntax
- Avoid: Literature/publication questions (sparse data)
- Focus areas: Phenotypic queries, cultivation conditions, taxonomic integration

**Further Exploration Needed**:
- None - comprehensive exploration completed

---

**Session Complete - Ready for Next Database**

```
Database: bacdive
Status: ✅ COMPLETE
Report: /evaluation/exploration/bacdive_exploration.md
Patterns Tested: 10
Questions Identified: 28 (20 complex, 8 simple)
Integration Points: 4 (MediaDive x2, Taxonomy, MONDO)
```
