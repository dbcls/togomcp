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

from togo_mcp.togoid import convertId, getRelation

_TOGOID = "https://api.togoid.dbcls.jp"


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
