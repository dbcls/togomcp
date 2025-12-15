# PubChem Keyword Search

## Specialized API (Use First)
Use `get_pubchem_compound_id(compound_name)` to find PubChem Compound IDs.

**Example:**
```python
get_pubchem_compound_id("aspirin")
```

For detailed attributes after getting ID:
```python
get_compound_attributes_from_pubchem("2244")  # aspirin CID
```

## Fallback: SPARQL Query
If API fails, read MIE file first:
```python
get_MIE_file("pubchem")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label` for compound names
- `compound:InChIKey`, `compound:iupacName` for identifiers
- `sio:CHEMINF_000059` for SMILES
