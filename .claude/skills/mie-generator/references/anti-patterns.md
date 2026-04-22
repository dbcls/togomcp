# Anti-patterns and Common Errors

Worked examples of the four patterns that must appear in every MIE file's `anti_patterns` section (or close equivalents tailored to the specific database), plus the common error scenarios.

## Anti-pattern 1: Text search when a structured property exists

**Problem.** Using string matching when a specific IRI or typed predicate is available.

**Wrong:**

```sparql
# Inefficient: text search for a controlled vocabulary value
?description bif:contains "'antibacterial'"
```

**Correct:**

```sparql
# Efficient: use the specific IRI from the ATC classification
?molecule cco:atcClassification <http://www.whocc.no/atc/J01> .
```

**Why.** Controlled vocabularies exist precisely so that you don't have to guess spellings or worry about alternative wordings. The IRI is canonical, the text is not.

## Anti-pattern 2: Skipping the schema check before text search

**Problem.** Reaching for text search without first reading `shape_expressions` to look for structured alternatives.

**Wrong:**

```sparql
# No schema check performed — jumps straight to text search
?text bif:contains "'kinase'"
```

**Correct workflow:**

1. `get_MIE_file(db)` → read `shape_expressions`
2. Use the search API (`search_chembl_target`, `search_uniprot_entity`, etc.) to find examples
3. DESCRIBE the examples to extract concept IRIs
4. Use those IRIs:

```sparql
VALUES ?term {
  <http://purl.obolibrary.org/obo/GO_0016301>   # kinase activity
  <http://purl.obolibrary.org/obo/GO_0004672>   # protein kinase activity
}
?entity classificationPredicate ?term .
```

**Why.** RDF databases are curated. If you think you need free-text search, you're almost always missing a predicate that someone put in precisely so you wouldn't have to.

## Anti-pattern 3: Circular reasoning with search results

**Problem.** Using search API results inside a `VALUES` block and then counting them. The count is predetermined by the size of the search result — you're not counting anything useful.

**Wrong:**

```sparql
VALUES ?entity { ex:1 ex:2 ... ex:20 }   # only the 20 results from the search API
SELECT (COUNT(?entity) AS ?count) WHERE { ... }
# Result: 20. Obviously.
```

**Correct.** Use the search API to discover concept IRIs, then query the full dataset against those IRIs:

```sparql
VALUES ?classification { <term:A> <term:B> }
SELECT (COUNT(DISTINCT ?entity) AS ?count)
WHERE { ?entity hasClassification ?classification . }
```

**Why.** The search API exists to help you find relevant concepts in a huge vocabulary. It's a discovery tool, not an answer tool. The full dataset lives in the triplestore.

## Anti-pattern 4: Unindexed text search when indexed is available

**Problem.** Using `FILTER(CONTAINS())` when `bif:contains` is available (Virtuoso backend).

**Wrong:**

```sparql
FILTER(CONTAINS(LCASE(?text), "keyword"))   # unindexed, full scan
```

**Correct:**

```sparql
?text bif:contains "'keyword'"   # uses Virtuoso's full-text index
```

**Why.** `FILTER(CONTAINS())` forces a full scan of every literal in scope. On a 100M+ triple store this is slow and often times out. `bif:contains` uses a proper inverted index.

## Common Error 1: Slow query or timeout

**Causes:**

- Text search used where structured IRIs or predicates are available
- Missing critical filters (reviewed status, graph clauses, date ranges)
- `FILTER(CONTAINS())` used when `bif:contains` would work
- Property path used just before `bif:contains` (forces intermediate materialization)

**Solutions:**

- Re-read `critical_warnings` and `shape_expressions` for mandatory filters
- Replace text search with structured lookups where possible
- On Virtuoso, use `bif:contains`; split property paths before it
- Always include a `LIMIT`

## Common Error 2: Empty or incomplete results

**Causes:**

- `VALUES` block populated with search results instead of concept IRIs (circular reasoning)
- Wrong IRI namespace — this fails silently, returning 0 rows rather than erroring
- Missing hierarchical navigation (query asks for "kinases" but only matches the specific term, not subclasses)
- Required status flag or graph clause omitted, returning a different slice of data than expected

**Solutions:**

- Re-read `critical_warnings` for known namespace traps
- DESCRIBE an example entity to confirm IRI patterns match what your query expects
- Use `rdfs:subClassOf+` or `skos:broader+` for hierarchical coverage
- Check that `GRAPH` clauses match the graph list in `schema_info.graphs`

## Common Error 3: Cross-database query timeout or empty results

**Causes:**

- Failed to read the MIE files of all databases in the query (so linking predicates weren't confirmed)
- Missing `GRAPH` clauses (query runs against the union graph, which is slow or differently shaped)
- Joining before filtering — the join is evaluated over the full product of both databases, then filtered, instead of the other way around

**Solutions:**

- Read MIE files for every database involved; confirm the shared IRI namespace that links them
- Use explicit `GRAPH` clauses for each database
- Apply restrictive filters inside each `GRAPH` block before the cross-database join
- Add `LIMIT` at every query level

## A note on documenting database-specific anti-patterns

The four anti-patterns above are universal. If you discovered a database-specific trap during schema exploration (e.g. "ChEMBL target IDs look like CHEMBL1234 but are IRIs `http://rdf.ebi.ac.uk/resource/chembl/target/CHEMBL1234` — users consistently write the bare ID"), add it as a fifth anti-pattern or fold it into one of the existing four. The goal is that a reader of the MIE file never falls into a trap that you already climbed out of.
