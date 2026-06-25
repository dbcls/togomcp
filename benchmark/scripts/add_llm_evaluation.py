#!/usr/bin/env python3
"""
Add Opus-Based Evaluation to Test Results

Reads the CSV output from automated_test_runner.py and scores both the baseline
and TogoMCP answers against the ideal answer using four criteria:
    1. Information recall (1-5): Does the answer contain all necessary information?
    2. Information precision (1-5): Does the answer contain only relevant information?
    3. Information repetition (1-5): Does the answer avoid repeating the same information?
    4. Readability (1-5): Is the answer easily readable and fluent?

Each criterion uses a 1-5 scale (1 = very poor, 5 = excellent).
The total score is the sum of all four criteria (4-20).

This is the automated form of the evaluation previously done by hand on the
platform (see results/reevaluation.md). It calls the Claude Messages API with
Claude Opus as the judge and forces a single tool call, so scores come back as
a validated JSON object — no free-text parsing, no Ollama, no local model.

Usage:
    python add_llm_evaluation.py test_results.csv
    python add_llm_evaluation.py test_results.csv -o evaluated_results.csv
    python add_llm_evaluation.py test_results.csv --model claude-opus-4-7
    # Five independent runs (-> results-v1.csv ... results-v5.csv):
    python add_llm_evaluation.py test_results.csv -o results.csv --runs 5

Auth: this uses the `anthropic` Python SDK, which requires an ANTHROPIC_API_KEY
(or ANTHROPIC_AUTH_TOKEN, or an `ant auth login` profile). Note this differs
from automated_test_runner.py, whose bundled Claude Code CLI can also use the
`claude login` keychain — the plain SDK does NOT read that keychain, so an API
key is required here.

Requirements:
    pip install anthropic pandas
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed. Install with: pip install pandas")
    sys.exit(1)

try:
    import anthropic
    from pydantic import BaseModel
except ImportError:
    print("Error: anthropic not installed. Install with: pip install anthropic")
    sys.exit(1)

# Default judge model. claude-opus-4-8 is the current Opus; override with
# --model (e.g. claude-opus-4-7) to reproduce an earlier evaluation batch.
DEFAULT_MODEL = "claude-opus-4-8"

# ---------------------------------------------------------------------------
# Rubric — the judge's system prompt. This is the same rubric used for the
# manual Opus re-evaluation (results/reevaluation.md); structured outputs make
# the "OUTPUT FORMAT" section from the old prompt unnecessary.
# ---------------------------------------------------------------------------
RUBRIC = """You are an expert evaluator of scientific and biomedical answers. \
Evaluate the quality of a given answer by comparing it to an ideal reference answer.

Score the answer on four criteria, each on a 1-5 scale:

## 1. INFORMATION RECALL (1-5)
Does the answer contain all the necessary information from the ideal answer?
- 5 (Excellent): Contains all key information from the ideal answer
- 4 (Good): Contains most key information, minor omissions
- 3 (Adequate): Contains essential information but misses some important details
- 2 (Poor): Missing significant information
- 1 (Very Poor): Missing most or all key information

## 2. INFORMATION PRECISION (1-5)
Does the answer contain only relevant information, without unnecessary content?
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

Be objective and consistent. Judge the answer's content and presentation against \
the ideal answer, and give a brief (1-2 sentence) explanation for your scores."""


class Evaluation(BaseModel):
    """Validated judge output. Scores are also clamped to 1-5 after parsing as
    a belt-and-suspenders guard."""

    recall: int
    precision: int
    repetition: int
    readability: int
    explanation: str


# Forced-tool-use schema. The judge is required to call this tool (and only
# this tool), so the response is always a structured object — portable across
# anthropic SDK versions that predate messages.parse / output_config.
_SCORE_PROP = {"type": "integer", "enum": [1, 2, 3, 4, 5], "description": "Score from 1 (very poor) to 5 (excellent)"}
EVAL_TOOL = {
    "name": "record_evaluation",
    "description": "Record the four 1-5 criterion scores and a brief explanation for the evaluated answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recall": _SCORE_PROP,
            "precision": _SCORE_PROP,
            "repetition": _SCORE_PROP,
            "readability": _SCORE_PROP,
            "explanation": {"type": "string", "description": "1-2 sentence justification for the scores"},
        },
        "required": ["recall", "precision", "repetition", "readability", "explanation"],
    },
}


def _failed_eval(reason: str, explanation: str) -> Dict[str, Any]:
    """Zero-score result used for un-evaluable or failed rows. A total_score of
    0 is the sentinel the summary and downstream analyzers use to exclude a
    row from score statistics."""
    return {
        "recall_score": 0,
        "precision_score": 0,
        "repetition_score": 0,
        "readability_score": 0,
        "total_score": 0,
        "explanation": explanation,
        "error": reason,
    }


class AnswerEvaluator:
    """Scores answer quality with Claude Opus using four criteria."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = anthropic.Anthropic()
        # Fail fast with a clear message instead of scoring every row 0 when no
        # credential is available. The anthropic SDK resolves a key lazily (at
        # call time), so check up front. `ant auth login` users have a key the
        # SDK reads — set ANTHROPIC_API_KEY if you don't.
        has_credential = bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or getattr(self.client, "api_key", None)
            or getattr(self.client, "auth_token", None)
        )
        if not has_credential:
            raise RuntimeError(
                "No Anthropic credential found. Set ANTHROPIC_API_KEY (or "
                "ANTHROPIC_AUTH_TOKEN, or run `ant auth login`). The plain "
                "anthropic SDK does not read the `claude login` keychain."
            )
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        print(f"Initializing Opus evaluator with model: {model}")

    def evaluate_answer(
        self,
        answer: str,
        ideal_answer: str,
        question: str = "",
    ) -> Dict[str, Any]:
        """Evaluate one answer against the ideal answer.

        Returns a dict with recall_score / precision_score / repetition_score /
        readability_score / total_score / explanation / error (error is None on
        success). Scores are 1-5; total_score is their sum (4-20).
        """
        if not answer or not ideal_answer:
            return _failed_eval("Empty answer or ideal answer", "Cannot evaluate empty text")
        if answer.startswith("[ERROR:") or answer.startswith("[SYSTEM ERROR:"):
            return _failed_eval("Answer contains error", "Answer execution failed")

        user_content = (
            "Evaluate the following answer against the ideal reference answer.\n\n"
            f"## Question\n{question or 'Not provided'}\n\n"
            f"## Ideal Answer (reference)\n{ideal_answer}\n\n"
            f"## Answer to Evaluate\n{answer}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": RUBRIC,
                        # The rubric is identical across every call; cache it so
                        # large batches pay for it once. Silently no-ops if the
                        # rubric is below the model's minimum cacheable prefix.
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
                tools=[EVAL_TOOL],
                tool_choice={"type": "tool", "name": "record_evaluation"},
            )

            usage = getattr(response, "usage", None)
            if usage is not None:
                self.total_input_tokens += getattr(usage, "input_tokens", 0) or 0
                self.total_output_tokens += getattr(usage, "output_tokens", 0) or 0

            tool_block = next(
                (b for b in response.content if getattr(b, "type", None) == "tool_use"),
                None,
            )
            if tool_block is None:
                return _failed_eval(
                    "No tool call in response (possible refusal)",
                    "Judge returned no parseable evaluation",
                )

            parsed = Evaluation(**tool_block.input)
            clamp = lambda v: min(5, max(1, int(v)))
            recall = clamp(parsed.recall)
            precision = clamp(parsed.precision)
            repetition = clamp(parsed.repetition)
            readability = clamp(parsed.readability)

            return {
                "recall_score": recall,
                "precision_score": precision,
                "repetition_score": repetition,
                "readability_score": readability,
                "total_score": recall + precision + repetition + readability,
                "explanation": parsed.explanation.strip(),
                "error": None,
            }
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.NotFoundError,
        ):
            # Bad key / no access / wrong --model would fail identically on
            # every row — abort the whole run instead of zeroing all rows.
            raise
        except Exception as e:
            return _failed_eval(str(e), f"Evaluation failed: {e}")


def evaluate_row(
    row: Dict,
    evaluator: AnswerEvaluator,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Evaluate the baseline and TogoMCP answers from one CSV row."""
    question = str(row.get("question", ""))
    ideal_answer = str(row.get("ideal_answer", ""))
    baseline_answer = str(row.get("baseline_answer", ""))
    togomcp_answer = str(row.get("togomcp_answer", ""))

    baseline_success = str(row.get("baseline_success", "True")).lower() == "true"
    togomcp_success = str(row.get("togomcp_success", "True")).lower() == "true"

    if baseline_success and baseline_answer and not baseline_answer.startswith("[ERROR"):
        if verbose:
            print("    Evaluating baseline answer...")
        baseline_eval = evaluator.evaluate_answer(baseline_answer, ideal_answer, question)
    else:
        baseline_eval = _failed_eval("Execution failed", "Answer failed or contains error")

    if togomcp_success and togomcp_answer and not togomcp_answer.startswith("[ERROR"):
        if verbose:
            print("    Evaluating TogoMCP answer...")
        togomcp_eval = evaluator.evaluate_answer(togomcp_answer, ideal_answer, question)
    else:
        togomcp_eval = _failed_eval("Execution failed", "Answer failed or contains error")

    return {
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


def process_csv(
    input_path: Path,
    output_path: Path,
    evaluator: AnswerEvaluator,
    verbose: bool = True,
) -> pd.DataFrame:
    """Read a results CSV, add the 12 evaluation columns, and write it out."""
    if verbose:
        print(f"\nProcessing: {input_path} -> {output_path}")

    df = pd.read_csv(input_path)

    if verbose:
        print(f"  Found {len(df)} rows")
        eval_columns = [c for c in df.columns if "recall" in c or "precision" in c or "total_score" in c]
        if eval_columns:
            print("  Warning: existing evaluation columns will be overwritten")

    new_columns: Dict[str, list] = {
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

    for idx, row in df.iterrows():
        if verbose:
            print(f"  Evaluating {row.get('question_id', idx)}...", end=" ")

        result = evaluate_row(row.to_dict(), evaluator, verbose=False)
        for col, value in result.items():
            new_columns[col].append(value)

        if verbose:
            print(
                f"Baseline: {result['baseline_total_score']}/20, "
                f"TogoMCP: {result['togomcp_total_score']}/20"
            )

    for col, values in new_columns.items():
        df[col] = values

    df.to_csv(output_path, index=False)
    if verbose:
        print(f"  Saved to: {output_path}")
    return df


def print_summary(df: pd.DataFrame, filename: str):
    """Print evaluation summary statistics."""
    print(f"\n{'='*70}")
    print(f"Evaluation Summary: {filename}")
    print(f"{'='*70}")

    total = len(df)

    if "baseline_success" in df.columns:
        baseline_success = (df["baseline_success"] == True).sum()
        togomcp_success = (df["togomcp_success"] == True).sum()
        print("\nExecution Success:")
        print(f"  Baseline:  {baseline_success:3d}/{total} ({100*baseline_success/total:.1f}%)")
        print(f"  TogoMCP:   {togomcp_success:3d}/{total} ({100*togomcp_success/total:.1f}%)")

    baseline_evaluated = df[df["baseline_total_score"] > 0]
    togomcp_evaluated = df[df["togomcp_total_score"] > 0]

    if len(baseline_evaluated) > 0:
        print(f"\nBaseline Scores (n={len(baseline_evaluated)}):")
        for dim in ("recall", "precision", "repetition", "readability"):
            col = f"baseline_{dim}"
            print(f"  {dim.capitalize():12s} {baseline_evaluated[col].mean():.2f} ± {baseline_evaluated[col].std():.2f}")
        print(f"  {'Total':12s} {baseline_evaluated['baseline_total_score'].mean():.2f} ± {baseline_evaluated['baseline_total_score'].std():.2f} (out of 20)")

    if len(togomcp_evaluated) > 0:
        print(f"\nTogoMCP Scores (n={len(togomcp_evaluated)}):")
        for dim in ("recall", "precision", "repetition", "readability"):
            col = f"togomcp_{dim}"
            print(f"  {dim.capitalize():12s} {togomcp_evaluated[col].mean():.2f} ± {togomcp_evaluated[col].std():.2f}")
        print(f"  {'Total':12s} {togomcp_evaluated['togomcp_total_score'].mean():.2f} ± {togomcp_evaluated['togomcp_total_score'].std():.2f} (out of 20)")

    both = df[(df["baseline_total_score"] > 0) & (df["togomcp_total_score"] > 0)]
    if len(both) > 0:
        diff = both["togomcp_total_score"] - both["baseline_total_score"]
        print(f"\nComparative Analysis (n={len(both)} pairs):")
        print(f"  TogoMCP better:  {(diff > 0).sum():3d} ({100*(diff > 0).sum()/len(both):.1f}%)")
        print(f"  Baseline better: {(diff < 0).sum():3d} ({100*(diff < 0).sum()/len(both):.1f}%)")
        print(f"  Tied:            {(diff == 0).sum():3d} ({100*(diff == 0).sum()/len(both):.1f}%)")
        print(f"  Mean difference: {diff.mean():+.2f} (TogoMCP - Baseline)")

    print(f"{'='*70}\n")


def _versioned_paths(base: Path, runs: int) -> List[Path]:
    """For runs>1, derive `<stem>-v1<suffix>` ... `<stem>-vN<suffix>` so the
    output matches the v1..v5 naming used in results/reevaluation.md."""
    if runs <= 1:
        return [base]
    return [base.with_name(f"{base.stem}-v{i}{base.suffix}") for i in range(1, runs + 1)]


def main():
    parser = argparse.ArgumentParser(
        description="Add Opus-based evaluation scores to a test-results CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Evaluation Criteria (each 1-5; total 4-20):
  1. Information Recall      - completeness of necessary information
  2. Information Precision   - relevance of provided information
  3. Information Repetition  - avoidance of redundancy
  4. Readability             - clarity and fluency

Examples:
  python add_llm_evaluation.py test_results.csv
  python add_llm_evaluation.py test_results.csv -o evaluated.csv
  python add_llm_evaluation.py test_results.csv --model claude-opus-4-7
  python add_llm_evaluation.py test_results.csv -o results.csv --runs 5
        """,
    )
    parser.add_argument("input_file", help="Input CSV file from automated_test_runner.py")
    parser.add_argument("-o", "--output", help="Output CSV file (default: overwrite input file)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude judge model (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of independent evaluation passes. >1 writes <output>-v1..-vN.csv",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("--no-summary", action="store_true", help="Don't print summary statistics")

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    if args.runs < 1:
        print("Error: --runs must be >= 1")
        sys.exit(1)

    try:
        evaluator = AnswerEvaluator(model=args.model)
    except Exception as e:
        print(f"Error initializing evaluator: {e}")
        print("Set ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN / `ant auth login`).")
        sys.exit(1)

    base_output = Path(args.output) if args.output else input_path
    output_paths = _versioned_paths(base_output, args.runs)

    start = time.time()
    for run_idx, out_path in enumerate(output_paths, start=1):
        if args.runs > 1 and not args.quiet:
            print(f"\n=== Evaluation run {run_idx}/{args.runs} ===")
        try:
            df = process_csv(input_path, out_path, evaluator, verbose=not args.quiet)
        except Exception as e:
            print(f"Error processing CSV: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        if not args.no_summary:
            print_summary(df, out_path.name)

    elapsed = time.time() - start
    print("✓ Evaluation complete!")
    print(f"  Runs: {args.runs} | Output: {', '.join(p.name for p in output_paths)}")
    print(
        f"  Judge tokens: {evaluator.total_input_tokens:,} in / "
        f"{evaluator.total_output_tokens:,} out | Wall time: {elapsed:.1f}s"
    )


if __name__ == "__main__":
    main()
