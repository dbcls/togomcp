# TogoMCP Question Design Guide

**Purpose**: Guide for creating high-quality evaluation questions that effectively test TogoMCP's database access capabilities.

**For**: Question authors and evaluation designers  
**Not for**: Manual scoring (see automated evaluation in `scripts/`)

---

## Quick Reference

**Good evaluation questions**:
- ✅ Test what Claude **can't** answer without database access
- ✅ Have verifiable, specific expected answers
- ✅ Are realistic questions researchers would ask
- ✅ Match one of the six question categories

**See existing questions**: `questions/Q01.json` through `questions/Q10.json` (120 examples)

---

## Question Quality Checklist

Before adding a question to your evaluation set, verify:

### ✅ **Biologically Realistic**
Would an actual researcher ask this question?

**Good examples** (from our question set):
- ❌ "Tell me about proteins" (too vague)
- ✅ "What is the UniProt ID for human BRCA1?" (specific, practical)
- ❌ "List everything in UniProt" (impossibly broad)
- ✅ "How many human proteins have signal peptides?" (reasonable scope)

**Ask yourself**:
- Would this come up in actual research?
- Is it solving a real problem?
- Would the answer be useful?

---

### ✅ **Testable Distinction**
Can you tell if the answer used databases vs baseline knowledge?

**Key indicators of database dependency**:
- **Exact IDs**: "What is the UniProt ID..." (baseline won't know specific IDs)
- **Current counts**: "How many variants are in ClinVar?" (baseline data is frozen)
- **Specific values**: "What is the molecular weight of compound X?" (requires lookup)
- **Recent data**: "What SARS-CoV-2 pathways are in Reactome?" (post-training cutoff)

**Good examples**:
- ✅ "What is the PubChem CID for aspirin?" → Database gives: 2244
- ✅ "How many descendants does GO:0006914 have?" → Database gives: 25
- ✅ "What is the ChEBI ID for ATP?" → Database gives: CHEBI:30616

**Questions to avoid**:
- ❌ "What does BRCA1 do?" → Baseline can answer from training
- ❌ "What is a kinase?" → General knowledge, no database needed
- ❌ "Why is DNA repair important?" → Conceptual, not database-specific

---

### ✅ **Appropriate Complexity**
Not too simple, not impossibly broad.

**Too simple** (baseline can answer):
- ❌ "What is DNA?"
- ❌ "Name a protein database"
- ❌ "What does UniProt stand for?"

**Just right** (requires database, achievable):
- ✅ "What is the UniProt accession for SpCas9 from S. pyogenes M1?"
- ✅ "How many human genes are annotated with GO:0006281?"
- ✅ "What is the highest resolution structure in PDB?"

**Too broad** (would timeout or be overwhelming):
- ❌ "List all proteins in UniProt"
- ❌ "Give me every compound in PubChem"
- ❌ "What are all the pathways in Reactome?"

**Rule of thumb**:
- Single entity lookups: ✅ Good
- Filtered counts (< 10,000): ✅ Good
- Exhaustive lists of major categories: ✅ Good
- Unlimited dumps: ❌ Too broad

---

### ✅ **Clear Success Criteria**
You can objectively verify if the answer is correct.

**Verifiable answers**:
- ✅ Specific IDs: "P38398" (can check UniProt)
- ✅ Exact counts: "25 descendants" (can verify with query)
- ✅ Molecular properties: "180.16 g/mol" (can look up)
- ✅ Boolean facts: "Yes, it's in the database" (can confirm)

**Hard to verify**:
- ❌ Explanations: "BRCA1 is important because..." (subjective)
- ❌ Opinions: "The best database is..." (no ground truth)
- ❌ Predictions: "This will likely..." (not verifiable)

**Best practice**: Include `expected_answer` field in your question JSON:

```json
{
  "question": "What is the UniProt ID for human BRCA1?",
  "expected_answer": "P38398"
}
```

The automated evaluation checks if the response contains this expected answer.

---

## The Six Question Categories

Design at least 3-5 questions per category for balanced coverage.

### 1. **Precision Questions**

**Purpose**: Test ability to retrieve exact, specific data

**What they test**:
- Database ID lookups
- Exact molecular properties
- Specific sequences or values
- Precise measurements

**Examples from our question set**:

```
Q1: "What is the UniProt accession ID for SpCas9 from 
     Streptococcus pyogenes M1?"
Expected: Q99ZW2

Q15: "What is the PubChem Compound ID (CID) for aspirin?"
Expected: 2244

Q39: "What is the highest resolution ever achieved for a 
      structure in the PDB?"
Expected: 0.48 Å

Q51: "What is the MeSH descriptor ID for Diabetes Mellitus, 
      Type 2?"
Expected: D003924
```

**Key characteristics**:
- One specific, verifiable answer
- Requires exact database lookup
- Baseline can't provide specific IDs/values
- Clear success: answer matches or doesn't

**Good question starters**:
- "What is the [database] ID for..."
- "What is the exact [property] of..."
- "What is the [measurement] for..."

---

### 2. **Completeness Questions**

**Purpose**: Test ability to retrieve exhaustive or comprehensive data

**What they test**:
- Counting entries matching criteria
- Listing all members of a set
- Comprehensive enumeration
- Systematic coverage

**Examples from our question set**:

```
Q2: "How many descendant terms does GO:0006914 (autophagy) 
     have in the Gene Ontology?"
Expected: 25

Q14: "How many single nucleotide variants (SNVs) are recorded 
      in ClinVar?"
Expected: 3,236,823

Q26: "How many compounds in PubChem are FDA-approved drugs?"
Expected: ~4000 (verify current count)

Q74: "How many bacterial strains in BacDive can grow at 
      temperatures above 70°C?"
Expected: Count from query
```

**Key characteristics**:
- Quantitative answer (count or list)
- Requires systematic search
- Baseline might estimate but can't give exact count
- Clear success: correct count/complete list

**Good question starters**:
- "How many [entities] are in [database]..."
- "List all [things] that match [criteria]..."
- "What is the total count of..."
- "How many [X] have [property]..."

---

### 3. **Integration Questions**

**Purpose**: Test cross-database linking and ID conversion

**What they test**:
- Converting IDs between databases
- Finding related entries across databases
- Linking entities through relationships
- Multi-database workflows

**Examples from our question set**:

```
Q3: "What is the NCBI Gene ID for the protein with UniProt 
     accession P04637?"
Expected: 7157 (TP53)

Q27: "What is the ChEBI ID for ATP as referenced in Rhea 
      reactions?"
Expected: CHEBI:30616

Q63: "Convert the Ensembl gene ID ENSG00000012048 to its 
      corresponding NCBI Gene ID"
Expected: 672 (BRCA1)

Q99: "What is the UniProt ID for the protein encoded by mouse 
      gene with NCBI Gene ID 11461?"
Expected: P10107 (Anxa1)
```

**Key characteristics**:
- Requires cross-database navigation
- Tests ID conversion capabilities
- Baseline has limited cross-reference knowledge
- Clear success: correct corresponding ID

**Good question starters**:
- "Convert [database A] ID to [database B] ID..."
- "What is the [database] ID for [entity in other database]..."
- "Find the corresponding [ID type] for..."
- "Link [entity] from [database A] to [database B]..."

**Databases that link well** (from exploration):
- UniProt ↔ NCBI Gene
- PubChem ↔ ChEBI
- ChEMBL ↔ UniProt
- ClinVar ↔ MedGen
- Ensembl ↔ NCBI Gene

---

### 4. **Currency Questions**

**Purpose**: Test access to recent or time-sensitive information

**What they test**:
- Recently added entries
- Current status/classifications
- Latest updates
- Post-training-cutoff data

**Examples from our question set**:

```
Q4: "When was the BRCA1 variant c.5266dup last updated in 
     ClinVar?"
Expected: Recent date (2025-05-25)

Q28: "How many structures related to CRISPR Cas9 are currently 
      in the PDB?"
Expected: 461 (current count)

Q40: "What pathways in Reactome involve SARS-CoV-2 proteins?"
Expected: List of COVID-related pathways

Q88: "How many articles about mRNA vaccines are indexed in 
      PubMed as of 2024?"
Expected: Current count
```

**Key characteristics**:
- Time-dependent information
- May change as databases update
- Baseline knowledge frozen at training cutoff (Jan 2025)
- Clear success: current/recent data provided

**Good question starters**:
- "When was [entity] last updated in..."
- "How many [recent topic] entries are in..."
- "What [current status] is recorded for..."
- "As of [current year], how many..."

**Note**: Claude's training cutoff is January 2025, so anything after that is clearly demonstrating currency.

---

### 5. **Specificity Questions**

**Purpose**: Test ability to find niche or specialized information

**What they test**:
- Rare diseases or conditions
- Specialized organisms
- Uncommon compounds
- Domain-specific terminology

**Examples from our question set**:

```
Q5: "What is the MeSH descriptor ID for Erdheim-Chester 
     disease?"
Expected: D031249

Q17: "What is the NANDO identifier for Parkinson's disease 
      (Japanese rare disease database)?"
Expected: NANDO:1200010

Q53: "What is the strain number for Thermotoga maritima in 
      BacDive?"
Expected: DSM 3109

Q89: "What culture medium does BacDive recommend for growing 
      Methanococcus jannaschii?"
Expected: Specific medium from MediaDive
```

**Key characteristics**:
- Niche topics or rare entities
- Specialized databases (NANDO, BacDive, MediaDive)
- Baseline unlikely to know specifics
- Tests depth of database coverage

**Good question starters**:
- "What is the [database] ID for [rare entity]..."
- "Find information about [niche organism/compound]..."
- "What specialized [property] does [uncommon entity] have..."
- "In [specialized database], what is..."

**Databases good for specificity**:
- NANDO: Japanese rare diseases
- BacDive: Bacterial strains
- MediaDive: Culture media recipes
- MeSH: Medical terminology
- GlyCosmos: Glycoscience

---

### 6. **Structured Query Questions**

**Purpose**: Test ability to handle complex, multi-step queries

**What they test**:
- Filtering by multiple criteria
- Complex SPARQL-like queries
- Multi-step reasoning
- Combining constraints

**Examples from our question set**:

```
Q6: "Find ChEMBL molecules with IC50 values less than 100 nM 
     against any kinase target"
Expected: List of compounds with IDs

Q30: "Search the Gene Ontology for terms in the 
      biological_process namespace that contain 'DNA repair'"
Expected: List of GO terms

Q54: "Find all UniProt entries for human proteins that are 
      kinases AND have associated ChEMBL bioactivity data"
Expected: List of protein IDs

Q102: "What Rhea reactions involve both ATP and ADP, and are 
       classified as transport reactions?"
Expected: List of reaction IDs
```

**Key characteristics**:
- Multiple constraints (AND/OR logic)
- Requires filtering or complex queries
- May need multiple tool calls
- Tests SPARQL/database query capabilities

**Good question starters**:
- "Find all [entities] that [condition 1] AND [condition 2]..."
- "Search for [things] matching [complex criteria]..."
- "Filter [database] for entries with [property X] < [value] AND [property Y]..."
- "List [entities] that participate in [process] AND have [characteristic]..."

**Complexity levels**:
- Simple: One filter ("IC50 < 100 nM")
- Medium: Two filters ("kinases AND IC50 < 100 nM")
- Complex: Three+ filters or multi-database ("human kinases WITH ChEMBL data AND FDA approval")

---

## Question Format

### JSON Structure

Each question should follow this format:

```json
{
  "id": 1,
  "category": "Precision",
  "question": "What is the UniProt ID for human BRCA1?",
  "expected_answer": "P38398",
  "notes": "Tests basic UniProt ID lookup. Baseline cannot provide 
           specific database IDs. Verified in uniprot_exploration.md 
           using search_uniprot_entity tool."
}
```

### Required Fields

- **`question`** (string): Natural language question
  - Use clear, direct phrasing
  - Avoid mentioning "SPARQL" or "MCP tools"
  - Write as a researcher would ask

- **`expected_answer`** (string): Verifiable answer
  - Specific enough to validate automatically
  - Should appear in the correct response
  - Can be ID, number, term, etc.

### Recommended Fields

- **`id`** (number): Unique sequential identifier
- **`category`** (string): One of the six categories
- **`notes`** (string): Design rationale
  - Which database(s) are involved
  - Reference to exploration report findings
  - Why this requires database access
  - How answer was verified

### Optional Fields

- **`organism`** (string): Target organism (human, mouse, etc.)
- **`databases`** (array): Which databases are involved
- **`difficulty`** (string): simple, medium, complex

---

## Design Process

### Step 1: Identify Database Capability

Start with database exploration reports:

```bash
# Review database capabilities
cat exploration/00_SUMMARY.md

# Deep dive on specific database
cat exploration/uniprot_exploration.md
```

Look for:
- Unique data this database provides
- Search tool examples that work well
- SPARQL queries that retrieve interesting data
- Cross-references to other databases

### Step 2: Choose Question Category

Pick which of the six categories this tests:
- **Precision**: Specific ID or value?
- **Completeness**: Count or exhaustive list?
- **Integration**: Cross-database linking?
- **Currency**: Recent or updated data?
- **Specificity**: Niche or rare entity?
- **Structured Query**: Complex filtering?

### Step 3: Draft Question

Write in natural language:
- Be specific and concrete
- Include necessary context (organism, database, criteria)
- Avoid technical jargon about SPARQL/MCP
- Make it sound like a real research question

### Step 4: Determine Expected Answer

Verify the answer exists:
- Run the query yourself (use exploration tools)
- Confirm the answer is stable/verifiable
- Note where you found it (for documentation)

### Step 5: Validate Against Checklist

Check all four criteria:
- ✅ Biologically realistic?
- ✅ Testable distinction?
- ✅ Appropriate complexity?
- ✅ Clear success criteria?

### Step 6: Document in JSON

Add to appropriate question file (Q01-Q10.json):

```json
{
  "id": 121,
  "category": "Precision",
  "question": "Your question here",
  "expected_answer": "Verified answer",
  "notes": "Database: uniprot. Found via search_uniprot_entity. 
           Tests exact ID lookup vs baseline which cannot provide 
           specific database accessions. Verified in 
           uniprot_exploration.md."
}
```

---

## Common Pitfalls to Avoid

### ❌ **Questions Baseline Can Answer**

Bad:
- "What is BRCA1?" → Baseline knows from training
- "What does UniProt do?" → General knowledge
- "Why is DNA repair important?" → Conceptual

Good:
- "What is the UniProt ID for BRCA1?" → Requires database
- "How many entries are in UniProt?" → Current count needed
- "What is the GO ID for DNA repair?" → Specific ID needed

---

### ❌ **Ambiguous Questions**

Bad:
- "Tell me about aspirin" → Too vague
- "Find some kinases" → How many? Which type?
- "What pathways exist?" → In which database? All of them?

Good:
- "What is the PubChem CID for aspirin?" → Specific
- "How many human kinases are in UniProt?" → Clear scope
- "What Reactome pathways involve BRCA1?" → Clear database and entity

---

### ❌ **Impossible to Verify**

Bad:
- "Is UniProt the best protein database?" → Opinion
- "Will this protein be important?" → Prediction
- "Explain the significance of..." → Subjective

Good:
- "Is Q99ZW2 the UniProt ID for SpCas9?" → Boolean, verifiable
- "What is the function annotation for..." → Database field, verifiable
- "What GO terms are associated with..." → List, verifiable

---

### ❌ **Too Technical**

Bad:
- "Write a SPARQL query to find..." → Implementation detail
- "Use the MCP tool to..." → Too specific
- "Query the RDF endpoint for..." → Technical jargon

Good:
- "How many proteins in UniProt have..." → Natural language
- "Find all compounds that..." → Clear intent
- "What is the [property] of..." → Direct question

---

## Validation Before Running

### Use the Validator

```bash
cd scripts
python validate_questions.py ../questions/your_questions.json
```

Checks:
- ✅ Valid JSON syntax
- ✅ Required fields present
- ✅ Valid categories
- ✅ No duplicate questions
- ✅ Reasonable question length

### Estimate Cost

```bash
python validate_questions.py ../questions/your_questions.json --estimate-cost
```

Shows approximate API cost before running full evaluation.

---

## How Automated Evaluation Works

After you create questions, the automated system:

### 1. **Baseline Test**
Runs question without MCP tools:
```
"Answer using only your training knowledge. 
Do not use any database tools. 
[Your question]"
```

### 2. **TogoMCP Test**
Runs question with MCP tools enabled:
```
[Your question]
```
(Claude automatically uses available MCP tools)

### 3. **Comparison**
Checks:
- Does response contain `expected_answer`?
- Which MCP tools were used?
- Response time and token usage
- Success vs failure patterns

### 4. **Value-Add Assessment**
Automatically categorizes:
- **CRITICAL**: Baseline failed, TogoMCP succeeded
- **VALUABLE**: Both answered, TogoMCP much better
- **MARGINAL**: Minor improvement only
- **REDUNDANT**: No meaningful difference

### 5. **Results**
Generates:
- CSV with all metrics
- Statistical analysis
- Interactive dashboard
- Identified high-value questions

**See**: [`scripts/README.md`](scripts/README.md) for details on running evaluations.

---

## Examples from Existing Questions

### Example 1: Precision Question

```json
{
  "id": 1,
  "category": "Precision",
  "question": "What is the UniProt accession ID for SpCas9 from 
               Streptococcus pyogenes M1 GAS?",
  "expected_answer": "Q99ZW2",
  "notes": "Database: UniProt. Tests exact protein ID lookup. 
           Baseline cannot provide specific UniProt accessions. 
           Found via search_uniprot_entity('SpCas9 Streptococcus 
           pyogenes'). Verified in uniprot_exploration.md."
}
```

**Why it's good**:
- ✅ Specific organism strain mentioned
- ✅ Exact ID requested (Q99ZW2)
- ✅ Baseline won't know this specific accession
- ✅ Easily verifiable in UniProt

---

### Example 2: Completeness Question

```json
{
  "id": 2,
  "category": "Completeness",
  "question": "How many descendant terms does GO:0006914 
               (autophagy) have in the Gene Ontology?",
  "expected_answer": "25",
  "notes": "Database: GO (Gene Ontology). Tests hierarchical 
           navigation using getDescendants. Baseline cannot 
           enumerate exact descendant counts. Requires database 
           query to get complete list. Verified via 
           getDescendants(GO:0006914)."
}
```

**Why it's good**:
- ✅ Requires systematic enumeration
- ✅ Exact count needed (25)
- ✅ Baseline might estimate but can't give exact count
- ✅ Tests database hierarchy navigation

---

### Example 3: Integration Question

```json
{
  "id": 3,
  "category": "Integration",
  "question": "What is the NCBI Gene ID for the protein with 
               UniProt accession P04637?",
  "expected_answer": "7157",
  "notes": "Database: UniProt, NCBI Gene. Tests ID conversion 
           between databases. P04637 is TP53 (tumor protein p53). 
           Baseline has limited cross-reference knowledge. Requires 
           TogoID or direct cross-reference lookup. Verified in 
           uniprot_exploration.md."
}
```

**Why it's good**:
- ✅ Clear cross-database conversion
- ✅ Specific IDs in both systems
- ✅ Tests integration capability
- ✅ Easily verified in either database

---

### Example 4: Currency Question

```json
{
  "id": 4,
  "category": "Currency",
  "question": "When was the BRCA1 variant c.5266dup (also known 
               as 5382insC) last updated in ClinVar?",
  "expected_answer": "2025-05-25",
  "notes": "Database: ClinVar. Tests access to current database 
           metadata. Update dates are beyond training cutoff and 
           require live database access. This is a well-known 
           pathogenic variant. Verified in clinvar_exploration.md 
           via get_article_metadata on ClinVar entries."
}
```

**Why it's good**:
- ✅ Time-sensitive information
- ✅ Post-training cutoff data (2025-05-25)
- ✅ Baseline frozen at Jan 2025
- ✅ Demonstrates currency value

---

### Example 5: Specificity Question

```json
{
  "id": 5,
  "category": "Specificity",
  "question": "What is the MeSH descriptor ID for Erdheim-Chester 
               disease?",
  "expected_answer": "D031249",
  "notes": "Database: MeSH. Tests retrieval of rare disease 
           terminology. Erdheim-Chester is a rare histiocytic 
           disorder. Baseline unlikely to know specific MeSH ID 
           for this rare condition. Verified via 
           search_mesh_entity('Erdheim-Chester'). Found in 
           mesh_exploration.md."
}
```

**Why it's good**:
- ✅ Rare disease (niche topic)
- ✅ Specific terminology database (MeSH)
- ✅ Baseline unlikely to know this ID
- ✅ Tests depth of specialized knowledge

---

### Example 6: Structured Query Question

```json
{
  "id": 6,
  "category": "Structured Query",
  "question": "Find ChEMBL molecules with IC50 values less than 
               100 nM against any kinase target",
  "expected_answer": "List of ChEMBL IDs (e.g., CHEMBL25, 
                      CHEMBL98, etc.)",
  "notes": "Database: ChEMBL. Tests complex filtering with 
           multiple criteria: (1) bioactivity type = IC50, 
           (2) value < 100 nM, (3) target type = kinase. Requires 
           structured database query. Baseline cannot perform 
           such specific filtering. Verified in 
           chembl_exploration.md using search and filter examples."
}
```

**Why it's good**:
- ✅ Multiple criteria (target type + measurement + threshold)
- ✅ Requires database filtering capability
- ✅ Baseline can't perform this specific query
- ✅ Tests structured query handling

---

## Question Set Balance

### Recommended Distribution (120 questions)

- **20 questions per category** (6 categories × 20 = 120)
- **All 22 databases represented**
- **Mix of difficulty levels** (simple, medium, complex)
- **Diverse organisms** (human, model organisms, microbes)

### Current Distribution (Your Questions)

See [`questions/SUMMARY.md`](questions/SUMMARY.md) for detailed breakdown:

| Category | Count | Databases Emphasized |
|----------|-------|---------------------|
| Precision | 20 | UniProt, PubChem, PDB, MeSH |
| Completeness | 20 | GO, ClinVar, NCBI Gene, BacDive |
| Integration | 20 | UniProt↔Gene, PubChem↔ChEBI, ClinVar↔MedGen |
| Currency | 20 | ClinVar, PDB, Reactome, NCBI Gene |
| Specificity | 20 | NANDO, BacDive, MediaDive, MeSH |
| Structured Query | 20 | ChEMBL, GO, Rhea, UniProt |

---

## Tips for Success

### Start with High-Value Databases

Focus on databases with:
- Rich data (UniProt, PubChem, GO)
- Good search tools (search_uniprot_entity, search_chembl_molecule)
- Clear use cases (ClinVar for variants, PDB for structures)

**See**: [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md) for database rankings.

### Use Exploration Reports

Before writing questions:
1. Read relevant exploration report
2. Note successful search/SPARQL examples
3. Identify interesting findings
4. Verify data exists

### Test Your Questions

Before adding to evaluation set:
- Try the query yourself
- Confirm answer exists
- Verify it's stable (not changing daily)
- Check it's not in baseline knowledge

### Iterate Based on Results

After running evaluations:
- Remove REDUNDANT questions (baseline answered well)
- Keep CRITICAL questions (clear value-add)
- Refine MARGINAL questions (improve specificity)

---

## Resources

### Documentation
- **Exploration Reports**: [`exploration/`](exploration/) - Database capabilities
- **Existing Questions**: [`questions/Q01-Q10.json`](questions/) - 120 examples
- **Automated Evaluation**: [`scripts/README.md`](scripts/README.md) - Running tests
- **Project Status**: [`PROJECT_STATUS.md`](PROJECT_STATUS.md) - Current progress

### Tools
- **Validator**: `scripts/validate_questions.py` - Check question format
- **Test Runner**: `scripts/automated_test_runner.py` - Run evaluations
- **Analyzer**: `scripts/results_analyzer.py` - Analyze results

### Key Files
- **Question Summary**: [`questions/SUMMARY.md`](questions/SUMMARY.md)
- **Database Summary**: [`exploration/00_SUMMARY.md`](exploration/00_SUMMARY.md)
- **This Guide**: `QUESTION_DESIGN_GUIDE.md` (you are here)

---

## Quick Start for Question Creation

```bash
# 1. Review database capabilities
cat exploration/00_SUMMARY.md

# 2. Pick a database and review its report
cat exploration/uniprot_exploration.md

# 3. Draft your question (follow examples in questions/Q01.json)

# 4. Add to appropriate question file or create new one

# 5. Validate format
cd scripts
python validate_questions.py ../questions/your_questions.json

# 6. Test with evaluation (optional)
python automated_test_runner.py ../questions/your_questions.json

# 7. Review results
python results_analyzer.py evaluation_results.csv
```

---

**Last Updated**: 2025-12-18  
**Related**: Automated evaluation in `scripts/`, existing questions in `questions/`  
**For**: Question design and creation (not manual scoring)
