import asyncio
import csv
import io
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
#
# Text → ChEMBL-ID resolution runs as SPARQL against the RDF Portal graph, NOT
# the EBI REST lexical index. Reasons: (1) the REST /search.json index is
# token-OR ranked and buries the intended entity below orthologs/ligands/synonym
# noise (EGFR → the receptor is only rank ~6; a protein-name query returns
# thousands); (2) EBI REST is ~1/3 flaky. The RDF graph resolves deterministically
# in one indexed query, returning label + organism + type. Synonyms/brands/gene
# symbols live on skos:altLabel (on the molecule, and on the target COMPONENT).
# REST is retained ONLY for chemical STRUCTURE search (SMILES/InChI/InChIKey →
# flexmatch/similarity/substructure), which needs ChEMBL's chemistry engine and
# cannot be expressed in SPARQL. Those REST helpers keep the retry/HTML-strip
# plumbing below; EBI REST is flaky (~1/3 of calls 500 or time out).
_CHEMBL_MAX_ATTEMPTS = 3  # 1 initial try + 2 retries
_CHEMBL_BACKOFF_BASE = 1.0  # seconds; nth retry waits base*n (patched to 0 in tests)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str, max_len: int = 200) -> str:
    """Collapse an HTML error page into a short plain-text snippet.

    EBI returns full HTML documents (doctype, <script>/<style> blocks, favicon
    links) on failure — hundreds of tokens of noise with no diagnostic value.
    Drop scripts/styles wholesale, strip remaining tags, collapse whitespace,
    and truncate.
    """
    text = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "…"
    return text


async def _chembl_get_json(path: str, params: dict, *, context: str) -> dict:
    """GET a ChEMBL JSON endpoint, retrying transient 5xx/timeout failures.

    Returns the parsed JSON on success. On terminal failure returns
    ``{"error": <clean message>}`` — it never raises for HTTP/transport
    errors (the module's REST-wrapper contract). 4xx client errors are
    terminal (no retry); 5xx and read timeouts are retried up to
    ``_CHEMBL_MAX_ATTEMPTS`` times with a short linear backoff. HTML error
    bodies are stripped to a short snippet.
    """
    last_error = "unknown error"
    for attempt in range(_CHEMBL_MAX_ATTEMPTS):
        last = attempt == _CHEMBL_MAX_ATTEMPTS - 1
        try:
            response = await _chembl_client.get(path, params=params)
        except httpx.HTTPError as e:  # includes TimeoutException
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(f"{context} attempt {attempt + 1} failed: {last_error}")
            if last:
                break
            await asyncio.sleep(_CHEMBL_BACKOFF_BASE * (attempt + 1))
            continue
        if response.is_success:
            try:
                return response.json()
            except (json.JSONDecodeError, ValueError):
                # 200 with a non-JSON body — an upstream anomaly. Degrade
                # gracefully rather than raising (REST-wrapper contract).
                last_error = f"malformed JSON body: {_strip_html(response.text)}"
                logger.warning(f"{context} failed (terminal): {last_error}")
                break
        if 500 <= response.status_code < 600 and not last:
            last_error = f"HTTP {response.status_code}"
            logger.warning(f"{context} attempt {attempt + 1}: {last_error}, retrying")
            await asyncio.sleep(_CHEMBL_BACKOFF_BASE * (attempt + 1))
            continue
        # Terminal: a 4xx, or a 5xx after retries are exhausted.
        last_error = f"HTTP {response.status_code}: {_strip_html(response.text)}"
        logger.warning(f"{context} failed (terminal): {last_error}")
        break
    return {
        "error": (
            f"ChEMBL REST API request failed ({last_error}). Transient errors "
            "were already retried automatically. If it keeps failing, fall back "
            "to SPARQL: run_sparql(database='chembl', sparql_query=...)."
        )
    }


# --- name/symbol → ID resolution over the RDF graph (skos:altLabel) ---

_CHEMBL_GRAPH = "http://rdf.ebi.ac.uk/dataset/chembl"
_CHEMBL_PREFIXES = (
    "PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>\n"
    "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"
)
# UniProt accession (canonical pattern). A target query matching this routes to
# the structured skos:exactMatch UniProt link instead of altLabel text search.
_UNIPROT_ACCESSION_RE = re.compile(
    r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$"
)


def _bif_and(text: str) -> str | None:
    """Build a ``bif:contains`` argument from arbitrary caller text.

    Tokenizes to alphanumeric runs, single-quotes each token, and joins with AND
    (e.g. ``5'-nucleotidase`` → ``'5' AND 'nucleotidase'``). This is robust where
    the raw forms make Virtuoso 500: a bare numeric token (``5``) or a
    multi-word/punctuated phrase breaks the free-text parser, but quoting every
    token does not. It is only a *prefilter* — the exact FILTER on the label
    guarantees precision — so dropping apostrophes/slashes/hyphens is safe.
    Returns ``None`` when there is no alphanumeric token to search on.
    """
    toks = re.findall(r"[a-z0-9]+", text.lower())
    if not toks:
        return None
    return " AND ".join(f"'{t}'" for t in toks)


def _sparql_literal(text: str) -> str:
    """Escape ``text`` for inclusion in a double-quoted SPARQL string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _altlabel_match_block(query: str) -> str | None:
    """WHERE-clause fragment matching ``?entity`` (or ?comp) by exact synonym.

    Binds ?alt via skos:altLabel FIRST (bif:contains needs its var bound), fast-
    prefilters with the text index, then FILTERs for the exact (case-insensitive)
    label. Caller supplies the ``?entity skos:altLabel ?alt`` subject. Returns
    None if the query has no searchable token.
    """
    bif = _bif_and(query)
    if bif is None:
        return None
    return (
        f'  ?alt bif:contains "{bif}" .\n'
        f'  FILTER(LCASE(STR(?alt)) = "{_sparql_literal(query.lower())}")'
    )


async def _run_chembl_sparql(query: str) -> list[dict] | dict:
    """Execute a ChEMBL SPARQL query, returning CSV rows as ``list[dict]``.

    On endpoint failure returns ``{"error": ...}`` (never raises) to preserve
    the module's REST-wrapper contract. ``execute_sparql`` returns CSV text.
    """
    try:
        csv_text = await execute_sparql(query, database="chembl")
    except (ValueError, httpx.HTTPError) as e:
        first = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
        logger.warning(f"ChEMBL SPARQL failed: {type(e).__name__}: {first}")
        return {
            "error": (
                f"ChEMBL SPARQL query failed ({first[:200]}). If this persists, "
                "run the query yourself via run_sparql(database='chembl', ...)."
            )
        }
    return list(csv.DictReader(io.StringIO(csv_text)))


# Structure-search routing for search_chembl_molecule.
# /molecule/search.json is a LEXICAL text index — a SMILES string matched
# against it returns meaningless name/synonym hits. Structure-shaped input must
# instead go to /molecule.json with a structure filter. The detector is
# deliberately conservative: a false positive misroutes a real drug name.
_INCHIKEY_RE = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")


def _looks_like_structure(query: str) -> str | None:
    """Classify ``query`` as a chemical structure string.

    Returns ``"inchi"``, ``"inchikey"``, or ``"smiles"`` when the input is
    structure-shaped, else ``None`` (route to the lexical name index).

    Conservative by design — a name misrouted to the structure endpoint
    returns nothing, so anything with whitespace (multi-word names) or without
    unambiguous structural punctuation stays on the lexical path. This means a
    bare-chain SMILES like ``CCO`` (ethanol) is NOT detected; that is the
    accepted trade-off for not misrouting drug names.
    """
    s = query.strip()
    if not s or " " in s:
        return None
    if s.startswith("InChI="):
        return "inchi"
    if _INCHIKEY_RE.match(s):
        return "inchikey"
    # SMILES: require structural punctuation that essentially never appears in a
    # drug name or accession (excludes "aspirin", "EGFR", "CHEMBL25", "P00533").
    if any(c in s for c in "=#()[]"):
        return "smiles"
    return None


async def _search_chembl_structure(kind: str, query: str, limit: int) -> dict:
    """Query the ``/molecule.json`` structure endpoint (SMILES/InChI/InChIKey).

    Returns the same ``{"page_meta", "molecules"}`` shape as the lexical search
    endpoint, so callers parse both identically.
    """
    field = {
        "smiles": "molecule_structures__canonical_smiles__flexmatch",
        "inchikey": "molecule_structures__standard_inchi_key",
        "inchi": "molecule_structures__standard_inchi",
    }[kind]
    filt = {field: query, "limit": limit}
    return await _chembl_get_json(
        "/chembl/api/data/molecule.json", filt, context="ChEMBL structure search"
    )


@mcp.tool()
async def search_chembl_id_lookup(
    query: Annotated[
        str, Field(description="The query string to search for.", default="")
    ] = "",
    limit: Annotated[
        int, Field(description="The maximum number of results to return.")
    ] = 20,
    entity_type: Annotated[
        str,
        Field(
            description=(
                "Optional filter: COMPOUND (molecules) or TARGET (proteins). "
                "Omit to search both."
            ),
            default="",
        ),
    ] = "",
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """
    Resolve a name/synonym to ChEMBL IDs across compounds AND targets.

    Cross-entity convenience wrapper: it runs the same exact-synonym SPARQL
    resolution as `search_chembl_molecule` and `search_chembl_target` and UNIONs
    the two, so one call covers "what ChEMBL entity is <text>?". Prefer the
    entity-specific tools when you already know you want a drug or a target — they
    carry the extra fields (organism/type). Only COMPOUND and TARGET are covered
    (the two synonym-rich entity kinds); for assays/documents/cell-lines/tissues,
    query SPARQL directly via run_sparql(database='chembl', ...).

    Matching is EXACT (case-insensitive) against skos:altLabel synonyms — brands,
    generic names, gene symbols — not fuzzy/substring. Fix typos in the query
    before calling.

    The search string can be passed as any of: `query` (canonical), `search`,
    `term`, `keyword`, `keywords`, `search_term`, or `name`.

    Returns:
        dict: {'total_count' (int, rows returned — capped by `limit`),
        'results' (list)}. Each result has 'chembl_id', 'entity_type'
        (COMPOUND / TARGET), and 'name' (the entity's rdfs:label).

        On endpoint failure this tool does NOT raise — it returns a dict with a
        single 'error' key instead. Check for 'error' before reading 'results'.
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
    et = entity_type.strip().upper() if entity_type else ""
    if et and et not in {"COMPOUND", "TARGET"}:
        raise ValueError(
            f"Invalid entity_type {entity_type!r}. Use COMPOUND or TARGET (this "
            "SPARQL-backed lookup covers those two synonym-rich kinds; for "
            "assays/documents/cell-lines/tissues query SPARQL directly)."
        )
    match = _altlabel_match_block(query)
    if match is None:
        return {"total_count": 0, "results": []}
    compound_branch = (
        "  {\n"
        "    ?e skos:altLabel ?alt .\n"
        f"{match}\n"
        "    ?e a cco:SmallMolecule ; cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        '    BIND("COMPOUND" AS ?entity_type)\n'
        "  }"
    )
    target_branch = (
        "  {\n"
        "    ?comp skos:altLabel ?alt .\n"
        f"{match}\n"
        "    ?e cco:hasTargetComponent ?comp ;\n"
        "       cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        '    BIND("TARGET" AS ?entity_type)\n'
        "  }"
    )
    if et == "COMPOUND":
        body = compound_branch
    elif et == "TARGET":
        body = target_branch
    else:
        body = f"{compound_branch}\n  UNION\n{target_branch}"
    sparql = (
        f"{_CHEMBL_PREFIXES}\n"
        f"SELECT DISTINCT ?chembl_id ?entity_type ?name FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"{body}\n"
        f"}} LIMIT {int(limit)}"
    )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    parsed_results = [
        {
            "chembl_id": r.get("chembl_id"),
            "entity_type": r.get("entity_type"),
            "name": r.get("name"),
        }
        for r in rows
    ]
    return {"total_count": len(parsed_results), "results": parsed_results}


@mcp.tool()
async def search_chembl_target(
    query: str = "",
    limit: int = 20,
    organism: str = "",
    target_type: str = "",
    search: str = "",
    term: str = "",
    keyword: str = "",
    keywords: str = "",
    search_term: str = "",
    name: str = "",
) -> dict:
    """
    Resolve a biological TARGET (protein/receptor/enzyme) to a ChEMBL ID.

    ⚠️ DO NOT use this tool to look up drugs, compounds, or molecules by name.
       For drug/compound/molecule names (e.g., "sorafenib", "imatinib", "aspirin"),
       use `search_chembl_molecule` instead.

    Resolution is deterministic SPARQL against the ChEMBL RDF graph, not a lexical
    search — there is no ranking to second-guess:
      • UNIPROT ACCESSION (e.g. "P00533") → the structured skos:exactMatch link.
        Returns every target containing that protein (the single protein plus any
        complex/family/chimera it participates in) — filter `target_type` to get
        just one.
      • GENE SYMBOL / PROTEIN NAME (e.g. "EGFR", "epidermal growth factor
        receptor") → EXACT (case-insensitive) match on the target component's
        skos:altLabel synonyms. Not fuzzy/substring — fix typos before calling.

    Every result carries `organism` and `type`, so a symbol shared across species
    or complexes is disambiguated by inspecting those fields (or by passing the
    `organism`/`target_type` filters) — NOT by trusting order.

    The search string can be passed as any of: `query` (canonical), `search`,
    `term`, `keyword`, `keywords`, `search_term`, or `name`.

    Args:
        query (str): UniProt accession (preferred), gene symbol, or exact protein
            name. Examples: "P00533", "EGFR", "Thrombin".
        limit (int, optional): Max results. Defaults to 20.
        organism (str, optional): Case-insensitive substring filter on organism,
            e.g. "Homo sapiens". Applied inside the query.
        target_type (str, optional): Exact (case-insensitive) filter on target
            type, e.g. "SINGLE PROTEIN" — pass this to collapse an accession/symbol
            match to the canonical single protein and drop complexes/families.

    Target Types (values of `type`): SINGLE PROTEIN, PROTEIN COMPLEX,
        PROTEIN FAMILY, PROTEIN-PROTEIN INTERACTION, CHIMERIC PROTEIN,
        NUCLEIC-ACID, CELL-LINE, TISSUE, ORGANISM, …

    Returns:
        dict: {'total_count' (int, rows returned — capped by `limit`),
        'results' (list)}. Each result has 'chembl_id', 'name' (rdfs:label),
        'organism', 'type', and 'score' (always None — SPARQL exact match has no
        relevance score; kept for shape stability).

        On endpoint failure this tool does NOT raise — it returns a dict with a
        single 'error' key instead. Check for 'error' before reading 'results'.
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
    # Route: UniProt accession → structured skos:exactMatch; else exact altLabel.
    acc = query.strip().upper()
    if _UNIPROT_ACCESSION_RE.match(acc):
        match_block = (
            f"  ?comp skos:exactMatch "
            f"<http://purl.uniprot.org/uniprot/{acc}> ."
        )
    else:
        alt = _altlabel_match_block(query)
        if alt is None:
            return {"total_count": 0, "results": []}
        match_block = f"  ?comp skos:altLabel ?alt .\n{alt}"

    filters = ""
    if organism.strip():
        filters += (
            f'\n  FILTER(CONTAINS(LCASE(STR(?organism)), '
            f'"{_sparql_literal(organism.strip().lower())}"))'
        )
    if target_type.strip():
        filters += (
            f'\n  FILTER(LCASE(STR(?type)) = '
            f'"{_sparql_literal(target_type.strip().lower())}")'
        )
    sparql = (
        f"{_CHEMBL_PREFIXES}\n"
        f"SELECT DISTINCT ?chembl_id ?name ?organism ?type "
        f"FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"{match_block}\n"
        f"  ?target cco:hasTargetComponent ?comp ;\n"
        f"          cco:chemblId ?chembl_id ; rdfs:label ?name ; cco:targetType ?type .\n"
        f"  OPTIONAL {{ ?target cco:organismName ?organism . }}{filters}\n"
        f"}} LIMIT {int(limit)}"
    )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    parsed_results = [
        {
            "chembl_id": r.get("chembl_id"),
            "name": r.get("name"),
            "organism": r.get("organism") or None,
            "type": r.get("type"),
            "score": None,
        }
        for r in rows
    ]
    return {"total_count": len(parsed_results), "results": parsed_results}


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
    Resolve a DRUG / COMPOUND / MOLECULE (by name or structure) to a ChEMBL ID.

    ✅ Use this tool for drug, compound, or molecule names
       (e.g., "sorafenib", "imatinib", "aspirin", "Gleevec").
    ⚠️ For biological targets (proteins, receptors, enzymes, genes such as
       EGFR, BRCA1, TP53), use `search_chembl_target` instead.

    Two resolution paths, auto-selected from the query shape:

    • NAME / BRAND / SYNONYM → deterministic SPARQL, EXACT (case-insensitive)
      match on the molecule's skos:altLabel synonyms (which include brand and
      trade names — "Gleevec" → CHEMBL941 IMATINIB). Not fuzzy/substring: fix
      typos before calling. No relevance ranking to second-guess.

    • STRUCTURE (SMILES / InChI / InChIKey) → the ChEMBL REST chemistry engine
      (flexmatch), which SPARQL cannot do. Auto-detected from structural
      punctuation / the "InChI=" prefix / the InChIKey pattern, e.g. aspirin's
      SMILES "CC(=O)Oc1ccccc1C(=O)O" → CHEMBL25. Detection is conservative
      (multi-word input, or input without structural punctuation, is treated as
      a name), so a bare-chain SMILES like "CCO" is treated as a name.

    The search string can be passed as any of: `query` (canonical), `search`,
    `term`, `keyword`, `keywords`, `search_term`, or `name`.

    Args:
        query (str): Drug/compound name, brand, synonym, or a structure string.
            Examples: "Aspirin", "Gleevec", "CC(=O)Oc1ccccc1C(=O)O",
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-N".
        limit (int, optional): Maximum number of results to return. Defaults to 20.

    Returns:
        dict: {'total_count' (int, rows returned — capped by `limit`),
        'results' (list)}. Each result has 'chembl_id' (e.g. "CHEMBL25"), 'name'
        (rdfs:label, may be None for some structure hits), and 'score' (always
        None; kept for shape stability).

        On endpoint/HTTP failure this tool does NOT raise — it returns a dict with
        a single 'error' key instead. Check for 'error' before reading 'results'.
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
    # Structure-shaped input → REST chemistry engine (SPARQL cannot do this).
    structure_kind = _looks_like_structure(query)
    if structure_kind:
        bulk = await _search_chembl_structure(structure_kind, query, limit)
        if "error" in bulk:
            return bulk
        total_count = bulk.get("page_meta", {}).get("total_count", 0)
        parsed_results = [
            {
                "chembl_id": m.get("molecule_chembl_id"),
                "name": m.get("pref_name"),
                "score": None,
            }
            for m in bulk.get("molecules", [])
        ]
        return {"total_count": total_count, "results": parsed_results}

    # Name/brand/synonym → deterministic SPARQL exact match on skos:altLabel.
    match = _altlabel_match_block(query)
    if match is None:
        return {"total_count": 0, "results": []}
    sparql = (
        f"{_CHEMBL_PREFIXES}\n"
        f"SELECT DISTINCT ?chembl_id ?name FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"  ?m skos:altLabel ?alt .\n"
        f"{match}\n"
        f"  ?m a cco:SmallMolecule ; cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        f"}} LIMIT {int(limit)}"
    )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    parsed_results = [
        {"chembl_id": r.get("chembl_id"), "name": r.get("name"), "score": None}
        for r in rows
    ]
    return {"total_count": len(parsed_results), "results": parsed_results}


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
