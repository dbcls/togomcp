## 📋 WORKFLOWS

**VERIFICATION** (1–2 SPARQL) — `GATE 0` → analyze → find_databases → search/esearch
(often sufficient) → MIE if needed → run_sparql LIMIT 10 → answer.

**ENUMERATION** (2–3 SPARQL) — + exploratory SPARQL LIMIT 10 → comprehensive COUNT.
Cross-DB: add `togoid_getAllRelation` early → `togoid_convertId` → SPARQL on target.

**COMPARATIVE** (3–4 SPARQL) — enumerate ALL categories in one `GROUP BY ORDER BY DESC`.
Never search one category and declare it the winner.

**SYNTHESIS** (2–3 SPARQL) — entity searches → MIE → SPARQL → `togoid_convertId` if
cross-DB → `ncbi_esummary` for detail → one concise paragraph. Each fact once.

**EXPLORATION** (1–4 SPARQL) — default when GATE 0 routes NO. Five required habits:

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

- **Before:** read `critical_warnings` + `co_hosted_graphs` + `shape_expressions`; ground
  with a search tool first.
- **While writing:** copy PREFIXes from MIE; **pin every graph** (see CO-TENANCY);
  `LIMIT 10` first; `VALUES` for batch lookups (≤15 items); one broad `GROUP BY` over
  many narrow queries.
- **On failure:** max 2 consecutive. At #3: pivot to search, `ncbi_esearch`, TogoID, or
  partial synthesis.

---

## 🕸️ CO-TENANCY & SILENT-FAILURE TRAPS

Everything in this section fails **silently** — no error, no zero rows, no doubled
count. The result is plausible, correctly shaped, and wrong.

An unpinned query reads **every graph on the endpoint**, not just your database's. A
sibling graph that re-declares a predicate inflates counts; one that *supplies* a
predicate you assume is native narrows your query to an intersection.
`dcterms:identifier` looks like UniProt's — on `sib` only the co-hosted **OMA** graph
supplies it, so `?protein dcterms:identifier ?acc` silently becomes **UniProt INTERSECT
OMA**, dropping every protein with no OMA record. It returned a wrong count (248; truth
249) that passed every check for months.

1. **Pin every pattern.** `FROM <g>` or `GRAPH <g> { ... }`. Partial pinning still
   leaks — the unpinned patterns read the union. **"Your database" may be *several*
   graphs** (the MIE `graphs:` list), not one — list them all as repeated `FROM`
   clauses. UniProt owns **~16 graphs**: protein triples live in `.../uniprot`, but a
   taxon's `scientificName`/`rank` live in `.../taxonomy` (and GO defs in `.../go`,
   diseases in `.../diseases`, …), so pinning only `.../uniprot` returns **empty** for
   a taxon-name leg (silent). Pin the *set* your DB owns — that also
   excludes the co-tenants (OMA, Bgee) without a `GRAPH{}` block per pattern.
2. **`SELECT DISTINCT` is NOT the fix.** It can absorb inflation and hand you the right
   number for the wrong reason, then break when the multiplicity changes.
3. **Check a predicate is native:** bind the subject and run
   `SELECT ?g WHERE { GRAPH ?g { <subj> <pred> ?o } }`. >1 graph → re-declared.
   Nothing from your database's graph → it was never yours.
4. **Joins multiply.** *k* re-declared patterns → **2^k** rows per entity.
5. **Single-tenant ≠ safe.** The trap is graphs, not databases (see ENDPOINTS).
6. **The pin is not ground truth.** If pinned ≠ unpinned, that gap is a **finding to
   explain**, not a number to adopt. `dataset/microbedbjp` re-declares NCBI Taxonomy at
   an **older nomenclature vintage** (Proteobacteria *and* Pseudomonadota), and
   "Superkingdom Bacteria" survives **only** there — the authoritative graph has an empty
   rank IRI since NCBI retired "superkingdom". Blind pinning turns correct answers wrong.
7. **Normalize literals with `STR(?label)`.** Some labels exist twice — plain and
   `xsd:string`. Distinct RDF terms, so `DISTINCT` won't collapse them and `GROUP BY`
   splits the group (`GO_0005183`, `CHEBI:29108`). Scan every quoted literal against the
   MIE's `critical_warnings`; `VALUES` blocks are the worst spot.
8. **Never write a `VALUES` block you did not populate from a query you ran.** An
   **empty** one is *valid SPARQL* — it returns one row of `0` instead of erroring. An
   abridged one ("representative", "…") computes a well-shaped number from the wrong set.
9. **Anchor on stable IDs, never an export-local IRI.** Ask: *does any component encode a
   release, a build, an export file, or a counter?* A Reactome BioPAX IRI
   (`.../biopax/95/48887#Pathway2258`) encodes **three**, all re-minted quarterly; the old
   one now has zero triples. Passing today proves nothing — the defect is invisible until
   the next release.

   ```sparql
   ?pathway bp:xref [ bp:db "Reactome"^^xsd:string ; bp:id "R-HSA-196807"^^xsd:string ] .
   ```

   The `^^xsd:string` is mandatory — without it the join silently returns 0.

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