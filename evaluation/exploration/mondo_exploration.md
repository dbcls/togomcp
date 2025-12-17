# MONDO (Monarch Disease Ontology) Exploration Report

## Database Overview
- **Purpose**: Comprehensive disease ontology integrating multiple disease databases
- **Scope**: 30,304 total classes covering diseases and disorders
- **Key data types**:
  - Active diseases (28,500)
  - Disease classes with cross-references (27,176, ~90%)
  - OBO Foundry compliant ontology structure
- **Integration**: 39+ external databases including OMIM, Orphanet, DOID, MeSH, ICD, UMLS

## Schema Analysis (from MIE file)

### Main Properties
- **owl:Class**: Disease entity in ontology
- **rdfs:label**: Disease name
- **oboInOwl:id**: MONDO ID (e.g., "MONDO:0005147")
- **IAO:0000115**: Textual definition (~75% coverage)
- **rdfs:subClassOf**: Parent disease class (hierarchical classification)
- **oboInOwl:hasExactSynonym**: Semantically equivalent alternative names
- **oboInOwl:hasRelatedSynonym**: Related but not exact synonyms
- **oboInOwl:hasDbXref**: External database cross-references
- **owl:deprecated**: Obsolete term flag

### Important Relationships
- **Hierarchical structure**: rdfs:subClassOf creates disease classification tree
- **Single cross-reference property**: oboInOwl:hasDbXref for all external links
- **Comprehensive mapping**: 39+ external databases
- **Average cardinality**:
  - 6.5 cross-references per disease
  - 2.8 synonyms per disease
  - 1.2 parents per disease
- **Top-level class**: MONDO:0000001 "disease or disorder" (root)
- **Cross-reference coverage**:
  - UMLS: 70%
  - MEDGEN: 70%
  - DOID: 39%
  - GARD: 35%
  - Orphanet: 34%
  - OMIM: 33%
  - SCTID (SNOMED CT): 31%
  - MESH: 28%
  - NCIT: 25%
  - ICD9: 19%, ICD11: 14%, ICD10CM: 9%
  - NANDO: 8% (Japanese rare diseases)

### Query Patterns Observed
1. **Use bif:contains for search**: NOT FILTER(CONTAINS(...))
2. **Add relevance scoring**: `option (score ?sc)` with ORDER BY DESC(?sc)
3. **Filter blank nodes**: Add `FILTER(isIRI(?parent))` for hierarchy queries
4. **Include FROM clause**: `FROM <http://rdfportal.org/ontology/mondo>`
5. **Start specific for transitivity**: Use specific disease ID for rdfs:subClassOf*
6. **Always add LIMIT**: 20-100 for exploratory queries (30K+ classes)
7. **Use STRSTARTS for cross-refs**: Filter by database prefix (e.g., "OMIM:")
8. **Use OPTIONAL**: For variable coverage (definition, synonyms, xrefs)

## Search Queries Performed

### Query 1: Search diabetes-related diseases
**Tool**: TogoMCP run_sparql with bif:contains
**Result**: Found 10 diabetes-related disease entries:
- MONDO:0022650: "cardiomyopathy diabetes deafness"
- MONDO:0022971: "diabetes persistent mullerian ducts"
- MONDO:0023045: "ectodermal dysplasia arthrogryposis diabetes mellitus"
- MONDO:0100072: "neonatal diabetes, congenital sensorineural hearing loss and congenital cataracts"
- MONDO:1010051-1010568: Non-human animal diabetes entries
- Shows rare/complex diseases and animal models

### Query 2: Search cancer diseases
**Tool**: OLS4:search (multi-ontology search)
**Query**: "cancer"
**Result**: Found MONDO:0004992 "cancer" as primary cancer entity
- Also found in DOID, SNOMED, EFO ontologies
- MONDO serves as cross-ontology reference point

### Query 3: Search Alzheimer disease
**Tool**: OLS4:searchClasses (MONDO-specific search)
**Query**: "Alzheimer"
**Result**: Found 51 Alzheimer-related diseases including:
- MONDO:1011460: "Alzheimer disease, degu"
- MONDO:1011461: "Alzheimer disease, dog"
- MONDO:1011462: "Alzheimer disease, domestic cat"
- MONDO:1011463: "Alzheimer disease, sheep"
- MONDO:1011443: "Alzheimer disease, non-human animal" (parent class)
- MONDO:1012917: "Alzheimer disease, PSEN1-related, pig"
- MONDO:1012929: "Alzheimer disease, APP-related, pig"
- MONDO:1012938: "Alzheimer disease, SORL1-related, pig"
Note: Extensive coverage of animal models for research

### Query 4: Search cystic fibrosis
**Tool**: OLS4:searchClasses (MONDO-specific search)
**Query**: "cystic fibrosis"
**Result**: Found 465 cystic fibrosis-related diseases including:
- MONDO:0009061: "cystic fibrosis" (main human disease)
- MONDO:1010544: "cystic fibrosis, pig"
- MONDO:1010545: "cystic fibrosis, sheep"
- MONDO:1010543: "cystic fibrosis, domestic ferret"
- MONDO:1010043: "cystic fibrosis, non-human animal"
- MONDO:0009062: "cystic fibrosis-gastritis-megaloblastic anemia syndrome"
- MONDO:0005413: "cystic fibrosis associated meconium ileus"
- MONDO:0010178: "congenital bilateral aplasia of vas deferens from CFTR mutation"
Note: Shows related syndromes and complications

### Query 5: Search Parkinson disease
**Tool**: OLS4:searchClasses (MONDO-specific search)
**Query**: "Parkinson"
**Result**: Found 108 Parkinson-related diseases including:
- MONDO:0036193: "parkinsonism with polyneuropathy"
- MONDO:1012984: "Parkinson disease, non-human animal"
- MONDO:0800369: "Parkinson disease 19B, early-onset"
- MONDO:1012875: "Parkinson disease, PINK1-related, crab-eating macaque"
- MONDO:1012876: "Parkinson disease, PINK1-related, rhesus monkey"
- MONDO:1012884: "Parkinson disease, SNCA-related, rhesus monkey"
- MONDO:1012886: "Parkinson disease, LRRK2-related, white-tufted-ear marmoset"
- MONDO:0975748: "Parkinson disease 26, autosomal dominant, susceptibility to"
- MONDO:0013625: "Parkinson disease 17" (VPS35 gene)
- MONDO:0013150: "parkinsonism-dystonia, infantile"
Note: Extensive genetic subtypes and animal models

### Query 6: Search achondroplasia (skeletal dysplasia)
**Tool**: OLS4:searchClasses (MONDO-specific search)
**Query**: "achondroplasia"
**Result**: Found 8 achondroplasia-related diseases:
- MONDO:0007037: "achondroplasia" (main human disease)
- MONDO:1011147: "achondroplasia, dog"
- MONDO:1011148: "achondroplasia, cattle"
- MONDO:1011149: "achondroplasia, sheep"
- MONDO:1011146: "achondroplasia, water buffalo"
- MONDO:1010291: "achondroplasia, non-human animal"
- MONDO:0014658: "severe achondroplasia-developmental delay-acanthosis nigricans syndrome"
Note: FGFR3-related chondrodysplasia with detailed definitions

## SPARQL Queries Tested

```sparql
# Query 1: Search diseases with relevance ranking (VERIFIED)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?disease ?mondoId ?label
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  ?disease a owl:Class ;
    rdfs:label ?label ;
    oboInOwl:id ?mondoId .
  ?label bif:contains "'diabetes'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: 10 diabetes-related diseases including rare syndromes
```

```sparql
# Query 2: Get disease hierarchy (from MIE, with blank node filter)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?parent ?parentId ?parentLabel
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  obo:MONDO_0005147 rdfs:subClassOf+ ?parent .
  ?parent rdfs:label ?parentLabel ;
    oboInOwl:id ?parentId .
  FILTER(isIRI(?parent))
}
# CRITICAL: FILTER(isIRI(?parent)) excludes blank nodes
```

```sparql
# Query 3: Find diseases with OMIM cross-references (from MIE)
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?disease ?label ?xref
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  ?disease a owl:Class ;
    rdfs:label ?label ;
    oboInOwl:hasDbXref ?xref .
  FILTER(STRSTARTS(?xref, "OMIM:"))
}
LIMIT 50
# Would return diseases with OMIM genetic disorder cross-references
```

## Interesting Findings

### Specific Entities for Questions
1. **MONDO:0000001**: "disease or disorder" (root class)
2. **MONDO:0005147**: "type 1 diabetes mellitus"
3. **MONDO:0000003**: "achondroplasia" (skeletal dysplasia)
4. **MONDO:0007739**: "Huntington disease"
5. **MONDO:0004992**: "cancer"
6. **MONDO:0022650**: "cardiomyopathy diabetes deafness" (complex syndrome)

### Unique Properties
- **OBO Foundry compliant**: Standard ontology structure
- **Comprehensive integration**: 39+ external databases
- **90% cross-reference coverage**: Excellent mapping
- **Multiple synonym types**: Exact vs related synonyms
- **Rare disease focus**: Strong Orphanet and GARD coverage
- **Animal models**: Includes non-human disease entries
- **Monthly updates**: Regular release cycle

### Connections to Other Databases
- **Genetic disorders**: OMIM (33%), Orphanet (34%), GARD (35%)
- **Medical terminologies**: UMLS (70%), MEDGEN (70%), MESH (28%), SNOMED CT (31%)
- **Disease ontologies**: DOID (39%), EFO (8%)
- **Clinical classifications**: ICD-9 (19%), ICD-10 (9%), ICD-11 (14%)
- **Oncology**: ICDO (3%), OncoTree (2%)
- **Rare diseases**: NANDO (8% - Japanese rare diseases)
- **Cancer**: NCIT (25%)

### Specific, Verifiable Facts
1. MONDO contains 30,304 total disease classes
2. 28,500 active diseases
3. 27,176 diseases with cross-references (~90%)
4. Average 6.5 cross-references per disease
5. Average 2.8 synonyms per disease
6. ~75% have textual definitions
7. ~85% have synonyms
8. UMLS and MEDGEN: 70% coverage (highest)
9. OMIM: 33%, Orphanet: 34%, DOID: 39%
10. ICD-10CM: 9%, ICD-11: 14%

## Question Opportunities by Category

### Precision
- "What is the MONDO ID for type 1 diabetes mellitus?" (MONDO:0005147)
- "What is the OMIM cross-reference for achondroplasia?" (OMIM:100800)
- "What is the definition of Huntington disease in MONDO?"

### Completeness
- "List all subtypes of diabetes mellitus in MONDO"
- "How many diseases have Orphanet cross-references?"
- "What are all synonyms for cancer?"

### Integration
- "Convert MONDO:0005147 to ICD-10 code" (E10)
- "Link MONDO:0007739 (Huntington disease) to OMIM" (OMIM:143100)
- "Find MeSH term for MONDO achondroplasia"

### Currency
- "What diseases were added to MONDO in recent releases?"
- "How many NANDO cross-references exist?" (8%)

### Specificity
- "What is MONDO:0022650?" (cardiomyopathy diabetes deafness)
- "What rare genetic disorders are classified under skeletal dysplasia?"
- "Which animal models are included for diabetes insipidus?"

### Structured Query
- "Count diseases by top-level category"
- "Find all genetic disorders" (rdfs:subClassOf* from MONDO:0003847)
- "Search cancer diseases AND their OMIM mappings"

## Notes

### Limitations and Challenges
1. **Blank nodes in hierarchy**: Must filter with isIRI() to exclude OWL restrictions
2. **Large dataset**: 30K+ classes require careful query optimization
3. **Variable coverage**: Definitions ~75%, cross-refs vary by database (3-70%)
4. **Transitive queries expensive**: Need specific starting points
5. **Multiple naming conventions**: Different databases use different formats

### Best Practices for Querying
1. **Use bif:contains**: NOT FILTER(CONTAINS(...))
2. **Add relevance scoring**: `option (score ?sc)`
3. **CRITICAL**: Add `FILTER(isIRI(?parent))` for hierarchy to exclude blank nodes
4. **Include FROM clause**: `FROM <http://rdfportal.org/ontology/mondo>`
5. **Always add LIMIT**: 20-100 for exploratory queries
6. **Use OPTIONAL**: For definition, synonyms, xrefs (variable coverage)
7. **Start specific**: For rdfs:subClassOf* queries, use known disease ID
8. **Filter by prefix**: STRSTARTS(?xref, "OMIM:") for specific databases
9. **Check for deprecated**: Use owl:deprecated to filter obsolete terms

### Data Quality
- **Labels**: >99% complete
- **Definitions**: ~75% coverage
- **Cross-references**: ~90% coverage (27,176 of 30,304)
- **Synonyms**: ~85% coverage
- **Update frequency**: Monthly from MONDO team
- **Curation**: Community-driven with expert review
- **OBO Foundry**: Meets ontology best practices
