# 08. Troubleshooting

## It will not connect

| Symptom | What to check |
|---|---|
| It says nothing at all about TogoMCP and answers in generalities | **Whether the connector is enabled in that conversation.** In Claude you have to select it from the "+" in every conversation. This is the most common cause |
| On Team/Enterprise, "Add custom connector" cannot be clicked | **The organization's owner has to add it organization-wide first** (→ [Chapter 01](01-setup-en.md)). An individual cannot add it |
| `claude mcp list` shows `✘ Failed to connect` | Check the URL. Did you drop the trailing `/mcp`? |
| It worked yesterday but not today (Claude Code) | Scope. The default `--scope local` only takes effect in that directory. Re-add it with `--scope user` |
| `claude mcp add` comes back with "no such command" | Are you typing it **inside** a Claude session? This is a command for **the terminal** |
| A tool call fails | Network. Possibly a corporate proxy or a VPN |
| ChatGPT says "there is no such tool" | **Re-run Scan Tools**, or delete the connector and add it again. ChatGPT does not re-fetch the tool list on its own |

---

## The query fails, or is slow

### It times out at 60 seconds

SPARQL has an upper limit on execution time. **Do not re-send the same query.** You will get the same result.

Remedies, in descending order of effect:

**1. Narrow the target by IRI.** `FILTER(CONTAINS(...))` and `FILTER(regex(...))` are effectively unusable on large graphs. Consider whether you can specify the IRI directly.

```
Measured: FILTER(CONTAINS(STR(?seq), "/P01308-1"))  → timeout at 60 s
          rewritten to specify the IRI directly     → about 5 s
```

**2. Cut down the `OPTIONAL`s.** Each one added makes it heavier. Get it working with the mandatory part first, and add the rest afterwards.

**3. Apply a `LIMIT`.** But ⚠️ **an inner LIMIT is not a uniform sample.** Read [Chapter 7](07-verification-en.md) — this is not optional. If you are going to report counts, you need a separate COUNT.

**4. Split it into stages.** Getting the IDs and then sending the next query is faster than one enormous query, and you can see what is happening on the way.

You can ask Claude for this:
```
That query is too heavy. Can you rewrite it to narrow by IRI?
Also propose a version with fewer OPTIONALs, or split into two stages.
```

### It returns zero rows

**Zero rows with no error is the most dangerous pattern of all.** SPARQL does not raise an error when a predicate name or a graph name is wrong.

The order in which to check:

1. **Did you read the MIE?** The predicate names in a query written without reading it are guesses
   ```
   Check the MIE file for [DATABASE] and confirm that the predicate names used actually exist
   ```
2. **Is the graph name right?** Graph names do get renamed. Specifying an old one gives you **a silent zero rows**
3. **Remove the filters one at a time.** Identify which condition drives it to zero
   ```
   Drop the conditions one at a time and find out where the results disappear
   ```
4. **Doubt the ID itself.** The source ID may not exist, or may have been renamed

### The counts look wrong

Go to [Chapter 3](03-how-it-works-en.md) and [Chapter 7](07-verification-en.md). The essentials only:

```
Give me both COUNT(DISTINCT ...) and COUNT(*). If they differ, explain what is being duplicated.
```

There are two main reasons for inflation — **the graph is not pinned**, and **the predicate is multi-valued** (one entity carries the same predicate several times).

---

## The answer is wrong, or strange

### What to doubt first is not the syntax — it is the definition of the target

The real case from [Chapter 4](04-advanced-queries-en.md): define "lysosomal enzyme" by UniProt's keyword KW-0458, and the insulin receptor and mTOR come in, and the approved-drug results end up dominated by insulin preparations. **The syntax was perfectly correct, and execution succeeded.**

```
I suspect this result contains things that should not be in it.
Explain how you defined the target, and what that definition does and does not include.
```

### When you suspect no database was consulted

**Symptoms:** the answer is too fast (in the ten-second range), the tool log shows no `run_sparql` or search tool, there are no accessions or IDs attached.

```
List the tool calls that this answer was based on.
Separate the values you retrieved from a database from the ones you did not.
```

That flushes out "it was actually answering from memory." → [the failure demo in Chapter 4](04-advanced-queries-en.md)

### The AI agrees with you

Ask "is this right?" and it tends to agree. **Demand the counter-evidence.**

```
Find evidence in the databases that contradicts this claim.
```

---

## The endpoint is down

**This actually happens.** In August 2026 there was an occasion when every SPARQL endpoint at rdfportal.org was unreachable.

**How to tell:** it is not one particular query — **`run_sparql` fails against every database**. Meanwhile `get_MIE_file` and the usage guide respond normally (these are files inside the server, so they do not depend on the external endpoints).

**What to do:**

1. **Wait.** There is nothing to do but wait for recovery
2. **Switch to the REST-based tools.** `togovar_*`, `ncbi_*`, `search_chembl_*` and others are a separate route, so they can still work while SPARQL is down
<!-- workshop-only -->3. **In the workshop, switch to the saved outputs** (→ below)<!-- /workshop-only -->

```
The SPARQL endpoint is not responding. Can you answer the same question using only the REST-based tools?
```

---

<!-- workshop-only -->
## For workshop instructors

### Before you start, without fail

- [ ] Connectivity check (run `get_sparql_endpoints` once)
- [ ] **Run every query you will use live, start to finish, and time them**
- [ ] If Team/Enterprise participants are attending, confirm the organization-side setup is done
- [ ] Confirm the fallback material (below) opens on the machine in front of you

### Fallback material is mandatory

**A network failure wiping out every demo is something that actually happens.** Prepare the following under `instructor/fallback/`.

- A **complete transcript of the run** for each demo (including the tool calls)
- **Screenshots** (always include ones with the logs expanded)
- Tables of results (with the measurement date stated)

**When to switch:** if one demo fails, retry on the spot at most once. On the second failure, give up and go to the fallback. **Silence in front of an audience is the worst outcome.**

### Rules for the live queries

- **Do not write SPARQL on the fly.** Use only what was fixed in advance and rehearsed
- **Do not re-send the same query.** The usage guide forbids it
- Put **the queries, not the tables of results**, in the handouts (results change day to day)

### Questions to expect

| Question | How to answer |
|---|---|
| "How many tokens does it use?" | The usage guide is **re-read on every message** (once per round trip, no matter how many times tools are called; it is designed that way). It is 44,570 characters ≒ 11,000–13,000 tokens. It accumulates over a long conversation |
| "Does it work on the free plan?" | It does. On Free you get one custom connector |
| "What about KEGG?" | Local stdio only. Because of the licence conditions for academic use (→ [appendix](99-appendix-local-install-en.md)) |
| "Is my own data sent anywhere?" | The question text, and the query where needed, are passed to the server. Tell people not to paste sensitive data |
| "Can I ask in Japanese?" | No problem at all. Every demo in this tutorial is in Japanese |

---

<!-- /workshop-only -->
## If that still does not solve it

- Issues on the repository: https://github.com/dbcls/togomcp
- Status of the hosted version: https://togomcp.rdfportal.org/

When you report, attach **the full text of the query that was executed, the endpoint, the date and time of execution, and the error message** (→ the save format in [Chapter 7](07-verification-en.md) works as-is).
