# MedGen (Medical Genetics) Exploration

## Overview
- **Total concepts**: 233,939 clinical concepts
- **Total relationships (MGREL)**: 1,130,420
- **Total attributes (MGSAT)**: 1,117,180
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: http://rdfportal.org/dataset/medgen
- **Base URI**: http://www.ncbi.nlm.nih.gov/medgen/

## Key Entities (Verified)
| CUI | Label |
|-----|-------|
| C0011849 | Diabetes mellitus |
| C0011859 | Lipoatrophic diabetes |
| C0085207 | Gestational diabetes |
| C0023467 | Acute myeloid leukemia |

## Search Tools

### ncbi_esearch (RECOMMENDED for Discovery)
```python
ncbi_esearch(database='medgen', query='diabetes')
# Returns: CUI identifiers
```

### SPARQL for Detailed Queries

#### Find Concept by Identifier
```sparql
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?identifier ?label ?sty ?definition
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      dct:identifier "C0011849" ;
      rdfs:label ?label ;
      mo:sty ?sty .
  OPTIONAL { ?concept skos:definition ?definition }
}
```

#### Search by Keyword
```sparql
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?concept ?identifier ?label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      rdfs:label ?label ;
      dct:identifier ?identifier .
  ?label bif:contains "'diabetes'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

#### Get External Cross-References
```sparql
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT ?concept ?identifier ?external_db
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      dct:identifier "C0011849" ;
      mo:mgconso ?bn .
  ?bn rdfs:seeAlso ?external_db .
  BIND("C0011849" as ?identifier)
}
LIMIT 20
```

#### Find Related Concepts via MGREL
```sparql
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?disease ?disease_label ?related ?related_label ?rel_type
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?disease a mo:ConceptID ;
      dct:identifier "C0011849" ;
      rdfs:label ?disease_label .
  ?rel a mo:MGREL ;
      mo:cui1 ?disease ;
      mo:cui2 ?related ;
      mo:rela ?rel_type .
  ?related rdfs:label ?related_label .
  FILTER(?disease != ?related)
}
LIMIT 20
```

## Schema Notes

### CRITICAL: Relationships in MGREL
Relationships are NOT direct properties on ConceptID. They are stored in MGREL entities:
- `mo:cui1` = source concept
- `mo:cui2` = target concept
- `mo:rela` = relationship type (isa, has_manifestation, etc.)

### Key Properties
| Property | Description |
|----------|-------------|
| dct:identifier | CUI (e.g., C0011849) |
| rdfs:label | Concept name |
| mo:sty | UMLS semantic type |
| skos:definition | Definition (~34% coverage) |
| mo:mgconso | Cross-reference container |
| mo:mgsat | Attribute container |

### Semantic Types (mo:sty)
| Code | Description |
|------|-------------|
| sty:T047 | Disease or Syndrome |
| sty:T191 | Neoplastic Process |
| sty:T033 | Finding |
| sty:T184 | Sign or Symptom |

### Cross-Reference Coverage
| Database | Prefix | Coverage |
|----------|--------|----------|
| MeSH | mesh: | ~80% |
| MONDO | MONDO_ | ~70% |
| SNOMED CT | SCTID | ~60% |
| ICD-10 | ICD10 | ~50% |
| HPO | HP_ | ~40% |
| OMIM | mim/ | ~30% |

## Critical Patterns

### ALWAYS
- Include `FROM <http://rdfportal.org/dataset/medgen>`
- Use MGREL for relationships (NOT direct properties)
- Use DISTINCT for cross-reference queries
- Use `bif:contains` for keyword search
- Add LIMIT (large entity counts)

### NEVER
- Use direct relationship properties on ConceptID
- Query MGREL/MGSAT without LIMIT
- Use FILTER(CONTAINS()) for keyword search

## Anti-Patterns

### ❌ Wrong: Direct Relationship Properties
```sparql
SELECT ?disease ?gene WHERE {
  ?disease mo:disease_has_associated_gene ?gene .  -- WILL NOT WORK!
}
```

### ✅ Correct: Use MGREL
```sparql
SELECT ?disease ?gene
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?rel a mo:MGREL ;
      mo:cui1 ?disease ;
      mo:cui2 ?gene ;
      mo:rela ?rel_type .
  FILTER(CONTAINS(LCASE(?rel_type), "gene"))
}
LIMIT 100
```

## Question Opportunities
1. **Precision**: "What is the CUI for diabetes mellitus?" → C0011849
2. **Counting**: "How many concepts in MedGen?" → 233,939
3. **Search**: "Find concepts related to 'leukemia'"
4. **Cross-ref**: "What OMIM ID corresponds to C0011849?"
5. **Relationships**: "What are manifestations of diabetes mellitus?"
6. **Semantic type**: "Find all disease concepts (T047)"
