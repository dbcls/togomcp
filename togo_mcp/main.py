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

# Which peer addresses may set X-Forwarded-Proto/-For. uvicorn parses those headers
# by default but trusts only 127.0.0.1 unless told otherwise, and the container is
# published as a host port, so the proxy NEVER arrives as loopback. Left at the
# default, uvicorn discards X-Forwarded-Proto, sees scheme=http, and emits absolute
# redirects that downgrade https:// to http:// (the /mcp/ -> /mcp 307).
#
# The address depends on the container runtime, which is why this list is wide:
#   10.0.2.0/24    rootless podman + slirp4netns (the production path on vs94:
#                  `deploy.sh` -> rootless `podman run -p`). The rootlesskit port
#                  handler SNATs every inbound connection to the container's own
#                  slirp address, 10.0.2.100.
#   10.88.0.0/16   rootful podman default bridge.
#   172.16.0.0/12  Docker/Compose bridge range (compose.yaml).
# Getting this wrong is silent: the header is dropped, not rejected.
#
# NOTE on why this is not just "*": server.py records the peer address (hashed) in
# the tool-call log. On the rootless-slirp4netns path that field is ALREADY constant
# — every client arrives as 10.0.2.100 — so there the tight list buys nothing over
# "*", and the real protection is that only the proxy can reach the published port.
# It still matters on the rootful/Compose paths, where the peer is the true client.
# Override via TOGOMCP_FORWARDED_ALLOW_IPS (comma-separated; addresses and CIDR).
_DEFAULT_FORWARDED_ALLOW_IPS = "127.0.0.1,::1,10.0.2.0/24,10.88.0.0/16,172.16.0.0/12"

def _forwarded_allow_ips() -> str:
    return os.environ.get("TOGOMCP_FORWARDED_ALLOW_IPS", "").strip() or _DEFAULT_FORWARDED_ALLOW_IPS

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
        uvicorn_config={"forwarded_allow_ips": _forwarded_allow_ips()},
    )

def run_local():
    asyncio.run(setup())
    mcp.run()

if __name__ == "__main__":
    run()

