# TogoMCP Benchmark

This directory contains the evaluation benchmark for the paper:

> **TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol**

The benchmark consists of 50 biologically grounded questions spanning five question types and 23 RDF Portal databases, designed to evaluate TogoMCP's ability to answer biological questions that require live access to RDF knowledge graphs.

---

## Directory Structure

```
benchmark/
├── README.md                     # This file
├── QA_CREATION_GUIDE.md          # Protocol for creating benchmark questions (v5.5.0)
├── QUESTION_FORMAT.md            # YAML format specification for question files
├── togomcp_qa_prompt.md          # QA review prompt + review status tracker
├── keywords.tsv                  # Keyword pool used for question inspiration
├── questions/
│   ├── coverage_tracker.yaml     # Tracks question type and database coverage
│   ├── question_001.yaml         # Individual question files
│   ├── question_002.yaml
│   └── ... (question_001–question_050.yaml)
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
├── results/
│   ├── with_guide-2026-05-04.csv               # Raw answers, With Guide (current)
│   ├── ng1-2026-05-04.csv                      # Raw answers, NG1
│   ├── ng2-2026-05-04.csv                      # Raw answers, NG2
│   ├── no_mie-2026-05-04.csv                   # Raw answers, No MIE
│   ├── *-2026-05-04-Opus4.7-v{1..5}.csv        # Re-evaluated with Claude Opus 4.7 (× 5)
│   ├── togomcp_analysis_v3.md                  # Current analysis (2026-05-04 batch)
│   ├── togomcp_*_analysis.md                   # Per-comparison reports (current batch)
│   ├── reevaluation.md                         # Re-evaluation design notes
│   └── rev0/                                   # Prior batch (Feb–Mar 2026, Opus 4.6 judge)
└── examples/                     # Example dialogue logs
```

---

## Benchmark Design

### Question Set

The 50 questions were created following a strict type-first protocol (`QA_CREATION_GUIDE.md`), with **10 questions per type**:

| Type | Description |
|------|-------------|
| `yes_no` | Binary existence check against the RDF graph |
| `factoid` | Single retrievable value (count or attribute lookup) |
| `list` | Enumeration of entities satisfying a set of constraints |
| `summary` | Multi-dimensional aggregation across 3+ databases, answered as a single paragraph |
| `choice` | Categorical comparison requiring the agent to enumerate and count |

**Database coverage targets** (enforced during creation):
- Multi-database questions (2+ databases): ≥ 60%
- Multi-database questions (3+ databases): ≥ 20%
- UniProt usage cap: ≤ 70%
- All 23 RDF Portal databases covered at least once

Questions were validated to exclude answers recoverable from pre-training data or the published literature (PubMed test), ensuring that RDF database access is necessary to answer them correctly.

### Evaluation Conditions

Four experimental conditions were evaluated (see paper §Ablation Study):

| Condition | Config file | Description |
|-----------|-------------|-------------|
| **With Guide** | `config.yaml` | Full TogoMCP system with Usage Guide |
| **NG1** | `config_no_guide1.yaml` | No Usage Guide, but with an explicit instruction to call `list_databases` and `get_MIE_file` before querying |
| **NG2** | `config_no_guide2.yaml` | No Usage Guide, no MIE instruction |
| **No MIE** | `config_no_mie.yaml` | `get_MIE_file` tool excluded entirely |

Each condition was compared against a **baseline** agent (Claude Sonnet 4.5, no tools) run in the same session.

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

After creation, every question was reviewed against the checklist in `togomcp_qa_prompt.md`. Questions were corrected iteratively until all 50 passed (status `P` in the progress tracker at the bottom of that file). The 25 error categories checked include: coverage gaps, missing arithmetic verification, circular logic, vocabulary sampling, and format errors.

### Step 3 — Answer Collection

Answers were collected using `scripts/automated_test_runner.py`. To run all four conditions sequentially for a given date, use `scripts/run_all_conditions.sh`:

```bash
cd scripts
./run_all_conditions.sh 2026-05-04        # all four conditions
# — or per-condition —
python automated_test_runner.py ../questions/question_*.yaml \
    -c config.yaml \
    -o ../results/with_guide-2026-05-04.csv
```

The script runs each question in an isolated session (no conversation history) and collects answers from both the baseline agent and the TogoMCP agent. It outputs a CSV with columns for both agents' answers, token counts, and USD cost. The four conditions were run separately using their respective config files.

### Step 4 — LLM Evaluation (initial, llama3.2)

> **Note (provenance vs. current tooling):** for the paper, initial scoring used `scripts/add_llm_evaluation.py` with a local `llama3.2` model (Ollama), and those scores were then superseded by a manual Claude Opus re-evaluation on the platform (Step 5). The script has **since been rewritten** to call Claude Opus directly via the Claude API, which collapses Steps 4–5 into one command — see Step 5 for current usage. The `llama3.2` / Ollama path described here is historical.

Initial scoring was originally done with a local `llama3.2` judge, scoring each answer on four criteria (1–5 each, total 4–20):
- **Recall** — completeness relative to the `ideal_answer`
- **Precision** — relevance of provided information
- **Non-redundancy** (repetition) — avoidance of repeated content
- **Readability** — clarity and fluency

These initial scores (`with_guide-2026-05-04.csv`, `ng1-2026-05-04.csv`, `ng2-2026-05-04.csv`, `no_mie-2026-05-04.csv`) were found to be insufficiently reliable for the paper and were superseded by the Claude-judged re-evaluation in Step 5.

### Step 5 — Re-evaluation with Claude Opus

Because the llama3.2 scores were insufficiently reliable, all four conditions were re-evaluated five times each using **Claude Opus** as the judge (250 question–run pairs per condition). The current canonical re-evaluation is the 2026-05-04 batch judged by **Opus 4.7**; the earlier 2026-02–03 batch (judged by Opus 4.6) is preserved under `results/rev0/`.

The paper's Opus re-evaluation was performed manually on the platform (see `results/reevaluation.md`). That process is now automated — `add_llm_evaluation.py` calls Claude Opus through the Claude API with the same four-criteria rubric and forced tool use, producing the same 12 score columns. To reproduce the five-run batch for one condition:

```bash
export ANTHROPIC_API_KEY=sk-ant-...          # required by the anthropic SDK
python add_llm_evaluation.py ../results/with_guide-2026-05-04.csv \
    -o ../results/with_guide-2026-05-04-Opus.csv \
    --model claude-opus-4-8 --runs 5         # writes ...-Opus-v1.csv … -v5.csv
```

Use `--model claude-opus-4-7` to match the model used for the paper's canonical batch.

**Current batch — 2026-05-04, judge: Opus 4.7** (results reported in the paper)

| Condition | Result files |
|-----------|-------------|
| With Guide | `with_guide-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |
| NG1 | `ng1-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |
| NG2 | `ng2-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |
| No MIE | `no_mie-2026-05-04-Opus4.7-v1.csv` … `v5.csv` |

**Prior batch — 2026-02/03, judge: Opus 4.6** (archived under `results/rev0/`)

| Condition | Result files |
|-----------|-------------|
| With Guide | `rev0/with_guide-2026-02-28-Opus4.6-v1.csv` … `v5.csv` |
| NG1 | `rev0/ng1-2026-03-01-Opus4.6-v1.csv` … `v5.csv` |
| NG2 | `rev0/ng2-2026-03-01-Opus4.6-v1.csv` … `v5.csv` |
| No MIE | `rev0/no_mie-2026-02-28-Opus4.6-v1.csv` … `v5.csv` |

Design notes for the re-evaluation methodology are in `results/reevaluation.md`.

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
| `togomcp_qa_prompt.md` | QA review prompt (25 error categories) and per-question review status tracker |
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
