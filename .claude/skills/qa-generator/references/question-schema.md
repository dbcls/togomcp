# Question YAML schema (distilled from QUESTION_FORMAT.md)

`benchmark/scripts/verify_questions.py` enforces all of the structural rules below — run it. The judgment rules (insight, scope, non-circularity) it cannot check; those are in [qa-checklist.md](qa-checklist.md).

## Required top-level fields (every question)

| Field | Type | Rule |
|---|---|---|
| `id` | str | `question_XXX`, zero-padded, **must equal the filename stem** |
| `type` | enum | one of `yes_no`, `factoid`, `list`, `summary`, `choice` |
| `body` | str | self-contained; specific named entities + qualifiers; **must NOT name a database**; avoid vague verbs ("bind/contain/have/associated with") without a qualifier ("annotated with", "co-crystallized with") |
| `choices` | list | **only for `type: choice`**; 2–10 items; ≥1 correct |
| `inspiration_keyword` | map | `keyword_id` (KW-XXXX), `name`, `category` — from `keywords.tsv` |
| `togomcp_databases_used` | list | ≥1 (≥2 strongly preferred); **every entry must appear as a `database` in `sparql_queries`** |
| `verification_score` | map | see rubric below |
| `pubmed_test` | map | `time_spent`, `method`, `result`, `conclusion` (must contain `PASS`) |
| `sparql_queries` | list | ≥1; each: `query_number` (sequential from 1), `database`, `description`, `query`, `result_count` (int ≥0, the **real** count) |
| `rdf_triples` | str | Turtle; **every triple line followed by** `# Database: X \| Query: N \| Comment: ...` |
| `exact_answer` | varies | format by type (below) |
| `ideal_answer` | str | synthesized expert prose; **no meta-references** ("according to UniProt", "the query", "the database shows"); single paragraph (no blank lines) for `summary` |
| `question_template_used` | str | name of the template/pattern used |
| `time_spent` | map | `exploration`, `formulation`, `verification`, `pubmed_test`, `extraction`, `documentation`, `total` |

**Optional:** `documents` (`{pmid, title, url}`), `snippets` (`{text, document, offsetInBeginSection, offsetInEndSection}`) — only if literature is referenced.

## `exact_answer` format by type (validator-enforced)

| Type | Format |
|---|---|
| `yes_no` | the string `"yes"` or `"no"` |
| `factoid` | a single string or number (e.g. `127` or `"JAK2 (UniProt:O60674)"`) |
| `list` | a YAML array (even for one item) |
| `choice` | a YAML array; **every item must appear in `choices`** |
| `summary` | empty string `""` (or null) |

## `verification_score` rubric — must total ≥9 AND no dimension = 0

Each dimension is an integer 0–3; `total` must equal the sum; `passed: true`.

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `biological_insight` | inventory only | basic | function/properties | mechanism/evolution |
| `multi_database` | search only | single/weak | 2 databases | 3+ databases |
| `verifiability` | unbounded | loosely bounded | 6–10 items | ≤5 items or single answer |
| `rdf_necessity` | PubMed suffices | helpful | significantly enhances | impossible without RDF |

Score honestly from the actual question — do not inflate to clear the gate. A question that can't legitimately reach 9 with no zeros is not a good question; pick a better angle.

## Type ↔ structure compatibility

- `yes_no` — binary existence/property; no enumeration.
- `factoid` — one retrievable value or count.
- `list` — an enumerable set, **5–100 members** (or a stated top-N).
- `summary` — multi-dimensional aggregation across **3+ databases**, answered as **one paragraph**.
- `choice` — comparison/count among the bounded `choices` options.
