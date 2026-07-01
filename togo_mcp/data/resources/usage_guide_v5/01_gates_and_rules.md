# TogoMCP Usage Guide (v5)

---

## ⛔ GATE 0 — BEFORE EVERYTHING ELSE

**Does the message contain a specific, bounded question?**
Bounded = a count, a list, a yes/no, a named entity, a comparison with a winner.

```
Bounded? YES → proceed to STEP −1
         NO  → EXPLORATION. Write Seed Definition now. No tools until it's done.
```

**NO signals:** "tell me more" / "go deeper" / "what about X?" / "深掘りして" /
any follow-up that extends a prior answer / any message with no bounded answer in advance.

> **Continuation trap:** Prior workflow does not carry forward. Re-run GATE 0 every turn,
> even if the last turn was SYNTHESIS or EXPLORATION. This is the most common miss.

---

## ⛔ GATE 0a — WORKLOAD TYPE (check this too, orthogonal to GATE 0)

Does the task require enumerating/processing a result set whose size is
unknown but plausibly large (counts in the thousands+), or comparing
full graph contents rather than a sample?

Signals: "all triples", "every X", "compare graph A vs B in full",
"how many total", "extract the full set of Y for offline analysis",
"audit/diff an ontology against its data usage".

```
Interactive (bounded, sample-sized) → proceed to GATE 0 as today
Bulk/heavy (large or unknown extent) → see BULK MODE section below.
  Do NOT run an unbounded SPARQL query directly — the endpoint has a
  ~60s ceiling and will very likely time out, burning a tool call for
  nothing. Probe size first.
```

---

## 🚫 CRITICAL RULES

**1. No filesystem or scripting tools — for interactive/bounded questions.**
8× slower, 2× more tool calls, wrong answers *in that regime*. If
post-processing feels necessary on a bounded question, the SPARQL query
is wrong — fix it instead. For bulk/heavy workloads (GATE 0a), see
BULK MODE — scripting is the correct tool there, not a workaround.

**2. Max 2 consecutive `run_sparql` calls.** Counter resets after any non-SPARQL call.
At call #3: stop. Pivot to a search tool, `ncbi_esearch`, `togoid_convertId`, or
synthesize from partial data.

| Max consecutive SPARQL | Avg score |
|------------------------|-----------|
| **1–2**                | **17.81** |
| 3–4                    | 16.55     |
| 8+                     | 16.43     |

---

## 🧠 STEP −1: ANALYZE (no tools)

**1. Question type** — EXPLORATION is the default when in doubt:

```
Bounded?
├── YES → "Does X exist?"              → VERIFICATION  (1–2 SPARQL)
│         "How many?" / "List all"     → ENUMERATION   (2–3 SPARQL)
│         "Which has most?"            → COMPARATIVE   (3–4 SPARQL)
│         "Summarize" / "Describe"     → SYNTHESIS     (2–3 SPARQL)
└── NO  → EXPLORATION                                  (1–4 SPARQL)
```

When ambiguous, take the lower branch. Seed Definition costs ~10 seconds;
wrong workflow costs 5–10 tool calls.

**2. Entities and databases.** List every distinct entity class → map to databases → map
to endpoints. If cross-endpoint, plan the TogoID bridge now.

**3. Comparative?** Must enumerate ALL categories with `GROUP BY ORDER BY DESC(?count)`.

---

## ⚡ QUICK START

```
GATE 0  → classify (bounded → STEP −1 | open-ended → Seed Definition)
STEP −1 → analyze
STEP  0 → find_databases(keywords=[...])   always first
STEP  1 → search tool or ncbi_esearch
STEP  2 → get_MIE_file(database)           always before run_sparql
STEP  3 → run_sparql()  LIMIT 10 first · max 2 consecutive
STEP  4 → synthesize    no repetition · no meta-commentary
```