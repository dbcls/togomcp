# TogoMCP Usage Guide (v3 — Empirically Revised)

## 🚫 CRITICAL RULES — READ FIRST

Two rules account for most quality loss. Both are empirically validated, not stylistic.

### 1. Never use filesystem or scripting tools

No shell execution, file read/write, or code interpreters. Empirically: 8× slower, 2× more tool calls, wrong answers. If post-processing feels necessary, the SPARQL query is wrong — reformulate it to aggregate directly, or use `ncbi_esearch` / `togoid_convertId` to get structured data without manual mapping.

### 2. Stop after 2 consecutive `run_sparql` calls

"Consecutive" = 2 `run_sparql` calls in a row with no other tool call between them. The counter resets after any non-SPARQL call.

| Max consecutive SPARQL | Avg score (n=129) |
|------------------------|-------------------|
| **1–2 (compliant)** | **17.81** ← best |
| 3–4 | 16.55 |
| 5–7 | 17.39 |
| 8+ | 16.43 |

**At your 3rd consecutive SPARQL call, stop.** Pivot to: a search tool, `ncbi_esearch`, `togoid_convertId`, query simplification, or **synthesize from partial data**. The worst documented run had 20 consecutive SPARQL calls and scored 15/20 — *worse than the no-tools baseline*.

---

## 🧠 STEP -1: ANALYZE BEFORE TOUCHING ANY TOOL

Answer four questions before any tool call:

**1. Question type?**

| Type | Signal | Workflow | SPARQL budget |
|------|--------|----------|---------------|
| Verification | "Does X exist?" | VERIFICATION | 1–2 |
| Enumeration | "How many?", "List all" | ENUMERATION | 2–3 |
| Comparative | "Which has most?" | COMPARATIVE | 3–4 |
| Synthesis | "Summarize", "Describe" | SYNTHESIS | 2–3 |
| Exploration | "Tell me more", "深掘りして" | EXPLORATION | 1–4 |

**2. What entities and concepts?** List every distinct entity class. "Bacterial orders with most carbon-fixation proteins" → taxonomy, UniProt, GO.

**3. Which databases? Same endpoint?** Map entities → databases → endpoint. **If different endpoints, plan the bridge NOW**, not after SPARQL fails.

**4. Comparative?** If yes, you must enumerate **all** categories with `GROUP BY` + `ORDER BY DESC(?count)` — don't search within one category and call it the winner.

---

## ⚡ QUICK START

```
STEP -1: Analyze (no tools)
STEP  0: list_databases()                  ← ALWAYS first tool call
STEP  1: Specialized search OR ncbi_esearch
STEP  2: get_MIE_file(database)            ← ALWAYS before run_sparql
STEP  3: run_sparql() — LIMIT 10 first; max 2 consecutive
STEP  4: Synthesize. No repetition, no meta-commentary.
```

---

## 🎯 EMPIRICAL BUDGETS

From 150 evaluated questions. Treat numbers as directional; the patterns are robust.

| Metric | Optimal range | Red flag |
|--------|---------------|----------|
| Total tool calls | **6–15** (avg 17.40–17.50) | 21+ (avg 16.23) |
| Total SPARQL calls | **1–3** (avg 17.67) | 7+ (≤16.96) |
| Consecutive SPARQL | **1–2** (avg 17.81) | 3+ (≤16.55) |

**Tool effectiveness** (avg score, ≥5 appearances):

- **Tier 1 (≥17.5):** `search_mesh_descriptor` 18.00 · `search_chembl_target` 17.83 · `get_pubchem_compound_id` 17.80 · `togoid_getAllRelation` 17.67 · `search_reactome_entity` 17.58 · `search_pdb_entity` 17.50
- **Tier 2 (17.0–17.5):** `search_rhea_entity` · `togoid_convertId` · `ncbi_esummary` · `run_sparql` · `ncbi_esearch` · `OLS:search`
- **Tier 3 (<17.0):** `search_uniprot_entity` 16.44 · `PubMed:search_articles` 16.29 · `OLS:getDescendants` 15.50 · `togoid_getRelation` 15.43

`OLS:*` and `PubMed:*` come from external MCP servers; substitute `search_mesh_descriptor` and `ncbi_esearch` if unavailable. `togoid_getRelation` confirms a known route — for *discovery*, use `togoid_getAllRelation`.

---

## 🔍 STEP 0: `list_databases()` — ALWAYS FIRST

Match query keywords to database descriptions: "MANE" → Ensembl, "drug targets" → ChEMBL, "clinical variants" → ClinVar, "pathways" → Reactome, "culture media" → BacDive/MediaDive, "glycobiology" → GlyCosmos (specialist; see Known-Hard Queries).

---

## 📄 MIE FILES — ALWAYS BEFORE SPARQL

Call `get_MIE_file(database)` before any `run_sparql` for that database. Read in order:

1. **`critical_warnings`** — mandatory filters (e.g., `up:reviewed 1` in UniProt: omitting queries 244M instead of 589K rows and times out) and IRI namespace traps. Skipping this is the #1 cause of silent failures.
2. **`shape_expressions`** — authoritative list of structured predicates. Use `up:classifiedWith <GO_IRI>` instead of `bif:contains "chemotaxis"`; structured predicates are 10–100× faster.
3. **PREFIX declarations** from `schema_info` or `sample_rdf_entries` — copy verbatim, don't guess.
4. **`sparql_query_examples`** — modify a working scaffold rather than write from scratch.
5. **`anti_patterns`** if results are empty/wrong — common failure modes with corrected alternatives.

**Query design hierarchy** (fastest → slowest): specific concept IRI → `VALUES` with multiple IRIs → typed predicate → graph navigation (`rdfs:subClassOf+`) → `bif:contains` → `FILTER(CONTAINS())`. Confirm via `shape_expressions` that no structured alternative exists before any text search.

---

## 🔌 ENDPOINTS

- ✅ **sib:** UniProt + Rhea
- ✅ **ncbi:** ClinVar + PubMed + PubTator + NCBI Gene + MedGen
- ✅ **primary:** MeSH + GO + Taxonomy + MONDO + NANDO
- ✅ **ebi:** ChEMBL + ChEBI + Reactome + Ensembl
- ❌ UniProt (sib) ↔ ChEMBL (ebi) → use TogoID
- ❌ PubChem ↔ anything → `get_pubchem_compound_id`, then bridge

Same endpoint → single SPARQL. Different → NCBI cross-reference if available, else `togoid_convertId`, else search-on-A → SPARQL-on-B. Calling `get_sparql_endpoints()` did not consistently improve scores (17.59 without vs. 16.73 with) — call it only when you genuinely need to plan a bridge.

---

## 🔗 TogoID — PLAN EARLY

Late TogoID use (>50% into the sequence) correlates with worse scores. Plan in the first 3–5 calls.

```
1. togoid_getAllRelation()        ← discover routes (call EARLY)
2. togoid_countId(src, tgt, ids)  ← validate IDs before bulk conversion
3. togoid_convertId(ids, route)   ← get [source_id, target_id] pairs
```

Common routes: `ncbigene → uniprot`, `uniprot → pdb`, `uniprot → chembl_target`, `ncbigene → ensembl_gene`. Multi-hop OK: `ncbigene → uniprot → pdb`. If `togoid_convertId` returns empty, check format with `togoid_getDataset(src)` (versioned vs unversioned accessions).

Skip TogoID when: both DBs share an endpoint, or `ncbi_esearch` already cross-references what you need.

---

## 📋 WORKFLOWS

### VERIFICATION ("Does X exist?") — 5–8 tools, 1–2 SPARQL
`-1` analyze → `0` list_databases → `1` search/esearch (often answers it) → `2` MIE if needed → `3` run_sparql LIMIT 10 if needed → `4` answer.

### ENUMERATION ("How many?", "List all") — 8–12 tools, 2–3 SPARQL
**Single DB:** `-1` analyze → `0` list_databases → `1` search → `2` MIE → `3` exploratory SPARQL (LIMIT 10) → `4` comprehensive COUNT/list → answer.
**Cross DB:** + `togoid_getAllRelation()` early → `togoid_convertId` → MIE for target → SPARQL on target.

### COMPARATIVE ("Which has most?") — 10–15 tools, 3–4 SPARQL
**Critical:** enumerate ALL categories, count EACH, `ORDER BY DESC(?count)`. Don't search one category and declare it the winner.
`-1` identify all categories → `0` list_databases → `1` search/esearch confirms data exists → `2` MIE → `3` single SPARQL with `GROUP BY` across all categories → verify counts make sense → answer. **Prefer one broad GROUP BY over many narrow queries.**

### SYNTHESIS ("Summarize", "Describe") — 8–15 tools, 2–3 SPARQL
`-1` analyze → `0` list_databases → `1` entity searches → `2` MIE (1–2 DBs) → `3` SPARQL (2–3 calls) → `4` togoid_convertId if cross-DB → `5` ncbi_esummary/PubMed for detail → `6` concise paragraph.
> **Repetition warning:** synthesis answers degrade most on repetition (3.78 → 3.46/5 across runs). Each fact once.

### EXPLORATION ("Tell me more", "深掘りして") — open-ended deep dives
Use this when the seed is broad ("tell me about X") rather than a specific bounded question. All rules above still apply. Add three exploration-specific habits:

**Before any tool call — Seed Definition** (write it down):
1. The seed in one sentence (entity, finding, or open question).
2. 3–5 facts already known — prevents re-discovering them.
3. 3–5 specific unknowns — these drive every tool choice.
4. Entity → primary DB → supporting DB map.
5. If unknowns span endpoints, plan the bridge (`togoid_convertId` route) now.

**After each tool call — concierge check** (one line, recorded):
> "What did this confirm? What new question does it raise? Pursue now, or save for Next Steps?"

**Cross-database chain:** attempt at least one chain (e.g. UniProt → `togoid_convertId uniprot→pdb` → PDB → ChEMBL). Even a 2-DB connection that wasn't established before is valuable. "No results" from a database is a finding — report it as a gap, not a failure.

**End — prioritized Next Steps (3–5):** each item names a specific tool + query string + the unknown it addresses. "Look into this more" is not a Next Step.

Budget: 6–15 tool calls (Standard); 1–4 SPARQL total. If wanting a 5th SPARQL, synthesize from what you have — almost always the better answer.

---

## 🚨 SPARQL DISCIPLINE

**Before:** read MIE `critical_warnings` + `shape_expressions`; use structured predicates over text search; ground with a search tool first.
**While writing:** copy PREFIX declarations from MIE; start with `LIMIT 10`; `VALUES` clauses for batch lookups (≤15 items); one broad `GROUP BY` query over many narrow ones.
**On failure:** max 2 consecutive `run_sparql`. At call #3, pivot — simplify, switch to a search tool, use `ncbi_esearch` or TogoID, or synthesize from partial data.

---

## ⚠️ KNOWN-HARD QUERIES

These score below 14/20 across all evaluation runs. Extra retries don't help — handle with extra caution.

| Pattern | Strategy / fallback |
|---------|---------------------|
| Top-N gene ranking by ClinVar variant count | RDF/NCBI counts diverge. Use `ncbi_esearch` with `[Gene Name]` + `ncbi_esummary`; report with caveat that RDF snapshot may differ. |
| Specialist database counts (GlyCosmos, AMR Portal) | Sparse, fast-changing. One SPARQL attempt then synthesize; note approximation. |
| Human metalloprotease targets with cross-DB structure counts | ChEMBL + PDB across endpoints. Use `togoid_convertId` via `uniprot → pdb`; report counts separately, no joint filter. |
| Rhea reaction counts filtered by UniProt keyword | Keywords not in Rhea MIE. Read UniProt MIE for keyword IRI: `up:classifiedWith <http://purl.uniprot.org/keywords/NNN>`. EC-prefix is a fallback with overcount caveat. |
| Bacterial gene counts via NCBI | Field tags mandatory: `"Archaea[Organism] AND nifH[Gene Name]"`. Without them, esearch returns 20–30% of true results. |

---

## ✍️ OUTPUT QUALITY

Repetition is the only subscore declining across all evaluation runs (3.78 → 3.46/5).

- Each fact exactly once. If a step repeated something, drop it.
- No meta-commentary: no "Based on my analysis", "I found that", "In summary", "As established above".
- No reasoning leakage — intermediate tool results, self-assessments, chain-of-thought fragments don't belong in the final answer.
- One clean paragraph **or** structured list — not both.
- Partial data: state clearly what was found and what could not be confirmed. Don't pad with hedges.

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| On 3rd consecutive SPARQL | Stop. Pivot to search/NCBI/TogoID/partial synthesis. |
| Cross-DB SPARQL fails | Check endpoints — same → single SPARQL; different → TogoID or NCBI. |
| Empty SPARQL results | Use structured predicates from MIE; extract real IRIs via search first. |
| SPARQL timeout | Add LIMIT; replace `bif:contains` with structured IRIs. |
| Wrong count returned | Master reactions only? Right keyword IRI (not EC prefix)? |
| TogoID returns empty | Check ID format with `togoid_getDataset(src)` (versioned vs unversioned). |
| ≥15 tool calls, no answer | Stop. Synthesize from what you have. Partial + honest > wrong + exhaustive. |
| Final answer feels repetitive | Remove any sentence restating an earlier point. Re-read. |
| OLS4 / PubMed unavailable | `OLS:search` → `search_mesh_descriptor`; `PubMed:search_articles` → `ncbi_esearch`. |
