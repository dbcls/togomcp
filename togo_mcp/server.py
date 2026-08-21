import asyncio
import contextlib
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
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)

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
ENDPOINTS_CSV = str(CWD.joinpath("resources", "endpoints.csv"))
INDEX_HTML = str(CWD.joinpath("docs", "togomcp-intro.html"))
TUTORIAL_DIR = CWD.joinpath("docs", "tutorial")

# Shared httpx client for SPARQL queries.
#
# 90s, not 60s: RDF Portal endpoints charge a large COLD-CACHE penalty on the
# first touch of an entity's index pages. Measured on the SIB endpoint
# 2026-07-30 across five never-queried UniProt accessions, a MINIMAL
# single-protein lookup (one IRI, LIMIT 5) took 53.9-62.1s cold and 0.2s warm.
# A 60s ceiling sat INSIDE that band, so whether a perfectly good query
# succeeded was a coin flip — two such lookups timed out in production
# 2026-07-27. 90s clears the observed cold maximum with headroom while still
# cutting off genuinely runaway queries.
#
# Raising it does NOT make retries free: an ABORTED query does not warm the
# cache (verified — abort at 20s, retry still 55.3s), so only a query allowed
# to COMPLETE pays the cost once for everyone after it. That is the whole point
# of the higher ceiling.
# The 90s ceiling assumes the CLIENT is willing to wait 90s. An MCP connector
# usually is not: measured 2026-08-12 against production during a total RDF
# Portal outage, TCP+TLS to the endpoint completed in 25ms and then not one byte
# arrived, so every query burned the full 90s and the caller's connector gave up
# first — the user saw "no response", never the diagnostic below. Hence the
# liveness watchdog further down: a DEAD endpoint must fail fast (~13s), while a
# slow-but-alive one keeps the whole 90s.
_SPARQL_TIMEOUT_SECONDS = 90.0

# Connecting is not querying. 15s is ~600x the observed healthy connect time and
# still far inside any connector's patience, so a connect that misses it means
# the host is unreachable — a fact worth reporting as itself rather than as a
# generic timeout.
_SPARQL_CONNECT_TIMEOUT_SECONDS = 15.0

# How long a caller may wait for a free connection from the pool. Kept SHORT and
# separate from the read budget on purpose: waiting here is our own saturation,
# not the endpoint's fault, and it must never masquerade as "your query is slow".
_SPARQL_POOL_TIMEOUT_SECONDS = 5.0

# httpx's default Limits(max_connections=100) is GLOBAL, not per-host. Measured:
# 110 queries parked on one dead endpoint occupied all 100 slots, and a query to
# a DIFFERENT, healthy endpoint could then not get a connection at all. Making
# the ceiling explicit does not by itself prevent that — the short pool timeout
# above and the circuit breaker below do — but it documents the shared resource
# the two of them protect.
_SPARQL_MAX_CONNECTIONS = 100

_sparql_client = httpx.AsyncClient(
    timeout=httpx.Timeout(
        _SPARQL_TIMEOUT_SECONDS,
        connect=_SPARQL_CONNECT_TIMEOUT_SECONDS,
        pool=_SPARQL_POOL_TIMEOUT_SECONDS,
    ),
    limits=httpx.Limits(
        max_connections=_SPARQL_MAX_CONNECTIONS,
        max_keepalive_connections=20,
    ),
)

# --- Endpoint liveness ------------------------------------------------------
#
# A SPARQL read timeout has three possible causes, and until 2026-08-12 the error
# message offered only two (heavy query / cold cache). The third — the endpoint
# is simply not answering anything — is invisible at the socket layer: the
# connection opens, the TLS handshake completes, and then nothing. Only a
# *read-level* probe can tell it apart, so that is what this does: when a query
# is still running after _PROBE_AFTER_SECONDS, send `ASK {}` (a query with no
# work to do) and see whether the endpoint answers at all.
#
# Cost on the fast path is zero: a query that finishes inside the delay never
# triggers a probe.
_PROBE_AFTER_SECONDS = 8.0
_PROBE_TIMEOUT_SECONDS = 5.0

# The probe MUST NOT share _sparql_client. During the outage this exists for,
# that pool is exactly what fills up, so a probe sent through it would queue
# behind the very failures it is meant to diagnose — and a probe that fails
# because it never got a connection cannot distinguish "endpoint is down" from
# "our pool is full". Its own small pool keeps the answer meaningful.
_probe_client = httpx.AsyncClient(
    timeout=_PROBE_TIMEOUT_SECONDS,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)

# Circuit breaker. Once an endpoint has been observed unresponsive, further
# queries to it are refused instantly for this long instead of parking another
# connection on it for 90s. This is what keeps one dead endpoint from eating the
# shared pool and starving the healthy ones.
_ENDPOINT_DOWN_TTL_SECONDS = 60.0
_endpoint_down_until: dict[str, float] = {}

# Statuses a reverse proxy emits when it cannot get an answer from the backend.
# Virtuoso itself never returns these, so they mean "infrastructure", not "your
# query" — see the gateway branch in execute_sparql.
_GATEWAY_STATUS = frozenset({502, 503, 504})


class _EndpointUnresponsive(Exception):
    """The endpoint failed a liveness probe: it is not answering anything."""


def _mark_endpoint_down(url: str) -> None:
    _endpoint_down_until[url] = time.monotonic() + _ENDPOINT_DOWN_TTL_SECONDS


def _clear_endpoint_down(url: str) -> None:
    _endpoint_down_until.pop(url, None)


def _endpoint_down_remaining(url: str) -> float | None:
    """Seconds left on the breaker for ``url``, or None if it is closed."""
    deadline = _endpoint_down_until.get(url)
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        _endpoint_down_until.pop(url, None)
        return None
    return remaining


async def _probe_endpoint(url: str) -> bool:
    """True if ``url`` answers a trivial ASK within the probe budget.

    ANY HTTP response counts as alive, including 4xx/5xx: the question is
    whether the server is answering at all, not whether it liked the query.
    """
    try:
        await _probe_client.post(
            url, data={"query": "ASK {}"}, headers={"Accept": "text/csv"}
        )
    except httpx.HTTPError:
        return False
    return True


async def _post_with_liveness_watchdog(
    url: str, sparql_query: str, extra: dict[str, Any]
) -> httpx.Response:
    """POST the query, aborting early if the endpoint turns out to be dead.

    Records the probe verdict in ``extra["liveness_probe"]`` so the log — and the
    timeout message — can say whether the endpoint was confirmed up.
    """
    main = asyncio.ensure_future(
        _sparql_client.post(url, data={"query": sparql_query}, headers={"Accept": "text/csv"})
    )
    done, _pending = await asyncio.wait({main}, timeout=_PROBE_AFTER_SECONDS)
    if done:
        return main.result()  # re-raises the original httpx error, if any

    if await _probe_endpoint(url):
        # Endpoint confirmed answering. Give the query its full budget — this is
        # the cold-cache case the 90s ceiling exists for.
        extra["liveness_probe"] = "passed"
        return await main
    extra["liveness_probe"] = "failed"
    main.cancel()
    with contextlib.suppress(BaseException):
        await main
    raise _EndpointUnresponsive(url)


def _endpoint_down_message(url: str, *, cached_for: float | None = None) -> str:
    """Caller-facing text for cause 3: the endpoint itself is not answering."""
    if cached_for is None:
        evidence = (
            f"A liveness check (`ASK {{}}`, a query with no work to do) got no "
            f"answer within {_PROBE_TIMEOUT_SECONDS:.0f}s. A healthy endpoint "
            f"answers it in well under a second."
        )
    else:
        evidence = (
            f"This endpoint failed a liveness check moments ago, so this call was "
            f"refused without contacting it. It will be retried automatically "
            f"after ~{cached_for:.0f}s."
        )
    return (
        f"SPARQL endpoint at {url} is NOT RESPONDING. {evidence}\n\n"
        "THE PROBLEM IS NOT YOUR QUERY — it was never executed. Do NOT rewrite, "
        "narrow, or simplify it, and do NOT retry in a loop: further calls to this "
        f"endpoint are refused instantly for the next {_ENDPOINT_DOWN_TTL_SECONDS:.0f}s.\n\n"
        "What to do instead:\n"
        "(a) Tell the user this endpoint is currently unavailable, and name it.\n"
        "(b) Only the databases on THIS endpoint are affected — those on other "
        "endpoints still work. get_sparql_endpoints() shows which database sits on "
        "which endpoint; if another one can answer the question, use it.\n"
        "(c) The REST search tools (search_uniprot_entity, search_pdb_entity, "
        "search_chembl_*, ncbi_esearch, togovar_*, …) call different hosts entirely "
        "and are unaffected.\n"
        "(d) get_MIE_file, TogoMCP_Usage_Guide and get_sparql_endpoints read local "
        "files and keep working, so you can still prepare the query for later."
    )


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

    # Cause 3, already established: refuse instantly rather than park another
    # connection on a dead endpoint for 90s.
    cached_down = _endpoint_down_remaining(url)
    if cached_down is not None:
        extra["sparql_status"] = "endpoint_unresponsive"
        extra["circuit_breaker"] = "open"
        raise ValueError(_endpoint_down_message(url, cached_for=cached_down))

    try:
        response = await _post_with_liveness_watchdog(url, sparql_query, extra)
    except _EndpointUnresponsive as exc:
        extra["sparql_status"] = "endpoint_unresponsive"
        _mark_endpoint_down(url)
        raise ValueError(_endpoint_down_message(url)) from exc
    except httpx.PoolTimeout as exc:
        # Our own client ran out of connections — neither the query nor the
        # endpoint is at fault, so neither of the timeout hints below applies.
        extra["sparql_status"] = "pool_exhausted"
        raise ValueError(
            f"Could not get a connection to {url} within "
            f"{_SPARQL_POOL_TIMEOUT_SECONDS:.0f}s: this server's SPARQL connection "
            f"pool (max {_SPARQL_MAX_CONNECTIONS}) is currently full, usually because "
            "many queries are queued behind a slow or unresponsive endpoint. "
            "Your query was NOT executed and is not the problem — do not rewrite it. "
            "Wait a few seconds and retry once; if it recurs, the endpoint you are "
            "querying is likely degraded."
        ) from exc
    except httpx.ConnectTimeout as exc:
        # No TCP/TLS connection in 15s: the host is unreachable, full stop. No
        # probe needed — this IS the probe result.
        extra["sparql_status"] = "endpoint_unresponsive"
        _mark_endpoint_down(url)
        raise ValueError(
            f"SPARQL endpoint at {url} did not accept a connection within "
            f"{_SPARQL_CONNECT_TIMEOUT_SECONDS:.0f}s.\n\n"
            + _endpoint_down_message(url).split("\n\n", 1)[1]
        ) from exc
    except httpx.TimeoutException as exc:
        # A read/write timeout that survived the watchdog. If the probe ran and
        # passed, the endpoint is demonstrably up, which narrows the causes to
        # two — and lets us say so instead of guessing.
        extra["sparql_status"] = "timeout"
        probed = extra.get("liveness_probe") == "passed"
        evidence = (
            "This endpoint ANSWERED a liveness check while your query was running, "
            "so it is up and reachable — cause 3 (endpoint down) is ruled out. "
            if probed
            else ""
        )
        raise ValueError(
            f"SPARQL endpoint at {url} timed out after {_sparql_client.timeout.read}s. "
            f"{evidence}"
            "TWO different causes are possible — check which one before acting:\n"
            "(1) THE QUERY IS TOO HEAVY (most likely at this duration). Narrow it: "
            "add or lower LIMIT, anchor on specific IRIs, drop repeated self-joins on "
            "the same predicate (?s p ?a, ?b, ?c), and split multi-graph joins into "
            "separate queries. Do not re-send it unchanged.\n"
            "(2) THE ENDPOINT WAS COLD. A first-ever query against a large graph can "
            "take ~1 minute while indexes page in, even for a minimal lookup. If your "
            "query is ALREADY anchored on specific IRIs and carries a small LIMIT, "
            "there is nothing to narrow and this is the likely cause — the same query "
            "may well succeed on a second attempt. But an aborted query does NOT warm "
            "the cache, so a retry costs the same again: retry at most ONCE, never loop."
            f" ({exc.__class__.__name__})"
        ) from exc
    except httpx.HTTPError as exc:
        # Refused, reset, DNS failure, protocol error — the endpoint is not
        # serving, so open the breaker here too.
        extra["sparql_status"] = "network_error"
        _mark_endpoint_down(url)
        raise ValueError(
            f"SPARQL endpoint at {url} could not be reached: "
            f"{exc.__class__.__name__}: {exc}. Your query was not executed — this is "
            "an endpoint/network failure, not a query problem, so do not rewrite it. "
            "Other endpoints are unaffected; see get_sparql_endpoints()."
        ) from exc

    extra["http_code"] = response.status_code
    extra["n_bytes"] = len(response.content)
    if response.is_success:
        # Answered with data — the endpoint is demonstrably alive.
        _clear_endpoint_down(url)
        extra["sparql_status"] = "ok"
        extra["n_rows"] = max(response.text.count("\n") - 1, 0)
    elif 400 <= response.status_code < 500:
        _clear_endpoint_down(url)
        extra["sparql_status"] = "http_4xx"
    elif response.status_code in _GATEWAY_STATUS:
        # A reverse proxy answering for a backend it could not reach. Virtuoso
        # never emits these; nginx does, in ~0.1s, with an HTML error page. The
        # generic 5xx advice ("the query may be too heavy — add LIMIT") is then
        # actively wrong: the SPARQL engine never saw the query. Observed
        # 2026-08-12 on the ebi endpoint, where `ASK {}` and a one-IRI lookup
        # 502'd identically while the same queries had succeeded seconds earlier.
        #
        # Which of the two it is cannot be read off the status code, so ask the
        # endpoint: the same liveness probe used for timeouts settles it.
        if not await _probe_endpoint(url):
            extra["sparql_status"] = "endpoint_unresponsive"
            extra["liveness_probe"] = "failed"
            _mark_endpoint_down(url)
            raise ValueError(
                f"SPARQL endpoint at {url} returned HTTP {response.status_code} from "
                f"its gateway, and is not answering a trivial query either.\n\n"
                + _endpoint_down_message(url).split("\n\n", 1)[1]
            )
        _clear_endpoint_down(url)
        extra["sparql_status"] = "http_gateway"
        extra["liveness_probe"] = "passed"
        raise ValueError(
            f"SPARQL endpoint at {url} returned HTTP {response.status_code} from its "
            "GATEWAY (a reverse proxy), not from the SPARQL engine — so the engine may "
            "never have seen this query.\n\n"
            "A liveness check right afterwards SUCCEEDED, so the endpoint is up and "
            "this failure is specific to this request: either the backend dropped this "
            "one query, or the upstream blipped for a moment.\n\n"
            "Retry ONCE, unchanged — that is the single most likely fix here, and "
            "rewriting the query first would be guesswork. If the retry fails the same "
            "way, THEN treat it as too heavy: lower LIMIT, anchor on specific IRIs, and "
            "split multi-graph joins. Never loop."
        )
    else:
        _clear_endpoint_down(url)
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

# Every tool this server exposes is a query, search, or ID conversion — nothing
# writes to any database. Say so in the protocol rather than only in prose: a
# client cannot infer it from the tool name, and the MCP default is the unsafe
# one. OpenAI's ChatGPT developer-mode docs are explicit that "tools without this
# hint are treated as write actions", which means an unannotated read-only server
# gets a confirmation prompt on EVERY call, and can be refused outright by a plan
# that only permits read/search connectors. Claude and other clients use the same
# hint to decide what may be auto-approved.
#
# `openWorldHint` is True because every tool reaches an external endpoint (RDF
# Portal SPARQL, NCBI, TogoID, …) rather than a closed local dataset.
# `destructiveHint`/`idempotentHint` are deliberately unset: the MCP spec defines
# both as meaningful only when readOnlyHint is false.
#
# Apply this to EVERY new tool — a tool without it silently reverts to being
# treated as a writer. `tests/test_tool_descriptions.py` enforces it.
READ_ONLY_TOOL = {"readOnlyHint": True, "openWorldHint": True}


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
    """sha256[:12] over sorted '<file>=<sha256(bytes)>' — a content fingerprint.

    DERIVED, never hand-maintained. The previous version hashed each file's
    `mie_version:` field, which v3 dropped: every lookup returned None, so the
    digest reduced to a hash of the FILE NAMES and stayed frozen at 91ba06da8a78
    across a month of MIE edits. It stamps every tool-call log record's `meta`,
    where its whole job is telling which MIE content was live when a query ran,
    so a frozen value silently destroys that attribution. It also failed
    invisibly - a plausible 12-hex digest, which the test asserted the shape of.

    Hashing bytes removes the coupling to any field the format may rename. Unlike
    the trap-candidate date filter (which takes MIN of `verified.date`, so it moves
    only on a full re-verification), a fingerprint must move on ANY touch.
    """
    try:
        paths = sorted(Path(MIE_DIR).glob("*.yaml"))
    except OSError:
        return None
    items: list[str] = []
    for path in paths:
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        items.append(f"{path.name}={digest}")
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
# restarts — strictly more private.
#
# `ip_hash` is written unconditionally and is the field stats.py aggregates on.
# The RAW address is a separate, opt-in field (`ip`, see TOGOMCP_LOG_RAW_IP on
# _ToolCallLogger) — the hash is kept alongside it so a log excerpt can be
# shared or exported with `ip` stripped and still aggregate identically.
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

    TOGOMCP_LOG_RAW_IP additionally records the client address in the clear, as
    `ip`, so an abusive caller can actually be identified and blocked. It is
    off by default and fail-closed on purpose: absent, empty or misspelled all
    mean OFF, so a deploy-time env-forwarding miss (deploy.sh forwards a FIXED
    list — see CLAUDE.md) loses the raw address rather than silently leaking
    one. Turning it on makes the log PII, including everything /stats/log
    streams; `ip_hash` is unaffected and is written either way.
    """

    def __init__(self) -> None:
        log_path = os.getenv("TOGOMCP_QUERY_LOG", "").strip()
        self._enabled = bool(log_path)
        self._raw_ip = os.getenv("TOGOMCP_LOG_RAW_IP", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
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
        """Client address for the log: the peer as *uvicorn* resolved it.

        Deliberately NOT `X-Forwarded-For` read off the request. uvicorn's
        ProxyHeadersMiddleware already substitutes the client address from that
        header — but only when the peer is listed in `forwarded_allow_ips`
        (main.py), and it walks the chain right-to-left to the first untrusted
        hop. Reading the header here would skip that check entirely: anyone who
        can reach the port could name any address they like, which is worthless
        for the one job a raw IP has (attributing abuse). So: peer only, and let
        the trust decision stay where it is configured.
        """
        try:
            req: Request = get_http_request()
        except RuntimeError:
            return None
        return req.client.host if req.client else None

    @staticmethod
    def _forwarded_for() -> str | None:
        """Raw X-Forwarded-For chain, verbatim — UNTRUSTED forensic context.

        Caller-supplied and therefore spoofable; it is recorded next to `ip` to
        show what was claimed, never as a substitute for what was observed.
        """
        try:
            req: Request = get_http_request()
        except RuntimeError:
            return None
        xff = req.headers.get("X-Forwarded-For")
        return xff[:200] if xff else None

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
            client_ip = self._client_ip()
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
                "ip_hash": _hash_ip(client_ip),
                "meta": {**_STATIC_META, "client": _client_info(fctx)},
            }
            if self._raw_ip:
                record["ip"] = client_ip
                fwd = self._forwarded_for()
                if fwd:
                    record["forwarded_for"] = fwd
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


@mcp.custom_route("/stats/log", methods=["GET"])
async def stats_raw_log(request: Request):
    """Stream the raw JSONL tool-call log behind the same Basic auth as /stats.

    The dashboard's tables are lossy roll-ups; the questions worth asking next
    are usually ones no pre-computed table answers (this release came out of
    exactly that — reading the raw log surfaced two silent zero-row bugs and a
    timeout misdiagnosis that every aggregate had shown as unremarkable).

    Serves the SAME files `compute_stats` aggregates — active plus rotated —
    concatenated OLDEST FIRST so the stream reads chronologically. Streaming,
    not read-into-memory: this file grows without bound between rotations.
    The path comes from TOGOMCP_QUERY_LOG only; nothing is caller-supplied, so
    there is no traversal surface.

    NOTE: this streams records verbatim, so under TOGOMCP_LOG_RAW_IP it serves
    raw client IPs (`ip`) to anyone holding the dashboard credentials. The
    aggregate views never do. Treat the credentials accordingly.
    """
    creds = _stats_configured()
    if creds is None:
        return PlainTextResponse("Stats dashboard not configured.", status_code=503)
    if not _check_basic_auth(request, creds):
        return PlainTextResponse(
            "Authentication required", status_code=401, headers=_AUTH_HEADERS
        )
    from togo_mcp import stats as _stats_mod

    base = os.getenv("TOGOMCP_QUERY_LOG", "").strip()
    paths = _stats_mod.log_paths(base)
    if not paths:
        return PlainTextResponse("No log file found.", status_code=404)

    def _iter_chunks():
        # Reversed: log_paths returns [base (newest), base.1, base.2 (oldest)].
        for path in reversed(paths):
            try:
                with open(path, "rb") as fh:
                    while chunk := fh.read(64 * 1024):
                        yield chunk
            except OSError as exc:  # a file rotated away mid-stream — skip it
                logger.warning("stats log stream: skipping %s (%s)", path, exc)

    stamp = time.strftime("%Y%m%d", time.gmtime())
    total = sum(os.path.getsize(p) for p in paths if os.path.exists(p))
    return StreamingResponse(
        _iter_chunks(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="togomcp-log-{stamp}.jsonl"',
            # Advisory only: rotation could change the real length mid-stream,
            # so this is not sent as Content-Length.
            "X-Log-Bytes": str(total),
            "X-Log-Files": str(len(paths)),
        },
    )


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


@mcp.custom_route("/tutorial", methods=["GET"])
async def tutorial_en(request: Request) -> HTMLResponse:
    return HTMLResponse(TUTORIAL_DIR.joinpath("tutorial-en.html").read_text(encoding="utf-8"))

@mcp.custom_route("/tutorial/ja", methods=["GET"])
async def tutorial_ja(request: Request) -> HTMLResponse:
    return HTMLResponse(TUTORIAL_DIR.joinpath("tutorial-ja.html").read_text(encoding="utf-8"))

