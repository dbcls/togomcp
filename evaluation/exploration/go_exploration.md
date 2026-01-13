# Gene Ontology (GO) Exploration Report

## Database Overview
- **Purpose**: Controlled vocabulary for describing gene and gene product attributes
- **Scope**: Three ontology domains covering biological processes, molecular functions, and cellular components
- **Key entities**: 48,165 GO terms organized hierarchically
- **Data quality**: Standardized definitions, synonyms, and cross-references

## Schema Analysis (from MIE file)

### Main Properties
- `owl:Class`: GO term entity type
- `oboinowl:id`: GO identifier (e.g., "GO:0006914")
- `rdfs:label`: Term name
- `obo:IAO_0000115`: Definition
- `oboinowl:hasOBONamespace`: Domain (biological_process, molecular_function, cellular_component)
- `rdfs:subClassOf`: Hierarchical parent terms
- `oboinowl:hasExactSynonym`: Exact synonyms
- `oboinowl:hasDbXref`: External database cross-references
- `owl:deprecated`: Obsolescence flag

### Important Relationships
- Parent-child via rdfs:subClassOf (DAG structure)
- Cross-references to Wikipedia, Reactome, KEGG, MeSH
- Subset membership (GO slims)

### Query Patterns
- CRITICAL: Always use FROM <http://rdfportal.org/ontology/go>
- Use bif:contains for keyword search
- Use STR() for namespace comparisons
- Filter by GO_ prefix to exclude other ontologies

## Search Queries Performed

1. **Query**: OLS4:searchClasses(query="autophagy")
   - Results: Found GO:0006914 (autophagy) with definition
   - Also found related terms in APO, UPHENO, ChEBI ontologies

2. **Query**: OLS4:getDescendants(GO:0006914)
   - Results: 25 descendant terms including:
     - macroautophagy (GO:0016236)
     - microautophagy (GO:0016237)
     - mitophagy (GO:0000423)
     - xenophagy (GO:0098792)
     - reticulophagy (GO:0061709)

3. **Query**: OLS4:searchClasses(query="kinase")
   - Expected: Multiple kinase-related terms across namespaces

4. **Query**: OLS4:searchClasses(query="nucleus")
   - Expected: GO:0005634 and related cellular component terms

5. **Query**: Namespace distribution via SPARQL
   - Results: biological_process (30,804), molecular_function (12,793), cellular_component (4,568)

## SPARQL Queries Tested

```sparql
# Query 1: Count terms by namespace
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?namespace (COUNT(DISTINCT ?go) as ?count)
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go oboinowl:hasOBONamespace ?namespace .
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
GROUP BY ?namespace
ORDER BY DESC(?count)
# Results: biological_process (30,804), molecular_function (12,793), cellular_component (4,568)
```

```sparql
# Query 2: Search GO terms by keyword (from MIE examples)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?go ?label
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go rdfs:label ?label .
  ?label bif:contains "'apoptosis'" .
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 20
# Pattern verified - returns apoptosis-related GO terms
```

```sparql
# Query 3: Find kinase-related molecular functions (from MIE examples)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?go ?label ?definition ?namespace
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go rdfs:label ?label .
  ?go obo:IAO_0000115 ?definition .
  ?go oboinowl:hasOBONamespace ?namespace .
  ?label bif:contains "'kinase'" .
  FILTER(STR(?namespace) = "molecular_function")
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 10
# Pattern verified - returns kinase molecular function terms
```

## Interesting Findings

### Specific Entities for Questions
- **GO:0006914**: autophagy - 25 descendants (verified)
- **GO:0005634**: nucleus - key cellular component
- **GO:0004672**: protein kinase activity
- **GO:0016236**: macroautophagy
- **GO:0000423**: mitophagy

### Autophagy Descendants (25 terms)
- macroautophagy (GO:0016236)
- microautophagy (GO:0016237)
- chaperone-mediated autophagy (GO:0061684)
- mitophagy (GO:0000423)
- pexophagy (GO:0000425)
- xenophagy (GO:0098792)
- reticulophagy (GO:0061709)
- nucleophagy (GO:0044804)
- lipophagy (GO:0061724)
- ribophagy (GO:0034517)
- aggrephagy (GO:0035973)
- And more specialized terms...

### Term Distribution
- biological_process: 30,804 terms (64%)
- molecular_function: 12,793 terms (27%)
- cellular_component: 4,568 terms (9%)
- Total: 48,165 terms

### Unique Properties
- Rich synonym system (exact, related, narrow, broad)
- Hierarchical DAG structure
- GO slim subsets for organism-specific views
- External cross-references (Wikipedia, Reactome, KEGG, MeSH)

### Database Connections (via OLS4 tools)
- Can query across multiple ontologies (GO, ChEBI, MONDO, etc.)
- getDescendants/getAncestors for hierarchy navigation
- searchClasses for keyword discovery

## Question Opportunities by Category

### Precision
- What is the GO ID for autophagy? (GO:0006914)
- What is the GO ID for nucleus (cellular component)? (GO:0005634)
- What is the definition of GO:0004672?
- What namespace does GO:0006914 belong to? (biological_process)

### Completeness
- How many descendant terms does GO:0006914 (autophagy) have? (25)
- How many biological_process terms are in GO? (30,804)
- How many molecular_function terms are in GO? (12,793)
- List all child terms of macroautophagy

### Integration
- What Wikipedia article is linked to GO:0005634?
- What Reactome pathways are cross-referenced from autophagy terms?
- Find GO terms with MeSH cross-references

### Currency
- What new GO terms have been added recently?
- What terms were recently deprecated?

### Specificity
- What is the GO term for pexophagy? (GO:0000425)
- What is the GO term for xenophagy (pathogen autophagy)?
- Find GO terms related to rare metabolic processes

### Structured Query
- Find all biological_process terms containing "kinase"
- Find GO terms that are both in autophagy pathway AND have mitochondria
- Find molecular_function terms with enzyme activity definitions

## Notes
- **CRITICAL**: Always use FROM <http://rdfportal.org/ontology/go>
- Use bif:contains for text search (faster than REGEX)
- Use STR() for namespace comparisons
- Filter by GO_ prefix to exclude other ontology terms
- Use DISTINCT to remove duplicates from results
- OLS4 tools (getDescendants, getAncestors) are excellent for hierarchy queries
- ~25% of terms are deprecated - filter with owl:deprecated if needed
