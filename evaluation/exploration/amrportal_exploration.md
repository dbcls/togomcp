# AMR Portal Exploration Report

## Database Overview
- **Purpose**: Integrates antimicrobial resistance (AMR) surveillance data from NCBI Pathogen Detection, PATRIC, and CABBAGE
- **Scale**: 1.7M+ phenotypic AST results + 1.1M+ genotypic AMR features
- **Key data types**: Phenotype measurements (MIC, disk diffusion), genotype features (AMR genes, mutations), geographic/temporal metadata

## Schema Analysis (from MIE file)

### Main Entity Types
- `amr:PhenotypeMeasurement` - AST results with resistance phenotypes
- `amr:GenotypeFeature` - AMR genes and mutations detected in genomes

### Important Properties
- **Phenotype**: organism, antibioticName, resistancePhenotype, measurementValue/Sign/Units
- **Genotype**: amrClass, amrSubclass, geneSymbol, amrElementSymbol, elementType
- **Metadata**: country, geographicalRegion, collectionYear, isolationSource, host
- **Links**: bioSample, assemblyId, sraAccession, dct:references (PubMed)

### Query Patterns
- Must use `FROM <http://rdfportal.org/dataset/amrportal>` graph clause
- Organism names are full species names (e.g., "Escherichia coli", not "E. coli")
- Use `bif:contains` for keyword search with score ranking
- Always filter by organism or antibiotic before aggregations to avoid timeouts

## Search Queries Performed

Since AMR Portal uses SPARQL (no dedicated search function), queries were run directly:

1. **Query: Top organisms by phenotype count**
   - Salmonella enterica: 443,249 measurements (most common)
   - Escherichia coli: 364,276 measurements
   - Mycobacterium tuberculosis: 331,449 measurements
   - Klebsiella pneumoniae: 133,136 measurements
   - Neisseria gonorrhoeae: 95,195 measurements

2. **Query: Top AMR gene classes**
   - BETA-LACTAM: 243,389 features (most common)
   - AMINOGLYCOSIDE: 187,430 features
   - EFFLUX: 180,406 features (efflux pumps)
   - TETRACYCLINE: 89,420 features
   - QUINOLONE: 80,396 features

3. **Query: Resistance phenotype distribution**
   - Susceptible: 1,040,897 (60.7%)
   - Resistant: 302,729 (17.7%)
   - Intermediate: 35,332 (2.1%)
   - Non-susceptible: 828
   - Susceptible-dose dependent: 213

4. **Query: E. coli resistance by antibiotic**
   - Ampicillin: 7,688 resistant isolates (most common)
   - Tetracycline: 3,524 resistant
   - Ciprofloxacin: 3,289 resistant
   - Trimethoprim-sulfamethoxazole: 2,848 resistant
   - Amoxicillin-clavulanic acid: 2,295 resistant

5. **Query: Geographic distribution of ciprofloxacin-resistant E. coli**
   - United States: 1,041 isolates
   - United Kingdom: 790 isolates
   - Norway: 313 isolates
   - Vietnam: 101 isolates
   - Thailand: 91 isolates

## SPARQL Queries Tested

```sparql
# Query 1: Count beta-lactam resistance genes in K. pneumoniae
PREFIX amr: <http://example.org/ebiamr#>
SELECT DISTINCT ?geneSymbol (COUNT(DISTINCT ?bioSample) as ?isolateCount)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE {
  ?s a amr:GenotypeFeature .
  ?s amr:organism "Klebsiella pneumoniae" .
  ?s amr:geneSymbol ?geneSymbol .
  ?s amr:amrClass ?amrClass .
  ?s amr:bioSample ?bioSample .
  FILTER(CONTAINS(?amrClass, "BETA-LACTAM"))
}
GROUP BY ?geneSymbol
ORDER BY DESC(?isolateCount)
LIMIT 20
# Results: bla_1 (6,473 isolates), bla_2 (6,247), ompC (1,252), blaNDM-1 (191) etc.
```

```sparql
# Query 2: Countries with most ciprofloxacin-resistant E. coli
PREFIX amr: <http://example.org/ebiamr#>
SELECT ?country (COUNT(*) as ?resistantCount)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE {
  ?s a amr:PhenotypeMeasurement .
  ?s amr:organism "Escherichia coli" .
  ?s amr:antibioticName "ciprofloxacin" .
  ?s amr:resistancePhenotype "resistant" .
  ?s amr:country ?country .
}
GROUP BY ?country ORDER BY DESC(?resistantCount) LIMIT 15
# Results: USA (1,041), UK (790), Norway (313), Vietnam (101)
```

```sparql
# Query 3: Total phenotype and genotype counts
PREFIX amr: <http://example.org/ebiamr#>
SELECT (COUNT(*) as ?total)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE { ?s a amr:PhenotypeMeasurement . }
# Result: 1,714,486 phenotype measurements

SELECT (COUNT(*) as ?total)
FROM <http://rdfportal.org/dataset/amrportal>
WHERE { ?s a amr:GenotypeFeature . }
# Result: 1,164,007 genotype features
```

## Cross-Reference Analysis

**Linkage Points**:
- `amr:bioSample` → NCBI BioSample (~1.4M unique samples)
- `amr:sraAccession` → NCBI SRA (~870K accessions)
- `amr:assemblyId` → INSDC GenBank (~890K assemblies)
- `dct:references` → PubMed literature
- `amr:antibioticOntologyId` → ARO (Antibiotic Resistance Ontology)
- `obo:RO_0002162` → NCBI Taxonomy

**Cross-Database Queries** (co-located on EBI endpoint):
- AMR Portal ↔ ChEMBL: Link resistance surveillance to compound properties
- AMR Portal ↔ ChEBI: Chemical ontology for antibiotics
- AMR Portal ↔ Reactome: Potential pathway analysis
- AMR Portal ↔ Ensembl: Genomic context

## Interesting Findings (requiring queries, not from MIE)

### Epidemiological Facts
- **Top pathogen**: Salmonella enterica with 443,249 resistance measurements
- **E. coli ampicillin resistance**: 7,688 resistant isolates (most common E. coli resistance)
- **Global ciprofloxacin-resistant E. coli**: USA and UK lead with 1,041 and 790 cases respectively
- **K. pneumoniae beta-lactamase genes**: bla_1 found in 6,473 isolates, NDM-1 carbapenemase in 191 isolates
- **Overall resistance rate**: ~17.7% resistant, ~60.7% susceptible

### AMR Gene Distribution
- **Efflux pump prevalence**: 180,406 efflux-related genotype features (3rd most common mechanism)
- **Beta-lactam resistance dominance**: 243,389 beta-lactam resistance features (most common)
- **Multi-drug resistance genes**: 11,290 MULTIDRUG class features

### Methodology Coverage
- Laboratory methods: broth dilution (56%), agar dilution (8%), disk diffusion (7%)
- Standards: CLSI (most common)

## Question Opportunities by Category

### Precision
- "What is the total number of phenotypic resistance measurements in AMR Portal?" → 1,714,486
- "What is the most common resistance phenotype category?" → susceptible (1,040,897)
- "How many genotypic AMR features are recorded in AMR Portal?" → 1,164,007

### Completeness
- "How many ciprofloxacin-resistant E. coli isolates are reported from the USA?" → 1,041
- "How many bacterial species have resistance data in AMR Portal?" → 20+ major species
- "How many beta-lactam resistance genes are detected in Klebsiella pneumoniae isolates?" → Multiple (bla_1 in 6,473 isolates)

### Integration
- "Link AMR Portal resistance data with ChEMBL compound information for ciprofloxacin"
- "What NCBI Taxonomy IDs are associated with AMR genotype features?"

### Currency
- "What are the most recent temporal resistance trends for E. coli?" (requires year filtering)
- "How has carbapenem resistance in K. pneumoniae changed?" (requires temporal queries)

### Specificity
- "What resistance mechanisms are found in Clostridioides difficile?" (4,181 measurements)
- "What AMR genes are detected in Neisseria meningitidis isolates?" (2,659 phenotype records)

### Structured Query
- "Find isolates resistant to at least 3 different antibiotics (multi-drug resistant)"
- "Which countries report the highest ampicillin resistance rates in E. coli?"
- "What beta-lactamase genes correlate with carbapenem resistance in K. pneumoniae?"

## Notes

### Limitations
- Blank nodes used for all measurements (no direct URIs for records)
- Text capitalization inconsistent in some fields (Stool/stool, Urine/urine)
- Geographic completeness varies (~80% have location data)
- Cross-database queries add 10-20 seconds overhead

### Best Practices
- Always specify `FROM <http://rdfportal.org/dataset/amrportal>` graph clause
- Filter by organism or antibiotic before aggregations
- Use `bif:contains` for keyword search
- Use `LIMIT` for exploratory queries to avoid timeouts
- Use `LCASE()` for case-insensitive cross-database matching

### Important Count Distinctions
- **Entity count**: Number of unique organisms, antibiotics, or countries
- **Relationship count**: Total number of resistance measurements or features
- Example: 20+ organisms have data, but 1.7M+ total measurements exist
