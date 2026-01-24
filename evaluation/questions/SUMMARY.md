# TogoMCP Evaluation Questions Summary

## Overview
- **Total Questions**: 120
- **Files**: Q01.json through Q10.json (12 questions each)
- **Categories**: 6 (20 questions each)
- **Databases Covered**: All 23 databases

## Question Distribution

### By Category (20 questions each)

| Category | Questions | Description |
|----------|-----------|-------------|
| Precision | 20 | Exact IDs, sequences, specific properties |
| Completeness | 20 | Counts, exhaustive lists |
| Integration | 20 | Cross-database linking, ID conversions |
| Currency | 20 | Recent updates, current classifications |
| Specificity | 20 | Niche organisms, rare diseases, specialized compounds |
| Structured Query | 20 | Complex filters, multi-step queries |

### By File

| File | IDs | Categories |
|------|-----|------------|
| Q01.json | 1-12 | 2 per category |
| Q02.json | 13-24 | 2 per category |
| Q03.json | 25-36 | 2 per category |
| Q04.json | 37-48 | 2 per category |
| Q05.json | 49-60 | 2 per category |
| Q06.json | 61-72 | 2 per category |
| Q07.json | 73-84 | 2 per category |
| Q08.json | 85-96 | 2 per category |
| Q09.json | 97-108 | 2 per category |
| Q10.json | 109-120 | 2 per category |

## Database Coverage

### High Priority Databases (multiple questions)
- **UniProt**: Protein sequence and function (IDs 1, 3, 35, 37, 71, 97, 109)
- **ChEMBL**: Bioactive molecules and drugs (IDs 2, 11, 15, 27, 46, 61, 100)
- **PubChem**: Chemical compounds (IDs 13, 25, 47, 69, 92, 93)
- **ClinVar**: Genetic variants (IDs 8, 16, 23, 83)
- **GO**: Gene Ontology (IDs 4, 12, 28, 58, 59, 73, 76)
- **PDB**: Protein structures (IDs 7, 14, 19, 31, 41, 108, 110, 116)

### Medium Priority Databases
- **NCBI Gene**: Gene information (IDs 5, 38, 51, 65)
- **Ensembl**: Genomics (IDs 18, 44, 50, 78, 101)
- **MeSH**: Medical vocabulary (IDs 21, 26, 75, 86, 111)
- **Reactome**: Pathways (IDs 20, 70, 84, 95)
- **Rhea**: Biochemical reactions (IDs 24, 30, 43, 98)
- **PubMed/PubTator**: Literature (IDs 36, 56, 80, 120)

### Specialized Databases
- **MONDO**: Disease ontology (IDs 6, 29, 32, 40, 53, 68, 81, 89, 91, 102)
- **ChEBI**: Chemical ontology (IDs 17, 39, 49, 62, 66, 77, 105, 115)
- **NANDO**: Japanese rare diseases (IDs 9, 34, 68, 94, 106, 119)
- **BacDive**: Bacterial strains (IDs 10, 22, 45, 48, 57, 74, 87, 103)
- **MediaDive**: Culture media (IDs 45, 67, 104, 114)
- **Taxonomy**: NCBI Taxonomy (IDs 42, 55, 60, 79, 85, 113, 117)
- **AMR Portal**: Antimicrobial resistance (IDs 64, 72, 96, 112)
- **GlyCosmos**: Glycoscience (IDs 33, 52, 63, 82, 88, 118)
- **DDBJ**: Nucleotide sequences (IDs 54, 90, 107)

## Quality Assurance

### Non-Trivial Design
All 120 questions require actual database queries and cannot be answered by:
- Reading MIE documentation files
- Using entities from MIE examples
- General knowledge without database access

### Expert Relevance
Questions designed for real research workflows:
- Drug discovery (kinase inhibitors, IC50 values)
- Clinical genetics (pathogenic variants, disease IDs)
- Structural biology (resolution, methods)
- Rare disease research (NANDO, Orphanet integration)
- Antimicrobial resistance surveillance
- Glycobiology and specialized fields

### Biological Focus
All questions ask about biological/scientific content:
- Proteins, genes, diseases, compounds
- Sequences, structures, molecular weights
- Pathways, reactions, classifications
- Clinical significance, resistance patterns

## Validation

Run the validation script:
```bash
cd /evaluation/scripts
python validate_questions.py ../questions/Q01.json --recommendations
```

Check each file:
- ✅ JSON array format (not wrapped in object)
- ✅ 12 questions per file
- ✅ Sequential IDs (1-120)
- ✅ All 5 required fields present
- ✅ Valid category names (case-sensitive)
- ✅ Questions 10-500 characters
- ✅ 2 questions per category per file

## Key Question Examples

### Precision
- Q1: "What is the UniProt accession ID for human BRCA1?" → P38398
- Q13: "What is the PubChem Compound ID (CID) for caffeine?" → 2519

### Completeness
- Q3: "How many reviewed human proteins are in UniProt Swiss-Prot?" → 40,209
- Q4: "How many descendant terms does GO:0006914 (autophagy) have?" → 25

### Integration
- Q5: "What is the NCBI Gene ID corresponding to UniProt ID P04637?" → 7157
- Q17: "What is the ChEBI ID for ATP?" → CHEBI:30616

### Currency
- Q7: "How many CRISPR Cas9 structures are currently in the PDB?" → 461
- Q8: "How many SNVs are recorded in ClinVar?" → 3,236,823

### Specificity
- Q9: "What is the NANDO identifier for Parkinson's disease?" → NANDO:1200010
- Q21: "What is the MeSH descriptor ID for Erdheim-Chester disease?" → D031249

### Structured Query
- Q11: "Find approved kinase inhibitors with IC50 < 50 nM" → RUXOLITINIB, IBRUTINIB...
- Q12: "Find molecular function terms containing 'kinase'" → GO:0004672...

---

**Generated**: 2025-01-24
**Version**: 1.0
**Status**: Ready for evaluation
