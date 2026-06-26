---
name: prism
description: >
  PRISM finds entities (genes, proteins, compounds) at the INTERSECTION of two or more property sets on RDF
  knowledge graphs via TogoMCP — e.g. "genes common to disease X and druggable pathway Y", "targets both linked
  to phenotype P and modulated by existing drugs". Use whenever the user asks a set-intersection / overlap /
  "what is common to" / "is there a gene or target that is both ... and ..." question, a drug-repurposing or
  target-identification question, or anything combining a DISEASE/PHENOTYPE axis with a FUNCTION axis and/or a
  DRUGGABILITY axis. Trigger even on "shared genes between A and B", "druggable targets for disease X", or
  "intersection of ... and ...". PRISM makes each axis a reproducible predicate expanded over the ontology
  hierarchy, triangulated across evidence sources, and intersected by stable IDs with a provenance ledger. If
  you catch yourself listing candidate genes from memory, STOP and use it.
---

# PRISM — Predicate-defined, Reproducible, Identifier-bridged, Set-intersection Mining

PRISM answers "what entities are common to property set A and property set B?" on linked open data **without relying on recall**. A remembered list of candidates is a *hypothesis*, not a set. PRISM replaces hand-seeded lists with reproducible predicate chains, then triangulates weak axes across multiple evidence sources so the intersection does not silently collapse.

## Before you begin

- Call `TogoMCP_Usage_Guide` (or `TogoMCP-Test:TogoMCP_Usage_Guide`) **first**, and run its GATE 0 classification.
- Read `references/sparql-templates.md` — parameterized queries for every phase (hierarchy expansion, GO→UniProt, PubTator co-occurrence, ClinVar gene-anchored significance, ChEMBL targets, Reactome membership, TogoID bridging).
- Read `references/worked-example.md` for a full end-to-end run with a filled-in provenance ledger.

## When to use vs. not

Use PRISM when the question is an **intersection of properties** ("both A and B", "common to", "druggable target for disease", "shared genes", "overlap between"). Do **not** invoke the full machinery for a single-fact lookup ("what is the UniProt ID of CETP?") or a single-axis enumeration ("list genes in pathway X") — those are ordinary TogoMCP queries. The tell for PRISM is two or more *constraints of different kinds* that must be satisfied simultaneously.

---

## The PRISM mnemonic → five phases

```
P — Pose as sets & Predicate-define each axis   (kill recall)
R — Reach the full hierarchy                     (transitive closure)
I — Integrate multi-source evidence              (triangulate weak axes)
S — Stitch by stable ID & intersect              (set algebra)
M — Measure actionability & audit provenance     (stratify + ledger)
```

Do the phases in order. The two most-skipped, most-damaging-to-skip steps are **R** (hierarchy expansion) and **I** (triangulation). Skipping R silently under-covers a set; skipping I lets a single biased source collapse the intersection.

---

## PHASE P — Pose as sets & predicate-define each axis

1. **Write the question as explicit set algebra.** Name the operation (∩, ∪, \) and each operand. Example: `Answer = A ∩ B` where `A = {disease-associated} ∩ {function f}` and `B = {in druggable pathway}`.

2. **Name each set by the PREDICATE that defines it, not by example members.** "Lipid-transport genes" is not a definition; `human reviewed UniProt proteins where up:classifiedWith ∈ descendants(GO:0006869)` is. If you cannot yet name the predicate, that axis is still a hypothesis — resolve it before proceeding.

3. **De-recall.** Any candidate list you produced from memory is a *seed for sanity-checking*, never the set itself. The deliverable set must be derivable from databases by someone who shares none of your priors. Treat "genes I know are associated with X" as a red flag, not an answer.

4. **Map each axis to a database and an anchoring entity:**

| Axis type | Typical source(s) | Anchor |
|-----------|-------------------|--------|
| Molecular function | GO (term + descendants) → UniProt `up:classifiedWith` | GO term IRI |
| Pathway membership | Reactome (BioPAX) | pathway IRI / displayName |
| Disease / phenotype association | PubTator (literature), NCBI Gene (curation), ClinVar (variant), GWAS Catalog (external) | MeSH / MedGen / disease IRI |
| Druggability | ChEMBL (target + activity) | target/gene name |
| Clinical actionability | ClinVar germline classification | gene IRI |

---

## PHASE R — Reach the full hierarchy

Ontology- and keyword-defined axes are **DAGs**. Querying a single term or a single controlled-vocabulary keyword silently misses members annotated only to narrower terms.

- **Always expand to the transitive closure.** For a GO/MONDO/ChEBI axis, fetch descendants with `?term rdfs:subClassOf+ <ROOT>` against the ontology database (e.g. `go`), then feed the resulting term IRIs as `VALUES` into the annotation database (UniProt `up:classifiedWith`, etc.). See `references/sparql-templates.md → Hierarchy expansion`.
- **Do not trust a single UniProt keyword** (`up:classifiedWith keywords:NNN`) as a complete functional axis — it is one node in a keyword DAG. Prefer the GO-descendant route, or union the relevant child keywords.
- **Sanity check the expansion** by confirming that a few entities you *expect* (and a few you'd expect to be *absent*) land on the correct side. This is the one place where recall is useful — as a test oracle, not as the set.

> Lesson baked in: a `keyword:Lipid transport`-only axis dropped ABCA1 and ABCA4 (annotated to child terms `cholesterol efflux`, `phospholipid translocation`). Switching to `GO:0006869 + subClassOf+` recovered them. Under-coverage from skipping R is *silent* — you get a plausible-looking but incomplete set.

---

## PHASE I — Integrate multi-source evidence (triangulate weak axes)

Some axes are "hard" (a molecular function is what the annotation says). Others are "soft" — **disease association in particular is recorded differently by every source, each with a different bias.** A naive single-source intersection collapses.

**Define each soft axis as the UNION of bias-distinct sources, and record which source supports each member.**

| Source | Captures | Bias / blind spot |
|--------|----------|-------------------|
| PubTator co-occurrence | genes co-mentioned with the disease | **literature-volume bias** — buries GWAS-only loci with few papers |
| NCBI Gene curation (`esearch gene`) | curated/GeneRIF disease links | broad; surfaces GWAS loci; some non-causal mentions |
| ClinVar variant–condition | Mendelian / clinically-graded variants | **only Mendelian** — common-variant risk loci appear as "risk factor"/absent |
| GWAS Catalog (external, outside TogoMCP) | common-variant risk loci with effect sizes | not in TogoMCP — flag as external |

> Lesson baked in: for a disease intersection, PubTator alone kept only `{APOE, ABCA4}`; the curation axis additionally surfaced `CETP, ABCA1, LIPC, APOB, APOC1, SCARB1, ABCG1`; ClinVar pathogenicity flagged `ABCA4` alone (the others' pathogenic variants belong to *other* Mendelian disorders, not the target disease). Each axis was individually misleading; the union was correct. **Always tag provenance per member** so you can see which axis carried each gene.

---

## PHASE S — Stitch by stable ID & intersect

1. **Normalize every set to one stable identifier** (NCBI Gene ID or UniProt accession). Use `togoid_convertId` to bridge (e.g. UniProt ↔ ncbigene). UniProt RDF also carries the GeneID cross-reference directly (`rdfs:seeAlso` → `.../geneid/NNN`).
2. **Compute the intersection on IDs, not symbols** (symbols are ambiguous; `ABCA1` vs `ABCA4` differ by one character and are easy to confuse).
3. **Prefer SPARQL-side intersection** via `VALUES` of the smaller set; only fall back to reading two result sets and matching when federation is unavailable (SERVICE is disabled platform-wide on rdfportal — use sequential queries + `VALUES` bridging).

---

## PHASE M — Measure actionability & audit provenance

1. **Stratify the intersection by actionability**, not as a flat list:
   - Tier 1: directly actionable (e.g. ChEMBL target of an approved/late-stage drug).
   - Tier 2: on a shared druggable pathway (modulated indirectly).
   - Tier 3: mechanistically central but only investigational / no direct drug.
2. **Emit a provenance ledger** (required output). One row per member, columns = each axis + supporting source + verified/inferred. See the template in `references/worked-example.md`.
3. **Mark DB-verified vs inferred vs out-of-scope.** State plainly which claims came from a database query and which would need an external source (GWAS Catalog for effect sizes, ClinicalTrials.gov for approval/indication status).
4. **Re-ask "is this comprehensive?"** and name the residual gaps (unscanned pages, axes not yet triangulated, hierarchy levels not expanded).

---

## Operational discipline (query engineering)

These are not optional — they are what made the difference between answers and timeouts:

- **Anchor on the small set.** Put the smaller operand in `VALUES` as the inner anchor (e.g. gene-anchored, not disease-anchored). A disease scan joined against millions of variants times out; the same query gene-anchored returns in seconds.
- **Prefer single-graph queries.** Cross-graph joins invite namespace mismatches. Known trap: ClinVar stores MedGen refs as `http://ncbi.nlm.nih.gov/medgen/...` (no `www`) while MedGen entities use `http://www.ncbi.nlm.nih.gov/medgen/...` (with `www`). A direct join silently returns 0 rows — convert with `REPLACE(STR(?u), "://ncbi.nlm", "://www.ncbi.nlm")` (or the reverse).
- **On timeout: reconstruct, don't retry.** Re-anchor, drop a graph, add `LIMIT`, or split into two queries. Never resubmit the identical query.
- **Respect consecutive-SPARQL limits.** After 2 heavy SPARQL calls in a row, pivot to a non-SPARQL tool (`esearch`, an MIE read, OLS) before the next query.
- **Read the MIE before querying any database** you have not already characterized this session.
- **Soft filters can be empty for real reasons.** If a "pathogenic AND disease-named" filter returns nothing, that may be biology (the disease is a complex trait, not Mendelian), not a bug — but verify with a looser single-graph query before concluding.

---

## Anti-patterns (each one bit us; don't repeat them)

| Anti-pattern | Why it fails | Fix |
|--------------|--------------|-----|
| Seeding the set from memory | a recalled list is a hypothesis, biased and incomplete | Phase P: predicate-define |
| Single keyword / single GO term as a functional axis | DAG children are silently excluded | Phase R: `subClassOf+` |
| Single source for disease association | each source's bias collapses the intersection | Phase I: union bias-distinct sources |
| Intersecting on gene symbols | ambiguous; off-by-one-letter confusions | Phase S: intersect on stable IDs |
| Disease-anchored heavy join | scans millions of rows → timeout | anchor on the small set |
| Cross-graph join without namespace fix | `www`/no-`www` mismatch → 0 rows | convert namespaces or go single-graph |
| Flat result list | hides actionability and provenance | Phase M: stratify + ledger |

---

## Output template

```
## Answer (set-intersection)
<yes/no + the intersection, stratified into Tier 1/2/3>

## Provenance ledger
| member (ID) | function axis | disease axis (source) | druggability | actionability tier | verified? |

## Method (reproducible predicate chain)
function: <ontology root + subClassOf+ → annotation DB>
disease : <union of sources, per-member tags>
intersect: <stable ID>

## Honest limits
<DB-verified vs inferred; out-of-scope external sources; residual comprehensiveness gaps>
```
