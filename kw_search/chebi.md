# ChEBI Keyword Search

## Specialized API (Use First)
Use OLS4 (Ontology Lookup Service) for ChEBI searches:

```python
OLS4:searchClasses(query="glucose", ontologyId="chebi", pageSize=20)
```

**Example:**
```python
OLS4:searchClasses(query="glucose", ontologyId="chebi", pageSize=10)
```

## Fallback: SPARQL Query
If OLS4 fails, read MIE file first:
```python
get_MIE_file("chebi")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for chemical names
- `rdfs:subClassOf` for hierarchical relationships
- `obo:chebi#formula`, `obo:chebi#inchi` for chemical identifiers
- `RO_0000087` for biological roles
