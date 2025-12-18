# Cost Computation for TogoMCP Evaluations

This document explains how to compute API costs for TogoMCP evaluation test runs.

## Overview

The `compute_costs.py` script analyzes the results from `automated_test_runner.py` and calculates:

- **Baseline costs**: Exact costs based on actual token usage (Claude without tools)
- **TogoMCP costs**: Estimated costs based on response length and tool usage (Claude with MCP tools)
- Cost breakdowns by category and value-add assessment

## Important Note: TogoMCP Cost Estimation

⚠️ **The Agent SDK doesn't expose token counts**, so TogoMCP costs are **estimates** based on:
- Character count in responses (÷4 for rough token estimate)
- Overhead for MCP tool schemas (~1500 tokens)
- Tool usage (each tool call adds ~200 input + ~500 output tokens)

These estimates provide a reasonable approximation but should not be considered exact.

## Installation

No additional dependencies needed beyond what's already in `requirements.txt`.

## Basic Usage

### Analyze evaluation results:
```bash
python compute_costs.py evaluation_results.csv
```

### Specify a different model:
```bash
python compute_costs.py evaluation_results.csv --model claude-opus-4-20250514
```

### Export detailed JSON report:
```bash
python compute_costs.py evaluation_results.csv --export cost_report.json
```

### Use custom pricing:
```bash
python compute_costs.py evaluation_results.csv --pricing custom_pricing.json
```

### Show only baseline costs (skip TogoMCP estimation):
```bash
python compute_costs.py evaluation_results.csv --no-estimate
```

## Supported Models

The script includes default pricing for:

- `claude-sonnet-4-20250514` - Claude Sonnet 4 (default)
  - Input: $3.00/MTok, Output: $15.00/MTok
- `claude-opus-4-20250514` - Claude Opus 4
  - Input: $15.00/MTok, Output: $75.00/MTok
- `claude-haiku-4-20250110` - Claude Haiku 4
  - Input: $0.80/MTok, Output: $4.00/MTok
- `claude-sonnet-3-5-20241022` - Claude 3.5 Sonnet
  - Input: $3.00/MTok, Output: $15.00/MTok

## Custom Pricing

Create a JSON file with custom pricing:

```json
{
  "model_name": "My Custom Model",
  "input_price_per_mtok": 2.5,
  "output_price_per_mtok": 10.0
}
```

Then use it:
```bash
python compute_costs.py evaluation_results.csv --pricing custom_pricing.json
```

## Output

### Console Output

The script prints a comprehensive cost summary including:

1. **Baseline Costs** (exact):
   - Successful tests
   - Input/output tokens
   - Total cost
   - Average cost per test

2. **TogoMCP Costs** (estimated):
   - Same metrics as baseline
   - Warning about estimation

3. **Total Evaluation Cost**:
   - Combined baseline + TogoMCP
   - Percentage breakdown
   - Overhead analysis

4. **Costs by Category**:
   - Per question category breakdown

5. **Costs by Value-Add**:
   - Costs for CRITICAL, VALUABLE, MARGINAL, REDUNDANT, FAILED

### Example Output

```
================================================================================
COST ANALYSIS FOR TOGOMCP EVALUATION
================================================================================
Model: Claude Sonnet 4
Pricing: $3.00/MTok input, $15.00/MTok output
Total questions evaluated: 20

BASELINE COSTS (No Tools)
--------------------------------------------------------------------------------
  Successful tests:     20/20
  Input tokens:         1,520
  Output tokens:        2,200
  Total tokens:         3,720
  Total cost:           $0.0376
  Avg cost per test:    $0.0019

TOGOMCP COSTS (With MCP Tools) (ESTIMATED)
--------------------------------------------------------------------------------
  ⚠️  Note: Agent SDK doesn't expose token counts.
      These are ESTIMATES based on text length and tool usage.

  Successful tests:     20/20
  Input tokens:         32,400
  Output tokens:        14,500
  Total tokens:         46,900
  Total cost:           $0.3147
  Avg cost per test:    $0.0157

TOTAL EVALUATION COST
--------------------------------------------------------------------------------
  Baseline:             $0.0376 (10.7%)
  TogoMCP:              $0.3147 (89.3%)
  TOTAL:                $0.3523

  TogoMCP overhead:     +736.7% vs baseline

COSTS BY CATEGORY
--------------------------------------------------------------------------------
  Precision            $  0.0520  (Base: $0.0055, TogoMCP: $0.0465)
  Recall               $  0.1280  (Base: $0.0135, TogoMCP: $0.1145)
  Integration          $  0.1723  (Base: $0.0186, TogoMCP: $0.1537)

COSTS BY VALUE-ADD CATEGORY
--------------------------------------------------------------------------------
  CRITICAL     (12 tests)  $  0.2115  (Base: $0.0226, TogoMCP: $0.1889)
  VALUABLE     ( 6 tests)  $  0.1058  (Base: $0.0113, TogoMCP: $0.0945)
  MARGINAL     ( 2 tests)  $  0.0350  (Base: $0.0037, TogoMCP: $0.0313)

================================================================================
```

### JSON Export

Use `--export` to save detailed analysis:

```bash
python compute_costs.py evaluation_results.csv --export cost_report.json
```

The JSON file includes:
- All cost metrics
- Per-category breakdowns
- Per-value-add breakdowns
- Pricing information
- Token counts

## Interpreting Results

### Baseline vs TogoMCP

- **Baseline costs** are exact and based on actual API token usage
- **TogoMCP costs** are estimates and typically show 5-10x overhead due to:
  - MCP tool schemas being sent with each request
  - Tool call overhead
  - Potentially longer, more detailed responses

### Value-Add Categories

- **CRITICAL**: TogoMCP answered when baseline couldn't - highest ROI
- **VALUABLE**: Both answered, but TogoMCP more accurate or enhanced
- **MARGINAL**: Similar results, unclear benefit
- **REDUNDANT**: TogoMCP didn't use tools, same as baseline
- **FAILED**: TogoMCP failed to complete

Cost analysis by value-add helps identify where MCP tools provide the most value for the cost.

## Limitations

1. **TogoMCP token counts are estimates** - actual costs may vary ±30%
2. Estimation assumes:
   - ~4 characters per token
   - Fixed overhead of 1500 tokens for MCP schemas
   - ~200 input + ~500 output tokens per tool call
3. Doesn't account for caching or rate limits
4. Assumes consistent pricing (prices may change)

## Tips

1. **For budget planning**: Add 30% buffer to estimated TogoMCP costs
2. **Track trends**: Run cost analysis regularly to monitor changes
3. **Optimize categories**: Focus optimization efforts on high-cost categories
4. **Value analysis**: Calculate cost-per-CRITICAL-result to assess ROI

## Questions?

For issues or questions about cost computation, please refer to:
- `automated_test_runner.py` - Source of evaluation data
- Anthropic pricing page - Current API pricing
- This README - Usage documentation
