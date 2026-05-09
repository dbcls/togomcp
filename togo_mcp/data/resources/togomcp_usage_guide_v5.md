# TogoMCP Usage Guide (v5)

---

## ⛔ GATE 0 — BEFORE EVERYTHING ELSE

**Does the message contain a specific, bounded question?**
Bounded = a count, a list, a yes/no, a named entity, a comparison with a winner.

```
Bounded? YES → proceed to STEP −1
         NO  → EXPLORATION. Write Seed Definition now. No tools until it's done.
```

**NO signals:** "tell me more" / "go deeper" / "what about X?" / "深掘りして" /
any follow-up that extends a prior answer / any message with no bounded answer in advance.

> **Continuation trap:** Prior workflow does not carry forward. Re-run GATE 0 every turn,
> even if the last turn was SYNTHESIS or EXPLORATION. This is the most common miss.

---

## 🚫 CRITICAL RULES

**1. No filesystem or scripting tools.** 8× slower, 2× more tool calls, wrong answers.
If post-processing feels necessary, the SPARQL query is wrong — fix it instead.

**2. Max 2 consecutive `run_sparql` calls.** Counter resets after any non-SPARQL call.
At call #3: stop. Pivot to a search tool, `ncbi_esearch`, `togoid_convertId`, or
synthesize from partial data.

| Max consecutive SPARQL | Avg score |
|------------------------|-----------|
| **1–2**                | **17.81** |
| 3–4                    | 16.55     |
| 8+                     | 16.43     |

---

## 🧠 STEP −1: ANALYZE (no tools)

**1. Question type** — EXPLORATION is the default when in doubt:

```
Bounded?
├── YES → "Does X exist?"              → VERIFICATION  (1–2 SPARQL)
│         "How many?" / "List all"     → ENUMERATION   (2–3 SPARQL)
│         "Which has most?"            → COMPARATIVE   (3–4 SPARQL)
│         "Summarize" / "Describe"     → SYNTHESIS     (2–3 SPARQL)
└── NO  → EXPLORATION                                  (1–4 SPARQL)
```

When ambiguous, take the lower branch. Seed Definition costs ~10 seconds;
wrong workflow costs 5–10 tool calls.

**2. Entities and databases.** List every distinct entity class → map to databases → map
to endpoints. If cross-endpoint, plan the TogoID bridge now.

**3. Comparative?** Must enumerate ALL categories with `GROUP BY ORDER BY DESC(?count)`.

---

## ⚡ QUICK START

```
GATE 0  → classify (bounded → STEP −1 | open-ended → Seed Definition)
STEP −1 → analyze
STEP  0 → find_databases(keywords=[...])   always first
STEP  1 → search tool or ncbi_esearch
STEP  2 → get_MIE_file(database)           always before run_sparql
STEP  3 → run_sparql()  LIMIT 10 first · max 2 consecutive
STEP  4 → synthesize    no repetition · no meta-commentary
```

---

## 🎯 EMPIRICAL BUDGETS

| Metric             | Optimal    | Red flag |
|--------------------|------------|----------|
| Total tool calls   | 6–15       | 21+      |
| Total SPARQL calls | 1–3        | 7+       |
| Consecutive SPARQL | 1–2        | 3+       |

**Tool tiers** (avg score, ≥5 appearances):
- **Tier 1 (≥17.5):** `search_mesh_descriptor` · `search_chembl_target` · `get_pubchem_compound_id` · `togoid_getAllRelation` · `search_reactome_entity` · `search_pdb_entity`
- **Tier 2 (17.0–17.5):** `search_rhea_entity` · `togoid_convertId` · `ncbi_esummary` · `run_sparql` · `ncbi_esearch` · `OLS:search`
- **Tier 3 (<17.0):** `search_uniprot_entity` · `PubMed:search_articles` · `OLS:getDescendants` · `togoid_getRelation`

If `OLS:*` or `PubMed:*` unavailable, substitute `search_mesh_descriptor` / `ncbi_esearch`.
Use `togoid_getAllRelation` for discovery; `togoid_getRelation` only to confirm a known route.

---

## 🔍 STEP 0: DATABASE DISCOVERY

- **`find_databases(keywords=[...])`** — default; token-efficient substring match on title,
  description, and curated synonyms. Add `match="all"` to require every keyword.
- **`find_databases(category=...)`** — browse a topic area (`protein`, `gene`, `variant`,
  `compound`, `drug_target`, `pathway`, `reaction`, `ontology`, `structure`, `literature`,
  `taxonomy`, `disease`, `materials`, `physics`, …). Call `list_categories()` first if unsure.
- **`list_databases()`** — full catalog; higher cost. Only when too vague to keyword-match.

Quick hints: "MANE" → Ensembl · "drug targets" → ChEMBL · "clinical variants" → ClinVar ·
"pathways" → Reactome · "superconductor" → SuperCon · "glycobiology" → GlyCosmos.

---

## 📄 MIE FILES — ALWAYS BEFORE SPARQL

Call `get_MIE_file(database)` before any `run_sparql`. Read in this order:

1. **`critical_warnings`** — mandatory filters and IRI traps. The #1 cause of silent failures.
2. **`shape_expressions`** — use structured predicates over text search (10–100× faster).
3. **PREFIX declarations** — copy verbatim.
4. **`sparql_query_examples`** — modify a working scaffold; don't write from scratch.
5. **`anti_patterns`** — if results are empty or wrong.

**Predicate hierarchy** (fastest → slowest): specific IRI → `VALUES` → typed predicate →
graph navigation → `bif:contains` → `FILTER(CONTAINS())`.

---

## 🔌 ENDPOINTS

| Endpoint    | Databases                                       |
|-------------|-------------------------------------------------|
| **sib**     | UniProt · Rhea                                  |
| **ncbi**    | ClinVar · PubMed · PubTator · NCBI Gene · MedGen |
| **primary** | MeSH · GO · Taxonomy · MONDO · NANDO            |
| **ebi**     | ChEMBL · ChEBI · Reactome · Ensembl             |

Same endpoint → single SPARQL. Different endpoints → `togoid_convertId` or NCBI
cross-reference. Call `get_sparql_endpoints()` only when genuinely planning a bridge
(it hurt scores when called routinely: 16.73 vs. 17.59 without).

---

## 🔗 TogoID — PLAN EARLY

Late TogoID use (>50% into the sequence) correlates with worse scores.

```
1. togoid_getAllRelation()         discover available routes — call EARLY
2. togoid_countId(src, tgt, ids)   validate before bulk conversion
3. togoid_convertId(ids, route)    returns [source_id, target_id] pairs
```

Common routes: `ncbigene → uniprot` · `uniprot → pdb` · `uniprot → chembl_target` ·
`ncbigene → ensembl_gene`. Multi-hop OK (`ncbigene → uniprot → pdb`). If empty, check
ID format with `togoid_getDataset(src)`.

Skip when: both DBs share an endpoint, or `ncbi_esearch` already cross-references the IDs.

---

## 📋 WORKFLOWS

**VERIFICATION** (1–2 SPARQL) — `GATE 0` → analyze → find_databases → search/esearch
(often sufficient) → MIE if needed → run_sparql LIMIT 10 → answer.

**ENUMERATION** (2–3 SPARQL) — + exploratory SPARQL LIMIT 10 → comprehensive COUNT.
Cross-DB: add `togoid_getAllRelation` early → `togoid_convertId` → SPARQL on target.

**COMPARATIVE** (3–4 SPARQL) — enumerate ALL categories in one `GROUP BY ORDER BY DESC`.
Never search one category and declare it the winner.

**SYNTHESIS** (2–3 SPARQL) — entity searches → MIE → SPARQL → `togoid_convertId` if
cross-DB → `ncbi_esummary` for detail → one concise paragraph. Each fact once.

**EXPLORATION** (1–4 SPARQL) — default when GATE 0 routes NO. Four required habits:

1. **Seed Definition** (before any tool):
   - Seed in one sentence.
   - 3–5 facts already known (don't re-discover them).
   - 3–5 specific unknowns (these drive every tool choice).
   - Entity → DB map; bridge plan if cross-endpoint.

2. **Concierge check** after each tool call (one line):
   *"What did this confirm? What new question does it raise? Pursue now or save?
   Have I called this DB 3+ times in a row?"*

3. **Breadth — execute the entity→DB map.** Each entity class in your map must
   produce at least one direct call to the DB you mapped it to. Reading UniProt
   text annotations does **not** substitute for hitting Rhea / Taxonomy / ChEMBL /
   PubChem / MeSH directly — even when UniProt text mentions an EC number, a
   taxon, or a ligand, you still owe the mapped DB a call.
   **Max 3 consecutive calls against the same database/tool family.** Counter
   resets on any cross-DB call. Before a 4th, pivot to an unexplored DB from
   your map.

4. **Cross-database chain** — attempt at least one cross-endpoint chain
   (e.g. UniProt → PDB → ChEMBL). "No results" is a finding; report it as a gap.

5. **Prioritized Next Steps** (3–5 items at the end):
   each = specific tool + query string + unknown it addresses.
   "Look into this more" is not a Next Step.

---

## 🚨 SPARQL DISCIPLINE

- **Before:** read `critical_warnings` + `shape_expressions`; ground with a search tool first.
- **While writing:** copy PREFIXes from MIE; `LIMIT 10` first; `VALUES` for batch lookups
  (≤15 items); one broad `GROUP BY` over many narrow queries.
- **On failure:** max 2 consecutive. At #3: pivot to search, `ncbi_esearch`, TogoID, or
  partial synthesis.

---

## ⚠️ KNOWN-HARD QUERIES

| Pattern | Fallback |
|---------|----------|
| Top-N genes by ClinVar variant count | `ncbi_esearch [Gene Name]` + `ncbi_esummary`; caveat RDF snapshot divergence. |
| Specialist DB counts (GlyCosmos, AMR Portal) | One SPARQL attempt → synthesize; note approximation. |
| Human metalloprotease targets + structure counts | `togoid_convertId uniprot→pdb`; report counts separately. |
| Rhea reactions filtered by UniProt keyword | Read UniProt MIE for keyword IRI (`up:classifiedWith`); EC-prefix fallback overcounts. |
| Bacterial gene counts via NCBI | Field tags mandatory: `"Archaea[Organism] AND nifH[Gene Name]"` — omitting loses 70–80%. |

---

## ✍️ OUTPUT QUALITY

- Each fact exactly once.
- No meta-commentary ("Based on my analysis", "In summary", "As established above").
- No reasoning leakage in the final answer.
- Prose **or** list — not both.
- Partial data: state what was found and what wasn't. No padding.

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Missed EXPLORATION trigger | Return to GATE 0. Re-classify. If NO, write Seed Definition now. |
| Stuck on one DB (≥4 calls in EXPLORATION) | Pivot to the next unexplored DB from your entity→DB map. UniProt annotations don't substitute for direct Rhea/Taxonomy/ChEMBL/PubChem calls. |
| 3rd consecutive SPARQL | Stop. Pivot to search / NCBI / TogoID / partial synthesis. |
| Cross-DB SPARQL fails | Check endpoints; use TogoID or NCBI bridge. |
| Empty SPARQL results | Use structured predicates from MIE; extract IRIs via search first. |
| SPARQL timeout | Add LIMIT; replace `bif:contains` with structured IRIs. |
| Wrong count | Master reactions only? Correct keyword IRI (not EC prefix)? |
| TogoID empty | Check ID format with `togoid_getDataset(src)`. |
| ≥15 tool calls, no answer | Synthesize from partial data. Partial + honest > wrong + exhaustive. |
| Repetitive answer | Remove any sentence restating an earlier point. |
| OLS4 / PubMed unavailable | → `search_mesh_descriptor` / `ncbi_esearch`. |
