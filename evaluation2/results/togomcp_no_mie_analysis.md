# TogoMCP Evaluation Analysis: No-MIE Condition

**Date:** 2026-03-01  
**Evaluator LLM:** Claude Opus 4.6 (5 independent evaluation runs)  
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)  
**Scoring:** 4 criteria × 1–5 scale = total 4–20  
**Condition:** `get_MIE_file()` tool **excluded** from all TogoMCP runs

---

## Executive Summary

Without access to MIE schema files, TogoMCP produces a **statistically non-significant** improvement over the baseline. Across 250 question–run pairs, the mean total score rises from **14.07 to 14.37** (+0.30, Cohen's *d* = 0.08, Wilcoxon *p* = 0.45). TogoMCP wins on only **40.8%** of evaluations, ties on 14.4%, and **loses on 44.8%** — nearly as often as it wins. This represents a catastrophic degradation compared to the with-MIE condition (Δ = +2.72, *d* = 0.92, win rate 74.8%). The cost remains substantial (~90× higher than baseline), latency is 19× longer, and the average number of tool calls nearly **doubles** from ~10 to ~20 — yet these extra calls produce worse, not better, results. The core finding is unambiguous: **MIE schema files are the single most important component of the TogoMCP pipeline**, and removing them renders the system's costly tool-use workflow marginally beneficial at best.

---

## 1. Overall Score Comparison

| Metric | Baseline | TogoMCP (no MIE) | Δ | TogoMCP (with MIE)¹ |
|--------|----------|-------------------|---|----------------------|
| Mean ± SD | 14.07 ± 2.29 | 14.37 ± 3.37 | +0.30 | 16.70 ± 2.81 |
| Median | 13.0 | 14.0 | +1.0 | 17.0 |
| Min / Max | 9 / 20 | 7 / 20 | — | 10 / 20 |
| Perfect scores (= 20) | **1** (0.4%) | **21** (8.4%) | — | **61** (24.4%) |

¹ *From the with-MIE analysis (`togomcp_analysis_v2.md`) for reference.*

The baseline achieves a single perfect score (question_035, choice, one run), while TogoMCP manages 21 — but this is less than a third of the 61 perfects achieved with MIE. The TogoMCP distribution is dramatically more dispersed (SD 3.37 vs. 2.29 for baseline, vs. 2.81 for with-MIE), with a troubling left tail reaching as low as 7 — **below the baseline's minimum of 9**.

**Statistical significance:** The Wilcoxon signed-rank test on per-question means yields *p* = 0.45 (not significant). Cohen's *d* = 0.08 indicates a negligible effect size.

### Score Distributions

```
Baseline:               TogoMCP (no MIE):
 9: █                    7: ██
10: █                    8: ██████
11: █████████████        9: ███████████
12: ██████████████████  10: ██████████
    ████████████████    11: █████████████████████████
    █████████████████   12: █████████████████████████████████
13: ██████████████████  13: ███████████████████
    ████████████████    14: ██████████████████████████████
14: █████████████████   15: ██████████████████████
    ████████            16: ███████████████████
15: █████████████████   17: ███████████
    ████████████        18: ███████████████████████████
16: █████████████████   19: ██████████████
17: █████████████████   20: █████████████████████
    ████████████
18: ███████████
19: ██████████
20: █
```

The baseline distribution is tightly clustered around 12–14. The no-MIE TogoMCP distribution is bimodal: a cluster of failures at 8–13 and a cluster of successes at 18–20, with much wider spread overall.

---

## 2. Scores by Question Type

| Type | Baseline | TogoMCP | Δ | Win% | Lose% | With-MIE Δ¹ |
|------|----------|---------|---|------|-------|-------------|
| **yes_no** | 15.22 | 16.32 | **+1.10** | 48% | 34% | +3.32 |
| **factoid** | 11.96 | 14.18 | **+2.22** | 68% | 20% | +3.46 |
| **list** | 13.02 | 12.72 | **−0.30** | 32% | 50% | +2.96 |
| **summary** | 15.28 | 13.64 | **−1.64** | 12% | 70% | +0.50 |
| **choice** | 14.88 | 14.98 | **+0.10** | 44% | 50% | +3.36 |

The pattern of gains and losses is dramatically different from the with-MIE condition:

- **Factoid** questions remain the strongest beneficiary (+2.22), since they depend on retrievable database facts regardless of schema knowledge.
- **Summary** questions flip from a marginal gain (+0.50 with MIE) to a substantial loss (**−1.64**), with a 70% lose rate. Without schema knowledge, SPARQL queries for summaries produce unreliable data that actively harms answer quality.
- **List** questions also turn negative (−0.30), losing more often than winning (50% vs. 32%).
- **Choice** questions drop from +3.36 to a negligible +0.10.
- **Yes/no** questions retain the most benefit (+1.10) but still at one-third the with-MIE level.

---

## 3. Scores by Evaluation Criteria

| Criterion | Baseline | TogoMCP | Δ | With-MIE Δ¹ |
|-----------|----------|---------|---|-------------|
| **Recall** | 2.30 | 3.21 | **+0.91** | +1.92 |
| **Precision** | 3.49 | 3.79 | **+0.30** | +1.07 |
| **Repetition** | 4.08 | 3.77 | **−0.31** | −0.05 |
| **Readability** | 4.20 | 3.60 | **−0.60** | −0.22 |

The recall gain is halved (+0.91 vs. +1.92 with MIE) — the system retrieves some facts but misses many due to malformed queries. The precision gain is similarly reduced. Most critically, **repetition and readability penalties are much larger** (−0.31 and −0.60 vs. −0.05 and −0.22), indicating that without schema guidance the system generates verbose, artifact-laden responses full of failed query attempts and processing noise.

### Criteria by Question Type

| Type | Recall Δ | Precision Δ | Repetition Δ | Readability Δ |
|------|----------|-------------|--------------|---------------|
| yes_no | +1.06 | +0.56 | −0.16 | −0.36 |
| factoid | +1.58 | +0.78 | +0.20 | −0.34 |
| list | +0.58 | +0.26 | **−0.46** | **−0.68** |
| summary | +0.22 | **−0.30** | **−0.58** | **−0.98** |
| choice | +1.10 | +0.20 | **−0.54** | **−0.66** |

Summary questions suffer a nearly 1-point readability penalty — the largest single-criterion loss in the dataset. The pattern is clear: recall improvements are modest and often offset by degraded presentation quality.

---

## 4. Latency and Cost

### 4.1 Overall

| Metric | Baseline | TogoMCP (no MIE) | Ratio | TogoMCP (with MIE)¹ |
|--------|----------|-------------------|-------|----------------------|
| Mean time | 8.1 s | 154.1 s | **19.0×** | 96.2 s (11.7×) |
| Mean cost | $0.005 | $0.483 | **89.8×** | $0.429 (81×) |
| Output tokens | 291 | 4,063 | 14.0× | 3,100 |
| Mean tool calls | — | 20.2 | — | ~10 |

Without MIE, the system makes **twice as many tool calls** (20.2 vs. ~10), is **60% slower** (154s vs. 96s), and **13% more expensive** ($0.483 vs. $0.429) — all while delivering dramatically worse results. The extra tool calls represent the system's futile attempts to compensate for missing schema knowledge through trial-and-error.

### 4.2 Cost by Question Type

| Type | Time (Base→Togo) | Ratio | Cost (Base→Togo) | Ratio |
|------|-------------------|-------|-------------------|-------|
| yes_no | 6.8 → 110.3 s | 16× | $0.005 → $0.327 | 70× |
| factoid | 7.3 → 155.2 s | 21× | $0.005 → $0.503 | 111× |
| list | 8.2 → 171.4 s | 21× | $0.006 → $0.504 | 91× |
| summary | 10.6 → 170.2 s | 16× | $0.007 → $0.502 | 69× |
| choice | 7.5 → 163.4 s | 22× | $0.005 → $0.578 | 119× |

Choice questions are the most expensive (119× ratio, $0.58/question) despite yielding only +0.10 score improvement — a dismal cost-effectiveness ratio.

---

## 5. Tool Calls and Score

### 5.1 Tool Count vs. Score

There is a **strong negative correlation** between tool count and TogoMCP score (*r* = −0.464, *p* < 0.0001). This is substantially worse than the with-MIE condition (*r* = −0.375).

| Tool Calls | n | Mean Score | Δ (vs. Baseline) |
|------------|---|-----------|-------------------|
| 0–3 | 5 | **18.2** | +0.8 |
| 4–6 | 15 | **18.5** | +4.6 |
| 7–9 | 5 | **18.8** | +6.2 |
| 10–13 | 35 | 16.8 | +2.6 |
| 14–17 | 35 | 14.5 | +0.4 |
| **18+** | **155** | **13.1** | **−0.9** |

The optimal range is **4–9 tool calls** (mean score 18.2–18.8). Critically, **62% of all evaluations** (155/250) fell into the 18+ tool call category, where TogoMCP actually **hurts** performance (Δ = −0.9). Without MIE schemas to guide efficient queries, the system defaults to excessive, poorly-targeted tool chaining.

### 5.2 SPARQL Query Count vs. Score

| SPARQL Calls | n | Mean Score | Δ |
|-------------|---|-----------|---|
| 0 | 30 | **16.6** | +1.8 |
| 1 | 10 | **19.5** | +6.5 |
| 2 | 25 | 13.3 | −0.8 |
| 3 | 30 | 15.0 | −1.0 |
| 4 | 10 | **18.1** | +3.4 |
| 6 | 20 | 15.1 | +1.9 |
| 7+ | 85 | 13.1 | −0.6 |

The sweet spot is **1 SPARQL call** (score 19.5, Δ = +6.5) or **4 calls** (score 18.1). With 7+ SPARQL queries, the system averages only 13.1 — below baseline. The correlation (*r* = −0.382) confirms that more SPARQL queries indicate struggle, not thoroughness.

---

## 6. Tool Type Effectiveness

### 6.1 Most Frequently Used Tools and Their Scores

| Tool | Invocations | Mean Score | Δ | Signal |
|------|------------|-----------|---|--------|
| `run_sparql` | 1,620 | 14.1 | +0.1 | Neutral |
| `ncbi_esearch` | 700 | 14.0 | −0.1 | Neutral |
| `pubmed:search_articles` | 475 | 13.8 | −0.2 | Slight neg |
| `search_uniprot_entity` | 330 | **13.3** | **−0.9** | **Negative** |
| `search_chembl_target` | 200 | **13.0** | **−1.9** | **Negative** |
| `get_sparql_endpoints` | 155 | 13.6 | −0.1 | Neutral |
| `search_rhea_entity` | 150 | 14.2 | −0.2 | Neutral |
| `ncbi_esummary` | 145 | 13.4 | −0.7 | Slight neg |
| `pubmed:get_article_metadata` | 125 | **12.8** | **−1.6** | **Negative** |
| `ols:search` | 95 | **15.8** | +0.9 | Positive |
| `togoid_convertId` | 75 | **12.1** | **−1.6** | **Negative** |
| `ols:getDescendants` | 60 | 13.8 | +1.5 | Positive |
| `search_pdb_entity` | 60 | **11.3** | **−5.1** | **Very neg** |
| `search_mesh_descriptor` | 40 | **15.0** | +1.8 | **Positive** |

### 6.2 High-Score vs. Low-Score Tool Profiles

Comparing evaluations scoring ≥18 (n=62) vs. ≤11 (n=54):

| Tool | High-score (≥18) | Low-score (≤11) | Signal |
|------|:----------------:|:---------------:|--------|
| `ols:search` | **37%** | 11% | **Positive** |
| `search_uniprot_entity` | 24% | **59%** | **Negative** |
| `pubmed:get_article_metadata` | 11% | **43%** | **Negative** |
| `togoid_convertId` | 0% | **33%** | **Negative** |
| `get_sparql_endpoints` | 40% | **76%** | **Negative** |
| `search_chembl_target` | 10% | **28%** | **Negative** |
| `ncbi_esearch` | 47% | **65%** | **Negative** |
| `search_pdb_entity` | 0% | **13%** | **Negative** |
| `run_sparql` | 76% | **100%** | **Negative** |

The pattern is stark: **structured ontology tools** (`ols:search`, `search_mesh_descriptor`) are associated with high scores, while **text-based search tools** (`search_uniprot_entity`, `search_pdb_entity`, `search_chembl_target`) and **cross-database bridging** (`togoid_convertId`) are strongly associated with low scores. The `get_sparql_endpoints` tool appearing in 76% of low-score evaluations suggests the system frequently needs to look up endpoints on-the-fly — a task that MIE files would normally pre-resolve. Every low-scoring evaluation uses `run_sparql` (100%), confirming that the SPARQL queries themselves are poorly formed without schema guidance.

---

## 7. Perfect Score Analysis

### 7.1 Baseline Perfect Scores

The baseline achieved exactly **1 perfect score** (question_035, choice, run 3): "Among X-RAY DIFFRACTION, SOLUTION NMR, and ELECTRON MICROSCOPY, which experimental technique accounts for the greatest number of deposited PDB structures…" This question asks about a well-established fact (X-ray diffraction dominance in PDB) that the LLM already knows with high confidence.

**Near-perfect baseline scores (≥18):** 22 evaluations across 10 questions. These are concentrated in **yes/no** (4 questions) and **choice** (4 questions), all involving well-known entities where LLM knowledge alone suffices.

### 7.2 TogoMCP Perfect Scores

21 evaluations across 9 questions achieved perfect scores:

| Question | Type | Perfect Runs | Tools | Question Topic |
|----------|------|:----------:|:-----:|----------------|
| question_046 | yes_no | **5/5** | 13 | AXIN1 β-catenin destruction complex |
| question_014 | factoid | 4/5 | 5 | GO hormone activity protein count |
| question_036 | yes_no | 3/5 | 10 | Metachromatic leukodystrophy ontology |
| question_041 | choice | 2/5 | 28 | PKU metabolite identity |
| question_020 | yes_no | 2/5 | 15 | Symmachiella dynata genome assembly |
| question_043 | factoid | 2/5 | 13 | 1,4-dihydroxy-2-naphthoate reactions |
| question_010 | choice | 1/5 | 23 | SLE parent disease category |
| question_028 | list | 1/5 | 9 | B. subtilis biotin biosynthesis |
| question_019 | choice | 1/5 | 35 | Mucopolysaccharidosis PubMed co-annotations |

**Patterns:**
- **By type:** yes_no (10 perfects) and factoid (6) dominate; no summary questions achieved perfect scores.
- **Characteristics:** Perfect-scoring questions tend to have **fewer tool calls** (median 13, question_014 achieved perfection with just 5 tools), target **specific named entities**, and map to relatively clean database lookups.
- The single universally perfect question (question_046, 5/5) asks a compound yes/no question about AXIN1's properties across multiple databases — exactly the type of query where cross-referencing NCBI Gene, UniProt, and PDB can definitively verify each claim.

---

## 8. When TogoMCP Was Worse Than Baseline

**22 of 50 questions** (44%) had a lower or equal TogoMCP average than baseline. This is dramatically worse than the with-MIE condition (8 of 50 = 16%). The failures cluster into distinct patterns:

### 8.1 Excessive Tool Chaining with Bad SPARQL (Largest Pattern)

**question_005** (choice, Δ = −5.8): "Which kinase group — AGC, CAMK, CMGC, TK — has the most ChEMBL targets?" The system made 35 tool calls, cycling through repeated `search_chembl_target` calls and malformed SPARQL queries. Without MIE schemas for ChEMBL's structure, it couldn't write correct queries to count targets per kinase group. The baseline correctly answered "TK" using general knowledge.

**question_007** (yes_no, Δ = −5.0): "Does SPG11 satisfy three conditions (ClinVar pathogenic variants, PDB structures, ChEMBL targets)?" Used 26 tools, produced a **contradictory answer** — first confirming all 3 conditions, then reversing to "No." Without schema knowledge, each database check was unreliable, and the synthesis was incoherent.

**question_040** (list, Δ = −1.6): "NCL disease genes with PDB structures in ChEMBL." Made 43 tool calls — the second-highest in the dataset — yet retrieved incomplete data. The extreme tool count signals the system floundering without schema guidance.

### 8.2 Summary Synthesis Failure

**question_021** (summary, Δ = −4.8): "Proteasome protein landscape from UniProt." Produced a **drastically wrong protein count** (286 vs. 53) from malformed SPARQL. The evaluator noted "tool processing visible" — the response contained raw query artifacts.

**question_008** (summary, Δ = −3.4): "Taxonomic distribution of Chloroflexota in BacDive." Used 25 tools but couldn't properly query BacDive's schema without MIE guidance, producing incomplete taxonomy data with poor readability.

**question_015** (summary, Δ = −2.4): "Phage T4 late proteins." Made 42 tool calls and produced unreliable structural method breakdowns, likely from malformed PDB queries.

### 8.3 Schema Misalignment Leading to Wrong Answers

**question_035** (choice, Δ = −4.4): "Which PDB experimental technique is most common for human calmodulin-binding proteins?" Despite the baseline scoring 18.2 using general knowledge (X-ray diffraction dominates), TogoMCP scored only 13.8. Without PDB's schema, it couldn't retrieve method breakdowns and the evaluator noted "could not retrieve actual method breakdown."

**question_038** (choice, Δ = −3.6): "Which LGMD gene ortholog in mouse has the most ClinVar variants?" Scored 9.0 — below baseline's already-low 12.6. The cross-database query (Ensembl→ClinVar) was too complex without schema guidance.

### 8.4 Common Failure Characteristics

| Feature | Worse Questions (n=22) | Better Questions (n=28) |
|---------|:---------------------:|:---------------------:|
| Mean tool calls | **23.7** | **14.9** |
| Mean cost | **$0.51** | **$0.39** |
| Mean latency | **175 s** | **133 s** |
| Summary type | **50%** (6/12 summaries) | **14%** (2/14) |
| Uses `search_uniprot_entity` | **73%** | **43%** |
| Uses `togoid_convertId` | **41%** | **11%** |

The failure profile is clear: higher tool counts, higher costs, and reliance on text-based search tools and cross-database ID conversion — all symptoms of the system attempting to compensate for missing schema knowledge through brute-force trial and error.

---

## 9. TogoMCP Usage Guide Adherence

The Usage Guide prescribes a five-step workflow: **(1) Read Usage Guide → (2) list_databases → (3) get_MIE_file → (4) Search tools → (5) run_sparql.**

### 9.1 Step-by-Step Compliance

| Step | Tool | Usage Rate | Note |
|------|------|:----------:|------|
| 1. Usage Guide | `TogoMCP_Usage_Guide` | **96%** (240/250) | Near-universal |
| 2. Database discovery | `list_databases` | **96%** (240/250) | Near-universal |
| 3. Schema discovery | `get_MIE_file` | **0%** (0/250) | **Excluded by design** |
| 4. Entity/vocab search | Any search tool | **98%** (245/250) | Compensatory over-use |
| 5. Structured queries | `run_sparql` | **88%** (220/250) | High, but queries are poorly formed |

The system faithfully reads the Usage Guide and discovers databases, but with MIE files excluded, it **over-compensates with search tools** (98% vs. 86% with MIE) and runs more SPARQL queries per question — none of which are guided by schema knowledge.

### 9.2 Workflow Patterns

| Pattern | n | Mean Score | Δ | Tools | Cost | Time |
|---------|---|-----------|---|-------|------|------|
| **search_only** | 30 | **16.6** | **+1.8** | 16.5 | $0.51 | 93 s |
| **search + SPARQL** | 215 | 14.1 | +0.1 | 20.9 | $0.48 | 164 s |
| **SPARQL only** | 5 | 14.4 | +0.0 | 13.0 | $0.31 | 112 s |

The **search-only** pattern — where the system uses NCBI, PubMed, and other search APIs without attempting SPARQL — achieves the best results (+1.8). The dominant **search + SPARQL** pattern (86% of evaluations) achieves only +0.1 — essentially no improvement. This directly demonstrates that **SPARQL without MIE is counterproductive**: the queries are poorly formed, produce unreliable data, and the verbose processing adds noise that degrades readability.

### 9.3 Key Violation: Attempting SPARQL Without Schema Knowledge

The Usage Guide explicitly states that step 3 (get_MIE_file) should be called **before** writing SPARQL to learn structured properties, predicates, and examples. With MIE excluded, 88% of evaluations still attempted SPARQL queries — but blind SPARQL writing produced:
- Wrong predicates and property paths
- Missing GRAPH clauses
- Incorrect entity URIs
- Queries that returned empty results, triggering retry cascades

This is visible in the tool count data: the mean tools-per-evaluation is 20.2 (no MIE) vs. ~10 (with MIE), yet scores are 2.33 points lower. The extra 10 tools per question represent failed attempts to iterate toward correct queries without schema guidance.

---

## 10. Is the Increased Cost Justified?

### 10.1 Cost-Effectiveness Summary

| Condition | Cost/Question | Time/Question | Score Δ | Cost per Δ Point |
|-----------|:------------:|:------------:|:-------:|:----------------:|
| Baseline | $0.005 | 8.1 s | — | — |
| TogoMCP (no MIE) | **$0.483** | **154 s** | **+0.30** | **$1.61/point** |
| TogoMCP (with MIE)¹ | $0.429 | 96.2 s | +2.72 | $0.16/point |

### 10.2 Rationale: No, the Cost Is Not Justified (Overall)

In the no-MIE condition, the system spends **$0.483 per question** (89.8× the baseline) and **154 seconds** (19× the baseline) to achieve a **non-significant** +0.30 improvement. At $1.61 per point of improvement, this is **10× less cost-effective** than the with-MIE condition ($0.16/point).

For a 50-question run, the total cost is ~$24 for TogoMCP vs. ~$0.27 for baseline — an $24 premium for approximately **1.5 additional total score points across all 50 questions**. This is not economically justifiable.

### 10.3 Exceptions: Where It Still Helps

The no-MIE condition retains value for **factoid** questions (Δ = +2.22, 68% win rate) and **yes/no** questions (Δ = +1.10, 48% win rate). These question types often depend on NCBI searches and simple database lookups that don't require schema-guided SPARQL. For factoid queries specifically, the cost-effectiveness is $0.22/point — reasonable for precision-critical biomedical fact retrieval.

For **summary** (Δ = −1.64, 70% lose rate) and **list** (Δ = −0.30, 50% lose rate) questions, the no-MIE TogoMCP is **actively harmful** — the baseline is better, cheaper, and faster.

---

## 11. Inter-Run Evaluation Consistency

| Metric | Baseline | TogoMCP |
|--------|----------|---------|
| Mean std per question | 0.77 | 1.09 |
| Questions with std = 0 | 2 | 1 |
| Questions with std > 2 | 0 | 2 |

The inter-run consistency is similar to the with-MIE condition. The two highest-variance TogoMCP questions are:
- **question_038** (choice, std=2.83): Scores ranged from 7 to 14 — reflecting inconsistent cross-database query success.
- **question_011** (factoid, std=2.17): Scores ranged from 10 to 15 — varying quality of DDBJ genome queries.

---

## 12. Comparison: No-MIE vs. With-MIE Conditions

This section directly quantifies the impact of removing `get_MIE_file()` from the pipeline.

### 12.1 Head-to-Head

| Metric | No-MIE | With-MIE | Impact of MIE |
|--------|:------:|:--------:|:-------------:|
| TogoMCP score | 14.37 | 16.70 | **+2.33** |
| Baseline score | 14.07 | 13.98 | +0.09 (same) |
| Score delta | +0.30 | +2.72 | **+2.42** |
| Win rate | 40.8% | 74.8% | **+34.0 pp** |
| Loss rate | 44.8% | 14.4% | **−30.4 pp** |
| Perfect scores | 8.4% | 24.4% | **+16.0 pp** |
| Cohen's *d* | 0.08 | 0.92 | **+0.84** |
| Significance | p = 0.45 | p < 10⁻⁶ | non-sig → highly sig |
| Tool calls/question | 20.2 | ~10 | **−10 calls** |
| Cost/question | $0.483 | $0.429 | **−$0.05** |
| Latency/question | 154 s | 96 s | **−58 s** |

### 12.2 MIE's Effect by Question Type

| Type | No-MIE Δ | With-MIE Δ | MIE Uplift |
|------|:--------:|:----------:|:----------:|
| yes_no | +1.10 | +3.32 | +2.22 |
| factoid | +2.22 | +3.46 | +1.24 |
| list | −0.30 | +2.96 | **+3.26** |
| summary | −1.64 | +0.50 | **+2.14** |
| choice | +0.10 | +3.36 | **+3.26** |

MIE has the largest impact on **list** and **choice** questions (+3.26 each), where schema-guided SPARQL is essential for retrieving structured, comparable data. Even **summary** questions flip from harmful (−1.64) to marginally helpful (+0.50).

### 12.3 MIE's Mechanism of Action

The data reveals three mechanisms by which MIE files improve performance:

1. **Fewer, better-targeted SPARQL queries.** With MIE, the system writes correct queries from the start; without MIE, it iterates blindly, doubling tool calls (20 vs. 10) while achieving worse results.

2. **Correct predicate and property path usage.** Schema examples in MIE files show exact property paths (e.g., `up:classifiedWith`, `cco:hasExperiment`). Without them, the system guesses at predicates, producing queries that return empty or wrong results.

3. **Better readability through cleaner processing.** With MIE, fewer tool calls mean less processing noise in the final response. The readability penalty is −0.22 with MIE vs. −0.60 without — nearly 3× worse.

---

## 13. Key Findings and Recommendations

1. **`get_MIE_file()` is the single most critical tool in the TogoMCP pipeline.** Removing it collapses the improvement from large and significant (*d* = 0.92) to negligible and non-significant (*d* = 0.08), while increasing cost and latency. **MIE must never be optional.**

2. **Without MIE, SPARQL is counterproductive.** The search+SPARQL workflow (86% of evaluations) achieves only Δ = +0.1. The search-only workflow achieves Δ = +1.8. If MIE is unavailable, the system should be configured to **avoid SPARQL entirely** and rely on search APIs alone.

3. **Excessive tool calls are a diagnostic signal of failure.** 62% of evaluations used 18+ tools and scored below baseline. The system's retry behavior — triggered by failed SPARQL queries — actively harms performance. A tool-count limit (e.g., max 12 calls) would prevent the worst degradation.

4. **Summary and list questions should not use no-MIE TogoMCP.** With 70% and 50% loss rates respectively, the baseline is simply better for these question types without schema guidance.

5. **Factoid questions remain the strongest use case** even without MIE (Δ = +2.22, 68% win rate), particularly when they map to NCBI or simple database lookups that don't require SPARQL.

6. **Cost is not justified overall.** At $0.483/question for +0.30 points, the no-MIE condition is 10× less cost-effective than with-MIE. The system pays more, waits longer, and gets essentially the same quality as the baseline.

7. **The Usage Guide should be updated** to treat MIE as a hard prerequisite for SPARQL, not an optional recommendation. If MIE reading fails or is unavailable, the guide should instruct the system to fall back to search-only workflows.

---

*Analysis generated from 5 independent evaluation runs (250 total evaluations) of 50 questions, comparing no-tool baseline vs. TogoMCP without `get_MIE_file()` access. Reference comparison to with-MIE condition drawn from `togomcp_analysis_v2.md`.*
