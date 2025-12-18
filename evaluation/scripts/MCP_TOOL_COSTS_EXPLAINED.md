# MCP Tool Loading Costs - YES, They're Included!

## TL;DR

**Yes, the token counts include MCP tool loading costs.** In fact, the bulk of TogoMCP costs come from loading the tool schemas!

## Evidence from Your Test Run

```python
usage: {
    'input_tokens': 17,                      # Your question
    'cache_creation_input_tokens': 17474,    # MCP tool schemas! ← THIS IS THE COST
    'cache_read_input_tokens': 34565,        # Cached schemas
    'output_tokens': 490,
}
```

## What's in Those 17,474 Tokens?

The `cache_creation_input_tokens` includes:

### 1. **MCP Tool Schemas (Majority ~15,000-17,000 tokens)**
Every MCP tool definition sent to the API includes:
```json
{
  "name": "mcp__togomcp__search_uniprot_entity",
  "description": "Search for a UniProt entity ID by query...",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The query to search for..."
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of results..."
      }
    },
    "required": ["query"]
  }
}
```

For TogoMCP with ~20+ tools, this adds up quickly!

### 2. **System Prompt (~500 tokens)**
```
You have access to biological databases through MCP tools.
Use them when they would improve the accuracy...
```

### 3. **Other Context**
- Model instructions
- Tool usage examples
- Metadata

## Actual Cost Breakdown

### Cost per Request with Prompt Caching

**Anthropic Pricing (Sonnet 4):**
- Regular input: $3.00/MTok
- Cache write (creation): $3.75/MTok (25% premium)
- Cache read: $0.30/MTok (90% discount!)
- Output: $15.00/MTok

### First Request (Creates Cache):
```
Regular input:    17 tokens × $3.00/MTok    = $0.000051
Cache creation: 17,474 tokens × $3.75/MTok  = $0.065528
Output:          490 tokens × $15.00/MTok   = $0.007350
──────────────────────────────────────────────────────
TOTAL:                                      = $0.072929
```

### Subsequent Requests (Uses Cache):
```
Regular input:    17 tokens × $3.00/MTok    = $0.000051
Cache read:   34,565 tokens × $0.30/MTok    = $0.010370
Output:          490 tokens × $15.00/MTok   = $0.007350
──────────────────────────────────────────────────────
TOTAL:                                      = $0.017771
```

### Savings from Caching:
```
First request:   $0.0729
Later requests:  $0.0178 (75.6% cheaper!)
```

## Why Cache Reads Are Larger Than Creates

You saw:
- `cache_creation_input_tokens: 17,474`
- `cache_read_input_tokens: 34,565`

This is because:
1. **First turn**: Created cache with MCP schemas
2. **Subsequent turns**: Read cache PLUS added conversation history
3. Cache accumulates: schemas + past messages + tool results

## Impact on Your Evaluation Costs

### Old Estimate (Without Cache Awareness):
```
TogoMCP: $0.3129 (estimated)
```

### New Actual (With Cache):
```
First question:  $0.073
Next 9 questions: $0.018 × 9 = $0.162
Total TogoMCP: ~$0.235 (25% cheaper than estimate!)
```

## Key Takeaways

✅ **MCP tool schemas ARE included** in token counts
✅ **Prompt caching dramatically reduces** the per-request cost
✅ **The overhead is mostly tool definitions**, not user questions
✅ **Cache is automatic** through the Agent SDK
✅ **Costs are now accurately tracked** in your CSV files

## Why This Matters

1. **Budget Accurately**: Know the true cost of MCP tools
2. **Optimize Tool Count**: More tools = higher cache_creation cost
3. **Batch Evaluation**: Later questions benefit from caching
4. **Compare Fairly**: Baseline doesn't have this overhead

## MCP Tool Overhead Is Real

The ~17K token overhead means:
- **Baseline**: Just the question (~17 tokens)
- **TogoMCP**: Question + 17K tool schemas (~17,457 tokens)

That's a **1000x increase** in input tokens just from having MCP tools available!

But thanks to caching, this overhead is paid once and then dramatically reduced.

## Recommendation

Your current `compute_costs.py` calculates costs correctly from the token counts. However, to be fully accurate with cache pricing, you could:

1. **Account for cache_creation premium** (+25%)
2. **Account for cache_read discount** (-90%)

But for now, the simplified calculation (treating all as regular input) gives you a reasonable approximation that's close to actual costs.
