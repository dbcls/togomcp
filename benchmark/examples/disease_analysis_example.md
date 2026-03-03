# Alzheimer's Disease Multi-Scale Analysis — Conversation Summary

## Overview

This conversation was a structured bioinformatics research session, using multiple scientific databases and tools to build a comprehensive, multi-scale pathophysiology report on Alzheimer's disease (AD). The final deliverable was a professionally formatted Word document (.docx).

---

## Phase 1 — Disease Ontology Mapping

The session began by anchoring the analysis to standardized disease identifiers. Using **TogoID** and **OLS4**, the primary AD concept was mapped across ontologies:

- **MONDO:0004975** → MeSH `D000544`, DOID `10652`, HP `HP:0002511`
- Cross-references: SNOMED `26929004`, NCIT `C2866`, EFO `0000249`

---

## Phase 2 — Protein Discovery via SPARQL (UniProt)

SPARQL queries were run against the **UniProt RDF endpoint** to retrieve Swiss-Prot reviewed, human proteins annotated with Alzheimer's disease. Key proteins identified:

| UniProt ID | Symbol | Role |
|---|---|---|
| P05067 | APP | Amyloid precursor protein |
| P49768 | PSEN1 | γ-secretase catalytic subunit |
| P56817 | BACE1 | Rate-limiting β-secretase, major drug target |
| P10636 | MAPT | Tau — forms neurofibrillary tangles when hyperphosphorylated |
| P02649 | APOE | APOE4 allele impairs Aβ clearance, disrupts BBB |

Additional proteins linked to mitochondrial fission (DRP1), tau O-GlcNAcylation (OGT1), and cannabinoid signaling (CNR1) were also retrieved.

---

## Phase 3 — Cross-Database ID Conversion (TogoID)

UniProt accessions were converted to identifiers in downstream databases:

- **UniProt → NCBI Gene**: e.g., P05067 → Gene ID `351`
- **UniProt → PDB**: Revealed hundreds of structural entries per protein
- **UniProt → ChEMBL Target**: Linked proteins to drug target records (e.g., BACE1 → `CHEMBL4822`)

---

## Phase 4 — Pathway Analysis via SPARQL (Reactome)

SPARQL queries against the **Reactome RDF endpoint** identified key AD-associated pathways:

- **Deregulated CDK5 pathway**: Aβ → Ca²⁺ dysregulation → calpain cleaves p35 to p25 → CDK5:p25 phosphorylates CDC25A/B/C → aberrant CDK1/2/4 activation → neuronal death
- **Amyloid fiber formation** (R-HSA-624): Aggregation pathway for Aβ42 and tau

---

## Phase 5 — Drug-Target Analysis (ChEMBL + TogoID)

Approved AD therapeutics were retrieved from **ChEMBL** and mapped to compound databases:

| Drug | Mechanism | ChEMBL → DrugBank |
|---|---|---|
| Donepezil | AChE inhibitor | CHEMBL502 → DB00843 |
| Galantamine | AChE/nAChR modulator | CHEMBL807 → DB01043 |
| Rivastigmine | AChE/BChE inhibitor | CHEMBL659 → DB00674 |
| Memantine | NMDA antagonist | CHEMBL636 → DB00989 |
| Lecanemab | Anti-Aβ protofibril mAb | CHEMBL3833321 (FDA-approved 2023) |

---

## Phase 6 — Literature Evidence (PubMed)

**PubMed MCP** retrieved key recent reviews with DOIs:

- Serrano-Pozo et al., *Lancet Neurol* 2021 — APOE genetics and pathophysiology
- Hampel et al., *Mol Psychiatry* 2021 — Amyloid-β pathway systematic review
- Liu et al., *Transl Neurodegener* 2024 — AD mechanisms to therapies
- Kedia & Simons, *Nat Neurosci* 2025 — Oligodendrocytes in AD

---

## Document Generation

All findings were compiled into a 10-section professional Word document using **docx-js**, following the SKILL.md guidelines:

1. Executive Summary
2. Disease Ontology Cross-References
3. Molecular Level (proteins, ID mappings)
4. Pathway Level (Reactome SPARQL results, CDK5 cascade)
5. Cellular Level (6 cell type dysfunction table)
6. Tissue/Organ Level (Braak staging, regional pathology)
7. Clinical Level (preclinical → severe AD staging, biomarkers)
8. Treatment Mechanisms (drug-target table)
9. Integrated Multi-Scale Disease Model (causal cascade)
10. Key Literature Evidence & Data Sources

The document was validated (407 paragraphs, all checks passed) and exported as `alzheimer_multiscale_analysis.docx`.

---

## Tools & Databases Used

| Tool / Database | Purpose |
|---|---|
| OLS4 | Disease ontology lookup |
| TogoID | Cross-database identifier conversion |
| UniProt SPARQL | Protein–disease annotations |
| Reactome SPARQL | Biological pathway data |
| ChEMBL | Drug and target data |
| PubMed MCP | Literature retrieval |
| docx-js | Word document generation |
