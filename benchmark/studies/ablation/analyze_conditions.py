#!/usr/bin/env python3
"""Compare ablation conditions against a reference, from the replicate scored CSVs (v3 sweeps).

The v2 tool (ablation_analysis.py) is organized around the 11 v2 sections; this one takes any
condition names, so it serves the v3 stage-1 design (baseline, ablate_examples, keep_examples,
no_mie) and control runs alike. It reads <cond>-scored-v*.csv (or <cond>-scored.csv for a
--runs 1 sweep), NOT the merged averages, so every number is available both raw and with
content-policy refusals / stubs / failed judgements removed (answer_screen.py).

For each condition C against the reference R, on the TogoMCP arm, paired by question
(per-question mean over that question's valid replicates):

    effect = mean(C - R)   negative = C scores lower than R

with a 95% CI, z, and whether |z| clears the Bonferroni bar for the number of planned
comparisons. Also: the same effect raw; trimmed (questions whose reference score sits at the
ceiling or floor removed); split by held-out vs development and by question type; on the
recall and precision criteria; on effort (SPARQL calls, tool calls, time, cost); on
exact-answer correctness; and, with --judge2, under a second judge that scored the same
answers. --pair A B adds a direct A - B comparison (e.g. keep_examples vs no_mie).

Usage:
    python analyze_conditions.py --results results_v3_stage1 \\
        --reference baseline --conditions ablate_examples keep_examples no_mie \\
        --pair keep_examples no_mie --judge2 'gemma4/{cond}-scored-gemma4-v*.csv' gemma4
"""
from __future__ import annotations

import argparse
import csv
import glob
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from answer_screen import classify  # noqa: E402
from ablation_analysis import (_bonferroni_z, _delta_stats, _effort_from_row,  # noqa: E402
                               grade_exact, load_gold)

QUESTIONS = HERE.parents[1] / "questions"
CRITERIA = ("recall", "precision")
EFFORT = (("n_sparql", "SPARQL calls"), ("n_tools", "tool calls"), ("wall_s", "time (s)"),
          ("cost", "cost (USD)"))


def load_condition(files: list[str], gold: dict, tol: float, clean: bool) -> tuple[dict, Counter]:
    """question_id -> per-question means over valid replicates, plus cell counts."""
    cells = Counter()
    per = defaultdict(lambda: defaultdict(list))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                qid = r.get("question_id")
                if not qid:
                    continue
                cls = classify(r.get("togomcp_answer"), r.get("togomcp_success"))
                try:
                    total = float(r.get("togomcp_total_score") or 0)
                except ValueError:
                    total = 0.0
                if total <= 0:
                    cells["judge_failed"] += 1
                    continue
                cells[cls] += 1
                if clean and cls != "valid":
                    continue
                d = per[qid]
                d["total"].append(total)
                for c in CRITERIA:
                    try:
                        d[c].append(float(r[f"togomcp_{c}"]))
                    except (KeyError, ValueError):
                        pass
                for k, v in _effort_from_row(r).items():
                    d[k].append(v)
                g = gold.get(qid)
                if g:
                    ok = grade_exact(r.get("togomcp_answer"), g["type"], g["exact"], tol)
                    if ok is not None:
                        d["correct"].append(ok)
    return {q: {k: mean(v) for k, v in d.items() if v} for q, d in per.items()}, cells


def files_for(results: Path, cond: str, pattern: str | None = None) -> list[str]:
    if pattern:
        return sorted(glob.glob(str(results / pattern.format(cond=cond))))
    files = sorted(glob.glob(str(results / f"{cond}-scored-v*.csv")))
    if not files and (results / f"{cond}-scored.csv").exists():
        files = [str(results / f"{cond}-scored.csv")]
    return files


def effect(a: dict, b: dict, key: str = "total", restrict: set | None = None) -> dict:
    """paired stats of a - b over questions present in both"""
    qs = [q for q in a.keys() & b.keys() if key in a[q] and key in b[q]
          and (restrict is None or q in restrict)]
    st = _delta_stats([a[q][key] - b[q][key] for q in qs])
    st["a"] = mean(a[q][key] for q in qs) if qs else None
    st["b"] = mean(b[q][key] for q in qs) if qs else None
    st["z"] = st["mean"] / st["se"] if st.get("se") else None
    return st


def f(v, spec="+.2f"):
    return "n/a" if v is None else format(v, spec)


def pm(st, spec="+.2f"):
    return "n/a" if st["mean"] is None else f"{st['mean']:{spec}} ± {f(st['ci95'], '.2f')}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--reference", default="baseline")
    ap.add_argument("--conditions", nargs="+", required=True)
    ap.add_argument("--pair", nargs=2, action="append", default=[], metavar=("A", "B"),
                    help="extra direct comparison A - B (repeatable)")
    ap.add_argument("--judge2", nargs=2, metavar=("PATTERN", "NAME"),
                    help="second judge's files, relative to --results, with {cond} placeholder")
    ap.add_argument("--judge-name", default="claude-opus-4-8")
    ap.add_argument("--ceiling", type=float, default=20.0, help="trim: reference score >= this")
    ap.add_argument("--floor", type=float, default=12.0, help="trim: reference score <= this")
    ap.add_argument("--exclude", nargs="*", default=[], metavar="QID")
    ap.add_argument("--exact-tolerance", type=float, default=0.10)
    ap.add_argument("--out", help="markdown report (default: <results>/conditions_report.md)")
    args = ap.parse_args()

    results = Path(args.results).resolve()
    gold = load_gold()
    meta = {}
    for qf in sorted(QUESTIONS.glob("question_*.yaml")):
        q = yaml.safe_load(qf.read_text(encoding="utf-8"))
        meta[q["id"]] = (q["type"], bool(q.get("held_out", False)))
    names = [args.reference] + [c for c in args.conditions if c != args.reference]
    data, raw, cells = {}, {}, {}
    for c in names:
        fl = files_for(results, c)
        if not fl:
            raise SystemExit(f"no scored files for condition {c} in {results}")
        data[c], cells[c] = load_condition(fl, gold, args.exact_tolerance, clean=True)
        raw[c], _ = load_condition(fl, gold, args.exact_tolerance, clean=False)
        for q in args.exclude:
            data[c].pop(q, None)
            raw[c].pop(q, None)
    ref, conds = data[args.reference], [c for c in names if c != args.reference]
    k = len(conds) + len(args.pair)
    zbar = _bonferroni_z(k)

    L = [f"# Condition comparison: {results.name}", "",
         f"Reference `{args.reference}`; judge {args.judge_name}; TogoMCP arm; effects are "
         f"condition − reference, paired by question (per-question mean over valid replicates), "
         f"with 95% CIs. {k} planned comparisons: a |z| above {zbar:.2f} clears the Bonferroni bar "
         f"(α = 0.05/{k}).", "",
         "## Cells", "", "| Condition | Files | Valid | Refusal | Stub | Judge failed |",
         "|---|---:|---:|---:|---:|---:|"]
    for c in names:
        n = cells[c]
        L.append(f"| {c} | {len(files_for(results, c))} | {n['valid']} | {n['refusal']} | "
                 f"{n['stub']} | {n['judge_failed']} |")
    if args.exclude:
        L += ["", "Excluded questions: " + ", ".join(args.exclude)]

    def table(title, rows):
        out = ["", f"## {title}", "",
               "| Comparison | n | Reference | Condition | Effect (95% CI) | z | Bonferroni |",
               "|---|---:|---:|---:|---:|---:|---|"]
        for label, st in rows:
            sig = "n/a" if st["z"] is None else ("**yes**" if abs(st["z"]) > zbar else "no")
            out.append(f"| {label} | {st['n']} | {f(st['b'], '.2f')} | {f(st['a'], '.2f')} | "
                       f"{pm(st)} | {f(st['z'], '+.1f')} | {sig} |")
        return out

    main_rows = [(f"{c} − {args.reference}", effect(data[c], ref)) for c in conds]
    main_rows += [(f"{a} − {b}", effect(data[a], data[b])) for a, b in args.pair]
    L += table("Main result (refusals, stubs and failed judgements excluded)", main_rows)
    L += table("Raw (nothing excluded but failed judgements)",
               [(f"{c} − {args.reference}", effect(raw[c], raw[args.reference])) for c in conds]
               + [(f"{a} − {b}", effect(raw[a], raw[b])) for a, b in args.pair])
    trim = {q for q, d in ref.items() if args.floor < d.get("total", 0) < args.ceiling}
    L += table(f"Trimmed (reference score strictly between {args.floor:g} and {args.ceiling:g}; "
               f"{len(trim)} of {len(ref)} questions)",
               [(f"{c} − {args.reference}", effect(data[c], ref, restrict=trim)) for c in conds])
    for label, pick in (("held-out", True), ("development", False)):
        qs = {q for q, (_, h) in meta.items() if h is pick}
        L += table(f"{label.capitalize()} questions",
                   [(f"{c} − {args.reference}", effect(data[c], ref, restrict=qs)) for c in conds])
    L += ["", "## By question type (effect, 95% CI)", "",
          "| Type | " + " | ".join(conds) + " |", "|---|" + "---:|" * len(conds)]
    for t in sorted({m[0] for m in meta.values()}):
        qs = {q for q, (ty, _) in meta.items() if ty == t}
        L.append(f"| {t} | " + " | ".join(pm(effect(data[c], ref, restrict=qs)) for c in conds) + " |")
    L += ["", "## Criteria, effort and exact-answer correctness (effect, 95% CI)", "",
          "| Measure | Reference mean | " + " | ".join(conds) + " |", "|---|---:|" + "---:|" * len(conds)]
    rows = [(c, c) for c in CRITERIA] + list(EFFORT) + [("correct", "exact-answer correct (0–1)")]
    for key, label in rows:
        sts = [effect(data[c], ref, key=key) for c in conds]
        spec = "+.3f" if key in ("cost", "correct") else "+.2f"
        L.append(f"| {label} | {f(sts[0]['b'], '.2f') if sts else 'n/a'} | "
                 + " | ".join(pm(s, spec) for s in sts) + " |")
    L += ["", "Effort is per answer; a positive effort effect means the condition made the agent "
          "work harder. Exact-answer correctness grades the answer text against `exact_answer` "
          "(factoid tolerance 10%; summary questions have no gold)."]

    if args.judge2:
        pattern, jname = args.judge2
        d2 = {}
        for c in names:
            fl = files_for(results, c, pattern)
            if not fl:
                raise SystemExit(f"--judge2: no files for {c} ({pattern})")
            d2[c], _ = load_condition(fl, gold, args.exact_tolerance, clean=True)
        L += ["", f"## Under both judges", "",
              f"| Comparison | {args.judge_name} | {jname} | Same sign? |", "|---|---:|---:|---|"]
        pairs = [(c, args.reference) for c in conds] + [tuple(p) for p in args.pair]
        for a, b in pairs:
            s1, s2 = effect(data[a], data[b]), effect(d2[a], d2[b])
            ns1 = s1["ci95"] is None or abs(s1["mean"]) <= s1["ci95"]
            ns2 = s2["ci95"] is None or abs(s2["mean"]) <= s2["ci95"]
            same = "n.s. under both" if ns1 and ns2 else ("yes" if (s1["mean"] > 0) == (s2["mean"] > 0) else "**NO**")
            L.append(f"| {a} − {b} | {pm(s1)} | {pm(s2)} | {same} |")

    out = Path(args.out) if args.out else results / "conditions_report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
