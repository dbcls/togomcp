# NCBI Taxonomy Keyword Search

## Specialized API (Use First)
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
If OLS4 fails, read MIE file first:
```python
get_MIE_file("taxonomy")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for organism names
- `rdfs:subClassOf` for taxonomic hierarchy
- `oboInOwl:hasDbXref` for NCBI taxon IDs
- Common names vs scientific names
