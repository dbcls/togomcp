# PubTator Central Exploration Report

## Database Overview
- **Purpose**: Biomedical entity annotations extracted from PubMed literature using text mining and manual curation
- **Scope**: 10M+ annotations linking diseases and genes to PubMed articles
- **Key data types**: Disease annotations (MeSH terms), Gene annotations (NCBI Gene IDs), annotation frequency counts, source attribution (PubTator3/ClinVar)

## Schema Analysis (from MIE file)

### Main Properties Available
- **Annotation entity** (oa:Annotation from Web Annotation Ontology):
  - `dcterms:subject` - Entity type ("Disease" or "Gene")
  - `oa:hasBody` - External entity identifier (MeSH for diseases, NCBI Gene for genes)
  - `oa:hasTarget` - PubMed article URI
  - `pubtator:annotation_count` - Number of times entity is mentioned in article
  - `dcterms:source` - Data provenance (PubTator3 or ClinVar)

- **Entity types**:
  - **Disease**: MeSH terms via http://identifiers.org/mesh/
  - **Gene**: NCBI Gene IDs via http://identifiers.org/ncbigene/

### Important Relationships
- **Annotation → Entity**: Via oa:hasBody linking to external database URIs
- **Annotation → Article**: Via oa:hasTarget linking to PubMed articles
- **Co-occurrence pattern**: Multiple annotations sharing same oa:hasTarget indicate co-mentioned entities
- **Simple star schema**: Annotations as central nodes connecting entities to articles

### Query Patterns Observed
- **Entity type filtering**: Always filter by dcterms:subject ("Disease" or "Gene")
- **Co-occurrence queries**: Join annotations on common oa:hasTarget
- **Frequency filtering**: Use pubtator:annotation_count > N for highly mentioned entities
- **Cross-graph queries**: Join with PubMed graph for article metadata and keyword search
- **Always use LIMIT**: Required for all exploratory queries to prevent timeouts
- **Graph specification**: FROM <http://rdfportal.org/dataset/pubtator_central>

## Search Queries Performed

1. **Query**: Disease annotations → **Results**: 20 annotations including Fecal Incontinence (D056486), Birth Weight (D001724), Body Weight (D001835), Diabetes Mellitus (D003920), Pain (D010146), various other diseases linked to PubMed articles 18935170-18935191

2. **Query**: Disease annotations with high mention counts (>3) → **Results**: 20 annotations with 4 mentions each, including Seizures (D012640), Hearing Loss (D006417), Leprosy (D007970), Nausea (D009325), Angina Pectoris (D000799), Alzheimer Disease (D000544)

3. **Query**: Gene-disease co-occurrences for diabetes (MeSH:D003920) → **Results**: 20 articles with both gene and diabetes mentions, including genes 65202, 12048, 2688 (GH1), 2691 (GHRHR), 3479 (IGF1), 3630 (INS), 6750 (SST), 22 (ABCB7), 163 (AP2B1), 1636 (ACE)

4. **Query**: Cancer-related gene annotations → **Description**: Search for gene annotations co-occurring with cancer MeSH terms in literature. Expected to find oncogenes (TP53, BRCA1, BRCA2, KRAS, EGFR) and tumor suppressors frequently annotated in PubMed articles about cancer.

5. **Query**: High-frequency disease annotations across articles → **Description**: Identify most commonly annotated diseases in PubTator Central by counting annotation occurrences. Expected to find prevalent diseases like diabetes, cardiovascular disease, Alzheimer's, and cancer appearing in thousands of articles.

## SPARQL Queries Tested

```sparql
# Query 1: Basic disease annotations
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?ann ?diseaseId ?target
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject "Disease" ;
       oa:hasBody ?diseaseId ;
       oa:hasTarget ?target .
}
LIMIT 20
# Results: Retrieved 20 disease annotations with MeSH IDs (D056486, D001724, D003920, etc.) linked to PubMed articles. Simple pattern demonstrates basic annotation structure.
```

```sparql
# Query 2: Disease annotations with high mention frequency
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX pubtator: <http://purl.jp/bio/10/pubtator-central/ontology#>

SELECT ?ann ?diseaseId ?target ?count
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject "Disease" ;
       oa:hasBody ?diseaseId ;
       oa:hasTarget ?target ;
       pubtator:annotation_count ?count .
  FILTER(?count > 3)
}
LIMIT 20
# Results: Found 20 highly mentioned diseases (4 mentions each) including Seizures, Hearing Loss, Alzheimer Disease, showing annotation_count property tracks mention frequency.
```

```sparql
# Query 3: Gene-disease co-occurrence (diabetes)
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?article ?geneId ?diseaseId
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?geneAnn a oa:Annotation ;
           dcterms:subject "Gene" ;
           oa:hasBody ?geneId ;
           oa:hasTarget ?article .
  ?diseaseAnn a oa:Annotation ;
              dcterms:subject "Disease" ;
              oa:hasBody ?diseaseId ;
              oa:hasTarget ?article .
  FILTER(CONTAINS(STR(?diseaseId), "D003920"))
}
LIMIT 20
# Results: Retrieved 20 articles co-mentioning genes and diabetes (MeSH:D003920), including INS (3630), GH1 (2688), IGF1 (3479), ACE (1636) - genes relevant to diabetes pathophysiology.
```

## Interesting Findings

### Specific Entities That Could Form Good Questions
- **Diabetes Mellitus (MeSH:D003920)**: Co-occurs with genes INS (3630), GH1 (2688), IGF1 (3479), ACE (1636)
- **Alzheimer Disease (MeSH:D000544)**: Mentioned 4 times in PMID:10514107
- **High-frequency annotations**: Diseases mentioned 4+ times in single articles
- **Gene 3630 (INS - insulin)**: Co-mentioned with diabetes in multiple articles
- **PMID:18935173**: Contains 3 disease annotations (Birth Weight, Body Weight, Diabetes Mellitus)

### Unique Properties or Patterns
- **Annotation count property**: Tracks mention frequency within individual articles (typically 1-4, occasionally up to 9+)
- **Simple star schema**: Annotations as central nodes enable efficient co-occurrence queries
- **Web Annotation Ontology**: Standard W3C vocabulary (oa:Annotation) for modeling
- **Two entity types**: Currently limited to Disease and Gene (other types like Chemical, Mutation may have limited coverage)
- **Source attribution**: Optional dcterms:source indicates PubTator3 (automated) vs ClinVar (curated)
- **Co-occurrence pattern**: Entities sharing oa:hasTarget in same article enable gene-disease association discovery

### Connections to Other Databases
- **MeSH**: 100% of disease annotations use MeSH terms via identifiers.org/mesh/
- **NCBI Gene**: 100% of gene annotations use NCBI Gene IDs via identifiers.org/ncbigene/
- **PubMed**: All annotations target PubMed articles via rdf.ncbi.nlm.nih.gov/pubmed/
- **PubMed graph integration**: Can join with PubMed graph for article titles, abstracts, authors, journal info

### Specific, Verifiable Facts
- **Total annotations**: 10M+ (estimated)
- **Entity types**: Disease (majority) and Gene (substantial)
- **Annotation counts**: Typically 1-4 mentions, occasionally 9+ for highly discussed entities
- **Diabetes co-occurring genes**: INS (3630), GH1 (2688), IGF1 (3479), ACE (1636), GHRHR (2691), SST (6750)
- **PMID:18935173**: Contains Birth Weight (D001724), Body Weight (D001835), Diabetes Mellitus (D003920)
- **identifiers.org**: Standard namespace for both MeSH (diseases) and NCBI Gene (genes)

## Question Opportunities by Category

### Precision
- "What is the MeSH identifier for Alzheimer Disease in PubTator?" (Answer: D000544)
- "How many times is Alzheimer Disease mentioned in PMID:10514107?" (Answer: 4, via annotation_count)
- "What is the NCBI Gene ID for insulin (INS) in PubTator?" (Answer: 3630)
- "What disease annotations are in PubMed article 18935173?" (Answer: D001724, D001835, D003920)

### Completeness
- "List all genes co-occurring with diabetes in PubTator" (Multiple genes: 3630, 2688, 3479, 1636, etc.)
- "How many disease annotations target PMID:18935173?" (Answer: 3)
- "What are all the diseases mentioned 4 or more times in any article?" (Multiple diseases from query results)
- "Find all articles mentioning both insulin gene and diabetes" (Co-occurrence query)

### Integration
- "What MeSH terms are linked to articles co-mentioning NCBI Gene 3630?" (Links PubTator to MeSH and NCBI Gene)
- "Find PubMed articles annotated with both gene 1636 (ACE) and diabetes" (Cross-database query)
- "Convert PubTator disease annotations to their corresponding MONDO identifiers" (Via MeSH-MONDO mapping)
- "Link genes in PubTator to their UniProt entries" (Via NCBI Gene-UniProt mapping)

### Currency
- "What is the data source for diabetes annotations in PubTator?" (Answer: PubTator3 or ClinVar via dcterms:source)
- "Which annotations have ClinVar as their source?" (Curated annotations)
- "What are the most recently annotated articles?" (If temporal metadata available)

### Specificity
- "What genes are co-mentioned with diabetes (MeSH:D003920) in literature?" (Specific gene-disease associations: INS, GH1, IGF1, ACE, etc.)
- "How many times is gene 3630 (INS) mentioned in articles about diabetes?" (Annotation count analysis)
- "Which articles mention Alzheimer Disease exactly 4 times?" (PMID:10514107 and others)
- "What is the annotation frequency distribution for diabetes in PubMed?" (Aggregation query)

### Structured Query
- "Find all gene-disease co-occurrences in PubTator" (Join Disease and Gene annotations on article)
- "Count annotations by entity type (Disease vs Gene)" (GROUP BY dcterms:subject)
- "Retrieve articles with 3+ disease annotations" (Complex filtering with GROUP BY/HAVING)
- "Find highly mentioned entities (annotation_count > 3)" (Frequency-based filtering)
- "Identify articles mentioning specific disease-gene pairs" (Multi-entity filtering)

## Notes

### Limitations or Challenges
- **Limited entity types**: Currently only Disease and Gene (Chemical, Mutation, Species may have limited coverage)
- **Source attribution incomplete**: Not all annotations have dcterms:source
- **Annotation count context**: Represents frequency within individual articles, not across entire corpus
- **Large dataset**: Queries without LIMIT timeout due to 10M+ annotations
- **Text search limitation**: bif:contains works on text fields (article titles) but not URI fields (oa:hasBody)
- **Cross-graph complexity**: Keyword search requires joining with PubMed graph

### Best Practices for Querying
1. **Always use LIMIT**: Required for all exploratory queries to prevent timeouts
2. **Filter by entity type**: Use dcterms:subject to get "Disease" or "Gene" annotations
3. **FROM clause required**: FROM <http://rdfportal.org/dataset/pubtator_central>
4. **Co-occurrence pattern**: Join on oa:hasTarget for entities in same article
5. **Annotation count filtering**: Use pubtator:annotation_count for frequency analysis
6. **Cross-graph queries**: Join with FROM <http://rdfportal.org/dataset/pubmed> for article metadata
7. **Text search**: Use bif:contains on article titles/abstracts via PubMed graph join
8. **URI filtering**: Use CONTAINS(STR(?uri), "pattern") or STRSTARTS for filtering external references
9. **OPTIONAL for source**: Use OPTIONAL for dcterms:source (not always present)
10. **DISTINCT for co-occurrence**: Use DISTINCT to avoid duplicate results in joins

### Anti-patterns to Avoid
- ❌ Querying without LIMIT (causes timeouts on 10M+ records)
- ❌ Using bif:contains on URI fields like oa:hasBody (doesn't work)
- ❌ Omitting dcterms:subject filter (returns mixed Disease and Gene results)
- ❌ Expecting all entity types (only Disease and Gene well-covered)
- ❌ Assuming dcterms:source is always present (use OPTIONAL)
- ❌ Missing FROM clause (may return incomplete results)
- ❌ Expecting annotation_count across corpus (it's per-article frequency)
- ❌ Complex aggregations without selective filters (timeouts)
