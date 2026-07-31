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
OUT_FILE = (
    REPO_ROOT
    / "togo_mcp"
    / "data"
    / "resources"
    / "usage_guide_v6"
    / "02b_database_catalog.md"
)

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
    """Static appendix: tool surfaces that are NOT RDF Portal databases.

    Everything above this point is driven by an MIE `discovery:` block, which
    only exists for a SPARQL database. KEGG has neither an RDF Portal endpoint
    nor an MIE (by design — the MIE format describes a SPARQL schema), so it can
    never appear as a catalog row. Without a note here an agent has no way to
    learn that KEGG exists at all, or the two things that make it different:
    it is absent from the public HTTP server for licensing reasons, and its
    identifiers do not work in `run_sparql`.
    """
    return "\n".join([
        "**Not an RDF database — KEGG (local stdio server only):**",
        "",
        "KEGG is reachable through the `kegg_*` tools, NOT through `run_sparql`. It has "
        "no RDF Portal endpoint and no MIE file, so `database=\"kegg\"` is invalid on "
        "`run_sparql` and `get_MIE_file`.",
        "",
        "- **Availability.** The `kegg_*` tools exist ONLY on the local stdio server "
        "(`togo-mcp-local`). The public HTTP server at togomcp.rdfportal.org does not "
        "expose them: the KEGG API is licensed to academic users at academic "
        "institutions, and a public host cannot verify a caller's affiliation. "
        "**If you do not see `kegg_*` in your tool list, KEGG is unavailable to you** — "
        "use `reactome` or `rhea` over SPARQL instead, and do not report the absence "
        "as an error.",
        "- **What it uniquely adds.** A pathway map as a SIGNED DIRECTED GRAPH "
        "(activation vs inhibition per edge, from KGML relation subtypes), the FEEDBACK "
        "LOOPS that graph contains, and, for an organism map, the metabolic steps that "
        "organism LACKS. Reactome RDF has no equivalent of any of these, so they are not "
        "reproducible with `run_sparql`.",
        "- **Workflow.** `kegg_find` (keyword → entry IDs) → `kegg_get_entry` (full "
        "record incl. DBLINKS), `kegg_link` (gene↔pathway↔compound↔pubmed), "
        "`kegg_pathway_graph` (whole map), `kegg_pathway_neighborhood` (up/downstream of "
        "one gene), `kegg_pathway_paths` (how A reaches B, and the net sign of each "
        "route), `kegg_pathway_cycles` (negative/positive feedback loops).",
        "- **Reading signs.** Every graph tool returns "
        "`signal_quality.signed_edge_fraction` — how much of that map states a direction "
        "of regulation at all. It ranges from 0.98 to 0.40 across signaling maps and is 0 "
        "for metabolic ones, because most KGML relations record only a MECHANISM "
        "(phosphorylation, binding). Read a `net_sign` of 0, or an `unsigned` feedback "
        "loop, as UNKNOWN — never as \"no effect\".",
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

    content = build()

    if args.stdout:
        sys.stdout.write(content + "\n")
        return 0

    if args.check:
        current = OUT_FILE.read_text(encoding="utf-8") if OUT_FILE.exists() else ""
        if current != content + "\n":
            print(
                f"catalog OUT OF SYNC: {OUT_FILE.relative_to(REPO_ROOT)} differs from "
                "generator output. Run: python scripts/generate_usage_guide_catalog.py",
                file=sys.stderr,
            )
            return 1
        print("catalog in sync.")
        return 0

    OUT_FILE.write_text(content + "\n", encoding="utf-8")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
