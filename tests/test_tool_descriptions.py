"""Guard tests for the descriptions FastMCP actually exposes for every tool.

Two FastMCP quirks make it easy to ship a tool whose return/error contract
never reaches the calling LLM:

1. Only the docstring text BEFORE the first section header (``Args:`` etc.)
   becomes the exposed description; the ``Returns:``/``Raises:`` sections are
   dropped. Put the return/error contract in the body ABOVE ``Args:``.
2. A tool declared with ``@mcp.tool(description=...)`` ignores its docstring
   entirely — the decorator string IS the description. And an f-string is not a
   valid docstring at all (``__doc__`` is ``None``), so any dynamic content must
   live in the decorator/Field, never a "docstring".

These tests assemble the real server (root tools + mounted sub-servers) and
assert what FastMCP exposes, so a regression in either quirk fails loudly
instead of silently degrading the tool for agents.
"""

import asyncio

import pytest

from togo_mcp.main import mcp, setup

# Substrings that signal a tool tells the caller what it returns or how it
# fails. Deliberately permissive — the point is to catch an EMPTY or
# contentless description (e.g. an f-string mistaken for a docstring, or a
# return contract buried in a dropped ``Returns:`` section), not to police
# wording.
_RETURN_CUES = (
    "return", "->", "json", "csv", "yaml", "dict", "list", "array",
    "error", "result", "string", "pair", "map", "graph", "file", "id",
)


@pytest.fixture(scope="module")
def assembled_tools():
    """All tools on the fully-assembled server, including mounted sub-servers."""
    async def _collect():
        await setup()  # mounts togoid / ncbi / togovar
        return await mcp._list_tools()

    return asyncio.run(_collect())


def test_server_exposes_all_tools(assembled_tools) -> None:
    """The assembled server exposes the full tool catalog (sanity check that the
    fixture actually mounted the sub-servers)."""
    # Dropped from 32 to 29 when the discovery trio (find_databases /
    # list_databases / list_categories) was retired — the catalog moved into the
    # Usage Guide (DATABASE CATALOG section) as a static, generated resource.
    assert len(assembled_tools) >= 29


def test_every_tool_has_a_nonempty_description(assembled_tools) -> None:
    """No tool ships with a missing/stub description. Catches the f-string-as-
    docstring trap (which yields ``__doc__ is None`` → empty description) and a
    decorator with no ``description=`` and no docstring."""
    thin = [
        t.name for t in assembled_tools if not (t.description or "").strip()
        or len((t.description or "").strip()) < 20
    ]
    assert not thin, f"Tools with missing/stub descriptions: {thin}"


def test_every_tool_description_states_what_it_returns(assembled_tools) -> None:
    """Every exposed description carries a return/error cue. A tool whose return
    contract lives only in a dropped ``Returns:`` section (or a decorator string
    that omits it) fails here — promote the contract into the body above
    ``Args:`` (docstring tools) or into the ``description=`` string (decorator
    tools)."""
    missing = [
        t.name
        for t in assembled_tools
        if not any(cue in (t.description or "").lower() for cue in _RETURN_CUES)
    ]
    assert not missing, (
        "These tools' exposed descriptions state nothing about what they "
        f"return: {missing}. FastMCP drops the docstring `Returns:` section — "
        "move the return/error contract into the body above `Args:`, or into "
        "the decorator `description=` for decorator-driven tools."
    )


class TestReadOnlyAnnotations:
    """Every TogoMCP tool is a query/search/ID conversion — nothing writes. That
    has to be stated in the protocol, not just in prose: MCP's default for an
    unannotated tool is the UNSAFE one. OpenAI's ChatGPT developer-mode docs say
    "tools without this hint are treated as write actions", so an unannotated
    read-only server draws a confirmation prompt on every call and can be refused
    outright by a plan that only permits read/search connectors."""

    def test_every_tool_declares_read_only(self) -> None:
        tools = asyncio.run(self._tools())
        missing = [
            t.name
            for t in tools
            if getattr(getattr(t, "annotations", None), "readOnlyHint", None) is not True
        ]
        assert not missing, (
            f"tools missing readOnlyHint=True: {missing}. Add "
            "`annotations=READ_ONLY_TOOL` to the @mcp.tool decorator — without it "
            "clients treat the tool as a writer."
        )

    def test_every_tool_declares_open_world(self) -> None:
        """Each tool reaches an external endpoint (RDF Portal, NCBI, TogoID, …),
        not a closed local dataset."""
        tools = asyncio.run(self._tools())
        missing = [
            t.name
            for t in tools
            if getattr(getattr(t, "annotations", None), "openWorldHint", None) is not True
        ]
        assert not missing, f"tools missing openWorldHint=True: {missing}"

    def test_destructive_and_idempotent_hints_stay_unset(self) -> None:
        """The MCP spec defines both as meaningful only when readOnlyHint is false.
        Setting them on a read-only tool is noise that implies the opposite."""
        tools = asyncio.run(self._tools())
        wrong = [
            t.name
            for t in tools
            for hint in ("destructiveHint", "idempotentHint")
            if getattr(getattr(t, "annotations", None), hint, None) is not None
        ]
        assert not wrong, f"read-only tools must leave destructive/idempotent unset: {wrong}"

    @staticmethod
    async def _tools():
        await setup()
        return await mcp.list_tools()
