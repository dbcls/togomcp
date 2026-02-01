# MediaDive Exploration Report

**Date**: January 31, 2026
**Session**: 1 (Complete exploration)

## Executive Summary

MediaDive is a comprehensive microbial culture media database from DSMZ with 3,289 standardized recipes. It provides hierarchical recipe structures (medium → solution → solution_recipe → ingredient) with cross-references to chemical databases and integration with BacDive for strain phenotypes.

**Key capabilities requiring deep knowledge**:
- Cross-database integration with BacDive via shared BacDiveID (73% of strains linked)
- Performance optimization for composition queries (avg 21.9 compositions per medium)
- Partial coverage of chemical cross-references (GMO 41%, CAS 39%, ChEBI 32%)
- Filtering by taxonomic groups, temperature ranges, pH ranges, oxygen requirements

**Major integration opportunities**:
- BacDive: Strain phenotypes (taxonomy, oxygen tolerance, genus/species)
- Chemical databases: ChEBI, KEGG, PubChem, CAS via ingredient cross-references
- DSMZ documentation: PDF protocols for 99% of media

**Most valuable patterns discovered**:
1. Pre-filtering by genus/species in BacDive before MediaDive join (95-99% reduction)
2. Using OPTIONAL for partial cross-reference coverage
3. Filtering composition queries by specific medium
4. Temperature and pH numeric filtering for extremophile research

**Recommended question types**:
- Extremophile cultivation (hyperthermophiles, psychrophiles, acidophiles, alkaliphiles)
- Anaerobic bacteria media with reducing agents
- Cross-database questions linking BacDive phenotypes to MediaDive recipes
- Ingredient chemical cross-references

---

## Database Overview

- **Purpose**: Standardized microbial culture media recipes
- **Scope**: 3,289 media, 1,489 ingredients, 45,685 strains
- **Data types**: Culture media, solutions, ingredients, strains, growth conditions, gas compositions
- **Size**: ~250K entities total (72K compositions, 68K growth conditions, 45K strains)
- **Endpoint**: https://rdfportal.org/primary/sparql (shared "primary" endpoint)
- **Co-located databases**: BacDive, Taxonomy, MeSH, GO, MONDO, NANDO

---

## Structure Analysis

### Performance Strategies

**Strategy 1: Explicit GRAPH Clauses**
- Required for cross-database queries with BacDive
- MediaDive GRAPH: `<http://rdfportal.org/dataset/mediadive>`
- BacDive GRAPH: `<http://rdfportal.org/dataset/bacdive>`
- Performance impact: Essential for correct query execution

**Strategy 2: Pre-filtering Before Cross-Database Joins**
- Filter by genus/species/phenotype in BacDive GRAPH before MediaDive join
- Genus filter: Reduces 97K strains to ~5K (95% reduction)
- Species keyword filter: Reduces to ~200 strains (99.8% reduction)
- Oxygen phenotype filter: Reduces to ~35K strains (64% reduction)

**Strategy 7: OPTIONAL Ordering**
- Place OPTIONAL blocks after required patterns
- Use for partial coverage properties (ChEBI, KEGG, PubChem)
- Pattern: Required patterns first, then OPTIONAL blocks

**Strategy 10: LIMIT Clause**
- Always use LIMIT for composition queries (avg 21.9 per medium)
- Recommended LIMIT 30-50 for general queries
- Cross-database queries: LIMIT 50

**bif:contains for Keyword Search**
- Use for full-text search on labels/groups
- Syntax: `?label bif:contains "'keyword'"`
- Boolean support: `"'keyword1' OR 'keyword2'"`

### Common Pitfalls

**Error 1: FILTER CONTAINS Instead of bif:contains**
- Cause: Using FILTER(CONTAINS(LCASE(?label), "keyword"))
- Impact: Less efficient than bif:contains
- Solution: Use `?label bif:contains "'keyword'"`
- Note: Works for small datasets but slower at scale

**Error 2: Missing OPTIONAL for Partial Coverage**
- Cause: Requiring all cross-references filters out most ingredients
- Impact: Returns only ingredients with all databases (rare)
- Solution: Use OPTIONAL for each database property, then filter with OR
- Example: `FILTER(BOUND(?chebi) || BOUND(?kegg))`

**Error 3: Unbounded Composition Queries**
- Cause: Querying all 72K compositions without filtering
- Impact: Slow queries or timeouts
- Solution: Filter by specific medium first, use LIMIT
- Coverage: Avg 21.9 compositions per medium

**Error 4: Cross-Database Query Without Pre-Filtering**
- Cause: Joining 97K BacDive strains to 33K MediaDive strains without filter
- Impact: Slow performance (5-20s without filter vs 2-3s with filter)
- Solution: Apply genus/species/phenotype filter in BacDive GRAPH first
- Example: Add `schema:hasGenus "Bacillus"` in BacDive GRAPH

### Data Organization

**CultureMedium** (3,289 entities)
- Core medium records with label, group, pH, isComplex
- Links to compositions, solutions, growth conditions
- 99% have PDF documentation links

**Ingredient** (1,489 entities)
- Chemical components with cross-references
- Coverage: GMO 41%, CAS 39%, ChEBI 32%, KEGG 13%, PubChem 18%
- Properties: formula, CAS number, ChEBI ID, PubChem ID, KEGG ID

**MediumComposition** (72,184 entities)
- Links medium to ingredient with concentration
- Properties: gramsPerLiter, isOptionalIngredient
- Avg 21.9 per medium

**GrowthCondition** (68,001 entities)
- Links strain to medium with cultivation parameters
- Properties: growthTemperature, growthPH, hasOxygenRequirement, hasGrowthIndicator

**Strain** (45,685 entities)
- Microbial strains with taxonomy
- Properties: hasDSMNumber, hasBacDiveID (73% coverage), hasSpecies, belongsTaxGroup
- Tax groups: Bacteria (32K), Fungi (5K), Yeast (3K), Microalgae (1.3K), Archaea (952)

**Solution** (5,613 entities)
- Intermediate solution preparations
- Links to SolutionRecipe for detailed ingredient amounts

**SolutionRecipe** (40,471 entities)
- Detailed ingredient amounts in solutions
- Properties: ingredientAmount, ingredientUnit, gramsPerLiter

**GasComponent** (1,203 entities)
- Gas atmosphere requirements
- Properties: gasType, gasPercentage
- Common gases: Air, N2, CO2, H2, CH4, CO

### Cross-Database Integration Points

**Integration 1: MediaDive → BacDive (Primary Integration)**
- Connection: `schema:hasBacDiveID` (integer matching)
- Coverage: 73% of MediaDive strains have BacDiveID
- MediaDive provides: Growth conditions, media recipes, ingredient details
- BacDive provides: Genus, species, oxygen tolerance, detailed phenotypes
- Pre-filtering needed: Yes, filter by genus/species/phenotype in BacDive
- Performance: 2-3s (Tier 1) with filters, 5-8s (Tier 2) with phenotype joins

**Integration 2: Ingredients → Chemical Databases**
- Connection: schema:hasChEBI, schema:hasKEGG, schema:hasPubChem, schema:hasCAS
- Coverage: ChEBI 32%, KEGG 13%, PubChem 18%, CAS 39%, GMO 41%
- Use case: Link ingredients to broader chemical knowledge
- Pre-filtering needed: No, but use OPTIONAL

**Integration 3: Media → DSMZ Documentation**
- Connection: schema:hasLinkToSource
- Coverage: 99% of media
- Provides: Official PDF protocols

---

## Complex Query Patterns Tested

### Pattern 1: Cross-Database BacDive Integration (Genus Filter)

**Purpose**: Find growth conditions and media for bacteria of a specific genus

**Category**: Cross-Database, Performance-Critical

**Naive Approach**:
```sparql
# Without genus filter - processes all 97K BacDive strains
WHERE {
  GRAPH <http://rdfportal.org/dataset/bacdive> {
    ?strain schema:hasBacDiveID ?bacDiveID .
  }
  GRAPH <http://rdfportal.org/dataset/mediadive> {
    ?mediaDiveStrain schema:hasBacDiveID ?bacDiveID .
  }
}
```

**What Happened**: Query was slow (5-10s), returned many results without context

**Correct Approach**:
```sparql
# With genus filter - processes only ~5K Bacillus strains
WHERE {
  GRAPH <http://rdfportal.org/dataset/bacdive> {
    ?strain schema:hasBacDiveID ?bacDiveID ;
            schema:hasGenus "Bacillus" ;
            schema:hasSpecies ?species .
  }
  GRAPH <http://rdfportal.org/dataset/mediadive> {
    ?mediaDiveStrain schema:hasBacDiveID ?bacDiveID .
    ?growth schema:relatedToStrain ?mediaDiveStrain ;
            schema:partOfMedium ?medium ;
            schema:growthTemperature ?temp .
    ?medium rdfs:label ?mediumLabel .
  }
}
ORDER BY DESC(?temp) LIMIT 20
```

**What Knowledge Made This Work**:
- Strategy 2: Pre-filtering by genus reduces 97K strains to 5K (95% reduction)
- Strategy 1: Explicit GRAPH clauses for each database
- Strategy 10: LIMIT clause for result management
- Performance: 2-3s with genus filter

**Results Obtained**:
- Found 20 thermophilic Bacillus strains with media
- Highest temp: Bacillus caldolyticus at 70°C on NUTRIENT AGAR
- Sample: Bacillus smithii at 55°C, Bacillus alveayuensis at 55°C

**Natural Language Question Opportunities**:
1. "What media are used to culture thermophilic Bacillus species?" - Category: Integration
2. "Which Bacillus strains can grow above 60°C and what media support them?" - Category: Structured Query

---

### Pattern 2: BacDive Phenotype Integration (Oxygen Tolerance)

**Purpose**: Find anaerobic bacteria and their specialized media

**Category**: Cross-Database, Advanced

**Correct Approach**:
```sparql
WHERE {
  GRAPH <http://rdfportal.org/dataset/bacdive> {
    ?bacDiveStrain rdfs:label ?strainLabel ;
                   schema:hasBacDiveID ?bacDiveID .
    ?oxy a schema:OxygenTolerance ;
         schema:describesStrain ?bacDiveStrain ;
         schema:hasOxygenTolerance ?oxygenTolerance .
    FILTER(CONTAINS(LCASE(?oxygenTolerance), "anaero"))
  }
  GRAPH <http://rdfportal.org/dataset/mediadive> {
    ?mediaDiveStrain schema:hasBacDiveID ?bacDiveID .
    ?growth schema:relatedToStrain ?mediaDiveStrain ;
            schema:partOfMedium ?medium ;
            schema:growthTemperature ?temp .
    ?medium rdfs:label ?mediumLabel .
  }
}
ORDER BY DESC(?temp) LIMIT 20
```

**What Knowledge Made This Work**:
- BacDive has OxygenTolerance phenotype (schema:describesStrain pattern)
- Pre-filtering on oxygen tolerance reduces strains before join
- Performance: 5-8s (Tier 2) due to phenotype join complexity

**Results Obtained**:
- Found hyperthermophilic anaerobes: Pyrolobus fumarii (103°C), Pyrococcus kukulkanii (100°C)
- Media include specialized formulations: PYROLOBUS FUMARII MEDIUM, PYROCOCCUS MEDIUM
- All extreme thermophiles are obligate anaerobes

**Natural Language Question Opportunities**:
1. "What anaerobic bacteria grow above 90°C and what media are used?" - Category: Integration
2. "Which culture media support obligate anaerobes from hydrothermal vents?" - Category: Specificity

---

### Pattern 3: Cross-Database Ingredient Details

**Purpose**: Find reducing agents used in Clostridium culture media

**Category**: Cross-Database, Advanced

**Correct Approach**:
```sparql
SELECT DISTINCT ?species ?mediumLabel ?ingredientLabel ?gPerL ?chebi
WHERE {
  GRAPH <http://rdfportal.org/dataset/bacdive> {
    ?bacDiveStrain schema:hasBacDiveID ?bacDiveID ;
                   schema:hasGenus "Clostridium" ;
                   schema:hasSpecies ?species .
  }
  GRAPH <http://rdfportal.org/dataset/mediadive> {
    ?mediaDiveStrain schema:hasBacDiveID ?bacDiveID .
    ?growth schema:relatedToStrain ?mediaDiveStrain ;
            schema:partOfMedium ?medium .
    ?medium rdfs:label ?mediumLabel .
    
    ?composition schema:partOfMedium ?medium ;
                 schema:containsIngredient ?ingredient ;
                 schema:gramsPerLiter ?gPerL .
    ?ingredient rdfs:label ?ingredientLabel .
    OPTIONAL { ?ingredient schema:hasChEBI ?chebi }
    FILTER(CONTAINS(LCASE(?ingredientLabel), "cysteine") || 
           CONTAINS(LCASE(?ingredientLabel), "na2s") || 
           CONTAINS(LCASE(?ingredientLabel), "sulfide"))
  }
}
ORDER BY ?species DESC(?gPerL) LIMIT 30
```

**What Knowledge Made This Work**:
- Genus filter reduces strains before composition join
- FILTER on ingredient labels identifies reducing agents
- OPTIONAL for ChEBI (32% coverage)
- Composition data links medium to ingredients with concentrations

**Results Obtained**:
- L-Cysteine HCl x H2O: ChEBI 91248, commonly 0.5 g/L
- Na2S x 9 H2O: ChEBI 76209, commonly 0.3-0.5 g/L
- Found in media like ACETOBACTERIUM MEDIUM, CLOSTRIDIUM ACETOBUTYLICUM MEDIUM

**Natural Language Question Opportunities**:
1. "What reducing agents are used in Clostridium culture media and at what concentrations?" - Category: Structured Query
2. "Which Clostridium media contain sodium sulfide as a reducing agent?" - Category: Specificity

---

### Pattern 4: Temperature Range Queries (Extremophiles)

**Purpose**: Find hyperthermophilic archaea and their specialized media

**Category**: Structured Query, Performance-Critical

**Correct Approach**:
```sparql
SELECT ?medium ?mediumLabel ?strain ?species ?temp ?taxGroup
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?growth a schema:GrowthCondition ;
          schema:partOfMedium ?medium ;
          schema:relatedToStrain ?strain ;
          schema:growthTemperature ?temp .
  ?medium rdfs:label ?mediumLabel .
  ?strain schema:hasSpecies ?species ;
          schema:belongsTaxGroup ?taxGroup .
  FILTER(?taxGroup = "Archaeon" && ?temp > 75)
}
ORDER BY DESC(?temp) LIMIT 20
```

**What Knowledge Made This Work**:
- Numeric FILTER on temperature is efficient
- belongsTaxGroup provides taxonomic classification
- No need for cross-database join for MediaDive-only queries

**Results Obtained**:
- Pyrolobus fumarii: 103°C (highest temperature)
- Pyrococcus kukulkanii: 100°C
- Hyperthermus butylicus: 99°C
- Methanopyrus kandleri: 98°C
- All require specialized media (PYROLOBUS FUMARII MEDIUM, PYROCOCCUS MEDIUM, etc.)

**Natural Language Question Opportunities**:
1. "Which archaeal species grow above 90°C and what media support them?" - Category: Completeness
2. "What is the highest growth temperature recorded for any organism in MediaDive?" - Category: Precision

---

### Pattern 5: pH Range Queries (Acidophiles/Alkaliphiles)

**Purpose**: Find media for extreme pH conditions

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?medium ?label ?minPH ?maxPH ?isComplex
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?medium a schema:CultureMedium ;
          rdfs:label ?label ;
          schema:hasMinPH ?minPH ;
          schema:hasMaxPH ?maxPH ;
          schema:isComplex ?isComplex .
  FILTER(?maxPH < 4.0)
}
ORDER BY ?minPH LIMIT 20
```

**Results Obtained - Acidophiles**:
- ACIDIANUS SP. JP7 MEDIUM: pH 0.8 (most extreme)
- THERMOPLASMA ACIDOPHILUM MEDIUM: pH 1.0
- FERROPLASMA ACIDIPHILUM MEDIUM: pH 1.6-1.8

**Results Obtained - Alkaliphiles (minPH > 10)**:
- MJ/YTCT MEDIUM: pH 11.5 (most extreme)
- SERPENTINOMONAS MINIMAL MEDIUM: pH 11.0
- HALANAEROBIUM HYDROGENIFORMANS MEDIUM: pH 11.0

**Natural Language Question Opportunities**:
1. "What culture media are designed for acidophilic organisms with pH below 2?" - Category: Specificity
2. "Which media support growth at pH above 10?" - Category: Completeness

---

### Pattern 6: Ingredient Cross-References

**Purpose**: Find ingredients with links to chemical databases

**Category**: Integration, Partial Coverage

**Correct Approach**:
```sparql
SELECT ?ingredient ?label ?chebi ?kegg ?cas
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?ingredient a schema:Ingredient ;
              rdfs:label ?label .
  OPTIONAL { ?ingredient schema:hasChEBI ?chebi }
  OPTIONAL { ?ingredient schema:hasKEGG ?kegg }
  OPTIONAL { ?ingredient schema:hasCAS ?cas }
  FILTER(BOUND(?chebi) && BOUND(?kegg))
}
ORDER BY ?label LIMIT 30
```

**What Knowledge Made This Work**:
- OPTIONAL blocks for partial coverage databases
- FILTER with BOUND() to require specific databases
- Strategy 7: OPTIONAL ordering after required patterns

**Results Obtained**:
- 2-Mercaptoethanesulfonate: ChEBI 17905, KEGG C03576
- Agar: ChEBI 2509, KEGG C08815
- Biotin: ChEBI 15956, KEGG C00120
- Total: ~200 ingredients have both ChEBI and KEGG

**Natural Language Question Opportunities**:
1. "Which media ingredients have both ChEBI and KEGG identifiers?" - Category: Integration
2. "What is the ChEBI identifier for glucose in MediaDive?" - Category: Precision

---

### Pattern 7: Medium Composition Details

**Purpose**: Get complete ingredient list for a specific medium

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?ingredientLabel ?gPerL ?chebi
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?composition a schema:MediumComposition ;
               schema:partOfMedium <https://purl.dsmz.de/mediadive/medium/377> ;
               schema:containsIngredient ?ingredient ;
               schema:gramsPerLiter ?gPerL .
  ?ingredient rdfs:label ?ingredientLabel .
  OPTIONAL { ?ingredient schema:hasChEBI ?chebi }
}
ORDER BY DESC(?gPerL)
```

**What Knowledge Made This Work**:
- Filter by specific medium first (unbounded queries timeout)
- MediumComposition links medium to ingredients with concentrations
- Strategy 10: Use LIMIT or specific medium filter

**Results Obtained** (PYROCOCCUS MEDIUM):
- Sulfur: 30.0 g/L (ChEBI 26833)
- Peptone: 5.0 g/L
- MgCl2 x 6 H2O: 2.75 g/L (ChEBI 86345)
- 28 total ingredients with trace elements

**Natural Language Question Opportunities**:
1. "What are all the ingredients in PYROCOCCUS MEDIUM and their concentrations?" - Category: Completeness
2. "Which media contain sulfur as the primary carbon/energy source?" - Category: Structured Query

---

### Pattern 8: Gas Atmosphere Requirements

**Purpose**: Find media with specific gas atmosphere requirements

**Category**: Specificity

**Correct Approach**:
```sparql
SELECT ?gasType ?percentage ?medium ?mediumLabel
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?gas a schema:GasComponent ;
       schema:gasType ?gasType ;
       schema:gasPercentage ?percentage ;
       schema:partOfMedium ?medium .
  ?medium rdfs:label ?mediumLabel .
}
ORDER BY ?gasType DESC(?percentage) LIMIT 30
```

**Results Obtained**:
- Air: Up to 100% for aerobic organisms
- CH4 (methane): Up to 50% for methanotrophs (METHYLOCOCCUS MEDIUM)
- CO: Up to 100% for carboxydotrophs (MOORELLA THERMOACETICA MEDIUM)
- CO2: Up to 100% for various anaerobes
- H2: Common in hydrogenotrophic media

**Natural Language Question Opportunities**:
1. "Which media require methane (CH4) in the gas atmosphere?" - Category: Specificity
2. "What media are designed for carbon monoxide-utilizing bacteria?" - Category: Specificity

---

### Pattern 9: Psychrophilic Organisms

**Purpose**: Find cold-loving organisms and their cultivation conditions

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?medium ?mediumLabel ?strain ?species ?temp ?taxGroup
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?growth schema:partOfMedium ?medium ;
          schema:relatedToStrain ?strain ;
          schema:growthTemperature ?temp .
  ?medium rdfs:label ?mediumLabel .
  ?strain schema:hasSpecies ?species ;
          schema:belongsTaxGroup ?taxGroup .
  FILTER(?temp < 10)
}
ORDER BY ?temp LIMIT 30
```

**Results Obtained**:
- Neisseria zalophi: 0°C (BHI MEDIUM)
- Streptosporangium carneum: 2°C
- Clostridium psychrophilum: 4°C
- Octadecabacter antarcticus: 4°C (BACTO MARINE BROTH)
- Many polar marine bacteria at 4-5°C

**Natural Language Question Opportunities**:
1. "Which bacteria can grow below 5°C and what media are used?" - Category: Completeness
2. "What culture media are suitable for Antarctic marine bacteria?" - Category: Specificity

---

### Pattern 10: Taxonomic Group Distribution

**Purpose**: Count organisms by taxonomic group

**Category**: Completeness

**Correct Approach**:
```sparql
SELECT ?taxGroup (COUNT(?strain) as ?count)
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?strain a schema:Strain ;
          schema:belongsTaxGroup ?taxGroup .
}
GROUP BY ?taxGroup
ORDER BY DESC(?count)
```

**Results Obtained**:
- Bacterium: 32,662 strains
- Fungus: 5,079 strains
- Yeast: 3,125 strains
- Microalgae: 1,289 strains
- Archaeon: 952 strains
- Macroalgae: 884 strains
- Phage: 602 strains
- Protist: 380 strains

**Natural Language Question Opportunities**:
1. "How many archaeal strains are in MediaDive?" - Category: Completeness
2. "What is the distribution of organism types in the MediaDive database?" - Category: Completeness

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. **Marine media search**: Found 23 marine media including BACTO MARINE BROTH, MARINE AGAR
   - Usage: Marine organism cultivation questions

2. **Ingredient with ChEBI**: Glucose (ChEBI 17234), Sulfur (ChEBI 26833), Biotin (ChEBI 15956)
   - Usage: Chemical cross-reference questions

3. **Extreme temperature media**: PYROLOBUS FUMARII MEDIUM (103°C), Neisseria medium (0°C)
   - Usage: Extremophile cultivation questions

4. **Complex media**: OMIZ-PAT Medium (97 ingredients), DESULFOBULBUS SP. MEDIUM (55 ingredients)
   - Usage: Complex formulation questions

5. **BacDive-linked strains**: Bacillus subtilis (BacDiveID 1172), E. coli (BacDiveID 4435)
   - Usage: Cross-database integration questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What culture media support thermophilic Bacillus species and what are their growth temperatures?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: BacDive genus filter strategy, GRAPH clauses, GrowthCondition structure
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

2. "Which anaerobic bacteria grow above 90°C and what specialized media are used for their cultivation?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: OxygenTolerance phenotype in BacDive, temperature filtering
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

3. "What reducing agents (like cysteine or sodium sulfide) are used in Clostridium culture media?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: Genus filter, ingredient label matching, ChEBI cross-references
   - Category: Integration / Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

4. "For Bacillus strains with BacDive records, what growth temperatures and media are used?"
   - Databases involved: BacDive, MediaDive
   - Knowledge Required: BacDiveID linking, genus pre-filtering
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

**Performance-Critical Questions**:

5. "How many culture media in MediaDive are designed for archaea?"
   - Database: MediaDive
   - Knowledge Required: belongsTaxGroup property, efficient counting
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 10

6. "What are all the ingredients in PYROCOCCUS MEDIUM?"
   - Database: MediaDive
   - Knowledge Required: MediumComposition structure, medium-specific filtering
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 7

7. "Which media have more than 50 ingredients?"
   - Database: MediaDive
   - Knowledge Required: Composition counting, GROUP BY, HAVING
   - Category: Structured Query
   - Difficulty: Medium

**Error-Avoidance Questions**:

8. "Which media ingredients have both ChEBI and KEGG cross-references?"
   - Database: MediaDive
   - Knowledge Required: OPTIONAL for partial coverage, FILTER with BOUND()
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

**Complex Filtering Questions**:

9. "What culture media are suitable for organisms that grow at pH below 2?"
   - Database: MediaDive
   - Knowledge Required: Numeric pH filtering (hasMinPH, hasMaxPH)
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

10. "Which bacteria can grow below 5°C and what media support them?"
    - Database: MediaDive
    - Knowledge Required: Temperature filtering, taxonomic group filtering
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Pattern 9

11. "What media are designed for methane-oxidizing bacteria?"
    - Database: MediaDive
    - Knowledge Required: GasComponent structure, gasType filtering
    - Category: Specificity
    - Difficulty: Medium
    - Pattern Reference: Pattern 8

12. "Which alkaliphilic media have pH above 10?"
    - Database: MediaDive
    - Knowledge Required: Numeric pH filtering
    - Category: Specificity
    - Difficulty: Easy
    - Pattern Reference: Pattern 5

13. "What is the highest growth temperature recorded for any organism in MediaDive?"
    - Database: MediaDive
    - Knowledge Required: MAX aggregation, GrowthCondition structure
    - Category: Precision
    - Difficulty: Easy
    - Pattern Reference: Pattern 4

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the MediaDive ID for NUTRIENT AGAR medium?"
   - Method: Keyword search or direct lookup
   - Knowledge Required: None
   - Category: Entity Lookup
   - Difficulty: Easy

2. "How many culture media are in the MediaDive database?"
   - Method: COUNT query
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy

3. "What organism types (taxonomic groups) are covered in MediaDive?"
   - Method: DISTINCT query
   - Knowledge Required: None
   - Category: Completeness
   - Difficulty: Easy

**ID Mapping Questions**:

4. "What is the ChEBI identifier for glucose in MediaDive?"
   - Method: Ingredient lookup
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

5. "Which MediaDive strain corresponds to BacDive ID 1172?"
   - Method: BacDiveID lookup
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source**:
- → BacDive: Strain records link via BacDiveID for phenotypic data
- → Chemical databases: Ingredients link via ChEBI, KEGG, PubChem, CAS
- → DSMZ: Media link to PDF protocols via hasLinkToSource

**This Database as Target**:
- BacDive →: Strain phenotypes can be enriched with MediaDive growth conditions
- Taxonomy →: Species classifications can be validated

**Complex Multi-Database Paths**:
- BacDive → MediaDive → Chemical (ChEBI): Link bacterial phenotypes to growth media to ingredient chemistry
- BacDive (genus) → MediaDive (growth) → MediaDive (composition): Find all ingredients for bacteria of a specific genus

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Pre-filtering strategy (Strategy 2)**: Essential for cross-database queries - genus/species filters provide 95-99% reduction
2. **OPTIONAL for partial coverage**: Critical for ingredient cross-references (32-41% coverage)
3. **Specific medium filtering**: Required to avoid timeout on composition queries
4. **BacDiveID integer matching**: Direct matching without URI conversion

### Common Pitfalls Discovered

1. **Unbounded composition queries**: Must filter by medium or use LIMIT
2. **Requiring all cross-references**: Use OPTIONAL + OR filter instead of AND
3. **Missing pre-filter in cross-database queries**: Always filter in BacDive GRAPH first

### Recommendations for Question Design

1. **Cross-database questions should involve BacDive**: The primary integration point with 73% coverage
2. **Extremophile questions work well**: Clear temperature/pH ranges with interesting organisms
3. **Ingredient questions need OPTIONAL handling**: Due to partial cross-reference coverage
4. **Avoid unbounded composition counts**: Always scope to specific media or use aggregation

### Performance Notes

- Single-database queries: 1-2s typically
- Cross-database with genus filter: 2-3s (Tier 1)
- Cross-database with phenotype join: 5-8s (Tier 2)
- Composition queries need medium filter or LIMIT

---

## Notes and Observations

1. **Rich extremophile coverage**: MediaDive excels at extremophile cultivation data
   - Hyperthermophiles up to 103°C
   - Psychrophiles down to 0°C
   - Acidophiles at pH 0.8
   - Alkaliphiles at pH 11.5

2. **Hierarchical recipe structure**: Medium → Solution → SolutionRecipe → Ingredient provides detailed protocols

3. **Gas atmosphere data**: Unique feature - supports methanotrophs, carboxydotrophs, hydrogen-oxidizers

4. **PDF documentation**: 99% coverage provides authoritative protocols

5. **JCM media included**: Database includes media from Japanese Collection of Microorganisms

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database BacDive integration, extremophile cultivation, reducing agents
- Avoid: Unbounded composition queries without filters
- Focus areas: Temperature extremes, pH extremes, anaerobic bacteria, chemical cross-references

**Further Exploration Needed** (if any):
- Solution hierarchy detailed structure (limited exploration)
- Modification/ModificationDetail entities (not explored)

---

**Session Complete - Ready for Next Database**

---

## Session Summary

```
Database: mediadive
Status: ✅ COMPLETE
Report: /evaluation/exploration/mediadive_exploration.md
Patterns Tested: 10+ complex patterns
Questions Identified: 18+ questions
Integration Points: 3 (BacDive primary, Chemical databases, DSMZ docs)
```
