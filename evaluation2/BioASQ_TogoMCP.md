# BioASQ Benchmark Guidelines - TogoMCP Edition (v2.5)

## Core Principle: Biology First, Integration Essential

Questions must:
1. Ask biological questions researchers care about
2. Require integration across 2+ databases (≥60% of questions)
3. Be verifiable (single answer, ≤10 items, or aggregate)
4. Need RDF (impossible from literature alone)
5. Showcase database diversity

**Integration Methods:**
- **Method A**: Search APIs (exploratory) → SPARQL validation (comprehensive)
- **Method B**: Pure SPARQL across databases via cross-references

**Critical**: Search APIs find examples; SPARQL provides comprehensive evidence. Never use search results alone for yes/no questions or hardcode them in VALUES clauses.

---

## Question Wording: Avoid Ambiguity

**Be precise about:**
1. **Native vs. experimental properties**: "native cofactor" not just "bind"
2. **Annotation vs. structure data**: Specify source
3. **Total vs. filtered counts**: Make scope clear

**Red flags**: bind, contain, have, associated with, interact with, found in, related to
→ Add qualifying language: "natively", "annotated with", "crystallized with"

---

## Comprehensive vs. Example-Based Queries

**WRONG (circular reasoning):**
```
Search API finds 8 examples → VALUES clause with those 8 IDs → Verify only those 8
```

**CORRECT (comprehensive):**
```
Search API finds patterns → SPARQL with bif:contains on ALL entities → Aggregate results
```

**When to use each:**
- **Example-based**: Top-N ranking, specific lookups
- **Comprehensive**: Yes/no questions, phylogenetic distribution, existence claims

---

## Requirements

### Targets
- 50 total questions
- ≥30 (60%) integrate 2+ databases
- ≥10 (20%) integrate 3+ databases
- Type distribution: ≥10 each of factoid, yes/no, list, summary

### Database Balance
- **UniProt cap**: ≤70% (max 35 of 50)
- Use tracker to avoid overused databases

### Quality Standards
- Biological relevance (researchers care about answer)
- Integration-driven (clear cross-database links)
- Verifiable scope (bounded)
- RDF-necessary (cannot answer from PubMed OR training knowledge)
- Random keyword selection (no thematic bias)
- Comprehensive queries for yes/no questions

---

## Question Types

**Factoid**: Single answer via graph traversal/aggregation
**Yes/No**: Binary with EXISTS/NOT EXISTS - requires comprehensive SPARQL
**List**: Enumerate ≤10 items with ranking/filtering  
**Summary**: Single paragraph synthesis (NO multiple paragraphs, NO line breaks)

---

## Must Have / Must Not Have

**✅ Required:**
1. Biological insight (not database inventory)
2. Multi-database integration (60%+)
3. Complete verifiability
4. RDF necessity
5. Comprehensive analysis (yes/no questions)

**❌ Prohibited:**
1. Pure database inventory
2. Ontology structure questions
3. Unbounded scopes
4. Literature-recoverable answers
5. Search-only answers
6. Training knowledge answerable
7. Example-based comprehensive claims

---

## Scoring Rubric

Score 0-3 each dimension (total ≥8, no zeros):

- **Biological Insight**: 3=mechanisms/patterns, 0=inventory
- **Multi-Database**: 3=3+ DBs, 2=2 DBs, 1=single DB, 0=search-only
- **Verifiability**: 3=single/≤5 items, 0=unbounded
- **RDF Necessity**: 3=impossible without RDF, 0=PubMed/training knowledge

---

## Workflow (7 Steps)

### 1. Planning (Filesystem tools)
1. Read keywords.tsv and coverage_tracker.yaml
2. **Select keyword RANDOMLY** (count unused, generate random number, select by position)
3. Run `list_databases()` to review available databases
4. Identify underused databases (prioritize DDBJ, Glycosmos, MeSH, PubMed, Ensembl)
5. Identify 2-3 databases that connect for this keyword
6. Read MIE files with `get_MIE_file`
7. Formulate biological question
8. Determine question type (comprehensive vs. example-based)

### 1.5. Training Knowledge Self-Test 🔴 MANDATORY
1. Attempt to answer from memory
2. Document what you know and confidence level
3. **PASS** if: requires current DB values, cross-DB integration, temporal data
4. **FAIL** if: can answer with confidence, web searchable, historical fact, textbook knowledge
5. Document test in YAML
6. If FAIL: reformulate or abandon

### 2. Discovery (TogoMCP tools)
1. Execute search APIs (exploratory - find patterns)
2. Map cross-database links (entity IDs, cross-references)
3. Optional: Initial SPARQL exploration
4. Identify 3-5 examples
5. Plan comprehensive vs. example-based approach
6. Assess feasibility

### 3. Validation (TogoMCP tools)
1. Write SPARQL queries:
   - **Comprehensive**: bif:contains with multiple synonyms
   - **Example-based**: VALUES with specific IDs
2. Test queries
3. Validate cross-database integration
4. Extract RDF triples
5. Document data flow

### 4. PubMed Test
1. Try 2-3 search queries
2. Document queries, PMIDs, why they fail
3. Explain why RDF database essential

### 5. Documentation (Filesystem:write_file)
Create YAML with:
- Basic info (id, type, body, keyword)
- databases_used, search_apis_used
- training_knowledge_test (from Step 1.5)
- verification_score (with rationale)
- pubmed_test
- sparql_queries (with discovery_method)
- rdf_triples
- exact_answer, ideal_answer (single paragraph only)

Save to `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml`
Update `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml`

### 6. Validation
Read back YAML and verify:
- Structure correct
- training_knowledge_test present
- Comprehensive SPARQL (not VALUES for yes/no)
- Single paragraph ideal_answer
- All RDF triples present
- Database balance maintained

---

## Common Pitfalls

1. Circular reasoning with search results
2. UniProt dependency
3. Famous associations (textbook knowledge)
4. Search-only questions
5. Example-based yes/no questions
6. Multi-paragraph summaries
7. Vague integration
8. Keyword clustering (use RANDOM selection)
9. Organism bias
10. Missing RDF triples
11. Workspace confusion
12. Skipping training knowledge test
13. Insufficient search terms

**Self-audit checklist:**
- [ ] Random keyword selection
- [ ] Completed training knowledge test
- [ ] Not answerable from training knowledge
- [ ] Not answerable from PubMed
- [ ] Database balance checked
- [ ] Comprehensive SPARQL for yes/no
- [ ] Multiple synonyms/variations
- [ ] RDF triples complete
- [ ] Single paragraph (summary type)
- [ ] Underused database used
- [ ] Integration pattern clear

---

## Database-Specific Strategies (Priority Databases)

**DDBJ**: Sequence → annotation → function
**Glycosmos**: Glycan → protein → disease
**MeSH**: Disease term → genes → druggability
**PubMed**: Literature → database validation
**Ensembl**: Ortholog analysis → function conservation
**Taxonomy**: Phylogeny → protein/gene distribution (⚠️ query ALL organisms, aggregate by phylum)
**PubChem**: Compound properties → bioactivity → targets
**ChEBI**: Chemical classification → biological activity
**Rhea**: Reaction → enzyme → distribution

---

## Key Principles

1. Biology first (not database metadata)
2. Integration via multiple queries (60%+)
3. Requires current database state
4. Search discovers, SPARQL validates
5. Comprehensive for yes/no (bif:contains, not VALUES)
6. Verifiable scopes
7. Score ≥8
8. Database diversity (UniProt ≤70%)
9. **Random keyword selection**
10. Filesystem for user's computer
11. Single paragraph summaries
12. **Mandatory training knowledge test**
13. Avoid circular reasoning

**Integration model**: Search API (exploratory) → comprehensive SPARQL → combine results

---

## Version History

- **v2.5** (2025-02-07): Added precise question wording guidelines, ambiguity checklist
- **v2.4** (2025-02-06): Comprehensive vs. example-based queries, circular reasoning warnings
- **v2.3** (2025-02-05): Removed time estimates
- **v2.2** (2025-02-05): Enforced random keyword selection
- **v2.1** (2025-02-05): Added mandatory training knowledge self-test
- **v2.0** (2025-02-05): Database balance requirements, integration patterns
