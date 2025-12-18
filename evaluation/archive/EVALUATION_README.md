# TogoMCP Evaluation Suite

This directory contains automated tools for evaluating TogoMCP's biological database query capabilities.

## 🚀 Quick Start

```bash
cd scripts
export ANTHROPIC_API_KEY="your-key"
python automated_test_runner.py ../questions/Q01.json
python results_analyzer.py evaluation_results.csv
python generate_dashboard.py evaluation_results.csv --open
```

**Complete guide**: See [`scripts/README.md`](scripts/README.md)

---

## 📁 Directory Structure

```
evaluation/
├── README.md                    # This file - start here
├── scripts/                     # Automated evaluation tools ⭐ MAIN WORKFLOW
│   ├── README.md               # Complete automation guide
│   ├── QUICK_REFERENCE.md      # Quick command reference
│   ├── automated_test_runner.py # Run baseline vs TogoMCP tests
│   ├── results_analyzer.py     # Analyze evaluation results
│   ├── generate_dashboard.py   # Create interactive dashboards
│   ├── validate_questions.py   # Validate question files
│   └── ...                     # Other utilities
├── questions/                   # 120 evaluation questions
│   ├── Q01.json - Q10.json     # 10 files × 12 questions each
│   └── SUMMARY.md              # Question creation details
├── exploration/                 # Database exploration reports (reference)
│   ├── 00_SUMMARY.md           # Database capabilities overview
│   ├── 00_PROGRESS.md          # Exploration progress tracker
│   └── *_exploration.md        # 22 database reports
├── results/                     # Evaluation results (generated)
│   ├── Q01_out.csv, Q02_out.csv # Partial results
│   └── README.md               # Results documentation
└── archive/                     # Deprecated files
    └── manual_evaluation/      # Old manual templates (archived)
```

---

## What's What

### 🚀 **Main Workflow** → `scripts/`

**Start here** for running evaluations.

The automated evaluation system:
- Runs baseline Claude vs TogoMCP-enhanced comparisons
- Automatically evaluates correctness and tool usage
- Generates statistical analysis and reports
- Creates interactive HTML dashboards
- Provides reproducible, consistent results

**See**: [`scripts/README.md`](scripts/README.md) for complete documentation

**Quick Reference**: [`scripts/QUICK_REFERENCE.md`](scripts/QUICK_REFERENCE.md)

---

### 📝 **Questions** → `questions/`

120 pre-designed evaluation questions covering:
- **6 categories**: Precision, Completeness, Integration, Currency, Specificity, Structured Query
- **22 databases**: All explored TogoMCP databases
- **10 JSON files**: Q01-Q10.json (12 questions each)

Each question includes:
- Natural language question text
- Expected answer for verification
- Category classification
- Detailed notes and rationale

**See**: [`questions/SUMMARY.md`](questions/SUMMARY.md) for details

---

### 📚 **Reference Material** → `exploration/`

Comprehensive database capability documentation:
- **22 exploration reports**: One per database
- **Search query examples**: 5+ queries per database
- **SPARQL examples**: 3+ queries per database
- **Database characteristics**: Coverage, limitations, best practices

Used during question design to ensure:
- Questions target actual database capabilities
- Expected answers are verifiable
- Query complexity is appropriate

**See**: [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md) for overview

---

### 📊 **Results** → `results/`

Generated evaluation data (work in progress):
- Currently: Q01-Q02 evaluated (24 questions)
- Remaining: Q03-Q10 pending (96 questions)

Results include:
- Baseline performance metrics
- TogoMCP performance metrics
- Tool usage statistics
- Correctness evaluation
- Response time and token usage

**See**: [`results/README.md`](results/README.md) for details

---

## 📖 Evaluation Workflow

### Step 1: Understand the Questions

```bash
# Review question distribution and design
cat questions/SUMMARY.md

# Examine a specific question set
cat questions/Q01.json | jq
```

### Step 2: Run Evaluation

```bash
cd scripts

# Validate questions first
python validate_questions.py ../questions/Q01.json --estimate-cost

# Run evaluation
python automated_test_runner.py ../questions/Q01.json -o ../results/Q01_out.csv
```

### Step 3: Analyze Results

```bash
# Generate statistics
python results_analyzer.py ../results/Q01_out.csv -v

# Create interactive dashboard
python generate_dashboard.py ../results/Q01_out.csv --open
```

### Step 4: Review and Iterate

Based on results:
- Identify CRITICAL questions (clear TogoMCP value-add)
- Review problematic questions
- Refine question set if needed
- Scale to remaining question sets

---

## 📊 Current Status

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for detailed progress.

**Summary**:
- ✅ **Exploration**: 22 databases documented (100% complete)
- ✅ **Questions**: 120 questions ready (100% complete)
- 🔄 **Evaluation**: 2/10 question sets complete (20% complete)
- 📊 **Analysis**: Pending full evaluation

**Next**: Complete automated evaluation for Q03-Q10

---

## 🎯 Key Features

### Automated Evaluation
- **Consistent testing**: Same prompts, same methodology
- **Automatic scoring**: Has expected answer detection
- **Tool tracking**: Which MCP tools were used
- **Performance metrics**: Response time, token usage
- **Reproducible**: Same questions → same results

### Comprehensive Analysis
- **Success patterns**: Both/baseline only/TogoMCP only/neither
- **Category breakdown**: Performance by question type
- **Value-add assessment**: CRITICAL/VALUABLE/MARGINAL/REDUNDANT
- **Tool usage stats**: Most-used tools, usage rates
- **Recommendations**: Actionable insights for improvement

### Visual Dashboards
- **Interactive charts**: Success rates, patterns, categories
- **Tool visualization**: Usage frequency and distribution
- **Performance comparison**: Baseline vs TogoMCP metrics
- **Export-ready**: HTML dashboards for sharing

---

## 📚 Documentation Guide

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **This file** | Overview and quick start | First time here |
| [`scripts/README.md`](scripts/README.md) | Complete automation guide | Before running evaluations |
| [`scripts/QUICK_REFERENCE.md`](scripts/QUICK_REFERENCE.md) | Quick command reference | During daily use |
| [`questions/SUMMARY.md`](questions/SUMMARY.md) | Question design details | Understanding the question set |
| [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md) | Database capabilities | Designing new questions |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Project progress tracker | Checking overall status |
| [`results/README.md`](results/README.md) | Results documentation | Working with evaluation data |

---

## 🔧 Requirements

- Python 3.8+
- Anthropic API key
- Dependencies: See [`scripts/requirements.txt`](scripts/requirements.txt)

```bash
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## 🎓 Question Categories Explained

| Category | Purpose | Example |
|----------|---------|---------|
| **Precision** | Exact IDs, values, sequences | "What is the UniProt ID for human BRCA1?" |
| **Completeness** | Counts, exhaustive lists | "How many genes are in GO:0006281?" |
| **Integration** | Cross-database linking | "Convert UniProt P04637 to NCBI Gene ID" |
| **Currency** | Recent/updated information | "What SARS-CoV-2 pathways are in Reactome?" |
| **Specificity** | Niche, specialized queries | "What is the MeSH ID for Erdheim-Chester disease?" |
| **Structured Query** | Complex multi-step queries | "Find all human kinases with ChEMBL compounds" |

Each category has **20 questions** distributed across the 120-question set.

---

## 📈 Understanding Results

### Value-Add Categories

Questions are automatically categorized based on improvement:

- **CRITICAL (15-18 points)**: Baseline failed, TogoMCP succeeded → Use for benchmarks
- **VALUABLE (9-14 points)**: Significant improvement → Include in evaluation
- **MARGINAL (4-8 points)**: Minor improvement → Consider revising
- **REDUNDANT (0-3 points)**: No improvement → Exclude

### Success Patterns

| Pattern | Interpretation | Action |
|---------|----------------|--------|
| Both have expected | May be too easy | Consider more complex questions |
| Only baseline | TogoMCP failed | Check configuration, tool availability |
| Only TogoMCP | **Good!** Clear value-add | Keep this question |
| Neither | Too hard or unclear | Revise question or expected answer |

**See**: [`scripts/README.md`](scripts/README.md) for detailed metrics explanation

---

## 🗂️ Legacy Files

Manual evaluation templates have been **archived** to:
- `archive/manual_evaluation/`

These were used before automation was implemented. The current workflow uses automated Python scripts for consistent, reproducible evaluation.

**See**: [`archive/manual_evaluation/README.md`](archive/manual_evaluation/README.md) for details

---

## 🤝 Contributing

When modifying the evaluation suite:

1. **Questions**: Follow format in existing JSON files
2. **Scripts**: Update both README.md and QUICK_REFERENCE.md
3. **Documentation**: Keep PROJECT_STATUS.md current
4. **Results**: Document methodology changes

---

## 📞 Support

- **Script usage**: See [`scripts/README.md`](scripts/README.md)
- **Question format**: See [`scripts/QUESTION_FORMAT.md`](scripts/QUESTION_FORMAT.md)
- **Validation errors**: Run `validate_questions.py` first
- **API issues**: Check `ANTHROPIC_API_KEY` environment variable

---

**Last Updated**: 2025-12-18  
**Version**: 2.0 (Automated Evaluation)  
**Status**: Exploration ✅ | Questions ✅ | Evaluation 🔄 | Analysis 📊 Pending
