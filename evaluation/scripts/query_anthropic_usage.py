#!/usr/bin/env python3
"""
Anthropic Usage API Query Tool

This script demonstrates how to use Anthropic's Usage API to get actual
token usage and costs from your account.

Note: This gives you ACTUAL usage but requires querying before/after test runs
to calculate the difference attributable to your evaluation.

Usage:
    # Get usage for today
    python query_anthropic_usage.py
    
    # Get usage for a date range
    python query_anthropic_usage.py --start 2024-12-01 --end 2024-12-31
    
    # Save to file
    python query_anthropic_usage.py --output usage_report.json

Reference: https://docs.anthropic.com/en/api/usage
"""

import anthropic
import os
import json
import argparse
from datetime import datetime, timedelta

def query_usage(start_date=None, end_date=None):
    """
    Query Anthropic Usage API for token usage.
    
    Note: The Usage API may not be available in all API tiers.
    Check the Anthropic documentation for availability.
    """
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return None
    
    # Note: Usage API endpoint may vary
    # This is a conceptual example - check docs for actual endpoint
    client = anthropic.Anthropic(api_key=api_key)
    
    print("Note: The Usage API endpoint structure is not fully documented.")
    print("This script shows the CONCEPT of how you would use it.")
    print("\nTo get actual usage:")
    print("1. Check your Anthropic Console/Dashboard for usage metrics")
    print("2. Record usage before running evaluation")
    print("3. Record usage after running evaluation")
    print("4. Calculate difference = evaluation cost")
    print()
    
    # Example of what the usage data structure might look like
    example_usage = {
        "period_start": start_date or datetime.now().date().isoformat(),
        "period_end": end_date or datetime.now().date().isoformat(),
        "usage_by_model": {
            "claude-sonnet-4-20250514": {
                "input_tokens": 125000,
                "output_tokens": 45000,
                "cached_input_tokens": 10000,
                "cost_usd": 3.675  # Calculated from tokens
            }
        },
        "total_cost_usd": 3.675
    }
    
    return example_usage

def main():
    parser = argparse.ArgumentParser(
        description="Query Anthropic Usage API for actual token usage and costs"
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD)",
        default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD)",
        default=datetime.now().strftime("%Y-%m-%d")
    )
    parser.add_argument(
        "-o", "--output",
        help="Save results to JSON file"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("ANTHROPIC USAGE API QUERY")
    print("="*80)
    print(f"Date range: {args.start} to {args.end}\n")
    
    usage = query_usage(args.start, args.end)
    
    if usage:
        print("\nExample Usage Data Structure:")
        print(json.dumps(usage, indent=2))
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(usage, f, indent=2)
            print(f"\n✓ Saved to {args.output}")
    
    print("\n" + "="*80)
    print("ALTERNATIVE: Use Anthropic Console")
    print("="*80)
    print("The most reliable way to get actual usage:")
    print("1. Go to https://console.anthropic.com/")
    print("2. Navigate to Settings > Usage")
    print("3. View token usage and costs by date/model")
    print("4. Export usage reports if available")
    print("\nFor evaluation cost tracking:")
    print("- Record usage before test run")
    print("- Record usage after test run")
    print("- Difference = evaluation cost")
    print("="*80)

if __name__ == "__main__":
    main()
