"""Unit tests for scripts/togomcp_reproduce.py — no network.

The script is what a paper's reader runs years later against a query ledger, so its
parsing and comparison must be right without anyone watching. The network routes
are stubbed here; the live check is a development step (plan §6 #6), not a test.
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "togomcp_reproduce.py"


def _load():
    spec = importlib.util.spec_from_file_location("togomcp_reproduce", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    # Registered before exec: @dataclass resolves annotations through sys.modules.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


rp = _load()

LEDGER = """\
ledger_version: 1
mode: prospective
created: 2026-11-02
togomcp:
  server_url: https://togomcp.rdfportal.org/mcp
  server_version: null
calls:
  - id: q01
    role: evidence
    purpose: count
    tool: run_sparql
    args:
      database: uniprot
      sparql_query: SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }
    endpoint_url: https://rdfportal.org/sib/sparql
    observed:
      n_rows: 1
      value: 214
  - id: q02
    role: lookup
    purpose: id
    tool: search_uniprot_entity
    args:
      query: APOE human
    observed:
      key_values: [P02649]
  - id: q03
    role: diagnostic
    purpose: unpinned version
    tool: run_sparql
    args:
      database: uniprot
      query: SELECT * WHERE { ?s ?p ?o }
claims:
  - text: "214 proteins"
    supported_by: [q01]
"""

NOTE = (
    "# The aggregate is 0 over an EMPTY match — no row satisfied the WHERE clause.\n"
    "# Columns: n\n"
)


# --------------------------------------------------------------------------- #
# Ledger loading
# --------------------------------------------------------------------------- #


def test_load_valid_ledger() -> None:
    ledger = rp.load_ledger(LEDGER)
    assert [c["id"] for c in ledger["calls"]] == ["q01", "q02", "q03"]


@pytest.mark.parametrize("version", [2, 0, None, "1"])
def test_unknown_ledger_version_stops(version) -> None:
    text = LEDGER.replace("ledger_version: 1", f"ledger_version: {version!r}" if version is not None else "")
    with pytest.raises(rp.LedgerError, match="ledger_version"):
        rp.load_ledger(text)


@pytest.mark.parametrize(
    "old, new, match",
    [
        ("role: lookup", "role: maybe", "role"),
        ("id: q02", "id: q01", "duplicate"),
        ("tool: search_uniprot_entity", "tool: ''", "tool"),
    ],
)
def test_malformed_calls_are_rejected(old, new, match) -> None:
    with pytest.raises(rp.LedgerError, match=match):
        rp.load_ledger(LEDGER.replace(old, new, 1))


def test_not_yaml_is_a_ledger_error() -> None:
    with pytest.raises(rp.LedgerError):
        rp.load_ledger("calls: [unclosed")


def test_main_returns_3_on_unknown_version(tmp_path: Path, capsys) -> None:
    p = tmp_path / "ledger.yaml"
    p.write_text(LEDGER.replace("ledger_version: 1", "ledger_version: 9"), encoding="utf-8")
    assert rp.main([str(p)]) == rp.EXIT_BAD_LEDGER
    assert "ledger_version" in capsys.readouterr().err


def test_query_alias_is_accepted() -> None:
    assert rp.sparql_query_of({"sparql_query": "A", "query": "B"}) == "A"
    assert rp.sparql_query_of({"query": "B"}) == "B"
    assert rp.sparql_query_of({}) == ""


# --------------------------------------------------------------------------- #
# Result parsing
# --------------------------------------------------------------------------- #


def test_note_is_stripped_before_counting() -> None:
    summary = rp.summarize_sparql(NOTE + '"n"\n0\n')
    assert summary["n_rows"] == 1
    assert summary["value"] == "0"
    assert not summary["text"].startswith("#")


def test_only_leading_hash_lines_are_stripped() -> None:
    csv_text = '"tag"\n#hashtag\n'
    assert rp.strip_note(csv_text) == csv_text
    assert rp.csv_data_rows(csv_text) == [["#hashtag"]]


def test_multiline_literal_counts_as_one_row() -> None:
    csv_text = '"label"\n"line one\nline two"\n"other"\n'
    assert rp.summarize_sparql(csv_text)["n_rows"] == 2


def test_value_only_for_single_cell() -> None:
    assert rp.summarize_sparql('"a","b"\n1,2\n')["value"] is None
    assert rp.summarize_sparql('"a"\n1\n2\n')["value"] is None


def test_tool_text_row_counts() -> None:
    assert rp.summarize_tool_text('[{"id": 1}, {"id": 2}]')["n_rows"] == 2
    assert rp.summarize_tool_text('{"total_count": 9, "results": [1]}')["n_rows"] == 1
    assert rp.summarize_tool_text("free text")["n_rows"] is None


def test_hash_ignores_line_endings_and_trailing_space() -> None:
    assert rp.result_sha256('"n"\r\n214\r\n') == rp.result_sha256('"n"\n214  \n')
    assert rp.result_sha256('"n"\n214\n') != rp.result_sha256('"n"\n215\n')


# --------------------------------------------------------------------------- #
# Comparison
# --------------------------------------------------------------------------- #


def _actual(text: str, n_rows=None, value=None) -> dict:
    return {"n_rows": n_rows, "value": value, "text": text}


def test_compare_match_on_every_field() -> None:
    text = '"n"\n214'
    verdict = rp.compare(
        {"n_rows": 1, "value": 214, "key_values": ["214"], "result_sha256": rp.result_sha256(text)},
        _actual(text, 1, "214"),
    )
    assert verdict["status"] == "match"
    assert [c["field"] for c in verdict["checks"]] == ["n_rows", "value", "key_values", "result_sha256"]


def test_compare_value_numeric_equivalence() -> None:
    assert rp.compare({"value": 214}, _actual("", value="214.0"))["status"] == "match"
    assert rp.compare({"value": "214"}, _actual("", value="215"))["status"] == "mismatch"


def test_compare_tampered_n_rows_is_mismatch() -> None:
    verdict = rp.compare({"n_rows": 215}, _actual("", n_rows=214))
    assert verdict["status"] == "mismatch"


def test_compare_missing_key_value_is_named() -> None:
    verdict = rp.compare({"key_values": ["P02649", "P04114"]}, _actual("...P02649..."))
    assert verdict["status"] == "mismatch"
    assert verdict["checks"][0]["actual"] == {"missing": ["P04114"]}


def test_recorded_field_the_result_cannot_supply_is_not_a_pass() -> None:
    assert rp.compare({"n_rows": 3}, _actual("free text"))["status"] == "mismatch"


def test_nothing_recorded_is_unchecked_not_match() -> None:
    assert rp.compare({"result_sha256": None}, _actual("x"))["status"] == "unchecked"
    assert rp.compare(None, _actual("x"))["status"] == "unchecked"


# --------------------------------------------------------------------------- #
# SPARQL route (stubbed client)
# --------------------------------------------------------------------------- #


class _FakeHttp:
    def __init__(self, status: int, text: str) -> None:
        self.status, self.text, self.sent = status, text, None

    def post(self, url, data=None, headers=None):
        self.sent = (url, data, headers)
        return SimpleNamespace(status_code=self.status, text=self.text)


def test_sparql_request_matches_the_server() -> None:
    http = _FakeHttp(200, '"n"\n214\n')
    call = {"endpoint_url": "https://e/sparql", "args": {"query": "SELECT 1"}}
    assert rp.run_sparql_direct(call, http) == '"n"\n214\n'
    assert http.sent == ("https://e/sparql", {"query": "SELECT 1"}, {"Accept": "text/csv"})


@pytest.mark.parametrize("status, category", [(400, "ledger_error"), (503, "endpoint_error")])
def test_sparql_http_errors_are_classified(status, category) -> None:
    call = {"endpoint_url": "https://e/sparql", "args": {"sparql_query": "x"}}
    with pytest.raises(rp.CallFailed) as exc:
        rp.run_sparql_direct(call, _FakeHttp(status, "boom"))
    assert exc.value.category == category


def test_sparql_without_endpoint_is_a_ledger_error() -> None:
    with pytest.raises(rp.CallFailed) as exc:
        rp.run_sparql_direct({"args": {"sparql_query": "x"}}, _FakeHttp(200, ""))
    assert exc.value.category == "ledger_error"


# --------------------------------------------------------------------------- #
# Whole-ledger runs and exit codes (both routes stubbed)
# --------------------------------------------------------------------------- #


def _stub_routes(monkeypatch, sparql_result, mcp_result, version="2.28.1"):
    seen = {}

    def fake_sparql(call, client):
        if isinstance(sparql_result, Exception):
            raise sparql_result
        return sparql_result

    async def fake_mcp(calls, url):
        seen["url"] = url
        seen["tools"] = [c["tool"] for c in calls]
        return version, {c["id"]: mcp_result for c in calls}

    monkeypatch.setattr(rp, "run_sparql_direct", fake_sparql)
    monkeypatch.setattr(rp, "replay_mcp", fake_mcp)
    return seen


def test_all_match_exits_0_and_skips_diagnostic(monkeypatch) -> None:
    seen = _stub_routes(monkeypatch, '"n"\n214\n', '[{"accession": "P02649"}]')
    outcomes, meta = rp.run_ledger(rp.load_ledger(LEDGER))
    status = {o.id: o.status for o in outcomes}
    assert status == {"q01": "match", "q02": "match", "q03": "skipped"}
    assert seen["tools"] == ["search_uniprot_entity"]
    assert meta["server_version"] == "2.28.1"
    assert rp.exit_code(outcomes) == rp.EXIT_MATCH


def test_evidence_mismatch_exits_1(monkeypatch) -> None:
    _stub_routes(monkeypatch, '"n"\n215\n', '[{"accession": "P02649"}]')
    outcomes, _ = rp.run_ledger(rp.load_ledger(LEDGER))
    assert rp.exit_code(outcomes) == rp.EXIT_MISMATCH


def test_lookup_mismatch_is_only_a_warning(monkeypatch) -> None:
    _stub_routes(monkeypatch, '"n"\n214\n', "[]")
    outcomes, meta = rp.run_ledger(rp.load_ledger(LEDGER))
    assert {o.id: o.status for o in outcomes}["q02"] == "mismatch"
    assert rp.exit_code(outcomes) == rp.EXIT_MATCH
    assert "(warning only)" in rp.format_table(outcomes, meta)


def test_endpoint_error_exits_2(monkeypatch) -> None:
    _stub_routes(monkeypatch, rp.CallFailed("endpoint_error", "down"), '["P02649"]')
    outcomes, _ = rp.run_ledger(rp.load_ledger(LEDGER))
    assert rp.exit_code(outcomes) == rp.EXIT_UNVERIFIED


def test_ledger_error_exits_1(monkeypatch) -> None:
    _stub_routes(monkeypatch, rp.CallFailed("ledger_error", "HTTP 400"), '["P02649"]')
    outcomes, _ = rp.run_ledger(rp.load_ledger(LEDGER))
    assert rp.exit_code(outcomes) == rp.EXIT_MISMATCH


def test_local_ledger_replays_against_public_server(monkeypatch) -> None:
    seen = _stub_routes(monkeypatch, '"n"\n214\n', '["P02649"]')
    ledger = rp.load_ledger(LEDGER.replace("https://togomcp.rdfportal.org/mcp", "local"))
    _, meta = rp.run_ledger(ledger)
    assert seen["url"] == rp.DEFAULT_SERVER_URL
    assert meta["notes"] and "local" in meta["notes"][0]
    rp.run_ledger(ledger, server_url="http://localhost:8000/mcp")
    assert seen["url"] == "http://localhost:8000/mcp"


def test_write_ledger_fills_only_empty_hashes(monkeypatch) -> None:
    _stub_routes(monkeypatch, '"n"\n214\n', '["P02649"]')
    outcomes, _ = rp.run_ledger(rp.load_ledger(LEDGER))
    out = rp.load_ledger(rp.ledger_with_hashes(LEDGER, outcomes))
    by_id = {c["id"]: c for c in out["calls"]}
    assert by_id["q01"]["observed"]["result_sha256"] == rp.result_sha256('"n"\n214\n')
    assert "observed" not in by_id["q03"]


def test_write_ledger_keeps_queries_readable_and_identical(monkeypatch) -> None:
    query = "PREFIX up: <http://purl.uniprot.org/core/>\nSELECT ?s\nWHERE { ?s ?p ?o }"
    text = LEDGER.replace(
        "      sparql_query: SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }",
        "      sparql_query: |-\n" + "\n".join("        " + line for line in query.split("\n")),
    )
    _stub_routes(monkeypatch, '"n"\n214\n', '["P02649"]')
    outcomes, _ = rp.run_ledger(rp.load_ledger(text))
    out = rp.ledger_with_hashes(text, outcomes)
    assert "sparql_query: |-\n" in out  # a block, not an escaped one-line string
    assert rp.load_ledger(out)["calls"][0]["args"]["sparql_query"] == query
