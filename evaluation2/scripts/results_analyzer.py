#!/usr/bin/env python3
"""
Enhanced Results Analyzer - Uses Correctness Columns

This analyzer uses the new correctness columns added by the enhanced test runner:
- baseline_actually_answered
- baseline_has_expected
- togomcp_has_expected
- value_add

Usage:
    python results_analyzer_enhanced.py evaluation_results.csv
"""

import csv
import sys
from pathlib import Path
from collections import Counter, defaultdict


class EnhancedAnalyzer:
    """Analyzes TogoMCP evaluation results with correctness metrics."""
    
    def __init__(self, csv_path: str):
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
        
        print(f"✓ Loaded {len(self.results)} evaluation results\n")
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean values."""
        return value.strip().lower() in ('true', '1', 'yes')
    
    def _parse_float(self, value: str, default: float = 0.0) -> float:
        """Parse float values safely."""
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def get_overall_stats(self):
        """Calculate overall statistics."""
        total = len(self.results)
        if total == 0:
            return
        
        # Technical success
        baseline_success = sum(1 for r in self.results if self._parse_bool(r.get('baseline_success', 'False')))
        togomcp_success = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_success', 'False')))
        
        # Actual correctness
        baseline_answered = sum(1 for r in self.results if self._parse_bool(r.get('baseline_actually_answered', 'False')))
        baseline_correct = sum(1 for r in self.results if self._parse_bool(r.get('baseline_has_expected', 'False')))
        togomcp_correct = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_has_expected', 'False')))
        
        # Value-add distribution
        value_counts = Counter(r.get('value_add', 'MARGINAL') for r in self.results)
        
        tools_used_count = sum(1 for r in self.results if r.get('tools_used', '').strip())
        
        print("="*70)
        print("EVALUATION RESULTS ANALYSIS (WITH CORRECTNESS)")
        print("="*70)
        print(f"\nTotal Questions: {total}\n")
        
        print("BASELINE PERFORMANCE:")
        print(f"  Technical Success:          {baseline_success}/{total} ({baseline_success/total*100:.1f}%)")
        print(f"  Actually Answered:          {baseline_answered}/{total} ({baseline_answered/total*100:.1f}%)")
        print(f"  Has Expected Answer:        {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
        print()
        
        print("TOGOMCP PERFORMANCE:")
        print(f"  Technical Success:          {togomcp_success}/{total} ({togomcp_success/total*100:.1f}%)")
        print(f"  Has Expected Answer:        {togomcp_correct}/{total} ({togomcp_correct/total*100:.1f}%)")
        print(f"  Used Tools:                 {tools_used_count}/{total} ({tools_used_count/total*100:.1f}%)")
        print()
        
        print("VALUE-ADD DISTRIBUTION:")
        for level in ["CRITICAL", "VALUABLE", "MARGINAL", "REDUNDANT", "FAILED"]:
            count = value_counts[level]
            pct = count/total*100 if total > 0 else 0
            emoji = {
                "CRITICAL": "⭐⭐⭐",
                "VALUABLE": "⭐⭐",
                "MARGINAL": "⚠️",
                "REDUNDANT": "❌",
                "FAILED": "🔴"
            }[level]
            print(f"  {emoji} {level:12}         {count}/{total} ({pct:.1f}%)")
        print()
    
    def get_category_breakdown(self):
        """Breakdown by category."""
        categories = defaultdict(list)
        for result in self.results:
            category = result.get('category', 'Unknown')
            categories[category].append(result)
        
        print("BREAKDOWN BY CATEGORY:")
        print("-"*70)
        
        for category in sorted(categories.keys()):
            results = categories[category]
            total = len(results)
            
            answered = sum(1 for r in results if self._parse_bool(r.get('baseline_actually_answered', 'False')))
            value_add = Counter(r.get('value_add', 'MARGINAL') for r in results)
            critical = value_add['CRITICAL']
            
            print(f"\n{category} ({total} questions):")
            print(f"  Baseline Answered:    {answered}/{total}")
            print(f"  CRITICAL Questions:   {critical}/{total}")
            print(f"  Value Distribution:   {dict(value_add)}")
    
    def list_questions_by_value(self):
        """List questions grouped by value-add."""
        by_value = defaultdict(list)
        for r in self.results:
            value = r.get('value_add', 'MARGINAL')
            by_value[value].append(r)
        
        print("\nQUESTIONS BY VALUE-ADD:")
        print("-"*70)
        
        for level in ["CRITICAL", "VALUABLE", "MARGINAL", "REDUNDANT", "FAILED"]:
            questions = by_value[level]
            if not questions:
                continue
            
            emoji = {
                "CRITICAL": "⭐⭐⭐",
                "VALUABLE": "⭐⭐",
                "MARGINAL": "⚠️",
                "REDUNDANT": "❌",
                "FAILED": "🔴"
            }[level]
            
            print(f"\n{emoji} {level} ({len(questions)} questions):")
            for q in questions:
                q_id = q.get('question_id', '?')
                cat = q.get('category', '?')
                text = q.get('question_text', '')[:60]
                print(f"  Q{q_id} [{cat:15}] {text}...")
    
    def identify_issues(self):
        """Identify problematic questions."""
        issues = []
        
        for r in self.results:
            value = r.get('value_add', '')
            
            # REDUNDANT questions should be replaced
            if value == 'REDUNDANT':
                issues.append({
                    'id': r.get('question_id'),
                    'type': 'REDUNDANT',
                    'message': 'Baseline answered, TogoMCP didn\'t use tools - should be replaced'
                })
            
            # MARGINAL questions need improvement
            elif value == 'MARGINAL':
                issues.append({
                    'id': r.get('question_id'),
                    'type': 'MARGINAL',
                    'message': 'Low value-add - consider replacing with harder question'
                })
            
            # FAILED questions need investigation
            elif value == 'FAILED':
                issues.append({
                    'id': r.get('question_id'),
                    'type': 'FAILED',
                    'message': 'TogoMCP failed - check error logs'
                })
        
        if issues:
            print("\n⚠️ ISSUES FOUND:")
            print("-"*70)
            for issue in issues:
                print(f"Q{issue['id']}: [{issue['type']}] {issue['message']}")
        else:
            print("\n✓ No major issues found")
        
        print()
    
    def print_recommendations(self):
        """Print recommendations."""
        total = len(self.results)
        value_counts = Counter(r.get('value_add', 'MARGINAL') for r in self.results)
        
        critical_pct = value_counts['CRITICAL'] / total * 100
        valuable_pct = value_counts['VALUABLE'] / total * 100
        marginal_pct = value_counts['MARGINAL'] / total * 100
        redundant_pct = value_counts['REDUNDANT'] / total * 100
        
        print("💡 RECOMMENDATIONS:")
        print("-"*70)
        
        if critical_pct + valuable_pct >= 70:
            print("✅ EXCELLENT: 70%+ questions show significant TogoMCP value.")
        elif critical_pct + valuable_pct >= 50:
            print("✓ GOOD: 50-70% questions show TogoMCP value, but could be improved.")
        else:
            print("⚠️ NEEDS IMPROVEMENT: Less than 50% show significant value-add.")
        
        if redundant_pct > 0:
            print(f"\n❌ {value_counts['REDUNDANT']} REDUNDANT questions found.")
            print("   These should be replaced - baseline answered without tools.")
        
        if marginal_pct > 30:
            print(f"\n⚠️ {value_counts['MARGINAL']} MARGINAL questions ({marginal_pct:.0f}%).")
            print("   Consider replacing with less well-known entities.")
        
        if critical_pct < 40:
            print(f"\n📈 Only {critical_pct:.0f}% CRITICAL questions.")
            print("   Target 50-70% for best evaluation.")
            print("   Add more questions requiring database access.")
        
        print("\n✓ Use value-add metrics to improve question quality iteratively.")
        print("="*70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python results_analyzer_enhanced.py <results.csv>")
        sys.exit(1)
    
    try:
        analyzer = EnhancedAnalyzer(sys.argv[1])
        analyzer.get_overall_stats()
        analyzer.get_category_breakdown()
        analyzer.list_questions_by_value()
        analyzer.identify_issues()
        analyzer.print_recommendations()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
