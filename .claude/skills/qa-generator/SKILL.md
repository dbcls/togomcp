---
name: qa-generator
description: Generate new benchmark questions for the TogoMCP evaluation set (benchmark/questions/question_XXX.yaml). Use this skill whenever the user asks to create, write, add, or extend benchmark questions / the QA set / the evaluation dataset for TogoMCP — e.g. "add a few benchmark questions", "extend the QA set", "we need more list-type questions", "write a new question about <topic/database>", "grow the benchmark past 50", or anything mentioning benchmark/questions, coverage_tracker.yaml, the QA creation guide, or question YAML files. Each question is produced end-to-end against live RDF databases (SPARQL, OLS4, PubMed) following the v5.5.0 type-first protocol, then presented for approval before it is written.
---

# TogoMCP Benchmark QA Generator

This skill produces new, fully-validated benchmark questions one at a time, enforcing the type-first creation protocol and the 25-category QA review that the existing 50 questions passed. A question is only useful if it **requires live RDF access to answer** and is **arithmetically self-consistent**; this skill exists to guarantee both, not just to emit plausible-looking YAML.

It runs in a Claude Code environment with the **TogoMCP MCP server** (SPARQL + REST wrappers + TogoID), **OLS4** (ontology lookup), and **PubMed/NCBI** tools connected, plus filesystem access. Use those tools freely — that is the normal mode here. **Either TogoMCP server works** — they expose the identical tool surface, differing only in the tool prefix (`mcp__togomcp-dev__*` vs `mcp__togomcp__*`). Prefer the local `togomcp-dev` when present because its registry is fresher (it picks up new `endpoints.csv` rows immediately); the remote `togomcp` is a fine fallback for the established databases, with the one caveat that its registry can lag, so a *recently added* database may not be available there yet. OLS4 and PubMed are separate servers, unaffected by which TogoMCP you use.

## The Three Hard Rules

**1. Nothing is invented.** Every SPARQL query in `sparql_queries` must execute successfully against the real endpoint before it is written. Every `result_count`, every triple in `rdf_triples`, and every fact in `ideal_answer` must come from an actual query result you ran this session. A fabricated count or triple is worse than a missing one — it silently poisons the benchmark.

**2. Question scope = query scope (no sampling).** If exploration discovers N ontology terms (GO/MONDO/ChEBI/EC/MeSH), the SPARQL `VALUES` clause must use **all N**, including all `getDescendants()`. A "which/how many/list all" question must query the entire set, never a subset. This is the single most common way a question silently becomes wrong — see [references/coverage-gaps.md](references/coverage-gaps.md).

**3. Every `GROUP BY` gets an arithmetic-verification query.** Run a separate `COUNT(DISTINCT ?entity)` over the same criteria and confirm `sum of category counts == total`. If `sum < total` → a coverage gap exists, STOP and fix it. If `sum > total` → the overlap must be explained in `ideal_answer`.

## Workflow — one question, then checkpoint

Generate **one** question through all phases, then **stop and present it for the user's approval** (the YAML + the `verify_questions.py` result + your C01–C26 self-review). Only after approval do you write the file and update the tracker. For a "generate N" request, loop this — pause on each. Never batch-write.

### Phase 0 — Pick the type (type-first; non-negotiable)
Read `benchmark/questions/coverage_tracker.yaml`. Choose the **most under-represented** `type` (target ≈ total/5 per type; the five types are `yes_no`, `factoid`, `list`, `summary`, `choice`). If the user named a type/topic/database, honor it but still record the coverage rationale. Type is chosen **before** databases and keywords — not fitted to a keyword afterward.

> **Shortcut:** `python benchmark/scripts/verify_questions.py` (full run, no args) prints a **Next-Question Guidance** block that does Phase 0–1's bookkeeping for you — the per-type shortfall to the next balanced milestone, the most under-used databases to prefer, and how much UniProt headroom remains under the 70% cap. Use it to make the type/database picks unambiguous rather than eyeballing the tracker.

### Phase 1 — Pick databases (type-compatible, under-used)
The valid database set is the live registry — `togo_mcp/data/resources/endpoints.csv` (= what `list_databases()` returns); `verify_questions.py` derives its accepted set from that same file, so any current database is fair game and **newly added databases are not only allowed but are the highest-priority coverage targets** (they appear at count 0 in the Next-Question Guidance). Prefer under-used databases (the guidance lists them; the tracker's `databases` counts are a secondary view that may lag for just-added ones). Call `list_databases()`, then pick **2–3** with complementary domains and a real cross-reference path (e.g. UniProt→PDB, ChEMBL→ChEBI), compatible with the type (`summary` needs ≥3). Call `get_MIE_file()` for each chosen database before writing any SPARQL. Avoid pushing UniProt past 70% of the set.

### Phase 2 — Pick a keyword
Read `benchmark/keywords.tsv` (columns: `Keyword ID`, `Name`, `Category`). Filter by the type and the chosen databases, drop any already in the tracker's `keywords_used`, and pick **randomly** from what remains (do not browse for an appealing topic — that inverts the workflow). Avoid famous entities (BRCA1, TP53, insulin, aspirin, glycolysis, E. coli K-12, …).

### Phase 3 — Structured vocabulary discovery
Before any SPARQL, resolve every concept to a structured identifier via the hierarchy in [references/vocabulary-discovery.md](references/vocabulary-discovery.md): ontology IRIs (OLS4 `searchClasses` for GO/MONDO/ChEBI/UBERON; `search_mesh_descriptor`; EC via Rhea) **before** any text search. For every ontology term found, call `OLS4:getDescendants()` and record the full term set. Free-text `bif:contains` is a last resort and must be justified in the file.

### Phase 4 — Explore & formulate SPARQL (live)
Run real queries via `run_sparql` (and `search_*`/`ncbi_*` wrappers) to find the answer. **No blind retry loops** — if a query fails twice, diagnose (wrong predicate/graph/IRI) before retrying; consult the MIE file. Keep `VALUES` exhaustive (Rule 2).

### Phase 5 — Arithmetic verification
For every `GROUP BY`, run the verification query (Rule 3) and record the check.

### Phase 6 — Necessity gates (both must pass)
- **Training test:** the answer must depend on *current* database state, not recallable from memory.
- **PubMed test:** actually try to *answer* the specific question from PubMed (≥2 queries, read abstracts) and fail. Confirming the topic exists is not enough. The `pubmed_test.conclusion` must contain `PASS`.

### Phase 7 — Assemble the YAML
Fill every required field per [references/question-schema.md](references/question-schema.md) and [references/template.yaml](references/template.yaml): correct `exact_answer` format for the type; `rdf_triples` with a `# Database: X | Query: N | Comment: ...` line after **every** triple; a `verification_score` that honestly totals ≥9 with no zero dimension; a synthesized `ideal_answer` (single paragraph for `summary`; no meta-references like "according to UniProt"). The question `body` must be self-contained and must **not** name a database.

### Phase 8 — Self-review against C01–C26
Walk the full checklist in [references/qa-checklist.md](references/qa-checklist.md). Any CRITICAL (C01–C06, C22, C23) or MAJOR finding means fix it before presenting — do not present a question you know is flawed. **For C26 (structural near-duplicate), actively scan the existing questions that share this candidate's `type` and database set** — read their `body` and `sparql_queries` and confirm the candidate uses a genuinely different query pattern/predicate path, not the same shape with a new keyword. This is the one check the machine validator can't fully make at the checkpoint (single-file mode sees only this file), so it's on you here. Produce a short verdict (PASS / MINOR / MAJOR) with the triggered codes.

### Phase 9 — Machine validation
Write the candidate to a scratch path and run:
```bash
python benchmark/scripts/verify_questions.py /path/to/candidate.yaml   # single-file mode
```
Fix every ❌ error. (Single-file mode checks structure/format only — it does **not** see the rest of the set, so the aggregate gates and the structural near-duplicate guard run later, in the full Phase-11 validation. Phase 0–1 *biases* toward balance; the full run is what *enforces* the coverage caps and surfaces signature/keyword collisions.)

### Phase 10 — CHECKPOINT: present for approval
Show the user: the rendered YAML, the verify result, and the C01–C26 verdict. **Wait.** Do not write into `benchmark/questions/` or touch the tracker until they approve.

### Phase 11 — Commit the question (after approval only)
- Assign the next id: `question_0NN.yaml` where NN = (current highest + 1), `id` field matching the filename.
- Write it into `benchmark/questions/`.
- Update `benchmark/questions/coverage_tracker.yaml`: `total_questions`; the chosen type's `count`/`questions`; each database's `count`/`questions`; `multi_database_metrics` (2+/3+ counts and percentages); append the keyword to `keywords_used`.
- Append a row to the progress tracker in `benchmark/togomcp_qa_prompt.md` (`| 0NN | P | — |`) and bump its summary line.
- Run the **full** `python benchmark/scripts/verify_questions.py` (no args) to confirm the whole set, including the new question, still passes with 0 errors. **Read the "Structural Near-Duplicate Guard" section** — those are warnings (a reused keyword, an identical `(type, databases, template)` signature, or a 3+ cluster sharing a `(type, database-pair)`); they don't block, but any hit means you should re-examine C26 before considering the question final.

## Scope boundary
This skill stops at **approved, validated questions + updated tracker**. It does **not** run `automated_test_runner.py` or `add_llm_evaluation.py` — collecting answers and scoring the new questions is a separate, explicitly-triggered step (it incurs billed API runs).

## Source of truth
The canonical, full protocol lives in the repo and overrides anything distilled here if they ever disagree:
- `benchmark/QA_CREATION_GUIDE.md` — the v5.5.0 protocol
- `benchmark/QUESTION_FORMAT.md` — the YAML schema
- `benchmark/togomcp_qa_prompt.md` — the QA review prompt (C01–C26) + progress tracker

The `references/` files here are the distilled, in-loop actionable versions; read the canonical doc when a detail is ambiguous.

## File & tool map

| Asset | Path | How |
|---|---|---|
| Question files | `benchmark/questions/question_XXX.yaml` | Read/Write |
| Coverage tracker | `benchmark/questions/coverage_tracker.yaml` | Read/Edit |
| Keyword pool | `benchmark/keywords.tsv` | Read |
| Validator | `benchmark/scripts/verify_questions.py` | Bash (file arg = checkpoint; no arg = full set) |
| QA progress tracker | `benchmark/togomcp_qa_prompt.md` | Edit (Phase 11) |
| Databases / schema | — | `list_databases`, `get_MIE_file`, `run_sparql`, `search_*`, `ncbi_*` (TogoMCP MCP) |
| Ontology terms | — | OLS4 `searchClasses` / `getDescendants`; `search_mesh_descriptor` |
| Literature gate | — | PubMed / `ncbi_esearch` + `ncbi_efetch` |
