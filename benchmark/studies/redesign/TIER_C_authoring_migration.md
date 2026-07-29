# Tier C — migrate the MIE authoring tooling from v2 format to v3

**Status:** DONE (authoring tooling migrated to v3, 2026-07-25). The deferred acceptance item was
**exercised 2026-07-29 on the REVISION path** and passed; the fresh-DB path remains unexercised
(see "Acceptance run" at the bottom). Was: OPEN, not blocking step 6.
**Created:** 2026-07-24, on `mie-redesign`. **Migrated:** 2026-07-25. **Acceptance run:** 2026-07-29.
**Contract:** `togo_mcp/data/docs/MIE_v3_spec.md` is the v3 format spec the tooling must author to.

## What was done (2026-07-25)

All three authoring paths now teach v3. Changed files:

- **`.claude/skills/mie-generator/references/template.yaml`** — replaced with a v3 skeleton
  (`database` · `discovery` · header · `examples` · `schema_delta` · `id_join_map`). Structurally
  identical top-level keys + example sub-keys to the committed `uniprot.yaml` pilot (verified by diff).
- **`references/mie-structure.md`** — rewritten to the five v3 need-based parts; adds a "what v3
  dropped" map and the byte-budget rule; points at `togo_mcp/data/docs/MIE_v3_spec.md` as the contract.
- **`references/anti-patterns.md`** — recast: trap knowledge now splits into header `global_gotchas`
  (database-wide) vs inline `traps_avoided` (query-specific); the four universal traps become
  `teaches`/example idioms; the §4.4 enumeration-route rule is front-and-center.
- **`references/query-strategy.md`** — light edits only (format-neutral): "7-query set" → "example
  set", `shape_expressions`/`access.backend` references removed, "good query" criteria reframed to
  the `verified:`/`teaches`/enumeration lens.
- **`SKILL.md`** — hard rules retargeted to `examples[].verified:`+`date:`; Phase 2 discovery probes
  KEPT (format-independent) with only their destination-section names updated (`shape_expressions`→
  examples/`schema_delta`, `critical_warnings`→`global_gotchas`/`traps_avoided`, `co_hosted_graphs`→
  `graphs.co_hosted`, `schema_info.graphs`→`graphs`); Phase 2e reframed from ShEx modifiers to
  OPTIONAL/DISTINCT authoring choices; Phase 3/4/5/6 + declaration block + Quality bar rewritten to
  v3; §4.4 enumeration + §4.6 no-test-leakage checks added to Phase 5.
- **`.claude/agents/mie-builder.md`** — retired-trio reference removed; v3 field names + `verified:`/
  `date:` rule in the hard rules; output contract updated.
- **`.claude/workflows/mie-refresh.js`** — buildPrompt + validatePrompt rewritten to v3 (`examples[]`
  with `verified:`/`date:`, required-key check, `on:`-trap grep); a **Catalog** phase added that
  regenerates the Usage-Guide catalog ONCE after the whole batch (not per-builder — avoids racing on
  a partial corpus). `node --check` passes.
- **`scripts/check_mie_examples.py`** — NO code change needed (generic recursive walk on the `sparql`
  key already finds `examples[].sparql`; confirmed live on `uniprot` — 11/12 ok, 1 transient
  timeout). Docstring refreshed to say so.

**Verified:** template parses + required keys present + top-level order/example-keys identical to
`uniprot.yaml`; `check_mie_examples.py uniprot` runs clean on the v3 file; `test_catalog_in_sync`
passes; `mie-refresh.js` syntax-checks.

## Acceptance run (2026-07-29) — revision path PASSED, fresh-DB path still open

Ran the `mie-generator` skill in the main thread against `uniprot` (the v3 pilot, last verified
2026-07-21/22). The tooling drove the full workflow and produced a spec-valid v3 file: 12/12 examples
re-executed live, `check_mie_examples.py uniprot` clean, all 6 required keys in spec order, every
`verified:` carrying a `date:` (no `on:` keys), catalog regen idempotent, `test_catalog_in_sync` green.

**The mandatory phases earned their keep** — this was not a rubber-stamp:

- A UniProt release had landed: **every count drifted** (reviewed 574,627 → 575,503; the `go_function`
  and `ec_class` example figures; OMA `lscr:xrefSwissProt` 381,038 → 460,199).
- **Phase 2a** (mandatory even for revisions) found the graph list incomplete — six UniProt-owned
  graphs missing, including `obsolete`, whose 14,454 deleted entries the gotchas already discussed.
  Exactly the "trusting the existing graph list" failure 2a exists to catch.
- **Phase 2g** found a NEW trap: `rdfportal.org/ontology/go` duplicates GO `rdfs:label`/`subClassOf`
  against UniProt's own `sparql.uniprot.org/go`. Labels agree (so it reads as a legitimate
  multi-valued label and DISTINCT hides it) but `subClassOf` sets differ → now `go_label_duplication`.
- The `union_inflation` gotcha nearly got "corrected" wrongly: probing TP53 shows no OMA triples, which
  makes the OMA attribution look false. Per-graph decomposition shows the re-typing is a **subset**
  (335,971 of 589,957) that happens to exclude TP53. The gotcha now says so explicitly.

**Still open — the fresh-DB half.** This run started from an existing file and skipped Phase 0
(register the endpoint). "Author a database from scratch" and the throwaway diff-shape round-trip
against an already-covered DB have still never been exercised. Do those at the next database add.

### Two skill ambiguities this run surfaced (not blocking; fix when convenient)

1. **§4.6 test-leakage vs the canonical-subject exemption conflict.** `P04637` now collides with
   `question_099` (added since the pilot was authored — the benchmark reached 100 questions), which
   uses UniProt and names TP53 in its answer narrative. The bright-line rule says swap the subject;
   the skill's own 5h text says "Canonical non-benchmark subjects (ATP, TP53, BRCA1) are fine."
   Nothing states which wins. The exemption was applied and P04637 retained (the four TP53 examples
   concern variants/FALDO/OMA/Bgee, none touching q099's KW-0325 glycoprotein count) — but the next
   author hits the same fork with no guidance.
2. **No size guidance for a v3→v3 revision.** The Quality bar's "clearly smaller than the v2 file it
   replaces" is a conversion criterion. This revision grew +11% (22,294 → 24,837 bytes) entirely from
   new verified content, and there is no stated bar for when revision growth is legitimate.

### Related, but outside this task's scope

TIER_C chartered the three *authoring* paths only. The v3 drift in the **runtime** surface — the
served Usage Guide's MIE reading order, the `get_MIE_file` description, the `qa-generator` skill —
was never in scope here and was found and fixed separately in `f24c851`.

---

## Original scope (for reference)

## Why

The v3 redesign passed its equivalence gate (see `release/FINDINGS.md`) and the served corpus
flips to the v3 format at step 6. But the **authoring tooling still teaches the v2 format** — it
was written for `schema_info` / `shape_expressions` / `sample_rdf_entries` / `critical_warnings` /
`co_hosted_graphs` / `architectural_notes` / `data_statistics` / `anti_patterns`. The v3 format is
entirely different: `discovery` / `header` / `examples` (verified, dated) / `schema_delta` /
`id_join_map`. Post-release, if anyone runs the tooling to add or revise a database, it produces a
**v2-shaped file that no longer matches the served corpus or the spec.**

The v3 corpus itself was NOT built with these skills — it was built by the delegated
agent-per-DB method reading `togo_mcp/data/docs/MIE_v3_spec.md` directly (see the `project_mie_v3_corpus_complete`
memory). So the tooling has been bypassed, not updated. This task closes that gap.

## Already done (Tier A + B, do NOT redo) — commits 6c28415, d4a75cb

- Retired-discovery-trio references removed from `mie-generator` (category check now uses
  `scripts/generate_usage_guide_catalog.py --list-categories`; tools preamble updated).
- Catalog-regen wired into `mie-generator` Phase 6 + `tests/test_catalog_in_sync.py` drift guard.
- `scripts/generate_usage_guide_catalog.py` (+ `--list-categories`, `--check`) is the build-time
  catalog generator. **The generator is format-agnostic — it reads `discovery` or `schema_info` —
  so it does NOT need Tier-C work.**

## Scope — three authoring paths, all v2-shaped

### 1. `mie-generator` skill (main-thread, single file) — the big one
`.claude/skills/mie-generator/SKILL.md` + `references/{template.yaml, mie-structure.md,
anti-patterns.md, query-strategy.md}`.
- **Survives largely as-is:** Phases 0–3 (register endpoint, orient, live discovery 2a–2g, design)
  — discovering the schema against the live endpoint is format-independent.
- **Needs rewriting for v3:**
  - **Phase 4 "Write the file"** — rewrite the section list to v3 (`discovery`, `header` with
    `entity_counts`/`global_gotchas`, `examples` as verified+dated executable atoms with
    `traps_avoided`, `schema_delta`, `id_join_map`).
  - **Phase 5 "Validate"** — retarget the checks: every `examples` entry `verified:`+dated and
    live-re-run; §4.4 (every set-level enumeration route is a first-class example); §4.6 (no example
    subject is a benchmark question's entity — grep against `benchmark/questions/*.yaml`); Phase-5
    checklist items 8 & 9 from the spec. `scripts/check_mie_examples.py` may need a v3-aware pass.
  - **Phase 6 checklist** — replace v2 section bullets with v3 ones (keep the catalog-regen bullet).
  - **`references/template.yaml`** — replace with a v3 skeleton. **`mie-structure.md`** — rewrite
    per-section requirements to v3. **`anti-patterns.md`** — re-cast as v3 `traps_avoided`.
    `query-strategy.md` is mostly format-neutral (keep, light edits).
  - Remaining `schema_info` prose references (SKILL.md lines ~60, 73, 79, 81, 359) → v3 field names.

### 2. `mie-builder` agent (delegated worker) — `.claude/agents/mie-builder.md`
- Line ~31 references `list_categories` (retired) and line ~35 `schema_info` (v2). Same Tier-A
  (trio) + Tier-C (format) treatment as the skill. This is the agent the batch path spawns, so its
  format allegiance matters most.

### 3. `mie-refresh` workflow — `.claude/workflows/mie-refresh.js`
- Orchestrates one `mie-builder` per DB. Format-neutral today. Add: **regenerate the catalog ONCE
  after the whole batch** (`scripts/generate_usage_guide_catalog.py`), NOT per-builder — the builders
  may run in parallel/worktrees and a per-agent regen would race on a partial corpus.

## Acceptance criteria

- Running `mie-generator` on a fresh DB produces a spec-valid **v3** file (passes the same checks the
  hand/agent-authored v3 corpus passed).
- No authoring path references the retired trio.
- `references/template.yaml` is a v3 skeleton; `mie-structure.md` describes v3 sections.
- Batch path (`mie-refresh`) regenerates the catalog once at the end; drift guard stays green.
- A round-trip test: author a throwaway v3 MIE for an already-covered DB, diff its shape against the
  committed v3 file — structurally equivalent.

## Suggested approach

Mirror how the corpus was actually built: keep the live-discovery phases, and make Phase 4/5 + the
`references/` skeleton point at `togo_mcp/data/docs/MIE_v3_spec.md` as the single source of truth (rather than
duplicating the section spec in the skill). Consider having the skill *read* the spec at author time
so the two can't drift.
