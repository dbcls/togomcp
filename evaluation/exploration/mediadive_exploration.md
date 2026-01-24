# MediaDive Exploration Report

## Database Overview
- **Purpose**: Comprehensive microbial culture media database from DSMZ with standardized recipes for bacteria, archaea, fungi, yeast, microalgae, and phages
- **Endpoint**: https://rdfportal.org/primary/sparql
- **Graph**: `http://rdfportal.org/dataset/mediadive`
- **Key Features**: Hierarchical recipe structure (medium → solution → ingredient), chemical cross-references, strain-medium compatibility, growth conditions
- **Data Version**: Current release

## Schema Analysis (from MIE file)
### Main Entities
- **CultureMedium**: Central entity with label, group, pH, complexity
- **Ingredient**: Chemical components with cross-references (ChEBI, CAS, KEGG, PubChem, GMO)
- **MediumComposition**: Links media to ingredients with concentrations (g/L)
- **GrowthCondition**: Cultivation parameters (temperature, pH, oxygen requirement)
- **Strain**: Microbial strains with DSM numbers, BacDive IDs, species names

### Important Relationships
- Medium ↔ Composition ↔ Ingredient (hierarchical recipe)
- Medium ↔ Growth ↔ Strain (cultivation compatibility)
- Ingredient → Chemical databases (cross-references)
- Strain → BacDive (phenotypic data integration)

### Query Patterns
- Use `bif:contains` for keyword searches on labels
- Use OPTIONAL for cross-references (partial coverage)
- Filter by specific medium when querying compositions (many compositions per medium)
- LIMIT recommended: 30-50 for typical queries

## Search Queries Performed

1. **Query: "marine"** → Found 20+ marine-related media including BACTO MARINE BROTH (medium/514), MARINE AGAR (medium/123), MARINE CAULOBACTER MEDIUM (medium/601)

2. **Query: "fungi" OR "yeast"** → Found media for osmophilic fungi (M 40 Y, medium/187), EMERSON'S YEAST STARCH AGAR (medium/551), specialized fungal media

3. **Query: thermophile conditions (temp ≥ 55°C)** → Found 961 growth conditions for thermophilic organisms

4. **Query: extreme thermophiles (temp ≥ 70°C)** → Found hyperthermophiles:
   - Pyrolobus fumarii at 103°C (medium/792)
   - Pyrococcus kukulkanii at 100°C (medium/377)
   - Hyperthermus butylicus at 99°C (medium/491)

5. **Query: Ingredients with ChEBI** → 687 ingredients have ChEBI cross-references

## SPARQL Queries Tested

```sparql
# Query 1: Count total media
SELECT (COUNT(DISTINCT ?medium) as ?media_count)
FROM <http://rdfportal.org/dataset/mediadive>
WHERE { ?medium a schema:CultureMedium . }
# Results: 3,289 culture media
```

```sparql
# Query 2: High temperature growth conditions (hyperthermophiles)
SELECT ?strain ?species ?temp ?mediumLabel
WHERE {
  ?growth a schema:GrowthCondition ;
          schema:relatedToStrain ?strain ;
          schema:partOfMedium ?medium ;
          schema:growthTemperature ?temp .
  ?strain schema:hasSpecies ?species .
  ?medium rdfs:label ?mediumLabel .
  FILTER(?temp >= 70)
}
ORDER BY DESC(?temp) LIMIT 15
# Results: Found 15 hyperthermophile strains with growth at 70-103°C
# Highest: Pyrolobus fumarii at 103°C in PYROLOBUS FUMARII MEDIUM
```

```sparql
# Query 3: Strains with BacDive cross-references
SELECT (COUNT(DISTINCT ?strain) as ?bacdive_linked_count)
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?strain a schema:Strain ;
          schema:hasBacDiveID ?bacDiveID .
}
# Results: 33,226 strains have BacDive IDs (73% of total)
```

## Cross-Reference Analysis

**Entity counts** (unique entities with mappings):
- Ingredients with ChEBI: 687 (46% of 1,489 ingredients - higher than documented)
- Strains with BacDive IDs: 33,226 (73% of 45,685 strains)

**Cross-reference coverage by type**:
- GMO (General Media Object): 41% of ingredients
- CAS Registry: 39% of ingredients
- ChEBI: 32-46% of ingredients
- PubChem: 18% of ingredients
- KEGG: 13% of ingredients
- MetaCyc: 7% of ingredients

**BacDive Integration**:
- 33,226 strains link to BacDive for phenotypic data
- Enables cross-database queries for strain characterization + cultivation protocols
- Shared "primary" endpoint allows efficient federated queries

## Interesting Findings

**Findings requiring actual database queries:**

1. **961 thermophilic growth conditions (≥55°C)** exist in the database - enables studying extremophile cultivation requirements

2. **Highest growth temperature: 103°C** for Pyrolobus fumarii (strain/5869) using PYROLOBUS FUMARII MEDIUM (medium/792) - one of the most extreme thermophiles

3. **Hyperthermophile diversity**: Multiple genera thrive at ≥95°C: Pyrolobus, Pyrococcus, Hyperthermus, Pyrodictium, Methanopyrus, Pyrobaculum

4. **687 ingredients have ChEBI cross-references** - enables linking to chemical ontology for metabolic context

5. **BACTO MARINE BROTH (medium/514)** contains high NaCl concentrations (19.45-150 g/L depending on variant) - critical for marine microbe cultivation

6. **Marine media diversity**: 20+ specialized media for marine organisms including MARINE THERMOCOCCUS MEDIUM, MARINE CAULOBACTER MEDIUM

## Question Opportunities by Category

### Precision
- "What is the MediaDive medium ID for PYROLOBUS FUMARII MEDIUM?" → medium/792
- "What is the growth temperature for Pyrolobus fumarii in MediaDive?" → 103°C
- "What is the ChEBI ID for glucose in MediaDive?" → 17234 (ingredient/5)

### Completeness
- "How many culture media are in MediaDive?" → 3,289
- "How many thermophilic growth conditions (≥55°C) exist in MediaDive?" → 961
- "How many MediaDive ingredients have ChEBI cross-references?" → 687

### Integration
- "Link BacDive strain to its MediaDive culture medium recommendation" → BacDive ID ↔ Growth conditions
- "What ChEBI identifiers correspond to MediaDive ingredients with KEGG cross-references?" → Cross-database chemical mapping

### Currency
- "What is the current count of culture media in MediaDive?" → 3,289 (may update)
- "How many strains have been added to MediaDive with BacDive links?" → 33,226

### Specificity
- "What medium is recommended for growing Pyrococcus furiosus?" → PYROCOCCUS MEDIUM (medium/377)
- "What is the NaCl concentration in BACTO MARINE BROTH?" → 19.45 g/L (standard formulation)
- "What organisms can grow at temperatures above 100°C according to MediaDive?" → Pyrolobus fumarii (103°C), Pyrococcus kukulkanii (100°C)

### Structured Query
- "Find all media supporting growth at ≥80°C" → Filter by growthTemperature
- "List ingredients present in marine media with ChEBI cross-references" → Multi-criteria query
- "Find strains that grow on PYROCOCCUS MEDIUM at temperatures above 90°C" → Combined conditions

## Notes
- **Shared endpoint**: MediaDive is on the "primary" endpoint with BacDive, taxonomy, mesh, go, mondo, nando - enables powerful cross-database queries
- **Performance**: Use `bif:contains` for keyword searches; filter by specific medium for composition queries
- **Cross-reference coverage varies**: Use OPTIONAL for database-specific properties
- **Hierarchical structure**: medium → solution → solution_recipe → ingredient with preparation protocols
- **BacDive integration is key**: 73% of strains link to BacDive for phenotypic characterization
