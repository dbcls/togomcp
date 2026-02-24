#!/usr/bin/env python3
"""
Add LLM-Based Evaluation to Test Results

This script reads the CSV output from automated_test_runner.py and evaluates
both baseline and TogoMCP answers against the ideal answer using four criteria:
    1. Information recall (1-5): Does the answer contain all necessary information?
    2. Information precision (1-5): Does the answer contain only relevant information?
    3. Information repetition (1-5): Does the answer avoid repeating the same information?
    4. Readability (1-5): Is the answer easily readable and fluent?

Each criterion uses a 1-5 scale (1 = very poor, 5 = excellent).
The total score is the sum of all four criteria (4-20).

Usage:
    python add_llm_evaluation.py test_results.csv
    python add_llm_evaluation.py test_results.csv -o evaluated_results.csv
    python add_llm_evaluation.py test_results.csv --llm-model llama3.2

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
    print("Error: ollama not installed. Install with: pip install ollama")
    sys.exit(1)

DEFAULT_MODEL = "llama3.2"

class AnswerEvaluator:
    """Evaluates answer quality using LLM with four criteria."""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        """
        Initialize answer evaluator.
        
        Args:
            model: Ollama model name for evaluation
        """
        self.model = model
        print(f"Initializing LLM evaluator with model: {model}")
    
    def evaluate_answer(
        self, 
        answer: str, 
        ideal_answer: str,
        question: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate an answer against the ideal answer using four criteria.
        
        Args:
            answer: The answer to evaluate
            ideal_answer: The ideal/reference answer
            question: The original question (for context)
            
        Returns:
            Dict with:
                - recall_score: int (1-5)
                - precision_score: int (1-5)
                - repetition_score: int (1-5)
                - readability_score: int (1-5)
                - total_score: int (4-20)
                - explanation: str (brief explanation)
                - error: Optional[str]
        """
        result = {
            "recall_score": 1,
            "precision_score": 1,
            "repetition_score": 1,
            "readability_score": 1,
            "total_score": 4,
            "explanation": "",
            "error": None
        }
        
        # Handle empty or error answers
        if not answer or not ideal_answer:
            result["error"] = "Empty answer or ideal answer"
            result["explanation"] = "Cannot evaluate empty text"
            return result
        
        if answer.startswith("[ERROR:") or answer.startswith("[SYSTEM ERROR:"):
            result["error"] = "Answer contains error"
            result["explanation"] = "Answer execution failed"
            return result
        
        # Build evaluation prompt
        prompt = f"""You are an expert evaluator of scientific and biomedical answers. Your task is to evaluate the quality of a given answer by comparing it to an ideal reference answer.

# EVALUATION CRITERIA

Evaluate the answer on four criteria using a 1-5 scale:

## 1. INFORMATION RECALL (1-5)
Does the answer contain all the necessary information from the ideal answer?
- 5 (Excellent): Contains all key information from ideal answer
- 4 (Good): Contains most key information, minor omissions
- 3 (Adequate): Contains essential information but misses some important details
- 2 (Poor): Missing significant information
- 1 (Very Poor): Missing most or all key information

## 2. INFORMATION PRECISION (1-5)
Does the answer contain only relevant information, without unnecessary or irrelevant content?
- 5 (Excellent): All information is relevant and on-topic
- 4 (Good): Mostly relevant with minimal unnecessary content
- 3 (Adequate): Some irrelevant or tangential information
- 2 (Poor): Significant amount of irrelevant content
- 1 (Very Poor): Mostly irrelevant or off-topic information

## 3. INFORMATION REPETITION (1-5)
Does the answer avoid repeating the same information multiple times?
- 5 (Excellent): No repetition, each point made once clearly
- 4 (Good): Minimal repetition, does not detract from answer
- 3 (Adequate): Some repetition that could be condensed
- 2 (Poor): Significant repetition that affects clarity
- 1 (Very Poor): Excessive repetition throughout

## 4. READABILITY (1-5)
Is the answer easily readable, fluent, and well-structured?
- 5 (Excellent): Clear, fluent, well-organized prose
- 4 (Good): Generally readable with good flow
- 3 (Adequate): Understandable but somewhat awkward or poorly structured
- 2 (Poor): Difficult to read, poor grammar or structure
- 1 (Very Poor): Nearly unreadable, very poor language quality

# OUTPUT FORMAT

You must respond using this exact format:

RECALL: [score 1-5]
PRECISION: [score 1-5]
REPETITION: [score 1-5]
READABILITY: [score 1-5]
TOTAL: [sum of all four scores, 4-20]
EXPLANATION: [Brief 1-2 sentence summary of the evaluation]

# INPUT DATA

## Question (for context)
{question if question else "Not provided"}

## Ideal Answer (Reference)
{ideal_answer}

## Answer to Evaluate
{answer}

# EVALUATION INSTRUCTIONS

1. Read the ideal answer carefully to understand what information should be present
2. Compare the answer to evaluate against the ideal answer
3. Assign scores for each of the four criteria
4. Calculate the total score (sum of all four)
5. Provide a brief explanation

Be objective and consistent in your scoring. Focus on the quality of the answer content and presentation.
"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1}  # Low temperature for consistent evaluation
            )
            
            # Parse response
            llm_output = response.get('message', {}).get('content', '')
            
            # Extract scores using regex
            recall_match = re.search(r'RECALL:\s*(\d+)', llm_output, re.IGNORECASE)
            precision_match = re.search(r'PRECISION:\s*(\d+)', llm_output, re.IGNORECASE)
            repetition_match = re.search(r'REPETITION:\s*(\d+)', llm_output, re.IGNORECASE)
            readability_match = re.search(r'READABILITY:\s*(\d+)', llm_output, re.IGNORECASE)
            total_match = re.search(r'TOTAL:\s*(\d+)', llm_output, re.IGNORECASE)
            explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?:\n|$)', llm_output, re.IGNORECASE | re.DOTALL)
            
            if recall_match:
                result["recall_score"] = min(5, max(1, int(recall_match.group(1))))
            if precision_match:
                result["precision_score"] = min(5, max(1, int(precision_match.group(1))))
            if repetition_match:
                result["repetition_score"] = min(5, max(1, int(repetition_match.group(1))))
            if readability_match:
                result["readability_score"] = min(5, max(1, int(readability_match.group(1))))
            
            # Calculate total (verify against LLM's calculation)
            calculated_total = (
                result["recall_score"] + 
                result["precision_score"] + 
                result["repetition_score"] + 
                result["readability_score"]
            )
            
            if total_match:
                llm_total = int(total_match.group(1))
                # Use calculated total if LLM's total doesn't match
                result["total_score"] = calculated_total
            else:
                result["total_score"] = calculated_total
            
            if explanation_match:
                result["explanation"] = explanation_match.group(1).strip()  # Limit length
                
        except Exception as e:
            result["error"] = str(e)
            result["explanation"] = f"Evaluation failed: {str(e)}"
        
        return result


def evaluate_row(
    row: Dict, 
    evaluator: AnswerEvaluator,
    verbose: bool = False
) -> Dict[str, Any]:   
    """
    Evaluate a single row from the results CSV.
    
    Args:
        row: Dictionary containing CSV row data
        evaluator: AnswerEvaluator instance
        verbose: Print detailed progress
        
    Returns:
        Dict with new columns to add for both baseline and TogoMCP
    """
    question = str(row.get('question', ''))
    ideal_answer = str(row.get('ideal_answer', ''))
    baseline_answer = str(row.get('baseline_answer', ''))
    togomcp_answer = str(row.get('togomcp_answer', ''))
    
    baseline_success = str(row.get('baseline_success', 'True')).lower() == 'true'
    togomcp_success = str(row.get('togomcp_success', 'True')).lower() == 'true'
    
    # Evaluate baseline answer
    if baseline_success and baseline_answer and not baseline_answer.startswith('[ERROR'):
        if verbose:
            print("    Evaluating baseline answer...")
        baseline_eval = evaluator.evaluate_answer(baseline_answer, ideal_answer, question)
    else:
        baseline_eval = {
            "recall_score": 0,
            "precision_score": 0,
            "repetition_score": 0,
            "readability_score": 0,
            "total_score": 0,
            "explanation": "Answer failed or contains error",
            "error": "Execution failed"
        }
    
    # Evaluate TogoMCP answer
    if togomcp_success and togomcp_answer and not togomcp_answer.startswith('[ERROR'):
        if verbose:
            print("    Evaluating TogoMCP answer...")
        togomcp_eval = evaluator.evaluate_answer(togomcp_answer, ideal_answer, question)
    else:
        togomcp_eval = {
            "recall_score": 0,
            "precision_score": 0,
            "repetition_score": 0,
            "readability_score": 0,
            "total_score": 0,
            "explanation": "Answer failed or contains error",
            "error": "Execution failed"
        }
    
    result = {
        # Baseline scores
        "baseline_recall": baseline_eval["recall_score"],
        "baseline_precision": baseline_eval["precision_score"],
        "baseline_repetition": baseline_eval["repetition_score"],
        "baseline_readability": baseline_eval["readability_score"],
        "baseline_total_score": baseline_eval["total_score"],
        "baseline_evaluation_explanation": baseline_eval["explanation"],
        
        # TogoMCP scores
        "togomcp_recall": togomcp_eval["recall_score"],
        "togomcp_precision": togomcp_eval["precision_score"],
        "togomcp_repetition": togomcp_eval["repetition_score"],
        "togomcp_readability": togomcp_eval["readability_score"],
        "togomcp_total_score": togomcp_eval["total_score"],
        "togomcp_evaluation_explanation": togomcp_eval["explanation"],
    }
    
    return result


def process_csv(
    input_path: Path, 
    output_path: Optional[Path], 
    evaluator: AnswerEvaluator,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Process a CSV file and add evaluation columns.
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file (None = modify in place)
        evaluator: AnswerEvaluator instance
        verbose: Print progress
        
    Returns:
        DataFrame with added evaluation columns
    """
    if verbose:
        print(f"\nProcessing: {input_path}")
    
    # Read CSV
    df = pd.read_csv(input_path)
    
    if verbose:
        print(f"  Found {len(df)} rows")
        
        # Check for existing evaluation columns
        eval_columns = [col for col in df.columns if 'recall' in col or 'precision' in col or 'total_score' in col]
        if eval_columns:
            print(f"  Warning: Found existing evaluation columns - they will be overwritten")
    
    # New columns to add
    new_columns = {
        "baseline_recall": [],
        "baseline_precision": [],
        "baseline_repetition": [],
        "baseline_readability": [],
        "baseline_total_score": [],
        "baseline_evaluation_explanation": [],
        "togomcp_recall": [],
        "togomcp_precision": [],
        "togomcp_repetition": [],
        "togomcp_readability": [],
        "togomcp_total_score": [],
        "togomcp_evaluation_explanation": [],
    }
    
    # Process each row
    for idx, row in df.iterrows():
        if verbose:
            question_id = row.get('question_id', idx)
            print(f"  Evaluating {question_id}...", end=" ")
        
        result = evaluate_row(row.to_dict(), evaluator, verbose=False)
        
        for col, value in result.items():
            if col in new_columns:
                new_columns[col].append(value)
        
        if verbose:
            baseline_total = result.get("baseline_total_score", 0)
            togomcp_total = result.get("togomcp_total_score", 0)
            print(f"Baseline: {baseline_total}/20, TogoMCP: {togomcp_total}/20")
    
    # Add new columns to DataFrame
    for col, values in new_columns.items():
        df[col] = values
    
    # Save to output
    save_path = output_path or input_path
    df.to_csv(save_path, index=False)
    
    if verbose:
        print(f"\n  ✓ Saved to: {save_path}")
    
    return df


def print_summary(df: pd.DataFrame, filename: str):
    """Print evaluation summary statistics."""
    print(f"\n{'='*70}")
    print(f"Evaluation Summary: {filename}")
    print(f"{'='*70}")
    
    total = len(df)
    
    # Success statistics
    if 'baseline_success' in df.columns:
        baseline_success = (df['baseline_success'] == True).sum()
        togomcp_success = (df['togomcp_success'] == True).sum()
        print(f"\nExecution Success:")
        print(f"  Baseline:  {baseline_success:3d}/{total} ({100*baseline_success/total:.1f}%)")
        print(f"  TogoMCP:   {togomcp_success:3d}/{total} ({100*togomcp_success/total:.1f}%)")
    
    # Score statistics (only for successful executions with score > 0)
    baseline_evaluated = df[df['baseline_total_score'] > 0]
    togomcp_evaluated = df[df['togomcp_total_score'] > 0]
    
    if len(baseline_evaluated) > 0:
        print(f"\nBaseline Scores (n={len(baseline_evaluated)}):")
        print(f"  Recall:      {baseline_evaluated['baseline_recall'].mean():.2f} ± {baseline_evaluated['baseline_recall'].std():.2f}")
        print(f"  Precision:   {baseline_evaluated['baseline_precision'].mean():.2f} ± {baseline_evaluated['baseline_precision'].std():.2f}")
        print(f"  Repetition:  {baseline_evaluated['baseline_repetition'].mean():.2f} ± {baseline_evaluated['baseline_repetition'].std():.2f}")
        print(f"  Readability: {baseline_evaluated['baseline_readability'].mean():.2f} ± {baseline_evaluated['baseline_readability'].std():.2f}")
        print(f"  Total:       {baseline_evaluated['baseline_total_score'].mean():.2f} ± {baseline_evaluated['baseline_total_score'].std():.2f} (out of 20)")
    
    if len(togomcp_evaluated) > 0:
        print(f"\nTogoMCP Scores (n={len(togomcp_evaluated)}):")
        print(f"  Recall:      {togomcp_evaluated['togomcp_recall'].mean():.2f} ± {togomcp_evaluated['togomcp_recall'].std():.2f}")
        print(f"  Precision:   {togomcp_evaluated['togomcp_precision'].mean():.2f} ± {togomcp_evaluated['togomcp_precision'].std():.2f}")
        print(f"  Repetition:  {togomcp_evaluated['togomcp_repetition'].mean():.2f} ± {togomcp_evaluated['togomcp_repetition'].std():.2f}")
        print(f"  Readability: {togomcp_evaluated['togomcp_readability'].mean():.2f} ± {togomcp_evaluated['togomcp_readability'].std():.2f}")
        print(f"  Total:       {togomcp_evaluated['togomcp_total_score'].mean():.2f} ± {togomcp_evaluated['togomcp_total_score'].std():.2f} (out of 20)")
    
    # Comparison (for successfully evaluated pairs)
    both_evaluated = df[(df['baseline_total_score'] > 0) & (df['togomcp_total_score'] > 0)]
    if len(both_evaluated) > 0:
        print(f"\nComparative Analysis (n={len(both_evaluated)} pairs):")
        score_diff = both_evaluated['togomcp_total_score'] - both_evaluated['baseline_total_score']
        togomcp_better = (score_diff > 0).sum()
        baseline_better = (score_diff < 0).sum()
        tied = (score_diff == 0).sum()
        
        print(f"  TogoMCP better:  {togomcp_better:3d} ({100*togomcp_better/len(both_evaluated):.1f}%)")
        print(f"  Baseline better: {baseline_better:3d} ({100*baseline_better/len(both_evaluated):.1f}%)")
        print(f"  Tied:            {tied:3d} ({100*tied/len(both_evaluated):.1f}%)")
        print(f"  Mean difference: {score_diff.mean():+.2f} (TogoMCP - Baseline)")
    
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Add LLM-based evaluation scores to test results CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Evaluation Criteria:
  1. Information Recall (1-5): Completeness of necessary information
  2. Information Precision (1-5): Relevance of provided information
  3. Information Repetition (1-5): Avoidance of redundancy
  4. Readability (1-5): Clarity and fluency
  Total Score: Sum of all four criteria (4-20)

Examples:
  python add_llm_evaluation.py test_results.csv
  python add_llm_evaluation.py test_results.csv -o evaluated.csv
  python add_llm_evaluation.py test_results.csv --llm-model llama3.2
        """
    )
    parser.add_argument(
        "input_file",
        help="Input CSV file from automated_test_runner.py"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output CSV file (default: overwrite input file)"
    )
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_MODEL,
        help=f"Ollama model for evaluation (default: {DEFAULT_MODEL})"
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
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    # Initialize evaluator
    try:
        evaluator = AnswerEvaluator(model=args.llm_model)
    except Exception as e:
        print(f"Error initializing evaluator: {e}")
        print("Make sure Ollama is running and the model is available.")
        print(f"Try: ollama pull {args.llm_model}")
        sys.exit(1)
    
    # Process file
    output_path = Path(args.output) if args.output else None
    
    try:
        df = process_csv(
            input_path, 
            output_path, 
            evaluator,
            verbose=not args.quiet
        )
    except Exception as e:
        print(f"Error processing CSV: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Print summary
    if not args.no_summary:
        print_summary(df, input_path.name)
    
    print(f"✓ Evaluation complete!")
    if output_path:
        print(f"  Results saved to: {output_path}")
    else:
        print(f"  Results saved to: {input_path}")


if __name__ == "__main__":
    main()
