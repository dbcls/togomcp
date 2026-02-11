# Question Creation Worksheet

**⚠️ FILL EVERY BLANK OR QUESTION IS INVALID ⚠️**

**📋 OUTPUT FORMAT: See QUESTION_FORMAT.md for canonical YAML specification**

---

## Q___ : _________________ (question type)

### 1. BALANCE CHECK
```
□ Read coverage_tracker.yaml
Featured database: _______________ (current %: _____)
Reason: _______________

⚠️ DATASET COMPOSITION TARGET:
Multi-database questions: Target 60-80% of total (30-40 out of 50)
Single-database questions: Maximum 20-40% (10-20 out of 50)

Current status: _____ multi-DB / _____ total = _____%
Decision: □ Multi-database (2-4 DBs) □ Single-database (justify: _______________)
```

### 2. MIE & KEYWORD
```
□ get_MIE_file(dbname="_____________")
kw_search_tools: _______________
Keyword selected: KW-____ (_______________)
```

### 3. RDF NECESSITY TESTS ⚠️ CRITICAL FILTERS - BOTH MUST PASS

#### 3A. TRAINING KNOWLEDGE TEST
```
Question: Can I answer this from training knowledge alone?
My answer attempt: _______________
Confidence: _______________ (none/low/medium/high)

Result: □ PASS (cannot answer → proceed to 3B)
        □ FAIL (can answer → reject and redesign)

PASS examples (cannot answer from memory):
  - "How many human proteins have BOTH PDB structures AND disease variants?"
  - "Which Rhea reactions are catalyzed by UniProt protein P12345?"
  - "What is the exact count of proteins with phosphorylation at position 100-110?"
  
FAIL examples (can answer from memory):
  - "How many reviewed nitrogen fixation proteins are in UniProt?" 
    → Can estimate ~700-800 from training
  - "What organisms perform nitrogen fixation?" 
    → Know: Rhizobium, Azotobacter, cyanobacteria
  - "What is the function of nitrogenase?" 
    → Know: converts N2 to NH3
```

#### 3B. SEARCH/API TOOLS TEST ⚠️ CRITICAL - MUST BE HONEST

**CORE PRINCIPLE: IF YOU CAN ANSWER IT WITH THE TOOLS, THEN THE TOOLS CAN ANSWER IT.**

```
Question: Can search/API tools answer this question WITHOUT using RDF/SPARQL?

⚠️ ANTI-RATIONALIZATION RULES:
1. "Requires manual parsing" = TOOLS CAN ANSWER (parsing is trivial)
2. "Requires counting results" = TOOLS CAN ANSWER (counting is trivial)
3. "Requires aggregating data" = TOOLS CAN ANSWER (if data is all in responses)
4. "No built-in GROUP BY" = NOT A VALID EXCUSE (users can group/count themselves)
5. If YOU successfully answered it with tools → TEST FAILS, question is INVALID

MANDATORY EXECUTION (ACTUALLY TRY TO ANSWER THE QUESTION):
□ Step 1: Call tool 1: _______________(params="_____________")
  Result: _______________
  
□ Step 2: Call tool 2 (if needed): _______________(params="_____________")
  Result: _______________
  
□ Step 3: Processing needed: _______________
  (e.g., "extract genus from scientific name", "count unique values", "parse JSON field")
  
□ Step 4: Did I successfully get the answer? □ Yes □ No
  
  If YES → Answer obtained: _______________
          TEST RESULT: FAIL (tools CAN answer)
          ACTION: REJECT this question
          
  If NO → Why tools failed: _______________
         TEST RESULT: PASS (tools cannot answer)
         ACTION: Proceed to design SPARQL queries

⚠️ CRITICAL EVALUATION CRITERIA:

TOOLS CAN ANSWER (TEST FAILS) when:
- All required data is in API responses
- Processing = simple parsing, filtering, counting, grouping
- Example: Extract genus from organism names + count unique → TRIVIAL
- Example: Parse JSON field + filter by value → TRIVIAL
- Example: Retrieve N results + apply local aggregation → TRIVIAL
- If you got the answer by calling tools, TEST FAILS regardless of "complexity"

TOOLS CANNOT ANSWER (TEST PASSES) when:
- Data requires graph traversal not exposed by API
- Multiple databases need joining beyond API capabilities  
- Requires ontology reasoning not available in search
- Computational complexity exceeds practical limits (e.g., cross-product of millions)
- Example: "Count GO terms with EXACTLY 3 children" → must check ALL terms, API doesn't expose this
- Example: "Proteins with kinase activity AND disease variants" → cross-DB join not in single API

PASS examples (tools genuinely insufficient):
  ✓ "How many GO terms have EXACTLY 3 direct children?"
    → getDescendants shows one term's descendants
    → Would need to call for EVERY GO term (100,000+) then aggregate
    → Computationally impractical, RDF query needed
    
  ✓ "Which proteins have kinase activity (GO) AND disease variants (ClinVar)?"
    → No single API joins UniProt + GO + ClinVar
    → Would need separate searches + manual cross-referencing
    → RDF enables direct cross-database join
    
  ✓ "What percentage of Rhea reactions involve ATP?"
    → search_rhea_entity("ATP") returns SOME reactions
    → But denominator requires counting ALL reactions
    → Would need text search on all 18,000+ reactions
    → RDF enables precise ChEBI IRI filtering

FAIL examples (tools CAN answer - REJECT these):
  ✗ "How many distinct genera have nifH genes?"
    → ncbi_esearch gets all genes
    → ncbi_esummary gets organism names
    → Extract genus (first word) + count unique
    → Answer obtained with tools → REJECT
    
  ✗ "What is the molecular formula of aspirin?"
    → search_chembl_molecule("aspirin") returns formula directly
    → Answer obtained with tools → REJECT
    
  ✗ "List human genes on chromosome 7"
    → ncbi_esearch(query="Homo sapiens[Organism] AND 7[Chromosome]")
    → Returns gene list directly
    → Answer obtained with tools → REJECT

HONESTY CHECK:
□ Did I actually TRY to answer with tools? (not just theorize)
□ If I got an answer, did I mark TEST as FAIL?
□ Am I being honest about what "trivial processing" means?
□ Would a competent user be able to answer this with the tools I tested?

Result: □ PASS (tools cannot answer → requires RDF)
        □ FAIL (tools CAN answer → REJECT question and redesign)
```

### 4. SEARCH API (MUST EXECUTE)
```
□ Tool: _______________(query="_____________")
Total results: _____
Example IDs: _____ _____ _____ _____ _____
Purpose: Find examples for SPARQL query design (not for answering question)
```

### 5. SPARQL STRUCTURE (MUST EXECUTE)
```
□ run_sparql(dbname="_____", query=...)
Key properties found: _______________ _______________ _______________
Results: □ Non-empty □ Empty (investigated why: _______)
```

### 6. FINAL SPARQL (MUST EXECUTE)
```
□ run_sparql(dbname="_____", query=...)
Strategy: □ Comprehensive □ Example-based
Answer from results: _______________
Verified: □ Yes
```

### 7. INTEGRATION (if multi-DB)
```
□ N/A - Single database
□ Tested: DB1(_____) × DB2(_____)
Integration pattern: _______________
```

### 8. PUBMED TEST (MUST EXECUTE 2x)
```
□ PubMed:search_articles(query="_____________")
  PMIDs: _______________
  Insufficient because: _______________

□ PubMed:search_articles(query="_____________")
  PMIDs: _______________
  Insufficient because: _______________
```

### 9. SCORE
```
Biological Insight:  ___/3 (why: _______________)
Multi-Database:      ___/3 (why: _______________)
Verifiability:       ___/3 (why: _______________)
RDF Necessity:       ___/3 (why: _______________)
────────────────────────
TOTAL:              ___/12  (minimum: 9)
```

### 10. FILES
```
□ question_XXX.yaml written (following QUESTION_FORMAT.md specification)
□ coverage_tracker.yaml updated (new %: ___%)
```

---

## 📋 OUTPUT FORMAT REQUIREMENTS

**Your question_XXX.yaml MUST follow the canonical format in QUESTION_FORMAT.md**

**Required top-level fields:**
```yaml
id: question_XXX
type: [yes_no | factoid | list | summary]
body: "Question text without database names"
inspiration_keyword:
  keyword_id: KW-XXXX
  name: "Keyword name"
  category: "Category"
togomcp_databases_used:
  - database1
  - database2
verification_score:
  biological_insight: [0-3]
  multi_database: [0-3]
  verifiability: [0-3]
  rdf_necessity: [0-3]
  total: [0-12]
  passed: true
pubmed_test:
  time_spent: "15 minutes"
  method: "Description"
  result: "What was found"
  conclusion: "PASS (cannot answer)"
sparql_queries:
  - query_number: 1
    database: "dbname"
    description: "What this query does"
    query: |
      PREFIX declarations
      SELECT ...
    result_count: N
rdf_triples: |
  @prefix declarations
  <subject> <predicate> <object> .
  # Database: X | Query: N | Comment: ...
exact_answer: [varies by type]
ideal_answer: |
  One paragraph synthesis for domain experts
question_template_used: "Template N (Name)"
time_spent:
  exploration: "N minutes"
  formulation: "N minutes"
  verification: "N minutes"
  pubmed_test: "15 minutes"
  extraction: "N minutes"
  documentation: "N minutes"
  total: "N minutes"
```

**See QUESTION_FORMAT.md for:**
- Complete field specifications
- Format requirements by question type
- RDF triples comment format
- Validation rules
- Complete examples

---

**✓ ALL BOXES CHECKED? → Question valid**  
**✗ ANY BLANK/UNCHECKED? → Question invalid**  
**✗ FORMAT DOESN'T MATCH QUESTION_FORMAT.md? → Question invalid**
