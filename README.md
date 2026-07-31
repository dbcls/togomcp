# TogoMCP: An MCP Server for Life-Science Databases

![Python >=3.11](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that gives AI assistants (Claude, etc.) access to biological and biomedical RDF databases via SPARQL at the [RDF Portal](https://rdfportal.org/), as well as selected REST APIs (NCBI E-utilities, UniProt, ChEMBL, PDB, Reactome, Rhea, MeSH, and more).

## Quick Start: Remote Server (No Installation)

You can use the hosted TogoMCP server directly — no local setup needed.  
See **https://togomcp.rdfportal.org/** for connection instructions.

---

## Local Installation

### Prerequisites
- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Install `uv`
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and install
```bash
git clone https://github.com/dbcls/togomcp.git
cd togomcp
uv sync
```

### 3. Set NCBI API Key (required for NCBI tools)
[Obtain your NCBI API key](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/) and export it:
```bash
export NCBI_API_KEY="your-key-here"
```

---

## Configuration

### Claude Desktop

Edit your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `~\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
    "mcpServers": {
        "togomcp": {
            "command": "/path/to/uv",
            "args": [
                "--directory",
                "/path/to/togomcp",
                "run",
                "togo-mcp-local"
            ],
            "env": {
                "NCBI_API_KEY": "your-key-here"
            }
        }
    }
}
```

> **Tip**: Run `which uv` (macOS/Linux) or `where uv` (Windows) to find the full path to `uv`.

> **Note on KEGG**: TogoMCP does **not** enable KEGG by default. The `kegg_*` tools
> require `TOGOMCP_ENABLE_KEGG=1` **and** the local `stdio` server, because the KEGG API
> is licensed to **academic users at academic institutions**. If that is not you, simply
> leave it unset and everything else works normally. See
> [KEGG (opt-in, local `stdio` only)](#kegg-opt-in-local-stdio-only).

---

## Docker

A `Dockerfile` is provided for containerized deployment.

### Recommended: `docker compose`

`compose.yaml` defines two services — `togomcp-main` (port 8000) and `togomcp-test` (port 8001) — so you can run production and staging endpoints side by side from the same image.

```bash
cp .env.example .env                                # then fill in NCBI_API_KEY
docker build -t localhost/togo-mcp:latest .         # build main image (tag in .env)
docker compose up -d togomcp-main                   # start main endpoint
```

Common operations:

```bash
docker compose logs -f togomcp-main                 # tail logs
docker compose down                                 # stop and remove all services
docker compose down togomcp-test                    # stop and remove just one
docker compose up -d togomcp-test                   # after rebuilding, recreates with new image
```

Override image tags and host ports via `.env` — see `.env.example` for the full list. Use `docker compose up -d --force-recreate <svc>` if compose doesn't pick up a rebuilt image, and `docker image prune -f` to clean up dangling layers.

#### Behind a reverse proxy

Two env vars matter if you put TogoMCP behind nginx/Caddy/Traefik. Both fail in ways that are easy to misdiagnose:

- **`TOGOMCP_ALLOWED_HOSTS`** — FastMCP validates the `Host` header (DNS-rebinding protection) and answers **421** for any host not on the allow-list. The default list is localhost plus the public DBCLS vhosts, so your own hostname must be added or *every* proxied request is rejected.
- **`TOGOMCP_FORWARDED_ALLOW_IPS`** — which peer addresses may set `X-Forwarded-Proto`/`-For`. uvicorn parses those headers but trusts only `127.0.0.1` unless told otherwise, and a container reached via a published port never arrives as loopback. Left wrong, the header is **silently dropped** (not rejected): the app then believes it is serving plain HTTP and emits redirects that downgrade `https://` to `http://`. The default covers the usual container-runtime ranges; set this only if your proxy sits elsewhere.

Your proxy must also send `X-Forwarded-Proto` — nginx does not by default (`proxy_set_header X-Forwarded-Proto $scheme;`), while Caddy and Traefik do. Both halves are required; neither works alone.

### Simple: `docker run`

For a single container without compose:

```bash
docker build -t togo-mcp .
docker run -e NCBI_API_KEY="your-key-here" -p 8000:8000 togo-mcp
```

---

## Tool-Call Logging (Optional)

TogoMCP can record every MCP tool call as one JSON line per call (timestamp,
tool name, arguments, status, elapsed_ms, session/request/client IDs, transport,
client IP). SPARQL calls are enriched with endpoint URL, HTTP code, row/byte
counts, and a SHA-256 of the query. Note the client IP is the *peer* address as
the app sees it — behind a proxy or container that is the proxy/gateway, the same
value for every caller, unless `TOGOMCP_FORWARDED_ALLOW_IPS` lets uvicorn trust
`X-Forwarded-For`. Useful for benchmarking, MIE iteration,
and reconstructing multi-tool sequences.

**On/off is a single env var**: `TOGOMCP_QUERY_LOG`. Unset/empty = disabled
(zero-overhead default). Set to a writable file path to enable.
Output uses `RotatingFileHandler` (50 MB × 10, ~500 MB cap).

### Docker

`compose.yaml` bind-mounts `./logs` (and `./logs-test`) on the host to
`/var/log/togomcp` inside each container and passes through `TOGOMCP_QUERY_LOG`
/ `TOGOMCP_QUERY_LOG_TEST` from `.env`. Opt in:

```bash
echo 'TOGOMCP_QUERY_LOG=/var/log/togomcp/togomcp.jsonl' >> .env
mkdir -p logs
docker compose up -d togomcp-main
tail -f logs/togomcp.jsonl
```

The path in the env var is the **container-side** path; the bind mount makes
the same file visible at `./logs/togomcp.jsonl` on your host. Leaving the var
unset keeps logging off — no compose changes needed.

### Claude Desktop (local stdio)

Add `TOGOMCP_QUERY_LOG` to the `env` block alongside `NCBI_API_KEY`. Use an
absolute path (the spawned process's cwd is unpredictable) and ensure the
parent directory exists:

```json
"env": {
    "NCBI_API_KEY": "your-key-here",
    "TOGOMCP_QUERY_LOG": "/Users/you/togomcp-logs/togomcp.jsonl"
}
```

Then `mkdir -p ~/togomcp-logs` once and fully restart Claude Desktop.

---

## Available Databases & Tools

TogoMCP exposes tools for querying the following (via SPARQL or REST APIs):

| Category | Resources |
|---|---|
| Proteins / Proteomics | UniProt, PDB, jPOST |
| Genes / Genomics | NCBI Gene, Ensembl, HGNC, OMA, Bgee, HCO, MCO, DDBJ, MoG+, TogoVar, GWAS Catalog |
| Chemistry | ChEMBL, PubChem, ChEBI, Rhea, BRENDA, MassBank |
| Pathways | Reactome |
| Disease / Clinical | ClinVar, MedGen, MONDO, NANDO |
| Literature | PubMed, PubTator |
| Microbiology | BacDive, MediaDive, AMR Portal, NBRC |
| Glycomics | GlyCosmos |
| Ontologies / Vocabulary | MeSH, GO, Ontology Graphs (HP, UBERON, CL, SO, ECO, EFO, PRO, FMA, …) |
| Taxonomy | NCBI Taxonomy |
| Materials Science | SuperCon |

### KEGG (opt-in, local `stdio` only)

**KEGG is off by default. You do not need it, and TogoMCP is fully functional
without it** — this section only matters if you are eligible and want it.

A `kegg` tool group (`kegg_find`, `kegg_get_entry`, `kegg_pathway_graph`,
`kegg_pathway_neighborhood`, `kegg_pathway_paths`, `kegg_pathway_cycles`,
`kegg_link`, `kegg_conv`) is mounted only when **both** conditions hold:

1. you run the local `stdio` entry point `togo-mcp-local`, **and**
2. you set `TOGOMCP_ENABLE_KEGG=1`.

Why two gates, for two different reasons:

- **The transport gate is structural and not configurable.** The
  [KEGG API](https://www.kegg.jp/kegg/rest/) is provided "for academic use by academic
  users belonging to academic institutions", and offering a *service* built on KEGG
  additionally requires an academic service-provider license (see
  [KEGG's terms](https://www.kegg.jp/kegg/legal.html)). A public host cannot verify a
  caller's affiliation, so the hosted server at togomcp.rdfportal.org — and any HTTP
  deployment — never reaches `rest.kegg.jp`. **No environment variable can change
  this**; `TOGOMCP_ENABLE_KEGG` has no effect on the HTTP path at all.
- **The opt-in exists because eligibility is yours to assert.** Under `stdio` *you* are
  the caller, but only you know whether your institution's access covers you. Mounting
  KEGG by default would put an API call you may not be entitled to make on the path of
  least resistance — an AI assistant will use any tool it can see. Leaving the variable
  unset is the correct configuration for a non-academic user, and nothing else is
  affected.

Enable it in your Claude Desktop config:

```json
"env": {
    "NCBI_API_KEY": "your-key-here",
    "TOGOMCP_ENABLE_KEGG": "1"
}
```

Calls are capped at **3 requests per second** (TogoMCP enforces this process-wide, and
never retries an HTTP 403/429). KEGG is not part of RDF Portal: it has no SPARQL
endpoint, so `database="kegg"` is invalid in `run_sparql`. Use `kegg_conv` to translate
KEGG identifiers to UniProt, NCBI Gene/Protein, ChEBI or PubChem before querying any RDF
database with them.

---

## Example Prompts

Once connected, you can ask your AI assistant things like:

- *"Find all human proteins associated with Alzheimer's disease in UniProt."*
- *"Run a SPARQL query on the ChEMBL database to find compounds targeting EGFR."*
- *"Search PubMed for recent papers on CRISPR base editing."*
- *"What pathways involve the TP53 gene in Reactome?"*

---

## Directory Structure

```
togomcp/
├── togo_mcp/               # Main Python package
│   ├── server.py           # Root FastMCP instance + tool-call logging middleware
│   ├── main.py             # Assembles the server, mounts sub-servers, entry points
│   ├── rdf_portal.py       # RDF Portal / SPARQL, MIE, and endpoint tools
│   ├── api_tools.py        # REST search wrappers (UniProt, PDB, Reactome, MeSH, PubChem, etc.)
│   ├── chembl.py           # ChEMBL REST search wrappers
│   ├── ncbi_tools.py       # NCBI E-utilities sub-server
│   ├── togoid.py           # TogoID identifier-conversion sub-server
│   ├── togovar.py          # TogoVar human-variation sub-server
│   ├── kegg.py             # KEGG sub-server — mounted by togo-mcp-local ONLY (licence, see above)
│   ├── kgml.py             # KGML -> signed pathway graph (pure; no network, no FastMCP)
│   ├── stats.py            # Tool-call usage-log analysis
│   └── data/               # Bundled data files (included in wheel)
│       ├── mie/            # MIE files (YAML, one per database)
│       ├── docs/           # Developer documentation (MIE spec, examples)
│       └── resources/      # Static resources (endpoints.csv, usage guide, etc.)
├── benchmark/              # Benchmark question set, scripts, and results
├── scripts/                # Utility/maintenance scripts (deploy, Docker, MIE keywords)
├── tests/                  # Pytest test suite
├── Dockerfile              # Docker build configuration
├── compose.yaml            # Docker Compose (main + test services)
├── pyproject.toml          # Python project metadata and entry points
└── uv.lock                 # Locked dependency versions (uv)
```

---

## Contributing

Contributions are welcome!

**Adding a database**: five places, not two. Only the first two affect what the server *validates*; the rest are documentation surfaces that drift silently, and the tests are what catch them.

1. `togo_mcp/data/resources/endpoints.csv` — the registry row (this alone decides valid `database=` values).
2. `togo_mcp/data/mie/<db>.yaml` — the MIE file (see the MIE spec in `togo_mcp/data/docs/`).
3. `uv run python scripts/generate_usage_guide_catalog.py` — regenerates the Usage Guide's database catalog. Guarded by `tests/test_catalog_in_sync.py`.
4. `togo_mcp/data/resources/usage_guide_v6/02_budgets_and_discovery.md` — a **hand-written** copy of the registry that no generator touches. Bump the per-endpoint count *and* add the key. Guarded by `TestUsageGuideEndpointTable` in `tests/test_server.py`.
5. `togo_mcp/data/docs/togomcp-intro.html` — add a card to the database grid (not generated).

Note that a database *removal* really is just step 1: nothing validates against the other four.

**Adding a tool**: pass `annotations=READ_ONLY_TOOL` to the `@mcp.tool` decorator. Every TogoMCP tool is read-only, and MCP's default for an *unannotated* tool is the unsafe one — clients such as ChatGPT treat a tool with no `readOnlyHint` as a write action, which means a confirmation prompt on every call. A test asserts this, so omitting it fails the build.

Please open an issue or pull request on GitHub.

## Reference

Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

## License

This project is licensed under the [MIT License](LICENSE).

The MIT licence covers **this code only**, not the data or the third-party APIs it
reaches — each carries its own terms, and you are the caller. Most RDF Portal
databases are open, but note in particular that the **KEGG API** (`kegg_*` tools,
opt-in and local `stdio` only) is licensed to academic users at academic institutions
and requires a separate academic service-provider licence to redistribute as a
service — which is why it is off by default and the hosted server does not expose it at
all. See [KEGG (opt-in, local `stdio` only)](#kegg-opt-in-local-stdio-only).
