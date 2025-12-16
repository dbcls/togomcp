# TogoMCP Evaluation Rubric

## I. Question Design Criteria

### A. Question Quality Checklist
Before including a question in your evaluation set, check:

- [ ] **Biologically realistic** - Would an actual researcher ask this?
- [ ] **Testable distinction** - Can you tell if the answer used databases vs baseline knowledge?
- [ ] **Appropriate complexity** - Not trivially answered, not impossibly broad
- [ ] **Clear success criteria** - You can objectively verify if the answer is correct

### B. Question Categories (Design at least 2-3 questions per category)

1. **Precision Questions** - Require exact, verifiable data
   - Database IDs, sequences, molecular properties
   - Example: "What is the UniProt ID for human BRCA1?"

2. **Completeness Questions** - Require exhaustive/systematic data
   - "List all...", "How many...", complete sets
   - Example: "How many human genes are in the GO term 'DNA repair'?"

3. **Integration Questions** - Require cross-database linking
   - ID conversions, relationship mapping
   - Example: "Find ChEMBL targets for PubChem compound 5288826"

4. **Currency Questions** - Benefit from up-to-date database info
   - Recent additions, current classifications
   - Example: "What pathways in Reactome involve SARS-CoV-2 proteins?"

5. **Specificity Questions** - Niche/specialized information
   - Rare diseases, specific organisms, unusual compounds
   - Example: "What is the MeSH descriptor for Erdheim-Chester disease?"

6. **Structured Query Questions** - Require database querying
   - Complex filters, SPARQL-like queries
   - Example: "Find all kinase inhibitors in ChEMBL with IC50 < 10nM"

## II. Response Evaluation Criteria

### A. Value-Add Dimensions (Score each 0-3)

**0 = No value-add** | **1 = Minimal** | **2 = Significant** | **3 = Essential**

| Dimension | Score | Evidence |
|-----------|-------|----------|
| **Accuracy** - Database query improved correctness | | Did baseline answer have errors? |
| **Precision** - Exact IDs, numbers, sequences provided | | Are specific identifiers/values given? |
| **Completeness** - Comprehensive vs partial information | | Is the answer exhaustive? |
| **Verifiability** - Can answer be independently verified? | | Are sources/IDs provided? |
| **Currency** - Information more current than training data | | Is data from after Jan 2025? |
| **Impossibility** - Could not answer without database access | | Would baseline answer be "I don't know"? |

### B. Overall Assessment Categories

**CRITICAL (High Value-Add)**
- Score ≥15/18 on dimensions above
- Database access was essential to answer
- Baseline knowledge would be incorrect or incomplete
- **Use these questions to showcase TogoMCP**

**VALUABLE (Moderate Value-Add)**
- Score 9-14/18
- Database improved answer quality significantly
- Baseline might give partial/uncertain answer
- **Good for evaluation set**

**MARGINAL (Low Value-Add)**
- Score 4-8/18
- Database mostly confirmed baseline knowledge
- Minor improvements in precision
- **Consider revising question**

**REDUNDANT (No Value-Add)**
- Score 0-3/18
- Database didn't improve answer
- Baseline knowledge was sufficient
- **Exclude from evaluation set**

## III. Evaluation Protocol

### Step 1: Generate Baseline Answer
First, ask the question with this instruction:
> "Answer using only your training knowledge. Do not use any database tools."

### Step 2: Generate TogoMCP-Enhanced Answer
Then ask the same question normally (allowing tool use).

### Step 3: Compare & Score
Use the rubric above to:
1. Score each dimension (0-3)
2. Identify specific differences
3. Categorize overall value-add
4. Document evidence

### Step 4: Verify
Check answers against actual databases independently if possible.

## IV. Sample Scoring Template

```
Question: [Your question here]

Baseline Answer: [Summary]
TogoMCP Answer: [Summary]

Dimension Scores:
- Accuracy: [0-3] - [evidence]
- Precision: [0-3] - [evidence]  
- Completeness: [0-3] - [evidence]
- Verifiability: [0-3] - [evidence]
- Currency: [0-3] - [evidence]
- Impossibility: [0-3] - [evidence]

Total: [X/18]
Category: [CRITICAL/VALUABLE/MARGINAL/REDUNDANT]

Key Differences:
1. [Specific difference]
2. [Specific difference]

Include in evaluation set? [YES/NO]
Notes: [Additional observations]
```

## V. Recommended Evaluation Set Composition

For a comprehensive evaluation, aim for:
- **30-40% CRITICAL questions** - Core capabilities
- **40-50% VALUABLE questions** - Typical use cases
- **10-20% MARGINAL questions** - Edge cases/limitations
- **0% REDUNDANT questions** - Exclude these

Balance across:
- All 6 question categories
- Different organisms (human, model organisms, microbes)
- Different data types (genes, proteins, compounds, pathways, diseases)
- Different complexity levels

---

Would you like me to:
1. Generate sample questions with pre-scored examples?
2. Help you test this rubric on a few trial questions?
3. Refine any part of this framework?
