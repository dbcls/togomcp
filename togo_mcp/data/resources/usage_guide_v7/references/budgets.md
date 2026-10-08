> Usage Guide reference file — fetched on demand with `get_workflow(name="usage-guide", path="references/budgets.md")`. The always-loaded core is `TogoMCP_Usage_Guide()`.

## 🎯 EMPIRICAL BUDGETS — TOOL TIERS AND PROVENANCE

The budget table itself is in the core guide.

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
