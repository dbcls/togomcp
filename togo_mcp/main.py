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
# NOTE on why this is not just "*": server.py records the peer address in the
# tool-call log — hashed as `ip_hash` always, and in the clear as `ip` under
# TOGOMCP_LOG_RAW_IP. That address is whatever uvicorn's ProxyHeadersMiddleware
# resolved, which is the REAL client only when the peer is trusted here; for an
# untrusted peer the X-Forwarded-For chain is ignored and the proxy itself is
# recorded. So this list is what decides whether the logged IP can attribute
# abuse at all — "*" would let any caller able to reach the port write any
# address it liked into the log.
# Override via TOGOMCP_FORWARDED_ALLOW_IPS (comma-separated; addresses and CIDR).
_DEFAULT_FORWARDED_ALLOW_IPS = "127.0.0.1,::1,10.0.2.0/24,10.88.0.0/16,172.16.0.0/12"

def _forwarded_allow_ips() -> str:
    return os.environ.get("TOGOMCP_FORWARDED_ALLOW_IPS", "").strip() or _DEFAULT_FORWARDED_ALLOW_IPS

# KEGG is opt-in AND stdio-only. Both conditions must hold; neither alone enables it.
#
# The KEGG API is licensed "for academic use by academic users belonging to academic
# institutions", and providing a service on top of KEGG needs a separate academic
# service-provider licence. So:
#
#   * TRANSPORT (structural). The HTTP deployment is a public DBCLS host that cannot
#     verify a caller's affiliation, so it must never reach rest.kegg.jp. That gate is
#     the `local` argument and is NOT configurable — no env var can open it.
#   * ELIGIBILITY (opt-in). Under stdio the user running the process is the caller, but
#     TogoMCP is installed by academic and non-academic users alike. Mounting KEGG by
#     default would make an API call the user may not be entitled to into the path of
#     least resistance — an LLM will happily call a tool it can see. Requiring an
#     explicit opt-in makes eligibility an affirmative act by the person who can
#     actually judge it.
#
# WHY AN ENV VAR IS SAFE HERE, despite the general rule against gating on one
# (CLAUDE.md, "Deployment"): that rule exists because deploy.sh forwards env vars by a
# FIXED LIST, so a knob missing from the list is silently inert in production — twice in
# one week, both times with a green test suite. That hazard is entirely about a knob
# whose absence would leave a boundary OPEN. This one is inverted and therefore
# fail-closed: absent, empty, or unparseable all mean OFF, so a forwarding miss disables
# KEGG rather than enabling it. And because the transport gate is ANDed in front, the
# variable has no effect at all on the HTTP path — deploy.sh never enters the picture.
# Deliberately NOT added to TOGOMCP_PERSERVICE_VARS/TOGOMCP_SHARED_VARS.
_KEGG_ENV_VAR = "TOGOMCP_ENABLE_KEGG"
_TRUTHY = frozenset(["1", "true", "yes", "on"])


def _kegg_enabled() -> bool:
    """True only for an explicit opt-in. Anything else — including a typo — is False."""
    return os.environ.get(_KEGG_ENV_VAR, "").strip().lower() in _TRUTHY


async def setup(*, local: bool = False):
    mcp.mount(togoid_mcp, "togoid")
    mcp.mount(ncbi_mcp, "ncbi")
    mcp.mount(togovar_mcp, "togovar")
    if local and _kegg_enabled():
        from .kegg import kegg_mcp
        mcp.mount(kegg_mcp, "kegg")

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
    asyncio.run(setup(local=True))
    mcp.run()

if __name__ == "__main__":
    run()

