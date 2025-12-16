# New Evaluation Tools - Complete Guide

## Overview

We've added three powerful tools to enhance your TogoMCP evaluation workflow:

1. **Question Validator** - Catch errors before running expensive API calls
2. **Question Generator** - Create high-quality questions faster
3. **Visual Dashboard** - Beautiful, interactive charts and visualizations

---

## 1. Question Validator 

### Purpose
Validates question files before running evaluations to catch errors early and save time/money.

### Features
- ✅ JSON format validation
- ✅ Required field checking
- ✅ Category balance analysis
- ✅ Quality checks (length, vague language, etc.)
- ✅ Duplicate detection
- ✅ API cost estimation
- ✅ Improvement recommendations

### Usage

**Basic validation:**
```bash
python validate_questions.py questions.json
```

**With cost estimate:**
```bash
python validate_questions.py questions.json --estimate-cost
```

**With recommendations:**
```bash
python validate_questions.py questions.json --recommendations
```

**Strict mode (warnings become errors):**
```bash
python validate_questions.py questions.json --strict
```

**All options:**
```bash
python validate_questions.py questions.json --estimate-cost --recommendations
```

### Example Output

```
======================================================================
QUESTION VALIDATOR REPORT
======================================================================
File: example_questions.json

⚠️  WARNINGS
----------------------------------------------------------------------
  • Categories with <3 questions: Completeness, Integration, Currency

ℹ️  INFORMATION
----------------------------------------------------------------------
  Loaded 10 questions
  Category distribution:
    ✓ Precision: 3
    ⚠ Completeness: 2
    ⚠ Integration: 2
    ⚠ Currency: 1

💰 COST ESTIMATE
----------------------------------------------------------------------
  Questions:           10
  Estimated tokens:    ~7,500
  Estimated cost:      $0.0525
  Cost per question:   $0.0052

💡 RECOMMENDATIONS
----------------------------------------------------------------------
  1. Add 2-3 more questions to these categories: Completeness, Integration
  2. Add expected answers to 3 questions for verification

======================================================================
✅ VALIDATION PASSED WITH WARNINGS
======================================================================
```

### What It Checks

**Errors (must fix):**
- Invalid JSON format
- Missing required fields (`question`)
- Invalid field types
- Empty question array

**Warnings (should address):**
- Missing recommended fields (`id`, `category`, `expected_answer`, `notes`)
- Unknown categories
- <3 questions per category
- Duplicate questions
- Very short/long questions
- Vague language ("thing", "stuff")

**Info (nice to know):**
- Category distribution
- Questions without `?` at end
- Total questions loaded

### Integration with Workflow

```bash
# 1. Create questions
vim my_questions.json

# 2. VALIDATE FIRST (saves time!)
python validate_questions.py my_questions.json --estimate-cost

# 3. Fix any errors

# 4. Run evaluation
python automated_test_runner.py my_questions.json

# 5. Analyze
python results_analyzer.py evaluation_results.csv
```

---

## 2. Question Generator

### Purpose
Helps create high-quality evaluation questions using templates and smart suggestions.

### Features
- 🎯 Category-specific templates
- 🎯 Interactive question builder
- 🎯 Batch generation for entities
- 🎯 Database-aware suggestions
- 🎯 Auto-generated variations

### Usage

**Interactive mode (default):**
```bash
python question_generator.py
```

**Show all templates:**
```bash
python question_generator.py --template
```

**Batch generate for entity:**
```bash
python question_generator.py --entity BRCA1 --batch 5
```

**Generate for specific compound:**
```bash
python question_generator.py --entity aspirin --batch 8
```

### Interactive Mode

When you run `python question_generator.py`:

```
======================================================================
TogoMCP Question Generator - Interactive Mode
======================================================================

Select category:
  1. Precision
  2. Completeness
  3. Integration
  4. Currency
  5. Specificity
  6. Structured Query
  0. Done (save and exit)

Your choice [1-6, 0 to exit]: 1

--- Precision Questions ---

Available templates:
  1. What is the UniProt ID for human BRCA1?
  2. What is the PubChem Compound ID for aspirin?
  3. What is the EC number for human hexokinase?
  4. What is the SMILES string for caffeine (PubChem CID 2519)?
  5. What is the MeSH descriptor ID for Alzheimer's disease?

Choose template [1-5]: 1

Template: What is the UniProt ID for human BRCA1?
Databases: UniProt, NCBI Gene, Ensembl

Enter your question (or press Enter to use example): What is the UniProt ID for human TP53?
Expected answer (optional): P04637
Notes (optional): Testing UniProt ID lookup for tumor suppressor

✓ Added question 1
  Q: What is the UniProt ID for human TP53?
```

### Available Templates

**Precision (5 templates):**
- ID lookups (UniProt, NCBI Gene, PubChem)
- EC numbers
- SMILES strings
- MeSH descriptors

**Completeness (4 templates):**
- Gene counts by GO term
- Reaction/pathway listings
- Structure counts
- Variant listings

**Integration (4 templates):**
- ID conversions
- Cross-database links
- Interaction queries
- Structure lookups

**Currency (3 templates):**
- Recent pathways
- Latest publications
- Newly added genes

**Specificity (3 templates):**
- Rare diseases
- Obscure organisms
- Niche compounds

**Structured Query (2 templates):**
- Complex multi-database queries
- Filtered searches

### Batch Generation Example

```bash
python question_generator.py --entity BRCA1 --batch 5
```

Generates:
```
Generating 5 questions for: BRCA1

  1. [Precision] What is the UniProt ID for human BRCA1?
  2. [Precision] What is the NCBI Gene ID for BRCA1?
  3. [Completeness] How many variants of BRCA1 are known?
  4. [Integration] Find PDB structures for BRCA1.
  5. [Integration] What pathways involve BRCA1?

✓ Generated 5 questions

Save to file [generated_questions.json]: brca1_questions.json
✓ Saved 5 questions to brca1_questions.json

Next steps:
  1. Review and edit brca1_questions.json
  2. Validate: python validate_questions.py brca1_questions.json
  3. Run evaluation: python automated_test_runner.py brca1_questions.json
```

### Tips

**Good entities for batch generation:**
- Genes: BRCA1, TP53, EGFR, KRAS
- Proteins: p53, insulin, hemoglobin
- Compounds: aspirin, caffeine, resveratrol
- Diseases: cancer, diabetes, Alzheimer's

**Customization:**
1. Use templates as starting points
2. Modify for your specific needs
3. Always add expected answers
4. Keep notes descriptive

---

## 3. Visual Dashboard

### Purpose
Creates beautiful, interactive HTML dashboards with charts from evaluation results.

### Features
- 📊 Success rate comparison charts
- 📊 Category performance breakdown
- 📊 Tool usage visualization
- 📊 Response time analysis
- 📊 Success pattern distribution
- 🎨 Professional, publication-ready design
- 🎨 Responsive layout (mobile-friendly)
- 🎨 No installation needed (pure HTML+JS)

### Usage

**Generate dashboard:**
```bash
python generate_dashboard.py evaluation_results.csv
```

**Custom output name:**
```bash
python generate_dashboard.py evaluation_results.csv -o my_dashboard.html
```

**Generate and open in browser:**
```bash
python generate_dashboard.py evaluation_results.csv --open
```

### What's Included

**Summary Statistics (top cards):**
- Total questions evaluated
- Baseline success rate
- TogoMCP success rate
- Unique tools used

**Charts:**

1. **Success Rate Comparison** - Stacked bar chart
   - Shows success/failure for baseline vs TogoMCP
   - Quick visual of overall performance

2. **Success Pattern Distribution** - Doughnut chart
   - Both succeeded (green)
   - Only baseline succeeded (orange)
   - Only TogoMCP succeeded (blue)
   - Both failed (red)

3. **Category Performance** - Grouped bar chart
   - Per-category success rates
   - Baseline vs TogoMCP comparison
   - Identify strong/weak categories

4. **Top Tools Used** - Horizontal bar chart
   - 10 most-used tools
   - Frequency of use
   - Shows which databases are most valuable

5. **Response Time Comparison** - Bar chart
   - Average response time
   - Baseline vs TogoMCP
   - Performance overhead visualization

### Example Dashboard

The generated HTML file includes:
- Interactive charts (hover for details)
- Professional gradient design
- Responsive grid layout
- Clear typography
- No external dependencies (works offline after generation)

### Viewing

**Option 1: Double-click the HTML file**
Opens in your default browser

**Option 2: Command line**
```bash
open evaluation_dashboard.html        # macOS
xdg-open evaluation_dashboard.html    # Linux
start evaluation_dashboard.html       # Windows
```

**Option 3: Auto-open**
```bash
python generate_dashboard.py results.csv --open
```

### Sharing

The HTML file is self-contained and can be:
- Emailed to colleagues
- Posted on websites
- Included in reports
- Embedded in presentations
- Committed to git repositories

---

## Complete Workflow with New Tools

### Beginner Workflow

```bash
# 1. Generate questions
python question_generator.py --entity BRCA1 --batch 10

# 2. Validate
python validate_questions.py generated_questions.json --estimate-cost

# 3. Fix any issues
vim generated_questions.json

# 4. Run evaluation
python automated_test_runner.py generated_questions.json

# 5. Analyze
python results_analyzer.py evaluation_results.csv

# 6. Visualize
python generate_dashboard.py evaluation_results.csv --open
```

### Advanced Workflow

```bash
# 1. Create custom questions
python question_generator.py  # Interactive mode

# 2. Validate with strict checking
python validate_questions.py my_questions.json --strict --recommendations

# 3. Estimate costs
python validate_questions.py my_questions.json --estimate-cost

# 4. Run evaluation
python automated_test_runner.py my_questions.json -c config.json

# 5. Detailed analysis
python results_analyzer.py evaluation_results.csv -v --export report.md

# 6. Create dashboard
python generate_dashboard.py evaluation_results.csv -o dashboard_v1.html

# 7. Review dashboard
open dashboard_v1.html

# 8. Iterate based on insights
python question_generator.py  # Add more questions
python automated_test_runner.py updated_questions.json
python generate_dashboard.py new_results.csv -o dashboard_v2.html
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Validate questions | `python validate_questions.py questions.json` |
| Estimate costs | `python validate_questions.py questions.json --estimate-cost` |
| Generate questions (interactive) | `python question_generator.py` |
| Generate questions (batch) | `python question_generator.py --entity BRCA1 --batch 5` |
| Show templates | `python question_generator.py --template` |
| Create dashboard | `python generate_dashboard.py results.csv` |
| Open dashboard | `python generate_dashboard.py results.csv --open` |

---

## Tips & Best Practices

### Question Validation
✅ **Do:**
- Validate before every evaluation run
- Check cost estimates for large sets
- Address all errors, most warnings
- Use strict mode for final validation

❌ **Don't:**
- Skip validation (wastes time/money)
- Ignore duplicate warnings
- Leave categories sparse

### Question Generation
✅ **Do:**
- Start with templates
- Customize for your domain
- Add expected answers
- Use batch mode for exploration
- Review and edit generated questions

❌ **Don't:**
- Use generated questions without review
- Forget to validate after generation
- Skip adding notes/context

### Dashboard
✅ **Do:**
- Generate dashboard after each run
- Share with team for collaboration
- Use for presentations
- Compare dashboards across iterations
- Save HTML files with dates

❌ **Don't:**
- Overwrite previous dashboards
- Forget to check all charts
- Skip visual review

---

## Troubleshooting

### Validator Issues

**"File not found"**
- Check file path
- Ensure .json extension

**"Invalid JSON"**
- Validate JSON syntax
- Check for missing commas/brackets
- Use JSON linter

**High cost estimate**
- Reduce number of questions
- Split into batches

### Generator Issues

**No output file**
- Check save location
- Verify write permissions

**Template not found**
- Use `--template` to see all options
- Check category spelling

### Dashboard Issues

**Empty charts**
- Verify CSV has data
- Check file path
- Ensure CSV from automated_test_runner

**Won't open in browser**
- Try double-clicking HTML file
- Check browser settings
- Use --open flag

---

## Examples

See the example files:
- `example_questions.json` - Sample question set
- `sample_evaluation_results.csv` - Sample results
- Test dashboard: Generated from sample data

---

## Next Steps

1. **Try the validator**: `python validate_questions.py example_questions.json`
2. **Generate questions**: `python question_generator.py --template`
3. **Create a dashboard**: `python generate_dashboard.py sample_evaluation_results.csv --open`

These tools work seamlessly with the existing evaluation system to make your workflow faster, easier, and more insightful!
