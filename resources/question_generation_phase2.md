Your task is to create 120 high-quality evaluation questions based on the database exploration you've already completed.

PREREQUISITES:
Before starting, verify that exploration reports exist at:
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/

If exploration reports don't exist, you must complete the exploration phase first.

SETUP:
1. Read the database exploration summary:
   /Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/00_SUMMARY.md

2. Read the format requirements:
   * /Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/QUESTION_FORMAT.md
   * /Users/arkinjo/work/GitHub/togo-mcp/evaluation/QUESTION_DESIGN_GUIDE.md
   * /Users/arkinjo/work/GitHub/togo-mcp/evaluation/scripts/example_questions.json

QUESTION REQUIREMENTS:
- 120 questions total (distributed across 10 files)
- Each file contains exactly 12 questions with 2 questions from each category:
  * Precision (exact IDs, sequences, properties)
  * Completeness (exhaustive lists, counts)
  * Integration (cross-database linking, ID conversions)
  * Currency (recent updates, current classifications)
  * Specificity (niche organisms, rare diseases)
  * Structured Query (complex filters, multi-step queries)

- Each category should have exactly 20 questions across all files (2 per file × 10 files)
- ALL databases must be represented across the 120 questions
- Each question should involve 1-4 databases
- Questions should require database access to answer correctly
- Answers should be specific facts verified during exploration

BIOLOGICAL RELEVANCE REQUIREMENT:

⚠️ **CRITICAL: ALL QUESTIONS MUST BE BIOLOGICALLY RELEVANT** ⚠️

Questions should focus on BIOLOGICAL/SCIENTIFIC CONTENT that researchers care about:

✅ **ACCEPTABLE QUESTION TOPICS:**
- Biological entities: proteins, genes, diseases, compounds, organisms
- Scientific properties: sequences, structures, molecular weights, pathways
- Research findings: clinical significance, resistance patterns, expression levels
- Experimental results: IC50 values, resolution, binding affinities
- Methodology when interpretation-critical: AST methods (affect accuracy), experimental techniques (affect results)

❌ **UNACCEPTABLE QUESTION TOPICS:**
- Database versions or release numbers ("What is the current version of Reactome?")
- Software infrastructure ("What software is most commonly used for refinement?") - UNLESS the methodology directly affects scientific interpretation
- Administrative metadata ("How many database updates this year?")
- IT details with no scientific value ("What is the update schedule?")
- Pure procedural information ("What format does the database use?")

**BORDERLINE CASES - USE JUDGMENT:**
- Software/methodology questions: Acceptable ONLY if the method choice affects scientific interpretation
  Example: ✅ "What laboratory typing method is most common in AMR Portal?" - affects resistance data accuracy
  Example: ❌ "What software version was used for structure refinement?" - IT metadata, not biological insight
- Annotation evidence: Acceptable if it affects data quality assessment
  Example: ✅ "What evidence type is used for AMR gene annotation?" - helps assess prediction confidence
  Example: ❌ "What database schema version is current?" - pure infrastructure

**CURRENCY CATEGORY SPECIAL GUIDANCE:**
Currency questions should test access to RECENT BIOLOGICAL DATA, not database maintenance info:
- ✅ "What COVID-19 pathways have been added to Reactome recently?"
- ✅ "How many isolates collected in 2024 are in AMR Portal?"
- ✅ "What are the most recent CRISPR structures in PDB?"
- ❌ "What is the current database release number?"
- ❌ "When was the database last updated?"

QUESTION DESIGN CRITERIA:
Each question MUST satisfy:

✓ **Biologically Realistic**: Would an actual researcher ask this?
✓ **Biologically Relevant**: Does it address biological/scientific content, not IT infrastructure?
✓ **Testable Distinction**: Requires database access, not training knowledge
✓ **Appropriate Complexity**: Non-trivial but not impossibly broad
✓ **Clear Success Criteria**: Verifiable correct answer
✓ **Verifiable Ground Truth**: Confirmed during exploration phase
✓ **Natural Phrasing**: No mention of "SPARQL" or "MCP tools"

QUESTION CREATION PROCESS:
For each question:

1. **Reference exploration reports**: Review the exploration report(s) for the database(s) you're using

2. **Select a verified finding**: Choose an interesting BIOLOGICAL/SCIENTIFIC finding from the "Question Opportunities" section

3. **Check biological relevance**: Ask yourself:
   - Would a biologist/biomedical researcher care about this answer?
   - Does this provide scientific insight or just administrative information?
   - If this is a methodology question, does the methodology choice affect scientific interpretation?

4. **Verify the answer**: Based on the exploration report, confirm:
   - The entity/concept exists in the database
   - You know how to query for it (from tested SPARQL queries)
   - The answer is specific and verifiable
   - The answer relates to biological/scientific content

5. **Formulate naturally**: Write the question as a researcher would ask it

6. **Document thoroughly**: In the "notes" field, include:
   - Which database(s) are involved
   - Reference to exploration report findings
   - How the answer was verified
   - Why this tests database access vs training knowledge
   - Why this is biologically relevant (if not obvious)

OUTPUT FORMAT:

⚠️ **CRITICAL - EXACT JSON FORMAT REQUIRED** ⚠️

Each file MUST be a JSON **ARRAY** (not an object), following this EXACT structure:
```json
[
  {
    "id": 1,
    "category": "Precision",
    "question": "What is the UniProt ID for human BRCA1?",
    "expected_answer": "P38398",
    "notes": "Uses UniProt database. Verified in uniprot_exploration.md. Tests search_uniprot_entity tool."
  },
  {
    "id": 2,
    "category": "Completeness",
    "question": "How many human genes are annotated with GO:0006281?",
    "expected_answer": "523 genes (as of exploration)",
    "notes": "Uses GO database. Verified via SPARQL query in go_exploration.md. Tests counting and filtering."
  }
]
```

**FIELD REQUIREMENTS:**

**Required Fields (MUST include):**
- `question` (string, 10-500 characters): The actual question text

**Recommended Fields (MUST include all of these):**
- `id` (integer): Sequential number 1-120 (globally indexed across all files)
- `category` (string): EXACTLY one of these (case-sensitive):
  * "Precision"
  * "Completeness"
  * "Integration"
  * "Currency"
  * "Specificity"
  * "Structured Query"
- `expected_answer` (string): The verified correct answer
- `notes` (string): Rationale, databases used, verification method

**Format Rules:**
- ✅ Root element MUST be an array `[...]`
- ❌ Do NOT wrap in object `{"questions": [...]}`
- ✅ Each question is an object with fields above
- ✅ Use double quotes for all strings
- ✅ Include comma after each field except the last
- ✅ Include comma after each object except the last
- ✅ Categories must match EXACTLY (case-sensitive)

**Example of INCORRECT format (DO NOT USE):**
```json
{
  "questions": [
    {
      "id": 1,
      "question": "..."
    }
  ]
}
```

**Example of CORRECT format (USE THIS):**
```json
[
  {
    "id": 1,
    "category": "Precision",
    "question": "...",
    "expected_answer": "...",
    "notes": "..."
  },
  {
    "id": 2,
    "category": "Completeness",
    "question": "...",
    "expected_answer": "...",
    "notes": "..."
  }
]
```

FILE LOCATIONS:
Save questions to 10 separate JSON files with EXACTLY 12 questions each:
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q01.json (questions 1-12)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q02.json (questions 13-24)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q03.json (questions 25-36)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q04.json (questions 37-48)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q05.json (questions 49-60)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q06.json (questions 61-72)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q07.json (questions 73-84)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q08.json (questions 85-96)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q09.json (questions 97-108)
- /Users/arkinjo/work/GitHub/togo-mcp/evaluation/questions/Q10.json (questions 109-120)

WORKFLOW:
1. Read the exploration summary and understand database coverage plan
2. Review exploration reports to refresh findings
3. For each batch of 12 questions (files Q01.json through Q10.json):
   a. Distribute 2 questions across each of the 6 categories
   b. Follow the database coverage plan from the summary
   c. For each question:
      - Consult relevant exploration report(s)
      - Select a verified BIOLOGICAL/SCIENTIFIC finding (not IT metadata)
      - **CHECK: Is this biologically relevant? Would a researcher care?**
      - Formulate the question naturally (10-500 characters)
      - Write detailed notes referencing the exploration
      - Assign sequential ID (1-120 globally across all files)
      - Ensure category name is EXACTLY one of the 6 valid values (case-sensitive)
   d. Create the JSON file as an ARRAY with 12 question objects
   e. Verify JSON format is correct (use array, not object wrapper)
4. After all 10 files are created, verify:
   - Each file is a valid JSON array starting with `[` and ending with `]`
   - Each file has exactly 12 questions
   - Each file has exactly 2 questions from each category
   - IDs are sequential from 1-120
   - All category names match exactly: "Precision", "Completeness", "Integration", "Currency", "Specificity", "Structured Query"
   - All questions have all recommended fields: id, category, question, expected_answer, notes
   - All databases from the summary are represented
   - All questions reference findings from exploration reports
   - **ALL questions are biologically/scientifically relevant (not IT infrastructure)**

VALIDATION CHECKLIST:
Before finalizing each file, verify:
- [ ] File is a JSON array `[...]`, NOT an object `{"questions": [...]}`
- [ ] Contains exactly 12 question objects
- [ ] Each object has all 5 fields: id, category, question, expected_answer, notes
- [ ] IDs are sequential integers (e.g., 1-12 for Q01.json, 13-24 for Q02.json)
- [ ] Categories are exactly: "Precision", "Completeness", "Integration", "Currency", "Specificity", "Structured Query"
- [ ] Questions are 10-500 characters
- [ ] Each category appears exactly 2 times
- [ ] JSON syntax is valid (commas, quotes, brackets)
- [ ] **ALL questions focus on biological/scientific content, not IT infrastructure**
- [ ] **NO questions about database versions, software tools (unless interpretation-critical), or administrative metadata**

DUPLICATE DETECTION:
After creating all questions:
- [ ] Check for duplicate questions (same concept, different wording)
- [ ] Check for near-duplicates (essentially asking the same thing)
- [ ] If duplicates found, replace one with a different biological question from the same database/category

IMPORTANT REMINDERS:
- **BIOLOGICAL RELEVANCE IS MANDATORY**: Every question must address biological/scientific content
- **EXACT FORMAT REQUIRED**: Follow QUESTION_FORMAT.md precisely
- **ARRAY FORMAT**: Root element must be array, not object
- **CASE-SENSITIVE CATEGORIES**: Use exact category names
- **ALL RECOMMENDED FIELDS**: Include id, category, question, expected_answer, notes for every question
- **SEQUENTIAL IDs**: Number 1-120 globally across all files
- Draw ONLY from verified findings in exploration reports
- Reference specific exploration reports in question notes
- Ensure natural, realistic phrasing
- Maintain even distribution across categories and databases
- **Avoid database versions, release numbers, and pure IT metadata**
- **Currency questions should test recent biological data, not database maintenance info**

Begin by reading the exploration summary and example_questions.json, then generate the 120 questions across 10 files following the EXACT format specification and ensuring ALL questions are biologically relevant.
