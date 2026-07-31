"""Tests for togo_mcp.kegg — pure helpers plus respx-mocked tools.

NO TEST HERE TOUCHES rest.kegg.jp. The KEGG API is licensed to academic users at
academic institutions, and this suite runs in CI, so every request is mocked with
respx and every KGML input is the synthetic fixture (tests/fixtures/
kgml_pitfalls.xml), which contains no KEGG-derived content.

The `@kegg_mcp.tool()` decorator returns the original coroutine, so the tool
functions are awaited directly, as in test_togovar.py.
"""

import asyncio
import json
import time
from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import FastMCP

import togo_mcp.kegg as kegg
from togo_mcp.kegg import _MAX_GRAPH_RESPONSE_CHARS as _MAX_GRAPH_CAP
import togo_mcp.main as main
from togo_mcp.kegg import (
    _as_list,
    _bounded,
    _check_path_token,
    _normalize_pathway,
    _parse_flat_file,
    _parse_tsv_pairs,
    conv,
    find,
    get_entry,
    link,
    pathway_cycles,
    pathway_graph,
    pathway_neighborhood,
    pathway_paths,
)

BASE = "https://rest.kegg.jp"
FIXTURE = Path(__file__).parent / "fixtures" / "kgml_pitfalls.xml"
KGML = FIXTURE.read_text()
# The fixture declares itself as org "xxx", map number 00000.
MAP = "xxx00000"


def _synthetic_global_map(*, gaps: int, map_links: int, genes: int) -> str:
    """A whole-metabolism map's SHAPE, with no KEGG-derived content.

    hsa01100 is thousands of unreacted ortholog boxes (metabolic gaps) and
    hundreds of cross-map pointers wrapped around a connected core — the only
    shape in which the response caps compete for the budget at all.
    """
    entries, relations = [], []
    for i in range(gaps):
        entries.append(
            f'<entry id="{90000 + i}" name="ko:K{i:05d}" type="ortholog">'
            f'<graphics name="{i}.{i}.{i}.{i}" type="rectangle"/></entry>'
        )
    for i in range(map_links):
        entries.append(
            f'<entry id="{40000 + i}" name="path:map{i:05d}" type="map">'
            f'<graphics name="Other pathway {i}" type="roundrectangle"/></entry>'
        )
    for i in range(genes):
        entries.append(
            f'<entry id="{i + 1}" name="hsa:{i} hsa:{i + 9000}" type="gene">'
            f'<graphics name="GENE{i}, ALIAS{i}" type="rectangle"/></entry>'
        )
        if i:
            relations.append(
                f'<relation entry1="{i}" entry2="{i + 1}" type="PPrel">'
                '<subtype name="activation" value="--&gt;"/></relation>'
            )
    return (
        '<?xml version="1.0"?><pathway name="path:xxx01100" org="xxx" '
        'number="01100" title="Synthetic global map">'
        + "".join(entries) + "".join(relations) + "</pathway>"
    )


def _assert_graph_invariants(payload: str, graph: dict) -> None:
    """The three properties that must hold on EVERY kegg_pathway_graph return.

    They are asserted together, on every reduction path (count cap, size cap,
    neither), because each was a shipped bug: edges pointing at nodes that were
    cut, and a payload over the 1 MB transport limit that the caller never
    received at all.
    """
    node_ids = {n["id"] for n in graph["nodes"]}
    assert all(
        e["source"] in node_ids and e["target"] in node_ids for e in graph["edges"]
    ), "dangling edge: an endpoint is missing from `nodes`"
    assert len(payload.encode()) < 1_048_576, (
        f"payload is {len(payload.encode())} bytes — over the 1 MB transport limit"
    )
    touched = {e["source"] for e in graph["edges"]} | {
        e["target"] for e in graph["edges"]
    }
    if graph["edges"]:
        assert len(node_ids - touched) <= len(node_ids) / 2, (
            "more than half the returned nodes are isolated"
        )


@pytest.fixture(autouse=True)
def _isolate_module_state(monkeypatch):
    """Clear the KGML memo and disable throttling between tests.

    The rate limiter and the KGML cache are deliberately module-level (the 3
    req/s cap is process-wide, not per-tool), so tests must reset them or they
    leak across cases and add ~1/3 s of real sleep per mocked request. The
    limiter itself is exercised explicitly in TestRateLimit.
    """
    kegg._kgml_cache.clear()
    kegg._symbol_cache.clear()
    monkeypatch.setattr(kegg, "_MIN_INTERVAL", 0.0)
    monkeypatch.setattr(kegg, "_last_request_at", 0.0)
    monkeypatch.setattr(kegg, "_BACKOFF_BASE", 0.0)


# --------------------------------------------------------------------------- #
# Pure helpers — no HTTP
# --------------------------------------------------------------------------- #
class TestPureHelpers:
    def test_as_list_splits_the_separators_an_llm_actually_uses(self):
        assert _as_list("hsa:10458") == ["hsa:10458"]
        assert _as_list("hsa:10458,hsa:5290") == ["hsa:10458", "hsa:5290"]
        assert _as_list("hsa:10458, hsa:5290") == ["hsa:10458", "hsa:5290"]
        # KEGG's own '+' joiner must round-trip.
        assert _as_list("hsa:10458+hsa:5290") == ["hsa:10458", "hsa:5290"]
        assert _as_list(["hsa:10458", "hsa:5290"]) == ["hsa:10458", "hsa:5290"]
        assert _as_list("") == []
        assert _as_list([]) == []

    def test_check_path_token_rejects_path_altering_input(self):
        assert _check_path_token(" hsa:10458 ", label="entry") == "hsa:10458"
        for bad in ("a/b", "../get", "two words"):
            with pytest.raises(ValueError, match="Invalid entry"):
                _check_path_token(bad, label="entry")
        with pytest.raises(ValueError, match="must not be empty"):
            _check_path_token("", label="entry")

    def test_normalize_pathway_accepts_the_forms_kegg_itself_emits(self):
        # /link returns pathways prefixed; users type them bare.
        assert _normalize_pathway("path:hsa04151") == "hsa04151"
        assert _normalize_pathway("hsa04151") == "hsa04151"
        assert _normalize_pathway("ko00010") == "ko00010"
        assert _normalize_pathway("map00010") == "map00010"
        assert _normalize_pathway("eco00010") == "eco00010"

    @pytest.mark.parametrize("bad", ["hsa", "04151", "hsa4151", "hsa004151", "C00031"])
    def test_normalize_pathway_rejects_non_map_ids(self, bad):
        with pytest.raises(ValueError, match="Invalid pathway id"):
            _normalize_pathway(bad)

    def test_parse_flat_file_keeps_multiline_fields_as_lists(self):
        text = (
            "ENTRY       C00031                      Compound\n"
            "NAME        D-Glucose;\n"
            "            Grape sugar;\n"
            "FORMULA     C6H12O6\n"
            "EXACT_MASS  180.0634\n"
            "///\n"
        )
        (record,) = _parse_flat_file(text)
        assert record["entry_id"] == "C00031"
        assert record["entry_type"] == "Compound"
        # Every value is a list, including the single-line ones: the shape must
        # not depend on the data.
        assert record["fields"]["NAME"] == ["D-Glucose;", "Grape sugar;"]
        assert record["fields"]["FORMULA"] == ["C6H12O6"]
        assert record["fields"]["EXACT_MASS"] == ["180.0634"]

    def test_parse_flat_file_splits_multiple_records(self):
        text = "ENTRY       C00031\n///\nENTRY       C00022\n///\n"
        records = _parse_flat_file(text)
        assert [r["entry_id"] for r in records] == ["C00031", "C00022"]

    def test_parse_flat_file_handles_field_names_past_column_11(self):
        """Fixed-width slicing at column 12 truncates the longer field names."""
        text = "ENTRY       hsa00010\nCARBOHYDRATE_X  value here\n///\n"
        (record,) = _parse_flat_file(text)
        assert record["fields"]["CARBOHYDRATE_X"] == ["value here"]

    def test_parse_tsv_pairs(self):
        assert _parse_tsv_pairs("hsa:10458\tpath:hsa04810\n\n") == [
            ("hsa:10458", "path:hsa04810")
        ]
        assert _parse_tsv_pairs("") == []

    def test_bounded_reports_truncation_instead_of_silently_dropping(self):
        payload = [{"entry": f"C{i:05d}", "definition": "x" * 200} for i in range(2000)]
        parsed = json.loads(_bounded(payload, note="narrow it"))
        assert parsed["truncated"]["total"] == 2000
        assert parsed["truncated"]["returned"] == len(parsed["results"])
        assert parsed["truncated"]["returned"] < 2000

    def test_bounded_passes_small_payloads_through_as_a_bare_array(self):
        out = _bounded([{"entry": "C00031"}], note="")
        assert json.loads(out) == [{"entry": "C00031"}]


# --------------------------------------------------------------------------- #
# find
# --------------------------------------------------------------------------- #
class TestFind:
    @pytest.mark.asyncio
    async def test_returns_bare_json_array_and_joins_keywords_with_plus(self):
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/find/compound/grape+sugar").mock(
                return_value=httpx.Response(
                    200, text="cpd:C00031\tD-Glucose; Grape sugar\n"
                )
            )
            out = await find(database="compound", query="grape sugar")
        assert route.called
        # Both forms ship: `entry` verbatim (what KEGG tools take), `entry_id`
        # prefix-stripped (what downstream/RDF tools take) — same contract as
        # kegg_conv's source_id/target_id, so a caller never has to guess.
        assert json.loads(out) == [
            {
                "entry": "cpd:C00031",
                "entry_id": "C00031",
                "definition": "D-Glucose; Grape sugar",
            }
        ]

    @pytest.mark.asyncio
    async def test_empty_body_is_no_match_not_an_error(self):
        """KEGG answers 'nothing matched' with an empty HTTP 200, never a 404."""
        with respx.mock(using="httpx") as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            out = await find(database="compound", query="notathing")
        assert out == "[]"

    @pytest.mark.asyncio
    async def test_limit_trims_client_side(self):
        body = "".join(f"cpd:C{i:05d}\tname {i}\n" for i in range(50))
        with respx.mock(using="httpx") as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=body))
            out = await find(database="compound", query="x", limit=5)
        assert len(json.loads(out)) == 5

    @pytest.mark.asyncio
    async def test_organism_code_is_accepted_as_a_database(self):
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/find/hsa/kinase").mock(
                return_value=httpx.Response(200, text="hsa:10458\tBAIAP2\n")
            )
            await find(database="hsa", query="kinase")
        assert route.called

    @pytest.mark.asyncio
    async def test_unknown_database_raises_without_calling_kegg(self):
        # assert_all_called=False: the catch-all route exists precisely so the
        # test can assert it stays UNCALLED.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            with pytest.raises(ValueError, match="Unknown KEGG database"):
                await find(database="proteins", query="x")
            assert not router.calls

    @pytest.mark.asyncio
    async def test_blank_query_raises(self):
        with pytest.raises(ValueError, match="Missing search term"):
            await find(database="compound", query="")

    @pytest.mark.asyncio
    async def test_option_is_appended_and_validated(self):
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/find/compound/C6H12O6/formula").mock(
                return_value=httpx.Response(200, text="cpd:C00031\tC6H12O6\n")
            )
            await find(database="compound", query="C6H12O6", option="formula")
        assert route.called

        with pytest.raises(ValueError, match="Unknown find option"):
            await find(database="compound", query="x", option="mass")
        # A chemical-only option against a gene database is a caller error, not
        # something to discover as an upstream 400.
        with pytest.raises(ValueError, match="applies only to the chemical databases"):
            await find(database="hsa", query="x", option="formula")


# --------------------------------------------------------------------------- #
# get_entry
# --------------------------------------------------------------------------- #
class TestGetEntry:
    @pytest.mark.asyncio
    async def test_parses_flat_file_into_entry_objects(self):
        body = (
            "ENTRY       C00031                      Compound\n"
            "NAME        D-Glucose\n"
            "DBLINKS     ChEBI: 4167\n"
            "            PubChem: 3333\n"
            "///\n"
        )
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/get/C00031").mock(
                return_value=httpx.Response(200, text=body)
            )
            out = await get_entry(entries="C00031")
        assert route.called
        (record,) = json.loads(out)
        assert record["entry_id"] == "C00031"
        assert record["fields"]["DBLINKS"] == ["ChEBI: 4167", "PubChem: 3333"]

    @pytest.mark.asyncio
    async def test_more_than_ten_entries_raises_before_any_request(self):
        """KEGG's documented per-request cap; catching it here saves a 400."""
        # assert_all_called=False: the catch-all route exists precisely so the
        # test can assert it stays UNCALLED.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            with pytest.raises(ValueError, match="at most 10 entries"):
                await get_entry(entries=[f"C{i:05d}" for i in range(11)])
            assert not router.calls

    @pytest.mark.asyncio
    async def test_empty_response_is_an_empty_array(self):
        with respx.mock(using="httpx") as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            assert await get_entry(entries="C99999") == "[]"

    @pytest.mark.asyncio
    async def test_sequence_option_returns_fasta_records(self):
        body = ">hsa:10458 BAIAP2  (RefSeq) BAR/IMD domain\nMSLSRSEE\nMHRLKQ\n"
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/get/hsa:10458/aaseq").mock(
                return_value=httpx.Response(200, text=body)
            )
            out = await get_entry(entries="hsa:10458", sequence="aaseq")
        assert route.called
        (record,) = json.loads(out)
        assert record["entry_id"] == "hsa:10458"
        assert record["sequence"] == "MSLSRSEEMHRLKQ"

    @pytest.mark.asyncio
    async def test_kgml_is_not_reachable_through_the_sequence_option(self):
        """Raw KGML is never returned: it costs tokens and an LLM cannot read it."""
        with pytest.raises(ValueError, match="Unknown sequence option"):
            await get_entry(entries="hsa04151", sequence="kgml")


# --------------------------------------------------------------------------- #
# pathway_graph / pathway_neighborhood
# --------------------------------------------------------------------------- #
def _mock_kgml(router, body: str = KGML):
    return router.get(f"{BASE}/get/{MAP}/kgml").mock(
        return_value=httpx.Response(200, text=body)
    )


def _mock_symbol_lookup(router, rows: str = ""):
    """The `/find/<org>/<symbol>` fallback for a seed KGML cannot resolve.

    KEGG answers "no match" with an empty HTTP 200, which is the default here.
    """
    return router.get(url__regex=rf"{BASE}/find/xxx/.*").mock(
        return_value=httpx.Response(200, text=rows)
    )


class TestPathwayGraph:
    @pytest.mark.asyncio
    async def test_returns_a_signed_graph_with_the_mandated_caveat_fields(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_graph(pathway=MAP)
        graph = json.loads(out)

        assert graph["pathway"]["id"] == MAP
        assert graph["nodes"] and graph["edges"]
        # Handoff 6.2: signed fraction and fragmentation must always ship, so the
        # caller can tell how much of the sign information actually exists.
        sq = graph["signal_quality"]
        assert sq["signed_edge_count"] <= sq["edge_count"]
        assert 0.0 <= sq["signed_edge_fraction"] <= 1.0
        assert sq["component_count"] >= 1 and sq["largest_component"] >= 1
        assert len(sq["caveats"]) == 2
        assert "metabolic_gaps" in graph and "metabolic_gaps_note" in graph
        assert {e["sign"] for e in graph["edges"]} <= {-1, 0, 1}

    @pytest.mark.asyncio
    async def test_path_prefixed_id_resolves_to_the_same_map(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_graph(pathway=f"path:{MAP}")
        assert json.loads(out)["pathway"]["id"] == MAP

    @pytest.mark.asyncio
    async def test_cross_map_pointers_are_reported_but_not_edges(self):
        """Including them would fabricate interactions across different maps."""
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_graph(pathway=MAP)
        graph = json.loads(out)
        assert graph["map_links"]
        assert all(e["class"] != "maplink" for e in graph["edges"])

    @pytest.mark.asyncio
    async def test_kgml_is_memoized_so_one_map_costs_one_request(self):
        with respx.mock(using="httpx") as router:
            route = _mock_kgml(router)
            await pathway_graph(pathway=MAP)
            await pathway_graph(pathway=MAP)
            await pathway_neighborhood(pathway=MAP, seeds="AKT1")
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_expand_members_is_refused_above_the_edge_cap(self):
        """One entry box is a whole paralog family, so expansion is combinatorial."""
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            with pytest.raises(ValueError, match="expand_members=True would produce"):
                await pathway_graph(pathway=MAP, expand_members=True, max_edges=10)

    @pytest.mark.asyncio
    async def test_expand_members_emits_one_node_per_identifier_when_it_fits(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            plain = json.loads(await pathway_graph(pathway=MAP))
            expanded = json.loads(await pathway_graph(pathway=MAP, expand_members=True))
        # The fixture's entry 1 carries three paralogs; expansion must surface them.
        assert len(expanded["nodes"]) > len(plain["nodes"])
        assert all(n["member_count"] == 1 for n in expanded["nodes"])

    @pytest.mark.asyncio
    async def test_oversize_map_is_trimmed_and_says_so(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_graph(pathway=MAP, max_nodes=2)
        graph = json.loads(out)
        assert len(graph["nodes"]) == 2
        # `truncated` now carries a {returned, total} pair PER SECTION.
        assert graph["truncated"]["nodes"]["returned"] == 2
        assert graph["truncated"]["nodes"]["total"] == graph["stats"]["node_count"]
        assert graph["truncated"]["nodes"]["capped_by"] == "count"
        # stats must still describe the WHOLE map, not the trimmed view.
        assert graph["stats"]["node_count"] > 2

    @pytest.mark.asyncio
    async def test_global_map_shape_stays_under_the_transport_limit(self):
        """A whole-metabolism map must degrade, not exceed the 1 MB MCP limit.

        Regression for the worst failure this tool had: `_bounded` only LABELLED
        an oversized dict (`payload["truncated"] = ...`) and then serialized it in
        full, so the cap was decorative for every dict-returning tool. hsa01100
        (6,382 nodes, 8,124 edges, 2,073 metabolic gaps) then blew past the
        transport limit and the caller received NOTHING — not even the truncation
        note meant to help it recover.

        Synthetic rather than fetched: no test may touch rest.kegg.jp, and this
        reproduces the shape that matters — thousands of unreacted ortholog boxes
        (metabolic gaps) plus hundreds of cross-map pointers.
        """
        entries, relations = [], []
        for i in range(2500):  # isolated ortholog boxes -> metabolic_gaps
            entries.append(
                f'<entry id="{9000 + i}" name="ko:K{i:05d}" type="ortholog">'
                f'<graphics name="{i}.{i}.{i}.{i}" type="rectangle"/></entry>'
            )
        for i in range(400):  # cross-map pointers -> map_links
            entries.append(
                f'<entry id="{20000 + i}" name="path:map{i:05d}" type="map">'
                f'<graphics name="Some other pathway {i}" type="roundrectangle"/></entry>'
            )
        for i in range(300):  # a real connected core
            entries.append(
                f'<entry id="{i + 1}" name="hsa:{i}" type="gene">'
                f'<graphics name="GENE{i}" type="rectangle"/></entry>'
            )
            if i:
                relations.append(
                    f'<relation entry1="{i}" entry2="{i + 1}" type="PPrel">'
                    '<subtype name="activation" value="--&gt;"/></relation>'
                )
        big = (
            '<?xml version="1.0"?><pathway name="path:xxx01100" org="xxx" '
            'number="01100" title="Synthetic global map">'
            + "".join(entries) + "".join(relations) + "</pathway>"
        )

        with respx.mock(using="httpx") as router:
            router.get(f"{BASE}/get/xxx01100/kgml").mock(
                return_value=httpx.Response(200, text=big)
            )
            out = await pathway_graph(pathway="xxx01100")

        assert len(out.encode()) < 1_000_000, (
            f"payload is {len(out.encode())} bytes — over the 1 MB transport limit"
        )
        graph = json.loads(out)
        # stats must still report the FULL map, which is what makes a trimmed
        # response usable instead of merely small.
        assert graph["stats"]["metabolic_gap_count"] == 2500
        assert graph["stats"]["node_count"] > len(graph["nodes"])
        # …and every trimmed section says what it dropped.
        t = graph["truncated"]
        assert t["metabolic_gaps"]["total"] == 2500
        assert t["map_links"]["total"] == 400
        assert t["nodes"]["total"] == graph["stats"]["node_count"]
        # The graph itself must survive: a pathway tool answering with zero edges
        # reads as "these molecules are unconnected", which is worse than an error.
        assert len(graph["edges"]) >= min(kegg._PRIMARY_FLOOR, graph["stats"]["edge_count"])

    @pytest.mark.asyncio
    async def test_raised_caps_never_starve_the_graph_of_edges(self):
        """Raising the count caps must not let supporting detail eat the graph.

        Regression for the swing this file has already made in BOTH directions.
        A "gaps first" drop order threw away all 25 of hsa00010's metabolic gaps
        to save 2 KB; reversing it to "edges first" then let a whole-metabolism
        map's 186 KB of gaps push `edges` to ZERO — a pathway graph with no graph
        in it, which reads as "these molecules are unconnected" and is worse than
        an error because it does not look like one.

        The rule is not which section is more precious: the section OCCUPYING the
        budget is the one that pays, and the answer keeps a floor.
        """
        # gaps dominate, as on the real hsa01100
        big = _synthetic_global_map(gaps=2073, map_links=169, genes=900)

        async def fetch(**kwargs):
            kegg._kgml_cache.clear()
            with respx.mock(using="httpx", assert_all_called=False) as router:
                router.get(f"{BASE}/get/xxx01100/kgml").mock(
                    return_value=httpx.Response(200, text=big)
                )
                return json.loads(await pathway_graph(pathway="xxx01100", **kwargs))

        raised = await fetch(max_nodes=5000, max_edges=20000, max_gaps=5000)
        assert len(raised["edges"]) >= kegg._PRIMARY_FLOOR, "the graph was starved"
        t = raised["truncated"]
        # The two firing conditions must stay distinguishable…
        assert "map larger than the requested caps" in t["reasons"]
        assert "response exceeded the size cap" in t["reasons"]
        # …and the section that ATE the budget must be visible, even though the
        # count cap left it untrimmed — otherwise "why are there few edges?" is
        # unanswerable from the response.
        # The diagnostic that answers "why so few edges?": what each section
        # would have cost unreduced, including one that was never trimmed.
        complete = t["section_bytes_if_complete"]
        assert set(complete) == {"nodes", "edges", "metabolic_gaps", "map_links"}
        assert complete["nodes"] + complete["edges"] > _MAX_GRAPH_CAP
        # Every returned edge resolves — the invariant that independent clipping
        # of nodes and edges used to break (50/50 edges dangling).
        node_ids = {n["id"] for n in raised["nodes"]}
        assert all(
            e["source"] in node_ids and e["target"] in node_ids
            for e in raised["edges"]
        )
        # …and the returned nodes are not overwhelmingly edgeless.
        touched = {e["source"] for e in raised["edges"]} | {
            e["target"] for e in raised["edges"]
        }
        assert len(touched) >= len(node_ids) / 2

        # Default arguments must be untouched by all of this.
        default = await fetch()
        assert len(default["nodes"]) == 400
        assert len(default["metabolic_gaps"]) == 100
        assert len(default["edges"]) > 0
        assert "map larger than the requested caps" in default["truncated"]["reasons"]

    @pytest.mark.asyncio
    async def test_raising_max_gaps_cannot_spend_the_graphs_reserved_share(self):
        """The caps must not interact backwards: raising them all shrank the graph.

        `max_gaps=5000` on hsa01100 let 1,555 metabolic gaps take 74% of the
        payload, so the graph fell to the 50-node floor — FEWER nodes than the
        191 the same map returns at the defaults. A caller raising every cap is
        asking for more, so `nodes`+`edges` now take `_GRAPH_BUDGET_SHARE` of the
        budget before the supporting sections may spend any of it.
        """
        big = _synthetic_global_map(gaps=2073, map_links=169, genes=900)

        async def fetch(**kwargs):
            kegg._kgml_cache.clear()
            with respx.mock(using="httpx", assert_all_called=False) as router:
                router.get(f"{BASE}/get/xxx01100/kgml").mock(
                    return_value=httpx.Response(200, text=big)
                )
                out = await pathway_graph(pathway="xxx01100", **kwargs)
            graph = json.loads(out)
            _assert_graph_invariants(out, graph)
            return graph

        raised = await fetch(max_nodes=5000, max_edges=20000, max_gaps=5000)
        graph_bytes = len(
            json.dumps({"nodes": raised["nodes"], "edges": raised["edges"]})
        )
        reserve = _MAX_GRAPH_CAP * kegg._GRAPH_BUDGET_SHARE
        assert graph_bytes > reserve * 0.8, (
            f"the graph got {graph_bytes} bytes of its {reserve:.0f}-byte reserve"
        )
        assert len(raised["nodes"]) > kegg._PRIMARY_FLOOR, "collapsed to the floor"

        # The gaps that could not fit are reported as size_budget, NOT count:
        # telling a caller to raise a cap it already maxed out is worse than
        # silence, and `map_links` (small, count-capped) must keep saying count.
        assert raised["truncated"]["metabolic_gaps"]["capped_by"] == "size_budget"
        assert raised["truncated"]["map_links"]["capped_by"] == "count"
        # …and the hint must name the move that actually works here. "Raise
        # max_nodes" does not: the graph is size-bound, not count-bound.
        hint = raised["truncated"]["hint"]
        assert "LOWER `max_gaps`" in hint

        # Lowering max_gaps is what buys graph — the property the hint asserts.
        starved = await fetch(max_nodes=5000, max_edges=20000, max_gaps=0)
        assert len(starved["nodes"]) > len(raised["nodes"])
        assert starved["metabolic_gaps"] == []

    @pytest.mark.asyncio
    async def test_graph_invariants_hold_on_every_reduction_path(self):
        """Count cap, size cap and neither: same three guarantees each time."""
        cases = [
            (MAP, {}),                                   # neither cap fires
            (MAP, {"max_nodes": 2}),                     # count cap
            ("xxx01100", {}),                            # size cap
            ("xxx01100", {"max_nodes": 5000, "max_gaps": 5000}),
        ]
        big = _synthetic_global_map(gaps=2073, map_links=169, genes=900)
        for pathway, kwargs in cases:
            kegg._kgml_cache.clear()
            with respx.mock(using="httpx", assert_all_called=False) as router:
                _mock_kgml(router)
                router.get(f"{BASE}/get/xxx01100/kgml").mock(
                    return_value=httpx.Response(200, text=big)
                )
                out = await pathway_graph(pathway=pathway, **kwargs)
            _assert_graph_invariants(out, json.loads(out))

    @pytest.mark.asyncio
    async def test_bounded_actually_shrinks_a_dict_not_just_labels_it(self):
        """The dict branch used to add a `truncated` key and return everything."""
        payload = {
            "stats": {"n": 3000},
            "keep_me": "small",
            "big": [{"row": "x" * 100} for _ in range(3000)],
        }
        parsed = json.loads(
            kegg._bounded(payload, note="hint", secondary=("big",))
        )
        assert len(json.dumps(parsed)) <= kegg._MAX_RESPONSE_CHARS
        assert len(parsed["big"]) < 3000
        assert parsed["truncated"]["big"]["total"] == 3000
        assert parsed["truncated"]["big"]["capped_by"] == "size_budget"
        assert "response exceeded the size cap" in parsed["truncated"]["reasons"]
        # Un-named sections are never touched.
        assert parsed["stats"] == {"n": 3000} and parsed["keep_me"] == "small"

    @pytest.mark.asyncio
    async def test_map_without_kgml_raises_a_diagnostic_error(self):
        """Global/overview maps have no KGML; KEGG signals that with an empty 200."""
        with respx.mock(using="httpx") as router:
            router.get(f"{BASE}/get/hsa01100/kgml").mock(
                return_value=httpx.Response(200, text="")
            )
            with pytest.raises(ValueError, match="no KGML"):
                await pathway_graph(pathway="hsa01100")

    @pytest.mark.asyncio
    async def test_malformed_map_id_raises_without_calling_kegg(self):
        # assert_all_called=False: the catch-all route exists precisely so the
        # test can assert it stays UNCALLED.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            with pytest.raises(ValueError, match="Invalid pathway id"):
                await pathway_graph(pathway="not-a-map")
            assert not router.calls


class TestPathwayNeighborhood:
    @pytest.mark.asyncio
    async def test_paralog_family_member_resolves_though_the_box_is_labelled_otherwise(
        self,
    ):
        """The trap this tool claims to have solved, on the way IN.

        hsa04151's box 17 holds hsa:10000, hsa:207 and hsa:208 (AKT3/AKT1/AKT2)
        and KGML labels it "AKT3, MPPH, PKB-GAMMA, …" — the drawn member's
        symbol and ITS aliases. So `seeds="AKT1"`, the most obvious query anyone
        would type, matched nothing while `seeds="hsa:207"` resolved instantly,
        and `unresolved_note` said the gene might not be drawn on this map. It
        is drawn; it is simply drawn under a sibling's name.
        """
        akt = (
            '<?xml version="1.0"?><pathway name="path:xxx00001" org="xxx" '
            'number="00001" title="Paralog box">'
            '<entry id="17" name="hsa:10000 hsa:207 hsa:208" type="gene">'
            '<graphics name="AKT3, MPPH, MPPH2, PKB-GAMMA" type="rectangle"/></entry>'
            '<entry id="18" name="hsa:2475" type="gene">'
            '<graphics name="MTOR" type="rectangle"/></entry>'
            '<relation entry1="17" entry2="18" type="PPrel">'
            '<subtype name="activation" value="--&gt;"/></relation>'
            "</pathway>"
        )
        with respx.mock(using="httpx") as router:
            router.get(f"{BASE}/get/xxx00001/kgml").mock(
                return_value=httpx.Response(200, text=akt)
            )
            # /find is a SUBSTRING search: AKT1S1 comes back too and must be
            # rejected, or a near-miss silently answers for the wrong gene.
            router.get(f"{BASE}/find/xxx/AKT1").mock(
                return_value=httpx.Response(
                    200,
                    text=(
                        "hsa:207\tAKT1, AKT, PKB, RAC-ALPHA; AKT serine/threonine "
                        "kinase 1\n"
                        "hsa:84335\tAKT1S1, Lobe, PRAS40; AKT1 substrate 1\n"
                    ),
                )
            )
            out = await pathway_neighborhood(pathway="xxx00001", seeds="AKT1")
        result = json.loads(out)

        assert result["unresolved"] == []
        assert result["seeds"] == ["17"]
        assert [r["label"] for r in result["reached"]] == ["MTOR"]
        # AKT1S1 is not in this map and must not have been used to resolve it.
        note = result["seed_resolution"][0]
        assert note["seed"] == "AKT1"
        assert note["matched_members"] == ["hsa:207"]
        # The caller asked for AKT1 and is getting a box drawn as AKT3 — saying
        # so is the whole point, since every row below is labelled AKT3.
        assert note["node_labels"] == ["AKT3"]
        assert "paralog family" in note["note"]

    @pytest.mark.asyncio
    async def test_symbol_lookup_is_skipped_when_kgml_can_already_resolve(self):
        """The fallback costs a request against a 3/s budget — only on a miss."""
        with respx.mock(using="httpx", assert_all_called=False) as router:
            _mock_kgml(router)
            lookup = _mock_symbol_lookup(router)
            for seeds in ("PIK3CA", "hsa:207", "5290", "1"):
                await pathway_neighborhood(pathway=MAP, seeds=seeds)
            assert not lookup.called
            # A compound accession is not a gene symbol either: no lookup, and
            # no request wasted on a token /find could never match.
            await pathway_neighborhood(pathway=MAP, seeds="C00031")
            assert not lookup.called
            # …and a token that would alter the REST path never reaches it.
            await pathway_neighborhood(pathway=MAP, seeds="../../get/hsa:207")
            assert not lookup.called

    @pytest.mark.asyncio
    async def test_resolves_a_gene_symbol_and_reports_net_sign(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_neighborhood(pathway=MAP, seeds="PIK3CA", depth=2)
        result = json.loads(out)
        assert result["seeds"]
        assert not result["unresolved"]
        assert result["reached"]
        assert {r["net_sign"] for r in result["reached"]} <= {-1, 0, 1}
        assert "signal_quality" in result

    @pytest.mark.asyncio
    async def test_kegg_gene_id_and_bare_id_resolve_to_the_same_node(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            by_kegg = json.loads(await pathway_neighborhood(pathway=MAP, seeds="hsa:5290"))
            by_bare = json.loads(await pathway_neighborhood(pathway=MAP, seeds="5290"))
        assert by_kegg["seeds"] == by_bare["seeds"]

    @pytest.mark.asyncio
    async def test_unresolved_seed_is_flagged_rather_than_silently_narrowed(self):
        """An absent gene must not read as a biological negative."""
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            lookup = _mock_symbol_lookup(router)  # KEGG knows no such symbol
            out = await pathway_neighborhood(pathway=MAP, seeds="NOTAGENE")
        result = json.loads(out)
        assert lookup.called, "the symbol fallback must be tried before giving up"
        assert result["unresolved"] == ["NOTAGENE"]
        assert "LOOKUP failure" in result["unresolved_note"]
        # The advice must not stop at "not drawn on this map" — that was the
        # misleading half when the seed IS drawn, just under a sibling's label.
        assert "hsa:207" in result["unresolved_note"]
        assert "seed_resolution" not in result

    @pytest.mark.asyncio
    async def test_signed_only_drops_unsigned_edges(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_neighborhood(
                pathway=MAP, seeds="PIK3CA", depth=3, signed_only=True
            )
        result = json.loads(out)
        assert all(e["sign"] in (-1, 1) for e in result["edges"])

    @pytest.mark.asyncio
    async def test_invalid_direction_raises(self):
        with pytest.raises(ValueError, match="Invalid direction"):
            await pathway_neighborhood(pathway=MAP, seeds="AKT1", direction="sideways")

    @pytest.mark.asyncio
    async def test_missing_seeds_raises(self):
        with pytest.raises(ValueError, match="Missing `seeds`"):
            await pathway_neighborhood(pathway=MAP, seeds="")


class TestPathwayPaths:
    @pytest.mark.asyncio
    async def test_enumerates_signed_routes_between_two_molecules(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_paths(pathway=MAP, source="PIK3CA", target="MTOR")
        result = json.loads(out)
        assert result["source_nodes"] and result["target_nodes"]
        assert not result["unresolved"]
        assert result["path_count"] == len(result["paths"])
        shortest = min(result["paths"], key=lambda p: p["length"])
        assert [n["id"] for n in shortest["nodes"]] == ["1", "2", "11"]
        assert shortest["net_sign"] == 1

    @pytest.mark.asyncio
    async def test_unresolved_endpoint_is_distinguished_from_no_path(self):
        """find_paths returns [] for both; the tool must not conflate them."""
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            _mock_symbol_lookup(router)
            missing = json.loads(
                await pathway_paths(pathway=MAP, source="NOTAGENE", target="MTOR")
            )
            # Both endpoints exist, but MTOR has no directed route back to PIK3CA.
            nopath = json.loads(
                await pathway_paths(
                    pathway=MAP, source="MTOR", target="PIK3CA", max_length=1
                )
            )

        assert missing["unresolved"] == ["NOTAGENE"]
        assert "LOOKUP failure" in missing["unresolved_note"]
        assert "no_path_note" not in missing

        assert nopath["unresolved"] == []
        assert nopath["path_count"] == 0
        assert "no_path_note" in nopath
        assert "unresolved_note" not in nopath

    @pytest.mark.asyncio
    async def test_parallel_reactions_are_reported_as_distinct_routes(self):
        """Same node sequence via two reactions is not a duplicate — the
        reaction accession on each edge is what tells them apart."""
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_paths(
                pathway=MAP, source="cpd:C05981", target="cpd:C00076", max_length=4
            )
        paths = json.loads(out)["paths"]
        assert paths
        assert all("reaction" in e for p in paths for e in p["edges"])
        rendered = {json.dumps(p, sort_keys=True) for p in paths}
        assert len(rendered) == len(paths)

    @pytest.mark.asyncio
    async def test_hitting_max_paths_is_flagged_as_non_exhaustive(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_paths(
                pathway=MAP, source="cpd:C05981", target="cpd:C00076", max_paths=1
            )
        result = json.loads(out)
        assert result["path_count"] == 1
        assert "NOT exhaustive" in result["truncated"]["hint"]

    @pytest.mark.asyncio
    async def test_missing_endpoint_argument_raises(self):
        for src, tgt in (("", "MTOR"), ("PIK3CA", ""), ("", "")):
            with pytest.raises(ValueError, match="both required"):
                await pathway_paths(pathway=MAP, source=src, target=tgt)


class TestPathwayCycles:
    @pytest.mark.asyncio
    async def test_classifies_a_negative_feedback_loop(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_cycles(pathway=MAP, max_length=3)
        result = json.loads(out)
        assert set(result["counts"]) == {"negative", "positive", "unsigned"}
        loop = next(
            c
            for c in result["cycles"]
            if {n["id"] for n in c["nodes"]} == {"1", "2"}
        )
        # 1 -(activation)-> 2 -(inhibition)-> 1
        assert loop["feedback"] == "negative"
        assert loop["net_sign"] == -1

    @pytest.mark.asyncio
    async def test_feedback_filter_narrows_but_counts_stay_whole_map(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_cycles(pathway=MAP, feedback="negative", max_length=3)
        result = json.loads(out)
        assert result["feedback_filter"] == "negative"
        assert all(c["feedback"] == "negative" for c in result["cycles"])
        # `counts` describes every cycle found, not just the filtered ones, so a
        # caller can see what the filter removed.
        assert sum(result["counts"].values()) >= result["cycle_count"]

    @pytest.mark.asyncio
    async def test_cap_is_flagged_because_the_filter_runs_after_it(self):
        """A filtered-empty result under a reached cap is not a real zero."""
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            out = await pathway_cycles(pathway=MAP, max_length=3, max_cycles=1)
        result = json.loads(out)
        assert "AFTER this cap" in result["truncated"]["hint"]

    @pytest.mark.asyncio
    async def test_invalid_feedback_filter_raises(self):
        with pytest.raises(ValueError, match="Invalid feedback filter"):
            await pathway_cycles(pathway=MAP, feedback="neutral")

    @pytest.mark.asyncio
    async def test_reversible_reaction_two_cycles_are_excluded_by_default(self):
        """A reversible reaction A<->B is a 2-cycle by construction, not feedback.

        The fixture's R03469 is reversible between entries 30 and 31, so it is
        emitted in both directions. On a real metabolic map these dominate the
        two-cycles (82 of ko00010's 102).
        """
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            default = json.loads(await pathway_cycles(pathway=MAP, max_length=2))
            kept = json.loads(
                await pathway_cycles(
                    pathway=MAP, max_length=2, include_reversible_artifacts=True
                )
            )
        assert default["artifacts_excluded"] >= 1
        assert all(c.get("artifact") is None for c in default["cycles"])
        assert any(c.get("artifact") == "reversible_reaction" for c in kept["cycles"])
        assert kept["artifacts_excluded"] == 0
        assert len(kept["cycles"]) > len(default["cycles"])

    @pytest.mark.asyncio
    async def test_zero_cycles_is_explained_rather_than_left_to_be_misread(self):
        """Empty is the NORMAL outcome on real maps, and 'no feedback exists' is
        the wrong reading — a KEGG map routinely omits one arm of a real loop
        (hsa05200 draws MDM2 -| TP53 but not TP53 -> MDM2)."""
        with respx.mock(using="httpx") as router:
            # A map with relations but no closed loop of length <= 2 other than
            # the artifact one, which is excluded by default.
            _mock_kgml(router)
            result = json.loads(
                await pathway_cycles(pathway=MAP, feedback="positive", max_length=2)
            )
        assert result["cycle_count"] == 0
        joined = " ".join(result["interpretation"])
        assert "NOT evidence" in joined
        assert "kegg_pathway_paths" in joined

    @pytest.mark.asyncio
    async def test_unsigned_only_result_is_flagged(self):
        with respx.mock(using="httpx") as router:
            _mock_kgml(router)
            result = json.loads(
                await pathway_cycles(pathway=MAP, feedback="unsigned", max_length=3)
            )
        if result["cycle_count"] and not (
            result["counts"]["negative"] or result["counts"]["positive"]
        ):
            assert any("UNKNOWN" in n for n in result["interpretation"])


# --------------------------------------------------------------------------- #
# link / conv
# --------------------------------------------------------------------------- #
class TestLink:
    @pytest.mark.asyncio
    async def test_returns_source_target_pairs(self):
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/link/pathway/hsa:10458").mock(
                return_value=httpx.Response(200, text="hsa:10458\tpath:hsa04810\n")
            )
            out = await link(target="pathway", source="hsa:10458")
        assert route.called
        assert json.loads(out) == [
            {"source": "hsa:10458", "target": "path:hsa04810"}
        ]

    @pytest.mark.asyncio
    async def test_organism_target_is_accepted(self):
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/link/hsa/path:hsa04151").mock(
                return_value=httpx.Response(200, text="path:hsa04151\thsa:207\n")
            )
            await link(target="hsa", source="path:hsa04151")
        assert route.called

    @pytest.mark.asyncio
    async def test_unknown_target_raises_without_calling_kegg(self):
        # assert_all_called=False: the catch-all route exists precisely so the
        # test can assert it stays UNCALLED.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            with pytest.raises(ValueError, match="Unknown link target database"):
                await link(target="wikipathways", source="hsa:10458")
            assert not router.calls


class TestConv:
    @pytest.mark.asyncio
    async def test_surfaces_prefix_stripped_ids_for_the_sparql_handoff(self):
        """KEGG-namespaced IDs do not resolve in run_sparql; the bare ones do."""
        with respx.mock(using="httpx") as router:
            router.get(f"{BASE}/conv/uniprot/hsa:10458").mock(
                return_value=httpx.Response(200, text="hsa:10458\tup:P50570\n")
            )
            out = await conv(target="uniprot", source="hsa:10458")
        assert json.loads(out) == [
            {
                "source": "hsa:10458",
                "target": "up:P50570",
                "source_id": "10458",
                "target_id": "P50570",
            }
        ]

    @pytest.mark.asyncio
    async def test_chemical_conversion(self):
        with respx.mock(using="httpx") as router:
            router.get(f"{BASE}/conv/chebi/cpd:C00031").mock(
                return_value=httpx.Response(200, text="cpd:C00031\tchebi:4167\n")
            )
            out = await conv(target="chebi", source="cpd:C00031")
        assert json.loads(out)[0]["target_id"] == "4167"

    @pytest.mark.asyncio
    async def test_whole_namespace_conversion(self):
        with respx.mock(using="httpx") as router:
            route = router.get(f"{BASE}/conv/hsa/uniprot").mock(
                return_value=httpx.Response(200, text="up:P50570\thsa:10458\n")
            )
            await conv(target="hsa", source="uniprot")
        assert route.called

    @pytest.mark.asyncio
    async def test_crossing_gene_and_chemical_families_raises(self):
        # assert_all_called=False: the catch-all route exists precisely so the
        # test can assert it stays UNCALLED.
        with respx.mock(using="httpx", assert_all_called=False) as router:
            router.get(url__startswith=BASE).mock(return_value=httpx.Response(200, text=""))
            with pytest.raises(ValueError, match="Cannot convert between identifier families"):
                await conv(target="chebi", source="hsa:10458")
            assert not router.calls

    @pytest.mark.asyncio
    async def test_unknown_namespace_raises(self):
        with pytest.raises(ValueError, match="Unknown conversion namespace"):
            await conv(target="ensembl", source="hsa:10458")


# --------------------------------------------------------------------------- #
# Transport behavior: rate limit, retries, licence-signal handling
# --------------------------------------------------------------------------- #
class TestRateLimit:
    @pytest.mark.asyncio
    async def test_requests_are_spaced_by_the_shared_process_wide_limiter(
        self, monkeypatch
    ):
        """3 req/s is a per-PROCESS budget, so the gate must not be per-tool."""
        monkeypatch.setattr(kegg, "_MIN_INTERVAL", 0.05)
        monkeypatch.setattr(kegg, "_last_request_at", 0.0)
        with respx.mock(using="httpx") as router:
            router.get(url__startswith=BASE).mock(
                return_value=httpx.Response(200, text="a\tb\n")
            )
            start = time.monotonic()
            # Two DIFFERENT tools: a per-tool limiter would let these run together.
            await asyncio.gather(
                find(database="compound", query="x"),
                link(target="pathway", source="hsa:10458"),
                find(database="compound", query="y"),
            )
            elapsed = time.monotonic() - start
        assert elapsed >= 2 * 0.05


class TestTransportErrors:
    @pytest.mark.asyncio
    async def test_403_is_not_retried_and_names_the_licence_and_rate_cap(self):
        """Retrying a 403/429 is what gets an institution's address blocked."""
        with respx.mock(using="httpx") as router:
            route = router.get(url__startswith=BASE).mock(
                return_value=httpx.Response(403, text="Forbidden")
            )
            with pytest.raises(ValueError, match="RATE LIMIT EXCEEDED OR ACCESS RESTRICTED"):
                await find(database="compound", query="x")
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_429_is_not_retried(self):
        with respx.mock(using="httpx") as router:
            route = router.get(url__startswith=BASE).mock(
                return_value=httpx.Response(429, text="Too Many Requests")
            )
            with pytest.raises(ValueError, match="RATE LIMIT EXCEEDED"):
                await find(database="compound", query="x")
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_transient_5xx_is_retried_then_succeeds(self):
        with respx.mock(using="httpx") as router:
            route = router.get(url__startswith=BASE).mock(
                side_effect=[
                    httpx.Response(502, text="bad gateway"),
                    httpx.Response(200, text="cpd:C00031\tD-Glucose\n"),
                ]
            )
            out = await find(database="compound", query="glucose")
        assert route.call_count == 2
        assert json.loads(out)[0]["entry"] == "cpd:C00031"

    @pytest.mark.asyncio
    async def test_persistent_5xx_raises_with_the_upstream_body(self):
        with respx.mock(using="httpx") as router:
            router.get(url__startswith=BASE).mock(
                return_value=httpx.Response(500, text="internal error detail")
            )
            with pytest.raises(ValueError, match="internal error detail"):
                await find(database="compound", query="x")

    @pytest.mark.asyncio
    async def test_4xx_surfaces_the_upstream_diagnostic(self):
        with respx.mock(using="httpx") as router:
            router.get(url__startswith=BASE).mock(
                return_value=httpx.Response(400, text="Bad request: no such database")
            )
            with pytest.raises(ValueError, match="no such database"):
                await find(database="compound", query="x")

    @pytest.mark.asyncio
    async def test_network_failure_retries_then_raises(self):
        with respx.mock(using="httpx") as router:
            route = router.get(url__startswith=BASE).mock(
                side_effect=httpx.ConnectError("unreachable")
            )
            with pytest.raises(ValueError, match="could not reach rest.kegg.jp"):
                await find(database="compound", query="x")
        assert route.call_count == kegg._MAX_ATTEMPTS


# --------------------------------------------------------------------------- #
# The licence gate — the whole reason this sub-server exists separately
# --------------------------------------------------------------------------- #
class TestTransportGate:
    """KEGG must be mounted on stdio ONLY.

    The public HTTP host cannot verify a caller's academic affiliation, and
    serving KEGG through it would need an academic service-provider licence. The
    gate is a `local=` argument rather than an env var precisely so that it
    cannot be opened by a deployment-config oversight — see main.setup().
    """

    async def _tool_names(
        self, *, local: bool, monkeypatch, opt_in: str | None = "1"
    ) -> set[str]:
        # A fresh root server per call: `setup()` mutates the module-global `mcp`,
        # and a leaked mount would make this test pass for the wrong reason.
        fresh = FastMCP("gate-test")
        monkeypatch.setattr(main, "mcp", fresh)
        if opt_in is None:
            monkeypatch.delenv(main._KEGG_ENV_VAR, raising=False)
        else:
            monkeypatch.setenv(main._KEGG_ENV_VAR, opt_in)
        await main.setup(local=local)
        return {t.name for t in await fresh.list_tools()}

    @pytest.mark.asyncio
    async def test_http_setup_does_not_mount_kegg(self, monkeypatch):
        names = await self._tool_names(local=False, monkeypatch=monkeypatch)
        assert not [n for n in names if n.startswith("kegg_")], (
            "KEGG reached the HTTP tool surface. The public host must never call "
            "rest.kegg.jp — see the licence note in main.setup()."
        )
        # The other sub-servers must still be there (guards against a no-op setup).
        assert any(n.startswith("togovar_") for n in names)

    @pytest.mark.asyncio
    async def test_stdio_setup_mounts_kegg(self, monkeypatch):
        names = await self._tool_names(local=True, monkeypatch=monkeypatch)
        assert {
            "kegg_find",
            "kegg_get_entry",
            "kegg_pathway_graph",
            "kegg_pathway_neighborhood",
            "kegg_pathway_paths",
            "kegg_pathway_cycles",
            "kegg_link",
            "kegg_conv",
        } <= names

    @pytest.mark.asyncio
    async def test_opt_in_cannot_open_the_http_transport(self, monkeypatch):
        """THE load-bearing test for the env var.

        The transport gate is ANDed in FRONT of the opt-in, so no environment
        setting may put KEGG on the public HTTP surface. If this ever passes
        KEGG through, the licence boundary has become one env var wide.
        """
        for value in ("1", "true", "YES", "on"):
            names = await self._tool_names(
                local=False, monkeypatch=monkeypatch, opt_in=value
            )
            assert not [n for n in names if n.startswith("kegg_")], (
                f"TOGOMCP_ENABLE_KEGG={value!r} opened the HTTP surface"
            )

    @pytest.mark.asyncio
    async def test_stdio_without_opt_in_does_not_mount_kegg(self, monkeypatch):
        """Default OFF: a non-academic user who installs TogoMCP and runs the
        stdio server must not be handed KEGG tools they may not be entitled to
        call — an LLM will use a tool it can see."""
        names = await self._tool_names(local=True, monkeypatch=monkeypatch, opt_in=None)
        assert not [n for n in names if n.startswith("kegg_")]
        # The rest of the server is unaffected.
        assert any(n.startswith("togovar_") for n in names)

    @pytest.mark.parametrize(
        "value", ["", "  ", "0", "false", "no", "off", "maybe", "ture", "enabled"]
    )
    def test_opt_in_parsing_is_fail_closed(self, value, monkeypatch):
        """Empty, falsy OR MALFORMED all mean OFF.

        This is what makes the env var safe where CLAUDE.md warns against one:
        deploy.sh forwards env vars by a fixed list, so a forwarding miss yields
        an ABSENT variable — which here DISABLES KEGG instead of enabling it.
        A typo ("ture") must fail the same way, not default to on.
        """
        monkeypatch.setenv(main._KEGG_ENV_VAR, value)
        assert main._kegg_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", "on", " on "])
    def test_opt_in_accepts_the_usual_truthy_spellings(self, value, monkeypatch):
        monkeypatch.setenv(main._KEGG_ENV_VAR, value)
        assert main._kegg_enabled() is True

    def test_opt_in_absent_is_off(self, monkeypatch):
        monkeypatch.delenv(main._KEGG_ENV_VAR, raising=False)
        assert main._kegg_enabled() is False

    async def _guide(self, *, local: bool, monkeypatch) -> str:
        """Assemble the Usage Guide as a client on that transport receives it.

        Opts in, so `local=True` really mounts KEGG — the guide gate reads the
        LIVE tool registry, so with the opt-in absent this would compare two
        identical KEGG-free guides and pass for the wrong reason.
        """
        import togo_mcp.rdf_portal as rdf_portal

        fresh = FastMCP("guide-test")
        monkeypatch.setattr(main, "mcp", fresh)
        # The guide probes the live registry through rdf_portal's own `mcp`.
        monkeypatch.setattr(rdf_portal, "mcp", fresh)
        monkeypatch.setenv(main._KEGG_ENV_VAR, "1")
        await main.setup(local=local)
        return await rdf_portal.togomcp_usage_guide()

    @pytest.mark.asyncio
    async def test_remote_guide_omits_the_kegg_operating_instructions(self, monkeypatch):
        """A client with no `kegg_*` tools must not be told how to call them.

        Regression: the gate originally relied on `mcp.get_tool()` RAISING for an
        unknown tool. It returns None instead, so the condition was always true
        and every HTTP client received the stdio-only section — instructions to
        call six tools it does not have.
        """
        guide = await self._guide(local=False, monkeypatch=monkeypatch)
        for tool in (
            "kegg_find",
            "kegg_conv",
            "kegg_pathway_graph",
            "kegg_pathway_cycles",
        ):
            assert tool not in guide, f"remote guide leaks {tool} instructions"

    @pytest.mark.asyncio
    async def test_remote_guide_still_warns_kegg_is_not_a_sparql_database(
        self, monkeypatch
    ):
        """The short note stays for everyone: without it an agent asked about
        KEGG will invent `database="kegg"` and get a hard validation error."""
        guide = await self._guide(local=False, monkeypatch=monkeypatch)
        assert "Not an RDF Portal database — KEGG" in guide
        assert 'database="kegg"' in guide
        # And it must tell the agent what to do instead of erroring out.
        assert "unavailable in this session" in guide

    @pytest.mark.asyncio
    async def test_stdio_guide_carries_the_kegg_section(self, monkeypatch):
        guide = await self._guide(local=True, monkeypatch=monkeypatch)
        assert "KEGG (available in this session)" in guide
        for tool in ("kegg_find", "kegg_conv", "kegg_pathway_cycles"):
            assert tool in guide
        # The bridge rule is the one an agent must not miss.
        assert "Bridging to RDF Portal" in guide

    @pytest.mark.asyncio
    async def test_the_two_transports_actually_differ(self, monkeypatch):
        """Guards against both halves passing for the wrong reason (e.g. the
        conditional part silently missing from the package)."""
        remote = await self._guide(local=False, monkeypatch=monkeypatch)
        local = await self._guide(local=True, monkeypatch=monkeypatch)
        assert len(local) > len(remote)
        assert remote in local or "KEGG (available" not in remote

    @pytest.mark.asyncio
    async def test_no_kegg_tool_names_the_sparql_tool_literally(self, monkeypatch):
        """No KEGG description may carry the `run_sparql` token.

        A deferred-tool client ranks by DESCRIPTION text and loads only the top
        few, so a tool that does not rank is effectively uncallable. Five KEGG
        descriptions each naming `run_sparql` put five decoys on exactly the query
        someone types to FIND run_sparql — measured: the real tool took seven
        searches to reach.

        This assertion was first written as `== ["kegg_conv"]`, on the argument
        that the bridge tool needs the precise name. Testing showed kegg_conv then
        remained the sole KEGG decoy across all three probe queries, and the
        argument does not survive: what the caller must know is "convert before
        any RDF query", which survives periphrasis intact. The tool's own
        vocabulary (uniprot/chebi/pubchem — the namespaces it converts between) is
        load-bearing and deliberately kept.

        A lexical proxy, not a search test: the ranking layer is client-side and
        this repo cannot query it. It guards the intent only.
        """
        fresh = FastMCP("gate-test")
        monkeypatch.setattr(main, "mcp", fresh)
        monkeypatch.setenv(main._KEGG_ENV_VAR, "1")
        await main.setup(local=True)
        naming = [
            t.name
            for t in await fresh.list_tools()
            if t.name.startswith("kegg_") and "run_sparql" in (t.description or "")
        ]
        assert naming == [], (
            f"tools naming `run_sparql`: {naming}. Say 'not RDF-resolvable' or "
            "'any downstream RDF query' instead — naming the tool competes with it "
            "in the caller's tool search."
        )

    @pytest.mark.asyncio
    async def test_kegg_conv_still_documents_what_it_converts(self, monkeypatch):
        """The de-collision must not strip the bridge tool's actual vocabulary.

        Guards against over-applying the rule above: `uniprot`/`chebi`/`pubchem`
        are the namespaces kegg_conv accepts, so removing them to reduce token
        overlap would leave the tool's API undocumented — a worse failure than a
        search collision.
        """
        fresh = FastMCP("gate-test")
        monkeypatch.setattr(main, "mcp", fresh)
        monkeypatch.setenv(main._KEGG_ENV_VAR, "1")
        await main.setup(local=True)
        conv_desc = next(
            t.description or ""
            for t in await fresh.list_tools()
            if t.name == "kegg_conv"
        ).lower()
        for namespace in ("uniprot", "chebi", "pubchem", "ncbi-geneid"):
            assert namespace in conv_desc, f"kegg_conv no longer documents {namespace}"
        # …and it must still say WHY you would call it.
        assert "convert" in conv_desc and "not rdf-resolvable" in conv_desc

    @pytest.mark.asyncio
    async def test_kegg_tools_are_read_only_and_documented(self, monkeypatch):
        """Same contract test_tool_descriptions.py applies to the HTTP surface —
        repeated here because the stdio-only tools never reach that fixture."""
        fresh = FastMCP("gate-test")
        monkeypatch.setattr(main, "mcp", fresh)
        monkeypatch.setenv(main._KEGG_ENV_VAR, "1")
        await main.setup(local=True)
        kegg_tools = [t for t in await fresh.list_tools() if t.name.startswith("kegg_")]
        assert len(kegg_tools) == 8
        for tool in kegg_tools:
            assert tool.annotations.readOnlyHint is True, tool.name
            assert tool.annotations.openWorldHint is True, tool.name
            # FastMCP drops the docstring `Returns:` section, so the contract has
            # to live in the body above `Args:`.
            assert "RETURNS" in (tool.description or ""), tool.name
            assert "RAISES" in (tool.description or ""), tool.name
