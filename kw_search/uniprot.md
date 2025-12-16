# UniProt Keyword Search

## Specialized API (Use First)
Use `search_uniprot_entity(query, limit=20)` to search for UniProt protein entries.

**Example:**
```python
search_uniprot_entity("insulin receptor", limit=10)
```

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("uniprot")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel`, `skos:altLabel` for names
- `up:mnemonic`, `up:recommendedName` for protein names
- Always filter by `up:reviewed true` for Swiss-Prot quality data
