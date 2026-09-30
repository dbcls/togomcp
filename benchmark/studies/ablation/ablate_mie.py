#!/usr/bin/env python3
"""Generate section-ablated variants of the TogoMCP MIE corpus.

Each MIE YAML (togo_mcp/data/mie/*.yaml) is a set of top-level keys. For an
ablation study we need, for each key (or unit of keys) S, a full copy of the
corpus with exactly S removed from every file — served to the model by a local
togo-mcp server via TOGOMCP_MIE_DIR.

Two corpus formats are supported (--format). `v3` (the default) is the live
corpus since 2026-07-24: strippable keys V3_SECTIONS, grouped into V3_UNITS, with
V3_NEVER_STRIPPED kept in every condition (the minimum needed to address the
endpoint). `v2` is kept only to reproduce the 2026-07 sweeps against a v2 corpus
(--mie-dir pointing at one); it refuses to run on v3 files, which it would
silently leave untouched.

Removal is TEXTUAL, not a YAML round-trip. MIE files use extensive `|` block
scalars and column-0 comments that PyYAML/ruamel would reformat, which would
contaminate the ablation (the model would see a differently-formatted file, not
just a missing section). We instead delete the exact line range of the section's
top-level key — plus the contiguous comment/blank block immediately above it,
which documents that section — and leave every other byte untouched.

Outputs (default: mie_variants_v3/ for v3, mie_variants/ for v2):
    <out>/baseline/                 verbatim copy of the corpus
    <out>/no_mie/                   baseline copy for the tool-blocked no_mie condition
    <out>/ablate_<section>/         corpus with <section> removed everywhere
    <out>/ablate_group_<unit>/      corpus with every key of <unit> removed
    <out>/keep_<unit>/              corpus with every OTHER unit removed (leave-one-in)
    <out>/section_presence.csv      database x section boolean matrix
    <out>/manifest.json             source hashes, conditions, per-file byte deltas

Every condition is checked before the script exits 0: each file that carried a
stripped key must have lost bytes and no longer carry that key, and each
condition must strip something from at least one file. Any failure exits 1.

Usage:
    python ablate_mie.py                                  # v3: all single-key ablations
    python ablate_mie.py --sections examples --keep-groups examples   # 2026-10 stage 1
    python ablate_mie.py --groups all --keep-groups all
    python ablate_mie.py --format v2 --mie-dir <v2 corpus> --out mie_variants
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# ---------------------------------------------------------------------------
# v2 (historical)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# v3 (live corpus since 2026-07-24; MIE_v3_spec.md §2)
# ---------------------------------------------------------------------------
# Kept in every condition: without them the agent cannot address the endpoint at all,
# so stripping them would test "no MIE" badly rather than any content.
V3_NEVER_STRIPPED = ["mie_spec", "database", "endpoint", "base_uri", "graphs"]
# Strippable top-level keys, in spec order. `discovery` is not read at runtime by the
# server (only scripts/generate_usage_guide_catalog.py reads it, offline, to build
# 02b_database_catalog.md), so via get_MIE_file it is the only copy the agent sees.
V3_SECTIONS = ["discovery", "entity_counts", "global_gotchas", "examples",
               "schema_delta", "id_join_map"]
# Ablation units. `examples` is the load-bearing unit (v2 keep_query recovered 99% of the
# whole-MIE effect alone, and v3 removed the restatements that let other sections cover
# for it, spec §4.2). `header` = the two database-wide summaries; global_gotchas also
# feeds the trap banner get_MIE_file prints above the YAML, which is derived from the
# served text and so disappears with it.
V3_UNITS: dict[str, list[str]] = {
    "discovery": ["discovery"],
    "header": ["entity_counts", "global_gotchas"],
    "examples": ["examples"],
    "schema_delta": ["schema_delta"],
    "id_join_map": ["id_join_map"],
}

_v3_grouped = [s for members in V3_UNITS.values() for s in members]
assert sorted(_v3_grouped) == sorted(V3_SECTIONS), "V3_UNITS must partition V3_SECTIONS exactly"
assert not set(V3_SECTIONS) & set(V3_NEVER_STRIPPED)

FORMATS = {
    "v2": {"sections": CANONICAL_SECTIONS, "groups": GROUPS, "never": []},
    "v3": {"sections": V3_SECTIONS, "groups": V3_UNITS, "never": V3_NEVER_STRIPPED},
}

# Databases excluded from the ablation corpus entirely (by MIE file stem). SuperCon
# is a superconducting-materials DB with no benchmark question targeting it, so it
# carries no ablation signal and only adds served-corpus noise — keep it out of every
# variant. Override with --exclude-db (pass an empty value to exclude nothing).
EXCLUDED_DATABASES = {"supercon"}

# A column-0 top-level YAML key line, e.g. "schema_info:" or "critical_warnings: |".
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(\s|$)")

REPO_ROOT = Path(__file__).resolve().parents[3]  # benchmark/studies/ablation/ -> repo root
DEFAULT_MIE_DIR = REPO_ROOT / "togo_mcp" / "data" / "mie"
DEFAULT_OUT_DIRS = {
    "v2": Path(__file__).resolve().parent / "mie_variants",
    "v3": Path(__file__).resolve().parent / "mie_variants_v3",
}
V3_MARKER_RE = re.compile(r"^mie_spec:\s*3\b", re.MULTILINE)


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


def top_keys(text: str) -> set[str]:
    return {k for k in (_top_key(l) for l in text.splitlines()) if k}


def section_presence(text: str, sections: list[str] = CANONICAL_SECTIONS) -> dict[str, bool]:
    """Which of `sections` are present as top-level keys in `text`."""
    keys = top_keys(text)
    return {s: (s in keys) for s in sections}


def format_errors(fmt: str, texts: dict[str, str]) -> list[str]:
    """Refuse a corpus that does not match --format.

    The failure this guards is silent: v2 section names against a v3 corpus strip
    nothing, and every "ablated" condition is a duplicate baseline (2026-07-25 to
    2026-10). For v3 we also require every top-level key to be known, so a spec
    change that adds a key cannot slip past the never-stripped/strippable split.
    """
    errs = []
    known = set(FORMATS[fmt]["sections"]) | set(FORMATS[fmt]["never"])
    for name, t in texts.items():
        is_v3 = bool(V3_MARKER_RE.search(t))
        if fmt == "v3":
            if not is_v3:
                errs.append(f"{name}: no `mie_spec: 3` marker (not a v3 file)")
                continue
            unknown = top_keys(t) - known
            if unknown:
                errs.append(f"{name}: unknown top-level key(s) {sorted(unknown)}; "
                            f"classify them in V3_SECTIONS or V3_NEVER_STRIPPED")
        elif is_v3:
            errs.append(f"{name}: is a v3 file, but --format v2 would strip nothing from it")
    return errs


def check_condition(cond: str, strip: list[str], texts: dict[str, str],
                    out: dict[str, str]) -> list[str]:
    """Hard post-condition for one variant: it really lost what it claims to lose."""
    errs = []
    touched = 0
    for name, original in texts.items():
        had = [s for s in strip if s in top_keys(original)]
        if not had:
            continue
        touched += 1
        new = out[name]
        if len(new) >= len(original):
            errs.append(f"{cond}/{name}: had {had} but lost no bytes")
        left = [s for s in had if s in top_keys(new)]
        if left:
            errs.append(f"{cond}/{name}: still carries {left}")
    if touched == 0:
        errs.append(f"{cond}: strips nothing from any file (would be a duplicate baseline)")
    return errs


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    ap.add_argument("--format", choices=sorted(FORMATS), default="v3",
                    help="MIE corpus format (default v3, the live corpus). v2 only "
                         "reproduces the 2026-07 sweeps against a v2 corpus.")
    ap.add_argument("--mie-dir", default=str(DEFAULT_MIE_DIR),
                    help=f"Source MIE corpus (default: {DEFAULT_MIE_DIR})")
    ap.add_argument("--out", default=None,
                    help="Output root for variants (default: mie_variants_v3/ for v3, "
                         "mie_variants/ for v2)")
    ap.add_argument("--sections", default=None,
                    help="Comma-separated sections to ablate (default: every strippable "
                         "section of the format). Pass an empty value to build group "
                         "variants only.")
    ap.add_argument("--groups", default="",
                    help="Comma-separated GROUP variants to build (each removes every "
                         f"section in the group at once). v2: {', '.join(GROUPS)}; "
                         f"v3: {', '.join(V3_UNITS)}. "
                         "Use 'all' for all of them. Default: none. Group ablation is the "
                         "direct test of the redundancy that makes leave-one-out null — "
                         "see FINDINGS.md.")
    ap.add_argument("--keep-groups", default="",
                    help="Comma-separated LEAVE-ONE-IN variants to build (each KEEPS only that "
                         "group and strips every other one), from the same group names as "
                         "--groups. Use 'all' for every group. The complement of "
                         "--groups: tests whether a group is SUFFICIENT alone (paired against "
                         "no_mie), not whether it is necessary. Default: none.")
    ap.add_argument("--exclude-db", default=",".join(sorted(EXCLUDED_DATABASES)),
                    help="Comma-separated MIE file stems to omit from the corpus "
                         f"(default: {','.join(sorted(EXCLUDED_DATABASES)) or '(none)'}); "
                         "pass an empty value to exclude nothing")
    args = ap.parse_args()

    fmt = args.format
    ALL_SECTIONS: list[str] = FORMATS[fmt]["sections"]
    GROUPS_F: dict[str, list[str]] = FORMATS[fmt]["groups"]
    mie_dir = Path(args.mie_dir)
    out_dir = Path(args.out) if args.out else DEFAULT_OUT_DIRS[fmt]
    sections_arg = ",".join(ALL_SECTIONS) if args.sections is None else args.sections
    sections = [s.strip() for s in sections_arg.split(",") if s.strip()]
    excluded = {s.strip() for s in args.exclude_db.split(",") if s.strip()}

    unknown = [s for s in sections if s not in ALL_SECTIONS]
    if unknown:
        print(f"ERROR: unknown {fmt} section(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Valid: {', '.join(ALL_SECTIONS)}", file=sys.stderr)
        return 2

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    if groups == ["all"]:
        groups = list(GROUPS_F)
    unknown_g = [g for g in groups if g not in GROUPS_F]
    if unknown_g:
        print(f"ERROR: unknown group(s): {', '.join(unknown_g)}", file=sys.stderr)
        print(f"Valid: {', '.join(GROUPS_F)} (or 'all')", file=sys.stderr)
        return 2

    keep_groups = [g.strip() for g in args.keep_groups.split(",") if g.strip()]
    if keep_groups == ["all"]:
        keep_groups = list(GROUPS_F)
    unknown_k = [g for g in keep_groups if g not in GROUPS_F]
    if unknown_k:
        print(f"ERROR: unknown keep-group(s): {', '.join(unknown_k)}", file=sys.stderr)
        print(f"Valid: {', '.join(GROUPS_F)} (or 'all')", file=sys.stderr)
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

    texts: dict[str, str] = {f.name: f.read_text(encoding="utf-8") for f in mie_files}
    ferrs = format_errors(fmt, texts)
    if ferrs:
        print(f"ERROR: corpus {mie_dir} does not match --format {fmt}:", file=sys.stderr)
        for e in ferrs:
            print(f"  ! {e}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    # --- baseline (verbatim copy) ---------------------------------------
    baseline_dir = out_dir / "baseline"
    if baseline_dir.exists():
        shutil.rmtree(baseline_dir)
    baseline_dir.mkdir(parents=True)
    for f in mie_files:
        shutil.copy2(f, baseline_dir / f.name)
    # no_mie blocks get_MIE_file at the tool level (config_no_mie*.yaml), so the served
    # corpus is moot; run_ablation.py still needs a dir to boot the server on.
    if fmt == "v3":
        nomie_dir = out_dir / "no_mie"
        if nomie_dir.exists():
            shutil.rmtree(nomie_dir)
        shutil.copytree(baseline_dir, nomie_dir)

    # --- presence matrix -------------------------------------------------
    presence: dict[str, dict[str, bool]] = {
        Path(name).stem: section_presence(t, ALL_SECTIONS) for name, t in texts.items()}

    presence_path = out_dir / "section_presence.csv"
    with presence_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["database"] + ALL_SECTIONS)
        for db in sorted(presence):
            w.writerow([db] + [int(presence[db][s]) for s in ALL_SECTIONS])

    # --- one variant dir per ablated section ----------------------------
    manifest: dict = {
        "format": fmt,
        "source_mie_dir": str(mie_dir),
        "n_files": len(mie_files),
        "excluded_databases": sorted(excluded),
        "never_stripped": FORMATS[fmt]["never"],
        "sections": sections,
        "groups": {g: GROUPS_F[g] for g in groups},
        "keep_groups": {g: GROUPS_F[g] for g in keep_groups},
        # run_ablation.py compares these with the live corpus to refuse stale variants.
        "source_sha256": {name: _sha256(t) for name, t in sorted(texts.items())},
        "conditions": {},
    }
    warnings: list[str] = []
    errors: list[str] = []

    for section in sections:
        cond = f"ablate_{section}"
        cdir = out_dir / cond
        if cdir.exists():
            shutil.rmtree(cdir)
        cdir.mkdir(parents=True)

        removed_from = 0
        deltas: dict[str, int] = {}
        outs: dict[str, str] = {}
        for f in mie_files:
            original = texts[f.name]
            new_text, removed = strip_section(original, section)
            if removed:
                removed_from += 1
                deltas[f.name] = len(original) - len(new_text)
                if not _validates(new_text):
                    warnings.append(f"{cond}/{f.name}: result does not parse as YAML")
            (cdir / f.name).write_text(new_text, encoding="utf-8")
            outs[f.name] = new_text
        errors += check_condition(cond, [section], texts, outs)

        manifest["conditions"][cond] = {
            "section": section,
            "files_with_section": removed_from,
            "byte_deltas": deltas,
        }
        print(f"{cond:32s}  removed from {removed_from:2d}/{len(mie_files)} files")

    # --- one variant dir per ablated GROUP (all its sections removed at once) ---
    for group in groups:
        members = GROUPS_F[group]
        cond = f"ablate_group_{group}"
        cdir = out_dir / cond
        if cdir.exists():
            shutil.rmtree(cdir)
        cdir.mkdir(parents=True)

        touched = 0
        deltas: dict[str, int] = {}
        removed_counts: dict[str, int] = {s: 0 for s in members}
        outs = {}
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
            outs[f.name] = new_text
        errors += check_condition(cond, members, texts, outs)

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
        strip = [s for g, members in GROUPS_F.items() if g != group for s in members]
        cond = f"keep_{group}"
        cdir = out_dir / cond
        if cdir.exists():
            shutil.rmtree(cdir)
        cdir.mkdir(parents=True)

        touched = 0
        deltas: dict[str, int] = {}
        outs = {}
        for f in mie_files:
            original = texts[f.name]
            new_text, removed = strip_sections(original, strip)
            if removed:
                touched += 1
                deltas[f.name] = len(original) - len(new_text)
                if not _validates(new_text):
                    warnings.append(f"{cond}/{f.name}: result does not parse as YAML")
            (cdir / f.name).write_text(new_text, encoding="utf-8")
            outs[f.name] = new_text
        errors += check_condition(cond, strip, texts, outs)

        manifest["conditions"][cond] = {
            "keeps_group": group,
            "kept_sections": GROUPS_F[group],
            "stripped_sections": strip,
            "files_touched": touched,
            "byte_deltas": deltas,
        }
        print(f"{cond:32s}  kept only {group} ({len(GROUPS_F[group])} sec), stripped "
              f"{len(strip)} section(s) from {touched:2d}/{len(mie_files)} files")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nbaseline           -> {baseline_dir}")
    print(f"section_presence   -> {presence_path}")
    print(f"manifest           -> {out_dir / 'manifest.json'}")
    if warnings or errors:
        print("\nFAILED CHECKS:" if errors else "\nWARNINGS:", file=sys.stderr)
        for w in errors + warnings:
            print(f"  ! {w}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
