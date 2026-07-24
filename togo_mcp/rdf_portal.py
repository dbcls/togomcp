import csv as _csv
import io as _io
from pathlib import Path
import re
import sys
from typing import Annotated, Any, Literal

from pydantic import Field
import yaml

from .server import *


# Virtuoso / OpenLink internal graphs that ship on every endpoint and are
# never useful for actual queries. Filtered out of get_graph_list() by default.
_SYSTEM_GRAPH_PATTERNS = (
    "openlinksw.com/schemas/virtrdf",
    "w3.org/ns/ldp",
    "activitystreams-owl",
    "urn:core:services",
    "localhost:8890/dav",
)


def _is_system_graph(graph: str) -> bool:
    """True if the graph URI is a known Virtuoso/OpenLink internal graph."""
    g = graph.lower()
    return any(pat in g for pat in _SYSTEM_GRAPH_PATTERNS)


@mcp.tool(name="TogoMCP_Usage_Guide")
def togomcp_usage_guide() -> str:
    """
    ⚠️ CALL THIS TOOL FIRST every turn, before any other TogoMCP tool.

    Returns the v6 Usage Guide, which enforces the empirically-validated workflow:

        GATE 0: classify the question (bounded → STEP −1 | open-ended → EXPLORATION).
        STEP −1: analyze entities, databases, endpoints (no tools).
        STEP  0: pick database(s) from the DATABASE CATALOG in this guide — no tool call.
        STEP  1: specialized search or ncbi_esearch — ground in real IRIs.
        STEP  2: get_MIE_file(database) — required before any run_sparql.
        STEP  3: run_sparql() — pin every graph; LIMIT 10 first; max 2 consecutive.
        STEP  4: synthesize — each fact once, no meta-commentary.

    Why this matters (measured): questions with ≥3 consecutive run_sparql calls
    score ~1.1 points lower than compliant ones; jumping to text search before
    reading the MIE schema accounts for ~95% of silent SPARQL failures. The
    guide's DATABASE CATALOG lists all databases with what each is for (scan it
    to pick 1–3), plus the EXPLORATION habits (Seed Definition, concierge
    check, prioritized Next Steps) for open-ended deep dives.

    Most RDF Portal endpoints host MANY databases (primary: 16, ebi: 5, ncbi: 5,
    sib: 4) and every endpoint hosts many GRAPHS. An unpinned query silently
    reads all of them, so a co-hosted graph can supply a predicate you believe is
    native and return a plausible, correctly-shaped, WRONG number — with no error.
    The guide's CO-TENANCY section is the one to read before writing SPARQL.

    Re-run GATE 0 every turn — prior workflow does not carry forward.

    Returns:
        str: The content of the TogoMCP usage guide.
    """
    # The guide is split into part files by change-cadence; assemble them in
    # sorted order, joined by the section separator, into one document.
    parts = sorted(Path(TOGOMCP_USAGE_GUIDE).glob("*.md"))
    return "\n\n---\n\n".join(p.read_text(encoding="utf-8") for p in parts)


# --- Tools for RDF Portal --- #


@mcp.tool()
async def get_sparql_endpoints() -> dict[str, Any]:
    """Get the available SPARQL endpoints for RDF Portal.

    RETURNS a dict with two keys: `databases` (maps each database ->
    {url, endpoint_name, keyword_search}) and `endpoints` (maps each
    endpoint_name -> {url, databases}).

    Returns:
        Dict with two keys:
        - databases: Dict mapping database -> {url, endpoint_name, keyword_search}
        - endpoints: Dict mapping endpoint_name -> {url, databases}
    """
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
        f"ALWAYS pass database (required; valid values: {', '.join(SPARQL_ENDPOINT_KEYS)}) "
        "for single-database queries. For cross-database queries on a shared endpoint, "
        "still pass a member database AND add endpoint_name (valid values: "
        f"{', '.join(ENDPOINT_NAMES)}) or endpoint_url, which take priority over database. "
        "Invalid database/endpoint_name values fail immediately with a deterministic "
        "error — do not retry. "
        "RETURNS the query results as a CSV-formatted string (first row is the "
        "header of SELECT variable names)."
    ),
)
async def run_sparql(
    *,
    sparql_query: Annotated[
        str, Field(description="The SPARQL query to execute. Alias: `query`.", default="")
    ] = "",
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION)
    ],
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
    query: str = "",
) -> str:
    """
    Run a SPARQL query on an RDF database.

    Use `get_MIE_file()` to understand the RDF graph structure of each database.

    RETURNS the query results as a CSV-formatted string (first row is the
    header of SELECT variable names).

    Args:
        sparql_query (str): The SPARQL query to execute. Accepts alias `query`.
        database (str): Database name for single-database queries (required).
        endpoint_name (str, optional): Endpoint name for cross-database queries (e.g., 'ebi' for ChEMBL+ChEBI).
        endpoint_url (str, optional): Direct SPARQL endpoint URL.
        query (str, optional): Alias for `sparql_query`.

    Note:
        `database` is required. For cross-database queries on a shared endpoint,
        pass a member database AND add endpoint_name (or endpoint_url).
        Priority: endpoint_url > endpoint_name > database.

    Returns:
        str: CSV-formatted results of the SPARQL query.
    """
    sparql_query = sparql_query or query
    if not sparql_query:
        raise ValueError(
            "Missing SPARQL query. Pass it as `sparql_query` (canonical) or `query`."
        )
    return await execute_sparql(sparql_query, database, endpoint_name, endpoint_url)


# --- Tools for exploring RDF databases ---


@mcp.tool(
    name="get_graph_list",
    description=(
        "Get a list of named graphs on a SPARQL endpoint. ALWAYS pass database "
        "(required). Virtuoso/OpenLink internal graphs are filtered out. Graph URIs "
        "containing the database substring (case-insensitive) are ranked first — useful "
        "when the endpoint hosts multiple databases (e.g. SIB hosts UniProt + Rhea + "
        "Bgee + OMA). For a database not yet in the registry, pass `endpoint_url` (or "
        "`endpoint_name` if its parent endpoint is registered) to bypass database "
        "validation; the required `database` value is then used only as a ranking hint. "
        "RETURNS a CSV-formatted list of named graphs (database-name matches first); "
        "on missing endpoint selection it returns a string beginning with 'Error:' "
        "— check for that prefix before use."
    ),
)
async def get_graph_list(
    *,
    database: Annotated[
        str,
        Field(
            description=(
                "RDF database name (e.g. 'uniprot', 'chembl'). Required. When the name is "
                "in the registry it resolves the endpoint URL; in any case the value is "
                "used as a case-insensitive substring to rank matching graph URIs first. "
                "For an unregistered database, also pass `endpoint_url` or `endpoint_name` "
                "(which take priority); `database` is then just the ranking hint."
            ),
        ),
    ],
    endpoint_name: Annotated[
        str,
        Field(
            description=(
                "Short endpoint name (e.g. 'primary', 'sib', 'ebi'). Use when the "
                "database is not yet registered but its parent endpoint is."
            ),
            default="",
        ),
    ] = "",
    endpoint_url: Annotated[
        str,
        Field(
            description=(
                "Direct SPARQL endpoint URL. Use when neither the database nor its "
                "parent endpoint name is in the registry."
            ),
            default="",
        ),
    ] = "",
    include_system: Annotated[
        bool,
        Field(
            description=(
                "If True, include Virtuoso/OpenLink internal graphs (virtrdf, ldp, "
                "activitystreams, etc.). Default False — these are never useful for queries."
            ),
            default=False,
        ),
    ] = False,
) -> str:
    """
    Get a list of named graphs on a SPARQL endpoint.

    The endpoint URL is resolved with the same priority used by `run_sparql`:
    `endpoint_url` > `endpoint_name` > `database`. `database` is required. If only
    `database` is given it must be in the registry; otherwise pass `endpoint_url` (or
    `endpoint_name`) to bypass that check, in which case `database` is used only as a
    case-insensitive substring to rank matching graph URIs first. Virtuoso/OpenLink
    internal graphs are filtered out unless `include_system=True`.

    Args:
        database (str): Database name (required). Doubles as a substring ranking hint.
        endpoint_name (str, optional): Short endpoint name (e.g. 'primary', 'sib').
        endpoint_url (str, optional): Direct SPARQL endpoint URL.
        include_system (bool, optional): If True, include Virtuoso/OpenLink internal
            graphs. Default False.

    Returns:
        str: CSV-formatted list of named graphs, with database-name matches first.
    """
    if not database and not endpoint_name and not endpoint_url:
        return (
            "Error: provide one of `database`, `endpoint_name`, or `endpoint_url`. "
            "For an unregistered database, pass `endpoint_url` (or `endpoint_name` if "
            "its parent endpoint is registered); `database` can be supplied alongside "
            "as a ranking hint."
        )
    sparql_query = """
SELECT DISTINCT ?graph WHERE {
  GRAPH ?graph {
    ?s ?p ?o .
  }
}"""
    raw_csv = await execute_sparql(
        sparql_query,
        database=database,
        endpoint_name=endpoint_name,
        endpoint_url=endpoint_url,
    )

    reader = _csv.reader(_io.StringIO(raw_csv))
    rows = list(reader)
    if not rows:
        return raw_csv
    header, body = rows[0], rows[1:]

    if not include_system:
        body = [row for row in body if row and not _is_system_graph(row[0])]

    db_lower = database.lower()

    def _rank_key(row: list[str]) -> tuple[int, str]:
        graph = row[0] if row else ""
        return (0 if db_lower in graph.lower() else 1, graph)

    body.sort(key=_rank_key)

    out = _io.StringIO()
    writer = _csv.writer(out)
    writer.writerow(header)
    writer.writerows(body)
    return out.getvalue()


@mcp.tool(
    name="get_MIE_file",
    description="**At the start of any task, identify ALL databases needed and call this tool for EACH of them before writing any SPARQL queries.** Do not query a database until its MIE file has been read. Get the MIE (Metadata Interoperability Exchange) file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database. RETURNS the MIE file as a YAML-formatted string; an unknown database returns a string beginning with 'Error:' that lists the valid database names.",
)
async def get_MIE_file(
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION, default="")
    ] = "",
    dbname: str = "",
    db: str = "",
) -> str:
    """
    Get the MIE file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database in YAML format, which can be used as a hint to build SPARQL queries.

    RETURNS the MIE as YAML, preceded by a `#`-commented banner headlining that
    database's CRITICAL WARNINGS and CO-HOSTED GRAPHS. Read the banner first: it
    lists the silent-failure traps — the ones that return a wrong POSITIVE or
    partial result with no error. Then, for EVERY predicate you use, check it
    against `co_hosted_graphs`/`critical_warnings` before writing the query.
    Reading this file once is not enough; the traps that have caused wrong
    answers were all documented here and simply not re-consulted at the moment
    the predicate was typed.

    (The authoritative list of supported `database` values is injected into the
    tool `description=` on the decorator above; see DATABASE_DESCRIPTION.)

    Args:
        database (str): The name of the database for which to retrieve the shape expression.
            Accepts aliases `dbname` and `db`.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.
    """
    database = database or dbname or db
    if not database:
        return "Error: Missing required argument `database` (aliases: `dbname`, `db`)."
    mie_file = Path(MIE_DIR).joinpath(f"{database}.yaml")
    if not mie_file.exists():
        # Return a structured error string rather than raising, so the
        # downstream LLM can read the diagnostic and recover (e.g. retry
        # with a real database name) instead of seeing an opaque tool
        # exception that may break the MCP session.
        valid = ", ".join(sorted(SPARQL_ENDPOINT.keys()))
        hint = ""
        if database in ("togoid", "ncbi"):
            hint = (
                f" Note: '{database}' is a tool-prefix for a sub-server "
                "(e.g. togoid_convertId, ncbi_esearch), NOT a SPARQL "
                "database — it has no MIE file. Use the prefixed tools "
                "directly."
            )
        return (
            f"Error: No MIE file for '{database}'. Valid database names: "
            f"{valid}.{hint} Do not retry with the same value."
        )
    with open(mie_file, encoding="utf-8") as file:
        content = file.read()
    return (
        f"Content-type: application/yaml; charset=utf-8\n"
        f"{_mie_trap_banner(content, database)}{content}"
    )


def _first_sentence(text: str, limit: int = 160) -> str:
    """Condense one warning/entry to a single scannable headline."""
    flat = " ".join(text.split())
    for stop in (". ", " — ", ": "):
        head, sep, _ = flat.partition(stop)
        if sep and len(head) <= limit:
            return head
    return flat[:limit] + ("…" if len(flat) > limit else "")


def _mie_trap_banner(content: str, database: str) -> str:
    """Headline the silent-failure traps ABOVE the YAML body.

    The traps that have caused wrong answers were already documented, in the
    right file, and simply not read at the moment a predicate was typed. The
    body still holds the authoritative text — this is a scannable index that
    is impossible to skim past, not a replacement for it.
    """
    try:
        doc = yaml.safe_load(content)
        if not isinstance(doc, dict):
            return ""
        info = doc.get("schema_info") or {}
        # Co-hosted graphs: v2 = schema_info.co_hosted_graphs (list of strings);
        # v3 = graphs.co_hosted (dict {name: note}). Read new-or-old location.
        co_hosted = info.get("co_hosted_graphs")
        if not co_hosted:
            gco = (doc.get("graphs") or {}).get("co_hosted")
            if isinstance(gco, dict):
                co_hosted = [f"{k}: {v}" for k, v in gco.items()]
            elif isinstance(gco, list):
                co_hosted = gco
        co_hosted = co_hosted or []
        # Warnings: v2 = critical_warnings (block string / list);
        # v3 = global_gotchas (list of {id, say}). Read new-or-old location.
        warnings = doc.get("critical_warnings")
        if not warnings:
            gg = doc.get("global_gotchas")
            if isinstance(gg, list):
                warnings = [
                    (g.get("say") if isinstance(g, dict) else str(g)) for g in gg
                ]
        warnings = warnings or ""
    except Exception:
        # Never let a banner failure block the file the caller asked for.
        return ""

    if isinstance(warnings, str):
        # Split on TOP-LEVEL bullets only. yaml strips the block scalar's common
        # indent, so a warning starts at column 0 and its continuation/sub-bullets
        # are indented — splitting on any "- " would promote sub-bullets to
        # warnings of their own.
        items = [w.strip() for w in re.split(r"\n- ", "\n" + warnings) if w.strip()]
    elif isinstance(warnings, list):
        items = [str(w).strip() for w in warnings if str(w).strip()]
    else:
        items = []

    if not items and not co_hosted:
        return ""

    lines = [
        f"# READ THIS BEFORE WRITING ANY SPARQL AGAINST `{database}`.",
        "# These are silent-failure traps: they return a wrong POSITIVE result or a",
        "# partial one, with no error. Full text is in the YAML body below.",
    ]
    if items:
        lines.append(f"# {len(items)} CRITICAL WARNING(S):")
        lines += [f"#   {i}. {_first_sentence(w)}" for i, w in enumerate(items, 1)]
    if co_hosted:
        lines.append(
            f"# {len(co_hosted)} CO-HOSTED GRAPH(S) — this endpoint's other graphs can "
            "re-declare"
        )
        lines.append(
            "#   your predicates and inflate/skew results unless you pin the graph:"
        )
        lines += [f"#   - {_first_sentence(str(g))}" for g in co_hosted]
    lines.append(
        "# For EVERY predicate you are about to use, check it against the above: is it "
        "supplied"
    )
    lines.append(
        "#   by a co-hosted graph rather than this database, and does a warning already "
        "name it?"
    )
    return "\n".join(lines) + "\n"
