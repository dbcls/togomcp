# Ensembl RDF Exploration

## Overview
- **Total genes**: ~3M genes across 100+ species
- **Total transcripts**: ~4M
- **Total proteins**: ~2M
- **Endpoint**: https://rdfportal.org/ebi/sparql
- **Graph**: http://rdfportal.org/dataset/ensembl
- **Base URI**: http://rdf.ebi.ac.uk/resource/ensembl/

## Species Gene Distribution
| Species | Taxonomy ID | Gene Count |
|---------|-------------|------------|
| Mouse | 10090 | 744,820 |
| Sheep | 9940 | 633,869 |
| Pig | 9823 | 624,705 |
| Salmon | 8030 | 267,676 |
| Zebrafish | 7962 | 154,109 |
| Dog | 9615 | 144,873 |
| Rat | 10116 | 143,695 |
| Goat | 9925 | 123,153 |
| Chicken | 9031 | 91,195 |
| **Human** | **9606** | **87,688** |

## Key Entities (Verified)
| Ensembl ID | Symbol | Description |
|------------|--------|-------------|
| ENSG00000012048 | BRCA1 | BRCA1 DNA repair associated |
| LRG_292 | BRCA1 | Locus Reference Genomic |

## SPARQL Queries

### Search Genes by Symbol
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene ?id ?label ?description
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        dcterms:description ?description ;
        obo:RO_0002162 taxonomy:9606 .
  ?label bif:contains "'BRCA*'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
```

### List Genes on Chromosome
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene ?id ?label
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        so:part_of ?chr ;
        terms:has_biotype <http://ensembl.org/glossary/ENSGLOSSARY_0000026> ;
        obo:RO_0002162 taxonomy:9606 .
  FILTER(CONTAINS(STR(?chr), "GRCh38/X"))
}
LIMIT 100
```

### Get Gene Genomic Coordinates
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>

SELECT DISTINCT ?gene ?id ?label ?start ?end ?strand
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        faldo:location ?loc .
  ?loc faldo:begin/faldo:position ?start ;
       faldo:end/faldo:position ?end ;
       faldo:begin/rdf:type ?strand_type .
  BIND(IF(?strand_type = faldo:ForwardStrandPosition, "+", "-") AS ?strand)
  FILTER(?id = "ENSG00000012048")
}
```

### Gene-Transcript-Protein Mapping
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>

SELECT ?gene_id ?gene_label ?transcript_id ?protein_id ?uniprot
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?gene_id ;
        rdfs:label ?gene_label .
  ?transcript so:transcribed_from ?gene ;
              dcterms:identifier ?transcript_id ;
              so:translates_to ?protein .
  ?protein dcterms:identifier ?protein_id ;
           rdfs:seeAlso ?uniprot .
  FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
  FILTER(?gene_label = "BRCA1")
}
LIMIT 20
```

## Schema Notes

### Hierarchy
- Gene (terms:EnsemblGene) → Transcript (terms:EnsemblTranscript) → Protein (terms:EnsemblProtein)
- Transcripts transcribed_from genes
- Proteins translation_of transcripts

### Key Properties
| Property | Description |
|----------|-------------|
| dcterms:identifier | Ensembl ID (ENSG/ENST/ENSP) |
| rdfs:label | Gene symbol |
| dcterms:description | Full description |
| terms:has_biotype | Gene/transcript type |
| obo:RO_0002162 | Species (taxonomy ID) |
| so:part_of | Chromosome |
| faldo:location | Genomic coordinates |

### Biotypes
| Code | Description |
|------|-------------|
| ENSGLOSSARY_0000026 | protein_coding |
| ENSGLOSSARY_0000038 | miRNA |
| ENSGLOSSARY_0000030 | lncRNA |

### FALDO Coordinates
- `faldo:begin/faldo:position` = start position
- `faldo:end/faldo:position` = end position
- `faldo:ForwardStrandPosition` = + strand
- `faldo:ReverseStrandPosition` = - strand

## Cross-References
| Database | Pattern | Coverage |
|----------|---------|----------|
| UniProt | rdfs:seeAlso | ~60% |
| HGNC | rdfs:seeAlso | human genes |
| NCBI Gene | rdfs:seeAlso | variable |
| Reactome | rdfs:seeAlso | selected |

## Critical Patterns

### ALWAYS
- Filter by species: `obo:RO_0002162 taxonomy:9606` (for human)
- Use DISTINCT with FALDO queries
- Use `bif:contains` for text search
- Include `FROM <http://rdfportal.org/dataset/ensembl>`

### NEVER
- Query without species filter (causes timeout)
- Use FILTER/REGEX for gene symbol search
- Forget LIMIT on exploratory queries

## Anti-Patterns

### ❌ Missing Species Filter
```sparql
SELECT ?gene ?label WHERE {
  ?gene a terms:EnsemblGene ;
        rdfs:label ?label .
  FILTER(?label = "TP53")
}
```

### ✅ With Species Filter
```sparql
SELECT ?gene ?label WHERE {
  ?gene a terms:EnsemblGene ;
        rdfs:label ?label ;
        obo:RO_0002162 taxonomy:9606 .
  FILTER(?label = "TP53")
}
```

## Question Opportunities
1. **Precision**: "What is the Ensembl ID for BRCA1?" → ENSG00000012048
2. **Counting**: "How many human genes in Ensembl?" → 87,688
3. **Location**: "What chromosome is BRCA1 on?" → 17
4. **Cross-ref**: "What UniProt ID corresponds to ENSG00000012048?" → P38398
5. **Species**: "Which species has the most genes?" → Mouse (744,820)
6. **Biotype**: "How many protein-coding human genes?"
