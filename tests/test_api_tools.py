"""Tests for togo_mcp.api_tools module — HTTP mocking with respx."""

import json

import httpx
import pytest
import respx

import togo_mcp.api_tools as api_tools
from togo_mcp.api_tools import (
    _resolve_query_alias,
    search_pdb_entity,
    search_reactome_entity,
    search_rhea_entity,
    search_uniprot_entity,
)


@pytest.fixture(autouse=True)
def _no_rest_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero the REST retry backoff so the retry-then-error tests don't sleep."""
    monkeypatch.setattr(api_tools, "_REST_BACKOFF_BASE", 0.0)


class TestResolveQueryAlias:
    """Alias precedence is centralized; a conflict raises (surfacing the likely
    caller mistake) rather than silently dropping a value (Bug 5)."""

    def test_single_value_resolves(self) -> None:
        assert _resolve_query_alias("ATP") == "ATP"

    def test_duplicate_same_value_ok(self) -> None:
        # Same value via two aliases is not a conflict.
        assert _resolve_query_alias("ATP", search="ATP") == "ATP"

    def test_conflict_raises(self) -> None:
        with pytest.raises(ValueError, match="Multiple distinct search terms"):
            _resolve_query_alias("ATP", keyword="glucose")

    @pytest.mark.asyncio
    async def test_conflict_raises_via_tool(self) -> None:
        """The conflict surfaces through the tool layer, not just the helper."""
        with pytest.raises(ValueError, match="Multiple distinct search terms"):
            await search_reactome_entity(query="ATP", keyword="glucose")

    def test_alias_only_resolves(self) -> None:
        assert _resolve_query_alias("", term="x") == "x"
        assert _resolve_query_alias("") == ""

# ---------------------------------------------------------------------------
# UniProt
# ---------------------------------------------------------------------------


class TestSearchUniprotEntity:
    """Tests for search_uniprot_entity with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_basic_search(self) -> None:
        """Successful UniProt search returns TSV text."""
        tsv_body = "Entry\tProtein names\tOrganism\nP04637\tp53\tHomo sapiens\n"
        with respx.mock(using="httpx") as router:
            router.get("https://rest.uniprot.org/uniprotkb/search").mock(
                return_value=httpx.Response(200, text=tsv_body)
            )
            result = await search_uniprot_entity("TP53", limit=5)
        assert "P04637" in result
        assert "Homo sapiens" in result

    @pytest.mark.asyncio
    async def test_http_error_returns_message(self) -> None:
        """HTTP errors degrade to a guidance string (not an exception).

        UniProt search is declared `-> str`, so the error path returns a
        message that steers the caller toward retry / SPARQL fallback,
        matching the convention used by the other search tools.
        """
        with respx.mock(using="httpx") as router:
            router.get("https://rest.uniprot.org/uniprotkb/search").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            result = await search_uniprot_entity("TP53")
        assert isinstance(result, str)
        assert "UniProt REST API request failed" in result

    @pytest.mark.asyncio
    async def test_retries_5xx_then_succeeds(self) -> None:
        """The shared `_rest_get` plumbing now retries transient 5xx for the
        non-ChEMBL REST wrappers too (they previously did a single try)."""
        tsv_body = "Entry\tProtein names\tOrganism\nP04637\tp53\tHomo sapiens\n"
        with respx.mock(using="httpx") as router:
            route = router.get("https://rest.uniprot.org/uniprotkb/search").mock(
                side_effect=[
                    httpx.Response(503, text="<html>busy</html>"),
                    httpx.Response(200, text=tsv_body),
                ]
            )
            result = await search_uniprot_entity("TP53")
        assert route.call_count == 2
        assert "P04637" in result

    @pytest.mark.asyncio
    async def test_4xx_not_retried(self) -> None:
        """4xx is a terminal client error — no retry, degrades to a message."""
        with respx.mock(using="httpx") as router:
            route = router.get("https://rest.uniprot.org/uniprotkb/search").mock(
                return_value=httpx.Response(400, text="<html>bad</html>")
            )
            result = await search_uniprot_entity("TP53")
        assert route.call_count == 1
        assert "UniProt REST API request failed" in result
        assert "<" not in result and ">" not in result


# ---------------------------------------------------------------------------
# PDB
# ---------------------------------------------------------------------------


class TestSearchPdbEntity:
    """Tests for search_pdb_entity with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_basic_search(self) -> None:
        """Successful PDB search returns JSON with total and results."""
        body = {
            "total": 100,
            "results": [["1ABC", "Crystal structure of XYZ"], ["2DEF", "NMR structure"]],
        }
        with respx.mock(using="httpx") as router:
            router.get("https://pdbj.org/rest/newweb/search/pdb").mock(
                return_value=httpx.Response(200, json=body)
            )
            result_text = await search_pdb_entity("pdb", "kinase", limit=2)
        result = json.loads(result_text)
        assert result["total"] == 100
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_limit_applied(self) -> None:
        """Results are limited to the requested number."""
        entries = [[f"PDB{i}", f"desc{i}"] for i in range(10)]
        body = {"total": 10, "results": entries}
        with respx.mock(using="httpx") as router:
            router.get("https://pdbj.org/rest/newweb/search/pdb").mock(
                return_value=httpx.Response(200, json=body)
            )
            result_text = await search_pdb_entity("pdb", "kinase", limit=3)
        result = json.loads(result_text)
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_pdb_rich_projection(self) -> None:
        """PDB rows project named fields; NMR resolution sentinel -> None."""
        body = {
            "total": "2",
            "results": [
                [
                    "1abc", "Kinase X", "Doe, J.", "A great paper", "Nature",
                    2020, "1", "12345678", "10.1/x",
                    1, 2, 3, "X-RAY DIFFRACTION", 1.8, "ATP, MG",
                ],
                [
                    "2def", "Kinase Y NMR", "Roe, R.", "Another", "Cell",
                    2019, "2", "", "",
                    1, 2, 3, "SOLUTION NMR", 999999995904, "",
                ],
            ],
        }
        with respx.mock(using="httpx") as router:
            router.get("https://pdbj.org/rest/newweb/search/pdb").mock(
                return_value=httpx.Response(200, json=body)
            )
            result = json.loads(await search_pdb_entity("pdb", "kinase"))
        assert result["total"] == 2
        first = result["results"][0]
        assert first == {
            "id": "1abc", "title": "Kinase X", "method": "X-RAY DIFFRACTION",
            "resolution": 1.8, "ligands": "ATP, MG", "year": 2020,
            "pmid": "12345678", "doi": "10.1/x",
        }
        assert result["results"][1]["resolution"] is None  # NMR sentinel
        assert result["results"][1]["ligands"] is None      # empty -> None

    @pytest.mark.asyncio
    async def test_cc_projection_string_shape(self) -> None:
        """Free-text query: PDBj returns SMILES/InChI as ';'-separated str."""
        body = {
            "total": "1",
            "results": [[
                "CFF", "CAFFEINE", "C8 H10 N4 O2", "Cn1cnc2c1...;O=C2N...",
                "InChI=1S/C8H10N4O2/...", "SYSTEMATIC", "2000-05-16",
                "2020-06-17", "1,3,7-trimethyl...", "",
            ]],
        }
        with respx.mock(using="httpx") as router:
            router.get("https://pdbj.org/rest/newweb/search/cc").mock(
                return_value=httpx.Response(200, json=body)
            )
            result = json.loads(await search_pdb_entity("cc", "caffeine"))
        row = result["results"][0]
        assert row["id"] == "CFF"
        assert row["formula"] == "C8 H10 N4 O2"
        assert row["smiles"] == ["Cn1cnc2c1...", "O=C2N..."]
        assert row["inchi"] == "InChI=1S/C8H10N4O2/..."
        assert row["iupac_name"] == "1,3,7-trimethyl..."

    @pytest.mark.asyncio
    async def test_cc_projection_list_shape(self) -> None:
        """Structured-filter searches make PDBj return SMILES/InChI columns as
        JSON lists (not ';'-strings). Projecting them must not crash and must
        yield the same normalized shape. Regression for the formula/smiles
        'list object has no attribute split' bug."""
        body = {
            "total": -1,  # PDBj returns -1 (uncounted) for filter searches
            "results": [[
                "CFF", "CAFFEINE", "C8 H10 N4 O2",
                ["O=C2N(...)C", "Cn1cnc2N(...)c12"],          # smiles as list
                ["InChI=1S/C8H10N4O2/c1-10-..."],             # inchi as list
                ["3,7-DIHYDRO-..."],                          # syn as list
                "2000-05-16", "2020-06-17", "1,3,7-trimethyl...", None,
            ]],
        }
        with respx.mock(using="httpx") as router:
            router.get("https://pdbj.org/rest/newweb/search/cc").mock(
                return_value=httpx.Response(200, json=body)
            )
            result = json.loads(
                await search_pdb_entity("cc", "", formula="C8 H10 N4 O2")
            )
        assert result["total"] is None  # PDBj -1 ("uncounted") -> null
        row = result["results"][0]
        assert row["id"] == "CFF"
        assert row["smiles"] == ["O=C2N(...)C", "Cn1cnc2N(...)c12"]
        assert row["inchi"] == "InChI=1S/C8H10N4O2/c1-10-..."  # first of list

    @pytest.mark.asyncio
    async def test_cc_filter_forwarded(self) -> None:
        """formula/smiles filters reach PDBj; inchi is no longer accepted."""
        body = {"total": -1, "results": []}
        with respx.mock(using="httpx") as router:
            route = router.get("https://pdbj.org/rest/newweb/search/cc").mock(
                return_value=httpx.Response(200, json=body)
            )
            await search_pdb_entity("cc", "", formula="C8 H10 N4 O2")
        request = route.calls.last.request
        assert request.url.params["formula"] == "C8 H10 N4 O2"
        with pytest.raises(TypeError):  # inchi removed from the signature
            await search_pdb_entity("cc", "", inchi="InChI=1S/C8H10N4O2")

    @pytest.mark.asyncio
    async def test_filter_only_search_allowed(self) -> None:
        """An empty query is valid when a structured filter is supplied."""
        body = {"total": "0", "results": []}
        with respx.mock(using="httpx") as router:
            route = router.get("https://pdbj.org/rest/newweb/search/pdb").mock(
                return_value=httpx.Response(200, json=body)
            )
            await search_pdb_entity("pdb", "", method="em", res_max=3.0)
        request = route.calls.last.request
        assert request.url.params["method"] == "5"  # em -> code 5
        assert request.url.params["res_max"] == "3.0"

    @pytest.mark.asyncio
    async def test_no_criteria_raises(self) -> None:
        """No query and no filter is an error."""
        with pytest.raises(ValueError):
            await search_pdb_entity("pdb", "")

    @pytest.mark.asyncio
    async def test_unknown_method_raises_valueerror(self) -> None:
        """An out-of-enum method gives a clear ValueError, not a bare KeyError
        (the schema enum normally blocks this; guard is for drift/direct calls)."""
        with pytest.raises(ValueError, match="Unknown method"):
            await search_pdb_entity("pdb", "x", method="cryoem")


# ---------------------------------------------------------------------------
# Reactome
# ---------------------------------------------------------------------------


class TestSearchReactomeEntity:
    """Tests for search_reactome_entity with mocked HTTP."""

    _REACTOME_URL = "https://reactome.org/ContentService/search/query"

    @staticmethod
    def _entry(stid: str, name: str, typ: str, species: list[str], summ: str = "") -> dict:
        return {
            "stId": stid, "id": stid, "name": name, "type": typ,
            "exactType": typ, "species": species, "summation": summ,
        }

    def _payload(self, *entries: dict) -> dict:
        return {"results": [{"entries": list(entries)}]}

    # --- envelope / error contract (§4) ---

    @pytest.mark.asyncio
    async def test_http_error_returns_error_dict(self) -> None:
        """HTTP errors return a ChEMBL-style {'error': ...} dict, not results."""
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(500, text="Server Error")
            )
            result = await search_reactome_entity("apoptosis")
        assert isinstance(result, dict)
        assert "error" in result and "results" not in result
        assert "Reactome REST API request failed" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_results_envelope(self) -> None:
        """Empty results use the {total_count, has_more, results} envelope."""
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            result = await search_reactome_entity("apoptosis")
        assert result == {"total_count": 0, "has_more": False, "results": []}

    @pytest.mark.asyncio
    async def test_success_envelope_shape(self) -> None:
        """A hit returns total_count/has_more/results with the record fields."""
        entry = self._entry("R-HSA-109581", "Apoptosis", "Pathway", ["Homo sapiens"])
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(entry))
            )
            result = await search_reactome_entity("apoptosis")
        assert set(result) == {"total_count", "has_more", "results"}
        assert result["total_count"] == 1 and result["has_more"] is False
        assert result["results"][0]["id"] == "R-HSA-109581"

    # --- query / types validation ---

    @pytest.mark.asyncio
    async def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown Reactome type"):
            await search_reactome_entity("apoptosis", types="NotARealType")

    @pytest.mark.asyncio
    async def test_type_case_normalized(self) -> None:
        """A mis-cased valid type is normalized to canonical case before dispatch."""
        with respx.mock(using="httpx") as router:
            route = router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            await search_reactome_entity("apoptosis", types="pathway")
        assert route.calls.last.request.url.params["types"] == "Pathway"

    @pytest.mark.asyncio
    async def test_whitespace_query_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing search string"):
            await search_reactome_entity("   ")

    # --- §1 species case-normalization + §2 validation ---

    @pytest.mark.asyncio
    async def test_species_case_normalized_before_dispatch(self) -> None:
        """§1: a mis-cased species is normalized to canonical casing so the
        server-side (case-sensitive) filter actually engages."""
        with respx.mock(using="httpx") as router:
            route = router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            await search_reactome_entity("glycolysis", species="homo sapiens")
        assert route.calls.last.request.url.params["species"] == "Homo sapiens"

    @pytest.mark.asyncio
    async def test_invalid_species_raises(self) -> None:
        """§2: an unrecognized species raises — distinguishable from empty."""
        with pytest.raises(ValueError, match="Unknown Reactome species"):
            await search_reactome_entity("glycolysis", species="Not A Species")

    @pytest.mark.asyncio
    async def test_numeric_species_raises(self) -> None:
        """A numeric taxon id is not a valid species name -> raises."""
        with pytest.raises(ValueError, match="Unknown Reactome species"):
            await search_reactome_entity("glycolysis", species="9606")

    # --- client-side filter guarantees (belt-and-suspenders) ---

    @pytest.mark.asyncio
    async def test_species_filter_applied_client_side(self) -> None:
        """A VALID species whose server filter got relaxed (cross-species rows
        returned) is still honored client-side."""
        human = self._entry("R-HSA-1", "Apoptosis", "Pathway", ["Homo sapiens"])
        mouse = self._entry("R-MMU-1", "Apoptosis", "Pathway", ["Mus musculus"])
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(human, mouse))
            )
            result = await search_reactome_entity("apoptosis", species="Mus musculus")
        assert [r["id"] for r in result["results"]] == ["R-MMU-1"]

    @pytest.mark.asyncio
    async def test_type_filter_applied_client_side(self) -> None:
        pathway = self._entry("R-HSA-1", "Apoptosis", "Pathway", ["Homo sapiens"])
        reaction = self._entry("R-HSA-2", "Cleavage", "Reaction", ["Homo sapiens"])
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(pathway, reaction))
            )
            result = await search_reactome_entity("apoptosis", types="Pathway")
        assert [r["type"] for r in result["results"]] == ["Pathway"]

    # --- §3 overall cap + opt-in summation ---

    @pytest.mark.asyncio
    async def test_limit_caps_and_sets_has_more(self) -> None:
        """§3: limit is a true overall cap; has_more true when more matched."""
        entries = [
            self._entry(f"R-HSA-{i}", f"P{i}", "Pathway", ["Homo sapiens"])
            for i in range(5)
        ]
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(*entries))
            )
            result = await search_reactome_entity("kinase", limit=3)
        assert result["total_count"] == 3
        assert len(result["results"]) == 3
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_summation_opt_in(self) -> None:
        """§3: summation omitted by default, added (highlight-stripped) on request."""
        entry = self._entry(
            "R-HSA-1", "Apoptosis", "Pathway", ["Homo sapiens"],
            '<span class="highlighting" >Apoptosis</span> is cell death.',
        )
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(entry))
            )
            off = await search_reactome_entity("apoptosis")
        assert "summation" not in off["results"][0]
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(entry))
            )
            on = await search_reactome_entity("apoptosis", include_summation=True)
        assert on["results"][0]["summation"] == "Apoptosis is cell death."

    @pytest.mark.asyncio
    async def test_highlight_stripped_from_name(self) -> None:
        """<span> highlighting markup is stripped from the returned name."""
        entry = self._entry(
            "R-HSA-1",
            'The <span class="highlighting" >Apoptosis</span> pathway',
            "Pathway", ["Homo sapiens"],
        )
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(entry))
            )
            result = await search_reactome_entity("apoptosis")
        assert result["results"][0]["name"] == "The Apoptosis pathway"

    # --- §6 rows alias ---

    @pytest.mark.asyncio
    async def test_rows_alias_overrides_limit(self) -> None:
        """`rows` is a deprecated alias for the overall `limit` cap."""
        entries = [
            self._entry(f"R-HSA-{i}", f"P{i}", "Pathway", ["Homo sapiens"])
            for i in range(4)
        ]
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(*entries))
            )
            result = await search_reactome_entity("kinase", rows=2)
        assert result["total_count"] == 2 and result["has_more"] is True


# ---------------------------------------------------------------------------
# Rhea
# ---------------------------------------------------------------------------


class TestSearchRheaEntity:
    """Tests for search_rhea_entity with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_basic_search(self) -> None:
        """Successful Rhea search returns parsed TSV results."""
        tsv_body = (
            "Rhea ID\tEquation\n"
            "RHEA:10000\tATP + H2O = ADP + Pi\n"
            "RHEA:10001\tGlucose + ATP = G6P + ADP\n"
        )
        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(
                return_value=httpx.Response(200, text=tsv_body)
            )
            result = json.loads(await search_rhea_entity("ATP", limit=5))
        assert len(result) == 2
        assert result[0]["rhea_id"] == "RHEA:10000"
        assert "ATP" in result[0]["equation"]

    @pytest.mark.asyncio
    async def test_empty_response_same_shape(self) -> None:
        """An empty TSV response returns a bare JSON array `[]`, identical in
        shape to the non-empty case (Bug 3 regression)."""
        tsv_body = "Rhea ID\tEquation\n"
        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(
                return_value=httpx.Response(200, text=tsv_body)
            )
            result = json.loads(
                await search_rhea_entity("nonexistent_compound", limit=5)
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_negative_limit_raises(self) -> None:
        """A negative limit is rejected, not forwarded (Bug 1) — otherwise Rhea
        dumps the entire database."""
        with pytest.raises(ValueError, match="limit must be >= 0"):
            await search_rhea_entity("ATP", limit=-1)

    @pytest.mark.asyncio
    async def test_http_error_returns_error_array(self) -> None:
        """HTTP errors return a JSON string holding a one-element error array."""
        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(
                return_value=httpx.Response(500, text="Server Error")
            )
            result = json.loads(await search_rhea_entity("ATP"))
        assert isinstance(result, list)
        assert "Rhea REST API request failed" in result[0]["error"]
