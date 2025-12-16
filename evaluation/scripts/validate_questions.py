#!/usr/bin/env python3
"""
TogoMCP Question Validator

Validates question files before running evaluations to:
- Catch JSON format errors
- Verify required fields
- Check category balance
- Estimate API costs
- Suggest improvements

Usage:
    python validate_questions.py questions.json
    python validate_questions.py questions.json --strict
    python validate_questions.py questions.json --estimate-cost
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import argparse


class QuestionValidator:
    """Validates TogoMCP evaluation question files."""
    
    VALID_CATEGORIES = {
        "Precision",
        "Completeness",
        "Integration",
        "Currency",
        "Specificity",
        "Structured Query"
    }
    
    REQUIRED_FIELDS = {"question"}
    RECOMMENDED_FIELDS = {"id", "category", "expected_answer", "notes"}
    
    # Token estimates (rough averages)
    AVG_QUESTION_TOKENS = 50
    AVG_BASELINE_RESPONSE_TOKENS = 100
    AVG_TOGOMCP_RESPONSE_TOKENS = 150
    
    # Pricing (as of Dec 2024 for Claude Sonnet 4)
    PRICE_PER_INPUT_TOKEN = 3.00 / 1_000_000  # $3 per million
    PRICE_PER_OUTPUT_TOKEN = 15.00 / 1_000_000  # $15 per million
    
    def __init__(self, filepath: str, strict: bool = False):
        """Initialize validator."""
        self.filepath = Path(filepath)
        self.strict = strict
        self.questions = []
        self.errors = []
        self.warnings = []
        self.info = []
        
    def validate(self) -> bool:
        """Run all validation checks. Returns True if valid."""
        # Check file exists
        if not self.filepath.exists():
            self.errors.append(f"File not found: {self.filepath}")
            return False
        
        # Load and parse JSON
        if not self._load_json():
            return False
        
        # Run validation checks
        self._check_structure()
        self._check_fields()
        self._check_categories()
        self._check_duplicates()
        self._check_question_quality()
        
        # Strict mode: warnings become errors
        if self.strict and self.warnings:
            self.errors.extend(self.warnings)
            self.warnings = []
        
        return len(self.errors) == 0
    
    def _load_json(self) -> bool:
        """Load and parse JSON file."""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                self.errors.append("JSON must be an array of questions")
                return False
            
            if len(data) == 0:
                self.errors.append("Question array is empty")
                return False
            
            self.questions = data
            self.info.append(f"Loaded {len(self.questions)} questions")
            return True
            
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return False
    
    def _check_structure(self):
        """Check that each question is a valid object."""
        for i, q in enumerate(self.questions, 1):
            if not isinstance(q, dict):
                self.errors.append(f"Question {i}: Must be an object, got {type(q).__name__}")
    
    def _check_fields(self):
        """Check required and recommended fields."""
        for i, q in enumerate(self.questions, 1):
            if not isinstance(q, dict):
                continue
            
            # Check required fields
            for field in self.REQUIRED_FIELDS:
                if field not in q or not q[field]:
                    self.errors.append(f"Question {i}: Missing required field '{field}'")
            
            # Check recommended fields
            missing_recommended = self.RECOMMENDED_FIELDS - set(q.keys())
            if missing_recommended:
                self.warnings.append(
                    f"Question {i}: Missing recommended fields: {', '.join(missing_recommended)}"
                )
            
            # Check field types
            if "question" in q and not isinstance(q["question"], str):
                self.errors.append(f"Question {i}: 'question' must be a string")
            
            if "category" in q and q["category"] not in self.VALID_CATEGORIES:
                self.warnings.append(
                    f"Question {i}: Unknown category '{q['category']}'. "
                    f"Valid: {', '.join(sorted(self.VALID_CATEGORIES))}"
                )
    
    def _check_categories(self):
        """Check category distribution."""
        categories = [q.get("category") for q in self.questions if q.get("category")]
        
        if not categories:
            self.warnings.append("No categories specified for any questions")
            return
        
        category_counts = Counter(categories)
        
        # Check for missing categories
        missing = self.VALID_CATEGORIES - set(categories)
        if missing:
            self.info.append(f"Missing categories: {', '.join(sorted(missing))}")
        
        # Check for underrepresented categories (< 3 questions)
        sparse = [cat for cat, count in category_counts.items() if count < 3]
        if sparse:
            self.warnings.append(
                f"Categories with <3 questions (recommend 3-5): {', '.join(sparse)}"
            )
        
        # Show distribution
        self.info.append("Category distribution:")
        for cat in sorted(self.VALID_CATEGORIES):
            count = category_counts.get(cat, 0)
            status = "✓" if count >= 3 else "⚠" if count > 0 else "✗"
            self.info.append(f"  {status} {cat}: {count}")
    
    def _check_duplicates(self):
        """Check for duplicate questions."""
        seen = {}
        for i, q in enumerate(self.questions, 1):
            if not isinstance(q, dict) or "question" not in q:
                continue
            
            question_text = q["question"].strip().lower()
            
            if question_text in seen:
                self.warnings.append(
                    f"Question {i} appears to be duplicate of Question {seen[question_text]}"
                )
            else:
                seen[question_text] = i
    
    def _check_question_quality(self):
        """Check question quality indicators."""
        for i, q in enumerate(self.questions, 1):
            if not isinstance(q, dict) or "question" not in q:
                continue
            
            text = q["question"]
            
            # Check length
            if len(text) < 10:
                self.warnings.append(f"Question {i}: Very short ({len(text)} chars)")
            elif len(text) > 500:
                self.warnings.append(f"Question {i}: Very long ({len(text)} chars)")
            
            # Check for common issues
            if not text.strip().endswith("?"):
                self.info.append(f"Question {i}: Doesn't end with '?' (may be a statement)")
            
            # Check for vague language
            vague_terms = ["thing", "stuff", "something", "anything"]
            text_lower = text.lower()
            for term in vague_terms:
                if term in text_lower:
                    self.warnings.append(f"Question {i}: Contains vague term '{term}'")
                    break
    
    def estimate_cost(self) -> Dict:
        """Estimate API costs for running these questions."""
        num_questions = len(self.questions)
        
        # Baseline test: input (system + question) + output
        baseline_input = num_questions * (200 + self.AVG_QUESTION_TOKENS)  # 200 for system prompt
        baseline_output = num_questions * self.AVG_BASELINE_RESPONSE_TOKENS
        
        # TogoMCP test: input (system + question) + output (longer, with tools)
        togomcp_input = num_questions * (200 + self.AVG_QUESTION_TOKENS)
        togomcp_output = num_questions * self.AVG_TOGOMCP_RESPONSE_TOKENS
        
        total_input = baseline_input + togomcp_input
        total_output = baseline_output + togomcp_output
        
        input_cost = total_input * self.PRICE_PER_INPUT_TOKEN
        output_cost = total_output * self.PRICE_PER_OUTPUT_TOKEN
        total_cost = input_cost + output_cost
        
        return {
            "num_questions": num_questions,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "cost_per_question": total_cost / num_questions if num_questions > 0 else 0
        }
    
    def print_report(self, show_cost: bool = False):
        """Print validation report."""
        print("=" * 70)
        print("QUESTION VALIDATOR REPORT")
        print("=" * 70)
        print(f"File: {self.filepath}")
        print()
        
        # Errors
        if self.errors:
            print("❌ ERRORS")
            print("-" * 70)
            for error in self.errors:
                print(f"  • {error}")
            print()
        
        # Warnings
        if self.warnings:
            print("⚠️  WARNINGS")
            print("-" * 70)
            for warning in self.warnings:
                print(f"  • {warning}")
            print()
        
        # Info
        if self.info:
            print("ℹ️  INFORMATION")
            print("-" * 70)
            for info in self.info:
                print(f"  {info}")
            print()
        
        # Cost estimate
        if show_cost and len(self.questions) > 0:
            cost = self.estimate_cost()
            print("💰 COST ESTIMATE")
            print("-" * 70)
            print(f"  Questions:           {cost['num_questions']}")
            print(f"  Estimated tokens:    ~{cost['total_tokens']:,}")
            print(f"  Estimated cost:      ${cost['total_cost']:.4f}")
            print(f"  Cost per question:   ${cost['cost_per_question']:.4f}")
            print()
            print("  Note: This is a rough estimate. Actual costs may vary.")
            print()
        
        # Summary
        print("=" * 70)
        if self.errors:
            print("❌ VALIDATION FAILED")
            print(f"   Fix {len(self.errors)} error(s) before running evaluation")
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print(f"   Consider addressing {len(self.warnings)} warning(s)")
        else:
            print("✅ VALIDATION PASSED")
            print("   Questions file is ready for evaluation")
        print("=" * 70)
        print()
    
    def get_recommendations(self) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Category balance
        categories = [q.get("category") for q in self.questions if q.get("category")]
        category_counts = Counter(categories)
        
        sparse = [cat for cat, count in category_counts.items() if count < 3]
        if sparse:
            recommendations.append(
                f"Add 2-3 more questions to these categories: {', '.join(sparse)}"
            )
        
        missing = self.VALID_CATEGORIES - set(categories)
        if missing:
            recommendations.append(
                f"Consider adding questions for: {', '.join(sorted(missing))}"
            )
        
        # Total count
        if len(self.questions) < 10:
            recommendations.append(
                f"Current: {len(self.questions)} questions. Recommend 10-20 for meaningful evaluation."
            )
        
        # Missing fields
        missing_ids = sum(1 for q in self.questions if not q.get("id"))
        if missing_ids > 0:
            recommendations.append(
                f"Add IDs to {missing_ids} questions for easier tracking"
            )
        
        missing_expected = sum(1 for q in self.questions if not q.get("expected_answer"))
        if missing_expected > 0:
            recommendations.append(
                f"Add expected answers to {missing_expected} questions for verification"
            )
        
        return recommendations


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate TogoMCP evaluation question files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("questions_file", help="Path to questions JSON file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--estimate-cost",
        action="store_true",
        help="Show estimated API costs"
    )
    parser.add_argument(
        "--recommendations",
        action="store_true",
        help="Show improvement recommendations"
    )
    
    args = parser.parse_args()
    
    # Validate
    validator = QuestionValidator(args.questions_file, strict=args.strict)
    is_valid = validator.validate()
    
    # Print report
    validator.print_report(show_cost=args.estimate_cost)
    
    # Show recommendations
    if args.recommendations:
        recommendations = validator.get_recommendations()
        if recommendations:
            print("💡 RECOMMENDATIONS")
            print("-" * 70)
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
            print()
    
    # Exit code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
