# TogoMCP Evaluation Documentation Suite

This directory contains a complete set of templates and tools for evaluating TogoMCP's capabilities.

## Files Overview

### 1. `togomcp_evaluation_rubric.md`
**Purpose:** The main evaluation framework and methodology

**Contents:**
- Question design criteria
- Six question categories (Precision, Completeness, Integration, Currency, Specificity, Structured Query)
- Scoring rubric (6 dimensions, 0-3 scale)
- Assessment categories (CRITICAL, VALUABLE, MARGINAL, REDUNDANT)
- Evaluation protocol
- Recommended evaluation set composition

**Use this to:** Understand the evaluation methodology and design your questions

---

### 2. `togomcp_evaluation_template.md`
**Purpose:** Comprehensive template for detailed evaluation of individual questions

**Contents:**
- Full question documentation
- Baseline vs TogoMCP comparison
- Detailed scoring with justifications
- Verification section
- Decision tracking
- Summary statistics section

**Use this to:** Conduct thorough evaluations with full documentation

**Best for:** 
- Important benchmark questions
- Publication-quality evaluations
- Detailed case studies
- When you need comprehensive records

---

### 3. `togomcp_quick_eval_form.md`
**Purpose:** Simplified one-page evaluation form

**Contents:**
- Condensed question/answer sections
- Quick scoring checkboxes
- Minimal documentation fields

**Use this to:** Rapidly evaluate multiple questions

**Best for:**
- Initial screening of candidate questions
- Quick comparisons
- When time is limited
- Pilot testing

---

### 4. `togomcp_evaluation_tracker.csv`
**Purpose:** Spreadsheet-ready data tracking

**Contents:**
- CSV format with all essential fields
- One row per question
- Ready to import into Excel/Google Sheets

**Use this to:** Track and analyze evaluations at scale

**Best for:**
- Managing 20+ evaluations
- Statistical analysis
- Creating charts/graphs
- Sharing results with team
- Progress tracking

---

### 5. `togomcp_evaluation_tracker.md`
**Purpose:** Instructions for the CSV tracker

**Contents:**
- Usage instructions
- Column definitions
- Analysis tips
- Suggestions for additional columns

---

## Recommended Workflow

### For Small-Scale Evaluation (5-10 questions)
1. Read `togomcp_evaluation_rubric.md`
2. Design your questions using the rubric criteria
3. Use `togomcp_evaluation_template.md` for each question
4. Compile results in a summary document

### For Medium-Scale Evaluation (10-30 questions)
1. Read `togomcp_evaluation_rubric.md`
2. Design your questions
3. Use `togomcp_quick_eval_form.md` for initial screening
4. Use `togomcp_evaluation_template.md` for promising questions
5. Track all results in `togomcp_evaluation_tracker.csv`
6. Analyze trends in spreadsheet

### For Large-Scale Evaluation (30+ questions)
1. Read `togomcp_evaluation_rubric.md`
2. Design comprehensive question set
3. Use `togomcp_quick_eval_form.md` for all questions
4. Track in `togomcp_evaluation_tracker.csv` from the start
5. Use `togomcp_evaluation_template.md` only for top performers (CRITICAL category)
6. Perform statistical analysis on CSV data

---

## Quick Start Guide

### Step 1: Design Questions
Using `togomcp_evaluation_rubric.md`, create questions that:
- [ ] Are biologically realistic
- [ ] Have testable distinctions
- [ ] Have appropriate complexity
- [ ] Have clear success criteria
- [ ] Cover multiple categories

### Step 2: Set Up Tracking
- [ ] Open `togomcp_evaluation_tracker.csv` in your spreadsheet tool
- [ ] Customize columns if needed
- [ ] Create one row per question

### Step 3: Conduct Evaluations
For each question:
1. Get baseline answer (no tools)
2. Get TogoMCP answer (with tools)
3. Score using rubric dimensions
4. Document in template or CSV
5. Make inclusion decision

### Step 4: Analyze Results
- [ ] Calculate score distributions
- [ ] Check category coverage
- [ ] Identify CRITICAL questions
- [ ] Remove REDUNDANT questions
- [ ] Document key insights

### Step 5: Refine
- [ ] Revise low-performing questions
- [ ] Fill gaps in coverage
- [ ] Verify surprising results
- [ ] Finalize evaluation set

---

## Tips for Success

### Writing Good Questions
- **Be specific:** "What is the UniProt ID..." not "Tell me about..."
- **Be realistic:** Ask what researchers actually need
- **Be verifiable:** You should be able to check the answer
- **Avoid overlap:** Each question should test something distinct

### Conducting Fair Comparisons
- **Same question:** Use identical wording for baseline vs TogoMCP
- **Clear instructions:** For baseline, explicitly say "no database tools"
- **Document everything:** Capture exact responses
- **Be objective:** Score based on rubric, not impressions

### Scoring Consistently
- **Use examples:** Refer back to scored questions
- **Get second opinions:** Have colleague review borderline cases
- **Document reasoning:** Write why you gave each score
- **Be honest:** Include limitations and failures

### Managing the Process
- **Start small:** Evaluate 5 questions before scaling up
- **Iterate:** Refine questions based on initial results
- **Take breaks:** Evaluation fatigue affects consistency
- **Track time:** Note how long evaluations take

---

## Example Evaluation Flow

```
1. Design question: "What is the UniProt ID for human BRCA1?"
   └─ Category: Precision
   └─ Use case: Need exact ID for database queries

2. Baseline test
   └─ Prompt: "Answer using only your training knowledge..."
   └─ Response: "BRCA1 is a tumor suppressor gene..."
   └─ No ID provided

3. TogoMCP test
   └─ Prompt: "What is the UniProt ID for human BRCA1?"
   └─ Tools used: search_uniprot_entity
   └─ Response: "P38398"

4. Scoring
   └─ Accuracy: 3 (correct ID)
   └─ Precision: 3 (exact database ID)
   └─ Completeness: 2 (concise answer)
   └─ Verifiability: 3 (can check UniProt)
   └─ Currency: 1 (stable information)
   └─ Impossibility: 2 (baseline couldn't provide ID)
   └─ Total: 14/18 → VALUABLE

5. Decision: INCLUDE ✓
   └─ Reason: Clear demonstration of database value
   └─ Good baseline test case
```

---

## Customization Options

### Adding Fields to CSV
Consider adding:
- `Organism`: Human, Mouse, E. coli, etc.
- `Data_Type`: Gene, Protein, Compound, Pathway, Disease
- `Complexity`: Simple, Medium, Complex
- `Response_Time_Baseline`: Seconds
- `Response_Time_TogoMCP`: Seconds
- `Verification_Status`: Verified, Unverified, Failed
- `Error_Type`: If TogoMCP failed (wrong answer, timeout, etc.)
- `Priority`: High, Medium, Low

### Creating Domain-Specific Rubrics
You can adapt the rubric for:
- Specific organisms (e.g., human-only, microbe-focused)
- Specific data types (e.g., compound-centric, pathway-centric)
- Specific use cases (drug discovery, basic research, etc.)

---

## Support and Questions

For questions about:
- **Rubric methodology:** See `togomcp_evaluation_rubric.md`
- **Template usage:** Examples in each template file
- **CSV analysis:** See `togomcp_evaluation_tracker.md`
- **TogoMCP capabilities:** Test with sample questions first

---

## Version History

- **v1.0** (2025-12-15): Initial template suite created
  - Comprehensive rubric
  - Full evaluation template
  - Quick eval form
  - CSV tracker
  - Documentation

---

## Next Steps

After completing your evaluation:
1. **Compile results:** Summarize key findings
2. **Share feedback:** Report issues or suggestions to TogoMCP developers
3. **Publish benchmarks:** Consider sharing your question set
4. **Iterate:** Refine questions based on results
5. **Monitor:** Re-evaluate as TogoMCP evolves

Good luck with your evaluation!
