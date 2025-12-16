# MeSH Keyword Search

## Specialized API (Use First)
Use `search_mesh_entity(query, limit=10)` to search MeSH terms.

**Examples:**
```python
search_mesh_entity("diabetes", limit=10)
search_mesh_entity("cardiovascular disease", limit=20)
```

Returns MeSH IDs and descriptors.

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("mesh")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `meshv:prefLabel` for descriptor names
- `meshv:treeNumber` for hierarchical classification
- `meshv:concept` for related concepts
- `meshv:scopeNote` for definitions
