# TogoMCP

FastMCP server exposing the [RDF Portal](https://rdfportal.org/) (SPARQL) plus selected REST APIs (NCBI E-utilities, UniProt, ChEMBL, PDB, PubChem, Reactome, Rhea, MeSH, TogoID) to AI assistants.

## Architecture

The server is assembled in [main.py](togo_mcp/main.py): a root `FastMCP` instance (`mcp`, defined in [server.py](togo_mcp/server.py)) mounts three sub-servers as prefixes:

- `togoid_mcp` from [togoid.py](togo_mcp/togoid.py) — mounted as `togoid`
- `ncbi_mcp` from [ncbi_tools.py](togo_mcp/ncbi_tools.py) — mounted as `ncbi`
- `togovar_mcp` from [togovar.py](togo_mcp/togovar.py) — mounted as `togovar`

A REST wrapper becomes a **mounted sub-server** (not a flat `api_tools.py` `search_*` tool) when the external API is a cohesive multi-endpoint surface with *no* SPARQL counterpart in RDF Portal — the flat wrappers are keyword-search front doors to a SPARQL database (their error hint points back to `run_sparql`), so a DB without a SPARQL endpoint doesn't belong there. TogoVar (human genome variation: gnomAD/ToMMo/JGA/BBJ frequencies, ClinVar+MGeND significance) fits the sub-server shape, like TogoID and NCBI.

Tools registered directly on the root `mcp` live in [rdf_portal.py](togo_mcp/rdf_portal.py) (SPARQL, MIE files, endpoint resolution) and [api_tools.py](togo_mcp/api_tools.py) (REST search wrappers).

Entry points (from [pyproject.toml](pyproject.toml)):
- `togo-mcp-server` — HTTP transport on `0.0.0.0:8000`
- `togo-mcp-local` — stdio transport (Claude Desktop)

## Data layout

Bundled under [togo_mcp/data/](togo_mcp/data/) and shipped in the wheel via `package-data`:

- `mie/*.yaml` — one MIE (Metadata-Interoperability-Exchange) file per supported RDF database
- `resources/endpoints.csv` — SPARQL endpoint registry consumed by `load_sparql_endpoints`
- `resources/togomcp_usage_guide*.md` — static guidance served as a resource
- `docs/` — developer docs (MIE spec, examples)

## Parameter conventions

These conventions were deliberately normalized across tools; preserve them when adding new tools:

- **`database`** is the canonical parameter name for RDF-database selection. `dbname` is deprecated — do not add it to new tools. Only `get_MIE_file` in `rdf_portal.py` still accepts `dbname`/`db` as legacy aliases (its `database` has a default, so alias-only calls resolve). `run_sparql`/`get_graph_list` dropped these aliases: `database` is schema-`required` there, so alias-only calls were already rejected by validation and the fallback was dead code.
- **`database` vs `endpoint_name`**: `database` takes a single RDF database key (e.g. `uniprot`, `chembl`); `endpoint_name` takes an endpoint group (e.g. `ebi`, `sib`). Mixing them returns a deterministic error telling the caller not to retry — do not add fallback behavior.
- **`database` is required on `run_sparql`/`get_graph_list`.** Its params are keyword-only (`*,`) so the schema `required` array carries `database` — many LLMs omit fields that aren't marked required and only fail at runtime, so this is deliberate; prefer a hard `required` over a `oneOf`/`anyOf` soft constraint. Endpoint-selection is still overridable: pass a member `database` **plus** `endpoint_name`/`endpoint_url` for cross-DB/federated queries (priority `endpoint_url > endpoint_name > database`). A consequence: endpoint-only calls are rejected by schema validation — always supply `database`. (These two tools no longer define `dbname`/`db` at all, so passing either now errors as an unexpected argument rather than being silently ignored.)
- **`ids` accepts `str | list[str]`** across NCBI and TogoID tools. Normalize with `_normalize_ids` (ncbi_tools.py) or `_ids_to_csv` (togoid.py).
- **Search-tool query aliases**: all non-NCBI `search_*` tools accept `query`/`search`/`term`/`keyword`/`keywords`/`search_term`/`name`. Resolve via `_resolve_query_alias` in [api_tools.py](togo_mcp/api_tools.py). NCBI `esearch` uses `db`/`term` aliases specifically.

## Return-shape and error conventions

Two intentional, *different* error conventions coexist — preserve each module's:

- **REST-wrapper tools** in [api_tools.py](togo_mcp/api_tools.py) (`search_uniprot/pdb/mesh/reactome/rhea_entity`, ChEMBL, PubChem) and the catalog tools in [rdf_portal.py](togo_mcp/rdf_portal.py) (`list_databases`, `find_databases`): **raise `ValueError` for bad parameters** (caught early, tells the caller not to retry) but **degrade gracefully on upstream/HTTP failure** by returning a payload carrying an `error` key plus a "fall back to SPARQL" hint. Never raise on a transient HTTP error here.
- **TogoID tools** in [togoid.py](togo_mcp/togoid.py): **raise on HTTP error** via `raise_for_status_with_body` (with a `client_error_hint`). This is the module's consistent convention; FastMCP surfaces the message to the caller. Don't convert only some togoid tools to the return-JSON style — keep the module uniform.
- **TogoVar tools** in [togovar.py](togo_mcp/togovar.py): same convention as TogoID — **raise `ValueError` on bad params AND on HTTP error** (via `raise_for_status_with_body`); never return an `{"error": ...}` payload. No "fall back to SPARQL" hint (TogoVar has no RDF Portal endpoint). Keep the module uniform. The variant-query DSL is assembled by the pure helper `_build_variant_query` (unit-tested without HTTP); the `search_variant` tool exposes flat filters, not raw nested JSON. Note two live-API quirks the wrapper handles: the client pins `Accept: application/json` (else the API 501s), and a frequency `dataset` is an object `{"name": ...}` (a bare string 500s). The list endpoint does not echo a tgv ID — `rs`/`clinvar` cross-links come from each row's `external_link`.

List-style result tools return a **JSON string of a bare array** (not a Python `list`): empty and non-empty then share one wire shape. Returning a bare `list` makes FastMCP double-represent it (text array + wrapped `{"result": ...}`), so empty vs non-empty diverge for clients. `dict` returns (ChEMBL, `search_reactome_entity`, `get_sparql_endpoints`) and NCBI `list[TextContent]` returns are exempt — they aren't wrapped. `search_reactome_entity` uses the ChEMBL envelope `{total_count, has_more, results}` on success and `{"error": ...}` on failure (it validates+normalizes `species`/`types` case-insensitively against vendored vocabularies and raises on an unknown value — the server-side filter is case-sensitive and silently ignores a mis-cased value; `limit` is a true overall cap, not per-type; `summation` is opt-in).

## Testing

```bash
uv run pytest              # all tests
uv run pytest tests/test_server.py -v
```

`tests/test_api_tools.py` has a pre-existing failure caused by FastMCP wrapping tool functions as `FunctionTool` objects (not directly callable from tests). Don't block on it unless explicitly asked.

## Running locally

```bash
export NCBI_API_KEY="..."   # required for NCBI tools (has a default fallback but rate-limited)
uv sync
uv run togo-mcp-local        # stdio
uv run togo-mcp-server       # HTTP :8000
```

## Editing MIE files

MIE YAMLs in `togo_mcp/data/mie/` drive the `get_MIE_file` tool — the primary schema/example resource LLMs read before writing SPARQL. The format spec is [MIE_file_specs.md](togo_mcp/data/docs/MIE_file_specs.md). When adding a database, also add an entry to `resources/endpoints.csv`.
