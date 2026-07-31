"""Tests for the pure KGML parser.

Each test names the pitfall from togo_mcp/kgml.py's module docstring that it
pins down. The fixture is synthetic (see its header) so this suite needs no
network and carries no KEGG licensing footprint.
"""

from pathlib import Path

import pytest

from togo_mcp.kgml import (
    KGMLParseError,
    diagnose,
    find_cycles,
    find_paths,
    metabolic_gaps,
    neighborhood,
    parse_kgml,
)

FIXTURE = Path(__file__).parent / "fixtures" / "kgml_pitfalls.xml"


@pytest.fixture(scope="module")
def kgml() -> str:
    return FIXTURE.read_text()


@pytest.fixture(scope="module")
def graph(kgml: str) -> dict:
    return parse_kgml(kgml)


def _edge(graph, source, target, **match):
    hits = [
        e
        for e in graph["edges"]
        if e["source"] == source
        and e["target"] == target
        and all(e.get(k) == v for k, v in match.items())
    ]
    assert hits, f"no edge {source}->{target} matching {match}"
    return hits


# --------------------------------------------------------------------------- #
# Pitfall 1 — entry/@name is a space-separated list
# --------------------------------------------------------------------------- #


def test_multi_id_entry_keeps_every_identifier(graph):
    node = next(n for n in graph["nodes"] if n["id"] == "1")
    assert node["members"] == ["hsa:5290", "hsa:5291", "hsa:5293"]
    assert node["member_count"] == 3
    # A "one entry == one gene" parser would report 1 here and lose two paralogs.
    assert graph["stats"]["multi_member_entries"] == 2


def test_index_resolves_bare_and_prefixed_ids_and_symbols(graph):
    assert graph["index"]["by_member"]["hsa:5291"] == ["1"]
    assert graph["index"]["by_member"]["5291"] == ["1"]
    assert graph["index"]["by_label"]["akt1"] == ["2"]


def test_expand_members_explodes_entries_into_identifier_nodes(kgml):
    g = parse_kgml(kgml, expand_members=True)
    ids = {n["id"] for n in g["nodes"]}
    assert {"hsa:5290", "hsa:5291", "hsa:5293", "hsa:207"} <= ids
    # 3 members x 1 member for the 1->2 activation edge.
    assert len(_edge(g, "hsa:5290", "hsa:207")) == 1
    assert len(_edge(g, "hsa:5293", "hsa:207")) == 1


# --------------------------------------------------------------------------- #
# Pitfall 2 — group entries are complexes
# --------------------------------------------------------------------------- #


def test_group_is_expanded_onto_its_components(graph):
    # The KGML relation is 2 -> 10 (a group). Both components must inherit it.
    for component in ("11", "12"):
        (edge,) = _edge(graph, "2", component, sign=1)
        assert edge["expanded_from_group"]["target"] == "10"
    # And the group must no longer be a graph node once expanded.
    assert "10" not in {n["id"] for n in graph["nodes"]}


def test_group_membership_is_still_reported(graph):
    (group,) = graph["groups"]
    assert group["entry"] == "10"
    assert group["components"] == ["11", "12"]
    assert group["component_members"] == ["hsa:2475", "hsa:57521", "hsa:64798"]


def test_group_placeholder_name_is_not_an_identifier(graph):
    # Real KGML writes name="undefined" on groups; it must not enter the id space.
    assert "undefined" not in graph["index"]["by_member"]


def test_unexpanded_mode_leaves_the_group_dangling(kgml):
    g = parse_kgml(kgml, expand_groups=False)
    assert "10" in {n["id"] for n in g["nodes"]}
    (edge,) = _edge(g, "2", "10")
    assert "expanded_from_group" not in edge
    # This is exactly the naive failure: an edge into a node with no identifier.
    node = next(n for n in g["nodes"] if n["id"] == "10")
    assert node["members"] == []


# --------------------------------------------------------------------------- #
# Pitfall 3 — ECrel subtype @value is an entry id, not a compound accession
# --------------------------------------------------------------------------- #


def test_ecrel_compound_reference_is_dereferenced(graph):
    (edge,) = _edge(graph, "40", "41", **{"class": "ECrel"})
    (via,) = edge["via"]
    assert via["subtype"] == "compound"
    assert via["entry"] == "30"
    assert via["members"] == ["cpd:C05981"]  # the raw "30" would be meaningless
    assert via["resolved"] is True


def test_ecrel_is_not_marked_as_a_direct_interaction(graph):
    (edge,) = _edge(graph, "40", "41", **{"class": "ECrel"})
    assert edge["direct"] is False
    ppr = _edge(graph, "1", "2", **{"class": "PPrel"})
    assert ppr[0]["direct"] is True


# --------------------------------------------------------------------------- #
# Pitfall 4 — maplink / map entries are cross-map pointers
# --------------------------------------------------------------------------- #


def test_maplink_is_excluded_from_the_graph_but_reported(graph):
    assert not [e for e in graph["edges"] if e["class"] == "maplink"]
    assert "20" not in {n["id"] for n in graph["nodes"]}
    origins = {m["origin"] for m in graph["map_links"]}
    assert origins == {"entry", "maplink"}
    entry_link = next(m for m in graph["map_links"] if m["origin"] == "entry")
    assert entry_link["targets"] == ["path:hsa04150"]


# --------------------------------------------------------------------------- #
# Pitfall 5 — reaction @id is the enzyme; reversibility doubles the edge
# --------------------------------------------------------------------------- #


def test_reaction_id_is_the_enzyme_not_the_reaction(graph):
    (edge,) = _edge(graph, "30", "31", **{"class": "reaction"})
    assert edge["reaction"] == ["rn:R03469"]
    assert edge["enzyme_entry"] == "40"
    assert edge["enzyme_members"] == ["ko:K00922"]


def test_reversible_reaction_yields_both_directions(graph):
    forward = _edge(graph, "30", "31", **{"class": "reaction"})
    back = [e for e in graph["edges"] if e["source"] == "31" and e["target"] == "30"]
    assert len(forward) == 1
    # rn:R03469 reversed AND the separate irreversible rn:R04372 — two distinct
    # reactions between the same pair, which must NOT collapse into one edge.
    assert {r for e in back for r in e["reaction"]} == {"rn:R03469", "rn:R04372"}
    assert len(back) == 2


# --------------------------------------------------------------------------- #
# Pitfall 6 — rendering-only entries
# --------------------------------------------------------------------------- #


def test_rendering_only_entry_is_skipped(graph):
    assert "50" not in {n["id"] for n in graph["nodes"]}
    assert graph["stats"]["skipped_rendering_entries"] == 1
    assert "path:xxx00000" not in graph["index"]["by_member"]


# --------------------------------------------------------------------------- #
# Pitfall 7 — the enzyme layer and the compound layer are not joined by KGML
#
# Found by running scripts/kgml_probe.py over hsa00010 / ko00010 / eco00010, not
# by reading the DTD: edge counts looked healthy while the graph was in fact two
# disconnected halves.
# --------------------------------------------------------------------------- #


def test_catalysis_edges_bridge_substrate_enzyme_product(graph):
    (into,) = _edge(graph, "30", "40", **{"class": "catalysis"})
    (out_of,) = _edge(graph, "40", "31", **{"class": "catalysis"})
    assert into["enzyme_members"] == ["ko:K00922"]
    assert out_of["reaction"] == ["rn:R03469"]


def test_catalysis_respects_reversibility(graph):
    # rn:R03469 is reversible -> the enzyme is reachable from both metabolites.
    assert _edge(graph, "31", "40", **{"class": "catalysis"})
    assert _edge(graph, "40", "30", **{"class": "catalysis"})
    # rn:R04372 is irreversible -> only 31 -> 41 -> 30, never the reverse.
    assert _edge(graph, "31", "41", **{"class": "catalysis"})
    assert not [
        e
        for e in graph["edges"]
        if e["class"] == "catalysis"
        and e["source"] == "41"
        and e["target"] == "31"
    ]


def test_without_catalysis_the_graph_falls_into_disconnected_layers(kgml):
    unlinked = parse_kgml(kgml, link_enzymes=False)
    linked = parse_kgml(kgml)
    # Enzymes {40,41} and compounds {30,31} are separate islands without the bridge.
    assert unlinked["stats"]["component_count"] == 3
    assert linked["stats"]["component_count"] == 2
    # And the enzyme cannot reach any metabolite at all.
    assert neighborhood(unlinked, ["40"], depth=5)["reached"] == [
        r for r in neighborhood(unlinked, ["40"], depth=5)["reached"] if r["id"] == "41"
    ]


def test_diagnose_reports_the_layer_split(kgml):
    p = diagnose(kgml)["pitfalls"]["7_enzyme_compound_layers"]
    assert p["components_without_catalysis_edges"] == 3
    assert p["components_with_catalysis_edges"] == 2
    assert p["catalysis_edges_added"] == 6


# --------------------------------------------------------------------------- #
# Pitfall 8 — KEGG draws one metabolite in several places
#
# Also found from real maps: hsa00010 left 34 of 94 nodes isolated even after the
# pitfall-7 fix. A map is a drawing, not a graph — pyruvate gets an entry id per
# box it appears in, so one molecule becomes several unconnected nodes.
# --------------------------------------------------------------------------- #

# C00022 is drawn twice (entries 60 and 61). The two halves of the chain only
# meet if those two drawings are recognised as the same molecule.
DUPLICATE_KGML = """<?xml version="1.0"?>
<pathway name="path:xxx00001" org="xxx" number="00001" title="Duplicate drawing">
  <entry id="30" name="cpd:C00031" type="compound">
    <graphics name="C00031" type="circle" x="10" y="10" width="8" height="8"/>
  </entry>
  <entry id="60" name="cpd:C00022" type="compound">
    <graphics name="C00022" type="circle" x="90" y="10" width="8" height="8"/>
  </entry>
  <entry id="61" name="cpd:C00022" type="compound">
    <graphics name="C00022" type="circle" x="10" y="90" width="8" height="8"/>
  </entry>
  <entry id="31" name="cpd:C00033" type="compound">
    <graphics name="C00033" type="circle" x="90" y="90" width="8" height="8"/>
  </entry>
  <entry id="40" name="ko:K00001" type="ortholog" reaction="rn:R00001">
    <graphics name="1.1.1.1" type="rectangle" x="50" y="10" width="46" height="17"/>
  </entry>
  <entry id="41" name="ko:K00002" type="ortholog" reaction="rn:R00002">
    <graphics name="1.1.1.2" type="rectangle" x="50" y="90" width="46" height="17"/>
  </entry>
  <reaction id="40" name="rn:R00001" type="irreversible">
    <substrate id="30" name="cpd:C00031"/>
    <product id="60" name="cpd:C00022"/>
  </reaction>
  <reaction id="41" name="rn:R00002" type="irreversible">
    <substrate id="61" name="cpd:C00022"/>
    <product id="31" name="cpd:C00033"/>
  </reaction>
</pathway>
"""


def test_duplicate_drawings_split_one_molecule_into_islands():
    g = parse_kgml(DUPLICATE_KGML, merge_duplicate_entries=False)
    assert g["stats"]["duplicated_entries"] == 1
    assert g["stats"]["component_count"] == 2
    # C00031 cannot reach C00033 even though the chemistry is a single chain.
    assert not find_paths(g, "cpd:C00031", "cpd:C00033", max_length=6)


def test_merging_duplicate_drawings_restores_the_chain():
    g = parse_kgml(DUPLICATE_KGML)  # merging is the default
    assert g["stats"]["component_count"] == 1
    assert g["stats"]["node_count"] == 5  # 6 entries, C00022 drawn twice
    routes = {
        tuple(n["label"] for n in p["nodes"])
        for p in find_paths(g, "cpd:C00031", "cpd:C00033", max_length=6)
    }
    # The compound-only route (substrate -> product edges) ...
    assert ("C00031", "C00022", "C00033") in routes
    # ... and the route through the catalysing enzymes both exist.
    assert ("C00031", "1.1.1.1", "C00022", "1.1.1.2", "C00033") in routes


def test_merge_records_the_absorbed_entry_ids():
    g = parse_kgml(DUPLICATE_KGML)
    node = next(n for n in g["nodes"] if n["members"] == ["cpd:C00022"])
    assert node["id"] == "60"
    assert node["merged_entries"] == ["61"]  # provenance back to the KGML


def test_merge_does_not_invent_self_loops():
    g = parse_kgml(DUPLICATE_KGML)
    assert not [e for e in g["edges"] if e["source"] == e["target"]]


def test_isolated_ortholog_boxes_are_reported_as_metabolic_gaps():
    # An organism map keeps the reference layout and leaves the steps the organism
    # lacks as ortholog boxes with no <reaction> — isolated by construction.
    g = parse_kgml(DUPLICATE_KGML, link_enzymes=False)
    gaps = metabolic_gaps(g)
    assert {x["members"][0] for x in gaps} == {"ko:K00001", "ko:K00002"}
    # With the reactions wired up they are no longer gaps.
    assert metabolic_gaps(parse_kgml(DUPLICATE_KGML)) == []


def test_isolated_nodes_are_broken_down_by_type():
    # The breakdown is what distinguishes "the organism lacks this enzyme"
    # (isolated compounds) from "the parse lost an edge" (isolated gene boxes).
    g = parse_kgml(DUPLICATE_KGML, link_enzymes=False)
    assert g["stats"]["isolated_by_type"] == {"ortholog": 2}


def test_diagnose_reports_the_merge_effect():
    p = diagnose(DUPLICATE_KGML)["pitfalls"]["8_duplicate_layout_entries"]
    assert p["duplicated_entries"] == 1
    assert p["nodes_before_merge"] == 6
    assert p["nodes_after_merge"] == 5
    assert p["components_before_merge"] == 2
    assert p["components_after_merge"] == 1


# --------------------------------------------------------------------------- #
# Signs and duplicates
# --------------------------------------------------------------------------- #


def test_duplicate_relations_are_merged(graph):
    assert len(_edge(graph, "1", "2")) == 1


def test_mechanism_is_kept_separate_from_sign(graph):
    (edge,) = _edge(graph, "1", "2")
    assert edge["sign"] == 1
    assert edge["effects"] == ["activation"]
    # "phosphorylation" describes HOW, not WHETHER it activates.
    assert edge["mechanisms"] == ["phosphorylation"]


def test_conflicting_subtypes_collapse_to_unsigned(graph):
    (edge,) = _edge(graph, "11", "2")
    assert edge["sign"] == 0
    assert sorted(edge["effects"]) == ["activation", "inhibition"]


def test_inhibition_is_negative(graph):
    (edge,) = _edge(graph, "2", "1")
    assert edge["sign"] == -1


# --------------------------------------------------------------------------- #
# Graph queries
# --------------------------------------------------------------------------- #


def test_neighborhood_tracks_net_sign_through_the_complex(graph):
    result = neighborhood(graph, ["PIK3CA"], direction="downstream", depth=2)
    assert result["seeds"] == ["1"]
    reached = {r["id"]: r for r in result["reached"]}
    assert reached["2"]["distance"] == 1
    assert reached["2"]["net_sign"] == 1
    # 1 -(activation)-> 2 -(activation)-> MTOR, reached only via group expansion.
    assert reached["11"]["distance"] == 2
    assert reached["11"]["net_sign"] == 1


def test_neighborhood_upstream(graph):
    result = neighborhood(graph, ["hsa:2475"], direction="upstream", depth=1)
    assert {r["id"] for r in result["reached"]} == {"2"}


def test_neighborhood_reports_unresolved_seeds(graph):
    result = neighborhood(graph, ["NOT_A_GENE"])
    assert result["reached"] == []
    assert result["unresolved"] == ["NOT_A_GENE"]


def test_signed_only_drops_mechanism_only_edges(graph):
    loose = neighborhood(graph, ["40"], direction="downstream", depth=1)
    strict = neighborhood(graph, ["40"], direction="downstream", depth=1, signed_only=True)
    # ECrel to the other enzyme, plus the catalysis edges into the compound layer.
    assert {r["id"] for r in loose["reached"]} == {"41", "30", "31"}
    assert strict["reached"] == []


def test_find_paths_returns_signed_routes(graph):
    paths = find_paths(graph, "PIK3CA", "MTOR", max_length=3)
    assert paths
    shortest = min(paths, key=lambda p: p["length"])
    assert [n["id"] for n in shortest["nodes"]] == ["1", "2", "11"]
    assert shortest["net_sign"] == 1


def test_find_cycles_detects_negative_feedback(graph):
    cycles = find_cycles(graph, max_length=3)
    two_cycles = [c for c in cycles if c["length"] == 2]
    assert two_cycles
    loop = next(c for c in two_cycles if {n["id"] for n in c["nodes"]} == {"1", "2"})
    # 1 -(activation)-> 2 -(inhibition)-> 1  ==  negative feedback
    assert loop["net_sign"] == -1
    assert loop["feedback"] == "negative"


# --------------------------------------------------------------------------- #
# Diagnostics and error handling
# --------------------------------------------------------------------------- #


def test_diagnose_quantifies_each_pitfall(kgml):
    report = diagnose(kgml)
    p = report["pitfalls"]
    # Set-based: 11 identifiers total, a first-id-only parser keeps 8.
    assert p["1_multi_id_entries"]["total_identifiers"] == 11
    assert p["1_multi_id_entries"]["identifiers_a_naive_parse_keeps"] == 8
    assert p["1_multi_id_entries"]["identifiers_lost_by_naive_parse"] == 3
    assert p["2_group_complexes"]["groups"] == 1
    assert p["2_group_complexes"]["relations_touching_a_group"] == 1
    assert p["3_ecrel_compound_refs"]["compound_subtypes_needing_dereference"] == 1
    assert p["4_cross_map_pointers"]["maplink_relations"] == 1
    assert p["5_reactions"]["reversible"] == 1
    assert p["6_rendering_entries"]["skipped"] == 1


def test_stats_are_stable(graph):
    s = graph["stats"]
    assert s["node_count"] == 8
    assert s["edge_count"] == 15
    assert s["signed_edge_count"] == 4
    assert s["reaction_edge_count"] == 3
    assert s["catalysis_edge_count"] == 6
    assert s["group_count"] == 1
    assert s["map_link_count"] == 2
    assert s["total_identifiers"] == 11
    assert s["dangling_endpoints"] == 0


def test_html_instead_of_kgml_fails_loudly():
    # The most common operator error: fetching the pathway page, not /kgml.
    with pytest.raises(KGMLParseError, match="expected <pathway>"):
        parse_kgml("<html><body>Not KGML</body></html>")


def test_malformed_xml_fails_loudly():
    with pytest.raises(KGMLParseError, match="not well-formed"):
        parse_kgml("<pathway><entry></pathway>")


def test_empty_pathway_is_valid_not_an_error():
    g = parse_kgml('<?xml version="1.0"?><pathway name="path:xxx" org="xxx"/>')
    assert g["nodes"] == []
    assert g["edges"] == []
