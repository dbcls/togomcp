# MIE Structure — Per-Section Requirements

The 11 sections of an MIE file, in required order, with what to include and what to omit.

## 1. `schema_info`

Descriptive header. Required fields:

- `title`: canonical database name
- `description`: 2–3 sentences — what the database contains, its main entity types, primary use cases
- `endpoint`: SPARQL endpoint URL
- `base_uri`: root URI namespace
- `graphs`: list of named graphs in the endpoint
- `kw_search_tools`: list of available keyword-search tool names, or `[]` if none
- `version`: `mie_version`, `mie_created` (today's date), `data_version`, `update_frequency`
- `access.backend`: `"Virtuoso"` / `"Blazegraph"` / etc. — determines `bif:contains` availability

## 2. `critical_warnings`

A plain string (YAML `|` block) listing silent-failure traps. These are the first things a reader scans, so put anything that would make a query return 0 rows without erroring.

Categories to look for:

- **Mandatory performance filters.** Is there a status flag that, if omitted, blows up the result set by 1000x? (e.g. UniProt's `up:reviewed 1` — without it you query 244M entries instead of 589K.)
- **IRI namespace traps.** Does the database use OBO IRIs where you'd expect internal ones? Does it use multiple parallel namespaces for the same concept?
- **Typos required verbatim.** Some databases have a misspelled predicate (`referecens` instead of `references`) that is preserved for backwards compatibility. Using the correct spelling returns zero rows. Document these.
- **Graph-specific patterns.** Some predicates only resolve in specific named graphs.

Use `[]` only if you have genuinely confirmed there are no traps. In practice most real databases have at least one.

## 3. `shape_expressions`

ShEx-style schema for every major entity type, as a YAML `|` string. Start from the `./shex/<db>.shex` file if present; otherwise build from DESCRIBE queries.

Inline comments should document:

- Instance counts for major entity types (from discovery queries)
- Non-obvious predicate semantics (what does `foo:observedValue` actually mean in context?)
- IRI patterns and namespace gotchas
- Measurement scaffolds or indirect value access patterns (blank nodes, reified statements)

```
PREFIX ex: <http://example.org/>

<EntityShape> {
  a [ ex:Type ] ;                  # ~2.4M instances
  ex:required xsd:string ;
  ex:optional xsd:string ?         # ~18% of entities have this
}
```

## 4. `sample_rdf_entries`

**Exactly 3 entries.** Single shared `rdf_prefixes` block at the top — do not repeat `@prefix` declarations in every entry.

The 3 entries should:

- Cover the most important entity types in the database
- Demonstrate at least one non-obvious access pattern (measurement scaffold, cross-reference, reified statement)
- Include enough context that a reader can see how the pieces connect

**Every triple must be validated against the endpoint via a SELECT or ASK query.** No made-up IRIs, no fabricated literals.

```yaml
sample_rdf_entries:
  rdf_prefixes: |
    @prefix ex: <http://example.org/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  entries:
    - title: "Representative entity"
      description: One-sentence purpose.
      rdf: |
        ex:entity1 a ex:Type ;
                   ex:required "value" .
```

## 5. `sparql_query_examples`

**Exactly 7 queries. Distribution: 2 basic / 3 intermediate / 2 advanced.**

Requirements across the set:

- ≥ 2 queries use specific IRIs or VALUES with IRIs
- ≥ 2 queries use typed predicates or graph navigation
- ≤ 1 query uses text search (with Gate Check passed — see `references/query-strategy.md`)
- All 7 include a `LIMIT` clause
- All 7 are tested against the endpoint before the file is written

Each entry has:

- `title`: action-oriented, specific
- `description`: 1–2 sentences of context
- `question`: the natural-language question the query answers
- `complexity`: `basic` | `intermediate` | `advanced`
- `sparql`: the query, with inline comments explaining non-obvious choices

If a query uses text search, add a comment in the SPARQL explaining why no structured alternative exists.

## 6. `cross_database_queries`

If the target database shares a SPARQL endpoint with others (RDF Portal, ChEMBL endpoint with UniProt, etc.), include 1–2 cross-database examples.

**Before writing any cross-database query**, read the MIE files of every other database involved (from `./togo_mcp/data/mie/`) to confirm the linking predicates and shared IRI namespaces.

```yaml
cross_database_queries:
  shared_endpoint: endpoint_name
  co_located_databases: [db1, db2]
  examples:
    - title: "..."
      description: |
        Linking strategy:
        - db1: predicate X links to shared IRI namespace (e.g. EC numbers)
        - db2: predicate Y links to same IRI namespace
        - Direct IRI matching; no text search required
      databases_used: [db1, db2]
      complexity: intermediate
      sparql: |
        ...
      notes: |
        - Linking via: [IRI type]
        - MIE files checked: db1, db2
```

**Isolated endpoint?** Use `examples: []` and a `notes` block explaining why, plus manual bridging strategies.

## 7. `cross_references`

Pattern descriptions for each cross-reference predicate (`rdfs:seeAlso`, `skos:exactMatch`, custom predicates). For each pattern:

- `pattern`: the predicate
- `description`: what it links to
- `databases`: coverage by category (e.g. "UniProt: 78%", "ChEMBL: 45%")
- `sparql`: optional — include only if the pattern is non-trivial

## 8. `architectural_notes`

Six sub-sections:

- `query_strategy`: priority order for writing new queries against this database
- `schema_design`: central entity types and their relationships, key controlled vocabularies, IRI patterns
- `performance`: critical filters, key optimizations, `bif:contains` tips for Virtuoso
- `data_integration`: cross-reference patterns and coverage
- `data_quality`: known anomalies, duplicates, data entry artifacts
- `text_search_justification`: number of example queries using text search, fields where it's legitimate, reasons structured alternatives were confirmed absent

## 9. `data_statistics`

**Counts and coverage percentages only.** Every number has a verified date and a verification method.

- `total_entities`: total count
- `verified_date`: ISO date
- `verification_method`: "Direct COUNT query" or "sampling with N=..."
- `coverage`: sub-fields for key properties, each with its own percentage and calculation

**Omit these sub-sections** (they are auditing artefacts that clutter the file at query time):

- `verification_queries` — not needed at query time
- `cardinality` (avg-X-per-entity) — rarely useful
- `performance_characteristics` — belongs in `architectural_notes.performance`

## 10. `anti_patterns`

**3–4 entries.** The first must be "Schema Check Before Text Search" (or equivalent) — this is the single most common failure mode.

Each entry has:

- `title`
- `problem`: one-sentence statement of the mistake
- `wrong_sparql`: minimal example of the bad pattern
- `correct_sparql`: the fixed version
- `explanation`: why the wrong version is wrong

The other 2–3 slots should cover database-specific traps discovered during schema exploration.

## 11. `common_errors`

**2–3 entries.** Each with:

- `error`: symptom (the error message or behaviour the user sees)
- `causes`: list of root causes
- `solutions`: list of concrete fixes

Good picks: timeout / slow query, empty results, cross-database query failure.

## Line budget

| Database complexity    | Target lines |
|------------------------|--------------|
| Small / focused        | 400–500      |
| Typical                | 500–700      |
| Complex (UniProt-like) | 700–900      |

If you're over 900 lines, look for duplication between `shape_expressions` (which documents the schema) and `architectural_notes.schema_design` (which explains the schema). Keep the factual schema in `shape_expressions` and the higher-level reasoning in `architectural_notes`.
