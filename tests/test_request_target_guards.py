"""Caller-supplied targets must not reach past what the server means to expose.

- run_sparql/get_graph_list `endpoint_url`: the server POSTs to it and returns the
  body, so an unchecked URL reads hosts on the server's own network (SSRF).
- get_MIE_file `database`: becomes a path component, so `../x` or `/etc/x` read an
  arbitrary *.yaml off the host.
"""
import asyncio
import socket

import pytest

from togo_mcp import server
from togo_mcp import rdf_portal


def _check(url: str) -> None:
    asyncio.run(server.check_endpoint_url(url))


def _resolve_to(monkeypatch, addr: str) -> None:
    async def fake_getaddrinfo(self, host, port, *a, **kw):
        family = socket.AF_INET6 if ":" in addr else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (addr, port))]

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", fake_getaddrinfo)


def test_registered_endpoint_is_allowed_without_dns(monkeypatch):
    _resolve_to(monkeypatch, "10.0.0.5")  # internal resolution is fine for these
    _check(server.SPARQL_ENDPOINT["uniprot"]["url"])


def test_public_host_is_allowed(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    _check("https://query.example.org/sparql")


@pytest.mark.parametrize(
    "addr",
    ["127.0.0.1", "10.1.2.3", "192.168.10.5", "172.16.0.1", "169.254.169.254",
     "10.0.2.2", "::1", "fd00::1", "0.0.0.0"],
)
def test_non_public_resolution_is_rejected(monkeypatch, addr):
    _resolve_to(monkeypatch, addr)
    with pytest.raises(ValueError, match="non-public address"):
        _check("http://internal.example/sparql")


def test_registered_host_on_another_port_is_not_exempt(monkeypatch):
    _resolve_to(monkeypatch, "10.0.0.5")
    with pytest.raises(ValueError, match="non-public address"):
        _check("https://rdfportal.org:8890/sparql")


@pytest.mark.parametrize(
    "suffix", ["", "/", "?default-graph-uri=http%3A%2F%2Fexample.org%2Fg"],
)
def test_registered_endpoint_spellings_stay_exempt(monkeypatch, suffix):
    _resolve_to(monkeypatch, "10.0.0.5")
    _check(server.SPARQL_ENDPOINT["uniprot"]["url"] + suffix)


@pytest.mark.parametrize(
    "path", ["/conductor", "/sib/sparql/../../conductor", "/sib/sparq%6c", "/sib/sparql/x"],
)
def test_other_path_on_a_registered_host_is_not_exempt(monkeypatch, path):
    """The exemption is for the registered endpoint, not its whole host: a Virtuoso
    admin UI on the same internal-resolving host must hit the public-address check."""
    _resolve_to(monkeypatch, "10.0.0.5")
    with pytest.raises(ValueError, match="non-public address"):
        _check("https://rdfportal.org" + path)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://x/", "ftp://x/"])
def test_non_http_scheme_is_rejected(url):
    with pytest.raises(ValueError, match="only http and https"):
        _check(url)


def test_extra_hosts_env_exempts(monkeypatch):
    _resolve_to(monkeypatch, "127.0.0.1")
    monkeypatch.setenv("TOGOMCP_EXTRA_SPARQL_HOSTS", "foo.example, LocalHost")
    _check("http://localhost:8890/sparql")


def test_execute_sparql_refuses_before_any_request(monkeypatch):
    _resolve_to(monkeypatch, "127.0.0.1")

    async def boom(*a, **kw):  # pragma: no cover - must not be reached
        raise AssertionError("request was sent")

    monkeypatch.setattr(server, "_post_with_liveness_watchdog", boom)
    with pytest.raises(ValueError, match="not allowed"):
        asyncio.run(server.execute_sparql(
            "ASK {}", database="uniprot", endpoint_url="http://localhost:8000/mcp"))


@pytest.mark.parametrize("database", ["../../../compose", "/etc/hosts", "uniprot/../go"])
def test_get_mie_file_rejects_path_like_database(database):
    fn = getattr(rdf_portal.get_MIE_file, "fn", rdf_portal.get_MIE_file)
    out = asyncio.run(fn(database=database))
    assert out.startswith("Error: No MIE file for"), out[:200]


def test_get_mie_file_still_serves_a_real_database():
    fn = getattr(rdf_portal.get_MIE_file, "fn", rdf_portal.get_MIE_file)
    assert not asyncio.run(fn(database="uniprot")).startswith("Error:")
