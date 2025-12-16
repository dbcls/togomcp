"""
NCBI E-utilities search tools for TogoMCP.

Provides keyword search functionality for NCBI databases using the esearch API:
- NCBI Gene (ncbigene)
- NCBI Taxonomy (taxonomy)
- ClinVar (clinvar)
- MedGen (medgen)
- PubMed (pubmed)
- PubChem Compound (pccompound)
- PubChem Substance (pcsubstance)
- PubChem BioAssay (pcassay)

Requires NCBI_API_KEY environment variable for optimal rate limits (10 req/sec vs 3 req/sec).
"""

import os
import asyncio
import httpx
from typing import Optional, List, Dict, Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from .server import *

# Get API key from environment
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "your-email@example.com")  # NCBI recommends providing email

# Rate limiting
RATE_LIMIT_DELAY = 0.1 if NCBI_API_KEY else 0.34  # 10/sec with key, 3/sec without

ncbi_mcp = FastMCP("NCBI API server")

class NCBISearchError(Exception):
    """Custom exception for NCBI API errors"""
    pass


async def ncbi_esearch(
    db: str,
    term: str,
    retmax: int = 20,
    retstart: int = 0,
    sort: Optional[str] = None,
    field: Optional[str] = None
) -> Dict[str, Any]:
    """
    Core function to query NCBI E-utilities esearch API.
    
    Args:
        db: NCBI database name
        term: Search query
        retmax: Maximum number of results
        retstart: Starting index for pagination
        sort: Sort order (database-specific)
        field: Specific field to search in
    
    Returns:
        Parsed JSON response from NCBI
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    
    params = {
        "db": db,
        "term": term,
        "retmax": retmax,
        "retstart": retstart,
        "retmode": "json",
        "tool": "TogoMCP",
        "email": NCBI_EMAIL
    }
    
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    if sort:
        params["sort"] = sort
    
    if field:
        params["field"] = field
    
    # Rate limiting
    await asyncio.sleep(RATE_LIMIT_DELAY)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check for errors in NCBI response
            if "error" in data:
                raise NCBISearchError(f"NCBI API error: {data['error']}")
            
            return data
            
        except httpx.HTTPError as e:
            raise NCBISearchError(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            raise NCBISearchError(f"Error querying NCBI: {str(e)}")


def format_esearch_result(data: Dict[str, Any], db: str, query: str) -> str:
    """Format esearch results for display"""
    esearch_result = data.get("esearchresult", {})
    
    count = esearch_result.get("count", "0")
    ids = esearch_result.get("idlist", [])
    retmax = esearch_result.get("retmax", "0")
    retstart = esearch_result.get("retstart", "0")
    query_translation = esearch_result.get("querytranslation", "N/A")
    
    # Database-specific labels
    db_labels = {
        "gene": "Gene IDs",
        "taxonomy": "Taxonomy IDs (TaxIDs)",
        "clinvar": "Variation IDs",
        "medgen": "Concept IDs (CUIs)",
        "pubmed": "PubMed IDs (PMIDs)",
        "pccompound": "Compound IDs (CIDs)",
        "pcsubstance": "Substance IDs (SIDs)",
        "pcassay": "Assay IDs (AIDs)"
    }
    
    id_label = db_labels.get(db, "IDs")
    
    result = f"""NCBI {db.upper()} Search Results
=====================================
Query: {query}
Query Translation: {query_translation}

Total Results: {count}
Returned: {len(ids)} (showing {retstart}-{int(retstart) + len(ids)})

{id_label}: {', '.join(ids)}
"""
    
    if esearch_result.get("warninglist"):
        result += f"\nWarnings: {esearch_result['warninglist']}"
    
    # Add helpful links for results
    if db == "pccompound" and ids:
        result += f"\n\nView first result: https://pubchem.ncbi.nlm.nih.gov/compound/{ids[0]}"
    elif db == "pcsubstance" and ids:
        result += f"\n\nView first result: https://pubchem.ncbi.nlm.nih.gov/substance/{ids[0]}"
    elif db == "pcassay" and ids:
        result += f"\n\nView first result: https://pubchem.ncbi.nlm.nih.gov/assay/assay.cgi?aid={ids[0]}"
    elif db == "gene" and ids:
        result += f"\n\nView first result: https://www.ncbi.nlm.nih.gov/gene/{ids[0]}"
    elif db == "taxonomy" and ids:
        result += f"\n\nView first result: https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={ids[0]}"
    elif db == "pubmed" and ids:
        result += f"\n\nView first result: https://pubmed.ncbi.nlm.nih.gov/{ids[0]}"
    
    return result

# Individual Tool Implementation Functions
@ncbi_mcp.tool()
async def search_ncbigene_entity(
    query: str,
    max_results: int = 20,
    organism: Optional[str] = None
) -> List[TextContent]:
    """
    Search NCBI Gene database for genes matching keywords.
    
    Args:
        query: Search query (supports Entrez syntax)
        max_results: Maximum number of results to return
        organism: Optional organism filter (e.g., 'Homo sapiens', 'human')
    
    Returns:
        Formatted search results with gene IDs
    """
    toolcall_log("search_ncbigene_entity")
    try:
        # Add organism filter if provided
        search_query = query
        if organism:
            search_query = f"{query} AND {organism}[organism]"
        
        data = await ncbi_esearch("gene", search_query, retmax=max_results)
        result = format_esearch_result(data, "gene", search_query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching NCBI Gene: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_taxonomy_entity(
    query: str,
    max_results: int = 20
) -> List[TextContent]:
    """
    Search NCBI Taxonomy database for organisms.
    
    Args:
        query: Search query for organism names or taxonomy
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results with taxonomy IDs
    """
    toolcall_log("search_taxonomy_entity")
    try:
        data = await ncbi_esearch("taxonomy", query, retmax=max_results)
        result = format_esearch_result(data, "taxonomy", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching NCBI Taxonomy: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_clinvar_entity(
    query: str,
    max_results: int = 20
) -> List[TextContent]:
    """
    Search ClinVar for genetic variants and clinical interpretations.
    
    Args:
        query: Search query for variants, genes, or conditions
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results with ClinVar variation IDs
    """
    toolcall_log("search_clinvar_entity")
    try:
        data = await ncbi_esearch("clinvar", query, retmax=max_results)
        result = format_esearch_result(data, "clinvar", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching ClinVar: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_medgen_entity(
    query: str,
    max_results: int = 20
) -> List[TextContent]:
    """
    Search MedGen for medical genetics concepts and conditions.
    
    Args:
        query: Search query for medical genetics concepts
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results with MedGen concept IDs
    """
    toolcall_log("search_medgen_entity")
    try:
        data = await ncbi_esearch("medgen", query, retmax=max_results)
        result = format_esearch_result(data, "medgen", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching MedGen: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_pubmed_entity(
    query: str,
    max_results: int = 20,
    sort_by: str = "relevance"
) -> List[TextContent]:
    """
    Search PubMed via NCBI E-utilities for biomedical literature.
    
    Args:
        query: Search query (supports PubMed/Entrez syntax)
        max_results: Maximum number of results to return
        sort_by: Sort order ('relevance' or 'pub_date')
    
    Returns:
        Formatted search results with PubMed IDs (PMIDs)
    """
    toolcall_log("search_pubmed_entity")
    try:
        data = await ncbi_esearch("pubmed", query, retmax=max_results, sort=sort_by)
        result = format_esearch_result(data, "pubmed", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching PubMed: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_pubchem_compound_entity(
    query: str,
    max_results: int = 20
) -> List[TextContent]:
    """
    Search PubChem Compound database for unique chemical structures.
    
    Args:
        query: Search query for chemical compounds
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results with PubChem Compound IDs (CIDs)
    """
    toolcall_log("search_pubchem_compound_entity")
    try:
        data = await ncbi_esearch("pccompound", query, retmax=max_results)
        result = format_esearch_result(data, "pccompound", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching PubChem Compound: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_pubchem_substance_entity(
    query: str,
    max_results: int = 20
) -> List[TextContent]:
    """
    Search PubChem Substance database for depositor-provided chemical records.
    
    Args:
        query: Search query for substance records
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results with PubChem Substance IDs (SIDs)
    """
    toolcall_log("search_pubchem_substance_entity")
    try:
        data = await ncbi_esearch("pcsubstance", query, retmax=max_results)
        result = format_esearch_result(data, "pcsubstance", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching PubChem Substance: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

@ncbi_mcp.tool()
async def search_pubchem_assay_entity(
    query: str,
    max_results: int = 20
) -> List[TextContent]:
    """
    Search PubChem BioAssay database for biological screening data.
    
    Args:
        query: Search query for bioassay data
        max_results: Maximum number of results to return
    
    Returns:
        Formatted search results with PubChem Assay IDs (AIDs)
    """
    toolcall_log("search_pubchem_assay_entity")
    try:
        data = await ncbi_esearch("pcassay", query, retmax=max_results)
        result = format_esearch_result(data, "pcassay", query)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching PubChem BioAssay: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]


# Additional utility functions for future use
@ncbi_mcp.tool()
async def esummary(db: str, ids: List[str]) -> Dict[str, Any]:
    """
    Fetch summary information for given IDs using esummary.
    Useful for getting detailed info after esearch.
    
    Args:
        db: NCBI database name
        ids: List of IDs to fetch summaries for
    
    Returns:
        Parsed JSON response with summary data
    """
    toolcall_log("esummary")
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    params = {
        "db": db,
        "id": ",".join(ids),
        "retmode": "json",
        "tool": "TogoMCP",
        "email": NCBI_EMAIL
    }
    
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    await asyncio.sleep(RATE_LIMIT_DELAY)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        return response.json()

@ncbi_mcp.tool()
async def efetch(db: str, ids: List[str], rettype: str = "xml") -> str:
    """
    Fetch full records using efetch.
    Returns actual data (sequences, records, etc.)
    
    Args:
        db: NCBI database name
        ids: List of IDs to fetch
        rettype: Return type (xml, fasta, gb, etc.)
    
    Returns:
        Response text in requested format
    """
    toolcall_log("efetch")
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    params = {
        "db": db,
        "id": ",".join(ids),
        "rettype": rettype,
        "retmode": "text",
        "tool": "TogoMCP",
        "email": NCBI_EMAIL
    }
    
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    await asyncio.sleep(RATE_LIMIT_DELAY)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        return response.text
