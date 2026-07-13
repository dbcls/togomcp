# Condition Ablation Harness (paper reproduction)

Repeatable runner for the paper's **non-MIE** ablation conditions — the ones that
toggle whole components (usage guide, MIE access) via config files, as opposed to
the MIE-subcomponent study in [`../ablation/`](../ablation/). Runs against the
**production** TogoMCP server (the configs already point there) and supports
**multiple judge models** per run.

## Conditions

| Condition | Config | What it removes vs `with_guide` |
|---|---|---|
| `with_guide` | `../scripts/config.yaml` | — (full system: usage-guide tool + MIE + guided prompt) |
| `MIE-instr` | `../scripts/config_no_guide1.yaml` | usage-guide tool; MIE workflow instructions still in the prompt |
| `No-Guide` | `../scripts/config_no_guide2.yaml` | usage-guide tool + workflow instructions (minimal prompt) |
| `no_mie` | `../scripts/config_no_mie.yaml` | the whole MIE (`get_MIE_file` blocked) |

(`MIE-instr` and `No-Guide` are the paper's names for the former `ng1`/`ng2`.)

Each condition: collect answers (`../scripts/automated_test_runner.py`) → judge
with each requested model (`../scripts/add_llm_evaluation.py`, once per judge).
Both scripts are reused unchanged.

## Prerequisites

One interpreter with the benchmark deps — the repo `.venv` after:
```bash
uv sync --extra dev            # installs claude-agent-sdk, pandas, anthropic, ollama
```
Pass that interpreter with `--python` (your shell's `python` need not be it).

**Auth:** both the runner and the **Claude judge** (`add_llm_evaluation.py` now
defaults to the Claude CLI / agent SDK) authenticate via your `claude login` — do
**not** export `ANTHROPIC_API_KEY` (it would switch the CLI to API billing).
**Ollama judges** (non-`claude-*` model names, e.g. `gemma4`) need a running
Ollama host (`--ollama-host`, else `$OLLAMA_HOST`/localhost) and no key. (For an
API-billed Claude judge, run `add_llm_evaluation.py --use-api` directly with
`ANTHROPIC_API_KEY` set.)

## Run it

```bash
cd benchmark/conditions
VENV=/Users/arkinjo/work/GitHub/togomcp/.venv/bin/python

# Full sweep, one Opus judge (all questions — 100 today):
python run_conditions.py --python "$VENV" --model claude-sonnet-5

# Multiple judges (Opus + a local Gemma), compared side by side:
python run_conditions.py --python "$VENV" --model claude-sonnet-5 \
    --judges claude-opus-4-8,gemma4

# Judge variance: 3 passes per judge (writes -v1..-v3 per condition/judge):
python run_conditions.py --python "$VENV" --judges claude-opus-4-8 --runs 3

# Compare across conditions and judges (name the run you want to analyze):
python conditions_analysis.py --date $(date +%F) --model claude-sonnet-5
```

## Output layout

Runs are organized on disk by **date** then **answering model**, so many runs over
time stay browsable and never collide (the answering model is part of the path, not
just the judge):

```
results/
└─ <date>/
   └─ <answering-model>/          e.g. 2026-07-09/claude-sonnet-5/
      ├─ <cond>-answers.csv               collected answers per condition
      ├─ <cond>-<judge>[-vN].csv          scored per judge (join on question_id)
      ├─ manifest.json                    what was produced (drives the analyzer)
      ├─ summary.csv                      condition × judge means + Δ vs with_guide
      └─ report.md                        readable comparison + component deltas
```

`conditions_analysis.py` writes `summary.csv` / `report.md` back into that same run
folder. With no `--date`/`--model` it analyzes the newest run; give `--date` (and
`--model` if a date has several) to pick a specific one.

## Notes

- **Idempotent**: an existing answers CSV skips collection; existing scored CSVs
  skip that judge. Delete files or pass `--force` to redo. Safe to resume.
- **Accumulating manifest**: conditions run in *separate* invocations against the
  same `<date>/<model>` folder are merged into one `manifest.json`, so a default
  `with_guide`-only run and a later `--conditions no_mie` run against the same
  date+model stay Δ-comparable in a single analysis (re-running a condition overlays
  it). A different `--date` or `--model` is a separate run folder, not comparable.
- **Multi-judge**: pass any mix of `claude-*` and Ollama model names to `--judges`;
  provider is inferred per model. Each judge produces its own scored CSV, and the
  report shows them side by side so you can gauge judge agreement.
- **Production server**: absolute scores depend on the live server's state at run
  time; the *relative* Δ between conditions is the reproducible signal.
- The `no_mie` block relies on a **deny** rule (`disallowed_tools`) naming
  `mcp__togomcp__get_MIE_file`. Verify no leak after a run:
  ```bash
  python3 -c "import csv;r=list(csv.DictReader(open('results/<DATE>/<MODEL>/no_mie-answers.csv')));print('LEAK' if any('get_MIE_file' in x['tools_used'] for x in r) else 'clean')"
  ```
- This is a multi-hour sequential run (all questions — 100 today — × conditions × judges).
  Run under `tmux`/`nohup`; resume via re-run.
