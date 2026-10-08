## 📋 WORKFLOWS

**VERIFICATION** (1–2 SPARQL) — `GATE 0` → analyze → pick DB from the catalog → search/esearch
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

- **Before:** read `global_gotchas` + `graphs.co_hosted`, then pick the closest
  `examples` entry to adapt; ground with a search tool first.
- **While writing:** copy PREFIXes from the example you are adapting; **pin every
  graph** (see CO-TENANCY);
  `LIMIT 10` first; `VALUES` for batch lookups (≤15 items); one broad `GROUP BY` over
  many narrow queries.
- **On failure:** max 2 consecutive. At #3: pivot to search, `ncbi_esearch`, TogoID, or
  partial synthesis.
- **On an empty result:** `run_sparql` prefixes it with a `#` diagnosis block — read it.
  An empty result is **not** an endpoint failure, and it has two causes needing opposite
  answers: the data is genuinely absent (report that), or one triple pattern is wrong and
  the real answer is non-zero. The single `ASK` probe the block names **is** the pivot,
  not a third query — spend it rather than re-running a variant of the same SELECT.

---

## 🕸️ CO-TENANCY & SILENT-FAILURE TRAPS

Everything in this section fails **silently** — no error, no zero rows, no doubled
count. The result is plausible, correctly shaped, and wrong.

An unpinned query reads **every graph on the endpoint**, not just your database's. A
sibling graph that re-declares a predicate inflates counts; one that *supplies* a
predicate you assume is native narrows your query to an intersection (on `sib`,
`dcterms:identifier` comes only from the co-hosted OMA graph, so an unpinned UniProt
query silently becomes UniProt INTERSECT OMA).

The rules, one line each. The worked examples, the evidence and the probe queries are
in reference file `co-tenancy.md` — fetch it when a count looks inflated, a join
returns 0 unexpectedly, or pinned ≠ unpinned.

1. **Pin every pattern.** `FROM <g>` or `GRAPH <g> { ... }`; partial pinning still leaks.
   "Your database" may be *several* graphs (the MIE `graphs:` list) — pin the whole set
   (UniProt owns ~16: taxon names live in `.../taxonomy`, not `.../uniprot`).
2. **`SELECT DISTINCT` is NOT the fix.** It hides inflation and breaks when multiplicity changes.
3. **Check a predicate is native:** bind the subject and run
   `SELECT ?g WHERE { GRAPH ?g { <subj> <pred> ?o } }`. >1 graph → re-declared;
   none of yours → it was never yours.
4. **Joins multiply.** *k* re-declared patterns → **2^k** rows per entity.
5. **Single-tenant ≠ safe.** The trap is graphs, not databases (see ENDPOINTS).
6. **The pin is not ground truth.** If pinned ≠ unpinned, that gap is a **finding to
   explain**, not a number to adopt.
7. **Normalize literals with `STR(?label)`.** One predicate can carry mixed literal forms
   (plain, `^^xsd:string`, `@en`); an exact match on the wrong form returns 0 with no
   error. Scan every quoted literal against the MIE's `global_gotchas`; `VALUES` blocks
   are the worst spot.
8. **Never write a `VALUES` block you did not populate from a query you ran.** An empty
   one is valid SPARQL and returns one row of `0`.
9. **Anchor on stable IDs, never an export-local IRI** (one that encodes a release, a
   build or a counter — e.g. Reactome BioPAX IRIs, re-minted quarterly). Join on the
   accession with its datatype: `bp:id "R-HSA-196807"^^xsd:string`.
10. **Always pass a third argument to `REGEX()`** — `REGEX(?x, "A|B", "")`. The
    two-argument form silently returns 0 for alternation (`A|B`) and brace quantifiers
    (`{n,m}`) on every Virtuoso endpoint.
11. **The same entity carries different IRIs in different graphs.** A TogoID relation
    graph keys each side by TogoID's canonical form, often not the source database's own
    IRI, so the join returns 0 and reads as "no data". Probe one row of the relation
    graph for both IRI forms before joining.