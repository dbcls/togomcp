# TogoMCP Usage Guide

A step-by-step workflow for answering user questions using TogoMCP tools.

---

## Quick Workflow

### Step 1: Extract Keywords
Identify key terms, IDs, and domain (proteins, chemicals, diseases, genes, pathways, etc.)

### Step 2: Select Databases
Run `list_databases()` and choose by domain:
- Proteins: `uniprot`, `pdb`, `ensembl`, `ncbigene`
- Chemicals: `pubchem`, `chembl`, `chebi`, `rhea`
- Diseases: `mondo`, `mesh`, `medgen`, `clinvar`
- Pathways: `reactome`, `go`

### Step 3: Search - ALWAYS Try Tools First

**Available Search Tools:**
- `search_uniprot_entity(query, limit)` - proteins (searches names, descriptions, AND disease associations)
- `search_chembl_molecule/target(query, limit)` - drugs/targets
- `search_pdb_entity(db, query, limit)` - structures
- `search_reactome_entity(query, rows)` - pathways
- `search_rhea_entity(query, limit)` - reactions
- `search_mesh_entity(query, limit)` - medical concepts

**Decision Tree:**
```
Try search tool → Got results? → Use them
                → Insufficient? → Try different keywords
                → Still no? → Use SPARQL (Step 4)
```

**Don't assume limitations - search tools are more powerful than their names suggest.**

### Step 4: SPARQL (When Needed)

**Before SPARQL, ALWAYS run:** `get_MIE_file(dbname)`

**Use SPARQL when you need:**
- Specific annotation types (Disease_Annotation vs Function_Annotation)
- Complex boolean logic (X AND Y AND NOT Z)
- Precise field targeting (search only within specific predicates)
- Aggregations (COUNT, GROUP BY)

**Critical Rules:**
- UniProt: Always filter `up:reviewed 1`
- ChEMBL: Use `FROM <http://rdf.ebi.ac.uk/dataset/chembl>`
- Split property paths when using `bif:contains`
- Always use `LIMIT` (20-100)

### Step 5: Connect IDs
Use TogoID to convert between databases:
```python
togoid_convertId(ids="P04637,P17612", route="uniprot,chembl_target")
```

### Step 6: Synthesize Results
Combine information, cite sources, note limitations.

---

## Best Practices

✅ **Test, don't assume** - Try search tools before SPARQL
✅ **Read MIE files** - Before writing any SPARQL
✅ **Combine approaches** - Search for breadth, SPARQL for depth
✅ **Start simple** - Escalate complexity only when needed

❌ Don't skip search tools based on assumptions
❌ Don't write SPARQL without reading MIE file
❌ Don't forget `up:reviewed 1` in UniProt
❌ Don't use `bif:contains` with property paths

---

## Complementary Approach: Search + SPARQL

**For comprehensive results, use both:**

```
1. search_uniprot_entity("cardiovascular disease") → Quick overview
2. SPARQL on Disease_Annotation → Targeted precision
3. Merge results, remove duplicates → Comprehensive coverage
```

**When to use both:**
- Initial exploration (search) + comprehensive analysis (SPARQL)
- Quality check (compare both methods)
- Different aspects (search names, SPARQL annotations)

---

## Quick Examples

**Disease-protein associations:**
```python
# Start with search
search_uniprot_entity("hypertension", limit=20)
# If incomplete, add SPARQL targeting Disease_Annotation
```

**Finding drug targets:**
```python
# Search protein
search_uniprot_entity("angiotensin converting enzyme")
# Convert to ChEMBL
togoid_convertId(ids="P12821", route="uniprot,chembl_target")
# Find inhibitors in ChEMBL
```

**Pathway analysis:**
```python
search_reactome_entity("apoptosis", rows=30)
```

---

## Common Query Patterns

| Question Type | Start With | Then |
|--------------|------------|------|
| "Proteins with disease X" | `search_uniprot_entity("disease")` | SPARQL if needed |
| "Drugs targeting protein Y" | `search_uniprot_entity("protein")` | Convert to ChEMBL |
| "Structure of protein Z" | `search_uniprot_entity("protein")` | Convert to PDB |
| "Pathways involving gene A" | `search_reactome_entity("gene")` | Cross-reference |

---

## Remember

**The goal is to find the best answer efficiently, not to use the most sophisticated tool.**

1. Try search tools first (they're more capable than you think)
2. Use SPARQL for precision when needed
3. Combine both for comprehensive results
4. Always read MIE files before SPARQL