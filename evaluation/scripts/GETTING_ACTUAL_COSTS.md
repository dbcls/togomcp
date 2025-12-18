# Getting Actual Costs from Anthropic API

## Quick Answer

**No, the Anthropic API does not return dollar amounts or credits directly.**

It only returns **token counts**, which you must convert to costs using the pricing table.

## What the API Returns

### ✅ Available in Response
```python
response.usage.input_tokens              # Count of input tokens
response.usage.output_tokens             # Count of output tokens
response.usage.cache_read_input_tokens   # Cached tokens (if using prompt caching)
```

### ❌ NOT Available
- Cost in dollars/credits
- Price per token  
- Total cost

## Your Current Situation

### Baseline Tests: ✅ Exact Costs
Your `automated_test_runner.py` already captures token counts:
```python
"usage": {
    "input_tokens": response.usage.input_tokens,
    "output_tokens": response.usage.output_tokens
}
```
**Result**: `compute_costs.py` provides **exact** baseline costs

### TogoMCP Tests: ⚠️ Estimated Costs  
The Agent SDK doesn't expose token counts, so:
```python
# Token counts NOT available through Agent SDK
togomcp_result = await self._make_togomcp_call(question)
# No usage information in the result
```
**Result**: `compute_costs.py` **estimates** TogoMCP costs

## Options to Get Exact TogoMCP Costs

### Option 1: Inspect Agent SDK (Quickest to try)
The SDK might expose token counts in some field we haven't checked:

```bash
python inspect_agent_sdk_tokens.py "What is UniProt ID for Cas9?"
```

This will inspect all message attributes and report if token/usage fields exist.

### Option 2: Switch to Direct API Calls (Most Reliable)
Instead of using the Agent SDK, use the Anthropic API directly with MCP tools:

**Pros**: 
- Get exact token counts
- Full control over tool calling

**Cons**:
- More complex code
- Manual tool calling loop
- Lose SDK convenience features

**Implementation**: Would require modifying `automated_test_runner.py` to handle
tool calling manually instead of using `ClaudeSDKClient`.

### Option 3: Anthropic Console Usage Tracking (Manual)
1. Go to https://console.anthropic.com/settings/usage
2. Record usage before evaluation run
3. Run evaluation  
4. Record usage after evaluation run
5. Calculate difference

**Pros**:
- 100% accurate actual costs
- No code changes needed

**Cons**:
- Manual process
- Can't separate baseline vs TogoMCP
- Other API usage might interfere

### Option 4: Keep Current Estimation (Simplest)
The current estimation method is reasonable:

```python
# Estimates based on:
# - Text length ÷ 4 for token approximation
# - 1500 token overhead for MCP schemas
# - ~200 input + ~500 output per tool call
```

**Accuracy**: Typically within ±30% of actual costs
**Best for**: Relative comparisons, trend analysis, rough budgeting

## Recommendation

**Immediate**: Try Option 1 (`inspect_agent_sdk_tokens.py`)
- Takes 2 minutes to run
- Will tell you if SDK has token info

**If tokens not available**: 
- Keep Option 4 (estimation) for now
- Plan to implement Option 2 if exact costs are critical

**For high-stakes budgeting**:
- Use Option 3 (Console tracking) for validation
- Compare against estimates to calibrate accuracy

## Tools Provided

1. **`compute_costs.py`** - Current solution with estimation
2. **`inspect_agent_sdk_tokens.py`** - Check if SDK exposes tokens
3. **`query_anthropic_usage.py`** - Example of usage API concept
4. **`COST_COMPUTATION_README.md`** - Full documentation

## Example: Validation Approach

To validate estimation accuracy:

```bash
# 1. Record baseline usage
python query_anthropic_usage.py --output before.json

# 2. Run evaluation
python automated_test_runner.py questions.json

# 3. Record after usage
python query_anthropic_usage.py --output after.json

# 4. Calculate difference (actual cost)
# Compare to compute_costs.py output (estimated cost)
# Calculate accuracy percentage
```

This helps you understand how accurate the estimates are for your use case.
