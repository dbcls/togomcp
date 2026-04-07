"""Tests for togo_mcp.server module."""

import csv
from pathlib import Path

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
            dbname="chembl",
            endpoint_name="ebi",
            endpoint_url="https://custom.example.com/sparql",
        )
        assert url == "https://custom.example.com/sparql"

    def test_endpoint_name_over_dbname(self) -> None:
        """endpoint_name takes priority over dbname when endpoint_url is empty."""
        from togo_mcp.server import ENDPOINT_NAME_TO_URL, ENDPOINT_NAMES

        if not ENDPOINT_NAMES:
            pytest.skip("No endpoint names configured")
        ep_name = ENDPOINT_NAMES[0]
        expected_url = ENDPOINT_NAME_TO_URL[ep_name]
        url = resolve_endpoint_url(dbname="", endpoint_name=ep_name, endpoint_url="")
        assert url == expected_url

    def test_dbname_fallback(self) -> None:
        """dbname is used when both endpoint_url and endpoint_name are empty."""
        from togo_mcp.server import SPARQL_ENDPOINT, SPARQL_ENDPOINT_KEYS

        if not SPARQL_ENDPOINT_KEYS:
            pytest.skip("No databases configured")
        db = SPARQL_ENDPOINT_KEYS[0]
        expected_url = SPARQL_ENDPOINT[db]["url"]
        url = resolve_endpoint_url(dbname=db, endpoint_name="", endpoint_url="")
        assert url == expected_url

    def test_invalid_dbname_raises(self) -> None:
        """An unknown dbname raises ValueError."""
        with pytest.raises(ValueError, match="Unknown database"):
            resolve_endpoint_url(dbname="nonexistent_db_xyz", endpoint_name="", endpoint_url="")

    def test_invalid_endpoint_name_raises(self) -> None:
        """An unknown endpoint_name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown endpoint name"):
            resolve_endpoint_url(dbname="", endpoint_name="nonexistent_ep_xyz", endpoint_url="")

    def test_none_provided_raises(self) -> None:
        """Passing all empty strings raises ValueError."""
        with pytest.raises(ValueError, match="At least one of"):
            resolve_endpoint_url(dbname="", endpoint_name="", endpoint_url="")
