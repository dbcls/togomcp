# RDF Portal Guide v15.0

## Core Principle
**MIE Files → Explore RDF → Comprehensive SPARQL → TogoID Only If Needed**

**MIE files** (Metadata Interoperability Exchange) contain ShEx schemas, RDF examples, and SPARQL templates - essential for understanding graph structures before querying.

Most cross-references exist in anchor RDF databases. Explore first, convert only when necessary.
- **70-95% coverage** achievable
- **2x faster** than tool-heavy approaches
- **Higher transparency** for research

---

## Workflow (10-20 minutes)

1. **MIE File Analysis** [CRITICAL] - Understand graph structure, properties, examples
2. **RDF Exploration** [MANDATORY] - Discover available cross-references
3. **Comprehensive SPARQL** [CORE] - Get ALL data in ONE query
4. **Execution** [CORE] - Run query, extract IDs
5. **TogoID** [IF NEEDED] - Only for missing databases
6. **Final Report** - Consolidate all findings

**Documentation:** Create ONE artifact at Step 1, then update it progressively after each step for a complete analysis record.

**Optional:** Use OLS for publication-grade keyword standardization

---

## Step 1: Analyze MIE File ⭐

### Get MIE File FIRST

**MIE files are CRITICAL** - they contain the graph structure, property definitions, and example queries.

```python
# Always start here!
mie_content = get_MIE_file(dbname="uniprot")

# Create initial artifact with MIE analysis
# Artifact name: rdf_analysis_results.md
```

**Create artifact: `rdf_analysis_results.md`**
```markdown
# RDF Portal Analysis Results

*This document is progressively updated at each step*

---

## Step 1: MIE File Analysis

### Database: uniprot

### MIE File Contents
[MIE content displayed here - includes ShEx schema, RDF examples, SPARQL examples]

### Key Elements Identified
- ShEx schema properties
- Cross-reference predicates (e.g., rdfs:seeAlso)
- Example SPARQL queries
- Data structure patterns
```

### Available Databases
```python
# List all available databases
databases = list_databases()

# Update artifact with database list
```

**Update artifact to add:**
```markdown
### Available Databases
[Database list displayed here]

**Common anchors identified:**
- uniprot, chembl, pubchem, pdb, reactome
- mesh, go, taxonomy, wikidata
```

---

## Step 2: Explore RDF Cross-References ⭐

### Discover Available Cross-References

```sparql
# What databases are linked?
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?refType (COUNT(DISTINCT ?protein) as ?count) 
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           rdfs:seeAlso ?ref .
  BIND(REPLACE(STR(?ref), "^(https?://[^/]+).*", "$1") AS ?refType)
}
GROUP BY ?refType
ORDER BY DESC(?count)
LIMIT 30
```

```python
# Execute discovery query
xref_results = run_sparql(dbname="uniprot", sparql_query=discovery_query)

# Update artifact with discovery results
```

**Update artifact to add:**
```markdown
---

## Step 2: Cross-Reference Discovery

### Discovery Query
```sparql
[Discovery query displayed here]
```

### Results
[Query results displayed here - showing available databases and counts]

### Sample Entity Analysis
**Entity examined:** P04637 (p53)

[Sample cross-references displayed here]

### Findings Summary

**Available in RDF (Use SPARQL):**
- ✅ PDB
- ✅ Reactome
- ✅ ChEMBL
- ✅ Ensembl

**Missing from RDF (Consider TogoID):**
- ❌ DrugBank
- ❌ KEGG

**Recommendation:** Use comprehensive SPARQL for available databases. Test TogoID coverage for missing databases.
```

---

## Step 3: Comprehensive SPARQL Query ⭐

### Design Pattern: ONE Query with OPTIONAL

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?protein ?label ?pdb ?reactome ?chembl ?ensembl
WHERE {
  # Core properties
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> .
  
  # REQUIRED: Anchor cross-reference
  ?protein rdfs:seeAlso ?pdb .
  FILTER(CONTAINS(STR(?pdb), "rdf.wwpdb.org"))
  
  # OPTIONAL: Additional databases
  OPTIONAL {
    ?protein rdfs:seeAlso ?reactome .
    FILTER(CONTAINS(STR(?reactome), "reactome"))
  }
  
  OPTIONAL {
    ?protein rdfs:seeAlso ?chembl .
    FILTER(CONTAINS(STR(?chembl), "chembl"))
  }
  
  OPTIONAL {
    ?protein rdfs:seeAlso ?ensembl .
    FILTER(CONTAINS(STR(?ensembl), "ensembl"))
  }
  
  # Content filters
  FILTER([your keyword filters])
}
LIMIT 100
```

```python
# Execute comprehensive query
comprehensive_query = """[Your SPARQL query here]"""
results = run_sparql(dbname="uniprot", sparql_query=comprehensive_query)

# Update artifact with query and results
```

**Update artifact to add:**
```markdown
---

## Step 3: Comprehensive SPARQL Query

### Query
```sparql
[Comprehensive SPARQL query displayed here]
```

### Results
[Query results displayed here]

### Coverage Analysis
- Total entities retrieved: [count]
- Entities with PDB: [count] ([percentage]%)
- Entities with Reactome: [count] ([percentage]%)
- Entities with ChEMBL: [count] ([percentage]%)
- Entities with Ensembl: [count] ([percentage]%)
```

**Key Points:**
- Use `OPTIONAL` for cross-refs to avoid excluding entities
- Get everything in ONE query, not multiple queries
- Filter by organism early for performance

---

## Step 4: Execution

Execute the SPARQL query and parse results to collect all cross-references for each entity.

```python
# Parse results and extract cross-reference IDs
import json

# Assuming results is a JSON response
parsed_results = json.loads(results)

# Extract and organize IDs by database
id_mapping = {}
for binding in parsed_results.get('results', {}).get('bindings', []):
    protein_id = extract_id(binding.get('protein', {}).get('value', ''))
    
    id_mapping[protein_id] = {
        'uniprot': protein_id,
        'pdb': extract_id(binding.get('pdb', {}).get('value', '')) if 'pdb' in binding else None,
        'reactome': extract_id(binding.get('reactome', {}).get('value', '')) if 'reactome' in binding else None,
        'chembl': extract_id(binding.get('chembl', {}).get('value', '')) if 'chembl' in binding else None,
        'ensembl': extract_id(binding.get('ensembl', {}).get('value', '')) if 'ensembl' in binding else None
    }

# Update artifact with extracted IDs
```

**Update artifact to add:**
```markdown
---

## Step 4: Extracted Cross-Reference IDs

### Summary
- Total proteins: [count]
- Proteins with PDB: [count]
- Proteins with Reactome: [count]
- Proteins with ChEMBL: [count]
- Proteins with Ensembl: [count]

### ID Mappings (JSON)
```json
[JSON formatted mappings displayed here]
```

### ID Mappings (TSV)
```
UniProt	PDB	Reactome	ChEMBL	Ensembl
[TSV formatted data displayed here]
```
```

---

## Step 5: TogoID (Only If Needed)

### When to Use TogoID

**Use ONLY if:**
- Database NOT in anchor RDF (<20% SPARQL coverage)
- TogoID coverage is better than SPARQL
- Need multi-hop conversion

**Test first:**
```python
# Test coverage before full conversion
sample_ids = "P04637,P00533,P21802"  # Sample
test_result = countId(
    ids=sample_ids,
    source="uniprot",
    target="drugbank"
)

coverage = test_result["target"] / test_result["source"]

# Update artifact with coverage test
```

**Update artifact to add:**
```markdown
---

## Step 5: TogoID Analysis

### Coverage Test
- Source: uniprot
- Target: drugbank
- Sample IDs: [IDs listed here]
- Source count: [count]
- Target count: [count]
- Coverage: [percentage]%

### Decision
[Good coverage decision or limitation documented here]
```

```python
if coverage > 0.5:
    # Good coverage - use TogoID
    all_uniprot_ids = ",".join(id_mapping.keys())
    converted = convertId(
        ids=all_uniprot_ids,
        route="uniprot,drugbank",
        report="pair"
    )
    
    # Update artifact with conversion results
```

**If good coverage, update artifact to add:**
```markdown
### Conversion Results
- Route: uniprot → drugbank
- Total IDs submitted: [count]
- Successfully converted: [count]
- Conversion rate: [percentage]%

### Converted IDs
[Conversion results displayed here]
```

**If poor coverage, update artifact to add:**
```markdown
### Limitation Documented
- Database: drugbank
- Coverage: [percentage]%
- Conclusion: TogoID coverage insufficient. Consider alternative approaches or accept data limitation.
```

---

## Step 6: Final Report

After completing all steps, finalize the artifact with a comprehensive summary.

```python
# Update artifact with final summary
```

**Update artifact to add:**
```markdown
---

## Final Report

### Project Overview
- Analysis Date: [date]
- Anchor Database: uniprot
- Target Organism: Homo sapiens (9606)
- Methodology: RDF Portal Guide v15.0

### Workflow Summary

**Step 1: MIE Analysis** ✅
- MIE file retrieved and analyzed
- ShEx schema documented
- RDF examples reviewed

**Step 2: RDF Exploration** ✅
- Cross-references discovered in RDF
- Sample entities examined
- Available databases identified

**Step 3: Comprehensive SPARQL** ✅
- Single comprehensive query executed
- Results: [count] proteins retrieved
- Coverage per database documented

**Step 4: ID Extraction** ✅
- Cross-reference IDs extracted
- Mappings available in JSON and TSV formats

**Step 5: TogoID** [✅ or N/A]
- Coverage test performed
- [Conversions completed or not needed]

### Final Coverage Summary

| Database | Source | Count | Coverage |
|----------|--------|-------|----------|
| PDB | SPARQL | [count] / [total] | [percentage]% |
| Reactome | SPARQL | [count] / [total] | [percentage]% |
| ChEMBL | SPARQL | [count] / [total] | [percentage]% |
| Ensembl | SPARQL | [count] / [total] | [percentage]% |

### Methodology Notes
- MIE-first approach for understanding graph structure
- Comprehensive SPARQL for efficient data retrieval
- TogoID used only when necessary
- Single artifact progressively updated for complete documentation

### Reproducibility
All queries, results, and methodologies documented in this artifact.
Analysis can be reproduced by following the documented steps.

---

**Analysis Complete** ✅
```

---

## Decision Tree

```
Need multiple databases?
  ↓
Get MIE file for anchor database
  ↓
Create artifact & document MIE analysis
  ↓
Study ShEx schema & examples
  ↓
Explore anchor RDF cross-references
  ↓
Update artifact with findings
  ↓
Databases in RDF (>80% coverage)?
  ├─ YES → Use comprehensive SPARQL, SKIP TogoID
  │        Update artifact with results
  └─ NO → Test TogoID coverage
           ├─ >50% → Use TogoID
           │         Update artifact with conversion
           └─ <50% → Document limitation
                     Update artifact with notes
  ↓
Finalize artifact with summary report
```

---

## Common Patterns

### UniProt Anchor (Proteins)
**In RDF:** PDB (20-30%), Reactome (15-25%), ChEMBL (10-20%), Ensembl (95%), GO (80%)  
**May need TogoID:** DrugBank, KEGG

### ChEMBL/PubChem (Compounds)
**In RDF:** UniProt, PubChem, ChEBI  
**May need TogoID:** DrugBank, KEGG

### Ensembl (Genes)
**In RDF:** UniProt, GO, Reactome  
**May need TogoID:** OMIM, HGNC

---

## Critical Warnings

❌ **Don't skip MIE file analysis** - Critical for understanding graph structure  
❌ **Don't assume TogoID is needed** - Most cross-refs are in RDF  
❌ **Don't skip RDF exploration** - Leads to unnecessary tools  
❌ **Don't make all cross-refs REQUIRED** - Use OPTIONAL patterns  
❌ **Don't create multiple queries** - Use ONE comprehensive query

✅ **Always get MIE file first**  
✅ **Create ONE artifact and update it progressively**  
✅ **Always explore anchor RDF** before converting  
✅ **Test TogoID coverage before using**  
✅ **Document your methodology**  
✅ **Compare SPARQL vs TogoID coverage**

---

## Coverage Expectations

| Quality | SPARQL Direct | +TogoID | Multi-DB Total |
|---------|---------------|---------|----------------|
| **Field-Leading** | 80-95% | +5-10% | 85-100% |
| **Publication** | 60-80% | +10-20% | 70-90% |
| **Proof-of-Concept** | 40-60% | +15-25% | 55-75% |

---

## Key Takeaway

> **"Start with MIE files to understand graph structure. Most cross-references already exist in anchor RDF. Explore first, convert only when necessary. Document everything in ONE progressively updated artifact for complete reproducibility."**

- 📚 MIE files reveal structure & examples
- ⚡ 2x faster analysis
- 🎯 Better coverage (+5-10%)
- 🔍 More transparent
- ✅ Higher reproducibility
- 📝 ONE artifact, progressively updated through all steps