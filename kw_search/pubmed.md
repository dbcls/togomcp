# PubMed Keyword Search

## Specialized API (Use First)
Use `PubMed:search_articles(query, max_results=20, ...)` to search biomedical literature.

**Parameters:**
- `query`: PubMed search syntax or natural language
- `max_results`: Number of results (default 20)
- `date_from`, `date_to`: Date filters (YYYY/MM/DD format)
- `datetype`: "pdat" (publication), "edat" (entry), "mdat" (modification)
- `sort`: "relevance", "pub_date", "author", "journal_name", "title"

**Examples:**
```python
PubMed:search_articles("CRISPR gene editing", max_results=20)
PubMed:search_articles("Smith J[Author]", max_results=10)
PubMed:search_articles("Nature[journal] AND artificial intelligence")
PubMed:search_articles("asthma", date_from="2020", date_to="2024")
```

**Note:** PubMed only indexes biomedical/life sciences literature, not physics, math, or computer science.

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("pubmed")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `dc:title` for article titles
- `fabio:hasSubtitle` for abstracts
- `prism:publicationDate` for dates
- `dcterms:subject` for MeSH terms
