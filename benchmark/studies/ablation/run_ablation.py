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
    python ablate_mie.py --sections examples --keep-groups examples     # v3 stage 1

MIE format (--mie-format, default v3). v3 serves mie_variants_v3/, defaults to the
2026-10 configs and to the frozen question set (every benchmark/questions/question_*.yaml,
verified against SET_MANIFEST.json), and refuses to start on variants built from a
corpus that no longer matches togo_mcp/data/mie/ or on a prompt that names the retired
find_databases(). v2 reproduces the 2026-07 sweeps (mie_variants/, config.yaml,
pilot_questions.txt) exactly as before.

Every condition's server writes a JSONL tool-call log (<cond>-toolcalls.jsonl, via
TOGOMCP_QUERY_LOG). After answering, a condition is marked `error` if its server
executed zero tool calls (the relative --results-dir failure mode), or, for no_mie, if
get_MIE_file executed at all. run_manifest.json in the results dir records the
question-set hash, models, configs, variant hashes and the per-condition tool counts.

Usage:
    python run_ablation.py --answer-use-api --judge-use-api --runs 3 \
        --results-dir $PWD/results_v3_stage1                # v3 stage 1 (4 conditions)
    python run_ablation.py --mie-format v2 --conditions baseline,ablate_shape_expressions
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
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from statistics import mean

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from answer_screen import classify as screen_answer  # noqa: E402  (shared refusal/stub detector)
from ablate_mie import (CANONICAL_SECTIONS, EXCLUDED_DATABASES, GROUPS,  # single source of truth
                        V3_SECTIONS, V3_UNITS)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]  # benchmark/studies/ablation/ -> repo root
SCRIPTS_DIR = REPO_ROOT / "benchmark" / "scripts"
DEFAULT_BASE_CONFIG = SCRIPTS_DIR / "config.yaml"
RUNNER = SCRIPTS_DIR / "automated_test_runner.py"
EVALUATOR = SCRIPTS_DIR / "add_llm_evaluation.py"
VARIANTS_DIR = HERE / "mie_variants"
VARIANTS_DIR_V3 = HERE / "mie_variants_v3"
DEFAULT_BASE_CONFIG_V3 = SCRIPTS_DIR / "config_2026_10.yaml"
LIVE_MIE_DIR = REPO_ROOT / "togo_mcp" / "data" / "mie"
QUESTIONS_DIR = REPO_ROOT / "benchmark" / "questions"
SET_MANIFEST = QUESTIONS_DIR / "SET_MANIFEST.json"
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
# MIE v3 redesign smoke test (benchmark/studies/redesign/): a 2-corpus A/B, NOT an ablation.
# smoke_v2 = full current corpus; smoke_v3 = same but uniprot+bacdive swapped for their
# v3 rewrites. Both are ordinary mie_variants/<cond>/ dirs, so run_condition serves them
# unchanged; they only need to be on the valid list. Compare the two per question.
SMOKE_CONDITIONS = ["smoke_v2", "smoke_v3"]
# MIE v3 redesign RELEASE gate (step 5): the full-corpus equivalence A/B. Reuse
# smoke_v2 as the v2 arm (it is already the full current production corpus, byte-for-byte
# identical to togo_mcp/data/mie/), and full_v3 as the v3 arm (mie_variants/full_v3 = a
# copy of benchmark/studies/redesign/mie_v3, all 36 files). Ordinary mie_variants/<cond>/ dirs,
# served unchanged; run `--conditions smoke_v2,full_v3` in 25-question batches, fold with
# append_results.py. Pair v3 against v2 per question.
RELEASE_CONDITIONS = ["full_v3"]
# Valid set = all families; the DEFAULT stays section-only so existing
# invocations are unchanged. `--conditions groups` is baseline + every group;
# `--conditions keep` is baseline + every leave-one-in.
ALL_CONDITIONS = (SECTION_CONDITIONS + GROUP_CONDITIONS + NON_MIE_CONDITIONS
                  + KEEP_CONDITIONS + SMOKE_CONDITIONS + RELEASE_CONDITIONS)
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
# The judge is the measuring instrument: pin it rather than inherit add_llm_evaluation.py's
# default, which can change under a running study. v3 always passes it explicitly.
DEFAULT_JUDGE_MODEL_V3 = "claude-opus-4-8"

# v3 condition families (names follow the v2 ones; the variants live in mie_variants_v3/).
V3_SECTION_CONDITIONS = ["baseline"] + [f"ablate_{s}" for s in V3_SECTIONS]
V3_GROUP_CONDITIONS = [f"ablate_group_{u}" for u in V3_UNITS]
V3_KEEP_CONDITIONS = [f"keep_{u}" for u in V3_UNITS]
# 2026-10 stage 1: whole removal first, then leave-one-in before leave-one-out.
V3_STAGE1 = ["baseline", "no_mie", "ablate_examples", "keep_examples"]
V3_ALL_CONDITIONS = (V3_SECTION_CONDITIONS + V3_GROUP_CONDITIONS + NON_MIE_CONDITIONS
                     + V3_KEEP_CONDITIONS)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_variants_fresh(variants_dir: Path, allow_stale: bool = False) -> list[str]:
    """Refuse v3 variants built from a corpus that is no longer the live one.

    The variants are a snapshot; an MIE commit after `ablate_mie.py` ran would make
    "baseline" silently differ from what production serves.
    """
    manifest_path = variants_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} missing — run ablate_mie.py first")
    built = json.loads(manifest_path.read_text(encoding="utf-8"))
    if built.get("format") != "v3":
        raise SystemExit(f"{variants_dir} was not built with --format v3")
    excluded = set(built.get("excluded_databases", sorted(EXCLUDED_DATABASES)))
    live = {f.name: _sha256_file(f) for f in sorted(LIVE_MIE_DIR.glob("*.yaml"))
            if f.stem not in excluded}
    if live != built.get("source_sha256"):
        changed = sorted(n for n in set(live) | set(built.get("source_sha256", {}))
                         if live.get(n) != built["source_sha256"].get(n))
        if allow_stale:
            print(f"WARNING: --allow-stale-variants: serving {variants_dir}, built from an older "
                  f"corpus ({len(changed)} file(s) differ from the live one: {', '.join(changed)}). "
                  f"Recorded in run_manifest.json.")
            return changed
        raise SystemExit(
            f"variants in {variants_dir} are stale: {len(changed)} MIE file(s) differ from "
            f"{LIVE_MIE_DIR} ({', '.join(changed[:8])}{' ...' if len(changed) > 8 else ''}). "
            f"Re-run ablate_mie.py, but NOT while a sweep is serving from {variants_dir}: it "
            f"deletes and rebuilds those directories under the running servers. Build into a "
            f"new --out instead, or wait for the sweep to finish. To continue a sweep on its own "
            f"snapshot (e.g. its last condition), pass --allow-stale-variants.")
    return []


def frozen_question_set() -> tuple[list[str], dict]:
    """All question files, verified against SET_MANIFEST.json."""
    if not SET_MANIFEST.exists():
        raise SystemExit(f"{SET_MANIFEST} missing — run benchmark/scripts/make_set_manifest.py")
    m = json.loads(SET_MANIFEST.read_text(encoding="utf-8"))
    files = sorted(QUESTIONS_DIR.glob("question_*.yaml"))
    cur = {f.name: _sha256_file(f) for f in files}
    if cur != m["files"]:
        raise SystemExit(
            f"question files differ from {SET_MANIFEST.name} (set {m['set_hash'][:12]}). "
            f"Run make_set_manifest.py --check; commit and re-freeze before a run.")
    return [str(f) for f in files], m


def count_tool_calls(log_path: Path) -> dict[str, int]:
    """Per-tool counts of calls the server actually executed (JSONL `tool` field)."""
    counts: dict[str, int] = {}
    if not log_path.exists():
        return counts
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            tool = json.loads(line).get("tool")
        except (json.JSONDecodeError, AttributeError):
            continue
        if tool:
            counts[tool] = counts.get(tool, 0) + 1
    return counts


def tool_call_errors(cond: str, counts: dict[str, int]) -> list[str]:
    errs = []
    if sum(counts.values()) == 0:
        errs.append(f"[{cond}] the local server executed ZERO tool calls: the agent did not "
                    f"use this condition's server (check --results-dir / rendered config)")
    mie_calls = counts.get("get_MIE_file", 0)
    if cond == "no_mie" and mie_calls:
        errs.append(f"[{cond}] get_MIE_file executed {mie_calls} time(s): the MIE leaked "
                    f"into the no-MIE condition")
    if cond != "no_mie" and sum(counts.values()) and not mie_calls:
        errs.append(f"[{cond}] get_MIE_file never executed: this condition's MIE variant "
                    f"was never served, so it measured nothing")
    return errs


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


ISOLATE = False   # set by --isolate; module-level so render_config sees it
ALLOW_MEMORY = False  # set by --allow-memory-exposure


def render_config(base_config: Path, port: int, out_path: Path) -> None:
    """Clone the base benchmark config, redirecting only the togomcp server URL."""
    cfg = yaml.safe_load(base_config.read_text(encoding="utf-8"))
    if ALLOW_MEMORY and not ISOLATE:
        cfg["allow_memory_exposure"] = True   # the runner refuses a non-isolated run otherwise
    if ISOLATE:
        # Opt-in (stage 1 ran without it): confine non-MCP reads to the session's own saved
        # outputs and give each condition its own Claude Code config dir, so no condition can
        # read another condition's transcripts (and the full MIE responses in them).
        cfg["strict_isolation"] = True
        cfg["claude_config_dir"] = str(RESULTS_DIR / "claude-config" / out_path.name.split(".")[0])
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


def merge_scored(run_paths: list[Path], out_path: Path, screen: bool = True) -> None:
    """Average per-question scores across replicate scored CSVs into one CSV.

    With ``screen`` (default), each replicate cell is first screened with
    answer_screen.classify: a content-policy refusal or a stub (failed/empty/login-error
    answer) has that ARM's judge scores treated as missing, exactly like a failed-judge
    0, because its 4/20 floor measures the policy filter, not TogoMCP (Trap 8; 50
    stage-1 cells in 2026-10, unevenly across conditions). ``n_excluded_togomcp`` and
    ``n_excluded_baseline`` record how many replicates were dropped per row. Callers
    also write the unscreened average to <cond>-scored-raw.csv for side-by-side
    reporting.

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
        excluded = {arm: [screen and screen_answer(row.get(f"{arm}_answer"),
                                                   row.get(f"{arm}_success")) != "valid"
                          for row in rows] for arm in ("togomcp", "baseline")}
        rec["n_excluded_togomcp"] = sum(excluded["togomcp"])
        rec["n_excluded_baseline"] = sum(excluded["baseline"])
        for col in numeric_cols:
            arm = col.split("_", 1)[0]
            drop = excluded.get(arm) if _is_score_col(col) else None
            nums = [float(row[col]) for i, row in enumerate(rows)
                    if _is_number(row.get(col, "")) and not (drop and drop[i])]
            if _is_score_col(col):
                nz = [v for v in nums if v != 0]  # drop failed-judge sentinels
                rec[col] = f"{mean(nz):.4g}" if nz else "0"
            else:
                rec[col] = f"{mean(nums):.6g}" if nums else ""
        merged.append(rec)

    out_fields = list(fieldnames)
    for extra in ("n_runs", "n_excluded_togomcp", "n_excluded_baseline"):
        if extra not in out_fields:
            out_fields.append(extra)
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
                  answer_use_api: bool = False, judge_runs: int = 1,
                  tool_counts: dict | None = None) -> str:
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
    # JSONL record of every tool call the server executes: the ground truth for the
    # post-run checks (the plain server log only says "CallToolRequest", not which tool).
    toolcall_log = RESULTS_DIR / f"{cond}-toolcalls.jsonl"
    env["TOGOMCP_QUERY_LOG"] = str(toolcall_log)

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
    answered = False
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
                answered = True
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

    # --- post-answer guards: did this condition's server really do the work? ---
    # Checked whenever a tool-call log exists (also on a resumed run), before any
    # judging money is spent on answers that measured nothing.
    if answered or toolcall_log.exists():
        counts = count_tool_calls(toolcall_log)
        if tool_counts is not None:
            tool_counts[cond] = counts
        total = sum(counts.values())
        print(f"[{cond}] server executed {total} tool call(s); "
              f"get_MIE_file={counts.get('get_MIE_file', 0)}")
        errs = tool_call_errors(cond, counts)
        if errs:
            raise SystemExit("\n".join(errs))

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
        elif ALLOW_MEMORY:
            eval_cmd += ["--allow-memory-exposure"]
        # Judge inherits the full env (incl. ANTHROPIC_API_KEY when --judge-use-api);
        # the default (no --use-api) authenticates via `claude login` like the runner.
        subprocess.run(eval_cmd, check=True, cwd=str(SCRIPTS_DIR), env=env)

    # --- average all R*M scored files into the flat scored CSV ablation_analysis reads ---
    all_scored = [f for p in plan for f in p["scored_files"]]
    if len(all_scored) > 1:
        merge_scored(all_scored, final_scored)
        merge_scored(all_scored, final_scored.with_name(f"{cond}-scored-raw.csv"), screen=False)
        print(f"[{cond}] averaged {len(all_scored)} scored file(s) "
              f"({runs} answer x {judge_runs} judge) -> {final_scored.name}")
    return "done"


def write_run_manifest(args, conditions, questions, base_config, set_manifest,
                       summary, tool_counts) -> None:
    """Append this invocation to <results>/run_manifest.json (one entry per invocation)."""
    qhash = {Path(q).name: _sha256_file(Path(q)) for q in questions}
    full_set = bool(set_manifest) and qhash == set_manifest.get("files")
    variants_manifest = VARIANTS_DIR / "manifest.json"
    try:
        commit = subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                                         text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_commit": commit,
        "mie_format": args.mie_format,
        "conditions": conditions,
        "status": summary,
        "question_set_hash": set_manifest.get("set_hash") if full_set else None,
        "question_subset_of": set_manifest.get("set_hash") if set_manifest and not full_set else None,
        "n_questions": len(questions),
        "question_files": qhash if not full_set else None,
        "answer_model": args.model,
        "judge_model": args.judge_model,
        "runs": args.runs,
        "judge_runs": args.judge_runs,
        "answer_use_api": args.answer_use_api,
        "judge_use_api": args.judge_use_api,
        "base_config": str(base_config),
        "base_config_sha256": _sha256_file(base_config),
        "variants_dir": str(VARIANTS_DIR),
        "variants_manifest_sha256": (_sha256_file(variants_manifest)
                                     if variants_manifest.exists() else None),
        "tool_calls": tool_counts,
        "isolate": args.isolate,
        "memory_exposure_allowed": args.allow_memory_exposure and not args.isolate,
        "stale_variants_allowed": getattr(args, "_stale_files", []),
    }
    path = RESULTS_DIR / "run_manifest.json"
    entries = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    entries.append(entry)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"run manifest -> {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mie-format", choices=["v2", "v3"], default="v3",
                    help="MIE corpus format (default v3). v2 reproduces the 2026-07 sweeps.")
    ap.add_argument("--conditions", default=None,
                    help="comma-separated conditions. Default: v3 = stage1 (baseline, no_mie, "
                         "ablate_examples, keep_examples); v2 = baseline + all 11 single-"
                         "section ablations. Aliases: 'groups' (baseline + every group "
                         "ablation), 'keep' (baseline + every leave-one-in), 'stage1' (v3).")
    ap.add_argument("--questions", nargs="+", default=None,
                    help="explicit question YAML paths (default: v3 = the frozen set, all "
                         "benchmark/questions/question_*.yaml checked against "
                         "SET_MANIFEST.json; v2 = pilot_questions.txt)")
    ap.add_argument("--base-config", default=None,
                    help=f"benchmark config to clone (default: v3 = {DEFAULT_BASE_CONFIG_V3.name}, "
                         f"v2 = {DEFAULT_BASE_CONFIG.name}). no_mie needs one that denies "
                         f"get_MIE_file, e.g. config_no_mie_2026_10.yaml.")
    ap.add_argument("--results-dir", default=None, metavar="DIR",
                    help="write results here instead of ./results. Use to stage a NEW batch of "
                         "questions (run every condition for them in one batch, then fold in with "
                         "append_results.py) — extends n without re-running the existing set.")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="answering model")
    ap.add_argument("--judge-model", default=None,
                    help=f"LLM-judge model (default: v3 = {DEFAULT_JUDGE_MODEL_V3}, always passed "
                         "explicitly and recorded in run_manifest.json; v2 = add_llm_evaluation.py's "
                         "own default)")
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
    ap.add_argument("--isolate", action="store_true",
                    help="strict transcript isolation (per-condition Claude config dir + a hook "
                         "confining Read/Bash to the session's own outputs). Requires "
                         "--answer-use-api. Off by default: stage 1 (2026-10) ran without it.")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the server + benchmark subprocesses "
                         "(default: this one; must import togo_mcp, claude_agent_sdk, pandas, anthropic)")
    ap.add_argument("--skip-preflight", action="store_true",
                    help="skip the up-front dependency check")
    ap.add_argument("--force", action="store_true", help="re-run conditions even if scored CSV exists")
    ap.add_argument("--allow-memory-exposure", action="store_true",
                    help="run WITHOUT --isolate: the repository's auto-memory is then in every "
                         "answering agent's context (as in stage 1, 2026-10). Only to reproduce "
                         "such a run; recorded in run_manifest.json.")
    ap.add_argument("--allow-stale-variants", action="store_true",
                    help="serve variants built from an older corpus. Only for continuing a sweep "
                         "on the snapshot its earlier conditions used; the differing files are "
                         "recorded in run_manifest.json.")
    ap.add_argument("--remerge", action="store_true",
                    help="only rebuild <cond>-scored.csv (screened) and <cond>-scored-raw.csv from "
                         "the existing replicate files of --conditions in --results-dir; no "
                         "server, no API. Use after a detector change or for conditions merged "
                         "by an older run_ablation.py.")
    ap.add_argument("--dry-run", action="store_true",
                    help="boot the server + render config + check readiness, but skip the "
                         "runner/evaluator (validates orchestration without API cost)")
    args = ap.parse_args()

    for tool in (RUNNER, EVALUATOR):
        if not tool.exists():
            raise SystemExit(f"missing dependency script: {tool}")

    global ISOLATE, ALLOW_MEMORY
    ISOLATE, ALLOW_MEMORY = args.isolate, args.allow_memory_exposure
    if not args.remerge and not args.isolate and not args.allow_memory_exposure:
        raise SystemExit(
            "this sweep is not isolated: without --isolate (needs --answer-use-api) every "
            "answering agent gets the repository's auto-memory in its context and can read "
            "other sessions' transcripts. Pass --isolate, or --allow-memory-exposure to "
            "reproduce a pre-2026-10-06 run.")
    if not args.remerge and not args.dry_run and not args.judge_use_api \
            and not args.allow_memory_exposure:
        raise SystemExit("the Claude judge without --judge-use-api runs inside this repo and gets "
                         "its auto-memory; pass --judge-use-api (or --allow-memory-exposure).")
    if args.isolate and not args.answer_use_api:
        raise SystemExit("--isolate needs --answer-use-api: a fresh Claude config dir has no "
                         "claude-login credentials")
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

    if args.remerge:
        if not args.results_dir or not args.conditions:
            raise SystemExit("--remerge needs --results-dir and --conditions")
        for cond in [c.strip() for c in args.conditions.split(",") if c.strip()]:
            reps = sorted(RESULTS_DIR.glob(f"{cond}-scored-v*.csv"))
            if not reps:
                print(f"[{cond}] no replicate scored files; skipped")
                continue
            merge_scored(reps, RESULTS_DIR / f"{cond}-scored.csv")
            merge_scored(reps, RESULTS_DIR / f"{cond}-scored-raw.csv", screen=False)
            print(f"[{cond}] re-merged {len(reps)} replicate(s) -> {cond}-scored.csv (+ -raw)")
        return 0

    global VARIANTS_DIR
    v3 = args.mie_format == "v3"
    if v3 and not args.judge_model:
        args.judge_model = DEFAULT_JUDGE_MODEL_V3
    if v3:
        VARIANTS_DIR = VARIANTS_DIR_V3
        valid, groups_c, keep_c = V3_ALL_CONDITIONS, V3_GROUP_CONDITIONS, V3_KEEP_CONDITIONS
        default_conditions = V3_STAGE1
    else:
        valid, groups_c, keep_c = ALL_CONDITIONS, GROUP_CONDITIONS, KEEP_CONDITIONS
        default_conditions = SECTION_CONDITIONS
    cond_arg = args.conditions if args.conditions is not None else ",".join(default_conditions)
    conditions = [c.strip() for c in cond_arg.split(",") if c.strip()]
    if conditions == ["groups"]:
        conditions = ["baseline"] + groups_c
    elif conditions == ["keep"]:
        conditions = ["baseline"] + keep_c
    elif conditions == ["stage1"] and v3:
        conditions = list(V3_STAGE1)
    unknown = [c for c in conditions if c not in valid]
    if unknown:
        raise SystemExit(f"unknown {args.mie_format} condition(s): {', '.join(unknown)}\n"
                         f"valid: {', '.join(valid)}")

    base_config = Path(args.base_config or (DEFAULT_BASE_CONFIG_V3 if v3 else DEFAULT_BASE_CONFIG))
    if not base_config.exists():
        raise SystemExit(f"base config not found: {base_config}")
    base_cfg = yaml.safe_load(base_config.read_text(encoding="utf-8")) or {}
    if v3 and "find_databases" in str(base_cfg.get("togomcp_system_prompt", "")):
        raise SystemExit(
            f"{base_config} tells the agent to call find_databases(), retired in 2.0.0. "
            f"Use config_2026_10.yaml / config_no_mie_2026_10.yaml.")
    # no_mie and the MIE-serving conditions need DIFFERENT base configs, so they cannot
    # share one invocation: run no_mie on its own with the no-MIE config.
    denies_mie = any("get_MIE_file" in str(d) for d in (base_cfg.get("disallowed_tools") or []))
    if denies_mie and any(c != "no_mie" for c in conditions):
        raise SystemExit(
            f"{base_config} denies get_MIE_file, so every condition except no_mie would run "
            f"without the MIE. Run no_mie in a separate invocation with this config.")

    # Footgun guard: no_mie MUST run on a base config that denies get_MIE_file.
    # With the default config.yaml the tool stays available and it becomes a silent
    # WITH-MIE run — the same class of silent-invalid failure as the --results-dir bug.
    if "no_mie" in conditions and not denies_mie:
        raise SystemExit(
            f"condition 'no_mie' requires a --base-config that denies get_MIE_file, "
            f"but {base_config} does not. Use benchmark/scripts/"
            f"{'config_no_mie_2026_10.yaml' if v3 else 'config_no_mie.yaml'}. Running "
            f"no_mie on a config that allows the tool would silently serve WITH the MIE.")

    set_manifest = None
    if v3:
        args._stale_files = check_variants_fresh(VARIANTS_DIR, args.allow_stale_variants)
        if args.questions:
            questions = args.questions
            if SET_MANIFEST.exists():
                set_manifest = json.loads(SET_MANIFEST.read_text(encoding="utf-8"))
        else:
            questions, set_manifest = frozen_question_set()
    else:
        questions = load_pilot(args.questions)
    missing = [q for q in questions if not Path(q).is_file()]
    if missing:
        raise SystemExit("question file(s) not found (one path per argument):\n  "
                         + "\n  ".join(missing))
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
    tool_counts: dict[str, dict[str, int]] = {}
    started = time.monotonic()
    for cond in conditions:
        try:
            summary[cond] = run_condition(cond, questions, base_config, args.port,
                                          args.model, args.judge_model, args.force,
                                          args.dry_run, args.python, args.runs,
                                          args.judge_use_api, args.answer_use_api,
                                          args.judge_runs, tool_counts)
        except SystemExit as e:
            print(f"[{cond}] ABORTED: {e}", file=sys.stderr)
            summary[cond] = "error"
        print()

    if not args.dry_run:
        write_run_manifest(args, conditions, questions, base_config, set_manifest,
                           summary, tool_counts)

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
