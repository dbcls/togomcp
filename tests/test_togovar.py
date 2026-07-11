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
    _project_variant,
    _range_from_bounds,
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
        {"hgnc_id": 404, "symbol": "ALDH2", "name": "aldehyde dehydrogenase 2"}
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
