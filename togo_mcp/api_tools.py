import httpx
from typing import List, Dict, Annotated, Any, Optional
from pydantic import Field
import json
import re

from .server import *

######################################
#####　Database-specific tools ########
######################################
# DB: UniProt
@mcp.tool()
async def search_uniprot_entity(query: str, limit: int = 20) -> str:
    """
    Search for a UniProt entity ID by query.

    Args:
        query (str): The query to search for. The query should be unambiguous enough to uniquely identify the entity.
        limit (int): The maximum number of results to return. Default is 20.

    Returns:
        str: The UniProt protein entity ID corresponding to the given query."
    """
    toolcall_log("search_uniprot_entity")
    url = "https://rest.uniprot.org/uniprotkb/search"
    params = {
        "query": query,
        "fields": "accession,protein_name,organism_name",
        "format": "tsv",
        "size": limit 
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.text
        return data
    except httpx.HTTPError as e:
        print(f"Error querying UniProt: {e}")
        raise

# DB: ChEMBL
async def search_chembl_generic(entity_type: str, query: str, limit: int = 20) -> dict:
    """
    Search for ChEMBL ID by query.

    Args:
        entity_type (str): The type of entity to search for.
        query (str): The query string to search for.
        limit (int): The maximum number of results to return.

    Returns:
        A dictionary parsed from the JSON response.
    """
    url = f"https://www.ebi.ac.uk/chembl/api/data/{entity_type}/search.json"
    params = {"q": query, "limit": limit}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"Error querying ChEMBL {entity_type}: {e}")
        raise


@mcp.tool()
async def search_chembl_id_lookup(
    query: Annotated[str, Field(description="The query string to search for.")],
    limit: Annotated[int, Field(description="The maximum number of results to return.")] = 20
    ) -> dict:
    """
    Search for ChEMBL ID by query.

    Returns:
        str: A JSON-formatted string containing the search results.
    """
    toolcall_log("search_chembl_id_lookup")
    bulk = await search_chembl_generic("chembl_id_lookup", query, limit)
    total_count = bulk.get("page_meta", {}).get("total_count", 0)
    parsed_results = []
    for result in bulk.get("chembl_id_lookups", []):
        parsed_results.append({
            "chembl_id": result.get("chembl_id"),
            "entity_type": result.get("entity_type"),
            "score": result.get("score")})

    return {"total_count": total_count, "results": parsed_results}

@mcp.tool()
async def search_chembl_target(query: str, limit: int = 20) -> dict:
    """
    Search for ChEMBL target by query.
    
    Targets in ChEMBL represent biological entities (proteins, protein complexes, 
    nucleic acids, organisms, tissues, cell lines) that are the focus of drug 
    discovery and bioactivity studies.
    
    Args:
        query (str): Search query string. Can be:
            - Target name (e.g., "Thrombin", "EGFR", "Dopamine receptor")
            - Gene name (e.g., "BRCA1", "TP53")
            - UniProt accession (e.g., "P00734")
            - Organism name (e.g., "Homo sapiens")
            - Any keywords related to target properties
        limit (int, optional): Maximum number of results to return. Defaults to 20.
    
    Returns:
        dict: Dictionary containing:
            - 'total_count' (int): Total number of matching targets found
            - 'results' (list): List of target dictionaries, each containing:
                - 'chembl_id' (str): ChEMBL target identifier (e.g., "CHEMBL1824")
                - 'name' (str): Preferred target name
                - 'organism' (str): Organism name (e.g., "Homo sapiens")
                - 'type' (str): Target type (e.g., "SINGLE PROTEIN", "PROTEIN COMPLEX")
                - 'score' (float): Relevance score for the search query
    
    Example:
        >>> results = await search_chembl_target("EGFR human", limit=5)
        >>> print(f"Found {results['total_count']} targets")
        >>> for target in results['results']:
        ...     print(f"{target['chembl_id']}: {target['name']} ({target['organism']})")
        
        Output:
        Found 15 targets
        CHEMBL203: Epidermal growth factor receptor (Homo sapiens)
    
    Target Types:
        - SINGLE PROTEIN: Individual protein target
        - PROTEIN COMPLEX: Multi-protein complex
        - PROTEIN FAMILY: Group of related proteins
        - NUCLEIC-ACID: DNA/RNA targets
        - TISSUE: Tissue-level target
        - CELL-LINE: Cell line target
        - ORGANISM: Whole organism target
    
    Raises:
        httpx.HTTPError: If the API request fails
    """
    toolcall_log("search_chembl_target")
    bulk = await search_chembl_generic("target", query, limit)
    total_count = bulk.get("page_meta", {}).get("total_count", 0)

    parsed_results = []
    for target in bulk.get("targets", []):
        parsed_results.append({
            "chembl_id": target.get("target_chembl_id"),
            "name": target.get("pref_name"),
            "organism": target.get("organism"),
            "type": target.get("target_type"),
            "score": target.get("score")
        })

    return {"total_count": total_count, "results": parsed_results}


@mcp.tool()
async def search_chembl_molecule(query: str, limit: int = 20) -> dict:
    """
    Search for ChEMBL molecule by query.
    
    Molecules in ChEMBL represent small molecule drugs, drug candidates, and 
    bioactive compounds with reported bioactivity data. This includes approved 
    drugs, clinical candidates, and research compounds.
    
    Args:
        query (str): Search query string. Can be:
            - Molecule name (e.g., "Aspirin", "Imatinib", "Caffeine")
            - Drug name (brand or generic, e.g., "Gleevec", "Paracetamol")
            - Synonyms or alternative names
            - SMILES notation (chemical structure string)
            - InChI or InChI Key
            - Any keywords related to molecule properties
        limit (int, optional): Maximum number of results to return. Defaults to 20.
    
    Returns:
        dict: Dictionary containing:
            - 'total_count' (int): Total number of matching molecules found
            - 'results' (list): List of molecule dictionaries, each containing:
                - 'chembl_id' (str): ChEMBL molecule identifier (e.g., "CHEMBL25")
                - 'name' (str): Preferred molecule name (may be None for some compounds)
                - 'score' (float): Relevance score for the search query
    
    Example:
        >>> results = await search_chembl_molecule("aspirin", limit=5)
        >>> print(f"Found {results['total_count']} molecules")
        >>> for molecule in results['results']:
        ...     print(f"{molecule['chembl_id']}: {molecule['name']} (score: {molecule['score']})")
        
        Output:
        Found 3 molecules
        CHEMBL25: Aspirin (score: 23.5)
        CHEMBL1456: Acetylsalicylic acid derivative (score: 12.3)
    
    Use Cases:
        - Finding ChEMBL IDs for known drugs or compounds
        - Discovering molecules with similar names
        - Searching for bioactive compounds by structure (using SMILES/InChI)
        - Identifying research compounds and clinical candidates
    
    Note:
        - Some molecules may not have a preferred name and 'name' field will be None
        - Higher scores indicate better matches to the query
        - For structure-based searches, use SMILES or InChI notation
    
    Raises:
        httpx.HTTPError: If the API request fails
    """
    toolcall_log("search_chembl_molecule")
    bulk = await search_chembl_generic("molecule", query, limit)
    total_count = bulk.get("page_meta", {}).get("total_count", 0)
    parsed_results = []
    for molecule in bulk.get("molecules", []):
        parsed_results.append({
            "chembl_id": molecule.get("molecule_chembl_id"),
            "name": molecule.get("pref_name"),
            "score": molecule.get("score")
        })

    return {"total_count": total_count, "results": parsed_results}

# @mcp.tool()
async def get_chembl_entity_by_id(service: str, chembl_id: str) -> str:
    """
    Get ChEMBL entity by ID.

    Args:
        service (str): The service to use for the search. Supported values are:
            - "activity" (for ChEMBL activity search, activity ID is an integer; remove the "CHEMBL" or "CHEMBL_ACT" prefixes)
            - "assay" (for ChEMBL assay search)
            - "assay_class" (for ChEMBL assay class search)
            - "atc_class" (for ChEMBL ATC class search)
            - "binding_site" (for ChEMBL binding site search)
            - "biotherapeutic" (for ChEMBL biotherapeutic search)
            - "cell_line" (for ChEMBL cell line search)
            - "chembl_id_lookup" (for ChEMBL ID lookup)
            - "chembl_release" (for ChEMBL release search)
            - "compound_record" (for ChEMBL compound search)
            - "compound_structural_alert" (for ChEMBL compound structural alert search)
            - "document" (for ChEMBL document search)
            - "drug" (for ChEMBL drug search)
            - "drug_indication" (for ChEMBL drug indication search)
            - "drug_warning" (for ChEMBL drug warning search)
            - "go_slim" (for ChEMBL GO slim search)
            - "image" (for ChEMBL image search)
            - "mechanism" (for ChEMBL mechanism search)
            - "metabolism" (for ChEMBL metabolism search)
            - "molecule" (for ChEMBL molecule search)
            - "molecule_form" (for ChEMBL molecule form search)
            - "organism" (for ChEMBL organism search)
            - "protein_classification" (for ChEMBL protein classification search)
            - "source" (for ChEMBL source search)
            - "target" (for ChEMBL target search)
            - "target_relation" (for ChEMBL target relation search)
            - "tissue" (for ChEMBL tissue search)
            - "xref_source" (for ChEMBL cross-reference source search)

        chembl_id (str): The ChEMBL ID to search for.

    """
    toolcall_log("get_chembl_entity_by_id")
    url = f"https://www.ebi.ac.uk/chembl/api/data/{service}/{chembl_id}.json"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        print(f"Error fetching ChEMBL entity {chembl_id}: {e}")
        raise


# DB: PubChem
@mcp.tool()
async def get_pubchem_compound_id(compound_name: str) -> str:
    """
    Get a PubChem compound ID

    Args: Compound name
        example: "resveratrol"

    Returns: PubChem Compound ID in the JSON format
    """
    toolcall_log("get_pubchem_compound_id")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound_name}/cids/JSON"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        print(f"Error fetching PubChem compound ID for {compound_name}: {e}")
        raise

@mcp.tool()
async def get_compound_attributes_from_pubchem(pubchem_compound_id: str) -> str:
    """
    Get compound attributes from PubChem RDF

    Args: PubChem Compound ID
        example: "445154"

    Returns: Compound attributes in the JSON format
    """
    toolcall_log("get_compound_attributes_from_pubchem")
    url = "https://togodx.dbcls.jp/human/sparqlist/api/metastanza_pubchem_compound"
    params = {"id": pubchem_compound_id}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        print(f"Error fetching PubChem compound attributes for {pubchem_compound_id}: {e}")
        raise

# DB: PDB
@mcp.tool()
async def search_pdb_entity(db: str, query: str, limit: int = 20) -> str:
    """
    Search for PDBj entry information by keywords.

    Args:
        db (str): The database to search in. Allowed values are:
            - "pdb" (Protein Data Bank, protein structures)
            - "cc" (Chemical Component Dictionary, chemical components or small molecules in PDB)
            - "prd" (BIRD, Biologically Interesting Reference Molecule Dictionary, mostly peptides).
        query (str): Query string, any keywords that can be used to search for PDB entries.
        limit (int): The maximum number of results to return. Default is 20.

    Returns:
        str: A JSON-formatted string containing the search results.
    """
    toolcall_log("search_pdb_entity")
    url = f"https://pdbj.org/rest/newweb/search/{db}?query={query}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        # Parse the response as JSON
        total_results = response.json().get("total", 0)
        result_list = [{entry[0]: entry[1]} for entry in response.json().get("results", [])[:limit]]
        response_dict = {"total": total_results, "results": result_list}
        return json.dumps(response_dict)
    except httpx.HTTPError as e:
        print(f"Error searching PDB {db} for {query}: {e}")
        raise

# DB: MeSH
@mcp.tool()
async def search_mesh_descriptor(query: str, limit: int = 10) -> str:
    """
    Search for MeSH ID by query.

    Args:
        query (str): The query string to search for.
        limit (int): The maximum number of results to return. Default is 10.

    Returns:
        str: A JSON-formatted string containing the search results.
    """
    toolcall_log("search_mesh_descriptor")
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"label": query,
              "match": "contains",
              "limit": limit}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        print(f"Error searching MeSH for {query}: {e}")
        raise

# DB: Reactome
@mcp.tool()
async def search_reactome_entity(
    query: str,
    species: Optional[List[str]] = None,
    types: Optional[List[str]] = None,
    rows: int = 30
) -> List[Dict[str, str]]:
    """
    Search the Reactome knowledgebase using keyword search.
    
    Parameters:
    -----------
    query : str
        The search query string (e.g., "apoptosis", "TP53", "cell cycle")
    species : list of str, optional
        Filter by species (e.g., ["Homo sapiens"], ["9606"])
    types : list of str, optional
        Filter by entity types (e.g., ["Pathway", "Reaction", "Complex"])
    rows : int, default=30
        Number of results to return
    
    Returns:
    --------
    list of dict
        List of results with 'id', 'name', and 'type' fields
        Example: [
            {'id': 'R-HSA-109581', 'name': 'Apoptosis', 'type': 'Pathway'},
            {'id': 'R-HSA-204981', 'name': '14-3-3epsilon...', 'type': 'Reaction'}
        ]
        
    Example:
    --------
    >>> results = search_reactome("apoptosis", rows=5)
    >>> for entry in results:
    ...     print(f"{entry['type']:10} {entry['id']}: {entry['name']}")
    
    >>> # Filter by type
    >>> pathways = [r for r in results if r['type'] == 'Pathway']
    """
    toolcall_log("search_reactome_entity")
    # Build API request
    base_url = "https://reactome.org/ContentService/search/query"
    params = {
        "query": query,
        "cluster": "true",
        "start": 0,
        "rows": rows
    }
    
    if species:
        params["species"] = ','.join(species)
    if types:
        params["types"] = ','.join(types)
    
    # Make API call
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                base_url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=30.0
            )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        print(f"Error querying Reactome: {e}")
        raise
    
    # Extract and return results
    results = []
    for result_group in data.get("results", []):
        for entry in result_group.get("entries", []):
            # Clean HTML highlighting tags from name
            name = entry.get('name', 'N/A')
            name = re.sub(r'<span class="highlighting"\s*>', '', name)
            name = re.sub(r'</span>', '', name)
            
            results.append({
                'id': entry.get('stId', entry.get('id', 'N/A')),
                'name': name.strip(),
                'type': entry.get('type', 'Unknown')
            })
    
    return results

# DB: RhEA
@mcp.tool()
async def search_rhea_entity(
    query: str,
    limit: Optional[int] = 100
) -> List[Dict[str, str]]:
    """
    Search Rhea database for biochemical reactions using keyword search.
    
    Args:
        query (str): Search query string. Examples:
                    - "ATP" - find reactions involving ATP
                    - "glucose" - find reactions with glucose
                    - "uniprot:*" - reactions with UniProt annotations
                    - "" - retrieve all reactions
        limit (int, optional): Maximum number of results. Defaults to 100.
    
    Returns:
        List[Dict[str, str]]: List of reactions, each containing:
            - 'rhea_id': Reaction identifier (e.g., "RHEA:10000")
            - 'equation': Reaction equation text
    
    Example:
        >>> results = search_rhea_entity("ATP", limit=5)
        >>> for reaction in results:
        ...     print(f"{reaction['rhea_id']}: {reaction['equation']}")
    """
    toolcall_log("search_rhea_entity")
    # API endpoint
    url = "https://www.rhea-db.org/rhea"
    
    params = {
        "query": query,
        "columns": "rhea-id,equation",
        "format": "tsv",
        "limit": limit
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        
        # Parse TSV response
        lines = response.text.strip().split('\n')
        
        if len(lines) < 2:
            return []
        
        # First line is header, skip it
        results = []
        for line in lines[1:]:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 2:
                    results.append({
                        'rhea_id': parts[0],
                        'equation': parts[1]
                    })
        
        return results
    
    except httpx.HTTPError as e:
        print(f"Error fetching data from Rhea API: {e}")
        return []
