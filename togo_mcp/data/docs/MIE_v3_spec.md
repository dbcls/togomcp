# MIE File Specification v3

*The authorable contract for every MIE file under `togo_mcp/data/mie/`. It supersedes the retired
v2 spec (`MIE_file_specs.md`, removed 2026-07-25). Worked reference: `togo_mcp/data/mie/uniprot.yaml`
(the hand-authored v3 pilot). The design rationale — **why** each rule exists, with the ablation
evidence — lives in `internal_docs/mie-redesign-from-scratch-2026-07-20.md` (gitignored, not
shipped). Where the rationale and this spec disagree, this spec wins. The authoring tooling that
implements it is the `mie-generator` skill (`.claude/skills/mie-generator/`).*

## 1. Overview

### 1.1 Purpose
An MIE file tells an LLM what it **cannot recover on its own** about one RDF database:
the non-obvious predicates, the join paths, the count/graph traps, and verified example
queries it can reuse. v3 is organized by **agent need × recoverability** with the
**verified, executable worked example as the atomic unit**.

### 1.2 Why v3 (evidence)
The 2026-07 ablations found the v2.3 layout documents the same fact up to three times over,
each time in a different **form**: a predicate stated as a declarative constraint (ShEx shape
in `shape_expressions`), shown as a concrete instance (sample triple in `sample_rdf_entries`),
and used as an executable step (worked query in `sparql_query_examples`) — with the
`cross_references` list a loose fourth restatement for xref predicates. Three modes of
expression, one underlying fact, three separate sections. (`schema_info` is *not*
one of these — it is the metadata header, and survives into v3 as `discovery` + `header`.)
Leave-one-in confirmed the value concentrates in the query-construction content: the
`query` group alone recovers **99%** of the whole-MIE benefit. v3 collapses the
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

Top-level keys, in order. **Required:** `mie_spec`, `database`, `discovery`, `endpoint`,
`graphs`, `examples`, `id_join_map`. **Optional:** `base_uri`, `entity_counts`,
`global_gotchas`, `schema_delta`.

`mie_spec` is the FORMAT version and the file's first key. It is not a content version:
it changes only when this spec changes, never when a file is edited. It exists so a reader
can reject a format it does not understand instead of silently reading nothing — the v2→v3
flip stranded four separate readers keyed on v2 field names, each returning empty rather
than failing, and none noticed for a month. Consumers MUST check it. (Content identity is
derived, not declared: `server._detect_mie_bundle_version` hashes file bytes, and staleness
comes from `verified.date` — do not reintroduce a hand-maintained `mie_version`. v2 had one;
its values ran 1.2–7.1 with no cross-file meaning, and its only consumer hashed it.)

An **additive optional key does not bump `mie_spec`.** Consumers test it for equality
(`stats.load_mie_dates` skips anything that is not exactly 3), so bumping for a backward-compatible
addition would strand every one of them — the failure the field exists to prevent, triggered by a
change that breaks nothing. `check:` (§3.6, added 2026-08-26) is such an addition and files carrying
it stay `mie_spec: 3`. Bump only when an existing key changes meaning or disappears.

```
mie_spec: 3      # format version — bump ONLY on a spec change, never on a content edit
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
entity_counts:   # optional; every count COUNT(DISTINCT)+graph-pinned, with a `date:` or a global `verified:`
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

### 3.6 `check:` (required on any falsifiable claim) — the machine-testable half of a gotcha
A `global_gotchas` entry's `say`, and each `traps_avoided` line, may assert something the endpoint
can settle: a count, a multiplier, "this returns 0 rows", "this is not here", "this does not run".
Every such assertion carries a `check:` — the query (or pair of queries) that re-decides it, so
`scripts/check_mie_gotchas.py` can catch drift the way `check_mie_examples.py` catches a dead example.

```yaml
global_gotchas:
  - id: mandatory_graph_pin
    say: "<what silently fails + the fix>"
    check:
      kind: ratio                 # count | ratio | zero_rows | absent | error
      date: "YYYY-MM-DD"          # when the expectation below was last measured
      unpinned: |                 # kind: ratio takes TWO queries, each returning one scalar
        SELECT (COUNT(*) AS ?n) WHERE { ... }
      pinned: |
        SELECT (COUNT(*) AS ?n) WHERE { GRAPH <…> { ... } }
      expect: {ratio: 6.29, tolerance: 0.05}
```

`traps_avoided` entries are plain strings by default; to attach a check, write the entry as a
mapping instead — `{say: "<the trap + the fix>", check: {...}}`. Both forms may be mixed in one list.

| `kind` | The claim it settles | Passes when |
|---|---|---|
| `count` | "this figure is N" | `query` returns one scalar within `expect.tolerance` (fractional, default 0.02) of `expect.value` |
| `ratio` | "written this way it inflates ×R"; also "these two forms agree" (ratio 1.0) | the two legs' quotient is within `expect.tolerance` (fractional, default 0.05) of `expect.ratio`. Name the legs `unpinned:`/`pinned:` for an inflation claim, `numerator:`/`denominator:` otherwise |
| `zero_rows` | "written this way it silently returns nothing" | `query` returns 0 rows |
| `absent` | "this predicate / graph / value is not on this endpoint" | `query` returns 0 rows |
| `error` | "this is rejected, or does not complete" | `query` fails: a SPARQL compile/execution error, or no result within `expect.timeout_s` (default 60) |

**`kind: error` is the one that matters most.** Of the six factual defects the 2026-08-25 cross-check
found in `oma`/`bgee`, three were "this TIMES OUT" written over an operation that finishes in 1–30
seconds. A false timeout warning steers the reader away from a route that works — the same harm as
§4.4, arriving by the opposite door — and it is invisible to every other check in this spec, because
a warning that nobody tests is indistinguishable from a warning that is true. Under `kind: error`,
an operation that completes **fails the check**.

Three rules keep the checks honest:
- **Do not encode a marginal claim.** The bgee anatomy join measured 129s against a 120s client
  timeout: "times out" is a coin flip there, so it is written as a measured runtime in the `say` and
  checked as a `count`, not asserted as an `error`. If a claim only holds sometimes, weaken the
  claim; do not widen the tolerance.
- **Runtime is not a property of a query — it is a property of the cache.** Virtuoso's buffer cache
  makes the same query take 75s and then 0.1s, and this is not a rare edge: of four timeout claims
  that survived a first re-measurement in the 2026-08-26 sweep, **two collapsed to ~0.1s on the very
  next run** (ncbigene's un-scoped gene enumeration, pubmed's STRSTARTS topic COUNT). Before writing
  `kind: error`, run the query **at least twice**. If the second run completes, the claim is
  cache-state-dependent: state the cold and warm figures in the `say` and check something that does
  not move — the result value, a row count, or the prescribed fix — because a `kind: error` check on
  a cacheable query is a coin flip that will eventually fail CI for no reason. Only two claims in the
  whole corpus fail warm (`ddbj` gene_cds_protein, `pubchem` compound_scan_timeout); those keep
  `kind: error`.
  This has a second consequence worth passing to the reader: **never diagnose a query's correctness
  from how long it took.** A fast run may mean the pages were warm, not that the query was cheap or
  the scope was right — and every silent-wrong-answer trap in this corpus returns fast.
- **Reuse the query you already ran.** The Phase-2g redeclaration probe measures every multiplier the
  header will state. Paste those two queries into the `check:` rather than composing new ones — the
  figure and the check then cannot disagree, and the marginal cost is zero.

`check:` blocks are **test fixtures, not reader content**: `get_MIE_file` strips them before serving,
so they cost the reader nothing and a deliberately-broken `zero_rows`/`error` query is never shown to
an agent that might copy it. For the same reason they are excluded from the §5 item 7 byte-share
measurement, which is taken over the served form.

Qualitative advice ("use this", "write it in this order", "prefer the IRI") is out of scope — there
is nothing to run. A `say` that mixes both carries a check for the falsifiable half only.

## 4. Authoring rules

### 4.1 Every falsifiable claim is verified, dated, and machine-re-decidable (non-negotiable)
Every `entity_counts` value and every example's `verified:` block is re-run live against the
endpoint, and carries the date it was run in a `date: "YYYY-MM-DD"` field. A re-run that
disagrees is a drift signal, not silent rot. This makes the file **machine-testable**: a CI
job can execute every example and assert its `verified` result.

**The same rule binds the prose.** A `global_gotchas` `say` or a `traps_avoided` line that
asserts a number, a multiplier, a zero-row outcome, an absence, or a failure-to-run **MUST**
carry a `check:` that re-decides it (§3.6), and that check must have been run this pass.
Qualitative advice is exempt — there is nothing to execute.

This clause was added on 2026-08-26 because the narrower rule demonstrably was not enough. A
2026-08-25 cross-check of four MIE headers against the SIB endpoint found a factual defect in
**all four**, none of which any existing gate could see: `uniprot` prescribed the *opposite* of
the working literal form, `oma` stated a ×2.00 inflation that measures ×6.29, and `oma`/`bgee`
between them warned that three operations "time out" when they finish in 1–30 seconds. The
examples in those same files were clean — because examples get executed and prose does not.
Prose is not a lower evidentiary tier than a query; it was only an untested one.

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

### 4.6 Illustrative subjects must not be drawn from the benchmark (no test leakage)
An example teaches a **route**; the specific entity it uses is just the vehicle. Never pick that
entity from the evaluation set — an example whose subject is a benchmark question's exact
keyword / class / gold entity leaks the test answer into the corpus and inflates the step-5
equivalence run on that question (the MIE "knows" the answer instead of the agent deriving it).
- *How this bit us:* the first-draft `keyword_enum` (uniprot) and `enum_has_role` (chebi) used
  **LIM domain** (q066) and **antimicrobial agent** (q075) — the exact subjects of those questions,
  and `keyword_enum` even carried q066's first-step count (71). Fixed by swapping to neutral,
  live-verified subjects (SH3 domain → 108; neurotoxin → 89) that exercise the identical route.
- *Rule:* before finalizing an example, check its subject (keyword phrase, class IRI, gold gene /
  compound / accession) against `benchmark/questions/*.yaml` (the `inspiration_keyword` and
  `exact_answer` fields — a one-line grep). If it collides with a question that uses **this DB**,
  pick a different member of the same class. Canonical, non-benchmark subjects (ATP, TP53, BRCA1)
  are fine; the point is only to avoid the specific entities the benchmark scores on.

## 5. Validation checklist (Phase 5 — non-negotiable)
1. File parses as YAML; required keys present (§2).
2. `discovery` has all four fields; description is one sentence.
3. **Every** example has `verified:` with a `date:` field (not `on:` — §4.1 trap), and was actually re-run this pass.
3b. **Every falsifiable claim in `global_gotchas` / `traps_avoided` carries a `check:` (§3.6), and
   `scripts/check_mie_gotchas.py <db>` is clean.** Read each `say` and each trap line and ask: does
   this assert a figure, a multiplier, a zero-row outcome, an absence, or a failure-to-run? If yes it
   needs a check. Timeout and "unrunnable" claims take `kind: error` specifically — an operation that
   completes fails that check, which is the point.
4. At least one `aggregation` and one `cross_db` example where the DB supports them.
5. Every `co_hosted` graph that inflates/joins/stubs is flagged.
6. No fact restated across sections (§4.2); nothing in `schema_delta` that an example shows.
7. Byte count recorded vs the v2.x file it replaces (the deterministic half of the win),
   measured over the **served** form — `check:` blocks are stripped before serving (§3.6) and
   do not count against the composition budget.
8. Every set-level enumeration route the DB supports ("**all** entities with property X") has its
   own example, not only a per-instance/text pattern or a `traps_avoided` mention (§4.4). Check this
   DB's row in `.claude/skills/mie-generator/references/enumeration_audit.md` (all 36 DBs pre-scanned): if it is **Tier A**, the v3 file must
   add a *new* standalone `enum_*` example (the route is buried in v2); if **Tier B/C**, keep the
   worked query and its load-bearing caveat together — do not compress the query away and leave only
   the warning.
9. No example's subject is a benchmark question's keyword / class / gold entity for **this DB**
   (§4.6) — grep the subject against `benchmark/questions/*.yaml`; swap to a neutral member if it
   collides. No test leakage.
