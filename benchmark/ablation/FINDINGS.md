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

1. **Group ablation** — remove a whole group (e.g. all query-guidance sections at
   once) so redundancy can't compensate. Bigger effects, same cost.
2. **The full 100-question set** — n≈88 would resolve a `common_errors`-sized effect
   even after multiple-comparison correction. `append_results.py` extends n without
   re-running what's already done.

A sharper *effort* signal would also help: `tools_used` records tool **names** only,
so we can count queries but not their **outcomes**. Logging each `run_sparql` result
(syntax error / empty / rows) in `automated_test_runner.py` would give failed-query
rate and first-query success rate — far more sensitive than raw call counts, and it
would directly test whether the query-guidance sections do what they claim.

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
