# Query Strategy

This file contains the detailed query design guidance for writing SPARQL examples in an MIE file. Read it before designing the 7-query set in Phase 3 of the main workflow.

## Query design hierarchy

Prefer earlier entries over later ones. The order reflects speed, stability, and how well the query conveys the underlying schema to the next reader.

### 1. Specific IRIs (best)

Fast, stable, unambiguous. Use whenever the concept you're filtering by is identified by an IRI in a controlled vocabulary.

```sparql
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .       # Human
?molecule cco:atcClassification <http://www.whocc.no/atc/J01> .      # Antibacterials
?term rdfs:subClassOf <http://purl.obolibrary.org/obo/GO_0006915> .  # Apoptosis
```

### 2. VALUES with multiple IRIs

When you need to match several known concepts.

```sparql
VALUES ?concept {
  <http://purl.obolibrary.org/obo/GO_0016301>   # kinase activity
  <http://purl.obolibrary.org/obo/GO_0004672>   # protein kinase activity
}
?entity classificationPredicate ?concept .
```

### 3. Typed predicates

When a controlled vocabulary is expressed through string literals on a specific predicate rather than IRIs.

```sparql
?molecule cco:organismName "Homo sapiens" .
?activity cco:standardType "IC50" .
?entity status "approved" .
```

### 4. Graph navigation

When you need hierarchical coverage.

```sparql
?organism rdfs:subClassOf+ ?phylum .
?term skos:broader+ ?parentTerm .
```

### 5. `bif:contains` (indexed text search, Virtuoso only)

Use only when the field is genuinely unstructured free text.

```sparql
?comment bif:contains "'keyword1' AND 'keyword2'"
```

### 6. `FILTER(CONTAINS())` (last resort — unindexed)

Use only when `bif:contains` is unavailable (non-Virtuoso backend) and no structured alternative exists.

```sparql
FILTER(CONTAINS(LCASE(?text), "pattern"))
```

## Decision tree

```
1. Specific IRI for this concept?          YES → Use IRI directly
2. Controlled vocabulary / typed pred?     YES → Use the predicate
3. Graph structure to navigate?            YES → Use rdfs:subClassOf+ / skos:broader+
4. Any available search API?               YES → Find example entities, DESCRIBE them,
                                                 extract IRIs, restart at step 1
5. Genuinely unstructured free text?       NO  → Re-examine the schema
                                           YES → Virtuoso? bif:contains. Else FILTER(CONTAINS()).
```

## Performance table

| Approach             | Speed     | When to use                              |
|----------------------|-----------|------------------------------------------|
| Specific IRIs        | ★★★★★     | Always prefer when available             |
| VALUES with IRIs     | ★★★★★     | Multiple known concepts                  |
| Typed predicates     | ★★★★☆     | Controlled vocabularies                  |
| Graph navigation     | ★★★☆☆     | Hierarchical queries                     |
| `bif:contains`       | ★★☆☆☆     | Unstructured text (Virtuoso)             |
| `FILTER(CONTAINS())` | ★☆☆☆☆     | Last resort                              |

## The circular reasoning trap

This one catches people a lot.

**Wrong — counts only what you already found:**

```sparql
VALUES ?entity { ex:1 ex:2 ... ex:20 }   # 20 results from the search API
SELECT (COUNT(?entity) AS ?count) WHERE { ... }
```

This produces a count of 20. Of course it does. The search API only returned 20, and you're counting those same 20.

**Correct — use discovered concept IRIs to query the full dataset:**

```sparql
VALUES ?classification {
  <http://example.org/classification/TypeA>
  <http://example.org/classification/TypeB>
}
SELECT (COUNT(DISTINCT ?entity) AS ?count)
WHERE { ?entity hasClassification ?classification . }
```

The search API's role is to help you discover the relevant concept IRIs. Once you have them, query the full graph against those IRIs — don't query the filtered search results.

## The text-search Gate Check

Before using `bif:contains` or `FILTER(CONTAINS())` in any example query, confirm **all** of these:

- [ ] You have read the full `shape_expressions` section (including inline comments)
- [ ] You have checked for specific IRIs (ontology, taxonomy, classification codes)
- [ ] You have checked for typed predicates with controlled vocabularies
- [ ] You have checked for hierarchical relationships (`rdfs:subClassOf`, `skos:broader`)
- [ ] You have used any available search API to find and DESCRIBE example entities
- [ ] You can state in one sentence why no structured alternative exists

### Never use text search for

- Organisms — use taxonomy IRIs (`<http://purl.uniprot.org/taxonomy/...>`, NCBI Taxonomy)
- Ontology terms — use GO / MeSH / ChEBI / SO IRIs
- EC numbers — use the EC namespace
- Drug classifications — use ATC IRIs
- Any field backed by a controlled vocabulary

### Fields where text search IS legitimate

- `rdfs:comment` on a gene or protein (genuinely free prose)
- `dcterms:description` on an article abstract
- Synthesis notes, experimental conditions, free-form remarks
- Anything a human wrote as paragraph text with no codes

## Virtuoso-specific pitfalls

### Check the backend first

`access.backend: "Virtuoso"` in `schema_info` determines whether `bif:contains` is available. If you don't know, run a minimal `bif:contains` query once and see if it errors.

### Split property paths before `bif:contains`

**Wrong — breaks silently or runs forever:**

```sparql
?entity ex:path/ex:label ?text .
?text bif:contains "'keyword'"
```

**Correct:**

```sparql
?entity ex:path ?intermediate .
?intermediate ex:label ?text .
?text bif:contains "'keyword'"
```

`bif:contains` needs to see the variable bound to a plain string literal it can look up in its full-text index. Property paths can produce intermediate results that break this.

### `bif:contains` query syntax

The argument is a string with Virtuoso-specific operators:

```sparql
?text bif:contains "'apple'"                       # single term
?text bif:contains "'apple' AND 'banana'"          # both
?text bif:contains "'apple' OR 'banana'"           # either
?text bif:contains "'apple*'"                      # prefix
```

Inner quotes must be single quotes. The outer string is the usual double-quoted SPARQL literal.

## What makes a query good in an MIE file

The 7 example queries are not just there to work — they are there to teach the schema to the next LLM. For each one, ask:

- Does the query use a pattern that generalises? A reader should be able to swap in a different IRI and get a different-but-sensible result.
- Does it demonstrate a non-obvious access pattern that the reader would not guess from the ShEx alone? (Measurement scaffolds, blank-node activity records, and reified statements are prime candidates.)
- Does it include a `LIMIT`? (Always.)
- Does it include comments explaining non-obvious choices (why this predicate, why this filter)?

A query that passes all four is carrying its weight. A query that just demonstrates "you can SELECT things" is not.
