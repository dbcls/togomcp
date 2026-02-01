# PDB (Protein Data Bank) Exploration Report

**Date**: January 31, 2026
**Session**: 1

## Executive Summary

The PDB database contains 3D structural data for biological macromolecules with 245,833 entries and 204,000+ unique structures. Key findings:

- **Critical numeric type conversion requirement**: Queries filtering by resolution or R-factors MUST use `xsd:decimal()` conversion - without it, string comparisons fail silently and return 0 results
- **Rich cross-database integration**: UniProt cross-references cover ~172% of entries (multiple chains per structure), EMDB links for cryo-EM, DOI/PubMed for publications
- **Diverse experimental methods**: X-ray (~85%), Electron Microscopy (~7%), NMR (~7%)
- **Category-based data organization**: Uses pdbx:has_*Category/pdbx:has_* traversal pattern

## Database Overview

- **Purpose**: 3D structural data for proteins, nucleic acids, and complexes
- **Scope**: 245,833 entries with experimental structures
- **Key data types**: 
  - Entry metadata (structure title, keywords)
  - Experimental methods and conditions
  - Refinement statistics (resolution, R-factors)
  - Sequence/entity information
  - Cross-references to external databases
  - Publication citations
  - Biological assemblies
  - Software used in structure determination
- **Dataset size considerations**: 900K+ entities require query optimization
- **Access methods**: SPARQL endpoint + search_pdb_entity tool

## Structure Analysis

### Performance Strategies

1. **Always use `xsd:decimal()` for numeric comparisons**
   - Resolution, R-factors, cell parameters are stored as strings
   - String comparison `?resolution < 2.0` returns 0 results
   - Must use `xsd:decimal(?resolution) < 2.0`
   - Performance impact: Difference between 0 results and correct results (77,877 for resolution < 2.0)

2. **Use pdbx:datablock type filter early**
   - Filter by `?entry a pdbx:datablock` to restrict to entry-level data
   - Prevents returning intermediate category objects

3. **Use struct_keywords for classification searches**
   - `pdbx:struct_keywords.pdbx_keywords` is optimized for searches
   - Using struct.title for keyword searches is slower

4. **Include FROM graph clause**
   - `FROM <http://rdfportal.org/dataset/pdbj>` improves optimization

5. **Use LIMIT for interactive queries**
   - Recommend LIMIT 20-100 for initial exploration

### Common Pitfalls

1. **String vs Numeric Comparison Failure**
   - Error: Query returns 0 results when filtering numeric fields
   - Cause: Resolution, R-factors stored as strings
   - Solution: Use `xsd:decimal()` type conversion
   - Example:
     - WRONG: `FILTER(?resolution < 2.0)` → 0 results
     - RIGHT: `FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 2.0)` → 77,877 results

2. **Missing OPTIONAL for Method-Dependent Data**
   - NMR structures lack resolution/R-factor data
   - Cryo-EM structures may lack traditional R-factors
   - Solution: Use OPTIONAL or filter by experimental method

3. **Missing Entry Type Filter**
   - Without `?entry a pdbx:datablock`, query may return category objects
   - Always filter by datablock type for entry-level queries

### Data Organization

The PDB uses a Category-Item hierarchical pattern:

- **Datablock root** (pdbx:datablock): One per PDB entry
- **Categories**: has_entryCategory, has_entityCategory, has_entity_polyCategory, has_exptlCategory, has_refineCategory, has_struct_refCategory, has_citationCategory, etc.
- **Items**: Specific data elements within categories

Key categories:
1. **struct/struct_keywords**: Entry title, classification keywords
2. **entity/entity_poly**: Molecular entities, polymer sequences
3. **exptl**: Experimental method (X-RAY DIFFRACTION, ELECTRON MICROSCOPY, SOLUTION NMR)
4. **refine**: Refinement statistics (resolution, R-factors)
5. **struct_ref**: Cross-references to sequence databases (UniProt, GenBank)
6. **database_2**: Links to EMDB, BMRB, other WWPDB partners
7. **citation**: Publication references with DOI/PubMed
8. **cell/symmetry**: Crystallographic parameters (X-ray only)
9. **software**: Computational tools used
10. **pdbx_struct_assembly**: Biological assembly information

### Cross-Database Integration Points

**Integration 1: PDB → UniProt**
- Relationship: Protein sequence cross-references via struct_ref
- Property: `pdbx:struct_ref.db_name "UNP"` + `pdbx:struct_ref.pdbx_db_accession`
- Coverage: 352K references (~172% per entry due to multi-chain structures)
- Use case: Find all structures for a specific protein
- TogoID also supports conversion: `route='uniprot,pdb'` or `route='pdb,uniprot'`

**Integration 2: PDB → EMDB**
- Relationship: Cryo-EM density maps via database_2
- Property: `pdbx:database_2.database_id "EMDB"` + `database_2.database_code`
- Coverage: ~7% of entries
- Use case: Find cryo-EM structures with associated density maps

**Integration 3: PDB → PubMed**
- Relationship: Publication citations
- Property: `pdbx:citation.pdbx_database_id_PubMed`
- Coverage: ~73% of entries
- Use case: Find structures associated with specific publications

**Integration 4: PDB → DOI**
- Relationship: Publication DOI
- Property: `pdbx:citation.pdbx_database_id_DOI`
- Coverage: ~75% of entries

**Integration 5: PDB → GenBank/EMBL/RefSeq**
- Relationship: Nucleotide sequence cross-references
- Property: `pdbx:struct_ref.db_name` = "GB", "EMBL", or "REF"
- Coverage: ~6K references total

## Complex Query Patterns Tested

### Pattern 1: Numeric Type Conversion for Resolution Filtering

**Purpose**: Find high-resolution X-ray structures

**Category**: Performance-Critical, Error Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
FILTER(?resolution < 2.0)
```

**What Happened**:
- Result: 0 results returned
- Why it failed: Resolution values stored as strings, string comparison "1.5" < "2.0" doesn't work as expected

**Correct Approach (using proper pattern)**:
```sparql
FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 2.0)
```

**What Knowledge Made This Work**:
- Key Insight: Resolution, R-factors are stored as xsd:string, not xsd:decimal
- Must explicitly cast to decimal for numeric comparisons
- Include lower bound (> 0) to filter invalid values

**Results Obtained**:
- Correct query: 77,877 X-ray structures with resolution < 2.0 Å
- Naive query: 0 results

**Natural Language Question Opportunities**:
1. "How many X-ray crystal structures in PDB have resolution better than 2.0 Angstroms?" - Category: Completeness
2. "What are the highest resolution protein structures in the PDB?" - Category: Precision

---

### Pattern 2: Cross-Reference Query for UniProt-PDB Linking

**Purpose**: Find all PDB structures for a specific protein

**Category**: Integration, Cross-Database

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>
SELECT ?entry_id ?resolution ?title
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_struct_refCategory/pdbx:has_struct_ref ?ref ;
         pdbx:has_structCategory/pdbx:has_struct ?struct .
  ?ref pdbx:struct_ref.db_name "UNP" ;
       pdbx:struct_ref.pdbx_db_accession ?uniprot_id .
  ?struct pdbx:struct.title ?title .
  OPTIONAL { ?entry pdbx:has_refineCategory/pdbx:has_refine/pdbx:refine.ls_d_res_high ?resolution }
  FILTER(?uniprot_id = "P04637")
}
```

**What Knowledge Made This Work**:
- Cross-references stored in struct_ref category
- db_name = "UNP" identifies UniProt references
- pdbx_db_accession contains the UniProt ID
- OPTIONAL needed because NMR/EM structures may lack resolution

**Results Obtained**:
- P04637 (p53): 250+ PDB structures
- P38398 (BRCA1): 20+ structures including X-ray, NMR, Cryo-EM

**Natural Language Question Opportunities**:
1. "What 3D structures are available for the human p53 protein?" - Category: Integration
2. "Which experimental methods have been used to determine BRCA1 structures?" - Category: Structured Query
3. "What is the best resolution structure available for a given UniProt protein?" - Category: Precision

---

### Pattern 3: Multi-Criteria Structure Quality Filtering

**Purpose**: Find high-quality kinase structures with good R-factors and publications

**Category**: Structured Query, Complex Filtering

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?entry_id ?title ?resolution ?r_work ?year
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_structCategory/pdbx:has_struct ?struct ;
         pdbx:has_struct_keywordsCategory/pdbx:has_struct_keywords ?kw ;
         pdbx:has_refineCategory/pdbx:has_refine ?refine ;
         pdbx:has_citationCategory/pdbx:has_citation ?citation ;
         pdbx:has_exptlCategory/pdbx:has_exptl/pdbx:exptl.method "X-RAY DIFFRACTION" .
  ?kw pdbx:struct_keywords.pdbx_keywords ?keywords .
  ?refine pdbx:refine.ls_d_res_high ?resolution ;
          pdbx:refine.ls_R_factor_R_work ?r_work .
  ?citation pdbx:citation.year ?year .
  FILTER(CONTAINS(LCASE(?keywords), "kinase"))
  FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 2.0)
  FILTER(xsd:decimal(?r_work) < 0.20)
}
ORDER BY xsd:decimal(?resolution)
```

**What Knowledge Made This Work**:
- Multiple criteria: keywords, resolution, R-factor, publication
- xsd:decimal() required for ALL numeric comparisons
- struct_keywords for classification (not title)
- Filter by experimental method for valid resolution data

**Results Obtained**:
- High-quality kinase structures with R-work < 0.20 and resolution < 2.0 Å
- Best examples: Phosphoglycerate kinase (16PK) at 1.6 Å

**Natural Language Question Opportunities**:
1. "What are the highest quality kinase structures with published validation?" - Category: Structured Query
2. "Find recent protein kinase structures with resolution better than 2 Angstroms" - Category: Structured Query

---

### Pattern 4: Experimental Method Distribution Analysis

**Purpose**: Count structures by experimental method

**Category**: Completeness

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?method (COUNT(DISTINCT ?entry) AS ?count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_exptlCategory/pdbx:has_exptl ?exptl .
  ?exptl pdbx:exptl.method ?method .
}
GROUP BY ?method
ORDER BY DESC(?count)
```

**Results Obtained**:
- X-RAY DIFFRACTION: 174,904
- ELECTRON MICROSCOPY: 15,032
- SOLUTION NMR: 13,902
- ELECTRON CRYSTALLOGRAPHY: 226
- NEUTRON DIFFRACTION: 212
- SOLID-STATE NMR: 162

**Natural Language Question Opportunities**:
1. "How many protein structures were determined by cryo-electron microscopy?" - Category: Completeness
2. "What fraction of PDB structures were solved by X-ray crystallography?" - Category: Completeness

---

### Pattern 5: Software Usage Statistics

**Purpose**: Analyze refinement software usage in structural biology

**Category**: Completeness, Currency

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?software_name (COUNT(DISTINCT ?entry) AS ?usage_count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  ?entry pdbx:has_softwareCategory/pdbx:has_software ?sw .
  ?sw pdbx:software.name ?software_name ;
      pdbx:software.classification "refinement" .
}
GROUP BY ?software_name
ORDER BY DESC(?usage_count)
```

**Results Obtained**:
- PHENIX: 71,337 structures
- REFMAC: 70,213 structures
- CNS: 22,819 structures
- X-PLOR: 8,462 structures
- BUSTER: 7,356 structures

**Natural Language Question Opportunities**:
1. "What is the most commonly used refinement software for PDB structures?" - Category: Completeness
2. "How many structures were refined using PHENIX?" - Category: Completeness

---

### Pattern 6: Cryo-EM Structure with EMDB Cross-Reference

**Purpose**: Find cryo-EM structures with their EMDB density map codes

**Category**: Integration, Cross-Database

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?entry_id ?emdb_code ?title
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_database_2Category/pdbx:has_database_2 ?db ;
         pdbx:has_structCategory/pdbx:has_struct ?struct ;
         pdbx:has_exptlCategory/pdbx:has_exptl ?exptl .
  ?db pdbx:database_2.database_id "EMDB" ;
      pdbx:database_2.database_code ?emdb_code .
  ?struct pdbx:struct.title ?title .
  ?exptl pdbx:exptl.method "ELECTRON MICROSCOPY" .
}
```

**What Knowledge Made This Work**:
- EMDB links stored in database_2 category
- Filter by database_id = "EMDB"
- Combined with exptl.method filter for EM structures

**Results Obtained**:
- Ribosome structures with EMDB maps (e.g., 8A22 → EMD-15100)
- SARS-CoV-2 structures with cryo-EM data

**Natural Language Question Opportunities**:
1. "What cryo-EM structures of ribosomes have associated electron density maps?" - Category: Integration
2. "Find SARS-CoV-2 spike protein structures with EMDB density maps" - Category: Specificity

---

### Pattern 7: Biological Assembly and Oligomeric State Query

**Purpose**: Find protein complexes with specific oligomeric states

**Category**: Structured Query

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?entry_id ?oligomeric_count ?oligomeric_details ?title
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_pdbx_struct_assemblyCategory/pdbx:has_pdbx_struct_assembly ?assembly ;
         pdbx:has_structCategory/pdbx:has_struct ?struct .
  ?assembly pdbx:pdbx_struct_assembly.oligomeric_count ?oligomeric_count ;
            pdbx:pdbx_struct_assembly.oligomeric_details ?oligomeric_details .
  ?struct pdbx:struct.title ?title .
  FILTER(CONTAINS(LCASE(?oligomeric_details), "hexameric"))
}
```

**Results Obtained**:
- SARS-CoV-2 Spike with ACE2: hexameric complex (7A98)
- Tubulin complexes: hexameric (8BDF)
- Various enzyme complexes

**Natural Language Question Opportunities**:
1. "Which protein structures form tetrameric assemblies?" - Category: Structured Query
2. "Find hexameric enzyme complexes in the PDB" - Category: Structured Query

---

### Pattern 8: Multi-Chain Structure with Multiple UniProt References

**Purpose**: Find large complexes with many distinct protein components

**Category**: Completeness, Integration

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?entry_id ?title (COUNT(DISTINCT ?uniprot_id) AS ?num_proteins)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_struct_refCategory/pdbx:has_struct_ref ?ref ;
         pdbx:has_structCategory/pdbx:has_struct ?struct .
  ?ref pdbx:struct_ref.db_name "UNP" ;
       pdbx:struct_ref.pdbx_db_accession ?uniprot_id .
  ?struct pdbx:struct.title ?title .
}
GROUP BY ?entry_id ?title
HAVING (COUNT(DISTINCT ?uniprot_id) >= 5)
ORDER BY DESC(?num_proteins)
```

**Results Obtained**:
- Trypanosoma brucei mitoribosome: 125 distinct proteins
- Human ribosome complexes: 80+ proteins
- SARS-CoV-2 ribosome complexes: 83 proteins

**Natural Language Question Opportunities**:
1. "What are the largest multi-protein complexes in the PDB?" - Category: Completeness
2. "Which ribosome structures have the most protein components?" - Category: Completeness

---

### Pattern 9: Polymer Type Distribution

**Purpose**: Count different polymer types (protein, DNA, RNA, hybrid)

**Category**: Completeness

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?poly_type (COUNT(DISTINCT ?poly) AS ?count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?poly a pdbx:entity_poly .
  ?poly pdbx:entity_poly.type ?poly_type .
}
GROUP BY ?poly_type
ORDER BY DESC(?count)
```

**Results Obtained**:
- polypeptide(L): 384,206
- polydeoxyribonucleotide (DNA): 20,008
- polyribonucleotide (RNA): 13,539
- DNA/RNA hybrid: 269
- polypeptide(D): 144
- peptide nucleic acid: 3

**Natural Language Question Opportunities**:
1. "How many RNA structures are in the PDB?" - Category: Completeness
2. "What fraction of PDB structures contain DNA?" - Category: Completeness

---

### Pattern 10: Publication Citation with Year Filter

**Purpose**: Find structures published in specific years

**Category**: Currency

**Note**: Year filtering requires attention - direct comparison works but ordering needs care.

**Correct Approach**:
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT ?entry_id ?pubmed_id ?year ?journal ?title
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_citationCategory/pdbx:has_citation ?citation .
  ?citation pdbx:citation.pdbx_database_id_PubMed ?pubmed_id ;
            pdbx:citation.year ?year ;
            pdbx:citation.journal_abbrev ?journal ;
            pdbx:citation.title ?title .
}
ORDER BY DESC(?year)
LIMIT 20
```

**Results Obtained**:
- Most recent publications: 2023
- Coverage: ~73% of entries have PubMed IDs

**Natural Language Question Opportunities**:
1. "What structures were published in Nature in the last 3 years?" - Category: Currency
2. "Find recent CRISPR-Cas structures with their publications" - Category: Specificity

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. **Search: "BRCA1 human"**
   - Found: 4Y2G, 4Y18, 7JZV, 1JM7, etc. (249 total)
   - Usage: Protein structure questions, multi-method comparison

2. **Search: "kinase"** (via keywords)
   - Found: Numerous kinase structures with varied resolution
   - Usage: Quality filtering questions

3. **Ultra-high resolution structures**
   - Found: 3NIR (crambin, 0.48 Å), 5D8V (HiPIP, 0.48 Å)
   - Usage: Precision questions about structure quality

4. **SARS-CoV-2 structures**
   - Found: Multiple spike, nsp1, ribosome complexes
   - Usage: Currency/specificity questions

5. **Ribosome structures**
   - Found: 6HIV (125 proteins), mitochondrial/cytoplasmic
   - Usage: Complex assembly questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What 3D structures are available for the human tumor suppressor p53?"
   - Databases: PDB + (implicit UniProt P04637 knowledge)
   - Knowledge Required: struct_ref cross-reference pattern, UNP db_name
   - Category: Integration
   - Difficulty: Medium

2. "Which proteins have both X-ray crystal structures and cryo-EM structures?"
   - Database: PDB
   - Knowledge Required: Experimental method filtering, UniProt grouping
   - Category: Integration
   - Difficulty: Hard

3. "Find cryo-EM structures of SARS-CoV-2 with their associated electron density maps"
   - Databases: PDB + EMDB
   - Knowledge Required: database_2 cross-references, EMDB linking
   - Category: Specificity / Integration
   - Difficulty: Medium

**Performance-Critical Questions**:

4. "How many protein structures have resolution better than 2.0 Angstroms?"
   - Database: PDB
   - Knowledge Required: xsd:decimal() conversion - CRITICAL (without it, returns 0)
   - Category: Completeness
   - Difficulty: Medium

5. "What is the average resolution of X-ray structures solved in the last 5 years?"
   - Database: PDB
   - Knowledge Required: Numeric conversion, year filtering, aggregation
   - Category: Completeness
   - Difficulty: Hard

6. "Find kinase structures with resolution < 2.0 Å and R-factor < 0.20"
   - Database: PDB
   - Knowledge Required: Multiple numeric filters with xsd:decimal()
   - Category: Structured Query
   - Difficulty: Hard

**Error-Avoidance Questions**:

7. "List structures with NMR-derived models"
   - Database: PDB
   - Knowledge Required: NMR structures lack resolution data (OPTIONAL needed)
   - Category: Completeness
   - Difficulty: Medium

8. "Find structures across all experimental methods with their quality metrics"
   - Database: PDB
   - Knowledge Required: OPTIONAL for method-dependent properties
   - Category: Structured Query
   - Difficulty: Hard

**Complex Filtering Questions**:

9. "What hexameric protein assemblies are available in the PDB?"
   - Database: PDB
   - Knowledge Required: pdbx_struct_assembly category, oligomeric_details
   - Category: Structured Query
   - Difficulty: Medium

10. "Find protein-DNA complexes with resolution better than 2.5 Å"
    - Database: PDB
    - Knowledge Required: Polymer type filtering + numeric resolution
    - Category: Structured Query
    - Difficulty: Hard

11. "What refinement software was used for the highest resolution structures?"
    - Database: PDB
    - Knowledge Required: Software category + resolution ordering
    - Category: Structured Query
    - Difficulty: Medium

12. "Find structures of membrane proteins determined by cryo-EM"
    - Database: PDB
    - Knowledge Required: Keywords filtering + experimental method
    - Category: Specificity
    - Difficulty: Medium

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the PDB ID for the highest resolution crambin structure?"
   - Method: search_pdb_entity or simple SPARQL
   - Knowledge Required: None (straightforward)
   - Category: Precision
   - Difficulty: Easy

2. "How many PDB structures contain the word 'ribosome' in the title?"
   - Method: search_pdb_entity
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy

**ID Mapping Questions**:

3. "What UniProt ID corresponds to PDB structure 3NIR?"
   - Method: togoid_convertId(ids='3NIR', route='pdb,uniprot')
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

4. "How many PDB structures are linked to UniProt P04637?"
   - Method: togoid_convertId(ids='P04637', route='uniprot,pdb')
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

5. "What PDB structures are available for human BRCA1?"
   - Method: search_pdb_entity('BRCA1 human')
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source**:
- → UniProt: via struct_ref (UNP) + TogoID
- → EMDB: via database_2 (EMDB)
- → GenBank: via struct_ref (GB)
- → PubMed: via citation
- → DOI: via citation

**This Database as Target**:
- UniProt →: proteins with known structures
- ChEMBL →: drug-target structural data
- Reactome →: pathway proteins with structures

**Complex Multi-Database Paths**:
- UniProt → PDB → EMDB: Find cryo-EM structures for specific proteins
- UniProt → PDB → PubMed: Find publications for protein structures
- PDB → UniProt → GO: Functional annotation of structurally characterized proteins

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Numeric type conversion is CRITICAL**: Without xsd:decimal(), numeric filters return 0 results - this is a silent failure that's hard to diagnose
2. **Category traversal pattern**: Understanding pdbx:has_*Category/pdbx:has_* is essential
3. **Cross-reference patterns**: struct_ref for sequences, database_2 for other databases
4. **Method-dependent data availability**: NMR lacks resolution, EM may lack R-factors

### Common Pitfalls Discovered

1. **Silent failures**: String numeric comparisons return 0 instead of error
2. **Missing OPTIONAL**: Queries fail for structures without certain metadata
3. **Wrong field for searches**: Using title instead of keywords is slower

### Recommendations for Question Design

1. **Focus on numeric filtering questions**: These demonstrate clear MIE value
2. **Include cross-database integration**: PDB-UniProt and PDB-EMDB links
3. **Test multi-criteria queries**: Combine resolution, method, keywords
4. **Include method-specific questions**: X-ray vs EM vs NMR differences

### Performance Notes

- Total entries: 245,833
- X-ray structures with resolution < 2.0 Å: 77,877
- Entries with PubMed citations: 169,057 (~69%)
- Average UniProt references per entry: 1.72 (352K total)

---

## Notes and Observations

1. **Data freshness**: Most recent publication year in database is 2023
2. **Large complexes**: Ribosome structures have 80-125 distinct protein chains
3. **Polymer diversity**: Includes proteins, DNA, RNA, hybrids, PNA
4. **Software tracking**: Comprehensive records of tools used in structure determination

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Numeric filtering (resolution), cross-database (UniProt), multi-criteria
- Focus areas: Quality metrics, experimental methods, protein complexes
- Avoid: Questions requiring data not in database (e.g., future publications)

**Further Exploration Needed**:
- Federated queries combining PDB with UniProt endpoint
- More testing of NMR-specific queries
- Exploration of cell/symmetry data for crystallography questions

---

**Session Complete - Ready for Next Database**
