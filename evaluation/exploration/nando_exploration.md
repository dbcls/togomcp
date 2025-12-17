# NANDO (Nanbyo Data) Exploration Report

## Database Overview
- **Purpose**: Comprehensive ontology for Japanese intractable (rare) diseases maintained by the Japanese government
- **Scope**: 2,777 disease classes organized in hierarchical taxonomy, primarily focusing on designated intractable diseases eligible for government support
- **Key Data Types**:
  - Disease classes with multilingual labels (English, Japanese kanji, hiragana)
  - Notification numbers for designated intractable diseases
  - Disease descriptions and diagnostic criteria
  - Hierarchical disease classification
  - Cross-references to international disease ontologies
- **Main Entities**:
  - 2,777 total disease classes
  - 2,454 designated diseases with notification numbers (88%)
  - 2,341 diseases with MONDO mappings (84%)
  - ~500 diseases with KEGG Disease links
  - 15 major disease categories

## Schema Analysis (from MIE file)

### Main Properties Available
1. **Disease Identification**:
   - `dct:identifier` - NANDO ID (NANDO:xxxxxxx format, 100% coverage)
   - `rdfs:label` - Multilingual labels (@en, @ja, @ja-hira)
   - `skos:prefLabel` - Preferred Japanese label
   - `skos:altLabel` - Alternative names and acronyms
   - `nando:hasNotificationNumber` - Government designation number (88% coverage)

2. **Disease Description**:
   - `dct:description` - Japanese medical description (~44% coverage)
   - `owl:Class` - OWL ontology class type
   - `owl:deprecated` - Deprecated disease marker (9 deprecated classes)

3. **Disease Classification**:
   - `rdfs:subClassOf` - Hierarchical parent-child relationships
   - NANDO ID patterns:
     - 0000001: Root class (Intractable disease)
     - 1000001: Top designated disease level
     - 11xxxxx: Disease categories (15 categories)
     - 12xxxxx: Specific designated diseases
     - 22xxxxx: Additional disease subtypes

4. **Cross-References**:
   - `skos:closeMatch` - MONDO Disease Ontology mappings (~84% coverage)
   - `rdfs:seeAlso` - External resources (KEGG, government docs, patient info)
   - `dct:source` - Source documentation (PDFs, ~86% coverage)
   - Total: 6,120 external references

5. **Language Support**:
   - `@en` - English labels (100% coverage)
   - `@ja` - Japanese kanji labels (100% coverage)
   - `@ja-hira` - Japanese hiragana pronunciation labels (variable coverage)
   - Average 3.0 labels per disease

### Important Relationships
- **Hierarchical taxonomy**: owl:Thing → Intractable disease (NANDO:0000001) → Designated intractable disease (NANDO:1000001) → Disease categories (11xxxxx) → Specific diseases (12xxxxx)
- **International alignment**: skos:closeMatch links to MONDO (2,341 mappings)
- **Molecular context**: rdfs:seeAlso links to KEGG Disease (~500 links)
- **Official documentation**: dct:source and rdfs:seeAlso to Japanese government resources
- **Some diseases have multiple MONDO mappings** (one-to-many relationships for disease variants)

### Query Patterns Observed
1. **bif:contains for keyword search**: Full-text search with relevance scoring
2. **Language filtering**: FILTER(LANG(?label) = "en") for English, "ja" for Japanese
3. **Hiragana identification**: FILTER(REGEX(STR(?label), "^[ぁ-ん]+$"))
4. **MONDO URI filtering**: FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))
5. **Direct parent-child**: Use rdfs:subClassOf (not rdfs:subClassOf+) for better performance

### Critical Performance Notes
- **Use bif:contains** for keyword searches (10-100x faster than REGEX)
- **Always filter by language**: Prevents duplicate rows from multilingual labels
- **Use STRSTARTS** for URI filtering before joins
- **Avoid unlimited rdfs:subClassOf+**: Use direct parent-child or add LIMIT
- **FROM clause recommended**: FROM <http://nanbyodata.jp/ontology/nando>

## Search Queries Performed

### Query 1: Parkinson's Disease Search
**Query**: Keyword search for Parkinson-related diseases
```sparql
SELECT ?disease ?label ?identifier
WHERE {
  ?disease a owl:Class ; rdfs:label ?label ; dct:identifier ?identifier .
  ?label bif:contains "'Parkinson*'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
```
**Results**: Found 3 Parkinson-related diseases:
- Parkinson's disease (NANDO:1200010)
- Rapid-onset dystonia-parkinsonism (NANDO:1200524)
- Multiple system atrophy, Parkinsonian type (NANDO:1200036)
- Demonstrates full-text search with relevance ranking

### Query 2: Disease Category Listing
**Query**: Retrieve top-level disease categories with bilingual labels
```sparql
SELECT ?category ?en_label ?ja_label
WHERE {
  ?category a owl:Class ; rdfs:subClassOf nando:1000001 ;
            rdfs:label ?en_label ; rdfs:label ?ja_label .
  FILTER(LANG(?en_label) = "en")
  FILTER(LANG(?ja_label) = "ja" && !REGEX(STR(?ja_label), "^[ぁ-ん]+$"))
}
LIMIT 20
```
**Results**: Retrieved 15 major disease categories:
- Neuromuscular disease (神経・筋疾患)
- Metabolic disease (代謝系疾患)
- Immune system disease (免疫系疾患)
- Cardiovascular disease (循環器系疾患)
- Blood disease (血液系疾患)
- Respiratory disease (呼吸器系疾患)
- Gastrointestinal disease (消化器系疾患)
- Chromosome abnormality (染色体または遺伝子に変化を伴う症候群)
- Plus 7 more categories

### Query 3: MONDO Cross-References
**Query**: Diseases mapped to MONDO Disease Ontology
```sparql
SELECT ?disease ?label ?mondo_id
WHERE {
  ?disease a owl:Class ; rdfs:label ?label ; skos:closeMatch ?mondo_id .
  FILTER(STRSTARTS(STR(?mondo_id), "http://purl.obolibrary.org/obo/MONDO_"))
  FILTER(LANG(?label) = "en")
}
LIMIT 20
```
**Results**: Retrieved 20 disease-MONDO mappings:
- Neuromuscular disease → MONDO_0019056
- Metabolic disease → MONDO_0004955, MONDO_0005066 (2 mappings)
- Spinal and bulbar muscular atrophy → MONDO_0010735, MONDO_0016113 (2 mappings)
- Amyotrophic lateral sclerosis → MONDO_0004976
- Shows both category and specific disease mappings
- Demonstrates one-to-many relationships possible

### Query 4: Designated Intractable Diseases
**Query**: Government-designated diseases with notification numbers
```sparql
SELECT ?disease ?identifier ?prefLabel ?en_label ?notif_num
WHERE {
  ?disease a owl:Class ; dct:identifier ?identifier ;
           skos:prefLabel ?prefLabel ; nando:hasNotificationNumber ?notif_num .
  OPTIONAL {
    ?disease rdfs:label ?en_label .
    FILTER(LANG(?en_label) = "en")
  }
}
ORDER BY xsd:integer(?notif_num)
LIMIT 15
```
**Results**: Retrieved 15 designated diseases (all with notification number "1"):
- Spinal and bulbar muscular atrophy (球脊髄性筋萎縮症)
- Malignant thymoma (悪性胸腺腫)
- Amyloid nephropathy (アミロイド腎)
- Type 1 diabetes (1型糖尿病)
- Ulcerative colitis (潰瘍性大腸炎)
- Angelman syndrome (アンジェルマン症候群)
- Plus 9 more diseases

### Query 5: Disease Hierarchy - Neuromuscular Diseases
**Query**: Parent-child relationships under neuromuscular category
```sparql
SELECT ?parent ?parent_label ?child ?child_label
WHERE {
  ?child rdfs:subClassOf ?parent ; rdfs:label ?child_label ; a owl:Class .
  ?parent rdfs:label ?parent_label ; a owl:Class .
  FILTER(LANG(?child_label) = "en" && LANG(?parent_label) = "en")
  FILTER(?parent = nando:1100001)
}
ORDER BY ?child_label
LIMIT 15
```
**Results**: Found 15 neuromuscular diseases including:
- Acute encephalitis with refractory, repetitive partial seizures
- Aicardi syndrome
- Alexander disease
- Amyotrophic lateral sclerosis (ALS)
- Angelman syndrome
- Charcot-Marie-Tooth disease
- Huntington's disease would be in full result set
- Demonstrates hierarchical organization

### Query 6: Multilingual Labels with KEGG Links
**Query**: Comprehensive disease information with all labels and cross-references
```sparql
SELECT ?disease ?identifier ?en_label ?ja_label ?ja_hira ?kegg ?mondo
WHERE {
  ?disease a owl:Class ; rdfs:subClassOf+ nando:1100001 ;
           dct:identifier ?identifier ; rdfs:label ?en_label ; rdfs:label ?ja_label ;
           rdfs:seeAlso ?kegg .
  OPTIONAL {
    ?disease rdfs:label ?ja_hira .
    FILTER(REGEX(STR(?ja_hira), "^[ぁ-ん]+$"))
  }
  OPTIONAL {
    ?disease skos:closeMatch ?mondo .
    FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))
  }
  FILTER(LANG(?en_label) = "en")
  FILTER(LANG(?ja_label) = "ja" && !REGEX(STR(?ja_label), "^[ぁ-ん]+$"))
  FILTER(CONTAINS(STR(?kegg), "kegg.jp"))
}
LIMIT 10
```
**Results**: Retrieved 10 neuromuscular diseases with full metadata:
- Spinal muscular atrophy (脊髄性筋萎縮症) → KEGG H00455, MONDO_0001516
- Progressive supranuclear palsy (進行性核上性麻痺) → KEGG H00077, MONDO_0019037
- Parkinson's disease (パーキンソン病) → KEGG H00057, MONDO_0005180
- Huntington's disease (ハンチントン病) → KEGG H00059, MONDO_0007739
- Myasthenia gravis (重症筋無力症) → KEGG H01594, MONDO_0009688
- Multiple sclerosis (多発性硬化症) → KEGG H01490, MONDO_0005301
- Shows rich multilingual and cross-database integration

### Query 7: Disease Count by Category
**Query**: Statistical aggregation of diseases per category
```sparql
SELECT ?category ?category_label (COUNT(DISTINCT ?disease) as ?disease_count)
WHERE {
  ?category a owl:Class ; rdfs:subClassOf nando:1000001 ; rdfs:label ?category_label .
  ?disease rdfs:subClassOf ?category ; a owl:Class .
  FILTER(LANG(?category_label) = "en")
}
GROUP BY ?category ?category_label
ORDER BY DESC(?disease_count)
```
**Results**: Disease distribution across 15 categories:
- Neuromuscular disease: 84 diseases (largest)
- Metabolic disease: 45 diseases
- Chromosome abnormality: 42 diseases
- Immune system disease: 27 diseases
- Cardiovascular disease: 21 diseases
- Gastrointestinal disease: 21 diseases
- Endocrine disease: 16 diseases
- Skin and connective tissue disease: 15 diseases
- Renal and urological disease: 14 diseases
- Respiratory disease: 14 diseases
- Blood disease: 13 diseases
- Bone and joint disease: 13 diseases
- Eye and visual system disease: 8 diseases
- Otorhinolaryngological disease: 4 diseases
- Hearing and balance disorder: 1 disease

## SPARQL Queries Tested

```sparql
# Query 1: Keyword Search - Parkinson's Disease
# Purpose: Find diseases using full-text search with relevance ranking
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
LIMIT 10

# Results: Found 3 Parkinson-related diseases
# Key finding: bif:contains provides relevance ranking, much faster than REGEX
# Verification: NANDO:1200010 (Parkinson's disease), NANDO:1200524 (Rapid-onset dystonia-parkinsonism)
```

```sparql
# Query 2: Disease Categories - Bilingual Listing
# Purpose: Retrieve top-level disease categories with English and Japanese labels
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX nando: <http://nanbyodata.jp/ontology/NANDO_>

SELECT ?category ?en_label ?ja_label
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?category a owl:Class ;
            rdfs:subClassOf nando:1000001 ;
            rdfs:label ?en_label ;
            rdfs:label ?ja_label .
  FILTER(LANG(?en_label) = "en")
  FILTER(LANG(?ja_label) = "ja" && !REGEX(STR(?ja_label), "^[ぁ-ん]+$"))
}
ORDER BY ?en_label
LIMIT 20

# Results: Retrieved 15 major disease categories with bilingual labels
# Key finding: Language filtering essential to separate English/Japanese/hiragana
# Demonstrates: 100% multilingual coverage for all categories
```

```sparql
# Query 3: International Harmonization - MONDO Mappings
# Purpose: Find diseases mapped to MONDO Disease Ontology
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?disease ?label ?mondo_id
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           rdfs:label ?label ;
           skos:closeMatch ?mondo_id .
  FILTER(STRSTARTS(STR(?mondo_id), "http://purl.obolibrary.org/obo/MONDO_"))
  FILTER(LANG(?label) = "en")
}
LIMIT 20

# Results: Retrieved 20 disease-MONDO mappings
# Key finding: ~84% diseases have MONDO mappings (2,341/2,777)
# Note: Some diseases have multiple MONDO mappings (one-to-many relationships)
# Example: Metabolic disease → MONDO_0004955, MONDO_0005066
```

```sparql
# Query 4: Government-Designated Diseases
# Purpose: List diseases eligible for Japanese government support
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX nando: <http://nanbyodata.jp/ontology/NANDO_>

SELECT ?disease ?identifier ?prefLabel ?en_label ?notif_num
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           dct:identifier ?identifier ;
           skos:prefLabel ?prefLabel ;
           nando:hasNotificationNumber ?notif_num .
  OPTIONAL {
    ?disease rdfs:label ?en_label .
    FILTER(LANG(?en_label) = "en")
  }
}
ORDER BY xsd:integer(?notif_num)
LIMIT 15

# Results: Retrieved 15 designated diseases (notification number "1")
# Key finding: 88% diseases have notification numbers (2,454/2,777)
# Demonstrates: Official government designation system for patient support
```

```sparql
# Query 5: Disease Hierarchy Navigation
# Purpose: Explore parent-child relationships within disease categories
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX nando: <http://nanbyodata.jp/ontology/NANDO_>

SELECT ?parent ?parent_label ?child ?child_label
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?child rdfs:subClassOf ?parent ;
         rdfs:label ?child_label ;
         a owl:Class .
  ?parent rdfs:label ?parent_label ;
          a owl:Class .
  FILTER(LANG(?child_label) = "en" && LANG(?parent_label) = "en")
  FILTER(?parent = nando:1100001)
}
ORDER BY ?child_label
LIMIT 15

# Results: Found 15 neuromuscular diseases under Neuromuscular disease category
# Key finding: 84 total diseases in Neuromuscular disease category
# Demonstrates: Clear hierarchical organization for disease classification
```

## Interesting Findings

### 1. Specific Entities for Questions
- **NANDO:1200010**: Parkinson's disease (パーキンソン病) with MONDO and KEGG links
- **NANDO:1200001**: Spinal and bulbar muscular atrophy (notification #1)
- **NANDO:1100001**: Neuromuscular disease category (84 diseases)
- **NANDO:1100002**: Metabolic disease (2 MONDO mappings: MONDO_0004955, MONDO_0005066)
- **Root NANDO:0000001**: Intractable disease (top of hierarchy)

### 2. Unique Properties
- **Multilingual labels**: All diseases have English, Japanese kanji, many have hiragana
- **Government designation**: 88% have notification numbers for support eligibility
- **One-to-many mappings**: Some diseases map to multiple MONDO terms
- **Hierarchical ID pattern**: 0000001 (root) → 1000001 → 11xxxxx (categories) → 12xxxxx (diseases)
- **High MONDO coverage**: 84% diseases mapped to international ontology

### 3. Connections to Other Databases
- **MONDO**: 2,341 mappings (84% coverage) for international harmonization
- **KEGG Disease**: ~500 links to molecular pathways and genes
- **Japanese Government**: 2,397 source PDFs (86% coverage) with diagnostic criteria
- **Patient Information**: Nanbyou.or.jp patient resources
- **Clinical Databases**: Syndrome Finder clinical descriptions

### 4. Specific Verifiable Facts
- 2,777 total disease classes in NANDO
- 15 major disease categories
- Neuromuscular disease has most diseases (84)
- 88% diseases have notification numbers (2,454)
- 84% diseases have MONDO mappings (2,341)
- 9 deprecated disease classes
- Average 3.0 labels per disease (multilingual)
- 100% identifier and label coverage

## Question Opportunities by Category

### Precision
- "What is the NANDO identifier for Parkinson's disease?"
- "What is the notification number for Spinal and bulbar muscular atrophy (NANDO:1200001)?"
- "What is the MONDO ontology ID for Parkinson's disease in NANDO?"
- "How many diseases are in the Neuromuscular disease category?"

### Completeness
- "List all major disease categories in NANDO with their Japanese names"
- "How many designated intractable diseases have MONDO cross-references?"
- "What are all the Parkinson-related diseases in NANDO?"
- "List all diseases under the Metabolic disease category"

### Integration
- "What is the KEGG Disease ID for Parkinson's disease (NANDO:1200010)?"
- "Convert NANDO:1200001 to its corresponding MONDO identifier"
- "Find the Japanese government documentation (PDF) for Parkinson's disease"
- "What diseases have multiple MONDO mappings in NANDO?"

### Currency
- "What are the most recently designated intractable diseases?"
- "Which diseases have been deprecated (marked as owl:deprecated)?"
- "What new MONDO mappings have been added to NANDO?"

### Specificity
- "What is the hiragana pronunciation for the Japanese name of Huntington's disease?"
- "Find diseases with notification number 1 that are metabolic diseases"
- "What alternative names (skos:altLabel) exist for Parkinson's disease?"
- "Identify diseases in NANDO that have both KEGG and MONDO links"

### Structured Query
- "Find all neuromuscular diseases that have KEGG Disease links and MONDO mappings"
- "List diseases sorted by their notification numbers"
- "Count how many diseases in each category have MONDO cross-references"
- "Find all diseases whose English labels contain 'muscular' and have Japanese descriptions"

## Notes

### Database Characteristics
- **Government-maintained**: Official Japanese rare disease registry
- **Multilingual**: Complete English and Japanese coverage
- **Hierarchical**: Clear taxonomy from root to specific diseases
- **Well-connected**: High MONDO coverage (84%), KEGG links
- **Policy-focused**: Notification numbers for government support eligibility
- **International alignment**: Strong integration with global disease ontologies

### Limitations and Challenges
1. **Language complexity**: Need to filter hiragana from kanji (both use @ja tag)
2. **Variable hiragana coverage**: Not all diseases have pronunciation labels
3. **Description sparsity**: Only 44% have Japanese descriptions
4. **One-to-many MONDO**: Some diseases have multiple MONDO mappings
5. **Japanese-centric**: Documentation and descriptions primarily in Japanese

### Best Practices for Querying
1. **Use bif:contains for search**: 10-100x faster than REGEX
2. **Filter by language explicitly**: FILTER(LANG(?label) = "en") for English
3. **Separate kanji and hiragana**: Use REGEX pattern "^[ぁ-ん]+$" for hiragana
4. **Use STRSTARTS for URIs**: Filter MONDO URIs before joins
5. **Direct parent-child**: Use rdfs:subClassOf, not rdfs:subClassOf+
6. **Always add FROM clause**: FROM <http://nanbyodata.jp/ontology/nando>
7. **OPTIONAL for sparse properties**: Use OPTIONAL for descriptions, hiragana labels

### Data Quality Observations
- **Perfect ID coverage**: 100% diseases have dct:identifier
- **Complete multilingual labels**: 100% have English and Japanese labels
- **High notification coverage**: 88% have government designation numbers
- **Strong MONDO integration**: 84% have international mappings
- **Good documentation**: 86% have source PDFs
- **Minimal deprecation**: Only 9 deprecated classes
- **Average 3.0 labels**: English + kanji + hiragana (when available)

### Integration Opportunities
- **MONDO**: Via skos:closeMatch for international disease harmonization
- **KEGG**: Via rdfs:seeAlso for molecular pathways and genes
- **Japanese Government**: Via dct:source for official diagnostic criteria
- **Patient Resources**: Via rdfs:seeAlso to nanbyou.or.jp portals
- **Clinical Databases**: Via rdfs:seeAlso to Syndrome Finder
- **TogoID**: For systematic cross-database ID conversion

### Question Design Insights
- **Multilingual questions excellent**: All diseases have English and Japanese labels
- **Hierarchy questions powerful**: Clear category-disease relationships
- **MONDO integration questions**: 84% coverage enables international mapping
- **Government designation queries**: 88% have notification numbers
- **Keyword searches effective**: bif:contains with relevance ranking
- **Category distribution questions**: Rich statistics (84 neuromuscular, 45 metabolic, etc.)
- **Cross-reference questions**: Multiple databases (MONDO, KEGG, Government docs)

### Unique Value Propositions
1. **Japanese rare disease authority**: Official government-maintained ontology
2. **Multilingual support**: Complete English and Japanese coverage
3. **Policy integration**: Notification numbers link to government support programs
4. **International harmonization**: High MONDO coverage (84%) for global alignment
5. **Hierarchical classification**: Clear taxonomy for disease organization
6. **Official documentation**: 86% diseases have government source PDFs
7. **Patient-focused**: Links to Japanese patient information resources
8. **Molecular context**: KEGG Disease links for ~500 diseases
