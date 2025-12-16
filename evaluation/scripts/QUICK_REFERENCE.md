# TogoMCP Evaluation - Quick Reference Card

## 🚀 Getting Started (2 minutes)

```bash
cd evaluation/scripts
export ANTHROPIC_API_KEY="your-key"
./quick_start_evaluation.sh
```

Done! Review the output and generated report.

## 📋 File Guide

| File | Purpose | When to Use |
|------|---------|-------------|
| `quick_start_evaluation.sh` | Demo the complete system | First time, quick tests |
| `automated_test_runner.py` | Run baseline vs TogoMCP tests | Every evaluation |
| `results_analyzer.py` | Analyze test results | After running tests |
| `USAGE_GUIDE.md` | Complete workflow guide | Learning the system |
| `ANALYZER_README.md` | Analysis tool details | Understanding metrics |
| `example_questions.json` | Sample questions | Learning question format |
| `config.json` | MCP configuration | Customizing servers |

## 🎯 Common Commands

### Run Evaluation
```bash
python automated_test_runner.py questions.json
```

### Analyze Results
```bash
python results_analyzer.py evaluation_results.csv
```

### Detailed Analysis
```bash
python results_analyzer.py evaluation_results.csv -v
```

### Export Report
```bash
python results_analyzer.py evaluation_results.csv --export report.md
```

### Complete Workflow
```bash
# 1. Create/edit questions
vim my_questions.json

# 2. Run tests
python automated_test_runner.py my_questions.json -o results.csv

# 3. Analyze
python results_analyzer.py results.csv

# 4. Export
python results_analyzer.py results.csv --export analysis_$(date +%Y%m%d).md
```

## 📊 Question Categories (Need 3-5 of each)

| Category | Example Question | Tests |
|----------|-----------------|-------|
| **Precision** | "What is the UniProt ID for human BRCA1?" | Exact IDs, sequences |
| **Completeness** | "How many genes in GO:0006281?" | Counts, comprehensive lists |
| **Integration** | "Convert UniProt P04637 to NCBI Gene ID" | Cross-database linking |
| **Currency** | "SARS-CoV-2 pathways in Reactome?" | Recent information |
| **Specificity** | "MeSH ID for Erdheim-Chester disease?" | Niche topics |
| **Structured Query** | "Find all kinases in UniProt+ChEMBL" | Complex queries |

## 🎓 Understanding Results

### Success Patterns

| Pattern | Count | Meaning |
|---------|-------|---------|
| Both succeeded | High | Questions may be too easy |
| Only baseline succeeded | >0 | **Problem**: TogoMCP issues |
| Only TogoMCP succeeded | High | **Good**: Clear value-add |
| Both failed | >0 | Questions need revision |

### Assessment Categories

| Score | Category | Meaning | Action |
|-------|----------|---------|--------|
| 15-18 | CRITICAL | Essential value-add | Include in benchmarks |
| 9-14 | VALUABLE | Significant improvement | Include in eval set |
| 4-8 | MARGINAL | Minor improvement | Consider revising |
| 0-3 | REDUNDANT | No value-add | Exclude |

### Tool Usage

| Rate | Interpretation | Action |
|------|----------------|--------|
| >70% | Good coverage | Continue |
| 50-70% | Moderate | Add more database-focused questions |
| <50% | Too simple | Revise questions to require databases |

## ⚡ Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| API key error | `export ANTHROPIC_API_KEY="sk-ant-..."` |
| SDK not found | `pip install claude-agent-sdk anthropic` |
| MCP connection failed | Check server URL, network, online status |
| Tests failing | Review error messages, simplify questions |
| No tools used | Questions too simple, add database requirements |
| Low success rate | Simplify questions, check MCP config |

## 📈 Evaluation Scale Guide

### Small (5-10 questions)
- **Time**: 1-2 hours
- **Approach**: Automated + all manual templates
- **Purpose**: Initial testing, learning

### Medium (20-40 questions)
- **Time**: 3-6 hours
- **Approach**: Automated + manual for top questions
- **Purpose**: Comprehensive evaluation

### Large (50+ questions)
- **Time**: 1-2 days
- **Approach**: Automated + manual for CRITICAL only
- **Purpose**: Benchmark creation, paper

## 🎯 Best Practices Checklist

**Question Design:**
- [ ] Realistic (researchers would ask this)
- [ ] Verifiable (can check answer)
- [ ] Clear success criteria
- [ ] Covers all 6 categories
- [ ] Not trivial, not impossible

**Testing:**
- [ ] API key set
- [ ] Dependencies installed
- [ ] MCP servers configured
- [ ] Questions file validated
- [ ] Results saved with date

**Analysis:**
- [ ] Reviewed statistics
- [ ] Identified high-value questions
- [ ] Checked problematic questions
- [ ] Noted category gaps
- [ ] Followed recommendations

**Documentation:**
- [ ] Exported analysis report
- [ ] Saved questions file
- [ ] Noted configuration used
- [ ] Documented insights
- [ ] Version controlled

## 🔄 Iteration Workflow

```
Create Questions → Run Tests → Analyze → Review
       ↑                                    ↓
       └──────────── Revise ←───────────────┘
```

**Stop when:**
- 70%+ questions show TogoMCP value-add
- All categories have 3+ questions
- <10% problematic questions
- Clear benchmark candidates identified

## 📚 Documentation Priority

**Must Read (30 min):**
1. This card (you are here!)
2. `/scripts/USAGE_GUIDE.md` - Complete workflow
3. `/scripts/ANALYZER_README.md` - Understanding metrics

**Should Read (1 hour):**
4. `/EVALUATION_README.md` - System overview
5. `/togomcp_evaluation_rubric.md` - Methodology
6. `/scripts/README.md` - Automated testing details

**Reference:**
7. `/togomcp_evaluation_template.md` - Manual eval form
8. `/togomcp_quick_eval_form.md` - Quick manual form
9. `/scripts/MCP_CONFIGURATION.md` - MCP setup

## 💡 Pro Tips

1. **Start small**: 5 questions to learn, then scale
2. **Use git**: Version control everything
3. **Export often**: Save reports with dates
4. **Iterate fast**: Run → Analyze → Refine → Repeat
5. **Focus on CRITICAL**: These are your benchmarks
6. **Fix problems early**: Don't ignore failed tests
7. **Balance categories**: All 6 matter
8. **Document insights**: Future you will thank you

## 📞 Help Resources

**Local Files:**
- `USAGE_GUIDE.md` - Complete instructions
- `ANALYZER_README.md` - Analysis details
- `README.md` - Testing guide
- `NEW_TOOLS_SUMMARY.md` - What's new

**Quick Commands:**
```bash
# Show this card
cat QUICK_REFERENCE.md

# View detailed guides
less USAGE_GUIDE.md
less ANALYZER_README.md

# Run demo
./quick_start_evaluation.sh
```

## ✅ Success Checklist

You know you're successful when:
- [ ] Can run evaluation in <5 minutes
- [ ] Understand all metrics in analysis
- [ ] Can identify high-value questions
- [ ] Know how to iterate based on recommendations
- [ ] Have 20+ questions with 70%+ tool usage
- [ ] Clear CRITICAL questions for benchmarks
- [ ] <10% problematic questions
- [ ] Documented insights and recommendations

---

**Remember:**
- Quality > Quantity
- Iteration is key
- Document everything
- Ask for help when stuck

**You've got this!** 🎉
