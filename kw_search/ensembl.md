# Ensembl Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("ensembl")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ensembl: <http://rdf.ebi.ac.uk/resource/ensembl/>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT DISTINCT ?gene ?label ?description
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a ensembl:protein_coding ;
        rdfs:label ?label .
  OPTIONAL { ?gene dc:description ?description }
  
  FILTER(CONTAINS(LCASE(?label), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Gene symbols/names
- `dc:description` - Gene descriptions
- `ensembl:protein_coding`, `ensembl:lncRNA`, etc. - Gene biotypes
- FALDO properties for genomic locations
- `obo:SO_transcribed_from` - Transcript relationships
- Cross-references to UniProt, HGNC, NCBI Gene

## Notes
- 100+ species with genome annotations
- Filter by biotype for specific gene classes
- Use FALDO for positional queries
- Transcript variants linked to proteins via translation
