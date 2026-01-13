# ChEBI (Chemical Entities of Biological Interest) Exploration

## Overview
- **Total entities**: 223,078 chemical entities
- **Entities with formulas**: ~187,110 (~86%)
- **Endpoint**: https://rdfportal.org/ebi/sparql
- **Graph**: http://rdf.ebi.ac.uk/dataset/chebi
- **Base URI**: http://purl.obolibrary.org/obo/CHEBI_

## Key Entities (Verified)
| ChEBI ID | Name | Formula | Mass |
|----------|------|---------|------|
| CHEBI:15365 | acetylsalicylic acid (aspirin) | C9H8O4 | 180.157 |
| CHEBI:15377 | water | H2O | 18.015 |
| CHEBI:17203 | L-proline | C5H9NO2 | 115.130 |
| CHEBI:28659 | phosphorus atom | P | 30.974 |

## Search Tools

### OLS4:searchClasses (RECOMMENDED for Discovery)
```python
OLS4:searchClasses(ontologyId='chebi', query='aspirin')
# Returns: CHEBI:141699, CHEBI:138614, CHEBI:140202...
```

### SPARQL for Detailed Data

#### Keyword Search with bif:contains
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?entity ?label ?sc
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?entity a owl:Class ;
          rdfs:label ?label .
  ?label bif:contains "'glucose'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
```

#### Get Molecular Properties
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>

SELECT ?label ?formula ?mass ?smiles ?inchikey
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  obo:CHEBI_15365 rdfs:label ?label .
  OPTIONAL { obo:CHEBI_15365 chebi:formula ?formula }
  OPTIONAL { obo:CHEBI_15365 chebi:mass ?mass }
  OPTIONAL { obo:CHEBI_15365 chebi:smiles ?smiles }
  OPTIONAL { obo:CHEBI_15365 chebi:inchikey ?inchikey }
}
```

#### Navigate Hierarchy (Find Parents)
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT ?parent ?parentLabel
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  obo:CHEBI_17203 rdfs:subClassOf ?parent .
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/CHEBI_"))
  ?parent rdfs:label ?parentLabel .
}
```

#### Find Chemical Relationships (Conjugate Acids/Bases)
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi#>

SELECT ?acid ?acidLabel ?base ?baseLabel
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?acid rdfs:subClassOf ?restriction .
  ?restriction owl:onProperty chebi:is_conjugate_acid_of ;
               owl:someValuesFrom ?base .
  ?acid rdfs:label ?acidLabel .
  ?base rdfs:label ?baseLabel .
}
LIMIT 20
```

## Schema Notes

### CRITICAL: Two Namespaces!
- **Data properties** (formula, mass, smiles): `chebi/` (with slash)
  - `http://purl.obolibrary.org/obo/chebi/formula`
- **Relationship properties** (is_conjugate_acid_of): `chebi#` (with hash)
  - `http://purl.obolibrary.org/obo/chebi#is_conjugate_acid_of`

### Key Properties
| Property | Namespace | Description |
|----------|-----------|-------------|
| chebi:formula | chebi/ | Molecular formula |
| chebi:mass | chebi/ | Molecular mass |
| chebi:smiles | chebi/ | SMILES notation |
| chebi:inchi | chebi/ | InChI identifier |
| chebi:inchikey | chebi/ | InChIKey |
| chebi:is_conjugate_acid_of | chebi# | Conjugate acid relationship |
| chebi:is_tautomer_of | chebi# | Tautomer relationship |

### Biological Roles
Accessed via OWL restrictions:
```sparql
?entity rdfs:subClassOf ?restriction .
?restriction owl:onProperty <http://purl.obolibrary.org/obo/RO_0000087> ;
             owl:someValuesFrom ?role .
```

## Cross-References
| Database | Prefix | Coverage |
|----------|--------|----------|
| KEGG | KEGG: | Common |
| DrugBank | DrugBank: | Drugs |
| PubChem | PMID: | Common |
| HMDB | HMDB: | Metabolites |
| CAS | CAS: | Common |

## Critical Patterns

### ALWAYS
- Include `FROM <http://rdf.ebi.ac.uk/dataset/chebi>`
- Use `bif:contains` for text search
- Filter by CHEBI_ URI prefix for chemical entities only
- Use correct namespace (chebi/ for data, chebi# for relationships)

### NEVER
- Use FILTER CONTAINS (slower, no scoring)
- Use chebi# for formula/mass/smiles (wrong namespace)
- Forget to filter out non-CHEBI classes

## Anti-Patterns

### ❌ Wrong Namespace for Data Properties
```sparql
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi#>
SELECT ?formula WHERE {
  ?entity chebi:formula ?formula .  -- WRONG!
}
```

### ✅ Correct Namespace
```sparql
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>
SELECT ?formula WHERE {
  ?entity chebi:formula ?formula .  -- CORRECT!
}
```

## Question Opportunities
1. **Precision**: "What is the molecular formula of aspirin?" → C9H8O4
2. **Counting**: "How many chemical entities in ChEBI?" → 223,078
3. **Structure**: "What is the SMILES of caffeine?"
4. **Hierarchy**: "What chemical classes is L-proline part of?"
5. **Cross-ref**: "What is the KEGG ID for glucose?"
6. **Relationships**: "What is the conjugate base of acetic acid?"
