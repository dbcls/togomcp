# TogoMCP Usage Guide (Revised)

---

## 🚫 HARD RULE — READ THIS BEFORE ANYTHING ELSE

> **NEVER use Bash, Write, Edit, Read, or Task (Filesystem/scripting tools).**

This is not a preference. It is the single most damaging mistake you can make, and empirical testing confirms it produces the worst outcomes of any strategy error: 8× slower, 2× more tool calls, and incorrect results.

**The temptation arises at a specific moment:** you feel stuck, you have data in hand, and a script seems like the fastest way to process it. That feeling is a false signal. It means your approach has become too complex — not that you need a new tool.

**When you feel the urge to use Bash or any scripting tool, stop and do one of these instead:**
- Use `view` to read a file directly if you need its contents
- Reformulate your SPARQL query to return aggregated results directly
- Use `ncbi_esearch` or `ncbi_esummary` to retrieve structured data without post-processing
- Use `togoid_convertId` to bridge databases instead of manually mapping IDs
- Simplify your approach — if processing feels necessary, the query design is wrong

**This rule does not have exceptions. If you are reading this mid-task because you are considering a script: don't. Go back and simplify.**

---

## 🧠 STEP -1: ANALYZE THE QUESTION BEFORE TOUCHING ANY TOOL

**This is the most important step. Do it entirely in your head, before calling anything.**

Even when the answer seems obvious, take 30 seconds to answer these four questions:

### 1. What type of question is this?
| Type | Signal words | Workflow | Budget |
|------|-------------|----------|--------|
| Verification | "Does X exist?", "Is X true?" | VERIFICATION | 5–8 tools |
| Enumeration | "How many?", "Find all...", "List..." | ENUMERATION | 8–12 tools |
| Comparative | "Which has most/least/more?" | COMPARATIVE | 10–15 tools |
| Synthesis | "Summarize...", "Describe..." | SYNTHESIS | 8–15 tools |

### 2. What entities and concepts are involved?
List every distinct entity class in the question. For example:
- "Which bacterial orders have the most reviewed proteins annotated with carbon fixation activity?"
  - Entities: bacterial orders (taxonomy), reviewed proteins (UniProt), GO annotation (carbon fixation)
  - This immediately signals a **multi-database, cross-endpoint** question.

### 3. Which databases are likely involved?
Map each entity to a likely database:
- Taxonomy → NCBI Taxonomy or UniProt taxonomy graph
- Reviewed proteins → UniProt (Swiss-Prot)
- GO annotations → GO ontology, or via `up:classifiedWith` in UniProt
- Reactions → Rhea
- Variants → ClinVar
- Pathways → Reactome
- Drug targets → ChEMBL

If you identify 2+ databases, note them — you will need to check whether they share a SPARQL endpoint.

### 4. Is this a comparative question?
If yes, flag it now. Comparative questions require you to:
- Enumerate **all** categories, not just one
- Count **each** independently
- Use `ORDER BY DESC(?count)` to find the winner
- Avoid the circular trap of searching within one category and declaring it the winner

**Only after completing this analysis should you proceed to `list_databases()`.**

> 💡 **Why this matters:** Confidence in your prior knowledge is the most common reason procedural rules feel optional. The analysis makes the rules feel necessary, because it surfaces complexity you would otherwise miss.

---

## ⚡ QUICK START

```
┌──────────────────────────────────────────────────────┐
│ STEP -1: Analyze the question (no tools yet)         │
│   • What type? (verification/enumeration/            │
│     comparative/synthesis)                           │
│   • What entities? → Which databases?                │
│   • Multi-database? → Will need endpoint check       │
│   • Comparative? → Must enumerate ALL categories     │
├──────────────────────────────────────────────────────┤
│ STEP 0: Call list_databases()                        │
│   Then match your question type:                     │
├──────────────────────────────────────────────────────┤
│ "Does X exist?", "Is X true?"                        │
│ → VERIFICATION workflow (fastest, 5–8 tools)         │
│                                                      │
│ "How many...", "Find all...", "List..."               │
│ → ENUMERATION workflow (8–12 tools)                  │
│                                                      │
│ "Which has MOST/LEAST/MORE?"                         │
│ → COMPARATIVE workflow (10–15 tools)                 │
│                                                      │
│ "Summarize...", "Describe..."                         │
│ → SYNTHESIS workflow (mixed tools, 8–15 tools)       │
├──────────────────────────────────────────────────────┤
│ Does your question involve 2+ databases?             │
│ → Check ENDPOINT ARCHITECTURE section                │
│ → If different endpoints, plan with TogoID EARLY     │
└──────────────────────────────────────────────────────┘
```

---

## 🎯 EFFICIENCY PRINCIPLES (READ FIRST)

Empirical testing shows that **answer quality peaks at 6–10 tool calls** and declines beyond 15. Follow these rules:

### Tool Budget
- **Target: 6–15 tool calls total.** Beyond 20 is a red flag.
- **SPARQL: aim for 3–4 calls.** Beyond 7, quality drops sharply.
- **NCBI esearch: 1–3 calls is the sweet spot.** Most reliable single tool.
- **Never exceed 2 consecutive SPARQL retries.** If 2 fail, pivot strategy (simplify query, try a search tool, use NCBI, or use TogoID to bridge databases).

### Tool Selection Priority
When multiple tools could answer a question, prefer in this order:
1. **Specialized entity search tools** (search_reactome, search_chembl_target, search_pdb, search_rhea) — highest precision when applicable
2. **NCBI esearch + esummary** — most reliable for gene/variant/taxonomy questions
3. **PubMed search_articles** — for literature-backed evidence
4. **TogoID** — for bridging databases on different SPARQL endpoints (plan early, convert once)
5. **SPARQL via run_sparql** — most powerful but fragile; use after grounding with search tools
6. **OLS search** — for ontology term resolution

### Strategy: Analyze First, Search Second, SPARQL Third
**Do NOT jump straight into SPARQL — or even into search tools.** Complete Step -1 (question analysis) first, then use entity search tools to ground your understanding, then build targeted SPARQL queries. Questions that start with analysis and a search tool outperform those that start with SPARQL alone.

### Strategy: Plan Cross-DB Bridges Early
When a question involves 2+ databases on **different** SPARQL endpoints, decide your bridging strategy in the first few tool calls — not after 10+ failed SPARQL attempts. Your options: same-endpoint SPARQL join, NCBI as universal bridge, or TogoID conversion (see Endpoint Architecture section).

### Graceful Degradation
If your tool calls are approaching 15 with no clean result, **STOP and synthesize the best answer from partial data you already have.** A well-reasoned answer from incomplete data almost always scores better than an incorrect answer from an over-extended tool chain.

### Output Quality
- **Never include internal reasoning artifacts** in the final answer (no "Perfect!", "Excellent!", "Now I have the complete analysis", "## Answer", or similar).
- Write a **clean, direct paragraph** as the final answer.

---

## 🔍 STEP 0: DATABASE DISCOVERY (ALWAYS THE FIRST TOOL CALL)

**Call `list_databases()` as your very first tool call — every time, no exceptions.**

```python
list_databases()  # Returns: 23 databases with descriptions

# Match keywords in descriptions to your query:
# "MANE" → Ensembl (not just NCBI Gene!)
# "drug targets" → ChEMBL
# "clinical variants" → ClinVar
# "pathways" → Reactome
# "culture media" + "growth conditions" → BacDive / MediaDive
```

**When to skip:** Only if you are continuing work from a prior step in the same session where `list_databases()` was already called and no new database types are being introduced.

**Rule:** 5 seconds of discovery prevents minutes of debugging.

### Why This Rule Is Not Optional
The most common reason people skip `list_databases()` is confidence — they already have a database in mind. But that confidence is exactly the risk:

- Descriptions contain keywords that reveal unexpected content (e.g., "MANE" appears in Ensembl, not NCBI Gene)
- A question that looks single-database is often multi-database once entities are enumerated
- Skipping this step means planning your entire query strategy on an assumption, not evidence

**If you completed Step -1 properly, `list_databases()` will feel necessary, not bureaucratic.** The entities you identified in Step -1 map directly to databases you now need to confirm.

### Common Mistake
❌ **Assuming:** "UniProt has reviewed proteins, so I'll start there" → Misses taxonomy endpoint planning
✅ **Discovering:** `list_databases()` reveals which databases share endpoints → Shapes cross-DB strategy from the start

---

## 🔌 ENDPOINT ARCHITECTURE (CHECK BEFORE MULTI-DB QUERIES)

When a question involves 2+ databases, you must determine whether they share a SPARQL endpoint. This decision shapes your entire strategy.

```python
get_sparql_endpoints()
# Returns: which databases share endpoints
```

### Can Query Together (Same Endpoint → Single SPARQL)
✅ **ncbi endpoint:** ClinVar + PubMed + PubTator + NCBI Gene + MedGen
✅ **primary endpoint:** MeSH + GO + Taxonomy + MONDO + NANDO
✅ **ebi endpoint:** ChEMBL + ChEBI + Reactome + Ensembl
✅ **sib endpoint:** UniProt + Rhea

### CANNOT Query Together (Different Endpoints → Need a Bridge)
❌ NCBI Gene (ncbi) + Taxonomy (primary)
❌ UniProt (sib) + ChEMBL (ebi)
❌ PubChem (pubchem) + any other database

### Choosing a Cross-Database Bridge Strategy

When databases are on **different endpoints**, choose one of these strategies:

| Strategy | When to use | Example |
|----------|-------------|---------|
| **Same-endpoint SPARQL** | Both DBs share an endpoint | ClinVar + MedGen (both ncbi) |
| **NCBI as bridge** | Gene/variant/disease question; NCBI can cross-reference natively | Gene names → ClinVar variants → disease |
| **TogoID conversion** | You have IDs in DB-A format and need DB-B format; a known route exists | UniProt accessions → PDB structure IDs |
| **Sequential search → SPARQL** | Use search tool on DB-A to get IDs, then SPARQL on DB-B | search_mesh → SPARQL on primary endpoint |

**Decision flow:**
```
Question involves 2+ DBs?
  → get_sparql_endpoints()
    → Same endpoint? → Single SPARQL query (best case)
    → Different endpoints?
        → Can NCBI esearch cross-reference what you need? → Use NCBI
        → Need explicit ID mapping? → Use TogoID (plan early!)
        → Neither works? → Sequential search → SPARQL
```

---

## 🔗 TogoID: CROSS-DATABASE ID CONVERSION

TogoID maps identifiers between biological databases. Use it when you have IDs from one database and need corresponding IDs in another.

### When to Use TogoID
- Question requires data from 2+ databases on **different** SPARQL endpoints
- You have IDs in one format (e.g., NCBI Gene) and need another (e.g., UniProt)
- A direct conversion route exists (check with `togoid_getAllRelation`)

### When NOT to Use TogoID
- Both databases share a SPARQL endpoint (use a single SPARQL query — simpler, faster)
- NCBI esearch can already cross-reference what you need (it often can)
- You only need data from one database

### Common Conversion Routes
- `ncbigene → uniprot` — Gene IDs → Protein accessions
- `uniprot → pdb` — Protein accessions → 3D structure IDs
- `ncbigene → ensembl_gene` — NCBI Gene → Ensembl Gene IDs
- `uniprot → chembl_target` — Proteins → Drug target entries
- `ncbigene → hgnc` — Gene IDs → HGNC symbols
- Multi-hop: `ncbigene → uniprot → pdb` (Gene → Protein → Structure)

### TogoID Workflow (3 steps)

**Plan EARLY — call these in the first few tool calls, not after 10+ SPARQL failures.**

```
Step 1: DISCOVER — Does a conversion route exist?
  togoid_getAllRelation()         → see all available routes
  OR togoid_getRelation(src,tgt) → check a specific route

Step 2: VALIDATE — Are my IDs in the right format?
  togoid_countId(src, tgt, ids)  → pre-check before bulk conversion
  (Also: togoid_getDataset(src)  → see expected ID format and examples)

Step 3: CONVERT — Map the IDs
  togoid_convertId(ids, route)   → get [source_id, target_id] pairs
```

---

## 📋 WORKFLOW: VERIFICATION ("Does X exist?", "Is X true?")

**Budget: 5–8 tool calls. This is the fastest workflow.**

```
-1. Analyze question (no tools)
 0. list_databases()              → identify 1–2 databases
 1. Entity search OR ncbi_esearch → look up the specific entity
 2. (If needed) get_MIE_file()    → check schema
 3. (If needed) run_sparql()      → 1–2 targeted queries
 4. Answer directly
```

---

## 📋 WORKFLOW: ENUMERATION ("How many?", "Find all...", "List...")

**Budget: 8–12 tool calls.**

### Single-Database Enumeration
```
-1. Analyze question (no tools)
 0. list_databases()        → identify database
 1. Entity search tools     → ground your understanding with examples
 2. get_MIE_file()          → find structured properties
 3. run_sparql() (2–4 calls) → comprehensive structured queries
 4. Answer with counts/list
```

### Cross-Database Enumeration
```
-1. Analyze question (no tools)    → identify entities, flag multi-DB
 0. list_databases()               → confirm databases
 1. get_sparql_endpoints()         → same or different endpoint?
2a. Same endpoint → get_MIE_file(), then single SPARQL
2b. Different endpoints:
    → togoid_getAllRelation()       → discover conversion route (EARLY!)
    → Query DB-A for source IDs
    → togoid_convertId()           → map to DB-B IDs
    → Query DB-B with converted IDs
 3. Answer with counts/list
```

---

## 📋 WORKFLOW: COMPARATIVE ("Which has most/least?")

**Budget: 10–15 tool calls. The most complex workflow.**

### Critical Rule: Don't Be Circular!
❌ Search → find examples from category A → count only A → "A has the most!"
✅ Enumerate ALL categories → count EACH → compare systematically

### 7-Step Checklist
☐ **-1. Analyze question** → Identify: comparative type, all entities, all databases needed
☐ **0. Check endpoints** → `get_sparql_endpoints()` if multi-database
☐ **0b. Plan bridge** → if different endpoints, call `togoid_getAllRelation()` or decide on NCBI bridge
☐ **1. Get MIE file** → find structured properties
☐ **2. Enumerate ALL categories** → don't assume, list them
☐ **3. Broad search query** → use OR: `"(nifH OR 'nitrogenase iron protein')"`
☐ **4. Count EACH category** → process ALL results, not samples
☐ **5. Compare** → ORDER BY DESC(?count) to find winner

---

## 📋 WORKFLOW: SYNTHESIS ("Summarize...", "Describe...")

**Budget: 8–15 tool calls. Use mixed tools.**

```
-1. Analyze question (no tools)    → map entities to databases
 0. list_databases()               → identify 2–3 relevant databases
 1. get_sparql_endpoints()         → check if cross-DB bridge needed
 2. Entity search tools            → get key entity IDs and context
 3. get_MIE_file() (1–2 DBs)       → find structured properties
 4. run_sparql() (2–4 calls)       → get quantitative data
 5. (If cross-DB) togoid_convertId() → bridge identifiers
 6. PubMed search (optional)       → get literature context
 7. Synthesize into coherent paragraph
```

---

## 🚨 SPARQL DISCIPLINE

SPARQL is the most powerful tool but also the most failure-prone. Follow these rules strictly:

### Before Writing SPARQL
1. **Always read the MIE file first.** 95% of SPARQL failures come from skipping this step.
2. **Use structured predicates, not text search.** `up:classifiedWith <GO_term>` beats `bif:contains "chemotaxis"` every time.

### While Writing SPARQL
3. **Use PREFIX declarations** from the MIE file examples.
4. **Start with a simple query (LIMIT 10)** to verify structure before going comprehensive.
5. **Use VALUES clauses** for batch lookups (10–15 items per query, not more).

### If SPARQL Fails
6. **Maximum 2 consecutive SPARQL retries.** After that, pivot:
   - Simplify the query (remove JOINs, reduce scope)
   - Try a different database or search tool
   - Use NCBI esearch as an alternative path
   - Use TogoID to bridge to a database where the query is simpler
7. **Never enter a SPARQL retry loop** (3+ consecutive run_sparql calls).

---

## 🛠️ TOOLS REFERENCE (BY EFFECTIVENESS)

### Tier 1: High Precision (use when applicable)
- `search_reactome_entity(query)` — Pathways.
- `search_chembl_target(query)` — Drug targets.
- `search_pdb_entity(db, query)` — 3D structures.
- `search_rhea_entity(query)` — Biochemical reactions.

### Tier 2: Reliable Workhorses
- `ncbi_esearch(database, query)` — **Most reliable tool overall.**
- `ncbi_esummary(database, ids)` — Detail retrieval. Pair with esearch.
- `run_sparql(dbname, query)` — Most powerful but requires MIE schema.

### Tier 3: Cross-Database Bridging (TogoID)
- `togoid_getAllRelation()` — Discover all available conversion routes. Call EARLY.
- `togoid_getRelation(source, target)` — Check if a specific route exists.
- `togoid_countId(source, target, ids)` — Pre-check before bulk conversion.
- `togoid_convertId(ids, route)` — Convert IDs between databases.
- `togoid_getAllDataset()` — List all databases in TogoID with ID formats.
- `togoid_getDataset(dataset)` — Get ID format details for a specific database.

### Tier 4: Supporting Tools
- `search_uniprot_entity(query)` — Protein lookup.
- `search_mesh_descriptor(query)` — MeSH term resolution.
- `search_chembl_molecule(query)` — Drug/compound lookup.

### Schema & Discovery (use at start)
- `list_databases()` — **ALWAYS THE FIRST TOOL CALL.**
- `get_MIE_file(dbname)` — **ALWAYS before SPARQL.**
- `get_sparql_endpoints()` — Before multi-database queries.

---

## 🔑 KEY RULES

1. **Analyze before acting.** Step -1 is not a tool call — it is mental work done before any tool is touched. It makes every subsequent step more deliberate.
2. **No scripting tools, ever.** See the hard rule at the top. Re-read it now if you skipped it.
3. **Database discovery first.** Call `list_databases()` as the very first tool call, every time.
4. **Check endpoints for multi-database queries.** Same endpoint → single SPARQL. Different → bridge strategy.
5. **Plan cross-DB bridges early.** Decide in the first few tool calls, not after SPARQL has failed.
6. **MIE file before SPARQL.** 95% of SPARQL failures come from skipping this.
7. **Search first, SPARQL second.** Ground your understanding before building queries.
8. **Use OR logic for broad searches.** `"(nifH OR 'nitrogenase iron protein')"` finds 5× more than `"nifH"` alone.
9. **Structured properties over text search.** `up:classifiedWith <GO_term>` is 10–100× faster.
10. **No circular reasoning in comparisons.** Enumerate ALL categories, count EACH, then compare.
11. **Respect the tool budget.** Target 6–15 calls. At 15 with no clean answer, stop and synthesize.
12. **Max 2 SPARQL retries.** Then pivot.
13. **Clean output only.** No reasoning artifacts in the final answer.

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Tempted to use Bash or write a script | **Stop. Re-read the hard rule at the top.** Use `view` to read files, reformulate your SPARQL to aggregate results directly, or use `togoid_convertId` to map IDs without post-processing. If you still feel you need a script, your approach is too complex — simplify it. |
| Jumped into tools before analyzing the question | Stop. Do Step -1 now. Identify question type, entities, and databases before continuing. |
| Cross-DB query fails | Check `get_sparql_endpoints()` — same endpoint? Use single SPARQL. Different? Use TogoID or NCBI bridge |
| Don't know if TogoID can convert | Call `togoid_getAllRelation()` or `togoid_getRelation(src,tgt)` to check |
| TogoID returns empty results | Check ID format with `togoid_getDataset(src)` — IDs may need different format |
| Empty SPARQL results | Read MIE schema for correct property names |
| SPARQL timeout | Add LIMIT, use structured predicates instead of text search |
| Incomplete results | Use OR logic for synonyms; process ALL results for comparatives |
| 2 SPARQL retries failed | STOP. Simplify query, try search tools, NCBI, or TogoID as alternative |
| Approaching 15 tool calls | STOP. Synthesize best answer from data collected so far |

---

## 🚫 TOP 5 MISTAKES (FROM EMPIRICAL TESTING)

### 1. Using Filesystem/Scripting Tools
**Impact:** 8× slower, 2× more tool calls, wrong answers. The single worst outcome in testing.
**Fix:** Never use Bash/Write/Edit/Read/Task. See the hard rule at the top.

### 2. Skipping Question Analysis (NEW — most common root cause)
**Impact:** Misidentifies question type, misses multi-database structure, jumps to wrong tools with false confidence.
**Fix:** Always complete Step -1 before any tool call. Map entities to databases explicitly. Flag comparative questions. Confidence in prior knowledge is the enemy here — it is exactly what makes procedural rules feel optional when they aren't.

### 3. Skipping Database Discovery
**Impact:** Query wrong database, miss 50–80% of relevant data.
**Fix:** Call `list_databases()` first, always. Step -1 makes this feel necessary because it surfaces which databases you need to verify.

### 4. Jumping Straight to SPARQL Without Search
**Impact:** Poorly constructed queries, many retries, degraded answers.
**Fix:** Use entity search tools first to understand the data, then SPARQL.

### 5. SPARQL Retry Loops (3+ consecutive calls)
**Impact:** Strong predictor of poor answer quality. Wastes tool budget.
**Fix:** Max 2 retries, then pivot strategy — try NCBI, TogoID, or a search tool.

### 6. Late Cross-DB Planning
**Impact:** Attempting SPARQL joins across different endpoints fails; TogoID called at step 15 as a last resort produces worse results than when planned early.
**Fix:** Check `get_sparql_endpoints()` and `togoid_getAllRelation()` in the first 3–4 tool calls for multi-database questions.

---

## 🎯 REMEMBER

1. **Step -1 first — always. Analyze the question before touching any tool.**
2. **No scripting tools — ever. If tempted, re-read the hard rule at the top.**
3. **`list_databases()` is always the first tool call — no exceptions.**
4. **For multi-DB questions: check endpoints, then plan your bridge EARLY.**
5. **Search first, SPARQL second — ground before querying.**
6. **MIE file before any SPARQL — your schema map.**
7. **TogoID for cross-endpoint bridges — discover routes early, convert once.**
8. **6–15 tool calls is the sweet spot — quality degrades beyond this.**
9. **Max 2 SPARQL retries — then pivot.**
10. **Synthesize from partial data rather than over-extending.**
11. **Clean final output — no artifacts, no meta-commentary.**