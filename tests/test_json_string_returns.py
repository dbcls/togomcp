"""Regression tests for the JSON-string return contract (Bug 3).

These tools previously returned bare Python lists, which FastMCP double-
represents (a text array plus a wrapped ``{"result": [...]}`` structured
object), so empty vs non-empty results had different client-visible shapes.
They now return a JSON string of a bare array — empty and non-empty share one
stable shape. See also the rhea/reactome cases in test_api_tools.py.
"""

import json

import httpx
import pytest
import respx

from togo_mcp.rdf_portal import (
    _keyword_matches,
    _singularize,
    find_databases,
    list_databases,
)
from togo_mcp.togoid import convertId, getRelation

_TOGOID = "https://api.togoid.dbcls.jp"


class TestRdfPortalListReturns:
    """list_databases / find_databases read a local CSV cache — no network."""

    def test_list_databases_is_json_array_string(self) -> None:
        result = list_databases()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, list) and parsed  # catalog is non-empty
        assert {"database", "title", "description"} <= parsed[0].keys()

    def test_find_databases_hit_and_miss_same_shape(self) -> None:
        miss = find_databases(keywords=["zzzznotarealdatabasexyz"])
        assert miss == "[]"  # bare array string, not {"result": []}
        hit = find_databases(keywords=["protein"])
        assert isinstance(hit, str)
        assert isinstance(json.loads(hit), list)


class TestKeywordMatcher:
    """Multi-word / plural / word-order matching for find_databases.

    Regression for phrase misses: "drug targets" and "clinical variants" are
    hinted verbatim in the Usage Guide but previously returned [] because the
    matcher did a brittle whole-phrase substring test against space-joined
    curated keywords.
    """

    def test_singularize_drops_trailing_s(self) -> None:
        assert _singularize("targets") == "target"
        assert _singularize("variants") == "variant"

    def test_singularize_leaves_ss_and_short_words(self) -> None:
        assert _singularize("class") == "class"  # 'ss' ending kept
        assert _singularize("is") == "is"  # too short
        assert _singularize("kinase") == "kinase"  # no trailing 's'

    def test_phrase_matches_out_of_order_and_plural(self) -> None:
        hay = "compound drug target bioactivity assay"
        assert _keyword_matches("drug targets", hay)  # plural + adjacent
        assert _keyword_matches("targets of drugs", hay)  # reordered + stopword

    def test_phrase_requires_all_content_tokens(self) -> None:
        hay = "compound drug bioactivity assay"  # no 'target'
        assert not _keyword_matches("drug targets", hay)

    def test_drug_targets_finds_chembl_first(self) -> None:
        res = json.loads(find_databases(keywords="drug targets"))
        dbs = [r["database"] for r in res]
        assert "chembl" in dbs
        assert dbs[0] == "chembl"  # ranked first

    def test_clinical_variants_finds_clinvar(self) -> None:
        res = json.loads(find_databases(keywords="clinical variants"))
        assert "clinvar" in [r["database"] for r in res]


class TestTogoidListReturns:
    @pytest.mark.asyncio
    async def test_convertid_returns_json_array_string(self) -> None:
        body = {"results": [["672", "P38398"], ["675", "O15129"]]}
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/convert").mock(
                return_value=httpx.Response(200, json=body)
            )
            result = await convertId(ids="672,675", route="ncbigene,uniprot")
        assert isinstance(result, str)
        assert json.loads(result) == [["672", "P38398"], ["675", "O15129"]]

    @pytest.mark.asyncio
    async def test_convertid_missing_results_is_empty_array(self) -> None:
        """When nothing converts, TogoID omits `results` entirely — coalesce to
        a bare `[]` rather than leaking null."""
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/convert").mock(
                return_value=httpx.Response(200, json={})
            )
            result = await convertId(ids="999999999", route="ncbigene,uniprot")
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_getrelation_returns_json_array_string(self) -> None:
        body = [{"forward": "encoded by", "reverse": "encodes",
                 "description": "gene-protein link"}]
        with respx.mock(using="httpx") as router:
            router.get(f"{_TOGOID}/config/relation/ncbigene-uniprot").mock(
                return_value=httpx.Response(200, json=body)
            )
            result = await getRelation(source="ncbigene", target="uniprot")
        assert isinstance(result, str)
        assert json.loads(result)[0]["forward"] == "encoded by"
