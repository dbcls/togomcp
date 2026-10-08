#!/usr/bin/env python3
"""Inter-judge agreement between two judges that scored the SAME answer files.

For each condition, pass the two judges' scored CSVs (one per replicate, same order):

    python judge_agreement.py \\
        --cond baseline 'results_v3_stage1/baseline-scored-v?.csv' 'results_v3_stage1/gemma4/baseline-scored-gemma4-v?.csv' \\
        --cond no_mie   '.../no_mie-scored-v?.csv' '.../gemma4/no_mie-scored-gemma4-v?.csv' \\
        --reference baseline --names claude-opus-4-8 gemma4 --out agreement.md

Cells are matched by (replicate, question_id, arm), arm = TogoMCP or no-tool answer. Refusals
and stubs (answer_screen.py) and failed judgements (score 0) are dropped from both judges.

Reported per condition and pooled:
  * Pearson and Spearman on cell totals and on per-question means
  * ICC(2,1) (absolute agreement) and ICC(3,1) (consistency), two raters, cell totals
  * per criterion (recall, precision, repetition, readability): exact-agreement rate,
    within-1 rate, Pearson, mean offset
  * systematic offset (judge A minus judge B) per arm, with 95% CI
  * TogoMCP - no-tool delta under each judge, and, with --reference, each condition's
    paired delta against the reference condition under each judge: does its SIGN agree?
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_screen import classify  # noqa: E402

CRITERIA = ("recall", "precision", "repetition", "readability")
ARMS = (("togomcp", "TogoMCP"), ("baseline", "no-tool"))


def load(pattern: str) -> dict:
    """(rep, qid, arm) -> {'total': float, crit: float...} for valid, judged cells."""
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"no files match {pattern}")
    out = {}
    for rep, f in enumerate(files, 1):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                for arm, _ in ARMS:
                    if classify(r.get(f"{arm}_answer"), r.get(f"{arm}_success")) != "valid":
                        continue
                    try:
                        tot = float(r[f"{arm}_total_score"])
                    except (KeyError, ValueError):
                        continue
                    if tot <= 0:
                        continue
                    cell = {"total": tot}
                    for c in CRITERIA:
                        try:
                            cell[c] = float(r[f"{arm}_{c}"])
                        except (KeyError, ValueError):
                            pass
                    out[(rep, r["question_id"], arm)] = cell
    return out


def pearson(x, y):
    if len(x) < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else None


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    return pearson(ranks(x), ranks(y)) if len(x) >= 3 else None


def icc(x, y):
    """ICC(2,1) and ICC(3,1) for two raters (Shrout & Fleiss)."""
    n, k = len(x), 2
    if n < 3:
        return None, None
    rows = list(zip(x, y))
    grand = st.mean(x + y)
    row_m = [st.mean(r) for r in rows]
    col_m = [st.mean(x), st.mean(y)]
    ss_r = k * sum((m - grand) ** 2 for m in row_m)
    ss_c = n * sum((m - grand) ** 2 for m in col_m)
    ss_t = sum((v - grand) ** 2 for r in rows for v in r)
    ss_e = ss_t - ss_r - ss_c
    ms_r, ms_c, ms_e = ss_r / (n - 1), ss_c / (k - 1), ss_e / ((n - 1) * (k - 1))
    icc2 = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e + k * (ms_c - ms_e) / n)
    icc3 = (ms_r - ms_e) / (ms_r + (k - 1) * ms_e)
    return icc2, icc3


def mean_ci(d):
    if len(d) < 2:
        return None, None
    return st.mean(d), 1.96 * st.stdev(d) / math.sqrt(len(d))


def qmeans(cells, arm):
    by = defaultdict(list)
    for (rep, q, a), c in cells.items():
        if a == arm:
            by[q].append(c["total"])
    return {q: st.mean(v) for q, v in by.items()}


def f(v, p=2):
    return "n/a" if v is None else f"{v:.{p}f}"


def fs(v, p=2):
    return "n/a" if v is None else f"{v:+.{p}f}"


def section(name, A, B, na, nb):
    common = sorted(set(A) & set(B))
    L = [f"## {name}", "", f"{len(common)} cells judged validly by both "
         f"({len(set(A) - set(B))} only by {na}, {len(set(B) - set(A))} only by {nb})."]
    xa = [A[k]["total"] for k in common]
    xb = [B[k]["total"] for k in common]
    i2, i3 = icc(xa, xb)
    L += ["", "| Level | n | Pearson | Spearman | ICC(2,1) | ICC(3,1) |", "|---|---:|---:|---:|---:|---:|",
          f"| cells, both arms | {len(common)} | {f(pearson(xa, xb))} | {f(spearman(xa, xb))} | "
          f"{f(i2)} | {f(i3)} |"]
    for arm, label in ARMS:
        ma, mb = qmeans({k: A[k] for k in common}, arm), qmeans({k: B[k] for k in common}, arm)
        qs = sorted(set(ma) & set(mb))
        x, y = [ma[q] for q in qs], [mb[q] for q in qs]
        j2, j3 = icc(x, y)
        L.append(f"| question means, {label} | {len(qs)} | {f(pearson(x, y))} | {f(spearman(x, y))} | "
                 f"{f(j2)} | {f(j3)} |")
    L += ["", f"Per criterion (cells, both arms; offset = {na} − {nb}):", "",
          "| Criterion | Exact | Within 1 | Pearson | Offset |", "|---|---:|---:|---:|---:|"]
    for c in CRITERIA:
        ks = [k for k in common if c in A[k] and c in B[k]]
        a = [A[k][c] for k in ks]
        b = [B[k][c] for k in ks]
        if not ks:
            continue
        L.append(f"| {c} | {sum(p == q for p, q in zip(a, b)) / len(ks):.0%} | "
                 f"{sum(abs(p - q) <= 1 for p, q in zip(a, b)) / len(ks):.0%} | {f(pearson(a, b))} | "
                 f"{fs(st.mean(p - q for p, q in zip(a, b)))} |")
    L += ["", "| Arm | Mean " + na + " | Mean " + nb + " | Offset (95% CI) |", "|---|---:|---:|---:|"]
    for arm, label in ARMS:
        ks = [k for k in common if k[2] == arm]
        m, ci = mean_ci([A[k]["total"] - B[k]["total"] for k in ks])
        L.append(f"| {label} | {f(st.mean(A[k]['total'] for k in ks))} | "
                 f"{f(st.mean(B[k]['total'] for k in ks))} | {fs(m)} ± {f(ci)} |")
    deltas = {}
    for nm, J in ((na, A), (nb, B)):
        mt, mbase = qmeans({k: J[k] for k in common}, "togomcp"), qmeans({k: J[k] for k in common}, "baseline")
        qs = sorted(set(mt) & set(mbase))
        deltas[nm] = {q: mt[q] - mbase[q] for q in qs}
    L += ["", "TogoMCP − no-tool Δ (per-question means, paired):", "", "| Judge | Δ (95% CI) | n |",
          "|---|---:|---:|"]
    for nm in (na, nb):
        m, ci = mean_ci(list(deltas[nm].values()))
        L.append(f"| {nm} | {fs(m)} ± {f(ci)} | {len(deltas[nm])} |")
    return L, mt_by_judge(A, B, common, na, nb)


def mt_by_judge(A, B, common, na, nb):
    """per judge: question -> TogoMCP mean, for the cross-condition sign test."""
    return {na: qmeans({k: A[k] for k in common}, "togomcp"),
            nb: qmeans({k: B[k] for k in common}, "togomcp")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cond", nargs=3, action="append", metavar=("NAME", "JUDGE_A_GLOB", "JUDGE_B_GLOB"),
                    required=True)
    ap.add_argument("--names", nargs=2, default=["judge A", "judge B"])
    ap.add_argument("--reference", help="condition whose TogoMCP scores the others are paired against")
    ap.add_argument("--out", help="markdown output (default: stdout)")
    args = ap.parse_args()
    na, nb = args.names
    L = [f"# Judge agreement: {na} vs {nb}", ""]
    pooled_a, pooled_b, tm = {}, {}, {}
    for name, ga, gb in args.cond:
        A, B = load(ga), load(gb)
        sec, tm[name] = section(name, A, B, na, nb)
        L += sec + [""]
        pooled_a.update({(name,) + k: v for k, v in A.items()})
        pooled_b.update({(name,) + k: v for k, v in B.items()})
    if len(args.cond) > 1:
        common = sorted(set(pooled_a) & set(pooled_b))
        x, y = [pooled_a[k]["total"] for k in common], [pooled_b[k]["total"] for k in common]
        i2, i3 = icc(x, y)
        L += ["## Pooled over conditions", "", f"{len(common)} cells: Pearson {f(pearson(x, y))}, "
              f"Spearman {f(spearman(x, y))}, ICC(2,1) {f(i2)}, ICC(3,1) {f(i3)}.", ""]
    if args.reference:
        ref = tm[args.reference]
        L += [f"## Condition effects vs {args.reference} (TogoMCP arm, paired by question)", "",
              f"| Condition | {na} | {nb} | Same sign? |", "|---|---:|---:|---|"]
        # "Same sign?" is only asked when at least one judge's 95% CI excludes zero.
        for name in tm:
            if name == args.reference:
                continue
            res = {}
            for nm in (na, nb):
                qs = sorted(set(tm[name][nm]) & set(ref[nm]))
                res[nm] = mean_ci([tm[name][nm][q] - ref[nm][q] for q in qs])
            (ma, ca), (mb, cb) = res[na], res[nb]
            if ma is None or mb is None:
                same = "n/a"
            elif abs(ma) <= (ca or 0) and abs(mb) <= (cb or 0):
                same = "n.s. under both"        # neither CI excludes 0: no sign to agree on
            elif (ma > 0) == (mb > 0):
                same = "yes"
            else:
                same = "**NO**"
            L.append(f"| {name} | {fs(ma)} ± {f(ca)} | {fs(mb)} ± {f(cb)} | {same} |")
    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
