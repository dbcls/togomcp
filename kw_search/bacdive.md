# BacDive Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("bacdive")
```

## SPARQL Template
```sparql
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT ?strain ?label ?description
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ;
          rdfs:label ?label .
  OPTIONAL { ?strain dct:description ?description }
  
  FILTER(CONTAINS(LCASE(?label), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Strain name/designation
- `dct:description` - Strain characteristics
- `schema:additionalProperty` - Growth conditions, morphology, etc.

## Notes
- Use FROM clause for graph
- Use OPTIONAL for description (not always present)
- Filter on label for text search
