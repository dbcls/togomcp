# TogoMCP: MCP Server for the RDF Portal

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
git clone https://github.com/dbcls/togo-mcp.git
cd togo-mcp
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
                "/path/to/togo-mcp",
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

#### Admin Mode

Replace `togo-mcp-local` with `togo-mcp-admin` to also enable tools for generating new MIE (Machine-Interpretable Entity) files — useful for contributors adding new database support.

---

## Docker

A `Dockerfile` is provided for containerized deployment:

```bash
docker build -t togo-mcp .
docker run -e NCBI_API_KEY="your-key-here" -p 8000:8000 togo-mcp
```

---

## Available Databases & Tools

TogoMCP exposes tools for querying the following (via SPARQL or REST APIs):

| Category | Resources |
|---|---|
| Genomics / Sequences | UniProt, NCBI (Gene, PubMed, Taxonomy) |
| Chemistry | ChEMBL, PubChem, Rhea |
| Structure | PDB |
| Pathways | Reactome |
| Ontologies | MeSH, GO, ChEBI |
| General RDF | RDF Portal databases via SPARQL |

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
togo-mcp/
├── togo_mcp/               # Main Python package
│   ├── server.py           # MCP server entry point
│   ├── main.py             # Core logic and tool registration
│   ├── admin.py            # Admin-mode tools (MIE generation)
│   ├── api_tools.py        # REST API integrations (ChEMBL, PDB, Reactome, etc.)
│   ├── ncbi_tools.py       # NCBI E-utilities tools
│   ├── rdf_portal.py       # RDF Portal / SPARQL tools
│   └── togoid.py           # TogoID identifier conversion tools
├── mie/                    # Machine-Interpretable Entity (MIE) files (YAML)
│   ├── uniprot.yaml        # (one per supported database)
│   └── ...
├── sparql-examples/        # Example SPARQL queries per database
├── shex/                   # ShEx schemas for RDF validation
├── docs/                   # Developer documentation
│   ├── MIE_file_specs.md   # Spec for writing MIE files
│   └── ...
├── benchmark/              # Benchmarking scripts and results
├── scripts/                # Utility/maintenance scripts
├── resources/              # Static resources
├── Dockerfile              # Docker build configuration
├── pyproject.toml          # Python project metadata and entry points
└── uv.lock                 # Locked dependency versions (uv)
```

---

## Contributing

Contributions are welcome! To add support for a new database, see the `mie/` directory and the admin-mode tools for generating MIE files. Please open an issue or pull request on GitHub.

## License

This project is licensed under the [MIT License](LICENSE).
