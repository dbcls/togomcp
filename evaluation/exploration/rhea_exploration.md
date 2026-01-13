# Rhea - Annotated Reactions Database Exploration

## Overview
- **Total reactions**: 17,078 master reactions
- **Directional reactions**: 34,156 (left→right + right→left)
- **Bidirectional reactions**: 17,078 (reversible)
- **Small molecules**: 11,763
- **Polymers**: 254
- **Transport reactions**: 5,984
- **Endpoint**: https://rdfportal.org/sib/sparql
- **Graph**: http://rdfportal.org/dataset/rhea
- **Base URI**: http://rdf.rhea-db.org/

## Key Entities (Verified)
| Rhea ID | Equation |
|---------|----------|
| RHEA:22044 | K(+)(out) + ATP + H2O + H(+)(in) = K(+)(in) + ADP + phosphate + 2 H(+)(out) |
| RHEA:10000 | H2O + pentanamide = NH4(+) + pentanoate |

## Search Tools

### search_rhea_entity (RECOMMENDED for Discovery)
```python
search_rhea_entity(query='ATP', limit=5)
# Returns: RHEA:22044, RHEA:18353, RHEA:50048...
```

### SPARQL for Detailed Queries

#### Search Reactions by Keyword
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?reaction ?equation ?label
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rdfs:label ?label ;
            rhea:status rhea:Approved .
  ?equation bif:contains "'atp'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
```

#### Get Reaction Details by Accession
```sparql
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?property ?value
WHERE {
  ?reaction rhea:accession "RHEA:10000" ;
            ?property ?value .
}
```

#### Find Transport Reactions
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?reaction ?equation ?participant ?compound ?location
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:isTransport 1 ;
            rhea:side ?side .
  ?side rhea:contains ?participant .
  ?participant rhea:compound ?compound ;
               rhea:location ?location .
}
LIMIT 50
```

#### Get Reactions with EC Number and GO Terms
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT DISTINCT ?reaction ?equation ?ec ?goTerm
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:ec ?ec ;
            rdfs:seeAlso ?goTerm .
  FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 50
```

## Schema Notes

### Reaction Quartet System
Each reaction has 4 representations:
- **Master (unspecified)**: RHEA:10000
- **Left→Right**: RHEA:10001
- **Right→Left**: RHEA:10002
- **Bidirectional**: RHEA:10003

### Key Properties
| Property | Description |
|----------|-------------|
| rhea:equation | Text equation (e.g., "H2O + ATP = ADP + Pi") |
| rhea:status | rhea:Approved, rhea:Preliminary, rhea:Obsolete |
| rhea:isChemicallyBalanced | 1 = balanced, 0 = unbalanced |
| rhea:isTransport | 1 = transport reaction |
| rhea:ec | EC number (enzyme classification) |
| rhea:side | Left/right side of reaction |
| rhea:location | rhea:In or rhea:Out (for transport) |

### Stoichiometry
- `rhea:contains1` = stoichiometry 1
- `rhea:contains2` = stoichiometry 2
- `rhea:contains3` = stoichiometry 3
- `rhea:containsN` = stoichiometry > 3

## Cross-References
| Database | Pattern | Coverage |
|----------|---------|----------|
| Gene Ontology | GO_ prefix | ~55% |
| EC Numbers | uniprot/enzyme/ | ~45% |
| KEGG Reaction | kegg.reaction/ | ~35% |
| ChEBI | All compounds | 100% |

## Critical Patterns

### ALWAYS
- Use `bif:contains` for text search (not FILTER CONTAINS)
- Add `ORDER BY DESC(?sc)` after bif:contains
- Filter by `rhea:status rhea:Approved`
- Add LIMIT to prevent timeouts

### NEVER
- Query without LIMIT on open-ended relationships
- Confuse master reactions with directional variants
- Use FILTER(CONTAINS()) for keyword search

## Anti-Patterns

### ❌ Slow FILTER CONTAINS
```sparql
WHERE {
  ?reaction rhea:equation ?equation .
  FILTER(CONTAINS(LCASE(?equation), "atp"))
}
```

### ✅ Fast bif:contains
```sparql
WHERE {
  ?reaction rhea:equation ?equation .
  ?equation bif:contains "'atp'" option (score ?sc) .
}
ORDER BY DESC(?sc)
```

## Question Opportunities
1. **Precision**: "What is the equation for RHEA:10000?"
2. **Counting**: "How many reactions in Rhea?" → 17,078
3. **Transport**: "How many transport reactions?" → 5,984
4. **EC mapping**: "What EC number is RHEA:22044 associated with?"
5. **Cross-ref**: "What GO terms are associated with ATP hydrolysis reactions?"
6. **Boolean search**: "Find reactions involving both glucose and phosphate"
