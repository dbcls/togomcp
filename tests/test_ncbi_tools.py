"""Tests for togo_mcp.ncbi_tools module."""

import asyncio

from fastmcp import Client

from togo_mcp import ncbi_tools
from togo_mcp.ncbi_tools import _validate_query_field_tags, ncbi_mcp


class TestValidateQueryFieldTags:
    """Tests for _validate_query_field_tags validation logic."""

    # --- Critical database without field tags ---

    def test_critical_db_no_tags_has_issues(self) -> None:
        """A query without field tags on a critical database should flag issues."""
        result = _validate_query_field_tags("BRCA1", "gene")
        assert result["has_issues"] is True
        assert result["is_critical"] is True
        assert result["has_field_tags"] is False

    def test_critical_db_with_proper_tags_no_issues(self) -> None:
        """A properly tagged query on a critical database should pass."""
        result = _validate_query_field_tags("BRCA1[Gene Name] AND Homo sapiens[Organism]", "gene")
        assert result["has_issues"] is False
        assert result["has_field_tags"] is True

    # --- Non-critical database ---

    def test_non_critical_db_no_tags_no_critical_flag(self) -> None:
        """A non-critical database without tags should not flag is_critical."""
        result = _validate_query_field_tags("asthma", "mesh")
        assert result["is_critical"] is False

    def test_non_critical_db_with_tags(self) -> None:
        """A non-critical database with tags should pass cleanly."""
        result = _validate_query_field_tags("asthma[MeSH Terms]", "mesh")
        assert result["has_issues"] is False
        assert result["has_field_tags"] is True

    # --- Organism detection ---

    def test_organism_term_without_tag(self) -> None:
        """Organism terms like 'human' without [Organism] should be flagged."""
        result = _validate_query_field_tags("human BRCA1", "gene")
        assert result["has_issues"] is True
        issues_text = " ".join(result["issues"])
        assert "human" in issues_text.lower()

    def test_organism_term_with_tag(self) -> None:
        """Organism terms with [Organism] tag should not trigger organism warning."""
        result = _validate_query_field_tags("Homo sapiens[Organism] AND BRCA1[Gene Name]", "gene")
        organism_issues = [i for i in result["issues"] if "Organism" in i]
        assert len(organism_issues) == 0

    def test_mouse_organism_detection(self) -> None:
        """The term 'mouse' should be detected as an organism term."""
        result = _validate_query_field_tags("mouse TP53", "gene")
        assert result["has_issues"] is True
        issues_text = " ".join(result["issues"])
        assert "mouse" in issues_text.lower()

    # --- Gene symbol detection ---

    def test_gene_symbol_detection_without_tag(self) -> None:
        """Uppercase potential gene symbols without [Gene Name] should be flagged on gene db."""
        result = _validate_query_field_tags("BRCA1", "gene")
        assert result["has_issues"] is True
        issues_text = " ".join(result["issues"])
        assert "Gene Name" in issues_text

    def test_gene_symbol_not_flagged_on_non_gene_db(self) -> None:
        """Gene symbol detection should not trigger on non-gene databases."""
        result = _validate_query_field_tags("BRCA1", "pubmed")
        gene_issues = [i for i in result["issues"] if "Gene Name" in i]
        assert len(gene_issues) == 0

    # --- Unknown database ---

    def test_unknown_database(self) -> None:
        """An unknown database should not crash and should return minimal results."""
        result = _validate_query_field_tags("test query", "unknown_db")
        assert result["is_critical"] is False
        assert isinstance(result["issues"], list)


class _FakeResponse:
    status_code = 200
    is_success = True
    text = "record"

    def json(self) -> dict:
        return {"result": {}}


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient; records the params of each GET."""

    calls: list[dict] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def get(self, url: str, params: dict) -> _FakeResponse:
        _FakeAsyncClient.calls.append(params)
        return _FakeResponse()


def _call(tool: str, args: dict):
    async def run():
        async with Client(ncbi_mcp) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(run())


class TestEutilsParameterAliases:
    """Agents that know the raw E-utilities API send its parameter names
    (`id`, `retmax`, `retstart`). The 2026-07-27→09-15 production log carried
    134 calls rejected for exactly these; they must now validate and map."""

    def _stub_http(self, monkeypatch) -> None:
        _FakeAsyncClient.calls = []
        monkeypatch.setattr(ncbi_tools, "RATE_LIMIT_DELAY", 0)
        monkeypatch.setattr(ncbi_tools.httpx, "AsyncClient", _FakeAsyncClient)
        monkeypatch.setattr(ncbi_tools, "raise_for_status_with_body", lambda *a, **k: None)

    def test_efetch_accepts_id(self, monkeypatch) -> None:
        self._stub_http(monkeypatch)
        _call("efetch", {"db": "pubmed", "id": "10194345", "rettype": "abstract"})
        assert _FakeAsyncClient.calls[-1]["id"] == "10194345"

    def test_esummary_accepts_id_list(self, monkeypatch) -> None:
        self._stub_http(monkeypatch)
        _call("esummary", {"database": "pubmed", "id": ["1", "2"]})
        assert _FakeAsyncClient.calls[-1]["id"] == "1,2"

    def test_ids_wins_over_id(self, monkeypatch) -> None:
        self._stub_http(monkeypatch)
        _call("efetch", {"database": "pubmed", "ids": "7", "id": "8"})
        assert _FakeAsyncClient.calls[-1]["id"] == "7"

    def test_esearch_accepts_retmax_and_retstart(self, monkeypatch) -> None:
        seen: dict = {}

        async def fake_api(**kwargs):
            seen.update(kwargs)
            return {"esearchresult": {"count": "0", "idlist": []}}

        monkeypatch.setattr(ncbi_tools, "_ncbi_esearch_api", fake_api)
        # A string retmax ("40") was among the rejected calls; it must coerce.
        _call("esearch", {"db": "pubmed", "term": "TDP-43", "retmax": "40", "retstart": 5})
        assert seen["retmax"] == 40
        assert seen["retstart"] == 5
