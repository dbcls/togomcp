# Configuration Format Guide

## Overview

The `automated_test_runner.py` script supports both JSON and YAML configuration formats. YAML is now the recommended format because it makes multiline strings much easier to read and write.

## File Format Support

The script automatically detects the format:
1. Tries to load as YAML first
2. Falls back to JSON if YAML parsing fails
3. Uses default configuration if no config file is provided

## Using YAML Configuration

### Basic Usage

```bash
# Use YAML config
python automated_test_runner.py questions/*.yaml -c config.yaml

# JSON still works for backward compatibility
python automated_test_runner.py questions/*.yaml -c config.json
```

### Multiline Strings in YAML

YAML provides several ways to write multiline strings:

#### 1. Literal Block Style (`|`)
**Preserves newlines and indentation**

```yaml
system_prompt: |
  Line 1
  Line 2
  Line 3
```

Result: `"Line 1\nLine 2\nLine 3\n"`

#### 2. Folded Block Style (`>`)
**Folds newlines into spaces (good for long paragraphs)**

```yaml
description: >
  This is a very long description that
  spans multiple lines but will be
  folded into a single line with spaces.
```

Result: `"This is a very long description that spans multiple lines but will be folded into a single line with spaces.\n"`

#### 3. Literal Block Chomping (`|-` or `|+`)
**Controls trailing newlines**

```yaml
# Strip final newlines
text1: |-
  Hello
  World

# Keep single final newline (default)
text2: |
  Hello
  World

# Keep all final newlines
text3: |+
  Hello
  World

```

#### 4. Inline Strings
**For short, single-line text**

```yaml
model: claude-sonnet-4-5-20250929
temperature: 1.0
```

## Example Comparison

### JSON Format (Old)
```json
{
  "baseline_system_prompt": "You are an expert assistant answering biological and biomedical questions. Answer using only your training knowledge. Do not use any database tools or external resources.\n\nWrite answers that are:\n- COMPLETE: Include all necessary information\n- PRECISE: Include only relevant information\n- NON-REDUNDANT: Avoid repeating the same information\n- READABLE: Use clear, fluent scientific prose\n- DIRECT: State facts without meta-references (no 'research shows', 'according to', etc.)\n\nIf you don't know something with certainty, state this clearly and concisely."
}
```

### YAML Format (New - Recommended)
```yaml
baseline_system_prompt: |
  You are an expert assistant answering biological and biomedical questions. 
  Answer using only your training knowledge. 
  Do not use any database tools or external resources.
  
  Write answers that are:
  - COMPLETE: Include all necessary information
  - PRECISE: Include only relevant information
  - NON-REDUNDANT: Avoid repeating the same information
  - READABLE: Use clear, fluent scientific prose
  - DIRECT: State facts without meta-references (no 'research shows', 'according to', etc.)
  
  If you don't know something with certainty, state this clearly and concisely.
```

Much more readable!

## Configuration Options

### Required Fields
- `model`: Claude model identifier
- `baseline_system_prompt`: System prompt for baseline tests (no tools)
- `togomcp_system_prompt`: System prompt for TogoMCP tests (with tools)
- `mcp_servers`: Dictionary of MCP server configurations

### Optional Fields
- `max_tokens`: Maximum tokens per response (default: 4000)
- `temperature`: Sampling temperature (default: 1.0)
- `timeout`: Request timeout in seconds (default: 120)
- `retry_attempts`: Number of retry attempts (default: 3)
- `retry_delay`: Initial retry delay in seconds (default: 2)
- `max_retry_delay`: Maximum retry delay in seconds (default: 30)
- `allowed_tools`: List of allowed tool patterns (default: ["mcp__*"])
- `disallowed_tools`: List of disallowed tools (default: web tools)

## Migration from JSON to YAML

To migrate your existing JSON config to YAML:

1. Rename `config.json` to `config.yaml`
2. Convert multiline strings to use `|` block style
3. Remove escape sequences like `\n`
4. Remove quotes around string values (optional, but cleaner)
5. Use proper YAML indentation (2 spaces)

See `config.yaml` for a complete example.

## Tips

1. **Use `|` for prompts**: Literal block style is perfect for system prompts
2. **Use `>` for descriptions**: Folded style is good for long paragraphs
3. **Comments**: Use `#` for comments (unlike JSON)
4. **No quotes needed**: Most strings don't need quotes in YAML
5. **Indentation matters**: Use 2 spaces (not tabs)
6. **Test your config**: Run the script to validate YAML parsing

## Troubleshooting

If YAML parsing fails, the script will:
1. Attempt to parse as JSON (backward compatibility)
2. Log a warning if neither format works
3. Use default configuration

Check the log file `test_runner.log` for parsing errors.
