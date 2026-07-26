# Paper evaluation — frozen results

The evaluation results **as reported in the paper**:

> Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). **TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol**. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

> 📌 **Authoritative source: the [`paper2026rev1`](https://github.com/dbcls/togomcp/tree/paper2026rev1) branch.** The *exact* results behind the paper are the frozen snapshot on that branch (under `benchmark/results/`). This directory is that snapshot carried forward onto the main line for convenience — if the two ever diverge, **`paper2026rev1` is authoritative**. Cite/compare against the branch.

> ⚠️ **This directory is frozen.** These CSVs and analysis notes are the citable record behind the paper's figures — do not overwrite or regenerate them in place. New or reproduction runs land in a fresh `../results/` (created on demand by `../scripts/run_all_conditions.sh`); compare against this archive, don't replace it.

## Scope

- **50 questions** — the `question_001`–`question_050` slot (balanced **10 per type**: yes_no, factoid, list, summary, choice). The benchmark has since grown to 100 questions; the later 50 postdate the paper and are **not** evaluated here. The live `../questions/` is a **maintained** set — any question may be revised over time, so those files may differ from what was evaluated; the exact as-evaluated questions are frozen alongside these results on [`paper2026rev1`](https://github.com/dbcls/togomcp/tree/paper2026rev1).
- **Four conditions**, each compared against a **baseline** (Claude Sonnet 4.5, no tools) in the same session. The agent model is Claude Sonnet 4.5 throughout; conditions differ only in tool/prompt availability:

  | Condition | Config (`../scripts/`) | What it gives the agent |
  |-----------|------------------------|-------------------------|
  | **With Guide** | `config.yaml` | Full TogoMCP system + Usage Guide |
  | **NG1** | `config_no_guide1.yaml` | No Usage Guide; explicit instruction to call `list_databases` + `get_MIE_file` first † |
  | **NG2** | `config_no_guide2.yaml` | No Usage Guide, no MIE instruction |
  | **No MIE** | `config_no_mie.yaml` | `get_MIE_file` excluded entirely |

  † `list_databases` has since been retired (its catalog moved into the generated Usage Guide); the config is preserved as-run — re-running NG1 today, that instruction no-ops.

## Judge & rubric

Answers were scored by a **Claude Opus** judge (forced tool use), **5 runs per condition** (50 questions × 5 = **250 question–run pairs** per condition), on four criteria (1–5 each, total **4–20**):

- **Recall** — completeness relative to the `ideal_answer`
- **Precision** — relevance of the information provided
- **Non-redundancy** — avoidance of repeated content
- **Readability** — clarity and fluency

The paper's Opus re-evaluation was performed manually on the platform (see `reevaluation.md`); `../scripts/add_llm_evaluation.py` now reproduces it via the Claude API with the same rubric and 12 score columns. An earlier `llama3.2` (Ollama) judge pass was found insufficiently reliable and superseded — that path is historical.

## Batches

**Canonical — answers `2026-05-04`, judge Opus 4.7** (the numbers in the paper):

| Condition | Raw answers | Scored (× 5) |
|-----------|-------------|--------------|
| With Guide | `with_guide-2026-05-04.csv` | `with_guide-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |
| NG1 | `ng1-2026-05-04.csv` | `ng1-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |
| NG2 | `ng2-2026-05-04.csv` | `ng2-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |
| No MIE | `no_mie-2026-05-04.csv` | `no_mie-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |

**Prior batch — `rev0/`** (answers `2026-02-28`/`2026-03-01`), kept for provenance. Judged by **both Opus 4.6 and Opus 4.7** (× 5 each), e.g. `rev0/with_guide-2026-02-28-Opus4.6-v1.csv` and `rev0/…-Opus4.7-v1.csv`.

## Analysis notes

- `reevaluation.md` — design of the Opus re-evaluation (why llama3.2 was dropped; the 5-run protocol).
- `togomcp_analysis_v3.md` — the current-batch analysis (v2 lives under `rev0/`).
- `togomcp_four_condition_comparison.md`, `togomcp_no_guide_analysis.md`, `togomcp_no_mie_analysis.md`, `togomcp_wg_vs_ng1_detailed.md` — per-comparison reports.

## Reproducing (into a fresh dir, not here)

```bash
cd ../scripts
# collect answers for the paper's 50-question scope (writes to ../results/, NOT this archive)
python automated_test_runner.py ../questions/question_0[0-4]*.yaml ../questions/question_050.yaml \
    -c config.yaml -o ../results/with_guide-$(date +%F).csv
# then judge 5× with Opus (use --model claude-opus-4-7 to match the paper's canonical batch)
python add_llm_evaluation.py ../results/with_guide-<DATE>.csv \
    -o ../results/with_guide-<DATE>-Opus.csv --model claude-opus-4-7 --runs 5
```

See `../README.md` for the full tooling, requirements, and config reference.
