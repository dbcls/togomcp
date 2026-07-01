# Research Article Analysis Workflow using TogoMCP RDF Databases

**Analyze research articles systematically using TogoMCP RDF databases.**

---

## MANDATORY WORKFLOW CHECKLIST

**Before starting, acknowledge you will follow ALL these steps:**
- [ ] ✅ PHASE 1: Extract key elements
- [ ] ✅ PHASE 2A: Select databases systematically (apply ALL 5 mandatory rules)
- [ ] ✅ PHASE 2B: Read ALL MIE files for selected databases
- [ ] ✅ PHASE 2C: Run keyword searches
- [ ] ✅ PHASE 2D: **Execute complex SPARQL queries FOR EACH DATABASE** (NON-NEGOTIABLE)
- [ ] ✅ PHASE 3: Reconstruct the argument (3A DB-backed logical flow) + triage gaps (3B)
- [ ] ✅ PHASE 4: Score flow soundness + record gap disposition
- [ ] ✅ FINAL SUMMARY: Main claim / Conclusion / DB-backed flow / Gap analysis

**⚠️ CRITICAL: Completing Phase 2D for ALL selected databases is NON-NEGOTIABLE. Skipping ANY database invalidates the entire analysis.**

---

## PHASE 1: EXTRACT KEY ELEMENTS

**Quick extraction (5 minutes). Items 1-3 feed the Final Summary directly — capture them in the article's own terms:**

1. **Main Claim**: One sentence — the single assertion the paper argues for (not a topic, not a question; the thing that would be *false* if the paper is wrong).
2. **Central Conclusion**: 1-3 sentences — what the authors say follows from their results.
3. **Argument skeleton (results → conclusion)**: list the paper's own inferential steps in order. This is the spine you will DB-back in Phase 3A.
   - **Experimental observation(s)**: what was measured/observed — the paper's NEW data. These will NOT be in the databases; do not expect to validate them.
   - **Inferential step(s)**: each "we observed X, therefore Y" link.
   - **Background premise per step**: the already-known biology each inference relies on. THIS is what the databases can confirm or refute.
4. **Key Entities**:
   - Metabolites/Chemicals: [list with structures/formulas if mentioned]
   - Proteins/Genes: [list with IDs if mentioned]
   - Reactions: [list transformations]
   - Pathways: [list pathway names]
   - Processes: [list biological processes]
   - Diseases: [list if applicable]

---

## PHASE 2A: SELECT DATABASES SYSTEMATICALLY ⚠️ MANDATORY

### Five Mandatory Selection Rules (Apply ALL):

```
RULE 1: Metabolite/Chemical Rule
IF article mentions ANY chemical/metabolite/compound/drug
→ ChEBI is MANDATORY

RULE 2: Reaction Rule  
IF article describes ANY enzymatic/chemical transformation
→ Rhea is MANDATORY

RULE 3: Pathway Rule
IF article mentions ANY pathway/metabolism/biosynthesis
→ Reactome is MANDATORY

RULE 4: Protein Rule
IF article mentions ANY protein/enzyme/receptor/gene
→ UniProt is MANDATORY

RULE 5: Process Rule
IF article discusses ANY biological process/function
→ GO is MANDATORY
```

### Quick Database Mapping:

| Entity Type | Mandatory Databases | Supporting Databases |
|-------------|-------------------|---------------------|
| Chemicals/Metabolites | ChEBI, Rhea, Reactome | PubChem, ChEMBL |
| Proteins/Enzymes | UniProt, GO | PDB, ChEMBL, Reactome |
| Reactions | Rhea, UniProt | GO |
| Pathways | Reactome, GO | UniProt, Rhea, ChEBI |
| Diseases | MONDO, MeSH | ClinVar, MedGen |
| Genes/Variants | NCBI Gene | Ensembl, ClinVar, UniProt |

### Selection Documentation Template:

```
=== DATABASE SELECTION ===

Entity Summary:
- Metabolites: [list]
- Proteins: [list]  
- Reactions: [list]
- Pathways: [list]
- Processes: [list]

Rules Applied:
☑ Rule 1 (Chemical): [YES/NO] → ChEBI [SELECTED/NOT NEEDED]
☑ Rule 2 (Reaction): [YES/NO] → Rhea [SELECTED/NOT NEEDED]
☑ Rule 3 (Pathway): [YES/NO] → Reactome [SELECTED/NOT NEEDED]
☑ Rule 4 (Protein): [YES/NO] → UniProt [SELECTED/NOT NEEDED]
☑ Rule 5 (Process): [YES/NO] → GO [SELECTED/NOT NEEDED]

Selected Databases (Priority Order):
TIER 1: [list with brief reason for each]
TIER 2: [list]
TIER 3: [list]
```

**⚠️ CHECKPOINT: Did you apply ALL 5 rules? If NO to any rule, STOP and reconsider.**

---

## PHASE 2B: STUDY MIE FILES ⚠️ MANDATORY FOR ALL TIER 1 DATABASES

**For EACH selected Tier 1 database, run `get_MIE_file(database)` and read:**

### Critical MIE Insights to Extract:

**ChEBI:**
- ✅ Two namespaces: `chebi/` (data: formula, mass) vs `chebi#` (relationships)
- ✅ Filter: `STRSTARTS(STR(?entity), "http://purl.obolibrary.org/obo/CHEBI_")`
- ✅ Search: Use `bif:contains` for keywords
- ✅ Properties: formula, mass, smiles, inchikey, cross-references

**Rhea:**
- ✅ Query pattern: `?reaction rdfs:subClassOf rhea:Reaction`
- ✅ Search: `bif:contains` on `rhea:equation`
- ✅ Always add `LIMIT` to exploratory queries
- ✅ Properties: equation, status, ec, participants

**Reactome:**
- ✅ ALWAYS use: `FROM <http://rdf.ebi.ac.uk/dataset/reactome>`
- ✅ String comparisons: Use `^^xsd:string` for `bp:db`
- ✅ Search: `bif:contains` on `bp:displayName`
- ✅ Start from specific entities, not unbounded variables

**UniProt:**
- ✅ CRITICAL: Always filter `up:reviewed 1` (99.8% reduction)
- ✅ NO property paths with `bif:contains` - split them
- ✅ Organism: `up:organism <http://purl.uniprot.org/taxonomy/####>`
- ✅ Properties: mnemonic, recommendedName, enzyme, classifiedWith

**GO:**
- ✅ ALWAYS use: `FROM <http://rdfportal.org/ontology/go>`
- ✅ ALWAYS use: `DISTINCT` (prevents duplicates)
- ✅ Filter: `STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_")`
- ✅ Namespace: Use `STR(?namespace)` for comparisons

**⚠️ CHECKPOINT: Have you read MIE files for ALL Tier 1 databases? If NO, STOP.**

---

## PHASE 2C: KEYWORD SEARCHES (Initial Discovery)

**⚠️ CRITICAL RULE: Every ID found in Phase 2C MUST be used in Phase 2D SPARQL queries. NO EXCEPTIONS.**

### Keyword Search Strategy:

**For each key entity, use appropriate search tool:**

```
Chemicals:     OLS4:searchClasses(ontologyId="chebi", query="...")
               get_pubchem_compound_id(compound_name)
               search_chembl_molecule(query)

Proteins:      search_uniprot_entity(query)
               search_chembl_target(query)
               search_pdb_entity(db="pdb", query)

Reactions:     search_rhea_entity(query)

Pathways:      search_reactome_entity(query)

Processes:     OLS4:searchClasses(ontologyId="go", query="...")

Genes:         ncbi_esearch(database="gene", query)

Diseases:      search_mesh_entity(query)
```

### ID Tracking Template (MANDATORY):

**Create a tracking table for EVERY ID found:**

```
=== PHASE 2C: KEYWORD SEARCH RESULTS (with SPARQL Status Tracking) ===

ChEBI IDs Found:
- CHEBI:16359 (cholic acid) → ☐ SPARQL Query Pending
- CHEBI:28865 (taurocholic acid) → ☐ SPARQL Query Pending

UniProt IDs Found:
- P05231 (IL-6) → ☐ SPARQL Query Pending
- P01375 (TNFα) → ☐ SPARQL Query Pending  
- Q969Q1 (MuRF1) → ☐ SPARQL Query Pending
- Q969P5 (Atrogin-1) → ☐ SPARQL Query Pending

Rhea IDs Found:
- RHEA:47100 (conjugation) → ☐ SPARQL Query Pending
- RHEA:47108 (direct reaction) → ☐ SPARQL Query Pending

Reactome IDs Found:
- R-HSA-194068 (bile acid metabolism) → ☐ SPARQL Query Pending
- R-HSA-444843 (GPBAR1 complex) → ☐ SPARQL Query Pending

GO IDs Found:
- GO:0006954 (inflammatory response) → ☐ SPARQL Query Pending
- GO:0014732 (skeletal muscle atrophy) → ☐ SPARQL Query Pending

TOTAL IDs FOUND: 10
SPARQL QUERIES REQUIRED: 10 (minimum)
```

**After documenting each ID, mark it "☐ SPARQL Query Pending"**

**In Phase 2D, check off each ID as you complete its SPARQL query: "☑ SPARQL Completed"**

**⚠️ CHECKPOINT: Count your "☐ Pending" IDs. ALL must become "☑ Completed" by end of Phase 2D.**

---

## PHASE 2D: COMPLEX SPARQL QUERIES ⚠️ NON-NEGOTIABLE - EXECUTE FOR EVERY DATABASE

**⚠️ CRITICAL RULE 1: For EVERY database selected in Phase 2A, you MUST execute at least 1-2 complex SPARQL queries. NO EXCEPTIONS.**

**⚠️ CRITICAL RULE 2: For EVERY ID found in Phase 2C keyword searches, you MUST execute at least 1 SPARQL query using that specific ID. NO EXCEPTIONS.**

### The Keyword Search → SPARQL Query Pipeline:

**MANDATORY WORKFLOW FOR EACH ID:**

```
Phase 2C: Keyword Search → Found ID: Q969Q1 (MuRF1)
         Mark: ☐ SPARQL Query Pending
         ↓
Phase 2D: MUST execute SPARQL with Q969Q1:
         PREFIX up: <http://purl.uniprot.org/core/>
         PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
         SELECT ?mnemonic ?fullName ?ecNumber ?goTerm
         WHERE { uniprot:Q969Q1 up:reviewed 1 ; ... }
         ↓
         SPARQL returns: EC 2.3.2.27, GO:0061630, GO:0014732
         Mark: ☑ SPARQL Completed
         ↓
Phase 3: Cite SPARQL results (not search text):
         "MuRF1 (Q969Q1) - SPARQL confirmed EC 2.3.2.27 (E3 ubiquitin ligase),
         GO:0061630 (ubiquitin ligase activity), GO:0014732 (skeletal muscle atrophy)"
```

**Common Mistake to Avoid:**

❌ **WRONG (citing search result text):**
```
"MuRF1 (Q969Q1) is an E3 ubiquitin ligase" 
← Based on search_uniprot_entity() result text only
← No SPARQL query executed
← Cannot validate EC number or GO terms
```

✅ **CORRECT (citing SPARQL query results):**
```
"MuRF1 (Q969Q1) is an E3 ubiquitin ligase:
 - EC 2.3.2.27 (from SPARQL query)
 - GO:0061630 (ubiquitin protein ligase activity, from SPARQL)
 - GO:0014732 (skeletal muscle atrophy, from SPARQL)"
← Based on actual SPARQL query execution
← Complete functional validation
```

### Database-Specific Query Requirements:

---

### IF ChEBI WAS SELECTED → MANDATORY ChEBI SPARQL QUERIES

**MINIMUM REQUIRED: 2 queries**

#### ChEBI Query Type 1: Molecular Structure Validation
**Purpose:** Get exact formulas, masses, SMILES, InChIKeys for chemical identity proof

**Template:**
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?label ?formula ?mass ?smiles ?inchikey
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  obo:CHEBI_#### rdfs:label ?label ;
                 chebi:formula ?formula ;
                 chebi:mass ?mass .
  OPTIONAL { obo:CHEBI_#### chebi:smiles ?smiles }
  OPTIONAL { obo:CHEBI_#### chebi:inchikey ?inchikey }
}
```

**What this validates:** Exact molecular identity with stereochemistry, not just name matching

#### ChEBI Query Type 2: Chemical Hierarchy/Classification
**Purpose:** Get parent classes, conjugate forms, chemical relationships

**Template:**
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?label ?parent ?parentLabel
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  obo:CHEBI_#### rdfs:label ?label ;
                 rdfs:subClassOf ?parent .
  ?parent rdfs:label ?parentLabel .
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/CHEBI_"))
}
LIMIT 20
```

**What this validates:** Chemical classification (e.g., bile acid → 5β-cholanic acid → steroid)

**✅ VERIFICATION**: Did you execute BOTH ChEBI query types? If NO, analysis is INCOMPLETE.

---

### IF Rhea WAS SELECTED → MANDATORY Rhea SPARQL QUERIES

**MINIMUM REQUIRED: 2 queries**

#### Rhea Query Type 1: Reaction Equation with Stoichiometry
**Purpose:** Get exact chemical transformation equations with cofactors

**Template:**
```sparql
PREFIX rhea: <http://rdf.rhea-db.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?reaction ?equation ?status ?ec
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:status ?status .
  FILTER(CONTAINS(LCASE(?equation), "substrate_keyword"))
  OPTIONAL { ?reaction rhea:ec ?ec }
}
LIMIT 10
```

**What this validates:** Exact stoichiometric transformations (A + B → C + D), not just "enzyme converts X to Y"

#### Rhea Query Type 2: Reaction Participants with ChEBI Links
**Purpose:** Link reactions to exact chemical structures

**Template:**
```sparql
PREFIX rhea: <http://rdf.rhea-db.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?reaction ?equation ?side ?compound ?chebi
WHERE {
  VALUES ?reaction { <http://rdf.rhea-db.org/####> }
  ?reaction rhea:equation ?equation .
  OPTIONAL { 
    ?reaction rhea:side ?side .
    ?side rhea:contains ?participant .
    ?participant rhea:compound ?compound .
    ?compound rhea:chebi ?chebi .
  }
}
LIMIT 30
```

**What this validates:** Complete reaction participants with ChEBI cross-references

**✅ VERIFICATION**: Did you execute BOTH Rhea query types? If NO, analysis is INCOMPLETE.

---

### IF Reactome WAS SELECTED → MANDATORY Reactome SPARQL QUERIES

**MINIMUM REQUIRED: 2 queries**

#### Reactome Query Type 1: Pathway Structure
**Purpose:** Get complete pathway hierarchy with sub-components

**Template:**
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT DISTINCT ?pathway ?displayName ?component ?componentName
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:displayName ?displayName .
  FILTER(CONTAINS(LCASE(?displayName), "pathway_keyword"))
  OPTIONAL {
    ?pathway bp:pathwayComponent ?component .
    ?component bp:displayName ?componentName .
  }
}
LIMIT 20
```

**What this validates:** Complete pathway architecture (synthesis, degradation, transport sub-pathways)

#### Reactome Query Type 2: Protein-Ligand Complexes
**Purpose:** Validate specific protein-metabolite interactions

**Template:**
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT DISTINCT ?complex ?displayName ?component ?componentName
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?complex a bp:Complex ;
           bp:displayName ?displayName .
  FILTER(CONTAINS(?displayName, "protein_name"))
  OPTIONAL {
    ?complex bp:component ?component .
    ?component bp:displayName ?componentName .
  }
}
LIMIT 15
```

**What this validates:** Specific protein-ligand binding (e.g., "GPBAR1:Bile acids" complex)

**✅ VERIFICATION**: Did you execute BOTH Reactome query types? If NO, analysis is INCOMPLETE.

---

### IF UniProt WAS SELECTED → MANDATORY UniProt SPARQL QUERIES

**MINIMUM REQUIRED: 2 queries**

#### UniProt Query Type 1: Protein Function Annotations
**Purpose:** Get EC numbers, GO terms, recommended names

**Template:**
```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT ?mnemonic ?fullName ?ecNumber ?goTerm
WHERE {
  uniprot:P##### up:reviewed 1 ;
                 up:mnemonic ?mnemonic ;
                 up:recommendedName ?name ;
                 up:classifiedWith ?goTerm .
  ?name up:fullName ?fullName .
  OPTIONAL { uniprot:P##### up:enzyme ?ecNumber }
  FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 50
```

**What this validates:** Complete protein functional annotations (cytokine activity, receptor binding, etc.)

#### UniProt Query Type 2: Protein Localization and Components
**Purpose:** Get cellular component GO terms, subcellular localization

**Template:**
```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?goTerm ?goLabel
WHERE {
  uniprot:P##### up:reviewed 1 ;
                 up:classifiedWith ?goTerm .
  ?goTerm rdfs:label ?goLabel .
  FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
}
```

**What this validates:** Protein location (membrane, extracellular, etc.)

**✅ VERIFICATION**: Did you execute BOTH UniProt query types? If NO, analysis is INCOMPLETE.

---

### IF GO WAS SELECTED → MANDATORY GO SPARQL QUERIES

**MINIMUM REQUIRED: 2 queries**

#### GO Query Type 1: Process/Function Definitions
**Purpose:** Get exact definitions of claimed biological processes

**Template:**
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?term ?label ?definition
FROM <http://rdfportal.org/ontology/go>
WHERE {
  VALUES ?term { obo:GO_####### obo:GO_####### }
  ?term rdfs:label ?label .
  OPTIONAL { ?term obo:IAO_0000115 ?definition }
}
```

**What this validates:** Precise definitions matching article claims

#### GO Query Type 2: Term Hierarchy
**Purpose:** Get parent/child relationships for processes

**Template:**
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?term ?label ?parent ?parentLabel
FROM <http://rdfportal.org/ontology/go>
WHERE {
  obo:GO_####### rdfs:label ?label ;
                 rdfs:subClassOf ?parent .
  ?parent rdfs:label ?parentLabel .
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 20
```

**What this validates:** Process hierarchy (e.g., skeletal muscle atrophy → muscle atrophy → muscle adaptation)

**✅ VERIFICATION**: Did you execute BOTH GO query types? If NO, analysis is INCOMPLETE.

---

### MANDATORY CROSS-DATABASE EVIDENCE CHAIN

**REQUIREMENT: Build at least ONE complete evidence chain linking 3+ databases**

**Example Chain Pattern:**
```
ChEBI (metabolite structure) 
  → Rhea (reaction equation) 
    → UniProt (enzyme with EC number) 
      → Reactome (pathway) 
        → GO (biological process)
```

**Execution Steps:**
1. Get ChEBI ID and molecular formula for key metabolite
2. Find Rhea reaction with that ChEBI ID as substrate
3. Extract EC number from Rhea reaction
4. Find UniProt protein with that EC number
5. Find Reactome pathway containing that protein
6. Get GO biological process term for that pathway

**Documentation:**
```
EVIDENCE CHAIN 1: [Claim being validated]
Step 1 (ChEBI): CHEBI:##### - Formula: C24H40O5, Mass: 408.57 Da
Step 2 (Rhea): RHEA:##### - Equation: A + B = C + D
Step 3 (UniProt): P##### - EC 2.3.2.27, "E3 ubiquitin ligase"
Step 4 (Reactome): R-HSA-##### - "Protein degradation pathway"
Step 5 (GO): GO:####### - "skeletal muscle atrophy"
```

**✅ VERIFICATION**: Did you build at least ONE complete cross-database chain? If NO, analysis is INCOMPLETE.

---

## PHASE 2D COMPLETION CHECKLIST - MANDATORY VERIFICATION

**Before proceeding to Phase 3, verify ALL selected databases were queried:**

### Database Query Status:

- [ ] ✅ **ChEBI SELECTED?** → If YES: Executed 2+ SPARQL queries (structure + hierarchy)
- [ ] ✅ **Rhea SELECTED?** → If YES: Executed 2+ SPARQL queries (equations + participants)
- [ ] ✅ **Reactome SELECTED?** → If YES: Executed 2+ SPARQL queries (pathways + complexes)
- [ ] ✅ **UniProt SELECTED?** → If YES: Executed 2+ SPARQL queries (function + localization)
- [ ] ✅ **GO SELECTED?** → If YES: Executed 2+ SPARQL queries (definitions + hierarchy)
- [ ] ✅ **Cross-Database Chain?** → Built at least 1 complete evidence chain (3+ databases)

### Evidence Documentation Status:

- [ ] ✅ Documented exact formulas and masses (if ChEBI queried)
- [ ] ✅ Documented exact reaction equations (if Rhea queried)
- [ ] ✅ Documented complete pathway structures (if Reactome queried)
- [ ] ✅ Documented GO term definitions (if GO queried)
- [ ] ✅ Documented EC numbers and annotations (if UniProt queried)

**⚠️ STOP: If ANY checkbox above is unchecked, GO BACK and complete the missing queries.**

**⚠️ DO NOT PROCEED to Phase 3 until ALL queries are complete.**

---

## PHASE 3: EVIDENCE SYNTHESIS — RECONSTRUCT THE ARGUMENT, THEN TRIAGE THE GAPS

Phase 2D validated entities. Phase 3 assembles them into the paper's *argument* and isolates what the databases cannot account for. Two products: **3A** the DB-backed logical flow, **3B** the triaged gap analysis. Do NOT skip 3A — a pile of validated entities is not an argument.

### 3A. DB-Backed Logical Flow (results → conclusion)

Take the argument skeleton from Phase 1 and annotate each step with the SPARQL evidence for its *background premise*. Keep the paper's OWN observations separate from the DB-backed premises — the observations are the new data (not in the DBs); the premises are what the DBs can confirm.

**Template — one row per inferential step:**
```
STEP n: [paper's observation]  ──→  [paper's inference]
  Background premise (already-known biology the inference relies on):
    [statement]
  DB evidence for the premise:
    [ChEBI/Rhea/UniProt/Reactome/GO ID + exact SPARQL result: formula / equation / EC / GO definition]
  Premise status: ☑ DB-CONFIRMED | ⚠ DB-PARTIAL | ✗ DB-ABSENT | ✗ DB-CONTRADICTS
```

A chain of ☑ DB-CONFIRMED premises beneath the paper's observations = a logically sound, evidence-backed flow from results to conclusion. Any ⚠/✗ premise is a point where the flow depends on something the databases do not (yet) support — carry it to 3B. The cross-database evidence chain (ChEBI→Rhea→UniProt→Reactome→GO) is *supporting* biochemical connectivity for a premise; it is NOT itself the logical flow.

### 3B. Gap Analysis — triage, do NOT assume novelty

Every ⚠ DB-PARTIAL / ✗ DB-ABSENT / ✗ DB-CONTRADICTS item is a gap between the article and the databases. **A gap is a hypothesis to triage, not a finding.** There are many reasons a gap exists; novelty is only one. Before calling anything novel, RULE OUT the mundane explanations — the query-artifact branch is **non-optional**, because this workflow can manufacture false gaps (dropped `FROM`, `chebi:` vs `chemrof:`, missing `^^xsd:string`).

For each gap, assign ONE primary explanation and a confidence:

| Explanation | What it means | How to rule it in/out |
|---|---|---|
| **QUERY-ARTIFACT** | The gap is a bug in *our* query, not a real absence | RE-RUN with corrected `FROM`/namespace/`^^xsd:string`; re-check the MIE. MUST be excluded first. |
| **CONTRADICTION** | The DB actively disagrees with the claim | SPARQL returned a conflicting value (different formula, different EC, obsolete/renamed term) |
| **SCOPE / COVERAGE** | Entity is real but lives in a DB we didn't query, or is outside this DB's remit | Try a supporting DB (PubChem, ChEMBL, PDB); check the DB's declared scope |
| **CURATION LAG** | Known & published, just not in this RDF snapshot | Entity exists upstream (primary DB site / literature) but not in the Portal graph |
| **TRIVIAL / KNOWN** | Absent only because uncurated, not because new | The premise is textbook biology no one bothered to encode |
| **CANDIDATE NOVELTY** | Plausibly the paper's genuine new contribution | Survives a CORRECT query, sits on an otherwise DB-CONFIRMED flow, and none of the above fit |

Only after the first five are excluded does a gap earn **CANDIDATE NOVELTY** — and it is phrased "suggests," never "proves." A gap on an unverified query is a bug, not a discovery.

**Gap record template:**
```
GAP n: [what the article claims / needs that the DB does not supply]
  Located at: STEP n of the logical flow (3A)
  Query verified correct? ☑ (re-ran, still absent) / ☐ (NOT yet — resolve before triaging)
  Primary explanation: [QUERY-ARTIFACT | CONTRADICTION | SCOPE | CURATION LAG | TRIVIAL | CANDIDATE NOVELTY]
  Confidence: [high/med/low] — [one line of reasoning]
  If CANDIDATE NOVELTY: why each of the other five was excluded
```

---

## PHASE 4: ASSESSMENT

Two DISTINCT judgments — do NOT collapse them:
- **Flow soundness** (a score): how well the DB-backed *premises* support the paper's inferences.
- **Gap disposition** (NOT a score): what each unsupported item most likely IS, from the 3B triage. A CANDIDATE-NOVELTY gap is **not** a validation failure — it is a finding.

### Flow soundness — score the BACKGROUND PREMISES, not the novelty

Score each inferential step (from 3A) by how well its background premise is DB-backed. A premise the DB confirms scores high; a premise the DB *contradicts* scores low. A premise the DB is merely *silent* on is NOT scored here — it goes to the gap triage (3B). **Silence is not evidence against the paper.**

| Step / Premise | Premise DB-support (1-10) | SPARQL Evidence | Database IDs |
|----------------|---------------------------|-----------------|--------------|
| Step 1: [premise] | X/10 | [exact formula/equation/EC/GO def from SPARQL] | [IDs] |
| Step 2: [premise] | X/10 | ... | ... |

### Evidence Quality Levels (apply to the PREMISE, not the paper's new data):

- **★★★★★ Perfect (10/10)**: SPARQL returned exact structure/equation/definition matching the premise
- **★★★★☆ Strong (8-9/10)**: premise verified via SPARQL, minor connective gaps
- **★★★☆☆ Moderate (5-7/10)**: premise partly verified via SPARQL
- **★★☆☆☆ Weak (3-4/10)**: premise mostly unverified (only keyword search)
- **★☆☆☆☆ Contradicted (1-2/10)**: **SPARQL actively CONTRADICTS the premise** — reserved for disagreement, NOT for mere absence

**⚠️ Absence ≠ low score.** If the DB is silent because the item is triaged as CANDIDATE NOVELTY (or curation lag / scope), it does NOT lower flow soundness — it is reported in the gap analysis as a finding, not scored as a failure. Only a CONTRADICTION drags the score down.

### Gap disposition summary (carried from 3B):

| Gap | Located at | Query verified? | Explanation | Confidence |
|-----|-----------|-----------------|-------------|------------|
| Gap 1 | Step n | ☑ | CANDIDATE NOVELTY | med |
| Gap 2 | Step n | ☑ | CURATION LAG | high |

### Database Recommendations (only for gaps triaged as LAG / SCOPE / CANDIDATE NOVELTY):
- Curation-lag gap: "Add ChEBI:##### for metabolite X, formula C24H40O4 (verified by mass spec in article)"
- Scope gap: "Link Reactome R-HSA-##### to GO:####### (pathway-process connection missing)"
- Candidate-novelty gap: flag to authors/curators as *possibly new*, pending independent confirmation — do NOT assert as established fact.

---

## FINAL SUMMARY — THE USER-FACING DELIVERABLE

Everything above is the *work*; this is the *report* you present to the user. Four parts, in this order. Do not bury them in the scoring tables — this is what the user asked for.

### 1. Main Claim
[One sentence, from Phase 1 — the single assertion the paper argues for.]

### 2. Conclusion
[1-3 sentences, from Phase 1 — what the authors say follows from their results.]

### 3. Logical Flow (results → conclusion), database-backed
[From 3A. Show the chain: each experimental observation → inference → conclusion, with each *background premise* annotated by its SPARQL evidence and status (☑ DB-CONFIRMED / ⚠ DB-PARTIAL / ✗ DB-ABSENT / ✗ DB-CONTRADICTS). Make explicit which links are DB-confirmed and which rest on something the databases do not supply. This is the spine of the paper's argument, with the known parts anchored to exact database facts (formulas, equations, EC numbers, GO definitions) — not to the paper's prose.]

### 4. Gap Analysis — where the databases fall silent, and what that might mean
[From 3B. For each gap: state it, confirm the query was verified correct, then give the triaged explanation and confidence. Surface CANDIDATE-NOVELTY gaps as the most interesting output — the parts of the paper that curated knowledge cannot yet account for — but phrase them as *suggesting* possible novelty, having explicitly ruled out query artifacts, contradiction, scope, curation lag, and triviality. State plainly: a gap is a hypothesis about *why* the databases are silent, not a proof of discovery. Many gaps are mundane; call those what they are.]

**One-line verdict:** [Is the paper's flow DB-sound? Which gap(s), if any, are candidate-novelty vs. mundane, and with what confidence?]

---

## ANTI-SKIPPING SAFEGUARDS - READ BEFORE EVERY ANALYSIS

### Why Database Skipping Invalidates Analysis:

**CASE STUDY - What Happens When You Skip Rhea/Reactome:**

**WRONG APPROACH (Keyword search only):**
```
User: "Analyze article about bile acid metabolism"
AI: [searches ChEBI for "cholic acid", finds CHEBI:16359]
AI: [searches UniProt for "TGR5", finds Q8TDU6]
AI: "Analysis complete! Cholic acid and TGR5 receptor validated."
```

**PROBLEM**: 
- No reaction equations (Rhea not queried)
- No pathway structure (Reactome not queried)  
- Cannot validate claimed transformations
- Cannot verify metabolic flow
- **Validation score: 3/10 (Weak)** - only entity names checked

**CORRECT APPROACH (Full SPARQL queries):**
```
User: "Analyze article about bile acid metabolism"
AI: [Applies Rule 1 → ChEBI selected]
AI: [Applies Rule 2 → Rhea selected (reactions mentioned)]
AI: [Applies Rule 3 → Reactome selected (metabolism pathway)]
AI: [Applies Rule 4 → UniProt selected (TGR5 protein)]
AI: [Applies Rule 5 → GO selected (biological processes)]

AI: [Reads ChEBI MIE file]
AI: [Executes ChEBI SPARQL: gets formula C24H40O5, mass 408.57 Da]
AI: [Reads Rhea MIE file]
AI: [Executes Rhea SPARQL: finds "cholate + taurine = taurocholate + H2O"]
AI: [Reads Reactome MIE file]
AI: [Executes Reactome SPARQL: finds R-HSA-194068 with synthesis + recycling subpathways]
AI: [Reads UniProt MIE file]
AI: [Executes UniProt SPARQL: finds Q8TDU6 with GO:0005886, GO:0005125]
AI: [Reads GO MIE file]
AI: [Executes GO SPARQL: finds GO:0006954 "inflammatory response"]

AI: [Builds evidence chain: ChEBI → Rhea → UniProt → Reactome → GO]
AI: "Analysis complete! Validated with exact formulas, reaction equations, pathway structure."
```

**RESULT**:
- Exact molecular formula verified (C24H40O5)
- Conjugation reaction equation verified (stoichiometry)
- Complete pathway structure verified (synthesis + recycling)
- Protein function and localization verified
- **Validation score: 9/10 (Strong)** - complete mechanistic validation

**THE DIFFERENCE**: Keyword search finds names. SPARQL queries validate mechanisms.

---

### Self-Check Questions Before Claiming "Analysis Complete":

1. **Did I execute SPARQL queries for EVERY database I selected?**
   - If NO → Analysis is INCOMPLETE

2. **Can I cite exact formulas/masses from ChEBI SPARQL results?**
   - If NO and ChEBI was selected → GO BACK

3. **Can I cite exact reaction equations from Rhea SPARQL results?**
   - If NO and Rhea was selected → GO BACK

4. **Can I cite pathway sub-components from Reactome SPARQL results?**
   - If NO and Reactome was selected → GO BACK

5. **Can I cite GO term definitions from GO SPARQL results?**
   - If NO and GO was selected → GO BACK

6. **Did I build at least one cross-database evidence chain?**
   - If NO → GO BACK

**IF YOU ANSWERED "NO" OR "GO BACK" TO ANY QUESTION: You skipped critical validation steps. Return to Phase 2D.**

---

## FINAL QUALITY CHECKLIST

**Before submitting analysis, verify ALL items:**

### Database Selection:
- [ ] ✅ Applied ALL 5 mandatory selection rules
- [ ] ✅ Documented database selection with clear justification
- [ ] ✅ Did NOT skip any database that matched selection rules

### MIE Files:
- [ ] ✅ Read MIE files for 100% of selected Tier 1 databases
- [ ] ✅ Understood critical query patterns for each database
- [ ] ✅ Applied MIE insights to all SPARQL queries

### Keyword Searches:
- [ ] ✅ Searched all key entities in appropriate databases
- [ ] ✅ Documented all obtained database IDs
- [ ] ✅ Created ID tracking table with "☐ SPARQL Query Pending" for each ID
- [ ] ✅ ALL IDs marked "☑ SPARQL Completed" by end of Phase 2D

### SPARQL Queries (CRITICAL - MOST IMPORTANT SECTION):
- [ ] ✅ **ChEBI: Executed structure + hierarchy queries** (if selected)
- [ ] ✅ **Rhea: Executed equation + participant queries** (if selected)
- [ ] ✅ **Reactome: Executed pathway + complex queries** (if selected)
- [ ] ✅ **UniProt: Executed function + localization queries** (if selected)
- [ ] ✅ **GO: Executed definition + hierarchy queries** (if selected)
- [ ] ✅ **Built at least ONE complete cross-database evidence chain**
- [ ] ✅ **Can cite exact formulas, equations, structures from SPARQL results**
- [ ] ✅ **Can cite GO definitions from SPARQL results**
- [ ] ✅ **Executed 2+ queries per database (not just 1)**

### Evidence Documentation:
- [ ] ✅ Cited specific SPARQL query results (not just database IDs)
- [ ] ✅ Documented complete evidence chains with all intermediate IDs
- [ ] ✅ Recorded both positive AND negative SPARQL results
- [ ] ✅ Distinguished evidence from SPARQL queries vs. keyword searches

### Assessment:
- [ ] ✅ Validation scores reflect SPARQL evidence quality
- [ ] ✅ Distinguished 5 evidence quality levels correctly
- [ ] ✅ Made specific, actionable database update recommendations

---

## COMMON MISTAKES TO AVOID

❌ **FATAL MISTAKE**: Skipping SPARQL queries for selected databases
✅ **CORRECT**: Execute 2+ SPARQL queries per database, every time

❌ **MISTAKE 1**: Only doing keyword searches, claiming "analysis complete"
✅ **CORRECT**: Keyword search finds IDs → SPARQL queries validate mechanisms

❌ **MISTAKE 2**: Executing 1 query per database instead of 2+
✅ **CORRECT**: Structure + hierarchy (ChEBI), equation + participants (Rhea), etc.

❌ **MISTAKE 3**: Not building cross-database evidence chains
✅ **CORRECT**: Link ChEBI → Rhea → UniProt → Reactome → GO with all IDs

❌ **MISTAKE 4**: Claiming "databases don't have this" without running SPARQL
✅ **CORRECT**: Run proper SPARQL queries first, THEN identify gaps

❌ **MISTAKE 5**: Citing only database IDs without SPARQL result details
✅ **CORRECT**: "ChEBI:16359 - SPARQL returned C24H40O5, 408.57 Da"

❌ **MISTAKE 6**: Not applying all 5 database selection rules
✅ **CORRECT**: Systematically apply every rule, document rationale

❌ **MISTAKE 7**: Skipping MIE files and writing incorrect SPARQL queries
✅ **CORRECT**: Read MIE file FIRST for every database, learn critical patterns

❌ **MISTAKE 8**: Finding IDs in keyword search but not querying them with SPARQL
✅ **CORRECT**: Create tracking table, mark each ID "Pending", execute SPARQL for ALL IDs

❌ **MISTAKE 9**: Citing keyword search result text instead of SPARQL query results
✅ **CORRECT**: "Q969Q1 - SPARQL returned EC 2.3.2.27, GO:0061630" (not "Q969Q1 is E3 ligase")

---

## QUALITY ASSURANCE - ANALYSIS COMPLETENESS SCORE

**Calculate your analysis completeness score:**

| Checkpoint | Points | Self-Assessment |
|------------|--------|-----------------|
| Applied all 5 database selection rules | 10 pts | [ ] |
| Read MIE files for all selected databases | 10 pts | [ ] |
| Executed keyword searches for all entities | 10 pts | [ ] |
| **Executed 2+ SPARQL queries per database** | **40 pts** | [ ] |
| Built cross-database evidence chain | 15 pts | [ ] |
| Documented SPARQL results with IDs | 10 pts | [ ] |
| Provided validation scores with evidence | 5 pts | [ ] |

**TOTAL: _____ / 100 points**

- **90-100 points**: Excellent - comprehensive analysis
- **70-89 points**: Good - minor gaps in SPARQL queries
- **50-69 points**: Acceptable - missing some SPARQL validations
- **Below 50 points**: INCOMPLETE - major databases skipped

**If you scored below 70 points, GO BACK and complete missing SPARQL queries.**

---

**Template v7.0** | 2026-07-01 | Reoriented from per-entity fact-checking to argument reconstruction + gap triage

**KEY IMPROVEMENT IN v7.0:**
- Phase 1 now extracts the **argument skeleton** (observation → inference → premise), separating the paper's NEW data from the DB-backable background premises
- Phase 3 rewritten: **3A** DB-backed logical flow (results → conclusion), **3B** gap triage — a gap is a hypothesis, not a finding
- Phase 4 fixes the scoring inversion: **absence ≠ low score**; only an active CONTRADICTION lowers flow soundness. Silence goes to gap triage instead
- New **FINAL SUMMARY** deliverable: Main Claim / Conclusion / DB-backed Logical Flow / Gap Analysis
- Gaps are triaged across six explanations (query-artifact, contradiction, scope, curation lag, trivial, candidate novelty); novelty is only claimed after the mundane five are ruled out, and phrased "suggests," never "proves"
- Retains v6.0's ID tracking (Phase 2C/2D): every keyword-search ID still MUST be SPARQL-validated
