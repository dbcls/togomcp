"""Drift guard: the intro page's "What's New" block must match the CHANGELOG markers.

The `#whats-new` section of `togo_mcp/data/docs/togomcp-intro.html` is generated
from the `<!-- whatsnew: DATE | text -->` markers in `CHANGELOG.md` by
`scripts/generate_whatsnew.py`. If the CHANGELOG markers change and the page is
not regenerated, the landing page's What's New silently goes stale. This test
fails on that drift.

Fix on failure: `python scripts/generate_whatsnew.py`
"""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN_PATH = REPO_ROOT / "scripts" / "generate_whatsnew.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_whatsnew", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_whatsnew_matches_changelog_markers():
    gen = _load_generator()
    expected = gen.build()
    committed = gen.HTML.read_text(encoding="utf-8")
    assert committed == expected, (
        "Intro page 'What's New' is out of sync with the CHANGELOG whatsnew markers. "
        "Run: python scripts/generate_whatsnew.py"
    )


def test_whatsnew_has_markers():
    """At least one marker must exist — an empty section is a mistake, not a state."""
    gen = _load_generator()
    assert gen.load_markers(), "no `whatsnew:` markers found in CHANGELOG.md"
