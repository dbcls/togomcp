# MedGen Keyword Search

## Specialized API (Use First)
Use `ncbi_esearch()` to search MedGen database:

**Parameters:**
- `database`: "medgen"
- `query`: Search query (supports Entrez syntax with field tags and boolean operators)
- `max_results`: Number of results (default 20)
- `start_index`: For pagination (default 0)
- `sort_by`: Optional sort order
- `search_field`: Optional specific field to search in

**Examples:**
```python
ncbi_esearch(database="medgen", query="breast cancer", max_results=20)
ncbi_esearch(database="medgen", query="hypertrophic cardiomyopathy", max_results=15)
ncbi_esearch(database="medgen", query="cystic fibrosis", max_results=10)
ncbi_esearch(database="medgen", query="marfan syndrome", max_results=20)
```

**Supported Query Syntax:**
- Simple keywords: "breast cancer", "diabetes"
- Field tags: "cardiomyopathy[concept]", "genetic[condition]"
- Boolean operators: AND, OR, NOT
- Example: "cardiomyopathy AND genetic"

## Fallback: SPARQL Query
If API is insufficient for complex queries, read MIE file first:
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
- ncbi_esearch is recommended for keyword searches by disease name or concept
- Integrates multiple nomenclatures (OMIM, Orphanet, HPO)
- Use SPARQL for complex hierarchical navigation via relationships
- Search diseases, phenotypes, or clinical findings
