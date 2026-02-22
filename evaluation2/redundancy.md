# Redundancy Analysis Report — 50 TogoMCP Evaluation Questions

Analysis date: 2026-02-21  
Scope: Semantic redundancy (same biological question, different entities) and structural redundancy (same DB combination + question template)

---

## Summary Table

| Severity | Cluster | Questions | Issue |
|----------|---------|-----------|-------|
| 🔴 HIGH | A — ClinVar variant count | Q1, Q13, Q15, Q21, Q25, Q29, Q40 (7 Qs) | Near-identical template across 7 questions; Q15 & Q29 are near-clones |
| 🔴 HIGH | B — Rhea reaction count | Q3, Q27, Q31, Q43 (4 Qs) | Same "count Rhea reactions for entity X" template; Q3 & Q31 share identical DB combo + type |
| 🟠 MEDIUM | C — BacDive/MediaDive culture conditions | Q8, Q17, Q48 (3 Qs) | 3 questions about bacterial culture conditions; Q8 & Q17 share identical DB combo |
| 🟠 MEDIUM | D — AMR resistance surveillance | Q18, Q34, Q50 (3 Qs) | 3 AMR questions; Q18 & Q50 share identical DB combo |
| 🟠 MEDIUM | E — GlyCosmos glycosylation | Q12, Q22, Q44 (3 Qs) | 3 glycobiology questions; Q12 & Q44 share identical DB combo |
| 🟠 MEDIUM | F — Ensembl MANE Select transcripts | Q7, Q23, Q37 (3 Qs) | 3 questions use MANE Select coverage as a central dimension |
| 🟡 LOW | G — MedGen rare-disease cross-reference | Q36, Q42 (2 Qs) | Same yes/no template: "Does disease X cross-reference MedGen concept with property Y?" |
| 🟡 LOW | H — PDB structure count by category | Q5, Q35 (2 Qs) | Both choice questions: "Which category has most PDB structures?" |
| 🟡 LOW | I — SLE appears in two questions | Q10, Q15 (2 Qs) | Same disease (SLE) in different questions |
| 🟡 LOW | J — PubTator article count for disease | Q19, Q47 (2 Qs) | Both count disease-annotated PubMed articles via PubTator |
| 🟡 LOW | K — "Which taxon has most X" pattern | Q16, Q50 (2 Qs) | Both choice questions asking which bacterial taxon has most [gene/resistance] |

---

## 🔴 HIGH SEVERITY

### Cluster A — ClinVar Pathogenic Variant Count (7 questions)

All 7 questions share the same core operation: **query ClinVar for pathogenic/likely-pathogenic variant counts associated with specific disease genes**, then compare, rank, or summarize those counts.

| Q# | Type | Question (abbreviated) | DBs |
|----|------|------------------------|-----|
| Q1 | yes_no | Does HSPB1 have pathogenic ClinVar variants for CMT disease? | clinvar, ncbigene |
| Q13 | list | Which 5 genes have most ClinVar variants for Joubert syndrome? | nando, medgen, clinvar |
| Q15 | summary | Characterize ClinVar variant landscapes of DNASE1L3 & TLR7 for SLE | mondo, ncbigene, clinvar |
| Q21 | summary | Summarize ClinVar variant landscape for retinitis pigmentosa | mesh, clinvar, medgen |
| Q25 | choice | Which of KCNQ2/KCNQ3/KCNB1/KCNT1 has most pathogenic ClinVar variants? | mondo, ncbigene, clinvar |
| Q29 | summary | Summarize ClinVar variant landscape of 8 BBS genes | mesh, ncbigene, clinvar |
| Q40 | list | Which NCL genes have >100 pathogenic ClinVar variants AND lysosome GO annotation? | uniprot, clinvar |

**Most problematic pair — Q15 vs Q29:**
Both are `summary` type, both ask the evaluator to tally pathogenic variant counts across multiple named disease genes, break down variants by clinical significance category, and note chromosomal distribution. The template is: *"For disease D with genes G1…Gn, summarize the ClinVar variant burden per gene, broken down by variant type and clinical significance."* The only difference is the disease (SLE vs. BBS) and the specific genes named. An AI system that can answer one can answer the other with trivial adaptation.

**Also close — Q21 vs Q29:**  
Both are `summary` questions asking for the ClinVar variant landscape of a single inherited disease, decomposed into clinical significance categories, number of implicated genes, and associated phenotype concepts. Template is essentially identical.

**Recommendation:** Retain Q1 (simplest, yes/no), Q13 (list, top-N), Q25 (choice, bounded comparison), Q40 (list with dual GO+ClinVar filter). Replace Q15, Q21, Q29 with questions that do not use ClinVar variant counts as the primary answer dimension.

---

### Cluster B — Rhea Reaction Counting (4 questions + broader biosynthesis theme)

Four questions share the structural template **"how many approved Rhea reactions match criterion X?"**, all using UniProt or ChEBI as the cross-reference axis:

| Q# | Type | Question (abbreviated) | DBs |
|----|------|------------------------|-----|
| Q3 | factoid | How many reviewed human proteins with autophagy GO terms have ≥1 Rhea reaction? | uniprot, rhea |
| Q27 | factoid | How many distinct Rhea reactions are annotated for nicotinate metabolism enzymes? | reactome, uniprot, rhea |
| Q31 | factoid | How many distinct Rhea reactions are catalyzed by reviewed human glycosyltransferases? | uniprot, rhea |
| Q43 | factoid | How many Rhea reactions have 1,4-dihydroxy-2-naphthoate as participant? | rhea, chebi |

**Most problematic pair — Q3 vs Q31:**  
Identical DB combo (`uniprot + rhea`), identical question type (`factoid`), and identical structural pattern: *"Count the [Rhea reactions / UniProt proteins] at the intersection of [GO/keyword annotation] and [Rhea]."* A system that handles one trivially handles the other by substituting the GO term.

**Broader biosynthesis crowding:** Beyond these four, nine more questions also centrally feature biosynthetic pathways (Q4 melatonin, Q11 chlorophyll, Q24 gluconeogenesis, Q26 riboflavin, Q28 biotin, Q41 prostaglandin, Q45 ubiquinone, Q48 bacteriochlorophyll, Q49 CoA). While these use varied DB combinations and question types, **biosynthetic pathway biology dominates ~26% of the question set** (13/50), reducing coverage of other biological domains (e.g., structural biology, cell signaling, transcriptomics, ecology).

**Recommendation:** Replace at least one of Q3/Q31 (the structural clone pair). Consider replacing 3–4 of the lower-distinctiveness biosynthesis questions (e.g., Q27, Q43) with questions from under-represented biological domains.

---

## 🟠 MEDIUM SEVERITY

### Cluster C — BacDive/MediaDive Culture Conditions (3 questions)

| Q# | Type | Question (abbreviated) | DBs |
|----|------|------------------------|-----|
| Q8 | summary | Summarize culture conditions for anaerobic sulfate-reducing bacteria | bacdive, mediadive |
| Q17 | yes_no | Does Anabaena sp. DSM 101043 grow in nitrogen-free BG11- medium? | bacdive, mediadive |
| Q48 | list | For 5 Chlorobiaceae genera, how many strains have growth-condition records? | bacdive, mediadive, taxonomy |

**Q8 and Q17 share an identical DB combo** (`bacdive + mediadive`). More importantly, all three questions ask the same underlying question: *"What growth/culture conditions does strain/taxon X require, as documented in BacDive/MediaDive?"* A system that learns to query these two databases for culture metadata will succeed on all three trivially.

**Recommendation:** Keep Q17 (specific strain, yes/no) and Q48 (comparative across genera, adds taxonomy). Replace Q8 (summary of general anaerobes) with a BacDive question focused on a completely different attribute (e.g., isolation source, genome size, 16S rRNA gene accession) or replace it entirely with a different database pair.

---

### Cluster D — AMR Resistance Surveillance (3 questions)

| Q# | Type | Question (abbreviated) | DBs |
|----|------|------------------------|-----|
| Q18 | list | List AMR elements for mupirocin resistance in S. aureus | amrportal, taxonomy |
| Q34 | summary | Summarize trimethoprim resistance landscape by species, gene families, geography | amrportal, taxonomy, ncbigene |
| Q50 | choice | Which of 4 ESKAPE species has most antibiotic drug classes in genotypic resistance records? | taxonomy, amrportal |

**Q18 and Q50 share an identical DB combo** (`amrportal + taxonomy`). All three questions query AMRPortal for resistance elements and cross-reference by taxonomy — the core skill tested is identical. The variation is question type (list, summary, choice) and antibiotic class/species granularity.

**Recommendation:** Keep Q50 (choice, most discriminative) and Q34 (summary, multi-dimensional, adds ncbigene). Replace Q18 with an AMRPortal question focusing on a different axis (e.g., resistance mechanism type, geographic origin), or drop it in favour of a question using a different database combination entirely.

---

### Cluster E — GlyCosmos Glycosylation (3 questions)

| Q# | Type | Question (abbreviated) | DBs |
|----|------|------------------------|-----|
| Q12 | yes_no | Does Influenza hemagglutinin A4GCH5 have glycosylation sites in GlyCosmos? | uniprot, glycosmos |
| Q22 | factoid | How many human glycogenes in GlyCosmos are annotated with N-linked glycosylation GO? | go, glycosmos |
| Q44 | list | Which human siglec proteins have N-glycan structures in GlyCosmos? | glycosmos, uniprot |

**Q12 and Q44 share an identical DB combo** (`glycosmos + uniprot`). Both ask whether specific glycoproteins have experimental glycosylation data in GlyCosmos — Q12 for a single viral protein (yes/no), Q44 for a set of human lectins (list). The core skill and data access pattern are the same.

**Recommendation:** Keep Q22 (uses GO as additional axis; factoid count) and Q44 (list, human proteins). Replace Q12 with a GlyCosmos question that tests a qualitatively different feature (e.g., glycan structure class, disease association, or organism other than human/influenza), or replace it with a different DB pair entirely.

---

### Cluster F — Ensembl MANE Select Transcripts (3 questions)

| Q# | Type | Question (abbreviated) | DBs |
|----|------|------------------------|-----|
| Q7 | yes_no | Does SPG11 have both a MANE Select transcript in Ensembl AND a PDB structure? | ensembl, uniprot, pdb |
| Q23 | list | Which spinocerebellar ataxia proteins lack a MANE Select transcript in Ensembl? | uniprot, ensembl |
| Q37 | summary | Summarize Notch signaling proteins by enzymatic function, MANE Select coverage, and Reactome pathways | uniprot, ensembl, reactome |

All three use MANE Select transcript presence/absence in Ensembl as a primary answer dimension. Q23 and Q37 are the closest: both retrieve a set of disease/pathway proteins from UniProt and then check each protein's MANE Select coverage in Ensembl. In Q37, MANE Select is one of three summary dimensions (alongside enzymatic function and Reactome categories), making it less redundant with Q23. Q7 is the most distinct (adds PDB, specific single gene).

**Recommendation:** This cluster is borderline — the question types are distinct (yes/no, list, summary) and Q37 uses MANE Select as only one of three facets. However, if Q23 is replaced, consider choosing a different Ensembl property (e.g., regulatory features, variant consequence scores) for the replacement. If kept, no immediate action required.

---

## 🟡 LOW SEVERITY

### Cluster G — MedGen Rare-Disease Cross-Reference (2 questions)

| Q# | Type | Question | DBs |
|----|------|----------|-----|
| Q36 | yes_no | Does MLD in MONDO cross-reference a MedGen concept where Cholecystitis is documented? | mondo, medgen |
| Q42 | yes_no | Is Leigh syndrome classified as NANDO intractable disease with OMIM cross-reference in MedGen? | nando, medgen |

Both are yes/no questions asking whether a rare disease in one ontology (MONDO / NANDO) cross-references a concept in MedGen with a specific property. The template is identical; only the disease, source ontology, and target property differ. Since these are two of the only ten yes/no questions and they use different source DBs (MONDO vs. NANDO), they are defensible, but replacing one with a yes/no question targeting a completely different attribute would increase diversity.

---

### Cluster H — "Which category has most PDB structures?" (2 questions)

| Q# | Type | Question | DBs |
|----|------|----------|-----|
| Q5 | choice | Which kinase group (AGC, CAMK, CMGC, TK) has most X-ray crystal structures? | chembl, pdb |
| Q35 | choice | Which experimental technique has most serine protease structures in PDB? | uniprot, pdb |

Both are choice questions with the pattern *"which [category] has the most [PDB structures]?"* The categorisation axis differs (protein family vs. experimental method), and the DB combos are different, so this is a mild structural overlap only.

---

### Cluster I — SLE in Two Questions (2 questions)

| Q# | Type | Focus |
|----|------|-------|
| Q10 | choice | SLE disease ontology hierarchy in MONDO/MeSH |
| Q15 | summary | ClinVar variant landscape of monogenic SLE genes |

Different angles (ontology hierarchy vs. genomic variants), different DB combos. The overlap is the disease name only. Low concern unless SLE appears in any additional questions beyond these two.

---

### Cluster J — PubTator Disease+Gene Article Count (2 questions)

| Q# | Type | Question | DBs |
|----|------|----------|-----|
| Q19 | choice | Which MPS type has most PubMed articles with co-annotated genes in PubTator? | pubtator, pubmed, ncbigene |
| Q47 | factoid | How many PubMed articles are co-annotated with Cockayne syndrome AND ERCC6 in PubTator? | mesh, pubtator, pubmed |

Both retrieve article counts from PubMed filtered by disease and gene co-annotation in PubTator. Q19 compares five disease types (choice); Q47 retrieves a single count (factoid). Mild overlap in data access pattern.

---

### Cluster K — "Which bacterial taxon has most X?" Pattern (2 questions)

| Q# | Type | Question | DBs |
|----|------|----------|-----|
| Q16 | choice | Which of 4 bacterial orders has most nifH/nifD genes? | ncbigene, taxonomy |
| Q50 | choice | Which of 4 ESKAPE species has most antibiotic resistance drug classes? | taxonomy, amrportal |

Both are choice questions asking which bacterial taxonomic group has the highest count of some biological feature. Different domains (nitrogen fixation genes vs. AMR elements) and different DB combos. Low concern.

---

## Keyword Category Imbalance

Even setting redundancy aside, the **keyword category distribution is skewed**:

| Category | Count | % |
|----------|-------|---|
| Biological process | 22 | 44% |
| Disease | 18 | 36% |
| Molecular function | 8 | 16% |
| Cellular component | 1 | 2% |
| Developmental stage | 1 | 2% |

Only **1 question** addresses cellular component biology (Q33, gas vesicle) and only **1 question** addresses developmental biology (Q17, heterocyst). Domains like structural biology, cell division, transport, immunity, and evolution are either absent or thinly represented. If this question set is intended to evaluate broad biological coverage, these gaps are as significant as the redundancy issues.

---

## Prioritized Replacement Recommendations

Listed from highest to lowest priority:

| Priority | Action | Questions to Replace | Rationale |
|----------|--------|---------------------|-----------|
| 1 | Replace 2 of 3 ClinVar summary clones | Q15 or Q21, Q29 | Near-identical summary templates; highest structural redundancy |
| 2 | Replace one of Q3/Q31 | Q3 (or Q31) | Structural clone: same DBs (uniprot+rhea), same type (factoid), same pattern |
| 3 | Replace Q8 | Q8 | BacDive+MediaDive combo duplicated; Q17+Q48 sufficient for these DBs |
| 4 | Replace Q18 or Q50 | Q18 | AMR combo duplicated; Q34+Q50 sufficient |
| 5 | Replace Q12 | Q12 | GlyCosmos+UniProt combo duplicated; Q44 is more informative (list vs. yes/no) |
| 6 | Add ≥4 questions from under-represented categories | New questions | Cellular component, developmental, structural, immunity, ecology under-covered |

---

## Quick Reference: Structurally Identical DB Combos

| DB Combo | Questions | Action |
|----------|-----------|--------|
| `uniprot + rhea` (factoid) | Q3, Q31 | Replace one |
| `bacdive + mediadive` | Q8, Q17 | Replace Q8 |
| `chebi + pubchem + rhea` | Q11, Q45 | Acceptable (different types: factoid vs. summary) |
| `glycosmos + uniprot` | Q12, Q44 | Replace Q12 |
| `clinvar + mondo + ncbigene` | Q15, Q25 | Acceptable (different types: summary vs. choice) |
| `amrportal + taxonomy` | Q18, Q50 | Replace Q18 |
| `pdb + uniprot` | Q28, Q35 | Acceptable (different types: list vs. choice) |