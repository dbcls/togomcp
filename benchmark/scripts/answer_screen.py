"""Classify a benchmark answer cell before its score is used (shared detector).

    refusal  a content-policy refusal: the answer IS the API's refusal text ("...appears to
             violate our Usage Policy..."), about 420 characters, scored at the floor by the
             judge. It measures the policy filter, not TogoMCP (ablation FINDINGS, Trap 8;
             it hit Q034/Q044 in the v3 equivalence run, unevenly across arms).
    stub     no real answer: success=False, a "Not logged in" login-error stub (the runner
             marks those success=True), an "[ERROR: ...]" placeholder, or an empty answer.
    valid    everything else.

Used by results_analyzer.py and the benchmark-runner skill's summarize_run.py, so both
exclude the same cells. Report raw and clean numbers side by side; never drop silently.
"""
from __future__ import annotations

import re

REFUSAL_RE = re.compile(r"violate our Usage Policy|unable to respond to this request", re.I)
STUB_RE = re.compile(r"Not logged in|^\[(SYSTEM )?ERROR:|Empty response from claude-agent-sdk", re.I)


def classify(answer: str | None, success: str | bool | None = None) -> str:
    """Return 'refusal', 'stub' or 'valid' for one arm of one row."""
    a = (answer or "").strip()
    if REFUSAL_RE.search(a):
        return "refusal"
    if str(success).strip().lower() in ("false", "0") or not a or STUB_RE.search(a):
        return "stub"
    return "valid"
