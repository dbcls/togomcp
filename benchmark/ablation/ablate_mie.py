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

# Canonical 11 MIE top-level sections, in spec order (MIE_file_specs.md §2/§3).
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
                    help="Comma-separated sections to ablate (default: all 11)")
    args = ap.parse_args()

    mie_dir = Path(args.mie_dir)
    out_dir = Path(args.out)
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]

    unknown = [s for s in sections if s not in CANONICAL_SECTIONS]
    if unknown:
        print(f"ERROR: unknown section(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Valid: {', '.join(CANONICAL_SECTIONS)}", file=sys.stderr)
        return 2

    mie_files = sorted(mie_dir.glob("*.yaml"))
    if not mie_files:
        print(f"ERROR: no MIE files under {mie_dir}", file=sys.stderr)
        return 2

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
