# MIE Structure — Per-Section Requirements (v3)

The authorable contract is `togo_mcp/data/docs/MIE_v3_spec.md`; this file is the
working companion to it. Where they disagree, **the spec wins** — read it first.

v3 has **five need-based parts**, not eleven author-function sections. Top-level
keys, in order:

| key | required | what it is |
|---|---|---|
| `database` | ✅ | the DB key (== filename stem == `SPARQL_ENDPOINT` key) |
| `discovery` | ✅ | the 4 catalog fields (title, description, keywords, categories) |
| `endpoint` (+ `base_uri`, `graphs`, `entity_counts`, `global_gotchas`) | ✅ endpoint/graphs | the header — provenance + database-wide truths |
| `examples` | ✅ | the load-bearing content — verified, executable atoms |
| `schema_delta` | optional | ONLY non-obvious predicates no example demonstrates |
| `id_join_map` | ✅ | stable anchors + cross-DB join paths |

The central design move: **one verified example replaces the ShEx shape, the
sample triple, and the annotated warning** it would otherwise be written as three
or four times (spec §1.2 — the `query` group alone recovers 99% of the whole-MIE
benefit; the restatement is dropped). Carry only what the model **cannot recover**
on its own (spec §4.3).

## 1. `database`

A single scalar: the DB key. Lowercase, matches the filename stem and the
endpoint-registry key in `endpoints.csv`.

## 2. `discovery` (required — kept SMALL)

The four fields a build-time generator rolls into the Usage-Guide catalog
(`scripts/generate_usage_guide_catalog.py`). It is the **source of truth for
cross-DB discovery** and is multiplied across the whole catalog, so keep it
minimal and uniform across DBs. It is **not** served per-request.

- `title`: short human title (e.g. `UniProt RDF`).
- `description`: **ONE tight sentence** — what kind of data, phrased for keyword /
  semantic matching. Not a paragraph.
- `keywords`: data-type / domain terms (lowercase), **not** entity names. Include
  synonyms a user might type (`mutation`, `polymorphism` alongside `variant`).
- `categories`: 1–3 coarse buckets. **Copy each token verbatim** — lowercase,
  underscores for multi-word (`drug_target`). Do not Title-Case, pluralize,
  space-separate, or invent variants. Print the corpus's canonical set with
  `uv run python scripts/generate_usage_guide_catalog.py --list-categories`; an
  off-spec token fragments the catalog into a single-DB bucket.

Moving or renaming these four keys requires updating whatever aggregates them
(the guide generator, and the server's `_load_databases_cache`).

## 3. Header — `endpoint`, `base_uri`, `graphs`, `entity_counts`, `global_gotchas`

Provenance and database-wide truths, served by `get_MIE_file`. Author it so the
header **stands alone** (spec §4.5 — a future `level=header` tier may serve it
without the examples).

- `endpoint`: SPARQL endpoint URL.
- `base_uri`: optional root namespace.
- `graphs`:
  - `primary`: the DB's own graph IRI — the **default pin target**.
  - `supporting`: list of same-DB graph localnames (optional).
  - `co_hosted`: `{name: "one-line note"}` — datasets sharing the endpoint. **MUST
    flag any that (a) inflate counts, (b) enable a direct cross-DB join, or (c) are
    empty stubs.** Populate from the Phase 2g union-inflation probe, never guess.
    On a multi-graph endpoint where 2g came back clean, record that explicitly
    (`probed_clean: "2g probe run YYYY-MM-DD — no re-declaration found"`) rather
    than omitting the field — a silent omission is indistinguishable from never
    having probed. Only a genuinely single-graph endpoint (currently just
    `supercon`) is exempt.
- `entity_counts` (optional): every value **`COUNT(DISTINCT)` + graph-pinned**,
  each with a `date:` (or a single global `verified:` date). This is where the
  "how big is this DB" answers live; also record the inflated unpinned `COUNT(*)`
  with a "never report" note when union inflation exists, so the trap is concrete.
- `global_gotchas`: the **2–5 that bite ANY query** on this DB (union inflation,
  a mandatory filter, absent labels, a timeout-prone path). Each is `{id, say}`
  where `say` states **what silently fails + the fix**. Query-specific traps do
  **not** go here — they ride inline on the example (`traps_avoided`, §4).

## 4. `examples` (required) — the core

Each example is self-contained, executable, verified, and dated. Fields:

- `id`: short slug.
- `intent`: one line — what this teaches.
- `question`: the natural-language question it answers.
- `complexity`: `basic` | `intermediate` | `advanced` | `aggregation` | `cross_db`.
- `endpoint_name`: the endpoint group (e.g. `sib`) — **only** for `cross_db`
  examples; omit for single-DB ones.
- `sparql`: a complete, runnable query (PREFIXes included; `LIMIT` where a row
  query could run away).
- `verified`: **REQUIRED** — a map of the actual live result plus `date:`
  (`{n: 108, date: "2026-07-22"}`). Re-run this pass. Use `date:`, **never `on:`**
  (YAML 1.1 parses the bare word `on` as boolean `true` — spec §4.1 trap); quote
  the date value.
- `teaches`: the reusable idiom in one line.
- `traps_avoided` (optional): the inline, query-specific warnings — "what the
  naive query gets wrong + the fix".

Rules across the set:

- **Elevate the least-recoverable classes.** Every MIE that can support them
  SHOULD include at least one `aggregation` and one `cross_db` example. An
  `aggregation` example ships its verified total and demonstrates
  `COUNT(DISTINCT)` + graph-scoping.
- **Enumeration is first-class (spec §4.4).** For every "**all** entities with
  property X" question the DB can answer, there must be an example showing the
  **set-level** route (a controlled-vocabulary term / typed predicate), not just a
  per-instance or text-match pattern, and **not** buried as a `traps_avoided`
  caveat on some other example. Check this DB's row in
  `benchmark/redesign/enumeration_audit.md` (all 36 DBs pre-scanned): **Tier A**
  DBs must add a *new* standalone `enum_*` example (the route is buried in v2);
  **Tier B/C** DBs must keep the worked query and its load-bearing caveat together.
- **No test leakage (spec §4.6).** An example's subject (keyword phrase, class
  IRI, gold gene/compound/accession) must **not** be a benchmark question's exact
  subject for **this DB**. Grep it against `benchmark/questions/*.yaml`
  (`inspiration_keyword` / `exact_answer`) before finalizing; swap to a neutral
  member of the same class if it collides. Canonical non-benchmark subjects (ATP,
  TP53, BRCA1) are fine.
- **One fact, one place (spec §4.2).** A predicate shown in any example is **not**
  repeated in `schema_delta`. A warning is database-wide (`global_gotchas`) **or**
  query-specific (`traps_avoided`) — never both.

There is no fixed count (v2's "exactly 7, 2/3/2" is retired). Author the set the
DB's questions need: cover the primary lookup routes, the enumeration route(s),
one aggregation, and one cross-DB join where they exist. Typical files land at
8–14 examples; a rich hub DB (UniProt) more.

## 5. `schema_delta` (optional)

A short list of **non-obvious** predicates / vocabularies / entity types a query
might need but that **no example demonstrates**. Not a schema dump. If a predicate
is shown in an example, or the model can guess it (basic prefixes, `rdfs:label`),
it does **not** belong here. Prose one-liners, each carrying the semantics + a
coverage figure where relevant.

## 6. `id_join_map` (required) — the least-recoverable asset

How to anchor stably and cross to other databases.

- `stable_anchor`: how to anchor stably — the IRI/accession pattern, plus any
  secondary human key (e.g. a mnemonic).
- `same_endpoint_joins` (optional): `{db: "join predicate/path"}` — co-hosted DBs
  reachable by a **direct GRAPH join, no bridge**. Point each at the `cross_db`
  example that demonstrates it.
- `xrefs` (optional): `{db: "xref predicate + prefix/coverage"}` — outbound
  references. **Mechanism-agnostic**: name each entry after however the DB actually
  points out (`rdfs:seeAlso` by IRI prefix, a `hasLink`/accession string, an ID
  that needs a transform).
- `bridged_via_togoid` (optional): list of DBs reachable **only** via
  `togoid_convertId` (NOT co-hosted). A DB whose joins are all intra-endpoint may
  have none.

## What v3 does NOT have

Do not carry these v2 sections forward — they were dropped deliberately (spec §1.3):

- `shape_expressions`, `sample_rdf_entries` — the example **is** the shape and the
  sample; don't restate them.
- `sparql_query_examples` / `cross_database_queries` as separate sections — folded
  into `examples` (with `cross_db` and `aggregation` elevated as complexity tiers).
- `cross_references` — becomes `id_join_map`.
- `critical_warnings` / `anti_patterns` / `common_errors` — database-wide traps go
  to `global_gotchas`; query-specific ones go inline as `traps_avoided`. There is
  no standalone anti-pattern section and no mandatory "schema check before text
  search" entry; that guidance now lives as `teaches`/`traps_avoided` on the
  enumeration examples themselves.
- `architectural_notes`, `data_statistics` — the few non-obvious notes go to
  `schema_delta`; the counts go to header `entity_counts`.

## Byte budget

The win is measured, not vibed. Record the byte count of the v3 file vs the v2.x
file it replaces (spec §5 item 7) — the UniProt pilot came in **~55–74% smaller**.
There is no line ceiling, but if a v3 file is not clearly smaller than its v2
predecessor, you are probably restating a fact the examples already carry.
