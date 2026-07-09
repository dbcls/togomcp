#!/usr/bin/env python3
"""Orchestrate the MIE-subcomponent ablation sweep.

For each condition (baseline + one leave-one-out per MIE section) this:
  1. boots a local TogoMCP HTTP server whose get_MIE_file serves that
     condition's section-stripped corpus (via TOGOMCP_MIE_DIR + _serve.py);
  2. renders a benchmark config from the canonical benchmark/scripts/config.yaml
     with ONLY the togomcp server URL redirected to the local server;
  3. runs automated_test_runner.py over the pilot questions -> answers CSV;
  4. runs add_llm_evaluation.py to LLM-judge the answers -> scored CSV;
  5. tears the server down.

It reuses automated_test_runner.py and add_llm_evaluation.py unchanged (as
subprocesses) and is idempotent: a condition whose scored CSV already exists is
skipped (delete it or pass --force to re-run), so a partial sweep resumes safely.

Prerequisites: `uv sync`; ANTHROPIC_API_KEY (answering + default judge);
NCBI_API_KEY (local server's NCBI tools). Generate inputs first:
    python ablate_mie.py
    python select_pilot.py

Usage:
    python run_ablation.py                              # full sweep, pilot subset
    python run_ablation.py --conditions baseline,ablate_shape_expressions
    python run_ablation.py --questions q1.yaml q2.yaml  # ad-hoc subset
    python run_ablation.py --model claude-sonnet-4-5-20250929 --judge-model claude-opus-4-8
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from ablate_mie import CANONICAL_SECTIONS  # single source of truth for the 11

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SCRIPTS_DIR = REPO_ROOT / "benchmark" / "scripts"
DEFAULT_BASE_CONFIG = SCRIPTS_DIR / "config.yaml"
RUNNER = SCRIPTS_DIR / "automated_test_runner.py"
EVALUATOR = SCRIPTS_DIR / "add_llm_evaluation.py"
VARIANTS_DIR = HERE / "mie_variants"
PILOT_FILE = HERE / "pilot_questions.txt"
RESULTS_DIR = HERE / "results"
RENDERED_DIR = RESULTS_DIR / "rendered_configs"

ALL_CONDITIONS = ["baseline"] + [f"ablate_{s}" for s in CANONICAL_SECTIONS]
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def wait_ready(port: int, proc: subprocess.Popen, timeout: float = 90.0) -> bool:
    """Poll GET /mcp until the server answers (up), the process dies, or timeout."""
    url = f"http://127.0.0.1:{port}/mcp"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False  # server exited before ever serving — don't wait out the clock
        try:
            urllib.request.urlopen(  # noqa: S310 (loopback only)
                urllib.request.Request(url, headers={"Accept": "text/event-stream"}),
                timeout=5,
            )
            return True
        except urllib.error.HTTPError:
            return True  # 4xx == server is up and routing
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(1.0)
    return False


# Modules each spawned subprocess needs, all under the same interpreter.
SERVER_IMPORTS = {
    "togo_mcp": "the TogoMCP server (_serve.py) — run `uv sync` in the repo root",
    "fastmcp": "the TogoMCP server (_serve.py) — run `uv sync` in the repo root",
}
BENCH_IMPORTS = {
    "claude_agent_sdk": "automated_test_runner.py — `pip install claude-agent-sdk`",
    "pandas": "add_llm_evaluation.py — `pip install pandas`",
    "anthropic": "add_llm_evaluation.py — `pip install anthropic`",
}


def preflight(python: str, required: dict[str, str]) -> None:
    """Fail fast (with install hints) if `python` can't import what the subprocesses need."""
    missing = []
    for mod, why in required.items():
        r = subprocess.run([python, "-c", f"import {mod}"], capture_output=True)
        if r.returncode != 0:
            missing.append((mod, why))
    if missing:
        lines = [f"Interpreter cannot import required modules:\n  {python}\n"]
        for mod, why in missing:
            lines.append(f"  - {mod:18s} needed by {why}")
        lines.append(
            "\nRun the sweep with an interpreter that has BOTH the TogoMCP package and the "
            "benchmark deps. Typically: activate the repo .venv and\n"
            "    pip install claude-agent-sdk pandas anthropic\n"
            "then re-run. (Pass --python to point at a specific interpreter.)"
        )
        raise SystemExit("\n".join(lines))


def render_config(base_config: Path, port: int, out_path: Path) -> None:
    """Clone the base benchmark config, redirecting only the togomcp server URL."""
    cfg = yaml.safe_load(base_config.read_text(encoding="utf-8"))
    servers = cfg.setdefault("mcp_servers", {})
    if "togomcp" not in servers:
        raise SystemExit(f"base config {base_config} has no mcp_servers.togomcp to redirect")
    servers["togomcp"] = {"type": "http", "url": f"http://127.0.0.1:{port}/mcp"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_pilot(explicit: list[str] | None) -> list[str]:
    if explicit:
        return explicit
    if not PILOT_FILE.exists():
        raise SystemExit(f"{PILOT_FILE} missing — run select_pilot.py first (or pass --questions)")
    files = [ln.strip() for ln in PILOT_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not files:
        raise SystemExit(f"{PILOT_FILE} is empty")
    return files


def _server_log_tail(log_path: Path, n: int = 15) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(no server log captured)"
    tail = lines[-n:] if lines else ["(server produced no output)"]
    return "\n".join("    " + ln for ln in tail)


def run_condition(cond: str, questions: list[str], base_config: Path, port: int,
                  model: str, judge_model: str | None, force: bool, dry_run: bool,
                  python: str) -> str:
    scored = RESULTS_DIR / f"{cond}-scored.csv"
    answers = RESULTS_DIR / f"{cond}-answers.csv"
    if scored.exists() and not force:
        print(f"[{cond}] scored CSV exists — skipping (delete it or --force to re-run)")
        return "skipped"

    variant_dir = VARIANTS_DIR / cond
    if not variant_dir.is_dir():
        raise SystemExit(f"[{cond}] variant dir missing: {variant_dir} — run ablate_mie.py")

    cfg_path = RENDERED_DIR / f"{cond}.config.yaml"
    render_config(base_config, port, cfg_path)

    env = dict(os.environ)
    env["TOGOMCP_MIE_DIR"] = str(variant_dir)
    env["ABLATION_PORT"] = str(port)

    print(f"[{cond}] booting local server on :{port} (MIE={variant_dir.name})")
    server_log = RESULTS_DIR / f"{cond}-server.log"
    log_fh = server_log.open("w", encoding="utf-8")
    server = subprocess.Popen(
        [python, str(HERE / "_serve.py")], env=env,
        stdout=log_fh, stderr=subprocess.STDOUT,
    )
    try:
        if not wait_ready(port, server):
            died = server.poll() is not None
            why = "server process exited during startup" if died else f"timed out on :{port}"
            raise SystemExit(
                f"[{cond}] server failed to become ready ({why}). Last server output:\n"
                f"{_server_log_tail(server_log)}\n"
                f"  (full log: {server_log})"
            )
        if dry_run:
            print(f"[{cond}] DRY-RUN: server ready; would run runner over "
                  f"{len(questions)} questions with config {cfg_path.name}")
            return "dry-run"
        print(f"[{cond}] running benchmark over {len(questions)} questions (model={model})")
        subprocess.run(
            [python, str(RUNNER), *questions,
             "-c", str(cfg_path), "--model", model, "-o", str(answers)],
            check=True, cwd=str(SCRIPTS_DIR),
        )
    finally:
        log_fh.close()
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        print(f"[{cond}] server stopped")

    print(f"[{cond}] LLM-judging answers -> {scored.name}")
    eval_cmd = [python, str(EVALUATOR), str(answers), "-o", str(scored)]
    if judge_model:
        eval_cmd += ["--model", judge_model]
    # Evaluator inherits the env: the Claude judge (add_llm_evaluation.py default)
    # authenticates via `claude login`, same as the runner. Do not inject a key.
    subprocess.run(eval_cmd, check=True, cwd=str(SCRIPTS_DIR))
    return "done"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conditions", default=",".join(ALL_CONDITIONS),
                    help="comma-separated conditions (default: baseline + all 11 ablations)")
    ap.add_argument("--questions", nargs="+", default=None,
                    help="explicit question YAML paths (default: pilot_questions.txt)")
    ap.add_argument("--base-config", default=str(DEFAULT_BASE_CONFIG),
                    help=f"benchmark config to clone (default: {DEFAULT_BASE_CONFIG})")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="answering model")
    ap.add_argument("--judge-model", default=None,
                    help="LLM-judge model (default: add_llm_evaluation.py's own default)")
    ap.add_argument("--port", type=int, default=8971, help="loopback port for the local server")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the server + benchmark subprocesses "
                         "(default: this one; must import togo_mcp, claude_agent_sdk, pandas, anthropic)")
    ap.add_argument("--skip-preflight", action="store_true",
                    help="skip the up-front dependency check")
    ap.add_argument("--force", action="store_true", help="re-run conditions even if scored CSV exists")
    ap.add_argument("--dry-run", action="store_true",
                    help="boot the server + render config + check readiness, but skip the "
                         "runner/evaluator (validates orchestration without API cost)")
    args = ap.parse_args()

    for tool in (RUNNER, EVALUATOR):
        if not tool.exists():
            raise SystemExit(f"missing dependency script: {tool}")

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in ALL_CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown condition(s): {', '.join(unknown)}\nvalid: {', '.join(ALL_CONDITIONS)}")

    base_config = Path(args.base_config)
    if not base_config.exists():
        raise SystemExit(f"base config not found: {base_config}")

    questions = load_pilot(args.questions)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_preflight:
        required = dict(SERVER_IMPORTS)
        if not args.dry_run:
            required.update(BENCH_IMPORTS)
        preflight(args.python, required)

    print(f"Ablation sweep: {len(conditions)} conditions x {len(questions)} questions")
    print(f"  model={args.model}  judge={args.judge_model or '(eval default)'}  "
          f"port={args.port}  python={args.python}\n")

    summary: dict[str, str] = {}
    started = time.monotonic()
    for cond in conditions:
        try:
            summary[cond] = run_condition(cond, questions, base_config, args.port,
                                          args.model, args.judge_model, args.force,
                                          args.dry_run, args.python)
        except SystemExit as e:
            print(f"[{cond}] ABORTED: {e}", file=sys.stderr)
            summary[cond] = "error"
        print()

    mins = (time.monotonic() - started) / 60
    print("=" * 60)
    print(f"Sweep complete in {mins:.1f} min")
    for cond in conditions:
        print(f"  {cond:34s} {summary.get(cond, '?')}")
    print(f"\nScored CSVs in {RESULTS_DIR}")
    print("Next: python ablation_analysis.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
