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


# Tuning for the `extract` (containment) resolution path.
# 5 chars: measured floor that keeps incidental synonyms ("urea", "gel") out
# while every real drug name in the 2026-07-27..29 log sample cleared it. The
# exact-equality leg is OR'd back in so a shorter exact name is never lost.
_MIN_CONTAINED_LEN = 5
# Virtuoso's free-text parser degrades on long OR disjunctions; a drug name is
# effectively always within the first few tokens of an intervention string.
_MAX_BIF_TOKENS = 8
# Rows fetched before span-resolution prunes nested/duplicate hits. Generous
# because the pruning is client-side: a 3-drug regimen can legitimately draw
# dozens of raw synonym rows, and truncating early silently loses a component.
_EXTRACT_ROW_BUDGET = 200


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


def _target_exact_match_block(query: str) -> str | None:
    """WHERE fragment binding ?target by exact (case-insensitive) name.

    A target's name lives in TWO places, on two different nodes, and searching
    only the first is why `search_chembl_target("aldehyde dehydrogenase")`
    returned nothing while CHEMBL3542434 is literally named "Aldehyde
    dehydrogenase" (verified live 2026-08-12):

    * ``?comp skos:altLabel`` — synonyms of the target's protein COMPONENT
      (gene symbols, UniProt recommended names). The only leg that used to exist.
    * ``?target rdfs:label`` — the target's OWN name, i.e. the exact string this
      tool returns as `name`. CHEMBL3542434 carries no skos:altLabel at all, so
      component synonyms could never reach it.

    The second leg also un-hides the 4,894 targets with no protein component at
    all (2,383 ORGANISM, 1,997 CELL-LINE, 294 TISSUE, …). Those were unreachable
    by ANY query, even though `target_type` advertises CELL-LINE/TISSUE/ORGANISM
    as filter values — the old WHERE clause required cco:hasTargetComponent.

    Returns None when the query has no searchable token.
    """
    bif = _bif_and(query)
    if bif is None:
        return None
    q = _sparql_literal(query.lower())
    return (
        "  {\n"
        "    ?comp skos:altLabel ?alt .\n"
        f'    ?alt bif:contains "{bif}" .\n'
        f'    FILTER(LCASE(STR(?alt)) = "{q}")\n'
        "    ?target cco:hasTargetComponent ?comp .\n"
        "  } UNION {\n"
        "    ?target rdfs:label ?tlabel .\n"
        f'    ?tlabel bif:contains "{bif}" .\n'
        f'    FILTER(LCASE(STR(?tlabel)) = "{q}")\n'
        "  }"
    )


def _target_substring_match_block(query: str) -> str | None:
    """WHERE fragment binding ?target whose OWN name CONTAINS ``query``.

    Second pass only, and only when the exact pass found nothing. Exact-first is
    still the right default — the reason this module resolves names over SPARQL
    rather than the EBI REST index is that token-OR ranking buries the intended
    entity (EGFR lands at rank ~6 among orthologs and ligands). A substring pass
    that runs ONLY on zero results, returns everything it finds unranked, and
    labels itself `match_mode: "substring"` reintroduces none of that: there is
    no ranking for the caller to second-guess, and nothing displaces an exact hit
    that never existed.

    Breadth is bounded in practice — 'dehydrogenase', one of the broadest tokens
    a caller would plausibly type, matches 250 target labels (measured
    2026-08-12, 0.35s), not thousands. bif:contains does the index work; the
    FILTER makes it a real substring rather than a token bag.
    """
    bif = _bif_and(query)
    if bif is None:
        return None
    q = _sparql_literal(query.lower())
    return (
        "  ?target rdfs:label ?tlabel .\n"
        f'  ?tlabel bif:contains "{bif}" .\n'
        f'  FILTER(CONTAINS(LCASE(STR(?tlabel)), "{q}"))'
    )


def _target_sparql(match_block: str, filters: str, limit: int) -> str:
    """Assemble a target query around a ?target-binding match block."""
    return (
        f"{_CHEMBL_PREFIXES}\n"
        f"SELECT DISTINCT ?chembl_id ?name ?organism ?type "
        f"FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"{match_block}\n"
        f"  ?target cco:chemblId ?chembl_id ; rdfs:label ?name ; cco:targetType ?type .\n"
        f"  OPTIONAL {{ ?target cco:organismName ?organism . }}{filters}\n"
        f"}} LIMIT {int(limit) + 1}"
    )


def _target_zero_hint(query: str, *, organism: str, target_type: str) -> str:
    """Why a target search came back empty — and that it is not an outage.

    A 0-result is not an error, so a caller cannot tell it from a connectivity
    failure. That confusion is not hypothetical: on 2026-08-12 an empty target
    search was read as an endpoint problem, because the ebi endpoint really was
    down that day for unrelated reasons.
    """
    narrowed = [f"{k}={v!r}" for k, v in (("organism", organism), ("target_type", target_type)) if v]
    filter_note = (
        f" NOTE: you also passed {' and '.join(narrowed)} — a match may exist that "
        "those filters removed; retry without them to find out."
        if narrowed
        else ""
    )
    return (
        f"No ChEMBL target matched {query!r} — not by exact name or synonym, and not "
        "by substring of a target name. THIS IS NOT AN ENDPOINT FAILURE: the query "
        f"ran and returned nothing.{filter_note} Matching is literal, never fuzzy, so "
        "check spelling first. Then try a UniProt accession ('P00533'), a gene symbol "
        "('ALDH2'), or the full official name ('Aldehyde dehydrogenase, mitochondrial') "
        "— any of which resolves deterministically."
    )


def _id_lookup_zero_hint(query: str, *, entity_type: str) -> str:
    """Why a cross-entity lookup came back empty — and that it is not an outage.

    Same reasoning as `_target_zero_hint`, but this tool matches EXACTLY and has
    no substring fallback: keeping the cross-entity front door predictable is
    worth more than making it clever, so the hint names the entity-specific tool
    that does fall back instead.
    """
    scoped = (
        f" You restricted the search to entity_type={entity_type!r}; other kinds "
        "were not searched at all — omit it to search COMPOUND, TARGET, CELL_LINE "
        "and TISSUE together."
        if entity_type
        else ""
    )
    return (
        f"No ChEMBL entity exactly matched {query!r}. THIS IS NOT AN ENDPOINT FAILURE: "
        f"the query ran and returned nothing.{scoped} This tool matches whole names "
        "only, case-insensitively — never a prefix, a single word, or a fuzzy match, so "
        "check spelling first. For looser matching on a protein/enzyme, call "
        "search_chembl_target, which falls back to a substring pass over target names; "
        "for a drug string carrying a dose or several agents, call search_chembl_molecule "
        "with mode='extract'."
    )


def _containment_match_block(query: str) -> str | None:
    """WHERE-clause fragment matching ``?alt`` synonyms CONTAINED IN ``query``.

    The inverse of `_altlabel_match_block`: instead of "the synonym equals the
    caller's string", this asks "the synonym occurs inside it" — which is what
    turns a clinical-trial intervention string ("Ropivacaine 10% + Clonidine")
    into the substances it names. bif:contains ORs the tokens (any one may carry
    the drug); the FILTER then does the real work.

    A 5-character floor keeps incidental short synonyms out; the exact-equality
    leg is OR'd back in so a shorter *exact* name is never lost to that floor.
    Returns None when the query has no searchable token.
    """
    toks = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
    if not toks:
        return None
    # Cap the OR list: Virtuoso's free-text parser degrades on very long
    # disjunctions, and a drug name is nearly always in the first few tokens.
    bif = " OR ".join(f"'{t}'" for t in toks[:_MAX_BIF_TOKENS])
    q = _sparql_literal(query.lower())
    return (
        f'  ?alt bif:contains "{bif}" .\n'
        f"  FILTER(\n"
        f'    (STRLEN(STR(?alt)) >= {_MIN_CONTAINED_LEN} '
        f'&& CONTAINS("{q}", LCASE(STR(?alt))))\n'
        f'    || LCASE(STR(?alt)) = "{q}"\n'
        f"  )"
    )


def _resolve_spans(query: str, rows: list[dict]) -> list[dict]:
    """Reduce raw containment hits to the maximal non-overlapping drug mentions.

    The endpoint returns every synonym occurring anywhere in ``query``, which
    over-generates in two ways this collapses:

    * **Nested synonyms** — "Sofpironium Bromide Gel" matches SOFPIRONIUM
      BROMIDE, SOFPIRONIUM *and* BROMIDE (the bare counter-ion). Longest-span-
      first selection keeps only SOFPIRONIUM BROMIDE, since the shorter spans
      overlap it. Likewise "fexofenadine HCL" keeps the hydrochloride salt
      rather than also emitting bare FEXOFENADINE.
    * **Genuinely distinct components** — "Ropivacaine 10% + Clonidine" yields
      two non-overlapping spans, so both survive: a regimen resolves to its
      parts rather than to whichever part happened to sort first.

    Rows whose rdfs:label is just the ChEMBL ID (unnamed entries) are dropped —
    they carry no information a caller can act on.
    """
    low = query.lower()
    spans: list[tuple[int, int, str, str, str]] = []
    for r in rows:
        alt = (r.get("alt") or "").lower()
        cid, name = r.get("chembl_id") or "", r.get("name") or ""
        if not alt or not cid or not name or name == cid:
            continue
        start = low.find(alt)
        if start < 0:  # LCASE mismatch (accents/whitespace) — not a real span
            continue
        spans.append((start, start + len(alt), cid, name, alt))
    # Longest first, so a nested synonym never displaces the phrase containing it.
    spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
    taken: list[tuple[int, int, str, str, str]] = []
    for s in spans:
        if any(not (s[1] <= t[0] or s[0] >= t[1]) for t in taken):
            continue
        taken.append(s)
    seen: set[str] = set()
    out: list[dict] = []
    for start, end, cid, name, alt in sorted(taken):
        if cid in seen:
            continue
        seen.add(cid)
        out.append(
            {
                "chembl_id": cid,
                "name": name,
                "matched_span": query[start:end],
                "match_type": "exact" if alt == low else "contained",
            }
        )
    return out


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

# Every drug-substance type a name/structure lookup may legitimately return.
# ChEMBL's substance tree roots at cco:Substance (SmallMolecule | Biological |
# UndefinedSubstance); a bare `?m a cco:SmallMolecule` therefore drops EVERY
# biologic — antibodies, therapeutic proteins, vaccines, oligos, cell therapies —
# so "efalizumab", "Rituxan" and ~1M other substances resolved to zero rows.
#
# Enumerated rather than matched with `?t rdfs:subClassOf* cco:Substance` for two
# reasons: the property path costs ~17s vs ~0.15s for VALUES, and cco:Unclassified-
# Molecule (390 instances) is orphaned in the ontology — it has no subClassOf edge,
# so the path would silently miss it. Verified against the live endpoint 2026-07-30.
#
# cco:TargetComponent is deliberately EXCLUDED: it carries skos:altLabel and would
# otherwise leak ~12.8k protein targets into molecule results (use search_chembl_target).
_CHEMBL_MOLECULE_TYPES = (
    "cco:SmallMolecule cco:Inorganic cco:NaturalProductDerived cco:Synthetic "
    "cco:Biological cco:ProteinMolecule cco:Oligonucleotide cco:Oligosaccharide "
    "cco:Enzyme cco:CellTherapy cco:Vaccine cco:Virus "
    "cco:Antibody cco:Mab cco:Fab cco:FabPrime cco:FabPrime2 cco:ScFv cco:DiScFv "
    "cco:SdAb cco:BiTE cco:Immunoadhesin cco:IIIfunct "
    "cco:UndefinedSubstance cco:UnknownSubstance cco:UnclassifiedSubstance "
    "cco:UnclassifiedMolecule"
)


def _molecule_type_block(var: str, *, indent: str = "  ") -> str:
    """SPARQL constraining ``var`` to any ChEMBL drug-substance type.

    Replaces a hard-coded ``a cco:SmallMolecule`` so biologics resolve too.
    """
    tvar = f"?_{var.lstrip('?')}_type"
    return (
        f"{indent}{var} a {tvar} .\n"
        f"{indent}VALUES {tvar} {{ {_CHEMBL_MOLECULE_TYPES} }}"
    )


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
        f"  ?m sio:SIO_000008 ?node .\n"
        f"{_molecule_type_block('?m')}\n"
        f"  ?m cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        f"}} LIMIT {int(limit)}"
    )
    return await _run_chembl_sparql(sparql)


@mcp.tool(annotations=READ_ONLY_TOOL)
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
    search: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    term: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    keyword: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    keywords: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    search_term: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    name: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
) -> dict:
    """
    Resolve a name to ChEMBL IDs across several entity kinds in one call.

    Cross-entity convenience wrapper over the ChEMBL RDF graph. Two matching
    regimes, because the entity kinds carry different searchable text:

    • EXACT (case-insensitive) NAME match — COMPOUND (skos:altLabel: brands,
      generics, synonyms), TARGET (its own rdfs:label OR its component's
      skos:altLabel — gene symbols and protein names), CELL_LINE and TISSUE
      (rdfs:label, e.g. "Liver", "CCRF S-180"). Not fuzzy/substring — fix typos
      before calling, or use `search_chembl_target`, which falls back to a
      substring pass. Prefer the entity-specific tools
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
    ASSAY, whose keyword search can have many hits). ⚠️ On a default (cross-kind)
    search, `has_more`=true can also mean an entire entity_type is missing from
    the page: the kinds are UNIONed and the limit is applied to the whole, so
    e.g. "Liver" at limit=5 returns 5 TARGET rows and no TISSUE row, though both
    exist. Do NOT conclude a kind is absent from a truncated page — raise `limit`
    or re-run with `entity_type` set. Each result carries
    'chembl_id', 'entity_type', and 'organism' (null for COMPOUND / where absent —
    use it to tell e.g. human from mouse targets). Name kinds also carry 'name'
    (rdfs:label); ASSAY rows instead carry 'description' (the free-text assay
    description, name=null) and a relevance 'score' (higher = better match).

    An EMPTY 'results' additionally carries 'hint'. Read it: an empty result is
    NOT an endpoint failure, and must not be reported as one. On a real endpoint
    failure this tool does NOT raise — it returns a dict with a single 'error'
    key instead; CHECK FOR 'error' BEFORE READING 'results'.

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
        return {
            "total_count": 0,
            "has_more": False,
            "results": [],
            "hint": _id_lookup_zero_hint(query, entity_type=et),
        }
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
            f"{_molecule_type_block('?e', indent='').lstrip()}\n"
            "    ?e cco:chemblId ?chembl_id ; rdfs:label ?name .",
            prefilter=True,
            has_organism=False,  # molecules have no organism
        ),
        # TARGET does not fit exact_branch: a target's name lives on TWO nodes,
        # so it needs an inner UNION. Searching only the component's altLabel
        # meant a target could not be found by the string this tool returns as
        # `name` ("Aldehyde dehydrogenase" → 0 rows, while "ALDH2" → 3), and
        # requiring cco:hasTargetComponent hid the 4,894 targets that have no
        # protein component. Same fix as search_chembl_target; see
        # _target_exact_match_block for the full rationale and figures.
        #
        # cco:targetType is what makes ?e a TARGET. It is load-bearing on the
        # second leg: `?e rdfs:label ?tlabel` alone matches ANY labelled entity,
        # so without it a molecule whose name collided would come back stamped
        # entity_type="TARGET".
        "TARGET": (
            "  {\n"
            "    {\n"
            "      ?comp skos:altLabel ?alt .\n"
            f'      ?alt bif:contains "{bif}" .\n'
            f'      FILTER(LCASE(STR(?alt)) = "{exact}")\n'
            "      ?e cco:hasTargetComponent ?comp .\n"
            "    } UNION {\n"
            "      ?e rdfs:label ?tlabel .\n"
            f'      ?tlabel bif:contains "{bif}" .\n'
            f'      FILTER(LCASE(STR(?tlabel)) = "{exact}")\n'
            "    }\n"
            "    ?e cco:targetType ?target_type ; cco:chemblId ?chembl_id ; "
            "rdfs:label ?name .\n"
            "    OPTIONAL { ?e cco:organismName ?organism }\n"
            '    BIND("TARGET" AS ?entity_type)\n'
            "  }"
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
    out = {
        "total_count": len(parsed_results),
        "has_more": has_more,
        "results": parsed_results,
    }
    if not parsed_results:
        out["hint"] = _id_lookup_zero_hint(query, entity_type=et)
    return out


@mcp.tool(annotations=READ_ONLY_TOOL)
async def search_chembl_target(
    query: str = "",
    limit: int = 20,
    organism: str = "",
    target_type: str = "",
    search: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    term: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    keyword: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    keywords: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    search_term: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    name: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
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
        receptor") → EXACT (case-insensitive) match, tried against BOTH the
        target's own name and its protein component's skos:altLabel synonyms.
      • If that finds nothing, ONE substring pass over target names runs as a
        fallback (e.g. "dehydrogenase"). Still never fuzzy — fix typos.

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

    RETURNS a dict {'total_count', 'has_more', 'results', 'match_mode'}.
    `total_count` is rows RETURNED (capped by `limit`), not the full match count;
    `has_more` is true if more exist beyond this page. Each result has
    'chembl_id', 'name' (rdfs:label), 'organism', and 'type'. `match_mode` is
    'exact', 'substring', or 'none' — 'substring' means the exact pass found
    nothing and these are looser, UNRANKED matches, so verify 'name' before using
    them; 'none' means both passes ran and neither matched.

    An EMPTY 'results' additionally carries 'hint'. Read it: an empty result is
    NOT an endpoint failure, and must not be reported as one. On a real endpoint
    failure this tool does NOT raise — it returns a dict with a single 'error'
    key instead; CHECK FOR 'error' BEFORE READING 'results'.

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
    # Route: UniProt accession → structured skos:exactMatch (no text search, and
    # no substring fallback — an accession either links or it does not).
    acc = query.strip().upper()
    is_accession = bool(_UNIPROT_ACCESSION_RE.match(acc))
    if is_accession:
        match_block: str | None = (
            f"  ?comp skos:exactMatch <http://purl.uniprot.org/uniprot/{acc}> .\n"
            f"  ?target cco:hasTargetComponent ?comp ."
        )
    else:
        match_block = _target_exact_match_block(query)
    if match_block is None:
        return {
            "total_count": 0,
            "has_more": False,
            "results": [],
            "match_mode": "exact",
            "hint": _target_zero_hint(query, organism=organism, target_type=target_type),
        }

    rows = await _run_chembl_sparql(_target_sparql(match_block, filters, int(limit)))
    if isinstance(rows, dict):
        return rows  # {"error": ...}

    match_mode = "exact"
    if not rows and not is_accession:
        fallback = _target_substring_match_block(query)
        if fallback is not None:
            fb_rows = await _run_chembl_sparql(
                _target_sparql(fallback, filters, int(limit))
            )
            # A failing fallback must not turn a clean "0 exact matches" into an
            # error: the first pass already succeeded, and its emptiness is the
            # real answer.
            if not isinstance(fb_rows, dict) and fb_rows:
                rows, match_mode = fb_rows, "substring"

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
    out = {
        "total_count": len(parsed_results),
        "has_more": has_more,
        "results": parsed_results,
        "match_mode": match_mode,
    }
    if not parsed_results:
        # Both passes ran and both found nothing; reporting "exact" here would
        # imply a looser pass was still available to try.
        out["match_mode"] = "none"
        out["hint"] = _target_zero_hint(
            query, organism=organism, target_type=target_type
        )
    return out


async def _extract_chembl_molecules(query: str, limit: int) -> dict:
    """Resolve every ChEMBL substance NAMED INSIDE ``query`` (mode='extract').

    For clinical-trial intervention strings and dosed/formulated product names,
    which exact synonym matching cannot resolve by design: "Ropivacaine 10% +
    Clonidine 1 ug/kg" is not a synonym of anything, but it names two substances.
    """
    match = _containment_match_block(query)
    if match is None:
        return {"total_count": 0, "has_more": False, "results": [], "mode": "extract"}
    # LCASE(?alt) collapses case-variant synonyms server-side. Without it the row
    # budget is spent on ("Temozolomide","TEMOZOLOMIDE","temozolomide") and later
    # components of a regimen fall off the end of the LIMIT.
    sparql = (
        f"{_CHEMBL_PREFIXES}\n"
        f"SELECT DISTINCT ?chembl_id ?name (LCASE(STR(?alt)) AS ?alt)\n"
        f"FROM <{_CHEMBL_GRAPH}> WHERE {{\n"
        f"  ?m skos:altLabel ?alt .\n"
        f"{match}\n"
        f"{_molecule_type_block('?m')}\n"
        f"  ?m cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
        f"}} LIMIT {_EXTRACT_ROW_BUDGET}"
    )
    rows = await _run_chembl_sparql(sparql)
    if isinstance(rows, dict):
        return rows  # {"error": ...}
    results = _resolve_spans(query, rows)
    results, has_more = _paginate(results, limit)
    out = {
        "total_count": len(results),
        "has_more": has_more,
        "results": results,
        "mode": "extract",
    }
    if not results:
        out["note"] = (
            f"No ChEMBL substance is named inside {query!r}. It may be a regimen "
            "acronym (FOLFIRI), a procedure, a placeholder ('Treatment A'), or a "
            "sponsor code ChEMBL does not carry."
        )
    return out


@mcp.tool(annotations=READ_ONLY_TOOL)
async def search_chembl_molecule(
    query: str = "",
    limit: int = 20,
    mode: str = "exact",
    search: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    term: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    keyword: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    keywords: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    search_term: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
    name: Annotated[str, Field(description="Alias for `query` — pass ONE of query/search/term/keyword/keywords/search_term/name. Supplying two with different values raises ValueError.")] = "",
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

    ⚠️ `mode='extract'` — for a string that NAMES a drug rather than IS one.
       Exact matching (the default) cannot resolve a clinical-trial intervention
       string, a dosed/formulated product, or a multi-drug regimen, because none
       of those is a synonym of anything: "Ustekinumab 90 mg", "Diclofenac SR",
       "Ropivacaine 10% + Clonidine 1 µg/kg" all return 0 rows under 'exact'.
       `mode='extract'` instead finds every substance NAMED INSIDE the string,
       returning one result per distinct drug — so the combination above yields
       ROPIVACAINE and CLONIDINE. Nested synonyms collapse to the longest match
       ("Sofpironium Bromide Gel" → SOFPIRONIUM BROMIDE, not also BROMIDE).
       Use it as the RETRY when 'exact' returns nothing, not as the first call:
       it is a text-extraction heuristic, so treat a hit as a candidate to
       confirm, and note that it resolves a regimen to its COMPONENTS — it will
       never return "FOLFIRI" itself, only the drugs a string spells out.

    RETURNS a dict {'total_count', 'has_more', 'results'}. `total_count` is rows
    RETURNED (capped by `limit`), not the full match count; `has_more` is true if
    more exist beyond this page. Each result has 'chembl_id' (e.g. "CHEMBL25") and
    'name' (rdfs:label, may be None for some structure hits). Under
    `mode='extract'` each result additionally carries 'matched_span' (the text
    that matched) and 'match_type' ('exact' if the span is the whole query,
    else 'contained') — CHECK 'match_type' before trusting a hit. When a call
    returns no results, a 'note' key explains why and what to try next. On
    endpoint/HTTP failure this tool does NOT raise — it returns a dict with a
    single 'error' key instead; CHECK FOR 'error' BEFORE READING 'results'.

    Args:
        query (str): Drug/compound name, brand, synonym, or a structure string.
            Examples: "Aspirin", "Gleevec", "CC(=O)Oc1ccccc1C(=O)O",
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-N".
        limit (int, optional): Maximum number of results to return. Defaults to 20.
        mode (str, optional): "exact" (default) matches the WHOLE string against a
            synonym; "extract" finds substances named INSIDE it. Defaults to "exact".
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
    mode = (mode or "exact").strip().lower()
    if mode not in ("exact", "extract"):
        raise ValueError(
            f"Unknown mode {mode!r}. Use 'exact' (default: the whole string must "
            "BE a synonym) or 'extract' (find substances NAMED INSIDE the string)."
        )
    if mode == "extract":
        return await _extract_chembl_molecules(query, int(limit))
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
        f"{_molecule_type_block('?m')}\n"
        f"  ?m cco:chemblId ?chembl_id ; rdfs:label ?name .\n"
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
    out = {
        "total_count": len(parsed_results),
        "has_more": has_more,
        "results": parsed_results,
    }
    if not parsed_results:
        # An empty exact match is indistinguishable from "not in ChEMBL" unless
        # we say why. The dominant real-world cause is a decorated string (dose,
        # formulation, regimen) that is not itself a synonym of anything.
        out["note"] = (
            f"0 EXACT synonym matches for {query!r}. ChEMBL indexes single "
            "substances, not regimens or dosed/formulated products. If this "
            "string carries a dose, a formulation, or several drugs "
            "(\"Ustekinumab 90 mg\", \"Ropivacaine 10% + Clonidine\"), retry "
            "with mode='extract' to resolve the substances named inside it."
        )
    return out
