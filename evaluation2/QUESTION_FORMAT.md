# Question YAML File Format Specification

## Overview

This document specifies the YAML file format for BioASQ benchmark questions in the TogoMCP evaluation dataset. Each question is stored as a separate YAML file with structured metadata, SPARQL queries, RDF evidence, and reference answers.

## File Naming Convention

```
question_{sequential_number}.yaml
```

**Examples:**
- `question_001.yaml`
- `question_042.yaml`
- `question_123.yaml`

**Rules:**
- Use zero-padded sequential numbering (3 digits minimum)
- Numbers must be unique within the dataset

## File Structure

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique question identifier (format: `question_XXX`) |
| `type` | enum | Question type: `yes_no`, `factoid`, `list`, `summary`, or `choice` |
| `body` | string | The question text (stand-alone, no database names) |
| `choices` | array | Choice options (required only for `choice` type) |
| `inspiration_keyword` | object | Keyword that inspired the question |
| `togomcp_databases_used` | array | List of TogoMCP databases queried |
| `verification_score` | object | Verification scoring results |
| `pubmed_test` | object | Results of PubMed answerability test |
| `sparql_queries` | array | All SPARQL queries used to answer the question |
| `rdf_triples` | string | RDF triples extracted as evidence (Turtle format) |
| `exact_answer` | varies | Precise answer in type-appropriate format |
| `ideal_answer` | string | Synthesized paragraph answer for experts |
| `question_template_used` | string | Template used for question formulation |
| `time_spent` | object | Time breakdown for question creation |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `documents` | array | PubMed articles referenced (if any) |
| `snippets` | array | Text snippets from literature (if needed) |

---

## Field Specifications

### `id`

**Type:** String  
**Format:** `question_{number}`  
**Required:** Yes

**Description:** Unique identifier for the question.

**Example:**
```yaml
id: question_001
```

---

### `type`

**Type:** Enum  
**Required:** Yes  
**Allowed Values:**
- `yes_no` - Binary yes/no question (⚠️ **CRITICAL**: Must use comprehensive SPARQL with bif:contains, NEVER VALUES from search results)
- `factoid` - Single factual answer (count, name, value)
- `list` - Enumerated list of items (≤10 items, with ranking/filtering)
- `summary` - Narrative synthesis answer (**SINGLE PARAGRAPH**, no line breaks)
- `choice` - Multiple choice question with predefined options

**Description:** Question type determines the format of `exact_answer` and SPARQL approach required.

**Example:**
```yaml
type: factoid
```

---

### `body`

**Type:** String  
**Required:** Yes  
**Constraints:**
- Must be stand-alone (no pronouns referencing other questions)
- No explicit database names (e.g., "in UniProt")
- Must reflect actual biomedical information needs
- Should be clear and unambiguous

**Description:** The question text as it would appear in the benchmark.

**Example:**
```yaml
body: "How many human protein kinases annotated with 'protein kinase activity' have at least one experimentally determined crystal structure?"
```

---

### `choices`

**Type:** Array of Strings  
**Required:** Only for `type: choice`  
**Constraints:**
- Minimum 2 choices
- Maximum 10 choices (typically 4-5)
- At least one correct answer must exist
- Choices should be plausible distractors
- Order may be randomized during presentation

**Description:** Array of possible answer choices for multiple choice questions.

**Example:**
```yaml
choices:
  - "Proteobacteria"
  - "Firmicutes"
  - "Actinobacteria"
  - "Bacteroidetes"
```

---

### `inspiration_keyword`

**Type:** Object  
**Required:** Yes

**Structure:**
```yaml
inspiration_keyword:
  keyword_id: string    # Format: KW-XXXX
  name: string          # Keyword name
  category: string      # Category from keywords.tsv
```

**Description:** The keyword from `keywords.tsv` that inspired this question.

**Example:**
```yaml
inspiration_keyword:
  keyword_id: KW-0001
  name: Kinase
  category: Molecular function
```

---

### `togomcp_databases_used`

**Type:** Array of Strings  
**Required:** Yes  
**Minimum:** 1 database  
**Recommended:** 2-4 databases  

**Dataset Composition Targets (50 total questions):**
- **Multi-database (2+):** ≥60% (minimum 30 questions)
- **Multi-database (3+):** ≥20% (minimum 10 questions)
- **Single-database:** ≤40% (maximum 20 questions)
- **UniProt cap:** ≤70% (maximum 35 questions) - avoid over-reliance on UniProt

**Allowed Values:**
`uniprot`, `rhea`, `pubchem`, `pdb`, `chembl`, `chebi`, `reactome`, `ensembl`, `amrportal`, `mesh`, `go`, `taxonomy`, `mondo`, `nando`, `bacdive`, `mediadive`, `clinvar`, `pubmed`, `pubtator`, `ncbigene`, `medgen`, `ddbj`, `glycosmos`

**Description:** List of TogoMCP databases queried via SPARQL. Multi-database integration showcases TogoMCP's core strength and should be prioritized.

**Examples:**

Multi-database (preferred):
```yaml
togomcp_databases_used:
  - uniprot
  - pdb
  - go
```

Single-database (acceptable if high-scoring on other dimensions):
```yaml
togomcp_databases_used:
  - ncbigene
```

---

### `verification_score`

**Type:** Object  
**Required:** Yes

**Structure:**
```yaml
verification_score:
  biological_insight: integer   # 0-3 points
  multi_database: integer       # 0-3 points
  verifiability: integer        # 0-3 points
  rdf_necessity: integer        # 0-3 points
  total: integer                # Sum (0-12)
  passed: boolean               # true if total ≥9 and no zeros
```

**Constraints:**
- Each dimension: 0-3 points
- Total: 0-12 points
- **Must pass:** `total ≥ 9` AND no dimension has 0
- `passed` must be `true` for accepted questions

**Scoring Dimensions:**
- **biological_insight**: Biological/scientific insight level
  - 0: Database inventory/metadata (reject)
  - 1: Basic biology, limited insight
  - 2: Biological function or properties
  - 3: Mechanisms, patterns, or evolutionary relationships
- **multi_database**: Database integration level
  - 0: Search-only, no RDF
  - 1: Single database OR weak multi-database integration
  - 2: Two databases with clear integration
  - 3: Three or more databases with meaningful integration
- **verifiability**: Answer verifiability
  - 0: Unbounded or subjective
  - 1: Loosely bounded (e.g., "major pathways")
  - 2: 6-10 items or clear aggregate
  - 3: Single answer or ≤5 items with exact criteria
- **rdf_necessity**: Requires RDF graph traversal
  - 0: Answerable from PubMed or training knowledge
  - 1: RDF helpful but not essential
  - 2: RDF significantly enhances answer
  - 3: Impossible without RDF and current database state

**Description:** Mandatory verification scoring using the rubric.

**Example:**
```yaml
verification_score:
  biological_insight: 3
  multi_database: 2
  verifiability: 3
  rdf_necessity: 3
  total: 11
  passed: true
```

---

### `pubmed_test`

**Type:** Object  
**Required:** Yes

**Structure:**
```yaml
pubmed_test:
  time_spent: string        # e.g., "15 minutes"
  method: string            # Description of search attempt
  result: string            # What was found (can be multi-line)
  conclusion: string        # "PASS" or "FAIL" with reason
```

**Description:** Documentation of attempt to answer question using only PubMed within 15 minutes.

**Example:**
```yaml
pubmed_test:
  time_spent: 15 minutes
  method: Searched "human kinases crystal structures PDB" programmatically using search_articles and get_article_metadata
  result: |
    Found several review papers listing some kinases with structures, 
    but no complete count. Would need to manually compile from multiple 
    papers and cross-reference. Cannot determine exact number.
  conclusion: PASS (cannot answer from literature)
```

---

### `sparql_queries`

**Type:** Array of Objects  
**Required:** Yes  
**Minimum:** 1 query

**Structure:**
```yaml
sparql_queries:
  - query_number: integer       # Sequential numbering
    database: string            # Database queried
    description: string         # What this query does
    query: string               # Full SPARQL query (multi-line)
    result_count: integer       # Number of results returned
```

**Constraints:**
- Queries must be executable
- Must use proper SPARQL syntax
- Include all PREFIX declarations
- Query text should be properly indented YAML multi-line string

**Description:** All SPARQL queries executed to answer the question.

**Example:**
```yaml
sparql_queries:
  - query_number: 1
    database: uniprot
    description: Get all human proteins annotated with GO:0004672 (protein kinase activity)
    query: |
      PREFIX up: <http://purl.uniprot.org/core/>
      PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      
      SELECT DISTINCT ?protein
      WHERE {
        ?protein a up:Protein ;
                 up:organism taxon:9606 ;
                 up:classifiedWith <http://purl.obolibrary.org/obo/GO_0004672> .
      }
    result_count: 518
    
  - query_number: 2
    database: uniprot
    description: Count how many of these proteins have PDB cross-references
    query: |
      PREFIX up: <http://purl.uniprot.org/core/>
      PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      
      SELECT (COUNT(DISTINCT ?protein) AS ?count)
      WHERE {
        ?protein a up:Protein ;
                 up:organism taxon:9606 ;
                 up:classifiedWith <http://purl.obolibrary.org/obo/GO_0004672> ;
                 rdfs:seeAlso ?pdb .
        ?pdb a up:PDB_Resource .
      }
    result_count: 1
```

---

### `rdf_triples`

**Type:** String (multi-line)  
**Format:** Turtle (RDF serialization)  
**Required:** Yes

**Structure:**
- PREFIX declarations at top
- Triples organized by query
- Each triple followed by comment indicating source
- Comment format: `# Database: X | Query: N | Comment: Relevance`

**Description:** RDF triples extracted from SPARQL query results as evidence.

**Example:**
```yaml
rdf_triples: |
  @prefix up: <http://purl.uniprot.org/core/> .
  @prefix pdb: <http://rdf.wwpdb.org/pdb/> .
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
  
  <http://purl.uniprot.org/uniprot/P04637> a up:Protein .
  # Database: UniProt | Query: 1 | Comment: TP53 protein entry
  
  <http://purl.uniprot.org/uniprot/P04637> rdfs:seeAlso <http://rdf.wwpdb.org/pdb/1TUP> .
  # Database: UniProt | Query: 2 | Comment: Cross-reference to PDB structure
  
  <http://rdf.wwpdb.org/pdb/1TUP> pdb:has_resolution "2.1"^^xsd:float .
  # Database: PDB | Query: 3 | Comment: Structure resolution value
```

**Constraints:**
- Must be valid Turtle syntax
- All URIs must be complete (no abbreviated forms without PREFIX)
- Comments are mandatory for traceability
- Should include cross-database links

---

### `documents`

**Type:** Array of Objects  
**Required:** No (only if PubMed articles used)

**Structure:**
```yaml
documents:
  - pmid: string           # PubMed ID
    title: string          # Article title
    url: string            # PubMed URL
```

**Description:** PubMed articles referenced (should be minimal, <20% of evidence).

**Example:**
```yaml
documents:
  - pmid: "12345678"
    title: "Crystal structures of protein kinases"
    url: https://pubmed.ncbi.nlm.nih.gov/12345678/
```

---

### `snippets`

**Type:** Array of Objects  
**Required:** No (only if text snippets needed)

**Structure:**
```yaml
snippets:
  - text: string                      # Complete sentence(s)
    document: string                  # PMID reference
    offsetInBeginSection: integer     # Character offset start
    offsetInEndSection: integer       # Character offset end
```

**Description:** Text snippets from literature (only when RDF triples insufficient).

**Example:**
```yaml
snippets:
  - text: "Protein kinases represent one of the largest protein families, with over 500 members in the human genome."
    document: "12345678"
    offsetInBeginSection: 0
    offsetInEndSection: 108
```

---

### `exact_answer`

**Type:** Varies by question type  
**Required:** Yes

**Format by Type:**

#### For `yes_no` questions:
```yaml
exact_answer: "yes"  # or "no"
```

**⚠️ CRITICAL REQUIREMENT for yes/no questions:**
- SPARQL must use **comprehensive** query with `bif:contains` and multiple synonyms
- **NEVER** use VALUES clause with IDs from search API results (circular reasoning)
- Use EXISTS/NOT EXISTS patterns for validation
- See QA_CREATION_GUIDE.md "AVOID CIRCULAR REASONING" section

#### For `factoid` questions:
```yaml
exact_answer: "Entity Name (Database:ID)"
```

Example:
```yaml
exact_answer: "JAK2 (UniProt:O60674)"
```

#### For `list` questions (≤10 items):
```yaml
exact_answer:
  - "Entity1 (DB:ID1)"
  - "Entity2 (DB:ID2)"
  - "Entity3 (DB:ID3)"
```

Example:
```yaml
exact_answer:
  - "JAK2 (UniProt:O60674)"
  - "EGFR (UniProt:P00533)"
  - "BRAF (UniProt:P15056)"
```

#### For `choice` questions:
**Format:** Array of strings (subset of `choices` field)

**Single correct answer:**
```yaml
exact_answer:
  - "Actinobacteria"
```

**Multiple correct answers (if applicable):**
```yaml
exact_answer:
  - "Parkinsonian disorder"
  - "Hereditary neurological disease"
```

**Constraints:**
- Must be an array (even for single answer)
- All items must exist in the `choices` field
- At least one item required

#### For count/aggregation questions:
```yaml
exact_answer: 127  # or "127.5" for averages
```

#### For `summary` questions:
```yaml
exact_answer: ""  # Leave blank
```

**Description:** The precise, verifiable answer extracted from SPARQL results.

---

### `ideal_answer`

**Type:** String (multi-line)  
**Required:** Yes

**Constraints:**
- One paragraph (can be long)
- Synthesizes information from RDF triples
- Written for domain experts
- No meta-references (e.g., "According to UniProt...")
- Natural integration of data from multiple databases
- Includes specific quantitative data
- No mention of SPARQL or queries

**Additional Constraints for `choice` Questions:**
- Must explain why the correct answer(s) is/are correct
- Should explain why the incorrect options are wrong
- Should provide biological context for the comparison

**Description:** Expert-level synthesized answer based on RDF evidence.

**Example (factoid):**
```yaml
ideal_answer: |
  There are 127 human protein kinases annotated with 'protein kinase activity' 
  (GO:0004672) that have at least one experimentally determined crystal structure 
  deposited in PDB. This represents approximately 24% of the 518 human kinases 
  annotated with this molecular function. The structures range in resolution from 
  0.92 Å to 3.5 Å, with a median resolution of 2.1 Å. The most extensively 
  structurally characterized kinases include EGFR with 87 structures, CDK2 with 
  54 structures, and Aurora kinase A with 47 structures. These structural data 
  provide insights into kinase conformational states, substrate binding, and 
  inhibitor interactions that are critical for drug development.
```

**Example (choice):**
```yaml
ideal_answer: |
  Actinobacteria shows the highest number of spore-forming strains in BacDive 
  with approximately 25,000 strains from spore-forming genera (primarily 
  Streptomyces with ~24,500 strains, plus Micromonospora and others). This 
  significantly exceeds Firmicutes (~4,400 spore-forming strains) despite 
  Firmicutes being famous for endospore formation. While Firmicutes produce 
  heat-resistant endospores through asymmetric cell division, Actinobacteria 
  produce exospores via aerial hyphal differentiation. The dominance of 
  Actinobacteria in culture collections reflects extensive Streptomyces 
  isolation for antibiotic screening programs. Proteobacteria and Bacteroidetes 
  are not known to contain significant numbers of spore-forming genera.
```

---

### `question_template_used`

**Type:** String  
**Required:** Yes

**Allowed Values:**
- `Template 1 (Ontology Counting)`
- `Template 2 (Cross-Database Counting)`
- `Template 3 (Extrema Finding)`
- `Template 4 (Aggregation Statistics)`
- `Template 5 (Bounded Comparison)`
- `Template 6 (TOP-N Ranking)`
- `Template 7 (Yes/No Existence)`
- `Template 8 (Percentage Calculation)`
- Or custom template name

**Description:** Which question template was used during formulation.

**Example:**
```yaml
question_template_used: Template 2 (Cross-Database Counting)
```

---

### `time_spent`

**Type:** Object  
**Required:** Yes

**Structure:**
```yaml
time_spent:
  exploration: string      # e.g., "90 minutes"
  formulation: string      # e.g., "25 minutes"
  verification: string     # e.g., "110 minutes"
  pubmed_test: string      # e.g., "15 minutes"
  extraction: string       # e.g., "50 minutes"
  documentation: string    # e.g., "40 minutes"
  total: string            # e.g., "330 minutes" or "5.5 hours"
```

**Description:** Time breakdown for creating the question.

**Example:**
```yaml
time_spent:
  exploration: 90 minutes
  formulation: 25 minutes
  verification: 110 minutes
  pubmed_test: 15 minutes
  extraction: 50 minutes
  documentation: 40 minutes
  total: 330 minutes
```

---

## Complete Examples

### Example 1: Factoid Question

```yaml
id: question_001
type: factoid
body: "How many human protein kinases annotated with 'protein kinase activity' have at least one experimentally determined crystal structure?"

inspiration_keyword:
  keyword_id: KW-0001
  name: Kinase
  category: Molecular function

togomcp_databases_used:
  - uniprot
  - pdb
  - go

verification_score:
  biological_insight: 3
  multi_database: 2
  verifiability: 3
  rdf_necessity: 3
  total: 11
  passed: true

pubmed_test:
  time_spent: 15 minutes
  method: Searched "human kinases crystal structures PDB" using search_articles
  result: |
    Found several review papers listing some kinases with structures, 
    but no complete count. Would need to manually compile from multiple 
    papers and cross-reference. Cannot determine exact number.
  conclusion: PASS (cannot answer from literature)

sparql_queries:
  - query_number: 1
    database: uniprot
    description: Get all human proteins annotated with GO:0004672 (protein kinase activity)
    query: |
      PREFIX up: <http://purl.uniprot.org/core/>
      PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
      
      SELECT DISTINCT ?protein
      WHERE {
        ?protein a up:Protein ;
                 up:organism taxon:9606 ;
                 up:classifiedWith <http://purl.obolibrary.org/obo/GO_0004672> .
      }
    result_count: 518
    
  - query_number: 2
    database: uniprot
    description: Count how many of these proteins have PDB cross-references
    query: |
      PREFIX up: <http://purl.uniprot.org/core/>
      PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      
      SELECT (COUNT(DISTINCT ?protein) AS ?count)
      WHERE {
        ?protein a up:Protein ;
                 up:organism taxon:9606 ;
                 up:classifiedWith <http://purl.obolibrary.org/obo/GO_0004672> ;
                 rdfs:seeAlso ?pdb .
        ?pdb a up:PDB_Resource .
      }
    result_count: 1

rdf_triples: |
  @prefix up: <http://purl.uniprot.org/core/> .
  @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
  
  <http://purl.uniprot.org/uniprot/O60674> a up:Protein .
  # Database: UniProt | Query: 1 | Comment: JAK2 kinase entry
  
  <http://purl.uniprot.org/uniprot/O60674> rdfs:seeAlso <http://rdf.wwpdb.org/pdb/3KRR> .
  # Database: UniProt | Query: 2 | Comment: Cross-reference to PDB structure

exact_answer: 127

ideal_answer: |
  There are 127 human protein kinases annotated with 'protein kinase activity' 
  (GO:0004672) that have at least one experimentally determined crystal structure 
  deposited in PDB. This represents approximately 24% of the 518 human kinases 
  annotated with this molecular function. The structures range in resolution from 
  0.92 Å to 3.5 Å, with a median resolution of 2.1 Å. The most extensively 
  structurally characterized kinases include EGFR with 87 structures, CDK2 with 
  54 structures, and Aurora kinase A with 47 structures.

question_template_used: Template 2 (Cross-Database Counting)

time_spent:
  exploration: 90 minutes
  formulation: 25 minutes
  verification: 110 minutes
  pubmed_test: 15 minutes
  extraction: 50 minutes
  documentation: 40 minutes
  total: 330 minutes
```

### Example 2: Choice Question

```yaml
id: question_029
type: choice
body: "Based on cultured bacterial diversity in the BacDive database, which phylum shows the highest number of strains from spore-forming genera?"

choices:
  - "Proteobacteria"
  - "Firmicutes"
  - "Actinobacteria"
  - "Bacteroidetes"

inspiration_keyword:
  keyword_id: KW-0749
  name: Sporulation
  category: Biological process

togomcp_databases_used:
  - bacdive

verification_score:
  biological_insight: 2
  multi_database: 2
  verifiability: 3
  rdf_necessity: 2
  total: 11
  passed: true

pubmed_test:
  time_spent: 15 minutes
  method: Searched for bacterial sporulation literature and spore-forming genera
  result: |
    PubMed confirms that both Firmicutes (endospores) and Actinobacteria 
    (exospores) are spore-forming phyla, but does not provide current strain 
    counts from culture collections by phylum.
  conclusion: PASS (cannot answer from literature - requires current database state)

sparql_queries:
  - query_number: 1
    database: bacdive
    description: Check phylum distribution
    query: |
      PREFIX schema: <https://purl.dsmz.de/schema/>
      
      SELECT ?phylum (COUNT(DISTINCT ?strain) as ?strainCount)
      FROM <http://rdfportal.org/dataset/bacdive>
      WHERE {
        ?strain a schema:Strain ;
                schema:hasPhylum ?phylum .
      }
      GROUP BY ?phylum
      ORDER BY DESC(?strainCount)
      LIMIT 10
    result_count: 10

  - query_number: 2
    database: bacdive
    description: Count total spore-forming strains by phylum
    query: |
      PREFIX schema: <https://purl.dsmz.de/schema/>
      
      SELECT ?phylum (COUNT(DISTINCT ?strain) as ?sporeFormingStrains)
      FROM <http://rdfportal.org/dataset/bacdive>
      WHERE {
        VALUES ?genus { 
          "Bacillus" "Clostridium" "Geobacillus" "Paenibacillus" 
          "Streptomyces" "Micromonospora" "Actinoplanes"
        }
        
        ?strain a schema:Strain ;
                schema:hasGenus ?genus ;
                schema:hasPhylum ?phylum .
                
        FILTER(?phylum IN ("Firmicutes", "Bacillota", "Actinobacteria", "Actinomycetota"))
      }
      GROUP BY ?phylum
      ORDER BY DESC(?sporeFormingStrains)
    result_count: 4

rdf_triples: |
  @prefix schema: <https://purl.dsmz.de/schema/> .
  
  <https://purl.dsmz.de/bacdive/strain/1> a schema:Strain .
  # Database: BacDive | Query: 1 | Comment: Example strain entity
  
  <https://purl.dsmz.de/bacdive/strain/1> schema:hasGenus "Bacillus" .
  # Database: BacDive | Query: 2 | Comment: Spore-forming genus
  
  <https://purl.dsmz.de/bacdive/strain/1> schema:hasPhylum "Firmicutes" .
  # Database: BacDive | Query: 2 | Comment: Phylum classification

exact_answer:
  - "Actinobacteria"

ideal_answer: |
  Actinobacteria shows the highest number of spore-forming strains in BacDive 
  with approximately 25,000 strains from spore-forming genera (primarily 
  Streptomyces with ~24,500 strains). This significantly exceeds Firmicutes 
  (~4,400 spore-forming strains) despite Firmicutes being famous for endospore 
  formation. While Firmicutes produce heat-resistant endospores, Actinobacteria 
  produce exospores via aerial hyphal differentiation. The dominance reflects 
  extensive Streptomyces isolation for antibiotic screening. Proteobacteria and 
  Bacteroidetes do not contain significant numbers of spore-forming genera.

question_template_used: choice_comparative_quantitative

time_spent:
  exploration: 30 minutes
  formulation: 10 minutes
  verification: 25 minutes
  pubmed_test: 15 minutes
  extraction: 20 minutes
  documentation: 20 minutes
  total: 120 minutes
```

---

## Validation Rules

### YAML Syntax
- [ ] Valid YAML syntax (proper indentation, no tabs)
- [ ] All required fields present
- [ ] Field types match specification
- [ ] Multi-line strings use `|` or `>` correctly

### Content Validation
- [ ] `id` matches filename
- [ ] `type` is one of allowed values
- [ ] For `type: choice`: `choices` field is present with 2-10 items
- [ ] For `type: yes_no`: SPARQL uses comprehensive query (bif:contains), NOT VALUES from search
- [ ] For `type: summary`: `ideal_answer` is single paragraph (no line breaks)
- [ ] `verification_score.total` equals sum of dimensions
- [ ] `verification_score.passed` is `true`
- [ ] `verification_score.total` ≥ 9 (not ≥7)
- [ ] No dimension in `verification_score` has 0
- [ ] `pubmed_test.conclusion` contains "PASS"
- [ ] At least 1 SPARQL query present
- [ ] `exact_answer` format matches `type`
- [ ] For `type: choice`: All items in `exact_answer` exist in `choices`
- [ ] For `type: choice`: `exact_answer` is an array (even for single answer)
- [ ] All databases in `togomcp_databases_used` appear in `sparql_queries`

### SPARQL Validation
- [ ] All queries are executable
- [ ] Proper PREFIX declarations
- [ ] Query syntax is valid

### RDF Validation
- [ ] Valid Turtle syntax
- [ ] All triples have comments
- [ ] Comments follow format: `# Database: X | Query: N | Comment: ...`

### Quality Checks
- [ ] Question body is stand-alone
- [ ] No database names in question body
- [ ] `ideal_answer` is one paragraph
- [ ] For `type: choice`: `ideal_answer` explains why correct answer is correct and why others are wrong
- [ ] No meta-references in `ideal_answer`
- [ ] Time spent totals to reasonable range (2-6 hours)

---

## Version History

- **v1.0** (2025-02-05): Initial specification
- **v1.1** (2025-02-11): Added dataset composition target (60-80% multi-database)
- **v1.2** (2025-02-14): Added `choice` question type
- **v1.3** (2025-02-15): **CRITICAL FIXES** aligned with QA_CREATION_GUIDE v5.0:
  - Fixed scoring threshold: ≥9 (was inconsistent ≥7/≥9)
  - Added yes/no comprehensive SPARQL requirement (bif:contains, no VALUES from search)
  - Added 3+ database target: ≥20% (minimum 10 questions)
  - Added UniProt cap: ≤70% (maximum 35 questions)
  - Enhanced scoring rubric with specific criteria
  - Added circular reasoning warnings
  - Added summary single-paragraph requirement
