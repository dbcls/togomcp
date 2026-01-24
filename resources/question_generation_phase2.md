# TogoMCP Question Generation - Phase 2: Create 120 Questions

## Quick Reference
- **Goal**: Create 120 high-quality evaluation questions
- **Output**: 10 JSON files (Q01.json - Q10.json) with 12 questions each
- **Format**: JSON array with required fields (see validation script)
- **Distribution**: 2 questions per category per file (20 total per category)
- **Anti-Trivial**: Questions must require database queries, not just MIE reading
- **Validation**: Run `python validate_questions.py` after generation

---

## Prerequisites

**Verify exploration is complete**:
- Check for exploration reports in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
- If missing, complete Phase 1 first

**Read these files**:
- `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_SUMMARY.md`
- `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/QUESTION_FORMAT.md`
- `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/QUESTION_DESIGN_GUIDE.md`
- `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/example_questions.json`

---

## Question Requirements

### Distribution
- **120 questions total** (10 files × 12 questions)
- **2 questions per category per file** (20 total per category)
- **ALL databases represented** across 120 questions
- **1-4 databases per question**

### Expert Realism Requirement

**CRITICAL**: Questions must be ones that real biology/biomedical experts would actually ask.

Ask yourself: "Would a researcher working in genomics, drug discovery, clinical genetics, microbiology, or systems biology actually want to know this answer for their work?"

✅ **Expert-Relevant Questions** (Create These):
- Questions that support actual research workflows
- Questions that provide actionable scientific insights
- Questions that help interpret experimental/clinical data
- Questions that identify disease mechanisms or drug targets
- Questions that guide experimental design

❌ **Non-Expert Questions** (Avoid These):
- Database trivia or curiosities with no research value
- Arbitrary comparisons or rankings without scientific meaning
- Questions about alphabetical/numerical ordering of IDs
- "Fun facts" that don't advance scientific understanding
- Questions focused on database statistics rather than biology

### Categories (6 total, exactly 20 questions each)
1. **Precision**: Exact IDs, sequences, specific properties
2. **Completeness**: Counts, exhaustive lists
3. **Integration**: Cross-database linking, ID conversions
4. **Currency**: Recent updates, current classifications
5. **Specificity**: Niche organisms, rare diseases, specialized compounds
6. **Structured Query**: Complex filters, multi-step queries

---

## CRITICAL: Avoid Trivial Questions

### ❌ TRIVIAL (Don't Create These)

Questions answerable by just reading MIE files:

**Bad Examples**:
- ❌ "What is the organism for UniProt:P12345?" (P12345 is example from MIE)
- ❌ "What properties does the database schema include?" (schema info)
- ❌ "What is an example SPARQL query for this database?" (documentation)
- ❌ "How many example queries are in the MIE file?" (counting docs)
- ❌ "What namespace prefix is used for this database?" (technical metadata)
- ❌ "Show me the recommended SPARQL pattern for querying X" (asking for documentation)

**Why trivial**: Can be answered by reading documentation, not querying database.

**CRITICAL - Don't Reproduce MIE SPARQL Examples**:

❌ **BAD - Question Based on MIE Example Query**:
- MIE file shows example: "Get protein name for P12345"
- You create: "What is the protein name for UniProt:P12345?" 
- Problem: This is just testing if you read the MIE example, not if you can query real data

❌ **BAD - Question About Query Patterns**:
- "What SPARQL pattern retrieves protein names from UniProt?"
- "Show me how to query for gene information"
- Problem: These ask about HOW to query (documentation), not actual biological data

✅ **GOOD - Question Using Adapted Query on Real Entity**:
- MIE shows query pattern for getting protein names
- You adapt it to search for "SpCas9" → find Q99ZW2
- You create: "What is the UniProt ID for SpCas9?"
- Good: Uses query pattern to find real entity, asks about biological data

### ❌ VAGUE LANGUAGE (Don't Use These)

Questions with unclear or ambiguous phrasing:

**Bad Examples**:
- ❌ "How many reactions involve specific proteins?" (what does "specific" mean?)
- ❌ "What are some diseases in the database?" (vague: "some")
- ❌ "How many entries have certain properties?" (vague: "certain")
- ❌ "Which organisms are included?" (too broad without context)

**Good Alternatives**:
- ✅ "How many reactions have protein participants?" (clear what's counted)
- ✅ "How many cancer types are classified in MONDO?" (specific subset)
- ✅ "How many proteins have GO annotations?" (clear property)
- ✅ "How many bacterial species are in BacDive?" (specific organism type)

### ✅ NON-TRIVIAL (Create These)

Questions requiring actual database queries:

**Good Examples**:
- ✅ "What is the UniProt ID for human BRCA1?" (requires search/query)
- ✅ "How many kinase structures are in PDB?" (requires COUNT query)
- ✅ "What MONDO IDs map to NANDO:1200001?" (requires cross-reference lookup)
- ✅ "Find ChEMBL compounds with IC50 < 100 nM targeting EGFR" (requires filtering)
- ✅ "How many NANDO diseases have exactly 2 MONDO mappings?" (requires aggregation)

**Why non-trivial**: Requires using search tools or running SPARQL queries against real data.

### The Triviality Test

Before creating a question, ask:
1. **Can this be answered by reading the MIE file?** → If YES, it's trivial ❌
2. **Does this use entities from MIE examples (including SPARQL queries)?** → If YES, it's trivial ❌
3. **Does this ask about query patterns or documentation?** → If YES, it's trivial ❌
4. **Does this require searching or querying the database with real entities?** → If YES, it's good ✅
5. **Would someone need database access to answer this?** → If NO, it's trivial ❌

---

## Content Guidelines

### ✅ BIOLOGICAL RELEVANCE (MANDATORY)

**Ask about**:
- Biological entities: proteins, genes, diseases, compounds, organisms
- Scientific properties: sequences, structures, molecular weights, pathways
- Research findings: clinical significance, resistance patterns, expression
- Experimental results: IC50 values, resolution, binding affinities
- Methodology (only if interpretation-critical): AST methods, experimental techniques

**Expert Realism by Category**:

**Precision** - Experts need exact identifiers for:
- ✅ Key research targets: "What is UniProt ID for BRCA1?" (clinical genetics)
- ✅ Drug compounds: "What is ChEMBL ID for imatinib?" (drug development)
- ✅ Disease classification: "What is MONDO ID for Huntington's?" (rare disease research)
- ❌ "What is the 100th protein in UniProt alphabetically?" (no research value)
- ❌ "Which protein has the shortest ID?" (database trivia)

**Completeness** - Experts count to understand:
- ✅ Disease burden: "How many pathogenic BRCA1 variants in ClinVar?" (clinical relevance)
- ✅ Drug coverage: "How many kinase inhibitors in ChEMBL?" (therapeutic landscape)
- ✅ Research scope: "How many CRISPR-Cas9 structures in PDB?" (method development)
- ❌ "How many proteins have 'ase' in their name?" (word game, not biology)
- ❌ "How many database entries were added on Tuesdays?" (curiosity, not science)

**Integration** - Experts cross-reference to:
- ✅ Connect data: "What NCBI Gene ID for UniProt P04637?" (data integration)
- ✅ Find orthologs: "What mouse gene corresponds to human BRCA1?" (model organisms)
- ✅ Link pathways: "What Reactome pathways involve TP53?" (systems biology)
- ❌ "How many databases link to this database?" (infrastructure comparison)
- ❌ "What's the longest cross-reference chain?" (graph trivia)

**Currency** - Experts need current data for:
- ✅ Recent discoveries: "How many COVID-19 pathways in Reactome?" (emerging disease)
- ✅ Growing fields: "How many cryo-EM structures in PDB?" (technology adoption)
- ✅ Evolving classifications: "How many cancer subtypes in MONDO?" (nosology updates)
- ❌ "What's the newest database entry by date?" (arbitrary recency)
- ❌ "How many entries added this month?" (database activity, not biology)

**Specificity** - Experts study specialized areas:
- ✅ Rare diseases: "What is NANDO ID for Fabry disease?" (orphan drug development)
- ✅ Extremophiles: "What's the highest growth temperature in BacDive?" (biotechnology)
- ✅ Specialized chemistry: "What glycoepitope ID for Lewis a antigen?" (glycobiology)
- ❌ "What's the rarest entry in the database?" (scarcity for its own sake)
- ❌ "Which organism has the weirdest name?" (entertainment, not research)

**Structured Query** - Experts filter data to:
- ✅ Drug discovery: "Find ChEMBL compounds with IC50 < 100 nM for EGFR" (lead optimization)
- ✅ Clinical interpretation: "Find ClinVar variants with conflicting classifications" (curation)
- ✅ Research planning: "Find bacteria resistant to multiple antibiotic classes" (epidemiology)
- ❌ "Find entries where ID number is prime" (mathematical curiosity)
- ❌ "Find proteins whose name contains exactly 3 vowels" (word puzzle)

**Examples**:
- ✅ "What is the molecular weight of CHEMBL25?"
- ✅ "Which kinase inhibitors in ChEMBL have IC50 < 100 nM?"
- ✅ "What laboratory typing methods are used in AMR Portal?" (affects data accuracy)

### ❌ AVOID INFRASTRUCTURE METADATA

**Do NOT ask about**:
- Database versions/release numbers
- Software tools (unless methodology directly affects interpretation)
- Administrative metadata (update schedules, formats)
- Pure IT infrastructure
- MIE file contents or documentation structure

**Examples**:
- ❌ "What is the current version of Reactome?"
- ❌ "What software is used for structure refinement?" (unless affects results)
- ❌ "When was the database last updated?"
- ❌ "How many example queries are in the MIE file?"

### ❌ AVOID STRUCTURAL/ORGANIZATIONAL METADATA

**Do NOT ask about classification system structure**:
- Tree numbers, classification codes, hierarchy positions (ask about the actual entities instead)
- Namespace prefixes or URI patterns
- Property names or relationship types in the schema
- Organizational structure of vocabularies

**Bad Examples**:
- ❌ "What is the tree number for Diabetes Mellitus in MeSH?" (asks about classification structure)
- ❌ "What is the ICD-10 code for disease X?" (classification code, not biology)
- ❌ "What namespace prefix does UniProt use?" (technical metadata)
- ❌ "What property links proteins to structures?" (schema question)

**Good Alternatives**:
- ✅ "How many diabetes subtypes are classified in MeSH?" (asks about biological content)
- ✅ "What diseases are classified under Diabetes Mellitus in MeSH?" (asks about entities)
- ✅ "How many proteins link to PDB structures?" (asks about data, not schema)

### ⚠️ SPECIAL GUIDANCE: Currency Questions

Currency tests **recent biological data**, NOT database maintenance:
- ✅ "What COVID-19 pathways were added to Reactome in 2024?"
- ✅ "How many AMR isolates collected in 2024 are in the database?"
- ❌ "What is the current database release number?"
- ❌ "When was the MIE file last updated?"

---

## Counting Questions: Entity vs. Relationship Counts

### CRITICAL DISTINCTION

When databases have cross-references/mappings, there are TWO counts:

**Entity Count** = Unique entities WITH mappings
- Query: `COUNT(DISTINCT ?entity)`
- Example: "2,150 NANDO diseases have MONDO mappings"
- Question: "How many diseases HAVE MONDO mappings?"

**Relationship Count** = Total mapping relationships
- Query: `COUNT(?target)` (no DISTINCT)
- Example: "2,341 total NANDO→MONDO mappings"
- Question: "How many total NANDO→MONDO mapping relationships?"

**Why different?**: Some entities map to multiple targets
- NANDO:1200001 → MONDO:0010735 AND MONDO:0016113
- 1 entity, but 2 relationships

### Question Formulation

✅ **CLEAR** (explicitly state what to count):
- "How many proteins HAVE UniProt→PDB mappings?" (entity count)
- "How many total protein→structure relationships exist?" (relationship count)
- "How many diseases map to exactly 2 MONDO IDs?" (distribution query)

❌ **AMBIGUOUS** (unclear which count):
- "How many UniProt→PDB mappings?" (entities or relationships?)
- "Count the cross-references" (which count?)

### Answer Format for Counting Questions

Always clarify which count:
- Entity: "2,150 diseases have mappings"
- Relationship: "2,341 total mapping relationships"
- In notes: Explain if counts differ and why

---

## JSON Format Specification

### ⚠️ CRITICAL: Use ARRAY Format

**CORRECT** ✅:
```json
[
  {
    "id": 1,
    "category": "Precision",
    "question": "What is the UniProt ID for human BRCA1?",
    "expected_answer": "P38398",
    "notes": "Uses UniProt database. Verified in uniprot_exploration.md via search_uniprot_entity. Requires actual search, not trivial."
  },
  {
    "id": 2,
    "category": "Completeness",
    "question": "How many NANDO diseases have MONDO mappings?",
    "expected_answer": "2,150 unique diseases have mappings",
    "notes": "Uses NANDO. Entity count from nando_exploration.md via SPARQL COUNT(DISTINCT). Relationship count is 2,341. Requires database query, not MIE reading."
  }
]
```

**INCORRECT** ❌:
```json
{
  "questions": [...]  // Don't wrap in object!
}
```

### Required Fields

**Must include all 5**:
- `id` (integer): Sequential 1-120 across all files
- `category` (string): Exactly one of the 6 categories (case-sensitive)
- `question` (string): 10-500 characters, naturally phrased
- `expected_answer` (string): Specific, verifiable answer
- `notes` (string): Database(s), verification method, why non-trivial

### Field Rules
- Categories must match EXACTLY: "Precision", "Completeness", "Integration", "Currency", "Specificity", "Structured Query"
- IDs are globally sequential (Q01: 1-12, Q02: 13-24, etc.)
- Notes should reference exploration reports AND explain why question is non-trivial
- For counting questions: clarify entity vs. relationship count in notes

---

## Question Creation Process

### For Each Question:

1. **Reference exploration report(s)** for the database(s) you're using

2. **Select verified biological finding** from "Question Opportunities" section
   - Must be from actual query results, NOT MIE examples
   - Should require database access to answer

3. **Apply triviality test**:
   - ❌ Can this be answered by reading MIE file? → Reject
   - ✅ Does this require search/query? → Good
   - Example: "What is UniProt ID for BRCA1?" ✅ vs "What is organism for P12345?" ❌

4. **Apply expert realism test** (CRITICAL):
   - ❓ Ask: "Would a real researcher actually want to know this for their work?"
   - ❓ Does this support research workflows (drug discovery, clinical genetics, epidemiology)?
   - ❓ Does this provide actionable scientific insights?
   - ❌ Is this database trivia, arbitrary ordering, or "fun facts"? → Reject
   - ✅ Does this help interpret data, identify targets, or guide experiments? → Good
   - Example: "How many pathogenic BRCA1 variants?" ✅ vs "How many proteins start with Q?" ❌

5. **Check biological relevance**:
   - Would a researcher care about this answer?
   - Does it provide scientific insight vs. administrative info?
   - If methodology: does it affect scientific interpretation?

6. **For cross-reference counts**:
   - Check exploration report for BOTH entity and relationship counts
   - Decide which count to ask about
   - Formulate question to make this clear
   - Document both counts in notes

7. **Verify answer**:
   - Entity/concept exists in database (found through exploration)
   - Query method is known (from tested SPARQL or search)
   - Answer is specific and verifiable
   - Answer relates to biological/scientific content
   - Answer is NOT just reading MIE file
   - **CRITICAL: Answer directly addresses the question asked**
     * If question asks "how many species", answer should be a count of species
     * If question asks "which X", answer should list specific X entities
     * If question asks "what is Y", answer should provide Y value
     * Don't answer a different question than what was asked

7. **Formulate naturally**: Write as a researcher would ask

8. **Document thoroughly** in notes:
   - Database(s) involved
   - Exploration report reference
   - Verification method (what query/search was used)
   - Why non-trivial (requires what kind of database access)
   - Why this tests database access vs. training knowledge
   - For cross-references: entity vs. relationship count clarification

---

## File Structure

Create 10 files with EXACTLY 12 questions each:

```
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q01.json  (IDs 1-12)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q02.json  (IDs 13-24)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q03.json  (IDs 25-36)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q04.json  (IDs 37-48)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q05.json  (IDs 49-60)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q06.json  (IDs 61-72)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q07.json  (IDs 73-84)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q08.json  (IDs 85-96)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q09.json  (IDs 97-108)
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q10.json  (IDs 109-120)
```

Each file contains:
- 2 questions from each of the 6 categories
- JSON array format (not wrapped in object)
- Sequential IDs continuing from previous file

---

## Workflow

1. **Read exploration summary** to understand database coverage plan

2. **Review exploration reports** for findings (actual query results, not MIE examples)

3. **For each file (Q01.json through Q10.json)**:
   
   a. **Distribute categories**: 2 questions × 6 categories = 12 questions
   
   b. **Follow coverage plan** from summary
   
   c. **For each question**:
      - Consult relevant exploration report(s)
      - Select verified BIOLOGICAL finding from actual queries (not MIE examples)
      - ✅ Triviality test: Requires database query? (not just MIE reading)
      - ✅ Expert realism test: Would a real researcher ask this for their work?
      - ✅ Biological relevance: About biology/science? (not IT metadata)
      - ⚠️ If counting cross-references: Which count (entity or relationship)?
      - Formulate naturally (10-500 characters)
      - Write clear expected answer (clarify count type if needed)
      - Write detailed notes:
        * Exploration report reference
        * What query/search method was used
        * Why this requires database access (non-trivial)
        * Why this is expert-relevant (if not obvious)
        * Entity vs. relationship count clarification (if applicable)
      - Assign sequential ID (1-120 globally)
      - Use exact category name (case-sensitive)
   
   d. **Create JSON file** as array with 12 objects
   
   e. **Validate format**:
      - Root is array `[...]`, not object
      - All 5 fields present
      - Categories spelled correctly
      - IDs sequential
      - Questions are non-trivial

4. **After all 10 files created**:
   
   a. **Run validation script**:
      ```bash
      cd /Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts
      python validate_questions.py ../questions/Q01.json
      python validate_questions.py ../questions/Q02.json
      # ... repeat for all files
      ```
   
   b. **Check database coverage**:
      - Verify all 23 databases represented
      - Identify any missing databases
      - Check for over-representation
   
   c. **Check for redundancy**:
      - Look for duplicate questions
      - Identify near-duplicates (same concept, different wording)
      - Check for excessive repetition of query patterns
   
   d. **Quality review**:
      - All questions biologically relevant?
      - All questions expert-realistic (would researchers actually ask these)?
      - All questions non-trivial (require database queries)?
      - No database trivia, arbitrary orderings, or "fun facts"?
      - Counting questions have clear semantics?
      - All answers verifiable from exploration reports?
      - No questions about MIE file contents or structure?

---

## Validation & Remediation

### Automated Validation

The validation script (`validate_questions.py`) checks:
- ✅ JSON format (array structure, valid syntax)
- ✅ Required fields present
- ✅ Category names valid
- ✅ Category distribution (should be even)
- ✅ Duplicate questions
- ✅ Question quality (length, vague terms)

**Run validation**:
```bash
python validate_questions.py questions/Q01.json --strict --estimate-cost
```

### Manual Checks (After Validation)

1. **Triviality Check** (CRITICAL):
   - Review each question: Can it be answered by reading MIE?
   - Flag any questions using MIE example entities
   - Flag questions about schema/documentation structure
   - Replace trivial questions with ones requiring actual queries

2. **Expert Realism Check** (CRITICAL):
   - Review each question: Would a real researcher ask this for their work?
   - Flag database trivia, arbitrary orderings, "fun facts"
   - Flag questions like "shortest/longest name", "starts with letter X", "alphabetically Nth"
   - Replace with questions that support research workflows or provide scientific insights
   - Example fixes:
     * "How many proteins start with Q?" → "How many kinase inhibitors in ChEMBL?"
     * "What's the shortest gene name?" → "What genes are associated with Huntington's?"

3. **Structural Metadata Check** (CRITICAL):
   - Scan for: "tree number", "classification code", "ICD code", "namespace", "prefix"
   - Flag questions about organizational/classification structure
   - Replace with questions about actual biological entities/content
   - Example fix: "What is tree number for X?" → "How many subtypes of X exist?"

4. **Vague Language Check**:
   - Scan for unclear terms: "specific", "certain", "some", "various" without clear meaning
   - Flag questions where the scope is ambiguous
   - Rephrase for clarity or replace
   - Example fix: "reactions involving specific proteins" → "reactions with protein participants"

5. **Question-Answer Alignment Check** (CRITICAL):
   - For each question, verify answer directly addresses what's asked:
     * "How many species..." should answer with species count
     * "Which X..." should list specific X entities
     * "What is the Y..." should provide the Y value
   - Flag mismatches where question asks one thing but answer provides another
   - Fix by either rewriting question or revising answer

6. **Database Coverage** (must be 100%):
   - Count questions per database from notes
   - Ensure all 23 databases represented
   - If gaps: replace questions from over-represented databases

7. **Redundancy Detection**:
   - Exact duplicates: remove immediately
   - Near-duplicates: keep better phrased, replace other
   - Conceptual redundancy: if 3+ questions test same capability, reduce to 2

8. **Quality Verification**:
   - Scan for infrastructure keywords: "version", "release", "software", "update", "MIE"
   - Flag for manual review if found
   - Verify counting questions specify entity OR relationship count
   - Check all notes reference exploration reports
   - Verify notes explain why question is non-trivial

### Remediation Process

**If issues found**:

1. **Identify replacement candidates**:
   - Trivial questions (answerable from MIE alone)
   - Non-expert questions (database trivia, arbitrary orderings, "fun facts")
   - Questions from over-represented databases
   - Lower-quality questions (infrastructure focus)
   - Redundant questions

2. **Create replacements**:
   - Use exploration reports (query results section)
   - Avoid MIE example entities
   - Ensure requires actual database query
   - Ensure expert-relevant (supports research workflows)
   - Maintain same category
   - Keep same ID (replace in-place)
   - Ensure biological relevance
   - Verify no new redundancy

3. **Re-run validation** after changes

---

## Success Criteria

Before finalizing:

- ✅ All 10 files created (Q01-Q10)
- ✅ Each file has exactly 12 questions
- ✅ 120 questions total (IDs 1-120)
- ✅ Each category has exactly 20 questions
- ✅ All 23 databases represented
- ✅ 0 exact duplicates
- ✅ <5 near-duplicates (with justification)
- ✅ **All questions non-trivial (require database queries)**
- ✅ **No questions answerable from MIE alone**
- ✅ All questions biologically relevant
- ✅ All counting questions have clear semantics
- ✅ All validation checks pass
- ✅ JSON format correct (array, not object)

---

## Quick Validation Checklist (Per File)

Before saving each file:
- [ ] Root element is array `[...]`, not object
- [ ] Contains exactly 12 questions
- [ ] All 5 fields present: id, category, question, expected_answer, notes
- [ ] IDs sequential (1-12, 13-24, etc.)
- [ ] Categories exact match (case-sensitive)
- [ ] Questions 10-500 characters
- [ ] Each category appears exactly 2 times
- [ ] Valid JSON syntax
- [ ] **All questions require database queries (non-trivial)**
- [ ] **No questions about MIE examples or documentation**
- [ ] **No vague language ("some", "certain", "specific" without clarity)**
- [ ] **Answers directly address questions asked (alignment check)**
- [ ] **No structural metadata (tree numbers, classification codes, schema properties)**
- [ ] All questions focus on biology/science (not IT infrastructure)
- [ ] Cross-reference counting questions specify which count
- [ ] Notes explain why each question is non-trivial

---

## Examples: Trivial vs. Non-Trivial

### ❌ TRIVIAL (Avoid These)

**Example 1: MIE Example Entity**
```json
{
  "id": 1,
  "category": "Precision",
  "question": "What is the organism for UniProt:P12345?",
  "expected_answer": "Homo sapiens",
  "notes": "P12345 is an example from the MIE file"
}
```
**Problem**: P12345 appears in MIE examples. Can be answered by reading MIE, not querying database.

**Example 2: Structural Metadata**
```json
{
  "id": 2,
  "category": "Precision",
  "question": "What is the tree number for Diabetes Mellitus in MeSH?",
  "expected_answer": "C18.452.394.750",
  "notes": "Tree numbers organize MeSH hierarchy"
}
```
**Problem**: Tree numbers are classification structure metadata, not biological content. Asks about organizational code rather than the disease itself.

**Example 3: MIE SPARQL Query Reproduction**
```json
{
  "id": 3,
  "category": "Precision",
  "question": "What is the recommended name for UniProt protein P12345?",
  "expected_answer": "Example Protein",
  "notes": "Uses example SPARQL query from MIE file"
}
```
**Problem**: P12345 is the example entity from the MIE SPARQL query examples. Question just reproduces the MIE documentation query without finding real data.

**Example 4: Query Pattern Question**
```json
{
  "id": 4,
  "category": "Structured Query",
  "question": "What SPARQL pattern should be used to retrieve protein annotations from UniProt?",
  "expected_answer": "SELECT ?annotation WHERE { ?protein up:annotation ?annotation }",
  "notes": "SPARQL pattern from documentation"
}
```
**Problem**: Asks about query patterns/documentation, not biological data. Tests knowledge of SPARQL syntax, not database content.

**Example 5: Documentation Question**
```json
{
  "id": 5,
  "category": "Completeness",
  "question": "How many example SPARQL queries are in the Reactome MIE file?",
  "expected_answer": "12",
  "notes": "Counted from MIE file documentation"
}
```
**Problem**: Question about MIE documentation, not biological data. Trivial.

### ⚠️ PROBLEMATIC (Fix These)

**Example 6: Vague Language**
```json
{
  "id": 6,
  "category": "Completeness",
  "question": "How many biochemical reactions involve specific proteins?",
  "expected_answer": "92,977 reactions",
  "notes": "Reactome biochemical reactions"
}
```
**Problem**: "specific proteins" is vague. Does it mean "particular proteins" or "having protein participants"? Unclear what's being counted.

**Fix**:
```json
{
  "id": 6,
  "category": "Completeness",
  "question": "How many biochemical reactions in Reactome have protein participants?",
  "expected_answer": "92,977 reactions",
  "notes": "Reactome biochemical reactions with protein involvement"
}
```

**Example 7: Question-Answer Mismatch**
```json
{
  "id": 7,
  "category": "Currency",
  "question": "How many species have gene annotations in Ensembl?",
  "expected_answer": "Mouse: 744,820 genes, Human: 87,688 genes, Pig: 624,705 genes",
  "notes": "Multi-species gene counts"
}
```
**Problem**: Question asks "how many species" but answer gives gene counts per species. Mismatch.

**Fix Option 1** (change question):
```json
{
  "id": 7,
  "category": "Currency",
  "question": "Which species have the most gene annotations in Ensembl?",
  "expected_answer": "Mouse: 744,820 genes, Human: 87,688 genes, Pig: 624,705 genes",
  "notes": "Top species by gene annotation count"
}
```

**Fix Option 2** (change answer):
```json
{
  "id": 7,
  "category": "Currency",
  "question": "How many species have gene annotations in Ensembl?",
  "expected_answer": "100+ species annotated (including human, mouse, zebrafish, and 97+ others)",
  "notes": "Ensembl covers diverse vertebrate and model organism species"
}
```

### ✅ NON-TRIVIAL (Create These)

```json
{
  "id": 1,
  "category": "Precision",
  "question": "What is the organism for UniProt:P12345?",
  "expected_answer": "Homo sapiens",
  "notes": "P12345 is an example from the MIE file"
}
```
**Problem**: P12345 appears in MIE examples. Can be answered by reading MIE, not querying database.

```json
{
  "id": 2,
  "category": "Completeness",
  "question": "How many example SPARQL queries are in the Reactome MIE file?",
  "expected_answer": "12",
  "notes": "Counted from MIE file documentation"
}
```
**Problem**: Question about MIE documentation, not biological data. Trivial.

### ✅ NON-TRIVIAL (Create These)

```json
{
  "id": 1,
  "category": "Precision",
  "question": "What is the UniProt ID for human BRCA1?",
  "expected_answer": "P38398",
  "notes": "Uses UniProt. Found via search_uniprot_entity('BRCA1 human'). Requires actual search query, not in MIE examples. Verified in uniprot_exploration.md."
}
```
**Good**: Requires actual search/query. BRCA1 is real entity found through exploration, not MIE example.

```json
{
  "id": 2,
  "category": "Completeness",
  "question": "How many NANDO diseases have MONDO mappings?",
  "expected_answer": "2,150 unique diseases have mappings",
  "notes": "Uses NANDO. Requires COUNT(DISTINCT ?disease) SPARQL query. Entity count verified in nando_exploration.md. Relationship count (2,341) is different due to one-to-many mappings. Non-trivial: requires actual database query."
}
```
**Good**: Requires running COUNT query on actual data. Cannot be answered from MIE file.

---

## Important Reminders

✅ **DO**:
- Draw from verified exploration findings (query results, not MIE examples)
- Reference specific exploration reports in notes
- Use natural, realistic phrasing without vague terms
- Maintain even category distribution
- Focus on biological/scientific content
- Clarify entity vs. relationship counts
- **Ensure questions require database queries**
- **Ensure answers directly address questions asked**
- **Explain why each question is non-trivial in notes**
- Run validation script after generation

❌ **DON'T**:
- Use entities that are just examples from MIE files (including SPARQL query examples)
- Ask about MIE file contents or structure
- Ask about SPARQL query patterns or how to query databases
- Reproduce MIE SPARQL examples as questions
- Ask about database versions or release numbers
- Ask about structural/organizational metadata (tree numbers, classification codes, schema properties)
- Use vague language ("specific", "certain", "some" without clear meaning)
- Create question-answer mismatches (answer must address question asked)
- Focus on pure IT infrastructure (unless interpretation-critical)
- Use ambiguous counting language for cross-references
- Create duplicate or near-duplicate questions
- Skip validation steps
- Wrap JSON in object (use array!)

---

**Begin by reading the exploration summary and example questions, then generate all 120 questions following this specification. Ensure every question requires actual database access, not just MIE reading. Run validation after completion and remediate any issues.**