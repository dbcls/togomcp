"""Tests for togo_mcp.togovar — pure DSL builder plus respx-mocked tools.

The `@togovar_mcp.tool()` decorator returns the original coroutine, so the tool
functions are awaited directly here. HTTP is mocked with respx; the pure DSL
builder (`_build_variant_query`) is tested without any network.
"""

import json

import httpx
import pytest
import respx

from togo_mcp.togovar import (
    _as_list,
    _build_variant_query,
    _compact_allele,
    _match_type,
    _project_variant,
    _range_from_bounds,
    _summarize_allele,
    _variant_iri,
    search_disease,
    search_gene,
    search_variant,
)

BASE = "https://grch38.togovar.org/api"


# --------------------------------------------------------------------------- #
# _build_variant_query — pure, no HTTP
# --------------------------------------------------------------------------- #
def test_no_filters_returns_empty():
    assert _build_variant_query() == {}


def test_single_filter_returned_bare():
    # One clause is NOT wrapped in `and`.
    assert _build_variant_query(gene_hgnc_id=404) == {
        "gene": {"relation": "eq", "terms": [404]}
    }


def test_multiple_filters_wrapped_in_and():
    q = _build_variant_query(gene_hgnc_id=404, variant_type="snv")
    assert set(q) == {"and"}
    assert {"gene": {"relation": "eq", "terms": [404]}} in q["and"]
    assert {"type": {"relation": "eq", "terms": ["snv"]}} in q["and"]
    assert len(q["and"]) == 2


def test_tgv_id_list_and_string():
    assert _build_variant_query(tgv_id="tgv16331") == {"id": ["tgv16331"]}
    assert _build_variant_query(tgv_id=["tgv1", "tgv2"]) == {"id": ["tgv1", "tgv2"]}


def test_location_single_position():
    q = _build_variant_query(chromosome="12", position=111766887)
    assert q == {"location": {"chromosome": "12", "position": 111766887}}


def test_location_region_becomes_range():
    q = _build_variant_query(chromosome="X", start=100, stop=200)
    assert q == {"location": {"chromosome": "X", "position": {"gte": 100, "lte": 200}}}


def test_frequency_filter_shape():
    q = _build_variant_query(dataset="tommo", max_frequency=0.01)
    assert q == {
        "frequency": {"dataset": {"name": "tommo"}, "frequency": {"lte": 0.01}}
    }


def test_frequency_subpopulation_allowed():
    q = _build_variant_query(dataset="gnomad_genomes.eas", min_frequency=0.05)
    assert q["frequency"]["dataset"] == {"name": "gnomad_genomes.eas"}


def test_significance_with_source():
    q = _build_variant_query(
        clinical_significance="pathogenic", significance_source="mgend"
    )
    assert q == {
        "significance": {
            "relation": "eq",
            "terms": ["pathogenic"],
            "source": ["mgend"],
        }
    }


def test_consequence_passthrough():
    q = _build_variant_query(consequence="missense_variant")
    assert q == {"consequence": {"relation": "eq", "terms": ["missense_variant"]}}


# --- validation errors ------------------------------------------------------
def test_invalid_chromosome_raises():
    with pytest.raises(ValueError, match="Invalid chromosome"):
        _build_variant_query(chromosome="23", position=1)


def test_position_without_chromosome_raises():
    with pytest.raises(ValueError, match="require `chromosome`"):
        _build_variant_query(position=1000)


def test_position_and_region_mutually_exclusive():
    with pytest.raises(ValueError, match="not both"):
        _build_variant_query(chromosome="1", position=1, start=2, stop=3)


def test_chromosome_without_coordinate_raises():
    with pytest.raises(ValueError, match="requires `position`"):
        _build_variant_query(chromosome="1")


def test_invalid_variant_type_raises():
    with pytest.raises(ValueError, match="Invalid variant_type"):
        _build_variant_query(variant_type="deletion")


def test_unknown_dataset_raises():
    with pytest.raises(ValueError, match="Unknown frequency dataset"):
        _build_variant_query(dataset="1000genomes", max_frequency=0.1)


def test_frequency_bounds_without_dataset_raises():
    with pytest.raises(ValueError, match="require `dataset`"):
        _build_variant_query(max_frequency=0.1)


def test_dataset_without_bounds_raises():
    with pytest.raises(ValueError, match="min_frequency and/or max_frequency"):
        _build_variant_query(dataset="tommo")


def test_invalid_significance_source_raises():
    with pytest.raises(ValueError, match="Invalid significance_source"):
        _build_variant_query(clinical_significance="benign", significance_source="foo")


# --- small helpers ----------------------------------------------------------
def test_as_list():
    assert _as_list("a") == ["a"]
    assert _as_list("") == []
    assert _as_list(["a", " b ", ""]) == ["a", "b"]


def test_range_from_bounds():
    assert _range_from_bounds(1, 2) == {"gte": 1, "lte": 2}
    assert _range_from_bounds(None, 2) == {"lte": 2}
    assert _range_from_bounds(1, None) == {"gte": 1}


def test_project_variant():
    row = {
        "type": "SO_0001483",
        "chromosome": "12",
        "position": 111803962,
        "reference": "G",
        "alternate": "A",
        "symbols": [{"name": "ALDH2", "id": 404}],
        "external_link": {
            "dbsnp": [{"title": "rs671"}],
            "clinvar": [{"title": "VCV000018390"}],
        },
        "frequencies": [{"source": "tommo", "af": 0.21, "ac": 52, "an": 250}],
        "significance": [
            {
                "source": "clinvar",
                "interpretations": ["P"],
                "conditions": [{"name": "Alcohol sensitivity", "medgen": "C123"}],
            }
        ],
        "most_severe_consequence": "SO_0001583",
    }
    p = _project_variant(row)
    assert p["variant"] == "12:111803962:G>A"
    assert p["genes"] == ["ALDH2"]
    assert p["rs"] == ["rs671"]
    assert p["clinvar"] == ["VCV000018390"]
    assert p["frequencies"]["tommo"] == {"af": 0.21, "ac": 52, "an": 250}
    assert p["significance"][0]["conditions"] == ["Alcohol sensitivity"]


# --------------------------------------------------------------------------- #
# T5/T6 — label maps, tgv_id, variant IRI in the projection
# --------------------------------------------------------------------------- #
def test_project_variant_labels_and_roundtrip_keys():
    row = {
        "id": "tgv47264307",
        "type": "SO_0001483",
        "chromosome": "12",
        "position": 111803962,
        "reference": "G",
        "alternate": "A",
        "most_severe_consequence": "SO_0001583",
        "significance": [{"source": "clinvar", "interpretations": ["P", "DR"]}],
    }
    p = _project_variant(row)
    # T6: stable SPARQL round-trip keys
    assert p["tgv_id"] == "tgv47264307"
    assert p["variant_iri"] == "http://identifiers.org/hco/12/GRCh38#111803962-G-A"
    # T5: opaque codes get human-readable companions
    assert p["type_label"] == "SNV"
    assert p["most_severe_consequence_label"] == "missense_variant"
    assert p["significance"][0]["interpretation_labels"] == [
        "Pathogenic",
        "Drug response",
    ]
    # raw codes preserved for backward compatibility
    assert p["significance"][0]["interpretations"] == ["P", "DR"]


def test_project_variant_unknown_code_falls_through():
    row = {"type": "SO_9999999", "most_severe_consequence": None,
           "significance": [{"interpretations": ["ZZ"]}]}
    p = _project_variant(row)
    assert p["type_label"] is None  # unknown SO -> no label
    assert p["most_severe_consequence_label"] is None
    # unknown significance code passes through unchanged, never dropped
    assert p["significance"][0]["interpretation_labels"] == ["ZZ"]


# --------------------------------------------------------------------------- #
# T1 — large-allele summarization / bounded variant label
# --------------------------------------------------------------------------- #
def test_summarize_allele_bounds_large_sequences():
    long_seq = "A" * 4000
    assert _summarize_allele("ACGT", False) == "ACGT"  # short: verbatim
    summ = _summarize_allele(long_seq, False)
    assert summ.endswith("(4000 bp)") and len(summ) < 40
    assert _summarize_allele(long_seq, True) == long_seq  # include_full
    assert _summarize_allele(None, False) is None


def test_compact_allele_and_variant_label_bounded():
    assert _compact_allele("A") == "A"
    assert _compact_allele("A" * 3000) == "A" * 8 + "…3000bp"


def test_project_variant_large_sv_bounded():
    row = {
        "chromosome": "17",
        "position": 43045008,
        "reference": "T" * 8080,
        "alternate": "T",
        "type": "SO_0000159",
    }
    p = _project_variant(row)
    # T1: variant label is length-bounded (was ~16.5k chars before the fix)
    assert len(p["variant"]) <= 64
    # true lengths still reported
    assert p["ref_length"] == 8080
    assert p["alt_length"] == 1
    # reference summarized, not the full 8kb sequence
    assert len(p["reference"]) < 64 and p["reference"].endswith("(8080 bp)")
    # IRI omitted for the multi-kb allele (would reintroduce the bloat)
    assert p["variant_iri"] is None
    # full sequence available on request
    full = _project_variant(row, include_full_alleles=True)
    assert full["reference"] == "T" * 8080


def test_variant_iri_none_for_incomplete_or_long():
    assert _variant_iri("12", 100, "G", "A").endswith("#100-G-A")
    assert _variant_iri("12", None, "G", "A") is None
    assert _variant_iri("12", 100, "A" * 100, "A") is None  # allele too long


# --------------------------------------------------------------------------- #
# T3/T4 — match_type classification
# --------------------------------------------------------------------------- #
def test_match_type_ranks():
    assert _match_type("ALDH2", "aldh2") == ("exact", 0)
    assert _match_type("ALDH2A1", "ALDH2") == ("prefix", 1)
    assert _match_type("Cystic fibrosis", "fibrosis") == ("word", 2)
    assert _match_type("Hepatic fibrosis-renal cysts", "cystic fibrosis") == (
        "fuzzy",
        3,
    )


# --------------------------------------------------------------------------- #
# Tool coroutines — respx-mocked HTTP
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@respx.mock
async def test_search_gene_projects_hgnc_id():
    respx.get(f"{BASE}/search/gene").mock(
        return_value=httpx.Response(
            200, json=[{"id": 404, "symbol": "ALDH2", "name": "aldehyde dehydrogenase 2"}]
        )
    )
    out = json.loads(await search_gene(query="ALDH2"))
    assert out == [
        {
            "hgnc_id": 404,
            "symbol": "ALDH2",
            "name": "aldehyde dehydrogenase 2",
            "match_type": "exact",
        }
    ]


@pytest.mark.asyncio
async def test_search_gene_blank_raises():
    with pytest.raises(ValueError, match="Missing gene search term"):
        await search_gene(query="  ")


@pytest.mark.asyncio
@respx.mock
async def test_search_disease_projects_mondo():
    respx.get(f"{BASE}/search/disease").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": "MONDO_0004438", "cui": "C1336076", "label": "breast cancer"}],
        )
    )
    out = json.loads(await search_disease(query="breast cancer"))
    assert out[0]["mondo_id"] == "MONDO_0004438"
    assert out[0]["medgen_cui"] == "C1336076"


@pytest.mark.asyncio
@respx.mock
async def test_search_variant_builds_body_and_projects():
    route = respx.post(f"{BASE}/search/variant").mock(
        return_value=httpx.Response(
            200,
            json={
                "statistics": {"total": 100, "filtered": 3},
                "data": [
                    {
                        "chromosome": "12",
                        "position": 111803962,
                        "reference": "G",
                        "alternate": "A",
                        "symbols": [{"name": "ALDH2"}],
                        "external_link": {"dbsnp": [{"title": "rs671"}]},
                    }
                ],
            },
        )
    )
    out = json.loads(
        await search_variant(gene_hgnc_id=404, variant_type="snv", stat=False)
    )
    # Response projection — stat=False omits counts/statistics entirely
    assert out["data"][0]["variant"] == "12:111803962:G>A"
    assert out["data"][0]["rs"] == ["rs671"]
    assert "statistics" not in out
    assert "total" not in out
    assert "filtered" not in out
    # Request body carried the composed DSL and stat=0
    sent = json.loads(route.calls.last.request.content)
    assert sent["query"] == {
        "and": [
            {"gene": {"relation": "eq", "terms": [404]}},
            {"type": {"relation": "eq", "terms": ["snv"]}},
        ]
    }
    assert route.calls.last.request.url.params["stat"] == "0"


@pytest.mark.asyncio
@respx.mock
async def test_search_variant_stat_included_when_requested():
    respx.post(f"{BASE}/search/variant").mock(
        return_value=httpx.Response(
            200,
            json={"statistics": {"total": 1, "filtered": 1, "type": {}}, "data": []},
        )
    )
    out = json.loads(await search_variant(tgv_id="tgv16331", stat=True))
    assert "statistics" in out
    assert out["total"] == 1
    assert out["filtered"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_search_variant_http_error_raises():
    respx.post(f"{BASE}/search/variant").mock(
        return_value=httpx.Response(400, text="bad query")
    )
    with pytest.raises(ValueError, match="TogoVar variant search"):
        await search_variant(gene_hgnc_id=404)


# --------------------------------------------------------------------------- #
# T3 — gene re-ranking: exact first; non-existent symbol has no exact hit
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@respx.mock
async def test_search_gene_exact_ranked_first():
    # API returns a loose set in arbitrary order; exact must float to the top.
    respx.get(f"{BASE}/search/gene").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 407, "symbol": "ALDHX", "name": "aldehyde dehydrogenase 1B1"},
                {"id": 15471, "symbol": "ALDH12", "name": "aldehyde dehydrogenase 8"},
                {"id": 404, "symbol": "ALDH2", "name": "aldehyde dehydrogenase 2"},
            ],
        )
    )
    out = json.loads(await search_gene(query="ALDH2"))
    assert out[0]["symbol"] == "ALDH2"
    assert out[0]["hgnc_id"] == 404
    assert out[0]["match_type"] == "exact"


@pytest.mark.asyncio
@respx.mock
async def test_search_gene_nonexistent_has_no_exact():
    # "ALDH2A1" does not exist; the endpoint still returns ALDH2-ish rows, but
    # none should be classified `exact`.
    respx.get(f"{BASE}/search/gene").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 404, "symbol": "ALDH2", "name": "aldehyde dehydrogenase 2"},
                {"id": 15471, "symbol": "ALDH12", "name": "aldehyde dehydrogenase 8"},
            ],
        )
    )
    out = json.loads(await search_gene(query="ALDH2A1"))
    assert all(r["match_type"] != "exact" for r in out)


@pytest.mark.asyncio
@respx.mock
async def test_search_gene_limit_applied():
    respx.get(f"{BASE}/search/gene").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": i, "symbol": f"G{i}", "name": "x"} for i in range(50)],
        )
    )
    out = json.loads(await search_gene(query="G", limit=5))
    assert len(out) == 5


# --------------------------------------------------------------------------- #
# T4 — disease re-ranking demotes loose token matches
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@respx.mock
async def test_search_disease_exact_first_fuzzy_last():
    respx.get(f"{BASE}/search/disease").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "MONDO_0008941", "cui": None,
                 "label": "Hepatic fibrosis-renal cysts-intellectual disability"},
                {"id": "MONDO_0009061", "cui": "C0010674", "label": "Cystic fibrosis"},
            ],
        )
    )
    out = json.loads(await search_disease(query="cystic fibrosis"))
    assert out[0]["mondo_id"] == "MONDO_0009061"
    assert out[0]["match_type"] == "exact"
    assert out[-1]["match_type"] == "fuzzy"


# --------------------------------------------------------------------------- #
# T2 — statistics_caveats attached, only for facets present
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@respx.mock
async def test_search_variant_statistics_caveats():
    respx.post(f"{BASE}/search/variant").mock(
        return_value=httpx.Response(
            200,
            json={
                "statistics": {
                    "total": 100, "filtered": 10,
                    "type": {"SO_0001483": 10},
                    "consequence": {"SO_0001583": 999999},
                },
                "data": [],
            },
        )
    )
    out = json.loads(await search_variant(gene_hgnc_id=404, stat=True))
    caveats = out["statistics_caveats"]
    assert "consequence" in caveats and "NOT scoped" in caveats["consequence"]
    assert "type" in caveats
    # facets absent from the response are not annotated
    assert "dataset" not in caveats
    assert "significance" not in caveats


# --------------------------------------------------------------------------- #
# T1 — response size safety valve trims rows on overflow
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@respx.mock
async def test_search_variant_size_valve_trims():
    # Each row carries a multi-kb allele; with include_full_alleles the payload
    # blows past the cap and rows must be trimmed with a `truncated` flag.
    big = "A" * 5000
    rows = [
        {"chromosome": "1", "position": i, "reference": big, "alternate": "A",
         "id": f"tgv{i}"}
        for i in range(50)
    ]
    respx.post(f"{BASE}/search/variant").mock(
        return_value=httpx.Response(200, json={"data": rows})
    )
    out = json.loads(
        await search_variant(gene_hgnc_id=404, include_full_alleles=True)
    )
    assert "truncated" in out
    assert len(out["data"]) < 50
    assert out["truncated"]["returned_rows"] == len(out["data"])
