---
name: query-provenance
description: >-
  Record the exact TogoMCP tool calls (SPARQL queries, search_*, TogoID, NCBI,
  TogoVar) behind each conclusion of an investigation, re-run them to confirm they
  still give the same results, and package them for a paper: a query ledger
  (ledger.yaml), a human-readable PROVENANCE.md, and a draft Methods paragraph.
  Use whenever the user wants results to be reproducible or citable — "save the
  queries", "for a paper", "for publication", "Methods section", "reproduce",
  "reproducibility", "provenance", "audit trail", "再現", "論文に載せる" — at the
  START of an investigation (record as you go; preferred) or AFTER it (reconstruct
  from the visible conversation). Records tool calls, never prompts: the same
  prompt does not reproduce the same path.
metadata:
  version: "1.0"
  catalog: "Save the queries behind your results so others can reproduce them: exact tool calls, re-run to confirm, plus a draft Methods for a paper"
---

# Query provenance — a reproducible record of what was actually run

The goal is a record a reader can re-run: for every claim, the tool calls that
support it, **copied exactly as they were sent**, plus what they returned, checked
by running them again. A prompt is not a record (an LLM does not take the same path
twice); a call with its arguments is.

This skill's record is the **query ledger**. It is not PRISM's "provenance ledger"
(PRISM's is a per-member evidence table for one intersection); the two can coexist.

Files under `references/` are fetched with
`get_workflow(name="query-provenance", path="references/...")` (when this skill is
installed locally, read them as files instead):

- [references/ledger-format.md](references/ledger-format.md) — the full `ledger.yaml` specification. **Read it before writing the first entry.**
- [references/methods-template.md](references/methods-template.md) — the Methods paragraph template and citation.
- [references/reproduce.md](references/reproduce.md) — the re-run script for readers: pinned URL, command, full copy.
- [references/worked-example.md](references/worked-example.md) — one small investigation, ledger to package.

## Two modes

| Mode | When | What you do |
|---|---|---|
| **Prospective** (preferred) | The user says at the start that this is for a paper, or the purpose is clearly publication | Append to the ledger **as you go**, right after each call that may support a conclusion |
| **Retrospective** | The user asks after the investigation is done | Build the ledger from tool calls **visible in this conversation**. A call whose exact text you cannot see is recorded as `unrecoverable` — never filled in from memory — and re-run fresh if it is needed |

A retrospective package must say at its top: *"Reconstructed after the fact; calls
lost to context compaction may be missing."*

## The rules that make the record worth having

1. **Copy, do not rewrite.** `args` is the argument object you passed to the tool,
   character for character — the same keys (if you passed `query=` to `run_sparql`,
   record `query`), the same whitespace, the same PREFIX lines (write a multi-line
   query as a YAML `|-` block, which adds no trailing newline). Do not reformat, do
   not "clean up", do not reconstruct from memory. A plausible rewrite is the single
   worst failure of this skill: it looks right and reproduces something else.
2. **Never invent a value you could not observe.** In a session:
   - `result_sha256` is **always `null`** — you cannot compute a SHA-256 without
     running code. The reader's script fills it in.
   - `togomcp.server_version` is **`null`** — the server version is not visible to
     you. The script reports it.
   - `executed_at` is a date (`2026-11-02`) unless you really know the time.
3. **Resolve `endpoint_url`, do not guess it.** `run_sparql` does not print the URL
   it used. Call `get_sparql_endpoints` once and take
   `databases[<database>].url`; if the call passed `endpoint_name` or
   `endpoint_url`, those win (priority `endpoint_url > endpoint_name > database`).
4. **Support a count with a COUNT.** You will miscount a 200-row result. When a
   claim is a number, make the evidence call `SELECT (COUNT(DISTINCT ?x) AS ?n)`
   and record its value in `observed.value`. An aggregate with no `GROUP BY`
   returns ONE row even when nothing matched — compare the value, not the row count.
5. **Strip the empty-result note.** `run_sparql` prepends lines starting with `#`
   when a result is empty (0 rows, or a lone aggregate of 0). They are not data:
   drop leading `#` lines before counting rows.
6. **Do not write a reproduction script.** One tested script already exists for
   readers (`references/reproduce.md`); the ledger is its input. Code you cannot run
   to check is code nobody will catch an error in. In an environment with a shell
   (Claude Code) you MAY additionally run that script — never a script of your own.

## Procedure

### 1. Record

For each call that may support a conclusion, append an entry (format:
`references/ledger-format.md`). Give it a `role`:

- `evidence` — directly supports a claim. Re-run and compared.
- `lookup` — an intermediate step (resolving an ID, confirming a label). Re-run; a
  mismatch is a warning.
- `diagnostic` — a failure or comparison that explains the path (e.g. the unpinned
  query whose co-tenant inflation made you add the graph pin). Not re-run.

Failed attempts stay out by default; keep one as `diagnostic` only when it changed
the conclusion.

In prospective mode, write the entry right after the call while its text is still
in front of you. Long sessions lose early text to compaction; an entry written at
the time cannot be lost that way.

### 2. Select

For each final claim, choose the **smallest** set of calls that supports it and list
them under `claims[].supported_by`. Every claim in the write-up needs at least one
`evidence` call; a claim with none is either removed or labelled as not backed by
a recorded query.

### 3. Re-run and compare

Re-run every `evidence` and `lookup` call by **calling the same tool with the
arguments copied from the ledger** — from the ledger, not from the original call in
the conversation, so that a copying error in the ledger is caught here. No code.

Compare with what the entry recorded:

| Recorded | Match when |
|---|---|
| `n_rows` | the same number of data rows (header and `#` note lines excluded) |
| `value` | the same single value (numerically equal is enough: `214` = `214.0`) |
| `key_values` | every one appears in the new result |

Classify each mismatch:

- `data_changed` — the call is right, the data moved (a new UniProt release, a
  reloaded graph). Report both numbers; the newer one is the current answer.
- `ledger_error` — the record is wrong (a copying slip, a call missing from a
  retrospective reconstruction). Fix the ledger from the conversation if the
  original is visible, then re-run.
- `endpoint_error` — unreachable or timed out. Retry later; do not count it as a
  match.

Record the outcome per call under `verification` in the ledger.

### 4. Package

Write three files (contents: `references/ledger-format.md` § Outputs):

- `ledger.yaml` — the ledger, with verification results.
- `PROVENANCE.md` — for people: per claim, the supporting calls, their purpose, the
  full query text, the comparison result; and how to re-run
  (`references/reproduce.md`: pinned script URL and command).
- `METHODS.md` — the draft Methods paragraph (step 5).

Where to put them:

- **Claude Code**: `provenance/<YYYY-MM-DD>-<slug>/` in the working directory.
- **claude.ai / Claude Desktop with file creation**: as files.
- **No file creation**: each file in its own fenced code block, `ledger.yaml` first.

### 5. Methods

Fill `references/methods-template.md`. **Every number comes from the ledger and its
verification results** — databases, endpoints, dates, counts. Nothing from memory.
Leave the TogoMCP version as a placeholder for the author (rule 2) unless the
script reported it.

## Limitations (state these in PROVENANCE.md)

- **Context compaction.** In a long session the exact text of early calls can be
  lost. Prospective recording is the defence; a retrospective ledger can only hold
  what is still visible, and says so.
- **No proof of origin.** The ledger cannot prove these calls were what produced the
  original answer. What it shows is that the recorded calls, re-run, give results
  that match.
- **Versions are approximate.** Most databases do not expose a release number, and
  the server version is not visible in a session. The date, endpoint URL and graph
  IRIs stand in for a version; the script adds the server version when run.
- **No hashes in-session.** `result_sha256` is filled only by the script.

## Gotchas

- **Unpinned graphs.** A `run_sparql` query without `FROM`/`GRAPH` reads every graph
  co-hosted on its endpoint, so the same text can return a different number after an
  unrelated database is loaded next to it. Record `graphs` from the query; if it pins
  none, say so in PROVENANCE.md.
- **Search tools re-rank.** `search_*` results are ordered by the upstream service
  and can reorder between releases. Use `key_values` for those, not `n_rows`.
- **`LIMIT` without `ORDER BY`** returns an arbitrary subset, which can differ
  between runs. Add `ORDER BY` to evidence queries, or record only the count.
- **Retrospective gaps are findings.** An `unrecoverable` entry is honest; a
  reconstructed one presented as original is not.
