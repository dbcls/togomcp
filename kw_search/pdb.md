# PDB Keyword Search

## Specialized API (Use First)
Use `search_pdb_entity(db, query, limit=20)` where `db` can be:
- `"pdb"` - Protein Data Bank structures
- `"cc"` - Chemical Component Dictionary
- `"prd"` - BIRD (peptides/molecules)

**Examples:**
```python
search_pdb_entity("pdb", "insulin", limit=10)
search_pdb_entity("cc", "ATP", limit=5)
search_pdb_entity("prd", "peptide", limit=5)
```

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("pdb")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `dc:title` for entry titles
- `PDBo:has_entityCategory` for entity information
- `PDBo:has_exptl` for experimental methods
