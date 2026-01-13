#!/usr/bin/env python3
"""
Unified Results Analyzer - Supports Both Pattern Matching and LLM Evaluation

This analyzer automatically detects whether the CSV contains LLM evaluation columns
and provides appropriate analysis for both evaluation methods.

Usage:
    python results_analyzer_unified.py results.csv                    # Pattern matching only
    python results_analyzer_unified.py results_with_llm.csv           # With LLM evaluation
    python results_analyzer_unified.py results_with_llm.csv --mode llm      # Force LLM mode
    python results_analyzer_unified.py results_with_llm.csv --mode combined # Combined metrics
"""

import csv
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional


class UnifiedAnalyzer:
    """Analyzes TogoMCP evaluation results with support for both pattern matching and LLM evaluation."""
    
    def __init__(self, csv_path: str, mode: str = 'auto'):
        """
        Initialize analyzer.
        
        Args:
            csv_path: Path to CSV results file
            mode: Evaluation mode - 'auto', 'pattern', 'llm', or 'combined'
        """
        self.csv_path = Path(csv_path)
        self.results = []
        self.mode = mode
        self.has_llm_columns = False
        self.load_results()
    
    def load_results(self):
        """Load results from CSV file and detect available columns."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Results file not found: {self.csv_path}")
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.results = list(reader)
        
        # Detect LLM columns
        if self.results:
            sample_row = self.results[0]
            self.has_llm_columns = all(
                col in sample_row for col in [
                    'baseline_llm_match', 
                    'togomcp_llm_match',
                    'full_combined_baseline_found',
                    'full_combined_togomcp_found'
                ]
            )
        
        # Auto-detect mode
        if self.mode == 'auto':
            if self.has_llm_columns:
                self.mode = 'combined'
                print(f"✓ Detected LLM evaluation columns - using COMBINED mode")
            else:
                self.mode = 'pattern'
                print(f"✓ No LLM columns detected - using PATTERN MATCHING mode")
        elif self.mode in ['llm', 'combined'] and not self.has_llm_columns:
            print(f"⚠️  Warning: LLM mode requested but no LLM columns found")
            print(f"   Falling back to PATTERN MATCHING mode")
            self.mode = 'pattern'
        
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
    
    def _get_correctness_columns(self) -> tuple:
        """Get the appropriate correctness column names based on mode."""
        if self.mode == 'pattern':
            return ('baseline_has_expected', 'togomcp_has_expected')
        elif self.mode == 'llm':
            return ('baseline_llm_match', 'togomcp_llm_match')
        else:  # combined
            return ('full_combined_baseline_found', 'full_combined_togomcp_found')
    
    def get_overall_stats(self):
        """Calculate overall statistics."""
        total = len(self.results)
        if total == 0:
            return
        
        baseline_col, togomcp_col = self._get_correctness_columns()
        
        # Technical success
        baseline_success = sum(1 for r in self.results if self._parse_bool(r.get('baseline_success', 'False')))
        togomcp_success = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_success', 'False')))
        
        # Actual correctness
        baseline_answered = sum(1 for r in self.results if self._parse_bool(r.get('baseline_actually_answered', 'False')))
        baseline_correct = sum(1 for r in self.results if self._parse_bool(r.get(baseline_col, 'False')))
        togomcp_correct = sum(1 for r in self.results if self._parse_bool(r.get(togomcp_col, 'False')))
        
        # Value-add distribution
        value_counts = Counter(r.get('value_add', 'MARGINAL') for r in self.results)
        
        tools_used_count = sum(1 for r in self.results if r.get('tools_used', '').strip())
        
        mode_label = {
            'pattern': 'PATTERN MATCHING',
            'llm': 'LLM EVALUATION',
            'combined': 'COMBINED (Pattern OR LLM)'
        }[self.mode]
        
        print("="*70)
        print(f"EVALUATION RESULTS ANALYSIS - {mode_label}")
        print("="*70)
        print(f"\nTotal Questions: {total}\n")
        
        print("BASELINE PERFORMANCE:")
        print(f"  Technical Success:          {baseline_success}/{total} ({baseline_success/total*100:.1f}%)")
        print(f"  Actually Answered:          {baseline_answered}/{total} ({baseline_answered/total*100:.1f}%)")
        print(f"  Has Expected Answer:        {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
        
        # Show breakdown if combined mode
        if self.mode == 'combined' and self.has_llm_columns:
            pattern_only = sum(
                1 for r in self.results 
                if self._parse_bool(r.get('baseline_has_expected', 'False')) 
                and not self._parse_bool(r.get('baseline_llm_match', 'False'))
            )
            llm_only = sum(
                1 for r in self.results 
                if self._parse_bool(r.get('baseline_llm_match', 'False')) 
                and not self._parse_bool(r.get('baseline_has_expected', 'False'))
            )
            both = sum(
                1 for r in self.results 
                if self._parse_bool(r.get('baseline_has_expected', 'False')) 
                and self._parse_bool(r.get('baseline_llm_match', 'False'))
            )
            print(f"    └─ Pattern only:          {pattern_only}")
            print(f"    └─ LLM only:              {llm_only}")
            print(f"    └─ Both methods:          {both}")
        
        print()
        
        print("TOGOMCP PERFORMANCE:")
        print(f"  Technical Success:          {togomcp_success}/{total} ({togomcp_success/total*100:.1f}%)")
        print(f"  Has Expected Answer:        {togomcp_correct}/{total} ({togomcp_correct/total*100:.1f}%)")
        print(f"  Used Tools:                 {tools_used_count}/{total} ({tools_used_count/total*100:.1f}%)")
        
        # Show breakdown if combined mode
        if self.mode == 'combined' and self.has_llm_columns:
            pattern_only = sum(
                1 for r in self.results 
                if self._parse_bool(r.get('togomcp_has_expected', 'False')) 
                and not self._parse_bool(r.get('togomcp_llm_match', 'False'))
            )
            llm_only = sum(
                1 for r in self.results 
                if self._parse_bool(r.get('togomcp_llm_match', 'False')) 
                and not self._parse_bool(r.get('togomcp_has_expected', 'False'))
            )
            both = sum(
                1 for r in self.results 
                if self._parse_bool(r.get('togomcp_has_expected', 'False')) 
                and self._parse_bool(r.get('togomcp_llm_match', 'False'))
            )
            print(f"    └─ Pattern only:          {pattern_only}")
            print(f"    └─ LLM only:              {llm_only}")
            print(f"    └─ Both methods:          {both}")
        
        print()
        
        # LLM confidence statistics (if available)
        if self.has_llm_columns and self.mode in ['llm', 'combined']:
            print("LLM EVALUATION CONFIDENCE:")
            baseline_confidences = Counter(
                r.get('baseline_llm_confidence', 'low') 
                for r in self.results 
                if self._parse_bool(r.get('baseline_llm_match', 'False'))
            )
            togomcp_confidences = Counter(
                r.get('togomcp_llm_confidence', 'low') 
                for r in self.results 
                if self._parse_bool(r.get('togomcp_llm_match', 'False'))
            )
            
            print(f"  Baseline - High: {baseline_confidences.get('high', 0)}, "
                  f"Medium: {baseline_confidences.get('medium', 0)}, "
                  f"Low: {baseline_confidences.get('low', 0)}")
            print(f"  TogoMCP  - High: {togomcp_confidences.get('high', 0)}, "
                  f"Medium: {togomcp_confidences.get('medium', 0)}, "
                  f"Low: {togomcp_confidences.get('low', 0)}")
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
        baseline_col, togomcp_col = self._get_correctness_columns()
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
            baseline_correct = sum(1 for r in results if self._parse_bool(r.get(baseline_col, 'False')))
            togomcp_correct = sum(1 for r in results if self._parse_bool(r.get(togomcp_col, 'False')))
            value_add = Counter(r.get('value_add', 'MARGINAL') for r in results)
            critical = value_add['CRITICAL']
            
            print(f"\n{category} ({total} questions):")
            print(f"  Baseline Answered:    {answered}/{total} ({answered/total*100:.1f}%)")
            print(f"  Baseline Correct:     {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
            print(f"  TogoMCP Correct:      {togomcp_correct}/{total} ({togomcp_correct/total*100:.1f}%)")
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
            for q in questions[:10]:  # Show first 10
                q_id = q.get('question_id', '?')
                cat = q.get('category', '?')
                text = q.get('question_text', '')[:60]
                print(f"  Q{q_id} [{cat:15}] {text}...")
            
            if len(questions) > 10:
                print(f"  ... and {len(questions) - 10} more")
    
    def compare_evaluation_methods(self):
        """Compare pattern matching vs LLM evaluation (only if both available)."""
        if not self.has_llm_columns:
            return
        
        print("\nCOMPARISON: PATTERN MATCHING vs LLM EVALUATION:")
        print("-"*70)
        
        # Agreement analysis
        baseline_agree = sum(
            1 for r in self.results
            if self._parse_bool(r.get('baseline_has_expected', 'False')) == 
               self._parse_bool(r.get('baseline_llm_match', 'False'))
        )
        togomcp_agree = sum(
            1 for r in self.results
            if self._parse_bool(r.get('togomcp_has_expected', 'False')) == 
               self._parse_bool(r.get('togomcp_llm_match', 'False'))
        )
        
        total = len(self.results)
        
        print(f"\nAgreement Rate:")
        print(f"  Baseline:  {baseline_agree}/{total} ({baseline_agree/total*100:.1f}%)")
        print(f"  TogoMCP:   {togomcp_agree}/{total} ({togomcp_agree/total*100:.1f}%)")
        
        # Pattern found but LLM missed
        baseline_pattern_only = sum(
            1 for r in self.results
            if self._parse_bool(r.get('baseline_has_expected', 'False'))
            and not self._parse_bool(r.get('baseline_llm_match', 'False'))
        )
        togomcp_pattern_only = sum(
            1 for r in self.results
            if self._parse_bool(r.get('togomcp_has_expected', 'False'))
            and not self._parse_bool(r.get('togomcp_llm_match', 'False'))
        )
        
        print(f"\nPattern Found but LLM Missed:")
        print(f"  Baseline:  {baseline_pattern_only}")
        print(f"  TogoMCP:   {togomcp_pattern_only}")
        
        # LLM found but pattern missed
        baseline_llm_only = sum(
            1 for r in self.results
            if self._parse_bool(r.get('baseline_llm_match', 'False'))
            and not self._parse_bool(r.get('baseline_has_expected', 'False'))
        )
        togomcp_llm_only = sum(
            1 for r in self.results
            if self._parse_bool(r.get('togomcp_llm_match', 'False'))
            and not self._parse_bool(r.get('togomcp_has_expected', 'False'))
        )
        
        print(f"\nLLM Found but Pattern Missed:")
        print(f"  Baseline:  {baseline_llm_only}")
        print(f"  TogoMCP:   {togomcp_llm_only}")
        
        print(f"\n💡 Combined method captures {baseline_llm_only} additional baseline matches")
        print(f"   and {togomcp_llm_only} additional TogoMCP matches that pattern matching missed.")
    
    def identify_issues(self):
        """Identify problematic questions."""
        baseline_col, togomcp_col = self._get_correctness_columns()
        issues = []
        
        for r in self.results:
            value = r.get('value_add', '')
            q_id = r.get('question_id')
            
            # REDUNDANT questions should be replaced
            if value == 'REDUNDANT':
                issues.append({
                    'id': q_id,
                    'type': 'REDUNDANT',
                    'message': 'Baseline answered, TogoMCP didn\'t use tools - should be replaced'
                })
            
            # MARGINAL questions need improvement
            elif value == 'MARGINAL':
                issues.append({
                    'id': q_id,
                    'type': 'MARGINAL',
                    'message': 'Low value-add - consider replacing with harder question'
                })
            
            # FAILED questions need investigation
            elif value == 'FAILED':
                issues.append({
                    'id': q_id,
                    'type': 'FAILED',
                    'message': 'TogoMCP failed - check error logs'
                })
            
            # Check for low confidence LLM matches (if in LLM mode)
            if self.has_llm_columns and self.mode in ['llm', 'combined']:
                if (self._parse_bool(r.get(togomcp_col, 'False')) and 
                    r.get('togomcp_llm_confidence') == 'low'):
                    issues.append({
                        'id': q_id,
                        'type': 'LOW_CONFIDENCE',
                        'message': 'TogoMCP marked correct but with low LLM confidence'
                    })
        
        if issues:
            print("\n⚠️ ISSUES FOUND:")
            print("-"*70)
            for issue in issues[:20]:  # Show first 20
                print(f"Q{issue['id']}: [{issue['type']}] {issue['message']}")
            if len(issues) > 20:
                print(f"... and {len(issues) - 20} more issues")
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
        
        if self.has_llm_columns:
            print(f"\n✓ Using {self.mode.upper()} evaluation mode.")
            if self.mode == 'pattern':
                print("   Consider running add_llm_evaluation.py for more robust evaluation.")
            elif self.mode == 'combined':
                print("   Combined evaluation provides most comprehensive assessment.")
        
        print("\n✓ Use value-add metrics to improve question quality iteratively.")
        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Unified analyzer supporting both pattern matching and LLM evaluation"
    )
    parser.add_argument("results_file", help="Path to results CSV file")
    parser.add_argument(
        "--mode",
        choices=['auto', 'pattern', 'llm', 'combined'],
        default='auto',
        help="Evaluation mode (default: auto-detect)"
    )
    parser.add_argument(
        "--no-comparison",
        action='store_true',
        help="Skip pattern vs LLM comparison"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = UnifiedAnalyzer(args.results_file, mode=args.mode)
        analyzer.get_overall_stats()
        analyzer.get_category_breakdown()
        analyzer.list_questions_by_value()
        
        if not args.no_comparison and analyzer.has_llm_columns:
            analyzer.compare_evaluation_methods()
        
        analyzer.identify_issues()
        analyzer.print_recommendations()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
