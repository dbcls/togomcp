# TogoMCP Question Creation - Quick Guide (v4.3)

**Use QUESTION_WORKSHEET.md while working. This is reference only.**

---

## Core Rules

1. **Check balance FIRST** - Never start without reading coverage_tracker.yaml
2. **Read MIE file** - Always check `kw_search_tools` field
3. **Execute everything** - Every tool must be called with results documented
4. **Follow canonical format** - See QUESTION_FORMAT.md for exact YAML specification
5. **No circular reasoning** - Don't use search API results in VALUES for comprehensive queries
6. **Structured properties first** - Avoid text filters (bif:contains only when necessary)
7. **TWO critical gates** - Training test AND Search/API test must both PASS

---

## Workflow (10 Steps)

```
1. Balance → 2. MIE & Keyword → 3A. Training Test (GATE 1) → 3B. Search/API Test (GATE 2) → 
4. Search API → 5. SPARQL Structure → 6. Final SPARQL → 7. Integration → 8. PubMed → 9. Score → 10. Files
```

---

## Critical Gates (BOTH MUST PASS)

### Gate 1: Training Knowledge Test (Step 3A)
```
Question: Can I answer from training knowledge alone?

❌ FAIL (REJECT): Can answer from training
"How many nitrogen fixation proteins in UniProt?"
→ Can estimate ~700-800 from training knowledge

✅ PASS (ACCEPT): Cannot answer from training
"How many human proteins have BOTH PDB structures AND ClinVar disease variants?"
→ Requires actual database cross-reference query
```

### Gate 2: Search/API Tools Test (Step 3B)
```
Question: Can search/API tools answer this WITHOUT SPARQL?

❌ FAIL (REJECT): Search tools CAN answer
"How many direct children does GO:0097190 have?"
→ OLS4:getDescendants returns directParent info → can filter and count

✅ PASS (ACCEPT): Search tools CANNOT answer
"How many GO terms have EXACTLY 3 direct children?"
→ getDescendants shows descendants but can't aggregate counts across all terms
→ Requires SPARQL to iterate and count across entire database

✅ PASS (ACCEPT): Search tools insufficient
"How many GO biological process terms have Reactome cross-references?"
→ Search finds examples but can't filter by hasOBONamespace property + count
→ Requires SPARQL property filtering + aggregation
```

**Purpose:** Ensure questions require RDF/SPARQL capabilities, not just API calls
- **PASS** = Search tools insufficient → Good question
- **FAIL** = Search tools can answer → Bad question, redesign

---

## Critical Patterns

### Database Balance
- **UniProt: ≤35 questions (70% max)**
- **GO: ≤25 questions (50% max)**
- Skip if >45%, prioritize if <5%

### Search Then SPARQL
```
✅ CORRECT:
1. ncbi_esearch → Get pattern/IDs (for query design, not answer)
2. SPARQL with structured properties
3. Aggregate comprehensive results

❌ WRONG:
1. ncbi_esearch → Get 8 IDs
2. SPARQL with VALUES [those 8 IDs]
3. Count only those 8 ← Circular!
```

### Integration
```
Always use VALUES pre-filtering:

VALUES ?gene_uri { 
  <http://ncbi.nlm.nih.gov/gene/672>
  <http://ncbi.nlm.nih.gov/gene/4607>
}

Then join across graphs.
```

### Question Wording
```
❌ Vague: "Which proteins bind magnesium?"
✅ Precise: "Which proteins are annotated with native magnesium cofactor binding?"
```

---

## Tools Reference

**User files:**
- `Filesystem:read_text_file(path)`
- `Filesystem:write_file(content, path)`

**RDF databases:**
- `TogoMCP-Test:get_MIE_file(dbname)`
- `TogoMCP-Test:run_sparql(dbname, sparql_query)` or `endpoint_name`
- `TogoMCP-Test:ncbi_esearch(database, query, max_results)`
- `TogoMCP-Test:search_*_entity(query, limit)`

**Ontology APIs (for testing insufficiency):**
- `OLS4:searchClasses(ontologyId, query)`
- `OLS4:getDescendants(classIri, ontologyId)`
- `OLS4:getAncestors(classIri, ontologyId)`

**Validation:**
- `PubMed:search_articles(query, max_results)`

---

## Scoring (≥7/9 required)

| Dimension | 3 | 2 | 1 | 0 |
|-----------|---|---|---|---|
| **Bio Insight** | Mechanisms | Relationships | Facts | Inventory |
| **Multi-DB** | 3+ DBs | 2 DBs | 1 DB+refs | Search only |
| **Verifiability** | ≤5 items | ≤10 items | ≤20 items | Unbounded |
| **RDF Necessity** | Impossible | Very hard | Tedious | Not needed |

---

## Question Types

- **Factoid:** Single answer (count, name, etc.)
- **Yes/No:** Binary (use comprehensive SPARQL)
- **List:** ≤10 ranked items
- **Summary:** 3-5 sentence paragraph
- **Choice:** Multiple choice (4 options)

---

## File Locations

```
FORMAT: /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_FORMAT.md ⭐ CANONICAL SPECIFICATION
Input:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv
Track:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml
Output: /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml
```

⚠️ **CRITICAL**: All question files MUST follow the canonical format specified in QUESTION_FORMAT.md
- See QUESTION_FORMAT.md for complete field specifications and validation rules
- Required fields: id, type, body, inspiration_keyword, togomcp_databases_used, verification_score, pubmed_test, sparql_queries, rdf_triples, exact_answer, ideal_answer, question_template_used, time_spent

---

## Requirements Summary

**Coverage:** All 23 databases (Tier 1 ≥3 each, Tier 2-4 ≥1 each)  
**Types:** 10 factoid, 10 yes/no, 10 list, 10 summary, 20 choice  
**Integration:** 60%+ use 2+ databases  
**Quality:** All score ≥7/9, pass BOTH gates (training + search/API), fail PubMed test  
**Format:** Follow QUESTION_FORMAT.md specification exactly

---

**For detailed workflow steps, see QUESTION_WORKSHEET.md (10 steps with execution checkpoints)**  
**For format specification, see QUESTION_FORMAT.md**  
**For comprehensive guidelines, see QA_CREATION_GUIDE.md**
