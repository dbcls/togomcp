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
    """Return the first non-empty value among `query` and its accepted aliases.

    These are all aliases for the single `query` parameter. Supplying two or
    more with *different* values is treated as a caller error and raises
    ValueError. A warning would only land in the server log, never reaching
    the (often LLM-driven) caller — where this conflict is a likely mistake
    (e.g. the model fills `query` while a wrapper fills `keyword`); raising
    surfaces it through the tool result so the caller can retry with one term.
    Duplicates with the same value, or a single value, resolve normally.
    """
    candidates = {
        "query": query, "search": search, "term": term, "keyword": keyword,
        "keywords": keywords, "search_term": search_term, "name": name,
    }
    provided = {k: v for k, v in candidates.items() if v}
    if len({*provided.values()}) > 1:
        raise ValueError(
            f"Multiple distinct search terms supplied: {provided}; pass only "
            "one — these are all aliases for the same `query` parameter."
        )
    return next(iter(provided.values()), "")


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
        str: TSV-formatted results with columns: accession, protein_name,
        organism_name. On upstream/HTTP failure this tool does NOT raise — it
        returns a plain string beginning with "Error:" (not TSV). Check for that
        prefix before parsing rows.
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
        dict: {'total_count' (int), 'results' (list)} where each result has
        'chembl_id', 'entity_type', and 'score'. On upstream/HTTP failure this
        tool does NOT raise — it returns a dict with a single 'error' key
        instead. Check for 'error' before reading 'results'.
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
    if "error" in bulk:
        # Propagate the upstream-failure payload rather than silently
        # collapsing it into an empty {'total_count': 0, 'results': []}.
        return bulk
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

    On upstream/HTTP failure this tool does NOT raise — it returns a dict with a
    single 'error' key (a message plus a "fall back to SPARQL" hint) instead of
    the usual {'total_count', 'results'} shape. Check for 'error' before reading
    'results'.
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
    if "error" in bulk:
        # Propagate the upstream-failure payload rather than silently
        # collapsing it into an empty {'total_count': 0, 'results': []}.
        return bulk
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

    On upstream/HTTP failure this tool does NOT raise — it returns a dict with a
    single 'error' key (a message plus a "fall back to SPARQL" hint) instead of
    the usual {'total_count', 'results'} shape. Check for 'error' before reading
    'results'.
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
    if "error" in bulk:
        # Propagate the upstream-failure payload rather than silently
        # collapsing it into an empty {'total_count': 0, 'results': []}.
        return bulk
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

    Returns: PubChem Compound ID in the JSON format. On upstream/HTTP failure
        this tool does NOT raise — it returns a plain string beginning with
        "Error:" (not JSON). Check for that prefix before parsing.
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

    Returns: Compound attributes in the JSON format. On upstream/HTTP failure
        this tool does NOT raise — it returns a plain string beginning with
        "Error:" (not JSON). Check for that prefix before parsing.
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
#
# PDBj /rest/newweb/search/{db} returns each hit as a positional array whose
# column meaning is fixed per database (verified live 2026-06). Rather than
# returning only {id: name}, we project the useful columns into named fields.
#
#   pdb: 0 id · 1 title · 2 authors · 3 citation · 4 journal · 5 year ·
#        6 volume · 7 pmid · 8 doi · 9 release · 10 deposit · 11 modify ·
#        12 method · 13 resolution · 14 ligands
#   cc:  0 code · 1 name · 2 formula · 3 smiles · 4 inchi ·
#        5 systematic_name · 6 release · 7 modified · 8 iupac_name · 9 synonym
#        (cols 3/4/5 are ';'-strings for free-text query, JSON lists for
#        structured-filter searches — normalized in _project_cc_row)
#   prd: 0 id · 1 (empty) · 2 release · 3 modified · 4 name · 5 formula ·
#        6 description

# Friendly aliases for PDBj's numeric experimental-method codes (1–15).
_PDB_METHOD_CODES = {
    "xray": 1,
    "neutron": 2,
    "fiber": 3,
    "electron-crystallography": 4,
    "em": 5,  # cryo-EM / electron microscopy
    "nmr": 6,  # solution NMR
    "solid-state-nmr": 7,
}

# PDBj uses a large float sentinel in the resolution column for entries that
# have no resolution (e.g. NMR). Real resolutions are well under 1000 Å.
_PDB_RES_SENTINEL_FLOOR = 1000


def _project_pdb_row(row: list) -> dict:
    g = lambda i: row[i] if len(row) > i else None
    res = g(13)
    if isinstance(res, (int, float)) and res >= _PDB_RES_SENTINEL_FLOOR:
        res = None
    return {
        "id": g(0),
        "title": g(1),
        "method": g(12),
        "resolution": res,
        "ligands": g(14) or None,
        "year": g(5) or None,
        "pmid": g(7) or None,
        "doi": g(8) or None,
    }


def _cc_smiles_list(val) -> list:
    """Normalize PDBj's polymorphic cc SMILES column to list[str].

    Free-text `query` searches return it as a ';'-separated string; structured
    filter searches (formula/smiles) return it as a JSON list. Handle both.
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [s for s in val if s]
    return [s for s in str(val).split(";") if s]


def _cc_first(val):
    """Return a single scalar from a cc column that PDBj may deliver as a
    scalar string (free-text query) or a one-element list (filter query)."""
    if isinstance(val, list):
        return val[0] if val else None
    return val or None


def _project_cc_row(row: list) -> dict:
    g = lambda i: row[i] if len(row) > i else None
    return {
        "id": g(0),
        "name": g(1),
        "formula": g(2),
        "smiles": _cc_smiles_list(g(3)),
        "inchi": _cc_first(g(4)),
        "iupac_name": g(8) or None,
    }


def _project_prd_row(row: list) -> dict:
    g = lambda i: row[i] if len(row) > i else None
    return {
        "id": g(0),
        "name": g(4),
        "formula": g(5) or None,
        "description": g(6) or None,
    }


_PDB_ROW_PROJECTORS = {
    "pdb": _project_pdb_row,
    "cc": _project_cc_row,
    "prd": _project_prd_row,
}


@mcp.tool()
async def search_pdb_entity(
    db: Literal["pdb", "cc", "prd"],
    query: str = "",
    limit: Annotated[int, Field(ge=0, le=500)] = 20,
    offset: Annotated[int, Field(ge=0)] = 0,
    method: Literal[
        "",
        "xray",
        "nmr",
        "em",
        "neutron",
        "fiber",
        "electron-crystallography",
        "solid-state-nmr",
    ] = "",
    res_min: Annotated[float, Field(ge=0)] | None = None,
    res_max: Annotated[float, Field(ge=0)] | None = None,
    source: str = "",
    ligand: str = "",
    formula: str = "",
    smiles: str = "",
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> str:
    """
    Search PDBj for structures, chemical components, or BIRD molecules.

    Returns rich, named fields per hit (not just the title) — for `pdb`,
    each result carries the experimental method, resolution, bound ligands,
    and citation; for `cc`, the formula, SMILES, and InChI.

    Args:
        db (str): The database to search in. Allowed values are:
            - "pdb" (Protein Data Bank, macromolecular structures)
            - "cc" (Chemical Component Dictionary, ligands / small molecules)
            - "prd" (BIRD, Biologically Interesting Reference Molecule
              Dictionary, mostly peptides).
        query (str): Free-text keywords. May be empty when at least one
            structured filter is supplied. Accepts aliases: `search`, `term`,
            `keyword`, `keywords`, `search_term`, `name`. If both `query` and
            an alias are given with different values, this raises ValueError (pass only one).
        limit (int): Max results to return, in [0, 500]. Default 20.
        offset (int): Number of leading results to skip (server-side
            pagination). Default 0.

        Structured filters for db="pdb" (combine freely with `query`):
            method (str): Experimental method — one of "xray", "nmr", "em"
                (cryo-EM), "neutron", "fiber", "electron-crystallography",
                "solid-state-nmr".
            res_min / res_max (float): Resolution bounds in Å.
            source (str): Source organism (e.g. "Homo sapiens").
            ligand (str): Keep entries whose ligand list contains this string.
                Matching is a substring, not an exact CCD code — `ATP` also
                matches `dATP`. Pass the exact ligand name for precision.

        Structured filters for db="cc" (chemical search):
            formula (str): Molecular formula in the canonical spaced,
                element-counted form (e.g. "C8 H10 N4 O2"). The unspaced form
                ("C8H10N4O2") is not matched by PDBj.
            smiles (str): SMILES substructure query.

    Note:
        PDBj search hits multiple fields (title, authors, keywords,
        citation metadata), not just the title — an entry can match even
        when its title does not contain the query. Verify relevance against
        the returned fields. Filters that don't apply to the chosen `db`
        are ignored.

    Returns:
        str: JSON string `{"total": int | null, "results": [ {…fields…} ]}`.
            `total` is `null` when PDBj does not provide a count (typical for
            structured-filter searches) — it is *not* zero and does not mean
            "no results"; consult `results` directly in that case.
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

    params: dict = {"query": query, "limit": limit, "offset": offset}
    if db == "pdb":
        if method:
            # `method` is enum-constrained at the schema layer, but guard the
            # lookup so a Literal/dict drift (or a direct call) gives a clear
            # error instead of a bare KeyError.
            code = _PDB_METHOD_CODES.get(method)
            if code is None:
                raise ValueError(
                    f"Unknown method {method!r}. Valid values: "
                    f"{sorted(_PDB_METHOD_CODES)}."
                )
            params["method"] = code
        if res_min is not None:
            params["res_min"] = res_min
        if res_max is not None:
            params["res_max"] = res_max
        if source:
            params["source"] = source
        if ligand:
            params["ligand"] = ligand
    elif db == "cc":
        if formula:
            params["formula"] = formula
        if smiles:
            params["smiles"] = smiles

    # A search needs either free text or at least one structured filter.
    has_filter = any(
        k not in ("query", "limit", "offset") for k in params
    )
    if not query and not has_filter:
        raise ValueError(
            "Missing search criteria. Pass `query` (or an alias: search, term, "
            "keyword, keywords, search_term, name) and/or a structured filter "
            "(pdb: method/res_min/res_max/source/ligand; cc: formula/smiles)."
        )

    project = _PDB_ROW_PROJECTORS[db]
    try:
        response = await _pdbj_client.get(
            f"/rest/newweb/search/{db}", params=params
        )
        raise_for_status_with_body(response, context="PDBj search")
        payload = response.json()
        raw_total = payload.get("total", 0)
        try:
            total_results = int(raw_total)
        except (TypeError, ValueError):
            total_results = 0
        # PDBj returns -1 ("not computed") for structured-filter searches, even
        # alongside real rows. Surface that as null rather than a nonsensical
        # negative count.
        if total_results < 0:
            total_results = None
        # `limit`/`offset` are honored server-side; the slice is a safety belt.
        result_list = [
            project(entry) for entry in payload.get("results", [])[:limit]
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
        str: A JSON-formatted string containing the search results. On
        upstream/HTTP failure this tool does NOT raise — it returns a plain
        string beginning with "Error:" (not JSON). Check for that prefix before
        parsing.
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
#
# Canonical Reactome search `types` facet values (the API is case-sensitive and
# silently ignores unknown/mis-cased values, returning UNFILTERED results).
# Verified against /ContentService/search/facet on 2026-06-24. Keyed by
# lowercase for case-insensitive validation -> canonical form.
_REACTOME_TYPES = {
    t.lower(): t
    for t in (
        "Complex", "Protein", "Reaction", "Set", "Pathway",
        "Genes and Transcripts", "Chemical Compound", "DNA Sequence",
        "Polymer", "Drug", "RNA Sequence", "OtherEntity", "Cell",
    )
}


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
) -> str:
    """Search the Reactome knowledgebase using keyword search.

    Args:
        query: The search query string (e.g., "apoptosis", "TP53", "cell cycle").
            Accepts aliases: `search`, `term`, `keyword`, `keywords`,
            `search_term`, `name`. If both `query` and an alias are given with
            different values, this raises ValueError (pass only one).
        species: Filter by species. Must be the scientific name
            (e.g., "Homo sapiens", "Mus musculus"). Numeric NCBI taxon
            IDs like "9606" are rejected here (this tool raises ValueError)
            because the Reactome API silently ignores them AND can
            degrade co-occurring filters (e.g. `types`). Accepts a
            single string or a list of strings.
        types: Filter by entity type(s). Accepts a single string (e.g.,
            "Pathway") or a list (e.g., ["Pathway", "Reaction", "Complex"]).
            Validated case-insensitively against the Reactome type enum;
            unknown values raise ValueError (the API would otherwise silently
            ignore them and return unfiltered results). Valid values:
            Complex, Protein, Reaction, Set, Pathway, Genes and Transcripts,
            Chemical Compound, DNA Sequence, Polymer, Drug, RNA Sequence,
            OtherEntity, Cell.
        rows: Per-category result cap. Reactome clusters results by
            entity type (`cluster=true`), so `rows=30` returns up to 30
            hits *per type*, not 30 hits total. To bound the total,
            constrain `types` to a single value.

    Returns:
        JSON string: a bare array of results, each with 'id', 'name', and
        'type' fields. Empty and non-empty results share the same shape.
        Example: '[{"id": "R-HSA-109581", "name": "Apoptosis",
        "type": "Pathway"}]'

    Raises:
        ValueError: If `query` is blank or `types`/`species` are invalid.
    """
    query = _resolve_query_alias(
        query,
        search=search,
        term=term,
        keyword=keyword,
        keywords=keywords,
        search_term=search_term,
        name=name,
    ).strip()
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
        types_list = [types] if isinstance(types, str) else list(types)
        normalized, unknown = [], []
        for t in types_list:
            canon = _REACTOME_TYPES.get(t.strip().lower())
            (normalized if canon else unknown).append(canon or t)
        if unknown:
            raise ValueError(
                f"Unknown Reactome type(s): {unknown}. The search API silently "
                "ignores invalid/mis-cased types and returns UNFILTERED "
                f"results. Valid values (case-insensitive): "
                f"{sorted(set(_REACTOME_TYPES.values()))}."
            )
        params["types"] = ",".join(normalized)

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
        return json.dumps([{
            "error": (
                f"Reactome REST API request failed ({type(e).__name__}: "
                f"{e}). Reactome's search endpoint can be slow or briefly "
                "unavailable. Retry once after a brief delay. If it keeps "
                "failing, fall back to SPARQL: "
                "run_sparql(database='reactome', sparql_query=...)."
            )
        }])

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

    return json.dumps(results)


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
) -> str:
    """
    Search Rhea database for biochemical reactions using keyword search.

    Args:
        query (str): Search query string. Examples:
                    - "ATP" - find reactions involving ATP
                    - "glucose" - find reactions with glucose
                    - "uniprot:*" - reactions with UniProt annotations
                    - "" - retrieve all reactions
                    Accepts aliases: `search`, `term`, `keyword`, `keywords`,
                    `search_term`, `name`. If both `query` and an alias are
                    given with different values, this raises ValueError (pass only one).
        limit (int, optional): Maximum number of results. Defaults to 100.
            Must be >= 0; a negative limit is rejected (it would make Rhea
            return the entire database).

    Returns:
        JSON string: a bare array of reactions, each with 'rhea_id' and
        'equation'. Empty and non-empty results share the same shape.
        Example: '[{"rhea_id": "RHEA:10000", "equation": "ATP + H2O = ..."}]'

    Raises:
        ValueError: If `limit` is negative.
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
    ).strip()

    if limit is not None and limit < 0:
        raise ValueError(
            f"limit must be >= 0 (got {limit}). A negative limit makes Rhea "
            "return the entire result set (thousands of reactions)."
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
            return json.dumps([])

        # First line is header, skip it
        results = []
        for line in lines[1:]:
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 2:
                    results.append({"rhea_id": parts[0], "equation": parts[1]})

        return json.dumps(results)

    except (httpx.HTTPError, ValueError) as e:
        logger.warning(f"Rhea search failed: {type(e).__name__}: {e}")
        return json.dumps([{
            "error": (
                f"Rhea REST API request failed ({type(e).__name__}: {e}). "
                "Usually transient — retry once after a brief delay. If it "
                "keeps failing, fall back to SPARQL: "
                "run_sparql(database='rhea', sparql_query=...)."
            )
        }])
