# TogoMCP Automated Evaluation - Agent SDK Version

This directory contains the **corrected** automated test runner that uses the **Claude Agent SDK** with full MCP support.

## Important Note

This is the **correct** version that actually works with MCP servers. The previous version in `/evaluation/scripts/` used the wrong SDK and **cannot** use MCP servers.

## What's Different?

| Feature | Old Version (`/scripts`) | New Version (here) |
|---------|-------------------------|-------------------|
| SDK Used | `anthropic` | `claude-agent-sdk` |
| MCP Support | ❌ No | ✅ Yes |
| Status | Broken for MCP | Works correctly |

## Quick Start

### 1. Installation

```bash
cd /Users/arkinjo/work/GitHub/togo-mcp/evaluation/agent_scripts

# Install dependencies
pip install -r requirements.txt

# Or install manually
pip install claude-agent-sdk anthropic
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Run Example

```bash
# Run with example questions
python automated_test_runner.py example_questions.json

# With custom config
python automated_test_runner.py example_questions.json -c config.json

# Custom output path
python automated_test_runner.py example_questions.json -o my_results.csv
```

## Files in This Directory

### Core Files

1. **`automated_test_runner.py`** - Main evaluation script (using Agent SDK)
2. **`config.json`** - Configuration with MCP server settings
3. **`requirements.txt`** - Python dependencies
4. **`example_questions.json`** - 10 sample questions

### Documentation

5. **`README.md`** - This file
6. **`MCP_CONFIGURATION.md`** - How to configure MCP servers
7. **`USAGE_GUIDE.md`** - Detailed usage instructions

## How It Works

### Two-Phase Testing

The script runs each question twice:

#### Phase 1: Baseline (No Tools)
- Uses regular `anthropic` SDK
- System prompt: "Answer using only your training knowledge..."
- **No MCP servers, no tools**
- Captures: answer text, timing, token usage

#### Phase 2: TogoMCP (With MCP)
- Uses `claude-agent-sdk`
- System prompt: "You have access to biological databases..."
- **MCP servers enabled** (TogoMCP by default)
- Captures: answer text, timing, tools used, tool details

### Results

Output CSV contains:
- Both baseline and TogoMCP answers
- Tool usage details
- Response times
- Token usage
- Success/failure status

## Configuration

### Basic Configuration

Edit `config.json`:

```json
{
  "model": "claude-sonnet-4-20250514",
  "mcp_servers": {
    "togomcp": {
      "type": "http",
      "url": "https://togomcp.rdfportal.org/mcp"
    }
  }
}
```

### MCP Server Types

#### 1. Remote HTTP
```json
{
  "togomcp": {
    "type": "http",
    "url": "https://togomcp.rdfportal.org/mcp",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

#### 2. stdio - Local Process
```json
{
  "local-mcp": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem"],
    "env": {
      "ALLOWED_PATHS": "/path/to/data"
    }
  }
}
```

#### 3. Multiple Servers
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
    }
  }
}
```

### Per-Question MCP Configuration

You can override MCP servers for specific questions in `questions.json`:

```json
[
  {
    "id": 1,
    "question": "What is the UniProt ID for human BRCA1?",
    "mcp_servers": {
      "togomcp": {
        "type": "http",
        "url": "https://togomcp.rdfportal.org/mcp"
      }
    }
  },
  {
    "id": 2,
    "question": "Find papers about BRCA1",
    "mcp_servers": {
      "pubmed": {
        "type": "http",
        "url": "https://pubmed.mcp.claude.com/mcp"
      }
    }
  }
]
```

## Usage Examples

### Basic Evaluation

```bash
# Run all questions
python automated_test_runner.py example_questions.json

# Results saved to: evaluation_results.csv
```

### Custom Configuration

```bash
# Use different MCP server
python automated_test_runner.py questions.json -c my_config.json
```

### Custom Output

```bash
# JSON output instead of CSV
python automated_test_runner.py questions.json --format json -o results.json
```

### Full Example

```bash
# Complete evaluation with all options
python automated_test_runner.py \
  my_questions.json \
  -c my_config.json \
  -o detailed_results.csv \
  --format csv
```

## Output Format

The CSV output includes these columns:

| Column | Description |
|--------|-------------|
| `question_id` | Question identifier |
| `date` | Evaluation date |
| `category` | Question category |
| `question_text` | The question asked |
| `baseline_success` | Whether baseline succeeded |
| `baseline_text` | Baseline answer |
| `baseline_time` | Baseline response time (seconds) |
| `baseline_input_tokens` | Tokens used (input) |
| `baseline_output_tokens` | Tokens used (output) |
| `togomcp_success` | Whether TogoMCP succeeded |
| `togomcp_text` | TogoMCP answer |
| `togomcp_time` | TogoMCP response time (seconds) |
| `tools_used` | Comma-separated tool names |
| `tool_details` | JSON with full tool details |
| `expected_answer` | Expected answer (from questions file) |
| `notes` | Additional notes |

## Analysis

After running evaluation, you can analyze results using the analyzer from the scripts directory:

```bash
# Copy results analyzer
cp ../scripts/results_analyzer.py .

# Analyze results
python results_analyzer.py evaluation_results.csv

# Verbose mode
python results_analyzer.py evaluation_results.csv -v
```

## Question File Format

Create questions in JSON format:

```json
[
  {
    "id": 1,
    "category": "Precision",
    "question": "What is the UniProt ID for human BRCA1?",
    "expected_answer": "P38398",
    "notes": "Test basic UniProt ID lookup"
  }
]
```

### Required Fields
- `question`: The question text

### Optional Fields
- `id`: Question identifier (defaults to index)
- `category`: Precision|Completeness|Integration|Currency|Specificity|Structured Query
- `expected_answer`: What you expect the answer to be
- `notes`: Additional context
- `mcp_servers`: Override default MCP configuration

## Common Issues

### Error: "claude-agent-sdk not found"

**Solution:**
```bash
pip install claude-agent-sdk
```

### Error: "ANTHROPIC_API_KEY not set"

**Solution:**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### Error: "MCP server connection failed"

**Check:**
1. Server URL is correct
2. Server is online: `curl https://togomcp.rdfportal.org/mcp`
3. Network allows HTTP connections
4. API tokens are set (if required)

### Error: "This event loop is already running"

This shouldn't happen with the current implementation, but if it does, make sure you're running the script directly:

```bash
python automated_test_runner.py questions.json
```

Not importing and calling from another async context.

## Comparison with Original Scripts

If you have results from both versions:

```bash
# Old version (no MCP, baseline only)
../scripts/automated_test_runner.py questions.json -o old_results.csv

# New version (with MCP)
./automated_test_runner.py questions.json -o new_results.csv

# Compare
diff old_results.csv new_results.csv
```

You should see:
- Old version: `tools_used` column is always empty
- New version: `tools_used` column shows MCP tool names

## Integration with Evaluation Framework

The output CSV is compatible with the existing evaluation tracker:

1. Run automated evaluation
2. Open `evaluation_results.csv` in spreadsheet
3. Add manual scoring columns from rubric:
   - Accuracy (0-3)
   - Precision (0-3)
   - Completeness (0-3)
   - Verifiability (0-3)
   - Currency (0-3)
   - Impossibility (0-3)
4. Calculate total score and assessment
5. Import into master evaluation tracker

## Best Practices

1. **Start small**: Test with 3-5 questions first
2. **Verify MCP**: Check that tools are actually being used
3. **Compare carefully**: Look at both baseline and TogoMCP answers
4. **Document findings**: Use the `notes` field liberally
5. **Save configs**: Keep track of which MCP configuration was used
6. **Version control**: Track question files and configs in git

## Next Steps

After running your first evaluation:

1. Review results CSV
2. Check which tools were used
3. Compare baseline vs TogoMCP answers
4. Add manual scoring using rubric
5. Analyze patterns in tool usage
6. Refine questions based on results

## Support

For issues specific to:
- **MCP servers**: Check TogoMCP documentation
- **Agent SDK**: See https://docs.anthropic.com/en/docs/agent-sdk
- **This script**: Review the code and comments
- **Evaluation methodology**: See `../togomcp_evaluation_rubric.md`

## License

This evaluation tooling follows the same license as the main TogoMCP project.

---

**Created**: 2025-12-15  
**Version**: 1.0 (Agent SDK)  
**Status**: Production-ready with MCP support
