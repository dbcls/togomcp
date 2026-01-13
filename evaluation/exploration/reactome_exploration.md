# Reactome Pathway Database Exploration Report

## Database Overview
- **Purpose**: Curated knowledgebase of biological pathways and processes
- **Scope**: 22,000+ pathways across 30+ species with molecular interactions
- **Key entities**: Pathways, Reactions, Proteins, Complexes, Small Molecules
- **Data quality**: Expert manual curation with literature evidence

## Schema Analysis (from MIE file)

### Main Properties (BioPAX Level 3)
- `bp:Pathway`: Biological pathway entity
- `bp:displayName`: Pathway/entity name
- `bp:pathwayComponent`: Sub-pathways and reactions
- `bp:BiochemicalReaction`: Chemical transformation
- `bp:left/bp:right`: Reaction substrates/products
- `bp:Protein`, `bp:Complex`, `bp:SmallMolecule`: Entity types
- `bp:entityReference`: Canonical entity definition
- `bp:xref`: Cross-references (UniProt, ChEBI, GO, etc.)

### Important Relationships
- `bp:pathwayComponent`: Pathway hierarchy (parent → children)
- `bp:Catalysis`: Enzyme-reaction relationships
- `bp:controller/bp:controlled`: Regulatory relationships
- `bp:component`: Complex composition

### Query Patterns
- Always use FROM <http://rdf.ebi.ac.uk/dataset/reactome>
- Use bif:contains for text search with option (score ?sc)
- **CRITICAL**: Use ^^xsd:string for bp:db comparisons
- Start property paths from specific URIs, not variables

## Search Queries Performed

1. **Query**: search_reactome_entity("autophagy")
   - Results: R-HSA-9612973 (Autophagy pathway - human)
   - Also found mouse (R-MMU), rat (R-RNO), dog (R-CFA), cow (R-BTA) versions
   - Related entities: ATG5, ATG7 proteins, autophagy complexes

2. **Query**: search_reactome_entity("mTOR")
   - Results: R-HSA-165159 (MTOR signalling pathway - human)
   - Proteins: MTOR (R-HSA-165662)
   - Reactions: TORC2 phosphorylates AKT at S473
   - Complexes: mTORC1, mTORC1 dimer

3. **Query**: search_reactome_entity("cancer")
   - Expected: Disease-related pathways

4. **Query**: search_reactome_entity("apoptosis")
   - Expected: Cell death pathways

5. **Query**: search_reactome_entity("SARS-CoV-2")
   - Expected: COVID-19 related pathways (good for currency questions)

## SPARQL Queries Tested

```sparql
# Query 1: Search pathways by keyword (from MIE examples)
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
    bp:displayName ?name .
  ?name bif:contains "'cancer'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
# Pattern verified - returns cancer-related pathways
```

```sparql
# Query 2: Get proteins with UniProt IDs (from MIE examples)
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?proteinName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?entity bp:entityReference ?proteinRef .
  ?proteinRef a bp:ProteinReference ;
    bp:name ?proteinName ;
    bp:xref ?xref .
  ?xref a bp:UnificationXref ;
    bp:db "UniProt"^^xsd:string ;
    bp:id ?uniprotId .
}
LIMIT 50
# Pattern verified - CRITICAL to use ^^xsd:string for bp:db
```

```sparql
# Query 3: Find pathway hierarchy (from MIE examples)
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX reactome: <http://www.reactome.org/biopax/68/49646#>

SELECT ?subPathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  reactome:Pathway227 bp:pathwayComponent ?subPathway .
  ?subPathway a bp:Pathway ;
    bp:displayName ?name .
}
LIMIT 100
# Pattern verified - retrieves sub-pathways
```

## Interesting Findings

### Specific Entities for Questions
- **R-HSA-9612973**: Autophagy pathway (human)
- **R-HSA-165159**: MTOR signalling pathway
- **R-HSA-165662**: MTOR protein
- **R-HSA-377400**: mTORC1 complex
- Various ATG proteins (ATG5, ATG7)

### Pathway Identifiers
- R-HSA-*: Human pathways
- R-MMU-*: Mouse pathways
- R-RNO-*: Rat pathways
- R-CFA-*: Dog pathways
- R-BTA-*: Cow pathways

### Unique Properties
- Hierarchical pathway organization
- Stoichiometric complex composition
- EC numbers for enzyme reactions
- Cellular location annotations
- Evidence via PubMed citations

### Database Connections
- **UniProt**: 87K protein references
- **ChEBI**: 32K small molecule references
- **GO**: 65K biological process annotations
- **PubMed**: 443K evidence citations
- **Guide to Pharmacology**: 8K drug-target interactions
- **COSMIC**: 5K cancer gene variants

### Key Statistics
- 22,071 pathways
- 88,464 reactions
- 226,021 proteins
- 101,651 complexes
- 50,136 small molecules
- 30+ species

## Question Opportunities by Category

### Precision
- What is the Reactome pathway ID for human autophagy? (R-HSA-9612973)
- What is the Reactome ID for mTOR signalling? (R-HSA-165159)
- What is the Reactome protein ID for human MTOR? (R-HSA-165662)

### Completeness
- How many pathways in Reactome are related to autophagy?
- How many human pathways are in Reactome?
- List all sub-pathways of mTOR signalling
- How many proteins are in the mTORC1 complex?

### Integration
- What UniProt IDs are in the autophagy pathway?
- What GO terms are annotated to R-HSA-9612973?
- What ChEBI compounds are substrates in the mTOR pathway?
- Link Reactome proteins to PDB structures

### Currency
- What pathways in Reactome involve SARS-CoV-2 proteins?
- What are the newest disease-related pathways?
- Latest additions to immune signalling pathways

### Specificity
- Find pathways specific to rare disease mechanisms
- What enzymes have EC number 2.7.10.1 in Reactome?
- Find pathways with documented drug interactions

### Structured Query
- Find cancer pathways with mTOR signalling components
- Find pathways with both autophagy AND apoptosis components
- Find human pathways with ChEBI compounds and UniProt proteins

## Notes
- Always use FROM <http://rdf.ebi.ac.uk/dataset/reactome>
- **CRITICAL**: Use ^^xsd:string for bp:db comparisons
- Use bif:contains with option (score ?sc) for relevance ranking
- Start property path traversals from specific URIs
- Add LIMIT to exploratory queries
- Pathway IDs include species prefix (HSA=human, MMU=mouse, etc.)
