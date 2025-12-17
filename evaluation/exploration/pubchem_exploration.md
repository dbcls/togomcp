# PubChem Exploration Report

## Database Overview
- **Purpose**: Comprehensive public database of chemical molecules and biological activities
- **Scope**: 119M compounds, 339M substances, 1.7M bioassays, 167K genes, 249K proteins, 81K pathways
- **Key data types**: Compounds with molecular descriptors, bioactivity data, FDA drug classifications, stereoisomer relationships, patent references

## Schema Analysis (from MIE file)

### Main Properties Available
- **Molecular descriptors** (via SIO ontology):
  - `sio:CHEMINF_000335` - Molecular formula
  - `sio:CHEMINF_000334` - Molecular weight
  - `sio:CHEMINF_000376` - Canonical SMILES
  - `sio:CHEMINF_000396` - InChI
  - 25 average descriptors per compound

- **Drug classifications**:
  - `obo:RO_0000087` - Biological roles (17,367 FDA-approved drugs)
  - `rdf:type` - Ontology classifications (ChEBI ~5%, SNOMED CT for drugs)

- **Relationships**:
  - `cheminf:CHEMINF_000455` - Stereoisomer relationships (avg 2.3 per compound)
  - `vocab:is_standardized_into` - Substance-to-compound mappings
  - `pdbx:link_to_pdb` - Protein-to-PDB links

- **External references**:
  - `rdfs:seeAlso` - Wikidata (~2%), identifiers.org
  - `cito:isDiscussedBy` - Patents (~10% coverage) from US, EP, CN, CA, JP, KR

### Important Relationships
- **Central hub model**: Compounds linked to substances, bioassays, genes, proteins, pathways
- **Descriptor pattern**: `sio:SIO_000008` links to descriptors → `sio:SIO_000300` for values
- **Multi-layer architecture**: Separate named graphs per entity type (compound, substance, bioassay, gene, protein, pathway)
- **Cross-database integration**: ChEBI, SNOMED CT, NCI Thesaurus, Protein Ontology

### Query Patterns Observed
- CID-specific queries very efficient (<1s)
- Weight range filtering works up to 10K results
- Descriptor queries need type filtering for efficiency
- Bioassay queries require explicit FROM clauses
- Aggregations with GROUP BY must use LIMIT <100

## Search Queries Performed

1. **Query**: aspirin → **Results**: CID2244 with molecular formula C9H8O4, MW 180.16
2. **Query**: ibuprofen → **Results**: CID3672 with molecular formula C13H18O2, MW 206.28
3. **Query**: paclitaxel → **Results**: CID36314 (cancer drug)
4. **Query**: caffeine → **Results**: CID2519 (stimulant)
5. **Query**: resveratrol → **Results**: CID445154 with molecular formula C14H12O3, MW 228.24

## SPARQL Queries Tested

```sparql
# Query 1: Get molecular descriptors for aspirin
PREFIX compound: <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/>
PREFIX sio: <http://semanticscience.org/resource/>

SELECT ?descriptorType ?value
WHERE {
  compound:CID2244 sio:SIO_000008 ?descriptor .
  ?descriptor a ?descriptorType ;
              sio:SIO_000300 ?value .
  FILTER(?descriptorType IN (
    sio:CHEMINF_000335,
    sio:CHEMINF_000334,
    sio:CHEMINF_000376,
    sio:CHEMINF_000396
  ))
}
# Results: Successfully retrieved SMILES (CC(=O)OC1=CC=CC=C1C(=O)O), InChI, molecular formula (C9H8O4), and molecular weight (180.16)
```

```sparql
# Query 2: Find FDA-approved drugs by molecular weight range
PREFIX vocab: <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX sio: <http://semanticscience.org/resource/>

SELECT ?compound ?weight
WHERE {
  ?compound a vocab:Compound ;
            obo:RO_0000087 vocab:FDAApprovedDrugs ;
            sio:SIO_000008 ?weightDesc .
  ?weightDesc a sio:CHEMINF_000334 ;
              sio:SIO_000300 ?weight .
  FILTER(?weight >= 150 && ?weight <= 200)
}
LIMIT 20
# Results: Found 20 FDA-approved drugs in weight range, including CID440545 (180.16), CID2723 (156.61), CID3518 (198.31)
```

```sparql
# Query 3: Find stereoisomers of aspirin
PREFIX compound: <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/>
PREFIX cheminf: <http://semanticscience.org/resource/>
PREFIX sio: <http://semanticscience.org/resource/>

SELECT ?stereoisomer ?smiles
WHERE {
  compound:CID2244 cheminf:CHEMINF_000455 ?stereoisomer .
  ?stereoisomer sio:SIO_000008 ?smilesDesc .
  ?smilesDesc a sio:CHEMINF_000376 ;
              sio:SIO_000300 ?smiles .
}
LIMIT 10
# Results: Found 10 stereoisomer CIDs (CID102100677-CID71309054), all with same SMILES for aspirin (achiral)
```

```sparql
# Query 4: List bioassays from DTP_NCI source
PREFIX vocab: <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#>
PREFIX source: <http://rdf.ncbi.nlm.nih.gov/pubchem/source/>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?bioassay ?title ?aid
FROM <http://rdf.ncbi.nlm.nih.gov/pubchem/bioassay>
WHERE {
  ?bioassay a vocab:BioAssay ;
            dcterms:source source:DTP_NCI ;
            dcterms:title ?title ;
            dcterms:identifier ?aid .
}
LIMIT 10
# Results: Retrieved NCI tumor cell line growth inhibition assays (AID1-115) for various cell lines (lung, ovarian, leukemia)
```

## Interesting Findings

### Specific Entities That Could Form Good Questions
- **Well-known drugs**: Aspirin (CID2244), Ibuprofen (CID3672), Paclitaxel (CID36314), Caffeine (CID2519)
- **Natural products**: Resveratrol (CID445154) with precise MW and stereochemistry
- **FDA-approved drugs**: 17,367 total, filterable by molecular weight and properties
- **Bioassays**: 1.7M total, including NCI cancer screening data

### Unique Properties or Patterns
- **Comprehensive molecular descriptors**: >99% coverage for formula, weight, SMILES, >95% for InChI
- **Stereoisomer tracking**: Average 2.3 stereoisomers per compound with CHEMINF_000455
- **Multi-jurisdictional patents**: ~10% compounds have patent refs from 6 jurisdictions (US, EP, CN, CA, JP, KR)
- **Named graphs architecture**: Separate graphs for compound, substance, bioassay, gene, protein, pathway
- **Ontology integration**: ChEBI (~5%), SNOMED CT, NCI Thesaurus classifications via rdf:type

### Connections to Other Databases
- **ChEBI**: ~5-10% compounds have ChEBI classifications
- **Wikidata**: ~2% compounds linked via rdfs:seeAlso
- **UniProt**: Protein entities with UniProt cross-references
- **PDB**: Proteins link to PDB structures via pdbx:link_to_pdb
- **NCBI Protein**: Via identifiers.org
- **Gene Ontology**: Functional annotations for genes

### Specific, Verifiable Facts
- **Aspirin (CID2244)**: Molecular formula C9H8O4, MW 180.16, SMILES "CC(=O)OC1=CC=CC=C1C(=O)O"
- **17,367 FDA-approved drugs** with explicit vocab:FDAApprovedDrugs classification
- **1.7M bioassays** including systematic NCI cancer screening (AID series)
- **25 average descriptors per compound** providing comprehensive chemical characterization
- **119M compounds** total with >99% molecular formula coverage

## Question Opportunities by Category

### Precision
- "What is the molecular weight of PubChem compound CID2244 (aspirin)?" (Answer: 180.16)
- "What is the canonical SMILES for resveratrol (CID445154)?" (Answer: C1=CC(=CC=C1C=CC2=CC(=CC(=C2)O)O)O)
- "What is the InChI identifier for caffeine in PubChem?" (CID2519)
- "How many FDA-approved drugs are in PubChem?" (Answer: 17,367)

### Completeness
- "List all stereoisomers of ibuprofen in PubChem" (uses CHEMINF_000455)
- "How many bioassays from the DTP_NCI source are in PubChem?" 
- "What molecular descriptors are available for a specific compound?"
- "How many compounds have ChEBI classifications?"

### Integration
- "Find the ChEBI identifier for aspirin in PubChem" (via rdf:type)
- "What PDB structures are linked to PubChem proteins?" (via pdbx:link_to_pdb)
- "Convert PubChem CID to Wikidata identifier" (via rdfs:seeAlso)
- "What patents reference compound CID36314 (paclitaxel)?" (via cito:isDiscussedBy)

### Currency
- "What are the most recently added FDA-approved drugs?" (17,367 total, continuously updated)
- "Which bioassays have been added in the last year?"
- "What new stereoisomer relationships have been identified?"

### Specificity
- "What is the molecular formula of the polyphenol resveratrol?" (C14H12O3)
- "Which NCI bioassay tests the OVCAR-8 ovarian cancer cell line?" (AID109)
- "What is the molecular weight range of FDA-approved anticoagulants?"
- "What proteins in PubChem link to the PDB structure 10GS?"

### Structured Query
- "Find all FDA-approved drugs with molecular weight between 150 and 200" (efficient filtering)
- "List compounds with more than 5 stereoisomers"
- "Find bioassays measuring kinase inhibition"
- "Retrieve compounds with both ChEBI and SNOMED CT classifications"

## Notes

### Limitations or Challenges
- **Query timeouts**: Aggregations without LIMIT and type filtering can timeout
- **Mixed datatypes**: Descriptor values stored as different types (string/double/integer)
- **Named graph requirement**: Bioassay/protein queries need explicit FROM clauses
- **Incomplete coverage**: External links vary (2-95% by database), ontology mappings primarily for drugs
- **Large scale**: 119M compounds require careful query construction

### Best Practices for Querying
1. **Always use LIMIT** for exploratory queries (50-100)
2. **Filter by descriptor type** before retrieving values: `FILTER(?descriptorType IN (...))`
3. **Use FROM clauses** for bioassay/protein/pathway queries
4. **CID-specific queries** are very efficient - use when possible
5. **Add type filters** for aggregations: `?compound a vocab:Compound`
6. **Namespace filtering** for ontology classes: `FILTER(STRSTARTS(STR(?class), STR(chebi:)))`
7. **Weight range queries** work well up to 10K results
8. **Use ORDER BY DESC** for meaningful aggregation results

### Anti-patterns to Avoid
- ❌ GROUP BY without LIMIT on all compounds (timeout)
- ❌ Retrieving all descriptors without type filter (too many results)
- ❌ Bioassay queries without FROM clause (empty results)
- ❌ Comparing descriptor values without checking type first (datatype errors)
- ❌ Large aggregations without namespace filtering (timeout)
