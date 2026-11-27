"""`run_sparql` must warn when a dataset clause leaves a GRAPH block outside the dataset.

Why this exists (Usage Guide trap #12): with `FROM <A>` (or `FROM NAMED <A>`) present, a
`GRAPH <B> { ... }` naming a graph the clause does not list matches nothing. Measured
2026-11-27 on every Virtuoso endpoint tried: SELECT gives 0 rows, but ASK gives TRUE and
COUNT(*) gives 1 whatever the data (true counts 38 and 23,858; a nonexistent subject; a
nonexistent graph). The empty-result note cannot catch the ASK/COUNT case, because the
body is not empty, so this warning is static and fires whatever the result.

Virtuoso DOES return the rows when <B> is listed in a plain FROM (verified the same day),
so only a graph in neither FROM nor FROM NAMED is flagged.
"""

from __future__ import annotations

import asyncio

import pytest

from togo_mcp import rdf_portal
from togo_mcp.rdf_portal import _undeclared_graph_note, _undeclared_graphs

A = "http://rdfportal.org/ontology/mondo"
B = "http://rdfportal.org/ontology/hp"
TRIPLE = "<http://purl.obolibrary.org/obo/HP_0001250> <http://www.w3.org/2000/01/rdf-schema#label> ?l"


@pytest.mark.parametrize(
    "query",
    [
        # the production shape: FROM one graph, GRAPH another
        f"SELECT ?l FROM <{A}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        # FROM NAMED alone triggers it too (measured)
        f"SELECT (COUNT(*) AS ?n) FROM NAMED <{A}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        # ASK — the form that lies loudest
        f"ASK FROM <{A}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        # inside OPTIONAL: rows come back, the label leg is silently empty (prod, uniprot)
        f"SELECT ?s ?l FROM <{A}> WHERE {{ ?s ?p ?o OPTIONAL {{ GRAPH <{B}> {{ {TRIPLE} }} }} }}",
        # lowercase keywords, no space before the IRI
        f"select ?l from <{A}> where {{ graph<{B}> {{ {TRIPLE} }} }}",
    ],
)
def test_flags_undeclared_graph(query: str) -> None:
    assert _undeclared_graphs(query) == [B]
    note = _undeclared_graph_note(query)
    assert note is not None and note.startswith("# WARNING")
    assert f"<{B}>" in note
    assert "FROM NAMED" in note and "trap #12" in note
    assert all(line.startswith("#") for line in note.splitlines())


@pytest.mark.parametrize(
    "query",
    [
        # no dataset clause: Virtuoso answers correctly
        f"SELECT ?l WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        # the fix: declare it as a named graph
        f"SELECT ?l FROM <{A}> FROM NAMED <{B}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        # listed in a plain FROM: Virtuoso returns the rows (verified 2026-11-27)
        f"SELECT ?l FROM <{B}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        f"SELECT ?l FROM <{A}> FROM <{B}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        # GRAPH ?var is a different (non-empty) Virtuoso behaviour, not this trap
        f"SELECT ?g FROM <{A}> WHERE {{ GRAPH ?g {{ {TRIPLE} }} }}",
        # a SERVICE body has its own dataset
        f"SELECT ?l FROM <{A}> WHERE {{ ?s ?p ?o SERVICE <https://example.org/sparql> "
        f"{{ GRAPH <{B}> {{ {TRIPLE} }} }} }}",
        # FROM / GRAPH text inside a comment or a string literal is not a clause
        f"# FROM <{A}>\nSELECT ?l WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}",
        f'SELECT ?l WHERE {{ GRAPH <{B}> {{ ?s ?p "FROM <{A}>" }} }}',
    ],
)
def test_does_not_flag(query: str) -> None:
    assert _undeclared_graphs(query) == []
    assert _undeclared_graph_note(query) is None


def test_hash_inside_iri_is_not_a_comment() -> None:
    """An IRI like `...rdf-schema#label` must not truncate the rest of the line."""
    q = f"SELECT ?l FROM <{A}> WHERE {{ ?s <http://x.org/ns#p> ?o . GRAPH <{B}> {{ {TRIPLE} }} }}"
    assert _undeclared_graphs(q) == [B]


def test_lists_each_missing_graph_once_in_order() -> None:
    q = (
        f"SELECT * FROM <{A}> WHERE {{ GRAPH <urn:g2> {{ ?a ?b ?c }} "
        f"GRAPH <urn:g1> {{ ?a ?b ?c }} GRAPH <urn:g2> {{ ?a ?b ?c }} GRAPH <{A}> {{ ?a ?b ?c }} }}"
    )
    assert _undeclared_graphs(q) == ["urn:g2", "urn:g1"]


def test_run_sparql_prepends_warning_even_when_result_is_non_empty(monkeypatch) -> None:
    """The point: COUNT(*) = 1 is a non-empty body the empty-result note ignores."""

    async def fake_execute(*_args, **_kwargs):
        return '"n"\n1\n'

    monkeypatch.setattr(rdf_portal, "execute_sparql", fake_execute)
    fn = getattr(rdf_portal.run_sparql, "fn", rdf_portal.run_sparql)
    q = f"SELECT (COUNT(*) AS ?n) FROM <{A}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}"
    out = asyncio.run(fn(sparql_query=q, database="mondo"))
    assert out.startswith("# WARNING — RESULT NOT TRUSTWORTHY")
    assert out.endswith('"n"\n1\n')


def test_run_sparql_unchanged_for_a_clean_query(monkeypatch) -> None:
    body = '"l"\n"Seizure"\n'

    async def fake_execute(*_args, **_kwargs):
        return body

    monkeypatch.setattr(rdf_portal, "execute_sparql", fake_execute)
    fn = getattr(rdf_portal.run_sparql, "fn", rdf_portal.run_sparql)
    q = f"SELECT ?l FROM <{A}> FROM NAMED <{B}> WHERE {{ GRAPH <{B}> {{ {TRIPLE} }} }}"
    assert asyncio.run(fn(sparql_query=q, database="mondo")) == body
