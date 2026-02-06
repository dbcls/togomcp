# TogoMCP Usage Guide (Concise)

## Critical Concepts

### ⚠️ Search vs. Comprehensive Queries

**Search APIs (Exploratory)**
- Purpose: Find patterns, examples, cross-references
- Returns: 10-20 results typically
- Use for: Understanding data, identifying entities
- **NOT for**: Definitive answers to comprehensive questions

**SPARQL (Comprehensive)**
- Purpose: Validation, complete analysis, definitive answers
- Returns: All matching entities
- Use for: Aggregations, existence claims, phylogenetic distribution
- **Required for**: Yes/no questions, "are there any...", "which organisms..."

### Circular Reasoning Trap ⚠️

**WRONG** - Using search results in SPARQL VALUES:
```
1. Search API finds 8 example proteins
2. Hardcode those IDs: VALUES ?protein { uniprot:P1 uniprot:P2 ... }
3. Query only those 8 proteins
→ CIRCULAR: You only checked what you already found!
```

**CORRECT** - Comprehensive search with bif:contains:
```
1. Search API finds examples (identify patterns/synonyms)
2. SPARQL searches ALL entities: bif:contains "'term1' OR 'term2' OR 'term3'"
3. Aggregate complete results
→ COMPREHENSIVE: Checked everything matching criteria
```

---

## Quick Reference: Tools by Purpose

### Discovery
- `list_databases()` - List 22 RDF databases
- `get_sparql_endpoints()` - Get endpoint URLs and search tools
- `togoid_getAllDataset()` - ID conversion routes
- `ncbi_list_databases()` - NCBI databases

### Search (Exploratory)
| Domain | Tool |
|--------|------|
| Proteins | `search_uniprot_entity(query, limit=20)` |
| Drugs/Molecules | `search_chembl_molecule(query, limit=20)` |
| Drug Targets | `search_chembl_target(query, limit=20)` |
| 3D Structures | `search_pdb_entity(db, query, limit=20)` db: "pdb"/"cc"/"prd" |
| Pathways | `search_reactome_entity(query, rows=30)` |
| Reactions | `search_rhea_entity(query, limit=100)` |
| Medical Terms | `search_mesh_entity(query, limit=10)` |
| Ontologies | `OLS4:search(query)` or `OLS4:searchClasses(query, ontologyId)` |
| Chemicals | `get_pubchem_compound_id(name)` → `get_compound_attributes_from_pubchem(id)` |
| NCBI | `ncbi_esearch(database, query)` - Gene, Taxonomy, ClinVar, MedGen, PubMed, PubChem |

### SPARQL (Comprehensive)
- `get_MIE_file(dbname)` - **MANDATORY** before SPARQL: schema + examples
- `run_sparql(dbname, query)` - Execute query
- `get_sparql_example(dbname)` - Example queries
- `get_graph_list(dbname)` - Named graphs

### ID Conversion (TogoID)
- `togoid_convertId(ids, route)` - Convert IDs (e.g., "uniprot,pdb")
- `togoid_getRelation(source, target)` - Check if route exists
- `togoid_countId(ids, source, target)` - Count convertible IDs

### Retrieval
- `ncbi_esummary(database, ids)` - Summaries
- `ncbi_efetch(database, ids, rettype)` - Full records
- `OLS4:fetch(id)` - Ontology term details
- `OLS4:getAncestors/getDescendants(classIri, ontologyId)` - Hierarchy

---

## Complete Workflow

```
1. ANALYZE QUERY
   ├─ Extract keywords, IDs, entities
   ├─ Identify domain (proteins/chemicals/diseases/etc.)
   └─ Classify: Comprehensive (yes/no, exists) or Example-based (specific, top-N)?

2. SELECT DATABASE(S)
   └─ Run list_databases() if unsure

3. EXECUTE SEARCH (EXPLORATORY)
   ├─ ALWAYS try search tools first
   ├─ Find patterns, examples, synonyms
   ├─ Document ALL variations for Step 4
   └─ Multiple keywords if needed

4. SPARQL (if needed)
   ├─ MANDATORY: get_MIE_file(dbname) first
   ├─ Comprehensive query: Use bif:contains with ALL search terms (NO VALUES)
   ├─ Example-based query: Can use VALUES with specific IDs
   └─ ALWAYS include LIMIT

5. CONVERT IDs
   ├─ Check route: togoid_getRelation(source, target)
   └─ Convert: togoid_convertId(ids, route)

6. RETRIEVE DETAILS
   └─ Use ncbi_esummary/efetch, OLS4:fetch, etc.

7. SYNTHESIZE RESULTS
   ├─ Combine all sources
   ├─ Cite databases used
   └─ State methodology (comprehensive vs example-based)
```

---

## Database Quick Reference

| Category | Database | Search Tool | Description |
|----------|----------|-------------|-------------|
| **Proteins** | uniprot | search_uniprot_entity | 444M proteins, functions |
| | pdb | search_pdb_entity | 204K 3D structures |
| **Chemicals** | pubchem | ncbi_esearch | 119M compounds |
| | chembl | search_chembl_molecule/target | 2.4M bioactive molecules |
| | chebi | OLS4:searchClasses | 217K entities |
| **Diseases** | mondo | OLS4:searchClasses | 30K disease classes |
| | mesh | search_mesh_entity | 30K descriptors |
| | clinvar | ncbi_esearch | 3.5M variants |
| **Pathways** | reactome | search_reactome_entity | 22K pathways |
| | go | OLS4:searchClasses | 48K GO terms |
| **Reactions** | rhea | search_rhea_entity | 17K reactions |
| **Genes** | ncbigene | ncbi_esearch | 57M gene entries |
| **Taxonomy** | taxonomy | ncbi_esearch | 3M organisms |
| **Literature** | pubmed | ncbi_esearch | Biomedical lit |

---

## Critical SPARQL Rules

### MANDATORY Prerequisites
```python
# ALWAYS run this BEFORE writing SPARQL
get_MIE_file(dbname)  # Schema, RDF patterns, examples
```

### Database-Specific Rules
| Database | Critical Rule |
|----------|--------------|
| **UniProt** | ALWAYS filter: `?protein up:reviewed 1` (Swiss-Prot quality) |
| **ChEMBL** | Use: `FROM <http://rdf.ebi.ac.uk/dataset/chembl>` |
| **Full-text** | Split property paths when using `bif:contains` |
| **All** | ALWAYS use `LIMIT` (start with 20-100) |
| **Comprehensive** | Use `bif:contains` with OR, NOT VALUES |

### Comprehensive vs Example-Based Queries

**Example-Based (Specific lookups, Top-N)**
```sparql
# Can use VALUES with specific IDs from search
VALUES ?protein { uniprot:P04637 uniprot:P38398 }
?protein up:reviewed 1 ;
         up:recommendedName/up:fullName ?name .
```

**Comprehensive (Yes/No, Exists, Distribution)**
```sparql
# MUST use bif:contains with ALL search terms
?protein up:reviewed 1 ;
         up:recommendedName ?name .
?name up:fullName ?fullName .
# Use ALL synonyms found in exploratory search
?fullName bif:contains "'term1' OR 'synonym1' OR 'variant1' OR 'abbrev1'"
```

---

## Common Patterns

### Pattern 1: Comprehensive Phylogenetic Distribution
```python
# Question: "Are X enzymes found in phyla beyond Y and Z?"

# Step 1: Exploratory search (find synonyms)
results = search_uniprot_entity("enzyme name", limit=20)
# Document: "enzyme", "alternative name", "abbreviation"

# Step 2: Get schema
get_MIE_file("uniprot")

# Step 3: Comprehensive SPARQL
query = """
PREFIX up: <http://purl.uniprot.org/core/>
SELECT DISTINCT ?protein ?phylum
WHERE {
  ?protein up:reviewed 1 ;
           up:recommendedName ?name ;
           up:organism ?organism .
  ?name up:fullName ?fullName .
  ?fullName bif:contains "'enzyme' OR 'alternative' OR 'abbrev'"
  
  ?organism rdfs:subClassOf+ ?phylumNode .
  ?phylumNode up:rank "phylum" ;
              up:scientificName ?phylum .
}
LIMIT 1000
"""
results = run_sparql("uniprot", query)

# Step 4: Aggregate by phylum
phyla = {}
for r in results:
    phyla[r['phylum']] = phyla.get(r['phylum'], 0) + 1
```

### Pattern 2: Disease-Associated Proteins
```python
# Step 1: Search (exploratory)
proteins = search_uniprot_entity("Alzheimer disease", limit=50)

# Step 2: If more precision needed
get_MIE_file("uniprot")
query = """
PREFIX up: <http://purl.uniprot.org/core/>
SELECT ?protein ?name ?disease
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

### Pattern 3: Drug Targets → Inhibitors
```python
# Step 1: Find target
protein = search_uniprot_entity("ACE human", limit=5)  # P12821

# Step 2: Convert to ChEMBL
target = togoid_convertId("P12821", "uniprot,chembl_target")

# Step 3: Search inhibitors
inhibitors = search_chembl_molecule("ACE inhibitor", limit=20)

# Step 4: Get properties
cid = get_pubchem_compound_id("lisinopril")
props = get_compound_attributes_from_pubchem(cid)
```

### Pattern 4: Gene → Structures/Drugs/Pathways
```python
# 1. Find gene
gene = ncbi_esearch("gene", "EGFR human")  # 1956

# 2. Convert to UniProt
uniprot = togoid_convertId("1956", "ncbigene,uniprot")  # P00533

# 3. Get structures
pdbs = togoid_convertId("P00533", "uniprot,pdb")

# 4. Get drug targets
targets = togoid_convertId("P00533", "uniprot,chembl_target")

# 5. Search pathways
pathways = search_reactome_entity("EGFR signaling", rows=20)
```

---

## Critical Rules

### ✅ ALWAYS
1. Try search tools first (exploratory)
2. Run `get_MIE_file()` before SPARQL
3. Use `LIMIT` in SPARQL
4. Filter UniProt: `up:reviewed 1`
5. Document search terms for comprehensive queries
6. For comprehensive questions: Use `bif:contains` with ALL synonyms
7. Cite data sources
8. State methodology (comprehensive vs example-based)

### ❌ NEVER
1. Skip search tools
2. Write SPARQL without MIE file
3. Forget `up:reviewed 1` in UniProt
4. Omit `LIMIT`
5. Use VALUES with search results for comprehensive questions (circular reasoning!)
6. Conclude from examples alone for comprehensive questions
7. Use `bif:contains` with property paths (split them)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No search results | Try synonyms, broader terms, different database |
| SPARQL fails | Run get_MIE_file()? Check prefixes, add LIMIT, use up:reviewed 1 |
| ID conversion empty | Check togoid_getRelation(), verify ID format, try multi-hop |
| Timeout | Reduce LIMIT, add filters, use up:reviewed 1, try search instead |
| Incomplete comprehensive results | Use bif:contains with ALL synonyms, not VALUES |

---

## Key Databases & Routes

**Common ID Conversions:**
- UniProt ↔ PDB: `"uniprot,pdb"` or `"pdb,uniprot"`
- UniProt → NCBI Gene: `"uniprot,ncbigene"`
- NCBI Gene → Ensembl: `"ncbigene,ensembl_gene"`
- UniProt → ChEMBL: `"uniprot,chembl_target"`
- ChEBI → PubChem: `"chebi,pubchem_compound"`

**NCBI Databases:** gene, taxonomy, clinvar, medgen, pubmed, pccompound, pcsubstance, pcassay

**Ontologies (OLS4):** go, mondo, chebi, hp, uberon, doid, efo, obi, etc.
