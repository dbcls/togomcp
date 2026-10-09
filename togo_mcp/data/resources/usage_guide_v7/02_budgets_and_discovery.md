## 🎯 EMPIRICAL BUDGETS

| Metric             | Optimal    | Red flag |
|--------------------|------------|----------|
| Total tool calls   | 4–10       | 21+      |
| Total SPARQL calls | 1–3        | 7+       |
| Consecutive SPARQL | 1–2        | 3+       |

Score peaks at ≤10 tool calls and 1–3 SPARQL, then declines steadily (21+ calls ≈ −2.5 pts vs
the sweet spot; ≥3 **consecutive** run_sparql ≈ **−1.1** vs ≤2). With STEP 0 now a no-tool catalog
scan, a compliant flow is typically MIE + 1–3 SPARQL (+ one grounding search) — aim low.

If `OLS:*` or `PubMed:*` unavailable, substitute `search_mesh_descriptor` / `ncbi_esearch`.
(Tool tiers and the provenance of these numbers: reference file `budgets.md`.)

---

## 🔍 STEP 0: DATABASE DISCOVERY

**No tool call.** The **DATABASE CATALOG** (below) lists every database with what it holds — it
is already in this guide, so scan it directly. Match the KIND of data you need (not an entity
name) against the catalog, pick 1–3 candidate databases, then go straight to STEP 2
(`get_MIE_file`). The full roster of `database=` keys is also on the `run_sparql` /
`get_MIE_file` schema, so you never need a tool to learn what exists.

Only if two or three candidates still look alike after reading their catalog lines, fetch the
long form (full descriptions + all keywords): reference file `database-catalog.md`.

---

## 📄 MIE FILES — ALWAYS BEFORE SPARQL

Call `get_MIE_file(database)` before any `run_sparql`. Read in this order:

1. **`global_gotchas`** — database-wide filters and IRI traps. The #1 cause of silent failures.
2. **`graphs.co_hosted`** — which sibling graphs re-declare which predicates, and by
   what multiplier. Read this BEFORE writing a join; it is the only field that
   describes what your query does *not* say. The response's trap banner summarizes 1–2.
3. **`examples`** — the load-bearing section. Each carries a live-verified `sparql`
   (with its PREFIXes — copy them verbatim), an `intent`/`question` to match against
   your task, what it `teaches`, and the `traps_avoided` that query already handles.
   Pick the closest one and adapt it; do not write from scratch.
4. **`traps_avoided`** on the example you chose — the per-query counterpart to
   `global_gotchas`. Re-read it as you edit, especially if results come back empty.
5. **`schema_delta`** — only the predicates no example already demonstrates. Reach
   here when adapting an example is not enough, not as a starting point.
6. **`id_join_map`** — stable ID anchors and cross-database join paths.

**Re-consult per predicate, not once per database.** Reading the MIE at the start of a
task is not enough — the failures come from one predicate inside an otherwise fine
query. For each predicate you write, check it is not flagged as foreign or re-declared.

**The MIE describes; the ENDPOINT decides.** An MIE can be stale or wrong — `uniprot.yaml`
prescribed a fix that silently included 14,432 deleted entries until 2026-07. If a live
count contradicts the MIE, the endpoint wins: report the contradiction, don't reconcile
it silently.

**Predicate hierarchy** (fastest → slowest): specific IRI → `VALUES` → typed predicate →
graph navigation → `bif:contains` → `FILTER(CONTAINS())`.

---

## 🔌 ENDPOINTS

Most endpoints are **shared**. Everything on one row is read by the same unpinned
query whether you meant it or not — see 🕸️ CO-TENANCY under SPARQL DISCIPLINE.

Values below are the exact `database=` keys — copy them verbatim; `endpoint_name`
is the bold row label.

| Endpoint | n | `database` keys |
|---|---:|---|
| **primary** | 20 | `mesh` `go` `taxonomy` `mondo` `nando` `bacdive` `mediadive` `brenda` `hgnc` `jpostdb` `massbank` `nbrc` `mogplus` `hco` `mco` `ontology` `fantabio` `pubcasefinder` `jogo` `tismed` |
| **ebi** | 6 | `chembl` `chebi` `reactome` `ensembl` `amrportal` `gwascatalog` |
| **ncbi** | 5 | `clinvar` `pubmed` `pubtator` `ncbigene` `medgen` |
| **sib** | 4 | `uniprot` `rhea` `bgee` **`oma`** |
| **pubchem** | 1 | `pubchem` |
| **pdb** | 1 | `pdb` |
| **ddbj** | 1 | `ddbj` |
| **glycosmos** | 1 | `glycosmos` |
| **nims** | 1 | `supercon` ← key ≠ endpoint name |
| **togovar** | 1 | `togovar` |
| **wikipathways** | 1 | `wikipathways` |
| **idsm** | 1 | `idsm` |
| **lipidmaps** | 1 | `lipidmaps` |
| **swisslipids** | 1 | `swisslipids` |
| **microbes** | 1 | `bh26microbes` ← key ≠ endpoint name; experimental (QLever) |
| **marpolbase** | 1 | `marpolbase` ← Marchantia polymorpha genome; own endpoint, 7 graphs, 10k row cap, no `SERVICE` |

**One database ≠ one graph.** A database alone on its endpoint still serves many graphs
(GlyCosmos ~150, PubChem 68, PDB 46, DDBJ 43, IDSM 39), so co-tenancy is a property of
**graphs**, not of this table. `lipidmaps` declares **no named graphs at all**: every
`GRAPH`/`FROM` pin returns 0 rows there.

Same endpoint → single SPARQL. Different endpoints → `togoid_convertId` or NCBI
cross-reference. This table is copied from `endpoints.csv` and drifts;
`get_sparql_endpoints()` is authoritative — call it when planning a bridge, or when a
count looks inflated (it hurt scores when called routinely: 16.73 vs. 17.59 without).

Before writing a `SERVICE` federation query, or on an **HTTP 403 / HTML reply** from an
endpoint outside RDF Portal (`lipidmaps`: put a space before the paren — `SUBSTR (?s, 33, 2)`),
fetch reference file `endpoints.md`: federation works only from a few verified callers.

---

## 🔗 TogoID — PLAN EARLY

Late TogoID use (>50% into the sequence) correlates with worse scores.

```
0. togoid_identifyId(ids)          bare accession → dataset key — DON'T GUESS
1. togoid_getAllRelation()         discover available routes — call EARLY
2. togoid_countId(src, tgt, ids)   validate before bulk conversion
3. togoid_convertId(ids, route)    returns [source_id, target_id] pairs
```

Common routes: `ncbigene → uniprot` · `uniprot → pdb` · `uniprot → chembl_target` ·
`ncbigene → ensembl_gene`. Multi-hop OK (`ncbigene → uniprot → pdb`). If empty, check
ID format with `togoid_getDataset(src)`.

**Never invent a dataset key.** `ncbi_protein`, `entrez_gene` and `uniprotkb` are not
TogoID keys and every call using one fails. GenBank/ENA/DDBJ **protein** accessions
(`AEK21611`) are `insdc_cds`, NOT `ncbi_protein`; NCBI Gene IDs are `ncbigene`. Given a
bare accession, call `togoid_identifyId` — it returns candidate keys ordered
most-specific-first, narrowable with `category=`. When the shape cannot decide (a bare
number fits a dozen datasets), `verify=True` marks which datasets actually hold the ID
(`attested`: yes/ambiguous/no) — slow, ≤10 IDs per call.

`getRelation` direction is not a constraint: TogoID registers most pairs one way only, but
conversion traverses both. A result tagged `registered_direction: target-source` still
converts in the direction you asked for. When NO direct pair exists, the error from
`getRelation`/`countId`/`convertId` lists multi-hop routes that work — use one as `route=`.
A route flagged `via taxonomy`/`go`/a pathway links a whole group, not equivalent IDs.

Skip when: both DBs share an endpoint, or `ncbi_esearch` already cross-references the IDs.