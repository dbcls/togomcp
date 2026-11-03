#!/usr/bin/env python3
"""Do clients read the Usage Guide and the MIE before SPARQL, and do they pin graphs?

Reads a production tool-call log (JSONL, one record per call, written by
_ToolCallLogger) and prints three tables:

1. Clients: calls, sessions, and the share of SESSIONLESS calls. Since 2026-10
   Anthropic/ClaudeAI (Claude Desktop + claude.ai) and claude-code use the
   stateless 2026-07-28 protocol, so `session_id` is None for every call. Their
   calls cannot be grouped into conversations, and tables 2 and 3 exclude them —
   pooling them under one None "session" mixes different users (this script's
   first draft did, and its post-October figures were wrong).
2. Per conversation (sessioned calls only): was TogoMCP_Usage_Guide called before
   the first run_sparql, and had get_MIE_file(<database>) been called before each
   run_sparql? A conversation ("episode") is a session split at gaps > --gap
   minutes, because an Anthropic session spans many conversations.
3. Monthly unpinned-query rate per client. Stateless, so it covers sessionless calls
   too. Pinned = GRAPH / FROM / FROM NAMED followed by an IRI (the test in
   rdf_portal._GRAPH_SCOPED_RE). RDF Portal endpoints only, minus nims: external
   endpoints may legitimately have no named graphs, and supercon has no co-tenants.

Identify clients by meta.client.name, not client_id. Most of the log is bots; read
the per-client rows, not the totals.

Usage:
    python scripts/analyze_guide_mie_usage.py LOG.jsonl [--gap 30] [--since 2026-10-01]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from datetime import datetime, timedelta

PIN_RE = re.compile(r"\b(?:graph|from(?:\s+named)?)\s*<", re.I)
FOCUS = ("Anthropic/ClaudeAI", "claude-code", "openai-mcp", "openai-mcp (Codex)")
MONTHS_SHOWN = 6


def client(r: dict) -> str:
    return ((r.get("meta") or {}).get("client") or {}).get("name") or "?"


def episodes(recs: list[dict], gap: timedelta) -> list[list[dict]]:
    """Sessioned calls grouped by session, split at gaps. Sessionless calls are dropped."""
    by = collections.defaultdict(list)
    for r in recs:
        if r.get("session_id"):
            by[r["session_id"]].append(r)
    out = []
    for calls in by.values():
        calls.sort(key=lambda r: r["ts"])
        cur, last = [], None
        for r in calls:
            t = datetime.fromisoformat(r["ts"])
            if last is not None and t - last > gap:
                out.append(cur)
                cur = []
            cur.append(r)
            last = t
        out.append(cur)
    return out


def sparql_in_scope(r: dict) -> bool:
    url = (r.get("extra") or {}).get("endpoint_url") or ""
    return r["tool"] == "run_sparql" and url.startswith("https://rdfportal.org/") and "/nims/" not in url


def is_unpinned(r: dict) -> bool:
    a = r.get("args") or {}
    return not PIN_RE.search(a.get("sparql_query") or a.get("query") or "")


def pct(a: int, b: int) -> str:
    return f"{a / b:4.0%}" if b else "   -"


def table_clients(recs: list[dict]) -> None:
    c = collections.defaultdict(collections.Counter)
    for r in recs:
        k = c[client(r)]
        k["calls"] += 1
        k["sessionless"] += r.get("session_id") is None
    print("1. Clients (calls; share without a session)")
    for name, k in sorted(c.items(), key=lambda kv: -kv[1]["calls"])[:12]:
        print(f"   {name[:26]:26} {k['calls']:7d}  sessionless {pct(k['sessionless'], k['calls'])}")


def table_guide_mie(recs: list[dict], gap: timedelta) -> None:
    s = collections.defaultdict(collections.Counter)
    for ep in episodes(recs, gap):
        name = client(ep[0])
        if name not in FOCUS or not any(r["tool"] == "run_sparql" for r in ep):
            continue
        first = next(i for i, r in enumerate(ep) if r["tool"] == "run_sparql")
        g = "guide first" if any(r["tool"] == "TogoMCP_Usage_Guide" for r in ep[:first]) else "no guide first"
        k = s[(name, g)]
        k["episodes"] += 1
        read: set = set()
        for r in ep:
            a = r.get("args") or {}
            if r["tool"] == "get_MIE_file":
                read.add(a.get("database") or a.get("dbname") or a.get("db"))
            elif r["tool"] == "run_sparql":
                k["sparql"] += 1
                k["mie"] += a.get("database") in read
                if sparql_in_scope(r):
                    k["scoped"] += 1
                    k["unpinned"] += is_unpinned(r)
    print("\n2. Sessioned conversations: guide before first SPARQL, and MIE read before each SPARQL")
    for name in sorted({n for n, _ in s}):
        eps = sum(k["episodes"] for (n, _), k in s.items() if n == name)
        sparql = sum(k["sparql"] for (n, _), k in s.items() if n == name)
        if sparql <= eps * 1.1:
            # A new session per call (openai-mcp does this): nothing ever precedes the
            # SPARQL call inside its "conversation", so the columns would read 0%.
            print(f"   {name[:20]:20} skipped: about one call per session, conversations cannot be rebuilt")
            for key in [key for key in s if key[0] == name]:
                del s[key]
    for (name, g), k in sorted(s.items()):
        print(f"   {name[:20]:20} {g:15} episodes {k['episodes']:4d}  SPARQL {k['sparql']:5d}  "
              f"MIE read before {pct(k['mie'], k['sparql'])}  unpinned {pct(k['unpinned'], k['scoped'])}")


def table_unpinned(recs: list[dict]) -> None:
    m = collections.defaultdict(collections.Counter)
    for r in recs:
        if sparql_in_scope(r):
            k = m[(client(r), r["ts"][:7])]
            k["n"] += 1
            k["u"] += is_unpinned(r)
    months = sorted({mo for _, mo in m})[-MONTHS_SHOWN:]
    print("\n3. Unpinned run_sparql rate by month (RDF Portal endpoints; includes sessionless calls)")
    for name in FOCUS:
        row = [f"{mo}: {pct(m[(name, mo)]['u'], m[(name, mo)]['n'])} (n={m[(name, mo)]['n']})"
               for mo in months if m[(name, mo)]["n"]]
        if row:
            print(f"   {name[:20]:20} " + " | ".join(row))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("log", help="tool-call log, JSONL")
    ap.add_argument("--gap", type=int, default=30, help="minutes of silence that end a conversation")
    ap.add_argument("--since", help="only records on or after this date (YYYY-MM-DD)")
    args = ap.parse_args()
    with open(args.log, encoding="utf-8") as fh:
        recs = [json.loads(line) for line in fh if line.strip()]
    if args.since:
        recs = [r for r in recs if r["ts"] >= args.since]
    print(f"{len(recs)} records, {recs[0]['ts'][:10]} → {recs[-1]['ts'][:10]}\n")
    table_clients(recs)
    table_guide_mie(recs, timedelta(minutes=args.gap))
    table_unpinned(recs)


if __name__ == "__main__":
    main()
