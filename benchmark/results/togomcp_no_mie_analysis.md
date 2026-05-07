# TogoMCP Evaluation Analysis: No-MIE Condition

**Date:** 2026-05-05
**Benchmark answers collected:** 2026-05-04 (Sonnet 4.5, `claude-sonnet-4-5-20250929`)
**Evaluator LLM:** Opus 4.7 (`claude-opus-4-7`), 5 independent evaluation runs
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)
**Scoring:** 4 criteria × 1–5 scale = total 4–20
**Condition:** `get_MIE_file()` **disallowed** across all server prefixes (`mcp__togomcp__`, `mcp__togomcp-dev__`, `mcp__claude_ai_TogoMCP-Test__`); Usage Guide and `find_databases` remain available

---

## Executive Summary

Without access to MIE schema files, TogoMCP still delivers a **statistically significant and large** improvement over the baseline. Across 250 question–run pairs, the mean total score rises from **15.28 to 18.24** (+2.96, Cohen's *d* = 1.38, Wilcoxon *p* < 10⁻⁹). TogoMCP wins on **83.2 %** of evaluations, ties on 12.8 %, and loses on only **4.0 %**. This is **dramatically better than rev0's no-MIE condition** (Δ = +0.30, *d* = 0.08, win rate 40.8 %) — the result that prompted rev0 to call MIE "the single most critical tool in the TogoMCP pipeline." That conclusion no longer holds in the new runs.

The mechanism behind the improvement is straightforward: **the model substitutes direct search and SPARQL exploration for the missing schema-reading step**. Mean tool calls per question are 16.9 — higher than WG (12.4) but well below the NG2 condition's 20.9. `find_databases` is called in 100 % of questions (driven by the still-active Usage Guide), and `run_sparql` runs an average of 5.4 times per question without prior schema reading. The catastrophic rev0 failure modes (excessive trial-and-error tool chaining, data-dump readability collapses) **do not reproduce**.

This condition's data validity required a methodology fix: the original `disallowed_tools` rule (single-prefix `mcp__togomcp__get_MIE_file`) was bypassed by an account-level `mcp__claude_ai_TogoMCP-Test__get_MIE_file` alias, leaking 45 calls into the run. The 2026-05-05 enumeration form (all three prefixes blocked) holds: **0 / 50 rows** show any `get_MIE_file` call from any server.

---

## 1. Overall Score Comparison

| Metric | Baseline | TogoMCP (No-MIE) | Δ | TogoMCP (WG)¹ |
|--------|----------|-------------------|---|----------------|
| Mean ± SD | 15.28 ± 2.16 | 18.24 ± 1.83 | +2.96 | 18.55 ± 1.72 |
| Median | 15 | 19 | +4 | 19 |
| Min / Max | 12 / 20 | 13 / 20 | — | 12 / 20 |
| Perfect scores (= 20) | **4 / 250** (1.6 %) | **84 / 250** (33.6 %) | — | 107 / 250 (42.8 %) |

¹ *Reference: from [`togomcp_analysis_v3.md`](togomcp_analysis_v3.md).*

The baseline reaches 20 four times (vs 0 in WG/NG2) — these are choice questions where the LLM's general knowledge happens to be correct (e.g., `question_005` TK kinase group, `question_035` PDB experimental technique). TogoMCP reaches 20 on 33.6 % of evaluations — the lowest perfect-score rate among the four conditions, but still far above any rev0 condition.

### Score distributions

```
Baseline:                        TogoMCP (No-MIE):
12: ██ (20)                      13: ▎ (3)
13: ████ (45)                    14: ▌ (5)
14: ███ (36)                     15: █▊ (17)
15: ████ (46)                    16: ███ (29)
16: ██▌ (28)                     17: ██▍ (24)
17: ██ (23)                      18: ██▊ (28)
18: ██▋ (29)                     19: ██████ (60)
19: █▊ (19)                      20: ████████▍ (84)
20: ▎ (4)
```

Both distributions span the 12–20 range, but TogoMCP's mass is concentrated at 19–20 (144 / 250 = 57.6 %).

---

## 2. Scores by Question Type

| Type | Baseline | TogoMCP | Δ | Cohen's *d* | Win % | Lose % |
|------|----------|---------|---|:-----------:|:-----:|:------:|
| **factoid** | 13.36 | **17.70** | **+4.34** | 2.95 | 98 % | 0 % |
| **list** | 14.18 | 18.16 | **+3.98** | 2.63 | 96 % | 0 % |
| **yes_no** | 16.06 | 19.06 | **+3.00** | 1.06 | 80 % | 10 % |
| **summary** | 15.52 | 17.26 | **+1.74** | 1.25 | 72 % | 6 % |
| **choice** | 17.30 | 19.02 | **+1.72** | 0.89 | 70 % | 4 % |

A pattern that **inverts** the rev0 No-MIE results:

- Rev0: Δ for list was −0.30 (loss zone) and summary was −1.64. Both are now strongly positive (+3.98, +1.74).
- Rev0: choice was +0.10. Now +1.72.
- Rev0: factoid was already the strongest (+2.22). Now +4.34, the highest in this condition.

The largest change is on **list** questions: rev0's "MIE-essential" interpretation was that without schema knowledge the model couldn't write SPARQL for list retrieval. The new runs show the model can produce list answers via `search_uniprot_entity`, `ncbi_esearch`, and `search_chembl_target` — direct lookups that don't require schema reading.

**Choice and yes_no are the most degraded** vs WG: No-MIE delivers Δ = +1.72 / +3.00 vs WG's +3.20 / +4.22. The schema-guided cross-database comparisons that powered WG's choice answers are harder to reproduce without `get_MIE_file`.

---

## 3. Scores by Evaluation Criteria

| Criterion | Baseline | TogoMCP | Δ | Rev0 No-MIE Δ |
|-----------|----------|---------|---|:-------------:|
| **Recall** | 2.04 | 3.77 | **+1.74** | +0.91 |
| **Precision** | 3.73 | 4.60 | **+0.87** | +0.30 |
| **Repetition** | 4.72 | 4.91 | +0.18 | −0.31 |
| **Readability** | 4.79 | 4.96 | +0.16 | −0.60 |

Every criterion now shows a positive delta — including readability and repetition, which were both negative in rev0. The rev0 narrative ("without schema guidance the system generates verbose, artifact-laden responses") **does not hold** in the new runs. The deployed `togomcp` server's tool outputs are clean enough, and the model's tool-output integration is fluent enough, that the no-MIE condition's responses read as well as the baseline's.

---

## 4. Latency and Cost

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean time | 7.8 s | **206 s** | 26× |
| Median time | 7.7 s | 159 s | 21× |
| Max time | 12.5 s | 1056 s | — |
| Mean cost | $0.005 | $0.388 | 75× |
| Mean tool calls | — | 16.9 | — |

**No-MIE is the slowest condition** (206 s mean, vs WG's 137 s and NG2's 183 s). The model's compensatory pattern — issuing many `run_sparql` queries without prior schema reading — accumulates more retries on the SPARQL endpoint. Cost per Δ point is $0.129, modestly worse than WG's $0.108.

### Cost-effectiveness by type

| Type | Δ | Cost/q | pts / $ |
|------|:-:|:------:|:-------:|
| factoid | +4.34 | $0.42 | **10.4** |
| list | +3.98 | $0.40 | 9.9 |
| yes_no | +3.00 | $0.35 | 8.6 |
| summary | +1.74 | $0.42 | 4.2 |
| choice | +1.72 | $0.39 | 4.4 |

Factoid and list are most cost-effective; choice and summary are weakest. Notable that even the worst No-MIE category (choice at 4.4 pts/$) **beats** the best rev0 No-MIE category (summary's $1.61/point in rev0 = 0.6 pts/$ inverted).

---

## 5. Tool Calls and Score

### 5.1 Tool count vs. score

Pearson *r* = −0.33 (Spearman *ρ* = −0.34). Mean tool count is 16.9 (median 16, range 4–60).

| Tool calls | n | Mean score |
|:----------:|:-:|:----------:|
| 1–7 | 8 | **19.32** |
| 8–14 | 15 | 18.93 |
| 15–21 | 18 | 17.39 |
| 22–29 | 5 | 18.28 |
| 30+ | 4 | 17.25 |

Sweet spot is **1–14 tool calls** (mean 19.0). Beyond 15 calls, scores dip to 17.4 — but recover slightly at 22–29 calls (18.28), suggesting that questions which *legitimately* require many tools (heavy retrieval workflows) can still succeed if the queries are well-targeted. The final tier (30+ calls, score 17.25) reflects the genuine struggle zone.

### 5.2 SPARQL queries vs. score

| `run_sparql` calls | n | Mean score |
|:------------------:|:-:|:----------:|
| 0 | **13** | **18.20** |
| 1 | 1 | 16.80 |
| 3 | 5 | 18.36 |
| 4 | 2 | 19.30 |
| 5 | 4 | 17.70 |
| 6–9 | 15 | 18.64 |
| 10–14 | 5 | 18.20 |
| 15+ | 3 | 17.47 |

**Pearson *r*(SPARQL count, score) = 0.002** — essentially zero correlation. As in NG2, removing the MIE-grounding step decouples SPARQL volume from score: the model brute-forces variants until something works, and the volume of attempts no longer signals failure. **13 of 50 questions** (26 %) skip SPARQL entirely and rely on search APIs alone — the highest "no-SPARQL" rate of any condition. These score 18.20 on average, confirming that for many factoid/yes-no questions, search APIs alone are sufficient.

Total SPARQL calls: 272 (mean 5.4/q). Lower than NG2's 343, because the Usage Guide (still active in this condition) keeps the model focused on the discovery → query path even without MIE.

---

## 6. Tool-Type Effectiveness

Tools used in ≥ 5 questions, ranked by mean question score:

| Tool | n questions | Mean score | Verdict |
|------|:-----------:|:----------:|---------|
| `get_graph_list` | 6 | **18.67** | Strong — substitute schema discovery |
| `togoid_convertId` | 10 | 18.40 | Strong (cross-DB ID bridging) |
| `search_chembl_target` | 6 | 18.33 | Strong |
| `run_sparql` | 37 | 18.25 | Universal — moderate |
| `find_databases` | 50 | 18.24 | Universal first-after-Guide |
| `TogoMCP_Usage_Guide` | 50 | 18.24 | Universal first call |
| `search_uniprot_entity` | 24 | 18.17 | Adequate |
| `search_rhea_entity` | 9 | 18.04 | Adequate |
| `ncbi_esummary` | 16 | 17.99 | Adequate |
| `ncbi_esearch` | 26 | 17.92 | Slightly below average |
| `search_reactome_entity` | 7 | 17.86 | Slightly below average |
| `togoid_getAllRelation` | 8 | 17.67 | Below average |
| `search_mesh_descriptor` | 6 | 17.60 | Below average (vs WG's 20.0!) |
| `pubmed:get_article_metadata` | 6 | 16.67 | **Weak — fallback signal** |
| `pubmed:search_articles` | 6 | 16.03 | **Weak — fallback signal** |

Two patterns:

1. **`get_graph_list` is now the highest-scoring power tool** (mean 18.67 across 6 questions). Without `get_MIE_file`, the model uses `get_graph_list` to enumerate available named graphs in a SPARQL endpoint — partially substituting for schema reading. The high mean score suggests this is an effective, learnable workaround.
2. **PubMed fallback tools are again the weakest signal** (mean 15.7–16.7). When the model resorts to literature search, it's typically because structured queries failed — and the literature-grounded answers score lower than database-grounded ones.

Notable: `search_mesh_descriptor` was the perfect-score tool in WG (mean 20.0 on 4 questions). In No-MIE it drops to 17.6 (mean across 6 questions). MeSH lookup alone is insufficient when the downstream SPARQL needs schema knowledge to be precise.

---

## 7. Perfect Score Analysis

### 7.1 Universal-perfect questions (5/5)

**13 of 50 questions** achieved 20/20 on every Opus 4.7 run — fewer than WG (16) and NG1 (17) but on par with NG2 (16):

| Question | Type | Tools | Notes |
|----------|------|:-----:|-------|
| question_007 | yes_no | 18 | SPG11 cross-DB verification |
| question_014 | factoid | 6 | GO hormone activity protein count |
| question_018 | list | 22 | AMR symbols for mupirocin resistance |
| question_020 | yes_no | 4 | Symmachiella dynata genome |
| question_024 | summary | 14 | Gluconeogenesis Rhea reactions |
| question_026 | yes_no | 11 | PubChem pteridine class |
| question_028 | list | 4 | B. subtilis biotin biosynthesis |
| question_038 | choice | 14 | Mouse LGMD orthologs + PDB |
| question_041 | choice | 28 | PKU metabolite identity |
| question_042 | yes_no | 14 | DNA-related |
| question_043 | factoid | 11 | DHNA approved Rhea reactions |
| question_046 | yes_no | 17 | AXIN1 destruction-complex |
| question_050 | choice | 16 | Salmonella enterica AMR |

### 7.2 Characteristics

- **By type:** 5 yes/no, 3 choice, 2 factoid, 2 list, 1 summary. The same skew toward verifiable types as the other conditions.
- **Tool count:** median 14 (range 4–28). Notably, the universal-perfect summary (q024 gluconeogenesis) achieved 20/20 with 14 tools — fewer than NG2's universal-perfect q024 (33 tools), suggesting the Usage Guide's structured workflow is more efficient even without MIE.
- **No baseline reaches 20 in this set.** All 13 universally-perfect questions are clear TogoMCP wins where the database-grounded answer beats the LLM's general knowledge.

### 7.3 Questions where NG2 was universal-perfect but No-MIE was NOT

q003 (heart-attack ChEMBL targets), q023 (MANE Select transcripts), q033 (Notch ligands), q035 (PDB technique), q036 (metachromatic leukodystrophy), q039 (Brugada genes). These are questions where MIE-skipping is *easier* than MIE-blocking — the model in NG2 could have read MIE if it wanted to (and didn't), while in No-MIE it explicitly cannot, and the substitute strategy occasionally falls short.

---

## 8. When TogoMCP Was Worse Than Baseline

**2 of 50 questions** had Δ < 0 (the same count as WG):

### 8.1 question_017 (yes_no, Δ = −2.40) — the canonical failure

> "Does Anabaena sp. DSM 101043 grow in nitrogen-free BG11- medium?"

Same failure as in NG2. Without MIE, the model can't learn that BacDive is the right database for cyanobacteria strain growth conditions. Despite calling `find_databases`, the model doesn't recognize BacDive's specific MediaDive integration; it falls back to general searches and concludes "no specific information." Tool count: 27, SPARQL: 0.

The Usage Guide / `find_databases` discovery pipeline cannot fully substitute for `get_MIE_file` here: the discovery tools tell the model *which* databases exist, not *what* they cover or *how* to query them. MIE files are the only resource that bundles "database X has MediaDive cross-references and BG11- annotations."

### 8.2 question_034 (summary, Δ = −0.20)

AMR resistance summary. The model used `search_articles` and `pubmed` as the dominant tools (consistent with the "PubMed fallback = weak signal" pattern from §6). Δ = −0.20 is essentially evaluator noise; the answer was substantively correct but slightly less polished than the baseline's hedged narrative.

### 8.3 Five questions tied with baseline (Δ = 0.00 to +0.40)

q004 (melatonin pathway), q005 (TK kinase group — baseline already at 18.8), q032 (anaerobe genome), q008 (Chloroflexota BacDive), q016 (Hyphomicrobiales taxonomy). These are mostly **multiple-choice questions where the baseline already has correct answers** (16+) from training knowledge, leaving No-MIE TogoMCP little headroom.

### 8.4 The catastrophic rev0 failures don't reproduce

Rev0's worst-case failures included:
- q005 kinase group: rev0 Δ = −5.8. New: Δ = +0.20 (tied).
- q007 SPG11: rev0 Δ = −5.0 (self-contradiction). New: **Δ = +5.4 (universal-perfect)**.
- q021 proteasome: rev0 Δ = −4.8 (drastically wrong protein count). New: Δ = +1.0 with correct count.

The Sonnet 4.5 model and the question set are unchanged from rev0; the rev0 patterns of "blind SPARQL writing produces wrong predicates" and "self-contradiction without structured workflow" therefore appear to have been resolved by **server-side changes** — substantial MIE schema enrichment, `togomcp` tool error handling improvements (e.g. `4e594cb`), and tool output formatting cleanups. The evaluator change (Opus 4.6 → 4.7) may also contribute by scoring borderline cases differently.

---

## 9. Workflow Compliance

### 9.1 First tool called

**100 % of questions start with `TogoMCP_Usage_Guide`** (50 / 50). The system-prompt directive ("REQUIRED FIRST ACTION") works the same here as in WG.

### 9.2 Step-by-step compliance

| Workflow Step | Tool | Usage Rate |
|---|---|:----------:|
| 1. Read Usage Guide | `TogoMCP_Usage_Guide` | **100 %** (50/50) |
| 2. Database discovery | `find_databases` | **100 %** (50/50) |
| 2b. (Fallback) | `list_databases` | 8 % (4/50) |
| 3. Schema discovery | `get_MIE_file` | **0 %** (excluded) |
| 4. Entity / vocab search | various | ~80 % |
| 5. Structured queries | `run_sparql` | 74 % (37/50) |

The Usage Guide drives uniform discovery: every question reads the guide, then calls `find_databases`. The MIE step is missing by design. After `find_databases`, the model proceeds to a mix of search APIs and SPARQL — substitute strategies that work well on factoid / list questions but less reliably on summary / choice.

### 9.3 The substitute-for-MIE strategies

When the model can't read MIE, it appears to use three substitute strategies (visible in the tool-usage logs):

1. **`get_graph_list` for graph enumeration** (used in 6 questions, mean score 18.67). Tells the model what named graphs exist in the SPARQL endpoint.
2. **`search_*_entity` tools to learn vocabulary** before issuing SPARQL. Most-used: `search_uniprot_entity` (24 questions), `search_chembl_target` (6).
3. **Direct NCBI / PubMed fallback** when SPARQL fails. `ncbi_esearch` 26 questions, `pubmed:search_articles` 6 questions. The PubMed fallbacks are the weakest-scoring strategy (mean 16.0).

The **first strategy is best**, the **third is worst**. A simple rule for No-MIE deployments: prefer `get_graph_list` and structured-vocabulary search over text-based literature fallback.

---

## 10. Three-Condition Comparison (No-MIE / NG2 / WG)

| Metric | Baseline | No-MIE (this) | NG2 | WG |
|--------|----------|:-------------:|:---:|:--:|
| TogoMCP score | — | 18.24 | 18.04 | **18.55** |
| Δ vs baseline | — | +2.96 | +3.22 | **+3.45** |
| Cohen's *d* | — | 1.38 | 1.19 | **1.82** |
| Win rate | — | 83.2 % | 81.2 % | **94.4 %** |
| Loss rate | — | **4.0 %** | 6.0 % | 1.6 % |
| Perfect-score rate | — | 33.6 % | 40.0 % | **42.8 %** |
| Mean tools / q | — | 16.9 | **20.9** | 12.4 |
| Time / q | — | **206 s** | 183 s | 137 s |
| Cost / q | — | $0.388 | $0.405 | $0.380 |
| Cost per Δ point | — | $0.129 | $0.124 | **$0.108** |

**No-MIE has the highest latency** (206 s) but the **lowest loss rate** of the unguided/restricted conditions (4.0 % vs NG2's 6.0 %). The Usage Guide's structured workflow keeps the model focused even when MIE is unavailable.

---

## 11. The MIE-vs-Discovery Decomposition

Comparing No-MIE (Usage Guide + discovery, no MIE) to NG2 (no Usage Guide, no instruction, MIE *available* but rarely used):

| Aspect | No-MIE | NG2 |
|--------|:-----:|:---:|
| `get_MIE_file` usage | 0 % (blocked) | 18 % (rarely chosen) |
| `find_databases` usage | 100 % (Guide-driven) | 10 % (spontaneous) |
| Discovery + schema combined | Discovery only | Neither, mostly |
| Mean score | 18.24 | 18.04 |
| Δ vs baseline | +2.96 | +3.22 |
| Loss rate | 4.0 % | 6.0 % |

**No-MIE and NG2 deliver nearly identical headline scores** but for different reasons:

- No-MIE has *forced* discovery (Usage Guide) but *no* schema reading → moderate-tool-count, lower-variance answers.
- NG2 has *neither* (rarely uses either) → higher-tool-count, higher-variance answers, but slightly higher mean Δ because the unguided model picks more direct strategies that score well on factoid/list.

Neither condition has access to the optimal pipeline (discovery + MIE + SPARQL = WG / NG1). Both substitute, in different ways, and end up at similar outcomes — but **No-MIE is slower and has a lower perfect-score rate**, while NG2 is more variable.

---

## 12. Inter-Run Evaluator Consistency

| Metric | TogoMCP |
|--------|:-------:|
| Mean std per question | **0.52** |
| Max std | 1.30 |
| Questions with std = 0 | 17 |
| Questions with std > 1 | 4 |
| Questions with std > 2 | 0 |

Inter-run agreement is **substantially tighter than rev0** (mean std 0.52 vs rev0's 1.09). Only 4 questions have std > 1 (vs rev0's 2 with std > 2). The Opus 4.7 evaluators agree more consistently than Opus 4.6 did, and the responses themselves are less ambiguous (no data dumps, no self-contradictions).

---

## 13. Is the Increased Cost Justified?

| Condition | Extra cost / q | Score Δ | Cost / Δ point | Verdict |
|-----------|:--------------:|:-------:|:--------------:|:-------:|
| **No-MIE** | $0.382 | +2.96 | $0.129 | ✅ Justified |
| WG | $0.375 | +3.45 | $0.108 | ✅ Strongly justified |

**Yes — the cost is justified**, in stark contrast to rev0's "10× less cost-effective than with-MIE" verdict ($1.61/point). The new $0.129/point is ~12 % worse than WG, not 10× worse.

**Where No-MIE is most attractive:** factoid (10.4 pts/$) and list (9.9 pts/$) questions, where direct retrieval is sufficient and the missing schema-reading step doesn't matter much.

**Where No-MIE is weakest:** summary (4.2 pts/$) and choice (4.4 pts/$) — the cross-database synthesis tasks that benefit most from MIE schema knowledge.

**Comparison with rev0:** the rev0 No-MIE condition was deemed "actively harmful" for summary and list questions (Δ = −1.64 and −0.30). New No-MIE shows Δ = +1.74 and +3.98 on the same types — the harmful-without-MIE pattern is gone.

---

## 14. Key Findings and Recommendations

1. **MIE is no longer "the single most critical tool."** Rev0's headline framing — "MIE files are essential, removing them collapses TogoMCP" — does not hold in the new runs. No-MIE delivers Δ = +2.96 (within 0.5 of WG's +3.45). The model substitutes effectively via `find_databases` + direct search + `run_sparql` exploration.

2. **The Usage Guide remains valuable even without MIE.** No-MIE's 100 % `find_databases` rate, low loss rate (4.0 %), and tighter inter-run variance (std 0.52) are direct consequences of the Usage Guide's structured workflow. Compared to NG2 (which has neither Guide nor instruction), No-MIE achieves similar scores at lower tool count and lower variance.

3. **The catastrophic rev0 failures don't reproduce.** Self-contradictions, data dumps, and trial-and-error tool chains have all been resolved. q005 (rev0 Δ = −5.8) and q007 (rev0 Δ = −5.0) now both score positive in No-MIE.

4. **q017 (Anabaena BacDive query) remains the canonical "MIE-needed" failure.** Without MIE, the model can't learn that BacDive carries MediaDive-integrated growth-condition annotations. This is the single biggest loss case across both NG2 and No-MIE conditions. **Lesson:** for niche-database questions (cyanobacteria strains, AMR-portal-specific resistance, glycoproteomic per-site curation), MIE is still essential.

5. **`get_graph_list` is an effective substitute when MIE is missing.** Used in 6 questions with mean score 18.67 — the highest in the No-MIE tool ranking. Worth highlighting in the manuscript as a discovered workaround.

6. **PubMed search is a tertiary fallback that signals failure.** `pubmed:search_articles` and `pubmed:get_article_metadata` rank as the lowest-mean tools (15.7–16.7). When the model resorts to literature search, it's typically because structured queries failed.

7. **Cost is justified.** $0.129 per Δ point makes No-MIE economically viable for any precision-critical biomedical QA workload, though WG / NG1 are strictly more cost-effective.

8. **For deployments where MIE files are unavailable** (e.g., new endpoints not yet documented), the No-MIE configuration with the Usage Guide active is a reasonable fallback. Plan for a longer median latency (~160 s vs ~110 s in WG) and a slightly higher loss rate, but expect comparable mean accuracy.

---

*Analysis: 5 independent Opus 4.7 evaluation runs × 50 questions = 250 evaluations. Source CSV: `no_mie-2026-05-04.csv` (post-fix data, with `mcp__*__get_MIE_file` blocked across all server prefixes via enumeration); per-run scoring CSVs: `no_mie-2026-05-04-Opus4.7-v{1..5}.csv`. Reference comparison: 2026-02 paper analysis at [`rev0/togomcp_no_mie_analysis.md`](rev0/togomcp_no_mie_analysis.md).*
