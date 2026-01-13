# AMR Portal Exploration Report

## Database Overview
- **Purpose**: Antimicrobial resistance (AMR) surveillance database integrating phenotypic and genotypic data
- **Scope**: 1.7M phenotype measurements, 1.1M genotype features from bacterial isolates worldwide
- **Key data types**: Phenotypic AST results (MIC, disk diffusion), genotypic AMR features (genes, mutations)
- **Focus**: Epidemiological surveillance, genotype-phenotype correlation, geographic resistance patterns

## Schema Analysis (from MIE file)

### Main Properties Available
- **PhenotypeMeasurement**: Antimicrobial susceptibility test results
  - `amr:organism`, `amr:species`, `amr:genus` - Organism identification
  - `amr:antibioticName`, `amr:resistancePhenotype` - Test results (resistant/susceptible/intermediate)
  - `amr:country`, `amr:geographicalRegion`, `amr:geographicalSubregion` - Geographic metadata
  - `amr:collectionYear` - Temporal data
  - `amr:bioSample`, `amr:assemblyId`, `amr:sraAccession` - Cross-references
  - `amr:measurementValue`, `amr:measurementSign`, `amr:measurementUnits` - Quantitative MIC
- **GenotypeFeature**: AMR gene/mutation annotations
  - `amr:amrClass`, `amr:amrSubclass` - Resistance class (BETA-LACTAM, AMINOGLYCOSIDE, etc.)
  - `amr:geneSymbol`, `amr:amrElementSymbol` - Gene identification
  - `amr:region`, `amr:regionStart`, `amr:regionEnd` - Genomic coordinates
  - `obo:RO_0002162` - NCBI Taxonomy link

### Important Relationships
- BioSample IRI links phenotype and genotype data from same isolate
- Antibiotic Resistance Ontology (ARO) links for standardized terms
- NCBI Taxonomy via `obo:RO_0002162`
- PubMed references via `dct:references`

### Query Patterns Observed
- Always include FROM clause: `<http://rdfportal.org/dataset/amrportal>`
- Filter by organism first for performance
- Use `bif:contains` for flexible organism name matching
- Use LIMIT to prevent timeouts on large aggregations

## Search Queries Performed

### Query 1: Sample phenotype data
- **Search**: Basic PhenotypeMeasurement retrieval
- **Results**: Found resistance data for multiple organisms:
  - Streptococcus pneumoniae - trimethoprim-sulfamethoxazole (Thailand)
  - Klebsiella pneumoniae - ceftriaxone resistant (USA)
  - Salmonella enterica - multiple antibiotics susceptible (USA)

### Query 2: Organisms represented
- **Search**: DISTINCT organisms in phenotype data
- **Results**: 50+ bacterial species including:
  - Escherichia coli, Klebsiella pneumoniae
  - Salmonella enterica, Pseudomonas aeruginosa
  - Staphylococcus aureus, Mycobacterium tuberculosis
  - Neisseria gonorrhoeae, Acinetobacter baumannii

### Query 3: Genotype features (AMR genes)
- **Search**: GenotypeFeature retrieval with genomic coordinates
- **Results**: AMR genes with precise locations:
  - norM (EFFLUX) in N. gonorrhoeae: ERZ25089697.1:136650-138029
  - blaZ (BETA-LACTAM) in S. aureus: DAKTIE010000166.1:2295-3140
  - mecA (BETA-LACTAM) in S. aureus: DAKTIE010000169.1:1563-3569
  - gyrA_S91F (QUINOLONE) in N. gonorrhoeae: mutation

### Query 4: AMR class distribution
- **Search**: Gene class counts
- **Results**: Most common AMR classes:
  - BETA-LACTAM: 243,389 features
  - AMINOGLYCOSIDE: 187,430
  - EFFLUX: 180,406
  - TETRACYCLINE: 89,420
  - QUINOLONE: 80,396
  - SULFONAMIDE: 63,261

### Query 5: Resistance phenotype distribution
- **Search**: Phenotype value counts
- **Results**: Phenotype breakdown:
  - susceptible: 1,040,897 (61%)
  - resistant: 302,729 (18%)
  - intermediate: 35,332 (2%)
  - non-susceptible: 828
  - susceptible-dose dependent: 213

### Query 6: E. coli antibiotic resistance
- **Search**: E. coli resistance by antibiotic
- **Results**: Highest resistance rates in E. coli:
  - ampicillin: 7,688 resistant / 15,663 total (49%)
  - tetracycline: 3,524 / 8,807 (40%)
  - ciprofloxacin: 3,289 / 16,726 (20%)
  - trimethoprim-sulfamethoxazole: 2,848 / 12,361 (23%)

### Query 7: Geographic distribution of ciprofloxacin resistance
- **Search**: E. coli ciprofloxacin resistance by country
- **Results**: Top countries:
  - United States: 1,041 resistant isolates
  - United Kingdom: 790
  - Norway: 313
  - Viet Nam: 101
  - Thailand: 91

### Query 8: Carbapenem resistance genes
- **Search**: Beta-lactam genes in carbapenem-resistant isolates
- **Results**: Associated genes:
  - bla variants: 2,066 - 327 isolates (various)
  - ampC: 1,891 isolates
  - blaNDM-1: 258 isolates (carbapenemase)
  - ompC: 515 isolates (porin)

### Query 9: Temporal trends
- **Search**: E. coli ciprofloxacin resistance 2010-2023
- **Results**: Yearly data available (variable by year)
  - 2015: 630/1,438 resistant (44%)
  - 2020: 271/1,643 resistant (16%)
  - 2023: 138/215 resistant (64%)

## SPARQL Queries Tested

```sparql
# Query 1: Basic phenotype retrieval
PREFIX amr: <http://example.org/ebiamr#>

SELECT ?s ?organism ?antibiotic ?phenotype ?country
FROM <http://rdfportal.org/dataset/amrportal>
WHERE {
  ?s a amr:PhenotypeMeasurement .
  ?s amr:organism ?organism .
  ?s amr:antibioticName ?antibiotic .
  ?s amr:resistancePhenotype ?phenotype .
  OPTIONAL { ?s amr:country ?country }
}
LIMIT 20
# Results: Multiple organisms with resistance data
```

```sparql
# Query 2: AMR gene class distribution
PREFIX amr: <http://example.org/ebiamr#>

SELECT DISTINCT ?amrClass (COUNT(*) as ?count)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE {
  ?s a amr:GenotypeFeature .
  ?s amr:amrClass ?amrClass .
}
GROUP BY ?amrClass
ORDER BY DESC(?count)
LIMIT 30
# Results: BETA-LACTAM (243K), AMINOGLYCOSIDE (187K), EFFLUX (180K)
```

```sparql
# Query 3: Geographic resistance distribution
PREFIX amr: <http://example.org/ebiamr#>

SELECT ?country ?region (COUNT(*) as ?resistantCount)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE {
  ?s a amr:PhenotypeMeasurement .
  ?s amr:organism "Escherichia coli" .
  ?s amr:antibioticName "ciprofloxacin" .
  ?s amr:resistancePhenotype "resistant" .
  ?s amr:country ?country .
  ?s amr:geographicalRegion ?region .
}
GROUP BY ?country ?region
ORDER BY DESC(?resistantCount)
LIMIT 20
# Results: USA (1041), UK (790), Norway (313)
```

```sparql
# Query 4: Genotype-phenotype correlation
PREFIX amr: <http://example.org/ebiamr#>

SELECT DISTINCT ?geneSymbol ?amrClass (COUNT(DISTINCT ?bioSample) as ?isolateCount)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE {
  ?pheno a amr:PhenotypeMeasurement .
  ?pheno amr:bioSample ?bioSample .
  ?pheno amr:antibioticName ?antibiotic .
  ?pheno amr:resistancePhenotype "resistant" .
  FILTER(?antibiotic IN ("meropenem", "imipenem", "ertapenem"))
  
  ?geno a amr:GenotypeFeature .
  ?geno amr:bioSample ?bioSample .
  ?geno amr:geneSymbol ?geneSymbol .
  ?geno amr:amrClass ?amrClass .
  FILTER(CONTAINS(?amrClass, "BETA-LACTAM"))
}
GROUP BY ?geneSymbol ?amrClass
ORDER BY DESC(?isolateCount)
LIMIT 20
# Results: bla_1 (2066), ampC (1891), blaNDM-1 (258)
```

## Interesting Findings

### Specific Entities for Good Questions
1. **blaNDM-1**: Major carbapenemase gene (258 isolates in carbapenem-resistant bacteria)
2. **mecA**: MRSA marker gene in S. aureus
3. **gyrA_S91F**: Quinolone resistance mutation in N. gonorrhoeae
4. **norM**: Efflux pump gene for multidrug resistance
5. **E. coli ampicillin resistance**: 49% resistance rate (7,688/15,663)

### Unique Properties/Patterns
- Blank nodes for all measurements (no direct URIs)
- BioSample IRI serves as primary linkage between phenotype and genotype
- Geographic hierarchy: region → subregion → country → ISO code
- AMR class names use abbreviated forms (BETA-LACTAM, AMINOGLYCOSIDE)
- Resistance phenotypes: resistant, susceptible, intermediate, non-susceptible

### Connections to Other Databases
- **BioSample**: ~1.4M samples linked
- **SRA**: ~870K sequence accessions
- **INSDC/GenBank**: ~890K assembly IDs
- **PubMed**: Literature references via dct:references
- **ARO**: Antibiotic Resistance Ontology terms
- **NCBI Taxonomy**: Via obo:RO_0002162

### Verifiable Facts
- Total phenotype measurements: 1,714,486
- Total genotype features: 1,164,007
- Resistance rate: 18% resistant, 61% susceptible, 2% intermediate
- Most common AMR class: BETA-LACTAM (243,389 features)
- E. coli ampicillin resistance: ~49%
- blaNDM-1 gene found in 258 carbapenem-resistant isolates

## Question Opportunities by Category

### Precision
- "How many phenotype measurements in AMR Portal show resistance?" → 302,729
- "What is the most common AMR gene class?" → BETA-LACTAM (243,389 features)
- "What percentage of E. coli isolates are ampicillin-resistant?" → ~49%
- "How many blaNDM-1-positive isolates are carbapenem-resistant?" → 258

### Completeness
- "List all organisms in AMR Portal with phenotype data" → 50+ species
- "What resistance phenotype categories exist?" → resistant, susceptible, intermediate, non-susceptible, susceptible-dose dependent
- "List AMR gene classes with >50,000 features" → BETA-LACTAM, AMINOGLYCOSIDE, EFFLUX, TETRACYCLINE, QUINOLONE, SULFONAMIDE, MACROLIDE

### Integration
- "Link E. coli ciprofloxacin-resistant isolates to their geographic regions"
- "Find beta-lactam resistance genes in carbapenem-resistant isolates"
- "Connect BioSample to both phenotype and genotype data"

### Currency
- "What are the resistance trends for E. coli ciprofloxacin from 2010-2023?"

### Specificity
- "What is the genomic position of norM efflux pump in N. gonorrhoeae ERZ25089697?" → 136650-138029
- "Which countries have the most ciprofloxacin-resistant E. coli isolates?" → USA (1041), UK (790)
- "What antibiotics show >40% resistance in E. coli?" → ampicillin, tetracycline

### Structured Query
- "Find multi-drug resistant isolates (resistant to ≥3 antibiotics)"
- "List genotype features with genomic coordinates for S. aureus"
- "Find isolates with both phenotypic resistance and corresponding resistance genes"

## Notes

### Limitations
- Large dataset requires careful query design (timeouts possible)
- Not all isolates have both phenotype and genotype data (~65% linkage)
- Geographic data coverage ~80% (not all records have country)
- Quantitative MIC measurements ~30% coverage
- Isolation source text inconsistent (Stool vs stool)

### Best Practices
- Always use FROM clause: `<http://rdfportal.org/dataset/amrportal>`
- Filter by organism first for performance
- Use LIMIT for exploratory queries
- Use `bif:contains` for flexible text matching on organism names
- Use OPTIONAL for geographic/temporal fields (not always present)

### Anti-Patterns to Avoid
- ❌ Aggregations without organism filter (timeout)
- ❌ Exact string match for organisms (use bif:contains)
- ❌ Forgetting FROM clause (searches all graphs)
- ❌ Complex joins without selective filters (timeout)
- ❌ Case-sensitive matching on isolation sources

### Data Quality
- Phenotype values: controlled vocabulary (resistant/susceptible/intermediate)
- Laboratory typing methods: broth dilution (56%), agar dilution (8%), disk diffusion (7%)
- Evidence type in genotype: predominantly HMM (65%)
- Temporal range: 1911-2025, concentrated in recent decades
- Geographic coverage: 150+ countries across all continents
