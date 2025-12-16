# ClinVar Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("clinvar")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX clinvar: <http://purl.jp/bio/10/clinvar/>

SELECT DISTINCT ?variant ?name ?condition
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant rdfs:label ?name ;
           clinvar:interpreted_condition ?condition_iri .
  ?condition_iri rdfs:label ?condition .
  
  FILTER(CONTAINS(LCASE(?name), "keyword") || 
         CONTAINS(LCASE(?condition), "keyword"))
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Variant name/identifier
- `clinvar:interpreted_condition` - Disease/phenotype associations
- `clinvar:variant_type` - Variant type classification
- `clinvar:clinical_significance` - Pathogenicity classification
- Gene associations via cross-references
- Cross-references to MedGen, OMIM, MeSH

## Notes
- Search by variant name, gene, or associated condition
- 3.5M+ variant records with clinical interpretations
- Use clinical_significance for filtering pathogenic variants
