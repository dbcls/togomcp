# NANDO (Japanese Rare Diseases) Keyword Search

## Specialized API (Use First)
Use OLS4 (Ontology Lookup Service) for NANDO searches:

```python
OLS4:searchClasses(query="intractable disease", ontologyId="nando", pageSize=20)
```

**Examples:**
```python
OLS4:searchClasses(query="筋ジストロフィー", ontologyId="nando", pageSize=10)  # Japanese
OLS4:searchClasses(query="muscular dystrophy", ontologyId="nando", pageSize=10)  # English
```

Note: NANDO supports both Japanese and English labels.

## Fallback: SPARQL Query
If OLS4 fails, read MIE file first:
```python
get_MIE_file("nando")
```

Then construct SPARQL using properties from MIE file. Key properties typically include:
- `rdfs:label`, `skos:prefLabel` for disease names (Japanese/English)
- `rdfs:subClassOf` for disease classification
- `dcterms:description` for disease descriptions
- `nando:notificationNumber` for government designation IDs
- Cross-references to MONDO and KEGG
