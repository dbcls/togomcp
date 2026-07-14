import asyncio
import json
import re
from typing import Annotated, Literal

import httpx
from pydantic import Field

from .server import *

# Shared httpx clients for connection reuse
_uniprot_client = httpx.AsyncClient(base_url="https://rest.uniprot.org", timeout=30.0)
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


# ---------------------------------------------------------------------------
# Shared REST plumbing
#
# Every REST-wrapper tool below fronts a flaky third-party HTTP API (EBI is
# ~1/3 flaky; the others have occasional 5xx/timeout blips). They share one
# resilience story: retry transient 5xx/read-timeout failures with a short
# linear backoff, treat 4xx as terminal, collapse HTML error pages to a short
# snippet, and NEVER raise for an HTTP/transport error — degrade to an
# `error`-carrying payload with a "fall back to SPARQL" hint (the module's
# REST-wrapper contract). `_rest_get` centralizes that; each tool keeps its
# own success-body handling (`.text` vs `.json()`) and error-envelope shape
# (plain "Error:" string / `{"error"}` dict / bare `[{"error"}]` array).
# ---------------------------------------------------------------------------

_REST_MAX_ATTEMPTS = 3  # 1 initial try + 2 retries
_REST_BACKOFF_BASE = 1.0  # seconds; nth retry waits base*n (patched to 0 in tests)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str, max_len: int = 200) -> str:
    """Collapse an HTML error page into a short plain-text snippet.

    Upstream APIs return full HTML documents (doctype, <script>/<style> blocks,
    favicon links) on failure — hundreds of tokens of noise with no diagnostic
    value. Drop scripts/styles wholesale, strip remaining tags, collapse
    whitespace, and truncate.
    """
    text = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "…"
    return text


class _RestError:
    """Terminal outcome of `_rest_get`, carrying a clean, short message.

    Distinguishable from a successful ``httpx.Response`` via ``isinstance`` so
    callers branch on the outcome without an exception crossing the
    REST-wrapper boundary.
    """

    __slots__ = ("message", "status_code", "body")

    def __init__(
        self, message: str, status_code: int | None = None, body: str | None = None
    ) -> None:
        self.message = message
        # HTTP status for an error response; None for a transport/timeout error.
        # Lets a caller special-case a status (e.g. Reactome's 404 = "no matches").
        self.status_code = status_code
        # Raw (untruncated, un-stripped) response body for an HTTP-status error,
        # capped for memory; None for a transport error. `message` is the short
        # loggable form — `body` is for callers that must inspect it structurally
        # (e.g. parse a JSON error to tell "no matches" from a broken endpoint).
        self.body = body


async def _rest_get(
    client: httpx.AsyncClient,
    path: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    context: str,
) -> "httpx.Response | _RestError":
    """GET ``path``, retrying transient 5xx/timeout failures with linear backoff.

    Returns the successful ``httpx.Response`` (2xx). On terminal failure returns
    ``_RestError(<clean short message>)`` — it never raises for HTTP/transport
    errors. 4xx client errors are terminal (no retry); 5xx and read timeouts are
    retried up to ``_REST_MAX_ATTEMPTS`` times. HTML error bodies are stripped to
    a short snippet.
    """
    last_error = "unknown error"
    last_status: int | None = None
    last_body: str | None = None
    for attempt in range(_REST_MAX_ATTEMPTS):
        last = attempt == _REST_MAX_ATTEMPTS - 1
        try:
            response = await client.get(path, params=params, headers=headers)
        except httpx.HTTPError as e:  # includes TimeoutException
            last_error = f"{type(e).__name__}: {e}"
            last_status, last_body = None, None
            logger.warning(f"{context} attempt {attempt + 1} failed: {last_error}")
            if last:
                break
            await asyncio.sleep(_REST_BACKOFF_BASE * (attempt + 1))
            continue
        if response.is_success:
            return response
        last_status = response.status_code
        if 500 <= response.status_code < 600 and not last:
            last_error = f"HTTP {response.status_code}"
            logger.warning(f"{context} attempt {attempt + 1}: {last_error}, retrying")
            await asyncio.sleep(_REST_BACKOFF_BASE * (attempt + 1))
            continue
        # Terminal: a 4xx, or a 5xx after retries are exhausted.
        last_error = f"HTTP {response.status_code}: {_strip_html(response.text)}"
        last_body = response.text[:4096]  # raw body for structural inspection
        logger.warning(f"{context} failed (terminal): {last_error}")
        break
    return _RestError(last_error, last_status, last_body)


def _rest_fail_msg(subject: str, detail: str, database: str) -> str:
    """Shared "REST API failed → retry already done → fall back to SPARQL" hint.

    ``subject`` names the failed operation (e.g. "UniProt REST API request");
    ``database`` is the RDF-Portal key for the SPARQL fallback suggestion.
    """
    return (
        f"{subject} failed ({detail}). Transient errors were already retried "
        "automatically. If it keeps failing, fall back to SPARQL: "
        f"run_sparql(database='{database}', sparql_query=...)."
    )


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
    resp = await _rest_get(
        _uniprot_client, "/uniprotkb/search", params=params, context="UniProt search"
    )
    if isinstance(resp, _RestError):
        logger.warning(f"UniProt search failed: {resp.message}")
        return "Error: " + _rest_fail_msg(
            "UniProt REST API request", resp.message, "uniprot"
        )
    return resp.text


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
    resp = await _rest_get(_pubchem_client, url, context="PubChem CID lookup")
    if isinstance(resp, _RestError):
        logger.warning(f"PubChem CID lookup failed for {compound_name!r}: {resp.message}")
        return "Error: " + _rest_fail_msg(
            f"PubChem CID lookup for {compound_name!r}", resp.message, "pubchem"
        )
    return resp.text


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
    resp = await _rest_get(
        _pubchem_client, url, params=params, context="PubChem compound attributes"
    )
    if isinstance(resp, _RestError):
        logger.warning(
            f"PubChem compound-attributes fetch failed for "
            f"{pubchem_compound_id!r}: {resp.message}"
        )
        return "Error: " + _rest_fail_msg(
            f"PubChem compound-attributes fetch for {pubchem_compound_id!r}",
            resp.message,
            "pubchem",
        )
    return resp.text


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
    resp = await _rest_get(
        _pdbj_client, f"/rest/newweb/search/{db}", params=params, context="PDBj search"
    )
    if isinstance(resp, _RestError):
        logger.warning(f"PDBj search failed for db={db!r} query={query!r}: {resp.message}")
        return json.dumps(
            {"error": _rest_fail_msg("PDBj REST API request", resp.message, "pdb")}
        )
    try:
        payload = resp.json()
    except ValueError as e:
        detail = f"malformed JSON body: {_strip_html(resp.text)}"
        logger.warning(f"PDBj search returned non-JSON for db={db!r}: {e}")
        return json.dumps(
            {"error": _rest_fail_msg("PDBj REST API request", detail, "pdb")}
        )
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
    result_list = [project(entry) for entry in payload.get("results", [])[:limit]]
    return json.dumps({"total": total_results, "results": result_list})


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
    resp = await _rest_get(
        _mesh_client, "/mesh/lookup/descriptor", params=params,
        context="MeSH descriptor lookup",
    )
    if isinstance(resp, _RestError):
        logger.warning(f"MeSH descriptor lookup failed for {query!r}: {resp.message}")
        return "Error: " + _rest_fail_msg(
            "MeSH descriptor lookup", resp.message, "mesh"
        )
    return resp.text


# DB: Reactome
#
# The ContentService Solr search silently RELAXES filters that would yield zero
# results and returns UNFILTERED rows instead (its "helpful" default; the server
# `Force filters` param that disables it has a space in its name that breaks over
# HTTP). Confirmed live 2026-07-14: query="apoptosis" + a nonexistent species
# returned 1058 cross-species matches. So this wrapper does NOT trust the server
# to honor `species`/`types` — it re-applies both filters CLIENT-SIDE against the
# fields every result already carries (`species` array, `type` == the facet
# value), which guarantees the contract regardless of server relaxation. `types`
# is still validated up front (a mis-cased value would also silently relax).
#
# Canonical Reactome search `types` facet values (case-sensitive on the server).
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

# Canonical Reactome species (displayName), fetched live 2026-07-14 from
# /ContentService/data/species/all (96 species). Keyed by lowercase for
# case-insensitive validation -> canonical casing. The server-side species
# filter is case-SENSITIVE; a mis-cased value is silently ignored and the API
# returns UNFILTERED results, so we normalize to canonical casing before
# dispatch (mirrors the _REACTOME_TYPES guard).
_REACTOME_SPECIES = {
    s.lower(): s
    for s in (
        'Alphapapillomavirus 9', 'Arenicola marina', 'Bacillus anthracis', 'Bos taurus',
        'Caenorhabditis elegans', 'Candida albicans', 'Canis familiaris', 'Cavia porcellus',
        'Cercopithecus aethiops', 'Chlamydia trachomatis', 'Chlorocebus sabaeus',
        'Clostridium botulinum', 'Clostridium perfringens', 'Clostridium tetani',
        'Corynephage beta', 'Cowpox virus', 'Cricetulus griseus', 'Crithidia fasciculata',
        'Danio rerio', 'Dengue virus', 'Dengue virus type 2', 'Dictyostelium discoideum',
        'Drosophila melanogaster', 'Escherichia coli', 'Escherichia coli O127:H6',
        'Escherichia coli O157:H7', 'Escherichia coli O6:K15:H31',
        'Escherichia coli O78:H11', 'Felis catus', 'Gallus gallus', 'Hepatitis B virus',
        'Hepatitis C Virus', 'Hepatitis C virus genotype 2a',
        'Hepatitis C virus subtype 1a', 'Homarus americanus', 'Homo sapiens',
        'Human SARS coronavirus', 'Human alphaherpesvirus 2', 'Human cytomegalovirus',
        'Human gammaherpesvirus 4', 'Human herpesvirus 1', 'Human herpesvirus 8',
        'Human immunodeficiency virus 1', 'Human papillomavirus type 16',
        'Human papillomavirus type 18', 'Human respiratory syncytial virus A',
        'Infectious bronchitis virus', 'Influenza A virus', 'Klebsiella pneumoniae',
        'Legionella pneumophila', 'Leishmania major', 'Leishmania mexicana',
        'Listeria monocytogenes', 'Listeria monocytogenes serotype 1/2a',
        'Listeria monocytogenes serovar 1/2a', 'Macaca mulatta', 'Measles virus',
        'Meleagris gallopavo', 'Molluscum contagiosum virus',
        'Molluscum contagiosum virus subtype 1', 'Moloney murine leukemia virus',
        'Mus musculus', 'Mycobacterium tuberculosis', 'Mycobacterium tuberculosis H37Rv',
        'Neisseria gonorrhoeae', 'Neisseria meningitidis',
        'Neisseria meningitidis serogroup B', 'Oryctolagus cuniculus', 'Oryza sativa',
        'Ovis aries', 'Penicillium chrysogenum', 'Plasmodium falciparum',
        'Rattus norvegicus', 'Respiratory syncytial virus', 'Rotavirus', 'Rotavirus A',
        'Saccharomyces cerevisiae', 'Salmonella enterica', 'Salmonella typhimurium',
        'Schizosaccharomyces pombe', 'Sendai virus',
        'Severe acute respiratory syndrome coronavirus 2', 'Shigella flexneri',
        'Sindbis virus', 'Staphylococcus aureus', 'Sus scrofa',
        'Tick-borne encephalitis virus', 'Toxoplasma gondii', 'Triticum aestivum',
        'Vaccinia virus', 'Vesicular stomatitis virus', 'Vigna radiata',
        'Vigna radiata var. radiata', 'West Nile virus', 'Xenopus laevis',
        'Xenopus tropicalis',
    )
}

# Reactome wraps matched substrings in <span class="highlighting">…</span> in
# `name` and `summation`; strip the markup (both open and close tags).
_REACTOME_HL_RE = re.compile(r"</?span[^>]*>")


def _reactome_clean(text: str) -> str:
    """Strip Reactome's search-highlighting <span> markup and trim."""
    return _REACTOME_HL_RE.sub("", text or "").strip()


def _reactome_is_no_match(body: str | None) -> bool:
    """True iff a 404 body is Reactome's "no entries found" signal.

    Reactome returns HTTP 404 both for "nothing matched this query" (an EMPTY
    result set) and for a genuinely broken request (a renamed endpoint path, an
    API-version migration, …). Only the former should map to empty results;
    everything else must surface as an error, or the tool would look healthy
    while silently returning nothing for every query. So key NARROWLY on the
    structured body — reason == "NOT_FOUND" AND the message text — not on the
    404 status alone. A non-JSON / differently-shaped 404 body returns False
    (→ genuine error).
    """
    if not body:
        return False
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return False
    if not isinstance(payload, dict) or payload.get("reason") != "NOT_FOUND":
        return False
    messages = payload.get("messages") or []
    return (
        bool(messages)
        and isinstance(messages[0], str)
        and messages[0].startswith("No entries found for query")
    )


@mcp.tool()
async def search_reactome_entity(
    query: str = "",
    species: str | list[str] | None = None,
    types: str | list[str] | None = None,
    limit: int | None = None,
    include_summation: bool = False,
    rows: int | None = None,
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """Search the Reactome pathway knowledgebase by keyword (name / fuzzy match).

    Resolves a term (pathway / reaction / protein / complex / small-molecule
    name) to Reactome stable IDs. Matching is keyword/fuzzy — UNLIKE the
    exact-match ChEMBL search tools, so expect ranked, approximate hits.

    RETURNS a dict {'total_count', 'has_more', 'results'} — NOT a bare list.
    `total_count` is the number of records RETURNED (capped by `limit`);
    `has_more` is true if more matched beyond the cap. Each result carries
    'id' (stable Reactome stId, e.g. "R-HSA-109581"), 'name', 'type' (facet
    type), 'exactType' (specific BioPAX-ish class), 'species' (list), and — only
    when include_summation=True — 'summation' (≤240-char description). On
    upstream failure returns {'error': ...} instead — CHECK FOR 'error' BEFORE
    READING 'results'.

    `species` and `types` are validated case-INSENSITIVELY against Reactome's
    controlled vocabularies and normalized to canonical casing before dispatch:
    the server-side filter is case-SENSITIVE and silently ignores a mis-cased
    value (returning UNFILTERED results), so a mis-cased species used to lose
    most hits. An unrecognized species/type now RAISES rather than silently
    returning the wrong rows.

    Args:
        query: Search string, e.g. "apoptosis", "TP53", "cell cycle". Accepts
            aliases: `search`, `term`, `keyword`, `keywords`, `search_term`,
            `name` (supplying two different values raises ValueError).
        species: Filter by species scientific name, case-insensitive
            (e.g. "Homo sapiens", "homo sapiens", "Mus musculus"). A single
            string or a list. Unrecognized names raise ValueError (96 species
            available; see reactome.org/ContentService/data/species/all).
        types: Filter by entity type(s), case-insensitive; a string or list.
            Valid values: Cell, Chemical Compound, Complex, DNA Sequence, Drug,
            Genes and Transcripts, OtherEntity, Pathway, Polymer, Protein,
            RNA Sequence, Reaction, Set. Unknown values raise ValueError.
        limit: Maximum number of records returned overall (default 25). A true
            total cap, not per-type.
        include_summation: When True, add a ≤240-char 'summation' description to
            each record. Default False keeps the payload small (a broad default
            search is ~hundreds of tokens instead of thousands).
        rows: DEPRECATED alias for `limit` (the old name meant per-type rows).
            Passing both `limit` and `rows` with different values raises.

    Returns:
        dict: {'total_count': int, 'has_more': bool, 'results': [ ... ]} on
        success, or {'error': str} on upstream/HTTP failure.

    Raises:
        ValueError: If `query` is blank or `types`/`species` are invalid.
    """
    # `rows` is a deprecated alias for `limit` (both mean the overall cap).
    # Supplying both with different values is a caller error — raise, mirroring
    # the query-alias conflict check, rather than silently picking one.
    if limit is not None and rows is not None and limit != rows:
        raise ValueError(
            f"Pass only one of `limit` and `rows` (aliases for the overall "
            f"result cap); got limit={limit}, rows={rows}."
        )
    limit = limit if limit is not None else (rows if rows is not None else 25)
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
    # Over-fetch by one (per type) so has_more can be detected after the overall
    # cap; Reactome's `rows` is per-type, so this is an upper bound, not a total.
    params = {"query": query, "cluster": "true", "start": 0, "rows": int(limit) + 1}

    # `want_*` are the lowercased filter sets re-applied client-side after the
    # response comes back (belt-and-suspenders: the server also silently relaxes
    # a zero-yield filter and returns unrelated rows).
    want_species: set[str] | None = None
    want_types: set[str] | None = None

    if species:
        species_list = [species] if isinstance(species, str) else list(species)
        normalized_sp, unknown_sp = [], []
        for s in species_list:
            canon = _REACTOME_SPECIES.get(s.strip().lower())
            (normalized_sp if canon else unknown_sp).append(canon or s)
        if unknown_sp:
            raise ValueError(
                f"Unknown Reactome species: {unknown_sp}. The search API is "
                "case-SENSITIVE and silently ignores an unrecognized or mis-cased "
                "species, returning UNFILTERED results. Pass the exact scientific "
                "name (matched case-insensitively here), e.g. 'Homo sapiens', "
                "'Mus musculus', 'Rattus norvegicus', 'Danio rerio', "
                "'Saccharomyces cerevisiae'. "
                f"{len(_REACTOME_SPECIES)} species available; see "
                "reactome.org/ContentService/data/species/all for the full list."
            )
        # Canonical casing so the server-side filter actually engages.
        params["species"] = ",".join(normalized_sp)
        want_species = {s.lower() for s in normalized_sp}
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
        want_types = {t.lower() for t in normalized}

    # Make API call
    resp = await _rest_get(
        _reactome_client, "/ContentService/search/query", params=params,
        headers={"Accept": "application/json"}, context="Reactome search",
    )
    if isinstance(resp, _RestError):
        # Reactome signals "nothing matched" with HTTP 404 (reason NOT_FOUND,
        # message "No entries found for query: …"). That is an EMPTY result set,
        # not an upstream failure — return the empty envelope so a caller doesn't
        # read `error` and conclude the endpoint broke. Key narrowly on the
        # structured body (see _reactome_is_no_match): any OTHER 404 — a renamed
        # path, an API migration — stays a genuine error rather than silently
        # reporting "no results" for every query.
        if resp.status_code == 404 and _reactome_is_no_match(resp.body):
            return {"total_count": 0, "has_more": False, "results": []}
        logger.warning(f"Reactome search failed: {resp.message}")
        return {"error": _rest_fail_msg("Reactome REST API request", resp.message, "reactome")}
    try:
        data = resp.json()
    except ValueError as e:
        detail = f"malformed JSON body: {_strip_html(resp.text)}"
        logger.warning(f"Reactome search returned non-JSON: {e}")
        return {"error": _rest_fail_msg("Reactome REST API request", detail, "reactome")}

    # Extract results, re-applying species/type filters client-side (the server
    # silently relaxes zero-yield filters — see the module comment above).
    results = []
    for result_group in data.get("results", []):
        for entry in result_group.get("entries", []):
            entry_type = entry.get("type", "Unknown")
            if want_types is not None and entry_type.lower() not in want_types:
                continue
            entry_species = entry.get("species") or []
            if isinstance(entry_species, str):
                entry_species = [entry_species]
            if want_species is not None and not (
                want_species & {s.lower() for s in entry_species}
            ):
                continue

            record = {
                "id": entry.get("stId", entry.get("id", "N/A")),
                "name": _reactome_clean(entry.get("name", "N/A")),
                "type": entry_type,
                "exactType": entry.get("exactType", entry_type),
                "species": entry_species,
            }
            if include_summation:
                # max_len=239 so the truncated form (239 chars + "…") is ≤240,
                # matching the docstring's "≤240-char" promise.
                record["summation"] = _strip_html(entry.get("summation", ""), max_len=239)
            results.append(record)

    has_more = len(results) > int(limit)
    results = results[: int(limit)]
    return {"total_count": len(results), "has_more": has_more, "results": results}


# DB: RhEA
# The Rhea table endpoint (/rhea) exposes a fixed, documented set of columns
# (rhea-db.org/help/rest-api). This maps each valid column ID to the JSON key
# it becomes in the result, and doubles as the validation vocabulary: an
# UNKNOWN column is SILENTLY DROPPED by the server (HTTP 200, no error, just a
# narrower table) — the same silent-relaxation trap as Reactome's `types` — so
# we reject unknown columns up front rather than let a caller believe they
# requested EC numbers and receive none. Keys mirror the column ID with `-`
# collapsed to `_`; the parenthesised cross-reference columns get short aliases.
_RHEA_COLUMNS = {
    "rhea-id": "rhea_id",
    "equation": "equation",
    "chebi": "chebi",
    "chebi-id": "chebi_id",
    "ec": "ec",
    "uniprot": "uniprot",  # count of UniProtKB entries annotated with the reaction
    "go": "go",
    "pubmed": "pubmed",
    "reaction-xref(EcoCyc)": "xref_ecocyc",
    "reaction-xref(MetaCyc)": "xref_metacyc",
    "reaction-xref(KEGG)": "xref_kegg",
    "reaction-xref(Reactome)": "xref_reactome",
    "reaction-xref(M-CSA)": "xref_mcsa",
}
# Lowercase → canonical, so `columns` can be matched case-INSENSITIVELY (the
# API's own filter is case-sensitive, but there's no reason to make the caller
# pay for that; we normalize to canonical casing before dispatch). Mirrors the
# case-insensitive handling of Reactome's `species`/`types`.
_RHEA_COLUMNS_LC = {col.lower(): col for col in _RHEA_COLUMNS}
# Hard ceiling on `limit`. Rhea has ~18k+ reactions and no server-side cap, so
# an unbounded limit (e.g. 20000) can return a six-figure-token payload that
# blows the context window. 500 is generous for any real search.
_RHEA_MAX_LIMIT = 500

# A `chebi:`-scoped term takes a BARE ChEBI number (chebi:17234). ChEBI IDs are
# canonically written WITH the prefix (CHEBI:17234) everywhere else — including
# this tool's own chebi_id output — so a caller naturally forms chebi:CHEBI:17234.
# The embedded ':' then breaks Rhea's Lucene parser and it returns an opaque
# HTTP 500. Collapse the redundant prefix to what the caller obviously meant.
_RHEA_CHEBI_DOUBLE_PREFIX_RE = re.compile(r"(?i)\bchebi:chebi:")


@mcp.tool()
async def search_rhea_entity(
    query: str = "",
    limit: int | None = 25,
    columns: str | list[str] = "rhea-id,equation",
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """
    Search the Rhea reaction database by keyword and return matching reactions.

    Matching is KEYWORD/FUZZY over reaction participants, equations, EC numbers,
    and cross-references — NOT exact-ID lookup. A term like "glucose" matches any
    reaction mentioning glucose. Field-scoped terms and wildcards are supported
    (e.g. `ec:1.1.1.1`, `chebi:17234`, `uniprot:*`). A `chebi:`-scoped term takes
    a BARE ChEBI number, not the `CHEBI:` prefix; a redundant `chebi:CHEBI:17234`
    is auto-corrected to `chebi:17234` (the prefixed form otherwise 500s).

    RETURNS a dict {'total_count', 'has_more', 'results'} — NOT a bare list.
    'total_count' is the number of reactions RETURNED (capped by `limit`, max
    500); 'has_more' is true if more matched beyond the cap. Each result carries
    the requested `columns` as snake_cased keys (e.g. 'rhea-id' → 'rhea_id',
    'chebi-id' → 'chebi_id'). On upstream failure returns {'error': ...} instead
    — CHECK FOR 'error' BEFORE READING 'results'.

    Args:
        query: Search string, e.g. "ATP", "glucose", "ec:1.1.1.1",
            "chebi:17234", "uniprot:*". REQUIRED — a blank query raises
            ValueError (it would otherwise dump an arbitrary slice of the whole
            database). Accepts aliases: `search`, `term`, `keyword`, `keywords`,
            `search_term`, `name` (supplying two different values raises ValueError).
        limit: Maximum number of reactions returned (default 25). Must be
            between 0 and 500; a negative limit or one above 500 raises
            ValueError. `has_more` in the result signals whether more matched.
        columns: Which fields to return, as a comma-separated string or a list
            of column IDs (case-INSENSITIVE). Default "rhea-id,equation". Each
            requested column becomes a key on every result row; hyphenated IDs
            are snake_cased in the output (e.g. `chebi-id` → `chebi_id`). The 13
            valid column IDs and their output keys:
              - chebi                   -> chebi        (';'-joined ChEBI names)
              - chebi-id                -> chebi_id     (';'-joined ChEBI ids)
              - ec                      -> ec           (';'-joined EC numbers)
              - equation                -> equation     (textual reaction equation)
              - go                      -> go           (GO id + label)
              - pubmed                  -> pubmed       (';'-joined PubMed ids)
              - reaction-xref(EcoCyc)   -> xref_ecocyc
              - reaction-xref(KEGG)     -> xref_kegg
              - reaction-xref(M-CSA)    -> xref_mcsa
              - reaction-xref(MetaCyc)  -> xref_metacyc
              - reaction-xref(Reactome) -> xref_reactome
              - rhea-id                 -> rhea_id      (e.g. RHEA:10000)
              - uniprot                 -> uniprot      (count of annotated UniProtKB entries)
            An unknown column raises ValueError — the API would otherwise
            silently drop it and return an unannounced narrower table.

    Returns:
        dict: {'total_count': int, 'has_more': bool, 'results': [ ... ]} on
        success, where each result is one reaction keyed by the requested
        columns. `total_count` is the number of rows returned (capped by
        `limit`); `has_more` is true if more reactions matched beyond the cap.
        On upstream/HTTP failure returns {'error': str} instead — CHECK FOR
        'error' BEFORE READING 'results'.

    Raises:
        ValueError: If `query` is blank, `limit` is out of range, or `columns`
            names an unknown field.
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
    # Collapse a redundant `chebi:CHEBI:` prefix (see _RHEA_CHEBI_DOUBLE_PREFIX_RE)
    # so a canonically-formatted ChEBI ID doesn't trigger an opaque upstream 500.
    query = _RHEA_CHEBI_DOUBLE_PREFIX_RE.sub("chebi:", query)
    if not query:
        # A blank query makes Rhea return an arbitrary first slice of the whole
        # database (ordered by ID) — plausible-looking rows unrelated to any
        # search. Raise instead, matching the ChEMBL/Reactome guard.
        raise ValueError(
            "Missing search string. Pass it as `query` (canonical) or any of: "
            "search, term, keyword, keywords, search_term, name."
        )

    if limit is None:
        limit = 25
    if limit < 0 or limit > _RHEA_MAX_LIMIT:
        raise ValueError(
            f"limit must be between 0 and {_RHEA_MAX_LIMIT} (got {limit}). "
            "Rhea applies no server-side cap, so an unbounded limit can return "
            "a payload large enough to exhaust the context window."
        )

    # Normalize + validate columns case-insensitively (see _RHEA_COLUMNS_LC).
    # Reject unknowns rather than let the server silently drop them. Preserve
    # caller order and drop duplicates so the TSV columns line up positionally
    # with `col_ids`.
    if isinstance(columns, str):
        requested = [c.strip() for c in columns.split(",") if c.strip()]
    else:
        requested = [str(c).strip() for c in columns if str(c).strip()]
    col_ids, seen = [], set()
    for col in requested:
        canon = _RHEA_COLUMNS_LC.get(col.lower())
        if canon is None:
            raise ValueError(
                f"Unknown Rhea column {col!r}. The API silently drops invalid "
                "columns and returns a narrower table without warning. Valid "
                f"column IDs (case-insensitive): {sorted(_RHEA_COLUMNS)}."
            )
        if canon not in seen:
            seen.add(canon)
            col_ids.append(canon)
    if not col_ids:
        raise ValueError("columns must name at least one valid Rhea column.")

    # Over-fetch by one so has_more can be detected after truncating to `limit`.
    params = {
        "query": query,
        "columns": ",".join(col_ids),
        "format": "tsv",
        "limit": limit + 1,
    }

    resp = await _rest_get(_rhea_client, "/rhea", params=params, context="Rhea search")
    if isinstance(resp, _RestError):
        logger.warning(f"Rhea search failed: {resp.message}")
        return {"error": _rest_fail_msg("Rhea REST API request", resp.message, "rhea")}

    # Parse TSV. The header row carries display LABELS ("Reaction identifier"),
    # not column IDs, so we map by POSITION against the requested `col_ids`.
    # Values never contain tabs (multi-valued cells are ';'-joined), so a plain
    # tab split is safe; a trailing empty cell may be dropped, hence the guard.
    lines = resp.text.strip().split("\n")
    if len(lines) < 2:
        return {"total_count": 0, "has_more": False, "results": []}

    keys = [_RHEA_COLUMNS[c] for c in col_ids]
    results = []
    for line in lines[1:]:  # first line is the header
        if not line.strip():
            continue
        parts = line.split("\t")
        results.append(
            {key: (parts[i] if i < len(parts) else "") for i, key in enumerate(keys)}
        )

    has_more = len(results) > limit
    results = results[:limit]
    return {"total_count": len(results), "has_more": has_more, "results": results}
