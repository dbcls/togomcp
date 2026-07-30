"""Tests for togo_mcp.chembl — HTTP mocking with respx.

Split out of test_api_tools.py when the ChEMBL tools moved to togo_mcp.chembl.
The ChEMBL wrappers still ride on api_tools' shared REST plumbing, so the backoff
fixture patches api_tools._REST_BACKOFF_BASE (where _rest_get reads it), and
_strip_html is imported from api_tools where it now lives.
"""

import json

import httpx
import pytest
import respx

import togo_mcp.api_tools as api_tools
from togo_mcp.api_tools import _strip_html
from togo_mcp.chembl import (
    _containment_match_block,
    _resolve_spans,
    _UNIPROT_ACCESSION_RE,
    _bif_and,
    _bif_longest_token,
    _looks_like_structure,
    _sparql_literal,
    search_chembl_id_lookup,
    search_chembl_molecule,
    search_chembl_target,
)

# The RDF Portal SPARQL endpoint the ChEMBL tools resolve names against.
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
def _no_rest_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero the REST retry backoff so the retry-then-error tests don't sleep."""
    monkeypatch.setattr(api_tools, "_REST_BACKOFF_BASE", 0.0)


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

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "'bsynrymutxbxsq'"),  # longest block
            ("InChI=1S/C9H8O4/c1-6", "'c9h8o4'"),  # longest token (6 > 'inchi'=5)
            ("egfr", "'egfr'"),
            ("---", None),
        ],
    )
    def test_longest_token(self, text: str, expected: str | None) -> None:
        assert _bif_longest_token(text) == expected


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
        assert result["results"][0] == {"chembl_id": "CHEMBL941", "name": "IMATINIB"}

    @pytest.mark.asyncio
    async def test_smiles_uses_rest_flexmatch_not_sparql(self) -> None:
        # SMILES is toolkit-specific → REST flexmatch (chemistry engine), not
        # an exact SPARQL string match that would miss most real inputs.
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
    async def test_inchikey_resolves_via_sparql(self) -> None:
        # InChIKey is canonical → exact, CASE-SENSITIVE SPARQL match; no REST.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            sparql = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,name", "CHEMBL25,ASPIRIN")
                )
            )
            rest = router.get("https://www.ebi.ac.uk/chembl/api/data/molecule.json")
            result = await search_chembl_molecule("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        assert sparql.called and not rest.called
        sent = _sent_query(sparql)
        assert "CHEMINF_000059" in sent  # InChIKey value-node type
        assert 'FILTER(STR(?v) = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")' in sent  # case-sensitive
        assert "LCASE" not in sent
        assert "'bsynrymutxbxsq'" in sent  # longest-token prefilter (lowercased)
        assert result["results"][0]["chembl_id"] == "CHEMBL25"

    @pytest.mark.asyncio
    async def test_inchi_resolves_via_sparql(self) -> None:
        inchi = "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"
        with respx.mock(using="httpx", assert_all_called=False) as router:
            sparql = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,name", "CHEMBL25,ASPIRIN")
                )
            )
            rest = router.get("https://www.ebi.ac.uk/chembl/api/data/molecule.json")
            result = await search_chembl_molecule(inchi)
        assert sparql.called and not rest.called
        sent = _sent_query(sparql)
        assert "CHEMINF_000113" in sent  # InChI value-node type
        assert f'FILTER(STR(?v) = "{inchi}")' in sent
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
        assert result == {"total_count": 0, "has_more": False, "results": []}


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
        }

    @pytest.mark.asyncio
    async def test_invalid_target_type_raises(self) -> None:
        # An unrecognized enum value must fail loudly, not silently match 0 rows.
        with pytest.raises(ValueError, match="Invalid target_type"):
            await search_chembl_target("EGFR", target_type="BOGUS_TYPE")

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
    """Cross-entity resolution. Default UNIONs the four EXACT-name kinds
    (compound/target/cell_line/tissue); ASSAY is opt-in keyword-in-description."""

    @pytest.mark.asyncio
    async def test_default_unions_four_name_kinds(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,entity_type,name,organism",
                        "CHEMBL203,TARGET,Epidermal growth factor receptor,Homo sapiens",
                    ),
                )
            )
            result = await search_chembl_id_lookup("EGFR")
        sent = _sent_query(route)
        assert sent.count("UNION") == 3  # 4 branches
        for frag in ("cco:SmallMolecule", "cco:hasTargetComponent", "cco:CellLine",
                     "cco:Tissue"):
            assert frag in sent
        assert "cco:Assay" not in sent  # ASSAY excluded from the default UNION
        assert "cco:organismName" in sent  # organism carried for disambiguation
        assert result["results"][0]["entity_type"] == "TARGET"
        assert result["results"][0]["organism"] == "Homo sapiens"

    @pytest.mark.asyncio
    async def test_compound_organism_is_null(self) -> None:
        # Molecules have no organism → the branch must not bind it (null in output).
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv("chembl_id,entity_type,name,organism", "CHEMBL25,COMPOUND,ASPIRIN,"),
                )
            )
            result = await search_chembl_id_lookup("aspirin", entity_type="compound")
        sent = _sent_query(route)
        # only the non-compound branches carry organism; here there is one branch (compound)
        assert "cco:organismName" not in sent
        assert result["results"][0]["organism"] is None

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
    async def test_cell_line_uses_label_filter_no_prefilter(self) -> None:
        # Small type-constrained set → plain exact FILTER on rdfs:label, no
        # bif:contains prefilter needed.
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,entity_type,name", "CHEMBL3307278,CELL_LINE,CCRF S-180")
                )
            )
            result = await search_chembl_id_lookup("CCRF S-180", entity_type="cell_line")
        sent = _sent_query(route)
        assert "cco:CellLine" in sent
        assert "bif:contains" not in sent  # no prefilter for the small set
        assert 'FILTER(LCASE(STR(?alt)) = "ccrf s-180")' in sent
        assert result["results"][0]["chembl_id"] == "CHEMBL3307278"

    @pytest.mark.asyncio
    async def test_assay_keyword_in_description(self) -> None:
        # ASSAY does a keyword match on dcterms:description — bif:contains, and
        # crucially NO exact FILTER (descriptions are free text, not names). It
        # exposes `description` (not `name`) + a relevance `score`, ranked.
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,entity_type,description,organism,sc",
                        "CHEMBL641506,ASSAY,Inhibition of human acetylcholinesterase,,28",
                        "CHEMBL9,ASSAY,weaker match,,12",
                    ),
                )
            )
            result = await search_chembl_id_lookup(
                "acetylcholinesterase", entity_type="assay"
            )
        sent = _sent_query(route)
        assert "cco:Assay" in sent and "dcterms:description" in sent
        assert "FILTER(LCASE" not in sent  # keyword match, not exact
        # relevance-ranked via the bif:contains score
        assert "option (score ?sc)" in sent
        assert "ORDER BY DESC(?sc)" in sent
        assert "DISTINCT" not in sent  # DISTINCT would conflict with ORDER BY ?sc
        row = result["results"][0]
        assert row["entity_type"] == "ASSAY"
        assert row["name"] is None  # assays have no name
        assert row["description"] == "Inhibition of human acetylcholinesterase"
        assert row["score"] == 28  # populated + non-increasing
        assert result["results"][1]["score"] == 12

    @pytest.mark.asyncio
    async def test_has_more_true_when_over_limit(self) -> None:
        # Over-fetch by one: limit+1 rows returned → has_more True, page capped.
        with respx.mock(using="httpx") as router:
            router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,entity_type,name,organism",
                        "CHEMBL1,TISSUE,Liver,Rattus norvegicus",
                        "CHEMBL2,TISSUE,Liver,Homo sapiens",
                        "CHEMBL3,TISSUE,Liver,Mus musculus",  # the +1 over limit=2
                    ),
                )
            )
            result = await search_chembl_id_lookup("Liver", limit=2)
        assert result["has_more"] is True
        assert result["total_count"] == 2  # capped to limit
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_invalid_entity_type_raises(self) -> None:
        # DOCUMENT is explicitly unsupported; ASSAY is now valid.
        with pytest.raises(ValueError, match="Invalid entity_type"):
            await search_chembl_id_lookup("EGFR", entity_type="DOCUMENT")


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


class TestBiologicsAreNotDropped:
    """Regression: the name/structure lookups constrained matches to
    `?m a cco:SmallMolecule`, which silently dropped EVERY biologic — antibodies,
    therapeutic proteins, vaccines, oligos, cell therapies. Production logs for
    2026-07-27..29 showed 531/854 `search_chembl_molecule` calls returning zero
    rows; replaying the failures against a widened type set recovered 110 real
    drugs (efalizumab, Rituxan→RITUXIMAB, Nivolumab, filgrastim, …).
    """

    @pytest.mark.asyncio
    async def test_name_search_includes_biologic_types(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,name", "CHEMBL1201575,EFALIZUMAB")
                )
            )
            result = await search_chembl_molecule("efalizumab")
        sent = _sent_query(route)
        # Small molecules must still match, and the biologic branches too.
        for frag in ("cco:SmallMolecule", "cco:Antibody", "cco:ProteinMolecule",
                     "cco:UnknownSubstance", "cco:Vaccine", "cco:CellTherapy"):
            assert frag in sent, frag
        assert result["results"][0]["chembl_id"] == "CHEMBL1201575"

    @pytest.mark.asyncio
    async def test_molecule_search_excludes_target_components(self) -> None:
        # cco:TargetComponent also carries skos:altLabel; letting it into the
        # molecule type set would leak ~12.8k protein targets into drug results.
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(200, text=_csv("chembl_id,name"))
            )
            await search_chembl_molecule("EGFR")
        assert "cco:TargetComponent" not in _sent_query(route)

    @pytest.mark.asyncio
    async def test_inchikey_lookup_includes_biologic_types(self) -> None:
        # ~940k InChIKey-bearing substances are typed UnknownSubstance /
        # ProteinMolecule / Oligonucleotide / Oligosaccharide, not SmallMolecule.
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,name", "CHEMBL25,ASPIRIN")
                )
            )
            await search_chembl_molecule("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        sent = _sent_query(route)
        assert "CHEMINF_000059" in sent  # still the InChIKey value-node path
        for frag in ("cco:SmallMolecule", "cco:UnknownSubstance",
                     "cco:ProteinMolecule", "cco:Oligonucleotide"):
            assert frag in sent, frag

    @pytest.mark.asyncio
    async def test_id_lookup_compound_branch_includes_biologics(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv(
                        "chembl_id,entity_type,name,organism",
                        "CHEMBL1201575,COMPOUND,EFALIZUMAB,",
                    ),
                )
            )
            result = await search_chembl_id_lookup("efalizumab", entity_type="compound")
        sent = _sent_query(route)
        assert "cco:Antibody" in sent and "cco:SmallMolecule" in sent
        assert result["results"][0]["entity_type"] == "COMPOUND"


class TestExtractMode:
    """`mode='extract'` resolves substances NAMED INSIDE a string — the clinical-
    trial intervention strings exact matching cannot resolve by design. In the
    2026-07-27..29 logs, 420 of the 531 zero-row `search_chembl_molecule` calls
    were of this shape; extraction recovers 239 of them.
    """

    def test_spans_collapse_nested_synonyms(self) -> None:
        # "Sofpironium Bromide Gel" matches the full salt, the base, AND the bare
        # counter-ion. Longest-span-first must keep only SOFPIRONIUM BROMIDE.
        rows = [
            {"chembl_id": "CHEMBL3707223", "name": "SOFPIRONIUM BROMIDE",
             "alt": "sofpironium bromide"},
            {"chembl_id": "CHEMBL3707224", "name": "SOFPIRONIUM", "alt": "sofpironium"},
            {"chembl_id": "CHEMBL1231461", "name": "BROMIDE", "alt": "bromide"},
        ]
        out = _resolve_spans("Sofpironium Bromide Gel, 15%", rows)
        assert [r["chembl_id"] for r in out] == ["CHEMBL3707223"]
        assert out[0]["matched_span"] == "Sofpironium Bromide"
        assert out[0]["match_type"] == "contained"

    def test_spans_keep_distinct_components(self) -> None:
        # Non-overlapping spans are genuinely different drugs — keep them all.
        rows = [
            {"chembl_id": "CHEMBL1077896", "name": "ROPIVACAINE", "alt": "ropivacaine"},
            {"chembl_id": "CHEMBL134", "name": "CLONIDINE", "alt": "clonidine"},
        ]
        out = _resolve_spans("5 ml Ropivacaine 10% + Clonidine 1 ug/kg", rows)
        assert [r["name"] for r in out] == ["ROPIVACAINE", "CLONIDINE"]

    def test_spans_drop_unnamed_and_non_matching(self) -> None:
        rows = [
            # rdfs:label == its own ChEMBL id: carries no usable information.
            {"chembl_id": "CHEMBL4248195", "name": "CHEMBL4248195", "alt": "temozolomide"},
            {"chembl_id": "CHEMBL810", "name": "TEMOZOLOMIDE", "alt": "temozolomide"},
            # present in the row set but not actually a substring of the query
            {"chembl_id": "CHEMBL999", "name": "NOTHERE", "alt": "cisplatin"},
        ]
        out = _resolve_spans("Temozolomide 20 mg", rows)
        assert [r["chembl_id"] for r in out] == ["CHEMBL810"]

    def test_span_equal_to_whole_query_is_exact(self) -> None:
        rows = [{"chembl_id": "CHEMBL25", "name": "ASPIRIN", "alt": "aspirin"}]
        out = _resolve_spans("Aspirin", rows)
        assert out[0]["match_type"] == "exact"

    def test_containment_block_uses_or_and_length_floor(self) -> None:
        block = _containment_match_block("Ropivacaine 10% + Clonidine")
        assert " OR " in block  # any token may carry the drug (not AND)
        assert "STRLEN" in block and "CONTAINS(" in block
        # the exact-equality leg is OR'd back in so a short exact name survives
        assert "LCASE(STR(?alt)) =" in block

    @pytest.mark.asyncio
    async def test_extract_mode_collapses_case_variants_server_side(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200,
                    text=_csv("chembl_id,name,alt", "CHEMBL139,DICLOFENAC,diclofenac"),
                )
            )
            result = await search_chembl_molecule("Diclofenac SR", mode="extract")
        sent = _sent_query(route)
        # LCASE in the projection is what stops case-variants from eating the
        # row budget and silently dropping later components of a regimen.
        assert "LCASE(STR(?alt))" in sent
        assert result["mode"] == "extract"
        assert result["results"][0]["chembl_id"] == "CHEMBL139"

    @pytest.mark.asyncio
    async def test_exact_mode_is_unchanged_and_is_the_default(self) -> None:
        with respx.mock(using="httpx") as router:
            route = router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(
                    200, text=_csv("chembl_id,name", "CHEMBL25,ASPIRIN")
                )
            )
            result = await search_chembl_molecule("aspirin")
        sent = _sent_query(route)
        assert 'FILTER(LCASE(STR(?alt)) = "aspirin")' in sent  # still exact
        assert "mode" not in result  # exact returns the original shape
        assert result["results"][0] == {"chembl_id": "CHEMBL25", "name": "ASPIRIN"}

    @pytest.mark.asyncio
    async def test_empty_exact_result_explains_itself(self) -> None:
        # An empty result is otherwise indistinguishable from "not in ChEMBL".
        with respx.mock(using="httpx") as router:
            router.post(CHEMBL_SPARQL_URL).mock(
                return_value=httpx.Response(200, text=_csv("chembl_id,name"))
            )
            result = await search_chembl_molecule("Ustekinumab 90 mg")
        assert result["total_count"] == 0
        assert "extract" in result["note"]

    @pytest.mark.asyncio
    async def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown mode"):
            await search_chembl_molecule("aspirin", mode="fuzzy")
