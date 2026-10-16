"""Credentials (NCBI `api_key`) must never reach a client or the tool-call log.

Regression for: `ncbi_efetch` with an invalid ID returned
"NCBI efetch HTTP 400 from https://eutils.../efetch.fcgi?...&api_key=<KEY>".
"""

import asyncio

import httpx
import pytest
import respx
from fastmcp import Client, FastMCP

from togo_mcp import ncbi_tools, server
from togo_mcp.server import (
    _RedactSecrets,
    raise_for_status_with_body,
    redact_secrets,
    register_secret,
)

FAKE_KEY = "0123456789abcdef0123456789abcdef0123"


@pytest.fixture
def ncbi_key(monkeypatch):
    monkeypatch.setattr(ncbi_tools, "NCBI_API_KEY", FAKE_KEY)
    register_secret(FAKE_KEY)
    yield FAKE_KEY
    server._registered_secrets.discard(FAKE_KEY)


# --- unit: redact_secrets ----------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "https://x.example/f?db=gene&api_key=SECRETVALUE123&tool=T",
        "https://x.example/f?api_key=SECRETVALUE123",
        "https://x.example/f?db=gene&API_KEY=SECRETVALUE123",
        "https://x.example/f?db=gene&apikey=SECRETVALUE123#frag",
        "https://x.example/f?access_token=SECRETVALUE123&x=1",
    ],
)
def test_redacts_secret_query_params_by_name(text):
    out = redact_secrets(text)
    assert "SECRETVALUE123" not in out
    assert "REDACTED" in out


def test_leaves_non_secret_params_alone():
    url = "https://x.example/f?db=gene&id=672&tool=TogoMCP&email=a%40b.jp"
    assert redact_secrets(url) == url


def test_redacts_registered_value_outside_a_query_string(ncbi_key):
    # e.g. echoed back in a response body or a repr, with no `api_key=` prefix.
    out = redact_secrets(f"upstream said: invalid key {ncbi_key}!")
    assert ncbi_key not in out


def test_short_values_are_not_registered():
    register_secret("abc")
    assert redact_secrets("abc def") == "abc def"


# --- raise_for_status_with_body ---------------------------------------------


def test_raise_for_status_with_body_masks_url():
    req = httpx.Request("GET", f"https://e.example/efetch.fcgi?id=x&api_key={FAKE_KEY}")
    resp = httpx.Response(400, text="<ERROR>ID list is empty!</ERROR>", request=req)
    with pytest.raises(ValueError) as ei:
        raise_for_status_with_body(resp, context="NCBI efetch")
    msg = str(ei.value)
    assert FAKE_KEY not in msg
    assert "api_key=REDACTED" in msg
    assert "ID list is empty!" in msg  # the useful diagnostic survives


# --- end to end through the mounted server + middleware ----------------------


def _parent() -> FastMCP:
    parent = FastMCP("t")
    parent.add_middleware(_RedactSecrets())
    parent.mount(ncbi_tools.ncbi_mcp, "ncbi")
    return parent


@respx.mock
def test_efetch_http_error_does_not_leak_key(ncbi_key):
    asyncio.run(_test_efetch_http_error_does_not_leak_key(ncbi_key))


async def _test_efetch_http_error_does_not_leak_key(ncbi_key):
    respx.get(url__startswith="https://eutils.ncbi.nlm.nih.gov/").mock(
        return_value=httpx.Response(400, text="<ERROR>ID list is empty!</ERROR>")
    )
    async with Client(_parent()) as c:
        res = await c.call_tool(
            "ncbi_efetch", {"database": "gene", "ids": ["notanid"]}, raise_on_error=False
        )
    text = "".join(getattr(b, "text", "") for b in res.content)
    assert ncbi_key not in text
    assert "ID list is empty!" in text


@respx.mock
def test_efetch_transport_error_does_not_leak_key(ncbi_key):
    asyncio.run(_test_efetch_transport_error_does_not_leak_key(ncbi_key))


async def _test_efetch_transport_error_does_not_leak_key(ncbi_key):
    # httpx puts the full URL (query string included) into some exception texts.
    def boom(request):
        raise httpx.ConnectError(f"failed for {request.url}", request=request)

    respx.get(url__startswith="https://eutils.ncbi.nlm.nih.gov/").mock(side_effect=boom)
    async with Client(_parent()) as c:
        res = await c.call_tool(
            "ncbi_efetch", {"database": "gene", "ids": ["672"]}, raise_on_error=False
        )
    text = "".join(getattr(b, "text", "") for b in res.content)
    assert ncbi_key not in text


def test_middleware_scrubs_unexpected_tool_output(ncbi_key):
    asyncio.run(_test_middleware_scrubs_unexpected_tool_output(ncbi_key))


async def _test_middleware_scrubs_unexpected_tool_output(ncbi_key):
    # A future tool that forgets to redact is still covered by the middleware.
    parent = FastMCP("t")
    parent.add_middleware(_RedactSecrets())

    @parent.tool
    def leaky() -> str:
        return f"debug: https://e.example/x?api_key={ncbi_key}"

    @parent.tool
    def raises() -> str:
        raise RuntimeError(f"boom https://e.example/x?api_key={ncbi_key}")

    async with Client(parent) as c:
        r1 = await c.call_tool("leaky", {})
        r2 = await c.call_tool("raises", {}, raise_on_error=False)
    for r in (r1, r2):
        text = "".join(getattr(b, "text", "") for b in r.content)
        assert ncbi_key not in text, text
