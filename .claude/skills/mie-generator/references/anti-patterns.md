# Traps: `global_gotchas` and `traps_avoided` (v3)

v3 has **no `anti_patterns` section**. The trap knowledge that v2 packed into
`anti_patterns` / `critical_warnings` / `common_errors` now lives in two places,
split by scope (spec §4.2 — one fact, one place):

- **`global_gotchas`** (header) — the 2–5 traps that bite **ANY** query on this
  DB. Each is `{id, say}`; `say` states *what silently fails + the fix*.
- **`traps_avoided`** (inline on an example) — a **query-specific** warning: what
  the naive version of *this* query gets wrong, and the fix, right next to the
  correct query that avoids it.

A warning is database-wide **or** query-specific — never both, never a separate
prose section. This file is a cookbook of the recurring traps and where each one
belongs.

## The enumeration trap is the one that matters most (spec §4.4)

The single highest-value thing these files teach is the **set-level enumeration
route**: how to get **ALL** entities with property/feature/class X. The failure
mode (regressed on benchmark q066) is compression keeping the *caveat* about a
predicate while dropping the *worked route* — which reads to the agent as "avoid
this," the opposite of the intent.

So a positive route is **never** only a `traps_avoided` caveat. It is its own
`example` (a `basic`/`intermediate` query, often `enum_*`). The caveat then rides
*on that example* as a `traps_avoided` line telling the reader **not** to fall
back to text matching:

```yaml
- id: keyword_enum
  intent: enumerate ALL proteins carrying a UniProt keyword — the classification route
  complexity: basic
  sparql: |
    SELECT (COUNT(DISTINCT ?protein) AS ?n)
    FROM <http://sparql.uniprot.org/uniprot>
    WHERE { ?protein a up:Protein ; up:reviewed 1 ; up:classifiedWith keywords:727 . }  # KW-0727 = SH3 domain
  verified: {n: 108, date: "2026-07-22"}
  teaches: "Enumerate by a domain/feature/function via up:classifiedWith keywords:NNN — the PRIMARY route for 'all proteins with feature X'."
  traps_avoided:
    - "Do NOT substitute a name/comment text match — it misses synonyms and non-name mentions and silently UNDERCOUNTS. Resolve the feature name to its KW number, then enumerate by that IRI."
```

## The four universal traps and where they go

These held in v2 as the four mandatory anti-patterns. In v3 they are mostly
**`teaches`/`traps_avoided` on the enumeration and lookup examples**, or a
`global_gotchas` entry when they are database-wide.

### 1. Text search when a structured property exists

Controlled vocabularies exist so you don't guess spellings. The IRI is canonical;
the text is not. Express this as an **example** that uses the IRI, with a
`traps_avoided` line naming the text query it replaces:

- *wrong idiom* — `?description bif:contains "'antibacterial'"`
- *right idiom* — `?molecule cco:atcClassification <http://www.whocc.no/atc/J01> .`

### 2. Skipping the schema check before text search

The workflow (read the schema → use a search API to find example entities →
DESCRIBE them → extract IRIs → query by IRI) is the *author's* method, not
something to ship as prose. What ships is the resulting IRI-based `example`. If
text search survives at all in a file, it is one example with a `teaches` line
stating in one sentence why no structured alternative exists.

### 3. Circular reasoning with search results

Never `VALUES ?x { <20 results from a search API> }` inside a `COUNT` — the count
is predetermined by the search-result size. The search API discovers concept
IRIs; the **triplestore** holds the answer. Any `aggregation` example must count
the full dataset against a controlled-vocab IRI, not a hand-pasted result set:

```sparql
SELECT (COUNT(DISTINCT ?entity) AS ?count)
WHERE { ?entity ex:hasClassification <term:A> . }   # not VALUES of prior results
```

### 4. Unindexed text search when indexed is available

On Virtuoso, `?text bif:contains "'keyword'"` uses the full-text index;
`FILTER(CONTAINS(LCASE(?text), "keyword"))` forces a full scan and often times
out. If a file legitimately needs text search, the example uses `bif:contains`
and its `teaches` says so.

## Database-wide traps → `global_gotchas`

These are not query-specific; they bite everything. Each becomes a `{id, say}`:

- **Mandatory performance filter** — a status flag whose omission blows up the
  result set (`up:reviewed 1` — without it you query ~244M rows instead of ~574K).
  `id: reviewed_filter`.
- **Union inflation on a co-hosted endpoint** — a predicate re-declared on a
  shared IRI by a sibling graph, or this DB's own entities re-typed by a sibling,
  so an unscoped `COUNT` inflates by the number of graphs (product across joined
  predicates). Found only by Phase 2g. `id: union_inflation`; the `say` gives the
  multiplier and the graph-pinned safe pattern, and the same sibling list is
  mirrored into `graphs.co_hosted`.
- **IRI namespace trap** — OBO IRIs where you'd expect internal ones; the wrong
  namespace returns 0 rows silently.
- **Absent labels** — e.g. `up:Protein` has no `rdfs:label`; a label query returns
  0 rows silently, and the names come from a different predicate.
- **Timeout-prone path** — e.g. a pre-flattened lineage where `rdfs:subClassOf*`
  times out but single-hop already covers the full ancestry.
- **Verbatim typo** — a misspelled predicate preserved for compatibility, where
  the corrected spelling returns 0 rows.

## Verification (non-negotiable)

Every predicate name and IRI cited in a `global_gotchas` or `traps_avoided` entry
must exist on the live endpoint (Phase 5). A warning about a non-existent
predicate is worse than no warning — the reader avoids the wrong thing while the
real trap stays unflagged. Traps are collected **during Phase 2** (from surprising
COUNT distributions and the 2g probe), not reconstructed from memory in Phase 4.
