# TogoMCP Benchmark

This directory contains the evaluation benchmark for the paper:

> Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). **TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol**. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

The benchmark now contains 100 biologically grounded questions (20 per type) spanning 34 RDF Portal databases, designed to evaluate TogoMCP's ability to answer biological questions that require live access to RDF knowledge graphs.

> **Scope of the paper's results.** The exact questions **and** results reported in the paper are the frozen snapshot on the **[`paper2026rev1`](https://github.com/dbcls/togomcp/tree/paper2026rev1)** branch (a carried-forward copy of the results lives under **[`results-Kinjo2026/`](results-Kinjo2026/)** — see its README). The paper evaluated **50 questions** (the `question_001`–`question_050` slot, balanced 10 per type); the later 50 (`question_051`–`question_100`) were added afterward and are not part of it.
>
> **The live question set is maintained.** Any question — including 001–050 — may be **revised over time** (databases change, answers drift, errors surface), so the current `questions/` files are *not* a frozen record and may differ from what the paper ran. For the exact as-evaluated questions, use `paper2026rev1`. Below, "100 questions" means the current set.

(The TogoMCP catalog has since grown to 36 databases; the two most recent — `supercon` and `ontology` — are not exercised by the question set.)

---

## Directory Structure

```
benchmark/
├── README.md                     # This file
├── QA_CREATION_GUIDE.md          # Protocol for creating benchmark questions (v5.5.0)
├── QUESTION_FORMAT.md            # YAML format specification for question files
├── keywords.tsv                  # Keyword pool used for question inspiration
├── questions/
│   ├── coverage_tracker.yaml     # Tracks question type and database coverage
│   ├── question_001.yaml         # Individual question files
│   ├── question_002.yaml
│   └── ... (question_001–question_100.yaml)
├── scripts/
│   ├── automated_test_runner.py  # Collects answers from baseline and TogoMCP agents
│   ├── add_llm_evaluation.py     # Scores collected answers using Claude Opus as judge
│   ├── results_analyzer.py       # Statistical analysis of evaluation results
│   ├── generate_dashboard.py     # Generates HTML evaluation dashboard
│   ├── verify_questions.py       # Validates question YAML files
│   ├── run_all_conditions.sh     # Runs all four conditions sequentially for a date
│   ├── config.yaml               # Config for "With Guide" condition
│   ├── config_no_guide1.yaml     # Config for NG1 condition
│   ├── config_no_guide2.yaml     # Config for NG2 condition
│   ├── config_no_guide2_no_test_server.yaml  # NG2 variant pinned to production MCP endpoint
│   ├── config_no_mie.yaml        # Config for "No MIE" condition
│   ├── CONFIG_FORMAT.md          # Configuration file format documentation
│   └── evaluation_dashboard.html # Pre-generated results dashboard
├── results-Kinjo2026/            # FROZEN paper-evaluation archive (its own README)
│   ├── README.md                 # Scope (50 Q), conditions, judge batches, file scheme, rubric
│   ├── *-2026-05-04.csv          # Raw answers, 4 conditions (canonical batch)
│   ├── *-2026-05-04-Opus4.7-v{1..5}.csv   # Scored × 5 (Opus 4.7 judge)
│   ├── togomcp_*_analysis*.md     # Analysis + per-comparison reports
│   ├── reevaluation.md           # Re-evaluation design notes
│   └── rev0/                     # Prior batch (Feb–Mar 2026; judged Opus 4.6 + 4.7)
├── results/                      # (created on demand) scratch output for NEW / reproduction runs
└── studies/                      # Investigations run *with* the benchmark (not the benchmark itself)
    ├── ablation/                 # MIE-subcomponent leave-one-out / leave-one-in ablation harness (+ FINDINGS)
    ├── conditions/               # Condition ablation harness (usage-guide / MIE), multi-judge
    ├── redesign/                 # The MIE v3 redesign investigation (mie_v3 staging, release/smoke gates, FINDINGS)
    └── examples/                 # Example dialogue logs (skill demos)
```

The top level is **the benchmark** — questions, the collection/eval scripts, and the creation protocol. The other three are clearly separated:
- **`results-Kinjo2026/`** — the paper's frozen, citable evaluation (50 questions). See its own README; do not overwrite it.
- **`results/`** — scratch; where new or reproduction runs land (`run_all_conditions.sh` recreates it). Not the paper's numbers.
- **`studies/`** — larger investigations built *on* the benchmark, each with its own README; they reach up to `../../questions` and `../../scripts`.

---

## Benchmark Design

### Question Set

The set was built in two tranches: the **first 50** (`question_001`–`question_050`, 10 per type) covered the paper's evaluation slot; a **second 50** were added afterward, bringing the current total to **100 questions, 20 per type**. Both tranches followed the same strict type-first protocol (`QA_CREATION_GUIDE.md`). This is a **living set** — questions are revised as databases evolve or errors are found, so a given `question_NNN.yaml` may differ from its paper-time version (frozen on `paper2026rev1`). The type definitions:

| Type | Description |
|------|-------------|
| `yes_no` | Binary existence check against the RDF graph |
| `factoid` | Single retrievable value (count or attribute lookup) |
| `list` | Enumeration of entities satisfying a set of constraints |
| `summary` | Multi-dimensional aggregation across 3+ databases, answered as a single paragraph |
| `choice` | Categorical comparison requiring the agent to enumerate and count |

**Database coverage targets** (enforced during creation; figures below describe the full 100-question set):
- Multi-database questions (2+ databases): ≥ 60%
- Multi-database questions (3+ databases): ≥ 20%
- UniProt usage cap: ≤ 70%
- All 34 RDF Portal databases (the TogoMCP catalog at the time the set was frozen) covered at least once

Questions were validated to exclude answers recoverable from pre-training data or the published literature (PubMed test), ensuring that RDF database access is necessary to answer them correctly.

### Evaluation Conditions

Four experimental conditions were evaluated (see paper §Ablation Study):

| Condition | Config file | Description |
|-----------|-------------|-------------|
| **With Guide** | `config.yaml` | Full TogoMCP system with Usage Guide |
| **NG1** | `config_no_guide1.yaml` | No Usage Guide, but with an explicit instruction to call `list_databases` and `get_MIE_file` before querying |
| **NG2** | `config_no_guide2.yaml` | No Usage Guide, no MIE instruction |
| **No MIE** | `config_no_mie.yaml` | `get_MIE_file` tool excluded entirely |

Each condition was compared against a **baseline** agent (Claude Sonnet 4.5, no tools) run in the same session. The judge, five-run protocol, batch filenames, and the retirement of NG1's `list_databases` tool are documented in [`results-Kinjo2026/README.md`](results-Kinjo2026/README.md).

---

## Workflow

### Step 1 — Question Creation

Questions were created one-by-one following the protocol in `QA_CREATION_GUIDE.md` (v5.5.0). The mandatory workflow enforces:

1. **Type-first selection** — choose the under-represented question type before selecting databases or keywords.
2. **Structured vocabulary discovery** — check GO, MONDO, ChEBI, MeSH, EC etc. via OLS4 before resorting to text search.
3. **Arithmetic verification** — for any `GROUP BY` query, verify that the sum of category counts equals the total unique entity count.
4. **PubMed test** — confirm that the question cannot be answered from literature alone.

Each question is stored as a YAML file in `questions/` following the format in `QUESTION_FORMAT.md`.

### Step 2 — QA Review

After creation, every question is reviewed against the checklist in `.claude/skills/qa-generator/references/qa-checklist.md` (C01–C27), and corrected iteratively until it passes — a question only enters `questions/` once it has cleared that review. The error categories checked include: coverage gaps, missing arithmetic verification, circular logic, vocabulary sampling, cross-graph count inflation, and format errors.

### Step 3 — Running an evaluation

Collect answers, then score them. New runs land in a fresh `results/` — the paper's frozen archive under `results-Kinjo2026/` is never touched.

```bash
cd scripts
# 1. collect answers for all four conditions on a given date -> ../results/<cond>-<DATE>.csv
./run_all_conditions.sh 2026-07-25
#    (or one condition: automated_test_runner.py ../questions/question_*.yaml -c config.yaml -o ../results/with_guide-<DATE>.csv)

# 2. score with a Claude Opus judge, 5 runs -> ...-Opus-v1.csv … -v5.csv
export ANTHROPIC_API_KEY=sk-ant-...
python add_llm_evaluation.py ../results/with_guide-<DATE>.csv \
    -o ../results/with_guide-<DATE>-Opus.csv --model claude-opus-4-8 --runs 5
```

The runner executes each question in an isolated session (no history) and records both agents' answers, token counts, and cost. The judge scores each answer 1–5 on four criteria (recall, precision, non-redundancy, readability; total 4–20) with forced tool use, producing 12 score columns.

The `question_*.yaml` glob matches all **100** questions; to match the paper's 50-question scope use `../questions/question_0[0-4]*.yaml ../questions/question_050.yaml`.

## Results

- **The paper's results** — the authoritative frozen snapshot is the **[`paper2026rev1`](https://github.com/dbcls/togomcp/tree/paper2026rev1)** branch; a carried-forward copy lives under **[`results-Kinjo2026/`](results-Kinjo2026/)** with its own README (50-question scope, conditions, the Opus 4.7 canonical batch + the `rev0/` prior batch, file scheme, rubric). Cite/compare against these; don't overwrite them.
- **New runs** — land in `results/` (created on demand), analyzed with `scripts/results_analyzer.py` / `scripts/generate_dashboard.py`.
- **Investigations** built on the benchmark (MIE ablations, the v3 redesign) — under `studies/`, each with its own README.

---

## Configuration

Each config file (YAML) specifies:
- `model` — the agent model (Claude Sonnet 4.5)
- `baseline_system_prompt` / `togomcp_system_prompt` — system prompts
- `mcp_servers` — MCP server URLs (TogoMCP, and optionally PubMed, OLS4, PubDictionaries)
- `allowed_tools` / `disallowed_tools` — tool access control (web search is always denied)
- `pricing` — token pricing for cost tracking

See `scripts/CONFIG_FORMAT.md` for the full specification and YAML formatting guidance.

---

## Key Files

| File | Purpose |
|------|---------|
| `QA_CREATION_GUIDE.md` | Detailed protocol (v5.5.0) for creating benchmark questions, including coverage gap detection, arithmetic verification, and type-first workflow |
| `QUESTION_FORMAT.md` | YAML schema for question files, including field types, constraints, and complete examples |
| `questions/coverage_tracker.yaml` | Running tally of question type and database usage during creation |
| `scripts/automated_test_runner.py` | Answer collection script using `claude-agent-sdk` |
| `scripts/run_all_conditions.sh` | Sequential orchestrator that runs all four conditions for a given date and skips existing outputs |
| `scripts/add_llm_evaluation.py` | Answer scoring with Claude Opus as judge, via the Claude API (forced tool use) |

---

## Requirements

```bash
pip install 'claude-agent-sdk>=0.1.70' anthropic pyyaml pandas
```

Both the baseline and TogoMCP conditions now run through the `claude-agent-sdk` (Claude Code CLI), so authentication for `automated_test_runner.py` comes from the CLI: an `ANTHROPIC_API_KEY` environment variable if set, otherwise the CLI's stored login (`claude login` — OAuth/keychain). Setting `ANTHROPIC_API_KEY` is therefore optional but recommended for reproducible, uniformly-billed runs (it forces both conditions onto the same API-billed credential). The `automated_test_runner.py` script requires access to the TogoMCP MCP server at `https://togomcp.rdfportal.org/mcp` (or the staging endpoint at `https://test-togomcp.rdfportal.org/mcp`).

`add_llm_evaluation.py` (the Opus judge) uses the plain `anthropic` SDK instead, which **requires** `ANTHROPIC_API_KEY` (or `ANTHROPIC_AUTH_TOKEN` / an `ant auth login` profile) — it does not read the `claude login` keychain. `ollama` is no longer required: the judge now calls the Claude API directly.

> The baseline previously used the standalone `anthropic` SDK with an explicit `temperature`/`max_tokens`; it now uses the agent SDK like the TogoMCP path so both conditions share identical (CLI-fixed) sampling and differ only in tool availability. The `anthropic` package is no longer required.

> **Pin `claude-agent-sdk>=0.1.70`.** Older versions ship a stale bundled `claude` CLI that silently returns empty responses against the current Anthropic API — the test runner records these as failures with the marker `"Empty response from claude-agent-sdk (no ResultMessage text)"`. If you see that error pattern at high frequency, upgrade with `pip install -U claude-agent-sdk` and verify with `echo "What is 2+2?" | <site-packages>/claude_agent_sdk/_bundled/claude --print`.

### Operational notes

The runner has a few knobs in each `config*.yaml` worth knowing about for long sweeps:

- `retry_attempts` / `retry_delay` / `max_retry_delay` — exponential-backoff retry for transient MCP failures (default 3 attempts, 2-30s backoff). The runner now retries on three conditions: timeouts, exceptions, **and** empty responses from the agent SDK.
- `inter_question_delay` — seconds to sleep between questions (default 0). Set to 30-90s if you hit clustered failures suggesting throttling at the togomcp MCP server or its upstream SPARQL endpoint.
- `togomcp_time` records only the latency of the call that produced the recorded answer (excludes time spent on preceding failed retry attempts and inter-attempt sleeps), so it stays comparable to `baseline_time`.
- `tools_used` records only `mcp__*` tools — built-in agent tools (Read, Bash, ToolSearch, etc.) are filtered out so per-question tool-use counts are apples-to-apples with prior runs.
