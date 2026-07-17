# MIE Subcomponent Ablation Harness

Quantifies how much each **MIE section** contributes to TogoMCP benchmark
performance by removing one section at a time from the MIE corpus and measuring
the drop in LLM-judge scores.

An MIE file has **11 top-level sections**; each is ablated leave-one-out
(1 baseline + 11 conditions). The analysis spotlights the **4 spec-named
categories**:

| Spec category | MIE section |
|---|---|
| Schema description (スキーマ記述) | `schema_info` |
| ShEx/shape (ShEx/シェイプ) | `shape_expressions` |
| SPARQL query examples (SPARQL クエリ例) | `sparql_query_examples` |
| Entity/vocab coverage (エンティティ・語彙カバレッジ) | `cross_references` |

> The 4 spotlight categories map 1:1 to 4 distinct sections. All 11 sections are
> ablated leave-one-out and reported individually.

## How it works

MIE content reaches the model **only** through the `get_MIE_file` tool, which
reads the directory named by `TOGOMCP_MIE_DIR` (added to `togo_mcp/server.py`).
So each condition boots a **local** TogoMCP HTTP server pointed at a
section-stripped copy of the corpus, and the existing benchmark runner queries it
exactly as it would query production — only the served MIE differs.

```
ablate_mie.py     → mie_variants/{baseline, ablate_<section>}/  (+ section_presence.csv, manifest.json)
select_pilot.py   → pilot_questions.txt  (DB-spanning subset)
run_ablation.py   → per condition: boot local server (_serve.py) → automated_test_runner.py
                    → add_llm_evaluation.py → results/<condition>-scored.csv
ablation_analysis.py → results/ablation_contributions.csv + ablation_report.md
```

`run_ablation.py` **reuses** `../scripts/automated_test_runner.py` and
`../scripts/add_llm_evaluation.py` unchanged (as subprocesses) and clones
`../scripts/config.yaml`, redirecting only the `togomcp` server URL to the local
server — so the answering prompt/model/other MCP servers stay identical to a
normal run.

## Prerequisites

Two dependency sets, which may live in the same venv:

- **Server** (`_serve.py`): the TogoMCP package — `uv sync` in the repo root.
- **Benchmark** (`automated_test_runner.py`, `add_llm_evaluation.py`):
  `pip install claude-agent-sdk pandas anthropic` (per those scripts' own notes).
- `ablate_mie.py` / `select_pilot.py` / `ablation_analysis.py` need only
  **pyyaml** (already a TogoMCP dependency) — no pandas.

Environment:
```bash
export NCBI_API_KEY=...           # local server's NCBI tools
```

**Auth:** both the **runner** (`automated_test_runner.py`) and the **Claude judge**
(`add_llm_evaluation.py`, which now defaults to the Claude CLI / agent SDK)
authenticate through your `claude login` — do *not* set `ANTHROPIC_API_KEY`, or
the CLI switches to API billing. If your judge is a local Ollama model
(`--judge-model gemma3`), no key is needed either. (To force the judge onto the
Anthropic Messages API instead, run `add_llm_evaluation.py --use-api` yourself
with `ANTHROPIC_API_KEY` set.)

## Run it

```bash
cd benchmark/ablation

# 1. Generate the 11 section-stripped MIE corpora (+ presence matrix).
python ablate_mie.py

# 2. Pick a DB-spanning pilot subset (40 questions covering all 34 DBs).
python select_pilot.py            # or: --full  for all 100

# 3. Validate orchestration without spending API credits (boots each server).
python run_ablation.py --dry-run --conditions baseline,ablate_shape_expressions

# 4. Run the full sweep (baseline + 11 ablations over the pilot subset).
python run_ablation.py --model claude-sonnet-4-5-20250929

# 5. Compute per-section contribution + report.
python ablation_analysis.py
```

Outputs land in `results/`:
- `<condition>-answers.csv` / `<condition>-scored.csv` — per condition.
- `ablation_contributions.csv` — one ranked row per section.
- `ablation_report.md` — ranked table + 4-category spotlight + caveats.

> **Read [FINDINGS.md](FINDINGS.md) before running or interpreting a sweep.** The
> 2026-07 run was a null result (0/11 sections significant), and it records the two
> traps that produced convincing-looking wrong answers first: a banked baseline, and
> an aggregate mistaken for a per-question effect.

## ⚠️ Never bank a baseline across batches

`run_ablation.py` skips a condition whose `<cond>-scored.csv` already exists. That is
what makes a sweep resumable — and it is also the harness's sharpest edge: if the
baseline was produced in an **earlier session**, the sweep silently reuses it and every
contribution is measured against a different batch.

This is not hypothetical. In 2026-07 a baseline banked from a 1-condition trial ran
~0.4/20 low, which made **all 11** contributions negative — "removing any section
helps". All contributions subtract the *same* baseline, so they are not independent:
one low baseline drags them all negative together. Re-running the baseline fresh in the
same batch (16.72 → 17.13) made the pattern vanish, and rebased the effort axis too.

**Rule:** a question's baseline and ablated rows must come from the same batch. If the
baseline predates the ablations, delete it and let it re-run. When extending the set,
run **every** condition for the new questions in one batch.

## Extending n without re-running the sweep

The analysis keys on `question_id` and pairs per question, so more questions can be
folded in later — the ones already swept are not redone (~$0.54/question-run; +25
questions ≈ $490 vs ≈ $1.9k for a 100-question redo):

```bash
python append_results.py --list-existing results        # what's already covered
python run_ablation.py --results-dir results_batch2 \
       --questions <new...> --runs 3 --answer-use-api --judge-use-api   # ALL conditions, one batch
python append_results.py results_batch2 results         # fold in (idempotent, dedups by qid)
python ablation_analysis.py --exclude-ceiling 20 --exclude-floor 12
```

## Notes & knobs

- **Idempotent**: a condition whose `results/<cond>-scored.csv` exists is skipped.
  Delete it (or pass `--force`) to re-run. A partial sweep resumes safely — but see
  the baseline warning above before relying on a *reused* baseline.
- **Use the API, not the subscription, for anything this size**:
  `--answer-use-api --judge-use-api` (needs `ANTHROPIC_API_KEY`). On `claude login` the
  Opus judge gets rate-limited into empty responses and the answering agent degrades
  into `"Not logged in"` stubs that the runner still records as `success=True`.
- **Sequential**: conditions run one at a time on one loopback port (`--port`,
  default 8971); only one local server is alive at a time.
- **Contribution** = `mean(baseline) − mean(section removed)` on
  `togomcp_total_score` (0–20), paired per question. Positive ⇒ the section helps.
  Reported with a **95% CI over the paired per-question deltas**; a contribution only
  means anything when its CI excludes 0 (`*`). Mind the **multiple comparisons**: 11
  sections are tested, so ~0.6 nominal hits are expected by chance and the corrected
  bar is |z| > 2.84 — the report's Verdict section spells this out. And an *aggregate*
  difference is not an effect: removing `sparql_query_examples` shifted total SPARQL
  calls +25%, but paired per question it was +0.87 ± 1.07 (i.e. nothing).
- **Scale up**: `python select_pilot.py --full` then re-run the sweep for all 100
  questions. `--conditions` restricts to a subset of sections.
- **Replicates**: `run_ablation.py --runs R` answers + judges each question R times
  per condition (replicates in `<cond>-scored-vR.csv`) and averages them per
  question into the flat `<cond>-scored.csv`. Averaging divides the judge-jitter
  part of the paired-delta variance by R — the lever that gives a 40-question pilot
  usable power; a single-shot 40-Q sweep only resolves ~2-point section effects
  (see `select_pilot.py` docstring). Cost scales ×R.
- **Cost**: pilot ≈ 12 conditions × 40 questions × R × (1 answer + 1 judge)
  (R=1 by default). Multiply by ~2.5 for the full 100-question set.

## Verified / not verified

Verified locally (no API): the `TOGOMCP_MIE_DIR` hook, the section stripper
(byte-exact removal, comment attribution, all variants valid YAML with 10 keys),
DB-spanning pilot selection, launcher boot + MCP handshake, config rendering, the
`--dry-run` server lifecycle, and the analyzer (on synthetic scores). The live
`automated_test_runner` / `add_llm_evaluation` subprocess calls require the
benchmark env + API keys and are run by the user (step 4).
