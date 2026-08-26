"""Offline tests for `scripts/check_mie_gotchas.py` and the `check:` blocks in the corpus.

The script itself needs a live SPARQL endpoint, so what is tested here is everything
around that: the shape of every `check:` block the repo ships (which is what CI will
try to execute — a malformed one should fail here, not silently at 06:17 on a Monday),
and the pure decision functions that turn a query result into a verdict.

The one that matters most is `_is_query_error`. `kind: error` passes when the endpoint
REJECTS a query and must not pass when the endpoint is merely down — Virtuoso answers a
genuine rejection with HTTP 500 and so does a dead gateway, so if that line is drawn
wrong the whole mechanism inverts: an outage would "confirm" every timeout claim in the
corpus, which is precisely the class of error this machinery exists to catch.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MIE_DIR = ROOT / "togo_mcp" / "data" / "mie"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_mie_gotchas", ROOT / "scripts" / "check_mie_gotchas.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_mie_gotchas"] = mod
    spec.loader.exec_module(mod)
    return mod


checker = _load_checker()

# Every check: block shipped in the corpus, as (db, location, block).
ALL_CHECKS = [
    (path.stem, loc, check)
    for path in sorted(MIE_DIR.glob("*.yaml"))
    for loc, _claim, check in checker.iter_claims(yaml.safe_load(path.read_text(encoding="utf-8")))
    if check
]


class TestShippedCheckBlocks:
    """Structural validation of the `check:` blocks in the MIE corpus (spec §3.6)."""

    def test_corpus_has_checks_at_all(self) -> None:
        """Guard against the whole mechanism silently disappearing in a refactor."""
        assert ALL_CHECKS, "no check: blocks found in any MIE file"

    @pytest.mark.parametrize("db,loc,check", ALL_CHECKS,
                             ids=[f"{d}:{l}" for d, l, _ in ALL_CHECKS])
    def test_block_is_well_formed(self, db: str, loc: str, check: dict) -> None:
        assert isinstance(check, dict), f"{db} {loc}: check is not a mapping"
        kind = check.get("kind")
        assert kind in checker.KINDS, f"{db} {loc}: bad kind {kind!r}"

        # `date:`, never `on:` — YAML 1.1 parses bare `on` as boolean True, so a
        # validator looking for the key finds nothing (spec §4.1 trap).
        assert "date" in check, f"{db} {loc}: check has no date:"
        assert True not in check, f"{db} {loc}: `on:` parsed as boolean — use date:"
        assert isinstance(check["date"], str), f"{db} {loc}: quote the date"

        exp = check.get("expect") or {}
        if kind == "ratio":
            num = check.get("unpinned") or check.get("numerator")
            den = check.get("pinned") or check.get("denominator")
            assert num and den, f"{db} {loc}: ratio needs two query legs"
            assert "ratio" in exp, f"{db} {loc}: ratio needs expect.ratio"
            queries = [num, den]
        else:
            assert check.get("query"), f"{db} {loc}: {kind} needs a query:"
            queries = [check["query"]]
            if kind == "count":
                assert "value" in exp, f"{db} {loc}: count needs expect.value"

        for q in queries:
            assert checker.is_runnable_sparql_like(q), f"{db} {loc}: not a SPARQL query"

    @pytest.mark.parametrize("db,loc,check", ALL_CHECKS,
                             ids=[f"{d}:{l}" for d, l, _ in ALL_CHECKS])
    def test_tolerance_is_fractional_not_absolute(self, db: str, loc: str, check: dict) -> None:
        """A tolerance is a FRACTION of the expected value, so > 1 is always a mistake.

        Easy to get wrong on a large count — writing `tolerance: 1000` next to
        `value: 709482280` reads as "±1000" but means ±1000x, which accepts anything
        and turns the check into decoration.
        """
        tol = (check.get("expect") or {}).get("tolerance")
        if tol is not None:
            assert 0 <= float(tol) < 1, f"{db} {loc}: tolerance {tol} is not a fraction"


class TestQueryErrorClassification:
    """`_is_query_error` separates "the endpoint rejected this" from "the endpoint is down".

    Get this backwards and an outage silently confirms every `kind: error` claim.
    """

    def test_virtuoso_rejection_is_a_query_error(self) -> None:
        body = "Virtuoso 37000 Error TR...: transitive start not given"
        assert checker._is_query_error(500, body) is True

    def test_unbound_transitive_rejection_is_a_query_error(self) -> None:
        body = ("Virtuoso 37000 Error TR...: Query contains a transitive derived table "
                "but neither end of it is bound by equality")
        assert checker._is_query_error(500, body) is True

    def test_sparql_compile_error_is_a_query_error(self) -> None:
        assert checker._is_query_error(400, "SPARQL compiler: Undefined namespace prefix") is True

    @pytest.mark.parametrize("code", [502, 503, 504])
    def test_gateway_failure_is_not_a_query_error(self, code: int) -> None:
        assert checker._is_query_error(code, "<html>502 Bad Gateway</html>") is False

    def test_bare_500_without_an_engine_message_is_not_a_query_error(self) -> None:
        """An HTML error page from a proxy is infrastructure, not a rejection."""
        assert checker._is_query_error(500, "<html><body>Internal Server Error</body></html>") is False


class TestFalsifiableHeuristic:
    """The un-checked-claim scanner. It over-reports by design; it must not UNDER-report
    the shapes that were actually wrong in the 2026-08-25 sweep."""

    @pytest.mark.parametrize("text,label", [
        ("an unpinned join returns ×6.29 rows", "multiplier"),
        ("a live COUNT(DISTINCT) over either TIMES OUT at 60s", "timeout/unrunnable"),
        ("an unfiltered COUNT or LIMIT-less scan times out", "timeout/unrunnable"),
        ("an unpinned gene/type join is unrunnable, not merely doubled", "timeout/unrunnable"),
        ('`rhea:status "Approved"` silently returns 0 rows', "zero-rows"),
        ("re-types 335,971 reviewed UniProt IRIs", "figure"),
    ])
    def test_catches_the_shapes_that_were_wrong(self, text: str, label: str) -> None:
        assert label in checker.falsifiable_hints(text)

    def test_qualitative_advice_is_not_flagged(self) -> None:
        assert checker.falsifiable_hints(
            "Prefer the IRI over a text match, and apply the status filter early.") == []
