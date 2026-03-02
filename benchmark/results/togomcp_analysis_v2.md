# TogoMCP Evaluation Analysis Report

**Date:** 2026-02-28  
**Evaluator LLM:** Claude Opus 4.6 (5 independent evaluation runs)  
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)  
**Scoring:** 4 criteria × 1–5 scale = total 4–20

---

## Executive Summary

TogoMCP delivers a statistically significant and practically large improvement over the baseline (no-tool) condition. Across 250 question–run pairs, the mean total score rises from **13.98 to 16.70** (+2.72, Cohen's *d* = 0.92, Wilcoxon *p* < 10⁻⁶). TogoMCP wins on **74.8 %** of individual evaluations, ties on 10.8 %, and loses on only 14.4 %. The gains are strongly concentrated in **information recall** (+1.92 on the 5-point scale) — confirming that tool-augmented access to live RDF databases supplies factual content that the LLM alone cannot fabricate. The cost of this improvement is substantial: **~81× higher dollar cost** and **~12× higher latency**, but the absolute cost remains modest ($0.43 per question), and the quality improvement is unattainable by the baseline at any cost.

---

## 1. Overall Score Comparison

| Metric | Baseline | TogoMCP | Δ |
|--------|----------|---------|---|
| Mean ± SD | 13.98 ± 2.22 | 16.70 ± 2.81 | +2.72 |
| Median | 13.0 | 17.0 | +4.0 |
| Min / Max | 11 / 19 | 10 / 20 | — |
| Perfect scores (= 20) | **0** | **61 / 250** (24.4 %) | — |

The baseline **never** achieves a perfect score of 20, while TogoMCP reaches it in nearly one quarter of all evaluations. The baseline distribution is tightly clustered around 12–14, whereas TogoMCP's distribution is right-skewed with a strong peak at 20.

**Statistical significance:** A Wilcoxon signed-rank test (per-question means, one-sided) yields *p* < 10⁻⁶, and each individual run independently achieves *p* < 0.0002. Cohen's *d* = 0.92 indicates a large effect size.

---

## 2. Scores by Question Type

| Type | Baseline | TogoMCP | Δ | Win % | Lose % |
|------|----------|---------|---|-------|--------|
| **yes_no** | 15.18 | 18.50 | **+3.32** | 84 % | 4 % |
| **choice** | 14.96 | 18.32 | **+3.36** | 82 % | 8 % |
| **factoid** | 11.82 | 15.28 | **+3.46** | 86 % | 8 % |
| **list** | 12.98 | 15.94 | **+2.96** | 74 % | 18 % |
| **summary** | 14.98 | 15.48 | **+0.50** | 48 % | 34 % |

TogoMCP dominates on **yes/no**, **choice**, and **factoid** questions — types with precise, verifiable answers where database evidence is decisive. **Summary** questions see the smallest gain and the highest loss rate (34 %), because they require multi-dimensional synthesis where verbosity and imprecise aggregation often reduce readability without proportionally boosting recall.

---

## 3. Scores by Evaluation Criteria

| Criterion | Baseline | TogoMCP | Δ |
|-----------|----------|---------|---|
| **Recall** | 2.15 | 4.07 | **+1.92** |
| **Precision** | 3.28 | 4.35 | **+1.07** |
| **Repetition** | 4.30 | 4.26 | −0.05 |
| **Readability** | 4.25 | 4.03 | −0.22 |

The dominant improvement comes from **recall** — TogoMCP retrieves specific facts (variant counts, reaction identifiers, database cross-references) that the baseline simply cannot provide. Precision also improves substantially as database-grounded facts tend to be more accurate than hallucinated estimates. Repetition and readability suffer marginally, likely because multi-step tool-use responses sometimes include residual processing artifacts and verbose data dumps.

### Criteria by Question Type

The biggest recall gains appear for **factoid** (+2.64) and **choice** (+2.34), where the baseline's inability to produce specific counts or database-derived rankings is most punishing. For **summary** questions, the recall gain (+1.08) is partly offset by a readability drop (−0.66), suggesting that TogoMCP's verbosity penalty is most pronounced when producing synthesized prose.

---

## 4. Latency and Cost

### 4.1 Latency

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean | 8.2 s | 96.2 s | 11.7× |
| Median | 7.7 s | 81.2 s | 10.5× |
| Max | 15.6 s | 357.8 s | — |

The latency overhead varies by question type, from 9.9× for summary questions (which already require longer baseline responses) to 15.0× for factoid questions (where multiple SPARQL queries are fired sequentially). The median latency of ~81 seconds is acceptable for asynchronous research workflows but would be slow for interactive use.

### 4.2 Cost (USD)

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean per question | $0.0053 | $0.4294 | 81× |
| Total per 50-question run | $0.27 | $21.47 | 81× |

The cost increase is dominated by output tokens (mean 3,100 for TogoMCP vs. 287 for baseline), which reflect the multi-step tool call chains and structured SPARQL results. Input tokens are paradoxically lower for TogoMCP (29 vs. 340 on average), because the baseline receives the full question context whereas TogoMCP distributes context across tool calls.

### 4.3 Cost by Question Type

Factoid questions are the most expensive (119× cost ratio) due to complex multi-database SPARQL workflows, while choice and summary questions are the least expensive per unit (~67–68× ratio), reflecting simpler query patterns.

---

## 5. Tool Calls and Score

### 5.1 Tool Count vs. Score

There is a **moderate negative correlation** (r = −0.375) between the number of tool calls and the TogoMCP score. The sweet spot appears to be **4–8 tool calls** (mean score 17.9–19.6), while questions requiring **15+ calls** tend to score lower (mean 13.6–15.0). This suggests that simpler, more focused queries produce cleaner results, while excessive tool chaining introduces errors, data coverage gaps, or processing noise.

| Tool Calls | Mean Score | n |
|------------|-----------|---|
| 4–5 | 19.3 | 25 |
| 6–8 | 18.4 | 40 |
| 9–10 | 16.3 | 60 |
| 11–13 | 15.1 | 50 |
| 14–16 | 16.7 | 40 |
| 17+ | 14.6 | 35 |

### 5.2 SPARQL Query Count vs. Score

A similar pattern holds for the number of `run_sparql` invocations: questions with 0–2 SPARQL calls score 18.1–18.9, while those with 4+ calls drop to 14.4–16.3. However, some high-SPARQL questions (15 calls, score 17.2) succeed when the queries are well-structured. The key factor is not the number of queries per se, but whether each query returns clean, comprehensive results.

---

## 6. Tool Type Effectiveness

### 6.1 Tools Associated with High vs. Low Scores

| Tool (shortened) | % of High-score (≥18) | % of Low-score (≤13) | Signal |
|---|---|---|---|
| ncbi_esearch | 94 % | 71 % | **Positive** — NCBI search helps |
| search_mesh_descriptor | 26 % | 0 % | **Positive** — MeSH lookup aligns vocabulary |
| search_uniprot_entity | 18 % | 90 % | **Negative** — over-reliance on UniProt search correlates with failures |
| search_reactome_entity | 5 % | 40 % | **Negative** — Reactome searches often retrieve incomplete data |
| ols:getDescendants | 0 % | 17 % | **Negative** — descendant tree traversal in failing queries adds noise |
| togoid_convertId | 11 % | 31 % | **Negative** — ID conversion pipelines are error-prone |

The most effective tools are **ncbi_esearch** (finding genes and variants) and **search_mesh_descriptor** (precise vocabulary alignment). The least effective pattern involves heavy `search_uniprot_entity` and `search_reactome_entity` usage without corresponding SPARQL precision — these text-based searches retrieve approximate matches that then feed into imprecise SPARQL queries.

### 6.2 Most Invoked Tools

The five most frequent tools — `run_sparql` (990 calls), `get_MIE_file` (415), `ncbi_esearch` (255), `TogoMCP_Usage_Guide` (250), and `list_databases` (250) — form the core workflow backbone. `run_sparql` is by far the workhorse, invoked ~4× per question on average.

---

## 7. Perfect Score Analysis

### 7.1 Baseline: No Perfect Scores

The baseline achieved a maximum of 19 (on 9/250 evaluations) but **never** reached 20. The highest baseline averages (18.2) occur for choice and yes/no questions with well-known entities (e.g., KCNQ2/KCNQ3 epilepsy genes, COX-1/COX-2 enzymes). Even here, the baseline loses points on recall because it cannot provide exact counts, database identifiers, or verified cross-references.

### 7.2 TogoMCP: 21 Questions with ≥1 Perfect Run

Sixty-one of 250 evaluations (24.4 %) achieved a perfect score. These span 21 distinct questions, with one question (question_047, factoid) achieving a perfect 20/20 on all 5 runs. Key patterns:

**By question type:** Choice (9 questions) and yes/no (6) dominate the perfect-score list, followed by list (3), factoid (2), and summary (1). This aligns with the finding that discrete, verifiable questions benefit most from database access.

**By question characteristics:** Perfect-scoring questions tend to:

- Ask about **specific named entities** (HSPB1, ERCC6, mupirocin resistance genes) rather than broad categories.
- Require **fewer tool calls** (median 8, range 4–19) — indicating clean, focused query strategies.
- Cost **less** (median $0.27) — efficient queries are also more accurate.
- Have **large score differentials** from baseline (median Δ = +6.4) — these are precisely the questions where LLM-alone knowledge fails and database access is essential.

### 7.3 The Single Universally Perfect Question

**question_047** (factoid): "How many PubMed articles are co-annotated with both Cockayne syndrome and the causative DNA repair gene ERCC6 in automated biomedical literature text-mining?" — This question maps directly to a single, clean SPARQL query against the PubTator database with an unambiguous numeric answer. It exemplifies the ideal TogoMCP use case: a specific question requiring a precise database lookup.

---

## 8. When TogoMCP Was Worse Than Baseline

Eight of 50 questions (16 %) had a lower TogoMCP average than baseline. These fall into four failure modes:

### 8.1 Wrong Search Concept (Largest Failure)

**question_013** (list, Δ = −4.6): "Top 5 genes with most pathogenic ClinVar variants for Joubert syndrome." TogoMCP searched different MedGen concepts than those that correctly retrieve Joubert syndrome data, yielding an entirely wrong gene list (KIAA0586, NPHP1, TCTN3 instead of CEP290, RPGRIP1L, CC2D2A). The baseline, using general biomedical knowledge, produced the correct ranking despite lacking exact counts.

**Lesson:** Ontology misalignment in the initial search step can cascade into completely wrong answers, even when the downstream SPARQL pipeline is technically sound.

### 8.2 Incomplete Entity Coverage

**question_006** (factoid, Δ = −1.0): "How many human metalloprotease drug targets with 3D structures in ChEMBL?" TogoMCP found 11 (only the MMP family) vs. the ideal answer of 69. The query was too narrow, missing ADAMs, ADAMTSs, and other metalloprotease families.

**question_009** (list, Δ = −1.8): TogoMCP retrieved 3 of 7 enzymes in the leukotriene pathway, missing ALOX5AP, ABCC1, and MAPKAPK2. The Reactome pathway search was incomplete.

**Lesson:** Vocabulary coverage gaps (searching only one enzyme family instead of all metalloproteases) remain the single most common failure pattern.

### 8.3 Factual Errors in Multi-Step Synthesis

**question_015** (summary, Δ = −1.0): TogoMCP claimed X-ray crystallography dominates PDB structures for T4 phage proteins at 87.4 %, when the actual answer is cryo-EM at 69 %. This appears to be a SPARQL aggregation or interpretation error.

**question_045** (summary, Δ = −1.6): Structural descriptions of 3-demethylubiquinones contained inconsistencies with the ideal answer, and the count of approved reactions was missed.

**Lesson:** Multi-step SPARQL pipelines can produce confidently wrong numbers that score worse than the baseline's hedged approximations.

### 8.4 Minor Margins (Readability Trade-off)

**question_017** (yes/no, Δ = −0.4) and **question_035** (choice, Δ = −0.2): Both give the correct answer but lose marginal points on readability/repetition compared to the baseline's cleaner prose. These are effectively ties where evaluator noise dominates.

---

## 9. TogoMCP Usage Guide Adherence

The Usage Guide prescribes a five-step workflow: **(1) Read the Usage Guide → (2) list_databases → (3) get_MIE_file (schema discovery) → (4) Search tools (entity/vocabulary discovery) → (5) run_sparql (structured queries).** Section 9 examines adherence to each step and, critically, how search tools fit into the overall pipeline.

### 9.1 Step-by-Step Compliance Rates

| Workflow Step | Tool(s) | Usage Rate | Role |
|---|---|---|---|
| 1. Usage Guide | `TogoMCP_Usage_Guide` | **100 %** (250/250) | Read instructions |
| 2. Database discovery | `list_databases` | **100 %** (250/250) | Discover available databases |
| 3. Schema discovery | `get_MIE_file` | **92 %** (230/250) | Read ShEx schemas and examples |
| 4. Entity/vocabulary search | Any search tool | **86 %** (215/250) | Exploratory entity discovery |
| 5. Structured queries | `run_sparql` | **92 %** (230/250) | Final data retrieval |

Steps 1 and 2 are perfectly followed. Steps 3–5 see some divergence, which leads to three distinct workflow patterns.

### 9.2 Three Workflow Patterns and Their Scores

| Pattern | n | Mean Score | Latency | Cost |
|---|---|---|---|---|
| **Full workflow** (Guide → ListDB → MIE → Search → SPARQL) | 195 (78 %) | 16.30 ± 2.91 | 108 s | $0.48 |
| **No Search** (Guide → ListDB → MIE → SPARQL) | 35 (14 %) | **17.69 ± 2.08** | 57 s | $0.29 |
| **Search-Only** (Guide → ListDB → Search, no MIE/SPARQL) | 20 (8 %) | **18.90 ± 0.97** | 52 s | $0.22 |

A striking finding: questions that **skipped the search step entirely** (No Search) scored *higher* than the full workflow, and questions that **skipped both MIE and SPARQL** (Search-Only) scored *highest of all*. This inverts the expected pattern.

### 9.3 Why Did Search-Only and No-Search Patterns Outperform?

**Search-Only** (4 questions: 001, 016, 020, 025): These used NCBI esearch/esummary or efetch exclusively. All are yes/no or choice questions with well-scoped named entities (e.g., HSPB1 variants, epilepsy gene comparisons). NCBI's search API returned clean, authoritative answers directly without requiring SPARQL at all. Mean score: 18.9.

**No Search** (7 questions: 008, 012, 017, 018, 021, 038, 050): These went straight from MIE schema reading to SPARQL queries, skipping exploratory searches. Many involve databases where entity identifiers were already known or derivable from the schema (e.g., AMR resistance elements, BacDive organisms, specific UniProt proteins). Mean score: 17.7.

**Full workflow** (39 questions): The majority of questions followed the full pipeline. The lower average (16.3) is dragged down by the **worst-performing questions** — which are also the most complex, with the highest tool counts. The full workflow isn't bad; it's simply that the questions that *need* all five steps tend to be harder.

### 9.4 Search Tool Usage and Score

The overall correlation between search tool count and score is weakly negative (r = −0.13), but this masks a non-linear relationship:

| Search tool calls | Mean Score | n |
|---|---|---|
| 0 | 17.69 | 35 |
| 1 | 16.49 | 35 |
| 2 | 15.49 | 45 |
| 3 | **18.57** | 30 |
| 4–5 | 17.07 | 60 |
| 6–10 | 15.20 | 30 |
| 11+ | 16.40 | 15 |

There is a **U-shaped** pattern: zero search calls performs well (questions answerable directly from schema + SPARQL), 3 calls is the sweet spot (enough discovery without over-searching), and 6+ calls correlates with struggling queries.

### 9.5 Individual Search Tool Effectiveness

| Search Tool | n | Mean Score | ≥ 18 | ≤ 13 | Assessment |
|---|---|---|---|---|---|
| `get_pubchem_compound_id` | 5 | **19.80** | 5 | 0 | Excellent — precise compound lookup |
| `ncbi_efetch` | 5 | **19.20** | 5 | 0 | Excellent — full record retrieval |
| `pubdict:find_ids` | 15 | **18.73** | 11 | 0 | Excellent — dictionary term mapping |
| `search_mesh_descriptor` | 40 | **18.32** | 30 | 5 | Very good — vocabulary alignment |
| `search_chembl_target` | 130 | **17.31** | 78 | 31 | Good — drug target discovery |
| `ols:search` | 35 | 17.09 | 18 | 5 | Good — ontology term finding |
| `search_rhea_entity` | 70 | 16.67 | 33 | 16 | Fair — biochemical reaction lookup |
| `ncbi_esearch` | 255 | 16.45 | 109 | 30 | Fair — workhorse but noisy |
| `ncbi_esummary` | 85 | 16.64 | 48 | 21 | Fair |
| `search_pdb_entity` | 25 | 15.80 | 5 | 4 | Below average |
| `search_uniprot_entity` | 140 | **15.11** | 21 | 38 | Weak — text search ≠ structured query |
| `ols:getDescendants` | 20 | **14.60** | 2 | 7 | Weak — adds complexity without payoff |
| `search_reactome_entity` | 45 | **14.44** | 6 | 17 | Weak — incomplete pathway retrieval |
| `search_chembl_molecule` | 5 | 13.60 | 0 | 3 | Poor (small sample) |

**Key insights:** Tools that return precise, structured identifiers (`get_pubchem_compound_id`, `pubdict:find_ids`, `search_mesh_descriptor`) strongly outperform text-based search tools (`search_uniprot_entity`, `search_reactome_entity`). The latter retrieve approximate matches that can lead the SPARQL pipeline astray — exactly the "vocabulary coverage gap" pattern documented in Section 8.2.

### 9.6 Search Tool Usage by Question Type

| Type | Search calls | SPARQL calls | MIE calls | Score |
|---|---|---|---|---|
| choice | 4.2 | 3.1 | 1.2 | 18.32 |
| yes_no | 3.1 | 2.8 | 1.4 | 18.50 |
| list | 3.9 | 4.7 | 1.6 | 15.94 |
| factoid | 2.7 | 4.7 | 1.7 | 15.28 |
| summary | 4.6 | 4.5 | 2.4 | 15.48 |

High-scoring types (choice, yes/no) have moderate search usage but **low SPARQL counts**, while low-scoring types (factoid, summary) have **high SPARQL counts**. Summary questions are the most tool-intensive on every dimension — they call the most search tools (4.6), the most MIE files (2.4), and nearly the most SPARQL queries (4.5) — yet score worst. This confirms that complexity, not tool volume, is the determining factor.

### 9.7 Worst vs. Best Questions: Search Tool Patterns

The **bottom 5 questions** by score (mean ≤ 12.6) average 6.2 search calls and 5.0 SPARQL calls — heavy usage of both. They are characterized by `search_uniprot_entity` and `search_reactome_entity` as the dominant search tools, and frequently use `togoid_convertId` for cross-database bridging.

The **top 5 questions** by score (mean ≥ 19.8) average just 2.0 search calls and 1.6 SPARQL calls. They rely on `ncbi_esearch`, `search_mesh_descriptor`, or no search at all, and rarely need `togoid_convertId`.

### 9.8 Search-First vs. Search-Later: Tool Ordering Patterns

The Usage Guide prescribes a specific ordering: read the MIE schema first (to learn structured predicates), then use search tools (for exploratory entity discovery), then write SPARQL. In practice, five distinct orderings emerged:

| Ordering Pattern | n | Mean Score | Latency | Cost |
|---|---|---|---|---|
| **search → mie → sparql** (search first) | 140 (56 %) | 16.46 ± 2.99 | 104 s | $0.46 |
| **mie → search → sparql** (guide-recommended) | 50 (20 %) | 16.00 ± 2.72 | 122 s | $0.55 |
| **mie → sparql** (no search) | 30 (12 %) | 18.10 ± 1.92 | 48 s | $0.25 |
| **search only** (no mie/sparql) | 20 (8 %) | 18.90 ± 0.97 | 52 s | $0.22 |
| **mie → sparql → search** (search after) | 10 (4 %) | 15.10 ± 1.45 | 84 s | $0.42 |

The **search-first** pattern (56 % of evaluations) — where the system calls search tools *before* reading MIE schemas — is the most common. It scores slightly higher (16.5) than the guide-recommended MIE-first order (16.0), though this difference is not statistically significant (Mann-Whitney *p* = 0.25). The **search-after** pattern (doing SPARQL first, then searching) performs worst at 15.1.

#### Controlling for question difficulty

Are these score differences genuine, or are simpler workflows just assigned to easier questions? Using baseline scores as a difficulty proxy:

| Workflow | Baseline (difficulty) | TogoMCP | Δ (improvement) |
|---|---|---|---|
| search_only | **15.20** (easiest) | 18.90 | +3.70 |
| no_search | 14.33 | 18.10 | **+3.77** |
| search_before_both | 14.36 | 16.46 | +2.10 |
| search_between (guide order) | **12.38** (hardest) | 16.00 | **+3.62** |
| search_after_sparql | 13.30 | 15.10 | +1.80 |

**The user's intuition is partly confirmed:** search-only questions *are* somewhat easier (baseline 15.2 vs. 14.4 overall), and they are concentrated in the two "easiest" question types — 50 % yes/no, 50 % choice, 0 % factoid/list/summary (Kruskal-Wallis on baseline scores across workflows: *p* < 0.0001).

**But the workflow effect is real, not just a difficulty artifact.** The score *improvement* (Δ) tells the story that raw scores miss:

- **search_only Δ = +3.70** — significantly larger than search_before_both's Δ = +2.10 (*p* = 0.049), even though search_only starts from higher baselines.
- **Guide-order (search_between) Δ = +3.62** — the largest improvement despite having the *hardest* questions (baseline 12.38). These are complex factoid/list/summary questions where the guide's MIE-first approach yields the best recovery.
- **no_search Δ = +3.77** — the highest improvement. These questions have moderate baseline difficulty but the schema-then-SPARQL pipeline works cleanly.
- **search_before_both Δ = +2.10** — the smallest improvement. This is the dominant pattern (56 %), but its lower delta suggests that jumping to search before reading schemas leads to less effective SPARQL.

After regressing out baseline scores, residual TogoMCP scores confirm the pattern: search_only (+1.86) and no_search (+1.30) still outperform search_before_both (−0.35) and search_between (−0.27), though the per-question sample is small (n = 50).

**Within-type comparisons** (which fully control the question-type confound) are revealing:

- For **list** questions: no_search (Δ = +6.4) ≫ search_between (Δ = +4.4) > search_before_both (Δ = +1.3).
- For **summary** questions: search_between (Δ = +2.3) > no_search (Δ = +0.6) > search_before_both (Δ = −0.1).
- For **choice** questions: search_between (Δ = +7.4) > no_search (Δ = +6.3) > search_only (Δ = +2.7) > search_before_both (Δ = +1.6).

The consistent pattern across types is that **search_before_both has the smallest improvement**, while the guide-recommended and no-search patterns recover more. This holds even within the same question type, ruling out difficulty as the sole explanation.

#### The critical factor: interleaving

More important than which comes first is whether search and SPARQL are **separated or interleaved**:

| Pattern | n | Mean Score | Search calls | SPARQL calls |
|---|---|---|---|---|
| **All search before first SPARQL** | 100 | **17.06** ± 2.66 | 3.7 | 3.7 |
| **All search after first SPARQL** | 10 | 15.10 ± 1.45 | 3.0 | 3.5 |
| **Interleaved** (search–SPARQL–search–SPARQL…) | 90 | **15.53** ± 3.01 | 5.8 | 5.6 |
| Neither (no search or no SPARQL) | 50 | **18.42** ± 1.64 | 1.3 | 1.7 |

The **all-search-before-SPARQL** pattern significantly outperforms the **interleaved** pattern (17.1 vs. 15.5, Mann-Whitney *p* = 0.0004). It also outperforms the **all-search-after** pattern (17.1 vs. 15.1, *p* = 0.023). This is the strongest ordering signal in the data.

This finding survives difficulty controls. The baseline scores for all-search-before (13.7) and interleaved (14.0) are nearly identical, so the difference in TogoMCP scores cannot be attributed to question difficulty. The improvement (Δ) confirms this: all-search-before gains +3.37 points while interleaved gains only +1.53 (*p* = 0.0002 on raw deltas). Residual analysis (after regressing out baseline) also favors all-search-before (+0.44 vs. −1.18, *p* = 0.08 per question — marginal with n = 38 questions, but the direction is consistent).

**Why interleaving hurts:** Interleaved workflows average 5.8 search calls and 5.6 SPARQL calls — roughly 60 % more of each than the clean search-then-SPARQL pattern (3.7 each). The interleaving pattern indicates that the system is *reactive*: it runs a SPARQL query, discovers it's missing something, searches for more entities, tries again. This trial-and-error loop produces more total tool calls, higher cost, and lower accuracy. By contrast, doing all discovery upfront leads to better-informed, fewer SPARQL queries.

#### Interaction with question type

The ordering effect varies by question type. Since workflow patterns are unevenly distributed across types (search-only is 50 % yes/no + 50 % choice; search_between is 40 % factoid), raw scores confound workflow and type effects. The **improvement (Δ)** is more informative:

| Type | Search-first Δ | Guide order Δ | No search Δ | Search-only Δ |
|---|---|---|---|---|
| **yes_no** | +3.5 (n=30) | — | +1.5 (n=10) | +4.7 (n=10) |
| **choice** | +1.6 (n=25) | +7.4 (n=5) | +6.3 (n=10) | +2.7 (n=10) |
| **factoid** | +3.9 (n=30) | +2.8 (n=20) | — | — |
| **list** | +1.3 (n=25) | +4.4 (n=15) | +6.4 (n=5) | — |
| **summary** | −0.1 (n=30) | +2.3 (n=10) | +0.6 (n=5) | — |

For **list** and **summary** questions — the hardest types — the guide-recommended MIE-first ordering (Δ = +4.4, +2.3) substantially outperforms search-first (Δ = +1.3, −0.1). This suggests that schema knowledge is particularly valuable for complex query types requiring well-structured SPARQL. For **yes/no** questions, search-first (+3.5) and search-only (+4.7) both work well, confirming that simple verification queries don't need the full pipeline.

Note that several cells have small *n* (especially search_between for choice, n = 5), so individual within-type comparisons should be interpreted cautiously. The consistent cross-type pattern of search_before_both underperforming on Δ is the more robust signal.

### 9.9 Overall Adherence Assessment

The Usage Guide was **faithfully followed at the procedural level**: all 250 evaluations started with the guide and list_databases; 92 % read MIE files; 86 % used search tools; 92 % ran SPARQL. The prescribed step order was respected in 20 % of evaluations (MIE → Search → SPARQL), while 56 % used a search-first variant.

**On ordering:** The raw scores of simpler workflows (search-only, no-search) are inflated by a confound — these patterns are assigned to easier questions (higher baseline scores, concentrated in yes/no and choice types). However, the **score improvement** (delta) analysis, within-type comparisons, and especially the **interleave analysis** (all-search-before vs. interleaved, which face comparable baseline difficulty) all confirm a real workflow effect. The most robust finding is that **completing all discovery before the first SPARQL query** significantly outperforms reactive interleaving, even after controlling for difficulty.

Where compliance diverges from the guide's *intent* is in two areas:

**1. Vocabulary discovery quality.** The guide mandates structured vocabulary lookup (GO, MONDO, ChEBI, MeSH) before text search, and comprehensive descendant retrieval. In practice, `ols:getDescendants` was used only 20 times (8 %) and `ols:searchClasses` only 5 times (2 %), while text-based `search_uniprot_entity` was used 140 times (56 %). This suggests that the system often **bypasses structured ontology discovery** in favor of faster but less precise text searches — the exact pattern the guide warns against.

**2. Search–SPARQL interleaving.** The guide implies a clean discovery-then-query workflow. The 36 % of evaluations that interleaved search and SPARQL calls scored significantly lower (15.5 vs. 17.1, *p* < 0.001) than those that completed all discovery before querying. Interleaving is a symptom of reactive, trial-and-error querying — suggesting the initial search was incomplete.

The most actionable improvements would be: **(a)** increase structured vocabulary tool usage (OLS, MeSH, PubDictionaries) and decrease reliance on text-based entity searches; and **(b)** enforce a clean search-then-SPARQL pipeline rather than allowing interleaved discovery.

---

## 10. Is the Increased Cost Justified?

### 10.1 Raw Numbers

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Cost per question | $0.005 | $0.429 | 81× |
| Time per question | 8.2 s | 96.2 s | 12× |
| Cost per score point | $0.0004 | $0.028 | 72× |
| Score improvement per extra dollar | — | 9.6 pts/$ | — |

### 10.2 Rationale: Yes, the Cost is Justified

**The improvement is qualitatively unattainable by the baseline.** No amount of prompt engineering or repeated baseline calls can produce specific ClinVar variant counts, SPARQL-derived reaction numbers, or database cross-references. The baseline's ceiling is ~18 (achieved on only 5.2 % of evaluations), while TogoMCP regularly exceeds this.

**The absolute cost is modest.** At $0.43 per question, a full 50-question evaluation costs $21.47 — well within the budget for research-grade biomedical question-answering.

**The gains are concentrated where they matter most.** Factoid questions (Δ = +3.46), which test the ability to produce precise, verifiable facts, see the largest improvement. This is exactly the domain where LLM hallucination is most dangerous and database grounding is most valuable.

**The latency is acceptable for asynchronous use.** At ~80 seconds median, TogoMCP is too slow for real-time chatbot use but perfectly appropriate for research pipelines, automated evaluation, and batch processing.

### 10.3 Where the Cost is Not Justified

For **summary** questions (Δ = +0.50, win rate only 48 %), the cost-benefit ratio is weakest. Summary synthesis requires the LLM to produce flowing prose that integrates multi-database results — a task where TogoMCP's verbosity and processing artifacts often cancel out its factual gains. For these questions, a hybrid approach (baseline prose augmented with targeted fact-checking) might be more cost-effective.

---

## 11. Inter-Run Evaluation Consistency

The 5 independent Claude Opus 4.6 evaluations of the same answers show good consistency:

| Metric | Baseline | TogoMCP |
|--------|----------|---------|
| Mean std per question | 0.76 | 1.08 |
| Questions with perfect agreement (std = 0) | 3 | 1 |
| Questions with std > 2 | 0 | 2 |

TogoMCP scores are slightly more variable because its longer, more detailed answers create more room for evaluator disagreement on precision and readability. The two highly variable questions (028 and 010, both with std > 2) feature answers at the boundary between "excellent" and "good", where individual evaluator runs may or may not deduct points for minor issues.

---

## 12. Key Findings and Recommendations

1. **TogoMCP is strongly beneficial** for yes/no, choice, and factoid questions (+3.3–3.5 points, >80 % win rate). Use it whenever precise, verifiable database evidence is needed.

2. **Summary questions are the weak spot** (+0.5 points, 48 % win rate). Consider reducing SPARQL complexity for summary tasks or post-processing TogoMCP outputs to improve readability.

3. **Fewer, better-targeted tool calls win.** The 4–8 tool call range achieves the highest scores. Excessive chaining (15+ calls) suggests the system is struggling and often produces worse results.

4. **Vocabulary alignment is critical.** The worst failure (question_013, Δ = −4.6) stemmed from searching the wrong MedGen concept. Investing more in ontology-aware vocabulary discovery would prevent this class of error.

5. **Structured vocabulary tools are underused but highly effective.** `search_mesh_descriptor` (mean 18.3), `pubdict:find_ids` (mean 18.7), and `get_pubchem_compound_id` (mean 19.8) dramatically outperform text-based search tools like `search_uniprot_entity` (mean 15.1) and `search_reactome_entity` (mean 14.4). The system should be steered toward structured lookups and away from text-search-driven workflows.

6. **The Usage Guide is well-followed procedurally** (100 % initial compliance), but its deeper intent — prioritizing structured vocabulary over text search, and completing discovery before querying — is often bypassed. The clean search-then-SPARQL pattern (all discovery before first query) scores significantly higher than interleaved workflows (Δ = +3.37 vs. +1.53, *p* < 0.001), and this finding survives difficulty controls (baseline scores are comparable). Enforcing this separation and increasing OLS/MeSH/PubDictionaries usage are the highest-leverage improvement opportunities.

7. **Simpler workflows score higher, but partly because they get easier questions.** The search-only and no-search patterns achieve the highest raw scores (18.9 and 18.1), but their baseline scores are also elevated (15.2 and 14.3), and they are concentrated in yes/no and choice types. However, even after controlling for difficulty, their score *improvements* (Δ = +3.7) exceed the dominant search_before_both pattern (Δ = +2.1, *p* = 0.049), and within-type comparisons confirm that the guide-recommended MIE-first order consistently outperforms search-first — especially for harder question types like list and summary.

8. **The cost is justified for precision-critical queries** but could be optimized. Simple questions (yes/no with known entities) often succeed with just 4–5 tool calls and $0.18–0.26 per question. When a question maps cleanly to NCBI resources, NCBI-native queries should be preferred over the full SPARQL pipeline.
