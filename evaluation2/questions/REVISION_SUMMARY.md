# TogoMCP Question Revision Summary

## Session: February 9, 2026

### Question 014: REVISED ✅

**Original Question (v1):**
- Type: `list`
- Question: "Which 10 ciliopathy subtypes in MONDO disease ontology have the most external database cross-references?"
- **Problem:** Database metadata question - counts cross-references (curation effort) rather than revealing biological/clinical patterns
- **Quality Issue:** Cross-reference count reflects CURATION EFFORT, not clinical importance. "Who cares?" - Only database curators, not clinicians/biologists
- **Decision:** REJECTED

**Revised Question (v2):**
- Type: `factoid`
- Question: "Which ciliopathy subtype in MONDO has the highest genetic heterogeneity (most genetic subtypes representing different causative genes)?"
- **Answer:** Primary ciliary dyskinesia (59 genetic subtypes)
- **Strengths:**
  - BIOLOGICALLY MEANINGFUL - genetic heterogeneity is clinically important for diagnosis
  - Reveals disease complexity and diagnostic challenges
  - Informs genetic testing strategies (larger panels needed for heterogeneous diseases)
  - Reflects research progress in molecular characterization
  - NOT answerable from PubMed - requires systematic database query of disease hierarchy
  - Clinically actionable - helps prioritize testing and counseling approaches
- **Decision:** ACCEPTED ✅

### Key Changes:
1. **Question type:** `list` → `factoid` 
2. **Focus shift:** Database metadata counting → Biological property (genetic heterogeneity)
3. **Clinical relevance:** Now informs diagnostic complexity, testing strategies, and genetic counseling
4. **Database usage:** Still single database (MONDO only), but now reveals meaningful biology

### Results from Revised Question:
- **Top 5 ciliopathies by genetic heterogeneity:**
  1. Primary ciliary dyskinesia: 59 subtypes (highest)
  2. Joubert syndrome: 39 subtypes
  3. Jeune syndrome: 23 subtypes
  4. Bardet-Biedl syndrome: 22 subtypes
  5. Meckel syndrome: 14 subtypes

### Clinical Significance:
This ranking reveals diagnostic complexity and testing requirements:
- PCD's 59 genetic subtypes require large NGS panels (>40 genes) for diagnosis
- High heterogeneity explains why ~30% of PCD cases remain genetically unresolved
- Informs resource allocation for genetic research and test development
- Guides genetic counseling strategies for ciliopathy families
- Demonstrates that ciliary diseases affecting core structural components (PCD) show greater genetic diversity than those affecting specific signaling pathways

### Impact on Question Set Balance:
- **Factoid questions:** 11 → 12 (120% of target)
- **List questions:** 7 → 6 (60% of target)
- **Total scientifically meaningful questions:** 48 → 49 out of 50

---

## Overall Revision Progress (3/4 complete):

✅ **Question 001:** REVISED (yes/no → factoid, requires database counting)  
✅ **Question 007:** REVISED (summary → yes/no, excludes annotation artifacts, tests teleost WGD)  
✅ **Question 014:** REVISED (list → factoid, database metadata → genetic heterogeneity)  
⏳ **Question 015:** NANDO cross-references (database metadata → needs biological focus)

---

## Files Updated:
- `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_014.yaml` - Complete rewrite
- `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml` - Updated type counts and revision history

---

## Next Steps:
1. Revise Question 015 (NANDO cross-references issue)
2. Update final coverage tracker with complete revision notes
3. Run final quality assessment on all 50 questions
