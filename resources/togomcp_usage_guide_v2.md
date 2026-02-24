# TogoMCP Usage Guide (v2 — Empirically Revised)

## 🚫 HARD RULE — READ THIS BEFORE ANYTHING ELSE

> **NEVER use Bash, Write, Edit, Read, or Task (Filesystem/scripting tools).**

This is not a preference. Empirical testing confirms it produces the worst outcomes of any strategy error: 8× slower, 2× more tool calls, and incorrect results.

**When you feel the urge to use Bash or any scripting tool, stop and do one of these instead:**
- Reformulate your SPARQL query to return aggregated results directly
- Use `ncbi_esearch` or `ncbi_esummary` to retrieve structured data without post-processing
- Use `togoid_convertId` to bridge databases instead of manually mapping IDs
- Simplify your approach — if processing feels necessary, the query design is wrong

**This rule has no exceptions.**

---

## 🚨 THE SPARQL DISCIPLINE CRISIS — READ THIS SECOND

> **This is the single biggest driver of poor scores.** In evaluation, 72% of questions violated the max-2-consecutive-SPARQL rule. Questions with 1–2 max consecutive SPARQL calls averaged **17.81/20**. Questions with 3–4 consecutive averaged **16.55**. Questions with 8+ consecutive averaged **16.43** — barely better than the baseline that uses no tools at all.

**The 2-retry limit is not a guideline. It is the empirically optimal stopping point.**

After 2 consecutive `run_sparql` failures, your query approach is wrong. More retries will not fix it. Pivoting will.

**When 2 consecutive SPARQL calls fail, immediately:**
1. Try a specialized search tool (`ncbi_esearch`, `search_mesh_descriptor`, `search_chembl_target`, etc.)
2. Or use `togoid_convertId` to bridge to a database where the query is simpler
3. Or simplify the query by removing JOINs, reducing scope, or splitting into two separate queries
4. Or **synthesize from partial data** — a well-reasoned partial answer scores higher than an incorrect exhaustive one

**The worst documented outcome** was a question with 20 consecutive `run_sparql` calls (steps 7–26 of 26, an unbroken chain), scoring 15/20. The baseline, using no tools, averaged 15.9/20 on the same question set.

---

## 🧠 STEP -1: ANALYZE THE QUESTION BEFORE TOUCHING ANY TOOL

**This is the most important step. Do it entirely in your head, before calling anything.**

Answer these four questions before touching any tool:

### 1. What type of question is this?
| Type | Signal words | Workflow | SPARQL budget |
|------|-------------|----------|--------------|
| Verification | "Does X exist?", "Is X true?" | VERIFICATION | 1–2 SPARQL |
| Enumeration | "How many?", "Find all...", "List..." | ENUMERATION | 2–3 SPARQL |
| Comparative | "Which has most/least/more?" | COMPARATIVE | 3–4 SPARQL |
| Synthesis | "Summarize...", "Describe..." | SYNTHESIS | 2–3 SPARQL |

### 2. What entities and concepts are involved?
List every distinct entity class in the question. For example:
- "Which bacterial orders have the most reviewed proteins annotated with carbon fixation activity?"
  - Entities: bacterial orders (taxonomy), reviewed proteins (UniProt), GO annotation (carbon fixation)
  - This immediately signals a **multi-database, cross-endpoint** question.

### 3. Which databases are likely involved? Are they on the same endpoint?
Map each entity to a database, then immediately check if they share a SPARQL endpoint:
- UniProt + Rhea → same SIB endpoint ✅ (single SPARQL possible)
- ChEMBL + UniProt → different endpoints ❌ (need TogoID or sequential approach)
- ClinVar + PubMed → same NCBI endpoint ✅

**If different endpoints: plan your bridge NOW (step -1), not after SPARQL has failed.**

### 4. Is this a comparative question?
If yes, flag it. Comparative questions require you to:
- Enumerate **all** categories, not just one
- Count **each** independently
- Use `ORDER BY DESC(?count)` to find the winner
- Avoid the circular trap of searching within one category and declaring it the winner

---

## ⚡ QUICK START

```
┌─────────────────────────────────────────────────────────────┐
│ STEP -1: Analyze the question (no tools yet)                │
│   • Type? (verification/enumeration/comparative/synthesis)  │
│   • Entities → Databases → Same endpoint?                   │
│   • If multi-DB on different endpoints → plan bridge NOW    │
│   • If comparative → commit to enumerating ALL categories   │
├─────────────────────────────────────────────────────────────┤
│ STEP 0: list_databases()  [ALWAYS FIRST]                    │
├─────────────────────────────────────────────────────────────┤
│ STEP 1: Specialized search tool OR ncbi_esearch             │
│   → Ground your understanding BEFORE writing any SPARQL     │
│   → This step alone often answers verification questions    │
├─────────────────────────────────────────────────────────────┤
│ STEP 2: get_MIE_file() for each database you will query     │
│   → ALWAYS before run_sparql. No exceptions.                │
├─────────────────────────────────────────────────────────────┤
│ STEP 3: run_sparql() — targeted, structured, with LIMIT     │
│   → Max 1–3 total. Max 2 consecutive. Then STOP and pivot.  │
├─────────────────────────────────────────────────────────────┤
│ STEP 4: Synthesize and write a clean final answer           │
│   → No artifacts, no repetition, no meta-commentary        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 EFFICIENCY PRINCIPLES

Empirical results from 150 evaluated question-answer pairs:

### Tool Budget (measured)

| Total tools used | Questions | Avg score |
|-----------------|-----------|-----------|
| ≤5 | 17 | 16.12 |
| **6–10** | **34** | **17.50** ← optimal |
| **11–15** | **48** | **17.40** ← acceptable |
| 16–20 | 25 | 16.72 |
| 21+ | 26 | 16.23 ← red flag zone |

**Target: 6–15 total tool calls.** Beyond 20 is a measured red flag — scores return to near-baseline levels.

### SPARQL Budget (measured)

| Total SPARQL calls | Questions | Avg score |
|-------------------|-----------|-----------|
| 0 | 21 | 16.33 |
| **1–3** | **48** | **17.67** ← optimal |
| 4–6 | 34 | 16.82 |
| 7–9 | 25 | 16.96 |
| 10+ | 22 | 16.31 |

**Target: 1–3 SPARQL calls total.** This is the empirically optimal range. Beyond 6 SPARQL calls, average scores decline toward baseline-equivalent levels.

### Consecutive SPARQL Rule (measured)

| Max consecutive SPARQL | Questions | Avg score |
|-----------------------|-----------|-----------|
| **1–2 (compliant)** | **36** | **17.81** ← best |
| 3–4 (violation) | 44 | 16.55 |
| 5–7 (violation) | 28 | 17.39 |
| 8+ (violation) | 21 | 16.43 |

**Hard limit: 2 consecutive SPARQL calls. Then pivot.** The compliant group scores **1.26 points higher** than the 3–4 violation group.

### Tool Selection Priority (by measured avg score, min 5 appearances)

| Tool | Avg score |
|------|-----------|
| `search_mesh_descriptor` | 18.00 ← highest |
| `search_chembl_target` | 17.83 |
| `get_pubchem_compound_id` | 17.80 |
| `togoid_getAllRelation` | 17.67 |
| `search_reactome_entity` | 17.58 |
| `search_pdb_entity` | 17.50 |
| `search_rhea_entity` | 17.35 |
| `togoid_convertId` | 17.17 |
| `ncbi_esummary` | 17.10 |
| `OLS:search` | 17.07 |
| `run_sparql` | 17.06 |
| `ncbi_esearch` | 17.02 |
| `search_uniprot_entity` | 16.44 |
| `OLS:getDescendants` | 15.50 ← lowest |
| `togoid_getRelation` | 15.43 ← lowest |

**Practical implication:** When in doubt, reach for `search_mesh_descriptor`, `search_chembl_target`, or `togoid_getAllRelation` first. `OLS:getDescendants` and `togoid_getRelation` are lower-yield; use them only when specifically needed, not as exploratory tools.

---

## 🔍 STEP 0: DATABASE DISCOVERY (ALWAYS THE FIRST TOOL CALL)

**Call `list_databases()` as your very first tool call — every time, no exceptions.**

```python
list_databases()
# Match keywords in descriptions to your query:
# "MANE" → Ensembl (not just NCBI Gene)
# "drug targets" → ChEMBL
# "clinical variants" → ClinVar
# "pathways" → Reactome
# "culture media" / "growth conditions" → BacDive / MediaDive
# "glycobiology" → GlyCosmos (specialist — see Known-Hard Queries below)
```

---

## 🔌 ENDPOINT ARCHITECTURE

When a question involves 2+ databases, check whether they share a SPARQL endpoint. **Note: empirically, skipping `get_sparql_endpoints()` did NOT consistently harm scores (questions without it averaged 17.59 vs 16.73 with it).** Call it when you genuinely need to plan a cross-endpoint bridge, not as a ritual.

### Endpoints at a glance
- ✅ **sib:** UniProt + Rhea
- ✅ **ncbi:** ClinVar + PubMed + PubTator + NCBI Gene + MedGen
- ✅ **primary:** MeSH + GO + Taxonomy + MONDO + NANDO
- ✅ **ebi:** ChEMBL + ChEBI + Reactome + Ensembl
- ❌ UniProt (sib) ↔ ChEMBL (ebi) → needs TogoID
- ❌ PubChem (own endpoint) ↔ anything else → use `get_pubchem_compound_id` then bridge

### Cross-database bridge strategy
```
Both DBs on same endpoint? → Single SPARQL (fastest)
Different endpoints?
  → NCBI cross-reference available? → Use ncbi_esearch (most reliable)
  → Explicit ID mapping needed? → togoid_convertId (plan EARLY)
  → Neither? → Specialized search on DB-A → SPARQL on DB-B
```

---

## 🔗 TogoID: CROSS-DATABASE ID CONVERSION

**Plan TogoID in the first 3–5 tool calls, not after SPARQL has failed.** Empirically, TogoID called late (>50% into the tool sequence) correlates with worse scores.

### When to use TogoID
- Question requires data from 2+ databases on **different** SPARQL endpoints
- You have IDs from one database and need corresponding IDs in another
- A direct conversion route exists

### When NOT to use TogoID
- Both databases share a SPARQL endpoint (use single SPARQL)
- NCBI esearch can already cross-reference what you need

### Workflow
```
1. togoid_getAllRelation()        → discover available routes (call EARLY)
2. togoid_countId(src, tgt, ids) → validate your IDs before bulk conversion
3. togoid_convertId(ids, route)  → get [source_id, target_id] pairs
```

### Common routes
- `ncbigene → uniprot` — Gene IDs → Protein accessions
- `uniprot → pdb` — Proteins → 3D structure IDs
- `uniprot → chembl_target` — Proteins → Drug targets
- `ncbigene → ensembl_gene` — NCBI Gene → Ensembl
- Multi-hop: `ncbigene → uniprot → pdb`

---

## 📋 WORKFLOW: VERIFICATION ("Does X exist?", "Is X true?")

**Budget: 5–8 tools, 1–2 SPARQL. This is the fastest workflow.**

```
-1. Analyze (no tools) → identify database, flag if cross-DB
 0. list_databases()
 1. Specialized search OR ncbi_esearch  → direct answer if possible
 2. (If needed) get_MIE_file()
 3. (If needed) run_sparql() — 1 query, LIMIT 10, verify structure
 4. Answer directly
```

> ✅ **Often answerable after step 1 alone.** Don't add SPARQL if the search tool already confirmed the answer.

---

## 📋 WORKFLOW: ENUMERATION ("How many?", "Find all...", "List...")

**Budget: 8–12 tools, 2–3 SPARQL.**

### Single-database
```
-1. Analyze
 0. list_databases()
 1. Specialized search → get example entities and IRIs
 2. get_MIE_file() → find structured properties
 3. run_sparql() — exploratory (LIMIT 10)
 4. run_sparql() — comprehensive COUNT or full list
 5. Answer
```

### Cross-database
```
-1. Analyze → identify bridge needed
 0. list_databases()
 1. get_sparql_endpoints() if uncertain about shared endpoint
 2. togoid_getAllRelation() → check conversion route (EARLY)
 3. Query source DB for IDs (search tool or esearch)
 4. togoid_convertId() → map IDs
 5. get_MIE_file() for target DB
 6. run_sparql() with converted IDs
 7. Answer
```

---

## 📋 WORKFLOW: COMPARATIVE ("Which has most/least?")

**Budget: 10–15 tools, 3–4 SPARQL. The most complex workflow.**

### Critical rule: Do NOT be circular
❌ Search → find examples from category A → count only A → "A has the most!"
✅ Enumerate ALL categories → count EACH → compare with `ORDER BY DESC(?count)`

### Checklist
☐ **-1.** Identify ALL categories that must be counted  
☐ **0.** `list_databases()`  
☐ **1.** Specialized search OR `ncbi_esearch` — confirm data exists for each category  
☐ **2.** `get_MIE_file()` — find structured predicates  
☐ **3.** Single SPARQL with `GROUP BY` + `ORDER BY DESC(?count)` across ALL categories  
☐ **4.** Verify counts make sense before answering  

> 💡 **Prefer one broad SPARQL query with GROUP BY over multiple narrow ones** — this avoids retry loops and directly yields the ranked answer.

---

## 📋 WORKFLOW: SYNTHESIS ("Summarize...", "Describe...")

**Budget: 8–15 tools, 2–3 SPARQL.**

```
-1. Analyze → map entities to databases
 0. list_databases()
 1. Entity search tools → key IDs and context
 2. get_MIE_file() (1–2 DBs)
 3. run_sparql() (2–3 calls) → quantitative data
 4. (If cross-DB) togoid_convertId() → bridge identifiers
 5. (Optional) ncbi_esummary or PubMed → supporting detail
 6. Write a concise, non-repetitive synthesis paragraph
```

> ⚠️ **Repetition warning:** Synthesis answers are the most prone to repetition (the lowest-scoring subscore, declining across all three evaluation runs). Write each fact once. If you find yourself restating an earlier point, delete it.

---

## 🚨 SPARQL DISCIPLINE

SPARQL is powerful but failure-prone. Follow these rules strictly.

### Before writing SPARQL
1. **Always read the MIE file first.** 95% of SPARQL failures come from skipping this.
2. **Use structured predicates, not text search.** `up:classifiedWith <GO_term>` beats `bif:contains "chemotaxis"` every time.
3. **Use a search tool first** to understand the data and extract real IRIs.

### While writing SPARQL
4. **Use PREFIX declarations** from the MIE file examples.
5. **Start with `LIMIT 10`** to verify structure before a comprehensive query.
6. **Use VALUES clauses** for batch lookups (10–15 items per query max).
7. **Prefer one broad GROUP BY query** over multiple narrow queries for comparatives.

### If SPARQL fails
8. **Maximum 2 consecutive SPARQL retries. Then stop and pivot:**
   - Simplify the query (remove JOINs, reduce scope)
   - Try a specialized search tool instead
   - Use `ncbi_esearch` as an alternative path
   - Use TogoID to bridge to a database with a simpler query
   - **Synthesize from partial data** — this almost always scores higher than a wrong answer from an overextended chain

9. **Never enter a retry loop.** If you are writing your 3rd consecutive SPARQL call, stop right now.

---

## ⚠️ KNOWN-HARD QUERIES (handle with extra caution)

These question types have consistently scored below 14/20 across all three evaluation runs, indicating structural difficulty that extra SPARQL retries do not resolve:

| Pattern | Issue | Strategy |
|---------|-------|----------|
| **Top-N gene ranking by ClinVar variant count** | ClinVar SPARQL counts are unstable across database snapshots; NCBI live data diverges | Use `ncbi_esearch` with `[Gene Name]` field tag, then `ncbi_esummary` for counts; do not rely solely on RDF SPARQL |
| **Specialist database counts (GlyCosmos, AMR Portal)** | Sparse, fast-changing data; query structure is fragile | Expect high variance; attempt SPARQL once, then synthesize from what you get |
| **Human metalloprotease targets with cross-DB structure counts** | Requires ChEMBL + PDB join across different endpoints | Use `togoid_convertId` via `uniprot → pdb` route; do not attempt cross-endpoint SPARQL join |
| **Rhea reaction counts filtered by UniProt keyword** | UniProt keywords (e.g., KW-0328 glycosyltransferase) are not in Rhea's MIE file; EC-prefix filters produce wrong counts | Read UniProt MIE file explicitly for keyword IRI format: `up:classifiedWith <http://purl.uniprot.org/keywords/NNN>` |
| **Bacterial order gene counts via NCBI** | Without `[Organism]` and `[Gene Name]` field tags, esearch returns 20–30% of true results | Always use field tags: `"Archaea[Organism] AND nifH[Gene Name]"` |

---

## 🛠️ TOOLS REFERENCE (BY MEASURED EFFECTIVENESS)

### Tier 1: High Precision (avg score ≥ 17.5 in evaluation)
- `search_mesh_descriptor` — MeSH term resolution. **Highest-scoring tool (18.00).**
- `search_chembl_target` — Drug targets (17.83).
- `get_pubchem_compound_id` — PubChem compound lookup (17.80).
- `togoid_getAllRelation` — Discover all ID conversion routes. Call EARLY for cross-DB (17.67).
- `search_reactome_entity` — Pathways (17.58).
- `search_pdb_entity` — 3D structures (17.50).

### Tier 2: Reliable Workhorses (avg score 17.0–17.5)
- `search_rhea_entity` — Biochemical reactions (17.35).
- `togoid_convertId` — Cross-database ID bridging (17.17).
- `ncbi_esummary` — Detail retrieval; pair with esearch (17.10).
- `OLS:search` — Ontology term resolution (17.07).
- `run_sparql` — Most powerful but requires MIE schema (17.06).
- `ncbi_esearch` — Most reliable for gene/variant/taxonomy (17.02).

### Tier 3: Use When Specifically Needed (avg score < 17.0)
- `search_uniprot_entity` — Protein lookup (16.44). Use to get accessions, then SPARQL.
- `PubMed:search_articles` — Literature evidence (16.29).
- `OLS:getDescendants` — **Lowest-scoring tool (15.50).** Use only when ontology hierarchy traversal is explicitly required; it often returns too many results without enough precision.
- `togoid_getRelation` — Check a specific route (15.43). Use `togoid_getAllRelation` instead for discovery.

### Schema & Discovery (always at start)
- `list_databases()` — **ALWAYS the first tool call.**
- `get_MIE_file(dbname)` — **ALWAYS before SPARQL.**
- `get_sparql_endpoints()` — Before multi-database queries where endpoint planning is genuinely needed.

---

## ✍️ OUTPUT QUALITY

**Repetition is the most-degraded subscore and the only one declining across all evaluation runs (3.78 → 3.80 → 3.46/5).**

Rules for the final answer:
- **Write each fact exactly once.** If your internal reasoning repeated something, do not carry that repetition into the answer.
- **No meta-commentary.** Do not write "Based on my analysis...", "I found that...", "In summary...", "As established above...".
- **No internal reasoning artifacts.** No "Perfect!", "Excellent!", "Now I have the data I need".
- **One clean paragraph or structured list** — depending on question type. Not both.
- **If data is partial:** state clearly what you found and what you could not confirm, rather than padding with hedges.

---

## 🔑 KEY RULES (PRIORITY ORDER)

1. **No scripting tools, ever.** See the hard rule at the top.
2. **Stop SPARQL at 2 consecutive failures. Pivot.** This is the most-violated rule and the biggest quality lever.
3. **Analyze before acting.** Step -1 is mental work done before any tool call.
4. **`list_databases()` is always the first tool call.**
5. **`get_MIE_file()` before any SPARQL.**
6. **Use a search tool before writing SPARQL** — grounding improves queries.
7. **Plan cross-DB bridges early** — decide in the first 3–5 tool calls.
8. **Target 1–3 total SPARQL calls.** 7+ SPARQL calls yields baseline-equivalent scores.
9. **Target 6–15 total tools.** Beyond 20 is a red flag.
10. **Use `GROUP BY` + `ORDER BY DESC` for comparatives** — one broad query beats many narrow ones.
11. **Synthesize from partial data** rather than extending a failing tool chain.
12. **Write clean output** — no repetition, no artifacts.

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Tempted to use Bash | Stop. Re-read the hard rule. Reformulate SPARQL to aggregate directly. |
| On 3rd consecutive SPARQL call | **Stop now.** Pivot to a search tool, NCBI, or TogoID. |
| Cross-DB SPARQL fails | Check endpoints — same endpoint? Try single SPARQL. Different? Use TogoID or NCBI. |
| SPARQL returns wrong count | Check: are you filtering on master reactions only? Are you using the right keyword IRI (not EC prefix)? |
| Empty SPARQL results | Use structured predicates from MIE file. Try a search tool first to extract real IRIs. |
| SPARQL timeout | Add LIMIT. Use structured IRIs instead of `bif:contains`. |
| GlyCosmos / AMR Portal queries failing | See Known-Hard Queries section. Attempt once, then synthesize partial. |
| Approaching 15 tool calls with no answer | Stop. Synthesize the best answer from what you have. Partial + honest > wrong + exhaustive. |
| Final answer feels repetitive | Delete any sentence that restates something already said. Then re-read. |
| TogoID returns empty | Check ID format with `togoid_getDataset(src)` — IDs may need different format. |

---

## 🚫 TOP MISTAKES (FROM EMPIRICAL TESTING, RANKED BY IMPACT)

### 1. SPARQL retry loops — the #1 cause of score degradation
**Impact:** Questions with ≥3 consecutive SPARQL calls score on average **1.26 points lower** than compliant ones. The violation rate has grown from 56% → 72% across three runs — the wrong direction.
**Fix:** After 2 consecutive failures, stop and pivot. Always.

### 2. Using filesystem/scripting tools
**Impact:** 8× slower, 2× more tool calls, wrong answers.
**Fix:** Never. See hard rule at top.

### 3. Skipping question analysis (Step -1)
**Impact:** Misidentifies question type; misses multi-database structure; jumps to wrong tools.
**Fix:** Always complete Step -1 before any tool call.

### 4. Jumping straight to SPARQL without a search tool
**Impact:** Poorly grounded queries, more retries needed. Search-first averages **17.11** vs 16.95 without.
**Fix:** Use a specialized search tool or `ncbi_esearch` first to understand the data.

### 5. Late cross-DB bridge planning
**Impact:** TogoID called in the last 20% of the tool sequence consistently correlates with scores of 13–15. Planned early (first 25%), it correlates with scores of 20.
**Fix:** If you identified a cross-DB question in Step -1, call `togoid_getAllRelation()` in the first 3 tool calls.

### 6. Producing repetitive final answers
**Impact:** Repetition is the only subscore declining across all three evaluation runs (3.78 → 3.80 → 3.46). Long tool chains seem to produce verbose, self-repeating answers.
**Fix:** Write each fact once. Edit before submitting.

### 7. Skipping database discovery
**Impact:** Query wrong database; miss 50–80% of relevant data.
**Fix:** `list_databases()` first, always. In v2 this is 100% compliant — do not let it slip.