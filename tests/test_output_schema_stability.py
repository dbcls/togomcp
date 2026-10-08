"""A tool that has an output schema must keep it.

MCP clients validate a tool result against the output schema they received at
`tools/list` time, and many hosts cache that list for a long time (CLAUDE.md, "Clients
cache the tool list"). So if a server stops declaring a schema and stops returning
structured content, a client still holding the old definition rejects EVERY call to
that tool: "Tool ... has an output schema but did not return structured content". The
server is healthy, its own tests are green, and a freshly connected client works.

This happened in 2.23.0: `TogoMCP_Usage_Guide` was switched to `output_schema=None`.
A claude.ai connector that had cached the 2.21 tool list could no longer call the
guide at all, and re-listing tools did not clear it. The opposite direction is safe:
returning structured content to a client that expects none is ignored.

So removing an output schema is a break of the same class as renaming a tool. This
test pins the set that has one. ADDING a tool with a schema: add it here. A tool
leaving this set needs the same care as a rename (see `_StaleToolNames` in server.py),
not an edit to this list.
"""

from __future__ import annotations

import asyncio

from fastmcp import Client

MUST_KEEP_OUTPUT_SCHEMA = {
    "TogoMCP_Usage_Guide",
    "get_MIE_file",
    "get_compound_attributes_from_pubchem",
    "get_graph_list",
    "get_pubchem_compound_id",
    "get_sparql_endpoints",
    "get_workflow",
    "pubcasefinder_get_case_reports",
    "pubcasefinder_rank_by_phenotypes",
    "run_sparql",
    "search_chembl_id_lookup",
    "search_chembl_molecule",
    "search_chembl_target",
    "search_mesh_descriptor",
    "search_pdb_entity",
    "search_reactome_entity",
    "search_rhea_entity",
    "search_uniprot_entity",
    "togoid_convertId",
    "togoid_countId",
    "togoid_getAllDataset",
    "togoid_getAllRelation",
    "togoid_getDataset",
    "togoid_getDescription",
    "togoid_getRelation",
    "togoid_identifyId",
    "togovar_search_disease",
    "togovar_search_gene",
    "togovar_search_variant",
}
# The NCBI tools return list[TextContent] and have never declared a schema.


def _schemas() -> dict[str, object]:
    """Output schema of every tool on the fully assembled public server."""
    from togo_mcp.main import mcp, setup

    async def go():
        await setup()  # mounts togoid / ncbi / togovar / pubcasefinder
        async with Client(mcp) as client:
            return {t.name: t.output_schema for t in await client.list_tools()}

    return asyncio.run(go())


def test_tools_keep_their_output_schema() -> None:
    schemas = _schemas()
    lost = sorted(n for n in MUST_KEEP_OUTPUT_SCHEMA if n in schemas and schemas[n] is None)
    assert not lost, (
        f"{lost} no longer declare an output schema. Clients with a cached tool list will "
        "reject every call to them. Restore the schema (and the structured content)."
    )
    missing = sorted(MUST_KEEP_OUTPUT_SCHEMA - set(schemas))
    assert not missing, f"tools gone from the server, still pinned here: {missing}"


def test_every_schema_bearing_tool_is_pinned() -> None:
    """A tool that gains a schema becomes something clients cache; pin it."""
    schemas = _schemas()
    unpinned = sorted(
        n for n, s in schemas.items() if s is not None and n not in MUST_KEEP_OUTPUT_SCHEMA
    )
    assert not unpinned, f"add to MUST_KEEP_OUTPUT_SCHEMA: {unpinned}"


def test_string_tools_return_matching_structured_content() -> None:
    """The schema is only half of it: the result must carry structured content too."""
    from togo_mcp.main import mcp

    async def go():
        async with Client(mcp) as client:
            out = {}
            for name, args in (
                ("TogoMCP_Usage_Guide", {}),
                ("get_MIE_file", {"database": "uniprot"}),
                ("get_workflow", {}),
            ):
                r = await client.call_tool(name, args)
                out[name] = (r.content[0].text, r.structured_content)
            return out

    for name, (text, structured) in asyncio.run(go()).items():
        assert structured == {"result": text}, name
