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
    async def test_zero_match_404_returns_empty_not_error(self) -> None:
        """Reactome signals 'no matches' as HTTP 404 (NOT_FOUND); that must map to
        an empty result set, NOT an {'error': ...} the caller reads as a failure."""
        body = (
            '{"code":404,"reason":"NOT_FOUND","url":"http://reactome.org/'
            'ContentService/search/query","messages":["No entries found for '
            'query: zzqxwvfoobarnotreal"],"targets":null}'
        )
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(404, text=body)
            )
            result = await search_reactome_entity("zzqxwvfoobarnotreal")
        assert result == {"total_count": 0, "has_more": False, "results": []}

    @pytest.mark.asyncio
    async def test_other_404_is_still_an_error(self) -> None:
        """A non-JSON 404 (e.g. an HTML 'Not Found' page from a renamed path) is
        NOT the no-match signal and stays a genuine error."""
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(404, text="<html>404 Not Found</html>")
            )
            result = await search_reactome_entity("apoptosis")
        assert "error" in result and "results" not in result

    @pytest.mark.asyncio
    async def test_404_json_but_not_no_match_is_error(self) -> None:
        """The guard keys on the message, not just status+reason: a JSON 404 with
        reason NOT_FOUND but a different message (e.g. an endpoint/API migration)
        must stay an error — otherwise every query would silently return empty
        while the tool looked healthy."""
        body = (
            '{"code":404,"reason":"NOT_FOUND",'
            '"messages":["HTTP 404 Not Found"],"targets":null}'
        )
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(404, text=body)
            )
            result = await search_reactome_entity("apoptosis")
        assert "error" in result and "results" not in result

    @pytest.mark.asyncio
    async def test_limit_rows_conflict_raises(self) -> None:
        """`limit` and `rows` are aliases; conflicting values raise (like the
        query-alias conflict check), rather than silently picking one."""
        with pytest.raises(ValueError, match="only one of `limit` and `rows`"):
            await search_reactome_entity("kinase", limit=10, rows=5)

    @pytest.mark.asyncio
    async def test_summation_capped_at_240(self) -> None:
        """A long summation is truncated so the returned value is ≤240 chars
        (240 + ellipsis was 241 — the documented cap is 240)."""
        entry = self._entry(
            "R-HSA-1", "Apoptosis", "Pathway", ["Homo sapiens"], "x" * 500
        )
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json=self._payload(entry))
            )
            result = await search_reactome_entity("apoptosis", include_summation=True)
        assert len(result["results"][0]["summation"]) <= 240

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
        """Successful Rhea search returns an envelope of parsed TSV results."""
        tsv_body = (
            "Rhea ID\tEquation\n"
            "RHEA:10000\tATP + H2O = ADP + Pi\n"
            "RHEA:10001\tGlucose + ATP = G6P + ADP\n"
        )
        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(
                return_value=httpx.Response(200, text=tsv_body)
            )
            result = await search_rhea_entity("ATP", limit=5)
        assert result["total_count"] == 2
        assert result["has_more"] is False
        assert result["results"][0]["rhea_id"] == "RHEA:10000"
        assert "ATP" in result["results"][0]["equation"]

    @pytest.mark.asyncio
    async def test_empty_response_same_shape(self) -> None:
        """An empty TSV response returns the same envelope with an empty list,
        so empty and non-empty share one shape."""
        tsv_body = "Rhea ID\tEquation\n"
        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(
                return_value=httpx.Response(200, text=tsv_body)
            )
            result = await search_rhea_entity("nonexistent_compound", limit=5)
        assert result == {"total_count": 0, "has_more": False, "results": []}

    @pytest.mark.asyncio
    async def test_has_more_boundary(self) -> None:
        """has_more is boundary-correct: over-fetching limit+1 detects overflow.
        With 3 matching rows, limit=2 -> has_more True and 2 rows returned."""
        tsv_body = (
            "Rhea ID\tEquation\n"
            "RHEA:1\ta\nRHEA:2\tb\nRHEA:3\tc\n"  # server returns limit+1 = 3
        )
        captured = {}
        with respx.mock(using="httpx") as router:
            def _capture(request: httpx.Request) -> httpx.Response:
                captured["limit"] = request.url.params.get("limit")
                return httpx.Response(200, text=tsv_body)

            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_capture)
            result = await search_rhea_entity("glucose", limit=2)
        assert captured["limit"] == "3"  # over-fetched by one
        assert result["has_more"] is True
        assert result["total_count"] == 2
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_empty_query_raises(self) -> None:
        """A blank query raises rather than dumping an arbitrary slice of the DB
        (§1 silent-wrong-answer guard)."""
        with pytest.raises(ValueError, match="Missing search string"):
            await search_rhea_entity()
        with pytest.raises(ValueError, match="Missing search string"):
            await search_rhea_entity(query="")

    @pytest.mark.asyncio
    async def test_negative_limit_raises(self) -> None:
        """A negative limit is rejected, not forwarded — otherwise Rhea dumps
        the entire database."""
        with pytest.raises(ValueError, match="limit must be between 0 and 500"):
            await search_rhea_entity("ATP", limit=-1)

    @pytest.mark.asyncio
    async def test_limit_over_ceiling_raises(self) -> None:
        """A limit above the ceiling raises — no single call can return a
        six-figure-token payload (§2)."""
        with pytest.raises(ValueError, match="limit must be between 0 and 500"):
            await search_rhea_entity("glucose", limit=20000)

    @pytest.mark.asyncio
    async def test_http_error_returns_error_dict(self) -> None:
        """HTTP errors return an {'error': ...} dict, same type as success."""
        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(
                return_value=httpx.Response(500, text="Server Error")
            )
            result = await search_rhea_entity("ATP")
        assert isinstance(result, dict)
        assert "Rhea REST API request failed" in result["error"]

    @pytest.mark.asyncio
    async def test_custom_columns_parsed_by_position(self) -> None:
        """Extra columns are mapped to friendly keys by position (the TSV header
        carries display labels, not column IDs, so position is the only anchor)."""
        tsv_body = (
            "Reaction identifier\tEC number\tCross-reference (KEGG)\n"
            "RHEA:10736\tEC:1.1.1.1;EC:1.1.1.71\tKEGG:R00623\n"
        )
        captured = {}
        with respx.mock(using="httpx") as router:
            def _capture(request: httpx.Request) -> httpx.Response:
                captured["columns"] = request.url.params.get("columns")
                return httpx.Response(200, text=tsv_body)

            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_capture)
            result = await search_rhea_entity(
                "ec:1.1.1.1", columns="rhea-id,ec,reaction-xref(KEGG)"
            )
        assert captured["columns"] == "rhea-id,ec,reaction-xref(KEGG)"
        assert result["results"][0] == {
            "rhea_id": "RHEA:10736",
            "ec": "EC:1.1.1.1;EC:1.1.1.71",
            "xref_kegg": "KEGG:R00623",
        }

    @pytest.mark.asyncio
    async def test_columns_accepts_list(self) -> None:
        """`columns` may be a list of IDs, deduped in caller order."""
        tsv_body = "Reaction identifier\tEquation\nRHEA:10000\tATP + H2O = ADP + Pi\n"
        captured = {}
        with respx.mock(using="httpx") as router:
            def _capture(request: httpx.Request) -> httpx.Response:
                captured["columns"] = request.url.params.get("columns")
                return httpx.Response(200, text=tsv_body)

            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_capture)
            result = await search_rhea_entity(
                "ATP", columns=["rhea-id", "equation", "rhea-id"]
            )
        assert captured["columns"] == "rhea-id,equation"
        assert result["results"][0]["rhea_id"] == "RHEA:10000"

    @pytest.mark.asyncio
    async def test_columns_case_insensitive(self) -> None:
        """`columns` matches case-insensitively and normalizes to canonical
        casing before dispatch (§5) — RHEA-ID behaves like rhea-id."""
        tsv_body = "Reaction identifier\nRHEA:10000\n"
        captured = {}
        with respx.mock(using="httpx") as router:
            def _capture(request: httpx.Request) -> httpx.Response:
                captured["columns"] = request.url.params.get("columns")
                return httpx.Response(200, text=tsv_body)

            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_capture)
            result = await search_rhea_entity("ATP", columns="RHEA-ID")
        assert captured["columns"] == "rhea-id"  # normalized to canonical
        assert result["results"][0] == {"rhea_id": "RHEA:10000"}

    @pytest.mark.asyncio
    async def test_projection_does_not_change_row_set(self) -> None:
        """`columns` is a projection over FIELDS, never ROWS: total_count and
        has_more must be invariant under `columns`, even when the projected
        column is empty on every row. Regression for the sparse-column row-drop
        that silently collapsed total_count/has_more to 0/false."""
        _KEY = {
            "rhea-id": "rhea_id", "equation": "equation", "chebi": "chebi",
            "chebi-id": "chebi_id", "ec": "ec", "uniprot": "uniprot",
            "go": "go", "pubmed": "pubmed",
            "reaction-xref(EcoCyc)": "xref_ecocyc",
            "reaction-xref(KEGG)": "xref_kegg",
            "reaction-xref(MetaCyc)": "xref_metacyc",
            "reaction-xref(Reactome)": "xref_reactome",
            "reaction-xref(M-CSA)": "xref_mcsa",
        }

        def _mock(request: httpx.Request) -> httpx.Response:
            # Worst case: rhea-id anchor populated, every OTHER column blank.
            fetched = request.url.params.get("columns").split(",")
            header = "\t".join(f"h_{c}" for c in fetched)
            body = "\n".join(
                "\t".join(rid if c == "rhea-id" else "" for c in fetched)
                for rid in ("RHEA:1", "RHEA:2", "RHEA:3")
            )
            return httpx.Response(200, text=f"{header}\n{body}\n")

        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_mock)
            for col in _KEY:
                r = await search_rhea_entity("glucose", limit=10, columns=col)
                assert r["total_count"] == 3, col
                assert r["has_more"] is False, col
                assert len(r["results"]) == 3, col
                # every requested column present as a key on every row, blank ok
                assert all(_KEY[col] in row for row in r["results"]), col

    @pytest.mark.asyncio
    async def test_sparse_column_still_returns_rows(self) -> None:
        """The pathological case: projecting onto only a sparse xref column must
        still return the matched rows (with the xref blank), not an empty
        envelope. rhea-id is fetched as an anchor to keep rows countable."""
        captured = {}

        def _mock(request: httpx.Request) -> httpx.Response:
            captured["columns"] = request.url.params.get("columns")
            # Rhea emits an all-blank data line per row for a sole sparse column;
            # the anchor makes the tool fetch rhea-id too, so each line has content.
            return httpx.Response(
                200,
                text=(
                    "Reaction identifier\tCross-reference (Reactome)\n"
                    "RHEA:14293\t\nRHEA:14405\t\nRHEA:22152\t\n"
                ),
            )

        with respx.mock(using="httpx") as router:
            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_mock)
            r = await search_rhea_entity(
                "glucose", limit=2, columns="reaction-xref(Reactome)"
            )
        # anchor prepended to the outgoing request
        assert captured["columns"] == "rhea-id,reaction-xref(Reactome)"
        assert r["total_count"] == 2
        assert r["has_more"] is True  # 3 matched > limit 2
        assert all("xref_reactome" in row for row in r["results"])
        # projected down to ONLY the requested column (anchor dropped from output)
        assert r["results"][0] == {"xref_reactome": ""}

    @pytest.mark.asyncio
    async def test_chebi_double_prefix_collapsed(self) -> None:
        """A canonically-prefixed ChEBI id in a chebi:-scoped term (chebi:CHEBI:
        17234) is collapsed to the bare form the API accepts, avoiding an opaque
        upstream 500 (§2). Case-insensitive on both the scope and the prefix."""
        tsv_body = "Reaction identifier\nRHEA:10076\n"
        captured = {}
        with respx.mock(using="httpx") as router:
            def _capture(request: httpx.Request) -> httpx.Response:
                captured["query"] = request.url.params.get("query")
                return httpx.Response(200, text=tsv_body)

            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_capture)
            await search_rhea_entity("chebi:CHEBI:17234", columns="rhea-id")
        assert captured["query"] == "chebi:17234"

        with respx.mock(using="httpx") as router:
            def _capture2(request: httpx.Request) -> httpx.Response:
                captured["query"] = request.url.params.get("query")
                return httpx.Response(200, text=tsv_body)

            router.get("https://www.rhea-db.org/rhea").mock(side_effect=_capture2)
            await search_rhea_entity("CHEBI:CHEBI:17234", columns="rhea-id")
        assert captured["query"] == "chebi:17234"

    @pytest.mark.asyncio
    async def test_unknown_column_raises(self) -> None:
        """An invalid column is rejected, not forwarded — the API would silently
        drop it and return a narrower table without warning."""
        with pytest.raises(ValueError, match="Unknown Rhea column"):
            await search_rhea_entity("ATP", columns="rhea-id,bogus")

    @pytest.mark.asyncio
    async def test_empty_columns_raises(self) -> None:
        """A columns value naming no valid field is rejected."""
        with pytest.raises(ValueError, match="at least one valid Rhea column"):
            await search_rhea_entity("ATP", columns=" , ")
