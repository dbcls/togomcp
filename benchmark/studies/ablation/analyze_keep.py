#!/usr/bin/env python3
"""Leave-one-in analysis: is each MIE group SUFFICIENT alone?

Pairs each keep_<group> (only that group's sections served) against the existing
no_mie (floor) and baseline (ceiling) in results_groups/:
  sufficiency  = keep_X - no_mie   (how much group X ALONE lifts above no-MIE)
  complement   = baseline - keep_X (what the OTHER two groups add on top of X)
  fraction     = sufficiency / (baseline - no_mie)   (share of the whole-MIE gap X recovers)

Both score (togomcp_total_score) and exact-answer correctness, paired per question
with a 95% CI (reuses ablation_analysis). keep_X, baseline, no_mie are all the
1-judge / 3-answer primary batch, so they pair cleanly. Prints a report; run by the
detached watcher into results_groups/keep_analysis_result.txt on sweep completion.
"""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ablation_analysis as A

R = HERE / "results_groups"
KEEPS = ["keep_query", "keep_guardrails", "keep_orientation"]
gold = A.load_gold()

def _present(cond, scored=True):
    return (R / f"{cond}-scored.csv").exists()

def score_delta(a_cond, b_cond, exclude):
    """mean(a - b) on togomcp_total_score, paired."""
    a = A.load_scores(R / f"{a_cond}-scored.csv", ["togomcp_total_score"])
    b = A.load_scores(R / f"{b_cond}-scored.csv", ["togomcp_total_score"])
    qids = [q for q in (a.keys() & b.keys()) - exclude
            if a[q]["togomcp_total_score"] is not None and b[q]["togomcp_total_score"] is not None]
    d = [a[q]["togomcp_total_score"] - b[q]["togomcp_total_score"] for q in qids]
    st = A._delta_stats(d)
    st["z"] = st["mean"] / (st["ci95"] / 1.96) if st.get("ci95") else float("nan")
    return st

def corr_delta(a_cond, b_cond, exclude):
    a = A.load_correctness(a_cond, gold, 0.10, R)
    b = A.load_correctness(b_cond, gold, 0.10, R)
    qids = (a.keys() & b.keys()) - exclude
    d = [a[q] - b[q] for q in qids]
    st = A._delta_stats(d)
    st["z"] = st["mean"] / (st["ci95"] / 1.96) if st.get("ci95") else float("nan")
    return st

def main():
    for c in ("baseline", "no_mie"):
        if not _present(c):
            print(f"MISSING {c}-scored.csv — cannot pair. Abort."); return 1
    done = [k for k in KEEPS if _present(k)]
    print(f"leave-one-in analysis — keep conditions present: {done or 'NONE YET'}")
    if not done:
        print("no keep_* scored CSVs yet."); return 1

    # ceiling/floor exclusion off the baseline score (matches the trimmed group analysis)
    bs = A.load_scores(R / "baseline-scored.csv", ["togomcp_total_score"])
    auto = {q for q, r in bs.items() if r.get("togomcp_total_score") is not None
            and (r["togomcp_total_score"] >= 20 or r["togomcp_total_score"] <= 12)}

    whole = score_delta("baseline", "no_mie", set())       # the +0.9 gap to recover
    wc = score_delta("baseline", "no_mie", auto)
    print(f"\nwhole-MIE gap (baseline - no_mie): untrimmed {whole['mean']:+.2f} ± {whole['ci95']:.2f}"
          f"  |  trimmed {wc['mean']:+.2f} ± {wc['ci95']:.2f}\n")

    for trim, ex, lab in [("untrimmed", set(), ""), ("trimmed", auto, f"(-{len(auto)})")]:
        gap = whole["mean"] if not ex else wc["mean"]
        print(f"===== {trim} {lab} =====")
        print(f"{'group':16} {'suff=keep-no_mie':>22} {'z':>5} {'%gap':>6}   "
              f"{'compl=base-keep':>18} {'corr(keep-no_mie)':>20}")
        for k in done:
            suff = score_delta(k, "no_mie", ex)
            comp = score_delta("baseline", k, ex)
            cor = corr_delta(k, "no_mie", ex)
            frac = 100 * suff["mean"] / gap if gap else float("nan")
            sig = "*" if suff.get("ci95") and abs(suff["mean"]) > suff["ci95"] else " "
            print(f"{k:16} {suff['mean']:+8.2f} ± {suff['ci95']:.2f}{sig}  {suff['z']:+5.2f} "
                  f"{frac:5.0f}%   {comp['mean']:+7.2f} ± {comp['ci95']:.2f}   "
                  f"{cor['mean']:+.3f} ± {cor['ci95']:.3f}")
        print()
    print("READ: sufficiency * = CI excludes 0 (group X alone beats no-MIE). "
          "%gap = share of the +0.9 whole-MIE effect that X alone recovers. "
          "Prediction: keep_query recovers most; keep_guardrails ~0.")
    print("\nANALYSIS_COMPLETE")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
