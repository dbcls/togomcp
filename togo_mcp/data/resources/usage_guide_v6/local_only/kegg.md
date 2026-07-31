## 🧬 KEGG (available in this session)

The `kegg_*` tools are mounted, so KEGG is usable here. It is NOT an RDF Portal database: no SPARQL endpoint, no MIE, and `database="kegg"` is invalid on `run_sparql`.

- **What it uniquely adds.** A pathway map as a SIGNED DIRECTED GRAPH (activation vs inhibition per edge, from KGML relation subtypes), the FEEDBACK LOOPS that graph contains, and, for an organism map, the metabolic steps that organism LACKS. Reactome RDF has no equivalent of any of these, so they are not reproducible with `run_sparql`.
- **Workflow.** `kegg_find` (keyword → entry IDs) → `kegg_get_entry` (full record incl. DBLINKS), `kegg_link` (gene↔pathway↔compound↔pubmed), `kegg_pathway_graph` (whole map), `kegg_pathway_neighborhood` (up/downstream of one gene), `kegg_pathway_paths` (how A reaches B, and the net sign of each route), `kegg_pathway_cycles` (negative/positive feedback loops).
- **Reading signs.** Every graph tool returns `signal_quality.signed_edge_fraction` — how much of that map states a direction of regulation at all. It ranges from 0.98 to 0.40 across signaling maps and is 0 for metabolic ones, because most KGML relations record only a MECHANISM (phosphorylation, binding). Read a `net_sign` of 0, or an `unsigned` feedback loop, as UNKNOWN — never as "no effect".
- **Organism vs reference maps.** For "which genes are in this pathway" use the ORGANISM map (`hsa04151`, `eco00010`), not the `ko`/`map` reference map. On a METABOLIC map, `kegg_pathway_paths` needs a larger `max_length`: compounds are joined through their enzyme, so the hop count is about double the reaction count.
- **Bridging to RDF Portal — REQUIRED.** KEGG-namespaced IDs (`hsa:10458`, `cpd:C00031`, `path:hsa04151`) do NOT resolve in any SPARQL database. Convert them with `kegg_conv` FIRST: genes ↔ `uniprot` / `ncbi-geneid` / `ncbi-proteinid`, chemicals ↔ `chebi` / `pubchem`. Only the converted identifiers belong in a `run_sparql` query or a TogoID call.
- **Rate limit.** KEGG allows 3 requests/second and blocks abusers. An HTTP 403/429 from a `kegg_*` tool means that cap or an access restriction was hit — do NOT retry it.

