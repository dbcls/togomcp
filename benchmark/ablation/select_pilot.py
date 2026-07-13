#!/usr/bin/env python3
"""Select a DB-spanning pilot subset of benchmark questions for the ablation sweep.

The full set is presently 100 questions (20 per type), touching 34 distinct
RDF databases. Running every question across
12 ablation conditions is expensive, so the pilot picks a subset that still
exercises as many databases and question types as possible —
the ablation signal for a section is only visible on questions whose target DB
actually carries that section, so broad DB coverage matters more than raw count.

Selection is a deterministic greedy set-cover: repeatedly take the question that
adds the most not-yet-covered databases, breaking ties toward under-represented
question types then question id. It stops once every database is covered and at
least --min questions are chosen (capped at --max).

Variance control & how many questions are enough
-------------------------------------------------
A paired ablation delta (baseline − ablated) on the 0–20 judge score is noisy.
Two things inflate its SD without carrying section signal: judge jitter (the same
answer rescored varies run-to-run) and *ceiling/floor* questions — a with-tools
baseline already at 20/20 can only move DOWN under any ablation, and one scoring
very low bounces UP under almost any ablation. This script drops the ceiling/floor
questions up front where a prior baseline score is available (only ~2 exist in the
data so far).

"Enough" is an effect-size question, not a fixed count. On the only sweep run to
date (15 questions, ONE answer + ONE judge each) the paired-delta SD is ~4.5–5
points even after the ceiling/floor drop; at that SD a paired t-test (α=.05, 80%
power) needs n≈60–150 to resolve the ~1-point effects most sections show, and
n=40 resolves only ~2-point effects. So ~40 is a coverage/type-balance target,
NOT a proven significance threshold — treat single-shot contributions as
directional. The lever that makes 40 adequate is REPLICATION, not more questions:
`run_ablation.py --runs R` averages R runs per question, dividing the judge-jitter
part of the variance by R (we can't yet separate judge jitter from true
question-to-question heterogeneity — that needs replicate data).

Important limitation: baselines only exist for questions already run through a
sweep (results/baseline-scored.csv). Questions never scored yet CANNOT be
pre-filtered — they are kept as candidates and reported as "unscored". Re-apply
the same ceiling/floor cut post-sweep with:
    python ablation_analysis.py --exclude <qids at ceiling/floor>
so the averaged set lands in the low-variance regime regardless.

Usage:
    python select_pilot.py                 # 40 Qs, ceiling/floor pre-filtered
    python select_pilot.py --min 36 --max 40
    python select_pilot.py --no-score-filter   # coverage only, keep all Qs
    python select_pilot.py --full          # emit all questions (full sweep)
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QDIR = REPO_ROOT / "benchmark" / "questions"
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "pilot_questions.txt"
DEFAULT_BASELINE = HERE / "results" / "baseline-scored.csv"


def load_questions(qdir: Path) -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(qdir / "question_*.yaml"))):
        d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        out.append({
            "path": f,
            "id": d.get("id", Path(f).stem),
            "type": d.get("type", "unknown"),
            "dbs": set(d.get("togomcp_databases_used") or []),
        })
    return out


def load_baseline_scores(path: Path, metric: str) -> dict[str, float | None]:
    """question_id -> baseline score (None if judge-failed sentinel 0 / non-numeric).

    Reads the with-tools metric from a prior sweep's baseline-scored.csv; missing
    file returns {} (no pre-filtering possible)."""
    scores: dict[str, float | None] = {}
    if not path.exists():
        return scores
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if metric not in (reader.fieldnames or []):
            raise SystemExit(f"{path.name} missing column: {metric}")
        for row in reader:
            qid = row.get("question_id")
            if not qid:
                continue
            try:
                v = float(row[metric])
            except (TypeError, ValueError):
                v = None
            scores[qid] = None if v == 0 else v  # 0 == failed-judge sentinel
    return scores


def classify(q: dict, scores: dict[str, float | None],
             ceiling: float, floor: float) -> str:
    """'ceiling' | 'floor' | 'failed' | 'keep' | 'unscored' for one question."""
    if q["id"] not in scores:
        return "unscored"
    s = scores[q["id"]]
    if s is None:
        return "failed"      # judge crashed on baseline — unusable as a paired anchor
    if s >= ceiling:
        return "ceiling"
    if s <= floor:
        return "floor"
    return "keep"


def greedy_pilot(questions: list[dict], min_q: int, max_q: int) -> list[dict]:
    all_dbs = set().union(*(q["dbs"] for q in questions)) if questions else set()
    covered_dbs: set[str] = set()
    type_counts: dict[str, int] = {}
    chosen: list[dict] = []
    remaining = list(questions)

    def sort_key(q: dict):
        new_dbs = len(q["dbs"] - covered_dbs)
        # Prefer more new DBs, then the least-used type so far, then stable id.
        return (-new_dbs, type_counts.get(q["type"], 0), q["id"])

    while remaining and len(chosen) < max_q:
        remaining.sort(key=sort_key)
        best = remaining[0]
        new_dbs = len(best["dbs"] - covered_dbs)
        # Stop early once all DBs are covered and we have the minimum count —
        # unless the next pick still adds coverage, in which case keep going.
        if new_dbs == 0 and covered_dbs >= all_dbs and len(chosen) >= min_q:
            break
        chosen.append(best)
        remaining.remove(best)
        covered_dbs |= best["dbs"]
        type_counts[best["type"]] = type_counts.get(best["type"], 0) + 1

    return chosen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions-dir", default=str(DEFAULT_QDIR))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--min", type=int, default=40,
                    help="minimum pilot size (coverage/balance target; NOT a power "
                         "guarantee — see module docstring on replication)")
    ap.add_argument("--max", type=int, default=40, help="maximum pilot size")
    ap.add_argument("--full", action="store_true", help="emit all questions, not a subset")
    ap.add_argument("--baseline-scores", default=str(DEFAULT_BASELINE),
                    help="prior sweep's scored CSV used to drop ceiling/floor questions")
    ap.add_argument("--score-metric", default="togomcp_total_score",
                    help="baseline column defining ceiling/floor (the ablated path's metric)")
    ap.add_argument("--ceiling", type=float, default=20.0,
                    help="drop questions whose baseline score is >= this (can only fall)")
    ap.add_argument("--floor", type=float, default=12.0,
                    help="drop questions whose baseline score is <= this (bounces up)")
    ap.add_argument("--no-score-filter", action="store_true",
                    help="disable ceiling/floor pre-filtering (coverage only)")
    args = ap.parse_args()

    questions = load_questions(Path(args.questions_dir))
    if not questions:
        print("ERROR: no questions found")
        return 2

    if args.full:
        chosen = questions
        pool = questions
        buckets: dict[str, list[str]] = {}
    else:
        scores = {} if args.no_score_filter else load_baseline_scores(
            Path(args.baseline_scores), args.score_metric)
        buckets = {"ceiling": [], "floor": [], "failed": [], "keep": [], "unscored": []}
        pool = []
        for q in questions:
            verdict = "unscored" if not scores else classify(
                q, scores, args.ceiling, args.floor)
            buckets[verdict].append(q["id"])
            if verdict not in ("ceiling", "floor", "failed"):
                pool.append(q)  # keep + unscored are candidates
        chosen = greedy_pilot(pool, args.min, args.max)

    chosen = sorted(chosen, key=lambda q: q["id"])
    Path(args.out).write_text("\n".join(q["path"] for q in chosen) + "\n", encoding="utf-8")

    all_dbs = set().union(*(q["dbs"] for q in questions))
    pool_dbs = set().union(*(q["dbs"] for q in pool)) if pool else set()
    cov = set().union(*(q["dbs"] for q in chosen)) if chosen else set()
    tcounts: dict[str, int] = {}
    for q in chosen:
        tcounts[q["type"]] = tcounts.get(q["type"], 0) + 1

    print(f"selected {len(chosen)}/{len(questions)} questions -> {args.out}")
    if not args.full:
        excl = buckets["ceiling"] + buckets["floor"] + buckets["failed"]
        if excl:
            print(f"pre-filtered {len(excl)} question(s) on prior baseline "
                  f"(ceiling>={args.ceiling:g} / floor<={args.floor:g}):")
            for k in ("ceiling", "floor", "failed"):
                if buckets[k]:
                    print(f"  {k:8}: {', '.join(buckets[k])}")
        else:
            print("pre-filter: no prior baseline scores found — nothing dropped "
                  f"(looked in {args.baseline_scores})")
        if buckets["unscored"]:
            print(f"UNSCORED (kept, can't pre-judge): {len(buckets['unscored'])} question(s) — "
                  "re-apply the cut post-sweep via ablation_analysis.py --exclude")
        lost = sorted(all_dbs - pool_dbs)
        if lost:
            print(f"  NB: {len(lost)} DB(s) only appear in filtered-out questions "
                  f"and became uncoverable: {', '.join(lost)}")
    print(f"DB coverage: {len(cov)}/{len(all_dbs)} databases")
    missing = sorted(all_dbs - cov)
    if missing:
        print(f"  uncovered DBs: {', '.join(missing)}")
    print(f"type spread: {dict(sorted(tcounts.items()))}")
    print("questions: " + ", ".join(q["id"] for q in chosen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
