"""KGML (KEGG Markup Language) -> normalized pathway graph.

This module is deliberately **pure**: no network, no FastMCP, no third-party
dependencies (stdlib only). It is the counterpart of `togovar._build_variant_query`
— the part that carries the real logic and can be unit-tested without HTTP. The
eventual `togo_mcp/kegg.py` sub-server is expected to be a thin layer that fetches
KGML from rest.kegg.jp and hands the text to `parse_kgml()` here.

WHY A PARSER AND NOT A PASSTHROUGH
----------------------------------
Handing raw KGML to an LLM is close to useless: it is coordinate-heavy XML whose
edges are expressed as *entry-id* references, not as biological identifiers. The
value TogoMCP can add over `curl rest.kegg.jp/get/hsa04151/kgml` is turning it
into a **signed directed graph over resolved identifiers**, which is a shape RDF
Portal cannot produce (Reactome RDF has no equivalent of KGML's PPrel subtypes).

THE EIGHT WAYS A NAIVE PARSER GETS THIS WRONG
---------------------------------------------
Every one of these is handled below and exercised by tests/test_kgml.py. 1-6 come
from reading the DTD; **7 and 8 were only found by running the parser over real
maps** (scripts/kgml_probe.py) — both are invisible in edge counts and show up
only in connectivity.

1. ``entry/@name`` is a SPACE-SEPARATED LIST. One entry is frequently a whole
   paralog family (``hsa:5290 hsa:5291 hsa:5293 ...``). "one entry == one gene"
   silently drops most of the pathway's genes.

2. ``entry/@type="group"`` is a COMPLEX, and relations point at the *group*, not
   at its members. Without expanding ``<component>``, every complex-mediated edge
   dead-ends at a node with no identifier at all, disconnecting the graph.

3. ``ECrel`` edges are INDIRECT, mediated by a compound named in
   ``<subtype name="compound" value="N"/>`` — and ``N`` is an **entry id**, not a
   compound accession. Reporting the raw number makes the edge uninterpretable;
   worse, treating ECrel like PPrel asserts a direct protein-protein relation
   that does not exist.

4. ``maplink`` relations and ``entry/@type="map"`` are POINTERS TO OTHER MAPS.
   Mixing them into the node/edge set fabricates edges between molecules that
   were never claimed to interact.

5. ``<reaction>`` carries ``@id`` = the **entry id of the catalysing enzyme**, and
   ``@name`` = the reaction accession. Swapping the two is a common bug. Also
   ``@type="reversible"`` means the substrate->product edge exists in BOTH
   directions; ignoring it produces wrong reachability in metabolic maps.

6. Rendering-only entries (``graphics/@type="line"``, title/legend boxes) are not
   molecules. They inflate node counts and, in metabolic maps, can attach to
   relations as phantom participants.

7. A metabolic map is TWO STACKED GRAPHS that KGML never joins: ``ECrel``
   connects enzyme entries to enzyme entries, ``<reaction>`` connects compound
   entries to compound entries. Parse both and the result is disconnected by
   construction — "downstream of this enzyme" never reaches a metabolite. Bridged
   here with explicit ``catalysis`` edges (substrate -> enzyme -> product).

8. A KEGG map is a DRAWING, NOT A GRAPH. The same molecule is drawn wherever it
   is needed and each drawing gets its own ``entry id``; pyruvate can be three
   entries in one map. Left unmerged, one molecule becomes several islands and
   reachability depends on which box the traversal happened to enter.

NOT A PITFALL — A RESULT
------------------------
Isolated ``ortholog`` nodes in an ORGANISM map are not a parse failure: KEGG keeps
the reference layout and leaves the steps the organism lacks as bare ortholog
boxes. See ``metabolic_gaps()`` for the arithmetic that confirms this.

OUTPUT MODEL
------------
Nodes are **entries** by default (faithful to KGML: an entry is the unit a
relation actually connects), each carrying its resolved ``members``. Set
``expand_members=True`` to explode entries into one node per identifier — correct
for "is gene A upstream of gene B", but note the fan-out: an edge between two
20-member entries becomes 400 edges.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from typing import Any, Iterable, Literal

__all__ = [
    "parse_kgml",
    "neighborhood",
    "find_paths",
    "find_cycles",
    "diagnose",
    "metabolic_gaps",
    "KGMLParseError",
]


class KGMLParseError(ValueError):
    """Raised on XML that is not usable KGML (bad XML, or no <pathway> root)."""


# --------------------------------------------------------------------------- #
# Vocabularies (KGML DTD, https://www.kegg.jp/kegg/xml/docs/)
# --------------------------------------------------------------------------- #

# entry/@type
_MOLECULAR_ENTRY_TYPES = frozenset(
    ["ortholog", "enzyme", "reaction", "gene", "group", "compound", "brite", "other"]
)
# Not molecular: "map" -> a link to another pathway map (pitfall 4).

# relation/@type
_RELATION_CLASSES = frozenset(["ECrel", "PPrel", "GErel", "PCrel", "maplink"])

# subtype/@name -> effect sign. Only these four carry a direction of regulation;
# everything else (phosphorylation, binding/association, ...) describes the
# MECHANISM and is sign-neutral. Conflating "phosphorylation" with "activation"
# is wrong often enough to matter (inhibitory phosphorylation is routine).
_SIGN_BY_SUBTYPE = {
    "activation": 1,
    "expression": 1,
    "inhibition": -1,
    "repression": -1,
}

# Subtypes whose @value is an ENTRY ID that must be dereferenced (pitfall 3).
_ENTRY_REF_SUBTYPES = frozenset(["compound", "hidden compound"])

# Mechanism subtypes, kept verbatim on the edge.
_MECHANISM_SUBTYPES = frozenset(
    [
        "phosphorylation",
        "dephosphorylation",
        "glycosylation",
        "ubiquitination",
        "methylation",
        "binding/association",
        "dissociation",
        "indirect effect",
        "state change",
        "missing interaction",
    ]
)


def _split_names(value: str | None) -> list[str]:
    """KGML packs multiple identifiers into one attribute, space-separated."""
    if not value:
        return []
    return [tok for tok in value.split() if tok]


def _split_labels(value: str | None) -> list[str]:
    """graphics/@name is comma-separated display labels; KEGG truncates with '...'."""
    if not value:
        return []
    return [tok.strip().rstrip(".") for tok in value.split(",") if tok.strip()]


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def parse_kgml(
    kgml: str | bytes,
    *,
    expand_groups: bool = True,
    expand_members: bool = False,
    include_maplink: bool = False,
    link_enzymes: bool = True,
    merge_duplicate_entries: bool = True,
) -> dict[str, Any]:
    """Parse KGML into a normalized signed directed graph.

    Args:
        kgml: KGML document text (or bytes).
        expand_groups: rewrite edges that touch a ``group`` entry onto each of its
            components (pitfall 2). The group node itself is always kept in
            ``nodes`` so a caller can see the complex; when this is True the group
            no longer appears as an edge endpoint.
        expand_members: emit one node per identifier instead of one per entry
            (pitfall 1). Off by default because of combinatorial fan-out.
        include_maplink: keep ``maplink`` relations as ordinary edges (pitfall 4).
            Off by default; the links are always reported under ``map_links``.
        link_enzymes: emit ``catalysis`` edges substrate -> enzyme -> product so the
            enzyme layer (ECrel) and the compound layer (reaction) are connected
            (pitfall 7). On by default: without it a metabolic map parses into two
            disconnected halves.
        merge_duplicate_entries: collapse entries that carry an identical member set
            into one node (pitfall 8). KEGG draws the same molecule in several
            places on a map, giving it several entry ids; keeping them separate
            breaks reachability. On by default — measured over six real maps it
            only ever merged components (hsa05200: 49 -> 32) and never split one,
            and the absorbed ids are kept on ``merged_entries``.

    Returns:
        A dict with ``pathway``, ``nodes``, ``edges``, ``groups``, ``map_links``,
        ``index`` and ``stats``. Every value is JSON-serializable.
    """
    if isinstance(kgml, bytes):
        kgml = kgml.decode("utf-8", errors="replace")

    try:
        root = ET.fromstring(kgml)
    except ET.ParseError as exc:  # noqa: PERF203 - single try is fine
        raise KGMLParseError(f"not well-formed XML: {exc}") from exc
    if root.tag != "pathway":
        raise KGMLParseError(
            f"root element is <{root.tag}>, expected <pathway> "
            "(did you fetch the HTML page instead of /kgml?)"
        )

    pathway = {
        "name": root.get("name"),
        "org": root.get("org"),
        "number": root.get("number"),
        "title": root.get("title"),
        "link": root.get("link"),
    }

    # --- pass 1: entries -------------------------------------------------- #
    entries: dict[str, dict[str, Any]] = {}
    map_links: list[dict[str, Any]] = []
    skipped_rendering = 0

    for el in root.findall("entry"):
        eid = el.get("id")
        if eid is None:
            continue
        etype = el.get("type") or "other"
        graphics = el.findall("graphics")
        gtype = graphics[0].get("type") if graphics else None
        gname = graphics[0].get("name") if graphics else None

        # Pitfall 6: rendering-only entries. In metabolic maps the reaction
        # "arrows" are drawn as entries with graphics/@type="line"; they are not
        # molecules and must never become nodes.
        if gtype == "line" and etype not in ("compound", "gene", "ortholog", "enzyme"):
            skipped_rendering += 1
            continue

        names = _split_names(el.get("name"))

        # Pitfall 4: a "map" entry is a pointer to another pathway.
        if etype == "map":
            map_links.append(
                {
                    "entry": eid,
                    "targets": names,
                    "title": (_split_labels(gname) or [None])[0],
                    "origin": "entry",
                }
            )
            continue

        if etype not in _MOLECULAR_ENTRY_TYPES:
            skipped_rendering += 1
            continue

        # Group entries carry the literal placeholder name="undefined"; their real
        # membership is the <component> list, so do not let the placeholder leak
        # into the identifier space.
        if etype == "group":
            names = []

        entries[eid] = {
            "entry": eid,
            "type": etype,
            "members": names,  # pitfall 1: ALWAYS a list
            "labels": _split_labels(gname),
            "components": [
                c.get("id") for c in el.findall("component") if c.get("id")
            ],  # pitfall 2
            "reactions": _split_names(el.get("reaction")),
            "link": el.get("link"),
        }

    # --- pass 2: relations ------------------------------------------------- #
    raw_edges: list[dict[str, Any]] = []
    dangling = 0

    for el in root.findall("relation"):
        e1, e2 = el.get("entry1"), el.get("entry2")
        rclass = el.get("type") or "unknown"

        subtypes: list[dict[str, str | None]] = [
            {"name": s.get("name"), "value": s.get("value")} for s in el.findall("subtype")
        ]

        if rclass == "maplink":
            map_links.append(
                {
                    "entry1": e1,
                    "entry2": e2,
                    "subtypes": subtypes,
                    "origin": "maplink",
                }
            )
            if not include_maplink:
                continue

        if e1 not in entries or e2 not in entries:
            # Endpoint was a map entry or a rendering artefact we dropped.
            dangling += 1
            continue

        effects: list[str] = []
        mechanisms: list[str] = []
        unknown_subtypes: list[str] = []
        via: list[dict[str, Any]] = []
        for s in subtypes:
            # Both attributes are optional in the DTD, so both arrive as str|None.
            # Narrow once here rather than at each use.
            sname, svalue = s["name"], s["value"]
            if not sname:
                continue  # a <subtype> with no @name carries no information
            if sname in _SIGN_BY_SUBTYPE:
                effects.append(sname)
            elif sname in _ENTRY_REF_SUBTYPES:
                # Pitfall 3: @value is an ENTRY ID, dereference it.
                ref = entries.get(svalue) if svalue else None
                via.append(
                    {
                        "subtype": sname,
                        "entry": svalue,
                        "members": ref["members"] if ref else [],
                        "labels": ref["labels"] if ref else [],
                        "resolved": ref is not None,
                    }
                )
            elif sname in _MECHANISM_SUBTYPES:
                mechanisms.append(sname)
            else:
                # Fail open: KEGG has added subtypes before. Keep it, but flag it
                # rather than silently filing it as a mechanism.
                unknown_subtypes.append(sname)

        # A relation may carry both activation and inhibition (it happens, e.g.
        # dual-function kinases). Collapsing that to whichever came last would
        # assert a direction the data does not support — emit sign 0 instead.
        signs = {_SIGN_BY_SUBTYPE[e] for e in effects}
        sign = signs.pop() if len(signs) == 1 else 0

        raw_edges.append(
            {
                "source": e1,
                "target": e2,
                "class": rclass,
                # ECrel is enzyme-enzyme *through a metabolite*: never a direct
                # physical interaction, and callers must be able to tell.
                "direct": rclass in ("PPrel", "GErel", "PCrel"),
                "sign": sign,
                "effects": effects,
                "mechanisms": mechanisms,
                "unknown_subtypes": unknown_subtypes,
                "via": via,
                "origin": "relation",
            }
        )

    # --- pass 3: reactions (metabolic edges) -------------------------------- #
    for el in root.findall("reaction"):
        # Pitfall 5: @id is the ENZYME's entry id; @name is the reaction accession.
        enzyme_entry = el.get("id")
        rnames = _split_names(el.get("name"))
        reversible = (el.get("type") or "irreversible") == "reversible"
        enzyme = entries.get(enzyme_entry) if enzyme_entry else None

        subs = [s.get("id") for s in el.findall("substrate") if s.get("id")]
        prods = [p.get("id") for p in el.findall("product") if p.get("id")]

        for s in subs:
            for p in prods:
                if s not in entries or p not in entries:
                    dangling += 1
                    continue
                base = {
                    "class": "reaction",
                    "direct": False,
                    "sign": 0,
                    "effects": [],
                    "mechanisms": [],
                    "unknown_subtypes": [],
                    "reaction": rnames,
                    "reversible": reversible,
                    "enzyme_entry": enzyme_entry,
                    "enzyme_members": enzyme["members"] if enzyme else [],
                    "via": [],
                    "origin": "reaction",
                }
                raw_edges.append({**base, "source": s, "target": p})
                if reversible:
                    raw_edges.append({**base, "source": p, "target": s})

        # PITFALL 7 — found by running scripts/kgml_probe.py over hsa00010 /
        # ko00010 / eco00010, not by reading the DTD.
        #
        # A metabolic map is really TWO graphs stacked on top of each other:
        #   * <relation type="ECrel">  connects ENZYME entries to ENZYME entries
        #   * <reaction>               connects COMPOUND entries to COMPOUND entries
        # Nothing in KGML joins the two layers, so a parser that stops here emits a
        # graph that is *disconnected by construction*: "what is downstream of
        # PFKM" traverses only enzymes and never reaches a metabolite, and
        # "downstream of glucose" never reaches an enzyme. The edge counts look
        # healthy (hsa00010: 120 edges) which is exactly why this is easy to miss.
        #
        # The enzyme is already known — it is reaction/@id (pitfall 5) — so bridge
        # the layers explicitly: substrate -> enzyme -> product.
        if link_enzymes and enzyme is not None and enzyme_entry in entries:
            cat = {
                "class": "catalysis",
                "direct": False,
                "sign": 0,
                "effects": [],
                "mechanisms": [],
                "unknown_subtypes": [],
                "reaction": rnames,
                "reversible": reversible,
                "enzyme_entry": enzyme_entry,
                "enzyme_members": enzyme["members"],
                "via": [],
                "origin": "reaction",
            }
            forward = [(s, enzyme_entry) for s in subs if s in entries]
            forward += [(enzyme_entry, p) for p in prods if p in entries]
            backward = (
                [(p, enzyme_entry) for p in prods if p in entries]
                + [(enzyme_entry, s) for s in subs if s in entries]
                if reversible
                else []
            )
            for src, tgt in forward + backward:
                raw_edges.append({**cat, "source": src, "target": tgt})

    # --- pass 4: group expansion ------------------------------------------- #
    groups = [
        {
            "entry": e["entry"],
            "components": e["components"],
            "component_members": [
                m for c in e["components"] for m in entries.get(c, {}).get("members", [])
            ],
            "labels": e["labels"],
        }
        for e in entries.values()
        if e["type"] == "group"
    ]

    def _endpoints(eid: str) -> list[tuple[str, bool]]:
        """Resolve an edge endpoint to concrete entries, expanding complexes."""
        e = entries.get(eid)
        if expand_groups and e and e["type"] == "group" and e["components"]:
            return [(c, True) for c in e["components"] if c in entries]
        return [(eid, False)]

    edges: list[dict[str, Any]] = []
    for edge in raw_edges:
        for src, src_grp in _endpoints(edge["source"]):
            for tgt, tgt_grp in _endpoints(edge["target"]):
                if src == tgt and edge["origin"] == "relation" and (src_grp or tgt_grp):
                    # Expanding a complex onto itself would fabricate self-loops.
                    continue
                new = dict(edge, source=src, target=tgt)
                if src_grp or tgt_grp:
                    new["expanded_from_group"] = {
                        "source": edge["source"] if src_grp else None,
                        "target": edge["target"] if tgt_grp else None,
                    }
                edges.append(new)

    # --- pass 5: node projection ------------------------------------------- #
    if expand_members:
        nodes, edges = _expand_members(entries, edges, expand_groups)
    else:
        nodes = [
            {
                "id": eid,
                "type": e["type"],
                "members": e["members"],
                "member_count": len(e["members"]),
                "labels": e["labels"],
                "label": e["labels"][0] if e["labels"] else (e["members"] or [eid])[0],
                "components": e["components"],
                "reactions": e["reactions"],
                "link": e["link"],
            }
            for eid, e in entries.items()
            # Once expanded, a group is structural metadata, not a graph node.
            if not (expand_groups and e["type"] == "group")
        ]

    if merge_duplicate_entries and not expand_members:
        nodes, edges = _merge_duplicate_entries(nodes, edges)

    edges = _dedupe_edges(edges)

    node_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    index = _build_index(nodes)

    return {
        "pathway": pathway,
        "nodes": nodes,
        "edges": edges,
        "groups": groups,
        "map_links": map_links,
        "index": index,
        "options": {
            "expand_groups": expand_groups,
            "expand_members": expand_members,
            "include_maplink": include_maplink,
            "link_enzymes": link_enzymes,
            "merge_duplicate_entries": merge_duplicate_entries,
        },
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "signed_edge_count": sum(1 for e in edges if e["sign"]),
            "direct_edge_count": sum(1 for e in edges if e["direct"]),
            "reaction_edge_count": sum(1 for e in edges if e["class"] == "reaction"),
            "catalysis_edge_count": sum(1 for e in edges if e["class"] == "catalysis"),
            **_connectivity(nodes, edges),
            "group_count": len(groups),
            "map_link_count": len(map_links),
            "multi_member_entries": sum(
                1 for e in entries.values() if len(e["members"]) > 1
            ),
            "total_identifiers": len({m for e in entries.values() for m in e["members"]}),
            "dangling_endpoints": dangling,
            "skipped_rendering_entries": skipped_rendering,
        },
    }


def _expand_members(
    entries: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    expand_groups: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One node per identifier (pitfall 1), with the entry recorded for provenance."""
    nodes: list[dict[str, Any]] = []
    members_of: dict[str, list[str]] = {}
    seen: set[str] = set()

    for eid, e in entries.items():
        if expand_groups and e["type"] == "group":
            continue
        ids = e["members"] or [f"entry:{eid}"]
        members_of[eid] = ids
        for i, mid in enumerate(ids):
            if mid in seen:
                continue
            seen.add(mid)
            nodes.append(
                {
                    "id": mid,
                    "type": e["type"],
                    "members": [mid],
                    "member_count": 1,
                    "labels": e["labels"],
                    "label": e["labels"][i] if i < len(e["labels"]) else mid,
                    "entries": [eid],
                    "components": [],
                    "reactions": e["reactions"],
                    "link": e["link"],
                }
            )

    out: list[dict[str, Any]] = []
    for edge in edges:
        srcs = members_of.get(edge["source"], [])
        tgts = members_of.get(edge["target"], [])
        for s in srcs:
            for t in tgts:
                if s == t:
                    continue
                out.append(
                    dict(edge, source=s, target=t, entry_pair=[edge["source"], edge["target"]])
                )
    return nodes, out


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """KGML repeats identical <relation> blocks; merge them.

    The reaction accession is part of the key on purpose: two *different*
    reactions can connect the same substrate/product pair (and a reversible
    reaction's back-edge can collide with a separate forward reaction). Keying on
    endpoints alone would silently merge distinct biochemistry into one edge.
    """
    merged: dict[tuple, dict[str, Any]] = {}
    for e in edges:
        key = (
            e["source"],
            e["target"],
            e["class"],
            e["sign"],
            tuple(sorted(e["effects"])),
            tuple(e.get("reaction") or ()),
        )
        if key in merged:
            prev = merged[key]
            prev["mechanisms"] = sorted(set(prev["mechanisms"]) | set(e["mechanisms"]))
            for v in e.get("via", []):
                if v not in prev.get("via", []):
                    prev.setdefault("via", []).append(v)
        else:
            merged[key] = dict(e)
    return list(merged.values())


def _merge_duplicate_entries(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collapse entries that carry an identical member set into one node (pitfall 8).

    KEGG lays out a metabolic map for readability, not as a graph: one metabolite
    is drawn wherever it is needed, each drawing getting its own ``<entry id>``.
    Pyruvate can be three separate entries in one map. Treated as three nodes they
    are three unconnected islands, and "is glucose upstream of pyruvate" depends on
    which pyruvate box the traversal happens to land in.

    The canonical node is the lowest entry id (numerically) of each member set; the
    ids it absorbed are kept on ``merged_entries`` so provenance back to the KGML
    is not lost.
    """
    canonical: dict[str, str] = {}
    by_members: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for n in nodes:
        if n["members"]:
            by_members[tuple(sorted(n["members"]))].append(n)

    kept: list[dict[str, Any]] = []
    for group in by_members.values():
        group.sort(key=lambda n: (len(n["id"]), n["id"]))
        head, rest = group[0], group[1:]
        head = dict(head, merged_entries=[n["id"] for n in rest])
        for n in rest:
            canonical[n["id"]] = head["id"]
        kept.append(head)
    # Nodes with no members (an unexpanded group) are never merge candidates.
    kept.extend(dict(n, merged_entries=[]) for n in nodes if not n["members"])

    remapped: list[dict[str, Any]] = []
    for e in edges:
        src = canonical.get(e["source"], e["source"])
        tgt = canonical.get(e["target"], e["target"])
        if src == tgt and e["class"] != "reaction":
            # Merging two drawings of one molecule must not invent a self-loop.
            continue
        remapped.append(dict(e, source=src, target=tgt))
    return kept, remapped


def _connectivity(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> dict[str, Any]:
    """Weakly-connected-component summary — the cheapest smoke test for pitfall 7.

    A metabolic map that parses into two big components of roughly equal size is
    the signature of an enzyme layer and a compound layer that were never joined.
    The ``isolated_by_type`` breakdown separates the two explanations for leftover
    islands: isolated *compounds* mean the organism lacks the enzyme for that step
    (real biology), isolated *gene/ortholog* boxes mean the parse lost an edge.
    """
    parent: dict[str, str] = {n["id"]: n["id"] for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        a, b = find(e["source"]), find(e["target"])
        if a != b:
            parent[a] = b

    sizes: dict[str, int] = defaultdict(int)
    for n in nodes:
        sizes[find(n["id"])] += 1
    ordered = sorted(sizes.values(), reverse=True)

    isolated_by_type: dict[str, int] = defaultdict(int)
    for n in nodes:
        if sizes[find(n["id"])] == 1:
            isolated_by_type[n["type"]] += 1

    # How many identifiers are drawn more than once on this map (pitfall 8).
    seen: dict[tuple[str, ...], int] = defaultdict(int)
    for n in nodes:
        if n["members"]:
            seen[tuple(sorted(n["members"]))] += 1

    return {
        "component_count": len(ordered),
        "largest_component": ordered[0] if ordered else 0,
        "isolated_nodes": sum(1 for s in ordered if s == 1),
        "isolated_by_type": dict(isolated_by_type),
        "duplicated_entries": sum(c - 1 for c in seen.values() if c > 1),
        "distinct_member_sets": len(seen),
    }


def _build_index(nodes: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """member-id -> node ids, and lowercased label -> node ids (for seeding by symbol)."""
    by_member: dict[str, list[str]] = defaultdict(list)
    by_label: dict[str, list[str]] = defaultdict(list)
    for n in nodes:
        for m in n["members"]:
            by_member[m].append(n["id"])
            # KEGG member ids are "org:geneid" / "cpd:C00076"; index the bare id too.
            if ":" in m:
                by_member[m.split(":", 1)[1]].append(n["id"])
        for lab in n["labels"]:
            by_label[lab.lower()].append(n["id"])
    return {"by_member": dict(by_member), "by_label": dict(by_label)}


# --------------------------------------------------------------------------- #
# Graph queries — the actual payoff over a passthrough wrapper
# --------------------------------------------------------------------------- #

Direction = Literal["downstream", "upstream", "both"]


def _adjacency(
    graph: dict[str, Any], direction: Direction
) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    adj: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for e in graph["edges"]:
        if direction in ("downstream", "both"):
            adj[e["source"]].append((e["target"], e))
        if direction in ("upstream", "both"):
            adj[e["target"]].append((e["source"], e))
    return adj


def resolve_seeds(graph: dict[str, Any], seeds: Iterable[str]) -> list[str]:
    """Accept node ids, KEGG member ids ('hsa:5290'), bare ids, or gene symbols."""
    idx = graph["index"]
    known = {n["id"] for n in graph["nodes"]}
    out: list[str] = []
    for s in seeds:
        if s in known:
            out.append(s)
            continue
        hits = idx["by_member"].get(s) or idx["by_label"].get(s.lower()) or []
        out.extend(hits)
    return list(dict.fromkeys(out))


def neighborhood(
    graph: dict[str, Any],
    seeds: Iterable[str],
    *,
    direction: Direction = "downstream",
    depth: int = 2,
    signed_only: bool = False,
) -> dict[str, Any]:
    """BFS from `seeds`, tracking distance and the net sign along the path.

    ``net_sign`` is the product of edge signs on the discovered shortest path:
    +1 net activation, -1 net inhibition, 0 if any edge on the path is unsigned
    (mechanism-only or metabolic). This is the query KGML can answer and Reactome
    RDF cannot.
    """
    seeds = list(seeds)
    start = resolve_seeds(graph, seeds)
    # Report seeds that matched nothing rather than silently narrowing the query.
    unresolved = [s for s in seeds if not resolve_seeds(graph, [s])]
    if not start:
        return {
            "seeds": [],
            "reached": [],
            "edges": [],
            "unresolved": unresolved,
        }

    adj = _adjacency(graph, direction)
    by_id = {n["id"]: n for n in graph["nodes"]}
    dist: dict[str, int] = {s: 0 for s in start}
    net: dict[str, int] = {s: 1 for s in start}
    used: list[dict[str, Any]] = []
    q = deque(start)

    while q:
        cur = q.popleft()
        if dist[cur] >= depth:
            continue
        for nxt, edge in adj.get(cur, []):
            if signed_only and not edge["sign"]:
                continue
            used.append(edge)
            if nxt in dist:
                continue
            dist[nxt] = dist[cur] + 1
            net[nxt] = net[cur] * edge["sign"]
            q.append(nxt)

    reached = [
        {
            "id": nid,
            "label": by_id[nid]["label"],
            "members": by_id[nid]["members"],
            "distance": d,
            "net_sign": net[nid],
        }
        for nid, d in sorted(dist.items(), key=lambda kv: (kv[1], kv[0]))
        if nid not in start
    ]
    return {
        "seeds": start,
        "unresolved": unresolved,
        "direction": direction,
        "depth": depth,
        "reached": reached,
        "edges": _dedupe_edges(used),
    }


def find_paths(
    graph: dict[str, Any],
    source: str,
    target: str,
    *,
    max_length: int = 4,
    max_paths: int = 20,
) -> list[dict[str, Any]]:
    """Enumerate simple directed paths source -> target, with the net sign of each."""
    srcs = resolve_seeds(graph, [source])
    tgts = set(resolve_seeds(graph, [target]))
    if not srcs or not tgts:
        return []
    adj = _adjacency(graph, "downstream")
    by_id = {n["id"]: n for n in graph["nodes"]}
    found: list[dict[str, Any]] = []

    def dfs(node: str, path: list[str], edges: list[dict[str, Any]], seen: set[str]):
        if len(found) >= max_paths or len(path) > max_length:
            return
        if node in tgts and len(path) > 1:
            sign = 1
            for e in edges:
                sign *= e["sign"]
            found.append(
                {
                    "nodes": [
                        {"id": n, "label": by_id[n]["label"]} for n in path
                    ],
                    "length": len(path) - 1,
                    "net_sign": sign,
                    "edges": [
                        {
                            "class": e["class"],
                            "sign": e["sign"],
                            "effects": e["effects"],
                            "mechanisms": e["mechanisms"],
                        }
                        for e in edges
                    ],
                }
            )
            return
        for nxt, edge in adj.get(node, []):
            if nxt in seen:
                continue
            dfs(nxt, path + [nxt], edges + [edge], seen | {nxt})

    for s in srcs:
        dfs(s, [s], [], {s})
    return found


def metabolic_gaps(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Enzyme boxes an organism-specific map draws but has no gene for.

    In an organism map (hsa00010, eco00010, ...) KEGG keeps the reference layout
    and marks the steps the organism *lacks* by leaving the box as an ``ortholog``
    entry with no ``<reaction>`` behind it — the white boxes in the rendered image.
    They come out of the parse as isolated ortholog nodes.

    This was confirmed arithmetically rather than assumed: across the reference map
    and two organism maps of glycolysis the identity held exactly, twice — counting
    ENTRY BOXES, i.e. with ``merge_duplicate_entries=False``.

        ko00010 reactions 63 - hsa00010 reactions 34 = 29 == hsa00010 isolated orthologs
        ko00010 reactions 63 - eco00010 reactions 35 = 28 == eco00010 isolated orthologs

    Under the DEFAULT ``merge_duplicate_entries=True`` the counts are 25 and 23,
    and both numbers are correct — they count different things. The identity above
    counts boxes; merging collapses a KO drawn twice on the map into one node, so
    the merged count is the number of DISTINCT missing steps (hsa00010 loses 4
    duplicate boxes, eco00010 loses 5). The distinct count is the biologically
    meaningful one, so callers should prefer the default.

    So this is a *result*, not a parse failure: the set of metabolic steps missing
    from an organism. Reactome cannot answer this at all, which is much of the
    argument for carrying KEGG in the first place.
    """
    degree: dict[str, int] = defaultdict(int)
    for e in graph["edges"]:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    return [
        {
            "id": n["id"],
            "label": n["label"],
            "members": n["members"],
            "reactions": n["reactions"],
        }
        for n in graph["nodes"]
        if n["type"] == "ortholog" and degree[n["id"]] == 0
    ]


def find_cycles(graph: dict[str, Any], *, max_length: int = 5, max_cycles: int = 50):
    """Bounded enumeration of directed cycles — i.e. feedback loops.

    Cycles with net_sign == -1 are negative feedback, +1 positive feedback. This
    is a structural claim about the pathway that no keyword search can surface.
    """
    adj = _adjacency(graph, "downstream")
    by_id = {n["id"]: n for n in graph["nodes"]}
    out: list[dict[str, Any]] = []
    seen_keys: set[tuple] = set()

    def dfs(start: str, node: str, path: list[str], edges: list[dict[str, Any]]):
        if len(out) >= max_cycles or len(path) > max_length:
            return
        for nxt, edge in adj.get(node, []):
            if nxt == start and len(path) >= 2:
                key = tuple(sorted(path))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                sign = 1
                for e in edges + [edge]:
                    sign *= e["sign"]
                out.append(
                    {
                        "nodes": [{"id": n, "label": by_id[n]["label"]} for n in path],
                        "length": len(path),
                        "net_sign": sign,
                        "feedback": (
                            "negative" if sign < 0 else "positive" if sign > 0 else "unsigned"
                        ),
                    }
                )
            elif nxt not in path and nxt > start:
                dfs(start, nxt, path + [nxt], edges + [edge])

    for n in sorted(by_id):
        dfs(n, n, [n], [])
    return out


# --------------------------------------------------------------------------- #
# Diagnostics — quantify what a naive parser would have gotten wrong
# --------------------------------------------------------------------------- #


def diagnose(kgml: str | bytes) -> dict[str, Any]:
    """Compare the correct parse against the naive one, pitfall by pitfall.

    Intended to be run over real maps to justify (or refute) the parser's
    complexity before any of it is wired into a tool surface.
    """
    correct = parse_kgml(kgml, expand_groups=True, include_maplink=False)
    naive = parse_kgml(
        kgml,
        expand_groups=False,
        include_maplink=True,
        link_enzymes=False,
        merge_duplicate_entries=False,
    )
    unlinked = parse_kgml(kgml, expand_groups=True, link_enzymes=False)
    unmerged = parse_kgml(kgml, expand_groups=True, merge_duplicate_entries=False)

    if isinstance(kgml, bytes):
        kgml = kgml.decode("utf-8", errors="replace")
    root = ET.fromstring(kgml)

    entries = root.findall("entry")
    multi = [e for e in entries if len(_split_names(e.get("name"))) > 1]

    # The honest form of "how much does a naive parse lose": compare SETS. Summing
    # (len - 1) per entry over-counts, because the same gene legitimately appears
    # in several boxes of one map — it would be counted as lost more than once.
    naive_ids = {
        _split_names(e.get("name"))[0]
        for e in entries
        if e.get("type") != "map" and _split_names(e.get("name"))
    }
    all_ids = {
        m
        for e in entries
        if e.get("type") != "map"
        for m in _split_names(e.get("name"))
    }
    naive_ids.discard("undefined")
    all_ids.discard("undefined")
    groups = [e for e in entries if e.get("type") == "group"]
    maps = [e for e in entries if e.get("type") == "map"]
    ecrel = [r for r in root.findall("relation") if r.get("type") == "ECrel"]
    maplink = [r for r in root.findall("relation") if r.get("type") == "maplink"]
    reversible = [r for r in root.findall("reaction") if r.get("type") == "reversible"]

    group_edges = 0
    group_ids = {g.get("id") for g in groups}
    for r in root.findall("relation"):
        if r.get("entry1") in group_ids or r.get("entry2") in group_ids:
            group_edges += 1

    ecrel_with_compound = sum(
        1
        for r in ecrel
        for s in r.findall("subtype")
        if s.get("name") in _ENTRY_REF_SUBTYPES
    )

    return {
        "pathway": correct["pathway"],
        "pitfalls": {
            "1_multi_id_entries": {
                "entries_with_multiple_ids": len(multi),
                # Set difference, not a per-entry sum — see the comment above.
                "identifiers_lost_by_naive_parse": len(all_ids - naive_ids),
                "total_identifiers": len(all_ids),
                "identifiers_a_naive_parse_keeps": len(naive_ids),
            },
            "2_group_complexes": {
                "groups": len(groups),
                "relations_touching_a_group": group_edges,
                "edges_that_would_dead_end": group_edges,
            },
            "3_ecrel_compound_refs": {
                "ecrel_relations": len(ecrel),
                "compound_subtypes_needing_dereference": ecrel_with_compound,
            },
            "4_cross_map_pointers": {
                "map_entries": len(maps),
                "maplink_relations": len(maplink),
                "phantom_edges_if_included": naive["stats"]["edge_count"]
                - parse_kgml(kgml, expand_groups=False, include_maplink=False)["stats"][
                    "edge_count"
                ],
            },
            "5_reactions": {
                "reactions": len(root.findall("reaction")),
                "reversible": len(reversible),
                "extra_edges_from_reversibility": len(reversible),
            },
            "6_rendering_entries": {
                "skipped": correct["stats"]["skipped_rendering_entries"],
            },
            # Pitfall 7 is invisible in edge counts — it only shows up in
            # connectivity, which is why it survived the synthetic fixture.
            "7_enzyme_compound_layers": {
                "components_without_catalysis_edges": unlinked["stats"][
                    "component_count"
                ],
                "largest_component_without": unlinked["stats"]["largest_component"],
                "components_with_catalysis_edges": correct["stats"]["component_count"],
                "largest_component_with": correct["stats"]["largest_component"],
                "catalysis_edges_added": correct["stats"]["catalysis_edge_count"],
            },
            # Pitfall 8: KEGG draws one metabolite in several places, each drawing
            # getting its own entry id. Also only visible in connectivity.
            "8_duplicate_layout_entries": {
                "duplicated_entries": unmerged["stats"]["duplicated_entries"],
                "distinct_member_sets": unmerged["stats"]["distinct_member_sets"],
                "nodes_before_merge": unmerged["stats"]["node_count"],
                "nodes_after_merge": correct["stats"]["node_count"],
                "components_before_merge": unmerged["stats"]["component_count"],
                "components_after_merge": correct["stats"]["component_count"],
                "isolated_before_merge": unmerged["stats"]["isolated_nodes"],
                "isolated_after_merge": correct["stats"]["isolated_nodes"],
                "isolated_by_type_before": unmerged["stats"]["isolated_by_type"],
                "isolated_by_type_after": correct["stats"]["isolated_by_type"],
            },
        },
        "correct": correct["stats"],
        "naive": naive["stats"],
    }
