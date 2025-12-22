# PubMed Keyword Search

## Specialized API (Use First - Two Options)

### Option 1: PubMed-specific API (Recommended for detailed queries)
Use `PubMed:search_articles()` for comprehensive PubMed searches:

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

### Option 2: NCBI E-utilities (Alternative)
Use `ncbi_esearch()` for basic searches:

**Examples:**
```python
ncbi_esearch(database="pubmed", query="CRISPR gene editing", max_results=20)
ncbi_esearch(database="pubmed", query="breast cancer treatment", max_results=15)
```

## Important Notes
**PubMed Database Scope:** PubMed ONLY indexes biomedical and life sciences literature including:
- Medicine, clinical research, public health, epidemiology
- Biology, molecular biology, genetics, genomics
- Biochemistry, cell biology, developmental biology
- Pharmacology, toxicology, drug development
- Microbiology, virology, immunology
- Neuroscience, physiology, anatomy
- Biomedical engineering, medical devices

**PubMed does NOT contain papers from:**
- Physics, astrophysics → use arXiv
- Mathematics, pure math → use arXiv or MathSciNet
- Computer science, AI/ML → use arXiv, ACM Digital Library, IEEE Xplore
- Pure chemistry (non-biomedical) → use ACS publications or SciFinder
- Engineering (non-biomedical) → use IEEE Xplore or arXiv
- Social sciences, economics, psychology (non-medical) → use other databases

## Fallback: SPARQL Query
If APIs fail, read MIE file first:
```python
get_MIE_file("pubmed")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `dc:title` for article titles
- `fabio:hasSubtitle` for abstracts
- `prism:publicationDate` for dates
- `dcterms:subject` for MeSH terms

## Recommendation
Use `PubMed:search_articles()` for most searches as it provides richer features like date filtering and sorting. Use `ncbi_esearch()` only if you need consistency with other NCBI database searches.
