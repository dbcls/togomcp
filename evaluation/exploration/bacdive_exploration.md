# BacDive (Bacterial Diversity Metadatabase) Exploration Report

## Database Overview
- **Purpose**: Standardized bacterial and archaeal strain information for microbiology research
- **Scope**: 97,334 strain records with phenotypic and genotypic characterizations
- **Key data types**: Taxonomy, morphology, physiology, cultivation conditions, molecular sequences
- **Focus**: Type strains (20,060), culture collection links, enzyme activities

## Schema Analysis (from MIE file)

### Main Properties Available
- **Taxonomy**: `schema:hasGenus`, `schema:hasSpecies`, `schema:hasFamily`, `schema:hasOrder`, `schema:hasClass`, `schema:hasPhylum`, `schema:hasDomain`
- **Identifiers**: `schema:hasBacDiveID`, `schema:hasTaxID` (NCBI)
- **Phenotypes**: 
  - `schema:GramStain` with `schema:hasGramStain` (positive/negative/variable)
  - `schema:CellMotility` with `schema:isMotile` (boolean)
  - `schema:OxygenTolerance` with `schema:hasOxygenTolerance` (aerobe/anaerobe/facultative)
- **Culture conditions**:
  - `schema:CultureMedium` with `schema:hasMediaLink` to MediaDive
  - `schema:CultureTemperature` with `schema:hasTemperatureRangeStart/End`
  - `schema:CulturePH` with `schema:hasPHRangeStart/End`
- **Sequences**: `schema:16SSequence`, `schema:GenomeSequence` with `schema:hasSequenceAccession`
- **Culture collections**: `schema:CultureCollectionNumber` with `schema:hasLink`
- **Enzymes**: `schema:Enzyme` with `schema:hasActivity` (+/-/variable)

### Important Relationships
- Hub-and-spoke: All entities link to Strain via `schema:describesStrain`
- NCBI Taxonomy IDs (`schema:hasTaxID`) on all strains
- Culture collection links to DSMZ, JCM, KCTC, ATCC, NBRC
- Sequence accessions to ENA/GenBank
- MediaDive links for culture media recipes

### Query Patterns Observed
- Keyword search using `bif:contains` with boolean operators
- Temperature filtering with `schema:hasTemperatureRangeEnd >= value`
- Type strain filtering with `schema:isTypeStrain true`
- BacDive ID lookup with `schema:hasBacDiveID`

## Search Queries Performed

### Query 1: Thermotoga strains
- **Search**: `bif:contains "'Thermotoga'"`
- **Results**: 9 strains including:
  - Thermotoga maritima 17060 (type strain, DSM 3109)
  - Thermotoga petrophila 17068
  - Thermotoga neapolitana 17061, 17062

### Query 2: Hyperthermophiles (>80°C growth)
- **Search**: `schema:hasTemperatureRangeEnd >= 80`
- **Results**: 221 strains capable of growth above 80°C
- Top temperature: Pyrococcus kukulkanii at 112°C optimal growth
- Other hyperthermophiles: Pyrolobus fumarii (103°C), Aeropyrum pernix (102°C)

### Query 3: Methanocaldococcus jannaschii details
- **Search**: `bif:contains "'jannaschii'"`
- **Results**: Found at BacDive ID 6981
  - Culture medium: DSMZ Medium 282 (linked to MediaDive)
  - Taxonomy confirmed: Methanocaldococcus genus (formerly Methanococcus)

### Query 4: Culture collections for Thermotoga maritima
- **Search**: Culture collection numbers for strain 17060
- **Results**: 4 culture collection links:
  - DSM 3109 (DSMZ)
  - ATCC 43589
  - JCM 10099
  - NBRC 100826

### Query 5: Type strains count
- **Search**: `schema:isTypeStrain true`
- **Results**: 20,060 type strains (~21% of all strains)

## SPARQL Queries Tested

```sparql
# Query 1: Search strains by keyword
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strain ?label ?sc
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?label .
  ?label bif:contains "'Thermotoga'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
# Results: 9 Thermotoga strains found
```

```sparql
# Query 2: Find hyperthermophiles by temperature
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strain ?strainLabel ?tempStart ?tempEnd
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?strainLabel .
  ?temp a schema:CultureTemperature ;
        schema:describesStrain ?strain ;
        schema:hasTemperatureRangeEnd ?tempEnd .
  FILTER(?tempEnd >= 80)
}
ORDER BY DESC(?tempEnd)
LIMIT 30
# Results: Pyrococcus kukulkanii tops at 112°C, 221 total hyperthermophiles
```

```sparql
# Query 3: Get culture medium with MediaDive link
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strain ?strainLabel ?medium ?mediaLink
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?strainLabel .
  ?m a schema:CultureMedium ;
     schema:describesStrain ?strain ;
     rdfs:label ?medium .
  OPTIONAL { ?m schema:hasMediaLink ?mediaLink }
  FILTER(?strain = <https://purl.dsmz.de/bacdive/strain/6981>)
}
# Results: Methanocaldococcus jannaschii uses DSMZ Medium 282
```

```sparql
# Query 4: Get culture collection numbers
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strain ?strainLabel ?collectionLabel ?link
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?strainLabel .
  ?ccn a schema:CultureCollectionNumber ;
       schema:describesStrain ?strain ;
       rdfs:label ?collectionLabel .
  OPTIONAL { ?ccn schema:hasLink ?link }
  FILTER(?strain = <https://purl.dsmz.de/bacdive/strain/17060>)
}
# Results: DSM 3109, ATCC 43589, JCM 10099, NBRC 100826
```

## Interesting Findings

### Specific Entities for Good Questions
1. **Thermotoga maritima**: BacDive ID 17060, DSM 3109, type strain
2. **Pyrococcus kukulkanii**: Record for highest growth temperature (112°C)
3. **Methanocaldococcus jannaschii**: BacDive ID 6981, uses DSMZ Medium 282
4. **Pyrolobus fumarii**: Growth at 103°C
5. **Aeropyrum pernix**: Growth at 102°C

### Unique Properties/Patterns
- Type strain designation enables quality filtering
- Multiple culture collection cross-references per strain
- MediaDive integration for culture recipes
- Comprehensive temperature/pH growth data

### Connections to Other Databases
- **NCBI Taxonomy**: `schema:hasTaxID` on all strains
- **DSMZ/JCM/KCTC/ATCC**: Culture collection links with URLs
- **ENA/GenBank**: Sequence accessions
- **MediaDive**: Culture medium recipes via `schema:hasMediaLink`

### Verifiable Facts
- Total strains: 97,334
- Type strains: 20,060 (21%)
- 16S sequences: ~87,045 (35% coverage)
- Enzyme records: 573,112
- Hyperthermophiles (>80°C): 221 strains
- Highest growth temperature: 112°C (Pyrococcus kukulkanii)

## Question Opportunities by Category

### Precision
- "What is the BacDive ID for Thermotoga maritima type strain?" → 17060
- "What is the DSM number for Thermotoga maritima?" → DSM 3109
- "What culture medium does BacDive recommend for Methanocaldococcus jannaschii?" → DSMZ Medium 282

### Completeness
- "How many bacterial strains are recorded in BacDive?" → 97,334
- "How many type strains are in BacDive?" → 20,060
- "How many strains in BacDive can grow at temperatures above 80°C?" → 221

### Integration
- "What is the NCBI Taxonomy ID for Thermotoga maritima?" → 2336
- "Which culture collections hold Thermotoga maritima strains?" → DSMZ, ATCC, JCM, NBRC
- "Link BacDive strain to its MediaDive culture medium" → e.g., Medium 282 link

### Currency
- "What is the most recently characterized hyperthermophile in BacDive?"
- "What strains have both genome sequences and 16S rRNA sequences available?"

### Specificity
- "What is the highest growth temperature recorded in BacDive?" → 112°C (Pyrococcus kukulkanii)
- "Which archaeal strain in BacDive has the highest temperature tolerance?" → Pyrococcus kukulkanii
- "What is the oxygen tolerance of Methanococcus maripaludis?" → anaerobe

### Structured Query
- "Find all Gram-negative thermophilic bacteria in BacDive"
- "List all type strains with 16S rRNA sequences from the Thermotogaceae family"
- "Which anaerobic strains in BacDive can grow above 90°C?"

## Notes

### Limitations
- Phenotype coverage varies (~40% for Gram stain, ~35% for 16S)
- Some older strains have incomplete metadata
- OLS4 search not applicable - use SPARQL with bif:contains

### Best Practices
- Always include `FROM <http://rdfportal.org/dataset/bacdive>` in SPARQL
- Use `bif:contains` for keyword searches with `option (score ?sc)`
- Use OPTIONAL for phenotype properties (coverage is incomplete)
- Filter by `schema:isTypeStrain true` for high-quality characterized strains
- Never use `?score` as variable name (reserved keyword)

### Data Quality
- 100% taxonomic coverage (all strains have taxonomy)
- ~21% are type strains (well-characterized)
- ~35% have 16S sequences
- ~55% have enzyme activity data
- ~40% have Gram stain data
