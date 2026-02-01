# AMR Portal (Antimicrobial Resistance) Exploration Report

**Date**: January 31, 2026  
**Session**: 1

## Executive Summary

The AMR Portal RDF database is a comprehensive antimicrobial resistance surveillance resource integrating data from NCBI Pathogen Detection, PATRIC, CABBAGE, and other sources. It contains:
- **1,714,486 phenotypic antimicrobial susceptibility test results**
- **1,164,007 genotypic AMR features** (resistance genes, mutations)

### Key Capabilities Requiring Deep Knowledge:
1. **Genotype-phenotype correlation studies** via bioSample linkage
2. **Geographic surveillance analysis** with hierarchical region data
3. **Temporal trend analysis** (1911-2025, concentrated in recent decades)
4. **Cross-database integration** with ChEMBL (antibiotics), NCBI Taxonomy, and PubMed

### Major Integration Opportunities:
- ChEMBL: Antibiotic compound properties and development status
- NCBI Taxonomy: Organism classification via `obo:RO_0002162`
- PubMed: Literature citations via `dct:references`
- BioSample/SRA: Sequence data linkage

### Most Valuable Patterns Discovered:
- Two-stage aggregation for cross-database analytics
- Case-insensitive filtering for inconsistent text fields
- BioSample-based genotype-phenotype correlation

### Recommended Question Types:
- Surveillance pattern analysis (geographic, temporal)
- Genotype-phenotype correlation studies
- Multi-drug resistance profiling
- Cross-database antibiotic enrichment queries

---

## Database Overview

**Purpose**: Antimicrobial resistance surveillance data integration from multiple global sources

**Key Data Types**:
- `amr:PhenotypeMeasurement`: Resistance test results with MIC values, disk diffusion data
- `amr:GenotypeFeature`: AMR genes, mutations, and resistance elements

**Dataset Size**: 
- 1.7M phenotype measurements
- 1.1M genotype features
- ~1.4M unique bioSamples

**Performance Considerations**:
- SPARQL endpoint with 60-second timeout
- Large dataset requires strategic filtering
- Cross-database aggregation needs two-stage pattern

**Access**: Virtuoso-based endpoint at https://rdfportal.org/ebi/sparql

---

## Structure Analysis

### Performance Strategies

**Strategy 1: Single Antibiotic Filtering**
- Why needed: Full antibiotic aggregation processes millions of records
- When to apply: When analyzing resistance patterns
- Performance impact: Queries complete in <5 seconds vs potential timeout

**Strategy 2: Geographic/Temporal Pre-filtering**
- Why needed: Reduces dataset before expensive aggregations
- When to apply: Regional or temporal analysis
- Performance impact: 3-5 seconds for filtered queries

**Strategy 3: Two-Stage Cross-Database Aggregation**
- Why needed: Aggregating across GRAPH boundaries causes timeout
- When to apply: Any ChEMBL/AMR integration with statistics
- Performance impact: ~6 seconds total (5s + 1s) vs timeout

**Strategy 4: SAMPLE() for Representative Data**
- Why needed: Collecting all values expensive for exploratory queries
- When to apply: Getting example values without full enumeration
- Performance impact: 2-3 seconds vs extended processing

**Strategy 5: LIMIT Clause Usage**
- Why needed: Exploratory queries without limits can timeout
- When to apply: Initial data exploration
- Performance impact: Essential for unknown result sizes

### Common Pitfalls

**Pitfall 1: Case Sensitivity in Text Fields**
- Cause: Inconsistent capitalization (Stool vs stool, Blood vs blood)
- Symptoms: Missing results, incomplete counts
- Solution: Use `CONTAINS(LCASE(?field), "value")` or `bif:contains`
- Example: `?source bif:contains "'blood'" option (score ?sc)`

**Pitfall 2: Cross-Database Aggregation Timeout**
- Cause: Trying to aggregate across GRAPH boundaries
- Symptoms: Query timeout (60s limit)
- Solution: Two-stage pattern - aggregate first, then join
- Example: Run AMR aggregation alone, use results in VALUES clause for ChEMBL

**Pitfall 3: Incomplete Genotype-Phenotype Linkage**
- Cause: Not all bioSamples have both phenotype and genotype data
- Symptoms: Lower-than-expected correlation results
- Solution: Verify linkage exists before complex joins; ~65% have both

**Pitfall 4: Antibiotic Name Case Mismatch**
- Cause: AMR Portal uses lowercase, ChEMBL uses uppercase
- Symptoms: Empty results in cross-database queries
- Solution: Use `BIND(LCASE(?chemblLabel) AS ?antibioticName)`

### Data Organization

**Phenotype Measurements**:
- Core resistance testing data
- Properties: organism, species, genus, antibioticName, resistancePhenotype
- Geographic: country, geographicalRegion, geographicalSubregion, isoCountryCode
- Temporal: collectionYear (1911-2025)
- Method: laboratoryTypingMethod, astStandard
- Quantitative: measurementValue, measurementSign, measurementUnits

**Genotype Features**:
- AMR gene annotations
- Properties: organism, amrClass, amrSubclass, geneSymbol, amrElementSymbol
- Genomic: region, regionStart, regionEnd, strand
- Evidence: evidenceType, evidenceAccession, evidenceDescription

**Key Linkages**:
- `amr:bioSample`: Links phenotype and genotype data from same isolate
- `obo:RO_0002162`: NCBI Taxonomy for genotype features
- `dct:references`: PubMed citations

### Cross-Database Integration Points

**Integration 1: AMR Portal → ChEMBL (Antibiotic Enrichment)**
- Connection: antibiotic names (lowercase) → molecule labels (uppercase)
- Join: BIND(LCASE(?chemblLabel) AS ?antibioticName)
- Required from each: AMR (resistance stats), ChEMBL (compound properties)
- Pre-filtering: VALUES clause with specific antibiotics
- Knowledge required: Case normalization, two-stage aggregation pattern

**Integration 2: AMR Portal → NCBI Taxonomy**
- Connection: obo:RO_0002162 property on GenotypeFeature
- Join: Direct IRI match to taxonomy IDs
- Required from each: AMR (organism data), Taxonomy (classification hierarchy)
- Pre-filtering: Organism filter in AMR first
- Knowledge required: RO_0002162 predicate for taxonomy linkage

**Integration 3: AMR Portal → PubMed**
- Connection: dct:references property
- Join: Direct PubMed IRI references
- Required from each: AMR (measurements), PubMed (publication metadata)
- Pre-filtering: Filter AMR data before joining
- Knowledge required: dct:references predicate location

**Integration 4: AMR Portal → BioSample/SRA**
- Connection: amr:bioSample, amr:sraAccession, amr:assemblyId
- Join: IRI-based linkage
- Required from each: AMR (resistance data), sequence archives (genomic data)
- Knowledge required: Multiple accession properties available

---

## Complex Query Patterns Tested

### Pattern 1: Geographic Resistance Distribution

**Purpose**: Analyze ciprofloxacin resistance patterns across countries in the Americas

**Category**: Structured Query / Specificity

**What Knowledge Made This Work**:
- Geographic hierarchy: geographicalRegion → country → isoCountryCode
- Phenotype values: "resistant", "susceptible", "intermediate"
- Filter by region first, then country aggregation

**Results Obtained**:
- USA: 7,458 resistant cases out of 47,219 tests
- Brazil: 278 resistant out of 505 tests
- Mexico: 188 resistant out of 228 tests
- 15+ countries with data

**Natural Language Question Opportunities**:
1. "Which countries in the Americas have the highest rates of ciprofloxacin resistance?" - Category: Specificity
2. "How does ciprofloxacin resistance vary across geographic regions?" - Category: Structured Query
3. "What antibiotics show the most resistance in South American countries?" - Category: Completeness

---

### Pattern 2: Genotype-Phenotype Correlation (Carbapenem Resistance)

**Purpose**: Link meropenem-resistant isolates to their beta-lactamase resistance genes

**Category**: Integration / Structured Query

**What Knowledge Made This Work**:
- bioSample IRI links phenotype and genotype records
- amrClass filtering: CONTAINS(?amrClass, "BETA-LACTAM")
- Gene symbols: bla_1, ampC, penA variants

**Results Obtained**:
- Found 30+ isolates with both meropenem resistance and BETA-LACTAM genes
- Gene families: bla_1 through bla_8, ampC, ampC_1, ampC_2, penA, pbpX
- BioSamples: SAMN06437298, SAMN05170177, etc.

**Natural Language Question Opportunities**:
1. "What beta-lactamase genes are commonly found in meropenem-resistant bacteria?" - Category: Integration
2. "Which bacterial isolates carry carbapenemase genes and show carbapenem resistance?" - Category: Structured Query
3. "Are there common genetic features among carbapenem-resistant Klebsiella pneumoniae?" - Category: Specificity

---

### Pattern 3: Multi-Drug Resistance Profiling

**Purpose**: Find bacterial isolates resistant to 3+ different antibiotics

**Category**: Structured Query / Completeness

**What Knowledge Made This Work**:
- GROUP BY bioSample to aggregate per isolate
- COUNT(DISTINCT ?antibiotic) for drug count
- HAVING clause for threshold filtering
- SAMPLE() for efficient metadata retrieval

**Results Obtained**:
- Top isolate: Proteus mirabilis from Sweden resistant to 33 antibiotics
- Klebsiella pneumoniae isolates: 27-32 drug resistances
- Countries: Sweden, Kenya, Jordan, Thailand
- Species: K. pneumoniae, E. coli, A. baumannii, P. aeruginosa

**Natural Language Question Opportunities**:
1. "Which bacterial isolates show resistance to the most antibiotics?" - Category: Completeness
2. "Where are the most multi-drug resistant Klebsiella pneumoniae isolates found?" - Category: Specificity
3. "How prevalent is multi-drug resistance in different bacterial species?" - Category: Structured Query

---

### Pattern 4: Temporal Trend Analysis

**Purpose**: Track ciprofloxacin resistance changes over years

**Category**: Currency / Structured Query

**What Knowledge Made This Work**:
- collectionYear property for temporal filtering
- Year range filtering: FILTER(?year >= 2010 && ?year <= 2023)
- Single antibiotic focus for performance

**Results Obtained**:
- 2010: 444 resistant isolates
- 2018: 2,719 resistant isolates (peak)
- 2023: 216 resistant isolates
- Clear temporal pattern visible

**Natural Language Question Opportunities**:
1. "How has ciprofloxacin resistance changed over the past decade?" - Category: Currency
2. "When was antimicrobial resistance to fluoroquinolones highest?" - Category: Precision
3. "What is the trend in multidrug-resistant tuberculosis over time?" - Category: Currency

---

### Pattern 5: Carbapenemase Gene Distribution

**Purpose**: Find NDM, KPC, OXA, VIM, IMP carbapenemase genes across organisms

**Category**: Specificity / Completeness

**What Knowledge Made This Work**:
- Gene symbol patterns: CONTAINS for "ndm", "kpc", "oxa", etc.
- Multiple FILTER conditions with OR
- Organism-gene co-occurrence analysis

**Results Obtained**:
- blaNDM-1: Most common in K. pneumoniae (196), E. coli (155)
- Also found in: A. baumannii, P. aeruginosa, Enterobacter species
- Variants: blaNDM-1_1, blaNDM-1_2, blaNDM-1_3

**Natural Language Question Opportunities**:
1. "Which bacterial species carry NDM-1 carbapenemase genes?" - Category: Completeness
2. "How prevalent are carbapenemase genes in Enterobacteriaceae?" - Category: Structured Query
3. "What organisms harbor clinically important carbapenem resistance genes?" - Category: Specificity

---

### Pattern 6: AMR Gene Class Distribution

**Purpose**: Analyze prevalence of different AMR gene classes

**Category**: Completeness / Structured Query

**What Knowledge Made This Work**:
- amrClass property on GenotypeFeature
- Aggregation by gene class
- Understanding AMR classification system

**Results Obtained**:
- BETA-LACTAM: 243,389 genes (most common)
- AMINOGLYCOSIDE: 187,430
- EFFLUX: 180,406
- TETRACYCLINE: 89,420
- QUINOLONE: 80,396

**Natural Language Question Opportunities**:
1. "What are the most common types of antimicrobial resistance genes?" - Category: Completeness
2. "How prevalent are efflux pump genes compared to other resistance mechanisms?" - Category: Structured Query
3. "Which antibiotic class has the most resistance genes detected?" - Category: Precision

---

### Pattern 7: Laboratory Method Distribution

**Purpose**: Understand AST testing methodology used

**Category**: Precision / Completeness

**What Knowledge Made This Work**:
- laboratoryTypingMethod property
- astStandard property (CLSI, EUCAST, etc.)
- Aggregation by method type

**Results Obtained**:
- Broth dilution: 959,895 (56%)
- Agar dilution: 142,476 (8%)
- Disk diffusion: 120,901 (7%)
- E-test: 33,937 (2%)
- CLSI standard: 397,226 tests
- EUCAST standard: 281,558 tests

**Natural Language Question Opportunities**:
1. "What laboratory methods are used for antimicrobial susceptibility testing?" - Category: Precision
2. "How many resistance tests use EUCAST vs CLSI standards?" - Category: Completeness
3. "What testing platforms are most commonly used for MIC determination?" - Category: Specificity

---

### Pattern 8: Cross-Database Integration with ChEMBL (Two-Stage)

**Purpose**: Enrich AMR resistance statistics with ChEMBL compound information

**Category**: Integration

**Naive Approach (without knowledge)**:
- Try to aggregate resistance counts across GRAPH boundaries
- Result: Timeout or error

**What Knowledge Made This Work**:
- Stage 1: Aggregate within AMR Portal only (5 seconds)
- Stage 2: Use aggregated results in VALUES clause for ChEMBL lookup (1 second)
- Case normalization: LCASE() for matching

**Results Obtained**:
- Stage 1 results:
  - ampicillin: 21,660 resistant
  - ciprofloxacin: 21,368 resistant
  - gentamicin: 8,398 resistant
  - meropenem: 3,697 resistant
- Stage 2 enriches with ChEMBL compound IDs

**Natural Language Question Opportunities**:
1. "What are the resistance rates for the most commonly tested antibiotics?" - Category: Completeness
2. "Which antibiotics have the highest resistance rates globally?" - Category: Precision
3. "How do clinical resistance patterns compare between different antibiotic classes?" - Category: Integration

---

### Pattern 9: Data Source Analysis

**Purpose**: Understand which databases contribute data

**Category**: Completeness / Precision

**What Knowledge Made This Work**:
- database property contains source information
- Multiple sources per record (semicolon-separated)
- Different sources for different types of data

**Results Obtained**:
- PATRIC: 426,161 records (largest single source)
- CABBAGE_PubMed_data: 316,524
- NARMS: 239,924
- NCBI_antibiogram: 191,077
- Combined sources common (e.g., "PATRIC;CABBAGE_PubMed_data": 142,419)

**Natural Language Question Opportunities**:
1. "What are the primary data sources for antimicrobial resistance surveillance?" - Category: Completeness
2. "How many resistance records come from the NARMS surveillance program?" - Category: Precision
3. "Which resistance databases contribute to global AMR surveillance?" - Category: Specificity

---

### Pattern 10: Quantitative MIC Analysis

**Purpose**: Analyze meropenem MIC distribution

**Category**: Precision / Structured Query

**What Knowledge Made This Work**:
- measurementValue, measurementSign, measurementUnits properties
- Understanding MIC interpretation (<=, >=, =, ==)
- Unit standardization (mg/L)

**Results Obtained**:
- <=0.06 mg/L: 21,849 tests (susceptible range)
- <=0.25 mg/L: 6,252 tests
- >=16 mg/L: 727 tests (resistant range)
- >8 mg/L: 1,195 tests

**Natural Language Question Opportunities**:
1. "What is the MIC distribution for meropenem in clinical isolates?" - Category: Precision
2. "How many bacterial isolates have high-level carbapenem resistance based on MIC values?" - Category: Structured Query
3. "What proportion of isolates fall into resistant vs susceptible MIC categories?" - Category: Completeness

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. **Top Organisms**: Salmonella enterica (443K), Escherichia coli (364K), Mycobacterium tuberculosis (331K), Klebsiella pneumoniae (133K)
   - Usage: Questions about specific organism resistance patterns

2. **Top Antibiotics**: ciprofloxacin (96K), tetracycline (80K), gentamicin (79K), ceftriaxone (72K)
   - Usage: Questions about specific antibiotic resistance

3. **Geographic Regions**: Americas (790K), Europe (249K), Asia (246K), Oceania (99K), Africa (54K)
   - Usage: Questions about regional surveillance patterns

4. **AMR Gene Classes**: BETA-LACTAM, AMINOGLYCOSIDE, EFFLUX, TETRACYCLINE, QUINOLONE
   - Usage: Questions about resistance mechanisms

5. **Resistance Phenotypes**: susceptible (1.04M), resistant (303K), intermediate (35K)
   - Usage: Questions about resistance distribution

6. **Laboratory Methods**: broth dilution (960K), agar dilution (142K), disk diffusion (121K)
   - Usage: Questions about testing methodology

7. **AST Standards**: CLSI (397K), EUCAST (282K), NARMS (7K)
   - Usage: Questions about standardization

8. **Collection Years**: Peak years 2018-2021 with 100K-200K records each
   - Usage: Temporal analysis questions

9. **Countries (Americas)**: USA (47K ciprofloxacin tests), Canada (2.6K), Brazil (505)
   - Usage: Country-specific surveillance questions

10. **Specific Genes**: blaNDM-1 (carbapenemase), acrF (efflux), ampC (beta-lactamase)
    - Usage: Questions about specific resistance genes

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which antibiotics used to treat Klebsiella pneumoniae infections are documented in both resistance databases and have chemical structures available?"
   - Databases: AMR Portal, ChEMBL
   - Knowledge Required: Two-stage aggregation, case normalization for drug names
   - Category: Integration
   - Difficulty: Hard

2. "What bacterial species with carbapenem resistance have their genomes sequenced and available in sequence archives?"
   - Databases: AMR Portal, BioSample/SRA
   - Knowledge Required: bioSample/sraAccession linkage patterns
   - Category: Integration
   - Difficulty: Medium

3. "Which organisms with documented antibiotic resistance have taxonomy classifications in NCBI?"
   - Databases: AMR Portal, NCBI Taxonomy
   - Knowledge Required: obo:RO_0002162 linkage for genotype features
   - Category: Integration
   - Difficulty: Medium

4. "What publications document the antimicrobial resistance patterns found in this surveillance data?"
   - Databases: AMR Portal, PubMed
   - Knowledge Required: dct:references property for literature linkage
   - Category: Integration
   - Difficulty: Easy

**Performance-Critical Questions**:

5. "How many bacterial isolates worldwide show resistance to meropenem?"
   - Database: AMR Portal
   - Knowledge Required: Single antibiotic filtering for performance
   - Category: Completeness
   - Difficulty: Easy

6. "What is the resistance rate distribution across all tested antibiotics?"
   - Database: AMR Portal
   - Knowledge Required: LIMIT clause, efficient aggregation
   - Category: Completeness
   - Difficulty: Medium

7. "Which countries have the most comprehensive antimicrobial resistance surveillance data?"
   - Database: AMR Portal
   - Knowledge Required: Geographic filtering and aggregation patterns
   - Category: Completeness
   - Difficulty: Medium

8. "How many distinct bacterial biosamples have both resistance phenotypes and resistance genes characterized?"
   - Database: AMR Portal
   - Knowledge Required: Understanding bioSample linkage coverage (~65%)
   - Category: Completeness
   - Difficulty: Medium

**Error-Avoidance Questions**:

9. "Find all blood culture isolates that showed antibiotic resistance"
   - Database: AMR Portal
   - Knowledge Required: Case-insensitive matching for "blood" (vs "Blood")
   - Category: Structured Query
   - Difficulty: Medium

10. "What resistance data is available for Klebsiella species?"
    - Database: AMR Portal
    - Knowledge Required: bif:contains keyword search for flexible matching
    - Category: Structured Query
    - Difficulty: Easy

11. "Compare resistance rates for ciprofloxacin across different testing laboratories"
    - Database: AMR Portal
    - Knowledge Required: laboratoryTypingMethod and astStandard properties
    - Category: Structured Query
    - Difficulty: Medium

**Complex Filtering Questions**:

12. "Which Klebsiella pneumoniae isolates are resistant to both meropenem and ciprofloxacin?"
    - Database: AMR Portal
    - Knowledge Required: bioSample aggregation for multi-drug patterns
    - Category: Structured Query
    - Difficulty: Medium

13. "What are the most highly multi-drug resistant bacterial isolates in the database?"
    - Database: AMR Portal
    - Knowledge Required: COUNT(DISTINCT antibiotic) with HAVING clause
    - Category: Completeness
    - Difficulty: Medium

14. "Find Escherichia coli isolates from urinary tract infections with fluoroquinolone resistance"
    - Database: AMR Portal
    - Knowledge Required: isolationSource filtering, antibiotic class filtering
    - Category: Structured Query
    - Difficulty: Hard

15. "What beta-lactamase genes are found in isolates showing meropenem resistance?"
    - Database: AMR Portal
    - Knowledge Required: Genotype-phenotype correlation via bioSample
    - Category: Integration
    - Difficulty: Hard

16. "Which bacterial species have the highest proportion of multi-drug resistant isolates?"
    - Database: AMR Portal
    - Knowledge Required: Complex aggregation with ratio calculation
    - Category: Structured Query
    - Difficulty: Hard

17. "Find resistance patterns in tuberculosis isolates from Asia collected after 2015"
    - Database: AMR Portal
    - Knowledge Required: Multiple filter combination (organism, region, year)
    - Category: Structured Query
    - Difficulty: Medium

**Temporal Analysis Questions**:

18. "How has ciprofloxacin resistance prevalence changed over the past 10 years?"
    - Database: AMR Portal
    - Knowledge Required: collectionYear filtering, temporal aggregation
    - Category: Currency
    - Difficulty: Medium

19. "When was antimicrobial resistance to carbapenems first detected in the surveillance data?"
    - Database: AMR Portal
    - Knowledge Required: MIN aggregation with year filtering
    - Category: Currency
    - Difficulty: Medium

20. "What is the trend in NDM carbapenemase gene detection over time?"
    - Database: AMR Portal
    - Knowledge Required: Gene symbol filtering + temporal analysis
    - Category: Currency
    - Difficulty: Hard

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

21. "What resistance phenotype is recorded for Salmonella enterica against ciprofloxacin?"
    - Method: Simple SPARQL lookup
    - Knowledge Required: None (straightforward query)
    - Category: Precision
    - Difficulty: Easy

22. "How many resistance tests are in the AMR Portal database?"
    - Method: Simple COUNT query
    - Knowledge Required: None
    - Category: Completeness
    - Difficulty: Easy

23. "What bacterial species are tested for antimicrobial resistance?"
    - Method: DISTINCT organism query
    - Knowledge Required: None
    - Category: Completeness
    - Difficulty: Easy

24. "What geographic regions have antimicrobial resistance surveillance data?"
    - Method: DISTINCT region query
    - Knowledge Required: None
    - Category: Completeness
    - Difficulty: Easy

**ID Mapping Questions**:

25. "What is the NCBI Taxonomy ID for Escherichia coli in the resistance database?"
    - Method: Query obo:RO_0002162 property
    - Knowledge Required: None (direct lookup)
    - Category: Precision
    - Difficulty: Easy

26. "What PubMed articles are cited in the antimicrobial resistance data?"
    - Method: Query dct:references property
    - Knowledge Required: None
    - Category: Integration
    - Difficulty: Easy

---

## Integration Patterns Summary

**AMR Portal as Source**:
- → ChEMBL: Via antibiotic name matching (case normalization needed)
- → PubMed: Via dct:references property (direct IRI links)
- → BioSample: Via amr:bioSample property (primary linkage)
- → SRA: Via amr:sraAccession property
- → INSDC: Via amr:assemblyId property

**AMR Portal as Target**:
- NCBI Taxonomy → AMR: Via obo:RO_0002162 on genotype features
- ARO Ontology → AMR: Via amr:antibioticOntologyId

**Complex Multi-Database Paths**:
- AMR → ChEMBL → ChEBI: Antibiotic compound properties and chemical ontology
- AMR → NCBI Taxonomy → BacDive: Organism classification and culture conditions
- AMR → PubMed → MeSH: Literature classification and medical subject headings

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Two-stage aggregation pattern**: Critical for any cross-database analytics involving counts or statistics
2. **Case-insensitive matching**: Essential for text fields with inconsistent capitalization
3. **BioSample linkage understanding**: Key for genotype-phenotype correlation studies
4. **Geographic hierarchy knowledge**: Enables proper regional analysis at multiple levels
5. **Performance-first filtering**: Adding specific criteria (single antibiotic, single region) before complex operations

### Common Pitfalls Discovered

1. **Text field inconsistency**: "Stool" vs "stool", "Blood" vs "blood" - always use LCASE()
2. **Incomplete genotype-phenotype coverage**: Only ~65% of samples have both data types
3. **Cross-database case mismatch**: ChEMBL uppercase vs AMR lowercase for drug names
4. **Large result sets**: Always use LIMIT for exploratory queries on 1.7M+ records

### Recommendations for Question Design

1. **Focus on surveillance use cases**: Geographic distribution, temporal trends, outbreak patterns
2. **Leverage genotype-phenotype correlation**: Unique capability for linking genes to resistance
3. **Include multi-drug resistance questions**: Clinically important and demonstrates complex queries
4. **Test cross-database integration**: ChEMBL enrichment requires specific knowledge
5. **Use real-world clinical scenarios**: Bloodstream infections, urinary tract infections, etc.

### Performance Notes

1. Most single-table aggregations complete in <10 seconds
2. Organism + antibiotic + phenotype aggregation works but requires LIMIT
3. Geographic filtering significantly reduces processing time
4. Cross-database queries need two-stage pattern or reverse join order
5. bif:contains provides efficient keyword search capability

---

## Notes and Observations

1. **Data quality varies by source**: PATRIC data more complete than some other sources
2. **Temporal data concentrated in recent years**: 2015-2021 have most records
3. **Geographic coverage uneven**: Americas (790K) >> Africa (54K)
4. **Quantitative MIC data limited**: Only ~30% of phenotype records have quantitative values
5. **Multiple data sources per record**: Many records from combined sources
6. **Taxonomy linkage only on genotype features**: Phenotype uses text organism names
7. **ARO ontology linkage incomplete**: Not all antibiotics have ontology IDs

---

## Next Steps

**Recommended for Question Generation**:
- Priority: Genotype-phenotype correlation questions
- Priority: Geographic surveillance pattern questions
- Priority: Multi-drug resistance profiling questions
- Priority: Temporal trend analysis questions
- Avoid: Questions requiring complete data coverage (varies by source)

**Focus Areas This Database Handles Well**:
- Surveillance epidemiology
- Resistance mechanism correlation
- Geographic and temporal patterns
- Multi-drug resistance detection

**Further Exploration Needed** (if any):
- More testing of complex ChEMBL integration patterns
- Exploration of ARO ontology linkage coverage
- Testing of PubMed cross-references for literature integration

---

**Session Complete - Ready for Next Database**

**Summary**:
```
Database: amrportal
Status: ✅ COMPLETE
Report: /evaluation/exploration/amrportal_exploration.md
Patterns Tested: 10+
Questions Identified: 26
Integration Points: 6+
Key Finding: Two-stage aggregation essential for cross-database queries
```
