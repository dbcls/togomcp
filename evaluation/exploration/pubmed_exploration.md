# PubMed RDF Exploration

## Overview
- **Total articles**: 37+ million citations
- **Abstracts coverage**: ~85%
- **DOI coverage**: ~70%
- **MeSH annotations**: ~95%
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: http://rdfportal.org/dataset/pubmed
- **Base URI**: http://rdf.ncbi.nlm.nih.gov/pubmed/

## Key Entities (Verified)
| PMID | Title | Journal | DOI |
|------|-------|---------|-----|
| 31558841 | Functional variants in ADH1B and ALDH2... | Eur J Hum Genet | 10.1038/s41431-019-0518-y |

## Search Tools

### ncbi_esearch (RECOMMENDED for Discovery)
```python
ncbi_esearch(database='pubmed', query='BRCA1 breast cancer')
# Returns: PMIDs with counts
```

### PubMed MCP Tools
- `search_articles` - Search PubMed articles
- `get_article_metadata` - Get article details by PMID
- `get_full_text_article` - Get full text from PMC

### SPARQL for Detailed Queries

#### Get Article by PMID
```sparql
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX prism: <http://prismstandard.org/namespeces/1.2/basic/>

SELECT ?title ?abstract ?doi ?journal ?issued
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?article bibo:pmid "31558841" ;
           dct:title ?title ;
           bibo:abstract ?abstract ;
           prism:doi ?doi ;
           prism:publicationName ?journal ;
           dct:issued ?issued .
}
```

#### Search by Keyword
```sparql
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?pmid ?title
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?article bibo:pmid ?pmid ;
           dct:title ?title .
  ?title bif:contains "'cancer' AND 'screening'" .
}
LIMIT 20
```

#### Find Articles with MeSH Terms
```sparql
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX mesh: <http://id.nlm.nih.gov/mesh/>

SELECT ?pmid ?title ?issued
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?article bibo:pmid ?pmid ;
           dct:title ?title ;
           dct:issued ?issued ;
           rdfs:seeAlso mesh:D016428 .  -- Alzheimer Disease
}
ORDER BY DESC(?issued)
LIMIT 50
```

#### Get Authors and Affiliations
```sparql
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX olo: <http://purl.org/ontology/olo/core#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX org: <http://www.w3.org/ns/org#>

SELECT ?pmid ?index ?author_name ?affiliation
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  ?article bibo:pmid ?pmid ;
           dct:creator ?creator .
  ?creator olo:slot ?slot .
  ?slot olo:index ?index ;
        olo:item ?author .
  ?author foaf:name ?author_name .
  OPTIONAL { ?author org:memberOf ?affiliation }
  FILTER(?pmid = "31558841")
}
ORDER BY ?index
```

## Schema Notes

### Key Properties
| Property | Description |
|----------|-------------|
| bibo:pmid | PubMed ID |
| dct:title | Article title |
| bibo:abstract | Abstract text |
| prism:doi | DOI |
| prism:publicationName | Journal name |
| dct:issued | Publication date |
| dct:creator | Author list |
| fabio:hasSubjectTerm | MeSH subject terms |
| rdfs:seeAlso | MeSH cross-references |

### Author Structure
- `dct:creator` → ordered list using OLO ontology
- `olo:slot` → `olo:index` (author position) + `olo:item` (author)
- `foaf:name` = author name
- `org:memberOf` = affiliation

### MeSH Annotations
| Property | Description |
|----------|-------------|
| fabio:hasPrimarySubjectTerm | Major topics |
| fabio:hasSubjectTerm | Secondary topics |
| rdfs:seeAlso | All MeSH links |

MeSH ID format: `mesh:D{descriptor}` or `mesh:D{descriptor}Q{qualifier}`

## Critical Patterns

### ALWAYS
- Include `FROM <http://rdfportal.org/dataset/pubmed>`
- Use `bif:contains` for keyword search
- Filter by PMID before querying authors
- Add LIMIT (37M+ articles)

### NEVER
- Count entire dataset (will timeout)
- Use FILTER/REGEX for keyword search
- Query authors without filtering articles first

## Anti-Patterns

### ❌ Counting Entire Dataset
```sparql
SELECT (COUNT(?article) as ?total) WHERE {
  ?article bibo:pmid ?pmid .
}
-- WILL TIMEOUT!
```

### ❌ Slow REGEX Search
```sparql
FILTER(REGEX(?title, "cancer", "i"))
```

### ✅ Fast bif:contains
```sparql
?title bif:contains "'cancer'" .
```

## Question Opportunities
1. **Precision**: "What is the DOI for PMID 31558841?" → 10.1038/s41431-019-0518-y
2. **Search**: "Find articles about CRISPR from 2024"
3. **MeSH**: "What articles are indexed with Alzheimer Disease (D016428)?"
4. **Authors**: "Who are the authors of PMID 31558841?"
5. **Journal**: "Find recent Nature articles about neuroscience"
