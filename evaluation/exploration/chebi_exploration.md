# ChEBI Exploration Report

## Database Overview
- **Purpose**: ChEBI (Chemical Entities of Biological Interest) is an ontology database containing 217,000+ chemical entities of biological interest
- **Scope**: Small molecules, atoms, ions, functional groups, and macromolecules with hierarchical classification
- **Key data types**: Molecular structure data (formula, mass, InChI, SMILES), biological roles, chemical relationships (conjugate acids/bases, tautomers, enantiomers), and cross-references to 20+ databases

## Schema Analysis (from MIE file)

### Main Properties Available
- **Core identification**: rdfs:label, oboInOwl:id, oboInOwl:hasOBONamespace
- **Structural data**: formula, mass, charge, smiles, inchi, inchikey
- **Definitions**: obo:IAO_0000115 (textual definitions)
- **Synonyms**: hasRelatedSynonym, hasExactSynonym
- **Cross-references**: hasDbXref (to CAS, KEGG, DrugBank, PubChem, HMDB, etc.)
- **Classification**: rdfs:subClassOf (hierarchical relationships)
- **Status**: owl:deprecated (indicates obsolete entries)

### Important Relationships
- Hierarchical classification via rdfs:subClassOf
- Chemical relationships via OWL restrictions:
  - has_role (biological roles via RO_0000087)
  - is_conjugate_acid_of / is_conjugate_base_of
  - is_tautomer_of
  - is_enantiomer_of
- **CRITICAL namespace distinction**:
  - Data properties use: `http://purl.obolibrary.org/obo/chebi/` (with trailing slash)
  - Relationship properties use: `http://purl.obolibrary.org/obo/chebi#` (with hash)

### Query Patterns Observed
- OWL ontology structure with owl:Class entities
- Use bif:contains for full-text search with relevance scoring
- Relationships encoded as OWL restrictions (not direct properties)
- Filter by CHEBI_ URI prefix to exclude ontology metadata
- OPTIONAL clauses needed for molecular properties (abstract classes lack them)

## Search Queries Performed

1. **Query**: "aspirin" in ChEBI ontology (via OLS4 searchClasses)
   - **Results**: Found 10 aspirin-related entities:
     - CHEBI:138614 - aspirin-triggered resolvin D2
     - CHEBI:140208 - aspirin-triggered protectin D1(1-)
     - CHEBI:138618 - aspirin-triggered resolvin D6
     - CHEBI:138617 - aspirin-triggered resolvin D5
     - CHEBI:138615 - aspirin-triggered resolvin D3
     - CHEBI:138616 - aspirin-triggered resolvin D4
     - CHEBI:140202 - aspirin-triggered protectin D1
     - CHEBI:138179 - aspirin-triggered resolvin D1
     - CHEBI:141699 - aspirin-based probe AP
     - CHEBI:134674 - Yosprala (aspirin + omeprazole mixture)
   - All are specialized derivatives or formulations involving aspirin
   - Shows rich hierarchy with resolvins (anti-inflammatory mediators)

2. **Direct lookup**: Aspirin (acetylsalicylic acid) CHEBI:15365 properties
   - **Results**:
     - Label: "acetylsalicylic acid"
     - Formula: C9H8O4
     - Mass: 180.15740
     - SMILES: CC(=O)Oc1ccccc1C(O)=O
     - InChIKey: BSYNRYMUTXBXSQ-UHFFFAOYSA-N

3. **Query**: "glucose" in ChEBI ontology
   - **Results**: Found 268 glucose-related entities including:
     - CHEBI:17234 - glucose (main entry, aldohexose)
     - CHEBI:229783 - glucose transporter 1 inhibitor
     - Multiple glucose derivatives and conjugates
   - Shows comprehensive carbohydrate coverage

4. **Query**: "caffeine" in ChEBI ontology  
   - **Results**: Found 16 caffeine-related entities including:
     - CHEBI:27732 - caffeine (trimethylxanthine, purine alkaloid)
     - CHEBI:177330 - caffeine-d9 (deuterated isotopologue)
     - CHEBI:178066 - caffeine-(trimethyl-(13)C3) (13C-modified)
     - CHEBI:31332 - caffeine monohydrate
   - Demonstrates isotopologue and derivative coverage

5. **Query**: "insulin" in ChEBI ontology
   - **Results**: Search via OLS4 for insulin-related entities
   - Shows protein hormone and peptide coverage in ChEBI

## SPARQL Queries Tested

```sparql
# Query 1: Get molecular properties for aspirin
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

# Results: Successfully retrieved complete molecular structure data for aspirin
# This demonstrates access to core molecular properties needed for drug databases
```

```sparql
# Query 2: Full-text search for glucose (from MIE examples)
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

# Expected results: D-glucose, beta-D-glucose, alpha-D-glucose, glucose-6-phosphate, etc.
# This shows powerful keyword search with relevance scoring
```

```sparql
# Query 3: Navigate hierarchy - find parent classes (from MIE examples)
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT ?parent ?parentLabel
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  obo:CHEBI_17203 rdfs:subClassOf ?parent .
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/CHEBI_"))
  ?parent rdfs:label ?parentLabel .
}

# Expected results: For L-proline (CHEBI:17203):
# - proline (CHEBI:26271)
# - proteinogenic amino acid (CHEBI:83813)
# Demonstrates hierarchical ontology navigation
```

```sparql
# Query 4: Find cross-references to external databases
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT ?entity ?label ?xref
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?entity a owl:Class ;
          rdfs:label ?label ;
          oboInOwl:hasDbXref ?xref .
  FILTER(STRSTARTS(?xref, "KEGG:") || STRSTARTS(?xref, "DrugBank:"))
}
LIMIT 100

# Expected results: Entities with KEGG Compound IDs and DrugBank IDs
# Demonstrates integration with external chemical databases
```

```sparql
# Query 5: Find chemical relationships via OWL restrictions
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

# Expected results: Pairs of conjugate acid-base compounds
# Shows how chemical relationships are encoded as OWL restrictions
```

## Interesting Findings

### Specific Entities for Questions
1. **Acetylsalicylic acid (aspirin)** - CHEBI:15365 - well-known drug with complete molecular data
2. **L-proline** - CHEBI:17203 - proteinogenic amino acid, good for hierarchy queries
3. **Water** - CHEBI:15377 - simplest molecule with extensive cross-references
4. **Ciprofloxacin** - CHEBI:100241 - antibiotic with conjugate base and tautomer relationships
5. **Triolein** - CHEBI:53753 - triglyceride with complex molecular structure
6. **Phosphorus atom** - CHEBI:28659 - elemental entity
7. **Aspirin-triggered resolvins** - CHEBI:138614-138618 - specialized derivatives showing hierarchy depth

### Unique Properties
- **Dual namespace system**: chebi/ for data properties, chebi# for relationships (critical to get right!)
- **OWL restriction encoding**: Biological roles and chemical relationships not as direct properties
- **Rich ontology hierarchy**: Multiple inheritance, deep classification trees
- **Comprehensive cross-references**: Links to 20+ external databases (CAS, KEGG, DrugBank, PubChem, HMDB)
- **Structure identifiers**: InChI/InChIKey for exact structure matching, SMILES for substructure

### Connections to Other Databases
- **KEGG**: Metabolic pathway connections
- **DrugBank**: Drug information
- **PubChem**: Compound data integration
- **HMDB**: Human metabolite connections
- **CAS**: Chemical registry numbers
- **UniProt**: Via RO_0000087 (has_role) relationships
- **GO**: Biological process/function connections

### Specific, Verifiable Facts
- Total chemical entities: 217,368
- Entities with formulas: 187,110 (~86%)
- Average database cross-references per entity: 1.9
- Average synonyms per entity: 1.2
- Average parent classes per entity: 1.7
- Coverage: ~91% with labels, ~86% with formulas, ~81% with InChI, ~85% with SMILES

## Question Opportunities by Category

### Precision
- "What is the ChEBI ID for acetylsalicylic acid (aspirin)?"
- "What is the molecular formula of L-proline (CHEBI:17203)?"
- "What is the InChIKey for ciprofloxacin?"
- "What is the exact molecular mass of triolein?"
- "What CAS registry number is assigned to water in ChEBI?"

### Completeness
- "List all aspirin-triggered resolvins in ChEBI"
- "How many parent classes does L-proline have?"
- "Count all chemical entities with KEGG cross-references"
- "List all conjugate bases of ciprofloxacin"
- "Find all tautomers of a specific compound"

### Integration
- "Convert ChEBI ID CHEBI:15365 to its KEGG Compound ID"
- "Find the DrugBank ID for ciprofloxacin from ChEBI"
- "Link ChEBI water (CHEBI:15377) to PubChem CID"
- "Find UniProt proteins that interact with a ChEBI compound via has_role relationship"

### Currency
- "What are the most recently added chemical entities in ChEBI (2025)?"
- "Find newly characterized resolvins added in 2024-2025"
- "What new drug compounds have been classified in recent releases?"

### Specificity
- "What is the stereochemistry of aspirin-triggered resolvin D1?"
- "What are all the hydroxy substituent positions in aspirin-triggered resolvin D2?"
- "Find the specific benzothiazole fluorophore in the aspirin-based probe AP"
- "What is the exact composition of Yosprala mixture?"

### Structured Query
- "Find all monocarboxylic acids with molecular weight between 100-200 Da"
- "Query all compounds with both formula containing 'C9' and KEGG cross-references"
- "Find all chemical entities that are conjugate acids AND have DrugBank entries"
- "Retrieve all resolvins with specific biological roles via RO_0000087"
- "Find compounds with more than 5 database cross-references using COUNT aggregation"

## Notes

### Limitations and Challenges
- **Namespace confusion**: Easy to mix up chebi/ and chebi# - critical error source
- **Abstract classes**: Many entities lack molecular properties (formula, mass, SMILES)
- **OWL restriction complexity**: Relationships encoded as restrictions, not simple properties
- **Deprecated entries**: Must filter out obsolete entities with owl:deprecated
- **Server availability**: May experience 503 errors during high load or complex queries
- **Cross-reference format**: Stored as literal strings requiring parsing (e.g., "KEGG:C00001")

### Best Practices for Querying
1. **Namespace discipline**: Use `chebi/` for formula, mass, smiles, inchi; use `chebi#` for is_conjugate_acid_of, etc.
2. **Full-text search**: Use bif:contains with single-quoted keywords for fast searches
3. **Entity filtering**: Always filter by `STRSTARTS(STR(?entity), "http://purl.obolibrary.org/obo/CHEBI_")`
4. **OPTIONAL clauses**: Use for all molecular properties since abstract classes lack them
5. **Relevance scoring**: Use `option (score ?sc)` with bif:contains and ORDER BY DESC(?sc)
6. **Relationship queries**: Use OWL restriction pattern:
   ```sparql
   ?entity rdfs:subClassOf ?restriction .
   ?restriction owl:onProperty <property_uri> ;
                owl:someValuesFrom ?value .
   ```
7. **Limit results**: Always include LIMIT to prevent timeouts with large result sets
8. **Check deprecation**: Filter out `owl:deprecated true` entities for current data
