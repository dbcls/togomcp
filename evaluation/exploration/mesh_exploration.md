# Medical Subject Headings (MeSH) Exploration Report

## Database Overview
- **Purpose**: National Library of Medicine's controlled vocabulary for biomedical literature indexing
- **Scope**: 2,456,909 total entities covering biomedical terminology
- **Key data types**:
  - Topical descriptors (30,248) - main subject headings
  - Terms (869,536)
  - Concepts (466,976)
  - Chemical records (250,445)
- **Structure**: Hierarchical classification with 16 main tree categories

## Schema Analysis (from MIE file)

### Main Properties
- **meshv:TopicalDescriptor**: Main subject heading entity
- **rdfs:label**: Descriptor/entity label
- **meshv:identifier**: MeSH ID (e.g., "D003920")
- **meshv:treeNumber**: Hierarchical alphanumeric classification codes
- **meshv:broaderDescriptor**: Parent descriptor (CRITICAL: NOT meshv:broader)
- **meshv:annotation**: Scope notes and indexing guidance (CRITICAL: NOT meshv:scopeNote)
- **meshv:preferredConcept**: Links to main concept
- **meshv:Concept**: Conceptual entity with preferred term
- **meshv:preferredTerm**: Main term for concept
- **meshv:Term**: Term entity (uses meshv:prefLabel NOT rdfs:label)
- **meshv:SCR_Chemical**: Supplementary chemical record
- **meshv:registryNumber**: Chemical registry number (CAS-like)
- **meshv:allowableQualifier**: Permitted subheadings for descriptors
- **meshv:Qualifier**: Subheading entity (e.g., "drug therapy", "diagnosis")
- **meshv:thesaurusID**: Cross-references to external databases

### Important Relationships
- **Hierarchical structure**: meshv:broaderDescriptor creates parent-child tree
- **Tree number system**: Alphanumeric codes for classification (e.g., C18.452.394.750)
- **16 main categories**: A-N with subcategories
- **Descriptor-Concept-Term structure**: Three-level semantic organization
- **Qualifier constraints**: meshv:allowableQualifier limits descriptor-qualifier combinations
- **Average cardinality**: 
  - 2.7 tree numbers per descriptor
  - 1.9 terms per concept
  - 22 qualifiers per descriptor
- **Cross-references**: 916K total (37% coverage)
  - FDA SRS: 22.6K
  - FDA UNII: 22.6K
  - OMIM: 12.5K
  - INN: 8.8K
  - GHR: 3.8K
  - ChEBI: 2.5K

### Query Patterns Observed
1. **CRITICAL property names**:
   - Use `meshv:broaderDescriptor` (NOT meshv:broader)
   - Use `meshv:annotation` (NOT meshv:scopeNote)
   - Terms use `meshv:prefLabel` (NOT rdfs:label)
2. **Use bif:contains for search**: NOT FILTER(CONTAINS(...))
3. **Add relevance scoring**: `option (score ?sc)` with ORDER BY DESC(?sc)
4. **Include FROM clause**: `FROM <http://id.nlm.nih.gov/mesh>`
5. **Always add LIMIT**: 20-100 for exploratory queries (2.5M+ entities)
6. **Use OPTIONAL**: For variable coverage (annotation, treeNumber)
7. **Tree number filtering**: Use SUBSTR or STRSTARTS for category filtering
8. **Transitive queries**: meshv:broaderDescriptor+ from specific descriptors

## Search Queries Performed

### Query 1: Search diabetes descriptors
**Tool**: TogoMCP run_sparql with bif:contains
**Result**: Found 10 diabetes-related descriptors:
- D003920: "Diabetes Mellitus" (main term)
- D048909: "Diabetes Complications"
- D000071698: "Latent Autoimmune Diabetes in Adults"
- D003919: "Diabetes Insipidus" (unrelated to diabetes mellitus)
- D003921-D003924: Various diabetes mellitus types
- D018500, D020790: Diabetes insipidus subtypes

### Query 2: Search cancer-related terms
**Tool**: TogoMCP:search_mesh_entity
**Query**: "cancer"
**Result**: Found 10 cancer-related entities including:
- T653055: "5T4 cancer vaccine"
- T362408: "Adrenal Cancer"
- T362378: "Adrenal Cortex Cancer"
- T746984: "Amplified in Breast Cancer-1 Protein"
- T362812: "Anal Cancer"
- T834667: "Androgen-Independent Prostatic Cancer"
Note: Mix of disease descriptors, vaccines, and proteins

### Query 3: Search pharmaceutical compound
**Tool**: TogoMCP:search_mesh_entity
**Query**: "aspirin"
**Result**: Found 10 aspirin-related entities:
- T003713: "Aspirin" (main descriptor)
- T128362: "5-N-succinylamino aspirin"
- T723646: "Aspirin Induced Asthma"
- T005110: "Aspirin Tolerance Test"
- T000875197: "Aspirin, Dipyridamole Drug Combination"
- T002625: "Aspirin-Like Agents"
Note: Includes drug, derivatives, combinations, conditions, and tests

### Query 4: Search anatomical structures
**Tool**: TogoMCP:search_mesh_entity
**Query**: "heart ventricle"
**Result**: Found 3 anatomical entities:
- T019241: "Heart Ventricle" (main anatomical descriptor)
- T019246: "Heart Ventricle, Artificial"
- T538027: "Heart Ventricles"
Note: Precise match with natural and artificial ventricle terms

### Query 5: Search medical procedures
**Tool**: TogoMCP:search_mesh_entity
**Query**: "radiotherapy"
**Result**: Found 10 radiotherapy-related procedures:
- T000890488: "3-D Conformal Radiotherapy"
- T055721: "Adjuvant Radiotherapy"
- T819516: "Carbon Ion Radiotherapy"
- T035083: "Computer-Assisted Radiotherapy Planning"
- T060031: "Conformal Radiotherapy"
- T035079: "Dosage, Radiotherapy"
- T819514: "Heavy Ion Radiotherapy"
Note: Diverse therapy techniques and planning methods

### Query 6: Search pathogen/organism
**Tool**: TogoMCP:search_mesh_entity
**Query**: "influenza virus"
**Result**: Found 10 influenza virus strain entities:
- T844855: "Canine Influenza Virus, H3N8 Subtype"
- T844853: "Equine Influenza Virus, H3N8 Subtype"
- T001132893: "H1N1 Influenza Virus"
- T001132892: "H5N1 Avian Influenza Virus"
- T001133205: "H5N6 Avian Influenza Virus"
- T770463: "H1N1 influenza virus H1 hemagglutinin"
Note: Species-specific and subtype-specific virus entities

## SPARQL Queries Tested

```sparql
# Query 1: Search descriptors with relevance ranking (VERIFIED)
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT ?descriptor ?label
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    rdfs:label ?label .
  ?label bif:contains "'diabetes'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: 10 diabetes descriptors ranked by relevance
```

```sparql
# Query 2: Get hierarchical classification (from MIE)
PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?parent ?parentLabel
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  mesh:D003920 meshv:broaderDescriptor+ ?parent .
  ?parent rdfs:label ?parentLabel .
}
# CRITICAL: Use broaderDescriptor (NOT broader)
# Results: Returns parent categories of Diabetes Mellitus up the hierarchy
```

```sparql
# Query 3: Find descriptors in specific tree category with allowable qualifiers
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?descriptor ?label (COUNT(DISTINCT ?qualifier) AS ?qualifierCount)
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    rdfs:label ?label ;
    meshv:treeNumber ?treeNum .
  FILTER(STRSTARTS(?treeNum, "C18"))
  OPTIONAL { ?descriptor meshv:allowableQualifier ?qualifier }
}
GROUP BY ?descriptor ?label
ORDER BY DESC(?qualifierCount)
LIMIT 20
# Results: Finds descriptors in category C18 (Nutritional and Metabolic Diseases)
# with counts of their allowable qualifiers
```

## Interesting Findings

### Specific Entities for Questions
1. **D003920**: "Diabetes Mellitus" - main diabetes descriptor
2. **D048909**: "Diabetes Complications"
3. **D003924**: "Diabetes Mellitus, Type 2"
4. **D003922**: "Diabetes Mellitus, Type 1"
5. **C517652**: "Insulin Glargine" (chemical record)

### Unique Properties
- **CRITICAL property names**: broaderDescriptor, annotation, prefLabel (for Terms)
- **Three-level structure**: Descriptor → Concept → Term
- **Tree number system**: Alphanumeric hierarchical codes
- **16 main categories**: A (Anatomy) through N (Health Care)
- **Qualifier constraints**: Only specific qualifiers allowed per descriptor
- **Annual updates**: Published yearly by NLM

### Connections to Other Databases
- **FDA SRS/UNII**: 22.6K pharmaceutical substances
- **OMIM**: 12.5K genetic disorders
- **INN**: 8.8K international drug names
- **GHR**: 3.8K genetics home reference
- **ChEBI**: 2.5K chemical entities
- **FMA**: 1.1K anatomical structures
- **SNOMED CT**: 800+ clinical terms

### Specific, Verifiable Facts
1. MeSH contains 2,456,909 total entities
2. 30,248 topical descriptors (main subject headings)
3. 869,536 terms
4. 250,445 chemical records
5. ~40% of descriptors have annotations
6. ~95% of descriptors have tree numbers
7. ~99.6% of descriptors have broaderDescriptor relationships
8. Average 2.7 tree numbers per descriptor
9. Average 22 qualifiers per descriptor
10. 916K cross-references (37% coverage)

## Question Opportunities by Category

### Precision
- "What is the MeSH descriptor ID for Diabetes Mellitus?" (D003920)
- "What is the MeSH ID for Insulin Glargine?" (C517652)
- "How many tree numbers does Diabetes Mellitus have?"

### Completeness
- "List all subtypes of Diabetes Mellitus"
- "What are all allowable qualifiers for Diabetes Mellitus descriptor?"
- "How many chemical records contain 'insulin'?"

### Integration
- "What is the OMIM cross-reference for a specific MeSH descriptor?"
- "Link MeSH Diabetes Mellitus to ChEBI insulin compounds"
- "Find FDA UNII codes for insulin-related chemicals"

### Currency
- "What are newly added descriptors in MeSH 2024?"
- "How many descriptors were updated recently?"

### Specificity
- "What is the tree number for Diabetes Mellitus?" (C18.452.394.750)
- "What is the annotation for Diabetes Mellitus descriptor?"
- "What qualifiers are NOT allowed with diabetes descriptor?"

### Structured Query
- "Count descriptors by main tree category (A-N)"
- "Find all parent categories of Diabetes Mellitus"
- "Search chemicals with both 'insulin' AND 'glargine'"

## Notes

### Limitations and Challenges
1. **CRITICAL property names**: Easy to use wrong properties (broader, scopeNote)
2. **Large dataset**: 2.5M+ entities require careful query optimization
3. **Variable coverage**: Only ~40% have annotations
4. **Three-level complexity**: Descriptor-Concept-Term structure
5. **Tree number system**: Alphanumeric codes require understanding
6. **Qualifier constraints**: Complex rules for allowable combinations

### Best Practices for Querying
1. **CRITICAL**: Use correct property names:
   - `meshv:broaderDescriptor` (NOT meshv:broader)
   - `meshv:annotation` (NOT meshv:scopeNote or skos:scopeNote)
   - `meshv:prefLabel` for Terms (NOT rdfs:label)
2. **Use bif:contains**: NOT FILTER(CONTAINS(...))
3. **Add relevance scoring**: `option (score ?sc)`
4. **Include FROM clause**: `FROM <http://id.nlm.nih.gov/mesh>`
5. **Always add LIMIT**: 20-100 for exploratory queries
6. **Use OPTIONAL**: For annotation, treeNumber (variable coverage)
7. **Start specific**: For broaderDescriptor+ transitive queries
8. **Tree filtering**: SUBSTR(?treeLabel, 1, 1) for main categories

### Data Quality
- **Topical descriptors**: 100% have labels
- **Annotations**: ~40% coverage
- **Tree numbers**: ~95% coverage
- **Hierarchical relationships**: ~99.6% have broaderDescriptor
- **Cross-references**: 37% coverage (916K total)
- **Update frequency**: Annual releases
- **Curation**: Professionally maintained by NLM
