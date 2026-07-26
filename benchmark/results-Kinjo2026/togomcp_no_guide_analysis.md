# TogoMCP Evaluation Analysis: No-Instruction Condition (NG2)

**Date:** 2026-05-05
**Benchmark answers collected:** 2026-05-04 (Sonnet 4.5, `claude-sonnet-4-5-20250929`)
**Evaluator LLM:** Opus 4.7 (`claude-opus-4-7`), 5 independent evaluation runs
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)
**Scoring:** 4 criteria × 1–5 scale = total 4–20
**Condition:** `TogoMCP_Usage_Guide` excluded; system prompt contains **no instruction** to call `find_databases()` or `get_MIE_file()` before querying

---

## Executive Summary

Without any orchestration instruction in the system prompt, TogoMCP still delivers a **statistically significant and large** improvement over the baseline. Across 250 question–run pairs, the mean total score rises from **14.82 to 18.04** (+3.22, Cohen's *d* = 1.19, Wilcoxon *p* < 10⁻⁸). TogoMCP wins on **81.2 %** of evaluations, ties on 12.8 %, and loses on only **6.0 %**. This is **dramatically better than rev0's no-guide condition** (Δ = +1.48, *d* = 0.46, win rate 60 %) and is now within 0.24 points of the WG condition (Δ = +3.45) — a much smaller gap than the 1.24-point gap reported in the 2026-02 paper.

Behind the strong topline result is a **substantively changed strategy**. The model in NG2 essentially **bypasses the discovery and schema-reading steps entirely**: only 10 % of questions touch a discovery tool (`find_databases` or `list_databases`) and only 18 % call `get_MIE_file`. Instead, the model fires direct queries — `run_sparql`, `search_uniprot_entity`, `ncbi_esearch` — and brute-forces its way to the answer. Mean tool calls per question are **20.9** (vs WG's 12.4), with a peak of 90 calls on a single question. Without an explicit instruction, the imperative tool docstrings (e.g., `find_databases`'s "REQUIRED first step") are not enough to drive structured workflow adherence in this model.

---

## 1. Overall Score Comparison

| Metric | Baseline | TogoMCP (NG2) | Δ |
|--------|----------|----------------|---|
| Mean ± SD | 14.82 ± 2.24 | 18.04 ± 2.24 | +3.22 |
| Median | 14 | 19 | +5 |
| Min / Max | 11 / 19 | 12 / 20 | — |
| Perfect scores (= 20) | **0 / 250** | **100 / 250** (40.0 %) | — |
| Cohen's *d* (per-question) | — | **1.19** | very large |
| Wilcoxon (one-sided, paired) | — | *p* < 10⁻⁸ | highly significant |

The baseline never reaches a perfect 20 (max is 19, on 23 evaluations). TogoMCP reaches 20 on 100 / 250 (40.0 %) — only marginally below WG's 42.8 % rate.

### Score distributions

```
Baseline:                 TogoMCP (NG2):
11: ▎ (9)                 12: ▏ (2)
12: █▏ (38)               13: █▏ (12)
13: ▊ (26)                14: █ (11)
14: █▊ (56)               15: █▏ (12)
15: ▉ (29)                16: ███▏ (33)
16: ▉ (28)                17: █▊ (18)
17: ▉ (31)                18: █▌ (17)
18: ▎ (10)                19: ████▎ (45)
19: ▊ (23)                20: █████████▌ (100)
20: (0)
```

The baseline distribution is broad and unimodal at 14–17. The NG2 TogoMCP distribution is bimodal: a substantial cluster at 16–17 and a sharp peak at 20.

---

## 2. Scores by Question Type

| Type | Baseline | TogoMCP | Δ | Cohen's *d* | Win % | Lose % |
|------|----------|---------|---|:-----------:|:-----:|:------:|
| **factoid** | 13.08 | **17.62** | **+4.54** | 2.40 | 100 % | 0 % |
| **list** | 13.66 | 17.94 | **+4.28** | 1.75 | 82 % | 0 % |
| **yes_no** | 15.54 | 18.86 | **+3.32** | 1.00 | 86 % | 10 % |
| **choice** | 16.28 | 18.98 | **+2.70** | 0.94 | 82 % | 6 % |
| **summary** | 15.52 | 16.78 | **+1.26** | 0.70 | 56 % | 14 % |

A different ordering than WG: **factoid and list dominate** here (+4.54 and +4.28), exceeding WG's deltas on the same types (+3.82 and +3.58). NG2's "go straight to `run_sparql` / `ncbi_esearch`" strategy is *more efficient* on factoid/list questions where the answer is a discrete count or a list — discovery and schema reading would be overhead.

**Summary remains the weak spot** (+1.26, 14 % loss rate). Without MIE schema guidance, the model has trouble producing well-calibrated multi-database synthesis; it tends to deliver narrower-than-ideal coverage.

**Choice is the most degraded** vs WG: NG2 +2.70 vs WG +3.20. Choice questions often require comparing entity counts across databases — a workflow where schema-guided SPARQL has the advantage.

---

## 3. Scores by Evaluation Criteria

| Criterion | Baseline | TogoMCP | Δ |
|-----------|----------|---------|---|
| **Recall** | 1.96 | 3.75 | **+1.79** |
| **Precision** | 3.49 | 4.50 | **+1.01** |
| **Repetition** | 4.62 | 4.86 | +0.24 |
| **Readability** | 4.74 | 4.92 | +0.18 |

Recall improves by +1.79 — the dominant driver, as in every other condition. **Repetition and readability are slightly positive**, reversing the rev0 NG2 readability penalty (−0.14) and repetition penalty (−0.34). The deployed `togomcp` server's tool outputs are now cleaner; the model's compensatory brute-force querying (more `run_sparql`) does not measurably hurt presentation quality.

---

## 4. Latency and Cost

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean time | 7.6 s | **183 s** | **24×** |
| Median time | 7.5 s | 122 s | 16× |
| Max time | 12.4 s | 1083 s | — |
| Mean cost | $0.005 | $0.405 | 78× |
| Mean tool calls | — | 20.9 | — |

NG2 is the **most expensive condition by latency** (183 s vs WG's 137 s) and the **most tool-heavy** (20.9 calls vs WG's 12.4). The model compensates for missing instruction with sheer query volume. Cost-per-Δ-point is $0.124, modestly worse than WG's $0.108.

### Cost-effectiveness by type

| Type | Δ | Cost/q | pts / $ |
|------|:-:|:------:|:-------:|
| yes_no | +3.32 | $0.32 | **10.4** |
| factoid | +4.54 | $0.45 | 10.1 |
| list | +4.28 | $0.41 | 10.4 |
| choice | +2.70 | $0.42 | 6.4 |
| summary | +1.26 | $0.42 | **3.0** |

Summary remains the weakest investment in NG2 (3.0 pts/$, vs WG's 5.3).

---

## 5. Tool Calls and Score

### 5.1 Tool count vs. score

There is a moderate negative correlation (Pearson *r* = −0.25, Spearman *ρ* = −0.36, *p* = 0.011). The mean tool count is **20.9** (median 17, range 2–90) — substantially higher than WG.

| Tool calls | n | Mean score |
|:----------:|:-:|:----------:|
| 1–7 | 7 | **19.20** |
| 8–14 | 15 | 18.64 |
| 15–21 | 9 | 17.22 |
| 22–29 | 8 | 17.65 |
| 30–49 | 9 | 17.71 |
| 50+ | 2 | 16.10 |

The sweet spot is **1–7 tool calls** (mean 19.2). Beyond 15 calls, scores drop. The two extreme-tool-count outliers (50+ calls) average 16.1 — clearly the model floundering.

### 5.2 SPARQL queries vs. score

| `run_sparql` calls | n | Mean score |
|:------------------:|:-:|:----------:|
| 0 | 13 | 17.68 |
| 1 | 5 | 17.72 |
| 3 | 8 | 18.05 |
| 4 | 2 | 16.90 |
| 5 | 5 | **19.48** |
| 10–14 | 8 | 18.38 |
| 15+ | 7 | 18.11 |

**Total SPARQL calls in NG2: 343** (mean 6.8/q) — the highest of any condition. Strikingly, **Pearson correlation between SPARQL count and score is essentially zero** (r = 0.006). Without schema guidance, more queries don't hurt much because the model just runs more variants until something works. This is very different from WG (r = −0.49), where more SPARQL was a strong negative signal.

### 5.3 Spontaneous discovery and MIE usage

This is the central finding for NG2:

| Tool subset | Rows | Mean TogoMCP score |
|-------------|:----:|:------------------:|
| Used `find_databases` or `list_databases` | **5 / 50 (10 %)** | 19.24 |
| Did not use any discovery tool | 45 / 50 (90 %) | 17.90 |
| Used `get_MIE_file` | **9 / 50 (18 %)** | **19.58** |
| Did not use `get_MIE_file` | 41 / 50 (82 %) | 17.70 |

When the model spontaneously calls discovery or MIE tools, scores are clearly higher (19.6 vs 17.7 with/without MIE; +1.88 points). But **only 18 %** of NG2 questions saw a `get_MIE_file` call — versus 92–96 % in WG and NG1. The model rarely consults schema; when it does, it benefits substantially.

The rev0 paper's NG2 had `list_databases` at 36 % and `get_MIE_file` at 74 %. The new runs have collapsed both: combined discovery at 10 %, MIE at 18 %. The 2026-05-05 docstring fix (`cf58f3e`, making `find_databases` "REQUIRED first step") raised `find_databases` usage from 0 % to 10 % but did not move overall discovery back to rev0's 36 %.

---

## 6. Tool-Type Effectiveness

Tools used in ≥ 4 questions, ranked by mean question score:

| Tool | n questions | Mean score | Verdict |
|------|:-----------:|:----------:|---------|
| `get_MIE_file` | 9 | **19.58** | Excellent — when used, big boost |
| `find_databases` | 5 | **19.24** | Excellent — when used, big boost |
| `search_rhea_entity` | 5 | 18.44 | Strong |
| `ncbi_efetch` | 5 | 18.40 | Strong |
| `search_pdb_entity` | 6 | 18.40 | Strong |
| `search_chembl_target` | 7 | 18.34 | Strong |
| `run_sparql` | 38 | 18.21 | Universal — moderate score |
| `togoid_convertId` | 5 | 18.16 | Adequate |
| `ncbi_esummary` | 10 | 18.12 | Adequate |
| `search_uniprot_entity` | 24 | 17.46 | **Below-average — most-used non-MCP tool** |
| `ncbi_esearch` | 16 | 17.39 | Below-average (workhorse, noisy) |
| `search_reactome_entity` | 4 | 17.10 | Below-average |
| `pubmed:get_article_metadata` | 9 | 15.76 | **Weak — fallback when SPARQL fails** |
| `pubmed:search_articles` | 12 | 15.67 | **Weak — fallback when SPARQL fails** |

**Key observation:** the tools associated with the **highest** scores (`get_MIE_file`, `find_databases`) are the ones the model rarely uses spontaneously, while the most-used tool (`search_uniprot_entity`, 24 questions) is only mid-pack. The PubMed tools (used as a literature-search fallback when structured queries fail) drag scores down to 15–16.

---

## 7. Perfect Score Analysis

### 7.1 Universal-perfect questions (5/5)

**16 of 50 questions** achieved 20/20 on every Opus 4.7 run — equal to WG's count:

| Question | Type | Tools | Notes |
|----------|------|:-----:|-------|
| question_003 | factoid | 12 | Heart-attack ChEMBL targets |
| question_007 | yes_no | 22 | SPG11 cross-database verification |
| question_014 | factoid | 7 | GO hormone activity protein count |
| question_020 | yes_no | 12 | Symmachiella dynata genome |
| question_023 | list | 25 | MANE Select transcripts |
| question_024 | summary | 33 | Gluconeogenesis Rhea reactions |
| question_026 | yes_no | 9 | PubChem pteridine class |
| question_028 | list | 9 | B. subtilis biotin biosynthesis |
| question_033 | list | 14 | Notch ligands |
| question_035 | choice | 34 | PDB experimental technique |
| question_036 | yes_no | 9 | Metachromatic leukodystrophy |
| question_038 | choice | 4 | Mouse LGMD orthologs + PDB |
| question_039 | list | 16 | Brugada syndrome genes |
| question_043 | factoid | 7 | DHNA approved Rhea reactions |
| question_046 | yes_no | 16 | AXIN1 destruction-complex |
| question_050 | choice | 11 | Salmonella enterica AMR |

### 7.2 Characteristics

- **Type spread:** 5 yes/no, 4 list, 3 choice, 3 factoid, 1 summary — broader spread than WG's distribution. NG2 hits universal perfection on **list questions** more often than WG (4 vs 2), reflecting NG2's strength on direct retrieval.
- **Tool count** ranges widely: 4 to 34 (median 12). Universal perfection is achievable both via minimal queries (q038 with 4 tools) and via extensive multi-step exploration (q024 summary with 33 tools, q035 choice with 34).
- **The single universal-perfect summary** (q024 gluconeogenesis Rhea reactions) achieved 20/20 with a 33-call workflow — proof that NG2 *can* succeed at synthesis, but at significant tool-call cost.

---

## 8. When TogoMCP Was Worse Than Baseline

**3 of 50 questions** had Δ < 0 (vs WG's 2):

### 8.1 question_017 (yes_no, Δ = −3.20) — the consistent failure

> "Does Anabaena sp. DSM 101043 grow in nitrogen-free BG11- medium?"
>
> Ideal: Yes (BacDive-confirmed, MediaDive cross-validated).
>
> NG2 TogoMCP: hedged or said "no specific information" — the model failed to find the strain through its direct-search strategy.

This question requires querying **BacDive** specifically. Without `find_databases` or `get_MIE_file`, the model never discovers BacDive as a candidate database; it falls back to `search_uniprot_entity` and `ncbi_esearch` for an organism-level question, which produce no usable results. Tool count: 23, SPARQL calls: 0.

q017 is **the single most consistent failure across NG2 and No-MIE** (both deliver Δ ≈ −2.4 to −3.2). When the question requires a specialized database the model doesn't already know about by name, the no-discovery strategy fails categorically.

### 8.2 question_037 (summary, Δ = −1.00)

Notch1 protein synthesis with 34 tool calls and 15 SPARQL queries. The model produced a verbose response with cross-database integration but the protein count was off by ~10× (model inflated the count due to inclusion of paralogs the ideal answer excluded).

### 8.3 question_015 (summary, Δ = −0.80)

Phage T4 PDB structures — model inverted the X-ray vs cryo-EM technique ratio. 11 tools, 3 SPARQL.

### 8.4 Five questions tied with baseline (Δ = 0.00)

q030 (chr-1 cardiomyopathy genes), q008 (Chloroflexota in BacDive), q034 (AMR resistance summary), q019 (PubMed co-annotations), q009 (leukotriene enzymes). These are mostly **summary or list** questions where TogoMCP's data-grounded response and the baseline's hedged-but-correct general answer scored equally well.

---

## 9. Spontaneous Workflow Patterns

This is the section where NG2 differs most from the other conditions. We examine **what the model does without an explicit instruction**.

### 9.1 First tool called

In WG/no_mie, every question starts with `TogoMCP_Usage_Guide`. In NG2, the first MCP tool varies wildly:

| First tool | n questions |
|------------|:-----------:|
| `search_uniprot_entity` | **13** |
| `ncbi_esearch` | 9 |
| `run_sparql` (no discovery!) | 9 |
| `pubmed:search_articles` | 6 |
| `search_chembl_target` | 2 |
| `search_rhea_entity` | 2 |
| `ncbi_list_databases` | 2 |
| `find_databases` | 2 |
| Other | 5 |

**Only 4 questions** (8 %) start with a discovery-class tool (`find_databases` or `ncbi_list_databases`). **9 questions** (18 %) jump straight to `run_sparql` without any prior MCP tool call.

### 9.2 Workflow categories

We bin each question by which steps appear in `tools_used`:

| Pattern | Description | n | Mean score |
|---------|-------------|:-:|:----------:|
| Direct search only | Search tools or NCBI, no SPARQL | 11 | 17.50 |
| Direct SPARQL only | `run_sparql` without discovery or MIE | 26 | 18.04 |
| Discovery-then-SPARQL | `find_databases` or `list_databases` first | 5 | **19.24** |
| MIE-then-SPARQL | `get_MIE_file` without discovery | 4 | **19.20** |
| Mixed (search + SPARQL) | All approaches combined | 4 | 17.85 |

The pattern is clean: **whenever the model spontaneously uses discovery or MIE, scores jump to ~19.2**. Without discovery / MIE (the dominant pattern at 74 % of questions), scores hover around 17.5–18.0.

### 9.3 The discovery-rate collapse

| Run date | Discovery (any) | `get_MIE_file` |
|----------|:---------------:|:--------------:|
| Rev0 (2026-03-01) | 36 % | 74 % |
| New (2026-05-04, pre-fix) | 2 % | 14 % |
| New (2026-05-05, post-fix) | **10 %** | **18 %** |

The post-fix rate is much closer to zero than to the rev0 baseline. The 2026-05-05 docstring change (making `find_databases` "REQUIRED first step") restored 10 percentage points of discovery, but a residual ~26-point gap remains. **Since the Sonnet 4.5 model (`claude-sonnet-4-5-20250929`) and the question set are unchanged from rev0**, the explanation must lie in changes to what the model *sees* — i.e., changes to the served tool inventory and tool descriptions:

1. **Two-tool dilution.** In rev0, only `list_databases` existed; its docstring directly stated "Call list_databases() BEFORE calling get_MIE_file() or run_sparql()" — an unambiguous imperative. The post-rev0 split into `list_databases` + `find_databases` + `list_categories` accumulated softer cross-references (e.g., "alternative to list_databases()", "(Optional)") that we only partially reverted with the `cf58f3e` fix. Three discovery tools advertising themselves as alternatives to each other is structurally weaker steering than one canonical entry point with imperative wording.
2. **Other tool docstrings have evolved.** `run_sparql`, `search_*` tools, and so on have all had description revisions between rev0 and now. If those revisions made direct querying *easier-looking* — for example, by adding clearer parameter descriptions, alias coverage, or example workflows — the model's relative attraction to discovery has shrunk in proportion. We have not audited every tool's pre-rev0 description in this report; this is a tractable follow-up.
3. **The MIE-prompt and Usage Guide content** were both updated in the same window (Usage Guide migrated to v4 in `4882920`). Even though the Usage Guide is *excluded* in NG2, the discovery-tool docstrings now reference workflows defined in the broader documentation; subtle wording changes propagate.

Distinguishing among these requires re-running NG2 against successively earlier deployments of the `togomcp` server. For the manuscript, the practical takeaway is: **tool-docstring framing is a measurable lever, but not the only one**, and the spontaneous discovery rate in NG2 is best treated as a property of the deployed tool inventory at evaluation time.

---

## 10. Three-Condition Comparison

| Metric | Baseline | NG2 (this) | NG1 | WG |
|--------|----------|:----------:|:---:|:--:|
| TogoMCP score | — | 18.04 | 18.61 | **18.55** |
| Δ vs baseline | — | +3.22 | +3.46 | **+3.45** |
| Cohen's *d* | — | 1.19 | 1.56 | **1.82** |
| Win rate | — | 81.2 % | 92.8 % | **94.4 %** |
| Loss rate | — | 6.0 % | 4.8 % | **1.6 %** |
| Perfect-score rate | — | 40.0 % | **48.4 %** | 42.8 % |
| Mean tools / q | — | **20.9** | 12.1 | 12.4 |
| Spontaneous MIE | — | 18 % | 96 % | 94 % |
| Time / q | — | 183 s | **126 s** | 137 s |
| Cost / q | — | $0.405 | $0.370 | $0.380 |
| Cost per Δ point | — | $0.124 | **$0.106** | $0.108 |

Key observations:

1. **NG2 is now within striking distance of WG/NG1** on the headline score: Δ = +3.22 vs +3.45 and +3.46. This is a much smaller gap than rev0 (Δ = +1.48 vs +2.72).
2. **NG2 is substantially less efficient.** It uses 73 % more tool calls, takes 45 % longer, and costs 17 % more per Δ point than NG1.
3. **NG2 has a much higher loss rate** on individual evaluations (6.0 % vs WG's 1.6 %). When NG2 fails, it tends to fail harder (worst Δ = −3.2 vs WG's −0.2).
4. **The MIE instruction (NG1 vs NG2) is now worth ≈ 0.24 points** in mean score and ~13 percentage points in win rate. In rev0 the same instruction was worth +1.25 points. The instruction matters less now in absolute terms, but still produces a much cleaner workflow.

---

## 11. Inter-Run Evaluator Consistency

| Metric | TogoMCP |
|--------|:-------:|
| Mean std per question | 0.66 |
| Max std | 1.82 |
| Questions with std = 0 | 17 |
| Questions with std > 1 | 16 |
| Questions with std > 2 | 0 |

Inter-run agreement is tighter than rev0 (mean std 0.66 vs rev0's 0.68 — barely different) but slightly looser than WG (0.46). The 16 questions with std > 1 reflect NG2's more variable success — when the model improvises a workflow, the answer quality varies more across runs.

---

## 12. Is the Increased Cost Justified?

| Condition | Extra cost / q | Score Δ | Cost / Δ point | Verdict |
|-----------|:--------------:|:-------:|:--------------:|:-------:|
| **NG2** | $0.400 | +3.22 | $0.124 | ✅ Justified |
| NG1 | $0.365 | +3.46 | $0.106 | ✅ Strongly justified |
| WG | $0.375 | +3.45 | $0.108 | ✅ Strongly justified |

NG2 is **cost-justified**, unlike the rev0 NG2 which the previous analysis flagged as "partially justified" at $0.25/point. The new $0.124/point is comparable to WG/NG1.

**Where NG2 is most attractive:** `factoid` and `list` questions, where the unguided direct-search strategy delivers Δ = +4.5 and +4.3 — *higher* than WG's deltas on the same types. If a deployment can tolerate occasional summary-question regressions, NG2's lower-instruction approach is competitive.

**Where NG1/WG dominate:** `summary` and `choice` questions, where structured workflow yields Δ = +3.0 / +3.5 vs NG2's +1.3 / +2.7. For synthesis-heavy workloads, the MIE instruction remains valuable.

---

## 13. Key Findings and Recommendations

1. **NG2 has caught up dramatically with WG/NG1** since rev0 (Δ went from +1.48 to +3.22). Tool augmentation now produces large gains even without explicit orchestration. This is the most striking change between rev0 and the new runs.

2. **The strategy by which NG2 succeeds has changed.** Rev0 NG2 spontaneously read MIE on 74 % of questions and used `list_databases` on 36 %. New NG2 uses MIE on 18 % and combined discovery on 10 %. The model has **shifted from "explore the catalog, then query" to "query directly with familiar tools and brute-force iterate."** Both strategies now produce strong scores.

3. **Spontaneous discovery did not recover with the docstring fix.** The 2026-05-05 `cf58f3e` change ("`find_databases` is REQUIRED first step") brought the rate from 0 % to 10 %, not back to rev0's 36 %. Tool docstrings alone — even imperative ones — are weak steering for this model. Explicit system-prompt instructions (NG1) achieve 92 % discovery; tool docstrings (NG2) achieve 10 %. The lesson for the manuscript: **rely on the system prompt for workflow control, not on tool docstrings.**

4. **Summary and choice questions still benefit from explicit instruction.** NG2 summary Δ is +1.26 (vs NG1's +3.08); NG2 choice Δ is +2.70 (vs WG's +3.20). For these synthesis-heavy types, structured orchestration matters.

5. **Factoid and list questions are NG2's strength.** Δ = +4.5 and +4.3 — actually exceeding WG's deltas. The unguided direct-query strategy is *more* efficient here than the structured workflow.

6. **q017 (Anabaena) is the canonical NG2 failure.** Without `find_databases`, the model can't discover BacDive as the relevant database for this question and falls back to general-purpose searches that produce nothing. This pattern — failure when the question requires a specialized database not already known to the model — is the dominant NG2 failure mode (occurring also in No-MIE).

7. **Unjustified high tool counts are diagnostic.** Mean tool count is 20.9 (median 17). When tool count exceeds 15, mean score drops to ~17. Two questions used 50+ tools and averaged 16.1. A tool-call cap (e.g., 20) might bound the worst NG2 latency without sacrificing mean accuracy.

8. **The cost is justified, but NG1 / WG are strictly more efficient.** $0.124 per Δ point is acceptable; $0.106 (NG1) at the same quality level is better. If a deployment can include a single MIE instruction in the system prompt, doing so is the easiest win available.

---

*Analysis: 5 independent Opus 4.7 evaluation runs × 50 questions = 250 evaluations. Source CSV: `ng2-2026-05-04.csv` (post-fix rerun, 2026-05-05 endpoint); per-run scoring CSVs: `ng2-2026-05-04-Opus4.7-v{1..5}.csv`. Reference comparison: 2026-02 paper analysis at [`rev0/togomcp_no_guide_analysis.md`](rev0/togomcp_no_guide_analysis.md).*
