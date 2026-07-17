# Changelog

All notable changes to TogoMCP are recorded here. The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/); releases are tagged in git
(`v1.0.0`, `v1.0.1`, …). Entries under released versions are high-level
summaries reconstructed from git history, not exhaustive.

Versions follow the **agent-pragmatic** semver policy documented in
[CLAUDE.md](CLAUDE.md): the public contract is the *tool surface* a client sees
(tool names, parameters, return shapes), not any importable Python API. Adding a
database or a tool is MINOR; a return-shape change rides there too, because our
dominant client re-reads the schema each session. Only a removal/rename is MAJOR.

## [Unreleased]

_Nothing yet._

## [1.7.1] - 2026-07-18

Follow-up to the 1.7.0 co-tenancy sweep: the sweep verified `co_hosted_graphs` and
`critical_warnings` but not the example queries agents copy. An audit of all 36 MIEs
found — and this release fixes — templates that silently returned 0 rows or contradicted
their own file. No tool-surface change; the served MIE/guide content is corrected.

### Fixed

- **11 broken example queries across 10 MIEs, each verified live.** Nine `anti_patterns.correct_sparql`
  / example blocks that returned 0 rows against the endpoint: `oma` (impossible class + no
  organism→taxon edge; rewritten as a HOG-family GROUP BY → 8,763), `supercon` (fictitious
  namespace/class → real `Schema:OxideAndMetallic` Tc scaffold → 4,707), `ddbj` (Gene `bfo:0000050`
  points at the Sequence, not the Entry → 3,244,894), `pubchem` (CID string mistaken for SMILES +
  unpinned descriptor graph → 1,231), `pubtator` (threshold above the IRI's max), `jpostdb`
  (non-existent `jpost:isDetectedIn` → PeptideEvidence bnode path → 242), `bacdive` (`^^rr:Literal`
  GramStain + boolean SporeFormation), `taxonomy` (Superkingdom example missing the graph pin and the
  `131567` exclusion, and mis-describing the bare-namespace rank), `nando` (anti-pattern taught
  `STRSTARTS` as corrective when it is a no-op — real fix is pin + `COUNT(DISTINCT)`); plus `pubmed`'s
  cross-DB join (`rdfs:seeAlso`→`fabio:hasSubjectTerm` for a disease topic).
- **Secondary-section doc drift in 6 MIEs**: `chebi` (a `data_integration` bullet prescribing a
  dead `skos:exactMatch`→ChEBI join), `pubmed` (`mesh/2025` pointer that resolves 0), `chembl`
  (34.0/36.0 version mismatch — counts re-confirmed on 36.0), `glycosmos` (~60 vs measured 148 graphs),
  `go` ("EIGHT" vs ten graphs), `mediadive` (missing the shared-DSMZ-namespace `schema:` prefix warning).
- **`amrportal`** two-stage cross-DB example split into two independently-runnable examples (was one
  un-runnable concatenated block).
- **`uniprot`** OMA warning extended to row-returning `SELECT`s (was framed as counts-only).
- **Benchmark**: 12 questions graph-pinned against co-tenant inflation (no recorded answer changed).

### Added

- **`scripts/check_mie_examples.py`** — runs every MIE's `sparql`/`correct_sparql` block against the
  live endpoint and gates on zero-row/error (with an `expect_empty` allowlist). Wired into the
  mie-generator skill's Phase 5b, which required this check but only in prose.
- **`benchmark/scripts/check_answer_drift.py`** — re-runs every stored benchmark query against its
  recorded `result_count`, the gap `verify_questions.py` (structure-only) can't cover.
- **Usage guide**: CO-TENANCY point 1 now says pin the graph *set* a database owns (UniProt is ~16
  graphs) — a single-graph pin returns empty for a leg whose data lives in a sibling.

## [1.7.0] - 2026-07-17

### Added

- **`co_hosted_graphs` on `mondo` and `taxonomy`**, both probe-verified: `ontology/efo`
  re-declares 16,423 of MONDO's 33,840 classes (×4 join multiplier — 83,035 rows vs 33,766
  pinned), and `dataset/microbedbjp` re-declares 2,153,834 NCBI taxon IRIs at an *older
  nomenclature vintage* (40,252 taxa carry a conflicting `scientificName` — taxid 1224 is
  "Pseudomonadota" authoritatively but "Proteobacteria" there). `dataset/gtdb` was probed
  and recorded as clean — it uses its own IRIs, zero overlap.
- **`mondo.yaml`: EFO's label copy can hide obsolescence.** Where the two graphs disagree
  (5 classes), EFO holds a stale label omitting MONDO's `obsolete ` prefix — so
  `FILTER(!STRSTARTS(?label, "obsolete"))` over the union keeps a retired class.
- **`rhea.yaml`: never name a participant via the ChEBI IRI.** `rh:chebi` points at an OBO
  class carrying no `rh:id` (0 of 13,530) and `rdfs:label` on only 428 (3.2%) — so that join
  silently drops ~96.8% of participants as a *partial* result. Names live on Rhea's own
  compound node (`rh:name`, 100% coverage). Includes an anti-pattern pair.
- **`bacdive.yaml`: `schema:` is not schema.org.** It means `https://purl.dsmz.de/schema/`;
  the endpoint auto-declares it, so the conventional `PREFIX schema: <http://schema.org/>`
  makes every pattern return 0 rows silently. Also: phylum names are stored unmerged across
  two nomenclature vintages (Firmicutes 13,862 + Bacillota 1,944, etc.), so filtering on the
  current name alone returns a small minority.
- **`get_MIE_file` now prepends a trap banner** headlining that database's critical warnings
  and co-hosted graphs above the YAML body, with a per-predicate check instruction. The
  banner is `#`-commented, so banner + body still parses as YAML.
- **Every one of the 36 databases now declares `co_hosted_graphs`** — 20 with probe-confirmed
  traps, 16 recorded probed-clean or exempt. Previously 3 did. Each entry names the sibling graph,
  the re-declared predicate, a **measured** multiplier, the trap kind and the fix; each clean note
  says which legs were probed. Highlights, all verified twice (agent + independent re-run):
  `glycosmos` ×4.16 with undocumented `tmp/*` staging graphs that duplicate real ones exactly
  (254,097 IRIs, 100% overlap); `go` ×3.27 (a *glycosmos* graph is co-hosted on `primary` and
  re-declares 19,255 GO classes); `chebi` up to ×12 on water — a product of 4 type-graphs × 3
  label-graphs; `ensembl` ×3 human / ×2 mouse; `bgee`/`oma` share 908,030 gene IRIs, and OMA's
  unpinned form does not inflate — it times out; `mogplus` **×701.6** (43,501 unpinned vs 62 — 99.86%
  foreign). `supercon` is the only genuine single-graph exemption.
- **`ddbj`: the same taxon IRI is labelled `"9606"` in one of its graphs and `"Homo sapiens"` in
  another — and both are in ddbj's own `graphs:` list.** An inward trap, invisible to any rule keyed
  on databases-per-endpoint; a naive label read returns the bare taxid ~half the time.
- **`nbrc`: pinning the NBRC graph is not enough.** Its canonical taxon link lands on
  `identifiers.org/taxonomy/<taxid>`, which co-hosted `microbedbjp` re-declares at an older
  nomenclature vintage — so the strain→taxon→name join is ×1.94 (42,416 rows / 21,869 strains vs
  21,858 pinned) with 1,211 taxa carrying conflicting names. The trap is on the **name leg**, in a
  graph the reader never asked for. Recorded with its cost: pinning drops 11 strains whose only name
  lives in the legacy graph.
- **`pdb`: BMRB owns the only `rdfs:label` on 29,544 PDB entry IRIs** (its internal `"info:pdb/1ATP"`);
  `dataset/pdb` puts none on entries, so an unpinned title query answers with another database's URI.
- **`amrportal`: ARO *is* loaded in-graph** (8,564 labelled classes; `ARO_0000073` → "meropenem").
  The file previously claimed no ARO ontology was loaded — safe for joins, but it denied a real
  capability by sending readers to OLS4 for labels that resolve locally.

### Changed

- **Usage guide v5 → v6: the endpoint table was wrong exactly where it mattered most.**
  It listed `sib` as "UniProt · Rhea" — OMA has been mounted there since 2026-04-28, and
  OMA is the graph that silently supplies `dcterms:identifier` and produced the one
  materially wrong benchmark answer (Q076: 248, truth 249). The guide was actively
  *reassuring* an agent that no co-tenant could corrupt a UniProt query. `primary` was
  listed with 5 databases; it hosts **16**. `ebi` was missing AMR Portal, and six
  endpoints (pubchem, pdb, ddbj, glycosmos, nims, togovar) were absent entirely — the
  table covered 15 of 36 databases. Now generated from and **regression-tested against**
  `endpoints.csv` (`TestUsageGuideEndpointTable`), because this table drifts silently and
  a stale copy is worse than none. Entries are now the exact `database=` keys, since a
  display name ("MoG+", "AMR Portal") does not resolve.
- **Usage guide gained the defensive-SPARQL rules it never had.** A grep of all four v5
  part files for `GRAPH`/`FROM <`/pin/`DISTINCT`/`xsd:string` returned **zero** hits: every
  rule ratified by the 2026-07-17 audit lived only in `qa-generator` (Hard Rules 4/5,
  C28/C29) or the MIE spec — i.e. on the *authoring* path. The usage guide is what a **live
  agent** reads, and it carried none of them. Added: CRITICAL RULE 3 (pin every graph), a
  🕸️ CO-TENANCY section, and three silent-failure traps (literal-form polymorphism →
  `STR(?label)`; hollow `VALUES` blocks, which are valid SPARQL returning a plausible wrong
  number; release-pinned IRIs → stable-ID anchoring with mandatory `^^xsd:string`).
  Co-tenancy is framed as a property of **graphs, not databases**, so single-tenant
  endpoints (TogoVar: 2.9M variant IRIs re-typed across its own two graphs) are not
  mistaken for safe.
- **The pin is not ground truth, and the guide says so.** Pinning can drop *legitimate*
  rows — `dataset/microbedbjp` re-declares NCBI Taxonomy at an older nomenclature vintage,
  and "Superkingdom Bacteria" survives only there. A pinned/unpinned disagreement is
  documented as a finding to explain, not a number to adopt; trusting the pin blindly would
  have turned two correct benchmark answers into wrong ones.
- **`get_MIE_file` reading order now surfaces `co_hosted_graphs`** (rank 2, required as of
  spec v2.3), with the per-predicate re-consultation rule and "the MIE describes; the
  endpoint decides" — the lesson of the uniprot prescription below.

- **MIE spec v2.2 → v2.3.** `co_hosted_graphs` promoted OPTIONAL → **REQUIRED whenever the
  endpoint hosts >1 named graph**, and the trigger corrected from *databases-per-endpoint* to
  *graphs-per-endpoint*. The old wording exempted exactly the wrong files: `togovar` sits
  alone on its endpoint and re-types 2.9M variant IRIs across its own graphs, and
  `glycosmos`/`pubchem`/`pdb`/`ddbj` host 43–150 graphs each while being "single-database".
  A clean probe must now be recorded explicitly (`"2g probe run … — no re-declaration
  found"`); only a genuinely single-graph endpoint (`supercon`) is exempt.
- **`data_version` given a provenance rule.** It was REQUIRED but derived from nothing,
  ranging from real (`ChEMBL 34.0`) to placeholder (`Current`, `2025+`) to wrong
  (`uniprot: "Release 2024_06"` against data modified 2026-01-28). It must now be a verified
  date or an endpoint-derived release citing its source, and be re-checked whenever
  `mie_updated` is bumped.
- **`mie-generator`**: 2g probe gated on `get_graph_list()` > 1 graph (was
  `get_sparql_endpoints()` > 1 database); missing `co_hosted_graphs` is now a Phase-5 review
  failure; new 5i-2 verifies `data_version` provenance.
- **`qa-generator`**: new **C29 MIE contradiction (named-check)** — every predicate must be
  checked against the MIE's `co_hosted_graphs`/`critical_warnings` *as it is written*, not
  recalled from a Phase-1 read. Q076 called `get_MIE_file('uniprot')` and still used
  `dcterms:identifier`, which that file already documented as OMA-supplied. C27's trigger
  corrected likewise, and it now notes that `COUNT(DISTINCT)` is not a universal fix.
- **The co-tenancy trap taxonomy has THREE kinds, not two — zero IRI overlap does NOT mean safe.**
  The rule shipped earlier in this release said it did; two independent probes disproved it, and it
  had already produced a wrong entry of our own (`gtdb` was recorded "clean" on zero overlap; it is
  really ×1.33). (1) same IRI + same predicate → **row duplication** (DISTINCT masks, pin fixes);
  (2) same IRI + conflicting value → **wrong answer** (DISTINCT cannot help); (3) same class +
  *disjoint* IRIs → **scope bleed**: foreign entities silently added, every row unique and
  well-formed, so **only the pin helps** (`?e a dsmz:Enzyme` returns 627,832 of which 8.7% are
  BRENDA's, ×11.47; MediaDive's culture media ×15.5). A ×2 duplicate is conspicuous; a ×15 union of
  plausible foreign rows is not. Propagated to the spec, `mie-generator` and `qa-generator` C27.
- **`mie-generator`: the 2g probe must keep `?p` unbound.** The recipe always specified a reverse
  probe, but nothing said *why*, so a caller could and did substitute a type-first probe — which
  produces false cleans: `ensembl_grch37` types genes as `obo:SO_0001217`, not `terms:EnsemblGene`,
  while re-declaring `rdfs:label` on the same IRIs (×3, invisible to a type probe); and
  `glycovid_pubchem` declares MeSH *descriptor* IRIs as `meshv:Concept` (same-class overlap 0,
  cross-class 768). Also: inflation is a **product of legs**, and a clean probe must record *which
  legs* it checked — a bare "clean" leaves a narrow probe indistinguishable from a thorough one.

### Fixed

- **`TogoMCP_Usage_Guide` advertised "the v4 Usage Guide"** while serving v5 — two versions
  stale. The docstring is the tool description an LLM reads, so it now names v6 and carries
  the co-tenancy warning at point-of-call (`Returns:` sections are dropped by FastMCP; this
  text sits above it).
- **`uniprot.yaml` prescribed including 14,432 deleted entries, and called the correct
  exclusion an anti-fix.** The MIE told readers that `COUNT(DISTINCT ?p)` → 589,059 was
  the right protein count and that `FROM <sparql.uniprot.org/uniprot>` "silently drops"
  data. Verified live: the 589,059 includes 14,432 entries that all carry `up:obsolete 1`
  — deletions, not data. Two *independent* corrections were conflated: `COUNT(DISTINCT)`
  defeats the co-hosted OMA graph's 337,813 re-typings (same IRIs, so they collapse),
  while the obsolete entries are *different* IRIs and survive DISTINCT. Current Swiss-Prot
  is **574,627** (`FROM <uniprot>` and `FILTER NOT EXISTS { ?p up:obsolete 1 }` agree
  exactly). The retracted advice appeared in six places, including an `anti_patterns` block
  teaching it as a rule; all six now agree.
- **`uniprot.yaml`'s "93.4% of reviewed proteins have gene names" was wrong three ways.**
  The figure counted `up:encodedBy` presence (gene *nodes*, 549,969), not gene *symbols*
  (`skos:prefLabel`, **503,655** — 46,314 gene nodes are unnamed), and divided by the
  inclusive-of-deleted 589,059. Both figures are now recorded separately, and `<GeneShape>`
  warns that an inner join on `skos:prefLabel` silently drops those 46,314 proteins.
- **`mie_revised` was invisible to `stats.py`.** Six MIEs used `mie_revised`; the spec and
  `load_mie_dates()` use `mie_updated`, so those files silently fell back to `mie_created`
  and reported revision dates ~2.5 months stale (uniprot/clinvar/medgen/ncbigene/pubtator
  all read as 2026-04-29). That skewed failure triage, which treats a failure as actionable
  only if it postdates the MIE date. All six normalized to `mie_updated`.
- **`taxonomy.yaml` understated the `tax:Superkingdom` trap.** It documented "returns 0 rows
  with no error" — true only when pinned. Unpinned it returns 173,618 taxa, every one from
  the co-hosted `microbedbjp` graph: a plausible answer built entirely on legacy nomenclature.
- Stale figures corrected in `mondo.yaml` (33,840 classes / 3,974 deprecated / 29,866 active,
  and four coverage percentages re-measured) and `bacdive.yaml`.
- **Four `data_version` claims were false, all caught by the new provenance rule.** `chembl` said
  `34.0` — the endpoint carries `pav:version "36.0"` (`dcterms:modified 2025-07-28`), two releases
  stale. `ncbigene` said `Release 2026.04` on data whose newest `dct:modified` is **2024-11-21**.
  `nando` said "Current release"; it is a **2023-11-28** snapshot (~2.5 years stale) while claiming
  quarterly updates. `mesh 2024` is unverifiable — its `void:dataDump` lists years statically, a menu
  not a receipt. Now endpoint-derived and cited where derivable: pubchem 2026-05-06, go 2026-05-19,
  chebi 250, mco 2024-09-13, hco 2020-07-15, reactome 95, ensembl 115, chembl 36.0.
- **`pubmed.yaml`'s `graphs:` list sent readers to a graph that answers nothing.** It advertised
  `id.nlm.nih.gov/mesh/2025`, which shares **zero** IRIs with the unversioned MeSH that PubMed's
  `fabio:hasSubjectTerm` actually points at (the year graphs namespace IRIs by year). Following the
  MIE's own graph list returned 0 rows; verified 0 vs 14 labels on PMID 31978945. Replaced.
- **`pubtator.yaml` had a duplicate `mie_updated` key** — YAML silently kept the last, so the file
  reported older than it was. Four MIEs (`hco`, `hgnc`, `jpostdb`, `massbank`) were missing
  `mie_updated` entirely; added.

## [1.6.2] - 2026-07-17

### Added
- **The release process is now enforced, not remembered.** `CLAUDE.md` states a
  release as four required steps (bump + `uv.lock`, CHANGELOG section, PR to
  `main`, tag the *merge* commit), and
  [`.github/workflows/changelog.yml`](.github/workflows/changelog.yml) fails a
  `dev → main` PR that changes `pyproject`'s version without a matching
  `## [x.y.z] - YYYY-MM-DD` heading. The check fires only on a real version
  change and asks only for the heading.

### Fixed
- **This changelog.** It documented through 1.0.1 while `pyproject` had reached
  1.6.1 — eight undocumented releases, 303 commits — and its `[Unreleased]`
  section described the FastMCP 421 / `deploy.sh` / reproducible-build work that
  had already shipped. That section *was* 1.1.0 and is now dated as such;
  1.2.0–1.6.1 are reconstructed from git history. Tagging had also stopped after
  `v1.0.1`; `v1.1.0`–`v1.6.1` now exist, on the merge commits, matching the
  existing convention.
- `ontology` MIE (v2.2 → v2.3): `IAO_0000233` was documented as an `xsd:anyURI`
  literal "(a LITERAL, not IRI)" — backwards for the very graph its count came
  from. The predicate is polymorphic *by graph*: all IRI in `hp` (1,461), all
  `xsd:anyURI` literals in `go` (20,249), `xsd:string` in `cl`, mixed in
  `mondo`/`uberon`. Also compressed 979 → 901 lines (duplication only; every
  verified fact retained), and repaired an anti-pattern whose `wrong_sparql`
  errored instead of returning its documented 5 rows.

### Changed
- `mie-generator` skill: the literal-form probe no longer enumerates a closed
  list of string-like forms. `xsd:anyURI` is an `xsd:` type *and* string-like, so
  the previous "watch for non-`xsd:` datatypes" rule missed it. The rule is now
  to ASK for **every** datatype the survey reports, whatever its namespace.

## [1.6.1] - 2026-07-16

### Fixed
- Ran **every** `anti_patterns.correct_sparql` in the collection against its live
  endpoint: 105 runnable blocks, 5 genuinely broken. All five fixed.
  - `bgee` (v2.2): the circular-reasoning anti-pattern was broken five ways and
    had never been executed — undeclared `oba:` prefix, a nonexistent graph
    (`dataset/bgee` vs the real `http://bgee.org`), the wrong predicate
    (`RO_0002206`; Bgee uses `genex:hasSequenceUnit`), Ensembl-namespaced gene
    IRIs Bgee does not have, and `VALUES` before `SELECT`.
  - `ensembl` (v2.7): the same shared template, plus an undeclared `terms:`
    prefix. Its biotype table was also a silent top-30 of 39 — it summed to
    87,654 against a stated 87,693, the 9 omitted biotypes holding exactly those
    39 genes. Now complete, and every opaque `SO_*`/`ENSGLOSSARY_*` code carries
    a verified label.
  - `bacdive` (v2.3): `schema:hasGramStain` is `^^rr:Literal` (an R2RML
    artifact), so `hasGramStain "positive"` returned **0 rows silently**.
    `CellMotilityShape` was wrong throughout (`xsd:boolean`, not `xsd:integer`).
  - `ddbj` (v2.2): `correct_sparql` packed two queries into one block behind a
    `<...Division#PHG>` placeholder.
  - `pubtator` (v2.5): `VALUES` before `SELECT` — a syntax error, not a query.
- `ontology` MIE (v2.1): its own advice was wrong — "prefer the `<ontology/go>`
  copy" returns 0 rows for any RO_/BFO_ term GO does not itself use. Coverage is
  per-*term*, not per-graph.

### Changed
- `mie-generator` skill, two root causes so the generator stops reproducing them:
  `DATATYPE()` cannot determine a literal's match form (RDF 1.1 makes a plain and
  an `xsd:string`-typed literal the same *value*, so it reports identically for
  graphs whose required form is **opposite** — the form is now settled by a
  per-form `ASK`); and the `ontology/go` fallback above.

## [1.6.0] - 2026-07-16

### Added
- **`ontology` database** — a cross-ontology term-resolution and
  hierarchy-expansion surface over the 37 ontology graphs on the RDF Portal
  primary endpoint (785,551 `owl:Class`): HP, UBERON, CL, SO, ECO, EFO, PRO,
  FMA, CLO, EDAM, SIO and ~14 others that have no MIE of their own. Resolves
  opaque IRIs to labels and expands subtrees for joins against co-located data —
  the one thing OLS4 cannot do. Listed on the intro page and README.

### Fixed
- `ontology` MIE (v2.0): v1.0 assumed a single obo namespace, so batch
  resolution returned **0 rows, silently**, for EFO/SIO/EDAM/MEO/FMA. Adds
  per-ontology IRI namespaces, a per-ontology predicate map (FMA has no
  `skos:notation`/`oboInOwl:*`/`IAO_0000115` at all), the `part_of` partonomy
  (UBERON brain: `subClassOf*` returns 5 taxon variants and **zero** body parts
  vs 72 real parts), and `COUNT(DISTINCT)` over DAG expansions (PubCaseFinder:
  111,591 reported vs 75,562 true — which also reordered the ranking).
- `chembl` MIE (v3.4): the typing warning was **inverted**, telling callers to
  append `^^xsd:string` — the one form that returns 0 rows. ChEMBL stores plain
  literals.
- `nando` MIE (v2.2): the `skos:closeMatch` "other targets" category did not
  exist; 2,150 was a distinct-disease count mislabelled as a triple count.
- `glycosmos` MIE (v4.2): verified lectin-name grounding layer.

## [1.5.0] - 2026-07-15

### Added
- `togovar_search_variant` surfaces per-transcript VEP consequences,
  genotype/QC counts and MedGen CUIs (C2–C7).

### Fixed
- TogoVar MIE (v1.3): multi-valued ClinVar gene, `tgv_id` gating, REST paging
  cap; corrected a stale REST/SPARQL ratio and the whole-database facet comment.

## [1.4.0] - 2026-07-14

### Fixed
- TogoVar `search_*` tools (T1–T8): output bloat, opaque codes and loose
  matching — bounded SV alleles, real labels, `tgv_id`/IRI exposure, `match_type`
  ranking.
- TogoVar MIE (v1.1, v1.2): corrected the ClinVar join key; documented that stat
  facets are scoped rather than whole-database.
- `mie-generator` skill: Rule 2 extended to verify *results*, not merely that a
  query executed.

## [1.3.1] - 2026-07-14

### Fixed
- `search_rhea_entity`: projection must not change the row set — the fetch is now
  anchored on the rhea-id.

### Added
- Versioning policy documented in `CLAUDE.md`.

## [1.3.0] - 2026-07-14

### Added
- `search_rhea_entity` gains a validated `columns` parameter for enriched
  reaction fields (13 column IDs, enumerated in the tool description).

### Fixed
- Return/error contracts restored across 10 tools. FastMCP drops the `Returns:`
  docstring section, so the contract never reached the client; it now lives in
  the description body. Guarded by a test that every tool exposes one.

## [1.2.0] - 2026-07-14

### Added
- **TogoVar** as a mounted sub-server (`togovar_search_gene|disease|variant`) —
  human genome variation: gnomAD/ToMMo/JGA/BBJ frequencies, ClinVar+MGeND
  significance.
- **HCO** (Human Chromosome Ontology) and **MCO** (Mouse Chromosome Ontology)
  databases.
- ChEMBL: `id_lookup` broadened to cell_line/tissue/assay; InChIKey/InChI
  resolved via SPARQL with REST reserved for SMILES.

### Changed
- `serverInfo.version` reports TogoMCP's own version rather than FastMCP's —
  making a stale deployment visible.
- ChEMBL tools extracted into `chembl.py`; ChEMBL retry plumbing shared across
  all REST wrappers.

### Fixed
- Reactome silently dropped zero-yield `species`/`types` filters (returning 1,058
  rows for a bogus species). Filters are now honored client-side, with a real
  limit cap and an enriched return envelope.

## [1.1.0] - 2026-07-06

### Changed
- **⚠️ Breaking (deployment): upgraded FastMCP 3.0 → 3.4.3.** FastMCP 3.4.3
  ("The Fast and the Secure-ious") adds Host/Origin validation to Streamable HTTP
  for DNS-rebinding protection. Its default allow-list is localhost only, so a
  `0.0.0.0`-bound server behind a reverse proxy now returns
  `421 Misdirected Request` for any request whose `Host` is a public vhost.
  `main.py` allow-lists the public vhosts (`togomcp.rdfportal.org`,
  `test-togomcp.rdfportal.org`); add internal names via `TOGOMCP_ALLOWED_HOSTS`.
  (#115)

### Added
- `scripts/deploy.sh` — Podman deploy helper that enforces test-before-prod
  promotion: prod only promotes the exact image already tested on the test
  container, refuses unless the test container answers `200`, requires typing the
  production hostname (fail-closed), and saves a rollback pointer. (#114)
- `TOGOMCP_ALLOWED_HOSTS` / `TOGOMCP_ALLOWED_HOSTS_TEST` env vars, wired through
  `compose.yaml` and documented in `.env.example`, to add hostnames to the
  FastMCP Host allow-list without a rebuild. (#115)

### Fixed
- Reproducible Docker images. `uv.lock` is now shipped into the build context
  (it had been excluded by `.dockerignore`) and installs use `uv sync --frozen`
  / `uv run --frozen`. Previously each build re-resolved dependencies from PyPI,
  silently floating the deployed FastMCP version — which is what let an unpinned
  build pick up FastMCP 3.4.3 the day it shipped and cause a production 421.
  (#112, #113)
- `pyproject` version had been stuck at `0.1.0` while git tags moved to `1.0.x`;
  reconciled to 1.1.0 and `uv.lock` regenerated so `--frozen` builds stay
  consistent.

## [1.0.1] - 2026-05-07

### Changed
- REST-wrapper and catalog tools return graceful error payloads instead of
  raising on bad input / upstream HTTP failures.
- `find_databases` made the canonical, required database-discovery tool.

### Added
- jPOST database onboarding; `get_graph_list` extended with endpoint arguments.
- MIE spec v2.1 (shape_expressions discipline, pre-publication audit phases) and
  a corresponding MIE-file sweep.
- Benchmark result batches (Opus 4.7) with prior runs archived.

## [1.0.0] - 2026-03-07

- First tagged release. FastMCP server exposing RDF Portal SPARQL plus selected
  REST APIs (NCBI E-utilities, UniProt, ChEMBL, PDB, PubChem, Reactome, Rhea,
  MeSH, TogoID), the bundled MIE files, and the SPARQL endpoint registry.

_MIE database onboarding and revisions land continuously and are summarised per
release above; see git history for the full detail._

[Unreleased]: https://github.com/dbcls/togomcp/compare/v1.6.2...HEAD
[1.7.1]: https://github.com/dbcls/togomcp/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/dbcls/togomcp/compare/v1.6.2...v1.7.0
[1.6.2]: https://github.com/dbcls/togomcp/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/dbcls/togomcp/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/dbcls/togomcp/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/dbcls/togomcp/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/dbcls/togomcp/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/dbcls/togomcp/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/dbcls/togomcp/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/dbcls/togomcp/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/dbcls/togomcp/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/dbcls/togomcp/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/dbcls/togomcp/releases/tag/v1.0.0
