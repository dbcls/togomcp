# TogoMCP Question Generation - Phase 1: Database Exploration

## Quick Reference
- **Goal**: Thoroughly explore databases to prepare for question generation (DO NOT create questions yet)
- **Output**: Exploration reports in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
- **Token Management**: STOP at ~180K tokens (Opus 4.5 has 200K context). Quality over quantity.
- **Key Focus**: Biological/scientific content, not IT infrastructure
- **Anti-Trivial**: Find facts requiring actual queries, not just MIE file reading

---

## Setup (First Session Only)

1. **Check existing progress**:
   - Look for exploration reports in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
   - If reports exist, note which databases are DONE and skip them

2. **Read these context files**:
   - `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/QUESTION_DESIGN_GUIDE.md`
   - `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/QUESTION_FORMAT.md`
   - `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/example_questions.json`

3. **List available databases**: Run `list_databases()`

4. **Create exploration directory** (if it doesn't exist):
   ```
   /Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/
   ```

---

## CRITICAL WORKFLOW RULE

⚠️ **EXPLORE → REPORT → (EVERY 3: PROGRESS) → NEXT DATABASE** ⚠️

**DO THIS**:
1. Explore database #1
2. **IMMEDIATELY write report for database #1**
3. Explore database #2
4. **IMMEDIATELY write report for database #2**
5. Explore database #3
6. **IMMEDIATELY write report for database #3**
7. **SAVE PROGRESS REPORT** (checkpoint: 3 databases done)
8. Explore database #4
9. **IMMEDIATELY write report for database #4**
10. Explore database #5
11. **IMMEDIATELY write report for database #5**
12. Explore database #6
13. **IMMEDIATELY write report for database #6**
14. **SAVE PROGRESS REPORT** (checkpoint: 6 databases done)
15. Continue pattern...

**DO NOT DO THIS**:
1. Explore database #1
2. Explore database #2
3. Explore database #3
4. Try to write all reports ❌ (will hit token limit!)
5. No progress checkpoints ❌ (can't resume if interrupted!)

**Why**: 
- Writing reports immediately prevents token overflow and captures findings while fresh
- Progress checkpoints every 3 databases enable resuming if interrupted
- Regular saves protect against context limit or session issues

---

## Exploration Workflow

For EACH database that needs exploration:

### 1. Read MIE File
- Call `get_MIE_file(dbname)`
- Study the ShEx schema (properties, relationships)
- Review RDF examples (data patterns)
- Study ALL SPARQL query examples
- **CRITICAL**: MIE examples are for learning query patterns - NOT for direct use in questions
  * Don't create questions that just reproduce MIE SPARQL queries
  * Don't use the same entities shown in MIE examples
  * Adapt query patterns to find DIFFERENT, real entities

### 2. Explore Content (Go Beyond MIE Examples!)

**CRITICAL**: Don't just read MIE files—actually query the database!

Run at least:
- **5 search queries** using `search_*` functions to find REAL entities
- **3 SPARQL queries** adapted from MIE examples but using DIFFERENT entities
- Try variations to understand data scope and diversity
- Look for specific, interesting entities NOT mentioned in MIE file

**Example - BAD (trivial)**:
- MIE shows example: "UniProt:P12345"
- Question: "What is the organism for UniProt:P12345?" ❌ (just reading MIE)

**Example - GOOD (requires query)**:
- Run search: `search_uniprot_entity("BRCA1 human")`
- Find real ID: P38398
- Question: "What is the UniProt ID for human BRCA1?" ✅ (requires actual lookup)

### 3. Document Cross-References (CRITICAL)

When exploring mappings between databases, distinguish:

**Entity Count** = Number of unique entities WITH mappings
```sparql
SELECT (COUNT(DISTINCT ?entity) as ?entity_count)
WHERE { ?entity <mapping_property> ?target . }
```

**Relationship Count** = Total number of mapping relationships
```sparql
SELECT (COUNT(?target) as ?relationship_count)
WHERE { ?entity <mapping_property> ?target . }
```

**Why both matter**: Some entities map to multiple targets
- Example: 2,150 diseases have mappings (entity count)
- Example: 2,341 total mappings exist (relationship count)
- Questions can ask about either count—document BOTH

**Mapping Distribution** (if entities have multiple mappings):
```sparql
SELECT ?mapping_count (COUNT(?entity) as ?entity_count)
WHERE {
  { SELECT ?entity (COUNT(?target) as ?mapping_count)
    WHERE { ?entity <mapping_property> ?target . }
    GROUP BY ?entity
  }
}
GROUP BY ?mapping_count
ORDER BY ?mapping_count
```

### 4. IMMEDIATELY Create Exploration Report (CRITICAL!)

⚠️ **DO NOT WAIT - CREATE THE REPORT IMMEDIATELY AFTER EXPLORING EACH DATABASE** ⚠️

**Why immediate**: Prevents token overflow, ensures findings are captured while fresh, allows continuation if stopped.

Save to: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/[dbname]_exploration.md`

#### Required Report Structure:

```markdown
# [Database Name] Exploration Report

## Database Overview
- Purpose and scope
- Key data types and entities

## Schema Analysis (from MIE file)
- Main properties
- Important relationships
- Query patterns

## Search Queries Performed
1. Query: [term] → Results: [summary of REAL entities found]
2. Query: [term] → Results: [summary of REAL entities found]
3. [etc., at least 5 total]

**Note**: Document actual entities discovered, not just MIE examples

## SPARQL Queries Tested
```sparql
# Query 1: [purpose - adapted from MIE with different entities]
[SPARQL query]
# Results: [summary of REAL data returned]
```

[At least 3 queries with REAL results]

**CRITICAL - Using MIE SPARQL Examples Correctly:**

❌ **BAD - Direct Copy from MIE**:
- MIE shows: `SELECT ?name WHERE { uniprot:P12345 up:recommendedName ?name }`
- You document: "Query tested: Get name for P12345"
- Problem: Just copied MIE example verbatim

✅ **GOOD - Adapted with Real Entities**:
- MIE shows: `SELECT ?name WHERE { ?protein up:recommendedName ?name }`
- You run: `SELECT ?name WHERE { uniprot:Q99ZW2 up:recommendedName ?name }`
- You document: "Query tested: Get protein name for SpCas9 (Q99ZW2), found via search"
- Result: You discovered Q99ZW2 is a real entity worth documenting for questions

## Cross-Reference Analysis (if applicable)
**Entity counts** (unique entities with mappings):
- [Source] → [Target]: X entities have mappings

**Relationship counts** (total mappings):
- [Source] → [Target]: Y total mappings

**Distribution** (if one-to-many):
- Z entities with 1 mapping
- Z entities with 2 mappings
- Z entities with 3+ mappings

## Interesting Findings

**Focus on discoveries requiring actual database queries:**

✅ **GOOD (non-trivial)**:
- "Found 2,150 NANDO diseases with MONDO mappings (requires COUNT query)"
- "BRCA1 (UniProt P38398) has 15 PDB structures (requires cross-database lookup)"
- "Kinase inhibitors in ChEMBL with IC50 < 100 nM: 347 compounds (requires filtering)"
- "Most common resistance mechanism in AMR Portal: efflux pump (requires aggregation)"

❌ **BAD (trivial - just reading MIE)**:
- "Example entity in MIE: UniProt:P12345" (no query needed)
- "MIE shows this SPARQL pattern works" (just documentation)
- "Database has organism property" (schema info, not data)

**Document**:
- Specific entities found through searches (NOT MIE examples)
- Unique properties/patterns discovered through queries
- Database connections requiring real lookups
- Verifiable facts from actual data (not MIE metadata)

## Question Opportunities by Category

**FOCUS ON BIOLOGICAL CONTENT** ✅
- Biological entities (proteins, genes, diseases, compounds)
- Scientific properties (sequences, structures, molecular weights)
- Research-relevant metadata (clinical significance, resistance)
- Methodology when interpretation-critical (AST methods, resolution)

**FOCUS ON EXPERT-RELEVANT QUESTIONS** ✅
Ask: "Would a real biologist/biomedical researcher actually want to know this?"

Examples of expert-relevant questions:
- ✅ "What is the IC50 of imatinib for EGFR?" (drug development)
- ✅ "How many pathogenic BRCA1 variants are in ClinVar?" (clinical genetics)
- ✅ "What resistance mechanisms are most common for E. coli?" (epidemiology)
- ✅ "Which kinases are targeted by approved drugs in ChEMBL?" (pharmacology)

Examples of non-expert questions (technically valid but not realistic):
- ⚠️ "What is the 15th protein alphabetically in UniProt?" (arbitrary, no research value)
- ⚠️ "How many proteins have IDs starting with 'Q'?" (ID trivia, not biology)
- ⚠️ "What is the shortest protein name in the database?" (curiosity, not research)
- ⚠️ "Which database has the most entries?" (comparison trivia, not science)

**AVOID INFRASTRUCTURE METADATA** ❌
- Database versions/release numbers
- Software tools (unless methodology-critical)
- Administrative metadata
- Pure IT infrastructure

**AVOID STRUCTURAL METADATA** ❌
- Classification system codes (MeSH tree numbers, ICD codes) - ask about the diseases/concepts themselves, not their organizational codes
- Namespace prefixes or URI patterns
- Property names or relationship types
- Schema structure questions
- Structural/organizational metadata (tree numbers, classification codes, namespace prefixes)
- Database schema details (property names, relationship types)

**AVOID TRIVIAL QUERIES** ❌
- Questions answerable by reading MIE file
- Questions using only example entities from MIE
- Questions about schema structure (not real data)

### Suggested Questions:

**Precision**: Specific IDs, measurements, sequences (for REAL entities)
- ✅ "What is the UniProt ID for human BRCA1?" (requires search)
- ❌ "What is the organism for UniProt:P12345?" (P12345 is from MIE example)

**Completeness**: Entity counts, comprehensive lists (from actual queries)
- ✅ "How many kinase structures in PDB?" (requires COUNT query)
- ✅ "How many proteins HAVE GO annotations?" (entity count from query)
- ❌ "How many example queries are in the MIE file?" (just counting docs)

**Integration**: Cross-database linking, ID conversions (for real lookups)
- ✅ "Convert UniProt P38398 to NCBI Gene ID" (requires togoid or cross-db query)
- ❌ "What properties link to other databases?" (schema info)

**Currency**: Recent biological discoveries, updated classifications
- ✅ "What COVID-19 pathways added to Reactome in 2024?" (requires date filtering)
- ❌ "What is the current database version?" (infrastructure metadata)

**Specificity**: Rare diseases, specialized organisms, niche compounds
- ✅ "What is the NANDO ID for Fabry disease?" (requires search for real disease)
- ❌ "What is an example rare disease in NANDO?" (trivial if MIE shows example)

**Structured Query**: Complex biological queries, multiple criteria
- ✅ "Find kinase inhibitors with IC50 < 100 nM" (requires filtering real data)
- ✅ "Find diseases mapping to exactly 2 MONDO IDs" (requires aggregation)
- ❌ "Show example of SPARQL query with FILTER" (just documentation)

## Notes
- Limitations or challenges
- Best practices for querying
- Important clarifications about counts
- Distinction between MIE examples and real data findings
```

---

## Token Management

**After EACH database (including report writing)**:
- Check token usage
- If approaching ~180K tokens → **STOP IMMEDIATELY and save progress**
- Opus 4.5 has 200K context window; leave buffer for completion message
- Do NOT rush through remaining databases
- Quality over quantity

**After EVERY 3 databases (or before token limit)**:
- **Save progress report** to `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_PROGRESS.md`
- Update counts of completed vs remaining databases
- Document current token usage
- This ensures continuity if exploration is interrupted

**Workflow Pattern**:
```
Database 1: Explore (10K tokens) + Report (3K tokens) = 13K used
Database 2: Explore (12K tokens) + Report (4K tokens) = 16K used (29K total)
Database 3: Explore (15K tokens) + Report (5K tokens) = 20K used (49K total)
→ SAVE PROGRESS REPORT (1K tokens) = 50K total
Database 4: Explore (10K tokens) + Report (3K tokens) = 13K used (63K total)
Database 5: Explore (11K tokens) + Report (4K tokens) = 15K used (78K total)
Database 6: Explore (14K tokens) + Report (4K tokens) = 18K used (96K total)
→ SAVE PROGRESS REPORT (1K tokens) = 97K total
...
Check after each: Still under 180K? Continue : Stop and save final progress
```

**Why write reports immediately**:
- Prevents accumulating too much context before documenting
- Ensures findings are saved if token limit is hit
- Allows accurate tracking of remaining capacity
- Fresh memory = better reports

**Why save progress every 3 databases**:
- Provides checkpoint for resuming if interrupted
- Documents momentum and patterns observed
- Tracks token usage trends
- Enables better session planning

### When Stopping Early (or Every 3 Databases)

**Update or Create**: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_PROGRESS.md`

**After every 3 databases OR when approaching token limit**, update this file:

```markdown
# Exploration Progress

## Current Session - [Date]

### Session Summary
- Databases explored this session: [N]
- Total databases completed: [X] of [Total]
- Token usage: ~[Y]K / 200K (Opus 4.5)
- Status: [In Progress / Paused / Complete]

### Completed ([X] of [Total])
- [database1] ✅ (Session [N])
- [database2] ✅ (Session [N])
- [database3] ✅ (Session [N])
- [database4] ✅ (Session [N-1])
- [etc.]

### Remaining ([Y] remaining)
- [database_a] ⏳
- [database_b] ⏳
- [etc.]

### Session Notes
- [Observations about explored databases]
- [Patterns or challenges noticed]
- [Token usage trends: databases averaging ~XK tokens each]
- [Estimated remaining capacity: can fit ~N more databases]

### Next Steps
- [Which databases to prioritize next session]
- [Any special considerations for remaining databases]
```

**Update frequency**:
- ✅ After every 3rd database exploration
- ✅ Before hitting token limit (~180K)
- ✅ When ending a session (even if <3 databases done)

**Why update regularly**:
- Checkpoint progress for resuming
- Track token usage patterns
- Plan remaining work
- Document insights while fresh

**Then respond with**:
```
⏸️ EXPLORATION PAUSED - TOKEN LIMIT APPROACHING

Explored [X] of [Y] databases in this session:
✅ Completed: [list]
⏳ Remaining: [list]

All exploration reports saved to /Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/

To continue: Run this prompt again. It will automatically skip completed databases.

DO NOT proceed to question generation until ALL databases are explored.
```

---

## Completion (All Databases Explored)

Create: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_SUMMARY.md`

```markdown
# Database Exploration Summary

## Overview
- Total databases explored: [N]
- Total sessions: [N]

## All Explored Databases
[List with brief descriptions]

## Database Coverage Plan for 120 Questions
Recommended distribution based on:
- Database richness (data diversity, not just schema size)
- Unique content (findings not in other databases)
- Integration opportunities (useful cross-database queries)

Suggested allocation:
- [database1]: ~[X] questions
- [database2]: ~[Y] questions
- [etc.]

## Database Characteristics

### Rich Content (good for multiple questions)
- [databases with diverse, queryable data]

### Specialized Content (good for specificity)
- [databases with niche/unique data]

### Well-Connected (good for integration)
- [databases with useful cross-references]

## Cross-Database Integration Opportunities
[Multi-database question possibilities requiring actual lookups]

## Recommendations
- Insights for question generation
- Databases that pair well for integration questions
- Particularly interesting findings (from queries, not MIE)
```

**Then respond with**:
```
✅ EXPLORATION COMPLETE

Explored ALL [N] databases:
- [list]

All exploration reports saved.
Summary with coverage plan created.

Ready for Phase 2: Question Generation.
```

---

## Important Reminders

✅ **DO**:
- Thoroughly explore each database with REAL queries
- **IMMEDIATELY write exploration report after each database (don't wait!)**
- **Save progress report after every 3 databases** (checkpoint for resuming)
- Document both entity and relationship counts for cross-references
- Focus on biological/scientific content discovered through queries
- Find actual entities (not just MIE examples)
- Check token usage after each database + report
- Stop when approaching token limit (~180K for Opus 4.5)
- Preserve existing exploration reports across sessions

❌ **DON'T**:
- Create questions yet (that's Phase 2)
- Explore multiple databases before writing reports ❌ (will hit token limit!)
- Skip progress checkpoints ❌ (can't resume efficiently!)
- Just read MIE files and call it exploration
- Document only example entities from MIE
- Focus on database versions or IT metadata
- Rush through databases to finish
- Continue past token limit
- Suggest questions answerable from MIE alone

---

**Begin by checking for existing exploration reports, then proceed with thorough exploration using REAL database queries. WRITE EACH REPORT IMMEDIATELY after exploring that database. SAVE PROGRESS after every 3 databases.**