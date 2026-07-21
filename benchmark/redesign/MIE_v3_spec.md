# MIE File Specification v3 (DRAFT — `mie-redesign` branch)

*Companion to the design rationale in `internal_docs/mie-redesign-from-scratch-2026-07-20.md`
(gitignored). Worked reference: `benchmark/redesign/mie_v3/uniprot.yaml`. This spec is the
authorable contract; the rationale explains **why** each rule exists (with the ablation
evidence). Where they disagree, this spec wins.*

## 1. Overview

### 1.1 Purpose
An MIE file tells an LLM what it **cannot recover on its own** about one RDF database:
the non-obvious predicates, the join paths, the count/graph traps, and verified example
queries it can reuse. v3 is organized by **agent need × recoverability** with the
**verified, executable worked example as the atomic unit**.

### 1.2 Why v3 (evidence)
The 2026-07 ablations found the v2.3 layout carries heavy *orthogonal* redundancy — the
same fact written up to four ways (schema list, ShEx shape, worked query, sample triple).
Leave-one-in confirmed the value concentrates in the query-construction content: the
`query` group alone recovers **99%** of the whole-MIE benefit. v3 collapses the 4×
restatement into one example-atom and drops the prose-only sections, keeping the value at a
fraction of the bytes (UniProt pilot: **~55–74% smaller**).

### 1.3 The shift from v2.3
| v2.3 (11 author-function sections) | v3 (5 need-based parts) |
|---|---|
| `schema_info` | → `discovery` block (4 fields) + header; schema → implicit-in-examples + `schema_delta` |
| `shape_expressions`, `sample_rdf_entries` | → **dropped**; the example IS the shape + the sample |
| `sparql_query_examples`, `cross_database_queries` | → `examples` (the core), with `cross_db` + `aggregation` elevated |
| `cross_references` | → `id_join_map` |
| `critical_warnings`, `anti_patterns`, `common_errors` | → database-wide → header `global_gotchas`; query-specific → inline `traps_avoided` |
| `architectural_notes`, `data_statistics` | → the few non-obvious notes → `schema_delta`; counts → header `entity_counts` |

## 2. File structure

Top-level keys, in order. **Required:** `database`, `discovery`, `endpoint`, `graphs`,
`examples`, `id_join_map`. **Optional:** `base_uri`, `entity_counts`, `global_gotchas`,
`schema_delta`.

```
database:        # the DB key (== filename stem, == SPARQL_ENDPOINT key)
discovery:       # {title, description, keywords, categories} — the build-time catalog source
endpoint:        # SPARQL URL   (+ base_uri, graphs, entity_counts, global_gotchas = the header)
examples:        # the load-bearing content — verified, executable atoms
schema_delta:    # ONLY non-obvious predicates no example already shows
id_join_map:     # stable anchors + cross-DB join paths
```

## 3. Section specifications

### 3.1 `discovery` (required, kept SMALL — it is multiplied across the whole catalog)
The four fields a build-time generator rolls into the Usage Guide catalog (rationale §1.1).
It is the **source of truth** for cross-DB discovery; it is *not* served per-request.
```yaml
discovery:
  title:       # short human title, e.g. "UniProt RDF"
  description: # ONE tight sentence: what kind of data, for keyword/semantic matching
  keywords:    # data-type/domain terms (lowercase), NOT entity names
  categories:  # 1–3 coarse buckets
```
Rules: keep it uniform and minimal across DBs; moving/renaming these four keys requires
updating whatever aggregates them (guide generator, and any transitional `_load_databases_cache`).

### 3.2 Header — provenance + database-wide truths (`get_MIE_file` only)
```yaml
endpoint:  # SPARQL endpoint URL
base_uri:  # optional
graphs:
  primary:    # the DB's own graph IRI — the default pin target
  supporting: # list of same-DB graph localnames
  co_hosted:  # {name: "one-line note"} — datasets sharing the endpoint. MUST flag any that
              # (a) inflate counts, (b) enable a direct cross-DB join, or (c) are empty stubs.
entity_counts:   # optional; every count COUNT(DISTINCT)+graph-pinned, with an `on:` date or a global `verified:`
global_gotchas:  # the 2–5 that bite ANY query on this DB. Each: {id, say}
  - id: <slug>
    say: "<what silently fails + the fix>"
```
`global_gotchas` carries **only database-wide** traps (union inflation, mandatory filters,
label absence). Query-specific traps go inline in the example (§3.3), never here.

### 3.3 `examples` (required) — the core
Each example is self-contained, executable, and verified. It replaces the shape, the sample,
and (annotated) the warning it would otherwise be written as.
```yaml
examples:
  - id: <slug>
    intent: <one line — what this teaches>
    question: "<natural-language question it answers>"
    complexity: basic | intermediate | advanced | aggregation | cross_db
    endpoint_name: <group>   # ONLY for cross_db (e.g. sib); omit for single-DB
    sparql: |
      <a complete, runnable query>
    verified: {<result key>: <value>, date: "YYYY-MM-DD"}   # REQUIRED — see §4.1
    teaches: "<the reusable idiom in one line>"
    traps_avoided:           # optional; the inline, query-specific warnings
      - "<what the naive query gets wrong + the fix>"
```
- **`aggregation`** and **`cross_db`** are elevated (least-recoverable, highest-failure):
  every MIE that can support them SHOULD include at least one of each. An `aggregation`
  example ships its verified total and demonstrates COUNT(DISTINCT)+graph-scoping.
- A predicate shown in any example is **not** repeated in `schema_delta`.

### 3.4 `schema_delta` (optional)
A short list of **non-obvious** predicates / vocabularies / entity types a query might need
but that **no example demonstrates**. Not a schema dump. If it's shown in an example, or the
model can guess it (basic prefixes, `rdfs:label`), it does **not** belong here.

### 3.5 `id_join_map` (required) — the least-recoverable asset
```yaml
id_join_map:
  stable_anchor:        # how to anchor stably (the IRI/accession pattern; secondary human keys)
  same_endpoint_joins:  # {db: "the join predicate/path"} — co-hosted, direct GRAPH join, no bridge
  xrefs:                # {db: "the xref predicate + prefix/coverage"} — outbound references
  bridged_via_togoid:   # list — DBs reachable only via togoid_convertId (NOT co-hosted)
```
The `xrefs` bucket is mechanism-agnostic — name each entry after however the DB actually points
out (rdfs:seeAlso by IRI prefix, a `hasLink`/accession string, an ID that needs a transform). A
DB whose joins are all intra-endpoint may have no `bridged_via_togoid` at all (both are optional).

## 4. Authoring rules

### 4.1 Everything countable is verified and dated (non-negotiable)
Every `entity_counts` value and every example's `verified:` block is re-run live against the
endpoint, and carries the date it was run in a `date: "YYYY-MM-DD"` field. A re-run that
disagrees is a drift signal, not silent rot. This makes the file **machine-testable**: a CI
job can execute every example and assert its `verified` result.

> **YAML trap:** use `date:`, never `on:`, for the timestamp key. YAML 1.1 parses the bare
> word `on` (also `off`/`yes`/`no`) as a **boolean**, so `on: 2026-07-21` becomes the key
> `true`, not `"on"` — and a validator looking for the `on` key silently finds nothing. Quote
> the date value too, so it stays a string rather than a parsed `date` object. (The v3 format
> has its own literal-typing footgun, exactly like the SPARQL ones the MIEs document.)

### 4.2 One fact, one place
Do not restate a fact across sections. Warnings are database-wide (`global_gotchas`) **or**
query-specific (`traps_avoided`) — never both, never a separate prose section. Schema shown
in an example is not repeated in `schema_delta`.

### 4.3 Carry only the non-recoverable
Before a fact earns bytes: can the model get it from training or one `get_graph_list` /
exploratory `SELECT`? If yes, cut it. Exception: an example's own scaffolding (PREFIX,
SELECT, rdfs:label) rides for free because the non-recoverable idiom can't be shown without it.

### 4.4 A positive route is not a caveat (the enumeration rule)
A mechanism that is a **primary query route** must appear as its own `example` (or `schema_delta`
entry) — it must **not** survive only as a `traps_avoided` caveat on some other example. Many
mechanisms are dual: they are both "*the* way to do X" and "watch out for X when doing Y."
Compression tends to keep the caveat and drop the route, which reads to the agent as "avoid this,"
the opposite of the intent.
- *Concrete failure (smoke test, q066):* UniProt keyword classification (`up:classifiedWith
  keywords:NNN`) is THE route to enumerate "all proteins with feature/domain X" (LIM domain → 71).
  The v3 draft kept it only as a caveat on the GO example ("up:classifiedWith *also* carries
  keywords, filter them out"), so the agent used name/annotation text instead and undercounted
  (14–25 vs 71) — **systematically, all 3 runs**. Fix: a first-class `keyword_enum` example.
- *Rule of thumb:* for every "**all** entities with property P" question the DB can answer, there
  should be an example showing the **set-level** route (a controlled-vocabulary term / typed
  predicate), not just a per-instance or text-match pattern. Enumeration ≠ instance lookup.

### 4.5 Progressive disclosure (optional, forward-looking)
The header is the cheap tier; `examples` the expensive one. A future `get_MIE_file(database,
level=header|+examples|full)` can serve tiers. Author so the header stands alone.

## 5. Validation checklist (Phase 5 — non-negotiable)
1. File parses as YAML; required keys present (§2).
2. `discovery` has all four fields; description is one sentence.
3. **Every** example has `verified:` with a `date:` field (not `on:` — §4.1 trap), and was actually re-run this pass.
4. At least one `aggregation` and one `cross_db` example where the DB supports them.
5. Every `co_hosted` graph that inflates/joins/stubs is flagged.
6. No fact restated across sections (§4.2); nothing in `schema_delta` that an example shows.
7. Byte count recorded vs the v2.x file it replaces (the deterministic half of the win).
8. Every set-level enumeration route the DB supports ("**all** entities with property X") has its
   own example, not only a per-instance/text pattern or a `traps_avoided` mention (§4.4).
