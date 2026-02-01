# ClinVar Exploration Report

**Date**: 2026-01-31
**Session**: 1

## Executive Summary
ClinVar is a comprehensive database of genetic variants with clinical interpretations, containing 3.5M+ variant records. This exploration revealed that ClinVar provides excellent opportunities for complex queries requiring deep database knowledge, particularly:

- Cross-database integration with MedGen (disease concepts) and NCBI Gene (gene annotations)
- Complex filtering by clinical significance, variant type, submitter count, and date
- Performance-critical queries on large datasets requiring proper pre-filtering
- Error-avoidance patterns for URI conversion and property path handling

Key capabilities requiring deep knowledge:
- URI pattern differences between databases (www.ncbi vs ncbi in MedGen↔ClinVar)
- Blank node chains for disease associations and cross-references
- Split property paths for performance in cross-database queries
- VALUES clause pre-filtering to reduce search space

## Database Overview
- **Purpose**: Aggregates genomic variation and its relationship to human health
- **Key data types**: 
  - VariationArchiveType (genetic variants with VCV accessions)
  - Gene (gene entities with HGNC/OMIM links)
  - ClinAsserTraitType (disease/phenotype associations)
  - ClassifiedRecord (clinical assertions/interpretations)
- **Dataset size**: 3,588,969 total variations
- **Performance considerations**: 
  - Use bif:contains for text search (not FILTER CONTAINS)
  - Always use LIMIT for exploratory queries
  - Complex blank node joins may be slow (3-10s)
  - Cross-database queries typically 2-10 seconds
- **Access methods**: SPARQL endpoint (ncbi shared), ncbi_esearch for variant discovery

## Structure Analysis

### Performance Strategies
1. **bif:contains for text search**
   - Why needed: FILTER CONTAINS scans all records; bif:contains uses index
   - When to apply: Any keyword search on labels/names
   - Performance impact: 10-100x faster than FILTER
   - Example: `?label bif:contains "'BRCA1'"` not `FILTER(CONTAINS(?label, "BRCA1"))`

2. **LIMIT on all exploratory queries**
   - Why needed: Dataset has 3.5M+ variants
   - When to apply: All queries during exploration
   - Performance impact: Prevents timeouts

3. **FROM clause specification**
   - Why needed: Multi-database endpoint requires graph targeting
   - When to apply: All queries
   - Example: `FROM <http://rdfportal.org/dataset/clinvar>`

4. **VALUES clause pre-filtering**
   - Why needed: Reduces search space before cross-database joins
   - When to apply: Cross-database queries with known entities
   - Performance impact: 99%+ reduction in search space

5. **Split property paths for cross-database queries**
   - Why needed: Complex property paths cause timeouts
   - When to apply: When accessing nested blank node data
   - Example: Split `cvo:classified_record/cvo:classifications/cvo:germline_classification/cvo:description` into individual triple patterns

### Common Pitfalls
1. **Missing Graph Specification**
   - Cause: Queries without FROM clause
   - Symptoms: Incomplete results or timeout
   - Solution: Always specify `FROM <http://rdfportal.org/dataset/clinvar>`

2. **FILTER CONTAINS vs bif:contains**
   - Cause: Using SQL-like CONTAINS pattern
   - Symptoms: Slow queries (10-100x slower)
   - Solution: Use `?label bif:contains "'term'"` with single-quoted terms

3. **Cross-Database URI Mismatch**
   - Cause: MedGen uses www.ncbi.nlm.nih.gov, ClinVar uses ncbi.nlm.nih.gov
   - Symptoms: No results from cross-database queries
   - Solution: Use `IRI(REPLACE(STR(?medgen_concept), "www.ncbi", "ncbi"))`

4. **Property Paths in Cross-Database Queries**
   - Cause: Long property paths without splitting
   - Symptoms: Timeout (>60s)
   - Solution: Split into individual triple patterns

### Data Organization
1. **Variants (VariationArchiveType)**
   - Core records with VCV accessions
   - Contains: variation_type, record_status, dates, submitter counts
   - Links: disease associations, classified records

2. **Genes (cvo:Gene)**
   - Gene entities with NCBI Gene IDs
   - Contains: symbol, full_name, cytogenetic_location
   - Cross-refs: HGNC, OMIM

3. **Diseases (ClinAsserTraitType)**
   - Blank nodes linked via med2rdf:disease
   - Contains: disease name, type, external references
   - Cross-refs: MedGen, MeSH, OMIM via dct:references → rdfs:seeAlso

4. **Classifications (ClassifiedRecord)**
   - Nested blank nodes for clinical significance
   - Path: classified_record → classifications → germline_classification → description

### Cross-Database Integration Points

**Integration 1: ClinVar → NCBI Gene**
- Connection: Variant → gene via med2rdf:gene property
- Join: ClinVar gene URI (http://ncbi.nlm.nih.gov/gene/{id}) → NCBI Gene dct:identifier
- Required info: Gene symbols, types, descriptions from NCBI Gene
- Pre-filtering: Use VALUES clause with specific gene URIs
- Knowledge required: URI conversion with BIND, placing BIND between GRAPH clauses
- Performance: ~2-3 seconds with VALUES pre-filtering

**Integration 2: ClinVar → MedGen**
- Connection: Disease blank node → dct:references → rdfs:seeAlso → MedGen URI
- Join: Convert MedGen URI pattern (www.ncbi → ncbi)
- Required info: Disease concepts, semantic types from MedGen
- Pre-filtering: Use VALUES with specific MedGen CUI
- Knowledge required: URI conversion with REPLACE
- Performance: ~3-5 seconds with VALUES pre-filtering

**Integration 3: ClinVar → PubMed (indirect)**
- Connection: Citations in disease blank nodes
- Link via: dct:references → cvo:url/rdfs:seeAlso
- Use case: Finding literature supporting clinical interpretations

## Complex Query Patterns Tested

### Pattern 1: Cross-Database Gene-Variant Integration

**Purpose**: Find variants for a specific gene with comprehensive gene annotations

**Category**: Cross-Database, Performance-Critical

**Naive Approach (without proper knowledge)**:
Query ClinVar variants and try to join with NCBI Gene using direct URI matching

**What Happened**:
- No results due to URI pattern mismatch
- ClinVar uses http://ncbi.nlm.nih.gov/gene/{id}
- NCBI Gene uses identifiers.org pattern with dct:identifier string

**Correct Approach (using proper pattern)**:
```sparql
GRAPH <http://rdfportal.org/dataset/clinvar> {
  VALUES ?gene_uri { <http://ncbi.nlm.nih.gov/gene/672> }
  ?gene_bn med2rdf:gene ?gene_uri .
  ?classrec sio:SIO_000628 ?gene_bn .
  ?variant a cvo:VariationArchiveType ;
           cvo:classified_record ?classrec .
  BIND("672" AS ?gene_id)
}
GRAPH <http://rdfportal.org/dataset/ncbigene> {
  ?ncbi_gene dct:identifier ?gene_id ;
             rdfs:label ?gene_symbol .
}
```

**What Knowledge Made This Work**:
- VALUES pre-filtering reduces ClinVar variants from 3.5M to ~1000
- BIND converts gene_uri to string ID for NCBI Gene matching
- Explicit GRAPH clauses required for cross-database queries
- Performance: ~2-3 seconds (vs timeout without VALUES)

**Results Obtained**:
- Number of results: 20 (limited)
- Sample results:
  * BRCA1 variants with gene type "protein-coding"
  * Full gene descriptions from NCBI Gene

**Natural Language Question Opportunities**:
1. "What genetic variants affect BRCA1, and what is the gene's function?" - Category: Integration
2. "Find all pathogenic variants in the TP53 tumor suppressor gene" - Category: Structured Query
3. "Which CFTR variants are associated with cystic fibrosis?" - Category: Integration

---

### Pattern 2: MedGen Disease Integration

**Purpose**: Link ClinVar variants to disease concepts in MedGen

**Category**: Cross-Database, Error-Avoidance

**Naive Approach (without proper knowledge)**:
Try to join MedGen concepts directly with ClinVar references

**What Happened**:
- No results due to URI namespace mismatch
- MedGen: http://www.ncbi.nlm.nih.gov/medgen/C0011849
- ClinVar refs: http://ncbi.nlm.nih.gov/medgen/C0011849

**Correct Approach (using proper pattern)**:
```sparql
GRAPH <http://rdfportal.org/dataset/medgen> {
  VALUES ?medgen_cui { "C0011849" }
  ?medgen_concept a mo:ConceptID ;
                  dct:identifier ?medgen_cui .
  BIND(IRI(REPLACE(STR(?medgen_concept), "www.ncbi", "ncbi")) AS ?cv_medgen_uri)
}
GRAPH <http://rdfportal.org/dataset/clinvar> {
  ?disease dct:references ?ref .
  ?ref rdfs:seeAlso ?cv_medgen_uri .
  ?variant med2rdf:disease ?disease .
}
```

**What Knowledge Made This Work**:
- URI conversion with REPLACE function (Strategy 5)
- Split property path for dct:references → rdfs:seeAlso
- VALUES pre-filtering on MedGen CUI
- Performance: ~3-5 seconds (vs no results without URI conversion)

**Results Obtained**:
- Number of results: 15 (limited)
- Sample results:
  * Diabetes mellitus (C0011849) variants
  * Variants in INS, WFS1, KCNJ11, GCK genes

**Natural Language Question Opportunities**:
1. "What genetic variants are associated with diabetes mellitus?" - Category: Integration
2. "Which genes have pathogenic variants causing hereditary breast cancer?" - Category: Structured Query
3. "Find all variants linked to Li-Fraumeni syndrome" - Category: Specificity

---

### Pattern 3: Clinical Significance Filtering

**Purpose**: Find pathogenic variants with high confidence (multiple submitters)

**Category**: Structured Query, Completeness

**Naive Approach (without proper knowledge)**:
Simple filter on significance string without performance consideration

**Correct Approach (using proper pattern)**:
```sparql
SELECT ?variant ?label ?num_submitters ?significance
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:number_of_submitters ?num_submitters ;
           cvo:record_status "current" ;
           cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
  FILTER(?num_submitters >= 10)
  FILTER(?significance = "Pathogenic")
}
ORDER BY DESC(?num_submitters)
LIMIT 20
```

**What Knowledge Made This Work**:
- Property path for nested classification structure
- Filter by record_status "current" to exclude deprecated
- Combined filtering on multiple criteria
- Performance: ~3-5 seconds

**Results Obtained**:
- Number of results: 20 (limited)
- Sample results:
  * GJB2 c.35del - 80 submitters (most cited)
  * BRCA1 c.68_69del - 78 submitters
  * CFTR p.Phe508del - 78 submitters
  * BRCA2 c.5946del - 73 submitters

**Natural Language Question Opportunities**:
1. "What are the most well-studied pathogenic variants in ClinVar?" - Category: Completeness
2. "Which pathogenic variants have the strongest evidence from multiple laboratories?" - Category: Structured Query
3. "Find high-confidence pathogenic variants with at least 10 submitters" - Category: Precision

---

### Pattern 4: Gene-Specific Variant Counts

**Purpose**: Count variants by type for a specific gene

**Category**: Completeness, Performance-Critical

**Correct Approach**:
```sparql
SELECT ?variation_type (COUNT(?variant) as ?count)
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           cvo:variation_type ?variation_type ;
           rdfs:label ?label ;
           cvo:record_status "current" .
  ?label bif:contains "'BRCA1'" .
}
GROUP BY ?variation_type
ORDER BY DESC(?count)
```

**What Knowledge Made This Work**:
- bif:contains for efficient gene symbol search
- GROUP BY for aggregation by type
- record_status filter for current records only
- Performance: ~2-3 seconds

**Results Obtained**:
- Total BRCA1 variants: ~15,000
- Types: SNV (~60%), deletions (~25%), duplications (~10%), others

**Natural Language Question Opportunities**:
1. "How many BRCA1 variants of each type are in ClinVar?" - Category: Completeness
2. "What is the distribution of variant types for the CFTR gene?" - Category: Structured Query

---

### Pattern 5: Clinical Significance Distribution

**Purpose**: Count variants by clinical significance classification

**Category**: Completeness

**Correct Approach**:
```sparql
SELECT ?significance (COUNT(?variant) as ?count)
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           cvo:record_status "current" ;
           cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
}
GROUP BY ?significance
ORDER BY DESC(?count)
```

**Results Obtained**:
- Uncertain significance: 1,821,577 (51%)
- Likely benign: 993,150 (28%)
- Benign: 213,802 (6%)
- Pathogenic: 200,004 (6%)
- Conflicting: 145,497 (4%)

**Natural Language Question Opportunities**:
1. "How many variants in ClinVar are classified as pathogenic?" - Category: Completeness
2. "What percentage of ClinVar variants have uncertain significance?" - Category: Precision

---

### Pattern 6: Conflicting Interpretations

**Purpose**: Find variants with conflicting clinical interpretations

**Category**: Specificity, Structured Query

**Correct Approach**:
```sparql
SELECT ?variant ?label ?num_submitters ?significance
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:number_of_submitters ?num_submitters ;
           cvo:record_status "current" ;
           cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
  FILTER(CONTAINS(?significance, "Conflicting"))
  FILTER(?num_submitters >= 5)
}
ORDER BY DESC(?num_submitters)
```

**Results Obtained**:
- SPG7 c.1529C>T - 64 submitters with conflicting interpretations
- POLG c.1760C>T - 52 submitters
- APC c.3920T>A (I1307K) - 52 submitters

**Natural Language Question Opportunities**:
1. "Which variants have conflicting interpretations from different laboratories?" - Category: Specificity
2. "Find variants where clinical significance is disputed" - Category: Structured Query

---

### Pattern 7: Recently Updated Variants

**Purpose**: Find newly added or recently updated variants

**Category**: Currency

**Correct Approach**:
```sparql
SELECT ?variant ?label ?type ?created ?last_updated ?significance
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?variant a cvo:VariationArchiveType ;
           cvo:date_created ?created ;
           cvo:date_last_updated ?last_updated ;
           cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
  FILTER(?created >= "2025-01-01"^^xsd:date)
}
ORDER BY DESC(?created)
LIMIT 20
```

**Results Obtained**:
- Recent additions from June 2025
- Examples: BTK, GRN, PAX2, PKD1 variants

**Natural Language Question Opportunities**:
1. "What pathogenic variants were added to ClinVar in the last month?" - Category: Currency
2. "Show recently submitted variants for hereditary cancer genes" - Category: Currency

---

### Pattern 8: Gene Location Queries

**Purpose**: Find genes and variants by chromosomal location

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?gene ?symbol ?full_name ?cyto_loc ?hgnc ?omim
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  ?gene a cvo:Gene ;
        cvo:symbol ?symbol ;
        cvo:full_name ?full_name ;
        cvo:cytogenetic_location ?cyto_loc .
  OPTIONAL { ?gene cvo:hgnc_id ?hgnc }
  OPTIONAL { ?gene cvo:omim ?omim }
  FILTER(REGEX(?cyto_loc, "^17[pq]"))
}
ORDER BY ?cyto_loc
```

**Results Obtained**:
- Genes on chromosome 17
- BRCA1 location: 17q21.31

**Natural Language Question Opportunities**:
1. "What genes on chromosome 17 have pathogenic variants?" - Category: Structured Query
2. "Find all variants in the BRCA1 chromosomal region (17q21)" - Category: Specificity

---

## Simple Queries Performed

1. **Search: "BRCA1"**
   - Found: VCV000856461 - BRCA1 c.2244dup pathogenic frameshift
   - Usage: Testing gene-specific queries

2. **Search: "TP53"**
   - Found: VCV000012361 - TP53 c.628_629del Li-Fraumeni syndrome
   - Usage: Disease association queries

3. **Search: Variation ID lookup**
   - Found: VCV000017004 - GJB2 c.35del (most cited pathogenic variant)
   - Usage: Accession-based queries

4. **Search: CFTR**
   - Found: VCV000007105 - CFTR p.Phe508del (cystic fibrosis)
   - Usage: Cross-database integration examples

5. **NCBI esearch: "BRCA1[gene] AND pathogenic"**
   - Found: 13,961 pathogenic BRCA1 variants
   - Usage: Alternative search method

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What genetic variants are associated with diabetes mellitus, and what genes are affected?"
   - Databases: ClinVar, MedGen, NCBI Gene
   - Knowledge Required: URI conversion (www.ncbi→ncbi), VALUES pre-filtering, split property paths
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

2. "Find all pathogenic variants in BRCA1 and list the associated diseases"
   - Databases: ClinVar (+ MedGen for disease enrichment)
   - Knowledge Required: med2rdf:disease navigation, dct:references→rdfs:seeAlso path
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1, Pattern 2

3. "Which genes have the most pathogenic variants for hereditary cancer syndromes?"
   - Databases: ClinVar, NCBI Gene
   - Knowledge Required: Cross-database join via gene URI, aggregation
   - Category: Completeness / Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 1, Pattern 3

4. "What is the gene type and function for genes with variants causing Li-Fraumeni syndrome?"
   - Databases: ClinVar, NCBI Gene
   - Knowledge Required: Disease filtering + cross-database gene enrichment
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

**Performance-Critical Questions**:

5. "How many pathogenic variants are recorded in ClinVar?"
   - Database: ClinVar
   - Knowledge Required: Property path for significance, efficient COUNT
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

6. "What are the most well-studied pathogenic variants (with 10+ submitters)?"
   - Database: ClinVar
   - Knowledge Required: Combined filtering, ORDER BY optimization
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

7. "Count all variant types in ClinVar and their frequencies"
   - Database: ClinVar
   - Knowledge Required: Efficient GROUP BY, record_status filtering
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 4

**Error-Avoidance Questions**:

8. "Find variants where the variant name contains 'kinase'"
   - Database: ClinVar
   - Knowledge Required: bif:contains syntax (not FILTER CONTAINS)
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

9. "What variants in BRCA1 have multiple disease associations?"
   - Database: ClinVar
   - Knowledge Required: Blank node navigation for diseases
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

**Complex Filtering Questions**:

10. "Find pathogenic deletions in BRCA1 with at least 5 submitters"
    - Database: ClinVar
    - Knowledge Required: Multiple filter criteria combination
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

11. "Which variants have conflicting clinical interpretations from multiple laboratories?"
    - Database: ClinVar
    - Knowledge Required: Significance filtering with CONTAINS
    - Category: Specificity
    - Difficulty: Medium
    - Pattern Reference: Pattern 6

12. "Find recently added pathogenic variants (since 2025)"
    - Database: ClinVar
    - Knowledge Required: Date filtering with xsd:date
    - Category: Currency
    - Difficulty: Easy
    - Pattern Reference: Pattern 7

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the ClinVar accession for the common cystic fibrosis variant p.Phe508del?"
   - Method: bif:contains search
   - Knowledge Required: None (straightforward search)
   - Category: Entity Lookup
   - Difficulty: Easy

2. "Find the clinical significance of ClinVar variant VCV000017004"
   - Method: Direct accession lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

3. "What is the NCBI Gene ID for the BRCA1 gene in ClinVar?"
   - Method: Gene lookup
   - Knowledge Required: None (direct property access)
   - Category: ID Mapping
   - Difficulty: Easy

---

## Integration Patterns Summary

**ClinVar as Source**:
- → NCBI Gene: via med2rdf:gene property (gene ID extraction)
- → MedGen: via dct:references → rdfs:seeAlso (URI conversion required)
- → PubMed: via citation links in disease references

**ClinVar as Target**:
- MedGen →: Disease concept linking (URI conversion required)
- NCBI Gene →: Gene-centric variant queries

**Complex Multi-Database Paths**:
- ClinVar → MedGen → PubMed: Variant → Disease → Literature
- NCBI Gene → ClinVar → MedGen: Gene → Variants → Disease concepts

---

## Lessons Learned

### What Knowledge is Most Valuable
1. URI pattern differences between databases (www.ncbi vs ncbi)
2. Property path navigation through blank nodes
3. VALUES pre-filtering for cross-database queries
4. bif:contains syntax for efficient text search

### Common Pitfalls Discovered
1. URI mismatch causing empty results in cross-database queries
2. Property path performance issues without splitting
3. Missing GRAPH clauses in multi-database queries
4. BIND placement (must be between GRAPH clauses, not inside)

### Recommendations for Question Design
1. Cross-database questions should test URI conversion knowledge
2. Performance questions should involve large result sets requiring filtering
3. Include questions that test blank node navigation (disease associations)
4. Test both bif:contains and FILTER patterns

### Performance Notes
- Simple property queries: <1 second
- bif:contains searches: 1-3 seconds
- Complex blank node joins: 3-10 seconds
- Cross-database queries: 2-5 seconds with optimization, timeout without
- Aggregation on full dataset: 5-15 seconds

---

## Notes and Observations

- ClinVar has excellent clinical significance categorization
- Disease associations use nested blank nodes requiring careful navigation
- MedGen integration requires URI conversion (critical finding)
- NCBI Gene integration requires identifier extraction and conversion
- Most variants are from single submitters; high submitter count indicates well-studied variants
- Conflicting interpretations are common and clinically important

---

## Next Steps

**Recommended for Question Generation**:
- Priority: Cross-database integration questions (MedGen, NCBI Gene)
- Focus: Clinical significance filtering, disease associations
- Avoid: Simple accession lookups (too easy)

**Further Exploration Needed**:
- Three-way integration (ClinVar + MedGen + PubMed) - may require separate queries
- Somatic vs germline classification differences
- Star allele nomenclature variants

---

**Session Complete - Ready for Next Database**
