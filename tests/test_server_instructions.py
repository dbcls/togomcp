"""The server `instructions` reach a client, and every name they cite is real.

The instructions are the one text of ours a host keeps in the system prompt for the
whole conversation (see the comment on SERVER_INSTRUCTIONS in server.py), so they
name a tool and a workflow directly. A rename elsewhere would leave them pointing at
nothing, with no error anywhere — asserted here against what a client receives.
"""

import asyncio
import re

import pytest


def _initialize(local: bool):
    from fastmcp import Client

    from togo_mcp.main import mcp, setup

    async def go():
        await setup(local=local)
        async with Client(mcp) as client:
            tools = {t.name for t in await client.list_tools()}
            # Era-neutral accessor: initialize_result is None on a server/discover
            # connection, which is what the in-memory client negotiates.
            return client.instructions, tools

    return asyncio.run(go())


@pytest.mark.parametrize("local", [False, True])
def test_instructions_are_sent_on_both_transports(local: bool) -> None:
    from togo_mcp.server import SERVER_INSTRUCTIONS

    instructions, _ = _initialize(local)
    assert instructions == SERVER_INSTRUCTIONS


def test_named_tools_and_workflows_exist() -> None:
    from togo_mcp.rdf_portal import WORKFLOWS

    instructions, tools = _initialize(local=False)
    for tool in ("TogoMCP_Usage_Guide", "get_workflow"):
        assert tool in instructions and tool in tools, tool
    named = set(re.findall(r'name="([a-z0-9-]+)"', instructions))
    assert named and named <= set(WORKFLOWS), named - set(WORKFLOWS)


def test_instructions_stay_short() -> None:
    # Paid for in every conversation by every user. Raise this only deliberately.
    from togo_mcp.server import SERVER_INSTRUCTIONS

    assert len(SERVER_INSTRUCTIONS) <= 300, len(SERVER_INSTRUCTIONS)
