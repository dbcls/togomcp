# Gene Ontology (GO) Exploration Report

## Database Overview
- **Purpose**: Provides a controlled vocabulary of terms for describing gene and gene product attributes across all organisms
- **Scope**: 48,165 total GO terms organized into three independent ontology domains
- **Key data types**: 
  - Biological processes (30,804 terms)
  - Molecular functions (12,793 terms)
  - Cellular components (4,568 terms)
  - External terms (11 terms)

## Schema Analysis (from MIE file)

### Main Properties
- **oboinowl:id**: GO term identifier (GO:NNNNNNN format)
- **rdfs:label**: Human-readable term name
- **obo:IAO_0000115**: Term definition (~100% coverage)
- **oboinowl:hasOBONamespace**: Domain classification (biological_process/molecular_function/cellular_component/external)
- **rdfs:subClassOf**: Hierarchical parent-child relationships
- **oboinowl:hasExactSynonym, hasRelatedSynonym, hasNarrowSynonym, hasBroadSynonym**: Comprehensive synonym system (~80% coverage)
- **oboinowl:hasDbXref**: External database cross-references (~52% coverage)
- **oboinowl:inSubset**: GO slim views for specific applications
- **owl:deprecated**: Obsolete term flag (~25% of terms)

### Important Relationships
- Hierarchical structure using rdfs:subClassOf forms directed acyclic graphs (DAGs)
- Terms can have multiple parents (complex inheritance)
- Cross-references to 20+ external databases (Wikipedia, Reactome, KEGG, MESH, EC, RHEA, SNOMEDCT, NCIt, NIF_Subcellular)
- Alternative IDs track merged term history

### Query Patterns Observed
1. **CRITICAL**: Always use FROM clause: `FROM <http://rdfportal.org/ontology/go>`
2. Use `bif:contains` for keyword search instead of REGEX (10-100x faster)
3. Use `STR()` for namespace comparisons to avoid datatype mismatch
4. Always use `DISTINCT` to deduplicate results (terms stored in multiple graphs)
5. Filter by GO_ prefix to exclude other ontology terms: `FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))`

## Search Queries Performed

### Query 1: Search for "autophagy"
**Tool**: OLS4:search
**Result**: Found GO:0006914 (autophagy) and related terms across multiple ontologies
- Main GO term: GO:0006914 "autophagy" in biological_process namespace
- Definition: "The cellular catabolic process in which cells digest cellular materials..."

### Query 2: Get autophagy descendants
**Tool**: OLS4:getDescendants for GO:0006914
**Result**: 25 descendant terms including:
- GO:0016236 (macroautophagy) - most common form
- GO:0016237 (microautophagy)
- GO:0061684 (chaperone-mediated autophagy)
- GO:0000423 (mitophagy) - mitochondrial autophagy
- GO:0061724 (lipophagy) - lipid droplet degradation
- GO:0035973 (aggrephagy) - protein aggregate degradation
- GO:0098792 (xenophagy) - pathogen degradation

### Query 3: Count terms by namespace
**Tool**: TogoMCP run_sparql
**Result**: 
- biological_process: 30,804 terms
- molecular_function: 12,793 terms  
- cellular_component: 4,568 terms
- (Matches MIE file statistics exactly)

### Query 4: Search DNA repair terms
**Tool**: TogoMCP run_sparql with keyword "DNA repair"
**Result**: Found multiple DNA repair-related terms:
- GO:0006281 "DNA repair" (main term)
- GO:0045739 "positive regulation of DNA repair"
- GO:0042275 "error-free postreplication DNA repair"
- GO:0006282 "regulation of DNA repair"
- GO:0043504 "mitochondrial DNA repair"

### Query 5: Get ancestors of DNA repair term
**Tool**: OLS4:getAncestors for GO:0006281
**Result**: 15 ancestor terms showing hierarchical path:
- GO:0006974 "DNA damage response"
- GO:0006259 "DNA metabolic process"
- GO:0033554 "cellular response to stress"
- GO:0090304 "nucleic acid metabolic process"
- GO:0043170 "macromolecule metabolic process"
- GO:0008152 "metabolic process"
- GO:0050896 "response to stimulus"
- GO:0008150 "biological_process" (root)

## SPARQL Queries Tested

```sparql
# Query 1: Count terms by namespace (verification)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?namespace (COUNT(DISTINCT ?go) as ?count)
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go oboinowl:hasOBONamespace ?namespace .
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
GROUP BY ?namespace
ORDER BY DESC(?count)
# Results: biological_process (30804), molecular_function (12793), cellular_component (4568)
```

```sparql
# Query 2: Find DNA repair terms with definitions
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT ?go ?label ?definition ?namespace
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go rdfs:label ?label .
  ?go obo:IAO_0000115 ?definition .
  ?go oboinowl:hasOBONamespace ?namespace .
  ?label bif:contains "'DNA repair'" .
  FILTER(STR(?namespace) = "biological_process")
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 5
# Results: Found 5 DNA repair-related terms with full definitions
```

```sparql
# Query 3: Example from MIE - Search kinase molecular functions
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
# Works well - would return protein kinase activity and related terms
```

## Interesting Findings

### Specific Entities for Questions
1. **GO:0006914 (autophagy)** - 25 descendant terms, well-structured hierarchy
2. **GO:0006281 (DNA repair)** - Complex multi-level hierarchy with 15 ancestors
3. **GO:0016236 (macroautophagy)** - Specific subtype with many child terms
4. **GO:0000423 (mitophagy)** - Selective autophagy of mitochondria
5. **GO:0004672 (protein kinase activity)** - Fundamental molecular function
6. **GO:0005634 (nucleus)** - Well-annotated cellular component with GO slim subsets

### Unique Properties
- **Four synonym types** provide comprehensive term matching
- **GO slim subsets** (inSubset property) enable organism-specific and application-specific views
- **~25% deprecated terms** with proper owl:deprecated flags and alternative IDs
- **Cross-references to 20+ databases** enable integrated knowledge access
- **bif:contains** uses Virtuoso's full-text index for fast searches

### Connections to Other Databases
- **Wikipedia**: General knowledge (extensive coverage)
- **Reactome**: Biochemical pathways
- **KEGG_REACTION**: Metabolic reactions
- **RHEA**: Enzyme reactions
- **EC**: Enzyme classification
- **MESH**: Medical subject headings
- **SNOMEDCT**: Clinical terminology
- **NCIt**: Cancer terminology
- **NIF_Subcellular**: Subcellular structures

### Specific, Verifiable Facts
1. GO has exactly 48,165 terms (30,804 biological_process + 12,793 molecular_function + 4,568 cellular_component + 11 external)
2. Autophagy (GO:0006914) has precisely 25 descendant terms
3. DNA repair (GO:0006281) has 15 ancestor terms in its hierarchical path
4. ~52% of terms have external cross-references
5. ~80% of terms have synonyms

## Question Opportunities by Category

### Precision
- "What is the GO identifier for the biological process 'mitophagy'?" (GO:0000423)
- "What is the exact definition of GO:0016236 (macroautophagy)?"
- "How many descendant terms does GO:0006914 (autophagy) have?" (25)
- "What GO term describes 'chaperone-mediated autophagy'?" (GO:0061684)

### Completeness
- "List all types of selective autophagy in the GO database" (13+ specific -phagy terms)
- "How many GO terms are in the biological_process namespace?" (30,804)
- "What are all the parent terms of GO:0006281 (DNA repair)?" (2 direct parents)
- "List all molecular function terms related to 'kinase activity'"

### Integration
- "What external databases does GO:0005634 (nucleus) cross-reference to?" (Wikipedia, NIF_Subcellular, GO slim)
- "Convert GO:0006914 to its Wikipedia entry"
- "What Reactome pathways are linked to autophagy-related GO terms?"
- "Find MeSH terms linked to DNA repair GO terms"

### Currency
- "What is the current count of deprecated GO terms?" (~25%)
- "What are the most recently added autophagy-related terms?"
- "How many GO terms are currently in the GO slim generic subset?"

### Specificity
- "What is the GO term for 'piecemeal microautophagy of the nucleus'?" (GO:0034727)
- "What distinguishes GO:0180045 (type 1 mitophagy) from GO:0061734 (type 2 mitophagy)?"
- "What is the GO term for xenophagy?" (GO:0098792 - degradation of intracellular pathogens)
- "What specialized forms of microautophagy exist?" (micropexophagy, micromitophagy, microlipophagy)

### Structured Query
- "Find all GO terms in the molecular_function namespace that contain 'kinase'"
- "Count how many terms exist for each GO namespace"
- "Find all biological process terms that have Wikipedia cross-references"
- "List GO terms with definitions containing both 'mitochondri*' AND 'transport'"

## Notes

### Limitations and Challenges
1. **FROM clause is CRITICAL** - Queries fail or timeout without it
2. **Duplicate results common** - Always use DISTINCT due to multiple graph storage
3. **Namespace comparison requires STR()** - Datatype mismatch issues otherwise
4. **Aggregation queries may timeout** - Use LIMIT appropriately for large counts
5. **Multiple ontologies in same endpoint** - Must filter by GO_ prefix to exclude PRO, CHEBI, etc.
6. **Deprecated terms (~25%)** - Need to check owl:deprecated flag for current terms

### Best Practices for Querying
1. Always include `FROM <http://rdfportal.org/ontology/go>` clause
2. Use `bif:contains` instead of REGEX for keyword searches (10-100x faster)
3. Use `FILTER(STR(?namespace) = "...")` for namespace filtering
4. Add `FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))` to get only GO terms
5. Always use `SELECT DISTINCT` to avoid duplicate rows
6. Use namespace filters early to reduce result set size
7. Boolean operators in bif:contains: Use single quotes and parentheses, e.g., `"('kinase' AND 'protein')"`

### Data Quality
- **Definitions**: ~100% coverage for non-obsolete terms
- **Synonyms**: ~80% coverage with four synonym types
- **Cross-references**: ~52% coverage to 20+ external databases
- **Hierarchical structure**: Well-formed DAGs with clear parent-child relationships
- **Regular updates**: Monthly release cycle
- **Provenance tracking**: created_by and creation_date properties available
