"""Tests for the log-record enrichment helpers in togo_mcp.server.

Covers privacy (IP hashing) and the session-meta / output-size helpers added to
_ToolCallLogger. The middleware itself is exercised end-to-end via the in-memory
FastMCP client during development; here we unit-test the pure helpers.
"""
import json
import os
from pathlib import Path

# Logging must be disabled during import (no log path) — the middleware reads
# TOGOMCP_QUERY_LOG at construction time.
os.environ.pop("TOGOMCP_QUERY_LOG", None)

from togo_mcp import server


def test_hash_ip_is_irreversible_and_deterministic():
    h = server._hash_ip("198.51.100.9")
    assert h is not None and len(h) == 16
    assert h == server._hash_ip("198.51.100.9")        # stable within a process
    assert "198.51.100.9" not in h                      # raw IP never present
    assert server._hash_ip("203.0.113.1") != h          # different IP -> different hash
    assert server._hash_ip(None) is None
    assert server._hash_ip("") is None


def test_static_meta_shape():
    m = server._STATIC_META
    assert set(m) == {"server_version", "usage_guide_version", "mie_bundle_version"}
    assert m["usage_guide_version"] == "v6"             # from usage-guide filename
    assert m["server_version"]                          # importlib.metadata resolved
    assert m["mie_bundle_version"] and len(m["mie_bundle_version"]) == 12


def test_client_info_none_without_context():
    assert server._client_info(None) is None


def test_result_size():
    assert server._result_size(None) is None

    class _Block:
        text = "hello"

    class _Result:
        content = [_Block()]

    assert server._result_size(_Result()) == 5          # len("hello")
    # objects with neither content nor structured_content fall back to str()
    assert server._result_size(12345) == len("12345")


# --------------------------------------------------------------------------- #
# Client-IP source and the raw-IP opt-in (TOGOMCP_LOG_RAW_IP).
# --------------------------------------------------------------------------- #


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, peer, headers=None):
        self.client = _FakeClient(peer) if peer else None
        self.headers = headers or {}


def _with_request(monkeypatch, req):
    monkeypatch.setattr(server, "get_http_request", lambda: req)


def test_client_ip_is_the_peer_not_the_forwarded_for_header(monkeypatch):
    """X-Forwarded-For is caller-supplied: anyone who can reach the port can
    name any address. uvicorn's ProxyHeadersMiddleware already substitutes the
    header into the peer for TRUSTED peers only, so the peer is the value that
    carries the trust decision — and the only one worth attributing abuse to."""
    _with_request(
        monkeypatch,
        _FakeRequest("10.0.2.100", {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}),
    )
    assert server._ToolCallLogger._client_ip() == "10.0.2.100"


def test_client_ip_none_without_http_context(monkeypatch):
    def _raise():
        raise RuntimeError("no request")

    monkeypatch.setattr(server, "get_http_request", _raise)
    assert server._ToolCallLogger._client_ip() is None
    assert server._ToolCallLogger._forwarded_for() is None


def test_forwarded_for_is_verbatim_and_bounded(monkeypatch):
    _with_request(monkeypatch, _FakeRequest("10.0.2.100", {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}))
    assert server._ToolCallLogger._forwarded_for() == "1.2.3.4, 5.6.7.8"

    _with_request(monkeypatch, _FakeRequest("10.0.2.100", {"X-Forwarded-For": "9.9.9.9, " * 100}))
    assert len(server._ToolCallLogger._forwarded_for()) == 200

    _with_request(monkeypatch, _FakeRequest("10.0.2.100"))
    assert server._ToolCallLogger._forwarded_for() is None


def test_raw_ip_flag_is_off_by_default_and_fail_closed(monkeypatch):
    """Absent, empty, or misspelled all mean OFF: deploy.sh forwards env vars by
    a fixed list, so a forwarding miss must lose the raw address rather than
    silently leak one."""
    monkeypatch.delenv("TOGOMCP_LOG_RAW_IP", raising=False)
    assert server._ToolCallLogger()._raw_ip is False

    for off in ("", "  ", "0", "false", "no", "ture", "off"):
        monkeypatch.setenv("TOGOMCP_LOG_RAW_IP", off)
        assert server._ToolCallLogger()._raw_ip is False, off

    for on in ("1", "true", "TRUE", " yes ", "On"):
        monkeypatch.setenv("TOGOMCP_LOG_RAW_IP", on)
        assert server._ToolCallLogger()._raw_ip is True, on


class _FakeMessage:
    name = "run_sparql"
    arguments = {"database": "uniprot"}


class _FakeContext:
    fastmcp_context = None
    message = _FakeMessage()


async def _ok(_context):
    return None


def _emit_one(monkeypatch, tmp_path, *, raw_ip, peer="203.0.113.7", headers=None):
    """Drive the middleware once and return the record it wrote."""
    import asyncio

    log_path = tmp_path / f"log-{raw_ip}.jsonl"
    monkeypatch.setenv("TOGOMCP_QUERY_LOG", str(log_path))
    if raw_ip:
        monkeypatch.setenv("TOGOMCP_LOG_RAW_IP", "1")
    else:
        monkeypatch.delenv("TOGOMCP_LOG_RAW_IP", raising=False)
    _with_request(monkeypatch, _FakeRequest(peer, headers))

    mw = server._ToolCallLogger()
    assert mw._enabled
    try:
        asyncio.run(mw.on_call_tool(_FakeContext(), _ok))
    finally:
        for h in mw._log.handlers:
            h.close()
    return json.loads(log_path.read_text().strip())


def test_record_omits_raw_ip_by_default(monkeypatch, tmp_path):
    rec = _emit_one(
        monkeypatch, tmp_path, raw_ip=False, headers={"X-Forwarded-For": "203.0.113.7"}
    )
    assert rec["ip_hash"] == server._hash_ip("203.0.113.7")
    assert "ip" not in rec and "forwarded_for" not in rec
    assert "203.0.113.7" not in json.dumps(rec)


def test_record_carries_raw_ip_when_opted_in(monkeypatch, tmp_path):
    rec = _emit_one(
        monkeypatch,
        tmp_path,
        raw_ip=True,
        headers={"X-Forwarded-For": "203.0.113.7, 10.0.2.100"},
    )
    assert rec["ip"] == "203.0.113.7"
    assert rec["forwarded_for"] == "203.0.113.7, 10.0.2.100"
    # the hash stays alongside, so stripping `ip` leaves the log aggregatable
    assert rec["ip_hash"] == server._hash_ip("203.0.113.7")


def test_mie_bundle_version_tracks_content(tmp_path, monkeypatch):
    """The digest must move when MIE CONTENT moves.

    test_static_meta_shape only asserts "truthy, 12 chars" — which the broken
    implementation satisfied for a month while hashing `<file>=None` lines, i.e.
    the file NAMES alone. Shape was asserted; the property was not. This asserts
    the property: same bytes -> same digest, changed bytes -> changed digest.
    """
    import shutil

    src = Path("togo_mcp/data/mie")
    shutil.copytree(src, tmp_path / "mie")
    monkeypatch.setattr(server, "MIE_DIR", str(tmp_path / "mie"))

    before = server._detect_mie_bundle_version()
    assert before and len(before) == 12
    assert server._detect_mie_bundle_version() == before      # deterministic

    target = tmp_path / "mie" / "uniprot.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8")
    after = server._detect_mie_bundle_version()
    assert after != before, "digest ignored a content change"

    (tmp_path / "mie" / "rhea.yaml").unlink()
    assert server._detect_mie_bundle_version() != after       # roster change too


def test_mie_bundle_version_none_on_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "MIE_DIR", str(tmp_path))
    assert server._detect_mie_bundle_version() is None
