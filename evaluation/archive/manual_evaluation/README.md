# Manual Evaluation Templates (ARCHIVED)

These templates were used for manual evaluation before automation was implemented.

**Status**: Deprecated - Use automated evaluation scripts instead

**Current workflow**: See `/evaluation/scripts/README.md`

---

## Files

- `togomcp_evaluation_rubric.md` - Manual scoring rubric and methodology
- `togomcp_evaluation_template.md` - Detailed evaluation form template
- `togomcp_quick_eval_form.md` - Quick evaluation form
- `togomcp_evaluation_tracker.md` - Tracker usage instructions
- `togomcp_evaluation_tracker.csv` - Tracker template (TSV format)

---

## Why Archived?

The evaluation process has been **automated with Python scripts** that provide:
- Consistent baseline vs TogoMCP comparisons
- Automatic correctness evaluation
- Statistical analysis and reporting
- Interactive dashboards
- Reproducible results

Manual scoring (the core of these templates) is no longer needed.

---

## Looking for Question Design Guidance?

The **question design criteria** from `togomcp_evaluation_rubric.md` are still valuable but have been extracted and updated in:

**→ [`/evaluation/QUESTION_DESIGN_GUIDE.md`](../../QUESTION_DESIGN_GUIDE.md)**

This new guide includes:
- ✅ Question quality checklist (from the old rubric)
- ✅ The six question categories with examples
- ✅ Examples from the existing 120-question set
- ✅ How automated evaluation validates questions
- ❌ Manual scoring methodology (no longer needed)

**Use the new guide** for creating evaluation questions.

---

## Historical Context

These templates were designed for manual evaluation when the project needed:
- Detailed human scoring (6 dimensions, 0-3 scale)
- Qualitative assessment categories (CRITICAL, VALUABLE, MARGINAL, REDUNDANT)
- Flexible evaluation workflows (template vs quick form vs tracker)

The automated scripts now handle these assessments programmatically while maintaining the same evaluation principles.

---

## If You Need Manual Evaluation

While automated evaluation is recommended, these templates remain valid for:
- Qualitative case studies
- Detailed documentation of specific questions
- Human validation of automated results
- Publications requiring detailed examples

However, **for question design**, use the current [`QUESTION_DESIGN_GUIDE.md`](../../QUESTION_DESIGN_GUIDE.md) instead of the rubric.

---

**Archived**: 2025-12-18  
**Replaced by**: 
- Automated evaluation: `/evaluation/scripts/`
- Question design: `/evaluation/QUESTION_DESIGN_GUIDE.md`
