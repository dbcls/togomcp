# Critical Query Strategy Insight

## The Problem with FILTER(CONTAINS())

**User's Key Insight:** Simply replacing `bif:contains` with `FILTER(CONTAINS())` is no good. The latter is even worse than the former.

### Why FILTER(CONTAINS()) is Worse

| Feature | bif:contains | FILTER(CONTAINS()) |
|---------|--------------|-------------------|
| Indexing | ✓ Full-text indexed | ✗ Unindexed |
| Performance | Moderate (text search) | **Terrible (scans all values)** |
| Best for | Unstructured text | **Never use** |

### The Real Solution: Use Specific IRIs

The correct alternative to string searching is **not** another string function, but using the RDF graph structure:

```sparql
# WRONG: String search with FILTER(CONTAINS())
?go rdfs:label ?label .
FILTER(CONTAINS(LCASE(?label), "kinase"))  # Scans every GO term label!

# STILL BAD: String search with bif:contains
?label bif:contains "'kinase'"  # Better than FILTER, but still string search

# CORRECT: Use specific IRIs
VALUES ?go { 
  <http://purl.obolibrary.org/obo/GO_0016301>  # kinase activity
  <http://purl.obolibrary.org/obo/GO_0004672>  # protein kinase activity
}
?protein up:classifiedWith ?go .  # Direct IRI lookup
```

## Query Design Hierarchy

**1. Specific IRIs (Best)**
- Fast: Direct lookup
- Stable: IRIs don't change
- Unambiguous: Exact concept
```sparql
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .
```

**2. VALUES with Multiple IRIs**
- Fast: Lookup multiple specific concepts
- Clear: Explicitly enumerate what you want
```sparql
VALUES ?go { <GO_0016301> <GO_0004672> <GO_0004713> }
?protein up:classifiedWith ?go .
```

**3. Typed Predicates**
- Fast: Property is typed/filtered
- Controlled: Limited vocabulary
```sparql
?activity cco:standardType "IC50" .
```

**4. Graph Navigation**
- Moderate: Traverses relationships
- Flexible: Can follow hierarchies
```sparql
?organism rdfs:subClassOf+ ?phylum .
```

**5. bif:contains (Last Resort)**
- Moderate: Text indexed
- Use only for: Unstructured text (comments, descriptions)
```sparql
?comment bif:contains "'apoptosis'"  # OK: free text field
```

**6. FILTER(CONTAINS()) (Never)**
- **Terrible: Unindexed scan**
- **Always wrong: No legitimate use case**
```sparql
FILTER(CONTAINS(?label, "text"))  # ✗ NEVER DO THIS
```

## Workflow: From String Search to Structured Query

### Step 1: Exploratory Search (Find IRIs)
```python
# Use search API to find examples
results = search_uniprot_entity("kinase", limit=10)

# Inspect one result to find GO terms
run_sparql("uniprot", """
  SELECT ?go ?label
  WHERE {
    <http://purl.uniprot.org/uniprot/P12345> up:classifiedWith ?go .
    ?go rdfs:label ?label .
  }
""")
# Result: GO_0016301 "kinase activity"
#         GO_0004672 "protein kinase activity"
```

### Step 2: Comprehensive Query (Use IRIs)
```python
# Now query ALL proteins with those GO terms
run_sparql("uniprot", """
  VALUES ?go { 
    <http://purl.obolibrary.org/obo/GO_0016301>
    <http://purl.obolibrary.org/obo/GO_0004672>
  }
  SELECT (COUNT(DISTINCT ?protein) as ?count)
  WHERE {
    ?protein up:reviewed 1 ;
             up:classifiedWith ?go .
  }
""")
```

### Step 3: Documentation (MIE File)
```yaml
sparql_query_examples:
  - title: "Find Kinase Proteins by GO Classification"
    description: "Uses specific GO term IRIs for kinase activity."
    question: "Which proteins have kinase activity?"
    complexity: basic
    sparql: |
      PREFIX up: <http://purl.uniprot.org/core/>
      
      # Use specific GO term IRIs (found via exploratory search)
      VALUES ?go { 
        <http://purl.obolibrary.org/obo/GO_0016301>  # kinase activity
        <http://purl.obolibrary.org/obo/GO_0004672>  # protein kinase activity
      }
      
      SELECT ?protein ?name
      WHERE {
        ?protein up:reviewed 1 ;
                 up:classifiedWith ?go ;
                 up:recommendedName/up:fullName ?name .
      }
      LIMIT 30

architectural_notes:
  query_strategy:
    - "Exploratory: search_uniprot_entity() to find examples"
    - "Extract: Inspect examples to find GO term IRIs"
    - "Comprehensive: Use GO term IRIs in VALUES"
    - "Never: FILTER(CONTAINS()) on labels - unindexed!"
```

## When bif:contains is Actually Appropriate

**✓ Unstructured Text Fields:**
- rdfs:comment (free text descriptions)
- dcterms:description (narrative descriptions)
- Reaction equations (chemical formulas as strings)
- Function annotations (prose descriptions)

**✗ Structured Fields (Use IRIs instead):**
- Organism names → Use taxonomy IRIs
- GO terms → Use GO term IRIs
- EC numbers → Use EC classification IRIs
- Activity types → Use typed predicates (cco:standardType)
- Diseases → Use disease ontology IRIs

## Example: Correct vs Incorrect Approaches

### Finding Human Proteins

```sparql
# ✗ WORST: FILTER(CONTAINS())
?organism up:scientificName ?name .
FILTER(CONTAINS(?name, "Homo sapiens"))  # Scans all organism names!

# ✗ BAD: bif:contains
?name bif:contains "'Homo sapiens'"  # Better, but still string search

# ✓ CORRECT: Specific IRI
?protein up:organism <http://purl.uniprot.org/taxonomy/9606> .  # Direct lookup
```

### Finding Disease-Associated Proteins

```sparql
# ✗ WORST: FILTER(CONTAINS())
?disease rdfs:label ?label .
FILTER(CONTAINS(LCASE(?label), "alzheimer"))  # Scans all disease labels!

# ~ OK: bif:contains (if no disease IRI known)
?comment bif:contains "'Alzheimer'"  # On comment field, acceptable

# ✓ BETTER: Specific disease IRI
?protein up:annotation ?annot .
?annot a up:Disease_Annotation ;
       up:diseaseAssociation <disease_IRI> .  # If disease ontology integrated

# ✓ BEST: MeSH IRI via drug indication
GRAPH <chembl> {
  ?drug cco:hasMesh <http://identifiers.org/mesh/D000544> .  # Alzheimer Disease
}
```

### Finding Reactions by Substrate

```sparql
# ✗ WORST: FILTER(CONTAINS())
?reaction rhea:equation ?eq .
FILTER(CONTAINS(?eq, "ATP"))  # Scans all reaction equations!

# ✓ OK: bif:contains (reaction equations are unstructured text)
?reaction rhea:equation ?eq .
?eq bif:contains "'ATP'"  # Acceptable: equations are text strings

# ✓ BETTER: If substrate has IRI
?reaction rhea:hasParticipant <ChEBI_IRI_for_ATP> .  # Direct lookup
```

## Key Takeaway

**"Structured query" doesn't mean "avoid bif:contains and use FILTER(CONTAINS())"**

**It means: "Use IRIs, typed predicates, and graph relationships instead of string matching"**

- Good: `?protein up:organism <taxonomy:9606>`
- Bad: `?name bif:contains "'human'"`
- Terrible: `FILTER(CONTAINS(?name, "human"))`

The hierarchy is:
**IRIs > Typed Predicates > Graph Navigation > bif:contains > FILTER(CONTAINS()) = Never**
