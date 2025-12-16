#!/usr/bin/env python3
"""
TogoMCP Evaluation Results Analyzer

Analyzes evaluation_results.csv to provide insights on:
- Success rates (baseline vs TogoMCP)
- Performance metrics (response times, token usage)
- Tool usage patterns
- Category-based analysis
- Comparative statistics

Usage:
    python results_analyzer.py evaluation_results.csv
    python results_analyzer.py evaluation_results.csv -v  # Verbose mode
    python results_analyzer.py evaluation_results.csv --export summary_report.md
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
import argparse
from datetime import datetime


class EvaluationAnalyzer:
    """Analyzes TogoMCP evaluation results."""
    
    def __init__(self, csv_path: str):
        """Initialize analyzer with CSV file."""
        self.csv_path = Path(csv_path)
        self.results = []
        self.load_results()
    
    def load_results(self):
        """Load results from CSV file."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.results = list(reader)
        
        print(f"✓ Loaded {len(self.results)} evaluation results from {self.csv_path.name}\n")
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean values."""
        return value.strip().lower() in ('true', '1', 'yes')
    
    def _parse_float(self, value: str, default: float = 0.0) -> float:
        """Parse float values safely."""
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def _parse_int(self, value: str, default: int = 0) -> int:
        """Parse int values safely."""
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def get_overall_stats(self) -> Dict:
        """Calculate overall statistics."""
        total = len(self.results)
        if total == 0:
            return {}
        
        baseline_success = sum(1 for r in self.results if self._parse_bool(r.get('baseline_success', 'False')))
        togomcp_success = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_success', 'False')))
        
        tools_used_count = sum(1 for r in self.results if r.get('tools_used', '').strip())
        
        baseline_times = [self._parse_float(r.get('baseline_time', '0')) for r in self.results]
        togomcp_times = [self._parse_float(r.get('togomcp_time', '0')) for r in self.results]
        
        baseline_input_tokens = [self._parse_int(r.get('baseline_input_tokens', '0')) for r in self.results]
        baseline_output_tokens = [self._parse_int(r.get('baseline_output_tokens', '0')) for r in self.results]
        
        return {
            'total': total,
            'baseline_success': baseline_success,
            'baseline_success_rate': baseline_success / total * 100,
            'togomcp_success': togomcp_success,
            'togomcp_success_rate': togomcp_success / total * 100,
            'tools_used_count': tools_used_count,
            'tools_used_rate': tools_used_count / total * 100,
            'avg_baseline_time': sum(baseline_times) / len(baseline_times) if baseline_times else 0,
            'avg_togomcp_time': sum(togomcp_times) / len(togomcp_times) if togomcp_times else 0,
            'total_baseline_input_tokens': sum(baseline_input_tokens),
            'total_baseline_output_tokens': sum(baseline_output_tokens),
            'avg_baseline_input_tokens': sum(baseline_input_tokens) / len(baseline_input_tokens) if baseline_input_tokens else 0,
            'avg_baseline_output_tokens': sum(baseline_output_tokens) / len(baseline_output_tokens) if baseline_output_tokens else 0,
        }
    
    def get_category_breakdown(self) -> Dict[str, Dict]:
        """Breakdown statistics by question category."""
        categories = defaultdict(list)
        
        for result in self.results:
            category = result.get('category', 'Unknown')
            categories[category].append(result)
        
        breakdown = {}
        for category, results in categories.items():
            total = len(results)
            baseline_success = sum(1 for r in results if self._parse_bool(r.get('baseline_success', 'False')))
            togomcp_success = sum(1 for r in results if self._parse_bool(r.get('togomcp_success', 'False')))
            tools_used = sum(1 for r in results if r.get('tools_used', '').strip())
            
            breakdown[category] = {
                'count': total,
                'baseline_success': baseline_success,
                'togomcp_success': togomcp_success,
                'tools_used': tools_used,
                'baseline_success_rate': baseline_success / total * 100 if total > 0 else 0,
                'togomcp_success_rate': togomcp_success / total * 100 if total > 0 else 0,
                'tools_used_rate': tools_used / total * 100 if total > 0 else 0,
            }
        
        return breakdown
    
    def get_tool_usage_stats(self) -> Dict:
        """Analyze which tools were used and how often."""
        all_tools = []
        tool_combinations = []
        
        for result in self.results:
            tools_str = result.get('tools_used', '').strip()
            if tools_str:
                tools = [t.strip() for t in tools_str.split(',')]
                all_tools.extend(tools)
                tool_combinations.append(tuple(sorted(tools)))
        
        tool_counts = Counter(all_tools)
        combination_counts = Counter(tool_combinations)
        
        return {
            'individual_tools': dict(tool_counts.most_common()),
            'tool_combinations': dict(combination_counts.most_common(10)),  # Top 10 combinations
            'unique_tools': len(tool_counts),
            'total_tool_calls': sum(tool_counts.values()),
        }
    
    def get_success_comparison(self) -> Dict:
        """Compare baseline vs TogoMCP success patterns."""
        both_succeeded = 0
        only_baseline = 0
        only_togomcp = 0
        both_failed = 0
        
        for result in self.results:
            baseline_ok = self._parse_bool(result.get('baseline_success', 'False'))
            togomcp_ok = self._parse_bool(result.get('togomcp_success', 'False'))
            
            if baseline_ok and togomcp_ok:
                both_succeeded += 1
            elif baseline_ok and not togomcp_ok:
                only_baseline += 1
            elif not baseline_ok and togomcp_ok:
                only_togomcp += 1
            else:
                both_failed += 1
        
        return {
            'both_succeeded': both_succeeded,
            'only_baseline': only_baseline,
            'only_togomcp': only_togomcp,
            'both_failed': both_failed,
        }
    
    def get_performance_comparison(self) -> Dict:
        """Compare response times between baseline and TogoMCP."""
        faster_baseline = 0
        faster_togomcp = 0
        same = 0
        
        time_differences = []
        
        for result in self.results:
            baseline_time = self._parse_float(result.get('baseline_time', '0'))
            togomcp_time = self._parse_float(result.get('togomcp_time', '0'))
            
            diff = togomcp_time - baseline_time
            time_differences.append(diff)
            
            if abs(diff) < 0.1:  # Within 100ms
                same += 1
            elif diff > 0:
                faster_baseline += 1
            else:
                faster_togomcp += 1
        
        avg_diff = sum(time_differences) / len(time_differences) if time_differences else 0
        
        return {
            'faster_baseline': faster_baseline,
            'faster_togomcp': faster_togomcp,
            'similar': same,
            'avg_time_difference': avg_diff,
            'median_time_difference': sorted(time_differences)[len(time_differences)//2] if time_differences else 0,
        }
    
    def identify_problematic_questions(self) -> List[Dict]:
        """Identify questions where TogoMCP failed or performed poorly."""
        problems = []
        
        for result in self.results:
            togomcp_ok = self._parse_bool(result.get('togomcp_success', 'False'))
            baseline_ok = self._parse_bool(result.get('baseline_success', 'False'))
            
            # TogoMCP failed but baseline succeeded
            if baseline_ok and not togomcp_ok:
                problems.append({
                    'id': result.get('question_id'),
                    'category': result.get('category'),
                    'question': result.get('question_text', '')[:100],
                    'issue': 'TogoMCP failed, baseline succeeded',
                    'error': result.get('togomcp_error', 'Unknown error'),
                })
            
            # Both failed
            elif not baseline_ok and not togomcp_ok:
                problems.append({
                    'id': result.get('question_id'),
                    'category': result.get('category'),
                    'question': result.get('question_text', '')[:100],
                    'issue': 'Both failed',
                    'error': f"Baseline: {result.get('baseline_error', 'Unknown')} | TogoMCP: {result.get('togomcp_error', 'Unknown')}",
                })
        
        return problems
    
    def identify_high_value_questions(self) -> List[Dict]:
        """Identify questions where TogoMCP added significant value."""
        high_value = []
        
        for result in self.results:
            togomcp_ok = self._parse_bool(result.get('togomcp_success', 'False'))
            baseline_ok = self._parse_bool(result.get('baseline_success', 'False'))
            tools_used = result.get('tools_used', '').strip()
            
            # TogoMCP succeeded, used tools, and either baseline failed or answered differently
            if togomcp_ok and tools_used:
                # Case 1: Baseline failed, TogoMCP succeeded
                if not baseline_ok:
                    high_value.append({
                        'id': result.get('question_id'),
                        'category': result.get('category'),
                        'question': result.get('question_text', '')[:100],
                        'value': 'CRITICAL - Baseline failed, TogoMCP succeeded',
                        'tools': tools_used,
                    })
                # Case 2: Both succeeded but TogoMCP used tools (likely more precise)
                elif baseline_ok:
                    high_value.append({
                        'id': result.get('question_id'),
                        'category': result.get('category'),
                        'question': result.get('question_text', '')[:100],
                        'value': 'VALUABLE - Enhanced with database tools',
                        'tools': tools_used,
                    })
        
        return high_value
    
    def print_summary(self, verbose: bool = False):
        """Print comprehensive summary of results."""
        print("=" * 70)
        print("TOGOMCP EVALUATION RESULTS ANALYSIS")
        print("=" * 70)
        print()
        
        # Overall Statistics
        stats = self.get_overall_stats()
        print("📊 OVERALL STATISTICS")
        print("-" * 70)
        print(f"Total Questions:              {stats['total']}")
        print(f"Date Range:                   {self._get_date_range()}")
        print()
        print(f"Baseline Success:             {stats['baseline_success']}/{stats['total']} ({stats['baseline_success_rate']:.1f}%)")
        print(f"TogoMCP Success:              {stats['togomcp_success']}/{stats['total']} ({stats['togomcp_success_rate']:.1f}%)")
        print(f"Questions Using Tools:        {stats['tools_used_count']}/{stats['total']} ({stats['tools_used_rate']:.1f}%)")
        print()
        print(f"Avg Baseline Time:            {stats['avg_baseline_time']:.2f}s")
        print(f"Avg TogoMCP Time:             {stats['avg_togomcp_time']:.2f}s")
        print(f"Time Difference:              {stats['avg_togomcp_time'] - stats['avg_baseline_time']:+.2f}s")
        print()
        print(f"Avg Baseline Input Tokens:    {stats['avg_baseline_input_tokens']:.0f}")
        print(f"Avg Baseline Output Tokens:   {stats['avg_baseline_output_tokens']:.0f}")
        print(f"Total Baseline Tokens:        {stats['total_baseline_input_tokens'] + stats['total_baseline_output_tokens']}")
        print()
        
        # Success Comparison
        comparison = self.get_success_comparison()
        print("🔄 SUCCESS PATTERN COMPARISON")
        print("-" * 70)
        print(f"Both Succeeded:               {comparison['both_succeeded']}")
        print(f"Only Baseline Succeeded:      {comparison['only_baseline']}")
        print(f"Only TogoMCP Succeeded:       {comparison['only_togomcp']}")
        print(f"Both Failed:                  {comparison['both_failed']}")
        print()
        
        # Performance Comparison
        perf = self.get_performance_comparison()
        print("⚡ PERFORMANCE COMPARISON")
        print("-" * 70)
        print(f"Baseline Faster:              {perf['faster_baseline']}")
        print(f"TogoMCP Faster:               {perf['faster_togomcp']}")
        print(f"Similar Speed (±100ms):       {perf['similar']}")
        print(f"Avg Time Difference:          {perf['avg_time_difference']:+.2f}s")
        print(f"Median Time Difference:       {perf['median_time_difference']:+.2f}s")
        print()
        
        # Tool Usage
        tool_stats = self.get_tool_usage_stats()
        print("🔧 TOOL USAGE ANALYSIS")
        print("-" * 70)
        print(f"Unique Tools Used:            {tool_stats['unique_tools']}")
        print(f"Total Tool Calls:             {tool_stats['total_tool_calls']}")
        print()
        print("Most Used Tools:")
        for tool, count in list(tool_stats['individual_tools'].items())[:10]:
            print(f"  • {tool:40} {count:3d} times")
        print()
        
        if verbose and tool_stats['tool_combinations']:
            print("Most Common Tool Combinations:")
            for combo, count in list(tool_stats['tool_combinations'].items())[:5]:
                print(f"  • {' + '.join(combo):50} {count:2d} times")
            print()
        
        # Category Breakdown
        breakdown = self.get_category_breakdown()
        print("📂 CATEGORY BREAKDOWN")
        print("-" * 70)
        for category in sorted(breakdown.keys()):
            data = breakdown[category]
            print(f"\n{category}:")
            print(f"  Questions:          {data['count']}")
            print(f"  Baseline Success:   {data['baseline_success']}/{data['count']} ({data['baseline_success_rate']:.1f}%)")
            print(f"  TogoMCP Success:    {data['togomcp_success']}/{data['count']} ({data['togomcp_success_rate']:.1f}%)")
            print(f"  Tools Used:         {data['tools_used']}/{data['count']} ({data['tools_used_rate']:.1f}%)")
        print()
        
        # High Value Questions
        high_value = self.identify_high_value_questions()
        if high_value:
            print("⭐ HIGH-VALUE QUESTIONS (TogoMCP Added Significant Value)")
            print("-" * 70)
            for q in high_value[:10]:  # Top 10
                print(f"Q{q['id']} [{q['category']}]: {q['value']}")
                print(f"  Question: {q['question']}...")
                print(f"  Tools: {q['tools']}")
                print()
        
        # Problematic Questions
        problems = self.identify_problematic_questions()
        if problems:
            print("⚠️  PROBLEMATIC QUESTIONS")
            print("-" * 70)
            for q in problems:
                print(f"Q{q['id']} [{q['category']}]: {q['issue']}")
                print(f"  Question: {q['question']}...")
                if verbose:
                    print(f"  Error: {q['error']}")
                print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS")
        print("-" * 70)
        self._print_recommendations(stats, comparison, high_value, problems)
        
        print("=" * 70)
    
    def _get_date_range(self) -> str:
        """Get date range from results."""
        dates = [r.get('date', '') for r in self.results if r.get('date')]
        if not dates:
            return "Unknown"
        return f"{min(dates)} to {max(dates)}" if len(set(dates)) > 1 else dates[0]
    
    def _print_recommendations(self, stats, comparison, high_value, problems):
        """Print actionable recommendations."""
        recommendations = []
        
        # Success rate recommendations
        if stats['togomcp_success_rate'] < stats['baseline_success_rate']:
            recommendations.append(
                "⚠️  TogoMCP has lower success rate than baseline. "
                "Review failed questions to identify issues."
            )
        elif stats['togomcp_success_rate'] > stats['baseline_success_rate'] + 10:
            recommendations.append(
                "✓ TogoMCP shows significant improvement over baseline. "
                "Consider expanding evaluation set."
            )
        
        # Tool usage recommendations
        if stats['tools_used_rate'] < 50:
            recommendations.append(
                "📊 Tools used in less than 50% of questions. "
                "Consider adding more questions that require database access."
            )
        
        # High value recommendations
        if len(high_value) > 0:
            recommendations.append(
                f"⭐ {len(high_value)} questions show clear TogoMCP value-add. "
                "These are good candidates for benchmark set."
            )
        
        # Problem recommendations
        if len(problems) > 0:
            recommendations.append(
                f"⚠️  {len(problems)} questions have issues. "
                "Review and refine these questions or MCP configuration."
            )
        
        # Category recommendations
        breakdown = self.get_category_breakdown()
        categories_with_low_count = [cat for cat, data in breakdown.items() if data['count'] < 3]
        if categories_with_low_count:
            recommendations.append(
                f"📂 Categories with <3 questions: {', '.join(categories_with_low_count)}. "
                "Consider adding more questions to these categories."
            )
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
                print()
        else:
            print("✓ No major issues detected. Evaluation set looks balanced.")
            print()
    
    def export_markdown_report(self, output_path: str):
        """Export detailed analysis as Markdown report."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# TogoMCP Evaluation Results Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Source:** {self.csv_path.name}\n\n")
            
            # Overall stats
            stats = self.get_overall_stats()
            f.write("## Overall Statistics\n\n")
            f.write(f"- **Total Questions:** {stats['total']}\n")
            f.write(f"- **Date Range:** {self._get_date_range()}\n")
            f.write(f"- **Baseline Success:** {stats['baseline_success']}/{stats['total']} ({stats['baseline_success_rate']:.1f}%)\n")
            f.write(f"- **TogoMCP Success:** {stats['togomcp_success']}/{stats['total']} ({stats['togomcp_success_rate']:.1f}%)\n")
            f.write(f"- **Tools Used:** {stats['tools_used_count']}/{stats['total']} ({stats['tools_used_rate']:.1f}%)\n\n")
            
            # Category breakdown
            breakdown = self.get_category_breakdown()
            f.write("## Category Breakdown\n\n")
            f.write("| Category | Count | Baseline Success | TogoMCP Success | Tools Used |\n")
            f.write("|----------|-------|------------------|-----------------|------------|\n")
            for category in sorted(breakdown.keys()):
                data = breakdown[category]
                f.write(f"| {category} | {data['count']} | ")
                f.write(f"{data['baseline_success_rate']:.0f}% | ")
                f.write(f"{data['togomcp_success_rate']:.0f}% | ")
                f.write(f"{data['tools_used_rate']:.0f}% |\n")
            f.write("\n")
            
            # Tool usage
            tool_stats = self.get_tool_usage_stats()
            f.write("## Tool Usage\n\n")
            f.write(f"- **Unique Tools:** {tool_stats['unique_tools']}\n")
            f.write(f"- **Total Tool Calls:** {tool_stats['total_tool_calls']}\n\n")
            f.write("### Most Used Tools\n\n")
            for tool, count in list(tool_stats['individual_tools'].items())[:10]:
                f.write(f"- `{tool}`: {count} times\n")
            f.write("\n")
            
            # High value questions
            high_value = self.identify_high_value_questions()
            if high_value:
                f.write("## High-Value Questions\n\n")
                for q in high_value:
                    f.write(f"### Q{q['id']} - {q['category']}\n")
                    f.write(f"**Question:** {q['question']}...\n\n")
                    f.write(f"**Value:** {q['value']}\n\n")
                    f.write(f"**Tools:** {q['tools']}\n\n")
            
            # Problems
            problems = self.identify_problematic_questions()
            if problems:
                f.write("## Problematic Questions\n\n")
                for q in problems:
                    f.write(f"### Q{q['id']} - {q['category']}\n")
                    f.write(f"**Question:** {q['question']}...\n\n")
                    f.write(f"**Issue:** {q['issue']}\n\n")
                    f.write(f"**Error:** {q['error']}\n\n")
        
        print(f"✓ Markdown report exported to {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze TogoMCP evaluation results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "results_file",
        help="Path to evaluation_results.csv file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--export",
        help="Export analysis to Markdown file"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = EvaluationAnalyzer(args.results_file)
        analyzer.print_summary(verbose=args.verbose)
        
        if args.export:
            analyzer.export_markdown_report(args.export)
    
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
