# TogoMCP Evaluation Results Template

**Evaluator:** [Your name]  
**Date:** [YYYY-MM-DD]  
**TogoMCP Version:** [Version if known]  
**Evaluation Session:** [e.g., "Initial Testing", "Q1 2025 Review"]

---

## Question #[N]: [Brief Title]

### Question Details
**Category:** [ ] Precision | [ ] Completeness | [ ] Integration | [ ] Currency | [ ] Specificity | [ ] Structured Query

**Full Question:**
```
[Write the exact question asked]
```

**Expected Use Case:**
[Brief description of when a researcher might ask this - e.g., "Planning cloning experiments", "Literature review for grant proposal"]

**Target Organism/Domain:** [e.g., "Homo sapiens", "E. coli", "General metabolic pathways"]

---

### Baseline Answer (No Database Tools)

**Prompt Used:**
```
Answer using only your training knowledge. Do not use any database tools.
[Question]
```

**Response:**
```
[Paste or summarize the baseline answer]
```

**Response Characteristics:**
- Length: [X words/paragraphs]
- Confidence level: [ ] High | [ ] Medium | [ ] Low | [ ] Uncertain
- Specific data provided: [ ] Yes | [ ] No
- Caveats mentioned: [ ] Yes | [ ] No

---

### TogoMCP-Enhanced Answer

**Prompt Used:**
```
[Question]
```

**Tools Used:**
- [ ] TogoMCP SPARQL queries
- [ ] TogoMCP search functions
- [ ] TogoMCP ID conversion
- [ ] PubMed
- [ ] OLS4
- [ ] PubDictionaries
- [ ] Other: _____________

**Tool Calls Made:** [Number]

**Response:**
```
[Paste or summarize the TogoMCP-enhanced answer]
```

**Response Characteristics:**
- Length: [X words/paragraphs]
- Database IDs provided: [ ] Yes | [ ] No
- Specific values/numbers: [ ] Yes | [ ] No
- References/citations: [ ] Yes | [ ] No

---

### Comparison & Scoring

#### Dimension Scores (0-3 each)

| Dimension | Score | Evidence/Justification |
|-----------|-------|------------------------|
| **Accuracy** | [0/1/2/3] | [Did the database query improve correctness? What errors were corrected?] |
| **Precision** | [0/1/2/3] | [Were exact IDs, sequences, or values provided that weren't in baseline?] |
| **Completeness** | [0/1/2/3] | [Was the answer more comprehensive? What was added?] |
| **Verifiability** | [0/1/2/3] | [Can the answer be independently verified? Are sources cited?] |
| **Currency** | [0/1/2/3] | [Is information more current than Jan 2025 knowledge cutoff?] |
| **Impossibility** | [0/1/2/3] | [Could baseline have answered this at all?] |

**Total Score:** [X/18]

#### Overall Assessment
**Category:** [ ] CRITICAL (≥15) | [ ] VALUABLE (9-14) | [ ] MARGINAL (4-8) | [ ] REDUNDANT (0-3)

---

### Key Differences

**What the baseline answer included:**
1. [Point 1]
2. [Point 2]
3. [Point 3]

**What TogoMCP added or corrected:**
1. [Point 1]
2. [Point 2]
3. [Point 3]

**Concrete examples of improvement:**
- **Example 1:** Baseline said "[quote]" but TogoMCP provided "[specific data/correction]"
- **Example 2:** [Another specific example]

---

### Verification

**Independent Verification Performed:** [ ] Yes | [ ] No

**Verification Method:**
[e.g., "Manually checked UniProt database", "Cross-referenced with NCBI Gene", "Verified SPARQL query results"]

**Verification Results:**
- [ ] TogoMCP answer confirmed correct
- [ ] TogoMCP answer partially correct (details: _____________)
- [ ] TogoMCP answer incorrect (details: _____________)
- [ ] Unable to verify

**Discrepancies Found:**
[Note any differences between TogoMCP answer and independent verification]

---

### Decision

**Include in Evaluation Set?** [ ] YES | [ ] NO

**Reasoning:**
[Why you're including or excluding this question]

**Suggested Question Modifications (if any):**
[How the question could be improved to better test TogoMCP capabilities]

---

### Additional Notes

**Strengths of TogoMCP Response:**
- [Strength 1]
- [Strength 2]

**Limitations Observed:**
- [Limitation 1]
- [Limitation 2]

**Unexpected Findings:**
[Anything surprising or noteworthy]

**Follow-up Questions This Raises:**
- [Question 1]
- [Question 2]

---

### Example Output Snippets

**Baseline Output Sample:**
```
[Key excerpt from baseline answer]
```

**TogoMCP Output Sample:**
```
[Key excerpt from TogoMCP answer, highlighting database-derived information]
```

---

### Tags/Keywords
[For easy searching later: e.g., "pathway", "human", "BRCA1", "ID-conversion", "SPARQL"]

---

**Evaluation Status:** [ ] Draft | [ ] Complete | [ ] Reviewed | [ ] Verified

**Reviewer Comments:**
[If peer-reviewed]

---

# Summary Statistics (Fill at end of evaluation session)

**Total Questions Evaluated:** [N]

**Score Distribution:**
- CRITICAL (≥15): [N] questions ([X%])
- VALUABLE (9-14): [N] questions ([X%])
- MARGINAL (4-8): [N] questions ([X%])
- REDUNDANT (0-3): [N] questions ([X%])

**Category Distribution:**
- Precision: [N]
- Completeness: [N]
- Integration: [N]
- Currency: [N]
- Specificity: [N]
- Structured Query: [N]

**Average Score:** [X.X/18]

**Questions Included in Final Set:** [N]

**Key Insights:**
1. [Overall finding 1]
2. [Overall finding 2]
3. [Overall finding 3]

**Recommendations for TogoMCP Development:**
1. [Suggestion 1]
2. [Suggestion 2]
