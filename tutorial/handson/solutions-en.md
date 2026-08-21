<!-- workshop-only -->
# Hands-on Exercises — Worked Solutions and Where People Get Stuck
<!-- /workshop-only --><!-- public-only -->
# Worked Solutions and Where People Get Stuck
<!-- /public-only -->

> ⚠️ Every number here is measured (**re-measured 2026-08-20 / 08-21**). Databases get updated, so **it is normal not to get the same numbers.** Check the steps and the reasoning instead.

---

## Exercise 1 — Check the connection and ask your first question

**(a)(b)** Omitted (depends on your protein).

**(c) Where people get stuck:** no accession comes back, or several do.

Protein names are not unique. "Amylase" covers AMY1A/AMY1B/AMY1C/AMY2A/AMY2B. **When it is ambiguous, the AI picks one on its own.** Specify it again by gene symbol.

**(d) The sequence length is not what you expected** — nearly always one of these three.

| Cause | Example |
|---|---|
| **You are looking at the precursor** | Insulin: expected 51 aa → actually **110 aa** (preproinsulin) |
| **There are multiple isoforms** | The default is the canonical one (`-1`). Other isoforms have different lengths |
| **The signal peptide or propeptide is included** | Common with secreted proteins |

**How to check:**

```
Is that sequence length for the precursor or for the mature protein?
If the signal peptide or propeptide regions are annotated in UniProt, show me those too.
```

> **The lesson:** when a number differs from what you expected, the first thing to suspect is **a mismatch between your expectation and the database's definition**. Not an error by the AI.

---

## Exercise 2 — Travel across databases carrying an ID

**(a)** For insulin, P01308: Ensembl **ENSG00000254647** / HGNC **6081** (formally `HGNC:6081`).

> 💡 HGNC sometimes comes back as a bare number. Fix the notation.

**(b) Interpreting 0 PDB hits — this is the real subject.**

**Zero hits does not mean "there is no structure."** The possibilities are:

1. No structure has genuinely been solved
2. **A structure exists, but that correspondence is not registered along the ID-conversion route**
3. It was solved as part of a complex, and there is no entry for that protein on its own

How to check — **come at it by another route**:

```
Find PDB structures for this protein by searching PDB directly,
not through ID conversion.
If the counts differ, explain why.
```

Searching the RCSB PDB website directly also takes 30 seconds.

> **The lesson:** when a single route returns 0 hits, that is not evidence that the thing does not exist. It is **evidence that it cannot be found by that route.**

**(c) Making the failed conversions explicit:**

```
Convert these IDs to XXX. Also state explicitly which ones could not be converted.
```

**A count that shrank silently is the most dangerous kind.** You send 20 and 12 come back, and you report "there were 12" without ever noticing that 8 vanished.

---

## Exercise 3 — TogoVar

**(a) Measured** (2026-08-21): pathogenic + likely pathogenic = **182 variants**.

**(b) Resolving the gene name — "GBA1" is an exact match, "GBA" is not.**

| Search term | First row | match_type |
|---|---|---|
| **GBA1** | GBA1 (HGNC:4177) | **exact** ✅ |
| **GBA** | GBA1 (HGNC:4177) | **prefix** ⚠️ |

HGNC renamed **GBA → GBA1** in 2022, so the old symbol "GBA" is not in the current set of approved symbols. Search for "GBA" and there is **not a single exact match** — GBA1, GBA2, GBA3, GBAT2 and GBA1LP all line up as prefix matches, five of them.

**★ If you did not get caught by this.** GBA1 comes up on the first row, so you can sail straight past. **That is the result of re-ranking, and it is luck.**

`match_type: prefix` means "**the symbol you asked about does not exist**." Look at **GBAT2**, sitting right there in the same list — its official name is "RFX5 antisense RNA 1," and it is not even in the GBA family. Make "take the first hit" a habit and it will get you eventually.

```
Was that gene symbol an exact match or a prefix match?
If there are other candidates, explain why it is not one of those.
```

**(c) They do not match. ★This is the single biggest point**

| Aggregation | Unit being counted | Total | Matches 182? |
|---|---|---:|---|
| `type` (SNV 157 / deletion 23 / insertion 2) | **variants** | **182** | ✅ matches |
| `significance` | **variant × condition** | **457** | ❌ 2.5× |
| `consequence` | **variant × transcript** | **2,613** | ❌ about 14× |

**Saying "277 pathogenic variants" is wrong** (277 is the number of Pathogenic records, and the total is larger still, 457).

**One more thing that runs against intuition.** You filtered on "pathogenic," yet the breakdown contains 35 *Uncertain significance* and 1 *Likely benign*. That is not a contradiction: **the filter works on variants, the breakdown works on variant × condition records.** rs421016 alone has 13 records.

The tool itself returns `statistics_caveats`. Read them.

**(b2) HGVS does not come out — the place everyone gets stuck live**

HGVS notation **is not included in the default output**. It takes an additional call with `include_transcripts=True`.

```
Give me the HGVS notation for that variant, including the transcript information.
```

What you get: `NM_000157.4:c.1448T>C` / `NP_000148.2:p.Leu483Pro`

> 💡 **The old conventional name is L444P** (the old numbering, with the 39-residue signal peptide excluded). The literature mostly writes L444P, so keep it in mind as a bridge.

⚠️ But the `include_transcripts` output is large — for GBA1 it comes back for 12 transcripts. Do the same thing on something BRCA1-sized (over 400) and your screen falls apart.

**(d) Enrichment in the Japanese population — the highlight of this exercise**

Take pathogenic + likely pathogenic and apply a ToMMo frequency ≥0.0005, and **only one is left** — rs421016 (L444P in the old notation, `NP_000148.2:p.Leu483Pro` in the current one).

| Cohort | Allele frequency |
|---|---|
| ToMMo (Japanese, n≈54,000) | **0.000801** |
| NCBN (Japanese) | 0.000807 |
| GEM-J WGA (Japanese) | 0.001326 |
| gnomAD exomes | 0.0000842 |
| gnomAD genomes | 0.000237 |

**Roughly a 10-fold enrichment in the Japanese population** (ToMMo / gnomAD exomes ≈ 9.5×, and ≈ 15.7× for GEM-J WGA). All three Japanese cohorts are high together, so it reads as a population difference rather than an artifact of a single cohort. This is information you would miss if you only looked at the international databases. That is TogoVar's reason for existing, and it is the value of TogoMCP carrying Japanese databases.

> ⚠️ **But do not assert it.** ToMMo and NCBN carry the quality flag `VQSRTrancheSNP99.95to100.00`, and GEM-J WGA carries `NotHighConfidenceRegion`. **GBA1 is highly homologous to the pseudogene GBAP1**, which makes short-read mapping hard, and the possibility that part of the frequency difference is a technical false positive cannot be excluded.
>
> This connects directly to "what it is not suited for" in Chapter 7. **Check the quality flags before you make a claim about population differences.**

> ⚠️ **Do not say "heterozygous carriers are unaffected, so there is nothing to worry about."**
>
> Gaucher disease is autosomal recessive, and heterozygous carriers **do not develop Gaucher disease itself**. But that does not mean "unrelated" — **heterozygous GBA1 variants substantially increase the risk of Parkinson's disease**, as multiple reports have found (Sanyal et al., *Mov Disord* 2020, PMID 32034799).
>
> That is exactly why Parkinson disease and dementia with Lewy bodies are sitting there on your screen. **A confident reassurance is inaccurate in this situation.**

**One more trap (sharp of you if you caught it):** many of the pathogenic variants have `tgv_id: null`. They exist on the REST side, but they are not in the subset on TogoVar's SPARQL side. **Chase this through SPARQL and you will silently lose them.**

---

## Exercise 4 — Changing the definition changes the answer ★most important

**(a) Using KW-0458 (the UniProt keyword "Lysosome")**

**161 proteins** as candidates. On the approved-drug side, **48 rows**.

| UniProt | Gene | Approved drugs |
|---|---|---|
| P06213 | **INSR** | **22** insulin preparations |
| P09619 | **PDGFRB** | imatinib, sunitinib, sorafenib and others, **12** |
| P06280 | GLA | migalastat |
| P10253 | GAA | miglitol, voglibose |
| … | | |

**34 of the 48 rows are insulin and PDGFR inhibitors.** Put that out under the heading "approved drugs targeting lysosomal enzymes" and you will be called on it immediately.

**(b) Using GO:0043202 (lysosomal lumen)**

**52 proteins** as candidates. On the approved-drug side, **16 rows / 3 proteins / 14 drugs**. The candidates now center on the genuine luminal hydrolases — GBA1, GLA, HEXA/HEXB, GAA, IDUA, IDS, ARSA/ARSB, SGSH, NAGLU, GALC, SMPD1, TPP1, PPT1.

**The 22 insulin preparations are gone.** PDGFRB stays (because GO:0043202 really is annotated on it), but the result is now at a scale you can read.

**The answer:**

> Of the 52 human lysosomal luminal enzymes, **3** are targets of approved drugs — **GLA** (migalastat, a pharmacological chaperone), **GAA** (miglitol / voglibose, though the indication is type 2 diabetes), and **PDGFRB** (11 drugs; a receptor tyrosine kinase, not a lysosomal enzyme).
>
> Take PDGFRB out and **there is effectively one approved small-molecule line that targets a lysosomal enzyme directly: migalastat. Because lysosomal diseases are treated by replacing the enzyme, not by inhibiting it.**

**(c) Why they are this different**

**KW-0458 is a subcellular-localization keyword, not a classification of function.** It means "a protein that localizes (at least sometimes) to the lysosome," so INSR, PDGFRB, MTOR, PCSK9, LRRK2, PSEN2, and around 20 RAB GTPases come in with it.

**Narrowing by EC number to `3.*` (hydrolases) does not fix it either.** 113 of the 161 survive. **Because RAB GTPases are EC 3.6.5.2 — perfectly respectable hydrolases.**

**And PDGFRB still survives into the GO:0043202 version.** Because that annotation genuinely is on it. **A localization annotation ≠ a functional classification.** It is not an error; it is a question of the resolution of your question.

**(d) Analogues in your own field** — what to look for:

- **A localization word used as a function word** ("mitochondrial protein" — works in the mitochondrion? localizes there? is encoded there?)
- **Speaking at a higher-level concept** ("kinase," "transcription factor" — where do you draw the line?)
- **Clinical vocabulary mixed with molecular vocabulary** ("cancer gene" — somatic driver? germline susceptibility?)
- **A conventional name that differs from the official one** (as with GBA / GBA1)

---

## Exercise 5 — The four verification steps

**Common failures:**

| Where people get stuck | What to do |
|---|---|
| The SPARQL gets summarized | Say explicitly: "print it **in full, verbatim**." A summary is useless for reproduction |
| The COUNT ends up with different conditions than the main query | Specify: "use the **same WHERE clause** as the main query and change only the COUNT" |
| The inner LIMIT goes unnoticed | Ask directly: "**did you use sampling or a LIMIT?**" |
| Eyeballing gets skipped | It takes 30 seconds. Do not skip it |

**(b) How to ask for an explanation when they differ:**

```
COUNT(*) and COUNT(DISTINCT) differ.
Show me which predicate has multiple values, and give one concrete example.
```

"One concrete example" is what does the work. An abstract explanation cannot be verified.

**(c) Eyeballing means looking at the "surprising" hit.** The top hit is usually correct, so it carries little information. An oddity like PDGFRB sitting in a list of lysosomal enzymes is **something you only notice by looking at the surprising hit**.

---

## Exercise 6 — Bad questions and good questions

**(b) Checklist:**

| Check | Danger sign |
|---|---|
| Were `run_sparql` or the search tools called | **Not called** = answering from memory |
| Do the specific names in the answer exist in the tool output | **They do not** = it came from memory (most important) |
| Are accessions / IDs attached | **Not attached** = unverifiable |
| Time taken | **Around 10 seconds** = possibly nothing happened |

The second one is decisive. In the worked example in Chapter 4, TP53, KRAS and MYC lined up in the answer and **not one of them existed in the tool output**.

**(d) The change you should expect** (measured, Chapter 4):

| | Vague version | Specified version |
|---|---|---|
| Time | 12 s | 182 s (**~15×**) |
| Tool calls | 1 | 8 |
| SPARQL | 0 | 4 |
| IDs verified | none | yes |
| Reproducible | **no** | yes |

**(e) The limitations that remain — this is the real point.** Even the specified version in Chapter 4:

- Has **INS** (co-occurrence via the pancreas as an organ), **GAPDH** (an experimental internal standard), and **POTEF** (a chimeric gene whose sequence is highly similar to ACTB; whether that is the cause of its rank is unconfirmed) contaminating the top of the list
- Leaves the true drivers **SMAD4 and CDKN2A outside the top 20**
- The reason: number of co-occurring papers measures "fame × paper count" and **does not measure disease specificity**

Your answer to (c) should have limitations of the same kind. **Can you write, in one line, what this metric measures and what it does not?** <!-- workshop-only -->If you can, this workshop has achieved its purpose.<!-- /workshop-only --><!-- public-only -->**If you can, this tutorial has achieved its purpose.**<!-- /public-only -->

---

## Exercise 7 — Making it look for counter-evidence

**The difference you should expect:**

"Is this claim correct?" → the AI **tends to agree**. It tends to selectively gather the evidence that supports you.

"Find evidence that contradicts this claim" → **the direction of the search changes, and different data comes out.**

**Which is more useful:** almost always the latter. You already have the evidence on the supporting side. What you do not have is the other side.

**Applying it in practice:**

```
Is there a hypothesis other than this interpretation that explains the same data?
Find evidence in the databases that supports that hypothesis.
```

This works when you are writing the discussion of a paper, and when you are anticipating reviewer comments.

---

## Free exercise — What to look at in the retrospective

When it does not work, the cause falls into three kinds. **What matters is being able to tell which one it is.**

| Cause | Sign | What to do |
|---|---|---|
| **The question's problem** | An answer comes back but misses the point. The tools were called | Specify it again with the five elements from Chapter 6 |
| **The database's problem** | 0 hits. Or plainly incomplete | Check what is and is not in that data. Try another DB |
| **The tool's problem** | Errors, timeouts, cannot connect | Go to Chapter 8 |

**The first is the most common.** And the first is also the hardest to notice — because an answer comes back, so it does not look like a failure.
