#!/usr/bin/env python3
"""
Add LM-Based Evaluation to Existing Results

This script reads existing evaluation results CSV files and adds:
    - LLM-based evaluation using a generative model to judge if texts discuss the same topic (Ollama with llama3.2)

Usage:
    python add__llm_evaluation.py Q01_out.csv

Requirements:
    pip install ollama pandas
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional, Any
import re

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed. Install with: pip install pandas")
    sys.exit(1)

try:
    import ollama
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install ollama")
    sys.exit(1)


class LLMEvaluator:
    """Evaluates if two texts discuss the same topic using a generative LLM.
    
    Uses Ollama with a generative model (e.g., llama3.2, mistral) to determine
    if the response text contains the expected answer or discusses the same topic.
    """
    
    def __init__(self, model: str = "llama3.2"):
        """
        Initialize LLM evaluator.
        
        Args:
            model: Ollama generative model name (e.g., llama3.2, mistral)
        """
        self.model = model
    
    def evaluate_match(self, response_text: str, expected_answer: str) -> Dict[str, Any]:
        """
        Use LLM to evaluate if response contains or discusses the expected answer.
        
        Args:
            response_text: The LLM response to evaluate
            expected_answer: The expected answer to find
            
        Returns:
            Dict with:
                - llm_match: bool (True if LLM judges it as a match)
                - llm_confidence: str ('high', 'medium', 'low')
                - llm_explanation: str (brief explanation)
                - error: Optional[str]
        """
        result = {
            "llm_match": False,
            "llm_confidence": "low",
            "llm_explanation": "",
            "error": None
        }
        
        if not response_text or not expected_answer:
            result["error"] = "Empty text"
            return result
        
        # Build prompt for LLM evaluation
        prompt = f"""You are an expert evaluator. Your task is to determine if a RESPONSE text contains or discusses the same information as an EXPECTED ANSWER.

    EXPECTED ANSWER:
    {expected_answer}

    RESPONSE TEXT:
    {response_text}

    Analyze if the RESPONSE contains the key information from the EXPECTED ANSWER. The response may have additional details, but the core information should match.

    Respond in this EXACT format (nothing else):
    MATCH: [YES/NO]
    CONFIDENCE: [HIGH/MEDIUM/LOW]
    REASON: [One brief sentence explaining why]

    Rules:
    - MATCH=YES if the response contains the expected information (even if phrased differently)
    - MATCH=NO if the response doesn't address the expected answer or gives wrong information
    - CONFIDENCE=HIGH if you're very sure, MEDIUM if somewhat sure, LOW if uncertain"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1}  # Low temperature for consistent evaluation
            )
            
            # Parse response
            llm_output = response.get('message', {}).get('content', '')
            
            # Extract MATCH
            match_line = re.search(r'MATCH:\s*(YES|NO)', llm_output, re.IGNORECASE)
            if match_line:
                result["llm_match"] = match_line.group(1).upper() == "YES"
            
            # Extract CONFIDENCE
            conf_line = re.search(r'CONFIDENCE:\s*(HIGH|MEDIUM|LOW)', llm_output, re.IGNORECASE)
            if conf_line:
                result["llm_confidence"] = conf_line.group(1).lower()
            
            # Extract REASON
            reason_line = re.search(r'REASON:\s*(.+)', llm_output, re.IGNORECASE)
            if reason_line:
                result["llm_explanation"] = reason_line.group(1).strip()[:200]  # Limit length
                
        except Exception as e:
            result["error"] = str(e)
        
        return result


def evaluate_row(row: Dict, llm_evaluator: LLMEvaluator) -> Dict[str, Any]:   
    """
    Evaluate a single row from the results CSV.
    
    Args:
        row: Dictionary containing CSV row data
        llm_evaluator: LLMEvaluator for generative model evaluation
    Returns:
        Dict with new columns to add:
            - baseline_llm_match 
            - baseline_llm_confidence
            - baseline_llm_explanation 
            - togomcp_llm_match 
            - togomcp_llm_confidence
            - togomcp_llm_explanation 
            - full_combined_baseline_found
            - full_combined_togomcp_found
    """
    expected = row.get('expected_answer', '')
    baseline_text = row.get('baseline_text', '')
    togomcp_text = row.get('togomcp_text', '')
    
    baseline_token_found = str(row.get('baseline_has_expected', 'False')).lower() == 'true'
    togomcp_token_found = str(row.get('togomcp_has_expected', 'False')).lower() == 'true'

    baseline_llm = llm_evaluator.evaluate_match(baseline_text, expected)
    togomcp_llm = llm_evaluator.evaluate_match(togomcp_text, expected)
        
    result = {
        "baseline_llm_match": baseline_llm["llm_match"],
        "baseline_llm_confidence": baseline_llm["llm_confidence"],
        "baseline_llm_explanation": baseline_llm["llm_explanation"],
        "togomcp_llm_match": togomcp_llm["llm_match"],
        "togomcp_llm_confidence": togomcp_llm["llm_confidence"],
        "togomcp_llm_explanation": togomcp_llm["llm_explanation"],
        # Combined with LLM: token OR llm
        "full_combined_baseline_found": (
            baseline_token_found or 
            baseline_llm["llm_match"]
        ),
        "full_combined_togomcp_found": (
            togomcp_token_found or 
            togomcp_llm["llm_match"]
        )
        }
    
    return result


def process_csv(
    input_path: Path, 
    output_path: Optional[Path], 
    llm_evaluator: LLMEvaluator,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Process a CSV file and add llm evaluation columns.
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file (None = modify in place)
        llm_evaluator: LLMEvaluator for generative model evaluation
        verbose: Print progress
        
    Returns:
        DataFrame with added columns
    """
    if verbose:
        print(f"\nProcessing: {input_path}")
    
    # Read CSV
    df = pd.read_csv(input_path)
    
    if verbose:
        print(f"  Found {len(df)} rows")
    
    # New columns to add
    new_columns = {
        "baseline_llm_match": [],
        "baseline_llm_confidence": [],
        "baseline_llm_explanation": [],
        "togomcp_llm_match": [],
        "togomcp_llm_confidence": [],
        "togomcp_llm_explanation": [],
        "full_combined_baseline_found": [],
        "full_combined_togomcp_found": []
    }
    
    # Process each row
    for idx, row in df.iterrows():
        if verbose:
            question_id = row.get('question_id', idx)
            print(f"  Evaluating Q{question_id}...", end=" ")
        
        result = evaluate_row(row.to_dict(), llm_evaluator)
        
        for col, value in result.items():
            if col in new_columns:
                new_columns[col].append(value)
        
        if verbose:
            baseline_llm = result.get("baseline_llm_match", False)
            togomcp_llm = result.get("togomcp_llm_match", False)
            msg = f" | LLM: base={baseline_llm}, togo={togomcp_llm}"
            print(msg)
    
    # Add new columns to DataFrame
    for col, values in new_columns.items():
        df[col] = values
    
    # Save to output
    save_path = output_path or input_path
    df.to_csv(save_path, index=False)
    
    if verbose:
        print(f"  Saved to: {save_path}")
    
    return df


def print_summary(df: pd.DataFrame, filename: str):
    """Print evaluation summary statistics."""
    print(f"\n{'='*60}")
    print(f"Summary for {filename}")
    print(f"{'='*60}")
    
    total = len(df)
    
    # LLM metrics
    baseline_llm = df['baseline_llm_match'].sum()
    togomcp_llm = df['togomcp_llm_match'].sum()
        
    print(f"\nLLM-Based Evaluation:")
    print(f"  Baseline LLM matches:   {baseline_llm:3d} ({100*baseline_llm/total:.1f}%)")
    print(f"  TogoMCP LLM matches:    {togomcp_llm:3d} ({100*togomcp_llm/total:.1f}%)")

def main():
    parser = argparse.ArgumentParser(
        description="Add LLM-based evaluation to existing results CSV files"
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        help="Input CSV file(s) to process"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output CSV file (only valid for single input file)"
    )
    parser.add_argument(
        "--llm-model",
        default='llama3.2',
        help="Ollama generative model for LLM evaluation (e.g., llama3.2, mistral)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Don't print summary statistics"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.output and len(args.input_files) > 1:
        print("Error: Cannot use -o with multiple input files")
        sys.exit(1)
    
    # Initialize LLM evaluator
    llm_evaluator = None
    if args.llm_model:
        print(f"  LLM model: {args.llm_model}")
        llm_evaluator = LLMEvaluator(model=args.llm_model)
    else:
        llm_evaluator = LLMEvaluator()
    
    # Process each file
    all_dfs = []
    for input_file in args.input_files:
        input_path = Path(input_file)
        
        if not input_path.exists():
            print(f"Warning: File not found: {input_path}")
            continue
        
        output_path = Path(args.output) if args.output else None
        
        df = process_csv(
            input_path, 
            output_path, 
            llm_evaluator,
            verbose=not args.quiet
        )
        all_dfs.append((input_path.name, df))
    
    # Print summaries
    if not args.no_summary:
        for filename, df in all_dfs:
            print_summary(df, filename)
    
    print(f"\n✓ Processing complete!")


if __name__ == "__main__":
    main()
