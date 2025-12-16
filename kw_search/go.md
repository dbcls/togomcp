# Gene Ontology (GO) Keyword Search

## Specialized API (Use First)
Use OLS4 (Ontology Lookup Service) for GO term searches:

```python
OLS4:searchClasses(query="apoptosis", ontologyId="go", pageSize=20)
```

**Examples:**
```python
OLS4:searchClasses(query="cell cycle", ontologyId="go", pageSize=10)
OLS4:searchClasses(query="protein binding", ontologyId="go", pageSize=15)
```

## Fallback: SPARQL Query
If OLS4 fails, read MIE file first:
```python
get_MIE_file("go")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for GO term names
- `rdfs:subClassOf` for hierarchical relationships
- `oboInOwl:hasOBONamespace` for domain filtering (biological_process, molecular_function, cellular_component)
- `obo:IAO_0000115` for definitions
