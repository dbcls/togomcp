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
platform (see results/reevaluation.md). The judge is pluggable:

    * --provider anthropic (default): a Claude judge. By default it runs through
      the Claude CLI / claude-agent-sdk (same auth as automated_test_runner.py —
      your `claude login`, no ANTHROPIC_API_KEY needed) and returns a JSON object
      constrained by a strict prompt. Pass --use-api to use the Anthropic Messages
      API instead (forced `record_evaluation` tool call; requires ANTHROPIC_API_KEY).
    * --provider ollama: a local model (e.g. Gemma, Qwen) via Ollama, using
      structured outputs (`format=<JSON schema>`) rather than tool calling,
      since not every local model supports tools. The SAME schema constrains
      generation, so every judge returns the same shape.

One judge per run — run the script once per model and keep the outputs in
separate files (column names are identical, so join later on question_id):

Usage:
    # Claude (default):
    python add_llm_evaluation.py test_results.csv -o results-claude.csv
    python add_llm_evaluation.py test_results.csv --model claude-opus-4-7

    # Local models via Ollama (provider inferred from the non-claude model):
    python add_llm_evaluation.py test_results.csv --model gemma3  -o results-gemma.csv
    python add_llm_evaluation.py test_results.csv --model qwen3   -o results-qwen.csv
    python add_llm_evaluation.py test_results.csv --provider ollama --model qwen3 \
        --ollama-host http://gpu-box:11434 -o results-qwen.csv

    # Five independent runs (-> results-v1.csv ... results-v5.csv):
    python add_llm_evaluation.py test_results.csv -o results.csv --runs 5

Auth / setup:
    * Claude judge (default, via the CLI / agent SDK): authenticates exactly like
      automated_test_runner.py — the bundled Claude Code CLI uses your `claude
      login` (OAuth/keychain). Do NOT set ANTHROPIC_API_KEY for this path unless
      you want API billing (the CLI prefers the key when it is present).
    * Claude judge with --use-api: the plain `anthropic` SDK requires an
      ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN, or an `ant auth login` profile).
      The plain SDK does NOT read the `claude login` keychain.
    * Ollama: a running Ollama host ($OLLAMA_HOST or http://localhost:11434)
      with the model already pulled (`ollama pull gemma3`). No API key.

Requirements:
    pip install claude-agent-sdk anthropic pandas ollama
"""

import argparse
import asyncio
import json
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

# Optional — only needed for --provider ollama. Guarded so Claude-only users
# don't have to install it; OllamaJudge raises a clear FatalJudgeError if it's
# requested without the package present.
try:
    import ollama
except ImportError:
    ollama = None

# The Claude judge defaults to the Claude CLI (claude-agent-sdk), which authenticates
# via `claude login` — no ANTHROPIC_API_KEY needed (matches automated_test_runner.py).
# Guarded so --provider ollama / --use-api users don't have to install it.
try:
    from claude_agent_sdk import (
        ClaudeSDKClient,
        ClaudeAgentOptions,
        ResultMessage,
        PermissionResultDeny,
    )
except ImportError:
    ClaudeSDKClient = None

# Default judge model for --provider anthropic. claude-opus-4-8 is the current
# Opus; override with --model (e.g. claude-opus-4-7) to reproduce an earlier
# evaluation batch. Ollama has no default — --model is required there.
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


# Transient judge failures (network blip, empty/garbled response, momentary
# refusal) get retried before a row is written off as a zero. A single crashed
# judge call otherwise sinks the whole row to total_score=0, which downstream
# analyzers exclude — losing a real answer. FatalJudgeError is never retried.
JUDGE_MAX_ATTEMPTS = 3
JUDGE_RETRY_BACKOFF = 1.0  # seconds; multiplied by the attempt number

# Abort the whole run after this many CONSECUTIVE rows fail evaluation outright
# (judge returned nothing parseable even after JUDGE_MAX_ATTEMPTS retries). A lone
# failed row is tolerated (transient/odd answer), but a sustained streak means the
# judge is systemically down — throttled subscription, dead host, refusing model —
# and every remaining row would silently score 0. Better to stop loudly (like
# FatalJudgeError) than complete a run of all-zeros. Reset on the first success.
ABORT_AFTER_CONSECUTIVE_FAILURES = 3


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


class FatalJudgeError(RuntimeError):
    """Abort the entire run. Raised for conditions that would fail identically
    on every row — a bad/absent credential, an unreachable Ollama host, or a
    model the backend can't find — so we stop instead of scoring every row 0."""


class JudgeBackend:
    """A judge-model provider. Subclasses turn (system_prompt, user_content)
    into a validated `Evaluation`, accumulate token usage on
    total_input_tokens / total_output_tokens, and raise `FatalJudgeError` for
    run-aborting conditions."""

    provider = "base"

    def __init__(self, model: str):
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def call(self, system_prompt: str, user_content: str):
        """Return a validated `Evaluation`, or None if the judge produced no
        parseable structured output (treated as a per-row failure). Raise
        `FatalJudgeError` to abort the whole run."""
        raise NotImplementedError


class AnthropicJudge(JudgeBackend):
    """Claude judge via the Anthropic Messages API, forcing a single
    `record_evaluation` tool call so the response is always structured."""

    provider = "anthropic"

    def __init__(self, model: str = DEFAULT_MODEL):
        super().__init__(model)
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
            raise FatalJudgeError(
                "No Anthropic credential found. Set ANTHROPIC_API_KEY (or "
                "ANTHROPIC_AUTH_TOKEN, or run `ant auth login`). The plain "
                "anthropic SDK does not read the `claude login` keychain."
            )

    def call(self, system_prompt: str, user_content: str):
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
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
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.NotFoundError,
        ) as e:
            # Bad key / no access / wrong --model would fail identically on
            # every row — abort the whole run instead of zeroing all rows.
            raise FatalJudgeError(str(e)) from e

        usage = getattr(response, "usage", None)
        if usage is not None:
            self.total_input_tokens += getattr(usage, "input_tokens", 0) or 0
            self.total_output_tokens += getattr(usage, "output_tokens", 0) or 0

        tool_block = next(
            (b for b in response.content if getattr(b, "type", None) == "tool_use"),
            None,
        )
        if tool_block is None:
            return None
        return Evaluation(**tool_block.input)


# Appended to the rubric for the CLI judge: the agent SDK has no forced-tool-use,
# so we constrain the output with a strict "JSON only" instruction and parse it.
_JSON_ONLY_INSTRUCTION = """

Respond with ONLY a single JSON object and nothing else — no prose, no markdown \
code fences, no leading or trailing text. It must have exactly these keys:
  "recall", "precision", "repetition", "readability" — each an integer 1-5, and
  "explanation" — a 1-2 sentence string justifying the scores.
Example: {"recall": 4, "precision": 5, "repetition": 5, "readability": 4, "explanation": "..."}"""

# One turn is plenty for a scoring call; guards against a hung CLI subprocess.
_AGENT_JUDGE_TIMEOUT = 180


def _usage_tokens(message: Any) -> tuple[int, int]:
    """Pull (input, output) token counts from an SDK message, in any of its shapes."""
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        return int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0)
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)


def _parse_eval_json(text: str):
    """Extract the judge's JSON object from `text` and return an Evaluation, or None."""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`").lstrip()
        if s[:4].lower() == "json":
            s = s[4:]
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j < i:
        return None
    try:
        d = json.loads(s[i:j + 1])
        return Evaluation(
            recall=int(d["recall"]),
            precision=int(d["precision"]),
            repetition=int(d["repetition"]),
            readability=int(d["readability"]),
            explanation=str(d.get("explanation", "")),
        )
    except (ValueError, KeyError, TypeError):
        return None


async def _deny_all_tools(tool_name, input_data, context):
    """The judge answers from the prompt alone; deny every tool the model might try."""
    return PermissionResultDeny(message="Judge runs without tools; answer from the prompt.")


class AgentSDKJudge(JudgeBackend):
    """Claude judge via the Claude CLI (claude-agent-sdk), authenticating through
    `claude login` like automated_test_runner.py — no ANTHROPIC_API_KEY required.

    The agent SDK doesn't expose forced tool use, so structured output is obtained
    with a strict "JSON only" prompt (mirroring OllamaJudge) and parsed. Each call
    is a single-turn, tool-less query run to completion via asyncio.run."""

    provider = "anthropic"

    def __init__(self, model: str = DEFAULT_MODEL):
        super().__init__(model)
        if ClaudeSDKClient is None:
            raise FatalJudgeError(
                "claude-agent-sdk not installed (needed for the default Claude CLI "
                "judge). Install with: pip install claude-agent-sdk — or use --use-api."
            )
        self._calls = 0

    async def _acall(self, system_prompt: str, user_content: str):
        options = ClaudeAgentOptions(
            system_prompt=system_prompt + _JSON_ONLY_INSTRUCTION,
            model=self.model,
            mcp_servers={},          # no tools for a judge
            allowed_tools=[],
            disallowed_tools=["WebSearch", "WebFetch", "web_search", "web_fetch"],
            can_use_tool=_deny_all_tools,
            max_turns=1,
            setting_sources=[],      # hermetic: no inherited settings/MCP/CLAUDE.md
        )
        final_text = None
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_content)
            async for message in client.receive_response():
                ti, to = _usage_tokens(message)
                self.total_input_tokens += ti
                self.total_output_tokens += to
                if isinstance(message, ResultMessage) and isinstance(
                    getattr(message, "result", None), str
                ):
                    final_text = message.result
        return final_text

    def call(self, system_prompt: str, user_content: str):
        self._calls += 1
        try:
            text = asyncio.run(
                asyncio.wait_for(self._acall(system_prompt, user_content),
                                 timeout=_AGENT_JUDGE_TIMEOUT)
            )
        except FatalJudgeError:
            raise
        except Exception as e:
            # A failure on the very first evaluation is almost always a setup
            # problem (CLI not authenticated, bad model) that will repeat on every
            # row — abort instead of scoring everything 0. Later failures are
            # treated as per-row (the pipeline records them as a failed eval).
            if self._calls == 1:
                raise FatalJudgeError(
                    "Claude CLI (agent SDK) call failed on the first evaluation — the CLI is "
                    "likely not authenticated (run `claude login`, or pass --use-api with "
                    f"ANTHROPIC_API_KEY set), or model {self.model!r} is unavailable. Detail: {e}"
                ) from e
            raise
        if not text:
            return None
        return _parse_eval_json(text)


def _model_available(model: str, available: List[str]) -> bool:
    """Ollama lists models by full tag (e.g. 'gemma3:latest'). Accept an exact
    match, or a bare name that resolves to a pulled '<name>:...' tag."""
    if model in available:
        return True
    if ":" not in model:
        return f"{model}:latest" in available or any(
            a.split(":", 1)[0] == model for a in available
        )
    return False


class OllamaJudge(JudgeBackend):
    """Local judge (e.g. Gemma, Qwen) via Ollama. Uses structured outputs
    (`format=<JSON schema>`) rather than tool calling, since not every local
    model supports tools — the same EVAL_TOOL schema constrains generation, so
    the returned shape matches the Anthropic judge exactly."""

    provider = "ollama"

    def __init__(self, model: str, host: str | None = None):
        super().__init__(model)
        if ollama is None:
            raise FatalJudgeError(
                "ollama package not installed. Install with: pip install ollama"
            )
        self.client = ollama.Client(host=host) if host else ollama.Client()
        # Verify the host is reachable and the model is pulled, so we fail fast
        # with an actionable message rather than erroring on every row.
        try:
            available = [m.model for m in self.client.list().models]
        except Exception as e:
            where = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            raise FatalJudgeError(f"Cannot reach Ollama at {where}: {e}") from e
        if not _model_available(model, available):
            raise FatalJudgeError(
                f"Model '{model}' not found on the Ollama host. Pull it with: "
                f"ollama pull {model}\nAvailable: {', '.join(available) or '(none)'}"
            )

    def call(self, system_prompt: str, user_content: str):
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            # Reuse the forced-tool-use schema as a structured-output grammar so
            # local models return the same object Claude does. Ollama grammar-
            # constrains generation to it; the clamp below stays as a guard.
            format=EVAL_TOOL["input_schema"],
            options={"temperature": 0},
        )
        self.total_input_tokens += getattr(response, "prompt_eval_count", 0) or 0
        self.total_output_tokens += getattr(response, "eval_count", 0) or 0
        content = (getattr(response.message, "content", "") or "").strip()
        if not content:
            return None
        try:
            return Evaluation.model_validate_json(content)
        except Exception:
            return None


def build_backend(provider: str, model: str, ollama_host: str | None = None,
                  use_api: bool = False) -> JudgeBackend:
    """Construct the judge backend for the chosen provider.

    For provider=anthropic the default is the Claude CLI (AgentSDKJudge, `claude
    login` auth); use_api=True selects the Anthropic Messages API (AnthropicJudge).
    """
    if provider == "anthropic":
        return AnthropicJudge(model) if use_api else AgentSDKJudge(model)
    if provider == "ollama":
        return OllamaJudge(model, host=ollama_host)
    raise FatalJudgeError(f"Unknown provider: {provider!r}")


class AnswerEvaluator:
    """Scores answer quality against an ideal answer using four criteria. The
    model call itself is delegated to a JudgeBackend (Anthropic or Ollama), so
    the scoring, clamping and error policy are identical across judges."""

    def __init__(self, backend: JudgeBackend):
        self.backend = backend
        self.model = backend.model
        self._consecutive_failures = 0   # streak of rows the judge couldn't score
        print(f"Initializing {backend.provider} evaluator with model: {backend.model}")

    @property
    def total_input_tokens(self) -> int:
        return self.backend.total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self.backend.total_output_tokens

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

        parsed = None
        reason = explanation = ""
        for attempt in range(1, JUDGE_MAX_ATTEMPTS + 1):
            try:
                parsed = self.backend.call(RUBRIC, user_content)
            except FatalJudgeError:
                # A run-aborting condition (bad key, missing model, dead host);
                # propagate so main() stops instead of zeroing every remaining row.
                raise
            except Exception as e:
                reason, explanation = str(e), f"Evaluation failed: {e}"
            else:
                if parsed is not None:
                    break
                reason = "No structured output in response (possible refusal)"
                explanation = "Judge returned no parseable evaluation"
            if attempt < JUDGE_MAX_ATTEMPTS:
                print(f"  judge attempt {attempt}/{JUDGE_MAX_ATTEMPTS} failed "
                      f"({reason}); retrying")
                time.sleep(JUDGE_RETRY_BACKOFF * attempt)

        if parsed is None:
            # This row could not be scored after every retry. Track the streak: a
            # lone failure is per-row (recorded as a 0-sentinel the analyzer drops),
            # but a sustained run of them means the judge is systemically down and
            # every remaining row would silently score 0 — abort loudly instead.
            self._consecutive_failures += 1
            if self._consecutive_failures >= ABORT_AFTER_CONSECUTIVE_FAILURES:
                raise FatalJudgeError(
                    f"Judge failed {self._consecutive_failures} rows in a row "
                    f"(last: {reason}). The judge is likely rate-limited/throttled, its "
                    "host is down, or the model is refusing — aborting so the run does not "
                    "complete as all-zeros. Wait and re-run, reduce concurrent Claude usage, "
                    "or switch judge (e.g. --use-api with ANTHROPIC_API_KEY, or --provider ollama)."
                )
            return _failed_eval(reason, explanation)

        self._consecutive_failures = 0   # a good score breaks the failure streak

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
  python add_llm_evaluation.py test_results.csv -o results-claude.csv
  python add_llm_evaluation.py test_results.csv --model claude-opus-4-7
  python add_llm_evaluation.py test_results.csv --model gemma3 -o results-gemma.csv
  python add_llm_evaluation.py test_results.csv --model qwen3  -o results-qwen.csv
  python add_llm_evaluation.py test_results.csv -o results.csv --runs 5
        """,
    )
    parser.add_argument("input_file", help="Input CSV file from automated_test_runner.py")
    parser.add_argument("-o", "--output", help="Output CSV file (default: overwrite input file)")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "ollama"],
        default=None,
        help="Judge provider. Default: inferred from --model (anthropic for "
        "claude-* models, ollama otherwise).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Judge model. Anthropic default: {DEFAULT_MODEL}. Required for "
        "--provider ollama (e.g. gemma3, qwen3).",
    )
    parser.add_argument(
        "--ollama-host",
        default=None,
        help="Ollama host URL (default: $OLLAMA_HOST or http://localhost:11434). "
        "Only used with --provider ollama.",
    )
    parser.add_argument(
        "--use-api",
        action="store_true",
        help="For the Claude judge, use the Anthropic Messages API (requires "
        "ANTHROPIC_API_KEY) instead of the default Claude CLI / agent SDK "
        "(which uses your `claude login`).",
    )
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

    # Resolve provider/model. Provider is inferred from the model name when not
    # given: claude-* -> anthropic, anything else -> ollama.
    provider = args.provider
    model = args.model
    if provider is None:
        provider = "anthropic" if (model is None or model.startswith("claude")) else "ollama"
    if model is None:
        if provider == "anthropic":
            model = DEFAULT_MODEL
        else:
            parser.error("--model is required for --provider ollama (e.g. --model gemma3)")

    try:
        backend = build_backend(provider, model, args.ollama_host, use_api=args.use_api)
        evaluator = AnswerEvaluator(backend)
    except FatalJudgeError as e:
        print(f"Error initializing evaluator: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing evaluator: {e}")
        if provider == "anthropic":
            if args.use_api:
                print("Set ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN / `ant auth login`).")
            else:
                print("The default Claude judge uses your `claude login` — run `claude login`, "
                      "or pass --use-api with ANTHROPIC_API_KEY set.")
        sys.exit(1)

    base_output = Path(args.output) if args.output else input_path
    output_paths = _versioned_paths(base_output, args.runs)

    start = time.time()
    for run_idx, out_path in enumerate(output_paths, start=1):
        if args.runs > 1 and not args.quiet:
            print(f"\n=== Evaluation run {run_idx}/{args.runs} ===")
        try:
            df = process_csv(input_path, out_path, evaluator, verbose=not args.quiet)
        except FatalJudgeError as e:
            print(f"Aborting run: {e}")
            sys.exit(1)
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
