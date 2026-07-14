import atexit
import json
from typing import Annotated, Any

import httpx
from pydantic import Field

from .server import *

# TogoVar REST API (GRCh38). Cohesive multi-endpoint external API, wrapped as a
# mounted sub-server (like togoid/ncbi) rather than a flat api_tools search_*
# tool — TogoVar has no SPARQL counterpart in RDF Portal, so it does not belong
# to the "keyword-search front door to a SPARQL DB" family. Following the TogoID
# convention, this module RAISES on HTTP error (via raise_for_status_with_body)
# and raises ValueError on bad parameters; it never returns an {"error": ...}
# payload. Keep the module uniform.
# The API returns 501 "Not implemented" unless the client asks for JSON, so pin
# the Accept header on every request via the shared client.
_client = httpx.AsyncClient(
    base_url="https://grch38.togovar.org/api",
    timeout=30.0,
    headers={"Accept": "application/json"},
)


def _close_client():
    """Close the shared httpx client on interpreter shutdown."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_client.aclose())
    except RuntimeError:
        asyncio.run(_client.aclose())


atexit.register(_close_client)

togovar_mcp = FastMCP("TogoVar API server")


# --------------------------------------------------------------------------- #
# Variant-query DSL builder (pure function — unit-tested without HTTP).
#
# The TogoVar /search/variant endpoint takes an expressive nested-JSON query
# language. Rather than make the LLM assemble that JSON, we expose a flat set of
# optional filters and fold them into the DSL here. Friendly labels
# (snv / missense_variant / pathogenic …) are accepted verbatim by the API, so
# no SO-accession translation table is needed.
# --------------------------------------------------------------------------- #

# Chromosome names TogoVar accepts (1-22, X, Y, MT).
_VALID_CHROMOSOMES = frozenset(
    [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]
)

# Short type aliases the API accepts alongside SO accessions.
_VARIANT_TYPES = frozenset(["snv", "ins", "del", "indel", "sub"])

# ClinVar/MGeND significance sources.
_SIGNIFICANCE_SOURCES = frozenset(["clinvar", "mgend"])

# Base frequency panels. Sub-population strata (e.g. gnomad_genomes.eas,
# ncbn.jpn.hondo, bbj_riken.mpheno1) are passed through by validating only the
# dotted prefix, so new strata don't require a code change.
_FREQUENCY_DATASET_BASES = frozenset([
    "gnomad_genomes",
    "gnomad_exomes",
    "tommo",
    "ncbn",
    "gem_j_wga",
    "jga_wgs",
    "jga_wes",
    "jga_snp",
    "bbj_riken",
])

# --------------------------------------------------------------------------- #
# Code -> human-readable label maps (the API returns opaque codes; agents and
# users need the labels). Both maps are the authoritative TogoVar vocabularies:
#   - significance: TogoVar advanced_search_conditions.json (clinvar bucket, a
#     superset of the mgend bucket).
#   - SO terms (variant `type` and VEP `most_severe_consequence`): resolved
#     against the Sequence Ontology (accession -> term name).
# Codes not in a map fall through unchanged, so an unknown value is never lost.
# --------------------------------------------------------------------------- #
_SIGNIFICANCE_LABELS = {
    "NC": "Not in ClinVar",
    "P": "Pathogenic",
    "LP": "Likely pathogenic",
    "PLP": "Pathogenic, low penetrance",
    "LPLP": "Likely pathogenic, low penetrance",
    "ERA": "Established risk allele",
    "LRA": "Likely risk allele",
    "URA": "Uncertain risk allele",
    "US": "Uncertain significance",
    "LB": "Likely benign",
    "B": "Benign",
    "CI": "Conflicting interpretations of pathogenicity",
    "DR": "Drug response",
    "CS": "Confers sensitivity",
    "RF": "Risk factor",
    "A": "Association",
    "PR": "Protective",
    "AF": "Affects",
    "O": "Other",
    "NP": "Not provided",
    "AN": "Association not found",
}

_SO_LABELS = {
    # variant types (the `type` field)
    "SO_0001483": "SNV",
    "SO_0002007": "MNV",
    "SO_0000159": "deletion",
    "SO_0000667": "insertion",
    "SO_1000002": "substitution",
    "SO_1000032": "delins",
    "SO_0002173": "indel",
    "SO_0001019": "copy_number_variation",
    "SO_0001060": "sequence_variant",
    # VEP consequence terms (the `most_severe_consequence` field)
    "SO_0001580": "coding_sequence_variant",
    "SO_0001907": "feature_elongation",
    "SO_0001906": "feature_truncation",
    "SO_0001589": "frameshift_variant",
    "SO_0001626": "incomplete_terminal_codon_variant",
    "SO_0001822": "inframe_deletion",
    "SO_0001821": "inframe_insertion",
    "SO_0001583": "missense_variant",
    "SO_0001621": "NMD_transcript_variant",
    "SO_0001818": "protein_altering_variant",
    "SO_0001819": "synonymous_variant",
    "SO_0002012": "start_lost",
    "SO_0001587": "stop_gained",
    "SO_0001578": "stop_lost",
    "SO_0002019": "start_retained_variant",
    "SO_0001567": "stop_retained_variant",
    "SO_0001624": "3_prime_UTR_variant",
    "SO_0001623": "5_prime_UTR_variant",
    "SO_0001627": "intron_variant",
    "SO_0001792": "non_coding_transcript_exon_variant",
    "SO_0001619": "non_coding_transcript_variant",
    "SO_0001574": "splice_acceptor_variant",
    "SO_0001575": "splice_donor_variant",
    "SO_0001630": "splice_region_variant",
    "SO_0001787": "splice_donor_5th_base_variant",
    "SO_0002170": "splice_donor_region_variant",
    "SO_0002169": "splice_polypyrimidine_tract_variant",
    "SO_0001893": "transcript_ablation",
    "SO_0001889": "transcript_amplification",
    "SO_0001620": "mature_miRNA_variant",
    "SO_0001894": "regulatory_region_ablation",
    "SO_0001891": "regulatory_region_amplification",
    "SO_0001566": "regulatory_region_variant",
    "SO_0001782": "TF_binding_site_variant",
    "SO_0001895": "TFBS_ablation",
    "SO_0001892": "TFBS_amplification",
    "SO_0001632": "downstream_gene_variant",
    "SO_0001628": "intergenic_variant",
    "SO_0001631": "upstream_gene_variant",
}

# Allele-rendering bounds (T1: large structural variants carry multi-kb REF/ALT
# that otherwise blow past the client token budget).
#   - Alleles longer than _ALLELE_INLINE_MAX are summarized in the `reference`/
#     `alternate` fields (unless include_full_alleles=True); the true lengths
#     are always reported as `ref_length`/`alt_length`.
#   - The compact `variant` label truncates each allele past _ALLELE_HEAD so the
#     locus string stays bounded (SNVs like "12:111766887:A>T" are unaffected).
#   - The reconstructed variant IRI embeds the full allele, so it is omitted for
#     alleles over _IRI_ALLELE_MAX (a multi-kb SV would reintroduce the bloat);
#     `tgv_id` is always emitted as the compact SPARQL round-trip key instead.
_ALLELE_INLINE_MAX = 50
_ALLELE_HEAD = 20
_IRI_ALLELE_MAX = 50
# Soft cap on the serialized response; above it, data rows are trimmed and a
# `truncated` note is added so the payload stays inline-readable.
_MAX_RESPONSE_CHARS = 90_000

# Per-facet scope of the `stat=True` statistics block. The TogoVar API applies
# the query filters INCONSISTENTLY across facets — verified live: `type`/
# `dataset` are scoped to the filtered set, but `consequence` is returned
# whole-database (its counts are orders of magnitude larger than `filtered` and
# barely move when the filter changes), and `significance` is faceted (it
# excludes its own significance filter and counts per variant-condition). This
# is a backend behavior a REST proxy cannot re-scope, so we ship the caveats
# alongside the raw numbers to stop callers from summing them against
# `filtered`. Attached to the response as `statistics_caveats`.
_STATISTICS_CAVEATS = {
    "type": "Scoped to the filtered set (per-value counts sum to `filtered`).",
    "dataset": (
        "Scoped to the filtered set; a variant present in N datasets is counted "
        "N times, so the sum may exceed `filtered` while each value is <= it."
    ),
    "consequence": (
        "NOT scoped — the TogoVar API returns the WHOLE-DATABASE consequence "
        "distribution regardless of filters. Do NOT sum against `filtered` or "
        "read these as counts for the filtered set."
    ),
    "significance": (
        "Faceted, NOT a filtered count: reflects the gene/disease-filtered set "
        "MINUS the significance filter itself, counted per variant-condition (a "
        "variant may recur under several conditions). May exceed `filtered`; do "
        "NOT sum against it."
    ),
}


def _summarize_allele(seq: str | None, include_full: bool) -> str | None:
    """Return an allele string bounded for display, or the full seq if asked.

    Sequences over _ALLELE_INLINE_MAX collapse to "<head>…(<n> bp)" unless
    include_full is True. None passes through.
    """
    if seq is None:
        return None
    if include_full or len(seq) <= _ALLELE_INLINE_MAX:
        return seq
    return f"{seq[:_ALLELE_HEAD]}…({len(seq)} bp)"


def _compact_allele(seq: Any) -> str:
    """Render one allele for the bounded `variant` locus label."""
    if not seq:
        return str(seq)
    if len(seq) <= _ALLELE_HEAD:
        return seq
    return f"{seq[:8]}…{len(seq)}bp"


def _variant_iri(
    chromosome: Any, position: Any, reference: Any, alternate: Any
) -> str | None:
    """Reconstruct the TogoVar/HCO variant IRI for a SPARQL round-trip.

    Returns None when coordinates are incomplete or when either allele exceeds
    _IRI_ALLELE_MAX (embedding a multi-kb SV allele would reintroduce the bloat
    T1 fixes — callers use `tgv_id` for those).
    """
    if not (chromosome and position and reference and alternate):
        return None
    if len(reference) > _IRI_ALLELE_MAX or len(alternate) > _IRI_ALLELE_MAX:
        return None
    return (
        f"http://identifiers.org/hco/{chromosome}/GRCh38#"
        f"{position}-{reference}-{alternate}"
    )


def _match_type(candidate: str | None, query: str) -> tuple[str, int]:
    """Classify how `candidate` matches `query` and give a sort rank.

    Returns ("exact"|"prefix"|"word"|"fuzzy", rank) — lower rank sorts first.
    The TogoVar search endpoints do loose token matching with no relevance
    order, so both resolver tools re-rank client-side: exact hits first, then
    prefix, then whole-word, then everything else (demoting unrelated
    token-only matches like "Hepatic fibrosis…" for "cystic fibrosis").
    """
    c = (candidate or "").strip().lower()
    q = query.strip().lower()
    if not c:
        return "fuzzy", 3
    if c == q:
        return "exact", 0
    if c.startswith(q):
        return "prefix", 1
    if q in c.split():
        return "word", 2
    return "fuzzy", 3


def _as_list(value: str | list[str]) -> list[str]:
    """Coerce a str-or-list argument to a clean list[str]."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(v).strip() for v in value if str(v).strip()]


def _range_from_bounds(
    minimum: float | None, maximum: float | None
) -> dict[str, float]:
    """Build a TogoVar Range object from optional inclusive bounds."""
    rng: dict[str, float] = {}
    if minimum is not None:
        rng["gte"] = minimum
    if maximum is not None:
        rng["lte"] = maximum
    return rng


def _build_variant_query(
    *,
    tgv_id: str | list[str] = "",
    gene_hgnc_id: int | None = None,
    disease_id: str | list[str] = "",
    disease_source: str | list[str] = "",
    chromosome: str = "",
    position: int | None = None,
    start: int | None = None,
    stop: int | None = None,
    variant_type: str | list[str] = "",
    consequence: str | list[str] = "",
    clinical_significance: str | list[str] = "",
    significance_source: str | list[str] = "",
    dataset: str = "",
    min_frequency: float | None = None,
    max_frequency: float | None = None,
) -> dict[str, Any]:
    """Assemble a TogoVar /search/variant `query` object from flat filters.

    Each supplied filter becomes one DSL clause. Zero filters returns `{}`
    (match everything). Exactly one filter is returned bare; two or more are
    combined under a top-level `and` (the API requires `and` to hold >= 2
    items). Raises ValueError on invalid enum/coordinate inputs so the caller
    is told not to retry.
    """
    clauses: list[dict[str, Any]] = []

    tgv_ids = _as_list(tgv_id)
    if tgv_ids:
        clauses.append({"id": tgv_ids})

    if gene_hgnc_id is not None:
        clauses.append({"gene": {"relation": "eq", "terms": [gene_hgnc_id]}})

    disease_ids = _as_list(disease_id)
    if disease_ids:
        disease_clause: dict[str, Any] = {
            "disease": {"relation": "eq", "terms": disease_ids}
        }
        sources = _as_list(disease_source)
        bad = [s for s in sources if s not in _SIGNIFICANCE_SOURCES]
        if bad:
            raise ValueError(
                f"Invalid disease_source {bad}; valid: "
                f"{sorted(_SIGNIFICANCE_SOURCES)}. Do not retry with the same value."
            )
        if sources:
            disease_clause["disease"]["source"] = sources
        clauses.append(disease_clause)

    if chromosome:
        if chromosome not in _VALID_CHROMOSOMES:
            raise ValueError(
                f"Invalid chromosome {chromosome!r}; valid: 1-22, X, Y, MT. "
                "Do not retry with the same value."
            )
        if position is not None and (start is not None or stop is not None):
            raise ValueError(
                "Pass either `position` (a single site) or `start`/`stop` "
                "(a region), not both."
            )
        if position is not None:
            pos: Any = position
        elif start is not None or stop is not None:
            pos = _range_from_bounds(start, stop)
        else:
            raise ValueError(
                "`chromosome` requires `position` (single site) or "
                "`start`/`stop` (region)."
            )
        clauses.append({"location": {"chromosome": chromosome, "position": pos}})
    elif position is not None or start is not None or stop is not None:
        raise ValueError(
            "`position`/`start`/`stop` require `chromosome` to be set."
        )

    types = _as_list(variant_type)
    if types:
        bad = [t for t in types if t not in _VARIANT_TYPES]
        if bad:
            raise ValueError(
                f"Invalid variant_type {bad}; valid: {sorted(_VARIANT_TYPES)}. "
                "Do not retry with the same value."
            )
        clauses.append({"type": {"relation": "eq", "terms": types}})

    consequences = _as_list(consequence)
    if consequences:
        # SO accession or its label are both accepted by the API — pass through.
        clauses.append(
            {"consequence": {"relation": "eq", "terms": consequences}}
        )

    significances = _as_list(clinical_significance)
    if significances:
        sig_clause: dict[str, Any] = {
            "significance": {"relation": "eq", "terms": significances}
        }
        sig_sources = _as_list(significance_source)
        bad = [s for s in sig_sources if s not in _SIGNIFICANCE_SOURCES]
        if bad:
            raise ValueError(
                f"Invalid significance_source {bad}; valid: "
                f"{sorted(_SIGNIFICANCE_SOURCES)}. Do not retry with the same value."
            )
        if sig_sources:
            sig_clause["significance"]["source"] = sig_sources
        clauses.append(sig_clause)

    if dataset or min_frequency is not None or max_frequency is not None:
        if not dataset:
            raise ValueError(
                "min_frequency/max_frequency require `dataset` (which panel). "
                f"Valid panels: {sorted(_FREQUENCY_DATASET_BASES)} "
                "(sub-populations like gnomad_genomes.eas are allowed)."
            )
        base = dataset.split(".", 1)[0]
        if base not in _FREQUENCY_DATASET_BASES:
            raise ValueError(
                f"Unknown frequency dataset {dataset!r} (base {base!r}); valid "
                f"panels: {sorted(_FREQUENCY_DATASET_BASES)}. Sub-populations "
                "like 'gnomad_genomes.eas' or 'ncbn.jpn' are allowed. "
                "Do not retry with the same value."
            )
        if min_frequency is None and max_frequency is None:
            raise ValueError(
                "`dataset` requires min_frequency and/or max_frequency "
                "(allele-frequency bounds in [0, 1])."
            )
        clauses.append({
            "frequency": {
                # The API models a dataset as an object keyed by `name`, not a
                # bare string (a bare string 500s "Symbol into Integer").
                "dataset": {"name": dataset},
                "frequency": _range_from_bounds(min_frequency, max_frequency),
            }
        })

    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"and": clauses}


def _project_variant(
    row: dict[str, Any], include_full_alleles: bool = False
) -> dict[str, Any]:
    """Flatten a /search/variant data row into the fields agents actually use.

    `tgv_id` (the row's `id`) and the reconstructed `variant_iri` are the two
    stable keys for a SPARQL round-trip (frequency/significance via REST here ->
    VEP/cross-references via SPARQL). Cross-database identifiers live under
    `external_link` (dbsnp -> rs, clinvar -> VCV), surfaced as `rs`/`clinvar`.
    Per-dataset frequencies are reshaped into a `{source: {af, ac, an}}` map.

    Opaque codes are given human-readable companions: `type_label`,
    `most_severe_consequence_label`, and `interpretation_labels` on each
    significance entry (the raw codes are kept for backward compatibility).

    Large structural variants carry multi-kb REF/ALT; the `variant` label is
    length-bounded and `reference`/`alternate` are summarized (with true
    `ref_length`/`alt_length`) unless include_full_alleles=True.
    """
    ext = row.get("external_link") or {}

    def _titles(key: str) -> list[str]:
        return [e.get("title") for e in ext.get(key, []) if e.get("title")]

    symbols = [s.get("name") for s in row.get("symbols", []) if s.get("name")]

    freqs: dict[str, Any] = {}
    for f in row.get("frequencies") or []:
        src = f.get("source")
        if src:
            freqs[src] = {"af": f.get("af"), "ac": f.get("ac"), "an": f.get("an")}

    significance = []
    for s in row.get("significance") or []:
        interps = s.get("interpretations") or []
        significance.append({
            "source": s.get("source"),
            "interpretations": interps,
            "interpretation_labels": [
                _SIGNIFICANCE_LABELS.get(i, i) for i in interps
            ],
            "conditions": [c.get("name") for c in s.get("conditions", [])],
        })

    chrom = row.get("chromosome")
    pos = row.get("position")
    ref = row.get("reference")
    alt = row.get("alternate")
    vtype = row.get("type")
    msc = row.get("most_severe_consequence")

    return {
        "tgv_id": row.get("id"),
        "variant": f"{chrom}:{pos}:{_compact_allele(ref)}>{_compact_allele(alt)}",
        "variant_iri": _variant_iri(chrom, pos, ref, alt),
        "type": vtype,
        "type_label": _SO_LABELS.get(vtype) if vtype else None,
        "chromosome": chrom,
        "position": pos,
        "reference": _summarize_allele(ref, include_full_alleles),
        "alternate": _summarize_allele(alt, include_full_alleles),
        "ref_length": len(ref) if isinstance(ref, str) else None,
        "alt_length": len(alt) if isinstance(alt, str) else None,
        "genes": symbols,
        "rs": _titles("dbsnp"),
        "clinvar": _titles("clinvar"),
        "most_severe_consequence": msc,
        "most_severe_consequence_label": _SO_LABELS.get(msc) if msc else None,
        "sift": row.get("sift"),
        "polyphen": row.get("polyphen"),
        "alphamissense": row.get("alphamissense"),
        "significance": significance,
        "frequencies": freqs,
    }


@togovar_mcp.tool()
async def search_gene(
    query: Annotated[str, Field(description="Gene symbol or alias, e.g. 'ALDH2'.")] = "",
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
) -> str:
    """Resolve a human gene symbol/alias to its HGNC ID for variant search.

    This is the FIRST step of the two-step variant workflow: the `hgnc_id`
    returned here is what `search_variant` takes as `gene_hgnc_id`.

    The TogoVar endpoint does loose token matching with no relevance order (it
    returns the same set for "ALDH2" and the non-existent "ALDH2A1"), so this
    tool RE-RANKS client-side: exact symbol match first, then prefix, then other
    matches. Each result carries `match_type` ("exact"|"prefix"|"word"|"fuzzy")
    against your query — CHECK IT: if the top hit is not `exact`, the exact
    symbol you asked for does not exist and the rows are loose false positives,
    so do not blindly feed the first `hgnc_id` downstream. (The endpoint echoes
    the matched token as `symbol` and the HGNC approved gene name as `name`; it
    does not expose approved-vs-alias status, so use `name` to sanity-check.)

    Args:
        query (str): Gene symbol or alias (e.g. "ALDH2", "BRCA2").
        limit (int): Max matches to return, in [1, 100]. Default 10.

    Returns:
        str: JSON array (bare list) of matches, each
        `{"hgnc_id": int, "symbol": str, "name": str, "match_type": str}`,
        best match first. Empty and non-empty results share the same `[...]`
        shape.

    Raises:
        ValueError: If `query` is blank, or on any HTTP/upstream error.
    """
    if not query.strip():
        raise ValueError("Missing gene search term. Pass a symbol via `query`, e.g. 'ALDH2'.")
    response = await _client.get("/search/gene", params={"term": query.strip()})
    raise_for_status_with_body(response, context="TogoVar gene search")
    hits = response.json()
    ranked = []
    for h in hits:
        kind, rank = _match_type(h.get("symbol"), query)
        ranked.append((rank, {
            "hgnc_id": h.get("id"),
            "symbol": h.get("symbol"),
            "name": h.get("name"),
            "match_type": kind,
        }))
    # Stable sort preserves the endpoint's within-rank order.
    ranked.sort(key=lambda t: t[0])
    results = [r for _, r in ranked[:limit]]
    return json.dumps(results)


@togovar_mcp.tool()
async def search_disease(
    query: Annotated[
        str, Field(description="Disease term, e.g. 'breast cancer'.")
    ] = "",
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
) -> str:
    """Resolve a disease term to MONDO / MedGen IDs for variant search.

    The returned `mondo_id` (or MedGen CUI) is what `search_variant` takes as
    `disease_id`. Both land directly on TogoMCP's existing mondo/medgen RDF
    databases and TogoID nodes.

    The TogoVar endpoint does loose token matching with no relevance order (a
    query like "cystic fibrosis" also returns unrelated "Hepatic fibrosis…"
    rows), so this tool RE-RANKS client-side: exact label match first, then
    prefix, then whole-word, then loose token matches last. Each result carries
    `match_type` ("exact"|"prefix"|"word"|"fuzzy") — a top hit that is not
    `exact` means no exact label matched.

    COVERAGE LIMIT: TogoVar only indexes diseases that have ClinVar/MGeND
    variant associations, so some canonical/parent MONDO terms are simply absent
    here (e.g. MONDO_0007254 "breast cancer" is a valid `disease_id` for
    `search_variant`, returning ~24,550 variants, yet does NOT appear in these
    results). If you already know the MONDO ID, pass it straight to
    `search_variant`; do not assume this resolver is exhaustive.

    Args:
        query (str): Disease name (e.g. "breast cancer", "Marfan syndrome").
        limit (int): Max matches to return, in [1, 100]. Default 10.

    Returns:
        str: JSON array (bare list) of matches, each `{"mondo_id": str,
        "medgen_cui": str | None, "label": str, "match_type": str}`, best match
        first.

    Raises:
        ValueError: If `query` is blank, or on any HTTP/upstream error.
    """
    if not query.strip():
        raise ValueError(
            "Missing disease search term. Pass a disease name via `query`."
        )
    response = await _client.get("/search/disease", params={"term": query.strip()})
    raise_for_status_with_body(response, context="TogoVar disease search")
    hits = response.json()
    ranked = []
    for h in hits:
        kind, rank = _match_type(h.get("label"), query)
        ranked.append((rank, {
            "mondo_id": h.get("id"),
            "medgen_cui": h.get("cui"),
            "label": h.get("label"),
            "match_type": kind,
        }))
    ranked.sort(key=lambda t: t[0])
    results = [r for _, r in ranked[:limit]]
    return json.dumps(results)


@togovar_mcp.tool()
async def search_variant(
    tgv_id: str | list[str] = "",
    gene_hgnc_id: int | None = None,
    disease_id: str | list[str] = "",
    disease_source: str | list[str] = "",
    chromosome: str = "",
    position: int | None = None,
    start: int | None = None,
    stop: int | None = None,
    variant_type: str | list[str] = "",
    consequence: str | list[str] = "",
    clinical_significance: str | list[str] = "",
    significance_source: str | list[str] = "",
    dataset: str = "",
    min_frequency: float | None = None,
    max_frequency: float | None = None,
    limit: Annotated[int, Field(ge=0, le=1000)] = 100,
    offset: Annotated[int, Field(ge=0)] = 0,
    stat: bool = False,
    include_full_alleles: bool = False,
) -> str:
    """Search TogoVar for human genome variants with population frequencies.

    TogoVar integrates allele frequencies from gnomAD, ToMMo (Japanese), NCBN,
    GEM-J, JGA, and BioBank Japan, plus ClinVar + MGeND clinical significance
    and SIFT/PolyPhen/AlphaMissense predictions — data with no SPARQL
    counterpart elsewhere in TogoMCP.

    All filters are optional and combined with AND. Supply zero filters to
    browse; but scope tightly — the database holds ~1 billion variants.

    COUNTS: `total` is the size of the whole REST backend (~1.1 billion) and is
    constant across queries; `filtered` is the count matching your filters. Note
    the REST backend is LARGER than TogoMCP's `togovar` SPARQL graph (~3.9x: the
    SPARQL side is the annotated subset), so REST counts will not match SPARQL
    `COUNT(*)` — they measure different sets.

    STATISTICS SCOPE (stat=True): only the `type` and `dataset` facets are
    scoped to the filtered set. `consequence` is returned whole-database by the
    API (ignores your filters) and `significance` is a facet excluding its own
    filter — do NOT sum either against `filtered`. See `statistics_caveats` in
    the response for the per-facet rule.

    ROUND-TRIP TO SPARQL: each row carries `tgv_id` and `variant_iri`; either
    resolves in the `togovar` SPARQL graph for VEP/cross-reference deep dives.

    TWO-STEP WORKFLOW for gene/disease filters:
        1. `search_gene("ALDH2")` -> hgnc_id -> pass as `gene_hgnc_id`.
        2. `search_disease("breast cancer")` -> mondo_id -> pass as `disease_id`.

    Args:
        tgv_id: TogoVar variant ID(s), e.g. "tgv16331".
        gene_hgnc_id: HGNC ID (integer) from `search_gene` (NOT a symbol).
        disease_id: MONDO ID(s) (e.g. "MONDO_0007254") or MedGen CUI(s) from
            `search_disease`.
        disease_source: Restrict disease link source(s): "clinvar", "mgend".
        chromosome: "1"-"22", "X", "Y", "MT". Required for a positional filter.
        position: Single 1-based site (mutually exclusive with start/stop).
        start, stop: Inclusive region bounds (require `chromosome`).
        variant_type: "snv", "ins", "del", "indel", "sub".
        consequence: SO consequence term or label, e.g. "missense_variant",
            "stop_gained", "frameshift_variant".
        clinical_significance: e.g. "pathogenic", "likely_pathogenic", "benign",
            "uncertain_significance", "risk_factor".
        significance_source: Restrict significance source(s): "clinvar", "mgend".
        dataset: Frequency panel for a frequency filter, e.g. "gnomad_genomes",
            "gnomad_exomes", "tommo", "ncbn", "gem_j_wga", "jga_wgs", "jga_wes",
            "jga_snp", "bbj_riken". Sub-populations allowed (e.g.
            "gnomad_genomes.eas", "ncbn.jpn").
        min_frequency, max_frequency: Allele-frequency bounds in [0, 1] on
            `dataset` (e.g. dataset="tommo", max_frequency=0.01 for rare-in-Japan).
        limit: Max variant rows to return, in [0, 1000]. Default 100.
        offset: Rows to skip (pagination). Default 0.
        stat: If True, also return match counts (`total`, `filtered`) and the
            aggregate breakdown (counts by dataset, type, consequence,
            significance). REQUIRED to get a count — e.g. "how many variants
            match". Left False by default because computing the aggregation is
            the slow part of the query; use stat=False when you only need rows.
            See STATISTICS SCOPE above — the facets are not uniformly filtered.
        include_full_alleles: If True, return full REF/ALT sequences even for
            large structural variants. Default False summarizes alleles over
            ~50 bp as "<head>…(<n> bp)" to keep the response inline-readable;
            `ref_length`/`alt_length` always give the true lengths.

    Returns:
        str: JSON string
        `{"data": [...], "total"?, "filtered"?, "statistics"?,
          "statistics_caveats"?, "truncated"?}`.
        Each data row carries `tgv_id`, `variant` (a length-bounded
        chr:pos:ref>alt locus label), `variant_iri` (for SPARQL round-trip;
        null for very long alleles), coordinates, `reference`/`alternate`
        (summarized unless include_full_alleles) with `ref_length`/`alt_length`,
        `type`(+`type_label`), genes, `rs` (dbSNP) and `clinvar` (VCV)
        cross-links, `most_severe_consequence`(+`_label`),
        SIFT/PolyPhen/AlphaMissense scores, clinical `significance` (each with
        `interpretations` codes + `interpretation_labels`), and a `frequencies`
        map keyed by dataset ({af, ac, an}). `total`/`filtered`/`statistics`/
        `statistics_caveats` are present ONLY when `stat=True`. `truncated` is
        present (and data rows trimmed) only if the response would be oversized.

        Clinical-significance codes (in `interpretations`): P=Pathogenic,
        LP=Likely pathogenic, PLP=Pathogenic low-penetrance, LPLP=Likely
        pathogenic low-penetrance, US=Uncertain significance, LB=Likely benign,
        B=Benign, CI=Conflicting interpretations, DR=Drug response, RF=Risk
        factor, PR=Protective, A=Association, AF=Affects, CS=Confers sensitivity,
        ERA/LRA/URA=Established/Likely/Uncertain risk allele, O=Other, NP=Not
        provided, AN=Association not found, NC=Not in ClinVar. `_label` fields
        carry these spelled out.

    Raises:
        ValueError: On invalid enum/coordinate inputs, or any HTTP/upstream error.
    """
    query = _build_variant_query(
        tgv_id=tgv_id,
        gene_hgnc_id=gene_hgnc_id,
        disease_id=disease_id,
        disease_source=disease_source,
        chromosome=chromosome,
        position=position,
        start=start,
        stop=stop,
        variant_type=variant_type,
        consequence=consequence,
        clinical_significance=clinical_significance,
        significance_source=significance_source,
        dataset=dataset,
        min_frequency=min_frequency,
        max_frequency=max_frequency,
    )

    body: dict[str, Any] = {"limit": limit, "offset": offset}
    if query:
        body["query"] = query
    # stat=1 (default upstream) collects the aggregate statistics block; stat=0
    # skips it for a lighter/faster response.
    params = {"stat": 1 if stat else 0}

    response = await _client.post("/search/variant", params=params, json=body)
    raise_for_status_with_body(response, context="TogoVar variant search")
    payload = response.json()

    result: dict[str, Any] = {
        "data": [
            _project_variant(row, include_full_alleles)
            for row in payload.get("data", [])
        ],
    }
    # Match counts and the category breakdown come from the statistics block,
    # which the API only computes (and it is the expensive part) when stat=1.
    # With stat=False the caller gets rows only — counts are omitted, not zero.
    if stat and "statistics" in payload:
        stats = payload["statistics"]
        result["total"] = stats.get("total")
        result["filtered"] = stats.get("filtered")
        result["statistics"] = stats
        # The API filters facets inconsistently (consequence is whole-database,
        # significance is a self-excluding facet); ship the scope rules so the
        # numbers are not misread. Only annotate facets actually present.
        result["statistics_caveats"] = {
            k: v for k, v in _STATISTICS_CAVEATS.items() if k in stats
        }

    # Safety valve: even with alleles summarized, a wide + stat response can be
    # large. If it overflows the soft cap, drop data rows (keeping any stats)
    # until it fits, and flag the truncation rather than silently returning it.
    out = json.dumps(result)
    if len(out) > _MAX_RESPONSE_CHARS and result["data"]:
        while result["data"] and len(out) > _MAX_RESPONSE_CHARS:
            drop = max(1, len(result["data"]) // 4)
            del result["data"][-drop:]
            result["truncated"] = {
                "reason": "response exceeded size cap; data rows trimmed",
                "returned_rows": len(result["data"]),
                "hint": "narrow filters or lower `limit` to see all rows.",
            }
            out = json.dumps(result)
    return out
