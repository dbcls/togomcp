## ⚠️ KNOWN-HARD QUERIES

| Pattern | Fallback |
|---------|----------|
| Top-N genes by ClinVar variant count | `ncbi_esearch [Gene Name]` + `ncbi_esummary`; caveat RDF snapshot divergence. |
| Specialist DB counts (GlyCosmos, AMR Portal) | One SPARQL attempt → synthesize; note approximation. |
| Human metalloprotease targets + structure counts | `togoid_convertId uniprot→pdb`; report counts separately. |
| Rhea reactions filtered by UniProt keyword | Read UniProt MIE for keyword IRI (`up:classifiedWith`); EC-prefix fallback overcounts. |
| Bacterial gene counts via NCBI | Field tags mandatory: `"Archaea[Organism] AND nifH[Gene Name]"` — omitting loses 70–80%. |
| Full predicate/ontology coverage across many graphs | `COUNT`-first probing per graph (BULK MODE), not one cross-graph query |

---

## ✍️ OUTPUT QUALITY

- Each fact exactly once.
- No meta-commentary ("Based on my analysis", "In summary", "As established above").
- No reasoning leakage in the final answer.
- Prose **or** list — not both.
- Partial data: state what was found and what wasn't. No padding.

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Missed EXPLORATION trigger | Return to GATE 0. Re-classify. If NO, write Seed Definition now. |
| Stuck on one DB (≥4 calls in EXPLORATION) | Pivot to the next unexplored DB from your entity→DB map. UniProt annotations don't substitute for direct Rhea/Taxonomy/ChEMBL/PubChem calls. |
| 3rd consecutive SPARQL | Stop. Pivot to search / NCBI / TogoID / partial synthesis. |
| Cross-DB SPARQL fails | Check endpoints; use TogoID or NCBI bridge. |
| Empty SPARQL results | **Read the `#` diagnosis block `run_sparql` prepends** — it names the two causes and the probe. Not an endpoint failure. Then: structured predicates from MIE; extract IRIs via search first. Typed literal missing (`^^xsd:string`)? Predicate applied to the wrong node? |
| Aggregate came back `0` | Same thing in aggregate form — `COUNT` over an empty match is one row of `0`, so it *looks* structurally fine. The diagnosis block fires here too; decide true-negative vs broken-pattern before reporting a zero. |
| `REGEX` filter returns nothing (pattern uses `A\|B` or `{n,m}`) | Two-arg `REGEX()` mishandles alternation and brace quantifiers on **every** endpoint. Always pass a third argument: `REGEX(?x, "A\|B", "")`. See SILENT-FAILURE TRAPS #10. |
| Cross-DB join through a TogoID relation graph returns 0 | The two graphs mint **different IRIs for the same entity**. A relation graph uses TogoID's canonical form per dataset — often, but **not always**, `identifiers.org/` — not the source DB's own form (`chembl` mints `rdf.ebi.ac.uk/resource/chembl/molecule/…`, the relation graph holds `identifiers.org/chembl.compound/…`). Probe one row of the relation graph for both IRI forms before joining. Indistinguishable from a true negative on a sparse DB. See SILENT-FAILURE TRAPS #11. |
| SPARQL timeout | Add LIMIT; replace `bif:contains` with structured IRIs. |
| Wrong count | Master reactions only? Correct keyword IRI (not EC prefix)? |
| **Count inflated** (2×, 4×, 8×) — or right but unproven | Co-tenancy. `GRAPH ?g` the pattern with its subject bound: >1 graph → re-declared; none of yours → foreign predicate, i.e. a silent intersection. Pin **every** pattern. `DISTINCT` hides it, doesn't fix it. |
| Pinned ≠ unpinned | A **finding**, not a number to pick — the pin can drop legitimate rows (microbedbjp's legacy-vintage taxonomy). Diagnose before adopting either. |
| Query returned 0 after months of working | Release-pinned IRI rotted (Reactome BioPAX). Re-anchor on a stable ID + `^^xsd:string`. |
| Aggregate returns a suspicious 0 or round number | Empty/abridged `VALUES` block — valid SPARQL, wrong answer. Repopulate from a live query. |
| TogoID empty | Check ID format with `togoid_getDataset(src)`. |
| ≥15 tool calls, no answer | Synthesize from partial data. Partial + honest > wrong + exhaustive. |
| Repetitive answer | Remove any sentence restating an earlier point. |
| OLS4 / PubMed unavailable | → `search_mesh_descriptor` / `ncbi_esearch`. |
| **A tool named in this guide is absent from your tool list** (canaries: `togovar_search_variant`, `search_chembl_id_lookup`) — or a tool you call returns "unknown tool" (`find_databases`, `ncbi_ncbi_esearch`) | Your MCP client cached the tool list when the connector was added and has not refetched it. **Tell the user in your answer**: remove and re-add the TogoMCP connector. Common with ChatGPT connectors — some are running lists months stale. Do not retry the missing name or invent a substitute. **Databases are unaffected**: the catalog in this guide is served live, so any database key listed there works even when your cached tool schema does not name it. |
