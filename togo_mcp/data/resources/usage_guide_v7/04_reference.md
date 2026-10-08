## ✍️ OUTPUT QUALITY

- Each fact exactly once.
- No meta-commentary ("Based on my analysis", "In summary", "As established above").
- No reasoning leakage in the final answer.
- Prose **or** list — not both.
- Partial data: state what was found and what wasn't. No padding.

---

## 🆘 TROUBLESHOOTING

The most common cases. The full table (REGEX, TogoID relation-graph joins, HTTP 403, rotted
IRIs, known-hard query patterns) is reference file `troubleshooting.md`.

| Problem | Fix |
|---------|-----|
| 3rd consecutive SPARQL | Stop. Pivot to search / NCBI / TogoID / partial synthesis. |
| Empty SPARQL results | **Read the `#` diagnosis block `run_sparql` prepends** — it names the two causes and the probe. Not an endpoint failure. Then: structured predicates from MIE; extract IRIs via search first. Typed literal missing (`^^xsd:string`)? Predicate applied to the wrong node? |
| Aggregate came back `0` | Same thing in aggregate form — `COUNT` over an empty match is one row of `0`, so it *looks* structurally fine. The diagnosis block fires here too; decide true-negative vs broken-pattern before reporting a zero. |
| **Count inflated** (2×, 4×, 8×) — or right but unproven | Co-tenancy. `GRAPH ?g` the pattern with its subject bound: >1 graph → re-declared; none of yours → foreign predicate, i.e. a silent intersection. Pin **every** pattern. `DISTINCT` hides it, doesn't fix it. |
| TogoID empty | Check ID format with `togoid_getDataset(src)`. |
| ≥15 tool calls, no answer | Synthesize from partial data. Partial + honest > wrong + exhaustive. |
| Repetitive answer | Remove any sentence restating an earlier point. |
| OLS4 / PubMed unavailable | → `search_mesh_descriptor` / `ncbi_esearch`. |
| **A tool named in this guide is absent from your tool list** (canaries: `get_workflow`, `pubcasefinder_rank_by_phenotypes`) — or a tool you call returns "unknown tool" (`find_databases`, `list_categories`), or a result ends with a `[TogoMCP notice]` that the name you called is outdated | Your MCP client cached the tool list when the connector was added and has not refetched it. **Tell the user in your answer** that the TogoMCP app must be updated in their client. In ChatGPT that is an admin task on Business (recreate and republish the app) and Enterprise/Edu (Action control → Refresh, then enable the new tools); on Pro, delete and recreate the TogoMCP plugin. Common with ChatGPT, which freezes the tool list — some clients are running lists months stale. Do not retry the missing name or invent a substitute. **Databases are unaffected**: the catalog in this guide is served live, so any database key listed there works even when your cached tool schema does not name it. |

---

## 📎 MORE DETAIL — reference files, fetched on demand

This guide is the core. Each file below is fetched with
`get_workflow(name="usage-guide", path="references/<file>")` — one call, returns plain
Markdown. Fetch one **only when its trigger applies**; none is needed for an ordinary
bounded question.

| File | Fetch when |
|---|---|
| `database-catalog.md` | Catalog lines above do not separate your 2–3 candidate databases (full descriptions + all keywords). |
| `co-tenancy.md` | A count looks inflated, a join returns 0 unexpectedly, or pinned ≠ unpinned (worked examples + probe queries for traps 1–11). |
| `endpoints.md` | Writing a `SERVICE` federation query; an HTTP 403 / HTML reply; planning around graph multiplicity. |
| `troubleshooting.md` | The table above does not cover your failure; also lists known-hard query patterns with fallbacks. |
| `bulk-mode.md` | GATE 0a routed you to bulk/heavy retrieval. |
| `budgets.md` | You want the per-tool score tiers behind the budgets. |

If `get_workflow` is not in your tool list, your client's tool list is stale (see the
TROUBLESHOOTING row above): the core alone is sufficient to answer — proceed without the
reference files.