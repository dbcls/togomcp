# MedGen Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("medgen")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX medgen: <http://identifiers.org/medgen/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT ?concept ?name ?definition
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a medgen:ConceptID ;
           rdfs:label ?name .
  OPTIONAL { ?concept dct:description ?definition }
  
  FILTER(CONTAINS(LCASE(?name), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Concept name (disease/phenotype/clinical finding)
- `dct:description` - Concept definition
- `medgen:MGREL` - Relationships between concepts
- `medgen:MGSAT` - Concept attributes
- `medgen:MGCONSO` - Terminology mappings
- Cross-references to OMIM, Orphanet, HPO, MONDO

## Notes
- 233K+ clinical concepts with genetic components
- Integrates multiple nomenclatures (OMIM, Orphanet, HPO)
- Search diseases, phenotypes, or clinical findings
- Use relationships for hierarchical navigation
