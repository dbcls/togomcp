# TogoMCP Tool-Call Log Specification

This document specifies the JSONL log written by the `_ToolCallLogger` middleware
in [`togo_mcp/server.py`](../../server.py) and consumed by
[`togo_mcp/stats.py`](../../stats.py). It is the authoritative reference for the
record shape, field semantics, and the privacy guarantees the format upholds.

## Overview

- **One line per MCP tool call.** Each line is a self-contained JSON object
  (JSON Lines / NDJSON). Lines are independent and unordered — every record
  carries its own UTC timestamp (`ts`).
- **Emitted by** `_ToolCallLogger`, a FastMCP middleware wrapping `on_call_tool`.
- **Written through** a `RotatingFileHandler`: `maxBytes=50_000_000` (50 MB),
  `backupCount=10`. The active file is the configured path; rotated siblings are
  `<path>.1` … `<path>.10` (newest-to-oldest). `stats.py:log_paths()` reads all
  of them.
- **Failure-isolated.** Logging never affects a tool call: a serialization or
  I/O error inside the logger is swallowed, and a logging misconfiguration at
  startup disables logging rather than crashing the server.

## Enabling and configuration

Logging is **off by default**. It is controlled entirely by environment
variables read at process start:

| Env var | Effect | Default |
| --- | --- | --- |
| `TOGOMCP_QUERY_LOG` | Filesystem path for the JSONL log. **Setting it (non-empty) enables logging.** Unset/empty = disabled, and `on_call_tool` short-circuits with no measurable overhead. Parent directories are created if needed. | unset (disabled) |
| `TOGOMCP_LOG_QUERY_TEXT` | When truthy (`1`/`true`/`yes`), the raw SPARQL query text is added to `extra.query_text`. Off by default — normally only the hash and structural shape are stored. | off |
| `TOGOMCP_LOG_HASH_SALT` | Salt for hashing client IPs. A stable salt hashes the same IP identically across restarts (linkable within a retention window); when unset, a fresh random salt is generated per process, so IP hashes are **not** linkable across restarts (strictly more private). | random per process |
| `TOGOMCP_LOG_RAW_IP` | When truthy (`1`/`true`/`yes`/`on`), the client IP is **also** recorded in the clear as `ip` (and the raw `X-Forwarded-For` chain as `forwarded_for`). Off by default; `ip_hash` is written either way. Fail-closed: absent, empty, or misspelled all mean off. | off |

## Privacy model

By default the format keeps raw personal and query-content data out of the log.
One knob deliberately trades that away, and it is stated first because it
reverses a guarantee earlier versions of this document made unconditionally:

- **Client IPs are pseudonymous by default, raw only on request.** `ip_hash` —
  `sha256("<salt>:<ip>")` truncated to 16 hex chars — is always written; see
  `TOGOMCP_LOG_HASH_SALT` above. The raw address is written as `ip` **only**
  under the explicit `TOGOMCP_LOG_RAW_IP` opt-in, whose purpose is identifying
  an abusive caller well enough to block them. With it on, the log is personal
  data: it needs a retention and access policy, and note that `/stats/log`
  streams those records verbatim to anyone holding the dashboard credentials.
  The hash is kept alongside `ip` precisely so an excerpt can be shared with
  `ip` stripped and still aggregate identically.
- **What `ip` actually contains.** The peer address as uvicorn's
  `ProxyHeadersMiddleware` resolved it — i.e. the real client only when the
  proxy's address is trusted via `forwarded_allow_ips` (`TOGOMCP_FORWARDED_ALLOW_IPS`,
  see `main.py`); otherwise it is the proxy. The `X-Forwarded-For` header is
  never read directly for this field: it is caller-supplied and spoofable by
  anyone who can reach the port, which would make it worthless for attribution.
  It is recorded separately and verbatim as `forwarded_for` (truncated to 200
  chars) so the claimed chain can be compared against the observed peer.
- **SPARQL query text is not stored by default.** Records carry `query_sha256`
  (an identity/dedup key) and `query_shape` (a structural fingerprint with all
  string-literal *contents* stripped — see [Query shape](#query-shape)). Raw
  text appears only under the explicit `TOGOMCP_LOG_QUERY_TEXT` opt-in.
- **Aggregation only ever counts.** `stats.py` derives categories and tallies;
  it never emits `args`, `ip`/`ip_hash`, or query text in its output — the
  per-client "IPs" column is a *count* of distinct addresses, never a list.

## Record schema

Every record is a JSON object with the following top-level fields. Fields marked
*(nullable)* may be `null` when the value is unavailable (e.g. no HTTP request
context under stdio transport).

| Field | Type | Present | Description |
| --- | --- | --- | --- |
| `ts` | string | always | Event timestamp, ISO 8601 with UTC offset (`datetime.now(timezone.utc).isoformat()`). The canonical bucketing key. |
| `tool` | string | always | MCP tool name as invoked (e.g. `run_sparql`, `get_MIE_file`, `togoid_convertId`). |
| `args` | object | always | The tool's arguments, verbatim (`{}` if none). |
| `status` | string | always | `"ok"` if the tool returned; `"error"` if it raised. |
| `elapsed_ms` | number | always | Wall-clock duration of the call in milliseconds, rounded to 2 dp. |
| `output_bytes` | integer | *(nullable)* | Best-effort serialized byte size of the tool result (sum of text content blocks, else JSON-encoded structured content, else `str()`). `null` on empty/unmeasurable results. |
| `session_id` | string | *(nullable)* | FastMCP session id. |
| `request_id` | string | *(nullable)* | FastMCP request id for this call. |
| `origin_request_id` | string | *(nullable)* | Originating request id (for nested/forwarded calls). |
| `client_id` | string | *(nullable)* | FastMCP client id. |
| `transport` | string | *(nullable)* | Transport in use (e.g. `http`, `stdio`). |
| `ip_hash` | string | *(nullable)* | Salted, truncated SHA-256 of the client IP. `null` when there is no HTTP request context (e.g. stdio). |
| `ip` | string | *(nullable)*, opt-in | Raw client IP — present only under `TOGOMCP_LOG_RAW_IP`. Same source as `ip_hash`: the peer address as resolved by uvicorn's proxy-header handling. |
| `forwarded_for` | string | opt-in, when sent | Raw `X-Forwarded-For` header, verbatim, truncated to 200 chars. **Untrusted** — caller-supplied context for `ip`, not a substitute for it. Present only under `TOGOMCP_LOG_RAW_IP`, and only when the header was sent. |
| `meta` | object | always | Server/build metadata — see [`meta`](#meta-object). |
| `error_class` | string | on error only | Exception class name — **in practice almost always `ToolError`**. FastMCP wraps a tool's raised exception before it reaches the logging middleware, so the original class (e.g. `ValueError`) is not preserved here. To distinguish an intentional error from a genuine bug, parse `error_message`, not this field. |
| `error_message` | string | on error only | Exception message, truncated to 500 chars. Carries the FastMCP wrapper prefix, e.g. `Error calling tool 'run_sparql': …`. |
| `extra` | object | SPARQL calls only | SPARQL-specific enrichment — see [`extra`](#extra-object-sparql-only). |

### `meta` object

Static per-process build/version identifiers plus the reporting client:

| Field | Type | Description |
| --- | --- | --- |
| `server_version` | string \| null | Installed `togo-mcp` package version. |
| `usage_guide_version` | string \| null | Detected usage-guide bundle version (e.g. `v6`), parsed from the served directory name. |
| `mie_bundle_version` | string \| null | `sha256[:12]` over sorted `<file>=<sha256(bytes)>` across all MIE YAMLs — a derived CONTENT fingerprint, so it moves on any edit to any MIE (and on add/remove/rename). Before 2026-08-21 it hashed a `mie_version:` field that v3 had dropped, leaving it frozen at `91ba06da8a78` — records in that window cannot be attributed to an MIE bundle. |
| `client` | object \| null | Reporting MCP client `{ "name", "version" }`, when advertised. |

### `extra` object (SPARQL only)

Present only on `run_sparql` calls. Populated inside `execute_sparql` and passed
to the logger via a `ContextVar`. The field set depends on how far the call got:

| Field | Type | Present | Description |
| --- | --- | --- | --- |
| `endpoint_url` | string | always | Resolved SPARQL endpoint URL the query was sent to. |
| `query_sha256` | string | always | SHA-256 of the stripped query text — stable identity/dedup key. |
| `query_shape` | object | always | Privacy-safe structural fingerprint — see [Query shape](#query-shape). |
| `query_text` | string | opt-in only | Raw query text; only when `TOGOMCP_LOG_QUERY_TEXT` is enabled. |
| `sparql_status` | string | always† | Collection-level outcome — see below. †Set on every code path (success, timeout, network error, HTTP 4xx/5xx). |
| `http_code` | integer | on HTTP response | HTTP status code returned by the endpoint. Absent if the request never completed (timeout / network error). |
| `n_bytes` | integer | on HTTP response | Size of the raw response body in bytes. |
| `n_rows` | integer | on success | CSV data-row count (`newline count − 1`, floored at 0). Present only when `sparql_status == "ok"`. |

#### `sparql_status` values (as recorded)

| Value | Meaning |
| --- | --- |
| `ok` | HTTP 2xx response received. |
| `http_4xx` | HTTP 4xx — from a SPARQL endpoint, almost always a malformed query. |
| `http_5xx` | HTTP 5xx — endpoint-side server error. |
| `timeout` | Request timed out (`httpx.TimeoutException`); query likely too heavy. |
| `network_error` | Endpoint unreachable (other `httpx.HTTPError`). |

`stats.py` further refines these into a reporting taxonomy: `ok` splits into
`ok` / `empty_result` (`n_rows == 0`) / `huge_result` (`n_bytes ≥ 10 MB`);
`http_4xx → syntax_error`, `http_5xx → server_error`,
`network_error → endpoint_down`, and anything else → `other_error`.

## Query shape

`extra.query_shape` is a structural, privacy-safe fingerprint of the SPARQL
query, produced by `stats.sparql_shape()`. **String-literal contents are
stripped before any feature extraction**, so user-supplied text never leaks;
what remains is schema-level.

| Field | Type | Description |
| --- | --- | --- |
| `form` | string | Query form: `select` / `ask` / `construct` / `describe` / `other`. |
| `from` | string[] | Graph IRIs from `FROM` / `FROM NAMED` clauses (max 20). The only place IRIs are retained. |
| `predicates` | string[] | Sorted, de-duplicated `prefix:local` qnames — the predicates/classes used (e.g. `up:reviewed`, `bif:contains`). Max 60. A bare `up:` in a `PREFIX` declaration does **not** match. |
| `n_predicates` | integer | Total distinct qnames before the 60-item cap. |
| `flags` | object | Structural keywords **present** in the query, from: `filter`, `optional`, `union`, `values`, `service`, `limit`, `offset`, `order`, `group`, `minus`, `having`, plus `bif_contains`. Only present flags are included (absent ones are omitted, not set `false`). |
| `len` | integer | Character length of the original query. |

This is the signal MIE-improvement analysis needs (e.g. "reactome queries using
`bp:db` but not `xsd:string` return 0 rows") without storing the raw query.

## Example records

A successful SPARQL call:

The first example has `TOGOMCP_LOG_RAW_IP` on, so it carries `ip` /
`forwarded_for`; the second is the default configuration, where neither field
exists.

```json
{
  "ts": "2026-07-07T00:00:00.123456+00:00",
  "tool": "run_sparql",
  "args": {"database": "uniprot", "query": "PREFIX up: <...> SELECT ..."},
  "status": "ok",
  "elapsed_ms": 412.55,
  "output_bytes": 1840,
  "session_id": "…", "request_id": "…", "origin_request_id": null,
  "client_id": "…", "transport": "http",
  "ip_hash": "9f3a1c0b7e2d4a56",
  "ip": "203.0.113.7",
  "forwarded_for": "203.0.113.7, 10.0.2.100",
  "meta": {
    "server_version": "2.4.0",
    "usage_guide_version": "v6",
    "mie_bundle_version": "a1b2c3d4e5f6",
    "client": {"name": "claude-ai", "version": "1.0"}
  },
  "extra": {
    "endpoint_url": "https://rdfportal.org/sib/sparql",
    "query_sha256": "…",
    "query_shape": {
      "form": "select",
      "from": [],
      "predicates": ["up:Protein", "up:mnemonic", "up:reviewed"],
      "n_predicates": 3,
      "flags": {"limit": true},
      "len": 142
    },
    "sparql_status": "ok",
    "http_code": 200,
    "n_bytes": 1840,
    "n_rows": 3
  }
}
```

A non-SPARQL call that raised (no `extra`):

```json
{
  "ts": "2026-07-07T00:00:01.000000+00:00",
  "tool": "search_uniprot_entity",
  "args": {"query": "..."},
  "status": "error",
  "elapsed_ms": 88.10,
  "output_bytes": null,
  "session_id": "…", "request_id": "…", "origin_request_id": null,
  "client_id": "…", "transport": "http",
  "ip_hash": "9f3a1c0b7e2d4a56",
  "meta": {"server_version": "2.4.0", "usage_guide_version": "v6", "mie_bundle_version": "a1b2c3d4e5f6", "client": null},
  "error_class": "ToolError",
  "error_message": "Error calling tool 'search_uniprot_entity': …"
}
```

## Consuming the log

`stats.py` is the reference reader. It:

- discovers the active file plus rotated siblings (`log_paths`),
- tolerantly parses each line, silently skipping malformed ones (`iter_records`),
- buckets records by UTC month (`month_of`), attributes each to a database
  (`database_of`: explicit `database` arg → tool-name-implied DB → endpoint
  group), classifies SPARQL outcomes (`sparql_class`), and rolls everything into
  per-month, per-tool, and per-database aggregates plus two MIE feeds:
  `mie_candidates` (a per-database/month ranking of where the logs most suggest
  MIE work) and `mie_trap_candidates` (the *filtered* feed — distinct failures
  deduped by `query_sha256`, date-filtered against each MIE's revision date via
  `load_mie_dates`, with schema-probe surveys and 4xx grammar errors set aside so
  a surviving entry is genuinely worth a human's time).

Run it standalone (pass `--mie` to enable the date-filtered trap feed):

```bash
python -m togo_mcp.stats "$TOGOMCP_QUERY_LOG" \
  --endpoints togo_mcp/data/resources/endpoints.csv \
  --mie togo_mcp/data/mie
```

### Getting the raw file off a running server

`GET /stats/log` streams the raw JSONL — the active file plus every rotated
sibling, concatenated **oldest first** so the stream reads chronologically. It
serves exactly the files `compute_stats` aggregates, so a download is verifiably
the same input the dashboard's numbers came from. The `/stats` dashboard links
it at the top.

```bash
curl -u "$TOGOMCP_STATS_USER:$TOGOMCP_STATS_PASSWORD" \
  https://togomcp.rdfportal.org/stats/log -o togomcp-log.jsonl
```

Same HTTP Basic gate as `/stats`: **503** when `TOGOMCP_STATS_USER` /
`TOGOMCP_STATS_PASSWORD` are unset (never an unauthenticated fallback), **401**
without valid credentials, **404** when no log file exists. The response carries
`X-Log-Bytes` and `X-Log-Files`; no `Content-Length`, because rotation can change
the real length mid-stream.

Reach for this when a question outruns the dashboard. The aggregates are lossy
by construction, and the failures worth finding tend not to be the ones already
tabulated — release 2.2.0 came out of reading the raw log directly, where a 62%
zero-row rate on one tool and a single repeated dead-end query shape were plainly
visible while every pre-computed table showed them as unremarkable traffic.

## Stability notes

- New top-level or `extra` fields may be **added** over time; readers must
  ignore unknown fields.
- Optional fields may be absent; never assume presence beyond the "always"
  fields in the schema tables above.
- Treat every line as independent — do not rely on ordering within a file.
