# QA Error Check Report — All 50 Questions

**Date:** 2026-02-22 (updated)
**Scope:** All 50 questions examined (Q1–Q50)
**Checks performed:** Format validation, logical/coverage-gap analysis, content rules, arithmetic verification, cross-reference with coverage_tracker

---

## Executive Summary

Of the 50 questions examined, **47 passed with no issues** and **3 have minor observations** (no action required). Seven questions that previously had issues (Q4, Q5, Q8, Q10, Q11, Q13, Q17) have been revised and now pass all checks.

**2026-02-22 update:** Four additional questions (Q14, Q28, Q42, Q49) were flagged in a subsequent QA pass and subsequently revised. All 50 questions now pass all checks with no minor observations remaining.

| Status | Count | Questions |
|--------|-------|-----------|
| Clean | 50 | All (Q1–Q50) |
| Minor (no action) | 0 | — |
| Failing | 0 | — |

---

## Revision History

The following 7 questions were flagged in the initial review and subsequently revised. All issues are now resolved.

### Q13 — Was Critical → Now Clean

**Original issues:** (1) Answer contradiction (exact_answer listed 10 genes, ideal_answer said 71); (2) Circular logic — Query 3 VALUES had 11 hand-selected MedGen URIs from incomplete Query 2; (3) Query 2 had LIMIT 50 without ORDER BY.

**Revisions applied:** Body restructured as TOP-N ranking ("Which 5 genes have the most..."). Query 2 now returns all 51 MedGen concepts (no LIMIT, ORDER BY ?cui). Query 3 uses all 51 URIs, returns 190 total genes. New Query 4 ranks top 5 by variant count with GROUP BY/ORDER BY DESC/LIMIT 5. exact_answer lists 5 genes with NCBI Gene IDs. ideal_answer states 190 total and ranks top 5 with counts (529, 255, 242, 222, 149).

**Re-examination verdict:** All three issues resolved. Pipeline is coherent (51 MedGen → 190 genes → top 5). No circular logic, no coverage gaps, no contradictions.

### Q5 — Was High → Now Clean

**Original issues:** (1) Arithmetic discrepancy (137 total genes, only 108 accounted for across 5 orders); (2) Incomplete documentation of organism→order mapping.

**Revisions applied:** Completely restructured as bounded choice question with 5 specific orders. Databases changed to GO + UniProt. Query 2 uses fixed-depth UNION taxonomy navigation (1–5 hops) returning 64 orders. Query 3 verifies total = 432 proteins. arithmetic_verification documents 430/432 gap (0.5%, 2 proteins from deep taxonomy nesting). Choice counts (61+53+14+13+12 = 153) are mutually exclusive by phyla.

**Re-examination verdict:** Both issues resolved. Arithmetic fully documented. Taxonomy navigation approach well-explained. Counterintuitive result (Enterobacterales > Synechococcales) has excellent biological explanation in ideal_answer.

### Q8 — Was High → Now Clean

**Original issues:** (1) Unverified aggregate counts (5,003 strains claimed, no verification query); (2) Query 1 used LIMIT 30.

**Revisions applied:** Query 1 now discovers all oxygen tolerance vocabulary (no LIMIT, no text filter, 10 categories returned). Query 2 uses exact controlled vocabulary VALUES terms. New Query 6 provides arithmetic verification. arithmetic_verification: sum of 3 anaerobic categories = 9,310, unique strains = 8,994, overlap of 316 strains documented. ideal_answer explicitly states "8,994 unique anaerobic strains (with 316 strains annotated under more than one category)."

**Re-examination verdict:** Both issues resolved. Aggregates verified. LIMIT removed. Overlap properly documented.

### Q4 — Was Medium → Now Clean

**Original issue:** Missing arithmetic verification for GROUP BY (Query 3 counted proteins per organism without verifying sum = total).

**Revisions applied:** Arithmetic verification comment block added: sum of 16 organism counts = 33 = total from Query 1. Query 2 GROUP BY also verified: 17 AANAT + 16 ASMT = 33 (no overlap). New Query 4 (ChEBI properties) and Query 5 (GO term hierarchy) add chemical and functional dimensions.

**Re-examination verdict:** Issue resolved. Both GROUP BY queries arithmetically verified.

### Q10 — Was Medium → Now Clean

**Original issue:** Four disease categories are not mutually exclusive; overlap not explained.

**Revisions applied:** Body now specifies "confirmed MeSH TopicalDescriptor mappings." Query 2 joins MONDO with MeSH RDF graph to validate meshv:TopicalDescriptor type. New Query 3 provides arithmetic verification. arithmetic_verification section: sum 482 > unique 346, overlap documented. ideal_answer explicitly explains: "The four categories are not mutually exclusive: immune system disorder is the broadest and contains the other three as subcategories."

**Re-examination verdict:** Issue resolved. Overlap documented in both arithmetic_verification and ideal_answer. Cross-graph validation (MONDO + MeSH) strengthens the question.

### Q11 — Was Medium → Now Clean

**Original issues:** (1) Circular logic concern — hardcoded ChEBI VALUES appeared disconnected from Query 1; (2) result_count semantics ambiguous (COUNT returns 1 row).

**Revisions applied:** Query 1 now returns DISTINCT ?chebiCompound directly (result_count: 64, one row per compound). New Query 2 is arithmetic verification confirming COUNT = 64. Query 3 uses all 64 ChEBI IRIs with clear provenance from Query 1. exact_answer corrected to 24.

**Re-examination verdict:** Both issues resolved. Clear provenance chain: Query 1 (64 ChEBI) → Query 2 (verify 64) → Query 3 (map to 24 PubChem compounds). result_count values are now unambiguous.

### Q17 — Was Medium → Now Clean

**Original issue:** Query 4's result_count: 1 was ambiguous — could mean "1 nitrogen ingredient found" or "1 aggregate row with COUNT = 0."

**Revisions applied:** Query 4 description expanded to multi-line YAML explicitly stating "Returns nitrogenIngredientCount = 0, confirming absence of fixed nitrogen sources." Added `result_value: 0` field. RDF triples section has explicit comment: "MediaDive Query 4 result: nitrogenIngredientCount = 0." ideal_answer now mentions "zero nitrogen-containing ingredients."

**Re-examination verdict:** Issue resolved. The meaning of the COUNT result is now unambiguous across description, result_value, RDF triples, and ideal_answer.

### Q14 — Was W (C03) → Now Clean

**Original issue:** Query 3 used GROUP BY to count proteins per organism but lacked a mandatory arithmetic verification that the sum of per-organism counts equals the total from Query 2 (2,453).

**Revisions applied:** Added Query 4 — a verification SPARQL summing all per-organism counts without LIMIT. Result: totalSum = 2,453, numOrganisms = 561. Arithmetic check passed (2,453 = 2,453). Added a `notes` field documenting that proteins are mutually exclusive by organism.

**Re-examination verdict:** Issue resolved. Arithmetic verification present and documented.

### Q28 — Was F (C07) → Now Clean

**Original issue:** Question used Escherichia coli K-12 (taxon:83333), explicitly prohibited as a famous/well-known model organism.

**Revisions applied:** Replaced with Bacillus subtilis (strain 168, taxon:224308). Verified 7 reviewed KW-0093 proteins in 4–12 range (BIOI, BIOK, BIOW, BIOB, BIOD, BIOF2, BIOF1), with 3 having PDB structures and 4 lacking them (3 + 4 = 7, arithmetic verified). Rewrote body, all SPARQL queries, RDF triples, exact_answer, and ideal_answer. Added biological commentary on B. subtilis using the BioI/BioW/BioK pimelate synthesis route, distinct from the E. coli BioC/BioH pathway.

**Re-examination verdict:** Prohibited organism replaced; arithmetic verified; question fully rewritten with fresh content.

### Q42 — Was W (C10) → Now Clean

**Original issue:** Both SPARQL queries used `bif:contains` text search for "Leigh syndrome" without first checking OLS4 or any structured ontology vocabulary for a disease IRI.

**Revisions applied:** Called `OLS4:search("Leigh syndrome")` → found MONDO:0009723. Replaced NANDO Query 1 `bif:contains` with `skos:closeMatch obo:MONDO_0009723` (structured predicate per NANDO schema). Replaced MedGen Query 2 `bif:contains` with `VALUES ?identifier { "C2931891" }` (CUI discovered via `ncbi_esearch(database=medgen, query="256000[OMIM]")`). The structured NANDO query returned 2 entries vs. 1 from text search — NANDO:2200527 (notification #92) and NANDO:1200175 "Leigh's encephalomyelopathy" (notification #21). Added `vocabulary_discovery` field documenting the lookup workflow. Updated RDF triples, ideal_answer, and result_count (1 → 2).

**Re-examination verdict:** Both queries now use structured identifiers; vocabulary discovery documented; second NANDO entry recovered.

### Q49 — Was F (C11) → Now Clean

**Original issue:** Queries 2 and 3 used GO:0015937 directly without evidence that `OLS4:getDescendants()` was called to check for child terms that would also need to be included.

**Revisions applied:** Called `OLS4:getDescendants(classIri="http://purl.obolibrary.org/obo/GO_0015937", ontologyId="go")` → returned totalElements = 0. GO:0015937 is a leaf term with no descendants. Added `vocabulary_discovery` field documenting the call and its nil result, confirming the single-term query covers 100% of the vocabulary.

**Re-examination verdict:** Issue resolved. Descendant check performed, documented, and confirms the query is exhaustive.

---

## Minor Observations

No minor observations remain. The three previously noted items (Q1 ClinVar wording, Q29 verifiability score, Q30 multi_database score) were reviewed and confirmed to require no action; they are not re-listed here.

---

## Clean Questions (No Issues Found)

All 50 questions pass all checks:

Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q20, Q21, Q22, Q23, Q24, Q25, Q26, Q27, Q28, Q29, Q30, Q31, Q32, Q33, Q34, Q35, Q36, Q37, Q38, Q39, Q40, Q41, Q42, Q43, Q44, Q45, Q46, Q47, Q48, Q49, Q50

All 50 questions pass all checks for format compliance, logical soundness, arithmetic verification, content rules, coverage completeness (vocabulary descendants checked), and content-rule compliance (no prohibited organisms, no unchecked vocabulary hierarchies).

---

## Summary of Checks Performed

For each question, the following were verified:

- **Format:** exact_answer type matches question type; verification_score arithmetic; no zero dimensions; score ≥ 9; passed = true; choice answers exist in choices array; SPARQL metadata complete; RDF triple comments formatted correctly; id matches filename; summary ideal_answer is single paragraph
- **Logic:** No circular reasoning (VALUES from search results in comprehensive queries); no coverage gaps (question scope = query scope); arithmetic verification for GROUP BY queries
- **Content:** No database names in question body; no famous/trivial facts; precise wording with qualifiers; all databases in togomcp_databases_used appear in SPARQL queries
