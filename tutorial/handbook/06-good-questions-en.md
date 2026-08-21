# 06. How to Ask a Good Question

For researchers outside informatics, this is the chapter **most worth taking away**.

The five elements below are not general advice. They are the **causes we actually observed** when we ran two versions of the same question against live databases in [Chapter 4](04-advanced-queries-en.md).

---

## The contrast, at a glance

| | Vague question | Specified question |
|---|---|---|
| Wording | "Tell me about genes involved in cancer" | "First identify the MeSH descriptor for 'Pancreatic Neoplasms', then…" |
| Time | **12 s** | 182 s (**~15× longer**) |
| Tool calls | **1** | 8 |
| SPARQL executions | **0** | 4 |
| MIE consulted | no | yes |
| Identifiers verified | **none** | MeSH D010190, resolved live |
| COUNT cross-check | no | yes — and it found a flaw |
| Provenance stated | no | database, graph, and predicates, all of it |
| **Reproducible** | **no** | yes, from the full query text |

Twelve seconds is not fast. **It is fast because nothing happened.**

---

## The five elements

### 1. Name the target with a controlled vocabulary and a way to resolve it

> "**In MeSH**, first **identify the descriptor** for 'Pancreatic Neoplasms'"

**What the vague version did:** the word "cancer" went straight into a full-text search, where it silently became a **completely different question** — "does the protein's *name* contain the string 'cancer'?" What came back was NY-ESO-1 and recoverin.

**What changed:** `search_mesh_descriptor` ran and produced **D010190, a verified IRI**. Every subsequent query was anchored to that single IRI, so the match became a **strict structured lookup** (`oa:hasBody <mesh/D010190>`) and the string matching disappeared.

> **Naming a vocabulary is enough to switch the tool selection from "full-text search" to "resolve an ID, then match on structure."**

Vocabularies worth naming: **MeSH** (diseases, medical concepts), **GO** (function, localization, process), **MONDO / NANDO** (diseases), **HP** (phenotypes), **UBERON** (anatomy), **ChEBI** (compounds), **NCBI Taxonomy** (organisms).

### 2. Demand the provenance — database and field names

> "**state the source database and field names**"

**The vague version:** nothing asked for sources, so **there was no reason to read the MIE**. No SPARQL meant no chance to pin a graph either. The structure of the request let an answer from memory pass as complete.

**The specified version:** the moment provenance became an obligation, `get_MIE_file(pubtator)` became a **mandatory prerequisite**. That MIE then disclosed three traps in advance — the predicate values are case-fixed, the target graph is a single named graph, and, critically, **the gene annotations do not distinguish species**.

> **"Cite your sources" is not a formatting request. It functions as a trigger that forces the schema to be read.**

### 3. State the species and the scope

> "**human** genes"

**The vague version:** nobody said anything about species, yet **`organism_id:9606` was silently added**. That is a specification invented on your behalf, where you cannot see it. Had the subject actually been mouse, a wrong answer would have come back and nobody would have noticed.

**The specified version:** the MIE's warning — this literature-annotation data **does not separate human genes from model-organism orthologs** — triggered a **concrete countermeasure**, a join that filters on taxon. Without it, identically named mouse and rat genes would have crept in and inflated the numbers **with no error and no empty result**.

> **Naming the species is not a filter. It is a switch that causes work to happen which prevents silent contamination.**

### 4. Fix the count and the ordering criterion as numbers

> "**the top 20, ordered by strength of association, as a table**"

**The vague version:** with no count specified, "about ten" was chosen unilaterally, and the ordering became "by fame" — **a criterion that cannot be defined**, and therefore cannot be verified or refuted.

**The specified version:** "top N, ordered" was translated into an **executable definition**: `GROUP BY … ORDER BY DESC(COUNT(DISTINCT ?article)) LIMIT 20`. At the same time, an operational definition — *strength of association = number of co-occurring papers* — was made explicit. That is what made the criticism in [Chapter 4](04-advanced-queries-en.md) **sayable at all**: co-occurrence is not causation. In the vague version there was no definition to criticize.

> **Demanding an ordering criterion forces "strength" to be reduced to a measurable quantity. Whether that reduction is valid can only be argued once the reduction is on the table.**

### 5. Demand an independent cross-check (COUNT)

> "**and cross-check the counts with COUNT**"

**Of the five, this one did the most work.**

Without it, a table reading "TP53 = 1,581" would have gone out unchallenged. The COUNT produced two numbers — 236,144 papers annotated with the disease, and 32,597 in which TP53 genuinely co-occurs — and the fact that the ratio did not add up **exposed a methodological flaw: the 20,000 rows taken by the inner LIMIT were not a uniform sample.**

**And when the counts were redone exactly, the ranking itself changed** — MTOR moved from 20th to 9th, INS from 6th to 16th. **Not just the absolute numbers: the ordering could not be trusted either.**

> **"Cross-check with COUNT" is not proofreading. It is a detector that exposes sampling bias and counting traps. No other single line you can add returns as much.**

---

## Templates you can use as-is

### General template

```
First identify [TARGET] using [VOCABULARY] ([ID or term]),
then list the [UNIT OF OUTPUT] that satisfy [RELATION],
top [N], ordered by [CRITERION], as a table,
stating the source database and field names for each.
Cross-check the counts with COUNT as well.
```

### By purpose

**Look up a protein**
```
Identify human [PROTEIN] in UniProt (give me the accession),
then summarize its function, sequence length, subcellular localization,
and associated diseases — indicating which UniProt field each came from.
```

**Enumerate proteins with a given function**
```
List human proteins annotated with GO [TERM] (GO:XXXXXXX),
restricted to reviewed entries.
Give both COUNT(DISTINCT) and COUNT(*), and if they differ,
explain what is being duplicated.
```

**Find molecules associated with a disease**
```
First identify the MeSH (or MONDO) ID for [DISEASE],
then list the top N associated human genes,
stating explicitly how you are defining "strength of association" —
and what that definition does and does not measure.
```

**Search structures with conditions**
```
Find PDB structures of [TARGET], restricted to [EXPERIMENTAL METHOD],
top N by best resolution.
Also give the breakdown of entry counts per experimental method.
```

**Cross identifiers**
```
Convert these IDs to [TARGET NAMESPACE].
If any could not be converted, say so explicitly.
```

That last line matters. **A count that shrank silently is the most dangerous kind.**

---

## And the ways of asking that you should avoid

| ✗ | Why it fails | ✓ |
|---|---|---|
| "Tell me about X" | "About" is undefined, so it can be answered from memory | "Give me [SPECIFIC ATTRIBUTE] of X from [DATABASE]" |
| "What are the important genes?" | "Important" is not measurable | "Top N by [METRIC], descending" |
| "Everything that's related" | "Everything" explodes at runtime; most of these time out | "Top N. Give the total separately with COUNT" |
| "What's the latest?" | A database does not know what "latest" means | "Entries deposited or updated since [YEAR]" |
| "Is this right?" | An AI tends to agree with you | "Find evidence in the databases that **contradicts** this claim" |

The last row is especially effective. **Do not ask "is this right?" — ask for the counter-evidence.**

---

## About the cost

Satisfying all five elements takes roughly **15× longer**. You do not need to do it every time.

| Situation | What to use |
|---|---|
| Exploring, getting a rough sense | Element 1 (identify the target) is enough |
| For discussion, or a slide | Elements 1, 3, 4 |
| **For a paper or a formal report** | **All five. No exceptions.** |

For any number that goes into a paper, **satisfy all five**. If you put a number that came back in twelve seconds into a manuscript, you will not be able to answer for it at review.

---

Next → [07. Verification and Reproducibility](07-verification-en.md)
