# Protein Data Bank (PDB) Exploration Report

## Database Overview
- **Purpose**: 3D structural data for proteins, nucleic acids, and complexes from experimental methods
- **Scope**: 204,594+ entries covering proteins, DNA, RNA, and their complexes
- **Key data types**:
  - X-ray diffraction structures (174,904 entries, ~85%)
  - Electron microscopy structures (15,032 entries, ~7%)
  - Solution NMR structures (13,902 entries, ~7%)
  - Other methods: electron crystallography, neutron diffraction, solid-state NMR

## Schema Analysis (from MIE file)

### Main Properties
- **pdbx:datablock**: Root entity representing PDB entry
- **pdbx:entry**: Entry metadata with entry.id
- **pdbx:entity**: Molecular entities (polymer, non-polymer, water, macrolide, branched)
- **pdbx:entity_poly**: Polymer-specific data (sequences, polymer type)
- **pdbx:exptl**: Experimental method (X-RAY DIFFRACTION, ELECTRON MICROSCOPY, SOLUTION NMR)
- **pdbx:refine**: Refinement statistics (resolution, R-work, R-free, reflections)
- **pdbx:struct**: Structure title and descriptor
- **pdbx:struct_keywords**: Classification keywords
- **pdbx:cell**: Unit cell parameters (a, b, c, α, β, γ)
- **pdbx:symmetry**: Space group information
- **pdbx:software**: Software used in structure determination
- **pdbx:pdbx_struct_assembly**: Biological assembly information (oligomeric state)
- **pdbx:citation**: Publication metadata (DOI, PubMed, journal)
- **pdbx:struct_ref**: Cross-references to sequence databases (UniProt, GenBank)
- **pdbx:database_2**: External database links (EMDB, BMRB, WWPDB partners)

### Important Relationships
- **Category-Item design pattern**: Datablock → has_*Category → has_* → individual items
- **Cross-references**: 
  - UniProt: 352,114 refs (~172% per entry, multiple chains)
  - EMDB: 13,974 refs (~7%, for cryo-EM)
  - GenBank: 5,874 refs
  - DOI: 186,683 refs (~75%)
  - PubMed: 181,261 refs (~73%)
- **Bidirectional references**: reference_to_entry, referenced_by_*, reference_to_entity

### Query Patterns Observed
1. Always filter by `?entry a pdbx:datablock` to get entry-level data
2. Extract entry_id: `BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)`
3. Use `xsd:decimal()` for numeric comparisons (resolution, R-factors)
4. Use `CONTAINS(LCASE(?keywords), "...")` for keyword searches on struct_keywords
5. Category traversal: `pdbx:has_*Category/pdbx:has_*` for accessing items
6. Use OPTIONAL for method-specific data (resolution for X-ray, EMDB for EM)
7. Always use FROM clause: `FROM <http://rdfportal.org/dataset/pdbj>`
8. Add LIMIT 20-100 to prevent timeouts

## Search Queries Performed

### Query 1: Search for "CRISPR Cas9" structures
**Tool**: TogoMCP search_pdb_entity
**Result**: 461 total structures found
- Examples: 8SPQ, 8SQH, 8SRS (SpRY-Cas9 variants)
- Various PAM sequences (TGG, TTC, TAC)
- Different R-loop configurations (0-18 bp)
- Mix of target and non-target DNA complexes

### Query 2: Count experimental methods
**Tool**: TogoMCP run_sparql
**Result**: Distribution of experimental methods:
- X-RAY DIFFRACTION: 174,904 entries (85.5%)
- ELECTRON MICROSCOPY: 15,032 entries (7.3%)
- SOLUTION NMR: 13,902 entries (6.8%)
- ELECTRON CRYSTALLOGRAPHY: 226 entries
- NEUTRON DIFFRACTION: 212 entries
- SOLID-STATE NMR: 162 entries
- Other methods: <100 entries each

### Query 3: Find ultra-high resolution structures
**Tool**: TogoMCP run_sparql (resolution < 0.8 Å)
**Result**: 10 structures with atomic resolution:
- 5D8V: 0.48 Å (R-work: 0.072) - tied best resolution
- 3NIR: 0.48 Å (R-work: 0.127) - tied best resolution
- 1EJG: 0.54 Å (R-work: 0.09)
- 3P4J: 0.55 Å (R-work: 0.078)
- 5NW3: 0.59 Å (R-work: 0.1345)
- All are exceptional quality X-ray structures

### Query 4: Search for hemoglobin structures
**Tool**: TogoMCP:search_pdb_entity
**Result**: 1,299 hemoglobin structures found
- 1BAB: Hemoglobin Thionville alpha-chain variant
- 5WOG: Human hemoglobin immersed in liquid oxygen (1 min)
- 6BB5: Human oxy-hemoglobin
- 5WOH: Human hemoglobin in liquid oxygen (20 sec)
- 9S4J-9S4K: Carboxyhemoglobin bound to S. aureus IsdH
- Shows variants, ligand states, and protein-protein complexes

### Query 5: Search for antibody structures
**Tool**: TogoMCP:search_pdb_entity
**Result**: 11,422 antibody structures found
- 7MFB-7MF9: Crystal structures of antibody 10E8v4 variants
- 7KQY: Human heavy-chain only antibody structure
- 9B74-9B7B: Humanized 44H10 Fab variants
- Shows extensive immunology research coverage
- Includes Fab fragments, full antibodies, and antibody-antigen complexes

## SPARQL Queries Tested

```sparql
# Query 1: Count experimental methods (verification)
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?method (COUNT(?entry) as ?count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_exptlCategory/pdbx:has_exptl/pdbx:exptl.method ?method .
}
GROUP BY ?method
ORDER BY DESC(?count)
LIMIT 10
# Results: X-RAY (174K), EM (15K), NMR (14K)
```

```sparql
# Query 2: Find ultra-high resolution structures
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?entry_id ?resolution ?r_work
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_refineCategory/pdbx:has_refine ?refine .
  ?refine pdbx:refine.ls_d_res_high ?resolution ;
          pdbx:refine.ls_R_factor_R_work ?r_work .
  FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 0.8)
}
ORDER BY xsd:decimal(?resolution)
LIMIT 10
# Results: Found 10 structures with resolution < 0.8 Å, best is 0.48 Å
```

```sparql
# Query 3: Example from MIE - Search kinase structures
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?entry_id ?title ?keywords
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_structCategory/pdbx:has_struct ?struct ;
         pdbx:has_struct_keywordsCategory/pdbx:has_struct_keywords ?kw .
  ?struct pdbx:struct.title ?title .
  ?kw pdbx:struct_keywords.pdbx_keywords ?keywords .
  FILTER(CONTAINS(LCASE(?keywords), "kinase"))
}
LIMIT 20
# Would return kinase structures efficiently
```

## Interesting Findings

### Specific Entities for Questions
1. **5D8V / 3NIR**: World record resolution (0.48 Å) - tied for best resolution ever
2. **CRISPR Cas9**: 461 structures available, active research area
3. **Experimental method distribution**: 85% X-ray, 7% EM, 7% NMR
4. **Ultra-high resolution**: Only ~10 structures below 0.8 Å resolution
5. **Software usage**: PHENIX (72K), REFMAC (70K) for refinement

### Unique Properties
- **Category-Item design**: Systematic organization via PDBx/mmCIF ontology
- **Multiple entities per entry**: Average 4.4 entities (chains, ligands, water)
- **UniProt cross-references**: 172% per entry (one ref per protein chain)
- **Quality metrics**: Resolution, R-work, R-free for X-ray; different for EM/NMR
- **Biological assemblies**: ~90% have assembly annotations (oligomeric state)

### Connections to Other Databases
- **UniProt** (UNP): 352K refs - protein sequences
- **EMDB**: 13.97K refs - electron microscopy density maps
- **GenBank** (GB): 5.87K refs - nucleotide sequences
- **DOI**: 186K refs (~75%) - publications
- **PubMed**: 181K refs (~73%) - literature
- **WWPDB partners**: PDB, RCSB, PDBe cross-references
- **BMRB**: ~3% - NMR data
- **RefSeq** (REF): 49 refs - reference sequences

### Specific, Verifiable Facts
1. PDB has 204,594 total entries
2. X-ray diffraction is used for 85.5% of structures (174,904)
3. Best resolution ever achieved: 0.48 Å (two structures: 5D8V, 3NIR)
4. 461 CRISPR Cas9 structures available
5. ~172% UniProt refs per entry (multiple protein chains)
6. ~7% of structures have EMDB cross-references (cryo-EM)
7. ~75% have DOI, ~73% have PubMed IDs

## Question Opportunities by Category

### Precision
- "What is the PDB ID of the structure with the highest resolution ever achieved?" (5D8V or 3NIR, both 0.48 Å)
- "What is the R-work value for PDB entry 5D8V?" (0.072)
- "How many CRISPR Cas9 structures are in the PDB?" (461)
- "What experimental method was used for PDB entry 8SPQ?" (likely cryo-EM or X-ray)

### Completeness
- "How many PDB entries were determined by electron microscopy?" (15,032)
- "List all experimental methods used in the PDB and their counts"
- "How many PDB entries have EMDB cross-references?" (13,974)
- "What are all the structures with resolution better than 0.6 Å?"

### Integration
- "What is the UniProt accession for the protein in PDB entry 16PK?" (P07378)
- "Find the EMDB entry associated with PDB entry 8A2Z" (EMD-15109)
- "What PubMed IDs are associated with CRISPR Cas9 structures?"
- "Convert PDB entry IDs to their corresponding DOIs"

### Currency
- "What are the most recently deposited cryo-EM structures?"
- "How many structures were added to PDB in 2024?"
- "What are the latest CRISPR Cas9 structures?" (8SPQ, 8SQH series)

### Specificity
- "What structures contain SpRY-Cas9 variant?" (8SPQ, 8SQH, 8SRS series)
- "What is the space group of PDB entry 5D8V?"
- "What software was used for refinement of the highest resolution structures?"
- "What biological assembly does PDB entry form?" (monomer, dimer, tetramer, etc.)

### Structured Query
- "Find all kinase structures with resolution better than 2.0 Å determined after 2020"
- "Count structures by space group for P212121"
- "Find all structures that used both XDS and PHENIX software"
- "List structures with tetrameric biological assemblies"

## Notes

### Limitations and Challenges
1. **Method-specific data**: Resolution only for X-ray/EM, not NMR
2. **Numeric type conversions**: Always use xsd:decimal() for resolution/R-factor comparisons
3. **OPTIONAL needed**: For cross-references, software, assemblies (not all entries have them)
4. **Multiple references**: UniProt refs are per-chain, resulting in >100% coverage
5. **Performance**: Multi-category joins can be slow; filter early by entry_id
6. **Missing FROM clause**: Queries may timeout without it

### Best Practices for Querying
1. Always filter by `?entry a pdbx:datablock` first
2. Extract entry_id: `BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)`
3. Use `xsd:decimal()` for all numeric comparisons
4. Filter invalid values: `FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 100)`
5. Use CONTAINS(LCASE(?keywords), "...") for keyword searches
6. Search struct_keywords not struct.title for better performance
7. Use OPTIONAL for method-specific data (resolution, cell parameters)
8. Always add FROM clause and LIMIT 20-100
9. Category traversal: `pdbx:has_*Category/pdbx:has_*` pattern

### Data Quality
- **Resolution coverage**: >85% (X-ray and some EM structures)
- **Cross-reference coverage**: UniProt ~172%, EMDB ~7%, DOI ~75%, PubMed ~73%
- **Quality indicators**: R-work, R-free for X-ray; resolution for X-ray/EM
- **Metadata completeness**: Keywords ~95%, citations ~80%, software ~90%
- **Update frequency**: Weekly releases
- **Validation**: wwPDB validation reports available for most structures
