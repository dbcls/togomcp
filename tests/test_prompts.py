"""MCP prompts: what a client lists and what a chosen prompt sends to the model.

`record_for_paper` exists because on Claude Desktop nothing of ours reaches the model
before its first call except tool NAMES (see the comment on it in rdf_portal.py), so
the user has to start query-provenance. Its text names tools and a workflow; a rename
would leave the user's choice pointing at nothing, which is pinned here.
"""

import asyncio
import re

import pytest


def _run(calls, *, local: bool = False):
    from fastmcp import Client

    from togo_mcp.main import mcp, setup

    async def go():
        await setup(local=local)
        async with Client(mcp) as client:
            return await calls(client)

    return asyncio.run(go())


def _render(arguments: dict) -> str:
    async def calls(client):
        res = await client.get_prompt("record_for_paper", arguments)
        return res.messages[0].content.text

    return _run(calls)


@pytest.mark.parametrize("local", [False, True])
def test_listed_with_a_title_on_both_transports(local: bool) -> None:
    async def calls(client):
        return {p.name: p for p in await client.list_prompts()}

    prompts = _run(calls, local=local)
    assert prompts["record_for_paper"].title == "Record this investigation for a paper"


def test_names_only_real_tools_and_workflows() -> None:
    from togo_mcp.rdf_portal import WORKFLOWS

    async def calls(client):
        return {t.name for t in await client.list_tools()}

    tools = _run(calls)
    text = _render({})
    for tool in ("get_workflow", "TogoMCP_Usage_Guide", "get_MIE_file"):
        assert tool in text and tool in tools, tool
    named = set(re.findall(r'name="([a-z0-9-]+)"', text))
    assert named == {"query-provenance"} and named <= set(WORKFLOWS)


def test_question_is_optional_and_appended() -> None:
    assert "The question:" not in _render({})
    text = _render({"question": "  How many human kinases?  "})
    assert text.endswith("The question:\nHow many human kinases?")
