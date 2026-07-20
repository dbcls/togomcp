#!/usr/bin/env python3
"""Quantify each MIE section's contribution from the ablation sweep's scored CSVs.

Reads results/<condition>-scored.csv (produced by run_ablation.py) and computes,
per ablated section, how much benchmark performance drops when that section is
removed from the MIE corpus:

    contribution(section) = mean(baseline) - mean(ablate_section)

on the TogoMCP (with-tools) LLM-judge scores — that's the path MIE content
affects; the no-tools `baseline_*` columns never read an MIE and are ignored.
Deltas are PAIRED: each condition is inner-joined to the baseline on question_id
so only questions answered under both contribute, and a positive delta means the
section helped.

Two views per section:
  * overall           — all pilot questions.
  * relevance-scoped  — only questions touching a database whose MIE actually
                        carries that section (via mie_variants/section_presence.csv).
                        With today's uniformly-complete MIEs this equals overall;
                        it earns its keep once some MIEs omit sections.

Depends only on the stdlib + pyyaml (no pandas), so it runs in the same venv as
the TogoMCP server.

Outputs:
    results/ablation_contributions.csv   machine-readable, one row per section
    results/ablation_report.md           ranked table + 4-category spotlight

Usage:
    python ablation_analysis.py
    python ablation_analysis.py --results results --metric togomcp_total_score
"""
from __future__ import annotations

import argparse
import csv
import glob
import re
from math import sqrt
from pathlib import Path
from statistics import NormalDist, mean, stdev

import yaml

from ablate_mie import CANONICAL_SECTIONS, GROUPS

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFAULT_RESULTS = HERE / "results"
PRESENCE_CSV = HERE / "mie_variants" / "section_presence.csv"
QUESTIONS_DIR = REPO_ROOT / "benchmark" / "questions"

# Spotlight: the 4 spec-named categories -> MIE section (1:1).
SPOTLIGHT: dict[str, list[str]] = {
    "schema_info": ["Schema description (スキーマ記述)"],
    "shape_expressions": ["ShEx/shape (ShEx/シェイプ)"],
    "sparql_query_examples": ["SPARQL query examples (SPARQL クエリ例)"],
    "cross_references": ["Entity/vocab coverage (エンティティ・語彙カバレッジ)"],
}
SCORE_MAX = 20  # togomcp_total_score = recall+precision+repetition+readability, each 1-5
SUBMETRICS = ["togomcp_recall", "togomcp_precision"]


def load_scores(path: Path, metrics: list[str]) -> dict[str, dict]:
    """question_id -> {question_type, <metric>: float|None, ...}. Non-numeric -> None.

    A metric value of 0 is the failed-judge sentinel written by
    add_llm_evaluation._failed_eval (real per-criterion scores clamp to 1-5,
    totals to 4-20), so it is read as None and paired-dropped rather than
    counted as a genuine zero. Without this, one crashed judge call — an
    18-point swing on a 15-question pilot — dominates a section's contribution.
    """
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        for m in metrics:
            if m not in cols:
                raise SystemExit(f"{path.name} missing column: {m}")
        for row in reader:
            qid = row.get("question_id")
            if not qid:
                continue
            rec: dict = {"question_type": row.get("question_type", "unknown")}
            for m in metrics:
                try:
                    v = float(row[m])
                except (TypeError, ValueError):
                    v = None
                rec[m] = None if v == 0 else v
            out[qid] = rec
    return out


def paired_mean(base: dict[str, dict], abl: dict[str, dict], metric: str,
                restrict: set[str] | None) -> tuple[float | None, float | None, int]:
    """Mean of `metric` over question_ids present (and numeric) in both."""
    bvals, avals = [], []
    for qid in base.keys() & abl.keys():
        if restrict is not None and qid not in restrict:
            continue
        bv, av = base[qid].get(metric), abl[qid].get(metric)
        if bv is None or av is None:
            continue
        bvals.append(bv)
        avals.append(av)
    if not bvals:
        return None, None, 0
    return mean(bvals), mean(avals), len(bvals)


def question_dbs() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for f in sorted(glob.glob(str(QUESTIONS_DIR / "question_*.yaml"))):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        out[d.get("id", Path(f).stem)] = set(d.get("togomcp_databases_used") or [])
    return out


def sections_with_db() -> dict[str, set[str]]:
    """label -> databases whose MIE carries it (from section_presence.csv).

    Group labels (`group_<name>`) map to the UNION of their members' databases: a
    group ablation is relevant to a question if ANY of its sections is.
    """
    out: dict[str, set[str]] = {s: set() for s in CANONICAL_SECTIONS}
    if PRESENCE_CSV.exists():
        with PRESENCE_CSV.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                db = row["database"]
                for s in CANONICAL_SECTIONS:
                    if row.get(s) == "1":
                        out[s].add(db)
    for g, members in GROUPS.items():
        out[f"group_{g}"] = set().union(*(out[m] for m in members)) if members else set()
    return out


def analysis_labels() -> list[str]:
    """Every condition the analysis knows how to read: the 11 sections + each group."""
    return CANONICAL_SECTIONS + [f"group_{g}" for g in GROUPS]


def _fmt(x: float | None, spec: str = "+.2f") -> str:
    return "n/a" if x is None else format(x, spec)


# --- Error bars --------------------------------------------------------------
# Every delta here is a PAIRED per-question difference, so its uncertainty comes
# from the spread of those differences — not from the two condition means. A
# contribution is only distinguishable from "the section does nothing" when its
# CI excludes 0. Normal approximation (1.96); at n~35 the t-correction is ~4%,
# immaterial to any conclusion drawn here, and it keeps this stdlib-only.
_Z95 = 1.96


def _bonferroni_z(k: int) -> float:
    """Two-sided |z| threshold at α = 0.05/k — the bar one section must clear when
    k sections are tested at once."""
    return NormalDist().inv_cdf(1 - (0.05 / max(k, 1)) / 2)


def _delta_stats(deltas: list[float]) -> dict:
    """mean / sd / se / 95% CI half-width over paired per-question deltas."""
    n = len(deltas)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "se": None, "ci95": None}
    m = mean(deltas)
    if n < 2:
        return {"n": n, "mean": m, "sd": None, "se": None, "ci95": None}
    sd = stdev(deltas)
    se = sd / sqrt(n)
    return {"n": n, "mean": m, "sd": sd, "se": se, "ci95": _Z95 * se}


def paired_contribution(base: dict[str, dict], abl: dict[str, dict], metric: str,
                        restrict: set[str] | None) -> dict:
    """Contribution (baseline − ablated) per question, with its error bar."""
    deltas = []
    for qid in base.keys() & abl.keys():
        if restrict is not None and qid not in restrict:
            continue
        bv, av = base[qid].get(metric), abl[qid].get(metric)
        if bv is None or av is None:
            continue
        deltas.append(bv - av)
    return _delta_stats(deltas)


def _sig(stats: dict | None) -> str:
    """'*' when the 95% CI excludes 0 (i.e. distinguishable from no effect)."""
    if not stats or stats.get("ci95") is None or stats.get("mean") is None:
        return ""
    return "*" if abs(stats["mean"]) > stats["ci95"] else ""


# --- Effort dimension --------------------------------------------------------
# The judge score measures answer QUALITY; it is blind to how much work the agent
# did to get there. Removing a query-guidance section (e.g. sparql_query_examples)
# can leave answer quality unchanged while forcing the agent to issue many more
# SPARQL attempts — an EFFORT cost the score never sees. These helpers surface it.
SPARQL_TOOL = "run_sparql"
EFFORT_KEYS = ("n_sparql", "n_tools", "wall_s", "cost")


def _effort_from_row(row: dict) -> dict:
    tu = row.get("tools_used") or ""
    calls = [t.strip() for t in tu.split(",") if t.strip()]   # full call sequence, with repeats

    def fnum(k: str) -> float:
        try:
            return float(row.get(k) or 0)
        except (TypeError, ValueError):
            return 0.0

    return {
        "n_sparql": sum(1 for t in calls if t.endswith(SPARQL_TOOL)),
        "n_tools": len(calls),
        "wall_s": fnum("togomcp_time"),
        "cost": fnum("togomcp_cost_usd"),
    }


def load_effort(condition: str, results: Path) -> dict[str, dict]:
    """question_id -> per-run-averaged effort for a condition.

    Reads the replicate <cond>-scored-vN.csv files (averaging effort across runs,
    since the merged <cond>-scored.csv keeps only run 1's tools_used) and falls
    back to the merged file when no replicates exist (a --runs 1 sweep).
    """
    files = sorted(glob.glob(str(results / f"{condition}-scored-v*.csv")))
    if not files:
        merged = results / f"{condition}-scored.csv"
        files = [str(merged)] if merged.exists() else []
    agg: dict[str, list[dict]] = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                qid = row.get("question_id")
                if qid:
                    agg.setdefault(qid, []).append(_effort_from_row(row))
    return {qid: {k: mean(d[k] for d in runs) for k in EFFORT_KEYS}
            for qid, runs in agg.items()}


def paired_effort(base: dict[str, dict], abl: dict[str, dict],
                  exclude: set[str]) -> dict | None:
    """Mean (ablated − baseline) effort over questions scored under both.

    Positive delta ⇒ removing the section made the agent work HARDER (more
    queries / tools / time / cost) for the same answer ⇒ the section buys
    efficiency. Paired per question, same exclude set as the quality analysis.
    """
    qids = (base.keys() & abl.keys()) - exclude
    if not qids:
        return None
    out: dict = {"n": len(qids)}
    for k in EFFORT_KEYS:
        base_mean = mean(base[q][k] for q in qids)
        st = _delta_stats([abl[q][k] - base[q][k] for q in qids])
        out[f"delta_{k}"] = st["mean"]
        out[f"ci95_{k}"] = st["ci95"]
        out[f"se_{k}"] = st["se"]
        out[f"sig_{k}"] = _sig(st)
        out[f"base_{k}"] = base_mean
        out[f"pct_{k}"] = (out[f"delta_{k}"] / base_mean * 100) if base_mean else 0.0
    return out


# --- Exact-answer correctness (secondary, tolerance-based) -------------------
# The judge's 4x(1-5) score has a large per-question SD. A crisper 0/1 match of
# the agent's answer against the question YAML's `exact_answer` gold is a
# lower-variance (if coarser) lens. Factoids use a relative tolerance as a safety
# margin for minor DB drift, but spot-checks (re-running the gold queries live)
# show factoid mismatches are mostly REAL agent miscounts on multi-step
# aggregations — the golds re-run to their stored values — not stale golds. So low
# factoid correctness is a valid signal the graded score smooths over. `choice`
# sits near a 100% ceiling (no discrimination). Summary questions have no gold.
_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: (i + 2) * 10 for i, w in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}


def _word_numbers(text: str) -> list[int]:
    """Integer values of spelled-out English cardinals ('four hundred twenty-eight')."""
    vals, cur, res, on = [], 0, 0, False
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in _UNITS:
            cur += _UNITS[w]; on = True
        elif w in _TENS:
            cur += _TENS[w]; on = True
        elif w == "hundred":
            cur = (cur or 1) * 100; on = True
        elif w in _SCALES:
            res += (cur or 1) * _SCALES[w]; cur = 0; on = True
        elif w == "and" and on:
            continue
        else:
            if on:
                vals.append(res + cur)
            cur = res = 0; on = False
    if on:
        vals.append(res + cur)
    return vals


def grade_exact(answer: str | None, gtype: str, gexact, tol: float) -> float | None:
    """0/1 correctness (list: fractional recall) vs the gold, or None if ungradable."""
    a = (answer or "").strip()
    if gtype == "summary" or gexact in (None, "", []):
        return None
    al = a.lower()
    if gtype == "yes_no":
        stance = "yes" if re.match(r"\W*yes\b", al) else "no" if re.match(r"\W*no\b", al) else None
        return 1.0 if stance == str(gexact).strip().lower() else 0.0
    if gtype == "factoid":
        # A factoid gold may be a bare count (int / "326"), or a string encoding an
        # entity name AND/OR a count — e.g. "Ms4a2 (86 variants)" (a two-part
        # "which X and how many") or "Ms4a2" (which-entity). Grade EVERY part the
        # gold names: the count numerically (within tolerance) and the entity as a
        # key match (leading token before "(", like the list/choice graders). A
        # bare-number gold keeps the original numeric-only behavior exactly.
        gs = str(gexact).strip()
        head = re.split(r"\s*\(", gs, 1)[0].strip()
        tok = head.split()[0] if head.split() else ""
        if re.fullmatch(r"[\d,]+", tok):          # bare numeric gold (7 of 8 factoids)
            name_key = ""
            gnums = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", gs)]
        else:                                     # entity, optionally followed by a count
            name_key = tok.lower()
            rest = gs[gs.find(tok) + len(tok):]   # digits AFTER the name (skip any in it, e.g. Ms4a2)
            gnums = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", rest)]
        gold_num = gnums[0] if gnums else None
        if gold_num is None and not name_key:
            return None                            # nothing gradable
        ok = True
        if name_key:                               # entity must be named (list/choice-style key match)
            ok = bool(re.search(rf"\b{re.escape(name_key)}\b", al)) if len(name_key) <= 4 \
                else (name_key in al)
        if ok and gold_num is not None:            # count must appear within tolerance
            cands = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", a)] + _word_numbers(a)
            ok = (0 in cands) if gold_num == 0 else any(abs(c - gold_num) <= tol * gold_num for c in cands)
        return 1.0 if ok else 0.0
    items = gexact if isinstance(gexact, list) else [gexact]
    if gtype == "choice":
        s = str(items[0]).strip().strip("[]'\"").lower()
        hit = re.search(rf"\b{re.escape(s)}\b", al) if len(s) <= 4 else (s in al)
        return 1.0 if hit else 0.0
    if gtype == "list":                       # fractional recall of gold entities
        got = 0
        for it in items:
            key = re.split(r"\s*\(", str(it))[0].strip().lower()
            key = key.split()[0] if key else key
            if key and (re.search(rf"\b{re.escape(key)}\b", al) if len(key) <= 4 else key in al):
                got += 1
        return got / len(items) if items else 0.0
    return None


def load_gold() -> dict[str, dict]:
    gold = {}
    for f in glob.glob(str(QUESTIONS_DIR / "question_*.yaml")):
        q = yaml.safe_load(open(f, encoding="utf-8")) or {}
        qid = q.get("id", Path(f).stem)
        gold[qid] = {"type": q.get("type"), "exact": q.get("exact_answer")}
    return gold


def load_correctness(condition: str, gold: dict, tol: float, results: Path) -> dict[str, float]:
    """question_id -> per-run-averaged exact-answer correctness for a condition."""
    files = sorted(glob.glob(str(results / f"{condition}-scored-v*.csv")))
    if not files:
        merged = results / f"{condition}-scored.csv"
        files = [str(merged)] if merged.exists() else []
    per: dict[str, list[float]] = {}
    for f in files:
        for r in csv.DictReader(open(f, encoding="utf-8")):
            qid = r.get("question_id")
            if not qid:
                continue
            g = gold.get(qid)
            if not g:
                continue
            c = grade_exact(r.get("togomcp_answer"), g["type"], g["exact"], tol)
            if c is not None:
                per.setdefault(qid, []).append(c)
    return {qid: mean(v) for qid, v in per.items() if v}


def paired_correctness(base: dict[str, float], abl: dict[str, float],
                       exclude: set[str]) -> dict | None:
    """Mean(baseline − ablated) exact-answer correctness, paired per question."""
    qids = (base.keys() & abl.keys()) - exclude
    if not qids:
        return None
    return {
        "n": len(qids),
        "base": mean(base[q] for q in qids),
        "abl": mean(abl[q] for q in qids),
        "contribution": mean(base[q] - abl[q] for q in qids),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(DEFAULT_RESULTS))
    ap.add_argument("--metric", default="togomcp_total_score",
                    help="scored-CSV column to analyze (default: togomcp_total_score)")
    ap.add_argument("--exclude", nargs="*", default=[], metavar="QID",
                    help="question_ids to drop from every condition (e.g. high-variance "
                         "questions whose baseline is at the ceiling/floor and swing under "
                         "any ablation). Paired: dropped from baseline and each ablated set.")
    ap.add_argument("--exclude-ceiling", type=float, default=None, metavar="N",
                    help="also auto-drop every question whose BASELINE metric is >= N "
                         "(can only fall under ablation → variance, no signal). Try 20.")
    ap.add_argument("--exclude-floor", type=float, default=None, metavar="N",
                    help="also auto-drop every question whose BASELINE metric is <= N "
                         "(bounces up under ablation → variance, no signal). Try 12.")
    ap.add_argument("--exact-tolerance", type=float, default=0.10, metavar="FRAC",
                    help="relative tolerance for factoid exact-answer matching (default 0.10 "
                         "= within 10%%; absorbs live-DB drift from the frozen gold count).")
    args = ap.parse_args()
    exclude = set(args.exclude)

    results = Path(args.results)
    baseline_csv = results / "baseline-scored.csv"
    if not baseline_csv.exists():
        raise SystemExit(f"baseline scored CSV not found: {baseline_csv} — run the sweep first")

    metric = args.metric
    metrics = [metric] + [m for m in SUBMETRICS if m != metric]
    baseline = load_scores(baseline_csv, metrics)

    # Auto-extend the exclude set with ceiling/floor questions read off the
    # baseline metric (the same cut select_pilot.py applies at selection time,
    # here guaranteed over every question actually in the sweep).
    if args.exclude_ceiling is not None or args.exclude_floor is not None:
        auto: list[str] = []
        for qid, rec in baseline.items():
            v = rec.get(metric)
            if v is None:
                continue
            if args.exclude_ceiling is not None and v >= args.exclude_ceiling:
                exclude.add(qid); auto.append(f"{qid}(={v:g}↑)")
            elif args.exclude_floor is not None and v <= args.exclude_floor:
                exclude.add(qid); auto.append(f"{qid}(={v:g}↓)")
        if auto:
            print(f"auto-excluded {len(auto)} ceiling/floor question(s): {', '.join(sorted(auto))}")

    for qid in exclude:
        baseline.pop(qid, None)

    sec_dbs = sections_with_db()
    qdbs = question_dbs()

    # Effort baseline (query/tool/time/cost per question), paired against each
    # ablation below. Empty when no per-run/merged answer data carries tools_used.
    base_effort = load_effort("baseline", results)

    # Exact-answer correctness baseline (secondary, lower-variance quality lens).
    gold = load_gold()
    base_correct = load_correctness("baseline", gold, args.exact_tolerance, results)

    rows = []
    for section in analysis_labels():
        csv_path = results / f"ablate_{section}-scored.csv"
        if not csv_path.exists():
            continue
        ablated = load_scores(csv_path, metrics)
        for qid in exclude:
            ablated.pop(qid, None)

        mb, ma, n = paired_mean(baseline, ablated, metric, None)
        dbs_with = sec_dbs.get(section, set())
        relevant = {qid for qid, dbs in qdbs.items() if dbs & dbs_with}
        mb_r, ma_r, n_r = paired_mean(baseline, ablated, metric, relevant)

        cstat = paired_contribution(baseline, ablated, metric, None)
        row = {
            "section": section,
            "spotlight": "; ".join(SPOTLIGHT.get(section, [])) or "-",
            "n": n,
            "mean_baseline": None if mb is None else round(mb, 3),
            "mean_ablated": None if ma is None else round(ma, 3),
            "contribution": None if mb is None or ma is None else round(mb - ma, 3),
            "contribution_ci95": None if cstat["ci95"] is None else round(cstat["ci95"], 3),
            "contribution_se": None if cstat["se"] is None else round(cstat["se"], 3),
            "contribution_sig": _sig(cstat),
            "n_relevant": n_r,
            "contribution_relevant": None if mb_r is None or ma_r is None else round(mb_r - ma_r, 3),
        }
        for sm in SUBMETRICS:
            smb, sma, _ = paired_mean(baseline, ablated, sm, None)
            row[f"delta_{sm}"] = None if smb is None or sma is None else round(smb - sma, 3)

        # Effort delta: how much harder the agent worked with this section removed.
        eff = paired_effort(base_effort, load_effort(f"ablate_{section}", results), exclude)
        row["delta_sparql"] = None if eff is None else round(eff["delta_n_sparql"], 2)
        row["delta_sparql_ci95"] = None if eff is None or eff["ci95_n_sparql"] is None \
            else round(eff["ci95_n_sparql"], 2)
        row["delta_sparql_sig"] = "" if eff is None else eff["sig_n_sparql"]
        row["pct_sparql"] = None if eff is None else round(eff["pct_n_sparql"], 1)
        row["delta_tools"] = None if eff is None else round(eff["delta_n_tools"], 2)
        row["delta_wall_s"] = None if eff is None else round(eff["delta_wall_s"], 1)
        row["delta_cost"] = None if eff is None else round(eff["delta_cost"], 4)

        # Exact-answer correctness delta (secondary quality lens): baseline − ablated.
        cor = paired_correctness(base_correct,
                                 load_correctness(f"ablate_{section}", gold,
                                                  args.exact_tolerance, results), exclude)
        row["correct_baseline"] = None if cor is None else round(cor["base"], 3)
        row["correct_ablated"] = None if cor is None else round(cor["abl"], 3)
        row["correct_contribution"] = None if cor is None else round(cor["contribution"], 3)
        row["n_correct"] = None if cor is None else cor["n"]
        rows.append(row)

    if not rows:
        raise SystemExit("no ablate_*-scored.csv files found — run the sweep first")

    rows.sort(key=lambda r: (r["contribution"] is None, -(r["contribution"] or 0)))

    out_csv = results / "ablation_contributions.csv"
    fieldnames = ["section", "spotlight", "n", "mean_baseline", "mean_ablated",
                  "contribution", "contribution_ci95", "contribution_se", "contribution_sig",
                  *[f"delta_{m}" for m in SUBMETRICS],
                  "delta_sparql", "delta_sparql_ci95", "delta_sparql_sig", "pct_sparql",
                  "delta_tools", "delta_wall_s", "delta_cost",
                  "correct_baseline", "correct_ablated", "correct_contribution", "n_correct",
                  "n_relevant", "contribution_relevant"]
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    base_vals = [r[metric] for r in baseline.values() if r.get(metric) is not None]
    base_mean = mean(base_vals) if base_vals else float("nan")
    base_correct_overall = mean(base_correct.values()) if base_correct else None
    write_report(rows, results / "ablation_report.md", metric, base_mean, len(baseline),
                 base_correct_overall)

    # console summary
    has_effort = any(r.get("delta_sparql") is not None for r in rows)
    has_correct = any(r.get("correct_contribution") is not None for r in rows)
    hdr = (f"{'section':28s} {'spot':4s} {'n':>3s} {'base':>6s} {'abl':>6s} "
           f"{'contrib':>8s} {'±95%CI':>7s}")
    if has_effort:
        hdr += f" {'Δsparql':>8s} {'±95%CI':>7s} {'Δcost$':>7s}"
    if has_correct:
        hdr += f" {'Δcorr':>7s}"
    print(hdr)
    print("  (* = 95% CI excludes 0, i.e. distinguishable from 'section does nothing')")
    for r in rows:
        spot = "yes" if r["spotlight"] != "-" else ""
        line = (f"{r['section']:28s} {spot:4s} {r['n']:>3d} "
                f"{_fmt(r['mean_baseline'], '.2f'):>6s} {_fmt(r['mean_ablated'], '.2f'):>6s} "
                f"{_fmt(r['contribution']) + r.get('contribution_sig', ''):>8s} "
                f"{_fmt(r.get('contribution_ci95'), '.2f'):>7s}")
        if has_effort:
            line += (f" {_fmt(r.get('delta_sparql')) + r.get('delta_sparql_sig', ''):>8s}"
                     f" {_fmt(r.get('delta_sparql_ci95'), '.2f'):>7s}"
                     f" {_fmt(r.get('delta_cost'), '+.3f'):>7s}")
        if has_correct:
            cc = r.get("correct_contribution")
            line += f" {('n/a' if cc is None else f'{cc*100:+.0f}pp'):>7s}"
        print(line)
    print(f"\nwrote {out_csv}")
    print(f"wrote {results / 'ablation_report.md'}")
    return 0


def write_report(rows: list[dict], path: Path, metric: str,
                 base_mean: float, n_baseline_q: int,
                 base_correct: float | None = None) -> None:
    lines = [
        "# MIE Subcomponent Ablation — Contribution Report",
        "",
        f"**Metric:** `{metric}` (TogoMCP with-tools LLM-judge score, max {SCORE_MAX}).  ",
        f"**Baseline mean:** {base_mean:.2f}/{SCORE_MAX} over {n_baseline_q} questions.  ",
        "**Contribution** = mean(baseline) − mean(section removed); higher ⇒ the section "
        "matters more. Deltas are paired per question, shown with a 95% CI over the paired "
        "per-question differences. **A contribution is only distinguishable from "
        "'this section does nothing' when its CI excludes 0** (marked `*`); everything else "
        "is consistent with no effect, regardless of its sign.",
        "",
        f"## All {len(rows)} ablations, ranked by contribution",
        "",
        "| Rank | Section | Spotlight category | n | Baseline | Ablated | Contribution (±95% CI) | z |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(rows, 1):
        ci = r.get("contribution_ci95")
        ci_s = "" if ci is None else f" ± {ci:.2f}"
        se = r.get("contribution_se")
        c = r.get("contribution")
        z = (c / se) if (se and c is not None) else None
        lines.append(
            f"| {i} | `{r['section']}` | {r['spotlight']} | {r['n']} | "
            f"{_fmt(r['mean_baseline'], '.2f')} | {_fmt(r['mean_ablated'], '.2f')} | "
            f"**{_fmt(r['contribution'])}{ci_s}**{r.get('contribution_sig', '')} | "
            f"{('n/a' if z is None else f'{z:+.2f}')} |"
        )

    # Verdict — the multiple-comparison caveat belongs next to the stars, not in a
    # footnote, because a single borderline hit across 11 tests is what chance looks
    # like. Bonferroni over the number of sections actually reported.
    n_sig = sum(1 for r in rows if r.get("contribution_sig"))
    k = len(rows)
    z_bonf = _bonferroni_z(k)
    lines += [
        "",
        "## Verdict",
        "",
        f"**{n_sig} of {k}** sections have a 95% CI excluding 0"
        + (" — i.e. no section is distinguishable from 'this section does nothing'."
           if n_sig == 0 else "."),
        "",
        f"**Multiple comparisons matter here.** {k} sections are tested, so at α=0.05 about "
        f"{0.05 * k:.1f} false positives are expected by chance alone. A lone section at the "
        f"nominal threshold is therefore NOT evidence on its own: a Bonferroni-corrected "
        f"threshold (α=0.05/{k}≈{0.05 / k:.4f}) needs **|z| > {z_bonf:.2f}**. Read `*` as "
        "\"worth following up\", not \"established\".",
        "",
        "**Leave-one-out understates.** Each section is removed while the other "
        f"{k - 1} remain, so redundant siblings cover for it — a near-zero contribution means "
        "\"not individually necessary given everything else\", NOT \"worthless\". Removing a "
        "whole *group* (e.g. all query-guidance sections at once) is what would expose their "
        "joint value.",
    ]

    lines += ["", "## Spotlight — the 4 spec-named categories", "",
              "| Section | Category | Contribution | Contribution (relevance-scoped) |",
              "|---|---|---:|---:|"]
    for r in rows:
        if r["spotlight"] == "-":
            continue
        lines.append(
            f"| `{r['section']}` | {r['spotlight']} | **{_fmt(r['contribution'])}** | "
            f"{_fmt(r['contribution_relevant'])} |"
        )

    # Effort dimension — visible only if the answer data carried tools_used.
    if any(r.get("delta_sparql") is not None for r in rows):
        lines += [
            "",
            "## Effort — what each section saves (blind spot of the quality score)",
            "",
            "Δ = mean(section removed − baseline), paired per question. **Positive ⇒ removing "
            "the section made the agent work harder** (more SPARQL attempts / tools / time / "
            "cost) for the same answer — i.e. the section buys efficiency the quality score "
            "above cannot see. A section can be ~0 on Contribution yet clearly positive here.",
            "",
            "| Section | Δ run_sparql (±95% CI) | Δ SPARQL % | Δ tool calls | Δ wall (s) | Δ cost ($) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for r in sorted(rows, key=lambda r: (r.get("delta_sparql") is None,
                                             -(r.get("delta_sparql") or 0))):
            pct = r.get("pct_sparql")
            ci = r.get("delta_sparql_ci95")
            ci_s = "" if ci is None else f" ± {ci:.2f}"
            lines.append(
                f"| `{r['section']}` | {_fmt(r.get('delta_sparql'))}{ci_s}"
                f"{r.get('delta_sparql_sig', '')} | "
                f"{('n/a' if pct is None else f'{pct:+.0f}%')} | "
                f"{_fmt(r.get('delta_tools'))} | {_fmt(r.get('delta_wall_s'), '+.0f')} | "
                f"{_fmt(r.get('delta_cost'), '+.3f')} |"
            )

    # Exact-answer correctness — secondary, lower-variance quality lens.
    if any(r.get("correct_contribution") is not None for r in rows):
        base_c = "" if base_correct is None else f" Baseline correctness: **{base_correct*100:.1f}%**."
        lines += [
            "",
            "## Exact-answer correctness (secondary quality lens)",
            "",
            f"0/1 match of the answer against the question's `exact_answer` gold (list: "
            f"fractional recall), paired per question; Δ = baseline − ablated in percentage "
            f"points.{base_c} Lower variance than the graded score. `choice` sits near a "
            "100% ceiling (no discrimination); `factoid` mismatches are mostly REAL agent "
            "miscounts on multi-step aggregations (the gold queries re-run to their stored "
            "values), which the graded score smooths over — the tolerance only absorbs minor "
            "DB drift, not these genuine errors.",
            "",
            "| Section | Baseline % | Ablated % | Δ correct (pp) | n |",
            "|---|---:|---:|---:|---:|",
        ]
        for r in sorted(rows, key=lambda r: (r.get("correct_contribution") is None,
                                             -(r.get("correct_contribution") or 0))):
            cc, cb, ca = (r.get("correct_contribution"), r.get("correct_baseline"),
                          r.get("correct_ablated"))
            lines.append(
                f"| `{r['section']}` | {('n/a' if cb is None else f'{cb*100:.1f}')} | "
                f"{('n/a' if ca is None else f'{ca*100:.1f}')} | "
                f"{('n/a' if cc is None else f'{cc*100:+.1f}')} | {r.get('n_correct', '-')} |"
            )

    lines += [
        "",
        "## Caveats",
        "",
        f"- Pilot subset ({n_baseline_q} questions), single answer + single judge run — "
        "treat magnitudes as directional, not precise. Re-run with more questions / "
        "`--runs` for error bars.",
        "- Rows where the judge failed (`total_score = 0` sentinel) are excluded per "
        "section, not scored as a genuine zero — so a section's `n` may be below the "
        f"{n_baseline_q}-question baseline when a judge call crashed under that condition.",
        "- The 4 spotlight categories map 1:1 to `schema_info`, `shape_expressions`, "
        "`sparql_query_examples`, and `cross_references` (entity/vocab coverage).",
        "- Relevance-scoped restricts to questions touching a DB whose MIE has the section; "
        "with today's uniformly-complete MIEs this matches the overall column.",
        "- A near-zero or negative contribution means removing the section did not hurt (or "
        "helped) on this pilot — a candidate for trimming or a coverage gap in the questions.",
        "- Effort deltas are averaged across the `--runs` replicates (the merged CSV keeps "
        "only run 1's `tools_used`, so they read the per-run files); Δ SPARQL % is relative "
        "to the baseline mean. A big positive effort delta with ~0 contribution means the "
        "section trades away quality-neutral efficiency — the score can't price it.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
