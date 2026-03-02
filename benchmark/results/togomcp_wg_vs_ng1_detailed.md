# With Guide vs NG1: Detailed Comparison

**Conditions compared:**
- **With Guide (WG):** Full Usage Guide tool + MIE files available
- **NG1:** No Usage Guide, but explicit instruction to call `list_databases()` and `get_MIE_file()` before SPARQL queries

Both are independent experiment runs (different dates, different stochastic outcomes), so per-question differences reflect both instruction effects and run-to-run variability.

---

## 1. The Headline: Statistically Indistinguishable

| Metric | With Guide | NG1 | Difference |
|--------|:----------:|:---:|:----------:|
| TogoMCP score | 16.70 | 16.62 | +0.08 |
| Δ vs baseline | +2.72 | +2.73 | −0.01 |
| Cohen's *d* | 0.91 | 0.93 | −0.02 |
| Win rate | 74.8% | 74.8% | 0.0 pp |
| Loss rate | 14.4% | 19.2% | −4.8 pp |
| Perfect scores | 24.4% | 22.4% | +2.0 pp |

**Statistical tests for WG vs NG1:**

| Test | Statistic | *p*-value | Interpretation |
|------|:---------:|:---------:|:---------------|
| Wilcoxon (TogoMCP scores) | — | **0.827** | No difference |
| *t*-test (TogoMCP scores) | *t* = 0.27 | **0.788** | No difference |
| Wilcoxon (Δ comparison) | — | **0.537** | No difference |
| Bootstrap 95% CI for Δ diff | — | [−0.64, +0.68] | **Contains zero** |

The difference between WG and NG1 is **not statistically significant** by any test. The 95% bootstrap confidence interval for the Δ difference spans [−0.64, +0.68], centered essentially at zero. Whatever additional value the Usage Guide provides beyond the MIE instruction is indistinguishable from noise with 50 questions and 5 evaluation runs.

---

## 2. Where They Do Differ: Criteria-Level Analysis

While total scores are identical, **one criterion shows a significant difference**:

| Criterion | WG Δ | NG1 Δ | Diff (WG−NG1) | *p*-value |
|-----------|:-----:|:-----:|:-------------:|:---------:|
| Recall | +1.92 | +1.91 | +0.01 | 0.552 |
| Precision | +1.07 | +0.97 | +0.10 | 0.433 |
| Repetition | −0.05 | −0.19 | +0.14 | 0.072 |
| **Readability** | **−0.22** | **+0.04** | **−0.26** | **0.004** |

**NG1 has significantly better readability** (*p* = 0.004). WG responses degrade readability (Δ = −0.22), while NG1 responses maintain or slightly improve it (Δ = +0.04). WG has marginally better repetition control (*p* = 0.072), but the effect is not significant at α = 0.05.

### Readability by Question Type

| Type | WG Readability Δ | NG1 Readability Δ | Diff |
|------|:-----------------:|:-----------------:|:----:|
| **summary** | −0.66 | −0.28 | −0.38 |
| **choice** | −0.12 | +0.38 | −0.50 |
| **factoid** | −0.28 | +0.02 | −0.30 |
| yes_no | −0.02 | +0.10 | −0.12 |
| list | −0.02 | −0.00 | −0.02 |

The readability penalty is most acute for **summary** and **choice** questions under WG. One possible explanation: the Usage Guide's workflow encouragement may prompt WG to include more intermediate reasoning or verbose SPARQL result narration, whereas NG1's simpler instruction leads to more direct answers.

### Repetition by Question Type

| Type | WG Repetition Δ | NG1 Repetition Δ | Diff |
|------|:----------------:|:-----------------:|:----:|
| **list** | +0.14 | −0.16 | +0.30 |
| **choice** | +0.00 | −0.24 | +0.24 |
| yes_no | +0.16 | −0.00 | +0.16 |
| factoid | −0.12 | −0.26 | +0.14 |
| summary | −0.42 | −0.30 | −0.12 |

WG has slightly better repetition for list and choice questions, possibly because the Usage Guide's structured workflow prevents redundant tool calls that produce repeated content.

---

## 3. Tool Usage: Same Outcome, Different Strategies

### 3.1 Workflow Compliance

| Tool | WG | NG1 |
|------|:--:|:---:|
| Usage Guide | **100%** (50/50) | 0% (excluded) |
| `list_databases` | **100%** (50/50) | 92% (46/50) |
| `get_MIE_file` | 92% (46/50) | 92% (46/50) |
| `run_sparql` | 92% (46/50) | 90% (45/50) |

Despite lacking the Usage Guide, NG1 achieves near-identical compliance on the key tools. The 8% gap in `list_databases` (92% vs 100%) is the most visible difference.

### 3.2 First Tool Called

| First tool | WG | NG1 |
|------------|:--:|:---:|
| Usage Guide | **50** | — |
| `list_databases` | 0 (always 2nd) | **34** (68%) |
| `ncbi_esearch` | 0 | 5 (10%) |
| `search_uniprot_entity` | 0 | 5 (10%) |
| Other search tools | 0 | 6 (12%) |

WG has a perfectly uniform start: every question begins with Usage Guide → `list_databases`. NG1 starts with `list_databases` 68% of the time, but 32% of questions begin with a search tool, bypassing the discovery phase entirely. These questions still often succeed because the model finds MIE files later, but this occasional shortcut explains part of the higher variance.

### 3.3 Tool Diversity and Volume

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Unique tools used (total) | **31** | 24 |
| Mean unique tools/question | **6.1** | 4.6 |
| Mean total tools/question | 11.7 | 12.6 |
| Median tools/question | 10 | 12 |
| Tool range | 4–34 | 1–29 |

WG uses **more diverse** tools (31 vs 24 unique across all questions) and more unique tools per question (6.1 vs 4.6). WG-exclusive tools include `togoid_getAllRelation`, `search_pdb_entity`, `getAncestors`, `ncbi_list_databases`, and `Bash` — tools the Usage Guide presumably steers toward in specific scenarios.

NG1 uses slightly more tools per question on average (12.6 vs 11.7), suggesting it compensates for less strategic tool selection with more SPARQL attempts.

### 3.4 SPARQL Patterns

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Total SPARQL calls | 198 | **279** |
| Mean SPARQL/question | 4.0 | **5.6** |
| Questions with >10 SPARQL | 2 | **6** |
| Heavy SPARQL mean score | 16.0 | 15.6 |

NG1 makes **41% more SPARQL calls** overall. It is more aggressive with SPARQL, sometimes attempting 14–24 calls on a single question (vs WG's max of 17). These "heavy SPARQL" attempts (>10 calls) don't necessarily hurt — they average 15.6 in NG1 — but they don't help much either, and they inflate cost and latency.

The pattern suggests that the Usage Guide helps WG use SPARQL more *efficiently* (fewer calls, same results), while NG1 sometimes brute-forces its way through SPARQL trial and error.

---

## 4. Directional Agreement: Where Do They Diverge?

Of 50 questions, WG and NG1 agree on the direction of improvement in **70%** of cases:

| Outcome | Count | Percentage |
|---------|:-----:|:----------:|
| Both improve over baseline | 33 | 66% |
| Both worse than baseline | 2 | 4% |
| WG improves, NG1 doesn't | 8 | 16% |
| NG1 improves, WG doesn't | 6 | 12% |

The 14 questions where they disagree on direction are the most informative:

### 4.1 WG Wins, NG1 Loses (8 questions)

| Question | Type | WG Δ | NG1 Δ | Root cause |
|----------|------|:----:|:-----:|:-----------|
| question_027 | factoid | +5.2 | −1.2 | WG found 58 reactions; NG1 only found 13 (incomplete pathway coverage, 16 SPARQL calls) |
| question_034 | summary | +3.4 | −1.2 | WG correctly used AMRportal for resistance data; NG1 pulled incorrect species (S. pneumoniae not in ideal) |
| question_032 | yes_no | +2.2 | −2.4 | WG found genome data; NG1 failed on genome completeness query |
| question_023 | list | +2.6 | −1.2 | WG found correct MANE transcripts; NG1 had errors |
| question_030 | choice | +1.8 | −2.4 | WG found 10 genes (ideal 15); NG1 found only 5 with formatting artifacts |
| question_005 | choice | +1.0 | −1.0 | WG correct answer; NG1 count discrepancies |
| question_044 | list | +0.8 | −1.4 | WG incomplete but positive; NG1 more incomplete |
| question_021 | summary | +0.2 | −0.8 | WG marginal; NG1 imprecise aggregation |

**Pattern:** These tend to be complex multi-database questions (factoid, choice) where WG's broader tool diversity or Usage Guide workflow helped select the right databases. For example, question_027 required comprehensive Rhea + UniProt coverage; question_034 required AMRportal-specific queries.

### 4.2 NG1 Wins, WG Loses (6 questions)

| Question | Type | WG Δ | NG1 Δ | Root cause |
|----------|------|:----:|:-----:|:-----------|
| question_006 | factoid | −1.0 | +2.4 | NG1 found 69 targets (correct); WG only found 11 (subset) |
| question_009 | list | −1.8 | +0.8 | NG1 retrieved more enzymes than WG |
| question_017 | yes_no | −0.4 | +2.2 | NG1 found organism data; WG failed |
| question_045 | summary | −1.6 | +0.6 | NG1 more accurate summary |
| question_049 | summary | −0.6 | +1.2 | NG1 better coverage |
| question_035 | choice | −0.2 | +1.0 | Marginal; both near-correct |

**Pattern:** These are cases where NG1's more aggressive SPARQL approach paid off (question_006: 14 SPARQL calls to systematically enumerate metalloproteases, while WG's fewer calls missed most). Run-to-run stochasticity also plays a role.

---

## 5. Answer Quality: Qualitative Observations

Examining the actual answer text reveals some stylistic differences:

**WG answers** tend to:
- Include more intermediate reasoning visible in the output (e.g., "Excellent! The data looks good. The count of 58...")
- Occasionally expose process artifacts ("Now I need to count the unique ChEMBL IDs that have PDB mappings")
- Use slightly more structured formatting

**NG1 answers** tend to:
- Also include intermediate reasoning (e.g., "Perfect! Now I have all the information I need")
- Produce slightly more direct final answers when successful
- Sometimes provide incorrect answers with confident framing (question_007: correctly found all evidence then answered "No")

The question_007 case is particularly instructive: NG1 found the same evidence as WG (MANE Select transcript, PDB structures, ChEMBL entry) but then incorrectly concluded "No" by arguing the ChEMBL entry lacked functional drug target data. WG answered "Yes" correctly. This type of reasoning error is rare but not caused by missing schema knowledge — it's a reasoning/interpretation failure that occurs stochastically.

---

## 6. Evaluator Variance

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Mean baseline eval std | 0.76 | 0.63 |
| Mean TogoMCP eval std | **1.08** | 0.76 |
| Max TogoMCP eval std | **2.24** | 1.64 |

WG responses have **higher evaluator variance** (std 1.08 vs 0.76). This means the 5 evaluator LLMs disagree more about WG answer quality. This could be because:

1. WG's intermediate reasoning artifacts create ambiguity about answer quality
2. WG's more verbose responses are harder to score consistently
3. Random variation between experiments

The lower NG1 variance suggests its answers are more consistently scoreable, even if the overall quality is identical.

---

## 7. Score Distributions

| Score range | WG TogoMCP | NG1 TogoMCP |
|-------------|:----------:|:-----------:|
| 4–8 | 0 (0%) | 0 (0%) |
| 9–12 | 18 (7%) | 30 (12%) |
| 13–16 | 96 (38%) | 89 (36%) |
| 17–19 | 75 (30%) | 75 (30%) |
| 20 | 61 (24%) | 56 (22%) |

WG has slightly fewer low scores (7% in 9–12 range vs 12%) and slightly more perfect scores (24% vs 22%). NG1 has a slightly wider spread, consistent with its higher SPARQL attempt variance.

---

## 8. Cost and Efficiency

| Metric | WG | NG1 |
|--------|:--:|:---:|
| Mean time/question | **96.2 s** | 89.5 s |
| Mean cost/question | $0.429 | $0.432 |
| Input tokens | 29 | 35 |
| Output tokens | 3,100 | 3,443 |
| Cost per Δ point | $0.16 | $0.16 |
| Total cost (50 q) | $21.47 | $21.57 |

Costs and efficiency are virtually identical. WG is slightly *slower* (96.2 s vs 89.5 s) because the Usage Guide tool call adds overhead at the start of every question. NG1 produces slightly more output tokens (3,443 vs 3,100), likely from its more verbose SPARQL reasoning chains.

---

## 9. Perfect Score Analysis

| Questions with 5/5 perfect | WG | NG1 | Both |
|-----------------------------|:--:|:---:|:----:|
| question_047 (factoid) | ✅ | ✅ | ✅ |
| question_043 (factoid) | 4/5 | ✅ | ~shared |
| question_026 (yes_no) | 4/5 | ✅ | ~shared |
| question_038 (choice) | 4/5 | ✅ | ~shared |
| question_019 (choice) | 3/5 | ✅ | NG1 only |
| question_046 (yes_no) | 0/5 | ✅ | NG1 only |

Interestingly, NG1 has **6 questions with universal 5/5 perfect scores** vs WG's **1 question** (question_047). However, WG has **13 questions with ≥4/5 perfects** vs NG1's **8**. This suggests WG is more consistently near-perfect, while NG1 is more "all or nothing."

---

## 10. Conclusions

### 10.1 The Usage Guide's Value is Almost Entirely the MIE Instruction

The data overwhelmingly supports the conclusion that the Usage Guide's additional content (workflow ordering, search-before-SPARQL guidance, interleaving warnings, tool recommendations) provides **no measurable benefit** beyond what the simple instruction "call `list_databases()` and `get_MIE_file()` before SPARQL" already provides. The 95% CI for the effect of the guide's additional content is [−0.64, +0.68], centered at −0.01.

### 10.2 The Guide Slightly Changes *How* Results Are Achieved, Not *What*

| Aspect | WG advantage | NG1 advantage |
|--------|:------------:|:-------------:|
| Tool diversity | ✅ (31 vs 24 unique tools) | |
| SPARQL efficiency | ✅ (198 vs 279 calls) | |
| Repetition control | ✅ (marginal, *p* = 0.07) | |
| **Readability** | | ✅ (**significant**, *p* = 0.004) |
| Evaluator agreement | | ✅ (std 0.76 vs 1.08) |
| Starting consistency | ✅ (100% uniform start) | |
| Latency | | ✅ (89.5 s vs 96.2 s) |

WG uses tools more diversely and SPARQL more efficiently. NG1 produces more readable, consistently-scored answers and is slightly faster. These differences cancel out perfectly on total score.

### 10.3 The Self-Contradiction Risk Is Stochastic, Not Systematic

The question_007 case (NG1 answered "No" despite finding correct "Yes" evidence) appeared to suggest NG1 was prone to self-contradiction without the Guide's structure. However, the comprehensive data shows this is stochastic — NG1 has other questions where it reasons better than WG from the same evidence. The Guide does not reliably prevent reasoning errors.

### 10.4 Practical Recommendation

For deployments, the **MIE instruction alone is sufficient**. The full Usage Guide adds ~7 seconds of latency per question (for the guide tool call), uses a tool call slot, and provides no measurable quality improvement. The instruction `"Before writing any SPARQL query, always call list_databases() to discover available databases, then call get_MIE_file() for each relevant database to learn its schema"` captures the entire operational benefit.

---

*Analysis based on 50 questions × 5 evaluation runs × 2 conditions = 500 evaluations. Statistical tests performed with Wilcoxon signed-rank, paired t-test, and bootstrap (10,000 resamples).*
