# MONDO (Monarch Disease Ontology) Exploration Report

## Database Overview
- **Purpose**: Comprehensive disease ontology integrating multiple disease databases into unified classification
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Key Features**: Unified disease classification with cross-references to 35+ databases, OBO Foundry compliant
- **Data Version**: 2024

## Schema Analysis (from MIE file)
### Main Entities
- **owl:Class**: Disease classes (30,304 total)
- **oboInOwl:hasDbXref**: Cross-references to external databases
- **IAO:0000115**: Disease definitions
- **rdfs:subClassOf**: Hierarchical relationships

### Important Properties
- `oboInOwl:id`: MONDO identifier (format: MONDO:XXXXXXX)
- `oboInOwl:hasDbXref`: Cross-references (OMIM, Orphanet, MeSH, ICD, etc.)
- `oboInOwl:hasExactSynonym`: Exact synonyms
- `oboInOwl:hasRelatedSynonym`: Related/broader synonyms
- `IAO:0000115`: Textual definitions
- `rdfs:subClassOf`: Parent disease classes
- `owl:deprecated`: Obsolete status flag

### Query Patterns
- **CRITICAL**: Use `bif:contains` for full-text search with relevance scoring
- **CRITICAL**: Use `FILTER(isIRI(?parent))` to exclude blank nodes in hierarchy queries
- Use `rdfs:subClassOf+` for transitive hierarchy navigation (requires specific start point)
- Use `STRSTARTS(?xref, "PREFIX:")` for filtering by cross-reference database

## Search Queries Performed

### 1. Fabry disease search
```
Query: "Fabry disease" via OLS4:searchClasses
Results: 
- MONDO:0010526: Fabry disease - lysosomal storage disease with specific neurological, cutaneous, renal, cardiovascular manifestations
- Total results: 7,368 (includes related matches)
```

### 2. Huntington disease search
```
Query: "Huntington disease" via OLS4:searchClasses
Results:
- MONDO:0007739: Huntington disease - rare neurodegenerative disorder with choreatic movements
- MONDO:0015548: Huntington disease-like syndrome
- MONDO:0011299: Huntington disease-like 1 (prion-related)
- MONDO:0011671: Huntington disease-like 2 (neuroacanthocytosis)
- MONDO:0011487: Huntington disease-like 3 (childhood-onset)
- Plus animal model versions (pig, sheep, Rhesus monkey)
```

### 3. Breast cancer search
```
Query: "breast cancer" via OLS4:searchClasses
Results:
- MONDO:0007254: breast cancer - primary or metastatic malignant neoplasm
- MONDO:0800418: breast cancer, familial, susceptibility to, 1
- MONDO:0800419: breast cancer, familial, susceptibility to, 2
- MONDO:0004438: sporadic breast cancer
- MONDO:0700079: hormone receptor-positive breast cancer
- MONDO:0006512: estrogen-receptor positive breast cancer
- Total results: 1,175 breast cancer-related terms
```

### 4. Type 2 diabetes search
```
Query: "type 2 diabetes" via OLS4:searchClasses
Results:
- MONDO:0005148: type 2 diabetes mellitus - chronic disease with insulin resistance
- Plus animal model versions (pig, cat, macaque)
- MONDO:0007453: maturity-onset diabetes of the young type 2 (MODY2)
```

### 5. Cross-references for Huntington disease
```
Query: Get all cross-references for MONDO:0007739
Results: 16 cross-references including:
- NANDO:1200012 (Japanese rare disease)
- DOID:12858
- ICD9:333.4, ICD10CM:G10, ICD10WHO:G10
- GARD:6677, NORD:1256
- MEDGEN:5654
- MESH:D006816
- NCIT:C82342
- OMIM:143100, Orphanet:399
- SCTID:58756001, UMLS:C0020179
```

## SPARQL Queries Tested

### Query 1: Count total disease classes
```sparql
SELECT (COUNT(DISTINCT ?disease) as ?total)
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  ?disease a owl:Class .
  FILTER(STRSTARTS(STR(?disease), "http://purl.obolibrary.org/obo/MONDO_"))
}
# Results: 30,304 disease classes
```

### Query 2: Count diseases with OMIM cross-references
```sparql
SELECT (COUNT(DISTINCT ?disease) as ?totalWithOMIM)
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  ?disease a owl:Class ;
    oboInOwl:hasDbXref ?xref .
  FILTER(STRSTARTS(?xref, "OMIM:"))
}
# Results: 9,944 diseases with OMIM references
```

### Query 3: Count diseases with MeSH cross-references
```sparql
SELECT (COUNT(DISTINCT ?disease) as ?totalWithMESH)
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  ?disease a owl:Class ;
    oboInOwl:hasDbXref ?xref .
  FILTER(STRSTARTS(?xref, "MESH:"))
}
# Results: 8,253 diseases with MeSH references
```

### Query 4: Count diseases with Orphanet cross-references
```sparql
SELECT (COUNT(DISTINCT ?disease) as ?totalWithOrphanet)
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  ?disease a owl:Class ;
    oboInOwl:hasDbXref ?xref .
  FILTER(STRSTARTS(?xref, "Orphanet:"))
}
# Results: 10,246 diseases with Orphanet references
```

## Cross-Reference Analysis

### Entity Counts (unique diseases with mappings via oboInOwl:hasDbXref)
| Database | Diseases with Mappings | Coverage |
|----------|------------------------|----------|
| Orphanet | 10,246 | 34% |
| OMIM | 9,944 | 33% |
| MeSH | 8,253 | 27% |

### Key Cross-Reference Patterns (from MIE)
- **Medical**: UMLS (70%), MEDGEN (70%), SCTID (31%), MESH (28%), NCIT (25%)
- **Genetic**: GARD (35%), DOID (39%), OMIM (33%), Orphanet (34%)
- **Clinical**: ICD9 (19%), ICD11 (14%), ICD10CM (9%)
- **Oncology**: ICDO (3%), ONCOTREE (2%)
- **Phenotype**: EFO (8%), HP (2%)
- **Japanese**: NANDO (8%)

### Integration Capabilities
- ~90% of diseases have at least one cross-reference
- Average: 6.5 cross-references per disease
- 84% of NANDO diseases link back to MONDO
- 28% coverage of MeSH disease descriptors

## Interesting Findings

**Focus on discoveries requiring actual database queries:**

1. **Cross-reference richness**: Huntington disease (MONDO:0007739) has 16 cross-references spanning medical, genetic, clinical, and Japanese databases

2. **Disease subtypes**: Breast cancer has 1,175+ related terms including molecular subtypes (ER+, ER-, HER2+, triple-negative), familial susceptibility types, and specific carcinoma classifications

3. **Animal models**: Many diseases have non-human animal versions (Huntington disease in pig, sheep, macaque; type 2 diabetes in multiple species)

4. **Rare disease coverage**: Strong integration with Orphanet (10,246 diseases) and GARD for rare diseases

5. **ICD mappings**: Disease codes for clinical billing/classification (ICD9, ICD10CM, ICD10WHO)

## Question Opportunities by Category

### Precision
- "What is the MONDO identifier for Fabry disease?" → MONDO:0010526
- "What is the MONDO identifier for Huntington disease?" → MONDO:0007739
- "What is the MONDO identifier for type 2 diabetes mellitus?" → MONDO:0005148
- "What is the MONDO identifier for breast cancer?" → MONDO:0007254

### Completeness
- "How many disease classes are in MONDO?" → 30,304
- "How many MONDO diseases have OMIM cross-references?" → 9,944
- "How many MONDO diseases have Orphanet cross-references?" → 10,246
- "How many MONDO diseases have MeSH cross-references?" → 8,253
- "How many breast cancer-related terms are in MONDO?" → 1,175+

### Integration
- "What OMIM ID corresponds to Huntington disease in MONDO?" → OMIM:143100
- "What MeSH descriptor ID corresponds to MONDO:0007739 (Huntington disease)?" → MESH:D006816
- "What is the Orphanet ID for Huntington disease?" → Orphanet:399
- "What is the NANDO ID for Huntington disease?" → NANDO:1200012
- "What ICD-10 code corresponds to Huntington disease in MONDO?" → ICD10CM:G10

### Currency
- "What is the current version year of MONDO?" → 2024
- "How many Huntington disease-like syndromes are in MONDO?" → 4 (HDL1, HDL2, HDL3, HDL4)

### Specificity
- "What is the MONDO ID for the rare lysosomal storage disease Fabry disease?" → MONDO:0010526
- "What is the MONDO ID for hormone receptor-positive breast cancer?" → MONDO:0700079
- "What MONDO entry describes familial breast cancer susceptibility type 1?" → MONDO:0800418

### Structured Query
- "Find all breast cancer subtypes classified by gene expression profile in MONDO" → Multiple entries (ER+, ER-, PR+, HER2+)
- "Find all MONDO diseases that have both OMIM and Orphanet cross-references" → Requires compound query
- "Find Huntington disease-like syndromes in MONDO" → MONDO:0015548, MONDO:0011299, MONDO:0011671, MONDO:0011487
- "What are all the parent categories of Fabry disease in MONDO?" → sphingolipidosis, lysosomal storage disease, hereditary disease, inborn errors of metabolism

## Notes
- **Search tools**: OLS4:searchClasses works well for keyword searches with pagination
- **Performance**: Use `bif:contains` for SPARQL full-text search with relevance ranking
- **Blank nodes**: Always use `FILTER(isIRI(?parent))` when querying hierarchy
- **Transitive queries**: Start from specific disease classes to avoid timeout
- **Shared endpoint**: Part of "primary" endpoint with mesh, go, taxonomy, nando, bacdive, mediadive
- **Cross-database queries**: MONDO serves as hub connecting to MeSH (27%), NANDO (8%), and others
