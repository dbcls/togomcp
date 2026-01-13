# NCBI Gene Database Exploration

## Overview
- **Total entries**: 57.7M+ genes across all organisms
- **Human genes**: ~193K (20,595 protein-coding, 22,103 ncRNA, 17,483 pseudogenes)
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: http://rdfportal.org/dataset/ncbigene
- **Base URI**: http://identifiers.org/ncbigene/

## Key Entities (Verified)
| Gene ID | Symbol | Description | Type | Chromosome |
|---------|--------|-------------|------|------------|
| 672 | BRCA1 | BRCA1 DNA repair associated | protein-coding | 17 |
| 7157 | TP53 | tumor protein p53 | protein-coding | 17 |
| 3630 | INS | insulin | protein-coding | 11 |
| 1 | A1BG | alpha-1-B glycoprotein | protein-coding | 19 |

## Human Gene Type Distribution
| Type | Count |
|------|-------|
| biological-region | 128,261 |
| ncRNA | 22,103 |
| protein-coding | 20,595 |
| pseudo | 17,483 |
| snoRNA | 1,201 |
| unknown | 1,191 |
| other | 845 |
| rRNA | 781 |
| tRNA | 658 |
| snRNA | 166 |
| scRNA | 4 |

## Search Tools

### ncbi_esearch (RECOMMENDED for Discovery)
Use for finding gene IDs before SPARQL queries:
```python
ncbi_esearch(database='gene', query='BRCA1 AND human[organism]')
# Returns: Gene IDs 7157, 1956, 3569, 7422, 7040...
```

Supports Entrez syntax:
- Field tags: `[Gene Name]`, `[Symbol]`, `[Organism]`
- Boolean: `AND`, `OR`, `NOT`
- Example: `"insulin receptor" AND human[organism]`

### SPARQL (for Detailed Metadata)

#### Basic Gene Lookup
```sparql
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX ncbio: <https://dbcls.github.io/ncbigene-rdf/ontology.ttl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?label ?description ?type ?chromosome
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  <http://identifiers.org/ncbigene/672> rdfs:label ?label ;
    ncbio:typeOfGene ?type .
  OPTIONAL { <http://identifiers.org/ncbigene/672> dct:description ?description }
  OPTIONAL { <http://identifiers.org/ncbigene/672> insdc:chromosome ?chromosome }
}
```

#### Text Search in Descriptions
```sparql
PREFIX ncbio: <https://dbcls.github.io/ncbigene-rdf/ontology.ttl#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?gene ?description ?sc
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene ncbio:taxid <http://identifiers.org/taxonomy/9606> ;
        dct:description ?description .
  ?description bif:contains "'insulin'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
```

#### Get Orthologs
```sparql
PREFIX orth: <http://purl.org/net/orth#>
PREFIX ncbio: <https://dbcls.github.io/ncbigene-rdf/ontology.ttl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?ortholog ?label ?taxid
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  <http://identifiers.org/ncbigene/3630> orth:hasOrtholog ?ortholog .
  ?ortholog rdfs:label ?label ;
            ncbio:taxid ?taxid .
}
LIMIT 100
```

## Schema Notes
- `rdfs:label` = gene symbols (INS, BRCA1)
- `dct:description` = full names (insulin, BRCA1 DNA repair associated)
- `ncbio:typeOfGene` = protein-coding, ncRNA, pseudo, etc.
- `insdc:dblink` = IRI links (Ensembl, HGNC, OMIM)
- `insdc:db_xref` = string references (Database:ID format)
- `orth:hasOrtholog` = orthology relationships

## Cross-References
| Target | Property | Coverage |
|--------|----------|----------|
| Ensembl | insdc:dblink | ~70% |
| HGNC | insdc:dblink | ~100% (human) |
| OMIM | insdc:dblink | variable |
| NCBI Taxonomy | ncbio:taxid | 100% |

## Critical Patterns

### RECOMMENDED WORKFLOW
1. Use `ncbi_esearch` for initial gene discovery
2. Use SPARQL for detailed metadata and cross-references
3. Always filter by `ncbio:taxid` to avoid timeouts

### ALWAYS
- Include `FROM <http://rdfportal.org/dataset/ncbigene>`
- Filter by taxid early (57M+ genes cause timeouts)
- Use `bif:contains` for text search
- Add LIMIT to orthology queries

### NEVER
- Search without organism filter
- Search full names in `rdfs:label` (use `dct:description`)
- Run unbounded orthology queries

## Anti-Patterns

### ❌ No Organism Filter (Timeout)
```sparql
SELECT ?gene ?description
WHERE {
  ?gene dct:description ?description .
  FILTER(CONTAINS(?description, "insulin"))
}
```

### ✅ Correct: Filter by Taxid First
```sparql
SELECT ?gene ?description ?sc
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene ncbio:taxid <http://identifiers.org/taxonomy/9606> ;
        dct:description ?description .
  ?description bif:contains "'insulin'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 100
```

## Question Opportunities
1. **Precision**: "What chromosome is BRCA1 located on?" → Chr 17
2. **Counting**: "How many protein-coding genes in humans?" → 20,595
3. **Cross-ref**: "What is the Ensembl ID for gene 672?" → ENSG00000012048
4. **Orthology**: "How many orthologs does INS have?" → ~150
5. **Type distribution**: "What are the types of human genes?"
