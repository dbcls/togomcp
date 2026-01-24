# ChEMBL Exploration Report

## Database Overview
- **Purpose**: Manually curated database of bioactive molecules with drug-like properties
- **Scope**: 1,920,809 small molecules (as of query), 20M bioactivity measurements, 1.6M assays
- **Key features**: Molecule-target-activity relationships, drug mechanisms, clinical development phases

## Schema Analysis (from MIE file)
### Main Properties
- `cco:SmallMolecule`: Small molecule entity
- `cco:chemblId`: ChEMBL identifier (e.g., "CHEMBL941")
- `cco:highestDevelopmentPhase`: Clinical development phase (0-4, where 4 = approved)
- `cco:Activity`: Bioactivity measurement linking molecule to target
- `cco:standardType`: Activity type (IC50, EC50, Ki, etc.)
- `cco:standardValue` / `cco:standardUnits`: Numeric values with units

### Important Relationships
- `cco:hasMolecule`: Activity → Molecule
- `cco:hasAssay`: Activity → Assay
- `cco:hasTarget`: Assay → Target
- `cco:hasTargetComponent`: Target → UniProt links
- `cco:moleculeXref`: External database cross-references
- `cco:hasMechanism`: Drug mechanism of action
- `cco:hasDrugIndication`: Disease indications

### Query Patterns
- Always use `FROM <http://rdf.ebi.ac.uk/dataset/chembl>` clause
- Use `bif:contains` for keyword search (not REGEX)
- Always include `cco:standardUnits` when filtering by activity values
- Filter by `cco:highestDevelopmentPhase 4` for approved drugs

## Search Queries Performed

1. **Query: "imatinib" (search_chembl_molecule)**
   - CHEMBL941: IMATINIB (the free base)
   - CHEMBL1642: IMATINIB MESYLATE (the salt form)
   - Total: 5 related compounds

2. **Query: "EGFR human" (search_chembl_target)**
   - CHEMBL203: Epidermal growth factor receptor (Homo sapiens)
   - CHEMBL4523747: EGFR/PPP1CA (protein-protein interaction)
   - Total: 134 related targets

3. **Query: "BCR-ABL kinase" (search_chembl_target)**
   - CHEMBL6105: BCR/ABL p210 fusion protein (Homo sapiens)
   - CHEMBL2096618: Bcr/Abl fusion protein
   - CHEMBL5146: Breakpoint cluster region protein
   - Total: 1,652 related targets

## SPARQL Queries Tested

```sparql
# Query 1: Count total small molecules
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT (COUNT(DISTINCT ?molecule) as ?total_molecules)
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?molecule a cco:SmallMolecule .
}
# Result: 1,920,809 molecules
```

```sparql
# Query 2: Count approved drugs (phase 4)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT (COUNT(DISTINCT ?molecule) as ?approved_drugs)
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?molecule a cco:SmallMolecule ;
            cco:highestDevelopmentPhase 4 .
}
# Result: 3,678 approved drugs
```

```sparql
# Query 3: Count human protein targets
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT (COUNT(DISTINCT ?target) as ?human_targets)
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?target a cco:SingleProtein ;
          cco:organismName "Homo sapiens" .
}
# Result: 4,387 human protein targets
```

```sparql
# Query 4: Find potent approved kinase inhibitors (IC50 < 50 nM)
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?label ?value ?targetLabel
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?activity a cco:Activity ;
            cco:standardType "IC50" ;
            cco:standardValue ?value ;
            cco:standardUnits "nM" ;
            cco:hasMolecule ?molecule ;
            cco:hasAssay/cco:hasTarget ?target .
  ?target rdfs:label ?targetLabel ;
          cco:organismName "Homo sapiens" .
  ?molecule rdfs:label ?label ;
            cco:highestDevelopmentPhase 4 .
  ?targetLabel bif:contains "'kinase'" option (score ?sc)
  FILTER(xsd:decimal(?value) > 0 && xsd:decimal(?value) < 50)
}
ORDER BY xsd:decimal(?value)
LIMIT 10
# Results: RUXOLITINIB (0.036 nM vs JAK2), REPOTRECTINIB (0.05 nM vs NTRK2), 
#          IMATINIB (0.06 nM vs erbB-2), IBRUTINIB (0.08 nM vs BTK)
```

```sparql
# Query 5: Find drug mechanisms for approved inhibitors
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT ?molecule ?label ?mechanism ?targetLabel
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?mech a cco:Mechanism ;
        cco:mechanismActionType ?mechanism ;
        cco:hasMolecule ?molecule ;
        cco:hasTarget ?target .
  ?molecule rdfs:label ?label ;
            cco:highestDevelopmentPhase 4 .
  ?target rdfs:label ?targetLabel ;
          cco:organismName "Homo sapiens" .
  FILTER(CONTAINS(?mechanism, "INHIBITOR"))
}
LIMIT 10
# Results: PHENYLBUTAZONE→COX, SIMVASTATIN→HMG-CoA reductase, COLCHICINE→Tubulin
```

## Cross-Reference Analysis

### External database links (via cco:moleculeXref):
- **PubChem**: 2.2M+ compounds linked
- **ZINC**: 1.2M+ compounds
- **DrugBank**: 8,400+ drugs
- **ChEBI**: 35,000+ compounds
- **FDA SRS**: 32,000+ substances

### UniProt links (via cco:hasTargetComponent/skos:exactMatch):
- 11,000+ target components linked to UniProt
- Essential for protein sequence and function data

### Disease ontology links (via cco:hasMesh):
- 51,000+ drug indications linked to MeSH

### Shared EBI endpoint databases:
- ChEBI, Reactome, Ensembl, AMRPortal

## Interesting Findings

**Discoveries requiring actual database queries (NOT in MIE examples):**

1. **1,920,809 small molecules** in ChEMBL (requires COUNT query)
2. **3,678 approved drugs** (phase 4, requires filter query)
3. **4,387 human protein targets** (requires organism filter)
4. **CHEMBL941 is imatinib** (Gleevec) - found via search
5. **CHEMBL203 is human EGFR** - key cancer target
6. **CHEMBL6105 is BCR-ABL fusion** - imatinib target
7. **RUXOLITINIB has IC50 of 0.036 nM** against JAK2 (potent kinase inhibitor)
8. **IBRUTINIB has IC50 of 0.08 nM** against BTK (potent BTK inhibitor)

**Key real entities discovered (NOT in MIE examples):**
- CHEMBL941: Imatinib (cancer drug)
- CHEMBL1789941: Ruxolitinib (JAK inhibitor)
- CHEMBL1873475: Ibrutinib (BTK inhibitor)
- CHEMBL4298138: Repotrectinib (NTRK inhibitor)
- CHEMBL203: Human EGFR target
- CHEMBL6105: BCR-ABL fusion protein target

## Question Opportunities by Category

### Precision
- ✅ "What is the ChEMBL ID for imatinib?" → CHEMBL941 (requires search)
- ✅ "What is the ChEMBL ID for human EGFR?" → CHEMBL203 (requires search)
- ✅ "What is the IC50 of imatinib against BCR-ABL?" → requires activity query
- ✅ "What is the highest development phase for CHEMBL941?" → 4 (approved)

### Completeness  
- ✅ "How many small molecules are in ChEMBL?" → 1,920,809
- ✅ "How many approved drugs are in ChEMBL?" → 3,678
- ✅ "How many human protein targets are in ChEMBL?" → 4,387

### Integration
- ✅ "What UniProt ID is linked to ChEMBL target CHEMBL203?" → requires skos:exactMatch query
- ✅ "What DrugBank ID corresponds to CHEMBL941?" → requires moleculeXref query

### Currency
- ✅ "How many approved drugs are currently in ChEMBL?" → 3,678 (quarterly updates)

### Specificity
- ✅ "What is the ChEMBL ID for the BCR-ABL fusion protein?" → CHEMBL6105
- ✅ "What is the ChEMBL ID for ruxolitinib?" → CHEMBL1789941
- ✅ "What is the ChEMBL ID for ibrutinib?" → CHEMBL1873475

### Structured Query
- ✅ "Find approved kinase inhibitors with IC50 < 50 nM" → compound filter
- ✅ "Find drugs that inhibit cyclooxygenase" → mechanism + target filter
- ✅ "Find human kinase targets in ChEMBL" → type + organism filter

## Notes
- Always use `FROM <http://rdf.ebi.ac.uk/dataset/chembl>` clause
- Use `bif:contains` for keyword searches (10-100x faster than REGEX)
- Always include `cco:standardUnits` when filtering activity values
- Filter by `cco:highestDevelopmentPhase 4` for approved drugs
- Some activity values can be negative (indicating issues) - filter appropriately
- ChEMBL uses `skos:exactMatch` for cross-references to UniProt
- Quarterly updates mean counts may change over time
- Activity property paths: `cco:hasActivity/cco:hasAssay/cco:hasTarget`
