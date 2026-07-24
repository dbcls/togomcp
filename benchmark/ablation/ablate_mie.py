#!/usr/bin/env python3
"""Generate section-ablated variants of the TogoMCP MIE corpus.

Each MIE YAML (togo_mcp/data/mie/*.yaml) has 11 canonical top-level sections.
For a leave-one-out ablation study we need, for each section S, a full copy of
the corpus with exactly S removed from every file — served to the model by a
local togo-mcp server via TOGOMCP_MIE_DIR.

Removal is TEXTUAL, not a YAML round-trip. MIE files use extensive `|` block
scalars and column-0 comments that PyYAML/ruamel would reformat, which would
contaminate the ablation (the model would see a differently-formatted file, not
just a missing section). We instead delete the exact line range of the section's
top-level key — plus the contiguous comment/blank block immediately above it,
which documents that section — and leave every other byte untouched.

Outputs (default under this script's directory):
    mie_variants/baseline/                 verbatim copy of the corpus
    mie_variants/ablate_<section>/         corpus with <section> removed everywhere
    mie_variants/section_presence.csv      database x section boolean matrix
    mie_variants/manifest.json             conditions + per-file byte deltas

Usage:
    python ablate_mie.py                   # default source + output dirs
    python ablate_mie.py --mie-dir <dir> --out <dir>
    python ablate_mie.py --sections shape_expressions,sparql_query_examples
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# Canonical 11 MIE top-level sections of the v2 format, in spec order. This harness is a
# historical v2 artifact (the 2026-07 ablation sweeps); the v2 spec that defined these sections
# (MIE_file_specs.md) was retired 2026-07-25 when the corpus flipped to v3 — see git history, or
# togo_mcp/data/docs/MIE_v3_spec.md §1.3 for the v2→v3 section mapping.
CANONICAL_SECTIONS = [
    "schema_info",
    "critical_warnings",
    "shape_expressions",
    "sample_rdf_entries",
    "sparql_query_examples",
    "cross_database_queries",
    "cross_references",
    "architectural_notes",
    "data_statistics",
    "anti_patterns",
    "common_errors",
]

# Functional groups, for GROUP ablation (condition `ablate_group_<name>`).
#
# Leave-one-out only measures a section's MARGINAL value — with 10 redundant siblings
# left in place to cover for it, all 11 single-section contributions came back
# indistinguishable from zero in the 2026-07 sweep (see FINDINGS.md). That null does
# NOT license deleting sections: individually-droppable is not jointly-droppable.
# Removing a whole functional group at once is the direct test, and it wins twice —
# redundancy can't compensate (bigger effects) and it needs 4 conditions instead of 12
# (cheaper, and a lower multiple-comparison bar: |z|>2.39 for k=3 vs |z|>2.84 for k=11).
#
# The groups partition CANONICAL_SECTIONS exactly (asserted below), so together they
# account for the whole MIE.
GROUPS: dict[str, list[str]] = {
    # everything that helps the agent CONSTRUCT a query
    "query": ["schema_info", "shape_expressions", "sparql_query_examples",
              "cross_references", "cross_database_queries"],
    # everything that warns it OFF a wrong query
    "guardrails": ["critical_warnings", "common_errors", "anti_patterns"],
    # everything that ORIENTS it in the database
    "orientation": ["architectural_notes", "data_statistics", "sample_rdf_entries"],
}

_grouped = [s for members in GROUPS.values() for s in members]
assert sorted(_grouped) == sorted(CANONICAL_SECTIONS), (
    "GROUPS must partition CANONICAL_SECTIONS exactly "
    f"(missing: {sorted(set(CANONICAL_SECTIONS) - set(_grouped))}, "
    f"extra: {sorted(set(_grouped) - set(CANONICAL_SECTIONS))}, "
    f"duplicated: {sorted({s for s in _grouped if _grouped.count(s) > 1})})"
)

# Databases excluded from the ablation corpus entirely (by MIE file stem). SuperCon
# is a superconducting-materials DB with no benchmark question targeting it, so it
# carries no ablation signal and only adds served-corpus noise — keep it out of every
# variant. Override with --exclude-db (pass an empty value to exclude nothing).
EXCLUDED_DATABASES = {"supercon"}

# A column-0 top-level YAML key line, e.g. "schema_info:" or "critical_warnings: |".
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(\s|$)")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIE_DIR = REPO_ROOT / "togo_mcp" / "data" / "mie"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "mie_variants"


def _top_key(line: str) -> str | None:
    """Return the top-level key named on `line`, or None if it isn't one."""
    m = TOP_KEY_RE.match(line)
    return m.group(1) if m else None


def find_section_span(lines: list[str], section: str) -> tuple[int, int] | None:
    """Return (start, end) half-open line indices covering `section` in `lines`.

    Convention: the comment/blank block between two sections documents the LOWER
    (next) section. So the span (a) absorbs the contiguous comment/blank block
    immediately ABOVE this section's key line — its own docs — and (b) runs up to
    the next top-level key, then backs off over that key's own leading
    comment/blank block so it stays attached to the next section. Otherwise
    removing section A would also strip section B's documentation comment.
    Returns None if the section is absent.
    """
    key_idx = None
    for i, line in enumerate(lines):
        if _top_key(line) == section:
            key_idx = i
            break
    if key_idx is None:
        return None

    # End = next top-level key (or EOF).
    end = len(lines)
    for j in range(key_idx + 1, len(lines)):
        if _top_key(lines[j]) is not None:
            end = j
            break

    # Back the end off over the next section's leading comment/blank block,
    # leaving it attached to that section (never crossing back into our own key).
    while end - 1 > key_idx:
        prev = lines[end - 1]
        if prev.strip() == "" or prev.lstrip().startswith("#"):
            end -= 1
        else:
            break

    # Absorb the contiguous comment/blank block directly above our key line.
    start = key_idx
    while start - 1 >= 0:
        prev = lines[start - 1]
        if prev.strip() == "" or prev.lstrip().startswith("#"):
            start -= 1
        else:
            break
    return start, end


def strip_section(text: str, section: str) -> tuple[str, bool]:
    """Remove `section` from MIE `text`. Returns (new_text, removed?)."""
    lines = text.splitlines(keepends=True)
    span = find_section_span(lines, section)
    if span is None:
        return text, False
    start, end = span
    new_lines = lines[:start] + lines[end:]
    return "".join(new_lines), True


def strip_sections(text: str, sections: list[str]) -> tuple[str, list[str]]:
    """Remove every section in `sections`. Returns (new_text, sections actually removed).

    Applied one at a time: each strip re-scans the shrunken text, so the spans stay
    correct as earlier removals shift line numbers.
    """
    removed: list[str] = []
    for s in sections:
        text, did = strip_section(text, s)
        if did:
            removed.append(s)
    return text, removed


def section_presence(text: str) -> dict[str, bool]:
    """Which canonical sections are present as top-level keys in `text`."""
    keys = {k for k in (_top_key(l) for l in text.splitlines()) if k}
    return {s: (s in keys) for s in CANONICAL_SECTIONS}


def _validates(text: str) -> bool:
    if yaml is None:
        return True  # can't check; assume ok
    try:
        yaml.safe_load(text)
        return True
    except yaml.YAMLError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mie-dir", default=str(DEFAULT_MIE_DIR),
                    help=f"Source MIE corpus (default: {DEFAULT_MIE_DIR})")
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR),
                    help=f"Output root for variants (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--sections", default=",".join(CANONICAL_SECTIONS),
                    help="Comma-separated sections to ablate (default: all 11). "
                         "Pass an empty value to build group variants only.")
    ap.add_argument("--groups", default="",
                    help="Comma-separated GROUP variants to build (each removes every "
                         f"section in the group at once): {', '.join(GROUPS)}. "
                         "Use 'all' for all of them. Default: none. Group ablation is the "
                         "direct test of the redundancy that makes leave-one-out null — "
                         "see FINDINGS.md.")
    ap.add_argument("--keep-groups", default="",
                    help="Comma-separated LEAVE-ONE-IN variants to build (each KEEPS only that "
                         f"group and strips the other two): {', '.join(GROUPS)}. Use 'all' for "
                         "keep_query, keep_guardrails, keep_orientation. The complement of "
                         "--groups: tests whether a group is SUFFICIENT alone (paired against "
                         "no_mie), not whether it is necessary. Default: none.")
    ap.add_argument("--exclude-db", default=",".join(sorted(EXCLUDED_DATABASES)),
                    help="Comma-separated MIE file stems to omit from the corpus "
                         f"(default: {','.join(sorted(EXCLUDED_DATABASES)) or '(none)'}); "
                         "pass an empty value to exclude nothing")
    args = ap.parse_args()

    mie_dir = Path(args.mie_dir)
    out_dir = Path(args.out)
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    excluded = {s.strip() for s in args.exclude_db.split(",") if s.strip()}

    unknown = [s for s in sections if s not in CANONICAL_SECTIONS]
    if unknown:
        print(f"ERROR: unknown section(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Valid: {', '.join(CANONICAL_SECTIONS)}", file=sys.stderr)
        return 2

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    if groups == ["all"]:
        groups = list(GROUPS)
    unknown_g = [g for g in groups if g not in GROUPS]
    if unknown_g:
        print(f"ERROR: unknown group(s): {', '.join(unknown_g)}", file=sys.stderr)
        print(f"Valid: {', '.join(GROUPS)} (or 'all')", file=sys.stderr)
        return 2

    keep_groups = [g.strip() for g in args.keep_groups.split(",") if g.strip()]
    if keep_groups == ["all"]:
        keep_groups = list(GROUPS)
    unknown_k = [g for g in keep_groups if g not in GROUPS]
    if unknown_k:
        print(f"ERROR: unknown keep-group(s): {', '.join(unknown_k)}", file=sys.stderr)
        print(f"Valid: {', '.join(GROUPS)} (or 'all')", file=sys.stderr)
        return 2

    if not sections and not groups and not keep_groups:
        print("ERROR: nothing to build — pass --sections, --groups, and/or --keep-groups",
              file=sys.stderr)
        return 2

    mie_files = sorted(mie_dir.glob("*.yaml"))
    if not mie_files:
        print(f"ERROR: no MIE files under {mie_dir}", file=sys.stderr)
        return 2

    if excluded:
        kept = [f for f in mie_files if f.stem not in excluded]
        dropped = sorted(f.stem for f in mie_files if f.stem in excluded)
        missing = sorted(excluded - {f.stem for f in mie_files})
        if dropped:
            print(f"excluded {len(dropped)} database(s) from corpus: {', '.join(dropped)}")
        if missing:
            print(f"NOTE: --exclude-db named absent file(s): {', '.join(missing)}",
                  file=sys.stderr)
        mie_files = kept

    out_dir.mkdir(parents=True, exist_ok=True)

    # --- baseline (verbatim copy) ---------------------------------------
    baseline_dir = out_dir / "baseline"
    if baseline_dir.exists():
        shutil.rmtree(baseline_dir)
    baseline_dir.mkdir(parents=True)
    for f in mie_files:
        shutil.copy2(f, baseline_dir / f.name)

    # --- presence matrix -------------------------------------------------
    presence: dict[str, dict[str, bool]] = {}
    texts: dict[str, str] = {}
    for f in mie_files:
        t = f.read_text(encoding="utf-8")
        texts[f.name] = t
        presence[f.stem] = section_presence(t)

    presence_path = out_dir / "section_presence.csv"
    with presence_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["database"] + CANONICAL_SECTIONS)
        for db in sorted(presence):
            w.writerow([db] + [int(presence[db][s]) for s in CANONICAL_SECTIONS])

    # --- one variant dir per ablated section ----------------------------
    manifest: dict = {
        "source_mie_dir": str(mie_dir),
        "n_files": len(mie_files),
        "sections": sections,
        "groups": {g: GROUPS[g] for g in groups},
        "conditions": {},
    }
    warnings: list[str] = []

    for section in sections:
        cond = f"ablate_{section}"
        cdir = out_dir / cond
        if cdir.exists():
            shutil.rmtree(cdir)
        cdir.mkdir(parents=True)

        removed_from = 0
        deltas: dict[str, int] = {}
        for f in mie_files:
            original = texts[f.name]
            new_text, removed = strip_section(original, section)
            if removed:
                removed_from += 1
                deltas[f.name] = len(original) - len(new_text)
                if not _validates(new_text):
                    warnings.append(f"{cond}/{f.name}: result does not parse as YAML")
            (cdir / f.name).write_text(new_text, encoding="utf-8")

        manifest["conditions"][cond] = {
            "section": section,
            "files_with_section": removed_from,
            "byte_deltas": deltas,
        }
        print(f"{cond:32s}  removed from {removed_from:2d}/{len(mie_files)} files")

    # --- one variant dir per ablated GROUP (all its sections removed at once) ---
    for group in groups:
        members = GROUPS[group]
        cond = f"ablate_group_{group}"
        cdir = out_dir / cond
        if cdir.exists():
            shutil.rmtree(cdir)
        cdir.mkdir(parents=True)

        touched = 0
        deltas: dict[str, int] = {}
        removed_counts: dict[str, int] = {s: 0 for s in members}
        for f in mie_files:
            original = texts[f.name]
            new_text, removed = strip_sections(original, members)
            if removed:
                touched += 1
                deltas[f.name] = len(original) - len(new_text)
                for s in removed:
                    removed_counts[s] += 1
                if not _validates(new_text):
                    warnings.append(f"{cond}/{f.name}: result does not parse as YAML")
            (cdir / f.name).write_text(new_text, encoding="utf-8")

        manifest["conditions"][cond] = {
            "group": group,
            "sections": members,
            "files_touched": touched,
            "files_per_section": removed_counts,
            "byte_deltas": deltas,
        }
        print(f"{cond:32s}  removed {len(members)} section(s) from {touched:2d}/"
              f"{len(mie_files)} files  ({', '.join(members)})")

    # --- one variant dir per LEAVE-ONE-IN group (keep only it; strip the other two) ---
    for group in keep_groups:
        strip = [s for g, members in GROUPS.items() if g != group for s in members]
        cond = f"keep_{group}"
        cdir = out_dir / cond
        if cdir.exists():
            shutil.rmtree(cdir)
        cdir.mkdir(parents=True)

        touched = 0
        deltas: dict[str, int] = {}
        for f in mie_files:
            original = texts[f.name]
            new_text, removed = strip_sections(original, strip)
            if removed:
                touched += 1
                deltas[f.name] = len(original) - len(new_text)
                if not _validates(new_text):
                    warnings.append(f"{cond}/{f.name}: result does not parse as YAML")
            (cdir / f.name).write_text(new_text, encoding="utf-8")

        manifest["conditions"][cond] = {
            "keeps_group": group,
            "kept_sections": GROUPS[group],
            "stripped_sections": strip,
            "files_touched": touched,
            "byte_deltas": deltas,
        }
        print(f"{cond:32s}  kept only {group} ({len(GROUPS[group])} sec), stripped "
              f"{len(strip)} section(s) from {touched:2d}/{len(mie_files)} files")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nbaseline           -> {baseline_dir}")
    print(f"section_presence   -> {presence_path}")
    print(f"manifest           -> {out_dir / 'manifest.json'}")
    if warnings:
        print("\nWARNINGS:", file=sys.stderr)
        for w in warnings:
            print(f"  ! {w}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
