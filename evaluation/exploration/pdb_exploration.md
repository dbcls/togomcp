# PDB Exploration Report

## Database Overview
- **Purpose**: 3D structural data for proteins, nucleic acids, and complexes
- **Scope**: All deposited biomolecular structures from X-ray, NMR, and cryo-EM
- **Key entities**: Structures (204K+), Entities, Polymers, Refinement stats, Cross-references
- **Data quality**: Contains resolution, R-factors, experimental methods

## Schema Analysis (from MIE file)

### Main Properties (PDBx/mmCIF ontology)
- `pdbx:datablock`: Root entry entity
- `pdbx:entry.id`: 4-character PDB ID
- `pdbx:entity`: Biological molecules in the structure
- `pdbx:entity_poly`: Polymer sequences (proteins, nucleic acids)
- `pdbx:exptl.method`: Experimental technique
- `pdbx:refine.ls_d_res_high`: Resolution (Å)
- `pdbx:refine.ls_R_factor_R_work`: R-work quality metric
- `pdbx:struct_ref`: Database cross-references (UniProt, GenBank)

### Important Categories
- `has_exptlCategory`: Experimental methods
- `has_refineCategory`: Refinement statistics
- `has_struct_refCategory`: Sequence database references
- `has_citationCategory`: Publications
- `has_struct_keywordsCategory`: Classification keywords
- `has_softwareCategory`: Software used
- `has_cellCategory`: Unit cell parameters
- `has_symmetryCategory`: Space group info

### Query Patterns
- Use FROM <http://rdfportal.org/dataset/pdbj>
- Extract entry_id with STRAFTER
- Use xsd:decimal() for numeric comparisons
- CONTAINS on keywords for efficient search

## Search Queries Performed

1. **Query**: search_pdb_entity(db="pdb", query="CRISPR Cas9")
   - Results: 473 structures
   - Examples: 8spq (SpRY-Cas9:gRNA complex), various PAM targeting complexes

2. **Query**: search_pdb_entity(db="pdb", query="kinase inhibitor")
   - Results: 13,193 structures
   - Examples: 1ydr, 1ydt, 1yds (PKA with inhibitors)

3. **Query**: search_pdb_entity(db="pdb", query="hemoglobin")
   - Expected: Hundreds of hemoglobin structures

4. **Query**: search_pdb_entity(db="pdb", query="ribosome")
   - Expected: Large ribosome structures (cryo-EM)

5. **Additional**: Verified structure metadata and resolution queries

## SPARQL Queries Tested

```sparql
# Query 1: Find highest resolution structures (< 0.8 Å)
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?entry_id ?resolution
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_refineCategory/pdbx:has_refine ?refine .
  ?refine pdbx:refine.ls_d_res_high ?resolution .
  FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 0.8)
}
ORDER BY xsd:decimal(?resolution)
LIMIT 10
# Results: 5D8V (0.48Å), 3NIR (0.48Å), 1EJG (0.54Å), etc.
```

```sparql
# Query 2: Count structures by experimental method
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?method (COUNT(?entry) as ?count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_exptlCategory/pdbx:has_exptl ?exptl .
  ?exptl pdbx:exptl.method ?method .
}
GROUP BY ?method
ORDER BY DESC(?count)
# Results: X-RAY (174,904), ELECTRON MICROSCOPY (15,032), SOLUTION NMR (13,902)
```

```sparql
# Query 3: Find structures with UniProt references (from MIE examples)
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?entry_id ?db_name ?db_accession
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_struct_refCategory/pdbx:has_struct_ref ?ref .
  ?ref pdbx:struct_ref.db_name "UNP" ;
       pdbx:struct_ref.pdbx_db_accession ?db_accession .
}
LIMIT 30
# Pattern verified - links PDB entries to UniProt accessions
```

## Interesting Findings

### Specific Entities for Questions
- **5D8V**: Highest resolution structure at 0.48Å
- **3NIR**: Also 0.48Å resolution (crambin)
- **8spq**: CRISPR Cas9 structure
- **1ydr**: PKA with H7 inhibitor
- **174,904**: Total X-ray structures

### Experimental Methods Distribution
- X-ray diffraction: 174,904 (~85%)
- Electron Microscopy: 15,032 (~7%)
- Solution NMR: 13,902 (~7%)
- Neutron diffraction: 212
- Electron crystallography: 226

### Unique Properties
- Resolution data (for X-ray/cryo-EM)
- R-factors for quality assessment
- Unit cell and symmetry parameters
- Software tools used for structure determination
- Publication/citation metadata

### Database Connections
- **UniProt**: 352K references (~172% coverage per entry)
- **EMDB**: ~7% of structures (cryo-EM maps)
- **GenBank**: 5.9K nucleotide references
- **DOI**: ~75% of entries
- **PubMed**: ~73% of entries

### Key Statistics
- 204,594 total entries
- 0.48Å best resolution (5D8V, 3NIR)
- 473 CRISPR Cas9 structures
- 13,193 kinase inhibitor structures

## Question Opportunities by Category

### Precision
- What is the highest resolution structure in PDB? (0.48Å for 5D8V/3NIR)
- What is the PDB ID for the highest resolution crambin structure? (3NIR)
- What experimental method was used for structure 8spq? (X-ray)
- What is the resolution of PDB entry 1UCS? (0.62Å)

### Completeness
- How many X-ray structures are in PDB? (174,904)
- How many CRISPR Cas9 structures are in PDB? (473)
- How many kinase inhibitor structures exist? (13,193)
- How many structures use electron microscopy? (15,032)

### Integration
- What UniProt accession is linked to PDB entry 16PK? (P07378)
- Convert PDB ID to EMDB map ID
- What publication (DOI) is associated with structure X?
- Link PDB structure to GenBank nucleotide sequence

### Currency
- What are the newest high-resolution structures?
- How many cryo-EM structures were deposited this year?
- Recent CRISPR-related structure depositions

### Specificity
- Find structures of crambin at atomic resolution
- What is the space group for structure 3NIR?
- Find structures with neutron diffraction data
- What software was used to refine structure X?

### Structured Query
- Find X-ray structures with resolution < 1.0Å
- Find kinase structures from 2020+ with resolution < 2.0Å
- Find structures with both DOI and PubMed references
- Find tetrameric protein assemblies

## Notes
- Always use xsd:decimal() for resolution/R-factor comparisons
- Use FROM <http://rdfportal.org/dataset/pdbj> clause
- Extract entry_id with STRAFTER from URI
- Use struct_keywords for efficient keyword searching
- NMR structures lack resolution data
- Multiple UniProt refs per entry (one per chain) is common
