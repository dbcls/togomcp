# 05. Workflows with Skills

## MCP and skills are not the same thing

The MCP we have dealt with so far is **"capability"** — what can be done. Look something up in UniProt, send a SPARQL query, convert an ID.

**A skill** is **"methodology"** — by what procedure, in what order.

Two people can hold the same tools, and the quality of what they get out still depends on whether there is a written procedure. We saw exactly this in [Chapter 4](04-advanced-queries-en.md). Using the same set of tools, the vague question answered in 12 seconds without touching a database, while the specified question found its own error. **A skill is that difference, packaged so it can be reproduced.**

```
MCP  = the toolbox (what can be done)
Skill = the written procedure (how to use it, in what order, what to verify)
```

Think of a skill as what saves you from writing out by hand, every single time, the things Chapters 6 and 7 of this tutorial ask of you.

---

## The three skills

The TogoMCP server provides the following skills (it calls them *workflows*).

> **Where to get them:** nowhere — they come with the connection. Any client connected to TogoMCP (Claude, ChatGPT, Gemini, …) can use them with no installation. The Usage Guide lists them, and the model fetches the one it needs with the `get_workflow` tool. The copy on the server is always the current one, so a fix reaches you without doing anything.
>
> A local copy is optional. If you use Claude Code and want a skill to trigger on its own, the source is at https://github.com/dbcls/togomcp (under `togo_mcp/data/skills/public/`): put the skill's directory in `~/.claude/skills/<name>/`. If a local copy and the server's copy ever differ, the server's copy wins.
>
> ChatGPT note: ChatGPT keeps the tool list it saw when the connector was added. If `get_workflow` is missing from it, the connector needs refreshing (see Chapter 1).

### research-article-analysis — verify a paper's claims against databases

**What it does:** hand it a paper, and it will refuse to take the text at its word, checking the claims against databases one by one.

Molecular formulas, reaction equations, pathways, protein function, GO definitions — for each of them it builds an evidence chain of **ChEBI → Rhea → UniProt → Reactome → GO**, and returns a verification result per claim.

**Why it works:** because it hits **independent provenance**, not the fragments a keyword search returns ("this paper says so"). Whether a paper's statements are correct is not something you can determine by reading that paper.

**When to use it:** peer review, background work before attempting a replication, checking a paper you are about to cite, fact-checking your own manuscript.

```
Verify the biological claims in this paper against the databases.
(attach the PDF, or give the DOI / PMID)
```

### disease-analysis — map a disease across scales

**What it does:** takes a single disease and describes it at each level — **molecule → pathway → cell → tissue → clinical → treatment**. It combines TogoID, OLS4 and PubMed on top of TogoMCP.

**Why it works:** information about a disease is scattered across a different database at every level. Molecular defects in UniProt, pathways in Reactome, phenotypes in HP, disease concepts in MONDO/MeSH, treatments in ChEMBL. Joining them by hand is **half a day's work**.

**When to use it:** getting a grip on an unfamiliar disease quickly, early scoping for a research plan, understanding the field a collaborator works in.

```
Analyze the pathophysiology of Fabry disease across scales, from the molecular level to the clinical symptoms.
```

### PRISM — take the intersection of several conditions

**What it does:** finds entities that are "both A and B". The name is the initials of **P**redicate-defined, **R**eproducible, **I**dentifier-bridged, **S**et-intersection **M**ining.

- "targets associated with disease X that are also druggable"
- "genes involved in pathway P that are also modulated by an existing drug"
- "compounds associated with phenotype Q that are also substrates of enzyme A"

**Why it works, and the most important point:** PRISM **forces each condition (each axis) to be defined as a reproducible predicate**. It expands along the ontology hierarchy, triangulates across multiple sources of evidence, takes the intersection on stable IDs, and **leaves behind a provenance ledger**.

This is the machinery for doing the four verification steps of [Chapter 7](07-verification-en.md) automatically, with nothing missed.

> The skill's own description contains a line like this —
> **"If you catch yourself about to list candidate genes from memory, stop and use PRISM."**
>
> That is the failure demo of [Chapter 4](04-advanced-queries-en.md), precisely.

**When to use it:** drug repositioning, drug-target identification, any question of the form "what do these two sets have in common?"

```
Use PRISM to find genes associated with [DISEASE] that are also modulated by an existing approved drug.
```

Applications with a track record include lipid transport in age-related macular degeneration, and the analysis of Pompe disease.

---

<!-- workshop-only -->## How skills are handled in the workshop

**Skills are introduced only, in this workshop.** We will not install them on the spot.

- Live, we will **run exactly one of them to completion** (`research-article-analysis` is recommended — the input is a single paper, which is easy to follow, and the output is a "verification result per claim" table, which is easy to read)
- For the remaining two, **complete outputs produced in advance** are handed out as materials
- If you want to try them, install them yourself from the GitHub repository above<!-- /workshop-only --><!-- public-only -->## To try them

You do not need to install anything: just ask, naming the skill if you want to be sure it is used (for example, "Use the research-article-analysis workflow to …"). `disease-analysis` also uses the OLS4 and PubMed MCP servers (Chapter 1), so connect those for it. **If you are trying one first, we recommend `research-article-analysis`** — the input is a single paper, which is easy to follow, and the output is a "verification result per claim" table, which makes it easy to read what happened.

Hand it a paper from your own field, and see **how far the claims can be backed up by databases**. You will see the verification discipline of Chapter 7 automated as it stands.<!-- /public-only -->

---

## Deciding whether to use a skill

| Situation | Recommendation |
|---|---|
| A one-off, simple query | No skill needed. The templates in Chapter 6 are enough |
| The same kind of work, repeated | **Use a skill.** The variation in procedure disappears |
| Results going into a paper | **Use a skill.** The provenance is kept automatically |
| You want to share or review the procedure itself | **Use a skill.** The procedure exists as a file |
| Exploring, feeling your way | A skill can get in the way. Ask plainly |

The essential value of a skill is that **the same procedure is followed even when you are tired, even when you are in a hurry**. As the failure demo in Chapter 4 showed, skipping the procedure gets you an answer in 12 seconds. And nothing on the screen tells you that anything was skipped.

---

## Writing your own skill

A skill is a Markdown file. In `SKILL.md` you write when to use it (`description`), and by what procedure the work is to be done.

If your lab has procedures of its own — "in our analyses we always hit these three DBs and tabulate them in this format" — you can make that a skill. The existing skills in the TogoMCP repository serve as worked examples.

---

Next → [06. How to Ask a Good Question](06-good-questions-en.md)
