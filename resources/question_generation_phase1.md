Your task is to thoroughly explore available databases in TogoMCP to prepare for question generation. Do NOT create any questions yet - this is purely an exploration phase.

⚠️ **TOKEN MANAGEMENT**: If you approach your token limit (around 150,000+ tokens used), STOP immediately. Do NOT rush through remaining databases with "concise" or "efficient" exploration. Quality over quantity. Save remaining databases for the next session.

SETUP:
1. First, check which databases have already been explored:
   - Look for existing exploration reports in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
   - If reports exist, note which databases are DONE and skip them

2. Read these files to understand the context:
   * /Users/arkinjo/work/GitHub/togo-mcp/evaluation/QUESTION_DESIGN_GUIDE.md
   * /Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/QUESTION_FORMAT.md
   * /Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/example_questions.json

3. Run list_databases() to see all available databases.

4. Identify which databases still need exploration (databases without exploration reports).

EXPLORATION TASK:
For EACH database that needs exploration:

1. **Read the MIE file**: Call get_MIE_file(dbname)

2. **Study the structure**:
   - Carefully read the ShEx schema to understand properties and relationships
   - Review the RDF examples to see data patterns
   - Study ALL SPARQL query examples

3. **Explore the content**:
   - Run at least 5 different search queries using search_* functions
   - Test at least 3 SPARQL queries from the MIE file examples
   - Try variations to understand what data is available
   - Look for interesting, specific entities

4. **Document findings**: Create an exploration report at:
   `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/[dbname]_exploration.md`
   
   Each report MUST include:
````markdown
   # [Database Name] Exploration Report
   
   ## Database Overview
   - Purpose and scope of this database
   - Key data types and entities
   
   ## Schema Analysis (from MIE file)
   - Main properties available
   - Important relationships
   - Query patterns observed
   
   ## Search Queries Performed
   1. Query: [search term] → Results: [summary]
   2. Query: [search term] → Results: [summary]
   3. [etc., at least 5 queries]
   
   ## SPARQL Queries Tested
```sparql
   # Query 1: [purpose]
   [SPARQL query]
   # Results: [summary of what you found]
```
```sparql
   # Query 2: [purpose]
   [SPARQL query]
   # Results: [summary]
```
   
   [At least 3 queries total]
   
   ## Interesting Findings
   - Specific entities that could form good questions
   - Unique properties or patterns
   - Connections to other databases
   - Specific, verifiable facts not commonly known
   
   ## Question Opportunities by Category
   - Precision: [ideas]
   - Completeness: [ideas]
   - Integration: [ideas]
   - Currency: [ideas]
   - Specificity: [ideas]
   - Structured Query: [ideas]
   
   ## Notes
   - Any limitations or challenges with this database
   - Best practices for querying
````

5. **Monitor your progress**: After completing each database exploration, check your token usage. If approaching limits, proceed to the STOPPING POINT section below.

WORKFLOW:
1. Check for existing exploration reports and identify remaining databases
2. Read the three required files (if first session)
3. List all databases
4. Create the exploration directory (if it doesn't exist):
   `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
5. For each database that needs exploration:
   - Get MIE file
   - Perform thorough exploration (searches, queries, analysis)
   - Create detailed exploration report
   - **Check token usage** - if approaching limit, go to STOPPING POINT
6. If ALL databases are explored, proceed to COMPLETION section

STOPPING POINT (When Token Limit is Approaching):
Create a progress file: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_PROGRESS.md`
````markdown
# Exploration Progress

## Session [N] - [Date]

### Completed Databases ([X] of [Total])
- [database1] ✅
- [database2] ✅
- [etc.]

### Remaining Databases ([Y] remaining)
- [database_a] ⏳
- [database_b] ⏳
- [etc.]

### Notes
- [Any observations about the databases explored so far]
- [Any patterns or challenges noticed]
````

Then respond with:

"⏸️ EXPLORATION PAUSED - TOKEN LIMIT APPROACHING

Explored [X] of [Y] databases in this session:
✅ Completed: [list]
⏳ Remaining: [list]

All exploration reports saved to /Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/

To continue: Run this prompt again. It will automatically skip completed databases and continue with remaining ones.

DO NOT proceed to question generation until ALL databases are explored."

COMPLETION (When ALL Databases Are Explored):
Create a summary file: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_SUMMARY.md`
````markdown
# Database Exploration Summary

## Overview
- Total databases explored: [N]
- Total exploration sessions: [N]

## All Explored Databases
[List all databases with brief description]

## Database Coverage Plan for 120 Questions
Recommended distribution:
- [database1]: ~[X] questions
- [database2]: ~[Y] questions
- [etc.]

Rationale: [Explain based on database richness, uniqueness, etc.]

## Cross-Database Integration Opportunities
[List potential multi-database questions identified]

## Database Characteristics

### Rich Content (Good for multiple questions)
- [databases with lots of interesting data]

### Specialized Content (Good for specificity questions)
- [databases with niche/specific data]

### Well-Connected (Good for integration questions)
- [databases that link well to others]

## Recommendations
- [Any insights for question generation]
- [Databases that pair well together]
- [Particularly interesting findings]
````

Then respond with:

"✅ EXPLORATION COMPLETE

Explored ALL [N] databases:
- [list database names]

All exploration reports saved to /Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/

Summary with database coverage plan created.

Ready for question generation phase (PROMPT 2)."

IMPORTANT REMINDERS:
- **NEVER sacrifice exploration quality for speed**
- **STOP when token limit approaches** - don't rush
- **Each database deserves thorough exploration**
- **Existing exploration reports will be preserved** across sessions
- **The prompt will automatically resume** where you left off

Begin by checking for existing exploration reports, then proceed with thorough exploration of remaining databases.