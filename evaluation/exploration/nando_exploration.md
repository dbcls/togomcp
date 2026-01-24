# NANDO (Nanbyo Data) Exploration Report

## Database Overview
- **Purpose**: Comprehensive ontology for Japanese intractable (rare) diseases maintained by Japanese government
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Key Features**: Multilingual labels (EN/JA/JA-Hira), government notification numbers, MONDO mappings
- **Data Version**: Current release (quarterly updates)

## Schema Analysis (from MIE file)
### Main Entities
- **owl:Class**: Disease classes (2,777 total)
- Hierarchical taxonomy: Root → Disease Categories → Specific Diseases

### Important Properties
- `dct:identifier`: NANDO identifier (e.g., NANDO:1200157)
- `rdfs:label`: Multilingual labels (@en, @ja, @ja-hira)
- `skos:prefLabel`: Preferred Japanese name
- `nando:hasNotificationNumber`: Government designation number
- `skos:closeMatch`: MONDO cross-references
- `rdfs:seeAlso`: KEGG, government documents, patient resources
- `dct:description`: Japanese disease descriptions
- `dct:source`: Source documentation PDFs

### Query Patterns
- **CRITICAL**: Always use `FROM <http://nanbyodata.jp/ontology/nando>` clause
- Use `bif:contains` for keyword search with relevance scoring
- Language filtering: `FILTER(LANG(?label) = "en")` for English
- Hiragana detection: `FILTER(REGEX(STR(?label), "^[ぁ-ん]+$"))`

## Search Queries Performed

1. **Query: "Fabry disease"** → Results: 8 entries found
   - NANDO:1200157 - Fabry disease (notification #19)
   - NANDO:1200158 - Classical Fabry disease
   - NANDO:1200159 - Variant Fabry disease
   - NANDO:1200160 - Heterozygous Fabry disease
   - Plus duplicates in 22xxxxx range

2. **Query: "amyloidosis"** → Results: 5 entries found
   - NANDO:1200209 - Systemic amyloidosis
   - NANDO:1200210 - AL amyloidosis
   - NANDO:1200211 - Amyloid light-chain amyloidosis
   - NANDO:1200212 - Transthyretin-related amyloidosis
   - NANDO:1200213 - Reactive AA amyloidosis

3. **Query: "ALS"/"amyotrophic"** → Results: 1 entry found
   - NANDO:1200002 - Amyotrophic lateral sclerosis (notification #2)

4. **Query: Disease categories** → Results: 15 main categories
   - Neuromuscular disease, Metabolic disease, Skin and connective tissue disease
   - Immune system disease, Cardiovascular disease, Blood disease
   - Renal and urological disease, Bone and joint disease, Endocrine disease
   - Respiratory disease, Eye and visual system disease, Hearing and balance disorder
   - Gastrointestinal disease, Chromosome abnormality, Otorhinolaryngological disease

5. **Query: Diseases with KEGG links** → Results: 519 diseases have KEGG cross-references

## SPARQL Queries Tested

```sparql
# Query 1: Get Fabry disease details with MONDO mapping
SELECT ?identifier ?en_label ?ja_label ?mondo_id ?notif_num
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  nando:1200157 dct:identifier ?identifier ;
                rdfs:label ?en_label ;
                rdfs:label ?ja_label .
  OPTIONAL { nando:1200157 skos:closeMatch ?mondo_id . 
             FILTER(STRSTARTS(STR(?mondo_id), "http://purl.obolibrary.org/obo/MONDO_")) }
  OPTIONAL { nando:1200157 nando:hasNotificationNumber ?notif_num }
  FILTER(LANG(?en_label) = "en")
  FILTER(LANG(?ja_label) = "ja" && !REGEX(STR(?ja_label), "^[ぁ-ん]+$"))
}
# Results: NANDO:1200157, "Fabry disease", "ファブリー病", MONDO:0010526, notification #19
```

```sparql
# Query 2: Neuromuscular diseases with notification numbers (top 15)
SELECT ?disease ?identifier ?en_label ?notif_num
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  ?disease a owl:Class ;
           rdfs:subClassOf nando:1100001 ;
           dct:identifier ?identifier ;
           rdfs:label ?en_label ;
           nando:hasNotificationNumber ?notif_num .
  FILTER(LANG(?en_label) = "en")
}
ORDER BY xsd:integer(?notif_num)
LIMIT 15
# Results: SBMA (#1), ALS (#2), SMA (#3), PLS (#4), PSP (#5), Parkinson's (#6), etc.
```

```sparql
# Query 3: Distribution of MONDO mapping counts per disease
SELECT ?mapping_count (COUNT(?disease) as ?disease_count)
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  { SELECT ?disease (COUNT(?mondo) as ?mapping_count)
    WHERE { 
      ?disease a owl:Class ;
               skos:closeMatch ?mondo .
      FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))
    }
    GROUP BY ?disease
  }
}
GROUP BY ?mapping_count
ORDER BY ?mapping_count
# Results: 1976 with 1 mapping, 157 with 2 mappings, 17 with 3 mappings
```

## Cross-Reference Analysis

### MONDO Mappings (skos:closeMatch)
**Entity count** (unique diseases with mappings): **2,150 diseases**
**Relationship count** (total mappings): **2,341 mappings**

**Distribution**:
- 1,976 diseases with 1 MONDO mapping
- 157 diseases with 2 MONDO mappings
- 17 diseases with 3 MONDO mappings

### External Links (rdfs:seeAlso)
- **KEGG Disease links**: 519 diseases
- **Government documents**: .docx files from mhlw.go.jp
- **Patient resources**: nanbyou.or.jp PDFs

### Source Documentation (dct:source)
- Approximately 2,397 diseases have source PDFs

## Interesting Findings

**Non-trivial discoveries from actual queries:**

1. **Notification number system**: Government-designated intractable diseases have official notification numbers (1-338+). Notification #1 is SBMA, #2 is ALS, #6 is Parkinson's disease. 2,454 diseases have notification numbers.

2. **Multilingual support**: Each disease has up to 3 Japanese labels:
   - @en: English name
   - @ja: Japanese kanji
   - @ja-hira: Japanese hiragana reading

3. **Disease hierarchy**: 15 disease categories under "Designated intractable disease" (NANDO:1000001), with specific diseases underneath. Neuromuscular disease is the largest category.

4. **One-to-many MONDO mappings**: 174 diseases map to multiple MONDO IDs (157 with 2, 17 with 3). Examples:
   - NANDO:1200030 (CIDP) → 3 MONDO mappings
   - NANDO:1200688 (22q11.2 deletion syndrome) → 3 MONDO mappings

5. **Japanese descriptions**: 1,211 diseases (44%) have detailed Japanese clinical descriptions covering symptoms, progression, and diagnostic criteria.

6. **Specific disease findings**:
   - Fabry disease (NANDO:1200157) has notification #19 and maps to MONDO:0010526
   - ALS (NANDO:1200002) has notification #2
   - 519 diseases have KEGG Disease cross-references for pathway context

## Question Opportunities by Category

### Precision Questions
- "What is the NANDO ID for Fabry disease?" → NANDO:1200157
- "What is the notification number for ALS in NANDO?" → 2
- "Which MONDO ID does NANDO:1200010 (Parkinson's disease) map to?" → MONDO:0005180

### Completeness Questions
- "How many diseases in NANDO are designated intractable diseases?" → 2,454
- "How many NANDO diseases have MONDO mappings?" → 2,150
- "How many diseases have KEGG Disease cross-references?" → 519
- "How many NANDO diseases have Japanese descriptions?" → 1,211

### Integration Questions
- "Find the MONDO ID for Huntington's disease in NANDO" (requires NANDO search + cross-ref lookup)
- "Which NANDO diseases in the neuromuscular category have KEGG links?" (requires category + cross-ref)
- NANDO → MONDO → UniProt pathway queries possible via shared endpoint

### Specificity Questions
- "What rare diseases are classified under metabolic disorders in NANDO?"
- "Find NANDO diseases related to amyloidosis"
- "Which diseases have multiple MONDO mappings?" (174 diseases)

### Structured Query Questions
- "Count diseases by category in NANDO"
- "Find diseases with notification numbers between 1-20"
- "List diseases with both MONDO and KEGG mappings"

## Notes
- Shares "primary" endpoint with mesh, go, taxonomy, mondo, bacdive, mediadive
- Cross-database queries possible via keyword matching (no direct semantic links to MeSH/GO)
- Dual ID numbering: 12xxxxx for specific diseases, 22xxxxx appears to be variants/duplicates
- Some diseases appear twice with different IDs (e.g., Fabry disease at 1200157 and 2200563)
- Notification numbers are unique government designations for support eligibility
- Japanese descriptions are rich but require Japanese language understanding for full value
