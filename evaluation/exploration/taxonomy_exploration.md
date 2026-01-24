# NCBI Taxonomy Exploration Report

## Database Overview
- **Purpose**: Comprehensive biological taxonomic classification covering organisms from bacteria to mammals
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Graph**: `http://rdfportal.org/ontology/taxonomy`
- **Key Features**: Hierarchical relationships, scientific/common names, genetic code assignments, cross-references
- **Search Tool**: ncbi_esearch (taxonomy database)
- **Data Version**: 2024

## Schema Analysis (from MIE file)
### Main Entities
- **Taxon**: Core taxonomic entity with hierarchical classification
- **Rank**: Taxonomic rank (Species, Genus, Family, Order, etc.)
- **GeneticCode**: Genetic code assignments for translation

### Important Properties
- `rdfs:label`: Organism name
- `dcterms:identifier`: NCBI Taxonomy ID (TaxID)
- `tax:rank`: Taxonomic rank (Species, Genus, etc.)
- `rdfs:subClassOf`: Parent taxon in hierarchy
- `tax:scientificName`: Full scientific name with authority
- `tax:commonName`: Common/vernacular names (multiple)
- `tax:geneticCode`: Nuclear genetic code
- `tax:geneticCodeMt`: Mitochondrial genetic code
- `owl:sameAs`: Cross-references to ontology systems
- `rdfs:seeAlso`: Links to UniProt Taxonomy

### Query Patterns
- Use `bif:contains` for name searches with relevance scoring
- Use `rdfs:subClassOf*` for lineage traversal (start from specific taxa)
- Always add LIMIT clauses (3M+ taxa in database)
- Filter by `tax:rank` for improved performance

## Search Queries Performed

### 1. Model organism lookups
```
Query: Homo sapiens → TaxID: 9606
Query: Mus musculus → TaxID: 10090
Query: Drosophila melanogaster → TaxID: 7227
Query: Caenorhabditis elegans → TaxID: 6239
Query: Arabidopsis thaliana → TaxID: 3702
```

### 2. Pathogenic bacteria
```
Query: Streptococcus pyogenes → TaxID: 1314
```

### 3. SARS-CoV-2 (COVID-19 virus)
```
Query: SARS-CoV-2 in SPARQL → Found TaxID: 2697049
Full name: "Severe acute respiratory syndrome coronavirus 2"
Parent species: Betacoronavirus pandemicum (TaxID: 3418604)
```

## SPARQL Queries Tested

### Query 1: Model organism biological annotations
```sparql
SELECT ?label ?id ?rank ?scientificName ?commonName ?geneticCode
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  VALUES ?taxon { taxon:9606 taxon:10090 taxon:7227 taxon:6239 taxon:3702 }
  ?taxon a tax:Taxon ;
    rdfs:label ?label ;
    dcterms:identifier ?id ;
    tax:rank ?rank .
  OPTIONAL { ?taxon tax:scientificName ?scientificName }
  OPTIONAL { ?taxon tax:commonName ?commonName }
  OPTIONAL { ?taxon tax:geneticCode ?geneticCode }
}
# Results: All model organisms found with Species rank, GeneticCode1
# Common names: mouse (Mus musculus), mouse-ear cress/thale-cress (Arabidopsis)
```

### Query 2: Complete human lineage
```sparql
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
# Results: 32 ancestors from root (1) to species
# Key ranks: Kingdom (Metazoa), Phylum (Chordata), Class (Mammalia), 
#            Order (Primates), Family (Hominidae), Genus (Homo), Species
```

### Query 3: Total taxa and species counts
```sparql
SELECT (COUNT(DISTINCT ?taxon) as ?total_taxa)
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE { ?taxon a tax:Taxon . }
# Results: 2,698,386 total taxa
```

### Query 4: Distribution by taxonomic rank
```sparql
SELECT ?rank (COUNT(?taxon) as ?count)
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  ?taxon a tax:Taxon ;
    tax:rank ?rank .
}
GROUP BY ?rank ORDER BY DESC(?count)
# Results: Top ranks:
# Species: 2,214,294
# NoRank: 253,143
# Genus: 113,635
# Strain: 46,887
# Subspecies: 30,646
# 45 distinct taxonomic ranks total
```

### Query 5: Genera with most species
```sparql
SELECT ?genus_label (COUNT(?species) AS ?count)
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  ?species a tax:Taxon ;
    tax:rank tax:Species ;
    rdfs:subClassOf ?genus .
  ?genus tax:rank tax:Genus ;
    rdfs:label ?genus_label .
}
GROUP BY ?genus_label ORDER BY DESC(?count)
# Results: Top genera by species count:
# Cortinarius: 2,030 (mushroom genus)
# Astragalus: 1,580 (plant genus)
# Megaselia: 1,308 (fly genus)
# Inocybe: 1,231 (mushroom)
# Streptomyces: 1,141 (bacteria)
```

### Query 6: Escherichia species
```sparql
SELECT ?species ?label ?id
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  ?species a tax:Taxon ;
    tax:rank tax:Species ;
    rdfs:subClassOf ?genus .
  ?genus rdfs:label "Escherichia" ;
    tax:rank tax:Genus .
}
# Results: 10 Escherichia species including:
# E. coli (562), E. albertii (208962), E. fergusonii (564),
# E. marmotae (1499973), E. ruysiae (2608867), E. senegalensis (223381)
```

### Query 7: SARS-CoV-2 lineage
```sparql
SELECT ?ancestor ?rank ?label ?id
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  taxon:2697049 rdfs:subClassOf* ?ancestor .
  ?ancestor a tax:Taxon ;
    tax:rank ?rank ;
    rdfs:label ?label .
}
# Results: Full viral taxonomy:
# Viruses → Riboviria → Orthornavirae (Kingdom) → Pisuviricota (Phylum) →
# Pisoniviricetes (Class) → Nidovirales (Order) → Coronaviridae (Family) →
# Orthocoronavirinae (Subfamily) → Betacoronavirus (Genus) → 
# Sarbecovirus (Subgenus) → Betacoronavirus pandemicum (Species) →
# SARS-CoV-2 (NoRank)
```

## Cross-Reference Analysis

### Entity Counts (owl:sameAs cross-references)
- ~100% of taxa have owl:sameAs links (5 per taxon on average)
- Linked to: OBO NCBITaxon, Berkeley BOP, DDBJ, NCBI Web

### Relationship Patterns
| Property | Target | Coverage |
|----------|--------|----------|
| owl:sameAs | OBO NCBITaxon | ~100% |
| owl:sameAs | Berkeley BOP | ~100% |
| owl:sameAs | DDBJ Taxonomy | ~100% |
| owl:sameAs | NCBI Web | ~100% |
| rdfs:seeAlso | UniProt Taxonomy | ~100% |

### Cross-Database Integration
- **Shared endpoint** (primary): mesh, go, mondo, nando, bacdive, mediadive
- Keyword-based integration using bif:contains across graphs

## Interesting Findings

**Findings requiring actual database queries:**

1. **2,698,386 total taxa** in NCBI Taxonomy RDF - verified via COUNT query

2. **2,214,294 species** - Species is by far the most common rank (82% of all taxa)

3. **45 distinct taxonomic ranks** including standard Linnaean ranks plus Clade, Strain, Serotype, etc.

4. **Genus diversity**: Cortinarius (mushrooms) is the most species-rich genus with 2,030 species

5. **Human lineage has 32 hierarchical levels** from root to species, including 7 major Linnaean ranks

6. **Model organisms confirmed**: All major model organisms found with correct TaxIDs:
   - Human: 9606
   - Mouse: 10090
   - Fruit fly: 7227
   - C. elegans: 6239
   - Arabidopsis: 3702

7. **SARS-CoV-2 taxonomy** (TaxID 2697049): Classified under Betacoronavirus pandemicum (species), Sarbecovirus (subgenus), Coronaviridae (family)

8. **Escherichia genus** contains 10 species including E. coli (562), E. albertii (208962), E. fergusonii (564)

9. **Genetic codes**: Most eukaryotes use GeneticCode1 (standard); bacteria/viruses use GeneticCode11

10. **Common names available**: ~30% of taxa have common names, higher for vertebrates (e.g., mouse, thale-cress)

## Question Opportunities by Category

### Precision
- "What is the NCBI Taxonomy ID for Homo sapiens?" → 9606
- "What is the NCBI Taxonomy ID for SARS-CoV-2?" → 2697049
- "What is the scientific name for TaxID 562?" → Escherichia coli
- "What is the genus for Streptococcus pyogenes (TaxID 1314)?" → Streptococcus

### Completeness
- "How many total taxa are in NCBI Taxonomy?" → 2,698,386
- "How many species are in NCBI Taxonomy?" → 2,214,294
- "How many taxonomic ranks are used in NCBI Taxonomy?" → 45
- "How many species are in the Escherichia genus?" → 10

### Integration
- "What is the OBO NCBITaxon URI for human?" → obo:NCBITaxon_9606
- "What is the UniProt Taxonomy link for mouse?" → purl.uniprot.org/taxonomy/10090
- "Convert TaxID 7227 to Berkeley BOP ontology format" → berkeleybop.org/...#7227

### Currency
- "Is SARS-CoV-2 classified in NCBI Taxonomy?" → Yes, TaxID 2697049
- "What is the current species classification for SARS-CoV-2?" → Betacoronavirus pandemicum

### Specificity
- "What genus has the most species in NCBI Taxonomy?" → Cortinarius (2,030 species)
- "How many ancestors does human have in the taxonomic hierarchy?" → 32
- "What is the taxonomic rank of SARS-CoV-2?" → NoRank (subspecies-level isolate)

### Structured Query
- "Find all species in the Escherichia genus" → 10 species including E. coli
- "Get the complete lineage for human from root to species" → 32 taxa
- "Find organisms using non-standard genetic codes" → Ciliates (GeneticCode6), bacteria/viruses (GeneticCode11)

## Notes
- **Performance**: Always use FROM clause and LIMIT; bif:contains for name searches
- **Hierarchy**: rdfs:subClassOf* traversal is expensive; start from specific taxa
- **Ranks**: tax:rank filtering significantly improves performance
- **Names**: Scientific names >99% complete; common names ~30%
- **Cross-references**: 5 owl:sameAs links per taxon on average
- **Shared endpoint**: Can integrate with GO, MONDO, MeSH, BacDive via keyword matching
- **Critical for integration**: Taxonomy IDs are used across all biological databases (UniProt, NCBI Gene, etc.)
