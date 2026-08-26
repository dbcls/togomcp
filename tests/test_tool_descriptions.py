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


def test_run_sparql_mandates_the_mie_file_in_what_clients_receive(assembled_tools) -> None:
    """`run_sparql` must tell the agent to read the MIE file first — in the SERVED
    description, not the docstring.

    This is asserted on the assembled tool list rather than on `__doc__` for a
    reason: `run_sparql` carries an explicit `description=` on its decorator, and
    FastMCP uses that INSTEAD of the docstring. The instruction lived only in the
    docstring until 2026-08-26 ("Use `get_MIE_file()` to understand the RDF graph
    structure"), which meant no client ever received it — a silent, green-suite
    failure of exactly the kind CLAUDE.md's Deployment section describes. Check
    what the client gets, not what the source says.

    The wording is deliberately NOT asserted, only the two load-bearing facts:
    that the MIE file must be read first, and that skipping it yields a wrong
    answer rather than an error. An agent told to expect a failure will read a
    clean result as success, which is the precise mechanism these MIEs exist to
    prevent (measured inflation on unpinned queries: x3.27, x6.29, x45,360 — all
    returned in seconds, none of them an error).
    """
    tool = next(t for t in assembled_tools if t.name == "run_sparql")
    desc = (tool.description or "")

    assert "get_MIE_file" in desc, (
        "run_sparql's SERVED description must name get_MIE_file. If you put it in "
        "the docstring, clients never see it — the decorator's description= wins."
    )
    lowered = desc.lower()
    assert "first" in lowered, "the MIE mandate must be ordered ('FIRST'), not merely suggested"
    assert "wrong answer" in lowered, (
        "the description must say skipping the MIE yields a WRONG ANSWER, not a "
        "failure — an agent watching for an error will trust a clean wrong result"
    )


def test_every_parameter_has_a_served_description(assembled_tools) -> None:
    """Every parameter of every tool ships a description the CLIENT can read.

    Checked at the top level of each property, which is where clients look. Two
    ways a description silently fails to arrive, both of which really happened
    and were fixed on 2026-08-26:

    1. It was written in the docstring under an INDENTED sub-heading (PDBj's
       "Structured filters for db=..." group) or as a COMBINED entry ("start,
       stop:"). FastMCP's ``Args:`` parser maps neither onto a parameter, so
       seven PDB filters and four TogoVar filters shipped blank.
    2. It was written as ``Annotated[T, Field(description=...)] | None``, which
       buries it inside ``anyOf[0]`` instead of the property. Write
       ``Annotated[T | None, Field(...)]`` — the union goes INSIDE.

    A ``Field(description=...)`` always beats the docstring, so it is the robust
    place to put anything that must reach an agent.
    """
    blank = [
        f"{tool.name}.{pname}"
        for tool in assembled_tools
        for pname, prop in (
            (getattr(tool, "parameters", None) or {}).get("properties", {}) or {}
        ).items()
        if not (prop.get("description") or "").strip()
    ]
    assert not blank, (
        f"{len(blank)} parameter(s) ship with no description a client can read: {blank}. "
        "Put it in Field(description=...); if the type is Optional, write "
        "Annotated[T | None, Field(...)] so it lands on the property, not in anyOf[0]."
    )


def test_no_parameter_is_documented_twice(assembled_tools) -> None:
    """One source per parameter: a ``Field(description=...)`` OR a docstring ``Args:``
    line, never both.

    A ``Field`` always wins, so an ``Args:`` line for the same parameter is dead text —
    and dead text drifts, because nothing that reads it can tell it is wrong. When this
    was first measured (2026-08-26) the corpus was already 92% single-source, but **7 of
    the 11 duplicated parameters had diverged**: ``run_sparql.sparql_query``'s dead
    ``Args:`` line still described it as just "the SPARQL query to execute", omitting the
    entire graph-pinning warning the served ``Field`` carries, and
    ``run_sparql.endpoint_url``'s omitted the priority rule. A maintainer reading the
    docstring would have been misinformed by the half nobody ships.

    Detection is by provenance, not by guessing: if the served description text is NOT
    found in the docstring, it came from a ``Field`` — and any ``Args:`` entry for that
    same parameter is therefore dead.
    """
    import inspect
    import re

    dupes = []
    for tool in assembled_tools:
        fn = getattr(tool, "fn", None)
        if fn is None:
            continue
        doc = inspect.getdoc(fn) or ""
        flat = re.sub(r"\s+", " ", doc)
        props = (getattr(tool, "parameters", None) or {}).get("properties", {}) or {}
        for pname, prop in props.items():
            served = re.sub(r"\s+", " ", prop.get("description") or "").strip()
            if not served or served in flat:
                continue  # docstring-sourced: its Args: line is the live one
            if re.search(rf"^\s{{4,8}}{re.escape(pname)}\s*\(", doc, re.M):
                dupes.append(f"{tool.name}.{pname}")

    assert not dupes, (
        f"{len(dupes)} parameter(s) documented in BOTH a Field and a docstring Args: "
        f"line, where only the Field is served: {dupes}. Delete the Args: entry — the "
        "Field is right there in the signature for anyone reading the source."
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
