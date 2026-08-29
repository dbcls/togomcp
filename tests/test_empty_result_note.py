"""`run_sparql` must diagnose an empty result rather than return a bare header.

Why this exists: in the 2026-07-27..08-29 production logs, `run_sparql` raised 163
times and returned HTTP 200 with an empty result 1,237 times. Agents did not react
to the second — abandonment after a zero-row result (50.0%) barely exceeded
abandonment after a SUCCESSFUL one (43.8%), and only 6.9% re-read the MIE, the same
rate as after a success. An empty body is indistinguishable from an answer.

The bodies asserted below were captured from a live Virtuoso endpoint on 2026-08-29
(`Accept: text/csv`), because the whole feature turns on which shapes are and are
not "empty" on the wire.
"""

from __future__ import annotations

import pytest

from togo_mcp.rdf_portal import _empty_result_note

# --- exact bodies, verified live 2026-08-29 -------------------------------- #
NO_ROWS = '"s","p"\n'                    # SELECT matching nothing
ASK_FALSE = '"bool"\n0\n'                # ASK {} that is false — a real ANSWER
COUNT_ZERO = '"n"\n0\n'                  # SELECT (COUNT(*) AS ?n), no GROUP BY
COUNT_SUM_ZERO = '"n","t"\n0,\n'         # SUM over an empty match is UNBOUND, not 0
HAS_DATA = '"s"\n"urn:x"\n'


def test_no_rows_is_diagnosed() -> None:
    note = _empty_result_note(NO_ROWS, "SELECT ?s ?p WHERE { ?s ?p ?o }")
    assert note is not None
    assert note.startswith("#")
    assert "0 rows" in note
    assert "not an endpoint error" in note


def test_note_names_both_causes_and_the_probe() -> None:
    """The point is not "0 rows" — an agent can see that. It is which of the two
    causes it is, since they need opposite answers."""
    note = _empty_result_note(NO_ROWS, "SELECT ?s WHERE { ?s ?p ?o }")
    assert "TRUE NEGATIVE" in note and "BROKEN PATTERN" in note
    assert "ASK {" in note, "must give the probe that distinguishes the two causes"


def test_ask_false_is_not_empty() -> None:
    """`ASK` false is an ANSWER. Flagging it would teach agents to distrust it."""
    assert _empty_result_note(ASK_FALSE, "ASK { ?s ?p ?o }") is None


@pytest.mark.parametrize("body", [COUNT_ZERO, COUNT_SUM_ZERO])
def test_zero_aggregate_is_diagnosed(body: str) -> None:
    """A structurally-fine, semantically-empty row: `COUNT` over nothing is one row
    of 0, so a row-count test cannot see it. This is the aggregate half of the same
    failure and gets the SAME message — that consistency is the point."""
    q = "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <g> { ?s <p> ?o } }"
    note = _empty_result_note(body, q)
    assert note is not None
    assert "EMPTY match" in note
    assert "TRUE NEGATIVE" in note and "BROKEN PATTERN" in note


def test_aggregate_with_group_by_is_left_alone() -> None:
    """With GROUP BY the same query returns 0 rows instead (verified live), so the
    no-rows branch owns it; the aggregate branch must not double-fire."""
    q = "SELECT ?s (COUNT(*) AS ?n) WHERE { ?s ?p ?o } GROUP BY ?s"
    assert _empty_result_note('"s","n"\n0,0\n', q) is None


def test_real_data_is_untouched() -> None:
    assert _empty_result_note(HAS_DATA, "SELECT ?s WHERE { ?s ?p ?o }") is None


def test_nonzero_aggregate_is_untouched() -> None:
    q = "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"
    assert _empty_result_note('"n"\n42\n', q) is None


# --- shape-aware additions ------------------------------------------------- #

def test_values_iri_block_gets_the_namespace_warning() -> None:
    """VALUES-with-IRIs was 17.6% empty vs 8.6% for literals, and is the verified
    MassBank/ChEMBL cross-namespace trap."""
    q = 'SELECT ?x WHERE { VALUES ?c { <http://rdf.ebi.ac.uk/resource/chembl/molecule/CHEMBL25> } ?c ?p ?x }'
    note = _empty_result_note(NO_ROWS, q)
    assert "DIFFERENT IRIs in different graphs" in note
    assert "trap #11" in note


def test_values_of_literals_does_not_get_the_iri_warning() -> None:
    q = 'SELECT ?x WHERE { VALUES ?n { "Trp53" "Cd4" } ?s ?p ?n }'
    note = _empty_result_note(NO_ROWS, q)
    assert "DIFFERENT IRIs in different graphs" not in note


def test_long_query_gets_the_bisect_advice() -> None:
    q = "SELECT ?s WHERE { ?s ?p ?o . " + "?s ?p2 ?o2 . " * 120 + "}"
    assert len(q) >= 1200
    note = _empty_result_note(NO_ROWS, q)
    assert "Bisect" in note


def test_at_most_two_shape_hints() -> None:
    """Past two the block stops being read, so the cap is load-bearing."""
    q = ('SELECT ?x WHERE { VALUES ?c { <http://example.org/a> } '
         'FILTER(?l = "x") ' + "?s ?p ?o . " * 120 + "}")
    note = _empty_result_note(NO_ROWS, q)
    assert note.count("SEEN HERE:") <= 2


def test_note_is_all_comment_lines() -> None:
    """Every line must be `#`-prefixed so the CSV body below stays parseable."""
    q = 'SELECT ?x WHERE { VALUES ?c { <http://example.org/a> } ?c ?p ?x }'
    note = _empty_result_note(NO_ROWS, q)
    assert all(ln.startswith("# ") for ln in note.splitlines())


# --- the tool actually prepends it, and clients are told ------------------- #

def test_run_sparql_prepends_the_note_and_keeps_the_csv(monkeypatch) -> None:
    """End-to-end through the tool: the note rides ABOVE the body, and the body
    survives. Prepending rather than replacing is what lets the aggregate case keep
    its real `0` while both empty kinds share one output shape."""
    import asyncio

    from togo_mcp import rdf_portal

    async def _fake(query, database="", endpoint_name="", endpoint_url=""):
        return NO_ROWS

    monkeypatch.setattr(rdf_portal, "execute_sparql", _fake)
    # `run_sparql` is a bare function under some FastMCP versions and a FunctionTool
    # under others; `.fn` unwraps the latter (cf. the note in CLAUDE.md).
    call = getattr(rdf_portal.run_sparql, "fn", rdf_portal.run_sparql)
    out = asyncio.run(
        call(sparql_query="SELECT ?s ?p WHERE { ?s ?p ?o }", database="uniprot")
    )
    assert out.endswith(NO_ROWS), "the CSV body must be preserved verbatim"
    assert out.startswith("# "), "the diagnosis must come first, where it is read"
    assert "TRUE NEGATIVE" in out


def test_run_sparql_leaves_a_populated_result_untouched(monkeypatch) -> None:
    import asyncio

    from togo_mcp import rdf_portal

    async def _fake(query, database="", endpoint_name="", endpoint_url=""):
        return HAS_DATA

    monkeypatch.setattr(rdf_portal, "execute_sparql", _fake)
    call = getattr(rdf_portal.run_sparql, "fn", rdf_portal.run_sparql)
    out = asyncio.run(
        call(sparql_query="SELECT ?s WHERE { ?s ?p ?o }", database="uniprot")
    )
    assert out == HAS_DATA


def test_served_description_states_the_empty_result_contract() -> None:
    """Asserted on what CLIENTS receive, not on `__doc__`.

    `run_sparql` carries an explicit `description=`, and FastMCP serves that INSTEAD
    of the docstring — it drops `Returns:` entirely. A return contract written in the
    docstring reaches nobody (that exact failure shipped once, fixed 2026-08-26).
    """
    import asyncio

    from togo_mcp.main import setup
    from togo_mcp.server import mcp

    async def _collect():
        await setup()
        return await mcp._list_tools()

    tool = next(t for t in asyncio.run(_collect()) if t.name == "run_sparql")
    desc = (tool.description or "").lower()
    assert "empty" in desc, "clients must be told the empty-result contract exists"
    assert "not an endpoint" in desc, (
        "the description must say an empty result is NOT an endpoint failure — an "
        "agent that reads it as one reports a false negative to the user"
    )
