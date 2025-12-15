from fastmcp import FastMCP
import csv
from typing import Dict
import os
import httpx
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def toolcall_log(funname: str) -> None:
    """
    toolcall_log
    
    :param funname: The name of the tool being called.
    :type funname: str
    """
    logger.info(f"TogoMCP_tool: {funname}")
    return None


# The MIE files are used to define the shape expressions for SPARQL queries. 
CWD = os.getenv("TOGOMCP_DIR", ".")
MIE_DIR = CWD + "/mie"
MIE_PROMPT= CWD + "/resources/MIE_prompt.md"
RDF_PORTAL_GUIDE= CWD + "/resources/rdf_portal_guide.md"
SPARQL_EXAMPLES= CWD + "/sparql-examples"
RDF_CONFIG_TEMPLATE= CWD + "/rdf-config/template.yaml"
ENDPOINTS_CSV = CWD + "/resources/endpoints.csv"

def load_sparql_endpoints(path: str) -> Dict[str, str]:
    """Load SPARQL endpoints from a CSV file."""
    endpoints = {}
    with open(path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            db_name, endpoint_url = row
            key = db_name.lower().replace(' ', '_').replace('-', '')
            endpoints[key] = endpoint_url
    return endpoints

# The SPARQL endpoints for various RDF databases, loaded from a CSV file.
SPARQL_ENDPOINT = load_sparql_endpoints(ENDPOINTS_CSV)
DBNAME_DESCRIPTION = f"Database name: One of {", ".join(SPARQL_ENDPOINT.keys())}"

# Making this a @mcp.tool() becomes an error, so we keep it as a function.
async def execute_sparql(sparql_query: str, dbname: str) -> str:
    """ Execute a SPARQL query on RDF Portal. 
    Args:
        sparql_query (str): The SPARQL query to execute.
        dbname (str): The name of the database to query. To find the supported databases, use the `get_sparql_endpoints` tool.
    Returns:
        dict: The results of the SPARQL query in CSV.
    """

    if dbname not in SPARQL_ENDPOINT:
        raise ValueError(f"Unknown database: {dbname}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPARQL_ENDPOINT[dbname], data={"query": sparql_query}, headers={"Accept": "text/csv"}
        )
    response.raise_for_status()
    return response.text

# The Primary MCP server
mcp = FastMCP("TogoMCP: RDF Portal MCP Server")
