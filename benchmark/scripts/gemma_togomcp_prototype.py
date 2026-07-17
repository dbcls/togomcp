#!/usr/bin/env python3
"""
Gemma + TogoMCP prototype — a standalone behavioral probe.

Purpose
-------
The production answer-collector (`automated_test_runner.py`) drives the
with-tools condition entirely through `claude-agent-sdk` (it spawns the Claude
Code CLI, which owns the MCP tool-calling loop). A *local* model like Gemma
cannot ride that path. This script re-implements that loop ourselves so we can
watch how a local model (default: gemma4 via Ollama) drives the live TogoMCP
tools — how it writes SPARQL, whether it recovers from tool errors, and whether
it follows the TogoMCP workflow idiom.

It is intentionally NOT wired into the benchmark pipeline. It is a prototype:
run it on a handful of questions and read the transcript.

What it does
------------
1. Connects to the live TogoMCP HTTP server as a first-class MCP client
   (`mcp` SDK, streamable-HTTP transport) and lists its ~35 tools.
2. Translates each MCP tool schema into Ollama's function-tool shape.
3. Runs an agentic loop per question:
       chat(gemma4, messages, tools) -> tool_calls? -> call_tool -> feed result back
   Tool errors are fed back as tool messages so we can observe recovery.
4. Writes two artifacts:
       - <out>.jsonl : full per-question transcript (every tool call + args +
                       result) — the deliverable for "see how it behaves".
       - <out>.csv   : one summary row per question (answer, tools, turns,
                       tokens) for eyeballing against Claude runs.

Requirements
------------
    pip install ollama mcp pyyaml          # all already in the dev extra
    ollama pull gemma4                     # or any tool-capable local model
    # Ollama server running ($OLLAMA_HOST or http://localhost:11434)

Usage
-----
    # A few questions, default gemma4, default live endpoint:
    python gemma_togomcp_prototype.py ../questions/question_001.yaml \
                                      ../questions/question_002.yaml

    # Try another local model / a different endpoint / cap questions:
    python gemma_togomcp_prototype.py ../questions/question_*.yaml \
        --model qwen3.6 --limit 5 -o gemma_run

    # Point at the local dev server instead of production:
    python gemma_togomcp_prototype.py ../questions/question_001.yaml \
        --mcp-url http://localhost:8000/mcp
"""

import argparse
import asyncio
import csv
import json
import sys
import time
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. pip install pyyaml")
    sys.exit(1)

try:
    import ollama
except ImportError:
    print("Error: ollama not installed. pip install ollama")
    sys.exit(1)

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("Error: mcp SDK not installed. pip install mcp")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Prompts.
#
# The REAL system prompt is loaded from the same config.yaml the production
# runner (automated_test_runner.py) uses — its `togomcp_system_prompt` carries
# the strong "REQUIRED FIRST ACTION: call TogoMCP_Usage_Guide()" + MANDATORY
# WORKFLOW instructions. Loading it here keeps this probe apples-to-apples with
# production instead of testing gemma4 against a weaker paraphrase. The constant
# below is only a fallback for when no config file is found.
# ---------------------------------------------------------------------------

DEFAULT_TOGOMCP_SYSTEM_PROMPT = (
    "You are an expert assistant answering biological and biomedical questions. "
    "You have access to biological databases through MCP tools. "
    "Use them when they would improve the accuracy or completeness of your answer. "
    "\n\n"
    "Recommended TogoMCP workflow: call TogoMCP_Usage_Guide first, then "
    "list_databases / find_databases to pick a database, get_MIE_file to learn its "
    "schema and example queries, get_graph_list to confirm the named graph, then "
    "run_sparql. Do not guess SPARQL blindly — read the MIE file first.\n\n"
    "Base your answers on retrieved data and write them to be:\n"
    "- COMPLETE: Include all necessary information from the databases\n"
    "- PRECISE: Include only relevant information that answers the question\n"
    "- NON-REDUNDANT: Synthesize information; don't repeat the same facts\n"
    "- READABLE: Use clear, fluent scientific prose with logical flow\n"
    "- DIRECT: State facts from databases without meta-references\n"
    "\n"
    "When you have gathered enough evidence, stop calling tools and write the final "
    "answer as a single well-formed paragraph."
)


def load_mcp_servers(config_path: Optional[str], single_url: str, use_all: bool) -> Dict[str, str]:
    """Return an ordered {server_name: url} map of MCP servers to connect to.

    Default (use_all=False): just {"togomcp": single_url} — the validated
    single-server behavior. With use_all=True, read the `mcp_servers` block from
    config.yaml (same one automated_test_runner.py uses) and connect to ALL of
    them (togomcp, pubmed, pubdictionaries, ols) for production parity. Only
    `type: http` servers are supported here (all four config servers are http).
    """
    if not use_all:
        return {"togomcp": single_url}
    servers: Dict[str, str] = {}
    if config_path and Path(config_path).exists():
        try:
            cfg = yaml.safe_load(Path(config_path).read_text()) or {}
        except yaml.YAMLError:
            cfg = {}
        for name, spec in (cfg.get("mcp_servers") or {}).items():
            if isinstance(spec, dict) and spec.get("url"):
                if spec.get("type", "http") != "http":
                    print(f"  ! skipping MCP server {name!r}: unsupported type "
                          f"{spec.get('type')!r} (only http)")
                    continue
                servers[name] = spec["url"]
    if not servers:
        print("  ! --all-config-servers set but no http mcp_servers found in "
              "config; falling back to single togomcp url")
        return {"togomcp": single_url}
    return servers


def load_system_prompt(config_path: Optional[str]) -> str:
    """Return the togomcp_system_prompt from config.yaml (same key the runner
    uses), falling back to the built-in default if the file or key is absent.

    Note: the config prompt references some tools by their claude-agent-sdk
    `mcp__<server>__<tool>` names (e.g. mcp__ols__*). In this local Ollama loop
    the TogoMCP tools are advertised under their BARE names (TogoMCP_Usage_Guide,
    find_databases, ...), which is exactly how the prompt's `TogoMCP_Usage_Guide()`
    / `find_databases()` / `get_MIE_file()` instructions spell them — so the
    load-bearing workflow directives resolve to real, callable tools.
    """
    if not config_path:
        return DEFAULT_TOGOMCP_SYSTEM_PROMPT
    p = Path(config_path)
    if not p.exists():
        print(f"  ! config not found: {config_path} — using built-in prompt")
        return DEFAULT_TOGOMCP_SYSTEM_PROMPT
    try:
        cfg = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        print(f"  ! config YAML error ({config_path}): {e} — using built-in prompt")
        return DEFAULT_TOGOMCP_SYSTEM_PROMPT
    prompt = cfg.get("togomcp_system_prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt
    print(f"  ! no togomcp_system_prompt in {config_path} — using built-in prompt")
    return DEFAULT_TOGOMCP_SYSTEM_PROMPT

FINAL_ANSWER_INSTRUCTION = """

Provide your answer as a single, well-formed paragraph that directly answers the question. Follow these guidelines:

1. COMPLETENESS: Include all necessary information to fully answer the question
2. PRECISION: Include only information directly relevant to answering the question
3. NO REPETITION: State each piece of information only once; avoid redundant phrasing
4. READABILITY: Write in clear, fluent prose with logical flow between sentences
5. DIRECT STYLE: State facts directly without meta-references like "According to research," "Studies show," or "The literature indicates"

Simply provide the factual answer as you would write an encyclopedia entry."""


# ---------------------------------------------------------------------------
# Question loading (mirrors automated_test_runner.load_questions)
# ---------------------------------------------------------------------------

def load_questions(files: List[str]) -> List[Dict]:
    questions: List[Dict] = []
    for fp in files:
        p = Path(fp)
        if not p.exists():
            print(f"  ! question file not found: {fp}")
            continue
        # coverage_tracker.yaml is not a question — skip it if globbed in.
        if p.name == "coverage_tracker.yaml":
            continue
        try:
            data = yaml.safe_load(p.read_text())
        except yaml.YAMLError as e:
            print(f"  ! YAML error in {fp}: {e}")
            continue
        if isinstance(data, list):
            questions.extend(data)
        elif isinstance(data, dict) and data.get("body"):
            questions.append(data)
    return questions


def build_question_prompt(q: Dict) -> str:
    """Assemble the user prompt, mirroring run_single_test's choice handling."""
    body = q.get("body", "")
    q_type = q.get("type", "unknown")
    choices = q.get("choices", [])
    if q_type == "choice" and choices:
        choices_text = "\n".join(f"  - {c}" for c in choices)
        body = f"{body}\n\nChoose one of the following options:\n{choices_text}"
    if q_type == "choice":
        instruction = (
            "\n\nState which option or options are correct and briefly explain "
            "why in one paragraph."
        )
    else:
        instruction = FINAL_ANSWER_INSTRUCTION
    return body + instruction


# ---------------------------------------------------------------------------
# MCP <-> Ollama bridging
# ---------------------------------------------------------------------------

def mcp_tools_to_ollama(mcp_tools, hide_substrings: List[str], prefix: str = "") -> tuple:
    """Translate one MCP server's tool definitions into Ollama's function-tool
    schema. Returns (ollama_tools, hidden_names, name_pairs) where name_pairs is
    a list of (advertised_name, original_name) so the caller can build a routing
    table back to the owning session.

    `prefix`: when connecting to MULTIPLE servers, advertise each tool as
    `mcp__<server>__<tool>` (matching production's naming and the config system
    prompt, which references mcp__ols__* / mcp__pubmed__*) to avoid cross-server
    name collisions. Empty prefix (single-server mode) keeps BARE names, which is
    what the validated single-server runs used — so that path is unchanged.

    `hide_substrings`: tool names containing any of these substrings are NOT
    advertised (checked against the ORIGINAL bare name). Structural intervention
    #2 — a local model that ignores tool-selection steering can't take the
    shallow keyword-search shortcut if the shortcut tool is never offered.
    """
    out, hidden, name_pairs = [], [], []
    for t in mcp_tools:
        if any(sub and sub in t.name for sub in hide_substrings):
            hidden.append(t.name)
            continue
        advertised = f"{prefix}{t.name}" if prefix else t.name
        params = t.inputSchema or {"type": "object", "properties": {}}
        out.append({
            "type": "function",
            "function": {
                "name": advertised,
                "description": (t.description or "")[:1024],
                "parameters": params,
            },
        })
        name_pairs.append((advertised, t.name))
    return out, hidden, name_pairs


def flatten_tool_result(result, max_chars: int) -> str:
    """Extract text from an MCP CallToolResult, truncated for local-model context."""
    parts: List[str] = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(block))
    text = "\n".join(parts) if parts else "(tool returned no content)"
    if getattr(result, "isError", False):
        text = "ERROR: " + text
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"
    return text


def message_to_dict(msg) -> Dict[str, Any]:
    """Best-effort serialization of an Ollama Message for the transcript."""
    for attr in ("model_dump", "dict"):
        fn = getattr(msg, attr, None)
        if callable(fn):
            try:
                dumped = fn()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
    return {"role": getattr(msg, "role", "assistant"),
            "content": getattr(msg, "content", "")}


# ---------------------------------------------------------------------------
# The agentic loop
# ---------------------------------------------------------------------------

async def answer_one(
    client: "ollama.AsyncClient",
    call_tool,                       # async (name, args) -> flattened str; routes to owning MCP server
    ollama_tools: List[Dict[str, Any]],
    model: str,
    system_prompt: str,
    question: Dict,
    max_turns: int,
    max_tool_chars: int,
    max_repeat: int,
    num_ctx: int,
) -> Dict[str, Any]:
    """Drive one question through the gemma+tools loop. Returns a result dict."""
    prompt = build_question_prompt(question)
    messages: List[Any] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    transcript: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    tool_uses: List[str] = []
    in_tokens = 0
    out_tokens = 0
    final_text: Optional[str] = None
    turns_used = 0
    # Per-turn prompt token count (Ollama prompt_eval_count). This is the actual
    # context size fed to the model each turn; the max is the peak. If it pins
    # near num_ctx, Ollama was truncating (dropping the front) during reasoning.
    per_turn_prompt_tokens: List[int] = []
    # Loop guard (structural intervention #3): count identical (tool, args)
    # signatures. gemma4 degenerates into repeating the same call verbatim
    # (the hallucinated BRCA1 loop); once a signature is seen `max_repeat`
    # times we stop executing it and feed back a nudge instead.
    call_sig_counts: Dict[str, int] = {}

    start = time.time()

    for turn in range(1, max_turns + 1):
        turns_used = turn
        resp = await client.chat(
            model=model,
            messages=messages,
            tools=ollama_tools,
            # num_ctx is critical: Ollama's default (4096) silently truncates
            # from the FRONT once system prompt + tool schemas + tool results
            # exceed it, dropping the question and making the model emit a
            # generic capability menu instead of an answer. gemma4 supports 128k.
            options={"temperature": 0, "num_ctx": num_ctx},
        )
        turn_prompt_tok = getattr(resp, "prompt_eval_count", 0) or 0
        per_turn_prompt_tokens.append(turn_prompt_tok)
        in_tokens += turn_prompt_tok
        out_tokens += getattr(resp, "eval_count", 0) or 0

        msg = resp.message
        messages.append(msg)  # AsyncClient accepts Message objects back
        transcript.append(message_to_dict(msg))

        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            final_text = (getattr(msg, "content", "") or "").strip()
            break

        # Execute every requested tool call, feeding results (and errors) back.
        for call in tool_calls:
            name = call.function.name
            args = call.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            tool_uses.append(name)
            print(f"      → {name}({json.dumps(args, default=str)[:140]})")

            sig = f"{name}::{json.dumps(args, sort_keys=True, default=str)}"
            call_sig_counts[sig] = call_sig_counts.get(sig, 0) + 1

            if call_sig_counts[sig] > max_repeat:
                # Repeated the exact same call too many times — refuse to execute
                # it again and push the model to change course or conclude.
                content = (
                    f"LOOP GUARD: you have already called {name} with these exact "
                    f"arguments {call_sig_counts[sig]} times. This call is blocked. "
                    "Do NOT repeat it. Either try a genuinely different tool/query "
                    "(e.g. get_MIE_file then run_sparql on the clinvar database), or "
                    "if you have enough evidence, STOP calling tools and write your "
                    "final answer now."
                )
                print(f"        ⚠ loop guard blocked repeat #{call_sig_counts[sig]}")
            else:
                try:
                    content = await call_tool(name, args or {}, max_tool_chars)
                except Exception as e:
                    content = f"ERROR calling tool {name!r}: {type(e).__name__}: {e}"

            tool_msg = {"role": "tool", "tool_name": name, "content": content}
            messages.append(tool_msg)
            transcript.append({
                "role": "tool", "tool_name": name,
                "args": args, "content": content,
            })

    elapsed = time.time() - start
    success = bool(final_text)
    if not success and final_text is None:
        final_text = (
            f"[NO FINAL ANSWER: model kept calling tools for all {max_turns} turns]"
        )

    return {
        "question_id": question.get("id", "?"),
        "question_type": question.get("type", "unknown"),
        "question": question.get("body", ""),
        "ideal_answer": question.get("ideal_answer", ""),
        "exact_answer": question.get("exact_answer", ""),
        "gemma_success": success,
        "gemma_answer": final_text,
        "gemma_turns": turns_used,
        "gemma_tool_calls": len(tool_uses),
        "tools_used": ", ".join(tool_uses),
        "gemma_input_tokens": in_tokens,
        "gemma_output_tokens": out_tokens,
        "gemma_peak_prompt_tokens": max(per_turn_prompt_tokens or [0]),
        "gemma_per_turn_prompt_tokens": per_turn_prompt_tokens,
        "gemma_time": round(elapsed, 2),
        "_transcript": transcript,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def connect_servers(stack: AsyncExitStack, servers: Dict[str, str],
                          hide_substrings: List[str], multi: bool, quiet: bool = False):
    """Connect to each MCP server into `stack`; return
    (sessions{name->session}, ollama_tools, hidden, static_routes{advertised->(name,orig)}).
    A per-server failure is logged and skipped (graceful degradation), so one
    unreachable/auth-gated server never aborts the whole run.
    """
    sessions: Dict[str, ClientSession] = {}
    ollama_tools: List[Dict[str, Any]] = []
    hidden: List[str] = []
    static_routes: Dict[str, tuple] = {}
    for sname, surl in servers.items():
        try:
            read, write, _sid = await stack.enter_async_context(streamablehttp_client(surl))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            sessions[sname] = session
            stools = (await session.list_tools()).tools
            prefix = f"mcp__{sname}__" if multi else ""
            s_ollama, s_hidden, pairs = mcp_tools_to_ollama(stools, hide_substrings, prefix)
            ollama_tools.extend(s_ollama)
            hidden.extend(s_hidden)
            for advertised, original in pairs:
                static_routes[advertised] = (sname, original)
            if not quiet:
                print(f"  ✓ {sname}: {len(s_ollama)} tools ({len(s_hidden)} hidden)")
        except Exception as e:
            if not quiet:
                print(f"  ✗ {sname} ({surl}): {type(e).__name__}: {str(e)[:120]}")
    return sessions, ollama_tools, hidden, static_routes


async def run(args: argparse.Namespace) -> int:
    questions = load_questions(args.question_files)
    if args.limit:
        questions = questions[: args.limit]
    if not questions:
        print("✗ No questions loaded.")
        return 1

    # Bind a guaranteed-str model name (argparse default is "gemma4", never
    # None, but the type checker can't see that through Namespace).
    model_name: str = args.model or "gemma4"

    # Fail fast if the model isn't pulled, with an actionable message.
    probe = ollama.Client(host=args.ollama_host or None)
    try:
        available = [m.model for m in probe.list().models if m.model]
    except Exception as e:
        where = args.ollama_host or "http://localhost:11434"
        print(f"✗ Cannot reach Ollama at {where}: {e}")
        return 1
    if model_name not in available and f"{model_name}:latest" not in available \
            and not any(a.split(":", 1)[0] == model_name for a in available):
        print(f"✗ Model '{model_name}' not pulled. Try: ollama pull {model_name}")
        print(f"  Available: {', '.join(available) or '(none)'}")
        return 1

    client = ollama.AsyncClient(host=args.ollama_host or None)

    base_system_prompt = load_system_prompt(args.config)
    hide_substrings = [s.strip() for s in args.hide_tools.split(",") if s.strip()]
    prompt_src = args.config if (args.config and Path(args.config).exists()
                                 and base_system_prompt is not DEFAULT_TOGOMCP_SYSTEM_PROMPT) \
        else "built-in default"
    servers = load_mcp_servers(args.config, args.mcp_url, args.all_config_servers)
    multi = len(servers) > 1

    print("=" * 70)
    print("Gemma + TogoMCP prototype")
    print("=" * 70)
    print(f"Model:      {model_name}")
    print(f"MCP servers:{', '.join(f'{n}={u}' for n, u in servers.items())}")
    print(f"Questions:  {len(questions)}")
    print(f"Prompt:     {prompt_src} ({len(base_system_prompt)} chars)")
    print(f"Force-guide:{args.force_guide}   |   Hide tools: {hide_substrings or '(none)'}")
    print(f"Max turns:  {args.max_turns}   |   loop-guard repeat cap: {args.max_repeat} "
          f"|   tool-result cap: {args.max_tool_chars} chars")
    print(f"num_ctx:    {args.num_ctx} (Ollama default is 4096)")
    print("=" * 70)

    results: List[Dict[str, Any]] = []
    jsonl_path = f"{args.output}.jsonl"
    csv_path = f"{args.output}.csv"

    # SETUP (once): connect all servers to enumerate tools + build the static
    # routing table (advertised_name -> (server_name, original_name)) and
    # optionally pre-load the usage guide. Then close these connections.
    system_prompt = base_system_prompt
    async with AsyncExitStack() as setup_stack:
        sessions, ollama_tools, hidden, static_routes = await connect_servers(
            setup_stack, servers, hide_substrings, multi)
        if not ollama_tools:
            print("✗ No MCP tools available from any server. Aborting.")
            return 1
        # Only re-connect servers that actually came up.
        ok_servers = {n: servers[n] for n in sessions}

        # Structural intervention #1: pre-load the usage guide into the system
        # prompt so it is guaranteed present (turn 0).
        if args.force_guide:
            guide_name = "mcp__togomcp__TogoMCP_Usage_Guide" if multi else "TogoMCP_Usage_Guide"
            rt = static_routes.get(guide_name)
            if rt is not None:
                try:
                    sname, orig = rt
                    gr = await sessions[sname].call_tool(
                        orig, {}, read_timeout_seconds=timedelta(seconds=60))
                    guide_text = flatten_tool_result(gr, args.guide_chars)
                    system_prompt = (
                        base_system_prompt
                        + "\n\n## PRE-LOADED TogoMCP USAGE GUIDE "
                          "(already fetched for you — do NOT call TogoMCP_Usage_Guide)\n\n"
                        + guide_text
                    )
                    print(f"Pre-loaded TogoMCP_Usage_Guide ({len(guide_text)} chars) "
                          "into system prompt.")
                except Exception as e:
                    print(f"  ! could not pre-load usage guide: {e}")

    print(f"Connected. {len(ollama_tools)} MCP tools advertised to {model_name} "
          f"across {len(ok_servers)} server(s) "
          f"({len(hidden)} hidden: {', '.join(hidden) or 'none'}).")
    print("Reconnecting fresh per question (robust to mid-run network drops).\n")

    # PER-QUESTION: open fresh MCP connections for each question so a dropped
    # session (e.g. httpx.ConnectTimeout) fails only THAT question — the next
    # reconnects — instead of crashing the whole run. Also gives transport-level
    # fresh isolation per question, matching the production runner's intent.
    with open(jsonl_path, "w", encoding="utf-8") as jf:
        for i, q in enumerate(questions, 1):
            qid = q.get("id", f"q{i}")
            print(f"[{i}/{len(questions)}] {qid} ({q.get('type','?')})")
            print(f"    {q.get('body','')[:90]}")

            def _fail(msg: str) -> Dict[str, Any]:
                return {
                    "question_id": qid,
                    "question_type": q.get("type", "unknown"),
                    "question": q.get("body", ""),
                    "ideal_answer": q.get("ideal_answer", ""),
                    "exact_answer": q.get("exact_answer", ""),
                    "gemma_success": False,
                    "gemma_answer": msg,
                    "gemma_turns": 0, "gemma_tool_calls": 0, "tools_used": "",
                    "gemma_input_tokens": 0, "gemma_output_tokens": 0,
                    "gemma_peak_prompt_tokens": 0, "gemma_per_turn_prompt_tokens": [],
                    "gemma_time": 0.0, "_transcript": [],
                }

            try:
                async with AsyncExitStack() as qstack:
                    q_sessions, _, _, _ = await connect_servers(
                        qstack, ok_servers, hide_substrings, multi, quiet=True)

                    async def call_tool(name: str, args_dict: dict, max_chars: int,
                                        _sessions=q_sessions) -> str:
                        """Route a tool call to its owning (per-question) session."""
                        route = static_routes.get(name)
                        if route is None:
                            return (f"ERROR: unknown tool {name!r}. Only the advertised "
                                    "MCP tools are available.")
                        sname, original = route
                        sess = _sessions.get(sname)
                        if sess is None:
                            return (f"ERROR: MCP server {sname!r} is not connected for "
                                    "this question; try a tool from another server.")
                        result = await sess.call_tool(
                            original, args_dict or {},
                            read_timeout_seconds=timedelta(seconds=90))
                        return flatten_tool_result(result, max_chars)

                    res = await asyncio.wait_for(
                        answer_one(
                            client, call_tool, ollama_tools, model_name,
                            system_prompt, q,
                            args.max_turns, args.max_tool_chars,
                            args.max_repeat, args.num_ctx,
                        ),
                        timeout=args.timeout,
                    )
            except asyncio.TimeoutError:
                res = _fail(f"[TIMEOUT after {args.timeout}s]")
                res["gemma_time"] = float(args.timeout)
            except Exception as e:
                # Connection/transport failure for THIS question only — record
                # and move on; the next question reconnects.
                res = _fail(f"[CONNECTION/RUN ERROR: {type(e).__name__}: {str(e)[:200]}]")

            jf.write(json.dumps(res, default=str) + "\n")
            jf.flush()
            results.append(res)

            mark = "✓" if res["gemma_success"] else "✗"
            print(f"    {mark} {res['gemma_turns']} turns, "
                  f"{res['gemma_tool_calls']} tool calls, "
                  f"{res['gemma_output_tokens']}↓ tok, {res['gemma_time']}s")
            print(f"    answer: {str(res['gemma_answer'])[:120]}\n")

    # Summary CSV (drop the bulky transcript column).
    fieldnames = [
        "question_id", "question_type", "question", "ideal_answer", "exact_answer",
        "gemma_success", "gemma_answer", "gemma_turns", "gemma_tool_calls",
        "tools_used", "gemma_input_tokens", "gemma_output_tokens", "gemma_time",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        w = csv.DictWriter(cf, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    ok = sum(1 for r in results if r["gemma_success"])
    tot_tool = sum(r["gemma_tool_calls"] for r in results)
    print("=" * 70)
    print(f"Done. {ok}/{len(results)} produced a final answer. "
          f"{tot_tool} total tool calls.")
    print(f"  Transcript (full trace): {jsonl_path}")
    print(f"  Summary CSV:             {csv_path}")
    print("=" * 70)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Gemma + TogoMCP prototype (standalone behavioral probe).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("question_files", nargs="+", help="Question YAML file(s).")
    ap.add_argument("--model", default="gemma4",
                    help="Ollama model tag (default: gemma4). Must support tools.")
    ap.add_argument("-c", "--config",
                    default=str(Path(__file__).parent / "config.yaml"),
                    help="Config YAML to read togomcp_system_prompt from "
                         "(default: config.yaml beside this script; the same "
                         "prompt the production runner uses).")
    ap.add_argument("--mcp-url", default="https://togomcp.rdfportal.org/mcp",
                    help="Single TogoMCP MCP endpoint (default: production). Used "
                         "unless --all-config-servers is set.")
    ap.add_argument("--all-config-servers", action="store_true",
                    help="Connect to ALL http mcp_servers in the config file "
                         "(togomcp + pubmed + pubdictionaries + ols) for production "
                         "parity with automated_test_runner.py, instead of just "
                         "--mcp-url. Tools are namespaced mcp__<server>__<tool>.")
    ap.add_argument("--ollama-host", default="",
                    help="Ollama host URL (default: $OLLAMA_HOST or localhost:11434).")
    ap.add_argument("-o", "--output", default="gemma_togomcp",
                    help="Output basename; writes <name>.jsonl and <name>.csv.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Only run the first N questions (0 = all).")
    ap.add_argument("--max-turns", type=int, default=10,
                    help="Max chat<->tool rounds per question (default: 10).")
    ap.add_argument("--force-guide", action=argparse.BooleanOptionalAction, default=True,
                    help="Pre-load TogoMCP_Usage_Guide contents into the system "
                         "prompt (structural intervention #1). --no-force-guide to disable.")
    ap.add_argument("--guide-chars", type=int, default=6000,
                    help="Truncate the pre-loaded usage guide to this many chars (default: 6000).")
    ap.add_argument("--hide-tools", default="togovar_search_",
                    help="Comma-separated substrings; tools whose names contain any "
                         "are NOT advertised to the model (structural intervention #2). "
                         "Default hides the togovar_search_* keyword shortcuts. "
                         "Pass '' to advertise all tools.")
    ap.add_argument("--max-repeat", type=int, default=2,
                    help="Loop guard (intervention #3): block a tool call once its "
                         "exact (name, args) signature has been used this many times "
                         "(default: 2).")
    ap.add_argument("--num-ctx", type=int, default=16384,
                    help="Ollama context window (num_ctx). Ollama's default of 4096 "
                         "silently truncates the system prompt + question once tool "
                         "schemas/results pile up, causing capability-menu non-answers. "
                         "gemma4 supports up to 131072; raise if RAM allows (default: 16384).")
    ap.add_argument("--max-tool-chars", type=int, default=8000,
                    help="Truncate each tool result to this many chars (default: 8000).")
    ap.add_argument("--timeout", type=int, default=600,
                    help="Per-question wall-clock timeout in seconds (default: 600).")
    args = ap.parse_args()

    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n⚠ interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
