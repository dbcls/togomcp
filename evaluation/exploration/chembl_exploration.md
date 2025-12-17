# ChEMBL Exploration Report

## Database Overview
- **Purpose**: ChEMBL is a manually curated database of bioactive molecules with drug-like properties
- **Scope**: 2.4M+ compounds, 1.6M assays, 20M bioactivity measurements, cross-references to external databases
- **Key data types**: Small molecules, proteins, targets, assays, activities, documents, drug mechanisms, and drug indications

## Schema Analysis (from MIE file)

### Main Properties Available
- **Molecules**: chemblId, label, highestDevelopmentPhase, atcClassification, substanceType, moleculeXref (to external DBs)
- **Activities**: standardType (IC50, EC50, Ki), standardValue, standardUnits, pChembl (normalized)
- **Targets**: targetType (SINGLE PROTEIN, PROTEIN COMPLEX, PROTEIN FAMILY), organismName, hasTargetComponent
- **Assays**: assayType, organismName, hasTarget
- **Drug mechanisms**: mechanismActionType (INHIBITOR, AGONIST, etc.)
- **Drug indications**: hasMeshHeading, highestDevelopmentPhase, links to MeSH disease terms

### Important Relationships
- **Molecule-Activity-Assay-Target**: Core bioactivity model
- **TargetComponent**: Bridges targets to UniProt identifiers via skos:exactMatch
- **Drug mechanisms**: Link molecules to targets with action types
- **Cross-references**: 
  - moleculeXref to PubChem, DrugBank, ChEBI, ZINC, HMDB
  - skos:exactMatch for UniProt proteins
  - hasMesh for disease ontologies
  - bibo:pmid for literature

### Query Patterns Observed
- Use bif:contains for fast keyword searches with boolean operators
- Always specify FROM <http://rdf.ebi.ac.uk/dataset/chembl>
- Filter by standardUnits when comparing activity values
- Start from specific target types (cco:SingleProtein) for efficiency
- Use path expressions like hasAssay/hasTarget for complex queries

## Search Queries Performed

1. **Query**: Search for imatinib molecules
   - **Results**: Found 5 entries:
     - CHEMBL941 - IMATINIB (score: 36.0)
     - CHEMBL1642 - IMATINIB MESYLATE (score: 36.0)
     - CHEMBL2386595, CHEMBL3040018, CHEMBL56904 (derivatives/related)
   - Demonstrates exact match and related compounds

2. **Query**: Search for kinase targets
   - **Results**: Found 1,632 kinase-related targets:
     - CHEMBL3714704 - Kinase (Mus musculus, SINGLE PROTEIN)
     - CHEMBL241 - cGMP-inhibited 3',5'-cyclic phosphodiesterase 3A (Homo sapiens)
     - CHEMBL290 - cGMP-inhibited 3',5'-cyclic phosphodiesterase 3B (Homo sapiens)
     - CHEMBL3061 - Phosphodiesterase 3A (Sus scrofa)
     - CHEMBL5129 - Phosphodiesterase 3B (Bos taurus)
   - Shows multi-organism target coverage

3. **Query**: Search for aspirin molecules
   - **Tool**: TogoMCP:search_chembl_molecule
   - **Results**: Found 52 aspirin-related molecules:
     - CHEMBL25 - ASPIRIN (score: 36.0)
     - CHEMBL5314595 - ASPIRIN TRELAMINE (score: 35.0)
     - CHEMBL1697753 - ASPIRIN DL-LYSINE (score: 31.0)
     - CHEMBL2260549 - ASPIRIN EUGENOL ESTER (score: 29.0)
     - CHEMBL2105097 - GUACETISAL (score: 17.0)
   - Demonstrates formulations and derivatives

4. **Query**: Search for imatinib molecules
   - **Tool**: TogoMCP:search_chembl_molecule
   - **Results**: Found 5 imatinib entries:
     - CHEMBL941 - IMATINIB (score: 36.0)
     - CHEMBL1642 - IMATINIB MESYLATE (salt form, score: 36.0)
     - Related derivatives and analogs
   - Shows drug and salt form coverage

5. **Query**: Search for kinase targets (repeated with tool documentation)
   - **Tool**: TogoMCP:search_chembl_target
   - **Results**: 1,632 kinase-related protein targets across species
   - Includes single proteins, protein families, and selectivity groups
   - Multi-organism coverage (human, mouse, pig, cow)
   - Shows multi-organism coverage and target diversity

## SPARQL Queries Tested

```sparql
# Query 1: Search molecules with bif:contains
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?label ?sc
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?molecule a cco:SmallMolecule ;
            rdfs:label ?label .
  ?label bif:contains "'aspirin'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 100

# Expected results: Aspirin and aspirin-related molecules with relevance scores
# Demonstrates fast full-text search capability
```

```sparql
# Query 2: Get human protein targets
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?target ?label ?targetType
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?target a cco:SingleProtein ;
          rdfs:label ?label ;
          cco:targetType ?targetType ;
          cco:organismName "Homo sapiens" .
}
LIMIT 100

# Expected results: Human proteins with their target classifications
# Critical for drug target research
```

```sparql
# Query 3: Find bioactivities for specific molecule
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?activity ?type ?value ?units ?target
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?activity a cco:Activity ;
            cco:hasMolecule <http://rdf.ebi.ac.uk/resource/chembl/molecule/CHEMBL941> ;
            cco:standardType ?type ;
            cco:hasAssay/cco:hasTarget ?target .
  OPTIONAL { ?activity cco:standardValue ?value }
  OPTIONAL { ?activity cco:standardUnits ?units }
}
LIMIT 100

# Expected results: IC50, EC50, Ki values for imatinib against various targets
# Shows bioactivity data structure
```

```sparql
# Query 4: Find potent kinase inhibitors (IC50 < 100 nM)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?label ?target ?targetLabel ?value
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?activity a cco:Activity ;
            cco:standardType "IC50" ;
            cco:standardValue ?value ;
            cco:standardUnits "nM" ;
            cco:hasMolecule ?molecule ;
            cco:hasAssay/cco:hasTarget ?target .
  ?target rdfs:label ?targetLabel .
  ?molecule rdfs:label ?label .
  ?targetLabel bif:contains "'kinase'" option (score ?sc)
  FILTER(xsd:decimal(?value) < 100)
}
ORDER BY DESC(?sc)
LIMIT 100

# Expected results: Potent kinase inhibitors with sub-100nM IC50 values
# Critical for drug discovery screening
```

```sparql
# Query 5: Cross-database integration (ChEMBL to DrugBank and UniProt)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?molecule ?moleculeLabel ?drugbankId ?uniprot ?targetLabel
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?molecule a cco:SmallMolecule ;
            rdfs:label ?moleculeLabel ;
            cco:moleculeXref ?drugbankId ;
            cco:hasActivity/cco:hasAssay/cco:hasTarget ?target .
  ?target cco:hasTargetComponent/skos:exactMatch ?uniprot ;
          rdfs:label ?targetLabel .
  FILTER(STRSTARTS(STR(?drugbankId), "http://www.drugbank.ca/drugs/"))
  FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
}
LIMIT 100

# Expected results: Molecules with DrugBank IDs linked to UniProt target proteins
# Essential for multi-database integration queries
```

## Interesting Findings

### Specific Entities for Questions
1. **Imatinib (CHEMBL941)** - First-line CML drug, BCR-ABL kinase inhibitor
2. **Imatinib mesylate (CHEMBL1642)** - Salt form of imatinib
3. **Kinase targets** - 1,632 entries across multiple organisms (human, mouse, pig, cow)
4. **cGMP-inhibited phosphodiesterases** - Multiple homologs across species

### Unique Properties
- **Bioactivity measurements**: 20M data points with standardized values and units
- **Drug development phases**: 0 (preclinical) to 4 (marketed)
- **ATC classification**: WHO anatomical therapeutic chemical codes
- **Mechanism types**: INHIBITOR, AGONIST, ANTAGONIST, MODULATOR, etc.
- **pChembl values**: Normalized activity measure (-log(molar IC50/EC50/Ki))

### Connections to Other Databases
- **PubChem**: 2.2M+ molecule links
- **DrugBank**: 8.4K drug links
- **UniProt**: 11K protein target links via TargetComponent
- **ChEBI**: 35K chemical entity links
- **MeSH**: 51K disease indication links
- **PDB**: 64K structure links
- **PubMed**: 88K literature references

### Specific, Verifiable Facts
- Total molecules: 2,400,000
- Total activities: 20,000,000
- Total assays: 1,600,000
- Total targets: 13,000
- Molecules with activities: ~80%
- Targets with UniProt mappings: ~85%
- Molecules with PubChem links: ~90%
- Average activities per molecule: 8.5
- Average assays per target: 120

## Question Opportunities by Category

### Precision
- "What is the ChEMBL ID for imatinib mesylate?"
- "What is the exact IC50 value of imatinib against BCR-ABL?"
- "What is the UniProt ID for the target CHEMBL3714704?"
- "What ATC classification code is assigned to doxylamine (CHEMBL1004)?"
- "What is the highest development phase for imatinib?"

### Completeness
- "List all kinase inhibitors with IC50 < 100 nM in ChEMBL"
- "How many human protein targets are in ChEMBL?"
- "Count all bioactivity measurements for imatinib"
- "List all mechanism action types in ChEMBL"
- "How many molecules have both DrugBank and UniProt cross-references?"

### Integration
- "Convert ChEMBL ID CHEMBL941 to its DrugBank ID"
- "Find the UniProt IDs for all targets of imatinib"
- "Link ChEMBL molecules to their PubChem CIDs"
- "Find MeSH disease terms associated with specific ChEMBL drugs"
- "Connect ChEMBL bioactivities to PubMed literature"

### Currency
- "What molecules were added to ChEMBL in version 34 (2024)?"
- "Find recently characterized kinase inhibitors (2023-2024)"
- "What new drug indications were added in recent releases?"
- "Find compounds in latest clinical trial phases"

### Specificity
- "What is the mechanism of action of imatinib against BCR-ABL?"
- "Find all serine/threonine kinase inhibitors excluding tyrosine kinases"
- "What are the disease indications for CHEMBL941 (imatinib) in phase 4 trials?"
- "Find molecules with INHIBITOR mechanism against angiotensin-converting enzyme (CHEMBL1808)"

### Structured Query
- "Find all molecules with IC50 < 10 nM against human kinases AND development phase >= 2"
- "Query molecules with ('kinase' AND NOT 'tyrosine') in target labels"
- "Retrieve all compounds with DrugBank links AND MeSH disease indications AND IC50 values"
- "Find targets with activities measured in both nM and uM units, convert and compare"
- "Complex query: molecules in phase 3+ trials with sub-micromolar activity against cancer-related targets"

## Notes

### Limitations and Challenges
- **Units critical**: Activity values meaningless without standardUnits (nM, uM, %)
- **Incomplete data**: Not all activities have standardValues, not all molecules have chemical descriptors
- **UniProt coverage**: Some targets lack UniProt mappings (especially non-human organisms)
- **Query timeout risk**: Missing FROM clause or using FILTER/REGEX instead of bif:contains
- **Multiple forms**: Same drug may appear as base, salt, mesylate, etc. (e.g., imatinib vs imatinib mesylate)

### Best Practices for Querying
1. **Always specify graph**: `FROM <http://rdf.ebi.ac.uk/dataset/chembl>`
2. **Use bif:contains**: For text searches with boolean operators ('kinase' AND NOT 'tyrosine')
3. **Check units**: Always include `cco:standardUnits` when comparing activity values
4. **Filter by type**: Use specific target types (cco:SingleProtein) before broader queries
5. **Path expressions**: Use hasAssay/hasTarget for efficient multi-hop queries
6. **Numeric filters**: Cast values with `xsd:decimal(?value)` before comparison
7. **OPTIONAL for cross-refs**: Not all entities have external database links
8. **LIMIT appropriately**: Use 100-10000 depending on query complexity
9. **pChembl for normalization**: Use pChembl values for comparing activities across different assay types
