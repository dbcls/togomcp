# TogoMCP: MCP server for the RDF Portal databases
This MCP server executes SPARQL queries against various biological/biomedical RDF databases provided at the [RDF Portal](https://rdfportal.org/). 

Additional functionalities are also provided that interact with a few REST APIs at various sites.

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
### Install RDFPortal-MCP server
```bash
# Clone the repository
git clone https://github.com/arkinjo/togo-mcp.git
cd togo-mcp

# Install dependencies
uv sync

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
                "togo-mcp-server"
            ]
        }
    }
}
```
#### "Admin" mode
In the above setting, you can also use `togo-mcp-admin` instead of `togo-mcp-server`, which includes additional MCP tools for generating new MIE files.

