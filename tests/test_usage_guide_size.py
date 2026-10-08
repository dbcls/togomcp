"""The Usage Guide core must arrive inline, and its reference files must be reachable.

MCP hosts stop returning a tool result inline past a size limit and save it to a file
instead. Claude Code has two: 50,000 characters for a text result, and 25,000 tokens of
MCP output. The v6 guide was 57,287 characters. Measured on the 2026-10 benchmark
transcripts: Sonnet 4.5 sessions got a saved file plus a 2 KB preview; Sonnet 5.5
sessions (whose tokenizer counts the same text as 25,324 tokens) got an error message
and a saved file with no preview, and NOT ONE of 330 received the whole guide — the
median session read 2 KB of it. Nothing failed: scores were produced, tests were green.

v7 tiers the guide: `TogoMCP_Usage_Guide` returns a core sized to arrive inline, and
the rest is fetched on demand with `get_workflow(name="usage-guide", path=...)`.
These tests keep it that way. The catalog grows by a row with every database added,
so without a guard the core walks back over the limit one release at a time.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from fastmcp import Client

REPO = Path(__file__).resolve().parent.parent
GUIDE_DIR = REPO / "togo_mcp" / "data" / "resources" / "usage_guide_v7"
REFERENCES = GUIDE_DIR / "references"

# Budget for the core, in characters of the served text. The hard client limit is
# 50,000; 40,000 leaves room for the JSON framing, for a host that counts bytes, and
# for a tokenizer denser than today's (Sonnet 5.5: ~0.44 tokens/char, so 40,000
# characters is ~17,500 tokens against the 25,000-token limit). When this fails, move
# detail into a reference file or tighten the compact catalog row — do not raise it
# without re-measuring delivery on real transcripts.
CORE_MAX_CHARS = 40_000
# A reference file is fetched alone, so it only has to clear the 50,000 limit itself.
REFERENCE_MAX_CHARS = 45_000


def _run(coro_fn):
    from togo_mcp.main import mcp

    async def go():
        async with Client(mcp) as client:
            return await coro_fn(client)

    return asyncio.run(go())


def _core() -> str:
    async def calls(client):
        return (await client.call_tool("TogoMCP_Usage_Guide", {})).content[0].text

    return _run(calls)


def test_core_fits_inline() -> None:
    core = _core()
    assert len(core) <= CORE_MAX_CHARS, (
        f"Usage Guide core is {len(core):,} characters (budget {CORE_MAX_CHARS:,}). "
        "Past 50,000 a host saves it to a file instead of showing it to the model."
    )
    # A host that counts the JSON-framed or byte length must stay under the limit too.
    assert len(json.dumps({"result": core}, ensure_ascii=False)) < 50_000
    assert len(core.encode("utf-8")) < 50_000


def test_guide_is_returned_as_plain_text() -> None:
    """No output schema: with one, the structured form {"result": "..."} is what a host
    saves when it does persist a result — a single JSON line a file reader cannot page."""

    async def calls(client):
        tools = {t.name: t for t in await client.list_tools()}
        result = await client.call_tool("TogoMCP_Usage_Guide", {})
        return tools["TogoMCP_Usage_Guide"].output_schema, result.structured_content

    schema, structured = _run(calls)
    assert schema is None
    assert structured is None


def test_every_reference_file_is_indexed_and_every_indexed_file_exists() -> None:
    """The MORE DETAIL table is the only way an agent learns a reference file exists."""
    core = _core()
    index = core[core.index("## 📎 MORE DETAIL") :]
    indexed = set(re.findall(r"^\| `([\w.-]+\.md)` \|", index, re.M))
    on_disk = {p.name for p in REFERENCES.glob("*.md")}
    assert indexed == on_disk, (
        f"MORE DETAIL lists {sorted(indexed)} but references/ holds {sorted(on_disk)}"
    )
    # Every file the core mentions as a reference must be fetchable.
    mentioned = set(re.findall(r"reference file `([\w.-]+\.md)`", core))
    assert mentioned <= on_disk, f"core points at missing files: {sorted(mentioned - on_disk)}"


def test_reference_files_are_served_and_fit_inline() -> None:
    names = sorted(p.name for p in REFERENCES.glob("*.md"))
    assert names, "no reference files"

    async def calls(client):
        out = {}
        for n in names:
            r = await client.call_tool(
                "get_workflow", {"name": "usage-guide", "path": f"references/{n}"}
            )
            out[n] = r.content[0].text
        return out

    served = _run(calls)
    for n in names:
        assert served[n] == (REFERENCES / n).read_text(encoding="utf-8"), n
        assert not served[n].startswith("Error:"), n
        assert len(served[n]) <= REFERENCE_MAX_CHARS, (
            f"references/{n} is {len(served[n]):,} characters; split it"
        )


def test_reference_files_stay_out_of_the_core() -> None:
    """The core is assembled from the TOP-LEVEL glob; a reference file dropped there by
    mistake would be served to everyone and silently eat the budget."""
    top = {p.name for p in GUIDE_DIR.glob("*.md")}
    assert not top & {p.name for p in REFERENCES.glob("*.md")}
    core = _core()
    assert "Usage Guide reference file — fetched on demand" not in core


def test_usage_guide_is_not_listed_as_a_workflow_but_is_fetchable() -> None:
    async def calls(client):
        listing = (await client.call_tool("get_workflow", {})).content[0].text
        core = (await client.call_tool("get_workflow", {"name": "usage-guide"})).content[0].text
        bad = (
            await client.call_tool(
                "get_workflow", {"name": "usage-guide", "path": "../01_gates_and_rules.md"}
            )
        ).content[0].text
        return listing, core, bad

    listing, core, bad = _run(calls)
    assert "- usage-guide:" not in listing
    assert "references/co-tenancy.md" in listing  # but its reference files are listed
    assert core == _core()
    assert bad.startswith("Error:") and "Do not retry" in bad


def test_core_keeps_what_a_stale_client_cannot_fetch() -> None:
    """A client whose cached tool list predates get_workflow gets the core only, so the
    rules a correct answer depends on must not move out to a reference file."""
    core = _core()
    for needle in (
        "Pin every graph",  # critical rule 3
        "Max 2 consecutive `run_sparql`",
        "get_MIE_file(database)",
        "DATABASE CATALOG",
        "| **primary** |",  # endpoint table
        "canaries:",  # the stale-tool-list row itself
        "third argument",  # REGEX silent failure
        "the core alone is sufficient",
    ):
        assert needle in core, f"core guide lost: {needle!r}"
