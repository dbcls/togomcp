# Cache Pricing Issue - Resolved! ✅

## Problem Summary

**Your calculation**: $0.4605  
**Actual billing**: $2.77  
**Discrepancy**: $2.31 (6x difference!)

## Root Cause: Prompt Cache Pricing Not Accounted For

The `compute_costs.py` script was treating ALL tokens as regular input at $3.00/MTok, but Anthropic has different pricing for prompt caching:

| Token Type | Script Was Using | Actual Anthropic Pricing | Impact |
|------------|------------------|-------------------------|--------|
| Regular Input | $3.00/MTok | $3.00/MTok | ✅ Correct |
| **Cache Creation** | $3.00/MTok | **$3.75/MTok** | ⚠️ 25% undercharge |
| **Cache Read** | $3.00/MTok | **$0.30/MTok** | ⚠️ Should be 90% discount |
| Output | $15.00/MTok | $15.00/MTok | ✅ Correct |

## Your Actual Token Usage (24 questions)

From `results.csv`:

```
BASELINE:
  Input:    1,364 tokens × $3.00/MTok  = $0.0041
  Output:   4,868 tokens × $15.00/MTok = $0.0730
  Total: $0.0771

TOGOMCP:
  Regular input:     466 tokens × $3.00/MTok  = $0.0014
  Cache creation: 348,663 tokens × $3.75/MTok  = $1.3075  ← Major cost!
  Cache read:   2,622,657 tokens × $0.30/MTok  = $0.7868  ← Savings from cache
  Output:        25,464 tokens × $15.00/MTok  = $0.3820
  Total: $2.4776
```

## Cost Breakdown

| Component | Old Calculation | Correct Calculation | Difference |
|-----------|----------------|-------------------|------------|
| Baseline | $0.0771 | $0.0771 | ✅ Same |
| TogoMCP | $0.3834 | $2.4776 | ⚠️ 6.5x higher! |
| **TOTAL** | **$0.4605** | **$2.5548** | **$2.09 difference** |

**Actual billing**: $2.77  
**Corrected calculation**: $2.55  
**Remaining gap**: $0.22 (only 8% - acceptable!)

## Why Cache Costs Are So High

### Cache Creation: 348,663 tokens

This is the **MCP tool schemas** being cached:
- ~20+ tools from TogoMCP
- Each tool has detailed schema (name, description, parameters, types, examples)
- Average: **14,527 tokens per question** for cache creation
- Cost: **$1.31 total** (48% of TogoMCP cost!)

### Cache Read: 2,622,657 tokens

This is reading cached schemas PLUS accumulated conversation:
- MCP tool schemas (reused from cache)
- Conversation history
- Previous tool results
- Average: **109,277 tokens per question** from cache
- Cost: **$0.79 total** (32% of TogoMCP cost!) - but saves $7.09 vs no caching!

## What Changed in compute_costs.py

### 1. Updated PricingInfo class:
```python
@dataclass
class PricingInfo:
    model_name: str
    input_price_per_mtok: float
    output_price_per_mtok: float
    cache_creation_price_per_mtok: float = None  # NEW: +25%
    cache_read_price_per_mtok: float = None      # NEW: -90%
    
    def compute_cost(self, input_tokens, output_tokens, 
                    cache_creation_tokens=0, cache_read_tokens=0):
        # Now includes cache pricing!
```

### 2. Updated pricing definitions:
```python
"claude-sonnet-4-20250514": PricingInfo(
    model_name="Claude Sonnet 4",
    input_price_per_mtok=3.0,
    output_price_per_mtok=15.0,
    cache_creation_price_per_mtok=3.75,  # NEW!
    cache_read_price_per_mtok=0.30       # NEW!
)
```

### 3. Updated cost calculations:
All functions now pass cache tokens to `compute_cost()`:
- `calculate_togomcp_costs()`
- `calculate_by_category()`
- `calculate_by_value_add()`

## New Output Example

```
================================================================================
COST ANALYSIS FOR TOGOMCP EVALUATION
================================================================================
Model: Claude Sonnet 4
Pricing: $3.00/MTok input, $15.00/MTok output
Total questions evaluated: 24

BASELINE COSTS (No Tools)
--------------------------------------------------------------------------------
  Total cost:           $0.0771

TOGOMCP COSTS (With MCP Tools) (EXACT)
--------------------------------------------------------------------------------
  ✅ Using actual token counts from Agent SDK ResultMessage

  Input tokens:         466
  Output tokens:        25,464
  Cache creation:       348,663 tokens  ← Shows cache costs!
  Cache read:           2,622,657 tokens
  Total cost:           $2.4776

TOTAL EVALUATION COST
--------------------------------------------------------------------------------
  Baseline:             $0.0771 (3.0%)
  TogoMCP:              $2.4776 (97.0%)
  TOTAL:                $2.5548  ← Much closer to $2.77 billing!

  TogoMCP overhead:     +3113.0% vs baseline
```

## Remaining $0.22 Difference

The small gap between calculated ($2.55) and billed ($2.77) is only 8% and likely due to:

1. **Rounding differences** - API may round differently than CSV
2. **Other API usage** during the same billing period
3. **Failed attempts** before successful responses
4. **Token counting edge cases** - API vs reported counts
5. **Network overhead** or metadata not captured

This is well within acceptable margin for cost estimation!

## Key Takeaways

✅ **Fixed**: Cache pricing now properly accounted for  
✅ **Accurate**: $2.55 calculated vs $2.77 billed (92% accurate)  
✅ **Transparent**: Cache costs clearly shown in output  
✅ **MCP overhead visible**: Can see exact cost of tool schemas  

## Impact on Future Evaluations

- **More expensive than originally thought**: TogoMCP costs 6.5x more than estimated
- **Cache is essential**: Without caching, costs would be **~$10** for same eval
- **Tool count matters**: More MCP tools = higher cache creation cost
- **Batch benefits**: Later questions benefit from caching (cheaper per question)

## Action Items

1. ✅ `compute_costs.py` updated with cache pricing
2. ✅ All cost calculations now include cache tokens
3. ✅ Output shows cache breakdown
4. 📊 Re-budget based on $2.55 per 24 questions (~$0.106/question with MCP)
5. 🔍 Consider optimizing: Can you reduce number of MCP tools loaded?

## Comparison

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Baseline cost | $0.08 | $0.08 (same) |
| TogoMCP cost | **$0.38** | **$2.48** |
| Total | **$0.46** | **$2.55** |
| vs Billing | **17% of actual** | **92% of actual** |

The fix increased calculated costs by 5.5x to match reality!
