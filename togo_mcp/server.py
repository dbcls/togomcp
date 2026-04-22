import csv
import logging
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def toolcall_log(funname: str) -> None:
    """Log a tool call with the caller's IP address.

    Args:
        funname: The name of the tool being called.
    """
    try:
        request: Request = get_http_request()
        user_ip = request.headers.get("X-Forwarded-For", None)
        logger.info(f"TogoMCP_tool: {funname}, IP: {user_ip}")
    except RuntimeError:
        # No HTTP request context (e.g., called via MCP)
        logger.info(f"TogoMCP_tool: {funname}, IP: MCP-call")
    return None


# The MIE files are used to define the shape expressions for SPARQL queries.
_PACKAGE_DATA_DIR = Path(__file__).parent.joinpath("data")
CWD = Path(os.getenv("TOGOMCP_DIR", str(_PACKAGE_DATA_DIR)))
MIE_DIR = str(CWD.joinpath("mie"))
MIE_PROMPT = str(CWD.joinpath("resources", "MIE_prompt.md"))
TOGOMCP_USAGE_GUIDE = str(CWD.joinpath("resources", "togomcp_usage_guide_v3.md"))
SPARQL_EXAMPLES = str(CWD.joinpath("sparql-examples"))
RDF_CONFIG_TEMPLATE = str(CWD.joinpath("rdf-config", "template.yaml"))
ENDPOINTS_CSV = str(CWD.joinpath("resources", "endpoints.csv"))
INDEX_HTML = str(CWD.joinpath("docs", "togomcp-intro.html"))
KW_SEARCH_INSTRUCTIONS = str(CWD.joinpath("kw_search"))

# Shared httpx client for SPARQL queries
_sparql_client = httpx.AsyncClient(timeout=60.0)


def load_sparql_endpoints(path: str) -> dict[str, dict[str, str]]:
    """Load SPARQL endpoints from a CSV file.

    Returns a dictionary keyed by database name with values containing:
    - url: The SPARQL endpoint URL
    - endpoint_name: Short name for the endpoint (e.g., 'ebi', 'sib')
    - keyword_search: The keyword search API to use
    """
    endpoints = {}
    with open(path, encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            db_name, endpoint_url, endpoint_name, keyword_search_api = row
            key = db_name.lower().replace(" ", "_").replace("-", "")
            endpoints[key] = {
                "url": endpoint_url,
                "endpoint_name": endpoint_name,
                "keyword_search": keyword_search_api,
            }
    return endpoints


# The SPARQL endpoints for various RDF databases, loaded from a CSV file.
SPARQL_ENDPOINT = load_sparql_endpoints(ENDPOINTS_CSV)
DATABASE_DESCRIPTION = (
    "Name of a single RDF database. Must be exactly one of: "
    f"{', '.join(SPARQL_ENDPOINT.keys())}. "
    "Do NOT pass an endpoint group name here (e.g. 'ebi', 'sib') — those go "
    "in endpoint_name instead."
)

# Build reverse lookups for endpoint_name -> url and list of databases per endpoint
ENDPOINT_NAME_TO_URL: dict[str, str] = {}
ENDPOINT_NAME_TO_DATABASES: dict[str, list] = {}
for db_name, info in SPARQL_ENDPOINT.items():
    ep_name = info["endpoint_name"]
    ENDPOINT_NAME_TO_URL[ep_name] = info["url"]
    if ep_name not in ENDPOINT_NAME_TO_DATABASES:
        ENDPOINT_NAME_TO_DATABASES[ep_name] = []
    ENDPOINT_NAME_TO_DATABASES[ep_name].append(db_name)

ENDPOINT_NAMES = list(ENDPOINT_NAME_TO_URL.keys())
SPARQL_ENDPOINT_KEYS = list(SPARQL_ENDPOINT.keys())


def resolve_endpoint_url(database: str, endpoint_name: str, endpoint_url: str) -> str:
    """Resolve the SPARQL endpoint URL from various input options.

    Priority: endpoint_url > endpoint_name > database

    Args:
        database: Database name (e.g., 'chembl', 'uniprot')
        endpoint_name: Short endpoint name (e.g., 'ebi', 'sib')
        endpoint_url: Direct endpoint URL

    Returns:
        The resolved SPARQL endpoint URL

    Raises:
        ValueError: If no valid input is provided or input is invalid.
            The error is raised immediately — callers should not retry on the
            same inputs, since the result is deterministic.
    """
    if endpoint_url:
        return endpoint_url
    if endpoint_name:
        if endpoint_name not in ENDPOINT_NAME_TO_URL:
            raise ValueError(
                f"Unknown endpoint_name: '{endpoint_name}'. "
                f"Valid endpoint names are: {', '.join(ENDPOINT_NAMES)}. "
                f"Do not retry with the same value."
            )
        return ENDPOINT_NAME_TO_URL[endpoint_name]
    if database:
        if database not in SPARQL_ENDPOINT:
            # Common mistake: passing an endpoint_name (e.g. 'ebi') as database.
            if database in ENDPOINT_NAME_TO_URL:
                members = ", ".join(ENDPOINT_NAME_TO_DATABASES.get(database, []))
                raise ValueError(
                    f"'{database}' is an endpoint_name, not a database. "
                    f"Pass it as endpoint_name= for cross-database queries, "
                    f"or choose one of its member databases: {members}. "
                    f"Do not retry with the same value."
                )
            raise ValueError(
                f"Unknown database: '{database}'. "
                f"Valid databases are: {', '.join(SPARQL_ENDPOINT_KEYS)}. "
                f"Do not retry with the same value."
            )
        return SPARQL_ENDPOINT[database]["url"]
    raise ValueError(
        "Missing required argument. Provide one of: database (e.g. 'chembl', "
        "'uniprot'), endpoint_name (e.g. 'ebi', 'sib'), or endpoint_url. "
        f"Valid databases: {', '.join(SPARQL_ENDPOINT_KEYS)}."
    )


# Making this a @mcp.tool() becomes an error, so we keep it as a function.
async def execute_sparql(
    sparql_query: str,
    database: str = "",
    endpoint_name: str = "",
    endpoint_url: str = "",
) -> str:
    """Execute a SPARQL query on RDF Portal.

    Args:
        sparql_query: The SPARQL query to execute.
        database: The name of the database to query (e.g., 'chembl', 'uniprot').
        endpoint_name: Short endpoint name (e.g., 'ebi', 'sib') for cross-database queries.
        endpoint_url: Direct SPARQL endpoint URL.

    Returns:
        The results of the SPARQL query in CSV format.

    Note:
        Priority: endpoint_url > endpoint_name > database
        For cross-database queries on shared endpoints, use endpoint_name or endpoint_url.
    """
    url = resolve_endpoint_url(database, endpoint_name, endpoint_url)

    response = await _sparql_client.post(
        url, data={"query": sparql_query}, headers={"Accept": "text/csv"}
    )
    response.raise_for_status()
    return response.text


# The Primary MCP server
mcp = FastMCP("TogoMCP: RDF Portal MCP Server")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.custom_route("/", methods=["GET"])
async def index(request: Request) -> HTMLResponse:
    with open(INDEX_HTML) as f:
        html_content = f.read()
    return HTMLResponse(html_content)
