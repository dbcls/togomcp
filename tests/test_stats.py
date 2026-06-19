"""Tests for the usage-log analysis engine (togo_mcp.stats)."""
import json

from togo_mcp import stats


def _rec(**kw):
    base = {"ts": "2026-06-01T10:00:00+00:00", "tool": "run_sparql",
            "args": {}, "status": "ok", "elapsed_ms": 100}
    base.update(kw)
    return base


def _sparql(status, *, db="uniprot", rows=None, nbytes=None, http=None, err=False):
    extra = {"endpoint_url": "https://rdfportal.org/sib/sparql", "sparql_status": status}
    if rows is not None:
        extra["n_rows"] = rows
    if nbytes is not None:
        extra["n_bytes"] = nbytes
    if http is not None:
        extra["http_code"] = http
    return _rec(args={"database": db}, status="error" if err else "ok", extra=extra)


def test_iter_records_skips_malformed(tmp_path):
    p = tmp_path / "log.jsonl"
    p.write_text('{"ts":"x","tool":"a"}\nnot json\n\n{"ts":"y","tool":"b"}\n')
    recs = list(stats.iter_records([str(p)]))
    assert [r["tool"] for r in recs] == ["a", "b"]


def test_log_paths_includes_rotated(tmp_path):
    base = tmp_path / "log.jsonl"
    base.write_text("{}\n")
    (tmp_path / "log.jsonl.1").write_text("{}\n")
    (tmp_path / "log.jsonl.2").write_text("{}\n")
    # .4 missing -> .3 absent stops enumeration
    got = stats.log_paths(str(base))
    assert got == [str(base), f"{base}.1", f"{base}.2"]


def test_month_of():
    assert stats.month_of({"ts": "2026-06-15T23:00:00+00:00"}) == "2026-06"
    # UTC normalization: 23:00-03:00 on Jun 30 is Jul 1 UTC
    assert stats.month_of({"ts": "2026-06-30T23:00:00-03:00"}) == "2026-07"
    assert stats.month_of({"ts": "garbage"}) is None
    assert stats.month_of({}) is None


def test_sparql_class():
    assert stats.sparql_class(_sparql("ok", rows=10, nbytes=500)) == "ok"
    assert stats.sparql_class(_sparql("ok", rows=0, nbytes=50)) == "empty_result"
    assert stats.sparql_class(_sparql("ok", rows=99, nbytes=stats.HUGE_BYTES + 1)) == "huge_result"
    assert stats.sparql_class(_sparql("timeout", err=True)) == "timeout"
    assert stats.sparql_class(_sparql("network_error", err=True)) == "endpoint_down"
    assert stats.sparql_class(_sparql("http_5xx", err=True)) == "server_error"
    assert stats.sparql_class(_sparql("http_4xx", err=True)) == "syntax_error"
    # non-SPARQL record
    assert stats.sparql_class(_rec(tool="togoid_convertId", extra=None)) is None
    assert stats.sparql_class(_rec(args={})) is None


def test_database_of():
    groups = {"https://rdfportal.org/ebi/sparql": "ebi"}
    assert stats.database_of(_rec(args={"database": "chembl"}), groups) == "chembl"
    assert stats.database_of(_rec(tool="search_uniprot_entity", args={"query": "x"}), groups) == "uniprot"
    cross = _rec(args={"endpoint_name": "ebi"}, extra={"endpoint_url": "https://rdfportal.org/ebi/sparql",
                                                       "sparql_status": "ok", "n_rows": 1})
    assert stats.database_of(cross, groups) == "ebi (cross-db)"
    assert stats.database_of(_rec(tool="togoid_convertId", args={"ids": "x"}), groups) is None


def test_aggregate_counts_and_rates():
    recs = [
        _sparql("ok", db="uniprot", rows=30, nbytes=2048),
        _sparql("ok", db="reactome", rows=0, nbytes=50),          # empty
        _sparql("http_4xx", db="reactome", http=400, err=True),   # syntax
        _sparql("timeout", db="chebi", err=True),                 # timeout
        _rec(tool="search_uniprot_entity", args={"query": "p"}, elapsed_ms=300),
        _rec(ts="2026-07-01T00:00:00+00:00", args={"database": "uniprot"},
             extra={"endpoint_url": "https://rdfportal.org/sib/sparql",
                    "sparql_status": "ok", "n_rows": 5, "n_bytes": 500}),
    ]
    agg = stats.aggregate(recs)
    assert agg["months"] == ["2026-06", "2026-07"]
    assert agg["n_records"] == 6

    jun = agg["by_month"]["2026-06"]
    assert jun["tool_calls"] == 5
    assert jun["errors"] == 2
    assert jun["error_rate"] == round(2 / 5, 4)
    sp = jun["sparql"]
    assert sp["total"] == 4
    assert sp["classes"]["ok"] == 1
    assert sp["classes"]["empty_result"] == 1
    assert sp["classes"]["syntax_error"] == 1
    assert sp["classes"]["timeout"] == 1
    assert sp["failures"] == 2  # syntax + timeout; empty is not a failure
    assert jun["databases"]["uniprot"]["calls"] == 2  # sparql + search tool
    assert jun["databases"]["reactome"]["empty"] == 1


def test_mie_candidates_ranking():
    recs = [
        _sparql("http_4xx", db="reactome", http=400, err=True),
        _sparql("ok", db="reactome", rows=0, nbytes=10),  # empty
        _sparql("timeout", db="chebi", err=True),
        _sparql("ok", db="uniprot", rows=5, nbytes=99),   # clean -> not a candidate
    ]
    cand = stats.aggregate(recs)["mie_candidates"]
    dbs = [c["database"] for c in cand]
    assert "uniprot" not in dbs           # no failures -> excluded
    assert dbs[0] == "reactome"           # 1 fail + 1 empty (score 1.5) ranks above chebi (1.0)
    assert cand[0]["score"] >= cand[1]["score"]


def test_percentiles():
    recs = [_rec(elapsed_ms=v) for v in (10, 20, 30, 40, 100)]
    t = stats.aggregate(recs)["by_month"]["2026-06"]["tools"]["run_sparql"]
    assert t["count"] == 5
    assert t["p50_ms"] == 30.0
    assert t["mean_ms"] == 40.0
    assert t["p95_ms"] >= 40.0


def test_render_html_is_wellformed():
    recs = [_sparql("http_4xx", db="reactome", http=400, err=True),
            _sparql("ok", db="uniprot", rows=5, nbytes=99)]
    html = stats.render_html(stats.aggregate(recs))
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    assert "MIE-improvement candidates" in html
    assert "reactome" in html


def test_aggregate_empty():
    agg = stats.aggregate([])
    assert agg["months"] == []
    assert agg["by_month"] == {}
    assert agg["mie_candidates"] == []
    # still renders
    assert "<html" in stats.render_html(agg)
