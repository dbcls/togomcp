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
| `get_workflow` | Step-by-step procedures for multi-step analyses (Chapter 5) |

### Layer 2: the grounding layer — turns "words" into "IDs"

| Tool | Conversion |
|---|---|
| `search_uniprot_entity` | protein name → UniProt accession |
| `search_chembl_molecule` / `_target` | drug or target name → ChEMBL ID |
| `search_pdb_entity` | description of a structure → PDB ID |
| `search_mesh_descriptor` | disease name → MeSH descriptor |
| `search_reactome_entity` / `search_rhea_entity` | pathway name, reaction → ID |
| `togoid_identifyId` | an ID of unknown origin → which DB it belongs to |
| `togoid_convertId` | **ID → ID in another DB** |
| `ncbi_esearch` / `ncbi_esummary` / `ncbi_efetch` | the NCBI family |
| `togovar_search_gene` / `_variant` / `_disease` | genes, variants, diseases (Japanese population data) |
| `pubcasefinder_rank_by_phenotypes` / `_get_case_reports` | symptoms (HPO) → ranked candidate rare diseases, case reports |

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
    intent: sequence + mass of a protein's canonical isoform
    sparql: |
      PREFIX up: <http://purl.uniprot.org/core/>
      PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      SELECT ?isoform ?sequence ?mass
      FROM <http://sparql.uniprot.org/uniprot>
      WHERE {
        uniprot:P01308 up:sequence ?isoform .
        ?isoform a up:Simple_Sequence ;
                 rdf:value ?sequence ; up:mass ?mass .
        FILTER(STRSTARTS(STR(?isoform),
               "http://purl.uniprot.org/isoforms/P01308-"))
      }
    verified: {row_count: 1, date: "2026-09-14"}
    traps_avoided:
      - say: Do not hard-code the canonical as isoforms/ACC-1.
             782 entries have a canonical other than -1
        check: {kind: count, expect: 782}
```

(Excerpted and simplified from the UniProt MIE as of 2026-10-01.)

| Element | The job it does |
|---|---|
| `sparql` | ① **the shape of the schema itself** (which predicates connect to what) |
| `verified` | ② **sample real data** (how many rows, and which values, actually came back) |
| `traps_avoided` | ③ **a warning** (the pitfall specific to this database) |

Instead of writing the same content three times as "schema description," "sample," and "note," it is **condensed into one example that runs**.

The warning also carries a `check:`: a query that asks the live endpoint whether "782 entries" is still true. **What a MIE says is managed not as its author's memory but as a claim that gets re-verified.**

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

**Reason 1: it prevents IRI hallucination.** Without reading the MIE, the AI guesses — "the predicate is probably called something like this." Write a **nonexistent predicate** such as `up:hasSequence` and SPARQL will not raise an error. **It returns 0 rows.** And the AI tends to report "no matches." This is an extremely hard failure to detect.

> 📝 **Since 2026-08-29 (TogoMCP 2.10), `run_sparql` annotates an empty result.** Is the data genuinely absent, or is one line of the query wrong and the real answer non-zero? The note tells the AI how to tell those two apart. In the server's logs, empty results were about 7.6 times as frequent as errors, and before the note existed most of them reached users as "no matches."
>
> But it is **a note, not an error**. Nothing guarantees the AI reads it and acts on it. **When the answer is 0 rows, be suspicious first** (Chapter 8).

**Reason 2: it steers you away from slow forms.** Two queries that return the same answer can differ a great deal in runtime depending on how they are written. The guide spells out a speed hierarchy.

```
specific IRI  ≫  narrowing by type  ≫  FILTER(CONTAINS(...))
    fast                              slow (effectively impossible on large graphs)
```

**But do not use elapsed time as your yardstick.** The August edition of this handbook said that a query fetching insulin's sequence with `FILTER(CONTAINS(STR(?seq), "/P01308-1"))` died at the 60-second timeout, and that naming the IRI directly brought it back in about 5 seconds. Re-run on 2026-10-01 in nearly the same form (no graph pin, `FILTER(CONTAINS)`, two `OPTIONAL`s), it **came back in 10 seconds**, but with **219,437 rows**. Pinning the graph with `FROM` gives **919 rows in 1.4 seconds**.

Runtime depends not only on how a query is written but on the state of the endpoint's cache. TogoMCP's own records include a query that took over 75 seconds and returned in 0.1 seconds on the very next run. Hence TogoMCP's policy: **never judge a query's correctness from how long it took.** Fast may only mean warm. And every silent-wrong-answer trap in this handbook comes back fast.

> 📝 **One more correction.** The August edition taught "name the canonical sequence directly as `isoforms/P01308-1`." For insulin that happens to be right, but as a general rule it is wrong. Swiss-Prot has **782 entries** whose canonical isoform is not `-1` (fibronectin P02751's is `-15`), and in 613 of them a `-1` node still exists as a different isoform. Hard-coding `-1` does not give you 0 rows; it **silently gives you a different sequence**. The UniProt MIE fixed this rule on 2026-09-14 (the example above).
>
> **MIE files can be wrong too. When they are, the endpoint's actual data decides** (in the usage guide's words: "The MIE describes; the ENDPOINT decides").

---

## 3-6. The traps — not "the wrong answer" but "the wrong count"

Most failures in life-science RDF happen **silently**. No error appears. A plausible-looking table comes back. The numbers are just wrong.

### (a) Federation (`SERVICE`): only the verified combinations

The `SERVICE` clause joins multiple endpoints in a single query. On rdfportal.org it is **not disabled** — this handbook said it was until 2026-08-26, and that was wrong. A bounded `SERVICE` genuinely reaches out and returns real rows: 13 of 14 external endpoints tested were reachable in 2026-08, and a query against a nonexistent host fails with a connection error (`HTCLI HC001`) rather than being answered locally, which is how we know the traffic is real.

What fails is `SERVICE` **in practice**, for two reasons that matter more than availability:

- **An unbounded federated join does not finish.** Joining a whole Rhea column to a whole UniProt column across endpoints ran past 130 seconds with no result. Federation makes the remote side re-evaluate for every binding, and neither engine can plan across the boundary.
- **Virtuoso's federation compiler rejects common SPARQL inside a `SERVICE` block.** An aggregate fails immediately with `SP031` ("the support of aggregate function call syntax is not enabled for the SERVICE"); `BIND` expressions and some syntax hit the same wall.

**Since 2026-09, a few combinations have been verified on the TogoMCP side.** WikiPathways → UniProt, IDSM → Rhea, SwissLipids → Rhea, RDF Portal's `ebi` → LIPID MAPS and a few more now have a worked example (`cross_db`) in the relevant MIE, including how to narrow the join key first. **Direction matters.** Of the two lipid databases, SwissLipids reaches out in a few seconds while LIPID MAPS cannot reach out at all, and MarpolBase refuses `SERVICE` outright by permission.

So the practical advice is this: **if the MIE has a `cross_db` example, copy it.** Otherwise, **join within a single endpoint using `GRAPH` clauses**, or **carry IDs and walk across manually** (the Chapter 4 approach). "Disabled" would tell you not to try; "does not scale" tells you a small, bounded `SERVICE` is a legitimate tool when nothing else reaches. An unverified combination, though, comes with no guarantee.

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
