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

## 🏗️ BULK MODE — heavy retrieval / full comparison tasks

Triggered by GATE 0a. Treat `run_sparql` as a probe, not a retrieval
engine, once a task leaves bounded/sample-sized territory.

1. **Study the shape first, with cheap bounded probes only:**
   - `get_MIE_file(database)` — schema + `critical_warnings`.
   - `get_graph_list(database)` — which named graphs hold what.
   - `COUNT(*)` queries to size the problem before touching it:
     `SELECT (COUNT(*) AS ?c) WHERE { ... }` — never skip sizing an
     unbounded task.
   - One or two `LIMIT 50` samples to confirm predicate/datatype shape.

2. **Decide:** can this be done in ≤2–3 bounded SPARQL calls (one
   `GROUP BY`, one `VALUES` batch)? If yes, stay in normal SPARQL
   discipline (LIMIT, max 2 consecutive) — this was not actually bulk.

3. **If not, switch to scripting:**
   - Extract via paginated SPARQL (`OFFSET`/`LIMIT` loops, ~5k–10k
     rows/page) driven from a script, not one giant query.
   - Do joins, set comparison, ontology diffing, and aggregation
     locally after extraction — not server-side in one query.
   - Example from practice: confirming whether a predicate is defined
     as part of an ontology vs. only used in data — probe `get_graph_list`
     → bounded `COUNT(*)` per candidate graph → only escalate to a
     scripted/paginated pull if a full dump turns out to be necessary.

4. **Never retry an unbounded query verbatim after a timeout.** Either
   add `LIMIT`/`OFFSET` pagination, narrow with a specific
   `GRAPH`/`VALUES` clause, or fall back to scripted pagination per (3).