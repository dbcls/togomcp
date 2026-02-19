# TogoMCP: MCP server for the RDF Portal databases
This MCP server executes SPARQL queries against various biological/biomedical RDF databases provided at the [RDF Portal](https://rdfportal.org/). 

Additional functionalities are also provided that interact with a few REST APIs at various sites.

## Remote MCP Server
You can use the remote TogoMCP server (no need for local installation). See https://togomcp.rdfportal.org/ for instructions.

## Installation
- Python (>= 3.11)
- [uv](https://docs.astral.sh/uv/) package manager

### Install uv (if not yet installed)
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
### Install TogoMCP server
```bash
# Clone the repository
git clone https://github.com/dbcls/togo-mcp.git
cd togo-mcp

# Install dependencies
uv sync

```

### Set NCBI API KEY
Part of TogoMCP tools require NCBI API keys.
[Obtain your NCBI API KEY](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/api/api-keys/) and set it as the `NCBI_API_KEY` environment variable.
```sh
export NCBI_API_KEY="your-key-here"
```

## Configuration
### Claude Desktop Configuration
Change the file paths as appropriate.

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `~\AppData\Roaming\Claude\claude_desktop_config.json`
```json
{
    "mcpServers": {
        "togomcp": {
            "command": "{path to uv}/uv",
            "args":[
                "--directory",
                "{path to togo-mcp}/togo-mcp",
                "run",
                "togo-mcp-local"
            ]
        }
    }
}
```
#### "Admin" mode
In the above setting, you can also use `togo-mcp-admin` instead of `togo-mcp-server`, which includes additional MCP tools for generating new MIE files.

