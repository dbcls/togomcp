from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
import csv
from typing import Dict
import os
import httpx
import logging
from starlette.requests import Request
from starlette.responses import PlainTextResponse,HTMLResponse


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def toolcall_log(funname: str) -> None:
    """
    toolcall_log
    
    :param funname: The name of the tool being called.
    :type funname: str
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
CWD = os.getenv("TOGOMCP_DIR", ".")
MIE_DIR = CWD + "/mie"
MIE_PROMPT= CWD + "/resources/MIE_prompt.md"
TOGOMCP_USAGE_GUIDE= CWD + "/resources/togomcp_usage_guide_new.md"
SPARQL_EXAMPLES= CWD + "/sparql-examples"
RDF_CONFIG_TEMPLATE= CWD + "/rdf-config/template.yaml"
ENDPOINTS_CSV = CWD + "/resources/endpoints.csv"
INDEX_HTML = CWD + "/docs/togomcp-intro.html"
KW_SEARCH_INSTRUCTIONS = CWD + "/kw_search"



def load_sparql_endpoints(path: str) -> Dict[str, Dict[str, str]]:
    """Load SPARQL endpoints from a CSV file.

    Returns a dictionary keyed by database name with values containing:
    - url: The SPARQL endpoint URL
    - endpoint_name: Short name for the endpoint (e.g., 'ebi', 'sib')
    - keyword_search: The keyword search API to use
    """
    endpoints = {}
    with open(path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            db_name, endpoint_url, endpoint_name, keyword_search_api = row
            key = db_name.lower().replace(' ', '_').replace('-', '')
            endpoints[key] = {
                "url": endpoint_url,
                "endpoint_name": endpoint_name,
                "keyword_search": keyword_search_api
            }
    return endpoints

# The SPARQL endpoints for various RDF databases, loaded from a CSV file.
SPARQL_ENDPOINT = load_sparql_endpoints(ENDPOINTS_CSV)
DBNAME_DESCRIPTION = f"Database name: One of {','.join(SPARQL_ENDPOINT.keys())}"

# Build reverse lookups for endpoint_name -> url and list of databases per endpoint
ENDPOINT_NAME_TO_URL: Dict[str, str] = {}
ENDPOINT_NAME_TO_DATABASES: Dict[str, list] = {}
for dbname, info in SPARQL_ENDPOINT.items():
    ep_name = info["endpoint_name"]
    ENDPOINT_NAME_TO_URL[ep_name] = info["url"]
    if ep_name not in ENDPOINT_NAME_TO_DATABASES:
        ENDPOINT_NAME_TO_DATABASES[ep_name] = []
    ENDPOINT_NAME_TO_DATABASES[ep_name].append(dbname)

ENDPOINT_NAMES = list(ENDPOINT_NAME_TO_URL.keys())
SPARQL_ENDPOINT_KEYS = list(SPARQL_ENDPOINT.keys())

def resolve_endpoint_url(
    dbname: str,
    endpoint_name: str,
    endpoint_url: str
) -> str:
    """Resolve the SPARQL endpoint URL from various input options.

    Priority: endpoint_url > endpoint_name > dbname

    Args:
        dbname: Database name (e.g., 'chembl', 'uniprot')
        endpoint_name: Short endpoint name (e.g., 'ebi', 'sib')
        endpoint_url: Direct endpoint URL

    Returns:
        The resolved SPARQL endpoint URL

    Raises:
        ValueError: If no valid input is provided or input is invalid
    """
    if endpoint_url:
        return endpoint_url
    if endpoint_name:
        if endpoint_name not in ENDPOINT_NAME_TO_URL:
            raise ValueError(
                f"Unknown endpoint name: {endpoint_name}. "
                f"Valid names are: {', '.join(ENDPOINT_NAMES)}"
            )
        return ENDPOINT_NAME_TO_URL[endpoint_name]
    if dbname:
        if dbname not in SPARQL_ENDPOINT:
            raise ValueError(
                f"Unknown database: {dbname}. "
                f"Valid databases are: {', '.join(SPARQL_ENDPOINT_KEYS)}"
            )
        return SPARQL_ENDPOINT[dbname]["url"]
    raise ValueError(
        "At least one of dbname, endpoint_name, or endpoint_url must be provided"
    )


# Making this a @mcp.tool() becomes an error, so we keep it as a function.
async def execute_sparql(
    sparql_query: str,
    dbname: str = "",
    endpoint_name: str = "",
    endpoint_url: str = ""
) -> str:
    """Execute a SPARQL query on RDF Portal.

    Args:
        sparql_query: The SPARQL query to execute.
        dbname: The name of the database to query (e.g., 'chembl', 'uniprot').
        endpoint_name: Short endpoint name (e.g., 'ebi', 'sib') for cross-database queries.
        endpoint_url: Direct SPARQL endpoint URL.

    Returns:
        The results of the SPARQL query in CSV format.

    Note:
        Priority: endpoint_url > endpoint_name > dbname
        For cross-database queries on shared endpoints, use endpoint_name or endpoint_url.
    """
    url = resolve_endpoint_url(dbname, endpoint_name, endpoint_url)

    async with httpx.AsyncClient() as client:
        response = await client.post(
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
    with open(INDEX_HTML, 'r') as f:
        html_content = f.read()
    return HTMLResponse(html_content)
