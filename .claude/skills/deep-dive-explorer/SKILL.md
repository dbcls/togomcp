---
name: deep-dive-explorer
description: >
  Systematically explore a biological or chemical entity, mechanism, or finding across TogoMCP RDF databases.
  Use this skill whenever you have a starting point — a protein name, compound, pathway, disease, or a partial
  finding — and want to map what's known, fill gaps, and surface the next level of understanding.
  Trigger when the user says things like: "tell me more about X", "what's the mechanism behind Y?",
  "go deeper on this finding", "what other databases have info on this?", "I found X is associated with Y,
  what else should I look into?", "深掘りして", "もっと詳しく調べて", or when a previous TogoMCP exploration
  surfaces a promising lead that deserves follow-up. Works without a research paper — any biological entity,
  protein, compound, pathway, or incomplete finding can be the starting seed.
---

# Deep-Dive Explorer: Cross-Database Biological Investigation

Turn a single finding or entity into a richly connected picture by systematically exploring what TogoMCP's RDF
databases know — and explicitly surfacing what they don't.

## Read First

Read the TogoMCP Usage Guide before calling any tools:
→ Call `TogoMCP:TogoMCP_Usage_Guide` as your first tool call. The v3 guide's SPARQL discipline and tool
  budget rules apply fully here.

Key rules to keep in mind:
- `list_databases()` is always the first tool call after the Usage Guide
- Max 2 consecutive `run_sparql` calls — then pivot
- Target 6–15 total tool calls across the whole exploration
- Always call `get_MIE_file()` before writing SPARQL for any database

---

## The Core Idea

Research-article analysis validates claims in a paper. This skill does something different: it starts from
**any seed** (an entity, a mechanism, a partial finding, a question) and explores outward. The goal is not
exhaustive validation but *productive discovery* — finding the most informative next facts and honestly
acknowledging what remains unknown.

After each significant discovery, briefly note:
1. **What this confirms or reveals**
2. **What new questions it raises**
3. **Whether to pursue one now or save it for the Next Steps summary**

This "concierge loop" is what makes exploration feel guided rather than mechanical.

---

## PHASE 1: Seed Definition (no tools yet)

Before touching any tool, answer these questions in writing:

**1. What is the seed?**
Name the entity, finding, or question precisely. Examples:
- Entity: "OmpK35 (outer membrane porin in *Klebsiella pneumoniae*)"
- Finding: "Loss of OmpK35 is associated with carbapenem resistance"
- Question: "How does AMPK mediate metformin's effect on glucose metabolism?"

**2. What do we already know?**
List 3–5 facts from the current conversation or general knowledge. This prevents re-discovering things
already established and focuses tool calls on genuine unknowns.

**3. What don't we know that we want to know?**
Write 3–5 specific unknowns. These drive the exploration plan. Examples:
- "Which specific carbapenem resistance mechanisms involve OmpK35 structurally?"
- "Are there known OmpK35 mutations in clinical isolates, and what is their effect?"
- "What pathways link porin loss to beta-lactam efflux upregulation?"

**4. Entity map**
List the entity types present and map each to the most likely database:

| Entity | Type | Primary DB | Supporting DB |
|--------|------|-----------|---------------|
| OmpK35 | Protein/Outer membrane porin | UniProt | PDB |
| Carbapenem | Drug/Beta-lactam | ChEMBL | ChEBI, PubChem |
| Carbapenem resistance | Disease mechanism | MeSH | Reactome, ChEMBL |
| Beta-lactam hydrolysis | Reaction | Rhea | ChEBI |
| Outer membrane permeability | Pathway/Process | Reactome | GO |

**5. Cross-database bridges needed?**
If the unknowns span multiple databases on different endpoints, plan the bridge now:
- UniProt (sib) ↔ ChEMBL (ebi) → needs `togoid_convertId`
- UniProt → PDB structure → needs `togoid_convertId` via `uniprot → pdb` route

Write your bridge plan before calling any tool.

---

## PHASE 2: Anchor ID Acquisition

Goal: find the stable database IDs for your seed entities before running SPARQL. Search tools are faster,
more reliable, and count against your budget less than SPARQL retries.

**Standard sequence:**
```
list_databases()                          ← always first
search_uniprot_entity(query)              ← for proteins
search_chembl_target/molecule(query)      ← for drug targets / compounds
get_pubchem_compound_id(query)            ← for compounds
search_reactome_entity(query)             ← for pathways
search_rhea_entity(query)                 ← for reactions
search_mesh_descriptor(query)             ← for diseases / anatomy
OLS4:searchClasses(ontologyId, query)     ← for GO / ChEBI terms
ncbi_esearch(database, term)              ← for genes / variants / literature
```

For each entity found, record:
```
=== ANCHOR IDs ===
UniProt: [ID] ([protein name], [organism])   ← [planned queries: structure, variants, GO terms]
ChEMBL: [ID] ([compound/target name])        ← [planned queries: activity data, targets]
PDB: [IDs]                                   ← [planned queries: structure features]
...
```

After each search result, apply the concierge loop:
> *"Found [X]. This [confirms/opens up] [Y]. New question: [Z]. Will I pursue Z now or save it?"*

If search tools answer your unknowns directly (happens often for verification questions), you may not need
SPARQL at all. Stop here and synthesize if so.

---

## PHASE 3: Targeted SPARQL Exploration

Run SPARQL queries only where search tools left genuine gaps. Follow v3 discipline strictly.

**Before each query:**
- Read `get_MIE_file(database)` if you haven't yet for this database
- Write the simplest query that answers one specific unknown
- Start with `LIMIT 10` to verify structure

**After each result, apply the concierge loop:**
> *Found: [specific data — IDs, EC numbers, GO terms, pathway names]*
> *This reveals: [mechanistic or structural insight]*
> *New question raised: [specific follow-up]*
> *Decision: pursue now / save for Next Steps*

**Cross-database chain (attempt at least one)**
If the unknowns span multiple databases, build one chain. Example for OmpK35:
```
UniProt (protein function, GO terms)
  → togoid_convertId uniprot→pdb
  → PDB (structural context of porin channel)
  → ChEMBL (carbapenem activity against related targets)
  → Reactome (beta-lactam transport or resistance pathway)
```

The chain doesn't have to be long — even a two-database connection that wasn't established before is
valuable.

**SPARQL budget: 1–4 total queries.** If you find yourself wanting a 5th SPARQL call, ask whether
synthesizing from what you have would serve the user better. It usually will.

---

## PHASE 4: Synthesis and Next Steps

### What we learned

For each original unknown from Phase 1, write one paragraph summarizing:
- What the databases confirmed (cite IDs and data points, not just text from search results)
- What was partially confirmed or ambiguous
- What the databases don't currently contain (gaps are findings too)

### Cross-database picture

Write 2–4 sentences connecting the findings across databases. This is the "concierge synthesis" — the
thing a knowledgeable advisor would say, not just a list of facts.

Example:
> "UniProt confirms OmpK35 (P77526) is an outer membrane porin with GO:0046930 (pore complex) annotation.
> PDB has no direct OmpK35 structure, but the homologous OmpC (1HXT) shows how channel narrowing could
> reduce carbapenem influx. ChEMBL records no direct OmpK35-carbapenem binding activity, consistent with
> the resistance being permeability-mediated rather than target-mediated."

### What we still don't know

Be explicit about the genuine unknowns that remain. These are as valuable as the findings — they tell the
user where the frontier is.

### Next Steps (prioritized)

List 3–5 specific, actionable follow-up explorations, ranked by likely yield:

```
NEXT STEPS (ranked by value)

1. [Most valuable] Query: [specific tool + query string]
   Why: [one sentence rationale]

2. [Second] Query: [specific tool + query string]
   Why: [one sentence rationale]

3. [Third] Query: [specific tool + query string]
   Why: [one sentence rationale]
```

This is the "concierge handoff" — the user can pick up any of these threads in the next conversation turn.

---

## Common Pitfalls in Exploration Mode

**Pitfall 1: Exploring too broadly**
It's tempting to query every database once you have an ID. Resist this. Pick 2–3 databases most likely to
address the specific unknowns. Breadth without focus wastes tool budget.

**Pitfall 2: Treating "no results" as failure**
If a database returns nothing for your entity, that's a real finding — it means the entity isn't there or
isn't annotated yet. Report it as a gap in the synthesis.

**Pitfall 3: Forgetting the concierge loop**
The value of this skill is not just facts collected but *questions surfaced*. After each tool call, spend
one sentence asking: "What does this make me want to know next?" Record that question even if you don't
pursue it immediately.

**Pitfall 4: Skipping SPARQL discipline**
Exploration mode does not relax the SPARQL rules. Max 2 consecutive SPARQL calls still applies.
The v3 tool budget still applies. The urge to "just run one more query" is exactly when discipline matters.

**Pitfall 5: Vague Next Steps**
"Look into this more in other databases" is not a useful Next Step. Each Next Step should name the tool,
the query string, and the specific unknown it addresses.

---

## Quick Reference: Entity → Database Mapping

| You have... | Start here | Then explore |
|-------------|-----------|--------------|
| Protein name / ID | `search_uniprot_entity` | PDB (structure), ChEMBL (drug targets), Reactome (pathways) |
| Drug / compound name | `search_chembl_molecule` + `get_pubchem_compound_id` | ChEBI (structure), Rhea (reactions), UniProt (targets) |
| Disease name | `search_mesh_descriptor` | ChEMBL (drug–disease), Reactome (disease pathways), NCBI |
| Pathway name | `search_reactome_entity` | UniProt (participants), GO (process), Rhea (reactions) |
| Reaction / enzyme | `search_rhea_entity` | UniProt (EC number), ChEBI (substrates), Reactome (pathway context) |
| Gene name / ID | `ncbi_esearch(database="gene")` | UniProt (protein), Ensembl, ClinVar (variants) |
| Phenotype / GO term | `OLS4:searchClasses` | UniProt (annotated proteins), Reactome (processes) |

---

## Exploration Depth Guide

Choose a depth level based on the user's intent:

| Depth | Tool calls | SPARQL | Output |
|-------|-----------|--------|--------|
| **Quick scan** | 4–6 | 0–1 | Key IDs + 2–3 facts + 3 Next Steps |
| **Standard** (default) | 8–12 | 1–3 | Full synthesis + cross-DB chain + Next Steps |
| **Thorough** | 12–18 | 3–4 | All entity types covered, multiple chains, gap analysis |

When in doubt, start at Standard depth. If the user says "go deeper" or "tell me everything," shift to Thorough.
