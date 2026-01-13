# NCBI Taxonomy RDF Exploration

## Overview
- **Total taxa**: 2,698,386
- **Estimated species**: ~1.5M
- **Taxonomic ranks**: 47 different ranks
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Graph**: http://rdfportal.org/ontology/taxonomy
- **Base URI**: http://identifiers.org/taxonomy/

## Key Entities (Verified)
| Taxonomy ID | Label | Rank | Common Name |
|-------------|-------|------|-------------|
| 9606 | Homo sapiens | Species | human |
| 10090 | Mus musculus | Species | mouse |
| 561 | Escherichia | Genus | - |
| 33208 | Metazoa | Kingdom | animals |

## Search Tools

### ncbi_esearch (RECOMMENDED for Discovery)
```python
ncbi_esearch(database='taxonomy', query='Escherichia coli')
# Returns: Taxonomy IDs
```

### SPARQL for Detailed Queries

#### Search Taxa by Name
```sparql
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?taxon ?id ?label
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  ?taxon a tax:Taxon ;
    rdfs:label ?label ;
    dcterms:identifier ?id .
  ?label bif:contains "'mouse'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
```

#### Get Taxa Details
```sparql
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX taxon: <http://identifiers.org/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?label ?id ?rank ?scientificName ?commonName ?geneticCode
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  VALUES ?taxon { taxon:9606 taxon:10090 }
  ?taxon a tax:Taxon ;
    rdfs:label ?label ;
    dcterms:identifier ?id ;
    tax:rank ?rank .
  OPTIONAL { ?taxon tax:scientificName ?scientificName }
  OPTIONAL { ?taxon tax:commonName ?commonName }
  OPTIONAL { ?taxon tax:geneticCode ?geneticCode }
}
```

#### Get Complete Lineage
```sparql
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX taxon: <http://identifiers.org/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?ancestor ?rank ?label ?id
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  taxon:9606 rdfs:subClassOf* ?ancestor .
  ?ancestor a tax:Taxon ;
    tax:rank ?rank ;
    rdfs:label ?label ;
    dcterms:identifier ?id .
}
ORDER BY DESC(?id)
```

#### Find Species in Genus
```sparql
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?species ?label ?id
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  ?species a tax:Taxon ;
    rdfs:label ?label ;
    dcterms:identifier ?id ;
    tax:rank tax:Species ;
    rdfs:subClassOf ?genus .
  ?genus rdfs:label "Escherichia" ;
    tax:rank tax:Genus .
}
LIMIT 20
```

## Schema Notes

### Key Properties
| Property | Description |
|----------|-------------|
| rdfs:label | Organism name |
| dcterms:identifier | Taxonomy ID |
| tax:rank | Taxonomic rank (Species, Genus, Family, etc.) |
| tax:scientificName | Scientific name |
| tax:commonName | Common name(s) |
| tax:authority | Naming authority |
| tax:geneticCode | Nuclear genetic code |
| tax:geneticCodeMt | Mitochondrial genetic code |
| rdfs:subClassOf | Parent taxon |

### Taxonomic Ranks
Major ranks: Superkingdom, Kingdom, Phylum, Class, Order, Family, Genus, Species, Strain

### Cross-References
| Pattern | Description | Coverage |
|---------|-------------|----------|
| owl:sameAs | OBO NCBITaxon, DDBJ | ~100% |
| rdfs:seeAlso | UniProt Taxonomy | ~100% |

## Critical Patterns

### ALWAYS
- Include `FROM <http://rdfportal.org/ontology/taxonomy>`
- Use `bif:contains` for text search
- Start transitive queries from specific taxon IDs
- Add LIMIT (2.7M+ taxa)

### NEVER
- Run unbounded rdfs:subClassOf* queries
- Use FILTER(CONTAINS()) for keyword search
- Query all species without LIMIT

## Anti-Patterns

### ❌ Unbounded Lineage Query
```sparql
SELECT ?ancestor WHERE {
  ?taxon rdfs:subClassOf* ?ancestor
}
```

### ✅ Bounded from Specific Taxon
```sparql
SELECT ?ancestor
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  taxon:9606 rdfs:subClassOf* ?ancestor .
}
LIMIT 50
```

## Question Opportunities
1. **Precision**: "What is the taxonomy ID for Homo sapiens?" → 9606
2. **Counting**: "How many taxa in the NCBI Taxonomy?" → 2,698,386
3. **Hierarchy**: "What is the lineage of humans?"
4. **Search**: "Find all taxa with 'coli' in the name"
5. **Genus content**: "How many species in genus Escherichia?"
6. **Cross-ref**: "What is the UniProt Taxonomy link for ID 9606?"
