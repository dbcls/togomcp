"""Tests for togo_mcp.pubcasefinder — pure helpers plus respx-mocked tools.

The `@pubcasefinder_mcp.tool()` decorator returns the original coroutine, so the
tools are awaited directly. HTTP is mocked with respx; the rate limiter and the
ID normalizers are tested without any network or sleeping.
"""

import json

import httpx
import pytest
import respx

from togo_mcp import pubcasefinder as pcf
from togo_mcp.pubcasefinder import (
    _cutoff_ties,
    _normalize_hpo_ids,
    _normalize_mondo_id,
    _project_candidate,
    _project_case_report,
    _rate_wait,
    get_case_reports,
    rank_by_phenotypes,
)

BASE = "https://pubcasefinder.dbcls.jp"


@pytest.fixture(autouse=True)
def _fresh_state():
    """Caches and the limiter are process-wide; isolate every test."""
    for cache in (pcf._ranking_cache, pcf._record_cache, pcf._case_report_cache):
        cache.clear()
    pcf._request_times.clear()
    yield
    pcf._request_times.clear()


# --------------------------------------------------------------------------- #
# Identifier normalization
# --------------------------------------------------------------------------- #
def test_normalize_hpo_ids_accepts_every_form_and_dedupes():
    assert _normalize_hpo_ids(
        "HP:0001166, HP_0001083 0002616 http://purl.obolibrary.org/obo/HP_0001166"
    ) == ["HP:0001166", "HP:0001083", "HP:0002616"]
    assert _normalize_hpo_ids(["hp:0001166", "HP:0001083"]) == ["HP:0001166", "HP:0001083"]


def test_normalize_hpo_ids_rejects_non_hpo():
    with pytest.raises(ValueError, match="Not HPO identifiers"):
        _normalize_hpo_ids(["HP:0001166", "MONDO:0007947"])
    with pytest.raises(ValueError, match="Not HPO identifiers"):
        _normalize_hpo_ids("HP:123")


def test_normalize_hpo_ids_blank_and_too_many():
    with pytest.raises(ValueError, match="Missing phenotypes"):
        _normalize_hpo_ids("  ")
    with pytest.raises(ValueError, match="At most"):
        _normalize_hpo_ids([f"HP:{i:07d}" for i in range(pcf.MAX_PHENOTYPES + 1)])


def test_normalize_mondo_id():
    for form in ("MONDO:0007947", "MONDO_0007947", "0007947",
                 "http://purl.obolibrary.org/obo/MONDO_0007947"):
        assert _normalize_mondo_id(form) == "MONDO:0007947"
    with pytest.raises(ValueError, match="Not a MONDO identifier"):
        _normalize_mondo_id("OMIM:154700")
    with pytest.raises(ValueError, match="Missing disease"):
        _normalize_mondo_id("")


# --------------------------------------------------------------------------- #
# Rate limiter (pure over _request_times)
# --------------------------------------------------------------------------- #
def test_rate_wait_free_below_minute_cap():
    pcf._request_times.extend([100.0 + i for i in range(9)])
    assert _rate_wait(110.0) == (0.0, None)


def test_rate_wait_minute_window_binds():
    pcf._request_times.extend([100.0 + i for i in range(10)])
    wait, binding = _rate_wait(110.0)
    # The oldest of the ten (t=100) ages out of the 60 s window at t=160.
    assert wait == pytest.approx(50.0)
    assert binding == "10 requests per minute"


def test_rate_wait_hour_window_binds_over_minute():
    # 100 requests spread over the last ~50 minutes, none in the last minute.
    now = 10_000.0
    pcf._request_times.extend([now - 3000 + i * 25 for i in range(100)])
    wait, binding = _rate_wait(now)
    assert binding == "100 requests per hour"
    assert wait == pytest.approx(600.0)


@pytest.mark.asyncio
async def test_exhausted_budget_raises_instead_of_waiting(monkeypatch):
    monkeypatch.setattr(pcf.time, "monotonic", lambda: 10_000.0)
    pcf._request_times.extend([10_000.0 - 3000 + i * 25 for i in range(100)])
    with pytest.raises(ValueError, match="rate budget exhausted"):
        await pcf._acquire_slot()


# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #
_OMIM_ROW = {
    "annotation_hp_num": 66, "annotation_hp_sum_ic": 658.778, "gene_id": "GENEID:2200",
    "id": "OMIM:154700", "matched_hpo_id": "HP:0001166,HP:0001083", "rank": 1, "score": 1.0,
}
_OMIM_RECORD = {
    "omim_disease_name_en": "Marfan syndrome", "omim_disease_name_ja": "マルファン症候群",
    "mondo_id": ["MONDO:0007947"], "ncbi_gene_id": ["GENEID:2200"], "hgnc_gene_symbol": ["FBN1"],
    "inheritance_en": {"HP:0000006": "Autosomal dominant inheritance"},
}


def test_project_candidate_disease():
    assert _project_candidate(_OMIM_ROW, _OMIM_RECORD, "omim") == {
        "rank": 1, "score": 1.0, "id": "OMIM:154700",
        "name_en": "Marfan syndrome", "name_ja": "マルファン症候群",
        "mondo_ids": ["MONDO:0007947"], "gene_ids": ["GENEID:2200"], "gene_symbols": ["FBN1"],
        "inheritance": ["Autosomal dominant inheritance"],
        "matched_hpo_ids": ["HP:0001166", "HP:0001083"], "annotated_hpo_count": 66,
    }


def test_project_candidate_gene_and_missing_record():
    row = {"id": "GENEID:11117", "rank": 1, "score": 0.99999, "matched_hpo_id": "HP:0001166",
           "annotation_hp_num": 132}
    record = {"hgnc_gene_symbol": "EMILIN1", "full_name": "elastin microfibril interfacer 1",
              "hgnc_gene_id": "HGNC:19880", "mondo_id": ["MONDO:0044622"]}
    out = _project_candidate(row, record, "gene")
    assert out["gene_symbol"] == "EMILIN1" and out["hgnc_id"] == "HGNC:19880"
    assert out["score"] == 1.0
    # A candidate upstream has no record for still projects, with null names.
    assert _project_candidate(_OMIM_ROW, {}, "orphanet")["name_en"] is None


def test_cutoff_ties():
    ranking = [{"rank": 1}, {"rank": 1}, {"rank": 1}, {"rank": 4}]
    assert _cutoff_ties(ranking, 2) == {"rank": 1, "tied_rows_not_returned": 1}
    assert _cutoff_ties(ranking, 3) is None
    assert _cutoff_ties(ranking, 10) is None


def test_project_case_report_strips_html_placeholders():
    ja = {"id": "Go to J-STAGE", "id_jglobal": "Go to J-GLOBAL", "journal": "脈管学", "pyear": "2018",
          "title": "…", "url": "https://www.jstage.jst.go.jp/x", "url_jglobal": "https://jglobal.jst.go.jp/y",
          "url_img_jstage": "<a><img></a>", "url_img_jglobal": "<a><img></a>"}
    assert _project_case_report(ja, "ja") == {
        "title": "…", "journal": "脈管学", "year": 2018,
        "jstage_url": "https://www.jstage.jst.go.jp/x", "jglobal_url": "https://jglobal.jst.go.jp/y",
    }
    en = {"id": 41782247, "journal": "Cardiol Young", "pyear": 2026, "title": "t",
          "url": "https://pubmed.ncbi.nlm.nih.gov/41782247"}
    assert _project_case_report(en, "en")["pmid"] == "41782247"


# --------------------------------------------------------------------------- #
# Tools — respx-mocked HTTP
# --------------------------------------------------------------------------- #
def _mock_rank_flow(ranking):
    hpo = respx.get(f"{BASE}/api/pcf_get_hpo_data_by_hpo_id").mock(
        return_value=httpx.Response(200, json={
            "HP:0001166": {"name_en": "Arachnodactyly", "name_ja": "くも指"},
        })
    )
    rank = respx.get(f"{BASE}/pcf_get_ranking_by_hpo_id").mock(
        return_value=httpx.Response(200, json=ranking)
    )
    names = respx.get(f"{BASE}/api/pcf_get_omim_data_by_omim_id").mock(
        return_value=httpx.Response(200, json={"OMIM:154700": _OMIM_RECORD})
    )
    return hpo, rank, names


@pytest.mark.asyncio
@respx.mock
async def test_rank_by_phenotypes_end_to_end_and_cached():
    second = dict(_OMIM_ROW, id="OMIM:000001", rank=2, score=0.5)
    hpo, rank, names = _mock_rank_flow([_OMIM_ROW, second])

    out = json.loads(await rank_by_phenotypes(hpo_ids="HP:0001166 HP:9999999", limit=1))

    assert out["query_phenotypes"] == [
        {"hpo_id": "HP:0001166", "name_en": "Arachnodactyly", "name_ja": "くも指"}
    ]
    assert out["unrecognized_hpo_ids"] == ["HP:9999999"]
    assert (out["total_count"], out["returned"], out["has_more"]) == (2, 1, True)
    assert out["results"][0]["name_en"] == "Marfan syndrome"
    # Unknown IDs are dropped BEFORE ranking: upstream would silently ignore them.
    assert rank.calls.last.request.url.params["phenotype"] == "HP:0001166"
    assert rank.calls.last.request.url.params["target"] == "omim"
    # Only the returned rows are named, in one batched call.
    assert names.calls.last.request.url.params["omim_id"] == "OMIM:154700"

    await rank_by_phenotypes(hpo_ids=["HP:0001166", "HP:9999999"], limit=1)
    assert (hpo.call_count, rank.call_count, names.call_count) == (1, 1, 1)
    assert len(pcf._request_times) == 3


@pytest.mark.asyncio
@respx.mock
async def test_rank_by_phenotypes_all_unrecognized_raises_without_ranking():
    respx.get(f"{BASE}/api/pcf_get_hpo_data_by_hpo_id").mock(
        return_value=httpx.Response(200, json={})
    )
    rank = respx.get(f"{BASE}/pcf_get_ranking_by_hpo_id")
    with pytest.raises(ValueError, match="None of"):
        await rank_by_phenotypes(hpo_ids="HP:9999999")
    assert not rank.called


@pytest.mark.asyncio
@respx.mock
async def test_rank_by_phenotypes_http_error_raises():
    respx.get(f"{BASE}/api/pcf_get_hpo_data_by_hpo_id").mock(
        return_value=httpx.Response(200, json={"HP:0001166": {"name_en": "Arachnodactyly"}})
    )
    respx.get(f"{BASE}/pcf_get_ranking_by_hpo_id").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(ValueError):
        await rank_by_phenotypes(hpo_ids="HP:0001166")


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_status_is_not_retried():
    route = respx.get(f"{BASE}/api/pcf_get_hpo_data_by_hpo_id").mock(
        return_value=httpx.Response(429, text="Too Many Requests")
    )
    with pytest.raises(ValueError, match="Do NOT retry"):
        await rank_by_phenotypes(hpo_ids="HP:0001166")
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_rank_by_phenotypes_bad_target_raises():
    with pytest.raises(ValueError, match="Unknown target"):
        await rank_by_phenotypes(hpo_ids="HP:0001166", target="disease")


@pytest.mark.asyncio
@respx.mock
async def test_get_case_reports_en_and_ja_params():
    route = respx.get(f"{BASE}/api/pcf_get_case_report").mock(
        side_effect=lambda request: httpx.Response(200, json=[
            {"id": 1, "journal": "J", "pyear": 2026, "title": "a", "url": "u1"},
            {"id": 2, "journal": "J", "pyear": 2025, "title": "b", "url": "u2"},
        ])
    )
    out = json.loads(await get_case_reports(mondo_id="MONDO_0007947", limit=1))
    assert (out["mondo_id"], out["total_count"], out["returned"], out["has_more"]) == (
        "MONDO:0007947", 2, 1, True)
    assert out["results"] == [{"pmid": "1", "title": "a", "journal": "J", "year": 2026, "url": "u1"}]
    assert "lang" not in route.calls.last.request.url.params

    await get_case_reports(mondo_id="MONDO:0007947", lang="ja")
    assert route.calls.last.request.url.params["lang"] == "ja"

    # Cached per (mondo, lang).
    await get_case_reports(mondo_id="0007947")
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_case_reports_empty_is_a_result():
    respx.get(f"{BASE}/api/pcf_get_case_report").mock(return_value=httpx.Response(200, json=[]))
    out = json.loads(await get_case_reports(mondo_id="MONDO:9999999"))
    assert out["total_count"] == 0 and out["results"] == []
