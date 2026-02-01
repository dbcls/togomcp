# PubMed Exploration Report

**Date**: 2026-01-31
**Session**: 1

## Executive Summary

PubMed is a comprehensive biomedical literature database containing 38+ million citations. The database provides rich metadata including titles, abstracts, authors with affiliations, publication details, and MeSH term annotations. Key integration opportunities exist with PubTator (entity annotations), NCBI Gene (gene metadata), MeSH (vocabulary terms), and other NCBI co-located databases.

Key capabilities requiring deep knowledge:
- Cross-database queries with PubTator for gene/disease entity annotations
- bif:contains full-text search (required for performance)
- MeSH term annotation structure (multiple property types)
- Author metadata navigation through OLO ontology patterns
- Date filtering complexities with variable formats

Major integration opportunities:
- PubMed → PubTator → NCBI Gene: Three-way integration for gene-literature analysis
- PubMed + MeSH: Literature by controlled vocabulary terms
- PubMed + PubTator: Entity annotations from text mining

Most valuable patterns discovered:
- Pre-filtering with bif:contains before cross-database joins (essential)
- Understanding rdfs:seeAlso vs fabio:hasPrimarySubjectTerm for MeSH
- Author extraction through OLO ordered list ontology
- Three-way GRAPH joins with progressive filtering

Recommended question types:
- Cross-database gene-disease-literature queries
- Performance-critical keyword searches
- Author/affiliation-based queries
- MeSH term annotation queries

## Database Overview

- **Purpose**: Biomedical literature citations and metadata
- **Scope**: MEDLINE, life science journals, online books
- **Key data types**: Articles, authors, affiliations, journals, MeSH annotations
- **Dataset size**: ~39 million citations (37+ million as of documentation)
- **Access methods**: SPARQL queries via ncbi endpoint, PubMed API tools

## Structure Analysis

### Performance Strategies

**Strategy 1: Use bif:contains for text search (CRITICAL)**
- Why needed: 39M articles makes FILTER/REGEX impossible
- When to apply: All keyword searches on titles, abstracts
- Performance impact: 10-100x faster than REGEX
- Example: `?title bif:contains "'CRISPR' AND 'cancer'"` completes in 2-3s

**Strategy 2: Pre-filter within GRAPH before joins**
- Why needed: Cross-database joins multiply search space
- When to apply: All cross-database queries
- Performance impact: 99.9%+ reduction in search space
- Example: Filter PubMed to ~100 articles before PubTator join

**Strategy 3: Use explicit GRAPH clauses**
- Why needed: Shared NCBI endpoint has multiple databases
- When to apply: All cross-database queries
- Performance impact: Prevents cross-contamination

**Strategy 4: Always add LIMIT**
- Why needed: Large result sets cause timeout
- When to apply: Every exploratory query
- Performance impact: Prevents 60s timeout

**Strategy 5: Filter by PMID for author queries**
- Why needed: Author lists span entire database
- When to apply: When extracting author information
- Performance impact: Must start with specific article(s)

### Common Pitfalls

**Error 1: Query timeout on full dataset**
- Cause: Attempting to count or aggregate 39M articles
- Symptoms: 60s timeout
- Solution: Use LIMIT, sampling with FILTER(?pmid < "10000")
- Example: Count queries always timeout without filtering

**Error 2: Using REGEX instead of bif:contains**
- Cause: Natural approach without MIE knowledge
- Symptoms: Very slow or timeout
- Solution: `?title bif:contains "'keyword'"` with single quotes
- Example before: `FILTER(REGEX(?title, "cancer", "i"))`
- Example after: `?title bif:contains "'cancer'"`

**Error 3: Cross-database filter after join**
- Cause: FILTER(CONTAINS()) placed outside GRAPH
- Symptoms: 370 trillion intermediate results → timeout
- Solution: Pre-filter with bif:contains inside GRAPH
- Example: Move keyword filter INTO PubMed GRAPH block

**Error 4: Empty results for MeSH term queries**
- Cause: Wrong MeSH ID or property
- Symptoms: Empty results for valid-looking queries
- Solution: Search by keyword first to discover actual MeSH terms in use
- Example: D016428 is "Journal Article", not "Alzheimer Disease"

**Error 5: Wrong date format assumptions**
- Cause: Dates stored as gYearMonth, date, or string
- Symptoms: Date comparisons fail
- Solution: Use STR() and STRSTARTS for date ranges
- Example: `FILTER(STRSTARTS(STR(?issued), "2024"))`

### Data Organization

**Article Data Section**
- Purpose: Core publication metadata
- Content: PMID, title, abstract, publication date, DOI
- Usage: Primary entity for all queries

**Author Data Section**
- Purpose: Author information with institutional affiliations
- Content: Ordered author lists using OLO ontology
- Usage: Requires OLO slot/index navigation
- Note: ~60% have affiliations

**MeSH Annotations Section**
- Purpose: Controlled vocabulary subject indexing
- Content: Multiple property types for different annotation levels
- Properties:
  - `rdfs:seeAlso`: General MeSH term links (descriptors, supplementary concepts)
  - `fabio:hasPrimarySubjectTerm`: Major topics (descriptor-qualifier pairs)
  - `fabio:hasSubjectTerm`: Supporting concepts (descriptor-qualifier pairs)
- Note: Descriptor-qualifier format is `D######Q######` (e.g., D000544Q000235)

**Journal Data Section**
- Purpose: Publication venue information
- Content: Journal name, ISSN, NLM ID, volume, issue, pages
- Usage: Filtering by journal name possible

### Cross-Database Integration Points

**Integration 1: PubMed → PubTator**
- Connection relationship: Shared article URI
- Join point: `http://rdf.ncbi.nlm.nih.gov/pubmed/{pmid}` (identical in both)
- Required from each:
  - PubMed: Article metadata (pmid, title)
  - PubTator: Entity annotations (Gene, Disease)
- Pre-filtering needed: bif:contains in PubMed GRAPH (essential)
- Knowledge required:
  - PubTator entity types: `dcterms:subject "Gene"` or `dcterms:subject "Disease"`
  - PubTator properties: `oa:hasBody`, `oa:hasTarget`
- Performance: Tier 1 (1-3s) with pre-filtering

**Integration 2: PubMed → PubTator → NCBI Gene**
- Three-way integration for gene metadata enrichment
- Connection chain: PubMed article → PubTator annotation → NCBI Gene metadata
- Join points:
  - PubMed ↔ PubTator: Shared article URI
  - PubTator ↔ NCBI Gene: `http://identifiers.org/ncbigene/{id}`
- Required from each:
  - PubMed: Article metadata
  - PubTator: Gene annotations
  - NCBI Gene: Gene symbols, descriptions
- Pre-filtering needed: Double pre-filter (bif:contains in PubMed + entity type in PubTator)
- Knowledge required:
  - NCBI Gene entity type: `insdc:Gene`
  - NCBI Gene properties: `rdfs:label` (symbol), `dct:description`
- Performance: Tier 2 (5-8s) with double pre-filtering

**Integration 3: PubMed + MeSH (Indirect)**
- Note: MeSH and PubMed are on DIFFERENT endpoints
- MeSH: `https://rdfportal.org/primary/sparql`
- PubMed: `https://rdfportal.org/ncbi/sparql`
- Integration approach: Extract MeSH IDs from PubMed, then query MeSH separately
- MeSH ID format in PubMed: `http://id.nlm.nih.gov/mesh/D######`

**Integration 4: PubMed + ClinVar**
- Not directly linked, but both on NCBI endpoint
- Potential via gene-based linkage through PubTator

## Complex Query Patterns Tested

### Pattern 1: Cross-Database Gene Annotation Integration

**Purpose**: Find genes mentioned in articles about specific topics

**Category**: Cross-Database, Integration

**Naive Approach (without proper knowledge)**:
```sparql
# BAD: No pre-filter, processes 37M × 10M join
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?title .
  }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?ann oa:hasTarget ?article ;
         oa:hasBody ?geneId .
  }
  FILTER(CONTAINS(?title, "BRCA1"))
}
```

**What Happened**:
- Error: Timeout after 60 seconds
- Why: Processes 37M articles × 10M annotations = 370 trillion intermediate results

**Correct Approach (using proper pattern)**:
```sparql
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?title .
    ?title bif:contains "'BRCA1'" .  # Early filtering!
  }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?ann dcterms:subject "Gene" ;
         oa:hasBody ?geneId ;
         oa:hasTarget ?article .
  }
}
LIMIT 50
```

**What Knowledge Made This Work**:
- Key Insights:
  - bif:contains provides indexed full-text search
  - Pre-filter WITHIN source GRAPH before join
  - PubTator properties: dcterms:subject, oa:hasBody, oa:hasTarget
- Performance improvement: ~2 seconds vs timeout
- Why it works: Reduces 37M to ~100 articles BEFORE join

**Results Obtained**:
- Number of results: 50 (limited)
- Sample results:
  - PMID 7866981: "Loss of heterozygosity of the BRCA1..." - Gene: 672 (BRCA1)
  - PMID 8173065: "Molecular cloning of BRCA1..." - Gene: 672 (BRCA1)
- Data quality: Good linkage between articles and gene mentions

**Natural Language Question Opportunities**:
1. "Which genes are mentioned in research articles about BRCA1 and cancer?" - Category: Integration
2. "What genes have been studied in connection with Alzheimer's disease in the literature?" - Category: Integration, Structured Query
3. "Find research articles that discuss both the TP53 gene and its role in cancer" - Category: Structured Query

---

### Pattern 2: Three-Way Integration (PubMed → PubTator → NCBI Gene)

**Purpose**: Get gene symbols for genes mentioned in articles

**Category**: Advanced Cross-Database, Integration

**Naive Approach**:
```sparql
# Attempt to join three databases without optimization
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> { ... }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> { ... }
  GRAPH <http://rdfportal.org/dataset/ncbigene> { ... }
}
```

**What Happened**:
- Error: Timeout or slow performance
- Why: Three-way join without pre-filtering

**Correct Approach**:
```sparql
WHERE {
  GRAPH <http://rdfportal.org/dataset/pubmed> {
    ?article bibo:pmid ?pmid ;
             dct:title ?title .
    ?title bif:contains "'Alzheimer' AND 'amyloid'" .
  }
  GRAPH <http://rdfportal.org/dataset/pubtator_central> {
    ?ann dcterms:subject "Gene" ;
         oa:hasBody ?geneId ;
         oa:hasTarget ?article .
  }
  GRAPH <http://rdfportal.org/dataset/ncbigene> {
    ?geneId a insdc:Gene ;
            rdfs:label ?gene_symbol .
  }
}
LIMIT 20
```

**What Knowledge Made This Work**:
- Key Insights:
  - Double pre-filtering (bif:contains in PubMed)
  - PubTator uses identifiers.org URIs directly compatible with NCBI Gene
  - NCBI Gene entity type: insdc:Gene
- Performance: ~5-8 seconds for 20 results

**Results Obtained**:
- Sample results:
  - PMID 1465181: "Acetylcholinesterase..." - Gene symbol: CHAT
  - PMID 1671712: "Segregation of a missense mutation..." - Gene symbol: App
- Data quality: Good enrichment with official gene symbols

**Natural Language Question Opportunities**:
1. "What genes are discussed in research about Alzheimer's disease and amyloid?" - Category: Integration
2. "Find the official gene symbols for genes mentioned in CRISPR gene editing research" - Category: Integration, Completeness
3. "Which human genes appear in literature about COVID-19 treatment?" - Category: Integration, Currency

---

### Pattern 3: Keyword Search with bif:contains

**Purpose**: Find recent articles about specific topics

**Category**: Performance-Critical, Structured Query

**Naive Approach**:
```sparql
# BAD: FILTER REGEX on 39M articles
WHERE {
  ?article dct:title ?title .
  FILTER(REGEX(?title, "cancer.*screening", "i"))
}
```

**What Happened**:
- Error: Timeout
- Why: REGEX not indexed, scans all 39M titles

**Correct Approach**:
```sparql
WHERE {
  ?article bibo:pmid ?pmid ;
           dct:title ?title ;
           dct:issued ?issued .
  ?title bif:contains "'cancer' AND 'screening'" .
}
ORDER BY DESC(?issued)
LIMIT 20
```

**What Knowledge Made This Work**:
- bif:contains uses Virtuoso's indexed full-text search
- Boolean operators: AND, OR, single quotes around terms
- Performance: ~2-3 seconds for 20 results

**Results Obtained**:
- Sample results for "CRISPR AND cancer":
  - PMID 40157335: "Comprehensive strategies for constructing efficient CRISPR/Cas..." (2025-07)
  - PMID 40300704: "Gasdermin E as a potential target..." (2025-07)

**Natural Language Question Opportunities**:
1. "What are the most recent research articles about CRISPR and cancer?" - Category: Currency
2. "Find publications discussing COVID-19 vaccines from 2024" - Category: Currency, Structured Query
3. "What literature exists on machine learning applications in drug discovery?" - Category: Structured Query

---

### Pattern 4: Author and Affiliation Extraction

**Purpose**: Find papers by authors from specific institutions

**Category**: Structured Query, Completeness

**Naive Approach**:
```sparql
# BAD: Starts from all authors
SELECT ?author_name
WHERE {
  ?creator olo:slot/olo:item ?author .
  ?author foaf:name ?author_name .
}
```

**What Happened**:
- Error: Timeout or millions of results
- Why: No article filtering first

**Correct Approach**:
```sparql
WHERE {
  ?article bibo:pmid ?pmid ;
           dct:title ?title ;
           dct:creator ?creator .
  ?creator olo:slot ?slot .
  ?slot olo:item ?author .
  ?author foaf:name ?author_name ;
          org:memberOf ?affiliation .
  ?affiliation bif:contains "'RIKEN'" .
}
LIMIT 20
```

**What Knowledge Made This Work**:
- OLO (Ordered List Ontology) structure: creator → slot → item → author
- Author properties: foaf:name, org:memberOf (optional)
- bif:contains on affiliation text works

**Results Obtained**:
- Sample results:
  - PMID 2026459: "MHC gene Q8/9d..." - Author: Nakayama K (RIKEN)
  - PMID 7568969: "[Mechanisms of the recognition...]" - Author: Kurumizaka H (RIKEN)

**Natural Language Question Opportunities**:
1. "Find publications from researchers at RIKEN institute" - Category: Structured Query
2. "What papers have been published by scientists affiliated with Harvard Medical School?" - Category: Completeness
3. "List recent publications from researchers at the National Institutes of Health" - Category: Currency, Structured Query

---

### Pattern 5: MeSH Term Annotation Queries

**Purpose**: Find articles annotated with specific MeSH terms

**Category**: Structured Query, Specificity

**Naive Approach**:
```sparql
# BAD: Wrong MeSH ID format or property
WHERE {
  ?article rdfs:seeAlso mesh:D016428 .  # This is "Journal Article"!
}
```

**What Happened**:
- Returns general articles, not disease-specific ones
- Why: D016428 is "Journal Article" publication type, not a disease

**Correct Approach**:
First, discover what MeSH terms are used:
```sparql
WHERE {
  ?article bibo:pmid ?pmid ;
           dct:title ?title ;
           rdfs:seeAlso ?mesh_term .
  ?title bif:contains "'Alzheimer'" .
  FILTER(STRSTARTS(STR(?mesh_term), "http://id.nlm.nih.gov/mesh/"))
}
LIMIT 20
```

Or use fabio:hasPrimarySubjectTerm for major subjects:
```sparql
WHERE {
  ?article bibo:pmid ?pmid ;
           fabio:hasPrimarySubjectTerm ?primary_term .
  ?title bif:contains "'Alzheimer'" .
}
```

**What Knowledge Made This Work**:
- Multiple MeSH annotation properties:
  - rdfs:seeAlso: All MeSH terms (descriptors, supplementary concepts, publication types)
  - fabio:hasPrimarySubjectTerm: Major subjects with descriptor-qualifier pairs
  - fabio:hasSubjectTerm: Supporting subjects
- Descriptor-qualifier format: D000544Q000378 = Alzheimer Disease + metabolism

**Results Obtained**:
- MeSH terms found for Alzheimer articles:
  - D000544 (Alzheimer Disease) with qualifiers
  - D003704 (Dementia) with qualifiers
  - D016428 (Journal Article) - publication type

**Natural Language Question Opportunities**:
1. "What MeSH terms are commonly used to annotate diabetes research articles?" - Category: Specificity
2. "Find articles indexed with the MeSH term for Parkinson's disease" - Category: Precision
3. "Which articles have primary subject annotations for breast cancer genetics?" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "BRCA1 breast cancer"
   - Found: PMIDs 41612657, 41608012, etc.
   - Usage: Cancer genetics questions

2. Search: "Alzheimer amyloid"
   - Found: PMIDs 1465181, 1671712, 1555768, etc.
   - Usage: Neurodegenerative disease questions

3. Search: "CRISPR cancer"
   - Found: PMIDs 40157335, 40300704, 40315964 (recent, 2025)
   - Usage: Currency questions, gene editing research

4. Search: Article PMID 31558841
   - Found: Alcohol metabolism genetics paper
   - Authors with affiliations: RIKEN, Osaka University, etc.
   - Usage: Author affiliation questions

5. Search: MeSH terms in Alzheimer articles
   - Found: D000544 (Alzheimer Disease), D003704 (Dementia)
   - Usage: MeSH annotation questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which genes are most frequently mentioned in research articles about Alzheimer's disease?"
   - Databases involved: PubMed, PubTator, NCBI Gene
   - Knowledge Required: Three-way GRAPH joins, bif:contains pre-filtering, PubTator entity types, NCBI Gene properties
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

2. "What genes are discussed in the literature about diabetes and insulin resistance?"
   - Databases involved: PubMed, PubTator, NCBI Gene
   - Knowledge Required: Cross-database joins, keyword search optimization
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 1, 2

3. "Find research articles that mention both BRCA1 and BRCA2 genes and identify the diseases discussed in those papers"
   - Databases involved: PubMed, PubTator (Gene and Disease)
   - Knowledge Required: Multi-entity PubTator queries, bif:contains
   - Category: Integration, Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

4. "What human kinase genes have been studied in cancer research in the past two years?"
   - Databases involved: PubMed, PubTator, NCBI Gene
   - Knowledge Required: Date filtering, gene type filtering, cross-database joins
   - Category: Integration, Currency
   - Difficulty: Hard
   - Pattern Reference: Pattern 2, 3

5. "Which diseases co-occur with cardiovascular disease in PubMed research articles?"
   - Databases involved: PubMed, PubTator
   - Knowledge Required: Disease co-occurrence queries, PubTator patterns
   - Category: Integration, Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

**Performance-Critical Questions**:

1. "How many research articles discuss CRISPR gene editing technology?"
   - Database: PubMed
   - Knowledge Required: bif:contains for counting (not full scan)
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

2. "What are the most recent publications about mRNA vaccine development?"
   - Database: PubMed
   - Knowledge Required: bif:contains, date ordering, LIMIT
   - Category: Currency, Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

3. "Find all articles published in Nature journals about artificial intelligence in healthcare"
   - Database: PubMed
   - Knowledge Required: Journal filtering, keyword search, proper FILTER ordering
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

**Error-Avoidance Questions**:

1. "Find articles about diabetes mellitus that have primary MeSH subject annotations"
   - Database: PubMed
   - Knowledge Required: fabio:hasPrimarySubjectTerm property (not rdfs:seeAlso alone)
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

2. "What is the MeSH descriptor-qualifier format for articles about Alzheimer's disease genetics?"
   - Database: PubMed
   - Knowledge Required: MeSH annotation structure (D######Q######)
   - Category: Specificity
   - Difficulty: Hard
   - Pattern Reference: Pattern 5

**Complex Filtering Questions**:

1. "Find publications from researchers at Harvard with 'MIT' co-authors"
   - Database: PubMed
   - Knowledge Required: OLO author structure, multiple affiliation filters
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

2. "What articles published in 2024 discuss immunotherapy for lung cancer?"
   - Database: PubMed
   - Knowledge Required: Date filtering with string operations, keyword combination
   - Category: Currency, Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

3. "Find review articles about machine learning in drug discovery"
   - Database: PubMed
   - Knowledge Required: Publication type filtering (if available), keyword search
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the PubMed ID for the seminal paper on CRISPR-Cas9 gene editing by Doudna and Charpentier?"
   - Method: PubMed search API
   - Knowledge Required: None (straightforward)
   - Category: Precision
   - Difficulty: Easy

2. "How many articles are indexed in PubMed about COVID-19?"
   - Method: PubMed search API with count
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy

3. "What are the keywords associated with PubMed article 35486828?"
   - Method: get_article_metadata API
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

1. "Convert PubMed ID 35486828 to its DOI"
   - Method: convert_article_ids or get_article_metadata
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

2. "Does PubMed article 35486828 have a full-text version in PubMed Central?"
   - Method: convert_article_ids with pmcid check
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**PubMed as Source**:
- → PubTator: Direct URI linkage (http://rdf.ncbi.nlm.nih.gov/pubmed/{pmid})
- → MeSH: MeSH IDs embedded in article metadata

**PubMed as Target**:
- Literature reference from virtually any biomedical database
- PubTator annotations point back to PubMed articles

**Complex Multi-Database Paths**:
- PubMed → PubTator → NCBI Gene: Literature-to-gene enrichment
- PubMed → PubTator (Disease) → MedGen: Literature-to-disease concepts (potential)
- PubMed → ClinVar (via genes): Literature supporting variant interpretation

---

## Lessons Learned

### What Knowledge is Most Valuable
1. bif:contains syntax is ESSENTIAL - queries fail without it
2. Pre-filtering within GRAPH before joins prevents timeout
3. PubTator entity types and properties (dcterms:subject, oa:hasBody, oa:hasTarget)
4. MeSH annotation property differences (rdfs:seeAlso vs fabio:hasPrimarySubjectTerm)
5. OLO ontology pattern for author extraction

### Common Pitfalls Discovered
1. MeSH term D016428 is "Journal Article", not a disease - must verify MeSH IDs
2. FILTER after cross-database join = timeout
3. Author queries without article filtering = timeout
4. Date formats vary - use string operations for filtering

### Recommendations for Question Design
1. Cross-database questions demonstrate clear MIE value
2. Keyword search questions must require bif:contains optimization
3. Author/affiliation questions show OLO pattern knowledge
4. MeSH annotation questions reveal property understanding

### Performance Notes
- Single article lookups: <1 second
- Keyword search (20 results): 2-3 seconds with bif:contains
- Two-database joins: 2-5 seconds with pre-filtering
- Three-database joins: 5-8 seconds with double pre-filtering
- Unoptimized cross-database: Timeout (60s)

---

## Notes and Observations

1. PubMed and MeSH are on DIFFERENT SPARQL endpoints (ncbi vs primary)
2. PubTator uses Web Annotation Ontology (oa:Annotation)
3. Gene annotations use identifiers.org URIs matching NCBI Gene
4. Disease annotations use identifiers.org/mesh/ URIs
5. ~85% of articles have abstracts, ~70% have DOIs, ~60% of authors have affiliations
6. Future publication dates appear for articles "in press"

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database gene-literature queries, bif:contains optimization, MeSH annotation queries
- Avoid: Simple PubMed searches (use API instead), MeSH endpoint joins (different endpoints)
- Focus areas: Three-way integration patterns, author affiliation queries, MeSH term structure

**Further Exploration Needed** (if any):
- MeSH endpoint queries for vocabulary navigation
- ClinVar integration via gene linkage
- PubTator disease annotation patterns

---

**Session Complete - Ready for Next Database**
