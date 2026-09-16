"""Tests for the `verified:` assertions in `scripts/check_mie_examples.py` (spec §4.1).

The checker needs a live endpoint to run a query, so what is tested here is everything
around that: the offline lint over every example the repo ships (which is what CI will
assert against live results — a malformed block should fail here, not silently on a
Monday), and the pure functions that turn a result into DRIFT.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MIE_DIR = ROOT / "togo_mcp" / "data" / "mie"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_mie_examples", ROOT / "scripts" / "check_mie_examples.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_mie_examples"] = mod
    spec.loader.exec_module(mod)
    return mod


checker = _load_checker()

ALL_EXAMPLES = [
    (path.stem, ex)
    for path in sorted(MIE_DIR.glob("*.yaml"))
    for ex in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("examples") or []
]


class TestCorpus:
    def test_corpus_has_examples(self) -> None:
        assert len(ALL_EXAMPLES) > 300

    @pytest.mark.parametrize("db,example", ALL_EXAMPLES,
                             ids=[f"{db}-{ex.get('id')}" for db, ex in ALL_EXAMPLES])
    def test_verified_block_is_assertable(self, db: str, example: dict) -> None:
        assert checker.lint_verified(example) == []


def _ex(verified, sparql="SELECT ?s WHERE { ?s ?p ?o }"):
    return {"id": "ex", "sparql": sparql, "verified": {"date": "2026-09-14", **verified}}


class TestLint:
    def test_bare_date_string_is_not_a_verified_block(self) -> None:
        assert checker.lint_verified({"sparql": "", "verified": "2026-07-31"})

    def test_prose_only_block_asserts_nothing(self) -> None:
        problems = checker.lint_verified(_ex({"first_row": "P04637 TP53"}))
        assert any("asserts nothing" in p for p in problems)

    def test_expect_empty_example_needs_no_assertion(self) -> None:
        ex = _ex({})
        ex["expect_empty"] = True
        assert checker.lint_verified(ex) == []

    def test_row_count_equal_to_limit_is_rejected(self) -> None:
        problems = checker.lint_verified(_ex({"row_count": 20}, "SELECT ?s WHERE { ?s ?p ?o } LIMIT 20"))
        assert any("min_rows" in p for p in problems)

    def test_row_count_below_limit_is_fine(self) -> None:
        assert checker.lint_verified(_ex({"row_count": 13}, "SELECT ?s WHERE { ?s ?p ?o } LIMIT 20")) == []

    def test_has_values_on_capped_unordered_query_is_rejected(self) -> None:
        problems = checker.lint_verified(_ex({"min_rows": 20, "has_values": ["P04637"]},
                                             "SELECT ?s WHERE { ?s ?p ?o } LIMIT 20"))
        assert any("ORDER BY" in p for p in problems)

    def test_has_values_on_ordered_capped_query_is_fine(self) -> None:
        q = "SELECT ?s WHERE { ?s ?p ?o } ORDER BY ?s LIMIT 20"
        assert checker.lint_verified(_ex({"min_rows": 20, "has_values": ["P04637"]}, q)) == []

    def test_has_values_on_uncapped_result_is_fine_without_order_by(self) -> None:
        q = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 20"
        assert checker.lint_verified(_ex({"row_count": 4, "has_values": ["P04637"]}, q)) == []

    def test_subquery_limit_does_not_cap_the_result(self) -> None:
        q = "SELECT ?s WHERE { { SELECT ?s WHERE { ?s ?p ?o } LIMIT 5 } ?s ?q ?r }"
        assert checker.outer_limit(q) is None

    def test_trailing_comment_does_not_hide_the_limit(self) -> None:
        assert checker.outer_limit("SELECT ?s WHERE { ?s ?p ?o }\nLIMIT 10   # keep it small\n") == 10

    def test_tolerance_is_fractional(self) -> None:
        assert checker.lint_verified(_ex({"n": 5, "tolerance": 5}))

    def test_has_values_must_be_a_list(self) -> None:
        assert checker.lint_verified(_ex({"row_count": 3, "has_values": "P04637, P38398"}))


class TestAssert:
    def test_n_within_tolerance(self) -> None:
        assert checker.assert_verified({"n": 1000}, [{"n": "1015"}]) == []
        assert checker.assert_verified({"n": 1000}, [{"n": "1030"}])

    def test_explicit_tolerance_widens(self) -> None:
        assert checker.assert_verified({"n": 1000, "tolerance": 0.05}, [{"n": "1030"}]) == []

    def test_n_needs_a_single_cell(self) -> None:
        assert checker.assert_verified({"n": 2}, [{"a": "1"}, {"a": "1"}])
        assert checker.assert_verified({"n": 2}, [{"a": "2", "b": "x"}])

    def test_row_count_is_exact_for_small_results(self) -> None:
        assert checker.assert_verified({"row_count": 13}, [{"a": "x"}] * 13) == []
        assert checker.assert_verified({"row_count": 13}, [{"a": "x"}] * 14)

    def test_min_rows(self) -> None:
        assert checker.assert_verified({"min_rows": 3}, [{"a": "x"}] * 3) == []
        assert checker.assert_verified({"min_rows": 3}, [{"a": "x"}] * 2)

    def test_has_values_matches_iri_local_name(self) -> None:
        rows = [{"protein": "http://purl.uniprot.org/uniprot/P04637"}]
        assert checker.assert_verified({"has_values": ["P04637"]}, rows) == []

    def test_has_values_matches_numbers_numerically(self) -> None:
        assert checker.assert_verified({"has_values": [507.182]}, [{"mass": "507.18200"}]) == []

    def test_numeric_has_values_uses_tolerance(self) -> None:
        assert checker.assert_verified({"has_values": [10000]}, [{"n": "10150"}]) == []
        assert checker.assert_verified({"has_values": [10000]}, [{"n": "10300"}])

    def test_quoted_number_in_has_values_is_exact(self) -> None:
        assert checker.assert_verified({"has_values": ["18390"]}, [{"id": "18391"}])
        assert checker.assert_verified({"has_values": ["18390"]}, [{"id": "18390"}]) == []

    def test_has_values_reports_each_missing_value(self) -> None:
        drift = checker.assert_verified({"has_values": ["P04637", "P38398"]}, [{"p": "P04637"}])
        assert len(drift) == 1 and "P38398" in drift[0]

    def test_has_values_is_not_a_substring_match(self) -> None:
        assert checker.assert_verified({"has_values": ["TP5"]}, [{"g": "TP53"}])


class TestZeroGate:
    def test_single_zero_count_is_zero_rows(self) -> None:
        assert checker.effective_rows([{"n": "0"}]) == 0

    def test_ask_false_is_zero_rows(self) -> None:
        assert checker.effective_rows([{"boolean": "false"}]) == 0

    def test_ordinary_rows(self) -> None:
        assert checker.effective_rows([{"a": "x"}, {"a": "y"}]) == 2


def test_example_path_pattern_matches_walk_queries() -> None:
    # main() recognises a v3 example by this path; if walk_queries changes its path format
    # the lint would silently check nothing.
    d = {"examples": [{"sparql": "SELECT * WHERE {?s ?p ?o}", "verified": {"date": "x"}}]}
    paths = [p for p, *_ in checker.walk_queries(d)]
    assert paths and re.fullmatch(r"/examples\[\d+\]/sparql", paths[0])


class TestEndpointResolution:
    """`endpoint_name:` on an example was ignored until 2026-09-16, so every cross_db
    example ran against its own database's endpoint — the one place such an example
    frequently CANNOT run. lipidmaps made it visible (it cannot SERVICE out, so its
    correct cross-DB example net-failed on every run); 61 examples corpus-wide were
    being graded against the wrong server."""

    @staticmethod
    def _maps():
        return checker.load_endpoint_map()

    def test_csv_yields_both_indexes(self) -> None:
        by_db, by_name = self._maps()
        assert by_db["lipidmaps"] == "https://lipidmaps.org/sparql"
        # `ebi` is an endpoint GROUP, not a database — it must resolve by NAME only.
        assert "ebi" in by_name
        assert "ebi" not in by_db

    def test_endpoint_name_beats_own_database(self) -> None:
        by_db, by_name = self._maps()
        url, problem = checker.resolve_endpoint(
            {"endpoint_name": "ebi"}, "lipidmaps", by_db, by_name)
        assert problem is None
        assert url == by_name["ebi"]
        assert url != by_db["lipidmaps"]  # the whole point

    def test_endpoint_url_beats_endpoint_name(self) -> None:
        by_db, by_name = self._maps()
        url, problem = checker.resolve_endpoint(
            {"endpoint_url": "https://example.org/sparql", "endpoint_name": "ebi"},
            "lipidmaps", by_db, by_name)
        assert (url, problem) == ("https://example.org/sparql", None)

    def test_falls_back_to_own_database(self) -> None:
        by_db, by_name = self._maps()
        url, problem = checker.resolve_endpoint({}, "lipidmaps", by_db, by_name)
        assert (url, problem) == (by_db["lipidmaps"], None)

    def test_unknown_name_is_a_problem_not_a_fallback(self) -> None:
        # Falling back here would silently recreate the original bug, one typo at a time.
        by_db, by_name = self._maps()
        url, problem = checker.resolve_endpoint(
            {"endpoint_name": "ebii"}, "lipidmaps", by_db, by_name)
        assert url is None
        assert problem and "unknown endpoint_name" in problem

    def test_every_shipped_endpoint_name_resolves(self) -> None:
        by_db, by_name = self._maps()
        unresolved = []
        for db, ex in ALL_EXAMPLES:
            if not isinstance(ex, dict) or "endpoint_name" not in ex:
                continue
            _, problem = checker.resolve_endpoint(ex, db, by_db, by_name)
            if problem:
                unresolved.append((db, ex.get("id"), ex["endpoint_name"]))
        assert not unresolved, f"unresolvable endpoint_name in shipped MIEs: {unresolved}"

    def test_corpus_actually_exercises_the_override(self) -> None:
        # If this ever hits 0 the override is dead code and the tests above prove nothing.
        overrides = [ex for _, ex in ALL_EXAMPLES
                     if isinstance(ex, dict) and ex.get("endpoint_name")]
        assert len(overrides) > 50
