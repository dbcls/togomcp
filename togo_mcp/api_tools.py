import json
import re
from typing import Annotated, Literal

import httpx
from pydantic import Field

from .server import *

# Shared httpx clients for connection reuse
_uniprot_client = httpx.AsyncClient(base_url="https://rest.uniprot.org", timeout=30.0)
_chembl_client = httpx.AsyncClient(base_url="https://www.ebi.ac.uk", timeout=30.0)
_pubchem_client = httpx.AsyncClient(timeout=30.0)
_pdbj_client = httpx.AsyncClient(base_url="https://pdbj.org", timeout=30.0)
_mesh_client = httpx.AsyncClient(base_url="https://id.nlm.nih.gov", timeout=30.0)
_reactome_client = httpx.AsyncClient(base_url="https://reactome.org", timeout=30.0)
_rhea_client = httpx.AsyncClient(base_url="https://www.rhea-db.org", timeout=30.0)


# Aliases LLMs commonly use in place of `query` when calling search tools.
# Every `search_*` tool accepts these as keyword aliases and folds them into
# `query` via _resolve_query_alias().
def _resolve_query_alias(
    query: str = "",
    *,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> str:
    """Return the first non-empty value among `query` and its accepted aliases."""
    return query or search or term or keyword or keywords or search_term or name


######################################
#####　Database-specific tools ########
######################################
# DB: UniProt
@mcp.tool()
async def search_uniprot_entity(
    query: str = "",
    limit: int = 20,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> str:
    """
    Search for a UniProt entity ID by query.

    ⚠️ Only the search string and `limit` are accepted. Extra parameters
       like `taxon`, `organism`, `reviewed`, `species`, etc. are silently
       dropped and have no effect — express such filters inside the Solr
       query string instead (e.g., `organism_id:9606 AND reviewed:true`).

    The search string can be passed as any of: `query` (canonical),
    `search`, `term`, `keyword`, `keywords`, `search_term`, or `name`.

    Args:
        query (str): The Solr-style query string for the UniProtKB /search endpoint.

            QUERY SYNTAX:
            - Simple keyword: "rubisco"
            - Field-specific: "field:value"  (e.g., "gene:BRCA1", "protein_name:rubisco")
            - Boolean operators: AND, OR, NOT  (e.g., "gene:TP53 AND organism_id:9606")
            - Grouping with parentheses: "((gene:CTNNB1) AND (taxonomy_id:9606))"
            - Wildcards (* suffix): "gene:PRO*" matches any gene starting with PRO
            - Ranges: "length:[1000 TO 2000]" or open-ended "length:[5000 TO *]"

            KEY QUERY FIELDS:
            Identity / Name:
              accession          UniProt primary accession (e.g., "accession:P04637")
              id                 UniProt entry name / mnemonic (e.g., "id:P53_HUMAN")
              protein_name       Protein name, including synonyms (e.g., "protein_name:rubisco")
              gene               Gene name with wildcard support (e.g., "gene:BRCA*")
              gene_exact         Exact gene name match (e.g., "gene_exact:TP53")
              ec                 Enzyme Commission number (e.g., "ec:1.1.1.1")

            Taxonomy:
              organism_id        NCBI taxonomy ID (e.g., "organism_id:9606" for human,
                                 "organism_id:10090" for mouse)
              organism_name      Organism scientific or common name
              taxonomy_id        Taxon ID including all descendants
              lineage            Taxonomic lineage keyword

            Annotation status:
              reviewed           true = Swiss-Prot (manually reviewed),
                                 false = TrEMBL (automatically annotated)
                                 ALWAYS add "reviewed:true" when seeking high-quality entries.

            Sequence properties:
              length             Sequence length as a range (e.g., "length:[100 TO 500]")
              mass               Molecular mass in Daltons (range supported)
              existence          Protein existence level: 1 (protein), 2 (transcript),
                                 3 (homology), 4 (predicted), 5 (uncertain)

            Functional annotation:
              keyword            UniProt keyword name (e.g., "keyword:Kinase")
              keyword_id         UniProt keyword ID (e.g., "keyword_id:KW-0418")
              function           Function free-text annotation
              family             Protein family (e.g., "family:globin")
              organelle          Subcellular organelle (e.g., "organelle:chloroplast")
              cc_subcellular_location  Subcellular location comment

            Cross-references:
              database           Database cross-reference (e.g., "database:PDB")
              xref               Cross-reference ID (e.g., "xref:pdb-1A2B")
              chebi              ChEBI ID (e.g., "chebi:15422")
              interactor         UniProt accession of interacting protein

            Literature:
              lit_author         Author surname (e.g., "lit_author:Smith")
              lit_pubmed         PubMed ID
              lit_doi            DOI

            EXAMPLES (structured queries):
              # Reviewed human TP53 protein
              "gene_exact:TP53 AND organism_id:9606 AND reviewed:true"

              # All human kinases manually reviewed
              "keyword:Kinase AND organism_id:9606 AND reviewed:true"

              # EGFR in human or mouse
              "gene_exact:EGFR AND (organism_id:9606 OR organism_id:10090) AND reviewed:true"

              # Long chloroplast proteins (>= 5000 aa) in any organism
              "organelle:chloroplast AND length:[5000 TO *]"

              # Proteins with PDB structures involved in apoptosis
              "database:PDB AND keyword:Apoptosis AND organism_id:9606 AND reviewed:true"

              # Proteins encoded by gene names starting with "PIK3"
              "gene:PIK3* AND organism_id:9606 AND reviewed:true"

        limit (int): The maximum number of results to return. Default is 20.

    Returns:
        str: TSV-formatted results with columns: accession, protein_name, organism_name.
    """
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    params = {
        "query": query,
        "fields": "accession,protein_name,organism_name",
        "format": "tsv",
        "size": limit,
    }
    try:
        response = await _uniprot_client.get("/uniprotkb/search", params=params)
        raise_for_status_with_body(response, context="UniProt search")
        data = response.text
        return data
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"UniProt search failed: {type(e).__name__}: {e}")
        return (
            f"Error: UniProt REST API request failed ({type(e).__name__}: {e}). "
            "Usually transient — retry once after a brief delay. If it keeps "
            "failing, fall back to SPARQL: "
            "run_sparql(database='uniprot', sparql_query=...)."
        )


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
    params = {"q": query, "limit": limit}
    try:
        response = await _chembl_client.get(
            f"/chembl/api/data/{entity_type}/search.json", params=params
        )
        raise_for_status_with_body(response, context="ChEMBL search")
        return response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"ChEMBL {entity_type} search failed: {type(e).__name__}: {e}")
        return {
            "error": (
                f"ChEMBL REST API request failed ({type(e).__name__}: {e}). "
                "Usually transient — retry once after a brief delay. If it "
                "keeps failing, fall back to SPARQL: "
                "run_sparql(database='chembl', sparql_query=...)."
            )
        }


@mcp.tool()
async def search_chembl_id_lookup(
    query: Annotated[
        str, Field(description="The query string to search for.", default="")
    ] = "",
    limit: Annotated[
        int, Field(description="The maximum number of results to return.")
    ] = 20,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """
    Search for ChEMBL ID by query.

    The search string can be passed as any of: `query` (canonical),
    `search`, `term`, `keyword`, `keywords`, `search_term`, or `name`.

    Returns:
        str: A JSON-formatted string containing the search results.
    """
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    bulk = await search_chembl_generic("chembl_id_lookup", query, limit)
    total_count = bulk.get("page_meta", {}).get("total_count", 0)
    parsed_results = []
    for result in bulk.get("chembl_id_lookups", []):
        parsed_results.append(
            {
                "chembl_id": result.get("chembl_id"),
                "entity_type": result.get("entity_type"),
                "score": result.get("score"),
            }
        )

    return {"total_count": total_count, "results": parsed_results}


@mcp.tool()
async def search_chembl_target(
    query: str = "",
    limit: int = 20,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """
    Search for a biological TARGET (protein/receptor/enzyme) in ChEMBL.

    ⚠️ DO NOT use this tool to look up drugs, compounds, or molecules by name.
       For drug/compound/molecule names (e.g., "sorafenib", "imatinib", "aspirin"),
       use `search_chembl_molecule` instead.

    This tool searches for biological entities that drugs act upon — proteins,
    protein complexes, nucleic acids, organisms, tissues, and cell lines.
    "Target" here means *drug target*, NOT "the thing I am looking up".

    Only the search string and `limit` are supported. The search string can be
    passed as any of: `query` (canonical), `search`, `term`, `keyword`,
    `keywords`, `search_term`, or `name`.

    Args:
        query (str): Search query string referring to a biological target. Examples:
            - Target name (e.g., "Thrombin", "EGFR", "Dopamine receptor")
            - Gene name (e.g., "BRCA1", "TP53")
            - UniProt accession (e.g., "P00734")
            - Organism name (e.g., "Homo sapiens")
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
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    bulk = await search_chembl_generic("target", query, limit)
    total_count = bulk.get("page_meta", {}).get("total_count", 0)

    parsed_results = []
    for target in bulk.get("targets", []):
        parsed_results.append(
            {
                "chembl_id": target.get("target_chembl_id"),
                "name": target.get("pref_name"),
                "organism": target.get("organism"),
                "type": target.get("target_type"),
                "score": target.get("score"),
            }
        )

    return {"total_count": total_count, "results": parsed_results}


@mcp.tool()
async def search_chembl_molecule(
    query: str = "",
    limit: int = 20,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """
    Search for a DRUG / COMPOUND / MOLECULE by name or structure in ChEMBL.

    ✅ Use this tool for drug, compound, or molecule names
       (e.g., "sorafenib", "imatinib", "aspirin", "Gleevec").
    ⚠️ For biological targets (proteins, receptors, enzymes, genes such as
       EGFR, BRCA1, TP53), use `search_chembl_target` instead.

    Molecules in ChEMBL are small-molecule drugs, drug candidates, and
    bioactive compounds — including approved drugs, clinical candidates,
    and research compounds.

    Only the search string and `limit` are supported. The search string can be
    passed as any of: `query` (canonical), `search`, `term`, `keyword`,
    `keywords`, `search_term`, or `name`.

    Args:
        query (str): Search query string referring to a drug or compound. Examples:
            - Generic or brand drug name (e.g., "Aspirin", "Gleevec", "Paracetamol")
            - Research compound name
            - Synonyms or alternative names
            - SMILES notation (chemical structure string)
            - InChI or InChI Key
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
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    bulk = await search_chembl_generic("molecule", query, limit)
    total_count = bulk.get("page_meta", {}).get("total_count", 0)
    parsed_results = []
    for molecule in bulk.get("molecules", []):
        parsed_results.append(
            {
                "chembl_id": molecule.get("molecule_chembl_id"),
                "name": molecule.get("pref_name"),
                "score": molecule.get("score"),
            }
        )

    return {"total_count": total_count, "results": parsed_results}


# DB: PubChem
@mcp.tool()
async def get_pubchem_compound_id(compound_name: str) -> str:
    """
    Get a PubChem compound ID

    Args: Compound name
        example: "resveratrol"

    Returns: PubChem Compound ID in the JSON format
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound_name}/cids/JSON"
    try:
        response = await _pubchem_client.get(url)
        raise_for_status_with_body(response, context="PubChem CID lookup")
        return response.text
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(
            f"PubChem CID lookup failed for {compound_name!r}: "
            f"{type(e).__name__}: {e}"
        )
        return (
            f"Error: PubChem CID lookup failed for {compound_name!r} "
            f"({type(e).__name__}: {e}). Usually transient — retry once after "
            "a brief delay. If it keeps failing, fall back to SPARQL: "
            "run_sparql(database='pubchem', sparql_query=...)."
        )


@mcp.tool()
async def get_compound_attributes_from_pubchem(pubchem_compound_id: str) -> str:
    """
    Get compound attributes from PubChem RDF

    Args: PubChem Compound ID
        example: "445154"

    Returns: Compound attributes in the JSON format
    """
    url = "https://togodx.dbcls.jp/human/sparqlist/api/metastanza_pubchem_compound"
    params = {"id": pubchem_compound_id}
    try:
        response = await _pubchem_client.get(url, params=params)
        raise_for_status_with_body(response, context="PubChem compound attributes")
        return response.text
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(
            f"PubChem compound-attributes fetch failed for "
            f"{pubchem_compound_id!r}: {type(e).__name__}: {e}"
        )
        return (
            f"Error: PubChem compound-attributes fetch failed for "
            f"{pubchem_compound_id!r} ({type(e).__name__}: {e}). Usually "
            "transient — retry once after a brief delay. If it keeps failing, "
            "fall back to SPARQL: run_sparql(database='pubchem', "
            "sparql_query=...)."
        )


# DB: PDB
@mcp.tool()
async def search_pdb_entity(
    db: Literal["pdb", "cc", "prd"],
    query: str = "",
    limit: Annotated[int, Field(ge=0, le=500)] = 20,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> str:
    """
    Search for PDBj entry information by keywords.

    Args:
        db (str): The database to search in. Allowed values are:
            - "pdb" (Protein Data Bank, protein structures)
            - "cc" (Chemical Component Dictionary, chemical components or small molecules in PDB)
            - "prd" (BIRD, Biologically Interesting Reference Molecule Dictionary, mostly peptides).
        query (str): Query string, any keywords that can be used to search for PDB entries.
            Accepts aliases: `search`, `term`, `keyword`, `keywords`,
            `search_term`, `name`.
        limit (int): The maximum number of results to return. Default is 20.
            Must be in [0, 500].

    Note:
        The PDBj search hits multiple fields (title, authors, keywords,
        citation metadata), not just the title. An entry can appear
        even if its title does not contain the query. Always verify
        relevance against the returned name/title before relying on
        a hit.

    Returns:
        str: A JSON-formatted string containing the search results.
    """
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    # PDBj returns result rows as ordered arrays; the "name" column
    # lives at a different index per DB. For PRD, index 1 is always
    # empty — the human-readable name is at index 4.
    name_idx = {"pdb": 1, "cc": 1, "prd": 4}[db]
    try:
        response = await _pdbj_client.get(
            f"/rest/newweb/search/{db}", params={"query": query}
        )
        raise_for_status_with_body(response, context="PDBj search")
        payload = response.json()
        total_results = payload.get("total", 0)
        result_list = [
            {entry[0]: entry[name_idx] if len(entry) > name_idx else ""}
            for entry in payload.get("results", [])[:limit]
        ]
        response_dict = {"total": total_results, "results": result_list}
        return json.dumps(response_dict)
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(
            f"PDBj search failed for db={db!r} query={query!r}: "
            f"{type(e).__name__}: {e}"
        )
        return json.dumps({
            "error": (
                f"PDBj REST API request failed ({type(e).__name__}: {e}). "
                "Usually transient — retry once after a brief delay. If it "
                "keeps failing, fall back to SPARQL: "
                "run_sparql(database='pdb', sparql_query=...)."
            )
        })


# DB: MeSH
@mcp.tool()
async def search_mesh_descriptor(
    query: str = "",
    limit: int = 10,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> str:
    """
    Search for MeSH ID by query.

    Args:
        query (str): The query string to search for. Accepts aliases:
            `search`, `term`, `keyword`, `keywords`, `search_term`, `name`.
        limit (int): The maximum number of results to return. Default is 10.

    Returns:
        str: A JSON-formatted string containing the search results.
    """
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    params = {"label": query, "match": "contains", "limit": limit}
    try:
        response = await _mesh_client.get("/mesh/lookup/descriptor", params=params)
        raise_for_status_with_body(response, context="MeSH descriptor lookup")
        return response.text
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(
            f"MeSH descriptor lookup failed for {query!r}: "
            f"{type(e).__name__}: {e}"
        )
        return (
            f"Error: MeSH descriptor lookup failed ({type(e).__name__}: {e}). "
            "Usually transient — retry once after a brief delay. If it keeps "
            "failing, fall back to SPARQL: "
            "run_sparql(database='mesh', sparql_query=...)."
        )


# DB: Reactome
@mcp.tool()
async def search_reactome_entity(
    query: str = "",
    species: str | list[str] | None = None,
    types: str | list[str] | None = None,
    rows: int = 30,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> list[dict[str, str]]:
    """Search the Reactome knowledgebase using keyword search.

    Args:
        query: The search query string (e.g., "apoptosis", "TP53", "cell cycle").
            Accepts aliases: `search`, `term`, `keyword`, `keywords`,
            `search_term`, `name`.
        species: Filter by species. Must be the scientific name
            (e.g., "Homo sapiens", "Mus musculus"). Numeric NCBI taxon
            IDs like "9606" are rejected here (this tool raises ValueError)
            because the Reactome API silently ignores them AND can
            degrade co-occurring filters (e.g. `types`). Accepts a
            single string or a list of strings.
        types: Filter by entity types. Accepts a single string (e.g.,
            "Pathway") or a list (e.g., ["Pathway", "Reaction", "Complex"]).
        rows: Per-category result cap. Reactome clusters results by
            entity type (`cluster=true`), so `rows=30` returns up to 30
            hits *per type*, not 30 hits total. To bound the total,
            constrain `types` to a single value.

    Returns:
        List of results with 'id', 'name', and 'type' fields.
        Example: [
            {'id': 'R-HSA-109581', 'name': 'Apoptosis', 'type': 'Pathway'},
            {'id': 'R-HSA-204981', 'name': '14-3-3epsilon...', 'type': 'Reaction'}
        ]

    Example:
        >>> results = search_reactome("apoptosis", rows=5)
        >>> for entry in results:
        ...     print(f"{entry['type']:10} {entry['id']}: {entry['name']}")

        >>> # Filter by type
        >>> pathways = [r for r in results if r['type'] == 'Pathway']

    Raises:
        httpx.HTTPError: If the API request fails.
    """
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )
    if not query:
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )
    # Build API request
    params = {"query": query, "cluster": "true", "start": 0, "rows": rows}

    if species:
        species_list = [species] if isinstance(species, str) else list(species)
        bad = [s for s in species_list if s.strip().isdigit()]
        if bad:
            raise ValueError(
                f"species must be a scientific name (e.g. 'Homo sapiens'); "
                f"got numeric taxon ID(s): {bad}. The Reactome search API "
                "silently ignores numeric IDs and can also drop other filters."
            )
        params["species"] = ",".join(species_list)
    if types:
        params["types"] = types if isinstance(types, str) else ",".join(types)

    # Make API call
    try:
        response = await _reactome_client.get(
            "/ContentService/search/query",
            params=params,
            headers={"Accept": "application/json"},
        )
        raise_for_status_with_body(response, context="Reactome search")
        data = response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"Reactome search failed: {type(e).__name__}: {e}")
        return (
            f"Error: Reactome REST API request failed ({type(e).__name__}: "
            f"{e}). Reactome's search endpoint can be slow or briefly "
            "unavailable. Retry once after a brief delay. If it keeps "
            "failing, fall back to SPARQL: "
            "run_sparql(database='reactome', sparql_query=...)."
        )

    # Extract and return results
    results = []
    for result_group in data.get("results", []):
        for entry in result_group.get("entries", []):
            # Clean HTML highlighting tags from name
            name = entry.get("name", "N/A")
            name = re.sub(r'<span class="highlighting"\s*>', "", name)
            name = re.sub(r"</span>", "", name)

            results.append(
                {
                    "id": entry.get("stId", entry.get("id", "N/A")),
                    "name": name.strip(),
                    "type": entry.get("type", "Unknown"),
                }
            )

    return results


# DB: RhEA
@mcp.tool()
async def search_rhea_entity(
    query: str = "",
    limit: int | None = 100,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> list[dict[str, str]]:
    """
    Search Rhea database for biochemical reactions using keyword search.

    Args:
        query (str): Search query string. Examples:
                    - "ATP" - find reactions involving ATP
                    - "glucose" - find reactions with glucose
                    - "uniprot:*" - reactions with UniProt annotations
                    - "" - retrieve all reactions
                    Accepts aliases: `search`, `term`, `keyword`, `keywords`,
                    `search_term`, `name`.
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
    # Unlike other search tools, Rhea permits an empty query (returns all
    # reactions). Only coalesce when an alias was provided.
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    )

    params = {
        "query": query,
        "columns": "rhea-id,equation",
        "format": "tsv",
        "limit": limit,
    }

    try:
        response = await _rhea_client.get("/rhea", params=params)
        raise_for_status_with_body(response, context="Rhea search")

        # Parse TSV response
        lines = response.text.strip().split("\n")

        if len(lines) < 2:
            return []

        # First line is header, skip it
        results = []
        for line in lines[1:]:
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 2:
                    results.append({"rhea_id": parts[0], "equation": parts[1]})

        return results

    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"Rhea search failed: {type(e).__name__}: {e}")
        return (
            f"Error: Rhea REST API request failed ({type(e).__name__}: {e}). "
            "Usually transient — retry once after a brief delay. If it keeps "
            "failing, fall back to SPARQL: "
            "run_sparql(database='rhea', sparql_query=...)."
        )
