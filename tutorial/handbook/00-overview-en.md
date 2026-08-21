# 00. Overview — Why TogoMCP

## The problem we are trying to solve

Over the past fifteen years, the major life-science databases have largely moved to RDF. UniProt, PDB, ChEMBL, Reactome — all of them are machine-readably searchable through a query language called SPARQL. In principle, a question like "which human lysosomal enzymes are targets of approved drugs?" should be answerable with a single query.

In practice it is not. There are three reasons.

**1. Few researchers can write SPARQL.** This is not a question of ability but of return on investment. It is not rational to keep up a skill you use a few times a year.

**2. Every database has its own vocabulary and its own graph structure.** In UniProt a protein is `up:Protein` and the relation to a gene is `up:encodedBy`. In PDB you traverse from `pdbo:datablock` through `pdbo:has_entityCategory`. Learning one gets you nothing for the next.

**3. Cross-database questions cannot be written without knowing each endpoint's quirks.** Which graph to specify, which predicates are fast, where the join breaks. This is often undocumented, and the failures are silent — you get no error, you get **the wrong count**.

TogoMCP is an **MCP server** that hands all three of these off to the AI assistant.

## What MCP is

**MCP (Model Context Protocol)** is a standard for handing "tools" to an AI assistant. It lets you bolt on connections to external data and services without rebuilding the AI itself.

```
    You    ──→  Claude, etc.  ──→  MCP server  ──→  external data
 (question)      (picks a tool)     (TogoMCP)      (SPARQL / REST)
```

What matters is the shift: **from what the AI "knows" to what it can "go and fetch."** Instead of recalling memories from its training data, it builds the answer by querying a database that is alive right now.

## What TogoMCP is

In one line:

> **An MCP server that makes the roughly 37 databases of RDF Portal queryable in natural language**

| Field | Databases |
|---|---|
| Proteins & proteomics | UniProt, PDB, jPOST |
| Genes & genomes | NCBI Gene, Ensembl, HGNC, OMA, Bgee, HCO, MCO, DDBJ, MoG+, TogoVar, GWAS Catalog |
| Chemistry | ChEMBL, PubChem, ChEBI, Rhea, BRENDA, MassBank |
| Pathways | Reactome |
| Disease & clinical | ClinVar, MedGen, MONDO, NANDO |
| Literature | PubMed, PubTator |
| Microbiology | BacDive, MediaDive, AMR Portal, NBRC |
| Glycans | GlyCosmos |
| Ontologies | MeSH, GO, HP, UBERON, CL, SO, ECO, EFO, PRO, FMA … |
| Taxonomy | NCBI Taxonomy |
| Materials science | SuperCon |

Having the Japan-originated databases (TogoVar, jPOST, GlyCosmos, NBRC, MoG+, NANDO, MediaDive) all in one place is a feature nothing else substitutes for. Chapter 4 makes that value concrete.

## Not "looks useful" but "measured and effective"

Tools of this kind are often impressive in a demo and useless in real work. For TogoMCP there is a quantitative evaluation.

In a comparison where the same problem set was solved with and without TogoMCP, the effect size was **Cohen's *d* = 1.82**, with ***p* < 0.001** by the Wilcoxon test.

> **Source:** Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042
>
> The figures above are **those reported in that paper**. They are not an independent measurement made for this tutorial.

An effect size of 1.82 is far beyond the conventional benchmark for "large" (0.8) in the behavioral sciences. But this is a **measurement on a benchmark problem set**, and it is no guarantee that you will see the same difference on your own research topic. Chapters 4 and 7 look concretely at the cases where it **does not** work.

> 💡 **Why the source is cited this carefully.** This tutorial will keep telling you not to believe a number that has no provenance. **The tutorial itself cannot then produce numbers without provenance.** The practice taught in Chapters 6 and 7 is observed in the body text as well.

## What this tutorial aims at

Three things.

1. **Get connected and be able to use it** (Chapters 1–2)
2. **Understand why it works** (Chapter 3) — without this, you are helpless when it does not
3. **Be able to doubt an answer and verify it** (Chapters 4, 6, 7)

Let me emphasize the third. What this tutorial spends the most time on is **not the examples that work, but the ones that do not**.

In Chapter 4 we deliberately throw a vague question at it. It comes back in 12 seconds with a fluent answer — and that answer **never once consulted a database**. What is more, nothing on the screen gives you a clue that this is so.

> **Being fast and confidently wrong is more dangerous than being slow and failing.**

Learning to tell the difference is the center of this tutorial.

---

Next → [01. Setup](01-setup-en.md)
