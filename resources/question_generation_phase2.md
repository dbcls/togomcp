# TogoMCP Question Generation - Phase 2: Create 120 Questions
# REVISED VERSION - Natural Language Questions (No Tool/Technology References)

## Quick Reference
- **Goal**: Create 120 evaluation questions, **70%+ requiring deep database knowledge**
- **Output**: 10 JSON files (Q01.json - Q10.json) with 12 questions each
- **Format**: JSON array with required fields
- **Distribution**: 2 questions per category per file (20 total per category)
- **CRITICAL**: Questions must be phrased NATURALLY - NO technical/tool mentions
- **Validation**: Run `python validate_questions.py` after generation

---

## CRITICAL: Natural Language Question Principle

⚠️ **Questions Must Sound Like a Researcher Asking** ⚠️

The evaluation tests whether TogoMCP can understand and answer natural research questions. Questions should be phrased as a biologist, chemist, or biomedical researcher would naturally ask them.

### What to EXCLUDE from Question Text

**❌ NEVER include these in the question field**:
- Technology names: "SPARQL", "API", "RDF", "endpoint", "query"
- Tool names: "togoid", "OLS4", "E-utilities", "MIE file"
- Implementation terms: "full-text search", "bif:contains", "property path"
- Database internals: "GRAPH", "URI", "triple", "schema", "ontology lookup"
- Method references: "convert using...", "search via...", "query the..."

**✅ Questions should read like**:
- A researcher asking a colleague
- A question you'd type into a smart assistant
- Natural language without implementation hints

### Examples: Bad vs Good

| ❌ BAD (Contains Technical Terms) | ✅ GOOD (Natural Language) |
|----------------------------------|---------------------------|
| "Use SPARQL to find human proteins with autophagy GO annotations" | "Which human proteins are involved in autophagy?" |
| "Query the Rhea database API for reactions involving ATP" | "What biochemical reactions use ATP as a substrate?" |
| "Search UniProt using full-text search for proteins described as 'kinase'" | "Find human proteins that function as kinases" |
| "Convert UniProt P04637 to NCBI Gene ID using togoid" | "What is the NCBI Gene ID for the protein P04637?" |
| "Execute a cross-database SPARQL join between UniProt and PDB" | "Which human proteins have experimentally determined 3D structures?" |
| "Query the citations graph in UniProt for TP53 papers" | "What research publications are associated with the TP53 protein entry?" |
| "Use MIE file performance strategies to count reviewed proteins" | "How many reviewed human kinases are in UniProt?" |
| "Apply bif:contains to search protein annotation text for 'receptor'" | "Find proteins that are described as membrane receptors" |
| "Look up GO:0006914 descendants using OLS4 API" | "What are the more specific terms under autophagy in Gene Ontology?" |
| "Search PubMed using MeSH terms for CRISPR clinical trials" | "What clinical trials are studying CRISPR-based therapies?" |

### Where Technical Details Belong

**All technical information goes in the `notes` field**:
- What databases/tools are needed (internal documentation)
- What knowledge/patterns are required
- What approach works vs. fails
- Performance considerations
- Why this question is complex or simple

The `notes` field is for evaluators and developers, NOT shown to users.

---

## Prerequisites

**Verify exploration is complete**:
- Check for exploration reports in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
- **Required**: All databases must have exploration reports with complex patterns documented
- If missing, complete Phase 1 (exploration) first using `question_generation_phase1.md`

**Read these files BEFORE starting**:
1. `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_SUMMARY.md`
2. `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/QUESTION_DESIGN_GUIDE.md`
3. `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/QUESTION_FORMAT.md`
4. `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/example_questions.json`

**Understand the complexity targets**:
- Total: 85 Complex (70%) + 35 Simple (30%)
- Structured Query: 18 Complex, 2 Simple (90% Complex)
- Integration: 16 Complex, 4 Simple (80% Complex)
- Completeness: 12 Complex, 8 Simple (60% Complex)
- Specificity: 10 Complex, 10 Simple (50% Complex)
- Currency: 10 Complex, 10 Simple (50% Complex)
- Precision: 9 Complex, 11 Simple (45% Complex)

---

## Question Requirements

### Distribution
- **120 questions total** (10 files × 12 questions)
- **2 questions per category per file** (20 total per category)
- **ALL databases represented** across 120 questions
- **85+ questions (70%) require deep database knowledge**
- **35 questions (30%) are straightforward for contrast**

### Complexity Classification

Every question must be classified as either:

**🔴 COMPLEX (Target: 85 questions / 70%)**

Questions that require deep knowledge of database structure and relationships:

1. **Cross-Database Questions** (Target: 25 questions)
   - Require combining information from multiple databases
   - Need understanding of how entities relate across databases
   - Example: "Which human enzymes catalyze reactions that produce glucose?"

2. **Performance-Sensitive Questions** (Target: 20 questions)
   - Require efficient strategies on large datasets
   - Need proper filtering and ordering
   - Example: "How many human proteins have annotations related to DNA repair?"

3. **Pattern-Sensitive Questions** (Target: 15 questions)
   - Have known pitfalls that need to be avoided
   - Require specific approaches to succeed
   - Example: "Find proteins whose functional description mentions 'membrane receptor'"

4. **Multi-Criteria Questions** (Target: 25 questions)
   - Combine multiple filtering conditions
   - Require understanding of data relationships
   - Example: "Find drug candidates with high potency against EGFR that are in clinical trials"

**🟢 SIMPLE (Target: 35 questions / 30% for contrast)**

Questions answerable with straightforward approaches:

1. **Direct Lookups** (Target: 15 questions)
   - Single entity searches
   - Basic property retrieval
   - Example: "What is the UniProt ID for human BRCA1?"

2. **Standard Queries** (Target: 12 questions)
   - Well-defined database operations
   - Documented standard procedures
   - Example: "What are the child terms of 'autophagy' in Gene Ontology?"

3. **ID Mappings** (Target: 8 questions)
   - Cross-reference lookups
   - Standard identifier conversions
   - Example: "What is the NCBI Gene ID corresponding to UniProt P04637?"

---

## Categories with Complexity Targets

Each category should have different complexity ratios:

1. **Structured Query** (20 total)
   - 🔴 Complex: 18 questions (90%)
   - 🟢 Simple: 2 questions (10%)
   - *Focus*: Multi-step queries with filtering

2. **Integration** (20 total)
   - 🔴 Complex: 16 questions (80%)
   - 🟢 Simple: 4 questions (20%)
   - *Focus*: Cross-database questions

3. **Completeness** (20 total)
   - 🔴 Complex: 12 questions (60%)
   - 🟢 Simple: 8 questions (40%)
   - *Focus*: Counting and coverage

4. **Specificity** (20 total)
   - 🔴 Complex: 10 questions (50%)
   - 🟢 Simple: 10 questions (50%)
   - *Focus*: Specialized domain queries

5. **Currency** (20 total)
   - 🔴 Complex: 10 questions (50%)
   - 🟢 Simple: 10 questions (50%)
   - *Focus*: Recent/updated data

6. **Precision** (20 total)
   - 🔴 Complex: 9 questions (45%)
   - 🟢 Simple: 11 questions (55%)
   - *Focus*: Exact values and measurements

---

## Question Creation Process

### For Each Question:

1. **Decide complexity first**:
   - Will this be 🔴 Complex or 🟢 Simple?
   - Check category targets: Have enough of each type?
   - For Complex: Which pattern (cross-database, performance, pitfall, multi-criteria)?

2. **Reference exploration report(s)**:
   - For 🔴 Complex: Read "Complex Query Patterns" section
   - For 🟢 Simple: Read "Simple Queries" section
   - Verify finding was actually tested

3. **Write the question in NATURAL LANGUAGE**:
   
   **CRITICAL CHECKLIST before writing**:
   - [ ] Does it sound like a researcher asking a colleague?
   - [ ] Are there ANY technical terms? (If yes, rephrase)
   - [ ] Would a biologist understand this without database knowledge?
   - [ ] Is the biological intent clear?
   
   **Good patterns**:
   - "Which [entities] are involved in [process]?"
   - "What [properties] does [entity] have?"
   - "Find [entities] that [biological criterion]"
   - "How many [entities] have [characteristic]?"
   - "What is the [identifier type] for [entity]?"

4. **Write detailed technical notes**:
   
   **For 🔴 Complex questions**:
   ```
   "COMPLEX QUERY - Requires: [database knowledge needed].
   
   Technical approach:
   - Databases involved: [list]
   - Key relationships: [describe]
   - Performance considerations: [if any]
   - Known pitfalls: [if any]
   
   Without proper knowledge: [what fails - timeout/error/wrong results].
   
   Verified in [exploration report] [pattern reference]."
   ```
   
   **For 🟢 Simple questions**:
   ```
   "SIMPLE QUERY - Straightforward [lookup/conversion/search].
   Demonstrates when basic approaches suffice.
   Verified in [exploration report]."
   ```

5. **Verify the answer**:
   - Answer is specific and verifiable
   - Answer directly addresses the question asked
   - Answer was confirmed during exploration

6. **Final natural language check**:
   - Re-read the question out loud
   - Does it sound natural?
   - Would you ask it this way to a knowledgeable colleague?

---

## Content Guidelines

### ✅ GOOD Question Patterns

**Cross-Database Questions** (25 target):
- ✅ "Which human enzymes catalyze reactions that involve ATP?"
- ✅ "What drugs target proteins that have 3D structures available?"
- ✅ "Find genes associated with Alzheimer's disease that have clinical variants"

**Performance-Sensitive Questions** (20 target):
- ✅ "How many reviewed human proteins have autophagy-related annotations?"
- ✅ "What human kinases have GO annotations for signal transduction?"
- ✅ "Count the enzymes in UniProt that are classified under EC 2.7 (transferases)"

**Pattern-Sensitive Questions** (15 target):
- ✅ "Find proteins whose description mentions 'membrane receptor'"
- ✅ "What proteins have annotations containing the term 'apoptosis'?"
- ✅ "Find research publications cited in the UniProt entry for p53"

**Multi-Criteria Questions** (25 target):
- ✅ "Find ChEMBL compounds with high potency against EGFR that are in clinical trials"
- ✅ "What pathogenic variants in BRCA1 have strong review evidence?"
- ✅ "Find human proteins with both kinase activity and nuclear localization"

**Simple Contrast Questions** (35 target):
- ✅ "What is the UniProt ID for human BRCA1?"
- ✅ "What is the NCBI Gene ID for protein P04637?"
- ✅ "What are the child terms of autophagy in Gene Ontology?"
- ✅ "What is the PubChem compound ID for aspirin?"

### ❌ BAD Question Patterns

**Technical language** (NEVER use):
- ❌ "Use SPARQL to query UniProt for..."
- ❌ "Search using the full-text search function for..."
- ❌ "Convert IDs using togoid..."
- ❌ "Query the Rhea API for..."
- ❌ "Look up in the MIE file..."
- ❌ "Execute a cross-database join..."

**Implementation hints** (NEVER include):
- ❌ "...using the reviewed protein filter..."
- ❌ "...via the enzyme EC number relationship..."
- ❌ "...through the citations graph..."
- ❌ "...with early filtering for performance..."

**Database jargon** (NEVER include):
- ❌ "...with GRAPH URI..."
- ❌ "...using property path..."
- ❌ "...via RDF triple patterns..."
- ❌ "...endpoint query..."

---

## Notes Field Format

### For Complex Questions:

**Template**:
```
"COMPLEX QUERY requiring deep database knowledge.

Databases/Resources: [List databases involved]

Knowledge Required:
- [Key insight 1: e.g., how databases connect]
- [Key insight 2: e.g., performance strategy]
- [Key insight 3: e.g., pitfall to avoid]

Without proper knowledge: [what fails - timeout/error/wrong approach].

Technical details: [Brief description of correct approach]

Verified in [exploration_report.md] [pattern reference]."
```

**Example**:
```
"COMPLEX QUERY requiring cross-database knowledge.

Databases/Resources: UniProt (proteins), Rhea (reactions), ChEBI (compounds)

Knowledge Required:
- How proteins link to reactions via enzyme classification
- Pre-filtering on reviewed proteins (444M total - needs filtering)
- Compound identification through reaction participants
- Proper ordering of conditions for performance

Without proper knowledge: Query times out or returns incomplete results
due to processing entire protein database before filtering.

Technical details: Start with reviewed human proteins, then link to 
reactions, then filter by compound involvement.

Verified in uniprot_exploration.md Pattern 2 and rhea_exploration.md 
integration section."
```

### For Simple Questions:

**Template**:
```
"SIMPLE QUERY - Straightforward [type: lookup/search/conversion].

Method: [Brief description]

Demonstrates when basic approaches suffice without complex optimization.

Verified in [exploration_report.md] simple queries section."
```

**Example**:
```
"SIMPLE QUERY - Straightforward entity lookup.

Method: Direct search for protein by gene name.

Demonstrates when basic approaches suffice without complex optimization.

Verified in uniprot_exploration.md simple queries section."
```

---

## File Structure and Distribution

Each file (Q01-Q10) should have:

**Category Distribution**:
- 2 questions × 6 categories = 12 questions per file

**Complexity Distribution**:

**Files Q01-Q07** (more complex):
- 🔴 Complex: 9-10 questions per file
- 🟢 Simple: 2-3 questions per file

**Files Q08-Q10** (more contrast):
- 🔴 Complex: 6-7 questions per file
- 🟢 Simple: 5-6 questions per file

---

## Validation Checklist

### Natural Language Check (CRITICAL)

For EVERY question, verify:
- [ ] No technology names (SPARQL, API, RDF, etc.)
- [ ] No tool names (togoid, OLS4, MIE, etc.)
- [ ] No implementation terms (full-text search, property path, etc.)
- [ ] No database internals (GRAPH, URI, triple, etc.)
- [ ] No method references (convert using, query via, etc.)
- [ ] Sounds like natural researcher question
- [ ] Biological intent is clear

### Complexity Distribution Check

After creating all questions:
```bash
# Count Complex markers
grep -r "COMPLEX QUERY" questions/*.json | wc -l
# Should be ~85

# Count Simple markers  
grep -r "SIMPLE QUERY" questions/*.json | wc -l
# Should be ~35
```

### Standard Validation

- [ ] All 10 files created (Q01-Q10)
- [ ] Each file has exactly 12 questions
- [ ] 120 questions total (IDs 1-120)
- [ ] Each category has exactly 20 questions
- [ ] All databases represented
- [ ] 0 exact duplicates
- [ ] JSON format correct

---

## Success Criteria

Before finalizing:

**Natural Language Criteria**:
- ✅ **ALL 120 questions phrased naturally (no technical terms)**
- ✅ **Questions sound like researcher asking colleague**
- ✅ **Biological intent clear without implementation hints**

**Complexity Criteria**:
- ✅ **85+ questions (70%) marked "COMPLEX QUERY"**
- ✅ **35 questions (30%) marked "SIMPLE QUERY"**
- ✅ **Category targets met**
- ✅ **All complexity notes explain what knowledge is needed**

**Standard Criteria**:
- ✅ All 10 files created
- ✅ 120 questions total
- ✅ All categories covered
- ✅ All databases represented
- ✅ JSON format valid

---

## Quick Question Creation Checklist

**For EVERY question**:

1. [ ] 🔴 Complex or 🟢 Simple? (Check targets)
2. [ ] **NATURAL LANGUAGE CHECK**: No technical terms in question?
3. [ ] Sounds like researcher asking colleague?
4. [ ] Biological intent clear?
5. [ ] Notes explain complexity/simplicity?
6. [ ] Answer verifiable from exploration?
7. [ ] Answer directly addresses question?
8. [ ] All 5 JSON fields present?

---

## Example Questions (Final Format)

### Complex Question Example

```json
{
  "id": 15,
  "category": "Integration",
  "question": "Which human enzymes catalyze reactions that involve ATP as a substrate or product?",
  "expected_answer": "[List of UniProt protein IDs with their names and associated Rhea reaction IDs]",
  "notes": "COMPLEX QUERY requiring cross-database knowledge.\n\nDatabases/Resources: UniProt (proteins/enzymes), Rhea (biochemical reactions), ChEBI (compounds)\n\nKnowledge Required:\n- Protein-to-reaction linkage via enzyme classification\n- Pre-filtering on reviewed proteins essential (444M total)\n- ATP identification in reaction participants\n- Efficient query ordering for performance\n\nWithout proper knowledge: Query times out processing entire protein database.\n\nVerified in uniprot_exploration.md Pattern 2 and rhea_exploration.md integration section."
}
```

### Simple Question Example

```json
{
  "id": 42,
  "category": "Precision",
  "question": "What is the UniProt accession number for human tumor protein p53?",
  "expected_answer": "P04637",
  "notes": "SIMPLE QUERY - Straightforward entity lookup.\n\nMethod: Direct search for well-known protein.\n\nDemonstrates when basic approaches suffice without complex optimization.\n\nVerified in uniprot_exploration.md simple queries section."
}
```

---

## Important Reminders

✅ **DO**:
- **Write ALL questions in natural language**
- Phrase questions as a researcher would ask
- Put ALL technical details in notes field
- Check every question for technical terms before including
- Meet complexity distribution targets
- Verify answers from exploration reports

❌ **DON'T**:
- **Include ANY technical terms in question text**
- Mention tools, APIs, databases internals, or methods
- Give implementation hints in the question
- Use database-specific jargon
- Assume the reader knows the underlying technology
- Rush - quality natural language is essential

---

**Begin by reading exploration summary, then generate 120 NATURALLY-PHRASED questions. Every question must sound like a researcher asking a colleague - no technical terms allowed in the question field. Technical details belong only in the notes field.**
