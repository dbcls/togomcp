# NCBI Taxonomy Keyword Search

## Specialized API (Use First - Two Options)

### Option 1: NCBI E-utilities (Recommended)
Use `ncbi_esearch()` to search NCBI Taxonomy database:

**Parameters:**
- `database`: "taxonomy"
- `query`: Search query (organism names, TaxIDs)
- `max_results`: Number of results (default 20)
- `start_index`: For pagination (default 0)

**Examples:**
```python
ncbi_esearch(database="taxonomy", query="Escherichia coli", max_results=20)
ncbi_esearch(database="taxonomy", query="Homo sapiens", max_results=10)
ncbi_esearch(database="taxonomy", query="primates", max_results=15)
ncbi_esearch(database="taxonomy", query="mammals", max_results=20)
```

### Option 2: OLS4 (Alternative)
Use OLS4 (Ontology Lookup Service) for taxonomy searches:

```python
OLS4:searchClasses(query="homo sapiens", ontologyId="taxonomy", pageSize=20)
```

**Examples:**
```python
OLS4:searchClasses(query="escherichia coli", ontologyId="taxonomy", pageSize=10)
OLS4:searchClasses(query="primates", ontologyId="taxonomy", pageSize=15)
```

## Fallback: SPARQL Query
If APIs are insufficient, read MIE file first:
```python
get_MIE_file("taxonomy")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for organism names
- `rdfs:subClassOf` for taxonomic hierarchy
- `oboInOwl:hasDbXref` for NCBI taxon IDs
- Common names vs scientific names

## Notes
- ncbi_esearch is recommended for general keyword searches
- OLS4 provides ontology-based search with hierarchical relationships
- Use SPARQL for complex taxonomic hierarchy queries
- Both scientific and common names are searchable
