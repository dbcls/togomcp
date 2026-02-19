# TogoMCP QA Review Prompt

> **Usage:** Paste this prompt into a new Claude session. No file attachment needed — Claude reads everything automatically and updates this file when done.

---

You are a strict QA reviewer for a TogoMCP evaluation question set.

**Step 1 — Find the next unreviewed question.**
Read the progress tracker table at the bottom of this prompt. Find the first question whose Status is `—` (not yet reviewed). That is your target question number (e.g., `007`).

**Step 2 — Read the question file.**
Use the `Filesystem:read_text_file` tool to read:
```
/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml
```
(replace `XXX` with the zero-padded number you identified in Step 1).

**Step 3 — Run all checks.**
Read the file in full, then check every error category below.

For each issue found, report:
- **Error code** (e.g., C02)
- **Evidence** — exact quote from the YAML field
- **Explanation** — why this violates the creation guide

At the end, give a **Verdict**: `PASS` | `MINOR ISSUES` | `MAJOR ERRORS` with a one-sentence summary.

---

## Error Categories

### 🔴 CRITICAL

**[C01] Circular Logic**
Is the ideal_answer derived from the same query used to construct the question? Could the question only be answered by re-running the exploration that produced it — i.e., is it self-fulfilling?

**[C02] Coverage Gap — Query scope narrower than question scope**
For questions asking "which X", "how many X", "list all X", yes/no existence, or summary questions:
- If vocabulary exploration discovered N ontology terms (GO, MONDO, ChEBI, etc.), does the SPARQL `VALUES` clause use **all** N terms?
- If exploration found a set of entities, does the query process **all** of them — not a sampled subset?
- Does the question ask comprehensively while the SPARQL only covers a portion?

**[C03] Arithmetic Verification Missing or Failed**
If any SPARQL query uses `GROUP BY` or counts by category:
- Is there a verification query confirming `sum of category counts = total unique entities`?
- If `sum > total`, is the overlap explained in `ideal_answer`?
- If `sum < total`, was the coverage gap caught and fixed?
- If `GROUP BY` is present but no verification query exists, flag it.

**[C04] Vocabulary Sampling**
- Were ontology terms discovered (GO, MONDO, ChEBI, MeSH, EC)?
- Were `OLS4:getDescendants()` results obtained?
- Does the SPARQL `VALUES` include **all** discovered terms, including all descendants?

**[C05] Unverified Filter Heuristic**
Were entities filtered using taxonomy ID ranges, name-pattern matching, or manual "eyeballing" — without a count-verification query confirming `(before filter) = (filtered) + (remaining)`?

**[C06] Reverse Engineering**
Is the question scope (e.g., "SLE-associated genes") broader than the set of entities actually queried (e.g., only one of several SLE genes)?

**[C22] Literature-Recoverable Answer**
Could a PubMed search + abstract reading fully answer this question without querying any RDF database? If yes, check whether `rdf_necessity` score is ≥ 2. Flag if score is 0 or 1.

**[C23] Biological Insight = 0**
Is `biological_insight` scored 0 or 1? Does the question merely inventory database contents with no mechanistic, functional, or evolutionary insight?

---

### 🟠 MAJOR

**[C07] Famous Entity**
Does the question body involve BRCA1, TP53, insulin, aspirin, glycolysis, E. coli K-12, or other canonically famous examples explicitly prohibited by the guide?

**[C08] Wrong Question Type**
Does the `type` label match the actual question structure?
- `yes_no` → binary, no enumeration required
- `factoid` → single value or count
- `list` → enumerable set
- `summary` → multi-dimensional aggregation, single-paragraph answer
- `choice` → comparison among bounded options

**[C09] Type Distribution Violation**
Does this `type` have more than 12 uses across all 50 questions (hard cap)? Check whether `type` was already at ≥ 10 uses when a different under-represented type (< 8 uses) should have been prioritized.

**[C10] Structured Vocabulary Check Skipped**
Was `bif:contains` or free-text search used for a concept where GO / MONDO / ChEBI / EC / MeSH should have been checked first? Is there a note in the YAML documenting why no structured IRI was available?

**[C11] Descendants Not Fetched**
If an ontology term (GO, MONDO, etc.) was found, is there evidence that `OLS4:getDescendants()` was called and all descendants were included in the query?

**[C12] PubMed Test Invalid**
Did `pubmed_test` actually attempt to **answer** the specific question (retrieve the count, list, or fact), or did it only confirm the topic exists in literature? A valid test must try — and fail — to retrieve the specific answer.

**[C13] Single Database Only**
Does `togomcp_databases_used` contain only one database? If so, is there documented justification?

**[C14] Database Post-Selection**
Were databases chosen because results appeared there during keyword exploration, rather than for biological complementarity defined before exploration began?

**[C15] Format Error — `exact_answer` type**
- `yes_no` → string `"yes"` or `"no"`
- `factoid` → single string or number
- `list` → YAML array (even for a single item)
- `choice` → YAML array, items must exist in the `choices` field
- `summary` → empty string `""`

**[C16] Format Error — SPARQL queries**
Each entry in `sparql_queries` must have: `query_number` (sequential), `database`, `description`, `query`, `result_count`.

**[C19] Inventory Question**
Does the question ask about database structure or metadata rather than biology? (e.g., "How many entries does UniProt have for kinases?" = inventory = prohibited.)

**[C21] Unbounded Scope**
For `list` or `summary` questions: is the scope verifiable (5–100 members), or is there a stated top-N justification? Flag if neither applies.

---

### 🟡 MINOR

**[C17] Format Error — RDF triples**
Every triple must be followed by a comment in the form:
```
# Database: X | Query: N | Comment: ...
```
Flag any triple without this annotation.

**[C18] Vague Wording**
Does the `body` use "bind", "contain", "have", "associated with", or "interact with" without a qualifying adjective (e.g., "annotated with", "co-crystallized with", "documented")?

**[C20] Undocumented Overlap**
If `sum of GROUP BY counts > total unique entities`, is the shared membership explicitly explained in `ideal_answer`?

**[C24] Keyword-Workflow Violated**
Does the question type feel force-fitted to the keyword topic, suggesting the keyword was chosen before type and database selection? (Assess from internal consistency of `inspiration_keyword`, `type`, and `togomcp_databases_used`.)

**[C25] UniProt Cap**
Is UniProt listed in `togomcp_databases_used`? If this question pushes cumulative UniProt usage past 35 of 50 questions (70%), flag it.

---

## Output Format

```
## question_XXX QA Report

### Issues Found

**[Cxx] Category Name** (CRITICAL / MAJOR / MINOR)
Evidence: "<exact quote from YAML>"
Explanation: <why this is a problem>

... (repeat for each issue)

### Verdict
PASS | MINOR ISSUES | MAJOR ERRORS
<One-sentence summary.>
```

If no issues are found in a category, skip it. End with the verdict.

---

**Step 4 — Update this file.**
After producing the report, use `Filesystem:edit_file` to update the progress tracker table in this file (`/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/togomcp_qa_prompt.md`):

1. Replace the `—` in the **Status** column with the verdict code:
   - `PASS` → `P`
   - `MINOR ISSUES` → `W`
   - `MAJOR ERRORS` → `F`
2. Replace the `—` in the **Issues** column with a comma-separated list of triggered error codes (e.g., `C11, C18`). If no issues, leave `—`.
3. Recount and update the **Summary** line at the bottom of the table accordingly.

Example: if question 006 has minor issues C11 and C18, change:
```
| 006 | — | — |
```
to:
```
| 006 | W | C11, C18 |
```

---

## Progress Tracker

Mark: `P` = pass · `W` = minor issues · `F` = major errors

| #   | Status | Issues |
|-----|--------|--------|
| 001 | P      | —      |
| 002 | P      | —      |
| 003 | P      | —      |
| 004 | P      | —      |
| 005 | P      | —      |
| 006 | P      | —      |
| 007 | P      | —      |
| 008 | P      | —      |
| 009 | P      | —      |
| 010 | P      | —      |
| 011 | P      | —        |
| 012 | P      | —      |
| 013 | P      | —      |
| 014 | P      | —      |
| 015 | P      | —      |
| 016 | P      | —      |
| 017 | P      | —      |
| 018 | P      | —      |
| 019 | P      | —      |
| 020 | P      | —      |
| 021 | P      | —      |
| 022 | P      | —      |
| 023 | P      | —        |
| 024 | P      | —      |
| 025 | P      | —      |
| 026 | P      | —      |
| 027 | P      | —      |
| 028 | P      | —        |
| 029 | P      | —      |
| 030 | P      | —        |
| 031 | P      | —      |
| 032 | P      | —        |
| 033 | P      | —        |
| 034 | P      | —      |
| 035 | P      | —      |
| 036 | P      | —      |
| 037 | P      | —      |
| 038 | P      | —      |
| 039 | P      | —      |
| 040 | P      | —      |
| 041 | P      | —      |
| 042 | P      | —      |
| 043 | P      | —      |
| 044 | W      | C18    |
| 045 | P      | —      |
| 046 | P      | —      |
| 047 | P      | —      |
| 048 | P      | —      |
| 049 | P      | —      |
| 050 | P      | —      |

**Summary:** `P` = 49 &nbsp;·&nbsp; `W` = 1 &nbsp;·&nbsp; `F` = 0 &nbsp;·&nbsp; Reviewed: 50 / 50
