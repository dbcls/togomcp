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

## Token savings: not measurable from this harness
The v3 files are 62–64% smaller (uniprot 57→21 KB, bacdive 50→19 KB — the deterministic win, measured
directly). But the harness's `togomcp_input_tokens` (~434) is far too small to include a MIE read, so
it does **not** capture cumulative context and can't confirm the runtime token reduction. A
logging limitation, not a redesign result.

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
