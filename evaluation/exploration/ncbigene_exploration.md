# NCBI Gene Database Exploration Report

**Date**: January 31, 2026
**Session**: 1 (Complete exploration)

## Executive Summary

NCBI Gene is a comprehensive gene database containing 57M+ entries covering all organisms. The database provides excellent integration opportunities with ClinVar (variants), PubMed (literature), PubTator (text mining), and MedGen (clinical concepts) through a shared NCBI endpoint. Key findings:

- **Key capabilities requiring deep knowledge**: Organism filtering (taxid), URI conversion for cross-database queries, text search patterns (bif:contains on descriptions not labels), orthology queries
- **Major integration opportunities**: ClinVar (gene-variant), PubMed (gene-literature), PubTator (gene text mining), MedGen (gene-disease)
- **Most valuable patterns discovered**: Cross-database queries require URI conversion (identifiers.org → ncbi.nlm.nih.gov), organism pre-filtering is essential for performance
- **Recommended question types**: Multi-database integration, gene type/chromosome filtering, orthology queries, disease-gene associations

## Database Overview

- **Purpose and scope**: Central gene information resource linking to sequences, maps, pathways, and literature
- **Key data types**: Protein-coding genes, ncRNAs, pseudogenes, biological regions, tRNAs, rRNAs
- **Dataset size**: 57,768,578 total genes; 20,595 human protein-coding genes
- **Available access methods**: SPARQL via RDF Portal, ncbi_esearch/esummary E-utilities, togoid conversions

## Structure Analysis

### Performance Strategies

1. **Organism Pre-filtering (taxid)** - Critical
   - Why: 57M+ genes across all organisms
   - When: ALWAYS when querying by properties
   - Performance: Reduces search space by 99.9%+
   - Example: `ncbio:taxid <http://identifiers.org/taxonomy/9606>` for human

2. **bif:contains for Text Search** - Critical
   - Why: FILTER/CONTAINS causes timeouts on large datasets
   - When: Any keyword search in descriptions
   - Performance: 10-100x faster than REGEX/FILTER
   - Syntax: `?description bif:contains "'keyword'" option (score ?sc)`

3. **Search Descriptions NOT Labels**
   - Why: Labels contain symbols (INS, BRCA1), descriptions contain full names (insulin)
   - When: Searching for gene function terms
   - Anti-pattern: `?label bif:contains "'insulin'"` returns nothing

4. **LIMIT for Orthology Queries**
   - Why: Average 150 orthologs per gene, unbounded queries timeout
   - When: Any query involving orth:hasOrtholog
   - Always add: `LIMIT 100` or appropriate limit

5. **URI Conversion for Cross-Database Queries** - Critical
   - Why: NCBI Gene uses `identifiers.org/ncbigene/`, ClinVar uses `ncbi.nlm.nih.gov/gene/`
   - When: Integrating with ClinVar
   - Pattern: `BIND(IRI(CONCAT("http://ncbi.nlm.nih.gov/gene/", ?gene_id)) AS ?cv_gene_uri)`
   - CRITICAL: BIND must be placed BETWEEN GRAPH clauses, not inside

### Common Pitfalls

1. **Searching without organism filter**
   - Cause: Queries all 57M+ genes
   - Symptoms: Timeout after 60 seconds
   - Solution: Always add `ncbio:taxid <http://identifiers.org/taxonomy/9606>`

2. **Searching full names in label field**
   - Cause: Labels are symbols (INS), not names (insulin)
   - Symptoms: Empty results for valid queries
   - Solution: Search `dct:description` not `rdfs:label`

3. **BIND inside GRAPH clause**
   - Cause: Variables from another GRAPH not accessible inside GRAPH
   - Symptoms: Query fails or returns no results
   - Solution: Place BIND between GRAPH clauses

4. **URI pattern mismatch in cross-database queries**
   - Cause: Different URI namespaces across databases
   - Symptoms: No results despite valid data
   - Solution: Use BIND with CONCAT to convert URI patterns

### Data Organization

- **Gene entity** (insdc:Gene): Core record with symbol, description, type, chromosome, location
- **Synonyms** (insdc:gene_synonym): Historical and alternative names
- **External links** (insdc:dblink): IRI links to Ensembl, HGNC, OMIM via identifiers.org
- **String references** (insdc:db_xref): Text-based references like "Database:ID"
- **Orthology** (orth:hasOrtholog): Cross-species gene relationships
- **Taxonomy** (ncbio:taxid): Organism classification

### Cross-Database Integration Points

**Integration 1: NCBI Gene → ClinVar (Variants)**
- Connection: Gene ID → variant associations via med2rdf:gene
- Join point: `med2rdf:gene <http://ncbi.nlm.nih.gov/gene/{id}>`
- Required info: Gene ID from NCBI Gene, variant info from ClinVar
- Pre-filtering: Filter by gene symbol first using bif:contains
- Knowledge required: URI conversion pattern, property path in ClinVar
- Verified: Pattern 2 below

**Integration 2: NCBI Gene → PubMed (Literature)**
- Connection: Keyword matching on gene symbol in article titles
- Join point: Both use text search (bif:contains)
- Required info: Gene symbol/description from NCBI Gene, article title/abstract from PubMed
- Pre-filtering: Use bif:contains in both GRAPH blocks
- Knowledge required: Double pre-filtering strategy
- Verified: Pattern 4 below

**Integration 3: NCBI Gene → PubTator → PubMed (Three-way)**
- Connection: PubTator annotations link genes to articles
- Join point: PubTator uses identifiers.org/ncbigene (compatible!)
- Required info: Gene metadata from NCBI Gene, annotations from PubTator, article info from PubMed
- Pre-filtering: Pre-filter in PubMed with bif:contains
- Knowledge required: Three database schemas
- Verified: Pattern 5 below

**Integration 4: NCBI Gene → TogoID → UniProt**
- Connection: ID conversion via togoid service
- Join point: togoid_convertId route 'ncbigene,uniprot'
- Required info: Gene ID, returns UniProt accessions
- Pre-filtering: N/A (direct lookup)
- Knowledge required: TogoID route availability

## Complex Query Patterns Tested

### Pattern 1: Performance-Critical Filtering (Gene Type + Organism)

**Purpose**: Find all protein-coding genes in human

**Category**: Performance-Critical

**Naive Approach**: Query all genes without organism filter
- Processes 57M+ genes → timeout

**Correct Approach**: Pre-filter by organism (taxid)
```sparql
SELECT (COUNT(?gene) as ?count)
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene a insdc:Gene ;
        ncbio:typeOfGene "protein-coding" ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
}
```

**What Knowledge Made This Work**:
- Key Insight: Filter by taxid FIRST to reduce from 57M to ~20K genes
- Performance: ~2 seconds vs timeout
- Result: 20,595 human protein-coding genes

**Natural Language Question Opportunities**:
1. "How many protein-coding genes are there in human?" - Category: Completeness
2. "What types of genes are annotated for human in NCBI Gene?" - Category: Completeness

---

### Pattern 2: Cross-Database (NCBI Gene → ClinVar)

**Purpose**: Find genetic variants associated with a specific gene

**Category**: Integration

**Naive Approach**: Direct join without URI conversion
- ClinVar uses different URI pattern (ncbi.nlm.nih.gov vs identifiers.org)
- Result: No matches

**Correct Approach**: Use URI conversion with BIND between GRAPH clauses
```sparql
SELECT ?gene_symbol ?var_label ?var_type
WHERE {
  GRAPH <http://rdfportal.org/dataset/ncbigene> {
    ?ncbi_gene a insdc:Gene ;
               dct:identifier ?gene_id ;
               rdfs:label ?gene_symbol .
    ?gene_symbol bif:contains "'BRCA1'" .
  }
  BIND(IRI(CONCAT("http://ncbi.nlm.nih.gov/gene/", ?gene_id)) AS ?cv_gene_uri)
  GRAPH <http://rdfportal.org/dataset/clinvar> {
    ?allele_bnode med2rdf:gene ?cv_gene_uri .
    ?variant rdfs:label ?var_label ;
             cvo:variation_type ?var_type .
    ...
  }
}
```

**What Knowledge Made This Work**:
- Key Insight 1: URI conversion needed (identifiers.org → ncbi.nlm.nih.gov)
- Key Insight 2: BIND must be BETWEEN GRAPH clauses
- Performance: ~3 seconds for 50 results
- Results: Variants with types (SNV, deletion, insertion, etc.)

**Natural Language Question Opportunities**:
1. "What genetic variants are associated with the BRCA1 gene?" - Category: Integration
2. "Find all pathogenic mutations in the TP53 tumor suppressor gene" - Category: Structured Query

---

### Pattern 3: Text Search Anti-Pattern (Label vs Description)

**Purpose**: Find genes related to insulin

**Category**: Error-Avoidance

**Naive Approach**: Search for 'insulin' in labels
```sparql
?label bif:contains "'insulin'" .
```
- Result: EMPTY - labels contain symbols (INS), not names

**Correct Approach**: Search in descriptions
```sparql
?description bif:contains "'insulin'" option (score ?sc) .
```

**What Knowledge Made This Work**:
- Key Insight: rdfs:label = symbols (INS), dct:description = full names (insulin)
- Performance: ~2 seconds for 20 results
- Results: INS (insulin), IGF1, INSR, IRS1, etc.

**Natural Language Question Opportunities**:
1. "Find human genes related to insulin signaling" - Category: Precision
2. "Which genes have descriptions mentioning 'kinase'?" - Category: Structured Query

---

### Pattern 4: Cross-Database (NCBI Gene → PubMed)

**Purpose**: Find literature about specific genes

**Category**: Integration

**Naive Approach**: No pre-filtering, join on entire databases
- Result: Timeout (37M articles × 57M genes)

**Correct Approach**: Double pre-filtering with bif:contains in both GRAPH blocks
```sparql
SELECT ?gene_symbol ?pmid ?article_title
WHERE {
  GRAPH <http://rdfportal.org/dataset/ncbigene> {
    ?ncbi_gene rdfs:label ?gene_symbol ;
               ncbio:taxid <http://identifiers.org/taxonomy/9606> .
    ?gene_symbol bif:contains "'TP53'" .
  }
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?article_title .
    ?article_title bif:contains "'TP53' AND 'cancer'" .
  }
}
```

**What Knowledge Made This Work**:
- Key Insight 1: Pre-filter NCBI Gene with taxid + bif:contains
- Key Insight 2: Pre-filter PubMed with bif:contains
- Performance: ~3-5 seconds for 30 results
- Performance gain: 99.999% reduction in search space

**Natural Language Question Opportunities**:
1. "Find publications about the TP53 gene and cancer" - Category: Integration
2. "What research papers mention BRCA1 and breast cancer?" - Category: Currency

---

### Pattern 5: Three-Way Integration (PubMed → PubTator → NCBI Gene)

**Purpose**: Find literature with gene annotations and gene metadata

**Category**: Integration (Complex)

**Naive Approach**: Three-way join without pre-filtering
- Result: Timeout

**Correct Approach**: Pre-filter in PubMed, let PubTator use compatible URIs
```sparql
SELECT ?pmid ?title ?geneId ?gene_symbol ?gene_desc
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?title .
    ?title bif:contains "'BRCA1' AND 'breast cancer'" .
  }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?ann dcterms:subject "Gene" ;
         oa:hasBody ?geneId ;
         oa:hasTarget ?article .
  }
  GRAPH <http://rdfportal.org/dataset/ncbigene> {
    ?geneId a insdc:Gene ;
            rdfs:label ?gene_symbol .
    OPTIONAL { ?geneId dct:description ?gene_desc }
  }
}
```

**What Knowledge Made This Work**:
- Key Insight 1: PubTator uses identifiers.org/ncbigene URIs (compatible with NCBI Gene!)
- Key Insight 2: Pre-filter in PubMed reduces articles from 37M to ~100
- Performance: ~5-8 seconds for 30 results
- No URI conversion needed between PubTator and NCBI Gene

**Natural Language Question Opportunities**:
1. "Find genes mentioned in publications about breast cancer and identify their functions" - Category: Integration
2. "What genes are discussed in Alzheimer's disease research literature?" - Category: Structured Query

---

### Pattern 6: Orthology Analysis

**Purpose**: Find orthologous genes across species

**Category**: Structured Query

**Naive Approach**: Query all orthology relationships
- Result: Millions of results, timeout

**Correct Approach**: Start with specific gene, use LIMIT
```sparql
SELECT ?ortholog ?label ?taxid
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  <http://identifiers.org/ncbigene/3630> orth:hasOrtholog ?ortholog .
  ?ortholog rdfs:label ?label ;
            ncbio:taxid ?taxid .
}
LIMIT 20
```

**What Knowledge Made This Work**:
- Key Insight: Average 150 orthologs per gene
- MUST start with specific gene ID
- MUST use LIMIT
- Performance: <1 second for 20 results

**Natural Language Question Opportunities**:
1. "What are the mouse and rat orthologs of human insulin gene?" - Category: Integration
2. "Find species that have orthologs of human TP53" - Category: Completeness

---

### Pattern 7: Chromosome-Based Queries with Gene Types

**Purpose**: Analyze gene distribution by chromosome

**Category**: Completeness

**Correct Approach**:
```sparql
SELECT ?chromosome (COUNT(?gene) AS ?gene_count)
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene a insdc:Gene ;
        ncbio:typeOfGene "protein-coding" ;
        insdc:chromosome ?chromosome ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
}
GROUP BY ?chromosome
ORDER BY DESC(?gene_count)
```

**Results Obtained**:
- Chromosome 1: 2,097 genes (most)
- Chromosome 19: 1,459 genes
- Chromosome Y: 89 genes (least autosome equivalent)
- MT (mitochondrial): 13 genes

**Natural Language Question Opportunities**:
1. "How many protein-coding genes are on human chromosome 21?" - Category: Completeness
2. "Which human chromosome has the most protein-coding genes?" - Category: Precision

---

### Pattern 8: OMIM Disease Associations

**Purpose**: Find genes with known disease associations

**Category**: Integration

**Correct Approach**: Filter by OMIM links using insdc:dblink
```sparql
SELECT ?gene ?label ?omim_link
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene insdc:dblink ?omim_link ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
  FILTER(STRSTARTS(STR(?omim_link), "http://identifiers.org/mim/"))
}
LIMIT 20
```

**What Knowledge Made This Work**:
- Key Insight: OMIM links via identifiers.org/mim/ pattern
- External links use insdc:dblink property
- Performance: ~2 seconds for filtered results

**Natural Language Question Opportunities**:
1. "Which human kinase genes have OMIM disease associations?" - Category: Integration
2. "Find genes on chromosome 17 with known Mendelian disease connections" - Category: Specificity

---

### Pattern 9: Boolean Text Search

**Purpose**: Complex keyword filtering with AND/OR/NOT

**Category**: Structured Query

**Correct Approach**:
```sparql
?description bif:contains "('cancer' OR 'tumor') AND NOT 'suppressor'" option (score ?sc) .
```

**Results**: Cancer/tumor-related genes excluding tumor suppressors (CT45A5, TACSTD2, TNF, TP53, etc.)

**Natural Language Question Opportunities**:
1. "Find human genes related to cancer that are not tumor suppressors" - Category: Structured Query
2. "What oncogenes are annotated in NCBI Gene?" - Category: Specificity

---

### Pattern 10: Gene → ClinVar → Pathogenic Variants

**Purpose**: Find pathogenic variants for a specific gene

**Category**: Integration + Structured Query

**Correct Approach**: Three-way property traversal in ClinVar
```sparql
WHERE {
  GRAPH <http://rdfportal.org/dataset/ncbigene> {
    VALUES ?gene_id { "672" }
    ?ncbi_gene dct:identifier ?gene_id ;
               rdfs:label ?gene_symbol .
  }
  GRAPH <http://rdfportal.org/dataset/clinvar> {
    ?allele_bnode med2rdf:gene <http://ncbi.nlm.nih.gov/gene/672> .
    ?variant cvo:classified_record ?classrec ;
             rdfs:label ?var_label .
    ?classrec ?rel ?allele_bnode .
    ?classrec cvo:classifications ?classi .
    ?classi cvo:germline_classification ?germ .
    ?germ cvo:description ?significance .
    FILTER(?significance = "Pathogenic")
  }
}
```

**What Knowledge Made This Work**:
- Key Insight 1: Split ClinVar property paths into individual patterns
- Key Insight 2: Use VALUES for specific gene to avoid full scan
- Key Insight 3: Clinical significance accessible via nested properties
- Performance: ~3 seconds for 15 pathogenic variants

**Natural Language Question Opportunities**:
1. "What pathogenic mutations are known in BRCA1?" - Category: Precision
2. "Find all ClinVar variants classified as pathogenic for the TP53 gene" - Category: Completeness

---

## Simple Queries Performed

1. Search: "BRCA1 AND human[organism]" via ncbi_esearch
   - Found: 672 (BRCA1), 7157 (TP53), 1956 (EGFR)
   - Usage: Cross-database queries, variant associations

2. Basic gene lookup: Gene ID 1 (A1BG)
   - Found: A1BG - alpha-1-B glycoprotein, chromosome 19
   - Usage: Testing basic RDF structure

3. ID conversion: P04637 → NCBI Gene
   - Found: 7157 (TP53)
   - Usage: UniProt to gene linking

4. Human gene type distribution
   - Found: protein-coding (20,595), ncRNA (22,103), pseudo (17,483)
   - Usage: Completeness questions

5. Insulin gene search
   - Found: INS (3630), IGF1, IGF2, INSR, IRS1, etc.
   - Usage: Keyword search testing

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What genetic variants are associated with the BRCA1 gene?"
   - Databases: NCBI Gene, ClinVar
   - Knowledge Required: URI conversion (identifiers.org → ncbi.nlm.nih.gov), BIND placement, ClinVar property patterns
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

2. "Find pathogenic mutations in the TP53 tumor suppressor gene"
   - Databases: NCBI Gene, ClinVar
   - Knowledge Required: URI conversion, ClinVar clinical significance traversal
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 10

3. "What genes are discussed in Alzheimer's disease research literature?"
   - Databases: PubMed, PubTator, NCBI Gene
   - Knowledge Required: Three-database integration, bif:contains pre-filtering
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 5

4. "Find publications that mention BRCA1 and breast cancer"
   - Databases: NCBI Gene, PubMed
   - Knowledge Required: Double pre-filtering with bif:contains
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

5. "What are the mouse orthologs of human insulin-related genes?"
   - Databases: NCBI Gene (internal orthology)
   - Knowledge Required: Orthology query patterns, LIMIT requirement
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

6. "Which human kinase genes have OMIM disease associations?"
   - Databases: NCBI Gene
   - Knowledge Required: External link patterns (insdc:dblink), text search in descriptions
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 8

**Performance-Critical Questions**:

7. "How many protein-coding genes are there in human?"
   - Database: NCBI Gene
   - Knowledge Required: Organism pre-filtering (taxid), gene type filtering
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 1

8. "What types of genes are annotated for human in NCBI Gene?"
   - Database: NCBI Gene
   - Knowledge Required: Taxid filtering, GROUP BY aggregation
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

9. "Which human chromosome has the most protein-coding genes?"
   - Database: NCBI Gene
   - Knowledge Required: Chromosome filtering, aggregation with ORDER BY
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 7

10. "How many human genes on chromosome 21 have orthologs?"
    - Database: NCBI Gene
    - Knowledge Required: Chromosome + organism filtering, orthology subquery
    - Category: Completeness
    - Difficulty: Hard
    - Pattern Reference: Pattern 7

**Error-Avoidance Questions**:

11. "Find human genes related to insulin signaling"
    - Database: NCBI Gene
    - Knowledge Required: Search descriptions NOT labels, bif:contains syntax
    - Category: Precision
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

12. "Which genes have descriptions mentioning 'receptor'?"
    - Database: NCBI Gene
    - Knowledge Required: bif:contains on dct:description (not rdfs:label)
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

**Complex Filtering Questions**:

13. "Find human genes related to cancer that are not tumor suppressors"
    - Database: NCBI Gene
    - Knowledge Required: Boolean text search (AND, OR, NOT operators)
    - Category: Structured Query
    - Difficulty: Hard
    - Pattern Reference: Pattern 9

14. "What protein-coding genes on chromosome 17 have Ensembl cross-references?"
    - Database: NCBI Gene
    - Knowledge Required: Chromosome + organism + external link filtering
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 7, Pattern 8

15. "Find ncRNA genes with official nomenclature status"
    - Database: NCBI Gene
    - Knowledge Required: Gene type + nomenclatureStatus filtering
    - Category: Specificity
    - Difficulty: Medium

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the NCBI Gene ID for human BRCA1?"
   - Method: ncbi_esearch tool
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

2. "What is the official symbol for NCBI Gene 7157?"
   - Method: Basic SPARQL lookup or ncbi_esummary
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "What chromosome is the human INS gene located on?"
   - Method: Basic lookup via ncbi_esearch + esummary
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

4. "What is the UniProt ID for NCBI Gene 672?"
   - Method: togoid_convertId
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

5. "Convert UniProt P04637 to its NCBI Gene ID"
   - Method: togoid_convertId
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source**:
- → ClinVar: Via URI conversion (identifiers.org → ncbi.nlm.nih.gov)
- → UniProt: Via TogoID conversion
- → Ensembl: Via insdc:dblink cross-references
- → OMIM: Via insdc:dblink cross-references
- → PubMed: Via keyword matching (bif:contains)

**This Database as Target**:
- PubTator →: Via identifiers.org/ncbigene URIs (direct compatibility!)
- UniProt →: Via TogoID conversion

**Complex Multi-Database Paths**:
- PubMed → PubTator → NCBI Gene: Literature gene mentions with gene metadata
- NCBI Gene → ClinVar → MedGen: Gene to variants to disease concepts
- NCBI Gene → UniProt: Gene to protein function and structure

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **URI conversion patterns** - Critical for ClinVar integration
2. **Organism pre-filtering (taxid)** - Essential for any query performance
3. **Label vs Description distinction** - Prevents empty results
4. **BIND placement rule** - Must be BETWEEN GRAPH clauses
5. **PubTator URI compatibility** - Enables seamless three-way integration

### Common Pitfalls Discovered

1. Searching labels for full names (use descriptions)
2. Forgetting taxid filter (causes timeout)
3. Placing BIND inside GRAPH clause (query fails)
4. Using FILTER/CONTAINS instead of bif:contains (performance)
5. Unbounded orthology queries (timeout)

### Recommendations for Question Design

1. Focus on cross-database questions that require URI conversion knowledge
2. Include questions that test understanding of label vs description
3. Create performance-critical questions that require taxid pre-filtering
4. Design integration questions spanning NCBI endpoint databases (ClinVar, PubMed, PubTator, MedGen)

### Performance Notes

- Gene ID lookup: <1 second
- Type/chromosome filtering with taxid: 1-5 seconds
- bif:contains search: 1-3 seconds
- Cross-database (2-way): 2-5 seconds
- Cross-database (3-way): 5-10 seconds
- Orthology queries: Use LIMIT always

---

## Notes and Observations

- The shared NCBI endpoint enables powerful integrations without federated queries
- PubTator's use of identifiers.org URIs makes it the easiest cross-database partner
- ClinVar integration requires URI conversion knowledge
- The database is heavily used for human genetics but supports all organisms
- E-utilities (ncbi_esearch, esummary) complement SPARQL well for discovery

---

## Next Steps

**Recommended for Question Generation**:
- Priority: Gene-ClinVar integration (pathogenic variants)
- Priority: Three-way PubMed-PubTator-NCBI Gene integration
- Priority: Performance-critical counting queries
- Avoid: Simple lookups (E-utilities handle well without MIE)

**Focus areas this database handles well**:
- Gene-disease associations via ClinVar
- Literature mining via PubMed/PubTator
- Cross-species analysis via orthology
- Human genomics (chromosome distribution)

---

**Session Complete - Ready for Next Database**
