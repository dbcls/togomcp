"""Tests for the log-record enrichment helpers in togo_mcp.server.

Covers privacy (IP hashing) and the session-meta / output-size helpers added to
_ToolCallLogger. The middleware itself is exercised end-to-end via the in-memory
FastMCP client during development; here we unit-test the pure helpers.
"""
import os

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
    assert m["usage_guide_version"] == "v5"             # from usage-guide filename
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
