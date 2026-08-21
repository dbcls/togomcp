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

**Measured at 39–51 s. The most robust of the five demos** (measured on two different models, zero failures and zero retries in both).

### What to watch for is that it hits a wall partway through

`search_pdb_entity` runs first. The result: **1,872 hits, in no particular order**.

**This search tool cannot answer the question.** Producing "the top 10 by best resolution" requires sorting on resolution, a numeric field, and that is a job for SPARQL, not for a search API.

So it proceeds to `get_MIE_file("pdb")` → `run_sparql`. This is one of the few demos where **the reason SPARQL is needed is visible on screen**.

### Results (measured 2026-08-21)

| # | PDB | Å | Title (excerpt) |
|---|---|---|---|
| 1 | **9ZNL** | 1.16 | Mpro covalently bound to inhibitor GRL-050-22 |
| 2 | 7GEF | 1.18 | COVID Moonshot — BEN-DND-93268d01-11 |
| 3 | 7K3T | 1.20 | possible zinc-binding intermediate |
| 4 | 9HJH | 1.20 | compound 1 bound to Mpro |
| 5 | 7GBE | 1.224 | COVID Moonshot — JAG-UCB-a3ef7265-20 |
| 6 | 7GEH | 1.23 | COVID Moonshot — EDJ-MED-06d94977-2 |
| 7 | 9HAK | 1.25 | compound 119 bound to Mpro |
| 8 | 9RJ5 | 1.25 | SARS-CoV-2 with a bound inhibitor |
| 9 | 6YB7 | 1.25 | unliganded active site |
| 10 | 7GBT | 1.25 | COVID Moonshot — BEN-DND-7e92b6ca-2 |

You can also get the breakdown by method: **X-ray 1,799 / cryo-EM 25 / neutron 4 / solution NMR 3 / electron crystallography 1** (1,832 total, measured 2026-08-21).

> 💡 **These numbers move.** Three weeks earlier the measurement totalled 1,822. Ten more since. **The databases are alive.**

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
ORDER BY ?res
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

This requires connecting UniProt (function and localization annotations) with ChEMBL (drug–target relationships). Measured at 79 s.

### Results

**Of 52 human lysosomal lumen enzymes, 3 are mechanism-of-action targets of an approved drug.**

| Gene | Approved drug | Action | What it means |
|---|---|---|---|
| **GLA** | migalastat | **STABILISER** | A pharmacological chaperone for Fabry disease. **Within these 52, the only case that targets the causative enzyme of a lysosomal disease itself** |
| **GAA** | miglitol, voglibose | INHIBITOR | The intent is not Pompe disease but **type 2 diabetes** (inhibition of intestinal α-glucosidase) |
| **PDGFRB** | imatinib, sunitinib and 11 others | INHIBITOR | A receptor tyrosine kinase. **Not a lysosomal enzyme** |

> 💡 **An easy confusion.** In ChEMBL, the drug carrying an indication for Pompe disease (Glycogen Storage Disease Type II) is **miglustat**, not miglitol. The names are similar.

The third one, PDGFRB, dominates the result by row count (11 of 14 drugs). But it is merely annotated to the lysosomal lumen in the context of receptor uptake and degradation — it is not a lysosomal enzyme in the usual sense. **This is a case where the scope definition fed straight through into the result** — taken up in the very next section.

Set PDGFRB aside and here is what can be read off.

> **Within these 52, the only approved small molecule aimed directly at a lysosomal enzyme was migalastat for GLA.** The two GAA drugs are diabetes drugs with a different indication.
>
> That is not surprising. **Lysosomal diseases are treated by "replacing" the enzyme, not by "inhibiting" it.**

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

### ⚠️ The most important thing here is that the original question was bad

How you define "lysosomal enzyme" makes the answer **an entirely different thing**.

Take UniProt's keyword **KW-0458 "Lysosome"** at face value and 161 proteins match. But that is **a subcellular-localization keyword, not "lysosomal enzyme."** In come INSR (the insulin receptor), PDGFRB, MTOR, PCSK9, LRRK2, and about 20 RAB GTPases.

The approved-drug side then looks like this:

> **22 insulin preparations and 12 PDGFR kinase inhibitors**

Put that under the heading "approved drugs targeting lysosomal enzymes" and in a room of biologists you would be called out within seconds.

**Narrowing by EC number to `3.*` (hydrolases) does not fix it either.** 113 of the 161 survive. RAB GTPases are EC 3.6.5.2 — respectable hydrolases.

**The fix that worked was switching to a GO term.**

```sparql
up:classifiedWith obo:GO_0043202     # lysosomal lumen
```

Candidates narrow from 161 → **52**, and the set comes to center on genuine lumenal hydrolases: GBA1, GLA, HEXA/HEXB, GAA, IDUA, IDS, ARSA/ARSB.

> **Lesson 1 of this chapter:** when the answer looks strange, what is wrong is usually not the query's syntax but **how you defined the target**.

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

Because salt forms are registered as separate molecules (migalastat / its hydrochloride, sunitinib / its malate). **Row count ≠ drug count.** There are 16 rows and 14 drugs, but effectively 12 active ingredients.

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

**Measured at 12–22 s. And the tool calls numbered 1, or 0.** What comes back is a fluent answer like this:

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

**Nothing was called.** Not even the usage guide (which itself says "call me first, every time").

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

That is no accident. This search only looks at **whether the protein's name contains the string "cancer."** TP53's UniProt name is "Cellular tumor antigen p53"; KRAS is "GTPase KRas". **Neither contains the string "cancer," so they are structurally unreachable.**

> **There are traces of a database being touched, and the answer comes from memory.**
>
> This is the failure mode this tutorial most wants to convey.

### ★ Either pattern, the same conclusion

Pattern ① is "never touched it"; Pattern ② is "only traces of touching it." **Different phrasings — but either way, the answer came from memory.**

And here is what matters — **from what is on screen, you cannot tell which one it was.** The fluency is the same, the speed is the same. **You only find out by opening the log.**

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

**Measured at 182 s, with 8 tool calls. Roughly 15× the cost.**

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

The value on the sample (1,581) and the strict value (32,597) are **off by about 20×**. To avoid a timeout, an inner `LIMIT 20000` had been applied — and **those 20,000 rows were not a uniform random sample.**

**And it was not only the absolute numbers that were off.**

The sample is 20,000 out of 236,144 = **8.47%**. Under a uniform sample the full-set value should be **11.81×** the sample value. The measured ratios ran **14.97× to 32.33×**, all 20 genes exceeded the expected value, and the spread between genes was **2.2×**.

As a result, **the ranking actually changed.**

| Gene | Rank on the sample | Rank on all rows | |
|---|---:|---:|---|
| **MTOR** | 20th | **9th** | ← up 11 places |
| **INS** | 6th | **16th** | ← down 10 places |
| IL6 | 17th | 12th | |
| EGF | 13th | 20th | |

> **Had the cross-check not been demanded, a table with the wrong ranking would have gone straight through.** Not just the absolute numbers — the ordering itself could not be trusted.

Note that trying to count all 20 genes strictly in a single query **timed out at 60 seconds**. Only by splitting into batches of 3–6 genes did it run to completion.

> **Had the cross-check not been demanded, a plausible-looking table would have gone straight through.**
>
> That single line, "cross-check the counts with COUNT as well," is the highest-return request in this tutorial.

---

### ★ And even with a good question, limits remain

Do not stop here. **The specified version's answer has clear flaws too.**

**(a) Things that are not biological have crept into the top ranks**

- **INS (insulin) at 6th** — co-occurrence via the organ, the pancreas. Insulin turning up in pancreatic cancer papers is a matter of course, not a causal relationship
- **GAPDH at 16th** — it appears in the Methods section of a great many papers simply because it has served for years as a housekeeping gene used as an internal control
- **POTEF at 14th** — a primate-specific chimeric gene formed by the fusion of an actin retrogene (UniProt A5A3E0 even names it "Chimeric POTE-actin protein"). Its C-terminal region is highly similar to ACTB, and in mass spectrometry **some peptides assigned to ACTB are reported to be shared with POTEF/POTEE/POTEI/POTEJ**
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

1. **Some questions cannot be answered by search tools.** That is where SPARQL becomes necessary (Demo 4)
2. **When the answer looks strange, suspect the definition of the target, not the syntax.** KW-0458 and GO:0043202 gave completely different answers (Demo 3')
3. **A vague question fails plausibly, in 12 seconds, without consulting a database** (the failure demo)
4. **Specifying it costs 15× more, but the provenance can be stated and errors can be found by yourself**
5. **Limits remain even after specification.** Co-occurrence in text mining is not causation

---

Next → [05. Skills](05-skills-workflows-en.md) — or feel free to skip ahead to [06. How to Ask a Good Question](06-good-questions-en.md)
