"""Drift guard: the committed Database Catalog guide part must match the generator.

The catalog (`usage_guide_v6/02b_database_catalog.md`) is generated from every
MIE `discovery:` block by `scripts/generate_usage_guide_catalog.py`. If a
database is added, removed, or re-described and the catalog is not regenerated,
the served Usage Guide silently goes stale. This test fails on that drift.

Fix on failure: `python scripts/generate_usage_guide_catalog.py`
"""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_PATH = REPO_ROOT / "scripts" / "generate_usage_guide_catalog.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_catalog", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_catalog_matches_generator():
    gen = _load_generator()
    expected = gen.build() + "\n"
    committed = gen.OUT_FILE.read_text(encoding="utf-8")
    assert committed == expected, (
        "Database Catalog is out of sync with the MIE discovery blocks. "
        "Run: python scripts/generate_usage_guide_catalog.py"
    )


def test_catalog_covers_every_served_database():
    """Every served MIE must appear as a catalog row — the retired discovery
    trio's list_databases contract."""
    gen = _load_generator()
    dbs = {r["database"] for r in gen.load_records()}
    catalog = gen.OUT_FILE.read_text(encoding="utf-8")
    missing = [db for db in dbs if f"**{db}**" not in catalog]
    assert not missing, f"databases absent from the catalog: {missing}"
