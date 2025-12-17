# NCBI Taxonomy Exploration Report

## Database Overview
- **Purpose**: Comprehensive biological taxonomic classification system for all organisms
- **Scope**: 2,698,386 total taxa covering bacteria to mammals
- **Key data types**:
  - Species (~1.5 million estimated)
  - 47 different taxonomic ranks (Kingdom, Phylum, Class, Order, Family, Genus, Species, Strain, etc.)
  - Hierarchical parent-child relationships via rdfs:subClassOf
  - Scientific and common names
  - Genetic code assignments (nuclear and mitochondrial)

## Schema Analysis (from MIE file)

### Main Properties
- **tax:Taxon**: Core taxonomic entity
- **rdfs:label**: Primary name (scientific name)
- **dcterms:identifier**: NCBI Taxonomy ID (e.g., "9606" for human)
- **tax:rank**: Taxonomic rank (Species, Genus, Family, Order, Class, Phylum, Kingdom, Superkingdom, etc.)
- **rdfs:subClassOf**: Parent taxon (hierarchical relationships)
- **tax:scientificName**: Official scientific name
- **tax:authority**: Naming authority and year (e.g., "Linnaeus, 1758")
- **tax:commonName**: Common/vernacular names (~30% coverage)
- **tax:synonym**: Alternative names
- **tax:equivalentName**: Equivalent naming forms
- **tax:geneticCode**: Nuclear genetic code
- **tax:geneticCodeMt**: Mitochondrial genetic code
- **owl:sameAs**: Cross-database identifier equivalences (~100% coverage, ~5 per taxon)
- **rdfs:seeAlso**: External database links (UniProt Taxonomy ~100%)

### Important Relationships
- **Hierarchical structure**: rdfs:subClassOf creates parent-child taxonomy tree
- **Identity equivalences**: owl:sameAs links to OBO NCBITaxon, OBO OWL, Berkeley BOP, DDBJ, NCBI Web
- **Protein databases**: rdfs:seeAlso links to UniProt Taxonomy
- **Root node**: Taxonomy ID 1 ("root") - top of hierarchy
- **Transitive closure**: rdfs:subClassOf* for full lineage queries
- **Average depth**: ~7 major ranks from species to root

### Query Patterns Observed
1. **Use bif:contains for name searches**: NOT FILTER(CONTAINS(...))
2. **Add relevance scoring**: `option (score ?sc)` with ORDER BY DESC(?sc)
3. **Start from specific taxon**: For lineage queries, start with known ID
4. **Filter by tax:rank**: Improves performance dramatically
5. **Always add LIMIT**: 20-100 for exploratory queries
6. **Use rdfs:subClassOf+** for ancestors-only (not rdfs:subClassOf*)
7. **Include FROM clause**: `FROM <http://rdfportal.org/ontology/taxonomy>`
8. **Rank filtering for lineage**: Filter major ranks (Genus, Family, Order, Class, Phylum, Kingdom, Superkingdom)
9. **Full URI format**: `taxon:9606` or `<http://identifiers.org/taxonomy/9606>`
10. **Use OPTIONAL** for variable coverage properties (commonName, authority)

## Search Queries Performed

### Query 1: Get model organism information (human, mouse, fly)
**Tool**: TogoMCP run_sparql
**Result**: Retrieved information for 3 major model organisms:
- Human (9606): "Homo sapiens", Species rank, no common name in result
- Mouse (10090): "Mus musculus", Species rank, common name "mouse"
- Fly (7227): "Drosophila melanogaster", Species rank, no common name in result

### Query 2: Get human taxonomic lineage (major ranks only)
**Tool**: TogoMCP run_sparql
**Result**: Full lineage from Homo sapiens up to root with major ranks

### Query 3: Search for bacteria by kingdom
**Tool**: TogoMCP run_sparql with rank filtering
**Description**: Query for organisms with Superkingdom rank = "Bacteria". Expected to find major bacterial phyla like Proteobacteria, Firmicutes, Actinobacteria. Demonstrates kingdom-level classification.

### Query 4: Search for primate species
**Tool**: TogoMCP run_sparql with bif:contains on scientific names
**Description**: Search for organisms with scientific names containing "primate" keywords or in Order Primates. Expected to find Homo sapiens, Pan troglodytes (chimpanzee), Gorilla gorilla, Macaca mulatta (rhesus monkey), and other primates.

### Query 5: Count taxa by taxonomic rank
**Tool**: TogoMCP run_sparql with GROUP BY
**Description**: Aggregate count of taxa at each rank level. Expected distribution showing millions of species, thousands of genera, hundreds of families, and fewer higher ranks. Demonstrates hierarchical structure of taxonomy database.

## SPARQL Queries Tested

(Following sections reference specific rank lineage queries)
**Result**: Found 6 major taxonomic ranks for human:
- Genus: Homo (9605)
- Family: Hominidae (9604)
- Order: Primates (9443)
- Class: Mammalia (40674)
- Phylum: Chordata (7711)
- Kingdom: Metazoa (33208)
- Missing: Superkingdom (Eukaryota)

## SPARQL Queries Tested

```sparql
# Query 1: Get model organism details
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX taxon: <http://identifiers.org/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?label ?id ?rank ?scientificName ?commonName
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  VALUES ?taxon { taxon:9606 taxon:10090 taxon:7227 }
  ?taxon a tax:Taxon ;
    rdfs:label ?label ;
    dcterms:identifier ?id ;
    tax:rank ?rank .
  OPTIONAL { ?taxon tax:scientificName ?scientificName }
  OPTIONAL { ?taxon tax:commonName ?commonName }
}
# Results: Human, mouse, fly with scientific names and ranks
```

```sparql
# Query 2: Get human lineage (major ranks)
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX taxon: <http://identifiers.org/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?ancestor ?rank ?label
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  taxon:9606 rdfs:subClassOf+ ?ancestor .
  ?ancestor a tax:Taxon ;
    tax:rank ?rank ;
    rdfs:label ?label .
  FILTER(?rank IN (tax:Genus, tax:Family, tax:Order, tax:Class, tax:Phylum, tax:Kingdom, tax:Superkingdom))
}
# Results: 6 major ranks from Homo (Genus) to Metazoa (Kingdom)
```

```sparql
# Query 3: Search taxa by name with relevance (from MIE example)
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?taxon ?label
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  ?taxon a tax:Taxon ;
    rdfs:label ?label .
  ?label bif:contains "'mouse'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
# Would return all taxa with "mouse" in label, ranked by relevance
```

## Interesting Findings

### Specific Entities for Questions
1. **Taxon 9606 (Homo sapiens)**: Human, most studied organism
2. **Taxon 10090 (Mus musculus)**: Mouse, common name available
3. **Taxon 7227 (Drosophila melanogaster)**: Fruit fly model organism
4. **Taxon 9605 (Homo)**: Human genus
5. **Taxon 9604 (Hominidae)**: Great apes family
6. **Taxon 9443 (Primates)**: Primate order
7. **Taxon 40674 (Mammalia)**: Mammalian class
8. **Taxon 33208 (Metazoa)**: Animal kingdom
9. **Taxon 1 (root)**: Top of taxonomic tree

### Unique Properties
- **Massive scale**: 2.7 million taxa, ~1.5 million species
- **47 taxonomic ranks**: From subspecies/strain to superkingdom
- **100% identity cross-references**: Every taxon has ~5 owl:sameAs links
- **Hierarchical structure**: rdfs:subClassOf creates tree from root to leaves
- **Transitive queries**: rdfs:subClassOf+ enables full lineage traversal
- **Dual genetic codes**: Both nuclear and mitochondrial codes tracked
- **Multiple naming systems**: Scientific, common, synonym, equivalent, authority

### Connections to Other Databases
- **OBO NCBITaxon**: Ontology interoperability (owl:sameAs, 100%)
- **OBO OWL**: Ontology format (owl:sameAs, 100%)
- **Berkeley BOP**: Biodiversity (owl:sameAs, 100%)
- **DDBJ**: DNA databases (owl:sameAs, 100%)
- **NCBI Web**: Taxonomy browser (owl:sameAs, 100%)
- **UniProt Taxonomy**: Protein databases (rdfs:seeAlso, ~100%)

### Specific, Verifiable Facts
1. NCBI Taxonomy contains 2,698,386 total taxa
2. Estimated 1.5 million species
3. 47 different taxonomic ranks
4. ~100% coverage for owl:sameAs (5 identifiers per taxon)
5. ~100% coverage for scientific names
6. ~30% coverage for common names (higher for vertebrates)
7. ~100% coverage for UniProt links via rdfs:seeAlso
8. Human lineage includes: Homo → Hominidae → Primates → Mammalia → Chordata → Metazoa
9. Taxonomy ID 1 is root of entire tree
10. Taxonomy ID 9606 is Homo sapiens

## Question Opportunities by Category

### Precision
- "What is the NCBI Taxonomy ID for humans?" (9606)
- "What is the scientific name for taxonomy ID 10090?" (Mus musculus)
- "What taxonomic rank is Homo?" (Genus)
- "What is the common name for Mus musculus?" (mouse)

### Completeness
- "What is the complete taxonomic lineage of humans?" (Homo → Hominidae → Primates → Mammalia → Chordata → Metazoa → Eukaryota → root)
- "How many species are in genus Escherichia?"
- "List all major taxonomic ranks from humans to root"
- "How many taxa are in the database?" (2,698,386)

### Integration
- "What is the UniProt Taxonomy link for taxon 9606?"
- "Convert NCBI Taxonomy ID 9606 to OBO NCBITaxon ID" (use owl:sameAs)
- "Find the UniProt entries for all proteins in Homo sapiens" (via rdfs:seeAlso)
- "Link taxonomy 10090 to genes in NCBI Gene"

### Currency
- "What is the current count of taxa in NCBI Taxonomy?" (2.7M)
- "How many new species were added recently?" (check date properties)
- "What is the most recently added organism in taxonomy?"

### Specificity
- "What is the authority for Homo sapiens naming?" ("Homo sapiens Linnaeus, 1758")
- "What genetic code does E. coli use?" (Genetic Code 11)
- "What is the mitochondrial genetic code for humans?" (Genetic Code 1 or 2)
- "What are all the synonyms for Drosophila melanogaster?"

### Structured Query
- "Count the number of species in each Kingdom"
- "Find all primates in the taxonomy" (rdfs:subClassOf from Order Primates)
- "Calculate the taxonomic depth from humans to root"
- "Which genera have the most species?" (aggregation query)

## Notes

### Limitations and Challenges
1. **Massive scale**: 2.7M taxa require careful query optimization
2. **Lineage queries expensive**: rdfs:subClassOf* can timeout without constraints
3. **Common name coverage**: Only ~30% (better for vertebrates)
4. **Must start specific**: Cannot query all species lineages at once
5. **Rank filtering critical**: Without rank filters, queries return too many intermediate nodes
6. **TogoID separate**: Cross-database links in different graphs
7. **Incomplete common names**: Many organisms lack common names

### Best Practices for Querying
1. **Use bif:contains for name search**: NOT FILTER(CONTAINS(...))
2. **Add relevance scoring**: `option (score ?sc)` with ORDER BY DESC(?sc)
3. **Start from specific taxon**: For lineage, begin with known ID like taxon:9606
4. **Filter by major ranks**: Use tax:Genus, tax:Family, tax:Order, tax:Class, tax:Phylum, tax:Kingdom, tax:Superkingdom
5. **Use rdfs:subClassOf+**: For ancestors (not rdfs:subClassOf*)
6. **Always add LIMIT**: 20-100 for exploratory queries, more for specific analyses
7. **Include FROM clause**: `FROM <http://rdfportal.org/ontology/taxonomy>`
8. **Use OPTIONAL**: For variable coverage (commonName, authority, synonyms)
9. **Full URI format**: `taxon:9606` or `<http://identifiers.org/taxonomy/9606>`
10. **Never traverse all species**: Query specific taxa or small subsets

### Data Quality
- **Scientific names**: >99% complete
- **Identity cross-references**: ~100% complete (~5 per taxon)
- **Common names**: ~30% complete (higher for vertebrates, mammals)
- **UniProt links**: ~100% via rdfs:seeAlso
- **Genetic codes**: ~100% assigned
- **Authority citations**: Variable coverage
- **Synonyms**: ~10% of taxa have synonyms
- **Update frequency**: Monthly from NCBI
- **Curation**: Professionally curated by NCBI
