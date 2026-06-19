"""Usage-log analysis for TogoMCP.

Reads the JSONL written by ``_ToolCallLogger`` (see :mod:`togo_mcp.server`),
aggregates monthly tool-call and SPARQL statistics, and powers the ``/stats``
dashboard. Pure standard library; reading the log has no effect on the running
MCP server.

Privacy: aggregation only ever *counts*. Raw ``args``, ``ip``, and query text
never appear in any output produced here — only derived categories and tallies.

What the collection layer records today (per JSONL line):
  ts, tool, args, status (ok|error), elapsed_ms, session_id/request_id/...,
  ip, error_class, error_message, and for SPARQL an ``extra`` dict with
  endpoint_url, query_sha256, sparql_status (ok|timeout|network_error|
  http_4xx|http_5xx), http_code, n_bytes, n_rows.

This module derives, per calendar month (UTC):
  * per-tool: call count, error count/rate, duration p50/p95/mean
  * SPARQL failure classification (syntax/timeout/empty/huge/endpoint-down/...)
  * per-database usage, oriented toward surfacing MIE-improvement candidates
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

# A result larger than this (bytes) is flagged "huge" — likely an unbounded
# query the MIE should steer away from (missing LIMIT / over-broad pattern).
HUGE_BYTES = 10_000_000

# SPARQL failure taxonomy surfaced in the dashboard. "ok" and "empty_result"
# are successful HTTP responses; the rest are errors.
SPARQL_CLASSES = (
    "ok",
    "empty_result",
    "huge_result",
    "syntax_error",
    "timeout",
    "endpoint_down",
    "server_error",
    "other_error",
)

# search_* tools whose target database is implied by the tool name (no
# ``database`` arg). Keeps per-database stats from undercounting keyword search.
_SEARCH_TOOL_DB = {
    "search_uniprot_entity": "uniprot",
    "search_reactome_entity": "reactome",
    "search_rhea_entity": "rhea",
    "search_pdb_entity": "pdb",
    "search_mesh_descriptor": "mesh",
    "search_chembl_molecule": "chembl",
    "search_chembl_target": "chembl",
}


# --------------------------------------------------------------------------- #
# SPARQL query shape (privacy-safe structural fingerprint)
# --------------------------------------------------------------------------- #
# Matches string literals (triple-quoted, double, single) so their CONTENTS can
# be stripped before any feature extraction — user literals never leak into the
# shape. IRIs live in <...> and are handled separately (only FROM graphs kept).
_LITERAL_RE = re.compile(
    r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''
)
# prefix:local — schema terms (predicates/classes), e.g. up:reviewed, bp:db,
# xsd:string, bif:contains. The local part requirement (`:[A-Za-z_]`) means bare
# "up:" in a PREFIX decl and "http://" inside an IRI do NOT match.
_QNAME_RE = re.compile(r"\b[A-Za-z][\w.-]*:[A-Za-z_]\w*")
_FROM_RE = re.compile(r"\bfrom\s+(?:named\s+)?<([^>]+)>", re.IGNORECASE)
_FLAG_WORDS = (
    "filter", "optional", "union", "values", "service",
    "limit", "offset", "order", "group", "minus", "having",
)


def sparql_shape(query: str) -> dict[str, Any]:
    """Privacy-safe structural fingerprint of a SPARQL query.

    String-literal CONTENTS are stripped first, so no user-supplied text can
    leak. What remains is schema-level: query form, FROM graphs, the set of
    qname predicates/classes used, structural flags, and length. This is the
    signal MIE-improvement analysis needs ("reactome queries using bp:db but
    not xsd:string return 0 rows") without storing the raw query.
    """
    q = query or ""
    stripped = _LITERAL_RE.sub('""', q)
    low = stripped.lower()

    form = "other"
    for f in ("select", "ask", "construct", "describe"):
        if re.search(rf"\b{f}\b", low):
            form = f
            break

    qnames = sorted(set(_QNAME_RE.findall(stripped)))
    flags = {w: bool(re.search(rf"\b{w}\b", low)) for w in _FLAG_WORDS}
    flags["bif_contains"] = "bif:contains" in low

    return {
        "form": form,
        "from": sorted(set(_FROM_RE.findall(stripped)))[:20],
        "predicates": qnames[:60],
        "n_predicates": len(qnames),
        "flags": {k: v for k, v in flags.items() if v},  # only present flags
        "len": len(q),
    }


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def log_paths(base: str) -> list[str]:
    """Return the active log file plus any rotated siblings (base.1, base.2…).

    ``RotatingFileHandler`` writes ``base`` (newest) and ``base.1`` … ``base.N``
    (older). We read all that exist; order does not matter (records carry ``ts``).
    """
    if not base:
        return []
    out = [base] if os.path.exists(base) else []
    i = 1
    while True:
        p = f"{base}.{i}"
        if not os.path.exists(p):
            break
        out.append(p)
        i += 1
    return out


def iter_records(paths: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield one parsed record per JSONL line, silently skipping bad lines."""
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(rec, dict):
                        yield rec
        except OSError:
            continue


def load_endpoint_groups(endpoints_csv: str) -> dict[str, str]:
    """Map endpoint_url -> endpoint group name (e.g. .../ebi/sparql -> 'ebi')."""
    groups: dict[str, str] = {}
    try:
        with open(endpoints_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                url = (row.get("endpoint_url") or "").strip()
                name = (row.get("endpoint_name") or "").strip()
                if url and name:
                    groups.setdefault(url, name)
    except OSError:
        pass
    return groups


# --------------------------------------------------------------------------- #
# Classification helpers
# --------------------------------------------------------------------------- #
def month_of(rec: dict[str, Any]) -> str | None:
    """UTC 'YYYY-MM' bucket for a record, or None if the timestamp is unusable."""
    ts = rec.get("ts")
    if not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def _args(rec: dict[str, Any]) -> dict[str, Any]:
    a = rec.get("args")
    return a if isinstance(a, dict) else {}


def _arg_database(rec: dict[str, Any]) -> str:
    a = _args(rec)
    for key in ("database", "db", "dbname"):
        v = a.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def database_of(rec: dict[str, Any], endpoint_groups: dict[str, str]) -> str | None:
    """Best-effort database attribution for a record.

    Priority: explicit ``database`` arg > tool-name implied DB > endpoint group
    (for cross-DB SPARQL that used endpoint_name/url). Returns None when the
    call is not database-specific (e.g. togoid_*, list_*, ncbi_* utilities).
    """
    db = _arg_database(rec)
    if db:
        return db

    tool = rec.get("tool")
    if isinstance(tool, str) and tool in _SEARCH_TOOL_DB:
        return _SEARCH_TOOL_DB[tool]

    extra = rec.get("extra")
    if isinstance(extra, dict):
        url = extra.get("endpoint_url")
        if isinstance(url, str) and url:
            group = endpoint_groups.get(url)
            return f"{group} (cross-db)" if group else "unknown-endpoint"
    return None


def sparql_class(rec: dict[str, Any]) -> str | None:
    """Classify a SPARQL record, or None if the record is not a SPARQL call."""
    extra = rec.get("extra")
    if not isinstance(extra, dict) or "sparql_status" not in extra:
        return None
    status = extra.get("sparql_status")
    if status == "ok":
        if (extra.get("n_rows") or 0) == 0:
            return "empty_result"
        if (extra.get("n_bytes") or 0) >= HUGE_BYTES:
            return "huge_result"
        return "ok"
    if status == "timeout":
        return "timeout"
    if status == "network_error":
        return "endpoint_down"
    if status == "http_5xx":
        return "server_error"
    if status == "http_4xx":
        # A 4xx from a SPARQL endpoint is almost always a malformed query.
        return "syntax_error"
    return "other_error"


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    rank = pct / 100 * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac, 2)


def aggregate(
    records: Iterable[dict[str, Any]],
    endpoint_groups: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Roll records up into a JSON-serializable monthly statistics structure."""
    endpoint_groups = endpoint_groups or {}

    # month -> accumulators
    tool_durs: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    tool_counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"count": 0, "errors": 0})
    )
    sparql: dict[str, dict[str, int]] = defaultdict(
        lambda: {c: 0 for c in SPARQL_CLASSES}
    )
    # month -> db -> tally
    dbs: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "calls": 0,
                "sparql": 0,
                "errors": 0,
                "empty": 0,
                "huge": 0,
                "rows_sum": 0,
                "rows_n": 0,
                "fail_classes": defaultdict(int),
            }
        )
    )
    months: set[str] = set()
    n_total = 0
    n_skipped_no_month = 0

    for rec in records:
        n_total += 1
        month = month_of(rec)
        if month is None:
            n_skipped_no_month += 1
            continue
        months.add(month)
        tool = rec.get("tool") or "<unknown>"
        is_error = rec.get("status") == "error"

        tc = tool_counts[month][tool]
        tc["count"] += 1
        if is_error:
            tc["errors"] += 1
        dur = rec.get("elapsed_ms")
        if isinstance(dur, (int, float)):
            tool_durs[month][tool].append(float(dur))

        cls = sparql_class(rec)
        if cls is not None:
            sparql[month][cls] += 1

        db = database_of(rec, endpoint_groups)
        if db is not None:
            d = dbs[month][db]
            d["calls"] += 1
            if is_error:
                d["errors"] += 1
            if cls is not None:
                d["sparql"] += 1
                d["fail_classes"][cls] += 1
                if cls == "empty_result":
                    d["empty"] += 1
                elif cls == "huge_result":
                    d["huge"] += 1
                extra = rec.get("extra") or {}
                rows = extra.get("n_rows")
                if isinstance(rows, (int, float)):
                    d["rows_sum"] += rows
                    d["rows_n"] += 1

    by_month: dict[str, Any] = {}
    for month in sorted(months):
        tools_out = {}
        total_calls = total_errors = 0
        for tool, c in sorted(tool_counts[month].items()):
            durs = sorted(tool_durs[month].get(tool, []))
            total_calls += c["count"]
            total_errors += c["errors"]
            tools_out[tool] = {
                "count": c["count"],
                "errors": c["errors"],
                "error_rate": round(c["errors"] / c["count"], 4) if c["count"] else 0,
                "p50_ms": _percentile(durs, 50),
                "p95_ms": _percentile(durs, 95),
                "mean_ms": round(sum(durs) / len(durs), 2) if durs else 0.0,
            }

        sp = dict(sparql[month])
        sp_total = sum(sp.values())
        sp_fail = sp_total - sp["ok"] - sp["empty_result"]

        dbs_out = {}
        for db, d in sorted(dbs[month].items()):
            dbs_out[db] = {
                "calls": d["calls"],
                "sparql": d["sparql"],
                "errors": d["errors"],
                "empty": d["empty"],
                "huge": d["huge"],
                "avg_rows": round(d["rows_sum"] / d["rows_n"], 1) if d["rows_n"] else None,
                "fail_classes": dict(d["fail_classes"]),
            }

        by_month[month] = {
            "tool_calls": total_calls,
            "errors": total_errors,
            "error_rate": round(total_errors / total_calls, 4) if total_calls else 0,
            "tools": tools_out,
            "sparql": {"total": sp_total, "failures": sp_fail, "classes": sp},
            "databases": dbs_out,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_records": n_total,
        "n_skipped_no_timestamp": n_skipped_no_month,
        "months": sorted(months),
        "by_month": by_month,
        "mie_candidates": _mie_candidates(by_month),
    }


def _mie_candidates(by_month: dict[str, Any]) -> list[dict[str, Any]]:
    """Rank (database, month) cells by how strongly the logs suggest the MIE
    needs work: failed SPARQL + empty results are the signal. Higher = more
    worth investigating. This is the MIE-improvement-candidate feed."""
    out: list[dict[str, Any]] = []
    for month, m in by_month.items():
        for db, d in m.get("databases", {}).items():
            fails = sum(
                n for c, n in d.get("fail_classes", {}).items()
                if c not in ("ok", "empty_result")
            )
            empties = d.get("empty", 0)
            sparql = d.get("sparql", 0)
            if sparql == 0:
                continue
            # Empty results count half — they are softer evidence than errors.
            score = fails + 0.5 * empties
            if score <= 0:
                continue
            out.append({
                "month": month,
                "database": db,
                "sparql_calls": sparql,
                "failures": fails,
                "empty_results": empties,
                "fail_rate": round((fails + empties) / sparql, 4) if sparql else 0,
                "score": round(score, 1),
                "fail_classes": d.get("fail_classes", {}),
            })
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Convenience: load + aggregate from the configured log path
# --------------------------------------------------------------------------- #
def compute_stats(
    log_path: str | None = None,
    endpoints_csv: str | None = None,
) -> dict[str, Any]:
    """Load the configured log (TOGOMCP_QUERY_LOG) and return the aggregate."""
    log_path = log_path if log_path is not None else os.getenv("TOGOMCP_QUERY_LOG", "").strip()
    groups = load_endpoint_groups(endpoints_csv) if endpoints_csv else {}
    return aggregate(iter_records(log_paths(log_path)), groups)


def render_html(stats: dict[str, Any]) -> str:
    """Render the aggregate as a self-contained HTML dashboard (no external JS/CSS)."""
    from html import escape

    def cell(v: Any) -> str:
        return escape("" if v is None else str(v))

    months = stats.get("months", [])
    parts: list[str] = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>TogoMCP usage stats</title><style>",
        "body{font:14px/1.5 system-ui,sans-serif;margin:2rem;color:#1a1a1a;background:#fafafa}",
        "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem;border-bottom:2px solid #ddd;padding-bottom:.2rem}",
        "h3{font-size:.95rem;margin:1rem 0 .3rem;color:#444}",
        "table{border-collapse:collapse;margin:.4rem 0 1rem;font-size:.85rem;background:#fff}",
        "th,td{border:1px solid #ddd;padding:.25rem .5rem;text-align:right}",
        "th:first-child,td:first-child{text-align:left}",
        "th{background:#f0f0f0}tr:nth-child(even) td{background:#f8f8f8}",
        ".muted{color:#888}.warn{color:#b00}.tag{font-size:.75rem;color:#666}",
        "</style></head><body>",
        "<h1>TogoMCP usage statistics</h1>",
        f"<p class='muted'>Generated {cell(stats.get('generated_at'))} · "
        f"{cell(stats.get('n_records'))} records · months: {cell(', '.join(months)) or '—'}</p>",
    ]

    cand = stats.get("mie_candidates", [])
    parts.append("<h2>MIE-improvement candidates</h2>")
    if cand:
        parts.append("<p class='muted'>Ranked by failed + empty SPARQL (per database / month). "
                     "High score = the MIE most likely needs work.</p>")
        parts.append("<table><tr><th>month</th><th>database</th><th>SPARQL</th>"
                     "<th>failures</th><th>empty</th><th>fail rate</th><th>score</th>"
                     "<th>classes</th></tr>")
        for r in cand[:50]:
            classes = ", ".join(f"{k}:{v}" for k, v in sorted(r.get("fail_classes", {}).items())
                                if k not in ("ok",))
            parts.append(
                f"<tr><td>{cell(r['month'])}</td><td>{cell(r['database'])}</td>"
                f"<td>{cell(r['sparql_calls'])}</td><td class='warn'>{cell(r['failures'])}</td>"
                f"<td>{cell(r['empty_results'])}</td><td>{cell(r['fail_rate'])}</td>"
                f"<td>{cell(r['score'])}</td><td class='tag'>{cell(classes)}</td></tr>"
            )
        parts.append("</table>")
    else:
        parts.append("<p class='muted'>No failed/empty SPARQL recorded.</p>")

    for month in reversed(months):
        m = stats["by_month"][month]
        parts.append(f"<h2>{cell(month)}</h2>")
        parts.append(
            f"<p>{cell(m['tool_calls'])} tool calls · {cell(m['errors'])} errors "
            f"(<span class='warn'>{cell(round(m['error_rate'] * 100, 1))}%</span>)</p>"
        )

        sp = m["sparql"]
        parts.append("<h3>SPARQL outcomes</h3><table><tr>"
                     + "".join(f"<th>{cell(c)}</th>" for c in SPARQL_CLASSES)
                     + "<th>total</th><th>failures</th></tr><tr>"
                     + "".join(f"<td>{cell(sp['classes'].get(c, 0))}</td>" for c in SPARQL_CLASSES)
                     + f"<td>{cell(sp['total'])}</td><td class='warn'>{cell(sp['failures'])}</td></tr></table>")

        parts.append("<h3>Per database</h3><table><tr><th>database</th><th>calls</th>"
                     "<th>SPARQL</th><th>errors</th><th>empty</th><th>huge</th>"
                     "<th>avg rows</th></tr>")
        for db, d in sorted(m["databases"].items(), key=lambda kv: kv[1]["calls"], reverse=True):
            parts.append(
                f"<tr><td>{cell(db)}</td><td>{cell(d['calls'])}</td><td>{cell(d['sparql'])}</td>"
                f"<td>{cell(d['errors'])}</td><td>{cell(d['empty'])}</td><td>{cell(d['huge'])}</td>"
                f"<td>{cell(d['avg_rows'])}</td></tr>"
            )
        parts.append("</table>")

        parts.append("<h3>Per tool</h3><table><tr><th>tool</th><th>calls</th><th>errors</th>"
                     "<th>error rate</th><th>p50 ms</th><th>p95 ms</th><th>mean ms</th></tr>")
        for tool, t in sorted(m["tools"].items(), key=lambda kv: kv[1]["count"], reverse=True):
            parts.append(
                f"<tr><td>{cell(tool)}</td><td>{cell(t['count'])}</td><td>{cell(t['errors'])}</td>"
                f"<td>{cell(t['error_rate'])}</td><td>{cell(t['p50_ms'])}</td>"
                f"<td>{cell(t['p95_ms'])}</td><td>{cell(t['mean_ms'])}</td></tr>"
            )
        parts.append("</table>")

    parts.append("</body></html>")
    return "".join(parts)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Aggregate TogoMCP usage logs.")
    ap.add_argument("log_path", nargs="?", default=os.getenv("TOGOMCP_QUERY_LOG", ""),
                    help="JSONL log path (default: $TOGOMCP_QUERY_LOG)")
    ap.add_argument("--endpoints", default="", help="endpoints.csv for DB attribution")
    args = ap.parse_args(argv)
    if not args.log_path:
        ap.error("no log path given and TOGOMCP_QUERY_LOG is unset")
    stats = aggregate(
        iter_records(log_paths(args.log_path)),
        load_endpoint_groups(args.endpoints) if args.endpoints else {},
    )
    print(json.dumps(stats, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
