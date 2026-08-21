# 07. Believing the Result / Doubting It — Verification and Reproducibility

As we saw in [Chapter 6](06-good-questions-en.md), a good question makes the answer better. **But there are limits that remain even after you have made the question a good one.** This chapter deals with those.

One thing first, as a premise.

> **You cannot put the output of an AI into a paper as it stands.**
>
> Not because AI cannot be trusted, but because **without a record of what you verified, you cannot answer at review**. It is the same as not reporting an experimental result without having kept a lab notebook.

---

## 7-1. Five failure modes we actually observed

Every one of them occurred in the measured runs of [Chapter 4](04-advanced-queries-en.md). **None of them raises an error.**

### (a) Inflated counts

```
COUNT(*)                 = 62
COUNT(DISTINCT ?protein) = 52      ← a 19% gap
```

This happened because a single protein can carry several EC numbers (GBA1 has 4, ASAH1 has 3). Counting rows naively, we would have reported "**62 lysosomal lumen enzymes**."

### (b) Sampling bias

Having limited the inner query to 20,000 rows to avoid a timeout:

```
TP53 co-occurrences in the sample =  1,581
TP53 co-occurrences over all rows = 32,597      ← about 20×
```

Writing "TP53 appears in 1,581 pancreatic cancer papers" would have been wrong.

**Worse still, the ranking itself changed** — MTOR went from 20th in the sample to 9th over all rows, INS from 6th to 16th. There was not even the escape route of "the absolute numbers may be off, but the ordering can be trusted."

### (c) Mistaking the definition

UniProt's keyword **KW-0458 "Lysosome" is a subcellular localization**, not "lysosomal enzyme." Using it, the approved-drug side of the result was dominated by **22 insulin preparations and 12 PDGFR inhibitors**.

**The syntax was perfectly correct, execution succeeded, and the answer was meaningless.**

### (d) Misreading the unit of aggregation

When we looked into variants in TogoVar:

| Breakdown | Total | Matches the variant count of 182? |
|---|---:|---|
| **type** (SNV 157 / deletion 23 / insertion 2) | **182** | ✅ matches |
| **significance** (Pathogenic 277 / Likely pathogenic 134 / others) | **457** | ❌ **2.5×** |
| **consequence** | **2,613** | ❌ **about 14×** |

**457 is not a number of variants.** It is a number of "variant × condition" pairs — because one variant can be tied to several diseases. consequence is "variant × transcript" on top of that, so it swells to 14×.

**And something counterintuitive happens.** We filtered on "pathogenic," yet the breakdown contains 35 *Uncertain significance* and 1 *Likely benign*. This is not a contradiction — **the filter is per variant, the breakdown is per variant-condition record**. In fact, a single variant (rs421016) alone accounts for 13 records.

**The tool itself returns a warning in `statistics_caveats`. Read it.**

> `"significance": "... counted PER VARIANT-CONDITION classification record ... Do NOT compare the sum to \`filtered\`."`

### (e) Misunderstanding what the metric measures

**INS, GAPDH and POTEF** came out at the top as genes associated with pancreatic cancer. None of them is a driver of pancreatic cancer.

- **INS** — organ-level co-occurrence, because the pancreas is an endocrine organ
- **GAPDH** — a housekeeping gene, merely mentioned as an internal control in experiments
- **POTEF** — a chimeric gene formed from a fused actin retrogene, highly similar in sequence to ACTB

> ⚠️ **Here we confess a failure of this tutorial itself.** The first draft described POTEF as "a known false-positive source for gene normalization." **It was plausible, and it very nearly went through as it stood.** When we checked, PubMed had a total of only 17 papers on POTEF, and nowhere in them was there any support for that claim.
>
> All we could confirm was a different fact — that it shares peptides with ACTB — and **whether that is the cause of its ranking in PubTator is not known.**
>
> **This is the subject of this chapter, exactly.** Without verification, your own conjecture gets promoted to fact inside your own prose.

Conversely, the true drivers — **SMAD4 and CDKN2A — were nowhere in the top 20**. The number of co-occurring papers measures "fame × publication volume," and **it does not measure disease specificity**.

---

## 7-2. The four verification steps

For any number that goes into a paper or a report, do these without exception.

### Step 1: Make it output the query that was executed, and save it

```
Give me the full text of the SPARQL you just executed, exactly as it ran. And the endpoint you used.
```

**Do not let it summarize.** You need the full text. This is what corresponds to a lab notebook.

### Step 2: Cross-check the counts with COUNT

```
Give me the count of that result with both COUNT(DISTINCT ...) and COUNT(*).
If they differ, explain what is being duplicated.
```

A difference is not an anomaly. **Reporting it without being able to explain it is the anomaly.**

If sampling was used (an inner LIMIT), then also:

```
If you ran the same aggregation over all rows with no LIMIT, what would this number become?
If that is too heavy, recount just the top few rows exactly and compare.
```

This is how you detect the sampling bias of (b).

### Step 3: Check one or two entries by eye in the source database

**Do not skip this.** It takes 30 seconds.

| DB | Where to check |
|---|---|
| UniProt | https://www.uniprot.org/uniprotkb/[accession] |
| PDB | https://www.rcsb.org/structure/[PDB ID] |
| ChEMBL | https://www.ebi.ac.uk/chembl/ |
| NCBI Gene | https://www.ncbi.nlm.nih.gov/gene/[ID] |
| TogoVar | https://togovar.org/ |
| MeSH | https://meshb.nlm.nih.gov/ |

Look at the top entry, and at one from the bottom — or one that surprises you. **The surprising one carries more information** — that PDGFRB was in a list of lysosomal enzymes is something you can notice by eye.

### Step 4: Record the date of execution and the endpoint

Databases get updated. **A result with no "when" cannot be reproduced.**

---

## 7-3. What to save for reproducibility

For each query, keep the following.

```
├─ query.rq          the full text of the SPARQL that was executed
├─ endpoint.txt      the endpoint URL and the graph name
├─ result.csv        the result itself
├─ counts.txt        the result of the COUNT cross-check
└─ meta.txt          date and time of execution, the original question, ★the model name,
                     ★the client, the tools used and their versions
```

**Do not forget to put "the original question" into meta.txt.** Six months later it is the only clue you have as to why you narrowed things the way you did.

### ★ Record the model name — a requirement specific to querying through an LLM

With ordinary SPARQL, the query, the endpoint and the date are enough to reproduce a result. **When an LLM is in the loop, that is not enough.**

**The same question behaves differently on a different model.** Even in this tutorial's measured runs, we saw differences like these.

| | One model | Another model |
|---|---|---|
| Tool calls for "tell me about genes involved in cancer" | **1** | **0** |
| Read the usage guide | yes | **no** |
| Time for the same demo | 8–18 s | 21–30 s |

**Even when the content of the answer is the same, the process that got there is not.** To verify after the fact *why* the answer came out the way it did, you need a record of the model.

So meta.txt needs at minimum these:

- **The model name** (e.g. `claude-opus-5` / `claude-sonnet-5`)
- **The client** (Claude desktop / Web / Claude Code / API)
- **The MCP server** (the hosted one, or a local install. Note the version too if you know it)

> ⚠️ **Careful:** "the model you configured" and "the model that actually did the processing" are not necessarily the same. Fallbacks and switching can happen. **Strictly, the accurate thing to write is "configured as …"**, and this tutorial's own measurement records are written that way.

You can also have Claude produce the whole set for you.

```
For the query just run, give me
(1) the full text of the SPARQL executed (2) the endpoint and graph name
(3) the results as CSV (4) the COUNT cross-check (5) the date and time and the original question,
in a form I can save to files as-is.
```

> 💡 The **PRISM** skill in [Chapter 5](05-skills-workflows-en.md) has machinery for structuring this record and keeping it automatically (a provenance ledger). Consider it once doing this by hand becomes tiresome.

---

## 7-4. How to write it up in a paper

### Cite at two levels

Cite **both TogoMCP and each individual database you actually used**. TogoMCP is the entrance; it is not where the data came from.

> Kinjo, A. R., Yamamoto, Y., Bustamante-Larriet, S., Labra-Gayo, J.-E., & Fujisawa, T. (2026). TogoMCP: Natural Language Querying of Life-Science Knowledge Graphs via Schema-Guided LLMs and the Model Context Protocol. *Database* **2026**:baag042. https://doi.org/10.1093/database/baag042

Plus a citation for each database you actually consulted — UniProt, PDB, ChEMBL, and so on.

### What belongs in the methods section

- The databases used and their version/release, and **the date of access**
- The **full text of the queries** executed (in supplementary material)
- The **identifiers** used to narrow the target (GO:0043202, MeSH D010190 and so on. By ID, not by name)
- If sampling or a LIMIT was used, **that fact itself, and its consequences**

Not many people can write that last item. **Being able to write it is a strength.**

### What must not be written

- **"We asked an AI"** — that is not a method
- Numbers you have not verified
- Claims whose source you cannot state

---

## 7-5. What this is good for / what it is not good for

Honestly.

### Good for

- **Exploration and hypothesis generation** — "which proteins with this function have no drug yet?"
- **Cross-database checking** — "what is this ID called in the other DBs?"
- **Organizing the known** — pulling scattered information into a single table
- **Drafting SPARQL** — as a starting point you intend to rewrite yourself (this is extremely effective)
- **Finding what you missed** — picking up connections that lie outside your own field

### Not good for

- **Analyses where completeness is a requirement** — "all of them" cannot be guaranteed. Not suitable for building the population for a phylogenetic analysis or a meta-analysis
- **Statistical inference** — it will return counts, but designing the test and the effect size is your job
- **Clinical decisions** — **never use it for this.** TogoVar's pathogenicity classifications are the contents of ClinVar submissions; they are neither a diagnosis nor advice
- **Producing primary data** — it only queries existing databases. It makes no new measurements
- **Substituting for expert judgment** — the one who judged whether PDGFRB is a lysosomal enzyme, in this tutorial, was **you**

---

## 7-6. Other cautions

**Licensing.** KEGG is restricted to those affiliated with academic institutions, and offering it in a public service requires a separate licence ([appendix](99-appendix-local-install-en.md)). Every database also has terms of use. Check them before any commercial use.

**Personal information.** What TogoVar returns is aggregate values (allele frequencies, submission counts), not individual-level data. Controlled-access datasets appear only as cohort counts. That said, ClinVar's condition descriptions can contain case-derived phenotypes. **It is public information, but do not speak of it as "the patient we found."**

**Handling disease information.** A single variant can be tied to several diseases (one variant carries both Gaucher disease and Parkinson's disease). This is **something to state as a ClinVar classification**, not as advice about risk. Be especially careful when showing it in a presentation.

---

## Summary of this chapter

1. Failure shows up **not as an error, but as a number that looks correct**
2. **The four verification steps** — keep the query / cross-check with COUNT / check by eye in the source DB / record the date
3. What you must save is **the query, not the table of results**
4. Cite at two levels: **TogoMCP + the individual databases**
5. **There are things it is not good for.** Guaranteeing completeness, and clinical decisions, above all

---

Next → [08. Troubleshooting](08-troubleshooting-en.md)
