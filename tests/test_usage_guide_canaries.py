"""Drift guard: the Usage Guide's stale-tool-list row must stay true to the tool registry.

The TROUBLESHOOTING table in `usage_guide_v6/04_reference.md` carries a row that
teaches the model to recognise a client whose cached tool list has gone stale —
the failure mode behind every phantom-tool call in the production log, all of
them from ChatGPT connectors, which record the list at *Scan Tools* time and
never refetch it. The row names tools in two opposite roles, and each role has
its own way of going wrong:

* **Canaries** — tools that DO exist. The model concludes "my list is stale" when
  one is absent from its own tool list. If a canary is ever renamed or removed,
  it vanishes from *every* client's list and the row fires for everyone: a
  universal false positive, telling healthy users to re-register, inside the one
  document that is supposed to be authoritative. That is the dangerous direction,
  and it would be self-inflicted by exactly the rename mechanic the row exists to
  explain.

* **Phantoms** — tools that do NOT exist, quoted as examples of the "unknown
  tool" error. If one is ever re-introduced (e.g. a `find_databases` redirect
  stub), the row starts citing a working call as evidence of breakage.

Both are silent in normal use — nothing fails at build time, and the damage lands
in someone else's chat session. Hence a test.

Note what is deliberately NOT asserted: that the canaries are the *newest* tools.
A canary added at time T detects every cache older than T, so leaving it alone as
new tools ship only makes it less sensitive — it under-detects, it never misfires.
Sensitivity is a judgement call for the release checklist; correctness is here.
"""

import asyncio
import re
from pathlib import Path

import pytest

from togo_mcp.main import mcp, setup

GUIDE_DIR = (
    Path(__file__).resolve().parent.parent
    / "togo_mcp" / "data" / "resources" / "usage_guide_v6"
)

# The row is identified by this phrase rather than by file or line, so it stays
# findable if it is reworded or moved to another part file.
_ROW_MARKER = "cached the tool list"

_CANARIES_RE = re.compile(r"canaries:\s*([^)]*)\)")
_PHANTOMS_RE = re.compile(r'unknown tool"\s*\(([^)]*)\)')
_BACKTICKED_RE = re.compile(r"`([^`]+)`")


def _stale_list_row() -> str:
    """The single guide line documenting a stale client tool list."""
    hits = [
        line
        for path in sorted(GUIDE_DIR.glob("*.md"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if _ROW_MARKER in line
    ]
    assert hits, (
        f"no Usage Guide row containing {_ROW_MARKER!r} — the stale-tool-list "
        "troubleshooting row was removed or reworded past recognition. It is the "
        "only channel that reaches a client whose cached tool list is stale; "
        "restore it, or delete this test deliberately."
    )
    assert len(hits) == 1, f"expected exactly one stale-tool-list row, found {len(hits)}"
    return hits[0]


def _names(pattern: re.Pattern, row: str, role: str) -> list[str]:
    match = pattern.search(row)
    assert match, f"stale-tool-list row no longer declares its {role} in the expected form"
    found = _BACKTICKED_RE.findall(match.group(1))
    assert found, f"stale-tool-list row declares no {role}"
    return found


@pytest.fixture(scope="module")
def registered_tool_names() -> set[str]:
    """Names of every tool on the fully-assembled public server."""
    async def _collect():
        await setup()  # mounts togoid / ncbi / togovar
        return {t.name for t in await mcp._list_tools()}

    return asyncio.run(_collect())


def test_canaries_are_real_tools(registered_tool_names: set[str]) -> None:
    """Every canary must exist, or the row fires for every healthy client."""
    row = _stale_list_row()
    missing = [n for n in _names(_CANARIES_RE, row, "canaries") if n not in registered_tool_names]
    assert not missing, (
        f"Usage Guide names canary tool(s) that no longer exist: {missing}. "
        "Every client would now see them absent from its tool list, so the "
        "stale-list row would tell healthy users to re-register their connector. "
        "Point the canaries at currently registered tools (prefer the newest ones — "
        "a canary only detects caches older than itself)."
    )


def test_phantom_examples_do_not_exist(registered_tool_names: set[str]) -> None:
    """The quoted 'unknown tool' examples must stay unregistered."""
    row = _stale_list_row()
    resurrected = [n for n in _names(_PHANTOMS_RE, row, "phantom examples") if n in registered_tool_names]
    assert not resurrected, (
        f"Usage Guide cites {resurrected} as example(s) of an 'unknown tool' error, "
        "but they are registered now — calling them succeeds, so the row cites a "
        "working call as evidence of a stale list. Replace the example(s) with names "
        "that are genuinely retired."
    )
