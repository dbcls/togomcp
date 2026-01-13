# Quick Migration Guide: Pattern Matching → LLM Evaluation

## For Existing Users

If you've been using the evaluation scripts with pattern matching only, here's how to upgrade to LLM-based evaluation.

## What's New?

✅ **More accurate evaluation** - LLM understands semantic similarity  
✅ **Backward compatible** - Old scripts and results still work  
✅ **Automatic detection** - New scripts auto-detect evaluation type  
✅ **Combined mode** - Get best of both worlds  

## Quick Start

### Option 1: Keep Using Pattern Matching

No changes needed! Your existing workflow continues to work:

```bash
# Old workflow (still works)
python automated_test_runner.py questions.json
python results_analyzer.py results.csv
python generate_dashboard.py results.csv
```

### Option 2: Add LLM Evaluation (Recommended)

Enhance your existing results with LLM evaluation:

```bash
# 1. Install Ollama and llama3.2 (one-time setup)
# See: https://ollama.ai

# 2. Add LLM evaluation to existing results
python add_llm_evaluation.py results.csv
# → Creates results_with_llm.csv

# 3. Use unified analysis scripts
python results_analyzer_unified.py results_with_llm.csv
python generate_dashboard_unified.py results_with_llm.csv --open
```

### Option 3: New Evaluation Workflow

Start fresh with combined evaluation:

```bash
# 1. Run basic evaluation
python automated_test_runner.py questions.json
# → Creates results.csv

# 2. Add LLM evaluation
python add_llm_evaluation.py results.csv
# → Creates results_with_llm.csv

# 3. Analyze with unified scripts
python results_analyzer_unified.py results_with_llm.csv
python generate_dashboard_unified.py results_with_llm.csv --open
```

## Side-by-Side Comparison

### Old Way (Pattern Matching Only)

```bash
# Pros:
# - Fast execution
# - No extra dependencies
# - Simple to understand

# Cons:
# - Misses paraphrased answers
# - May have false negatives
# - Strict string matching

python results_analyzer.py results.csv
```

Output shows only pattern matching results:
```
BASELINE PERFORMANCE:
  Has Expected Answer:  30/50 (60.0%)

TOGOMCP PERFORMANCE:
  Has Expected Answer:  35/50 (70.0%)
```

### New Way (Combined Evaluation)

```bash
# Pros:
# - More accurate matching
# - Semantic understanding
# - Captures more correct answers
# - Shows confidence levels

# Cons:
# - Requires Ollama setup
# - Slightly slower (one-time)

python add_llm_evaluation.py results.csv
python results_analyzer_unified.py results_with_llm.csv
```

Output shows combined results with breakdown:
```
BASELINE PERFORMANCE:
  Has Expected Answer:  38/50 (76.0%)
    └─ Pattern only:   5
    └─ LLM only:       8
    └─ Both methods:   25

LLM EVALUATION CONFIDENCE:
  Baseline - High: 20, Medium: 10, Low: 3
```

## Common Scenarios

### Scenario 1: "I just want to see if LLM helps"

```bash
# Run on existing results
python add_llm_evaluation.py results.csv

# Compare the two
python results_analyzer_unified.py results.csv        # Pattern only
python results_analyzer_unified.py results_with_llm.csv  # Combined
```

### Scenario 2: "I want to migrate all my old results"

```bash
# Batch process all result files
for f in results/*.csv; do
    if [[ ! "$f" =~ "_with_llm" ]]; then
        python add_llm_evaluation.py "$f"
    fi
done

# Now all files have LLM evaluation
```

### Scenario 3: "I want to keep both evaluation methods"

The unified scripts work with both! You can:

```bash
# Analyze pattern matching results
python results_analyzer_unified.py results.csv --mode pattern

# Analyze LLM results
python results_analyzer_unified.py results_with_llm.csv --mode llm

# Analyze combined (recommended)
python results_analyzer_unified.py results_with_llm.csv --mode combined
```

### Scenario 4: "I don't want to install Ollama"

No problem! Keep using the pattern matching workflow:

```bash
# Original scripts still work
python automated_test_runner.py questions.json
python results_analyzer.py results.csv
python generate_dashboard.py results.csv
```

Or use unified scripts in pattern mode:

```bash
python results_analyzer_unified.py results.csv --mode pattern
```

## What Gets Better with LLM Evaluation?

### Example: Paraphrased Answers

**Expected Answer:** `"UniProt ID: P12345"`

**Response:** `"The protein identifier in UniProt is P12345"`

- ❌ Pattern matching: MISS (exact string not found)
- ✅ LLM evaluation: MATCH (semantic similarity detected)
- ✅ Combined: MATCH (captures it)

### Example: Different Formatting

**Expected Answer:** `"Gene: BRCA1"`

**Response:** `"BRCA1 gene"`

- ❌ Pattern matching: MISS (order different)
- ✅ LLM evaluation: MATCH (same concept)
- ✅ Combined: MATCH (captures it)

### Example: Additional Context

**Expected Answer:** `"Tokyo"`

**Response:** `"The capital city of Japan is Tokyo, with a population of 14 million"`

- ✅ Pattern matching: MATCH (substring found)
- ✅ LLM evaluation: MATCH (answer present)
- ✅ Combined: MATCH (both agree)

## Installation Requirements

### For Pattern Matching Only (No Changes)

```bash
pip install -r requirements.txt
```

### For LLM Evaluation (Additional Setup)

```bash
# 1. Install Ollama
# Visit: https://ollama.ai

# 2. Pull the model
ollama pull llama3.2

# 3. Install Python package
pip install ollama

# That's it! Now run:
python add_llm_evaluation.py results.csv
```

## File Compatibility

All scripts are backward compatible:

| Script | Works with `results.csv` | Works with `results_with_llm.csv` |
|--------|-------------------------|-----------------------------------|
| `results_analyzer.py` | ✅ Yes | ⚠️ Yes (ignores LLM columns) |
| `generate_dashboard.py` | ✅ Yes | ⚠️ Yes (ignores LLM columns) |
| `results_analyzer_unified.py` | ✅ Yes (pattern mode) | ✅ Yes (combined mode) |
| `generate_dashboard_unified.py` | ✅ Yes (pattern mode) | ✅ Yes (combined mode) |

## FAQ

### Q: Do I need to re-run tests to use LLM evaluation?

**A:** No! Just run `add_llm_evaluation.py` on your existing results.csv file.

### Q: Will my old scripts break?

**A:** No! All old scripts continue to work with both file types.

### Q: What if I don't have Ollama?

**A:** Continue using pattern matching, or use unified scripts with `--mode pattern`.

### Q: Is LLM evaluation slower?

**A:** Initial evaluation is slower (adds ~2-3 seconds per question), but analysis is the same speed since results are cached in the CSV.

### Q: Can I use a different LLM model?

**A:** Yes! Use `--llm-model` parameter:
```bash
python add_llm_evaluation.py results.csv --llm-model mistral
```

### Q: How much better is combined evaluation?

**A:** Typically captures 10-20% more correct answers that pattern matching misses. Run comparison to see your specific improvement.

### Q: Should I delete old results?

**A:** No need! Keep both. The `_with_llm.csv` files include all original data plus LLM columns.

### Q: Can I switch back to pattern matching?

**A:** Yes! Use `--mode pattern` with unified scripts, or continue using old scripts.

## Recommended Workflow Going Forward

```bash
# 1. Run tests (generates results.csv)
python automated_test_runner.py questions.json

# 2. Optionally add LLM evaluation (generates results_with_llm.csv)
python add_llm_evaluation.py results.csv

# 3. Use unified analysis (auto-detects best mode)
python results_analyzer_unified.py results_with_llm.csv
python generate_dashboard_unified.py results_with_llm.csv --open

# 4. Review and iterate on questions
```

## Need Help?

- 📖 Read `UNIFIED_ANALYSIS.md` for detailed documentation
- 📖 Read `LLM_EVALUATION.md` for LLM evaluation details
- 🔍 Check existing issues on GitHub
- 💬 Ask questions in discussions

## Summary

✅ **No breaking changes** - Everything still works  
✅ **Optional enhancement** - Add LLM when you want better accuracy  
✅ **Gradual migration** - Upgrade at your own pace  
✅ **Backward compatible** - All scripts work with all file types  

Start with what you have, enhance when ready!
