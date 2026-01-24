# MedGen (Medical Genetics) Exploration Report

## Database Overview
- **Purpose**: NCBI's portal for information about medical conditions with a genetic component
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: `http://rdfportal.org/dataset/medgen`
- **Key Features**: Clinical concepts (CUI identifiers), UMLS semantic types, cross-references to OMIM, MONDO, Orphanet, MeSH, SNOMED CT
- **Data Version**: Current NCBI release (monthly updates)

## Schema Analysis (from MIE file)
### Main Entities
- **mo:ConceptID**: Clinical concepts (233,939 total) with CUI identifiers
- **mo:MGREL**: Relationship records (1,130,420 total) connecting concepts
- **mo:MGSAT**: Attribute records storing additional properties
- **mo:MGCONSO**: Terminology mappings with external database cross-references
- **rdf:Statement**: Reification statements for relationship provenance

### Important Properties
- `dct:identifier`: UMLS CUI identifier (e.g., "C0010674" for cystic fibrosis)
- `rdfs:label`: Human-readable disease/condition name
- `mo:sty`: UMLS semantic type classification
- `skos:definition`: Textual definition (available for ~34% of concepts)
- `mo:mgconso/rdfs:seeAlso`: Cross-references to external databases
- `mo:rela`: Relationship type in MGREL entities

### Query Patterns
- **CRITICAL**: Relationships are in MGREL entities, NOT direct properties on ConceptID
- Use `dct:identifier` for exact CUI lookup (fast, indexed)
- Use `bif:contains` for keyword search (can be slow, use FILTER with CONTAINS instead)
- Always use DISTINCT when querying cross-references to avoid duplicates

## Search Queries Performed

### 1. Query: "Huntington disease" via NCBI esearch
```
Results: 19 entries found
- CUI 1835515: Chorea due to Huntington disease-like 1
- CUI 1835513: Chorea due to Huntington disease-like 2
- CUI 1835511: Chorea due to Huntington disease-like 3
- CUI 1676144: Huntington disease-like syndrome due to C9ORF72 expansions
Main entry: C0020179 (confirmed via SPARQL)
```

### 2. Query: "Fabry disease" via NCBI esearch
```
Results: 14 entries found
- CUI 82621: Autonomic neuropathy (related)
- CUI 324539: Alpha-N-acetylgalactosaminidase deficiency type 2 (related - Fabry-like)
Related main entry exists with phenotype connections
```

### 3. Query: "cystic fibrosis" via NCBI esearch + SPARQL
```
Results: 78 entries found
Main entry: C0010674 (Cystic fibrosis)
Definition: Multisystem disease affecting respiratory tract, pancreas, intestine
Associated genes: CFTR (gene_id 1080), TGFB1, FCGR2A
Inheritance: Autosomal recessive
OMIM: 219700
```

### 4. Huntington disease cross-references via SPARQL
```
Query: Get external cross-references for C0020179
Results: 
- MONDO:0007739
- MeSH:D006816
- NCI:C82342
- OMIM:143100, 613004
- Orphanet:399
- SNOMED CT:58756001
```

### 5. Cystic fibrosis relationships via MGREL
```
Query: Get related concepts for C0010674
Results: 30+ phenotypic manifestations including:
- Bronchiectasis, Asthma, Hemoptysis (respiratory)
- Hepatomegaly, Biliary cirrhosis, Rectal prolapse (GI)
- Male infertility, Hypercalciuria (urogenital)
- Meconium ileus, Dehydration, Cor pulmonale
```

## SPARQL Queries Tested

### Query 1: Count total clinical concepts
```sparql
SELECT (COUNT(DISTINCT ?concept) as ?total)
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID .
}
# Results: 233,939 concepts
```

### Query 2: Distribution by UMLS semantic type
```sparql
SELECT ?stype (COUNT(DISTINCT ?concept) as ?count)
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
           mo:sty ?stype .
}
GROUP BY ?stype ORDER BY DESC(?count) LIMIT 20
# Results:
# T033 (Finding): 106,477 - largest category
# T047 (Disease/Syndrome): 64,364
# T191 (Neoplastic Process): 26,706
# T046 (Pathologic Function): 9,654
# T019 (Congenital Abnormality): 7,723
```

### Query 3: Find concept by CUI identifier
```sparql
SELECT ?concept ?identifier ?label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
           dct:identifier "C0020179" ;
           rdfs:label ?label .
  BIND("C0020179" as ?identifier)
}
# Results: Huntington disease (http://www.ncbi.nlm.nih.gov/medgen/C0020179)
```

### Query 4: Get cross-references for a disease
```sparql
SELECT DISTINCT ?external_db
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
           dct:identifier "C0020179" ;
           mo:mgconso ?bn .
  ?bn rdfs:seeAlso ?external_db .
}
# Results: MONDO, MeSH, NCI, OMIM, Orphanet, SNOMED CT mappings
```

### Query 5: Find disease manifestations via MGREL
```sparql
SELECT ?disease_label ?related_label ?rel_type
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?rel a mo:MGREL ;
       mo:cui1 <http://www.ncbi.nlm.nih.gov/medgen/C0010674> ;
       mo:cui2 ?cui2 ;
       mo:rela ?rel_type .
  <http://www.ncbi.nlm.nih.gov/medgen/C0010674> rdfs:label ?disease_label .
  ?cui2 rdfs:label ?related_label .
}
LIMIT 30
# Results: Cystic fibrosis → multiple manifestations (bronchiectasis, asthma, etc.)
```

### Query 6: Count relationship types
```sparql
SELECT ?relType (COUNT(?rel) as ?count)
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?rel a mo:MGREL ;
       mo:rela ?relType .
}
GROUP BY ?relType ORDER BY DESC(?count) LIMIT 20
# Results:
# has_manifestation / manifestation_of: 255,600 each
# isa / inverse_isa: 56,458 each
# disease_has_finding / is_finding_of_disease: 41,728 each
# has_inheritance_type: 13,040
```

## Cross-Reference Analysis

### Entity Counts (unique concepts with mappings)
| Database | Concepts with Mappings | Coverage |
|----------|------------------------|----------|
| MONDO | 22,846 | 9.8% |
| OMIM | 14,787 | 6.3% |
| MeSH | 9,997 | 4.3% |
| Orphanet | 9,026 | 3.9% |

### Definitions Coverage
- Concepts with definitions: 78,578 (33.6% of total)

### MGREL Relationship Statistics
| Relationship Type | Count | Description |
|-------------------|-------|-------------|
| has_manifestation / manifestation_of | 255,600 | Disease-phenotype links |
| isa / inverse_isa | 56,458 | Hierarchical classification |
| disease_has_finding | 41,728 | Clinical findings |
| has_inheritance_type | 13,040 | Genetic inheritance patterns |

## Interesting Findings

**Focus on discoveries requiring actual database queries:**

1. **Semantic type distribution**: "Finding" (T033) is the most common semantic type with 106,477 concepts, followed by "Disease or Syndrome" (T047) with 64,364 concepts. This reveals MedGen's emphasis on clinical findings for variant interpretation.

2. **Rich phenotype relationships**: Cystic fibrosis (C0010674) links to 30+ manifestations via MGREL including bronchiectasis, male infertility, meconium ileus - enabling genotype-phenotype correlation studies.

3. **Multi-database integration**: Huntington disease (C0020179) has 7 cross-references spanning disease ontologies (MONDO, Orphanet), clinical terminologies (SNOMED CT, MeSH), and genetic databases (OMIM).

4. **Relationship richness**: The database contains 1.13M relationship records. The "has_manifestation" relationship type alone accounts for 255,600 links, making MedGen valuable for clinical phenotype analysis.

5. **Inheritance pattern annotations**: 13,040 concepts have inheritance type relationships (autosomal dominant, recessive, X-linked, etc.) stored via MGREL, useful for genetic counseling.

6. **Gene-disease associations**: Concepts like cystic fibrosis include associated gene information (CFTR, TGFB1) with chromosomal locations, enabling variant-disease mapping.

## Question Opportunities by Category

### Precision
- "What is the MedGen CUI for Huntington disease?" → C0020179
- "What is the MedGen CUI for cystic fibrosis?" → C0010674
- "What OMIM ID corresponds to MedGen C0020179?" → 143100
- "What MONDO ID maps to MedGen C0010674?" → MONDO:0009061

### Completeness
- "How many clinical concepts are in MedGen?" → 233,939
- "How many MedGen concepts have OMIM cross-references?" → 14,787
- "How many MedGen concepts have MONDO cross-references?" → 22,846
- "How many MedGen concepts have Orphanet cross-references?" → 9,026
- "How many MedGen concepts have textual definitions?" → 78,578
- "How many relationships are in MedGen?" → 1,130,420
- "How many disease-manifestation relationships exist in MedGen?" → 255,600

### Integration
- "Find the MeSH descriptor ID for MedGen concept C0020179" → D006816
- "What Orphanet ID corresponds to Huntington disease in MedGen?" → Orphanet:399
- "Cross-link MedGen to ClinVar for diabetes-related variants" (cross-database)

### Specificity
- "What is the CUI for alpha-N-acetylgalactosaminidase deficiency type 2?" → C1836522
- "What manifestations are associated with cystic fibrosis in MedGen?" → 30+ phenotypes
- "What is the inheritance pattern for Huntington disease in MedGen?" → Autosomal dominant

### Structured Query
- "Find all phenotypic manifestations of cystic fibrosis" → MGREL query
- "Count concepts by UMLS semantic type" → T033: 106,477, T047: 64,364, T191: 26,706
- "Find diseases with both OMIM and Orphanet cross-references"
- "Get inheritance type distribution for genetic diseases"

## Notes
- **CRITICAL**: Relationships are stored in MGREL entities, NOT as direct properties on ConceptID
- **Search strategy**: Use NCBI esearch for keyword discovery, then SPARQL for detailed data
- **Performance**: CUI lookups via dct:identifier are fast; keyword search can be slow
- **Duplicates**: Always use DISTINCT when querying cross-references via mo:mgconso/rdfs:seeAlso
- **Shared endpoint**: Part of "ncbi" endpoint with clinvar, pubmed, pubtator, ncbigene
- **Semantic types**: Use STY URIs (e.g., sty:T047 for Disease/Syndrome)
- **Definition coverage**: Only ~34% of concepts have skos:definition
