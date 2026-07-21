# MIE v3 Smoke Test — Findings (2026-07-21/22)

Durable record of the first *measured* signal on the MIE v3 redesign: a 2-corpus A/B that
swaps only `uniprot.yaml` + `bacdive.yaml` for their v3 rewrites and asks whether the
benchmark questions those DBs answer regress. The raw `results/` CSVs are gitignored
(regenerable only at ~$85 / ~8h); the numbers that matter are here.

## What was run

| | |
|---|---|
| Design | 2 conditions (`smoke_v2` = full v2.x corpus · `smoke_v3` = same but uniprot+bacdive → v3) × **25 questions** × **3 replicates** |
| Questions | the 25 **two-DB** questions where uniprot or bacdive is one of exactly two DBs (swapped MIE = 50% of the DB content → strongest per-question signal). `smoke_questions.txt`. |
| Answering / Judge | `claude-sonnet-4-5` / eval-default (Opus), **Anthropic API** (`--answer-use-api --judge-use-api`) |
| Harness | `run_ablation.py --conditions smoke_v2,smoke_v3` (new `SMOKE_CONDITIONS`); corpora served via `TOGOMCP_MIE_DIR` |
| Wall / validity | 485.6 min (8.1h); CallToolRequests **953 / 1003** per condition; **0** login-error stubs |

**Prereq — two server shims** (`togo_mcp/rdf_portal.py`, needed for release anyway per redesign
§6 "transition ordering"): v3 renames the sections two functions read, so both now read
new-or-old location — `_load_databases_cache` (`discovery` else `schema_info`) and
`_mie_trap_banner` (`global_gotchas`/`graphs.co_hosted` else `critical_warnings`/
`schema_info.co_hosted_graphs`). Unit-tested against a v2 and a v3 file; 28 server tests pass.
Without them the v3 arm would lose discovery + the trap banner and confound the comparison.

## Headline: yellow light — flat on average, but a real localized regression

Paired v3−v2 judge score (n=25): **−0.44 ± 0.82** (95% CI includes 0). No **gross** regression
(within the ~0.5/20 bail bar), so not a red light. But it decomposes non-randomly:

| slice | Δ score (v3−v2) | read |
|---|---:|---|
| **uniprot** (n=20) | **−0.13** | flat — the main rewrite preserves quality on average |
| bacdive (n=5) | −1.66 | small n, mostly q033 variance |
| by type: factoid | −1.09 | multi-step types regress… |
| by type: list | −1.04 | …the hardest questions |
| by type: yes_no / summary | +0.29 / +0.34 | improve |
| distribution | 11 better / 3 tie / 11 worse | symmetric = flat + noise, *except* the movers below |

### The finding that earns the smoke test: q066 is a SYSTEMATIC v3 regression
Q066 (uniprot+jpostdb, factoid — "reviewed human proteins with a LIM domain, most phosphopeptides"):
- **v2** per-run scores [16, 20, 16] — mostly correct (LMO7 / Q8WWI1, matching the gold).
- **v3** per-run scores [12, 13, 13] — **consistently wrong on all 3 runs** (LIMA1 / Q9UHB6; found only
  **14** LIM-domain proteins vs the true **71**).

Not noise — v3 reliably steers the agent to a narrower, wrong protein set for domain-based
enumeration.

**Diagnosis (CONFIRMED, 2026-07-22).** The gold route for "reviewed human proteins with a LIM
domain" is the **keyword** classification `up:classifiedWith keywords:440` (KW-0440). Verified
live, the routes give: **keyword → 71** (correct), Domain_Annotation-text → 25, name-text → 45 —
non-keyword routes silently **undercount**. The v2 uniprot MIE documents keyword classification as
a first-class enumeration route in ~5 places (a critical warning, a sample triple
`up:classifiedWith keywords:1185`, a `cross_references` pattern with ~99% coverage, an
architectural note). The v3 rewrite **collapsed all of that into a single negative caveat** on the
GO example ("up:classifiedWith *also* carries keywords, filter them out") — so the agent reads
keywords as noise to exclude, not as the route to enumerate, and falls back to text/annotation
undercounting. **Fix applied:** a first-class `keyword_enum` example in `mie_v3/uniprot.yaml`
(verified 71) + a generalizable spec rule `MIE_v3_spec.md §4.4` ("a positive route is not a
caveat" / the enumeration rule) protecting all 34 DBs.

### q033 is variance, not a gap
Q033 (bacdive+uniprot, list): v3 per-run [19, 4, 15] — one run nailed it (19), one bombed (4).
v3 *can* do it; it's an unstable hard multi-step question. The bacdive −1.66 mean is mostly this.

## Token savings / dollar cost: NOT reliably measurable from this harness
The v3 files are 62–64% smaller (uniprot 57→21 KB, bacdive 50→19 KB — the deterministic win, measured
directly). The *runtime* saving that should buy is **invisible in this run**:

| metric (75 answers/condition) | v2 | v3 | diff |
|---|---:|---:|---:|
| togomcp cost | $42.17 | $37.58 | **−$4.59 (−11%)** |
| input tokens (sum) | 32,560 | 31,830 | −730 |
| output tokens (sum) | 523,757 | 479,800 | −43,957 (−8%) |

Two reasons the −11% is not a trustworthy "the redesign saves 11%":
1. **The harness under-logs input tokens.** `togomcp_input_tokens` is ~**400/answer** (median 402,
   max 1,668), but one `get_MIE_file(uniprot)` returns 5,000–14,000 tokens — so the field captures
   only a fraction. (Root cause since pinned: the harness recorded only the `input_tokens` field and
   dropped the `cache_creation`/`cache_read` buckets where MIE reads are billed — see the DONE
   follow-up below. Not "final turn only" as first guessed.) The byte-driven **input** saving the
   redesign targets is therefore unmeasured *in this run's data*.
2. **The −11% is an OUTPUT-token effect** (−44K output, not −input), which is answer-variance-
   dependent — possibly a denser MIE → tighter reasoning / fewer failed-query retries, possibly
   noise at n=25×3. Not attributable to the byte savings.

Theoretical input saving (unconfirmed): ~9–10K / ~8K fewer input tokens per uniprot / bacdive MIE
read, ≈ $0.03/query per read at Sonnet input rates × turns-that-carry-the-context — but **prompt
caching** likely discounts a re-read ~10×, which is probably why billed cost barely moves.

**Follow-up (harness) — DONE 2026-07-22.** Root cause was narrower and worse than "final turn only":
`automated_test_runner.py` recorded only the `input_tokens` field of the SDK usage dict and dropped
the two prompt-cache buckets — `cache_creation_input_tokens` and `cache_read_input_tokens` — which is
exactly where a large MIE read is billed. A single-turn probe makes it vivid: `input_tokens: 10` vs
`cache_creation_input_tokens: 20366` on the same call. So the redesign's whole target (input bytes)
was structurally unmeasured, not merely noisy. The old loop also *summed per-turn `AssistantMessage`
usage on top of the cumulative `ResultMessage` usage* — a latent double-count that the missing-cache
under-count happened to mask.

**Fix (in `automated_test_runner.py`):**
- Read cumulative usage from the `ResultMessage` only, and prefer summing its per-turn `iterations`
  ledger (correct whether the top-level figure is a running sum or a last-turn snapshot; kills the
  double-count). Primary-model scope — auxiliary CLI overhead (haiku summarizer) is excluded, as it
  doesn't carry MIE context.
- New CSV columns: `togomcp_cache_creation_tokens`, `togomcp_cache_read_tokens`,
  `togomcp_total_input_tokens` (= input + both cache buckets — **the v2-vs-v3 metric**), mirrored for
  baseline (≈0 there — a clean control). `_calc_cost` fallback is now cache-aware; the CLI's
  `total_cost_usd` is still preferred and was already correct.
- `run_ablation.py` needs no change (dynamic-fieldname averaging); `add_llm_evaluation.py` passes the
  columns through (pandas read→write). Helpers unit-tested (single-turn, multi-turn sum, fallback).

The next targeted re-run (item 1 below) will therefore *measure* the input-byte win in
`togomcp_total_input_tokens`; USD stays the secondary metric because prompt-cache discounting masks it
(the ablation FINDINGS flagged the same whole-loop gap — `tools_used` records names only).

## Verdict & next step

The smoke test did exactly its job: **it caught, cheaply and at 2 DBs, a concrete failure mode**
before the full-corpus build — v3 compression can drop query-guidance that matters for hard
enumeration questions, and it did so *systematically* on q066. uniprot is flat on average (−0.13),
so this is a targeted authoring gap, not a broken format.

**Diagnosis + fix DONE (2026-07-22)** — see the confirmed diagnosis above. The lesson is now spec
rule §4.4 (a positive route is not a caveat) + checklist item 8, and the uniprot pilot has a
`keyword_enum` example. **Remaining before scaling to the 34-DB corpus:**
1. Re-verify the fix lands in the agent loop — a cheap targeted re-run of just q066 (and the other
   uniprot enumeration questions) on the patched v3 corpus should recover to v2 parity. (Not yet
   done — the full 25-question re-run is only worth it once more DBs change.)
2. Apply §4.4 when authoring the full corpus: every DB with a controlled-vocabulary enumeration
   route needs a set-level example.

## Reproduce

```bash
# corpora + questions (regenerates corpus_v2/, corpus_v3/, smoke_questions.txt):
#   see the build steps in this dir's git history / the two-DB selection in the README analysis.
cd benchmark/ablation
export ANTHROPIC_API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' ../../.env | cut -d= -f2- | tr -d '"'"'"')
QARR=(); while read -r q; do [ -n "$q" ] && QARR+=("../questions/$q.yaml"); done < ../redesign/smoke/smoke_questions.txt
python run_ablation.py --conditions smoke_v2,smoke_v3 --questions "${QARR[@]}" \
  --results-dir "$PWD/../redesign/smoke/results" --runs 3 --answer-use-api --judge-use-api --port 8974
```
(Stage `mie_variants/smoke_v2` = full v2 corpus and `mie_variants/smoke_v3` = same + v3 uniprot/bacdive first.)
