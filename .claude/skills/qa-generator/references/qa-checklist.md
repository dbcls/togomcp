# QA self-review checklist (C01–C29)

Run this as Phase 8 on every candidate, in the voice of a strict reviewer trying to *reject* it. A CRITICAL or MAJOR finding must be fixed before the checkpoint — never present a question you know trips one. Output a verdict: `PASS` | `MINOR` | `MAJOR`, with the triggered codes. This file is the canonical wording for the checks.

## 🔴 CRITICAL — fix before presenting

- **C01 Circular logic** — Is `ideal_answer` only obtainable by re-running the exact exploration query that built the question? Self-fulfilling questions are invalid.
- **C02 Coverage gap (scope)** — For "which/how many/list all/yes-no/summary": does the SPARQL cover **all** discovered terms/entities, or only a sampled subset? Question scope must equal query scope.
- **C03 Arithmetic verification** — Every `GROUP BY`/categorical count needs a `COUNT(DISTINCT)` verification query. `sum == total` (or `sum > total` with overlap explained in `ideal_answer`). Missing verification = fail.
- **C04 Vocabulary sampling** — Were GO/MONDO/ChEBI/MeSH/EC terms (and their `getDescendants()`) discovered but only *some* placed in `VALUES`? Use all of them.
- **C05 Unverified filter heuristic** — Entities filtered by taxonomy-ID ranges / name patterns / eyeballing without a `(before) = (filtered) + (remaining)` count check.
- **C06 Reverse engineering** — Question scope ("SLE-associated genes") broader than what was actually queried (one of several).
- **C22 Literature-recoverable** — Could PubMed + abstracts fully answer it? Then `rdf_necessity` must be ≥2; flag if 0–1.
- **C23 Biological insight = 0/1** — Mere inventory of database contents with no mechanistic/functional/evolutionary insight.
- **C29 MIE contradiction (named-check)** — For **every predicate** in every stored query, and for **every fix** the query applies, confirm against that database's MIE that you are not doing something it explicitly documents as wrong. Two failure modes, both CRITICAL:
  1. **Foreign predicate** — the predicate is listed in `co_hosted_graphs` / `critical_warnings` as supplied by a *co-tenant graph* rather than the database itself. It resolves for the subset that graph covers and returns **nothing** for the rest, so the query silently answers a smaller question. *This is exactly what broke Q076*: it used `dcterms:identifier` on a UniProt protein, which `uniprot.yaml` had already documented — before the question was written — as OMA-supplied, with ZERO occurrences in the uniprot graph.
  2. **Warned-against fix** — the query applies a correction the MIE explicitly flags, or omits one it mandates (e.g. `COUNT(DISTINCT)` where the MIE says DISTINCT does not remove that particular duplication).

  **Reading the MIE once at Phase 1 does not discharge this check.** Q076's author called `get_MIE_file('uniprot')` and still shipped the trap; the knowledge was present and unread at the moment the predicate was typed. So do it as a *named* pass, per predicate, with the MIE open — not as a recollection. Verdict must name each predicate checked. If the MIE and the endpoint disagree, **the endpoint wins** — but then fix the MIE in the same session and say so, rather than silently working around it.

- **C28 Volatile anchor** — Does any stored query hardcode an entity IRI that encodes a release, build, export file, or load-order counter? Such an IRI is an address, not an identifier: it is re-minted upstream on every rebuild and the stale one then matches nothing and returns **0 rows silently**. A Reactome BioPAX subject (`.../biopax/95/48887#Pathway312` — release, export-file and element counters, all volatile) is an automatic CRITICAL; anchor on the stable-ID xref instead (`bp:xref [ bp:db "Reactome"^^xsd:string ; bp:id "R-HSA-…"^^xsd:string ]`, `^^xsd:string` mandatory). The check generalises beyond Reactome: for every hardcoded IRI, ask whether a stable accession exists and anchor on that. Keeping the volatile IRI in `rdf_triples` for orientation is fine if marked never-carry-forward. Passing today proves nothing — this defect is invisible until the next upstream release. (Hard Rule 5.)

- **C27 Cross-graph inflation** — If the answering endpoint hosts **more than one named graph** (`get_graph_list()` — NOT `get_sparql_endpoints()`; the trigger is graphs-per-endpoint, and the old databases-per-endpoint wording wrongly exempted single-database endpoints like `togovar`, which re-types 2.9M variant IRIs across its own two graphs, and `glycosmos`/`pdb`/`ddbj`/`pubchem`, which host 43–150 graphs each), the recorded count / result_count / GROUP BY was verified equal under (a) endpoint-default and (b) target-graph-pinned execution, OR it uses `COUNT(DISTINCT ?entity)` with a Phase-5 provenance probe recorded, and the stored query pins the target graph(s). A bare `COUNT` / `result_count` from a union endpoint with no scope check is an automatic MAJOR — CRITICAL when the type is `list`/`factoid`/`choice` (the number IS the answer). Absence of a MIE warning does not waive this check. **`COUNT(DISTINCT)` is not a universal fix** — it only collapses duplicates that share an IRI. It does NOT remove rows from a graph holding *different* IRIs (UniProt's 14,432 deleted entries survive DISTINCT; only a pin or `FILTER NOT EXISTS { ?p up:obsolete 1 }` drops them), and it does NOT help at all against **scope bleed**, where a co-tenant declares your class over its own disjoint IRIs and silently adds foreign entities — every row unique and well-formed (`?e a dsmz:Enzyme` returns 627,832 of which only 8.7% are BRENDA's; MediaDive's culture media ×15.5). Only the graph pin fixes that. Establish which kind you have. (Hard Rule 4; Phase 5 provenance probe.)

## 🟠 MAJOR — fix before presenting

- **C07 Famous entity** — BRCA1, TP53, insulin, aspirin, glycolysis, E. coli K-12, or similar canonical examples (see [coverage-gaps.md](coverage-gaps.md)).
- **C08 Wrong type** — `type` label doesn't match the actual structure (see schema's type↔structure table).
- **C09 Type distribution** — Type over the balanced cap (≈ total/5 + 2), or created while another type is under-represented.
- **C10 Structured-vocab skipped** — `bif:contains`/free-text used where a GO/MONDO/ChEBI/EC/MeSH IRI exists, with no note explaining why no IRI was available.
- **C11 Descendants not fetched** — Ontology term found but `getDescendants()` not called / descendants not included.
- **C12 PubMed test invalid** — The test only confirmed the topic exists; it must attempt and fail to retrieve the *specific* answer.
- **C13 Single database** — Only one DB in `togomcp_databases_used` without documented justification.
- **C14 Database post-selection** — DBs chosen because results showed up during exploration, not pre-planned for complementarity.
- **C15 `exact_answer` format** — Wrong shape for the type (see schema).
- **C16 SPARQL fields** — A `sparql_queries` entry missing `query_number`/`database`/`description`/`query`/`result_count`.
- **C19 Inventory question** — Asks about database structure/metadata ("how many entries does UniProt have…") rather than biology.
- **C21 Unbounded scope** — `list`/`summary` not 5–100 members and no stated top-N justification.
- **C26 Structural near-duplicate** — Does this question share its *structure* with an existing one, even under a different keyword? Before presenting, scan the existing questions that share this candidate's `type` and database set, and compare the **query pattern / predicate path / `question_template_used`**, not just the topic. The recurring real failure is "proteins annotated with X → their Rhea reactions" or "pathway enzymes that are ChEMBL drug targets" reused with a new keyword. If a structural twin exists, either change the query shape (different predicate path, different aggregation axis, different databases) or state explicitly in the file how this question differs. The full `verify_questions.py` run flags identical `(type, databases, template)` signatures and duplicate keywords mechanically — this check catches the same-shape/different-words cases a signature can't.

## 🟡 MINOR — fix or note

- **C17 RDF triple comments** — A triple without its `# Database: X | Query: N | Comment: ...` annotation.
- **C18 Vague wording** — `body` uses bind/contain/have/associated-with/interact-with without a qualifier.
- **C20 Undocumented overlap** — `sum > total` not explained in `ideal_answer`.
- **C24 Keyword-workflow inversion** — The type feels force-fitted to the keyword (keyword chosen before type/DB).
- **C25 UniProt cap** — UniProt usage pushed past 70% of the set.
