Create a question following the instructions below.

---

# TogoMCP Question Creation Guide (v5.5.0 - Type-First Edition)

Create 50 evaluation questions testing TogoMCP's ability to answer biological questions using RDF databases.

---

## 🎯 CORE REQUIREMENTS

**Execution-First:** Call tools, paste results. No "I will..." statements.

**Workflow Order:** Question type selection → Database selection → Keyword selection → Question development

**Question Specificity:** Use named entities, avoid famous facts (BRCA1, TP53, insulin, aspirin).
- ✅ GOOD: "Does JAK2 V617F have pathogenic ClinVar variants?"
- ❌ AVOID: "Do genes have variants?" (too general)

**Targets (50 questions):**
- **Question types:** 10 each (yes_no, factoid, list, summary, choice) - ENFORCED
- Multi-database (2+): ≥60% | Multi-database (3+): ≥20% | UniProt: ≤70%
- Every database used ≥1x (all 23)
- Score ≥9/12, no dimension = 0 | Keyword filtered to match type AND databases

---

## 🚨 DATA COVERAGE GAPS - CRITICAL

```
❌ WRONG: Search finds 134 → Sample 17 → VALUES those 17 → Check only those 17
✅ RIGHT: Search finds 134 → Extract ALL IDs → Process ALL comprehensively
```

**The Core Issue:** Question scope broader than query scope.

### Decision Tree: Valid Exploration vs. Coverage Gap

```
┌─────────────────────────────────────────────────────────┐
│ Did you discover entities during exploration?          │
│ (genes, diseases, proteins, pathways, etc.)            │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
     ✅ YES              ❌ NO
        │                   │
        ▼                   └──> Proceed (no coverage gap)
┌───────────────────────────────────────────────┐
│ Does your QUESTION ask about:                 │
│ A) Specific entity/entities you discovered?  │
│ B) All/which/how many entities of that type? │
└────────┬──────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
  (A)       (B)
    │         │
    │         ▼
    │    ┌─────────────────────────────────────────┐
    │    │ PRE-CATEGORIZATION CHECKPOINT (NEW):    │
    │    │ If you need to CATEGORIZE entities      │
    │    │ (e.g., group organisms by order):       │
    │    │                                         │
    │    │ 1. Extract ALL entity IDs first         │
    │    │ 2. Verify extraction complete:          │
    │    │    Total = Extracted + Remaining?       │
    │    │ 3. Then categorize ALL extracted        │
    │    └─────────────────┬───────────────────────┘
    │                      │
    │                      ▼
    │    ┌─────────────────────────────────────────┐
    │    │ Does your QUERY process:                │
    │    │ A) ALL discovered entities?             │
    │    │ B) SUBSET of discovered entities?       │
    │    └────┬──────────────────────────────────┬─┘
    │         │                                   │
    │       (A)                                 (B)
    │         │                                   │
    │         │                                   ▼
    │         │                            ❌ COVERAGE GAP
    │         │                            (Sampling)
    │         │
    │         ▼
    │    ✅ VALID
    │    (Comprehensive)
    │
    ▼
✅ VALID
(Specific entity query)
```

### Examples:

**✅ VALID - Specific Entity Discovered:**
- Explore: Find TLR7 gene in MONDO definition
- Ask: "How many pathogenic variants in **TLR7**?"
- Query: ALL TLR7 variants
- Why valid: Question asks about TLR7, query returns ALL TLR7 data

**✅ VALID - All Entities Processed:**
- Explore: Find 36 kinase GO terms
- Ask: "How many proteins have **kinase activity**?"
- Query: ALL 36 GO terms
- Why valid: Question asks about "kinase activity", query uses ALL 36 terms

**❌ COVERAGE GAP - Sampling:**
- Explore: Find 36 kinase GO terms
- Ask: "How many proteins have **kinase activity**?"
- Query: 8 of 36 GO terms
- Why invalid: Question asks comprehensively, query samples (22% coverage)

**❌ COVERAGE GAP - Entity Pre-filtering (Example from Question 6):**
- Explore: Find 44 proteins → 19 organisms total
- Filter: "Eyeball" 10 organisms that "look like plants" (taxonomy ID ranges)
- Ask: "Which plant **order** has the most proteins?"
- Query: Categorize only those 10 organisms by order
- Why invalid: Missing 2 plant organisms (17% loss) → missed entire order, wrong counts
- **Arithmetic check failed:** 23+5+2=30 ≠ 35 total plant proteins

**❌ COVERAGE GAP - Reverse Engineering:**
- Explore: Find 5 SLE-associated genes (TLR7, C1QA, DNASE1L3, IRF5, STAT4)
- Ask: "How many variants in **SLE-associated genes**?"
- Query: Only TLR7
- Why invalid: Question scope (5 genes) > query scope (1 gene)

### 6 Coverage Gap Types:

1. **Vocabulary Sampling** - Using 8/36 discovered GO terms
2. **Entity Pre-filtering** - Filter entities without verification → categorize incomplete set
3. **Database Post-selection** - Choose databases based on exploration results
4. **Filter Targeting** - Filters match entities you already found
5. **Cross-DB Sampling** - `VALUES ?id { <specific IDs from exploration> }` in comprehensive query
6. **Reverse Engineering** - Question scope > query scope

**Key Principle:** 
- Exploration to discover entities is REQUIRED and VALID
- Using those entities is VALID if question scope = query scope
- Coverage gap occurs when question scope > query scope (sampling)

**Query Type:**
- **Comprehensive** ("Which/How many X have Y?", "Summarize") → Process ALL
- **Example-Based** ("Top 5 X", "Name 3 examples") → Sampling allowed
- **Specific** ("How many variants in TLR7?") → Process ALL for that entity

---

## 🧮 MANDATORY ARITHMETIC VERIFICATION

**UNIVERSAL RULE:** Applies to ALL aggregations (GROUP BY, categorization, counting by category).

**Trigger Patterns - ALWAYS verify when you:**
- Use GROUP BY in SPARQL
- Count "by category," "by type," "per X"
- Ask "Which X has most Y?" or "How many Y per X?"
- Perform any categorical comparison or distribution analysis

### Checkpoint A: Pre-Filter Count Match

When filtering entities (e.g., extracting plants from all organisms):

```
Entities before filter: COUNT(*)           = _____
Entities after filter:  COUNT(*) + filters = _____

Example:
  Total organisms: 19
  Extracted plants: 12
  Remaining (bacteria/animals): 7
  Sum: 12 + 7 = 19 ✓

MUST MATCH: If different → filter is incomplete, missing entities!
```

**MANDATORY before categorization:**
- Never use unverified heuristics (taxonomy ID ranges, name patterns, manual selection)
- Always verify: filtered + remaining = total
- Document verification in notes

### Checkpoint B: Post-Aggregation Verification (UNIVERSAL)

**Applies to:** EVERY GROUP BY query, categorical counting, distribution analysis.

```
Query pattern:
  SELECT ?category (COUNT(?entity) as ?count)
  WHERE { ... }
  GROUP BY ?category
  
Verification (MANDATORY):
  SELECT (COUNT(DISTINCT ?entity) as ?total)
  WHERE { ... same criteria without GROUP BY ... }
```

**Three Possible Outcomes:**

**1. Sum = Total ✓ (Mutually Exclusive Categories)**
```
Example: Proteins by taxonomic order
  Poales: 23 + Fabales: 9 + Asterales: 2 + Caryophyllales: 1 = 35
  Total unique proteins: 35
  35 = 35 ✓ PASS
  
Interpretation: Each protein belongs to exactly one order
```

**2. Sum > Total ⚠️ (Valid if Documented)**
```
Example: Proteins by inflammasome type
  NLRP3: 8 + NLRP1: 6 + AIM2: 3 + IPAF: 3 + NLRP6: 2 + CARD8: 1 = 23
  Total unique proteins: 15
  23 > 15 → Overlap detected!
  
Interpretation: 8 proteins participate in multiple inflammasome types
ACTION REQUIRED: Explain overlap in ideal_answer
```

**3. Sum < Total ❌ (COVERAGE GAP)**
```
Example: Question 6 initial attempt
  Poales: 23 + Fabales: 5 + Caryophyllales: 2 = 30
  Total plant proteins: 35
  30 < 35 → MISSING 5 proteins!
  
Interpretation: Incomplete entity extraction, missing categories
ACTION REQUIRED: STOP, debug, find missing entities
```

### When Counts Don't Match

**If Sum > Total (Overlap):**
- ✅ VALID - Document in ideal_answer
- Explain shared components/multi-membership
- Example: "23 annotations for 15 unique proteins, with 8 shared components..."

**If Sum < Total (Missing Data):**
1. **STOP immediately** - Do not proceed
2. Re-examine filtering - What heuristic did you use?
3. Query for missing entities: `WHERE NOT IN (processed_ids)`
4. Verify ALL entities categorized
5. Update queries with complete entity set
6. Re-verify: sum = total

### Real Example: Question 6 Coverage Gap

**Scenario:** Counting proteins by plant taxonomic order

**Initial Attempt (WRONG):**
1. Found 44 proteins with GO:0015066 (alpha-amylase inhibitor)
2. Counted proteins per organism → 19 organisms
3. "Eyeballed" plant organisms → picked 10 using taxonomy ID ranges (3000-50000)
4. Got orders for 10 organisms → 3 orders
5. Counted: Poales: 23, Fabales: 5, Caryophyllales: 2
6. **Arithmetic:** 23 + 5 + 2 = 30

**Verification (FAILED):**
```
❌ Sum (30) ≠ Total plant proteins (35)
❌ Missing 5 proteins!
```

**Debug:** Re-queried for organisms NOT in the 10 selected
**Found:** taxon:72433 (4 proteins), taxon:324593 (2 proteins) - both plants!
**Impact:** Missed entire order (Asterales), wrong Fabales count

**Corrected Attempt:**
1. VALUES ?org { all 12 plant organisms } ← Complete set
2. Got orders for 12 organisms → 4 orders
3. Counted: Poales: 23, Fabales: 9, Asterales: 2, Caryophyllales: 1
4. **Arithmetic:** 23 + 9 + 2 + 1 = 35

**Verification (PASSED):**
```
✓ Sum (35) = Total (35)
✓ All entities accounted for
```

---

## 🎯 INTENTIONAL NARROWING (When Results Exceed Threshold)

**KEY DISTINCTION:**
```
❌ Coverage Gap:  Question asks "all kinases" → Query uses 8/36 GO terms → Answers 22% of question
✅ Intentional:   Question asks "RTK kinases" → Query uses 8/8 RTK terms → Answers 100% of question
```

**When to Narrow:**
| Result Count | Action |
|--------------|--------|
| <500 | Keep comprehensive scope |
| 500-2,000 | Consider narrowing OR convert to CHOICE question |
| 2,000-10,000 | Narrow scope (recommended) |
| >10,000 OR timeout | MUST narrow scope |

**Narrowing Process:**
1. **Test comprehensive scope:** Run COUNT query with ALL vocabulary
2. **If too broad:** Identify narrower biological subset (functional/taxonomic/clinical)
3. **Rewrite question:** Match question to narrower scope BEFORE finalizing
4. **Document:** Record narrowing decision with justification

**Required Documentation:**
```yaml
narrowing_applied: true
narrowing_details:
  initial_scope: "all kinase activity (36 GO terms, ~15K proteins)"
  narrowed_to: "receptor tyrosine kinases (8 GO terms, ~150 proteins)"
  justification: "RTKs are clinically relevant subclass, verifiable scope"
  vocabulary_complete_in_scope: true  # Used ALL 8 RTK terms
```

**Biological Justification Required:**
- ✅ Functional: kinase → receptor tyrosine kinase
- ✅ Taxonomic: bacteria → nitrogen-fixing soil bacteria  
- ✅ Clinical: variants → pathogenic variants in drug targets
- ❌ Random: "picked 8 of 36 terms randomly"
- ❌ Result-based: "these 8 terms gave interesting results"

**Still Comprehensive:**
Questions with intentional narrowing remain COMPREHENSIVE within their stated scope. Must process ALL entities matching the narrowed criteria.

---

## 🔬 STRUCTURED VOCABULARY DISCOVERY (MANDATORY)

**The Hierarchy (follow in order):**
1. Ontology IRIs (GO, MONDO, ChEBI) → 2. Typed predicates → 3. Classification codes → 4. Graph navigation → 5. Text search (LAST RESORT)

**Before ANY query, check structured vocabulary:**

| Concept Type | Check | Tool | Example |
|--------------|-------|------|---------|
| Molecular function | GO | `OLS4:searchClasses(ontologyId=go)` | "kinase activity" → GO:0016301 |
| Biological process | GO | `OLS4:searchClasses(ontologyId=go)` | "apoptosis" → GO:0006915 |
| Cellular component | GO | `OLS4:searchClasses(ontologyId=go)` | "nucleus" → GO:0005634 |
| Enzyme | EC, GO | `search_rhea_entity()`, `OLS4:searchClasses(ontologyId=go)` | "nitrogenase" → EC 1.18.6.1 |
| Disease | MONDO, MeSH | `OLS4:searchClasses(ontologyId=mondo)`, `search_mesh_descriptor()` | "Noonan syndrome" → MONDO:0018955 |
| Chemical/Drug | ChEBI, ChEMBL | `OLS4:searchClasses(ontologyId=chebi)`, `search_chembl_molecule()` | "aspirin" → CHEBI:15365 |
| Pathway | Reactome, GO | `search_reactome_entity()` | "glycolysis" → R-HSA-70171 |
| Anatomy | UBERON | `OLS4:searchClasses(ontologyId=uberon)` | "heart" → UBERON:0000948 |
| Organism | Taxonomy | `ncbi_esearch(database=taxonomy)` | "E. coli" → taxon:562 |

**Auto-Triggers:**
- "-ase" suffix → Check GO + EC
- "activity", "process", "pathway" → Check GO
- Disease names, "disorder", "syndrome" → Check MONDO + MeSH

**Red Flags - STOP and check ontology:**
- 🚩 Writing `bif:contains` on protein name → Check GO first
- 🚩 Searching enzyme by name → Check GO + EC first
- 🚩 Searching disease by name → Check MONDO/MeSH first
- 🚩 Using VALUES from search in comprehensive query → Data coverage gap

⚠️ **CHECKPOINT 1: Vocabulary Completeness**
```
Before writing SPARQL query:
┌─────────────────────────────────────────────┐
│ Discovered terms: _____ (from ontology)     │
│ Terms in VALUES:  _____ (in SPARQL)         │
│                                             │
│ IF NOT EQUAL → DATA COVERAGE GAP            │
└─────────────────────────────────────────────┘
```

**Workflow:**
```
Step 2.5: VOCABULARY DISCOVERY (before formulating question)
1. Identify concept type
2. Call tool: OLS4:searchClasses / search_reactome_entity / ncbi_esearch
3. If ontology term has descendants: Call OLS4:getDescendants()
4. Document ALL IRIs found (parent + ALL descendants)
5. Design query with ALL IRIs, NOT text search
6. Only if no IRI: justify text search, use comprehensive synonyms
```

---

## 📊 QUESTION TYPE REQUIREMENTS

| Type | Target | Hard Cap | Priority Trigger |
|------|--------|----------|------------------|
| YES/NO | 10 (20%) | 8-12 | Use when <8 |
| FACTOID | 10 (20%) | 8-12 | Use when <8 |
| LIST | 10 (20%) | 8-12 | Use when <8 |
| SUMMARY | 10 (20%) | 8-12 | Use when <8 |
| CHOICE | 10 (20%) | 8-12 | Use when <8 |

**Enforcement Strategy:**
- Questions 1-25: Aim for rough balance (each type 4-6 uses)
- Questions 26-40: Correct imbalances (bring lagging types to 8+)
- Questions 41-50: Fill to target of 10 each (or within 8-12 range)

**Type Status in Coverage Tracker:**
```yaml
question_type_usage:
  yes_no: 3
  factoid: 12
  list: 15
  summary: 2
  choice: 2

type_status:
  over_cap: [list]              # >12 uses - MUST AVOID
  at_capacity: [factoid]        # 10-12 uses - AVOID
  needs_priority: [summary, choice]  # <8 uses - PREFER
  ok: [yes_no]                  # 8-10 uses - CONSIDER
```

**Hard Rules:**
- ❌ NEVER create 13th question of any type
- ❌ NEVER create question of type >10 when other types <8
- ✅ ALWAYS prioritize types with <8 uses
- ✅ At question 40+: Only create types with <10 uses

---

## 🎨 TYPE-DRIVEN QUESTION DESIGN (MANDATORY)

**Workflow:** Type Selection → Database Selection → Keyword Selection → Question Design

### Pattern 1: YES/NO Questions

**Design Requirements:**
- Binary criterion (exists/doesn't exist, has/lacks property)
- Specific named entity (gene, protein, disease, compound)
- Verifiable with EXISTS or absence check

**Keyword Selection Strategy:**
- Filter to: Specific genes, proteins, diseases, pathways, compounds
- Avoid: Broad categories, processes, functions

**Database Combinations:**
- Gene + Variants: UniProt/NCBI Gene + ClinVar
- Protein + Structure: UniProt + PDB
- Compound + Target: ChEMBL + UniProt
- Disease + Gene: MONDO + NCBI Gene

**Example Patterns:**
- "Does [GENE] have [PROPERTY] in [DATABASE]?"
- "Is [PROTEIN] annotated with [FUNCTION]?"
- "Does [COMPOUND] target [PROTEIN_CLASS]?"

### Pattern 2: FACTOID Questions

**Two Sub-types:**

**2A: Counting (Comprehensive)**
- "How many X have Y?"
- Requires processing ALL entities
- Uses COUNT(*) or COUNT(DISTINCT)

**2B: Lookup (Specific)**
- "What is the [PROPERTY] of [ENTITY]?"
- Direct retrieval, no aggregation

**Keyword Selection Strategy:**
- Counting: Broad categories (kinase, receptor, pathway)
- Lookup: Specific entities

**Database Combinations:**
- Counting: GO + UniProt, Reactome + UniProt
- Lookup: Any single database with rich properties

### Pattern 3: LIST Questions

**Two Sub-types:**

**3A: Comprehensive**
- "Which X have Y?" (process ALL)
- "List all X that meet criterion Y"

**3B: Example-Based**
- "Top 5 X by Y"
- "Name 3 examples of X"

**Keyword Selection Strategy:**
- Filter to: Categories with 5-100 members (verifiable range)
- Avoid: Huge categories (>1000 members) unless narrowing

**Database Combinations:**
- Functional: GO + UniProt
- Structural: PDB + ChEMBL
- Clinical: ClinVar + NCBI Gene + ChEMBL

### Pattern 4: SUMMARY Questions

**Design Requirements:**
- Multi-dimensional aggregation
- 2-4 facets to summarize
- Single paragraph answer (not list)

**Keyword Selection Strategy:**
- Filter to: Complex processes, multi-component systems
- Good keywords: pathway, complex, assembly, regulation, signaling

**Database Combinations (CRITICAL):**
- Need 3+ databases for multi-dimensional view
- Reactome + GO + UniProt (pathway-function-protein)
- ChEMBL + UniProt + Rhea (target-protein-reaction)
- ClinVar + NCBI Gene + MONDO (variant-gene-disease)

**Aggregation Dimensions:**
- Taxonomic distribution
- Functional categories
- Structural features
- Clinical significance
- Temporal/spatial patterns

**Example Patterns:**
- "Summarize [COMPLEX_SYSTEM] by [DIMENSION1], [DIMENSION2], [DIMENSION3]"
- "Characterize [ENTITY_CLASS] across [TAXONOMIC], [FUNCTIONAL], [STRUCTURAL] dimensions"

### Pattern 5: CHOICE Questions

**Two Sub-types:**

**5A: Bounded List**
- "Which of [A, B, C, D] has the most X?"
- Choices explicitly enumerated (3-6 items)

**5B: Unbounded Categories**
- "Which [CATEGORY_TYPE] has the most X?"
- Categories discovered from data (orders, families, types)

**Keyword Selection Strategy:**
- Filter to: Concepts with natural categorical divisions
- Good keywords: organism groups, protein families, pathway types, disease categories

**Database Combinations:**
- Taxonomy + functional: Taxonomy + GO + UniProt
- Clinical + structural: ClinVar + PDB
- Chemical + biological: ChEBI + Rhea + UniProt

**Example Patterns:**
- "Which [TAXONOMIC_RANK] has most [PROPERTY]?"
- "Which [PROTEIN_FAMILY] is most [CRITERION]?"

---

## 📋 QUESTION TYPES (Quick Reference)

### Type 1: YES/NO (Always Comprehensive)
- "Does X have Y?" → Check ALL, use EXISTS, never VALUES from search

### Type 2: FACTOID
- **Counting** (Comprehensive): "How many X have Y?" → COUNT ALL
- **Lookup** (Example-Based): "What is name of X?" → Direct retrieval

### Type 3: LIST
- **Comprehensive**: "Which X have Y?" → Process ALL X
- **Example-Based**: "Top 5 X" → ORDER BY LIMIT

### Type 4: SUMMARY (Always Comprehensive)
- "Summarize X across Y" → Aggregate ALL, single paragraph

### Type 5: CHOICE
- **Bounded**: "Which of [A,B,C] has most X?" → Check all in list
- **Unbounded**: "Which category has most X?" → Check ALL categories

---

## 🔧 TROUBLESHOOTING COMPREHENSIVE QUERIES

When comprehensive queries fail (500 error):
- ✅ Extract ALL IDs → Process in batches → Aggregate
- ✅ Restructure query pattern (simpler joins, different order)
- ✅ Reconsider question scope (make bounded by design)
- ❌ Never: Sample subset and treat as complete

---

## 📝 QUESTION WORDING

**Be Specific:**
- ✅ "Does JAK2 have pathogenic variants?" NOT "Do genes have variants?"
- ❌ Avoid: BRCA1, TP53, insulin, aspirin, glycolysis, E. coli K-12

**Red Flag Words** (need qualifiers): bind, contain, have, associated with, interact with

**Add qualifiers:** "annotated with", "co-crystallized with", "documented"

---

## 🎯 DATABASE SELECTION STRATEGY (STEP 2 - After Type Selection)

**Critical Order:** Type Selection → Database Selection → Keyword Selection → Question Development

### Step 1: Read coverage_tracker.yaml

⚠️ **CRITICAL: `coverage_tracker.yaml` is on the USER'S COMPUTER**

**ALWAYS start by reading coverage tracker:**
```
Filesystem:read_text_file("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml")
```

**Check TWO sections:**

**A) question_type_usage - SELECT UNDER-REPRESENTED TYPE**
- Find types with <8 uses (highest priority)
- Avoid types with >10 uses (approaching cap)
- This determines which type to create

**B) database_usage - IDENTIFY UNDER-USED DATABASES**
- Find databases with 0-2 uses (highest priority)
- Note databases approaching 70% cap (avoid)
- This informs database selection in Step 3

### Step 2: Call list_databases()

**Call `list_databases()` to understand all 23 databases:**
- Database descriptions (what entities, cross-references, use cases they cover)
- Keywords in descriptions that reveal capabilities
- Cross-reference opportunities between databases

**Why this order:**
- Step 1 tells you WHICH type to create and databases to prioritize
- Step 2 tells you HOW those databases can be integrated for that type

### Step 3: Select Target Databases (2-3 recommended) Matching Question Type

**Selection Criteria:**
1. **Type compatibility (NEW - CRITICAL):**
   - YES/NO: Needs specific entities with binary properties
   - FACTOID: Needs countable/retrievable attributes
   - LIST: Needs enumerable sets with 5-100 members
   - SUMMARY: Needs 3+ databases with multi-dimensional properties
   - CHOICE: Needs natural categorical divisions

2. **Complementary domains:** Choose databases that can be meaningfully integrated
   - Example: ChEMBL (drug targets) + ClinVar (variants) + NCBI Gene (gene info)
   - Example: Reactome (pathways) + GO (functions) + UniProt (proteins)
   - Example: PubChem (compounds) + ChEBI (chemical ontology) + Rhea (reactions)

3. **Cross-reference opportunities:** Databases that share common identifiers
   - UniProt IDs link to: NCBI Gene, Ensembl, PDB, Reactome, Rhea
   - ChEMBL IDs link to: UniProt, ChEBI, PubChem
   - Disease IDs (MONDO) link to: genes, variants, drugs

4. **Coverage tracker needs:** Prioritize under-used databases (from Step 1)
   - Use databases with 0-2 uses identified in Step 1
   - Ensure all 23 databases used ≥1x across 50 questions

5. **Avoid common pitfalls:**
   - ❌ UniProt + databases with weak links → Choose databases with stronger integration
   - ❌ All protein-centric databases → Mix entity types (proteins, compounds, diseases, pathways)
   - ❌ Selecting based on "interesting results" → Select based on biological complementarity

**Document Decision:**
```yaml
database_selection_strategy:
  target_type: summary
  target_databases: [reactome, go, uniprot]
  rationale: "Multi-dimensional pathway characterization; reactome under-used"
  type_compatibility: "3+ databases enable pathway-function-protein aggregation"
  expected_integration: "Reactome pathways → UniProt proteins → GO functions"
```

### Step 4: Choose Keyword Matching Type AND Database Capabilities

**Now that you know your type and target databases, select keyword strategically:**

⚠️ **CRITICAL: `keywords.tsv` is on the USER'S COMPUTER, NOT Claude's computer**

**ALWAYS USE THESE TOOLS FOR USER'S FILES:**
```
Filesystem:read_text_file("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv")
Filesystem:read_text_file("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml")
```

**NEVER USE THESE TOOLS FOR USER'S FILES:**
```
❌ view("/Users/arkinjo/...")           ← Claude's computer only
❌ bash_tool("cat /Users/arkinjo/...")  ← Claude's computer only
```

**Keyword Selection Workflow:**
1. Read keywords.tsv using `Filesystem:read_text_file()` (USER'S COMPUTER)
2. **Filter keywords - FIRST by question type:**
   - YES/NO: Specific entities (genes, proteins, diseases, pathways)
   - FACTOID-count: Broad categories (kinase, receptor, pathway)
   - FACTOID-lookup: Specific entities
   - LIST: Categories with 5-100 members
   - SUMMARY: Complex systems (pathways, complexes, regulation)
   - CHOICE: Categorical concepts (organism groups, families)
3. **Filter keywords - SECOND by database capabilities:**
   - Example: For Reactome+GO+UniProt → Keep pathway/process keywords
   - Example: For ChEMBL+ClinVar+NCBI Gene → Keep drug target keywords
   - Discard keywords unrelated to your database combination
4. Cross-reference with coverage tracker: Remove already-used keywords
5. Count filtered unused keywords
6. Generate random number (1 to filtered count)
7. Select keyword at that position

**Why This Order Matters:**
- ✅ Type selection first ensures question has right structure
- ✅ Database selection matches type requirements
- ✅ Keyword filtering aligns with both type AND databases
- ✅ Natural multi-database questions with correct type
- ❌ Old way: Random keyword → force-fit databases → wrong type

**Complete 4-Step Example:**
```
Step 1: Read coverage_tracker.yaml
  - Type needs: summary (2 uses, PRIORITY), choice (2 uses, PRIORITY)
  - Selected type: summary (need multi-dimensional aggregation)
  - Under-used databases: reactome (1 use), bacdive (0 uses)
  - Approaching cap: uniprot (32 uses, 64%)
  
Step 2: Call list_databases()
  - Reactome: pathways, reactions, biological processes
  - GO: molecular functions, biological processes, cellular components
  - UniProt: protein sequences, functions, annotations
  - Integration: Reactome pathways → UniProt proteins via cross-refs
  
Step 3: Select target databases for SUMMARY type
  - Selected: reactome, go, uniprot (3 databases - required for summary)
  - Type compatibility: 3+ databases enable multi-dimensional aggregation
  - Rationale: Pathway-protein-function integration; reactome under-used (priority)
  - UniProt at 64% but essential for integration
  
Step 4: Filter keywords for SUMMARY + pathway databases
  - Type filter (summary): pathway, complex, assembly, regulation, signaling
  - Database filter: apoptosis, autophagy, phosphorylation, ubiquitination
  - Discarded: aspirin (compound, not pathway), melanoma (disease, not process)
  - Discarded: kinase (better for LIST/FACTOID, not multi-dimensional enough)
  - Filtered pool: 18 keywords matching SUMMARY + pathway databases
  - Random selection: "autophagy" (7th of 18 filtered keywords)
```

**Still NOT ALLOWED:** 
- Browsing keywords for "interesting" topics
- Choosing keywords before type/database selection
- Selecting databases after finding keyword results
- Selecting type after exploring keyword results

---

## 📊 DATABASE REQUIREMENTS

| Target | Requirement |
|--------|-------------|
| 2+ databases | ≥60% (≥30 questions) |
| 3+ databases | ≥20% (≥10 questions) |
| UniProt cap | ≤70% (≤35 questions) |
| Each database | ≥1 use (all 23) |

**Alternatives to UniProt:** Rhea, ChEMBL, PDB, Reactome, Ensembl, NCBI Gene

⚠️ **CHECKPOINT 2: Database Selection Timing**
```
Choose databases based on:
✅ Selected question type requirements (SUMMARY needs 3+ databases)
✅ Question's biological domain (disease → MONDO, variants → ClinVar)
❌ Where you found interesting results during exploration
```

---

## 🎯 SCORING RUBRIC (Total ≥9/12, No Zeros)

| Dimension | 0 | 1 | 2 | 3 |
|-----------|---|---|---|---|
| **Biological Insight** | Inventory | Basic biology | Function/properties | Mechanisms/evolution |
| **Multi-Database** | Search-only | Single OR weak | 2 databases | 3+ databases |
| **Verifiability** | Unbounded | Loosely bounded | 6-10 items | ≤5 items |
| **RDF Necessity** | PubMed OK | Helpful | Significantly enhances | Impossible without |

---

## ✅ MUST HAVE / ❌ PROHIBITED

**REQUIRED:**
1. Biological insight
2. Multi-DB (60%+)
3. Verifiability
4. RDF necessity
5. Comprehensive processing for yes/no, counts, "which have", summaries
6. **Question type selection BEFORE database selection**
7. **Database selection BEFORE keyword selection**
8. **Keyword filtered to match TYPE AND databases**
9. **Type distribution: No type >12, prioritize types <8**
10. Precise wording
11. Tool execution
12. UniProt <70%
13. Database diversity
14. Structured vocab check BEFORE text search
15. ALL discovered terms used in VALUES (no sampling)
16. **Arithmetic verification for ALL aggregations (GROUP BY, categorization)**
17. **No filtering heuristics without verification queries**
18. **Use Filesystem tools for keywords.tsv and coverage_tracker.yaml (USER'S COMPUTER)**
19. **Type-specific design patterns followed**

**PROHIBITED:**
1. Inventory questions | 2. Unbounded scopes | 3. Literature-recoverable answers
4. Data coverage gaps (sampling) | 5. Multi-paragraph summaries | 6. Ambiguous wording
7. Thematic clustering | 8. **Sampling for comprehensive questions**
9. **Text search without checking structured vocabulary first**
10. **Partial use of discovered vocabulary terms**
11. **Unverified filtering heuristics (ID ranges, name patterns)**
12. **Proceeding with aggregations without arithmetic verification**
13. **Using view() or bash_tool() for keywords.tsv (USER'S FILES)**
14. **Type selection after keyword exploration**
15. **Keyword selection before type/database selection**
16. **Unfiltered keyword selection (must match TYPE and databases)**
17. **Exceeding type capacity (>12 uses)**
18. **Creating question of type >10 when other types <8**

---

## 🚦 WORKFLOW CHECKLIST

### PRE-WORKFLOW (5 STEPS - MANDATORY ORDER)

- [ ] **Step 0: QUESTION TYPE SELECTION (NEW - FIRST STEP)**
  - [ ] Read coverage_tracker.yaml using `Filesystem:read_text_file()` (USER'S COMPUTER!)
  - [ ] **Check question_type_usage section**
  - [ ] Identified type status:
    - [ ] Over-cap types (>12): _______ (MUST AVOID)
    - [ ] At-capacity types (10-12): _______ (AVOID)
    - [ ] Needs-priority types (<8): _______ (PREFER)
    - [ ] OK types (8-10): _______ (CONSIDER)
  - [ ] **Selected target type for this question:** _______
  - [ ] Documented type selection rationale

- [ ] **Step 1: Database Coverage Check (constrained by type)**
  - [ ] Check database_usage section in coverage tracker
  - [ ] Identified under-used databases (0-2 uses)
  - [ ] Noted databases approaching 70% cap
  - [ ] **Type-Database compatibility verified:**
    - [ ] YES/NO: Specific entities with binary properties
    - [ ] FACTOID: Countable/retrievable attributes
    - [ ] LIST: Enumerable sets (5-100 items)
    - [ ] SUMMARY: Multi-dimensional properties (need 3+ databases)
    - [ ] CHOICE: Natural bounded categories
    
- [ ] **Step 2: Called `list_databases()` to understand capabilities**
  - [ ] Reviewed descriptions for entity types and cross-references
  - [ ] Identified integration opportunities
  - [ ] **Verified databases support selected question type**
  
- [ ] **Step 3: Selected 2-3 target databases based on:**
  - [ ] Type compatibility (e.g., SUMMARY needs 3+ databases for aggregation)
  - [ ] Complementary domains (mix entity types, not all protein-centric)
  - [ ] Cross-reference opportunities (shared identifiers)
  - [ ] Coverage tracker needs (prioritize under-used from Step 1)
  - [ ] Documented database_selection_strategy with type compatibility note
  
- [ ] **Step 4: Keyword selection matching TYPE and databases:**
  - [ ] Read keywords.tsv using `Filesystem:read_text_file()` (USER'S COMPUTER!)
  - [ ] **Filtered keywords FIRST by question type:**
    - [ ] YES/NO: Specific entities
    - [ ] FACTOID-count: Broad categories
    - [ ] FACTOID-lookup: Specific entities
    - [ ] LIST: Categories with 5-100 members
    - [ ] SUMMARY: Complex multi-dimensional systems
    - [ ] CHOICE: Categorical concepts
  - [ ] **Filtered keywords SECOND by database capabilities**
  - [ ] Removed already-used keywords (from coverage tracker)
  - [ ] Random selection from filtered pool (not browsing for topics)
  - [ ] Called get_MIE_file() for *ALL* selected databases
  - [ ] Question NOT inventory/metadata
  - [ ] Classified: Comprehensive vs Example-based vs Specific-entity

### STRUCTURED VOCABULARY DISCOVERY (MANDATORY)
- [ ] Identified ALL biological/chemical concepts
- [ ] For EACH: Determined concept type
- [ ] For EACH: Called appropriate tool:
  - [ ] Function/process/component → `OLS4:searchClasses(ontologyId=go)`
  - [ ] Disease → `OLS4:searchClasses(ontologyId=mondo)` or `search_mesh_descriptor()`
  - [ ] Chemical/drug → `OLS4:searchClasses(ontologyId=chebi)` or `search_chembl_molecule()`
  - [ ] Pathway → `search_reactome_entity()`
  - [ ] Enzyme → GO + EC check
- [ ] If ontology term found: Called `OLS4:getDescendants()` if applicable
- [ ] Documented: ALL IRIs (parent + ALL descendants)
- [ ] ✓ CHECKPOINT 1: Discovered N terms → Using N terms in VALUES
- [ ] Designed queries using ALL IRIs (not text search)
- [ ] If text search: DOCUMENTED why no structured term

### GATES (BOTH MUST PASS)
- [ ] Training test: Can't answer from memory (requires current DB state)
- [ ] PubMed test: Can't answer from literature (≥2 queries, examined abstracts)

### DISCOVERY
- [ ] Called keyword search tools to discover entities
- [ ] ✓ CHECKPOINT 3: Applied decision tree - question scope = query scope?
- [ ] Executed SPARQL using structured IRIs from vocab check
- [ ] If comprehensive: Extracted ALL IDs, verified ALL processed
- [ ] If query failed: Troubleshot without sampling

### ARITHMETIC VERIFICATION (MANDATORY FOR ALL AGGREGATIONS)
- [ ] **Identified if query uses GROUP BY or categorical counting**
- [ ] **✓ CHECKPOINT A: Pre-filter entity count verification (if filtering)**
  - [ ] If filtering entities: Total = Filtered + Remaining?
  - [ ] Documented filter criteria (if any)
  - [ ] If used heuristic (ID ranges, patterns): Ran verification query
- [ ] **✓ CHECKPOINT B: Post-aggregation verification (UNIVERSAL - always for GROUP BY)**
  - [ ] Calculated sum of category counts: _______
  - [ ] Queried total unique entities: _______
  - [ ] Arithmetic check: Sum [=, >, <] Total?
  - [ ] If Sum = Total: Documented mutually exclusive categories
  - [ ] If Sum > Total: Documented overlap in ideal_answer
  - [ ] If Sum < Total: STOPPED and debugged (coverage gap!)
- [ ] Arithmetic verification documented in question file

### CATEGORIZATION PHASE (if applicable)
- [ ] **Extracted ALL entities BEFORE categorizing** (not filtered subset)
- [ ] Verified: Number of entities categorized = number discovered
- [ ] Verified: Sum of category counts = total entities
- [ ] No unverified heuristics used (taxonomy ID ranges, name patterns)

### MULTI-DATABASE INTEGRATION (if applicable)
- [ ] ✓ CHECKPOINT 4: Cross-database links use structured predicates (not exploration IDs)
- [ ] Cross-database joins use comprehensive criteria
- [ ] No pre-filtering to specific entities found during exploration

### QUESTION FORMULATION
- [ ] ✓ CHECKPOINT 5: Applied decision tree from coverage gaps section
- [ ] Question scope matches query scope (no sampling)
- [ ] Wording is precise with qualifiers
- [ ] **Question matches selected type's pattern**

### TYPE VERIFICATION (NEW - CRITICAL)
- [ ] **Question type matches pre-selected type:** _______
- [ ] **Type-specific requirements met:**
  - [ ] YES/NO: Binary criterion, specific entity, EXISTS/absence check
  - [ ] FACTOID: Countable property OR retrievable attribute
  - [ ] LIST: Verifiable scope (5-100 items) OR top-N justified
  - [ ] SUMMARY: 2-4 aggregation dimensions, 3+ databases, single paragraph
  - [ ] CHOICE: Natural bounded categories OR explicit list (3-6 items)
- [ ] **Type hard cap check:** This type has <12 uses?
- [ ] **Type priority check:** If other types <8, is this type also <10?

### VALIDATION (CRITICAL)
**Attempt to ANSWER THE QUESTION from PubMed:**
- [ ] Called PubMed:search_articles with ≥2 queries (or ncbi_esearch + ncbi_efetch)
- [ ] Queries attempted to ANSWER (not validate topic importance)
- [ ] Examined abstracts
- [ ] Scored RDF Necessity: 0-1=REJECT, 2=borderline, 3=PASS

### FINAL PRE-SAVE VERIFICATION
- [ ] **DATA COVERAGE GAP CHECK using decision tree:**
  - [ ] Discovered entities during exploration? (YES/NO)
  - [ ] If YES: Question asks about (A) specific entity or (B) all/which/how many?
  - [ ] If (A): VALID - proceed
  - [ ] If (B): Query processes (A) ALL entities or (B) SUBSET?
  - [ ] If ALL: VALID - proceed | If SUBSET: COVERAGE GAP - rewrite
- [ ] **ARITHMETIC VERIFICATION PASSED:**
  - [ ] ✓ Checkpoint A: Pre-filter counts match (if applicable)
  - [ ] ✓ Checkpoint B: Sum verified against total (for ALL GROUP BY)
- [ ] ✓ CHECKPOINT 6: Review all 6 checkpoints passed
- [ ] Score ≥9/12, no zeros
- [ ] Vocabulary completeness: Discovered N = Used N (for comprehensive queries)
- [ ] Documented structured vocab check in YAML
- [ ] **TYPE DISTRIBUTION CHECK:**
  - [ ] This type now at _____ uses (must be ≤12)
  - [ ] No type >12 after this question
  - [ ] If at question 26+: Types <8 being prioritized?
- [ ] **Updated coverage_tracker.yaml using `Filesystem:write_file()` (USER'S COMPUTER!)**
  - [ ] Updated question_type_usage counts
  - [ ] Updated type_status categories
  - [ ] Updated database_usage counts
- [ ] Multi-DB ≥60%, UniProt ≤70%, all DBs ≥1x
- [ ] **READ QUESTION_FORMAT.md using `Filesystem:read_text_file()` (USER'S COMPUTER!)**
- [ ] **FORMAT CHECK:**
  - [ ] choice: exact_answer is array (even for single answer)
  - [ ] summary: exact_answer is empty string, ideal_answer is single paragraph
  - [ ] SPARQL: All queries have query_number, database, description, query, result_count
  - [ ] RDF: All triples have comments in format `# Database: X | Query: N | Comment: ...`

---

## ⚠️ COMMON PITFALLS (Top 20)

1. **Vocabulary sampling** - Using 8/36 discovered GO terms (missing 33% of data)
2. **Misunderstanding validation** - Use PubMed to ANSWER question, not validate topic
3. **Confusing exploration with sampling** - Discovering entities is required; sampling them is prohibited
4. **Misclassifying types** - "How many/Which have" = comprehensive (not example-based)
5. **Skipping vocab check** - Text search before checking GO/EC/MeSH/ChEBI
6. **Not getting descendants** - Found GO term but didn't call getDescendants()
7. **Famous facts** - Avoid TP53, BRCA1, insulin (use less-known specifics)
8. **VALUES for comprehensive** - Never use VALUES from search for counts/"which have"
9. **Vague wording** - Avoid "bind", "contain", "have" without qualifiers
10. **Database post-selection** - Choosing databases based on where you found results
11. **Inventory questions** - Focus on biology, not DB structure
12. **Wrong exact_answer format** - choice must be array, summary must be empty string
13. **Missing SPARQL metadata** - Forgot query_number, database, description, or result_count
14. **RDF triples without comments** - Every triple needs `# Database: X | Query: N | Comment: ...`
15. **Incomplete entity extraction before categorization** - Filtering entities without verification
    - **EXAMPLE:** Discovered 19 organisms → "Eyeballed" 10 plants using ID ranges → Missing 2 plants → Wrong counts (30≠35)
    - **PREVENTION:** Always verify: sum = total | Never use unverified heuristics
16. **Skipping arithmetic verification for GROUP BY queries** - Used GROUP BY but didn't verify sum=total
    - **EXAMPLE:** Counted by inflammasome type (8+6+3+3+2+1=23) but never checked unique count (15)
    - **IMPACT:** Failed to discover 8 shared proteins, incomplete biological understanding
    - **PREVENTION:** MANDATORY arithmetic check for ALL aggregations (GROUP BY, categorical counts)
17. **Using wrong tools for user's files** - Using `view()` or `bash_tool()` instead of `Filesystem:read_text_file()`
    - **EXAMPLE:** Tried `view("/Users/arkinjo/.../keywords.tsv")` → File not found error
    - **CAUSE:** keywords.tsv is on USER'S computer, not Claude's computer
    - **PREVENTION:** ALWAYS use `Filesystem:read_text_file()` for files in /Users/arkinjo/
18. **Keyword-first workflow** - Selecting random keyword first, then forcing databases to fit
    - **PROBLEM:** Random keyword (e.g., "melanoma") → Force UniProt+GO → Weak disease integration
    - **CORRECT:** Read coverage_tracker → list_databases() → Select databases (e.g., MONDO+ClinVar+ChEMBL) → Filter to disease keywords → Random from filtered
    - **RESULT:** Natural multi-database questions with strong biological integration, prioritizing under-used databases
19. **Unfiltered keyword pool** - Using all keywords without filtering to database capabilities
    - **EXAMPLE:** Selected Reactome+GO+UniProt but randomly chose "aspirin" (compound, not pathway/process)
    - **PREVENTION:** Filter keywords to match database types BEFORE random selection
20. **Type selection after exploration** - Letting question type emerge from data instead of selecting first
    - **PROBLEM:** Explored keyword → found interesting data → defaulted to LIST (15th consecutive)
    - **CORRECT:** Check type usage → Need SUMMARY (2 uses) → Select type first → Choose databases for multi-dimensional aggregation → Filter to appropriate keywords
    - **RESULT:** Enforced 10 questions per type (±2), balanced distribution

---

## 📁 FILE FORMAT REQUIREMENTS

**⚠️ MANDATORY: Read QUESTION_FORMAT.md before saving any question file**

**Critical Format Rules:**

1. **exact_answer format by type:**
   - `yes_no`: `"yes"` or `"no"` (string)
   - `factoid`: Single value (string or number)
   - `list`: Array of items (even for single item)
   - `choice`: **Array** (even for single answer) - items must exist in choices field
   - `summary`: Empty string `""`

2. **YAML structure:**
   - Use `|` for multi-line strings (SPARQL queries, RDF triples, ideal_answer)
   - No tabs, only spaces for indentation
   - All required fields present in correct order

3. **SPARQL queries structure:**
   ```yaml
   sparql_queries:
     - query_number: 1
       database: uniprot
       description: What this query does
       query: |
         PREFIX up: <http://purl.uniprot.org/core/>
         SELECT ...
       result_count: 42
   ```

4. **RDF triples format:**
   - Valid Turtle syntax
   - Every triple followed by comment: `# Database: X | Query: N | Comment: ...`

5. **Common errors to avoid:**
   - ❌ choice exact_answer as string → ✅ Must be array
   - ❌ summary exact_answer with text → ✅ Must be empty string
   - ❌ ideal_answer with line breaks (summary) → ✅ Single paragraph
   - ❌ Missing query_number in SPARQL → ✅ Sequential numbering
   - ❌ RDF triples without comments → ✅ All triples commented

**File Locations:**

⚠️ **ALL FILES ARE ON USER'S COMPUTER - Use Filesystem tools ONLY**

```
FORMAT:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/QUESTION_FORMAT.md         ← USER'S COMPUTER!
Input:   /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv               ← USER'S COMPUTER!
Track:   /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml  ← USER'S COMPUTER!
Output:  /Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml      ← USER'S COMPUTER!
```

**Tools by Computer:**

**USER'S COMPUTER (use Filesystem tools):**
- Reading files: `Filesystem:read_text_file(path)`
- Writing files: `Filesystem:write_file(path, content)`
- Files: keywords.tsv, coverage_tracker.yaml, question_XXX.yaml, QUESTION_FORMAT.md
- **NEVER use `view()` or `bash_tool()` for these files - they operate on Claude's computer!**

**CLAUDE'S COMPUTER (use togomcp_local/OLS4 tools):**
- RDF databases: `togomcp_local:get_MIE_file()` / `run_sparql()` / `search_*_entity()` / `ncbi_esearch()`
- Ontologies: `OLS4:searchClasses()` / `OLS4:getDescendants()` / `OLS4:getAncestors()`
- Validation: `PubMed:search_articles()` or `ncbi_esearch(database=pubmed)` + `ncbi_efetch()`

---

## 🎯 CRITICAL REMINDERS

- **TYPE-FIRST WORKFLOW (5 steps - MANDATORY ORDER):**
  0. Read coverage_tracker → Select under-represented question type (check question_type_usage)
  1. Select databases compatible with that type (SUMMARY needs 3+, others 2-3)
  2. Call list_databases() to verify capabilities
  3. Filter keywords to type AND databases (type filter FIRST, then database filter)
  4. Design question following type-specific pattern
- **Type selection is FIRST STEP:** Must happen before database/keyword selection
- **Type enforcement is MANDATORY:** Hard caps (no type >12), priority for types <8
- **keywords.tsv is on USER'S COMPUTER:** ALWAYS use `Filesystem:read_text_file()`, NEVER use `view()` or `bash_tool()`
- **Arithmetic verification is MANDATORY for ALL aggregations:** Every GROUP BY, categorical count, or distribution query requires sum verification; sum≠total indicates either entity overlap (valid if documented) or missing data (coverage gap requiring immediate debug)
- Never use filtering heuristics (ID ranges, name patterns, manual selection) without verification queries to confirm completeness
- Comprehensive queries must process ALL discovered entities; never sample for "which have", "how many", counts, or summaries
- Check structured vocabulary (GO/MONDO/ChEBI/etc.) BEFORE text search; use IRIs not bif:contains
- Database selection must be based on type requirements and biological domain, not where you found results during exploration
- Question scope must equal query scope; "which order has most" requires checking ALL orders
- Read QUESTION_FORMAT.md (using Filesystem:read_text_file) for exact_answer format rules before saving

---

## VERSION HISTORY

- **v5.5.0** (2026-02-17): TYPE-FIRST EDITION - Major revision to enforce 10 questions per type. Added "QUESTION TYPE REQUIREMENTS" section with hard caps (8-12) and priority triggers. Added "TYPE-DRIVEN QUESTION DESIGN" section with patterns for all 5 types. Completely restructured workflow to TYPE → DATABASE → KEYWORD order (previously database-first). Updated PRE-WORKFLOW to 5 steps (Step 0: type selection). Added type verification checklist. Updated all sections to reference type-first approach. Added pitfall #20. Updated REQUIRED/PROHIBITED lists with type enforcement rules. Updated CRITICAL REMINDERS with type-first workflow. Coverage tracker now tracks question_type_usage and type_status.
- **v5.4.0** (2026-02-17): WORKFLOW REORDER - Major revision to workflow: Database selection → Keyword selection → Question development (previously keyword-first). Added "DATABASE SELECTION STRATEGY" section with 4-step process. Updated PRE-WORKFLOW checklist, REQUIRED/PROHIBITED lists; added pitfalls #18-19; updated CRITICAL REMINDERS
- **v5.3.5** (2026-02-17): FILE TOOLS - Added prominent warnings throughout guide that keywords.tsv is on USER'S computer; emphasized use of Filesystem tools vs view/bash; added pitfall #18; updated all file-related sections with explicit computer location warnings
- **v5.3.4** (2026-02-16): UNIVERSALITY - Reframed arithmetic verification as universal for ALL aggregations (not just filtering); expanded Checkpoint B with three outcomes; added explicit GROUP BY triggers; added pitfall #17
- **v5.3.3** (2026-02-16): ARITHMETIC - Added "Mandatory Arithmetic Verification" section; enhanced decision tree with pre-categorization checkpoint; added real Question 6 example; added pitfall #16
- **v5.3.2** (2026-02-16): CLARITY - Added decision tree for valid exploration vs. coverage gaps; clarified "reverse engineering"; revised Checkpoints 2, 5; added specific-entity examples; updated pitfall #3
- **v5.3.1** (2026-02-16): Added "FILE FORMAT REQUIREMENTS" section with QUESTION_FORMAT.md compliance checklist; added format validation to workflow; expanded common pitfalls to 15
- **v5.3.0** (2026-02-16): Added "Intentional Narrowing" section to distinguish legitimate scope narrowing from coverage gaps
- **v5.2.3** (2026-02-15): Added mandatory `list_databases()` call; Added comprehensive data coverage gap check before saving
- **v5.2.2** (2026-02-15): Added 6 data coverage gap checkpoints at decision points
- **v5.2.1** (2026-02-15): CONCISE - Condensed from 765→263 lines
- **v5.2.0** (2026-02-15): Added comprehensive Structured Vocabulary Discovery section
