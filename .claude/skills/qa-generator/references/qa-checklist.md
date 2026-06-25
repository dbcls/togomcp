# QA self-review checklist (C01–C25)

Run this as Phase 8 on every candidate, in the voice of a strict reviewer trying to *reject* it. A CRITICAL or MAJOR finding must be fixed before the checkpoint — never present a question you know trips one. Output a verdict: `PASS` | `MINOR` | `MAJOR`, with the triggered codes. (Canonical wording: `benchmark/togomcp_qa_prompt.md`.)

## 🔴 CRITICAL — fix before presenting

- **C01 Circular logic** — Is `ideal_answer` only obtainable by re-running the exact exploration query that built the question? Self-fulfilling questions are invalid.
- **C02 Coverage gap (scope)** — For "which/how many/list all/yes-no/summary": does the SPARQL cover **all** discovered terms/entities, or only a sampled subset? Question scope must equal query scope.
- **C03 Arithmetic verification** — Every `GROUP BY`/categorical count needs a `COUNT(DISTINCT)` verification query. `sum == total` (or `sum > total` with overlap explained in `ideal_answer`). Missing verification = fail.
- **C04 Vocabulary sampling** — Were GO/MONDO/ChEBI/MeSH/EC terms (and their `getDescendants()`) discovered but only *some* placed in `VALUES`? Use all of them.
- **C05 Unverified filter heuristic** — Entities filtered by taxonomy-ID ranges / name patterns / eyeballing without a `(before) = (filtered) + (remaining)` count check.
- **C06 Reverse engineering** — Question scope ("SLE-associated genes") broader than what was actually queried (one of several).
- **C22 Literature-recoverable** — Could PubMed + abstracts fully answer it? Then `rdf_necessity` must be ≥2; flag if 0–1.
- **C23 Biological insight = 0/1** — Mere inventory of database contents with no mechanistic/functional/evolutionary insight.

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

## 🟡 MINOR — fix or note

- **C17 RDF triple comments** — A triple without its `# Database: X | Query: N | Comment: ...` annotation.
- **C18 Vague wording** — `body` uses bind/contain/have/associated-with/interact-with without a qualifier.
- **C20 Undocumented overlap** — `sum > total` not explained in `ideal_answer`.
- **C24 Keyword-workflow inversion** — The type feels force-fitted to the keyword (keyword chosen before type/DB).
- **C25 UniProt cap** — UniProt usage pushed past 70% of the set.
