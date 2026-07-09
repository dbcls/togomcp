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
from pathlib import Path
from statistics import mean

import yaml

from ablate_mie import CANONICAL_SECTIONS

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
    """section -> set of databases whose MIE contains it (from section_presence.csv)."""
    out: dict[str, set[str]] = {s: set() for s in CANONICAL_SECTIONS}
    if not PRESENCE_CSV.exists():
        return out
    with PRESENCE_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            db = row["database"]
            for s in CANONICAL_SECTIONS:
                if row.get(s) == "1":
                    out[s].add(db)
    return out


def _fmt(x: float | None, spec: str = "+.2f") -> str:
    return "n/a" if x is None else format(x, spec)


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

    rows = []
    for section in CANONICAL_SECTIONS:
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

        row = {
            "section": section,
            "spotlight": "; ".join(SPOTLIGHT.get(section, [])) or "-",
            "n": n,
            "mean_baseline": None if mb is None else round(mb, 3),
            "mean_ablated": None if ma is None else round(ma, 3),
            "contribution": None if mb is None else round(mb - ma, 3),
            "n_relevant": n_r,
            "contribution_relevant": None if mb_r is None else round(mb_r - ma_r, 3),
        }
        for sm in SUBMETRICS:
            smb, sma, _ = paired_mean(baseline, ablated, sm, None)
            row[f"delta_{sm}"] = None if smb is None else round(smb - sma, 3)
        rows.append(row)

    if not rows:
        raise SystemExit("no ablate_*-scored.csv files found — run the sweep first")

    rows.sort(key=lambda r: (r["contribution"] is None, -(r["contribution"] or 0)))

    out_csv = results / "ablation_contributions.csv"
    fieldnames = ["section", "spotlight", "n", "mean_baseline", "mean_ablated",
                  "contribution", *[f"delta_{m}" for m in SUBMETRICS],
                  "n_relevant", "contribution_relevant"]
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    base_vals = [r[metric] for r in baseline.values() if r.get(metric) is not None]
    base_mean = mean(base_vals) if base_vals else float("nan")
    write_report(rows, results / "ablation_report.md", metric, base_mean, len(baseline))

    # console summary
    print(f"{'section':28s} {'spotlight?':10s} {'n':>3s} {'base':>6s} {'abl':>6s} {'contrib':>8s}")
    for r in rows:
        spot = "yes" if r["spotlight"] != "-" else ""
        print(f"{r['section']:28s} {spot:10s} {r['n']:>3d} "
              f"{_fmt(r['mean_baseline'], '.2f'):>6s} {_fmt(r['mean_ablated'], '.2f'):>6s} "
              f"{_fmt(r['contribution']):>8s}")
    print(f"\nwrote {out_csv}")
    print(f"wrote {results / 'ablation_report.md'}")
    return 0


def write_report(rows: list[dict], path: Path, metric: str,
                 base_mean: float, n_baseline_q: int) -> None:
    lines = [
        "# MIE Subcomponent Ablation — Contribution Report",
        "",
        f"**Metric:** `{metric}` (TogoMCP with-tools LLM-judge score, max {SCORE_MAX}).  ",
        f"**Baseline mean:** {base_mean:.2f}/{SCORE_MAX} over {n_baseline_q} questions.  ",
        "**Contribution** = mean(baseline) − mean(section removed); higher ⇒ the section "
        "matters more. Deltas are paired per question.",
        "",
        "## All 11 sections, ranked by contribution",
        "",
        "| Rank | Section | Spotlight category | n | Baseline | Ablated | Contribution |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | `{r['section']}` | {r['spotlight']} | {r['n']} | "
            f"{_fmt(r['mean_baseline'], '.2f')} | {_fmt(r['mean_ablated'], '.2f')} | "
            f"**{_fmt(r['contribution'])}** |"
        )

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
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
