# PubMed Exploration Report

## Database Overview
- **Purpose**: Bibliographic database for biomedical literature from MEDLINE, life science journals, and online books
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: `http://rdfportal.org/dataset/pubmed`
- **Key Features**: Publication metadata (titles, abstracts, authors, journals), MeSH term annotations, cross-references to external databases
- **Data Version**: Updated continuously (daily updates)

## Schema Analysis (from MIE file)
### Main Entities
- **PubMedArticle**: Central entity identified by PMID
- **Author**: Authors with names and affiliations organized in ordered lists
- **Journal**: Publication venue with ISSN, eISSN, NLM Journal ID
- **MeSH Annotations**: Subject indexing via descriptors, qualifiers, and supplementary concepts

### Important Properties
- `bibo:pmid`: PubMed identifier
- `dct:title`: Article title
- `bibo:abstract`: Article abstract
- `dct:issued`: Publication date
- `prism:doi`: Digital Object Identifier
- `prism:publicationName`: Journal name
- `rdfs:seeAlso`: Links to MeSH terms
- `fabio:hasPrimarySubjectTerm` / `fabio:hasSubjectTerm`: MeSH descriptor-qualifier pairs

### Query Patterns
- **RECOMMENDED**: Use PubMed search API for initial discovery, SPARQL for detailed RDF data
- Use `bif:contains` for text searches (but may timeout on large result sets)
- Filter by PMID first when getting author/MeSH details
- LIMIT required for all queries

## Search Queries Performed

1. **Query: CRISPR gene editing (PubMed API)** → 23,378 total articles
   - Found recent articles including PMID 41570748 (HPV E7 targeting review)

2. **Query: Alzheimer Disease (PubMed API)** → 246,085 total articles
   - Massive coverage of neurodegenerative disease research

3. **Query: Article 31558841 (SPARQL)** → Found complete metadata
   - Title: "Functional variants in ADH1B and ALDH2 are non-additively associated with all-cause mortality in Japanese population"
   - DOI: 10.1038/s41431-019-0518-y
   - Journal: European journal of human genetics : EJHG
   - Publication date: 2020-03

4. **Query: Authors for article 31558841** → 8 authors
   - First: Sakaue S
   - Last: Okada Y
   - Author order preserved via olo:index

## SPARQL Queries Tested

```sparql
# Query 1: Get article metadata by PMID
SELECT ?title ?doi ?journal ?issued
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?article bibo:pmid "31558841" ;
           dct:title ?title ;
           dct:issued ?issued .
  OPTIONAL { ?article prism:doi ?doi }
  OPTIONAL { ?article prism:publicationName ?journal }
}
# Results: Title, DOI, journal "European journal of human genetics", issued 2020-03
```

```sparql
# Query 2: Get ordered author list for an article
SELECT ?index ?author_name
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?article bibo:pmid "31558841" ;
           dct:creator ?creator .
  ?creator olo:slot ?slot .
  ?slot olo:index ?index ;
        olo:item ?author .
  ?author foaf:name ?author_name .
}
ORDER BY ?index
# Results: 8 authors in order (Sakaue S, Akiyama M, Hirata M, Matsuda K, 
# Murakami Y, Kubo M, Kamatani Y, Okada Y)
```

## Cross-Reference Analysis

**MeSH term linking** (via rdfs:seeAlso):
- Links to MeSH descriptors (D prefix)
- Links to MeSH supplementary concepts (C prefix)
- Enables semantic subject-based querying

**Descriptor-qualifier pairs** (via fabio:hasSubjectTerm):
- Format: {descriptor_id}Q{qualifier_id}
- Examples: D000428Q000453Q000235 (descriptor with multiple qualifiers)

**Shared endpoint databases** (ncbi endpoint):
- PubTator: Text mining annotations linking articles to genes/diseases
- NCBI Gene: Gene metadata and cross-references
- ClinVar: Genetic variants
- MedGen: Clinical concepts

## Interesting Findings

**Findings requiring actual database queries:**

1. **23,378 CRISPR gene editing articles** in PubMed - shows massive research interest

2. **246,085 Alzheimer Disease articles** - one of the most studied diseases

3. **Article PMID 31558841** from 2020 demonstrates:
   - Complete RDF metadata structure
   - 8 authors with ordered affiliations
   - MeSH annotations for subject indexing
   - DOI and journal links

4. **Author ordering preserved**: Using OLO (Ordered List Ontology) with olo:index for correct authorship order

5. **Publication date format**: Uses gYearMonth (2020-03) for year-month precision

## Question Opportunities by Category

### Precision
- "What is the DOI for PubMed article 31558841?" → 10.1038/s41431-019-0518-y
- "Who is the first author of PMID 31558841?" → Sakaue S
- "What journal published PMID 31558841?" → European journal of human genetics

### Completeness
- "How many authors are listed on PubMed article 31558841?" → 8
- "How many articles about CRISPR gene editing are in PubMed?" → 23,378+
- "How many Alzheimer Disease articles are indexed in PubMed?" → 246,085+

### Integration
- "Find gene annotations from PubTator for articles about BRCA1" → Cross-database query
- "What MeSH terms are used to index article 31558841?" → Via rdfs:seeAlso
- "Link PubMed articles to disease annotations via MeSH" → Using mesh: URIs

### Currency
- "What are the most recent articles about COVID-19?" → Sort by dct:issued
- "When was article PMID 31558841 published?" → 2020-03

### Specificity
- "Find articles published in Nature journals about neuroscience" → Journal + keyword filter
- "What institution does author Sakaue S belong to?" → Via org:memberOf

### Structured Query
- "Find articles with both COVID-19 in title AND published in 2024" → Keyword + date filter
- "List articles indexed with MeSH term D016428 (Alzheimer Disease)" → MeSH term query
- "Find co-authored articles between two researchers" → Author overlap query

## Notes
- **37+ million citations** in PubMed - requires careful query optimization
- **Keyword searches via SPARQL may timeout** - use PubMed API for initial discovery
- **Author queries**: Filter by PMID first to avoid processing millions of relationships
- **MeSH annotations**: ~95% of articles have MeSH indexing
- **Abstracts**: ~85% of articles have abstracts
- **DOIs**: ~70% of articles have DOIs
- **Shared endpoint**: ncbi endpoint also hosts PubTator, NCBI Gene, ClinVar, MedGen
- **Date formats vary**: gYearMonth, date, or string depending on precision
