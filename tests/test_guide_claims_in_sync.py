"""Drift guard: `scripts/check_guide_claims.py` must keep checking what the guide says.

The claim-checker is a live script (endpoints are too unreliable for CI), so it runs
at release time — which leaves a gap this test fills. Each claim in that script names
an `anchor`: a substring that must still appear in the served Usage Guide. Without
this test the two can drift apart in both directions, and both are silent:

* **Guide edited, script not.** Someone rewrites the co-tenancy section; the checker
  keeps verifying a sentence nobody ships any more and keeps reporting "6 ok". The
  release passes while the guide's actual claims go unchecked.
* **Script edited, guide not.** A claim is dropped from the checker because it was
  awkward to run; the guide keeps asserting it to every client with nothing watching.

Anchoring is deliberately textual rather than structural. The guide is prose — there
is no id to key on — and the anchor is chosen to be the load-bearing phrase of the
claim, so an edit that changes the *meaning* almost always changes the anchor, while
reflowing a paragraph does not.

This test is offline and never touches the network. Whether the claims are still TRUE
is the script's job: `uv run python scripts/check_guide_claims.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GUIDE_DIR = REPO / "togo_mcp" / "data" / "resources" / "usage_guide_v6"
CHECKER = REPO / "scripts" / "check_guide_claims.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_guide_claims", CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def checker():
    assert CHECKER.exists(), f"missing {CHECKER}"
    return _load_checker()


@pytest.fixture(scope="module")
def guide_text() -> str:
    parts = [p.read_text(encoding="utf-8") for p in sorted(GUIDE_DIR.glob("*.md"))]
    assert parts, f"no guide sections found in {GUIDE_DIR}"
    return "\n".join(parts)


def test_checker_has_claims(checker):
    """Guard the guard: an empty CLAIMS list would make the anchor test vacuous."""
    assert len(checker.CLAIMS) >= 5, f"expected the full claim set, got {len(checker.CLAIMS)}"


def test_claim_ids_are_unique(checker):
    ids = [c["id"] for c in checker.CLAIMS]
    assert len(ids) == len(set(ids)), f"duplicate claim ids: {ids}"


def test_every_claim_endpoint_is_registered(checker):
    """A claim pointed at an endpoint that left the registry can never run."""
    for claim in checker.CLAIMS:
        # raises SystemExit if the endpoint_name is unknown
        assert checker.endpoint_url(claim["endpoint"]).startswith("http"), claim["id"]


@pytest.mark.parametrize(
    "claim_id,anchor",
    [(c["id"], c["anchor"]) for c in _load_checker().CLAIMS],
)
def test_claim_anchor_still_in_guide(claim_id: str, anchor: str, guide_text: str):
    """The guide must still make the claim the checker verifies."""
    assert anchor in guide_text, (
        f"claim {claim_id!r} anchors on text that is no longer in the Usage Guide:\n"
        f"    {anchor!r}\n"
        "  Either the guide was edited and the claim needs updating/removing in "
        "scripts/check_guide_claims.py, or the anchor needs re-pointing at the "
        "rewritten sentence. Do not just delete the claim — first check whether the "
        "guide still asserts it in different words."
    )
