# TogoMCP Question Design Guide
# MINIMAL REFERENCE VERSION

**Purpose**: Quick reference for understanding TogoMCP evaluation questions and MIE-dependency framework.

**For**: Understanding existing questions, validating question quality, reviewing evaluation results  
**Not for**: Creating new questions (see `question_generation_phase2.md` for creation)

---

## Quick Reference

**Question Distribution**:
- 🔴 **70% MIE-Required** (85 questions): Demonstrate MIE file value
- 🟢 **30% Simple** (35 questions): Show when MIE not needed (contrast)

**MIE-Required Patterns**:
1. Multi-database SPARQL joins (25 questions)
2. Performance-critical queries (20 questions)
3. Error-avoidance queries (15 questions)
4. Complex multi-criteria filtering (25 questions)

**Simple Patterns**:
1. Search tool queries (15 questions)
2. API-based queries (12 questions)
3. ID conversions (8 questions)

---

## MIE-Dependency Framework

### 🔴 MIE-Required Questions (85 total)

Questions that **cannot be answered correctly without MIE file knowledge**.

#### Pattern 1: Multi-Database SPARQL Joins (25 questions)

**Requires**: GRAPH URIs from multiple MIE files, join properties, pre-filtering strategies

**Example**:
```
Q: "Find human reviewed proteins in UniProt that catalyze Rhea 
    reactions involving ATP (ChEBI:30616)"

Why MIE-Required:
- Needs UniProt GRAPH URI: http://sparql.uniprot.org/uniprot
- Needs Rhea GRAPH URI: http://rdfportal.org/dataset/rhea
- Needs join property: up:enzyme → rhea:ec
- Needs reviewed=1 pre-filter to avoid timeout on 444M proteins
- Needs ChEBI URI format for ATP

Without MIE: Wrong GRAPH URIs (no results), timeout from missing 
reviewed=1, or fails to identify join point
```

#### Pattern 2: Performance-Critical Queries (20 questions)

**Requires**: Early filtering patterns, bif:contains syntax, LIMIT strategies

**Example**:
```
Q: "How many human reviewed proteins in UniProt have GO annotations 
    for DNA repair processes?"

Why MIE-Required:
- Needs early filtering: up:reviewed 1 must be FIRST constraint
- Without early filter: processes 444M proteins → timeout (60s)
- With MIE Strategy 8: reviewed=1 first → completes in 2 seconds

Without MIE: Query constructed as FILTER(?protein up:reviewed 1) 
after property (too late) → timeout
```

#### Pattern 3: Error-Avoidance Queries (15 questions)

**Requires**: Property path splitting, correct URI formats, GRAPH specifications

**Example**:
```
Q: "Find human reviewed proteins where the recommended name contains 
    'kinase' using full-text search"

Why MIE-Required:
- bif:contains incompatible with property paths
- Natural query: up:recommendedName/up:fullName + bif:contains
- Result: 400 Bad Request error

MIE Solution (common_errors section):
- Split property path first:
  up:recommendedName ?name .
  ?name up:fullName ?text .
  ?text bif:contains 'kinase' .

Without MIE: 400 error (backend-specific, not discoverable)
```

#### Pattern 4: Complex Multi-Criteria Filtering (25 questions)

**Requires**: Schema knowledge from ShEx, filter optimization, data model understanding

**Example**:
```
Q: "Find ChEMBL compounds with IC50 < 100 nM against EGFR that 
    reached Phase 2+ clinical trials"

Why MIE-Required:
- Needs ChEMBL data model: molecule → activity → target
- Needs bioactivity filtering: activity type + value threshold
- Needs target specification: ChEMBL ID for EGFR
- Needs development phase property: max_phase >= 2
- Needs filter order optimization

Without MIE: Cannot construct query without ChEMBL ShEx schema
```

### 🟢 Simple Questions (35 total)

Questions answerable with **simple tools or basic SPARQL** (no MIE needed).

#### Simple Pattern 1: Search Tool Queries (15 questions)

**Example**:
```
Q: "What is the UniProt ID for human BRCA1?"

Why NOT MIE-Required:
- Uses search_uniprot_entity('BRCA1 human')
- Returns P38398 directly
- No complex SPARQL construction needed
- Demonstrates appropriate tool selection
```

#### Simple Pattern 2: API-Based Queries (12 questions)

**Example**:
```
Q: "How many descendant terms does GO:0006914 (autophagy) have?"

Why NOT MIE-Required:
- Uses OLS4 getDescendants API
- Returns 25 descendants directly
- No SPARQL needed (API provides ontology navigation)
- Demonstrates when baseline tools suffice
```

#### Simple Pattern 3: ID Conversions (8 questions)

**Example**:
```
Q: "Convert UniProt P04637 to NCBI Gene ID"

Why NOT MIE-Required:
- Uses togoid_convertId(ids='P04637', route='uniprot,ncbigene')
- Returns 7157 directly
- No complex query construction
- Demonstrates simple cross-reference service
```

---

## Category Targets

Each category has specific MIE-dependency targets:

| Category | Total | 🔴 MIE-Required | 🟢 Simple | MIE % |
|----------|-------|-----------------|-----------|-------|
| **Structured Query** | 20 | 18 | 2 | 90% |
| **Integration** | 20 | 16 | 4 | 80% |
| **Completeness** | 20 | 12 | 8 | 60% |
| **Specificity** | 20 | 10 | 10 | 50% |
| **Currency** | 20 | 10 | 10 | 50% |
| **Precision** | 20 | 9 | 11 | 45% |
| **TOTAL** | **120** | **85** | **35** | **71%** |

**Why different targets?**
- **Structured Query**: Most inherently complex (filtering, combining criteria)
- **Integration**: Usually requires cross-database SPARQL (high MIE)
- **Precision/Currency**: Often simple lookups (lower MIE)
- **Completeness/Specificity**: Mixed (some complex, some simple)

---

## Category Definitions

### 1. Precision (20 questions)
Test ability to retrieve **exact, specific data**.
- Examples: Specific IDs, exact measurements, precise sequences
- MIE-Required: Complex lookups with multiple criteria
- Simple: Direct ID lookups via search tools

### 2. Completeness (20 questions)
Test ability to retrieve **exhaustive or comprehensive data**.
- Examples: Counts, complete lists, systematic enumeration
- MIE-Required: Performance-critical counts on large datasets
- Simple: API-based counts (OLS4, E-utilities)

### 3. Integration (20 questions)
Test **cross-database linking and ID conversion**.
- Examples: ID conversions, multi-database relationships
- MIE-Required: Cross-database SPARQL joins
- Simple: togoid ID conversions

### 4. Currency (20 questions)
Test access to **recent or time-sensitive information**.
- Examples: Recent additions, current status, post-training data
- MIE-Required: Complex queries on recent data
- Simple: Basic recent counts via search

### 5. Specificity (20 questions)
Test ability to find **niche or specialized information**.
- Examples: Rare diseases, specialized organisms, uncommon compounds
- MIE-Required: Complex queries in specialized databases
- Simple: Basic lookups in niche databases

### 6. Structured Query (20 questions)
Test ability to handle **complex, multi-step queries**.
- Examples: Multiple criteria, filtering, combining constraints
- MIE-Required: Most should be (90% target)
- Simple: API-based filtering when available

---

## Question Quality Criteria

All questions (MIE-Required and Simple) must be:

✅ **Biologically Realistic**
- Would an actual researcher ask this?
- Does it solve a real research problem?
- Is the answer useful?

✅ **Testable Distinction**
- Can you verify if database was used?
- Is the answer verifiable?
- Clear success criteria?

✅ **Appropriate Complexity**
- Not too simple (baseline can't answer)
- Not impossibly broad (wouldn't timeout)
- Right scope for category and type

✅ **Clear Success Criteria**
- Specific expected answer
- Objectively verifiable
- Stable (not changing daily unless Currency)

---

## Notes Field Format

### For 🔴 MIE-Required Questions

```
"REQUIRES MIE FILE(S): [Database(s)] MIE - [sections needed].

MIE Knowledge Required:
- [Specific element 1]
- [Specific element 2]
- [Specific element 3]

Without MIE: [what fails - timeout/error/wrong approach].

With MIE: [what MIE provides that enables success].

Verified in [dbname]_exploration.md [Pattern reference]."
```

### For 🟢 Simple Questions

```
"Simple [query type] using [tool/API name]. Does NOT require MIE file - 
demonstrates when baseline/simple tools suffice.

Query: [tool call]
Returns: [direct result]

Verified in [dbname]_exploration.md simple queries section."
```

---

## Validation Checklist

### MIE-Dependency Distribution
- [ ] 85 questions marked "REQUIRES MIE FILE(S)"
- [ ] 35 questions marked "Does NOT require MIE"
- [ ] Structured Query: 18/20 MIE-Required (90%)
- [ ] Integration: 16/20 MIE-Required (80%)
- [ ] Other categories meet targets

### MIE-Required Quality
- [ ] All cite specific MIE file(s) and sections
- [ ] All explain what fails without MIE
- [ ] All explain what MIE provides
- [ ] All reference exploration report patterns

### Simple Question Quality
- [ ] All explicitly state "Does NOT require MIE"
- [ ] All name the tool/API used
- [ ] All explain why MIE not needed

### Overall Quality
- [ ] 120 questions total (20 per category)
- [ ] All biologically relevant (not database trivia)
- [ ] All expert-realistic (researchers would ask)
- [ ] All have verifiable answers
- [ ] All databases represented

---

## Expected Evaluation Results

With proper MIE-dependency distribution:

**Success Rates**:
- WITH MIE: 85-90% overall
  - MIE-Required questions: 90% (complex queries succeed)
  - Simple questions: 95% (baseline sufficient)
  
- WITHOUT MIE: 60-70% overall
  - MIE-Required questions: 40% (timeouts, errors, wrong SPARQL)
  - Simple questions: 95% (no difference - proves fairness)

**Tool Usage**:
- WITH MIE: get_MIE_file called 70-80% of time
- WITHOUT MIE: Tool not available (0% usage)

**Performance Gap**:
- Overall difference: 15-25%
- On MIE-Required questions: 50% difference (90% vs 40%)
- On Simple questions: 0% difference (proves unbiased)

**Failure Categorization** (WITHOUT MIE):
- Timeouts: Missing performance optimizations
- 400 Errors: Missing error-avoidance patterns
- Wrong Results: Missing GRAPH URIs or join properties
- Empty Results: Missing cross-database knowledge

---

## Common Question Patterns

### ✅ Good MIE-Required Questions

**Multi-Database Join**:
```
"Find pathogenic ClinVar variants in genes encoding proteins with 
 PDB structures better than 2.0Å resolution"

Requires: ClinVar + Gene + UniProt + PDB MIE files
```

**Performance-Critical**:
```
"How many human reviewed proteins have transmembrane regions annotated?"

Requires: UniProt MIE early filtering strategy
```

**Error-Avoidance**:
```
"Find proteins where annotation text contains 'membrane receptor'"

Requires: UniProt MIE property path splitting solution
```

**Complex Filtering**:
```
"Find ChEMBL kinase inhibitors with IC50 < 100 nM in Phase 2+ trials"

Requires: ChEMBL MIE data model and filtering patterns
```

### ✅ Good Simple Questions

**Search Tool**:
```
"What is the UniProt ID for human BRCA1?"

Uses: search_uniprot_entity tool
```

**API Query**:
```
"How many descendants does GO:0006914 have?"

Uses: OLS4 getDescendants API
```

**ID Conversion**:
```
"Convert UniProt P04637 to NCBI Gene ID"

Uses: togoid_convertId service
```

### ❌ Bad Examples

**Claiming MIE-Required Without Justification**:
```
Question: "What is the UniProt ID for BRCA1?"
Notes: "REQUIRES MIE FILE: UniProt MIE"

Problem: This is actually a simple search, doesn't need MIE
```

**Vague About MIE Value**:
```
Notes: "REQUIRES MIE FILE: Helps with the query"

Problem: Doesn't explain WHAT from MIE or WHY needed
```

**Not Explaining Failure Mode**:
```
Notes: "REQUIRES MIE FILE: Needs it to work"

Problem: Doesn't explain what goes wrong without MIE
```

---

## Resources

**For Creating Questions**:
- **Phase 1**: `question_generation_phase1_REVISED.md` (exploration)
- **Phase 2**: `question_generation_phase2_REVISED.md` (question creation)
- **This Guide**: Reference only (understanding framework)

**For Validation**:
```bash
# Validate JSON format
python scripts/validate_questions.py questions/Q01.json

# Count MIE-Required questions
grep -r "REQUIRES MIE FILE" questions/*.json | wc -l

# Count Simple questions
grep -r "Does NOT require MIE" questions/*.json | wc -l
```

**For Running Evaluation**:
- `scripts/automated_test_runner.py` - Run tests WITH and WITHOUT MIE
- `scripts/add_llm_evaluation.py` - Add LLM-based scoring
- `scripts/results_analyzer.py` - Analyze results

---

## Summary

**MIE-Dependency is Key**:
- 70% questions should REQUIRE MIE files (demonstrate value)
- 30% questions should NOT need MIE (demonstrate fairness)
- Different categories have different MIE targets
- Notes must clearly explain MIE value or why not needed

**Four MIE-Required Patterns**:
1. Multi-database joins (need GRAPH URIs, join properties)
2. Performance-critical (need early filtering, optimization)
3. Error-avoidance (need solutions for backend-specific errors)
4. Complex filtering (need schema knowledge, data models)

**Three Simple Patterns**:
1. Search tools (direct entity lookups)
2. API queries (OLS4, E-utilities)
3. ID conversions (togoid service)

**Expected Impact**:
- WITH MIE: 85-90% success (complex queries work)
- WITHOUT MIE: 60-70% success (complex queries fail)
- Performance gap: 15-25% (proves MIE value)

---

**For question creation instructions, see**: `question_generation_phase2_REVISED.md`

**Last Updated**: 2026-01-30 (Minimal Reference Version)