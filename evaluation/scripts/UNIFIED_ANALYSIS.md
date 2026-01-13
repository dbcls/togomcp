# Unified Analysis Scripts - Supporting Both Pattern Matching and LLM Evaluation

## Overview

The analysis scripts have been updated to support **both** simple pattern matching and LLM-based evaluation methods. The new unified scripts automatically detect which evaluation columns are available and provide appropriate analysis.

## Changes Summary

### New Unified Scripts

1. **`results_analyzer_unified.py`** - Replaces `results_analyzer.py`
   - Auto-detects evaluation method (pattern matching vs LLM)
   - Supports three modes: `pattern`, `llm`, and `combined`
   - Provides method comparison when both are available
   - Shows LLM confidence statistics

2. **`generate_dashboard_unified.py`** - Replaces `generate_dashboard.py`
   - Generates interactive HTML dashboards for any evaluation method
   - Includes additional charts for LLM evaluation (method comparison, confidence distribution)
   - Visual mode badge showing current evaluation method

### Evaluation Modes

The unified scripts support three evaluation modes:

| Mode | Description | Columns Used |
|------|-------------|--------------|
| **pattern** | Simple string pattern matching | `baseline_has_expected`, `togomcp_has_expected` |
| **llm** | LLM-based semantic evaluation | `baseline_llm_match`, `togomcp_llm_match` |
| **combined** | Union of both methods (OR logic) | `full_combined_baseline_found`, `full_combined_togomcp_found` |

### CSV File Structure

**Basic results** (from `automated_test_runner.py`):
```
question_id, category, question_text, baseline_has_expected, togomcp_has_expected, ...
```

**With LLM evaluation** (from `add_llm_evaluation.py`):
```
... + baseline_llm_match, baseline_llm_confidence, baseline_llm_explanation,
      togomcp_llm_match, togomcp_llm_confidence, togomcp_llm_explanation,
      full_combined_baseline_found, full_combined_togomcp_found
```

## Usage

### Results Analyzer

```bash
# Auto-detect mode (recommended)
python results_analyzer_unified.py results.csv

# Force specific mode
python results_analyzer_unified.py results_with_llm.csv --mode pattern
python results_analyzer_unified.py results_with_llm.csv --mode llm
python results_analyzer_unified.py results_with_llm.csv --mode combined

# Skip method comparison
python results_analyzer_unified.py results_with_llm.csv --no-comparison
```

**Output includes:**
- Overall statistics with the selected evaluation method
- Breakdown by category
- Questions grouped by value-add
- Method comparison (pattern vs LLM) when both available
- LLM confidence distribution
- Issue identification
- Recommendations

### Dashboard Generator

```bash
# Auto-detect mode (recommended)
python generate_dashboard_unified.py results.csv

# Specify output file
python generate_dashboard_unified.py results_with_llm.csv -o my_dashboard.html

# Force specific mode
python generate_dashboard_unified.py results_with_llm.csv --mode combined

# Generate and open in browser
python generate_dashboard_unified.py results_with_llm.csv --open
```

**Dashboard includes:**
- Overall statistics cards
- Correctness comparison chart
- Success pattern distribution
- Value-add distribution (new!)
- Category performance
- Evaluation method comparison (if LLM data available)
- LLM confidence distribution (if LLM data available)
- Tool usage statistics
- Response time comparison

## Workflow

### Complete Evaluation Pipeline

1. **Run basic evaluation:**
   ```bash
   python automated_test_runner.py questions.json
   # → Generates results.csv with pattern matching
   ```

2. **Add LLM evaluation (optional but recommended):**
   ```bash
   python add_llm_evaluation.py results.csv
   # → Generates results_with_llm.csv
   ```

3. **Analyze results:**
   ```bash
   # For pattern matching only
   python results_analyzer_unified.py results.csv
   
   # For combined evaluation (recommended)
   python results_analyzer_unified.py results_with_llm.csv
   ```

4. **Generate dashboard:**
   ```bash
   # For pattern matching only
   python generate_dashboard_unified.py results.csv --open
   
   # For combined evaluation (recommended)
   python generate_dashboard_unified.py results_with_llm.csv --open
   ```

## Key Features

### Automatic Detection

The scripts automatically detect available columns:

```python
# Script checks for LLM columns
if 'baseline_llm_match' in columns:
    mode = 'combined'  # Use both methods
else:
    mode = 'pattern'   # Use pattern matching only
```

### Combined Evaluation Logic

The `combined` mode uses **OR logic**:

```python
full_combined_baseline_found = (
    baseline_has_expected OR baseline_llm_match
)
```

This captures cases that either method finds, providing the most comprehensive evaluation.

### Method Comparison

When LLM columns are present, the analyzer shows:

- **Agreement rate**: How often both methods agree
- **Pattern only**: Cases found by pattern matching but missed by LLM
- **LLM only**: Cases found by LLM but missed by pattern matching

This helps identify:
- When pattern matching is too strict
- When LLM evaluation adds value
- Cases where both methods fail

### Confidence Tracking

For LLM evaluations, confidence levels are tracked:

- **High**: LLM is very confident in the match
- **Medium**: LLM is somewhat confident
- **Low**: LLM is uncertain

Low confidence matches may need manual review.

## Backward Compatibility

The unified scripts are **fully backward compatible**:

- Work with old results files (pattern matching only)
- Work with new results files (with LLM evaluation)
- Old scripts still work but don't support LLM evaluation

### Migration Path

You can migrate gradually:

1. Continue using old scripts with old results
2. Use unified scripts with old results (pattern mode)
3. Add LLM evaluation to get enhanced analysis
4. Use unified scripts with new results (combined mode)

## Best Practices

### When to Use Each Mode

| Scenario | Recommended Mode |
|----------|-----------------|
| Quick evaluation, no LLM available | `pattern` |
| Want semantic matching | `llm` |
| Most comprehensive analysis | `combined` (default) |
| Comparing evaluation methods | `combined` with comparison |

### Interpreting Results

**High pattern-only count**: Pattern matching might be too strict, consider LLM evaluation

**High LLM-only count**: LLM is finding semantic matches that pattern matching misses

**Low LLM confidence**: These matches need manual review to verify correctness

**Combined mode recommended**: Captures the most correct answers and reduces false negatives

## Examples

### Example 1: Basic Pattern Matching

```bash
$ python results_analyzer_unified.py results.csv

✓ No LLM columns detected - using PATTERN MATCHING mode
✓ Loaded 50 evaluation results from results.csv

======================================================================
EVALUATION RESULTS ANALYSIS - PATTERN MATCHING
======================================================================

Total Questions: 50

BASELINE PERFORMANCE:
  Technical Success:          48/50 (96.0%)
  Actually Answered:          45/50 (90.0%)
  Has Expected Answer:        30/50 (60.0%)
...
```

### Example 2: Combined Evaluation with Breakdown

```bash
$ python results_analyzer_unified.py results_with_llm.csv

✓ Detected LLM evaluation columns - using COMBINED mode
✓ Loaded 50 evaluation results from results_with_llm.csv

======================================================================
EVALUATION RESULTS ANALYSIS - COMBINED (Pattern OR LLM)
======================================================================

Total Questions: 50

BASELINE PERFORMANCE:
  Technical Success:          48/50 (96.0%)
  Actually Answered:          45/50 (90.0%)
  Has Expected Answer:        38/50 (76.0%)
    └─ Pattern only:          5
    └─ LLM only:              8
    └─ Both methods:          25

LLM EVALUATION CONFIDENCE:
  Baseline - High: 20, Medium: 10, Low: 3
...
```

### Example 3: Method Comparison

```bash
$ python results_analyzer_unified.py results_with_llm.csv

...

COMPARISON: PATTERN MATCHING vs LLM EVALUATION:
----------------------------------------------------------------------

Agreement Rate:
  Baseline:  35/50 (70.0%)
  TogoMCP:   40/50 (80.0%)

Pattern Found but LLM Missed:
  Baseline:  5
  TogoMCP:   3

LLM Found but Pattern Missed:
  Baseline:  8
  TogoMCP:   7

💡 Combined method captures 8 additional baseline matches
   and 7 additional TogoMCP matches that pattern matching missed.
```

## Troubleshooting

### Issue: "No LLM columns detected"

**Cause**: CSV file doesn't have LLM evaluation columns

**Solution**: 
```bash
python add_llm_evaluation.py results.csv
```

### Issue: Mode forced but columns missing

**Cause**: Requested `--mode llm` but no LLM columns present

**Solution**: Script automatically falls back to pattern mode with a warning

### Issue: Dashboard looks different

**Cause**: Different evaluation modes show different charts

**Solution**: This is expected - LLM modes add extra visualizations

## Performance Considerations

- Pattern matching: Very fast, no external dependencies
- LLM evaluation: Slower (requires Ollama), but more accurate
- Combined mode: Same speed as LLM (uses pre-computed columns)

## Future Enhancements

Potential improvements:

- Multiple LLM model comparison
- Confidence-weighted metrics
- Interactive filtering by confidence
- Export disagreement cases for review
- A/B testing different evaluation thresholds

## Questions?

For issues or questions about the unified analysis scripts:
1. Check this README
2. Review `LLM_EVALUATION.md` for LLM evaluation details
3. Check the main `README.md` for general evaluation setup
4. Review example outputs in the documentation
