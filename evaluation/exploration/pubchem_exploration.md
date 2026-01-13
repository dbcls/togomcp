# PubChem Exploration Report

## Database Overview
- **Purpose**: Comprehensive public database of chemical molecules and biological activities
- **Scope**: Central hub linking compounds to genes, proteins, pathways, diseases, and literature
- **Key entities**: Compounds (119M), Substances (339M), BioAssays (1.7M), Genes (167K), Proteins (249K), Pathways (81K)
- **Data quality**: Molecular formula, weight, SMILES available for >99% of compounds

## Schema Analysis (from MIE file)

### Main Properties
- `vocab:Compound`: Central entity for chemical compounds
- `sio:SIO_000008`: Links compounds to molecular descriptors
- `sio:SIO_000300`: Holds descriptor values
- `obo:RO_0000087`: Biological roles (e.g., FDA-approved drugs)
- `cheminf:CHEMINF_000455`: Stereoisomer relationships
- `cito:isDiscussedBy`: Patent and literature references
- `vocab:is_active_ingredient_of`: Drug product links

### Important Descriptor Types
- `sio:CHEMINF_000335`: Molecular formula
- `sio:CHEMINF_000334`: Molecular weight
- `sio:CHEMINF_000376`: Canonical SMILES
- `sio:CHEMINF_000396`: InChI

### Query Patterns
- Use CID-based queries for efficient lookup
- Filter by descriptor type for specific properties
- Use FROM clause for bioassay/protein graphs
- LIMIT aggregations to 50-100 results

## Search Queries Performed

1. **Query**: get_pubchem_compound_id("aspirin")
   - Results: CID 2244
   - Molecular formula: C9H8O4, Weight: 180.16

2. **Query**: get_pubchem_compound_id("imatinib")
   - Results: CID 5291
   - Molecular formula: C29H31N7O, Weight: 493.6

3. **Query**: get_pubchem_compound_id("rapamycin")
   - Results: CID 5284616

4. **Query**: get_pubchem_compound_id("caffeine")
   - Results: CID 2519
   - Molecular formula: C8H10N4O2, Weight: 194.19

5. **Query**: get_compound_attributes_from_pubchem("2519")
   - Results: Full molecular descriptors including SMILES, InChI, molecular weight

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
# Results: Formula C9H8O4, Weight 180.16, SMILES, InChI
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
LIMIT 30
# Results: 30 FDA drugs including caffeine (CID1676, 194.19), etc.
```

```sparql
# Query 3: Count FDA-approved drugs in PubChem
PREFIX vocab: <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT (COUNT(DISTINCT ?compound) as ?count)
WHERE {
  ?compound a vocab:Compound ;
            obo:RO_0000087 vocab:FDAApprovedDrugs .
}
# Results: 17,367 FDA-approved drugs
```

## Interesting Findings

### Specific Entities for Questions
- **CID2244**: Aspirin - well-documented drug, MW 180.16, C9H8O4
- **CID5291**: Imatinib (Gleevec) - anticancer drug, MW 493.6, C29H31N7O
- **CID5284616**: Rapamycin/Sirolimus - immunosuppressant
- **CID2519**: Caffeine - MW 194.19, C8H10N4O2
- **CID1676**: Identified in FDA drugs query (MW ~194)

### Unique Properties
- Patent information via cito:isDiscussedBy (US, EP, CN, JP, KR patents)
- Stereoisomer relationships via cheminf:CHEMINF_000455
- Drug roles via obo:RO_0000087 (FDAApprovedDrugs, etc.)
- Ontology classifications (ChEBI, SNOMED CT, NCI)

### Database Connections
- **ChEBI**: ~5-10% of compounds have ChEBI classification
- **SNOMED CT**: Drug compounds
- **NCI Thesaurus**: Drug compounds
- **PDB**: Proteins linked via pdbx:link_to_pdb
- **Wikidata**: ~2-5% of compounds

### Key Statistics
- 119M compounds total
- 17,367 FDA-approved drugs
- 1.7M bioassays
- 167K genes, 249K proteins, 81K pathways
- >99% have molecular formula, weight, SMILES

## Question Opportunities by Category

### Precision
- What is the PubChem CID for aspirin? (2244)
- What is the molecular weight of imatinib? (493.6)
- What is the molecular formula for caffeine? (C8H10N4O2)
- What is the InChI for aspirin?
- What is the canonical SMILES for rapamycin?

### Completeness
- How many FDA-approved drugs are in PubChem? (17,367)
- How many bioassays are in PubChem? (1.7M)
- List FDA drugs with molecular weight between 400-500
- How many compounds have ChEBI classifications?

### Integration
- What is the ChEBI ID for aspirin (CID2244)?
- Convert PubChem CID to SMILES/InChI
- What proteins are linked to compound CID2244?
- What patents reference caffeine?

### Currency
- How many bioassays have been added for a specific target?
- What new compounds have been classified as FDA drugs?
- Recent patent filings discussing specific compounds

### Specificity
- What is the PubChem CID for a rare disease drug?
- Find compounds classified as specific ChEBI classes
- What is the molecular weight of a specific anticancer drug?
- Find compounds with specific structural features (via SMILES)

### Structured Query
- Find FDA drugs with molecular weight < 500 AND specific roles
- Find compounds with IC50 values in bioassays
- Find stereoisomers of a given compound
- Find compounds linked to specific pathways

## Notes
- Use get_pubchem_compound_id() for name-to-CID conversion
- Use get_compound_attributes_from_pubchem() for full molecular details
- Use FROM clauses for bioassay/protein/gene queries
- CID-based SPARQL queries are very efficient (<1s)
- Aggregation queries should use LIMIT 50-100
- Mixed datatypes in descriptors - filter by type first
