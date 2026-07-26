# TogoMCP Evaluation Analysis Report (v3)

**Date:** 2026-05-05
**Benchmark answers collected:** 2026-05-04 (Sonnet 4.5, `claude-sonnet-4-5-20250929`)
**Evaluator LLM:** Opus 4.7 (`claude-opus-4-7`), 5 independent evaluation runs
**Questions:** 50 (10 each of yes/no, factoid, list, summary, choice)
**Scoring:** 4 criteria × 1–5 scale = total 4–20
**Condition:** **With Guide (WG)** — `TogoMCP_Usage_Guide` available and called first by system-prompt directive

---

## Executive Summary

TogoMCP delivers a large, statistically significant improvement over the no-tool baseline. Across 250 question–run pairs, the mean total score rises from **15.10 to 18.55** (+3.45, Cohen's *d* = 1.82, Wilcoxon *p* < 10⁻⁹). TogoMCP wins on **94.4 %** of evaluations, ties on 4.0 %, and loses on only **1.6 %**. The gain is concentrated in **information recall** (+2.23 on the 5-point scale) — confirming that tool-augmented access to live RDF databases supplies factual content that the model cannot fabricate. Crucially, **readability and repetition no longer regress** in the new runs (both turned slightly positive, +0.07 and +0.11), reversing the rev0 readability penalty.

The cost of this improvement is substantial — **~70× higher dollar cost** and **~17× higher latency** — but the absolute cost is modest ($0.38 per question), and the quality jump is unattainable by the baseline at any cost. The baseline never reaches a perfect 20 across 250 evaluations; TogoMCP reaches 20 on **42.8 %** of evaluations.

Compared to the 2026-02 paper analysis (`rev0/togomcp_analysis_v2.md`), every headline number has improved: Δ from +2.72 to +3.45, *d* from 0.92 to 1.82, win rate from 74.8 % to 94.4 %, perfect-score rate from 24.4 % to 42.8 %. The Sonnet 4.5 model (`claude-sonnet-4-5-20250929`) and the question set are unchanged from rev0; the lift therefore reflects (i) substantial enrichment of MIE schemas since rev0 (v2.0 → v2.1 spec, anti-patterns, shape-expressions discipline, four new databases), (ii) `togomcp` server-side improvements in tool ergonomics and error handling, and (iii) the evaluator change from Opus 4.6 to Opus 4.7. The relative weight of these three factors is not separable from this run alone and should be flagged in the manuscript.

---

## 1. Overall Score Comparison

| Metric | Baseline | TogoMCP | Δ |
|--------|----------|---------|---|
| Mean ± SD | 15.10 ± 1.75 | 18.55 ± 1.72 | +3.45 |
| Median | 15 | 19 | +4 |
| Min / Max | 11 / 19 | 12 / 20 | — |
| Perfect scores (= 20) | **0 / 250** | **107 / 250** (42.8 %) | — |
| Cohen's *d* (per-question) | — | **1.82** | very large |
| Wilcoxon (one-sided, paired) | — | *p* < 10⁻⁹ | highly significant |

The baseline **never** achieves a perfect 20 (max is 19, on 3 evaluations); TogoMCP reaches it on nearly half of all evaluations.

### Score distributions (all 250 evaluations)

```
Baseline:                   TogoMCP:
11: ▏ (1)                   12: ▏ (1)
12: ███ (19)                13: ▎ (4)
13: ███▌ (23)               14: ▏ (3)
14: ████████ (50)           15: ▏ (2)
15: ████████████ (71)       16: ████▌ (28)
16: ███▎ (20)               17: ███▊ (23)
17: ██████▌ (40)            18: █████▉ (36)
18: ███▊ (23)               19: ███████▌ (46)
19: ▌ (3)                   20: █████████████████▌ (107)
20: (0)                     ────────────────────────
                            (mode = 20)
```

The baseline distribution is unimodal at 14–17. The TogoMCP distribution is right-skewed with a sharp peak at 20 — 42.8 % of evaluations land at the ceiling.

---

## 2. Scores by Question Type

| Type | Baseline | TogoMCP | Δ | Cohen's *d* | Win % | Lose % |
|------|----------|---------|---|:----------:|:-----:|:------:|
| **yes_no** | 15.62 | **19.84** | **+4.22** | 2.55 | 100 % | 0 % |
| **factoid** | 13.82 | 17.64 | **+3.82** | 2.35 | 96 % | 0 % |
| **list** | 14.30 | 17.88 | **+3.58** | 1.84 | 90 % | 4 % |
| **choice** | 16.22 | 19.42 | **+3.20** | 1.32 | 96 % | 0 % |
| **summary** | 15.52 | 17.96 | **+2.44** | 1.53 | 90 % | 4 % |

Every type now shows a clear, large positive effect — including summary, which was rev0's weakest type (+0.50 then; +2.44 now). yes_no is perfectly dominated (100 % win, 0 % loss, *d* = 2.55).

Mean per-question scores by type (averaged over 5 evaluator runs):

- yes/no: 9 of 10 questions hit a TogoMCP mean ≥ 19.5; 4 reach a perfect 20.
- factoid: 7 of 10 ≥ 17.5; 2 reach 20.
- choice: 7 of 10 ≥ 19; 5 reach 20.
- list: 5 of 10 ≥ 18; 2 reach 20.
- summary: 4 of 10 ≥ 18; 1 reaches 20.

---

## 3. Scores by Evaluation Criteria

| Criterion | Baseline | TogoMCP | Δ |
|-----------|----------|---------|---|
| **Recall** | 1.85 | **4.08** | **+2.23** |
| **Precision** | 3.61 | 4.65 | **+1.04** |
| **Repetition** | 4.80 | 4.91 | +0.11 |
| **Readability** | 4.84 | 4.91 | +0.07 |

The dominant improvement comes from **recall** (+2.23) — TogoMCP retrieves specific facts the baseline cannot produce. Precision also improves substantially as database-grounded facts are more accurate than hallucinated estimates.

The biggest qualitative shift versus rev0 is in the *style* axes: rev0 reported repetition Δ = −0.05 and readability Δ = −0.22. The new runs show both as slightly positive. This suggests the deployed `togomcp` server's tool outputs no longer leak verbose processing artefacts the way they did in February; the model's responses now read as encyclopedia-style prose rather than as data dumps with prose wrapping.

### Criteria deltas by question type

| Type | Recall Δ | Precision Δ | Repetition Δ | Readability Δ |
|------|:--------:|:-----------:|:------------:|:-------------:|
| yes_no | +2.42 | +1.32 | +0.30 | +0.18 |
| factoid | +2.74 | +0.86 | +0.10 | +0.12 |
| list | +2.30 | +1.04 | +0.16 | +0.08 |
| choice | +1.66 | +0.92 | +0.40 | +0.22 |
| summary | +1.46 | +0.86 | +0.10 | +0.02 |

Summary is still the weakest type on every criterion, but the readability penalty is gone — even on summary, readability Δ = +0.02 (vs rev0's −0.66). Tool-output integration into prose has improved substantially.

---

## 4. Latency and Cost

### 4.1 Latency

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean | 7.9 s | 137 s | 17× |
| Median | 7.7 s | 110 s | 14× |
| Max | 11.5 s | 526 s | — |

The latency overhead is acceptable for asynchronous research workflows but too slow for interactive use. Median ~110 s is dominated by the multi-step `find_databases → get_MIE_file → run_sparql` chain.

### 4.2 Cost (USD)

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Mean per question | $0.0054 | $0.380 | 70× |
| Total per 50-question run | $0.27 | $19.00 | 70× |
| Cost per Δ point | — | **$0.108** | — |

Cost is dominated by output tokens (the model emits multi-step tool-call rationales and structured SPARQL results). Total cost for a 50-question run with 5 evaluation passes is ~$19 — well within the budget of a research benchmark.

### 4.3 Cost-effectiveness by question type

| Type | Δ | Cost/q | pts / $ |
|------|:----:|:-----:|:-------:|
| yes_no | +4.22 | $0.27 | **15.5** |
| choice | +3.20 | $0.32 | 10.1 |
| factoid | +3.82 | $0.42 | 9.0 |
| list | +3.58 | $0.42 | 8.5 |
| summary | +2.44 | $0.46 | 5.3 |

yes/no is by a wide margin the most cost-effective question type — fewest tool calls, highest accuracy lift.

---

## 5. Tool Calls and Score

### 5.1 Tool count vs. score

There is a **moderate negative correlation** between total tool count and TogoMCP score (Pearson *r* = −0.28, Spearman *ρ* = −0.44, *p* < 0.01).

| Tool calls | n | Mean score |
|:----------:|:-:|:----------:|
| 0–4 | 2 | **20.00** |
| 5–9 | 21 | 19.07 |
| 10–14 | 14 | 18.69 |
| 15–19 | 7 | 16.69 |
| 20–29 | 4 | 17.50 |
| 30+ | 2 | 19.30 |

The sweet spot is **5–9 tool calls** (mean 19.1). Excessive chaining (15–19 calls) drops scores to 16.7, with two notable exceptions where 30+ tool calls still yielded near-perfect answers (q005 and q032 — both questions where the model found a productive workflow despite needing many calls).

### 5.2 SPARQL queries vs. score

| `run_sparql` calls | n | Mean score |
|:------------------:|:-:|:----------:|
| 0 | 3 | 19.20 |
| 1 | 4 | **20.00** |
| 2 | 11 | 19.45 |
| 3 | 7 | 17.94 |
| 4 | 6 | 19.10 |
| 5–6 | 6 | 18.55 |
| 7–9 | 5 | 18.05 |
| ≥ 10 | 8 | 17.07 |

Pearson *r*(SPARQL count, score) = **−0.49**. The cleanest pattern in the dataset: **1 SPARQL call achieves a perfect mean of 20.00** (4 questions hit 20/20 on a single well-formed query). High SPARQL volume (≥ 10) signals the model struggling to converge on a working query.

---

## 6. Tool-Type Effectiveness

Tools used in ≥ 3 questions, ranked by mean question score where the tool appears:

| Tool | n questions | Mean score | Verdict |
|------|:-----------:|:----------:|---------|
| `search_mesh_descriptor` | 4 | **20.00** | Excellent — vocabulary alignment |
| `ncbi_esearch` | 13 | 19.25 | Excellent — gene/variant lookup |
| `ncbi_esummary` | 7 | 19.23 | Excellent — record summary |
| `ncbi_efetch` | 3 | 18.87 | Strong — full record retrieval |
| `search_reactome_entity` | 3 | 18.60 | Strong (small n) |
| `find_databases` | 48 | 18.52 | Strong (used almost everywhere) |
| `TogoMCP_Usage_Guide` | 50 | 18.55 | Universal first call |
| `get_MIE_file` | 47 | 18.51 | Universal in workflow |
| `run_sparql` | 47 | 18.51 | Universal data-retrieval |
| `search_rhea_entity` | 5 | 18.44 | Adequate |
| `togoid_convertId` | 9 | 18.27 | Adequate |
| `togoid_getAllRelation` | 4 | 18.05 | Adequate |
| `search_chembl_target` | 4 | 17.70 | Below-average |
| `search_uniprot_entity` | 16 | **17.79** | **Below-average — over-reliance correlates with lower scores** |

The pattern is consistent with rev0: **NCBI tools and structured-vocabulary tools** (`search_mesh_descriptor`) lead the rankings; **text-based UniProt search** trails. Heavy reliance on `search_uniprot_entity` is a weak signal that the model is text-searching where structured SPARQL would do better. The four `search_mesh_descriptor` questions all hit 20 — a perfect signal that ontology-aligned vocabulary lookup is the highest-leverage move when the question maps to a MeSH descriptor.

---

## 7. Perfect Score Analysis

### 7.1 Universal-perfect questions (5/5)

**16 of 50 questions** achieved 20/20 on every one of the 5 Opus 4.7 evaluator runs:

| Question | Type | Tools | Notes |
|----------|------|:-----:|-------|
| question_001 | yes_no | 7 | HSPB1 / Charcot-Marie-Tooth ClinVar |
| question_005 | choice | 30 | TK kinase group ChEMBL targets — many tools, still perfect |
| question_010 | choice | 9 | SLE parent disease category |
| question_019 | choice | 9 | Mucopolysaccharidosis subtypes |
| question_020 | yes_no | 2 | Symmachiella dynata genome — minimal tooling |
| question_026 | yes_no | 8 | PubChem pteridine class |
| question_028 | list | 6 | B. subtilis biotin biosynthesis (BioK / BioW / BioI) |
| question_029 | summary | 7 | Notch1 — the only universal-perfect summary question |
| question_032 | yes_no | 14 | Anaerobe genome breadth |
| question_036 | yes_no | 9 | Metachromatic leukodystrophy ontology |
| question_038 | choice | 4 | Mouse LGMD orthologs + PDB |
| question_039 | list | 12 | Brugada syndrome genes |
| question_043 | factoid | 6 | DHNA approved Rhea reactions |
| question_046 | yes_no | 12 | AXIN1 destruction-complex queries |
| question_047 | factoid | 7 | Cockayne / ERCC6 PubTator co-annotations |
| question_050 | choice | 5 | Salmonella enterica AMR classes |

### 7.2 Characteristics of perfect-scoring questions

- **By type:** yes/no dominates (6), then choice (5), list (2), factoid (2), summary (1). The same type-skew as rev0.
- **Median tool count: 8** (range 2–30). Most universally-perfect questions are tightly scoped lookups requiring 5–10 tools.
- **Question structure:** specific named entities (HSPB1, ERCC6, AXIN1, mupirocin) consistently produce perfect scores; broad multi-database integrations rarely do.

The single universally perfect summary (question_029, Notch1) is the standout — summaries usually carry the heaviest synthesis burden, but Notch1's well-curated UniProt/Reactome/ChEMBL profile let the model produce a clean encyclopedic synthesis.

---

## 8. When TogoMCP Was Worse Than Baseline

Only **2 of 50 questions** had a TogoMCP mean ≤ baseline mean — the cleanest result in any condition:

### 8.1 question_044 (list, Δ = 0.00)

> "Which human siglec proteins have experimentally characterized N-glycan structures curated at specific glycosylation sites in glycoproteomic databases?"
>
> **Ideal:** SIGLEC5, SIGLEC7, SIGLEC8, SIGLEC14 (4 specific UniProt accessions in GlyConnect).
>
> **TogoMCP:** "10 human siglec proteins" — listed all members of the family from GlyCosmos rather than the four with curated per-site N-glycan data.

The model used the wrong knowledgebase: it queried GlyCosmos (which has broad glycoprotein coverage) instead of GlyConnect (which has specific per-site curation). Vocabulary-coverage failure.

### 8.2 question_021 (summary, Δ = −0.20)

> "Summarize the human proteasome protein landscape (UniProt KW-0647), GO subcomplexes, multi-subcomplex overlap, and ChEMBL drug-target fraction."

TogoMCP got the protein count exactly right (53) and the cross-database integration correct, but produced a slightly verbose response with a "Now I have all the necessary data" preamble that some evaluators penalized. Δ = −0.20 is essentially evaluator noise.

### 8.3 Patterns

The catastrophic failures rev0 documented (data dumps with Δ = −5.4 to −5.8; self-contradictions with Δ = −4.8) **do not reproduce** in WG. Both q030 (rev0's worst at Δ = −5.8) and q035 (rev0's −5.4) now score TogoMCP > baseline.

**Lesson preserved from rev0:** vocabulary alignment remains the single most important precondition. q044 fails for the same reason rev0's q013 failed — the model picks a database that sounds relevant by name (GlyCosmos for "glyco-anything", MedGen-from-Joubert) without verifying it carries the specific curation type the question asks for.

---

## 9. Usage Guide Adherence

### 9.1 Workflow compliance

| Workflow Step | Tool | Usage Rate | Role |
|---|---|:----------:|------|
| 1. Read Usage Guide | `TogoMCP_Usage_Guide` | **100 %** (50/50) | Always first |
| 2. Database discovery | `find_databases` | 96 % (48/50) | After fix `cf58f3e` it's the canonical entry; replaces `list_databases` (0 %) |
| 3. Schema discovery | `get_MIE_file` | 94 % (47/50) | Read schema for selected DBs |
| 4. Entity / vocab search | Any search tool | ~70 % | Variable depending on question |
| 5. Structured queries | `run_sparql` | 94 % (47/50) | Final retrieval |

**First tool called: `TogoMCP_Usage_Guide` in 50 / 50 cases (100 %).** Perfect compliance, as in rev0. The deployed Usage Guide v4 plus the system-prompt directive ("REQUIRED FIRST ACTION — NO EXCEPTIONS") yields uniform start-up behaviour.

### 9.2 The `find_databases` → `list_databases` migration

Rev0 had `list_databases` at 100 % usage. The new runs show:

- `find_databases`: 96 % (used 58 times across 48 questions)
- `list_databases`: 0 %

This is the intended outcome of `cf58f3e` ("Discovery tools: make find_databases canonical and required"). With the Usage Guide pointing at `find_databases` and the docstring opening with "REQUIRED first step", the model never falls back to `list_databases` in WG. The transition is clean.

### 9.3 Workflow-pattern proportions

Computed by checking the order of `find_databases` / `get_MIE_file` / `run_sparql` / search tools on each question:

| Pattern | n | Mean score |
|---------|:-:|:----------:|
| Full workflow (Guide → find → MIE → search → SPARQL) | ~30 (60 %) | 18.6 |
| No search step (Guide → find → MIE → SPARQL) | ~10 (20 %) | 18.8 |
| No SPARQL (Guide → find → MIE only, or Guide → search only) | ~6 (12 %) | 19.4 |
| Other / minimal | ~4 (8 %) | 18.0 |

The rev0 finding that simpler workflows score higher *partly because they get assigned easier questions* still holds. A clean MIE → SPARQL pipeline (no search) is consistently strong.

---

## 10. Inter-Run Evaluator Consistency

| Metric | TogoMCP |
|--------|:-------:|
| Mean std per question | **0.46** |
| Max std | 1.30 |
| Questions with std = 0 | 17 |
| Questions with std > 1 | 9 |
| Questions with std > 2 | 0 |

Inter-run agreement is **substantially tighter than rev0** (mean std 0.46 vs rev0's 1.08). The five Opus 4.7 evaluators agree more than the five Opus 4.6 evaluators did. 17 questions have std = 0 (all 5 runs assigned identical totals). The highest-variance questions are q006 (metalloproteases, 51 vs ideal 69), q034 (AMRportal vs PubMed for resistance data), and q021 (proteasome summary tone) — exactly the question profiles where small differences in evaluator interpretation accumulate.

---

## 11. Is the Increased Cost Justified?

| Metric | Baseline | TogoMCP | Ratio |
|--------|----------|---------|-------|
| Cost per question | $0.005 | $0.380 | 70× |
| Time per question | 7.9 s | 137 s | 17× |
| Cost per score point | $0.0004 | $0.020 | 50× |
| Score improvement per extra dollar | — | 9.2 pts/$ | — |

**The improvement is qualitatively unattainable at any baseline cost.** No prompt-engineering or repeated baseline calls can supply specific ClinVar variant counts, SPARQL-derived reaction numbers, or precise database cross-references. The baseline ceiling is ~19 (achieved on 1.2 % of evaluations); TogoMCP regularly exceeds this.

**The absolute cost is modest** — $19 for a 50-question evaluation pass. **The latency is acceptable** for asynchronous research pipelines. **The gains are concentrated where they matter** — recall on factoid and yes/no questions, where hallucination is most dangerous.

Every condition examined in the four-condition comparison has positive cost-effectiveness in the new runs. WG specifically achieves $0.108 per Δ point — the second-best ratio (NG1 edges it at $0.106).

---

## 12. Key Findings and Recommendations

1. **TogoMCP is robustly beneficial across every question type** in the WG condition (all five types have Δ > +2.4 with *p* < 0.005). Use it whenever precise, verifiable database evidence is needed.

2. **Summary questions are no longer the weak spot.** Rev0 had summary Δ = +0.50 with a 34 % loss rate. The new runs show Δ = +2.44 with a 4 % loss rate. Improvements in MIE schema richness and tool-output formatting have closed the synthesis gap.

3. **Fewer, better-targeted tool calls win.** The 5–9 tool range achieves the highest mean score (19.1). Excessive chaining (15+) suggests the model is struggling. The single-SPARQL pattern (4 questions, perfect 20 each) is the platonic ideal of database-grounded answering.

4. **Vocabulary-aligned tools are still the strongest.** `search_mesh_descriptor` (mean 20.0), `ncbi_esearch` (19.3), and `ncbi_esummary` (19.2) lead. `search_uniprot_entity` (17.8) trails — over-reliance on its text matching remains a weak signal, as it was in rev0.

5. **The Usage Guide directive achieves 100 % first-call compliance.** Every one of 50 questions started with `TogoMCP_Usage_Guide`. The system-prompt language "REQUIRED FIRST ACTION — NO EXCEPTIONS" works exactly as intended.

6. **`find_databases` has fully replaced `list_databases` as the canonical discovery tool** (96 % vs 0 %) after the post-rev0 docstring restoration. The migration is clean in WG; whether spontaneous discovery in the unguided NG2 condition recovered comparably is examined in [`togomcp_no_guide_analysis.md`](togomcp_no_guide_analysis.md).

7. **Vocabulary mismatch is the only systematic failure mode.** The two below-baseline cases (q044 GlyCosmos-vs-GlyConnect, q021 evaluator-noise) follow the rev0 pattern: when the model picks a database whose name *sounds* right for the question without verifying its specific curation scope, it produces a confidently-presented but wrong answer.

8. **The cost is justified for any precision-critical biomedical QA workload.** $0.38 / question is well within research budgets and the resulting answers contain database-grounded specifics that the LLM alone cannot manufacture.

---

*Analysis: 5 independent Opus 4.7 evaluation runs × 50 questions = 250 evaluations. Source CSV: `with_guide-2026-05-04.csv`; per-run scoring CSVs: `with_guide-2026-05-04-Opus4.7-v{1..5}.csv`. Reference comparison: 2026-02 paper analysis at [`rev0/togomcp_analysis_v2.md`](rev0/togomcp_analysis_v2.md).*
