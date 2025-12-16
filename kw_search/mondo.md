# MONDO (Disease Ontology) Keyword Search

## Specialized API (Use First)
Use OLS4 (Ontology Lookup Service) for disease searches:

```python
OLS4:searchClasses(query="diabetes", ontologyId="mondo", pageSize=20)
```

**Examples:**
```python
OLS4:searchClasses(query="alzheimer", ontologyId="mondo", pageSize=10)
OLS4:searchClasses(query="cancer", ontologyId="mondo", pageSize=15)
OLS4:searchClasses(query="rare disease", ontologyId="mondo", pageSize=20)
```

## Fallback: SPARQL Query
If OLS4 fails, read MIE file first:
```python
get_MIE_file("mondo")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for disease names
- `rdfs:subClassOf` for disease classification hierarchy
- `oboInOwl:hasDbXref` for cross-references to OMIM, Orphanet, DOID, etc.
- `obo:IAO_0000115` for disease definitions
