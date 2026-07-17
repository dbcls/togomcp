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

### Fixed

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

### Changed

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
