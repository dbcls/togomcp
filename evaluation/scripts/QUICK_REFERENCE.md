# TogoMCP Evaluation Scripts - Quick Reference

## ⚡ 30-Second Start

```bash
export ANTHROPIC_API_KEY="your-key"
./quick_start.sh
# OR manually:
python automated_test_runner.py example_questions.json
python compute_costs.py evaluation_results.csv
python results_analyzer.py evaluation_results.csv
python generate_dashboard.py evaluation_results.csv --open
```

## 🎯 Common Commands

### Run Evaluation
```bash
# Basic
python automated_test_runner.py questions.json

# With custom output
python automated_test_runner.py questions.json -o results.csv

# With config
python automated_test_runner.py questions.json -c config.json

# JSON format output
python automated_test_runner.py questions.json --format json

# Run all Q01-Q10 batches
./run_all_tests.sh
```

### Calculate Costs
```bash
# Basic cost analysis
python compute_costs.py results.csv

# Different model
python compute_costs.py results.csv --model claude-opus-4-20250514

# Export detailed report
python compute_costs.py results.csv --export cost_report.json

# Custom pricing
python compute_costs.py results.csv --pricing custom_pricing.json
```

### Validate Questions
```bash
# Basic validation
python validate_questions.py questions.json

# Strict mode
python validate_questions.py questions.json --strict

# With cost estimate
python validate_questions.py questions.json --estimate-cost
```

### Verify Questions
```bash
# Verify question set completeness (for Q01-Q10 batch)
python verify_questions.py
```

### Analyze Results
```bash
# Basic analysis
python results_analyzer.py results.csv

# Verbose (show all questions)
python results_analyzer.py results.csv -v

# Export report
python results_analyzer.py results.csv --export report.md
```

### Generate Dashboard
```bash
# Generate dashboard
python generate_dashboard.py results.csv

# Custom output path
python generate_dashboard.py results.csv -o dashboard.html

# Generate and open
python generate_dashboard.py results.csv --open
```

### Add LLM Evaluation
```bash
# Add LLM-based evaluation (requires Ollama)
python add_llm_evaluation.py results.csv

# With custom output
python add_llm_evaluation.py results.csv -o results_with_llm.csv

# Use different LLM model
python add_llm_evaluation.py results.csv --llm-model mistral

# Multiple files
python add_llm_evaluation.py Q01_out.csv Q02_out.csv Q03_out.csv
```

### Query Usage (Conceptual)
```bash
# Shows how to query Anthropic usage API
python query_anthropic_usage.py --start 2024-12-01 --end 2024-12-31
```

## 📊 Complete Workflow

```bash
# 1. Create questions file (see format below)
vim my_questions.json

# 2. Validate with cost estimate
python validate_questions.py my_questions.json --estimate-cost

# 3. Run evaluation
python automated_test_runner.py my_questions.json -o results_$(date +%Y%m%d).csv

# 4. Calculate actual costs
python compute_costs.py results_$(date +%Y%m%d).csv

# 5. Analyze results
python results_analyzer.py results_$(date +%Y%m%d).csv -v

# 6. Generate dashboard
python generate_dashboard.py results_$(date +%Y%m%d).csv --open

# 7. (Optional) Add LLM evaluation
python add_llm_evaluation.py results_$(date +%Y%m%d).csv

# 8. Export reports
python results_analyzer.py results_$(date +%Y%m%d).csv --export analysis_$(date +%Y%m%d).md
python compute_costs.py results_$(date +%Y%m%d).csv --export cost_$(date +%Y%m%d).json
```

## 📝 Question File Format

```json
[
  {
    "id": 1,
    "category": "Precision",
    "question": "What is the UniProt ID for human BRCA1?",
    "expected_answer": "P38398",
    "notes": "Test basic ID lookup"
  }
]
```

**Required**: `question`  
**Recommended**: `id`, `category`, `expected_answer`, `notes`

## 📂 Scripts at a Glance

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `automated_test_runner.py` | Run evaluations | questions.json | results.csv |
| `compute_costs.py` | Calculate costs | results.csv | cost breakdown |
| `results_analyzer.py` | Analyze results | results.csv | statistics + report.md |
| `validate_questions.py` | Validate questions | questions.json | validation report |
| `verify_questions.py` | Verify Q01-Q10 batch | (auto-detects) | verification report |
| `generate_dashboard.py` | Create dashboard | results.csv | dashboard.html |
| `add_llm_evaluation.py` | Add LLM evaluation | results.csv | enhanced results.csv |
| `query_anthropic_usage.py` | Query usage API | (API call) | usage data |
| `quick_start.sh` | Automated quickstart | - | runs full pipeline |
| `run_all_tests.sh` | Run Q01-Q10 batch | Q01-Q10.json | combined results |

## 🎓 Question Categories

| Category | Example | Purpose |
|----------|---------|---------|
| **Precision** | "What is UniProt ID for BRCA1?" | Exact IDs, values |
| **Completeness** | "How many genes in GO:0006281?" | Counts, lists |
| **Integration** | "Convert UniProt P04637 to Gene ID" | Cross-database |
| **Currency** | "SARS-CoV-2 pathways in Reactome?" | Recent info |
| **Specificity** | "MeSH ID for Erdheim-Chester?" | Niche topics |
| **Structured Query** | "Find all kinases in UniProt+ChEMBL" | Complex queries |

**Target**: 3-5 questions per category (or 2 per category for batch sets)

## 💰 Cost Information

### Typical Costs (Claude Sonnet 4)

| Evaluation Size | Baseline | TogoMCP | Total |
|----------------|----------|---------|-------|
| **12 questions** | $0.02 | $0.63 | **$0.65** |
| **24 questions** | $0.05 | $1.25 | **$1.30** |
| **120 questions** | $0.24 | $6.26 | **$6.50** |

**Per question**: ~$0.055 ($0.002 baseline + $0.053 TogoMCP)

### Cache Breakdown

TogoMCP uses **isolated sessions** for efficiency:
- Cache creation: ~8k tokens/question (@$3.75/MTok)
- Cache reads: ~50k tokens/question (@$0.30/MTok)
- No conversation accumulation
- Predictable costs

### Cost Commands

```bash
# Estimate before running
python validate_questions.py questions.json --estimate-cost

# Calculate after running
python compute_costs.py results.csv

# Export detailed breakdown
python compute_costs.py results.csv --export cost_report.json

# Check actual usage (conceptual)
python query_anthropic_usage.py --start 2024-12-01 --end 2024-12-31
```

## 📈 Understanding Results

### Value-Add Categories

| Score | Category | Meaning | Action |
|-------|----------|---------|--------|
| 15-18 | **CRITICAL** | Baseline failed, TogoMCP succeeded | Use for benchmarks |
| 9-14 | **VALUABLE** | Significant improvement | Include in eval |
| 4-8 | **MARGINAL** | Minor improvement | Consider revising |
| 0-3 | **REDUNDANT** | No improvement | Exclude |

### Success Patterns

| Pattern | Count | Interpretation |
|---------|-------|----------------|
| Both have expected | High | May be too easy |
| Only baseline | >0 | **Problem**: Check TogoMCP |
| Only TogoMCP | High | **Good**: Clear value-add |
| Neither | >0 | Revise questions |

### Tool Usage

| Rate | Meaning | Action |
|------|---------|--------|
| >70% | Excellent | Continue |
| 50-70% | Good | Add more DB-focused questions |
| <50% | Too simple | Revise questions |

## 🔧 Configuration

### config.json Structure

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

### Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Supported Models

| Model | Input/Output ($/MTok) | Cache Create | Cache Read |
|-------|-----------------------|--------------|------------|
| Sonnet 4 | $3.00 / $15.00 | $3.75 | $0.30 |
| Opus 4 | $15.00 / $75.00 | $18.75 | $1.50 |
| Haiku 4 | $0.80 / $4.00 | $1.00 | $0.08 |

## 🚨 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| API key error | `export ANTHROPIC_API_KEY="sk-ant-..."` |
| SDK not found | `pip install claude-agent-sdk anthropic` |
| MCP failed | Check URL, network, server status |
| No tools used | Questions too simple, add DB requirements |
| Low success | Simplify questions or check config |
| High costs | Check cache metrics with compute_costs.py |
| Ollama not found | Install Ollama for LLM evaluation |
| Model not found | `ollama pull llama3.2` |

## 📊 Output Files

### evaluation_results.csv

**Key Columns**:
- `baseline_has_expected`: Did baseline include expected answer?
- `togomcp_has_expected`: Did TogoMCP include expected answer?
- `baseline_actually_answered`: Did baseline try to answer (vs "I don't know")?
- `togomcp_cache_creation_input_tokens`: Cache creation tokens
- `togomcp_cache_read_input_tokens`: Cache read tokens
- `tools_used`: Comma-separated MCP tools used
- `value_add`: Assessment (CRITICAL/VALUABLE/MARGINAL/REDUNDANT)

### Enhanced Results (with LLM evaluation)

**Additional Columns**:
- `baseline_llm_match`: LLM judges baseline contains answer
- `baseline_llm_confidence`: LLM confidence (high/medium/low)
- `baseline_llm_explanation`: Brief explanation
- `togomcp_llm_match`: LLM judges TogoMCP contains answer
- `togomcp_llm_confidence`: LLM confidence
- `togomcp_llm_explanation`: Brief explanation
- `full_combined_baseline_found`: Token OR LLM match
- `full_combined_togomcp_found`: Token OR LLM match

### Cost Report (via compute_costs.py)

**Shows**:
- Baseline vs TogoMCP cost comparison
- Cache creation and read breakdown
- Costs by category
- Costs by value-add
- Per-question averages

### Analysis Report (via results_analyzer.py --export)

**Sections**:
- Overall Statistics
- Category Breakdown
- Success Patterns
- Value-Add Assessment
- Problematic Questions
- Recommendations

### dashboard.html

**Charts**:
- Has Expected Answer comparison
- Expected Answer pattern distribution
- Category performance
- Top tools used
- Response time comparison

## 💡 Pro Tips

1. **Use Quick Start**: Run `./quick_start.sh` for automated setup
2. **Batch Processing**: Use `./run_all_tests.sh` for Q01-Q10 files
3. **Estimate First**: Use `--estimate-cost` to budget before running
4. **Calculate After**: Run `compute_costs.py` to verify spending
5. **Start Small**: 5-10 questions to learn, then scale
6. **Use Dates**: Name outputs with dates (`results_20250117.csv`)
7. **Git Everything**: Version control questions, configs, and reports
8. **Focus on CRITICAL**: These show clearest value-add
9. **Check Tool Usage**: If <50%, questions may be too simple
10. **Monitor Costs**: Track spending across iterations
11. **Export Reports**: Save both cost and analysis reports
12. **LLM Evaluation**: Add semantic matching with `add_llm_evaluation.py`
13. **Iterate Fast**: Run → Calculate → Analyze → Refine → Repeat

## 🎯 Quality Checklist

**Good Question Set:**
- [ ] 3-5 questions per category (or 2 for batch)
- [ ] >70% tool usage rate
- [ ] >70% questions show TogoMCP value-add
- [ ] <10% problematic questions
- [ ] All questions have expected answers
- [ ] Clear CRITICAL questions identified
- [ ] Costs within budget

**Good Workflow:**
- [ ] Questions validated before running
- [ ] Cost estimated before running
- [ ] Results saved with dates
- [ ] Costs calculated after running
- [ ] Analysis reports exported
- [ ] Dashboard generated and reviewed
- [ ] (Optional) LLM evaluation added
- [ ] Insights documented
- [ ] Iterations tracked in git

## 📐 Evaluation Scale Guide

| Scale | Questions | Time | Cost (Sonnet 4) | Approach |
|-------|-----------|------|-----------------|----------|
| **Small** | 5-10 | 1-2h | ~$0.30 | Learn the system |
| **Medium** | 20-40 | 3-6h | ~$1.30 | Comprehensive eval |
| **Large** | 50+ | 1-2d | ~$3.00+ | Benchmark creation |
| **Batch** | 120 (10×12) | 1-2d | ~$6.50 | Full evaluation |

## 🔄 Iteration Loop

```
Create Questions → Validate (+ estimate cost) → Run Eval
       ↑                                            ↓
       |                                     Calculate Costs
       |                                            ↓
       └─────────── Refine ←────────── Analyze Results
                                              ↓
                                    (Optional) Add LLM Eval
```

**Stop When:**
- 70%+ questions show value-add
- All categories have 3+ questions
- <10% problematic questions
- Clear CRITICAL candidates identified
- Costs are within budget

## 🧪 LLM Evaluation Feature

### Prerequisites
```bash
# Install Ollama
# macOS:
brew install ollama

# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# Windows:
winget install Ollama.Ollama

# Download model
ollama pull llama3.2
```

### Usage
```bash
# Basic
python add_llm_evaluation.py results.csv

# Custom model
python add_llm_evaluation.py results.csv --llm-model mistral

# Multiple files
python add_llm_evaluation.py Q01_out.csv Q02_out.csv
```

### What It Does
- Uses generative LLM to judge if responses contain expected answers
- Provides semantic understanding beyond token matching
- Adds confidence levels and explanations
- Complements token-based matching

### Use Cases
- Catch paraphrased answers
- Understand context better
- Validate borderline matches
- Enhanced result analysis

## 📚 Quick Help

```bash
# View full README
cat README.md | less

# Show this card
cat QUICK_REFERENCE.md

# Check requirements
cat requirements.txt

# View example questions
cat example_questions.json | jq

# View question schema
cat question-schema.json | jq

# Check config
cat config.json | jq

# Get script help
python automated_test_runner.py --help
python compute_costs.py --help
python results_analyzer.py --help
python validate_questions.py --help
python add_llm_evaluation.py --help
```

## 🔗 Related Files

- **README.md**: Full documentation with cost analysis section
- **LLM_EVALUATION.md**: Guide to LLM-based evaluation
- **QUESTION_FORMAT.md**: Detailed question format specification
- **../README.md**: Main evaluation system overview
- **../QUESTION_DESIGN_GUIDE.md**: How to create questions
- **../PROJECT_STATUS.md**: Current progress and timeline
- **requirements.txt**: Python dependencies
- **config.json**: MCP configuration
- **example_questions.json**: Sample questions
- **question-schema.json**: JSON schema for validation

## ⚙️ Installation

```bash
# Quick start (recommended)
./quick_start.sh

# Or manual installation
pip install -r requirements.txt

# Or install individually
pip install claude-agent-sdk anthropic pandas

# For LLM evaluation
# Install Ollama (see LLM Evaluation section)
pip install ollama

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify installation
python -c "import anthropic, claude_agent_sdk, pandas; print('OK')"
```

## 🎨 Dashboard Features

**Metrics Displayed**:
- Total questions evaluated
- Baseline "has expected" rate
- TogoMCP "has expected" rate
- Unique tools used
- Total tool calls

**Charts**:
- Stacked bar: Has expected vs missing expected
- Doughnut: Pattern distribution (both/only baseline/only TogoMCP/neither)
- Bar: Category performance comparison
- Horizontal bar: Top 10 tools used
- Bar: Average response time comparison

## 📊 Cache Efficiency

The runner uses **isolated sessions**:
- Each question = fresh Claude session
- No conversation history between questions
- Stable cache costs (~50k read tokens per question)
- 46% cheaper than conversation accumulation

**Why it matters**:
- Predictable costs at scale
- No exponential growth
- Better reproducibility
- Cleaner methodology

## 📞 Getting Help

1. **Check README.md**: Full documentation with cost analysis
2. **Check LLM_EVALUATION.md**: LLM evaluation guide
3. **Check QUESTION_FORMAT.md**: Question format specification
4. **Run with --help**: `python script.py --help`
5. **Check examples**: Review `example_questions.json`
6. **Validate questions**: Find issues before running
7. **Calculate costs**: Understand your spending
8. **Review errors**: Error messages usually point to the issue

## ✅ Success Indicators

You're on the right track when:
- ✅ Evaluations complete without errors
- ✅ Costs match estimates (±10%)
- ✅ >70% tool usage rate
- ✅ Clear CRITICAL questions identified
- ✅ All categories represented
- ✅ Can explain each metric
- ✅ Dashboard shows clear patterns
- ✅ Iteration improves results
- ✅ Spending is within budget
- ✅ LLM evaluation adds insights (if used)

## 🎯 Cost Optimization Tips

1. **Remove REDUNDANT questions**: They don't show value-add
2. **Focus on CRITICAL**: Most bang for buck
3. **Batch evaluations**: Run multiple question sets together
4. **Use Haiku for testing**: Much cheaper for question development
5. **Track spending**: Monitor trends with compute_costs.py
6. **Plan ahead**: Use --estimate-cost before large runs
7. **Use quick_start.sh**: Automated pipeline saves time
8. **Batch process**: Use run_all_tests.sh for Q01-Q10

## 🔬 Advanced Features

### Batch Processing
```bash
# Process Q01-Q10 automatically
./run_all_tests.sh

# Edit batch range in script
vim run_all_tests.sh  # Change iend=10 to desired number
```

### Custom Pricing
```bash
# Create custom pricing file
cp custom_pricing_example.json my_pricing.json
vim my_pricing.json

# Use custom pricing
python compute_costs.py results.csv --pricing my_pricing.json
```

### Verify Question Batches
```bash
# Automatically checks Q01-Q10 batch
python verify_questions.py

# Verifies:
# - 120 total questions
# - 20 per category
# - All IDs 1-120 present
# - No duplicates
# - Correct structure
```

---

**Remember**:
- Quality > Quantity
- Estimate → Run → Calculate → Analyze → Iterate
- Start small, iterate fast
- Document everything
- Tool usage = question quality
- CRITICAL questions = your benchmarks
- Costs are predictable with isolated sessions
- LLM evaluation adds semantic understanding

**Need more details?** → Read [README.md](README.md), [LLM_EVALUATION.md](LLM_EVALUATION.md), [QUESTION_FORMAT.md](QUESTION_FORMAT.md)
