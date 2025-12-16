# DDBJ Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("ddbj")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT DISTINCT ?entry ?definition ?organism
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?entry a insdc:Entry ;
         insdc:definition ?definition ;
         insdc:organism ?organism .
  
  FILTER(CONTAINS(LCASE(?definition), "keyword") || 
         CONTAINS(LCASE(?organism), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `insdc:definition` - Sequence definition/description
- `insdc:organism` - Source organism
- `insdc:feature` - Genomic features (genes, CDS, tRNA, etc.)
- `insdc:sequence` - Nucleotide sequence
- FALDO properties for genomic coordinates
- Sequence Ontology for feature types

## Notes
- Search by definition, organism, or feature annotations
- Use FALDO for positional queries
- Cross-references to BioProject, BioSample, NCBI Protein
