#!/usr/bin/env python3
"""Reproduce the paper's condition ablations (usage guide / MIE), with multi-judge scoring.

This is the non-MIE-subcomponent counterpart to ../ablation/run_ablation.py. It
drives the four config-based conditions the paper reported, each against the
PRODUCTION remote TogoMCP server (no local server — the configs already point at
https://togomcp.rdfportal.org/mcp):

    with_guide  config.yaml              full system (usage-guide tool + MIE + guided prompt)
    MIE-instr   config_no_guide1.yaml    no usage-guide tool; MIE workflow instructions kept in prompt
    No-Guide    config_no_guide2.yaml    no usage-guide tool and no workflow instructions
    no_mie      config_no_mie.yaml       get_MIE_file blocked (no MIE access)

Per condition it (1) collects answers with automated_test_runner.py, then
(2) LLM-judges those answers with EACH requested judge model — so you can compare
judges (Opus, a local Gemma, …), not just repeat one judge. Both scripts in
../scripts are reused unchanged (as subprocesses).

Auth: both the runner AND the Claude judge (add_llm_evaluation.py now defaults to
the Claude CLI / agent SDK) authenticate via your `claude login` — do NOT set
ANTHROPIC_API_KEY (the CLI would switch to API billing). Ollama judges (non-claude
model names) need a running Ollama host and no key.

Idempotent: an existing answers CSV skips collection; an existing scored CSV
skips that judge. Delete files or pass --force to redo.

Prerequisites (one interpreter with all of them; pass it via --python):
    claude-agent-sdk, pandas, anthropic  (+ ollama if using a local judge)
    `uv sync --extra dev` installs them into the repo .venv.

Usage:
    python run_conditions.py --python /path/to/.venv/bin/python
    python run_conditions.py --model claude-opus-4-7 --judges claude-opus-4-8,gemma4
    python run_conditions.py --conditions with_guide,no_mie --runs 3
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SCRIPTS_DIR = REPO_ROOT / "benchmark" / "scripts"
QUESTIONS_DIR = REPO_ROOT / "benchmark" / "questions"
RUNNER = SCRIPTS_DIR / "automated_test_runner.py"
EVALUATOR = SCRIPTS_DIR / "add_llm_evaluation.py"
RESULTS_DIR = HERE / "results"

# condition -> (config file in ../scripts, one-line description for the report)
CONDITIONS: dict[str, tuple[str, str]] = {
    "with_guide": ("config.yaml", "Full system: usage-guide tool + MIE + guided prompt"),
    "MIE-instr": ("config_no_guide1.yaml", "No usage-guide tool; MIE workflow instructions kept in prompt"),
    "No-Guide": ("config_no_guide2.yaml", "No usage-guide tool and no workflow instructions"),
    "no_mie": ("config_no_mie.yaml", "get_MIE_file blocked (no MIE access)"),
}
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_JUDGES = "claude-opus-4-8"


def _judge_is_anthropic(judge_model: str) -> bool:
    """add_llm_evaluation infers the anthropic provider for a claude-* model, else ollama."""
    return judge_model.startswith("claude")


def _slug(model: str) -> str:
    """Filesystem-safe token for a judge model (e.g. 'gemma4:latest' -> 'gemma4_latest')."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def preflight(python: str, judges: list[str]) -> None:
    """Fail fast if `python` can't import what the subprocesses need."""
    required = {
        # Both the runner and the default Claude judge use the agent SDK.
        "claude_agent_sdk": "automated_test_runner.py + the Claude judge — `pip install claude-agent-sdk`",
        "pandas": "add_llm_evaluation.py — `pip install pandas`",
    }
    if any(not _judge_is_anthropic(j) for j in judges):
        required["ollama"] = "the Ollama judge — `pip install ollama`"
    missing = []
    for mod, why in required.items():
        if subprocess.run([python, "-c", f"import {mod}"], capture_output=True).returncode != 0:
            missing.append((mod, why))
    if missing:
        lines = [f"Interpreter cannot import required modules:\n  {python}\n"]
        lines += [f"  - {m:18s} needed by {w}" for m, w in missing]
        lines.append("\nUse an interpreter with the benchmark deps (repo .venv after "
                     "`uv sync --extra dev`), or pass --python.")
        raise SystemExit("\n".join(lines))


def _expected_scored(base: Path, runs: int) -> list[Path]:
    """add_llm_evaluation writes <stem>-v1..-vN for runs>1, else <base> itself."""
    if runs <= 1:
        return [base]
    return [base.with_name(f"{base.stem}-v{i}{base.suffix}") for i in range(1, runs + 1)]


def run_condition(cond: str, questions: list[str], model: str, judges: list[str],
                  runs: int, python: str,
                  ollama_host: str | None, force: bool, run_dir: Path) -> dict:
    config, _ = CONDITIONS[cond]
    cfg_path = SCRIPTS_DIR / config
    if not cfg_path.exists():
        raise SystemExit(f"[{cond}] config not found: {cfg_path}")

    # Date and model are encoded in run_dir (results/<date>/<slug(model)>/), so the
    # filenames only carry condition + judge. Absolute paths so the manifest stays
    # valid regardless of the analyzer's cwd.
    answers = (run_dir / f"{cond}-answers.csv").resolve()
    entry = {"condition": cond, "config": config, "model": model,
             "answers_csv": str(answers), "judges": {}}

    # ---- 1. collect answers (runner uses the Claude CLI login; no key in env) ----
    if answers.exists() and not force:
        print(f"[{cond}] answers exist — skipping collection ({answers.name})")
    else:
        print(f"[{cond}] collecting answers over {len(questions)} questions (model={model})")
        subprocess.run(
            [python, str(RUNNER), *questions, "-c", str(cfg_path),
             "--model", model, "-o", str(answers)],
            check=True, cwd=str(SCRIPTS_DIR),
        )

    # ---- 2. judge with each requested model ----
    for judge in judges:
        base = (run_dir / f"{cond}-{_slug(judge)}.csv").resolve()
        expected = _expected_scored(base, runs)
        if all(p.exists() for p in expected) and not force:
            print(f"[{cond}] judge {judge}: scored CSV(s) exist — skipping")
            entry["judges"][judge] = [str(p) for p in expected]
            continue
        print(f"[{cond}] judging with {judge} (runs={runs})")
        cmd = [python, str(EVALUATOR), str(answers), "--model", judge, "-o", str(base)]
        if runs > 1:
            cmd += ["--runs", str(runs)]
        if ollama_host and not _judge_is_anthropic(judge):
            cmd += ["--ollama-host", ollama_host]
        # Evaluator inherits the env (no ANTHROPIC_API_KEY injection): the Claude
        # judge authenticates via `claude login`, same as the runner.
        subprocess.run(cmd, check=True, cwd=str(SCRIPTS_DIR))
        entry["judges"][judge] = [str(p) for p in expected]
    return entry


def merge_manifest(existing: dict, fresh: dict) -> dict:
    """Accumulate a fresh run's conditions/judges into a prior manifest for the same
    <date>/<model> folder, so conditions collected in separate invocations stay
    Δ-comparable. Same-named conditions are overlaid by the fresh run; the condition
    order follows CONDITIONS. Judges are unioned (order preserved)."""
    by_cond = {c["condition"]: c for c in existing.get("conditions", [])}
    for c in fresh["conditions"]:
        by_cond[c["condition"]] = c  # fresh overlays a re-run of the same condition
    ordered = [by_cond[name] for name in CONDITIONS if name in by_cond]

    judges: list[str] = list(existing.get("judges", []))
    for j in fresh["judges"]:
        if j not in judges:
            judges.append(j)

    merged = dict(fresh)  # fresh wins for scalar fields (model, date, runs)
    merged["judges"] = judges
    merged["conditions"] = ordered
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conditions", default=",".join(CONDITIONS),
                    help="comma-separated conditions (default: all four)")
    ap.add_argument("--questions", nargs="+", default=None,
                    help="question YAML paths (default: all ../questions/question_*.yaml)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="answering model")
    ap.add_argument("--judges", default=DEFAULT_JUDGES,
                    help="comma-separated judge models; claude-* -> Anthropic, else Ollama "
                         f"(default: {DEFAULT_JUDGES})")
    ap.add_argument("--runs", type=int, default=1, help="judge passes per (condition, judge)")
    ap.add_argument("--ollama-host", default=None, help="Ollama host URL for non-claude judges")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the runner/evaluator subprocesses "
                         "(must import claude_agent_sdk, pandas, anthropic/ollama)")
    ap.add_argument("--date", default=datetime.date.today().isoformat(),
                    help="date tag in output filenames (default: today)")
    ap.add_argument("--results-dir", default=str(RESULTS_DIR))
    ap.add_argument("--force", action="store_true", help="re-run even if outputs exist")
    ap.add_argument("--skip-preflight", action="store_true")
    args = ap.parse_args()

    results_dir = Path(args.results_dir)

    for tool in (RUNNER, EVALUATOR):
        if not tool.exists():
            raise SystemExit(f"missing dependency script: {tool}")

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown condition(s): {', '.join(unknown)}\nvalid: {', '.join(CONDITIONS)}")

    judges = [j.strip() for j in args.judges.split(",") if j.strip()]
    if not judges:
        raise SystemExit("no judges specified")

    if not args.skip_preflight:
        preflight(args.python, judges)

    questions = args.questions or sorted(str(p) for p in QUESTIONS_DIR.glob("question_*.yaml"))
    if not questions:
        raise SystemExit("no question files found")

    # results/<date>/<slug(model)>/ — date and answering model become the on-disk
    # organization so many runs over time stay browsable and never collide.
    run_dir = (results_dir / args.date / _slug(args.model)).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Condition sweep: {len(conditions)} conditions x {len(questions)} questions")
    print(f"  answering model={args.model}  judges={judges}  runs={args.runs}")
    print(f"  server=PRODUCTION (per each config)  date={args.date}  python={args.python}")
    print(f"  run dir={run_dir}\n")

    manifest = {"date": args.date, "model": args.model, "judges": judges,
                "runs": args.runs, "conditions": []}
    for cond in conditions:
        try:
            manifest["conditions"].append(
                run_condition(cond, questions, args.model, judges, args.runs, args.python,
                              args.ollama_host, args.force, run_dir))
        except SystemExit as e:
            print(f"[{cond}] ABORTED: {e}", file=sys.stderr)
        print()

    # Accumulate: fold this run into any prior manifest for the same <date>/<model>
    # so conditions gathered across separate invocations remain comparable.
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = merge_manifest(prior, manifest)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"warning: ignoring unreadable prior manifest ({e})", file=sys.stderr)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("=" * 60)
    print(f"Done. Manifest: {manifest_path}")
    print(f"Next: python conditions_analysis.py --date {args.date} --model {args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
