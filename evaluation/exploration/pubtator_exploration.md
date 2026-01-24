# PubTator Central Exploration Report

## Database Overview
- **Purpose**: Biomedical entity annotations extracted from PubMed literature using text mining and manual curation
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: http://rdfportal.org/dataset/pubtator_central
- **Key Features**: Disease and Gene annotations linked to PubMed articles, Web Annotation Ontology (oa:Annotation) model
- **Data Sources**: PubTator3 (automated), ClinVar (curated), dbSNP

## Schema Analysis (from MIE file)

### Main Entity Types
- **Disease Annotations**: Links MeSH disease terms to PubMed articles where they're mentioned
- **Gene Annotations**: Links NCBI Gene IDs to PubMed articles where they're mentioned

### Important Properties
- `dcterms:subject`: Entity type ("Disease" or "Gene")
- `oa:hasBody`: External identifier (MeSH ID for diseases, NCBI Gene ID for genes)
- `oa:hasTarget`: PubMed article URI (http://rdf.ncbi.nlm.nih.gov/pubmed/{pmid})
- `pubtator:annotation_count`: Number of times entity is mentioned in the article
- `dcterms:source`: Data provenance (PubTator3, ClinVar, dbSNP) - optional, often missing

### Query Patterns
- **CRITICAL**: Must use `FROM <http://rdfportal.org/dataset/pubtator_central>` to specify graph
- Always use LIMIT - large aggregation queries will timeout
- Filter by `dcterms:subject` to separate Disease from Gene annotations
- Cross-database queries possible with PubMed, NCBI Gene (shared NCBI endpoint)

## Search Queries Performed

### 1. Entity Type Distribution
```
Query: Count annotations by entity type
Results: 
  - Disease annotations: 162,094,545
  - Gene annotations: 72,659,393
  - Total: 234,753,938 annotations
```

### 2. Sample Disease Identifiers
```
Query: Distinct disease MeSH IDs
Results: Found diseases including:
  - D056486 (Fecal Incontinence)
  - D001724 (Birth Weight)
  - D001835 (Body Weight)
  - D003920 (Diabetes Mellitus)
  - D010146 (Pain)
  - D009369 (Neoplasms/Cancer)
  - D000544 (Alzheimer Disease)
  - C565054 (rare disease - C-prefixed supplementary concept)
  - D000740 (Anemia)
```

### 3. Sample Gene Identifiers
```
Query: Distinct gene NCBI IDs
Results: Found genes including:
  - 11820, 12359, 1233, 20299, 207 (human/mouse genes)
  - 5594 (MAPK1), 6367 (CCL2), 8600 (TNFSF11)
  - 3320 (HSP90AA1), 7193 (TOP2A)
  - 3772517 (very high ID - possibly bacterial)
```

### 4. Articles with Gene Annotations
```
Query: Find articles with gene mentions
Results: PMIDs starting with 1682xxxx (e.g., 16821116, 16821125, 16821127)
Example PMID 16821116 has:
  - Genes: 11820, 12359, 11423
  - Diseases: D000544 (Alzheimer), D003072 (Cognition Disorders)
```

### 5. High-Frequency Mention Annotations
```
Query: Annotations with count > 5
Results: Maximum annotation_count = 9
  - Gene 28964 mentioned 9 times in PMID 15383276
  - Many genes mentioned 8 times in various articles
  - Majority of annotations have count = 1 or 2
```

## SPARQL Queries Tested

### Query 1: Diseases in a Specific Article
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?diseaseId
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann dcterms:subject "Disease" ;
       oa:hasBody ?diseaseId ;
       oa:hasTarget <http://rdf.ncbi.nlm.nih.gov/pubmed/18935173> .
}
# Results: D001724 (Birth Weight), D001835 (Body Weight), D003920 (Diabetes Mellitus)
```

### Query 2: Gene-Disease Co-Mentions for Alzheimer Disease
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX mesh: <http://identifiers.org/mesh/>

SELECT DISTINCT ?geneId ?article
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?geneAnn dcterms:subject "Gene" ;
           oa:hasBody ?geneId ;
           oa:hasTarget ?article .
  ?diseaseAnn dcterms:subject "Disease" ;
              oa:hasBody mesh:D000544 ;
              oa:hasTarget ?article .
}
LIMIT 20
# Results: Found genes co-mentioned with Alzheimer (D000544):
#   348 (APOE), 1327 (COX2), 4137 (MAPT), 1622 (DBH), 
#   6620 (SNCB), 6622 (SNCA), 351 (APP), 5663 (PSEN1)
```

### Query 3: Cross-Database - PubTator + PubMed + NCBI Gene
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?pmid ?title ?geneId ?gene_symbol
FROM <http://rdfportal.org/dataset/pubtator_central>
FROM <http://rdfportal.org/dataset/pubmed>
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?ann dcterms:subject "Gene" ;
       oa:hasBody ?geneId ;
       oa:hasTarget ?article .
  ?article bibo:pmid ?pmid ;
           dct:title ?title .
  ?geneId a insdc:Gene ;
          rdfs:label ?gene_symbol .
  FILTER(?geneId = <http://identifiers.org/ncbigene/7157>)
}
LIMIT 10
# Results: TP53 (gene 7157) mentioned in articles about:
#   - p53 codon 72 polymorphism and cervical cancer (PMID 10421306)
#   - Melatonin and MCF-7 breast cancer cells (PMID 10421427)
#   - Paclitaxel sensitivity (PMID 10421546)
#   - COVID-19 susceptibility genes (PMID 34437926)
```

### Query 4: BRCA1 Literature with Article Titles
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?pmid ?title ?geneId
FROM <http://rdfportal.org/dataset/pubtator_central>
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?ann dcterms:subject "Gene" ;
       oa:hasBody ?geneId ;
       oa:hasTarget ?article .
  ?article bibo:pmid ?pmid ;
           dct:title ?title .
  FILTER(?geneId = <http://identifiers.org/ncbigene/672>)
}
LIMIT 20
# Results: BRCA1 (gene 672) in articles about:
#   - Radiation-induced breast cancers (PMID 10036974)
#   - BRCA1/BRCA2 survival in Ashkenazi Jewish carriers (PMID 10037104)
#   - BRCA1 purification from tumor cells (PMID 10052688)
#   - PARP inhibitors and synthetic lethality (PMID 24984781)
```

### Query 5: Annotation Count Distribution (Genes)
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX pubtator: <http://purl.jp/bio/10/pubtator-central/ontology#>

SELECT ?count (COUNT(*) as ?annotations)
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann dcterms:subject "Gene" ;
       pubtator:annotation_count ?count .
}
GROUP BY ?count
ORDER BY DESC(?count)
# Results:
#   count=9: 1 annotation
#   count=8: 29 annotations
#   count=7: 1,244 annotations
#   count=6: 17,626 annotations
#   count=5: 63,029 annotations
#   count=4: 699,650 annotations
#   count=3: 1,084,914 annotations
#   count=2: 2,783,711 annotations
#   count=1: 68,009,189 annotations
```

## Cross-Reference Analysis

### Entity Counts
- **MeSH diseases referenced**: Large number (100+ distinct disease IDs in sample)
- **NCBI genes referenced**: Large number (50+ distinct gene IDs in sample)
- **PubMed articles with annotations**: Millions of unique PMIDs

### Database Connections
- **PubMed**: Via `oa:hasTarget` → `http://rdf.ncbi.nlm.nih.gov/pubmed/{pmid}`
- **MeSH**: Via `oa:hasBody` for diseases → `http://identifiers.org/mesh/{id}`
- **NCBI Gene**: Via `oa:hasBody` for genes → `http://identifiers.org/ncbigene/{id}`

### Shared Endpoint (NCBI)
PubTator shares endpoint with: ClinVar, PubMed, NCBI Gene, MedGen
- Enables rich cross-database queries
- Same article URIs work across all NCBI databases
- Gene URIs compatible with NCBI Gene database

## Interesting Findings

### Key Statistics (from queries)
- **162 million disease annotations** across PubMed literature
- **72 million gene annotations** across PubMed literature
- **Annotation counts**: Majority (68M/72M for genes) have single mentions; max observed was 9 mentions in one article
- **No source attribution found**: `dcterms:source` property appears to be unpopulated in current data

### Gene-Disease Co-Mention Discovery
- Found co-mentions of known gene-disease associations:
  - Alzheimer (D000544) with APOE (348), APP (351), PSEN1 (5663), SNCA (6622)
  - Diabetes (D003920) with INS (3630), HNF1A (3105), HNF4A (3172), etc.
- Enables literature-based gene-disease association discovery

### BRCA1 Literature Coverage
- Gene 672 (BRCA1) has extensive coverage in breast/ovarian cancer literature
- Cross-database query returned articles spanning 1999-2024
- Topics include PARP inhibitors, risk assessment, survival studies

### TP53 Literature Coverage
- Gene 7157 (TP53) mentioned across diverse cancer types
- Topics include p53 polymorphisms, drug sensitivity, COVID-19 susceptibility

## Question Opportunities by Category

### Precision
- ✅ "How many disease annotations are there for PMID 18935173?" (3 diseases found)
- ✅ "What is the annotation count for gene 28964 in PMID 15383276?" (9 mentions)
- ✅ "What MeSH disease ID is most frequently annotated?" (requires aggregation)

### Completeness
- ✅ "How many total gene annotations are in PubTator?" (72,659,393)
- ✅ "How many total disease annotations are in PubTator?" (162,094,545)
- ✅ "What is the distribution of annotation counts for genes?" (1-9, mostly 1)

### Integration
- ✅ "Find articles mentioning both BRCA1 and breast cancer with article titles" (PubTator + PubMed)
- ✅ "Find gene symbols for genes co-mentioned with Alzheimer disease" (PubTator + NCBI Gene)
- ✅ "What genes are mentioned in articles about PARP inhibitors?" (requires PubMed keyword search)

### Currency
- ✅ "What recent articles mention COVID-19 susceptibility genes?" (requires filtering by date)
- ✅ "Find 2024 publications mentioning mTOR pathway genes" (date filtering)

### Specificity
- ✅ "Find articles mentioning rare disease MeSH IDs (C-prefixed concepts)"
- ✅ "What genes are co-mentioned with Erdheim-Chester disease?"
- ✅ "Find annotations for uncommon genes (very high NCBI Gene IDs)"

### Structured Query
- ✅ "Find genes co-mentioned with Diabetes Mellitus (D003920) in literature" (JOIN query)
- ✅ "Find articles where a gene is mentioned more than 5 times" (FILTER query)
- ✅ "Find gene-disease pairs co-occurring in the same article" (double JOIN)

## Notes

### Limitations
- Large aggregation queries timeout (e.g., counting unique articles or diseases)
- Source attribution (`dcterms:source`) not populated in current data
- Only Disease and Gene entity types; no Chemical, Species, or Mutation annotations
- No text/abstract content in PubTator graph (need to join with PubMed)

### Best Practices
- Always use `FROM <http://rdfportal.org/dataset/pubtator_central>` clause
- Always filter by `dcterms:subject "Disease"` or `dcterms:subject "Gene"`
- Always use LIMIT for exploratory queries
- For cross-database queries, include multiple FROM clauses
- Gene annotations use `identifiers.org/ncbigene/` URIs compatible with NCBI Gene

### Query Performance
- Simple lookups by annotation ID: Fast (<1s)
- Entity-specific queries with filters: Moderate (1-5s)
- Cross-graph queries (PubTator + PubMed): ~2-10 seconds
- Three-way integration (PubTator + PubMed + NCBI Gene): ~5-15 seconds
- Large aggregations without LIMIT: Will timeout

### Cross-Database Integration
- PubTator is powerful for literature-based discovery when combined with:
  - **PubMed**: Article metadata, abstracts, keyword search (bif:contains)
  - **NCBI Gene**: Gene symbols, descriptions, functional annotations
  - **MeSH**: Disease/concept hierarchy and relationships
  - **ClinVar**: Clinical significance of genetic variants
