# NCBI Gene Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
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
- Search by symbol, synonym, or description
- Filter by gene type for specific categories
- Use taxonomic filters for organism-specific searches
