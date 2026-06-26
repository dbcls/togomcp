---
name: qa-generator
description: Generate, refresh, or replace benchmark questions for the TogoMCP evaluation set (benchmark/questions/question_XXX.yaml). Use whenever the user asks to create, add, extend, refresh, re-validate, replace, redirect, or retire benchmark questions — e.g. "add a few benchmark questions", "extend the QA set", "we need more list-type questions", "write a new question about a topic or database", "grow the benchmark past 50", "refresh question_042", "the answer to Q030 looks stale", "the queries are out of date". Anything mentioning benchmark/questions, coverage_tracker.yaml, the QA creation guide, or question YAML files. New questions follow the v5.5.0 type-first protocol against live RDF databases (SPARQL, OLS4, PubMed); updates re-run queries against current state and refresh answers — both presented for approval before writing.
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
The valid database set is the live registry — `togo_mcp/data/resources/endpoints.csv` (= what `list_databases()` returns) — restricted to **life-science** databases; `verify_questions.py` derives its accepted set from that same file, excluding non-life-science endpoint groups (currently `nims`, the NIMS materials-science endpoint, e.g. the `supercon` superconductor database). So any current life-science database is fair game and **newly added life-science databases are not only allowed but are the highest-priority coverage targets** (they appear at count 0 in the Next-Question Guidance). Do not build questions on the excluded materials databases even though `list_databases()` shows them — the validator will reject them. Prefer under-used databases (the guidance lists them; the tracker's `databases` counts are a secondary view that may lag for just-added ones). Call `list_databases()`, then pick **2–3** with complementary domains and a real cross-reference path (e.g. UniProt→PDB, ChEMBL→ChEBI), compatible with the type (`summary` needs ≥3). Call `get_MIE_file()` for each chosen database before writing any SPARQL. Avoid pushing UniProt past 70% of the set.

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

## Update mode — refresh or replace an existing question
The databases behind these questions change continuously, so a question that was correct when written can silently rot: its recorded `result_count`/`exact_answer`/`rdf_triples` drift from current state, a `bif:contains` query gets superseded by a now-available ontology IRI, or a newly added database makes a sharper question possible. When the user asks to **refresh**, **re-validate**, **replace**, **redirect**, or **retire** a question (or audit the set for staleness), run **update mode** instead of the create workflow above. Full protocol: [references/update-mode.md](references/update-mode.md). Two sub-modes, both keeping the **same `id`** and ending at the **same Phase-10 checkpoint** (present, then write only on approval):

- **Refresh** (same `id`, `type`, databases, keyword — the *answer* may move). Re-run every query in the file **exactly as written** against the live endpoint; diff new results vs. recorded. If nothing moved, report "verified, no drift" and stop. If the answer moved, that is the headline — re-derive `result_count`, `rdf_triples`, `exact_answer`, `ideal_answer` from the new results, re-run the Rule-3 arithmetic checks, and re-run the necessity gates only if scope changed. You may rewrite a query for a *better* predicate path (e.g. a structured IRI that didn't exist before), but the rewrite must return a re-validated answer and be justified. **Never silently keep a stale gold answer.** Tracker is untouched (nothing about type/db/keyword changed); only flip the `togomcp_qa_prompt.md` verdict if the C-review verdict changed.
- **Replace / redirect** (same `id`, new content — typically to adopt a newly added or better-fit database). This is *retire-old + create-new under the same id*: run create Phases 0–9 with the id pinned to the existing number, then do **delta tracker accounting** instead of append. Prefer **adding** a new question over replacing when the goal is just to cover a new database — replacement shrinks coverage breadth, so only redirect when the existing question is genuinely stale or inferior. Record the swap in `coverage_tracker.yaml`'s `next_priorities` notes, following the existing "QNNN replaced (date): …" convention.

**Tracker reconciliation (the part that bites).** `verify_questions.py` recomputes counts from the actual files and is your safety net, but it only covers *some* fields — know which:
- **Errors (the validator forces these):** `total_questions` and every per-`type` count. A type change in Replace mode *will* be caught.
- **Warnings only (you must fix them by hand anyway):** per-`database` counts. Decrement the old question's databases / increment the new ones, deleting a db block that drops to 0.
- **Not checked at all (purely manual):** `keywords_used` (free the old keyword, add the new — keep it an accurate map of in-set keywords), `multi_database_metrics` (recompute 2+/3+ counts and percentages), and the `togomcp_qa_prompt.md` row. The full-run **duplicate-keyword** guard will fire if you add the new keyword but forget to remove the old one.
After editing, run the **full** `verify_questions.py` and drive it to **0 errors**, then hand-reconcile the not-checked fields. Lean on the validator as the source of truth for counts.

**Staleness audit (batch).** To find *which* questions need attention, loop Refresh's re-run-and-diff step (read-only) across the set and report the drifted ones — then take each through the per-question checkpoint. It re-runs every query, so it is read-heavy; never batch-write fixes, pause on each like the create loop.

## Scope boundary
This skill stops at **approved, validated questions + updated tracker**. It does **not** run `automated_test_runner.py` or `add_llm_evaluation.py` — collecting answers and scoring the new questions is a separate, explicitly-triggered step (it incurs billed API runs).

## Source of truth
The skill's `references/` files are authoritative for the generation protocol — they are the in-loop, current versions and are what you follow. For the YAML schema specifically, `benchmark/QUESTION_FORMAT.md` remains the canonical spec (`references/question-schema.md` is its distilled form); consult it when a schema detail is ambiguous.

Two older repo docs are **not** authoritative for generation — do not defer to them on conflict:
- `benchmark/QA_CREATION_GUIDE.md` — the original v5.5.0 long-form protocol, kept for background/history only. It predates this skill and has stale paths and tool names; the `references/` files supersede it.
- `benchmark/togomcp_qa_prompt.md` — now used **only** as the QA progress-tracker data file that Phase 11 appends to (it holds the per-question P/W/F verdict, which lives nowhere else). Its embedded C01–C25 reviewer prompt is superseded by `references/qa-checklist.md` (C01–C26).

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
