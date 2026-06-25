# Coverage gaps, arithmetic verification & banned entities

The two ways a question silently becomes wrong are **sampling** (querying less than the question claims) and **bad arithmetic** (counts that don't reconcile). These are the CRITICAL categories C02–C06. Treat this file as the gate for Phases 4–5.

## Valid exploration vs. sampling — decision tree

```
Did you discover entities during exploration?
├─ NO  → no coverage-gap risk, proceed.
└─ YES → What does the question ask about?
         ├─ a SPECIFIC entity you discovered (e.g. "TLR7")
         │    → query returns ALL of that entity's data  → ✅ VALID
         └─ ALL / WHICH / HOW MANY entities
              ├─ query processes ALL discovered entities  → ✅ VALID (comprehensive)
              └─ query processes a SUBSET                 → ❌ COVERAGE GAP
```

Rule of thumb: **question scope must equal query scope.** "Which order has the most X" requires checking *every* order, not the few you happened to see.

## The 6 coverage-gap types (C02/C04/C05/C06)

1. **Vocabulary sampling** — using 8 of 36 discovered GO terms (missing 33% of data).
2. **Entity pre-filtering** — filtering entities without a verification count, then categorizing the incomplete set.
3. **Database post-selection** — choosing databases because results appeared there during exploration.
4. **Filter targeting** — filters tuned to match the entities you already found.
5. **Cross-DB sampling** — `VALUES ?id { <specific IDs from exploration> }` inside a query that claims to be comprehensive.
6. **Reverse engineering** — question scope wider than query scope (asks about 5 SLE genes, queries 1).

## Arithmetic verification (mandatory for every GROUP BY)

**Checkpoint A — pre-filter count** (when filtering entities):
```
COUNT(*) before filter            = A
COUNT(*) after filter + remainder = B
A must equal B — if not, the filter dropped entities silently.
```

**Checkpoint B — post-aggregation** (UNIVERSAL for every GROUP BY):
```
Aggregation: SELECT ?cat (COUNT(?e) AS ?n) WHERE {…} GROUP BY ?cat
Verification: SELECT (COUNT(DISTINCT ?e) AS ?total) WHERE {…same criteria, no GROUP BY…}

sum(?n) == ?total  → ✅ mutually exclusive categories
sum(?n) >  ?total  → ⚠️  overlap — VALID only if explained in ideal_answer (C20)
sum(?n) <  ?total  → ❌ COVERAGE GAP — STOP, find the missing entities, fix
```
Record the checkpoint (numbers and the verdict) in the question file so a reviewer can re-derive it.

## Banned: famous entities (C07)

Do not build questions around canonically famous examples — they're likely memorized and fail the training test. Explicitly prohibited examples include: **BRCA1, TP53, insulin, aspirin, glycolysis, E. coli K-12**, and obvious peers (hemoglobin, p53 pathway, the lac operon, penicillin, etc.). Prefer less-trodden entities where the answer genuinely depends on current database state.
