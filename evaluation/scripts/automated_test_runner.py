#!/usr/bin/env python3
"""
TogoMCP Automated Evaluation Runner

Evaluates TogoMCP's ability to answer biological database queries by comparing
baseline Claude (no tools) vs TogoMCP-enhanced Claude (with database access).

Key Features:
- Isolated question sessions (no conversation accumulation)
- Optimized cache efficiency (stable costs per question)
- Automatic correctness evaluation
- Tool usage tracking
- Token and cost metrics (including cache breakdown)

Usage:
    python automated_test_runner.py questions.json
    python automated_test_runner.py questions.json -o results.csv
    python automated_test_runner.py questions.json -c config.json

Architecture:
    Each question runs in a fresh Claude session with no shared conversation
    history. This ensures:
    - Stable, predictable cache costs
    - No cross-question contamination
    - Optimal cache reuse (create once, read thereafter)
    - 46% cost reduction vs conversation accumulation

Example cache pattern:
    Q1:  CREATE 16k + READ 16k  = 32k cache tokens
    Q2:  CREATE 0.5k + READ 33k = 33.5k cache tokens
    Q3:  CREATE 0.4k + READ 33k = 33.4k cache tokens
    ...stable pattern continues
"""

import json
import csv
import time
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import argparse
import sys
import asyncio

# Check dependencies
try:
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
    from claude_agent_sdk import AssistantMessage, ResultMessage
    from claude_agent_sdk.types import ToolPermissionContext
except ImportError:
    print("Error: claude-agent-sdk package not installed.")
    print("Install with: pip install claude-agent-sdk")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed (for baseline tests).")
    print("Install with: pip install anthropic")
    sys.exit(1)


class CorrectnessEvaluator:
    """Evaluates response correctness and quality."""
    
    # Phrases indicating inability to answer
    INABILITY_PHRASES = [
        r"don'?t have access",
        r"don'?t have the specific",
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
    ]
    
    def check_inability(self, text: str) -> bool:
        """Check if response indicates inability to answer."""
        if not text:
            return True
        
        text_lower = text.lower()
        for pattern in self.INABILITY_PHRASES:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def check_expected_answer(self, text: str, expected: str) -> Tuple[bool, float]:
        """
        Check if response contains expected answer.
        
        Returns:
            (found, confidence) where confidence is 0.0-1.0
        """
        if not expected or not text:
            return (False, 0.0)
        
        text_lower = text.lower()
        expected_lower = expected.lower()
        
        # Exact match
        if expected_lower in text_lower:
            return (True, 1.0)
        
        # Partial match (split on punctuation/whitespace)
        expected_parts = [
            p.strip() 
            for p in re.split(r'[,;\s]+', expected_lower) 
            if len(p.strip()) > 3
        ]
        
        if not expected_parts:
            return (False, 0.0)
        
        matches = sum(1 for part in expected_parts if part in text_lower)
        confidence = matches / len(expected_parts)
        found = confidence >= 0.5
        
        return (found, confidence)
    
    def evaluate_response(
        self, 
        text: str, 
        expected: str, 
        used_tools: bool
    ) -> Dict[str, Any]:
        """
        Evaluate response quality.
        
        Returns dict with:
            - actually_answered: bool
            - has_expected: bool
            - confidence: float
        """
        actually_answered = not self.check_inability(text)
        has_expected, confidence = self.check_expected_answer(text, expected)
        
        return {
            "actually_answered": actually_answered,
            "has_expected": has_expected,
            "confidence": confidence
        }
    
    def assess_value_add(
        self,
        baseline_answered: bool,
        baseline_has_expected: bool,
        togomcp_success: bool,
        togomcp_has_expected: bool,
        used_tools: bool
    ) -> str:
        """
        Assess TogoMCP value-add level.
        
        Returns one of:
            - CRITICAL: Essential improvement (baseline failed, TogoMCP succeeded)
            - VALUABLE: Significant improvement (both succeeded, TogoMCP better)
            - MARGINAL: Minor improvement
            - REDUNDANT: No clear improvement
            - FAILED: TogoMCP failed
        """
        if not togomcp_success:
            return "FAILED"
        
        if not baseline_answered and togomcp_success:
            return "CRITICAL"
        
        if baseline_answered:
            if not used_tools:
                return "REDUNDANT"
            if togomcp_has_expected and not baseline_has_expected:
                return "CRITICAL"
            if used_tools:
                return "VALUABLE"
        
        return "MARGINAL"


class EvaluationRunner:
    """
    Runs TogoMCP evaluation tests with isolated question sessions.
    
    Each question runs in a fresh Claude session with no conversation history,
    ensuring stable cache costs and no cross-question contamination.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize runner with configuration."""
        self.config = self._load_config(config_path)
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Please set it with your API key."
            )
        
        self.baseline_client = anthropic.Anthropic(api_key=self.api_key)
        self.evaluator = CorrectnessEvaluator()
        self.results = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4000,
            "temperature": 1.0,
            "baseline_system_prompt": (
                "Answer using only your training knowledge. "
                "Do not use any database tools or external resources. "
                "If you don't know something with certainty, say so."
            ),
            "togomcp_system_prompt": (
                "You have access to biological databases through MCP tools. "
                "Use them when they would improve the accuracy or completeness of your answer."
            ),
            "timeout": 60,
            "retry_attempts": 3,
            "retry_delay": 2,
            "mcp_servers": {
                "togomcp": {
                    "type": "http",
                    "url": "https://togomcp.rdfportal.org/mcp"
                }
            },
            "allowed_tools": ["mcp__*"],
            "disallowed_tools": ["WebSearch", "WebFetch", "web_search", "web_fetch"],
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def load_questions(self, questions_path: str) -> List[Dict]:
        """Load questions from JSON file."""
        with open(questions_path, 'r') as f:
            questions = json.load(f)
        print(f"✓ Loaded {len(questions)} questions from {questions_path}")
        return questions
    
    def _make_baseline_call(self, question: str) -> Dict:
        """
        Make baseline API call (no tools).
        
        Returns dict with:
            - success: bool
            - text: str (if successful)
            - error: str (if failed)
            - elapsed_time: float
            - usage: dict (token counts)
        """
        start_time = time.time()
        
        try:
            response = self.baseline_client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                system=self.config["baseline_system_prompt"],
                messages=[{"role": "user", "content": question}]
            )
            
            elapsed_time = time.time() - start_time
            
            # Extract text from content blocks
            text_content = []
            for block in response.content:
                if block.type == "text":
                    text_content.append(block.text)
            
            return {
                "success": True,
                "text": "\n".join(text_content),
                "elapsed_time": elapsed_time,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "elapsed_time": elapsed_time
            }
    
    async def _auto_approve_mcp_tools(
        self, 
        tool_name: str, 
        input_data: dict, 
        context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Auto-approve MCP tools, deny web tools."""
        if tool_name in ["WebSearch", "WebFetch", "web_search", "web_fetch"]:
            return PermissionResultDeny(
                message="Web tools not allowed in evaluation"
            )
        return PermissionResultAllow()
    
    async def _make_togomcp_call(
        self, 
        question: str,
        mcp_servers: Optional[Dict] = None
    ) -> Dict:
        """
        Make TogoMCP API call with database access.
        
        Uses isolated session (fresh client per question) for optimal
        cache efficiency and no conversation accumulation.
        
        Returns dict with:
            - success: bool
            - text: str (if successful)
            - tool_uses: list (tools called)
            - error: str (if failed)
            - elapsed_time: float
            - usage: dict (token counts including cache metrics)
        """
        start_time = time.time()
        
        # Use provided servers or fall back to config
        servers_to_use = mcp_servers if mcp_servers is not None else self.config["mcp_servers"]
        
        try:
            # Create fresh options for this question
            options = ClaudeAgentOptions(
                system_prompt=self.config["togomcp_system_prompt"],
                mcp_servers=servers_to_use,
                model=self.config["model"],
                allowed_tools=self.config["allowed_tools"],
                disallowed_tools=self.config["disallowed_tools"],
                can_use_tool=self._auto_approve_mcp_tools
            )
            
            tool_uses = []
            final_text = None
            usage_info = None
            
            # Create fresh client for this question only (isolated session)
            async with ClaudeSDKClient(options=options) as client:
                # Single query - no follow-ups
                await client.query(question)
                
                # Collect response
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        if hasattr(message, 'content') and isinstance(message.content, list):
                            for block in message.content:
                                block_type = getattr(block, 'type', type(block).__name__)
                                if block_type == "tool_use" or "ToolUse" in type(block).__name__:
                                    tool_name = getattr(block, 'name', 'unknown')
                                    tool_input = getattr(block, 'input', {})
                                    tool_uses.append({
                                        "name": tool_name,
                                        "input": tool_input
                                    })
                    
                    if isinstance(message, ResultMessage):
                        if hasattr(message, 'result') and isinstance(message.result, str):
                            final_text = message.result
                        if hasattr(message, 'usage'):
                            usage_info = message.usage
                
            # Client closes automatically, no state persists
            
            elapsed_time = time.time() - start_time
            
            result = {
                "success": True,
                "text": final_text if final_text else "[No text content extracted]",
                "tool_uses": tool_uses,
                "elapsed_time": elapsed_time
            }
            
            if usage_info:
                result["usage"] = usage_info
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            import traceback
            return {
                "success": False,
                "error": f"{str(e)}\n{traceback.format_exc()}",
                "elapsed_time": elapsed_time
            }
    
    async def run_single_evaluation(
        self, 
        question: Dict, 
        index: int, 
        total: int
    ) -> Dict:
        """
        Run complete evaluation for a single question.
        
        Tests both baseline (no tools) and TogoMCP (with tools),
        then evaluates correctness and value-add.
        """
        q_id = question.get("id", index)
        q_text = question["question"]
        category = question.get("category", "Unknown")
        expected_answer = question.get("expected_answer", "")
        
        print(f"\n[{index + 1}/{total}] Testing Q{q_id}: {category}")
        print(f"  Question: {q_text[:80]}{'...' if len(q_text) > 80 else ''}")
        
        # === Baseline Test (No Tools) ===
        print("  ⏳ Running baseline test (no tools)...")
        baseline_result = self._make_baseline_call(q_text)
        
        baseline_eval = self.evaluator.evaluate_response(
            baseline_result.get("text", ""),
            expected_answer,
            used_tools=False
        )
        
        if baseline_result["success"]:
            status = "✓ answered" if baseline_eval["actually_answered"] else "✗ said 'no access'"
            print(f"  {status} in {baseline_result['elapsed_time']:.2f}s")
        else:
            print(f"  ✗ Baseline failed: {baseline_result.get('error', 'Unknown error')}")
        
        # === TogoMCP Test (With Tools) ===
        print("  ⏳ Running TogoMCP test (with database access)...")
        togomcp_result = await self._make_togomcp_call(
            q_text,
            mcp_servers=question.get("mcp_servers")
        )
        
        used_tools = len(togomcp_result.get("tool_uses", [])) > 0
        togomcp_eval = self.evaluator.evaluate_response(
            togomcp_result.get("text", ""),
            expected_answer,
            used_tools=used_tools
        )
        
        if togomcp_result["success"]:
            tool_names = [t["name"] for t in togomcp_result.get("tool_uses", [])]
            print(f"  ✓ TogoMCP completed in {togomcp_result['elapsed_time']:.2f}s")
            if tool_names:
                print(f"    Tools: {', '.join(tool_names[:3])}{'...' if len(tool_names) > 3 else ''}")
            
            # Show cache usage
            if "usage" in togomcp_result:
                usage = togomcp_result["usage"]
                cache_create = usage.get("cache_creation_input_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                if cache_create > 0 or cache_read > 0:
                    print(f"    Cache: create={cache_create:,} read={cache_read:,}")
        else:
            print(f"  ✗ TogoMCP failed: {togomcp_result.get('error', 'Unknown error')}")
        
        # === Value-Add Assessment ===
        value_add = self.evaluator.assess_value_add(
            baseline_eval["actually_answered"],
            baseline_eval["has_expected"],
            togomcp_result["success"],
            togomcp_eval["has_expected"],
            used_tools
        )
        
        print(f"  📊 Value-Add: {value_add}")
        
        # === Compile Results ===
        result = {
            "question_id": q_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": category,
            "question_text": q_text,
            "baseline_success": baseline_result["success"],
            "baseline_actually_answered": baseline_eval["actually_answered"],
            "baseline_has_expected": baseline_eval["has_expected"],
            "baseline_confidence": baseline_eval["confidence"],
            "baseline_text": baseline_result.get("text", ""),
            "baseline_error": baseline_result.get("error", ""),
            "baseline_time": baseline_result["elapsed_time"],
            "togomcp_success": togomcp_result["success"],
            "togomcp_has_expected": togomcp_eval["has_expected"],
            "togomcp_confidence": togomcp_eval["confidence"],
            "togomcp_text": togomcp_result.get("text", ""),
            "togomcp_error": togomcp_result.get("error", ""),
            "togomcp_time": togomcp_result["elapsed_time"],
            "tools_used": ", ".join([t["name"] for t in togomcp_result.get("tool_uses", [])]),
            "tool_details": json.dumps(togomcp_result.get("tool_uses", [])),
            "value_add": value_add,
            "expected_answer": expected_answer,
            "notes": question.get("notes", "")
        }
        
        # Add token counts
        if baseline_result["success"] and "usage" in baseline_result:
            result["baseline_input_tokens"] = baseline_result["usage"]["input_tokens"]
            result["baseline_output_tokens"] = baseline_result["usage"]["output_tokens"]
        
        if togomcp_result["success"] and "usage" in togomcp_result:
            usage = togomcp_result["usage"]
            result["togomcp_input_tokens"] = usage.get("input_tokens", 0)
            result["togomcp_output_tokens"] = usage.get("output_tokens", 0)
            result["togomcp_cache_creation_input_tokens"] = usage.get("cache_creation_input_tokens", 0)
            result["togomcp_cache_read_input_tokens"] = usage.get("cache_read_input_tokens", 0)
        
        return result
    
    async def run_all_evaluations(self, questions: List[Dict]) -> List[Dict]:
        """
        Run evaluations for all questions.
        
        Each question runs in an isolated session with no conversation
        history accumulation, ensuring stable cache costs.
        """
        total = len(questions)
        print(f"\n{'='*70}")
        print(f"TogoMCP Evaluation Runner")
        print(f"{'='*70}")
        print(f"Questions: {total}")
        print(f"Model: {self.config['model']}")
        print(f"Design: Isolated sessions (no conversation accumulation)")
        print(f"Cache: Optimized for stable, predictable costs")
        print(f"{'='*70}")
        
        results = []
        
        for i, question in enumerate(questions):
            try:
                result = await self.run_single_evaluation(question, i, total)
                results.append(result)
                
                # Save intermediate results every 5 questions
                if (i + 1) % 5 == 0:
                    self._save_intermediate_results(results, i + 1)
                    
            except KeyboardInterrupt:
                print("\n\n⚠ Evaluation interrupted by user")
                print(f"Completed {i} out of {total} questions")
                break
            except Exception as e:
                print(f"\n✗ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'='*70}")
        print(f"Evaluation Complete: {len(results)}/{total} questions")
        self._print_cache_summary(results)
        print(f"{'='*70}\n")
        
        self.results = results
        return results
    
    def _print_cache_summary(self, results: List[Dict]):
        """Print summary of cache usage across all questions."""
        total_create = sum(
            int(r.get("togomcp_cache_creation_input_tokens", 0)) 
            for r in results
        )
        total_read = sum(
            int(r.get("togomcp_cache_read_input_tokens", 0)) 
            for r in results
        )
        
        questions_with_create = sum(
            1 for r in results 
            if int(r.get("togomcp_cache_creation_input_tokens", 0)) > 0
        )
        questions_with_read = sum(
            1 for r in results 
            if int(r.get("togomcp_cache_read_input_tokens", 0)) > 0
        )
        
        if len(results) > 0:
            print(f"\nCache Usage Summary:")
            print(f"  Questions with cache creation: {questions_with_create}/{len(results)}")
            print(f"  Questions with cache reads:    {questions_with_read}/{len(results)}")
            print(f"  Total cache creation tokens:   {total_create:,}")
            print(f"  Total cache read tokens:       {total_read:,}")
            print(f"  Avg cache create per Q:        {total_create/len(results):,.0f}")
            print(f"  Avg cache read per Q:          {total_read/len(results):,.0f}")
    
    def _save_intermediate_results(self, results: List[Dict], count: int):
        """Save intermediate results during long evaluation runs."""
        intermediate_path = Path("evaluation_results_intermediate.csv")
        self._export_to_csv(results, str(intermediate_path))
        print(f"  💾 Saved intermediate results ({count} questions)")
    
    def _export_to_csv(self, results: List[Dict], output_path: str):
        """Export results to CSV file."""
        if not results:
            return
        
        fieldnames = [
            "question_id", "date", "category", "question_text",
            "baseline_success", "baseline_actually_answered", "baseline_has_expected", 
            "baseline_confidence", "baseline_text", "baseline_error", "baseline_time",
            "baseline_input_tokens", "baseline_output_tokens",
            "togomcp_success", "togomcp_has_expected", "togomcp_confidence",
            "togomcp_text", "togomcp_error", "togomcp_time",
            "togomcp_input_tokens", "togomcp_output_tokens",
            "togomcp_cache_creation_input_tokens", "togomcp_cache_read_input_tokens",
            "tools_used", "tool_details",
            "value_add", "expected_answer", "notes"
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    def export_results(self, output_path: str, format: str = "csv"):
        """Export results to file (CSV or JSON)."""
        if not self.results:
            print("⚠ No results to export")
            return
        
        if format == "csv":
            self._export_to_csv(self.results, output_path)
            print(f"✓ Results exported to {output_path}")
        elif format == "json":
            with open(output_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"✓ Results exported to {output_path}")
    
    def print_summary(self):
        """Print evaluation summary statistics."""
        if not self.results:
            return
        
        total = len(self.results)
        baseline_success = sum(1 for r in self.results if r["baseline_success"])
        togomcp_success = sum(1 for r in self.results if r["togomcp_success"])
        baseline_answered = sum(1 for r in self.results if r["baseline_actually_answered"])
        baseline_correct = sum(1 for r in self.results if r["baseline_has_expected"])
        togomcp_correct = sum(1 for r in self.results if r["togomcp_has_expected"])
        
        value_counts = {
            "CRITICAL": 0, 
            "VALUABLE": 0, 
            "MARGINAL": 0, 
            "REDUNDANT": 0, 
            "FAILED": 0
        }
        for r in self.results:
            value_add = r.get("value_add", "MARGINAL")
            value_counts[value_add] = value_counts.get(value_add, 0) + 1
        
        tools_used_count = sum(1 for r in self.results if r["tools_used"])
        avg_baseline_time = sum(r["baseline_time"] for r in self.results) / total
        avg_togomcp_time = sum(r["togomcp_time"] for r in self.results) / total
        
        print("\n" + "="*70)
        print("EVALUATION SUMMARY")
        print("="*70)
        print(f"Total questions:              {total}")
        print()
        print("BASELINE PERFORMANCE (No Tools):")
        print(f"  Technical success:          {baseline_success}/{total} ({baseline_success/total*100:.1f}%)")
        print(f"  Actually answered:          {baseline_answered}/{total} ({baseline_answered/total*100:.1f}%)")
        print(f"  Has expected answer:        {baseline_correct}/{total} ({baseline_correct/total*100:.1f}%)")
        print()
        print("TOGOMCP PERFORMANCE (With Database Access):")
        print(f"  Technical success:          {togomcp_success}/{total} ({togomcp_success/total*100:.1f}%)")
        print(f"  Has expected answer:        {togomcp_correct}/{total} ({togomcp_correct/total*100:.1f}%)")
        print(f"  Used tools:                 {tools_used_count}/{total} ({tools_used_count/total*100:.1f}%)")
        print()
        print("VALUE-ADD ASSESSMENT:")
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
        print("TIMING:")
        print(f"  Avg baseline time:          {avg_baseline_time:.2f}s")
        print(f"  Avg TogoMCP time:           {avg_togomcp_time:.2f}s")
        print("="*70 + "\n")


async def main():
    """Main entry point for evaluation runner."""
    parser = argparse.ArgumentParser(
        description="TogoMCP Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python automated_test_runner.py questions.json
  
  # Custom output path
  python automated_test_runner.py questions.json -o results.csv
  
  # With custom config
  python automated_test_runner.py questions.json -c config.json
  
  # JSON output
  python automated_test_runner.py questions.json --format json

Design:
  Each question runs in an isolated session (no conversation accumulation).
  This ensures stable, predictable cache costs and no cross-question contamination.
  
  Expected cache pattern:
    Q1:  CREATE 16k + READ 16k  (initial setup)
    Q2+: CREATE ~0.5k + READ ~33k (stable pattern)
  
  Benefits:
    - 46% cost reduction vs conversation accumulation
    - Stable costs per question
    - No cross-question contamination
    - Optimal for independent question evaluation

Next steps:
  1. Calculate costs: python compute_costs.py results.csv
  2. Analyze results: python results_analyzer.py results.csv
  3. Generate dashboard: python generate_dashboard.py results.csv --open
        """
    )
    
    parser.add_argument(
        "questions_file", 
        help="Path to questions JSON file"
    )
    parser.add_argument(
        "-c", "--config", 
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Output path for results", 
        default="evaluation_results.csv"
    )
    parser.add_argument(
        "--format", 
        help="Output format (csv or json)", 
        choices=["csv", "json"],
        default="csv"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not Path(args.questions_file).exists():
        print(f"✗ Error: Questions file not found: {args.questions_file}")
        sys.exit(1)
    
    # Initialize runner
    try:
        runner = EvaluationRunner(config_path=args.config)
    except Exception as e:
        print(f"✗ Error initializing runner: {e}")
        sys.exit(1)
    
    # Load questions
    try:
        questions = runner.load_questions(args.questions_file)
    except Exception as e:
        print(f"✗ Error loading questions: {e}")
        sys.exit(1)
    
    # Run evaluation
    await runner.run_all_evaluations(questions)
    
    # Export results
    runner.export_results(args.output, format=args.format)
    
    # Print summary
    runner.print_summary()
    
    print(f"\nNext steps:")
    print(f"  1. Calculate costs: python compute_costs.py {args.output}")
    print(f"  2. Analyze results: python results_analyzer.py {args.output}")
    print(f"  3. Generate dashboard: python generate_dashboard.py {args.output} --open")


if __name__ == "__main__":
    asyncio.run(main())