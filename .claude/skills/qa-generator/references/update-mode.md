# Update mode — refreshing and replacing existing questions

The create workflow (Phases 0–11 in SKILL.md) is **append-only**: it mints `question_0NN.yaml`
at `NN = highest + 1`. Update mode operates on a question that **already exists**, keeping its
`id`, and exists because the RDF databases behind the benchmark change continuously — counts move,
new ontology IRIs appear, `bif:contains` hacks become avoidable, and newly onboarded databases make
sharper questions possible.

Everything from the create protocol still applies: the **Three Hard Rules** (nothing invented;
scope = query scope; every GROUP BY gets an arithmetic check), the **C01–C26** checklist, and the
**necessity gates**. Update mode changes only *what* you write (an existing file) and *how* you keep
the tracker honest (delta, not append). Like create mode: **one question at a time, present at the
checkpoint, write only on approval. Never batch-write.**

Pick the sub-mode by what is changing:

| You are… | the answer can change | type/databases/keyword change | sub-mode |
|---|---|---|---|
| re-validating a question against today's data | yes | no | **Refresh** |
| pointing a question at a new/better database or new topic | yes | yes | **Replace** |

---

## Sub-mode R — Refresh (same id, type, databases, keyword)

Goal: confirm the question still answers correctly against current state, and if the gold answer
has moved, move it — honestly.

**R1. Load.** Read `benchmark/questions/question_0NN.yaml`. Note its `sparql_queries`
(with stored `result_count`), `exact_answer`, `ideal_answer`, and the facts asserted in `rdf_triples`.

**R2. Re-run, exactly as written.** Execute every query in `sparql_queries` verbatim against the
live endpoint (read its database's MIE first only if a query now errors). Record the new
`result_count` and the key result rows.

**R3. Diff.**
- **No drift** — new results match stored `result_count` and the recorded answer. Report
  "verified, no drift," show the re-run evidence, and **stop**. No write needed. (The schema has no
  "last-verified" field — do not invent one.)
- **Drift** — any `result_count`, `exact_answer` value, or `rdf_triples` fact changed. This is a
  **benchmark-integrity event**: the gold answer moved. Continue.

**R4. Re-derive (only on drift).** Update from the *new* query results: `result_count` on each query,
`rdf_triples` (re-extract from the new rows; keep the `# Database: X | Query: N | Comment: …` line
after every triple), `exact_answer` (correct format for the type), and `ideal_answer`. Re-run every
**Rule-3 arithmetic** check (GROUP BY sum == COUNT(DISTINCT)). Bump `time_spent`/notes only if you
must; do not fabricate.

**R5. Optional query improvement.** You MAY rewrite a query for a genuinely better predicate path —
e.g. a structured GO/MONDO/ChEBI IRI now exists where the original used `bif:contains`, or a MIE
revision exposes a cleaner join. Constraints: the rewrite must **return a re-validated answer**
(run it), must not narrow scope (Rule 2), and must be justified in the file. Do **not** churn query
shape gratuitously — a refresh is not a rewrite contest.

**R6. Necessity gates.** Re-run the training + PubMed gates **only if scope/answer changed
materially**. A count that merely nudged (e.g. 41 → 43) usually leaves the gates intact — say so. A
qualitative flip (e.g. an existence yes→no, or a list gaining/losing members that change the point)
needs the PubMed gate re-run to keep `rdf_necessity` honest.

**R7. Self-review + validate.** Walk C01–C26 on the edited file (C03 especially if counts moved;
C08/C15 if the answer's shape shifted). Run `python benchmark/scripts/verify_questions.py
/path/to/question_0NN.yaml` (single-file) and fix every ❌.

**R8. CHECKPOINT.** Present: the **old → new diff** (what the answer was, what it is now, and why),
the changed fields, the re-run evidence, and the C-verdict. Wait for approval.

**R9. Write back + reconcile.** Overwrite the same `question_0NN.yaml`. **Tracker is untouched** —
type, databases, and keyword did not change. The only possible tracker-adjacent edit is the
`togomcp_qa_prompt.md` verdict cell, and only if the C-review verdict changed (e.g. `P` → `W`). Run
the **full** `verify_questions.py` to confirm 0 errors (a refreshed answer can shift the
structural-near-duplicate picture only if you rewrote a query — re-check C26 if so).

> If a refresh reveals the question can no longer be answered cleanly with its current databases
> (an endpoint dropped a predicate, a database was retired, the answer collapsed to empty/whole-DB),
> stop refreshing and switch to **Replace** — don't contort a query to keep a dead question alive.

---

## Sub-mode X — Replace / redirect (same id, new content)

Goal: retire a stale/inferior question and mint a better one **under the same id** — most often to
adopt a newly added or better-fit database.

**Prefer adding over replacing.** Covering a new database is usually a job for the create workflow
(a *new* id), which grows coverage. Replace only when the existing question is genuinely stale,
inferior, or made redundant — replacement keeps the set size flat and *loses* the old question's
coverage. State the justification.

**X1–X9. Run create Phases 0–9** (type → databases → keyword → vocab discovery → explore → arithmetic
→ necessity gates → assemble → self-review → single-file validate) with two changes:
- **Pin the id** to the existing `0NN` (filename and `id` field), not `highest + 1`.
- **Type policy:** keeping the same `type` avoids distribution churn. If you change it, that's
  allowed but the validator will force the type-count rebalance (see below) — do it deliberately.

**X10. CHECKPOINT.** Present the new question *and* an explicit note that it replaces the old one
(what it was → what it becomes → why). Wait for approval.

**X11. Write + delta tracker accounting.** Overwrite `question_0NN.yaml`, then update
`coverage_tracker.yaml` as a **delta**, not an append:
- `total_questions`: **unchanged** (replacement, not addition).
- `question_types`: decrement the **old** type's `count` and remove `0NN` from its `questions`;
  increment the **new** type and add `0NN`. (No-op if the type is unchanged.)
- `databases`: for each **old** database, remove `0NN` and decrement `count` — **delete the block**
  if it hits 0 and no other question uses it. For each **new** database, add `0NN` / increment /
  create the block.
- `keywords_used`: **remove** the old keyword line and **add** the new one. (Keep it an accurate map
  of in-set keywords; a leftover old keyword will trip the full-run duplicate-keyword guard once the
  new one is added, or wrongly block future reuse.)
- `multi_database_metrics`: recompute `two_plus_databases` and `three_plus_databases` counts,
  question lists, and percentages — the new question's DB-count may differ from the old one's.
- `next_priorities`: append a replacement note, following the existing convention, e.g.
  `- 'Q0NN replaced (YYYY-MM-DD): <old topic/dbs> → <new topic/dbs>; <one-line why>'`.
- `togomcp_qa_prompt.md`: set the `0NN` row's verdict from the new C-review; the summary counts are
  unchanged (same number of questions).

**X12. Full validation.** Run `python benchmark/scripts/verify_questions.py` (no args), drive to
**0 errors**, then re-read the Structural Near-Duplicate Guard.

---

## Tracker reconciliation — what the validator does and doesn't catch

`verify_coverage_tracker` recomputes the true counts from the question files. Use it as the source
of truth, but know its blind spots:

| Tracker field | Recomputed & compared? | Severity on drift | So you must… |
|---|---|---|---|
| `total_questions` | yes | **error (❌)** | trust the validator; fix to its number |
| `question_types[*].count` | yes | **error (❌)** | trust the validator; fix to its number |
| `databases[*].count` | yes | **warning (⚠)** | fix by hand — it won't block |
| `databases[*].questions` lists | no | — | maintain by hand |
| `question_types[*].questions` lists | no | — | maintain by hand |
| `keywords_used` | no (only duplicate-keyword collisions, via the structural guard) | — | maintain by hand |
| `multi_database_metrics` (2+/3+, %) | no | — | recompute by hand |
| `togomcp_qa_prompt.md` row/summary | no | — | maintain by hand |

Workflow: make the edits → run full `verify_questions.py` → fix every ❌ (and the ⚠ db-count lines)
→ hand-reconcile the "no" rows. The validator will not tell you the manual fields are wrong, so the
discipline is on you.

---

## Staleness audit (find what to update)

To discover *which* questions have drifted without editing anything:

1. For each `question_0NN.yaml`, run sub-mode **R1–R3** (load, re-run queries verbatim, diff). This
   is read-only and read-heavy (it re-executes every query in the set).
2. Report the drifted questions: `id`, which `result_count`/answer moved, old → new.
3. Take each drifted question through **Refresh** (or **Replace** if it's beyond saving), one at a
   time, pausing at the checkpoint — exactly like the create loop. **Never batch-write fixes.**

Good triggers for a proactive audit: a database was just refreshed/onboarded; the MIE files were
regenerated; or it's simply been a while and the user wants the gold answers re-confirmed.
