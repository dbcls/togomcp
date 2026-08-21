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

## [2.8.0] - 2026-08-21

A tutorial, and the routes to serve it. Nothing on the tool surface changed — no tool, parameter, or
return shape — so an agent sees exactly what it saw in 2.7.8. This is MINOR rather than PATCH because
the server gained a user-facing capability it did not have: it now serves documentation of its own, at
its own origin, in two languages.

The gap this closes is an onboarding one. The landing page could get a user connected and then left
them there; the measured failure modes of *using* the thing — asking a question no database can answer,
believing a fluent answer that came from the model rather than the endpoint, not noticing a count is
wrong rather than the answer — were written down nowhere a new user would find them.

<!-- whatsnew: 2026-08-21 | A <strong><a href="/tutorial">self-study tutorial</a></strong> now ships with the server — eight chapters taking a life-science researcher from a first question to a result they can defend, plus exercises with worked solutions. No RDF or SPARQL background assumed; also in <a href="/tutorial/ja">日本語</a>. -->

### Added

- **Tutorial pages, served by the server itself** at `/tutorial` (English) and `/tutorial/ja` (Japanese).
  A single self-contained HTML handbook each, built from `tutorial/` and bundled under
  `data/docs/tutorial/`, so they deploy with the wheel and need no separate hosting. Content: setup by
  three routes, two worked demos, how the MIE/SPARQL layer actually works, a deliberate *failure* demo,
  question-writing patterns, a four-step verification procedure, troubleshooting, and seven exercises
  with worked solutions. The two languages cross-link to each other.
- The intro page now points at the tutorial from the hero, the sticky menu, the end of the Setup
  section, and the footer — previously nothing on the landing page led a new user past "it is
  connected" to "here is how to use it well".

## [2.7.8] - 2026-08-20

Three field reports, no tool, parameter, or return shape changed — two MIE files and one docstring.
The common shape is a query that runs, returns rows, and is wrong or fragile in a way nothing signals.
Worth noting for anyone triaging the next one: **two of the three reports named the wrong cause**, and
the investigation only found the real one because the claim was reproduced rather than accepted. The
ChEMBL report was right. The UniProt performance report blamed a `FILTER(CONTAINS())` that turned out to
be the smaller half of the problem — a missing `FROM` pin was the larger. The `search_uniprot_entity`
report described a silent full-text fallback that does not exist; the tool was working, its docstring was
incomplete, and the results that looked wrong were correct. Deliberately no `whatsnew` marker: none of
this is visible to a user who is not writing SPARQL or tool queries by hand.

### Fixed

- **`chembl.yaml` did not warn that one UniProt accession maps to SEVERAL ChEMBL targets of different
  `cco:targetType` — so the obvious `?target a cco:SingleProtein` silently returns a fraction of the
  answer.** ChEMBL curates a mechanism onto whichever target entity the curator judged right, and that is
  frequently *not* the single protein: P10253's VOGLIBOSE and CELGOSIVIR hang off the PROTEIN FAMILY
  "Alpha glucosidase", and P18505 (GABA-A β1) has **no** mechanism on its single-protein target at all —
  all 69 of its drugs, the benzodiazepines and anaesthetics among them, sit on PROTEIN COMPLEX / PROTEIN
  COMPLEX GROUP targets. Measured 2026-08-20: SINGLE PROTEIN carries only 4,948 of 6,990 mechanisms
  (70.8%), so the type pin discards 2,042 of them, and 1,974 of the 12,253 UniProt-linked accessions
  (16.1%) map to more than one target type. There is no error and no empty result — just a short answer,
  which is what makes it worth a file entry rather than a docstring line.

  A new verified example, **`moa_target_types`**, carries the positive route: bind `cco:targetType` as a
  returned column instead of pinning an `rdf:type` class. That works because `cco:targetType` is on all
  17,803 Target entities and on **zero** TargetComponents, so it admits every target kind while still
  keeping components out of `?target` — which matters, because simply deleting the type pin is the wrong
  fix: `cco:hasProteinClassification` and `cco:organismName` are carried by TargetComponents too. There is
  also no `cco:Target` umbrella class to pin instead (`?t a cco:Target` returns 0 rows), so an `rdf:type`
  constraint can only ever name one kind. On the example's three accessions the query returns 143 rows /
  76 molecules; with the pin, 5 rows / 5 molecules.

- **The same trap was live in two existing examples, and both now say so.** `class_enum` returns 29 of the
  48 typed human phosphodiesterase targets — the families (including "Phosphodiesterase 4"), selectivity
  groups, protein-protein interactions, the complex and the chimera all carry the same classification IRI
  and were being dropped. `moa_integration`'s pin is a deliberate narrowing and stays, but now records what
  it omits and points at `moa_target_types`. Following the placement rule in the MIE spec, the finding is
  filed as a worked example plus `traps_avoided` lines rather than a `global_gotchas` paragraph: it has a
  concrete query that avoids it, and a query an agent can copy is worth more than prose it must translate.

- **`uniprot.yaml`'s `sequence_mass` example was fragile under extension, and the cause was not the one it
  looked like.** The example selected the canonical isoform with `FILTER(CONTAINS(STR(?seq), "/P01308-1"))`
  and carried **no `FROM` pin** — so it ran against the union of all 63 graphs on the SIB endpoint, OMA's
  584M triples included. Alone it returned in 0.19s; bolt on two `OPTIONAL`s and it did not finish. The 2×2
  measured 2026-08-20 (`OPTIONAL`s on `rdfs:seeAlso`/`up:database` and `up:classifiedWith`/`rdfs:label`):
  unpinned `FILTER` form **>200s, no result**; unpinned direct-IRI form **>200s** as well; pinned `FILTER`
  form **5.6s**; pinned direct-IRI form **~1.5s**. So the missing pin — which the file's own
  `union_inflation` gotcha already prescribes — was the larger half, and naming the IRI removes the
  remaining ~4×. The example now pins the graph and states `isoforms/P01308-1` directly: no `?seq` variable,
  no post-filter, 0.4s standalone.

  Three findings from verifying the replacement are recorded as `traps_avoided` rather than left implicit.
  `isoforms/ACC-1` is **not** universal — 2,985 of 3,000 sampled reviewed human entries have it, and the
  rest start at `-2`, `-3` or `-5` because the canonical was merged or demoted, so a direct-IRI lookup that
  returns 0 rows needs the accession-scoped fallback. The cross-accession trap the example already warned
  about is not a one-off: O94854 hangs five `Q9UPN3-*` isoform nodes off `up:sequence` and has no
  `O94854-1` node at all. And every sequence node is typed **both** `up:Simple_Sequence` and
  `up:External_Sequence`, so binding `?seq a ?class` doubles the rows.

- **`search_uniprot_entity`'s docstring never mentioned the `go` field, which reads as a silent failure when
  it is not one.** A `go:0043202` query returns proteins that look unrelated to lysosomes (keratocan,
  osteomodulin, syndecan-3), and with `go` absent from the documented field list the natural conclusion is
  that the tool accepted an unsupported field and fell back to full text. It does not: all three proteins
  genuinely carry `GO:0043202` in UniProt's own RDF (confirmed by SPARQL), and an unknown field name is
  rejected upstream with HTTP 400 (`'go_id' is not a valid search field`), surfacing as this tool's
  documented `"Error:"` string. The docstring now documents `go` along with the two ways it *can* mislead —
  the ID must be zero-padded to 7 digits (`go:43202` is a valid field with an unmatchable value: 0 rows,
  HTTP 200), and the match includes GO **descendants** (192 reviewed entries carry GO:0043202 directly, 214
  once its two children are counted). A new warning at the top of the docstring states the actual failure
  mode: a bad *field name* errors, a bad *value* is what fails silently.

## [2.7.7] - 2026-08-20

Logging release: the client IP can now be recorded in the clear, so an abusive caller can be
identified and blocked rather than merely counted. **No tool, parameter, or return shape changed** —
this is a patch against the tool surface, which is the contract semver applies to here. The change
that matters most is the one under *Fixed*: the address the log recorded was caller-supplied and
therefore spoofable, which was survivable while it was only ever hashed and is not survivable once
it is meant to identify someone.

### Added

- **`TOGOMCP_LOG_RAW_IP`: record the client IP in the clear, for abuse attribution.** Off by
  default. When set (`1`/`true`/`yes`/`on`), each tool-call record gains an `ip` field carrying
  the raw client address alongside the existing `ip_hash`, plus `forwarded_for` — the raw,
  untrusted `X-Forwarded-For` chain, kept verbatim next to the observed peer so the two can be
  compared. **This reverses a guarantee `log_file_specs.md` previously made unconditionally**
  ("client IPs are never stored raw"); that document's privacy model has been rewritten rather
  than patched, and now states the trade explicitly: with the knob on, the log is personal data
  and `/stats/log` streams it verbatim to whoever holds the dashboard credentials. The knob is
  fail-closed — absent, empty, or misspelled all mean off — so a `deploy.sh` env-forwarding miss
  loses the raw address instead of silently leaking one. Wired into all three places a knob must
  appear (`compose.yaml`, `.env.example`, `deploy.sh`'s forwarded list).

  `ip_hash` is still written unconditionally and remains what `/stats` aggregates on, so an
  excerpt can be shared with `ip` stripped and still aggregate identically. The dashboard is
  unchanged: reach is a *count* of distinct addresses, never a list, and a regression test now
  pins that no raw address can reach any aggregate.

### Fixed

- **The logged client IP was the caller's `X-Forwarded-For` header, not the peer — i.e. spoofable.**
  The middleware read the header directly, ahead of `request.client.host`, which skipped uvicorn's
  `ProxyHeadersMiddleware` entirely: that middleware substitutes the header into the peer address
  *only* for peers trusted via `forwarded_allow_ips`, walking the chain right-to-left to the first
  untrusted hop. Reading it ourselves meant anyone able to reach the port could write any address
  they liked into the log, and that the stored value was a comma-separated *chain* rather than an
  address. Both were invisible while the field was only ever hashed; neither is survivable once the
  value is meant to identify someone. The middleware now records the peer as uvicorn resolved it,
  leaving the trust decision where it is configured. On the production path (rootless podman, peer
  `10.0.2.100`, inside the default allow list) uvicorn has already substituted the forwarded client
  into that peer, so this yields a strictly better value than before.

  One consequence for anyone reading logs across the change: `ip_hash` was previously computed over
  the *header string* and is now computed over the resolved address, so the same client hashes
  differently on either side of the boundary. Reach counts spanning it can double-count a client.

## [2.7.6] - 2026-08-19

Usage-analysis release: the `/stats` dashboard was reporting numbers that could not be read
correctly, and three of them were actively wrong. **No tool, parameter, or return shape changed** —
this is filed as a patch against the tool surface, which is the contract semver applies to here.
Everything below is aggregation and presentation, computed from the log format as it already is;
the new columns work retroactively on logs already on disk.

The one deployment-facing addition is `TOGOMCP_STATS_EXCLUDE_CLIENTS`, wired into all three places
a knob has to appear (`compose.yaml`, `.env.example`, `deploy.sh`'s forwarded list).

### Added

- **`/stats` co-query attribution: cross-database work is no longer invisible.** A record gets one
  primary database (its `database=` arg), so a UniProt-Rhea join on the co-hosted SIB endpoint was
  filed entirely under uniprot — all 532 of them in 2026-08, while rhea's own row read 1 query and
  looked unused. A new **co-query** column credits every database whose namespace a query actually
  touched, derived from the prefixes already recorded in `extra.query_shape.predicates` (present on
  100% of logged SPARQL, so this works retroactively). It is counted separately from `calls` on
  purpose — one query legitimately credits several databases, and folding them together would stop
  the row adding up. A new **Cross-database joins** table lists the filed-under → also-queried pairs.
- **`/stats` now reports reach, not just volume.** Every per-database and per-tool row carries
  **IPs** (distinct hashed client addresses) and a new **Per client** table gives each client its
  calls, IPs, days, and **calls/IP**. That one ratio is the demand-vs-script tell: in 2026-08
  `openai-mcp` sent 693 calls from 355 IPs (2.0 each — a crowd) while `mcp`, the MCP SDK's default
  client name, sent 8,415 from 11 (765 each — a harness). The same column resolves rows that look
  alike by volume: massbank's 229 calls came from **150** IPs and rhea's 228 from **9**.

  Distinct *sessions* is deliberately NOT reported. It looks like the natural measure and is
  actively misleading: ChatGPT connectors are stateless and open one session per call, so
  `openai-mcp` scores 1.00 calls/session — identical to a scripted sweep, and the opposite of what
  that number suggests. Caveat on IPs: with `TOGOMCP_LOG_HASH_SALT` unset the salt is regenerated
  per process, so one client counts once per server restart. The dashboard says so inline.
- **`TOGOMCP_STATS_EXCLUDE_CLIENTS`** (new, optional) drops named clients from the aggregate — the
  escape hatch for a known self-inflicted source. On this log, excluding `mcp,glyconavi,mcporter`
  removes 29,051 of 33,500 records; massbank's row is untouched at 229 calls / 150 IPs, while rhea
  falls from 228 to 2. It is empty by default and never inferred: which traffic is real is an
  operator's judgement and a wrong guess silently deletes real users. Whatever is excluded is
  stated at the top of the dashboard. Wired into `compose.yaml`, `.env.example` **and**
  `deploy.sh`'s forwarded list — a knob missing from that list is inert in production.
- **MIE traps now name the other databases the failing query touched** (`co_databases`, rendered as
  *also touched*). Three of the uniprot timeouts in this log are Rhea-predicate queries: the gap may
  be in rhea's MIE, which was previously unreachable from rhea's row.

`SIGNATURE_PREFIXES` is precision-biased: a prefix qualifies only if it is declared in an MIE file
*and* binds to a namespace owned by exactly one database, which excludes shared vocabularies
(`obo:`, `sio:`, `bp:`, `orth:`, `faldo:`, …). The cost is a documented blind spot — go, chebi,
mondo, reactome, oma, bgee, hgnc and brenda are expressed *only* in shared vocabularies, so they
always read 0 co-query: undetectable, not unused. Removing that blind spot needs the collection
layer to record namespace IRIs instead of prefix strings, since a prefix string is the client's
choice rather than a property of the data.

**Colliding prefixes are resolved by local name** (`_AMBIGUOUS_PREFIX_QNAMES`). `schema:` is the
live case and it is not a *shared* vocabulary but a *collision*: bacdive, mediadive and taxonomy
bind it to DSMZ's own `https://purl.dsmz.de/schema/`, while massbank binds it to real schema.org —
a trap each of those MIEs already warns about, because declaring the wrong one returns 0 rows with
no error. In this log 128 records used `schema:` under a massbank primary and 10 under bacdive, so
mapping the bare prefix either way would have mis-credited the other. Qnames exclusive to one
database (`schema:describesStrain` → bacdive, `schema:CultureMedium` → mediadive, `schema:inChIKey`
→ massbank) are mapped; the genuinely shared bacdive↔mediadive join vocabulary (`schema:Strain`,
`schema:hasBacDiveID`, `schema:partOfMedium`) is deliberately left unmapped because it belongs to
both. The sets are derived from the MIE corpus and a test re-derives them, so they fail loudly when
a database's vocabulary moves.

### Fixed

- **`/stats` per-database table: `calls` no longer conflates reading an MIE with querying an
  endpoint.** The single `calls` column made two opposite rows unreadable. massbank showed
  229 calls / 176 SPARQL and looked like it had a REST API it does not have — the gap was 53
  `get_MIE_file` calls. rhea showed 228 calls / 1 SPARQL and looked unused — 223 of those were
  MIE reads. `calls` is now split into **query / graphs / search / MIE / other**, which sum
  exactly to it. Classification is by *tool identity*, not transport: the ChEMBL search wrappers
  are SPARQL-backed, so counting them as queries recreated the same confusion in mirror image
  (1,215 of chembl's 7,410 endpoint hits in 2026-07 were wrapper calls, not queries anyone wrote —
  and 4,963 of its 12,373 `calls` that month were MIE reads).
- **NCBI E-utilities traffic no longer contaminates the RDF per-database rows.** `db=`/`database=`
  on `ncbi_*` names an E-utilities database, and pubmed, clinvar, medgen and taxonomy are *also*
  RDF Portal keys — so the two namespaces silently merged. In 2026-08 the pubmed row read 3,589
  calls when its real RDF usage was 48, and clinvar 1,513 against a real 48. `database_of()` had
  documented this exclusion since it was written but never implemented it.
- **Three database-specific wrapper tools were missing from the per-database attribution map** and
  their calls vanished from the table entirely: `search_chembl_id_lookup`, `get_pubchem_compound_id`,
  `get_compound_attributes_from_pubchem` (52 calls in 2026-08). A new test scans the `@mcp.tool`
  registrations in `api_tools.py`/`chembl.py` and fails if a wrapper is added without a mapping.

Aggregation only; the log format and the tool surface are unchanged (`sparql` is still the
endpoint-hit count the MIE-candidate feed scores against).

## [2.7.5] - 2026-08-17

<!-- whatsnew: 2026-07-26 | Second paper out: <em>Measure before you rewrite</em> (<a href="https://doi.org/10.37044/osf.io/6v5ra_v1" target="_blank" rel="noopener">BioHackrXiv</a>) — the ablation study behind MIE v3, the schema-documentation format this server serves. -->

Citation-only release. No tool, parameter, or return shape changed — but the landing page is served
from the wheel (`server.py` mounts `docs/togomcp-intro.html` at `/`), so the second paper does not
reach <https://togomcp.rdfportal.org/> without a build and deploy. That is the whole reason this
carries a version bump rather than riding as a docs-only merge.

The whatsnew marker is dated 2026-07-26, the BioHackrXiv publication date, so it sorts *below* the
five entries the generator renders and does not appear in "What's New". That is deliberate: the
citation belongs in the Publications section, not the news feed. Redate it to surface it.

### Documentation

- **README + intro page: added the MIE v3 report** (Kinjo & Yamamoto 2026, BioHackrXiv,
  [doi:10.37044/osf.io/6v5ra_v1](https://doi.org/10.37044/osf.io/6v5ra_v1)) alongside the
  *Database* system paper. It is the published measurement behind the format `get_MIE_file`
  currently serves: single-section and group-level MIE ablations are null, whole-MIE removal
  costs 0.9/20, and the query-construction group alone recovers 99% of that — which is why v3
  reorganized around the verified executable example. Both surfaces now read "Publications"
  (plural); the intro page's spec (`make_intro.md`) was updated to match.

## [2.7.4] - 2026-08-15

Closes the last gap in the 2.7.1–2.7.3 arc: the Usage Guide is served on **every** session and nothing
ever checked what it asserts. No tool, parameter, or return shape changed.

The literal task — "test the SPARQL queries in the Usage Guide" — turned out to be nearly empty. The
guide contains exactly **two** fenced `sparql` blocks and neither is a runnable query; both are
fragments (a triple pattern, a `FILTER`). The guide's testable surface is not queries but **empirical
claims**: *"without `^^xsd:string` the join silently returns 0"*, *"pinning only `.../uniprot` returns
empty for a taxon-name leg"*, *"two-argument `REGEX()` returns 0 for alternation"*. Each is a statement
about live endpoint behaviour, each is what the surrounding advice rests on, and each rots silently
when an endpoint is reloaded. (The one hand-written table, ENDPOINTS, was already drift-guarded by
`test_server.py` — no second copy added.)

### Added

- **`scripts/check_guide_claims.py` — 6 claims, all passing.** Each is encoded as a *pair* of queries
  plus the expected relationship, almost always "the documented-broken form returns 0 **and** the
  documented-good form does not". That is stronger than either half: it fails loudly both when a trap
  disappears (endpoint patched → the guide now scares readers off a working pattern) and when a
  workaround stops working (→ the guide's fix is wrong). Covers guide items 1, 7, 9 and 10. A script
  rather than a pytest test, for the same reason `check_mie_examples.py` is: these endpoints returned
  502s, 503s and 90 s timeouts repeatedly across a single afternoon, so a live test in the suite would
  go red for reasons unrelated to any change.
- **`tests/test_guide_claims_in_sync.py`** — offline, 9 cases. Every claim carries an `anchor`: the
  load-bearing phrase that must still appear in the served guide. This closes the drift in *both*
  directions, both otherwise silent — guide rewritten and the checker keeps happily verifying a
  sentence nobody ships (still reporting "6 ok"), or a claim quietly dropped from the checker while the
  guide keeps asserting it. It caught a defect on its first run: an anchor written from memory that
  spanned a hard-wrapped line. Anchors must now stay within one source line, and that is noted where
  they are defined.

### Fixed

- **Guide item 7 cited two examples that no longer show what it said they showed.** It claimed
  `GO_0005183` and `CHEBI:29108` carry labels "twice — plain and `xsd:string`". Live, both carry
  **only** `xsd:string`: `GO_0005183` in 2 graphs (efo, go) and `CHEBI_29108` in 5 (Rhea, efo, uberon,
  pro, pro-reasoned), same value and same datatype every time. That is cross-graph *duplication* —
  item 1's co-tenancy trap — not a datatype split, so the two IRIs were illustrating the wrong lesson.
  The rule itself is sound and stays: the item is re-anchored on a case that is live and checked,
  `ontology/fma`'s `rdfs:label` at **104,919 `@en` + 17 `xsd:string`** in one graph on one predicate,
  and widened past plain-vs-typed to the forms the corpus actually contains (`@en`, `^^xsd:anyURI`,
  `^^rr:Literal`).

## [2.7.3] - 2026-08-14

**2.7.2's rule was too narrow, and one of the two fixes it offered was bad advice.** Asking "is any MIE
inconsistent with the new rule?" turned up no inconsistency in the corpus — but checking the *mechanism*
behind the bug, rather than only grepping for it, showed the rule itself was wrong. No tool, parameter,
or return shape changed.

Alternation is not the only construct the two-argument `REGEX()` mishandles. Brace quantifiers fail
identically, and on the same 10 of 10 endpoints:

```sparql
VALUES ?s { "ab" "aab" "aaab" }  FILTER(REGEX(?s, "a{1,2}b"))   -- returns 0. The answer is 3.
```

Verified across `{n}`, `{n,}` and `{n,m}`, and for alternation across `A|B`, `A|B|C`, one-sided `A|` and
`A|A`. Both are consistent with Virtuoso taking a "looks literal" fast path that mis-parses certain
metacharacters — which means the two known-broken constructs are what has been *tested*, not a proof
that nothing else is affected.

### Changed

- **The rule is now "always pass a third argument", full stop** (guide SILENT-FAILURE TRAPS #10,
  `04_reference.md`, and the mie-generator skill). 2.7.2 offered parenthesising and the flags argument as
  equal alternatives. Parenthesising does fix both known cases — but it requires the author to know
  *which* metacharacter is affected, which is precisely the knowledge the trap denies them, and it does
  nothing for a construct nobody has tested yet. The flags argument is unconditional and costs three
  characters. The unaffected list (plain substrings, `[Ff]entanyl`, `? + *`, anchors, `.`, escapes,
  `(?:…)`) is kept, because that asymmetry is *why* the bug survives review — a single-term filter works
  until someone widens it to a family or adds a count.
- **massbank + hco: `REGEX` calls updated** to the three-argument form. hco's `bands_on_arm` (`"^13q"`)
  and `position_to_band` (`"^13[pq]"`) were **not** broken — anchors and character classes are unaffected,
  and both re-run to their stored figures exactly (32 rows; 13q14.2 / gpos50 / 46700001 / 50300000, dates
  re-stamped). They are changed because they were one edit away from `"^13p|^13q"`, which is the latent
  form this rule exists to prevent.

### Added

- **`tests/test_regex_two_arg_guard.py` — the rule is now enforced, not advised.** It bans the
  two-argument form outright in any executable `sparql` field across the corpus (37 parametrised cases),
  and asserts the guide still documents the fix and both broken constructs. Two reasons it is a static
  test rather than a live one: `check_mie_examples.py` flags zero-ROW results, so it catches a broken
  `REGEX` only when that filter zeroes the *whole* query — inside an `OPTIONAL` or one `UNION` branch it
  returns rows, just silently fewer, and nothing notices. And a live test would pass the day an endpoint
  is patched, which is exactly when the corpus should still be written defensively. It found hco
  immediately; the ad-hoc grep that preceded it did not, because that grep only looked for patterns
  containing `|`.

## [2.7.2] - 2026-08-14

Promotes 2.7.1's `regex_alternation` finding from one MIE to the Usage Guide, after establishing that it
is not a MassBank fact — or even an RDF Portal fact. No tool, parameter, or return shape changed.

2.7.1 hedged: "Virtuoso engine behaviour … it plausibly affects every database on the endpoint." That
hedge is now a measurement. The bug reproduces with a query that touches **no data at all** —

```sparql
SELECT (COUNT(*) AS ?n) WHERE {
  VALUES ?s { "Fentanyl" "Sufentanil" "Aspirin" }
  FILTER(REGEX(?s, "Fentanyl|Sufentanil"))     # returns 0. The answer is 2.
}
```

— which makes it testable on every endpoint regardless of what each one hosts. All **10 of 10** in the
registry return 0: `primary`, `sib`, `ebi`, `pubchem`, `pdb`, `ncbi`, `ddbj`, `nims`, `glycosmos`,
`togovar`. Grouped `(A)|(B)` and three-argument `REGEX(…, "")` return 2 everywhere.

### Added

- **Usage Guide: `REGEX()` alternation is now SILENT-FAILURE TRAPS #10** (`03_workflows.md`). That section
  is where the endpoint-wide zero-row traps already live — the `^^xsd:string` join that returns 0, the
  plain-vs-typed literal split — and SPARQL DISCIPLINE already points at it before writing. The entry
  leads with both copyable fixes rather than the warning, on the ablation result that query content
  carries the effect and guardrail prose alone does not. It also names the reason the bug survives review:
  single terms, character classes and `.*`-anchored patterns all work, so it only appears when someone
  widens a *working* single-term filter into a family — and the empty result reads as "the database
  doesn't have those."
- **Usage Guide: a troubleshooting row** (`04_reference.md`) pointing at #10, for the case where the
  agent already has an empty result and is working backwards. Pointer only, no restatement.
- **mie-generator skill: the same rule under "Virtuoso-specific pitfalls"** (`references/query-strategy.md`),
  which until now covered only `bif:contains`. Different audience and different purpose: it stops all 37
  future MIE revisions from shipping a bare-alternation example or re-deriving the bug per file, and says
  explicitly that the rule belongs in the guide rather than in each MIE.

### Changed

- **massbank: the `regex_alternation` gotcha is trimmed to its local evidence plus a pointer.** With the
  universal rule in the guide, the file keeps what is genuinely MassBank's — the 44 matching compound
  nodes, the session that read 0 as "no fentanyls", and the fact that compound-name search is a common
  entry point here — and drops the restated general rule. The load-bearing part was always
  `find_compound_by_name` demonstrating the safe form, which is unchanged.

## [2.7.1] - 2026-08-14

No tool, parameter, or return shape changed — this is one MIE file. It is the second release driven by
reading the production tool-call log for *silent* failures rather than errors (2.5.2 did it for mogplus),
and the first where the log said the file was **covering the wrong questions** rather than getting a fact
wrong. Deliberately no `whatsnew` marker: nothing here is visible to a user who is not writing MassBank
SPARQL, and the intro page's five-item list is better spent elsewhere.

The evidence: 202 MassBank calls over 2026-07-29 → 08-14, 137 of them `run_sparql`. Two query classes
dominated and both failed badly — peak/diagnostic-ion search (52 queries, **29% errored**: 90 s timeouts
and gateway 502s) and batch InChIKey screening (48 queries, **63% returned empty**). Neither had an
example. Meanwhile every predicate the file spent an example or a `schema_delta` line on —
`has_peak_annotations`, `ch_exact_mass`, `molecularFormula`, `smiles`, `retention_time`, `pk_splash`,
literature refs — was touched **zero** times in 137 real queries. All nine pre-existing examples still
reproduced their stored figures exactly, so this was not drift; the file was accurate and aimed wrong.

### Added

- **massbank: a fragment-search route, where the file had only a prohibition.** 51 of 60 logged
  `mb:has_peak` queries were unanchored, because "which spectra contain these product ions?" inherently
  is; the file's only guidance was `peak_list`'s *"ALWAYS anchor on a specific spectrum IRI"*, and agents
  ignored it because nothing was offered instead. The new `peak_diagnostic_ions` example puts the rarest
  ion in a `DISTINCT` subquery and tests the rest with `FILTER EXISTS`: **1.10 s**, against 47–52 s for
  the `VALUES ?target` + `ABS()` form when it finished at all and a repeated 90 s timeout for the
  four-way `UNION`. Anchor choice is the whole trick and is now stated with numbers — the 188.1434 ±5 mDa
  window selects 159 spectra, the 105.0699 window 4,874. Three Virtuoso traps came out of reproducing the
  logged failures: `HAVING(COUNT(DISTINCT ?b) = 4)` over a `BIND`-only group raises `SQ200`,
  `IF(cond, ?ik, 1/0)` raises `SR084` because both arms are evaluated, and — the dangerous one — a
  `{ FILTER(?mz >= a && ?mz <= b) BIND(…) }` `UNION` branch whose `?mz` is bound in the *enclosing* group
  is silently not filtered, returning all 117,295 spectra for two different ion windows.
- **massbank: batch compound screening that reports its misses.** 30 of 48 logged screens returned empty
  and were then rewritten five or six times chasing a bug that was not there: MassBank holds 17,921
  structures, and of the 191 distinct InChIKeys the log queried only **31** have any spectrum. The new
  `screen_inchikey_batch` wraps the join in `OPTIONAL` so every queried key returns, misses as
  `n_spectra = 0`, and the caller can report coverage instead of a short list that reads as failure. The
  base rate is now `entity_counts.size_caveat`, so "no reference spectrum published" is a reportable
  answer rather than a suspected outage.
- **massbank: the cross-DB direction real traffic uses.** The file documented MassBank → external ID; 34
  logged queries went the other way. `xdb_ids_to_spectra` takes a ChEMBL/PubChem list to spectra in one
  query on one endpoint, and both cross-DB examples now say the call needs `database=massbank` **and**
  `endpoint_name=primary` — 7 logged calls died in schema validation having passed `endpoint_name` alone,
  a shape the old example's bare `endpoint_name: primary` field plausibly taught.
- **massbank: `find_compound_by_name`**, the one legitimate text-search route (MassBank has no name→IRI
  index), and `mb:ac_instrument` — 100% coverage, the free-text instrument model behind the 49-value
  controlled `mb:instrument_type` — documented for the first time.

### Fixed

- **massbank: bare `REGEX` alternation silently returns 0 rows, and now has a gotcha.** A logged user
  searched `"fentanyl|sufentanil|alfentanil|…"`, got nothing, and concluded MassBank has no fentanyls; it
  has 44 matching compound nodes. Verified on `rdfs:label`: the two-argument
  `REGEX(STR(?n), "Fentanyl|Sufentanil")` returns **0**, and so does `"Fentanyl|Fentanyl"` — while the
  same pattern matches 30 as `"(Fentanyl)|(Sufentanil)"`, 30 with an empty third argument `""`, and 44
  with `"i"`. `LCASE()` does not rescue it. Two fixes, both verified: always pass a flags argument, or
  parenthesise every branch. Single terms, character classes and `.*`-anchored patterns are unaffected.
  This is Virtuoso engine behaviour rather than a MassBank fact — scoped to this file for now, but it
  plausibly affects every database on the endpoint.
- **massbank: the ChEMBL bridge was documented in a form that does not exist in the data.** The cross-DB
  example recorded its result as the bare accession `CHEMBL277474`, so an agent that knows ChEMBL's own
  RDF minted `http://rdf.ebi.ac.uk/resource/chembl/molecule/CHEMBL112` and got 0 rows with no error —
  exactly what the log shows. The relation graph's subjects are `identifiers.org/chembl.compound/…`.
  All four subject IRI templates (ChEMBL, ChEBI, PubChem, HMDB) were read off live triples and are now in
  `id_join_map.same_endpoint_joins`, with the wrong-form trap called out by name. The inverse predicate
  `tid:TIO_000021` (InChIKey as *subject*) also exists and is the more natural direction from MassBank;
  the file previously documented only `TIO_000020`.
- **massbank: the skeleton-matching advice was 75× slower than necessary.** `spectra_by_inchikey` told
  callers to use `STRSTARTS` on the 14-character InChIKey skeleton. On an identical 178-skeleton batch,
  both returning the same answer: `STRSTARTS`+`CONCAT` **80.7 s**, `BIND(SUBSTR(STR(?ik), 33, 14))` +
  `VALUES` **1.07 s**. The new `screen_inchikey_skeleton` example uses the fast form, and scopes the
  warning to the correlated multi-skeleton case — a single skeleton with a constant literal prefix has no
  `CONCAT` and is fine. Also measured: skeleton matching lifts 31 exact hits to 32 skeletons / 47 keys, so
  it recovers stereo variants, not an order of magnitude.
- **massbank: drifted and missing coverage figures.** `precursor_mz_value` is 80.0% (was "~81%"),
  `precursor_type_value` 78.4% (was "~79%"); the remaining AnalyticalMethods predicates now carry
  measured coverage. `mb:collision_energy` was described as free text but without the vocabulary — it has
  **769 distinct strings** across 95,772 spectra, in which `"10"` (3,594 spectra) and `"10 eV"` (2,276)
  are the same physical setting, so the exact-match attempts seen 17 times in the log silently miss most
  of their target. Entity counts, xref coverage (CAS 69.6% / PubChem 55.3% / ChemSpider 38.4%) and the
  2g co-tenancy probe were all re-run and reproduce; `graphs.co_hosted` now records the probe as clean on
  all three legs (type, entity, hub) rather than asserting it.

## [2.7.0] - 2026-08-12

The other half of 2.6.0, plus the failure mode that made the original bug hard to read. Deliberately no
`whatsnew` marker: 2.6.0's entry already tells a user that ChEMBL target lookups now find targets by
their own name, and they do not know or care which of the two tools they went through — a second
near-identical line would push a genuinely distinct item off the five-item list for no benefit.

### Fixed

- **`search_chembl_id_lookup` carried the same target-name bug, and now does not.** Its TARGET branch
  searched only the protein component's `skos:altLabel` while returning the target's own `rdfs:label` as
  `name`, so `"Aldehyde dehydrogenase"` returned 0 rows there even after 2.6.0 had made
  `search_chembl_target` return CHEMBL3542434 for it — two tools disagreeing about the same question.
  The branch is now an inner UNION over both name locations, with `cco:hasTargetComponent` confined to
  the synonym leg, so component-less targets are reachable too: `entity_type="TARGET"` on `"CCRF-CEM"`
  went from 0 rows to CHEMBL382. `cco:targetType` was added to that branch as a guard — without it the
  new leg would match any labelled entity and stamp it `entity_type="TARGET"`. Worth knowing when
  reading results: a cell line exists **twice** under different IDs, as a `cco:CellLine` entity
  (CHEMBL3307641) and as a CELL-LINE *target* (CHEMBL382); finding one is not finding the other.
- **`search_chembl_id_lookup` empty results now carry a `hint`**, on the same reasoning as 2.6.0's: a
  0-result is not an error and was indistinguishable from an outage. This tool stays exact on purpose —
  a predictable cross-entity front door is worth more than a clever one — so instead of a substring
  fallback the hint names the tools that do fall back (`search_chembl_target`,
  `search_chembl_molecule(mode='extract')`), and flags a narrowing `entity_type` when one was passed.
- **A gateway 5xx no longer tells the agent its query is too heavy.** 502/503/504 come from a reverse
  proxy, not from Virtuoso, so the SPARQL engine may never have seen the query — advising "add LIMIT" is
  then actively wrong. Observed 2026-08-12 on the ebi endpoint, where `ASK {}` and a one-IRI lookup
  502'd identically in ~0.1s seconds after the same queries had succeeded. The status code alone cannot
  say whether the backend is down or just dropped one request, so the liveness probe added in 2.5.3 is
  now used to ask: probe fails → the endpoint-down message and the circuit breaker, exactly as for a
  timeout; probe passes → a message saying the endpoint is up, this failure is specific to this request,
  and the right first move is to **retry once unchanged** rather than rewrite. A plain 500 is Virtuoso's
  own and is untouched — it keeps the query-weight advice and spends no probe. Logged as
  `sparql_status: "http_gateway"` (classified `server_error`, so it stays out of the MIE-trap counts).

Also documented, not changed: on a default cross-kind `search_chembl_id_lookup`, `has_more=true` can
mean an entire `entity_type` is missing from the page — the kinds are UNIONed and the limit applies to
the whole, so "Liver" at `limit=5` returns 5 TARGET rows and no TISSUE row although both exist. The
docstring now says so explicitly, since "no tissue named Liver" is exactly the kind of false conclusion
this release is about.

## [2.6.0] - 2026-08-12

<!-- whatsnew: 2026-08-12 | Target lookups in ChEMBL now find a target by its <strong>own name</strong> (<em>"aldehyde dehydrogenase"</em> used to return nothing at all), reach the 4,894 targets that have no protein component — cell lines such as <em>CCRF-CEM</em>, plus tissues and organisms — and fall back to a substring match when a single word like <em>"dehydrogenase"</em> finds no exact hit. -->

MINOR rather than PATCH: nothing was removed or renamed and no existing key changed meaning, but two
response keys are new (`match_mode`, `hint`) and the tool answers queries it used to answer with an
empty array — a widening of what the tool accepts, which is where the agent-pragmatic policy files
additive change.

### Fixed

- **`search_chembl_target` can now find a target by the name it returns.** It could not: a target's name
  lives on two different RDF nodes — the protein component's `skos:altLabel` (gene symbols, UniProt
  recommended names) and the target's own `rdfs:label` — and only the first was searched, while the
  second is what came back as `name`. So `search_chembl_target("aldehyde dehydrogenase")` returned an
  empty array although CHEMBL3542434 is named exactly "Aldehyde dehydrogenase"; that target carries no
  `skos:altLabel` at all, so component synonyms could never reach it, while `"ALDH2"` found it fine.
  The match block is now a UNION over both, still exact and case-insensitive.
- **4,894 ChEMBL targets were unreachable by any query at all.** The old WHERE clause required
  `cco:hasTargetComponent` outside any UNION, and 2,383 ORGANISM, 1,997 CELL-LINE, 294 TISSUE,
  62 NUCLEIC-ACID and others simply have no protein component — even though the `target_type` parameter
  advertises CELL-LINE/TISSUE/ORGANISM as valid filter values, so those filters could never match
  anything. The target-name leg of the UNION requires no component, so `search_chembl_target("CCRF-CEM")`
  now resolves CHEMBL382 (CELL-LINE) instead of returning nothing.
- **A single word now finds something.** When the exact pass finds nothing, one substring pass over
  target names runs as a fallback, labelled `match_mode: "substring"` in the response so a caller knows
  the results are looser and unranked. Exact-first is still the default and still the reason this module
  resolves names over SPARQL rather than the EBI REST index (token-OR ranking buries the intended entity
  — EGFR lands around rank 6 among orthologs and ligands); a pass that runs only on zero results and
  ranks nothing reintroduces none of that. Breadth is bounded in practice: "dehydrogenase", about as
  broad as a caller would plausibly type, matches 250 target labels, not thousands.
- **An empty result now says it is not an outage.** A 0-result is not an error, so a caller could not
  distinguish "no such target" from "the endpoint is down" — and on 2026-08-12 an empty target search was
  in fact read as a connectivity failure, because the ebi endpoint really was down that day for unrelated
  reasons. Empty responses now carry a `hint` that states plainly the query ran and returned nothing,
  names any `organism`/`target_type` filter that may have removed a real match, and suggests the input
  forms that resolve deterministically. `match_mode` is `"none"` when both passes came up empty.

Additive only: `match_mode` and `hint` are new keys; no existing key changed meaning, and every input
that worked before returns at least what it returned before.

Checked and NOT changed: `search_chembl_molecule` shares the same synonym helper but is structurally
immune — every *named* small molecule carries its own `rdfs:label` among its `skos:altLabel` values
(verified: zero exceptions), so searching synonyms alone already reaches all of them. The other
`search_*` wrappers (UniProt, PDB, Reactome, Rhea, MeSH) do not share this code path at all; they are
REST wrappers over `_rest_get` and never touch SPARQL.

## [2.5.3] - 2026-08-12

An availability release, written during a live RDF Portal outage and verified against it. Nothing about
the tool surface changed; what changed is what happens when the endpoint on the other side stops
answering — previously a 90-second silence and a message naming the wrong cause, now a ~13-second
error naming the right one.

### Fixed

- **A SPARQL endpoint that is DOWN now fails in ~13s with a message that says so, instead of hanging
  the full 90s and blaming the query.** Observed during a total RDF Portal outage on 2026-08-12: TCP
  connect and the TLS handshake to `rdfportal.org/sib/sparql` both completed in 25ms, and then not one
  byte ever arrived. Nothing at the connect layer distinguishes that from a slow query, so
  `httpx.ReadTimeout` fired at 90s and the caller was handed the two-cause message — "your query is too
  heavy" or "the cache was cold" — when the truth was a third cause the message did not offer. Worse,
  the caller usually never read it: an MCP connector's own tool timeout expires well before 90s, so the
  user saw *no response at all*, and follow-up calls on that connector appeared dead too (the server
  itself stayed responsive throughout — verified in production, `get_MIE_file` returned in 0.24s
  immediately after a 90.97s SPARQL timeout on the same session, and again after a client-side abort).
  A read-level liveness probe now settles it: if a query is still running after 8s, `ASK {}` goes out on
  a **separate** httpx client with a 5s budget. No answer means the endpoint is dead, the query is
  cancelled, and the error explains that nothing about the query needs changing, names the affected
  endpoint, and points at the databases and REST tools that still work. Measured on the live outage:
  90.97s → 13.10s. The probe costs nothing on the fast path — a query that finishes inside 8s never
  triggers one — and when it *passes*, the existing two-cause message now says so explicitly, which
  keeps the cold-cache case (53.9–62.1s measured) on its full 90s budget.
- **One dead endpoint can no longer starve the healthy ones.** `_sparql_client` is a single
  `httpx.AsyncClient`, and httpx's default `Limits(max_connections=100)` is *global*, not per-host:
  with 110 queries parked on a dead endpoint, all 100 slots filled and a query to a different, healthy
  endpoint could not get a connection at all (measured). A 60s circuit breaker now refuses queries to an
  endpoint already found unresponsive — instantly, without opening a connection — and the pool-acquire
  wait is split out at 5s so exhaustion reports itself as this server's saturation rather than as a slow
  query. Connect timeouts (15s) are likewise reported as an unreachable host, not as a generic timeout.
- **An upstream outage no longer pollutes the MIE-trap statistics.** Every query issued during one used
  to log `sparql_status: "timeout"`, which `stats.py` counts in `TRAP_CLASSES` — so hours of failures no
  MIE edit could ever fix read as evidence that some MIE was wrong. Endpoint-level failures now log
  `endpoint_unresponsive` (classified `endpoint_down`) or `pool_exhausted` (its own class), and the
  probe verdict is recorded as `liveness_probe: passed|failed`.

Tool names, parameters and return shapes are unchanged; only failure timing and error text differ.

## [2.5.2] - 2026-08-08

No tool, parameter, or return shape changed — this is entirely MIE content plus one test. What makes
it worth a release is *how* the three MIE revisions were found, because two of the mechanisms are new
and neither is visible from inside a single file.

### Fixed

- **glycosmos, jpostdb: the FALDO glycosylation/phosphorylation-site route is now a worked example in
  both files.** Both described the chain in `schema_delta` prose only, and prose is what an agent has
  to re-derive under time pressure. Two separate live sessions did exactly that and got it wrong in two
  different ways. In glycosmos the reconstructed `PREFIX faldo:` lost its trailing `#`, which resolves
  `faldo:location` into a namespace that exists nowhere: the query parses, executes and returns **zero
  rows with no error** (116 rows with the `#`, 0 without). FALDO is shared vocabulary — `uniprot`,
  `ensembl`, `ddbj`, `hco` and `mogplus` all require the identical form, so this is not a per-database
  convention. In jpostdb the trap is arithmetic rather than syntax: there are **two** FALDO coordinate
  frames — a PeptideEvidence `faldo:begin` is protein-absolute, a Modification `faldo:position` is
  relative to its parent Peptide — and the two `ExactPosition` nodes are structurally identical,
  distinguishable *only* by what `faldo:reference` points at. Reading the modification position as
  absolute yields plausible small residue numbers that are simply wrong past the first peptide.
- **glycosmos: two examples had started returning zero rows, and three documented facts were false.**
  The `geneid` join node moved out of the `glycoprotein` graph into the `Rhea` graph, and `GO:0006486`
  was obsoleted upstream and vanished with no trace (re-anchored on `GO:0006487`). The `schema_delta`
  FALDO line was wrong on site IRI pattern, location IRI pattern, and both site figures. Saccharide
  inflation fell ×4.16 → ×1.52 because two `tmp/*` staging twins were dropped upstream, so the
  multiplier is now documented as reload-dependent rather than as a constant. The go.owl divergence
  recorded in 2026-07 has been **repaired** upstream and now agrees exactly with the native `go`
  database — kept as a dated observation, not deleted, because a snapshot that drifted once can drift
  again.
- **jpostdb: the `rdfs:label` trap covered only half the failure.** The file warned about empty-string
  labels, which a `FILTER` fixes. It did not warn that for the Unimod-typed population the predicate is
  **absent entirely**, which no `FILTER` can reach — a required (non-`OPTIONAL`) `rdfs:label` pattern
  silently zeroes the whole query. Measured across 12,518,574 modifications: 5,624,538 (44.9%) carry no
  label predicate, 5,206,460 (41.6%) carry `""`, 1,687,576 (13.5%) carry a real name. No Unimod-typed
  modification carries a label at all.
- **jpostdb: the "single-tenant, ZERO overlap" claim was true only for jPOST's own IRIs.** Re-probing
  found the endpoint now also carries ~40 `rdf.glycosmos.org/*` graphs, and the **hub** IRIs jPOST
  points at are re-declared: reading `rdfs:label` off a jPOST-referenced UniProt IRI returns ×2 rows
  (212 for 106 protein entries). Graph-pinning protects a database's own entities but not the join
  targets it follows outward — the pin has to go on every leg.

### Added

- **mogplus: `vep:symbol` and `vep:impact` are documented for the first time**, with two examples. This
  one came from the production tool-call log rather than a debugging session, and it is the first time
  that log has been read for *silent* failures instead of errors. Of 2,789 logged mogplus queries, 777
  (27.9%) returned zero rows — and every one entered through those two predicates, which the file did
  not mention once. The empties were deterministic per gene symbol (189 always empty, 720 always
  non-empty, zero overlap) and split into two causes a bare severity filter renders indistinguishable:
  the symbol is **absent** from VEP (532 queries, 117 symbols — mostly MGI QTL/locus names like `Aod4`
  and `Idd3` that have no transcript, so VEP never annotates them), or the symbol is **present with no
  HIGH/MODERATE variant** (245 queries, 72 symbols — a correct answer, not a failure; `Ebf1` carries
  50,916 annotations, all MODIFIER/LOW). The new `gene_symbol_impact` example returns the impact
  *distribution* so all three states are told apart in one query. Worse than the empties: the same
  template never pinned the release, so its ~2,000 **non-empty** results silently merged the disjoint
  v3/v2.1 cohorts (548 rows/21 variants unpinned vs 61/9 for v3), and never used `DISTINCT` against
  per-transcript fan-out (61 raw vs 26 distinct). Those results were not empty, they were wrong.
- **Drift guard for the Usage Guide's stale-tool-list row** (`tests/test_usage_guide_canaries.py`).
  That row names tools in two opposite roles and each can silently go wrong. Its **canaries**
  (`togovar_search_variant`, `search_chembl_id_lookup`) must exist — rename or remove one and it
  disappears from *every* client's tool list, so the row fires for everyone and tells healthy users to
  re-register, inside the document that is supposed to be authoritative. Its **phantom** examples
  (`find_databases`, `ncbi_ncbi_esearch`) must not exist — re-introduce one, say as a redirect stub,
  and the row cites a working call as evidence of breakage. Neither fails at build time today; the
  damage lands in someone else's chat session. Deliberately *not* asserted: that the canaries are the
  newest tools. A stale canary only under-detects (it catches caches older than itself and never
  misfires), so sensitivity stays a release-checklist judgement while correctness is enforced here.

## [2.5.1] - 2026-08-01

<!-- whatsnew: 2026-08-01 | <strong>ChatGPT users: refresh your connector.</strong> ChatGPT records TogoMCP's tool list when the connector is added and never refetches it, so tools added since then are invisible to it — re-run <em>Scan Tools</em>, or remove and re-add the connector. New databases are unaffected; those arrive through the live usage guide. -->

Documentation only — no tool, parameter, or return shape changed. What prompted it was reading the
production tool-call log: 28 calls in five days to tools that do not exist, **all** of them from
ChatGPT connectors (`openai-mcp`), and none from any other client family.

Both names were real once. `ncbi_ncbi_esearch` / `_esummary` / `_efetch` were valid until 2026-04-28,
when the redundant `ncbi_` prefix was dropped from the raw function names (mounted under `ncbi`, they
genuinely were `ncbi_ncbi_*`); `find_databases` was valid until the discovery trio was retired on
2026-07-24. The two caller populations share no IP, so these are two separate cache vintages — one of
them still in daily use three months after the rename. ChatGPT records the tool list at *Scan Tools*
time and does not refetch it.

The consequence worth acting on is the inverse of the errors: a client whose list is frozen also
cannot see tools added *after* it was cached, and there is no runtime channel that can fix that. New
**databases** are immune — the catalog is delivered by `TogoMCP_Usage_Guide` at query time, and
`database` is a free-form string validated server-side, so a stale schema neither hides nor blocks a
new database. New **tools** are not immune. Prefer a new database or a parameter on an existing tool
over a new tool where reach matters.

This also puts evidence behind the MAJOR-on-rename rule in [CLAUDE.md](CLAUDE.md): an agent cannot
recover from a rename because its *client* never refetches. Budget months of tail traffic on any name
that is removed or changed.

### Added

- **Usage Guide troubleshooting row for a stale client tool list.** Fires in both directions — a tool
  the guide names is missing from the model's tool list (canaries: `togovar_search_variant`,
  `search_chembl_id_lookup`), or a call returns "unknown tool". It instructs the model to tell the
  user to re-add the connector rather than retry the name or improvise a substitute, and states that
  databases are unaffected. The model is the only party that can see the discrepancy; the user is the
  only one who can fix it.
- **Connector-refresh note in the ChatGPT setup section of the intro page**, with the symptoms and the
  fix.
- **`TogoMCP_Usage_Guide` listed under Database &amp; Information on the intro page.** It had been
  missing since the tool shipped, despite being the third-most-called tool on the server.

## [2.5.0] - 2026-07-31

Two fixes found by using the KEGG tools rather than reading them: a seed form the
docstring itself advertised did not work, and a clean shutdown looked like a crash in
the client's log. MINOR rather than PATCH because the first adds two return fields.

### Fixed

- **A paralog-family member could not be used as a seed under its own name.**
  `kegg_pathway_neighborhood(pathway="hsa04151", seeds="AKT1")` returned `unresolved`, while
  `seeds="hsa:207"` — the same gene — resolved instantly and returned 33 downstream nodes. Box 17 of
  that map holds hsa:10000, hsa:207 and hsa:208 (AKT3/AKT1/AKT2), but KGML's `graphics/@name` carries
  only the DRAWN label, "AKT3" and *its* aliases, and seed resolution looked no further. So the
  paralog-family trap this tool advertises as solved was still open on the way IN, and
  `unresolved_note` compounded it by suggesting the gene might not be drawn on the map — it is drawn,
  under a sibling's name. Seeds and path endpoints that KGML cannot match are now looked up against
  KEGG's gene symbols and intersected with THAT MAP's members: one extra request per unmatched
  symbol, cached, and only on the path that would otherwise have returned nothing. `/find` is a
  substring search, so only rows carrying the symbol verbatim in their symbol list count — "AKT1"
  must not resolve through AKT1S1. When the fallback fires, `seed_resolution` /
  `endpoint_resolution` says which member matched and what the box is actually labelled, because
  every row of the answer then reads "AKT3" for a question asked about AKT1. `unresolved_note` now
  states that all three routes were tried and suggests retrying with a KEGG gene id.

- **A clean shutdown printed a 38-line traceback into the client's log.** The atexit hooks in
  `kegg.py` and `togoid.py` fell back to `asyncio.run(_client.aclose())` when no loop was running —
  which at interpreter shutdown is always — so a fresh loop reached into the already-closed loop that
  owned the sockets and raised `RuntimeError: Event loop is closed`. Harmless (exit code 0, stdout
  untouched, emitted after all work) but misleading: it is the first thing anyone debugging KEGG or
  TogoID would suspect. The hook now leaves the sockets to the OS, which reclaims them anyway. Fires
  only in a session that made at least one request through those clients.

## [2.4.1] - 2026-07-31

Four review rounds against the live KEGG API, all on `kegg_pathway_graph`'s response
reduction. Every fix below is a case where the tool returned something that looked like a
valid answer and was not: a graph whose edges pointed at absent nodes, a whole-metabolism map
with its `metabolic_gaps` silently gone, and a raised-cap call that returned less than the
defaults. Only the stdio + `TOGOMCP_ENABLE_KEGG=1` audience is affected; nothing here changes
the hosted tool surface.

### Fixed

- **Raising every `kegg_pathway_graph` cap returned a SMALLER graph than the defaults.** On hsa01100,
  `max_gaps=5000` let 1,555 metabolic gaps take 74% of the payload, so `nodes` fell to the 50-node
  floor — against the 191 nodes / 560 edges the same map returns at the defaults. No contract was
  broken (`max_*` are ceilings, not floors) but the tool did the opposite of what asking for more
  means, and `truncated.hint`'s advice to "raise max_nodes/max_edges/max_gaps" was actively wrong:
  the only move that bought graph was *lowering* `max_gaps`.
  The caps are ceilings on ONE shared response budget, and the supporting sections were reserving
  from it first. `nodes`+`edges` now take half the budget (`_GRAPH_BUDGET_SHARE`) before
  `metabolic_gaps`/`map_links` may spend any of it; the supporting sections are then count-capped as
  before and fitted into what remains, biggest-first. Same case now returns 138 nodes / 346 edges
  with 876 gaps. Default arguments are byte-for-byte unaffected (gaps are ~10% of the payload there,
  well inside the remainder), and a section cut for the reserve reports `capped_by: "size_budget"`
  rather than `"count"`, so the report never suggests raising a cap that is already maxed out. When
  the supporting sections hold enough budget to matter, `hint` now says to lower `max_gaps` and gives
  the byte split instead of the generic advice.
- **`kegg_pathway_graph` could return edges whose endpoints were not in `nodes`.** Under a raised
  `max_nodes` on a whole-metabolism map, 18 of 50 returned edges (and in a synthetic reproduction all
  50) referenced node ids that had been trimmed away, so the caller could not resolve a single
  endpoint — while 878 of 891 returned nodes appeared edgeless on a densely connected map. Both are
  wrong ANSWERS rather than small ones, and neither looks like an error: "this map is nearly
  disconnected" is a plausible reading of the second.
  The cause was reducing `nodes` and `edges` as two independent flat lists. The unit of reduction is
  now the NODE SET — a binary search finds the largest degree-ordered prefix whose INDUCED subgraph
  fits the budget, so every returned edge has both endpoints in `nodes` by construction, on every
  path (no cap, count cap, size cap). Verified across all six validation maps plus both capped cases.
- **`metabolic_gaps` and `map_links` vanished from every organism global map at default arguments.**
  The byte budget was computed against each section's UNREDUCED size, so `edges` at its full 8,124-row
  cost (~370 KB) made the budget look exhausted and the supporting sections were zeroed — even though
  the actual response was 222 KB against a 250 KB cap, and the 100 gaps cost 11.5 KB. The gaps are
  this tool's headline output, and they were invisible precisely where they mean most. The budget is
  now computed on what is actually being returned, with the (already count-capped, ~22 KB) supporting
  sections reserved BEFORE the graph is fitted into what remains.
- **`capped_by` mislabelled an induced edge count as a size-budget trim.** Edges follow the node set,
  so when the node prefix is bound by `max_nodes` the edges are too; reporting that as `size_budget`
  told the caller to narrow the question when raising `max_nodes` is what actually helps. Edges now
  inherit the node limit's reason unless their own count cap bound them first, and carry an explicit
  `note` that they are the induced subgraph.
- **`truncated.section_bytes_if_complete`** replaces the previous backstop-only diagnostic and is now
  emitted whenever the graph is reduced, reporting what each of the four sections would have cost
  unreduced. That is what answers "why are there so few edges?" — the section that drove the
  reduction is otherwise invisible, since a section that merely occupied the budget has
  `returned == total` and nothing flags it.

- **Raised count caps could starve `kegg_pathway_graph` of its edges.** With
  `max_nodes=5000, max_edges=20000, max_gaps=5000` on a whole-metabolism map, `metabolic_gaps`
  (186 KB, 84% of the payload) consumed the size budget and `edges` came back as **0** — a pathway
  graph with no graph in it, which reads as "these molecules are unconnected" and is more dangerous
  than an error because it does not look like one.
  This was the swing back from the previous fix: a "gaps first" drop order had thrown away all 25 of
  hsa00010's gaps to save 2 KB, and reversing it to "edges first" produced this. Neither fixed order
  is right, because the question is not which section is more precious. The backstop now works in two
  TIERS — supporting detail (`map_links`, `groups`, `metabolic_gaps`) is spent before the graph
  itself (`edges`, `nodes`), which additionally keeps a floor of 50 rows — and **within a tier the
  BIGGEST section goes first**, so the section that occupies the budget is the one that gives it back
  instead of a small section being zeroed for nothing.
- **The truncation report no longer hides the section that caused the truncation.** `truncated` now
  carries `reasons` (a list, so a count-cap trim and a size-backstop firing are distinguishable
  rather than collapsed into one string), `capped_by` per section (`"count"` / `"size_budget"` /
  `null`), and `section_bytes` when the size backstop fires. Previously the section that ate the
  budget was the only one absent from the report — it had `returned == total`, so nothing flagged it,
  and "why are there so few edges?" was unanswerable from the response.

- **`kegg_pathway_graph` could exceed the 1 MB MCP transport limit, so the caller got nothing.**
  `_bounded` only *labelled* an oversized dict — it set `payload["truncated"]` and then serialized
  everything anyway — so the size cap was decorative for all four dict-returning KEGG tools. A
  whole-metabolism map (`hsa01100`: 6,382 nodes, 8,124 edges, 2,073 metabolic gaps) blew past the
  transport limit, and because the rejection happens at the transport layer the caller received not
  even the truncation note meant to help it recover. The dict branch now really shrinks, dropping
  named sections in priority order and reporting `{returned, total}` PER SECTION while `stats` keeps
  describing the whole map.
- **The same fix exposed two bad calls of my own.** The first drop-order sacrificed `metabolic_gaps`
  first — throwing away all 25 of hsa00010's gaps to save 2 KB, i.e. the tool's unique answer to
  protect the bulk. And the 90 KB cap, inherited from a row-listing tool, was far too tight for a
  graph: it was firing on ORDINARY maps and cutting hsa05200 from 311 edges to 43. Graph payloads now
  get their own 250 KB cap (still ~60k tokens, well under the 1 MB transport limit) and drop
  bulkiest-and-tunable first, unique-and-cheap last. All six validation maps now return complete,
  untruncated graphs. New `max_gaps` caps gaps at the source, with the true count always in
  `stats.metabolic_gap_count`.
- **Two false statements in the KEGG docstrings**, both found by testing rather than review:
  global/overview maps like `01100` were said to have no KGML — they do, they are just enormous; and
  the glycolysis example claimed `C00031 → C00022` works at `max_length` 12, which was measured on
  `ko00010` and written up as "glycolysis". On `hsa00010`, C00031 (D-Glucose) is an ISOLATED node and
  returns nothing at any length; the chain starts at C00267 (alpha-D-Glucose). The example is now the
  measured one, and `kegg_pathway_paths` reports `isolated_endpoints` so a degree-0 endpoint is no
  longer indistinguishable from "just far away".
- **`kegg_pathway_paths` wasted its `max_paths` budget on enzyme detours** — a catalysis edge lets a
  route bypass the enzyme box over the identical reaction sequence, which is the same chemistry drawn
  differently. Routes repeating a reaction sequence are now collapsed and counted in
  `enzyme_detours_collapsed`; genuinely different reactions between the same pair stay distinct.
- **`kegg_find` now returns `entry_id`** (prefix-stripped) alongside the verbatim `entry`, matching
  `kegg_conv`. The identifier-form policy for all four ID-returning tools is stated once, in the
  module docstring, instead of being scattered and mutually inconsistent.

## [2.4.0] - 2026-07-31

### Added

- **KEGG, as an OPT-IN `stdio`-only tool group** (`kegg_find`, `kegg_get_entry`,
  `kegg_pathway_graph`, `kegg_pathway_neighborhood`, `kegg_pathway_paths`, `kegg_pathway_cycles`,
  `kegg_link`, `kegg_conv`). Requires BOTH the local stdio server AND `TOGOMCP_ENABLE_KEGG=1`;
  off by default so a non-academic user can install and run TogoMCP without being handed an API
  they may not be entitled to call — an AI assistant will use any tool it can see, and eligibility
  is the user's to assert. The two gates answer different questions and compose with AND:
  the transport gate (structural, not configurable) keeps the public host away from KEGG entirely,
  and the opt-in records eligibility. Mounted by `togo-mcp-local` and
  **structurally absent from the HTTP server** — the KEGG API is licensed to academic users at
  academic institutions, and serving it from a public host that cannot verify a caller's affiliation
  would need an academic service-provider license. The gate is a `setup(local=True)` argument, not an
  env flag, deliberately: `deploy.sh` forwards env vars by a fixed list, and a knob missing from that
  list is silently inert in production — that failure happened twice in one week (2026-07-29), both
  times with a green test suite. A licensing boundary must not be one forgotten list entry away from
  opening. `TOGOMCP_ENABLE_KEGG` does not weaken this: it is ANDed BEHIND the transport gate (so it
  has no effect on the HTTP path at all — `deploy.sh` never enters the picture) and it is
  **fail-closed**, since absent/empty/misspelled all mean OFF. The forwarding hazard is about a knob
  whose absence leaves a boundary OPEN; this one's absence closes it. It is deliberately NOT added to
  `compose.yaml`/`.env.example`/the `deploy.sh` lists, which would only imply it does something there.
- **KGML parsed into a signed directed graph** (`togo_mcp/kgml.py`, pure/stdlib-only, 39 tests, no
  network). This is the point of carrying KEGG at all: RDF Portal cannot answer "does A activate or
  inhibit B" in the form KGML states it. (Reactome RDF *does* carry signed regulation — 61,819 BioPAX
  `controlType` statements — but the sign is on a REACTION, so MDM2's repression of p53 is stored
  there as ACTIVATION of "MDM2 ubiquitinates TP53"; KGML states the between-molecule outcome
  directly.) Raw KGML is never
  returned — it is coordinate-heavy XML whose edges reference drawing-box ids, not genes.
  Eight distinct traps are resolved, six from the DTD and **two found only by running real maps**
  (both invisible in edge counts, visible only in connectivity): one entry box is a whole paralog
  family (a naive parse drops 23–76% of identifiers); complexes are indirection nodes; an `ECrel`
  edge's compound `@value` is an *entry id*, not an accession; cross-map pointers are not
  interactions; a `<reaction>`'s `@id` is its *enzyme's* box; rendering-only entries are not
  molecules; **the enzyme and compound layers are never joined by KGML** (so a metabolic map parses
  disconnected by construction — bridged with explicit `catalysis` edges); and **one molecule is
  drawn several times with different ids** (hsa05200: 54 duplicate drawings, 49 → 32 components once
  merged).
- **`metabolic_gaps` — the steps an organism cannot perform.** In an organism map KEGG keeps the
  reference layout and leaves the missing steps as bare `ortholog` boxes. These are a *result*, not a
  parse failure, and are reported as such. Confirmed arithmetically, twice, counting entry boxes:
  `ko00010` reactions 63 − `hsa00010` 34 = 29 = hsa00010's isolated ortholog boxes (and 63 − 35 = 28
  for `eco00010`). Under the default duplicate-merge these become 25 and 23 — the count of *distinct*
  missing steps rather than boxes, which is the biologically meaningful number.
- **Feedback-loop detection (`kegg_pathway_cycles`) and signed route enumeration
  (`kegg_pathway_paths`).** A directed cycle *is* a feedback loop, and the product of its edge signs
  says whether it is negative (self-limiting) or positive (self-reinforcing, switch-like) — a
  structural claim about a pathway that no keyword search surfaces and that RDF Portal cannot answer.
  Two traps are handled rather than left to the caller. `find_paths` returns an empty list both when
  an endpoint matched nothing and when the endpoints are fine but unconnected, so the tool resolves
  the endpoints itself and reports `unresolved` separately from `no_path_note`. And the
  `feedback` filter necessarily runs AFTER the `max_cycles` cap, so a filtered-empty result under a
  reached cap is not a real zero — `truncated` says so explicitly.
  On METABOLIC maps `max_length` must be raised: compounds are joined through their enzyme, so the
  hop count is about double the reaction count (glucose → pyruvate in glycolysis needs ~12, not the
  default 6).
- **Fixed: parallel reactions collapsed into identical path rows.** `find_paths` projected each edge
  without its reaction accession, so two genuinely different reactions joining the same pair of
  metabolites produced byte-identical output — a caller saw one path apparently repeated, and the
  duplicates consumed the `max_paths` budget. The accession is now on every path edge (verified on
  ko00010: R00200 vs R00199, two pyruvate-kinase routes that had been indistinguishable).
- **`kegg_conv` as the bridge to RDF Portal.** KEGG identifiers do not resolve in `run_sparql`, so
  the tool returns prefix-stripped `source_id`/`target_id` alongside the KEGG-namespaced forms:
  genes ↔ UniProt / NCBI Gene / NCBI Protein, chemicals ↔ ChEBI / PubChem. The Usage Guide's Database
  Catalog now states this explicitly, since an agent that skips it will put `hsa:10458` into a SPARQL
  query and get zero rows.

### Changed

- **`kegg_pathway_cycles` no longer oversells what it can find, and says so in the payload.**
  Measured across the six-map validation set it returns **zero signed cycles**: hsa04151 has no
  cycles at all despite being 98% signed, hsa04010 and hsa05200 have 4 and 3, every one `unsigned`.
  The reason is not a parser defect — a KEGG map is a DRAWING of one process, not a complete
  interaction model, so a canonical loop routinely has an arm that is simply absent. On hsa05200
  `MDM2 -| TP53` is drawn (sign -1) but `TP53 -> MDM2` is not: TP53's six outgoing edges all go to
  downstream effectors, and the induction arm lives on another map, so p53/MDM2 cannot close at any
  depth. (Duplicate layout entries are a third cause, and that one the parser does fix — merging
  takes hsa05200 from 0 cycles to 3.)
  So an empty result means "not drawn as a closed loop on THIS map", never "no feedback exists". The
  tool now ships an `interpretation` block saying exactly that, because empty is the NORMAL outcome
  and the obvious reading of it is wrong. **For any signed claim, `kegg_pathway_paths` is the robust
  primitive** — its `net_sign` needs only a path, so it returns the MDM2 -| TP53 inhibition the cycle
  search cannot see.
- **Reversible-reaction 2-cycles are classified and excluded by default.** A reversible reaction
  A↔B is emitted in both directions and so IS a 2-cycle by construction, with no feedback meaning
  (82 of ko00010's 102 two-cycles). `find_cycles` now marks them `artifact:
  "reversible_reaction"`; only the unambiguous length-2 same-reaction case is marked, since a longer
  cycle over reversible steps can be real biochemistry. This is a small cleanup and is documented as
  one — 69 of ko00010's 5,001 cycles at depth 6 — not a rescue: cycle enumeration on a metabolic map
  is meaningless regardless, because such a map has no signed edges at all.
- **The Usage Guide is now transport-aware.** The guide is served by both transports, so the KEGG
  material first shipped in full to HTTP clients that have no `kegg_*` tools — six tools' worth of
  operating instructions for things they cannot call, led by a sentence asserting KEGG "is reachable".
  It is now split: the catalog keeps a short, transport-neutral note (KEGG is not an RDF Portal
  database, `database="kegg"` is invalid, and if you see no `kegg_*` tool then KEGG is unavailable —
  use `reactome`/`rhea` and do not report it as an error), while the operating detail lives in
  `usage_guide_v6/local_only/kegg.md` and is appended only where the tools are actually mounted.
  The gate reads the LIVE tool registry rather than a flag, so the guide cannot disagree with what
  the server exposes, and the part files sit in a subdirectory that the guide's top-level `*.md`
  glob cannot reach by accident.
  The first attempt at that gate was wrong in a way worth recording: it assumed `mcp.get_tool()`
  RAISES for an unknown tool, when it returns `None`. The condition was therefore always true and
  every HTTP client still got the stdio-only section — the exact bug the change existed to prevent.
  Both halves are now pinned by tests that fail if the two transports stop differing.

### Notes

- Every `kegg_*` tool reports **how much of a map is actually signed**
  (`signal_quality.signed_edge_fraction`) next to any sign it returns. The fraction swings from 0.98
  (hsa04151) to 0.40 (hsa04010) to 0 (metabolic maps), because most KGML relations record a
  *mechanism* (`phosphorylation`, `binding/association`) without saying whether the effect activates
  or inhibits. A `net_sign` of 0 means UNKNOWN, never "no effect" — without that number an agent
  over-reads the graph.
- The 3 requests/second KEGG cap is enforced by a **process-wide** limiter, not a per-tool one, and
  KGML is memoized in-process; HTTP 403/429 is surfaced as a licence/rate signal and is never retried.
- No MIE file and no `endpoints.csv` row: KEGG has no SPARQL endpoint, and the MIE format describes a
  SPARQL schema. `database="kegg"` is invalid on `run_sparql`/`get_MIE_file` and stays that way.

## [2.3.0] - 2026-07-31

<!-- whatsnew: 2026-07-31 | New database: the <strong>NHGRI-EBI GWAS Catalog</strong> — 955,930 SNP–trait associations across 89,981 studies, with p-values, effect sizes, risk alleles and mapped genes, joinable to EFO trait terms. Ask things like "which variants are associated with QT interval, and how strong is the evidence?" -->

### Added

- **`gwascatalog` — the NHGRI-EBI GWAS Catalog, the 37th database.** Published genome-wide
  association results: 955,930 SNP–trait associations (801,096 at genome-wide significance) over
  444,106 SNPs, 89,981 studies and 11,017 EFO traits. It sits on the `ebi` endpoint we already talk
  to, so this is a registry row plus an MIE — no new infrastructure.
  Picked from the production tool-call log rather than by guesswork: with the ~94% of traffic that is
  a load-test harness and one automated pipeline filtered out, the largest remaining usage cluster is
  disease-variant work chaining `clinvar` → `togovar` → `medgen` → `mondo` → `hco` → `hgnc`, and
  trait association is the layer that thread was missing.
  The MIE ships 10 live-verified examples (4 basic, 3 intermediate, 2 aggregation, 1 cross_db) and
  documents three traps an agent cannot recover on its own. **The two vocabularies in the graph store
  string literals in opposite term forms** — `gwas:has_snp_reference_id` needs `^^xsd:string` while
  `m2r:snps` needs the plain form, and `DATATYPE()` reports `xsd:string` for both, so only an `ASK`
  tells them apart; getting it backwards returns 0 rows silently. **Two parallel association models**
  coexist: 955,930 med2rdf blank-node `Association`s carrying the flat row, versus 782,879
  IRI-addressable OBAN `TraitAssociation`s — different populations, and mixing them double-counts.
  And **`?s a gwas:Study` returns 224,583 across two disjoint IRI families**, of which only 89,981 are
  real GCST study records; the rest are EBI `Trackable/*` publication stubs.
  Trait labels live only in the co-hosted `ontology/efo` graph, so the `cross_db` example is the
  route to trait names, not a nicety.

### Changed

- Adding a database is now documented as touching **five** files, not one: `endpoints.csv`, the MIE,
  the regenerated `02b_database_catalog.md`, the **hand-written** endpoint table in
  `02_budgets_and_discovery.md` (no generator touches it — two `TestUsageGuideEndpointTable` tests
  are what catch a miss), and the intro page's database grid. The README's **Contributing** section
  now lists all five with the guarding test for each; it previously said two, which is how three of
  them got missed on the first pass of this very release. A *removal* really is just the registry row.

## [2.2.1] - 2026-07-30

### Added

- **`GET /stats/log` — download the raw JSONL tool-call log, linked from the top of `/stats`.** The
  dashboard's tables are lossy roll-ups, and the failures worth finding tend not to be the ones already
  tabulated: 2.2.0 came out of reading the raw log directly, where a 62% zero-row rate on one tool and a
  single repeated dead-end query shape were plainly visible while every pre-computed table showed them as
  unremarkable traffic. This makes that escape hatch a link instead of an SSH session.
  Serves the *same* files `compute_stats` aggregates — active plus every rotated sibling, concatenated
  oldest-first — so a download is verifiably the input the dashboard's numbers came from; serving only the
  active file would silently under-report against the tables above it. Streamed in chunks rather than read
  into memory (the log reaches ~550 MB across rotations), with `X-Log-Bytes`/`X-Log-Files` headers and no
  `Content-Length`, since rotation can change the real length mid-stream.
  Behind the **same HTTP Basic gate as `/stats`**: 503 when `TOGOMCP_STATS_USER`/`TOGOMCP_STATS_PASSWORD`
  are unset (never an unauthenticated fallback), 401 without valid credentials, 404 when no log exists.
  The served path comes from `TOGOMCP_QUERY_LOG` only — nothing is caller-supplied, so there is no
  traversal surface. Documented in `log_file_specs.md`.
  Still PATCH: the semver policy scopes the public contract to the *tool surface* (tool names, parameters,
  return shapes), and this adds no tool and changes no return shape.

### Fixed

- **A 60s SPARQL timeout sat inside the endpoints' cold-cache band, so valid queries failed by chance.**
  RDF Portal endpoints charge a large penalty on the *first* touch of an entity's index pages. Measured
  on the SIB endpoint across five never-queried UniProt accessions, a **minimal** single-protein lookup
  (one IRI, `LIMIT 5`) took **53.9–62.1s cold and 0.2s warm**. The client ceiling was exactly 60.0s —
  inside that spread — so whether a perfectly good query succeeded was a coin flip. Two such lookups
  timed out in production on 2026-07-27. Raised to **90s**, which clears the observed cold maximum with
  headroom while still cutting off genuinely runaway queries.
  Raising the ceiling is the fix precisely *because* retrying is not: an **aborted** query does not warm
  the cache (verified — abort at 20s, retry still 55.3s), so only a query allowed to *complete* pays the
  cost once on behalf of every query after it.
- **The timeout message diagnosed the wrong cause and forbade the one thing that would have worked.** It
  asserted "the query is likely too heavy", told the caller to add `LIMIT` and narrow with specific IRIs,
  and ended "Do not retry the same query without changes" — advice that is impossible to follow for a
  query that is *already* a single IRI with `LIMIT 5`. The logs show an agent obeying it faithfully:
  it simplified a 26-predicate query down to 8 predicates and timed out again 74 seconds later. The
  message now names both causes, says which is likelier, and permits exactly one retry rather than
  banning it outright — while keeping the narrow-it guidance, which remains correct for genuinely heavy
  queries (the same log's MassBank timeout is a 4-way `mb:has_peak` self-join, and that advice fits it).

## [2.2.0] - 2026-07-30

<!-- whatsnew: 2026-07-30 | Drug lookups in ChEMBL now find <strong>biologics</strong> — antibodies, therapeutic proteins, vaccines and cell therapies were silently missing, so names like <em>Rituxan</em> or <em>efalizumab</em> returned nothing. A new <code>mode='extract'</code> also resolves the drugs named inside a clinical-trial intervention string such as "Ropivacaine 10% + Clonidine". -->

Found by reading the production tool log rather than by a bug report: over three days,
531 of 854 `search_chembl_molecule` calls and 341 of 351 ClinVar `run_sparql` calls
returned zero rows. Two independent causes — one a real bug, one a documentation gap
that made an LLM reproduce the same bug in hand-written SPARQL.

### Added

- **`search_chembl_molecule(mode='extract')` — resolve drugs NAMED INSIDE a string.** Exact synonym
  matching cannot resolve a clinical-trial intervention string, a dosed/formulated product, or a
  multi-drug regimen, because none of those *is* a synonym: `"Ustekinumab 90 mg"`, `"Diclofenac SR"` and
  `"Ropivacaine 10% + Clonidine 1 µg/kg"` all return zero rows under exact matching. These were **420 of
  the 531** zero-row `search_chembl_molecule` calls in the 2026-07-27..29 logs. The new opt-in mode finds
  every substance named inside the string and recovers **239 of the 420** (measured end-to-end through the
  tool, 0 errors).
  Nested synonyms collapse to the longest match, so `"Sofpironium Bromide Gel"` yields SOFPIRONIUM BROMIDE
  and not also the bare counter-ion BROMIDE, while genuinely distinct components all survive
  (`"Cisplatin, Vinblastine, Temozolomide"` → all three). Each result carries `matched_span` and
  `match_type` (`exact` | `contained`) so a caller can tell a derived hit from a real one.
  **Exact remains the default and is byte-for-byte unchanged** — this is a retry path, not a relaxation of
  the existing contract. It is a text-extraction heuristic: measured false-positive rate ~1% (2 of 239, both
  a plausible component picked out of a compound name), and it resolves a regimen to its *components*, so
  it will never return "FOLFIRI" itself.
  The remaining **181 terms are a genuine floor** — placeholders (`"Treatment A"`), procedures
  (`"Sonoporation"`), sponsor codes ChEMBL does not carry (`BIIB023`, `VK-2019`), and vaccines
  (`Synflorix`). No string technique reaches them.
- **Zero-result returns now explain themselves.** An empty `search_chembl_molecule` result was
  indistinguishable from "not in ChEMBL". Both modes now attach a `note` naming the likely cause and the
  next step (exact → suggests `mode='extract'` for a decorated string; extract → names the regimen /
  procedure / placeholder / absent-sponsor-code cases).

### Fixed

- **ChEMBL name and structure lookups silently dropped every biologic.** `search_chembl_molecule` and the
  COMPOUND branch of `search_chembl_id_lookup` constrained matches to `?m a cco:SmallMolecule`. ChEMBL's
  substance tree roots at `cco:Substance` (`SmallMolecule` | `Biological` | `UndefinedSubstance`), so
  antibodies, therapeutic proteins, vaccines, oligos and cell therapies matched the synonym but failed the
  type check and returned zero rows — no error, just an empty result that reads as "not in ChEMBL".
  `efalizumab`, `Rituxan`→RITUXIMAB, `Nivolumab` and `filgrastim` were all unreachable by name; the
  InChI/InChIKey path was hit too, where ~940k substances carry a key but are typed `UnknownSubstance`,
  `ProteinMolecule`, `Oligonucleotide` or `Oligosaccharide` rather than `SmallMolecule`.
  All three sites now match any drug-substance type. Found in the 2026-07-27..29 production tool logs
  (531 of 854 `search_chembl_molecule` calls returned zero rows); replaying the distinct failing terms
  against the widened type set recovered **110 real drugs**. The remainder are clinical-trial intervention
  strings ("Modified FOLFOX6", "Ustekinumab 90 mg") that exact synonym matching is not meant to resolve.
  `cco:TargetComponent` stays excluded so protein targets don't leak into molecule results.

### Changed

- **ChEMBL MIE: the same `cco:SmallMolecule` trap was in the *guidance*, not just the code.** The
  `name_resolve` example's `traps_avoided` prescribed `?m a cco:SmallMolecule ; skos:altLabel ?alt` as the
  brand/synonym→molecule idiom — so an LLM following the MIE reproduced the bug the code fix removed, and
  there was no worked example for molecule name resolution at all. Added `molecule_name_resolve` (Rituxan,
  Humira, Keytruda, Lipitor → 3 antibodies + 2 small molecules in 0.15s) with the counterfactual recorded:
  pinning `cco:SmallMolecule` cuts the same query from 5 rows to 2. `xdb_chebi` carried the pin too and was
  under-answering its own "approved drugs" question by 56 substances; the pin is redundant there
  (`moleculeXref`/`highestDevelopmentPhase` are molecule-only) and is now gone. `entity_counts` gained
  `drug_substances: 2,878,135` — the file previously reported only `small_molecules: 1,920,603`, which
  reads as the size of ChEMBL and hides 33% of it.
- **ChEMBL MIE: `xdb_chebi`'s `verified` block was stale.** Its recorded `first_row` (ABACAVIR, dated
  2026-07-22) no longer reproduces — re-running the *original* query verbatim today returns
  2-MERCAPTOETHANESULFONIC ACID first, so this is upstream drift rather than a consequence of the type-pin
  removal. Re-verified and re-dated, with that distinction noted inline.
- **ClinVar MIE: new `sig_by_gene` example, and a warning off the `TypeAlleleDescr` dead end.** The
  per-gene significance breakdown — the composition of the gene pin and the classification walk — had no
  worked example, and the plausible-looking shortcut through `cvo:TypeAlleleDescr` +
  `cvo:clinical_significance` returns zero rows with no error for essentially every gene: of 26,161
  `TypeAlleleDescr` nodes only 280 carry `clinical_significance`, and those 280 cover **BRCA2 and BRCA1
  only**. That shape accounted for 340 of 341 zero-row ClinVar queries in the same production logs. The
  correct route (via `cvo:classified_record`) answers the EGFR case in ~0.3s and now ships as a verified
  example with the trap recorded in its `traps_avoided`.

## [2.1.3] - 2026-07-30

### Fixed

- **Claude setup guide: wrong settings path, and Team/Enterprise had no route at all.** Verified against
  Anthropic's custom-connectors article (which, unlike OpenAI's help centre, is fetchable and carries an
  "Updated" date). Three corrections: the path is **Settings → Customize → Connectors → "+" →
  "Add custom connector"**, not "Settings → Connectors" with a button "at the bottom of the page";
  **Team and Enterprise require an owner to add the connector organization-wide first**
  (Organization settings → Connectors → Add → Custom → Web) and members cannot self-add before that, so
  the omission stranded every Team/Enterprise user; and custom connectors are available on **all plans**
  including Free (capped at one) rather than paid-only as the heading implied — also on Cowork, not just
  Claude and Claude Desktop.
- **Method 2 reframed honestly.** The `claude_desktop_config.json` + `npx mcp-remote` recipe is a
  community bridge, not an Anthropic-documented path — the article states that file is for genuinely
  local MCP servers. It is now marked optional, with the note that Method 1 covers every plan, which
  removes its original "for people without a paid plan" rationale.

## [2.1.2] - 2026-07-29

### Fixed

- **Setup guide: the "Gemini CLI" tab documented a retired product with the wrong config key.** Google
  retired Gemini CLI on **2026-06-18** for the free tier, Google AI Pro, Ultra and Google One,
  replacing it with **Antigravity CLI**; it survives only for Gemini Code Assist Standard/Enterprise,
  Google Cloud access, and paid Gemini API keys. The page had carried the old instructions for six
  weeks. Worse, the two are not interchangeable and the mismatch fails *silently*: Antigravity reads
  `~/.gemini/config/mcp_config.json` and requires `serverUrl`, and its docs state that "legacy fields
  like `url` or `httpUrl` are not supported" — while the page showed `settings.json` with `httpUrl`.
  Anyone who followed it got a connector that never connected, with no error explaining why.
  The tab is now Antigravity-first with Gemini CLI as a footnote for the plans that still have it.
- **Setup guide links now point only at first-party docs.** The Gemini tab linked `geminicli.com`,
  one of several unofficial mirrors (`gemini-cli.xyz`, `geminicli.cloud`, `geminicli.work`). It returns
  200 and looks authoritative, which is precisely the hazard — it was still serving Gemini CLI
  instructions six weeks after the product was retired. Replaced with `antigravity.google/docs/mcp`
  and `google-gemini.github.io/gemini-cli/docs/`.

## [2.1.1] - 2026-07-29

### Fixed

- **ChatGPT setup guide: the plan tiers are now stated, and stated correctly.** 2.1.0 removed the tier
  claim on the grounds that sources disagreed irreconcilably. They didn't — the disagreement was between
  a dated, authoritative source and an undated stale one. OpenAI's help-center article (revised
  2026-07-28) is unambiguous: Business/Enterprise/Edu get full MCP and an admin must *publish* the app;
  **Pro is read/fetch only**; **Plus cannot use custom MCP connectors at all**. The
  `developers.openai.com` guide the page had been pointing at claims all five tiers get full read+write,
  and is wrong on both Plus and Pro; it carries no date or changelog, which is what made its staleness
  invisible. Note the help-center article is Cloudflare-blocked to WebFetch *and* to curl with a browser
  UA, so it can only be checked by a human in a browser — a 403 there is not a dead link.
  Stating the tiers matters: a Plus user following the old steps would simply fail with no explanation.
  Also corrected the menu path (**Settings → Apps**, not "Apps & Connectors"), added the Scan Tools and
  admin-publish steps, and noted that Developer Mode is web-only.

## [2.1.0] - 2026-07-29

<!-- whatsnew: 2026-07-29 | All tools now declare themselves <strong>read-only</strong> in the MCP protocol, so clients such as ChatGPT no longer treat every query as a write action needing confirmation. -->

### Added

- **All 29 tools now declare `readOnlyHint`** (plus `openWorldHint`) in their MCP annotations.
  TogoMCP has always been read-only — every tool is a query, search or ID conversion, and nothing
  writes to a database — but that was stated only in prose, and MCP's default for an *unannotated*
  tool is the unsafe one. OpenAI's ChatGPT developer-mode docs are explicit that "tools without this
  hint are treated as write actions", so an unannotated read-only server draws a confirmation prompt
  on **every** call and can be refused outright by a plan that only permits read/search connectors.
  Claude and other clients use the same hint to decide what may be auto-approved. `destructiveHint`
  and `idempotentHint` are deliberately left unset — the spec defines both as meaningful only when
  `readOnlyHint` is false. A test guard fails the build if a new tool omits the annotation, since the
  failure is otherwise invisible.

### Changed

- **ChatGPT setup guide no longer states a plan-tier list.** The page claimed Developer Mode was
  available to "Plus, Pro, Business, Enterprise, or Edu". Checking that against sources found three
  mutually inconsistent accounts — OpenAI's own developer guide says all those tiers with full
  read+write, secondary write-ups say Plus/Pro are read-only, and user reports exclude Plus
  entirely — with the authoritative help-center article Cloudflare-blocked to any automated check.
  Developer Mode is a staged-rollout beta, so the tier matrix is genuinely unstable. The page now
  links to OpenAI's guide for eligibility and states what settles it regardless: TogoMCP needs only
  read access, so a plan limited to read/search connectors runs it in full.

## [2.0.2] - 2026-07-29

### Fixed

- **The 2.0.1 proxy fix did not work in production — two reasons, both mine.** It shipped, deployed,
  and the `https://` → `http://` redirect downgrade persisted unchanged.
  1. **Wrong address range.** `forwarded_allow_ips` defaulted to `172.16.0.0/12`, derived from
     `compose.yaml`. But Compose is not the production path — `scripts/deploy.sh` is, and it runs
     **rootless podman with slirp4netns** on vs94, where the rootlesskit port handler SNATs every
     inbound connection to the container's own slirp address `10.0.2.100`. Not in the list, so
     uvicorn kept discarding `X-Forwarded-Proto`. The default now covers all three runtimes we
     deploy on: `10.0.2.0/24` (rootless podman), `10.88.0.0/16` (rootful podman), `172.16.0.0/12`
     (docker/compose).
  2. **The documented override could not reach the container.** `deploy.sh` forwards a fixed list of
     env vars and `TOGOMCP_FORWARDED_ALLOW_IPS` was not in it, so setting it in `.env` did nothing.
     Now forwarded, per-service, like every other knob.
  Both failures were silent — an untrusted `X-Forwarded-*` header is dropped, not rejected — and both
  came from treating `compose.yaml` as the deployment. Regression tests now assert the default trusts
  a slirp4netns peer and that `deploy.sh` forwards the override.
- **Corrected the rationale for not using `*`.** 2.0.1 argued a tight list protects the hashed peer
  IP in the tool-call log from forgery. On the rootless-slirp4netns path that field is *already*
  constant — every client arrives as `10.0.2.100` — so the tight list buys nothing there and the real
  protection is that only the proxy can reach the published port. The argument still holds on the
  rootful/compose paths, where the peer is the true client.

## [2.0.1] - 2026-07-29

<!-- whatsnew: 2026-07 | Published in <em>Database</em> — <a href="https://doi.org/10.1093/database/baag042" target="_blank" rel="noopener">2026:baag042</a>. -->

### Removed

- **`data/resources/structured_query_insight.md`** — a dead 2026-02 working note, referenced
  by no code and served by no tool, but shipped in every wheel and image via `package-data`.
  Its one idea (the specific IRI → `VALUES` → typed predicate → graph navigation →
  `bif:contains` → `FILTER(CONTAINS())` hierarchy) is already a line in the Usage Guide, and
  its "how to document this in an MIE" section still showed the pre-v3 `sparql_query_examples`
  skeleton. Removed because an unread file that contradicts the current format is a trap for
  whoever greps it next, not because of its size. Recoverable from git history.

### Fixed

- **Agent-facing docs now name the v3 MIE sections that actually exist.** The v3 release
  reshaped the MIE format but left the *instructions* pointing at v2 keys: the Usage Guide's
  "read in this order" list led with `critical_warnings` and included `shape_expressions`
  (ShEx was removed wholesale in v3), and `get_MIE_file`'s own description told the agent to
  check every predicate against `co_hosted_graphs`/`critical_warnings` — none of which appear
  in any of the 36 served files. Every session read that. Now points at `global_gotchas`,
  `graphs.co_hosted`, `examples` (+ per-example `traps_avoided`), `schema_delta` and
  `id_join_map`, and steers toward adapting a live-verified example over assembling a query
  from the schema. The trap-banner code was already format-agnostic, so served *behavior* was
  never wrong — only the guidance. Same fix applied to the disease-analysis, qa-generator and
  research-article-analysis skills.
- **UniProt MIE re-verified against the live endpoint (2026-07-29).** A UniProt release had landed
  since the file was authored, so every count it served was stale — reviewed Swiss-Prot 574,627 →
  575,503, and the `go_function`/`ec_class` example figures with it. Discovery also found six
  UniProt-owned graphs missing from the graph list (including `obsolete`, whose deleted entries the
  file's own gotchas already discussed) and a previously undocumented trap: `rdfportal.org/ontology/go`
  duplicates GO labels against UniProt's own `go` graph — the labels agree, so the duplicate reads as
  a legitimate multi-valued label and `DISTINCT` hides it, while the `subClassOf` sets differ. All 12
  examples re-executed live. Doubles as the TIER_C acceptance run for the v3 authoring tooling.
- **UniProt MIE: GO labels come from EIGHT graphs, not two.** The `go_label_duplication` trap added
  earlier in this cycle understated itself ×2 because it was derived from a single GO term. Measured
  across a real protein's annotations, an unpinned `?goTerm rdfs:label ?l` returns 238 rows for 70
  terms (~3.4x) — and two of the eight sources are UniProt's *own* `keywords` and `locations` graphs,
  so pinning "UniProt's graphs" does not fix it. Corrected, and now demonstrated by a new verified
  `go_label_pin` example rather than described in prose.
- **`get_sparql_endpoints` no longer advertises a nonexistent tool for MeSH.** The
  `keyword_search_api` column in `endpoints.csv` named `search_mesh_entity`; the tool is
  `search_mesh_descriptor`. All 36 rows were audited — this was the only bad value.
- **HTTPS scheme is no longer lost behind the reverse proxy.** uvicorn parses `X-Forwarded-*`
  by default but trusts only `127.0.0.1`, and the container is published as a host port — so the
  proxy arrives via the Docker bridge gateway and `X-Forwarded-Proto` was being discarded. The app
  therefore saw `scheme=http` and emitted absolute redirects that downgraded `https://` to `http://`
  (visible on the `/mcp/` → `/mcp` trailing-slash 307). `forwarded_allow_ips` is now passed through
  to uvicorn, defaulting to loopback + the Docker bridge range (`172.16.0.0/12`, since Compose
  allocates project networks unpredictably across it) and overridable via
  `TOGOMCP_FORWARDED_ALLOW_IPS` for a proxy on another subnet. Deliberately **not** `*`: the peer
  address is recorded (hashed) in the tool-call log, so blanket trust would let anyone able to reach
  port 8000 directly forge the logged IP. This is only half the fix — the proxy must also *send*
  `X-Forwarded-Proto` (dbcls/togomcp#175).

## [2.0.0] - 2026-07-24

<!-- whatsnew: 2026-07-24 | The database knowledge files (MIE) were rewritten to a leaner format — about half the size, with faster and more reliable query construction. The three database-discovery tools (<code>list_databases</code>, <code>find_databases</code>, <code>list_categories</code>) were consolidated into the built-in Usage Guide, which now carries a catalog of all 36 databases. -->

The MIE-format redesign (**v3**). A ground-up rewrite of every MIE around verified, executable
worked examples — the load-bearing query-construction content the 2026-07 ablations isolated —
collapsing the v2 format's 4× restatement (schema list + ShEx shape + worked query + sample triple)
into one atomic unit. All 36 served MIEs were rebuilt; the corpus is **50.9% smaller**
(1.57 MB → 770 KB). Validated as an equivalence gate over the full 100-question benchmark (×3, API
answering + judging): judge score flat within the declared ±0.5 margin (paired Δ **+0.29/20**, 95%
CI [−0.09, +0.68]), factoid correctness **up** (+1.0 on factoid questions), and measured runtime
**−15% input tokens / −15% cost / −6% latency**. Durable record:
`benchmark/studies/redesign/release/FINDINGS.md`.

MAJOR because the discovery trio is removed from the tool surface.

### Removed

- **`find_databases`, `list_databases`, `list_categories`** — the discovery trio. The full
  `database=` roster is already always on the `run_sparql` / `get_MIE_file` schema, and the
  descriptions/keywords/categories they served moved to a static, generated **Database Catalog**
  section of the Usage Guide. Removing them retires a whole class of "which tool tells me what
  exists" round-trips (agents can pick a database by reading the guide).

### Added

- **Database Catalog in the Usage Guide** — a build-time section listing all 36 databases (title,
  one-line description, keywords) grouped by category, generated from the MIE `discovery:` blocks by
  `scripts/generate_usage_guide_catalog.py` (`--check` / `--list-categories` modes), with a
  `test_catalog_in_sync` drift guard and a CI job (`catalog.yml`).

### Changed

- **Served MIE corpus flipped to the v3 format** (`togo_mcp/data/mie/*`) — same databases, new
  structure (`discovery` / header / `examples` / `schema_delta` / `id_join_map`), 29–65% smaller per
  file. No server-code change: the reader already handled both formats (`discovery`-or-`schema_info`,
  `global_gotchas`-or-`critical_warnings`).
- **Workflow STEP 0 is now a no-tool catalog scan** (was `find_databases(...)`) — updated in the
  `TogoMCP_Usage_Guide` docstring and guide parts 01/02/03.
- **Empirical budgets + tool tiers refreshed** from the v3 100-question run (optimal total tool
  calls 6–15 → 4–10; consecutive-SPARQL penalty 1.26 → ~1.1; `find_databases` removed from the tiers).

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

<!-- whatsnew: 2026-07-17 | Query results are more trustworthy: <code>get_MIE_file</code> now leads with each database's "traps" (mandatory filters, namespace pitfalls, and shared-graph count inflation), and all 36 databases document cross-graph co-tenancy so counts aren't silently inflated. -->

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

[Unreleased]: https://github.com/dbcls/togomcp/compare/v2.7.8...HEAD
[2.8.0]: https://github.com/dbcls/togomcp/compare/v2.7.8...v2.8.0
[2.7.8]: https://github.com/dbcls/togomcp/compare/v2.7.7...v2.7.8
[2.7.7]: https://github.com/dbcls/togomcp/compare/v2.7.6...v2.7.7
[2.7.6]: https://github.com/dbcls/togomcp/compare/v2.7.5...v2.7.6
[2.7.5]: https://github.com/dbcls/togomcp/compare/v2.7.4...v2.7.5
[2.7.4]: https://github.com/dbcls/togomcp/compare/v2.7.3...v2.7.4
[2.7.3]: https://github.com/dbcls/togomcp/compare/v2.7.2...v2.7.3
[2.7.2]: https://github.com/dbcls/togomcp/compare/v2.7.1...v2.7.2
[2.7.1]: https://github.com/dbcls/togomcp/compare/v2.7.0...v2.7.1
[2.7.0]: https://github.com/dbcls/togomcp/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/dbcls/togomcp/compare/v2.5.3...v2.6.0
[2.5.3]: https://github.com/dbcls/togomcp/compare/v2.5.2...v2.5.3
[2.5.2]: https://github.com/dbcls/togomcp/compare/v2.5.1...v2.5.2
[2.5.1]: https://github.com/dbcls/togomcp/compare/v2.5.0...v2.5.1
[2.5.0]: https://github.com/dbcls/togomcp/compare/v2.4.1...v2.5.0
[2.4.1]: https://github.com/dbcls/togomcp/compare/v2.4.0...v2.4.1
[2.4.0]: https://github.com/dbcls/togomcp/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/dbcls/togomcp/compare/v2.2.1...v2.3.0
[2.2.1]: https://github.com/dbcls/togomcp/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/dbcls/togomcp/compare/v2.1.3...v2.2.0
[2.1.3]: https://github.com/dbcls/togomcp/compare/v2.1.2...v2.1.3
[2.1.2]: https://github.com/dbcls/togomcp/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/dbcls/togomcp/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/dbcls/togomcp/compare/v2.0.2...v2.1.0
[2.0.2]: https://github.com/dbcls/togomcp/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/dbcls/togomcp/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/dbcls/togomcp/compare/v1.7.1...v2.0.0
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
