> Usage Guide reference file — fetched on demand with `get_workflow(name="usage-guide", path="references/bulk-mode.md")`. The always-loaded core is `TogoMCP_Usage_Guide()`.

## 🏗️ BULK MODE — heavy retrieval / full comparison tasks

Triggered by GATE 0a. Treat `run_sparql` as a probe, not a retrieval
engine, once a task leaves bounded/sample-sized territory.

1. **Study the shape first, with cheap bounded probes only:**
   - `get_MIE_file(database)` — verified `examples` + `global_gotchas`.
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
