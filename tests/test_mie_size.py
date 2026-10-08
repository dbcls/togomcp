"""Every served MIE must arrive inline.

Claude Code stops showing an MCP tool result to the model past 50,000 characters (and
past 25,000 tokens) and saves it to a file instead. Until 2026-10 two MIE files were
over that line as served: `massbank` (52,164) and `marpolbase` (50,101). On the
benchmark transcripts, Sonnet 5.5 sessions then read a median 14,000-17,000 characters
of the saved file — about a third of the schema they were about to query — while every
check stayed green, because the checkers validate what a file SAYS, not whether it is
delivered. Same failure as the v6 Usage Guide (tests/test_usage_guide_size.py), one
tool over.

The number that matters is the size THE HOST SEES: `get_MIE_file` strips `check:`
blocks and prepends a trap banner (so a file can be 61 KB on disk and 48 KB as served),
and the tool has an output schema, so the host receives the JSON-framed
`{"result": "..."}` form, about 1,000 characters longer than the YAML. The schema must
stay (see tests/test_output_schema_stability.py), so the budget is measured on that form.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastmcp import Client

REPO = Path(__file__).resolve().parent.parent
MIE_DIR = REPO / "togo_mcp" / "data" / "mie"
DATABASES = sorted(p.stem for p in MIE_DIR.glob("*.yaml"))

# The host's limit is 50,000 characters. 47,000 on the JSON-framed form leaves room for
# a host that counts bytes and for a denser tokenizer (Sonnet 5.5 counts ~0.44
# tokens/char, so 47,000 characters is ~20,500 tokens against the 25,000-token limit).
# When a file fails this: cut restatement (MIE_v3_spec.md §4.2) and authoring history
# (YAML comments are served too), never a verified example — and do not raise the
# number without re-measuring delivery on real transcripts.
HOST_MAX_CHARS = 47_000


def _host_form(text: str) -> str:
    return json.dumps({"result": text}, ensure_ascii=False, separators=(",", ":"))


def _serve_all() -> dict[str, tuple[str, object, object]]:
    from togo_mcp.main import mcp

    async def go():
        async with Client(mcp) as client:
            tools = {t.name: t for t in await client.list_tools()}
            schema = tools["get_MIE_file"].output_schema
            out = {}
            for db in DATABASES:
                r = await client.call_tool("get_MIE_file", {"database": db})
                out[db] = (r.content[0].text, r.structured_content, schema)
            return out

    return asyncio.run(go())


@pytest.fixture(scope="module")
def served() -> dict[str, tuple[str, object, object]]:
    return _serve_all()


def test_there_are_mie_files() -> None:
    assert len(DATABASES) >= 40


@pytest.mark.parametrize("database", DATABASES)
def test_served_mie_fits_inline(database: str, served) -> None:
    text = served[database][0]
    assert not text.startswith("Error:"), text[:200]
    seen = len(_host_form(text))
    assert seen <= HOST_MAX_CHARS, (
        f"get_MIE_file({database!r}) reaches the host as {seen:,} characters (budget "
        f"{HOST_MAX_CHARS:,}; YAML {len(text):,}). Past 50,000 a host saves it to a file and "
        "the model reads a fraction of it. Cut restatement and history, not verified examples."
    )
    assert len(_host_form(text).encode("utf-8")) < 50_000, (
        f"get_MIE_file({database!r}) is over 50,000 BYTES as the host sees it; a host that "
        "counts bytes would save it to a file."
    )


def test_mie_keeps_its_output_schema_and_structured_content(served) -> None:
    text, structured, schema = served[DATABASES[0]]
    assert schema is not None and "result" in schema["properties"]
    assert structured == {"result": text}
    assert text.startswith("Content-type: application/yaml")
