#!/usr/bin/env python3
"""
TogoMCP Automated Test Runner (Revised for YAML)

Collects answers from baseline Claude (no tools) and TogoMCP-enhanced Claude
(with database access) for biological questions. Does NOT evaluate answers -
that is done by a separate evaluation script.

Key Features:
- Handles revised BioASQ-style question format in YAML
- Isolated question sessions (no conversation accumulation)
- Prompts agents for complete one-paragraph final answers
- Outputs simple CSV with questions and answers
- Accepts multiple question files as command-line arguments
- No evaluation performed (handled separately)

Usage:
    python automated_test_runner.py question_001.yaml question_002.yaml
    python automated_test_runner.py questions/*.yaml -o results.csv
    python automated_test_runner.py question_*.yaml -c config.yaml

Output CSV columns:
    - question_id: Unique question identifier
    - question: The question text (body)
    - ideal_answer: Expected ideal answer
    - baseline_success: Whether baseline query executed successfully (True/False)
    - baseline_answer: Answer from baseline Claude (no tools)
    - togomcp_success: Whether TogoMCP query executed successfully (True/False)
    - togomcp_answer: Answer from TogoMCP Claude (with tools)
    - tools_used: Comma-separated list of tools used by TogoMCP
"""

import csv
import time
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import sys
import asyncio

# Check dependencies
try:
    import yaml
except ImportError:
    print("Error: PyYAML package not installed.")
    print("Install with: pip install pyyaml")
    sys.exit(1)

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

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TestRunner:
    """
    Runs tests to collect answers from baseline and TogoMCP agents.
    
    Each question runs in a fresh Claude session with no conversation history.
    No evaluation is performed - only answer collection.
    """
    
    # Prompt to encourage complete, final answers following BioASQ ideal answer principles
    FINAL_ANSWER_INSTRUCTION = """

Provide your answer as a single, well-formed paragraph that directly answers the question. Follow these guidelines:

1. COMPLETENESS: Include all necessary information to fully answer the question
2. PRECISION: Include only information directly relevant to answering the question
3. NO REPETITION: State each piece of information only once; avoid redundant phrasing
4. READABILITY: Write in clear, fluent prose with logical flow between sentences
5. DIRECT STYLE: State facts directly without meta-references like "According to research," "Studies show," or "The literature indicates"

Simply provide the factual answer as you would write an encyclopedia entry."""
    
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
        self.results = []
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from YAML or JSON file, or use defaults."""
        default_config = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4000,
            "temperature": 1.0,
            "baseline_system_prompt": (
                "You are an expert assistant answering biological and biomedical questions. "
                "Answer using only your training knowledge. "
                "Do not use any database tools or external resources. "
                "\n\n"
                "Write answers that are:\n"
                "- COMPLETE: Include all necessary information\n"
                "- PRECISE: Include only relevant information\n"
                "- NON-REDUNDANT: Avoid repeating the same information\n"
                "- READABLE: Use clear, fluent scientific prose\n"
                "- DIRECT: State facts without meta-references (no 'research shows', 'according to', etc.)\n"
                "\n"
                "If you don't know something with certainty, state this clearly and concisely."
            ),
            "togomcp_system_prompt": (
                "You are an expert assistant answering biological and biomedical questions. "
                "You have access to biological databases through MCP tools. "
                "Use them when they would improve the accuracy or completeness of your answer. "
                "\n\n"
                "Base your answers on retrieved data and write them to be:\n"
                "- COMPLETE: Include all necessary information from the databases\n"
                "- PRECISE: Include only relevant information that answers the question\n"
                "- NON-REDUNDANT: Synthesize information; don't repeat the same facts\n"
                "- READABLE: Use clear, fluent scientific prose with logical flow\n"
                "- DIRECT: State facts from databases without meta-references (no 'according to', 'the database shows', etc.)\n"
                "\n"
                "Simply state what you found as factual information, as you would write an encyclopedia entry."
            ),
            "timeout": 120,
            "retry_attempts": 3,
            "retry_delay": 2,
            "max_retry_delay": 30,
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
                # Try YAML first, fall back to JSON
                try:
                    user_config = yaml.safe_load(f)
                except yaml.YAMLError:
                    # Try JSON if YAML fails
                    f.seek(0)
                    import json
                    user_config = json.load(f)
                
                # Ensure user_config is a dict before updating
                if isinstance(user_config, dict):
                    default_config.update(user_config)
                else:
                    logger.warning(f"Config file {config_path} did not contain a dict, ignoring")
        
        return default_config
    
    def load_questions(self, question_files: List[str]) -> List[Dict]:
        """
        Load questions from multiple YAML files.
        
        Each file should contain a single question object in YAML format.
        Also supports legacy JSON format for backward compatibility.
        """
        all_questions = []
        
        for file_path in question_files:
            if not Path(file_path).exists():
                logger.warning(f"Question file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    # Try YAML first
                    try:
                        data = yaml.safe_load(f)
                    except yaml.YAMLError:
                        # Fall back to JSON for backward compatibility
                        f.seek(0)
                        import json
                        data = json.load(f)
                
                # Handle both single question and array of questions
                if isinstance(data, list):
                    all_questions.extend(data)
                    logger.info(f"Loaded {len(data)} questions from {file_path}")
                elif isinstance(data, dict):
                    all_questions.append(data)
                    logger.info(f"Loaded 1 question from {file_path}")
                else:
                    logger.warning(f"Unexpected format in {file_path}")
                    
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        print(f"✓ Loaded {len(all_questions)} total questions from {len(question_files)} files")
        return all_questions
    
    def _make_baseline_call(self, question_text: str) -> Dict:
        """
        Make baseline API call (no tools).
        
        Returns dict with:
            - success: bool
            - text: str (if successful)
            - error: str (if failed)
            - elapsed_time: float
        """
        start_time = time.time()
        
        # Add final answer instruction to the question
        full_prompt = question_text + self.FINAL_ANSWER_INSTRUCTION
        
        try:
            response = self.baseline_client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                system=self.config["baseline_system_prompt"],
                messages=[{"role": "user", "content": full_prompt}]
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
                "elapsed_time": elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Baseline call failed: {e}")
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
    
    async def _make_togomcp_call_with_retry(
        self,
        question_text: str,
        attempt: int = 1
    ) -> Dict:
        """Make TogoMCP call with retry logic."""
        max_attempts = self.config["retry_attempts"]
        base_delay = self.config["retry_delay"]
        max_delay = self.config.get("max_retry_delay", 30)
        
        for current_attempt in range(attempt, max_attempts + 1):
            try:
                result = await self._make_togomcp_call(question_text)
                return result
                
            except asyncio.TimeoutError:
                error_msg = f"Request timed out after {self.config['timeout']}s"
                logger.warning(f"Attempt {current_attempt}/{max_attempts}: {error_msg}")
                
                if current_attempt < max_attempts:
                    delay = min(base_delay * (2 ** (current_attempt - 1)), max_delay)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        "success": False,
                        "error": error_msg,
                        "elapsed_time": self.config["timeout"] * current_attempt
                    }
                    
            except Exception as e:
                error_str = str(e)
                logger.error(f"Attempt {current_attempt}/{max_attempts} failed: {error_str}")
                
                if current_attempt < max_attempts:
                    delay = min(base_delay * (2 ** (current_attempt - 1)), max_delay)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                
                return {
                    "success": False,
                    "error": error_str,
                    "elapsed_time": 0
                }
        
        return {
            "success": False,
            "error": "Max retry attempts exceeded",
            "elapsed_time": 0
        }
    
    async def _make_togomcp_call(self, question_text: str) -> Dict:
        """
        Make TogoMCP API call with database access.
        
        Returns dict with:
            - success: bool
            - text: str (if successful)
            - tool_uses: list (tools called)
            - error: str (if failed)
            - elapsed_time: float
        """
        start_time = time.time()
        
        # Add final answer instruction to the question
        full_prompt = question_text + self.FINAL_ANSWER_INSTRUCTION
        
        try:
            # Create fresh options for this question
            options = ClaudeAgentOptions(
                system_prompt=self.config["togomcp_system_prompt"],
                mcp_servers=self.config["mcp_servers"],
                model=self.config["model"],
                allowed_tools=self.config["allowed_tools"],
                disallowed_tools=self.config["disallowed_tools"],
                can_use_tool=self._auto_approve_mcp_tools
            )
            
            final_text = None
            tool_uses = []
            
            # Create fresh client for this question only (isolated session)
            async with ClaudeSDKClient(options=options) as client:
                # Single query - no follow-ups
                await asyncio.wait_for(
                    client.query(full_prompt),
                    timeout=self.config["timeout"]
                )
                
                # Collect response and tool uses
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        if hasattr(message, 'content') and isinstance(message.content, list):
                            for block in message.content:
                                block_type = getattr(block, 'type', type(block).__name__)
                                if block_type == "tool_use" or "ToolUse" in type(block).__name__:
                                    tool_name = getattr(block, 'name', 'unknown')
                                    tool_uses.append(tool_name)
                    
                    if isinstance(message, ResultMessage):
                        if hasattr(message, 'result') and isinstance(message.result, str):
                            final_text = message.result
            
            elapsed_time = time.time() - start_time
            
            return {
                "success": True,
                "text": final_text if final_text else "[No text content extracted]",
                "tool_uses": tool_uses,
                "elapsed_time": elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            import traceback
            logger.error(f"TogoMCP call failed: {str(e)}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "tool_uses": [],
                "elapsed_time": elapsed_time
            }
    
    async def run_single_test(
        self, 
        question: Dict, 
        index: int, 
        total: int
    ) -> Dict:
        """
        Run test for a single question.
        
        Collects answers from both baseline and TogoMCP agents.
        No evaluation is performed.
        """
        q_id = question.get("id", f"question_{index}")
        q_body = question.get("body", "")
        q_type = question.get("type", "unknown")
        ideal_answer = question.get("ideal_answer", "")
        
        print(f"\n[{index + 1}/{total}] Testing {q_id} ({q_type})")
        print(f"  Question: {q_body[:80]}{'...' if len(q_body) > 80 else ''}")
        
        # === Baseline Test (No Tools) ===
        print("  ⏳ Running baseline test (no tools)...")
        baseline_result = self._make_baseline_call(q_body)
        
        if baseline_result["success"]:
            print(f"  ✓ Baseline completed in {baseline_result['elapsed_time']:.2f}s")
            baseline_answer = baseline_result["text"]
        else:
            print(f"  ✗ Baseline failed: {baseline_result.get('error', 'Unknown error')}")
            baseline_answer = f"[ERROR: {baseline_result.get('error', 'Unknown error')}]"
        
        # === TogoMCP Test (With Tools) ===
        print("  ⏳ Running TogoMCP test (with database access)...")
        togomcp_result = await self._make_togomcp_call_with_retry(q_body)
        
        if togomcp_result["success"]:
            print(f"  ✓ TogoMCP completed in {togomcp_result['elapsed_time']:.2f}s")
            togomcp_answer = togomcp_result["text"]
            tools_used = togomcp_result.get("tool_uses", [])
            if tools_used:
                print(f"    Tools used: {', '.join(tools_used[:5])}{'...' if len(tools_used) > 5 else ''}")
        else:
            print(f"  ✗ TogoMCP failed: {togomcp_result.get('error', 'Unknown error')}")
            togomcp_answer = f"[ERROR: {togomcp_result.get('error', 'Unknown error')}]"
            tools_used = []
        
        # === Compile Results ===
        result = {
            "question_id": q_id,
            "question": q_body,
            "ideal_answer": ideal_answer,
            "baseline_success": baseline_result["success"],
            "baseline_answer": baseline_answer,
            "togomcp_success": togomcp_result["success"],
            "togomcp_answer": togomcp_answer,
            "tools_used": ", ".join(tools_used) if tools_used else ""
        }
        
        return result
    
    async def run_all_tests(self, questions: List[Dict]) -> List[Dict]:
        """
        Run tests for all questions.
        
        Each question runs in an isolated session.
        Returns list of results with answers collected.
        """
        total = len(questions)
        print(f"\n{'='*70}")
        print(f"TogoMCP Test Runner - Answer Collection")
        print(f"{'='*70}")
        print(f"Questions: {total}")
        print(f"Model: {self.config['model']}")
        print(f"Note: No evaluation performed - answers are only collected")
        print(f"{'='*70}")
        
        results = []
        
        for i, question in enumerate(questions):
            try:
                result = await self.run_single_test(question, i, total)
                results.append(result)
                
                # Save intermediate results every 5 questions
                if (i + 1) % 5 == 0:
                    self._save_intermediate_results(results, i + 1)
                    
            except KeyboardInterrupt:
                print("\n\n⚠ Test run interrupted by user")
                print(f"Completed {i} out of {total} questions")
                break
            except Exception as e:
                logger.error(f"Unexpected error on question {i}: {e}")
                import traceback
                traceback.print_exc()
                # Add error result
                results.append({
                    "question_id": question.get("id", f"question_{i}"),
                    "question": question.get("body", ""),
                    "ideal_answer": question.get("ideal_answer", ""),
                    "baseline_success": False,
                    "baseline_answer": f"[SYSTEM ERROR: {str(e)}]",
                    "togomcp_success": False,
                    "togomcp_answer": f"[SYSTEM ERROR: {str(e)}]",
                    "tools_used": ""
                })
                continue
        
        print(f"\n{'='*70}")
        print(f"Test Run Complete: {len(results)}/{total} questions")
        print(f"{'='*70}\n")
        
        self.results = results
        return results
    
    def _save_intermediate_results(self, results: List[Dict], count: int):
        """Save intermediate results during long test runs."""
        intermediate_path = Path("test_results_intermediate.csv")
        self._export_to_csv(results, str(intermediate_path))
        print(f"  💾 Saved intermediate results ({count} questions)")
    
    def _export_to_csv(self, results: List[Dict], output_path: str):
        """Export results to CSV file."""
        if not results:
            logger.warning("No results to export")
            return
        
        fieldnames = [
            "question_id",
            "question",
            "ideal_answer",
            "baseline_success",
            "baseline_answer",
            "togomcp_success",
            "togomcp_answer",
            "tools_used"
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    def export_results(self, output_path: str):
        """Export results to CSV file."""
        if not self.results:
            print("⚠ No results to export")
            return
        
        self._export_to_csv(self.results, output_path)
        print(f"✓ Results exported to {output_path}")
    
    def print_summary(self):
        """Print test run summary statistics."""
        if not self.results:
            return
        
        total = len(self.results)
        baseline_success = sum(
            1 for r in self.results 
            if r.get("baseline_success", False)
        )
        togomcp_success = sum(
            1 for r in self.results 
            if r.get("togomcp_success", False)
        )
        tools_used_count = sum(
            1 for r in self.results 
            if r.get("tools_used", "")
        )
        
        print("\n" + "="*70)
        print("TEST RUN SUMMARY")
        print("="*70)
        print(f"Total questions:              {total}")
        print()
        print("EXECUTION SUCCESS:")
        print(f"  Baseline successful:        {baseline_success}/{total} ({baseline_success/total*100:.1f}%)")
        print(f"  TogoMCP successful:         {togomcp_success}/{total} ({togomcp_success/total*100:.1f}%)")
        print()
        print("TOOL USAGE:")
        print(f"  Questions using tools:      {tools_used_count}/{total} ({tools_used_count/total*100:.1f}%)")
        print()
        print("Note: Answers have been collected but not evaluated.")
        print("Use a separate evaluation script to assess answer quality.")
        print("="*70 + "\n")


async def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="TogoMCP Test Runner - Answer Collection (No Evaluation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single question file
  python automated_test_runner.py question_001.yaml
  
  # Multiple question files
  python automated_test_runner.py question_001.yaml question_002.yaml question_003.yaml
  
  # Using wildcards
  python automated_test_runner.py questions/question_*.yaml
  
  # Custom output path
  python automated_test_runner.py question_*.yaml -o my_results.csv
  
  # With custom config (YAML or JSON)
  python automated_test_runner.py question_*.yaml -c config.yaml

Output:
  CSV file with columns:
    - question_id: Unique identifier
    - question: Question text (body)
    - ideal_answer: Expected ideal answer
    - baseline_success: Whether baseline query executed successfully (True/False)
    - baseline_answer: Answer from baseline Claude (no tools)
    - togomcp_success: Whether TogoMCP query executed successfully (True/False)
    - togomcp_answer: Answer from TogoMCP Claude (with tools)
    - tools_used: Comma-separated list of tools used by TogoMCP

Next Steps:
  Use a separate evaluation script to assess answer quality and compare
  baseline vs TogoMCP performance.
        """
    )
    
    parser.add_argument(
        "question_files",
        nargs='+',
        help="Path(s) to question YAML file(s)"
    )
    parser.add_argument(
        "-c", "--config", 
        help="Path to configuration file (YAML or JSON)"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Output path for results CSV", 
        default="test_results.csv"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    missing_files = [f for f in args.question_files if not Path(f).exists()]
    if missing_files:
        print(f"✗ Error: Question file(s) not found:")
        for f in missing_files:
            print(f"  - {f}")
        sys.exit(1)
    
    # Initialize runner
    try:
        runner = TestRunner(config_path=args.config)
    except Exception as e:
        print(f"✗ Error initializing runner: {e}")
        sys.exit(1)
    
    # Load questions
    try:
        questions = runner.load_questions(args.question_files)
        if not questions:
            print("✗ Error: No questions loaded")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading questions: {e}")
        sys.exit(1)
    
    # Run tests
    await runner.run_all_tests(questions)
    
    # Export results
    runner.export_results(args.output)
    
    # Print summary
    runner.print_summary()
    
    print(f"\nResults saved to: {args.output}")
    print(f"Next: Use an evaluation script to assess answer quality")


if __name__ == "__main__":
    asyncio.run(main())