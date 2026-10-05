#!/usr/bin/env python3
"""Audit answering-agent transcripts for access outside the MCP tools (ablation validity).

The runner's can_use_tool gate denies every non-MCP tool, but Claude Code does NOT consult it
for read-only access inside its own transcript folder (verified 2026-10-02: Read and
grep/find/cat on ~/.claude/projects/<cwd>/ succeed with the gate never called). That folder
holds every session's transcript, including full get_MIE_file responses, so an agent in an
ablated condition could in principle read the full MIE from another session. This script
checks that it did not.

Every SUCCESSFUL non-MCP tool call in each transcript is classified:

    own-output   reads only this session's own files (its saved large tool results)
    compute      Bash with no file path and no network (echo, wc, bc, arithmetic heredocs)
    REVIEW       lists the shared transcript folder without reading another session's file
    VIOLATION    reads another session's files, anything else on disk, or the network

Refused calls (the gate said no) are counted as attempts, not violations.

Injected context is checked too. Claude Code attaches the repository's auto-memory index
(~/.claude/projects/<repo>/memory/MEMORY.md) to every session started inside the repo, and
setting_sources=[] does not prevent it; from 2026-09-30 to 2026-10-05 every benchmark session
carried this project's index (notes on specific questions and database traps). A session with
an AutoMem attachment is counted in the MEMORY column and fails the audit. Runs with a
private CLAUDE_CONFIG_DIR (strict isolation) have none.

Sessions are attributed to a run by time window and answering model (--window), because the
runner does not record session ids. A window is NAME START END [MODEL-SUBSTRING], times in
ISO format with offset, e.g.

    python audit_transcripts.py \\
        --window stage1 2026-10-01T10:46+09:00 2026-10-05T00:00+09:00 sonnet-4-5 \\
        --window sonnet55_full 2026-10-01T11:22+09:00 2026-10-01T16:24+09:00 sonnet-5-5 \\
        --out audit.md

Exit status is 1 if any session in a window has a VIOLATION, so a pipeline can gate on it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_DIR = Path.home() / ".claude" / "projects" / "-Users-arkinjo-work-GitHub-togomcp-benchmark-scripts"
# Network = a command that fetches, not a URL inside a printed string.
NETWORK_CMD = {"curl", "wget", "nc", "ncat", "ssh", "scp", "rsync", "ftp", "telnet"}
NETWORK_CODE_RE = re.compile(r"\burllib\b|\brequests\.(get|post)|\bhttp\.client\b|\bsocket\.")
SAFE_PREFIXES = ("/dev/null", "/dev/stdin", "/dev/stdout", "/dev/stderr", "/tmp/", "/private/tmp/")


def parse_ts(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _tokens(cmd: str) -> list[str]:
    """Shell words of a command with heredoc bodies removed (they are data, not paths)."""
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\1\b", " ", cmd, flags=re.S)
    try:
        return shlex.split(cmd, posix=True)
    except ValueError:
        return cmd.split()


def _paths_from_bash(cmd: str, cwd: str) -> list[str]:
    """Words that name a real file or directory (or a glob over one). A grep pattern that
    happens to start with '/' names nothing on disk and is ignored."""
    out = []
    for w in _tokens(cmd):
        for part in re.split(r"[;&|<>()]+", w):
            part = part.strip().strip("'\"")
            if not part or "/" not in part:
                continue
            explicit = part.startswith(("/", "~", "./", "../"))
            p = os.path.expanduser(part)
            p = p if os.path.isabs(p) else os.path.normpath(os.path.join(cwd, p))
            if not explicit:
                # a bare word with a slash (a sed/awk script, a regex) counts only if it IS a file
                if os.path.exists(p):
                    out.append(p)
                continue
            probe = re.split(r"[*?\[]", p, maxsplit=1)[0].rstrip("/") or "/"
            if os.path.exists(probe) or os.path.exists(os.path.dirname(probe)) and "*" in p:
                out.append(p)
    return out


def classify(name: str, inp: dict, sid: str, folder: str, cwd: str) -> str:
    own = f"{folder}/{sid}"
    # Inter-agent tools. Claude Code auto-approves these too (2026-10-03: a stage-1 agent
    # spawned a sub-agent). A sub-agent's own calls are audited from its transcript under
    # <sid>/subagents/, so spawning one is not itself a read; messaging anyone but the
    # session's own parent is a cross-session channel.
    if name in ("Agent", "Task"):
        return "SUBAGENT"
    if name == "ListAgents":
        return "REVIEW"
    if name == "SendMessage":
        return "REVIEW" if str(inp.get("to", "")).strip() in ("main", "parent") else "VIOLATION"
    if name == "Bash":
        cmd = inp.get("command", "")
        words = {os.path.basename(w) for w in _tokens(cmd)}
        if words & NETWORK_CMD or NETWORK_CODE_RE.search(cmd):
            return "VIOLATION"
        paths = _paths_from_bash(cmd, cwd)
    else:
        paths = [inp[k] for k in ("file_path", "path", "notebook_path") if isinstance(inp.get(k), str)]
        if name in ("Grep", "Glob") and not paths:
            return "VIOLATION"           # defaults to the cwd: the repo
        if not paths:
            return "VIOLATION"
    paths = [p for p in paths if not p.startswith(SAFE_PREFIXES)]
    if not paths:
        return "compute" if name == "Bash" else "own-output"
    if all(p.startswith(own) for p in paths):
        return "own-output"
    folder_wide = all(p.startswith(own) or p.rstrip("/*") == folder for p in paths)
    if folder_wide and name == "Bash":
        cmd = inp.get("command", "")
        words = {os.path.basename(w) for w in _tokens(cmd)}
        # Listing only: find/ls whose output is at most trimmed (head/tail/wc/sort). Anything
        # that opens a file (cat, grep, jq, -exec, xargs ...) reads content and is a violation.
        if words & {"find", "ls"} and "-exec" not in cmd and not words & {
                "cat", "grep", "egrep", "jq", "less", "more", "sed", "awk", "python", "python3",
                "xargs", "strings", "od", "xxd", "cut", "tr", "diff"}:
            return "REVIEW"
    return "VIOLATION"


def audit_session(path: Path, folder: str) -> dict:
    """A session's transcript plus its sub-agents' transcripts, all under the parent's id."""
    a = audit_file(path, folder)
    for sub in sorted((path.parent / path.stem / "subagents").glob("*.jsonl")):
        b = audit_file(sub, folder, sid=path.stem)
        a["classes"] += b["classes"]
        a["attempts"] += b["attempts"]
        a["flagged"] += [(c, f"{n} (sub-agent)", i) for c, n, i in b["flagged"]]
        a["subagents"] = a.get("subagents", 0) + 1
    return a


def audit_file(path: Path, folder: str, sid: str | None = None) -> dict:
    sid = sid or path.stem
    cwd = str(Path.home())
    uses, out = {}, {"sid": sid, "model": None, "start": None, "classes": Counter(),
                     "attempts": Counter(), "flagged": [], "memory": 0}
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        cwd = r.get("cwd") or cwd
        att = r.get("attachment")
        if isinstance(att, dict) and att.get("type") == "instructions" and any(
                isinstance(x, dict) and x.get("type") == "AutoMem" for x in att.get("files") or []):
            out["memory"] = 1
        if r.get("timestamp") and not out["start"]:
            out["start"] = parse_ts(r["timestamp"])
        m = r.get("message") or {}
        out["model"] = out["model"] or m.get("model")
        content = m.get("content")
        if not isinstance(content, list):
            continue
        for x in content:
            if not isinstance(x, dict):
                continue
            if x.get("type") == "tool_use" and not x.get("name", "").startswith("mcp__") \
                    and x.get("name") != "ToolSearch":
                uses[x["id"]] = (x["name"], x.get("input") or {})
            elif x.get("type") == "tool_result" and x.get("tool_use_id") in uses:
                name, inp = uses[x["tool_use_id"]]
                if x.get("is_error"):
                    out["attempts"][name] += 1
                    continue
                c = classify(name, inp, sid, folder, cwd)
                out["classes"][c] += 1
                if c in ("VIOLATION", "REVIEW", "SUBAGENT"):
                    out["flagged"].append((c, name, json.dumps(inp)[:240]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=str(DEFAULT_DIR), help="transcript folder (default: %(default)s)")
    ap.add_argument("--window", nargs="+", action="append", metavar="NAME START END [MODEL]",
                    help="attribute sessions starting in [START, END) (and, if given, whose model "
                         "contains MODEL) to NAME; repeatable. Default: one window over everything.")
    ap.add_argument("--out", help="write a markdown report here as well")
    args = ap.parse_args()

    folder = str(Path(args.dir).expanduser().resolve())
    windows = []
    for w in args.window or [["all", "1970-01-01T00:00+00:00", "2100-01-01T00:00+00:00"]]:
        if len(w) not in (3, 4):
            raise SystemExit(f"--window takes NAME START END [MODEL], got {w}")
        windows.append((w[0], parse_ts(w[1]), parse_ts(w[2]), w[3] if len(w) == 4 else None))

    per_window = defaultdict(lambda: {"sessions": 0, "classes": Counter(), "attempts": Counter(),
                                      "flagged": [], "memory": 0})
    for f in sorted(Path(folder).glob("*.jsonl")):
        a = audit_session(f, folder)
        if not a["start"]:
            continue
        for name, start, end, model in windows:
            if start <= a["start"] < end and (model is None or (a["model"] and model in a["model"])):
                w = per_window[name]
                w["sessions"] += 1
                w["memory"] += a["memory"]
                w["classes"] += a["classes"]
                w["attempts"] += a["attempts"]
                w["flagged"] += [(a["sid"][:8], a["start"].isoformat(timespec="minutes"), *fl)
                                 for fl in a["flagged"]]

    L = ["# Transcript audit (non-MCP tool access)", "", f"Folder: `{folder}`", "",
         "| Window | Sessions | MEMORY | own-output | compute | SUBAGENT | REVIEW | VIOLATION | Refused attempts |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    bad = False
    for name, *_ in windows:
        w = per_window[name]
        c = w["classes"]
        bad |= c["VIOLATION"] > 0 or w["memory"] > 0
        L.append(f"| {name} | {w['sessions']} | {w['memory']} | {c['own-output']} | {c['compute']} | {c['SUBAGENT']} | {c['REVIEW']} | "
                 f"{c['VIOLATION']} | {sum(w['attempts'].values())} "
                 f"({', '.join(f'{k} {v}' for k, v in w['attempts'].most_common())}) |")
    for name, *_ in windows:
        fl = per_window[name]["flagged"]
        if fl:
            L += ["", f"## {name}: flagged calls", "", "| Session | Start | Class | Tool | Input |",
                  "|---|---|---|---|---|"]
            L += [f"| {s} | {t} | {c} | {n} | `{i.replace('|', '¦')}` |" for s, t, c, n, i in fl]
    L += ["", "MEMORY = sessions that had the repository's auto-memory index attached to their "
          "context (must be 0).", "Sub-agent transcripts (<session>/subagents/) are audited under their parent. "
          "SUBAGENT = a sub-agent was spawned (its calls are classified on their own rows). "
          "own-output = the session's own saved tool results; compute = Bash with no path or "
          "network; REVIEW = listing the shared folder without reading another session; "
          "VIOLATION = reading another session's files, anything else on disk, or the network. "
          "Refused attempts were denied by the runner's gate and had no effect."]
    text = "\n".join(L) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
