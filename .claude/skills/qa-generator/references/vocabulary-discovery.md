# Structured vocabulary discovery (Phase 3)

Resolve every biological concept in the question to a **structured identifier** before writing SPARQL. Free-text matching (`bif:contains`, `regex`, `CONTAINS`) is the last resort and must be justified in the file (C10). This is what makes a question reproducible and its `VALUES` clause exhaustive.

## Resolution hierarchy (try in order)

1. **Ontology IRI** (GO, MONDO, ChEBI, UBERON) via OLS4
2. **Typed predicate** in the database's MIE file
3. **Classification code** (EC number, taxon ID)
4. **Graph navigation** (follow cross-references)
5. **Text search** — last resort only

## Concept → tool map

| Concept | Source | Tool | Example |
|---|---|---|---|
| Molecular function | GO | `OLS4:searchClasses(ontologyId=go)` | "kinase activity" → GO:0016301 |
| Biological process | GO | `OLS4:searchClasses(ontologyId=go)` | "apoptosis" → GO:0006915 |
| Cellular component | GO | `OLS4:searchClasses(ontologyId=go)` | "nucleus" → GO:0005634 |
| Enzyme | EC, GO | `search_rhea_entity`, `OLS4` | "nitrogenase" → EC 1.18.6.1 |
| Disease | MONDO, MeSH | `OLS4:searchClasses(ontologyId=mondo)`, `search_mesh_descriptor` | "Noonan syndrome" → MONDO:0018955 |
| Chemical / drug | ChEBI, ChEMBL | `OLS4:searchClasses(ontologyId=chebi)`, `search_chembl_molecule` | "aspirin" → CHEBI:15365 |
| Pathway | Reactome, GO | `search_reactome_entity` | "glycolysis" → R-HSA-70171 |
| Anatomy | UBERON | `OLS4:searchClasses(ontologyId=uberon)` | "heart" → UBERON:0000948 |
| Organism | NCBI Taxonomy | `ncbi_esearch(db=taxonomy)` / TogoID | "E. coli" → taxon:562 |

## Mandatory checkpoint (record in the question file)

For every ontology term used:
1. Call `OLS4:getDescendants()` (and `getAncestors()` if you need the right level).
2. Put **all** discovered terms — parent + every descendant — in the SPARQL `VALUES` clause. Using a subset is **C04 (vocabulary sampling)** and silently undercounts.
3. Document it, e.g. as a comment block in the YAML:
   ```
   # STRUCTURED VOCABULARY DISCOVERY — DESCENDANTS CHECKED (OLS4:getDescendants)
   # GO:0030187 (melatonin biosynthetic process): 0 descendants — leaf, comprehensive
   # GO:0004059 (aralkylamine N-acetyltransferase activity): 0 descendants
   ```

If a concept genuinely has no structured IRI (rare), say so explicitly in the file and only then fall back to a justified text search.
