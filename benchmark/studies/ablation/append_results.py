#!/usr/bin/env python3
"""Fold a staged batch of NEW questions into the main ablation results.

Extending the sweep to more questions does not require re-running the ones already
done: ablation_analysis.py keys everything on question_id and pairs per question,
so appending rows for new questions simply grows n.

The workflow this supports:

  1. Pick questions not already in the sweep (see --list-existing below).
  2. Run EVERY condition for them, in ONE batch, into a staging dir:
       run_ablation.py --results-dir results_batchN --questions <new...> --runs 3 \
                       --answer-use-api --judge-use-api
     Running all conditions together is REQUIRED: each new question's baseline and
     ablated rows must come from the same batch, or the paired delta carries a
     batch offset (the confound that made the trial-baseline contributions all
     drift negative).
  3. Fold them in:
       append_results.py results_batchN results
     Rows are appended per <cond>-scored-vN.csv, keyed by question_id (existing
     qids are never overwritten — reruns of the same question are skipped), and
     the flat <cond>-scored.csv is rebuilt from the per-run files afterwards.

Idempotent: re-running appends nothing new.

Usage:
    python append_results.py results_batch2 results
    python append_results.py results_batch2 results --dry-run
    python append_results.py --list-existing results
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
from pathlib import Path

csv.field_size_limit(10_000_000)

# merge_scored lives in run_ablation; reuse it so the flat CSV is rebuilt with the
# identical averaging + failed-judge-sentinel rules the sweep itself used.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_ablation import merge_scored  # noqa: E402


def _qids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as fh:
        return {r["question_id"] for r in csv.DictReader(fh) if r.get("question_id")}


def list_existing(results: Path) -> None:
    base = results / "baseline-scored.csv"
    if not base.exists():
        raise SystemExit(f"no baseline-scored.csv in {results}")
    qids = sorted(_qids(base))
    print(f"{len(qids)} questions already in {results}:")
    print("  " + ", ".join(qids))


def append_condition(stage: Path, main: Path, cond: str, dry_run: bool) -> tuple[int, int]:
    """Append one condition's per-run rows. Returns (rows_added, runs_touched)."""
    added = runs = 0
    for src in sorted(glob.glob(str(stage / f"{cond}-scored-v*.csv"))):
        dst = main / os.path.basename(src)
        have = _qids(dst)
        with open(src, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields = list(reader.fieldnames or [])
            new_rows = [r for r in reader
                        if r.get("question_id") and r["question_id"] not in have]
        if not new_rows:
            continue
        runs += 1
        added += len(new_rows)
        if dry_run:
            continue
        if dst.exists():
            # Preserve the destination's column order; ignore any extra staged cols.
            with dst.open(encoding="utf-8") as fh:
                dst_fields = list(csv.DictReader(fh).fieldnames or fields)
            with dst.open("a", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=dst_fields, extrasaction="ignore").writerows(new_rows)
        else:
            with dst.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(new_rows)
    return added, runs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="?", help="staging results dir holding the new batch")
    ap.add_argument("main", nargs="?", default="results", help="main results dir (default: results)")
    ap.add_argument("--dry-run", action="store_true", help="report what would be appended")
    ap.add_argument("--list-existing", metavar="DIR",
                    help="list the question_ids already covered in DIR, then exit")
    args = ap.parse_args()

    if args.list_existing:
        list_existing(Path(args.list_existing))
        return 0
    if not args.stage:
        raise SystemExit("give a staging dir (or --list-existing DIR); see --help")

    stage, main_dir = Path(args.stage), Path(args.main)
    if not stage.is_dir():
        raise SystemExit(f"staging dir not found: {stage}")

    conds = sorted({os.path.basename(f).split("-scored-v")[0]
                    for f in glob.glob(str(stage / "*-scored-v*.csv"))})
    if not conds:
        raise SystemExit(f"no <cond>-scored-vN.csv files in {stage}")

    total = 0
    for cond in conds:
        added, runs = append_condition(stage, main_dir, cond, args.dry_run)
        total += added
        verb = "would append" if args.dry_run else "appended"
        print(f"{cond:34s} {verb} {added:4d} rows across {runs} run file(s)")
        if added and not args.dry_run:
            per_run = sorted(glob.glob(str(main_dir / f"{cond}-scored-v*.csv")))
            if len(per_run) > 1:
                merge_scored([Path(p) for p in per_run], main_dir / f"{cond}-scored.csv")
                print(f"{'':34s} rebuilt {cond}-scored.csv from {len(per_run)} runs")

    print(f"\n{'would append' if args.dry_run else 'appended'} {total} rows total")
    if not args.dry_run and total:
        print("Next: python ablation_analysis.py --exclude-ceiling 20 --exclude-floor 12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
