# TogoMCP Usage Guide

**Step-by-step workflow for answering biological questions using TogoMCP tools.**

---

## ⭐ Complete Workflow (7 Steps)

### 1. Analyze the Question
- Extract keywords, IDs, entities
- Identify domain (proteins, chemicals, diseases, pathways, etc.)
- Classify query type:
  - **Comprehensive**: yes/no, distribution, "Do ANY...", "Are there..."
  - **Example-based**: top-N, specific lookup, "List the...", "Which 5..."

### 2. Identify Relevant Databases

```python
# List all available databases with descriptions
databases = list_databases()
```

**Select database(s) based on domain:**

| Domain | Primary Databases |
|--------|-------------------|
| **Proteins** | uniprot, pdb, ensembl |
| **Genes** | ncbigene, ensembl, go |
| **Chemicals/Drugs** | chembl, pubchem, chebi |
| **Diseases** | mondo, mesh, medgen, clinvar, nando |
| **Pathways** | reactome, go |
| **Reactions** | rhea, reactome |
| **Taxonomy** | taxonomy, bacdive |
| **Structures** | pdb |
| **Variants** | clinvar |
| **Glycans** | glycosmos |
| **Literature** | pubmed, pubtator |

### 3. Load MIE Files

```python
# Load MIE file for each selected database
mie_info = get_MIE_file(dbname="your_database")
```

**MIE file contains:**
- **kw_search_tools**: Which search API to use (ncbi_esearch, search_*_entity, etc.)
- **ShEx schema**: Available structured properties (keywords, GO terms, EC numbers)
- **SPARQL examples**: Query patterns
- **RDF examples**: Data organization

### 4. Discovery Phase (Use kw_search_tools)

**Check MIE file's kw_search_tools field:**
- **ncbi_esearch** → ClinVar, MedGen, PubMed, NCBI_Gene, PubChem
- **search_*_entity** → UniProt, ChEMBL, PDB, Reactome, Rhea, MeSH
- **OLS4:searchClasses** → GO, MONDO, ChEBI, NANDO
- **Empty/SPARQL only** → BacDive, MediaDive, AMRPortal, PubTator, Glycosmos, DDBJ, Ensembl

**Execute search to:**
- Find 5-10 example entities
- **Identify structured properties** (classifications, keywords, ontologies)
- Document variations/synonyms

```python
# Example: UniProt
results = search_uniprot_entity("transferase", limit=20)
# Note: KW-0808 (Transferase keyword), GO:0016740 (Transferase activity)
```

### 5. Validation with SPARQL

**Query Priority (Best to Worst):**
1. **Structured properties** (up:classifiedWith, ontology IDs, cross-references)
2. **bif:contains** (full-text search - LAST RESORT only)

**Best Practice - Use Structured Properties:**
```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX keywords: <http://purl.uniprot.org/keywords/>

SELECT ?protein ?organism
WHERE {
  ?protein up:reviewed 1 ;
           up:classifiedWith keywords:KW-0808 ;  # Transferase (from MIE schema)
           up:organism ?organism .
}
LIMIT 100
```

**Last Resort - Use bif:contains:**
```sparql
# Only when NO structured properties exist
?protein up:recommendedName/up:fullName ?fullName .
?fullName bif:contains "'transferase' OR 'enzyme'"
```

**Database-Specific Rules:**
- **UniProt**: ALWAYS `?protein up:reviewed 1`
- **ChEMBL**: Use `FROM <http://rdf.ebi.ac.uk/dataset/chembl>`
- **All**: ALWAYS use `LIMIT` (20-100)

### 6. Link Across Databases (TogoID)

**Use TogoID when you need data from multiple databases:**

```python
# Check if conversion route exists
relation = togoid_getRelation("uniprot", "pdb")

# Convert IDs from Step 4 or Step 5
pdb_ids = togoid_convertId(ids="P04637,P12821", route="uniprot,pdb")

# Multi-hop conversion
ensembl_ids = togoid_convertId(ids="P04637", route="uniprot,ncbigene,ensembl_gene")
```

**After conversion:**
- If you need to query the new database → Return to Steps 3-5 for that database
- If you just needed the IDs → Proceed to Step 7

**Common conversion routes:**
- UniProt → PDB (structures)
- UniProt → ChEMBL (drug targets)
- NCBI Gene → UniProt → PDB
- UniProt → NCBI Gene → Ensembl

### 7. Present Results

- Synthesize information from all databases
- Cite all databases used (UniProt, PDB, ChEMBL, etc.)
- Provide IDs for user follow-up
- Note limitations (missing data, failed conversions)
- For comprehensive queries: State methodology and confidence

---

## Quick Reference

### 🔍 Search Tools

| Tool | Usage |
|------|-------|
| `search_uniprot_entity(query, limit)` | Proteins, functions, diseases |
| `search_chembl_molecule/target(query, limit)` | Drugs, targets |
| `search_pdb_entity(db, query, limit)` | 3D structures (db: "pdb", "cc", "prd") |
| `search_reactome_entity(query, rows)` | Pathways, reactions |
| `search_rhea_entity(query, limit)` | Biochemical reactions |
| `search_mesh_entity(query, limit)` | Medical vocabulary |
| `OLS4:search(query)` | All ontologies |
| `OLS4:searchClasses(query, ontologyId)` | Specific ontology |
| `ncbi_esearch(database, query)` | Gene, Taxonomy, ClinVar, MedGen, PubMed, PubChem |
| `get_pubchem_compound_id(name)` | PubChem by name |

### 🗄️ SPARQL Tools

| Tool | Purpose |
|------|---------|
| `get_MIE_file(dbname)` | Get schema, examples (do this in step 3) |
| `get_sparql_example(dbname)` | Get additional query examples |
| `run_sparql(dbname, query)` | Execute SPARQL query |

### 🔗 ID Conversion

| Tool | Purpose |
|------|---------|
| `togoid_convertId(ids, route)` | Convert between databases (e.g., "uniprot,pdb") |
| `togoid_getRelation(source, target)` | Check if conversion route exists |

### 📚 Additional Tools

| Tool | Purpose |
|------|---------|
| `ncbi_esummary(database, ids)` | Get summaries |
| `ncbi_efetch(database, ids, rettype)` | Get full records |
| `OLS4:fetch(id)` | Get ontology term details |
| `OLS4:getAncestors/Descendants(classIri, ontologyId)` | Get parent/child terms |

---

## Common Patterns

### Pattern 1: Find Proteins by Disease

```python
# 1. Analyze: Disease question → Use uniprot, mondo, mesh
# 2. Load MIE
mie = get_MIE_file("uniprot")

# 3. Discovery (kw_search_tools: search_uniprot_entity)
results = search_uniprot_entity("Alzheimer disease", limit=50)

# 4. Validation (if more precision needed)
query = """
PREFIX up: <http://purl.uniprot.org/core/>
SELECT ?protein ?name
WHERE {
  ?protein up:reviewed 1 ;
           up:recommendedName/up:fullName ?name ;
           up:annotation ?annot .
  ?annot a up:Disease_Annotation ;
         rdfs:comment ?disease .
  FILTER(CONTAINS(LCASE(?disease), "alzheimer"))
}
LIMIT 50
"""
```

### Pattern 2: Cross-Database Integration (Multi-Database Query)

```python
# 1. Analyze: "Find structures, drugs, and pathways for EGFR gene"
#    Domain: genes, proteins, structures, drugs, pathways

# 2. Identify databases: ncbigene, uniprot, pdb, chembl, reactome

# 3. Load MIE files
mie_gene = get_MIE_file("ncbigene")
mie_uniprot = get_MIE_file("uniprot")
mie_reactome = get_MIE_file("reactome")

# 4. Discovery - Start with gene database
gene_results = ncbi_esearch("gene", "EGFR human")
# → Gene ID: 1956

# 5. (Skip SPARQL for gene - we have the ID)

# 6. TogoID - Convert gene ID to other databases
uniprot_id = togoid_convertId("1956", "ncbigene,uniprot")
# → P00533

pdb_ids = togoid_convertId("P00533", "uniprot,pdb")
# → 1M14, 1M17, ... (50+ structures)

chembl_targets = togoid_convertId("P00533", "uniprot,chembl_target")
# → CHEMBL203

# 6a. Want pathway data? Return to steps 4-5 for reactome
pathways = search_reactome_entity("EGFR signaling", rows=20)
# → R-HSA-177929, ...

# 7. Present: Gene 1956 → Protein P00533 → 50 structures → Drug target CHEMBL203 → 15 pathways
```

### Pattern 3: Comprehensive Phylogenetic Distribution

```python
# 1. Analyze: "Are transferases found in phyla beyond X?" → Comprehensive query
# 2. Select: uniprot, taxonomy
# 3. Load MIE
mie = get_MIE_file("uniprot")

# 4. Discovery - identify structured properties
results = search_uniprot_entity("transferase", limit=20)
# Found: KW-0808 (Transferase keyword in MIE schema)

# 5. Validation - use structured property for ALL matching entities
query = """
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX keywords: <http://purl.uniprot.org/keywords/>

SELECT ?phylum (COUNT(DISTINCT ?protein) as ?count)
WHERE {
  ?protein up:reviewed 1 ;
           up:classifiedWith keywords:KW-0808 ;  # Structured property
           up:organism ?organism .
  ?organism rdfs:subClassOf+ ?phylumNode .
  ?phylumNode up:rank "phylum" ;
              up:scientificName ?phylum .
}
GROUP BY ?phylum
ORDER BY DESC(?count)
LIMIT 100
"""
```

---

## Critical Rules

### ✅ ALWAYS

1. **Analyze question first** - Understand domain and query type
2. **Run list_databases()** - Identify relevant databases
3. **Load MIE files** - Get schema and kw_search_tools for selected databases
4. **Use kw_search_tools first** - Search before writing SPARQL
5. **Prefer structured properties** - Use classifications/ontologies before bif:contains
6. **Use LIMIT in SPARQL** - Start with 20-100
7. **Filter UniProt** - Always add `?protein up:reviewed 1`
8. **Use TogoID after getting IDs** - Convert to link across databases
9. **Check ID conversion routes** - Use `togoid_getRelation()` before converting

### ❌ NEVER

1. **Don't skip list_databases()** - You might miss relevant databases
2. **Don't skip get_MIE_file()** - You'll waste time guessing at structure
3. **Don't use bif:contains first** - Always try structured properties
4. **Don't use VALUES for comprehensive queries** - This is circular reasoning!
   - ❌ WRONG: Search → Get 20 IDs → Query only those 20 → Conclude
   - ✅ RIGHT: Search → Identify structured properties → Query ALL matching entities
5. **Don't omit LIMIT** - Can cause timeouts

---

## Circular Reasoning Trap

**❌ WRONG Approach:**
```python
# Get 20 examples from search
results = search_uniprot_entity("enzyme", limit=20)
ids = [r['id'] for r in results]

# Only query those 20 - CIRCULAR REASONING!
query = f"VALUES ?protein {{ {' '.join(ids)} }}"
```

**✅ CORRECT Approach:**
```python
# Get examples to identify structured properties
results = search_uniprot_entity("enzyme", limit=20)
# Found: KW-0418 (Kinase), KW-0808 (Transferase)

# Query ALL entities with that classification
query = """
?protein up:classifiedWith ?classification .
VALUES ?classification { keywords:KW-0418 keywords:KW-0808 }
"""
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Which database to use?** | Run `list_databases()`, match domain to databases |
| **Which search tool?** | Check MIE file's kw_search_tools field |
| **No search results** | Try synonyms, broader terms, different database |
| **SPARQL fails** | Verify MIE file loaded, add LIMIT, check prefixes |
| **Slow/timeout** | Reduce LIMIT, add `up:reviewed 1` for UniProt |
| **ID conversion empty** | Check route: `togoid_getRelation(source, target)` |
| **Incomplete comprehensive results** | Use structured properties from MIE, not VALUES with limited IDs |

---

## All 23 Databases

**Proteins:** uniprot, pdb, ensembl  
**Chemicals:** pubchem, chembl, chebi  
**Diseases:** mondo, mesh, medgen, clinvar, nando  
**Pathways:** reactome, go  
**Reactions:** rhea  
**Genes:** ncbigene  
**Taxonomy:** taxonomy  
**Literature:** pubmed, pubtator  
**Microbiology:** bacdive, mediadive, amrportal  
**Sequences:** ddbj  
**Glycans:** glycosmos

---

## Workflow Summary

```
1. Analyze Question
   ↓
2. list_databases() → Identify relevant databases
   ↓
3. get_MIE_file(dbname) for each database → Get kw_search_tools and schema
   ↓
4. Discovery: Use kw_search_tools → Find examples, identify structured properties
   ↓
5. Validation: SPARQL with structured properties → Get IDs and data
   ↓
6. TogoID: Convert IDs to other databases (if needed)
   ↓ ─────┐
   │       │ (If querying new database)
   │       └→ Return to Steps 3-5 for new database
   ↓
7. Present results with citations from all databases
```

**Key Principle:** Structured properties FIRST, bif:contains LAST RESORT.
