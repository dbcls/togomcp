# PubTator Keyword Search

## Specialized API (Use First)
PubTator annotations are linked to PubMed articles. Use `PubMed:search_articles()` to find relevant articles, then query PubTator RDF for entity annotations.

**Examples:**
```python
# First, search PubMed for relevant articles
PubMed:search_articles("breast cancer BRCA1", max_results=20)

# Then use article PMIDs to query PubTator RDF for gene/disease annotations
```

## SPARQL Query Approach
PubTator requires SPARQL queries. Read MIE file first:
```python
get_MIE_file("pubtator")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `oa:hasBody` for annotated entities (genes, diseases)
- `oa:hasTarget` for linking to PubMed articles
- Entity types: Gene annotations (NCBI Gene IDs), Disease annotations (MeSH IDs)
- `pubtator:denotes_gene`, `pubtator:denotes_disease` for entity types
- Count information via `pubtator:count`

**Workflow:**
1. Use PubMed API to find articles by topic
2. Use PubTator SPARQL to find what genes/diseases are mentioned in those articles
