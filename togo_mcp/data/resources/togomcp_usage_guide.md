# TogoMCP Usage Guide

## ⚡ QUICK START (Read This First)

```
┌─────────────────────────────────────────────────┐
│ What's your question type?                      │
├─────────────────────────────────────────────────┤
│ "Which has MOST/LEAST/MORE?"                    │
│ → Use COMPARATIVE WORKFLOW below                │
│                                                  │
│ "How many...", "Find all...", "List..."         │
│ → Use STANDARD WORKFLOW below                   │
│                                                  │
│ "Find protein TP53", "Get details for..."       │
│ → Use search tools (skip to Tools section)      │
└─────────────────────────────────────────────────┘
```

---

## 🔍 STEP 0: DATABASE DISCOVERY (ALWAYS START HERE!)

**Call `list_databases()` to discover which databases contain your data:**

```python
list_databases()  # Returns: 23 databases with descriptions

# Match keywords in descriptions to your query:
# "MANE" → Ensembl (not just NCBI Gene!)
# "drug targets" + "approved" → ChEMBL
# "clinical variants" → ClinVar
# "pathways" → Reactome
```

### Quick Workflow

```python
# 1. Discover databases by keywords
list_databases()  # Read descriptions

# 2. Check if they share endpoints (for cross-DB queries)
get_sparql_endpoints()

# 3. Get schemas for identified databases
get_MIE_file('ensembl')  # Found "MANE" in description
get_MIE_file('chembl')   # Found "drug targets" in description

# 4. Query using discovered structured properties
```

### Common Mistake

❌ **Assuming:** "MANE is NCBI, so use ncbigene" → Empty results  
✅ **Discovering:** `list_databases()` shows "MANE" in Ensembl → Success

**When to use:** Starting new queries, uncertain about database, query has multiple concepts, or getting empty results  
**When to skip:** Already know exact database from prior work in same session

**Rule of thumb:** 5 seconds of discovery prevents hours of debugging

---

## 🔌 ENDPOINT ARCHITECTURE (CRITICAL!)

**Before any multi-database query, check if databases share an endpoint:**

```python
get_sparql_endpoints()
# Returns: which databases are on which endpoints
```

### Can Query Together (Same Endpoint)
✅ **ncbi endpoint:** ClinVar + PubMed + PubTator + NCBI Gene + MedGen  
✅ **primary endpoint:** MeSH + GO + Taxonomy + MONDO + NANDO  
✅ **ebi endpoint:** ChEMBL + ChEBI + Reactome + Ensembl  
✅ **sib endpoint:** UniProt + Rhea  

### CANNOT Query Together (Different Endpoints)
❌ NCBI Gene (ncbi) + Taxonomy (primary)  
❌ UniProt (sib) + ChEMBL (ebi)  
❌ PubChem (pubchem) + any other database  

### When Databases Are on Different Endpoints

**You MUST use hybrid approach:**

```python
# Example: Count genes by phylum (ncbigene + taxonomy on different endpoints)

# Step 1: Get ALL gene IDs (use API, not SPARQL)
all_genes = []
for offset in range(0, total_count, 100):
    batch = ncbi_esearch("gene", query, max_results=100, start_index=offset)
    all_genes.extend(batch)  # Don't stop at 100! Get ALL results

# Step 2: Get organism taxids (batch process)
phylum_counts = {}
for gene_batch in batches(all_genes, 50):
    summaries = ncbi_esummary("gene", gene_batch)
    taxids = [s['organism']['taxid'] for s in summaries]
    
    # Step 3: Map taxids to phyla (now can use SPARQL on taxonomy)
    for taxid in taxids:
        phylum = run_sparql(dbname="taxonomy", query=f"""
            SELECT ?phylum WHERE {{
                taxon:{taxid} rdfs:subClassOf+ ?phylum .
                ?phylum tax:rank tax:Phylum .
            }}
        """)
        phylum_counts[phylum] = phylum_counts.get(phylum, 0) + 1

# Step 4: Compare
sorted(phylum_counts.items(), key=lambda x: x[1], reverse=True)
```

**⚠️ CRITICAL: Process ALL results, not just samples!**

### Batch Processing Implementation

```python
# COMPLETE PATTERN: Process 1,000+ items efficiently
all_gene_ids = []  # From ncbi_esearch (e.g., 1,367 IDs)
phylum_counts = {}

# Batch 1: ncbi_esummary (50-100 IDs per call)
for i in range(0, len(all_gene_ids), 50):
    batch_ids = all_gene_ids[i:i+50]
    summaries = ncbi_esummary("gene", batch_ids)
    taxids = [s['organism']['taxid'] for s in summaries]
    
    # Batch 2: SPARQL (10-15 taxids per query)
    for j in range(0, len(taxids), 10):
        taxid_batch = taxids[j:j+10]
        query = f"""
            VALUES ?taxid {{ {' '.join([f'taxon:{t}' for t in taxid_batch])} }}
            ?taxid rdfs:subClassOf+ ?phylum .
            ?phylum tax:rank tax:Phylum .
        """
        results = run_sparql(dbname="taxonomy", query=query)
        for result in results:
            phylum_counts[result['phylumLabel']] += 1

# Total calls: ~(1367/50 + 1367/10) = ~27 + 137 = ~164 calls
```

**Performance Notes:**
- **ncbi_esummary**: 50-100 IDs optimal, max ~200
- **SPARQL VALUES**: 10-15 items optimal, fails >20
- **Rate limits**: None on TogoMCP; 60s timeout per query
- **Expected scale**: 50-200 calls for 1,000 items is normal

**Error Recovery:**
```python
# Save progress for long-running queries
import json
for batch_num, batch in enumerate(batches(all_items, 50)):
    # Process batch...
    phylum_counts[phylum] += 1
    
    # Save after each batch (every ~50 items)
    if batch_num % 10 == 0:  # Every 500 items
        with open('/tmp/progress.json', 'w') as f:
            json.dump(phylum_counts, f)
```

---

## 🚨 COMPARATIVE WORKFLOW ("which has MOST/LEAST")

**Use this for:** "Which phylum has most genes?", "Which organism has more proteins?"

### Critical Rule: Don't Be Circular!

**❌ WRONG (Circular Reasoning):**
```python
# 1. Search finds 100 examples from category A
# 2. Count only category A: "A has the most!"
# ❌ Problem: Never checked categories B, C, D!
```

**✅ RIGHT (Systematic):**
```python
# 1. Get MIE → find structured properties
# 2. ENUMERATE ALL categories (A, B, C, D...)
# 3. Use BROAD search: "(term1 OR term2 OR description)"
# 4. Count in EACH category
# 5. Compare systematically
```

### 6-Step Checklist

☐ **0. Check endpoints** → `get_sparql_endpoints()` if multi-database  
☐ **1. Get MIE file** → find structured properties  
☐ **2. Enumerate ALL categories** → don't assume, list them!  
☐ **3. Broad search query** → use OR: `"(nifH OR 'nitrogenase iron protein')"`  
☐ **4. Count EACH category** → process ALL results, not samples!  
☐ **5. Compare** → ORDER BY DESC(?count) to find winner  

### When to Stop vs Continue Processing

**❌ NEVER stop early (100% required):**
- **Comparative**: "Which has MOST/LEAST?" → Must count ALL
- **Exact counts**: "How many total..." → Must count ALL
- **Rankings**: "Top 10...", "Rank by..." → Must count ALL
- **Factoid answers**: Any definitive answer → Must be comprehensive

**✅ OK to stop early (sampling acceptable):**
- **Exploratory**: "Are there ANY X?" → Stop after finding examples
- **Approximate**: "Roughly how many..." → Representative sample OK

**Rule**: Questions with "most", "least", "all", "none", "exact", or requiring ranking → process 100%

**Example 1: Same Endpoint (Single SPARQL)**
```python
# Q: "Which organism has more kinases - human or mouse?"
# UniProt is all on 'sib' endpoint - can use single query

get_MIE_file('uniprot')  # up:organism, up:classifiedWith
get_sparql_endpoints()   # Confirm: uniprot on 'sib' endpoint

query = """
SELECT ?organism (COUNT(?p) as ?count) WHERE {
  ?p up:reviewed 1 ;
     up:classifiedWith <http://purl.uniprot.org/keywords/418> ;
     up:organism ?organism .
  FILTER(?organism IN (
    <http://purl.uniprot.org/taxonomy/9606>,
    <http://purl.uniprot.org/taxonomy/10090>
  ))
}
GROUP BY ?organism ORDER BY DESC(?count)
"""
```

**Example 2: Different Endpoints (Hybrid Approach)**
```python
# Q: "Which archaeal phylum has most nifH genes?"
# ncbigene (ncbi) + taxonomy (primary) = different endpoints!

get_sparql_endpoints()  # Confirm: different endpoints
get_MIE_file('taxonomy')  # Find: tax:rank, rdfs:subClassOf

# Step 1: Enumerate all phyla (taxonomy DB)
phyla = run_sparql(dbname="taxonomy", query="""
  SELECT DISTINCT ?phylum WHERE {
    ?phylum tax:rank tax:Phylum ;
            rdfs:subClassOf+ taxon:2157 .
  }
""")  # Found: 12 phyla

# Step 2: Get ALL genes (API - can't join in SPARQL)
all_genes = []
for offset in range(0, 1367, 100):  # Don't stop at 100!
    batch = ncbi_esearch("gene", 
                         "Archaea[Organism] AND (nifH[Gene Name] OR nitrogenase)",
                         max_results=100, start_index=offset)
    all_genes.extend(batch)

# Step 3: Count each phylum (batch process ALL)
phylum_counts = {}
for gene_batch in batches(all_genes, 50):
    summaries = ncbi_esummary("gene", gene_batch)
    for gene in summaries:
        taxid = gene['organism']['taxid']
        # Map to phylum via taxonomy DB
        result = run_sparql(dbname="taxonomy", query=f"""
            SELECT ?phylum WHERE {{
                taxon:{taxid} rdfs:subClassOf+ ?phylum .
                ?phylum tax:rank tax:Phylum .
            }}
        """)
        if result:
            phylum_counts[result[0]] = phylum_counts.get(result[0], 0) + 1

# Result: Methanobacteriota: 1,298, Thermoproteota: 18, ...
```

---

## 📋 STANDARD WORKFLOW (comprehensive queries)

**Use this for:** "How many...", "Find all...", "Are there any..."

### 3-Step Process

**1. GET MIE FILE FIRST (MANDATORY)**
```python
get_MIE_file('dbname')
# Check: shape_expressions section
# Find: classification predicates, external IRIs, typed predicates
```

**2. SEARCH FOR EXAMPLES**
- Use search tools if listed in `kw_search_tools`
- Or exploratory SPARQL (LIMIT 10)
- **Use OR logic:** `"(term OR synonym OR description)"`

**3. INSPECT & QUERY**
```sparql
# Inspect examples:
SELECT * WHERE { VALUES ?entity {...} ?entity ?p ?o } LIMIT 100

# Then comprehensive query using discovered properties
SELECT (COUNT(?x) as ?count) WHERE {
  ?x structured_property <value> .  # From MIE schema
}
```

### Before SPARQL: Gate Check

❓ Multi-database? Checked endpoints first?  
❓ Got MIE file?  
❓ Found structured property in schema?  
❓ Inspected examples to confirm?  
❓ Using structured predicates (not bif:contains)?  

**NO to any? → STOP, complete that step**

---

## 🔑 KEY RULES

### Rule 0: Database Discovery First
**Call `list_databases()` to identify relevant databases**

- Read database descriptions for keyword matches
- Identify 1-3 databases before calling MIE files
- **Never assume** a database contains data without checking
- Prevents 50-80% of "empty results" errors

### Rule 1: Check Endpoints for Multi-Database Queries
**Call `get_sparql_endpoints()` before combining databases**

- Same endpoint → single SPARQL with multiple GRAPHs
- Different endpoints → hybrid approach (API + SPARQL)
- **Never assume** databases can be joined

### Rule 2: MIE File First
**95% of failures = skipping `get_MIE_file()`**

Check these in schema:
- Classification predicates (atcClassification, classifiedWith)
- External IRIs (taxonomy, MeSH, GO terms)
- Typed predicates (assayType, status, phase)
- Hierarchies (subClassOf, pathwayComponent)

### Rule 3: Use OR Logic for Broad Searches
**Wrong:** `"nifH"` → finds 286 genes (21%)  
**Right:** `"(nifH OR 'nitrogenase iron protein')"` → finds 1,367 genes (100%)

### Rule 4: Structured > Text Search
```
Priority: Structured Properties > bif:contains
            (ALWAYS)              (RARE <5%)
```

**bif:contains ONLY if:** No structured alternative exists after checking MIE + inspecting examples

### Rule 5: No Circular Reasoning
**Never:**
- Search → get examples → query ONLY those examples
- That's circular - you only checked what you found!

**Always:**
- For comparisons: enumerate ALL categories first
- Use structured predicates to search entire database

---

## 🛠️ TOOLS REFERENCE

### Schema & Discovery
- `list_databases()` - **🔍 CALL THIS FIRST to discover which databases to use**
- `get_MIE_file(dbname)` - **Get schema for identified databases**
- `get_sparql_endpoints()` - **Check before multi-database queries**

### Search (Exploratory)
- `ncbi_esearch(database, query)` - NCBI databases
- `search_uniprot_entity(query)` - Proteins
- `search_chembl_molecule(query)` - Drugs
- `search_chembl_target(query)` - Drug targets
- `search_pdb_entity(db, query)` - Structures
- `search_reactome_entity(query)` - Pathways
- `search_rhea_entity(query)` - Reactions

### SPARQL
- `run_sparql(dbname, query)` - Execute query

### ID Conversion
- `togoid_convertId(ids, route)` - Convert between databases

---

## 📖 QUICK EXAMPLES

### Example 1: Simple Count
```python
# Q: "How many human proteins?"
get_MIE_file('uniprot')  # Found: up:organism predicate
query = """
SELECT (COUNT(?p) as ?count) WHERE {
  ?p up:reviewed 1 ;
     up:organism <http://purl.uniprot.org/taxonomy/9606> .
}
"""
```

### Example 2: Comparative
```python
# Q: "Which organism has more kinases - human or mouse?"
get_MIE_file('uniprot')  # Found: up:classifiedWith, up:organism

# Don't search and count only results!
# Instead: query both systematically
query = """
SELECT ?organism (COUNT(?p) as ?count) WHERE {
  ?p up:reviewed 1 ;
     up:classifiedWith <http://purl.uniprot.org/keywords/418> ;
     up:organism ?organism .
  FILTER(?organism IN (
    <http://purl.uniprot.org/taxonomy/9606>,
    <http://purl.uniprot.org/taxonomy/10090>
  ))
}
GROUP BY ?organism
"""
```

### Example 3: With Classification
```python
# Q: "How many antibiotics in ChEMBL?"
get_MIE_file('chembl')  # Found: cco:atcClassification

# Don't search "antibiotic" in text!
# Use classification:
query = """
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
SELECT (COUNT(?m) as ?count) 
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?m cco:atcClassification ?atc .
  FILTER(STRSTARTS(?atc, "J01"))
}
"""
```

---

## 🚫 TOP 5 MISTAKES

### 1. Skipping Database Discovery
**Impact:** Query wrong database, miss 50-80% of relevant data  
**Example:** Query "MANE Select" but only check NCBI Gene, miss Ensembl entirely  
**Fix:** Call `list_databases()` first, read descriptions for keywords

### 2. Assuming Cross-Database SPARQL Works
**Impact:** Query fails, confusion about why  
**Fix:** Call `get_sparql_endpoints()` first

### 3. Skipping MIE File
**Impact:** Wasted 1 hour → could be 1 minute

### 4. Sampling Instead of Exhaustive Processing
**Impact:** Wrong answer - counted 46/1,367 organisms (3% sample) and claimed "confident"  
**Why wrong:** For "which has MOST", 91% sample confidence ≠ 100% accurate count  
**Fix:** Process ALL results with pagination (~164 API calls for 1,367 items is normal)

### 5. Using bif:contains Without Checking Schema
**Impact:** 10-100x slower, incomplete results

---

## 🆘 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| Cross-DB query fails | Check `get_sparql_endpoints()` - use hybrid if different |
| Empty results | Check MIE schema for property names |
| Timeout | Add LIMIT, use structured predicates |
| Incomplete results | Did you use OR logic? Process ALL results? |
| "Which has most" is wrong | Did you enumerate ALL categories & process ALL results? |

---

---

## 🚫 ERROR HANDLING

### Common Batch Processing Errors

```python
# Pattern: Robust batch processing
failed_items = []
for batch in batches(all_items, batch_size):
    try:
        results = process_batch(batch)
        for item, result in zip(batch, results):
            if result:  # Valid result
                counts[result] += 1
            else:  # Missing/null result
                failed_items.append(item)
    except Exception as e:
        print(f"Batch failed: {e}")
        failed_items.extend(batch)

if failed_items:
    print(f"Warning: {len(failed_items)} items failed processing")
```

**Common issues:**
- **Missing data**: New organisms lacking phylum classification → skip and log
- **Timeout**: SPARQL query too large → reduce batch size to 5-10
- **Empty results**: Taxid not in database → normal, continue processing

---

## 🎯 REMEMBER

**Call list_databases() to discover relevant databases - this is reconnaissance, not optional**

**Check endpoints FIRST for multi-database queries**

**The MIE file is your map - read it before querying**

**Process ALL results, not samples - pagination is your friend**

**Comparisons: Enumerate ALL → Count EACH → Compare**

**Broad searches: Use OR logic for synonyms**

**1 minute planning > 1 hour debugging**
