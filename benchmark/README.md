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
│   ├── add_llm_evaluation.py     # Scores collected answers using an LLM judge
│   ├── results_analyzer.py       # Statistical analysis of evaluation results
│   ├── generate_dashboard.py     # Generates HTML evaluation dashboard
│   ├── verify_questions.py       # Validates question YAML files
│   ├── config.yaml               # Config for "With Guide" condition
│   ├── config_no_guide1.yaml     # Config for NG1 condition
│   ├── config_no_guide2.yaml     # Config for NG2 condition
│   ├── config_no_mie.yaml        # Config for "No MIE" condition
│   ├── CONFIG_FORMAT.md          # Configuration file format documentation
│   └── evaluation_dashboard.html # Pre-generated results dashboard
├── results/
│   ├── with_guide-2026-02-28.csv           # Raw answers, With Guide condition
│   ├── ng1-2026-03-01.csv                  # Raw answers, NG1 condition
│   ├── ng2-2026-03-01.csv                  # Raw answers, NG2 condition
│   ├── no_mie-2026-02-28.csv               # Raw answers, No MIE condition
│   ├── with_guide-2026-02-28-Opus4.6-v{1..5}.csv  # Re-evaluated with Claude Opus 4.6
│   ├── ng1-2026-03-01-Opus4.6-v{1..5}.csv
│   ├── ng2-2026-03-01-Opus4.6-v{1..5}.csv
│   ├── no_mie-2026-02-28-Opus4.6-v{1..5}.csv
│   └── *.md                                # Analysis reports
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

Answers were collected using `scripts/automated_test_runner.py`:

```bash
cd scripts
python automated_test_runner.py ../questions/question_*.yaml \
    -c config.yaml \
    -o ../results/with_guide-2026-02-28.csv
```

The script runs each question in an isolated session (no conversation history) and collects answers from both the baseline agent and the TogoMCP agent. It outputs a CSV with columns for both agents' answers, token counts, and USD cost. The four conditions were run separately using their respective config files.

### Step 4 — LLM Evaluation (initial, llama3.2)

Initial scoring was done with `scripts/add_llm_evaluation.py` using `llama3.2` as the judge:

```bash
python add_llm_evaluation.py ../results/with_guide-2026-02-28.csv \
    --llm-model llama3.2
```

Each answer is scored on four criteria (1–5 each, total 4–20):
- **Recall** — completeness relative to the `ideal_answer`
- **Precision** — relevance of provided information
- **Non-redundancy** (repetition) — avoidance of repeated content
- **Readability** — clarity and fluency

These initial scores (`with_guide-2026-02-28.csv`, `ng1-2026-03-01.csv`, `ng2-2026-03-01.csv`, `no_mie-2026-02-28.csv`) were found to be unreliable and are not used in the paper.

### Step 5 — Re-evaluation with Claude Opus 4.6

Because the llama3.2 scores were insufficiently reliable, all four conditions were re-evaluated five times each using **Claude Opus 4.6** as the judge (250 question–run pairs per condition). These are the results reported in the paper:

| Condition | Result files |
|-----------|-------------|
| With Guide | `with_guide-2026-02-28-Opus4.6-v1.csv` … `v5.csv` |
| NG1 | `ng1-2026-03-01-Opus4.6-v1.csv` … `v5.csv` |
| NG2 | `ng2-2026-03-01-Opus4.6-v1.csv` … `v5.csv` |
| No MIE | `no_mie-2026-02-28-Opus4.6-v1.csv` … `v5.csv` |

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
| `scripts/add_llm_evaluation.py` | LLM-based scoring using Ollama (initial pass) |

---

## Requirements

```bash
pip install anthropic claude-agent-sdk pyyaml pandas ollama
```

An `ANTHROPIC_API_KEY` environment variable must be set. The `automated_test_runner.py` script requires access to the TogoMCP MCP server at `https://togomcp.rdfportal.org/mcp`.
