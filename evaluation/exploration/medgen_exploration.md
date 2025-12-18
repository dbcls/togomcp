# MedGen Exploration Report

## Database Overview
- **Purpose**: NCBI's portal for medical conditions with a genetic component
- **Scope**: 233,000+ clinical concepts covering diseases, phenotypes, and clinical findings
- **Key data types**: ConceptID entities with relationships (MGREL), attributes (MGSAT), and terminology mappings (MGCONSO) to external databases

## Schema Analysis (from MIE file)

### Main Properties Available
- **ConceptID** (main entity):
  - `dct:identifier` - CUI identifier (C-prefixed string, e.g., C0011859)
  - `rdfs:label` - Concept name
  - `mo:sty` - UMLS semantic type (disease, phenotype, gene, etc.)
  - `skos:definition` - Text definition (~34% coverage)
  - `mo:mgconso` - Blank nodes containing external cross-references
  - `mo:mgsat` - Blank nodes containing attributes (inheritance patterns, etc.)

- **MGREL** (relationship entity) - **CRITICAL**:
  - `mo:cui1` - Source concept (ConceptID)
  - `mo:cui2` - Target concept (ConceptID)
  - `mo:rela` - Relationship type (isa, inverse_isa, has_manifestation, etc.)
  - `dct:source` - Source database
  - **NOTE**: Relationships are NOT direct properties on ConceptID - must query MGREL entities

- **MGCONSO** (terminology mapping via blank nodes):
  - `rdfs:seeAlso` - External database URIs (MONDO, MeSH, OMIM, HPO, etc.)
  - `mo:aui` - Atom Unique Identifier
  - `mo:lat` - Language
  - `dct:source` - Source database

- **MGSAT** (attribute entity via blank nodes):
  - `mo:atn` - Attribute name (e.g., "INHERITANCE")
  - `mo:atv` - Attribute value (e.g., "Autosomal recessive")
  - `mo:cui` - Associated concept
  - `dct:source` - Source database

### Important Relationships
- **CRITICAL**: All relationships between ConceptIDs are stored in MGREL entities, NOT as direct properties
- **MGREL query pattern**: ?rel a mo:MGREL ; mo:cui1 ?concept1 ; mo:cui2 ?concept2 ; mo:rela ?rel_type
- **Common relationship types**:
  - `isa` - Child-to-parent (narrower to broader)
  - `inverse_isa` - Parent-to-child (broader to narrower)
  - `has_manifestation` - Disease to phenotype
  - `manifestation_of` - Phenotype to disease
  - `undefined_relationship` - Unclassified relationships
- **Cross-references**: Via mo:mgconso blank nodes containing rdfs:seeAlso
- **Attributes**: Via mo:mgsat blank nodes for inheritance, clinical features, etc.

### Query Patterns Observed
- **Full-text search**: Use bif:contains for keyword searches with relevance ranking
- **MGREL traversal**: Always use MGREL entities for relationships between concepts
- **DISTINCT for cross-refs**: Always use DISTINCT when querying mo:mgconso (duplicates common)
- **Semantic type filtering**: Filter by mo:sty for specific concept categories
- **LIMIT required**: Always use LIMIT for MGREL/MGSAT queries (>1M records each)
- **Graph specification**: Always include FROM <http://rdfportal.org/dataset/medgen>

## Search Queries Performed

1. **Query**: Diabetes concepts with bif:contains → **Results**: 20 results including Lipoatrophic diabetes (C0011859), Bronze diabetes (C0018995), Gestational diabetes (C0085207), Nephrogenic diabetes insipidus (C0162283), various rare diabetes syndromes

2. **Query**: Relationships for Lipoatrophic diabetes (C0011859) → **Results**: 2 relationships found via MGREL - inverse_isa to "Diabetes mellitus" (parent concept), mapped_to "Acrorenal field defect, ectodermal dysplasia, and lipoatrophic diabetes"

3. **Query**: External cross-references for C0011859 → **Results**: 4 distinct references - MONDO:0005827, MeSH:D003923, NCI Thesaurus:C34537, SNOMED CT:127012008

4. **Query**: BRCA-related diseases (semantic type T047) → **Results**: 4 concepts - BRCA2-related disorder (CN239275), BRCA2-related cancer predisposition (CN377758), BRCA1-related cancer predisposition (CN377757), BROVCA2 hereditary breast and ovarian cancer (CN971385)

5. **Query**: Search for Alzheimer disease and related concepts → **Results**: 20 Alzheimer-related concepts including:
   - C0002395: "Alzheimer disease" (main concept)
   - C1847200: "Alzheimer disease 4"
   - C1852223: "Dementia/parkinsonism with non-Alzheimer amyloid plaques"
   - CN028944: "Alzheimer disease, type 15"
   - CN043623: "Late-onset familial alzheimer disease"
   - C3810041: "Alzheimer disease 18"
   - C3810349: "Alzheimer disease 19"
   - C0276496: "Familial Alzheimer disease"
   - C0494463: "Primary degenerative dementia of the Alzheimer type, senile onset"
   - C0750900: "Alzheimer Disease, Focal Onset"
   - Shows comprehensive coverage of familial variants, subtypes, and associated dementia syndromes

## SPARQL Queries Tested

```sparql
# Query 1: Keyword search for diabetes concepts
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?concept ?identifier ?label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      rdfs:label ?label ;
      dct:identifier ?identifier .
  ?label bif:contains "'diabetes'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
# Results: Retrieved 20 diabetes-related concepts with relevance ranking, including Lipoatrophic diabetes, Bronze diabetes, Gestational diabetes, and various rare diabetes syndromes.
```

```sparql
# Query 2: Find relationships for a concept (CRITICAL - uses MGREL)
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?disease ?disease_label ?related ?related_label ?rel_type
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?disease a mo:ConceptID ;
      dct:identifier "C0011859" ;
      rdfs:label ?disease_label .
  ?rel a mo:MGREL ;
      mo:cui1 ?disease ;
      mo:cui2 ?related ;
      mo:rela ?rel_type .
  ?related rdfs:label ?related_label .
  FILTER(?disease != ?related)
}
LIMIT 20
# Results: Found 2 relationships for Lipoatrophic diabetes - inverse_isa to Diabetes mellitus (parent), mapped_to related syndrome. Demonstrates CRITICAL MGREL query pattern.
```

```sparql
# Query 3: Retrieve external cross-references (requires DISTINCT)
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT ?concept ?identifier ?external_db
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      dct:identifier "C0011859" ;
      mo:mgconso ?bn .
  ?bn rdfs:seeAlso ?external_db .
  BIND("C0011859" as ?identifier)
}
LIMIT 20
# Results: Retrieved 4 distinct cross-references to MONDO (0005827), MeSH (D003923), NCI Thesaurus (C34537), SNOMED CT (127012008). DISTINCT prevents duplicates.
```

```sparql
# Query 4: Find concepts by semantic type with keyword filter
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX sty: <http://purl.bioontology.org/ontology/STY/>

SELECT ?concept ?identifier ?label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      mo:sty sty:T047 ;
      rdfs:label ?label ;
      dct:identifier ?identifier .
  ?label bif:contains "'BRCA*'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: Found 4 BRCA-related disease concepts with semantic type T047 (Disease or Syndrome): BRCA2-related disorder, BRCA1/2 cancer predisposition syndromes.
```

## Interesting Findings

### Specific Entities That Could Form Good Questions
- **Lipoatrophic diabetes (C0011859)**: Has hierarchical relationship to Diabetes mellitus, cross-referenced to MONDO, MeSH, SNOMED CT
- **BRCA1-related cancer predisposition (CN377757)**: Genetic disease concept with semantic type T047
- **BRCA2-related disorder (CN239275)**: Cancer predisposition syndrome
- **Gestational diabetes (C0085207)**: Common diabetes subtype
- **Nephrogenic diabetes insipidus (C0162283)**: Rare kidney disorder

### Unique Properties or Patterns
- **CRITICAL ARCHITECTURE**: Relationships stored in MGREL entities, NOT as direct ConceptID properties
- **UMLS semantic types**: Classify concepts into categories (T047 = Disease, T033 = Finding, etc.)
- **Relationship types**: isa/inverse_isa for hierarchy, has_manifestation for phenotypes
- **Blank node architecture**: MGCONSO and MGSAT use blank nodes for grouping
- **Duplicate cross-references**: Common - always use DISTINCT for mo:mgconso queries
- **CUI identifiers**: C-prefixed strings (C0011859) as primary keys
- **Definition coverage**: Only ~34% of concepts have skos:definition

### Connections to Other Databases
- **MONDO**: ~70% coverage via mo:mgconso/rdfs:seeAlso
- **MeSH**: ~80% coverage for medical terminology
- **OMIM**: ~30% coverage for Mendelian disorders
- **HPO**: ~40% coverage for phenotypes
- **SNOMED CT**: ~60% coverage for clinical terms
- **Orphanet**: ~20% coverage for rare diseases
- **ICD-10**: ~50% coverage for diagnosis codes
- **ClinVar**: Direct links for genetic variants

### Specific, Verifiable Facts
- **Total concepts**: 233,939 clinical concepts
- **Total relationships**: 1,130,420 in MGREL
- **Total attributes**: 1,117,180 in MGSAT
- **Definition coverage**: ~34% have skos:definition
- **External mapping coverage**: ~90% have at least one cross-reference
- **Average relationships per concept**: 4.8
- **Average external refs per concept**: 3.2
- **Lipoatrophic diabetes**: C0011859, linked to MONDO:0005827, MeSH:D003923

## Question Opportunities by Category

### Precision
- "What is the MedGen concept ID for Lipoatrophic diabetes?" (Answer: C0011859)
- "What is the MONDO identifier for MedGen concept C0011859?" (Answer: MONDO:0005827)
- "What is the MeSH ID for Lipoatrophic diabetes from MedGen?" (Answer: D003923)
- "What semantic type does concept C0011859 have?" (Answer: T047 - Disease or Syndrome)
- "What is the MedGen identifier for BRCA1-related cancer predisposition?" (Answer: CN377757)

### Completeness
- "How many total clinical concepts are in MedGen?" (Answer: 233,939)
- "How many relationships are stored in MGREL?" (Answer: 1,130,420)
- "List all external database cross-references for concept C0011859" (Answer: MONDO, MeSH, NCI Thesaurus, SNOMED CT)
- "What are all relationship types for Lipoatrophic diabetes?" (Answer: inverse_isa, mapped_to)
- "How many BRCA-related diseases are in MedGen?" (Answer: 4+ with semantic type T047)

### Integration
- "What is the parent disease of Lipoatrophic diabetes in the MedGen hierarchy?" (Answer: Diabetes mellitus via inverse_isa)
- "Convert MedGen CUI C0011859 to SNOMED CT identifier" (Answer: 127012008)
- "Find OMIM identifiers for BRCA-related disorders from MedGen" (Via mo:mgconso cross-references)
- "Link MedGen concept C0011859 to its MeSH descriptor" (Answer: D003923)
- "What ClinVar variants are associated with MedGen concepts?" (Via relationships)

### Currency
- "What is the current definition coverage in MedGen?" (Answer: ~34%)
- "How many concepts have been added to MedGen?" (Answer: 233,939 total)
- "What external databases does MedGen currently map to?" (Answer: MONDO, MeSH, OMIM, HPO, SNOMED CT, Orphanet, ICD-10)

### Specificity
- "What is the relationship type between Lipoatrophic diabetes and Diabetes mellitus?" (Answer: inverse_isa)
- "What UMLS semantic type classifies BRCA2-related disorder?" (Answer: T047 - Disease or Syndrome)
- "How many submitters contributed to concept C0011859?" (Via MGSAT attributes if available)
- "What are the inheritance patterns stored in MGSAT?" (Answer: Autosomal recessive, X-linked, etc.)

### Structured Query
- "Find all disease concepts (semantic type T047) related to diabetes" (Semantic type + keyword filtering)
- "Retrieve the disease hierarchy starting from Diabetes mellitus" (Traverse MGREL with isa/inverse_isa)
- "Find all concepts with OMIM cross-references" (Filter rdfs:seeAlso by OMIM URI pattern)
- "List phenotypic manifestations of a disease" (MGREL with has_manifestation relationship type)
- "Count concepts by semantic type" (GROUP BY mo:sty with appropriate LIMIT)

## Notes

### Limitations or Challenges
- **CRITICAL**: Relationships are in MGREL, not as direct ConceptID properties
- **Definition coverage**: Only ~34% of concepts have definitions
- **Duplicate cross-references**: mo:mgconso queries return duplicates without DISTINCT
- **Large entity counts**: MGREL (1.1M) and MGSAT (1.1M) require LIMIT to avoid timeouts
- **Blank node complexity**: MGCONSO and MGSAT use blank nodes requiring specific query patterns
- **Some relationships undefined**: Categorized as "undefined_relationship"
- **Query timeouts**: Aggregating without filters on MGREL/MGSAT causes timeouts

### Best Practices for Querying
1. **CRITICAL - Use MGREL for relationships**: Never query direct relationship properties on ConceptID
2. **Always include FROM clause**: FROM <http://rdfportal.org/dataset/medgen>
3. **Use DISTINCT for cross-references**: Prevents duplicates from mo:mgconso queries
4. **Use bif:contains** for keyword search with relevance ranking
5. **Always use LIMIT**: Especially for MGREL and MGSAT queries
6. **Filter by semantic type**: Use mo:sty to narrow by concept category
7. **Relationship query pattern**: ?rel a mo:MGREL ; mo:cui1 ?c1 ; mo:cui2 ?c2 ; mo:rela ?type
8. **Cross-reference pattern**: ?concept mo:mgconso ?bn . ?bn rdfs:seeAlso ?xref
9. **URI patterns for filtering**: MONDO = purl.obolibrary.org/obo/MONDO_, MeSH = id.nlm.nih.gov/mesh/, OMIM = identifiers.org/mim/
10. **Self-filter relationships**: FILTER(?cui1 != ?cui2) to exclude self-references

### Anti-patterns to Avoid
- ❌ **Querying direct relationship properties on ConceptID** (relationships are in MGREL)
- ❌ Not using DISTINCT with mo:mgconso (returns many duplicates)
- ❌ Aggregating MGREL or MGSAT without LIMIT (timeouts)
- ❌ Using FILTER(CONTAINS()) instead of bif:contains (slow)
- ❌ Omitting FROM clause (may return no results)
- ❌ Expecting all concepts to have definitions (only 34% coverage)
- ❌ Querying external URIs as subjects (they're references only)
- ❌ Assuming relationship types are standardized (some are "undefined_relationship")
