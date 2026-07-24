# Tier C — migrate the MIE authoring tooling from v2 format to v3

**Status:** OPEN (tracked follow-up to the v3 redesign). Not blocking the step-6 release.
**Created:** 2026-07-24, on `mie-redesign`.
**Contract:** `benchmark/redesign/MIE_v3_spec.md` is the v3 format spec the tooling must author to.

## Why

The v3 redesign passed its equivalence gate (see `release/FINDINGS.md`) and the served corpus
flips to the v3 format at step 6. But the **authoring tooling still teaches the v2 format** — it
was written for `schema_info` / `shape_expressions` / `sample_rdf_entries` / `critical_warnings` /
`co_hosted_graphs` / `architectural_notes` / `data_statistics` / `anti_patterns`. The v3 format is
entirely different: `discovery` / `header` / `examples` (verified, dated) / `schema_delta` /
`id_join_map`. Post-release, if anyone runs the tooling to add or revise a database, it produces a
**v2-shaped file that no longer matches the served corpus or the spec.**

The v3 corpus itself was NOT built with these skills — it was built by the delegated
agent-per-DB method reading `MIE_v3_spec.md` directly (see the `project_mie_v3_corpus_complete`
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
`references/` skeleton point at `MIE_v3_spec.md` as the single source of truth (rather than
duplicating the section spec in the skill). Consider having the skill *read* the spec at author time
so the two can't drift.
