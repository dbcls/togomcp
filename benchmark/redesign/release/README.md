# Step 5 — full-corpus equivalence run (runbook)

The v3 release gate: does the **full v3 corpus** answer the 100 benchmark questions *at least as
well* as production v2, for far fewer tokens? Run **batched with a review gate**, not all at once
(the batching is what caught q066 cheaply in the smoke). Durable numbers land in `FINDINGS.md` here;
the `results_rel_*/` dirs are regenerable and gitignored.

## Conditions (already registered + staged)
- **`smoke_v2`** = the v2 arm. Already the full production corpus, byte-identical to
  `togo_mcp/data/mie/` (verified). Reused as-is.
- **`full_v3`** = the v3 arm. `benchmark/ablation/mie_variants/full_v3/` (gitignored) is a copy of
  `benchmark/redesign/mie_v3/` — all 36 v3 files, de-overfit uniprot (SH3, not LIM). Registered in
  `run_ablation.py` as `RELEASE_CONDITIONS`.
- Re-stage `full_v3` if `mie_v3/` changes: `cp ../mie_v3/*.yaml ../../ablation/mie_variants/full_v3/`.

## Auth: API (decided) — reliable, needed for batches
Subscription degrades into login-error stubs under batch load (the runner mislabels them
success=True), which would silently corrupt the equivalence. Use `--answer-use-api --judge-use-api`
with `ANTHROPIC_API_KEY`. The server also needs `NCBI_API_KEY`. Rough cost/time (from the smoke's
$85 / 8.1h per 25×3×2): **canary (10Q) ≈ $34 / ~3h; each 25-QA batch ≈ $80 / ~8h.**

## Step 5a — the CANARY (locked, run this first)
10 risk-first questions (`canary_questions.txt`): all **factoid with verifiable numeric/specific
answers**, enumeration-heavy, spanning **14 DBs** incl. 3 of the 4 Tier-A (glycosmos q022, pubchem
q011, mogplus q071) — so a broken v3 file trips the alarm fast. (ddbj Tier-A omitted: its
taxonomy-subtree route was heavily re-verified during authoring; taxonomy is covered via q014.)

q002 uniprot+go · q006 chembl+pdb+uniprot · q011 pubchem+rhea+chebi · q014 go+taxonomy+uniprot ·
q022 go+glycosmos · q027 reactome+uniprot+rhea · q031 uniprot+rhea · q043 rhea+chebi ·
q061 brenda+massbank · q071 uniprot+ensembl+mogplus.

**Launch:**
```bash
cd benchmark/ablation
export ANTHROPIC_API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' ../../.env | cut -d= -f2- | tr -d '"'"'"')
export NCBI_API_KEY=$(grep -E '^NCBI_API_KEY=' ../../.env | cut -d= -f2- | tr -d '"'"'"')
QARR=(); while read -r q; do [ -n "$q" ] && QARR+=("../questions/$q.yaml"); done < ../redesign/release/canary_questions.txt
uv run --project ../.. python run_ablation.py --conditions smoke_v2,full_v3 \
  --questions "${QARR[@]}" \
  --results-dir "$PWD/../redesign/release/results_rel_canary" \
  --runs 3 --answer-use-api --judge-use-api --port 8974
```

## Review gate (every batch, canary included)
1. **Validity** — reject/redo the batch unless login-error stub count = 0 and `CallToolRequests > 0`.
2. **Paired v3−v2 judge delta** + better/tie/worse distribution (per-run + averaged).
3. **Systematic per-question regression scan** — any question wrong on all 3 v3 runs but right in v2
   (the q066 signature). Eyeball every flagged answer against the gold.
4. **Go/no-go.** Clean canary → proceed to the 25-QA batches. Trips → diagnose before spending the
   rest (exactly how the smoke stopped at q066).

## Step 5b — the remaining 90, in 25-QA batches
The canary's 10 count toward the 100. Run the rest as batches (both conditions each, `--runs 3`) into
`results_rel_batchN/`, then fold: `python append_results.py results_rel_batchN results_release`
(keyed by question_id, idempotent — overlaps skipped). Re-run `python ablation_analysis.py` on
`results_release` after each fold; the CI tightens 10 → 35 → 60 → 85 → 100.

## Final call at 100Q (the equivalence criteria)
- tokens/bytes **down** — deterministic (already known: 29–65% smaller files).
- judge score **flat within ~±0.5/20** — must not regress.
- factoid correctness **up-or-flat** — tests the aggregation-recipe claim.

A clean risk-first canary is strong evidence against a gross break but is **not** the verdict (it
tested the hard questions); the ±0.5/20 call needs the full 100.
