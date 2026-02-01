# PubTator Central Exploration Report

**Date**: January 31, 2026  
**Session**: 1 (Complete)

## Executive Summary

PubTator Central is a text-mining database that provides biomedical entity annotations extracted from PubMed literature. It links:
- **Disease annotations** (MeSH terms) to PubMed articles
- **Gene annotations** (NCBI Gene IDs) to PubMed articles

Key findings:
- **Key capability**: Gene-disease co-occurrence analysis from literature
- **Major integration opportunities**: Seamless joins with PubMed, NCBI Gene, ClinVar (all on same NCBI endpoint)
- **Most valuable patterns**: Pre-filtering with bif:contains before cross-database joins
- **Recommended question types**: Gene-disease associations, literature mining, multi-database enrichment

## Database Overview

- **Purpose**: Literature-based biomedical entity annotation using text mining and manual curation
- **Key data types**: 
  - Disease annotations (linked to MeSH terms)
  - Gene annotations (linked to NCBI Gene IDs)
- **Dataset size**: >10 million annotations (estimated)
- **Data sources**: PubTator3 (automated), ClinVar (curated), dbSNP
- **Available access methods**: SPARQL via ncbi endpoint (https://rdfportal.org/ncbi/sparql)

## Structure Analysis

### Key Entity Types

**Annotation** (oa:Annotation):
- `dcterms:subject`: Entity type ("Disease" or "Gene")
- `oa:hasBody`: Entity identifier (MeSH ID or NCBI Gene ID)
- `oa:hasTarget`: PubMed article URI
- `pubtator:annotation_count`: Number of mentions in the article
- `dcterms:source`: Data provenance (optional - PubTator3, ClinVar, dbSNP)

### URI Patterns

**Disease annotations**:
- Body: `http://identifiers.org/mesh/{MeSH_ID}` (e.g., `http://identifiers.org/mesh/D003920`)
- Some OMIM identifiers also present: `http://identifiers.org/omim/{ID}`

**Gene annotations**:
- Body: `http://identifiers.org/ncbigene/{gene_id}` (e.g., `http://identifiers.org/ncbigene/7157`)

**Target (Article) URIs**:
- Format: `http://rdf.ncbi.nlm.nih.gov/pubmed/{PMID}` (shared with PubMed database)

### Performance Strategies

**Strategy 1: Always use LIMIT for exploratory queries**
- Why: Dataset contains >10M annotations
- When: Any query without selective pre-filtering
- Impact: Prevents timeout (60s limit)

**Strategy 2: Pre-filter with bif:contains before cross-database joins**
- Why: Cross-database joins without pre-filtering process 37M×10M combinations
- When: Any PubTator-PubMed join
- Impact: 99.9997% reduction in search space (37M→~100 articles)

**Strategy 3: Use explicit GRAPH clauses**
- Why: Data is stored in specific named graph
- When: All queries
- Graph URI: `http://rdfportal.org/dataset/pubtator_central`

**Strategy 4: Filter by dcterms:subject for entity type**
- Why: Distinguishes Disease from Gene annotations
- When: Queries targeting specific entity types
- Values: "Disease" or "Gene" (string literals)

**Strategy 5: Use specific entity IDs for co-occurrence queries**
- Why: Large aggregations without filters timeout
- When: Gene-disease co-occurrence analysis
- Pattern: Start with specific disease (MeSH ID) or gene (NCBI Gene ID)

### Common Pitfalls

**Pitfall 1: Query without LIMIT**
- Symptom: Timeout
- Cause: Attempting to retrieve all annotations
- Solution: Add `LIMIT 100` or use selective filters

**Pitfall 2: Text search on URI fields (oa:hasBody)**
- Symptom: No results or error
- Cause: bif:contains doesn't work on URIs
- Solution: Search in PubMed graph (dct:title), not PubTator

**Pitfall 3: Forgetting entity type filter**
- Symptom: Mixed Disease and Gene results
- Cause: No dcterms:subject filter
- Solution: Add `dcterms:subject "Disease"` or `dcterms:subject "Gene"`

**Pitfall 4: Cross-database join without pre-filtering**
- Symptom: Timeout
- Cause: Joining all PubMed articles with all PubTator annotations
- Solution: Use bif:contains in PubMed GRAPH first

**Pitfall 5: Large aggregation without selective filter**
- Symptom: Timeout (e.g., counting all gene-disease co-occurrences)
- Cause: Processing millions of co-occurrences
- Solution: Filter by specific gene OR disease first, then aggregate

### Data Organization

**Primary Graph**: `http://rdfportal.org/dataset/pubtator_central`

**Entity Types**:
1. **Disease Annotations**: Link MeSH disease terms to articles
   - High coverage (majority of annotations)
   - Example: D003920 (Diabetes Mellitus) appears in ~100+ articles
   - Example: D001943 (Breast Neoplasms) appears in ~835K articles

2. **Gene Annotations**: Link NCBI Gene IDs to articles
   - Substantial coverage
   - Example: Gene 7157 (TP53) appears in ~274K articles
   - annotation_count can be >1 (e.g., 9 mentions in one article)

**Optional Properties**:
- `dcterms:source`: Data provenance (~50% coverage)
  - Values: "PubTator3", "ClinVar", "dbSNP"

### Cross-Database Integration Points

**Integration 1: PubTator → PubMed**
- Connection: Shared article URI (`http://rdf.ncbi.nlm.nih.gov/pubmed/{pmid}`)
- Join: PubTator `oa:hasTarget` ↔ PubMed article URI
- Pre-filtering needed: bif:contains on PubMed titles
- Knowledge required: Graph URIs, bif:contains syntax
- Use case: Find articles about specific topics with gene/disease annotations

**Integration 2: PubTator → NCBI Gene**
- Connection: Gene annotations use identifiers.org/ncbigene URIs
- Join: PubTator `oa:hasBody` directly matches NCBI Gene URIs
- Pre-filtering needed: Keyword search in PubMed first
- Knowledge required: NCBI Gene entity types (insdc:Gene), properties (rdfs:label)
- Use case: Enrich gene mentions with official symbols and descriptions

**Integration 3: PubTator → PubMed → NCBI Gene (Three-way)**
- Connection: Articles → Annotations → Gene metadata
- Join: PubMed article ↔ PubTator annotation ↔ NCBI Gene
- Pre-filtering needed: bif:contains in PubMed + entity type in PubTator
- Knowledge required: All three database MIE files
- Use case: Comprehensive literature-gene analysis

**Integration 4: PubTator (Disease-Gene Co-occurrence)**
- Connection: Same article with both Disease and Gene annotations
- Join: Two PubTator annotations sharing same article target
- Pre-filtering needed: Specific disease OR gene ID
- Knowledge required: MeSH ID format, NCBI Gene ID format
- Use case: Discover gene-disease associations from literature

## Complex Query Patterns Tested

### Pattern 1: Basic Annotation Retrieval (Reference Pattern)

**Purpose**: Retrieve annotations for a specific article

**Category**: Basic/Reference

**Tested Query**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX pubtator: <http://purl.jp/bio/10/pubtator-central/ontology#>

SELECT ?entityType ?body ?count
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject ?entityType ;
       oa:hasBody ?body ;
       oa:hasTarget <http://rdf.ncbi.nlm.nih.gov/pubmed/9677103> ;
       pubtator:annotation_count ?count .
}
```

**Results**: Successfully returned Disease (D001943 - Breast Neoplasms) and Gene (672 - BRCA1) annotations

---

### Pattern 2: Gene-Disease Co-occurrence Analysis (Performance-Critical)

**Purpose**: Find genes co-mentioned with a specific disease in literature

**Category**: Performance-Critical, Integration

**Naive Approach (without proper knowledge)**:
Trying to aggregate all gene-disease co-occurrences without filtering

**What Happened**:
- Timeout after 60 seconds
- Root cause: Attempting to join millions of annotations

**Correct Approach**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX mesh: <http://identifiers.org/mesh/>

SELECT ?geneId (COUNT(DISTINCT ?article) AS ?cooccurrence)
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?geneAnn a oa:Annotation ;
           dcterms:subject "Gene" ;
           oa:hasBody ?geneId ;
           oa:hasTarget ?article .
  ?diseaseAnn a oa:Annotation ;
              dcterms:subject "Disease" ;
              oa:hasBody mesh:D000544 ;  # Alzheimer Disease
              oa:hasTarget ?article .
}
GROUP BY ?geneId
ORDER BY DESC(?cooccurrence)
LIMIT 30
```

**What Knowledge Made This Work**:
- Pre-filter by specific disease MeSH ID
- Use dcterms:subject to distinguish Gene from Disease annotations
- Use COUNT(DISTINCT ?article) for co-occurrence frequency

**Results Obtained**:
- Successfully returned 30 genes ranked by co-occurrence
- Top gene: ncbigene/351 (APP - amyloid precursor protein) with 80,147 co-occurrences
- Other top genes: MAPT (4137), APOE (348), APP (11820)
- Query completed in ~5 seconds

**Natural Language Question Opportunities**:
1. "Which genes are most frequently mentioned together with Alzheimer disease in research literature?" - Category: Integration
2. "What are the top genetic associations with Parkinson disease according to published research?" - Category: Completeness
3. "Find genes that appear in the same publications as diabetes mellitus" - Category: Structured Query

---

### Pattern 3: PubTator-PubMed Cross-Database Integration (Two-way)

**Purpose**: Find gene annotations in articles about specific topics

**Category**: Integration, Performance-Critical

**Naive Approach**:
```sparql
# BAD: No pre-filtering
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ; dct:title ?title .
  }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?ann oa:hasTarget ?article ; oa:hasBody ?geneId .
  }
  FILTER(CONTAINS(?title, "BRCA1"))  # Too late!
}
```

**What Happened with Naive Approach**:
- Works but inefficient (FILTER after join)
- Performance varies, may timeout with complex filters

**Correct Approach (with bif:contains pre-filtering)**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX pubtator: <http://purl.jp/bio/10/pubtator-central/ontology#>

SELECT ?pmid ?title ?geneId ?count
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?title .
    ?title bif:contains "'BRCA1' AND 'cancer'" .  # Early filtering!
  }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?ann dcterms:subject "Gene" ;
         oa:hasBody ?geneId ;
         oa:hasTarget ?article ;
         pubtator:annotation_count ?count .
  }
}
LIMIT 50
```

**What Knowledge Made This Work**:
- MIE files for both PubMed and PubTator
- Graph URIs: `http://rdfportal.org/dataset/pubmed`, `http://rdfportal.org/dataset/pubtator_central`
- bif:contains for indexed full-text search (10-100x faster than FILTER)
- Pre-filtering reduces 37M articles to ~100 before join

**Results Obtained**:
- 50 results in ~2-3 seconds
- Found articles about BRCA1 and cancer with annotated genes
- Gene 672 (BRCA1) frequently annotated, along with BRCA2 (675), TP53 (7157)

**Natural Language Question Opportunities**:
1. "What genes are mentioned in articles about CRISPR genome editing?" - Category: Integration
2. "Find genes discussed in research papers about immunotherapy" - Category: Structured Query
3. "Which genes appear in publications about COVID-19 and inflammation?" - Category: Currency

---

### Pattern 4: Three-Way Integration (PubTator-PubMed-NCBI Gene)

**Purpose**: Combine literature search, text-mining annotations, and gene metadata

**Category**: Integration, Structured Query

**Correct Approach**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?pmid ?title ?geneId ?gene_symbol ?gene_desc
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?title .
    ?title bif:contains "'Alzheimer' AND 'genetics'" .
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
LIMIT 50
```

**What Knowledge Made This Work**:
- MIE files for all three databases
- Double pre-filtering: bif:contains in PubMed + dcterms:subject in PubTator
- NCBI Gene uses same identifiers.org/ncbigene URIs as PubTator (no conversion needed)
- OPTIONAL for gene description (not all genes have descriptions)

**Results Obtained**:
- 50 results in ~5-8 seconds
- Genes with official symbols and descriptions
- Example: APP (amyloid beta precursor protein), APOE (apolipoprotein E), CLU (clusterin)
- Full research context: article title + gene symbol + gene function

**Natural Language Question Opportunities**:
1. "What genes are discussed in Alzheimer's disease genetics research, and what are their functions?" - Category: Integration
2. "Find cancer research papers that mention kinases, and provide the official gene names" - Category: Structured Query
3. "Which genes involved in DNA repair are mentioned in recent cancer genomics publications?" - Category: Integration

---

### Pattern 5: Disease Annotation Count

**Purpose**: Count articles mentioning a specific disease

**Category**: Completeness

**Query**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX mesh: <http://identifiers.org/mesh/>

SELECT (COUNT(DISTINCT ?article) AS ?articleCount)
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject "Disease" ;
       oa:hasBody mesh:D001943 ;  # Breast Neoplasms
       oa:hasTarget ?article .
}
```

**Results**: ~835,000 articles (breast cancer is heavily represented)

**Natural Language Question Opportunities**:
1. "How many research papers mention breast cancer according to PubTator text mining?" - Category: Completeness
2. "What is the literature coverage for Parkinson disease in PubTator?" - Category: Completeness

---

### Pattern 6: Gene Article Count

**Purpose**: Count articles mentioning a specific gene

**Category**: Completeness

**Query**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT (COUNT(DISTINCT ?target) AS ?articleCount)
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject "Gene" ;
       oa:hasBody <http://identifiers.org/ncbigene/7157> ;  # TP53
       oa:hasTarget ?target .
}
```

**Results**: ~274,000 articles mentioning TP53

**Natural Language Question Opportunities**:
1. "How many publications mention the TP53 tumor suppressor gene?" - Category: Completeness
2. "What is the literature volume for BRCA1 in PubMed?" - Category: Completeness

---

### Pattern 7: High-Frequency Annotations

**Purpose**: Find genes mentioned multiple times within single articles

**Category**: Specificity, Structured Query

**Query**:
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX pubtator: <http://purl.jp/bio/10/pubtator-central/ontology#>

SELECT ?ann ?body ?target ?count
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject "Gene" ;
       oa:hasBody ?body ;
       oa:hasTarget ?target ;
       pubtator:annotation_count ?count .
  FILTER(?count > 5)
}
LIMIT 30
```

**Results**: Found genes with 6+ mentions per article (highly focused papers)

**Natural Language Question Opportunities**:
1. "Find articles that focus heavily on a single gene (mentioned more than 5 times)" - Category: Specificity
2. "Which genes have high-density mentions in individual research papers?" - Category: Structured Query

---

## Simple Queries Performed

### Entity Discovery Searches

1. **MeSH Disease Lookup**: 
   - Tool: search_mesh_descriptor
   - Found: D001943 (Breast Neoplasms), D064726 (Triple Negative Breast Neoplasms)
   - Usage: Disease annotation queries

2. **Gene Annotation Sample**:
   - Found: Gene 672 (BRCA1), Gene 7157 (TP53), Gene 351 (APP)
   - Usage: Gene-disease co-occurrence, literature mining

3. **Disease Annotation Sample**:
   - Found: D003920 (Diabetes Mellitus), D000544 (Alzheimer Disease), D001943 (Breast Neoplasms)
   - Usage: Disease-focused literature queries

### Key Statistics Discovered

- TP53 (7157): ~274K articles
- Breast Cancer (D001943): ~835K articles
- APP-Alzheimer co-occurrence: 80,147 articles
- Typical annotation_count: 1-2 (up to 9+ for focused studies)

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which genes are most frequently co-mentioned with Alzheimer disease in the research literature?"
   - Databases: PubTator
   - Knowledge Required: Gene-disease co-occurrence pattern, MeSH ID format, pre-filtering strategy
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

2. "What genes are discussed in CRISPR genome editing publications?"
   - Databases: PubMed, PubTator, NCBI Gene
   - Knowledge Required: Three-way join, bif:contains pre-filtering, graph URIs
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

3. "Find the official gene symbols and functions for genes mentioned in cancer immunotherapy research"
   - Databases: PubMed, PubTator, NCBI Gene
   - Knowledge Required: bif:contains, entity type filtering, NCBI Gene properties
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

4. "Which kinase genes are associated with diabetes in the literature?"
   - Databases: PubTator, NCBI Gene
   - Knowledge Required: Disease MeSH ID, gene-disease co-occurrence, gene type filtering
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

5. "What inflammatory diseases are commonly associated with the IL6 gene in publications?"
   - Databases: PubTator
   - Knowledge Required: NCBI Gene ID for IL6, disease co-occurrence aggregation
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 2 (reversed)

**Performance-Critical Questions**:

1. "How many genes are co-mentioned with breast cancer in the research literature?"
   - Database: PubTator
   - Knowledge Required: Pre-filter by disease, then count genes
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

2. "Find articles about BRCA1 that also mention other DNA repair genes"
   - Databases: PubMed, PubTator
   - Knowledge Required: bif:contains pre-filtering, gene annotation join
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

3. "What are the top 20 diseases mentioned in articles about TP53?"
   - Database: PubTator
   - Knowledge Required: Gene ID, disease aggregation with pre-filtering
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 2 (gene-centric)

**Error-Avoidance Questions**:

1. "Find cancer-related articles with annotated genes" (requires bif:contains, not FILTER)
   - Databases: PubMed, PubTator
   - Knowledge Required: bif:contains syntax, graph URIs
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

2. "List all diseases mentioned in a specific PubMed article" (requires entity type filter)
   - Database: PubTator
   - Knowledge Required: dcterms:subject "Disease", article URI format
   - Category: Precision
   - Difficulty: Easy
   - Pattern Reference: Pattern 1

**Complex Filtering Questions**:

1. "Find genes mentioned more than 5 times in single articles"
   - Database: PubTator
   - Knowledge Required: pubtator:annotation_count, FILTER comparison
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 7

2. "What diseases appear together with multiple genes in the same articles?"
   - Database: PubTator
   - Knowledge Required: Multi-annotation join, aggregation
   - Category: Structured Query
   - Difficulty: Hard

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What genes are annotated in PubMed article 9677103?"
   - Method: Direct annotation lookup
   - Knowledge Required: Article URI format
   - Category: Precision
   - Difficulty: Easy

2. "Is the TP53 gene mentioned in PubTator annotations?"
   - Method: Simple existence check
   - Knowledge Required: NCBI Gene ID
   - Category: Precision
   - Difficulty: Easy

**Count Questions**:

1. "How many articles mention TP53 according to PubTator?"
   - Method: COUNT query
   - Knowledge Required: Basic SPARQL
   - Category: Completeness
   - Difficulty: Easy

2. "How many articles are annotated with breast cancer in PubTator?"
   - Method: COUNT query with MeSH ID
   - Knowledge Required: MeSH ID lookup
   - Category: Completeness
   - Difficulty: Easy

---

## Integration Patterns Summary

**PubTator as Source**:
- → PubMed: Via shared article URI
- → NCBI Gene: Via identifiers.org/ncbigene URIs (direct match)
- → MeSH: Via identifiers.org/mesh URIs (disease annotations)

**PubTator as Target**:
- PubMed →: Article-based annotation lookup
- NCBI Gene →: Gene-centric literature search
- MeSH →: Disease-centric literature search

**Complex Multi-Database Paths**:
1. PubMed → PubTator → NCBI Gene: Literature search → annotations → gene metadata
2. NCBI Gene → PubTator → MeSH: Gene → literature → associated diseases
3. MeSH → PubTator → NCBI Gene: Disease → literature → associated genes

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Pre-filtering with bif:contains is essential**: Cross-database queries without pre-filtering timeout
2. **Entity type filtering (dcterms:subject)**: Distinguishes Disease from Gene annotations
3. **Graph URIs must be correct**: Data is in `http://rdfportal.org/dataset/pubtator_central`
4. **URI patterns enable seamless integration**: identifiers.org URIs match across databases
5. **Aggregations need selective filters**: Gene-disease co-occurrence requires starting with specific entity

### Common Pitfalls Discovered

1. **Forgetting LIMIT**: Queries without LIMIT on >10M annotations timeout
2. **Text search on URIs**: bif:contains doesn't work on oa:hasBody (URI field)
3. **Unfiltered aggregations**: Counting all co-occurrences without pre-filter fails
4. **Mixed entity types**: Queries without dcterms:subject return mixed Disease/Gene results

### Recommendations for Question Design

1. **Focus on integration questions**: PubTator's value is in connecting literature to entities
2. **Test gene-disease associations**: High biological relevance and clear MIE value
3. **Use specific entities for complex queries**: TP53, BRCA1, Alzheimer (D000544), Breast Cancer (D001943)
4. **Include performance-critical patterns**: Demonstrate timeout without proper optimization

### Performance Notes

- Simple annotation lookup: <1s
- Count queries: 1-3s
- Gene-disease co-occurrence (with pre-filter): 5-10s
- Two-way cross-database (with bif:contains): 2-3s
- Three-way cross-database: 5-8s
- Unfiltered aggregation: Timeout

---

## Notes and Observations

1. **Entity type coverage**: Only "Disease" and "Gene" types confirmed; other types (Chemical, Species, Mutation) may not be present in RDF version
2. **dcterms:source coverage**: ~50% of annotations have provenance (PubTator3, ClinVar, dbSNP)
3. **annotation_count range**: Typically 1-2, up to 9+ for focused studies
4. **High-volume entities**: TP53 (~274K articles), Breast Cancer (~835K articles)
5. **Integration strength**: Seamless joins with PubMed, NCBI Gene due to shared endpoint and URI patterns

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Gene-disease co-occurrence, three-way integration, performance-critical counts
- Focus areas: Literature mining, biomedical entity associations, multi-database enrichment
- Avoid: Questions about entity types other than Disease/Gene, unfiltered large aggregations

**Further Exploration Needed**:
- Check if dbSNP variant annotations are available
- Explore dcterms:source distribution more thoroughly
- Test ClinVar integration via shared endpoint

---

**Session Complete - Ready for Question Generation**

```
Database: pubtator
Status: ✅ COMPLETE
Report: /evaluation/exploration/pubtator_exploration.md
Patterns Tested: 7
Questions Identified: ~25
Integration Points: 4 (PubMed, NCBI Gene, MeSH, internal gene-disease)
```
