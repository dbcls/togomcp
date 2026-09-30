#!/usr/bin/env python3
"""
TogoMCP Results Analyzer

Analyzes the CSV produced by automated_test_runner.py +
add_llm_evaluation.py and prints a structured report.

Expected CSV columns (from the pipeline):
    question_id, question_type, question, ideal_answer,
    baseline_success, baseline_answer,
    togomcp_success, togomcp_answer, tools_used,
    baseline_recall, baseline_precision, baseline_repetition,
    baseline_readability, baseline_total_score, baseline_evaluation_explanation,
    togomcp_recall, togomcp_precision, togomcp_repetition,
    togomcp_readability, togomcp_total_score, togomcp_evaluation_explanation

Optional column (runner output since 2026-09-30):
    held_out   true if the question was never used to develop or fix MIE files

Usage:
    python results_analyzer.py evaluation_results.csv [--questions-dir DIR]

The held-out split reads `held_out` from the CSV when present. For older CSVs it
falls back to the question YAMLs in --questions-dir (default: ../questions), but
only for rows whose question text still matches the YAML body; a row whose
question was replaced since the run (e.g. a retired, dev-exposed question whose
id was reused) is reported as "unmatched" instead of being misclassified.
"""

import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:  # only needed for the YAML fallback of the held-out split
    yaml = None

DEFAULT_QUESTIONS_DIR = Path(__file__).resolve().parent.parent / "questions"


SCORE_COLS = ["recall", "precision", "repetition", "readability", "total_score"]
QUESTION_TYPES = ["yes_no", "factoid", "list", "summary", "choice"]


class ResultsAnalyzer:
    """Analyzes TogoMCP evaluation results."""

    def __init__(self, csv_path: str, questions_dir: Path = DEFAULT_QUESTIONS_DIR):
        self.csv_path = Path(csv_path)
        self.questions_dir = Path(questions_dir)
        self.results = []
        self._load()

    def _load(self):
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.csv_path}")
        with open(self.csv_path, "r", encoding="utf-8") as f:
            self.results = list(csv.DictReader(f))
        print(f"✓ Loaded {len(self.results)} rows from {self.csv_path.name}\n")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bool(self, value: str) -> bool:
        return str(value).strip().lower() in ("true", "1", "yes")

    def _float(self, value: str, default: float = 0.0) -> float:
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default

    def _score(self, row: dict, agent: str, col: str) -> float:
        """Return agent score for a dimension ('baseline' or 'togomcp')."""
        return self._float(row.get(f"{agent}_{col}", "0"))

    def _evaluated_rows(self):
        """Rows where both agents produced a non-zero total score."""
        return [
            r for r in self.results
            if self._score(r, "baseline", "total_score") > 0
            and self._score(r, "togomcp", "total_score") > 0
        ]

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def overall_stats(self):
        total = len(self.results)
        if total == 0:
            return

        b_success = sum(1 for r in self.results if self._bool(r.get("baseline_success")))
        t_success = sum(1 for r in self.results if self._bool(r.get("togomcp_success")))
        tools_used = sum(1 for r in self.results if r.get("tools_used", "").strip())

        evaluated = self._evaluated_rows()
        n_eval = len(evaluated)

        def avg(agent, col):
            if not evaluated:
                return 0.0
            return sum(self._score(r, agent, col) for r in evaluated) / n_eval

        print("=" * 70)
        print("OVERALL RESULTS")
        print("=" * 70)
        print(f"\nTotal questions : {total}")
        print(f"Evaluated pairs : {n_eval}  "
              f"(both agents scored > 0)")
        print()

        print("EXECUTION SUCCESS:")
        print(f"  Baseline  : {b_success}/{total} ({b_success/total*100:.1f}%)")
        print(f"  TogoMCP   : {t_success}/{total} ({t_success/total*100:.1f}%)")
        print(f"  Used tools: {tools_used}/{total} ({tools_used/total*100:.1f}%)")
        print()

        if n_eval == 0:
            print("No evaluated pairs found — skipping score summary.\n")
            return

        print(f"AVERAGE SCORES (n={n_eval}, max per dimension = 5, total max = 20):")
        header = f"  {'Dimension':15}  {'Baseline':>9}  {'TogoMCP':>9}  {'Δ (T−B)':>9}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for col in SCORE_COLS:
            b_avg = avg("baseline", col)
            t_avg = avg("togomcp", col)
            max_val = 20 if col == "total_score" else 5
            label = col.replace("_", " ").title()
            print(f"  {label:15}  {b_avg:>9.2f}  {t_avg:>9.2f}  {t_avg - b_avg:>+9.2f}")
        print()

        # Win/loss/tie on total score
        wins = sum(
            1 for r in evaluated
            if self._score(r, "togomcp", "total_score")
            > self._score(r, "baseline", "total_score")
        )
        losses = sum(
            1 for r in evaluated
            if self._score(r, "togomcp", "total_score")
            < self._score(r, "baseline", "total_score")
        )
        ties = n_eval - wins - losses
        print("TOGOMCP vs BASELINE (by total score):")
        print(f"  TogoMCP better  : {wins}/{n_eval} ({wins/n_eval*100:.1f}%)")
        print(f"  Baseline better : {losses}/{n_eval} ({losses/n_eval*100:.1f}%)")
        print(f"  Tied            : {ties}/{n_eval} ({ties/n_eval*100:.1f}%)")
        print()

    def type_breakdown(self):
        """Per question-type score comparison — the primary analysis goal."""
        by_type = defaultdict(list)
        for r in self._evaluated_rows():
            qtype = r.get("question_type", "unknown").strip() or "unknown"
            by_type[qtype].append(r)

        print("=" * 70)
        print("BREAKDOWN BY QUESTION TYPE")
        print("=" * 70)

        # Determine ordering: known types first, then any others
        order = [t for t in QUESTION_TYPES if t in by_type]
        order += sorted(k for k in by_type if k not in QUESTION_TYPES)

        for qtype in order:
            rows = by_type[qtype]
            n = len(rows)
            print(f"\n  {qtype.upper()}  (n={n})")
            print(f"  {'Dimension':15}  {'Baseline':>9}  {'TogoMCP':>9}  {'Δ (T−B)':>9}")
            print("  " + "-" * 48)
            for col in SCORE_COLS:
                b_avg = sum(self._score(r, "baseline", col) for r in rows) / n
                t_avg = sum(self._score(r, "togomcp", col) for r in rows) / n
                label = col.replace("_", " ").title()
                print(f"  {label:15}  {b_avg:>9.2f}  {t_avg:>9.2f}  {t_avg - b_avg:>+9.2f}")
            wins = sum(
                1 for r in rows
                if self._score(r, "togomcp", "total_score")
                > self._score(r, "baseline", "total_score")
            )
            print(f"  TogoMCP wins    : {wins}/{n} ({wins/n*100:.1f}%)")

        print()

    # ------------------------------------------------------------------
    # Held-out (out-of-sample) split
    # ------------------------------------------------------------------

    @staticmethod
    def _norm(text) -> str:
        return " ".join(str(text or "").split())

    def _question_meta(self) -> dict:
        """id -> (held_out, normalized body) from the question YAMLs."""
        meta = {}
        if yaml is None or not self.questions_dir.is_dir():
            return meta
        for f in sorted(self.questions_dir.glob("question_*.yaml")):
            try:
                d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            meta[d.get("id", f.stem)] = (d.get("held_out") is True, self._norm(d.get("body")))
        return meta

    def _held_out_label(self, row: dict, meta: dict) -> str:
        """'held_out', 'development' or 'unmatched' for one result row."""
        raw = str(row.get("held_out", "")).strip().lower()
        if raw in ("true", "1", "yes"):
            return "held_out"
        if raw in ("false", "0", "no"):
            return "development"
        # Older CSV without the column: fall back to the YAML, but only if the
        # question text is unchanged (choice questions carry appended options,
        # hence startswith).
        entry = meta.get(row.get("question_id", ""))
        if entry is None:
            return "unmatched"
        held, body = entry
        if not body or not self._norm(row.get("question")).startswith(body):
            return "unmatched"
        return "held_out" if held else "development"

    def held_out_breakdown(self):
        """Scores split into held-out vs development questions."""
        rows = self._evaluated_rows()
        meta = {} if all("held_out" in r for r in self.results) else self._question_meta()
        groups = defaultdict(list)
        for r in rows:
            groups[self._held_out_label(r, meta)].append(r)

        if not groups.get("held_out"):
            return  # nothing to split: no held-out question in this run

        print("=" * 70)
        print("HELD-OUT vs DEVELOPMENT QUESTIONS")
        print("=" * 70)
        print("  held_out    = never used to develop or fix MIE files (out-of-sample)")
        print("  development = the rest; MIE work may have been tuned on these")
        print()
        print(f"  {'Group':12}  {'n':>4}  {'Baseline':>9}  {'TogoMCP':>9}  {'Δ (T−B)':>9}  {'Win %':>6}")
        print("  " + "-" * 58)
        for label in ("held_out", "development", "unmatched"):
            g = groups.get(label, [])
            if not g:
                continue
            n = len(g)
            b = sum(self._score(r, "baseline", "total_score") for r in g) / n
            t = sum(self._score(r, "togomcp", "total_score") for r in g) / n
            w = sum(1 for r in g if self._score(r, "togomcp", "total_score")
                    > self._score(r, "baseline", "total_score")) / n * 100
            print(f"  {label:12}  {n:>4}  {b:>9.2f}  {t:>9.2f}  {t - b:>+9.2f}  {w:>5.1f}%")
        if groups.get("unmatched"):
            ids = sorted({r.get("question_id", "?") for r in groups["unmatched"]})
            print(f"\n  unmatched: question changed or missing since this run: {', '.join(ids)}")
        if len(groups["held_out"]) < 30:
            print(f"\n  Note: n={len(groups['held_out'])} held-out rows; treat the split as indicative only.")
        print()

    def per_question_scores(self):
        """Table of individual question scores."""
        print("=" * 70)
        print("PER-QUESTION SCORES")
        print("=" * 70)

        header = (
            f"  {'ID':14}  {'Type':10}  "
            f"{'B-Total':>7}  {'T-Total':>7}  {'Δ':>6}  "
            f"{'Tools used':>12}"
        )
        print(header)
        print("  " + "-" * (len(header) - 2))

        for r in self.results:
            qid = r.get("question_id", "?")
            qtype = r.get("question_type", "?")
            b = self._score(r, "baseline", "total_score")
            t = self._score(r, "togomcp", "total_score")
            tools = r.get("tools_used", "").strip()
            tool_count = len(tools.split(",")) if tools else 0
            note = f"{tool_count} tool(s)" if tool_count else "none"
            print(
                f"  {qid:14}  {qtype:10}  "
                f"{b:>7.1f}  {t:>7.1f}  {t - b:>+6.1f}  "
                f"{note:>12}"
            )
        print()

    def timing_stats(self):
        """Response time summary overall and per question type."""
        b_times = [self._float(r.get("baseline_time", "0")) for r in self.results
                   if self._float(r.get("baseline_time", "0")) > 0]
        t_times = [self._float(r.get("togomcp_time", "0")) for r in self.results
                   if self._float(r.get("togomcp_time", "0")) > 0]

        print("=" * 70)
        print("RESPONSE TIMES (seconds)")
        print("=" * 70)

        if not b_times and not t_times:
            print("  No timing data found (baseline_time / togomcp_time columns missing or empty).\n")
            return

        def stats(times):
            if not times:
                return "n/a"
            avg = sum(times) / len(times)
            mn, mx = min(times), max(times)
            return f"avg={avg:.1f}s  min={mn:.1f}s  max={mx:.1f}s  (n={len(times)})"

        print(f"  Baseline  : {stats(b_times)}")
        print(f"  TogoMCP   : {stats(t_times)}")
        print()

        # Per-type breakdown
        by_type_b: dict = defaultdict(list)
        by_type_t: dict = defaultdict(list)
        for r in self.results:
            qtype = r.get("question_type", "unknown").strip() or "unknown"
            bt = self._float(r.get("baseline_time", "0"))
            tt = self._float(r.get("togomcp_time", "0"))
            if bt > 0:
                by_type_b[qtype].append(bt)
            if tt > 0:
                by_type_t[qtype].append(tt)

        all_types = [t for t in QUESTION_TYPES if t in by_type_b or t in by_type_t]
        all_types += sorted(k for k in (set(by_type_b) | set(by_type_t)) if k not in QUESTION_TYPES)

        if all_types:
            print(f"  {'Type':12}  {'Baseline avg':>13}  {'TogoMCP avg':>12}  {'Δ (T−B)':>10}")
            print("  " + "-" * 52)
            for qtype in all_types:
                b_avg = sum(by_type_b[qtype]) / len(by_type_b[qtype]) if by_type_b[qtype] else 0
                t_avg = sum(by_type_t[qtype]) / len(by_type_t[qtype]) if by_type_t[qtype] else 0
                print(f"  {qtype:12}  {b_avg:>12.1f}s  {t_avg:>11.1f}s  {t_avg - b_avg:>+9.1f}s")
        print()

    def low_scoring_questions(self, threshold: float = 10.0):
        """Flag questions where either agent scored below threshold."""
        print("=" * 70)
        print(f"LOW-SCORING QUESTIONS (total score < {threshold:.0f} for either agent)")
        print("=" * 70)

        flagged = [
            r for r in self._evaluated_rows()
            if self._score(r, "baseline", "total_score") < threshold
            or self._score(r, "togomcp", "total_score") < threshold
        ]

        if not flagged:
            print(f"\n  ✓ All evaluated questions scored ≥ {threshold:.0f} for both agents.\n")
            return

        for r in flagged:
            qid = r.get("question_id", "?")
            qtype = r.get("question_type", "?")
            b = self._score(r, "baseline", "total_score")
            t = self._score(r, "togomcp", "total_score")
            q_text = r.get("question", "")[:70]
            print(f"\n  {qid} [{qtype}]  Baseline={b:.1f}  TogoMCP={t:.1f}")
            print(f"    {q_text}{'…' if len(r.get('question','')) > 70 else ''}")
            if b < threshold:
                expl = r.get("baseline_evaluation_explanation", "")[:120]
                print(f"    Baseline note: {expl}")
            if t < threshold:
                expl = r.get("togomcp_evaluation_explanation", "")[:120]
                print(f"    TogoMCP note : {expl}")
        print()


def main():
    ap = argparse.ArgumentParser(description="Analyze TogoMCP evaluation results.")
    ap.add_argument("csv", help="evaluated results CSV")
    ap.add_argument("--questions-dir", default=str(DEFAULT_QUESTIONS_DIR),
                    help="question YAMLs, used for the held-out split of older CSVs "
                         "(default: %(default)s)")
    args = ap.parse_args()

    try:
        analyzer = ResultsAnalyzer(args.csv, args.questions_dir)
        analyzer.overall_stats()
        analyzer.type_breakdown()
        analyzer.held_out_breakdown()
        analyzer.timing_stats()
        analyzer.per_question_scores()
        analyzer.low_scoring_questions()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
