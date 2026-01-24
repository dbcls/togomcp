# MeSH (Medical Subject Headings) Exploration Report

## Database Overview
- **Purpose**: National Library of Medicine's controlled vocabulary thesaurus for biomedical literature indexing
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Key Features**: Hierarchical subject headings, qualifiers (subheadings), chemical records, tree number classification
- **Data Version**: 2024

## Schema Analysis (from MIE file)
### Main Entities
- **TopicalDescriptor**: Main subject headings for indexing (~30K)
- **Qualifier**: Subheadings for refining descriptors (84 total)
- **SCR_Chemical**: Supplementary Chemical Records (~250K)
- **Term**: Individual terminology entries (~870K)
- **Concept**: Concept groupings (~467K)
- **TreeNumber**: Hierarchical classification codes

### Important Properties
- `meshv:identifier`: Descriptor ID (D######) or Qualifier ID (Q######)
- `meshv:broaderDescriptor`: Parent descriptor in hierarchy (NOT meshv:broader!)
- `meshv:annotation`: Scope notes and indexing guidance (NOT meshv:scopeNote!)
- `meshv:treeNumber`: Hierarchical classification codes
- `meshv:allowableQualifier`: Permitted subheadings for a descriptor
- `meshv:registryNumber`: CAS registry number for chemicals

### Query Patterns
- **CRITICAL**: Use `bif:contains` for full-text search with relevance scoring
- **CRITICAL**: Always use `FROM <http://id.nlm.nih.gov/mesh>` clause
- Use `meshv:broaderDescriptor+` for transitive hierarchy navigation
- Tree numbers use A-Z categories with numeric subcategories

## Search Queries Performed

### 1. Parkinson Disease search
```
Query: "Parkinson"
Results: 
- D010300: Parkinson Disease
- D010301: Parkinson Disease, Postencephalitic
- D010302: Parkinson Disease, Secondary
- D014927: Wolff-Parkinson-White Syndrome
- D000070579: Parkinson Disease Associated Proteins
```

### 2. Rare disease search - Erdheim-Chester
```
Query: "Erdheim-Chester"
Results: D031249 - Erdheim-Chester Disease (rare histiocytic disorder)
```

### 3. Rare disease search - Fabry
```
Query: "Fabry"
Results: D000795 - Fabry Disease (lysosomal storage disorder)
```

### 4. Neurodegenerative disease searches
```
Query: "Huntington"
Results: D006816 - Huntington Disease

Query: "Alzheimer"
Results: 
- D000544: Alzheimer Disease
- D023582: Alzheimer Vaccines
```

### 5. Drug searches
```
Query: "Metformin" (diabetes drug)
Results:
- D008687: Metformin
- D000068899: Sitagliptin Phosphate, Metformin Hydrochloride Drug Combination

Query: "Insulin"
Results: 20+ entries including:
- D007328: Insulin
- D000069036: Insulin Glargine
- D061267: Insulin Aspart
- D007333: Insulin Resistance
```

### 6. Modern biomedical technology search
```
Query: "CRISPR"
Results:
- D064113: CRISPR-Cas Systems
- D000076987: CRISPR-Associated Protein 9
- D064130: CRISPR-Associated Proteins
- D000094704: RNA, Guide, CRISPR-Cas Systems
```

## SPARQL Queries Tested

### Query 1: Count total topical descriptors
```sparql
SELECT (COUNT(DISTINCT ?descriptor) as ?total)
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor .
}
# Results: 30,248 topical descriptors
```

### Query 2: Count supplementary chemical records
```sparql
SELECT (COUNT(DISTINCT ?chemical) as ?total)
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?chemical a meshv:SCR_Chemical .
}
# Results: 250,445 chemical records
```

### Query 3: Count descriptors by tree category
```sparql
SELECT ?category (COUNT(DISTINCT ?descriptor) as ?count)
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    meshv:treeNumber ?tree .
  ?tree rdfs:label ?treeLabel .
  BIND(SUBSTR(?treeLabel, 1, 1) as ?category)
}
GROUP BY ?category
ORDER BY DESC(?count)
# Results:
# D (Chemicals/Drugs): 10,541 descriptors
# C (Diseases): 5,032 descriptors
# B (Organisms): 3,964 descriptors
# E (Analytical/Diagnostic): 3,102 descriptors
# G (Phenomena/Processes): 2,430 descriptors
# N (Health Care): 2,002 descriptors
# A (Anatomy): 1,904 descriptors
```

### Query 4: Get parent descriptors (Alzheimer Disease hierarchy)
```sparql
SELECT ?parent ?parentLabel
WHERE {
  mesh:D000544 meshv:broaderDescriptor+ ?parent .
  ?parent rdfs:label ?parentLabel .
}
# Results: Alzheimer Disease hierarchy includes:
# - Dementia
# - Tauopathies
# - Neurodegenerative Diseases
# - Brain Diseases
# - Central Nervous System Diseases
# - Nervous System Diseases
# - Neurocognitive Disorders
# - Mental Disorders
```

### Query 5: Get allowable qualifiers for Alzheimer Disease
```sparql
SELECT ?qualifier ?qualifierLabel
WHERE {
  mesh:D000544 meshv:allowableQualifier ?qualifier .
  ?qualifier rdfs:label ?qualifierLabel .
}
# Results: 30+ qualifiers including:
# - etiology
# - drug therapy
# - genetics
# - pathology
# - diagnosis
# - epidemiology
```

### Query 6: Count total qualifiers
```sparql
SELECT (COUNT(DISTINCT ?qualifier) as ?total)
WHERE {
  ?qualifier a meshv:Qualifier .
}
# Results: 84 qualifiers total
```

## Cross-Reference Analysis

### Entity Counts (unique entities with mappings via meshv:thesaurusID)
Based on MIE documentation:
- Total cross-references: ~916K
- FDA SRS: 22.6K entities
- FDA UNII: 22.6K entities
- OMIM: 12.5K entities
- INN: 8.8K entities
- GHR: 3.8K entities
- ChEBI: 2.5K entities
- SNOMED CT: 800+ entities
- FMA: 1.1K entities

### Integration with MONDO
- ~28% of MONDO diseases have MeSH cross-references via oboInOwl:hasDbXref
- Cross-database queries with MONDO: 2-3 seconds

## Interesting Findings

**Focus on discoveries requiring actual database queries:**

1. **Tree category distribution**: Chemicals/Drugs (D) is the largest category with 10,541 descriptors, followed by Diseases (C) with 5,032 descriptors

2. **Disease hierarchy depth**: Alzheimer Disease has 8+ parent categories including Dementia, Tauopathies, Neurodegenerative Diseases, Brain Diseases

3. **Qualifier richness**: 84 qualifiers available for refining descriptors. Alzheimer Disease alone can use 30+ qualifiers

4. **Modern terminology coverage**: CRISPR-related terms are well-represented (4 main descriptors)

5. **Rare disease coverage**: Both Erdheim-Chester Disease (D031249) and Fabry Disease (D000795) have dedicated descriptors

6. **Drug organization**: Metformin (D008687) and insulin variants are systematically organized with related compounds

## Question Opportunities by Category

### Precision
- "What is the MeSH descriptor ID for Alzheimer Disease?" → D000544
- "What is the MeSH descriptor ID for Parkinson Disease?" → D010300
- "What is the MeSH descriptor ID for CRISPR-Associated Protein 9?" → D000076987
- "What is the MeSH descriptor ID for Fabry Disease?" → D000795
- "What is the MeSH descriptor ID for Erdheim-Chester Disease?" → D031249
- "What is the MeSH descriptor ID for Multiple Sclerosis?" → D009103
- "What is the MeSH descriptor ID for Metformin?" → D008687
- "What is the MeSH qualifier ID for 'drug therapy'?" → Q000188

### Completeness
- "How many topical descriptors are in MeSH?" → 30,248
- "How many supplementary chemical records are in MeSH?" → 250,445
- "How many qualifiers are in MeSH?" → 84
- "How many disease-related descriptors (tree category C) are in MeSH?" → 5,032
- "How many drug/chemical descriptors (tree category D) are in MeSH?" → 10,541

### Integration
- "What OMIM cross-references are in MeSH?" → 12.5K entities
- "What ChEBI cross-references are in MeSH?" → 2.5K entities
- "Which MONDO diseases link to MeSH descriptors?" → ~28% coverage

### Currency
- "What is the current version year of MeSH?" → 2024
- "What new CRISPR-related terms are in MeSH?" → 4 descriptors covering systems, proteins, guide RNA

### Specificity
- "What is the MeSH ID for the rare histiocytic disorder Erdheim-Chester Disease?" → D031249
- "What is the MeSH ID for the lysosomal storage disorder Fabry Disease?" → D000795
- "What qualifiers can be used with Alzheimer Disease indexing?" → 30+ qualifiers

### Structured Query
- "Find all parent categories of Alzheimer Disease in MeSH" → 8+ parents including Dementia, Tauopathies
- "Find all insulin-related descriptors in MeSH" → 20+ entries
- "Find all CRISPR-related descriptors in MeSH" → 4 entries
- "How many descriptors are in each major MeSH tree category?" → D:10541, C:5032, B:3964...

## Notes
- **Performance**: Use `bif:contains` with `option (score ?sc)` for relevance-ranked searches
- **Property names**: Use `meshv:broaderDescriptor` (not `meshv:broader`) and `meshv:annotation` (not `meshv:scopeNote`)
- **Hierarchy**: Tree numbers provide alphanumeric codes (A-Z categories)
- **Multi-language**: Many descriptors have labels in multiple languages
- **Shared endpoint**: Part of "primary" endpoint with go, taxonomy, mondo, nando, bacdive, mediadive
- **Search tool issue**: `search_mesh_entity` tool returned empty errors; SPARQL queries work fine
