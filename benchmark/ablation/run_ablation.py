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
    python run_ablation.py --runs 5                      # 5 answer+judge reps/question
    python run_ablation.py --runs 1 --judge-runs 5       # 1 answer x 5 judges/question

Two independent replication axes, both averaged per question_id into the flat
<cond>-scored.csv that ablation_analysis.py consumes:

  --runs R       re-ANSWERS (server boot + fresh agent run) AND judges R times.
                 Averages answer stochasticity + judge jitter, at full answering cost.
  --judge-runs M re-JUDGES the SAME answers M times, no re-answering. Averages ONLY
                 judge jitter, at a fraction of the cost (a judge pass has no server
                 boot, no multi-step agent, no run_sparql round-trips).

They compose: --runs R --judge-runs M averages R*M scored files (<cond>-scored-vR-vM
.csv; ablation_analysis's -scored-v* glob absorbs both names). Per-question judge SD
is the dominant term saturating the pilot's CIs, so --runs 1 --judge-runs 5 buys the
same /5 judge-jitter reduction as --runs 5 far more cheaply, and mirrors the
conditions-study design (1 answer x 5 judges) that produced significant results.
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

from ablate_mie import CANONICAL_SECTIONS, GROUPS  # single source of truth

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

SECTION_CONDITIONS = ["baseline"] + [f"ablate_{s}" for s in CANONICAL_SECTIONS]
GROUP_CONDITIONS = [f"ablate_group_{g}" for g in GROUPS]
# no_mie is a whole-MIE condition: get_MIE_file is DENIED at the tool level (via the
# base config's disallowed_tools) rather than the corpus being section-stripped. It
# reuses the same server/render/replicate machinery, so run it with
#   --base-config benchmark/scripts/config_no_mie.yaml   (denies get_MIE_file + a
#   matching prompt) and a mie_variants/no_mie dir (a baseline copy — the served
# corpus is moot since the tool is blocked). Pair it against the baseline in the
# same --results-dir. The main() guard below refuses to run it with a base config
# that still ALLOWS get_MIE_file (that would be a silent WITH-MIE run).
NON_MIE_CONDITIONS = ["no_mie"]
# Leave-one-in: keep ONLY one group, strip the other two (built by
# ablate_mie.py --keep-groups all). The complement of the group ablation — tests
# whether a group is SUFFICIENT alone (pair keep_X against no_mie), not whether it
# is necessary. Served via get_MIE_file like the group variants (default config).
KEEP_CONDITIONS = [f"keep_{g}" for g in GROUPS]
# MIE v3 redesign smoke test (benchmark/redesign/): a 2-corpus A/B, NOT an ablation.
# smoke_v2 = full current corpus; smoke_v3 = same but uniprot+bacdive swapped for their
# v3 rewrites. Both are ordinary mie_variants/<cond>/ dirs, so run_condition serves them
# unchanged; they only need to be on the valid list. Compare the two per question.
SMOKE_CONDITIONS = ["smoke_v2", "smoke_v3"]
# MIE v3 redesign RELEASE gate (step 5): the full-corpus equivalence A/B. Reuse
# smoke_v2 as the v2 arm (it is already the full current production corpus, byte-for-byte
# identical to togo_mcp/data/mie/), and full_v3 as the v3 arm (mie_variants/full_v3 = a
# copy of benchmark/redesign/mie_v3, all 36 files). Ordinary mie_variants/<cond>/ dirs,
# served unchanged; run `--conditions smoke_v2,full_v3` in 25-question batches, fold with
# append_results.py. Pair v3 against v2 per question.
RELEASE_CONDITIONS = ["full_v3"]
# Valid set = all families; the DEFAULT stays section-only so existing
# invocations are unchanged. `--conditions groups` is baseline + every group;
# `--conditions keep` is baseline + every leave-one-in.
ALL_CONDITIONS = (SECTION_CONDITIONS + GROUP_CONDITIONS + NON_MIE_CONDITIONS
                  + KEEP_CONDITIONS + SMOKE_CONDITIONS + RELEASE_CONDITIONS)
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
                  python: str, runs: int = 1, judge_use_api: bool = False,
                  answer_use_api: bool = False, judge_runs: int = 1) -> str:
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

    # Answering runs on the claude_agent_sdk bundled CLI. If ANTHROPIC_API_KEY is in
    # its env, the CLI bills the Anthropic API; if absent, it uses the `claude login`
    # subscription. The subscription can't sustain a large batch — it degrades into
    # "Not logged in" login-error stubs (the runner mislabels them success=True) — so
    # --answer-use-api keeps the key for reliable API answering. Without it (default)
    # we strip the key so answering stays on the subscription; but then --judge-use-api
    # must NOT leak the key into answering, hence the same strip.
    answer_env = env
    if not answer_use_api and "ANTHROPIC_API_KEY" in answer_env:
        answer_env = {k: v for k, v in env.items() if k != "ANTHROPIC_API_KEY"}

    # runs==1 keeps the flat <cond>-answers/scored.csv names (backward compatible);
    # runs>1 writes -vR answer replicates. scored_base is the -o handed to the judge.
    def run_paths(r: int) -> tuple[Path, Path]:
        if runs == 1:
            return (RESULTS_DIR / f"{cond}-answers.csv",
                    RESULTS_DIR / f"{cond}-scored.csv")
        return (RESULTS_DIR / f"{cond}-answers-v{r}.csv",
                RESULTS_DIR / f"{cond}-scored-v{r}.csv")

    # Mirror add_llm_evaluation._versioned_paths: --runs 1 writes scored_base itself;
    # --runs M writes scored_base-v1..-vM. So one answer file fans out to M judge CSVs.
    def judge_scored_paths(scored_base: Path) -> list[Path]:
        if judge_runs == 1:
            return [scored_base]
        return [scored_base.with_name(f"{scored_base.stem}-v{j}{scored_base.suffix}")
                for j in range(1, judge_runs + 1)]

    plan = []
    for r in range(1, runs + 1):
        answers, scored_base = run_paths(r)
        scored_files = judge_scored_paths(scored_base)   # the M judge CSVs for this answer
        done = all(f.exists() for f in scored_files) and not force  # already fully judged
        need_answer = (not done) and (force or not answers.exists())
        plan.append({"r": r, "answers": answers, "scored_base": scored_base,
                     "scored_files": scored_files, "done": done,
                     "need_answer": need_answer})

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
                    check=True, cwd=str(SCRIPTS_DIR), env=answer_env,
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
            print(f"[{cond}] run {p['r']} scored CSV(s) exist — skipping judge")
            continue
        tag = "" if runs == 1 else f" (answer {p['r']}/{runs})"
        jtag = "" if judge_runs == 1 else f" x{judge_runs} judges"
        print(f"[{cond}] LLM-judging answers{tag}{jtag} -> {p['scored_base'].name}")
        eval_cmd = [python, str(EVALUATOR), str(p["answers"]), "-o", str(p["scored_base"])]
        if judge_runs > 1:
            eval_cmd += ["--runs", str(judge_runs)]   # M judge passes over the SAME answers
        if judge_model:
            eval_cmd += ["--model", judge_model]
        if judge_use_api:
            eval_cmd += ["--use-api"]     # plain anthropic SDK, forced-tool-call, ANTHROPIC_API_KEY
        # Judge inherits the full env (incl. ANTHROPIC_API_KEY when --judge-use-api);
        # the default (no --use-api) authenticates via `claude login` like the runner.
        subprocess.run(eval_cmd, check=True, cwd=str(SCRIPTS_DIR), env=env)

    # --- average all R*M scored files into the flat scored CSV ablation_analysis reads ---
    all_scored = [f for p in plan for f in p["scored_files"]]
    if len(all_scored) > 1:
        merge_scored(all_scored, final_scored)
        print(f"[{cond}] averaged {len(all_scored)} scored file(s) "
              f"({runs} answer x {judge_runs} judge) -> {final_scored.name}")
    return "done"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conditions", default=",".join(SECTION_CONDITIONS),
                    help="comma-separated conditions (default: baseline + all 11 "
                         "single-section ablations). Use 'groups' for baseline + every "
                         "GROUP ablation (build them first: ablate_mie.py --groups all).")
    ap.add_argument("--questions", nargs="+", default=None,
                    help="explicit question YAML paths (default: pilot_questions.txt)")
    ap.add_argument("--base-config", default=str(DEFAULT_BASE_CONFIG),
                    help=f"benchmark config to clone (default: {DEFAULT_BASE_CONFIG})")
    ap.add_argument("--results-dir", default=None, metavar="DIR",
                    help="write results here instead of ./results. Use to stage a NEW batch of "
                         "questions (run every condition for them in one batch, then fold in with "
                         "append_results.py) — extends n without re-running the existing set.")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="answering model")
    ap.add_argument("--judge-model", default=None,
                    help="LLM-judge model (default: add_llm_evaluation.py's own default)")
    ap.add_argument("--runs", type=int, default=1, metavar="N",
                    help="answer+judge each question N times per condition and average "
                         "per question (default 1). Replicates land in <cond>-scored-vN.csv; "
                         "the averaged <cond>-scored.csv feeds ablation_analysis.py. "
                         "Averaging R runs divides judge-jitter variance by R (but also "
                         "re-answers R times, at full answering cost).")
    ap.add_argument("--judge-runs", type=int, default=1, metavar="M",
                    help="re-JUDGE each answer M times WITHOUT re-answering, then average "
                         "(default 1). Far cheaper than --runs for cutting judge jitter: a "
                         "judge pass has no server boot, agent run, or SPARQL round-trips. "
                         "--runs R --judge-runs M averages R*M scored files. "
                         "--runs 1 --judge-runs 5 mirrors the conditions-study design.")
    ap.add_argument("--judge-use-api", action="store_true",
                    help="judge via the Anthropic Messages API (plain anthropic SDK, forced "
                         "record_evaluation tool call) instead of the claude-login agent SDK. "
                         "Requires ANTHROPIC_API_KEY. Use for long batches where subscription "
                         "Opus judging gets throttled.")
    ap.add_argument("--answer-use-api", action="store_true",
                    help="answer via the Anthropic API (keep ANTHROPIC_API_KEY in the answering "
                         "agent's env) instead of the claude-login subscription. Requires "
                         "ANTHROPIC_API_KEY. Use for long batches: the subscription degrades into "
                         "'Not logged in' login-error stubs under sustained load. Without this, "
                         "answering stays on the subscription and the key is withheld from it.")
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
    if args.judge_runs < 1:
        raise SystemExit(f"--judge-runs must be >= 1 (got {args.judge_runs})")

    if args.results_dir:
        global RESULTS_DIR, RENDERED_DIR
        # Resolve to absolute: the runner/judge subprocesses run with cwd=SCRIPTS_DIR,
        # so a relative --results-dir would make the rendered-config path (-c) and the
        # answer-output path (-o) resolve against benchmark/scripts instead of here.
        # The config would then be "not found" and the runner would silently fall back
        # to default settings (production togomcp URL, full MIEs) — zero ablation signal.
        RESULTS_DIR = Path(args.results_dir).resolve()
        RENDERED_DIR = RESULTS_DIR / "rendered_configs"
        print(f"results dir: {RESULTS_DIR}")

    if (args.judge_use_api or args.answer_use_api) and not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("--judge-use-api/--answer-use-api require ANTHROPIC_API_KEY in the "
                         "environment (e.g. `ANTHROPIC_API_KEY=$MY_ANTHROPIC_API_KEY ...`).")

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    if conditions == ["groups"]:
        conditions = ["baseline"] + GROUP_CONDITIONS
    elif conditions == ["keep"]:
        conditions = ["baseline"] + KEEP_CONDITIONS
    unknown = [c for c in conditions if c not in ALL_CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown condition(s): {', '.join(unknown)}\nvalid: {', '.join(ALL_CONDITIONS)}")

    base_config = Path(args.base_config)
    if not base_config.exists():
        raise SystemExit(f"base config not found: {base_config}")

    # Footgun guard: no_mie MUST run on a base config that denies get_MIE_file.
    # With the default config.yaml the tool stays available and it becomes a silent
    # WITH-MIE run — the same class of silent-invalid failure as the --results-dir bug.
    if "no_mie" in conditions:
        denied = (yaml.safe_load(base_config.read_text(encoding="utf-8")) or {}).get(
            "disallowed_tools") or []
        if not any("get_MIE_file" in str(d) for d in denied):
            raise SystemExit(
                f"condition 'no_mie' requires a --base-config that denies get_MIE_file, "
                f"but {base_config} does not. Use "
                f"benchmark/scripts/config_no_mie.yaml. Running no_mie on the default "
                f"config.yaml would silently serve WITH the MIE.")

    questions = load_pilot(args.questions)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_preflight:
        required = dict(SERVER_IMPORTS)
        if not args.dry_run:
            required.update(BENCH_IMPORTS)
        preflight(args.python, required)

    runs_note = f" x {args.runs} answer-runs" if args.runs > 1 else ""
    runs_note += f" x {args.judge_runs} judge-runs" if args.judge_runs > 1 else ""
    judge_path = "anthropic API" if args.judge_use_api else "claude-login agent SDK"
    answer_path = "anthropic API" if args.answer_use_api else "claude-login subscription"
    print(f"Ablation sweep: {len(conditions)} conditions x {len(questions)} questions{runs_note}")
    print(f"  answer={args.model} via {answer_path}  "
          f"judge={args.judge_model or '(eval default)'} via {judge_path}\n"
          f"  port={args.port}  python={args.python}\n")

    summary: dict[str, str] = {}
    started = time.monotonic()
    for cond in conditions:
        try:
            summary[cond] = run_condition(cond, questions, base_config, args.port,
                                          args.model, args.judge_model, args.force,
                                          args.dry_run, args.python, args.runs,
                                          args.judge_use_api, args.answer_use_api,
                                          args.judge_runs)
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
