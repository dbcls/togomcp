# BacDive Exploration Report

## Database Overview
- **Purpose**: Bacterial and archaeal strain metadata database maintained by DSMZ (German Collection of Microorganisms and Cell Cultures)
- **Scale**: 97,334 strain records with phenotypic and genotypic data
- **Key data types**: Strains, taxonomy, enzyme activities, culture conditions (temp, pH, medium), sequences (16S, genome), culture collection numbers

## Schema Analysis (from MIE file)

### Main Entity Types
- `schema:Strain` - Central entity with taxonomic hierarchy (domain→phylum→class→order→family→genus→species)
- `schema:Enzyme` - Enzyme activity phenotypes with +/- results
- `schema:GramStain` - Gram staining results
- `schema:CultureTemperature` - Growth temperature ranges
- `schema:CultureMedium` - Culture media links (to MediaDive)
- `schema:16SSequence` / `schema:GenomeSequence` - Sequence data with accessions
- `schema:CultureCollectionNumber` - Strain repository IDs (DSMZ, JCM, ATCC, etc.)

### Important Properties
- `schema:hasBacDiveID` - Unique BacDive identifier
- `schema:hasTaxID` - NCBI Taxonomy ID (100% coverage)
- `schema:isTypeStrain` - Boolean type strain indicator
- `schema:hasTemperatureRangeStart/End` - Growth temperature bounds
- `schema:hasGramStain` - positive/negative/variable
- `schema:hasOxygenTolerance` - aerobe/anaerobe/facultative
- `schema:hasActivity` - Enzyme activity (+/-)

### Query Patterns
- Must use `FROM <http://rdfportal.org/dataset/bacdive>` graph clause
- Use `bif:contains` for keyword search with score ranking (Virtuoso)
- Use `OPTIONAL` for phenotypes (coverage ~40%)
- Hub-and-spoke architecture: Strain is central, phenotypes link via `schema:describesStrain`

## Search Queries Performed

1. **Query: Top genera by strain count**
   - Streptomyces: 24,747 strains (25.4% - largest genus)
   - Bacillus: 3,332 strains
   - Arthrobacter: 2,045 strains
   - Streptococcus: 2,001 strains
   - Escherichia: 1,898 strains
   - Pseudomonas: 1,879 strains

2. **Query: Domain distribution**
   - Bacteria: 95,742 strains (98.4%)
   - Archaea: 1,049 strains (1.1%)

3. **Query: Type strain count**
   - Type strains: 20,060 (20.6%)
   - Non-type strains: 77,274 (79.4%)

4. **Query: Gram stain distribution**
   - Gram-negative: 10,747 strains
   - Gram-positive: 7,333 strains
   - Gram-variable: 135 strains

5. **Query: Top enzymes with positive activity**
   - Alkaline phosphatase: 16,153 positive results
   - Beta-galactosidase: 13,609 positive
   - Catalase: 13,129 positive
   - Leucine arylamidase: 12,735 positive

## SPARQL Queries Tested

```sparql
# Query 1: Find hyperthermophiles (growth temp ≥70°C)
PREFIX schema: <https://purl.dsmz.de/schema/>
SELECT ?strain ?label ?bacdiveId ?tempStart ?tempEnd
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ; rdfs:label ?label ; schema:hasBacDiveID ?bacdiveId .
  ?temp a schema:CultureTemperature ;
        schema:describesStrain ?strain ;
        schema:hasTemperatureRangeStart ?tempStart .
  FILTER(?tempStart >= 70)
}
ORDER BY DESC(?tempStart) LIMIT 20
# Results: 360 strains grow at ≥70°C
# Top: Pyrococcus kukulkanii (105°C), Pyrolobus fumarii (103°C), Aeropyrum pernix (102°C)
```

```sparql
# Query 2: Find Thermotoga maritima strain collection numbers
PREFIX schema: <https://purl.dsmz.de/schema/>
SELECT ?strain ?label ?ccnLabel
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ; rdfs:label ?label ; schema:hasSpecies "Thermotoga maritima" .
  ?ccn a schema:CultureCollectionNumber ; schema:describesStrain ?strain ; rdfs:label ?ccnLabel .
}
# Results: BacDive ID 17060, DSM 3109, ATCC 43589, JCM 10099, NBRC 100826
```

```sparql
# Query 3: Find methanogens (anaerobic archaea)
PREFIX schema: <https://purl.dsmz.de/schema/>
SELECT ?strain ?label ?bacdiveId ?oxygenTolerance
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ; rdfs:label ?label ; schema:hasBacDiveID ?bacdiveId ; schema:hasGenus "Methanococcus" .
  ?ot a schema:OxygenTolerance ; schema:describesStrain ?strain ; schema:hasOxygenTolerance ?oxygenTolerance .
}
# Results: All Methanococcus strains are strict anaerobes
# Found: M. aeolicus (7001), M. vannielii (6993), M. maripaludis (6989), M. voltae (6994)
```

## Cross-Reference Analysis

**Entity counts with cross-references:**
- All strains have NCBI Taxonomy IDs (100% coverage)
- ~60% have culture collection numbers
- ~35% have 16S rRNA sequences
- ~20% have MediaDive culture medium links

**Cross-Database Linkages:**
- `schema:hasTaxID` → NCBI Taxonomy (co-located on same endpoint)
- `schema:hasMediaLink` → MediaDive (co-located on same endpoint)
- `schema:hasSequenceAccession` → ENA/GenBank (external)
- `schema:hasLink` (CultureCollectionNumber) → DSMZ, JCM, ATCC, KCTC (external)

**Co-located databases on "primary" endpoint:**
- BacDive ↔ MediaDive: Culture protocols
- BacDive ↔ Taxonomy: Phylogenetic context
- BacDive ↔ MONDO: Disease associations
- BacDive ↔ MeSH: Medical terminology

## Interesting Findings (requiring queries, not from MIE)

### Biodiversity Statistics
- **Total strains**: 97,334
- **Streptomyces dominance**: 24,747 strains (25.4% of all strains) - reflects biotechnology/antibiotic interest
- **Archaea representation**: 1,049 strains (1.1%) including methanogens and hyperthermophiles
- **Type strains**: 20,060 (20.6%) - reference strains for species

### Extremophile Data
- **Hyperthermophiles** (≥70°C): 360 strains
- **Highest growth temperature**: Pyrococcus kukulkanii at 105°C (BacDive ID 132578)
- **Other hyperthermophiles**: Pyrolobus fumarii (103°C), Aeropyrum pernix (102°C)

### Phenotype Data
- **Catalase-positive strains**: 13,129 strains
- **Most common positive enzyme**: Alkaline phosphatase (16,153 positive results)
- **Gram-negative predominance**: 10,747 vs 7,333 Gram-positive

### Reference Strain Data
- **Thermotoga maritima**: BacDive ID 17060, DSM 3109 (model thermophile organism)
- Culture collection numbers: ATCC 43589, JCM 10099, NBRC 100826

## Question Opportunities by Category

### Precision
- "What is the BacDive ID for Thermotoga maritima?" → 17060
- "What is the DSM strain number for Thermotoga maritima?" → DSM 3109
- "What is the BacDive ID for Pyrococcus kukulkanii?" → 132578

### Completeness
- "How many bacterial strains are in BacDive?" → 97,334
- "How many archaeal strains are in BacDive?" → 1,049
- "How many type strains are in BacDive?" → 20,060
- "How many strains in BacDive can grow at temperatures ≥70°C?" → 360

### Integration
- "What are the culture collection numbers for Thermotoga maritima in BacDive?"
- "Link BacDive strain to its MediaDive culture medium recipe"
- "What is the NCBI Taxonomy ID for a specific BacDive strain?"

### Currency
- "What are the most recently added strains to BacDive?" (requires date data if available)
- Current growth conditions for specific organisms

### Specificity
- "What is the optimal growth temperature for Pyrolobus fumarii?" → 103°C
- "What is the oxygen tolerance for Methanococcus species?" → strict anaerobes
- "Which bacteria in BacDive grow at temperatures above 100°C?" → Pyrococcus kukulkanii, Pyrolobus fumarii, Aeropyrum pernix

### Structured Query
- "Find all Gram-negative thermophilic bacteria with catalase activity"
- "List Streptomyces strains with beta-galactosidase activity"
- "Which archaea are recorded as strict anaerobes in BacDive?"

## Notes

### Data Coverage
- Phenotype coverage varies significantly (~40% Gram stain, ~35% 16S, ~55% enzyme)
- Type strains have better phenotypic characterization
- Streptomyces over-represented due to industrial/antibiotic interest

### Best Practices
- Always specify `FROM <http://rdfportal.org/dataset/bacdive>` graph clause
- Use `OPTIONAL` for all phenotype properties
- Use `bif:contains` for keyword search with `option (score ?sc)` for ranking
- Don't use `?score` as variable name (reserved keyword in Virtuoso)
- Filter by genus/family before complex phenotype joins

### Limitations
- Not all strains have complete phenotypic data
- MediaDive links available only for ~20% of strains
- 16S sequences available for ~35% of strains
