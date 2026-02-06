#!/usr/bin/env python3
"""
TogoMCP Visual Dashboard Generator

Creates an interactive HTML dashboard with charts and visualizations from
evaluation results.

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


class DashboardGenerator:
    """Generate visual dashboard from evaluation results."""
    
    def __init__(self, csv_path: str):
        """Initialize with CSV results."""
        self.csv_path = Path(csv_path)
        self.results = []
        self.load_results()
    
    def load_results(self):
        """Load results from CSV."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.results = list(reader)
        
        print(f"✓ Loaded {len(self.results)} results from {self.csv_path.name}")
    
    def _parse_bool(self, value: str) -> bool:
        """Parse boolean values."""
        return value.strip().lower() in ('true', '1', 'yes')
    
    def _parse_float(self, value: str, default: float = 0.0) -> float:
        """Parse float values."""
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def get_success_rate_data(self) -> Dict:
        """Get success rate comparison data based on Has Expected Answer."""
        total = len(self.results)
        baseline_has_expected = sum(1 for r in self.results if self._parse_bool(r.get('baseline_has_expected', 'False')))
        togomcp_has_expected = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_has_expected', 'False')))
        
        return {
            "labels": ["Baseline", "TogoMCP"],
            "has_expected": [baseline_has_expected, togomcp_has_expected],
            "missing_expected": [total - baseline_has_expected, total - togomcp_has_expected],
            "total": total
        }
    
    def get_category_data(self) -> Dict:
        """Get per-category statistics based on Has Expected Answer."""
        categories = defaultdict(lambda: {"baseline": 0, "togomcp": 0, "total": 0})
        
        for result in self.results:
            category = result.get('category', 'Unknown')
            categories[category]["total"] += 1
            
            if self._parse_bool(result.get('baseline_has_expected', 'False')):
                categories[category]["baseline"] += 1
            
            if self._parse_bool(result.get('togomcp_has_expected', 'False')):
                categories[category]["togomcp"] += 1
        
        return {
            "categories": sorted(categories.keys()),
            "baseline": [categories[c]["baseline"] for c in sorted(categories.keys())],
            "togomcp": [categories[c]["togomcp"] for c in sorted(categories.keys())],
            "total": [categories[c]["total"] for c in sorted(categories.keys())]
        }
    
    def get_tool_usage_data(self) -> Dict:
        """Get tool usage statistics."""
        all_tools = []
        
        for result in self.results:
            tools_str = result.get('tools_used', '').strip()
            if tools_str:
                tools = [t.strip() for t in tools_str.split(',')]
                all_tools.extend(tools)
        
        tool_counts = Counter(all_tools)
        top_10 = tool_counts.most_common(10)
        
        return {
            "tools": [t[0] for t in top_10],
            "counts": [t[1] for t in top_10],
            "total_unique": len(tool_counts),
            "total_calls": sum(tool_counts.values())
        }
    
    def get_performance_data(self) -> Dict:
        """Get response time comparison."""
        baseline_times = []
        togomcp_times = []
        
        for result in self.results:
            bt = self._parse_float(result.get('baseline_time', '0'))
            tt = self._parse_float(result.get('togomcp_time', '0'))
            
            if bt > 0:
                baseline_times.append(bt)
            if tt > 0:
                togomcp_times.append(tt)
        
        return {
            "baseline_times": baseline_times,
            "togomcp_times": togomcp_times,
            "avg_baseline": sum(baseline_times) / len(baseline_times) if baseline_times else 0,
            "avg_togomcp": sum(togomcp_times) / len(togomcp_times) if togomcp_times else 0
        }
    
    def get_success_pattern_data(self) -> Dict:
        """Get pattern breakdown based on Has Expected Answer."""
        both_have_expected = 0
        only_baseline = 0
        only_togomcp = 0
        neither_have_expected = 0
        
        for result in self.results:
            baseline_has = self._parse_bool(result.get('baseline_has_expected', 'False'))
            togomcp_has = self._parse_bool(result.get('togomcp_has_expected', 'False'))
            
            if baseline_has and togomcp_has:
                both_have_expected += 1
            elif baseline_has and not togomcp_has:
                only_baseline += 1
            elif not baseline_has and togomcp_has:
                only_togomcp += 1
            else:
                neither_have_expected += 1
        
        return {
            "labels": ["Both Have Expected", "Only Baseline", "Only TogoMCP", "Neither Have Expected"],
            "values": [both_have_expected, only_baseline, only_togomcp, neither_have_expected],
            "colors": ["#10b981", "#f59e0b", "#3b82f6", "#ef4444"]
        }
    
    def generate_html(self, output_path: str):
        """Generate interactive HTML dashboard."""
        success_data = self.get_success_rate_data()
        category_data = self.get_category_data()
        tool_data = self.get_tool_usage_data()
        perf_data = self.get_performance_data()
        pattern_data = self.get_success_pattern_data()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TogoMCP Evaluation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #1f2937;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #6b7280;
            font-size: 1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .stat-label {{
            color: #6b7280;
            font-size: 0.9em;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-value {{
            color: #1f2937;
            font-size: 2.5em;
            font-weight: bold;
        }}
        
        .stat-subvalue {{
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }}
        
        .chart-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            color: #1f2937;
            font-size: 1.3em;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        .footer {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
            color: #6b7280;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 TogoMCP Evaluation Dashboard</h1>
            <div class="subtitle">Analysis of {len(self.results)} evaluation results from {self.csv_path.name}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Questions</div>
                <div class="stat-value">{len(self.results)}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Baseline Has Expected Answer</div>
                <div class="stat-value">{success_data['has_expected'][0] / success_data['total'] * 100:.1f}%</div>
                <div class="stat-subvalue">{success_data['has_expected'][0]}/{success_data['total']} have expected</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">TogoMCP Has Expected Answer</div>
                <div class="stat-value">{success_data['has_expected'][1] / success_data['total'] * 100:.1f}%</div>
                <div class="stat-subvalue">{success_data['has_expected'][1]}/{success_data['total']} have expected</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Tools Used</div>
                <div class="stat-value">{tool_data['total_unique']}</div>
                <div class="stat-subvalue">{tool_data['total_calls']} total calls</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Has Expected Answer Comparison</div>
                <div class="chart-container">
                    <canvas id="successChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Expected Answer Pattern Distribution</div>
                <div class="chart-container">
                    <canvas id="patternChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Category Performance</div>
                <div class="chart-container">
                    <canvas id="categoryChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Top Tools Used</div>
                <div class="chart-container">
                    <canvas id="toolChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">Response Time Comparison</div>
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Generated by TogoMCP Visual Dashboard Generator
        </div>
    </div>
    
    <script>
        // Has Expected Answer Chart
        new Chart(document.getElementById('successChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(success_data['labels'])},
                datasets: [
                    {{
                        label: 'Has Expected Answer',
                        data: {json.dumps(success_data['has_expected'])},
                        backgroundColor: '#10b981'
                    }},
                    {{
                        label: 'Missing Expected Answer',
                        data: {json.dumps(success_data['missing_expected'])},
                        backgroundColor: '#ef4444'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ stacked: true }},
                    y: {{ stacked: true, beginAtZero: true }}
                }},
                plugins: {{
                    legend: {{ position: 'top' }}
                }}
            }}
        }});
        
        // Expected Answer Pattern Chart
        new Chart(document.getElementById('patternChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(pattern_data['labels'])},
                datasets: [{{
                    data: {json.dumps(pattern_data['values'])},
                    backgroundColor: {json.dumps(pattern_data['colors'])}
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'right' }}
                }}
            }}
        }});
        
        // Category Chart
        new Chart(document.getElementById('categoryChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(category_data['categories'])},
                datasets: [
                    {{
                        label: 'Baseline',
                        data: {json.dumps(category_data['baseline'])},
                        backgroundColor: '#f59e0b'
                    }},
                    {{
                        label: 'TogoMCP',
                        data: {json.dumps(category_data['togomcp'])},
                        backgroundColor: '#3b82f6'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ beginAtZero: true }}
                }},
                plugins: {{
                    legend: {{ position: 'top' }}
                }}
            }}
        }});
        
        // Tool Usage Chart
        new Chart(document.getElementById('toolChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(tool_data['tools'])},
                datasets: [{{
                    label: 'Times Used',
                    data: {json.dumps(tool_data['counts'])},
                    backgroundColor: '#8b5cf6'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {{
                    x: {{ beginAtZero: true }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
        
        // Performance Chart
        new Chart(document.getElementById('performanceChart'), {{
            type: 'bar',
            data: {{
                labels: ['Baseline', 'TogoMCP'],
                datasets: [{{
                    label: 'Avg Response Time (seconds)',
                    data: [{perf_data['avg_baseline']:.2f}, {perf_data['avg_togomcp']:.2f}],
                    backgroundColor: ['#f59e0b', '#3b82f6']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ beginAtZero: true }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ Dashboard generated: {output_path}")
        return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate visual dashboard from TogoMCP evaluation results"
    )
    
    parser.add_argument("results_file", help="Path to evaluation_results.csv")
    parser.add_argument(
        "-o", "--output",
        help="Output HTML file path",
        default="evaluation_dashboard.html"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open dashboard in browser after generation"
    )
    
    args = parser.parse_args()
    
    try:
        generator = DashboardGenerator(args.results_file)
        output_path = generator.generate_html(args.output)
        
        if args.open:
            print(f"Opening dashboard in browser...")
            webbrowser.open(f"file://{Path(output_path).absolute()}")
    
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
