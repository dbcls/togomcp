# NANDO (Nanbyo Data) Exploration Report

## Database Overview
- **Purpose**: Comprehensive ontology for Japanese intractable (rare) diseases maintained by the Japanese government
- **Scope**: 2,777 disease classes organized in hierarchical taxonomy
- **Focus**: Designated intractable diseases eligible for government healthcare support
- **Key features**: Multilingual labels (English, Japanese kanji, hiragana), notification numbers, cross-references to MONDO and KEGG

## Schema Analysis (from MIE file)

### Main Properties Available
- `dct:identifier`: NANDO ID (e.g., "NANDO:1200010")
- `rdfs:label`: Disease names in multiple languages (@en, @ja, @ja-hira)
- `skos:prefLabel`: Preferred Japanese label
- `skos:altLabel`: Alternative names/synonyms
- `nando:hasNotificationNumber`: Government notification number
- `dct:description`: Disease descriptions (mainly Japanese)
- `rdfs:subClassOf`: Hierarchical parent-child relationships
- `skos:closeMatch`: MONDO ontology mappings
- `rdfs:seeAlso`: External resources (KEGG, government docs)
- `dct:source`: Source documentation

### Important Relationships
- Hierarchical taxonomy: Intractable disease → Disease categories → Specific diseases
- MONDO mappings via `skos:closeMatch` (84% coverage)
- KEGG Disease links via `rdfs:seeAlso`
- Government documentation via `dct:source` and `rdfs:seeAlso`

### Query Patterns Observed
- Disease category IDs: NANDO:11xxxxx
- Specific disease IDs: NANDO:12xxxxx and NANDO:22xxxxx
- Root class: NANDO:0000001

## Search Queries Performed

### Query 1: Parkinson-related diseases
- **Search**: `bif:contains "'Parkinson*'"`
- **Results**: 3 diseases found
  - NANDO:1200010 - Parkinson's disease (notification #6)
  - NANDO:1200524 - Rapid-onset dystonia-parkinsonism
  - NANDO:1200036 - Multiple system atrophy, Parkinsonian type

### Query 2: Fabry disease variants
- **Search**: `bif:contains "'Fabry*'"`
- **Results**: 8 entries covering:
  - NANDO:1200157/2200563 - Fabry disease
  - NANDO:1200158/2201213 - Classical Fabry disease
  - NANDO:1200159/2201214 - Variant Fabry disease
  - NANDO:1200160/2201215 - Heterozygous Fabry disease

### Query 3: Diseases by notification number
- **Search**: Ordered by `nando:hasNotificationNumber`
- **Results**: Notification #1 includes:
  - NANDO:1200001 - Spinal and bulbar muscular atrophy
  - NANDO:2200079 - Malignant thymoma
  - NANDO:2200138 - Amyloid nephropathy
  - NANDO:2200960 - Angelman syndrome
  - NANDO:2201034 - Hereditary hemorrhagic telangiectasia

### Query 4: MONDO cross-references
- **Search**: `skos:closeMatch` with MONDO filter
- **Results**: Strong coverage of major disease categories
  - Metabolic disease → MONDO:0004955, MONDO:0005066
  - ALS → MONDO:0004976
  - SMA types I-IV → specific MONDO IDs

### Query 5: Disease categories
- **Search**: Direct children of root category
- **Results**: 15+ major categories including:
  - Neuromuscular disease (NANDO:1100001)
  - Metabolic disease (NANDO:1100002)
  - Immune system disease (NANDO:1100004)
  - Cardiovascular disease (NANDO:1100005)

## SPARQL Queries Tested

```sparql
# Query 1: Find diseases with English labels and identifiers
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?disease ?label ?identifier
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           rdfs:label ?label ;
           dct:identifier ?identifier .
  ?label bif:contains "'Parkinson*'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
# Results: Found Parkinson's disease (NANDO:1200010), Multiple system atrophy Parkinsonian type, Rapid-onset dystonia-parkinsonism
```

```sparql
# Query 2: Designated diseases with notification numbers
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX nando: <http://nanbyodata.jp/ontology/NANDO_>

SELECT ?disease ?en_label ?notif_num ?identifier
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           dct:identifier ?identifier ;
           nando:hasNotificationNumber ?notif_num ;
           rdfs:label ?en_label .
  FILTER(LANG(?en_label) = "en")
}
ORDER BY xsd:integer(?notif_num)
LIMIT 30
# Results: 30 diseases ordered by notification number, starting with #1 (SBMA) through #2 (ALS)
```

```sparql
# Query 3: Diseases with MONDO mappings
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?disease ?en_label ?mondo_id
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           rdfs:label ?en_label ;
           skos:closeMatch ?mondo_id .
  FILTER(STRSTARTS(STR(?mondo_id), "http://purl.obolibrary.org/obo/MONDO_"))
  FILTER(LANG(?en_label) = "en")
}
LIMIT 20
# Results: Strong MONDO mapping coverage - disease categories and specific diseases linked
```

```sparql
# Query 4: Total disease count
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT (COUNT(DISTINCT ?disease) AS ?total_diseases)
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class .
}
# Results: 2,777 total disease classes
```

## Interesting Findings

### Specific Entities for Good Questions
1. **Parkinson's disease**: NANDO:1200010 (notification #6, has MONDO mapping)
2. **Spinal and bulbar muscular atrophy (Kennedy disease)**: NANDO:1200001 (notification #1)
3. **Amyotrophic lateral sclerosis**: NANDO:1200002 (notification #2)
4. **Fabry disease**: NANDO:1200157 (metabolic/lysosomal storage disorder)
5. **Angelman syndrome**: NANDO:2200960 (chromosome abnormality)
6. **Hereditary hemorrhagic telangiectasia**: NANDO:2201034

### Unique Properties/Patterns
- Japanese government notification numbers are unique to this database
- Trilingual labels: English, Japanese kanji, Japanese hiragana
- Some diseases have multiple NANDO IDs (12xxxxx and 22xxxxx series)
- 84% of diseases have MONDO mappings (2,341/2,777)

### Connections to Other Databases
- **MONDO**: ~2,341 diseases mapped via `skos:closeMatch`
- **KEGG Disease**: ~500 diseases linked via `rdfs:seeAlso`
- **Government docs**: Ministry of Health documents (.docx)
- **Nanbyou.or.jp**: Patient information PDFs

### Verifiable Facts
- Total diseases: 2,777
- Diseases with notification numbers: ~2,454 (88%)
- Diseases with MONDO mappings: ~2,341 (84%)
- Diseases with descriptions: ~44%
- Disease categories under root: 15+

## Question Opportunities by Category

### Precision
- "What is the NANDO identifier for Parkinson's disease?" → NANDO:1200010
- "What is the notification number for spinal and bulbar muscular atrophy in NANDO?" → 1
- "What is the NANDO identifier for Fabry disease?" → NANDO:1200157

### Completeness
- "How many rare disease classes are in the NANDO ontology?" → 2,777
- "How many NANDO diseases have MONDO ontology mappings?" → ~2,341
- "List all subtypes of Fabry disease in NANDO" → Classical, Variant, Heterozygous variants

### Integration
- "What MONDO ID is mapped to NANDO Parkinson's disease (NANDO:1200010)?" → MONDO:0005180
- "What is the NANDO ID for the disease with MONDO ID MONDO:0004976?" → NANDO:1200002 (ALS)
- "Link NANDO Fabry disease to its MONDO equivalent"

### Currency
- "What rare diseases in NANDO have been designated by the Japanese government?" (tests current designations)

### Specificity
- "What is the Japanese kanji label for Parkinson's disease in NANDO?" → パーキンソン病
- "Which NANDO disease has notification number 6?" → Parkinson's disease
- "Find the NANDO identifier for Kennedy disease (SBMA)" → NANDO:1200001

### Structured Query
- "Find all neuromuscular diseases in NANDO with MONDO mappings"
- "List NANDO diseases in the chromosome abnormality category"
- "Which NANDO diseases have both KEGG links and MONDO mappings?"

## Notes

### Limitations
- OLS4:searchClasses returns results from many ontologies, not just NANDO
- Direct SPARQL queries on NANDO graph are most reliable
- Some hiragana labels require regex pattern filtering

### Best Practices
- Always include `FROM <http://nanbyodata.jp/ontology/nando>` in SPARQL
- Use `bif:contains` for keyword searches (much faster than REGEX)
- Filter by language tag: `FILTER(LANG(?label) = "en")` for English
- For kanji: `FILTER(LANG(?label) = "ja" && !REGEX(STR(?label), "^[ぁ-ん]+$"))`
- For hiragana: `FILTER(REGEX(STR(?label), "^[ぁ-ん]+$"))`

### Data Quality
- 100% identifier coverage
- 100% multilingual label coverage
- 88% notification number coverage
- 84% MONDO mapping coverage
- 44% description coverage
