# Unified Analysis Scripts - Quick Reference

## 🆕 New Enhanced Scripts

### results_analyzer_unified.py

**Replaces**: `results_analyzer.py`  
**Status**: Recommended for all new analyses

**What's New**:
- ✅ Auto-detects evaluation method (pattern/LLM/combined)
- ✅ Supports both simple pattern matching AND LLM evaluation
- ✅ Shows method comparison when both available
- ✅ Displays LLM confidence statistics
- ✅ Backward compatible with old results files

**Usage**:
```bash
# Auto-detect mode (recommended)
python results_analyzer_unified.py results.csv

# Works with LLM-enhanced results
python results_analyzer_unified.py results_with_llm.csv

# Force specific mode
python results_analyzer_unified.py results.csv --mode pattern
python results_analyzer_unified.py results_with_llm.csv --mode llm
python results_analyzer_unified.py results_with_llm.csv --mode combined
```

### generate_dashboard_unified.py

**Replaces**: `generate_dashboard.py`  
**Status**: Recommended for all new dashboards

**What's New**:
- ✅ Auto-detects evaluation method
- ✅ Additional charts for LLM evaluation
- ✅ Method comparison visualization
- ✅ LLM confidence distribution chart
- ✅ Value-add distribution chart
- ✅ Visual mode badges
- ✅ Backward compatible with old results

**Usage**:
```bash
# Auto-detect and open
python generate_dashboard_unified.py results.csv --open

# Works with LLM-enhanced results
python generate_dashboard_unified.py results_with_llm.csv --open

# Force specific mode
python generate_dashboard_unified.py results.csv --mode pattern
```

### add_llm_evaluation.py

**Purpose**: Enhance pattern-matching results with LLM semantic evaluation

**Benefits**:
- Catches paraphrased answers pattern matching misses
- Typically finds 10-20% more correct answers
- No need to re-run tests
- Adds semantic understanding

**Requirements**:
```bash
# One-time setup
# 1. Install Ollama from https://ollama.ai
# 2. Pull model
ollama pull llama3.2
# 3. Install Python package
pip install ollama
```

**Usage**:
```bash
# Enhance existing results
python add_llm_evaluation.py results.csv
# → Creates results_with_llm.csv

# Then analyze with unified scripts
python results_analyzer_unified.py results_with_llm.csv
python generate_dashboard_unified.py results_with_llm.csv --open
```

## 📊 Quick Workflow Comparison

### Old Workflow (Pattern Matching Only)
```bash
# 1. Run evaluation
python automated_test_runner.py questions.json

# 2. Analyze (pattern matching)
python results_analyzer.py results.csv

# 3. Generate dashboard
python generate_dashboard.py results.csv --open
```

### New Workflow (Enhanced with LLM)
```bash
# 1. Run evaluation
python automated_test_runner.py questions.json

# 2. Add LLM evaluation (optional but recommended)
python add_llm_evaluation.py results.csv

# 3. Analyze (combined evaluation)
python results_analyzer_unified.py results_with_llm.csv

# 4. Generate enhanced dashboard
python generate_dashboard_unified.py results_with_llm.csv --open
```

### Minimal Migration
```bash
# No changes needed! Unified scripts work with old files too:
python results_analyzer_unified.py results.csv  # Auto-detects pattern mode
python generate_dashboard_unified.py results.csv --open
```

## 🎯 When to Use What

| Scenario | Script | Mode |
|----------|--------|------|
| Quick analysis, no LLM | `results_analyzer_unified.py` | Auto (pattern) |
| Most accurate evaluation | `add_llm_evaluation.py` + unified scripts | Combined |
| Backward compatibility | Unified scripts | Auto-detect |
| Just pattern matching | Old scripts OR unified with `--mode pattern` | Pattern |
| Compare methods | `results_analyzer_unified.py` on LLM results | Combined |

## 📚 Documentation

- **[UNIFIED_ANALYSIS.md](UNIFIED_ANALYSIS.md)** - Comprehensive unified scripts guide
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - How to migrate from pattern-only
- **[LLM_EVALUATION.md](LLM_EVALUATION.md)** - LLM evaluation details
- **[README.md](README.md)** - Main scripts documentation

## ✅ Compatibility Matrix

| File Type | Old Scripts | Unified Scripts |
|-----------|-------------|-----------------|
| `results.csv` (pattern only) | ✅ Full support | ✅ Full support (auto pattern mode) |
| `results_with_llm.csv` (LLM) | ⚠️ Ignores LLM columns | ✅ Full support (auto combined mode) |

## 🚀 Getting Started

**If you're new**: Use the unified scripts from the start
```bash
python results_analyzer_unified.py results.csv
```

**If you have existing results**: Unified scripts work out of the box
```bash
python results_analyzer_unified.py your_old_results.csv
```

**If you want LLM evaluation**: Add it anytime
```bash
python add_llm_evaluation.py your_old_results.csv
python results_analyzer_unified.py your_old_results_with_llm.csv
```

## 💡 Key Benefits

### Unified Scripts
- ✅ **Backward compatible**: Works with all existing results
- ✅ **Auto-detection**: No manual mode selection needed
- ✅ **Future-proof**: Supports both evaluation methods
- ✅ **Enhanced analysis**: Better insights when LLM data available

### LLM Evaluation
- ✅ **More accurate**: Semantic understanding vs exact matching
- ✅ **Fewer false negatives**: Catches paraphrased answers
- ✅ **Confidence tracking**: Know how sure the LLM is
- ✅ **No re-running**: Apply to existing results

## 🔄 Migration Strategy

1. **Immediate**: Start using unified scripts (no changes needed)
2. **Optional**: Add LLM evaluation when you want better accuracy
3. **Gradual**: Keep old scripts until comfortable with new ones
4. **Eventually**: Rely primarily on unified + LLM workflow

**No breaking changes, migrate at your own pace!**
