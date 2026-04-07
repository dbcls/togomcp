from pathlib import Path
import sys
from typing import Annotated, Any

from pydantic import Field
import yaml

from .server import *


@mcp.tool(name="TogoMCP_Usage_Guide")
def togomcp_usage_guide() -> str:
    """
    ⚠️ CALL THIS TOOL FIRST before using ANY other TogoMCP tool (SPARQL, search, or database tools).
    This guide enforces the mandatory workflow:
        (1) Get MIE schema files to discover structured properties,
        (2) Use search tools for exploratory examples,
        (3) Inspect properties,
        (4) Write comprehensive SPARQL queries.
    **CRITICAL**: 95% of query failures happen because users skip step 1 and use text search (bif:contains)
      or API calls when structured predicates exist in the schema. Skipping this wastes 10-20 tool calls
      and produces incomplete results.
      For comprehensive queries (counts, 'find all', 'which has most'), this guide shows you how to discover
      structured properties (taxonomy IRIs, typed predicates, classification terms) that are 10-100x faster
      than text search. Always call this guide first to learn the correct workflow for your specific query type.

        Returns:
            str: The content of the TogoMCP usage guide.
    """
    toolcall_log("togomcp_usage_guide")
    with open(TOGOMCP_USAGE_GUIDE, encoding="utf-8") as file:
        prompt = file.read()
    return prompt


# --- Tools for RDF Portal --- #


@mcp.tool()
async def get_sparql_endpoints() -> dict[str, Any]:
    """Get the available SPARQL endpoints for RDF Portal.

    Returns:
        Dict with two keys:
        - databases: Dict mapping dbname -> {url, endpoint_name, keyword_search}
        - endpoints: Dict mapping endpoint_name -> {url, databases}
    """
    toolcall_log("get_sparql_endpoints")
    return {
        "databases": SPARQL_ENDPOINT,
        "endpoints": {
            name: {
                "url": ENDPOINT_NAME_TO_URL[name],
                "databases": ENDPOINT_NAME_TO_DATABASES[name],
            }
            for name in ENDPOINT_NAMES
        },
    }


@mcp.tool(
    name="run_sparql",
    description="Run a SPARQL query on an RDF database. Specify dbname for single-database queries, or endpoint_name/endpoint_url for cross-database queries on shared endpoints.",
)
async def run_sparql(
    sparql_query: Annotated[str, Field(description="The SPARQL query to execute")],
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION, default="")] = "",
    endpoint_name: Annotated[
        str,
        Field(
            description=f"Endpoint name for cross-database queries. One of: {', '.join(ENDPOINT_NAMES)}. "
            "Use this when querying multiple databases on the same endpoint.",
            default="",
        ),
    ] = "",
    endpoint_url: Annotated[
        str,
        Field(
            description="Direct SPARQL endpoint URL. Use this for explicit control over the endpoint.",
            default="",
        ),
    ] = "",
) -> str:
    """
    Run a SPARQL query on an RDF database.

    Use `get_MIE_file()` to understand the RDF graph structure of each database.

    Args:
        sparql_query (str): The SPARQL query to execute.
        dbname (str, optional): Database name for single-database queries.
        endpoint_name (str, optional): Endpoint name for cross-database queries (e.g., 'ebi' for ChEMBL+ChEBI).
        endpoint_url (str, optional): Direct SPARQL endpoint URL.

    Note:
        Provide at least one of: dbname, endpoint_name, or endpoint_url.
        Priority: endpoint_url > endpoint_name > dbname

    Returns:
        str: CSV-formatted results of the SPARQL query.
    """
    toolcall_log("run_sparql")
    return await execute_sparql(sparql_query, dbname, endpoint_name, endpoint_url)


# --- Tools for exploring RDF databases ---


@mcp.tool(
    name="get_graph_list",
    description="Get a list of named graphs in a specific RDF database.",
)
async def get_graph_list(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)],
) -> str:
    f"""
    Get a list of named graphs in a specific RDF database.

    Args:
        dbname (str): The name of the database for which to retrieve the named graphs. Supported values are {", ".join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: CSV-formatted list of named graphs.
    """
    toolcall_log("get_graph_list")
    sparql_query = """
SELECT DISTINCT ?graph WHERE {
  GRAPH ?graph {
    ?s ?p ?o .
  }
}"""
    return await execute_sparql(sparql_query, dbname)


@mcp.tool(
    name="get_MIE_file",
    description="**At the start of any task, identify ALL databases needed and call this tool for EACH of them before writing any SPARQL queries.** Do not query a database until its MIE file has been read. Get the MIE (Metadata Interoperability Exchange) file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database.",
)
async def get_MIE_file(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)],
) -> str:
    f"""
    Get the MIE file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database in YAML format, which can be used as a hint to build SPARQL queries.

    Args:
        dbname (str): The name of the database for which to retrieve the shape expression. Supported values are {", ".join(SPARQL_ENDPOINT.keys())}."

    Returns:
        str: The MIE file containing the RDF schema information in YAML format.
    """
    toolcall_log("get_MIE_file")
    mie_file = Path(MIE_DIR).joinpath(f"{dbname}.yaml")
    drop_keys = []
    #    drop_keys += ["data_statistics", "architectural_notes"]
    #    drop_keys += ["validation_notes"]
    if not mie_file.exists():
        raise FileNotFoundError(f"MIE file not found for database: '{dbname}'")
    with open(mie_file, encoding="utf-8") as file:
        content = file.read()
    return f"Content-type: application/yaml; charset=utf-8\n{content}"


# Module-level cache for list_databases results
_cached_databases: list[dict[str, Any]] | None = None


@mcp.tool(name="list_databases")
def list_databases() -> list[dict[str, Any]]:
    """
    CRITICAL FIRST STEP: Database Discovery & Selection

    **ALWAYS CALL THIS FIRST when you need to:**
    - Determine which database(s) contain relevant data for a query
    - Discover available databases before starting research
    - Verify database capabilities and coverage
    - Identify cross-database integration opportunities

    **What it returns:**
    A list of all 22 RDF databases with:
    - Database name (for use in other tool calls)
    - Title (human-readable name)
    - Description (detailed content, entities, cross-references, use cases)

    **Why this matters:**
    Database descriptions contain CRITICAL KEYWORDS that reveal content:
    - "MANE" appears in Ensembl description -> transcript quality flags
    - "drug targets" appears in ChEMBL -> pharmaceutical research
    - "clinical variants" appears in ClinVar -> disease associations
    - "pathways" appears in Reactome -> biological processes

    **Workflow:**
    1. Call list_databases() BEFORE calling get_MIE_file() or run_sparql()
    2. Read descriptions to identify 1-3 relevant databases
    3. Proceed with get_MIE_file() on identified databases
    4. Query comprehensively with discovered structured properties

    **Common mistake to avoid:**
    Do not assume a database based on name alone (e.g., "gene query -> only NCBI Gene").
    Discover databases by reading descriptions (e.g., "gene query -> both NCBI Gene AND
    Ensembl have complementary data").

    **Example pattern:**
    Query: "MANE Select transcripts for drug targets"
    -> Call list_databases()
    -> See "MANE" in Ensembl description
    -> See "drug targets" in ChEMBL description
    -> Query both databases on shared 'ebi' endpoint

    **This is reconnaissance, not optional.**
    Skipping this step = guessing which database to use = missing 50-80% of relevant data.

    Returns:
        A list of dictionaries, each containing schema info for a file.
    """
    toolcall_log("list_databases")

    global _cached_databases
    if _cached_databases is not None:
        return _cached_databases

    resources_dir = Path(MIE_DIR)
    if not resources_dir.is_dir():
        print(f"Error: Directory '{resources_dir}' not found.", file=sys.stderr)
        return []

    all_schemas_info = []
    for db_name in sorted(SPARQL_ENDPOINT.keys()):
        filename = db_name + ".yaml"
        file_path = resources_dir.joinpath(filename)
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise yaml.YAMLError("YAML file is not a dictionary.")

            schema_info = data.get("schema_info")
            if not isinstance(schema_info, dict):
                raise yaml.YAMLError(
                    "'schema_info' section not found or not a dictionary."
                )

            title = schema_info.get("title")
            description = schema_info.get("description")

            all_schemas_info.append(
                {
                    "database": db_name,
                    "title": title or "No title found.",
                    "description": description or "No description found.",
                }
            )

        except yaml.YAMLError as e:
            all_schemas_info.append(
                {
                    "database": db_name,
                    "title": "No title found.",
                    "description": f"Error processing YAML file: {e}",
                }
            )
        except OSError as e:
            all_schemas_info.append(
                {
                    "database": db_name,
                    "title": "No title found.",
                    "description": f"Error reading file: {e}",
                }
            )

    _cached_databases = all_schemas_info
    return _cached_databases
