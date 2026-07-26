# TogoMCP Four-Condition Comparison Analysis

**Date:** 2026-03-01  
**Evaluator LLM:** Claude Opus 4.6 (5 independent evaluation runs per condition)  
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)

---

## Experimental Conditions

| Label | Usage Guide | `list_databases`/`get_MIE_file` instruction | MIE tool available |
|-------|:-----------:|:-------------------------------------------:|:------------------:|
| **With Guide** | ✅ | ✅ (via guide) | ✅ |
| **NG1** (no guide + MIE instr) | ❌ | ✅ (explicit instruction) | ✅ |
| **NG2** (no guide, no instr) | ❌ | ❌ | ✅ |
| **No MIE** | ❌ | ❌ | ❌ |

The key comparison is between **NG1** and **NG2**: both lack the Usage Guide, but NG1 is explicitly told to call `list_databases()` and `get_MIE_file()` before querying. This isolates the effect of the MIE/discovery instruction from the full Usage Guide.

> **Note:** NG1 and NG2 are independent experiment runs (different baseline and TogoMCP answers), so direct per-question score comparisons reflect both instruction effects and run-to-run stochasticity. Overall aggregates are more reliable.

---

## 1. Executive Summary

| Metric | With Guide | NG1 (MIE instr) | NG2 (no instr) | No MIE |
|--------|:----------:|:----------------:|:--------------:|:------:|
| TogoMCP score | **16.70** | **16.62** | 15.85 | 14.37 |
| Δ vs baseline | **+2.72** | **+2.73** | +1.48 | +0.30 |
| Cohen's *d* | **0.92** | **0.93** | 0.46 | 0.08 |
| Wilcoxon *p* | < 10⁻⁶ | **0.000001** | 0.0015 | 0.45 (NS) |
| Win rate | **74.8%** | **75%** | 60% | 40.8% |
| Loss rate | **14.4%** | **19%** | 24% | 44.8% |
| Perfect scores (=20) | **24.4%** | **22.4%** | 17.6% | 8.4% |
| Mean tools/q | ~10 | 12.6 | 12.4 | 20.2 |
| Cost/question | $0.429 | $0.432 | $0.377 | $0.483 |
| Time/question | 96.2 s | 89.5 s | 80.1 s | 154.1 s |
| Cost per Δ point | **$0.16** | **$0.16** | $0.25 | $1.61 |

**The central finding: NG1 ≈ With Guide >> NG2 >> No MIE.**

Adding the explicit `list_databases`/`get_MIE_file` instruction (NG1 vs NG2) recovers nearly the **entire** benefit of the full Usage Guide. NG1's Δ = +2.73 is virtually identical to With Guide's Δ = +2.72, with comparable effect size (*d* = 0.93 vs 0.92), win rate (75% vs 74.8%), and cost-effectiveness ($0.16/point vs $0.16/point).

---

## 2. Scores by Question Type

| Type | With Guide Δ | NG1 Δ | NG2 Δ | No MIE Δ |
|------|:-----------:|:-----:|:-----:|:--------:|
| **factoid** | +3.46 | **+3.80** | +2.82 | +2.22 |
| **choice** | +3.36 | **+3.48** | +1.06 | +0.10 |
| **yes_no** | +3.32 | +2.70 | +1.14 | +1.10 |
| **list** | +2.96 | +2.64 | +2.44 | −0.30 |
| **summary** | +0.50 | **+1.04** | −0.08 | −1.64 |

### Win/Loss Rates by Type

| Type | NG1 Win% | NG1 Lose% | NG2 Win% | NG2 Lose% |
|------|:--------:|:---------:|:--------:|:---------:|
| **factoid** | **88%** | 12% | 86% | 0% |
| **yes_no** | **82%** | 14% | 48% | 24% |
| **choice** | **76%** | 14% | 64% | 26% |
| **list** | **68%** | 28% | 62% | 32% |
| **summary** | **60%** | 28% | 40% | 38% |

### Cohen's *d* by Type

| Type | NG1 *d* | NG1 *p* | NG2 *d* | NG2 *p* |
|------|:-------:|:-------:|:-------:|:-------:|
| **factoid** | **1.36** | 0.003 | **1.20** | 0.001 |
| **choice** | **1.02** | 0.010 | 0.26 | 0.22 |
| **yes_no** | **0.98** | 0.020 | 0.34 | 0.14 |
| **list** | **0.79** | 0.029 | 0.69 | 0.07 |
| **summary** | 0.58 | 0.085 | −0.04 | 0.56 |

**Key observations:**

- **Choice questions** show the largest instruction effect: NG1 *d* = 1.02 vs NG2 *d* = 0.26. These require comparing entities across databases — a task where schema-guided SPARQL is critical.
- **Yes/no questions** similarly benefit (NG1 *d* = 0.98 vs NG2 *d* = 0.34), because consistent MIE reading helps produce confident, evidence-backed verdicts.
- **Factoid questions** are strong in both conditions but still benefit from the instruction (NG1 Δ = +3.80 vs NG2 Δ = +2.82).
- **Summary questions** flip from harmful (NG2 Δ = −0.08) to beneficial (NG1 Δ = +1.04). This is the most dramatic type-level difference and suggests that structured schema knowledge prevents the verbose, error-laden summaries that plagued NG2.
- **List questions** show the smallest instruction effect, likely because list retrieval often works through NCBI search APIs that don't depend heavily on SPARQL schema knowledge.

---

## 3. Scores by Evaluation Criteria

| Criterion | NG1 Δ | NG2 Δ | Instruction effect |
|-----------|:-----:|:-----:|:------------------:|
| **Recall** | **+1.91** | +1.45 | +0.46 |
| **Precision** | **+0.97** | +0.50 | +0.47 |
| **Repetition** | **−0.19** | −0.34 | +0.15 |
| **Readability** | **+0.04** | −0.14 | +0.18 |

The MIE instruction improves every criterion. The most striking effect is on **readability**: NG1 achieves a net-positive readability change (+0.04), while NG2 suffers a deficit (−0.14). This confirms that structured schema knowledge leads to cleaner, more focused responses rather than data-dump-laden output.

### Criteria by Question Type (NG1)

| Type | Recall Δ | Precision Δ | Repetition Δ | Readability Δ |
|------|:--------:|:-----------:|:------------:|:-------------:|
| factoid | **+2.96** | **+1.08** | −0.26 | +0.02 |
| choice | **+2.12** | **+1.22** | −0.24 | **+0.38** |
| list | **+1.82** | **+0.98** | −0.16 | +0.00 |
| yes_no | **+1.66** | **+0.94** | −0.00 | +0.10 |
| summary | +0.98 | +0.64 | −0.30 | −0.28 |

Choice questions actually achieve a **positive** readability change (+0.38), meaning TogoMCP responses are better-written than baseline for this type when guided by MIE schemas.

---

## 4. Latency and Cost

| Metric | With Guide | NG1 | NG2 | No MIE |
|--------|:----------:|:---:|:---:|:------:|
| Time/q | 96.2 s | **89.5 s** | **80.1 s** | 154.1 s |
| Cost/q | $0.429 | $0.432 | $0.377 | $0.483 |
| Output tokens | 3,100 | 3,443 | 3,231 | 4,063 |
| Cost/Δ point | $0.16 | **$0.16** | $0.25 | $1.61 |

NG1 and With Guide have nearly identical cost-effectiveness ($0.16/point). NG2 is cheaper per question ($0.377) but less cost-effective per point of improvement ($0.25).

### Cost-Effectiveness by Type (NG1)

| Type | Δ | Extra cost | pts/$ |
|------|:---:|:---------:|:-----:|
| **choice** | +3.48 | $0.253 | **13.7** |
| **yes_no** | +2.70 | $0.362 | 7.5 |
| **list** | +2.64 | $0.375 | 7.0 |
| **factoid** | +3.80 | $0.578 | 6.6 |
| **summary** | +1.04 | $0.563 | 1.8 |

Choice questions are by far the most cost-effective in NG1 (13.7 pts/$), because they can often be resolved with a few well-targeted SPARQL comparisons.

---

## 5. Tool Usage Comparison

### 5.1 Workflow Compliance

| Tool | NG1 usage | NG2 usage | Difference |
|------|:---------:|:---------:|:----------:|
| `TogoMCP_Usage_Guide` | 0% (excluded) | 0% (excluded) | — |
| `list_databases` | **92%** (46/50) | 36% (18/50) | **+56 pp** |
| `get_MIE_file` | **92%** (46/50) | 74% (37/50) | **+18 pp** |
| `run_sparql` | **90%** (45/50) | 76% (38/50) | **+14 pp** |

The explicit instruction dramatically increases `list_databases` usage (92% vs 36%) and modestly increases `get_MIE_file` (92% vs 74%) and `run_sparql` usage (90% vs 76%).

### 5.2 Tool Invocation Volumes

| Tool | NG1 calls | NG2 calls |
|------|:---------:|:---------:|
| `run_sparql` | **279** | 213 |
| `get_MIE_file` | **96** | 59 |
| `ncbi_esearch` | 65 | **116** |
| `search_uniprot_entity` | 47 | **55** |
| `list_databases` | **46** | 18 |
| `pubmed:search_articles` | 9 | **38** |
| `search_chembl_target` | 15 | **28** |

NG1 makes more SPARQL and MIE calls; NG2 compensates with more NCBI searches, PubMed searches, and ChEMBL searches. This reflects the fundamental strategy difference: **NG1 queries structured RDF databases with schema guidance**, while **NG2 falls back to text-based search APIs** when it lacks schema knowledge.

### 5.3 SPARQL Efficiency

| Metric | NG1 | NG2 |
|--------|:---:|:---:|
| Mean SPARQL calls/q | **5.6** | 4.3 |
| Median SPARQL calls/q | **4** | 4 |
| Spearman(SPARQL, score) | **−0.445** (*p* = 0.001) | −0.227 (*p* = 0.11) |

NG1 makes more SPARQL calls on average, and the negative correlation between SPARQL count and score is stronger. This seems paradoxical, but it reflects that NG1 uses SPARQL more ambitiously on harder questions. The correlation in NG2 is weaker because NG2 often avoids SPARQL entirely for difficult questions (falling back to search APIs), which obscures the relationship.

---

## 6. Perfect Score Analysis

### 6.1 Questions with Perfect 20/20 in All 5 Runs

| Question | Type | NG1 | NG2 | Both |
|----------|------|:---:|:---:|:----:|
| question_026 (PubChem pteridine class) | yes_no | ✅ | ✅ | ✅ |
| question_038 (Mouse LGMD genes + PDB) | choice | ✅ | ✅ | ✅ |
| question_043 (Rhea reactions for DHNA) | factoid | ✅ | ✅ | ✅ |
| question_019 (Mucopolysaccharidosis types) | choice | ✅ | — | NG1 only |
| question_046 (AXIN1 drug target) | yes_no | ✅ | — | NG1 only |
| question_047 (Cockayne syndrome PubTator) | factoid | ✅ | — | NG1 only |
| question_018 (Mupirocin resistance AMR) | list | — | ✅ | NG2 only |
| question_036 (Metachromatic leukodystrophy) | yes_no | — | ✅ | NG2 only |

Three questions achieve universal perfection in both conditions — these represent clean, well-defined database lookups. NG1 has 3 additional universal perfects (6 total vs NG2's 5), and achieves 56 total perfect evaluations vs NG2's 44.

---

## 7. When NG1 Was Worse Than Baseline

NG1 has **10 questions** where TogoMCP < Baseline (vs 16 in NG2). The worst failures:

| Question | Type | Δ | Failure Mode |
|----------|------|:-:|:-------------|
| question_030 | choice | −2.4 | Data dump (gene lists) |
| question_032 | yes_no | −2.4 | Incomplete genome data |
| question_013 | list | −1.4 | Wrong MedGen concept |
| question_015 | summary | −1.4 | Wrong structural technique |
| question_044 | list | −1.4 | Incomplete retrieval |
| question_027 | factoid | −1.2 | Complex multi-DB failure |
| question_034 | summary | −1.2 | Wrong database |
| question_023 | list | −1.2 | MANE transcript errors |
| question_005 | choice | −1.0 | Count discrepancies |
| question_021 | summary | −0.8 | Imprecise aggregation |

**Maximum failure magnitude is −2.4** (NG1) vs **−5.8** (NG2). The MIE instruction eliminates the catastrophic self-contradiction failure (question_007, NG2 Δ = −4.8) and the worst data-dump failures (question_035, NG2 Δ = −5.4).

---

## 8. Head-to-Head: NG1 vs NG2

### 8.1 Direct TogoMCP Score Comparison

Across 50 questions, NG1's mean TogoMCP score is **0.77 points higher** than NG2 (16.62 vs 15.85, Wilcoxon *p* = 0.017).

### 8.2 Largest NG1 Advantages

| Question | Type | NG1 T | NG2 T | Diff | Likely cause |
|----------|------|:-----:|:-----:|:----:|:-------------|
| question_035 | choice | 17.8 | 12.4 | +5.4 | MIE prevents data dump |
| question_019 | choice | 20.0 | 15.0 | +5.0 | Clean SPARQL comparison |
| question_012 | yes_no | 19.6 | 14.8 | +4.8 | Schema-guided GlyCosmos query |
| question_007 | yes_no | 15.6 | 11.2 | +4.4 | Avoids self-contradiction |
| question_017 | yes_no | 16.6 | 12.6 | +4.0 | Better BacDive query |
| question_047 | factoid | 20.0 | 16.0 | +4.0 | Clean PubTator SPARQL |

These are predominantly questions requiring **cross-database SPARQL** or **structured schema knowledge** — exactly where MIE guidance is most valuable.

### 8.3 Cases Where NG2 Outperformed NG1

| Question | Type | NG1 T | NG2 T | Diff | Likely cause |
|----------|------|:-----:|:-----:|:----:|:-------------|
| question_015 | summary | 12.6 | 15.6 | −3.0 | NG2's alternative approach worked |
| question_027 | factoid | 11.2 | 13.6 | −2.4 | Both poor, NG2 less bad |
| question_044 | list | 10.6 | 12.8 | −2.2 | Both poor, NG2 less bad |
| question_003 | factoid | 17.0 | 19.2 | −2.2 | NG2's non-SPARQL path better |

NG2 advantages tend to be on questions where *both* conditions struggle, and NG2's simpler approach (search API instead of failed SPARQL) produces a less-bad result. Only question_003 represents a genuine NG2 win on a high-scoring question.

---

## 9. The Instruction Effect: What Does the MIE Instruction Actually Do?

The comparison between NG1 and NG2 isolates the effect of a single system-prompt instruction: "call `list_databases()` and `get_MIE_file()` before queries."

### 9.1 Quantified Impact

| Metric | NG1 − NG2 effect |
|--------|:-----------------:|
| Score improvement (Δ) | **+1.25 points** |
| Cohen's *d* | +0.47 |
| Win rate | +15 pp |
| Loss rate | −5 pp |
| Perfect score rate | +4.8 pp |
| Worst single failure | −2.4 vs −5.8 (halved) |
| Summary questions | Δ flips from −0.08 to **+1.04** |

### 9.2 Mechanism

The instruction's effect operates through three channels:

1. **Schema-guided SPARQL (primary).** With 92% MIE usage (vs 74%), NG1 writes correct SPARQL predicates from the start. This shows in the SPARQL invocation count (279 vs 213) — NG1 uses SPARQL more often and more effectively.

2. **Database discovery (secondary).** With 92% `list_databases` usage (vs 36%), NG1 starts with awareness of all 22 databases. NG2 often misses relevant databases entirely (e.g., using PubMed instead of AMRportal for resistance data).

3. **Reduced fallback to text search (tertiary).** NG2 compensates for missing schema knowledge with 116 NCBI searches (vs 65 in NG1) and 38 PubMed searches (vs 9). These text-based searches are less precise and often retrieve noisy, incomplete results.

### 9.3 Comparison with the Full Usage Guide

The MIE instruction recovers **~100% of the Usage Guide's benefit** (NG1 Δ = +2.73 vs With Guide Δ = +2.72). The remaining Usage Guide content — workflow ordering rules, search-before-SPARQL guidance, interleaving warnings — appears to be redundant when the model already has schema knowledge. The critical content of the Usage Guide is, effectively, just the instruction to read MIE files.

---

## 10. Four-Condition Cost-Benefit Summary

| Condition | Extra cost/q | Score Δ | Cost/Δ point | Verdict |
|-----------|:-----------:|:-------:|:------------:|:--------|
| **With Guide** | $0.424 | +2.72 | **$0.16** | ✅ Strongly justified |
| **NG1** (MIE instr) | $0.427 | **+2.73** | **$0.16** | ✅ Strongly justified |
| **NG2** (no instr) | $0.372 | +1.48 | $0.25 | ⚠️ Partially justified |
| **No MIE** | $0.478 | +0.30 | $1.61 | ❌ Not justified |

### The Component Value Hierarchy

```
Full system:  Guide + MIE instr + MIE tool  →  Δ = +2.72  ($0.16/pt)
                           ↓ remove Guide
NG1:          MIE instruction + MIE tool     →  Δ = +2.73  ($0.16/pt)   [−0.01]
                           ↓ remove MIE instruction  
NG2:          MIE tool only (spontaneous)    →  Δ = +1.48  ($0.25/pt)   [−1.25]
                           ↓ remove MIE tool
No MIE:       Neither                        →  Δ = +0.30  ($1.61/pt)   [−1.18]
```

The **MIE instruction** is worth +1.25 points. The **MIE tool availability** (spontaneous use at 74%) is worth +1.18 points. The **Usage Guide itself** (beyond the MIE instruction) is worth approximately **zero** additional points.

---

## 11. Recommendations

1. **The MIE instruction is the single most impactful intervention.** A simple "always call `list_databases()` then `get_MIE_file()` before writing SPARQL" instruction recovers 100% of the Usage Guide benefit at zero additional cost.

2. **The full Usage Guide is not necessary** if the MIE instruction is present. Its workflow rules (search ordering, interleaving warnings) are either redundant or insufficiently enforced to matter.

3. **The MIE tool itself is essential.** Even without any instruction, the model spontaneously uses it 74% of the time, yielding a moderate improvement. But consistent use (via instruction) nearly doubles the benefit.

4. **Summary questions remain the weak point** across all conditions. NG1 is the only non-guide condition that makes them marginally positive (+1.04), but even With Guide only achieves +0.50. Consider a specialized pipeline for summary questions.

5. **For cost-constrained deployments**, the ranking is clear: NG1 ≈ With Guide > NG2 >> No MIE. If you must choose one instruction to add to the system prompt, "call `list_databases()` and `get_MIE_file()` before any SPARQL query" is the answer.

---

*Analysis generated from 4 experimental conditions × 5 evaluation runs × 50 questions = 1,000 total evaluations. Reference data for "With Guide" and "No MIE" conditions drawn from `togomcp_analysis_v2.md` and `togomcp_no_mie_analysis.md`.*
