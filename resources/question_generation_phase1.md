# TogoMCP Question Generation - Phase 1: Database Exploration
# REVISED VERSION - Natural Language Questions (No Tool References)

## Quick Reference
- **Goal**: Thoroughly explore ONE database per session, focusing on COMPLEX queries
- **Workflow**: Explore → Report → STOP (continue next database in new session)
- **Output**: Exploration reports in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
- **Key Focus**: Complex query patterns, cross-database connections, performance-critical queries
- **CRITICAL**: Generated questions must sound natural - NO explicit tool/technology mentions
- **No Rush**: Take time for thorough exploration - quality over speed

---

## IMPORTANT: Natural Language Question Principle

⚠️ **Questions Must NOT Mention Technical Implementation** ⚠️

The evaluation questions are designed to test whether TogoMCP can correctly interpret and answer researcher questions. Therefore, questions should be phrased naturally, as a biologist or researcher would ask them.

**❌ AVOID in questions**:
- "SPARQL", "query", "RDF", "triple"
- "API", "endpoint", "tool", "function"
- "MIE file", "schema", "ontology lookup"
- "Full-text search", "bif:contains"
- "ID conversion", "togoid", "cross-reference"
- "GRAPH", "URI", "property path"
- Database-specific technical terms (unless the researcher would naturally use them)

**✅ NATURAL phrasing examples**:
- Instead of "Use SPARQL to query UniProt for..." → "What human proteins are involved in..."
- Instead of "Search using full-text search for..." → "Find proteins related to..."
- Instead of "Convert UniProt ID to NCBI Gene ID using togoid..." → "What is the NCBI Gene ID for protein X?"
- Instead of "Query the Rhea database API for..." → "What biochemical reactions involve..."

**The technical details belong in the NOTES field, not in the question itself.**

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

⚠️ **ONE DATABASE PER SESSION** ⚠️

**Session Workflow**:
1. Choose ONE unexplored database
2. Thoroughly explore that database (no rushing)
3. Create detailed exploration report
4. **STOP - End session**
5. Next session: Continue with next database

**Why One Database Per Session?**
- Allows thorough, unhurried exploration
- Prevents context overflow
- Ensures high-quality documentation
- Makes progress trackable and resumable
- Avoids fatigue-induced errors

**Progress Tracking**:
- Each completed exploration creates a `[dbname]_exploration.md` file
- Check `/evaluation/exploration/` directory to see what's done
- Pick next unexplored database from the list

---

## Focus: Questions That Require Deep Database Knowledge

### Primary Goal: Find Queries That Need Expert Knowledge

The purpose of this exploration is to identify question patterns that:
1. **Cannot be answered** without understanding the database structure
2. **Will fail or produce wrong results** without optimization
3. **Require specific knowledge** of how databases connect
4. **Demonstrate the complexity** of real biological research questions

### What Makes a Question "Complex"?

✅ **COMPLEX (Focus on these)**:

**Cross-Database Questions**
- Questions spanning 2+ databases requiring knowledge of:
  * How entities relate across databases
  * What information exists in each database
  * How to efficiently combine information
- Example: "Which human enzymes catalyze reactions that involve ATP?"
  (Needs: protein database + reaction database + compound database)

**Questions Requiring Optimization**
- Questions on large datasets requiring:
  * Efficient filtering strategies
  * Proper ordering of conditions
- Example: "How many human kinases have autophagy-related annotations?"
  (Large dataset needs smart filtering)

**Questions with Known Pitfalls**
- Questions where naive approaches fail:
  * Text search combined with complex conditions
  * Missing scope specifications causing wrong results
  * Inefficient ordering causing timeouts
- Example: "Find proteins whose description mentions 'membrane receptor'"
  (Text search has specific requirements)

**Questions Requiring Structural Knowledge**
- Questions needing understanding of data organization:
  * Multiple data sections per database
  * Relationships between data types
  * Correct scoping of queries
- Example: "Find publications cited in UniProt entries about TP53"
  (Publications stored separately from main protein data)

❌ **SIMPLE (De-emphasize these)**:

**Simple Entity Lookups**
- Direct search for a single entity
- Basic property retrieval
- Simple counting without complex filtering
- Example: "What is the UniProt ID for BRCA1?"

**Straightforward Aggregations**
- Simple counts without performance concerns
- Basic grouping operations
- Example: "How many proteins are in the database?"

**Direct ID Lookups**
- Questions using standard identifiers directly
- Simple cross-references
- Example: "What are the child terms of GO:0006914?"

---

## Thorough Exploration Workflow

**Remember**: You have ONE database for this entire session. Take your time and be thorough.

### 1. Study the Database Structure THOROUGHLY

**CRITICAL**: Study these aspects in detail - don't rush:

**Performance Considerations**:
- Read ALL documented optimization strategies
- Understand WHY each strategy is needed
- Note which strategies apply to large datasets
- Document pre-filtering techniques
- Study how to organize complex queries
- Example: UniProt has ~444M proteins - filtering order matters

**Common Mistakes**:
- Read EVERY documented error pattern
- Understand the root cause of each error
- Study the before/after examples carefully
- Note syntax requirements and limitations
- Document cross-database pitfalls
- Example: Study why certain text searches fail

**Example Queries**:
- **Carefully study COMPLEX examples** (multi-database, filtered, optimized)
- Understand what makes each query work
- Note patterns you can reuse
- Document which queries demonstrate:
  * Cross-database connections
  * Performance optimization
  * Error avoidance
  * Structural knowledge
- **Skip trivial examples** quickly (they're less informative)

**Data Model**:
- Understand the key entity types
- Note important properties and relationships
- Understand the data organization

### 2. Test Complex Query Patterns Extensively

**CRITICAL**: Focus exploration on queries that demonstrate database knowledge value.

**No Rush - Test Thoroughly**:
- **At least 5 cross-database queries** (combining 2+ databases)
- **At least 5 performance-critical queries** (large datasets with filtering)
- **At least 5 queries using error-avoidance patterns**
- **3-5 simple searches** for finding real entities (to confirm data exists)

**Test Systematically**:
- For each pattern type, try multiple variations
- Document what works and what doesn't
- Note performance differences
- Record actual results and entities found

**Document Everything**:
- Which queries FAILED without proper knowledge
- Which queries SUCCEEDED after applying correct patterns
- Performance differences (timeout vs. X second response)
- Error messages before pattern applied
- Actual results and real entities found
- Variations you tried and their outcomes

### 3. Document Cross-Database Connection Patterns

**Take Time to Explore Integration Thoroughly**:

**Identify ALL Integration Opportunities**:
- Which databases can be combined?
- What are ALL the connecting relationships?
- What information is needed from each?
- What pre-filtering is required to avoid timeouts?
- Are there multiple ways to connect these databases?

**Test Multiple Integration Patterns**:
- Try different connection points
- Test different filtering strategies
- Document which patterns work best
- Note performance characteristics

**Example**: Protein Database Integration Analysis:
```
Connection Opportunities:
1. Proteins → Reactions (via enzyme classification)
   - Relationship: enzyme activity
   - Pre-filtering: reviewed proteins, organism filter
   - Both databases needed

2. Proteins → Structures (via cross-references)
   - Relationship: structural data links
   - Pre-filtering: reviewed recommended

3. Proteins → Gene Ontology (via annotations)
   - Relationship: functional classification
   - Pre-filtering: ESSENTIAL for performance

4. Proteins → Compounds (indirect via reactions)
   - Path: Proteins → Reactions → Compounds
   - Three-database combination
   - Multiple filtering points needed
```

### 4. Create Comprehensive Exploration Report

**Take Your Time - This is the Output of Your Session**

Save to: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/[dbname]_exploration.md`

#### Required Report Structure:

```markdown
# [Database Name] Exploration Report

**Date**: [Current date]
**Session**: [Session number for this database]

## Executive Summary
[Brief overview of what you learned about this database]
- Key capabilities requiring deep knowledge
- Major integration opportunities
- Most valuable patterns discovered
- Recommended question types

## Database Overview
- Purpose and scope
- Key data types and entities
- Dataset size and performance considerations
- Available access methods

## Structure Analysis

### Performance Strategies
[List and explain ALL key performance strategies]
- Strategy 1: [Description]
  * Why it's needed
  * When to apply
  * Performance impact
- [List all strategies - don't skip any]

### Common Pitfalls
[List and explain ALL error patterns and solutions]
- Error 1: [Pattern]
  * Cause
  * Symptoms
  * Solution
  * Example before/after
- [List all documented errors]

### Data Organization
[Comprehensive view of data structure]
- Data section 1: [Description]
  * Purpose
  * Content type
  * Usage notes
- [Document all sections]

### Cross-Database Integration Points
[Comprehensive analysis of how this database connects to others]

**Integration 1: [Database A] → [Database B]**
- Connection relationship: [describe]
- Join point: [describe]
- Required information from each: [list]
- Pre-filtering needed: [describe]
- Knowledge required: [list]
- Example tested: [reference to pattern below]

[Document ALL integration opportunities discovered]

## Complex Query Patterns Tested

[For EACH pattern tested, provide comprehensive documentation]

### Pattern 1: [Pattern Name] (e.g., "Performance-Critical Filtering")

**Purpose**: [What biological/scientific question this answers]

**Category**: [e.g., Performance-Critical, Error Avoidance, Cross-Database]

**Naive Approach (without proper knowledge)**:
[Describe what happens without expert knowledge]

**What Happened**:
- Error message: [exact error if any]
- Timeout: [yes/no, after how long]
- Other issues: [describe]
- Why it failed: [explain root cause]

**Correct Approach (using proper pattern)**:
[Describe the working approach]

**What Knowledge Made This Work**:
- Key Insights:
  * [Insight 1]
  * [Insight 2]
- Performance improvement: [X seconds vs timeout/error]
- Why it works: [explain mechanism]

**Results Obtained**:
- Number of results: [N]
- Sample results:
  * Result 1: [entity ID and description]
  * Result 2: [entity ID and description]
- Data quality observations: [any notes]

**Natural Language Question Opportunities**:
[List 2-3 potential evaluation questions - phrased NATURALLY]
1. "[Natural question text - no technical terms]" - Category: [category]
2. "[Natural question text - no technical terms]" - Category: [category]

---

[Continue for ALL patterns tested - aim for at least 10-15 patterns]

---

## Simple Queries Performed

[Brief documentation of simple queries used to find real entities]

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "[term]"
   - Found: [ID] - [Name/Description]
   - Usage: [What question types this entity could support]

[Document 5-10 searches - enough to have diverse entity examples]

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:
[List question opportunities - ALL phrased naturally without technical terms]

1. "[Natural question: e.g., 'Which human enzymes catalyze reactions involving ATP?']"
   - Databases involved: [A, B, (C)]
   - Knowledge Required: [list what needs to be known - for notes field]
   - Category: [Structured Query / Integration]
   - Difficulty: [Easy/Medium/Hard]
   - Pattern Reference: [Link to pattern tested above]

2. "[Another natural question]"
   - [Same structure]

[List 10-15 integration question opportunities - all natural language]

**Performance-Critical Questions**:
1. "[Natural question requiring optimization]"
   - Database: [name]
   - Knowledge Required: [specific strategies needed - for notes field]
   - Category: [Completeness / Structured Query]
   - Difficulty: [Easy/Medium/Hard]
   - Pattern Reference: [Link to pattern tested above]

[List 8-12 performance question opportunities]

**Error-Avoidance Questions**:
1. "[Natural question that triggers common pitfall]"
   - Database: [name]
   - Knowledge Required: [specific solution needed - for notes field]
   - Category: [Structured Query]
   - Difficulty: [Medium/Hard]
   - Pattern Reference: [Link to pattern tested above]

[List 5-8 error-avoidance question opportunities]

**Complex Filtering Questions**:
1. "[Natural question with multiple criteria]"
   - Database: [name]
   - Knowledge Required: [filtering strategies - for notes field]
   - Category: [Structured Query / Completeness]
   - Difficulty: [Medium/Hard]
   - Pattern Reference: [Link to pattern tested above]

[List 8-10 complex filtering opportunities]

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:
1. "[Simple natural question: e.g., 'What is the UniProt ID for human BRCA1?']"
   - Method: [simple search]
   - Knowledge Required: None (straightforward)
   - Category: [Entity Lookup]
   - Difficulty: [Easy]

[List 5-8 simple lookup opportunities]

**ID Mapping Questions**:
1. "[Natural ID mapping question: e.g., 'What is the NCBI Gene ID for UniProt P04637?']"
   - Method: [ID conversion]
   - Knowledge Required: None
   - Category: [ID Mapping]
   - Difficulty: [Easy]

[List 3-5 ID conversion opportunities]

---

## Integration Patterns Summary

**This Database as Source**:
[Which databases can receive data FROM this database]
- → Database 1: [via what relationship]
- → Database 2: [via what relationship]

**This Database as Target**:
[Which databases provide data TO this database]
- Database 1 →: [via what relationship]
- Database 2 →: [via what relationship]

**Complex Multi-Database Paths**:
[3+ database integration opportunities]
- Path 1: [DB A] → [This DB] → [DB C]: [use case]
- Path 2: [DB D] → [This DB] → [DB E]: [use case]

---

## Lessons Learned

### What Knowledge is Most Valuable
[Reflect on which aspects were most useful]
1. [Insight 1]
2. [Insight 2]

### Common Pitfalls Discovered
[What mistakes did you make and learn from?]
1. [Pitfall 1]
2. [Pitfall 2]

### Recommendations for Question Design
[Based on your exploration, what makes good NATURAL questions for this database?]
1. [Recommendation 1]
2. [Recommendation 2]

### Performance Notes
[What did you learn about query performance?]
- [Note 1]
- [Note 2]

---

## Notes and Observations

[Any additional notes, surprises, or observations]
- [Observation 1]
- [Observation 2]

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: [list 3-5 highest priority question types]
- Avoid: [any question types that don't work well]
- Focus areas: [key topics this database handles well]

**Further Exploration Needed** (if any):
- [Any areas you didn't have time to explore fully]
- [Any patterns you'd like to test more]

---

**Session Complete - Ready for Next Database**
```

---

## After Completing the Report

**Before Ending Session**:
1. ✅ Review the report for completeness
2. ✅ Verify all patterns are documented
3. ✅ Check that knowledge requirements are clearly identified (for notes field)
4. ✅ Ensure integration opportunities are well-described
5. ✅ **Confirm all question opportunities are phrased naturally (no technical terms)**

**Session Summary**:
```
Database: [name]
Status: ✅ COMPLETE
Report: /evaluation/exploration/[dbname]_exploration.md
Patterns Tested: [N]
Questions Identified: [N]
Integration Points: [N]
```

**For Next Session**:
- Check exploration directory for completed databases
- Choose next unexplored database from the list
- Start fresh with thorough exploration

---

## Important Reminders

✅ **DO**:
- **Take your time - no rushing**
- Focus on ONE database per session completely
- Test complex queries extensively
- Document wrong vs. correct approaches thoroughly
- Test multiple variations of each pattern type
- Identify ALL cross-database opportunities
- Test error patterns and their solutions
- Verify that complex queries fail WITHOUT proper knowledge
- Write comprehensive exploration report before ending
- **Phrase ALL question opportunities naturally (as a researcher would ask)**
- Document technical details in the notes/knowledge-required sections

❌ **DON'T**:
- Try to explore multiple databases in one session
- Rush through the exploration due to perceived time limits
- Skip testing complex patterns
- Ignore performance strategy sections
- Miss cross-database integration opportunities  
- Create incomplete reports to "save time"
- Move to next database before report is complete
- **Include technical terms (SPARQL, API, MIE, etc.) in question text**
- **Phrase questions in implementation-focused language**

---

## Natural Language Question Examples

**GOOD (Natural) vs BAD (Technical)**:

| ❌ BAD (Technical) | ✅ GOOD (Natural) |
|-------------------|-------------------|
| "Use SPARQL to find proteins with GO annotation GO:0006914" | "Which human proteins are involved in autophagy?" |
| "Query the Rhea database API for reactions with ATP" | "What biochemical reactions involve ATP?" |
| "Search UniProt using full-text search for 'kinase'" | "Find human proteins that function as kinases" |
| "Convert P04637 to NCBI Gene ID using togoid" | "What is the NCBI Gene ID for UniProt protein P04637?" |
| "Execute a cross-database join between UniProt and PDB" | "Which human proteins have 3D structures available?" |
| "Query the citations graph in UniProt" | "What research papers cite UniProt entry P53_HUMAN?" |
| "Use MIE performance strategy to count proteins" | "How many human enzymes are annotated in UniProt?" |
| "Apply bif:contains to search annotation text" | "Find proteins described as 'membrane receptors'" |

**The technical details should go in the NOTES field, explaining:**
- What databases/tools are needed
- What knowledge is required
- What approach works vs. fails
- Performance considerations

---

**Begin by checking for existing exploration reports, then select ONE database to explore thoroughly. Test complex queries that fail without proper knowledge and succeed with it. Create a comprehensive report with NATURALLY-PHRASED question opportunities before ending the session. Quality over speed.**
