# ChEMBL Keyword Search

## Specialized APIs (Use First)
ChEMBL has multiple search endpoints:

### For molecules:
```python
search_chembl_molecule(query, limit=20)
```

### For targets (proteins/genes):
```python
search_chembl_target(query, limit=20)
```

### For general ID lookup:
```python
search_chembl_id_lookup(query, limit=20)
```

**Examples:**
```python
search_chembl_molecule("aspirin", limit=10)
search_chembl_target("EGFR", limit=10)
search_chembl_id_lookup("CHEMBL25", limit=5)
```

## Fallback: SPARQL Query
If APIs fail, read MIE file first:
```python
get_MIE_file("chembl")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for names
- `chembl:molecularFormula`, `chembl:smiles` for chemical data
- `chembl:hasActivity` for bioactivity relationships
