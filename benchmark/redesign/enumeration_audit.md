# §4.4 Enumeration-route audit — all 36 databases

*The enforceable input to `MIE_v3_spec.md` §4.4 ("a positive route is not a caveat") and Phase-5
checklist item 8. Produced 2026-07-22 by a 4-way parallel read of every v2 `togo_mcp/data/mie/*.yaml`
(no live queries — documentation mining; the v2 counts were live-verified at their own authoring).
Purpose: when authoring each v3 file (redesign step 4), guarantee the DB's set-level enumeration
route — "give me **ALL** entities with property/class/feature X" — survives compression as a
first-class worked example, not as a caveat. This is the exact axis q066 regressed on.*

## Headline

**This is a compression-guard job, not a repair job.** For **34 of 36** DBs the *primary* set-level
enumeration route is **already** a first-class worked query in the v2 MIE (the two pilots, uniprot +
bacdive, already carry it in v3). §4.4's risk here is almost entirely **v3 compression dropping the
worked route while keeping its scary union-inflation / timeout caveat** — which reads to the agent as
"avoid this," the q066 failure. So the audit's job is to mark, per DB, *what must not be compressed
away*, ranked by exposure.

## Risk tiers (how to use this during step-4 authoring)

- **Tier A — route is already buried in v2** (only-caveat / only-sample / only inside a composite
  query). These are latent q066s *today*; the v3 file must promote them to a standalone
  `enum_*` example. **4 DBs.**
- **Tier B — thin margin**: the enumeration axis is carried by exactly one worked example with no
  fallback hierarchy, or the route reads like xref/navigation a compressor is prone to drop. Keep the
  specific worked query, never just the predicate in a schema list. **6 DBs.**
- **Tier C — route + caveat are inseparable**: the route works only when a load-bearing caveat rides
  with it (graph-pin, anchor-or-503, use-REST, avoid-`+`-path). Author the example and its trap as
  one unit. **5 DBs** (overlaps A/B).
- **OK** — first-class and robust; author normally.

## Per-DB table

| db | enumeration route (predicate) | v2 status | tier | guard note |
|---|---|---|---|---|
| **uniprot** | `up:classifiedWith keywords:NNN` | ✅ v3 `keyword_enum` | done | the q066 fix; the reference pattern |
| **bacdive** | controlled phenotype value (OxygenTolerance…) | ✅ v3 `oxygen_tolerance` | done | reference pattern |
| ddbj | `nuc:division` (21-val); **higher-clade `rdfs:subClassOf*` in `ontology/taxonomy`** | division first-class; **subtree only-caveat** | **A** | promote the taxonomy-subtree route to a worked example |
| glycosmos | disease/CAZy/GO; **reverse GO & reverse HPA-tissue** | primary first-class; **reverse routes only inside composite VALUES** | **A** | add standalone "all genes with GO term X / High in tissue X" |
| pubchem | FDA-role IRI + assay-outcome (first-class); **ChEBI/ontology-class membership** | primary first-class; **class-enum only-caveat (timeout)** | **A/C** | class-enum route + its aggregation-timeout caveat as one unit |
| mogplus | `overlaps_gene <ENSMUSG>` (first-class); **`vep:consequence`/`snpeff:` = `SO_*`** | gene-overlap first-class; **SO route only in anti_pattern** | **A/C** | promote SO-consequence example; keep "must anchor or 503" caveat |
| medgen | `mo:sty <STY IRI>` (UMLS semantic type) | first-class, **single example** | **B** | only set-level axis (`mo:isa` covers 44 concepts) — protect the one query |
| mediadive | `schema:belongsTaxGroup` (6-val) | first-class, **single example** | **B** | thin margin — keep the worked query |
| hgnc | `rdfs:seeAlso ?ref . ?ref a idt:<type>` | first-class | **B** | reads like xref-nav; compressor-prone. No functional hierarchy exists |
| chebi | `rdfs:subClassOf+` **and** `has_role` (RO_0000087 restriction) | first-class (both) | **B** | textbook §4.4 case; caveats survive alone → protect the routes |
| clinvar | significance value (`cvo:description "Pathogenic"`), variation_type | first-class | **B** | 3 classification branches + bnode-inflation caveat must accompany |
| ensembl | `terms:has_biotype` / `has_transcript_flag` (glossary IRIs) | first-class | **B/C** | must pin GRAPH (grch37/expressionatlas 3× inflation) |
| taxonomy | `tax:rank` IRI **and** `rdfs:subClassOf`(+/*) subtree | first-class (core axis) | **C** | MUST pin `ontology/taxonomy`; `tax:Superkingdom` IRI does not exist |
| togovar | SO consequence / SIFT-PolyPhen / ClinVar significance | first-class | **C** | SPARQL is the ~2.8× subset — **comprehensive pathogenic enum = REST tool**, not SPARQL |
| oma | `orth:hasTaxonomicRange <tax>`; `orth:organism` | first-class | **C** | fragile: `hasHomologousMember+` & organism-subtree time out — never property-path |
| amrportal | ARO IRI + `amrClass`(47-val) + phenotype(5-val) | first-class | OK | value sets small/enumerable |
| bgee | `genex:hasAnatomicalEntity <UBERON>` | first-class | OK (pin graph) | anatomy-scoped count; pin GRAPH to avoid label inflation |
| brenda | `d3o:isClassifiedAs <ec/X.X.X.X>` | first-class | OK | EC-IRI + `d3o:hasTaxID` both worked |
| chembl | `cco:hasProteinClassification`; `cco:hasMesh` | first-class | OK | classification-IRI + MeSH-IRI (100% coverage) |
| go | `hasOBONamespace`(3-val) **and** `rdfs:subClassOf+` | first-class | OK | ontology — enumeration is the point |
| hco | `hco:bandtype` (8-val) + `subClassOf hco:Cytoband` | first-class | OK | small enumerable stain set |
| jpostdb | `jpost:disease/sampleType/organ` (DOID/NCIt/BTO); `unimod:UNIMOD_*` | first-class | OK | pre-typed IRIs, no text search |
| massbank | `mb:instrument_type`(49) / `ms_type` / `ion_mode` | first-class | OK | method-facet + structure both first-class |
| mco | `subClassOf mco:MouseChromosome` (22-val) | first-class | OK | tiny flat ontology; labels broken → IRI axis only |
| mesh | `meshv:treeNumber` STRSTARTS + `broaderDescriptor+` | first-class | OK | controlled vocab — tree enum is headline |
| mondo | `rdfs:subClassOf*` + `hasDbXref` STRSTARTS | first-class | OK | ontology; needs `owl:deprecated`/`isIRI` filters |
| nando | `rdfs:subClassOf+` + `hasNotificationNumber` | first-class | OK | ontology; language-tag + deprecated-subtree traps |
| nbrc | `mccv:MCCV_000038→040-045` category + type-strain flag | first-class | OK | in-graph category enum only (not the cross-graph subtree trick) |
| ncbigene | `ncbio:typeOfGene` + `ncbio:taxid <tax>` | first-class | OK | `taxid` mandatory (57.8M genes) — organism-scope enum |
| ontology | `rdfs:subClassOf*` + `BFO_0000050` part_of; join to data | first-class | OK | the subtree-expansion surface itself; graph-pin + DISTINCT |
| pdb | `exptl.method` / `entity.pdbx_ec` / SIFTS `xref_db_acc` | first-class | OK | typed-predicate enum; entry FILTER + graph pin |
| pubmed | MeSH `fabio:hasPrimarySubjectTerm`; pubtype `rdfs:seeAlso mesh:` | first-class | OK | seeAlso-vs-fabio distinction documented |
| pubtator | `dcterms:subject "Disease"|"Gene"` + `oa:hasBody` IRI | first-class | OK | enumeration is the DB's core |
| reactome | GO via `RelationshipXref`; EC VALUES; organism; MOD | first-class | OK | UnificationXref-vs-RelationshipXref trap documented |
| rhea | ChEBI participant class (`rhea:chebi`); EC IRI; `isTransport` | first-class | OK | ChEBI-class is the flagship compound-enum path |
| supercon | typed property classes (`a Schema:tc` …) + subClassOf nav | first-class | OK | property-filter, "vocab" is the co-loaded ontology |

## What this means for step 4

1. **Author normally for the ~25 OK rows** — the enumeration example already exists in v2; carry it
   across, re-verify + date it (§4.1), and it satisfies item 8.
2. **Tier A (ddbj, glycosmos, pubchem, mogplus): write a NEW standalone `enum_*` example** — the route
   is buried in v2 and would otherwise never make it into the compressed v3 file. Highest priority.
3. **Tier B/C: keep the specific worked query AND its load-bearing caveat together.** The compression
   instinct (keep the vivid warning, drop the query) is exactly what must not happen for medgen,
   mediadive, hgnc, chebi, clinvar, ensembl, taxonomy, togovar, oma.
4. **Phase-5 item 8 check per file:** does the v3 file contain a set-level enumeration example for
   this DB's row above? If the row is Tier A and the answer is "only a caveat," the file fails item 8.

*Verification note:* v2 statuses are from documentation mining; each Tier-A "new example" must be
**live-verified with a dated count** when authored (§4.1), same as the uniprot `keyword_enum` (71) and
bacdive `oxygen_tolerance` were.
