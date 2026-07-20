# MIE Subcomponent Ablation — Findings (2026-07 sweep)

The generated `results/ablation_report.md` is gitignored (regenerable). This file is
the durable record of what the 2026-07 sweep actually found, and — more usefully —
of the two methodological traps it walked into, so the next run doesn't repeat them.

## What was run

| | |
|---|---|
| Design | 12 conditions (baseline + 11 leave-one-out) × 40-question pilot × 3 replicates |
| Answering | `claude-sonnet-4-5-20250929`, **Anthropic API** (`--answer-use-api`) |
| Judge | `claude-opus-4-8`, **Anthropic API**, forced-tool-call (`--judge-use-api`) |
| Cost / wall | ~$845 / ~72 h, 0 login errors |
| Analysis | `ablation_analysis.py --exclude-ceiling 20 --exclude-floor 12` (n=34 after exclusions) |

## Headline: a null result

**0 of 11 sections** have a 95% CI excluding 0 — on *any* axis (judge score,
exact-answer correctness, or effort). Baseline mean **17.13/20**.

| Section | Contribution (±95% CI) | z | Δ run_sparql (±CI) |
|---|---:|---:|---:|
| `common_errors` | **+0.65 ± 0.65** | **+1.94** | +0.63 ± 1.04 |
| `cross_database_queries` | +0.25 ± 0.77 | +0.63 | −0.02 ± 0.75 |
| `architectural_notes` | +0.23 ± 0.51 | +0.91 | −0.10 ± 0.46 |
| `schema_info` | +0.20 ± 0.50 | +0.77 | −0.07 ± 0.66 |
| `critical_warnings` | +0.14 ± 0.62 | +0.43 | −0.19 ± 0.69 |
| `data_statistics` | +0.07 ± 0.66 | +0.21 | +0.11 ± 0.79 |
| `anti_patterns` | +0.04 ± 0.40 | +0.19 | −0.05 ± 0.43 |
| `cross_references` | −0.06 ± 0.52 | −0.22 | −0.36 ± 0.48 |
| `sample_rdf_entries` | −0.08 ± 0.63 | −0.24 | −0.09 ± 0.76 |
| `sparql_query_examples` | −0.13 ± 0.57 | −0.44 | +0.66 ± 0.88 |
| `shape_expressions` | −0.15 ± 0.54 | −0.53 | −0.13 ± 0.86 |

`common_errors` is the one near-miss: z=1.94 (nominal p≈0.052), and the only section
pointing the same way on both quality (+0.65) and effort (+0.63). **It is not a
finding.** 11 sections were tested; Bonferroni needs |z| > 2.84, and one borderline
hit out of 11 is roughly what chance produces.

Scaling from its effect size, `common_errors` would need **n≈73** to clear the
corrected bar (n≈88, i.e. the full 100-question set, would give z≈3.1). A partial
extension to n≈57 would only have produced a nominally-significant result that still
failed correction — the worst of both worlds. It's the full set or nothing.

## Trap 1 — never bank a baseline across batches

The first analysis showed **every** contribution slightly negative (−0.16…−0.51),
i.e. removing any section apparently *helped*. That was an artifact, not an effect:

* The baseline had been **banked from a 1-condition trial run 1–2 days earlier** and
  was *skipped/reused* by the sweep, so it was a different batch than the ablations.
* All 11 contributions subtract the **same** baseline mean, so they are not 11
  independent signals. One baseline sitting ~0.4 low drags every contribution
  negative *together* — "11 of 11 negative" is one event, not eleven.
* Re-running the baseline **fresh, in the same batch** moved it 16.72 → **17.13**
  (+0.41) and the uniformly-negative pattern vanished into a healthy mixed spread
  (7 positive / 4 slightly negative). It rebased the *effort* axis too: the old
  "removing any section costs more query effort" was equally an artifact.

**Rule:** a question's baseline and ablated rows must come from the same batch.
`run_ablation.py` skips a condition whose `<cond>-scored.csv` exists — convenient for
resuming an interrupted sweep, dangerous if it silently reuses a baseline from an
earlier session. When extending (`append_results.py`), run **every** condition for the
new questions in one batch.

## Trap 2 — an aggregate difference is not a per-question effect

Before error bars, `sparql_query_examples` looked like a clear winner: removing it
drove SPARQL calls 466 → 585 (**+25%**) across the run. It does not survive pairing.
Per-question query counts vary enormously (paired SD ≈ 3.2), so the per-question
delta was +0.87 ± 1.07 — CI includes 0. The aggregate ratio was reading a sum as an
effect. Every delta reported here is now a *paired per-question* difference with a CI.

## Interpreting the null

Leave-one-out measures **marginal** contribution: each section is removed while the
other 10 remain, so redundant siblings cover for it. Near-zero means "not individually
necessary given everything else" — **not** "worthless". The agent still answers well
(baseline 17.13/20) and still leans on SPARQL (~85% of answers) without any one
section.

Two levers remain, in order of expected value:

1. **Group ablation** — remove a whole functional group at once so redundancy can't
   compensate. **Run 2026-07-19 → also null on both axes** (see the next section).
   Predicted `guardrails` would lead; it came last. The redundancy-compensation
   hypothesis this lever was meant to expose was *refuted*, not confirmed.
2. **The full 100-question set** — n≈88 would resolve a `common_errors`-sized effect
   even after multiple-comparison correction. `append_results.py` extends n without
   re-running what's already done.

A sharper *effort* signal would also help: `tools_used` records tool **names** only,
so we can count queries but not their **outcomes**. Logging each `run_sparql` result
(syntax error / empty / rows) in `automated_test_runner.py` would give failed-query
rate and first-query success rate — far more sensitive than raw call counts, and it
would directly test whether the query-guidance sections do what they claim.

## Group ablation (2026-07-19 sweep) — the follow-up, also null

The 2026-07-08 sweep left "run the group ablation" as the top lever. It took nine days
to actually land, because **every prior group attempt was silently voided by a
harness bug** — not by anything about the science.

### The bug that ate every earlier group attempt

`run_ablation.py` passes the rendered-config path (`-c`) and answer-output path (`-o`)
to the runner/judge subprocesses, which run with `cwd=SCRIPTS_DIR`. When
`--results-dir` was **relative** — exactly as the README's group recipe documented
(`--results-dir results_groups`) — those paths resolved against `benchmark/scripts`
instead of `benchmark/ablation`. The config was then *not found*, the runner fell back
to **default settings (production togomcp URL, full MIEs)**, and the booted-but-idle
local server was never queried. Every condition served identical full MIEs → zero
ablation signal. The section sweep escaped this only because it used the **absolute**
default results dir (`HERE/"results"`); the group command's relative `--results-dir`
was the sole trigger. Tell-tale: a compromised condition's `<cond>-server.log` has
**0 `CallToolRequest`s** while a valid one has ~1500. Fixed in `c7fc2cd`
(`Path(args.results_dir).resolve()`); the valid run below shows 1492–2041 tool calls
per condition. **Always confirm non-zero `CallToolRequest`s per condition before
trusting an ablation result.**

### What was run

| | |
|---|---|
| Design | 4 conditions (baseline + 3 groups) × 40-question pilot × 3 replicates |
| Groups | `query` (schema_info, shape_expressions, sparql_query_examples, cross_references, cross_database_queries; 53% of MIE bytes) · `guardrails` (critical_warnings, common_errors, anti_patterns; 25%) · `orientation` (architectural_notes, data_statistics, sample_rdf_entries; 22%) |
| Answering / Judge | `claude-sonnet-4-5-20250929` / eval default, **Anthropic API** (`--answer-use-api --judge-use-api`) |
| Cost / wall | ~$265 answering / ~27.5 h |
| Validity | per-condition local-server tool calls 1492–2041 (all queried the stripped local server, not production) |

### Headline: null on judge score; a borderline query-correctness near-miss

**No group clears the multiple-comparison bar on either axis.** On judge score all three
CIs include 0. On exact-answer correctness `query`'s *untrimmed* CI now barely excludes 0
(+0.088 ± 0.087, z=1.97) — but that is the single-comparison threshold; with k=3 the bar is
|z|>2.39, its trimmed CI still includes 0, so it does not survive. Baseline **16.88/20**
(trimmed). Removing the entire `query` group — **53% of the MIE** — costs only **+0.20 pts**
on the score.

Judge score (`ablation_analysis.py --exclude-ceiling 20 --exclude-floor 12`, n=35;
untrimmed n=40 in parens):

| Group | Contribution (±95% CI) | z | Δ run_sparql (±CI) | Δ correctness |
|---|---:|---:|---:|---:|
| `query` | **+0.20 ± 0.40** (+0.23 ± 0.39) | +0.98 | +0.83 ± 1.67 | +9pp |
| `orientation` | +0.10 ± 0.52 (+0.11 ± 0.47) | +0.38 | −0.86 ± 0.99 | −3pp |
| `guardrails` | +0.04 ± 0.45 (+0.04 ± 0.39) | +0.17 | **−0.92 ± 0.92\*** | +6pp |

Exact-answer correctness, paired per question **with a CI** (gradable questions only, so
summary-type are dropped → **n=32 untrimmed / 27 trimmed**; Q071 became gradable on
2026-07-20 when `grade_exact` was generalized to score compound "entity (N)" factoids on
both parts — before that its string gold returned `None`):

| Group | Δ correctness (±95% CI), untrimmed | z |
|---|---:|---:|
| `query` | **+0.088 ± 0.087** | +1.97 |
| `guardrails` | +0.061 ± 0.091 | +1.30 |
| `orientation` | −0.027 ± 0.091 | −0.58 |

Removing `query` is the **only near-miss on either axis**: its correctness drop sits right
at the nominal single-comparison threshold (z≈1.97, untrimmed CI just excludes 0) but fails
the k=3 correction and reverts to CI-includes-0 when trimmed (+0.092 ± 0.095, z=1.89) — a
real trend, still underpowered. Correctness has *less* power than the score axis (n=32 vs 40).

### What it means

* **The redundancy hypothesis is refuted.** The group sweep existed because
  leave-one-*section*-out was null *supposedly* because redundant siblings compensated —
  so removing a whole group should show a big effect. It doesn't. Group effects are as
  null as single-section effects. Redundancy isn't the story; on this metric/these
  questions the MIE content just doesn't move the score.
* **The pre-registered prediction failed.** Σ-of-single-sections predicted `guardrails`
  leads (+0.82). It came **last** (+0.04); `query` leads but null. The Σ heuristic has
  no predictive value here.
* **The one robust effect is behavioral, not quality:** removing `guardrails`
  significantly **cuts** SPARQL calls (−0.92\*) — the warnings provoke extra defensive
  queries. Trimmed and untrimmed agree on ordering, magnitudes, and this significance.
* **Ceiling is the likely ceiling on power.** Baseline ~16.7–16.9/20 with per-question
  SD≈1 (see the baseline-variability note): the judge score is too saturated to resolve
  sub-0.4-pt effects even at runs=3. To chase the `query` correctness trend, make
  correctness the primary endpoint and power n to ~150+, or add per-query outcome
  logging (failed/empty/rows) for a sharper effort signal.

## no_mie (whole MIE removed) — 2026-07-19/20 sweep — the FIRST non-null

Escalation of the group null: if removing 53% of the MIE (the `query` group) did
nothing, does removing **all** of it? `no_mie` blocks `get_MIE_file` at the tool level
(`config_no_mie.yaml` `disallowed_tools` + a matching prompt) instead of stripping the
corpus — so the agent keeps every other tool (run_sparql, NCBI, PubChem, search_*) and
loses only the MIE. Run as a first-class `run_ablation.py` condition
(`--conditions no_mie --base-config benchmark/scripts/config_no_mie.yaml`; a guard
refuses a base config that still allows get_MIE_file) on the local server, so it pairs
against the group sweep's baseline. Validity: **0** get_MIE_file executions server-side
(13 attempts, all blocked — the model still reflexively reaches for it ~7% of questions).

**Result: significant.** baseline − no_mie on the judge score:

| judging | trim | contribution (±95% CI) | z |
|---|---|---:|---:|
| 1-judge (3 ans×1) | untrimmed | +0.93 ± 0.68 | 2.68 ✱ |
| 5-judge (3 ans×5) | untrimmed | +0.88 ± 0.66 | 2.62 ✱ |
| 5-judge (3 ans×5) | trimmed (−4) | +0.91 ± 0.72 | 2.48 ✱ |

A single planned comparison, so the bar is |z|>1.96; the effect clears it (p≈0.007–0.02)
and is stable across judge treatments (0.88–0.94). Exact-answer **correctness** drops only
+0.06–0.07 (NS, n=32: +0.056 ± 0.119 untrimmed / +0.073 ± 0.129 trimmed) — the MIE improves
judged *quality* more than raw correctness.

### The redundancy arc completes (and reverses the group conclusion)

| removed | contribution | significant? |
|---|---:|---|
| one section (×11) | ≤ +0.65 | none |
| one group (×3) | ≤ +0.20 | none |
| Σ of the 3 groups | +0.34 | — |
| **whole MIE** | **+0.88–0.93** | **yes** |

The whole-MIE effect is **~2.7× the sum of its group parts** — super-additive, the
signature of **strong redundancy**. This *disambiguates* the group nulls: alone they were
"no value OR redundant"; no_mie shows the MIE genuinely helps (+0.9/20), so the group
nulls are **redundancy, not worthlessness**. Section-null + group-null + whole-significant
is one coherent story: real value, heavily distributed. (The earlier "redundancy refuted"
note in the group section was premature — it's *confirmed* once no_mie is in hand.)

### Variance is ANSWER-limited, not judge-limited (corrects a standing assumption)

The 5× re-judge barely moved the CI (±0.68→±0.66). Decomposing the baseline's
3 answers × 5 judges: judge-jitter SD **0.41** vs between-answer (agent stochasticity)
SD **1.20** — the per-question mean variance is `va/3 + vj/15` = 0.478 + 0.011, i.e.
**98% answer-side**. So the pilot's CIs are limited by agent run-to-run variance, NOT
judge jitter — reversing the belief (carried in the baseline-variability notes and the
group caveats) that judge jitter dominated. The conditions study benefited from 5 judges
because it had *1 answer*; our 3-answer design is answer-limited. The lever that would
tighten these CIs is **more answer replicates** (6 ans×1 judge → variance 0.267, ~halved)
or **more questions** — not more judges. `--judge-runs` remains useful as a cheap
robustness check (it confirmed the effect isn't judge-noise), just not as a power lever here.

Caveat: baseline is cross-batch (Trap 1), but the effect (0.9) is ~2.7× the baseline's own
replicate drift (±0.35), so it survives a worst-case baseline shift. Sharpened scored CSVs
kept as `*-scored-5judge.csv`; primary `*-scored.csv` restored to the 1-judge batch so the
group conditions stay validly paired.

## Side findings

* **Exact-answer correctness (secondary metric).** Factoid correctness is low
  (~29% at pilot scale). Re-running all 20 factoid gold queries live found **20/20
  fresh, zero drift** — so those misses are **real agent miscounts** on multi-step
  aggregations, not stale golds. The 4×(1–5) judge smooths these over; the binary
  metric exposes them. `choice` sits at a 100% ceiling (no discrimination).
* **Subscription auth cannot sustain a batch this size.** Answering *and* Opus judging
  on `claude login` degraded into rate-limited empty judge responses and, worse,
  `"Not logged in · Please run /login"` answer stubs that the runner recorded as
  `success=True` — whole conditions of 40/40 login errors scoring 4/20. Fixed by
  `--answer-use-api --judge-use-api`, plus an abort-after-3-consecutive-failed-rows
  guard in `add_llm_evaluation.py` so a throttled judge can never again silently
  score a run all-zeros.
