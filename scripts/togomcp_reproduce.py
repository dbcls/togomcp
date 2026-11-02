#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "pyyaml>=6.0", "fastmcp>=4,<5"]
# ///
"""Re-run the tool calls recorded in a TogoMCP query ledger and check the results.

A query ledger (`ledger.yaml`) is written by the `query-provenance` workflow during a
TogoMCP session: each call that supports a claim is recorded with its tool name, its
arguments exactly as sent, and what was observed. This script is for the reader or
author of a paper to run LATER, in their own environment. The session itself checks
by re-calling the tools; it never needs this script.

Two routes, chosen per call:

- `tool: run_sparql` is POSTed straight to the recorded `endpoint_url`, the same
  request the server sends (form field `query`, `Accept: text/csv`). It does not go
  through TogoMCP at all, so it still works if the server changes or goes away —
  that is the route long-term reproducibility rests on.
- Every other tool (search_*, togoid_*, ncbi_*, togovar_*, ...) is replayed over MCP
  against `togomcp.server_url`, because the REST URL those wrappers build internally
  is not in the ledger. The server's `serverInfo.version` is reported.

`role: evidence` and `role: lookup` calls are run; `role: diagnostic` calls are not.
A lookup mismatch is a warning only.

Exit codes: 0 every evidence call matched; 1 an evidence call mismatched or its
recorded call is invalid (`ledger_error`); 2 nothing mismatched but some evidence
call could not be run (`endpoint_error` — retry later); 3 the ledger itself could not
be read (unknown `ledger_version`, malformed YAML).

The ledger format is specified in the workflow's `references/ledger-format.md`. The
parsing and comparison below are pure functions, unit-tested in
`tests/test_reproduce.py`; change the format and this script together.

Usage:
    uv run togomcp_reproduce.py ledger.yaml
    uv run togomcp_reproduce.py ledger.yaml --json
    uv run togomcp_reproduce.py ledger.yaml --server-url http://localhost:8000/mcp
    uv run togomcp_reproduce.py ledger.yaml --write-ledger ledger.hashed.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

import yaml

__version__ = "1.0.0"
# The TogoMCP release whose tag carries THIS version of the script. Bump it with
# __version__ whenever the script changes, then run
# scripts/generate_reproduce_reference.py: the workflow's references/reproduce.md
# pins this tag's URL next to a full copy of the file, and the two must agree.
RELEASED_IN = "v2.29.0"

SUPPORTED_LEDGER_VERSIONS = frozenset({1})
DEFAULT_SERVER_URL = "https://togomcp.rdfportal.org/mcp"
RUN_ROLES = frozenset({"evidence", "lookup"})
KNOWN_ROLES = RUN_ROLES | {"diagnostic"}
SPARQL_TIMEOUT_SECONDS = 300.0
USER_AGENT = f"togomcp-reproduce/{__version__}"

EXIT_MATCH, EXIT_MISMATCH, EXIT_UNVERIFIED, EXIT_BAD_LEDGER = 0, 1, 2, 3


class LedgerError(ValueError):
    """The ledger cannot be used at all. Nothing is run."""


class CallFailed(Exception):
    """A single call could not be run. `category` is ledger_error or endpoint_error."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #


def load_ledger(text: str) -> dict[str, Any]:
    """Parse and validate a ledger. Raises LedgerError on anything unusable."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise LedgerError(f"not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("the ledger must be a YAML mapping")
    version = data.get("ledger_version")
    if version not in SUPPORTED_LEDGER_VERSIONS:
        raise LedgerError(
            f"ledger_version {version!r} is not supported by this script "
            f"(version {__version__}; supports {sorted(SUPPORTED_LEDGER_VERSIONS)}). "
            "Use the script version that matches the ledger."
        )
    calls = data.get("calls")
    if not isinstance(calls, list) or not calls:
        raise LedgerError("`calls` must be a non-empty list")
    seen: set[str] = set()
    for i, call in enumerate(calls):
        where = f"calls[{i}]"
        if not isinstance(call, dict):
            raise LedgerError(f"{where} must be a mapping")
        cid = call.get("id")
        if not cid:
            raise LedgerError(f"{where} has no `id`")
        if cid in seen:
            raise LedgerError(f"duplicate call id {cid!r}")
        seen.add(cid)
        if call.get("role") not in KNOWN_ROLES:
            raise LedgerError(f"{cid}: `role` must be one of {sorted(KNOWN_ROLES)}")
        if not call.get("tool"):
            raise LedgerError(f"{cid}: no `tool`")
        if not isinstance(call.get("args", {}), dict):
            raise LedgerError(f"{cid}: `args` must be a mapping")
    return data


def sparql_query_of(args: dict[str, Any]) -> str:
    """The query text of a run_sparql call: `sparql_query`, else its alias `query`."""
    return args.get("sparql_query") or args.get("query") or ""


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #


def strip_note(text: str) -> str:
    """Drop the `#`-prefixed diagnosis block run_sparql prepends to an empty result.

    The server adds it only at the TOOL layer, so a direct endpoint POST never has
    one — but a result pasted from a session might. Only LEADING `#` lines are
    removed: the block is prepended, and a data cell may legitimately start with `#`.
    """
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith("#"):
        i += 1
    return "".join(lines[i:])


def normalize(text: str) -> str:
    """Line endings unified and trailing whitespace dropped, so that a CRLF endpoint
    and an LF one hash the same."""
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip()


def result_sha256(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def csv_data_rows(csv_text: str) -> list[list[str]]:
    """Data rows of a SPARQL CSV result, header excluded. A real parse: a literal
    containing a newline makes a newline count over-report."""
    rows = [r for r in csv.reader(io.StringIO(strip_note(csv_text))) if r]
    return rows[1:]


def summarize_sparql(csv_text: str) -> dict[str, Any]:
    body = strip_note(csv_text)
    rows = csv_data_rows(body)
    value = rows[0][0] if len(rows) == 1 and len(rows[0]) == 1 else None
    return {"n_rows": len(rows), "value": value, "text": body}


def summarize_tool_text(text: str) -> dict[str, Any]:
    """What can be counted in a non-SPARQL tool result.

    List tools return a JSON bare array; ChEMBL and Reactome return an envelope with
    `results`. Anything else (NCBI text, a single record) has no row count.
    """
    n_rows = None
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, list):
        n_rows = len(parsed)
    elif isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
        n_rows = len(parsed["results"])
    return {"n_rows": n_rows, "value": None, "text": text}


# --------------------------------------------------------------------------- #
# Comparison
# --------------------------------------------------------------------------- #


def _same_value(expected: Any, actual: Any) -> bool:
    if actual is None:
        return False
    if str(expected).strip() == str(actual).strip():
        return True
    try:
        return float(expected) == float(actual)
    except (TypeError, ValueError):
        return False


def compare(observed: dict[str, Any] | None, actual: dict[str, Any]) -> dict[str, Any]:
    """Check each recorded observation against a fresh result.

    Returns {"status": match|mismatch|unchecked, "checks": [...]}. A field that was
    not recorded is not checked; a recorded field the fresh result cannot supply
    (e.g. `n_rows` for a free-text tool) is a mismatch, not a silent pass.
    """
    observed = observed or {}
    checks: list[dict[str, Any]] = []

    if observed.get("n_rows") is not None:
        ok = actual["n_rows"] is not None and int(observed["n_rows"]) == actual["n_rows"]
        checks.append({"field": "n_rows", "expected": observed["n_rows"],
                       "actual": actual["n_rows"], "ok": ok})
    if observed.get("value") is not None:
        ok = _same_value(observed["value"], actual["value"])
        checks.append({"field": "value", "expected": observed["value"],
                       "actual": actual["value"], "ok": ok})
    keys = observed.get("key_values") or []
    if keys:
        missing = [str(k) for k in keys if str(k) not in actual["text"]]
        checks.append({"field": "key_values", "expected": [str(k) for k in keys],
                       "actual": {"missing": missing}, "ok": not missing})
    if observed.get("result_sha256"):
        got = result_sha256(actual["text"])
        checks.append({"field": "result_sha256", "expected": observed["result_sha256"],
                       "actual": got, "ok": got == observed["result_sha256"]})

    if not checks:
        status = "unchecked"
    else:
        status = "match" if all(c["ok"] for c in checks) else "mismatch"
    return {"status": status, "checks": checks}


@dataclass
class CallOutcome:
    id: str
    role: str
    tool: str
    route: str  # sparql | mcp | skipped
    status: str  # match | mismatch | unchecked | error | skipped
    category: str | None = None  # ledger_error | endpoint_error, for status=error
    message: str | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)
    result_sha256: str | None = None


def exit_code(outcomes: list[CallOutcome]) -> int:
    """Only evidence decides the exit code; a lookup mismatch is a warning."""
    evidence = [o for o in outcomes if o.role == "evidence"]
    if any(o.status == "mismatch" or o.category == "ledger_error" for o in evidence):
        return EXIT_MISMATCH
    if any(o.status == "error" for o in evidence):
        return EXIT_UNVERIFIED
    return EXIT_MATCH


# --------------------------------------------------------------------------- #
# Running calls (network)
# --------------------------------------------------------------------------- #


def run_sparql_direct(call: dict[str, Any], client: Any) -> str:
    url = call.get("endpoint_url")
    if not url:
        raise CallFailed("ledger_error", "run_sparql call has no `endpoint_url`")
    query = sparql_query_of(call.get("args") or {})
    if not query:
        raise CallFailed("ledger_error", "run_sparql call has no `sparql_query`/`query` in args")
    import httpx

    try:
        resp = client.post(url, data={"query": query}, headers={"Accept": "text/csv"})
    except httpx.HTTPError as exc:
        raise CallFailed("endpoint_error", f"{type(exc).__name__}: {exc}") from exc
    if 400 <= resp.status_code < 500:
        # A query the endpoint rejects was recorded wrong; resending will not help.
        raise CallFailed("ledger_error", f"HTTP {resp.status_code}: {resp.text[:300]}")
    if resp.status_code >= 500:
        raise CallFailed("endpoint_error", f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.text


async def replay_mcp(calls: list[dict[str, Any]], server_url: str) -> tuple[str | None, dict]:
    """Replay non-SPARQL calls over one MCP session.

    Returns (server version, {call id: text or CallFailed}).
    """
    from fastmcp import Client

    results: dict[str, Any] = {}
    try:
        async with Client(server_url) as client:
            info = client.server_info
            version = getattr(info, "version", None) if info else None
            for call in calls:
                try:
                    res = await client.call_tool(
                        call["tool"], call.get("args") or {}, raise_on_error=False
                    )
                except Exception as exc:  # transport failure mid-session
                    results[call["id"]] = CallFailed("endpoint_error", f"{type(exc).__name__}: {exc}")
                    continue
                text = "\n".join(
                    getattr(c, "text", "") for c in (res.content or []) if getattr(c, "text", None)
                )
                if res.is_error:
                    # A tool error on recorded arguments (unknown tool, bad parameter)
                    # means the recorded call no longer stands as written.
                    results[call["id"]] = CallFailed("ledger_error", text[:300] or "tool error")
                else:
                    results[call["id"]] = text
    except Exception as exc:
        failure = CallFailed("endpoint_error", f"cannot reach {server_url}: {type(exc).__name__}: {exc}")
        return None, {c["id"]: failure for c in calls if c["id"] not in results} | results
    return version, results


def run_ledger(
    ledger: dict[str, Any], server_url: str | None = None
) -> tuple[list[CallOutcome], dict[str, Any]]:
    import httpx

    togomcp = ledger.get("togomcp") or {}
    recorded_url = togomcp.get("server_url")
    notes: list[str] = []
    if server_url:
        mcp_url = server_url
    elif not recorded_url or recorded_url == "local":
        mcp_url = DEFAULT_SERVER_URL
        notes.append(
            f"The ledger was recorded on a local (stdio) server; non-SPARQL calls were "
            f"replayed against {DEFAULT_SERVER_URL} instead."
        )
    else:
        mcp_url = recorded_url

    outcomes: list[CallOutcome] = []
    texts: dict[str, Any] = {}
    sparql_calls = [c for c in ledger["calls"] if c["role"] in RUN_ROLES and c["tool"] == "run_sparql"]
    mcp_calls = [c for c in ledger["calls"] if c["role"] in RUN_ROLES and c["tool"] != "run_sparql"]

    with httpx.Client(timeout=SPARQL_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT},
                      follow_redirects=True) as http:
        for call in sparql_calls:
            try:
                texts[call["id"]] = run_sparql_direct(call, http)
            except CallFailed as exc:
                texts[call["id"]] = exc

    server_version = None
    if mcp_calls:
        server_version, replayed = asyncio.run(replay_mcp(mcp_calls, mcp_url))
        texts.update(replayed)

    for call in ledger["calls"]:
        base = dict(id=call["id"], role=call["role"], tool=call["tool"])
        if call["role"] not in RUN_ROLES:
            outcomes.append(CallOutcome(**base, route="skipped", status="skipped"))
            continue
        route = "sparql" if call["tool"] == "run_sparql" else "mcp"
        got = texts[call["id"]]
        if isinstance(got, CallFailed):
            outcomes.append(CallOutcome(**base, route=route, status="error",
                                        category=got.category, message=str(got)))
            continue
        actual = summarize_sparql(got) if route == "sparql" else summarize_tool_text(got)
        verdict = compare(call.get("observed"), actual)
        message = None
        if verdict["status"] == "mismatch":
            message = "data_changed or ledger_error: compare the recorded call with the source"
        outcomes.append(CallOutcome(**base, route=route, status=verdict["status"],
                                    checks=verdict["checks"], message=message,
                                    result_sha256=result_sha256(actual["text"])))

    meta = {
        "script_version": __version__,
        "mcp_server_url": mcp_url if mcp_calls else None,
        "server_version": server_version,
        "notes": notes,
    }
    return outcomes, meta


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def format_table(outcomes: list[CallOutcome], meta: dict[str, Any]) -> str:
    lines = [f"togomcp_reproduce {meta['script_version']}"]
    if meta.get("mcp_server_url"):
        lines.append(f"MCP server: {meta['mcp_server_url']} "
                     f"(serverInfo.version: {meta.get('server_version') or 'unknown'})")
    lines += [f"note: {n}" for n in meta.get("notes", [])]
    lines.append("")
    lines.append(f"{'id':<10} {'role':<10} {'route':<7} {'status':<10} detail")
    for o in outcomes:
        if o.status == "error":
            detail = f"{o.category}: {o.message}"
        elif o.checks:
            detail = "; ".join(
                f"{c['field']} {'ok' if c['ok'] else 'expected ' + json.dumps(c['expected']) + ' got ' + json.dumps(c['actual'])}"
                for c in o.checks
            )
        else:
            detail = o.message or ""
        if o.role == "lookup" and o.status in ("mismatch", "error"):
            detail = "(warning only) " + detail
        lines.append(f"{o.id:<10} {o.role:<10} {o.route:<7} {o.status:<10} {detail}")
    return "\n".join(lines)


class _LedgerDumper(yaml.SafeDumper):
    """Writes multi-line strings (queries) as `|` blocks. The default dumper turns them
    into escaped one-line strings: the same value, but unreadable as a supplement."""


def _str_presenter(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_LedgerDumper.add_representer(str, _str_presenter)


def ledger_with_hashes(ledger_text: str, outcomes: list[CallOutcome]) -> str:
    """The ledger with `observed.result_sha256` filled in where it was empty."""
    data = yaml.safe_load(ledger_text)
    by_id = {o.id: o for o in outcomes}
    for call in data["calls"]:
        o = by_id.get(call["id"])
        if o and o.result_sha256 and o.status in ("match", "unchecked"):
            obs = call.setdefault("observed", {}) or {}
            call["observed"] = obs
            if not obs.get("result_sha256"):
                obs["result_sha256"] = o.result_sha256
    return yaml.dump(data, Dumper=_LedgerDumper, sort_keys=False, allow_unicode=True, width=1000)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("ledger", help="path to ledger.yaml")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    parser.add_argument("--server-url", help="MCP server for non-SPARQL calls "
                        "(default: the ledger's togomcp.server_url)")
    parser.add_argument("--write-ledger", metavar="PATH",
                        help="write a copy of the ledger with result_sha256 filled in for "
                        "calls that matched (or had nothing to check)")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    try:
        with open(args.ledger, encoding="utf-8") as fh:
            text = fh.read()
        ledger = load_ledger(text)
    except (OSError, LedgerError) as exc:
        print(f"error: {args.ledger}: {exc}", file=sys.stderr)
        return EXIT_BAD_LEDGER

    outcomes, meta = run_ledger(ledger, args.server_url)
    code = exit_code(outcomes)
    if args.json:
        print(json.dumps({**meta, "exit_code": code, "calls": [asdict(o) for o in outcomes]},
                         indent=2, ensure_ascii=False))
    else:
        print(format_table(outcomes, meta))
    if args.write_ledger:
        with open(args.write_ledger, "w", encoding="utf-8") as fh:
            fh.write(ledger_with_hashes(text, outcomes))
    return code


if __name__ == "__main__":
    sys.exit(main())
