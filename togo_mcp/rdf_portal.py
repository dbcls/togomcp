from pathlib import Path
import sys
from typing import Annotated, Any, Literal

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
        - databases: Dict mapping database -> {url, endpoint_name, keyword_search}
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
    description=(
        "Run a SPARQL query on an RDF database. "
        f"Specify database (valid values: {', '.join(SPARQL_ENDPOINT_KEYS)}) "
        "for single-database queries, or endpoint_name (valid values: "
        f"{', '.join(ENDPOINT_NAMES)}) / endpoint_url for cross-database "
        "queries on shared endpoints. Invalid database/endpoint_name values "
        "fail immediately with a deterministic error — do not retry."
    ),
)
async def run_sparql(
    sparql_query: Annotated[
        str, Field(description="The SPARQL query to execute. Alias: `query`.", default="")
    ] = "",
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION, default="")
    ] = "",
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
    dbname: str = "",
    db: str = "",
    query: str = "",
) -> str:
    """
    Run a SPARQL query on an RDF database.

    Use `get_MIE_file()` to understand the RDF graph structure of each database.

    Args:
        sparql_query (str): The SPARQL query to execute. Accepts alias `query`.
        database (str, optional): Database name for single-database queries.
            Accepts aliases `dbname` and `db`.
        endpoint_name (str, optional): Endpoint name for cross-database queries (e.g., 'ebi' for ChEMBL+ChEBI).
        endpoint_url (str, optional): Direct SPARQL endpoint URL.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.
        query (str, optional): Alias for `sparql_query`.

    Note:
        Provide at least one of: database (or dbname/db), endpoint_name, or endpoint_url.
        Priority: endpoint_url > endpoint_name > database.

    Returns:
        str: CSV-formatted results of the SPARQL query.
    """
    toolcall_log("run_sparql")
    database = database or dbname or db
    sparql_query = sparql_query or query
    if not sparql_query:
        raise ValueError(
            "Missing SPARQL query. Pass it as `sparql_query` (canonical) or `query`."
        )
    return await execute_sparql(sparql_query, database, endpoint_name, endpoint_url)


# --- Tools for exploring RDF databases ---


@mcp.tool(
    name="get_graph_list",
    description="Get a list of named graphs in a specific RDF database.",
)
async def get_graph_list(
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION, default="")
    ] = "",
    dbname: str = "",
    db: str = "",
) -> str:
    f"""
    Get a list of named graphs in a specific RDF database.

    Args:
        database (str): The name of the database for which to retrieve the named graphs.
            Accepts aliases `dbname` and `db`. Supported values are {", ".join(SPARQL_ENDPOINT.keys())}.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.

    Returns:
        str: CSV-formatted list of named graphs.
    """
    toolcall_log("get_graph_list")
    database = database or dbname or db
    if not database:
        return "Error: Missing required argument `database` (aliases: `dbname`, `db`)."
    sparql_query = """
SELECT DISTINCT ?graph WHERE {
  GRAPH ?graph {
    ?s ?p ?o .
  }
}"""
    return await execute_sparql(sparql_query, database)


@mcp.tool(
    name="get_MIE_file",
    description="**At the start of any task, identify ALL databases needed and call this tool for EACH of them before writing any SPARQL queries.** Do not query a database until its MIE file has been read. Get the MIE (Metadata Interoperability Exchange) file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database.",
)
async def get_MIE_file(
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION, default="")
    ] = "",
    dbname: str = "",
    db: str = "",
) -> str:
    f"""
    Get the MIE file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database in YAML format, which can be used as a hint to build SPARQL queries.

    Args:
        database (str): The name of the database for which to retrieve the shape expression.
            Accepts aliases `dbname` and `db`. Supported values are {", ".join(SPARQL_ENDPOINT.keys())}.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.

    Returns:
        str: The MIE file containing the RDF schema information in YAML format.
    """
    toolcall_log("get_MIE_file")
    database = database or dbname or db
    if not database:
        return "Error: Missing required argument `database` (aliases: `dbname`, `db`)."
    mie_file = Path(MIE_DIR).joinpath(f"{database}.yaml")
    if not mie_file.exists():
        raise FileNotFoundError(f"MIE file not found for database: '{database}'")
    with open(mie_file, encoding="utf-8") as file:
        content = file.read()
    return f"Content-type: application/yaml; charset=utf-8\n{content}"


# Module-level cache for database records loaded from MIE schema_info sections.
# Each record: {database, title, description, keywords, categories}.
_databases_cache: list[dict[str, Any]] | None = None


def _load_databases_cache() -> list[dict[str, Any]]:
    """Load and cache schema_info from every MIE file. Returns full records including
    optional `keywords` and `categories` fields when present."""
    global _databases_cache
    if _databases_cache is not None:
        return _databases_cache

    resources_dir = Path(MIE_DIR)
    if not resources_dir.is_dir():
        print(f"Error: Directory '{resources_dir}' not found.", file=sys.stderr)
        _databases_cache = []
        return _databases_cache

    records: list[dict[str, Any]] = []
    for db_name in sorted(SPARQL_ENDPOINT.keys()):
        filename = db_name + ".yaml"
        file_path = resources_dir.joinpath(filename)
        record: dict[str, Any] = {
            "database": db_name,
            "title": "No title found.",
            "description": "No description found.",
            "keywords": [],
            "categories": [],
        }
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

            record["title"] = schema_info.get("title") or "No title found."
            record["description"] = schema_info.get("description") or "No description found."
            kws = schema_info.get("keywords") or []
            cats = schema_info.get("categories") or []
            if isinstance(kws, list):
                record["keywords"] = [str(k).lower() for k in kws if str(k).strip()]
            if isinstance(cats, list):
                record["categories"] = [str(c).lower() for c in cats if str(c).strip()]
        except yaml.YAMLError as e:
            record["description"] = f"Error processing YAML file: {e}"
        except FileNotFoundError:
            record["description"] = f"MIE file not found: {filename}"
        except OSError as e:
            record["description"] = f"Error reading {filename}: {e.strerror or 'unknown error'}"

        records.append(record)

    _databases_cache = records
    return _databases_cache


@mcp.tool(name="list_databases")
def list_databases() -> list[dict[str, Any]]:
    """
    Database Discovery & Selection — full catalog browse.

    Returns every available RDF database with `{database, title, description}`. Use this
    when you want to see the entire catalog. For token-efficient lookup when you already
    have search terms in mind, prefer `find_databases(keywords=...)`.

    Common keywords-in-descriptions to watch for: "MANE" (Ensembl), "drug targets" (ChEMBL),
    "clinical variants" (ClinVar), "pathways" (Reactome).

    Workflow:
    1. (Optional) call list_databases() or find_databases() to identify 1–3 relevant DBs.
    2. get_MIE_file(database) for each.
    3. run_sparql() with discovered structured properties.

    Returns:
        A list of dicts with keys `database`, `title`, `description`.
    """
    toolcall_log("list_databases")
    return [
        {"database": r["database"], "title": r["title"], "description": r["description"]}
        for r in _load_databases_cache()
    ]


def _normalize_terms(value: str | list[str] | None) -> list[str]:
    """Lowercase, strip, drop empties. Accepts str | list[str] | None."""
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip().lower()
        return [v] if v else []
    return [s.strip().lower() for s in value if isinstance(s, str) and s.strip()]


def _make_snippet(text: str, keyword: str, context: int = 80) -> str:
    """Return ~context chars surrounding the first occurrence of keyword (case-insensitive).
    Falls back to the leading slice when no match is found."""
    if not text:
        return ""
    if not keyword:
        return text[: context * 2].strip().replace("\n", " ") + ("..." if len(text) > context * 2 else "")
    idx = text.lower().find(keyword.lower())
    if idx < 0:
        return _make_snippet(text, "", context)
    start = max(0, idx - context // 2)
    end = min(len(text), idx + len(keyword) + context // 2)
    snippet = text[start:end].strip().replace("\n", " ")
    return f"{'...' if start > 0 else ''}{snippet}{'...' if end < len(text) else ''}"


@mcp.tool(name="find_databases")
def find_databases(
    keywords: Annotated[
        str | list[str] | None,
        Field(
            description=(
                "Keyword or list of keywords (case-insensitive substring match against "
                "title, description, and the database's curated keywords field)."
            )
        ),
    ] = None,
    category: Annotated[
        str | list[str] | None,
        Field(
            description=(
                "Category filter (substring, case-insensitive). Call list_categories() "
                "to see the available set."
            )
        ),
    ] = None,
    match: Annotated[
        Literal["any", "all"],
        Field(
            description=(
                "'any' returns DBs matching at least one keyword (OR); 'all' requires "
                "every keyword to match (AND)."
            )
        ),
    ] = "any",
    verbose: Annotated[
        bool,
        Field(
            description=(
                "If True, return the full description; if False (default), return a "
                "short snippet around the first match."
            )
        ),
    ] = False,
) -> list[dict[str, Any]]:
    """
    Token-efficient database discovery — alternative to list_databases().

    Filters the RDF database catalog by keywords and/or category, returning only matching
    entries. Use this when you already have specific search terms (gene, pathway, drug
    target, variant, etc.) and want a focused candidate list before calling get_MIE_file().

    Use list_databases() instead when you want to browse the full catalog.

    Returns:
        List of dicts: `{database, title, matched_keywords, categories, snippet}` (or
        `description` when `verbose=True`). Sorted by number of matched keywords
        descending, then alphabetically by database name.
    """
    toolcall_log("find_databases")
    kw_list = _normalize_terms(keywords)
    cat_list = _normalize_terms(category)

    if not kw_list and not cat_list:
        return []

    results: list[dict[str, Any]] = []
    for r in _load_databases_cache():
        if cat_list:
            db_cats = " ".join(r["categories"])
            if not any(c in db_cats for c in cat_list):
                continue

        haystack = " ".join([
            r["title"].lower(),
            r["description"].lower(),
            " ".join(r["keywords"]),
        ])
        matched = [k for k in kw_list if k in haystack]

        if kw_list:
            if match == "all" and len(matched) < len(kw_list):
                continue
            if match == "any" and not matched:
                continue

        anchor = matched[0] if matched else (cat_list[0] if cat_list else "")
        body_key = "description" if verbose else "snippet"
        body_val = r["description"] if verbose else _make_snippet(r["description"], anchor)

        results.append({
            "database": r["database"],
            "title": r["title"],
            "matched_keywords": matched,
            "categories": r["categories"],
            body_key: body_val,
        })

    results.sort(key=lambda x: (-len(x["matched_keywords"]), x["database"]))
    return results


@mcp.tool(name="list_categories")
def list_categories() -> dict[str, list[str]]:
    """
    Coarse-grained index of database categories with member database names.

    Use this when you don't yet have specific keywords — drill down with
    `find_databases(category=...)` once you've identified relevant categories.

    Returns:
        Dict mapping category name -> sorted list of database names. Returns an empty
        dict if no databases have been annotated with categories yet.
    """
    toolcall_log("list_categories")
    cats: dict[str, list[str]] = {}
    for r in _load_databases_cache():
        for c in r["categories"]:
            cats.setdefault(c, []).append(r["database"])
    return {k: sorted(v) for k, v in sorted(cats.items())}
