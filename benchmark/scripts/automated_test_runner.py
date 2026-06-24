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
        """Initialize runner with configuration.

        Both baseline and TogoMCP calls now run through the claude-agent-sdk
        (Claude Code CLI), so authentication comes from the CLI itself: an
        ANTHROPIC_API_KEY environment variable if set, otherwise the CLI's
        stored login (OAuth / keychain). We therefore no longer require
        ANTHROPIC_API_KEY up front; if no usable credential exists at all,
        the SDK call fails and is reported per-question.
        """
        self.config = self._load_config(config_path)
        self.results = []

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from YAML or JSON file, or use defaults."""
        default_config = {
            "model": "claude-sonnet-4-5-20250929",
            # NOTE: max_tokens / temperature are retained for reference only.
            # Both baseline and TogoMCP now run through the claude-agent-sdk
            # (Claude Code CLI), which does NOT expose these sampling params,
            # so they are no longer applied to either call. This is exactly
            # what makes the two conditions comparable: identical (CLI-fixed)
            # sampling, differing only in tool availability. Kept here so
            # pre-existing config files that set them still load cleanly.
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
            # Seconds to sleep between consecutive questions. 0 = back-to-back
            # (default). Set to 30-90s if you suspect throttling at the
            # togomcp MCP server or its upstream SPARQL endpoint, to give
            # them time to recover between sessions.
            "inter_question_delay": 0,
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
    # Baseline call (claude-agent-sdk, no tools)
    # ------------------------------------------------------------------

    async def _deny_all_tools(
        self,
        tool_name: str,
        input_data: dict,
        context: ToolPermissionContext
    ) -> PermissionResultDeny:
        """Deny every tool call: the baseline condition runs with no tools.

        `allowed_tools=[]` only hides tool *definitions* from the model; the
        SDK still exposes built-in agent tools (Read, Write, Bash, …) that the
        model could attempt. This gate guarantees the baseline answer is built
        purely from training knowledge, mirroring the safeguard the TogoMCP
        path uses in `_auto_approve_mcp_tools`.
        """
        return PermissionResultDeny(
            message="Baseline condition: no tools are available; answer from knowledge."
        )

    async def _make_baseline_call(self, question_text: str, answer_instruction: str = "") -> Dict:
        """
        Make baseline call (no tools) via the claude-agent-sdk / Claude Code CLI.

        Routed through the SAME SDK and CLI as the TogoMCP call so both
        conditions share identical sampling settings (the CLI's fixed
        temperature/max_tokens, which are not externally configurable),
        authentication, and cost accounting. The ONLY difference from the
        TogoMCP call is tool availability: baseline registers no MCP servers,
        advertises no tools, denies every tool attempt, and is capped at a
        single turn.

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
            options = ClaudeAgentOptions(
                system_prompt=self.config["baseline_system_prompt"],
                model=self.config["model"],
                mcp_servers={},          # no database access
                allowed_tools=[],        # advertise no tools to the model
                disallowed_tools=self.config["disallowed_tools"],
                can_use_tool=self._deny_all_tools,
                max_turns=1,             # single-shot answer, no tool loop
                # Same hermeticity guard as the TogoMCP path: do not inherit
                # MCP servers / settings from ~/.claude or project .claude.
                setting_sources=[],
            )

            final_text   = None
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

                gen = aiter(client.receive_response())
                while True:
                    try:
                        message = await asyncio.wait_for(
                            anext(gen),
                            timeout=self.config["timeout"]
                        )
                    except StopAsyncIteration:
                        break

                    usage = _extract_usage_from_obj(message)
                    if usage:
                        total_input  += usage["input_tokens"]
                        total_output += usage["output_tokens"]
                        usage_found   = True

                    if isinstance(message, ResultMessage):
                        if hasattr(message, 'result') and isinstance(message.result, str):
                            final_text = message.result
                        cli_cost = getattr(message, 'total_cost_usd', None)
                        if cli_cost is not None:
                            cost_usd = float(cli_cost)
                            use_cli_cost = True

            elapsed_time = time.time() - start_time

            if not usage_found:
                logger.warning(
                    "Baseline: token usage not found in SDK response messages. "
                    "Token counts will be 0."
                )

            if not use_cli_cost:
                cost_usd = _calc_cost(total_input, total_output, self.config["pricing"])

            # Treat an empty answer as a failure, same as the TogoMCP path: an
            # empty ResultMessage usually means the subprocess died mid-stream
            # and the SDK didn't raise.
            if not final_text or not final_text.strip():
                return {
                    "success": False,
                    "error": (
                        "Empty response from claude-agent-sdk (baseline, no "
                        "ResultMessage text). Likely subprocess failure — "
                        "check test_runner.log."
                    ),
                    "elapsed_time": elapsed_time,
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "cost_usd": cost_usd,
                }

            return {
                "success": True,
                "text": final_text,
                "elapsed_time": elapsed_time,
                "input_tokens": total_input,
                "output_tokens": total_output,
                "cost_usd": cost_usd,
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            import traceback
            logger.error(f"Baseline call failed: {str(e)}\n{traceback.format_exc()}")
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
        """Auto-approve MCP tools; deny everything else.

        `allowed_tools=["mcp__*"]` only filters the tool definitions advertised
        to the model — it does NOT prevent the model from attempting built-in
        agent tools (Read, Write, Bash, Edit, …) that the SDK still exposes.
        Without this gate, those calls succeed silently. We caught it during
        the 2026-05-04 ng2 run when the model wrote five Python helpers and a
        markdown report into benchmark/scripts/ while answering the Joubert
        and ClinVar questions. Block anything that isn't an MCP tool.
        """
        if tool_name in ["WebSearch", "WebFetch", "web_search", "web_fetch"]:
            return PermissionResultDeny(message="Web tools not allowed in evaluation")
        if not tool_name.startswith("mcp__"):
            return PermissionResultDeny(
                message=(
                    f"Non-MCP tool {tool_name!r} blocked: this benchmark only allows "
                    "MCP tool calls. Use the registered MCP servers to retrieve data."
                )
            )
        return PermissionResultAllow()

    async def _make_togomcp_call_with_retry(
        self,
        question_text: str,
        answer_instruction: str = "",
        attempt: int = 1
    ) -> Dict:
        """Make TogoMCP call with retry logic.

        Retries on:
          - asyncio.TimeoutError (subprocess hung)
          - any other exception
          - returned dict with success=False (e.g. empty response from the SDK
            subprocess — almost always a transient upstream issue worth retrying)
        """
        max_attempts = self.config["retry_attempts"]
        base_delay   = self.config["retry_delay"]
        max_delay    = self.config.get("max_retry_delay", 30)

        last_result: Optional[Dict] = None
        total_elapsed = 0.0

        for current_attempt in range(attempt, max_attempts + 1):
            attempt_failed = False
            error_for_log = ""

            try:
                result = await self._make_togomcp_call(question_text, answer_instruction)
                total_elapsed += result.get("elapsed_time", 0.0)

                if result.get("success"):
                    # Return the successful attempt's own elapsed_time —
                    # we deliberately do NOT roll up the time spent on
                    # preceding failed attempts or retry sleeps. The CSV's
                    # togomcp_time column reflects only the call that
                    # produced the answer.
                    return result

                # Application-level failure: treat like a retryable exception.
                last_result = result
                error_for_log = result.get("error", "success=False (no detail)")
                attempt_failed = True

            except asyncio.TimeoutError:
                total_elapsed += self.config["timeout"]
                error_for_log = f"Request timed out after {self.config['timeout']}s"
                last_result = {
                    "success": False,
                    "error": error_for_log,
                    "tool_uses": [],
                    "elapsed_time": self.config["timeout"],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
                attempt_failed = True

            except Exception as e:
                error_for_log = str(e)
                last_result = {
                    "success": False,
                    "error": error_for_log,
                    "tool_uses": [],
                    "elapsed_time": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
                attempt_failed = True

            if attempt_failed:
                logger.warning(
                    f"Attempt {current_attempt}/{max_attempts}: {error_for_log}"
                )
                if current_attempt < max_attempts:
                    delay = min(base_delay * (2 ** (current_attempt - 1)), max_delay)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

        # All retries exhausted. Augment the error with a rate-limit / quota
        # hint when the failure pattern is consistent with throttling
        # (each attempt completed quickly, which is the signature we see
        # when the bundled claude CLI returns an empty response without
        # raising — usually rate limit or session quota, not a code bug).
        if last_result is None:
            last_result = {
                "success": False,
                "error": "No attempts made (max_attempts <= 0)",
                "tool_uses": [],
                "elapsed_time": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }

        avg_per_attempt = total_elapsed / max(1, max_attempts)
        rate_limit_hint = ""
        if avg_per_attempt < 10.0:
            rate_limit_hint = (
                " Each attempt finished in <10s and the SDK raised no error. "
                "Most likely throttling at the togomcp MCP server (per-IP "
                "request cap, connection-pool exhaustion) or its upstream "
                "SPARQL endpoint — NOT the Anthropic API. Check the togomcp "
                "container logs (docker/podman logs togomcp-main) for 429s, "
                "503s, or upstream timeouts around the failure window. If "
                "it correlates with token-heavy preceding questions, "
                "consider raising `inter_question_delay` in config.yaml."
            )

        last_result = dict(last_result)
        last_result["error"] = (
            f"All {max_attempts} attempts failed (total {total_elapsed:.1f}s "
            f"across attempts, avg {avg_per_attempt:.1f}s/attempt). "
            f"Last error: {last_result.get('error', 'unknown')}.{rate_limit_hint}"
        )
        # elapsed_time stays as the last attempt's own time — we don't roll
        # cumulative attempt time or retry sleeps into the recorded latency.
        return last_result

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
                can_use_tool=self._auto_approve_mcp_tools,
                # Hermeticity: disable inheriting MCP servers / settings from
                # the user's ~/.claude/settings.json or any project-level
                # .claude/settings.json. Without this, the SDK pulls in every
                # MCP server the user has registered with Claude Code (e.g.
                # togomcp-dev for local dev work), contaminating the benchmark
                # — verified empirically with 56 unintended mcp__togomcp-dev__*
                # tool calls across 7 questions in with_guide-2026-05-03.csv.
                setting_sources=[],
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

                # Wrap each message receive in wait_for so the loop can't hang
                # silently when the subprocess / MCP session dies mid-stream.
                # Without this, the SDK can return an empty `receive_response`
                # iterator without raising, producing a "success" with no text.
                gen = aiter(client.receive_response())
                while True:
                    try:
                        message = await asyncio.wait_for(
                            anext(gen),
                            timeout=self.config["timeout"]
                        )
                    except StopAsyncIteration:
                        break

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
                                    name = getattr(block, 'name', 'unknown')
                                    # Record EVERY tool the model attempts, not
                                    # just `mcp__*`. The earlier filter hid
                                    # built-in agent tools (Read, Write, Bash,
                                    # Edit, …) the model occasionally tried
                                    # mid-question — silent leakage that wrote
                                    # files into benchmark/scripts/ during the
                                    # 2026-05-04 ng2 run. Recording all names
                                    # makes such attempts visible in the CSV;
                                    # they will also be denied by
                                    # _auto_approve_mcp_tools.
                                    tool_uses.append(name)

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

            # Reject empty-result responses as failures so the retry loop sees
            # them. An empty `final_text` (no ResultMessage with text) usually
            # means the claude-agent-sdk subprocess died or the MCP session
            # closed mid-stream; the SDK doesn't always raise in that case,
            # so without this guard the result is silently misclassified as a
            # success with placeholder text.
            if not final_text or not final_text.strip():
                return {
                    "success": False,
                    "error": (
                        "Empty response from claude-agent-sdk (no ResultMessage text). "
                        "Likely subprocess/MCP failure — check test_runner.log."
                    ),
                    "tool_uses": tool_uses,
                    "elapsed_time": elapsed_time,
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "cost_usd": cost_usd,
                }

            return {
                "success": True,
                "text": final_text,
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
        baseline_result = await self._make_baseline_call(q_body, answer_instruction)

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
        inter_delay = float(self.config.get("inter_question_delay", 0))
        if inter_delay > 0:
            print(f"Inter-question delay: {inter_delay:.1f}s")

        for i, question in enumerate(questions):
            try:
                result = await self.run_single_test(question, i, total)
                results.append(result)

                if (i + 1) % 5 == 0:
                    self._save_intermediate_results(results, i + 1)

                # Cooldown before the next question, if configured. Skip on the
                # last question — no point sleeping after the run is done.
                if inter_delay > 0 and (i + 1) < total:
                    print(f"  ⏸  Sleeping {inter_delay:.1f}s before next question...")
                    await asyncio.sleep(inter_delay)

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
