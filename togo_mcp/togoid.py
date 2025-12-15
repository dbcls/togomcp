from .server import *
import httpx

_client = httpx.AsyncClient(base_url="https://api.togoid.dbcls.jp")

@mcp.tool()
async def convertId(
    ids: str,
    route: str,
    limit: int = 10000,
    offset: int = 0,
) -> list:
    """Convert IDs from one database to another.
    
    Args:
        ids: Comma-separated list of source IDs
        route: Comma-separated list of datasets (source to target)
        limit: Maximum number of results (max 10000)
        offset: Pagination offset
    
    Returns:
        Dictionary with ids, route, and result arrays
    """
    params = {
        "ids": ids,
        "route": route,
        "report": "target",
        "format": "json",
        "limit": limit,
        "offset": offset,
        "noheader": "0"
    }
    
    response = await _client.get("/convert", params=params)
    response.raise_for_status()
    return response.json() .get("results")


@mcp.tool()
async def countId(
    source: str,
    target: str,
    ids: str
) -> dict:
    """Count how many IDs can be converted between databases.
    
    Args:
        source: Source database key
        target: Target database key
        ids: Comma-separated list of IDs
    
    Returns:
        Dictionary with source and target counts
    """
    response = await _client.get(
        f"/count/{source}-{target}",
        params={"ids": ids}
    )
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def getAllDataset() -> dict:
    """Get configuration for all available datasets.
    
    Returns:
        Dictionary mapping dataset names to their configurations
        including labels, regex patterns, prefixes, examples, etc.
    """
    response = await _client.get("/config/dataset")
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def getDataset(dataset: str) -> dict:
    """Get configuration for a specific dataset.
    
    Args:
        dataset: Dataset key (e.g., 'uniprot', 'ncbigene')
    
    Returns:
        Dictionary with dataset configuration including:
        - label: Human-readable name
        - regex: ID validation pattern
        - prefix: URI prefixes for linking
        - examples: Sample IDs
        - annotations: Available annotation types
    """
    response = await _client.get(f"/config/dataset/{dataset}")
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def getAllRelation() -> dict:
    """Get all possible conversion relationships between databases.
    
    Returns:
        Dictionary mapping database pairs to their relationships
    """
    response = await _client.get("/config/relation")
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def getRelation(source: str, target: str) -> list:
    """Get relationship details between two specific databases.
    
    Args:
        source: Source database key
        target: Target database key
    
    Returns:
        List of relationship objects with forward, reverse, and description
    """
    response = await _client.get(f"/config/relation/{source}-{target}")
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def getDescription() -> dict:
    """Get descriptions for all databases.
    
    Returns:
        Dictionary with English and Japanese descriptions,
        names, and organization info for each database
    """
    response = await _client.get("/config/descriptions")
    response.raise_for_status()
    return response.json()
