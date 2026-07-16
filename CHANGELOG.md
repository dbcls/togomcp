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
- `ontology` MIE (v2.2 → v2.3): `IAO_0000233` documented as an `xsd:anyURI`
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

[Unreleased]: https://github.com/dbcls/togomcp/compare/v1.6.1...HEAD
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
