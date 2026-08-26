# 03. How It Works

Why can an AI write correct SPARQL against a database nobody taught it? The answer is not "because it is smart." **It is because we hand it the schema documentation.**

---

## 3-1. The shape of the data — groundwork for this chapter

If Chapter 0's "What RDF and SPARQL are" was enough for you, skip this. **The real subject of this chapter is the traps in its second half.** This section goes just far enough to make those legible.

An RDF database is a pile of **three-part statements — "the B of A is C."** Each of the three positions has a name.

```
  subject         predicate        object
     │               │               │
     ▼               ▼               ▼
  insulin ──── organism ─────────→ human
     │
     ├──────── length ───────────→ 110
     │
     └──────── associated ───────→ diabetes
                disease
```

Such a statement is called a **triple**. **A "count" is the number of triples matching your conditions** — that fact does the work later in this chapter.

### Names are shaped like URLs

The diagram above used English words. The actual data does not.

```
<http://purl.uniprot.org/uniprot/P01308>          ← subject   (insulin)
    <http://purl.uniprot.org/core/organism>       ← predicate (organism)
        <http://purl.uniprot.org/taxonomy/9606> . ← object    (human)
```

A name shaped like a URL is an **IRI**. They are long, so you give the leading part an alias — which is all the `PREFIX` lines at the top of a SPARQL query are.

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
#      ↑ from here on, up:organism means the long IRI above
```

> **📖 Why a URL shape?** Not so you can click it open. So that **the same thing carries the same name everywhere in the world.** If UniProt's "human" and NCBI's "human" are both `taxonomy/9606`, the two connect mechanically. That single fact is what lets Chapter 4 walk across several databases.
>
> The flip side: **if the IRIs differ, the machine treats them as different things — however identical they look to you.** Chapter 4 runs into exactly this.

### Graphs — compartments for triples

One store (an **endpoint**) often houses several datasets side by side. So triples are kept in compartments called **graphs**.

```
endpoint (sparql.uniprot.org)
 ├─ graph <.../uniprot>        ← UniProt's own triples
 ├─ graph <.../taxonomy>       ← organism triples
 └─ graph <.../another-dataset> ← something else living here
```

Writing `FROM <graph>` in SPARQL means **look only inside that compartment.** Leaving it out means **search across all of them.**

You may be thinking that since the answer comes back either way, this is a detail. **Section 3-6 demonstrates that it is not.**

### How to read a query (you do not have to write one)

SPARQL appears several times from here on. You do not need to be able to write it, but **knowing the shape lets you follow what the AI did.**

```sparql
SELECT ?protein ?mass                     # what to give back
FROM <http://sparql.uniprot.org/uniprot>  # which compartment to look in
WHERE {                                   # what shape of triple to look for
  ?protein up:mass ?mass .                #  subject  predicate  object
}
```

Anything starting with `?` is a **blank**. Find every triple of the form "the `up:mass` of `?protein` is `?mass`", and return the values that landed in the blanks as a table. **That is all.**

---

## 3-2. The overall structure

```
    You
     │  "For human insulin, …"
     ▼
 ┌─────────────┐
 │  Claude     │  ← picks the tools, builds the query, reads the results
 └─────────────┘
     │  MCP protocol
     ▼
 ┌─────────────┐
 │  TogoMCP    │  ← the tools themselves. Also hands out the documentation
 └─────────────┘
     │
     ├──→ SPARQL endpoints (rdfportal.org and others)
     └──→ REST APIs (UniProt, ChEMBL, PDB, NCBI, TogoID, TogoVar …)
```

TogoMCP is **not a mere relay**. On top of the ability to send SPARQL, it has the ability to **hand out knowledge** — "this database is shaped like this, write it this way and it is fast, here is where it fails." Without the latter, the former is useless.

---

## 3-3. The tools come in three layers

Sorted by role, the TogoMCP tools look like this. **Once you understand this three-layer structure, everything else is application.**

### Layer 1: the guidance layer — teaches you how to use it

| Tool | Role |
|---|---|
| `TogoMCP_Usage_Guide` | How to use the whole thing. Catalog of databases. Rules you must follow |
| `get_MIE_file` | **The schema documentation for each database** (below — the most important one) |
| `get_sparql_endpoints` | Which DB lives at which endpoint |
| `get_graph_list` | The graphs inside an endpoint |

### Layer 2: the grounding layer — turns "words" into "IDs"

| Tool | Conversion |
|---|---|
| `search_uniprot_entity` | protein name → UniProt accession |
| `search_chembl_molecule` / `_target` | drug or target name → ChEMBL ID |
| `search_pdb_entity` | description of a structure → PDB ID |
| `search_mesh_descriptor` | disease name → MeSH descriptor |
| `search_reactome_entity` / `search_rhea_entity` | pathway name, reaction → ID |
| `togoid_convertId` | **ID → ID in another DB** |
| `ncbi_esearch` / `ncbi_esummary` / `ncbi_efetch` | the NCBI family |
| `togovar_search_gene` / `_variant` / `_disease` | genes, variants, diseases (Japanese population data) |

**Why this layer is called "grounding":** it pins wobbly words like "insulin" or "pancreatic cancer" to immovable identifiers like **P01308** or **D010190**. Skip this layer and every step after it becomes guesswork. The failure demo in Chapter 4 is exactly what happens when this layer gets bypassed.

### Layer 3: the execution layer

| Tool | Role |
|---|---|
| `run_sparql` | Execute SPARQL |

Just one. **But you must not arrive here without reading Layer 1** — that is TogoMCP's single most important rule.

---

## 3-4. The MIE file — the core of the mechanism

A **MIE (Metadata Interoperability Exchange) file** is a YAML documentation file, one per database. The design goal is plain.

> **Give the LLM exactly enough information to write correct, fast SPARQL on the first attempt — no more, no less.**

"No more, no less" is the crux. Handing over the entire schema would be accurate, but it is far too large to be practical. An outline alone is not enough to write with. MIE files are built on the policy of **carrying only what the model cannot reconstruct on its own**.

### What is in a MIE

At the center of a MIE are **verified worked examples**. A single example does three jobs at once.

```yaml
examples:
  - id: sequence_mass
    description: Retrieve a protein's sequence and mass
    sparql: |
      PREFIX up: <http://purl.uniprot.org/core/>
      SELECT ?sequence ?mass
      FROM <http://sparql.uniprot.org/uniprot>
      WHERE {
        ?protein up:sequence ?seq .
        ?seq rdf:value ?sequence ; up:mass ?mass .
      }
    traps_avoided:
      - union_inflation: without pinning the graph in a FROM clause,
        rows from other co-resident datasets get picked up and the count inflates
    verified: 2026-07-29
```

| Element | The job it does |
|---|---|
| `sparql` | ① **the shape of the schema itself** (which predicates connect to what) |
| the execution result | ② **sample real data** (what actually comes back) |
| `traps_avoided` | ③ **a warning** (the pitfall specific to this database) |

Instead of writing the same content three times as "schema description," "sample," and "note," it is **condensed into one example that runs**.

### See it for yourself

You can check this yourself. Ask Claude:

```
Show me the UniProt MIE file. Just the examples section is fine.
```

---

## 3-5. The rule: "always read the MIE before SPARQL"

The TogoMCP usage guide carries several mandatory rules. This is the most important one.

> **Before calling `run_sparql`, always call `get_MIE_file` for that database.**

The rule is not there to be difficult. There are two reasons.

**Reason 1: it prevents IRI hallucination.** Without reading the MIE, the AI guesses — "the predicate is probably called something like this." Write a **nonexistent predicate** such as `up:hasSequence` and SPARQL will not raise an error. **It returns 0 rows.** And the AI reports "no matches." This is an extremely hard failure to detect.

**Reason 2: it prevents timeouts.** Two queries that return the same answer can differ in runtime by orders of magnitude depending on how they are written. The guide spells out a speed hierarchy.

```
specific IRI  ≫  narrowing by type  ≫  FILTER(CONTAINS(...))
    fast                              slow (effectively impossible on large graphs)
```

**A measured example:** a query that fetched insulin's sequence using `FILTER(CONTAINS(STR(?seq), "/P01308-1"))` **died at the 60-second timeout**. Rewritten to name the isoform IRI directly, it came back in about 5 seconds.

---

## 3-6. The traps — not "the wrong answer" but "the wrong count"

Most failures in life-science RDF happen **silently**. No error appears. A plausible-looking table comes back. The numbers are just wrong.

### (a) Federation (`SERVICE`) does not survive contact with real data

The `SERVICE` clause joins multiple endpoints in a single query. On rdfportal.org it is **not disabled** — this handbook said it was until 2026-08-26, and that was wrong. A bounded `SERVICE` genuinely reaches out and returns real rows: 13 of 14 external endpoints tested were reachable in 2026-08, and a query against a nonexistent host fails with a connection error (`HTCLI HC001`) rather than being answered locally, which is how we know the traffic is real.

What fails is `SERVICE` **in practice**, for two reasons that matter more than availability:

- **An unbounded federated join does not finish.** Joining a whole Rhea column to a whole UniProt column across endpoints ran past 130 seconds with no result. Federation makes the remote side re-evaluate for every binding, and neither engine can plan across the boundary.
- **Virtuoso's federation compiler rejects common SPARQL inside a `SERVICE` block.** An aggregate fails immediately with `SP031` ("the support of aggregate function call syntax is not enabled for the SERVICE"); `BIND` expressions and some syntax hit the same wall.

So the practical advice is unchanged: **join within a single endpoint using `GRAPH` clauses**, or **carry IDs and walk across manually** (the Chapter 4 approach). Only the reason is different — and the difference is worth knowing, because "disabled" tells you not to try, while "does not scale" tells you a small, bounded `SERVICE` is a legitimate tool when nothing else reaches.

### (b) Row inflation at co-resident endpoints

A single SPARQL endpoint may host several datasets side by side. When multiple datasets **each declare predicates** on a shared node (an organism IRI, say), a query that does not specify a graph picks up all of them, and **the row count inflates silently**.

The countermeasure is to pin the graph with `FROM <graph name>`, exactly as the MIE instructs.

```sparql
FROM <http://sparql.uniprot.org/uniprot>     ← write this
```

### 🔬 Try it: see the trap with your own eyes

**As long as you follow the MIE, this trap never fires.** The graph is pinned from the start. Which means that if you quietly obey, **you will never even learn the trap was there**.

So let us **break the rule on purpose.**

```
Take a query that counts human lysosomal lumen enzymes in UniProt and run it
both ways — one version with the graph pinned in a FROM clause, one without —
then compare the counts. Give both COUNT(*) and COUNT(DISTINCT).
```

That last sentence matters. **Without it, this trap stays invisible.**

**Measured (2026-08-21):**

| Version | `COUNT(*)` | `COUNT(DISTINCT ?protein)` |
|---|---|---|
| **`FROM` pinned** | **98** | **98** |
| **`FROM` not pinned** | **196** | **98** |

**Here is the crux.** The row count doubled, but **`COUNT(DISTINCT ?protein)` is 98 in both cases — a perfect match.**

So this is not the simple story of "leave the graph unpinned and the answer changes." **As long as you are using `COUNT(DISTINCT)`, the answer in this example comes out right anyway.** The dangerous one is `COUNT(*)`: use that and **the wrong number, 196, comes back with no error and no warning.**

Worse still, the inflation factor is not fixed. Depending on the target it may double or it may not. If you are using `AVG` or `SUM`, or stacking joins on re-declared predicates (2^k for k of them), **`DISTINCT` cannot absorb it and the answer itself goes wrong.**

### Track down where it came from

You can find out where the duplication came from by asking:

```
Which graph are those doubled rows coming from? Check with GRAPH ?g.
```

In the measurement, the `a up:Protein` typing was **supplied by two graphs** — UniProt itself, and another dataset co-resident at the same endpoint. Both declare the type on the same IRI, so without specifying a graph you get two rows per protein.

> **Learn this diagnostic move itself.** "When a count looks suspicious, count the suppliers with `GRAPH ?g`" transfers directly to real work.

### (c) Duplication from multi-valued predicates — this one does happen

Even after preventing (b), things can still inflate. That is the case where **one entity holds the same predicate more than once**.

**A measured example.** Counting the set of lysosomal lumen enzymes used in Chapter 4 gives this:

```
COUNT(*)                    = 62
COUNT(DISTINCT ?protein)    = 52      ← a 19% difference
```

The cause was that **a single protein carries several EC numbers**. Seven proteins were affected — for example —

| Gene | Number of EC numbers | Breakdown |
|---|---:|---|
| **GBA1** | **4** | 2.4.1.-, 3.2.1.-, 3.2.1.45, 3.2.1.46 |
| **ASAH1** | 3 | 3.5.1.-, 3.5.1.109, 3.5.1.23 |
| **SMPD1** | 2 | 3.1.4.12, 3.1.4.3 |

Naively counting rows, you would have reported "**62 lysosomal lumen enzymes**." The correct figure is 52.

> **The lesson:** before reporting a count, compare `COUNT(*)` against `COUNT(DISTINCT ...)`. If they differ, do not report until you can explain what is being duplicated.

Chapter 7 organizes this verification procedure.

---

## 3-7. Summary

1. TogoMCP is not "a tool for sending SPARQL" but **"a mechanism for handing out the knowledge of how it should be sent"**
2. The tools form three layers: **guidance / grounding / execution**
3. **The MIE file** is the core. Taking a verified worked example as its atomic unit, it conveys schema, real data, and traps all at once
4. The rules (read the MIE first, pin the graph) exist to prevent **silent failure**
5. Failures in life-science RDF surface **not as errors but as counts that are off**

---

Next → [04. Harder Questions](04-advanced-queries-en.md)
