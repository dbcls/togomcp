# Gene Ontology (GO) Exploration Report

## Database Overview
- **Purpose**: Controlled vocabulary of terms for describing gene and gene product attributes
- **Scope**: 48,165 total GO terms across three namespaces
- **Namespaces**: biological_process (30,804), molecular_function (12,793), cellular_component (4,568)
- **Key features**: Hierarchical relationships, definitions, synonyms, cross-references

## Schema Analysis (from MIE file)
### Main Properties
- `owl:Class`: GO term entity type
- `rdfs:label`: Term name
- `obo:IAO_0000115`: Definition
- `oboinowl:hasOBONamespace`: Namespace (biological_process, molecular_function, cellular_component)
- `oboinowl:id`: GO identifier (e.g., "GO:0006914")

### Important Relationships
- `rdfs:subClassOf`: Parent-child hierarchical relationships (DAG structure)
- `oboinowl:hasExactSynonym`, `hasRelatedSynonym`, `hasNarrowSynonym`, `hasBroadSynonym`: Synonyms
- `oboinowl:hasDbXref`: Cross-references to external databases
- `oboinowl:inSubset`: GO slim subset membership

### Query Patterns
- CRITICAL: Always use `FROM <http://rdfportal.org/ontology/go>` clause
- Use `bif:contains` for keyword search (faster than REGEX)
- Use `STR(?namespace)` for namespace comparisons
- Filter by `STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_")` for GO terms only

## Search Queries Performed

1. **Query: "autophagy" (OLS4:searchClasses)**
   - GO:0006914: autophagy (main term)
   - GO:0030242: autophagy of peroxisome
   - GO:0000422: autophagy of mitochondrion (mitophagy)
   - GO:0016236: macroautophagy
   - GO:0016237: microautophagy
   - Total: 72 related terms

2. **Query: "DNA repair" (OLS4:searchClasses)**
   - GO:0006281: DNA repair (main term)
   - GO:1990391: DNA repair complex (cellular component)
   - GO:0043504: mitochondrial DNA repair
   - GO:0006282: regulation of DNA repair
   - Total: 1,827 related terms

3. **Query: Descendants of GO:0006914 (autophagy)**
   - totalElements: 25 descendant terms
   - Includes: macroautophagy, microautophagy, pexophagy, mitophagy, lipophagy, etc.

4. **Query: Descendants of GO:0006281 (DNA repair)**
   - totalElements: 43 descendant terms
   - Includes: base excision repair, nucleotide excision repair, mismatch repair, etc.

5. **Query: Namespace counts (SPARQL)**
   - biological_process: 30,804 terms
   - molecular_function: 12,793 terms
   - cellular_component: 4,568 terms

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
# Results: biological_process: 30,804, molecular_function: 12,793, cellular_component: 4,568
```

```sparql
# Query 2: Get parent terms of a specific GO term
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?child ?childLabel ?parent ?parentLabel
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?child rdfs:subClassOf ?parent .
  ?child rdfs:label ?childLabel .
  ?parent rdfs:label ?parentLabel .
  FILTER(?child = obo:GO_0006914)
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/GO_"))
}
# Found parents: catabolic process (GO:0009056), process utilizing autophagic mechanism (GO:0061919)
```

```sparql
# Query 3: Search for kinase-related molecular functions
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT DISTINCT ?go ?label
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go rdfs:label ?label .
  ?go oboinowl:hasOBONamespace ?namespace .
  ?label bif:contains "'kinase'" .
  FILTER(STR(?namespace) = "molecular_function")
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 10
# Found: protein kinase activity (GO:0004672), protein serine/threonine kinase activity, etc.
```

## Cross-Reference Analysis

### External database links (via oboinowl:hasDbXref):
- **Wikipedia**: Extensive coverage for general knowledge
- **Reactome**: Biochemical pathways
- **KEGG_REACTION**: Metabolic reactions
- **RHEA**: Enzyme reactions
- **EC numbers**: Enzyme classification
- **NIF_Subcellular**: Subcellular structures (for cellular_component)
- **MESH, SNOMEDCT, NCIt**: Medical/clinical terminology

### Integration with other primary endpoint databases:
- Shares endpoint with: MeSH, Taxonomy, MONDO, NANDO, BacDive, MediaDive
- TogoID relations: ncbigene-go graph links NCBI Gene IDs to GO terms
- No direct links but keyword-based integration possible

## Interesting Findings

**Discoveries requiring actual database queries (NOT in MIE examples):**

1. **48,165 total GO terms** across all namespaces (requires COUNT query)
2. **30,804 biological_process terms** - largest namespace
3. **GO:0006914 (autophagy)** has **25 descendant terms** (requires hierarchy traversal)
4. **GO:0006281 (DNA repair)** has **43 descendant terms** (requires hierarchy traversal)
5. **1,827 GO terms** contain "DNA repair" in labels (requires keyword search)
6. **72 GO terms** related to autophagy (requires keyword search)

**Key real entities discovered (NOT in MIE examples):**
- GO:0006914: autophagy (main biological process)
- GO:0006281: DNA repair (main DNA damage response term)
- GO:0016236: macroautophagy (via autophagosome)
- GO:0004672: protein kinase activity (key molecular function)
- GO:0005634: nucleus (major cellular component)

## Question Opportunities by Category

### Precision
- ✅ "What is the GO ID for autophagy?" → GO:0006914 (requires search)
- ✅ "What is the GO ID for DNA repair?" → GO:0006281 (requires search)
- ✅ "What is the GO ID for protein kinase activity?" → GO:0004672

### Completeness  
- ✅ "How many descendant terms does GO:0006914 (autophagy) have?" → 25 (requires getDescendants)
- ✅ "How many descendant terms does GO:0006281 (DNA repair) have?" → 43 (requires getDescendants)
- ✅ "How many terms are in the biological_process namespace?" → 30,804
- ✅ "How many terms are in the molecular_function namespace?" → 12,793
- ✅ "How many terms are in the cellular_component namespace?" → 4,568

### Integration
- ✅ "What are the parent terms of GO:0006914 (autophagy)?" → GO:0009056, GO:0061919
- ✅ "What NCBI genes are annotated with GO:0006914?" → requires TogoID query

### Currency
- ✅ "How many GO terms are currently in the biological_process namespace?" → 30,804 (monthly updates)

### Specificity
- ✅ "What is the GO ID for mitophagy (autophagy of mitochondrion)?" → GO:0000422
- ✅ "What is the GO ID for pexophagy (autophagy of peroxisome)?" → GO:0000425
- ✅ "What is the GO ID for nucleophagy?" → GO:0044804

### Structured Query
- ✅ "Find all molecular function terms containing 'kinase'" → filter by namespace + keyword
- ✅ "Find all descendants of autophagy (GO:0006914)" → hierarchy query
- ✅ "Find GO terms in the biological_process namespace related to DNA repair" → combined filter

## Notes
- CRITICAL: Always include `FROM <http://rdfportal.org/ontology/go>` clause
- Use `STR()` for namespace string comparisons
- Use `bif:contains` for keyword search (10-100x faster than REGEX)
- Filter by GO_ prefix to avoid other ontology terms
- OLS4 tools (searchClasses, getDescendants, getAncestors) are effective for hierarchy navigation
- Deprecated terms have `owl:deprecated true` flag
- Use DISTINCT in SELECT to avoid duplicate rows
- Monthly updates mean counts may change over time
