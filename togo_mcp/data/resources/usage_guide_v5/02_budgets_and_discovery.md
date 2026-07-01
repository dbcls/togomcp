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