# MediaDive Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("mediadive")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX md: <https://dsmz.de/mediadive/>

SELECT DISTINCT ?medium ?label ?description
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?medium a md:Medium ;
          rdfs:label ?label .
  OPTIONAL { ?medium dct:description ?description }
  
  FILTER(CONTAINS(LCASE(?label), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Medium name/number
- `dct:description` - Medium description
- `md:ingredient` - Ingredients with amounts
- `md:solution` - Solution components
- `md:hasPH` - pH value
- `md:hasTemperature` - Growth temperature

## Notes
- Search medium names, ingredients, or applications
- Use OPTIONAL for properties that may not exist
- Media recipes have hierarchical structure: medium → solution → ingredient
