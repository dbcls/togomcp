"""Tests for togo_mcp.server module."""

import asyncio
import csv
import importlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
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

        out = asyncio.run(mw.on_call_tool(_build_ctx("run_sparql", {"database": "uniprot"}), call_next))
        assert out == "ok"

        for h in mw._log.handlers:  # type: ignore[union-attr]
            h.flush()
        records = _read_jsonl(log_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["tool"] == "run_sparql"
        assert rec["args"] == {"database": "uniprot"}
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
            "graphs:\n"
            "  co_hosted:\n"
            '    "http://example.org/sib": "re-types 42 IRIs"\n'
            "global_gotchas:\n"
            "  - id: first\n"
            '    say: "FIRST TRAP: does a bad thing."\n'
            "  - id: second\n"
            '    say: "SECOND TRAP: does another."\n'
        )
        banner = _mie_trap_banner(content, "demo")
        assert "`demo`" in banner
        assert "2 CRITICAL WARNING(S)" in banner
        assert "1 CO-HOSTED GRAPH(S)" in banner
        assert "FIRST TRAP" in banner and "SECOND TRAP" in banner
        # Every line is a YAML comment, so the result still parses as YAML.
        assert all(line.startswith("#") for line in banner.splitlines())

    def test_banner_never_blocks_the_file(self) -> None:
        """A malformed or bannerless MIE still returns its content."""
        from togo_mcp.rdf_portal import _mie_trap_banner

        assert _mie_trap_banner("{{ not: valid: yaml", "demo") == ""
        assert _mie_trap_banner("discovery:\n  title: x\n", "demo") == ""

    def test_real_mie_banner_precedes_yaml_and_parses(self) -> None:
        import yaml

        from togo_mcp.rdf_portal import _mie_trap_banner

        path = Path("togo_mcp/data/mie/uniprot.yaml")
        content = path.read_text(encoding="utf-8")
        banner = _mie_trap_banner(content, "uniprot")
        assert "up:reviewed" in banner  # the #1 uniprot trap (reviewed-flag filter)
        # Banner + body must still be loadable as YAML by any downstream consumer.
        doc = yaml.safe_load(banner + content)
        assert doc["discovery"]["title"] == "UniProt RDF"


class TestMIECheckBlockStripping:
    """`check:` blocks are CI fixtures and must never reach the caller (spec §3.6).

    Half the check kinds hold a query written to FAIL — `zero_rows`, `absent` and
    `error`. `get_MIE_file` tells the reader every SPARQL string in the file is a
    verified route to adapt, so shipping a deliberately-broken one is worse than
    wasting the bytes. Stripping is text-level rather than a YAML round-trip
    because these files carry load-bearing comments a round-trip would delete.
    """

    def test_strips_check_keeps_everything_else(self) -> None:
        import yaml

        from togo_mcp.rdf_portal import _strip_check_blocks

        src = (
            "global_gotchas:\n"
            "  - id: a\n"
            '    say: "keep me"\n'
            "    check:\n"
            "      kind: ratio\n"
            "      unpinned: |\n"
            "        SELECT (COUNT(*) AS ?n) WHERE { ?s a <X> }\n"
            "\n"
            "      pinned: |\n"
            "        SELECT (COUNT(*) AS ?n) WHERE { GRAPH <G> { ?s a <X> } }\n"
            "      expect: {ratio: 6.29}\n"
            "  - id: b\n"
            '    say: "also keep"\n'
            "examples:\n"
            "  - id: e\n"
            "    sparql: |\n"
            "      SELECT * WHERE { ?s ?p ?o }\n"
            "    traps_avoided:\n"
            '      - say: "trap text"\n'
            "        check:\n"
            "          kind: error\n"
            "          query: |\n"
            "            SELECT * WHERE { ?a <p>+ ?b }\n"
            '      - "plain string trap"\n'
        )
        out = _strip_check_blocks(src)

        assert "check:" not in out
        assert "COUNT(*)" not in out and "?a <p>+ ?b" not in out
        # Everything the reader is meant to see survives, including the sibling
        # `say` of a trap that carried a check and the real example query.
        for kept in ("keep me", "also keep", "trap text", "plain string trap",
                     "SELECT * WHERE { ?s ?p ?o }"):
            assert kept in out
        doc = yaml.safe_load(out)
        assert len(doc["global_gotchas"]) == 2
        assert len(doc["examples"][0]["traps_avoided"]) == 2

    def test_content_without_checks_is_untouched(self) -> None:
        """A file with no `check:` must come back byte-identical.

        The fixture is chosen dynamically rather than named: checks are being added
        to the corpus over time, so hard-coding a file here means this test quietly
        stops testing anything the day that file gains one.
        """
        from togo_mcp.rdf_portal import _strip_check_blocks

        for path in sorted(Path("togo_mcp/data/mie").glob("*.yaml")):
            src = path.read_text(encoding="utf-8")
            if "check:" in src:
                continue
            assert _strip_check_blocks(src) == src, path.name
            return
        pytest.skip("every MIE now carries a check: block")

    def test_shipped_mies_still_parse_after_stripping(self) -> None:
        """Strip every real MIE and confirm the served form is valid YAML.

        The stripper walks indentation, so a `check:` written at an unexpected
        depth could in principle eat a sibling key. Running it over the whole
        corpus is the cheapest guard against that.
        """
        import yaml

        from togo_mcp.rdf_portal import _strip_check_blocks

        for path in sorted(Path("togo_mcp/data/mie").glob("*.yaml")):
            served = _strip_check_blocks(path.read_text(encoding="utf-8"))
            doc = yaml.safe_load(served)
            assert isinstance(doc, dict), path.name
            assert doc.get("mie_spec") == 3, path.name
            assert doc.get("database") == path.stem, path.name
            for gotcha in doc.get("global_gotchas") or []:
                assert "check" not in gotcha, f"{path.name}: {gotcha.get('id')}"


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


# ---------------------------------------------------------------------------
# Reverse-proxy header trust (togo_mcp.main)
# ---------------------------------------------------------------------------


class TestForwardedAllowIps:
    """uvicorn parses X-Forwarded-* but trusts only 127.0.0.1 by default. The
    container is published as a host port, so the reverse proxy arrives via the
    Docker bridge gateway — left at the default, X-Forwarded-Proto is discarded
    and the app emits http:// redirects behind https://."""

    @staticmethod
    def _trusts(spec: str, ip: str) -> bool:
        from uvicorn.middleware.proxy_headers import _TrustedHosts

        return ip in _TrustedHosts(spec)

    def test_default_trusts_every_container_runtime_we_deploy_on(self, monkeypatch) -> None:
        """The peer address depends on the runtime, and getting it wrong fails
        SILENTLY (the header is dropped, not rejected). 2.0.1 shipped with only the
        Docker range and did nothing in production, which is rootless podman +
        slirp4netns: the rootlesskit port handler SNATs every inbound connection to
        the container's own slirp address, 10.0.2.100."""
        from togo_mcp.main import _forwarded_allow_ips

        monkeypatch.delenv("TOGOMCP_FORWARDED_ALLOW_IPS", raising=False)
        spec = _forwarded_allow_ips()
        cases = [
            ("10.0.2.100", "rootless podman + slirp4netns — the production path"),
            ("10.88.0.1", "rootful podman default bridge"),
            ("172.17.0.1", "docker default bridge"),
            ("172.18.0.1", "docker compose project network"),
            ("172.31.255.254", "top of the docker bridge range"),
            ("127.0.0.1", "loopback"),
            ("::1", "loopback v6"),
        ]
        for ip, why in cases:
            assert self._trusts(spec, ip), f"{ip} must be trusted by default ({why})"

    def test_deploy_script_forwards_the_override(self) -> None:
        """compose.yaml is NOT the production deploy path — scripts/deploy.sh is, and
        it forwards a FIXED list of env vars. 2.0.1 documented the override in
        .env.example while deploy.sh silently dropped it, so it was inert in prod."""
        from pathlib import Path

        deploy = Path(__file__).resolve().parents[1] / "scripts" / "deploy.sh"
        body = deploy.read_text(encoding="utf-8")
        block = body.split("TOGOMCP_PERSERVICE_VARS=(", 1)[1].split(")", 1)[0]
        assert "TOGOMCP_FORWARDED_ALLOW_IPS" in block, (
            "deploy.sh must forward TOGOMCP_FORWARDED_ALLOW_IPS or the documented "
            "override cannot reach the container"
        )

    def test_default_does_not_trust_the_public_internet(self, monkeypatch) -> None:
        """Not '*': server.py records the peer address in the tool-call log, so a
        blanket trust would let a direct caller forge the IP that gets logged."""
        from togo_mcp.main import _forwarded_allow_ips

        monkeypatch.delenv("TOGOMCP_FORWARDED_ALLOW_IPS", raising=False)
        spec = _forwarded_allow_ips()
        for ip in ("203.0.113.9", "10.1.2.3", "192.168.1.1"):
            assert not self._trusts(spec, ip), f"{ip} must NOT be trusted by default"

    def test_env_overrides_for_a_proxy_on_another_subnet(self, monkeypatch) -> None:
        from togo_mcp.main import _forwarded_allow_ips

        monkeypatch.setenv("TOGOMCP_FORWARDED_ALLOW_IPS", "10.0.0.0/8")
        assert self._trusts(_forwarded_allow_ips(), "10.1.2.3")

    def test_blank_env_falls_back_to_the_default(self, monkeypatch) -> None:
        from togo_mcp.main import _DEFAULT_FORWARDED_ALLOW_IPS, _forwarded_allow_ips

        monkeypatch.setenv("TOGOMCP_FORWARDED_ALLOW_IPS", "   ")
        assert _forwarded_allow_ips() == _DEFAULT_FORWARDED_ALLOW_IPS

    def test_uvicorn_config_reaches_uvicorn(self) -> None:
        """Guard against a silent no-op: FastMCP must forward uvicorn_config into
        uvicorn.Config, and forwarded_allow_ips must be a real Config parameter."""
        import inspect

        import uvicorn
        from fastmcp import FastMCP

        assert "forwarded_allow_ips" in inspect.signature(uvicorn.Config.__init__).parameters
        src = inspect.getsource(FastMCP.run_http_async)
        assert "config_kwargs.update(uvicorn_config_from_user)" in src


class TestSparqlTimeout:
    """The SPARQL client timeout is load-bearing, not a round number.

    RDF Portal endpoints charge a large cold-cache penalty on first touch of an
    entity's index pages: measured 2026-07-30 on the SIB endpoint, a minimal
    single-protein UniProt lookup (one IRI, LIMIT 5) took 53.9-62.1s cold and
    0.2s warm. The previous 60s ceiling sat inside that band, so a perfectly
    good query succeeded or failed by chance — two did time out in production
    on 2026-07-27. Anything at or below ~62s reopens that bug.
    """

    def test_timeout_clears_the_measured_cold_band(self) -> None:
        from togo_mcp.server import _SPARQL_TIMEOUT_SECONDS, _sparql_client

        assert _SPARQL_TIMEOUT_SECONDS >= 75.0, (
            "cold single-entity lookups were measured up to 62.1s; a ceiling near "
            "that makes a valid query fail by coin flip"
        )
        assert _sparql_client.timeout.read == _SPARQL_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    async def test_timeout_message_names_both_causes(self) -> None:
        """The old message asserted 'too heavy' and forbade any retry.

        That advice is unfollowable for a single-IRI query with a small LIMIT —
        there is nothing left to narrow. In the 2026-07-27 logs an agent obeyed
        it, simplified a 26-predicate query to 8 predicates, and timed out again.
        """
        import httpx

        from togo_mcp import server as srv

        async def _boom(*a, **k):
            raise httpx.ReadTimeout("simulated")

        original = srv._sparql_client.post
        srv._sparql_client.post = _boom  # type: ignore[method-assign]
        try:
            with pytest.raises(ValueError) as ei:
                await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        finally:
            srv._sparql_client.post = original  # type: ignore[method-assign]
        msg = str(ei.value)
        assert "TOO HEAVY" in msg and "COLD" in msg  # both causes offered
        assert "retry at most ONCE" in msg  # bounded retry, not a blanket ban
        assert "90" in msg  # reports the real ceiling


class TestEndpointLiveness:
    """Cause 3: the endpoint is answering nothing at all.

    Measured against production on 2026-08-12 during a total RDF Portal outage:
    TCP connect and the TLS handshake to the SPARQL endpoint both completed in
    25ms, and then not one byte ever arrived. Nothing at the connect layer
    signals that, so every query burned the full 90s ceiling and reported "your
    query is too heavy or the cache was cold" — neither of which was true, and
    neither of which the caller usually saw, because an MCP connector's own tool
    timeout expires long before 90s. Only a read-level probe tells it apart.
    """

    @staticmethod
    def _srv(monkeypatch, *, probe_result: bool, post):
        from togo_mcp import server as srv

        srv._endpoint_down_until.clear()
        monkeypatch.setattr(srv, "_PROBE_AFTER_SECONDS", 0.05)
        monkeypatch.setattr(srv._sparql_client, "post", post)

        async def _probe(url):
            return probe_result

        monkeypatch.setattr(srv, "_probe_endpoint", _probe)
        return srv

    @staticmethod
    async def _hang(*a, **k):
        await asyncio.sleep(30)

    @pytest.mark.asyncio
    async def test_dead_endpoint_fails_fast_and_blames_the_endpoint(self, monkeypatch) -> None:
        srv = self._srv(monkeypatch, probe_result=False, post=self._hang)

        started = time.perf_counter()
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        elapsed = time.perf_counter() - started

        msg = str(ei.value)
        assert "NOT RESPONDING" in msg
        assert "THE PROBLEM IS NOT YOUR QUERY" in msg
        # The advice the old message gave is exactly the advice that must NOT
        # appear here: there is nothing to narrow in a query that never ran.
        assert "TOO HEAVY" not in msg
        # Must land well inside any connector's tool timeout, or the caller sees
        # "no response" instead of this text — the whole point of the watchdog.
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_breaker_refuses_without_touching_the_endpoint(self, monkeypatch) -> None:
        srv = self._srv(monkeypatch, probe_result=False, post=self._hang)
        with pytest.raises(ValueError):
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")

        async def _must_not_be_called(*a, **k):
            raise AssertionError("breaker was open; the endpoint must not be contacted")

        monkeypatch.setattr(srv._sparql_client, "post", _must_not_be_called)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        assert "refused without contacting it" in str(ei.value)

    @pytest.mark.asyncio
    async def test_live_endpoint_still_gets_the_two_cause_message(self, monkeypatch) -> None:
        """A slow but ALIVE endpoint must keep its full 90s and its old advice.

        This is the cold-cache case the 90s ceiling exists for (53.9-62.1s
        measured); a watchdog that aborted it would reintroduce the 2026-07-27
        bug it was raised to fix.
        """
        async def _slow_then_timeout(*a, **k):
            await asyncio.sleep(0.15)
            raise httpx.ReadTimeout("simulated")

        srv = self._srv(monkeypatch, probe_result=True, post=_slow_then_timeout)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        msg = str(ei.value)
        assert "TOO HEAVY" in msg and "COLD" in msg
        assert "cause 3 (endpoint down) is ruled out" in msg
        assert srv._endpoint_down_remaining(
            srv.SPARQL_ENDPOINT["uniprot"]["url"]
        ) is None, "a live endpoint must not trip the breaker"

    @pytest.mark.asyncio
    async def test_pool_exhaustion_is_not_reported_as_a_slow_query(self, monkeypatch) -> None:
        """httpx's connection pool is GLOBAL, not per-host.

        Measured: 110 queries parked on one dead endpoint filled all 100 slots,
        and a query to a DIFFERENT, healthy endpoint could then not get a
        connection. That surfaced as a 90s timeout blaming the innocent query.
        """
        from togo_mcp import server as srv

        srv._endpoint_down_until.clear()

        async def _pool_timeout(*a, **k):
            raise httpx.PoolTimeout("no free connection")

        monkeypatch.setattr(srv._sparql_client, "post", _pool_timeout)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        msg = str(ei.value)
        assert "connection pool" in msg
        assert "NOT executed" in msg
        assert "TOO HEAVY" not in msg

    @pytest.mark.asyncio
    async def test_connect_timeout_blames_the_endpoint(self, monkeypatch) -> None:
        from togo_mcp import server as srv

        srv._endpoint_down_until.clear()

        async def _connect_timeout(*a, **k):
            raise httpx.ConnectTimeout("unreachable")

        monkeypatch.setattr(srv._sparql_client, "post", _connect_timeout)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        msg = str(ei.value)
        assert "did not accept a connection" in msg
        assert "THE PROBLEM IS NOT YOUR QUERY" in msg
        assert srv._endpoint_down_remaining(srv.SPARQL_ENDPOINT["uniprot"]["url"]) is not None

    @pytest.mark.asyncio
    async def test_a_successful_answer_closes_the_breaker(self, monkeypatch) -> None:
        from togo_mcp import server as srv

        url = srv.SPARQL_ENDPOINT["uniprot"]["url"]
        srv._mark_endpoint_down(url)
        # Recovery must not wait out the full TTL when the endpoint is back.
        srv._endpoint_down_until.clear()

        async def _ok(*a, **k):
            return httpx.Response(200, text="s,p,o\na,b,c\n",
                                  request=httpx.Request("POST", url))

        monkeypatch.setattr(srv._sparql_client, "post", _ok)
        out = await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="uniprot")
        assert "s,p,o" in out
        assert srv._endpoint_down_remaining(url) is None

    @pytest.mark.asyncio
    async def test_gateway_5xx_with_a_dead_endpoint_reports_the_outage(self, monkeypatch) -> None:
        """nginx answering 502 in ~0.1s is infrastructure, not a heavy query.

        Observed 2026-08-12 on the ebi endpoint: `ASK {}` and a one-IRI lookup
        502'd identically, seconds after the same queries had succeeded. The
        generic 5xx advice ("the query may be too heavy — add LIMIT") is wrong
        there: the SPARQL engine never saw the query.
        """
        from togo_mcp import server as srv

        srv._endpoint_down_until.clear()

        async def _bad_gateway(*a, **k):
            return httpx.Response(
                502,
                text="<html><head><title>502 Bad Gateway</title></head></html>",
                request=httpx.Request("POST", "https://rdfportal.org/ebi/sparql"),
            )

        async def _probe_dead(url):
            return False

        monkeypatch.setattr(srv._sparql_client, "post", _bad_gateway)
        monkeypatch.setattr(srv, "_probe_endpoint", _probe_dead)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="chembl")
        msg = str(ei.value)
        assert "502" in msg
        assert "THE PROBLEM IS NOT YOUR QUERY" in msg
        assert "TOO HEAVY" not in msg
        assert srv._endpoint_down_remaining(srv.SPARQL_ENDPOINT["chembl"]["url"]) is not None

    @pytest.mark.asyncio
    async def test_gateway_5xx_with_a_live_endpoint_says_retry_once_first(self, monkeypatch) -> None:
        """A one-off 502 from a healthy endpoint deserves a retry, not a rewrite.

        The breaker must stay CLOSED here: shutting off an endpoint that answers
        fine would turn one bad request into a 60s outage of our own making.
        """
        from togo_mcp import server as srv

        srv._endpoint_down_until.clear()

        async def _bad_gateway(*a, **k):
            return httpx.Response(
                503, text="<html>503</html>",
                request=httpx.Request("POST", "https://rdfportal.org/ebi/sparql"),
            )

        async def _probe_alive(url):
            return True

        monkeypatch.setattr(srv._sparql_client, "post", _bad_gateway)
        monkeypatch.setattr(srv, "_probe_endpoint", _probe_alive)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="chembl")
        msg = str(ei.value)
        assert "GATEWAY" in msg
        assert "Retry ONCE, unchanged" in msg
        assert "Never loop." in msg
        assert srv._endpoint_down_remaining(srv.SPARQL_ENDPOINT["chembl"]["url"]) is None

    @pytest.mark.asyncio
    async def test_a_virtuoso_500_still_gets_the_query_weight_advice(self, monkeypatch) -> None:
        """500 is Virtuoso's own; only 502/503/504 come from a proxy. The engine
        DID see the query, so 'too heavy' remains the right hint — and no probe
        should be spent on it."""
        from togo_mcp import server as srv

        srv._endpoint_down_until.clear()
        probed = []

        async def _five_hundred(*a, **k):
            return httpx.Response(
                500, text="Virtuoso 42000 Error ...",
                request=httpx.Request("POST", "https://rdfportal.org/ebi/sparql"),
            )

        async def _probe(url):
            probed.append(url)
            return True

        monkeypatch.setattr(srv._sparql_client, "post", _five_hundred)
        monkeypatch.setattr(srv, "_probe_endpoint", _probe)
        with pytest.raises(ValueError) as ei:
            await srv.execute_sparql("SELECT * WHERE { ?s ?p ?o }", database="chembl")
        assert "too heavy" in str(ei.value)
        assert probed == [], "a Virtuoso 500 needs no liveness probe"

    def test_probe_client_does_not_share_the_sparql_pool(self) -> None:
        """A probe sent through the saturated pool cannot diagnose the saturation.

        It would queue behind the very failures it exists to explain, and a probe
        that fails for want of a connection cannot tell "endpoint is down" from
        "our pool is full".
        """
        from togo_mcp import server as srv

        assert srv._probe_client is not srv._sparql_client
        assert srv._probe_client._transport._pool is not srv._sparql_client._transport._pool
        assert srv._probe_client.timeout.read == srv._PROBE_TIMEOUT_SECONDS
        # Probe + watchdog delay must both fit inside a connector's patience.
        assert srv._PROBE_AFTER_SECONDS + srv._PROBE_TIMEOUT_SECONDS <= 20.0

    def test_pool_wait_is_short_and_separate_from_the_read_budget(self) -> None:
        from togo_mcp import server as srv

        assert srv._sparql_client.timeout.read == srv._SPARQL_TIMEOUT_SECONDS
        assert srv._sparql_client.timeout.pool == srv._SPARQL_POOL_TIMEOUT_SECONDS
        assert srv._sparql_client.timeout.pool < 30.0, (
            "waiting for a free connection is our own saturation; it must never "
            "consume the query's budget or masquerade as a slow endpoint"
        )
        assert srv._sparql_client.timeout.connect == srv._SPARQL_CONNECT_TIMEOUT_SECONDS


class TestRawLogDownload:
    """/stats/log streams the raw JSONL behind the same Basic auth as /stats.

    The dashboard's tables are lossy roll-ups. Release 2.2.0 came out of reading
    the raw log directly — it surfaced two silent zero-row bugs and a timeout
    misdiagnosis that every aggregate had shown as unremarkable — so the escape
    hatch is the point of the feature, not a nicety.
    """

    @staticmethod
    def _client(tmp_path, monkeypatch, *, rotated: bool = True, auth: bool = True):
        import json as _json

        from starlette.testclient import TestClient

        from togo_mcp.main import mcp

        active = tmp_path / "log.jsonl"
        # ts values chosen so a chronological stream is oldest-first.
        active.write_text(_json.dumps({"ts": "2026-07-30T00:00:00+00:00", "n": 3}) + "\n")
        if rotated:
            (tmp_path / "log.jsonl.1").write_text(
                _json.dumps({"ts": "2026-07-28T00:00:00+00:00", "n": 1}) + "\n"
                + _json.dumps({"ts": "2026-07-29T00:00:00+00:00", "n": 2}) + "\n"
            )
        monkeypatch.setenv("TOGOMCP_QUERY_LOG", str(active))
        if auth:
            monkeypatch.setenv("TOGOMCP_STATS_USER", "u")
            monkeypatch.setenv("TOGOMCP_STATS_PASSWORD", "p")
        else:
            monkeypatch.delenv("TOGOMCP_STATS_USER", raising=False)
            monkeypatch.delenv("TOGOMCP_STATS_PASSWORD", raising=False)
        return TestClient(mcp.http_app())

    def test_requires_auth(self, tmp_path, monkeypatch) -> None:
        with self._client(tmp_path, monkeypatch) as c:
            assert c.get("/stats/log").status_code == 401
            assert c.get("/stats/log", auth=("u", "nope")).status_code == 401

    def test_refuses_when_stats_not_configured(self, tmp_path, monkeypatch) -> None:
        # Never expose the log just because credentials happen to be unset.
        with self._client(tmp_path, monkeypatch, auth=False) as c:
            assert c.get("/stats/log").status_code == 503

    def test_streams_all_files_oldest_first(self, tmp_path, monkeypatch) -> None:
        import json as _json

        with self._client(tmp_path, monkeypatch) as c:
            r = c.get("/stats/log", auth=("u", "p"))
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/x-ndjson")
        assert "attachment" in r.headers["content-disposition"]
        assert r.headers["x-log-files"] == "2"
        rows = [_json.loads(x) for x in r.text.splitlines() if x.strip()]
        # Rotated siblings must be included, or the download silently under-
        # reports versus the dashboard that aggregates them.
        assert [x["n"] for x in rows] == [1, 2, 3]

    def test_404_when_no_log_exists(self, tmp_path, monkeypatch) -> None:
        from starlette.testclient import TestClient

        from togo_mcp.main import mcp

        monkeypatch.setenv("TOGOMCP_QUERY_LOG", str(tmp_path / "absent.jsonl"))
        monkeypatch.setenv("TOGOMCP_STATS_USER", "u")
        monkeypatch.setenv("TOGOMCP_STATS_PASSWORD", "p")
        with TestClient(mcp.http_app()) as c:
            assert c.get("/stats/log", auth=("u", "p")).status_code == 404

    def test_dashboard_link_is_absolute(self, tmp_path, monkeypatch) -> None:
        """/stats has no trailing slash, so a relative href would go to /log."""
        import re

        with self._client(tmp_path, monkeypatch) as c:
            html = c.get("/stats", auth=("u", "p")).text
            href = re.search(r"<a href='([^']+)' download", html).group(1)
            assert href == "/stats/log"
            assert c.get(href, auth=("u", "p")).status_code == 200
