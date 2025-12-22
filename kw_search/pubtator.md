# PubTator Keyword Search

## Specialized API (Use First)
PubTator annotations are linked to PubMed articles. Use PubMed search APIs to find relevant articles, then query PubTator RDF for entity annotations.

### Step 1: Search PubMed for relevant articles
**Option A: PubMed-specific API (Recommended)**
```python
PubMed:search_articles("breast cancer BRCA1", max_results=20)
```

**Option B: NCBI E-utilities**
```python
ncbi_esearch(database="pubmed", query="breast cancer BRCA1", max_results=20)
```

### Step 2: Query PubTator RDF for annotations
Use the PMIDs from Step 1 to query PubTator RDF for gene/disease annotations.

## SPARQL Query Approach
PubTator requires SPARQL queries for extracting annotations. Read MIE file first:
```python
get_MIE_file("pubtator")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `oa:hasBody` for annotated entities (genes, diseases)
- `oa:hasTarget` for linking to PubMed articles
- Entity types: Gene annotations (NCBI Gene IDs), Disease annotations (MeSH IDs)
- `pubtator:denotes_gene`, `pubtator:denotes_disease` for entity types
- Count information via `pubtator:count`

## Workflow Summary
1. Use PubMed API (`PubMed:search_articles()` or `ncbi_esearch()`) to find articles by topic
2. Extract PMIDs from search results
3. Use PubTator SPARQL to find what genes/diseases are mentioned in those articles
4. Analyze co-occurrence patterns and annotation statistics

## Notes
- PubTator is not directly searchable via keyword search API
- Always start with PubMed search to identify relevant articles
- PubTator provides entity annotations (genes, diseases, chemicals, mutations, species)
- Best for mining entity mentions and co-occurrences from literature
