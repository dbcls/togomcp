#!/usr/bin/env python3
"""Launch a local TogoMCP HTTP server for one ablation condition.

Thin wrapper around togo_mcp so the ablation harness can (a) choose a loopback
port and (b) whitelist the loopback Host header, neither of which the packaged
`togo-mcp-server` entry point exposes (it is pinned to 0.0.0.0:8000). Production
code is left untouched.

The MIE corpus served is controlled by TOGOMCP_MIE_DIR, which togo_mcp.server
reads at import time — so the orchestrator sets it in this process's environment
BEFORE spawning us. Port comes from ABLATION_PORT (default 8000).
"""
import asyncio
import os

from togo_mcp.main import mcp, setup


def main() -> None:
    port = int(os.environ.get("ABLATION_PORT", "8000"))
    asyncio.run(setup())
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=port,
        # Accept the loopback Host header the benchmark client sends. FastMCP's
        # Host validation otherwise 421s an unlisted host (see the prod 421 saga).
        allowed_hosts=[
            "127.0.0.1", "localhost",
            f"127.0.0.1:{port}", f"localhost:{port}",
        ],
    )


if __name__ == "__main__":
    main()
