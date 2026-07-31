#!/usr/bin/env python3
"""Validate togo_mcp/kgml.py against REAL KEGG maps.

WHY THIS IS A SEPARATE SCRIPT, AND WHY IT DOES NOT DOWNLOAD BY DEFAULT
---------------------------------------------------------------------
The KEGG API is licensed to "academic users belonging to academic institutions"
(https://www.kegg.jp/kegg/rest/), so the fetch must originate from your own
institutional network — not from CI, not from a cloud sandbox, not from a shared
service host. That is the same constraint that makes the planned `kegg` sub-server
stdio-only. This script therefore defaults to reading KGML files you already have
on disk, and only fetches when you pass --fetch explicitly.

Usage
-----
    # 1. Download the maps yourself (from an academic network), then:
    python scripts/kgml_probe.py kgml/hsa04151.xml kgml/hsa00010.xml

    # 2. Or let the script fetch, respecting the 3 req/s cap:
    python scripts/kgml_probe.py --fetch hsa04151 hsa00010 ko04010 eco00010

    # 3. Explore one map interactively:
    python scripts/kgml_probe.py kgml/hsa04151.xml --neighbors PIK3CA --depth 2
    python scripts/kgml_probe.py kgml/hsa04151.xml --path AKT1 MTOR
    python scripts/kgml_probe.py kgml/hsa04151.xml --cycles

Suggested validation set — each stresses a different pitfall:
    hsa04151  PI3K-Akt        many groups, deep multi-id entries
    hsa04010  MAPK            dense PPrel with mixed subtypes
    hsa00010  Glycolysis      reaction/ECrel heavy, reversible reactions
    ko00010   Glycolysis (KO) ortholog entries instead of genes
    eco00010  Glycolysis (E. coli)  prokaryote — the coverage KEGG uniquely adds
    hsa05200  Pathways in cancer    maplink-heavy, very large
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from togo_mcp.kgml import (  # noqa: E402
    KGMLParseError,
    diagnose,
    find_cycles,
    find_paths,
    metabolic_gaps,
    neighborhood,
    parse_kgml,
)

KEGG_KGML_URL = "https://rest.kegg.jp/get/{}/kgml"
MIN_INTERVAL = 1 / 3  # KEGG asks for <= 3 requests per second.


def fetch(map_id: str, cache: Path) -> str:
    """Fetch one KGML, caching to disk so a re-run costs no KEGG requests."""
    import httpx

    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{map_id}.xml"
    if path.exists():
        return path.read_text()
    resp = httpx.get(KEGG_KGML_URL.format(map_id), timeout=30.0)
    resp.raise_for_status()
    if not resp.text.strip():
        raise SystemExit(f"{map_id}: empty response (no KGML for this map?)")
    path.write_text(resp.text)
    time.sleep(MIN_INTERVAL)
    return resp.text


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:5.1f}%" if whole else "    - "


def report(label: str, kgml: str) -> dict:
    d = diagnose(kgml)
    p = d["pitfalls"]
    title = d["pathway"]["title"] or "(untitled)"
    print(f"\n=== {label}  {title}")
    print(f"    nodes {d['correct']['node_count']:5d}   edges {d['correct']['edge_count']:5d}"
          f"   identifiers {d['correct']['total_identifiers']:5d}")

    lost = p["1_multi_id_entries"]["identifiers_lost_by_naive_parse"]
    total = p["1_multi_id_entries"]["total_identifiers"]
    print(f"  1 multi-id entries      {p['1_multi_id_entries']['entries_with_multiple_ids']:5d}"
          f"   identifiers a naive parse drops: {lost:5d} ({_pct(lost, total)})")
    print(f"  2 group complexes       {p['2_group_complexes']['groups']:5d}"
          f"   relations that would dead-end:   {p['2_group_complexes']['relations_touching_a_group']:5d}")
    print(f"  3 ECrel relations       {p['3_ecrel_compound_refs']['ecrel_relations']:5d}"
          f"   compound refs to dereference:    {p['3_ecrel_compound_refs']['compound_subtypes_needing_dereference']:5d}")
    print(f"  4 map entries           {p['4_cross_map_pointers']['map_entries']:5d}"
          f"   maplink relations:               {p['4_cross_map_pointers']['maplink_relations']:5d}")
    print(f"  5 reactions             {p['5_reactions']['reactions']:5d}"
          f"   reversible (extra edges):        {p['5_reactions']['reversible']:5d}")
    print(f"  6 rendering entries     {p['6_rendering_entries']['skipped']:5d}")
    p7 = p["7_enzyme_compound_layers"]
    print(f"  7 layer split           "
          f"components {p7['components_without_catalysis_edges']:3d} -> "
          f"{p7['components_with_catalysis_edges']:3d}"
          f"   largest {p7['largest_component_without']:4d} -> {p7['largest_component_with']:4d}"
          f"   (+{p7['catalysis_edges_added']} catalysis edges)")

    c = d["correct"]
    print(f"    signed {c['signed_edge_count']:4d}/{c['edge_count']:<4d}"
          f" ({_pct(c['signed_edge_count'], c['edge_count'])})"
          f"   direct {c['direct_edge_count']:4d}"
          f"   metabolic {c['reaction_edge_count']:4d}"
          f"   catalysis {c['catalysis_edge_count']:4d}"
          f"   dangling {c['dangling_endpoints']:3d}")
    p8 = p["8_duplicate_layout_entries"]
    print(f"  8 duplicate drawings    {p8['duplicated_entries']:5d}"
          f"   nodes {p8['nodes_before_merge']:4d} -> {p8['nodes_after_merge']:4d}"
          f"   components {p8['components_before_merge']:4d} -> {p8['components_after_merge']:4d}"
          f"   isolated {p8['isolated_before_merge']:4d} -> {p8['isolated_after_merge']:4d}")

    print(f"    components {c['component_count']:4d}"
          f"   largest {c['largest_component']:4d}/{c['node_count']}"
          f"   isolated {c['isolated_nodes']:4d}  {dict(c['isolated_by_type'])}")
    gaps = metabolic_gaps(parse_kgml(kgml))
    if gaps:
        # Not a defect — see metabolic_gaps(). Steps this organism cannot perform.
        print(f"    metabolic gaps (ortholog boxes with no reaction): {len(gaps)}")
        print("      " + ", ".join(g["label"] for g in gaps[:12])
              + (" ..." if len(gaps) > 12 else ""))
    leftover = {
        k: v for k, v in p8["isolated_by_type_after"].items() if k != "ortholog"
    }
    if leftover:
        print(f"    isolated after merge, excluding gaps: {leftover}")

    unknown = sorted(
        {
            s
            for e in parse_kgml(kgml)["edges"]
            for s in e.get("unknown_subtypes", [])
        }
    )
    if unknown:
        print(f"    !! subtypes not in the DTD vocabulary: {unknown}")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="KGML file paths, or KEGG map ids with --fetch")
    ap.add_argument("--fetch", action="store_true", help="download from rest.kegg.jp (academic networks only)")
    ap.add_argument("--cache", type=Path, default=Path("kgml_cache"))
    ap.add_argument("--neighbors", metavar="SEED", help="show the neighborhood of SEED")
    ap.add_argument("--direction", default="downstream", choices=["downstream", "upstream", "both"])
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--path", nargs=2, metavar=("FROM", "TO"), help="enumerate signed paths")
    ap.add_argument("--cycles", action="store_true", help="list feedback loops")
    ap.add_argument("--json", action="store_true", help="dump the full parsed graph as JSON")
    args = ap.parse_args()

    if args.fetch:
        print("NOTE: fetching from rest.kegg.jp. The KEGG API is for academic users at\n"
              "      academic institutions; run this from your institutional network only.",
              file=sys.stderr)

    for target in args.targets:
        try:
            kgml = fetch(target, args.cache) if args.fetch else Path(target).read_text()
        except FileNotFoundError:
            print(f"{target}: no such file (did you mean --fetch?)", file=sys.stderr)
            return 2

        try:
            report(target, kgml)
            graph = parse_kgml(kgml)
        except KGMLParseError as exc:
            print(f"{target}: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(graph, indent=2, ensure_ascii=False))

        if args.neighbors:
            res = neighborhood(graph, [args.neighbors], direction=args.direction, depth=args.depth)
            if res["unresolved"]:
                print(f"    unresolved seed(s): {res['unresolved']}")
            print(f"    {args.direction} of {args.neighbors} (depth {args.depth}): "
                  f"{len(res['reached'])} nodes")
            for r in res["reached"][:40]:
                mark = {1: "+", -1: "-", 0: "?"}[r["net_sign"]]
                print(f"      d{r['distance']} [{mark}] {r['label']:<20} {','.join(r['members'][:4])}")

        if args.path:
            paths = find_paths(graph, args.path[0], args.path[1], max_length=args.depth + 2)
            print(f"    {len(paths)} path(s) {args.path[0]} -> {args.path[1]}")
            for p in paths[:15]:
                mark = {1: "activating", -1: "inhibiting", 0: "unsigned"}[p["net_sign"]]
                print(f"      ({mark:>10}) " + " -> ".join(n["label"] for n in p["nodes"]))

        if args.cycles:
            cycles = find_cycles(graph, max_length=args.depth + 2)
            neg = [c for c in cycles if c["feedback"] == "negative"]
            pos = [c for c in cycles if c["feedback"] == "positive"]
            print(f"    feedback loops: {len(neg)} negative, {len(pos)} positive, "
                  f"{len(cycles) - len(neg) - len(pos)} unsigned")
            for c in (neg + pos)[:15]:
                loop = [n["label"] for n in c["nodes"]]
                print(f"      [{c['feedback'][:3]}] " + " -> ".join(loop + [loop[0]]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
