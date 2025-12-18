# TogoMCP Evaluation

**Automated evaluation suite for testing TogoMCP's biological database query capabilities.**

## 🚀 Quick Start (30 seconds)

```bash
cd scripts
export ANTHROPIC_API_KEY="your-key-here"
python automated_test_runner.py ../questions/Q01.json
python results_analyzer.py evaluation_results.csv
python generate_dashboard.py evaluation_results.csv --open
```

**First time here?** → Read the [5-minute overview](#5-minute-overview) below.

---

## 📁 What's Here

| Directory | What It Contains | When You Need It |
|-----------|------------------|------------------|
| **`scripts/`** | Automated evaluation tools | Running evaluations ⭐ |
| **`questions/`** | 120 pre-designed test questions | Understanding what's tested |
| **`exploration/`** | Database capability documentation | Reference material |
| **`results/`** | Evaluation output data | Analyzing results |
| **`archive/`** | Deprecated manual templates | Historical reference only |

**Key files**:
- **`README.md`** - Quick start guide (you are here)
- **`QUESTION_DESIGN_GUIDE.md`** - How to create evaluation questions
- **`PROJECT_STATUS.md`** - Current progress and timeline

---

## 5-Minute Overview

### What Is This?

This evaluation suite tests how well TogoMCP (Model Context Protocol for biological databases) improves Claude's ability to answer biology research questions.

**The Test**: Ask Claude the same question twice:
1. **Baseline**: Without access to database tools
2. **TogoMCP**: With access to 22 biological databases

**The Goal**: Measure the improvement when Claude can query real databases.

### What's Been Done?

✅ **Phase 1**: Explored 22 biological databases (UniProt, PubChem, GO, etc.)  
✅ **Phase 2**: Created 120 evaluation questions across 6 categories  
🔄 **Phase 3**: Running automated evaluations (24/120 complete)  
📊 **Phase 4**: Comprehensive analysis (pending)

**See**: [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for detailed progress.

### The 120 Questions

Questions test 6 different capabilities:

| Category | Tests | Example |
|----------|-------|---------|
| **Precision** | Exact IDs, values | "What is the UniProt ID for human BRCA1?" |
| **Completeness** | Counts, exhaustive lists | "How many genes in GO term DNA repair?" |
| **Integration** | Cross-database linking | "Convert UniProt P04637 to Gene ID" |
| **Currency** | Recent/updated data | "SARS-CoV-2 pathways in Reactome?" |
| **Specificity** | Niche, specialized topics | "MeSH ID for Erdheim-Chester disease?" |
| **Structured Query** | Complex multi-step queries | "Find all kinases with ChEMBL data" |

**See**: [`questions/SUMMARY.md`](questions/SUMMARY.md) for complete details.

### The 22 Databases

**Proteins & Genes**: UniProt, PDB, NCBI Gene, Ensembl, DDBJ, Taxonomy  
**Chemicals**: ChEBI, ChEMBL, PubChem, Rhea  
**Pathways**: Reactome, GO  
**Clinical**: ClinVar, MedGen, MONDO, NANDO  
**Literature**: MeSH, PubMed, PubTator  
**Specialized**: BacDive, MediaDive, GlyCosmos

**See**: [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md) for database capabilities.

---

## 🎯 Common Use Cases

### I want to create evaluation questions

```bash
cat QUESTION_DESIGN_GUIDE.md  # Read the question design guide
cat questions/Q01.json | jq   # See examples
```

**Full guide**: [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md)

### I want to run evaluations

```bash
cd scripts
cat README.md  # Read the complete guide
python automated_test_runner.py ../questions/Q03.json
```

**Full documentation**: [`scripts/README.md`](scripts/README.md)  
**Quick commands**: [`scripts/QUICK_REFERENCE.md`](scripts/QUICK_REFERENCE.md)

### I want to understand the questions

```bash
cat questions/SUMMARY.md
cat questions/Q01.json | jq
```

Each question includes:
- Natural language question text
- Expected answer for verification
- Category (Precision/Completeness/etc.)
- Detailed notes explaining the test

### I want to see what databases can do

```bash
cat exploration/00_SUMMARY.md  # Overview of all 22 databases
cat exploration/uniprot_exploration.md  # Deep dive on specific database
```

Each database report includes:
- 5+ search query examples
- 3+ SPARQL query examples
- Capabilities and limitations
- Question design opportunities

### I want to check project progress

```bash
cat PROJECT_STATUS.md
```

Shows:
- What's complete (exploration, questions)
- What's in progress (evaluation)
- What's next (analysis)
- Detailed metrics and timeline

### I want to analyze results

```bash
cd scripts
python results_analyzer.py ../results/results.csv -v
python generate_dashboard.py ../results/results.csv --open
```

Get:
- Success rate comparisons
- Tool usage statistics
- Category performance breakdown
- Interactive HTML dashboard

---

## 📚 Documentation Guide

**Start here** (pick one based on your goal):

| I want to... | Read this |
|--------------|-----------|
| **Create evaluation questions** | [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md) |
| **Run evaluations** | [`scripts/README.md`](scripts/README.md) |
| **Quick command reference** | [`scripts/QUICK_REFERENCE.md`](scripts/QUICK_REFERENCE.md) |
| **Check project status** | [`PROJECT_STATUS.md`](PROJECT_STATUS.md) |
| **Learn about questions** | [`questions/SUMMARY.md`](questions/SUMMARY.md) |
| **Learn about databases** | [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md) |

---

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Anthropic API key
- ~30 minutes for small evaluation (10 questions)
- ~6-8 hours for full evaluation (120 questions)

### Setup

```bash
# 1. Install dependencies
cd scripts
pip install -r requirements.txt

# 2. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Verify setup
python -c "import anthropic; print('Ready!')"

# 4. Test with example
python automated_test_runner.py example_questions.json
```

**Troubleshooting**: See [`scripts/README.md`](scripts/README.md#troubleshooting)

---

## 📊 Current Status

**Last Updated**: 2025-12-18

| Phase | Status | Progress |
|-------|--------|----------|
| Database Exploration | ✅ Complete | 22/22 databases (100%) |
| Question Generation | ✅ Complete | 120/120 questions (100%) |
| Automated Evaluation | 🔄 In Progress | 24/120 questions (20%) |
| Analysis & Reporting | 📊 Pending | Awaiting full evaluation |

**Next**: Complete evaluation for Q03-Q10 (96 questions)

**See**: [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for detailed breakdown.

---

## 💡 Key Concepts

### Baseline vs TogoMCP

**Baseline**: Claude answers using only training knowledge (cutoff: January 2025)
- May be outdated
- No access to specific database IDs
- Can't verify current data
- Limited to general knowledge

**TogoMCP**: Claude answers with database access via MCP
- Current, verified data
- Exact IDs and values
- Cross-database integration
- Comprehensive results

### Value-Add Categories

Questions are automatically scored:

- **CRITICAL** (15-18 points): Essential improvement, use for benchmarks
- **VALUABLE** (9-14 points): Significant improvement, include in evaluation
- **MARGINAL** (4-8 points): Minor improvement, consider revising
- **REDUNDANT** (0-3 points): No improvement, exclude

**Goal**: Identify CRITICAL questions that clearly demonstrate TogoMCP's value.

### Success Patterns

After evaluation, each question falls into one of four patterns:

| Pattern | Meaning | Action |
|---------|---------|--------|
| **Both have expected** | Both answered correctly | Question may be too easy |
| **Only baseline** | TogoMCP failed | Check configuration |
| **Only TogoMCP** | Clear value-add! | **Keep this question** |
| **Neither** | Both failed | Revise or clarify question |

---

## 🔬 Example Workflow

### Complete Evaluation for One Question Set

```bash
# 1. Validate questions
cd scripts
python validate_questions.py ../questions/Q03.json --estimate-cost

# 2. Run evaluation
python automated_test_runner.py ../questions/Q03.json -o ../results/Q03_out.csv

# 3. Analyze results
python results_analyzer.py ../results/Q03_out.csv -v

# 4. Generate dashboard
python generate_dashboard.py ../results/Q03_out.csv --open

# 5. Review and document findings
# (Check dashboard for insights, identify high-value questions)
```

**Time**: ~30-45 minutes for 12 questions  
**Cost**: ~$0.15-0.30 (Claude Sonnet 4)

---

## 🎓 Learning Path

**New to this project?** Follow this sequence:

1. **Read this README** (you're here!) - 5 min
2. **Check [`PROJECT_STATUS.md`](PROJECT_STATUS.md)** - Understand progress - 5 min
3. **Browse [`questions/SUMMARY.md`](questions/SUMMARY.md)** - See what's tested - 10 min
4. **Read [`scripts/README.md`](scripts/README.md)** - Learn the tools - 20 min
5. **Run a test evaluation** - Try Q01.json - 30 min
6. **Review results** - Analyze what happened - 15 min

**Total**: ~90 minutes to full understanding

**Want details on databases?** See [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md)  
**Want to create questions?** See [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md)

---

## 🚨 Common Questions

### Why is evaluation only 20% complete?

The automated evaluation is compute-intensive:
- Each question requires 2 API calls (baseline + TogoMCP)
- Full evaluation = 240 API calls
- Takes 6-8 hours + ~$2-3 in API costs

We ran Q01-Q02 as validation. Q03-Q10 are ready to run.

### Can I add my own questions?

Yes! See [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md) for the complete guide.

Quick example:

```json
{
  "id": 121,
  "category": "Precision",
  "question": "Your question here",
  "expected_answer": "Expected result",
  "notes": "Why this tests database access"
}
```

Then validate and run:

```bash
python validate_questions.py my_questions.json
python automated_test_runner.py my_questions.json
```

### What happened to the manual templates?

They've been archived to `archive/manual_evaluation/`. The automated scripts replaced the manual workflow for consistency and reproducibility.

**Still accessible** if you need them for special cases.

### How do I interpret results?

Key metrics:
- **has_expected**: Did the answer include the expected result?
- **tools_used**: Which MCP tools were called?
- **value_add**: CRITICAL/VALUABLE/MARGINAL/REDUNDANT

**See**: [`scripts/README.md`](scripts/README.md#understanding-results) for details.

---

## 🤝 Contributing

### Adding Questions
1. Read [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md)
2. Follow format in existing JSON files
3. Use `validate_questions.py` to check
4. Ensure expected answers are verifiable

### Improving Documentation
1. Keep README.md concise (entry point)
2. Put details in specific docs (scripts/README.md, QUESTION_DESIGN_GUIDE.md)
3. Update PROJECT_STATUS.md when progress changes
4. Add examples to help users

### Reporting Issues
- Missing database functionality? Document in exploration reports
- Question problems? Note in question SUMMARY.md
- Script bugs? See scripts/README.md for troubleshooting

---

## 📈 Next Steps

**If you're here to use the evaluation suite**:
1. Install dependencies: `pip install -r scripts/requirements.txt`
2. Read the full guide: [`scripts/README.md`](scripts/README.md)
3. Run your first evaluation: Start with Q01.json
4. Analyze results and iterate

**If you're here to understand the project**:
1. Check status: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
2. Review questions: [`questions/SUMMARY.md`](questions/SUMMARY.md)
3. Explore databases: [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md)
4. Learn question design: [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md)

**If you're here to complete the evaluation**:
1. Run Q03-Q10: See [`scripts/QUICK_REFERENCE.md`](scripts/QUICK_REFERENCE.md)
2. Combine results: Use `results/combine_csv.py`
3. Analyze: `results_analyzer.py` + `generate_dashboard.py`
4. Document findings: Update PROJECT_STATUS.md

---

## 📞 Support

**For question design**: [`QUESTION_DESIGN_GUIDE.md`](QUESTION_DESIGN_GUIDE.md)  
**For script usage**: [`scripts/README.md`](scripts/README.md)  
**For question format**: [`scripts/QUESTION_FORMAT.md`](scripts/QUESTION_FORMAT.md)  
**For database info**: [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md)  
**For project status**: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)

---

## 📄 License

This evaluation tooling follows the same license as the main TogoMCP project.

---

**Last Updated**: 2025-12-18  
**Version**: 2.0 (Automated Evaluation)  
**Status**: Foundation Complete ✅ | Evaluation In Progress 🔄

**Ready to start?** → Pick your path above and dive in!
