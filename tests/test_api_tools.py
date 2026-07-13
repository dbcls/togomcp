"""Tests for togo_mcp.api_tools module — HTTP mocking with respx."""

import json

import httpx
import pytest
import respx

import togo_mcp.api_tools as api_tools
from togo_mcp.api_tools import (
    _UNIPROT_ACCESSION_RE,
    _bif_and,
    _looks_like_structure,
    _resolve_query_alias,
    _sparql_literal,
    _strip_html,
    search_chembl_id_lookup,
    search_chembl_molecule,
    search_chembl_target,
    search_pdb_entity,
    search_reactome_entity,
    search_rhea_entity,
    search_uniprot_entity,
)

# The RDF Portal SPARQL endpoint the ChEMBL tools now resolve names against.
CHEMBL_SPARQL_URL = "https://rdfportal.org/ebi/sparql"


def _csv(header: str, *rows: str) -> str:
    """Build a SPARQL CSV response body (header line + data rows)."""
    return "\n".join([header, *rows]) + ("\n" if rows else "")


def _sent_query(route) -> str:
    """Decode the SPARQL text from a captured form-encoded POST body."""
    import urllib.parse

    body = route.calls[0].request.content.decode()
    return urllib.parse.parse_qs(body)["query"][0]


@pytest.fixture(autouse=True)
def _no_chembl_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero the ChEMBL retry backoff so the retry-then-error tests don't sleep."""
    monkeypatch.setattr(api_tools, "_CHEMBL_BACKOFF_BASE", 0.0)


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


# ---------------------------------------------------------------------------
# ChEMBL
# ---------------------------------------------------------------------------


class TestBifAnd:
    """_bif_and turns caller text into a robust bif:contains argument: each
    alphanumeric token single-quoted, AND-joined. This survives what the raw
    forms 500 on — bare numerics and punctuation."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("egfr", "'egfr'"),
            ("EGFR", "'egfr'"),  # lowercased
            ("epidermal growth factor", "'epidermal' AND 'growth' AND 'factor'"),
            ("5'-nucleotidase", "'5' AND 'nucleotidase'"),  # numeric + apostrophe
            ("HER2/neu", "'her2' AND 'neu'"),  # slash
            ("ar", "'ar'"),  # 2-char
            ("", None),
            ("---", None),  # pure punctuation → no token
            ("   ", None),
        ],
    )
    def test_tokenize(self, text: str, expected: str | None) -> None:
        assert _bif_and(text) == expected


class TestSparqlLiteral:
    """_sparql_literal escapes for a double-quoted SPARQL string literal."""

    def test_escapes_quote_and_backslash(self) -> None:
        assert _sparql_literal('a"b') == 'a\\"b'
        assert _sparql_literal("a\\b") == "a\\\\b"
        assert _sparql_literal("plain") == "plain"


class TestUniprotAccessionRegex:
    """The accession regex routes target queries to the structured exactMatch
    path; it must accept real accessions and reject symbols / names / IDs."""

    @pytest.mark.parametrize(
        "text, is_accession",
        [
            ("P00533", True),
            ("Q9Y6K9", True),
            ("A0A024R161", True),  # 10-char form
            ("EGFR", False),
            ("TP53", False),
            ("CHEMBL25", False),
            ("aspirin", False),
        ],
    )
    def test_match(self, text: str, is_accession: bool) -> None:
        assert bool(_UNIPROT_ACCESSION_RE.match(text.upper())) is is_accession


class TestChemblStructureDetection:
    """_looks_like_structure classifies structure-shaped queries and — crucially
    — does NOT misclassify drug names / IDs / accessions (a false positive would
    misroute a real name to the structure endpoint and return nothing)."""

    @pytest.mark.parametrize(
        "query, expected",
        [
            ("CC(=O)Oc1ccccc1C(=O)O", "smiles"),  # aspirin SMILES
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "inchikey"),
            ("InChI=1S/C9H8O4/c1-6(10)13", "inchi"),
            ("aspirin", None),
            ("Dopamine receptor", None),  # multi-word name
            ("EGFR", None),
            ("CHEMBL25", None),
            ("P00533", None),  # UniProt accession
            ("Gleevec", None),
            ("CCO", None),  # bare-chain SMILES — accepted trade-off, treated as name
            ("", None),
        ],
    )
    def test_classification(self, query: str, expected: str | None) -> None:
        assert _looks_like_structure(query) == expected


class TestSearchChemblMolecule:
    """Molecule resolution: names go to SPARQL (exact altLabel); structure-shaped
    input goes to the REST chemistry engine."""

    @pytest.mark.asyncio
    async def test_name_resolves_via_sparql(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,name", "CHEMBL941,IMATINIB")
                )
            )
            result = await search_chembl_molecule("Gleevec")
        assert route.called
        sent = _sent_query(route)
        assert "skos:altLabel" in sent and "bif:contains" in sent
        assert "'gleevec'" in sent  # normalized bif token
        assert 'FILTER(LCASE(STR(?alt)) = "gleevec")' in sent  # exactness
        assert result["total_count"] == 1
        assert result["results"][0] == {
            "chembl_id": "CHEMBL941",
            "name": "IMATINIB",
            "score": None,
        }

    @pytest.mark.asyncio
    async def test_structure_uses_rest_not_sparql(self) -> None:
        body = {
            "page_meta": {"total_count": 3},
            "molecules": [{"molecule_chembl_id": "CHEMBL25", "pref_name": "ASPIRIN"}],
        }
        with respx.mock(using="httpx", assert_all_called=False) as router:
            rest = router.get(
                "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
            ).mock(return_value=httpx.Response(200, json=body))
            sparql = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(200, text=_csv("chembl_id,name"))
            )
            result = await search_chembl_molecule("CC(=O)Oc1ccccc1C(=O)O", limit=5)
        assert rest.called and not sparql.called
        assert "canonical_smiles__flexmatch" in str(rest.calls[0].request.url)
        assert result["results"][0]["chembl_id"] == "CHEMBL25"

    @pytest.mark.asyncio
    async def test_sparql_failure_returns_error_key(self) -> None:
        with respx.mock(using="httpx") as router:
            router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(500, text="boom")
            )
            result = await search_chembl_molecule("aspirin")
        assert "error" in result and "total_count" not in result

    @pytest.mark.asyncio
    async def test_untokenizable_query_returns_empty(self) -> None:
        # Pure punctuation → no bif token → empty, without hitting the endpoint.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            route = router.post(CHEMBL_SPARQL_URL)
            result = await search_chembl_molecule("---")
        assert not route.called
        assert result == {"total_count": 0, "results": []}


class TestSearchChemblTarget:
    """Target resolution: UniProt accession → structured skos:exactMatch; gene
    symbol / protein name → exact altLabel; both via SPARQL, no ranking."""

    @pytest.mark.asyncio
    async def test_accession_uses_exactmatch(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,name,organism,type",
                        "CHEMBL203,Epidermal growth factor receptor,Homo sapiens,SINGLE PROTEIN",
                    ),
                )
            )
            result = await search_chembl_target("P00533", target_type="SINGLE PROTEIN")
        sent = _sent_query(route)
        assert "skos:exactMatch <http://purl.uniprot.org/uniprot/P00533>" in sent
        assert "bif:contains" not in sent  # accession path skips text search
        assert 'FILTER(LCASE(STR(?type)) = "single protein")' in sent
        assert result["results"][0] == {
            "chembl_id": "CHEMBL203",
            "name": "Epidermal growth factor receptor",
            "organism": "Homo sapiens",
            "type": "SINGLE PROTEIN",
            "score": None,
        }

    @pytest.mark.asyncio
    async def test_symbol_uses_altlabel(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,name,organism,type",
                        "CHEMBL203,Epidermal growth factor receptor,Homo sapiens,SINGLE PROTEIN",
                    ),
                )
            )
            result = await search_chembl_target("EGFR", organism="Homo sapiens")
        sent = _sent_query(route)
        assert "skos:altLabel" in sent and "'egfr'" in sent
        assert 'FILTER(LCASE(STR(?alt)) = "egfr")' in sent
        assert 'CONTAINS(LCASE(STR(?organism)), "homo sapiens")' in sent
        assert result["results"][0]["chembl_id"] == "CHEMBL203"

    @pytest.mark.asyncio
    async def test_empty_organism_cell_becomes_none(self) -> None:
        with respx.mock(using="httpx") as router:
            router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,name,organism,type",
                        "CHEMBL999,Some target,,SINGLE PROTEIN",
                    ),
                )
            )
            result = await search_chembl_target("Something")
        assert result["results"][0]["organism"] is None

    @pytest.mark.asyncio
    async def test_sparql_failure_returns_error_key(self) -> None:
        with respx.mock(using="httpx") as router:
            router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(500, text="boom")
            )
            result = await search_chembl_target("EGFR")
        assert "error" in result and "total_count" not in result


class TestSearchChemblIdLookup:
    """Cross-entity resolution: UNION over compound + target branches, each an
    exact altLabel match; entity_type narrows to one branch."""

    @pytest.mark.asyncio
    async def test_default_unions_both(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,entity_type,name",
                        "CHEMBL203,TARGET,Epidermal growth factor receptor",
                    ),
                )
            )
            result = await search_chembl_id_lookup("EGFR")
        sent = _sent_query(route)
        assert "UNION" in sent
        assert "cco:SmallMolecule" in sent and "cco:hasTargetComponent" in sent
        assert result["results"][0]["entity_type"] == "TARGET"

    @pytest.mark.asyncio
    async def test_entity_type_compound_single_branch(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,entity_type,name")
                )
            )
            await search_chembl_id_lookup("aspirin", entity_type="compound")
        sent = _sent_query(route)
        assert "UNION" not in sent
        assert "cco:SmallMolecule" in sent and "cco:hasTargetComponent" not in sent

    @pytest.mark.asyncio
    async def test_invalid_entity_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid entity_type"):
            await search_chembl_id_lookup("EGFR", entity_type="ASSAY")


class TestChemblStructureRetryAndErrorCleaning:
    """The REST structure path keeps the retry/HTML-strip plumbing (EBI is flaky).
    Reached via a structure-shaped molecule query hitting /molecule.json."""

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        body = {
            "page_meta": {"total_count": 1},
            "molecules": [{"molecule_chembl_id": "CHEMBL25", "pref_name": "ASPIRIN"}],
        }
        with respx.mock(using="httpx") as router:
            route = router.get(
                "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
            ).mock(
                side_effect=[
                    httpx.Response(500, text="<html>err</html>"),
                    httpx.Response(200, json=body),
                ]
            )
            result = await search_chembl_molecule("CC(=O)Oc1ccccc1C(=O)O")
        assert route.call_count == 2
        assert result["results"][0]["chembl_id"] == "CHEMBL25"

    @pytest.mark.asyncio
    async def test_4xx_not_retried(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.get(
                "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
            ).mock(return_value=httpx.Response(404, text="<html>nope</html>"))
            result = await search_chembl_molecule("CC(=O)Oc1ccccc1C(=O)O")
        assert route.call_count == 1
        assert "error" in result

    @pytest.mark.asyncio
    async def test_error_body_is_html_free(self) -> None:
        html = (
            "<!doctype html><html><head><script>x=1</script>"
            "<style>a{color:red}</style></head><body>500 Internal Error</body></html>"
        )
        with respx.mock(using="httpx") as router:
            router.get(
                "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
            ).mock(return_value=httpx.Response(500, text=html))
            result = await search_chembl_molecule("CC(=O)Oc1ccccc1C(=O)O")
        assert "<" not in result["error"] and ">" not in result["error"]
        assert len(result["error"]) < 500

    def test_strip_html_collapses_and_truncates(self) -> None:
        html = "<div>  hello   <b>world</b> </div>"
        assert _strip_html(html) == "hello world"
        assert _strip_html("<p>" + "x" * 500 + "</p>", max_len=50).endswith("…")


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

    @pytest.mark.asyncio
    async def test_http_error_returns_error_array(self) -> None:
        """HTTP errors return a JSON string holding a one-element error array."""
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(500, text="Server Error")
            )
            result = json.loads(await search_reactome_entity("apoptosis"))
        assert isinstance(result, list)
        assert "Reactome REST API request failed" in result[0]["error"]

    @pytest.mark.asyncio
    async def test_empty_results_same_shape(self) -> None:
        """Empty results are a bare JSON array, identical in shape to non-empty
        (Bug 3 regression)."""
        with respx.mock(using="httpx") as router:
            router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            result = json.loads(await search_reactome_entity("apoptosis"))
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_type_raises(self) -> None:
        """An unknown / mis-cased `types` value raises rather than silently
        returning unfiltered results (Bug 2)."""
        with pytest.raises(ValueError, match="Unknown Reactome type"):
            await search_reactome_entity("apoptosis", types="NotARealType")

    @pytest.mark.asyncio
    async def test_type_case_normalized(self) -> None:
        """A mis-cased but valid type is normalized to canonical case and sent
        to the API (Bug 2)."""
        with respx.mock(using="httpx") as router:
            route = router.get(self._REACTOME_URL).mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            await search_reactome_entity("apoptosis", types="pathway")
        assert route.calls.last.request.url.params["types"] == "Pathway"

    @pytest.mark.asyncio
    async def test_whitespace_query_raises(self) -> None:
        """A whitespace-only query is treated as empty (Bug 4)."""
        with pytest.raises(ValueError, match="Missing search string"):
            await search_reactome_entity("   ")


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
