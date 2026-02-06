# TogoMCP Usage Guide

A comprehensive, step-by-step workflow for answering user questions using TogoMCP tools. **Follow each step carefully—do not skip any step.**

---

## Table of Contents

1. [Quick Reference: Tool Categories](#quick-reference-tool-categories)
2. [⚠️ CRITICAL: Search vs. Comprehensive Queries](#critical-search-vs-comprehensive-queries)
3. [Complete Workflow](#complete-workflow)
4. [Step 1: Analyze the Query](#step-1-analyze-the-query)
5. [Step 2: Select the Right Database(s)](#step-2-select-the-right-databases)
6. [Step 3: Execute Search Tools](#step-3-execute-search-tools)
7. [Step 4: Use SPARQL for Advanced Queries](#step-4-use-sparql-for-advanced-queries)
8. [Step 5: Convert and Link IDs](#step-5-convert-and-link-ids)
9. [Step 6: Retrieve Additional Information](#step-6-retrieve-additional-information)
10. [Step 7: Synthesize and Present Results](#step-7-synthesize-and-present-results)
11. [Common Query Patterns](#common-query-patterns)
12. [Critical Rules and Best Practices](#critical-rules-and-best-practices)
13. [Troubleshooting](#troubleshooting)

---

## Quick Reference: Tool Categories

### 📋 Discovery Tools
| Tool | Purpose |
|------|---------|
| `list_databases()` | List all 22 available RDF databases with descriptions |
| `get_sparql_endpoints()` | Get SPARQL endpoint URLs and recommended search tools |
| `togoid_getAllDataset()` | List all datasets available for ID conversion |
| `togoid_getDescription()` | Get detailed descriptions of all databases |
| `ncbi_list_databases()` | List NCBI databases (Gene, Taxonomy, ClinVar, etc.) |

### 🔍 Search Tools (by Domain)

| Domain | Tool | Usage |
|--------|------|-------|
| **Proteins** | `search_uniprot_entity(query, limit)` | Search proteins, functions, diseases |
| **Chemicals/Drugs** | `search_chembl_molecule(query, limit)` | Search drug-like molecules |
| | `search_chembl_target(query, limit)` | Search drug targets |
| | `get_pubchem_compound_id(compound_name)` | Get PubChem Compound ID |
| | `get_compound_attributes_from_pubchem(id)` | Get compound properties |
| **Structures** | `search_pdb_entity(db, query, limit)` | Search PDB (db: "pdb", "cc", "prd") |
| **Pathways** | `search_reactome_entity(query, rows)` | Search pathways and reactions |
| **Reactions** | `search_rhea_entity(query, limit)` | Search biochemical reactions |
| **Medical Terms** | `search_mesh_entity(query, limit)` | Search MeSH vocabulary |
| **Ontologies** | `OLS4:search(query)` | Search all ontologies (GO, MONDO, etc.) |
| | `OLS4:searchClasses(query, ontologyId)` | Search specific ontology |
| **NCBI** | `ncbi_esearch(database, query)` | Search Gene, Taxonomy, ClinVar, MedGen, PubMed, PubChem |
| | `ncbi_esummary(database, ids)` | Get summaries for IDs |
| | `ncbi_efetch(database, ids, rettype)` | Fetch full records |

### 🔗 ID Conversion Tools (TogoID)
| Tool | Purpose |
|------|---------|
| `togoid_convertId(ids, route)` | Convert IDs between databases (e.g., "uniprot,pdb") |
| `togoid_countId(ids, source, target)` | Count convertible IDs |
| `togoid_getDataset(dataset)` | Get dataset configuration (regex, examples) |
| `togoid_getRelation(source, target)` | Get relationship between databases |
| `togoid_getAllRelation()` | Get all possible conversion routes |

### 🗄️ SPARQL Tools
| Tool | Purpose |
|------|---------|
| `get_MIE_file(dbname)` | **MANDATORY before SPARQL** - Get schema, examples |
| `get_sparql_example(dbname)` | Get example SPARQL queries |
| `get_graph_list(dbname)` | List named graphs in database |
| `run_sparql(dbname, sparql_query)` | Execute SPARQL query |

### 📚 Ontology Tools (OLS4)
| Tool | Purpose |
|------|---------|
| `OLS4:search(query)` | General ontology search |
| `OLS4:searchClasses(query, ontologyId)` | Search within specific ontology |
| `OLS4:fetch(id)` | Get entity details |
| `OLS4:getAncestors(classIri, ontologyId)` | Get parent terms |
| `OLS4:getDescendants(classIri, ontologyId)` | Get child terms |
| `OLS4:listOntologies()` | List all available ontologies |

### 📖 Dictionary Tools (PubDictionaries)
| Tool | Purpose |
|------|---------|
| `PubDictionaries:list_dictionaries()` | List available dictionaries |
| `PubDictionaries:get_dictionary_description(name)` | Get dictionary info |
| `PubDictionaries:find_ids(dictionary, labels)` | Find IDs for terms |
| `PubDictionaries:find_terms(dictionary, ids)` | Find terms for IDs |
| `PubDictionaries:search(dictionary, labels)` | Search dictionary |

---

## ⚠️ CRITICAL: Search vs. Comprehensive Queries

### Understanding the Difference

**Search APIs (Step 3)**: 
- **Purpose**: Exploratory discovery, finding patterns and examples
- **Returns**: 10-20 results typically
- **Use for**: Understanding data, identifying entities, mapping cross-references
- **NOT for**: Definitive answers to comprehensive questions

**SPARQL Queries (Step 4)**:
- **Purpose**: Validation, comprehensive analysis, definitive answers
- **Returns**: Complete dataset matching criteria
- **Use for**: Aggregations, existence claims, distribution patterns
- **Required for**: Yes/no questions, phylogenetic distribution, negative claims

### The Circular Reasoning Trap ⚠️

**WRONG Approach** (Common Error):
```
1. Search API finds 8 example proteins
2. Hardcode those 8 IDs into SPARQL VALUES clause
3. Query properties of those 8 proteins
4. Conclude based on incomplete data
→ CIRCULAR REASONING - You only checked what you already found!
```

**CORRECT Approach**:
```
1. Search API finds examples (understand the pattern)
2. SPARQL searches ALL entities using bif:contains with multiple search terms
3. Aggregate/classify comprehensive results
4. Conclude based on complete dataset
→ COMPREHENSIVE ANALYSIS - You checked everything matching criteria
```

### When Each Approach Applies

**Example-Based Queries (Can Use Search Results):**
- ✅ Top-N rankings: "Which 5 kinases have most inhibitors?"
- ✅ Specific lookups: "What PDB structures exist for protein P04637?"
- ✅ Bounded verification: "Do these 3 specific proteins bind ATP?"

**Comprehensive Queries (MUST Use Full SPARQL):**
- ✅ Yes/No questions: "Do ANY proteins in category X have property Y?"
- ✅ Existence claims: "Are there compounds with property Z?"
- ✅ Phylogenetic distribution: "Are enzymes found in phyla beyond A and B?"
- ✅ Negative claims: "No proteins of type Y have annotation Z"

### How to Write Comprehensive SPARQL

**WRONG - Using Hardcoded VALUES:**
```sparql
# DON'T DO THIS for comprehensive questions!
VALUES ?protein { 
  uniprot:P12345 uniprot:P67890 uniprot:P11111 
}
?protein up:organism ?organism .
```

**CORRECT - Using bif:contains with Multiple Search Terms:**
```sparql
# DO THIS for comprehensive questions!
?protein up:recommendedName ?name .
?name up:fullName ?fullName .
?fullName bif:contains "'rhamnosyltransferase' OR 'protein-arginine rhamnosyl' OR 'WbbL' OR 'EF-P rhamnosyl'"
?protein up:organism ?organism .
```

**Key Principles:**
1. Use ALL known synonyms and variations in bif:contains
2. Search comprehensively, don't limit to search API results
3. Aggregate by classification when needed (GROUP BY)
4. For phylogenetic questions: query all organisms, then classify by phylum

---

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│  START: User Query                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: Analyze the Query                                         │
│  • Extract keywords, IDs, entities                                  │
│  • Identify domain (proteins, chemicals, diseases, etc.)           │
│  • Determine query type (search, convert, annotate)                │
│  • Is this comprehensive or example-based?                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Select Database(s)                                        │
│  • Run list_databases() if unsure                                  │
│  • Check get_sparql_endpoints() for search tools                   │
│  • Match domain to database(s)                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Execute Search Tools (EXPLORATORY PHASE)                  │
│  ⚠️  ALWAYS TRY SEARCH TOOLS FIRST                                 │
│  • Use domain-specific search (see table above)                    │
│  • Find patterns, examples, cross-references                       │
│  • Document search terms for comprehensive SPARQL                  │
│  • Try multiple keywords/synonyms                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
         ┌──────────────────┐            ┌──────────────────┐
         │ Need Comprehensive│───YES─────│  STEP 4: SPARQL  │
         │ Analysis?         │            │  (bif:contains)  │
         │ (yes/no, exists)  │            └──────────────────┘
         └──────────────────┘                     │
                    │                              │
                   NO                              │
                    │                              │
                    ▼                              │
         ┌──────────────────┐                     │
         │ Got Specific IDs?│───── YES ───────────┤
         └──────────────────┘                     │
                    │                              │
                   NO                              │
                    │                              │
                    ▼                              │
         ┌──────────────────┐                     │
         │  STEP 4: SPARQL  │                     │
         │  (Advanced Query)│                     │
         └──────────────────┘                     │
                    │                              │
                    └──────────────┬───────────────┘
                                   ▼
                         ┌──────────────────┐
                         │  STEP 5: ID      │
                         │  Conversion      │
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  STEP 6: Retrieve│
                         │  Additional Info │
                         └──────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │  STEP 7: Present │
                         │  Results         │
                         └──────────────────┘
```

---

## Step 1: Analyze the Query

### ✅ CHECKLIST - Do Not Skip

- [ ] **Extract keywords**: Identify proteins, genes, diseases, chemicals, species
- [ ] **Identify IDs**: Look for existing IDs (UniProt: P12345, PDB: 1ABC, etc.)
- [ ] **Determine domain**: Which biological area? (See table below)
- [ ] **Clarify intent**: What does the user want to know?
- [ ] **Classify query type**: Comprehensive (yes/no, exists) or Example-based (specific lookup, top-N)?

### Domain Classification

| Domain | Keywords to Look For | Primary Databases |
|--------|---------------------|-------------------|
| **Proteins** | protein, enzyme, receptor, kinase, sequence | UniProt, PDB, Ensembl |
| **Genes** | gene, transcript, expression, chromosome | NCBI Gene, Ensembl, GO |
| **Chemicals/Drugs** | drug, compound, molecule, inhibitor, SMILES | ChEMBL, PubChem, ChEBI |
| **Diseases** | disease, disorder, syndrome, cancer, condition | MONDO, MeSH, MedGen, ClinVar |
| **Pathways** | pathway, signaling, metabolism, process | Reactome, GO, KEGG |
| **Reactions** | reaction, catalysis, enzyme activity | Rhea, Reactome |
| **Taxonomy** | species, organism, bacteria, human, mouse | NCBI Taxonomy, BacDive |
| **Structures** | structure, 3D, crystal, cryo-EM, NMR | PDB |
| **Variants** | mutation, variant, SNP, polymorphism | ClinVar, dbSNP |
| **Glycans** | glycan, sugar, carbohydrate, glycoprotein | GlyCosmos, GlyTouCan |
| **Literature** | paper, publication, abstract, citation | PubMed, PubTator |

### Query Type Classification

**Comprehensive Questions** (Require full SPARQL with bif:contains):
- "Do ANY..."
- "Are there..."
- "Is X found in phyla other than..."
- "Which organisms have..."
- "Are ALL..."

**Example-Based Questions** (Can use search API results):
- "Which 5..."
- "What is the top..."
- "List the structures for protein X..."
- "Show me examples of..."

---

## Step 2: Select the Right Database(s)

### ✅ CHECKLIST - Do Not Skip

- [ ] **If unsure**: Run `list_databases()` to see all 22 databases
- [ ] **Check recommended search tools**: Run `get_sparql_endpoints()` 
- [ ] **For ID conversion**: Run `togoid_getAllDataset()` to see available routes

### Database Quick Reference

| Category | Database | Description | Search Tool |
|----------|----------|-------------|-------------|
| **Proteins** | `uniprot` | 444M proteins, functions, diseases | `search_uniprot_entity` |
| | `pdb` | 204K+ 3D structures | `search_pdb_entity` |
| | `ensembl` | Genome annotations, 100+ species | SPARQL only |
| **Chemicals** | `pubchem` | 119M compounds, 1.7M bioassays | `ncbi_esearch` |
| | `chembl` | 2.4M+ bioactive molecules | `search_chembl_molecule/target` |
| | `chebi` | 217K+ chemical entities | `OLS4:searchClasses` |
| **Diseases** | `mondo` | 30K+ disease classes | `OLS4:searchClasses` |
| | `mesh` | 30K descriptors, 250K chemicals | `search_mesh_entity` |
| | `medgen` | 233K+ clinical concepts | `ncbi_esearch` |
| | `clinvar` | 3.5M+ variant records | `ncbi_esearch` |
| | `nando` | Japanese intractable diseases | `OLS4:searchClasses` |
| **Pathways** | `reactome` | 22K+ pathways, 30+ species | `search_reactome_entity` |
| | `go` | 48K+ GO terms | `OLS4:searchClasses` |
| **Reactions** | `rhea` | 17K+ biochemical reactions | `search_rhea_entity` |
| **Genes** | `ncbigene` | 57M+ gene entries | `ncbi_esearch` |
| **Taxonomy** | `taxonomy` | 3M+ organisms | `ncbi_esearch` |
| **Literature** | `pubmed` | Biomedical literature | `ncbi_esearch` |
| | `pubtator` | Entity annotations from PubMed | SPARQL only |
| **Microbiology** | `bacdive` | 97K+ bacterial strains | SPARQL only |
| | `mediadive` | 3.3K culture media recipes | SPARQL only |
| | `amrportal` | AMR surveillance data | SPARQL only |
| **Sequences** | `ddbj` | Nucleotide sequences | SPARQL only |
| **Glycans** | `glycosmos` | Glycan structures | SPARQL only |

---

## Step 3: Execute Search Tools

### ✅ CHECKLIST - Do Not Skip

- [ ] **ALWAYS try search tools FIRST** - They are often more capable than expected
- [ ] **Remember: This is EXPLORATORY** - Finding patterns, not definitive answers
- [ ] **Use the correct tool** for your domain (see table below)
- [ ] **Try multiple keywords/synonyms** if initial search returns insufficient results
- [ ] **Document search terms** for use in comprehensive SPARQL queries
- [ ] **Adjust limit parameter** (default usually 20, increase if needed)
- [ ] **For comprehensive questions**: Note ALL variations and synonyms found

### Search Tool Decision Matrix

```
What are you searching for?
│
├─► Proteins/Enzymes ──────────► search_uniprot_entity(query, limit=20)
│   (includes disease associations!)
│
├─► Drugs/Compounds ───────────► search_chembl_molecule(query, limit=20)
│
├─► Drug Targets ──────────────► search_chembl_target(query, limit=20)
│
├─► 3D Structures ─────────────► search_pdb_entity(db="pdb", query, limit=20)
│   Small molecules in PDB ────► search_pdb_entity(db="cc", query, limit=20)
│   Peptides in PDB ───────────► search_pdb_entity(db="prd", query, limit=20)
│
├─► Pathways/Processes ────────► search_reactome_entity(query, rows=30)
│
├─► Biochemical Reactions ─────► search_rhea_entity(query, limit=100)
│
├─► Medical Terms/MeSH ────────► search_mesh_entity(query, limit=10)
│
├─► Ontology Terms ────────────► OLS4:search(query)
│   (GO, MONDO, ChEBI, etc.)    or OLS4:searchClasses(query, ontologyId)
│
├─► NCBI Data ─────────────────► ncbi_esearch(database, query)
│   Genes ─────────────────────► ncbi_esearch("gene", query)
│   Taxonomy ──────────────────► ncbi_esearch("taxonomy", query)
│   ClinVar ───────────────────► ncbi_esearch("clinvar", query)
│   MedGen ────────────────────► ncbi_esearch("medgen", query)
│   PubMed ────────────────────► ncbi_esearch("pubmed", query)
│   PubChem Compound ──────────► ncbi_esearch("pccompound", query)
│
└─► Chemical by Name ──────────► get_pubchem_compound_id(compound_name)
                                 → get_compound_attributes_from_pubchem(id)
```

### Search Tips

1. **Start broad, then narrow**: Begin with simple terms, add specificity if needed
2. **Use synonyms**: If "hypertension" doesn't work, try "high blood pressure"
3. **Include species**: Add "human" or organism name for more relevant results
4. **Check multiple databases**: Cross-reference results for completeness
5. **Document variations**: Note all alternative names/spellings for comprehensive SPARQL

### Example: Exploratory Search for Comprehensive Query

```python
# User asks: "Are bacterial rhamnosyltransferases found in phyla beyond Pseudomonadota?"
# This is a COMPREHENSIVE question - needs full SPARQL, not just search results

# Step 3: Exploratory search (finding patterns)
results = search_uniprot_entity("rhamnosyltransferase", limit=20)
# Found examples in: Mycobacterium, E. coli, Pseudomonas, Treponema
# Also found variations: "protein-arginine rhamnosyltransferase", "WbbL"

# Document search terms for Step 4:
# - "rhamnosyltransferase"
# - "protein-arginine rhamnosyltransferase"
# - "WbbL"
# - "EF-P rhamnosyl"

# DO NOT conclude yet - these are just examples!
# Proceed to Step 4 for comprehensive SPARQL query
```

---

## Step 4: Use SPARQL for Advanced Queries

### ⚠️ MANDATORY PREREQUISITE

**BEFORE writing ANY SPARQL query, you MUST:**

```python
# Step 4.1: ALWAYS run this first
get_MIE_file(dbname)  # Returns schema, RDF patterns, and examples
```

### ✅ CHECKLIST - Do Not Skip

- [ ] **Run `get_MIE_file(dbname)`** - Contains ShEx schema, RDF examples, SPARQL examples
- [ ] **Optionally run `get_sparql_example(dbname)`** - Get additional examples
- [ ] **Check `get_graph_list(dbname)`** if you need specific named graphs
- [ ] **Include LIMIT clause** - Always limit results (20-100)
- [ ] **Apply database-specific rules** (see below)
- [ ] **For comprehensive questions**: Use bif:contains with ALL search terms from Step 3
- [ ] **For example-based questions**: Can use VALUES with specific IDs from Step 3

### When to Use SPARQL

| Use Search Tools When... | Use SPARQL When... |
|--------------------------|-------------------|
| Looking for entities by name | Need specific annotation types |
| Simple keyword search | Complex boolean logic (AND, NOT) |
| Broad exploration | Precise field targeting |
| Quick results needed | Aggregations (COUNT, GROUP BY) |
| Finding examples (10-20 results) | Comprehensive analysis (ALL matching entities) |
| | Cross-linking within database |

### Critical Database-Specific Rules

| Database | Critical Rule |
|----------|--------------|
| **UniProt** | ALWAYS filter `?protein up:reviewed 1` for Swiss-Prot quality |
| **ChEMBL** | Use `FROM <http://rdf.ebi.ac.uk/dataset/chembl>` |
| **Full-text search** | Split property paths when using `bif:contains` |
| **All databases** | ALWAYS use `LIMIT` (start with 20-100) |
| **Comprehensive queries** | Use bif:contains with multiple search terms, NOT VALUES |

### SPARQL Workflow: Comprehensive vs. Example-Based

#### Example-Based Workflow (Specific Lookups, Top-N)

```python
# 1. Get the schema and examples (MANDATORY)
mie_info = get_MIE_file("uniprot")

# 2. Can use specific IDs from search results
query = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT ?protein ?name ?structure_count
WHERE {
  VALUES ?protein { uniprot:P04637 uniprot:P38398 uniprot:P00533 }
  ?protein up:reviewed 1 ;
           up:recommendedName/up:fullName ?name ;
           rdfs:seeAlso ?pdb .
  FILTER(CONTAINS(STR(?pdb), "rdf.wwpdb.org"))
}
GROUP BY ?protein ?name
ORDER BY DESC(COUNT(?pdb))
LIMIT 5
"""

results = run_sparql("uniprot", query)
```

#### Comprehensive Workflow (Yes/No, Existence, Distribution)

```python
# 1. Get the schema and examples (MANDATORY)
mie_info = get_MIE_file("uniprot")

# 2. MUST use bif:contains with ALL search terms (NO VALUES!)
query = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema/>

SELECT DISTINCT ?protein ?organism ?phylum
WHERE {
  # Comprehensive search with ALL variations
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:recommendedName ?name ;
           up:organism ?organism .
  ?name up:fullName ?fullName .
  
  # CRITICAL: Use bif:contains with ALL synonyms found in Step 3
  ?fullName bif:contains "'rhamnosyltransferase' OR 'protein-arginine rhamnosyl' OR 'WbbL' OR 'EF-P rhamnosyl'"
  
  # Get phylum classification
  ?organism rdfs:subClassOf+ ?phylumNode .
  ?phylumNode up:rank "phylum" ;
              up:scientificName ?phylum .
}
LIMIT 1000
"""

results = run_sparql("uniprot", query)

# 3. Aggregate by phylum for comprehensive answer
phyla = {}
for result in results:
    phylum = result['phylum']
    phyla[phylum] = phyla.get(phylum, 0) + 1

# Now you have a COMPLETE picture across all phyla
```

### Common SPARQL Patterns

**Pattern 1: Comprehensive Existence Check**
```sparql
# Question: "Do ANY glycolysis enzymes localize to mitochondria?"
# WRONG: VALUES ?protein { <pre-selected IDs> }
# CORRECT: Use bif:contains to find ALL glycolysis enzymes

PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?protein ?location
WHERE {
  ?protein up:reviewed 1 ;
           up:annotation ?annot ;
           up:classifiedWith ?go .
  
  # Find ALL glycolysis enzymes
  ?go rdfs:label ?goLabel .
  FILTER(CONTAINS(LCASE(?goLabel), "glycolysis") || CONTAINS(LCASE(?goLabel), "glycolytic"))
  
  # Check subcellular location
  ?annot a up:Subcellular_Location_Annotation ;
         rdfs:comment ?location .
  FILTER(CONTAINS(LCASE(?location), "mitochondrion"))
}
LIMIT 100
```

**Pattern 2: Phylogenetic Distribution**
```sparql
# Question: "In which phyla are enzyme X found?"
# WRONG: VALUES with pre-selected organisms
# CORRECT: Search ALL organisms, aggregate by phylum

PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?phylum (COUNT(DISTINCT ?protein) as ?count)
WHERE {
  ?protein up:reviewed 1 ;
           up:recommendedName ?name ;
           up:organism ?organism .
  ?name up:fullName ?fullName .
  
  # Search ALL matching proteins
  ?fullName bif:contains "'enzyme name' OR 'alternative name'"
  
  # Get phylum
  ?organism rdfs:subClassOf+ ?phylumNode .
  ?phylumNode up:rank "phylum" ;
              up:scientificName ?phylum .
}
GROUP BY ?phylum
ORDER BY DESC(?count)
```

---

## Step 5: Convert and Link IDs

### ✅ CHECKLIST - Do Not Skip

- [ ] **Check if conversion route exists**: Use `togoid_getRelation(source, target)`
- [ ] **Use correct database keys**: e.g., "uniprot", "pdb", "ncbigene"
- [ ] **Handle missing conversions**: Not all IDs have mappings

### ID Conversion Workflow

```python
# 1. Check available datasets
all_datasets = togoid_getAllDataset()

# 2. Check if route exists between two databases
relation = togoid_getRelation("uniprot", "pdb")

# 3. Convert IDs
result = togoid_convertId(
    ids="P04637,P17612",           # Comma-separated IDs
    route="uniprot,pdb"            # Source,target
)

# 4. For multi-hop conversions
result = togoid_convertId(
    ids="P04637",
    route="uniprot,ncbigene,ensembl_gene"  # Chain of databases
)
```

### Common Conversion Routes

| From | To | Route |
|------|-----|-------|
| UniProt → PDB | `togoid_convertId(ids, "uniprot,pdb")` |
| UniProt → NCBI Gene | `togoid_convertId(ids, "uniprot,ncbigene")` |
| UniProt → ChEMBL Target | `togoid_convertId(ids, "uniprot,chembl_target")` |
| NCBI Gene → Ensembl | `togoid_convertId(ids, "ncbigene,ensembl_gene")` |
| PDB → UniProt | `togoid_convertId(ids, "pdb,uniprot")` |
| ChEBI → PubChem | `togoid_convertId(ids, "chebi,pubchem_compound")` |

---

## Step 6: Retrieve Additional Information

### ✅ CHECKLIST - Do Not Skip

- [ ] **After getting IDs**: Fetch detailed information
- [ ] **Use appropriate fetch tool** for the data type
- [ ] **Handle missing data gracefully**

### Retrieval Tools

| Data Type | Tool | Usage |
|-----------|------|-------|
| **NCBI Records** | `ncbi_esummary(database, ids)` | Get summaries for gene, pubmed, etc. |
| | `ncbi_efetch(database, ids, rettype)` | Get full records (fasta, gb, xml) |
| **Ontology Terms** | `OLS4:fetch(id)` | Get term details |
| | `OLS4:getAncestors(classIri, ontologyId)` | Get parent terms |
| | `OLS4:getDescendants(classIri, ontologyId)` | Get child terms |
| **PubChem** | `get_compound_attributes_from_pubchem(id)` | Get compound properties |
| **Dictionaries** | `PubDictionaries:find_terms(dict, ids)` | Get labels for IDs |

### Example: Complete Information Retrieval

```python
# 1. Search for a protein
results = search_uniprot_entity("BRCA1 human", limit=5)
# → Get UniProt ID: P38398

# 2. Convert to other databases
pdb_ids = togoid_convertId("P38398", "uniprot,pdb")
gene_ids = togoid_convertId("P38398", "uniprot,ncbigene")

# 3. Get detailed gene information
gene_summary = ncbi_esummary("gene", gene_ids)

# 4. Get ontology annotations
go_terms = OLS4:search("BRCA1")
```

---

## Step 7: Synthesize and Present Results

### ✅ CHECKLIST - Do Not Skip

- [ ] **Combine information** from all sources queried
- [ ] **Cite databases used** (UniProt, PDB, ChEMBL, etc.)
- [ ] **Note limitations**: Missing data, incomplete conversions
- [ ] **Provide IDs and links** for user follow-up
- [ ] **For comprehensive questions**: State confidence in completeness

### Response Template

```markdown
## Summary
[Brief answer to the user's question]
[For comprehensive questions: "Based on comprehensive SPARQL query of all matching entities..."]

## Details
[Organized findings from databases]

## Data Sources
- UniProt: [IDs used, query type]
- PDB: [IDs used]
- [Other databases]

## Methodology
[For comprehensive questions: Explain search terms used and validation approach]

## Notes
- [Any limitations or caveats]
- [Suggestions for further exploration]
```

---

## Common Query Patterns

### Pattern 1: Find Proteins Associated with a Disease

```python
# Step 1: Search UniProt (includes disease associations!)
proteins = search_uniprot_entity("Alzheimer disease", limit=50)

# Step 2: If more precision needed, use SPARQL
get_MIE_file("uniprot")  # MANDATORY
query = """
PREFIX up: <http://purl.uniprot.org/core/>
SELECT ?protein ?name ?disease
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:recommendedName/up:fullName ?name ;
           up:annotation ?annot .
  ?annot a up:Disease_Annotation ;
         rdfs:comment ?disease .
  FILTER(CONTAINS(LCASE(?disease), "alzheimer"))
}
LIMIT 50
"""
results = run_sparql("uniprot", query)
```

### Pattern 2: Find Drug Targets and Inhibitors

```python
# Step 1: Search for the protein target
protein = search_uniprot_entity("angiotensin converting enzyme human", limit=5)
# → UniProt ID: P12821

# Step 2: Convert to ChEMBL target
chembl_target = togoid_convertId("P12821", "uniprot,chembl_target")

# Step 3: Search for inhibitors in ChEMBL
inhibitors = search_chembl_molecule("ACE inhibitor", limit=20)

# Step 4: Get compound details from PubChem
compound_id = get_pubchem_compound_id("lisinopril")
properties = get_compound_attributes_from_pubchem(compound_id)
```

### Pattern 3: Find Protein Structure

```python
# Step 1: Search for protein
protein = search_uniprot_entity("p53 human", limit=5)
# → UniProt ID: P04637

# Step 2: Convert to PDB
pdb_ids = togoid_convertId("P04637", "uniprot,pdb")

# Step 3: Or search PDB directly
structures = search_pdb_entity(db="pdb", query="p53 tumor suppressor", limit=20)
```

### Pattern 4: Explore Pathways

```python
# Step 1: Search Reactome
pathways = search_reactome_entity("apoptosis", rows=30)

# Step 2: For related reactions
reactions = search_rhea_entity("caspase", limit=50)

# Step 3: Get GO terms for biological process
go_terms = OLS4:searchClasses("programmed cell death", ontologyId="go")
```

### Pattern 5: Cross-Database Integration

```python
# Goal: From gene name to structures, drugs, and pathways

# 1. Find gene
gene = ncbi_esearch("gene", "EGFR human")
# → Gene ID: 1956

# 2. Get UniProt ID
uniprot_ids = togoid_convertId("1956", "ncbigene,uniprot")
# → P00533

# 3. Get structures
pdb_ids = togoid_convertId("P00533", "uniprot,pdb")

# 4. Get drug targets
chembl_targets = togoid_convertId("P00533", "uniprot,chembl_target")

# 5. Search pathways
pathways = search_reactome_entity("EGFR signaling", rows=20)
```

### Pattern 6: Comprehensive Phylogenetic Distribution (NEW)

```python
# Question: "Are bacterial rhamnosyltransferases found in phyla beyond X and Y?"

# Step 1: Exploratory search (understanding patterns)
search_results = search_uniprot_entity("rhamnosyltransferase", limit=20)
# Found: Mycobacterium, E. coli, Pseudomonas, also "protein-arginine rhamnosyltransferase", "WbbL"

# Step 2: Get MIE file
get_MIE_file("uniprot")

# Step 3: Comprehensive SPARQL query (NOT using VALUES!)
query = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema/>

SELECT DISTINCT ?protein ?organism ?phylum
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:recommendedName ?name ;
           up:organism ?organism .
  ?name up:fullName ?fullName .
  
  # COMPREHENSIVE: Use ALL search terms found
  ?fullName bif:contains "'rhamnosyltransferase' OR 'protein-arginine rhamnosyl' OR 'WbbL' OR 'EF-P rhamnosyl'"
  
  # Get phylum classification
  ?organism rdfs:subClassOf+ ?phylumNode .
  ?phylumNode up:rank "phylum" ;
              up:scientificName ?phylum .
}
LIMIT 1000
"""

results = run_sparql("uniprot", query)

# Step 4: Aggregate by phylum
phyla = {}
for result in results:
    phylum = result['phylum']
    protein_count = phyla.get(phylum, 0) + 1
    phyla[phylum] = protein_count

# Step 5: Answer definitively based on COMPLETE data
print(f"Found rhamnosyltransferases in {len(phyla)} bacterial phyla:")
for phylum, count in sorted(phyla.items(), key=lambda x: x[1], reverse=True):
    print(f"  {phylum}: {count} proteins")
```

---

## Critical Rules and Best Practices

### ✅ ALWAYS DO

1. **Try search tools first** - They're more capable than you might think (exploratory phase)
2. **Run `get_MIE_file()` before SPARQL** - This is mandatory, not optional
3. **Use `LIMIT` in all SPARQL queries** - Start with 20-100
4. **Filter UniProt by `up:reviewed 1`** - For Swiss-Prot quality data
5. **Check conversion routes exist** before calling `togoid_convertId()`
6. **Cite your data sources** in the final response
7. **Handle empty results gracefully** - Try alternative keywords
8. **For comprehensive questions**: Use bif:contains with ALL synonyms, not VALUES
9. **Document methodology**: State whether query is comprehensive or example-based

### ❌ NEVER DO

1. **Don't skip to SPARQL** without trying search tools first
2. **Don't write SPARQL** without reading MIE file first
3. **Don't assume search tools are limited** - Test them first
4. **Don't forget `up:reviewed 1`** in UniProt queries (gets TrEMBL noise)
5. **Don't omit LIMIT** - Can cause timeouts with large datasets
6. **Don't use `bif:contains` with property paths** - Split them
7. **Don't assume all IDs convert** - Check conversion availability
8. **Don't use VALUES with search results for comprehensive questions** - This is circular reasoning!
9. **Don't conclude from examples alone** - Comprehensive questions need comprehensive queries

### 🔴 Critical Rule: Avoiding Circular Reasoning

**NEVER do this for comprehensive questions:**
```python
# WRONG: Circular reasoning trap
search_results = search_uniprot_entity("enzyme", limit=20)
ids = extract_ids(search_results)  # Get 20 IDs

query = f"""
VALUES ?protein {{ {' '.join(ids)} }}  # ← Only checking the 20 found!
?protein up:organism ?org .
"""
```

**ALWAYS do this for comprehensive questions:**
```python
# CORRECT: Comprehensive analysis
search_results = search_uniprot_entity("enzyme", limit=20)
# Used to identify search terms and patterns

query = """
?protein up:recommendedName ?name .
?name up:fullName ?fullName .
?fullName bif:contains "'enzyme' OR 'variant1' OR 'variant2'"  # ← ALL matching entities
?protein up:organism ?org .
"""
```

---

## Troubleshooting

### Problem: Search Returns No Results

```
✓ Check spelling and try synonyms
✓ Try broader terms
✓ Remove species filter temporarily
✓ Try a different database
✓ Use SPARQL with get_MIE_file() for complex queries
```

### Problem: SPARQL Query Fails

```
✓ Did you run get_MIE_file() first? (MANDATORY)
✓ Check prefix declarations
✓ Add LIMIT clause
✓ For UniProt: add up:reviewed 1
✓ For ChEMBL: add FROM <http://rdf.ebi.ac.uk/dataset/chembl>
✓ Check property paths - split if using bif:contains
```

### Problem: ID Conversion Returns Empty

```
✓ Check if route exists: togoid_getRelation(source, target)
✓ Verify ID format matches expected pattern
✓ Try alternative routes (multi-hop conversion)
✓ Not all IDs have mappings - this is expected
```

### Problem: Timeout or Slow Query

```
✓ Reduce LIMIT
✓ Add more specific filters
✓ For UniProt: MUST use up:reviewed 1
✓ Consider using search tools instead
```

### Problem: Incomplete Results for Comprehensive Question

```
✓ Did you use bif:contains with ALL search terms?
✓ Check if you accidentally used VALUES with limited IDs
✓ Try adding more synonyms and variations to bif:contains
✓ Verify you're not limiting to examples from search API
✓ Consider if database has incomplete coverage
```

---

## Appendix: All Available Databases

Run `list_databases()` to see the complete list of 22 databases:

| Database | Domain | Description |
|----------|--------|-------------|
| amrportal | Microbiology | Antimicrobial resistance data |
| bacdive | Microbiology | Bacterial strain information |
| chebi | Chemistry | Chemical entities of biological interest |
| chembl | Chemistry/Drugs | Bioactive molecules, drug data |
| clinvar | Genetics | Genomic variation and health |
| ddbj | Sequences | Nucleotide sequence data |
| ensembl | Genomics | Genome annotations |
| glycosmos | Glycobiology | Glycan structures |
| go | Ontology | Gene Ontology terms |
| medgen | Medicine | Medical genetics concepts |
| mediadive | Microbiology | Culture media recipes |
| mesh | Medicine | Medical subject headings |
| mondo | Diseases | Disease ontology |
| nando | Diseases | Japanese intractable diseases |
| ncbigene | Genes | NCBI Gene database |
| pdb | Structures | Protein 3D structures |
| pubchem | Chemistry | Chemical compounds |
| pubmed | Literature | Biomedical publications |
| pubtator | Literature | Entity annotations from PubMed |
| reactome | Pathways | Biological pathways |
| rhea | Reactions | Biochemical reactions |
| taxonomy | Taxonomy | Organism classification |
| uniprot | Proteins | Protein sequences and functions |

---

**Remember: Search APIs are for EXPLORATION (finding patterns, examples). SPARQL is for VALIDATION (comprehensive analysis, definitive answers). Know which type of question you're answering, and use the appropriate approach.**
