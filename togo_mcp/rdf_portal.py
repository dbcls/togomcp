import csv as _csv
import io as _io
import json
from pathlib import Path
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

    Returns the v4 Usage Guide, which enforces the empirically-validated workflow:

        GATE 0: classify the question (bounded → STEP −1 | open-ended → EXPLORATION).
        STEP −1: analyze entities, databases, endpoints (no tools).
        STEP  0: find_databases(keywords=[...]) — token-efficient discovery.
        STEP  1: specialized search or ncbi_esearch — ground in real IRIs.
        STEP  2: get_MIE_file(database) — required before any run_sparql.
        STEP  3: run_sparql() — LIMIT 10 first; max 2 consecutive calls, then pivot.
        STEP  4: synthesize — each fact once, no meta-commentary.

    Why this matters (measured): questions with ≥3 consecutive run_sparql calls
    score 1.26 points lower than compliant ones; jumping to text search before
    reading the MIE schema accounts for ~95% of silent SPARQL failures. The
    guide also documents the controlled category taxonomy used by
    find_databases() and the EXPLORATION habits (Seed Definition, concierge
    check, prioritized Next Steps) for open-ended deep dives.

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

    (The authoritative list of supported `database` values is injected into the
    tool `description=` on the decorator above; see DATABASE_DESCRIPTION.)

    Args:
        database (str): The name of the database for which to retrieve the shape expression.
            Accepts aliases `dbname` and `db`.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.

    Returns:
        str: The MIE file containing the RDF schema information in YAML format.
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
def list_databases() -> str:
    """
    Supplementary: full catalog dump (browse only, no filtering).

    Returns every available RDF database with `{database, title, description}`. Use
    this only when you need the entire catalog with no filter — for example, to
    enumerate all databases or to discover what kinds of data exist before you
    have specific search terms.

    For every normal workflow, call `find_databases(keywords=[...])` first — that
    is the canonical entry point. This tool is a supplementary fallback.

    Returns:
        JSON string: a bare array of dicts with keys `database`, `title`,
        `description`.
    """
    return json.dumps([
        {"database": r["database"], "title": r["title"], "description": r["description"]}
        for r in _load_databases_cache()
    ])


def _normalize_terms(value: str | list[str] | None) -> list[str]:
    """Lowercase, strip, drop empties. Accepts str | list[str] | None."""
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip().lower()
        return [v] if v else []
    return [s.strip().lower() for s in value if isinstance(s, str) and s.strip()]


# Filler words dropped from multi-word keyword phrases so a phrase like
# "mechanism of action" matches on its content words, not the connective tissue.
_PHRASE_STOPWORDS = frozenset(
    {"of", "the", "and", "or", "a", "an", "for", "to", "in", "on", "with"}
)


def _singularize(token: str) -> str:
    """Naive plural→singular: drop a trailing 's' so a query for "targets"
    matches curated "target" and "variants" matches "variant". Leaves 'ss'
    endings and short words alone (class, is, gas)."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _keyword_matches(keyword: str, haystack: str) -> bool:
    """True if `keyword` matches `haystack`.

    A user keyword may be a multi-word phrase (e.g. "drug targets"). It matches
    when every content token is found in the haystack as a substring —
    order-independent and plural-tolerant (each token is tested both as-is and
    singularized). This is deliberately looser than a literal phrase-substring
    test, which brittly failed on word order and plurals: "drug targets" missed
    the curated "drug"+"target", and "clinical variants" missed "clinical
    significance"+"variant". Both are hinted verbatim in the Usage Guide, so the
    matcher must honor them.
    """
    tokens = [t for t in keyword.split() if t not in _PHRASE_STOPWORDS]
    if not tokens:  # phrase was entirely stopwords — fall back to raw tokens
        tokens = keyword.split()
    if not tokens:
        return False
    return all((t in haystack) or (_singularize(t) in haystack) for t in tokens)


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
                "Data-type / domain keyword(s) describing the KIND of data you "
                "need (e.g. 'drug targets', 'variants', 'expression', 'pathways', "
                "'orthologs'), as a single string or a list. Matched (case-"
                "insensitively, order- and plural-tolerant) against each database's "
                "title, description, and curated keywords. Prefer several related "
                "terms (OR-matched) over one narrow phrase. Do NOT pass specific "
                "entities (gene symbols, drug names, accessions) — use the search_* "
                "tools for those."
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
) -> str:
    """
    Database discovery — REQUIRED first step for any TogoMCP workflow.

    Always call this BEFORE `get_MIE_file()` or `run_sparql()`. Returns 1–3
    candidate databases scoped to your terms — much more efficient than browsing
    the full catalog.

    HOW TO CHOOSE `keywords` (this is what makes or breaks the search):
    - Match is against each database's curated KIND-OF-DATA vocabulary, plus its
      title and description — NOT against specific entities. So feed data-type /
      domain words: "drug targets", "variants", "expression", "pathways",
      "orthologs", "structures", "compounds", "reactions", "glycans".
    - Do NOT pass a specific entity as a keyword — a gene symbol (BRCA1), drug
      name (imatinib), accession (P04637), or a narrow class term (kinase,
      GPCR). Those are not in the index and will miss; look entities up with the
      `search_*` tools (search_uniprot_entity, search_chembl_target, …) instead.
    - Pass SEVERAL related terms as a list, not one narrow phrase. Matching is
      OR by default (`match="any"`), so more synonyms = higher recall, e.g.
      keywords=["drug target", "inhibitor", "bioactivity"] rather than just
      "kinase". Multi-word phrases and plurals are handled (each content word is
      matched independently and singularized).
    - If the result is empty, GENERALIZE: swap the term for a broader
      data-domain synonym ("kinase" → "enzyme" / "drug target"; "SNP" →
      "variant") and retry, or call `list_categories()` to browse domains.

    Workflow:
    1. find_databases(keywords=[...]) — identify 1–3 relevant databases.
    2. get_MIE_file(database) — learn each candidate's schema and SPARQL idioms.
    3. run_sparql() — query with the discovered structured properties.

    Proven keywords: "MANE" (Ensembl), "drug targets" (ChEMBL),
    "clinical variants" (ClinVar), "pathways" (Reactome), "variants" (gnomAD),
    "ortholog" (OMA), "expression" (Bgee).

    If you have no search terms and want to browse the full catalog instead, see
    `list_databases()` — that tool is supplementary, not a substitute for this one.

    Returns:
        JSON string: a bare array of dicts
        `{database, title, matched_keywords, categories, snippet}` (or
        `description` when `verbose=True`). Sorted by number of matched keywords
        descending, then alphabetically by database name.
    """
    kw_list = _normalize_terms(keywords)
    cat_list = _normalize_terms(category)

    if not kw_list and not cat_list:
        return json.dumps([])

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
        matched = [k for k in kw_list if _keyword_matches(k, haystack)]

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
    return json.dumps(results)


@mcp.tool(name="list_categories")
def list_categories() -> dict[str, list[str]]:
    """
    Coarse-grained index of database categories with member database names.

    Use this when you don't yet have specific keywords — drill down with
    `find_databases(category=...)` once you've identified relevant categories.

    RETURNS a dict mapping each category name -> a sorted list of database
    names, or an empty dict if no databases have been categorized yet.

    Returns:
        Dict mapping category name -> sorted list of database names. Returns an empty
        dict if no databases have been annotated with categories yet.
    """
    cats: dict[str, list[str]] = {}
    for r in _load_databases_cache():
        for c in r["categories"]:
            cats.setdefault(c, []).append(r["database"])
    return {k: sorted(v) for k, v in sorted(cats.items())}
