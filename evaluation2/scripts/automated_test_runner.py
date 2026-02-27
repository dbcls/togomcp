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
- Outputs simple CSV with questions, answers, and token/cost data
- Accepts multiple question files as command-line arguments
- No evaluation performed (handled separately)
- Tracks token usage and USD cost for both baseline and TogoMCP calls

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
    - baseline_input_tokens: Input tokens consumed by baseline call
    - baseline_output_tokens: Output tokens consumed by baseline call
    - baseline_cost_usd: Estimated USD cost for baseline call
    - togomcp_success: Whether TogoMCP query executed successfully (True/False)
    - togomcp_answer: Answer from TogoMCP Claude (with tools)
    - togomcp_input_tokens: Input tokens consumed by TogoMCP call (all turns)
    - togomcp_output_tokens: Output tokens consumed by TogoMCP call (all turns)
    - togomcp_cost_usd: Estimated USD cost for TogoMCP call
    - total_cost_usd: Combined cost for this question
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


# ---------------------------------------------------------------------------
# Cost calculation helpers
# ---------------------------------------------------------------------------

def _calc_cost(input_tokens: int, output_tokens: int, pricing: Dict) -> float:
    """Return estimated USD cost given token counts and per-million-token prices."""
    input_cost  = input_tokens  / 1_000_000 * pricing["input_per_million"]
    output_cost = output_tokens / 1_000_000 * pricing["output_per_million"]
    return round(input_cost + output_cost, 6)


def _extract_usage_from_obj(obj) -> Optional[Dict[str, int]]:
    """
    Try to pull input_tokens / output_tokens from an object that may carry
    usage information in several common shapes:
      - obj.usage.input_tokens / obj.usage.output_tokens
      - obj.input_tokens / obj.output_tokens  (flat)
      - dict keys 'input_tokens', 'output_tokens'
    Returns a dict {"input_tokens": int, "output_tokens": int} or None.
    """
    if obj is None:
        return None

    # Attribute-based (SDK objects)
    usage = getattr(obj, "usage", None)
    if usage is not None:
        # ResultMessage.usage is a plain dict; other SDKs use objects
        if isinstance(usage, dict):
            inp = usage.get("input_tokens")
            out = usage.get("output_tokens")
        else:
            inp = getattr(usage, "input_tokens", None)
            out = getattr(usage, "output_tokens", None)
        if inp is not None and out is not None:
            return {"input_tokens": int(inp), "output_tokens": int(out)}

    # Flat attributes directly on the object
    inp = getattr(obj, "input_tokens", None)
    out = getattr(obj, "output_tokens", None)
    if inp is not None and out is not None:
        return {"input_tokens": int(inp), "output_tokens": int(out)}

    # Dict-style
    if isinstance(obj, dict):
        inp = obj.get("input_tokens")
        out = obj.get("output_tokens")
        if inp is not None and out is not None:
            return {"input_tokens": int(inp), "output_tokens": int(out)}

    return None


class TestRunner:
    """
    Runs tests to collect answers from baseline and TogoMCP agents.

    Each question runs in a fresh Claude session with no conversation history.
    No evaluation is performed - only answer collection.
    Token usage and USD cost are tracked for every call.
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
            # ------------------------------------------------------------------
            # Pricing (USD per 1 million tokens).
            # Defaults match Claude Sonnet 4.5 list prices; override in config.yaml
            # to match whichever model you are actually using.
            # ------------------------------------------------------------------
            "pricing": {
                "input_per_million": 3.0,
                "output_per_million": 15.0,
            },
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

        if config_path:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_path}. Using default settings.")
            else:
                with open(config_file, 'r') as f:
                    try:
                        user_config = yaml.safe_load(f)
                    except yaml.YAMLError:
                        f.seek(0)
                        import json
                        user_config = json.load(f)

                if isinstance(user_config, dict):
                    # Deep-merge dict sub-keys so partial overrides work
                    for key in ("pricing", "mcp_servers"):
                        if key in user_config and isinstance(user_config[key], dict):
                            default_config[key].update(user_config.pop(key))
                    default_config.update(user_config)
                    logger.info(f"Loaded config from: {config_path}")
                else:
                    logger.warning(f"Config file {config_path} did not contain a dict, ignoring")
        else:
            logger.warning("No config file specified (-c / --config). Using default settings.")

        return default_config

    # ------------------------------------------------------------------
    # Question loading
    # ------------------------------------------------------------------

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
                    try:
                        data = yaml.safe_load(f)
                    except yaml.YAMLError:
                        f.seek(0)
                        import json
                        data = json.load(f)

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

    # ------------------------------------------------------------------
    # Baseline call (Anthropic SDK – usage always available)
    # ------------------------------------------------------------------

    def _make_baseline_call(self, question_text: str, answer_instruction: str = "") -> Dict:
        """
        Make baseline API call (no tools).

        Returns dict with:
            - success: bool
            - text: str (if successful)
            - error: str (if failed)
            - elapsed_time: float
            - input_tokens: int
            - output_tokens: int
            - cost_usd: float
        """
        start_time = time.time()

        if not answer_instruction:
            answer_instruction = self.FINAL_ANSWER_INSTRUCTION

        full_prompt = question_text + answer_instruction

        try:
            response = self.baseline_client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                system=self.config["baseline_system_prompt"],
                messages=[{"role": "user", "content": full_prompt}]
            )

            elapsed_time = time.time() - start_time

            text_content = [
                block.text
                for block in response.content
                if block.type == "text"
            ]

            input_tokens  = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_usd = _calc_cost(input_tokens, output_tokens, self.config["pricing"])

            return {
                "success": True,
                "text": "\n".join(text_content),
                "elapsed_time": elapsed_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Baseline call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "elapsed_time": elapsed_time,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }

    # ------------------------------------------------------------------
    # TogoMCP call (claude-agent-sdk)
    # ------------------------------------------------------------------

    async def _auto_approve_mcp_tools(
        self,
        tool_name: str,
        input_data: dict,
        context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Auto-approve MCP tools, deny web tools."""
        if tool_name in ["WebSearch", "WebFetch", "web_search", "web_fetch"]:
            return PermissionResultDeny(message="Web tools not allowed in evaluation")
        return PermissionResultAllow()

    async def _make_togomcp_call_with_retry(
        self,
        question_text: str,
        answer_instruction: str = "",
        attempt: int = 1
    ) -> Dict:
        """Make TogoMCP call with retry logic."""
        max_attempts = self.config["retry_attempts"]
        base_delay   = self.config["retry_delay"]
        max_delay    = self.config.get("max_retry_delay", 30)

        for current_attempt in range(attempt, max_attempts + 1):
            try:
                result = await self._make_togomcp_call(question_text, answer_instruction)
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
                        "elapsed_time": self.config["timeout"] * current_attempt,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cost_usd": 0.0,
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
                    "elapsed_time": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }

        return {
            "success": False,
            "error": "Max retry attempts exceeded",
            "elapsed_time": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }

    async def _make_togomcp_call(self, question_text: str, answer_instruction: str = "") -> Dict:
        """
        Make TogoMCP API call with database access.

        Returns dict with:
            - success: bool
            - text: str (if successful)
            - tool_uses: list (tools called)
            - error: str (if failed)
            - elapsed_time: float
            - input_tokens: int   (accumulated across all turns)
            - output_tokens: int  (accumulated across all turns)
            - cost_usd: float
        """
        start_time = time.time()

        if not answer_instruction:
            answer_instruction = self.FINAL_ANSWER_INSTRUCTION

        full_prompt = question_text + answer_instruction

        try:
            options = ClaudeAgentOptions(
                system_prompt=self.config["togomcp_system_prompt"],
                mcp_servers=self.config["mcp_servers"],
                model=self.config["model"],
                allowed_tools=self.config["allowed_tools"],
                disallowed_tools=self.config["disallowed_tools"],
                can_use_tool=self._auto_approve_mcp_tools
            )

            final_text   = None
            tool_uses    = []
            total_input  = 0
            total_output = 0
            usage_found  = False
            cost_usd     = 0.0
            use_cli_cost = False

            async with ClaudeSDKClient(options=options) as client:
                await asyncio.wait_for(
                    client.query(full_prompt),
                    timeout=self.config["timeout"]
                )

                async for message in client.receive_response():
                    # ---- Accumulate token usage from every message ----
                    usage = _extract_usage_from_obj(message)
                    if usage:
                        total_input  += usage["input_tokens"]
                        total_output += usage["output_tokens"]
                        usage_found   = True

                    # ---- Collect tool names ----
                    if isinstance(message, AssistantMessage):
                        if hasattr(message, 'content') and isinstance(message.content, list):
                            for block in message.content:
                                block_type = getattr(block, 'type', type(block).__name__)
                                if block_type == "tool_use" or "ToolUse" in type(block).__name__:
                                    tool_uses.append(getattr(block, 'name', 'unknown'))

                                # Some SDKs embed usage inside content blocks too
                                inner_usage = _extract_usage_from_obj(block)
                                if inner_usage:
                                    total_input  += inner_usage["input_tokens"]
                                    total_output += inner_usage["output_tokens"]
                                    usage_found   = True

                    # ---- Capture final answer + authoritative cost ----
                    if isinstance(message, ResultMessage):
                        if hasattr(message, 'result') and isinstance(message.result, str):
                            final_text = message.result
                        # The CLI already calculates true cost (incl. cache charges);
                        # prefer it over our own recomputation when available.
                        cli_cost = getattr(message, 'total_cost_usd', None)
                        if cli_cost is not None:
                            cost_usd = float(cli_cost)
                            use_cli_cost = True

            elapsed_time = time.time() - start_time

            if not usage_found:
                logger.warning(
                    "Token usage not found in SDK response messages. "
                    "Token counts will be 0. "
                    "Check whether a newer claude-agent-sdk version exposes usage data."
                )

            if not use_cli_cost:
                cost_usd = _calc_cost(total_input, total_output, self.config["pricing"])

            return {
                "success": True,
                "text": final_text if final_text else "[No text content extracted]",
                "tool_uses": tool_uses,
                "elapsed_time": elapsed_time,
                "input_tokens": total_input,
                "output_tokens": total_output,
                "cost_usd": cost_usd,
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            import traceback
            logger.error(f"TogoMCP call failed: {str(e)}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "tool_uses": [],
                "elapsed_time": elapsed_time,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }

    # ------------------------------------------------------------------
    # Single test
    # ------------------------------------------------------------------

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
        q_id         = question.get("id", f"question_{index}")
        q_body       = question.get("body", "")
        q_type       = question.get("type", "unknown")
        ideal_answer = question.get("ideal_answer", "")
        choices      = question.get("choices", [])

        if q_type == "choice" and choices:
            choices_text = "\n".join(f"  - {c}" for c in choices)
            q_body = f"{q_body}\n\nChoose one of the following options:\n{choices_text}"

        if q_type == "choice":
            answer_instruction = (
                "\n\nState which option or options are correct and briefly explain why in one paragraph."
            )
        else:
            answer_instruction = self.FINAL_ANSWER_INSTRUCTION

        print(f"\n[{index + 1}/{total}] Testing {q_id} ({q_type})")
        print(f"  Question: {q_body[:80]}{'...' if len(q_body) > 80 else ''}")

        # === Baseline Test (No Tools) ===
        print("  ⏳ Running baseline test (no tools)...")
        baseline_result = self._make_baseline_call(q_body, answer_instruction)

        if baseline_result["success"]:
            print(
                f"  ✓ Baseline completed in {baseline_result['elapsed_time']:.2f}s "
                f"| {baseline_result['input_tokens']}↑ {baseline_result['output_tokens']}↓ tokens "
                f"| ${baseline_result['cost_usd']:.4f}"
            )
            baseline_answer = baseline_result["text"]
        else:
            print(f"  ✗ Baseline failed: {baseline_result.get('error', 'Unknown error')}")
            baseline_answer = f"[ERROR: {baseline_result.get('error', 'Unknown error')}]"

        # === TogoMCP Test (With Tools) ===
        print("  ⏳ Running TogoMCP test (with database access)...")
        togomcp_result = await self._make_togomcp_call_with_retry(q_body, answer_instruction)

        if togomcp_result["success"]:
            print(
                f"  ✓ TogoMCP completed in {togomcp_result['elapsed_time']:.2f}s "
                f"| {togomcp_result['input_tokens']}↑ {togomcp_result['output_tokens']}↓ tokens "
                f"| ${togomcp_result['cost_usd']:.4f}"
            )
            togomcp_answer = togomcp_result["text"]
            tools_used = togomcp_result.get("tool_uses", [])
            if tools_used:
                print(f"    Tools used: {', '.join(tools_used[:5])}{'...' if len(tools_used) > 5 else ''}")
        else:
            print(f"  ✗ TogoMCP failed: {togomcp_result.get('error', 'Unknown error')}")
            togomcp_answer = f"[ERROR: {togomcp_result.get('error', 'Unknown error')}]"
            tools_used = []

        total_cost = round(baseline_result["cost_usd"] + togomcp_result["cost_usd"], 6)

        # === Compile Results ===
        result = {
            "question_id":           q_id,
            "question_type":         q_type,
            "question":              q_body,
            "ideal_answer":          ideal_answer,
            # Baseline
            "baseline_success":      baseline_result["success"],
            "baseline_time":         round(baseline_result.get("elapsed_time", 0.0), 2),
            "baseline_answer":       baseline_answer,
            "baseline_input_tokens": baseline_result["input_tokens"],
            "baseline_output_tokens":baseline_result["output_tokens"],
            "baseline_cost_usd":     baseline_result["cost_usd"],
            # TogoMCP
            "togomcp_success":       togomcp_result["success"],
            "togomcp_time":          round(togomcp_result.get("elapsed_time", 0.0), 2),
            "togomcp_answer":        togomcp_answer,
            "togomcp_input_tokens":  togomcp_result["input_tokens"],
            "togomcp_output_tokens": togomcp_result["output_tokens"],
            "togomcp_cost_usd":      togomcp_result["cost_usd"],
            # Combined
            "total_cost_usd":        total_cost,
            "tools_used":            ", ".join(tools_used) if tools_used else "",
        }

        return result

    # ------------------------------------------------------------------
    # Run all tests
    # ------------------------------------------------------------------

    async def run_all_tests(self, questions: List[Dict]) -> List[Dict]:
        """
        Run tests for all questions.

        Each question runs in an isolated session.
        Returns list of results with answers and token/cost data collected.
        """
        total = len(questions)
        pricing = self.config["pricing"]
        print(f"\n{'='*70}")
        print(f"TogoMCP Test Runner - Answer Collection")
        print(f"{'='*70}")
        print(f"Questions: {total}")
        print(f"Model:     {self.config['model']}")
        print(f"Pricing:   ${pricing['input_per_million']}/M input tokens, "
              f"${pricing['output_per_million']}/M output tokens")
        print(f"Note: No evaluation performed - answers are only collected")
        print(f"{'='*70}")

        results = []

        for i, question in enumerate(questions):
            try:
                result = await self.run_single_test(question, i, total)
                results.append(result)

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
                results.append({
                    "question_id":           question.get("id", f"question_{i}"),
                    "question_type":         question.get("type", "unknown"),
                    "question":              question.get("body", ""),
                    "ideal_answer":          question.get("ideal_answer", ""),
                    "baseline_success":      False,
                    "baseline_time":         0.0,
                    "baseline_answer":       f"[SYSTEM ERROR: {str(e)}]",
                    "baseline_input_tokens": 0,
                    "baseline_output_tokens":0,
                    "baseline_cost_usd":     0.0,
                    "togomcp_success":       False,
                    "togomcp_time":          0.0,
                    "togomcp_answer":        f"[SYSTEM ERROR: {str(e)}]",
                    "togomcp_input_tokens":  0,
                    "togomcp_output_tokens": 0,
                    "togomcp_cost_usd":      0.0,
                    "total_cost_usd":        0.0,
                    "tools_used":            "",
                })
                continue

        print(f"\n{'='*70}")
        print(f"Test Run Complete: {len(results)}/{total} questions")
        print(f"{'='*70}\n")

        self.results = results
        return results

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_intermediate_results(self, results: List[Dict], count: int):
        """Save intermediate results during long test runs."""
        self._export_to_csv(results, "test_results_intermediate.csv")
        print(f"  💾 Saved intermediate results ({count} questions)")

    def _export_to_csv(self, results: List[Dict], output_path: str):
        """Export results to CSV file."""
        if not results:
            logger.warning("No results to export")
            return

        fieldnames = [
            "question_id",
            "question_type",
            "question",
            "ideal_answer",
            # Baseline
            "baseline_success",
            "baseline_time",
            "baseline_answer",
            "baseline_input_tokens",
            "baseline_output_tokens",
            "baseline_cost_usd",
            # TogoMCP
            "togomcp_success",
            "togomcp_time",
            "togomcp_answer",
            "togomcp_input_tokens",
            "togomcp_output_tokens",
            "togomcp_cost_usd",
            # Combined
            "total_cost_usd",
            "tools_used",
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

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def print_summary(self):
        """Print test run summary statistics including token usage and cost."""
        if not self.results:
            return

        total            = len(self.results)
        baseline_success = sum(1 for r in self.results if r.get("baseline_success", False))
        togomcp_success  = sum(1 for r in self.results if r.get("togomcp_success", False))
        tools_used_count = sum(1 for r in self.results if r.get("tools_used", ""))

        # Token totals
        bl_in   = sum(r.get("baseline_input_tokens",  0) for r in self.results)
        bl_out  = sum(r.get("baseline_output_tokens", 0) for r in self.results)
        bl_cost = sum(r.get("baseline_cost_usd",      0.0) for r in self.results)

        tg_in   = sum(r.get("togomcp_input_tokens",  0) for r in self.results)
        tg_out  = sum(r.get("togomcp_output_tokens", 0) for r in self.results)
        tg_cost = sum(r.get("togomcp_cost_usd",      0.0) for r in self.results)

        grand_cost = sum(r.get("total_cost_usd", 0.0) for r in self.results)

        pricing = self.config["pricing"]

        print("\n" + "="*70)
        print("TEST RUN SUMMARY")
        print("="*70)
        print(f"Total questions:               {total}")
        print()
        print("EXECUTION SUCCESS:")
        print(f"  Baseline successful:         {baseline_success}/{total} ({baseline_success/total*100:.1f}%)")
        print(f"  TogoMCP successful:          {togomcp_success}/{total} ({togomcp_success/total*100:.1f}%)")
        print()
        print("TOOL USAGE:")
        print(f"  Questions using tools:       {tools_used_count}/{total} ({tools_used_count/total*100:.1f}%)")
        print()
        print("TOKEN USAGE:")
        print(f"  Baseline   input  tokens:    {bl_in:>12,}  (avg {bl_in//total if total else 0:,}/q)")
        print(f"  Baseline   output tokens:    {bl_out:>12,}  (avg {bl_out//total if total else 0:,}/q)")
        print(f"  TogoMCP    input  tokens:    {tg_in:>12,}  (avg {tg_in//total if total else 0:,}/q)")
        print(f"  TogoMCP    output tokens:    {tg_out:>12,}  (avg {tg_out//total if total else 0:,}/q)")
        print()
        print("ESTIMATED COST (USD):")
        print(f"  Pricing:  ${pricing['input_per_million']:.2f}/M input, "
              f"${pricing['output_per_million']:.2f}/M output")
        print(f"  Baseline total:              ${bl_cost:>10.4f}  (avg ${bl_cost/total if total else 0:.4f}/q)")
        print(f"  TogoMCP  total:              ${tg_cost:>10.4f}  (avg ${tg_cost/total if total else 0:.4f}/q)")
        print(f"  Grand total:                 ${grand_cost:>10.4f}  (avg ${grand_cost/total if total else 0:.4f}/q)")
        print()
        print("Note: Answers have been collected but not evaluated.")
        print("      TogoMCP token counts may be 0 if the claude-agent-sdk version")
        print("      in use does not expose usage data in response messages.")
        print("Use a separate evaluation script to assess answer quality.")
        print("="*70 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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

Output CSV columns (new token/cost columns marked with *):
    question_id, question_type, question, ideal_answer
    baseline_success, baseline_time, baseline_answer
    * baseline_input_tokens, * baseline_output_tokens, * baseline_cost_usd
    togomcp_success, togomcp_time, togomcp_answer
    * togomcp_input_tokens, * togomcp_output_tokens, * togomcp_cost_usd
    * total_cost_usd
    tools_used

Pricing config (add to config.yaml to override defaults):
    pricing:
      input_per_million: 3.0    # USD per 1M input tokens
      output_per_million: 15.0  # USD per 1M output tokens
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

    missing_files = [f for f in args.question_files if not Path(f).exists()]
    if missing_files:
        print("✗ Error: Question file(s) not found:")
        for f in missing_files:
            print(f"  - {f}")
        sys.exit(1)

    try:
        runner = TestRunner(config_path=args.config)
    except Exception as e:
        print(f"✗ Error initializing runner: {e}")
        sys.exit(1)

    try:
        questions = runner.load_questions(args.question_files)
        if not questions:
            print("✗ Error: No questions loaded")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading questions: {e}")
        sys.exit(1)

    await runner.run_all_tests(questions)
    runner.export_results(args.output)
    runner.print_summary()

    print(f"\nResults saved to: {args.output}")
    print(f"Next: Use an evaluation script to assess answer quality")


if __name__ == "__main__":
    asyncio.run(main())
