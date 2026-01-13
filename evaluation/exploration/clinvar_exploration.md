# ClinVar RDF Exploration

## Overview
- **Total variants**: 3,588,969 variation records
- **Current records**: ~3.2M (rest deprecated)
- **Total genes**: ~20,000
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: http://rdfportal.org/dataset/clinvar
- **Base URI**: http://ncbi.nlm.nih.gov/clinvar/

## Variation Type Distribution
| Type | Count |
|------|-------|
| single nucleotide variant | 3,236,823 |
| Deletion | 160,620 |
| Duplication | 73,448 |
| Microsatellite | 36,328 |
| copy number gain | 24,800 |
| copy number loss | 22,592 |
| Indel | 16,935 |
| Insertion | 13,373 |

## Search Tools

### ncbi_esearch (RECOMMENDED for Discovery)
```python
ncbi_esearch(database='clinvar', query='BRCA1 pathogenic')
# Returns: 75,871 results - Variation IDs: 4539422, 4539187...
```

Supports Entrez syntax:
- Gene symbols: `BRCA1`, `TP53`
- Significance: `pathogenic`, `benign`, `uncertain`
- Disease: `breast cancer`, `cystic fibrosis`

### SPARQL for Detailed Queries

#### Search Variants by Gene
```sparql
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT ?variant ?label ?type ?status
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:variation_type ?type ;
           cvo:record_status ?status .
  ?label bif:contains "'BRCA1'" .
}
LIMIT 100
```

#### Get Variant by Accession
```sparql
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT *
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant cvo:accession "VCV000856461" ;
           ?property ?value .
}
```

#### Find Variants with Clinical Significance
```sparql
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT ?variant ?label ?significance
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
}
LIMIT 100
```

#### Count Variants by Type
```sparql
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>

SELECT ?variation_type (COUNT(?variant) as ?count)
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           cvo:variation_type ?variation_type ;
           cvo:record_status "current" .
}
GROUP BY ?variation_type
ORDER BY DESC(?count)
LIMIT 50
```

## Schema Notes

### Key Properties
| Property | Description |
|----------|-------------|
| cvo:accession | VCV accession (e.g., VCV000856461) |
| cvo:variation_id | Numeric ID |
| cvo:variation_type | SNV, Deletion, Duplication, etc. |
| cvo:record_status | "current" or deprecated |
| cvo:number_of_submitters | Evidence strength indicator |
| cvo:date_created | Creation date (xsd:date) |
| cvo:date_last_updated | Last update (xsd:date) |

### Clinical Significance Path
```
variant → cvo:classified_record → cvo:classifications 
        → cvo:germline_classification → cvo:description
```

### Gene Properties
| Property | Description |
|----------|-------------|
| cvo:gene_id | NCBI Gene ID |
| cvo:symbol | Gene symbol (BRCA1) |
| cvo:full_name | Full gene name |
| cvo:hgnc_id | HGNC identifier |
| cvo:omim | OMIM number |
| cvo:cytogenetic_location | Chromosome band |

## Cross-References
| Database | Pattern | Coverage |
|----------|---------|----------|
| MedGen | dct:references | ~95% |
| OMIM | dct:references / cvo:omim | ~40% |
| MeSH | dct:references | ~30% |
| HGNC | cvo:hgnc_id | ~100% (human) |

## Critical Patterns

### ALWAYS
- Include `FROM <http://rdfportal.org/dataset/clinvar>`
- Use `bif:contains` for gene symbol search
- Filter by `cvo:record_status "current"`
- Add LIMIT to prevent timeouts

### NEVER
- Use FILTER(CONTAINS()) for keyword search
- Query without FROM clause
- Forget OPTIONAL for blank node chains

## Anti-Patterns

### ❌ Missing Graph Specification
```sparql
SELECT ?s ?p ?o WHERE {
  ?s a cvo:VariationArchiveType .
}
```

### ✅ With FROM Clause
```sparql
SELECT ?s ?p ?o
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?s a cvo:VariationArchiveType .
}
```

## Question Opportunities
1. **Precision**: "What type is variant VCV000856461?" → Duplication
2. **Counting**: "How many SNVs in ClinVar?" → 3,236,823
3. **Gene-based**: "How many pathogenic BRCA1 variants?"
4. **Cross-ref**: "What MedGen ID is associated with variant X?"
5. **Well-studied**: "Which variants have 3+ submitters?"
6. **Recent**: "What variants were updated in 2024?"
