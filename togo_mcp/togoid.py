from .server import *
import httpx

_client = httpx.AsyncClient(base_url="https://api.togoid.dbcls.jp")
togoid_mcp = FastMCP("TogoID API server")


# ============================================================================
# DISCOVERY TOOLS — Use these EARLY in multi-database workflows
# ============================================================================

@togoid_mcp.tool()
async def getAllRelation() -> dict:
    """Discover all available ID conversion routes between databases.

    ⚡ PLANNING TOOL — Call this EARLY when a question involves 2+ databases
    that are on DIFFERENT SPARQL endpoints and you need to map IDs between them.

    Returns a map of all source→target database pairs that TogoID can convert.
    Use this to plan your cross-database strategy BEFORE attempting SPARQL joins
    or manual ID lookups.

    Common conversion routes include:
        - ncbigene ↔ uniprot (Gene IDs to/from protein accessions)
        - uniprot ↔ pdb (Protein accessions to/from 3D structure IDs)
        - ncbigene ↔ ensembl_gene (NCBI Gene to/from Ensembl gene IDs)
        - chembl_target ↔ uniprot (Drug targets to/from protein accessions)
        - ncbigene ↔ hgnc (Gene IDs to/from HGNC symbols)
        - pubchem_compound ↔ chembl_compound (Compound IDs across databases)

    When to use:
        - Question references 2+ databases on different SPARQL endpoints
        - You need to bridge identifiers (e.g., "find UniProt proteins for
          these NCBI Gene IDs")
        - Before writing complex multi-step SPARQL to join databases manually

    When NOT to use:
        - Both databases share a SPARQL endpoint (use a single SPARQL query)
        - You only need data from one database
        - NCBI esearch can already cross-reference what you need

    Returns:
        Dictionary mapping database pairs to their relationship metadata.
        Each entry shows source, target, and the nature of the link.
    """
    toolcall_log("getAllRelation")
    response = await _client.get("/config/relation")
    response.raise_for_status()
    return response.json()


@togoid_mcp.tool()
async def getRelation(source: str, target: str) -> list:
    """Check if a specific ID conversion route exists and get its details.

    Use this to verify that a particular source→target conversion is available
    before calling convertId. Also reveals the nature of the relationship
    (e.g., "encoded by", "has structure", "is target of").

    Args:
        source: Source database key (e.g., 'uniprot', 'ncbigene', 'chembl_target')
        target: Target database key (e.g., 'pdb', 'ensembl_gene', 'hgnc')

    Returns:
        List of relationship objects with:
        - forward: relationship label from source to target
        - reverse: relationship label from target to source
        - description: explanation of the link

    Example:
        >>> getRelation('ncbigene', 'uniprot')
        # Shows: ncbigene → uniprot via "encoded by" relationship

        >>> getRelation('uniprot', 'pdb')
        # Shows: uniprot → pdb via "has structure" relationship
    """
    toolcall_log("getRelation")
    response = await _client.get(f"/config/relation/{source}-{target}")
    response.raise_for_status()
    return response.json()


@togoid_mcp.tool()
async def getAllDataset() -> dict:
    """List all databases registered in TogoID with their ID formats.

    Returns configuration for every dataset TogoID knows about, including:
    - label: Human-readable database name
    - regex: Pattern for validating IDs (helps you check if you have the
      right ID format before converting)
    - prefix: URI prefix for linked data
    - examples: Sample IDs you can use to test conversions

    Useful for:
        - Discovering which databases are available for ID conversion
        - Checking the expected ID format (e.g., UniProt accession vs entry name)
        - Finding example IDs to test with countId before bulk conversion

    Returns:
        Dictionary mapping dataset keys (e.g., 'uniprot', 'ncbigene', 'pdb')
        to their configuration objects.
    """
    toolcall_log("getAllDataset")
    response = await _client.get("/config/dataset")
    response.raise_for_status()
    return response.json()


@togoid_mcp.tool()
async def getDataset(dataset: str) -> dict:
    """Get configuration for a specific database in TogoID.

    Retrieves detailed metadata about a single dataset, including its ID format,
    URI prefix, example IDs, and available annotations.

    Args:
        dataset: Dataset key (e.g., 'uniprot', 'ncbigene', 'pdb', 'chembl_target',
                 'ensembl_gene', 'hgnc', 'pubchem_compound')

    Returns:
        Dictionary with:
        - label: Human-readable name
        - regex: ID validation pattern (use to verify your IDs are correctly formatted)
        - prefix: URI prefixes for linking
        - examples: Sample IDs (use with countId to test before bulk conversion)
        - annotations: Available annotation types for this dataset
    """
    toolcall_log("getDataset")
    response = await _client.get(f"/config/dataset/{dataset}")
    response.raise_for_status()
    return response.json()


@togoid_mcp.tool()
async def getDescription() -> dict:
    """Get human-readable descriptions for all databases in TogoID.

    Returns names, descriptions (in English and Japanese), and organization info
    for each registered database. Useful for understanding what each database
    contains when planning cross-database queries.

    Returns:
        Dictionary keyed by dataset name with description metadata.
    """
    toolcall_log("getDescription")
    response = await _client.get("/config/descriptions")
    response.raise_for_status()
    return response.json()


# ============================================================================
# CONVERSION TOOLS — Use these AFTER planning with discovery tools above
# ============================================================================

@togoid_mcp.tool()
async def convertId(
    ids: str,
    route: str,
    limit: int = 10000,
    offset: int = 0,
) -> list:
    """Convert identifiers from one database to another.

    Maps IDs between biological databases — e.g., NCBI Gene IDs to UniProt
    accessions, or UniProt accessions to PDB structure IDs.

    IMPORTANT WORKFLOW:
        1. First call getAllRelation() or getRelation() to verify the conversion
           route exists
        2. Optionally call countId() to check how many IDs will convert
        3. Then call convertId() with your IDs

    Args:
        ids: Comma-separated list of source IDs.
            Examples: "672,675,7157" (NCBI Gene IDs), "P38398,P04637" (UniProt)
        route: Comma-separated pair of dataset keys: 'source,target'.
            Examples:
                - 'ncbigene,uniprot' (Gene → Protein)
                - 'uniprot,pdb' (Protein → 3D Structure)
                - 'ncbigene,ensembl_gene' (NCBI Gene → Ensembl Gene)
                - 'chembl_target,uniprot' (Drug Target → Protein)
                - 'uniprot,chembl_target' (Protein → Drug Target)
                - 'ncbigene,hgnc' (Gene → HGNC symbol)
            Multi-hop routes are also supported:
                - 'ncbigene,uniprot,pdb' (Gene → Protein → Structure)
        limit: Maximum number of results (default 10000)
        offset: Pagination offset for large result sets

    Returns:
        List of [source_id, target_id] pairs.
        Example: [["672", "P38398"], ["675", "O15129"], ...]

    Common use cases:
        - Bridging databases on different SPARQL endpoints
        - Mapping gene IDs to protein accessions for UniProt SPARQL queries
        - Finding PDB structures for a set of proteins
        - Identifying ChEMBL drug targets for a list of genes
    """
    toolcall_log("convertId")
    params = {
        "ids": ids,
        "route": route,
        "report": "pair",
        "format": "json",
        "limit": limit,
        "offset": offset,
        "noheader": "0"
    }

    response = await _client.get("/convert", params=params)
    response.raise_for_status()
    return response.json().get("results")


@togoid_mcp.tool()
async def countId(
    source: str,
    target: str,
    ids: str
) -> dict:
    """Check how many of your IDs can be converted before doing bulk conversion.

    A lightweight pre-check: tells you how many source IDs have mappings in the
    target database WITHOUT actually returning the mapped IDs. Use this to:
        - Verify your IDs are in the correct format
        - Estimate result size before a large convertId call
        - Check if a conversion route works for your specific IDs

    Args:
        source: Source database key (e.g., 'ncbigene', 'uniprot')
        target: Target database key (e.g., 'uniprot', 'pdb')
        ids: Comma-separated list of source IDs to check

    Returns:
        Dictionary with:
        - source count: number of input IDs recognized
        - target count: number of target IDs found

    Example:
        >>> countId('ncbigene', 'uniprot', '672,675,7157')
        # Returns: {"source": 3, "target": 5}
        # (3 genes map to 5 UniProt entries — some genes have multiple proteins)
    """
    toolcall_log("countId")
    response = await _client.get(
        f"/count/{source}-{target}",
        params={"ids": ids}
    )
    response.raise_for_status()
    return response.json()