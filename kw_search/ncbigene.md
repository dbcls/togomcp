# NCBI Gene Keyword Search

## Specialized API (Use First)
Use `ncbi_esearch()` to search NCBI Gene database:

**Parameters:**
- `database`: "gene" or "ncbigene"
- `query`: Search query (supports Entrez syntax with field tags and boolean operators)
- `max_results`: Number of results (default 20)
- `start_index`: For pagination (default 0)
- `sort_by`: Optional sort order
- `search_field`: Optional specific field to search in

**Examples:**
```python
ncbi_esearch(database="gene", query="BRCA1", max_results=20)
ncbi_esearch(database="gene", query="BRCA1 AND human[organism]", max_results=10)
ncbi_esearch(database="gene", query="insulin receptor", max_results=15)
ncbi_esearch(database="gene", query="diabetes[disease]", max_results=20)
```

**Supported Query Syntax:**
- Simple keywords: "BRCA1", "insulin receptor"
- Field tags: "human[organism]", "diabetes[disease]"
- Boolean operators: AND, OR, NOT
- Example: "TP53 AND human[organism]"

## Fallback: SPARQL Query
If API is insufficient for complex queries, read MIE file first:
```python
get_MIE_file("ncbigene")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX ncbigene: <http://identifiers.org/ncbigene/>

SELECT DISTINCT ?gene ?symbol ?description
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene a ncbigene:Gene ;
        rdfs:label ?symbol .
  OPTIONAL { ?gene dct:description ?description }
  
  FILTER(CONTAINS(LCASE(?symbol), "keyword") || 
         CONTAINS(LCASE(?description), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Gene symbol
- `dct:description` - Gene description
- `ncbigene:type` - Gene type (protein-coding, ncRNA, pseudogene)
- `ncbigene:chromosome` - Chromosomal location
- `faldo:location` - Genomic coordinates
- Cross-references to Ensembl, HGNC, OMIM

## Notes
- 57M+ gene entries across all organisms
- ncbi_esearch is recommended for keyword searches
- Use SPARQL for complex filtering by gene type, chromosome, or specific annotations
- Filter by organism using [organism] field tag in queries
