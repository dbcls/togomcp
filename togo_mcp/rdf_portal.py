import csv as _csv
import io as _io
import re as _re
from pathlib import Path
from typing import Annotated, Any

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


# Guide parts that document tools which are NOT on every transport. Each entry is
# (probe tool name, part file); the part is appended only when that tool is really
# mounted on this server.
#
# Gated on the LIVE tool registry rather than on a flag or an env var, so the
# guide cannot disagree with what the server actually exposes. That matters here
# specifically: the KEGG tools are stdio-only for LICENSING reasons (the public
# host cannot verify a caller's academic affiliation), and this whole boundary is
# structural precisely because a config knob drifting out of step is the failure
# mode that cost two releases (see CLAUDE.md, "Deployment").
#
# The part files live in a SUBDIRECTORY of the guide dir, so the `*.md` glob below
# cannot pick them up by accident.
_CONDITIONAL_GUIDE_PARTS = (
    ("kegg_find", Path(TOGOMCP_USAGE_GUIDE) / "local_only" / "kegg.md"),
)


async def _conditional_guide_parts() -> list[str]:
    """Read the guide parts whose tools are actually mounted on this server.

    Shipping "call `kegg_find`, then bridge with `kegg_conv`" to a client that has
    neither tool is noise at best and an instruction to call something imaginary
    at worst. The short, transport-neutral KEGG note stays in the catalog for
    everyone; only the operating detail is gated.
    """
    parts: list[str] = []
    for probe, path in _CONDITIONAL_GUIDE_PARTS:
        try:
            tool = await mcp.get_tool(probe)
        except Exception:
            # Belt and braces: FastMCP currently RETURNS None for an unknown tool
            # rather than raising, but a version that raises must also mean "not
            # mounted" and not leak the part. Checking only for an exception is
            # exactly the bug this guard shipped with — it made the condition
            # always true, so every HTTP client got the stdio-only section.
            continue
        if tool is None:
            continue  # not mounted on this transport — omit its guide part
        try:
            parts.append(path.read_text(encoding="utf-8"))
        except OSError as exc:
            logger.warning("usage guide: cannot read conditional part %s (%s)", path, exc)
    return parts


@mcp.tool(name="TogoMCP_Usage_Guide", annotations=READ_ONLY_TOOL)
async def togomcp_usage_guide() -> str:
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
    # sorted order, joined by the section separator, into one document. Parts for
    # tools that are not on every transport are appended last, and only when the
    # tool they document is actually mounted here.
    parts = sorted(Path(TOGOMCP_USAGE_GUIDE).glob("*.md"))
    sections = [p.read_text(encoding="utf-8") for p in parts]
    sections.extend(await _conditional_guide_parts())
    return "\n\n---\n\n".join(sections)


# --- Tools for RDF Portal --- #


@mcp.tool(annotations=READ_ONLY_TOOL)
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
    annotations=READ_ONLY_TOOL,
    name="run_sparql",
    # This `description=` is what clients actually receive — FastMCP serves it INSTEAD of
    # the docstring below, not in addition to it. It has to be a `description=` rather than
    # a docstring because it interpolates the live registry, and an f-string cannot be a
    # docstring. Everything agent-facing therefore belongs HERE (and in the per-parameter
    # Field descriptions); the docstring deliberately holds no second copy to drift from.
    description=(
        "Run a SPARQL query on an RDF database. "
        "CALL get_MIE_file(database) FIRST — for every database, before its first run_sparql "
        "each session. This is not background reading: it carries the mandatory graph pins, "
        "literal types and join paths for that endpoint, each live-verified. "
        "SKIPPING IT DOES NOT MAKE YOUR QUERY FAIL — that is the danger. It makes it return a "
        "WRONG ANSWER THAT LOOKS RIGHT: well-formed rows, plausible magnitude, no error, no "
        "warning. Unpinned queries on these endpoints have been measured returning x3.27, x6.29 "
        "and x45,360 the correct row count, all in under 4 seconds. Speed and a clean result "
        "are NOT evidence of correctness here; the graph pin from the MIE file is. "
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
    # The pin reminder belongs HERE, not only in the tool description: this is the
    # field the agent is filling in at the moment it types a triple pattern, and that
    # moment is where the trap has repeatedly been missed (CLAUDE.md: the traps that
    # caused wrong answers were all documented and simply not re-consulted then).
    sparql_query: Annotated[
        str,
        Field(
            description=(
                "The SPARQL query to execute. Alias: `query`. "
                "PIN EVERY GRAPH: copy the FROM/GRAPH clause from this database's "
                "get_MIE_file examples. An unpinned pattern silently reads every "
                "co-hosted graph on the endpoint — it does not error, it returns "
                "inflated or foreign rows that look correct (measured: x3.27, x6.29, "
                "x45,360). DISTINCT does not fix it; only the graph pin does."
            ),
            default="",
        ),
    ] = "",
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION)
    ],
    endpoint_name: Annotated[
        str,
        Field(
            description=f"Endpoint name for cross-database queries. One of: {', '.join(ENDPOINT_NAMES)}. "
            "Use this when querying multiple databases on the same endpoint — pass it "
            "ALONGSIDE a member `database`, never instead of it. Overrides `database` for "
            "endpoint selection (priority: endpoint_url > endpoint_name > database).",
            default="",
        ),
    ] = "",
    endpoint_url: Annotated[
        str,
        Field(
            description="Direct SPARQL endpoint URL, for an endpoint not in the registry or for "
            "explicit control. Highest priority — overrides both `endpoint_name` and `database` "
            "(which is still required, and is then used only as a label).",
            default="",
        ),
    ] = "",
    query: Annotated[
        str, Field(description="Alias for `sparql_query`. Pass one or the other.", default="")
    ] = "",
) -> str:
    """
    Run a SPARQL query on an RDF database.

    MAINTAINER NOTE — where the agent-facing text actually lives.

    This tool needs a `description=` on the decorator above, because its text
    interpolates the live database/endpoint registry and an f-string cannot be a
    docstring (it makes `__doc__` None). FastMCP serves that string INSTEAD of the
    body of this docstring, so nothing written below reaches an agent — do not
    restate the contract here, a second copy only rots.

    Two exact points, because "the docstring is not served" is too coarse and was
    wrong here until 2026-08-26:
      - The `Args:` section IS still served: FastMCP uses it for the description of
        any parameter that has no `Field(description=...)`. Every parameter of this
        tool now carries a Field, so today the whole docstring is inert — but delete
        a Field and the corresponding `Args:` line goes live again.
      - `Note:` and `Returns:` are dropped entirely. A return contract that must
        reach the agent goes in the decorator string (this one does).


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


# No `description=` here on purpose: this text interpolates nothing, so the docstring
# can carry it and there is exactly ONE copy. `description=` is for tools whose text
# must inject a runtime value (see run_sparql, which lists the live database registry)
# — an f-string cannot be a docstring, it makes __doc__ None.
@mcp.tool(
    annotations=READ_ONLY_TOOL,
    name="get_graph_list",
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
    Get a list of named graphs on a SPARQL endpoint. ALWAYS pass database (required).

    RETURNS a CSV-formatted list of named graphs (database-name matches first). On
    missing endpoint selection it returns a string beginning with 'Error:' — check for
    that prefix before use.

    Graph URIs containing the `database` substring (case-insensitive) are ranked first,
    always — useful when the endpoint hosts multiple databases (e.g. SIB hosts UniProt +
    Rhea + Bgee + OMA). Virtuoso/OpenLink internal graphs are filtered out unless
    `include_system=True`.

    The endpoint URL is resolved with the same priority used by `run_sparql`:
    `endpoint_url` > `endpoint_name` > `database`. If only `database` is given it must be
    in the registry; otherwise pass `endpoint_url` (or `endpoint_name` if its parent
    endpoint is registered) to bypass that check, and the required `database` value then
    serves only as the ranking hint.
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
    annotations=READ_ONLY_TOOL,
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
    Get the MIE file for a specific RDF database in YAML format — verified, executable worked SPARQL examples plus the database's graphs, gotchas, schema deltas and ID/join map — the primary resource for building a correct query.

    RETURNS the MIE as YAML, preceded by a `#`-commented banner headlining that
    database's CRITICAL WARNINGS and CO-HOSTED GRAPHS. Read the banner first: it
    lists the silent-failure traps — the ones that return a wrong POSITIVE or
    partial result with no error. Then, for EVERY predicate you use, check it
    against `global_gotchas` and `graphs.co_hosted` — plus the `traps_avoided`
    on whichever example you are adapting — before writing the query.
    Reading this file once is not enough; the traps that have caused wrong
    answers were all documented here and simply not re-consulted at the moment
    the predicate was typed.

    Start from the `examples` closest to your question and adapt it: each one is
    live-verified and dated, so its shape, graph pinning and literal typing are
    known-good. Prefer that over assembling a query from `schema_delta`, which
    only carries predicates no example already demonstrates.

    (The authoritative list of supported `database` values is injected into the
    tool `description=` on the decorator above; see DATABASE_DESCRIPTION.)

    Args:
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
        content = _strip_check_blocks(file.read())
    return (
        f"Content-type: application/yaml; charset=utf-8\n"
        f"{_mie_trap_banner(content, database)}{content}"
    )


# `check:` opening a mapping on its own line — the only shape MIE_v3_spec.md §3.6
# sanctions. Requiring the line to be *exactly* `check:` keeps this from matching a
# stray "check:" inside a SPARQL block scalar, which would eat the rest of a query.
_CHECK_KEY = _re.compile(r"^(\s*)check:\s*$")


def _strip_check_blocks(content: str) -> str:
    """Remove every `check:` block before the MIE reaches the caller (spec §3.6).

    A `check:` is a CI fixture, not reader content: `scripts/check_mie_gotchas.py`
    executes it to re-decide the claim its sibling `say:` makes. Serving it would be
    actively harmful, not merely wasteful — a `kind: zero_rows` or `kind: error`
    check holds a query written to FAIL, and an agent that has been told every SPARQL
    string in this file is a verified route to copy has no way to tell it apart.

    Indentation-scoped and text-level on purpose. A YAML round-trip would drop the
    comments, and in these files the comments carry load-bearing guidance.
    """
    out, lines, i = [], content.splitlines(keepends=True), 0
    while i < len(lines):
        m = _CHECK_KEY.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        indent = len(m.group(1))
        i += 1  # drop the `check:` line itself
        while i < len(lines):
            line = lines[i]
            if not line.strip():          # blank lines belong to the block until it ends
                i += 1
                continue
            if len(line) - len(line.lstrip()) <= indent:
                break                     # dedented to a sibling — block is over
            i += 1
    return "".join(out)


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
        # graphs.co_hosted is {name: note} per MIE_v3_spec.md §2. The list branch is
        # NOT v2 back-compat (v2's schema_info.co_hosted_graphs is gone) — it tolerates
        # a hand-authored file that wrote the sequence shape, because dropping those
        # entries would silently omit exactly the warning this banner exists to raise.
        gco = (doc.get("graphs") or {}).get("co_hosted")
        if isinstance(gco, dict):
            co_hosted = [f"{k}: {v}" for k, v in gco.items()]
        elif isinstance(gco, list):
            co_hosted = list(gco)
        else:
            co_hosted = []
        # global_gotchas is an optional list of {id, say}.
        gg = doc.get("global_gotchas")
        items = (
            [
                str(g.get("say") if isinstance(g, dict) else g).strip()
                for g in gg
            ]
            if isinstance(gg, list)
            else []
        )
        items = [w for w in items if w]
    except Exception:
        # Never let a banner failure block the file the caller asked for.
        return ""

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
