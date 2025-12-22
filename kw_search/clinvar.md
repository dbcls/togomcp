# ClinVar Keyword Search

## Specialized API (Use First)
Use `ncbi_esearch()` to search ClinVar database:

**Parameters:**
- `database`: "clinvar"
- `query`: Search query (supports Entrez syntax with field tags and boolean operators)
- `max_results`: Number of results (default 20)
- `start_index`: For pagination (default 0)
- `sort_by`: Optional sort order
- `search_field`: Optional specific field to search in

**Examples:**
```python
ncbi_esearch(database="clinvar", query="BRCA1", max_results=20)
ncbi_esearch(database="clinvar", query="BRCA1 AND pathogenic", max_results=15)
ncbi_esearch(database="clinvar", query="breast cancer", max_results=20)
ncbi_esearch(database="clinvar", query="hypertrophic cardiomyopathy", max_results=10)
```

**Supported Query Syntax:**
- Simple keywords: "BRCA1", "breast cancer"
- Field tags: "BRCA1[gene]", "pathogenic[condition]"
- Boolean operators: AND, OR, NOT
- Example: "BRCA1 AND pathogenic"

## Fallback: SPARQL Query
If API is insufficient for complex queries, read MIE file first:
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
- 3.5M+ variant records with clinical interpretations
- ncbi_esearch is recommended for keyword searches by gene or condition
- Use SPARQL for complex filtering by clinical_significance, variant_type, or specific annotations
- Combine gene and pathogenicity terms in queries for targeted results
