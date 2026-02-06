# BioASQ Benchmark Guidelines - TogoMCP Edition (REVISED v2.4)

## Core Principle: Biology First, Integration Essential

TogoMCP's strength is **cross-database integration via unified access**. Questions must:
1. **Ask biological questions** researchers would actually want answered
2. **Require integration** across 2+ databases (≥60% of questions)
3. **Be verifiable** with complete, definitive answers
4. **Need RDF** - impossible from literature alone
5. **Showcase database diversity** - avoid over-reliance on any single database

**Integration happens via TWO methods:**

**Method A: Search API Discovery → SPARQL Validation** (Recommended for most questions)
1. Use search APIs to discover entity IDs across databases (exploratory phase)
2. Map cross-references between databases (e.g., UniProt P09917 ↔ ChEMBL215)
3. Write **comprehensive SPARQL queries** to validate relationships and extract RDF triples
4. Combine results programmatically

⚠️ **CRITICAL DISTINCTION - Search vs. Validation:**
- **Search APIs**: Good for *discovering examples* and *finding patterns* (returns 10-20 results)
- **SPARQL queries**: Required for *comprehensive validation* and *definitive answers*
- **Never**: Use search API results as sole evidence for yes/no or comprehensive questions
- **Never**: Hardcode search results into VALUES clauses for comprehensive queries

Example: search_uniprot_entity("ALOX5") → P09917 → search_chembl_target("ALOX5") → CHEMBL215 → SPARQL query for bioactivity data

**Method B: Pure SPARQL Integration** (Use when databases share endpoints or have direct cross-references)
1. Query database A with SPARQL to get entity IDs
2. Use those IDs in SPARQL query to database B
3. Join results via shared identifiers

**Both methods are valid.** Method A is often more practical because:
- Search APIs handle free-text matching better than SPARQL bif:contains
- Discovery phase is faster with search APIs
- SPARQL then provides structured validation and RDF triples

**Not acceptable**: Database inventory questions ("How many proteins in UniProt have annotation X?") unless biologically framed
**Required**: Biological insight questions ("Which apoptosis proteins have both GO annotations and PDB structures?")

---

## ⚠️ CRITICAL: Comprehensive vs. Example-Based Queries

### The Circular Reasoning Trap

**WRONG approach (example-based):**
```
Step 1: Search API finds 8 examples
Step 2: Hardcode those 8 IDs into SPARQL VALUES clause
Step 3: Verify properties of those 8 examples
Step 4: Conclude based on 8 examples
Problem: You only checked what you already found - circular reasoning!
```

**CORRECT approach (comprehensive):**
```
Step 1: Search API finds examples (exploratory - understand the pattern)
Step 2: SPARQL queries ALL entities matching criteria using bif:contains
Step 3: Aggregate/classify comprehensive results
Step 4: Conclude based on complete dataset
```

### When Each Approach Applies

**Example-based queries are ACCEPTABLE for:**
- Listing specific entities: "Which 5 kinases have most inhibitors?" (top-N ranking)
- Checking properties of known entities: "Do these 3 proteins bind ATP?" (bounded verification)
- Cross-referencing specific IDs: "What PDB structures exist for protein X?" (specific lookup)

**Comprehensive queries are REQUIRED for:**
- Yes/No questions: "Do ANY proteins in category X have property Y?"
- Phylogenetic distribution: "Are enzymes found in phyla beyond A and B?"
- Existence claims: "Are there compounds with property X?"
- Negative claims: "No proteins of type Y have annotation Z"
- Comparative statements: "Only phylum A has enzyme X"

### How to Write Comprehensive SPARQL

**For yes/no or distribution questions:**

```sparql
# WRONG - Hardcoded VALUES (circular reasoning)
VALUES ?protein { uniprot:P12345 uniprot:P67890 }  # ← From search API
?protein up:annotation ?annot .

# CORRECT - Comprehensive search with bif:contains
?protein up:recommendedName ?name .
?name up:fullName ?fullName .
?fullName bif:contains "'keyword1' OR 'keyword2' OR 'keyword3'"  # ← All variants
?protein up:annotation ?annot .
```

**For phylogenetic distribution questions:**

```sparql
# WRONG - Only checking pre-selected organisms
VALUES ?taxon { taxon:9606 taxon:10090 }  # ← From search

# CORRECT - Query all organisms, then aggregate by phylum
?protein up:organism ?organism .
?organism rdfs:subClassOf+ ?phylum .
?phylum up:rank "phylum" .
GROUP BY ?phylum
```

**Multiple search terms for comprehensive coverage:**

```sparql
# Search with all known synonyms and variations
?fullName bif:contains "'rhamnosyltransferase' OR 'protein-arginine rhamnosyl' OR 'WbbL' OR 'EF-P rhamnosyl'"
```

---

## ⚠️ TWO WORKSPACES - CRITICAL TO UNDERSTAND

### User's Computer: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/`
**ONLY use Filesystem tools:**
- `Filesystem:read_text_file(path="/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/...")`
- `Filesystem:write_file(path="/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/...")`
- `Filesystem:list_directory(path="/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/...")`

**Use for**: Reading keywords, saving questions to `questions/` subdirectory, updating tracker
**Key paths**:
- Keywords: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv`
- Questions: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml`
- Tracker: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml`

### Claude's Computer: `/home/claude/...`
**ONLY use bash/computer tools:**
- `bash_tool`, `create_file`, `view`

**Use for**: Testing SPARQL queries, temporary work

**❌ Never**: `bash_tool` on `/Users/arkinjo/...` paths (will fail)
**✅ Always**: Save questions to `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml`

---

## Requirements

### Question Targets
- **50 total questions**
- **≥30 questions (60%)** must integrate 2+ databases
- **≥10 questions (20%)** must integrate 3+ databases
- **Type distribution**: ≥10 factoid, ≥10 yes/no, ≥10 list, ≥10 summary
- **Database coverage**: Prioritize unused databases (see Database Balance Requirements below)

### Database Balance Requirements
- **UniProt cap**: Use in ≤70% of questions (maximum 35 of 50)
- **Priority databases**: Each must appear in ≥3 questions
  - DDBJ (nucleotide sequences, genomes)
  - Glycosmos (glycan structures)
  - MeSH (medical subject headings)
  - PubMed (literature integration)
  - Ensembl (comparative genomics)
  - Taxonomy (phylogenetic relationships)
  - PubChem (≥3 questions)
  - ChEBI (≥3 questions)
  - Rhea (≥3 questions)
- **Avoid UniProt-centric bias**: Not every question needs protein data
- **Alternative anchors**: Use genes (NCBI Gene), diseases (MONDO), pathways (Reactome), compounds (PubChem), variants (ClinVar) as starting points
- **Check tracker before planning**: Actively avoid overused databases, target underused ones

### Quality Standards
- **Biological relevance**: Would a researcher care about the answer?
- **Integration-driven**: Showcases cross-database links
- **Verifiable**: Single answer, ≤10 items, or single aggregate
- **RDF-necessary**: Requires graph queries, cannot answer from PubMed OR from Claude's training knowledge
- **Random keyword selection**: No bias, no thematic clustering - pure random from unused keywords
- **Comprehensive queries**: For yes/no or existence claims, must query ALL matching entities, not just examples

---

## Natural Integration Patterns

Use these biological relationships that require multiple databases (via separate SPARQL queries or Search API + SPARQL):

### Protein-Centric Patterns

**Protein → Structure → Ligand**
- Query UniProt for proteins with annotations → Extract PDB IDs from rdfs:seeAlso → Query ChEMBL for ligand binding
- "Which kinase inhibitors bind to structurally characterized active sites?"

**Gene → Variant → Disease**  
- Query NCBI Gene for gene info → Query ClinVar for variants using gene IDs → Query MONDO for disease classifications
- "Which ion channel genes have pathogenic variants in neurological disorders?"

**Pathway → Enzyme → Cofactor**
- Query Reactome for pathway components → Query UniProt for enzyme details → Query ChEBI for cofactor properties
- "Which heme-dependent enzymes participate in xenobiotic metabolism pathways?"

**Process → Protein → Organism**
- Query GO for process annotations → Query UniProt for proteins → Query Taxonomy for organism distribution
- "Are nitrogen fixation enzymes conserved across bacterial and archaeal lineages?"

**Compound → Target → Indication**
- Query PubChem/ChEBI for compound properties → Query ChEMBL for bioactivity → Query UniProt for target info
- "Which anti-inflammatory compounds target kinases implicated in autoimmune diseases?"

**Reaction → Enzyme → Structure**
- Query Rhea for reactions → Query UniProt for enzymes → Check PDB cross-references in UniProt
- "Which dehydrogenase reactions lack structural data for their catalytic domains?"

### Non-Protein Starting Points (PRIORITIZE THESE)

**Literature → Database Validation**
- PubMed search for disease → MeSH terms → MONDO disease classification → NCBI Gene associations
- "How many Alzheimer's disease genes from 2024 papers are in druggable protein families?"

**Sequence → Annotation → Function**
- DDBJ sequence records → NCBI Gene annotations → GO functional classification
- "Which bacterial genomes from DDBJ have complete nitrogen fixation operons?"

**Glycan → Protein → Disease**
- Glycosmos glycan structures → UniProt glycoproteins → MONDO disease associations
- "Which glycosylation defects are associated with congenital disorders?"

**Taxonomy → Distribution → Evolution**
- Taxonomy phylogenetic tree → Ensembl ortholog groups → GO function conservation
- "Are ABC transporters conserved across all vertebrate lineages?"

**Medical Ontology Integration**
- MeSH disease terms → MONDO disease ontology → ClinVar genetic variants
- "Which rare diseases share genetic architecture with common diseases?"

**Organism Traits → Genetic Basis**
- BacDive organism search → Taxonomy classification → NCBI Gene → UniProt proteins
- "Which thermophilic bacteria have characterized heat shock proteins?"

**Compound Chemistry → Bioactivity → Mechanism**
- PubChem compound properties → ChEMBL bioactivity → Reactome pathway effects
- "Which PubChem compounds inhibit multiple glycolysis enzymes?"

---

## Question Requirements

### ✅ MUST Have (All Required)

**1. Biological Insight**
- Reveals relationships, mechanisms, or patterns
- Research-relevant: scientists would want this answer
- Not about database completeness or ontology structure

**2. Multi-Database Integration (for ≥60% of questions)**
- Requires JOIN across 2+ databases via cross-references or shared identifiers
- Cannot answer from single database website
- Tests TogoMCP's core integration capability
- Clear data flow between databases (document in search_apis_used and sparql_queries)

**3. Complete Verifiability**
- Single answer, OR ≤10 enumerated items, OR single aggregate value
- Definitive correctness check possible

**4. RDF Graph Necessity**
- Requires: graph traversal, cross-database JOIN, aggregation, complex filtering
- Cannot answer from PubMed/literature with reasonable effort
- Cannot answer from Claude's training knowledge alone

**5. Comprehensive Analysis (for yes/no and existence claims)**
- Must query ALL matching entities, not just examples from search APIs
- Use bif:contains with multiple search terms/synonyms
- Aggregate results across complete dataset
- Cannot rely on VALUES clauses with hardcoded examples for comprehensive questions

### ❌ MUST NOT Have (All Prohibited)

1. **Database inventory questions** - Nuanced rules:
   
   **PROHIBITED:**
   - Pure counts without biological context: "How many proteins in UniProt have annotation X?"
   - Ontology completeness: "How many GO terms exist for process Y?"
   - Database statistics: "What percentage of genes have structures?"
   
   **ACCEPTABLE if biologically framed:**
   - Comparative ranking with insight: "Which 5 enzymes have most inhibitors?" → Reveals druggability
   - Counting as discovery method: "Which pathways have >10 drug targets?" → Identifies therapeutic areas
   - Aggregation revealing patterns: "Which organisms have most nitrogen-fixing genes?" → Evolutionary insight
   
   **Key distinction**: Ask "So what?" If the count/ranking reveals biological insight beyond database completeness → ACCEPTABLE. If it's just database metadata → REJECT.

2. **Ontology structure questions** - "Is term A classified under B?" (unless biologically meaningful)

3. **Unbounded scopes** - "List ALL proteins that..." (cannot verify completeness)

4. **Literature-recoverable** - Answerable from reviews/textbooks with reasonable effort

5. **Search-only answers** - Must require SPARQL validation, not just search API results

6. **Example-based comprehensive claims** - Cannot use VALUES with hardcoded search results for yes/no or existence questions

7. **Training knowledge answerable** - Test with these criteria:
   
   **REJECT if Claude can answer from memory:**
   - Historical facts: "Which kinase inhibitor was first FDA-approved?" → Imatinib (known)
   - Famous associations: "Is BRCA1 involved in DNA repair?" → Yes (well-known)
   - Textbook knowledge: "What enzyme deficiency causes PKU?" → PAH (standard)
   
   **ACCEPT if question requires current database state:**
   - Specific counts: "How many PDB structures exist for protein X?" → Requires current count
   - Comparative rankings: "Which 5 proteins have most structures?" → Needs database aggregation
   - Quantitative bioactivity: "Which inhibitors have IC50 < 100 nM?" → Needs ChEMBL data
   - Cross-database joins: "Which genes with epilepsy variants have GO synaptic annotations?" → Requires integration
   
   **Test**: Before accepting a question, ask: "Could I answer this with 2024 training knowledge + reasonable web searching?" If yes → REJECT or reformulate.

---

## Question Types (Distribute Evenly)

### Factoid (≥10)
Single answer from graph traversal or aggregation
- "Which human kinase has the most FDA-approved inhibitors?"
- "What is the minimum IC50 of BRAF inhibitors in clinical trials?"

### Yes/No (≥10)  
Binary with EXISTS/NOT EXISTS patterns - **REQUIRES COMPREHENSIVE SPARQL**
- "Do any glycolysis enzymes localize to both nucleus and mitochondria?"
- "Are there proteins that bind both ATP and GTP with similar affinity?"
- ⚠️ **CRITICAL**: Cannot use VALUES with pre-selected examples - must search ALL entities
- ⚠️ **CRITICAL**: Must use multiple search terms to ensure comprehensive coverage

### List (≥10)
Enumerate ≤10 items with ranking/filtering
- "Which 5 metabolic pathways have the most drug targets?"
- "List kinases with pathogenic variants in ≥3 different cancer types"

### Summary (≥10)
Narrative synthesis with verifiable components
- **FORMAT REQUIREMENT: EXACTLY ONE PARAGRAPH** - No line breaks, no multiple paragraphs, no headers
- Each claim must trace to RDF triples from SPARQL queries
- Synthesize biological narrative from structured data
- Focus on mechanistic insights, not tool usage or databases
- Use sparingly - verify all claims are bounded and checkable

**Example structure**: "Glycolysis enzyme inhibitors demonstrate [claim 1 from Query 4] with [claim 2 from Query 4]. The pathway context [claim 3 from Query 1] confirms [biological insight]. Integration reveals [mechanistic conclusion from combined data]."

**Common violations to avoid:**
- Multiple paragraphs (NEVER do this)
- Unbounded claims without SPARQL evidence
- Describing the methodology instead of biological findings
- Including information not in exact_answer or RDF triples

---

## Scoring Rubric (Must Pass)

Score 0-3 for each dimension, **total ≥8** with **no zeros**:

**Biological Insight (0-3)**
- 3: Reveals mechanisms, relationships, or clinical patterns
- 2: Biologically meaningful but narrow
- 1: Minor biological relevance
- 0: Database inventory → REJECT

**Multi-Database Integration (0-3)**
- 3: Requires 3+ databases, multiple queries combined via shared IDs
- 2: Requires 2 databases, queries linked by cross-references/IDs
- 1: Single database (acceptable for ≤40% of questions)
- 0: Search-only, no SPARQL validation → REJECT

**Verifiability (0-3)**
- 3: Single answer/aggregate or ≤5 items
- 2: 6-10 items systematically checked
- 1: Requires complex validation
- 0: Unbounded → REJECT

**RDF Necessity (0-3)**
- 3: Impossible without graph queries (integration, traversal, aggregation)
- 2: Extremely impractical from literature (requires extensive manual curation)
- 1: Easier with RDF but doable from literature
- 0: PubMed-answerable OR training knowledge → REJECT

**Additional checks:**
- [ ] Used search APIs for discovery (document which ones)
- [ ] Validated with **comprehensive SPARQL** (not just search results or hardcoded VALUES)
- [ ] For yes/no questions: queried ALL matching entities using bif:contains
- [ ] Cannot answer from PubMed with reasonable effort
- [ ] Cannot answer from Claude's training knowledge (tested explicitly in Step 1.5)
- [ ] RDF triples extracted from SPARQL queries
- [ ] Requires current database state (counts, IDs, specific values)
- [ ] Checked database balance (not overusing UniProt?)

---

## Common Pitfalls (Avoid These)

Based on questions 1-7, watch for:

1. **Circular reasoning with search results**: Using search API to find examples → hardcoding those IDs in VALUES → verifying only those examples → concluding based on incomplete data
2. **UniProt dependency**: If you can't formulate question without UniProt → rethink starting point
3. **Famous associations**: "Is X involved in Y?" → Too general if it's textbook knowledge
4. **Search-only questions**: If search APIs answer the question completely → need more SPARQL validation
5. **Example-based yes/no questions**: Must use comprehensive SPARQL with bif:contains, not VALUES with search results
6. **Multi-paragraph summaries**: Summary type must be SINGLE paragraph (strictly enforced)
7. **Vague integration**: "Uses 3 databases" isn't enough → show actual data flow between databases
8. **Keyword clustering**: ~~Don't create 5 questions about kinases~~ → **USE RANDOM SELECTION** - no thematic choice allowed
9. **Organism bias**: All human proteins → include bacteria, plants, archaea (random keywords will naturally diversify)
10. **Missing RDF triples**: Every claim in exact_answer must have supporting RDF triple
11. **Workspace confusion**: Work on USER'S computer (`/Users/arkinjo/...`) not Claude's (`/home/claude/`)
12. **Format violations**: Read back your YAML before finalizing → catch structure errors
13. **Skipping training knowledge test**: ALWAYS complete Step 1.5 before proceeding to Discovery
14. **Insufficient search terms**: For comprehensive queries, use multiple synonyms and variations

**Self-audit checklist before submitting:**
- [ ] Used RANDOM keyword selection (no thematic bias)
- [ ] Completed explicit training knowledge self-test (Step 1.5)
- [ ] Can I answer this from my training knowledge? (If yes → reject)
- [ ] Does PubMed answer this with reasonable effort? (If yes → reject)
- [ ] Did I check database balance? (Not contributing to UniProt overuse?)
- [ ] Is biological insight clear? (Would a researcher care?)
- [ ] **For yes/no questions: Did I use comprehensive SPARQL, not VALUES with examples?**
- [ ] **Did I search with multiple synonyms/variations?**
- [ ] Are RDF triples complete? (Every claim traceable?)
- [ ] Is format correct? (Single paragraph for summary, YAML structure valid?)
- [ ] Did I use an underused database? (Check coverage tracker)
- [ ] Is integration pattern clear? (Documented data flow between DBs)

---

## Database-Specific Strategies

To use underutilized databases, try these concrete approaches:

### DDBJ (Nucleotide/Genome sequences)
- **Pattern**: Gene sequence → annotation → function
- **Example**: "Which bacterial genomes contain complete Type VI secretion systems?"
- **Integration**: DDBJ sequence → NCBI Gene features → UniProt proteins → GO functions
- **Tools**: Use DDBJ tools when available, or integrate via NCBI Gene cross-references

### Glycosmos (Glycan structures)
- **Pattern**: Glycan structure → protein attachment → disease
- **Example**: "Which N-glycan structures are found on immune checkpoint proteins?"
- **Integration**: Glycosmos glycan → UniProt glycoprotein sites → PDB structures
- **Note**: May require web interface consultation if MCP tools limited

### MeSH (Medical ontology)
- **Pattern**: Disease term → gene associations → druggability
- **Example**: "Which MeSH cardiovascular terms map to MONDO diseases with >5 gene associations?"
- **Integration**: MeSH terms → MONDO disease classification → NCBI Gene → ChEMBL targets
- **Tools**: search_mesh_descriptor for discovery

### PubMed (Literature)
- **Pattern**: Literature analysis → database validation
- **Example**: "Which proteins mentioned in 2024 diabetes papers have FDA-approved drugs?"
- **Integration**: PubMed search → extract gene names → NCBI Gene → ChEMBL bioactivity → verify drugs
- **Tools**: PubMed MCP tools (search_articles, get_article_metadata)

### Ensembl (Comparative genomics)
- **Pattern**: Ortholog analysis → function conservation
- **Example**: "Which human metabolic genes lack orthologs in marsupials?"
- **Integration**: Ensembl orthologs → NCBI Gene → Reactome pathways → Taxonomy
- **Note**: Check if Ensembl RDF endpoint available, otherwise use cross-references

### Taxonomy (Phylogenetic relationships)
- **Pattern**: Phylogenetic classification → protein/gene distribution
- **Example**: "Which enzyme families are unique to archaea vs bacteria?"
- **Integration**: Taxonomy classification → UniProt organism filtering → GO function analysis
- **Tools**: SPARQL on Taxonomy endpoint, rdfs:subClassOf+ for hierarchical queries
- ⚠️ **CRITICAL**: For phylogenetic distribution questions, must query ALL organisms and aggregate by phylum - cannot hardcode organism IDs

### BacDive (Bacterial diversity)
- **Pattern**: Organism traits → genetic basis
- **Example**: "Which thermophilic bacteria have characterized heat shock proteins?"
- **Integration**: BacDive organism search → Taxonomy classification → UniProt proteins → PDB structures
- **Note**: May require API consultation or web interface

### PubChem (Chemical compounds)
- **Pattern**: Compound properties → bioactivity → targets
- **Example**: "Which PubChem compounds with MW < 500 inhibit multiple kinases?"
- **Integration**: PubChem compound search → ChEMBL bioactivity → UniProt targets
- **Tools**: get_pubchem_compound_id, get_compound_attributes_from_pubchem

### ChEBI (Chemical ontology)
- **Pattern**: Chemical classification → biological activity
- **Example**: "Which flavonoid subclasses have anti-inflammatory targets?"
- **Integration**: ChEBI classification → PubChem equivalents → ChEMBL bioactivity
- **Tools**: Use skos:exactMatch to link ChEBI ↔ ChEMBL ↔ PubChem

### Rhea (Biochemical reactions)
- **Pattern**: Reaction → enzyme → distribution
- **Example**: "Which organisms have enzymes for all steps in heme biosynthesis?"
- **Integration**: Rhea reactions → EC numbers → UniProt enzymes → Taxonomy
- **Tools**: search_rhea_entity for discovery

**Action**: When planning next question, explicitly choose an underused database and build question around it.

---

## Workflow (7 Steps)

### 1. Planning
**User's computer - Filesystem tools**

1. Read keywords: `Filesystem:read_text_file("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/keywords.tsv")`
2. Check coverage: `Filesystem:read_text_file("/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml")`
3. **Select keyword RANDOMLY**:
   - Count total unused keywords (exclude previously used from tracker)
   - Generate random number between 1 and total unused
   - Select that keyword by position
   - **NO thematic selection, NO strategic choice, PURE RANDOM**
   - Only exclusion: previously used keywords from coverage tracker
   - This eliminates selection bias
4. **Identify underused databases** - prioritize DDBJ, Glycosmos, MeSH, PubMed, Ensembl
5. **Identify 2-3 databases** that naturally connect for this keyword (avoid UniProt if >70% usage)
6. Read MIE files: Use `get_MIE_file` for each database
7. **Formulate biological question** - what would a researcher ask?
8. **Determine question type** - will this require comprehensive or example-based queries?
   - If yes/no or existence claim → comprehensive SPARQL required
   - If top-N ranking or specific entity lookup → example-based acceptable

### 1.5. Training Knowledge Self-Test 🔴 MANDATORY
**No tools - pure introspection**

**Purpose**: Explicitly verify the question cannot be answered from Claude's training knowledge before investing time in database queries.

**Process**:
1. **Attempt to answer the question** from memory right now
2. **Document what you know**:
   - General knowledge about the topic (e.g., "I know heme biosynthesis has ~8 enzymes")
   - Specific facts you remember (e.g., "ALAS has two isoforms: ALAS1 and ALAS2")
   - Uncertainty about the exact answer (e.g., "I'm uncertain which isoform lacks structures")
   
3. **Apply decision criteria**:
   - ✅ **PASS (proceed)** if:
     - Answer requires specific current database values (counts, IDs, measurements)
     - Requires cross-database integration of multiple entities
     - Requires temporal data (2024 updates, recent deposits)
     - General knowledge insufficient without systematic validation
   
   - ❌ **FAIL (reject/reformulate)** if:
     - You can state the answer with reasonable confidence
     - A reasonable web search would likely find the answer
     - It's a famous association or historical fact
     - It's textbook knowledge in the field

4. **Document the test**:
   ```yaml
   training_knowledge_test:
     attempted_answer: "What I think I know about this question"
     confidence_level: "low|medium|high"
     knowledge_sources: "What general knowledge I have about this topic"
     requires_database: true|false
     reason: "Why this passes or fails the test"
     decision: "PASS - proceed to discovery | FAIL - reformulate question"
   ```

**Examples**:

**Example 1: FAIL (training knowledge sufficient)**
- Question: "Is BRCA1 involved in DNA repair?"
- Attempted answer: "Yes, BRCA1 is well-known to be involved in DNA repair, particularly homologous recombination"
- Confidence: High
- Decision: FAIL - this is textbook knowledge, reformulate

**Example 2: PASS (database required)**
- Question: "Which human heme biosynthesis enzyme isoform lacks PDB structures?"
- Attempted answer: "I know ALAS has isoforms ALAS1 and ALAS2, and there may be structural coverage differences, but I don't know which specific isoform lacks structures or current PDB coverage"
- Confidence: Low
- Requires database: Yes - need current PDB cross-reference checking across all pathway enzymes
- Decision: PASS - proceed to discovery

**Example 3: BORDERLINE → Reformulate to strengthen**
- Question: "Which kinase inhibitor was first FDA-approved?"
- Attempted answer: "Imatinib (Gleevec) in 2001"
- Confidence: High
- Decision: FAIL - historical fact, but could reformulate to: "Which kinases gained FDA-approved inhibitors in 2023-2024?" (requires current database state)

**CRITICAL**: If you FAIL this test, either:
- Reformulate to require current database state
- Reformulate to require multi-entity integration
- Abandon and select different question

This step is **non-negotiable**. Never skip it.

### 2. Discovery
**TogoMCP search tools + optional SPARQL exploration**

1. **Execute search APIs** (exploratory phase - finding patterns and examples):
   - Use search_uniprot_entity, search_chembl_target, search_reactome_entity, ncbi_esearch, etc.
   - Limit to 10-20 results per search
   - Document entity IDs discovered (these become cross-reference anchors)
   - **For comprehensive questions**: Note search terms that should be used in SPARQL
   - **For comprehensive questions**: Identify multiple synonyms/variations needed for complete coverage
   
2. **Map cross-database links**:
   - Note how entities connect (e.g., UniProt P09917 → ChEMBL215 via target search)
   - Identify which databases share which identifiers
   - Plan SPARQL queries to validate these connections
   
3. **Initial SPARQL exploration** (optional):
   - Test queries on Claude's computer to understand data structure
   - Check if cross-references exist (rdfs:seeAlso, skos:exactMatch, etc.)
   - **For comprehensive questions**: Test bif:contains patterns with multiple search terms
   
4. **Identify 3-5 concrete examples** demonstrating the biological pattern

5. **Plan comprehensive vs. example-based approach**:
   - **Comprehensive questions**: Plan to use bif:contains with all synonyms, not VALUES
   - **Example-based questions**: Can use discovered IDs for specific lookups
   - Document which approach and why

6. **Assess feasibility**: 
   - Can this be integrated? (Clear data flow between databases?)
   - Is it verifiable? (Bounded scope?)
   - Does it need RDF? (Test PubMed quickly)
   - Does it need current database state? (Already confirmed in Step 1.5)
   - **For yes/no questions**: Can we comprehensively search ALL entities, not just examples?

**Output**: List of entity IDs, cross-reference mappings, search terms for comprehensive queries, and integration strategy

### 3. Validation
**Claude's computer - bash_tool (for testing) + TogoMCP tools (for execution)**

1. **Write SPARQL queries** - CRITICAL decision point:
   
   **For comprehensive questions (yes/no, existence, distribution):**
   - ✅ Use bif:contains with multiple search terms: `?fullName bif:contains "'term1' OR 'term2' OR 'term3'"`
   - ✅ Search ALL entities matching criteria
   - ✅ Use multiple synonyms and variations
   - ✅ Aggregate by classification (phylum, GO term, etc.)
   - ❌ NEVER use VALUES with hardcoded search results
   - ❌ NEVER rely on limited search API results as complete dataset
   
   **For example-based questions (top-N, specific lookups):**
   - ✅ Can use VALUES with specific entity IDs
   - ✅ Can build on search API discoveries
   - ✅ Focused queries on known entities
   
2. Test SPARQL queries using TogoMCP tools (one query per database endpoint)
3. **Validate cross-database integration** - ensure IDs/cross-references link correctly across queries
4. For multi-DB questions: Query DB1 → extract IDs → Query DB2 with those IDs → combine results
5. Confirm answer completeness (COUNT/EXISTS/ORDER BY)
6. **For yes/no questions**: Verify you've queried comprehensively, not just validated examples
7. Extract RDF triples as evidence from SPARQL results
8. Cross-validate with alternative query formulations
9. **Document data flow**: How does information flow between databases? Which IDs link them?

### 4. PubMed Test
**PubMed MCP tools**

1. Attempt to answer using PubMed tools (reasonable effort)
2. Try 2-3 different search queries
3. Document search queries, PMID results, and why they fail
4. **Self-checks in order:**
   - Can Claude answer from training knowledge? → Already tested in Step 1.5
   - Can PubMed answer with reasonable effort? → Test now
   - Does question require current database counts/IDs? → Already confirmed
   - Does question need cross-database integration? → Test now

**Good PubMed test documentation**:
- Lists specific search queries attempted
- Notes number of articles found and sample PMIDs
- Explains why literature is insufficient (scattered data, no systematic integration, missing quantitative details)
- Explains why RDF database access is essential

**Weak PubMed test documentation**:
- "Cannot answer from PubMed" without trying
- No specific queries listed
- Doesn't explain gap between literature and RDF approach

### 5. Documentation
**User's computer - Filesystem:write_file ONLY**

Create YAML with required sections (including training_knowledge_test from Step 1.5):

```yaml
id: question_XXX
type: factoid|yes_no|list|summary
body: "Biological question here"

inspiration_keyword:
  keyword_id: KW-XXXX
  name: "Keyword name"

togomcp_databases_used:
  - Database1
  - Database2
  - Database3

search_apis_used:
  - tool: search_xxx
    query: "search string"
    result: "What was found and how it connects to other DBs - EXPLORATORY PHASE ONLY"

training_knowledge_test:
  attempted_answer: "What Claude thinks it knows"
  confidence_level: "low|medium|high"
  knowledge_sources: "General knowledge about this topic"
  requires_database: true
  reason: "Why database access is essential"
  decision: "PASS - proceeded to discovery"

verification_score:
  biological_insight: 3
  multi_database: 3
  verifiability: 3
  rdf_necessity: 3
  total: 12
  passed: true
  rationale: "Why each dimension scored high"

pubmed_test:
  passed: true
  queries_attempted:
    - "query 1"
    - "query 2"
  pmids_found: ["12345", "67890"]
  conclusion: "Cannot answer - requires integration across DBs with specific evidence"

sparql_queries:
  - query_number: 1
    database: Database1
    description: "Purpose and discovery method"
    discovery_method: "search_api('query') identified patterns; SPARQL queries COMPREHENSIVELY using bif:contains"
    query: |
      # For yes/no questions: MUST use bif:contains, NOT VALUES
      # For phylogenetic questions: MUST query all organisms, NOT hardcoded list
      SELECT ...
      WHERE {
        ?entity up:recommendedName ?name .
        ?name up:fullName ?fullName .
        ?fullName bif:contains "'term1' OR 'term2' OR 'term3'"  # Comprehensive search
        # NOT: VALUES ?entity { <id1> <id2> }  # This is circular reasoning!
      }
    result_count: N
    key_findings: "What this COMPREHENSIVE query revealed"

rdf_triples: |
  # Discovery: search_xxx("query") → found examples (exploratory)
  # Validation: Query N searched ALL entities comprehensively
  <subject> <predicate> <object> .
  # Database: XX | Query: N | Comment: Why this matters biologically

exact_answer: "Answer here"

ideal_answer: |
  SINGLE PARAGRAPH ONLY - synthesis explaining biological significance,
  not tool references or database details. NO MULTIPLE PARAGRAPHS.
```

**Critical format requirements:**
- **training_knowledge_test**: MUST be included showing explicit self-test
- **search_apis_used**: Clearly label as "exploratory phase" - not final evidence
- **sparql_queries**: For comprehensive questions, must document use of bif:contains, not VALUES
- **discovery_method**: Explain whether query is comprehensive (bif:contains) or example-based (VALUES)
- ideal_answer: SINGLE PARAGRAPH - no line breaks, no multiple paragraphs
- rdf_triples: Every claim in exact_answer must have supporting triple
- verification_score: Include detailed rationale for each dimension

Save question:
```python
Filesystem:write_file(
    path="/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml",
    content="..."
)
```

Update tracker:
```python
Filesystem:write_file(
    path="/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/coverage_tracker.yaml",
    content="..."
)
```

### 6. Validation
**User's computer - Filesystem:read_text_file**

Read back and verify:
```python
Filesystem:read_text_file(
    path="/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/questions/question_XXX.yaml"
)
```

Verify:
- YAML structure correct
- **training_knowledge_test section present and complete**
- **For yes/no questions: SPARQL uses bif:contains, NOT VALUES with hardcoded IDs**
- **Search APIs clearly labeled as exploratory, not final evidence**
- Integration patterns documented (clear data flow)
- Evidence from comprehensive SPARQL (not search APIs alone)
- Biological insight clear
- ideal_answer is SINGLE paragraph
- Database balance maintained (checked tracker)
- All RDF triples present
- PubMed test thorough

---

## Examples

### ❌ Circular Reasoning with Search Results (Bad - Common Error!)
**Question**: "Are bacterial rhamnosyltransferases found in phyla other than Pseudomonadota and Actinomycetota?"

**WRONG approach**:
```yaml
search_apis_used:
  - tool: search_uniprot_entity
    query: "rhamnosyltransferase"
    result: "Found P9WMY3 (Mycobacterium), P36667 (E. coli), Q88LS1 (Pseudomonas)"

sparql_queries:
  - query: |
      # WRONG - Hardcoding the search results!
      VALUES ?protein { 
        uniprot:P9WMY3 uniprot:P36667 uniprot:Q88LS1
      }
      ?protein up:organism ?org .
      ?org rdfs:subClassOf+ ?phylum .
```
**Problem**: Only verified the 3 proteins from search - circular reasoning! Missed proteins in Spirochaetota, Fusobacteriota, etc.

**CORRECT approach**:
```yaml
search_apis_used:
  - tool: search_uniprot_entity
    query: "rhamnosyltransferase"
    result: "Found examples in Mycobacterium, E. coli, Pseudomonas - EXPLORATORY PHASE to identify search patterns"

sparql_queries:
  - query: |
      # CORRECT - Comprehensive search with multiple terms
      SELECT ?protein ?organism ?phylum
      WHERE {
        ?protein up:reviewed 1 ;
                 up:recommendedName ?name ;
                 up:organism ?organism .
        ?name up:fullName ?fullName .
        ?fullName bif:contains "'rhamnosyltransferase' OR 'protein-arginine rhamnosyl' OR 'WbbL'"
        ?organism rdfs:subClassOf+ ?phylum .
        ?phylum up:rank "phylum" .
      }
```
**Why correct**: Searches ALL proteins comprehensively, not just the examples found in search.

### ❌ Training Knowledge Answerable (Bad)
"Is BRCA1 involved in DNA repair?"
- **Problem**: General knowledge, no database needed
- **Claude knows**: Yes, from training data
- **No RDF needed**: Basic biological fact
- **Training knowledge test would FAIL**

### ❌ Training Knowledge Answerable (Bad)
"Which human kinase inhibitor was first FDA-approved?"
- **Problem**: Historical fact in training knowledge
- **Claude knows**: Imatinib (Gleevec), 2001
- **No RDF needed**: Well-documented milestone
- **Training knowledge test would FAIL**

### ❌ Database Inventory (Bad)
"How many proteins in UniProt have apoptosis annotations?"
- **Problem**: Database completeness, not biology
- **Single DB**: UniProt only
- **No insight**: Just counting annotations

### ✅ Biological Integration (Good)
"Which apoptosis regulators have structural data for their protein interaction domains?"
- **Biology**: Understanding molecular mechanisms of apoptosis regulation
- **Integration**: Query GO for apoptosis terms → Query UniProt for proteins with those GO annotations → Filter proteins with PDB cross-references (rdfs:seeAlso) → 3 databases, 2-3 SPARQL queries
- **Comprehensive approach**: Query ALL proteins with apoptosis GO terms, not just examples
- **Insight**: Reveals which regulatory interactions are structurally characterized
- **Verifiable**: Bounded set of proteins with specific domain types
- **Requires database**: Specific current counts and IDs, not in training knowledge
- **Training knowledge test**: Would PASS - requires current PDB coverage

### ❌ Ontology Metadata (Bad)
"Is type 1 diabetes classified as autoimmune disease in MONDO?"
- **Problem**: Asking about ontology structure, not biology
- **Single DB**: MONDO only
- **No insight**: Just database organization

### ✅ Clinical Integration (Good)
"Which autoimmune diseases share risk genes with type 1 diabetes?"
- **Biology**: Understanding genetic overlap in autoimmune conditions
- **Integration**: Query ClinVar for T1DM-associated genes → Query MONDO for other autoimmune diseases → Query ClinVar for genes in those diseases → Find overlap (3 databases, 3-4 SPARQL queries)
- **Comprehensive approach**: Query ALL T1DM genes from ClinVar, not select examples
- **Insight**: Reveals shared genetic architecture
- **Verifiable**: Enumerate overlapping genes
- **Training knowledge test**: Would PASS - requires systematic gene-disease associations

### ✅ Counting for Insight (Good - acceptable inventory)
"Which 5 manganese-binding proteins have the most crystal structures?"
- **Why acceptable**: Ranking reveals research priorities and structural characterization patterns
- **Integration**: UniProt search → PDB cross-reference counting → ranking by structure count
- **Example-based OK**: Top-N ranking can use discovered proteins
- **Insight**: Shows which manganese-dependent functions are most studied structurally
- **Requires database**: Current PDB counts change monthly, not in training knowledge
- **Training knowledge test**: Would PASS - requires current structure counts

### 🔶 Borderline Case (Needs Reformulation)
"Which human heme biosynthesis enzyme isoform lacks PDB structures?"
- **Current status**: Borderline - answer might be discoverable through literature
- **Training knowledge**: Know pathway has isoforms, uncertain about specific structural gaps
- **Better reformulation**: "How does PDB structural coverage differ between tissue-specific and housekeeping isoforms across all human metabolic pathways?"
- **Why better**: Broader pattern, requires systematic comparison, clearly needs database aggregation

---

## Key Principles Summary

1. **Biology first**: Ask what researchers want to know, not what databases contain
2. **Integration via multiple queries**: 60%+ must use 2+ databases through separate queries linked by IDs/cross-references
3. **Requires database access**: Must need current database state - not answerable from Claude's training knowledge (tested explicitly in Step 1.5)
4. **Search discovers, SPARQL validates comprehensively**: Search APIs find patterns/examples (exploratory), SPARQL provides comprehensive evidence
5. **Comprehensive vs. example-based queries**: 
   - Yes/no questions → bif:contains with all synonyms, NOT VALUES with search results
   - Top-N rankings → can use discovered entity IDs
   - Phylogenetic distribution → query ALL organisms, aggregate by classification
6. **Verifiable scopes**: Single answer, ≤10 items, or aggregate value
7. **Score ≥8**: Including biological insight and multi-DB integration
8. **Database diversity**: Cap UniProt at 70%, prioritize underused databases
9. **Random keyword selection**: Pure random from unused keywords - no thematic bias or strategic clustering
10. **Workspace discipline**: Filesystem for `/Users/arkinjo/...`, TogoMCP tools for SPARQL execution
11. **Ideal answer format**: SINGLE PARAGRAPH ONLY - no multiple paragraphs, no line breaks
12. **Mandatory self-test**: ALWAYS complete training knowledge test (Step 1.5) before proceeding
13. **Avoid circular reasoning**: Never use VALUES with hardcoded search results for comprehensive questions

**Integration model**: Search API discovery (exploratory) → comprehensive SPARQL validation → combine results

**Distribution**: 60%+ multi-database, even type split, **random keyword selection**, balanced database usage
**Focus**: TogoMCP's unified access to distributed databases, biological insight, verifiable answers

---

## Version History

**v2.4 (2025-02-06)**: Critical revision - comprehensive vs. example-based queries
- **MAJOR**: Added comprehensive query requirements for yes/no and existence questions
- **MAJOR**: Documented circular reasoning trap with search APIs → VALUES hardcoding
- New section: "CRITICAL: Comprehensive vs. Example-Based Queries"
- Updated all workflow steps to emphasize comprehensive SPARQL for yes/no questions
- Added requirement to use bif:contains with multiple search terms
- Prohibited VALUES clauses with hardcoded search results for comprehensive questions
- Added new examples showing WRONG (circular reasoning) vs. CORRECT (comprehensive) approaches
- Updated YAML template to document comprehensive vs. example-based approach
- Updated Common Pitfalls section with circular reasoning warning
- Based on analysis of question_004.yaml error

**v2.3 (2025-02-05)**: Removed time estimates
- Removed all time estimates from workflow steps
- Removed time_spent section from YAML template
- Changed "15 min" constraints to "reasonable effort"
- Removed "3-5 hours per question" guidance
- Time estimates were unreliable and not useful

**v2.2 (2025-02-05)**: Enforced random keyword selection
- **CRITICAL**: Keyword selection must be purely random - no thematic choice or bias
- Updated Planning step (Step 1) to detail random selection process
- Added to Quality Standards and Key Principles Summary
- Updated Common Pitfalls to emphasize random selection over manual diversification
- Random selection eliminates clustering bias observed in questions 1-7

**v2.1 (2025-02-05)**: Added mandatory training knowledge self-test
- NEW: Step 1.5 - Training Knowledge Self-Test (mandatory gate before discovery)
- Added training_knowledge_test section to YAML format
- Updated workflow from 6 to 7 steps
- Added explicit examples of PASS/FAIL criteria for self-test
- Strengthened "Cannot answer from training knowledge" requirement

**v2.0 (2025-02-05)**: Major revision based on questions 1-7 analysis
- Added database balance requirements (UniProt cap, priority databases)
- Acknowledged Search API → SPARQL as valid integration pattern
- Clarified training knowledge boundary with test criteria
- Nuanced database inventory prohibition (counting can be acceptable)
- Strengthened ideal answer single-paragraph enforcement
- Added non-protein integration patterns
- Added common pitfalls section
- Added database-specific strategies
- Improved PubMed test guidance

**v1.0 (2025-01-XX)**: Original guidelines
