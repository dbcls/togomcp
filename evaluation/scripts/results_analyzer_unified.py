"""
Unified Results Analyzer - Enhanced with Statistical Analysis

This analyzer automatically detects whether the CSV contains LLM evaluation columns
and provides comprehensive analysis including statistical significance testing,
confusion matrices, and quality scoring.

Key Features:
- Automatic mode detection (pattern, llm, or combined)
- Statistical significance testing (McNemar's test, Cohen's Kappa)
- Confusion matrix analysis with precision/recall metrics  
- Question quality scoring system (0-100 scale)
- Detailed discrepancy analysis between evaluation methods
- Enhanced pattern matching with inability detection
- Numeric tolerance matching for count-based questions

New in Enhanced Version:
- Statistical validation of evaluation method differences
- Automated question quality assessment
- Performance metrics (precision, recall, F1-score)
- Confidence-weighted analysis

Usage:
    python results_analyzer_unified.py results.csv
    python results_analyzer_unified.py results_with_llm.csv --enhanced       # All enhancements
    python results_analyzer_unified.py results_with_llm.csv --statistical    # Statistical tests
    python results_analyzer_unified.py results_with_llm.csv --quality        # Quality scoring
    python results_analyzer_unified.py results_with_llm.csv --confusion-matrix

Requirements for enhanced features:
    pip install scipy scikit-learn  # For statistical analysis
"""

import csv
import sys
import re
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any
import warnings

# Optional dependencies for enhanced features
try:
    from scipy.stats import mcnemar
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    from sklearn.metrics import cohen_kappa_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class StatisticalAnalyzer:
    """Statistical significance testing for evaluation method comparison."""
    
    def __init__(self, results: List[Dict]):
        self.results = results
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean values."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes')
    
    def mcnemar_test(self, pattern_results: List[bool], llm_results: List[bool]) -> Dict:
        """
        McNemar's test for paired categorical data.
        
        Tests if pattern matching and LLM evaluation disagree significantly.
        Null hypothesis: Both methods have same error rate.
        
        Returns:
            {
                'statistic': float,
                'p_value': float,
                'significant': bool (p < 0.05),
                'interpretation': str,
                'contingency_table': dict
            }
        """
        if not SCIPY_AVAILABLE:
            return {'error': 'scipy not installed'}
        
        # Create contingency table
        both_correct = sum(1 for p, l in zip(pattern_results, llm_results) if p and l)
        pattern_only = sum(1 for p, l in zip(pattern_results, llm_results) if p and not l)
        llm_only = sum(1 for p, l in zip(pattern_results, llm_results) if not p and l)
        both_wrong = sum(1 for p, l in zip(pattern_results, llm_results) if not p and not l)
        
        table = [[both_correct, pattern_only],
                 [llm_only, both_wrong]]
        
        try:
            result = mcnemar(table, exact=False, correction=True)
            
            interpretation = ""
            if result.pvalue < 0.001:
                interpretation = "Very strong evidence of systematic difference"
            elif result.pvalue < 0.01:
                interpretation = "Strong evidence of systematic difference"
            elif result.pvalue < 0.05:
                interpretation = "Significant difference detected"
            else:
                interpretation = "No significant difference"
            
            return {
                'statistic': result.statistic,
                'p_value': result.pvalue,
                'significant': result.pvalue < 0.05,
                'interpretation': interpretation,
                'contingency_table': {
                    'both_correct': both_correct,
                    'pattern_only': pattern_only,
                    'llm_only': llm_only,
                    'both_wrong': both_wrong
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def cohen_kappa(self, pattern_results: List[bool], llm_results: List[bool]) -> Dict:
        """
        Cohen's Kappa for inter-rater agreement.
        
        Measures agreement beyond chance:
        - < 0: Poor (worse than chance)
        - 0.0-0.20: Slight
        - 0.21-0.40: Fair
        - 0.41-0.60: Moderate
        - 0.61-0.80: Substantial
        - 0.81-1.0: Almost perfect
        
        Returns:
            {
                'kappa': float,
                'strength': str,
                'interpretation': str
            }
        """
        if not SKLEARN_AVAILABLE:
            return {'error': 'sklearn not installed'}
        
        try:
            kappa = cohen_kappa_score(pattern_results, llm_results)
            
            if kappa < 0:
                strength = "Poor"
                interpretation = "Agreement worse than chance - methods fundamentally disagree"
            elif kappa < 0.21:
                strength = "Slight"
                interpretation = "Minimal agreement beyond chance"
            elif kappa < 0.41:
                strength = "Fair"
                interpretation = "Some agreement, but methods often disagree"
            elif kappa < 0.61:
                strength = "Moderate"
                interpretation = "Moderate agreement - methods mostly align"
            elif kappa < 0.81:
                strength = "Substantial"
                interpretation = "Strong agreement - methods are well-aligned"
            else:
                strength = "Almost perfect"
                interpretation = "Near-perfect agreement between methods"
            
            return {
                'kappa': kappa,
                'strength': strength,
                'interpretation': interpretation
            }
        except Exception as e:
            return {'error': str(e)}
    
    def print_statistical_comparison(self):
        """Print statistical comparison between pattern matching and LLM."""
        print("\n" + "=" * 70)
        print("STATISTICAL SIGNIFICANCE ANALYSIS")
        print("=" * 70)
        
        # Baseline comparison
        baseline_pattern = [self._parse_bool(r.get('baseline_has_expected', 'False')) for r in self.results]
        baseline_llm = [self._parse_bool(r.get('baseline_llm_match', 'False')) for r in self.results]
        
        print("\n📊 BASELINE EVALUATION METHODS:")
        print("-" * 70)
        
        kappa_baseline = self.cohen_kappa(baseline_pattern, baseline_llm)
        if 'error' not in kappa_baseline:
            print(f"\nCohen's Kappa: {kappa_baseline['kappa']:.3f}")
            print(f"  Agreement: {kappa_baseline['strength']}")
            print(f"  Meaning: {kappa_baseline['interpretation']}")
        else:
            print(f"\nCohen's Kappa: Not available ({kappa_baseline['error']})")
        
        mcnemar_baseline = self.mcnemar_test(baseline_pattern, baseline_llm)
        if 'error' not in mcnemar_baseline:
            print(f"\nMcNemar's Test:")
            print(f"  χ² statistic: {mcnemar_baseline['statistic']:.3f}")
            print(f"  p-value: {mcnemar_baseline['p_value']:.4f}")
            print(f"  Significant: {'YES' if mcnemar_baseline['significant'] else 'NO'} (α=0.05)")
            print(f"  Interpretation: {mcnemar_baseline['interpretation']}")
            
            ct = mcnemar_baseline['contingency_table']
            print(f"\n  Contingency Table:")
            print(f"    Both methods agree correct: {ct['both_correct']}")
            print(f"    Pattern only:               {ct['pattern_only']} (likely false positives)")
            print(f"    LLM only:                   {ct['llm_only']}")
            print(f"    Both methods agree wrong:   {ct['both_wrong']}")
        else:
            print(f"\nMcNemar's Test: Not available ({mcnemar_baseline['error']})")
        
        # TogoMCP comparison
        togomcp_pattern = [self._parse_bool(r.get('togomcp_has_expected', 'False')) for r in self.results]
        togomcp_llm = [self._parse_bool(r.get('togomcp_llm_match', 'False')) for r in self.results]
        
        print("\n📊 TOGOMCP EVALUATION METHODS:")
        print("-" * 70)
        
        kappa_togomcp = self.cohen_kappa(togomcp_pattern, togomcp_llm)
        if 'error' not in kappa_togomcp:
            print(f"\nCohen's Kappa: {kappa_togomcp['kappa']:.3f}")
            print(f"  Agreement: {kappa_togomcp['strength']}")
            print(f"  Meaning: {kappa_togomcp['interpretation']}")
        else:
            print(f"\nCohen's Kappa: Not available ({kappa_togomcp['error']})")
        
        mcnemar_togomcp = self.mcnemar_test(togomcp_pattern, togomcp_llm)
        if 'error' not in mcnemar_togomcp:
            print(f"\nMcNemar's Test:")
            print(f"  χ² statistic: {mcnemar_togomcp['statistic']:.3f}")
            print(f"  p-value: {mcnemar_togomcp['p_value']:.4f}")
            print(f"  Significant: {'YES' if mcnemar_togomcp['significant'] else 'NO'} (α=0.05)")
            print(f"  Interpretation: {mcnemar_togomcp['interpretation']}")
            
            ct = mcnemar_togomcp['contingency_table']
            print(f"\n  Contingency Table:")
            print(f"    Both methods agree correct: {ct['both_correct']}")
            print(f"    Pattern only:               {ct['pattern_only']} (may be false positives)")
            print(f"    LLM only:                   {ct['llm_only']} (often data updates)")
            print(f"    Both methods agree wrong:   {ct['both_wrong']}")
        else:
            print(f"\nMcNemar's Test: Not available ({mcnemar_togomcp['error']})")
        
        # Summary interpretation
        print("\n💡 INTERPRETATION:")
        print("-" * 70)
        
        if 'error' not in kappa_baseline and kappa_baseline['kappa'] < 0.6:
            print("⚠️  BASELINE: Low agreement between methods suggests systematic differences")
            print("   → Pattern matching likely has high false positive rate")
            print("   → Recommend using LLM evaluation as primary metric")
        
        if 'error' not in kappa_togomcp and kappa_togomcp['kappa'] > 0.8:
            print("✅ TOGOMCP: High agreement suggests both methods work well")
            print("   → Consider using combined approach for completeness")


class ConfusionMatrixAnalyzer:
    """Generate and display confusion matrices treating LLM as ground truth."""
    
    def __init__(self, results: List[Dict]):
        self.results = results
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean values."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes')
    
    def generate_matrix(self, pattern_results: List[bool], llm_results: List[bool]) -> Dict:
        """
        Generate confusion matrix metrics.
        
        Treats LLM evaluation as ground truth.
        Pattern matching is being evaluated against LLM.
        """
        tp = sum(1 for p, l in zip(pattern_results, llm_results) if p and l)
        fp = sum(1 for p, l in zip(pattern_results, llm_results) if p and not l)
        fn = sum(1 for p, l in zip(pattern_results, llm_results) if not p and l)
        tn = sum(1 for p, l in zip(pattern_results, llm_results) if not p and not l)
        
        total = len(pattern_results)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / total if total > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0  # Negative Predictive Value
        
        return {
            'true_positive': tp,
            'false_positive': fp,
            'false_negative': fn,
            'true_negative': tn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'accuracy': accuracy,
            'specificity': specificity,
            'npv': npv
        }
    
    def print_matrix(self, label: str, matrix: Dict):
        """Print formatted confusion matrix with metrics."""
        print(f"\n{label}")
        print("=" * 70)
        print("\nConfusion Matrix (LLM Evaluation as Ground Truth):")
        print(f"                    LLM=Correct    LLM=Incorrect    Total")
        print(f"  Pattern=Correct      {matrix['true_positive']:4d}           {matrix['false_positive']:4d}          {matrix['true_positive']+matrix['false_positive']:4d}")
        print(f"  Pattern=Incorrect    {matrix['false_negative']:4d}           {matrix['true_negative']:4d}          {matrix['false_negative']+matrix['true_negative']:4d}")
        print(f"  Total                {matrix['true_positive']+matrix['false_negative']:4d}           {matrix['false_positive']+matrix['true_negative']:4d}")
        
        print(f"\nPerformance Metrics:")
        print(f"  Accuracy:   {matrix['accuracy']:.2%}  (Overall agreement)")
        print(f"  Precision:  {matrix['precision']:.2%}  (When pattern says correct, how often is it right?)")
        print(f"  Recall:     {matrix['recall']:.2%}  (Of all LLM-correct answers, how many did pattern catch?)")
        print(f"  F1-Score:   {matrix['f1_score']:.3f}  (Harmonic mean of precision and recall)")
        print(f"  Specificity:{matrix['specificity']:.2%}  (Of all LLM-incorrect, how many did pattern reject?)")
        print(f"  NPV:        {matrix['npv']:.2%}  (When pattern says incorrect, how often is it right?)")
        
        # Interpretation
        print(f"\n💡 Interpretation:")
        if matrix['precision'] < 0.7:
            print(f"  ⚠️  Low precision ({matrix['precision']:.0%}): Pattern has many false positives")
            print(f"     {matrix['false_positive']} cases where pattern found match but LLM says incorrect")
        else:
            print(f"  ✅ Good precision ({matrix['precision']:.0%}): Pattern matches are reliable")
        
        if matrix['recall'] < 0.7:
            print(f"  ⚠️  Low recall ({matrix['recall']:.0%}): Pattern misses many correct answers")
            print(f"     {matrix['false_negative']} cases where LLM found match but pattern missed")
        else:
            print(f"  ✅ Good recall ({matrix['recall']:.0%}): Pattern catches most correct answers")
    
    def print_confusion_matrices(self):
        """Print confusion matrices for both baseline and TogoMCP."""
        print("\n" + "=" * 70)
        print("CONFUSION MATRIX ANALYSIS")
        print("=" * 70)
        
        # Baseline
        baseline_pattern = [self._parse_bool(r.get('baseline_has_expected', 'False')) for r in self.results]
        baseline_llm = [self._parse_bool(r.get('baseline_llm_match', 'False')) for r in self.results]
        baseline_matrix = self.generate_matrix(baseline_pattern, baseline_llm)
        self.print_matrix("BASELINE (No Tools)", baseline_matrix)
        
        # TogoMCP
        togomcp_pattern = [self._parse_bool(r.get('togomcp_has_expected', 'False')) for r in self.results]
        togomcp_llm = [self._parse_bool(r.get('togomcp_llm_match', 'False')) for r in self.results]
        togomcp_matrix = self.generate_matrix(togomcp_pattern, togomcp_llm)
        self.print_matrix("TOGOMCP (With Database Tools)", togomcp_matrix)
        
        # Comparison
        print(f"\n📊 COMPARISON:")
        print("-" * 70)
        print(f"Pattern Matching Reliability:")
        print(f"  Baseline:  Precision={baseline_matrix['precision']:.0%}, Recall={baseline_matrix['recall']:.0%}, F1={baseline_matrix['f1_score']:.3f}")
        print(f"  TogoMCP:   Precision={togomcp_matrix['precision']:.0%}, Recall={togomcp_matrix['recall']:.0%}, F1={togomcp_matrix['f1_score']:.3f}")
        
        if baseline_matrix['f1_score'] < 0.7:
            print(f"\n⚠️  Baseline pattern matching is unreliable (F1={baseline_matrix['f1_score']:.3f})")
            print(f"   Recommend: Use LLM evaluation as primary baseline metric")
        
        if togomcp_matrix['recall'] < togomcp_matrix['precision']:
            print(f"\n💡 TogoMCP pattern matching is conservative (misses some correct answers)")
            print(f"   Consider: Use combined metric (pattern OR LLM) for completeness")


class QuestionQualityScorer:
    """Automated question quality assessment."""
    
    def __init__(self):
        pass
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string boolean values."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes')
    
    def score_question(self, result: Dict) -> Dict[str, Any]:
        """
        Score question quality on multiple dimensions.
        
        Scoring (out of 100):
        - Value-add: 30 points (CRITICAL=30, VALUABLE=20, MARGINAL=10, other=0)
        - Evaluation consistency: 30 points (both agree=30, disagree=15)
        - LLM confidence: 20 points (high=20, medium=15, low=10)
        - Tools usage: 20 points (used=20, not used=0)
        """
        score = 0
        issues = []
        breakdown = {}
        
        # 1. Value-add (30 points)
        value = result.get('value_add', 'MARGINAL')
        if value == 'CRITICAL':
            breakdown['value_add'] = 30
        elif value == 'VALUABLE':
            breakdown['value_add'] = 20
        elif value == 'MARGINAL':
            breakdown['value_add'] = 10
            issues.append("Low value-add - baseline can answer")
        elif value == 'REDUNDANT':
            breakdown['value_add'] = 0
            issues.append("REDUNDANT - baseline answered, no tools used")
        else:  # FAILED
            breakdown['value_add'] = 0
            issues.append(f"FAILED - TogoMCP error")
        
        # 2. Evaluation consistency (30 points)
        baseline_pattern = self._parse_bool(result.get('baseline_has_expected', 'False'))
        baseline_llm = self._parse_bool(result.get('baseline_llm_match', 'False'))
        togomcp_pattern = self._parse_bool(result.get('togomcp_has_expected', 'False'))
        togomcp_llm = self._parse_bool(result.get('togomcp_llm_match', 'False'))
        
        # Check if we have LLM data
        has_llm = 'baseline_llm_match' in result
        
        if has_llm:
            baseline_consistent = (baseline_pattern == baseline_llm)
            togomcp_consistent = (togomcp_pattern == togomcp_llm)
            
            if baseline_consistent and togomcp_consistent:
                breakdown['consistency'] = 30
            elif baseline_consistent or togomcp_consistent:
                breakdown['consistency'] = 20
                issues.append("Partial evaluation disagreement")
            else:
                breakdown['consistency'] = 10
                issues.append("Pattern and LLM disagree on both baseline and TogoMCP")
        else:
            breakdown['consistency'] = 20  # Neutral if no LLM data
        
        # 3. LLM confidence (20 points)
        if has_llm:
            togomcp_conf = result.get('togomcp_llm_confidence', 'low')
            if togomcp_conf == 'high':
                breakdown['confidence'] = 20
            elif togomcp_conf == 'medium':
                breakdown['confidence'] = 15
            else:
                breakdown['confidence'] = 10
                if togomcp_llm:
                    issues.append("Low LLM confidence despite match")
        else:
            breakdown['confidence'] = 15  # Neutral
        
        # 4. Tools usage (20 points)
        tools = result.get('tools_used', '').strip()
        if tools:
            breakdown['tools'] = 20
        else:
            breakdown['tools'] = 0
            if value != 'REDUNDANT':  # Don't double-count
                issues.append("No tools used despite non-REDUNDANT value")
        
        total_score = sum(breakdown.values())
        
        # Determine tier
        if total_score >= 80:
            tier = 'EXCELLENT'
        elif total_score >= 60:
            tier = 'GOOD'
        elif total_score >= 40:
            tier = 'FAIR'
        else:
            tier = 'POOR'
        
        return {
            'question_id': result.get('question_id'),
            'category': result.get('category', 'Unknown'),
            'score': total_score,
            'tier': tier,
            'breakdown': breakdown,
            'issues': issues
        }
    
    def print_quality_report(self, results: List[Dict]):
        """Generate and print quality report."""
        print("\n" + "=" * 70)
        print("QUESTION QUALITY ANALYSIS")
        print("=" * 70)
        
        scores = [self.score_question(r) for r in results]
        
        # Overall stats
        avg_score = sum(s['score'] for s in scores) / len(scores) if scores else 0
        tier_counts = Counter(s['tier'] for s in scores)
        
        print(f"\n📊 OVERALL QUALITY:")
        print(f"  Average Score: {avg_score:.1f}/100")
        print(f"  Distribution:")
        for tier in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR']:
            count = tier_counts[tier]
            pct = count / len(scores) * 100 if scores else 0
            emoji = {'EXCELLENT': '🌟', 'GOOD': '✅', 'FAIR': '⚠️', 'POOR': '❌'}[tier]
            print(f"    {emoji} {tier:10} {count:3d} ({pct:5.1f}%)")
        
        # Quality by category
        by_category = defaultdict(list)
        for s in scores:
            by_category[s['category']].append(s['score'])
        
        print(f"\n📂 QUALITY BY CATEGORY:")
        for category in sorted(by_category.keys()):
            cat_scores = by_category[category]
            cat_avg = sum(cat_scores) / len(cat_scores)
            print(f"  {category:20} Avg: {cat_avg:5.1f}/100  ({len(cat_scores)} questions)")
        
        # Poor questions needing replacement
        poor_questions = [s for s in scores if s['tier'] == 'POOR']
        fair_questions = [s for s in scores if s['tier'] == 'FAIR']
        
        if poor_questions:
            print(f"\n❌ POOR QUALITY QUESTIONS ({len(poor_questions)} need replacement):")
            for q in poor_questions[:10]:
                print(f"  Q{q['question_id']:3} [{q['category']:15}] Score: {q['score']:2d}/100")
                for issue in q['issues'][:2]:
                    print(f"      - {issue}")
            if len(poor_questions) > 10:
                print(f"  ... and {len(poor_questions) - 10} more")
        
        if fair_questions:
            print(f"\n⚠️  FAIR QUALITY QUESTIONS ({len(fair_questions)} could be improved):")
            for q in fair_questions[:5]:
                print(f"  Q{q['question_id']:3} [{q['category']:15}] Score: {q['score']:2d}/100")
            if len(fair_questions) > 5:
                print(f"  ... and {len(fair_questions) - 5} more")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 70)
        
        poor_pct = len(poor_questions) / len(scores) * 100 if scores else 0
        fair_pct = len(fair_questions) / len(scores) * 100 if scores else 0
        
        if poor_pct > 10:
            print(f"  1. URGENT: {len(poor_questions)} poor-quality questions need replacement")
            print(f"     Focus on fixing REDUNDANT and FAILED questions first")
        
        if fair_pct > 20:
            print(f"  2. IMPROVE: {len(fair_questions)} fair-quality questions could be enhanced")
            print(f"     Consider making them more challenging or database-specific")
        
        if avg_score < 60:
            print(f"  3. Overall quality is below target (avg={avg_score:.0f}/100)")
            print(f"     Target: 70+ average score for robust evaluation")
        else:
            print(f"  ✅ Overall quality is good (avg={avg_score:.0f}/100)")
        
        print()


# Convenience function for integration
def run_all_enhancements(results: List[Dict]):
    """Run all enhancement analyses."""
    print("\n" + "=" * 70)
    print("ENHANCED ANALYSIS MODULE")
    print("=" * 70)
    
    if SCIPY_AVAILABLE and SKLEARN_AVAILABLE:
        stats = StatisticalAnalyzer(results)
        stats.print_statistical_comparison()
        
        matrix = ConfusionMatrixAnalyzer(results)
        matrix.print_confusion_matrices()
    else:
        print("\n⚠️  Statistical analysis unavailable")
        print("   Install with: pip install scipy scikit-learn")
    
    quality = QuestionQualityScorer()
    quality.print_quality_report(results)




class EnhancedPatternMatcher:
    """Enhanced pattern matching with inability detection and numeric tolerance.
    
    Addresses key issues identified in discrepancy analysis:
    1. False positives: Pattern finds keywords in "I don't know" responses
    2. False negatives: Exact matches fail for semantically equivalent answers
    """
    
    # Phrases indicating inability to answer (expanded list)
    INABILITY_PHRASES = [
        r"don'?t have access",
        r"don'?t have the specific",
        r"don'?t have specific",
        r"cannot provide",
        r"would need to",
        r"i'?d recommend",
        r"you would need to",
        r"without access",
        r"can'?t provide",
        r"don'?t know",
        r"cannot tell",
        r"unable to provide",
        r"can'?t tell you",
        r"i don'?t have",
        r"not memorized",
        r"to get this information",
        r"check the.*database",
        r"search.*directly",
        r"no access to",
        r"need to query",
        r"need to check",
        r"cannot give you",
        r"can'?t give you",
        r"not able to provide",
        r"i'?m not able to",
        r"beyond my knowledge",
        r"outside my training",
        r"i lack the",
        r"i cannot access",
        r"real-?time data",
        r"current exact",
        r"continuously updated",
        r"changes over time",
        r"changes frequently",
        r"varies by release",
        r"would require querying",
    ]
    
    # Numeric pattern to extract numbers from text
    NUMERIC_PATTERN = re.compile(r'[\d,]+(?:\.\d+)?')
    
    def __init__(self, numeric_tolerance: float = 0.15):
        """
        Initialize matcher.
        
        Args:
            numeric_tolerance: Tolerance for numeric matching (default 15%)
        """
        self.numeric_tolerance = numeric_tolerance
        self._compiled_inability = [re.compile(p, re.IGNORECASE) for p in self.INABILITY_PHRASES]
    
    def check_inability(self, text: str) -> bool:
        """Check if response indicates inability to answer."""
        if not text:
            return True
        
        for pattern in self._compiled_inability:
            if pattern.search(text):
                return True
        return False
    
    def extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        numbers = []
        for match in self.NUMERIC_PATTERN.findall(text):
            try:
                # Remove commas and convert
                num = float(match.replace(',', ''))
                numbers.append(num)
            except ValueError:
                pass
        return numbers
    
    def check_numeric_match(self, response_text: str, expected: str) -> Tuple[bool, float]:
        """
        Check if response contains expected numeric value within tolerance.
        
        Returns:
            (found, confidence)
        """
        expected_numbers = self.extract_numbers(expected)
        if not expected_numbers:
            return (False, 0.0)
        
        response_numbers = self.extract_numbers(response_text)
        if not response_numbers:
            return (False, 0.0)
        
        # Check if any expected number matches within tolerance
        matches = 0
        for exp_num in expected_numbers:
            for resp_num in response_numbers:
                if exp_num > 0:
                    diff_ratio = abs(resp_num - exp_num) / exp_num
                    if diff_ratio <= self.numeric_tolerance:
                        matches += 1
                        break
        
        if matches > 0:
            confidence = matches / len(expected_numbers)
            return (True, confidence)
        
        return (False, 0.0)
    
    def enhanced_check_expected(
        self, 
        response_text: str, 
        expected: str,
        check_inability: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced pattern matching with inability detection and numeric tolerance.
        
        Returns dict with:
            - has_expected: bool (final determination)
            - pattern_found: bool (raw pattern match)
            - indicates_inability: bool
            - numeric_match: bool
            - confidence: float
            - reason: str (explanation)
        """
        result = {
            "has_expected": False,
            "pattern_found": False,
            "indicates_inability": False,
            "numeric_match": False,
            "confidence": 0.0,
            "reason": ""
        }
        
        if not expected or not response_text:
            result["reason"] = "Empty text"
            return result
        
        text_lower = response_text.lower()
        expected_lower = expected.lower()
        
        # Check inability first (if enabled)
        if check_inability:
            result["indicates_inability"] = self.check_inability(response_text)
        
        # Check exact pattern match
        if expected_lower in text_lower:
            result["pattern_found"] = True
            result["confidence"] = 1.0
        else:
            # Partial match (split on punctuation/whitespace)
            expected_parts = [
                p.strip() 
                for p in re.split(r'[,;\s]+', expected_lower) 
                if len(p.strip()) > 3
            ]
            
            if expected_parts:
                matches = sum(1 for part in expected_parts if part in text_lower)
                result["confidence"] = matches / len(expected_parts)
                result["pattern_found"] = result["confidence"] >= 0.5
        
        # Check numeric match (for count-based questions)
        numeric_match, numeric_conf = self.check_numeric_match(response_text, expected)
        if numeric_match:
            result["numeric_match"] = True
            # Boost confidence if numeric match found
            result["confidence"] = max(result["confidence"], numeric_conf)
        
        # Final determination
        if result["pattern_found"] or result["numeric_match"]:
            if result["indicates_inability"]:
                # Pattern found but response indicates inability
                result["has_expected"] = False
                result["reason"] = "Pattern found but response indicates inability to answer"
            else:
                result["has_expected"] = True
                result["reason"] = "Pattern or numeric match found"
        else:
            result["has_expected"] = False
            result["reason"] = "No pattern or numeric match found"
        
        return result


class DiscrepancyAnalyzer:
    """Analyzes discrepancies between pattern matching and LLM evaluation."""
    
    DISCREPANCY_TYPES = {
        'FALSE_POSITIVE': 'Pattern matched but LLM says incorrect',
        'FALSE_NEGATIVE': 'Pattern missed but LLM says correct',
        'AGREEMENT_CORRECT': 'Both methods agree: correct',
        'AGREEMENT_INCORRECT': 'Both methods agree: incorrect'
    }
    
    def __init__(self, results: List[Dict]):
        self.results = results
        self.matcher = EnhancedPatternMatcher()
    
    def classify_discrepancy(
        self, 
        pattern_match: bool, 
        llm_match: bool
    ) -> str:
        """Classify the type of discrepancy."""
        if pattern_match and not llm_match:
            return 'FALSE_POSITIVE'
        elif not pattern_match and llm_match:
            return 'FALSE_NEGATIVE'
        elif pattern_match and llm_match:
            return 'AGREEMENT_CORRECT'
        else:
            return 'AGREEMENT_INCORRECT'
    
    def analyze_all(self) -> Dict[str, Any]:
        """Analyze all discrepancies in the results."""
        analysis = {
            'baseline': {
                'FALSE_POSITIVE': [],
                'FALSE_NEGATIVE': [],
                'total_discrepancies': 0,
                'agreement_rate': 0.0
            },
            'togomcp': {
                'FALSE_POSITIVE': [],
                'FALSE_NEGATIVE': [],
                'total_discrepancies': 0,
                'agreement_rate': 0.0
            },
            'root_causes': defaultdict(int),
            'by_category': defaultdict(lambda: {'baseline': 0, 'togomcp': 0})
        }
        
        total = len(self.results)
        baseline_agree = 0
        togomcp_agree = 0
        
        for r in self.results:
            q_id = r.get('question_id')
            category = r.get('category', 'Unknown')
            
            # Parse boolean values
            baseline_pattern = str(r.get('baseline_has_expected', 'False')).lower() == 'true'
            baseline_llm = str(r.get('baseline_llm_match', 'False')).lower() == 'true'
            togomcp_pattern = str(r.get('togomcp_has_expected', 'False')).lower() == 'true'
            togomcp_llm = str(r.get('togomcp_llm_match', 'False')).lower() == 'true'
            
            # Baseline analysis
            baseline_type = self.classify_discrepancy(baseline_pattern, baseline_llm)
            if baseline_type in ['FALSE_POSITIVE', 'FALSE_NEGATIVE']:
                analysis['baseline'][baseline_type].append({
                    'question_id': q_id,
                    'category': category,
                    'question': r.get('question_text', '')[:80],
                    'expected': r.get('expected_answer', ''),
                    'pattern_confidence': r.get('baseline_confidence'),
                    'llm_confidence': r.get('baseline_llm_confidence'),
                    'llm_explanation': r.get('baseline_llm_explanation', ''),
                    'response_snippet': str(r.get('baseline_text', ''))[:200]
                })
                analysis['baseline']['total_discrepancies'] += 1
                analysis['by_category'][category]['baseline'] += 1
                
                # Root cause analysis
                if baseline_type == 'FALSE_POSITIVE':
                    response = str(r.get('baseline_text', ''))
                    if self.matcher.check_inability(response):
                        analysis['root_causes']['Pattern in inability response'] += 1
                    else:
                        analysis['root_causes']['Pattern in non-answer context'] += 1
                else:
                    analysis['root_causes']['Semantic match not captured by pattern'] += 1
            else:
                baseline_agree += 1
            
            # TogoMCP analysis
            togomcp_type = self.classify_discrepancy(togomcp_pattern, togomcp_llm)
            if togomcp_type in ['FALSE_POSITIVE', 'FALSE_NEGATIVE']:
                analysis['togomcp'][togomcp_type].append({
                    'question_id': q_id,
                    'category': category,
                    'question': r.get('question_text', '')[:80],
                    'expected': r.get('expected_answer', ''),
                    'pattern_confidence': r.get('togomcp_confidence'),
                    'llm_confidence': r.get('togomcp_llm_confidence'),
                    'llm_explanation': r.get('togomcp_llm_explanation', ''),
                    'response_snippet': str(r.get('togomcp_text', ''))[:200]
                })
                analysis['togomcp']['total_discrepancies'] += 1
                analysis['by_category'][category]['togomcp'] += 1
                
                # Root cause analysis
                if togomcp_type == 'FALSE_POSITIVE':
                    analysis['root_causes']['Different/outdated data returned'] += 1
                else:
                    analysis['root_causes']['Data updated since expected answer'] += 1
            else:
                togomcp_agree += 1
        
        if total > 0:
            analysis['baseline']['agreement_rate'] = baseline_agree / total
            analysis['togomcp']['agreement_rate'] = togomcp_agree / total
        
        return analysis
    
    def print_report(self):
        """Print detailed discrepancy report."""
        analysis = self.analyze_all()
        
        print("\n" + "=" * 70)
        print("DISCREPANCY ANALYSIS: PATTERN MATCHING vs LLM EVALUATION")
        print("=" * 70)
        
        total = len(self.results)
        
        # Summary
        print(f"\n📊 SUMMARY")
        print("-" * 70)
        print(f"Total questions: {total}")
        print(f"\nBaseline:")
        print(f"  Agreement rate: {analysis['baseline']['agreement_rate']*100:.1f}%")
        print(f"  Total discrepancies: {analysis['baseline']['total_discrepancies']}")
        print(f"    - False Positives: {len(analysis['baseline']['FALSE_POSITIVE'])}")
        print(f"    - False Negatives: {len(analysis['baseline']['FALSE_NEGATIVE'])}")
        
        print(f"\nTogoMCP:")
        print(f"  Agreement rate: {analysis['togomcp']['agreement_rate']*100:.1f}%")
        print(f"  Total discrepancies: {analysis['togomcp']['total_discrepancies']}")
        print(f"    - False Positives: {len(analysis['togomcp']['FALSE_POSITIVE'])}")
        print(f"    - False Negatives: {len(analysis['togomcp']['FALSE_NEGATIVE'])}")
        
        # Root causes
        print(f"\n🔍 ROOT CAUSES")
        print("-" * 70)
        for cause, count in sorted(analysis['root_causes'].items(), key=lambda x: -x[1]):
            print(f"  {cause}: {count}")
        
        # By category
        print(f"\n📂 DISCREPANCIES BY CATEGORY")
        print("-" * 70)
        for category, counts in sorted(analysis['by_category'].items()):
            print(f"  {category}: Baseline={counts['baseline']}, TogoMCP={counts['togomcp']}")
        
        # Detailed examples
        print(f"\n📋 SAMPLE FALSE POSITIVES (Baseline)")
        print("-" * 70)
        print("(Pattern found keywords but LLM correctly identified non-answers)")
        for item in analysis['baseline']['FALSE_POSITIVE'][:5]:
            print(f"\n  Q{item['question_id']} [{item['category']}]")
            print(f"  Expected: {item['expected']}")
            print(f"  LLM says: {item['llm_explanation'][:100]}...")
            print(f"  Response: {item['response_snippet'][:150]}...")
        
        if len(analysis['baseline']['FALSE_POSITIVE']) > 5:
            print(f"\n  ... and {len(analysis['baseline']['FALSE_POSITIVE']) - 5} more")
        
        print(f"\n📋 SAMPLE FALSE NEGATIVES (TogoMCP)")
        print("-" * 70)
        print("(Pattern missed but LLM recognized correct answer)")
        for item in analysis['togomcp']['FALSE_NEGATIVE'][:5]:
            print(f"\n  Q{item['question_id']} [{item['category']}]")
            print(f"  Expected: {item['expected']}")
            print(f"  LLM says: {item['llm_explanation'][:100]}...")
        
        if len(analysis['togomcp']['FALSE_NEGATIVE']) > 5:
            print(f"\n  ... and {len(analysis['togomcp']['FALSE_NEGATIVE']) - 5} more")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 70)
        
        baseline_fp = len(analysis['baseline']['FALSE_POSITIVE'])
        togomcp_fn = len(analysis['togomcp']['FALSE_NEGATIVE'])
        
        if baseline_fp > 10:
            print(f"""
1. HIGH BASELINE FALSE POSITIVE RATE ({baseline_fp} cases)
   Root cause: Pattern matching finds keywords in "I don't know" responses
   Solution: Use LLM-based evaluation as primary metric
   Benefit: More accurate baseline success rate measurement
""")
        
        if togomcp_fn > 5:
            print(f"""
2. TOGOMCP FALSE NEGATIVES ({togomcp_fn} cases)
   Root cause: Database counts change over time
   Solution: Use numeric tolerance (±15%) for count comparisons
   Benefit: Accept current accurate data as correct
""")
        
        print("""
3. RECOMMENDED PRIMARY METRIC
   Use: full_combined_*_found (Pattern OR LLM match)
   Rationale: Captures both exact matches and semantic equivalence
   
4. FOR FUTURE EVALUATIONS
   - Periodically update expected answers with fresh database queries
   - Add timestamp to expected answers for time-sensitive data
   - Use LLM evaluation for final scoring
""")


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
        self.matcher = EnhancedPatternMatcher()
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
        
        # Auto-detect mode - PREFER LLM when available (key recommendation)
        if self.mode == 'auto':
            if self.has_llm_columns:
                self.mode = 'llm'  # Changed from 'combined' to 'llm' per recommendation
                print(f"✓ Detected LLM evaluation columns - using LLM mode (recommended)")
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
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes')
    
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
            'llm': 'LLM EVALUATION (Recommended)',
            'combined': 'COMBINED (Pattern OR LLM)'
        }[self.mode]
        
        print("=" * 70)
        print(f"EVALUATION RESULTS ANALYSIS - {mode_label}")
        print("=" * 70)
        print(f"\nTotal Questions: {total}\n")
        
        print("BASELINE PERFORMANCE:")
        print(f"  Technical Success:          {baseline_success}/{total} ({baseline_success/total*100:.1f}%)")
        print(f"  Actually Answered:          {baseline_answered}/{total} ({baseline_answered/total*100:.1f}%)")
        print(f"  Has Expected Answer:        {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
        
        # Show ALL method comparison when LLM columns available
        if self.has_llm_columns:
            pattern_correct = sum(1 for r in self.results if self._parse_bool(r.get('baseline_has_expected', 'False')))
            llm_correct = sum(1 for r in self.results if self._parse_bool(r.get('baseline_llm_match', 'False')))
            combined_correct = sum(1 for r in self.results if self._parse_bool(r.get('full_combined_baseline_found', 'False')))
            
            print(f"\n  📊 Method Comparison:")
            print(f"    Pattern matching:         {pattern_correct}/{total} ({pattern_correct/total*100:.1f}%)")
            print(f"    LLM evaluation:           {llm_correct}/{total} ({llm_correct/total*100:.1f}%)")
            print(f"    Combined (Pattern|LLM):   {combined_correct}/{total} ({combined_correct/total*100:.1f}%)")
            
            # Show breakdown
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
            print(f"      ├─ Pattern only:        {pattern_only} (likely false positives)")
            print(f"      ├─ LLM only:            {llm_only}")
            print(f"      └─ Both methods:        {both}")
        
        print()
        
        print("TOGOMCP PERFORMANCE:")
        print(f"  Technical Success:          {togomcp_success}/{total} ({togomcp_success/total*100:.1f}%)")
        print(f"  Has Expected Answer:        {togomcp_correct}/{total} ({togomcp_correct/total*100:.1f}%)")
        print(f"  Used Tools:                 {tools_used_count}/{total} ({tools_used_count/total*100:.1f}%)")
        
        # Show ALL method comparison for TogoMCP
        if self.has_llm_columns:
            pattern_correct = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_has_expected', 'False')))
            llm_correct = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_llm_match', 'False')))
            combined_correct = sum(1 for r in self.results if self._parse_bool(r.get('full_combined_togomcp_found', 'False')))
            
            print(f"\n  📊 Method Comparison:")
            print(f"    Pattern matching:         {pattern_correct}/{total} ({pattern_correct/total*100:.1f}%)")
            print(f"    LLM evaluation:           {llm_correct}/{total} ({llm_correct/total*100:.1f}%)")
            print(f"    Combined (Pattern|LLM):   {combined_correct}/{total} ({combined_correct/total*100:.1f}%)")
            
            # Show breakdown
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
            print(f"      ├─ Pattern only:        {pattern_only} (may be false positives)")
            print(f"      ├─ LLM only:            {llm_only} (often data updates)")
            print(f"      └─ Both methods:        {both}")
        
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
        print("-" * 70)
        
        for category in sorted(categories.keys()):
            results = categories[category]
            total = len(results)
            
            answered = sum(1 for r in results if self._parse_bool(r.get('baseline_actually_answered', 'False')))
            baseline_correct = sum(1 for r in results if self._parse_bool(r.get(baseline_col, 'False')))
            togomcp_correct = sum(1 for r in results if self._parse_bool(r.get(togomcp_col, 'False')))
            value_add = Counter(r.get('value_add', 'MARGINAL') for r in results)
            critical = value_add['CRITICAL']
            
            # Show discrepancy count if LLM available
            discrepancy_info = ""
            if self.has_llm_columns:
                baseline_disc = sum(
                    1 for r in results
                    if self._parse_bool(r.get('baseline_has_expected', 'False')) != 
                       self._parse_bool(r.get('baseline_llm_match', 'False'))
                )
                togomcp_disc = sum(
                    1 for r in results
                    if self._parse_bool(r.get('togomcp_has_expected', 'False')) != 
                       self._parse_bool(r.get('togomcp_llm_match', 'False'))
                )
                discrepancy_info = f"  Eval Discrepancies:   Base={baseline_disc}, Togo={togomcp_disc}"
            
            print(f"\n{category} ({total} questions):")
            print(f"  Baseline Answered:    {answered}/{total} ({answered/total*100:.1f}%)")
            print(f"  Baseline Correct:     {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
            print(f"  TogoMCP Correct:      {togomcp_correct}/{total} ({togomcp_correct/total*100:.1f}%)")
            print(f"  CRITICAL Questions:   {critical}/{total}")
            if discrepancy_info:
                print(discrepancy_info)
            print(f"  Value Distribution:   {dict(value_add)}")
    
    def list_questions_by_value(self):
        """List questions grouped by value-add."""
        by_value = defaultdict(list)
        for r in self.results:
            value = r.get('value_add', 'MARGINAL')
            by_value[value].append(r)
        
        print("\nQUESTIONS BY VALUE-ADD:")
        print("-" * 70)
        
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
        print("-" * 70)
        
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
        
        # Pattern found but LLM missed (FALSE POSITIVES)
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
        
        print(f"\n⚠️  FALSE POSITIVES (Pattern=True, LLM=False):")
        print(f"  Baseline:  {baseline_pattern_only}")
        print(f"  TogoMCP:   {togomcp_pattern_only}")
        print(f"  Cause: Pattern finds keywords in 'I don't know' responses")
        
        # LLM found but pattern missed (FALSE NEGATIVES)
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
        
        print(f"\n✓ FALSE NEGATIVES (Pattern=False, LLM=True):")
        print(f"  Baseline:  {baseline_llm_only}")
        print(f"  TogoMCP:   {togomcp_llm_only}")
        print(f"  Cause: Semantic matches / data updates not captured by pattern")
        
        print(f"\n💡 IMPACT ON METRICS:")
        baseline_pattern = sum(1 for r in self.results if self._parse_bool(r.get('baseline_has_expected', 'False')))
        baseline_llm = sum(1 for r in self.results if self._parse_bool(r.get('baseline_llm_match', 'False')))
        print(f"  Baseline: Pattern={baseline_pattern/total*100:.1f}% → LLM={baseline_llm/total*100:.1f}%")
        print(f"    (Pattern OVERESTIMATES by {(baseline_pattern-baseline_llm)/total*100:.1f} percentage points)")
        
        togomcp_pattern = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_has_expected', 'False')))
        togomcp_llm = sum(1 for r in self.results if self._parse_bool(r.get('togomcp_llm_match', 'False')))
        diff = (togomcp_llm - togomcp_pattern) / total * 100
        direction = "UNDERESTIMATES" if diff > 0 else "OVERESTIMATES"
        print(f"  TogoMCP:  Pattern={togomcp_pattern/total*100:.1f}% → LLM={togomcp_llm/total*100:.1f}%")
        print(f"    (Pattern {direction} by {abs(diff):.1f} percentage points)")
    
    def identify_issues(self):
        """Identify problematic questions with enhanced analysis."""
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
                    'severity': 'HIGH',
                    'message': 'Baseline answered, TogoMCP didn\'t use tools - should be replaced'
                })
            
            # MARGINAL questions need improvement
            elif value == 'MARGINAL':
                issues.append({
                    'id': q_id,
                    'type': 'MARGINAL',
                    'severity': 'MEDIUM',
                    'message': 'Low value-add - consider replacing with harder question'
                })
            
            # FAILED questions need investigation
            elif value == 'FAILED':
                issues.append({
                    'id': q_id,
                    'type': 'FAILED',
                    'severity': 'HIGH',
                    'message': 'TogoMCP failed - check error logs'
                })
            
            # Check for evaluation discrepancies (if in LLM mode)
            if self.has_llm_columns:
                # Baseline false positive (pattern inflating success)
                if (self._parse_bool(r.get('baseline_has_expected', 'False')) and 
                    not self._parse_bool(r.get('baseline_llm_match', 'False'))):
                    issues.append({
                        'id': q_id,
                        'type': 'BASELINE_FALSE_POSITIVE',
                        'severity': 'INFO',
                        'message': 'Pattern matched but LLM says baseline didn\'t answer correctly'
                    })
                
                # TogoMCP false negative (pattern underreporting)
                if (self._parse_bool(r.get('togomcp_llm_match', 'False')) and 
                    not self._parse_bool(r.get('togomcp_has_expected', 'False'))):
                    issues.append({
                        'id': q_id,
                        'type': 'TOGOMCP_FALSE_NEGATIVE',
                        'severity': 'INFO',
                        'message': 'LLM says correct but pattern didn\'t match - may need expected answer update'
                    })
                
                # Low confidence LLM matches
                if (self._parse_bool(r.get(togomcp_col, 'False')) and 
                    r.get('togomcp_llm_confidence') == 'low'):
                    issues.append({
                        'id': q_id,
                        'type': 'LOW_CONFIDENCE',
                        'severity': 'LOW',
                        'message': 'TogoMCP marked correct but with low LLM confidence'
                    })
        
        # Group by severity
        high_issues = [i for i in issues if i['severity'] == 'HIGH']
        medium_issues = [i for i in issues if i['severity'] == 'MEDIUM']
        info_issues = [i for i in issues if i['severity'] == 'INFO']
        
        if issues:
            print("\n⚠️ ISSUES FOUND:")
            print("-" * 70)
            
            if high_issues:
                print(f"\n🔴 HIGH SEVERITY ({len(high_issues)} issues):")
                for issue in high_issues[:10]:
                    print(f"  Q{issue['id']}: [{issue['type']}] {issue['message']}")
                if len(high_issues) > 10:
                    print(f"  ... and {len(high_issues) - 10} more")
            
            if medium_issues:
                print(f"\n🟡 MEDIUM SEVERITY ({len(medium_issues)} issues):")
                for issue in medium_issues[:10]:
                    print(f"  Q{issue['id']}: [{issue['type']}] {issue['message']}")
                if len(medium_issues) > 10:
                    print(f"  ... and {len(medium_issues) - 10} more")
            
            if info_issues:
                print(f"\n🔵 INFO ({len(info_issues)} items - evaluation discrepancies):")
                type_counts = Counter(i['type'] for i in info_issues)
                for t, c in type_counts.items():
                    print(f"  {t}: {c} questions")
        else:
            print("\n✓ No major issues found")
        
        print()
    
    def print_recommendations(self):
        """Print recommendations based on analysis."""
        total = len(self.results)
        value_counts = Counter(r.get('value_add', 'MARGINAL') for r in self.results)
        
        critical_pct = value_counts['CRITICAL'] / total * 100
        valuable_pct = value_counts['VALUABLE'] / total * 100
        marginal_pct = value_counts['MARGINAL'] / total * 100
        redundant_pct = value_counts['REDUNDANT'] / total * 100
        
        print("💡 RECOMMENDATIONS:")
        print("-" * 70)
        
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
        
        # Evaluation method recommendations
        print(f"\n📊 EVALUATION METHOD RECOMMENDATIONS:")
        if self.has_llm_columns:
            print(f"   Current mode: {self.mode.upper()}")
            
            # Calculate discrepancy impact
            baseline_pattern = sum(1 for r in self.results if self._parse_bool(r.get('baseline_has_expected', 'False')))
            baseline_llm = sum(1 for r in self.results if self._parse_bool(r.get('baseline_llm_match', 'False')))
            
            if baseline_pattern > baseline_llm + 5:
                print(f"\n   ⚠️  IMPORTANT: Pattern matching may be OVERESTIMATING baseline performance")
                print(f"      Pattern: {baseline_pattern/total*100:.1f}% vs LLM: {baseline_llm/total*100:.1f}%")
                print(f"      Reason: Pattern finds keywords in 'I don't know' responses")
                print(f"      Action: Use LLM evaluation as primary metric (--mode llm)")
            
            if self.mode == 'pattern':
                print("\n   💡 Recommendation: Run with --mode llm for more accurate results")
            elif self.mode == 'combined':
                print("\n   💡 Combined mode provides most comprehensive assessment")
                print("      but may include some false positives from pattern matching")
            elif self.mode == 'llm':
                print("\n   ✅ LLM mode provides most accurate evaluation")
        else:
            print("   Pattern matching only - consider running add_llm_evaluation.py")
            print("   for more robust evaluation that handles:")
            print("   - 'I don't know' responses with expected keywords")
            print("   - Semantic matches with different phrasing")
            print("   - Dynamic data that has changed since expected answers")
        
        print("\n📋 NEXT STEPS:")
        print("   1. Use LLM-based evaluation as the primary metric")
        print("   2. Review REDUNDANT questions and replace them")
        print("   3. Update expected answers for questions with data updates")
        print("   4. Add more database-specific questions for CRITICAL coverage")
        print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Unified analyzer supporting both pattern matching and LLM evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python results_analyzer_unified.py results.csv
  python results_analyzer_unified.py results_with_llm.csv --mode llm
  python results_analyzer_unified.py results_with_llm.csv --discrepancy
  python results_analyzer_unified.py results_with_llm.csv --enhanced
  python results_analyzer_unified.py results_with_llm.csv --quality --statistical
  python results_analyzer_unified.py results_with_llm.csv --confusion-matrix
        """
    )
    parser.add_argument("results_file", help="Path to results CSV file")
    parser.add_argument(
        "--mode",
        choices=['auto', 'pattern', 'llm', 'combined'],
        default='auto',
        help="Evaluation mode (default: auto-detect, prefers LLM when available)"
    )
    parser.add_argument(
        "--no-comparison",
        action='store_true',
        help="Skip pattern vs LLM comparison"
    )
    parser.add_argument(
        "--discrepancy",
        action='store_true',
        help="Show detailed discrepancy analysis"
    )
    parser.add_argument(
        "--brief",
        action='store_true',
        help="Show only overall stats and recommendations"
    )
    parser.add_argument(
        "--enhanced",
        action='store_true',
        help="Run all enhanced analyses (statistical, confusion matrix, quality)"
    )
    parser.add_argument(
        "--statistical",
        action='store_true',
        help="Show statistical significance analysis (requires scipy, sklearn)"
    )
    parser.add_argument(
        "--confusion-matrix",
        action='store_true',
        help="Show confusion matrix analysis"
    )
    parser.add_argument(
        "--quality",
        action='store_true',
        help="Show question quality scoring"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = UnifiedAnalyzer(args.results_file, mode=args.mode)
        analyzer.get_overall_stats()
        
        if not args.brief:
            analyzer.get_category_breakdown()
            analyzer.list_questions_by_value()
        
        if not args.no_comparison and analyzer.has_llm_columns:
            analyzer.compare_evaluation_methods()
        
        # Detailed discrepancy analysis if requested
        if args.discrepancy and analyzer.has_llm_columns:
            disc_analyzer = DiscrepancyAnalyzer(analyzer.results)
            disc_analyzer.print_report()
        
        if not args.brief:
            analyzer.identify_issues()
        
        # Enhanced analyses (if requested and LLM columns available)
        if analyzer.has_llm_columns:
            if args.enhanced or args.statistical:
                if SCIPY_AVAILABLE and SKLEARN_AVAILABLE:
                    try:
                        stats = StatisticalAnalyzer(analyzer.results)
                        stats.print_statistical_comparison()
                    except Exception as e:
                        print(f"\n⚠️  Statistical analysis failed: {e}")
                else:
                    print("\n⚠️  Statistical analysis requires scipy and scikit-learn")
                    print("   Install with: pip install scipy scikit-learn")
            
            if args.enhanced or args.confusion_matrix:
                try:
                    matrix = ConfusionMatrixAnalyzer(analyzer.results)
                    matrix.print_confusion_matrices()
                except Exception as e:
                    print(f"\n⚠️  Confusion matrix analysis failed: {e}")
            
            if args.enhanced or args.quality:
                try:
                    quality = QuestionQualityScorer()
                    quality.print_quality_report(analyzer.results)
                except Exception as e:
                    print(f"\n⚠️  Quality scoring failed: {e}")
        elif (args.enhanced or args.statistical or args.confusion_matrix or args.quality):
            print("\n⚠️  Enhanced analyses require LLM evaluation columns")
            print("   Run add_llm_evaluation.py first to add LLM evaluations")
        
        analyzer.print_recommendations()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()