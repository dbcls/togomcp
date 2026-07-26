# TogoMCP Four-Condition Comparison Analysis (2026-05-04 rerun)

**Date:** 2026-05-05
**Benchmark answers collected:** 2026-05-04 (Sonnet 4.5, `claude-sonnet-4-5-20250929`)
**Evaluator LLM:** Opus 4.7 (`claude-opus-4-7`), 5 independent evaluation runs per condition
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)

---

## Experimental Conditions

| Label | `TogoMCP_Usage_Guide` | System-prompt MIE/discovery instruction | `get_MIE_file` |
|-------|:--------------------:|:---------------------------------------:|:--------------:|
| **With Guide (WG)** | ✅ available, called first | implicit (Usage Guide owns the workflow) | ✅ |
| **NG1** (no guide + MIE instr) | ❌ disallowed | ✅ explicit ("call `find_databases()` then `get_MIE_file()` before SPARQL") | ✅ |
| **NG2** (no instruction) | ❌ disallowed | ❌ no instruction at all | ✅ available |
| **No MIE** | ✅ available | tells the model to use the catalog but **not** to read MIE | ❌ disallowed |

The pivotal contrast remains **NG1 vs NG2**: both lack the Usage Guide tool, but NG1's system prompt explicitly orchestrates the discovery → schema → query workflow, whereas NG2's system prompt is silent and leaves the choice entirely to the model.

> **Note:** Each condition is an independent run, so per-question score differences fold both treatment effects and run-to-run stochasticity. Aggregate statistics across 250 evaluations per condition are robust; individual-question comparisons should be read with this caveat in mind.

---

## 1. Executive Summary

| Metric | With Guide | NG1 (MIE instr) | NG2 (no instr) | No MIE |
|--------|:----------:|:----------------:|:--------------:|:------:|
| TogoMCP score | **18.55** | **18.61** | 18.04 | 18.24 |
| Baseline score | 15.10 | 15.15 | 14.82 | 15.28 |
| Δ vs baseline | **+3.45** | **+3.46** | +3.22 | +2.96 |
| Cohen's *d* | **1.82** | 1.56 | 1.19 | 1.38 |
| Wilcoxon *p* | < 10⁻⁹ | < 10⁻⁹ | < 10⁻⁸ | < 10⁻⁹ |
| Win rate | **94.4 %** | 92.8 % | 81.2 % | 83.2 % |
| Tie rate | 4.0 % | 2.4 % | 12.8 % | 12.8 % |
| Loss rate | 1.6 % | 4.8 % | 6.0 % | 4.0 % |
| Perfect scores (=20) | 42.8 % | **48.4 %** | 40.0 % | 33.6 % |
| Mean tools / q | 12.4 | 12.1 | **20.9** | 16.9 |
| Cost / question | $0.380 | $0.370 | $0.405 | $0.388 |
| Time / question | 137 s | **126 s** | 183 s | 206 s |
| Cost per Δ point | $0.108 | **$0.106** | $0.124 | $0.129 |

**The central finding: WG ≈ NG1 > NG2 ≈ No-MIE, but all four conditions deliver substantial, statistically significant improvement.** Every condition produces Δ > +2.9 with *p* < 10⁻⁸, Cohen's *d* > 1.1, and a win rate above 81 %. This is a notable departure from the 2026-02 paper benchmark, where NG2 showed Δ = +1.48 and No-MIE Δ = +0.30 — substantially lower than WG. The full inter-condition stratification has compressed by roughly half.

The MIE instruction (NG1) still nearly matches the Usage Guide (WG): Δ +3.46 vs +3.45, win rate 92.8 % vs 94.4 %, and identical cost-per-point ($0.106 vs $0.108). The "MIE instruction = Usage Guide" finding survives.

What has changed is that **the gap from NG1 down to NG2 / No-MIE is much smaller now** (~0.3–0.5 points instead of ~1.2 points). The Sonnet 4.5 model and the question set are unchanged from the rev0 run; the explanations therefore lie on the **server / evaluator side**:

- **MIE schemas have grown substantially richer** since rev0 (v2.0 → v2.1 spec, anti-patterns, shape_expressions discipline, four new databases). When the model does read MIE — and even via indirect benefit when the server's tool output formatting reflects the schema — answers are more grounded.
- **Server-side tool ergonomics improved** (e.g. `4e594cb` made tools return graceful errors instead of raising; tool docstrings have been refined; output formatting is cleaner). This particularly explains the rev0 readability/repetition penalties not reproducing.
- **Evaluator changed from Opus 4.6 → Opus 4.7.** A different evaluator can produce systematically different rubric scores even on identical answers; this is a confound that should be flagged in the manuscript.

---

## 2. Scores by Question Type

| Type | WG Δ | NG1 Δ | NG2 Δ | No MIE Δ |
|------|:----:|:-----:|:-----:|:--------:|
| **factoid** | +3.82 | +3.74 | **+4.54** | **+4.34** |
| **list** | +3.58 | +3.40 | **+4.28** | +3.98 |
| **yes_no** | +4.22 | **+4.64** | +3.32 | +3.00 |
| **choice** | +3.20 | +2.42 | +2.70 | +1.72 |
| **summary** | +2.44 | **+3.08** | +1.26 | +1.74 |

A new pattern emerges that did **not** appear in the 2026-02 results:

- On **factoid** and **list** questions, NG2 / No-MIE *exceed* WG / NG1 — the unguided model leans hard on direct search tools (`run_sparql`, `search_uniprot_entity`, `ncbi_esearch`) and gets clean numeric answers without the discovery overhead.
- On **choice** and **summary** questions, the order reverses: WG / NG1 dominate, because schema-guided SPARQL produces cleaner cross-database comparisons and synthesis.
- **yes_no** is the only type where the rev0 ordering (WG > NG1 > NG2 > No-MIE) holds.

The most striking change vs rev0: **NG2's summary Δ went from −0.08 (rev0) to +1.26 (now)**. Summary questions are no longer actively harmful in the unguided condition.

### Win/Loss rates by type

| Type | WG win/loss | NG1 win/loss | NG2 win/loss | No-MIE win/loss |
|------|:-----------:|:------------:|:------------:|:---------------:|
| factoid | 96 / 0 % | 98 / 0 % | **100 / 0 %** | 98 / 0 % |
| yes_no | **100 / 0 %** | 100 / 0 % | 86 / 10 % | 80 / 10 % |
| choice | 96 / 0 % | 78 / 16 % | 82 / 6 % | 70 / 4 % |
| list | 90 / 4 % | 92 / 8 % | 82 / 0 % | 96 / 0 % |
| summary | 90 / 4 % | **96 / 0 %** | 56 / 14 % | 72 / 6 % |

NG2 still has the highest summary loss rate (14 %), but the absolute degradation is much milder than the 38 % loss rate seen in rev0.

### Cohen's *d* by type

| Type | WG *d* | NG1 *d* | NG2 *d* | No-MIE *d* |
|------|:------:|:-------:|:-------:|:----------:|
| yes_no | **2.55** | 2.15 | 1.00 | 1.06 |
| factoid | 2.35 | 2.07 | **2.40** | **2.95** |
| list | 1.84 | 1.48 | 1.75 | **2.63** |
| summary | 1.53 | **2.36** | 0.70 | 1.25 |
| choice | **1.32** | 0.82 | 0.94 | 0.89 |

Effect sizes are large (>1) almost everywhere. The two cells where the effect drops below moderate are NG2/summary (*d* = 0.70) and NG1/choice (*d* = 0.82).

---

## 3. Scores by Evaluation Criteria

| Criterion | WG Δ | NG1 Δ | NG2 Δ | No-MIE Δ |
|-----------|:-----:|:-----:|:-----:|:--------:|
| **Recall** | **+2.23** | +1.97 | +1.79 | +1.74 |
| **Precision** | +1.04 | +1.01 | +1.01 | +0.87 |
| **Repetition** | +0.11 | +0.21 | +0.24 | +0.18 |
| **Readability** | +0.07 | +0.26 | +0.18 | +0.16 |

Recall remains the dominant driver, as in rev0. Notably, **the readability and repetition penalties seen in rev0 (typically negative values) are now slightly positive** for every condition. TogoMCP outputs are not just more factual — they are now also marginally cleaner prose than the baseline. This is the largest qualitative shift between the two run dates and likely reflects either the deployed `togomcp` server's improved tool ergonomics or the model's improved tool-output integration.

---

## 4. Latency and Cost

| Metric | WG | NG1 | NG2 | No-MIE |
|--------|:--:|:---:|:---:|:------:|
| Time / q | 137 s | **126 s** | 183 s | 206 s |
| Cost / q | $0.380 | $0.370 | $0.405 | $0.388 |
| Mean tools / q | 12.4 | 12.1 | **20.9** | 16.9 |
| Cost per Δ point | $0.108 | **$0.106** | $0.124 | $0.129 |

NG1 has the lowest cost-per-Δ-point ($0.106), edging out WG ($0.108). Both spend roughly half as much per point as the unguided conditions, reflecting more efficient tool use (fewer total calls, shorter latency). NG2's mean tool count (20.9) is the highest by a wide margin — without instruction, the model substitutes raw query volume for schema knowledge.

### Cost-effectiveness by type (NG1)

| Type | NG1 Δ | Extra cost | pts / $ |
|------|:-----:|:----------:|:-------:|
| yes_no | +4.64 | $0.30 | **15.3** |
| factoid | +3.74 | $0.43 | 8.7 |
| list | +3.40 | $0.39 | 8.7 |
| summary | +3.08 | $0.42 | 7.4 |
| choice | +2.42 | $0.32 | 7.5 |

Yes/no questions remain the most cost-effective (15.3 pts/$), as in rev0.

---

## 5. Tool Usage

### 5.1 Workflow compliance

| Tool | WG (rows w/ tool) | NG1 | NG2 | No-MIE |
|------|:-----------------:|:---:|:---:|:------:|
| `TogoMCP_Usage_Guide` | **100 %** (50/50) | 0 % (excluded) | 0 % (excluded) | **100 %** (50/50) |
| `find_databases` | 96 % (48/50) | 92 % (46/50) | 10 % (5/50) | **100 %** (50/50) |
| `list_databases` | 0 % | 0 % | 4 % (2/50) | 8 % (4/50) |
| `get_MIE_file` | 94 % (47/50) | 96 % (48/50) | 18 % (9/50) | 0 % (excluded) |
| `run_sparql` | 94 % (47/50) | 96 % (48/50) | 76 % (38/50) | 74 % (37/50) |

### 5.2 Total tool invocations

| Tool | WG | NG1 | NG2 | No-MIE |
|------|:--:|:---:|:---:|:------:|
| `find_databases` | 58 | 50 | 5 | 53 |
| `get_MIE_file` | 88 | 98 | 11 | — |
| `run_sparql` | **241** | **317** | **343** | 272 |
| `TogoMCP_Usage_Guide` | 50 | — | — | 50 |

Two patterns to highlight:

1. **`find_databases` has fully replaced `list_databases` as the canonical discovery tool** in every condition where it is used (WG 58 calls vs `list_databases` 0; NG1 50 vs 0; No-MIE 53 vs 4). The post-`cf58f3e` docstring restoration ("REQUIRED first step", "Always call BEFORE …") works as intended in the *guided* and *MIE-instructed* conditions.
2. **In NG2, neither discovery tool is used.** Only 5 / 50 questions touch `find_databases` and 2 / 50 touch `list_databases` — total combined discovery rate of 14 %. Without an explicit system-prompt instruction, the model just goes straight to `run_sparql` (76 % of rows, 343 calls — the highest in the experiment). This was 36 % in the rev0 paper data and is the most striking behavioural regression in the new runs. (See [togomcp_no_guide_analysis.md](togomcp_no_guide_analysis.md) for a deep dive.)

### 5.3 SPARQL efficiency

| Metric | WG | NG1 | NG2 | No-MIE |
|--------|:--:|:---:|:---:|:------:|
| Total SPARQL calls | 241 | 317 | **343** | 272 |
| Mean SPARQL / q | 4.8 | 6.3 | **6.9** | 5.4 |

NG2 fires the most SPARQL queries despite producing the lowest TogoMCP score among the four — consistent with the rev0 pattern that high SPARQL volume correlates with model struggle, not thoroughness.

---

## 6. Perfect Score Analysis

### 6.1 Perfect-score rate per condition

| Condition | Evaluations at 20/20 | Rate |
|-----------|:--------------------:|:----:|
| **NG1** | **121 / 250** | **48.4 %** |
| WG | 107 / 250 | 42.8 % |
| NG2 | 100 / 250 | 40.0 % |
| No-MIE | 84 / 250 | 33.6 % |

NG1 reaches 20/20 most often — slightly ahead of WG (it edges out on summary questions especially). The baseline reaches 20/20 only twice in NG1, four times in No-MIE, and never in WG or NG2.

### 6.2 Universal-perfect questions (5/5 across all evaluators)

The new runs are far more perfect-score-rich than rev0. Counting questions that hit **20/20 across all 5 Opus 4.7 evaluators** (intersection):

| Condition | Universal-perfect questions (5/5) | Type breakdown |
|-----------|:--:|----------------|
| WG | 16 | yes_no 6, choice 5, list 2, factoid 2, summary 1 |
| NG1 | **17** | yes_no 8, choice 5, list 2, factoid 2 (no summary) |
| NG2 | 16 | yes_no 5, list 4, factoid 3, choice 3, summary 1 |
| No-MIE | 13 | yes_no 5, choice 3, factoid 2, list 2, summary 1 |

NG1 has the highest count overall; WG / NG1 / NG2 all reach the double digits. The pool of guaranteed-easy questions is much larger than rev0's (which had 1–6 universally perfect per condition).

---

## 7. When TogoMCP Was Worse Than Baseline

Per-row losses (across 250 evaluations) are now rare:

| Condition | Loss rate | Worst single Δ (per question, mean over 5 runs) |
|-----------|:---------:|:-----------------------------:|
| WG | 1.6 % | −0.2 (q021 proteasome summary) — barely below baseline |
| NG1 | 4.8 % | −1.2 (q013 Joubert top-5 genes); −1.0 (q030 chr-1 cardiomyopathy) |
| NG2 | 6.0 % | −3.2 (q017 Anabaena DSM 101043 BG11- query) |
| No-MIE | 4.0 % | −2.4 (q017 Anabaena DSM 101043 BG11- query) |

The dominant failure pattern is unchanged from rev0: **q017 (Anabaena DSM 101043 strain lookup)** trips the database-grounded path in every condition where the model attempts SPARQL. The baseline's general-knowledge guess outperforms TogoMCP's null-result query on this question. This is now the consistent worst-case across conditions.

The catastrophic rev0 failures (q030 / q035 data dumps with Δ = −5.4 to −5.8; q007 self-contradiction with Δ = −4.8) **do not reproduce** in the new runs. Either the deployed `togomcp` server's tool-output formatting has improved (less raw-data leakage into responses), or the Opus 4.7 evaluator scores these data-dump answers more kindly.

---

## 8. Head-to-Head: NG1 vs NG2

The MIE instruction's effect, isolated:

| Metric | NG1 − NG2 |
|--------|:---------:|
| Score Δ | +0.24 points |
| Cohen's *d* gap | +0.37 |
| Win rate gap | +11.6 pp |
| Loss rate gap | −1.2 pp |
| Perfect-score rate gap | +8.4 pp |
| Worst single Δ | −1.2 vs −3.2 (NG2's q017 Anabaena failure is much sharper) |
| Summary Δ | +3.08 vs +1.26 (gap +1.82) |
| Mean tool calls | 12.1 vs 20.9 (NG1 ~42 % fewer) |

The MIE instruction is now worth **+0.24 mean points and +1.82 summary points** — substantial but smaller than its rev0 effect (+1.25 mean points). The model has compressed its no-instruction-deficit on simple factoid/list/yes-no, but synthesis-heavy summary questions still benefit clearly from explicit MIE guidance.

The instruction also **halves the tool-call overhead** in NG1 vs NG2 (12.1 vs 20.9 mean tools / question). NG2's compensatory pattern is to fire many more `run_sparql` queries (343 vs 317 total) without prior schema reading, producing roughly the same answers at higher cost and latency.

---

## 9. The Component Value Hierarchy

```
WG        Usage Guide + MIE-via-guide + MIE tool   →  Δ = +3.45  ($0.108/pt)   reference
            ↓ remove the guide tool, keep the MIE step in the system prompt
NG1       MIE-instruction system prompt + MIE tool →  Δ = +3.46  ($0.106/pt)   ≈ tied
            ↓ remove the system-prompt MIE instruction
NG2       MIE tool available, never instructed     →  Δ = +3.22  ($0.124/pt)   −0.24 vs NG1
            ↓ remove the MIE tool (and re-add Usage Guide that no longer mentions MIE)
No-MIE    Usage Guide, no MIE tool                 →  Δ = +2.96  ($0.129/pt)   −0.26 vs NG2
```

Two main observations:

- **The Usage Guide adds essentially zero quality beyond the equivalent system-prompt MIE instruction.** WG vs NG1 is a tie within run-to-run noise.
- **Each successive removal of MIE-related guidance costs ~0.25 points.** The drop from NG1 → NG2 (remove instruction) is +0.24, and NG2 → No-MIE (also remove the tool) is +0.26. These are real but small effects vs the rev0 results, where each step was ~1.2 points.

---

## 10. Cost-Benefit Summary

| Condition | Extra cost / q | Score Δ | Cost / Δ point | Verdict |
|-----------|:-------------:|:-------:|:--------------:|:--------|
| **WG** | $0.375 | +3.45 | **$0.108** | ✅ Strongly justified |
| **NG1** | $0.365 | +3.46 | **$0.106** | ✅ Strongly justified |
| **NG2** | $0.400 | +3.22 | $0.124 | ✅ Justified |
| **No-MIE** | $0.382 | +2.96 | $0.129 | ✅ Justified |

In contrast to rev0, **no condition is cost-unjustified** in the new runs. Even No-MIE's $0.129 / point is solidly positive (rev0 had it at $1.61 / point — an order of magnitude worse).

---

## 11. Recommendations

1. **NG1's MIE instruction in the system prompt is still the lowest-cost intervention with the largest payoff.** It matches WG to within run-to-run noise at slightly lower cost and latency. If a deployment can only afford one nudge, it is "before any SPARQL, call `find_databases()` then `get_MIE_file()`."

2. **The Usage Guide is functionally redundant with the MIE instruction.** Both produce the same headline numbers. Choose based on whether you want a structured, tool-encapsulated guide (Usage Guide) or a system-prompt directive (MIE instruction).

3. **Summary questions still favour guided conditions.** WG/NG1 keep summary Δ above +2.4; NG2/No-MIE drop to +1.3–1.7 with much higher loss rates. For synthesis-heavy workloads, the MIE step matters most.

4. **The "MIE-essential" stratification has weakened.** NG2 (no instruction) and No-MIE both deliver Δ ≈ +3.0 — strong improvements that did not materialize in rev0. The manuscript should acknowledge this: tool-augmentation now produces sizeable gains across configurations, with the Usage Guide / MIE instruction acting as a **modest amplifier** rather than the dominant lever it was in rev0.

5. **Spontaneous discovery in NG2 has collapsed.** `find_databases` rate is 10 % (5/50 rows); `list_databases` is 4 % (2/50). Combined "any discovery tool" rate is 14 %, vs the rev0 ng2's 36 % `list_databases` rate. The Sonnet 4.5 model and question set are unchanged; the change comes from the **served tool inventory** (rev0 had only `list_databases`; the catalog now serves three discovery tools that previously cross-referenced each other as "alternatives") and **docstring framing** (rev0's `list_databases` was imperative; intervening edits softened the language; only partially recovered by the 2026-05-05 fix). The manuscript should treat NG2's discovery rate as a property of the deployed tool catalog at evaluation time, not as a steady property of the model.

---

*Analysis: 4 conditions × 5 evaluation runs × 50 questions = 1,000 total Opus 4.7 evaluations of 200 baseline + 200 TogoMCP answer pairs. Source CSVs: `{condition}-2026-05-04.csv`; per-run scoring CSVs: `{condition}-2026-05-04-Opus4.7-v{1..5}.csv`. Reference comparison data for the 2026-02 paper run is in [`rev0/togomcp_four_condition_comparison.md`](rev0/togomcp_four_condition_comparison.md).*
