from .server import *
from .rdf_portal import *
from .api_tools import *
from .chembl import *
from .togoid import togoid_mcp
from .ncbi_tools import ncbi_mcp
from .togovar import togovar_mcp
import asyncio
import os

# FastMCP >= 3.4.3 validates the Host header (DNS-rebinding protection) and 421s
# any host not on the allow-list. The default list is localhost only, so the
# public vhosts served through the reverse proxy must be added explicitly or every
# proxied request is rejected. Operators can append internal names (e.g. the
# container host) via TOGOMCP_ALLOWED_HOSTS="host1,host2" without editing source.
_DEFAULT_ALLOWED_HOSTS = ["togomcp.rdfportal.org", "test-togomcp.rdfportal.org"]

def _allowed_hosts() -> list[str]:
    extra = os.environ.get("TOGOMCP_ALLOWED_HOSTS", "")
    return _DEFAULT_ALLOWED_HOSTS + [h.strip() for h in extra.split(",") if h.strip()]

async def setup():
    mcp.mount(togoid_mcp, "togoid")
    mcp.mount(ncbi_mcp, "ncbi")
    mcp.mount(togovar_mcp, "togovar")

def run():
    asyncio.run(setup())
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000,
        allowed_hosts=_allowed_hosts(),
    )

def run_local():
    asyncio.run(setup())
    mcp.run()

if __name__ == "__main__":
    run()

