# GlyCosmos Keyword Search

## No Specialized API - Use SPARQL

**CRITICAL: Read MIE file first:**
```python
get_MIE_file("glycosmos")
```

## SPARQL Template
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>

SELECT DISTINCT ?entity ?label
WHERE {
  GRAPH ?g {
    ?entity rdfs:label ?label .
    FILTER(CONTAINS(LCASE(?label), "keyword"))
  }
}
LIMIT 50
```

## Key Properties (from MIE)
- `rdfs:label` - Entity names
- `glycan:has_glycosequence` - Glycan structure
- GlyTouCan IDs for glycan structures
- Glycoprotein information
- Glycosylation site data
- Lectin-glycan interactions

## Notes
- GlyCosmos uses 100+ named graphs - use GRAPH ?g pattern
- Major graphs: GlyTouCan, GlycoProtein, GlycoGene
- Search glycan structures, proteins, genes, or epitopes
- Complex domain requiring MIE file consultation
