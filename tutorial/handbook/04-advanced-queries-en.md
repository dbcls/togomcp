# 04. Harder Questions

This is where it gets real. We cover three things.

1. **Demo 4** — a question that search alone cannot answer (PDB)
2. **Demo 3'** — a question that spans several databases (UniProt × ChEMBL)
3. **The failure demo** — ★ the most important part of this chapter

---

## Demo 4: a question that search alone cannot answer

```
Give me the top 10 PDB structures of the SARS-CoV-2 main protease
(3CL protease), ordered by best resolution.
```

**Measured at 39–54 s** (on two models in August and on Sonnet on 10-20; zero failures and zero retries every time).

### What to watch for is that it hits a wall partway through

`search_pdb_entity` runs first. The result: **thousands of hits, ordered by relevance (not by resolution)**. The hit count depends on the search words (3,710 for "SARS-CoV-2 main protease" on 2026-10-20).

**This search tool cannot answer the question.** Producing "the top 10 by best resolution" requires sorting on resolution, a numeric field, and that is a job for SPARQL, not for a search API.

So it proceeds to `get_MIE_file("pdb")` → `run_sparql`. This is one of the few demos where **the reason SPARQL is needed is visible on screen** (recorded 2026-08).

> 📝 **The 2026-10-20 re-run (Sonnet) took a different path.** It sliced the range several times with the search tool's resolution filter (`res_max`) and reached **the same top 10** without SPARQL. The model itself noted that it could not guarantee completeness below 1.3 Å. Which path a run takes depends on the model and the run. If you need completeness, have it write SPARQL on structured conditions (EC number and taxon).

### Results (measured 2026-10-20; unchanged since August)

| # | PDB | Å | Title (excerpt) |
|---|---|---|---|
| 1 | **9ZNL** | 1.16 | Mpro covalently bound to inhibitor GRL-050-22 |
| 2 | 7GEF | 1.18 | COVID Moonshot — BEN-DND-93268d01-11 |
| 3 | 7K3T | 1.20 | possible zinc-binding intermediate |
| 4 | 9HJH | 1.20 | compound 1 bound to Mpro |
| 5 | 7GBE | 1.224 | COVID Moonshot — JAG-UCB-a3ef7265-20 |
| 6 | 7GEH | 1.23 | COVID Moonshot — EDJ-MED-06d94977-2 |
| 7 | 6YB7 | 1.25 | unliganded active site |
| 8 | 7GBT | 1.25 | COVID Moonshot — BEN-DND-7e92b6ca-2 |
| 9 | 7GEC | 1.25 | COVID Moonshot — VLA-UCB-00f2c2b3-7 |
| 10 | 7JKV | 1.25 | complex with inhibitor GRL-2420 |

Ranks 7–10 are **4 of the 6 entries tied at 1.25 Å**. `ORDER BY ?res` alone leaves ties unordered, so they reshuffle from run to run (9HAK and 9RJ5 sometimes make the cut). The query uses `?entry_id` as a second sort key to fix the order (checked 2026-10-14).

You can also get the breakdown by method: **X-ray 1,818 / cryo-EM 25 / neutron 4 / solution NMR 3 / electron crystallography 1** (1,851 counted by method, measured 2026-10-20; some entries, such as joint X-ray and neutron studies, use more than one method, so there are 1,847 entries). Ask like this to get it (checked with Sonnet on 2026-10-20):

```
How many PDB structures of the SARS-CoV-2 main protease (3CL protease) are there for each experimental method?
```

> 💡 **These numbers move.** On 2026-08-21 the total was 1,832 (and three weeks before that, 1,822). Nineteen more in two months. **The databases are alive.**

### The query that ran

```sparql
PREFIX pdbo: <http://rdf.wwpdb.org/schema/pdbx-with-vrptx-v50.owl#>
PREFIX dc:   <http://purl.org/dc/elements/1.1/>
SELECT ?entry_id ?res (SAMPLE(?title) AS ?title)
FROM <http://rdfportal.org/dataset/pdb>
WHERE {
  ?entry a pdbo:datablock .
  FILTER(STRSTARTS(STR(?entry), "http://rdf.wwpdb.org/pdb/"))
  BIND(STRAFTER(STR(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbo:has_entityCategory/pdbo:has_entity ?ent .
  ?ent pdbo:link_to_enzyme <http://purl.uniprot.org/enzyme/3.4.22.69> .
  ?entry pdbo:has_entity_src_genCategory/pdbo:has_entity_src_gen/pdbo:link_to_taxonomy_source
         <http://purl.uniprot.org/taxonomy/2697049> .
  ?entry pdbo:has_exptlCategory/pdbo:has_exptl/pdbo:exptl.method "X-RAY DIFFRACTION" .
  ?entry pdbo:has_refineCategory/pdbo:has_refine/pdbo:refine.ls_d_res_high ?res .
  OPTIONAL { ?entry dc:title ?title }
}
GROUP BY ?entry_id ?res
ORDER BY ?res ?entry_id
LIMIT 10
```

### Three things to look at in this query

**1. The target is not narrowed by a keyword search over titles.** It is narrowed by the EC-number IRI (`enzyme/3.4.22.69`) and the taxon IRI (`taxonomy/2697049`). Narrow by strings in the title and you drop entries that do not spell out "Mpro" while picking up unrelated ones. **If you can narrow by IRI, do not narrow by string.**

**2. The resolution is X-ray only.** Cryo-EM resolution lives in a different predicate (`em_3d_reconstruction.resolution`). This ranking **does not mix methods**. That is the right thing to do, but it is something you should say out loud.

**3. The results move.** 9ZNL is a relatively new structure. If a 1.1 Å structure is deposited tomorrow, the ranking changes. **So save the query, not the table.**

---

## Demo 3': across several databases

```
Among human lysosomal enzymes, tell me which ones are targets of approved drugs.
```

This requires connecting UniProt (function and localization annotations) with ChEMBL (drug–target relationships). Measured at 64–79 s.

> 📝 The results below are the August 2026 record. On the 2026-10-20 re-run (Sonnet) the model chose GO:0005764 (lysosome) as the definition itself, picked about 80 proteins, and answered **GLA and GAA only** (no PDGFRB). **If you do not specify the definition, each run picks its own**: the subject of the second half of this section.

### Results

**Of 52 human lysosomal lumen enzymes, 3 are mechanism-of-action targets of an approved drug.**

| Gene | Approved drug | Action | What it means |
|---|---|---|---|
| **GLA** | migalastat | **STABILISER** | A pharmacological chaperone for Fabry disease. **Within these 52, the only case that targets the causative enzyme of a lysosomal disease itself** |
| **GAA** | miglitol, voglibose | INHIBITOR | GAA deficiency causes Pompe disease, but these two are **type 2 diabetes** drugs (aimed at intestinal α-glucosidases; ChEMBL also records GAA itself as their target) |
| **PDGFRB** | 11 drugs incl. imatinib, sunitinib | INHIBITOR (becaplermin: AGONIST) | A receptor tyrosine kinase. **Not a lysosomal enzyme** |

> 💡 **An easy confusion.** In ChEMBL, the drug carrying an indication for Pompe disease (Glycogen Storage Disease Type II) is **miglustat**, not miglitol. The names are similar.

The third one, PDGFRB, dominates the result by row count (11 of 14 drugs). But it is merely annotated to the lysosomal lumen in the context of receptor uptake and degradation — it is not a lysosomal enzyme in the usual sense. **This is a case where the scope definition fed straight through into the result** — taken up in the very next section.

Set PDGFRB aside and here is what can be read off.

> **Within these 52, the only approved small molecule aimed directly at a lysosomal enzyme was migalastat for GLA.** The two GAA drugs are diabetes drugs with a different indication.
>
> That is not surprising. **Lysosomal diseases are treated by replacing the enzyme, reducing its substrate or stabilizing it with a chaperone — never by inhibiting the causative enzyme.**

> ⚠️ **Be careful how you say this.** It is **not** a claim that migalastat is the only such drug in the world. It is a **measurement**: "cross-referencing the 52 human reviewed enzymes carrying GO:0043202 against approved drugs in ChEMBL produced this." Generalize past that scope and you are doing to yourself exactly what this tutorial warns against in Chapter 7.

### ★ The most interesting landing point — GBA1 returns 0 rows

**GBA1 (P04062), the causative enzyme of Gaucher disease, is among the 52 — yet the approved-drug side came back with 0 rows.**

Miglustat, a Gaucher disease drug, does not target GBA1; its target is the substrate-synthesizing enzyme **UGCG** (ceramide glucosyltransferase). And imiglucerase, the enzyme replacement therapy, has — as the next section shows — its target registered on the substrate side.

**That "causative enzyme = drug target" does not hold becomes visible at the level of the data structure.**

### And along the way, another good teaching case appears

Even among drugs for the same Gaucher disease, **miglustat and eliglustat look different in the DB.**

| Drug | How it appears in ChEMBL |
|---|---|
| **Miglustat** | Mechanism-of-action record present → UGCG (Q16739) can be **retrieved directly** as INHIBITOR |
| **Eliglustat** | Mechanism-of-action record **does not exist**. Only the indication "Gaucher Disease, phase 4" can be retrieved |

Eliglustat is a UGCG inhibitor too, but **you have to cross-check that in the literature**.

> **The lesson: "not in the database" is not "not a fact."**
>
> When 0 rows come back, that is not evidence of nonexistence — it is evidence that **it cannot be found by this route**. Chapter 7 takes this up again.

### ⚠️ The most important thing here is that the original question did not state its intent

What the instructor meant in this demo was "**enzymes that work inside the lysosome**" (such as the hydrolases whose loss causes lysosomal storage diseases). But the prompt only says "lysosomal enzymes." **It can be read in more than one way, and every reading fits the words.** And the AI answers without saying which reading it chose.

| Definition the AI chose | Candidates (reviewed human proteins with an EC number) | Approved-drug targets |
|---|---:|---|
| UniProt keyword **KW-0458 "Lysosome"** (can localize to the lysosome) | 161 (442 carry the keyword in all) | **11 proteins**: INSR (21 insulin preparations), PDGFRB (11 drugs), PCSK9, HCK, PSEN2, mTOR, GLA, GAA, and more |
| GO **GO:0043202** (localizes to the lysosomal lumen) | 52 | **3 proteins**: GLA, GAA, PDGFRB |
| GO **GO:0005764** (localizes to the lysosome) + hand-picking by the model (Sonnet, 2026-10-20) | ~80 | **2 proteins**: GLA, GAA |

(2026-10-20. Salt forms of one drug count as one drug. The August measurement had 22 insulin preparations. The third row is a single run.)

**Every definition lets in things the intent excludes.**

- **KW-0458:** INSR (the insulin receptor), MTOR, PCSK9, LRRK2, PSEN2, and ten RAB GTPases. They pass through the lysosome; they are not enzymes that work inside it
- **GO:0043202:** PDGFRB (a receptor tyrosine kinase), HSP90AA1 and HSPA8 (chaperones), GYG1 (glycogenin). The set does center on lumenal hydrolases such as GBA1, GLA, HEXA/HEXB, GAA, IDUA, IDS and ARSA/ARSB, but this too is **a localization term, not a function**

**Narrowing by EC number to `3.*` (hydrolases) does not fix it.** With KW-0458, 114 of the 161 survive. RAB GTPases are EC 3.6.5.2, and HSP90AA1 and HSPA8 are EC 3.6.4.10 hydrolases too.

What matters is that **every answer fits the words, so none of them looks wrong.** The "21 insulin preparations" table is a correct answer to the question as written. It only looks strange against your own intent.

> **Lesson 1 of this chapter:** when the answer looks strange, suspect not the query's syntax but **whether you wrote your intent into the question**. If you do not, the AI picks a definition silently, and a different one each run.

### What happens when you write the intent in

Write the intent into the same question and it looks like this:

```
Among human enzymes that work inside the lysosomal lumen (such as the hydrolases whose loss causes lysosomal storage diseases; exclude receptors, chaperones, and proteins that only pass through the lysosome), tell me which are mechanism-of-action targets of approved drugs (ChEMBL highest development phase 4). State which database and which annotation you used to define the set, and give the candidate count with COUNT.
```

We ran it three times on Sonnet on 2026-10-20 (63–90 s). **All three runs chose GO:0043202 as the definition, excluded PDGFRB from the 52 candidates with the reason "it is a receptor," and answered GLA and GAA.** All three also stated which annotation defined the set. With the intent written in, the AI stops picking a definition silently.

**And yet you still cross-check.**

- **What got excluded was the model's judgement, not an annotation.** PDGFRB went in all three runs, but HSP90AA1, HSPA8, ATP13A2, TXNDC5 and HGSNAT were handled differently from run to run (none has an approved drug, so the final answer was unaffected)
- **Run 3 never ran the COUNT and reported the candidate count as "50."** It is 52, and that run had passed 52 accessions to ChEMBL. Whether the cross-check you asked for was done, only the log tells you

### Anticipated questions

**Q. Why do enzyme replacement therapies like imiglucerase not show up?**

Imiglucerase **does exist** in ChEMBL (`CHEMBL1201632`, approved phase 4, mechanism of action registered as well). Follow it and here is what you get.

| Item | Value |
|---|---|
| substanceType | **Enzyme** |
| Target | **CHEMBL2364176 "Glucocerebroside"** |
| Target type | **SMALL MOLECULE** |
| Links to UniProt | **0** |
| Action type | HYDROLYTIC ENZYME |

**The target is a "substrate," not a protein.** Enzyme replacement therapy is not "a drug that inhibits an enzyme" but "a drug that supplies the enzyme itself," so in ChEMBL the target stands on the substrate side. **A join going through a UniProt accession can never catch it, no matter what you do.** As a database representation, this is correct behavior.

**Q. Why is PDGFRB mixed in?**

PDGFRB genuinely carries GO:0043202. **A localization annotation ≠ a functional classification.** This is not an error; your question simply lacked resolution.

**Q. It looks like the same drug appears twice?**

Because salt forms are registered as separate molecules (migalastat / its hydrochloride, sunitinib / its malate). **Row count ≠ drug count.** There are 16 rows, but merging each salt form with its parent leaves 14 drugs.

### ⚠️ The query you must not write

You will be tempted to restrict the ChEMBL side to "single proteins only." **Do not.**

```sparql
?target a cco:SingleProtein .    # ← add this and
```

Measured: **16 rows → 8, drugs 14 → 7, with no error.** Voglibose is tied to a **protein family** called "Alpha glucosidase," and PDGFRB's 7 drugs to a **complex** called "PDGF receptor." One UniProt accession corresponds to several target entities of differing types.

**This is the textbook case of "silent failure."** No error appears; only the count drops.

---

## ★ The failure demo: the center of this chapter

From here on is the most important part of this tutorial.

### First, throw a bad question at it

```
Tell me about genes involved in cancer
```

**Measured at 12–25 s, with 0–2 tool calls.** What comes back is a fluent answer like this (the August 2026 record):

> The main genes involved in cancer include the tumor suppressors TP53, RB1, PTEN, APC, BRCA1/2, and the oncogenes KRAS, MYC, EGFR, ERBB2 (HER2), PIK3CA, ALK, BRAF. TP53 is mutated in roughly half of all human cancers…

**Plausible. Fast. And it consulted no database.**

### Open the tool log

**What you see here depends on the model you are using.** In our measurements there were two patterns.

| | Tool calls |
|---|---|
| **Pattern ①** | **0** — the databases were never touched at all |
| **Pattern ②** | **exactly 1** — a search was issued, but its results were not used |

---

#### Pattern ① — the log is empty

**Nothing was called.** Not even the usage guide (whose tool description at the time said "call me first, every time").

Twenty-seven genes came back in 20 seconds, sorted neatly into oncogenes and tumor suppressors. **Not one of them was looked up just now.**

Here is the model's own account of it:

> "I had TogoMCP loaded — and its usage guide says, in its own words, 'call me first on every turn' — and I touched none of it. I treated this as recall of textbook knowledge and answered **exactly as I would with zero tools connected.**"

**The conclusion is plain, so feel free to skip Pattern ② and move to the next section.**

---

#### Pattern ② — a single search

The one search that ran was this:

```
search_uniprot_entity(query="cancer AND organism_id:9606 AND reviewed:true", limit=20)
```

What came back:

```
Q9Y238  Deleted in lung and esophageal cancer protein 1
P51587  Breast cancer type 2 susceptibility protein
Q5HYN5  Cancer/testis antigen family 45 member A1
O00559  Receptor-binding cancer antigen expressed on SiSo cells
P35243  Recoverin (Cancer-associated retinopathy protein)
P78358  Cancer/testis antigen 1 (NY-ESO-1)
...
```

**TP53, KRAS, MYC, PTEN, RB1 and APC — the genes lined up in the answer — are not among these. Not one of them.**

That is no accident, but it is not because their names lack "cancer" either. TP53's UniProt name is "Cellular tumor antigen p53" and KRAS's is "GTPase KRas", yet both **do match this search** (`cancer AND gene_exact:TP53 AND organism_id:9606 AND reviewed:true` returns P04637; checked 2026-10-20). What came back was **only the top 20**, led by proteins with "cancer" in their names, and TP53 was outside it. **The AI saw only those 20, and the genes in its answer did not come from them.**

> **There are traces of a database being touched, and the answer comes from memory.**
>
> This is the failure mode this tutorial most wants to convey.

### ★ Either pattern, the same conclusion

Pattern ① is "never touched it"; Pattern ② is "only traces of touching it." **Different phrasings — but either way, the answer came from memory.**

And here is what matters — **from what is on screen, you cannot tell which one it was.** The fluency is the same, the speed is the same. **You only find out by opening the log.**

> 📝 **The 2026-10-20 re-runs showed a third pattern.** Sonnet and Haiku each issued 2–7 searches and then **disclosed in the answer** that TP53, KRAS and the like were not in the search results and came from general knowledge. Some runs do disclose. **Others do not, so the conclusion stands: the only thing you can rely on is checking for yourself.**

> 💡 **This is model-dependent behavior.** When you try it yourself, something different from what is written here may happen. **What matters is not "which pattern you got" but the fact that you opened the log and checked.**

### Why this is dangerous

On screen there is **nothing at all** to tip you off. The answer is fast, it is fluent, and **as content it is broadly correct** (TP53 really is a tumor suppressor).

The problem is not correctness. It is that **the provenance is unknown, and the result can be neither verified nor refuted nor reproduced**. You cannot put it in a paper.

**Being slow and failing is far safer than being fast and confidently wrong.**

### Three axes were left vague

| Axis | What went unspecified | What happened |
|---|---|---|
| **Species** | "cancer" with no species given | **`organism_id:9606` was added on its own.** The user never said "human" — a specification fabricated where the user cannot see it |
| **Cancer type** | "cancer" = all several hundred MeSH descriptors | Genes from breast, lung and colorectal cancer mixed together at random |
| **Type of evidence** | "involved in" undefined | Germline susceptibility / somatic driver / expression biomarker / therapeutic target / mere literature co-occurrence — **none of them chosen, all of them blended** |

---

### Next, throw the same intent at it, properly specified

```
In MeSH, first identify the descriptor for 'Pancreatic Neoplasms', then give me the
human genes associated with that disease as a table — the top 20, ordered by strength of
association — stating the source database and field names. Cross-check the counts with COUNT.
```

**Measured at 182 s, with 8 tool calls. Roughly 15× the cost** (the August 2026 record below). — That run gets as far as cross-checking one gene, TP53 (step 4 below). The **re-ranking of all top-20 genes by a full count comes from a second run of the same prompt**, which took **369 s, 13 tool calls and 8 SPARQL queries (one of which timed out) — roughly 30×**. Both runs drew the same 20,000-row sample, so their sample ranks agree.

### What changed

**1. The target became grounded in a verified ID.** `search_mesh_descriptor` ran and **MeSH D010190** was settled. Every subsequent query is anchored to that IRI, so string matching disappeared entirely.

**2. The provenance became sayable.**

| Item | Value |
|---|---|
| Endpoint | `https://rdfportal.org/ncbi/sparql` |
| Main graph | `http://rdfportal.org/dataset/pubtator_central` |
| Disease side | `dcterms:subject "Disease"` + `oa:hasBody <identifiers.org/mesh/D010190>` |
| Join key | `oa:hasTarget` (a shared PubMed article IRI = the definition of co-occurrence) |
| Species restriction | `ncbigene:taxid <identifiers.org/taxonomy/9606>` |
| Definition of "strength" | `COUNT(DISTINCT ?article)` |

**3. Results came out.**

| Rank | Gene | NCBI Gene | Co-occurring papers |
|---:|---|---|---:|
| 1 | TP53 | 7157 | 1581 |
| 2 | AKT1 | 207 | 1200 |
| 3 | EGFR | 1956 | 1151 |
| 4 | VEGFA | 7422 | 1129 |
| 5 | KRAS | 3845 | 1076 |
| 6 | **INS** | 3630 | 986 |
| 7 | NFKB1 | 4790 | 889 |
| … | | | |
| 16 | **GAPDH** | 2597 | 604 |

**4. And the COUNT cross-check exposed a methodological flaw.**

```
Total papers annotated with D010190                    = 236,144
Of those, papers where TP53 co-occurs (strict, all)    =  32,597
```

The value on the sample (1,581) and the strict value (32,597) are **off by about 20×**. To avoid a timeout, an inner `LIMIT 20000` had been applied, so a smaller sample value is expected in itself. The problem is the ratio: as shown below, **those 20,000 rows were not a uniform random sample.**

**And it was not only the absolute numbers that were off.**

The sample is 20,000 out of 236,144 = **8.47%**. Under a uniform sample the full-set value should be **11.81×** the sample value. The measured ratios ran **14.97× to 32.33×**, all 20 genes exceeded the expected value, and the spread between genes was **2.2×**.

As a result, **the ranking actually changed** (from here on, the results are from the 369 s run; ranks on all rows are corrected to the full top list recomputed on 2026-10-20).

| Gene | Rank on the sample | Rank on all rows | |
|---|---:|---:|---|
| **MTOR** | 20th | **9th** | ← up 11 places |
| **INS** | 6th | **17th** | ← down 11 places |
| IL6 | 17th | 12th | |
| EGF | 13th | outside (26th or lower) | |

> **Had the cross-check not been demanded, a table with the wrong ranking would have gone straight through.** Not just the absolute numbers — the ordering itself could not be trusted.

Note that trying to count all 20 genes strictly in a single query **timed out at 60 seconds**. Only by splitting into batches of 3–6 genes did it run to completion.

> **Had the cross-check not been demanded, a plausible-looking table would have gone straight through.**
>
> That single line, "cross-check the counts with COUNT as well," is the highest-return request in this tutorial.

> 📝 **On the 2026-10-20 re-runs this error did not occur.** Sonnet (63 s) and Haiku (151 s) applied no inner `LIMIT`, counted all rows from the start, and did not time out. Whether a run samples depends on the model and the run. **That some runs avoid it is no reason to skip the cross-check**: without it you cannot tell which run you got.
>
> The top 20 recomputed on all rows (2026-10-20) includes **CD8A (14th), CD274 (PD-L1, 18th) and CD4 (20th)**, which were missing from August's "sample top 20, recounted in full" table.
>
> TP53 32,597 / AKT1 31,314 / EGFR 24,044 / TGFB1 21,785 / VEGFA 21,011 / TNF 20,199 / KRAS 20,109 / NFKB1 18,370 / MTOR 17,748 / ERBB2 17,375 / MYC 16,765 / IL6 16,763 / GAPDH 16,581 / CD8A 16,416 / CTNNB1 16,310 / MAPK1 15,751 / INS 15,517 / CD274 14,766 / BCL2 14,534 / CD4 13,923

---

### ★ And even with a good question, limits remain

Do not stop here. **The specified version's answer has clear flaws too.**

**(a) Things that are not biological have crept into the top ranks**

- **INS (insulin), 6th on the sample, 17th in full** — co-occurrence via the organ, the pancreas. Insulin turning up in pancreatic cancer papers is a matter of course, not a causal relationship
- **GAPDH, 16th on the sample, 13th in full** — it appears in the Methods section of a great many papers simply because it has served for years as a housekeeping gene used as an internal control
- **POTEF, 14th on the sample, 24th in full (outside the top 20)** — a primate-specific chimeric gene formed by the fusion of an actin retrogene (UniProt A5A3E0 even names it "Chimeric POTE-actin protein"). Its C-terminal region is highly similar to ACTB, and in mass spectrometry **some peptides assigned to ACTB are reported to be shared with POTEF/POTEE/POTEI/POTEJ**
  - ⚠️ **But whether that is "the reason it lands at 14th in pancreatic cancer papers" has not been confirmed.** All we have is a suspicion of identification ambiguity from sequence similarity. **Do not promote a guess into an assertion** — do not do here the very thing this tutorial warns against in Chapter 7

**(b) The genuine drivers are missing**

**SMAD4 and CDKN2A**, the principal drivers of pancreatic cancer, **fall outside the top 20**.

**Why.** Because co-occurring paper count measures "how famous the gene is and how many papers have been written about it" — **it does not measure disease specificity**. TP53 is studied across all cancers, so it turns up in pancreatic cancer papers in bulk.

The question said "ordered by strength of association," but **it never specified which association.** If you want specificity, you need an additional specification such as "normalize by co-occurrence counts across all cancers."

> **Lesson 2 of this chapter:** a good question makes the answer better. **But limits remain even after you make the question good.**
>
> Verification does not end with improving the question. On to [Chapter 7](07-verification-en.md).

---

## Chapter summary

1. **Some questions are hard to answer with search tools alone.** Guaranteeing completeness takes SPARQL (Demo 4)
2. **When the answer looks strange, suspect whether you wrote your intent into the question, not the syntax.** KW-0458 and GO:0043202 gave completely different answers (Demo 3')
3. **A vague question gets a plausible answer from memory, without consulting a database** (the failure demo)
4. **Specifying it costs 15× more, but the provenance can be stated and errors can be found by yourself**
5. **Limits remain even after specification.** Co-occurrence in text mining is not causation

---

Next → [05. Skills](05-skills-workflows-en.md) — or feel free to skip ahead to [06. How to Ask a Good Question](06-good-questions-en.md)
