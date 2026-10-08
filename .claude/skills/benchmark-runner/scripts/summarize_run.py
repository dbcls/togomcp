#!/usr/bin/env python3
"""Summarize one benchmark-runner run directory: summary.csv, report.md, diff vs previous run.

A run directory (benchmark/results/<date>/<answer-model>/<mode>/) holds:
    manifest.json                 written by run_benchmark.py
    answers-v<R>.csv              automated_test_runner.py output, one per replicate
    scored-<judge>-v<R>.csv       add_llm_evaluation.py output, one per judge x replicate
    toolcalls.jsonl               the local server's tool-call log (TOGOMCP_QUERY_LOG)

Every answer cell is classified before scoring is aggregated:
    refusal  content-policy refusal (both known formats, see answer_screen.REFUSAL_RE: "...violate
             our Usage Policy..." and "API Error: ... can't help with this ... [bio]"): the
             answer is the API's refusal text, scored at the floor; excluded (Trap 8)
    stub     failed or login-error answer ("Not logged in", "[ERROR: Empty response...",
             success=False); excluded
    valid    everything else
Excluded counts are reported per arm; raw (unexcluded) means are reported next to the clean
ones so nothing is hidden. A judge score of 0 is add_llm_evaluation's failed-judge sentinel and
is treated as missing.

The diff compares per-question means with the most recent earlier run of the same mode. That
is DRIFT (server, MIE, data, model or judge changed between runs), not a paired effect: never
read a cross-run difference as the effect of one change unless the manifests agree on
everything else. The report says which manifest fields differ.

Usage:
    python summarize_run.py <run_dir> [--usage-log <jsonl>] [--previous <run_dir>]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
QUESTIONS = REPO / "benchmark" / "questions"
RESULTS_ROOT = REPO / "benchmark" / "results"
sys.path.insert(0, str(REPO))

sys.path.insert(0, str(REPO / "benchmark" / "scripts"))
from answer_screen import classify  # noqa: E402  (shared with results_analyzer.py)
SCORE_COLS = ("recall", "precision", "repetition", "readability", "total_score")
DIFF_FLAG = 3.0   # per-question |delta| (points of 20) worth listing in the diff


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_questions() -> dict[str, dict]:
    out = {}
    for f in sorted(QUESTIONS.glob("question_*.yaml")):
        q = yaml.safe_load(f.read_text(encoding="utf-8"))
        out[q["id"]] = {"type": q["type"], "held_out": bool(q.get("held_out", False)),
                        "databases": list(q.get("togomcp_databases_used") or [])}
    return out


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def scored_files(run: Path) -> dict[str, list[Path]]:
    """judge -> [scored-<judge>-v1.csv, ...]"""
    by: dict[str, list[Path]] = defaultdict(list)
    for f in sorted(run.glob("scored-*-v*.csv")):
        m = re.match(r"scored-(.+)-v(\d+)\.csv$", f.name)
        if m:
            by[m.group(1)].append(f)
    return dict(by)


# ---------------------------------------------------------------------------
# per-question aggregation
# ---------------------------------------------------------------------------
def aggregate(run: Path, questions: dict[str, dict]):
    """Return (rows, cells): per (judge, question) means and per-arm exclusion counts."""
    cells = Counter()          # (judge, arm, class) -> n
    per = defaultdict(lambda: {"tm": [], "base": [], "tm_raw": [], "base_raw": []})
    for judge, files in scored_files(run).items():
        for f in files:
            with f.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    qid = r.get("question_id")
                    if not qid:
                        continue
                    for arm, pre in (("tm", "togomcp"), ("base", "baseline")):
                        cls = classify(r.get(f"{pre}_answer", ""), r.get(f"{pre}_success", ""))
                        cells[(judge, arm, cls)] += 1
                        s = num(r.get(f"{pre}_total_score"))
                        if s is None or s == 0:      # 0 = failed-judge sentinel
                            cells[(judge, arm, "judge_failed")] += 1
                            continue
                        per[(judge, qid)][f"{arm}_raw"].append(s)
                        if cls == "valid":
                            per[(judge, qid)][arm].append(s)
    rows = []
    for (judge, qid), d in sorted(per.items()):
        q = questions.get(qid, {})
        mt = st.mean(d["tm"]) if d["tm"] else None
        mb = st.mean(d["base"]) if d["base"] else None
        rows.append({
            "judge": judge, "question_id": qid, "type": q.get("type", ""),
            "held_out": q.get("held_out", False),
            "n_tm": len(d["tm"]), "tm_mean": mt,
            "n_base": len(d["base"]), "base_mean": mb,
            "delta": (mt - mb) if mt is not None and mb is not None else None,
            "tm_raw_mean": st.mean(d["tm_raw"]) if d["tm_raw"] else None,
            "base_raw_mean": st.mean(d["base_raw"]) if d["base_raw"] else None,
        })
    return rows, cells


def mean_of(rows, key, **filt):
    vals = [r[key] for r in rows if r[key] is not None
            and all(r[k] == v for k, v in filt.items())]
    return (st.mean(vals), len(vals)) if vals else (None, 0)


def paired_delta(rows, **filt):
    """Mean of per-question (TogoMCP - no-tool), with a 95% CI (t approx by 1.96)."""
    d = [r["delta"] for r in rows if r["delta"] is not None
         and all(r[k] == v for k, v in filt.items())]
    if not d:
        return None, None, 0
    m = st.mean(d)
    ci = 1.96 * st.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else None
    return m, ci, len(d)


# ---------------------------------------------------------------------------
# operational metrics and tool calls
# ---------------------------------------------------------------------------
def operational(run: Path) -> dict:
    rows = []
    for f in sorted(run.glob("answers-v*.csv")):
        with f.open(encoding="utf-8") as fh:
            rows += list(csv.DictReader(fh))
    if not rows:
        return {}
    g = lambda r, k: num(r.get(k)) or 0.0
    t = [g(r, "togomcp_time") for r in rows]
    c = [g(r, "togomcp_cost_usd") for r in rows]
    cb = [g(r, "baseline_cost_usd") for r in rows]
    return {
        "cells": len(rows),
        "tm_time_mean_s": st.mean(t), "tm_time_median_s": st.median(t),
        "tm_cost_mean": st.mean(c), "tm_cost_median": st.median(c),
        "base_cost_mean": st.mean(cb),
        "answer_cost_total": sum(c) + sum(cb),
        "tm_input_tokens_mean": st.mean(g(r, "togomcp_input_tokens") for r in rows),
        "tm_cache_creation_mean": st.mean(g(r, "togomcp_cache_creation_tokens") for r in rows),
        "tm_cache_read_mean": st.mean(g(r, "togomcp_cache_read_tokens") for r in rows),
        "tm_total_input_mean": st.mean(g(r, "togomcp_total_input_tokens") for r in rows),
    }


def sparql_profile(records) -> dict:
    from togo_mcp.stats import sparql_class
    cls = Counter(c for c in (sparql_class(r) for r in records) if c)
    n = sum(cls.values())
    err = sum(v for k, v in cls.items() if k not in ("ok", "empty_result", "huge_result"))
    return {"n": n, "error_rate": err / n if n else None,
            "empty_rate": cls["empty_result"] / n if n else None, "classes": dict(cls)}


def tool_profile(run: Path) -> dict:
    from togo_mcp.stats import iter_records
    recs = list(iter_records([str(run / "toolcalls.jsonl")]))
    meta = next((r["meta"] for r in reversed(recs) if isinstance(r.get("meta"), dict)), {})
    return {"n_calls": len(recs), "by_tool": dict(Counter(r.get("tool") for r in recs)),
            "meta": {k: meta.get(k) for k in ("server_version", "usage_guide_version",
                                               "mie_bundle_version")},
            "sparql": sparql_profile(recs), "records": recs}


# ---------------------------------------------------------------------------
# usage-log link
# ---------------------------------------------------------------------------
# Self-hosted clients are judged by calls per IP; hosted clients (claude.ai, claude-code,
# ChatGPT) exit through shared egress, so their IPs are not users and are never filtered
# that way. The default SDK name `mcp` was the 2026-07 load-test harness.
SYNTHETIC_CLIENTS = {"mcp", "glyconavi", "mcporter"}
HOSTED_CLIENT_PREFIXES = ("Anthropic/", "claude-code", "openai-mcp")
BATCH_SESSION_CALLS = 100    # sessions this long with repeated guide calls are batch evals


def real_usage(records: list[dict]) -> tuple[list[dict], dict]:
    from togo_mcp.stats import client_of
    dropped = Counter()
    by_session = defaultdict(list)
    for r in records:
        if r.get("session_id"):
            by_session[r["session_id"]].append(r)
    batch_sessions = {s for s, rs in by_session.items()
                      if len(rs) >= BATCH_SESSION_CALLS
                      and sum(x.get("tool") == "TogoMCP_Usage_Guide" for x in rs) >= 5}
    per_ip = Counter((client_of(r), r.get("ip_hash") or r.get("ip")) for r in records)
    kept = []
    for r in records:
        client = client_of(r)
        if client in SYNTHETIC_CLIENTS:
            dropped[f"client:{client}"] += 1
            continue
        if r.get("session_id") in batch_sessions:
            dropped["batch-eval session"] += 1
            continue
        if not client.startswith(HOSTED_CLIENT_PREFIXES) and \
                per_ip[(client, r.get("ip_hash") or r.get("ip"))] > 300:
            dropped[f"high-volume self-hosted IP ({client})"] += 1
            continue
        kept.append(r)
    return kept, dict(dropped)


def usage_section(log_path: Path, questions: dict, bench_sparql: dict) -> list[str]:
    from togo_mcp.stats import client_of, database_of, iter_records, load_endpoint_groups
    recs = list(iter_records([str(log_path)]))
    kept, dropped = real_usage(recs)
    groups = load_endpoint_groups(str(REPO / "togo_mcp" / "data" / "resources" / "endpoints.csv"))
    ep_csv = REPO / "togo_mcp" / "data" / "resources" / "endpoints.csv"
    with ep_csv.open(encoding="utf-8") as fh:
        registered = {row["database"] for row in csv.DictReader(fh)}
    attributed = Counter(d for d in (database_of(r, groups) for r in kept) if d)
    # Agents pass invented names (database="notarealdb", "hsa"); the server rejects them, so
    # they are not use of any database. Cross-DB endpoint calls are kept under their own label.
    real_db = Counter({d: n for d, n in attributed.items()
                       if d in registered or d.endswith("(cross-db)")})
    invalid = Counter({d: n for d, n in attributed.items() if d not in real_db})
    # Concentration: share of a database's calls from its single largest (client, /24) source.
    # A high share means one agent or pipeline, not broad demand. Hosted clients share egress
    # networks, so a high share there is "one network", which may still be many users.
    src = defaultdict(Counter)
    for r in kept:
        d = database_of(r, groups)
        if d in real_db:
            ip = r.get("ip") or ""
            net = ip.rsplit(".", 1)[0] + ".0/24" if ip.count(".") == 3 else (r.get("ip_hash") or "?")
            src[d][(client_of(r), net)] += 1
    q_db = Counter(db for q in questions.values() for db in q["databases"])
    ts = sorted(r.get("ts", "") for r in recs if r.get("ts"))
    real_sparql = sparql_profile(kept)
    tot_r, tot_q = sum(real_db.values()) or 1, sum(q_db.values()) or 1
    out = ["## Usage log vs benchmark", "",
           f"Log: `{log_path.name}`, {len(recs):,} records ({ts[0][:10] if ts else '?'} to "
           f"{ts[-1][:10] if ts else '?'}). Kept {len(kept):,} as real use after excluding "
           + (", ".join(f"{k} {v:,}" for k, v in sorted(dropped.items())) or "nothing") + ".",
           "", "### Database distribution (share of database-attributed calls vs share of "
           "question database mentions)", "",
           "| Database | Real use | Question set | Top source (share) |", "|---|---:|---:|---|"]
    for db in sorted(set(real_db) | set(q_db), key=lambda d: -(real_db[d] / tot_r + q_db[d] / tot_q))[:25]:
        top = src[db].most_common(1)
        top_s = (f"{top[0][0][0]} {top[0][0][1]} ({top[0][1] / real_db[db]:.0%})"
                 if top else "")
        out.append(f"| {db} | {real_db[db] / tot_r:.1%} ({real_db[db]}) | "
                   f"{q_db[db] / tot_q:.1%} ({q_db[db]}) | {top_s} |")
    unused = sorted(d for d in real_db if d not in q_db and not d.endswith("(cross-db)"))
    if unused:
        out += ["", "Used in practice but in no question: " + ", ".join(unused)]
    if invalid:
        out += ["", f"Calls naming an unregistered database (rejected by the server, not counted "
                f"above): {sum(invalid.values())} ("
                + ", ".join(f"{d} {n}" for d, n in invalid.most_common(8)) + ")"]
    fmt = lambda p: f"{p['error_rate']:.1%}" if p["error_rate"] is not None else "n/a"
    fmte = lambda p: f"{p['empty_rate']:.1%}" if p["empty_rate"] is not None else "n/a"
    out += ["", "Top source = the largest (client, /24 network) bucket. Anthropic and OpenAI clients "
            "exit through shared networks, so a high share there means one network, not "
            "necessarily one user; for self-hosted clients it usually means one pipeline."]
    out += ["", "### SPARQL outcome", "", "| | SPARQL calls | Error rate | Empty-result rate |",
            "|---|---:|---:|---:|",
            f"| Real use | {real_sparql['n']:,} | {fmt(real_sparql)} | {fmte(real_sparql)} |",
            f"| This benchmark run | {bench_sparql['n']:,} | {fmt(bench_sparql)} | {fmte(bench_sparql)} |",
            "", "Error = timeout, syntax (HTTP 4xx), server, endpoint-down, pool or other errors; "
            "empty results are counted separately because they are often correct answers."]
    return out


# ---------------------------------------------------------------------------
# previous run
# ---------------------------------------------------------------------------
def find_previous(run: Path, manifest: dict) -> Path | None:
    mode = manifest.get("mode")
    cands = []
    for m in RESULTS_ROOT.glob("*/*/*/manifest.json"):
        d = m.parent
        if d.resolve() == run.resolve() or not (d / "summary.csv").exists():
            continue
        try:
            pm = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if pm.get("mode") == mode and pm.get("started", "") < manifest.get("started", "~"):
            cands.append((pm.get("started", ""), d))
    return max(cands)[1] if cands else None


MANIFEST_KEYS = ("question_set_hash", "answer_model", "judge_models", "server_version",
                 "usage_guide_version", "mie_bundle_version", "target", "replicates")


def diff_section(run_rows, manifest, prev: Path, primary: str) -> list[str]:
    pm = json.loads((prev / "manifest.json").read_text(encoding="utf-8"))
    with (prev / "summary.csv").open(encoding="utf-8") as fh:
        prows = [r for r in csv.DictReader(fh) if r["judge"] == primary]
    pmap = {r["question_id"]: num(r["tm_mean"]) for r in prows}
    pbase = {r["question_id"]: num(r["base_mean"]) for r in prows}
    out = ["## Diff against the previous run", "",
           f"Previous: `{prev.relative_to(REPO)}` (started {pm.get('started', '?')}).", ""]
    changed = [(k, pm.get(k), manifest.get(k)) for k in MANIFEST_KEYS if pm.get(k) != manifest.get(k)]
    if changed:
        out += ["Manifest fields that differ (any difference below may come from these):", "",
                "| Field | Previous | This run |", "|---|---|---|"]
        out += [f"| {k} | {a} | {b} |" for k, a, b in changed]
        if any(k in ("answer_model", "judge_models") for k, _, _ in changed):
            out += ["", "**A model changed: this diff is not a time-series point. Run the bridge "
                    "procedure (SKILL.md) before comparing.**"]
    else:
        out.append("All manifest fields agree; differences are run-to-run or data drift.")
    cur = {r["question_id"]: r for r in run_rows if r["judge"] == primary}
    common = sorted(set(cur) & set(pmap))
    d_tm = [cur[q]["tm_mean"] - pmap[q] for q in common
            if cur[q]["tm_mean"] is not None and pmap[q] is not None]
    d_b = [cur[q]["base_mean"] - pbase[q] for q in common
           if cur[q]["base_mean"] is not None and pbase.get(q) is not None]
    out += ["", f"Questions in both runs: {len(common)}. Mean change ({primary}): "
            f"TogoMCP {st.mean(d_tm):+.2f}, no-tool {st.mean(d_b):+.2f}." if d_tm and d_b else
            f"Questions in both runs: {len(common)}."]
    flagged = [(q, pmap[q], cur[q]["tm_mean"]) for q in common
               if cur[q]["tm_mean"] is not None and pmap[q] is not None
               and abs(cur[q]["tm_mean"] - pmap[q]) >= DIFF_FLAG]
    if flagged:
        out += ["", f"Questions whose TogoMCP mean moved by {DIFF_FLAG:.0f} or more:", "",
                "| Question | Previous | This run | Change |", "|---|---:|---:|---:|"]
        out += [f"| {q} | {a:.1f} | {b:.1f} | {b - a:+.1f} |" for q, a, b in sorted(flagged)]
    return out


# ---------------------------------------------------------------------------
# inter-judge agreement
# ---------------------------------------------------------------------------
def _pearson(x, y):
    if len(x) < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else None


def _rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def judge_agreement(rows, judges) -> list[str]:
    if len(judges) < 2:
        return []
    out = ["## Judge agreement (per-question TogoMCP means)", "",
           "| Judges | n | Pearson | Spearman | Mean offset |", "|---|---:|---:|---:|---:|"]
    by = {(r["judge"], r["question_id"]): r["tm_mean"] for r in rows}
    for i, a in enumerate(judges):
        for b in judges[i + 1:]:
            qs = [q for (j, q) in by if j == a and by.get((b, q)) is not None and by[(a, q)] is not None]
            x, y = [by[(a, q)] for q in qs], [by[(b, q)] for q in qs]
            p = _pearson(x, y)
            s = _pearson(_rank(x), _rank(y)) if len(x) >= 3 else None
            off = st.mean(xx - yy for xx, yy in zip(x, y)) if x else None
            f = lambda v: f"{v:.2f}" if v is not None else "n/a"
            out.append(f"| {a} vs {b} | {len(qs)} | {f(p)} | {f(s)} | {f(off)} |")
    out += ["", "Full agreement statistics (ICC, per-criterion) are a separate analysis; this "
            "table is the per-run health check that both judges still rank questions alike."]
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--usage-log", help="production tool-call JSONL (/stats/log download)")
    ap.add_argument("--previous", help="run dir to diff against (default: latest earlier run "
                                       "of the same mode under benchmark/results)")
    args = ap.parse_args()
    run = Path(args.run_dir).resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    questions = load_questions()
    rows, cells = aggregate(run, questions)
    if not rows:
        print(f"no scored-<judge>-v*.csv files in {run}", file=sys.stderr)
        return 1
    judges = manifest.get("judge_models") or sorted({r["judge"] for r in rows})
    judges = [j for j in judges if any(r["judge"] == j for r in rows)]
    primary = judges[0]

    with (run / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4g}" if isinstance(v, float) else v) for k, v in r.items()})

    ops = operational(run)
    tools = tool_profile(run) if (run / "toolcalls.jsonl").exists() else None
    f2 = lambda v: f"{v:.2f}" if v is not None else "n/a"
    L = [f"# Benchmark run: {manifest.get('mode')} / {manifest.get('answer_model')} / "
         f"{manifest.get('started', '')[:10]}", "",
         "| Field | Value |", "|---|---|"]
    for k in ("mode", "answer_model", "judge_models", "replicates", "question_set_hash",
              "n_questions", "target", "server_version", "usage_guide_version",
              "mie_bundle_version", "git_commit", "started", "finished"):
        L.append(f"| {k} | {manifest.get(k)} |")
    L += ["", "## Scores (refusal- and stub-clean; raw in parentheses)", "",
          "| Judge | TogoMCP | No-tool | Δ (paired) | 95% CI | n |", "|---|---:|---:|---:|---:|---:|"]
    for j in judges:
        mt, _ = mean_of(rows, "tm_mean", judge=j)
        mb, _ = mean_of(rows, "base_mean", judge=j)
        rt, _ = mean_of(rows, "tm_raw_mean", judge=j)
        rb, _ = mean_of(rows, "base_raw_mean", judge=j)
        d, ci, n = paired_delta(rows, judge=j)
        L.append(f"| {j} | {f2(mt)} ({f2(rt)}) | {f2(mb)} ({f2(rb)}) | {f2(d)} | "
                 f"{'±' + f2(ci) if ci else 'n/a'} | {n} |")
    for label, key, vals in (("type", "type", sorted({r['type'] for r in rows})),
                             ("held-out", "held_out", [True, False])):
        L += ["", f"### By {label} ({primary})", "",
              f"| {label} | TogoMCP | No-tool | Δ | n |", "|---|---:|---:|---:|---:|"]
        for v in vals:
            mt, n = mean_of(rows, "tm_mean", judge=primary, **{key: v})
            mb, _ = mean_of(rows, "base_mean", judge=primary, **{key: v})
            d, _, _ = paired_delta(rows, judge=primary, **{key: v})
            name = {True: "held-out", False: "development"}.get(v, v) if key == "held_out" else v
            L.append(f"| {name} | {f2(mt)} | {f2(mb)} | {f2(d)} | {n} |")
    L += ["", "## Excluded cells", "", "| Judge | Arm | Refusal | Stub | Judge failed | Valid |",
          "|---|---|---:|---:|---:|---:|"]
    for j in judges:
        for arm in ("tm", "base"):
            L.append(f"| {j} | {'TogoMCP' if arm == 'tm' else 'no-tool'} | "
                     f"{cells[(j, arm, 'refusal')]} | {cells[(j, arm, 'stub')]} | "
                     f"{cells[(j, arm, 'judge_failed')]} | {cells[(j, arm, 'valid')]} |")
    if ops:
        d, _, _ = paired_delta(rows, judge=primary)
        L += ["", "## Operational metrics (TogoMCP arm, per cell)", "",
              "| Metric | Value |", "|---|---:|",
              f"| Cells | {ops['cells']} |",
              f"| Time mean / median (s) | {ops['tm_time_mean_s']:.0f} / {ops['tm_time_median_s']:.0f} |",
              f"| Cost mean / median (USD) | {ops['tm_cost_mean']:.3f} / {ops['tm_cost_median']:.3f} |",
              f"| No-tool cost mean (USD) | {ops['base_cost_mean']:.3f} |",
              f"| Input tokens: uncached / cache-write / cache-read (mean) | "
              f"{ops['tm_input_tokens_mean']:.0f} / {ops['tm_cache_creation_mean']:.0f} / "
              f"{ops['tm_cache_read_mean']:.0f} |",
              f"| Answering cost, whole run (USD, judges excluded) | {ops['answer_cost_total']:.2f} |"]
        if d:
            L.append(f"| TogoMCP cost per point of Δ (USD) | {ops['tm_cost_mean'] / d:.3f} |")
    if tools:
        L += ["", "## Tool calls (local server log)", "",
              f"{tools['n_calls']:,} calls: " + ", ".join(
                  f"{k} {v}" for k, v in sorted(tools["by_tool"].items(), key=lambda x: -x[1])),
              "", f"SPARQL: {tools['sparql']['n']} calls, error rate "
              f"{f2(tools['sparql']['error_rate'] and tools['sparql']['error_rate'] * 100)}%, "
              f"classes {tools['sparql']['classes']}."]
    L += [""] + judge_agreement(rows, judges)
    prev = Path(args.previous).resolve() if args.previous else find_previous(run, manifest)
    L += [""] + (diff_section(rows, manifest, prev, primary) if prev else
                 ["## Diff against the previous run", "", "No earlier run of this mode found."])
    if args.usage_log:
        bench = tools["sparql"] if tools else {"n": 0, "error_rate": None, "empty_rate": None}
        L += [""] + usage_section(Path(args.usage_log), questions, bench)
    (run / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {run / 'summary.csv'} and {run / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
