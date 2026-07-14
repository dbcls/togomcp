"""ChEMBL search tools (extracted from api_tools.py).

The ChEMBL wrappers resolve names/structures via SPARQL over the RDF Portal
graph rather than the flaky EBI REST lexical index, and ride on the shared REST
retry plumbing that lives in api_tools (_rest_get / _RestError / _rest_fail_msg /
_strip_html). See the "DB: ChEMBL" notes below for the full rationale.
"""
import csv
import io
import json
import re
from typing import Annotated

import httpx
from pydantic import Field

from .server import *
from .api_tools import (
    _resolve_query_alias,
    _rest_get,
    _RestError,
    _rest_fail_msg,
    _strip_html,
)

# ChEMBL REST client (EBI). The RDF Portal SPARQL endpoint is reached via
# execute_sparql (from .server), not this client.
_chembl_client = httpx.AsyncClient(base_url="https://www.ebi.ac.uk", timeout=30.0)


# DB: ChEMBL
#
# Text → ChEMBL-ID resolution runs as SPARQL against the RDF Portal graph, NOT
# the EBI REST lexical index. Reasons: (1) the REST /search.json index is
# token-OR ranked and buries the intended entity below orthologs/ligands/synonym
# noise (EGFR → the receptor is only rank ~6; a protein-name query returns
# thousands); (2) EBI REST is ~1/3 flaky. The RDF graph resolves deterministically
# in one indexed query, returning label + organism + type. Synonyms/brands/gene
# symbols live on skos:altLabel (on the molecule, and on the target COMPONENT).
# Canonical structure IDENTIFIERS (InChIKey/InChI) are stored as RDF literals, so
# they too resolve by exact SPARQL match. REST is retained ONLY for SMILES
# (flexmatch) — a SMILES is written differently by each toolkit, so it needs the
# chemistry engine's structural normalization, not an exact string match — and
# would be needed for similarity/substructure search. Those REST helpers ride on
# the shared `_rest_get` retry/HTML-strip plumbing near the top of this module;
# EBI REST is flaky (~1/3 of calls 500 or time out).


async def _chembl_get_json(path: str, params: dict, *, context: str) -> dict:
    """GET a ChEMBL JSON endpoint, retrying transient failures via `_rest_get`.

    Returns the parsed JSON on success. On terminal failure — including a 200
    with a non-JSON body — returns ``{"error": <clean message>}``; it never
    raises for HTTP/transport errors (the module's REST-wrapper contract).
    """
    resp = await _rest_get(_chembl_client, path, params=params, context=context)
    if isinstance(resp, _RestError):
        return {"error": _rest_fail_msg("ChEMBL REST API request", resp.message, "chembl")}
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError):
        # 200 with a non-JSON body — an upstream anomaly. Degrade gracefully
        # rather than raising (REST-wrapper contract).
        detail = f"malformed JSON body: {_strip_html(resp.text)}"
        logger.warning(f"{context} failed (terminal): {detail}")
        return {"error": _rest_fail_msg("ChEMBL REST API request", detail, "chembl")}


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
# The full cco:targetType controlled vocabulary (enumerated live 2026-07-14), used
# to validate the target_type filter so a typo fails loudly instead of as 0 rows.
_CHEMBL_TARGET_TYPES = frozenset(
    {
        "SINGLE PROTEIN", "ORGANISM", "CELL-LINE", "PROTEIN COMPLEX",
        "PROTEIN-PROTEIN INTERACTION", "PROTEIN FAMILY", "TISSUE",
        "SELECTIVITY GROUP", "NUCLEIC-ACID", "PROTEIN COMPLEX GROUP",
        "SMALL MOLECULE", "CHIMERIC PROTEIN", "OLIGOSACCHARIDE", "UNKNOWN",
        "MACROMOLECULE", "SUBCELLULAR", "LIPID", "PROTEIN NUCLEIC-ACID COMPLEX",
        "METAL", "3D CELL CULTURE", "PHENOTYPE", "UNCHECKED", "NO TARGET",
        "ADMET", "NON-MOLECULAR",
    }
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


def _paginate(rows: list, limit: int) -> tuple[list, bool]:
    """Split a limit+1 fetch into (page, has_more).

    Query with LIMIT limit+1; if the extra row came back, more results exist
    beyond this page. Lets a caller tell "N of N" from "N of many" — otherwise
    total_count == limit is indistinguishable from a silent truncation.
    """
    return rows[:limit], len(rows) > limit


# Structure-search routing for search_chembl_molecule.
# Structure IDENTIFIERS split by whether an exact string match is meaningful:
#   • InChIKey / InChI are CANONICAL — every toolkit emits the identical string
#     for a molecule — so an exact match on the RDF-stored value is correct and
#     resolves in SPARQL (fast, on the reliable endpoint).
#   • Canonical SMILES is toolkit-SPECIFIC — a user's SMILES is usually written
#     differently than ChEMBL's stored canonical form, so an exact string match
#     silently misses. It needs the REST chemistry engine's flexmatch, which
#     normalizes tautomers/salts/charges before matching. (Similarity and
#     substructure search would likewise need the chemistry engine.)
_INCHIKEY_RE = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")
# CHEMINF value-node types under the SIO qualified-value pattern
# (?m sio:SIO_000008 ?node; ?node a <CHEMINF_*>; ?node sio:SIO_000300 ?value).
_CHEMINF = {
    "inchikey": "http://semanticscience.org/resource/CHEMINF_000059",
    "inchi": "http://semanticscience.org/resource/CHEMINF_000113",
}


def _looks_like_structure(query: str) -> str | None:
    """Classify ``query`` as a chemical structure string.

    Returns ``"inchi"``, ``"inchikey"``, or ``"smiles"`` when the input is
    structure-shaped, else ``None`` (route to name resolution).

    Conservative by design — a name misrouted to a structure path returns
    nothing, so anything with whitespace (multi-word names) or without
    unambiguous structural punctuation stays on the name path. This means a
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


def _bif_longest_token(text: str) -> str | None:
    """Single-quoted bif:contains prefilter using the longest alphanumeric token.

    For a canonical identifier (InChIKey/InChI) one long distinctive token is a
    highly selective, always-present prefilter; the exact FILTER then guarantees
    the match. Returns None if there is no alphanumeric token.
    """
    toks = re.findall(r"[a-z0-9]+", text.lower())
    if not toks:
        return None
    return f"'{max(toks, key=len)}'"


async def _search_chembl_smiles_flexmatch(query: str, limit: int) -> dict:
    """SMILES → molecule via the ChEMBL REST chemistry engine (flexmatch).

    Returns the ``{"page_meta", "molecules"}`` REST shape. Used only for SMILES:
    flexmatch normalizes the structure first, so it tolerates the toolkit-specific
    ways the same molecule's canonical SMILES may be written. (InChIKey/InChI are
    canonical and resolved via SPARQL — see _search_chembl_inchi_sparql.)
    """
    filt = {
        "molecule_structures__canonical_smiles__flexmatch": query,
        "limit": limit,
    }
    return await _chembl_get_json(
        "/chembl/api/data/molecule.json", filt, context="ChEMBL SMILES flexmatch"
    )


async def _search_chembl_inchi_sparql(
    kind: str, query: str, limit: int
) -> list[dict] | dict:
    """Exact InChIKey / InChI → molecule lookup over the RDF graph.

    These identifiers are canonical, so an exact (CASE-SENSITIVE — InChIKeys are
    canonical uppercase) match on the stored SIO_000300 value is correct and
    toolkit-independent. bif:contains on the longest token prefilters via the
    Virtuoso text index. Returns CSV rows as list[dict], or {"error": ...}.
    """
    prefilter = _bif_longest_token(query)
    if prefilter is None:
        return []
    sparql = (
        f"{_CHEMBL_PREFIXES}\n"
        f"PREFIX sio: <http://semanticscience.org/resource/>\n"
        f"SELECT DISTINCT ?chembl_id ?name FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"  ?node a <{_CHEMINF[kind]}> ; sio:SIO_000300 ?v .\n"
        f'  ?v bif:contains "{prefilter}" .\n'
        f'  FILTER(STR(?v) = "{_sparql_literal(query)}")\n'
        f"  ?m sio:SIO_000008 ?node ; a cco:SmallMolecule ;\n"
        f"     cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        f"}} LIMIT {int(limit)}"
    )
    return await _run_chembl_sparql(sparql)


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
                "Optional: COMPOUND, TARGET, CELL_LINE, TISSUE, or ASSAY. Omit to "
                "search the four name kinds together. ASSAY (keyword match on the "
                "assay description) is opt-in only."
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
    Resolve a name to ChEMBL IDs across several entity kinds in one call.

    Cross-entity convenience wrapper over the ChEMBL RDF graph. Two matching
    regimes, because the entity kinds carry different searchable text:

    • EXACT (case-insensitive) NAME match — COMPOUND (skos:altLabel: brands,
      generics, synonyms), TARGET (component skos:altLabel: gene symbols, protein
      names), CELL_LINE and TISSUE (rdfs:label, e.g. "Liver", "CCRF S-180"). Not
      fuzzy/substring — fix typos before calling. Prefer the entity-specific tools
      (`search_chembl_molecule` / `search_chembl_target`) when you know the kind;
      they carry extra fields (organism/type).

    • KEYWORD-IN-DESCRIPTION — ASSAY. Assays have no name; their searchable text
      is a free-text dcterms:description, so ASSAY does a keyword (token) match on
      that description, NOT an exact match, e.g. entity_type="ASSAY",
      query="acetylcholinesterase" → every assay whose description mentions it.
      ASSAY results are relevance-ranked (best description match first).

    Default (no `entity_type`) searches the four EXACT-name kinds and UNIONs them.
    ASSAY is opt-in via entity_type="ASSAY" — its keyword semantics and high hit
    counts would otherwise swamp a name lookup. (DOCUMENT is not supported; query
    SPARQL directly for it.)

    The search string can be passed as any of: `query` (canonical), `search`,
    `term`, `keyword`, `keywords`, `search_term`, or `name`.

    RETURNS a dict {'total_count', 'has_more', 'results'}. `total_count` is the
    number of rows RETURNED (capped by `limit`), NOT the full match count; check
    `has_more` (true = more results exist beyond this page — relevant mainly for
    ASSAY, whose keyword search can have many hits). Each result carries
    'chembl_id', 'entity_type', and 'organism' (null for COMPOUND / where absent —
    use it to tell e.g. human from mouse targets). Name kinds also carry 'name'
    (rdfs:label); ASSAY rows instead carry 'description' (the free-text assay
    description, name=null) and a relevance 'score' (higher = better match).
    On endpoint failure this tool does NOT raise — it returns a dict with a single
    'error' key instead; CHECK FOR 'error' BEFORE READING 'results'.

    Args:
        entity_type (str, optional): One of COMPOUND, TARGET, CELL_LINE, TISSUE,
            ASSAY. Omit to search the four name kinds together.
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
    allowed = {"COMPOUND", "TARGET", "CELL_LINE", "TISSUE", "ASSAY"}
    if et and et not in allowed:
        raise ValueError(
            f"Invalid entity_type {entity_type!r}. Use one of: "
            f"{', '.join(sorted(allowed))} (DOCUMENT is not supported — query "
            "SPARQL directly). Omit it to search the four name kinds together."
        )
    bif = _bif_and(query)
    if bif is None:
        return {"total_count": 0, "has_more": False, "results": []}
    exact = _sparql_literal(query.lower())

    def exact_branch(
        label: str, bind: str, rest: str, prefilter: bool, has_organism: bool
    ) -> str:
        # bind → binds ?alt (+ ?chembl_id); prefilter uses the text index (needed
        # for the huge altLabel sets, skipped for the small type-constrained ones).
        # has_organism → carry cco:organismName so callers can disambiguate a name
        # shared across species (e.g. mouse CHEMBL3608 vs human CHEMBL203).
        lines = ["  {", f"    {bind}"]
        if prefilter:
            lines.append(f'    ?alt bif:contains "{bif}" .')
        lines.append(f'    FILTER(LCASE(STR(?alt)) = "{exact}")')
        lines.append(f"    {rest}")
        if has_organism:
            lines.append("    OPTIONAL { ?e cco:organismName ?organism }")
        lines.append(f'    BIND("{label}" AS ?entity_type)')
        lines.append("  }")
        return "\n".join(lines)

    branches = {
        "COMPOUND": exact_branch(
            "COMPOUND",
            "?e skos:altLabel ?alt .",
            "?e a cco:SmallMolecule ; cco:chemblId ?chembl_id ; rdfs:label ?name .",
            prefilter=True,
            has_organism=False,  # molecules have no organism
        ),
        "TARGET": exact_branch(
            "TARGET",
            "?comp skos:altLabel ?alt .",
            "?e cco:hasTargetComponent ?comp ; cco:chemblId ?chembl_id ; "
            "rdfs:label ?name .",
            prefilter=True,
            has_organism=True,
        ),
        "CELL_LINE": exact_branch(
            "CELL_LINE",
            "?e a cco:CellLine ; rdfs:label ?alt ; cco:chemblId ?chembl_id .",
            "BIND(STR(?alt) AS ?name)",
            prefilter=False,
            has_organism=True,
        ),
        "TISSUE": exact_branch(
            "TISSUE",
            "?e a cco:Tissue ; rdfs:label ?alt ; cco:chemblId ?chembl_id .",
            "BIND(STR(?alt) AS ?name)",
            prefilter=False,
            has_organism=True,
        ),
        # ASSAY: keyword match on the free-text description, relevance-ranked via the
        # bif:contains score (ORDER BY below); no exact FILTER, no DISTINCT.
        # ASSAY has no name — the searchable text is the free-text description,
        # exposed as `description` (not overloaded onto `name`), with a relevance
        # `score` (the whole point of keyword search). Ranked by that score.
        "ASSAY": (
            "  {\n"
            "    ?e a cco:Assay ; dcterms:description ?description ; cco:chemblId ?chembl_id .\n"
            f'    ?description bif:contains "{bif}" option (score ?sc) .\n'
            "    OPTIONAL { ?e cco:organismName ?organism }\n"
            '    BIND("ASSAY" AS ?entity_type)\n'
            "  }"
        ),
    }
    prefixes = f"{_CHEMBL_PREFIXES}\nPREFIX dcterms: <http://purl.org/dc/terms/>"
    fetch = int(limit) + 1  # over-fetch by one to detect truncation (has_more)
    if et == "ASSAY":
        # Rank by description-match score; DISTINCT would conflict with ORDER BY ?sc.
        sparql = (
            f"{prefixes}\n"
            f"SELECT ?chembl_id ?entity_type (STR(?description) AS ?description) "
            f"?organism ?sc FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
            f"{branches['ASSAY']}\n"
            f"}} ORDER BY DESC(?sc) LIMIT {fetch}"
        )
    else:
        if et:
            body = branches[et]
        else:
            # Default: the four exact-name kinds (ASSAY's keyword match is opt-in).
            body = "\n  UNION\n".join(
                branches[t] for t in ("COMPOUND", "TARGET", "CELL_LINE", "TISSUE")
            )
        sparql = (
            f"{prefixes}\n"
            f"SELECT DISTINCT ?chembl_id ?entity_type ?name ?organism "
            f"FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
            f"{body}\n"
            f"}} LIMIT {fetch}"
        )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    rows, has_more = _paginate(rows, int(limit))
    if et == "ASSAY":
        parsed_results = [
            {
                "chembl_id": r.get("chembl_id"),
                "entity_type": "ASSAY",
                "name": None,  # assays have no name — see `description`
                "description": r.get("description"),
                "organism": r.get("organism") or None,
                "score": int(r["sc"]) if (r.get("sc") or "").strip().isdigit() else None,
            }
            for r in rows
        ]
    else:
        parsed_results = [
            {
                "chembl_id": r.get("chembl_id"),
                "entity_type": r.get("entity_type"),
                "name": r.get("name"),
                "organism": r.get("organism") or None,
            }
            for r in rows
        ]
    return {
        "total_count": len(parsed_results),
        "has_more": has_more,
        "results": parsed_results,
    }


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

    Target-type values (for `type` and the `target_type` filter): SINGLE PROTEIN,
    PROTEIN COMPLEX, PROTEIN FAMILY, PROTEIN-PROTEIN INTERACTION, CHIMERIC PROTEIN,
    NUCLEIC-ACID, CELL-LINE, TISSUE, ORGANISM, SELECTIVITY GROUP, SMALL MOLECULE,
    OLIGOSACCHARIDE, LIPID, METAL, and other rarer kinds. An unrecognized
    `target_type` raises rather than silently matching nothing.

    The search string can be passed as any of: `query` (canonical), `search`,
    `term`, `keyword`, `keywords`, `search_term`, or `name`.

    RETURNS a dict {'total_count', 'has_more', 'results'}. `total_count` is rows
    RETURNED (capped by `limit`), not the full match count; `has_more` is true if
    more exist beyond this page. Each result has 'chembl_id', 'name' (rdfs:label),
    'organism', and 'type'. On endpoint failure this tool does NOT raise — it
    returns a dict with a single 'error' key instead; CHECK FOR 'error' BEFORE
    READING 'results'.

    Args:
        query (str): UniProt accession (preferred), gene symbol, or exact protein
            name. Examples: "P00533", "EGFR", "Thrombin".
        limit (int, optional): Max results. Defaults to 20.
        organism (str, optional): Case-insensitive substring filter on organism,
            e.g. "Homo sapiens". Applied inside the query.
        target_type (str, optional): Exact (case-insensitive) filter on target
            type, e.g. "SINGLE PROTEIN" — collapses an accession/symbol match to the
            canonical single protein and drops complexes/families.
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
    if target_type.strip() and target_type.strip().upper() not in _CHEMBL_TARGET_TYPES:
        raise ValueError(
            f"Invalid target_type {target_type!r}. It must be one of the ChEMBL "
            f"target-type vocabulary: {', '.join(sorted(_CHEMBL_TARGET_TYPES))}. "
            "(An unrecognized value would otherwise silently match nothing.)"
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
            return {"total_count": 0, "has_more": False, "results": []}
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
        f"}} LIMIT {int(limit) + 1}"
    )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    rows, has_more = _paginate(rows, int(limit))
    parsed_results = [
        {
            "chembl_id": r.get("chembl_id"),
            "name": r.get("name"),
            "organism": r.get("organism") or None,
            "type": r.get("type"),
        }
        for r in rows
    ]
    return {
        "total_count": len(parsed_results),
        "has_more": has_more,
        "results": parsed_results,
    }


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

    Resolution path is auto-selected from the query shape:

    • NAME / BRAND / SYNONYM → deterministic SPARQL, EXACT (case-insensitive)
      match on the molecule's skos:altLabel synonyms (which include brand and
      trade names — "Gleevec" → CHEMBL941 IMATINIB). Not fuzzy/substring: fix
      typos before calling. No relevance ranking to second-guess.

    • InChIKey / InChI → deterministic SPARQL, EXACT (case-SENSITIVE) match on the
      RDF-stored identifier. These are canonical (toolkit-independent), so exact
      match is correct, e.g. "BSYNRYMUTXBXSQ-UHFFFAOYSA-N" → CHEMBL25.

    • SMILES → the ChEMBL REST chemistry engine (flexmatch), NOT exact match: a
      SMILES is written differently by each toolkit, so flexmatch normalizes the
      structure first, e.g. "CC(=O)Oc1ccccc1C(=O)O" → CHEMBL25.

    Structure detection is conservative (multi-word input, or input without the
    "InChI=" prefix / InChIKey pattern / structural punctuation, is treated as a
    name), so a bare-chain SMILES like "CCO" is treated as a name.

    The search string can be passed as any of: `query` (canonical), `search`,
    `term`, `keyword`, `keywords`, `search_term`, or `name`.

    RETURNS a dict {'total_count', 'has_more', 'results'}. `total_count` is rows
    RETURNED (capped by `limit`), not the full match count; `has_more` is true if
    more exist beyond this page. Each result has 'chembl_id' (e.g. "CHEMBL25") and
    'name' (rdfs:label, may be None for some structure hits). On endpoint/HTTP
    failure this tool does NOT raise — it returns a dict with a single 'error' key
    instead; CHECK FOR 'error' BEFORE READING 'results'.

    Args:
        query (str): Drug/compound name, brand, synonym, or a structure string.
            Examples: "Aspirin", "Gleevec", "CC(=O)Oc1ccccc1C(=O)O",
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-N".
        limit (int, optional): Maximum number of results to return. Defaults to 20.
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
    # Structure-shaped input.
    structure_kind = _looks_like_structure(query)
    if structure_kind == "smiles":
        # SMILES canonical form is toolkit-specific → REST flexmatch normalizes.
        bulk = await _search_chembl_smiles_flexmatch(query.strip(), limit)
        if "error" in bulk:
            return bulk
        # REST page_meta.total_count is the TRUE match count; has_more from it.
        upstream_total = bulk.get("page_meta", {}).get("total_count", 0)
        parsed_results = [
            {
                "chembl_id": m.get("molecule_chembl_id"),
                "name": m.get("pref_name"),
            }
            for m in bulk.get("molecules", [])
        ]
        return {
            "total_count": len(parsed_results),
            "has_more": upstream_total > len(parsed_results),
            "results": parsed_results,
        }
    if structure_kind in ("inchikey", "inchi"):
        # Canonical identifiers → exact SPARQL lookup (reliable endpoint).
        rows = await _search_chembl_inchi_sparql(
            structure_kind, query.strip(), int(limit) + 1
        )
        if isinstance(rows, dict):
            return rows  # {"error": ...}
        rows, has_more = _paginate(rows, int(limit))
        parsed_results = [
            {"chembl_id": r.get("chembl_id"), "name": r.get("name")}
            for r in rows
        ]
        return {
            "total_count": len(parsed_results),
            "has_more": has_more,
            "results": parsed_results,
        }

    # Name/brand/synonym → deterministic SPARQL exact match on skos:altLabel.
    match = _altlabel_match_block(query)
    if match is None:
        return {"total_count": 0, "has_more": False, "results": []}
    sparql = (
        f"{_CHEMBL_PREFIXES}\n"
        f"SELECT DISTINCT ?chembl_id ?name FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"  ?m skos:altLabel ?alt .\n"
        f"{match}\n"
        f"  ?m a cco:SmallMolecule ; cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        f"}} LIMIT {int(limit) + 1}"
    )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    rows, has_more = _paginate(rows, int(limit))
    parsed_results = [
        {"chembl_id": r.get("chembl_id"), "name": r.get("name")}
        for r in rows
    ]
    return {
        "total_count": len(parsed_results),
        "has_more": has_more,
        "results": parsed_results,
    }
