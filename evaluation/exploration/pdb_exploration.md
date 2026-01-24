# PDB (Protein Data Bank) Exploration Report

## Database Overview
- **Purpose**: 3D structural data for biological macromolecules (proteins, nucleic acids, complexes)
- **Scope**: 245,833 total entries as of exploration date
- **Experimental methods**: X-ray (174,904), Cryo-EM (15,032), NMR (13,902), and others
- **Key features**: Resolution data, refinement statistics, cross-references to UniProt/EMDB/publications

## Schema Analysis (from MIE file)
### Main Properties
- `pdbx:datablock`: Root entry entity
- `pdbx:entry`: Entry identifier
- `pdbx:entity`: Molecular entities (polymer, non-polymer, water)
- `pdbx:refine`: Refinement statistics (resolution, R-factors)
- `pdbx:exptl`: Experimental method information

### Important Relationships
- `pdbx:struct_ref`: Cross-references to sequence databases (UniProt, GenBank)
- `pdbx:database_2`: External database links (EMDB, BMRB)
- `pdbx:citation`: Publication references (DOI, PubMed)
- `pdbx:struct_keywords`: Classification keywords

### Query Patterns
- Use `pdbx:datablock` type filter for entry-level queries
- Use `STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/")` for clean PDB IDs
- Use `xsd:decimal()` for numeric comparisons (resolution, R-factors)
- Use `CONTAINS(LCASE())` for keyword searches

## Search Queries Performed

1. **Query: "CRISPR Cas9"**
   - Total: 474 structures
   - 8SPQ: SpRY-Cas9:gRNA complex targeting TGG PAM DNA
   - 8T6P: SpRY-Cas9:gRNA complex with 2 bp R-loop
   - Extensive coverage of Cas9 variants and conformations

2. **Query: "hemoglobin human"**
   - Total: 647 structures
   - 6BB5: Human Oxy-Hemoglobin
   - 5WOH: Human Hemoglobin immersed in liquid oxygen
   - 1BAB: Hemoglobin Thionville variant

3. **Query: "insulin receptor"**
   - Total: 3,642 structures
   - 7MD4: Insulin receptor ectodomain with IRPA-3 agonists
   - 8U4B: Cryo-EM of long form insulin receptor (IR-B) apo state
   - 5KQV: Insulin receptor ectodomain with bovine insulin

4. **Query: "crambin highest resolution"**
   - Found ultra-high resolution entries
   - 3U7T: Room temperature neutron/X-ray crambin
   - 9EWK: Ultrahigh-resolution crambin

5. **Query: "ribosome human"**
   - Total: 2,874 structures
   - 7QI5: Human mitochondrial ribosome at 2.63 Å
   - 4UG0: Human 80S ribosome structure

## SPARQL Queries Tested

```sparql
# Query 1: Find highest resolution structures
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?entry_id ?resolution
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_refineCategory/pdbx:has_refine ?refine .
  ?refine pdbx:refine.ls_d_res_high ?resolution .
  FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 0.6)
}
ORDER BY xsd:decimal(?resolution)
LIMIT 10
# Results: 5D8V (0.48Å), 3NIR (0.48Å), 1EJG (0.54Å), 3P4J (0.55Å), 5NW3 (0.59Å)
```

```sparql
# Query 2: Count entries by experimental method
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?method (COUNT(?entry) as ?count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_exptlCategory/pdbx:has_exptl/pdbx:exptl.method ?method .
}
GROUP BY ?method
ORDER BY DESC(?count)
# Results: X-RAY: 174,904, ELECTRON MICROSCOPY: 15,032, SOLUTION NMR: 13,902
```

```sparql
# Query 3: Count total entries
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT (COUNT(DISTINCT ?entry) as ?total_entries)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
}
# Result: 245,833 total entries
```

```sparql
# Query 4: Count Cryo-EM structures
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT (COUNT(?entry) as ?cryo_em_count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_exptlCategory/pdbx:has_exptl/pdbx:exptl.method "ELECTRON MICROSCOPY" .
}
# Result: 15,032 Cryo-EM structures
```

## Cross-Reference Analysis

### Entity counts (unique structures with references):
- **UniProt**: ~172% coverage (multiple chains per entry, avg 1.72 refs)
- **EMDB**: ~7% of entries have EM density maps
- **DOI**: ~75% of entries have DOI links
- **PubMed**: ~73% of entries have PubMed IDs
- **GenBank**: 5,874 nucleotide sequence references

### Relationship counts:
- UniProt references: 352,114 total
- GenBank references: 5,874 total
- DOI links: 186,683 total
- PubMed links: 181,261 total

## Interesting Findings

**Discoveries requiring actual database queries:**

1. **245,833 total PDB entries** (requires COUNT query)
2. **Highest resolution: 0.48 Å** for PDB entries 5D8V and 3NIR (crambin structures)
3. **15,032 Cryo-EM structures** in PDB (requires method filter)
4. **174,904 X-ray structures** dominate the database
5. **474 CRISPR Cas9 structures** available for genome editing research
6. **647 human hemoglobin structures** with various mutations and states
7. **3,642 insulin receptor structures** - extensive coverage for diabetes research

**Key real entities discovered (NOT in MIE examples):**
- 5D8V: Highest resolution (0.48Å) structure with 3NIR
- 6BB5: Human oxy-hemoglobin
- 8SPQ: Recent SpRY-Cas9 structure
- 7QI5: High-resolution human mitochondrial ribosome (2.63Å)
- 7MD4: Insulin receptor ectodomain complex

## Question Opportunities by Category

### Precision
- ✅ "What is the highest resolution ever achieved in a PDB structure?" → 0.48 Å (requires query)
- ✅ "What is the PDB ID of a crambin structure with 0.48 Å resolution?" → 3NIR or 5D8V
- ✅ "What is the resolution of PDB entry 6BB5?" → requires lookup
- ✅ "What is the PDB ID for human oxy-hemoglobin?" → 6BB5 (via search)

### Completeness  
- ✅ "How many entries are in the PDB?" → 245,833
- ✅ "How many Cryo-EM structures are in PDB?" → 15,032
- ✅ "How many X-ray structures are in PDB?" → 174,904
- ✅ "How many CRISPR Cas9 structures are in PDB?" → 474

### Integration
- ✅ "What UniProt ID is linked to PDB entry 16PK?" → P07378 (cross-reference)
- ✅ "What EMDB map corresponds to PDB entry 8A2Z?" → EMD-15109

### Currency
- ✅ "How many entries are currently in PDB?" → 245,833 (changes weekly)
- ✅ "How many Cryo-EM structures are currently in PDB?" → 15,032 (growing rapidly)

### Specificity
- ✅ "What PDB entry has the best resolution for crambin?" → 5D8V/3NIR
- ✅ "What is the PDB ID for human mitochondrial ribosome at 2.2Å?" → 7QI4

### Structured Query
- ✅ "Find structures with resolution better than 1.0 Å" → 5D8V, 3NIR, 1EJG, etc.
- ✅ "Find kinase structures determined by X-ray" → requires filtering
- ✅ "Find human hemoglobin structures" → 647 results

## Notes
- Always use `xsd:decimal()` for resolution/R-factor comparisons
- NMR structures lack resolution data - use OPTIONAL
- Multi-chain structures have multiple UniProt references
- Weekly updates make count queries time-sensitive
- Use keywords field for classification searches, not title
- FROM graph clause improves query performance
