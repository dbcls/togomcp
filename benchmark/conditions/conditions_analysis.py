#!/usr/bin/env python3
"""Compare the paper's condition ablations across one or more judge models.

Reads the manifest written by run_conditions.py and, for each judge, computes the
mean TogoMCP (with-tools) LLM-judge score per condition, plus the drop relative to
`with_guide` (the full system) — i.e. what removing each component costs:

    usage-guide tool       ≈ with_guide − MIE-instr   (MIE instructions still in prompt)
    guide tool + workflow  ≈ with_guide − No-Guide
    whole MIE              ≈ with_guide − no_mie

Scores from --runs>1 are pooled per (condition, judge). Depends only on the
stdlib — no pandas — so it runs in any interpreter.

Runs are organized on disk as results/<date>/<model>/ (see run_conditions.py). This
reads that run's manifest and writes its summary/report back into the same folder:
    results/<date>/<model>/summary.csv    condition x judge means + deltas
    results/<date>/<model>/report.md      readable comparison + component deltas

Usage:
    python conditions_analysis.py                                 # newest run
    python conditions_analysis.py --date 2026-07-08 --model claude-sonnet-5
    python conditions_analysis.py --date 2026-07-08 --model claude-sonnet-5 --metric togomcp_total_score
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import re
from pathlib import Path
from statistics import mean, pstdev

HERE = Path(__file__).resolve().parent
DEFAULT_RESULTS = HERE / "results"
REFERENCE = "with_guide"  # full system; deltas are measured against it
SCORE_MAX = 20


def _slug(model: str) -> str:
    """Filesystem-safe token for a model (must match run_conditions.py._slug)."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)

# Human labels for the component each condition removes vs the reference.
REMOVES = {
    "with_guide": "(reference — nothing removed)",
    "MIE-instr": "usage-guide tool (MIE workflow instructions kept in prompt)",
    "No-Guide": "usage-guide tool + workflow instructions",
    "no_mie": "whole MIE (get_MIE_file blocked)",
}


def load_metric(paths: list[str], metric: str) -> dict[str, float]:
    """Pool rows from all run files: question_id -> metric (last non-null wins per pooling)."""
    vals: dict[str, list[float]] = {}
    for p in paths:
        fp = Path(p)
        if not fp.exists():
            continue
        with fp.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if metric not in (reader.fieldnames or []):
                continue
            for row in reader:
                qid = row.get("question_id")
                if not qid:
                    continue
                try:
                    v = float(row[metric])
                except (TypeError, ValueError):
                    continue
                vals.setdefault(qid, []).append(v)
    # pool across runs by averaging each question's repeated scores
    return {qid: mean(vs) for qid, vs in vals.items() if vs}


def summarize(scores: dict[str, float]) -> tuple[float | None, float, int]:
    if not scores:
        return None, 0.0, 0
    xs = list(scores.values())
    return mean(xs), (pstdev(xs) if len(xs) > 1 else 0.0), len(xs)


def _fmt(x: float | None, spec: str = ".2f") -> str:
    return "n/a" if x is None else format(x, spec)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(DEFAULT_RESULTS))
    ap.add_argument("--date", default=None, help="date tag (default: newest run found)")
    ap.add_argument("--model", default=None,
                    help="answering model (disambiguates when a date has several)")
    ap.add_argument("--metric", default="togomcp_total_score")
    args = ap.parse_args()

    results = Path(args.results)
    # Runs live at results/<date>/<slug(model)>/manifest.json.
    if args.date and args.model:
        manifest_path = results / args.date / _slug(args.model) / "manifest.json"
    elif args.date:
        found = sorted(glob.glob(str(results / args.date / "*" / "manifest.json")))
        if not found:
            raise SystemExit(f"no run for date {args.date} in {results} — run run_conditions.py first")
        if len(found) > 1:
            models = ", ".join(Path(p).parent.name for p in found)
            raise SystemExit(f"date {args.date} has several models ({models}); pass --model")
        manifest_path = Path(found[0])
    else:
        found = sorted(glob.glob(str(results / "*" / "*" / "manifest.json")))
        if not found:
            raise SystemExit(f"no manifest under {results} — run run_conditions.py first")
        manifest_path = Path(found[-1])  # newest by date/model path sort
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    date = manifest["date"]
    judges = manifest["judges"]
    metric = args.metric

    # per (condition, judge) -> (mean, std, n)
    stats: dict[str, dict[str, tuple[float | None, float, int]]] = {}
    for c in manifest["conditions"]:
        cond = c["condition"]
        stats[cond] = {}
        for judge, paths in c.get("judges", {}).items():
            stats[cond][judge] = summarize(load_metric(paths, metric))

    conditions = [c["condition"] for c in manifest["conditions"]]
    out_dir = manifest_path.parent  # write summary/report beside the run's manifest

    # ---- CSV: condition x judge means + delta vs reference ----
    ref_means = {j: (stats.get(REFERENCE, {}).get(j, (None, 0, 0))[0]) for j in judges}
    summary_csv = out_dir / "summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        header = ["condition", "removes"]
        for j in judges:
            header += [f"{j}__mean", f"{j}__std", f"{j}__n", f"{j}__delta_vs_{REFERENCE}"]
        w.writerow(header)
        for cond in conditions:
            row = [cond, REMOVES.get(cond, "")]
            for j in judges:
                m, s, n = stats[cond].get(j, (None, 0, 0))
                ref = ref_means.get(j)
                delta = (ref - m) if (m is not None and ref is not None) else None
                row += [_fmt(m, ".3f"), _fmt(s, ".3f"), n, _fmt(delta, "+.3f")]
            w.writerow(row)

    write_report(out_dir / "report.md", date, manifest, judges,
                 conditions, stats, ref_means, metric)

    # console
    print(f"Metric: {metric} (max {SCORE_MAX}) | date {date} | "
          f"model {manifest['model']} | judges: {', '.join(judges)}\n")
    for cond in conditions:
        print(f"{cond:12s} {REMOVES.get(cond,''):42s}")
        for j in judges:
            m, s, n = stats[cond].get(j, (None, 0, 0))
            ref = ref_means.get(j)
            delta = (ref - m) if (m is not None and ref is not None) else None
            print(f"    {j:22s} mean {_fmt(m):>6s} ± {_fmt(s):>5s} (n={n})  "
                  f"Δvs {REFERENCE}: {_fmt(delta, '+.2f')}")
    print(f"\nwrote {summary_csv}")
    print(f"wrote {out_dir / 'report.md'}")
    return 0


def write_report(path: Path, date: str, manifest: dict, judges: list[str],
                 conditions: list[str], stats: dict, ref_means: dict, metric: str) -> None:
    lines = [
        f"# Condition Ablation — {date}",
        "",
        f"**Answering model:** `{manifest['model']}`  |  **Judges:** "
        f"{', '.join(f'`{j}`' for j in judges)}  |  **Runs/judge:** {manifest['runs']}  ",
        f"**Metric:** `{metric}` (TogoMCP with-tools LLM-judge score, max {SCORE_MAX}).  ",
        f"**Δ vs `{REFERENCE}`** = mean(full system) − mean(condition); higher ⇒ the removed "
        "component mattered more.",
        "",
        "## Mean score per condition (per judge)",
        "",
    ]
    head = "| Condition | Removes | " + " | ".join(judges) + " |"
    sep = "|---|---|" + "|".join(["---:"] * len(judges)) + "|"
    lines += [head, sep]
    for cond in conditions:
        cells = []
        for j in judges:
            m, s, n = stats[cond].get(j, (None, 0, 0))
            cells.append(f"{_fmt(m)} ± {_fmt(s)} (n={n})")
        lines.append(f"| `{cond}` | {REMOVES.get(cond,'')} | " + " | ".join(cells) + " |")

    lines += ["", f"## Component cost (Δ vs `{REFERENCE}`)", "",
              "| Condition | Removes | " + " | ".join(judges) + " |",
              "|---|---|" + "|".join(["---:"] * len(judges)) + "|"]
    for cond in conditions:
        if cond == REFERENCE:
            continue
        cells = []
        for j in judges:
            m = stats[cond].get(j, (None, 0, 0))[0]
            ref = ref_means.get(j)
            delta = (ref - m) if (m is not None and ref is not None) else None
            cells.append(f"**{_fmt(delta, '+.2f')}**")
        lines.append(f"| `{cond}` | {REMOVES.get(cond,'')} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Notes",
        "",
        "- Run against the **production** TogoMCP server; absolute numbers depend on the live "
        "server's state at run time.",
        "- Multiple judges are shown side by side — compare columns to gauge judge agreement on "
        "each component's importance.",
        f"- `{REFERENCE}` is the full system; every other row is that condition with one component "
        "removed. A near-zero Δ means the component didn't help on this question set.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
