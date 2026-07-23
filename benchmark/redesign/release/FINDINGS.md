# Step 5 — equivalence run FINDINGS (durable)

Regenerable `results_rel_*/` dirs are gitignored; this file holds the durable numbers + decisions.

## Step 5a — the CANARY (10 risk-first Q, ×3, smoke_v2 vs full_v3, API answer+judge)

Run 2026-07-22, `results_rel_canary/` (250.7 min, ~$34).

### Validity
All 60 cells succeeded with tool calls **except one**: `q061 full_v3 run-1` timed out (exhausted 3
retries, ~372 s/attempt; `succ=False`, 0 tool calls) — a transient per-call timeout on a heavy
question, correctly flagged so it can't pose as a real answer. Excluded from scoring. **0 login-error
stubs.** Gate passes (the one bad cell is a timeout on the v2-equivalent heavy question, not a corpus
defect; q061's 2 valid runs are +1.8 for v3).

### Scores (valid cells; v3−v2 paired per question)
| Q | DBs | v2 runs | v2μ | v3 runs | v3μ | Δ |
|---|---|---|---|---|---|---|
| q002 | uniprot+go | 20,18,19 | 19.0 | 20,19,20 | 19.7 | +0.7 |
| q006 | chembl+pdb+uniprot | 11,11,14 | 12.0 | 15,13,15 | 14.3 | +2.3 |
| q011 | pubchem+rhea+chebi | 18,17,17 | 17.3 | 16,20,18 | 18.0 | +0.7 |
| q014 | go+taxonomy+uniprot | 19,19,18 | 18.7 | 18,19,18 | 18.3 | −0.3 |
| q022 | go+glycosmos | 19,19,13 | 17.0 | 11,12,11 | 11.3 | **−5.7** |
| q027 | reactome+uniprot+rhea | 13,11,13 | 12.3 | 10,11,11 | 10.7 | −1.7 |
| q031 | uniprot+rhea | 16,18,17 | 17.0 | 15,13,15 | 14.3 | −2.7 |
| q043 | rhea+chebi | 20,19,19 | 19.3 | 20,20,20 | 20.0 | +0.7 |
| q061 | brenda+massbank | 14,11,13 | 12.7 | 15,14 (r1 timeout) | 14.5 | +1.8 |
| q071 | uniprot+ensembl+mogplus | 4,4,13 | 7.0 | 4,4,4 | 4.0 | −3.0 |

**Overall paired Δ = −0.72/20** (outside the ±0.5 margin) — but **driven almost entirely by q022**.

### Regression scan (v3 below v2 on every run — the q066 signature)
- **q022 (−5.7) — REAL, systematic, now FIXED (see below).**
- q027 (−1.7), q031 (−2.7): NOT clean regressions — *both arms* are wrong (q031: both mostly 136 vs
  gold 128; q027: both under-enumerate, max 28 vs gold 58). v3 loses a little on answer detail, not on
  a lost capability. Noise-band; revisit only if the full 100Q flags them.
- q071: bad canary item — near-identical 420-char answers scoring ~4/20 in **both** arms; its −3.0
  rides on one lucky v2 run (13). Question-quality artifact, not v3.

## q022 root cause + fix (the canary's job — glycosmos is Tier-A)

**Question:** distinct human glycogenes in GlyCosmos annotated to GO:0009101 *or any descendant* (gold **208**, 32 descendants).

**Root cause (subtler than "v3 lost a route"):** the GlyCosmos endpoint's OWN embedded
`GRAPH <http://purl.obolibrary.org/obo/go.owl>` is a **partial/divergent GO snapshot**. Its
`subClassOf*` closure for GO:0009101 yields only **14** terms → **44 genes** — which is exactly what
v3 computed. v3 was self-consistent on glycosmos; it trusted a deficient local hierarchy. The gold 208
needs the **authoritative full GO** (33 terms). Verified natively:
- `go` RDF database (RDF Portal): `subClassOf*` GO:0009101 = **33 terms**.
- VALUES those 33 IRIs into the glycosmos glycogenes reverse-GO join = **208** (matches gold exactly).
- v2 reached 208 only by fetching GO externally (`mcp__ols__getDescendants` + Bash) — and was unstable
  (run 3 fell to 44).

**Fix (`mie_v3/glycosmos.yaml`, 2026-07-22):** added first-class §4.4 example `enum_go_descendants` —
the "GO term **or its descendants**" enumeration is a **two-database recipe**: (1) expand with
`rdfs:subClassOf*` on the native **`go`** database to get descendant IRIs, (2) VALUES-join to
glycogenes. §4.6-safe demonstrator: **GO:0006493** (O-linked glycosylation), *not* q022's GO:0009101 —
verified **121** via `go` vs **100** via the deficient local go.owl. Two `traps_avoided` forbid using
the embedded go.owl for descendant expansion. Byte footer refreshed (61.6% vs v2).

**Fix verified (`results_rel_q022fix/`, 2026-07-22, 15.1 min, ~$3):**
| | v2 | v3 |
|---|---|---|
| q022 after fix | 17.0 (19,19,13) | **18.0 (18,18,18)** |
- v3 lands **208 on all 3 runs** (was 44/44/44), using **only native `run_sparql`** (go-expansion +
  glycosmos VALUES) — no Bash, no OLS4. The MIE example alone drove it.
- v3 is now **more stable than v2** here (v2 run 3 still collapses to 44).
- q022 Δ: **−5.7 → +1.0**.

**Recomputed canary overall Δ (q022 fixed): ≈ −0.05/20** — flat, within ±0.5. **Canary is clean.**

## Go/no-go
Canary **GREEN after the glycosmos fix**. A clean risk-first canary is strong evidence against a gross
break but is not the ±0.5/20 verdict — that needs the full 100. **Proceed to step 5b (the remaining 90
in 25-QA batches).** Watch q027/q031 in their batch; if the both-arms-weak pattern holds they're noise.

## Step 5b — batch 1 (q001–q032 minus canary; 25 Q, ×3, API)

Run 2026-07-22→23, `results_rel_batch1/` (431.7 min ≈ 7.2h). **0 invalid cells** (no timeouts, no stubs).

- **Batch-1 paired Δ = +1.31/20** (v3 16.56 vs v2 15.25). better/tie/worse (|Δ|>0.5): **13/4/8**.
- v3's wins largely come from *fixing v2's flaky cases*: q008 +7.3, q018 +10.3, q020 +4.3, q019 +3.7,
  q012 +3.3 (v2 had runs scoring 4 on q008/q018/q032; v3 stable).
- Regression-signature (v3 below v2 all runs) — all NOISE-BAND, not route defects:
  - q026 (−4.0): v3 found every fact (CID 168989, CHEBI:17601, RHEA:20772, EC 2.5.1.9) but 2/3 runs
    mis-concluded "No" on a compound-vs-class semantic technicality. r2 got the correct "Yes" (18).
  - q021 (−1.7): hard multi-part proteasome summary; BOTH arms fabricate exact sub-counts (v2 16/14/14,
    v3 14/13/12). Inherently fabrication-prone, not a missing route.
  - q010 (−1.3): v3 picks the CORRECT multiple-choice answer (immune system disorder) but reports a
    less-precise supporting count (471 vs gold 240). Core answer right.

**Batch-1 gate: PASS / GO** — v3 above v2, 0 invalid, no systematic q022-style regression.

## Cumulative (n=35: canary 10 + batch1 25, folded into results_release; fixed q022 seeded first)

- **Overall paired Δ = +0.92/20** (v3 16.18 vs v2 15.25). better/tie/worse: **19/5/11**.
- Regression-signature set = q010,q021,q026 (batch1) + q027,q031 (canary) — all diagnosed noise-band
  (reasoning/precision variance or both-arms-weak), none a corpus defect.
- 1 invalid cell total: q061 v3 r1 (the one canary timeout), correctly excluded.
- CI ladder: 10 → **35** done. v3 leads by ~+0.9/20 — tracking well above the "flat within ±0.5" bar.

## Step 5b — batch 2 (q033–q048; 15 Q, ×3, API)

Run 2026-07-23, `results_rel_batch2/` (243.5 min ≈ 4.1h). Ran as **15 Q** (user narrowed from 25).

- **Raw** paired Δ = −0.27/20 (v3 15.16 vs v2 15.42); no regression-signature.
- **NEW failure mode — spurious AUP refusals** ("…appears to violate our Usage Policy"): **28 refusal
  cells this batch, balanced 14 v3 / 14 v2** (no bias). Benign microbiology questions the content
  classifier false-positives on. **q034 and q044 refused on ALL 6 cells** (both arms) → they measure
  nothing (4/4/4 floor). **q033 refused 3/6** → the entire −5.3 artifact; its clean cells are equivalent.
- **Clean** (refusal + succ=False cells excluded): paired Δ = **−0.05/20** over 13 usable Q
  (v3 17.57 vs v2 17.53) — dead flat, within equivalence.

**Batch-2 gate: PASS** — clean Δ ≈ 0; the raw negative tilt was refusal-noise (unlucky 2-vs-1 split on
q033), not a corpus defect. No regression signature on clean cells.

## Cumulative (n=50: canary + batch1 + batch2, folded into results_release)

- **Raw**: paired Δ = **+0.56/20** (v3 15.87 vs v2 15.30), better/tie/worse 23/11/16.
- **Clean** (refusals excluded, 46 usable Q): paired Δ = **+0.34/20** (v3 17.10 vs v2 16.77), 21/10/15.
- Both PASS the "flat within ±0.5" bar and tilt slightly positive — v3 ≥ v2.
- **Refusal contamination is corpus-wide** (balanced across arms): fully-refused questions so far =
  q032, q034, q044, q071. NB **q071's canary "bad question" (identical 420-char answers) was the
  refusal message** — not a real v3/v2 difference. These are excluded from the clean verdict; effective
  n is reduced but the equivalence conclusion is unchanged.
- CI ladder: 10 → 35 → **50** done. v3 tracking at-or-above v2 on both raw and clean.
