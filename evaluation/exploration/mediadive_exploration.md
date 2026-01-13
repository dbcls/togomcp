# MediaDive (Microbial Culture Media Database) Exploration Report

## Database Overview
- **Purpose**: Comprehensive culture media database with standardized recipes for microbial cultivation
- **Scope**: 3,289 culture media recipes and 1,489 chemical ingredients
- **Key data types**: Media compositions, ingredients with chemical identifiers, growth conditions, strain compatibility
- **Focus**: DSMZ standardized protocols for bacteria, archaea, fungi, yeast, microalgae, and phages

## Schema Analysis (from MIE file)

### Main Properties Available
- **Media**: `schema:CultureMedium` with `rdfs:label`, `schema:belongsToGroup`, `schema:hasFinalPH`, `schema:isComplex`
- **Ingredients**: `schema:Ingredient` with `schema:hasFormula`, `schema:hasCAS`, `schema:hasChEBI`, `schema:hasPubChem`, `schema:hasKEGG`
- **Compositions**: `schema:MediumComposition` linking media to ingredients with `schema:gramsPerLiter`
- **Growth conditions**: `schema:GrowthCondition` with `schema:growthTemperature`, `schema:growthPH`, `schema:hasOxygenRequirement`
- **Strains**: `schema:Strain` with `schema:hasDSMNumber`, `schema:hasBacDiveID`, `schema:hasSpecies`

### Important Relationships
- Hierarchical recipe structure: medium → solution → solution_recipe → ingredient
- Strain-medium compatibility via growth conditions
- Ingredient cross-references to ChEBI, PubChem, KEGG, CAS Registry
- BacDive links for strain phenotypic data (73% coverage)
- DSMZ PDF documentation (99% coverage)

### Query Patterns Observed
- Keyword search using `bif:contains` on medium labels
- pH filtering with numeric ranges
- Temperature-based queries for extremophile media
- Composition queries require medium filter to avoid timeouts

## Search Queries Performed

### Query 1: LB Medium variants
- **Search**: `bif:contains "'LB'"`
- **Results**: 16+ LB-related media including:
  - Medium 381: LB (Luria-Bertani) MEDIUM (pH 7.0)
  - Medium 1338: LB MEDIUM WITH CARBONATES (pH 9.6)
  - Medium J1236: LB (LURIA-BERTANI) MEDIUM (LENNOX)
  - Various LB agar formulations

### Query 2: Methanocaldococcus Medium (282)
- **Search**: Specific medium lookup
- **Results**: 
  - Label: "METHANOCALDOCOCCUS MEDIUM"
  - pH: 6.0
  - isComplex: false (defined medium)
  - Linked to Methanocaldococcus jannaschii in BacDive

### Query 3: Marine media
- **Search**: `bif:contains "'marine'"`
- **Results**: 20+ marine media including:
  - Marine Agar 2216 (pH 8.5 and 9.0 variants)
  - Marine Caulobacter Medium (pH 7.1)
  - Marine Thermococcus Medium

### Query 4: Ingredients with ChEBI and KEGG cross-references
- **Search**: Filter by BOUND(?chebi) && BOUND(?kegg)
- **Results**: 20+ chemicals with both identifiers:
  - Glucose: ChEBI:17234, KEGG:C00031
  - Agar: ChEBI:2509, KEGG:C08815
  - Acetic acid: ChEBI:15366, KEGG:C00033
  - Ammonium chloride: ChEBI:31206, KEGG:C12538

### Query 5: Thermophile growth conditions (>70°C)
- **Search**: `schema:growthTemperature > 70`
- **Results**: 20 records at 90-103°C growth
- Highest: Medium 792 at 103°C (anaerobic)
- Most thermophile media require anaerobic conditions

## SPARQL Queries Tested

```sparql
# Query 1: Search media by keyword
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?medium ?label ?ph
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?medium a schema:CultureMedium ;
          rdfs:label ?label .
  ?label bif:contains "'LB'" option (score ?sc) .
  OPTIONAL { ?medium schema:hasFinalPH ?ph }
}
ORDER BY DESC(?sc)
LIMIT 20
# Results: 16+ LB medium variants found including pH variants
```

```sparql
# Query 2: Get specific medium properties
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?medium ?label ?group ?ph ?isComplex
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?medium a schema:CultureMedium ;
          rdfs:label ?label ;
          schema:belongsToGroup ?group ;
          schema:isComplex ?isComplex .
  OPTIONAL { ?medium schema:hasFinalPH ?ph }
  FILTER(?medium = <https://purl.dsmz.de/mediadive/medium/282>)
}
# Results: Methanocaldococcus Medium, pH 6.0, isComplex: false
```

```sparql
# Query 3: Get medium composition (ingredients)
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?composition ?mediumLabel ?ingredientLabel ?gPerL
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?composition a schema:MediumComposition ;
               schema:partOfMedium ?medium ;
               schema:containsIngredient ?ingredient ;
               schema:gramsPerLiter ?gPerL .
  ?medium rdfs:label ?mediumLabel .
  ?ingredient rdfs:label ?ingredientLabel .
  FILTER(?medium = <https://purl.dsmz.de/mediadive/medium/381>)
}
ORDER BY DESC(?gPerL)
# Results: LB medium ingredients - Tryptone 10g/L, Yeast extract 5g/L, NaCl 10g/L
```

```sparql
# Query 4: Find ingredients with chemical cross-references
PREFIX schema: <https://purl.dsmz.de/schema/>

SELECT ?ingredient ?label ?chebi ?kegg
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?ingredient a schema:Ingredient ;
              rdfs:label ?label .
  OPTIONAL { ?ingredient schema:hasChEBI ?chebi }
  OPTIONAL { ?ingredient schema:hasKEGG ?kegg }
  FILTER(BOUND(?chebi) && BOUND(?kegg))
}
ORDER BY ?label
LIMIT 20
# Results: Glucose (ChEBI:17234, KEGG:C00031), Agar (ChEBI:2509), etc.
```

## Interesting Findings

### Specific Entities for Good Questions
1. **LB Medium**: Medium 381, standard bacterial culture medium (pH 7.0)
2. **Methanocaldococcus Medium**: Medium 282 (pH 6.0), linked to archaeal hyperthermophile
3. **Marine Agar 2216**: Multiple pH variants (7.0, 8.5, 9.0)
4. **Glucose**: ChEBI:17234, KEGG:C00031, PubChem:5793 (well cross-referenced)
5. **Agar**: ChEBI:2509, KEGG:C08815, CAS:9002-18-0

### Unique Properties/Patterns
- Hierarchical recipe structure enables complete protocol reconstruction
- pH ranges available as both string (hasFinalPH) and numeric (hasMinPH/hasMaxPH)
- isComplex flag distinguishes defined vs undefined media
- Growth conditions link strains to compatible media

### Connections to Other Databases
- **ChEBI**: 32% of ingredients have ChEBI IDs
- **KEGG**: 13% of ingredients have KEGG IDs
- **PubChem**: 18% of ingredients have PubChem IDs
- **CAS Registry**: 39% of ingredients have CAS numbers
- **BacDive**: 73% of strains linked via hasBacDiveID
- **DSMZ PDFs**: 99% of media have PDF documentation

### Verifiable Facts
- Total media: 3,289
- Total ingredients: 1,489
- Total strains: 45,685
- Ingredients with ChEBI: ~32%
- Ingredients with CAS: ~39%
- Media with PDF links: ~99%

## Question Opportunities by Category

### Precision
- "What is the recommended pH for LB (Luria-Bertani) medium in MediaDive?" → 7.0
- "What DSMZ medium number is the Methanocaldococcus Medium?" → 282
- "What is the ChEBI ID for glucose in MediaDive?" → 17234

### Completeness
- "How many culture media recipes are in MediaDive?" → 3,289
- "How many chemical ingredients are in MediaDive?" → 1,489
- "List all LB medium variants in MediaDive"

### Integration
- "What is the KEGG compound ID for agar in MediaDive?" → C08815
- "Link MediaDive glucose to its ChEBI and PubChem identifiers"
- "Which MediaDive strains are linked to BacDive records?"

### Currency
- "What media recipes have been added to MediaDive recently?"

### Specificity
- "What is the pH range of Marine Agar 2216 variants in MediaDive?" → 7.0-9.0
- "Which MediaDive media support growth above 90°C?"
- "What ingredients make up standard LB medium?" → Tryptone, Yeast extract, NaCl

### Structured Query
- "Find all marine media in MediaDive with pH above 8.0"
- "List media for anaerobic thermophiles with growth above 80°C"
- "Which MediaDive ingredients have both ChEBI and KEGG identifiers?"

## Notes

### Limitations
- Composition queries can be large (~72K+ records) - always filter by specific medium
- Cross-reference coverage varies (ChEBI 32%, KEGG 13%)
- Not all media have numeric pH ranges

### Best Practices
- Always include `FROM <http://rdfportal.org/dataset/mediadive>` in SPARQL
- Use `bif:contains` for keyword searches on labels
- Use OPTIONAL for cross-reference properties (incomplete coverage)
- Filter composition queries by specific medium to avoid timeouts
- Use LIMIT 50-100 for exploratory queries

### Data Quality
- 99% of media have PDF documentation links
- 73% of strains linked to BacDive
- 39% of ingredients have CAS numbers
- 32% of ingredients have ChEBI identifiers
- Average 21.9 compositions per medium
