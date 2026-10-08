---
name: benchmark-runner
description: Run the TogoMCP benchmark periodically and report it — a canary (10 fixed questions) or the full frozen question set — answering with TogoMCP and a same-batch no-tool baseline, judging with Claude plus a local Gemma4 judge, and writing benchmark/results/<date>/<model>/<mode>/ with a manifest, summary.csv, report.md, a diff against the previous run and a usage-log comparison. Use whenever the user asks to "run the benchmark", "run the canary", "do the periodic evaluation", "check whether TogoMCP regressed", "evaluate the new release / new MIEs / new model", "compare with last month's run", or to re-summarize an existing run. Developer skill: never move it under togo_mcp/data/skills/public/.
---

# TogoMCP Benchmark Runner

Contract item 2.4 (periodic evaluation). Two scripts do the work; this file is the procedure
and the rules around them.

| Script | Does |
|---|---|
| `scripts/run_benchmark.py` | answer → guard → judge → manifest → summarize. Spends API money unless `--dry-run`. |
| `scripts/summarize_run.py` | rebuilds `summary.csv` + `report.md` for any run dir, free. Re-run it after adding a judge or to attach a usage log. |

## Procedure

1. **Check the question set is frozen.** `python benchmark/scripts/make_set_manifest.py --check`.
   If it fails, questions changed since the freeze: stop and ask the user whether to re-freeze
   (`make_set_manifest.py`, then commit). Every run records the set hash; runs on different
   hashes are not comparable question for question.
2. **Dry run and estimate.** `uv run python .claude/skills/benchmark-runner/scripts/run_benchmark.py
   --mode canary --dry-run` (or `--mode full`). It checks the freeze, the judges (Ollama model
   pulled), the config, boots the local server, and prints the plan and an estimate.
3. **Get approval before any paid run.** Show the user: mode, question count, replicates, cells,
   answering and judge models, target (local corpus or production), estimated cost and wall
   time. Wait for an explicit yes. Planning figures (2026-10-01, Sonnet 5.5 + Opus 4.8): about
   $0.31 per cell and 1.1 min per cell; canary ≈ $3 and 15 min, full (110 × 3) ≈ $100 and 6 h.
   Gemma4 judging is free but slow: about 46 s per judgement on the developer Mac (two per cell,
   TogoMCP and no-tool), so ≈ 15 min for a canary and ≈ 8.5 h for a full run, after answering.
4. **Run detached.** A full run outlives a tool timeout, so launch with `nohup` and
   `ANTHROPIC_API_KEY` set (e.g. `ANTHROPIC_API_KEY=$MY_ANTHROPIC_API_KEY nohup uv run python
   .../run_benchmark.py --mode full > <log> 2>&1 &`). Answering and the Claude judge go through
   the API; the `claude login` subscription degrades into "Not logged in" stubs on long runs.
5. **Read the report** (`report.md`) and relay to the user: scores per judge with the paired Δ
   and CI, the held-out vs development split, excluded-cell counts, operational metrics, judge
   agreement, the diff against the previous run, and the usage-log section if a log was given.

To re-summarize, or to add the usage-log section to an existing run:
`uv run python .claude/skills/benchmark-runner/scripts/summarize_run.py <run_dir> --usage-log <jsonl>`.

## Modes

- **canary**: the 10 questions in `benchmark/scripts/canary_questions_2026_10.txt` (2 per type;
  4 held-out + 6 hard development questions, refusal-prone questions excluded). 1 replicate by
  default. Use it after any change to the server, the MIEs, the Usage Guide, or upstream data, and
  before every release. It is a smoke alarm, not a measurement: 10 questions × 1 replicate cannot
  resolve small effects.
- **full**: all questions of the frozen set, 3 replicates by default. Use it on a schedule (for
  example quarterly) and for the report.

Do not use `benchmark/studies/redesign/release/canary_questions.txt` as the canary: it holds the
retired Q022 and the v3 MIEs were tuned on it. It stays unchanged for the release study.

## Targets

- **local** (default): a local server (`benchmark/studies/ablation/_serve.py`) serving `--mie-dir`
  (default: the working tree's `togo_mcp/data/mie/`). It writes this run's own tool-call log, which
  gives the manifest its `server_version`, `usage_guide_version` and `mie_bundle_version` (a
  content hash of the served MIEs), enables the tool-call guards, and gives the benchmark SPARQL
  error rate for the usage-log comparison.
- **production**: answers against `https://togomcp.rdfportal.org/mcp`. The server version comes
  from `initialize`; the MIE bundle version is unknown, and there is no tool-call guard. Say so
  whenever its numbers are reported. Production can lag `dev` (on 2026-10-01 it lacked four MIE
  gotchas), so local and production runs are different instruments.

## Models

- **Answering:** `claude-sonnet-5-5` by default. Always pass model IDs explicitly; the manifest
  records them.
- **Judges:** `claude-opus-4-8` (primary, via the API) and `gemma4` (via Ollama, no API cost). The
  first judge listed is the primary one used for the by-type, held-out and diff tables.
  The Ollama judge settings are pinned in `add_llm_evaluation.py` (`num_ctx` 16384, because
  Ollama's 4096 default silently drops the rubric once prompt + reasoning outgrow it; `think`
  on, as for every Gemma4 judgement since 2026-10-01; temperature 0) and recorded in the
  manifest as `ollama_judge_options`. Changing either is a judge change: bridge it.
- **Bridge on any model change.** When the answering or judge model changes (including ahead of an
  announced retirement: Sonnet 4.5 retires 2026-11-30), the time series breaks unless both models
  are measured on the same answers:
  1. Run one reference run with the OLD model and one with the NEW model, same target, same
     frozen set, same week (canary at least; full if the change will carry a report).
  2. For a judge change, re-judge the SAME answers with both judges instead of re-answering
     (`summarize_run.py` reports the agreement and the mean offset).
  3. Record both runs' paths and the offset in the new run's `report.md`, and treat the new run as
     the start of a new series. The diff table flags a model change and says this.
- **Pricing.** `run_benchmark.py` carries a per-model price table; a model missing from it must be
  priced with `--price-in/--price-out`.

## Guards (automatic)

- **Fresh in-batch baseline:** every question's no-tool answer is produced in the same batch as its
  TogoMCP answer. Never compare against a baseline from another run (ablation FINDINGS, Trap 1).
- **The server did the work:** on a local target, judging is refused if the server executed zero
  tool calls, or if `get_MIE_file` never ran.
- **Excluded cells, counted:** content-policy refusals, login stubs ("Not logged in"), empty or
  failed answers are excluded from the clean means and counted per arm in the report; raw means
  are shown next to the clean ones (Trap 8). Two refusal formats are detected
  (`benchmark/scripts/answer_screen.py`): "…violate our Usage Policy…" (2026-07) and, since
  2026-10, "API Error: Sonnet 4.5 can't help with this. … Details: `[bio]` …". The second hit 50+
  Sonnet 4.5 cells in the 2026-10 ablation, unevenly across conditions; Sonnet 5.5 produced none
  in the 2026-10 runs. The detector also keys on the AUP link and a leading "API Error:"; a future wording with
  neither would pass as a valid floor-scored answer, so check the
  excluded-cell counts against the lowest-scoring answers after a model change.
- **Judge failures:** a 0 score is the failed-judge sentinel and is treated as missing;
  `add_llm_evaluation.py` aborts after consecutive judge failures.
- **Transcript isolation and audit:** Claude Code lets the answering agent read its own
  transcript folder without asking the runner's gate, and that folder holds other sessions'
  transcripts, including full `get_MIE_file` responses. Every run therefore uses a private
  Claude Code config dir (`claude-config/` in the run dir) and a PreToolUse hook that confines
  Read/Bash to the session's own saved outputs (`strict_isolation` in
  `automated_test_runner.py`); after answering, `benchmark/scripts/audit_transcripts.py` checks
  every transcript and judging is refused if any session read outside its own outputs
  (`transcript_audit.md`).
  The same isolation keeps the repository's auto-memory (`MEMORY.md`) out of the agents' context;
  without it every session gets it. The runner and the Claude judge now fail closed: a
  non-isolated run, or a Claude judge without `--use-api`, is refused unless
  `--allow-memory-exposure` is given.
- **No overwrite:** a run dir that already has a manifest is refused; give a new `--out`.
- **Stale prompt:** a config that still names the retired `find_databases()` is refused.

## Diff against the previous run

`summarize_run.py` picks the most recent earlier run of the same mode (or `--previous`). The
difference between two runs is drift: the server, MIEs, upstream data, models or judge may all have
changed. The report lists every manifest field that differs. Only when they all agree is a
difference run-to-run or data noise. Questions whose TogoMCP mean moved by 3 points or more are
listed; look at those answers before concluding anything.

## Usage-log link

Pass `--usage-log` a production tool-call JSONL (download: `curl -u "$TOGOMCP_STATS_USER:$TOGOMCP_STATS_PASSWORD"
https://togomcp.rdfportal.org/stats/log > togomcp-log-<date>.jsonl`; format in
`TogoMCP_ログファイル仕様.md`). The report then compares (a) the database distribution of real use
with the question set's, and (b) the SPARQL error and empty-result rates of real use with this run's.

Real use is what remains after dropping: the synthetic self-hosted clients (`mcp`, which was the
2026-07 load-test harness and the ChEMBL spike, `glyconavi`, `mcporter`), any other self-hosted
client above 300 calls from one IP, and batch-evaluation sessions (100+ calls with repeated
`TogoMCP_Usage_Guide`). Hosted clients (claude.ai, claude-code, ChatGPT) are never filtered by IP:
they exit through shared egress addresses, so their IPs are not users. The dropped counts are
printed in the report; check them before quoting a distribution.

## Scheduling

On hold (decided with DBCLS, 2026-10, for budget reasons; report section 6). There is no
scheduled run: a person invokes this skill when a canary or full run is wanted. Scheduling stays
possible (the `schedule` skill, or cron on a machine with Ollama and the API key) but needs the
approval rule above replaced by a standing budget agreed with the user and DBCLS.

## Output

`benchmark/results/<date>/<answer-model>/<mode>/` (gitignored): `manifest.json`,
`config.rendered.yaml`, `answers-v<R>.csv`, `scored-<judge>-v<R>.csv`, `toolcalls.jsonl`,
`server.log`, `summary.csv` (per judge × question: means, n, Δ, raw means), `report.md`.
