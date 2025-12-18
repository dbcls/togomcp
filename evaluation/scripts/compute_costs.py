#!/usr/bin/env python3
"""
Cost Calculator for TogoMCP Evaluation Tests

This script computes the API costs for test runs by automated_test_runner.py,
providing separate cost breakdowns for baseline and TogoMCP evaluations.

Usage:
    python compute_costs.py evaluation_results.csv
    python compute_costs.py evaluation_results.csv --model claude-sonnet-4-20250514
    python compute_costs.py evaluation_results.csv --pricing custom_pricing.json
"""

import csv
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PricingInfo:
    """Pricing information for a model."""
    model_name: str
    input_price_per_mtok: float  # Price per million input tokens
    output_price_per_mtok: float  # Price per million output tokens
    cache_creation_price_per_mtok: float = None  # Cache write price (usually +25%)
    cache_read_price_per_mtok: float = None  # Cache read price (usually -90%)
    
    def __post_init__(self):
        """Set cache pricing based on base input price if not specified."""
        if self.cache_creation_price_per_mtok is None:
            # Cache creation typically costs 25% more than regular input
            self.cache_creation_price_per_mtok = self.input_price_per_mtok * 1.25
        if self.cache_read_price_per_mtok is None:
            # Cache read typically costs 90% less than regular input
            self.cache_read_price_per_mtok = self.input_price_per_mtok * 0.10
    
    def compute_cost(self, input_tokens: int, output_tokens: int, 
                    cache_creation_tokens: int = 0, cache_read_tokens: int = 0) -> float:
        """Compute cost for given token counts including cache tokens."""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_mtok
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_mtok
        cache_creation_cost = (cache_creation_tokens / 1_000_000) * self.cache_creation_price_per_mtok
        cache_read_cost = (cache_read_tokens / 1_000_000) * self.cache_read_price_per_mtok
        return input_cost + output_cost + cache_creation_cost + cache_read_cost


# Default pricing for common models (as of December 2024)
# https://www.anthropic.com/pricing
# Cache pricing: creation +25%, read -90%
DEFAULT_PRICING = {
    "claude-sonnet-4-20250514": PricingInfo(
        model_name="Claude Sonnet 4",
        input_price_per_mtok=3.0,
        output_price_per_mtok=15.0,
        cache_creation_price_per_mtok=3.75,
        cache_read_price_per_mtok=0.30
    ),
    "claude-opus-4-20250514": PricingInfo(
        model_name="Claude Opus 4",
        input_price_per_mtok=15.0,
        output_price_per_mtok=75.0,
        cache_creation_price_per_mtok=18.75,
        cache_read_price_per_mtok=1.50
    ),
    "claude-haiku-4-20250110": PricingInfo(
        model_name="Claude Haiku 4",
        input_price_per_mtok=0.8,
        output_price_per_mtok=4.0,
        cache_creation_price_per_mtok=1.0,
        cache_read_price_per_mtok=0.08
    ),
    "claude-sonnet-3-5-20241022": PricingInfo(
        model_name="Claude 3.5 Sonnet",
        input_price_per_mtok=3.0,
        output_price_per_mtok=15.0,
        cache_creation_price_per_mtok=3.75,
        cache_read_price_per_mtok=0.30
    ),
}


class CostCalculator:
    """Calculates costs from evaluation results."""
    
    def __init__(self, pricing: PricingInfo, estimate_togomcp: bool = True):
        """
        Initialize cost calculator.
        
        Args:
            pricing: Pricing information for the model
            estimate_togomcp: If True, estimate TogoMCP costs based on baseline
        """
        self.pricing = pricing
        self.estimate_togomcp = estimate_togomcp
    
    def load_results(self, csv_path: str) -> List[Dict]:
        """Load results from CSV file."""
        results = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
        return results
    
    def calculate_baseline_costs(self, results: List[Dict]) -> Dict:
        """Calculate costs for baseline tests."""
        total_input_tokens = 0
        total_output_tokens = 0
        successful_tests = 0
        
        for result in results:
            if result.get("baseline_success") == "True":
                try:
                    input_tokens = int(result.get("baseline_input_tokens", 0))
                    output_tokens = int(result.get("baseline_output_tokens", 0))
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    successful_tests += 1
                except (ValueError, TypeError):
                    pass
        
        total_cost = self.pricing.compute_cost(total_input_tokens, total_output_tokens)
        
        return {
            "total_tests": len(results),
            "successful_tests": successful_tests,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost": total_cost,
            "avg_cost_per_test": total_cost / len(results) if results else 0,
        }
    
    def estimate_togomcp_tokens(self, results: List[Dict]) -> Tuple[int, int]:
        """
        Estimate TogoMCP token usage based on response text and tool usage.
        
        This is an approximation since Agent SDK doesn't expose token counts.
        Estimation method:
        - Count characters in response, divide by ~4 (rough tokens-to-chars ratio)
        - Add estimated overhead for tool use (system prompts, tool schemas, etc.)
        """
        total_input_tokens = 0
        total_output_tokens = 0
        
        for result in results:
            if result.get("togomcp_success") == "True":
                # Estimate output tokens from response text
                text = result.get("togomcp_text", "")
                estimated_output = len(text) // 4  # Rough approximation
                
                # Estimate input tokens
                question = result.get("question_text", "")
                base_input = len(question) // 4
                
                # Add overhead for tool schemas and system prompts
                # MCP tools add significant schema overhead (~1000-2000 tokens)
                tool_overhead = 1500
                
                # Add tokens for tool uses (each tool call adds input/output)
                tools_used = result.get("tools_used", "")
                num_tools = len(tools_used.split(", ")) if tools_used else 0
                
                # Each tool use: ~200 tokens input (tool call) + ~500 tokens output (result)
                tool_tokens_input = num_tools * 200
                tool_tokens_output = num_tools * 500
                
                estimated_input = base_input + tool_overhead + tool_tokens_input
                estimated_output += tool_tokens_output
                
                total_input_tokens += estimated_input
                total_output_tokens += estimated_output
        
        return total_input_tokens, total_output_tokens
    
    def calculate_togomcp_costs(self, results: List[Dict]) -> Dict:
        """
        Calculate costs for TogoMCP tests.
        
        Uses actual token counts if available, otherwise estimates.
        """
        successful_tests = sum(1 for r in results if r.get("togomcp_success") == "True")
        
        # Check if actual token counts are available
        has_actual_tokens = any(
            r.get("togomcp_input_tokens") or r.get("togomcp_output_tokens")
            for r in results if r.get("togomcp_success") == "True"
        )
        
        if has_actual_tokens:
            # Use actual token counts from Agent SDK
            total_input_tokens = 0
            total_output_tokens = 0
            total_cache_creation = 0
            total_cache_read = 0
            
            for result in results:
                if result.get("togomcp_success") == "True":
                    try:
                        input_tokens = int(result.get("togomcp_input_tokens", 0))
                        output_tokens = int(result.get("togomcp_output_tokens", 0))
                        cache_creation = int(result.get("togomcp_cache_creation_input_tokens", 0))
                        cache_read = int(result.get("togomcp_cache_read_input_tokens", 0))
                        
                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens
                        total_cache_creation += cache_creation
                        total_cache_read += cache_read
                    except (ValueError, TypeError):
                        pass
            
            # Calculate cost with proper cache pricing
            total_cost = self.pricing.compute_cost(
                total_input_tokens, 
                total_output_tokens,
                cache_creation_tokens=total_cache_creation,
                cache_read_tokens=total_cache_read
            )
            estimated = False
            
            return {
                "total_tests": len(results),
                "successful_tests": successful_tests,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cache_creation_tokens": total_cache_creation,
                "cache_read_tokens": total_cache_read,
                "total_tokens": total_input_tokens + total_output_tokens,
                "total_cost": total_cost,
                "avg_cost_per_test": total_cost / len(results) if results else 0,
                "estimated": estimated,
            }
        elif self.estimate_togomcp:
            # Fall back to estimation
            input_tokens, output_tokens = self.estimate_togomcp_tokens(results)
            total_cost = self.pricing.compute_cost(input_tokens, output_tokens)
            estimated = True
            
            return {
                "total_tests": len(results),
                "successful_tests": successful_tests,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "total_cost": total_cost,
                "avg_cost_per_test": total_cost / len(results) if results else 0,
                "estimated": estimated,
            }
        else:
            # Can't calculate without token counts
            return {
                "total_tests": len(results),
                "successful_tests": successful_tests,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_cost_per_test": 0.0,
                "estimated": False,
            }
    
    def calculate_by_category(self, results: List[Dict]) -> Dict[str, Dict]:
        """Calculate costs broken down by question category."""
        categories = {}
        
        for result in results:
            category = result.get("category", "Unknown")
            
            if category not in categories:
                categories[category] = {
                    "baseline": {"tests": 0, "input": 0, "output": 0, "cost": 0.0},
                    "togomcp": {"tests": 0, "input": 0, "output": 0, "cost": 0.0},
                }
            
            # Baseline
            if result.get("baseline_success") == "True":
                try:
                    inp = int(result.get("baseline_input_tokens", 0))
                    out = int(result.get("baseline_output_tokens", 0))
                    categories[category]["baseline"]["tests"] += 1
                    categories[category]["baseline"]["input"] += inp
                    categories[category]["baseline"]["output"] += out
                    categories[category]["baseline"]["cost"] += self.pricing.compute_cost(inp, out)
                except (ValueError, TypeError):
                    pass
            
            # TogoMCP (use actual tokens if available, otherwise estimate)
            if result.get("togomcp_success") == "True":
                inp = 0
                out = 0
                
                # Try to get actual token counts first
                if result.get("togomcp_input_tokens"):
                    try:
                        inp = int(result.get("togomcp_input_tokens", 0))
                        out = int(result.get("togomcp_output_tokens", 0))
                    except (ValueError, TypeError):
                        pass
                
                # Fall back to estimation if no actual tokens
                if inp == 0 and out == 0 and self.estimate_togomcp:
                    text = result.get("togomcp_text", "")
                    question = result.get("question_text", "")
                    tools_used = result.get("tools_used", "")
                    num_tools = len(tools_used.split(", ")) if tools_used else 0
                    
                    inp = len(question) // 4 + 1500 + num_tools * 200
                    out = len(text) // 4 + num_tools * 500
                
                if inp > 0 or out > 0:
                    # Get cache tokens if available
                    cache_create = 0
                    cache_read_tok = 0
                    if result.get("togomcp_cache_creation_input_tokens"):
                        try:
                            cache_create = int(result.get("togomcp_cache_creation_input_tokens", 0))
                            cache_read_tok = int(result.get("togomcp_cache_read_input_tokens", 0))
                        except (ValueError, TypeError):
                            pass
                    
                    categories[category]["togomcp"]["tests"] += 1
                    categories[category]["togomcp"]["input"] += inp
                    categories[category]["togomcp"]["output"] += out
                    categories[category]["togomcp"]["cost"] += self.pricing.compute_cost(
                        inp, out, cache_create, cache_read_tok
                    )
        
        return categories
    
    def calculate_by_value_add(self, results: List[Dict]) -> Dict[str, Dict]:
        """Calculate costs by value-add category."""
        value_adds = {}
        
        for result in results:
            value_add = result.get("value_add", "Unknown")
            
            if value_add not in value_adds:
                value_adds[value_add] = {
                    "count": 0,
                    "baseline_cost": 0.0,
                    "togomcp_cost": 0.0,
                }
            
            value_adds[value_add]["count"] += 1
            
            # Baseline cost
            if result.get("baseline_success") == "True":
                try:
                    inp = int(result.get("baseline_input_tokens", 0))
                    out = int(result.get("baseline_output_tokens", 0))
                    value_adds[value_add]["baseline_cost"] += self.pricing.compute_cost(inp, out)
                except (ValueError, TypeError):
                    pass
            
            # TogoMCP cost (use actual tokens if available, otherwise estimate)
            if result.get("togomcp_success") == "True":
                inp = 0
                out = 0
                
                # Try to get actual token counts first
                if result.get("togomcp_input_tokens"):
                    try:
                        inp = int(result.get("togomcp_input_tokens", 0))
                        out = int(result.get("togomcp_output_tokens", 0))
                    except (ValueError, TypeError):
                        pass
                
                # Fall back to estimation if no actual tokens
                if inp == 0 and out == 0 and self.estimate_togomcp:
                    text = result.get("togomcp_text", "")
                    question = result.get("question_text", "")
                    tools_used = result.get("tools_used", "")
                    num_tools = len(tools_used.split(", ")) if tools_used else 0
                    
                    inp = len(question) // 4 + 1500 + num_tools * 200
                    out = len(text) // 4 + num_tools * 500
                
                if inp > 0 or out > 0:
                    # Get cache tokens if available
                    cache_create = 0
                    cache_read_tok = 0
                    if result.get("togomcp_cache_creation_input_tokens"):
                        try:
                            cache_create = int(result.get("togomcp_cache_creation_input_tokens", 0))
                            cache_read_tok = int(result.get("togomcp_cache_read_input_tokens", 0))
                        except (ValueError, TypeError):
                            pass
                    
                    value_adds[value_add]["togomcp_cost"] += self.pricing.compute_cost(
                        inp, out, cache_create, cache_read_tok
                    )
        
        return value_adds
    
    def print_summary(self, results: List[Dict]):
        """Print comprehensive cost summary."""
        baseline_costs = self.calculate_baseline_costs(results)
        togomcp_costs = self.calculate_togomcp_costs(results)
        
        print("\n" + "="*80)
        print("COST ANALYSIS FOR TOGOMCP EVALUATION")
        print("="*80)
        print(f"Model: {self.pricing.model_name}")
        print(f"Pricing: ${self.pricing.input_price_per_mtok:.2f}/MTok input, "
              f"${self.pricing.output_price_per_mtok:.2f}/MTok output")
        print(f"Total questions evaluated: {len(results)}")
        print()
        
        # Baseline costs
        print("BASELINE COSTS (No Tools)")
        print("-" * 80)
        print(f"  Successful tests:     {baseline_costs['successful_tests']}/{baseline_costs['total_tests']}")
        print(f"  Input tokens:         {baseline_costs['input_tokens']:,}")
        print(f"  Output tokens:        {baseline_costs['output_tokens']:,}")
        print(f"  Total tokens:         {baseline_costs['total_tokens']:,}")
        print(f"  Total cost:           ${baseline_costs['total_cost']:.4f}")
        print(f"  Avg cost per test:    ${baseline_costs['avg_cost_per_test']:.4f}")
        print()
        
        # TogoMCP costs
        status = " (ESTIMATED)" if togomcp_costs['estimated'] else " (EXACT)"
        print(f"TOGOMCP COSTS (With MCP Tools){status}")
        print("-" * 80)
        if togomcp_costs['estimated']:
            print("  ⚠️  Note: Using estimation (no actual token counts).")
            print("      Based on text length and tool usage.")
            print()
        else:
            print("  ✅ Using actual token counts from Agent SDK ResultMessage")
            print()
        print(f"  Successful tests:     {togomcp_costs['successful_tests']}/{togomcp_costs['total_tests']}")
        print(f"  Input tokens:         {togomcp_costs['input_tokens']:,}")
        print(f"  Output tokens:        {togomcp_costs['output_tokens']:,}")
        
        # Show cache information if available
        if 'cache_creation_tokens' in togomcp_costs:
            print(f"  Cache creation:       {togomcp_costs['cache_creation_tokens']:,} tokens")
            print(f"  Cache read:           {togomcp_costs['cache_read_tokens']:,} tokens")
        
        print(f"  Total tokens:         {togomcp_costs['total_tokens']:,}")
        print(f"  Total cost:           ${togomcp_costs['total_cost']:.4f}")
        print(f"  Avg cost per test:    ${togomcp_costs['avg_cost_per_test']:.4f}")
        print()
        
        # Comparison
        total_cost = baseline_costs['total_cost'] + togomcp_costs['total_cost']
        print("TOTAL EVALUATION COST")
        print("-" * 80)
        print(f"  Baseline:             ${baseline_costs['total_cost']:.4f} "
              f"({baseline_costs['total_cost']/total_cost*100:.1f}%)")
        print(f"  TogoMCP:              ${togomcp_costs['total_cost']:.4f} "
              f"({togomcp_costs['total_cost']/total_cost*100:.1f}%)")
        print(f"  TOTAL:                ${total_cost:.4f}")
        print()
        
        # Cost overhead
        if baseline_costs['total_cost'] > 0:
            overhead = (togomcp_costs['total_cost'] / baseline_costs['total_cost'] - 1) * 100
            print(f"  TogoMCP overhead:     {overhead:+.1f}% vs baseline")
        print()
        
        # By category
        category_costs = self.calculate_by_category(results)
        if category_costs:
            print("COSTS BY CATEGORY")
            print("-" * 80)
            for category, costs in sorted(category_costs.items()):
                baseline = costs["baseline"]["cost"]
                togomcp = costs["togomcp"]["cost"]
                total = baseline + togomcp
                print(f"  {category:20} ${total:8.4f}  (Base: ${baseline:.4f}, TogoMCP: ${togomcp:.4f})")
            print()
        
        # By value-add
        value_costs = self.calculate_by_value_add(results)
        if value_costs:
            print("COSTS BY VALUE-ADD CATEGORY")
            print("-" * 80)
            for value_add in ["CRITICAL", "VALUABLE", "MARGINAL", "REDUNDANT", "FAILED"]:
                if value_add in value_costs:
                    data = value_costs[value_add]
                    total = data["baseline_cost"] + data["togomcp_cost"]
                    print(f"  {value_add:12} ({data['count']:2} tests)  "
                          f"${total:8.4f}  (Base: ${data['baseline_cost']:.4f}, "
                          f"TogoMCP: ${data['togomcp_cost']:.4f})")
            print()
        
        print("="*80 + "\n")
    
    def export_cost_report(self, results: List[Dict], output_path: str):
        """Export detailed cost report as JSON."""
        baseline_costs = self.calculate_baseline_costs(results)
        togomcp_costs = self.calculate_togomcp_costs(results)
        category_costs = self.calculate_by_category(results)
        value_costs = self.calculate_by_value_add(results)
        
        report = {
            "model": self.pricing.model_name,
            "pricing": {
                "input_per_mtok": self.pricing.input_price_per_mtok,
                "output_per_mtok": self.pricing.output_price_per_mtok,
            },
            "total_questions": len(results),
            "baseline": baseline_costs,
            "togomcp": togomcp_costs,
            "total_cost": baseline_costs["total_cost"] + togomcp_costs["total_cost"],
            "by_category": category_costs,
            "by_value_add": value_costs,
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✓ Detailed cost report exported to {output_path}")


def load_custom_pricing(pricing_path: str) -> PricingInfo:
    """Load custom pricing from JSON file."""
    with open(pricing_path, 'r') as f:
        data = json.load(f)
    
    return PricingInfo(
        model_name=data.get("model_name", "Custom Model"),
        input_price_per_mtok=data["input_price_per_mtok"],
        output_price_per_mtok=data["output_price_per_mtok"]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Calculate API costs for TogoMCP evaluation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default pricing
  python compute_costs.py evaluation_results.csv
  
  # Specify model
  python compute_costs.py evaluation_results.csv --model claude-opus-4-20250514
  
  # Use custom pricing
  python compute_costs.py evaluation_results.csv --pricing custom_pricing.json
  
  # Export detailed report
  python compute_costs.py evaluation_results.csv --export cost_report.json
  
  # Don't estimate TogoMCP costs (only show baseline)
  python compute_costs.py evaluation_results.csv --no-estimate
        """
    )
    
    parser.add_argument("results_file", help="Path to evaluation results CSV file")
    parser.add_argument(
        "-m", "--model",
        help="Model identifier for pricing lookup",
        default="claude-sonnet-4-20250514"
    )
    parser.add_argument(
        "-p", "--pricing",
        help="Path to custom pricing JSON file"
    )
    parser.add_argument(
        "-e", "--export",
        help="Export detailed cost report to JSON file"
    )
    parser.add_argument(
        "--no-estimate",
        action="store_true",
        help="Don't estimate TogoMCP costs (only calculate baseline)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.results_file).exists():
        print(f"✗ Error: Results file not found: {args.results_file}")
        sys.exit(1)
    
    # Get pricing info
    if args.pricing:
        try:
            pricing = load_custom_pricing(args.pricing)
        except Exception as e:
            print(f"✗ Error loading custom pricing: {e}")
            sys.exit(1)
    else:
        if args.model not in DEFAULT_PRICING:
            print(f"✗ Error: Unknown model '{args.model}'")
            print(f"Available models: {', '.join(DEFAULT_PRICING.keys())}")
            sys.exit(1)
        pricing = DEFAULT_PRICING[args.model]
    
    # Calculate costs
    calculator = CostCalculator(pricing, estimate_togomcp=not args.no_estimate)
    
    try:
        results = calculator.load_results(args.results_file)
    except Exception as e:
        print(f"✗ Error loading results: {e}")
        sys.exit(1)
    
    if not results:
        print("✗ No results found in file")
        sys.exit(1)
    
    # Print summary
    calculator.print_summary(results)
    
    # Export if requested
    if args.export:
        try:
            calculator.export_cost_report(results, args.export)
        except Exception as e:
            print(f"✗ Error exporting report: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
