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
carry only the non-recoverable; every set-level enumeration route is a first-class example
(§4.4); no example subject is a benchmark question's entity (§4.6 — no test leakage).

## Execution sequence (gated)

| # | Step | State |
|---|---|---|
| 1 | Finalize the schema (write `MIE_v3_spec.md`) | ✅ done |
| 2 | Pilot MIE(s) in the new format, live-verified | ✅ UniProt + BacDive (62–64% smaller, live-verified) |
| 3 | Smoke test (pilot subset vs v2.x, ablation harness) — bail early on gross regression | ✅ done — **yellow light**, see `smoke/FINDINGS.md` |
| 3a | Diagnose q066 regression; fold the lesson into `MIE_v3_spec.md` | ✅ done — keyword-enumeration route was demoted to a caveat; fixed (spec §4.4 + `keyword_enum` example) |
| 3b | §4.4 enumeration-route audit of all 36 DBs → `enumeration_audit.md` | ✅ done — 34/36 already first-class; 4 Tier-A buried routes (ddbj/glycosmos/pubchem/mogplus) to un-bury, tiers B/C to keep route+caveat together |
| 4 | Author the **full** redesigned corpus (all 36) | ✅ **36/36 done** — all agent-authored (2 hand-authored pilots + 34 delegated), every enum route independently live-re-verified, all under §4.6 (no test leakage). 302 examples; byte reductions 29–65%. Live-verify caught many v2 errors along the way. Per-DB obligations from `enumeration_audit.md` all satisfied |
| 5 | **Release gate**: full-100Q equivalence run | 🔄 harness ready, not yet started — runs `--conditions smoke_v2,full_v3` (smoke_v2 = full prod v2, byte-identical to `togo_mcp/data/mie/`; `full_v3` = full v3 corpus) in **4×25-QA batches** with a review gate per batch, folded via `append_results.py`. API answering (~$80 + ~8h per batch). Dry-run green |
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

## Current status (2026-07-22)

- **Corpus complete — 36/36 v3 files** (`mie_v3/*.yaml`), **302 examples**, every enumeration route
  independently re-verified live, all authored under §4.6. Byte reductions **29–65%**. 2 hand-authored
  pilots + 34 delegated one-agent-per-DB, each caller-re-validated (never trusting the builder's own
  Phase-5 check). Authoring + live-verify caught real v2 errors across the corpus (chebi role-IRI
  mislabel, mediadive 6-vs-12-value CV, rhea dropped-`rhea:side` cross-join, pdb EC-prefix over-match,
  clinvar gene-bnode split, …).
- **q066 arc closed.** The keyword-enumeration regression is fixed (spec §4.4 + a first-class
  `keyword_enum` example), then **de-overfit** per §4.6 (the example now uses SH3 domain, *not* the
  benchmark's LIM domain), and a **transfer re-run confirmed the route generalizes** — de-overfit v3
  lands LMO7/50 on all 3 runs (score 18, no LIM-domain entity in the MIE). See `smoke/FINDINGS.md`.
- **Two authoring rules emerged from the smoke and are now in the spec:** §4.4 (a positive route is
  not a caveat) and §4.6 (illustrative subjects must not be benchmark entities — no test leakage),
  each with a Phase-5 checklist item (8 and 9). Also landed this cycle: a benchmark token-accounting
  fix so the redesign's input-byte win is measurable (cache buckets — see `smoke/FINDINGS.md`).

**Next:** step 5 — the batched 100Q equivalence run (harness ready; see the step 5 row).

## Files

- `README.md` — this plan/status.
- `MIE_v3_spec.md` — the v3 format contract (incl. §4.4 enumeration rule, §4.6 no-test-leakage).
- `enumeration_audit.md` — per-DB §4.4 enumeration-route checklist (all 36 DBs; drove step-4 authoring).
- `mie_v3/<db>.yaml` — new-format MIEs (**all 36 complete**).
- `smoke/FINDINGS.md` — durable record of the smoke test + q066 fix/de-overfit/transfer + token fix.
- `release/` — step-5 equivalence run: `README.md` (runbook), `canary_questions.txt` (locked 10-Q
  canary), and outputs (regenerable `results_*` gitignored; `FINDINGS.md` will hold the durable numbers).
