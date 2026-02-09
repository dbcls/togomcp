# MIE Prompt Revision Summary (Corrected)

## Critical Correction

**IMPORTANT:** The initial revision incorrectly suggested using `FILTER(CONTAINS())` as an alternative to `bif:contains`. This is WRONG.

- `bif:contains` = Virtuoso full-text search (indexed, fast)
- `FILTER(CONTAINS())` = Unindexed string scan (slow, worse than bif:contains)

**The correct structured alternative is using specific IRIs, not FILTER(CONTAINS()).**

---

## Key Changes from Original Prompt

### 1. Emphasized IRI-Based Queries (NEW)

**Core principle:** Use specific IRIs for concepts whenever possible.

**Examples:**
```sparql
# BEST: Specific IRI
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .  # Human

# GOOD: VALUES with multiple IRIs
VALUES ?go { 
  <http://purl.obolibrary.org/obo/GO_0016301>  # kinase activity
  <http://purl.obolibrary.org/obo/GO_0004672>  # protein kinase
}
?protein up:classifiedWith ?go .

# OK: Typed predicate
?molecule cco:organismName "Homo sapiens" .

# LAST RESORT: bif:contains (unstructured text only)
?comment bif:contains "'apoptosis'"

# NEVER: FILTER(CONTAINS()) - unindexed!
```

### 2. Added Workflow for Finding IRIs (NEW)

Shows how to use search APIs to discover IRIs, then use those IRIs in comprehensive queries:

```python
# 1. Exploratory: Find examples
results = search_uniprot_entity("kinase", limit=20)

# 2. Inspect: Extract GO term IRIs
run_sparql("uniprot", "SELECT ?go ?label WHERE { <protein> up:classifiedWith ?go ... }")
# Extract: GO_0016301, GO_0004672, etc.

# 3. Comprehensive: Query all proteins with those IRIs
run_sparql("uniprot", """
  VALUES ?go { <GO_0016301> <GO_0004672> }
  SELECT (COUNT(?protein) as ?count)
  WHERE { ?protein up:classifiedWith ?go }
""")
```

### 3. Explicit Warning Against FILTER(CONTAINS())

**Added prominent warning:**
- NEVER use FILTER(CONTAINS()) - it's always wrong
- It's unindexed and scans every value
- If you need text search, use bif:contains (indexed)
- But better: find specific IRIs and use those

### 4. Updated Query Requirements

**Changed from:**
- At least ONE structured query (vague)

**Changed to:**
- At least TWO queries using specific IRIs
- At least ONE query using typed predicates
- At most ONE with bif:contains (unstructured text only)
- **ZERO queries with FILTER(CONTAINS())**

### 5. Enhanced Anti-Patterns

**Added critical anti-pattern:**
```yaml
- title: "Using FILTER(CONTAINS()) Instead of Specific IRIs"
  wrong_sparql: |
    ?go rdfs:label ?label .
    FILTER(CONTAINS(LCASE(?label), "kinase"))  # Unindexed!
  correct_sparql: |
    VALUES ?go { <GO_0016301> <GO_0004672> }  # Specific IRIs
    ?protein up:classifiedWith ?go .
```

### 6. Decision Tree for Query Approach

Added flowchart showing:
1. Can you find specific IRI? → Use it
2. Controlled vocabulary exists? → Use typed predicate
3. Unstructured text only? → bif:contains
4. NEVER use FILTER(CONTAINS())

### 7. Database-Specific Guidance Updated

Each database type now emphasizes:
- Which IRIs to look for (taxonomy IRIs, GO terms, EC numbers)
- Which predicates are typed (cco:organismName, cco:standardType)
- When bif:contains is actually appropriate

---

## What "Structured Query" Really Means

### ✓ STRUCTURED (Good)

**1. Specific IRIs:**
```sparql
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .
?protein up:classifiedWith <http://purl.obolibrary.org/obo/GO_0016301> .
?reaction rhea:ec <http://purl.uniprot.org/enzyme/2.7.11.1> .
```

**2. VALUES with IRIs:**
```sparql
VALUES ?organism { 
  <http://purl.uniprot.org/taxonomy/9606>   # Human
  <http://purl.uniprot.org/taxonomy/10090>  # Mouse
}
?protein up:organism ?organism .
```

**3. Typed predicates:**
```sparql
?molecule cco:organismName "Homo sapiens" .
?activity cco:standardType "IC50" .
?protein up:reviewed 1 .
```

**4. Graph structure navigation:**
```sparql
?protein up:organism ?organism .
?organism rdfs:subClassOf+ ?phylum .
?phylum up:rank "phylum" .
```

### ✗ NOT STRUCTURED (Bad)

**1. FILTER(CONTAINS()) - Worst:**
```sparql
?go rdfs:label ?label .
FILTER(CONTAINS(LCASE(?label), "kinase"))  # Unindexed scan!
```

**2. bif:contains on structured fields - Bad:**
```sparql
?name bif:contains "'Homo sapiens'"  # Use up:organism IRI instead!
```

### ~ ACCEPTABLE (Only when necessary)

**bif:contains on unstructured text:**
```sparql
?annotation rdfs:comment ?comment .
?comment bif:contains "'apoptosis' AND 'caspase'"  # OK: free text
```

---

## Impact on Query Examples

### Before (Original Prompt):
Multiple queries using bif:contains for everything:
```sparql
?fullName bif:contains "'kinase'"
?name bif:contains "'human'"
?description bif:contains "'disease'"
```

### After (Revised Prompt):
Prioritize specific IRIs and typed predicates:

**Query 1: Specific organism IRI**
```sparql
SELECT ?protein ?name
WHERE {
  ?protein up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:recommendedName/up:fullName ?name .
}
```

**Query 2: Multiple GO term IRIs**
```sparql
VALUES ?go { <GO_0016301> <GO_0004672> }
SELECT ?protein ?goLabel
WHERE {
  ?protein up:classifiedWith ?go .
  ?go rdfs:label ?goLabel .
}
```

**Query 3: Typed predicate**
```sparql
SELECT ?molecule ?activity
WHERE {
  ?activity cco:hasMolecule ?molecule ;
            cco:standardType "IC50" ;
            cco:standardValue ?value .
}
```

**Query 4 (if needed): bif:contains on unstructured text**
```sparql
SELECT ?protein ?function
WHERE {
  ?protein up:annotation ?annot .
  ?annot a up:Function_Annotation ;
         rdfs:comment ?function .
  # OK because rdfs:comment is free text with no controlled vocabulary
  ?function bif:contains "'apoptosis' AND 'caspase'"
}
```

---

## Why This Matters

### Performance
- Specific IRIs: Fast (indexed lookups)
- Typed predicates: Fast (filtered by type)
- bif:contains: Moderate (text indexed)
- FILTER(CONTAINS()): **Terrible (unindexed scan)**

### Maintainability
- IRIs are stable identifiers
- String matching breaks when text changes
- Controlled vocabularies provide consistency

### Correctness
- IRIs are unambiguous
- String matching is error-prone (typos, variations)
- Typed predicates ensure data quality

### Query Intent
- Specific IRIs: "Give me proteins for human (taxon 9606)"
- FILTER(CONTAINS()): "Scan all labels for text containing 'human'"

---

## Migration Guide for Existing MIE Files

When revising existing MIE files:

1. **Identify queries using FILTER(CONTAINS())** → Replace with specific IRIs
2. **Identify queries using bif:contains on structured fields** → Replace with IRIs/predicates
3. **For each concept mentioned**:
   - Find its specific IRI (taxonomy, GO, EC, MeSH, etc.)
   - Replace text search with IRI-based query
4. **Keep bif:contains only for**:
   - Unstructured comments (rdfs:comment)
   - Descriptions (dcterms:description)
   - Free text annotations
5. **Add to architectural_notes**:
   - List key IRI patterns (organism: taxonomy:XXXXX, GO: obo:GO_XXXXXXX)
   - Document typed predicates (cco:organismName, cco:standardType)
   - Note when bif:contains is appropriate (which fields)

---

## Summary of Correct Approach

**Query Design Hierarchy (Best to Worst):**

1. **Specific IRIs** - Always use when available
2. **VALUES with IRIs** - For multiple known entities  
3. **Typed predicates** - For controlled vocabularies
4. **Graph navigation** - For hierarchical relationships
5. **bif:contains** - Only for unstructured text fields
6. **FILTER(CONTAINS())** - NEVER use this!

**Exploratory Workflow:**
1. Search APIs → Find examples
2. Inspect examples → Extract IRIs/values
3. Comprehensive SPARQL → Use IRIs/values
4. Never use search results directly in VALUES (circular reasoning)

**The key insight:** "Structured query" means using the RDF graph structure (IRIs, typed predicates, relationships), not just avoiding one particular string function.
