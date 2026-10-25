# Demo transcripts (fallback)

**If the live demo goes down, project this.** See the [README](README-en.md#fb) for how to use it.

## Measurement conditions

| Item | Value |
|---|---|
| Recorded | **2026-08-21** |
| Model | Session configured as **claude-opus-5** (the model that actually did the processing was not verified) |
| Server | Hosted `https://togomcp.rdfportal.org/mcp` |
| Client | Agent run through the API (not the desktop app's screen) |
| Endpoints | All **healthy**. The only failure was one timeout in failure demo B |
| Language | Japanese prompts |

> 📝 **About this English edition.** The sessions were run with Japanese prompts. The prompts and the model's replies below are translations (where the English handbook uses the same prompt, its wording is used). Tool calls, arguments, SPARQL and returned data are reproduced as recorded.

> ⚠️ **This is the 2026-08-21 record.** The main demo values were re-measured on real data on 2026-10-01 and 2026-10-14. Everything matched except the number of databases (37 → 45 → **47**) and **§9 TogoVar (changed throughout by the 10-09 data reload; §9 has been replaced with the 10-14 values)** (details in "What changed in the review" at the top of the instructor script). When you project it, say "this is the August record".
>
> ⚠️ **On 2026-10-20 the main queries were re-run on TogoMCP 2.27.0.** The values matched (PDB by method: X-ray 1,818, total 1,851; insulin products in the KW-0458 version: 21). The search in §7 did match TP53 as well; TP53 was simply outside the top 20 rows returned (it was not "unreachable"; see "The 2026-10-20 review" at the top of the instructor script).
>
> ⚠️ **On 2026-10-20 every demo was also re-run on Sonnet. The values matched, but in four demos the model behaved differently from August** (§5 PDB, §6 lysosome, §7 failure demo A, §8 failure demo B). The record has not been rebuilt: it stays as "the 2026-08 record", and each of those sections opens with a note on the 10-20 behavior. **If the live run takes a different path from this record, that by itself is not a fault** (see "What the 2026-10-20 Sonnet re-measurement showed" at the top of the instructor script).
>
> ⚠️ **Durations and tool-call behavior depend on the model.** The August re-measurement on **Sonnet 5** is in the appendix. Short demos take **1.5 to 2.5 times** as long. On 10-20, Sonnet took 19 s for the connection check, 29 s for demo 1, about 29 s for demo 2, 54 s for PDB, 64 s for the lysosome demo, 25 s for failure demo A and 63 s for failure demo B.

---

## 1. Database list (connection check) [M1]

**Prompt**

```
What databases can you use from TogoMCP?
```

**Measured 8 s** / 2 tool calls / 0 SPARQL / no failures

**Tool calls**

1. `TogoMCP_Usage_Guide()` → v6 guide retrieved. GATE 0 = bounded (list)
2. `get_sparql_endpoints()` → **37 databases / 10 endpoints** (August). primary=16, ebi=6, ncbi=5, sib=4, 6 on their own (pubchem, pdb, ddbj, glycosmos, nims, togovar)

**Reply**

> Through RDF Portal, **37 databases** sit on 10 SPARQL endpoints (August). By field:
>
> **Proteins and structures**: UniProt, PDB (about 255,000 entries), jPOST, OMA, BRENDA
> **Genes and genomes**: Ensembl, NCBI Gene, HGNC, Bgee, HCO / MCO, MoG+
> **Variants and disease**: ClinVar, TogoVar, GWAS Catalog, MedGen, MONDO, NANDO
> **Compounds and drug discovery**: PubChem, ChEBI, ChEMBL, MassBank
> **Reactions and pathways**: Rhea, Reactome
> **Ontologies**: GO, MeSH, and the `ontology` graph that bundles about 20 (HP / UBERON / CL / SO / EFO and others)
> **Literature**: PubMed, PubTator
> **Microbes**: BacDive, MediaDive, NBRC, AMR Portal
> **Sequences and taxonomy**: DDBJ, NCBI Taxonomy
> **Other**: GlyCosmos (glycans), SuperCon (superconducting materials)
>
> The endpoints are shared: databases on the same endpoint can be JOINed directly in one SPARQL query, and when you cross endpoints you bridge them by converting IDs with TogoID.

**Instructor note**: a safe demo that finishes in 8 seconds. The guide's table and the live values matched exactly (no drift).

> ⚠️ **As of 2026-10-14 there are 47 databases / 16 endpoints** (primary=20, ebi=6, ncbi=5, sib=4, 12 on their own. Added since August: Fanta.bio, WikiPathways, IDSM, PubCaseFinder, LIPID MAPS, SwissLipids, MarpolBase, the trial bh26microbes, and JoGo and TiSMeD on 10-09). If you project this record, add out loud: "it is 47 now".

---

## 2. Insulin → UniProt [M2]

**Prompt**

```
Give me the UniProt entry for the human insulin (INS) gene product. Function and sequence length too.
```

**Measured 18 s** / 4 tool calls / 1 SPARQL / no failures

**Tool calls**

1. `TogoMCP_Usage_Guide()` → GATE 0 re-run
2. `search_uniprot_entity(query="gene_exact:INS AND organism_id:9606 AND reviewed:true", limit=10)` → **P01308**, exactly one hit
3. `get_MIE_file(database="uniprot")` → adopts the `sequence_mass` example (whose subject is P01308 itself)
4. `run_sparql(database="uniprot", ...)` → 1 row: INS_HUMAN / mass 11,981 / length **110**

**Result**

| Item | Value |
|---|---|
| Accession | **P01308** (INS_HUMAN, Swiss-Prot) |
| Sequence length | **110 aa** |
| Mass | **11,981 Da** |

**Reply**

> The UniProt entry for human insulin is **P01308** (entry name INS_HUMAN, Swiss-Prot reviewed). Gene symbol INS, organism Homo sapiens (NCBI taxon 9606).
>
> **Function** (UniProt Function annotation)
> Insulin decreases blood glucose concentration. It increases cell permeability to monosaccharides, amino acids and fatty acids, and accelerates glycolysis, the pentose phosphate cycle and glycogen synthesis in liver.
>
> **Sequence length**
> The canonical isoform P01308-1 is **110 amino acids**, molecular weight **11,981 Da**. This is the full-length precursor, preproinsulin: the signal peptide (1-24), B chain (25-54), C peptide (57-87) and A chain (90-110) are cut out by processing. "Cleaved into: Insulin B chain; Insulin A chain" in the UniProt protein name refers to that cleavage.

**★ Instructor note: always explain the 110 aa**

Some participants will remember "insulin = 51 aa". UniProt's canonical sequence is not the mature A+B chains (21+30=51) but **the full-length preproinsulin, 110 aa**. Pass over it silently and someone will point it out as an error.

**One more finding:** write a bare `?protein up:sequence ?seq` and **the INS-IGF2 read-through `isoforms/F8WCM5-1` (200 aa) comes back too, giving 2 rows**. This run avoided it by naming the isoform IRI directly. Worth showing as a failure case.

> ⚠️ **The UniProt MIE changed on 2026-09-14.** Assuming the canonical is `isoforms/<ACC>-1` is wrong (782 entries have a canonical other than `-1`; fibronectin P02751 is `-15`). The current MIE selects it as "a `up:Simple_Sequence` whose IRI starts with the entry's own accession". The values for P01308 (110 aa, 11,981 Da) do not change.

---

## 3. ID conversion + PDB [M2]

**Prompt**

```
Convert that UniProt ID to an Ensembl gene ID and an HGNC ID. And the PDB structures too.
```

**Measured 18 s** / 5 tool calls / 0 SPARQL / no failures

**Tool calls**

1. `togoid_getRelation(source="uniprot", target="ensembl_gene")` → confirms the route
2. `togoid_convertId(ids="P01308", route="uniprot,ensembl_gene")` → `ENSG00000254647`
3. `togoid_convertId(ids="P01308", route="uniprot,hgnc")` → `6081`
4. `togoid_convertId(ids="P01308", route="uniprot,pdb")` → a long list of PDB IDs
5. `togoid_countId(source="uniprot", target="pdb", ids="P01308")` → **369 structures**

**Reply**

> The IDs corresponding to P01308 are:
>
> - **Ensembl gene ID: ENSG00000254647**
> - **HGNC ID: HGNC:6081** (TogoID returns the numeric part, `6081`)
>
> **369** PDB structures are registered; insulin is one of the most thoroughly solved proteins. Representative ones:
>
> - **1MSO**: human insulin, 1.0 Å high-resolution X-ray structure
> - **2HIU**: monomeric insulin by NMR
> - **1TRZ / 1ZNJ / 2AIY**: zinc-coordinated hexamers
> - **1LPH**: insulin lispro (rapid-acting analog)
> - **9M4X–9M51, 9LVC–9LVY**: the most recently deposited entries
>
> UniProt and Ensembl / PDB are on separate endpoints, so this conversion goes through TogoID's ID-conversion service rather than a SPARQL JOIN.

**Instructor notes**

- **There are many PDB entries: 369** (382 on 2026-10-20). Putting all of them on screen stalls the lecture. The right flow is to **get the count first with `togoid_countId`** and then name only representatives. "Measure the size with countId, then convertId" is exactly the procedure the guide recommends.
- **HGNC pitfall:** TogoID returns only the number `"6081"`, not the form `HGNC:6081`.

---

## 4. With and without a pinned graph [M3]

**Prompt**

```
Take a query that counts human lysosomal lumen enzymes in UniProt and run it both ways
(one version with the graph pinned in a FROM clause, one without), then compare the counts.
```

**Measured 40 s** / 6 tool calls / 3 SPARQL / no failures

> ⚠️ On 2026-10-20, Sonnet (26 s) **also narrowed by EC number** with the same prompt, so the counts came out as 62 / 52 (pinned) and 124 / 52 (not pinned). The pattern is the same: only `COUNT(*)` doubles, DISTINCT agrees. The diagnostic query also identified OMA's redeclaration.

### ★★ Result: say this part correctly

| Version | `COUNT(*)` | `COUNT(DISTINCT ?protein)` |
|---|---|---|
| **Pinned with FROM** | **98** | **98** |
| **Not pinned** | **196** | **98** |

**`COUNT(*)` doubles, but `COUNT(DISTINCT ?protein)` is 98 in both and agrees exactly.**

> ⚠️ **Do not just say "the count changes".** Showing only DISTINCT invites **the opposite conclusion**: "so FROM is unnecessary?"
>
> **Always put `COUNT(*)` and `COUNT(DISTINCT)` side by side in the same SELECT.** One slide then shows the contrast: "in the same query, one is broken and the other is fine".

### SPARQL executed

Pinned:

```sparql
PREFIX up:  <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(*) AS ?rows) (COUNT(DISTINCT ?protein) AS ?proteins)
FROM <http://sparql.uniprot.org/uniprot>
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:classifiedWith obo:GO_0043202 .
}
```

Not pinned: just delete the `FROM` line.

```sparql
PREFIX up:  <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(*) AS ?rows) (COUNT(DISTINCT ?protein) AS ?proteins)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:classifiedWith obo:GO_0043202 .
}
```

### Diagnostic query: find where the doubling comes from

**This in itself is teaching material: "how to investigate when a count looks suspicious".**

```sparql
PREFIX up:  <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?g (COUNT(DISTINCT ?protein) AS ?proteins)
WHERE {
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein up:reviewed 1 ;
             up:organism <http://purl.uniprot.org/taxonomy/9606> ;
             up:classifiedWith obo:GO_0043202 .
  }
  GRAPH ?g { ?protein a up:Protein . }
}
GROUP BY ?g ORDER BY DESC(?proteins)
```

| Graph | Proteins |
|---|---|
| `http://sparql.uniprot.org/uniprot` | 98 |
| `http://rdfportal.org/dataset/oma` | 98 |

**Reply**

> As an answer, the count is **98 in both versions**. But the unpinned version's row count has swollen to **196 rows, exactly double**.
>
> The cause is how the endpoint is shared. When the diagnostic query looks up where `a up:Protein` comes from, **both** `sparql.uniprot.org/uniprot` and `rdfportal.org/dataset/oma` return the same 98. OMA reuses UniProt's IRIs as they are and redeclares `up:Protein`, so without FROM each protein matches two typing triples and the rows double.
>
> The final count did not change in this example only because `COUNT(DISTINCT ?protein)` collapsed the duplicates of the same IRI. **Had you used `COUNT(*)`, the wrong answer 196 would have come back with no error and no warning.** The inflation is not fixed either: depending on the target proteins it may double or not. With `AVG` or `SUM`, or when you chain joins over redeclared predicates (2^k for k of them), DISTINCT cannot absorb it and the answer itself goes wrong.

**Instructor note**: this run actually hit the guide's "at most 2 consecutive `run_sparql`" rule. Before the third (diagnostic) query it called `get_graph_list` to reset the counter (which also exposed the 63 graphs sharing the endpoint, so it helped the lesson).

---

## 5. PDB Mpro by resolution [M4, flagship]

**Prompt**

```
Give me the top 10 PDB structures of the SARS-CoV-2 main protease
(3CL protease), ordered by best resolution.
```

**Measured 51 s** / 5 tool calls / 2 SPARQL / no failures

> ⚠️ **On 2026-10-20, Sonnet took a different path.** It called `search_pdb_entity` 5 times, slicing by the resolution ceiling (`res_max`), and reached **the same top 10 without SPARQL** (9ZNL onward; the 1.25 Å ties were 6YB7, 7JKV, 7GBT, 9HAK). The model itself noted that completeness was not guaranteed. 54 s. The record below is from 2026-08. If the live run does not go to SPARQL, say: "this run got there with search alone, but completeness is not guaranteed".

### ★ Showing that the search tool cannot sort (the 2026-08 record)

`search_pdb_entity` returned **`total`: 1,872**, but the resolution column ran

```
2.8 → 1.86 → 1.25 → 2.39 → 2.2 → 1.76 → 1.6 → 2.12 → 1.46 → 2.4 …
```

**This is relevance order, not resolution order.** There is range filtering with `res_min` / `res_max`, but **nothing equivalent to ORDER BY**, so "the top 10 by best resolution" **cannot be sorted out of a single search**.

> ⚠️ Earlier versions said "cannot answer in principle" here, but on 10-20 Sonnet reached the top 10 by stacking searches sliced with `res_max`. Do not say "in principle". What you can say is: "the search tool has no sorting, and even when it gets there, completeness is not guaranteed".

### SPARQL executed

```sparql
PREFIX pdbo: <http://rdf.wwpdb.org/schema/pdbx-with-vrptx-v50.owl#>
PREFIX dc:   <http://purl.org/dc/elements/1.1/>
SELECT ?entry_id ?res ?method (SAMPLE(?title) AS ?title)
FROM <http://rdfportal.org/dataset/pdb>
WHERE {
  ?entry a pdbo:datablock .
  FILTER(STRSTARTS(STR(?entry), "http://rdf.wwpdb.org/pdb/"))
  BIND(STRAFTER(STR(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbo:has_entityCategory/pdbo:has_entity/pdbo:link_to_enzyme
         <http://purl.uniprot.org/enzyme/3.4.22.69> .
  { ?entry pdbo:has_entity_src_genCategory/pdbo:has_entity_src_gen/pdbo:link_to_taxonomy_source
           <http://purl.uniprot.org/taxonomy/2697049> }
  UNION
  { ?entry pdbo:has_entity_src_natCategory/pdbo:has_entity_src_nat/pdbo:link_to_taxonomy_source
           <http://purl.uniprot.org/taxonomy/2697049> }
  ?entry pdbo:has_exptlCategory/pdbo:has_exptl/pdbo:exptl.method ?method .
  OPTIONAL { ?entry pdbo:has_refineCategory/pdbo:has_refine/pdbo:refine.ls_d_res_high ?xres }
  OPTIONAL { ?entry pdbo:has_em_3d_reconstructionCategory/pdbo:has_em_3d_reconstruction/pdbo:em_3d_reconstruction.resolution ?emres }
  BIND(COALESCE(?xres, ?emres) AS ?res)
  FILTER(BOUND(?res))
  OPTIONAL { ?entry dc:title ?title }
}
GROUP BY ?entry_id ?res ?method
ORDER BY ?res ?entry_id
LIMIT 10
```

**Result**

| # | PDB | Å | Summary |
|---|---|---|---|
| 1 | **9ZNL** | 1.16 | Covalently bound to inhibitor GRL-050-22 |
| 2 | 7GEF | 1.18 | COVID Moonshot BEN-DND-93268d01-11 |
| 3 | 7K3T | 1.20 | Possibly captures a zinc-bound intermediate |
| 4 | 9HJH | 1.20 | Complex with compound 1 |
| 5 | 7GBE | 1.224 | COVID Moonshot JAG-UCB-a3ef7265-20 |
| 6 | 7GEH | 1.23 | COVID Moonshot EDJ-MED-06d94977-2 |
| 7 | 6YB7 | 1.25 | Inhibitor-free (apo) form |
| 8 | 7GBT | 1.25 | COVID Moonshot BEN-DND-7e92b6ca-2 |
| 9 | 7GEC | 1.25 | COVID Moonshot VLA-UCB-00f2c2b3-7 |
| 10 | 7JKV | 1.25 | Complex with inhibitor GRL-2420 |

Ranks 7 to 10 are 4 of the 6 entries tied at 1.25 Å (6YB7, 7GBT, 7GEC, 7JKV, 9HAK, 9RJ5). With only `ORDER BY ?res`, as at recording time, the order of ties changes from run to run, so the version shown adds `?entry_id` as a second key (re-run 2026-10-14). **If 9HAK or 9RJ5 appears live, that is not an error.**

**Breakdown by experimental method** (EC 3.4.22.69 × taxon 2697049. **Replaced with the 2026-10-20 values**; at the 8-21 recording it was X-ray 1,799, total 1,832)

| Method | Count |
|---|---|
| X-ray diffraction | 1,818 |
| Cryo-EM | 25 |
| Neutron diffraction | 4 |
| Solution NMR | 3 |
| Electron crystallography | 1 |
| **Total** | **1,851** |

**Instructor note: if asked about the mismatch in counts**

Search tool 1,872 vs SPARQL 1,832 (at the 8-21 recording). This is a difference in how the population is defined (search = free-text match; SPARQL = the structured condition EC 3.4.22.69 × taxon 2697049). The accurate explanation is **"the definitions differ", not "the numbers differ, so one of them is broken"**.

The resolution predicate differs by method (X-ray uses `refine.ls_d_res_high`, cryo-EM uses `em_3d_reconstruction.resolution`, NMR has neither). The query above picks up both with `COALESCE`.

⚠️ **The query in this record is not the one in the handbook (Chapter 4) and the slides.** The handbook's query is restricted to X-ray, and the slides' "resolution is X-ray only" describes that one. The top 10 were the same either way (2026-10-20). Do not project this record and say "X-ray only".

---

## 6. Lysosomal enzymes × approved drugs [M4]

**Prompt**

```
Among human lysosomal enzymes, tell me which ones are targets of approved drugs.
```

**Measured 100 s** / 7 tool calls / 4 SPARQL / no failures

> ⚠️ **On 2026-10-20, Sonnet chose a different definition.** It defined the set by **GO:0005764** (lysosome), picked by hand from about 80 proteins, and answered **GLA and GAA only** (no PDGFRB; 64 s). The record below (GO:0043202 → 3 of 52) is from 2026-08. If a different answer comes out live, use it as the example for Chapter 4's "defining the target set".
>
> For reference: when the prompt states the intent (enzymes working in the lumen; exclude receptors, chaperones and proteins that only pass through) and asks to "state the definition and give the count with COUNT", Sonnet chose GO:0043202 (52 proteins) all 3 times on 10-20 and answered GLA and GAA. Excluding PDGFRB was the model's judgment, not an annotation, and the excluded set varied slightly from run to run.

### SPARQL executed (1: UniProt side)

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?acc ?gene ?name
FROM <http://sparql.uniprot.org/uniprot>
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism taxon:9606 ;
           up:classifiedWith obo:GO_0043202 ;
           up:enzyme ?ec .
  OPTIONAL { ?protein up:encodedBy/skos:prefLabel ?gene }
  OPTIONAL { ?protein up:recommendedName/up:fullName ?name }
  BIND(STRAFTER(STR(?protein), "uniprot/") AS ?acc)
}
ORDER BY ?gene
```

→ **52 proteins**

ACP2, ARSA, ARSB, ASAH1, ATP13A2, CTSA, CTSD, CTSF, CTSK, CTSL, CTSS, CTSV, FUCA1, GAA, GALC, GALNS, **GBA1**, **GLA**, GLB1, GNS, GUSB, GYG1, HEXA, HEXB, HGSNAT, HPSE, HSP90AA1, HSPA8, HYAL1, HYAL4, IDS, IDUA, IFI30, LGMN, LIPA, MAN2B1, MAN2B2, MANBA, NAAA, NAGLU, NEU1, NEU4, **PDGFRB**, PLBD2, PLD3, PPT1, PPT2, RNASET2, SGSH, SMPD1, TPP1, TXNDC5

### 2: ChEMBL side, passing the 52 accessions in `VALUES`

Key part only (the full text is long, so `VALUES` is abbreviated):

```sparql
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?acc ?targetType ?targetLabel ?drug ?actionType ?phase
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  VALUES ?up { <http://purl.uniprot.org/uniprot/P11117> … all 52 … }
  ?comp skos:exactMatch ?up .
  ?target cco:hasTargetComponent ?comp ;
          rdfs:label ?targetLabel ;
          cco:targetType ?targetType .
  ?mech a cco:Mechanism ; cco:hasTarget ?target ;
        cco:hasMolecule ?mol ; cco:mechanismActionType ?actionType .
  ?mol rdfs:label ?drug ; cco:highestDevelopmentPhase ?phase .
  FILTER(?phase = 4)
  BIND(STRAFTER(STR(?up), "uniprot/") AS ?acc)
}
ORDER BY ?acc ?drug
```

> ⚠️ **Do not add `?target a cco:SingleProtein`.** Measured: it drops 16 rows → 8 and 14 drugs → 7 **with no error**. The ChEMBL MIE warns about this trap with a worked example.

### Result: 3 proteins / 14 drugs (16 rows) out of 52

| Gene | targetType | Approved drug | Action |
|---|---|---|---|
| **GLA** | SINGLE PROTEIN | migalastat (+ hydrochloride) | **STABILISER** |
| **GAA** | SINGLE PROTEIN | miglitol | INHIBITOR |
| **GAA** | **PROTEIN FAMILY** | voglibose | INHIBITOR |
| **PDGFRB** | SINGLE / COMPLEX | imatinib, dasatinib, sunitinib, sorafenib, regorafenib, pazopanib, nintedanib, midostaurin, quizartinib, tivozanib, becaplermin | INHIBITOR (becaplermin only: AGONIST) |

**Reply**

> There are **52** reviewed proteins that localize to the human lysosomal lumen (GO:0043202) and carry an EC number. Of those, **3** are registered in ChEMBL as mechanism-of-action targets of an approved drug (phase 4).
>
> **GLA (alpha-galactosidase A, P06280)**: migalastat. Its action is not inhibition but **STABILISER**: a pharmacological chaperone that binds the mutant enzyme and helps it fold, a treatment for Fabry disease. It can be called **the only small molecule targeting the causative enzyme of a lysosomal disease itself**.
>
> **GAA (lysosomal alpha-glucosidase, P10253)**: miglitol, voglibose. Both are INHIBITORs, but they are aimed not at Pompe disease but at **type 2 diabetes**, suppressing the post-meal rise in blood glucose by inhibiting intestinal alpha-glucosidases.
>
> **PDGFRB (P09619)**: 11 drugs. But this is a receptor tyrosine kinase; its lysosomal-lumen GO annotation comes from receptor uptake and degradation, and it is not a "lysosomal enzyme" in the usual sense. **An example of the scope definition feeding straight into the result.**
>
> So, in substance, what the RDF shows is: the approved small molecule aimed directly at a lysosomal enzyme is **migalastat for GLA, one line**; GAA has diabetes drugs with a different indication; and PDGFRB is noise from the GO annotation.

### ★ Expected question 1: "Why doesn't enzyme replacement therapy show up?"

`search_chembl_molecule(query="imiglucerase")` → **CHEMBL1201632** (1 hit; **it exists**)

Follow-up:

| Item | Value |
|---|---|
| substanceType | **Enzyme** |
| highestDevelopmentPhase | 4 (approved) |
| Mechanism | present (CHEMBL_MEC_2080) |
| hasTarget | **CHEMBL2364176 "Glucocerebroside"** |
| targetType | **SMALL MOLECULE** |
| TargetComponents / UniProt links | **0 / 0** |
| mechanismActionType | HYDROLYTIC ENZYME |

> Imiglucerase's target is **the substrate (glucocerebroside)**, not a protein. ERT is not "a drug that inhibits an enzyme" but "a drug that replaces the enzyme itself", so ChEMBL registers its target on the substrate side. That is the structural reason **a join through UniProt accessions can never catch it**.

### ★ Expected question 2: "Why is PDGFRB mixed in?"

It really does carry GO:0043202. **A localization annotation is not a functional classification.** Not an error, but a question of how sharply the question is put.

### ★ The most interesting landing point: GBA1 returns 0 rows

**GBA1 (P04062) is among the 52, yet the approved-drug side returned 0 rows.** The Gaucher disease drugs miglustat and eliglustat target the substrate-synthesizing enzyme UGCG, so they are not linked to GBA1, and imiglucerase has its target on the substrate side as above.

**That "causative enzyme = drug target" does not hold becomes visible at the level of the data structure.**

**Instructor note**: salt forms of the same drug come out as separate rows (migalastat / its hydrochloride, sunitinib / its malate). **Rows ≠ drugs** (16 rows; 14 drugs once salt forms are merged).

---

## 7. ★★ Failure demo A (a vague question) [M4]

**Prompt**

```
Tell me about genes involved in cancer
```

**Measured 9 s** / **1** tool call / **0** SPARQL / MIE consulted: **no** / IDs verified: **no**

> ⚠️ **On 2026-10-20, Sonnet took 25 s and 2 tool calls** (`search_uniprot_entity` with keyword "Tumor suppressor" and "Proto-oncogene"). Most of the answer came from memory, but **it disclosed this itself: "TP53 and others are not in the search results; this is general knowledge".** The record below (memory-derived, without saying so) is from 2026-08. If the live run discloses it, say: "this run was honest. Not every run is."

**The only tool call made**

```
search_uniprot_entity(query="cancer AND organism_id:9606 AND reviewed:true", limit=20)
```

**Reply (excerpt)**

> Cancer-related genes fall broadly into "oncogenes" and "tumor suppressor genes".
>
> **Oncogenes**: KRAS, EGFR, ERBB2 (HER2), BRAF, PIK3CA, MYC, ALK, ABL1, RET, MET, CTNNB1
> **Tumor suppressors**: TP53 ("the guardian of the genome"; mutated in about half of human cancers), RB1, PTEN, APC, BRCA1 / BRCA2, CDKN2A, SMAD4, VHL, NF1, ATM, MLH1 / MSH2
>
> Which cancer type are you interested in?

### ★★★ Verification: the diff between tool output and reply (the core of this demo)

**The 20 rows the tool actually returned (all of them)**

| UniProt | Protein names |
|---|---|
| Q9Y238 | Deleted in lung and esophageal cancer protein 1 |
| P51587 | Breast cancer type 2 susceptibility protein |
| Q5HYN5 | Cancer/testis antigen family 45 member A1 |
| O00559 | Receptor-binding cancer antigen expressed on SiSo cells |
| P38398 | Breast cancer type 1 susceptibility protein |
| Q8TC20 | Cancer-associated gene 1 protein |
| Q9HCU9 | Breast cancer metastasis-suppressor 1 |
| P62952 | Apoptosis inducing factor BLCAP |
| O75638 | Cancer/testis antigen 2 (LAGE-1) |
| P23508 | Colorectal mutant cancer protein |
| Q9UL03 | Integrator complex subunit 6 |
| Q6SJ93 | Serine protease FAM111B |
| Q86SQ7 | Serologically defined colon cancer antigen 8 |
| P35243 | **Recoverin** (Cancer-associated retinopathy protein) |
| P78358 | Cancer/testis antigen 1 (NY-ESO-1) |
| Q9BPY8 | Homeodomain-only protein |
| Q99909 | Protein SSX3 |
| Q9UBW5 | Bridging integrator 2 |
| Q9Y5K1 | Meiotic recombination protein SPO11 |
| Q9Y657 | Spindlin-1 |

> **First, the decisive fact:** what the tool returned were **protein_name strings; not a single gene symbol came back.** The returned columns are just three: `Entry / Protein names / Organism`. So **not one** of the gene symbols listed in the reply **could have been taken from this tool output**.

**Diff**

| Verdict | Genes | Count |
|---|---|---|
| A string trace exists in the tool output (in the protein_name description, not as a symbol) | BRCA1, BRCA2 | 2 |
| **Not present in the tool output in any form** | KRAS, EGFR, ERBB2, BRAF, PIK3CA, MYC, ALK, ABL1, RET, MET, CTNNB1, TP53, RB1, PTEN, APC, CDKN2A, SMAD4, VHL, NF1, ATM, MLH1, MSH2 | **22** |

**Diff rate = 22 / 24 = 91.7%.** Taking "gene symbols returned by the tool" as the denominator, it is **24 / 24 = 100%**.

**The diff in the other direction is just as bad.** Of the 20 rows the tool returned, only BRCA1 and BRCA2 made it into the reply. **The other 18 were ignored entirely.** Most of them are name-match noise that merely has the string "cancer" in protein_name (the cancer/testis antigens, **Recoverin**, and so on), not cancer drivers.

**What this reply really is**

1. The tool call ran once **as an alibi**; it was not used to generate the reply
2. The content of the reply is **100% from memory (knowledge from training)**
3. Not one NCBI Gene ID, HGNC ID or UniProt accession is attached → unverifiable and irreproducible
4. Even **numbers** such as "TP53 is mutated in about half of human cancers" come from memory, **with no source**
5. Not one source database is named
6. The reply does not disclose at all that it discarded 18 of the 20 rows the tool returned

> **The content itself is broadly correct by textbook standards. That is exactly why it is dangerous.** Because its correctness comes from memory, **it would look exactly the same if it were wrong, and the reader cannot tell the difference.**

---

## 8. ★★ Failure demo B (a specified question) [M4]

**Prompt**

```
In MeSH, first identify the descriptor for 'Pancreatic Neoplasms', then give me the
human genes associated with that disease as a table (the top 20, ordered by strength of
association), stating the source database and field names.
Cross-check the counts with COUNT.
```

**Measured 369 s (6 min 09 s)** / 13 tool calls / 8 SPARQL (7 succeeded, **1 timeout**)

> ⚠️ **On 2026-10-20, Sonnet took no sample and aggregated over all rows from the start** (63 s, 8 tool calls, 3 SPARQL, 0 timeouts). The error below, "the sample ranking is overturned by the cross-check", did not occur. TP53 at 32,597 and the 236,144 papers for D010190 matched. The record below is from 2026-08. If it does not reproduce live, show this record and say: "whether it happens depends on the model and the run. That is why you ask for a cross-check every time."

> 🔄 **Live, this took 6 minutes in August.** If you are short of time, project this record.

### Provenance (what the prompt asked for)

| Item | Value |
|---|---|
| MeSH descriptor | **D010190 "Pancreatic Neoplasms"** |
| Endpoint | `https://rdfportal.org/ncbi/sparql` |
| Graph 1 | `http://rdfportal.org/dataset/pubtator_central` |
| Graph 2 | `http://rdfportal.org/dataset/ncbigene` |
| Disease side | `dcterms:subject "Disease"` + `oa:hasBody = identifiers.org/mesh/D010190` |
| Gene side | `dcterms:subject "Gene"` + `oa:hasBody = identifiers.org/ncbigene/N` |
| Co-occurrence defined as | matching `oa:hasTarget` (PubMed article IRI) |
| Species restriction | `ncbigene:taxid = identifiers.org/taxonomy/9606` |
| ID cross-check | `togoid_convertId` route=`ncbigene,hgnc` resolved **20/20** |

**PubMed articles annotated with D010190: 236,144 in total.**

### ★★★ The COUNT cross-check "overturned" the sample ranking (the 2026-08 record)

The table below is **the top 20 genes of the sample, recounted over all rows**; "rank" is the rank among those 20 genes. For the true top 20 over all rows, see "Top 20 over all rows" further down.

| Rank | Gene | Co-occurring papers (all rows) | Rank in the 20,000-row sample |
|---:|---|---:|---|
| 1 | TP53 | **32,597** | 1 |
| 2 | AKT1 | **31,314** | 2 |
| 3 | EGFR | **24,044** | 3 |
| 4 | TGFB1 | **21,785** | 8 |
| 5 | VEGFA | **21,011** | 4 |
| 6 | TNF | **20,199** | 9 |
| 7 | KRAS | **20,109** | 5 |
| 8 | NFKB1 | **18,370** | 7 |
| 9 | **MTOR** | **17,748** | **20** ← up 11 |
| 10 | ERBB2 | **17,375** | 10 |
| 11 | MYC | 16,765 | 15 |
| 12 | IL6 | 16,763 | 17 |
| 13 | **GAPDH** | 16,581 | 16 |
| 14 | CTNNB1 | 16,310 | 19 |
| 15 | MAPK1 | 15,751 | 12 |
| 16 | **INS** | **15,517** | **6** ← down 10 |
| 17 | BCL2 | 14,534 | 11 |
| 18 | **POTEF** | 11,989 | 14 |
| 19 | CASP3 | 11,750 | 18 |
| 20 | EGF | 10,522 | 13 |

**The sample is 20,000 / 236,144 = 8.47%. If it were a uniform sample, the all-rows value would be 11.81 times the sample value.** The measured ratios run from **14.97 (EGF) to 32.33 (MTOR)**: all 20 genes exceed the expectation, with a **2.2-fold spread** between genes.

> **The subset returned by `LIMIT 20000` is not a random sample.** As a result **the ranking really did reshuffle**: MTOR 20th → 9th, INS 6th → 16th (17th in the all-rows ranking), IL6 17th → 12th, EGF 13th → 20th (outside the top 20 in the all-rows ranking).
>
> **Had the cross-check not been requested, a table with the wrong ranking would have gone straight through.**

**Also: the COUNT query that put all 20 genes into one `VALUES` timed out at 60 seconds.** It only completed once split into batches of 3 to 6 genes.

### ★ Limits that remain: do not stop here

**Non-biological artifacts mixed into the top**

- **GAPDH (13th in the table, 16,581)**: a housekeeping gene. It appears in the Methods of nearly every wet-lab paper merely as an internal standard
- **POTEF (18th in the table; 24th and outside the top 20 in the all-rows ranking; 11,989)**: a chimeric gene fused with an actin retrogene (UniProt A5A3E0 = "Chimeric POTE-actin protein"). Its sequence is highly similar to ACTB, and it shares some of the peptides that mass spectrometry assigns to ACTB. ⚠️ **But whether that causes its rank has not been confirmed** (a guess made at recording time, corrected by the 2026-08-21 check)
- **INS (16th in the table, 17th in the all-rows ranking, 15,517)**: organ confounding, because the pancreas is an endocrine organ
- **AKT1 (2nd)**: possibly overestimated because a bare "Akt" / "PKB" in papers is normalized to AKT1

**Conversely, the main drivers of pancreatic ductal adenocarcinoma drop out of the top 20**

| Gene | Co-occurring papers | Compared with 20th (10,522) |
|---|---:|---|
| **CDKN2A** | 9,208 | **out** (inactivated in about 90% of PDAC) |
| **SMAD4** | 6,352 | **out** (inactivated in 45 to 55%) |
| BRCA2 | 5,547 | out |
| STK11 | 2,918 | out |

> **Raw co-occurrence counts measure not "genes important in pancreatic cancer" but "genes famous in the biomedical literature ∩ pancreatic cancer literature".**

**Two more**

- **The MeSH tree was not expanded.** Only D010190 was used; **D021441 "Carcinoma, Pancreatic Ductal"** and **D000077779** are separate descriptors. PDAC-specific papers are **missing entirely** from this count. This may also contribute to the underestimation of CDKN2A / SMAD4.
- **The top 20 is "an all-rows COUNT of the sample's top 20", not "the top 20 over all rows".** In the August recording, the all-rows COUNT over every gene timed out and did not complete. **When it was redone over all rows on 2026-10-20, genes absent from the sample table really did enter the top 20** (table below).

### Top 20 over all rows (2026-10-20, confirmed with `run_sparql`)

| Rank | Gene | Co-occurring papers | Rank | Gene | Co-occurring papers |
|---:|---|---:|---:|---|---:|
| 1 | TP53 | 32,597 | 11 | MYC | 16,765 |
| 2 | AKT1 | 31,314 | 12 | IL6 | 16,763 |
| 3 | EGFR | 24,044 | 13 | GAPDH | 16,581 |
| 4 | TGFB1 | 21,785 | 14 | **CD8A** | **16,416** |
| 5 | VEGFA | 21,011 | 15 | CTNNB1 | 16,310 |
| 6 | TNF | 20,199 | 16 | MAPK1 | 15,751 |
| 7 | KRAS | 20,109 | 17 | INS | 15,517 |
| 8 | NFKB1 | 18,370 | 18 | **CD274** (PD-L1) | **14,766** |
| 9 | MTOR | 17,748 | 19 | BCL2 | 14,534 |
| 10 | ERBB2 | 17,375 | 20 | **CD4** | **13,923** |

(21 CDH1 13,877 / 22 STAT3 13,470 / 23 IFNG 12,138 / 24 POTEF 11,989 / 25 HIF1A 11,760)

**CD8A, CD274 and CD4 in bold are genes that were not in the August sample table.** POTEF, CASP3 and EGF fall outside the top 20 over all rows. MTOR (9th) and GAPDH (13th) do not change.

### Side-by-side summary

| Aspect | A: vague | B: specified |
|---|---|---|
| Time | **9 s** | **369 s** |
| Tool calls | **1** (alibi) | **13** |
| SPARQL | **0** | **8** (7 succeeded / 1 timeout) |
| MIE consulted | no | yes |
| IDs verified | no | 20/20 |
| COUNT cross-check | no | yes: **overturned the sample ranking** |
| Provenance stated | no | endpoint / 2 graphs / 5 predicates |
| Where the answer came from | **100% memory** | 100% query results |
| **Reproducible** | **no** | yes |
| **Errors detectable** | **impossible** | **possible: it actually caught 2 flaws on its own** |

> **B took 41 times as long as A and hit a timeout on the way. But A's output cannot be verified, so even when it is correct it cannot be used.**
>
> **The speed gap is 41-fold, but the reliability gap is a qualitative break: "unknown" versus "measured".**

---

## 9. TogoVar GBA1 [M9, exercise]

**Prompt**

```
How many pathogenic variants are there in GBA1?
Which of them are frequent in the Japanese population?
```

**Measured 32 s** / 5 tool calls / **0 SPARQL** (REST only, so it may still work during an endpoint outage)

> ⚠️ **The values in this section are the 2026-10-14 re-measurement** (TogoVar was reloaded on 10-09, which changed both the counts and the unit of aggregation). The duration and the number of tool calls are still from the August record.

### Setup 1: resolving the gene name

| Search term | First row | match_type |
|---|---|---|
| **"GBA1"** | GBA1 (HGNC:4177) | **exact** ✅ |
| **"GBA"** | GBA1 (HGNC:4177) | **prefix** ⚠️ |

**"GBA" has no exact match at all.** All 6 hits (GBA1, GBA2, GBA3, GBAT2, GBA1LP, GBA3-AS1) are prefix matches. The old symbol "GBA" was renamed GBA1 in 2022 and is not in the current set of approved symbols.

> ⚠️ **Setup 1 turned out "weaker than expected".** After re-ranking, **GBA1 happens to come first**, so participants who do not look at `match_type` pass through thinking "no problem, then".
>
> **How to put it on the board:** "That the first row is right is **luck**. `match_type: prefix` means 'the symbol you asked for does not exist'."
> Pointing at **GBAT2 (= RFX5 antisense RNA 1, not even in the GBA family)** sitting in the same list works well.

### Setup 2: enrichment in the Japanese population

**Filter (pathogenic + likely pathogenic): `filtered` = 227**

By cohort (of the 227, how many have frequency data):
`clinvar 225` / `gnomad_exomes 131` / `gnomad_genomes 51` / **`tommo 31`** / `ncbn 16` / `gem_j_wga 12` / `jga_wgs 8` / `mgend 8` / `bbj2k 5` / `bbj1k 3` / `jogo 3`

**Narrow to ToMMo AF ≥ 0.0005 → `filtered` = 1**

> ⚠️ **The model chooses the threshold** (setup (4) on the slides, from 2026-10-22). The question only says "frequent". This record used 0.05% (AF ≥ 0.0005) and got 1. On 10-20, Sonnet chose 0.01% and got 4 (rs421016, rs381737, rs439898, rs1064651); Haiku used 0.01% and got 6 by combining ToMMo and NCBN. If the count differs, checking which threshold was chosen leads straight back to the point of the exercise.

**tgv3325667: `1:155235252:A>G` (GRCh38, SNV)**

- rsID **rs421016** / ClinVar **VCV000004288**
- HGVS: `NM_000157.4:c.1448T>C` / `NP_000148.2:p.Leu483Pro` (legacy name **L444P**)
- SIFT 0.01 / PolyPhen 0.977 / AlphaMissense 0.6022

| Cohort | AF | AC / AN |
|---|---|---|
| **ToMMo (Japan)** | **0.000785** | 96 / 122,332 |
| **NCBN (Japan)** | 0.000807 | 19 / 23,534 |
| **GEM-J WGA (Japan)** | 0.001326 | 20 / 15,088 |
| gnomAD exomes | 0.0000842 | 123 / 1,460,902 |
| gnomAD genomes | 0.000237 | 36 / 152,080 |

**Enrichment: ToMMo / gnomAD exomes ≈ 9.3-fold, ToMMo / gnomAD genomes ≈ 3.3-fold, GEM-J WGA / gnomAD exomes ≈ 15.7-fold.** All three Japanese cohorts are high together, so it reads as a population difference rather than a single-cohort artifact. (ToMMo's panel was updated and AN went from 108,602 to 122,332.)

> 💡 It also appears in the newly added JoGo (AF 0.00254) and BioBank Japan 2k (0.000509), but **their AN is small (393 and 3,928)**, so do not make them the centerpiece of the comparison.

> ⚠️ **Always add:** ToMMo and NCBN carry the quality flag `VQSRTrancheSNP99.95to100.00`, and GEM-J WGA carries `NotHighConfidenceRegion`. **GBA1 is highly homologous to the pseudogene GBAP1**, which makes short-read mapping difficult, so the possibility that part of the frequency difference is a technical false positive cannot be excluded.
>
> Ethics: say out loud that an AF of 0.08% is still rare and that Gaucher disease is autosomal recessive.
>
> ⚠️ **Do not say "heterozygous carriers don't develop it, so there is nothing to worry about".** On checking, there are several reports that **heterozygous GBA1 variants substantially raise the risk of Parkinson's disease** (Sanyal et al., *Mov Disord* 2020, PMID 32034799). That is exactly why Parkinson's disease and dementia with Lewy bodies are listed on screen. The accurate statement: "**heterozygous carriers do not develop Gaucher disease itself, but they are not unaffected either**". Do not give categorical reassurance.

### Setup 3: the unit-of-aggregation trap

| Breakdown | Sum | Matches `filtered` (227)? |
|---|---:|---|
| **type** (SNV 191 / deletion 31 / insertion 5) | **227** | ✅ **matches** |
| **significance** (Likely pathogenic 147 / Pathogenic 122 / Uncertain significance 32 / others) | **316** | ❌ **about 1.4×** |
| consequence | 827 | ❌ about 3.6× |

**Each breakdown counts "variants carrying that classification (consequence) at least once".** One variant carries several classifications, so the sum exceeds the number of variants. **"Pathogenic 122 + Likely pathogenic 147 = 269 pathogenic variants" is wrong**: 42 variants carry both.

**And "we filtered on pathogenic, yet Uncertain significance shows 32, and Benign and Likely benign 1 each".** That is because some variants are judged pathogenic under one condition and of uncertain significance under another. For rs421016 alone (`filtered`=1), its 15 classification records (14 ClinVar, 1 MGeND) count as 1 each for P, LP, RF and US in the breakdown, **4 in total**.

**The tool itself warns in `statistics_caveats`: "do not compare the sums with `filtered`".** As of 2026-10-20 the wording of that explanation matches the current behavior (it used to describe the pre-reload unit).

**Instructor note: where people get stuck live**

**HGVS is not in the default output.** A third call with `include_transcripts=True` is needed. **Build this into the exercise script from the start.** This is where participants get stuck with "there's no HGVS".

But the `include_transcripts=True` output is large (24 transcripts for rs421016, 2026-10-14), so for projection it is safer to have extracted just the MANE `NM_000157.4` row.

### Fit for public display ✅

**Safe to project.**

- All returned frequency information is **population aggregates** (af / ac / an). No individual genotypes, sample IDs, pedigrees or attributes
- Even the smallest AN is 15,088 alleles (≈7,544 people); no small cells posing a re-identification risk
- JGA (controlled access) appears **only as cohort counts**
- The ClinVar side shows only the number of submitters and condition names. No submitter names or case descriptions
- Disease names are **registered classification labels**, not diagnoses of specific individuals

---

# Appendix: re-measurement on Sonnet 5 (2026-08-21)

The live demos were planned on **Sonnet 5**, so we checked whether the record above (recorded with the opus-5 setting) reproduces.

## Conclusion: every demo reproduced. Values match; durations somewhat longer

| Demo | opus-5 setting | Sonnet 5 | Verdict |
|---|---|---|---|
| 1. DB list | 8 s / 2 calls / 37 DBs | **21 s** / 1 call / 37 DBs | values match; **about 2.5× slower** |
| 2. Insulin | 18 s / 4 calls / 1 SPARQL | **28 s** / 4 calls / 1 SPARQL | **P01308, 110 aa, 11,981 Da all match** |
| 3. ID conversion | 18 s / 5 calls | **30 s** / 4 calls | **ENSG00000254647, 6081, 369 all match** |
| 5. PDB Mpro | 51 s / 5 calls / 2 SPARQL | **47 s** / 5 calls / 2 SPARQL | **9ZNL 1.16 Å matches**; slightly faster |

**Zero failures, timeouts or retries on Sonnet 5 as well.**

> **Implication for instructors:** **allow 1.5 to 2.5 times as long for the short demos.** It is safer to estimate demo 1 in M2 at **around 30 s** and the connection check at **around 20 s** rather than 10.

## ★★ The failure demo came out stronger on Sonnet 5

For the same prompt, "Tell me about genes involved in cancer":

| | opus-5 setting | **Sonnet 5** |
|---|---|---|
| TogoMCP tool calls | **1** (`search_uniprot_entity`) | **0** |
| `TogoMCP_Usage_Guide` | called | **not called** |
| SPARQL | 0 | 0 |
| Genes listed in the reply | 24 | **27** |
| Of which absent from tool output | 22 to 24 (91.7 to 100%) | **27 (100%)** |
| DB identifiers | none | **none** |

Sonnet 5 **never touched a database.** Not even "one alibi search": purely from memory, it fluently answered with 27 genes (TP53, RB1, BRCA1/2, PTEN, APC, VHL, CDKN2A, NF1, KRAS, HRAS, NRAS, MYC, EGFR, ERBB2, BRAF, PIK3CA, ALK, EML4, MLH1, MSH2, MSH6, PMS2, ATM, CHEK2, PALB2, TERT), even sorted into categories.

**Its own account (translated):**

> "I had TogoMCP loaded (and its usage guide says of itself 'call me first, every time') and touched none of it. I treated it as recalling textbook knowledge and answered **just as I would with zero tools connected**."

### ⚠️ Effect on the script: the wording has to change

**The opus version of the script was built around opening the log and showing "this was the only search run". On Sonnet that search does not exist.**

You cannot know in advance which will happen on the day, so **use wording that works for both**.

**If there are 0 tool calls (the behavior observed on Sonnet)**, the story is actually simpler, and hits harder:

> 🎤 "Let me open the log. ... **It's empty.** It never touched a database."
> (pause)
> 🎤 "27 genes, sorted into categories, in 12 seconds. **Not one of them was looked up just now.** All of it is what the model remembered."
> 🎤 "And this usage guide says of itself, 'start over from the top for a new question'. **Even that was not called.**"
>
> (At measurement time the tool description said "call me first, every time", but in 2.27.0 it became a statement of fact. You can no longer say "it says 'call me every time'".)

**If a single search did run (the behavior observed on opus)**, follow the existing script: match the returned entities against the gene names in the reply and show that "not one of them is in there".

> **The conclusion is the same either way.** "Whether or not there is any trace of touching a database, the answer came from memory." **If anything, 0 calls is easier to understand**, so be glad if that happens.

## On the PDB counts: do not state them categorically

In the Sonnet 5 run, the method breakdown summed to **1,935** (X-ray 1,900 / EM 25 / NMR 5 / neutron 4 / electron crystallography 1). The recording the day before gave **1,832**.

**The cause of this difference has not been identified.** Only two things were observed:

- The total differed by 103 between the recording the day before (1,832) and the Sonnet 5 run (1,935)
- Running the §5 query (EC 3.4.22.69 × taxon 2697049) on 2026-10-20 gives a total of 1,851, which is smaller than 1,935

The hit count of `search_pdb_entity` also changed a lot with the search terms: **1,872 → 3,649**.

> **This in itself is teaching material.** "Questions meant to be the same give different numbers when the scope differs": the same pattern as KW-0458 vs GO:0043202 in Chapter 4. **Do not state absolute numbers for the method breakdown as fact on stage.** If you show the breakdown, add the conditions: "on that day, with that query".
