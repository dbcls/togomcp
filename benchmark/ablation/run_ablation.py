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
    python run_ablation.py --runs 5                      # 5 replicates/question, averaged

With --runs N (>1) each question is answered + judged N times per condition; the
replicates land in <cond>-scored-vR.csv and are averaged per question_id into the
flat <cond>-scored.csv that ablation_analysis.py consumes. Averaging R runs
divides the judge-jitter component of the paired-delta variance by R, which is the
lever that brings the pilot into a usable-power regime (see select_pilot.py).
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from statistics import mean

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


# Judge-criterion columns (both baseline_* and togomcp_*) where a 0 is the
# failed-judge sentinel add_llm_evaluation writes — real per-criterion scores clamp
# to 1–5, totals to 4–20. Matches the metrics ablation_analysis.load_scores nulls
# out on 0. NOT the *_success 0/1 flags or *_tokens/*_cost, whose 0 is a real value.
_SCORE_SUFFIXES = ("_recall", "_precision", "_repetition", "_readability", "_total_score")


def _is_score_col(col: str) -> bool:
    return col.endswith(_SCORE_SUFFIXES)


def _is_number(x: str | None) -> bool:
    if x is None or x == "":
        return False
    try:
        float(x)
        return True
    except ValueError:
        return False


def merge_scored(run_paths: list[Path], out_path: Path) -> None:
    """Average per-question scores across replicate scored CSVs into one CSV.

    Numeric columns are averaged per question_id; text columns are copied from the
    first replicate. For judge-criterion columns (recall/precision/repetition/
    readability/total_score, both baseline_* and togomcp_*) a 0 is the failed-judge
    sentinel add_llm_evaluation writes on a crashed call (real totals are 4–20), so
    zeros are treated as missing in the average — a score is 0 only when EVERY
    replicate failed. This matches ablation_analysis.load_scores, so the averaged
    CSV feeds that tool unchanged. Other numerics (``*_success`` flags, tokens,
    cost) average normally, zeros included. An ``n_runs`` column records how many
    replicates contributed to each row.
    """
    present = [p for p in run_paths if p.exists()]
    if not present:
        raise SystemExit(f"merge: no replicate scored CSVs exist for {out_path.name}")

    fieldnames: list[str] = []
    order: list[str] = []
    rows_by_qid: dict[str, list[dict]] = {}
    for p in present:
        with p.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if not fieldnames:
                fieldnames = list(reader.fieldnames or [])
            for row in reader:
                qid = row.get("question_id")
                if not qid:
                    continue
                if qid not in rows_by_qid:
                    order.append(qid)
                rows_by_qid.setdefault(qid, []).append(row)

    # A column is numeric only if every non-blank value across all replicates parses
    # as a float (so free-text answer columns are never averaged).
    numeric_cols = []
    for col in fieldnames:
        seen_any = False
        all_num = True
        for rows in rows_by_qid.values():
            for row in rows:
                v = row.get(col, "")
                if v in (None, ""):
                    continue
                seen_any = True
                if not _is_number(v):
                    all_num = False
                    break
            if not all_num:
                break
        if seen_any and all_num:
            numeric_cols.append(col)

    merged = []
    for qid in order:
        rows = rows_by_qid[qid]
        rec = dict(rows[0])
        rec["n_runs"] = len(rows)
        for col in numeric_cols:
            nums = [float(row[col]) for row in rows if _is_number(row.get(col, ""))]
            if _is_score_col(col):
                nz = [v for v in nums if v != 0]  # drop failed-judge sentinels
                rec[col] = f"{mean(nz):.4g}" if nz else "0"
            else:
                rec[col] = f"{mean(nums):.6g}" if nums else ""
        merged.append(rec)

    out_fields = list(fieldnames)
    if "n_runs" not in out_fields:
        out_fields.append("n_runs")
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)


def _server_log_tail(log_path: Path, n: int = 15) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(no server log captured)"
    tail = lines[-n:] if lines else ["(server produced no output)"]
    return "\n".join("    " + ln for ln in tail)


def run_condition(cond: str, questions: list[str], base_config: Path, port: int,
                  model: str, judge_model: str | None, force: bool, dry_run: bool,
                  python: str, runs: int = 1) -> str:
    final_scored = RESULTS_DIR / f"{cond}-scored.csv"
    if final_scored.exists() and not force:
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

    # runs==1 keeps the flat <cond>-answers/scored.csv names (backward compatible);
    # runs>1 writes -vR replicates and averages them into the flat <cond>-scored.csv.
    def run_paths(r: int) -> tuple[Path, Path]:
        if runs == 1:
            return (RESULTS_DIR / f"{cond}-answers.csv",
                    RESULTS_DIR / f"{cond}-scored.csv")
        return (RESULTS_DIR / f"{cond}-answers-v{r}.csv",
                RESULTS_DIR / f"{cond}-scored-v{r}.csv")

    plan = []
    for r in range(1, runs + 1):
        answers, scored = run_paths(r)
        done = scored.exists() and not force          # this replicate already judged
        need_answer = (not done) and (force or not answers.exists())
        plan.append({"r": r, "answers": answers, "scored": scored,
                     "done": done, "need_answer": need_answer})

    # --- answering passes: one server boot serves every run that needs answers ---
    if any(p["need_answer"] for p in plan):
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
                print(f"[{cond}] DRY-RUN: server ready; would run {runs} pass(es) over "
                      f"{len(questions)} questions with config {cfg_path.name}")
                return "dry-run"
            for p in plan:
                if not p["need_answer"]:
                    continue
                tag = "" if runs == 1 else f" (run {p['r']}/{runs})"
                print(f"[{cond}] running benchmark over {len(questions)} questions"
                      f"{tag} (model={model})")
                subprocess.run(
                    [python, str(RUNNER), *questions,
                     "-c", str(cfg_path), "--model", model, "-o", str(p["answers"])],
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
    elif dry_run:
        # every replicate already answered — honor the dry-run contract without a boot
        print(f"[{cond}] DRY-RUN: all {runs} run(s) already answered; nothing to do")
        return "dry-run"

    # --- judging passes (no server needed) ---
    for p in plan:
        if p["done"]:
            print(f"[{cond}] run {p['r']} scored CSV exists — skipping judge")
            continue
        tag = "" if runs == 1 else f" (run {p['r']}/{runs})"
        print(f"[{cond}] LLM-judging answers{tag} -> {p['scored'].name}")
        eval_cmd = [python, str(EVALUATOR), str(p["answers"]), "-o", str(p["scored"])]
        if judge_model:
            eval_cmd += ["--model", judge_model]
        # Evaluator inherits the env: the Claude judge (add_llm_evaluation.py default)
        # authenticates via `claude login`, same as the runner. Do not inject a key.
        subprocess.run(eval_cmd, check=True, cwd=str(SCRIPTS_DIR))

    # --- average replicates into the flat scored CSV ablation_analysis.py reads ---
    if runs > 1:
        merge_scored([p["scored"] for p in plan], final_scored)
        print(f"[{cond}] averaged {runs} run(s) -> {final_scored.name}")
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
    ap.add_argument("--runs", type=int, default=1, metavar="N",
                    help="answer+judge each question N times per condition and average "
                         "per question (default 1). Replicates land in <cond>-scored-vN.csv; "
                         "the averaged <cond>-scored.csv feeds ablation_analysis.py. "
                         "Averaging R runs divides judge-jitter variance by R.")
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

    if args.runs < 1:
        raise SystemExit(f"--runs must be >= 1 (got {args.runs})")

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

    runs_note = f" x {args.runs} runs" if args.runs > 1 else ""
    print(f"Ablation sweep: {len(conditions)} conditions x {len(questions)} questions{runs_note}")
    print(f"  model={args.model}  judge={args.judge_model or '(eval default)'}  "
          f"port={args.port}  python={args.python}\n")

    summary: dict[str, str] = {}
    started = time.monotonic()
    for cond in conditions:
        try:
            summary[cond] = run_condition(cond, questions, base_config, args.port,
                                          args.model, args.judge_model, args.force,
                                          args.dry_run, args.python, args.runs)
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
