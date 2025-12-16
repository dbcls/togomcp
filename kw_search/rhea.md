# Rhea Keyword Search

## Specialized API (Use First)
Use `search_rhea_entity(query, limit=100)` to search biochemical reactions.

**Parameters:**
- `query`: Search keywords (e.g., "ATP", "glucose", "uniprot:*")
- `limit`: Maximum results (default 100)

**Examples:**
```python
search_rhea_entity("ATP", limit=20)
search_rhea_entity("glucose phosphorylation", limit=10)
search_rhea_entity("", limit=50)  # Retrieve all reactions
```

Returns reaction ID and equation.

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("rhea")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label` for reaction names
- `rh:equation` for reaction equations
- `rh:status` for approval status
- `rh:side` for reaction participants (substrates/products)
