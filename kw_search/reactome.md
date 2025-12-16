# Reactome Keyword Search

## Specialized API (Use First)
Use `search_reactome_entity(query, species=None, types=None, rows=30)` to search pathways and reactions.

**Parameters:**
- `query`: Search keywords (e.g., "apoptosis", "TP53")
- `species`: Filter by species (e.g., ["Homo sapiens"], ["9606"])
- `types`: Filter by type (e.g., ["Pathway"], ["Reaction"], ["Complex"])
- `rows`: Number of results (default 30)

**Examples:**
```python
search_reactome_entity("apoptosis", rows=10)
search_reactome_entity("cell cycle", species=["Homo sapiens"], types=["Pathway"])
search_reactome_entity("EGFR", rows=20)
```

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("reactome")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `dc:title` for pathway/reaction names
- `biopax:displayName` for entity names
- `biopax:organism` for species filtering
