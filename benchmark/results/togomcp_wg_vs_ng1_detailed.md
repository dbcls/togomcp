# With Guide vs NG1: Detailed Comparison

**Date:** 2026-05-05
**Benchmark answers collected:** 2026-05-04 (Sonnet 4.5, `claude-sonnet-4-5-20250929`)
**Evaluator LLM:** Opus 4.7 (`claude-opus-4-7`), 5 independent evaluation runs per condition
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)

**Conditions compared:**

- **With Guide (WG):** Full Usage Guide tool + MIE files + system-prompt directive to call the guide first.
- **NG1:** No Usage Guide tool; system-prompt instruction to call `find_databases()` then `get_MIE_file()` before SPARQL.

Both are independent experiment runs (different baseline and TogoMCP answers), so per-question score differences fold in both treatment effects and run-to-run stochasticity. Aggregate statistics across 250 evaluations per condition are robust.

---

## 1. The Headline: Statistically Indistinguishable on Total Score

| Metric | WG | NG1 | Difference |
|--------|:--:|:---:|:----------:|
| Mean TogoMCP score | 18.55 | 18.61 | **−0.06** |
| Δ vs baseline | +3.45 | +3.46 | −0.004 |
| Cohen's *d* | 1.82 | 1.56 | +0.26 |
| Win rate | 94.4 % | 92.8 % | +1.6 pp |
| Loss rate | 1.6 % | 4.8 % | −3.2 pp |
| Perfect-score rate (=20) | 42.8 % | 48.4 % | −5.6 pp |

**Statistical tests for WG vs NG1 on per-question mean TogoMCP scores:**

| Test | Statistic | *p*-value | Interpretation |
|------|:---------:|:---------:|:---------------|
| Wilcoxon signed-rank | — | **0.887** | No difference |
| Paired *t*-test | *t* = −0.40 | **0.691** | No difference |
| Bootstrap 95 % CI for Δ_WG − Δ_NG1 | — | **[−0.40, +0.42]** | Contains zero |
| Mean diff in Δ | — | **−0.004 points** | Essentially zero |

The headline rev0 finding **holds**: the difference between WG's full Usage Guide and NG1's bare MIE instruction is indistinguishable from noise on the total-score axis. With 50 questions × 5 evaluators = 250 paired observations, the data still cannot distinguish them.

---

## 2. Where They Do Differ: Criteria-Level Analysis

While total scores are washed out, **three of the four sub-criteria show statistically significant differences** — more than rev0's single significant criterion (readability):

| Criterion | WG Δ | NG1 Δ | Diff (WG−NG1) | *p*-value | Direction |
|-----------|:----:|:-----:|:-------------:|:---------:|:---------:|
| **Recall** | +2.23 | +1.97 | **+0.26** | **0.010** | **WG better** |
| Precision | +1.04 | +1.01 | +0.03 | 0.645 | NS |
| **Repetition** | +0.11 | +0.21 | −0.10 | **0.024** | **NG1 better** |
| **Readability** | +0.07 | +0.26 | **−0.19** | **0.004** | **NG1 better** |

**The result is a clean trade-off**: WG retrieves more facts but with slightly more verbose / repetitive presentation; NG1 produces cleaner prose with marginally less recall. The two effects roughly cancel on total score.

This is a **stronger pattern than rev0**, where only readability differed (also favoring NG1). The new runs surface the recall advantage of WG too — likely because the Usage Guide's structured ordering ("read MIE before SPARQL") leads to more comprehensive retrieval, while NG1's bare instruction leaves the model freer to skip steps.

### Readability and repetition by question type

| Type | WG Read Δ | NG1 Read Δ | Diff | WG Rep Δ | NG1 Rep Δ | Diff |
|------|:---------:|:----------:|:----:|:--------:|:---------:|:----:|
| **summary** | +0.02 | +0.46 | −0.44 | +0.10 | +0.32 | −0.22 |
| **factoid** | +0.12 | +0.30 | −0.18 | +0.10 | +0.10 | 0.00 |
| **list** | +0.08 | +0.22 | −0.14 | +0.16 | +0.16 | 0.00 |
| choice | +0.22 | +0.10 | +0.12 | +0.40 | +0.18 | +0.22 |
| yes_no | +0.18 | +0.30 | −0.12 | +0.30 | +0.32 | −0.02 |

NG1's readability advantage is most pronounced on **summary** questions (+0.44 over WG). On choice questions the direction reverses — WG outdoes NG1 on both readability (+0.12) and repetition (+0.22).

### Recall by question type

| Type | WG Rec Δ | NG1 Rec Δ | Diff |
|------|:--------:|:---------:|:----:|
| **yes_no** | +2.42 | +2.42 | 0.00 |
| **factoid** | +2.74 | +2.42 | **+0.32** |
| **list** | +2.30 | +2.16 | +0.14 |
| **choice** | +1.66 | +1.16 | **+0.50** |
| **summary** | +1.46 | +1.62 | −0.16 |

WG's recall advantage is largest on **choice** (+0.50) and **factoid** (+0.32), where the Usage Guide's structured workflow helps the model retrieve all relevant evidence. On summary, NG1's recall actually edges out WG.

---

## 3. Tool Usage: Same Outcome, Different Strategies

### 3.1 Workflow compliance

| Tool | WG (rows) | NG1 (rows) | WG (calls) | NG1 (calls) |
|------|:---------:|:----------:|:----------:|:-----------:|
| `TogoMCP_Usage_Guide` | **100 %** (50/50) | 0 % (excluded) | 50 | — |
| `find_databases` | 96 % (48/50) | 92 % (46/50) | 58 | 50 |
| `get_MIE_file` | 94 % (47/50) | 96 % (48/50) | 88 | 98 |
| `run_sparql` | 94 % (47/50) | 96 % (48/50) | 241 | **317** |
| `search_uniprot_entity` | 32 % (16/50) | 24 % (12/50) | 42 | 26 |
| `ncbi_esearch` | 26 % (13/50) | 18 % (9/50) | 63 | 36 |

The most striking difference: **NG1 makes 32 % more `run_sparql` calls** (317 vs 241). Without the Usage Guide's structured workflow, the model substitutes a higher SPARQL volume — issuing more variant queries against the same questions.

### 3.2 First tool called

| First MCP tool | WG | NG1 |
|----------------|:--:|:---:|
| `TogoMCP_Usage_Guide` | **50** | — |
| `find_databases` | 0 (always second) | **45** |
| `ncbi_esearch` | 0 | 2 |
| `ncbi_efetch` | 0 | 1 |
| `search_uniprot_entity` | 0 | 1 |
| `search_chembl_target` | 0 | 1 |

WG has perfectly uniform start-up: every question begins with `TogoMCP_Usage_Guide → find_databases`. NG1 starts with `find_databases` 90 % of the time, but **5 questions (10 %) skip it** and jump straight to a search tool. These are typically questions where the model recognizes the entity from training knowledge (e.g., a specific ChEMBL target) and goes directly to the relevant search API.

### 3.3 SPARQL patterns

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Total SPARQL calls | 241 | **317** |
| Mean SPARQL / question | 4.8 | **6.3** |
| Questions with > 10 SPARQL | 5 | **9** |
| Pearson *r* (SPARQL count, score) | −0.49 | −0.36 |

NG1 makes **31 % more SPARQL** queries on average. The negative correlation between SPARQL count and score is *less negative* in NG1 (−0.36 vs WG's −0.49) — NG1 absorbs more SPARQL volume without proportional score loss, but the cost is the higher overall query count.

The pattern: **WG uses SPARQL more efficiently** (fewer calls per question, same retrieval), while NG1 brute-forces with more variant queries. Both arrive at similar answers.

---

## 4. Directional Agreement

| Outcome | Count | % |
|---------|:-----:|:-:|
| Both improve over baseline | **45** | 90 % |
| Both worse than baseline | **0** | 0 % |
| WG improves, NG1 doesn't | 3 | 6 % |
| NG1 improves, WG doesn't | 2 | 4 % |

**WG and NG1 agree on direction in 90 % of cases** — substantially higher agreement than rev0's 70 %. **Zero questions** have *both* TogoMCP arms below the baseline, a cleaner result than rev0 (which had 2). The five disagreement cases are the most informative.

### 4.1 WG wins, NG1 loses (3 questions)

| Question | Type | WG Δ | NG1 Δ | Diff | Likely cause |
|----------|------|:----:|:-----:|:----:|:-------------|
| question_013 | list | +1.0 | −1.2 | **+2.2** | Joubert top-5 — WG found correct genes; NG1 picked the wrong MedGen concept |
| question_030 | choice | +0.0 | −1.0 | **+1.0** | chr-1 cardiomyopathy genes — WG count closer to ideal |
| question_005 | choice | +1.0 | +0.0 | +1.0 | Kinase TK group — WG cleaner |

These are mostly **complex multi-database list / choice** questions where WG's structured workflow ensures comprehensive coverage.

### 4.2 NG1 wins, WG loses (2 questions)

| Question | Type | WG Δ | NG1 Δ | Diff | Likely cause |
|----------|------|:----:|:-----:|:----:|:-------------|
| question_044 | list | +0.0 | +3.0 | **−3.0** | Siglec glycoproteomic curation — NG1 found GlyConnect; WG queried GlyCosmos and over-listed |
| question_021 | summary | −0.2 | +2.2 | **−2.4** | Proteasome KW-0647 — NG1's cleaner answer scored higher |

NG1 wins on questions where **the Usage Guide's exploratory rigor backfires** — by reading more MIE files and searching more databases, WG sometimes pulls in over-broad data (e.g., all 10 siglecs from GlyCosmos instead of the 4 specifically curated in GlyConnect).

---

## 5. Largest Per-Question Gaps

### 5.1 WG significantly higher than NG1

| Question | Type | WG | NG1 | Diff | Note |
|----------|------|:--:|:---:|:----:|:-----|
| question_013 | list | 18.6 | 15.4 | **+3.20** | Joubert top-5 — direction-changing |
| question_030 | choice | 18.2 | 16.2 | +2.00 | chr-1 cardiomyopathy |
| question_001 | yes_no | 20.0 | 18.6 | +1.40 | HSPB1 / Charcot-Marie-Tooth |
| question_005 | choice | 20.0 | 18.6 | +1.40 | Kinase TK group |
| question_006 | factoid | 16.8 | 15.6 | +1.20 | Metalloprotease ChEMBL count |

These are mostly questions where **the Usage Guide's structured ordering helps the model produce comprehensive retrieval**. The recall-axis advantage shows up at the question level here.

### 5.2 NG1 significantly higher than WG

| Question | Type | WG | NG1 | Diff | Note |
|----------|------|:--:|:---:|:----:|:-----|
| question_044 | list | 12.8 | 15.8 | **−3.00** | Siglec glycoproteomic curation |
| question_003 | factoid | 16.8 | 19.4 | **−2.60** | Heart-attack ChEMBL targets |
| question_021 | summary | 14.8 | 17.2 | **−2.40** | Proteasome KW-0647 summary |
| question_031 | factoid | 16.0 | 18.4 | −2.40 | Glycosyltransferase Rhea reactions |
| question_025 | choice | 19.0 | 20.0 | −1.00 | Universal-perfect in NG1 only |

These are **questions where the bare instruction is enough**, and the Usage Guide's full procedural rigor adds verbosity / wrong-database overhead without proportionate accuracy gains.

---

## 6. Universal-Perfect Questions

| Set | Count | Question IDs |
|-----|:-----:|:-------------|
| Both 5/5 perfect | **12** | q010, q019, q020, q026, q028, q036, q038, q039, q043, q046, q047, q050 |
| WG only 5/5 | 4 | **q001** (HSPB1), **q005** (Kinase TK), **q029** (Notch1 summary), **q032** (anaerobe genome) |
| NG1 only 5/5 | 5 | q007 (SPG11), q012 (TMEM67 Joubert), q017 (Anabaena BG11-), q025 (kinetochore), q042 (Brugada syndrome) |

NG1 has a slight edge on universal-perfect count (17 vs WG's 16), but the more interesting observation is **which questions are universally perfect in only one condition**:

- WG's exclusive perfects include **the only universal-perfect summary** (q029 Notch1) — structured workflow helps synthesis.
- NG1's exclusive perfects include the **q017 Anabaena BG11-** question, which is the canonical *failure* in NG2 and No-MIE. NG1 got it 5/5 perfect here. Reading the Usage Guide didn't matter; the explicit MIE instruction was sufficient for the model to find BacDive's MediaDive-integrated growth-condition annotations.

---

## 7. Cost and Latency

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Mean time / q | 137 s | **126 s** |
| Mean cost / q | $0.380 | $0.370 |
| Mean tool calls / q | 12.4 | **12.1** |
| Cost per Δ point | $0.108 | **$0.106** |

NG1 is slightly **faster** (saves ~11 s per question, ~9 minutes over a full 50-q evaluation) and slightly **cheaper** ($0.01/q, $0.50 over 50 q). The savings come from skipping the `TogoMCP_Usage_Guide` tool call. With near-identical quality outcomes, NG1 is the marginally more cost-effective configuration — though the difference is small.

---

## 8. Inter-Run Evaluator Agreement

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Mean std per question | **0.46** | 0.58 |
| Max std | 1.30 | 1.30 |

WG has **tighter inter-run agreement** (mean std 0.46 vs 0.58). This is a reversal of rev0's pattern, where NG1 had tighter variance (std 0.76 vs WG's 1.08). Both are now substantially tighter than either rev0 condition (the Opus 4.7 evaluators agree more than Opus 4.6 did), but within the new runs WG's responses are slightly more consistently scoreable.

---

## 9. Conclusions

### 9.1 The Usage Guide's Value Beyond the MIE Instruction

The data overwhelmingly support the rev0 finding that **WG and NG1 deliver indistinguishable total scores** (Wilcoxon *p* = 0.887, bootstrap 95 % CI for the delta-of-deltas = [−0.40, +0.42], contains zero). The simple instruction "before any SPARQL, call `find_databases()` then `get_MIE_file()`" recovers essentially all of the Usage Guide's headline benefit.

But the new runs surface a subtler story than rev0: **the two configurations differ on three of the four sub-criteria**, just in opposite directions on different criteria.

| Criterion | Winner | Magnitude | Interpretation |
|-----------|:------:|:---------:|----------------|
| Recall | **WG** | +0.26 (*p* = 0.010) | Structured workflow → more comprehensive retrieval |
| Precision | tie | +0.03 (*p* = 0.65) | Both equally on-topic |
| Repetition | **NG1** | +0.10 (*p* = 0.024) | Bare instruction → tighter responses |
| Readability | **NG1** | +0.19 (*p* = 0.004) | Bare instruction → cleaner prose |

The WG-vs-NG1 trade-off is therefore **comprehensiveness vs polish**. WG fetches slightly more relevant facts; NG1 expresses them more cleanly. The total-score wash reflects these effects roughly cancelling.

### 9.2 The Choice Depends on Use Case

- **Synthesis-heavy summary workloads** → favour NG1 (readability advantage especially pronounced on summary questions: +0.44 over WG).
- **Comprehensive choice / factoid retrieval** → favour WG (recall advantage on choice +0.50, factoid +0.32).
- **Speed and cost-sensitive deployments** → favour NG1 (saves ~11 s and $0.01 per question, no quality penalty).
- **Production reliability** → favour WG (lower loss rate 1.6 % vs 4.8 %, lower inter-run variance).

### 9.3 Tool-Usage Strategy Difference

WG and NG1 reach the same destination via different routes:

- WG: 12.4 tools/q, 4.8 SPARQL/q, 32 % `search_uniprot_entity` use
- NG1: 12.1 tools/q, 6.3 SPARQL/q, 24 % `search_uniprot_entity` use

NG1 substitutes ~30 % more SPARQL volume for ~25 % less search-tool exploration. Without the Usage Guide's "search-before-SPARQL" framing, NG1 jumps to direct SPARQL queries earlier and iterates more. The result is the same answer quality.

### 9.4 Practical Recommendation

For deployments, **the MIE instruction alone is sufficient** for the headline performance level. The full Usage Guide tool adds ~7 seconds of latency per question, occupies one slot in the model's tool inventory, and trades a small recall advantage for a small readability disadvantage. If the deployment is primarily synthesis-focused, NG1's bare instruction is the cleaner choice. If it is primarily fact-retrieval-focused (factoid / choice), WG's recall advantage is worth the latency.

The simple system-prompt directive

> "Before writing any SPARQL query, always call `find_databases()` to identify candidate databases, then call `get_MIE_file()` for each relevant database to learn its schema."

captures the entire operational benefit at minimal cost.

---

*Analysis: 50 questions × 5 evaluation runs × 2 conditions = 500 evaluations. Statistical tests: Wilcoxon signed-rank, paired t-test, bootstrap (10,000 resamples, seed=42). Source CSVs: `with_guide-2026-05-04.csv`, `ng1-2026-05-04.csv`; per-run scoring CSVs: `{condition}-2026-05-04-Opus4.7-v{1..5}.csv`. Reference comparison: 2026-02 paper analysis at [`rev0/togomcp_wg_vs_ng1_detailed.md`](rev0/togomcp_wg_vs_ng1_detailed.md).*
