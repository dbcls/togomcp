# BacDive Exploration Report

## Database Overview
- **Purpose**: BacDive (Bacterial Diversity Metadatabase) provides standardized bacterial and archaeal strain information covering taxonomy, morphology, physiology, cultivation conditions, and molecular data.
- **Scope**: 97,000+ strain records with phenotypic and genotypic characterizations
- **Key data types**: Strains (core records), Phenotypes (morphology, Gram staining, enzyme activities, oxygen tolerance), CultureConditions (media, temperature, pH), Sequences (16S rRNA, genomes), GeographicOrigin

## Schema Analysis (from MIE file)

### Main Properties Available
- **Strain core**: BacDive ID, TaxID, genus, species, family, domain, designation, type strain status, scientific name
- **Phenotypes**: Gram stain, cell motility, oxygen tolerance
- **Enzyme activities**: Enzyme name, activity status (+/-), EC number
- **Culture conditions**: Temperature range, pH range, culture medium with links to recipes
- **Sequences**: 16S rRNA sequences and genome sequences with accessions, sequence length, database source
- **Geographic data**: Country, latitude, longitude of isolation location
- **Culture collections**: Links to institutional collections (DSMZ, JCM, KCTC, CCUG, etc.)

### Important Relationships
- Hub-and-spoke design with Strain as central entity
- All phenotypes and annotations connect via `schema:describesStrain`
- Sequences linked via `schema:hasSequenceAccession`
- Culture collections linked via `schema:hasLink` to institutional databases
- NCBI Taxonomy integration via `schema:hasTaxID`

### Query Patterns Observed
- **Full-text search** using Virtuoso's `bif:contains` with boolean operators (AND, OR, NOT)
- Relevance scoring with `option (score ?sc)`
- OPTIONAL clauses critical for phenotypes due to incomplete coverage
- Keywords in single quotes: `'keyword'`, boolean logic: `'keyword1' AND 'keyword2'`

## Search Queries Performed

1. **Query**: Escherichia coli strains
   - **Results**: Found 10 E. coli strains with IDs like 134430, 134451, 135530, etc.
   - Relevance scores all at 24 indicating exact matches

2. **Query**: Bacillus enzyme activities
   - **Results**: Found various positive enzyme activities including:
     - Bacillus aryabhattai: gelatinase (+)
     - Bacillus subtilis: caseinase, catalase, gamma-glutamyltransferase, protease, beta-galactosidase, alcohol dehydrogenase, gelatinase, amylase, DNase (+)
     - Bacillus cereus: oxidase, catalase (+)
     - Terribacillus saccharophilus: DNase, caseinase, catalase, lecithinase (+)

3. **Query**: Strains with 16S sequences (sorted by length)
   - **Results**: Found both genome-length sequences (9M+ bp) and actual 16S rRNA (~1900-2000 bp)
   - Notable long sequences: Bradyrhizobium barranii (9.9M bp genome), Frigoriglobus tundricola (9.8M bp)
   - Typical 16S: Mycobacterium insubricum (1995 bp), Leptospira species (~1900-1994 bp)

4. **Query**: Thermophilic bacteria with phenotypes
   - **Results**: Found strains with "thermophilic" in descriptions:
     - Campylobacter pinnipediorum: microaerotolerant, thermophilic, Gram-negative, temp 22-42°C
     - Nonomuraea rhodomycinica: aerobe, spore-forming, thermophilic, Gram-positive, temp 20-50°C
     - Mycoplasmopsis ciconiae: thermophilic, Gram-negative, pleomorphic, temp 10-46°C

5. **Query**: Culture collection numbers (DSM)
   - **Results**: Found extensive links to DSMZ collection:
     - DSM 45197, DSM 45095, DSM 45136, DSM 20295, DSM 30723, etc.
     - All with direct URLs to DSMZ catalogue pages

6. **Query**: Geographic locations
   - **Results**: Found diverse origins with coordinates:
     - Salmonella enterica (Denmark: 55.68°N, 12.57°E)
     - Rhodanobacter umsongensis (South Korea: 36.93°N, 127.73°E)
     - Marinactinospora thermotolerans (China: 17.98°N, 116.00°E)
     - Methanoregula boonei (USA: 42.5°N, -76.5°W)
     - Thermodesulfatator atlanticus (International waters: 36.23°N, -33.90°W)

## SPARQL Queries Tested

```sparql
# Query 1: Full-text search for E. coli
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strain ?label ?sc
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?label .
  ?label bif:contains "'escherichia' AND 'coli'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10

# Results: Successfully found 10 E. coli strains with relevance scores, demonstrating powerful full-text search capability
```

```sparql
# Query 2: Enzyme activities for Bacillus species
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strainLabel ?enzymeLabel ?activity
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?strainLabel .
  ?enzyme a schema:Enzyme ;
          schema:describesStrain ?strain ;
          rdfs:label ?enzymeLabel ;
          schema:hasActivity ?activity .
  FILTER(?activity = "+")
  FILTER(CONTAINS(LCASE(?strainLabel), "bacillus"))
}
LIMIT 20

# Results: Retrieved diverse enzyme activities including gelatinase, caseinase, catalase, protease, amylase, DNase for various Bacillus species
```

```sparql
# Query 3: 16S sequences with length filtering
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strain ?strainLabel ?accession ?length
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?strainLabel .
  ?seq a schema:16SSequence ;
       schema:describesStrain ?strain ;
       schema:hasSequenceAccession ?accession ;
       schema:hasSequenceLength ?length .
  FILTER(?length < 2000)
}
ORDER BY DESC(?length)
LIMIT 20

# Results: Found typical 16S rRNA sequences (~1900-2000 bp) from Mycobacterium, Leptospira, Bacteroides species with ENA/GenBank accessions
```

```sparql
# Query 4: Thermophilic bacteria with phenotypes
PREFIX schema: <https://purl.dsmz.de/schema/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?strain ?description ?gramStain ?tempStart ?tempEnd ?sc
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          dct:description ?description .
  ?description bif:contains "'thermophilic'" option (score ?sc) .
  
  OPTIONAL {
    ?gs a schema:GramStain ;
        schema:describesStrain ?strain ;
        schema:hasGramStain ?gramStain .
  }
  OPTIONAL {
    ?temp a schema:CultureTemperature ;
          schema:describesStrain ?strain ;
          schema:hasTemperatureRangeStart ?tempStart ;
          schema:hasTemperatureRangeEnd ?tempEnd .
  }
}
ORDER BY DESC(?sc)
LIMIT 15

# Results: Successfully combined full-text search with structured phenotype data, showing temperature ranges and Gram stain properties
```

```sparql
# Query 5: Geographic locations with coordinates
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?strainLabel ?country ?latitude ?longitude
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?strainLabel .
  ?location a schema:LocationOfOrigin ;
            schema:describesStrain ?strain ;
            schema:hasCountry ?country ;
            schema:hasLatitude ?latitude ;
            schema:hasLongitude ?longitude .
}
LIMIT 20

# Results: Retrieved diverse geographic origins worldwide with precise coordinates, enabling geographic distribution studies
```

## Interesting Findings

### Specific Entities for Questions
1. **Campylobacter pinnipediorum** (strain 140488) - microaerotolerant, thermophilic, Gram-negative, isolated from California sea lion abscess
2. **Nonomuraea rhodomycinica** (strain 140579) - aerobe, spore-forming, thermophilic, from peat swamp forest soil, temp 20-50°C
3. **Bradyrhizobium barranii subsp. apii** (strain 170252) - has complete 9.9M bp genome sequence
4. **Bacillus subtilis** (strain 137036) - exhibits 9 different positive enzyme activities
5. **Thermodesulfatator atlanticus** (strain 16890) - isolated from international waters in Atlantic Ocean

### Unique Properties
- **Mixed sequence data**: Database contains both 16S rRNA sequences (~1900 bp) AND complete genomes (up to 9M+ bp) in same field
- **Rich enzyme data**: 573,112 enzyme records covering diverse metabolic activities
- **Geographic precision**: Latitude/longitude coordinates for many strains enabling spatial analysis
- **Culture collection integration**: Direct links to institutional collections (DSMZ, JCM, KCTC, CCUG)
- **Full-text search power**: Virtuoso's `bif:contains` with boolean logic very effective

### Connections to Other Databases
- **NCBI Taxonomy**: Via `schema:hasTaxID` (100% coverage)
- **ENA/GenBank**: Via sequence accessions (~35% 16S, ~10% genomes)
- **Culture collections**: DSMZ (>90%), JCM (~40%), KCTC (~30%), CCUG (~25%)
- **MediaDive**: Via `schema:hasMediaLink` (~20% of culture media)

### Specific, Verifiable Facts
- Total strains: 97,334
- Total enzymes: 573,112
- Total 16S sequences: 87,045
- Average enzymes per strain: 5.9
- Gram stain coverage: ~40%
- 16S sequence coverage: ~35%
- Type strain data: More complete than regular strains

## Question Opportunities by Category

### Precision
- "What is the BacDive ID for Campylobacter pinnipediorum isolated from California sea lion?"
- "What is the NCBI Taxonomy ID for Nonomuraea rhodomycinica strain 140579?"
- "What is the 16S rRNA sequence accession (ENA) for Mycobacterium insubricum strain 8559?"
- "What is the DSM culture collection number for [specific strain]?"
- "What are the exact geographic coordinates (latitude/longitude) where Thermodesulfatator atlanticus was isolated?"

### Completeness
- "How many Escherichia coli strains are in BacDive?"
- "List all positive enzyme activities for Bacillus subtilis strain 137036"
- "How many bacterial strains in BacDive have complete 16S rRNA sequences?"
- "How many strains are from thermophilic bacteria?"
- "Count strains with Gram-negative phenotype"

### Integration
- "Find the NCBI Taxonomy ID for BacDive strain 134430 (E. coli)"
- "Convert BacDive strain ID to DSMZ culture collection number"
- "Find MediaDive recipe link for culture medium used with [specific strain]"
- "Link 16S sequence accession to NCBI Nucleotide database"

### Currency
- "What are the most recently added bacterial strains (2024) in BacDive?"
- "Find newly characterized thermophilic strains from marine environments"
- "What new enzyme activities have been characterized in 2024?"

### Specificity
- "What are the growth temperature and pH ranges for the thermophilic archaeon Thermodesulfatator atlanticus?"
- "What enzyme activities are positive for the rare bacterium Terribacillus saccharophilus?"
- "What is the isolation source and geographic location of Mycoplasmopsis ciconiae?"
- "Find all strains of Nonomuraea rhodomycinica with complete phenotypic profiles"

### Structured Query
- "Find all Gram-positive bacteria with gelatinase activity isolated from soil"
- "Retrieve all thermophilic strains (containing 'thermophilic' in description) with temperature range > 45°C and their Gram stain properties"
- "Find all strains from Japan with 16S rRNA sequences and culture collection numbers"
- "Query strains with positive catalase AND amylase activities from genus Bacillus"
- "Find marine bacterial strains (from locations with latitude < 30°) with complete genome sequences"

## Notes

### Limitations and Challenges
- **Incomplete phenotype coverage**: Only ~40% have Gram stain, ~35% have 16S sequences
- **OPTIONAL clauses essential**: Must use OPTIONAL for all phenotypes to avoid excluding strains
- **Mixed sequence types**: 16SSequence entities contain both actual 16S rRNA (~1900 bp) and complete genomes (millions of bp)
- **Variable ?score reserved**: Cannot use `?score` as variable name with `bif:contains`, must use `?sc` or similar
- **Query timeouts possible**: Always use LIMIT, especially with multi-join phenotype queries

### Best Practices for Querying
1. **Full-text search**: Use `bif:contains` as triple pattern, not in FILTER
2. **Syntax**: Keywords in single quotes: `'keyword'`, boolean: `'word1' AND 'word2'`
3. **Relevance scoring**: Use `option (score ?sc)` and `ORDER BY DESC(?sc)` for best results
4. **Phenotypes**: Always use OPTIONAL blocks for enzyme activities, Gram stain, motility, etc.
5. **Performance**: Start with genus/species filters or keyword search, then add phenotypes
6. **Sequences**: Filter by length to distinguish 16S RNA (<2000 bp) from genomes (>1M bp)
7. **LIMIT**: Always include LIMIT to prevent timeouts, especially for exploratory queries
