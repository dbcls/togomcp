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
counts, and a SHA-256 of the query. Useful for benchmarking, MIE iteration,
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
| Genes / Genomics | NCBI Gene, Ensembl, HGNC, OMA, Bgee, HCO, MCO, DDBJ, MoG+, TogoVar |
| Chemistry | ChEMBL, PubChem, ChEBI, Rhea, BRENDA, MassBank |
| Pathways | Reactome |
| Disease / Clinical | ClinVar, MedGen, MONDO, NANDO |
| Literature | PubMed, PubTator |
| Microbiology | BacDive, MediaDive, AMR Portal, NBRC |
| Glycomics | GlyCosmos |
| Ontologies / Vocabulary | MeSH, GO, Ontology Graphs (HP, UBERON, CL, SO, ECO, EFO, PRO, FMA, …) |
| Taxonomy | NCBI Taxonomy |
| Materials Science | SuperCon |

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
│   ├── api_tools.py        # REST search wrappers (UniProt, PDB, ChEMBL, Reactome, etc.)
│   ├── ncbi_tools.py       # NCBI E-utilities sub-server
│   ├── togoid.py           # TogoID identifier-conversion sub-server
│   ├── togovar.py          # TogoVar human-variation sub-server
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

Contributions are welcome! To add support for a new database, add an MIE file under `togo_mcp/data/mie/` and a corresponding row in `togo_mcp/data/resources/endpoints.csv` (see the MIE spec in `togo_mcp/data/docs/`). Please open an issue or pull request on GitHub.

## Reference

Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

## License

This project is licensed under the [MIT License](LICENSE).
