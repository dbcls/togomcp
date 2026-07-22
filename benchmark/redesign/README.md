# MIE Redesign (v3) — Plan & Status

*Tracked plan for the from-scratch MIE format redesign, executed on the `mie-redesign`
branch. The full design **rationale** (with the ablation evidence) lives in
`internal_docs/mie-redesign-from-scratch-2026-07-20.md` — a local working doc that is
**gitignored**, so this README is the on-branch summary. Where they differ, the rationale is
the argument and `MIE_v3_spec.md` is the contract.*

## Why

The 2026-07 MIE ablation sweeps established that the current v2.3 format carries heavy,
*orthogonal* redundancy — the same fact written up to four ways (schema list, ShEx shape,
worked query, sample triple):

- **Whole MIE helps** (`no_mie` removed the whole thing → **+0.9/20**, z≈2.6, significant).
- **No single section or group is *necessary*** (leave-one-out: all 11 sections and all 3
  groups null) — redundancy covers any one removal.
- **The `query` group alone is *sufficient*** (leave-one-in: `keep_query` recovers **99%** of
  the whole-MIE effect, z=3.32; guardrails/orientation 13%/44%, NS).

⇒ The value is real but concentrated in query-construction content. Reorganize *around it*,
collapse the 4× restatement, and drop the prose-only sections — same value, far fewer tokens.

## The v3 format (see `MIE_v3_spec.md`)

Organized by **agent need × recoverability**, with the **verified, executable worked example
as the atomic unit** (one example *is* the schema + shape + sample + annotated warning). Five
parts:

1. `discovery` — {title, description, keywords, categories}; the build-time Usage-Guide catalog source.
2. **header** — endpoint, graphs (with co-tenancy flags), dated `entity_counts`, `global_gotchas` (database-wide traps only).
3. `examples` — the load-bearing content; each executable, `verified:`+dated; `aggregation` and `cross_db` elevated; query-specific traps inline as `traps_avoided`.
4. `schema_delta` — only non-obvious predicates no example already shows.
5. `id_join_map` — stable anchors + cross-DB join paths.

Rules: everything countable is verified and dated (machine-testable); one fact, one place;
carry only the non-recoverable.

## Execution sequence (gated)

| # | Step | State |
|---|---|---|
| 1 | Finalize the schema (write `MIE_v3_spec.md`) | ✅ done |
| 2 | Pilot MIE(s) in the new format, live-verified | ✅ UniProt + BacDive (62–64% smaller, live-verified) |
| 3 | Smoke test (pilot subset vs v2.x, ablation harness) — bail early on gross regression | ✅ done — **yellow light**, see `smoke/FINDINGS.md` |
| 3a | Diagnose q066 regression; fold the lesson into `MIE_v3_spec.md` | ✅ done — keyword-enumeration route was demoted to a caveat; fixed (spec §4.4 + `keyword_enum` example) |
| 3b | §4.4 enumeration-route audit of all 36 DBs → `enumeration_audit.md` | ✅ done — 34/36 already first-class; 4 Tier-A buried routes (ddbj/glycosmos/pubchem/mogplus) to un-bury, tiers B/C to keep route+caveat together |
| 4 | Author the **full** redesigned corpus (all 36) | ⬜ (needs 3a+3b; 100Q gate needs full corpus — coverage is all-or-nothing). Per-DB §4.4 obligations in `enumeration_audit.md` |
| 5 | **Release gate**: full-100Q equivalence run | ⬜ |
| 6 | Release (MAJOR): flip served corpus + retire discovery trio | ⬜ |

Smoke result (2026-07-21/22): overall −0.44 ± 0.82 (NS); uniprot flat (−0.13, n=20), a **systematic**
v3 regression on q066 (LIM-domain enumeration — v3 found 14 proteins vs true 71, all 3 runs). The
compression can drop set-level enumeration guidance; diagnose before scaling (step 3a).

**Validation (step 5) is an equivalence test, not "did the score go up?":**
- tokens/bytes **down** — the deterministic win (no stats).
- judge score **flat within a declared margin** (~±0.5/20 at 100Q×3) — must not regress.
- factoid correctness **up-or-flat** — tests the aggregation-recipe claim.

## Key decisions locked

- **Parallel dir, production untouched.** New-format MIEs live under `benchmark/redesign/mie_v3/`;
  `togo_mcp/data/mie/` stays intact and servable throughout. No server code changes until the
  format is proven.
- **Retire the discovery trio at release** (`find_databases` / `list_databases` /
  `list_categories`) — a **MAJOR** semver bump + a workflow-prompt rewrite. Justified because
  the full DB roster is *already* always in the tool schema (`DATABASE_DESCRIPTION` on
  `run_sparql`/`get_MIE_file`), so those tools are redundant for "what exists"; the catalog
  (descriptions) moves to a build-time Usage-Guide generator.
- **Transition ordering:** ship/validate the guide-catalog generator *before* removing the trio.

## Current status (2026-07-21)

- `MIE_v3_spec.md` — the authorable spec (152 lines vs the v2.3 spec's 1506).
- `mie_v3/uniprot.yaml` — hand-authored UniProt pilot, **coverage-matched** to v2.5 (11
  examples: 7 single + 4 cross-DB), **~64% smaller** (57.4 KB → 20.9 KB), every count/example
  re-run live 2026-07-21 (zero drift).
- Authoring surfaced real query bugs the old prose missed — the insulin readthrough-isoform
  trap, the Rhea `COUNT` timeout — now inline `traps_avoided`; plus a `date:`-not-`on:`
  YAML-boolean footgun, documented in the spec.

**Next:** a second, contrasting pilot (cross-DB-heavy or isolated-endpoint DB) to check the
spec isn't overfit to UniProt, then the smoke test (step 3).

## Files

- `README.md` — this plan/status.
- `MIE_v3_spec.md` — the v3 format contract.
- `enumeration_audit.md` — per-DB §4.4 enumeration-route checklist for step-4 authoring.
- `mie_v3/<db>.yaml` — new-format MIEs (pilots first, full corpus later).
