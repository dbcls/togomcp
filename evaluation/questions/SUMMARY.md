# TogoMCP Evaluation Questions Summary

## Overview

This directory contains 120 high-quality evaluation questions designed to test TogoMCP's database access capabilities.

## Question Distribution

### Files
- **Q01.json** - Questions 1-12
- **Q02.json** - Questions 13-24
- **Q03.json** - Questions 25-36
- **Q04.json** - Questions 37-48
- **Q05.json** - Questions 49-60
- **Q06.json** - Questions 61-72
- **Q07.json** - Questions 73-84
- **Q08.json** - Questions 85-96
- **Q09.json** - Questions 97-108
- **Q10.json** - Questions 109-120

### Category Distribution (20 questions each)

| Category | Description | Questions |
|----------|-------------|-----------|
| **Precision** | Exact IDs, sequences, molecular properties | 20 |
| **Completeness** | Exhaustive lists, counts, coverage | 20 |
| **Integration** | Cross-database linking, ID conversions | 20 |
| **Currency** | Recent updates, current statistics | 20 |
| **Specificity** | Niche organisms, rare diseases, specialized data | 20 |
| **Structured Query** | Complex filters, multi-step queries | 20 |

Each file contains exactly 2 questions from each category.

## Database Coverage

All 23 TogoMCP databases are represented across the 120 questions:

| Database | Question Count | Key Question Topics |
|----------|---------------|---------------------|
| UniProt | 8 | Protein IDs, mnemonics, reviewed entries |
| PubChem | 6 | Compound IDs, molecular properties, FDA drugs |
| ChEMBL | 6 | Drug IDs, targets, bioactivity data |
| GO | 6 | Term IDs, hierarchies, namespace counts |
| PDB | 6 | Resolution, structures, experimental methods |
| ClinVar | 3 | Variant counts, types |
| Reactome | 3 | Pathway IDs, protein IDs |
| MONDO | 4 | Disease IDs, cross-references |
| NANDO | 5 | Japanese rare disease IDs, notification numbers |
| MeSH | 4 | Descriptor IDs, term counts |
| BacDive | 6 | Strain IDs, phenotypes, temperature |
| MediaDive | 5 | Medium IDs, ingredients, pH |
| Rhea | 4 | Reaction counts, equations |
| ChEBI | 5 | Chemical IDs, formulas |
| AMR Portal | 7 | Resistance data, gene classes |
| GlyCosmos | 6 | Glycan counts, epitopes, glycoproteins |
| Ensembl | 4 | Gene IDs, species counts |
| NCBI Gene | 4 | Gene IDs, types, chromosomes |
| Taxonomy | 2 | Organism taxonomy IDs (9606, 10090) |
| TogoID | 3 | ID conversions |

## Redundancy Check (Completed)

The following duplicate/near-duplicate questions were identified and fixed:

| Original Issue | Resolution |
|---------------|------------|
| Q17 & Q89: Both asked BRCA1 ↔ ENSG00000012048 | Q17 → Taxonomy ID for Homo sapiens; Q89 → TP53 Ensembl ID |
| Q8 & Q49: Both asked mTOR pathway R-HSA-165159 | Q49 → Taxonomy ID for Mus musculus |

### Remaining Conceptually Related (but distinct) Questions:
- Aspirin questions: Q2 (PubChem CID), Q61 (ChEBI ID), Q65 (cross-reference) - Different ID types
- Glucose questions: Q30, Q42, Q108 - Different database cross-references
- Thermotoga questions: Q21, Q46, Q58 - Different properties (BacDive ID, culture collections, DSM number)
- PDB method counts: Q20, Q31, Q67, Q115 - Different methods (X-ray, EM, NMR, total)
- Lewis epitopes: Q22, Q70, Q106 - Different variants

These are intentionally kept as they test different aspects of database access.

## Question Quality Criteria

All questions satisfy:

✅ **Biologically Realistic** - Would an actual researcher ask this?
✅ **Biologically Relevant** - Addresses scientific content, not IT infrastructure
✅ **Testable Distinction** - Requires database access vs training knowledge
✅ **Appropriate Complexity** - Non-trivial but not impossibly broad
✅ **Clear Success Criteria** - Verifiable correct answer
✅ **Verifiable Ground Truth** - Confirmed during exploration phase
✅ **Natural Phrasing** - No mention of SPARQL or MCP tools
✅ **No True Duplicates** - Each question tests a unique concept

## Question Examples by Category

### Precision
- "What is the UniProt accession ID for SpCas9 from S. pyogenes?" → Q99ZW2
- "What is the PubChem CID for aspirin?" → 2244
- "What is the highest resolution in PDB?" → 0.48 Å

### Completeness
- "How many descendant terms does GO:0006914 have?" → 25
- "How many reviewed human proteins are in UniProt?" → 40,209
- "How many bacterial strains are in BacDive?" → 97,334

### Integration
- "What is the NCBI Gene ID for UniProt P04637?" → 7157
- "What is the Taxonomy ID for Homo sapiens?" → 9606
- "What ChEBI ID corresponds to glucose?" → CHEBI:17234

### Currency
- "How many CRISPR Cas9 structures are in PDB?" → 461
- "How many FDA-approved drugs are in PubChem?" → 17,367
- "How many human genes are in Ensembl?" → 87,688

### Specificity
- "What is the MeSH ID for Erdheim-Chester disease?" → D031249
- "What is the NANDO ID for Parkinson's disease?" → NANDO:1200010
- "What is the highest growth temperature in BacDive?" → 112°C

### Structured Query
- "What are the top AMR gene classes in AMR Portal?" → BETA-LACTAM, AMINOGLYCOSIDE, EFFLUX
- "How many transport reactions are in Rhea?" → 5,984
- "Find strains that grow above 80°C" → 221 strains

## Validation

All questions were:
1. Derived from verified findings in exploration reports
2. Cross-referenced with exploration documentation
3. Tested for biological relevance
4. Formatted according to QUESTION_FORMAT.md specifications
5. Checked for redundancy and duplicates

## Usage

```bash
# Validate format
python scripts/validate_questions.py questions/Q01.json

# Run evaluation
python scripts/automated_test_runner.py questions/

# Analyze results
python scripts/results_analyzer.py evaluation_results.csv
```

## Related Files

- `exploration/` - Database exploration reports with verified findings
- `scripts/QUESTION_FORMAT.md` - JSON format specification
- `QUESTION_DESIGN_GUIDE.md` - Question design criteria
- `scripts/example_questions.json` - Example question format

---

**Generated**: 2025-01-13
**Last Updated**: 2025-01-13 (Redundancy check completed)
**Total Questions**: 120
**Databases Covered**: 23
**Categories**: 6
