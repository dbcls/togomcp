## 🎯 EMPIRICAL BUDGETS

| Metric             | Optimal    | Red flag |
|--------------------|------------|----------|
| Total tool calls   | 4–10       | 21+      |
| Total SPARQL calls | 1–3        | 7+       |
| Consecutive SPARQL | 1–2        | 3+       |

Score peaks at ≤10 tool calls and 1–3 SPARQL, then declines steadily (21+ calls ≈ −2.5 pts vs
the sweet spot; ≥3 **consecutive** run_sparql ≈ **−1.1** vs ≤2). With STEP 0 now a no-tool catalog
scan, a compliant flow is typically MIE + 1–3 SPARQL (+ one grounding search) — aim low.

**Tool tiers** (mean answer score when the tool appears, ≥5 uses):
- **Tier 1 (≥17.5):** `search_mesh_descriptor` · `get_compound_attributes_from_pubchem` · `search_chembl_target` · `OLS:search` · `get_pubchem_compound_id`
- **Tier 2 (17.0–17.5):** `run_sparql` · `togoid_getAllRelation` · `ncbi_esearch` · `search_chembl_molecule`
- **Tier 3 (<17.0):** `search_rhea_entity` · `ncbi_esummary` · `search_reactome_entity` · `search_uniprot_entity` · `togoid_convertId`

Tiers rank by the *questions* a tool tends to appear on as much as the tool itself — treat as a
soft prior, not a ban. If `OLS:*` or `PubMed:*` unavailable, substitute `search_mesh_descriptor` /
`ncbi_esearch`. Use `togoid_getAllRelation` for discovery; `togoid_getRelation` only to confirm a
known route.

> Budgets + tiers derived from the v3 equivalence run (100 questions × 3, 2026-07, refusal cells
> excluded, n=282). Directions are stable across models; the exact cut-points are a guide, not a gate.

---

## 🔍 STEP 0: DATABASE DISCOVERY

**No tool call.** The **DATABASE CATALOG** (next section) lists every database with what it holds,
grouped by category — it is already in this guide, so scan it directly. Match the KIND of data you
need (not an entity name) against the catalog, pick 1–3 candidate databases, then go straight to
STEP 2 (`get_MIE_file`). The full roster of `database=` keys is also on the `run_sparql` /
`get_MIE_file` schema, so you never need a tool to learn what exists.

The catalog's "By category" index is the controlled taxonomy (`protein`, `gene`, `variant`,
`compound`, `drug_target`, `pathway`, `reaction`, `ontology`, `structure`, `literature`,
`taxonomy`, `disease`, `materials`, `physics`, …); quick hints and per-database keywords are there too.

---

## 📄 MIE FILES — ALWAYS BEFORE SPARQL

Call `get_MIE_file(database)` before any `run_sparql`. Read in this order:

1. **`critical_warnings`** — mandatory filters and IRI traps. The #1 cause of silent failures.
2. **`co_hosted_graphs`** — which sibling graphs re-declare which predicates, and by
   what multiplier. Read this BEFORE writing a join; it is the only field that
   describes what your query does *not* say. The response's trap banner summarizes 1–2.
3. **`shape_expressions`** — use structured predicates over text search (10–100× faster).
4. **PREFIX declarations** — copy verbatim.
5. **`sparql_query_examples`** — modify a working scaffold; don't write from scratch.
6. **`anti_patterns`** — if results are empty or wrong.

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
| **primary** | 16 | `mesh` `go` `taxonomy` `mondo` `nando` `bacdive` `mediadive` `brenda` `hgnc` `jpostdb` `massbank` `nbrc` `mogplus` `hco` `mco` `ontology` |
| **ebi** | 5 | `chembl` `chebi` `reactome` `ensembl` `amrportal` |
| **ncbi** | 5 | `clinvar` `pubmed` `pubtator` `ncbigene` `medgen` |
| **sib** | 4 | `uniprot` `rhea` `bgee` **`oma`** |
| **pubchem** | 1 | `pubchem` |
| **pdb** | 1 | `pdb` |
| **ddbj** | 1 | `ddbj` |
| **glycosmos** | 1 | `glycosmos` |
| **nims** | 1 | `supercon` ← key ≠ endpoint name |
| **togovar** | 1 | `togovar` |

> **One database ≠ one graph.** GlyCosmos (~150 graphs), PubChem (68), PDB (46), DDBJ
> (43) and TogoVar serve many graphs from their *own* endpoint — TogoVar re-types 2.9M
> variant IRIs across two of its own. Co-tenancy is a property of **graphs**, not of this
> table. Only SuperCon (2) is near-single-graph.

Copied from `endpoints.csv` and it **drifts**: a database mounted beside yours silently
rewrites what your unpinned query means (OMA landed on `sib` 2026-04-28 and changed
answers written months earlier). `get_sparql_endpoints()` is authoritative.

Same endpoint → single SPARQL. Different endpoints → `togoid_convertId` or NCBI
cross-reference. Call `get_sparql_endpoints()` when planning a bridge, or when a
count looks inflated (it hurt scores when called routinely: 16.73 vs. 17.59 without).

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