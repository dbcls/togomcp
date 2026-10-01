#!/usr/bin/env python3
"""Run the TogoMCP benchmark (canary or full) end to end into benchmark/results/.

    answer (automated_test_runner.py, TogoMCP + in-batch no-tool baseline per question)
      -> guard (the server really executed tool calls, including get_MIE_file)
      -> judge (add_llm_evaluation.py, every judge x every replicate)
      -> manifest.json -> summarize_run.py (summary.csv, report.md, diff, usage-log link)

Output: benchmark/results/<date>/<answer-model>/<mode>/ (gitignored).

The default target is a LOCAL server (benchmark/studies/ablation/_serve.py) serving
--mie-dir, because only a local server gives this run its own tool-call log: the source of
the manifest's server/MIE/guide versions, the zero-tool-call guard and the benchmark SPARQL
error rate. --target production answers against https://togomcp.rdfportal.org/mcp; then the
server version comes from `initialize` and the MIE bundle version is unknown.

This script spends API money unless --dry-run. The skill (SKILL.md) requires showing the plan
and estimate to the user and getting approval first; --dry-run prints both.

Usage:
    python run_benchmark.py --mode canary --dry-run
    python run_benchmark.py --mode canary
    python run_benchmark.py --mode full --usage-log ~/Downloads/togomcp-log-20261001.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
SCRIPTS = REPO / "benchmark" / "scripts"
QUESTIONS = REPO / "benchmark" / "questions"
SET_MANIFEST = QUESTIONS / "SET_MANIFEST.json"
SERVE = REPO / "benchmark" / "studies" / "ablation" / "_serve.py"
RUNNER = SCRIPTS / "automated_test_runner.py"
EVALUATOR = SCRIPTS / "add_llm_evaluation.py"
SUMMARIZER = Path(__file__).resolve().parent / "summarize_run.py"
PRODUCTION_URL = "https://togomcp.rdfportal.org/mcp"

DEFAULT_ANSWER_MODEL = "claude-sonnet-5-5"
DEFAULT_JUDGES = ["claude-opus-4-8", "gemma4"]
DEFAULT_CANARY = SCRIPTS / "canary_questions_2026_10.txt"
DEFAULT_BASE_CONFIG = SCRIPTS / "config_2026_10_sonnet55.yaml"
# USD per MTok (input, output). The runner prefers the CLI-reported cost when present; this
# only feeds its fallback estimate, but a wrong table would misstate cost silently, so an
# unknown model must be priced explicitly.
PRICING = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-opus-5-5": (5.00, 25.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}
# Planning figures per cell (one question x one replicate: TogoMCP + no-tool answer), from
# the 2026-10-01 Sonnet 5.5 pilot (answer $0.25, ~1.0 min) plus ~$0.06 per Opus judge pass.
EST_ANSWER_USD, EST_CLAUDE_JUDGE_USD, EST_MIN_PER_CELL = 0.25, 0.06, 1.1
EST_OLLAMA_MIN_PER_CELL = 1.55   # Gemma4 on the developer Mac: ~46 s x 2 judgements per cell


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*a) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), *a], text=True).strip()


def frozen_questions(mode: str, canary_file: Path) -> tuple[list[Path], dict]:
    m = json.loads(SET_MANIFEST.read_text(encoding="utf-8"))
    files = sorted(QUESTIONS.glob("question_*.yaml"))
    if {f.name: sha256_file(f) for f in files} != m["files"]:
        raise SystemExit("question files differ from SET_MANIFEST.json: run "
                         "benchmark/scripts/make_set_manifest.py --check; re-freeze before a run")
    if mode == "full":
        return files, m
    ids = [ln.strip() for ln in canary_file.read_text(encoding="utf-8").splitlines()
           if ln.strip() and not ln.startswith("#")]
    paths = [QUESTIONS / f"{i}.yaml" for i in ids]
    missing = [p.name for p in paths if p.name not in m["files"]]
    if missing:
        raise SystemExit(f"canary questions not in the frozen set: {missing}")
    return paths, m


def ollama_options() -> dict:
    """The pinned Ollama judge settings, read from the evaluator so the manifest cannot drift."""
    sys.path.insert(0, str(SCRIPTS))
    import add_llm_evaluation as ev
    return {"num_ctx": ev.OLLAMA_NUM_CTX, "think": ev.OLLAMA_THINK, "temperature": 0}


def is_claude(model: str) -> bool:
    return model.startswith("claude")


def judge_tag(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def preflight_judges(judges: list[str]) -> None:
    local = [j for j in judges if not is_claude(j)]
    if not local:
        return
    try:
        listing = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise SystemExit(f"Ollama judge(s) {local} requested but `ollama list` failed: {e}")
    names = {ln.split()[0] for ln in listing.splitlines()[1:] if ln.strip()}
    for j in local:
        if j not in names and f"{j}:latest" not in names:
            raise SystemExit(f"Ollama model {j} not pulled (have: {sorted(names)})")


def wait_ready(port: int, proc: subprocess.Popen, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(urllib.request.Request(
                f"http://127.0.0.1:{port}/mcp", headers={"Accept": "text/event-stream"}), timeout=5)
            return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(1.0)
    return False


def production_server_version() -> str | None:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "benchmark-runner", "version": "1"}}}).encode()
    req = urllib.request.Request(PRODUCTION_URL, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.removeprefix("data:").strip()
        if line.startswith("{"):
            try:
                return json.loads(line)["result"]["serverInfo"]["version"]
            except (ValueError, KeyError):
                continue
    return None


def tool_counts(log: Path) -> tuple[dict[str, int], dict]:
    counts, meta = {}, {}
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            counts[r.get("tool")] = counts.get(r.get("tool"), 0) + 1
            if isinstance(r.get("meta"), dict):
                meta = r["meta"]
    return counts, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["canary", "full"], required=True)
    ap.add_argument("--answer-model", default=DEFAULT_ANSWER_MODEL)
    ap.add_argument("--judges", default=",".join(DEFAULT_JUDGES),
                    help="comma-separated judge models; the FIRST is the primary judge. claude-* "
                         "judge via the Anthropic API, anything else via Ollama.")
    ap.add_argument("--replicates", type=int, default=None, help="default: canary 1, full 3")
    ap.add_argument("--target", choices=["local", "production"], default="local")
    ap.add_argument("--mie-dir", default=str(REPO / "togo_mcp" / "data" / "mie"),
                    help="MIE corpus the local server serves (default: the working tree's)")
    ap.add_argument("--base-config", default=str(DEFAULT_BASE_CONFIG))
    ap.add_argument("--canary-file", default=str(DEFAULT_CANARY))
    ap.add_argument("--price-in", type=float, help="USD/MTok input, for a model not in PRICING")
    ap.add_argument("--price-out", type=float, help="USD/MTok output, for a model not in PRICING")
    ap.add_argument("--out", help="run dir (default: benchmark/results/<date>/<model>/<mode>)")
    ap.add_argument("--usage-log", help="production tool-call JSONL for the usage-log section")
    ap.add_argument("--port", type=int, default=8976)
    ap.add_argument("--dry-run", action="store_true",
                    help="check inputs, boot the server, print plan + estimate; no API calls")
    args = ap.parse_args()

    judges = [j.strip() for j in args.judges.split(",") if j.strip()]
    reps = args.replicates or (1 if args.mode == "canary" else 3)
    questions, set_manifest = frozen_questions(args.mode, Path(args.canary_file))
    if args.answer_model in PRICING:
        price = PRICING[args.answer_model]
    elif args.price_in is not None and args.price_out is not None:
        price = (args.price_in, args.price_out)
    else:
        raise SystemExit(f"no pricing for {args.answer_model}: pass --price-in/--price-out")
    preflight_judges(judges)
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is required: answering and Claude judging go through "
                         "the API (the subscription degrades into login-error stubs on long runs)")

    started = datetime.datetime.now().astimezone()
    out = Path(args.out) if args.out else (REPO / "benchmark" / "results" / started.date().isoformat()
                                           / args.answer_model / args.mode)
    out = out.resolve()
    if args.dry_run:
        import tempfile
        out = Path(tempfile.mkdtemp(prefix="benchmark-runner-dry-"))
    elif (out / "manifest.json").exists():
        raise SystemExit(f"{out} already holds a run; pass a new --out (runs are never overwritten)")

    cells = len(questions) * reps
    n_claude = sum(is_claude(j) for j in judges)
    est_usd = cells * (EST_ANSWER_USD + n_claude * EST_CLAUDE_JUDGE_USD)
    est_h = cells * EST_MIN_PER_CELL / 60
    est_ollama_h = cells * EST_OLLAMA_MIN_PER_CELL * (len(judges) - n_claude) / 60
    print(f"plan: mode={args.mode} questions={len(questions)} replicates={reps} cells={cells}\n"
          f"      answer={args.answer_model} judges={judges} (primary {judges[0]})\n"
          f"      target={args.target}"
          f"{' mie-dir=' + args.mie_dir if args.target == 'local' else ''}\n"
          f"      out={out}\n"
          f"estimate: about ${est_usd:.0f}; {est_h:.1f} h answering + {est_ollama_h:.1f} h local "
          f"judging (planning figures from the 2026-10-01 Sonnet 5.5 pilot)")

    out.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load(Path(args.base_config).read_text(encoding="utf-8"))
    cfg["model"] = args.answer_model
    cfg["pricing"] = {"input_per_million": price[0], "output_per_million": price[1]}
    if "find_databases" in str(cfg.get("togomcp_system_prompt", "")):
        raise SystemExit(f"{args.base_config} names the retired find_databases(); use a 2026-10 config")
    url = PRODUCTION_URL if args.target == "production" else f"http://127.0.0.1:{args.port}/mcp"
    cfg["mcp_servers"]["togomcp"] = {"type": "http", "url": url}
    cfg_path = out / "config.rendered.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")

    log = out / "toolcalls.jsonl"
    server = None
    if args.target == "local":
        env = dict(os.environ, TOGOMCP_MIE_DIR=str(Path(args.mie_dir).resolve()),
                   ABLATION_PORT=str(args.port), TOGOMCP_QUERY_LOG=str(log))
        server = subprocess.Popen([sys.executable, str(SERVE)], env=env,
                                  stdout=(out / "server.log").open("w"), stderr=subprocess.STDOUT)
        if not wait_ready(args.port, server):
            server.kill()
            raise SystemExit(f"local server did not come up on :{args.port}; see {out / 'server.log'}")
    try:
        if args.dry_run:
            print(f"DRY-RUN OK: questions frozen, judges available, config rendered, "
                  f"server {'up' if server else 'n/a (production)'}")
            shutil.rmtree(out, ignore_errors=True)
            return 0
        for r in range(1, reps + 1):
            subprocess.run([sys.executable, str(RUNNER), *map(str, questions), "-c", str(cfg_path),
                            "--model", args.answer_model, "-o", str(out / f"answers-v{r}.csv")],
                           check=True, cwd=str(SCRIPTS), env=os.environ)
    finally:
        if server:
            server.terminate()
            server.wait(timeout=15)

    counts, meta = tool_counts(log)
    if args.target == "local":
        if sum(counts.values()) == 0:
            raise SystemExit("GUARD: the local server executed ZERO tool calls; the agent did not use "
                             "it. Not judging. Check config.rendered.yaml.")
        if not counts.get("get_MIE_file"):
            raise SystemExit("GUARD: get_MIE_file never executed; the MIE was never served. Not judging.")

    for j in judges:
        for r in range(1, reps + 1):
            cmd = [sys.executable, str(EVALUATOR), str(out / f"answers-v{r}.csv"),
                   "-o", str(out / f"scored-{judge_tag(j)}-v{r}.csv"), "--model", j]
            cmd += ["--use-api"] if is_claude(j) else ["--provider", "ollama"]
            subprocess.run(cmd, check=True, cwd=str(SCRIPTS), env=os.environ)

    manifest = {
        "mode": args.mode,
        "started": started.isoformat(timespec="seconds"),
        "finished": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "answer_model": args.answer_model,
        "judge_models": [judge_tag(j) for j in judges],
        "replicates": reps,
        "question_set_hash": set_manifest["set_hash"],
        "n_questions": len(questions),
        "question_list": str(Path(args.canary_file).relative_to(REPO)) if args.mode == "canary" else "all",
        "target": "local " + str(Path(args.mie_dir).resolve().relative_to(REPO))
                  if args.target == "local" else f"production {PRODUCTION_URL}",
        "server_version": meta.get("server_version") if meta else production_server_version(),
        "usage_guide_version": meta.get("usage_guide_version"),
        "mie_bundle_version": meta.get("mie_bundle_version"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain", "--", "togo_mcp", "benchmark/scripts")),
        "baseline": "no-tool answer produced in the same batch, per question",
        "base_config": str(Path(args.base_config).resolve().relative_to(REPO)),
        "base_config_sha256": sha256_file(Path(args.base_config)),
        "pricing_usd_per_mtok": list(price),
        "ollama_judge_options": ollama_options() if any(not is_claude(j) for j in judges) else None,
        "tool_calls": counts,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    cmd = [sys.executable, str(SUMMARIZER), str(out)]
    if args.usage_log:
        cmd += ["--usage-log", args.usage_log]
    subprocess.run(cmd, check=True)
    print(f"\nreport: {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
