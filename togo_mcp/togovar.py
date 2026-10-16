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
# optional filters and fold them into the DSL here. Consequence and significance
# labels (missense_variant / pathogenic …) are accepted verbatim by the API.
# Variant TYPE is the exception: it is an enum that is case-sensitive, so it is
# translated (see _VARIANT_TYPE_TERMS).
# --------------------------------------------------------------------------- #

# Chromosome names TogoVar accepts (1-22, X, Y, MT).
_VALID_CHROMOSOMES = frozenset(
    [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]
)

# variant_type input (case-insensitive) -> the term the API accepts. The API's
# `type` filter is an enum of exactly SNV / INS / DEL / INDEL / MNV and their SO
# accessions (grch38.togovar.org/api/v1.yml); anything else, lowercase included,
# is HTTP 400. Before the 2026-10-16 fix this wrapper sent "snv"/"ins"/… verbatim, so EVERY
# variant_type filter failed. TogoVar calls SO_1000002 "MNV" (SO's name is
# "substitution") and SO_1000032 "Indel" (SO: "delins"), hence those aliases.
_VARIANT_TYPE_TERMS = {
    "snv": "SNV",
    "ins": "INS", "insertion": "INS",
    "del": "DEL", "deletion": "DEL",
    "indel": "INDEL", "delins": "INDEL",
    "mnv": "MNV", "sub": "MNV", "substitution": "MNV",
    **{so.lower(): so for so in
       ("SO_0001483", "SO_0000667", "SO_0000159", "SO_1000032", "SO_1000002")},
}

# ClinVar/MGeND significance sources.
_SIGNIFICANCE_SOURCES = frozenset(["clinvar", "mgend"])

# Base frequency panels. Sub-population strata (e.g. gnomad_genomes.eas,
# ncbn.jpn.hondo, bbj_riken.mpheno1) are passed through by validating only the
# dotted prefix, so new strata don't require a code change. A new BASE does: the
# 2026-10 reload added bbj1k, bbj2k, jogo and tommo_jsv1, and this list rejected
# all four until it was updated. The statistics `dataset` facet of any stat=True
# response is the live roster to compare against.
_FREQUENCY_DATASET_BASES = frozenset([
    "gnomad_genomes",
    "gnomad_exomes",
    "tommo",
    "tommo_jsv1",
    "ncbn",
    "gem_j_wga",
    "jga_wgs",
    "jga_wes",
    "jga_snp",
    "bbj1k",
    "bbj2k",
    "bbj_riken",
    "jogo",
])

# Bases the API no longer accepts on their own (HTTP 400 on the bare name, verified
# 2026-10-09) although it still accepts their dotted strata. Caught here so the
# caller is told what replaced it instead of getting an opaque schema error.
_STRATA_ONLY_DATASETS = {
    "bbj_riken": (
        "TogoVar no longer accepts the bare 'bbj_riken' panel. Use 'bbj1k' or "
        "'bbj2k' for the BioBank Japan whole-genome cohorts, or a 'bbj_riken.<stratum>' "
        "sub-population."
    ),
}

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
#     alleles over _IRI_ALLELE_MAX (a multi-kb SV would reintroduce the bloat).
_ALLELE_INLINE_MAX = 50
_ALLELE_HEAD = 20
_IRI_ALLELE_MAX = 50
# Soft cap on the serialized response; above it, data rows are trimmed and a
# `truncated` note is added so the payload stays inline-readable.
_MAX_RESPONSE_CHARS = 90_000

# Per-facet counting granularity of the `stat=True` statistics block. ALL four
# facets ARE scoped to the filtered set (verified live: each responds to the
# gene/disease/consequence/location filters), and since TogoVar's 2026-10-09
# data reload all four count VARIANTS — but a variant can fall under several
# values of `dataset`, `consequence` and `significance`, so only `type` sums to
# `filtered`:
#   - `type` counts each variant once.
#   - `dataset` counts a variant once per cohort it appears in.
#   - `consequence` counts a variant once per consequence term found on ANY of
#     its transcripts. Before the reload it counted per variant-TRANSCRIPT (a
#     BRCA1-locus variant then weighed ~460); verified 2026-10-14: BRCA1
#     pathogenic stop_gained gives filtered=652 and stop_gained=652, and
#     rs421016 (24 transcripts) counts 1 under each of its 4 terms.
#   - `significance` counts a variant once per classification label found in
#     ANY of its records (all conditions, all submitters). Before the reload it
#     counted per variant-CONDITION record; verified 2026-10-14: rs421016 has 15
#     records but counts 1 each under P, LP, RF and US. Unclassified variants
#     count under NA.
# So every consequence/significance value is <= `filtered`, but the SUMS exceed
# it, and adding labels (P + LP) double-counts variants that carry both. We ship
# these caveats alongside the raw numbers as `statistics_caveats`.
_STATISTICS_CAVEATS = {
    "type": (
        "Per-variant count, scoped to the filtered set (values sum to `filtered`)."
    ),
    "dataset": (
        "Per-variant count scoped to the filtered set; a variant present in N "
        "cohorts is counted N times, so the sum may exceed `filtered` while each "
        "value is <= it."
    ),
    "consequence": (
        "Per-variant count scoped to the filtered set: each value is the number "
        "of variants with that consequence on at least one transcript, so each "
        "value is <= `filtered`. A variant with different consequences on "
        "different transcripts counts under each, so the sum exceeds `filtered`. "
        "Do NOT compare the sum to `filtered`, and do NOT add values together to "
        "count variants."
    ),
    "significance": (
        "Per-variant count scoped to the filtered set: each value is the number "
        "of variants carrying that classification in at least one record (any "
        "condition, any submitter), so each value is <= `filtered`. A variant "
        "classified differently for different conditions counts under each "
        "label, so the sum exceeds `filtered` and labels you did not filter on "
        "(e.g. Uncertain significance under a pathogenic filter) can appear. Do "
        "NOT compare the sum to `filtered`, and do NOT add labels (e.g. P + LP) "
        "to count variants: that double-counts variants carrying both. "
        "Unclassified variants are counted under NA."
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
    T1 fixes). The REST row's position/reference/alternate are VCF-style (anchor
    base included), which is exactly what the SPARQL IRI is built from.
    """
    if not (chromosome and position and reference and alternate):
        return None
    if len(reference) > _IRI_ALLELE_MAX or len(alternate) > _IRI_ALLELE_MAX:
        return None
    return (
        f"http://identifiers.org/hco/{chromosome}/GRCh38#"
        f"{position}-{reference}-{alternate}"
    )


def _row_key(row: dict[str, Any]) -> list[Any]:
    """The API's sort / search-after key for a RAW (unprojected) variant row."""
    return [row.get("chromosome"), row.get("position"),
            row.get("reference"), row.get("alternate")]


def _normalize_offset(offset: int | list[str | int]) -> int | list[str | int]:
    """Validate `offset`: a non-negative int, or a [chromosome, position, reference,
    alternate] key (the previous page's `next_offset`) that the API pages after.

    The key form is the API's search-after cursor (api/v1.yml): it returns the rows
    strictly after that key and is not subject to the 10,000-row cap that an integer
    offset is. Raises ValueError on a malformed value (do not retry unchanged).
    """
    if isinstance(offset, bool):
        raise ValueError("`offset` must be an int or a 4-item key array.")
    if isinstance(offset, int):
        if offset < 0:
            raise ValueError("`offset` must be >= 0.")
        return offset
    if not isinstance(offset, (list, tuple)) or len(offset) != 4:
        raise ValueError(
            "`offset` key must be [chromosome, position, reference, alternate] — "
            "pass the previous page's `next_offset` unchanged. Do not retry unchanged."
        )
    chrom, pos, ref, alt = offset
    chrom = str(chrom)
    if chrom not in _VALID_CHROMOSOMES:
        raise ValueError(f"`offset` key: invalid chromosome {chrom!r}.")
    try:
        pos = int(pos)
    except (TypeError, ValueError):
        raise ValueError(f"`offset` key: position must be an integer, got {pos!r}.") from None
    return [chrom, pos, "" if ref is None else str(ref), "" if alt is None else str(alt)]


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
        bad = [t for t in types if t.strip().lower() not in _VARIANT_TYPE_TERMS]
        if bad:
            raise ValueError(
                f"Invalid variant_type {bad}; valid: SNV, INS, DEL, INDEL, MNV "
                "(any case; also insertion/deletion/delins/substitution or the "
                "SO accession). Do not retry with the same value."
            )
        terms = list(dict.fromkeys(
            _VARIANT_TYPE_TERMS[t.strip().lower()] for t in types
        ))
        clauses.append({"type": {"relation": "eq", "terms": terms}})

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
        if dataset in _STRATA_ONLY_DATASETS:
            raise ValueError(
                f"{_STRATA_ONLY_DATASETS[dataset]} Do not retry with the same value."
            )
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


# Genotype-count keys on a frequency panel. NOT universal — they are per-source
# (verified on rs671: jga_wgs carries the full set, jga_snp only aac/arc/rrc, ncbn
# only aac, tommo/jga_wes/gem_j_wga none, gnomAD neither), so each key is copied
# only when the panel actually has it rather than defaulted to None.
_GENOTYPE_KEYS = ("aac", "arc", "rrc", "hac", "hoc", "aoc", "ooc", "roc")


def _project_variant(
    row: dict[str, Any],
    include_full_alleles: bool = False,
    include_transcripts: bool = False,
) -> dict[str, Any]:
    """Flatten a /search/variant data row into the fields agents actually use.

    `variant_iri` is the SPARQL round-trip key and is emitted for every row with
    complete coordinates. Until 2026-10 it was gated on `tgv_id` (the row's `id`),
    because a row without one had no node in the then-smaller SPARQL graph; since
    the reload the graph holds ~99.9% of the REST set and most variants have NO
    tgv ID at all (verified 2026-10-09: ClinVar-Pathogenic CFTR 7:117480132-C-T is
    tgv_id=null and present in SPARQL), so that gate hid the key for most rows.

    Cross-database identifiers live under `external_links` (dbsnp -> rs, clinvar
    -> VCV), surfaced as `rs`/`clinvar`, and genes under `genes`. Both were renamed
    upstream in the same reload (from `external_link` / `symbols`); the old names
    are still read so a rollback does not empty the fields again.

    Per-dataset frequencies are reshaped into a `{source: {...}}` map carrying
    af/ac/an plus the QC `filter` and whatever genotype counts that panel has
    (hom-alt/het/hom-ref/hemizygous) — these drive carrier-frequency and
    Hardy-Weinberg reasoning and are per-source, not universal.

    Opaque codes are given human-readable companions: `type_label`,
    `most_severe_consequence_label`, and `interpretation_labels` on each
    significance entry (the raw codes are kept for backward compatibility).

    Per-transcript VEP (`transcripts`: HGVS c/p/g + per-transcript predictions) is
    opt-in via include_transcripts — a variant in a transcript-dense locus can
    carry 400+ transcript annotations, so it is kept out of the default payload.

    Large structural variants carry multi-kb REF/ALT; the `variant` label is
    length-bounded and `reference`/`alternate` are summarized (with true
    `ref_length`/`alt_length`) unless include_full_alleles=True.
    """
    ext = row.get("external_links") or row.get("external_link") or {}

    def _titles(key: str) -> list[str]:
        return [e.get("title") for e in ext.get(key, []) if e.get("title")]

    symbols = [
        s.get("name")
        for s in (row.get("genes") or row.get("symbols") or [])
        if s.get("name")
    ]

    freqs: dict[str, Any] = {}
    for f in row.get("frequencies") or []:
        src = f.get("source")
        if src:
            entry: dict[str, Any] = {
                "af": f.get("af"),
                "ac": f.get("ac"),
                "an": f.get("an"),
                "filter": f.get("filter"),
            }
            if f.get("quality") is not None:
                entry["quality"] = f["quality"]
            for gk in _GENOTYPE_KEYS:
                if gk in f:
                    entry[gk] = f[gk]
            freqs[src] = entry

    significance = []
    for s in row.get("significance") or []:
        interps = s.get("interpretations") or []
        significance.append({
            "source": s.get("source"),
            "interpretations": interps,
            "interpretation_labels": [
                _SIGNIFICANCE_LABELS.get(i, i) for i in interps
            ],
            "submission_count": s.get("submission_count"),
            "conditions": [
                {"name": c.get("name"), "medgen": c.get("medgen")}
                for c in s.get("conditions", [])
            ],
        })

    chrom = row.get("chromosome")
    pos = row.get("position")
    ref = row.get("reference")
    alt = row.get("alternate")
    vtype = row.get("type")
    msc = row.get("most_severe_consequence")
    tgv = row.get("id")

    projected = {
        "tgv_id": tgv,
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

    if include_transcripts:
        transcripts = []
        for tr in row.get("transcripts") or []:
            cons = tr.get("consequence") or []
            transcripts.append({
                "transcript_id": tr.get("transcript_id"),
                "gene_id": tr.get("gene_id"),
                "hgnc_id": tr.get("hgnc_id"),
                "consequence": cons,
                "consequence_labels": [_SO_LABELS.get(c, c) for c in cons],
                "hgvs_c": tr.get("hgvs_c"),
                "hgvs_p": tr.get("hgvs_p"),
                "hgvs_g": tr.get("hgvs_g"),
                "sift": tr.get("sift"),
                "polyphen": tr.get("polyphen"),
                "alphamissense": tr.get("alphamissense"),
            })
        projected["transcripts"] = transcripts

    return projected


def _label_facets(stats: dict[str, Any]) -> dict[str, Any]:
    """Add `*_labeled` companions to the code-keyed stat facets (C7).

    `type`/`consequence` are keyed by SO accession and `significance` by TogoVar's
    abbreviation codes; neither is readable on its own. The raw facets are left
    untouched for backward compatibility.

    ZERO COUNTS ARE DROPPED here. The API returns the FULL vocabulary in every
    facet — all 36 SO consequence terms and all 21 significance codes — mostly
    zeros (rs671: 3 non-zero of 36). Mirroring those into a labelled copy would
    double the noise, so the companion carries only what actually matched. Read the
    raw facet if you need the zeros.
    """
    labeled: dict[str, Any] = {}
    for facet, table in (
        ("type", _SO_LABELS),
        ("consequence", _SO_LABELS),
        ("significance", _SIGNIFICANCE_LABELS),
    ):
        counts = stats.get(facet)
        if isinstance(counts, dict):
            labeled[f"{facet}_labeled"] = {
                table.get(code, code): n for code, n in counts.items() if n
            }
    return labeled


@togovar_mcp.tool(annotations=READ_ONLY_TOOL)
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


@togovar_mcp.tool(annotations=READ_ONLY_TOOL)
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
    here (e.g. MONDO_0007254 "breast cancer" does NOT appear in these results).
    But a broad/parent MONDO ID still WORKS as a `disease_id` in `search_variant`
    even when unlisted here — the variant search resolves it via MONDO descendant
    expansion (MONDO_0007254 -> ~28,000 variants). So if you know or can resolve
    the canonical MONDO ID (e.g. via OLS4 or the `mondo` RDF database), pass it
    straight to `search_variant`; do not assume this resolver is exhaustive.

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


@togovar_mcp.tool(annotations=READ_ONLY_TOOL)
async def search_variant(
    tgv_id: str | list[str] = "",
    gene_hgnc_id: int | None = None,
    disease_id: str | list[str] = "",
    disease_source: str | list[str] = "",
    chromosome: str = "",
    position: int | None = None,
    # Explicit Field descriptions: the docstring documents these as COMBINED entries
    # ("start, stop:", "min_frequency, max_frequency:"), which FastMCP's Args: parser
    # cannot map onto individual parameters — all four shipped with EMPTY schema
    # descriptions until 2026-08-26. A Field wins over the docstring either way.
    start: Annotated[
        int | None,
        Field(description="Region start, 1-based inclusive. REQUIRES `chromosome`. Pair with `stop`; mutually exclusive with `position`."),
    ] = None,
    stop: Annotated[
        int | None,
        Field(description="Region end, 1-based inclusive. REQUIRES `chromosome`. Pair with `start`; mutually exclusive with `position`."),
    ] = None,
    variant_type: str | list[str] = "",
    consequence: str | list[str] = "",
    clinical_significance: str | list[str] = "",
    significance_source: str | list[str] = "",
    dataset: str = "",
    min_frequency: Annotated[
        float | None,
        Field(ge=0, le=1, description="Minimum allele frequency in [0, 1], applied to the cohort named by `dataset` — set `dataset` too, or the bound has no panel to apply to."),
    ] = None,
    max_frequency: Annotated[
        float | None,
        Field(ge=0, le=1, description="Maximum allele frequency in [0, 1], applied to the cohort named by `dataset`. E.g. dataset='tommo', max_frequency=0.01 for rare-in-Japan."),
    ] = None,
    limit: Annotated[int, Field(ge=0, le=1000)] = 100,
    offset: Annotated[
        int | list[str | int],
        Field(description="Rows to skip (int, offset + limit <= 10,000), OR the `next_offset` array [chromosome, position, reference, alternate] from the previous page, which pages past 10,000."),
    ] = 0,
    stat: bool = False,
    include_full_alleles: bool = False,
    include_transcripts: bool = False,
) -> str:
    """Search TogoVar for human genome variants with population frequencies.

    TogoVar integrates allele frequencies from gnomAD, ToMMo (Japanese), NCBN,
    GEM-J, JGA, BioBank Japan, and JoGo, plus ClinVar + MGeND clinical significance
    and SIFT/PolyPhen/AlphaMissense predictions — data with no SPARQL
    counterpart elsewhere in TogoMCP.

    All filters are optional and combined with AND. Supply zero filters to
    browse; but scope tightly — the database holds ~1.2 billion variants.

    COUNTS: `total` is the size of the whole REST backend (1,229,026,068 on
    2026-10-09) and is constant across queries; `filtered` is the count matching
    your filters. TogoMCP's `togovar` SPARQL graph is now about the same size
    (1,227,614,941), but the two are not the same set, so do not expect a REST
    count and a SPARQL `COUNT` to agree to the last variant.

    PAGING: an INTEGER `offset` is capped at `offset + limit <= 10,000` (HTTP 400
    beyond). To page further, use keys: every full page (as many rows as `limit`)
    returns `next_offset`, the [chromosome, position, reference, alternate] key of
    its last row. Pass it back unchanged as `offset` with the same filters to get the
    rows strictly after it, sorted by position — no 10,000 cap. A page shorter than
    `limit` is the last one and carries no `next_offset`.

    STATISTICS SCOPE (stat=True): all facets are scoped to the filtered set and
    count VARIANTS, but a variant can fall under several values. `type` counts
    each variant once (sums to `filtered`); `dataset` once per cohort;
    `consequence` once per consequence term on any of its transcripts;
    `significance` once per classification label in any of its records (any
    condition or submitter). So each value is <= `filtered`, but consequence/
    significance SUMS exceed it, and adding labels (P + LP) double-counts
    variants that carry both. See `statistics_caveats` for the per-facet rule.

    ROUND-TRIP TO SPARQL: use `variant_iri` — it is the subject IRI in the
    `togovar` SPARQL graph and is present on every row except one with a very
    long allele. Do NOT gate on `tgv_id`: most variants have none (it is null),
    and they are in SPARQL all the same. About 0.1% of REST variants have no
    SPARQL node, so an empty result for one IRI is possible and is not an error.

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
        variant_type: "SNV", "INS", "DEL", "INDEL" (delins) or "MNV"
            (substitution), any case, or the SO accession (e.g. "SO_0001483").
        consequence: SO consequence term or label, e.g. "missense_variant",
            "stop_gained", "frameshift_variant".
        clinical_significance: e.g. "pathogenic", "likely_pathogenic", "benign",
            "uncertain_significance", "risk_factor".
        significance_source: Restrict significance source(s): "clinvar", "mgend".
        dataset: Frequency panel for a frequency filter, e.g. "gnomad_genomes",
            "gnomad_exomes", "tommo", "tommo_jsv1", "ncbn", "gem_j_wga", "jga_wes",
            "jga_snp", "bbj1k", "bbj2k", "jogo". Sub-populations allowed (e.g.
            "gnomad_genomes.eas", "ncbn.jpn", "jga_wgs.jgad000758"). Two names
            that look valid match nothing: the bare "bbj_riken" is rejected
            (use "bbj1k"/"bbj2k"), and a filter on the bare "jga_wgs" returns 0
            variants although rows report it — filter on "jga_wgs.jgad000758" or
            "jga_wgs.jgad000868" instead (verified 2026-10-09).
        min_frequency, max_frequency: Allele-frequency bounds in [0, 1] on
            `dataset` (e.g. dataset="tommo", max_frequency=0.01 for rare-in-Japan).
        limit: Max variant rows to return, in [0, 1000]. Default 100.
        offset: Rows to skip (int, default 0), or a `next_offset` key array
            from the previous page (see PAGING).
        stat: If True, also return match counts (`total`, `filtered`) and the
            aggregate breakdown (counts by dataset, type, consequence,
            significance). REQUIRED to get a count — e.g. "how many variants
            match". Left False by default because computing the aggregation is
            the slow part of the query; use stat=False when you only need rows.
            See STATISTICS SCOPE above — every facet is scoped to the filtered
            set, but they count at different granularities, so only `type` sums
            to `filtered`.
        include_full_alleles: If True, return full REF/ALT sequences even for
            large structural variants. Default False summarizes alleles over
            ~50 bp as "<head>…(<n> bp)" to keep the response inline-readable;
            `ref_length`/`alt_length` always give the true lengths.
        include_transcripts: If True, add a `transcripts` list to each row with
            the per-transcript VEP annotation the REST backend already carries:
            transcript/gene IDs, SO consequence(+labels), HGVS c/p/g, and
            per-transcript SIFT/PolyPhen/AlphaMissense. Default False — a variant
            in a transcript-dense locus (e.g. BRCA1) can carry 400+ transcript
            annotations, which would dominate the response. Note this means HGVS
            and per-transcript predictions do NOT require a SPARQL round-trip.

    Returns:
        str: JSON string
        `{"data": [...], "total"?, "filtered"?, "statistics"?,
          "statistics_caveats"?, "truncated"?}`.
        Each data row carries `tgv_id` (null for most variants), `variant` (a
        length-bounded chr:pos:ref>alt locus label), `variant_iri` (the SPARQL
        subject IRI — see ROUND-TRIP above),
        coordinates, `reference`/`alternate` (summarized unless
        include_full_alleles) with `ref_length`/`alt_length`,
        `type`(+`type_label`), genes, `rs` (dbSNP) and `clinvar` (VCV)
        cross-links, `most_severe_consequence`(+`_label`),
        SIFT/PolyPhen/AlphaMissense scores, clinical `significance` (each with
        `interpretations` codes + `interpretation_labels`, `submission_count`,
        and `conditions` as {name, medgen CUI}), and a `frequencies` map keyed by
        dataset ({af, ac, an, filter, quality?} plus genotype counts where the
        panel provides them: aac=hom-alt, arc=het, rrc=hom-ref, hac/hoc=hemizygous
        — these are PER-SOURCE, so check the key rather than assuming it exists).
        `transcripts` is present only with include_transcripts=True.
        `total`/`filtered`/`statistics`/`statistics_caveats` are present ONLY when
        `stat=True`; `statistics` also carries `*_labeled` companions for the
        code-keyed facets (type/consequence/significance), and `scroll` reports the
        API's paging cap. `truncated` is present (and data rows trimmed) only if
        the response would be oversized.

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

    body: dict[str, Any] = {"limit": limit, "offset": _normalize_offset(offset)}
    if query:
        body["query"] = query
    # stat=1 (default upstream) collects the aggregate statistics block; stat=0
    # skips it for a lighter/faster response.
    params = {"stat": 1 if stat else 0}

    response = await _client.post("/search/variant", params=params, json=body)
    raise_for_status_with_body(response, context="TogoVar variant search")
    payload = response.json()

    rows = payload.get("data", [])
    result: dict[str, Any] = {
        "data": [
            _project_variant(row, include_full_alleles, include_transcripts)
            for row in rows
        ],
    }
    # Key for the next page, taken from the RAW last row: the projected row may
    # carry a length-bounded allele, which would not match the API's sort key.
    if limit and len(rows) == limit:
        result["next_offset"] = _row_key(rows[-1])
    # Surface the API's hard paging cap (offset + limit <= max_rows; HTTP 400
    # beyond it) so a caller paging a large result set sees the ceiling instead of
    # discovering it as an error.
    scroll = payload.get("scroll")
    if isinstance(scroll, dict) and scroll.get("max_rows") is not None:
        result["scroll"] = scroll
    # Match counts and the category breakdown come from the statistics block,
    # which the API only computes (and it is the expensive part) when stat=1.
    # With stat=False the caller gets rows only — counts are omitted, not zero.
    if stat and "statistics" in payload:
        stats = payload["statistics"]
        result["total"] = stats.get("total")
        result["filtered"] = stats.get("filtered")
        # The facets are keyed by SO accession / significance code, which are
        # unreadable on their own; ship labelled companions alongside the raw ones.
        result["statistics"] = {**stats, **_label_facets(stats)}
        # Every facet IS scoped to the filtered set; they just count at different
        # granularities (consequence per-transcript, significance per-condition), so
        # their sums exceed `filtered`. Ship the scope rules so the numbers are not
        # misread as variant counts. Only annotate facets actually present.
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
                "hint": "narrow filters or lower `limit` to see all rows, or page on with `next_offset`.",
            }
            # Re-key on the last row actually returned, so paging on resumes at
            # the first trimmed row instead of skipping the trimmed ones.
            if result["data"]:
                result["next_offset"] = _row_key(rows[len(result["data"]) - 1])
            out = json.dumps(result)
    return out
