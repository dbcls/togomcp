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
import re
import asyncio
import httpx
from typing import Optional, List, Dict, Any
from mcp.types import TextContent
from .server import toolcall_log
from fastmcp import FastMCP


# Get API key from environment
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "your-email@example.com")  # NCBI recommends providing email

# Rate limiting
RATE_LIMIT_DELAY = 0.1 if NCBI_API_KEY else 0.34  # 10/sec with key, 3/sec without

ncbi_mcp = FastMCP("NCBI API server")

class NCBISearchError(Exception):
    """Custom exception for NCBI API errors"""
    pass


# Database configuration with metadata
NCBI_DATABASES = {
    "gene": {
        "label": "NCBI Gene",
        "id_label": "Gene IDs",
        "url_template": "https://www.ncbi.nlm.nih.gov/gene/{id}",
        "description": "Search for genes by name, symbol, or other identifiers",
        "example_query": "BRCA1[Gene Name] AND Homo sapiens[Organism]",
        "supported_fields": ["[Organism]", "[Gene Name]", "[All Fields]"],
        "field_tags_critical": True,
    },
    "taxonomy": {
        "label": "NCBI Taxonomy",
        "id_label": "Taxonomy IDs (TaxIDs)",
        "url_template": "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={id}",
        "description": "Search for organisms and taxonomic information",
        "example_query": "Escherichia coli[Scientific Name]",
        "supported_fields": ["[Scientific Name]", "[Common Name]", "[All Fields]"],
        "field_tags_critical": False,
    },
    "clinvar": {
        "label": "ClinVar",
        "id_label": "Variation IDs",
        "url_template": "https://www.ncbi.nlm.nih.gov/clinvar/variation/{id}",
        "description": "Search for genetic variants and clinical interpretations",
        "example_query": "BRCA1[Gene Name] AND pathogenic[Clinical Significance]",
        "supported_fields": ["[Gene Name]", "[Clinical Significance]", "[All Fields]"],
        "field_tags_critical": True,
    },
    "medgen": {
        "label": "MedGen",
        "id_label": "Concept IDs (CUIs)",
        "url_template": "https://www.ncbi.nlm.nih.gov/medgen/{id}",
        "description": "Search for medical genetics concepts and conditions",
        "example_query": "breast cancer[All Fields]",
        "supported_fields": ["[All Fields]", "[Disease/Phenotype]"],
        "field_tags_critical": False,
    },
    "pubmed": {
        "label": "PubMed",
        "id_label": "PubMed IDs (PMIDs)",
        "url_template": "https://pubmed.ncbi.nlm.nih.gov/{id}",
        "description": "Search biomedical literature",
        "example_query": "CRISPR[Title/Abstract] AND gene editing[All Fields]",
        "supported_fields": ["[Title]", "[Author]", "[Journal]", "[All Fields]"],
        "field_tags_critical": False,
    },
    "pccompound": {
        "label": "PubChem Compound",
        "id_label": "Compound IDs (CIDs)",
        "url_template": "https://pubchem.ncbi.nlm.nih.gov/compound/{id}",
        "description": "Search for unique chemical structures",
        "example_query": "aspirin[All Fields]",
        "supported_fields": ["[All Fields]", "[MeSH Terms]"],
        "field_tags_critical": False,
    },
    "pcsubstance": {
        "label": "PubChem Substance",
        "id_label": "Substance IDs (SIDs)",
        "url_template": "https://pubchem.ncbi.nlm.nih.gov/substance/{id}",
        "description": "Search for depositor-provided chemical records",
        "example_query": "caffeine[All Fields]",
        "supported_fields": ["[All Fields]", "[Source Name]"],
        "field_tags_critical": False,
    },
    "pcassay": {
        "label": "PubChem BioAssay",
        "id_label": "Assay IDs (AIDs)",
        "url_template": "https://pubchem.ncbi.nlm.nih.gov/assay/assay.cgi?aid={id}",
        "description": "Search for biological screening data",
        "example_query": "kinase inhibitor[All Fields]",
        "supported_fields": ["[All Fields]", "[Target]"],
        "field_tags_critical": False,
    },
}


def _validate_query_field_tags(query: str, database: str) -> Dict[str, Any]:
    """
    Validate that the query includes appropriate NCBI field tags.
    
    Returns a dict with validation results and suggestions.
    """
    issues = []
    suggestions = []
    
    # Check if query has any field tags
    has_field_tags = bool(re.search(r'\[[^\]]+\]', query))
    
    # Get database info
    db_info = NCBI_DATABASES.get(database, {})
    is_critical = db_info.get("field_tags_critical", False)
    
    # Detect common organism terms without [Organism] tag
    organism_terms = ["human", "mouse", "rat", "archaea", "bacteria", "sapiens", "coli"]
    for term in organism_terms:
        if re.search(rf'\b{term}\b', query, re.IGNORECASE) and "[Organism]" not in query and "[organism]" not in query:
            issues.append(f"Term '{term}' found without [Organism] field tag")
            suggestions.append(f"Consider: '{term.capitalize()}[Organism]'")
    
    # Detect potential gene symbols without [Gene Name] tag (uppercase 3+ letters)
    if database == "gene":
        gene_pattern = r'\b[A-Z]{3,}\d*\b'
        potential_genes = re.findall(gene_pattern, query)
        if potential_genes and "[Gene Name]" not in query:
            issues.append(f"Potential gene symbols found without [Gene Name] tag: {', '.join(set(potential_genes))}")
            suggestions.append(f"Consider: '{potential_genes[0]}[Gene Name]'")
    
    # General warning if no field tags at all
    if not has_field_tags and is_critical:
        issues.append("No NCBI field tags found in query")
        suggestions.append(f"Add field tags from: {', '.join(db_info.get('supported_fields', []))}")
    
    return {
        "has_issues": len(issues) > 0,
        "is_critical": is_critical,
        "issues": issues,
        "suggestions": suggestions,
        "has_field_tags": has_field_tags
    }


async def _ncbi_esearch_api(
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


def _format_esearch_result(data: Dict[str, Any], db: str, query: str, validation: Optional[Dict] = None) -> str:
    """Format esearch results for display"""
    esearch_result = data.get("esearchresult", {})
    
    count = esearch_result.get("count", "0")
    ids = esearch_result.get("idlist", [])
    retmax = esearch_result.get("retmax", "0")
    retstart = esearch_result.get("retstart", "0")
    query_translation = esearch_result.get("querytranslation", "N/A")
    
    # Get database metadata
    db_info = NCBI_DATABASES.get(db, {})
    db_label = db_info.get("label", db.upper())
    id_label = db_info.get("id_label", "IDs")
    url_template = db_info.get("url_template")
    
    result = f"""{db_label} Search Results
=====================================
Query: {query}
Query Translation: {query_translation}

Total Results: {count}
Returned: {len(ids)} (showing {retstart}-{int(retstart) + len(ids)})

{id_label}: {', '.join(ids)}
"""
    
    if esearch_result.get("warninglist"):
        result += f"\nWarnings: {esearch_result['warninglist']}"
    
    # Add validation warnings if present
    if validation and validation.get("has_issues"):
        result += "\n\n" + "⚠️  QUERY OPTIMIZATION SUGGESTIONS " + "⚠️"
        result += "\n" + "=" * 50 + "\n"
        
        if validation.get("is_critical"):
            result += "⚠️  CRITICAL: For comprehensive results, use NCBI field tags!\n"
            result += f"   Without field tags, you may miss 70-80% of relevant results.\n\n"
        
        for issue in validation.get("issues", []):
            result += f"• {issue}\n"
        
        if validation.get("suggestions"):
            result += "\nSuggestions:\n"
            for suggestion in validation.get("suggestions", []):
                result += f"  → {suggestion}\n"
        
        result += f"\nSupported field tags: {', '.join(db_info.get('supported_fields', []))}"
        result += f"\nExample: {db_info.get('example_query', 'N/A')}\n"
        result += "\nSee: https://www.ncbi.nlm.nih.gov/books/NBK3837/\n"
    
    # Add helpful link for first result
    if url_template and ids:
        first_url = url_template.format(id=ids[0])
        result += f"\n\nView first result: {first_url}"
    
    return result


@ncbi_mcp.tool()
async def ncbi_esearch(
    database: str,
    query: str,
    max_results: int = 20,
    start_index: int = 0,
    sort_by: Optional[str] = None,
    search_field: Optional[str] = None
) -> List[TextContent]:
    """
    Search NCBI databases using E-utilities esearch API.
    
    ⚠️  CRITICAL FOR COMPREHENSIVE RESULTS ⚠️
    ALWAYS use NCBI field tags for Gene, ClinVar, and similar databases!
    Without field tags, you may miss 70-80% of relevant results.
    
    MANDATORY FIELD TAGS FOR GENE DATABASE:
    • [Organism] - Taxonomic filtering (e.g., "Homo sapiens[Organism]", "Archaea[Organism]")
    • [Gene Name] - Gene symbols (e.g., "TP53[Gene Name]", "nifH[Gene Name]")
    • [All Fields] - Broad keyword search (e.g., "nitrogenase[All Fields]")
    
    IMPACT OF FIELD TAGS (Gene Database):
    • Without field tags: ~300 results (20-30% recall) ❌
    • With field tags: ~1,300 results (100% recall) ✅
    • Performance loss: Missing field tags = 70-80% data loss!
    
    Args:
        database: NCBI database name. Supported values:
            - "gene" or "ncbigene": NCBI Gene database ⚠️ FIELD TAGS CRITICAL
            - "taxonomy": NCBI Taxonomy (organism information)
            - "clinvar": ClinVar (genetic variants) ⚠️ FIELD TAGS CRITICAL
            - "medgen": MedGen (medical genetics concepts)
            - "pubmed": PubMed (biomedical literature)
            - "pccompound": PubChem Compound
            - "pcsubstance": PubChem Substance
            - "pcassay": PubChem BioAssay
        query: Search query with NCBI field tags and boolean operators
        max_results: Maximum number of results to return (default: 20)
        start_index: Starting index for pagination (default: 0)
        sort_by: Optional sort order (e.g., "relevance", "pub_date" for PubMed)
        search_field: Optional specific field to search in
    
    Returns:
        Formatted search results with database-specific IDs
    
    Examples - GENE DATABASE (CRITICAL):
        ✅ CORRECT (finds ~1,300 archaeal nifH genes, 100% recall):
           database="gene"
           query="Archaea[Organism] AND (nifH[Gene Name] OR nitrogenase[All Fields])"
        
        ❌ WRONG (finds only ~300 genes, 23% recall):
           database="gene"
           query="archaea AND nifH"
           Problem: Missing [Organism] and [Gene Name] field tags!
        
        ✅ CORRECT (human genes):
           database="gene"
           query="Homo sapiens[Organism] AND TP53[Gene Name]"
        
        ❌ WRONG (incomplete results):
           query="human AND TP53"
    
    Examples - OTHER DATABASES:
        PubMed: database="pubmed", query="CRISPR[Title/Abstract] AND gene editing"
        Taxonomy: database="taxonomy", query="Escherichia coli[Scientific Name]"
        ClinVar: database="clinvar", query="BRCA1[Gene Name] AND pathogenic[Clinical Significance]"
        PubChem: database="pccompound", query="aspirin[All Fields]"
    
    Learn more: https://www.ncbi.nlm.nih.gov/books/NBK3837/
    """
    toolcall_log("ncbi_esearch")
    
    # Normalize database name (handle aliases)
    db_aliases = {
        "ncbigene": "gene",
    }
    normalized_db = db_aliases.get(database.lower(), database.lower())
    
    # Validate database
    if normalized_db not in NCBI_DATABASES:
        supported_dbs = ", ".join(NCBI_DATABASES.keys())
        return [TextContent(
            type="text",
            text=f"Error: Unsupported database '{database}'. Supported databases: {supported_dbs}"
        )]
    
    # Validate query for field tags
    validation = _validate_query_field_tags(query, normalized_db)
    
    try:
        data = await _ncbi_esearch_api(
            db=normalized_db,
            term=query,
            retmax=max_results,
            retstart=start_index,
            sort=sort_by,
            field=search_field
        )
        result = _format_esearch_result(data, normalized_db, query, validation)
        
        return [TextContent(type="text", text=result)]
    
    except NCBISearchError as e:
        return [TextContent(type="text", text=f"Error searching NCBI {database}: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]


@ncbi_mcp.tool()
async def ncbi_list_databases() -> List[TextContent]:
    """
    List all supported NCBI databases with descriptions and example queries.
    
    Returns:
        Formatted list of available databases
    """
    toolcall_log("ncbi_list_databases")
    
    result = "Supported NCBI Databases\n" + "=" * 50 + "\n\n"
    
    for db_name, db_info in NCBI_DATABASES.items():
        critical_marker = " ⚠️ FIELD TAGS CRITICAL" if db_info.get("field_tags_critical") else ""
        result += f"{db_info['label']} (database=\"{db_name}\"){critical_marker}\n"
        result += f"  Description: {db_info['description']}\n"
        result += f"  ID Type: {db_info['id_label']}\n"
        result += f"  Example Query: {db_info['example_query']}\n"
        result += f"  Supported Fields: {', '.join(db_info['supported_fields'])}\n\n"
    
    result += "\n⚠️  IMPORTANT: For Gene and ClinVar databases, ALWAYS use field tags!\n"
    result += "Without field tags, you may miss 70-80% of relevant results.\n\n"
    result += "Usage:\n"
    result += "  Use ncbi_esearch(database=\"<db_name>\", query=\"<your_query>\")\n"
    result += "  Example: ncbi_esearch(database=\"gene\", query=\"BRCA1[Gene Name] AND Homo sapiens[Organism]\")\n"
    result += "\nLearn more: https://www.ncbi.nlm.nih.gov/books/NBK3837/\n"
    
    return [TextContent(type="text", text=result)]


# Additional utility functions for future use
@ncbi_mcp.tool()
async def ncbi_esummary(database: str, ids: List[str]) -> List[TextContent]:
    """
    Fetch summary information for given IDs using esummary.
    Useful for getting detailed info after esearch.
    
    Args:
        database: NCBI database name
        ids: List of IDs to fetch summaries for
    
    Returns:
        Parsed JSON response with summary data
    """
    toolcall_log("ncbi_esummary")
    
    # Normalize database name
    db_aliases = {"ncbigene": "gene"}
    normalized_db = db_aliases.get(database.lower(), database.lower())
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    params = {
        "db": normalized_db,
        "id": ",".join(ids),
        "retmode": "json",
        "tool": "TogoMCP",
        "email": NCBI_EMAIL
    }
    
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    await asyncio.sleep(RATE_LIMIT_DELAY)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Format the response nicely
            import json
            formatted_json = json.dumps(data, indent=2)
            return [TextContent(type="text", text=formatted_json)]
            
    except Exception as e:
        return [TextContent(type="text", text=f"Error fetching summaries: {str(e)}")]


@ncbi_mcp.tool()
async def ncbi_efetch(
    database: str,
    ids: List[str],
    rettype: str = "xml",
    retmode: str = "text"
) -> List[TextContent]:
    """
    Fetch full records using efetch.
    Returns actual data (sequences, records, etc.)
    
    Args:
        database: NCBI database name
        ids: List of IDs to fetch
        rettype: Return type (xml, fasta, gb, etc.)
        retmode: Return mode (text, xml, json where applicable)
    
    Returns:
        Response text in requested format
    """
    toolcall_log("ncbi_efetch")
    
    # Normalize database name
    db_aliases = {"ncbigene": "gene"}
    normalized_db = db_aliases.get(database.lower(), database.lower())
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    params = {
        "db": normalized_db,
        "id": ",".join(ids),
        "rettype": rettype,
        "retmode": retmode,
        "tool": "TogoMCP",
        "email": NCBI_EMAIL
    }
    
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    await asyncio.sleep(RATE_LIMIT_DELAY)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            return [TextContent(type="text", text=response.text)]
            
    except Exception as e:
        return [TextContent(type="text", text=f"Error fetching records: {str(e)}")]
