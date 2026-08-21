"""Tests for the usage-log analysis engine (togo_mcp.stats)."""
import json
import re
from pathlib import Path

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


def test_endpoint_outage_is_not_an_mie_trap():
    """An upstream outage must not read as evidence that some MIE is wrong.

    Before endpoint_unresponsive existed, every query issued during a portal
    outage was logged as sparql_status="timeout" -> class "timeout", which is one
    of TRAP_CLASSES. A multi-hour outage therefore inflated the MIE-trap counts
    with failures no MIE edit could ever fix.
    """
    assert stats.sparql_class(_sparql("endpoint_unresponsive", err=True)) not in stats.TRAP_CLASSES
    assert stats.sparql_class(_sparql("pool_exhausted", err=True)) not in stats.TRAP_CLASSES


def test_sparql_class():
    assert stats.sparql_class(_sparql("ok", rows=10, nbytes=500)) == "ok"
    assert stats.sparql_class(_sparql("ok", rows=0, nbytes=50)) == "empty_result"
    assert stats.sparql_class(_sparql("ok", rows=99, nbytes=stats.HUGE_BYTES + 1)) == "huge_result"
    assert stats.sparql_class(_sparql("timeout", err=True)) == "timeout"
    assert stats.sparql_class(_sparql("network_error", err=True)) == "endpoint_down"
    assert stats.sparql_class(_sparql("endpoint_unresponsive", err=True)) == "endpoint_down"
    assert stats.sparql_class(_sparql("pool_exhausted", err=True)) == "pool_exhausted"
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


def test_database_of_ignores_ncbi_eutilities_namespace():
    """NCBI db=pubmed/clinvar/medgen is a FOREIGN namespace that collides with
    real RDF Portal keys — attributing it merged E-utilities traffic into the
    RDF rows (pubmed read 3,589 calls against a real 48)."""
    for arg in ("db", "database", "dbname"):
        for tool in ("ncbi_esearch", "ncbi_efetch", "ncbi_esummary"):
            assert stats.database_of(_rec(tool=tool, args={arg: "pubmed"}), {}) is None
    # get_MIE_file is NOT an NCBI tool: database=pubmed there is the RDF pubmed.
    assert stats.database_of(_rec(tool="get_MIE_file", args={"database": "pubmed"}), {}) == "pubmed"


def test_call_kind_classifies_by_tool_identity_not_transport():
    """get_graph_list and the ChEMBL search wrappers hit a SPARQL endpoint but
    are not user queries; get_MIE_file hits no endpoint at all."""
    assert stats.call_kind(_rec(tool="get_MIE_file", args={"database": "rhea"})) == "mie"
    graphs = _sparql("ok", db="massbank", rows=3)
    graphs["tool"] = "get_graph_list"
    assert stats.call_kind(graphs) == "graphs"
    chembl = _sparql("ok", db="chembl", rows=3)
    chembl["tool"] = "search_chembl_molecule"
    chembl["args"] = {"query": "aspirin"}
    assert stats.call_kind(chembl) == "search"          # SPARQL-backed, still a wrapper
    assert stats.call_kind(_rec(tool="search_uniprot_entity", args={"query": "p"})) == "search"
    assert stats.call_kind(_sparql("ok", db="uniprot", rows=1)) == "query"
    # run_sparql that failed on its parameters never reached the endpoint
    assert stats.call_kind(_rec(status="error", args={"sparql_query": "SELECT *"})) == "other"


def _shape(*preds):
    return {"predicates": list(preds), "n_predicates": len(preds), "flags": {}}


def test_co_queried_databases_finds_the_hidden_join():
    """The rhea case: a UniProt-primary query that is really a UniProt-Rhea join
    on the co-hosted SIB endpoint. rhea's own row read 1 query for 2026-08."""
    rec = _sparql("ok", db="uniprot", rows=5)
    rec["extra"]["query_shape"] = _shape("up:enzyme", "rhea:accession", "rhea:equation",
                                         "rdfs:subClassOf")
    assert stats.co_queried_databases(rec, "uniprot") == {"rhea"}
    # the primary never credits itself, and shared vocabularies say nothing
    assert stats.co_queried_databases(rec, "rhea") == {"uniprot"}
    assert "rdfs" not in stats.SIGNATURE_PREFIXES


def test_co_query_ignores_non_sparql_and_shared_vocabularies():
    assert stats.co_queried_databases(_rec(tool="get_MIE_file", args={"database": "rhea"})) == set()
    rec = _sparql("ok", db="chebi", rows=1)
    rec["extra"]["query_shape"] = _shape("obo:BFO_0000050", "sio:SIO_000008", "rdfs:label")
    assert stats.co_queried_databases(rec, "chebi") == set()
    # an endpoint-group primary names the same database, not a second one
    grp = _sparql("ok", db="togovar", rows=1)
    grp["extra"]["query_shape"] = _shape("tgvo:hasFrequency")
    assert stats.co_queried_databases(grp, "togovar (cross-db)") == set()


def test_co_query_is_counted_separately_from_calls():
    rec = _sparql("ok", db="uniprot", rows=5)
    rec["extra"]["query_shape"] = _shape("up:enzyme", "rhea:accession")
    agg = stats.aggregate([rec])["by_month"]["2026-06"]
    dbs = agg["databases"]
    assert dbs["uniprot"]["calls"] == 1 and dbs["uniprot"]["co_query"] == 0
    # rhea gets the co-query credit without any call being invented for it
    assert dbs["rhea"]["co_query"] == 1 and dbs["rhea"]["calls"] == 0
    assert agg["co_query_pairs"] == [
        {"primary": "uniprot", "co_queried": "rhea", "queries": 1}
    ]


def test_trap_candidate_carries_co_databases():
    """A trap in a UniProt-primary query can be a Rhea MIE gap."""
    rec = _sparql("timeout", db="uniprot", err=True)
    rec["extra"]["query_shape"] = _shape("up:enzyme", "rhea:equation")
    rec["extra"]["query_sha256"] = "abc123"
    trap = stats.mie_trap_candidates([rec])
    assert trap["candidates"][0]["co_databases"] == ["rhea"]


def test_signature_prefixes_are_declared_in_some_mie():
    """Guards against typos and against a prefix that no database actually uses.
    Every signature prefix must appear as a PREFIX declaration in the MIE corpus
    the queries are written from."""
    import re
    from pathlib import Path

    mie_dir = Path(stats.__file__).parent / "data" / "mie"
    declared = set()
    for path in mie_dir.glob("*.yaml"):
        declared |= set(re.findall(r"PREFIX\s+([A-Za-z0-9_.-]+):\s*<",
                                   path.read_text(encoding="utf-8")))
    missing = sorted(set(stats.SIGNATURE_PREFIXES) - declared)
    # uniprotkb/glycodm-style client-side variants are allowed; anything else is a typo
    assert missing == ["uniprotkb"], f"undeclared signature prefixes: {missing}"


def test_colliding_prefix_is_resolved_by_local_name():
    """bacdive/mediadive/taxonomy bind schema: to DSMZ's own namespace while
    massbank binds it to real schema.org. Mapping the bare prefix either way
    mis-credits the other (128 massbank vs 10 bacdive records in one month)."""
    dsmz = _sparql("ok", db="bacdive", rows=3)
    dsmz["extra"]["query_shape"] = _shape("schema:describesStrain", "schema:Strain",
                                          "schema:hasGramStain")
    assert stats.co_queried_databases(dsmz, "mediadive") == {"bacdive"}

    schema_org = _sparql("ok", db="massbank", rows=3)
    schema_org["extra"]["query_shape"] = _shape("schema:inChIKey", "schema:name")
    assert stats.co_queried_databases(schema_org, "bacdive") == {"massbank"}
    assert stats.co_queried_databases(schema_org, "massbank") == set()

    # the bacdive<->mediadive join vocabulary belongs to both, so it credits neither
    shared = _sparql("ok", db="mediadive", rows=3)
    shared["extra"]["query_shape"] = _shape("schema:hasBacDiveID", "schema:Strain",
                                            "schema:partOfMedium")
    assert stats.co_queried_databases(shared, "mediadive") == set()
    # ...but one exclusive term is enough to pin the other side of that join
    joined = _sparql("ok", db="mediadive", rows=3)
    joined["extra"]["query_shape"] = _shape("schema:hasBacDiveID", "schema:describesStrain")
    assert stats.co_queried_databases(joined, "mediadive") == {"bacdive"}

    assert "schema" not in stats.SIGNATURE_PREFIXES
    assert "schema" not in stats._SHARED_PREFIXES


def test_ambiguous_prefix_qnames_match_the_mie_corpus():
    """The exclusive-qname sets are derived from the MIE files; re-derive them so
    the map fails loudly when a database's vocabulary moves."""
    import re
    from collections import defaultdict
    from pathlib import Path

    mie_dir = Path(stats.__file__).parent / "data" / "mie"
    for prefix, expected in stats._AMBIGUOUS_PREFIX_QNAMES.items():
        # trailing (?![<A-Za-z0-9_]) skips prose placeholders like schema:has<Phenotype>
        qre = re.compile(rf"\b{prefix}:([A-Za-z_][A-Za-z0-9_]*)(?![<A-Za-z0-9_])")
        owners = defaultdict(set)
        for path in mie_dir.glob("*.yaml"):
            for local in set(qre.findall(path.read_text(encoding="utf-8"))):
                owners[local].add(path.stem)
        derived = defaultdict(set)
        for local, dbs in owners.items():
            if len(dbs) == 1:
                derived[next(iter(dbs))].add(local)
        assert {db: set(v) for db, v in expected.items()} == dict(derived), (
            f"{prefix}: exclusive-qname map is stale vs the MIE corpus"
        )


def test_signature_and_shared_prefixes_are_disjoint():
    """A prefix cannot be both an ownership signal and a shared vocabulary."""
    overlap = set(stats.SIGNATURE_PREFIXES) & stats._SHARED_PREFIXES
    assert not overlap, f"prefix classified both ways: {sorted(overlap)}"
    ambiguous = set(stats._AMBIGUOUS_PREFIX_QNAMES)
    assert not (ambiguous & set(stats.SIGNATURE_PREFIXES)), "colliding prefix also mapped whole"
    assert not (ambiguous & stats._SHARED_PREFIXES), "colliding prefix also called shared"


def test_signature_prefixes_name_real_databases():
    """Every mapped database must exist in the endpoint registry, or the column
    credits a database nobody can query."""
    import csv
    from pathlib import Path

    csv_path = Path(stats.__file__).parent / "data" / "resources" / "endpoints.csv"
    with open(csv_path, newline="", encoding="utf-8") as fh:
        known = {row["database"].strip() for row in csv.DictReader(fh)}
    mapped = set(stats.SIGNATURE_PREFIXES.values()) | {
        db for by_local in stats._AMBIGUOUS_PREFIX_QNAMES.values() for db in by_local
    }
    unknown = sorted(mapped - known)
    assert not unknown, f"signature prefixes point at unknown databases: {unknown}"


def _call(client, ip, **kw):
    rec = _rec(**kw)
    rec["ip_hash"] = ip
    rec["meta"] = {"client": {"name": client, "version": "1"}}
    return rec


def test_reach_counts_distinct_ips_not_sessions():
    """Distinct ip_hash separates demand from a script; distinct sessions does
    not (stateless clients open one per call) and is deliberately not reported."""
    recs = [_call("openai-mcp", f"ip{i}", args={"database": "massbank"}) for i in range(5)]
    recs += [_call("sweeper", "ipX", args={"database": "rhea"}) for _ in range(20)]
    m = stats.aggregate(recs)["by_month"]["2026-06"]
    assert m["databases"]["massbank"]["calls"] == 5
    assert m["databases"]["massbank"]["ips"] == 5      # five separate clients
    assert m["databases"]["rhea"]["calls"] == 20
    assert m["databases"]["rhea"]["ips"] == 1          # one operator, 20 calls
    assert "sessions" not in m["databases"]["rhea"]
    assert m["tools"]["run_sparql"]["ips"] == 6


def test_client_table_ranks_and_reports_concentration():
    recs = [_call("openai-mcp", f"ip{i}", args={"database": "pdb"}) for i in range(4)]
    recs += [_call("harness", "ipH", args={"database": "pdb"}) for _ in range(40)]
    clients = stats.aggregate(recs)["by_month"]["2026-06"]["clients"]
    assert [c["client"] for c in clients] == ["harness", "openai-mcp"]
    assert clients[0]["calls_per_ip"] == 40.0   # one operator
    assert clients[1]["calls_per_ip"] == 1.0    # a crowd
    assert clients[0]["top_tools"] == ["run_sparql"]
    # a record with no advertised client is still counted, not dropped
    bare = stats.aggregate([_rec(args={"database": "pdb"})])["by_month"]["2026-06"]["clients"]
    assert bare[0]["client"] == "<unknown>"


def test_client_exclusion_is_opt_in_and_reported():
    recs = [_call("harness", "ipH", args={"database": "pdb"}) for _ in range(9)]
    recs += [_call("openai-mcp", "ipU", args={"database": "pdb"})]
    default = stats.aggregate(recs)
    assert default["by_month"]["2026-06"]["tool_calls"] == 10
    assert default["excluded_clients"] == {"names": [], "n_records": 0}

    filtered = stats.aggregate(recs, exclude_clients=["harness"])
    assert filtered["by_month"]["2026-06"]["tool_calls"] == 1
    assert filtered["excluded_clients"] == {"names": ["harness"], "n_records": 9}
    assert filtered["n_records"] == 1


def test_parse_excluded_clients():
    assert stats.parse_excluded_clients(" mcp , glyconavi ") == {"mcp", "glyconavi"}
    assert stats.parse_excluded_clients("") == frozenset()
    assert stats.parse_excluded_clients(None) == frozenset()


def test_search_tool_db_covers_all_wrapper_tools():
    """Every database-specific wrapper tool must be mapped, or its calls vanish
    from the per-database table (they carry no ``database`` arg)."""
    import re
    from pathlib import Path

    root = Path(stats.__file__).parent
    registered: set[str] = set()
    for mod in ("api_tools.py", "chembl.py"):
        src = (root / mod).read_text(encoding="utf-8")
        registered |= set(re.findall(r"@mcp\.tool[^\n]*\n(?:@[^\n]*\n)*async def (\w+)", src))
    assert registered, "tool-registration scan found nothing — did the decorator change?"
    assert registered <= set(stats._SEARCH_TOOL_DB), (
        f"unmapped wrapper tools: {sorted(registered - set(stats._SEARCH_TOOL_DB))} "
        "— add them to stats._SEARCH_TOOL_DB"
    )


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
    assert jun["databases"]["uniprot"]["query"] == 1
    assert jun["databases"]["uniprot"]["search"] == 1
    assert jun["databases"]["reactome"]["empty"] == 1


def test_call_kinds_partition_calls():
    """calls must be the exact sum of the kind columns — the whole point of the
    breakdown is that a reader can account for every call in the row."""
    recs = [
        _sparql("ok", db="massbank", rows=5),
        _rec(tool="get_graph_list", args={"database": "massbank"},
             extra={"endpoint_url": "https://rdfportal.org/sib/sparql",
                    "sparql_status": "ok", "n_rows": 4}),
        _rec(tool="get_MIE_file", args={"database": "massbank"}),
        _rec(tool="get_MIE_file", args={"database": "massbank"}),
        _rec(tool="search_uniprot_entity", args={"query": "p53"}),
    ]
    dbs = stats.aggregate(recs)["by_month"]["2026-06"]["databases"]
    mb = dbs["massbank"]
    assert (mb["query"], mb["graphs"], mb["mie"], mb["search"], mb["other"]) == (1, 1, 2, 0, 0)
    assert mb["calls"] == 4
    assert mb["sparql"] == 2       # endpoint hits: query + graphs
    for d in dbs.values():
        assert sum(d[k] for k in stats.CALL_KINDS) == d["calls"]


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
    assert "calls = query + graphs + search + MIE + other" in html


def test_client_table_and_exclusion_banner_render():
    recs = [_call("harness", "ipH", args={"database": "pdb"}) for _ in range(3)]
    recs += [_call("openai-mcp", "ipU", args={"database": "pdb"})]
    html = stats.render_html(stats.aggregate(recs))
    assert "Per client" in html
    assert "<td>harness</td>" in html
    assert "TOGOMCP_STATS_EXCLUDE_CLIENTS" not in html   # nothing excluded

    html = stats.render_html(stats.aggregate(recs, exclude_clients=["harness"]))
    assert "Excluding 3 records from client(s) harness" in html


def test_cross_database_joins_table_renders():
    rec = _sparql("ok", db="uniprot", rows=5)
    rec["extra"]["query_shape"] = _shape("up:enzyme", "rhea:accession")
    html = stats.render_html(stats.aggregate([rec]))
    assert "Cross-database joins" in html
    assert "<td>rhea</td>" in html


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


def test_raw_ip_field_aggregates_like_ip_hash():
    """Records carrying only the raw `ip` (TOGOMCP_LOG_RAW_IP) must aggregate
    identically to records carrying only `ip_hash` — the reader unions the two
    fields, so turning the knob on or off mid-retention does not split reach
    counts across the boundary."""
    hashed = [_call("openai-mcp", f"ip{i}", args={"database": "pdb"}) for i in range(3)]
    raw = []
    for i in range(3):
        rec = _call("openai-mcp", None, args={"database": "pdb"})
        del rec["ip_hash"]
        rec["ip"] = f"ip{i}"
        raw.append(rec)

    from_hash = stats.aggregate(hashed)["by_month"]["2026-06"]
    from_raw = stats.aggregate(raw)["by_month"]["2026-06"]
    assert from_raw["databases"]["pdb"]["ips"] == from_hash["databases"]["pdb"]["ips"] == 3
    assert from_raw["clients"][0]["ips"] == from_hash["clients"][0]["ips"] == 3


def test_stats_output_never_contains_a_raw_ip():
    """The dashboard reports reach as a COUNT. A raw address must not survive
    into any aggregate, whatever the collection layer wrote."""
    recs = [_call("openai-mcp", None, args={"database": "pdb"}) for _ in range(2)]
    for i, rec in enumerate(recs):
        del rec["ip_hash"]
        rec["ip"] = f"198.51.100.{i}"
        rec["forwarded_for"] = f"198.51.100.{i}, 10.0.2.100"
    out = json.dumps(stats.aggregate(recs))
    assert "198.51.100." not in out
    assert "forwarded_for" not in out


def test_mie_corpus_declares_the_expected_spec():
    """Every shipped MIE declares `mie_spec: 3`.

    This is the guard the v2->v3 flip lacked. Readers keyed on v2 field names
    (`mie_created`, `mie_version`) went inert for a month because a missing key is
    indistinguishable from "nothing recorded". `load_mie_dates` now skips any file
    whose spec it does not recognize, so this test is what keeps that skip path
    from quietly eating the whole corpus.
    """
    import yaml

    paths = sorted(Path("togo_mcp/data/mie").glob("*.yaml"))
    assert paths, "no MIE files found"
    bad = {
        p.name: yaml.safe_load(p.read_text(encoding="utf-8")).get("mie_spec")
        for p in paths
    }
    bad = {k: v for k, v in bad.items() if v != stats.MIE_SPEC_EXPECTED}
    assert not bad, f"MIE files not declaring mie_spec={stats.MIE_SPEC_EXPECTED}: {bad}"


def test_load_mie_dates_reads_the_real_corpus():
    """Against the SHIPPED corpus, not a hand-written fixture.

    The previous test built its own v2-shaped file in tmp_path, so it kept passing
    while the function returned {} for all 37 real databases. A corpus-shape claim
    has to be asserted against the corpus.
    """
    dates = stats.load_mie_dates("togo_mcp/data/mie")
    n_files = len(list(Path("togo_mcp/data/mie").glob("*.yaml")))
    assert len(dates) == n_files, f"only {len(dates)}/{n_files} databases resolved a date"
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates.values())


def test_load_mie_dates_takes_min_not_max(tmp_path):
    """MIN of verified.date: one re-verified example must not advance the whole file."""
    (tmp_path / "demo.yaml").write_text(
        "mie_spec: 3\n"
        "examples:\n"
        '  - {id: a, verified: {n: 1, date: "2026-07-22"}}\n'
        '  - {id: b, verified: {n: 2, date: "2026-08-20"}}\n'
    )
    assert stats.load_mie_dates(str(tmp_path))["demo"] == "2026-07-22"


def test_load_mie_dates_skips_unrecognized_spec(tmp_path):
    """A v2 file (or any unknown spec) is skipped, not silently mis-read."""
    (tmp_path / "old.yaml").write_text(
        'schema_info:\n  version:\n    mie_updated: "2026-04-29"\n')
    (tmp_path / "new.yaml").write_text(
        "mie_spec: 3\nexamples:\n  - {id: a, verified: {n: 1, date: \"2026-07-22\"}}\n")
    out = stats.load_mie_dates(str(tmp_path))
    assert "old" not in out
    assert out["new"] == "2026-07-22"
