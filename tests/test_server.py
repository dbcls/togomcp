"""Tests for togo_mcp.server module."""

import asyncio
import csv
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from togo_mcp.server import load_sparql_endpoints, resolve_endpoint_url

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(tmp_dir: Path, rows: list[list[str]]) -> str:
    """Write a CSV file with a header and return its path."""
    csv_path = tmp_dir.joinpath("endpoints.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["db_name", "endpoint_url", "endpoint_name", "keyword_search_api"])
        for row in rows:
            writer.writerow(row)
    return str(csv_path)


# ---------------------------------------------------------------------------
# load_sparql_endpoints
# ---------------------------------------------------------------------------


class TestLoadSparqlEndpoints:
    """Tests for load_sparql_endpoints CSV parsing and key normalization."""

    def test_basic_loading(self, tmp_path: Path) -> None:
        """CSV rows are loaded with correct keys and values."""
        path = _write_csv(
            tmp_path,
            [
                ["UniProt", "https://uniprot.example.com/sparql", "uniprot_ep", "kw_api"],
            ],
        )
        result = load_sparql_endpoints(path)
        assert "uniprot" in result
        assert result["uniprot"]["url"] == "https://uniprot.example.com/sparql"
        assert result["uniprot"]["endpoint_name"] == "uniprot_ep"
        assert result["uniprot"]["keyword_search"] == "kw_api"

    def test_key_normalization_spaces(self, tmp_path: Path) -> None:
        """Spaces in db_name are replaced with underscores."""
        path = _write_csv(
            tmp_path,
            [
                ["NCBI Gene", "https://example.com/sparql", "ep", "kw"],
            ],
        )
        result = load_sparql_endpoints(path)
        assert "ncbi_gene" in result

    def test_key_normalization_hyphens(self, tmp_path: Path) -> None:
        """Hyphens in db_name are removed."""
        path = _write_csv(
            tmp_path,
            [
                ["rdf-config", "https://example.com/sparql", "ep", "kw"],
            ],
        )
        result = load_sparql_endpoints(path)
        assert "rdfconfig" in result

    def test_key_normalization_mixed(self, tmp_path: Path) -> None:
        """Mixed case, spaces, and hyphens are all normalized."""
        path = _write_csv(
            tmp_path,
            [
                ["My-DB Name", "https://example.com/sparql", "ep", "kw"],
            ],
        )
        result = load_sparql_endpoints(path)
        assert "mydb_name" in result

    def test_multiple_rows(self, tmp_path: Path) -> None:
        """Multiple CSV rows produce multiple dictionary entries."""
        path = _write_csv(
            tmp_path,
            [
                ["db1", "https://a.example.com/sparql", "ep1", "kw1"],
                ["db2", "https://b.example.com/sparql", "ep2", "kw2"],
            ],
        )
        result = load_sparql_endpoints(path)
        assert len(result) == 2
        assert "db1" in result
        assert "db2" in result

    def test_empty_csv(self, tmp_path: Path) -> None:
        """An empty CSV (header only) produces an empty dict."""
        path = _write_csv(tmp_path, [])
        result = load_sparql_endpoints(path)
        assert result == {}


# ---------------------------------------------------------------------------
# resolve_endpoint_url
# ---------------------------------------------------------------------------


class TestResolveEndpointUrl:
    """Tests for resolve_endpoint_url priority logic and error cases."""

    def test_endpoint_url_has_highest_priority(self) -> None:
        """When endpoint_url is provided, it is returned regardless of other args."""
        url = resolve_endpoint_url(
            database="chembl",
            endpoint_name="ebi",
            endpoint_url="https://custom.example.com/sparql",
        )
        assert url == "https://custom.example.com/sparql"

    def test_endpoint_name_over_database(self) -> None:
        """endpoint_name takes priority over database when endpoint_url is empty."""
        from togo_mcp.server import ENDPOINT_NAME_TO_URL, ENDPOINT_NAMES

        if not ENDPOINT_NAMES:
            pytest.skip("No endpoint names configured")
        ep_name = ENDPOINT_NAMES[0]
        expected_url = ENDPOINT_NAME_TO_URL[ep_name]
        url = resolve_endpoint_url(database="", endpoint_name=ep_name, endpoint_url="")
        assert url == expected_url

    def test_database_fallback(self) -> None:
        """database is used when both endpoint_url and endpoint_name are empty."""
        from togo_mcp.server import SPARQL_ENDPOINT, SPARQL_ENDPOINT_KEYS

        if not SPARQL_ENDPOINT_KEYS:
            pytest.skip("No databases configured")
        db = SPARQL_ENDPOINT_KEYS[0]
        expected_url = SPARQL_ENDPOINT[db]["url"]
        url = resolve_endpoint_url(database=db, endpoint_name="", endpoint_url="")
        assert url == expected_url

    def test_invalid_database_raises(self) -> None:
        """An unknown database raises ValueError."""
        with pytest.raises(ValueError, match="Unknown database"):
            resolve_endpoint_url(database="nonexistent_db_xyz", endpoint_name="", endpoint_url="")

    def test_endpoint_name_as_database_gives_hint(self) -> None:
        """Passing an endpoint_name as database raises with a specific hint."""
        from togo_mcp.server import ENDPOINT_NAMES

        if not ENDPOINT_NAMES:
            pytest.skip("No endpoint names configured")
        with pytest.raises(ValueError, match="is an endpoint_name"):
            resolve_endpoint_url(
                database=ENDPOINT_NAMES[0], endpoint_name="", endpoint_url=""
            )

    def test_invalid_endpoint_name_raises(self) -> None:
        """An unknown endpoint_name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown endpoint_name"):
            resolve_endpoint_url(database="", endpoint_name="nonexistent_ep_xyz", endpoint_url="")

    def test_none_provided_raises(self) -> None:
        """Passing all empty strings raises ValueError."""
        with pytest.raises(ValueError, match="Missing required argument"):
            resolve_endpoint_url(database="", endpoint_name="", endpoint_url="")


# ---------------------------------------------------------------------------
# _ToolCallLogger middleware
# ---------------------------------------------------------------------------


def _build_ctx(tool: str, args: dict | None = None) -> SimpleNamespace:
    """Minimal MiddlewareContext stand-in covering the attrs the logger reads."""
    return SimpleNamespace(
        message=SimpleNamespace(name=tool, arguments=args or {}),
        fastmcp_context=SimpleNamespace(
            session_id="sess-1",
            request_id="req-1",
            origin_request_id=None,
            client_id="client-1",
            transport="stdio",
        ),
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _make_logger(monkeypatch, tmp_path: Path, enabled: bool):
    """Re-import server with TOGOMCP_QUERY_LOG set/unset, return (_ToolCallLogger, log_path)."""
    log_path = tmp_path / "calls.jsonl"
    if enabled:
        monkeypatch.setenv("TOGOMCP_QUERY_LOG", str(log_path))
    else:
        monkeypatch.delenv("TOGOMCP_QUERY_LOG", raising=False)
    import togo_mcp.server as srv
    importlib.reload(srv)
    return srv._ToolCallLogger(), srv, log_path


class TestToolCallLogger:
    def test_disabled_short_circuits(self, monkeypatch, tmp_path: Path) -> None:
        mw, _srv, log_path = _make_logger(monkeypatch, tmp_path, enabled=False)
        assert mw._enabled is False

        async def call_next(_ctx):
            return "result"

        out = asyncio.run(mw.on_call_tool(_build_ctx("any_tool"), call_next))
        assert out == "result"
        assert not log_path.exists()

    def test_logs_success(self, monkeypatch, tmp_path: Path) -> None:
        mw, _srv, log_path = _make_logger(monkeypatch, tmp_path, enabled=True)
        assert mw._enabled is True

        async def call_next(_ctx):
            return "ok"

        out = asyncio.run(mw.on_call_tool(_build_ctx("find_databases", {"keywords": ["x"]}), call_next))
        assert out == "ok"

        for h in mw._log.handlers:  # type: ignore[union-attr]
            h.flush()
        records = _read_jsonl(log_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["tool"] == "find_databases"
        assert rec["args"] == {"keywords": ["x"]}
        assert rec["status"] == "ok"
        assert rec["session_id"] == "sess-1"
        assert rec["transport"] == "stdio"
        assert isinstance(rec["elapsed_ms"], (int, float))
        assert "extra" not in rec  # non-SPARQL call

    def test_logs_error(self, monkeypatch, tmp_path: Path) -> None:
        mw, _srv, log_path = _make_logger(monkeypatch, tmp_path, enabled=True)

        async def call_next(_ctx):
            raise ValueError("boom")

        with pytest.raises(ValueError):
            asyncio.run(mw.on_call_tool(_build_ctx("run_sparql"), call_next))

        for h in mw._log.handlers:  # type: ignore[union-attr]
            h.flush()
        rec = _read_jsonl(log_path)[0]
        assert rec["status"] == "error"
        assert rec["error_class"] == "ValueError"
        assert "boom" in rec["error_message"]

    def test_sparql_extra_merged(self, monkeypatch, tmp_path: Path) -> None:
        mw, srv, log_path = _make_logger(monkeypatch, tmp_path, enabled=True)

        async def call_next(_ctx):
            srv._sparql_extra_var.set(
                {"endpoint_url": "https://x/sparql", "sparql_status": "ok", "n_rows": 3}
            )
            return "csv body"

        asyncio.run(mw.on_call_tool(_build_ctx("run_sparql"), call_next))

        for h in mw._log.handlers:  # type: ignore[union-attr]
            h.flush()
        rec = _read_jsonl(log_path)[0]
        assert rec["extra"]["endpoint_url"] == "https://x/sparql"
        assert rec["extra"]["sparql_status"] == "ok"
        assert rec["extra"]["n_rows"] == 3


# ---------------------------------------------------------------------------
# _IgnoreUnknownSearchKwargs middleware — mounted sub-server regression
# ---------------------------------------------------------------------------
class TestIgnoreUnknownSearchKwargs:
    """A mounted sub-server search tool (e.g. togovar_search_*) is proxied as a
    FastMCPProviderTool, which has NO `.fn`. The middleware used to derive valid
    kwargs via `tool.fn`, raising AttributeError and killing every call to those
    three TogoVar tools. Guard the schema-based fallback path here — none of the
    togovar tests exercise the mount + middleware layer where the bug lived.
    """

    def _root_with_togovar(self):
        from fastmcp import FastMCP
        from togo_mcp.togovar import togovar_mcp

        root = FastMCP("test-root")
        root.mount(togovar_mcp, "togovar")
        return root

    def test_mounted_search_tool_valid_kwargs_no_fn(self) -> None:
        from togo_mcp.server import _IgnoreUnknownSearchKwargs

        root = self._root_with_togovar()
        mw = _IgnoreUnknownSearchKwargs()
        mw._valid_kwargs_cache.clear()
        ctx = SimpleNamespace(fastmcp_context=SimpleNamespace(fastmcp=root))

        # Must not raise (regression) and must resolve schema-derived arg names.
        valid = asyncio.run(mw._valid_kwargs(ctx, "togovar_search_variant"))
        assert valid is not None
        assert {"gene_hgnc_id", "chromosome", "consequence", "limit"} <= valid

    def test_mounted_search_tool_strips_unknown_kwargs(self) -> None:
        from togo_mcp.server import _IgnoreUnknownSearchKwargs

        root = self._root_with_togovar()
        mw = _IgnoreUnknownSearchKwargs()
        mw._valid_kwargs_cache.clear()
        seen: dict = {}

        async def call_next(context):
            seen["args"] = dict(context.message.arguments)
            return "ok"

        context = SimpleNamespace(
            message=SimpleNamespace(
                name="togovar_search_gene",
                arguments={"query": "ALDH2", "bogus": "drop-me"},
            ),
            fastmcp_context=SimpleNamespace(fastmcp=root),
        )
        asyncio.run(mw.on_call_tool(context, call_next))
        # The made-up kwarg is dropped; the declared one survives.
        assert seen["args"] == {"query": "ALDH2"}


class TestServerVersion:
    """serverInfo.version must be TogoMCP's own version, not FastMCP's default."""

    def test_reports_togomcp_version_not_fastmcp(self) -> None:
        from importlib.metadata import version

        from togo_mcp.server import mcp

        assert mcp.version == version("togo-mcp")
        # Sanity: it's a real version string, not the "0+unknown" source fallback
        # (the package is installed in the test env).
        assert mcp.version and mcp.version != "0+unknown"


class TestMIETrapBanner:
    """get_MIE_file prepends a trap banner above the YAML body.

    The traps that produced wrong benchmark answers were all documented in the
    right MIE and simply not re-read at the moment a predicate was typed, so the
    banner exists to make them unskippable. It must never swallow the file.
    """

    def test_headlines_warnings_and_co_hosted_graphs(self) -> None:
        from togo_mcp.rdf_portal import _mie_trap_banner

        content = (
            "schema_info:\n"
            "  co_hosted_graphs:\n"
            '    - "http://example.org/sib — re-types 42 IRIs"\n'
            "critical_warnings: |\n"
            "  - FIRST TRAP: does a bad thing.\n"
            "    continuation line, not a warning of its own\n"
            "  - SECOND TRAP: does another.\n"
        )
        banner = _mie_trap_banner(content, "demo")
        assert "`demo`" in banner
        assert "2 CRITICAL WARNING(S)" in banner
        assert "1 CO-HOSTED GRAPH(S)" in banner
        assert "FIRST TRAP" in banner and "SECOND TRAP" in banner
        # Every line is a YAML comment, so the result still parses as YAML.
        assert all(line.startswith("#") for line in banner.splitlines())

    def test_sub_bullets_do_not_become_warnings(self) -> None:
        """Indented sub-bullets belong to their parent warning, not the count."""
        from togo_mcp.rdf_portal import _mie_trap_banner

        content = (
            "critical_warnings: |\n"
            "  - PARENT TRAP: has two sub-cases.\n"
            "      - sub-case one\n"
            "      - sub-case two\n"
        )
        assert "1 CRITICAL WARNING(S)" in _mie_trap_banner(content, "demo")

    def test_banner_never_blocks_the_file(self) -> None:
        """A malformed or bannerless MIE still returns its content."""
        from togo_mcp.rdf_portal import _mie_trap_banner

        assert _mie_trap_banner("{{ not: valid: yaml", "demo") == ""
        assert _mie_trap_banner("schema_info:\n  title: x\n", "demo") == ""

    def test_real_mie_banner_precedes_yaml_and_parses(self) -> None:
        import yaml

        from togo_mcp.rdf_portal import _mie_trap_banner

        path = Path("togo_mcp/data/mie/uniprot.yaml")
        content = path.read_text(encoding="utf-8")
        banner = _mie_trap_banner(content, "uniprot")
        assert "up:reviewed" in banner  # the #1 uniprot trap (reviewed-flag filter)
        # Banner + body must still be loadable as YAML by any downstream consumer.
        doc = yaml.safe_load(banner + content)
        # v3 renamed schema_info -> discovery; the banner must not break parsing either way.
        meta = doc.get("discovery") or doc.get("schema_info")
        assert meta["title"] == "UniProt RDF"


class TestUsageGuideEndpointTable:
    """The guide's endpoint table is a hand-written copy of endpoints.csv.

    It silently drifted before: `sib` was listed as "UniProt · Rhea" long after OMA
    was mounted there (2026-04-28), so the guide told agents no co-tenant could
    corrupt a UniProt query — the exact trap that produced a wrong benchmark answer.
    These tests fail the build instead of the agent.
    """

    def _guide_table(self) -> str:
        from togo_mcp.server import TOGOMCP_USAGE_GUIDE

        return Path(TOGOMCP_USAGE_GUIDE, "02_budgets_and_discovery.md").read_text(
            encoding="utf-8"
        )

    def _csv_rows(self) -> list[dict[str, str]]:
        from togo_mcp.server import ENDPOINTS_CSV

        with open(ENDPOINTS_CSV, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_every_database_key_is_listed_verbatim(self) -> None:
        """Agents copy these into database=; a display name would not resolve."""
        guide = self._guide_table()
        missing = [r["database"] for r in self._csv_rows() if f"`{r['database']}`" not in guide]
        assert not missing, f"database keys absent from the guide's endpoint table: {missing}"

    def test_per_endpoint_counts_match_the_registry(self) -> None:
        import collections
        import re

        real = collections.Counter(r["endpoint_name"] for r in self._csv_rows())
        claimed = {
            m.group(1): int(m.group(2))
            for m in re.finditer(r"^\| \*\*(\w+)\*\* \| (\d+) \|", self._guide_table(), re.M)
        }
        assert claimed == dict(real), (
            f"guide endpoint counts {claimed} != endpoints.csv {dict(real)}"
        )

    def test_shared_endpoints_are_not_understated(self) -> None:
        """The co-tenancy warning is only true if the counts are."""
        guide = self._guide_table()
        assert "CO-TENANCY" in guide
        assert "`oma`" in guide, "OMA co-hosts sib and must be visible on the sib row"

    def test_guide_title_matches_the_served_directory_version(self) -> None:
        """The dir name is the version of record; the title drifted to v5 and the
        tool docstring to v4 while v5 was being served. Keep the three in step."""
        import re

        from togo_mcp.server import _detect_usage_guide_version

        version = _detect_usage_guide_version()
        title = Path(
            __import__("togo_mcp.server", fromlist=["x"]).TOGOMCP_USAGE_GUIDE,
            "01_gates_and_rules.md",
        ).read_text(encoding="utf-8")
        m = re.search(r"^# TogoMCP Usage Guide \((v\d+)\)", title, re.M)
        assert m, "guide title must declare its version"
        assert m.group(1) == version, (
            f"guide title says {m.group(1)} but the served directory is {version}"
        )
