"""Drift guard: query-provenance's references/reproduce.md must match the script.

reproduce.md pins a release-tag URL for `scripts/togomcp_reproduce.py` next to a full
copy of it. Both are generated from the script (`__version__`, `RELEASED_IN`) by
`scripts/generate_reproduce_reference.py`; if the script changes and the reference is
not regenerated, readers get a copy and a URL that disagree. This test fails on that.

Fix on failure: bump `__version__` and `RELEASED_IN` in the script if it changed in
this release, then `python scripts/generate_reproduce_reference.py`.
"""
import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_PATH = REPO_ROOT / "scripts" / "generate_reproduce_reference.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_reproduce_reference", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reproduce_reference_matches_script():
    gen = _load_generator()
    assert gen.OUTPUT.read_text(encoding="utf-8") == gen.build(), (
        "references/reproduce.md is stale; run `python scripts/generate_reproduce_reference.py`"
    )


def test_pinned_url_uses_a_release_tag():
    gen = _load_generator()
    tag = gen._constant(gen.SCRIPT.read_text(encoding="utf-8"), "RELEASED_IN")
    assert re.fullmatch(r"v\d+\.\d+\.\d+", tag), tag
