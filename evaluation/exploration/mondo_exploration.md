# MONDO (Monarch Disease Ontology) Exploration

## Overview
- **Total disease classes**: 30,304
- **Diseases with cross-refs**: ~27,176 (~90%)
- **Average cross-refs per disease**: 6.5
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Graph**: http://rdfportal.org/ontology/mondo
- **Base URI**: http://purl.obolibrary.org/obo/

## Key Entities (Verified)
| MONDO ID | Label | Definition |
|----------|-------|------------|
| MONDO:0005015 | diabetes mellitus | Metabolic disorder with high blood sugar |
| MONDO:0005147 | type 1 diabetes mellitus | Autoimmune diabetes |
| MONDO:0007739 | Huntington disease | Genetic neurodegenerative disorder |
| MONDO:0000003 | achondroplasia | Short-limb dwarfism |

## Search Tools

### OLS4:searchClasses (RECOMMENDED for Discovery)
```python
OLS4:searchClasses(ontologyId='mondo', query='diabetes', pageSize=10)
# Returns: MONDO:0005015 (diabetes mellitus), MONDO:0004782 (diabetes insipidus)...
```

### SPARQL for Detailed Queries

#### Search Diseases by Keyword
```sparql
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
LIMIT 20
```

#### Get Disease Definition and Synonyms
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX IAO: <http://purl.obolibrary.org/obo/IAO_>

SELECT ?label ?definition ?synonym ?parentLabel
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  obo:MONDO_0005015 rdfs:label ?label .
  OPTIONAL { obo:MONDO_0005015 IAO:0000115 ?definition }
  OPTIONAL { obo:MONDO_0005015 oboInOwl:hasExactSynonym ?synonym }
  OPTIONAL { 
    obo:MONDO_0005015 rdfs:subClassOf ?parent .
    ?parent rdfs:label ?parentLabel .
    FILTER(isIRI(?parent))
  }
}
```

#### Find Diseases with OMIM References
```sparql
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
```

#### Get Disease Hierarchy
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?parent ?parentId ?parentLabel
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  obo:MONDO_0005015 rdfs:subClassOf+ ?parent .
  ?parent rdfs:label ?parentLabel ;
    oboInOwl:id ?parentId .
  FILTER(isIRI(?parent))
}
```

## Schema Notes

### Key Properties
| Property | Description |
|----------|-------------|
| rdfs:label | Disease name |
| oboInOwl:id | MONDO ID (e.g., MONDO:0005015) |
| IAO:0000115 | Definition |
| rdfs:subClassOf | Parent disease class |
| oboInOwl:hasExactSynonym | Exact synonyms |
| oboInOwl:hasRelatedSynonym | Related synonyms |
| oboInOwl:hasDbXref | Cross-references |

### Cross-Reference Coverage
| Database | Prefix | Coverage |
|----------|--------|----------|
| UMLS | UMLS: | 70% |
| MEDGEN | MEDGEN: | 70% |
| DOID | DOID: | 39% |
| GARD | GARD: | 35% |
| Orphanet | Orphanet: | 34% |
| OMIM | OMIM: | 33% |
| SCTID (SNOMED CT) | SCTID: | 31% |
| MeSH | MESH: | 28% |
| NCIT | NCIT: | 25% |
| ICD-9 | ICD9: | 19% |
| ICD-11 | ICD11: | 14% |

## Critical Patterns

### ALWAYS
- Include `FROM <http://rdfportal.org/ontology/mondo>`
- Use `bif:contains` for text search
- Add `FILTER(isIRI(?parent))` to exclude blank nodes
- Add LIMIT for transitive hierarchy queries

### NEVER
- Use FILTER(CONTAINS()) for keyword search
- Run unbounded rdfs:subClassOf* queries
- Forget to filter out blank nodes in hierarchy

## Anti-Patterns

### ❌ Missing Blank Node Filter
```sparql
SELECT ?parent WHERE {
  ?disease rdfs:subClassOf ?parent
}
```

### ✅ With Blank Node Filter
```sparql
SELECT ?parent WHERE {
  ?disease rdfs:subClassOf ?parent .
  FILTER(isIRI(?parent))
}
```

## Question Opportunities
1. **Precision**: "What is the MONDO ID for diabetes mellitus?" → MONDO:0005015
2. **Counting**: "How many disease classes in MONDO?" → 30,304
3. **Definition**: "What is the definition of achondroplasia?"
4. **Cross-ref**: "What OMIM ID corresponds to Huntington disease?" → OMIM:143100
5. **Hierarchy**: "What are the parent classes of type 1 diabetes?"
6. **Search**: "Find all diseases related to 'autoimmune'"
