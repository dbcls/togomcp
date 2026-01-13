# MeSH (Medical Subject Headings) Exploration Report

## Database Overview
- **Purpose**: NLM controlled vocabulary thesaurus for biomedical literature indexing
- **Scope**: Subject headings, qualifiers, and supplementary records for PubMed indexing
- **Key entities**: 30K+ descriptors, 869K terms, 466K concepts, 250K chemicals
- **Data quality**: Expert-curated hierarchical medical terminology

## Schema Analysis (from MIE file)

### Main Properties
- `meshv:TopicalDescriptor`: Main subject headings
- `meshv:identifier`: MeSH descriptor ID (e.g., "D003920")
- `rdfs:label`: Preferred name
- `meshv:annotation`: Scope notes and indexing guidance
- `meshv:treeNumber`: Hierarchical classification codes
- `meshv:broaderDescriptor`: Parent descriptors
- `meshv:allowableQualifier`: Valid qualifier combinations
- `meshv:SCR_Chemical`: Supplementary chemical records

### Important Relationships
- `meshv:broaderDescriptor`: Parent-child hierarchy (NOT meshv:broader)
- `meshv:treeNumber`: Alphanumeric category codes (A-Z)
- `meshv:preferredConcept → meshv:preferredTerm`: Concept-term structure

### Query Patterns
- **CRITICAL**: Use meshv:broaderDescriptor (NOT meshv:broader)
- **CRITICAL**: Use meshv:annotation (NOT meshv:scopeNote)
- Always use FROM <http://id.nlm.nih.gov/mesh>
- Use bif:contains with option (score ?sc) for relevance ranking

## Search Queries Performed

1. **Query**: search_mesh_entity("diabetes mellitus")
   - Results: Found multiple diabetes-related terms (T840800, T826714, etc.)
   - Found related conditions and complications

2. **Query**: search_mesh_entity("Erdheim-Chester disease")
   - Results: T459455 (Erdheim-Chester Disease)
   - Rare histiocytic disorder - good for specificity questions

3. **Query**: search_mesh_entity("Niemann-Pick disease")
   - Results: T028436 (main term), T000998961 (Type C), etc.
   - Lysosomal storage disorder with multiple subtypes

4. **Query**: SPARQL for diabetes descriptors with identifiers
   - Results: D003920 (Diabetes Mellitus), D003924 (Type 2), etc.

5. **Additional searches**: Verified hierarchical structure and annotations

## SPARQL Queries Tested

```sparql
# Query 1: Search diabetes-related descriptors with identifiers
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT ?descriptor ?label ?identifier
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    rdfs:label ?label ;
    meshv:identifier ?identifier .
  ?label bif:contains "'diabetes'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: D003920 (Diabetes Mellitus), D003924 (Type 2), D003922 (Type 1), etc.
```

```sparql
# Query 2: Get hierarchical info for a descriptor (from MIE examples)
PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?label ?annotation ?treeNumber ?broaderLabel
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  mesh:D003920 rdfs:label ?label .
  OPTIONAL { mesh:D003920 meshv:annotation ?annotation }
  OPTIONAL { 
    mesh:D003920 meshv:treeNumber ?tree .
    ?tree rdfs:label ?treeNumber
  }
  OPTIONAL {
    mesh:D003920 meshv:broaderDescriptor ?broader .
    ?broader rdfs:label ?broaderLabel
  }
}
# Pattern verified - retrieves hierarchical information
```

```sparql
# Query 3: Find chemical records (from MIE examples)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT ?chemical ?label ?registryNumber
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?chemical a meshv:SCR_Chemical ;
    rdfs:label ?label .
  OPTIONAL { ?chemical meshv:registryNumber ?registryNumber }
  ?label bif:contains "'insulin'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
# Pattern verified - returns chemical records with CAS numbers
```

## Interesting Findings

### Specific Entities for Questions
- **D003920**: Diabetes Mellitus - main descriptor
- **D003924**: Diabetes Mellitus, Type 2 - specific type
- **T459455**: Erdheim-Chester Disease - rare histiocytic disorder
- **T028436**: Niemann-Pick Disease - lysosomal storage disorder
- **D002318**: Cardiovascular Diseases - major category

### MeSH Identifier Patterns
- D-prefix: Descriptors (subject headings)
- T-prefix: Terms
- C-prefix: Supplementary chemical records
- Q-prefix: Qualifiers

### Tree Number Categories
- A: Anatomy
- B: Organisms
- C: Diseases
- D: Chemicals and Drugs
- E: Analytical, Diagnostic and Therapeutic Techniques
- F: Psychiatry and Psychology
- G: Phenomena and Processes
- And more...

### Unique Properties
- Allowable qualifiers constrain valid indexing combinations
- Annotations provide indexing guidance
- Tree numbers enable hierarchical navigation
- CAS registry numbers for chemicals

### Database Connections
- **OMIM**: 12.5K references (genetic disorders)
- **ChEBI**: 2.5K references (chemicals)
- **FDA SRS/UNII**: 22.6K references (drugs)
- **SNOMED CT**: 800+ references (clinical terms)

### Key Statistics
- 30,248 topical descriptors
- 250,445 chemical records
- 869,536 terms
- ~40% of descriptors have annotations
- ~95% have tree numbers

## Question Opportunities by Category

### Precision
- What is the MeSH descriptor ID for Diabetes Mellitus? (D003920)
- What is the MeSH descriptor ID for Type 2 Diabetes? (D003924)
- What is the MeSH term ID for Erdheim-Chester Disease? (T459455)
- What is the MeSH ID for Niemann-Pick Disease? (T028436)

### Completeness
- How many topical descriptors are in MeSH? (30,248)
- How many chemical records contain "insulin"?
- List all child descriptors of Diabetes Mellitus
- How many MeSH terms are in the C (Diseases) category?

### Integration
- What OMIM entries are cross-referenced from a specific MeSH term?
- What ChEBI ID corresponds to a MeSH chemical record?
- Link MeSH disease term to FDA drug records

### Currency
- What is the current MeSH version? (2024)
- What new descriptors were added recently?

### Specificity
- What is the MeSH ID for Erdheim-Chester Disease (rare disorder)?
- Find MeSH terms for rare metabolic disorders
- What is the MeSH term for a specific histiocytosis?

### Structured Query
- Find diseases with both "diabetes" AND specific organ involvement
- Find chemical records with CAS registry numbers
- Find descriptors with specific tree number prefixes (C18 for metabolic)

## Notes
- **CRITICAL**: Use meshv:broaderDescriptor (NOT meshv:broader)
- **CRITICAL**: Use meshv:annotation (NOT meshv:scopeNote)
- Use bif:contains with option (score ?sc) for relevance ranking
- Always use FROM <http://id.nlm.nih.gov/mesh>
- Only ~40% of descriptors have annotations - use OPTIONAL
- D-prefix = Descriptors, T-prefix = Terms, C-prefix = Chemicals
