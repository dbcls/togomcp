# MedGen (Medical Genetics) Exploration Report

**Date**: January 31, 2026  
**Session**: 1 (Initial and Complete Exploration)

## Executive Summary

MedGen is NCBI's comprehensive portal for medical conditions with genetic components. Key findings from exploration:

- **Key capabilities requiring deep knowledge**: 
  - Cross-database integration with ClinVar requires critical URI conversion (`www.ncbi` → `ncbi`)
  - Relationships are stored in MGREL entities, NOT as direct properties on ConceptID (common pitfall)
  - Rich relationship types including inheritance patterns, manifestations, and hierarchical classifications
  
- **Major integration opportunities**: 
  - MedGen → ClinVar (genetic variants for diseases)
  - MedGen → MONDO, OMIM, Orphanet, HPO, MeSH (external ontology mappings)
  - Shared NCBI endpoint with ClinVar, PubMed, PubTator, NCBI Gene

- **Most valuable patterns discovered**:
  - URI conversion pattern for ClinVar integration (CRITICAL - without it, zero results)
  - MGREL traversal for disease-phenotype, disease-inheritance relationships
  - Semantic type filtering for specific concept types

- **Recommended question types**:
  - Cross-database questions linking diseases to genetic variants
  - Disease hierarchy and classification questions
  - Phenotype-disease association questions
  - Questions requiring understanding of MGREL structure

## Database Overview

- **Purpose and scope**: Medical genetics information portal integrating disease concepts with genetic data
- **Key data types and entities**: 
  - ConceptID (233,939 clinical concepts)
  - MGREL (1,130,420 relationships)
  - MGSAT (1,117,180 attributes)
  - MGCONSO (terminology mappings via blank nodes)
  - RDF reification statements (206,430 for provenance)
- **Dataset size**: 233K+ concepts, moderate size, performance generally good
- **Available access methods**: 
  - NCBI E-utilities (esearch, esummary)
  - SPARQL via RDF Portal (ncbi endpoint)

## Structure Analysis

### Performance Strategies

**Strategy 1: Use GRAPH Clause**
- MedGen graph URI: `http://rdfportal.org/dataset/medgen`
- Always include explicit `FROM` clause for single-database queries
- Use `GRAPH` clauses for cross-database queries

**Strategy 2: Use VALUES for Specific Concepts**
- Pre-filter with `VALUES ?medgen_cui { "C0010674" }` to reduce search space
- Essential for cross-database queries to avoid timeouts

**Strategy 3: URI Conversion for ClinVar Integration (CRITICAL)**
- MedGen uses `www.ncbi.nlm.nih.gov`, ClinVar uses `ncbi.nlm.nih.gov`
- Must use: `BIND(IRI(REPLACE(STR(?medgen_concept), "www.ncbi", "ncbi")) AS ?cv_uri)`
- Without this, cross-database queries return ZERO results

**Strategy 4: Always Use LIMIT**
- MGREL has 1.1M+ records
- MGSAT has 1.1M+ records
- Always add LIMIT to exploratory queries

**Strategy 5: Use DISTINCT for Cross-References**
- mgconso cross-references often return duplicates
- Always use `SELECT DISTINCT` when querying external cross-references

**Strategy 6: Split Property Paths in Cross-Database Queries**
- Complex property paths cause timeouts
- Split ClinVar classification path:
  ```
  ?variant cvo:classified_record ?classrec .
  ?classrec cvo:classifications ?classi .
  ?classi cvo:germline_classification ?germ .
  ?germ cvo:description ?significance .
  ```

### Common Pitfalls

**Error 1: Using Direct Relationship Properties on ConceptID**
- **Pattern**: Trying `?disease mo:disease_has_associated_gene ?gene`
- **Cause**: Relationships are stored in MGREL entities, not as direct properties
- **Symptom**: Empty results
- **Solution**: Use MGREL entities:
  ```sparql
  ?rel a mo:MGREL ;
      mo:cui1 ?disease ;
      mo:cui2 ?related ;
      mo:rela ?rel_type .
  ```

**Error 2: Missing URI Conversion for ClinVar**
- **Pattern**: Using MedGen URI directly in ClinVar graph
- **Cause**: Namespace mismatch (www.ncbi vs ncbi)
- **Symptom**: Zero results from cross-database query
- **Solution**: `BIND(IRI(REPLACE(STR(?medgen_concept), "www.ncbi", "ncbi")) AS ?cv_uri)`

**Error 3: Not Using DISTINCT for Cross-References**
- **Pattern**: `SELECT ?concept ?external_db WHERE { ?concept mo:mgconso ?bn . ?bn rdfs:seeAlso ?external_db }`
- **Cause**: Multiple mgconso blank nodes contain same rdfs:seeAlso values
- **Symptom**: Many duplicate rows
- **Solution**: Always use `SELECT DISTINCT`

**Error 4: Aggregating Without LIMIT**
- **Pattern**: `SELECT (COUNT(*) as ?count) WHERE { ?rel a mo:MGREL }`
- **Cause**: Over 1 million records
- **Symptom**: Timeout
- **Solution**: Use LIMIT or specific concept filters

### Data Organization

**ConceptID (Core Entity)**
- Properties: dct:identifier, rdfs:label, mo:sty, skos:definition
- Cross-references via mo:mgconso blank nodes
- Attributes via mo:mgsat blank nodes

**MGREL (Relationship Entity)**
- Links two concepts via mo:cui1 and mo:cui2
- Relationship type in mo:rela property
- Key relationship types:
  - `manifestation_of` / `has_manifestation` (255,600 each)
  - `isa` / `inverse_isa` (56,458 each)
  - `inheritance_type_of` / `has_inheritance_type` (13,040 / 6,580)
  - `disease_has_finding` / `is_finding_of_disease` (41,728 each)

**Semantic Types (UMLS Classification)**
- T033: Finding (106,477 concepts)
- T047: Disease or Syndrome (64,364 concepts)
- T191: Neoplastic Process (26,706 concepts)
- T046: Pathologic Function (9,654 concepts)
- T019: Congenital Abnormality (7,723 concepts)

### Cross-Database Integration Points

**Integration 1: MedGen → ClinVar (Genetic Variants)**
- Connection relationship: Disease concepts link to ClinVar variants
- Join point: MedGen CUI → URI conversion → ClinVar disease reference → variant
- Required information: 
  - MedGen: ConceptID, identifier, label
  - ClinVar: VariationArchiveType, clinical significance, variant type
- Pre-filtering needed: VALUES clause for specific CUI, split property paths
- Knowledge required: URI conversion pattern, ClinVar classification structure
- **CRITICAL**: Without URI conversion, returns zero results
- Performance: 3-5 seconds with optimizations

**Integration 2: MedGen → MONDO (Disease Ontology)**
- Connection relationship: rdfs:seeAlso via mgconso
- ~70% of MedGen concepts have MONDO mappings
- Pattern: `?bn rdfs:seeAlso ?mondo . FILTER(STRSTARTS(STR(?mondo), "http://purl.obolibrary.org/obo/MONDO_"))`

**Integration 3: MedGen → OMIM**
- Connection relationship: rdfs:seeAlso via mgconso
- ~30% coverage (9,953 diseases with OMIM cross-references)
- Pattern: `FILTER(STRSTARTS(STR(?omim), "http://identifiers.org/mim/"))`

**Integration 4: MedGen → MeSH**
- Connection relationship: rdfs:seeAlso via mgconso
- ~80% coverage
- Pattern: `FILTER(STRSTARTS(STR(?mesh), "http://id.nlm.nih.gov/mesh/"))`

**Integration 5: MedGen → Orphanet**
- Connection relationship: rdfs:seeAlso via mgconso
- ~20% coverage for rare diseases
- Pattern: `FILTER(STRSTARTS(STR(?orpha), "http://www.orpha.net/ORDO/"))`

## Complex Query Patterns Tested

### Pattern 1: Cross-Database Query - MedGen to ClinVar Variants (CRITICAL)

**Purpose**: Find genetic variants associated with a specific disease

**Category**: Cross-Database, Error-Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
WHERE {
  GRAPH <http://rdfportal.org/dataset/medgen> {
    ?medgen_concept a mo:ConceptID ;
                    dct:identifier "C0010674" .
  }
  GRAPH <http://rdfportal.org/dataset/clinvar> {
    ?ref rdfs:seeAlso ?medgen_concept .  # Won't match!
    ?variant med2rdf:disease ?disease .
  }
}
```

**What Happened**:
- Error message: None (silent failure)
- Results: 0 rows
- Why it failed: URI namespace mismatch - MedGen uses `www.ncbi.nlm.nih.gov`, ClinVar references use `ncbi.nlm.nih.gov`

**Correct Approach (using proper pattern)**:
```sparql
WHERE {
  GRAPH <http://rdfportal.org/dataset/medgen> {
    VALUES ?medgen_cui { "C0010674" }
    ?medgen_concept a mo:ConceptID ;
                    dct:identifier ?medgen_cui .
    BIND(IRI(REPLACE(STR(?medgen_concept), "www.ncbi", "ncbi")) AS ?cv_uri)
  }
  GRAPH <http://rdfportal.org/dataset/clinvar> {
    ?disease a med2rdf:Disease ;
             dct:references ?ref .
    ?ref rdfs:seeAlso ?cv_uri .
    ?variant a cvo:VariationArchiveType ;
             med2rdf:disease ?disease ;
             cvo:classified_record ?classrec .
    ?classrec cvo:classifications ?classi .
    ?classi cvo:germline_classification ?germ .
    ?germ cvo:description ?significance .
  }
}
```

**What Knowledge Made This Work**:
- URI conversion: `REPLACE(STR(?medgen_concept), "www.ncbi", "ncbi")`
- VALUES pre-filtering reduces search space
- Split property paths for ClinVar classification structure
- Performance improvement: From 0 results to 20+ in ~3-5 seconds

**Results Obtained**:
- 20+ variants for Cystic fibrosis (C0010674) including CFTR mutations
- 15+ variants for Marfan syndrome (C0024796) including FBN1 mutations
- Pathogenic and Likely pathogenic variants with clinical significance

**Natural Language Question Opportunities**:
1. "What genetic variants are associated with cystic fibrosis?" - Category: Integration
2. "Which pathogenic mutations cause Marfan syndrome?" - Category: Integration
3. "How many genetic variants have been reported for Huntington disease?" - Category: Completeness

---

### Pattern 2: MGREL Relationship Traversal (Disease-Phenotype)

**Purpose**: Find phenotypic manifestations of a disease

**Category**: Structured Query, Error-Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
# WRONG: Direct properties don't exist
SELECT ?disease ?phenotype
WHERE {
  ?disease mo:has_manifestation ?phenotype .
}
```

**What Happened**:
- Results: 0 rows
- Why it failed: Relationships stored in MGREL entities, not as direct properties on ConceptID

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?disease ?disease_label ?phenotype ?phenotype_label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  VALUES ?disease_cui { "C0010674" }
  ?disease a mo:ConceptID ;
      dct:identifier ?disease_cui ;
      rdfs:label ?disease_label .
  ?rel a mo:MGREL ;
      mo:cui1 ?disease ;
      mo:cui2 ?phenotype ;
      mo:rela "manifestation_of" .
  ?phenotype rdfs:label ?phenotype_label .
}
```

**What Knowledge Made This Work**:
- Understanding that MGREL stores all relationships
- Knowing the mo:rela value for manifestations
- Using cui1/cui2 to navigate relationship direction

**Results Obtained**:
- Cystic fibrosis: 43 phenotypic manifestations (bronchiectasis, meconium ileus, male infertility, etc.)
- Marfan syndrome: 97 phenotypic manifestations
- Huntington disease: 19 phenotypic manifestations

**Natural Language Question Opportunities**:
1. "What are the clinical features of cystic fibrosis?" - Category: Completeness
2. "Which symptoms are associated with Marfan syndrome?" - Category: Completeness
3. "What phenotypes characterize Huntington disease?" - Category: Completeness

---

### Pattern 3: Inheritance Pattern Retrieval

**Purpose**: Find the inheritance mode of a genetic disease

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?disease ?disease_label ?inheritance ?inheritance_label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?disease a mo:ConceptID ;
      dct:identifier "C0010674" ;
      rdfs:label ?disease_label .
  ?rel a mo:MGREL ;
      mo:cui1 ?disease ;
      mo:cui2 ?inheritance ;
      mo:rela "inheritance_type_of" .
  ?inheritance rdfs:label ?inheritance_label .
}
```

**Results Obtained**:
- Cystic fibrosis → Autosomal recessive inheritance
- Database-wide: 3,160 autosomal recessive diseases, 2,244 autosomal dominant diseases

**Natural Language Question Opportunities**:
1. "What is the inheritance pattern of cystic fibrosis?" - Category: Precision
2. "How many diseases in MedGen have autosomal recessive inheritance?" - Category: Completeness
3. "Which diseases are inherited in an X-linked recessive manner?" - Category: Structured Query

---

### Pattern 4: Cross-Reference to External Ontologies

**Purpose**: Find MONDO/OMIM/Orphanet identifiers for a disease

**Category**: Integration

**Correct Approach**:
```sparql
SELECT DISTINCT ?concept ?identifier ?label ?external_db
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      dct:identifier "C0010674" ;
      rdfs:label ?label ;
      mo:mgconso ?bn .
  ?bn rdfs:seeAlso ?external_db .
}
```

**Results Obtained**:
- Cystic fibrosis maps to:
  - MONDO_0009061
  - MeSH D003550
  - OMIM 219700, 602421
  - Orphanet_586
  - SNOMED CT 190905008

**Natural Language Question Opportunities**:
1. "What is the MONDO identifier for cystic fibrosis?" - Category: Integration
2. "Which OMIM entries correspond to Marfan syndrome?" - Category: Integration
3. "How many MedGen diseases have Orphanet cross-references?" - Category: Completeness

---

### Pattern 5: Semantic Type Filtering

**Purpose**: Find all concepts of a specific type (diseases, findings, neoplasms)

**Category**: Completeness, Structured Query

**Correct Approach**:
```sparql
SELECT ?concept ?identifier ?label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      mo:sty sty:T047 ;  # Disease or Syndrome
      rdfs:label ?label ;
      dct:identifier ?identifier .
}
LIMIT 100
```

**Results Obtained**:
- T047 (Disease or Syndrome): 64,364 concepts
- T033 (Finding): 106,477 concepts
- T191 (Neoplastic Process): 26,706 concepts

**Natural Language Question Opportunities**:
1. "How many disease concepts are in MedGen?" - Category: Completeness
2. "What neoplastic processes are documented in MedGen?" - Category: Completeness
3. "How many congenital abnormalities are cataloged?" - Category: Completeness

---

### Pattern 6: Full-Text Search with Keyword

**Purpose**: Find diseases by keyword in label

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?concept ?identifier ?label
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?concept a mo:ConceptID ;
      rdfs:label ?label ;
      dct:identifier ?identifier .
  ?label bif:contains "'cystic fibrosis'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
```

**Results Obtained**:
- Returns ranked results by relevance score
- Primary concept (C0010674) ranks first

**Natural Language Question Opportunities**:
1. "What conditions are related to 'diabetes' in MedGen?" - Category: Structured Query
2. "Find all familial cancer syndromes" - Category: Structured Query
3. "Which diseases mention 'cardiac' in their name?" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "cystic fibrosis"
   - Found: C0010674 - Cystic fibrosis (main disease concept)
   - Usage: Cross-database questions, phenotype questions, inheritance questions

2. Search: "Marfan syndrome"
   - Found: C0024796 - Marfan syndrome
   - Usage: Cross-database ClinVar questions, phenotype questions (97 manifestations)

3. Search: "Huntington disease"
   - Found: C0020179 - Huntington disease
   - Usage: Neurodegenerative disease questions, phenotype questions

4. Search: "diabetes mellitus"
   - Found: C0011849 - Diabetes mellitus
   - Usage: Disease hierarchy questions, common disease questions

5. Search: "breast cancer"
   - Found: C0346153 - Familial cancer of breast
   - Usage: Cancer genetics questions

6. Search: "familial" (neoplastic)
   - Found: Multiple familial cancer syndromes
   - Usage: Hereditary cancer questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions** (All phrased naturally):

1. "What genetic variants are associated with cystic fibrosis?"
   - Databases involved: MedGen, ClinVar
   - Knowledge Required: URI conversion pattern, ClinVar classification structure
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

2. "Which pathogenic mutations cause Marfan syndrome?"
   - Databases involved: MedGen, ClinVar
   - Knowledge Required: URI conversion, significance filtering
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

3. "Are there any pathogenic variants shared between cystic fibrosis and related CFTR disorders?"
   - Databases involved: MedGen, ClinVar
   - Knowledge Required: Multiple disease query, URI conversion
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

4. "What is the MONDO identifier for Huntington disease?"
   - Databases involved: MedGen, MONDO (via cross-reference)
   - Knowledge Required: mgconso cross-reference pattern, DISTINCT usage
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

5. "Which OMIM entries are linked to autosomal dominant diseases?"
   - Databases involved: MedGen, OMIM (via cross-reference)
   - Knowledge Required: MGREL inheritance traversal, mgconso pattern
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 3 + Pattern 4

**Error-Avoidance Questions** (CRITICAL - demonstrate anti-pattern knowledge):

6. "What phenotypes are associated with cystic fibrosis?"
   - Database: MedGen
   - Knowledge Required: MGREL structure (NOT direct properties on ConceptID)
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

7. "What diseases share manifestations with Marfan syndrome?"
   - Database: MedGen
   - Knowledge Required: MGREL traversal, relationship direction
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

8. "How many diseases have 'autosomal recessive' inheritance pattern?"
   - Database: MedGen
   - Knowledge Required: MGREL structure, inheritance relationship type
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

**Complex Filtering Questions**:

9. "Which diseases in MedGen have both OMIM and Orphanet cross-references?"
   - Database: MedGen
   - Knowledge Required: Multiple FILTER patterns, DISTINCT
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

10. "What familial cancer syndromes are documented in MedGen?"
    - Database: MedGen
    - Knowledge Required: Semantic type filtering + keyword search
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 5 + Pattern 6

11. "How many congenital abnormalities have MONDO mappings?"
    - Database: MedGen
    - Knowledge Required: Semantic type filtering + cross-reference pattern
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Pattern 4 + Pattern 5

12. "What are the child diseases of diabetes mellitus?"
    - Database: MedGen
    - Knowledge Required: MGREL hierarchy traversal (isa/inverse_isa)
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Related to Pattern 3

**Performance-Critical Questions**:

13. "How many diseases in MedGen have associated genetic variants in ClinVar?"
    - Databases: MedGen, ClinVar
    - Knowledge Required: URI conversion, efficient filtering, LIMIT
    - Category: Completeness
    - Difficulty: Hard
    - Pattern Reference: Pattern 1 (scaled)

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the MedGen concept ID for cystic fibrosis?"
   - Method: ncbi_esearch or simple SPARQL
   - Knowledge Required: None (straightforward)
   - Category: Precision
   - Difficulty: Easy

2. "What is the semantic type of MedGen concept C0024796?"
   - Method: Simple SPARQL lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "What is the definition of Huntington disease in MedGen?"
   - Method: Simple SPARQL lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

4. "Convert MedGen C0010674 to MONDO identifier"
   - Method: Cross-reference lookup (simple)
   - Knowledge Required: None (direct rdfs:seeAlso)
   - Category: Integration
   - Difficulty: Easy

5. "What MeSH descriptor corresponds to Marfan syndrome?"
   - Method: Cross-reference lookup (simple)
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source**:
- → ClinVar: via URI conversion for genetic variant data
- → MONDO: via rdfs:seeAlso for disease ontology mapping
- → OMIM: via rdfs:seeAlso for Mendelian disease data
- → Orphanet: via rdfs:seeAlso for rare disease data
- → MeSH: via rdfs:seeAlso for medical terminology
- → HPO: via rdfs:seeAlso for phenotype ontology

**This Database as Target**:
- ClinVar → MedGen: via disease references (requires URI conversion)
- PubMed → MedGen: potential via shared NCBI endpoint

**Complex Multi-Database Paths**:
- MedGen → ClinVar → NCBI Gene: Disease → Variant → Gene
- MedGen → MONDO → Other ontologies: Cross-ontology disease mapping

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **URI Conversion for ClinVar** - Without this knowledge, cross-database queries return zero results
2. **MGREL Structure** - Understanding that relationships are NOT direct properties but stored in MGREL entities
3. **Semantic Type Classification** - Knowing T047, T033, T191 codes enables targeted queries
4. **DISTINCT for Cross-References** - Avoiding duplicate results from mgconso patterns

### Common Pitfalls Discovered

1. **Assuming direct relationship properties exist** - They don't; use MGREL
2. **Forgetting URI conversion** - Critical for ClinVar integration
3. **Not using DISTINCT** - Cross-references generate many duplicates
4. **Aggregating without LIMIT** - 1M+ records in MGREL/MGSAT

### Recommendations for Question Design

1. Cross-database questions to ClinVar are HIGH VALUE - they demonstrate critical URI conversion knowledge
2. MGREL traversal questions demonstrate understanding of data model
3. Questions combining semantic type filtering with other criteria test schema knowledge
4. Inheritance pattern questions are straightforward with proper MGREL understanding

### Performance Notes

- Single-concept queries: < 1 second
- Keyword search with bif:contains: 2-5 seconds
- MGREL traversal: 2-5 seconds
- Cross-database to ClinVar: 3-5 seconds with proper optimization
- Full cross-reference retrieval: Use DISTINCT and LIMIT

---

## Notes and Observations

1. **MedGen is a clinical vocabulary hub** - Its value comes from integrating multiple terminologies
2. **MGREL is the key to relationships** - Almost all useful queries involve MGREL
3. **Definition coverage is limited** - Only ~34% of concepts have definitions
4. **External mapping quality varies** - MeSH (80%) > MONDO (70%) > OMIM (30%) > Orphanet (20%)
5. **The URI conversion requirement for ClinVar is undiscoverable** - You cannot figure this out without the MIE file
6. **Semantic types from UMLS are powerful filters** - Enable targeting specific concept types

---

## Next Steps

**Recommended for Question Generation**:
- Priority: Cross-database MedGen→ClinVar questions (demonstrate URI conversion)
- Priority: MGREL-based phenotype and inheritance questions (demonstrate data model knowledge)
- Avoid: Simple definition lookups (too easy, doesn't require MIE)
- Focus areas: Genetic disease-variant relationships, disease classification, phenotype associations

**Further Exploration Needed** (if any):
- Gene-disease associations via NCBI Gene (limited direct linkage in current data)
- PubMed integration possibilities

---

**Session Complete - Ready for Next Database**

```
Database: MedGen
Status: ✅ COMPLETE
Report: /evaluation/exploration/medgen_exploration.md
Patterns Tested: 6 major patterns
Questions Identified: 18+ opportunities
Integration Points: 6+ databases
Key Discovery: URI conversion for ClinVar is CRITICAL
```
