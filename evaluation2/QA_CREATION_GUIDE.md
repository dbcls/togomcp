# TogoMCP Question Creation Guide (v4.3)

Create 50 evaluation questions testing TogoMCP's ability to answer biological questions using RDF databases.

---

## ⚠️ CRITICAL: EXECUTION-FIRST PHILOSOPHY ⚠️

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║  THIS GUIDE REQUIRES ACTUAL TOOL EXECUTION, NOT PLANNING          ║
║                                                                    ║
║  ❌ WRONG: "I will write a SPARQL query to..."                    ║
║  ✅ RIGHT: [calls run_sparql(), pastes results]                   ║
║                                                                    ║
║  WRITING WITHOUT EXECUTING = INVALID QUESTION                     ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 📋 OUTPUT FORMAT SPECIFICATION

**⭐ CANONICAL FORMAT: See `QUESTION_FORMAT.md` for complete specification ⭐**

All question files MUST follow the YAML format defined in `QUESTION_FORMAT.md`, which specifies:
- Required and optional fields
- Field types and constraints
- Format by question type
- RDF triples comment format
- Validation rules
- Complete examples

**Quick reference** - Required top-level fields:
```yaml
id, type, body, inspiration_keyword, togomcp_databases_used,
verification_score, pubmed_test, sparql_queries, rdf_triples,
exact_answer, ideal_answer, question_template_used, time_spent
```

---

## QUESTION COMPLETION CHECKLIST

**⚠️ CHECK EACH ITEM AS YOU COMPLETE IT ⚠️**

```yaml
PRE-WORKFLOW:
□ Read coverage_tracker.yaml - DOCUMENTED current percentages below
□ Identified featured database (underutilized, not >45%)
□ Called get_MIE_file() - DOCUMENTED kw_search_tools below
□ Selected keyword from keywords.tsv

RDF NECESSITY GATES (BOTH MUST PASS):
□ Training knowledge test completed - PASS (cannot answer from memory)
□ Search/API tools test completed - PASS (cannot answer with search tools alone)

DISCOVERY (ALL TOOLS MUST BE EXECUTED):
□ Called search API from kw_search_tools - RESULTS PASTED below
□ Executed SPARQL structure query - RESULTS PASTED below  
□ Executed final SPARQL query - RESULTS PASTED below
□ All queries returned NON-EMPTY results (or investigated why)

VALIDATION (ALL TOOLS MUST BE EXECUTED):
□ Called PubMed:search_articles - AT LEAST 2 queries, PMIDs LISTED below

FINAL:
□ Score ≥9/12 calculated and justified
□ All fields in question_XXX.yaml filled (no placeholders)
□ coverage_tracker.yaml updated with new counts
□ question_XXX.yaml follows QUESTION_FORMAT.md specification

═══════════════════════════════════════════════════════════════════
IF ANY BOX UNCHECKED: QUESTION IS INCOMPLETE AND INVALID
═══════════════════════════════════════════════════════════════════
```

---

## CORE PRINCIPLES

1. **Biology First**: Ask questions researchers care about (not database inventory)
2. **Database Balance First**: Check coverage before every question
3. **RDF Necessity**: Must require current database state (not PubMed or training knowledge)
4. **TWO Critical Gates**: Both Training Test AND Search/API Test must PASS
5. **Integration-Driven**: 60%+ integrate 2+ databases
6. **Verifiable Scope**: Bounded, objectively checkable answers
7. **Comprehensive Analysis**: For yes/no questions, use comprehensive SPARQL (not example-based validation)
8. **EXECUTION REQUIRED**: Every tool mentioned must be actually called with results documented
9. **CANONICAL FORMAT**: Follow QUESTION_FORMAT.md specification exactly

---

## FILE LOCATIONS

```
FORMAT:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_FORMAT.md ⭐ CANONICAL SPECIFICATION
Input:   /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv
Track:   /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml
Output:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml
```

**Tools:**
- **User files:** `Filesystem:read_text_file()` / `Filesystem:write_file()`
- **RDF databases:** `TogoMCP-Test:get_MIE_file()` / `run_sparql()` / `search_*_entity()` / `ncbi_esearch()`
- **Ontology APIs:** `OLS4:searchClasses()` / `getDescendants()` / `getAncestors()`

---

## REQUIREMENTS

### Database Coverage (All 23 Required)
- **Tier 1 (≥3 each):** UniProt, ChEBI, ChEMBL, Rhea, PubChem, MeSH, GO, Reactome, Taxonomy, Ensembl, NCBI_Gene
- **Tier 2-4 (≥1 each):** PDB, ClinVar, MedGen, PubMed, AMRPortal, BacDive, MediaDive, DDBJ, NANDO, PubTator, Glycosmos, MONDO

### Balance Quotas (CRITICAL)
- **UniProt: ≤35 questions (70% max)** - Target 30-40%
- **GO: ≤25 questions (50% max)** - Target 24-30%
- **Skip databases >45%** for next 3+ questions
- **Prioritize databases <5%**
- **60%+ questions must NOT use UniProt**

### Question Types & Integration
- Factoid: 10 | Yes/No: 10 | List: 10 | Summary: 10 | Choice: 20
- **60%+ integrate 2+ databases** via cross-references or semantic links

### Quality Standards
- All questions score ≥9/12 (see Scoring Rubric)
- **Pass BOTH gates: Training Knowledge Test AND Search/API Tools Test**
- PubMed test shows non-answerability (must CALL the tool)
- Precise wording (avoid ambiguity)
- **Follow QUESTION_FORMAT.md specification**

---

## WORKFLOW (10 STEPS WITH MANDATORY EXECUTION)

### Step 1: Check Balance (MANDATORY FIRST STEP)

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 1: BALANCE CHECK 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: Filesystem:read_text_file(coverage_tracker.yaml)

PASTE RESULTS HERE:
[Current database percentages]

DECISION DOCUMENTED:
Featured database: [name]
Current coverage: [X%]
Reason: [underutilized/never used/strategic choice]

Status: □ COMPLETE
═══════════════════════════════════════════════════════════════════
```

**Critical**: Never start without checking balance. This prevents wasting effort on overused databases.

**Balance Rules:**
- Skip databases >45% for next 3+ questions
- Prioritize databases <5%
- Never exceed UniProt 70%, GO 50%

---

### Step 2: Read MIE File & Select Keyword

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 2: MIE FILE READ 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: TogoMCP-Test:get_MIE_file(dbname="featured_database")

DOCUMENT CRITICAL FIELDS:
kw_search_tools: [list the tools from MIE]
Example SPARQL patterns: [note patterns]
Key predicates: [list structured properties]

Status: □ COMPLETE
═══════════════════════════════════════════════════════════════════
```

**⭐ ALWAYS CHECK MIE's `kw_search_tools` FIELD FIRST ⭐**

**Why This Matters:**
- MIE explicitly tells you which API works for keyword discovery
- Wrong: Jump to SPARQL for keywords → Empty results
- Right: Use kw_search_tools → Get IDs → SPARQL for structure

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 2B: KEYWORD SELECTION 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: Filesystem:read_text_file(keywords.tsv)

DOCUMENT SELECTION:
Selected keyword: [KW-XXXX]
Keyword name: [name]
Category: [category]
Match to database: [why this keyword fits featured database]

Question formulated: [exact question text]

Wording check: 
□ No ambiguous verbs (bind/contain/have/associated with)
□ Scope is clear
□ Featured database is PRIMARY
□ No database names in question text

Status: □ COMPLETE
═══════════════════════════════════════════════════════════════════
```

**Question Formulation - Precise Wording:**

Avoid ambiguity by being specific about:
1. **Native vs. experimental**: "native cofactor" not just "bind"
2. **Annotation vs. structure**: "annotated with" vs "crystallized with"
3. **Total vs. filtered counts**: Make scope explicit

**Red flag verbs requiring qualification:**
- bind, contain, have, associated with, interact with, found in, related to
- **Solution**: Add qualifiers like "natively", "annotated as", "experimentally determined"

**Examples:**
```yaml
❌ Vague: "Which proteins bind magnesium?"
✅ Precise: "Which proteins are annotated with native magnesium cofactor binding?"

❌ Vague: "Which genes are associated with hypertension?"
✅ Precise: "Which genes have pathogenic variants annotated for hypertension in ClinVar?"
```

---

### Step 3: RDF Necessity Tests (TWO MANDATORY GATES - BOTH MUST PASS)

```
═══════════════════════════════════════════════════════════════════
🛑 CRITICAL: TWO GATES - BOTH MUST PASS 🛑
═══════════════════════════════════════════════════════════════════
Gate 3A: Training Knowledge Test
Gate 3B: Search/API Tools Test

⚠️ IF EITHER GATE FAILS → STOP and redesign question ⚠️
═══════════════════════════════════════════════════════════════════
```

#### Step 3A: Training Knowledge Test (GATE 1)

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 3A: TRAINING KNOWLEDGE TEST (GATE 1) 🛑
═══════════════════════════════════════════════════════════════════
⚠️ THIS IS GATE 1: IF YOU CAN ANSWER FROM MEMORY → REJECT QUESTION ⚠️

Question: Can I answer this question from my training knowledge alone?

Attempted answer from memory: [your answer based on training knowledge]
Confidence level: [high | medium | low | none]
Reasoning: [explain why you can or cannot answer]

DECISION:
□ PASS (cannot answer from memory → proceed to Gate 2)
□ FAIL (can answer from memory → STOP and redesign)

⚠️ If FAIL: STOP HERE. Redesign question or select different topic.

Status: □ COMPLETE (result is PASS)
═══════════════════════════════════════════════════════════════════
```

**Understanding Gate 1:**

**PASS (Good questions - cannot answer from memory):**
```yaml
✅ "How many human proteins have BOTH PDB structures AND ClinVar disease variants?"
   Cannot answer: Requires cross-referencing two databases with current data

✅ "How many GO biological process terms have Reactome cross-references?"
   Cannot answer: Need to count across entire GO database

✅ "Which bacterial strain in BacDive has the highest optimal growth temperature?"
   Cannot answer: Requires querying cultivation data across all strains

✅ "How many human protein kinases are targeted by FDA-approved drugs?"
   Cannot answer: Need exact count from ChEMBL's drug-target-mechanism data
```

**FAIL (Bad questions - can answer from memory):**
```yaml
❌ "How many reviewed proteins in UniProt are annotated with nitrogen fixation?"
   Can answer: ~700-800 proteins (nitrogenase complex, nif genes)

❌ "What organisms perform nitrogen fixation?"
   Can answer: Rhizobium, Azotobacter, cyanobacteria

❌ "What is the function of hemoglobin?"
   Can answer: Oxygen transport via heme groups

❌ "What is the structure of ATP?"
   Can answer: Adenosine triphosphate, three phosphate groups
```

---

#### Step 3B: Search/API Tools Test (GATE 2) ⚠️ NEW

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 3B: SEARCH/API TOOLS TEST (GATE 2) 🛑
═══════════════════════════════════════════════════════════════════
⚠️ THIS IS GATE 2: IF SEARCH TOOLS CAN ANSWER → REJECT QUESTION ⚠️

Question: Can search/API tools answer this WITHOUT using SPARQL/RDF?

Tools to test: [list relevant API tools from kw_search_tools]

YOU MUST EXECUTE: Test with actual API calls

Test execution:
Tool: [exact tool name]
Query: [exact parameters]
Result: [paste actual results]

PASTE ACTUAL TOOL OUTPUT HERE:
[tool results]

Analysis: [Can this answer the question? Why or why not?]

DECISION:
□ PASS (search tools CANNOT fully answer → proceed to Step 4)
□ FAIL (search tools CAN answer → STOP and redesign)

⚠️ If FAIL: STOP HERE. Redesign question to require RDF capabilities.

Status: □ COMPLETE (result is PASS, tool output pasted)
═══════════════════════════════════════════════════════════════════
```

**Understanding Gate 2:**

**PASS (Search tools insufficient - requires RDF):**
```yaml
✅ "How many GO biological process terms have Reactome cross-references?"
   - OLS4:searchClasses finds examples but cannot:
     * Filter by hasOBONamespace property (biological_process)
     * Check hasDbXref property existence
     * Aggregate counts across entire database
   - Requires SPARQL for property filtering + aggregation

✅ "How many GO terms have EXACTLY 3 direct children?"
   - OLS4:getDescendants shows descendants but cannot:
     * Aggregate counts across all terms
     * Filter for exactly 3 children
   - Requires SPARQL to iterate and count

✅ "Which proteins have kinase activity AND >5 disease variants?"
   - Search finds examples but cannot:
     * Join data from multiple sources
     * Apply complex filtering across databases
   - Requires SPARQL for cross-database integration

✅ "How many human protein kinases are targeted by FDA-approved drugs?"
   - search_chembl_target finds kinases but cannot:
     * Filter by drug development phase (phase 4)
     * Link to drug mechanisms
     * Aggregate across molecule-mechanism-target relationships
   - Requires SPARQL for multi-entity joins
```

**FAIL (Search tools CAN answer - question invalid):**
```yaml
❌ "How many direct children does GO:0097190 have?"
   - OLS4:getDescendants returns all descendants with directParent info
   - Can filter by directParent and count
   - Does NOT require SPARQL

❌ "What is the molecular formula of aspirin?"
   - search_chembl_molecule or search_pubchem returns this directly
   - Simple lookup, not RDF-specific

❌ "List the synonyms of GO:0006915"
   - OLS4:search returns all synonyms in response
   - No RDF querying needed
```

**Key Distinction:**
- **Can answer with search tools** = API provides complete answer → **REJECT**
- **Cannot answer with search tools** = Needs RDF property filtering, aggregation, or joins → **ACCEPT**

---

### Step 4: Search API Discovery

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 4: SEARCH API DISCOVERY 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: [tool from MIE's kw_search_tools]

Tool called: [exact tool name]
Query used: [exact query string]
Results count: [total number found]
Example IDs: [list at least 5]

Purpose: Find examples for SPARQL query design (NOT for answering question)

PASTE ACTUAL TOOL OUTPUT HERE:
[tool results]

Status: □ COMPLETE (results pasted above)
═══════════════════════════════════════════════════════════════════
```

**Critical**: Get 5-10 example IDs to understand data patterns before writing SPARQL.

**Important Notes:**
- These IDs are for query design ONLY
- Do NOT use these IDs in VALUES for comprehensive queries
- This step passed Gate 2 because these examples alone cannot answer the question

---

### Step 5: SPARQL Structure Examination

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 5: STRUCTURE EXAMINATION 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: run_sparql() to examine entity properties

Query executed: [paste query]

PASTE RESULTS (first 10-20 rows):
[actual SPARQL results]

Key properties discovered: [list important predicates]

IF EMPTY RESULTS: 
□ I investigated why (describe investigation)
□ I fixed the query (show corrected version)

Status: □ COMPLETE (non-empty results pasted OR investigation documented)
═══════════════════════════════════════════════════════════════════
```

**Structure Query Pattern:**
```sparql
# Example: Examine properties of example entities
SELECT ?entity ?property ?value
WHERE {
  VALUES ?entity {
    <example_id_1>
    <example_id_2>
    <example_id_3>
  }
  ?entity ?property ?value .
}
LIMIT 50
```

---

### Step 6: Strategy Decision & Final SPARQL

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 6A: STRATEGY DECISION 🛑
═══════════════════════════════════════════════════════════════════
DOCUMENTED DECISION:

Question type: [factoid/yesno/list/summary/choice]
Strategy: [comprehensive | example-based]
Justification: [why this strategy]

For yes/no: □ Using comprehensive SPARQL (bif:contains + synonyms)
            □ NOT using VALUES with search results

For factoid/count: □ Using comprehensive aggregation
                   □ NOT limiting to search result IDs

Status: □ COMPLETE
═══════════════════════════════════════════════════════════════════
```

**Strategy Guidelines:**
- **Comprehensive**: Use for counts, yes/no, "all/which/how many" questions
- **Example-based**: Only for "name one example" or bounded lists with explicit limits

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 6B: FINAL SPARQL EXECUTION 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: run_sparql() with final query

Database: [dbname or endpoint_name]
Query executed: [paste complete query]

PASTE COMPLETE RESULTS:
[all rows returned, or first 50 if many]

Answer verified: [Yes/No - can I answer the question from these results?]
Answer extracted: [the actual answer]

IF INTEGRATION: 
□ Tested cross-database links work
□ Results from both databases present

Status: □ COMPLETE (results pasted AND answer verified)
═══════════════════════════════════════════════════════════════════
```

---

### Step 7: Integration Testing (if multi-database)

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 7: INTEGRATION (IF MULTI-DB) 🛑
═══════════════════════════════════════════════════════════════════
If single database:
□ N/A - Single database query

If multi-database:
□ Tested integration between: DB1(_____) × DB2(_____)
□ Integration method: [cross-references | shared endpoint | VALUES pre-filter]
□ Both databases contributed results: [Yes/No]

Integration pattern used: [describe linking strategy]

Status: □ COMPLETE
═══════════════════════════════════════════════════════════════════
```

**Integration Patterns:**
- **Cross-references**: Use skos:exactMatch, rdfs:seeAlso, etc.
- **Shared endpoint**: Query multiple GRAPHs in single SPARQL
- **VALUES pre-filter**: Get IDs from DB1, use in DB2 query

---

### Step 8: PubMed Test (15 minutes maximum)

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 8: PUBMED TEST 🛑
═══════════════════════════════════════════════════════════════════
YOU MUST EXECUTE: PubMed:search_articles (minimum 2 queries)

Query 1:
  Exact query string: [paste here]
  Tool called: [Yes/No] ← MUST BE YES
  PMIDs returned: [list all]
  Total found: [count]
  Why insufficient: [explain why these papers don't answer the question]

Query 2:
  Exact query string: [paste here]
  Tool called: [Yes/No] ← MUST BE YES
  PMIDs returned: [list all]
  Total found: [count]
  Why insufficient: [explain why these papers don't answer the question]

Conclusion: [why RDF databases are essential for this question]

Status: □ COMPLETE (at least 2 queries executed, PMIDs listed)
═══════════════════════════════════════════════════════════════════
```

**Why Papers Are Insufficient (Common Reasons):**
- Don't provide exact counts/comprehensive data
- Outdated compared to current database state
- Discuss topic generally but lack specific answer
- Would require manual compilation from multiple sources
- No access to structured, queryable relationships

---

### Step 9: Score & Validate

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 9: SCORING & VALIDATION 🛑
═══════════════════════════════════════════════════════════════════
CALCULATE SCORE:

Biological Insight: [0/1/2/3] - Justification: [explain]
Multi-Database: [0/1/2/3] - Justification: [explain]
Verifiability: [0/1/2/3] - Justification: [explain]
RDF Necessity: [0/1/2/3] - Justification: [explain]

TOTAL: [sum] / 12

Minimum required: 9/12
Result: □ PASS □ FAIL

Status: □ COMPLETE (score ≥9/12)
═══════════════════════════════════════════════════════════════════
```

**Scoring Rubric (0-3 per dimension, total ≥9/12):**

| Dimension | 3 | 2 | 1 | 0 |
|-----------|---|---|---|---|
| **Biological Insight** | Mechanisms/patterns | Functional relationships | Simple facts | Database inventory |
| **Multi-Database** | 3+ DBs integrated | 2 DBs integrated | Single DB + references | Search-only |
| **Verifiability** | Single/≤5 items | ≤10 items | ≤20 items | Unbounded |
| **RDF Necessity** | Impossible without RDF | Very difficult | Possible but tedious | PubMed/training OK |

**Examples by Dimension:**

**Biological Insight:**
- 3: "How do kinase inhibitors achieve selectivity?" (mechanisms)
- 2: "Which kinases interact with CDK4?" (functional relationships)
- 1: "How many kinases are in humans?" (simple fact)
- 0: "List all proteins in UniProt" (database inventory)

**Multi-Database:**
- 3: UniProt + PDB + ClinVar integration
- 2: ChEMBL + ChEBI integration
- 1: UniProt with GO cross-references
- 0: Text search only

**Verifiability:**
- 3: Single count or ≤5 ranked items
- 2: 6-10 items
- 1: 11-20 items
- 0: Unbounded or subjective

**RDF Necessity:**
- 3: Requires cross-database joins, property filtering, aggregation
- 2: Complex SPARQL needed but possible without RDF
- 1: Could compile manually from papers with effort
- 0: Available in training data or PubMed

---

### Step 10: Document & Update

```
═══════════════════════════════════════════════════════════════════
🛑 EXECUTION CHECKPOINT 10: DOCUMENTATION 🛑
═══════════════════════════════════════════════════════════════════
⭐ FOLLOW CANONICAL FORMAT: See QUESTION_FORMAT.md for complete specification

YOU MUST EXECUTE: 
1. Filesystem:write_file(question_XXX.yaml) - following QUESTION_FORMAT.md
2. Filesystem:write_file(coverage_tracker.yaml - UPDATED)

Question file created: □ Yes
  - Follows QUESTION_FORMAT.md structure: □ Yes
  - All required fields present: □ Yes
    ✓ id, type, body
    ✓ inspiration_keyword (with keyword_id, name, category)
    ✓ togomcp_databases_used
    ✓ verification_score (with biological_insight, multi_database, verifiability, rdf_necessity, total, passed)
    ✓ pubmed_test (with time_spent, method, result, conclusion)
    ✓ sparql_queries (array with query_number, database, description, query, result_count)
    ✓ rdf_triples (Turtle format with comments: # Database: X | Query: N | Comment: ...)
    ✓ exact_answer (format matches question type)
    ✓ ideal_answer (one paragraph for experts)
    ✓ question_template_used
    ✓ time_spent (exploration, formulation, verification, pubmed_test, extraction, documentation, total)
  - All fields filled (no placeholders): □ Yes
  - SPARQL queries show ACTUAL execution: □ Yes
  - PubMed test shows ACTUAL PMIDs: □ Yes
  - RDF triples follow comment format: □ Yes

Coverage tracker updated: □ Yes
  - Counts incremented: □ Yes
  - Percentages recalculated: □ Yes
  - Question ID added to database list: □ Yes

Status: □ COMPLETE

⚠️ VALIDATE: Check your YAML against QUESTION_FORMAT.md specification
═══════════════════════════════════════════════════════════════════
```

**Output Format Checklist:**

```yaml
Required Structure (from QUESTION_FORMAT.md):

□ id: question_XXX (matches filename)
□ type: [yes_no | factoid | list | summary]
□ body: "Question without database names"
□ inspiration_keyword:
    keyword_id: KW-XXXX
    name: "Name"
    category: "Category"
□ togomcp_databases_used: [array of databases]
□ verification_score:
    biological_insight: [0-3]
    multi_database: [0-3]
    verifiability: [0-3]
    rdf_necessity: [0-3]
    total: [0-12]
    passed: true
□ pubmed_test:
    time_spent: "15 minutes"
    method: "Description"
    result: "What was found"
    conclusion: "PASS (...)"
□ sparql_queries: [array with all required sub-fields]
□ rdf_triples: "Turtle format with mandatory comments"
□ exact_answer: [format matches type]
□ ideal_answer: "One paragraph"
□ question_template_used: "Template N"
□ time_spent: [all phases documented]
```

**RDF Triples Comment Format:**
```turtle
<subject> <predicate> <object> .
# Database: [database_name] | Query: [query_number] | Comment: [relevance]
```

---

## COMPLETE WORKFLOW SUMMARY

```
1. CHECK BALANCE FIRST (coverage_tracker.yaml)
   └─ EXECUTE: read file, document percentages
   ↓
2. READ MIE FILE & SELECT KEYWORD (check kw_search_tools!)
   └─ EXECUTE: get_MIE_file(), read keywords.tsv, document selection
   ↓
3A. TRAINING KNOWLEDGE TEST (GATE 1: must PASS = cannot answer)
   └─ DOCUMENT: answer from memory, confidence, reasoning
   └─ If FAIL (can answer) → STOP and redesign
   ↓
3B. SEARCH/API TOOLS TEST (GATE 2: must PASS = cannot answer with APIs)
   └─ EXECUTE: test with API tools → paste results
   └─ If FAIL (APIs can answer) → STOP and redesign
   ↓
4. SEARCH API DISCOVERY
   └─ EXECUTE: search API → paste results (for query design, not answer)
   ↓
5. SPARQL STRUCTURE
   └─ EXECUTE: SPARQL structure → paste results
   ↓
6. STRATEGY DECISION & FINAL SPARQL
   └─ DOCUMENT: strategy choice (comprehensive vs example-based)
   └─ EXECUTE: final SPARQL → paste results, verify answer
   ↓
7. INTEGRATION (if multi-DB)
   └─ TEST: cross-database links work
   ↓
8. PUBMED TEST (15 min, must show insufficiency)
   └─ EXECUTE: PubMed:search_articles x2 → list PMIDs
   ↓
9. SCORE & VALIDATE (≥9/12, checklist)
   └─ CALCULATE: score each dimension, justify
   ↓
10. DOCUMENT & UPDATE (⭐ FOLLOW QUESTION_FORMAT.md)
   └─ EXECUTE: write question file following canonical format
   └─ EXECUTE: update coverage tracker (new counts + percentages)
   └─ VALIDATE: check all required fields against QUESTION_FORMAT.md
```

---

## SUCCESS CRITERIA

**Every question must:**
1. ✅ Pass Training Knowledge Test (CANNOT answer from memory)
2. ✅ Pass Search/API Tools Test (CANNOT answer with search tools alone)
3. ✅ Score ≥9/12 (no dimension = 0)
4. ✅ Use precise wording (no ambiguous verbs)
5. ✅ Feature database as PRIMARY (not peripheral)
6. ✅ Use comprehensive SPARQL (for yes/no questions)
7. ✅ Fail PubMed test (requires RDF)
8. ✅ Maintain database balance (check tracker first)
9. ✅ Use structured properties (no text filters when possible)
10. ✅ Have bounded, verifiable scope
11. ✅ **SHOW PROOF OF EXECUTION for all tools**
12. ✅ **ALL SPARQL queries executed with non-empty results**
13. ✅ **PubMed:search_articles called with PMIDs listed**
14. ✅ **Search/API tools tested with actual results pasted**
15. ✅ **Follow QUESTION_FORMAT.md specification exactly**

**By end of 50 questions:**
- All 23 databases covered (Tier 1 ≥3, Tier 2-4 ≥1)
- UniProt ≤70%, GO ≤50%
- 60%+ integrate 2+ databases
- 10 each of factoid, yes/no, list, summary
- 20 choice questions

---

## FINAL SELF-CHECK BEFORE SUBMITTING

```
❓ ANSWER HONESTLY FOR EVERY QUESTION:

TWO GATES:
□ I attempted to answer from memory first (Gate 3A)
□ I CANNOT answer this question from training knowledge (PASS)
□ I tested with search/API tools (Gate 3B)
□ Search tools CANNOT fully answer this question (PASS)
□ If either gate failed, I redesigned the question

EXECUTION PROOF:
□ I called the search API and pasted actual results
□ I tested search/API tools and pasted results (Gate 3B)
□ I called run_sparql() at least twice and pasted results
□ I called PubMed:search_articles at least twice
□ All my SPARQL queries returned non-empty results

DOCUMENTATION:
□ My question_XXX.yaml shows actual tool outputs (not plans)
□ PMIDs are listed (not "various papers")
□ Example IDs are listed (not "found some entities")
□ Search/API test results are documented

FORMAT COMPLIANCE:
□ My question_XXX.yaml follows QUESTION_FORMAT.md specification
□ All required fields are present
□ RDF triples use correct comment format: # Database: X | Query: N | Comment: ...
□ exact_answer format matches question type
□ verification_score.passed is true
□ time_spent includes all phases

VERIFICATION:
□ I can point to tool output proving my answer
□ Score is calculated with justification
□ Score ≥9/12 with no dimension = 0

IF ANY □ UNCHECKED: QUESTION IS INVALID
```

---

## VERSION HISTORY

- **v4.3** (2025-02-11): Restored full guide with all detailed workflow steps; added explicit references to QUESTION_FORMAT.md canonical specification throughout; aligned step numbering with WORKSHEET (10 steps with 3A/3B gates)
- **v4.2** (2025-02-11): Added Step 3B (Search/API Tools Test) as mandatory second gate to filter out questions answerable by API tools alone
- **v4.1** (2025-02-11): Corrected Training Knowledge Test logic (PASS = cannot answer from memory)
- **v4.0** (2025-02-11): Added mandatory execution checkpoints and blocking gates
- **v3.0** (2025-02-11): Integrated BioASQ advantages with comprehensive scoring
- **v2.0** (2025-02-10): Initial QA_CREATION_GUIDE with MIE kw_search_tools emphasis
