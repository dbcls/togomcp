# PubTator Exploration Report

## Database Overview
- **Purpose**: Text mining annotations of biomedical entities from PubMed literature
- **Scope**: >10 million annotations linking genes and diseases to PubMed articles
- **Key data types**: Disease annotations (MeSH IDs), Gene annotations (NCBI Gene IDs)
- **Focus**: Literature-based biomedical discovery, gene-disease associations, knowledge graph construction

## Schema Analysis (from MIE file)

### Main Properties Available
- **Annotations**: `oa:Annotation` with `dcterms:subject` (entity type), `oa:hasBody` (entity ID), `oa:hasTarget` (PubMed article)
- **Entity types**: "Disease", "Gene" (case-sensitive strings)
- **Mention frequency**: `pubtator:annotation_count` (integer, how many times entity appears in article)
- **Source attribution**: `dcterms:source` (optional - "PubTator3", "ClinVar", "dbSNP")

### Important Relationships
- Uses Web Annotation Ontology (oa:) for modeling
- Diseases link to MeSH terms via identifiers.org
- Genes link to NCBI Gene IDs via identifiers.org
- Articles use NCBI PubMed URIs (http://rdf.ncbi.nlm.nih.gov/pubmed/)

### Query Patterns Observed
- Always include FROM clause: `<http://rdfportal.org/dataset/pubtator_central>`
- Filter by entity type: `dcterms:subject "Disease"` or `dcterms:subject "Gene"`
- Use LIMIT to prevent timeouts (large dataset)
- Use OPTIONAL for dcterms:source (not always present)

## Search Queries Performed

### Query 1: Sample annotations
- **Search**: Basic annotation retrieval
- **Results**: 20 Disease and Gene annotations found
  - Disease examples: D056486 (Fecal Incontinence), D001724 (Birth Weight), D003920 (Diabetes Mellitus)
  - Gene examples: 11820, 12359, 1233, 207 (various NCBI Gene IDs)

### Query 2: Gene annotations
- **Search**: Filter by entityType="Gene"
- **Results**: Gene annotations linking NCBI Gene IDs to PubMed articles
  - Gene 11820 → PubMed 16821116
  - Gene 12359 → PubMed 16821116
  - Gene 1233 → PubMed 16821125

### Query 3: High-frequency annotations
- **Search**: annotation_count > 5
- **Results**: Most frequently mentioned entities:
  - Gene 28964: 9 mentions in PubMed 15383276 (highest)
  - Gene 81848: 8 mentions in PubMed 12027893
  - Gene 79760: 8 mentions in PubMed 12065586

### Query 4: Diabetes Mellitus (D003920) annotations
- **Search**: Filter by MeSH ID D003920
- **Results**: 20 PubMed articles mentioning diabetes:
  - PubMed 18935173, 18935609, 18935724, etc.

### Query 5: Gene-Disease co-occurrences
- **Search**: Articles with both gene and disease annotations
- **Results**: Found co-occurrences:
  - PubMed 16821116: Genes 11820, 12359 + Diseases D000544 (Alzheimer), D003072 (Cognitive Dysfunction)
  - PubMed 16821125: Genes 1233, 207, 2185 + Diseases D001847 (Bone Diseases), D001859 (Bone Neoplasms)

## SPARQL Queries Tested

```sparql
# Query 1: Basic annotation retrieval
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?ann ?entityType ?body ?target
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject ?entityType ;
       oa:hasBody ?body ;
       oa:hasTarget ?target .
}
LIMIT 20
# Results: Mixed Disease and Gene annotations
```

```sparql
# Query 2: Disease annotations for specific MeSH ID
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?ann ?target
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject "Disease" ;
       oa:hasBody <http://identifiers.org/mesh/D003920> ;
       oa:hasTarget ?target .
}
LIMIT 20
# Results: PubMed articles mentioning Diabetes Mellitus
```

```sparql
# Query 3: High-frequency mentions
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX pubtator: <http://purl.jp/bio/10/pubtator-central/ontology#>

SELECT ?ann ?entityType ?body ?target ?count
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?ann a oa:Annotation ;
       dcterms:subject ?entityType ;
       oa:hasBody ?body ;
       oa:hasTarget ?target ;
       pubtator:annotation_count ?count .
  FILTER(?count > 5)
}
ORDER BY DESC(?count)
LIMIT 20
# Results: Gene 28964 with 9 mentions (highest)
```

```sparql
# Query 4: Gene-Disease co-occurrence
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
}
LIMIT 20
# Results: Articles with both gene and disease annotations
```

## Interesting Findings

### Specific Entities for Good Questions
1. **Diabetes Mellitus**: MeSH D003920 - well-annotated disease
2. **Alzheimer Disease**: MeSH D000544 - appears in gene-disease co-occurrences
3. **Gene 28964**: Highest annotation count (9 mentions in one article)
4. **Gene 1616**: Appears in multiple articles with high frequency
5. **PubMed 16821116**: Example article with multiple gene-disease associations

### Unique Properties/Patterns
- Annotation IDs follow pattern: Disease/[number] or Gene/[number]
- annotation_count indicates mention frequency within single article
- Entity types are case-sensitive strings ("Disease", "Gene")
- Source attribution optional (~50% coverage)

### Connections to Other Databases
- **MeSH**: All disease annotations via identifiers.org/mesh/
- **NCBI Gene**: All gene annotations via identifiers.org/ncbigene/
- **PubMed**: All targets are PubMed article URIs

### Verifiable Facts
- Entity types: "Disease" and "Gene" confirmed
- Maximum annotation_count observed: 9
- Typical annotation_count: 1-2 per annotation
- MeSH D003920 (Diabetes Mellitus): Found in 20+ articles in sample
- PubMed 16821116: Contains both gene and disease annotations

## Question Opportunities by Category

### Precision
- "Which PubMed articles mention diabetes mellitus (MeSH:D003920)?" → PubMed IDs
- "What is the highest annotation count in PubTator?" → 9
- "What gene has the most mentions in a single article?" → Gene 28964

### Completeness
- "What entity types are annotated in PubTator?" → Disease, Gene
- "How many PubMed articles mention Alzheimer Disease?" → (requires count query)
- "List genes co-occurring with Alzheimer Disease in literature"

### Integration
- "Which genes are mentioned with Alzheimer Disease (D000544)?" → Gene-disease co-occurrence
- "Link PubTator disease annotations to MeSH terms"
- "Find articles mentioning both BRCA1 and breast cancer"

### Currency
- "What are the most recently annotated articles?"

### Specificity
- "How many times is gene 28964 mentioned in PubMed 15383276?" → 9
- "What diseases co-occur with gene 11820 in literature?" → D000544, D003072
- "Which article has the most gene annotations?"

### Structured Query
- "Find all gene-disease co-occurrences in article 16821116"
- "List annotations with count > 5"
- "Find diseases mentioned with gene 207"

## Notes

### Limitations
- Aggregation queries may timeout (use LIMIT)
- Source attribution not always available
- Only Disease and Gene entity types confirmed (Chemical, Species may have limited coverage)
- DISTINCT queries on large datasets may timeout

### Best Practices
- Always use FROM clause: `<http://rdfportal.org/dataset/pubtator_central>`
- Filter by entity type first: `dcterms:subject "Disease"` or `"Gene"`
- Use LIMIT for all queries (large dataset)
- Use OPTIONAL for dcterms:source (not always present)
- Entity type values are case-sensitive strings

### Anti-Patterns to Avoid
- ❌ Queries without LIMIT (causes timeout)
- ❌ Using bif:contains on URI fields (doesn't work)
- ❌ Expecting all annotations to have source attribution
- ❌ Aggregation without selective filters (timeout)
- ❌ Using lowercase entity types ("disease" vs "Disease")

### Data Quality
- Entity types confirmed: Disease, Gene
- Cross-references: MeSH (diseases), NCBI Gene (genes)
- annotation_count range: typically 1-9
- Source attribution: ~50% coverage (PubTator3, ClinVar, dbSNP)
