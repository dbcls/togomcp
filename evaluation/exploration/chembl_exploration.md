# ChEMBL Exploration Report

## Database Overview
- **Purpose**: Manually curated database of bioactive molecules with drug-like properties
- **Scope**: Drug discovery data linking compounds, targets, activities, mechanisms, and indications
- **Key entities**: Molecules (2.4M+), Activities (20M), Assays (1.6M), Targets (13K)
- **Data quality**: Expert curation, standardized bioactivity measurements

## Schema Analysis (from MIE file)

### Main Properties
- `cco:SmallMolecule`: Central entity for drug-like compounds
- `cco:chemblId`: ChEMBL identifier (e.g., "CHEMBL25")
- `cco:highestDevelopmentPhase`: Drug development stage (1-4, 4=marketed)
- `cco:atcClassification`: ATC drug classification codes
- `cco:Activity`: Bioactivity measurements
- `cco:standardType`: Activity type (IC50, EC50, Ki, etc.)
- `cco:standardValue`: Numeric activity value
- `cco:standardUnits`: Units (nM, uM, etc.)

### Important Relationships
- `cco:hasMolecule`: Links activities to molecules
- `cco:hasAssay`: Links activities to assays
- `cco:hasTarget`: Links assays to protein targets
- `cco:hasTargetComponent`: Links targets to components
- `skos:exactMatch`: Links to UniProt proteins
- `cco:moleculeXref`: Cross-references (DrugBank, PubChem, ChEBI)
- `cco:hasMechanism`: Drug mechanism of action
- `cco:hasDrugIndication`: Disease indications

### Query Patterns
- Always use FROM <http://rdf.ebi.ac.uk/dataset/chembl>
- Use bif:contains for text search (faster than FILTER/REGEX)
- Filter activities by cco:standardType and cco:standardUnits
- Start with specific types (cco:SingleProtein for targets)

## Search Queries Performed

1. **Query**: search_chembl_molecule("aspirin")
   - Results: Found CHEMBL25 (ASPIRIN), CHEMBL5314595 (ASPIRIN TRELAMINE), etc.
   - Total: 52 molecules

2. **Query**: search_chembl_molecule("imatinib")
   - Results: Found CHEMBL941 (IMATINIB), CHEMBL1642 (IMATINIB MESYLATE)
   - Total: 5 molecules

3. **Query**: search_chembl_target("kinase human")
   - Results: Found 1,711 targets including CHEMBL3886, CHEMBL4954
   - Includes various kinase types

4. **Query**: search_chembl_target("EGFR")
   - Results: Found CHEMBL203 (human EGFR), CHEMBL3608 (mouse EGFR)
   - Also protein-protein interactions involving EGFR

5. **Additional search**: Confirmed kinase targets with bioactivity data

## SPARQL Queries Tested

```sparql
# Query 1: Find marketed drugs (phase 4) with ATC classification
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?label ?phase ?atc
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?molecule a cco:SmallMolecule ;
            rdfs:label ?label ;
            cco:highestDevelopmentPhase ?phase .
  OPTIONAL { ?molecule cco:atcClassification ?atc }
  FILTER(?phase = 4)
}
LIMIT 20
# Results: CETIRIZINE (R06AE07), PENTAZOCINE (N02AD01), TOLMETIN (M01AB03), etc.
```

```sparql
# Query 2: Find potent kinase inhibitors (IC50 < 10 nM)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?label ?target ?targetLabel ?value ?units
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?activity a cco:Activity ;
            cco:standardType "IC50" ;
            cco:standardValue ?value ;
            cco:standardUnits ?units ;
            cco:hasMolecule ?molecule ;
            cco:hasAssay/cco:hasTarget ?target .
  ?target rdfs:label ?targetLabel ;
          cco:organismName "Homo sapiens" .
  ?molecule rdfs:label ?label .
  ?targetLabel bif:contains "'kinase'" option (score ?sc)
  FILTER(xsd:decimal(?value) < 10 && ?units = "nM")
}
ORDER BY ?value
LIMIT 20
# Results: Multiple compounds with sub-10nM IC50 against CDK5, GSK-3β, IRAK4, SYK, etc.
```

```sparql
# Query 3: Find drug indications (from MIE examples)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?moleculeLabel ?disease ?phase
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?indication a cco:DrugIndication ;
              cco:hasMolecule ?molecule ;
              cco:hasMeshHeading ?disease ;
              cco:highestDevelopmentPhase ?phase .
  ?molecule rdfs:label ?moleculeLabel .
  FILTER(?phase >= 3)
}
ORDER BY DESC(?phase)
LIMIT 100
# Pattern verified - links molecules to disease indications with MeSH terms
```

## Interesting Findings

### Specific Entities for Questions
- **CHEMBL25**: Aspirin - canonical small molecule drug
- **CHEMBL941**: Imatinib - groundbreaking kinase inhibitor
- **CHEMBL203**: Human EGFR target - important in oncology
- **CHEMBL262**: GSK-3 beta - kinase target with potent inhibitors
- **CHEMBL4036**: CDK5 - kinase with sub-nM inhibitors

### Drug Development Phases
- Phase 4 = Marketed drugs (has ATC classification)
- Phase 3 = Clinical trials
- Phase 2/1 = Earlier development

### Unique Properties
- ATC classification codes for drug classification
- pChembl values for normalized activity comparison
- Mechanism action types (INHIBITOR, AGONIST, etc.)
- MeSH disease headings for indications

### Database Connections
- **UniProt**: Via TargetComponent skos:exactMatch (~11K)
- **DrugBank**: Via moleculeXref (~8.4K)
- **PubChem**: Via moleculeXref (~2.2M)
- **ChEBI**: Via moleculeXref (~35K)
- **MeSH**: Via hasMesh for indications (~51K)

### Key Statistics
- 2.4M molecules, 20M bioactivities
- 1,711 kinase-related targets in human
- ~80% of molecules have activity data
- ~85% of targets have UniProt mappings

## Question Opportunities by Category

### Precision
- What is the ChEMBL ID for aspirin? (CHEMBL25)
- What is the ChEMBL target ID for human EGFR? (CHEMBL203)
- What is the highest development phase for imatinib? (4)
- What is the ATC code for cetirizine? (R06AE07)

### Completeness
- How many kinase targets are in ChEMBL for Homo sapiens? (~1,711)
- How many marketed drugs (phase 4) are in ChEMBL?
- List all drug indications for imatinib
- Count compounds with IC50 < 100 nM against any kinase

### Integration
- What is the UniProt ID for ChEMBL target CHEMBL203?
- Convert ChEMBL molecule ID to DrugBank ID
- Link ChEMBL targets to PDB structures
- What PubChem CID corresponds to CHEMBL25?

### Currency
- What are the newest Phase 3+ drug candidates?
- Latest compounds tested against emerging targets
- Recent additions to marketed drug list

### Specificity
- What compounds inhibit CDK5 with IC50 < 10 nM?
- Find drugs with specific mechanism of action types
- What is the mechanism of action for a specific drug?

### Structured Query
- Find molecules with IC50 < 100 nM against kinases AND phase >= 2
- Find EGFR inhibitors with published activity data
- Find compounds with both mechanism and indication data
- Filter drugs by ATC class AND development phase

## Notes
- Always use FROM <http://rdf.ebi.ac.uk/dataset/chembl> clause
- Use bif:contains for text search - much faster than FILTER/REGEX
- Filter activities by standardType AND standardUnits to ensure comparability
- Some activity values may be negative or zero (data quality issues)
- Target-to-UniProt via TargetComponent path requires skos:exactMatch
- Phase 4 drugs typically have ATC classification
