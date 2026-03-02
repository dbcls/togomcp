#!/usr/bin/env python3
"""
TogoMCP Visual Dashboard Generator

Creates an interactive HTML dashboard from the CSV produced by
automated_test_runner.py + add_llm_evaluation.py.

Expected CSV columns:
    question_id, question_type, question, ideal_answer,
    baseline_success, baseline_time, baseline_answer,
    togomcp_success, togomcp_time, togomcp_answer, tools_used,
    baseline_recall, baseline_precision, baseline_repetition,
    baseline_readability, baseline_total_score, baseline_evaluation_explanation,
    togomcp_recall, togomcp_precision, togomcp_repetition,
    togomcp_readability, togomcp_total_score, togomcp_evaluation_explanation

Usage:
    python generate_dashboard.py evaluation_results.csv
    python generate_dashboard.py evaluation_results.csv -o dashboard.html
    python generate_dashboard.py evaluation_results.csv --open
"""

import csv
import json
import sys
import argparse
import webbrowser
from pathlib import Path
from typing import List, Dict
from collections import Counter, defaultdict


SCORE_DIMS = ["recall", "precision", "repetition", "readability"]
QUESTION_TYPES = ["yes_no", "factoid", "list", "summary", "choice"]


class DashboardGenerator:
    """Generate interactive HTML dashboard from evaluation results."""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.results = []
        self._load()

    def _load(self):
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.csv_path}")
        with open(self.csv_path, "r", encoding="utf-8") as f:
            self.results = list(csv.DictReader(f))
        print(f"✓ Loaded {len(self.results)} results from {self.csv_path.name}")

    def _bool(self, value: str) -> bool:
        return str(value).strip().lower() in ("true", "1", "yes")

    def _float(self, value: str, default: float = 0.0) -> float:
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default

    def _score(self, row: dict, agent: str, col: str) -> float:
        return self._float(row.get(f"{agent}_{col}", "0"))

    def _evaluated_rows(self):
        return [
            r for r in self.results
            if self._score(r, "baseline", "total_score") > 0
            and self._score(r, "togomcp", "total_score") > 0
        ]

    # ------------------------------------------------------------------
    # Data builders
    # ------------------------------------------------------------------

    def _overall_score_data(self) -> Dict:
        """Average scores per dimension for both agents."""
        rows = self._evaluated_rows()
        n = len(rows) or 1
        labels = [d.replace("_", " ").title() for d in SCORE_DIMS] + ["Total Score"]
        cols = SCORE_DIMS + ["total_score"]
        b_avgs = [sum(self._score(r, "baseline", c) for r in rows) / n for c in cols]
        t_avgs = [sum(self._score(r, "togomcp", c) for r in rows) / n for c in cols]
        return {"labels": labels, "baseline": b_avgs, "togomcp": t_avgs, "n": len(rows)}

    def _type_breakdown_data(self) -> Dict:
        """Average total score per question type."""
        by_type = defaultdict(list)
        for r in self._evaluated_rows():
            qtype = r.get("question_type", "unknown").strip() or "unknown"
            by_type[qtype].append(r)

        order = [t for t in QUESTION_TYPES if t in by_type]
        order += sorted(k for k in by_type if k not in QUESTION_TYPES)

        labels, b_avgs, t_avgs, counts = [], [], [], []
        for qtype in order:
            rows = by_type[qtype]
            n = len(rows)
            labels.append(qtype)
            b_avgs.append(sum(self._score(r, "baseline", "total_score") for r in rows) / n)
            t_avgs.append(sum(self._score(r, "togomcp", "total_score") for r in rows) / n)
            counts.append(n)
        return {"labels": labels, "baseline": b_avgs, "togomcp": t_avgs, "counts": counts}

    def _win_loss_data(self) -> Dict:
        """Win / loss / tie counts (TogoMCP vs Baseline)."""
        wins = losses = ties = 0
        for r in self._evaluated_rows():
            b = self._score(r, "baseline", "total_score")
            t = self._score(r, "togomcp", "total_score")
            if t > b:
                wins += 1
            elif t < b:
                losses += 1
            else:
                ties += 1
        return {
            "labels": ["TogoMCP better", "Baseline better", "Tied"],
            "values": [wins, losses, ties],
            "colors": ["#3b82f6", "#f59e0b", "#9ca3af"],
        }

    def _score_distribution_data(self) -> Dict:
        """Histogram buckets for total scores (0-20, step 2)."""
        buckets = list(range(0, 22, 2))
        labels = [f"{lo}\u2013{lo+2}" for lo in buckets[:-1]]
        b_hist = [0] * len(labels)
        t_hist = [0] * len(labels)
        for r in self._evaluated_rows():
            b = self._score(r, "baseline", "total_score")
            t = self._score(r, "togomcp", "total_score")
            for i, lo in enumerate(buckets[:-1]):
                if lo <= b < lo + 2:
                    b_hist[i] += 1
                if lo <= t < lo + 2:
                    t_hist[i] += 1
        return {"labels": labels, "baseline": b_hist, "togomcp": t_hist}

    def _tool_usage_data(self) -> Dict:
        """Top-10 tools by call count."""
        counter = Counter()
        for r in self.results:
            tools_str = r.get("tools_used", "").strip()
            if tools_str:
                counter.update(t.strip() for t in tools_str.split(","))
        top = counter.most_common(10)
        return {
            "tools": [t[0] for t in top],
            "counts": [t[1] for t in top],
            "total_unique": len(counter),
            "total_calls": sum(counter.values()),
        }

    def _timing_data(self) -> Dict:
        """Average and per-type response times."""
        b_times = [self._float(r.get("baseline_time", "0")) for r in self.results
                   if self._float(r.get("baseline_time", "0")) > 0]
        t_times = [self._float(r.get("togomcp_time", "0")) for r in self.results
                   if self._float(r.get("togomcp_time", "0")) > 0]

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

        order = [t for t in QUESTION_TYPES if t in by_type_b or t in by_type_t]
        order += sorted(k for k in (set(by_type_b) | set(by_type_t)) if k not in QUESTION_TYPES)

        return {
            "avg_baseline": sum(b_times) / len(b_times) if b_times else 0,
            "avg_togomcp": sum(t_times) / len(t_times) if t_times else 0,
            "type_labels": order,
            "type_baseline": [
                sum(by_type_b[t]) / len(by_type_b[t]) if by_type_b[t] else 0
                for t in order
            ],
            "type_togomcp": [
                sum(by_type_t[t]) / len(by_type_t[t]) if by_type_t[t] else 0
                for t in order
            ],
        }

    def _per_question_data(self) -> List[Dict]:
        """Per-question data for the detail table."""
        rows = []
        for r in self.results:
            rows.append({
                "id": r.get("question_id", ""),
                "type": r.get("question_type", ""),
                "question": r.get("question", "")[:80],
                "b_total": self._score(r, "baseline", "total_score"),
                "t_total": self._score(r, "togomcp", "total_score"),
                "delta": (self._score(r, "togomcp", "total_score")
                          - self._score(r, "baseline", "total_score")),
                "b_time": self._float(r.get("baseline_time", "0")),
                "t_time": self._float(r.get("togomcp_time", "0")),
                "tools": r.get("tools_used", "").strip(),
            })
        return rows

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def _build_table_rows(self, per_q: List[Dict]) -> str:
        """Build HTML rows for the per-question table (avoids f-string nesting)."""
        rows_html = ""
        for q in per_q:
            delta = q["delta"]
            delta_color = "#10b981" if delta > 0 else ("#ef4444" if delta < 0 else "#6b7280")
            sign = "+" if delta > 0 else ""
            tool_count = len(q["tools"].split(",")) if q["tools"] else 0
            b_time_str = f"{q['b_time']:.1f}s" if q["b_time"] > 0 else "—"
            t_time_str = f"{q['t_time']:.1f}s" if q["t_time"] > 0 else "—"
            rows_html += (
                "<tr>"
                f"<td>{q['id']}</td>"
                f"<td><span class='type-badge'>{q['type']}</span></td>"
                f"<td class='question-cell' title='{q['question']}'>{q['question']}\u2026</td>"
                f"<td>{q['b_total']:.1f}</td>"
                f"<td>{q['t_total']:.1f}</td>"
                f"<td style='color:{delta_color};font-weight:600'>{sign}{delta:.1f}</td>"
                f"<td>{b_time_str}</td>"
                f"<td>{t_time_str}</td>"
                f"<td>{tool_count}</td>"
                "</tr>\n"
            )
        return rows_html

    def generate_html(self, output_path: str) -> str:
        overall  = self._overall_score_data()
        type_bd  = self._type_breakdown_data()
        win_loss = self._win_loss_data()
        score_dist = self._score_distribution_data()
        tool_data  = self._tool_usage_data()
        timing     = self._timing_data()
        per_q      = self._per_question_data()

        total = len(self.results)
        n_eval = overall["n"]
        b_avg_total = overall["baseline"][-1]
        t_avg_total = overall["togomcp"][-1]
        tools_used_count = sum(1 for r in self.results if r.get("tools_used", "").strip())
        table_rows_html = self._build_table_rows(per_q)

        html = (
            "<!DOCTYPE html>\n"
            "<html lang='en'>\n"
            "<head>\n"
            "  <meta charset='UTF-8'>\n"
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            "  <title>TogoMCP Evaluation Dashboard</title>\n"
            "  <script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'></script>\n"
            "  <style>\n"
            "    * { margin:0; padding:0; box-sizing:border-box; }\n"
            "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n"
            "           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n"
            "           padding: 20px; min-height: 100vh; }\n"
            "    .container { max-width: 1400px; margin: 0 auto; }\n"
            "    .card { background: white; padding: 25px; border-radius: 12px;\n"
            "            box-shadow: 0 4px 12px rgba(0,0,0,0.12); margin-bottom: 20px; }\n"
            "    h1 { color: #1f2937; font-size: 2em; margin-bottom: 8px; }\n"
            "    h2 { color: #374151; font-size: 1.2em; margin-bottom: 18px; font-weight: 600; }\n"
            "    .subtitle { color: #6b7280; font-size: 0.95em; }\n"
            "    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr));\n"
            "                  gap: 16px; margin-bottom: 20px; }\n"
            "    .stat-card { background: white; padding: 20px; border-radius: 12px;\n"
            "                 box-shadow: 0 4px 12px rgba(0,0,0,0.12); border-left: 4px solid #667eea; }\n"
            "    .stat-label { color: #6b7280; font-size: 0.8em; text-transform: uppercase;\n"
            "                  letter-spacing: 0.5px; margin-bottom: 6px; }\n"
            "    .stat-value { color: #1f2937; font-size: 2.2em; font-weight: 700; }\n"
            "    .stat-sub   { color: #9ca3af; font-size: 0.85em; margin-top: 4px; }\n"
            "    .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(480px,1fr));\n"
            "                   gap: 20px; }\n"
            "    .chart-container { position: relative; height: 300px; }\n"
            "    table { width: 100%; border-collapse: collapse; font-size: 0.88em; }\n"
            "    th { background: #f3f4f6; color: #374151; padding: 10px 12px; text-align: left;\n"
            "         font-weight: 600; border-bottom: 2px solid #e5e7eb; }\n"
            "    td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }\n"
            "    tr:hover td { background: #fafafa; }\n"
            "    .type-badge { display: inline-block; padding: 2px 8px; border-radius: 9999px;\n"
            "                  font-size: 0.78em; font-weight: 600; background: #ede9fe; color: #6d28d9; }\n"
            "    .question-cell { max-width: 280px; color: #4b5563; font-size: 0.85em; }\n"
            "    .mono { font-family: monospace; font-size: 0.9em; color: #374151; }\n"
            "    .footer { text-align: center; color: #e5e7eb; margin-top: 10px; font-size: 0.85em; }\n"
            "    @media (max-width:800px) { .charts-grid { grid-template-columns: 1fr; } }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            "<div class='container'>\n"

            # ── Header ──────────────────────────────────────────────────────────
            "  <div class='card'>\n"
            f"    <h1>&#128202; TogoMCP Evaluation Dashboard</h1>\n"
            f"    <p class='subtitle'>{total} questions &middot; {n_eval} evaluated pairs"
            f" &middot; {self.csv_path.name}</p>\n"
            "  </div>\n"

            # ── Stat cards ───────────────────────────────────────────────────────
            "  <div class='stats-grid'>\n"
            "    <div class='stat-card'>\n"
            "      <div class='stat-label'>Total Questions</div>\n"
            f"     <div class='stat-value'>{total}</div>\n"
            f"     <div class='stat-sub'>{n_eval} with LLM scores</div>\n"
            "    </div>\n"
            "    <div class='stat-card' style='border-left-color:#f59e0b'>\n"
            "      <div class='stat-label'>Avg Baseline Score</div>\n"
            f"     <div class='stat-value'>{b_avg_total:.1f}</div>\n"
            "      <div class='stat-sub'>out of 20</div>\n"
            "    </div>\n"
            "    <div class='stat-card' style='border-left-color:#3b82f6'>\n"
            "      <div class='stat-label'>Avg TogoMCP Score</div>\n"
            f"     <div class='stat-value'>{t_avg_total:.1f}</div>\n"
            f"     <div class='stat-sub'>out of 20 (&Delta; {t_avg_total - b_avg_total:+.1f})</div>\n"
            "    </div>\n"
            "    <div class='stat-card' style='border-left-color:#f97316'>\n"
            "      <div class='stat-label'>Avg Baseline Time</div>\n"
            f"     <div class='stat-value'>{timing['avg_baseline']:.1f}s</div>\n"
            "      <div class='stat-sub'>per question</div>\n"
            "    </div>\n"
            "    <div class='stat-card' style='border-left-color:#06b6d4'>\n"
            "      <div class='stat-label'>Avg TogoMCP Time</div>\n"
            f"     <div class='stat-value'>{timing['avg_togomcp']:.1f}s</div>\n"
            "      <div class='stat-sub'>per question</div>\n"
            "    </div>\n"
            "    <div class='stat-card' style='border-left-color:#10b981'>\n"
            "      <div class='stat-label'>Used Tools</div>\n"
            f"     <div class='stat-value'>{tools_used_count}</div>\n"
            f"     <div class='stat-sub'>of {total} questions"
            f" ({tools_used_count / total * 100:.0f}%)</div>\n"
            "    </div>\n"
            "    <div class='stat-card' style='border-left-color:#8b5cf6'>\n"
            "      <div class='stat-label'>Unique Tools</div>\n"
            f"     <div class='stat-value'>{tool_data['total_unique']}</div>\n"
            f"     <div class='stat-sub'>{tool_data['total_calls']} total calls</div>\n"
            "    </div>\n"
            "  </div>\n"

            # ── Charts ──────────────────────────────────────────────────────────
            "  <div class='charts-grid'>\n"
            "    <div class='card'>\n"
            "      <h2>Score Dimensions &mdash; Baseline vs TogoMCP</h2>\n"
            "      <div class='chart-container'><canvas id='dimChart'></canvas></div>\n"
            "    </div>\n"
            "    <div class='card'>\n"
            "      <h2>Win / Loss / Tie (by total score)</h2>\n"
            "      <div class='chart-container'><canvas id='winLossChart'></canvas></div>\n"
            "    </div>\n"
            "    <div class='card'>\n"
            "      <h2>Average Total Score by Question Type</h2>\n"
            "      <div class='chart-container'><canvas id='typeChart'></canvas></div>\n"
            "    </div>\n"
            "    <div class='card'>\n"
            "      <h2>Total Score Distribution</h2>\n"
            "      <div class='chart-container'><canvas id='distChart'></canvas></div>\n"
            "    </div>\n"
            "    <div class='card'>\n"
            "      <h2>Response Time by Question Type (seconds)</h2>\n"
            "      <div class='chart-container'><canvas id='timeTypeChart'></canvas></div>\n"
            "    </div>\n"
            "    <div class='card'>\n"
            "      <h2>Top Tools Used by TogoMCP</h2>\n"
            "      <div class='chart-container'><canvas id='toolChart'></canvas></div>\n"
            "    </div>\n"
            "  </div>\n"

            # ── Per-question table ───────────────────────────────────────────────
            "  <div class='card'>\n"
            "    <h2>Per-Question Detail</h2>\n"
            "    <table>\n"
            "      <thead><tr>\n"
            "        <th>ID</th><th>Type</th><th>Question (truncated)</th>\n"
            "        <th>Baseline /20</th><th>TogoMCP /20</th><th>&Delta; (T&minus;B)</th>\n"
            "        <th>B-Time</th><th>T-Time</th><th>Tools #</th>\n"
            "      </tr></thead>\n"
            f"     <tbody>\n{table_rows_html}     </tbody>\n"
            "    </table>\n"
            "  </div>\n"

            "  <div class='footer'>Generated by TogoMCP Dashboard Generator</div>\n"
            "</div>\n"

            # ── JavaScript ──────────────────────────────────────────────────────
            "<script>\n"

            # Dimension comparison
            "new Chart(document.getElementById('dimChart'), {\n"
            "  type: 'bar',\n"
            f"  data: {{ labels: {json.dumps(overall['labels'])},\n"
            "    datasets: [\n"
            f"      {{ label: 'Baseline', data: {json.dumps([round(x,2) for x in overall['baseline']])}, backgroundColor: '#f59e0b' }},\n"
            f"      {{ label: 'TogoMCP', data: {json.dumps([round(x,2) for x in overall['togomcp']])}, backgroundColor: '#3b82f6' }}\n"
            "    ]\n"
            "  },\n"
            "  options: { responsive:true, maintainAspectRatio:false,\n"
            "    scales: { y: { beginAtZero:true, max:20 } },\n"
            "    plugins: { legend: { position:'top' } }\n"
            "  }\n"
            "});\n\n"

            # Win/loss/tie
            "new Chart(document.getElementById('winLossChart'), {\n"
            "  type: 'doughnut',\n"
            f"  data: {{ labels: {json.dumps(win_loss['labels'])},\n"
            f"    datasets: [{{ data: {json.dumps(win_loss['values'])}, backgroundColor: {json.dumps(win_loss['colors'])} }}]\n"
            "  },\n"
            "  options: { responsive:true, maintainAspectRatio:false,\n"
            "    plugins: { legend: { position:'right' } }\n"
            "  }\n"
            "});\n\n"

            # Score by type
            "new Chart(document.getElementById('typeChart'), {\n"
            "  type: 'bar',\n"
            f"  data: {{ labels: {json.dumps(type_bd['labels'])},\n"
            "    datasets: [\n"
            f"      {{ label: 'Baseline', data: {json.dumps([round(x,2) for x in type_bd['baseline']])}, backgroundColor: '#f59e0b' }},\n"
            f"      {{ label: 'TogoMCP', data: {json.dumps([round(x,2) for x in type_bd['togomcp']])}, backgroundColor: '#3b82f6' }}\n"
            "    ]\n"
            "  },\n"
            "  options: { responsive:true, maintainAspectRatio:false,\n"
            "    scales: { y: { beginAtZero:true, max:20, title:{ display:true, text:'Avg Total Score' } } },\n"
            "    plugins: { legend: { position:'top' },\n"
            "      tooltip: { callbacks: { afterLabel: function(ctx) {\n"
            f"        const counts = {json.dumps(type_bd['counts'])};\n"
            "        return 'n = ' + counts[ctx.dataIndex]; } } }\n"
            "    }\n"
            "  }\n"
            "});\n\n"

            # Score distribution
            "new Chart(document.getElementById('distChart'), {\n"
            "  type: 'bar',\n"
            f"  data: {{ labels: {json.dumps(score_dist['labels'])},\n"
            "    datasets: [\n"
            f"      {{ label: 'Baseline', data: {json.dumps(score_dist['baseline'])}, backgroundColor: 'rgba(245,158,11,0.7)' }},\n"
            f"      {{ label: 'TogoMCP', data: {json.dumps(score_dist['togomcp'])}, backgroundColor: 'rgba(59,130,246,0.7)' }}\n"
            "    ]\n"
            "  },\n"
            "  options: { responsive:true, maintainAspectRatio:false,\n"
            "    scales: {\n"
            "      x: { title: { display:true, text:'Total Score Range' } },\n"
            "      y: { beginAtZero:true, title:{ display:true, text:'Number of Questions' }, ticks:{ stepSize:1 } }\n"
            "    },\n"
            "    plugins: { legend: { position:'top' } }\n"
            "  }\n"
            "});\n\n"

            # Response time by type
            "new Chart(document.getElementById('timeTypeChart'), {\n"
            "  type: 'bar',\n"
            f"  data: {{ labels: {json.dumps(timing['type_labels'])},\n"
            "    datasets: [\n"
            f"      {{ label: 'Baseline (s)', data: {json.dumps([round(x,1) for x in timing['type_baseline']])}, backgroundColor: '#f97316' }},\n"
            f"      {{ label: 'TogoMCP (s)', data: {json.dumps([round(x,1) for x in timing['type_togomcp']])}, backgroundColor: '#06b6d4' }}\n"
            "    ]\n"
            "  },\n"
            "  options: { responsive:true, maintainAspectRatio:false,\n"
            "    scales: { y: { beginAtZero:true, title:{ display:true, text:'Avg seconds' } } },\n"
            "    plugins: { legend: { position:'top' } }\n"
            "  }\n"
            "});\n\n"

            # Tool usage
            "new Chart(document.getElementById('toolChart'), {\n"
            "  type: 'bar',\n"
            f"  data: {{ labels: {json.dumps(tool_data['tools'])},\n"
            f"    datasets: [{{ label: 'Times Used', data: {json.dumps(tool_data['counts'])}, backgroundColor: '#8b5cf6' }}]\n"
            "  },\n"
            "  options: { responsive:true, maintainAspectRatio:false, indexAxis:'y',\n"
            "    scales: { x: { beginAtZero:true } },\n"
            "    plugins: { legend: { display:false } }\n"
            "  }\n"
            "});\n"
            "</script>\n"
            "</body>\n"
            "</html>\n"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ Dashboard written to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML dashboard from TogoMCP evaluation results"
    )
    parser.add_argument("results_file", help="Evaluated CSV file")
    parser.add_argument("-o", "--output", default="evaluation_dashboard.html",
                        help="Output HTML path (default: evaluation_dashboard.html)")
    parser.add_argument("--open", action="store_true",
                        help="Open dashboard in browser after generation")
    args = parser.parse_args()

    try:
        gen = DashboardGenerator(args.results_file)
        out = gen.generate_html(args.output)
        if args.open:
            print("Opening in browser\u2026")
            webbrowser.open(f"file://{Path(out).absolute()}")
    except FileNotFoundError as e:
        print(f"\u2717 {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\u2717 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
