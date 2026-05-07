# TogoMCP Evaluation Analysis: No Usage Guide Condition

**Date:** 2026-03-01  
**Evaluator LLM:** Claude Opus 4.6 (5 independent evaluation runs)  
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)  
**Scoring:** 4 criteria × 1–5 scale = total 4–20  
**Condition:** `TogoMCP_Usage_Guide()` tool **excluded**; no explicit instructions to call `list_databases()` or `get_MIE_file()` before queries

---

## Executive Summary

Without explicit guidance from the Usage Guide, TogoMCP still delivers a **statistically significant but moderate** improvement over the baseline. Across 250 question–run pairs, the mean total score rises from **14.37 to 15.85** (+1.48, Cohen's *d* = 0.46, Wilcoxon *p* = 0.0015). TogoMCP wins on **60.0%** of evaluations, ties on 16.0%, and loses on 24.0%. This represents a meaningful degradation compared to the full-tool condition (Δ = +2.72, *d* = 0.92, win rate 74.8%) but a clear improvement over the no-MIE condition (Δ = +0.30, *d* = 0.08, win rate 40.8%).

A striking finding is that despite the Usage Guide being excluded, the model **spontaneously called `get_MIE_file()` on 74% of questions** and `list_databases()` on 36%, demonstrating that the tool descriptions alone partially convey the intended workflow. However, the lack of explicit orchestration instruction produces less disciplined, less efficient tool usage — fewer perfect scores, more scattered query strategies, and weaker gains on complex question types.

---

## 1. Overall Score Comparison

| Metric | Baseline | TogoMCP (No Guide) | Δ |
|--------|----------|---------------------|---|
| Mean ± SD | 14.37 ± 1.93 | 15.85 ± 2.76 | +1.48 |
| Win / Tie / Loss | — | 60% / 16% / 24% | — |
| Perfect scores (= 20) | **0 / 250** | **44 / 250** (17.6%) | — |
| Cohen's *d* | — | 0.46 (medium) | — |
| Wilcoxon *p* | — | 0.0015 | — |

The baseline never achieves a perfect score, while TogoMCP reaches 20 on 44 of 250 evaluations (17.6%). However, this is notably lower than the 24.4% (61/250) achieved with the full Usage Guide.

### Score Distributions

```
Baseline:                    TogoMCP (No Guide):
11: ████ (4)                 10: ███ (3)
12: ████████ (37)            11: ████ (4)
13: ████████████ (62)        12: █████████ (26)
14: ██████████ (53)          13: ██████████ (30)
15: █████ (27)               14: █████████ (29)
16: █████ (25)               15: █████████ (29)
17: ███ (17)                 16: ████████████ (36)
18: ██ (12)                  17: ████ (12)
19: ██ (13)                  18: ██████ (18)
                             19: ██████ (19)
                             20: ██████████████ (44)
```

The baseline distribution is tightly clustered around 12–15. The no-guide TogoMCP distribution is bimodal: a broad cluster at 12–16 and a clear peak at 20, reflecting a mix of failed and successful tool-use strategies.

---

## 2. Scores by Question Type

| Type | Baseline | TogoMCP | Δ | Cohen's *d* | Win% | Tie% | Lose% |
|------|----------|---------|---|-------------|------|------|-------|
| **factoid** | 12.84 | 15.66 | **+2.82** | 1.20 | 86% | 14% | 0% |
| **list** | 13.14 | 15.58 | **+2.44** | 0.69 | 62% | 6% | 32% |
| **yes_no** | 15.52 | 16.66 | **+1.14** | 0.34 | 48% | 28% | 24% |
| **choice** | 16.06 | 17.12 | **+1.06** | 0.26 | 64% | 10% | 26% |
| **summary** | 14.30 | 14.22 | **−0.08** | −0.04 | 40% | 22% | 38% |

Factoid questions show the strongest, statistically significant benefit (*d* = 1.20, *p* = 0.001, 86% win rate with 0% losses). List questions also benefit substantially (*d* = 0.69). Summary questions show **no improvement** (Δ = −0.08, 38% loss rate), confirming this as the consistent weakness across all TogoMCP conditions.

---

## 3. Scores by Evaluation Criteria

| Criterion | Baseline | TogoMCP | Δ |
|-----------|----------|---------|---|
| **Recall** | 2.38 | 3.84 | **+1.45** |
| **Precision** | 3.54 | 4.04 | **+0.50** |
| **Repetition** | 4.33 | 4.00 | −0.34 |
| **Readability** | 4.11 | 3.98 | −0.14 |

The pattern is consistent with the other conditions: gains in recall and precision, marginal losses in repetition and readability. The recall gain (+1.45) is the primary driver of improvement, though it is lower than the with-guide condition (+1.92).

### Criteria by Question Type

| Type | Recall Δ | Precision Δ | Repetition Δ | Readability Δ |
|------|----------|-------------|--------------|---------------|
| factoid | **+1.96** | **+0.84** | +0.06 | −0.04 |
| list | **+1.90** | **+0.98** | −0.42 | −0.02 |
| choice | **+1.32** | +0.30 | −0.42 | −0.14 |
| yes_no | **+1.20** | +0.30 | −0.22 | −0.14 |
| summary | +0.88 | +0.06 | **−0.68** | **−0.34** |

Factoid and list questions achieve strong recall and precision gains without significant readability damage. Summary questions suffer the worst repetition penalty (−0.68) — verbose tool output floods the synthesis without adding proportional factual value.

---

## 4. Latency and Cost

### 4.1 Overall

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean time | 7.9 s | 80.1 s | **10.2×** |
| Median time | 7.3 s | 70.8 s | 9.7× |
| Max time | 12.5 s | 263.0 s | — |
| Mean cost | $0.0053 | $0.3768 | **71.5×** |
| Total cost (50 q) | $0.26 | $18.84 | 71.5× |
| Mean input tokens | 340 | 374 | 1.1× |
| Mean output tokens | 283 | 3,231 | 11.4× |

### 4.2 By Question Type

| Type | B time → T time | Ratio | B cost → T cost | Ratio |
|------|----------------|-------|-----------------|-------|
| yes_no | 7.4 → 59.6 s | 8.1× | $0.005 → $0.293 | 62× |
| factoid | 7.0 → 80.5 s | 11.5× | $0.004 → $0.435 | 98× |
| summary | 10.1 → 97.6 s | 9.6× | $0.007 → $0.404 | 57× |
| choice | 7.2 → 78.1 s | 10.9× | $0.005 → $0.385 | 82× |
| list | 7.6 → 84.5 s | 11.1× | $0.005 → $0.366 | 69× |

### 4.3 Cost-Effectiveness

| Type | Score Δ | Extra cost | Score pts / $ |
|------|---------|-----------|---------------|
| **list** | +2.44 | $0.361 | **6.8** |
| **factoid** | +2.82 | $0.431 | **6.5** |
| **yes_no** | +1.14 | $0.289 | 3.9 |
| **choice** | +1.06 | $0.380 | 2.8 |
| **summary** | −0.08 | $0.397 | **−0.2** |

Factoid and list questions offer the best return on investment. Summary questions yield a **negative** return: more money for a worse result.

---

## 5. Tool Calls and Score

### 5.1 Tool Call Volume

| Metric | Value |
|--------|-------|
| Mean tools/question | 12.4 |
| Median tools/question | 10 |
| Range | 1–65 |

### 5.2 Tool Count vs. Score

There is a **significant negative correlation** between tool count and TogoMCP score (Pearson *r* = −0.311, *p* = 0.028; Spearman *ρ* = −0.425, *p* = 0.002).

| Tool Calls | n | Mean Score |
|------------|---|-----------|
| 1–3 | 6 | **18.4** |
| 4–6 | 4 | **18.8** |
| 7–8 | 8 | **16.6** |
| 9–10 | 8 | **15.4** |
| 11–14 | 8 | **15.8** |
| 15–18 | 11 | **14.5** |
| 19+ | 5 | **14.2** |

The sweet spot is **3–6 tool calls** (mean score 18.4–18.8). Beyond 10 calls, scores drop substantially, suggesting excessive chaining reflects struggle rather than thoroughness.

### 5.3 SPARQL Count vs. Score

| SPARQL Calls | n | Mean Score | Mean Δ |
|-------------|---|-----------|--------|
| 0 | 12 | 16.57 | +2.08 |
| 1 | 5 | 16.44 | +1.92 |
| 3 | 6 | **17.70** | **+3.70** |
| 4 | 6 | 16.40 | +1.93 |
| 5–6 | 8 | 13.60 | −0.38 |
| 7+ | 5 | 15.68 | +1.22 |
| 11+ | 4 | 13.78 | +1.00 |

The optimal is 3 SPARQL calls (score 17.7, Δ = +3.7). Questions with 0 SPARQL calls also perform well (16.6) — these rely on NCBI search and other non-SPARQL tools. Questions in the 5–6 SPARQL range perform worst, suggesting an intermediate "struggle zone" where queries are attempted but fail to converge.

### 5.4 Latency vs. Score

Latency correlates negatively with score (Spearman *ρ* = −0.494, *p* = 0.0003). Faster runs tend to indicate cleaner, more targeted queries that produce better results.

---

## 6. Tool Type Effectiveness

### 6.1 Most Frequently Used Tools

| Tool | Invocations | Questions used in |
|------|------------|-------------------|
| `run_sparql` | 213 | 38 (76%) |
| `ncbi_esearch` | 116 | 14 (28%) |
| `get_MIE_file` | 59 | 37 (74%) |
| `search_uniprot_entity` | 55 | 23 (46%) |
| `pubmed:search_articles` | 38 | 10 (20%) |
| `search_chembl_target` | 28 | 6 (12%) |
| `list_databases` | 18 | 18 (36%) |

Note: `TogoMCP_Usage_Guide` was excluded from the tool set, so its invocation count is 0.

### 6.2 Tool Presence vs. Score

| Tool | Used (n) | Score when used | Score when not | Δ |
|------|----------|----------------|---------------|---|
| `list_databases` | 18 | **16.43** | 15.52 | **+0.91** |
| `ols:getDescendants` | 5 | **16.92** | 15.73 | **+1.19** |
| `search_rhea_entity` | 5 | **16.88** | 15.73 | **+1.15** |
| `run_sparql` | 38 | 15.62 | 16.57 | −0.95 |
| `ncbi_esearch` | 14 | 15.66 | 15.92 | −0.27 |
| `get_MIE_file` | 37 | 15.72 | 16.20 | −0.48 |
| `search_uniprot_entity` | 23 | **14.52** | 16.98 | **−2.46** |
| `pubmed:search_articles` | 10 | **14.84** | 16.10 | **−1.26** |

**Interpretation caution:** The negative association of `run_sparql` and `get_MIE_file` with scores is a confound, not a causal effect — harder questions require more SPARQL and schema reading, and these same questions tend to have lower scores. The `search_uniprot_entity` negative association (−2.46) is more diagnostic: heavy reliance on text-based UniProt searches often signals a struggle to formulate clean SPARQL queries.

Positive signals include `list_databases` (+0.91), `ols:getDescendants` (+1.19), and `search_rhea_entity` (+1.15) — structured vocabulary and database discovery tools that align with the Usage Guide's recommended workflow.

---

## 7. Perfect Score Analysis

### 7.1 Baseline: No Perfect Scores

The baseline never achieved a score of 20 across any of the 250 evaluations (5 runs × 50 questions). Its maximum was 19.

### 7.2 TogoMCP: 5 Questions with Perfect 20/20 in All 5 Runs

| Question ID | Type | Question (abbreviated) | Tools | SPARQL |
|-------------|------|------------------------|-------|--------|
| question_018 | list | AMR element symbols for mupirocin resistance | 3 | 1 |
| question_026 | yes_no | 6,7-dimethyl-8-(1-D-ribityl)lumazine in PubChem pteridine class | 13 | 4 |
| question_036 | yes_no | Metachromatic leukodystrophy cross-references in disease ontology | 8 | 3 |
| question_038 | choice | Mouse LGMD gene orthologs and PDB structures | 10 | 4 |
| question_043 | factoid | Approved reactions with 1,4-dihydroxy-2-naphthoic acid in Rhea | 6 | 0 |

**Patterns in perfect-scoring questions:**

- **Type distribution:** 2 yes/no, 1 factoid, 1 list, 1 choice — discrete, verifiable answer types dominate.
- **Low tool count:** Median 8 tools (range 3–13), well below the overall mean of 12.4.
- **Specificity:** Each question targets a named entity in a specific database, allowing clean, focused queries.
- **Clean SPARQL or no SPARQL:** Either zero SPARQL (using search APIs directly) or a small number of well-targeted SPARQL queries.

### 7.3 TogoMCP: 15 Total Questions with ≥1 Perfect Run

An additional 10 questions achieved a score of 20 in at least one of the 5 evaluation runs. These span all question types except summary, further confirming that synthesis-heavy questions resist perfection.

### 7.4 Baseline High Performers

No baseline question reached 20. The highest baseline averages are on choice and yes_no questions about well-known entities (e.g., kinase groups, epilepsy genes), where the LLM's training knowledge is sufficient for a near-correct answer but cannot supply the exact database evidence needed for a perfect score.

---

## 8. When TogoMCP Was Worse Than Baseline

Sixteen of 50 questions (32%) had a lower TogoMCP average than baseline. The 6 largest failures (Δ ≤ −1.5) reveal four failure modes:

### 8.1 Data Dumps Destroying Readability (Δ = −5.4 to −5.8)

**question_030** (choice, Δ = −5.8) and **question_035** (choice, Δ = −5.4): Both questions have correct final answers, but the responses include hundreds of raw data items (PDB IDs, gene lists) inline. Evaluators heavily penalized repetition (−1.8 to −2.4) and readability (−1.2 to −1.4). The baseline, providing a clean prose answer with the correct conclusion, scored substantially higher despite lacking specific evidence.

**Lesson:** Correct answers delivered through data-dump formatting can score worse than clean but less detailed baseline prose.

### 8.2 Self-Contradiction (Δ = −4.8)

**question_007** (yes_no, Δ = −4.8): TogoMCP first answered "Yes" with correct details (ENST00000261866, PDB structures), then reversed to "No," arguing the ChEMBL entry was a placeholder. This self-contradiction destroyed precision and readability scores.

**Lesson:** Without the Usage Guide's structured workflow, the model sometimes second-guesses its own correct findings.

### 8.3 Wrong Database / Misaligned Concepts (Δ = −3.2 to −2.0)

**question_045** (summary, Δ = −3.2): Confused 3-demethylubiquinone with a different intermediate, describing C-methylation instead of O-methylation. **question_034** (summary, Δ = −2.0): Used PubMed literature instead of the AMRportal database, missing specific isolate counts.

**Lesson:** Without guided database selection, the model sometimes queries the wrong data source entirely.

### 8.4 Incomplete Entity Coverage (Δ = −1.0 to −1.6)

**question_017** (yes_no, Δ = −1.6): Failed to find a specific organism in databases and hedged the answer. **question_009** (list, Δ = −1.4): Retrieved 3 of 5 relevant enzymes, missing two that required deeper pathway traversal.

**Lesson:** The model's exploratory search is less thorough without explicit workflow guidance.

---

## 9. Usage Guide Adherence — What Happened Without It?

Since the Usage Guide tool was **excluded**, the question becomes: how much of the intended workflow did the model discover on its own from tool descriptions alone?

### 9.1 Spontaneous Tool Discovery

| Workflow Step | Intended by Guide | Actual Usage | Comparison: With Guide |
|---|---|---|---|
| Read Usage Guide | Required first | **0%** (excluded) | 100% |
| `list_databases` | Required second | **36%** (18/50) | 100% |
| `get_MIE_file` | Required third | **74%** (37/50) | 92% |
| Search tools | Recommended fourth | ~80% | 86% |
| `run_sparql` | Core query tool | **76%** (38/50) | 92% |

The model called `get_MIE_file` on 74% of questions without being told to — the tool's description ("Get the MIE file containing the ShEx schema…") was sufficiently informative to prompt schema reading. However, only 36% called `list_databases` first, versus 100% with the guide. This partial compliance explains the intermediate performance.

### 9.2 Workflow Order

Of the 17 questions where both `list_databases` and `get_MIE_file` were called, 15 (88%) called `list_databases` first — correct order. This suggests the model intuitively understands the discovery-before-schema pattern, but only applies it when it thinks to call both tools.

### 9.3 Impact of Spontaneous MIE Usage

| Subgroup | n | TogoMCP Score | Δ vs Baseline |
|----------|---|--------------|---------------|
| Used `get_MIE_file` | 37 | 15.72 | +1.48 |
| Did not use `get_MIE_file` | 13 | 16.20 | +1.48 |

Surprisingly, the score is identical whether or not `get_MIE_file` was called. This is because the 13 questions *without* MIE tend to be the easier ones that the model could handle with search APIs alone (e.g., NCBI lookups), while the 37 *with* MIE are harder questions where MIE helps but doesn't fully compensate for the missing orchestration guidance. The non-MIE questions also average fewer tools (13.3 vs 12.1), suggesting these are cases where the model correctly identified a simpler path.

---

## 10. Three-Condition Comparison

### 10.1 Head-to-Head Summary

| Metric | Baseline | No Guide (this) | No MIE | With Guide |
|--------|----------|------------------|--------|------------|
| TogoMCP score | — | 15.85 | 14.37 | **16.70** |
| Δ vs baseline | — | **+1.48** | +0.30 | **+2.72** |
| Cohen's *d* | — | **0.46** | 0.08 | **0.92** |
| Significance | — | *p* = 0.0015 | *p* = 0.45 (NS) | *p* < 10⁻⁶ |
| Win rate | — | 60.0% | 40.8% | **74.8%** |
| Loss rate | — | 24.0% | 44.8% | **14.4%** |
| Perfect scores | 0% | **17.6%** | 8.4% | **24.4%** |
| Mean tools/q | — | 12.4 | 20.2 | ~10 |
| Cost/question | $0.005 | $0.377 | $0.483 | $0.429 |
| Time/question | 7.9 s | 80.1 s | 154.1 s | 96.2 s |
| Cost per Δ point | — | **$0.25** | $1.61 | **$0.16** |

### 10.2 Score Improvement by Question Type Across Conditions

| Type | No Guide Δ | No MIE Δ | With Guide Δ |
|------|-----------|----------|-------------|
| **factoid** | +2.82 | +2.22 | **+3.46** |
| **list** | +2.44 | −0.30 | **+2.96** |
| **yes_no** | +1.14 | +1.10 | **+3.32** |
| **choice** | +1.06 | +0.10 | **+3.36** |
| **summary** | −0.08 | −1.64 | **+0.50** |

### 10.3 Key Insights from the Three-Condition Comparison

**The Usage Guide contributes approximately +1.24 score points** (from +1.48 to +2.72). This effect operates through:

1. **Disciplined workflow orchestration.** The guide ensures `list_databases` → `get_MIE_file` → search → SPARQL ordering on every question, whereas the no-guide model only follows this pattern sporadically (36% call `list_databases`). This consistent pipeline is especially valuable for choice (+2.30 uplift from guide), yes/no (+2.18), and list (+0.52) questions.

2. **Reduced tool chaining.** With the guide, mean tool calls are ~10; without, 12.4. The guide helps the model avoid unproductive retry loops, particularly on complex questions.

3. **Better summary question handling.** The guide nudges summary Δ from −0.08 to +0.50 — still the weakest type, but no longer harmful.

**MIE files contribute approximately +1.18 score points** (from +0.30 to +1.48, comparing no-MIE to no-guide). This effect comes from:

1. **Correct SPARQL predicate usage.** Schema examples in MIE files provide exact property paths, preventing guessed predicates that return empty results.

2. **Halved tool chaining.** Without MIE, the system makes 20.2 calls/question; with spontaneous MIE (no guide), 12.4; with full guide, ~10.

3. **Dramatically better list/choice performance.** MIE converts list Δ from −0.30 to +2.44 and choice Δ from +0.10 to +1.06.

**The guide and MIE are complementary but separable.** Even without the guide, spontaneous MIE usage (74% of questions) recovers much of the benefit. The guide's additional value is in ensuring MIE is used *consistently* (92% vs 74%) and in orchestrating the broader workflow.

---

## 11. Is the Increased Cost Justified?

### 11.1 Cost-Benefit Analysis

| Condition | Extra cost/q | Score Δ | Cost/Δ point | Justified? |
|-----------|-------------|---------|-------------|------------|
| No Guide | $0.372 | +1.48 | **$0.25** | **Partially** |
| No MIE | $0.478 | +0.30 | $1.61 | **No** |
| With Guide | $0.424 | +2.72 | **$0.16** | **Yes** |

### 11.2 Rationale

**The no-guide condition is partially justified.** At $0.25 per point of improvement, it is 6.4× more cost-effective than the no-MIE condition ($1.61/point) but 1.6× less cost-effective than the with-guide condition ($0.16/point). The improvement is statistically significant (*p* = 0.0015) and practically meaningful for factoid (Δ = +2.82) and list (Δ = +2.44) questions.

**Where the cost IS justified:**

- **Factoid questions** ($0.43, Δ = +2.82, 86% win, 0% loss): Every dollar spent yields verifiable, database-grounded facts the baseline cannot produce.
- **List questions** ($0.37, Δ = +2.44, 62% win): Structured database retrieval provides complete, ranked answers.
- **Questions requiring database evidence:** Any query where the correct answer depends on specific counts, identifiers, or cross-references that are not in LLM training data.

**Where the cost is NOT justified:**

- **Summary questions** ($0.40, Δ = −0.08, 38% loss): The baseline is equally good or better, at 1/57th the cost.
- **Simple yes/no questions about well-known entities** where the baseline already scores 16+.

**Comparison with the full-guide condition:** Investing the small additional effort of enabling the Usage Guide tool would yield an additional +1.24 points per question at essentially the same cost ($0.43 vs $0.38), making the with-guide configuration strictly dominant.

### 11.3 Latency Considerations

At 80 seconds median (10× baseline), the no-guide condition is actually faster than both the no-MIE condition (154 s, 19×) and the with-guide condition (96 s, 12×). This is because the model, without explicit workflow instructions, sometimes takes shorter but less thorough paths. This speed advantage comes at the cost of lower accuracy, however.

For research workflows with batch processing, 80 seconds per question is acceptable. For interactive use, it remains too slow.

---

## 12. Evaluator Agreement

| Metric | Baseline | TogoMCP |
|--------|----------|---------|
| Mean std per question | 0.65 | 0.68 |
| Max std | 1.34 | 1.67 |

The five independent evaluations show good agreement (mean std < 0.7 for both conditions), lending confidence to the score comparisons. TogoMCP answers are slightly more variable to evaluate, as longer, more detailed responses create more room for evaluator disagreement on precision and presentation quality.

---

## 13. Key Findings and Recommendations

1. **The Usage Guide matters, but the model partially self-discovers the workflow.** Without explicit instructions, the model calls `get_MIE_file` on 74% of questions and achieves a moderate but significant improvement (Δ = +1.48 vs +2.72 with guide). The guide's value is in ensuring *consistent* compliance, not introducing a completely novel workflow.

2. **Factoid and list questions benefit most.** These types see Δ = +2.44 to +2.82 with 62–86% win rates. They should be prioritized for TogoMCP deployment.

3. **Summary questions should bypass TogoMCP or use a simplified pipeline.** With Δ = −0.08 and 38% loss rate, the baseline is as good or better for synthesis-heavy questions.

4. **Fewer, well-targeted tool calls produce better results.** The 3–6 call range achieves mean scores of 18.4–18.8. Beyond 10 calls, scores decline. A tool-count limit or early-termination heuristic could prevent degradation.

5. **Structured vocabulary tools remain underused.** `ols:getDescendants` (score +1.19 when used) and `search_rhea_entity` (+1.15) are highly effective but rarely invoked. The model gravitates toward text-based searches (`search_uniprot_entity`, score −2.46) which are less precise.

6. **Self-contradiction is a new failure mode without the guide.** The worst single failure (question_007, Δ = −4.8) involved the model reversing its own correct answer. The guide's structured workflow helps prevent this by establishing a clear evidence-then-conclusion pattern.

7. **Data dumps are the most common readability killer.** Multiple questions with correct answers scored poorly because raw data was dumped inline. Post-processing or explicit formatting instructions could mitigate this.

8. **Enabling the Usage Guide is the highest-ROI intervention.** It costs nothing extra, reduces latency (80 → 96 s, offset by fewer retries), and improves scores by +1.24 points. There is no reason to operate without it.

9. **The component hierarchy is clear: Guide > MIE > Neither.** With Guide achieves *d* = 0.92; No Guide (with spontaneous MIE) achieves *d* = 0.46; No MIE achieves *d* = 0.08. Both the Usage Guide and MIE files are essential for optimal performance, but MIE provides the larger single-component contribution.

---

*Analysis generated from 5 independent evaluation runs (250 total evaluations) of 50 questions, comparing no-tool baseline vs. TogoMCP without the Usage Guide tool. Reference comparisons drawn from `togomcp_analysis_v2.md` (with guide) and `togomcp_no_mie_analysis.md` (no MIE).*
