# Universal SPARQL Template - Compact Version

## One Template for All RDF Portal Databases

```sparql
PREFIX [prefix]: <[uri]>

SELECT DISTINCT 
    ?entity 
    ?label
    (MAX(?sc1) AS ?score1)
    (MAX(?sc2) AS ?score2)
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)

FROM <[graph]>  # Omit if not needed

WHERE {
  # Core entity
  ?entity a [EntityClass] ;
          [labelProperty] ?label .
  
  # CRITICAL FILTERS (from MIE anti_patterns)
  [criticalFilter]
  
  # Multi-property search
  {
    [property1Pattern]
    ?text1 bif:contains "'[keyword]'" option (score ?sc1) .
  } UNION {
    [property2Pattern]
    ?text2 bif:contains "'[keyword]'" option (score ?sc2) .
  }
  
  # Optional data
  OPTIONAL { ?entity [optionalProp] ?optionalValue . }
}
GROUP BY ?entity ?label
ORDER BY DESC(?totalScore)
LIMIT 50
```

## Fill These from MIE File

| Placeholder | Source | Example |
|-------------|--------|---------|
| `[prefix]` | schema_info | `up`, `schema`, `owl` |
| `[uri]` | schema_info | `http://purl.uniprot.org/core/` |
| `[graph]` | schema_info → graphs | `<http://sparql.uniprot.org/uniprot>` |
| `[EntityClass]` | shape_expressions | `up:Protein`, `schema:Strain` |
| `[labelProperty]` | shape_expressions | `rdfs:label`, `up:mnemonic` |
| `[criticalFilter]` | anti_patterns | `up:reviewed 1`, `FILTER(STRSTARTS...)` |
| `[property1Pattern]` | Test & MIE | `?entity prop ?text1` or split path |
| `[property2Pattern]` | Test & MIE | `?entity prop2 ?text2` |
| `[keyword]` | User input | `'kinase'`, `'glucose'` |

## Critical Rules (Universal)

```sparql
# ✅ DO
option (score ?sc)           # Any name except ?score
?entity prop ?x . ?x subprop ?text .  # Split property paths
OPTIONAL { ?entity prop ?val . }       # For incomplete data

# ❌ DON'T
option (score ?score)        # Reserved word!
?entity prop/subprop ?text . # No paths with bif:contains
?entity prop ?val .          # Required when optional
FILTER(bif:contains(...))    # Must be triple pattern
```

## Quick Examples

### UniProt (Option A: Single Property - with scoring) ✅ Tested & Working
```sparql
PREFIX core: <http://purl.uniprot.org/core/>

SELECT DISTINCT ?protein ?mnemonic ?sc
FROM <http://sparql.uniprot.org/uniprot>
WHERE {
  ?protein a core:Protein ;
           core:mnemonic ?mnemonic ;
           core:reviewed 1 .  # CRITICAL!
  ?protein core:recommendedName ?n . ?n core:fullName ?t .
  ?t bif:contains "'kinase'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
```

### UniProt (Option B: Multi-Property - no scoring) ✅ Tested & Working
```sparql
PREFIX core: <http://purl.uniprot.org/core/>

SELECT DISTINCT ?protein ?mnemonic ?source
FROM <http://sparql.uniprot.org/uniprot>
WHERE {
  ?protein a core:Protein ;
           core:mnemonic ?mnemonic ;
           core:reviewed 1 .  # CRITICAL!
  {
    ?protein core:recommendedName ?n . ?n core:fullName ?t .
    FILTER(CONTAINS(LCASE(?t), "kinase"))
    BIND("name" AS ?source)
  } UNION {
    ?protein core:annotation ?a . ?a rdfs:comment ?t .
    FILTER(CONTAINS(LCASE(?t), "kinase"))
    BIND("function" AS ?source)
  }
}
LIMIT 20
```

### ChEBI ✅ Tested & Working
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?entity ?label 
       (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?entity a owl:Class ; rdfs:label ?label .
  FILTER(STRSTARTS(STR(?entity), "http://purl.obolibrary.org/obo/CHEBI_"))
  {
    ?entity rdfs:label ?t .
    ?t bif:contains "'glucose'" option (score ?sc1) .
  } UNION {
    ?entity oboInOwl:hasRelatedSynonym ?t .
    ?t bif:contains "'glucose'" option (score ?sc2) .
  }
}
GROUP BY ?entity ?label
ORDER BY DESC(?totalScore)
LIMIT 20
```

### BacDive ✅ Tested & Working
```sparql
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT DISTINCT ?strain ?label 
       (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  ?strain a schema:Strain ; rdfs:label ?label .
  {
    ?strain rdfs:label ?t .
    ?t bif:contains "'escherichia'" option (score ?sc1) .
  } UNION {
    ?strain dct:description ?t .
    ?t bif:contains "'escherichia'" option (score ?sc2) .
  }
}
GROUP BY ?strain ?label
ORDER BY DESC(?totalScore)
LIMIT 20
```

## Boolean Keywords

```sparql
# AND
'keyword1' AND 'keyword2'

# OR
'keyword1' OR 'keyword2'

# NOT
'keyword' AND NOT 'exclude'

# Complex
('word1' OR 'word2') AND 'word3' AND NOT 'word4'
```

## 5-Step Usage

1. **Get MIE**: `TogoMCP-Test:get_MIE_file(dbname="X")`
2. **Fill**: Prefixes, entity class, critical filters
3. **Test**: Which properties are indexed?
4. **Adapt**: Replace placeholders with real values
5. **Run**: Execute query with keyword

## Fallback (if bif:contains fails)

**⚠️ UniProt/SIB Endpoint Note**: UNION + `bif:contains` doesn't work on SIB endpoint. Use:
- **Option A**: Single property with `bif:contains` (keeps scoring)
- **Option B**: FILTER CONTAINS with UNION (multi-property, no scoring)

**✅ ChEBI/BacDive Note**: UNION + `bif:contains` works perfectly. Use the main template.

### Fallback Pattern (works everywhere)
```sparql
# Replace bif:contains UNION blocks with:
{
  [property1]
  FILTER(CONTAINS(LCASE(?text), "keyword"))
  BIND("source1" AS ?source)
} UNION {
  [property2]
  FILTER(CONTAINS(LCASE(?text), "keyword"))
  BIND("source2" AS ?source)
}

# Remove: option (score ?sc)
# Remove: Score aggregation
# Sort by: ?label instead
```

---

**Remember**: Never use `?score` • Split property paths • OPTIONAL for sparse data • Always LIMIT