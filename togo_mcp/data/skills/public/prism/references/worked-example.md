# PRISM worked example — dry AMD lipid-transport ∩ druggable pathways

A full run illustrating all five phases, the failure modes encountered, and the required provenance ledger. The question:

> *Are there genes common to (lipid-transport dysfunction in dry AMD) and (pathways controllable by existing drugs)?*

## Phase P — pose as sets

```
Answer = A ∩ B
A = {dAMD-associated} ∩ {lipid transport}     # disease axis ∩ function axis
B = {druggable / in a drug-modulated pathway} # druggability axis
```

Predicate definitions chosen:
- function axis = `human reviewed UniProt where up:classifiedWith ∈ descendants(GO:0006869 "lipid transport")`
- disease axis = `UNION of {PubTator co-occurrence with MeSH D008268}, {NCBI Gene curated "macular degeneration"}, {ClinVar variant→condition}`
- druggability axis = `ChEMBL human SINGLE PROTEIN target` and/or `Reactome lipoprotein-metabolism membership`

The first-pass answer (CETP, ABCA1, APOE, LIPC) was **recall-seeded** and, as Phase R/I later showed, *missed ABCA4* — the gene most faithful to "lipid transport dysfunction" in dAMD. That miss is the entire reason PRISM exists.

## Phase R — reach the full hierarchy

- A keyword-only function axis (`keywords:445 "Lipid transport"`) returned ~180 genes but **silently dropped ABCA1, ABCA4, LCAT, LIPC** (annotated only to child terms like `cholesterol efflux`, `phospholipid translocation`).
- Fix: `GO:0006869 subClassOf+` → 107 descendant terms → fed as `VALUES` into UniProt `up:classifiedWith` → ~270 genes, now **including ABCA1, ABCA4, LCAT, LIPC, SCARB1, NPC1L1, STRA6, CLU**. (templates 1 → 2)

## Phase I — integrate (triangulate the disease axis)

| Source | What survived ∩ function set | Bias exposed |
|--------|------------------------------|--------------|
| PubTator (D008268) | APOE, ABCA4 only | literature volume — buried CETP/ABCA1/LIPC |
| NCBI Gene curation | + CETP, ABCA1, LIPC, APOB, APOC1, SCARB1, ABCG1, CD36, PLTP, VLDLR | broad; a few peripheral (ACE, SLC2A1) |
| ClinVar pathogenicity | ABCA4 only (Stargardt/AMD CUIs) | Mendelian-only; risk loci absent |

The single-source intersection collapsed to `{APOE}` (PubTator) — proof that one axis is not enough. The union recovered the real set.

## Phase S — stitch by ID

Normalized all sets to NCBI Gene ID (UniProt GeneID xref + esearch IDs), intersected on IDs.

## Phase M — measure & audit

### Provenance ledger

| Gene (NCBI ID) | Function (GO:0006869+desc) | Disease axis (source) | Druggability | Tier | Verified |
|----------------|---------------------------|------------------------|--------------|------|----------|
| ABCA4 (24)  | ✓ phospholipid translocation | PubTator + NCBI + **ClinVar pathogenic** (Stargardt/AMD) | visual-cycle modulators (emixustat, ALK-001) — investigational | 3 (mechanistic core) | DB-verified; drug status external |
| CETP (1071) | ✓ cholesteryl ester transfer | NCBI curation (GWAS locus) | CETP inhibitors — ChEMBL3572 | 1 | DB-verified |
| ABCA1 (19)  | ✓ cholesterol efflux | NCBI curation (GWAS locus) | LXR agonists (indirect) — ChEMBL2362986 | 1 | DB-verified |
| APOE (348)  | ✓ lipoprotein transport | PubTator + NCBI | pathway-level only | 2 | DB-verified |
| LIPC (3990) | ✓ lipid metabolism/transport | NCBI curation (GWAS locus) | fibrate/PPARA (indirect) | 2 | DB-verified |
| APOB (338)  | ✓ | NCBI curation | mipomersen/lomitapide | 2 | DB-verified |
| APOC1 (341) | ✓ | NCBI curation | pathway-level | 2 | DB-verified |
| SCARB1 (949)| ✓ | NCBI curation | pathway-level | 2 | DB-verified |
| ABCG1 (9619)| ✓ | NCBI curation | pathway-level | 2 | DB-verified |
| PLTP (5360) | ✓ | NCBI curation | pathway-level | 2 | DB-verified |
| VLDLR (7436)| ✓ | NCBI curation | pathway-level | 2 | DB-verified |
| CD36 (948)  | ✓ | PubTator + NCBI | pathway-level | 2 | DB-verified |
| NPC1L1*     | ✓ | (pathway node) | ezetimibe | 2 | function/drug verified; AMD link weak |

\* shared-pathway druggable node; included as a drug-modulation lever, not a confirmed AMD locus.

### Stratified answer
- **Tier 1 (AMD lipid locus × direct existing drug):** CETP, ABCA1.
- **Tier 2 (AMD lipid locus on a drug-modulated lipoprotein pathway):** APOE, LIPC, APOB, APOC1, SCARB1, ABCG1, PLTP, VLDLR, CD36 (+ pathway levers NPC1L1, LDLR/PCSK9/HMGCR).
- **Tier 3 (mechanistic core; drug investigational):** ABCA4 — the gene most faithful to "lipid-transport dysfunction" in dAMD.

### Honest limits (always state)
- Druggability (ChEMBL) and pathway membership (Reactome) and function (GO/UniProt) and disease links (PubTator/NCBI/ClinVar) are **DB-verified**.
- **AMD effect sizes** require the GWAS Catalog (outside TogoMCP).
- **Drug approval + AMD indication** require ClinicalTrials.gov / labels (outside TogoMCP).

## Failure log (what timed out / returned empty, and the fix)

| Symptom | Cause | Fix that worked |
|---------|-------|-----------------|
| Disease-anchored PubTator×functional-set join timed out | scanned all gene annotations for a high-frequency disease | take top-N disease genes, intersect by ID on read side |
| ClinVar MedGen-name cross-graph join → 0 rows | `www`/no-`www` namespace mismatch | single-graph by condition CUI; or `REPLACE` namespace |
| ClinVar "pathogenic AND macular" → 0 rows | complex-trait risk loci aren't "Pathogenic"; ABCA4 pathogenic load is under "Stargardt" (no "macular" in name) | drop significance filter; read full distribution per gene |
