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


def test_sparql_shape_strips_literals():
    q = ('SELECT ?x FROM <http://ex/g> WHERE { ?x rdfs:comment ?c . '
         '?c bif:contains "secret-123" FILTER(?x = "pii-456") } LIMIT 5')
    s = stats.sparql_shape(q)
    blob = json.dumps(s)
    assert "secret-123" not in blob and "pii-456" not in blob  # no literal leakage
    assert s["form"] == "select"
    assert s["from"] == ["http://ex/g"]
    assert "rdfs:comment" in s["predicates"] and "bif:contains" in s["predicates"]
    assert s["flags"].get("filter") and s["flags"].get("limit") and s["flags"].get("bif_contains")


def test_sparql_shape_form_and_no_false_qnames():
    s = stats.sparql_shape("ASK WHERE { ?s a bp:Pathway }")
    assert s["form"] == "ask"
    assert "bp:Pathway" in s["predicates"]
    # IRIs and bare PREFIX colons must not produce qnames
    s2 = stats.sparql_shape("PREFIX up: <http://purl.uniprot.org/core/> SELECT ?s WHERE { ?s a up:Protein }")
    assert "up:Protein" in s2["predicates"]
    assert not any(p.startswith("http") for p in s2["predicates"])


def test_aggregate_empty():
    agg = stats.aggregate([])
    assert agg["months"] == []
    assert agg["by_month"] == {}
    assert agg["mie_candidates"] == []
    assert agg["mie_trap_candidates"]["candidates"] == []
    # still renders
    assert "<html" in stats.render_html(agg)


# --------------------------------------------------------------------------- #
# MIE-trap candidates — the filtered feed
# --------------------------------------------------------------------------- #
def _trap(cls, *, db="uniprot", ts="2026-07-05T10:00:00+00:00", sha="h1", shape=None):
    """Build a SPARQL record whose *derived* class is `cls`.

    `cls` is the sparql_class() result we want ("empty_result", "timeout",
    "huge_result", "http_4xx", ...) — mapped here to the raw sparql_status +
    n_rows/n_bytes the collector actually writes.
    """
    raw = {"empty_result": "ok", "huge_result": "ok",
           "timeout": "timeout", "http_4xx": "http_4xx", "http_5xx": "http_5xx"}[cls]
    extra = {"endpoint_url": "https://rdfportal.org/sib/sparql",
             "sparql_status": raw, "query_sha256": sha}
    if cls == "empty_result":
        extra["n_rows"] = 0
    elif cls == "huge_result":
        extra["n_rows"] = 5
        extra["n_bytes"] = stats.HUGE_BYTES + 1
    if shape is not None:
        extra["query_shape"] = shape
    err = raw not in ("ok",)
    return _rec(ts=ts, args={"database": db}, status="error" if err else "ok", extra=extra)


def test_day_of():
    assert stats.day_of({"ts": "2026-07-05T10:00:00+00:00"}) == "2026-07-05"
    # UTC normalization crosses the date line
    assert stats.day_of({"ts": "2026-07-05T23:00:00-03:00"}) == "2026-07-06"
    assert stats.day_of({"ts": "nope"}) is None


def test_load_mie_dates(tmp_path):
    (tmp_path / "uniprot.yaml").write_text(
        'schema_info:\n  version:\n    mie_created: "2026-01-01"\n'
        '    mie_updated: "2026-04-29"\n')
    (tmp_path / "rhea.yaml").write_text(
        'schema_info:\n  version:\n    mie_created: "2026-02-02"\n')  # no mie_updated
    dates = stats.load_mie_dates(str(tmp_path))
    assert dates["uniprot"] == "2026-04-29"   # prefers mie_updated
    assert dates["rhea"] == "2026-02-02"      # falls back to mie_created


def test_is_schema_probe():
    survey = {"flags": {"group": True}, "n_predicates": 1}      # SELECT ?p (COUNT) GROUP BY ?p
    assert stats.is_schema_probe(survey) is True
    real_agg = {"flags": {"group": True}, "n_predicates": 5}    # legit multi-predicate aggregate
    assert stats.is_schema_probe(real_agg) is False
    assert stats.is_schema_probe(None) is False                 # missing shape -> keep


def test_trap_dedup_and_retry_count():
    # one distinct query (same sha) failing 3x -> one candidate, retries=3
    recs = [_trap("timeout", sha="stuck") for _ in range(3)]
    trap = stats.aggregate(recs)["mie_trap_candidates"]
    assert trap["distinct_queries"] == 1
    assert trap["candidates"][0]["retries"] == 3


def test_trap_date_filter_vs_mie():
    # failure predates the current MIE -> excluded; a later one survives
    recs = [
        _trap("empty_result", db="uniprot", sha="old", ts="2026-03-01T10:00:00+00:00"),
        _trap("empty_result", db="uniprot", sha="new", ts="2026-05-01T10:00:00+00:00"),
    ]
    trap = stats.aggregate(recs, mie_dates={"uniprot": "2026-04-29"})["mie_trap_candidates"]
    assert trap["excluded_pre_mie"] == 1
    assert [c["query_sha256"] for c in trap["candidates"]] == ["new"]


def test_trap_excludes_probes_and_grammar_errors():
    recs = [
        _trap("empty_result", sha="probe",
              shape={"flags": {"group": True}, "n_predicates": 1}),   # schema probe
        _trap("http_4xx", sha="bad-sparql"),                          # grammar error
        _trap("empty_result", sha="real",
              shape={"flags": {}, "n_predicates": 3,
                     "predicates": ["up:x", "up:y", "up:z"]}),        # real trap
    ]
    trap = stats.aggregate(recs)["mie_trap_candidates"]
    assert trap["excluded_schema_probe"] == 1
    assert trap["grammar_errors"] == 1
    assert [c["query_sha256"] for c in trap["candidates"]] == ["real"]
    assert trap["candidates"][0]["predicates"] == ["up:x", "up:y", "up:z"]


def test_trap_section_renders():
    recs = [_trap("empty_result", db="mesh", sha="r",
                  shape={"flags": {}, "n_predicates": 2, "predicates": ["a:b"]})]
    html = stats.render_html(stats.aggregate(recs))
    assert "MIE traps to fix (filtered)" in html
    assert "mesh" in html
