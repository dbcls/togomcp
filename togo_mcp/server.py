import csv
import hashlib
import json
import logging
import os
import re
import secrets
import time
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Per-call SPARQL extras: execute_sparql writes a dict here; the middleware reads
# it in its finally block and merges it into the JSONL line. Set to None when no
# SPARQL call is in flight.
_sparql_extra_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "togomcp_sparql_extra", default=None
)


# The MIE files are used to define the shape expressions for SPARQL queries.
_PACKAGE_DATA_DIR = Path(__file__).parent.joinpath("data")
CWD = Path(os.getenv("TOGOMCP_DIR", str(_PACKAGE_DATA_DIR)))
# TOGOMCP_MIE_DIR lets a caller point get_MIE_file at an alternative MIE corpus
# (e.g. a section-stripped variant for the ablation harness) without touching
# TOGOMCP_DIR. Unset → the bundled data/mie directory, so default behavior is
# unchanged.
MIE_DIR = os.getenv("TOGOMCP_MIE_DIR", str(CWD.joinpath("mie")))
# Directory of usage-guide part files, split by change-cadence and assembled
# (sorted *.md, joined by the section separator) at serve time. The "_v6" in
# the dir name is what _detect_usage_guide_version() reads — bumping the guide
# means renaming this directory, not editing a version string.
TOGOMCP_USAGE_GUIDE = str(CWD.joinpath("resources", "usage_guide_v6"))
RDF_CONFIG_TEMPLATE = str(CWD.joinpath("rdf-config", "template.yaml"))
ENDPOINTS_CSV = str(CWD.joinpath("resources", "endpoints.csv"))
INDEX_HTML = str(CWD.joinpath("docs", "togomcp-intro.html"))
KW_SEARCH_INSTRUCTIONS = str(CWD.joinpath("kw_search"))

# Shared httpx client for SPARQL queries
_sparql_client = httpx.AsyncClient(timeout=60.0)


def load_sparql_endpoints(path: str) -> dict[str, dict[str, str]]:
    """Load SPARQL endpoints from a CSV file.

    Returns a dictionary keyed by database name with values containing:
    - url: The SPARQL endpoint URL
    - endpoint_name: Short name for the endpoint (e.g., 'ebi', 'sib')
    - keyword_search: The keyword search API to use
    """
    endpoints = {}
    with open(path, encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            db_name, endpoint_url, endpoint_name, keyword_search_api = row
            key = db_name.lower().replace(" ", "_").replace("-", "")
            endpoints[key] = {
                "url": endpoint_url,
                "endpoint_name": endpoint_name,
                "keyword_search": keyword_search_api,
            }
    return endpoints


# The SPARQL endpoints for various RDF databases, loaded from a CSV file.
SPARQL_ENDPOINT = load_sparql_endpoints(ENDPOINTS_CSV)
DATABASE_DESCRIPTION = (
    "Name of a single RDF database. Must be exactly one of: "
    f"{', '.join(SPARQL_ENDPOINT.keys())}. "
    "Do NOT pass an endpoint group name here (e.g. 'ebi', 'sib') — those go "
    "in endpoint_name instead."
)

# Build reverse lookups for endpoint_name -> url and list of databases per endpoint
ENDPOINT_NAME_TO_URL: dict[str, str] = {}
ENDPOINT_NAME_TO_DATABASES: dict[str, list] = {}
for db_name, info in SPARQL_ENDPOINT.items():
    ep_name = info["endpoint_name"]
    ENDPOINT_NAME_TO_URL[ep_name] = info["url"]
    if ep_name not in ENDPOINT_NAME_TO_DATABASES:
        ENDPOINT_NAME_TO_DATABASES[ep_name] = []
    ENDPOINT_NAME_TO_DATABASES[ep_name].append(db_name)

ENDPOINT_NAMES = list(ENDPOINT_NAME_TO_URL.keys())
SPARQL_ENDPOINT_KEYS = list(SPARQL_ENDPOINT.keys())


def resolve_endpoint_url(database: str, endpoint_name: str, endpoint_url: str) -> str:
    """Resolve the SPARQL endpoint URL from various input options.

    Priority: endpoint_url > endpoint_name > database

    Args:
        database: Database name (e.g., 'chembl', 'uniprot')
        endpoint_name: Short endpoint name (e.g., 'ebi', 'sib')
        endpoint_url: Direct endpoint URL

    Returns:
        The resolved SPARQL endpoint URL

    Raises:
        ValueError: If no valid input is provided or input is invalid.
            The error is raised immediately — callers should not retry on the
            same inputs, since the result is deterministic.
    """
    if endpoint_url:
        return endpoint_url
    if endpoint_name:
        if endpoint_name not in ENDPOINT_NAME_TO_URL:
            raise ValueError(
                f"Unknown endpoint_name: '{endpoint_name}'. "
                f"Valid endpoint names are: {', '.join(ENDPOINT_NAMES)}. "
                f"Do not retry with the same value."
            )
        return ENDPOINT_NAME_TO_URL[endpoint_name]
    if database:
        if database not in SPARQL_ENDPOINT:
            # Common mistake: passing an endpoint_name (e.g. 'ebi') as database.
            if database in ENDPOINT_NAME_TO_URL:
                members = ", ".join(ENDPOINT_NAME_TO_DATABASES.get(database, []))
                raise ValueError(
                    f"'{database}' is an endpoint_name, not a database. "
                    f"Pass it as endpoint_name= for cross-database queries, "
                    f"or choose one of its member databases: {members}. "
                    f"Do not retry with the same value."
                )
            raise ValueError(
                f"Unknown database: '{database}'. "
                f"Valid databases are: {', '.join(SPARQL_ENDPOINT_KEYS)}. "
                f"Do not retry with the same value."
            )
        return SPARQL_ENDPOINT[database]["url"]
    raise ValueError(
        "Missing required argument. Provide one of: database (e.g. 'chembl', "
        "'uniprot'), endpoint_name (e.g. 'ebi', 'sib'), or endpoint_url. "
        f"Valid databases: {', '.join(SPARQL_ENDPOINT_KEYS)}."
    )


def raise_for_status_with_body(
    response: httpx.Response,
    *,
    context: str = "",
    client_error_hint: str | None = None,
    server_error_hint: str | None = None,
    body_max: int = 1500,
) -> None:
    """Drop-in replacement for ``response.raise_for_status()``.

    Surfaces the upstream response body in the raised ``ValueError`` so that
    when an external API replies with a useful diagnostic
    (e.g. Virtuoso's ``SPARQL compiler, line 1: Undefined namespace prefix``,
    or TogoID's ``{"message": "no route: pubchem <> chebi"}``), the calling
    agent sees that diagnostic instead of httpx's generic
    ``Client error '4xx' for url ...``.

    Args:
        response: The httpx response to check.
        context: Short label identifying the operation (e.g. "TogoID convertId").
        client_error_hint: Appended on 4xx responses; if None, a generic hint is used.
        server_error_hint: Appended on 5xx responses; if None, a generic hint is used.
        body_max: Truncate the body at this character count.

    Raises:
        ValueError: If the response is non-2xx.
    """
    if response.is_success:
        return
    body = response.text.strip()
    snippet = body[:body_max] + ("\n…[truncated]" if len(body) > body_max else "")
    label = f"{context} " if context else ""
    if 400 <= response.status_code < 500:
        hint = client_error_hint or (
            "The response body above usually states the exact problem. "
            "Verify input parameters and fix the request — do not retry the same input."
        )
    else:
        hint = server_error_hint or (
            "This may be transient or indicate the request is too heavy. "
            "Consider narrowing scope or adding limits before retrying."
        )
    raise ValueError(
        f"{label}HTTP {response.status_code} from {response.url}.\n"
        f"Response body:\n{snippet}\n\n{hint}"
    )


# Making this a @mcp.tool() becomes an error, so we keep it as a function.
async def execute_sparql(
    sparql_query: str,
    database: str = "",
    endpoint_name: str = "",
    endpoint_url: str = "",
) -> str:
    """Execute a SPARQL query on RDF Portal.

    Args:
        sparql_query: The SPARQL query to execute.
        database: The name of the database to query (e.g., 'chembl', 'uniprot').
        endpoint_name: Short endpoint name (e.g., 'ebi', 'sib') for cross-database queries.
        endpoint_url: Direct SPARQL endpoint URL.

    Returns:
        The results of the SPARQL query in CSV format.

    Note:
        Priority: endpoint_url > endpoint_name > database
        For cross-database queries on shared endpoints, use endpoint_name or endpoint_url.
    """
    url = resolve_endpoint_url(database, endpoint_name, endpoint_url)

    extra: dict[str, Any] = {
        "endpoint_url": url,
        "query_sha256": hashlib.sha256(sparql_query.strip().encode("utf-8")).hexdigest(),
    }
    # Privacy-safe structural fingerprint (literals stripped). Full text only
    # when explicitly opted in via TOGOMCP_LOG_QUERY_TEXT (off by default).
    try:
        from togo_mcp import stats as _stats_mod

        extra["query_shape"] = _stats_mod.sparql_shape(sparql_query)
    except Exception:
        pass
    if os.getenv("TOGOMCP_LOG_QUERY_TEXT", "").strip().lower() in ("1", "true", "yes"):
        extra["query_text"] = sparql_query
    _sparql_extra_var.set(extra)

    try:
        response = await _sparql_client.post(
            url, data={"query": sparql_query}, headers={"Accept": "text/csv"}
        )
    except httpx.TimeoutException as exc:
        extra["sparql_status"] = "timeout"
        raise ValueError(
            f"SPARQL endpoint at {url} timed out after {_sparql_client.timeout.read}s. "
            "The query is likely too heavy. Add LIMIT, narrow with specific IRIs or GRAPH "
            "clauses, or split into smaller queries. Do not retry the same query without "
            f"changes. ({exc.__class__.__name__})"
        ) from exc
    except httpx.HTTPError as exc:
        extra["sparql_status"] = "network_error"
        raise ValueError(
            f"SPARQL endpoint at {url} could not be reached: "
            f"{exc.__class__.__name__}: {exc}"
        ) from exc

    extra["http_code"] = response.status_code
    extra["n_bytes"] = len(response.content)
    if response.is_success:
        extra["sparql_status"] = "ok"
        extra["n_rows"] = max(response.text.count("\n") - 1, 0)
    elif 400 <= response.status_code < 500:
        extra["sparql_status"] = "http_4xx"
    else:
        extra["sparql_status"] = "http_5xx"

    raise_for_status_with_body(
        response,
        context="SPARQL endpoint",
        client_error_hint=(
            "The endpoint diagnostic above usually names the exact line/column. "
            "Common causes: syntax error (missing brace/comma), undefined namespace "
            "prefix, unsupported function. Fix the query — do not retry the same text."
        ),
        server_error_hint=(
            "This may be transient or indicate the query is too heavy. Consider "
            "adding LIMIT, stronger filters (specific IRIs, GRAPH clauses), or "
            "splitting the query."
        ),
    )
    return response.text


# The Primary MCP server.
# Pass TogoMCP's OWN version explicitly — otherwise FastMCP defaults serverInfo.version
# to its own package version, so `initialize` would advertise FastMCP's version under
# TogoMCP's name (misleading: it moves on a FastMCP upgrade, not on a TogoMCP release).
try:
    _TOGOMCP_VERSION = _pkg_version("togo-mcp")
except PackageNotFoundError:  # not installed as a distribution (source-tree run)
    _TOGOMCP_VERSION = "0+unknown"

mcp = FastMCP("TogoMCP: RDF Portal MCP Server", version=_TOGOMCP_VERSION)


from fastmcp.server.middleware import Middleware as _Middleware
import inspect as _inspect


class _IgnoreUnknownSearchKwargs(_Middleware):
    """Strip unknown kwargs from `search_*` tool calls before validation.

    LLMs often pass made-up filters (taxon, organism, reviewed, …) to our
    search_* tools. Pydantic's TypeAdapter rejects these with a validation
    error, which is unhelpful. This middleware looks up the target tool's
    function signature and drops any arguments that aren't declared on it.
    """

    _valid_kwargs_cache: dict[str, set[str]] = {}

    async def _valid_kwargs(self, ctx, tool_name: str) -> set[str] | None:
        # Match both root-level `search_*` tools and mounted sub-server search
        # tools, whose names carry a mount prefix (e.g. `togovar_search_variant`).
        if "search_" not in tool_name:
            return None
        cached = self._valid_kwargs_cache.get(tool_name)
        if cached is not None:
            return cached
        server = ctx.fastmcp_context.fastmcp if ctx.fastmcp_context else None
        if server is None:
            return None
        try:
            tool = await server.get_tool(tool_name)
        except Exception:
            return None
        fn = getattr(tool, "fn", None)
        if fn is not None:
            # Local FunctionTool: the wrapped function is the source of truth.
            valid = set(_inspect.signature(fn).parameters)
        else:
            # Mounted sub-server tools (e.g. togovar_search_*) are proxied as
            # FastMCPProviderTool, which exposes no .fn — deriving valid arg
            # names from tool.fn raised AttributeError and killed every call.
            # Fall back to the accepted argument names in the input JSON schema.
            props = (getattr(tool, "parameters", None) or {}).get("properties", {})
            valid = set(props)
        self._valid_kwargs_cache[tool_name] = valid
        return valid

    async def on_call_tool(self, context, call_next):
        name = context.message.name
        valid = await self._valid_kwargs(context, name)
        if valid is not None and context.message.arguments:
            filtered = {k: v for k, v in context.message.arguments.items() if k in valid}
            if filtered.keys() != context.message.arguments.keys():
                context.message.arguments = filtered
        return await call_next(context)


mcp.add_middleware(_IgnoreUnknownSearchKwargs())


# --- Session/static metadata for log records --------------------------------
# Computed once at import: what the server was running. Client (LLM) info is
# read per-call from the MCP context. None values are tolerated downstream.
def _detect_server_version() -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("togo-mcp")
        except PackageNotFoundError:
            return None
    except Exception:
        return None


def _detect_usage_guide_version() -> str | None:
    m = re.search(r"_v(\d+)", os.path.basename(TOGOMCP_USAGE_GUIDE))
    return f"v{m.group(1)}" if m else None


def _detect_mie_bundle_version() -> str | None:
    """sha256[:12] over sorted '<file>=<mie_version>' lines — changes whenever
    any MIE file's mie_version changes. Regex-parsed, no YAML dependency."""
    items: list[str] = []
    try:
        paths = sorted(Path(MIE_DIR).glob("*.yaml"))
    except OSError:
        return None
    for path in paths:
        ver = None
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    m = re.search(r'mie_version:\s*"?([^"\n]+)"?', line)
                    if m:
                        ver = m.group(1).strip()
                        break
        except OSError:
            continue
        items.append(f"{path.name}={ver}")
    if not items:
        return None
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()[:12]


_STATIC_META: dict[str, Any] = {
    "server_version": _detect_server_version(),
    "usage_guide_version": _detect_usage_guide_version(),
    "mie_bundle_version": _detect_mie_bundle_version(),
}

# Salt for hashing client IPs (PII). A stable salt (set TOGOMCP_LOG_HASH_SALT)
# hashes the same IP identically across restarts within a retention window; an
# unset salt is randomized per process, so hashes are not linkable across
# restarts — strictly more private. Raw IPs are never written to the log.
_IP_SALT = os.getenv("TOGOMCP_LOG_HASH_SALT", "").strip() or secrets.token_hex(16)


def _hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(f"{_IP_SALT}:{ip}".encode("utf-8")).hexdigest()[:16]


def _client_info(fctx: Any) -> dict[str, str | None] | None:
    """LLM client (name/version) from the MCP initialize handshake, if present."""
    try:
        params = fctx.session.client_params if fctx else None
        info = getattr(params, "clientInfo", None) if params else None
        if info is None:
            return None
        return {
            "name": getattr(info, "name", None),
            "version": getattr(info, "version", None),
        }
    except Exception:
        return None


def _result_size(result: Any) -> int | None:
    """Best-effort serialized byte size of a tool result (output-size stats)."""
    if result is None:
        return None
    try:
        content = getattr(result, "content", None)
        if content is not None:
            total = 0
            for block in content:
                text = getattr(block, "text", None)
                total += len((text if text is not None else str(block)).encode("utf-8"))
            return total
        sc = getattr(result, "structured_content", None)
        if sc is not None:
            return len(json.dumps(sc, default=str).encode("utf-8"))
        return len(str(result).encode("utf-8"))
    except Exception:
        return None


class _ToolCallLogger(_Middleware):
    """Emit one JSONL record per MCP tool call.

    Enabled by setting TOGOMCP_QUERY_LOG to a filesystem path. Unset/empty =
    disabled (the default), in which case on_call_tool short-circuits and adds
    no measurable overhead. SPARQL calls enrich their record via
    _sparql_extra_var (set inside execute_sparql).
    """

    def __init__(self) -> None:
        log_path = os.getenv("TOGOMCP_QUERY_LOG", "").strip()
        self._enabled = bool(log_path)
        self._log: logging.Logger | None = None
        if self._enabled:
            try:
                log_dir = os.path.dirname(log_path)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                handler = RotatingFileHandler(
                    log_path, maxBytes=50_000_000, backupCount=10, encoding="utf-8"
                )
                handler.setFormatter(logging.Formatter("%(message)s"))
                log = logging.getLogger("togomcp.toolcalls")
                log.setLevel(logging.INFO)
                log.propagate = False
                log.handlers = [handler]
                self._log = log
            except OSError as exc:
                # A logging misconfiguration must never stop the server booting.
                logger.warning(
                    "tool-call logging disabled: cannot open %s (%s)", log_path, exc
                )
                self._enabled = False
                self._log = None

    @staticmethod
    def _client_ip() -> str | None:
        try:
            req: Request = get_http_request()
        except RuntimeError:
            return None
        return req.headers.get("X-Forwarded-For") or (
            req.client.host if req.client else None
        )

    async def on_call_tool(self, context, call_next):
        if not self._enabled:
            return await call_next(context)

        token = _sparql_extra_var.set(None)
        start = time.perf_counter()
        status = "ok"
        error_class: str | None = None
        error_message: str | None = None
        result = None
        try:
            result = await call_next(context)
            return result
        except BaseException as exc:
            status = "error"
            error_class = exc.__class__.__name__
            error_message = str(exc)[:500]
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            extra = _sparql_extra_var.get()
            _sparql_extra_var.reset(token)
            fctx = context.fastmcp_context
            record: dict[str, Any] = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": context.message.name,
                "args": context.message.arguments or {},
                "status": status,
                "elapsed_ms": elapsed_ms,
                "output_bytes": _result_size(result),
                "session_id": getattr(fctx, "session_id", None) if fctx else None,
                "request_id": getattr(fctx, "request_id", None) if fctx else None,
                "origin_request_id": (
                    getattr(fctx, "origin_request_id", None) if fctx else None
                ),
                "client_id": getattr(fctx, "client_id", None) if fctx else None,
                "transport": getattr(fctx, "transport", None) if fctx else None,
                "ip_hash": _hash_ip(self._client_ip()),
                "meta": {**_STATIC_META, "client": _client_info(fctx)},
            }
            if error_class is not None:
                record["error_class"] = error_class
                record["error_message"] = error_message
            if extra:
                record["extra"] = extra
            try:
                self._log.info(json.dumps(record, default=str))  # type: ignore[union-attr]
            except Exception:
                # Logging must never break a tool call.
                pass


mcp.add_middleware(_ToolCallLogger())


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.custom_route("/", methods=["GET"])
async def index(request: Request) -> HTMLResponse:
    with open(INDEX_HTML) as f:
        html_content = f.read()
    return HTMLResponse(html_content)


# --------------------------------------------------------------------------- #
# Usage-stats dashboard (/stats, /stats.json) — HTTP Basic protected.
#
# Reads the JSONL written by _ToolCallLogger and serves monthly aggregates.
# Disabled unless BOTH TOGOMCP_STATS_USER and TOGOMCP_STATS_PASSWORD are set —
# the route then refuses (503) so stats are never exposed unauthenticated.
# Results are cached for _STATS_TTL seconds to bound recompute cost; computing
# is read-only and cannot affect tool calls.
# --------------------------------------------------------------------------- #
import base64 as _base64
import hmac as _hmac

_STATS_TTL = 60.0
_stats_cache: dict[str, Any] = {"ts": 0.0, "data": None}


def _stats_configured() -> tuple[str, str] | None:
    user = os.getenv("TOGOMCP_STATS_USER", "")
    pw = os.getenv("TOGOMCP_STATS_PASSWORD", "")
    return (user, pw) if user and pw else None


def _check_basic_auth(request: Request, creds: tuple[str, str]) -> bool:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = _base64.b64decode(header[6:]).decode("utf-8")
        user, _, pw = decoded.partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    # Constant-time compare to avoid leaking credential length/content via timing.
    return _hmac.compare_digest(user, creds[0]) and _hmac.compare_digest(pw, creds[1])


def _get_stats() -> dict[str, Any]:
    now = time.monotonic()
    if _stats_cache["data"] is not None and (now - _stats_cache["ts"]) < _STATS_TTL:
        return _stats_cache["data"]
    from togo_mcp import stats as _stats_mod

    data = _stats_mod.compute_stats(endpoints_csv=ENDPOINTS_CSV, mie_dir=MIE_DIR)
    _stats_cache["data"] = data
    _stats_cache["ts"] = now
    return data


_AUTH_HEADERS = {"WWW-Authenticate": 'Basic realm="TogoMCP stats"'}


@mcp.custom_route("/stats", methods=["GET"])
async def stats_dashboard(request: Request) -> HTMLResponse:
    creds = _stats_configured()
    if creds is None:
        return HTMLResponse(
            "<h1>503</h1><p>Stats dashboard not configured.</p>", status_code=503
        )
    if not _check_basic_auth(request, creds):
        return HTMLResponse("Authentication required", status_code=401, headers=_AUTH_HEADERS)
    from togo_mcp import stats as _stats_mod

    try:
        return HTMLResponse(_stats_mod.render_html(_get_stats()))
    except Exception as exc:  # never 500 with a stack trace; logging stays read-only
        logger.warning("stats render failed: %s", exc)
        return HTMLResponse("<h1>500</h1><p>Could not compute stats.</p>", status_code=500)


@mcp.custom_route("/stats.json", methods=["GET"])
async def stats_json(request: Request) -> JSONResponse:
    creds = _stats_configured()
    if creds is None:
        return JSONResponse({"error": "not configured"}, status_code=503)
    if not _check_basic_auth(request, creds):
        return JSONResponse({"error": "auth required"}, status_code=401, headers=_AUTH_HEADERS)
    try:
        return JSONResponse(_get_stats())
    except Exception as exc:
        logger.warning("stats compute failed: %s", exc)
        return JSONResponse({"error": "compute failed"}, status_code=500)
