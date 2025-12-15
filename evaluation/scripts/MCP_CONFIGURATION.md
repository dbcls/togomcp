# MCP Configuration Guide for Agent SDK

## Overview

The Claude Agent SDK supports MCP (Model Context Protocol) servers through the `mcp_servers` parameter in `ClaudeAgentOptions`. This guide covers all configuration options.

## Configuration Locations

### 1. Global Config File (`config.json`)

Default MCP servers for all questions:

```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "http",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

### 2. Per-Question Override (`questions.json`)

Override for specific questions:

```json
{
  "id": 1,
  "question": "Your question",
  "mcp_servers": {
    "custom-server": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

## MCP Server Types

### Type 1: HTTP (Streamable-HTTP)

Remote HTTP servers using HTTP transport.

**Basic:**
```json
{
  "togomcp": {
    "type": "http",
    "url": "https://togomcp.rdfportal.org/mcp"
  }
}
```

**With authentication:**
```json
{
  "togomcp": {
    "type": "http",
    "url": "https://togomcp.rdfportal.org/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}",
      "X-API-Key": "${API_KEY}"
    }
  }
}
```

**Environment variables:**
Use `${VAR_NAME}` syntax in headers. Set environment variables before running:
```bash
export API_TOKEN="your-token"
export API_KEY="your-key"
python automated_test_runner.py questions.json
```

### Type 2: stdio (Standard Input/Output)

Local process servers.

**Basic:**
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem"],
    "env": {
      "ALLOWED_PATHS": "/path/to/data"
    }
  }
}
```

**With custom environment:**
```json
{
  "custom-tool": {
    "command": "python",
    "args": ["./my_mcp_server.py"],
    "env": {
      "DEBUG": "true",
      "DATA_PATH": "/data",
      "API_KEY": "${MY_API_KEY}"
    }
  }
}
```

### Type 3: SDK (In-process)

Python MCP servers running in the same process (not applicable for this test runner, but shown for completeness).

## Multiple MCP Servers

You can configure multiple servers simultaneously:

```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "http",
      "url": "https://togomcp.rdfportal.org/mcp"
    },
    "pubmed": {
      "type": "http",
      "url": "https://pubmed.mcp.claude.com/mcp"
    },
    "local-files": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_PATHS": "/project/data"
      }
    }
  }
}
```

Claude can use tools from all configured servers.

## Available Public MCP Servers

### TogoMCP (Biological Databases)
```json
{
  "togomcp": {
    "type": "http",
    "url": "https://togomcp.rdfportal.org/mcp"
  }
}
```

**Provides access to:**
- UniProt (proteins)
- PubChem (compounds)
- ChEMBL (drug discovery)
- Reactome (pathways)
- Rhea (reactions)
- MeSH (medical terms)
- GO (gene ontology)
- PDB (protein structures)
- And more...

### PubMed
```json
{
  "pubmed": {
    "type": "http",
    "url": "https://pubmed.mcp.claude.com/mcp"
  }
}
```

**Provides access to:**
- PubMed search
- Article metadata
- Full-text retrieval

## Configuration Patterns

### Pattern 1: Database-Specific Testing

Test each database separately:

**config_uniprot.json:**
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

Run:
```bash
python automated_test_runner.py uniprot_questions.json -c config_uniprot.json
```

### Pattern 2: Cross-Database Integration

Test database integration:

**config_integration.json:**
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    },
    "pubmed": {
      "type": "sse",
      "url": "https://pubmed.mcp.claude.com/mcp"
    }
  }
}
```

Questions can use tools from both servers.

### Pattern 3: Per-Question Selection

Different servers for different questions:

```json
[
  {
    "id": 1,
    "question": "What is the UniProt ID for human BRCA1?",
    "mcp_servers": {
      "togomcp": {
        "type": "sse",
        "url": "https://togomcp.rdfportal.org/mcp"
      }
    }
  },
  {
    "id": 2,
    "question": "Find papers about BRCA1",
    "mcp_servers": {
      "pubmed": {
        "type": "sse",
        "url": "https://pubmed.mcp.claude.com/mcp"
      }
    }
  }
]
```

### Pattern 4: No MCP Servers

Test without any MCP (baseline only):

**config_no_mcp.json:**
```json
{
  "mcp_servers": {}
}
```

Both baseline and "TogoMCP" tests will have no tools (useful for testing the baseline comparison).

## Advanced Configuration

### Timeout Configuration

```json
{
  "timeout": 120,
  "mcp_servers": {
    "slow-server": {
      "type": "sse",
      "url": "https://slow.example.com/mcp"
    }
  }
}
```

### Retry Configuration

```json
{
  "retry_attempts": 5,
  "retry_delay": 3,
  "mcp_servers": {
    "unreliable-server": {
      "type": "sse",
      "url": "https://unreliable.example.com/mcp"
    }
  }
}
```

### Custom System Prompts

```json
{
  "togomcp_system_prompt": "You are a expert bioinformatician. Use TogoMCP to access biological databases and provide precise, verified information.",
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

## Environment Variables

Use environment variables for sensitive data:

**config.json:**
```json
{
  "mcp_servers": {
    "authenticated-server": {
      "type": "sse",
      "url": "${SERVER_URL}",
      "headers": {
        "Authorization": "Bearer ${AUTH_TOKEN}",
        "X-API-Key": "${API_KEY}"
      }
    }
  }
}
```

**Run:**
```bash
export SERVER_URL="https://secure.example.com/mcp"
export AUTH_TOKEN="your-token"
export API_KEY="your-key"
python automated_test_runner.py questions.json
```

## Testing MCP Configuration

### Quick Test

Create a test file with one question:

**test.json:**
```json
[
  {
    "id": 1,
    "question": "What is the UniProt ID for human TP53?"
  }
]
```

Run:
```bash
python automated_test_runner.py test.json -c config.json
```

Check output:
- Look for `tools_used` column in CSV
- Should see tool names like `TogoMCP:search_uniprot_entity`

### Verify Connection

Check if MCP server is accessible:

```bash
# For SSE servers
curl -v https://togomcp.rdfportal.org/mcp

# Should return HTTP 200 and SSE headers
```

## Troubleshooting

### Problem: No tools used

**Check:**
1. `mcp_servers` is not empty in config
2. Server URL is correct
3. Question actually needs database access
4. System prompt encourages tool use

**Debug:**
```bash
# Check CSV output
grep "tools_used" evaluation_results.csv
# Should show tool names, not be empty
```

### Problem: Connection timeout

**Solutions:**
1. Increase timeout in config:
   ```json
   {"timeout": 120}
   ```
2. Check server status:
   ```bash
   curl https://togomcp.rdfportal.org/mcp
   ```
3. Check network/firewall

### Problem: Authentication failed

**Check:**
1. Environment variables are set:
   ```bash
   echo $API_TOKEN
   ```
2. Token is valid and not expired
3. Headers are correctly formatted in config

### Problem: Wrong server used

**Solution:**
Use per-question override to force specific server:
```json
{
  "question": "Your question",
  "mcp_servers": {
    "specific-server": {
      "type": "sse",
      "url": "https://specific.example.com/mcp"
    }
  }
}
```

## Best Practices

### 1. Start Simple

Begin with one MCP server:
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

### 2. Test Incrementally

1. Test with 1 question
2. Verify tools are used
3. Add more questions
4. Add more servers if needed

### 3. Version Control Configs

Track configurations in git:
```
config_togomcp_only.json
config_pubmed_only.json
config_all_servers.json
```

### 4. Document Server Choices

In questions file:
```json
{
  "question": "Your question",
  "mcp_servers": {...},
  "notes": "Using TogoMCP for UniProt access"
}
```

### 5. Separate Concerns

Create different config files for different test scenarios:
- `config_precision.json` - For precision tests
- `config_integration.json` - For cross-database tests
- `config_currency.json` - For testing recent data

## Examples

### Example 1: TogoMCP Only

**config.json:**
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

### Example 2: Multiple Public Servers

**config.json:**
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    },
    "pubmed": {
      "type": "sse",
      "url": "https://pubmed.mcp.claude.com/mcp"
    }
  }
}
```

### Example 3: Local + Remote

**config.json:**
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    },
    "local-data": {
      "command": "python",
      "args": ["./local_mcp_server.py"],
      "env": {
        "DATA_DIR": "/project/data"
      }
    }
  }
}
```

### Example 4: Authenticated Server

**config.json:**
```json
{
  "mcp_servers": {
    "private-db": {
      "type": "sse",
      "url": "https://private.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${PRIVATE_TOKEN}",
        "X-Organization": "my-org"
      }
    }
  }
}
```

**Run:**
```bash
export PRIVATE_TOKEN="your-secret-token"
python automated_test_runner.py questions.json
```

## Summary

**Key Points:**
- MCP servers configured via `mcp_servers` in config or per-question
- Three types: SSE (remote), stdio (local), SDK (in-process)
- Can use multiple servers simultaneously
- Environment variables for sensitive data
- Per-question override available

**For TogoMCP evaluation:**
```json
{
  "mcp_servers": {
    "togomcp": {
      "type": "sse",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

This is already in the default `config.json` - you're ready to go!

---

**Last Updated**: 2025-12-15  
**Agent SDK Version**: 0.1.0+
