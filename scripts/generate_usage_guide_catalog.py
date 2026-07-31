#!/usr/bin/env python3
"""Generate the Database Catalog part of the TogoMCP Usage Guide.

The catalog bakes the per-database *semantic* layer — title, one-line
description, categories, keywords — from every MIE `discovery:` block into a
static guide section. It is the build-time replacement for the runtime
discovery trio (`find_databases` / `list_databases` / `list_categories`): the
bare NAME roster already lives in `DATABASE_DESCRIPTION` on
`run_sparql`/`get_MIE_file`, so this section supplies only what the schema
lacks — what each database is *for*, so an agent can pick by reading instead of
calling a tool.

Source of truth is the SERVED corpus (`togo_mcp/data/mie/*.yaml`), so the
catalog tracks whatever is actually being served (v2 today, v3 after the
release flip) with one code path. It reads the same `discovery`-or-`schema_info`
location the server's `_load_databases_cache` reads.

Usage:
    python scripts/generate_usage_guide_catalog.py           # write the part file
    python scripts/generate_usage_guide_catalog.py --check   # exit 1 if out of sync
    python scripts/generate_usage_guide_catalog.py --stdout   # print, don't write

The output is deterministic (stable sort, normalized whitespace); a CI/pytest
drift guard regenerates and asserts byte-identical to the committed file.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MIE_DIR = REPO_ROOT / "togo_mcp" / "data" / "mie"
GUIDE_DIR = REPO_ROOT / "togo_mcp" / "data" / "resources" / "usage_guide_v6"
OUT_FILE = GUIDE_DIR / "02b_database_catalog.md"

# Guide parts served ONLY when the tools they document are actually mounted.
# Deliberately in a SUBDIRECTORY: the guide assembles `sorted(glob("*.md"))` over
# the top level, so anything here is invisible to that glob and can never be
# served by accident to a client that lacks the tools.
LOCAL_ONLY_DIR = GUIDE_DIR / "local_only"
LOCAL_ONLY_KEGG = LOCAL_ONLY_DIR / "kegg.md"

# Proven keyword → database hints carried over from find_databases' docstring so
# nothing the tool taught is lost when it is retired.
PROVEN_HINTS = [
    ('"MANE"', "ensembl"),
    ('"drug targets"', "chembl"),
    ('"clinical variants"', "clinvar"),
    ('"pathways"', "reactome"),
    ('"gnomAD" / "variants"', "togovar"),
    ('"orthologs"', "oma"),
    ('"expression"', "bgee"),
    ('"glycobiology"', "glycosmos"),
    ('"superconductor"', "supercon"),
]


def _first_sentence(text: str, cap: int = 200) -> str:
    """Collapse whitespace and take the first sentence (or a capped prefix)."""
    flat = re.sub(r"\s+", " ", (text or "").strip())
    if not flat:
        return "(no description)"
    m = re.match(r"(.+?[.!?])(?:\s|$)", flat)
    out = m.group(1) if m else flat
    if len(out) > cap:
        out = out[: cap - 1].rstrip() + "…"
    return out


def load_records(mie_dir: Path = MIE_DIR) -> list[dict]:
    """Read the discovery block of every served MIE into catalog records.

    Mirrors the server's `_load_databases_cache`: read `discovery` (v3) or
    `schema_info` (v2), lowercase keywords/categories. Database key = filename.
    """
    records: list[dict] = []
    for path in sorted(mie_dir.glob("*.yaml")):
        db = path.stem
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:  # pragma: no cover - corrupt file
            raise SystemExit(f"catalog: cannot parse {path}: {exc}")
        disc = {}
        if isinstance(data, dict):
            disc = data.get("discovery") or data.get("schema_info") or {}
        if not isinstance(disc, dict):
            disc = {}
        records.append(
            {
                "database": db,
                "title": (disc.get("title") or "").strip() or db,
                "description": _first_sentence(disc.get("description") or ""),
                "keywords": [
                    str(k).lower() for k in (disc.get("keywords") or []) if str(k).strip()
                ],
                "categories": sorted(
                    str(c).lower() for c in (disc.get("categories") or []) if str(c).strip()
                ),
            }
        )
    return records


def render_catalog(records: list[dict]) -> str:
    """Render the deterministic markdown catalog section from records."""
    records = sorted(records, key=lambda r: r["database"])

    # category -> sorted member db names
    cat_index: dict[str, list[str]] = {}
    for r in records:
        for c in r["categories"] or ["(uncategorized)"]:
            cat_index.setdefault(c, []).append(r["database"])

    lines: list[str] = []
    lines.append("## 📚 DATABASE CATALOG")
    lines.append("")
    lines.append(
        f"All {len(records)} RDF databases, with what each is *for*. Scan by the KIND "
        "of data you need (not by entity name), pick 1–3 candidates, then "
        "`get_MIE_file(database)` before any `run_sparql`. The exact `database=` key is "
        "**bold**."
    )
    lines.append("")
    lines.append(
        "Quick hints: "
        + " · ".join(f"{kw} → `{db}`" for kw, db in PROVEN_HINTS)
        + "."
    )
    lines.append("")

    # Compact category index (replaces list_categories).
    lines.append("**By category** (a database may appear under several):")
    lines.append("")
    for cat in sorted(cat_index):
        members = " ".join(f"`{db}`" for db in sorted(cat_index[cat]))
        lines.append(f"- **{cat}** — {members}")
    lines.append("")

    # Alphabetical per-database rows (replaces list_databases + find_databases).
    lines.append("**All databases** (alphabetical):")
    lines.append("")
    for r in records:
        cats = ", ".join(r["categories"]) if r["categories"] else "—"
        kws = ", ".join(r["keywords"]) if r["keywords"] else "—"
        lines.append(
            f"- **{r['database']}** — {r['title']}. {r['description']} "
            f"_(categories: {cats})_  \n  keywords: {kws}"
        )
    lines.append("")
    return "\n".join(lines)


def render_non_sparql_companions() -> str:
    """The KEGG note that ships to EVERY client, on both transports.

    Everything above it is driven by an MIE `discovery:` block, which only exists
    for a SPARQL database. KEGG has neither an RDF Portal endpoint nor an MIE (by
    design — the MIE format describes a SPARQL schema), so it can never be a
    catalog row.

    This block is deliberately SHORT and says only what is true for a reader who
    may well have no `kegg_*` tools at all — the public HTTP server does not
    mount them. Its job is to stop an agent inventing `database="kegg"` and to
    tell it what to do when the tools are absent. The operating instructions live
    in `render_local_only_kegg()`, which is served only where the tools exist:
    shipping "call `kegg_find` then `kegg_conv`" to a client that has neither is
    at best noise and at worst an instruction to call something imaginary.
    """
    return "\n".join([
        "**Not an RDF Portal database — KEGG:**",
        "",
        "KEGG has no SPARQL endpoint and no MIE file, so `database=\"kegg\"` is invalid "
        "on `run_sparql` and `get_MIE_file` — there is no query you can write here that "
        "reaches it.",
        "",
        "**Check your tool list before offering KEGG to the user.** The `kegg_*` tools "
        "are mounted only by the local stdio server (`togo-mcp-local`): the KEGG API is "
        "licensed to academic users at academic institutions, and the public host at "
        "togomcp.rdfportal.org cannot verify a caller's affiliation, so it does not "
        "expose them. **If you see no `kegg_*` tool, KEGG is simply unavailable in this "
        "session** — answer pathway questions from `reactome` or `rhea` over SPARQL, and "
        "do not report the absence as an error or ask the user to retry. When the tools "
        "ARE present, this guide carries a KEGG section with the details.",
        "",
    ])


def render_local_only_kegg() -> str:
    """The KEGG operating instructions, served ONLY where the tools are mounted.

    Written for a reader who HAS the six `kegg_*` tools, so it can be direct. See
    `render_non_sparql_companions()` for why this is a separate file.
    """
    return "\n".join([
        "## 🧬 KEGG (available in this session)",
        "",
        "The `kegg_*` tools are mounted, so KEGG is usable here. It is NOT an RDF Portal "
        "database: no SPARQL endpoint, no MIE, and `database=\"kegg\"` is invalid on "
        "`run_sparql`.",
        "",
        "- **What it uniquely adds — two things.** (1) A pathway map as a SIGNED "
        "DIRECTED GRAPH: activation vs inhibition per edge, from KGML relation subtypes. "
        "(2) For an organism map, the metabolic steps that organism LACKS "
        "(`metabolic_gaps`). Reactome RDF has no equivalent of either, so neither is "
        "reproducible with `run_sparql`. **If a question does not depend on edge SIGN or "
        "on organism-specific absence, RDF Portal alone can usually answer it — prefer "
        "`reactome`/`rhea` there.**",
        "- **Workflow.** `kegg_find` (keyword → entry IDs) → `kegg_get_entry` (full "
        "record incl. DBLINKS), `kegg_link` (gene↔pathway↔compound↔pubmed), "
        "`kegg_pathway_graph` (whole map), `kegg_pathway_neighborhood` (up/downstream of "
        "one gene), `kegg_pathway_paths` (how A reaches B, and the net sign of the route).",
        "- **Signed claims: use `kegg_pathway_paths`, not `kegg_pathway_cycles`.** A "
        "`net_sign` needs only a PATH, whereas cycle detection needs a loop that KEGG "
        "actually drew closed on ONE map — and it usually did not. Measured over six real "
        "maps, `kegg_pathway_cycles` found ZERO signed cycles: canonical loops like "
        "p53/MDM2 have one arm on another map (hsa05200 draws `MDM2 -| TP53` but not "
        "`TP53 -> MDM2`), so they never close. **An empty cycle result means \"not drawn "
        "as a closed loop on this map\", NEVER \"no feedback exists\" — do not report the "
        "latter.** On metabolic maps cycle search is meaningless outright (no signed "
        "edges, and thousands of cycles from reversible reactions).",
        "- **Reading signs.** Every graph tool returns "
        "`signal_quality.signed_edge_fraction` — how much of that map states a direction "
        "of regulation at all. It ranges from 0.98 to 0.40 across signaling maps and is 0 "
        "for metabolic ones, because most KGML relations record only a MECHANISM "
        "(phosphorylation, binding). Read a `net_sign` of 0, or an `unsigned` feedback "
        "loop, as UNKNOWN — never as \"no effect\".",
        "- **Organism vs reference maps.** For \"which genes are in this pathway\" use the "
        "ORGANISM map (`hsa04151`, `eco00010`), not the `ko`/`map` reference map. On a "
        "METABOLIC map, `kegg_pathway_paths` needs a larger `max_length`: compounds are "
        "joined through their enzyme, so the hop count is about double the reaction count.",
        "- **Bridging to RDF Portal — REQUIRED.** KEGG-namespaced IDs (`hsa:10458`, "
        "`cpd:C00031`, `path:hsa04151`) do NOT resolve in any SPARQL database. Convert "
        "them with `kegg_conv` FIRST: genes ↔ `uniprot` / `ncbi-geneid` / "
        "`ncbi-proteinid`, chemicals ↔ `chebi` / `pubchem`. Only the converted "
        "identifiers belong in a `run_sparql` query or a TogoID call.",
        "- **Rate limit.** KEGG allows 3 requests/second and blocks abusers. An HTTP "
        "403/429 from a `kegg_*` tool means that cap or an access restriction was hit — "
        "do NOT retry it.",
        "",
    ])


def build() -> str:
    return render_catalog(load_records()) + "\n" + render_non_sparql_companions()


def build_local_only() -> str:
    return render_local_only_kegg()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed file is stale")
    ap.add_argument("--stdout", action="store_true", help="print to stdout, do not write")
    ap.add_argument(
        "--list-categories",
        action="store_true",
        help="print the canonical category vocabulary in use (replaces the retired list_categories tool)",
    )
    args = ap.parse_args(argv)

    if args.list_categories:
        cats = sorted({c for r in load_records() for c in r["categories"]})
        sys.stdout.write("\n".join(cats) + "\n")
        return 0

    # Both generated parts are checked/written together; a stale local-only file
    # is exactly as wrong as a stale catalog, it is just served to fewer clients.
    outputs = [(OUT_FILE, build()), (LOCAL_ONLY_KEGG, build_local_only())]

    if args.stdout:
        for path, content in outputs:
            sys.stdout.write(f"===== {path.relative_to(REPO_ROOT)} =====\n")
            sys.stdout.write(content + "\n")
        return 0

    if args.check:
        stale = [
            path
            for path, content in outputs
            if (path.read_text(encoding="utf-8") if path.exists() else "")
            != content + "\n"
        ]
        if stale:
            names = ", ".join(str(p.relative_to(REPO_ROOT)) for p in stale)
            print(
                f"guide OUT OF SYNC: {names} differs from generator output. "
                "Run: python scripts/generate_usage_guide_catalog.py",
                file=sys.stderr,
            )
            return 1
        print("catalog in sync.")
        return 0

    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
