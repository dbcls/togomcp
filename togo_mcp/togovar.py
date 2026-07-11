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


def _project_variant(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten a /search/variant data row into the fields agents actually use.

    The list endpoint does not echo a tgv ID; cross-database identifiers live
    under `external_link` (dbsnp -> rs, clinvar -> VCV), which we surface as
    `rs`/`clinvar` for TogoID/ClinVar interoperability. Per-dataset frequencies
    are reshaped into a `{source: {af, ac, an}}` map.
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

    significance = [
        {
            "source": s.get("source"),
            "interpretations": s.get("interpretations"),
            "conditions": [c.get("name") for c in s.get("conditions", [])],
        }
        for s in row.get("significance") or []
    ]

    return {
        "variant": (
            f"{row.get('chromosome')}:{row.get('position')}:"
            f"{row.get('reference')}>{row.get('alternate')}"
        ),
        "type": row.get("type"),
        "chromosome": row.get("chromosome"),
        "position": row.get("position"),
        "reference": row.get("reference"),
        "alternate": row.get("alternate"),
        "genes": symbols,
        "rs": _titles("dbsnp"),
        "clinvar": _titles("clinvar"),
        "most_severe_consequence": row.get("most_severe_consequence"),
        "sift": row.get("sift"),
        "polyphen": row.get("polyphen"),
        "alphamissense": row.get("alphamissense"),
        "significance": significance,
        "frequencies": freqs,
    }


@togovar_mcp.tool()
async def search_gene(
    query: Annotated[str, Field(description="Gene symbol or alias, e.g. 'ALDH2'.")] = "",
) -> str:
    """Resolve a human gene symbol/alias to its HGNC ID for variant search.

    This is the FIRST step of the two-step variant workflow: the `hgnc_id`
    returned here is what `search_variant` takes as `gene_hgnc_id`.

    Args:
        query (str): Gene symbol or alias (e.g. "ALDH2", "BRCA2").

    Returns:
        str: JSON array (bare list) of matches, each
        `{"hgnc_id": int, "symbol": str, "name": str}`, best match first.
        Empty and non-empty results share the same `[...]` shape.

    Raises:
        ValueError: If `query` is blank, or on any HTTP/upstream error.
    """
    if not query.strip():
        raise ValueError("Missing gene search term. Pass a symbol via `query`, e.g. 'ALDH2'.")
    response = await _client.get("/search/gene", params={"term": query.strip()})
    raise_for_status_with_body(response, context="TogoVar gene search")
    hits = response.json()
    results = [
        {"hgnc_id": h.get("id"), "symbol": h.get("symbol"), "name": h.get("name")}
        for h in hits
    ]
    return json.dumps(results)


@togovar_mcp.tool()
async def search_disease(
    query: Annotated[
        str, Field(description="Disease term, e.g. 'breast cancer'.")
    ] = "",
) -> str:
    """Resolve a disease term to MONDO / MedGen IDs for variant search.

    The returned `mondo_id` (or MedGen CUI) is what `search_variant` takes as
    `disease_id`. Both land directly on TogoMCP's existing mondo/medgen RDF
    databases and TogoID nodes.

    Args:
        query (str): Disease name (e.g. "breast cancer", "Marfan syndrome").

    Returns:
        str: JSON array (bare list) of matches, each
        `{"mondo_id": str, "medgen_cui": str | None, "label": str}`.

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
    results = [
        {"mondo_id": h.get("id"), "medgen_cui": h.get("cui"), "label": h.get("label")}
        for h in hits
    ]
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
) -> str:
    """Search TogoVar for human genome variants with population frequencies.

    TogoVar integrates allele frequencies from gnomAD, ToMMo (Japanese), NCBN,
    GEM-J, JGA, and BioBank Japan, plus ClinVar + MGeND clinical significance
    and SIFT/PolyPhen/AlphaMissense predictions — data with no SPARQL
    counterpart elsewhere in TogoMCP.

    All filters are optional and combined with AND. Supply zero filters to
    browse; but scope tightly — the database holds ~1 billion variants.

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

    Returns:
        str: JSON string `{"data": [...], "total"?, "filtered"?, "statistics"?}`.
        Each data row carries `variant` (chr:pos:ref>alt), coordinates, genes,
        `rs` (dbSNP) and `clinvar` (VCV) cross-links, most-severe consequence,
        SIFT/PolyPhen/AlphaMissense scores, clinical `significance`, and a
        `frequencies` map keyed by dataset ({af, ac, an}). `total`/`filtered`/
        `statistics` are present ONLY when `stat=True`. (The list endpoint does
        not return a tgv ID; use `rs`/`clinvar` for cross-database linking.)

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
        "data": [_project_variant(row) for row in payload.get("data", [])],
    }
    # Match counts and the category breakdown come from the statistics block,
    # which the API only computes (and it is the expensive part) when stat=1.
    # With stat=False the caller gets rows only — counts are omitted, not zero.
    if stat and "statistics" in payload:
        stats = payload["statistics"]
        result["total"] = stats.get("total")
        result["filtered"] = stats.get("filtered")
        result["statistics"] = stats
    return json.dumps(result)
