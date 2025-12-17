# Reactome Pathway Database Exploration Report

## Database Overview
- **Purpose**: Open-source, curated knowledgebase of biological pathways and processes
- **Scope**: 22,000+ pathways across 30+ species
- **Key data types**:
  - Pathways (22,000) - hierarchical organization
  - Biochemical reactions (11,000)
  - Proteins (226,000)
  - Protein complexes (101,000)
  - Small molecules (50,000)
- **Based on**: BioPAX Level 3 ontology for pathway representation

## Schema Analysis (from MIE file)

### Main Properties
- **bp:Pathway**: Core pathway entity with hierarchical structure
- **bp:displayName**: Human-readable pathway/entity name
- **bp:pathwayComponent**: Links to sub-pathways and reactions
- **bp:organism**: Organism classification (via bp:BioSource)
- **bp:BiochemicalReaction**: Biochemical reaction entity
- **bp:left**: Substrate/reactant entities
- **bp:right**: Product entities
- **bp:eCNumber**: Enzyme Commission number classification
- **bp:Protein**: Protein entity
- **bp:Complex**: Multi-component protein complex
- **bp:component**: Components of a complex
- **bp:componentStoichiometry**: Stoichiometric ratios in complexes
- **bp:SmallMolecule**: Chemical compound entity
- **bp:entityReference**: Links to reference entities (ProteinReference, SmallMoleculeReference)
- **bp:xref**: Cross-references to external databases
- **bp:UnificationXref**: Primary external database identifier
- **bp:PublicationXref**: Literature citations
- **bp:db**: External database name (requires ^^xsd:string type)
- **bp:id**: External database ID
- **bp:comment**: Additional annotations

### Important Relationships
- **Hierarchical pathways**: bp:pathwayComponent creates parent-child relationships
- **Transitive closure**: bp:pathwayComponent* for full pathway hierarchies
- **Reaction networks**: bp:left and bp:right link reactions to entities
- **Complex assembly**: bp:component and bp:componentStoichiometry define complexes
- **External integration**: bp:xref with bp:db and bp:id link to external databases
- **Cross-references**:
  - UniProt: 87K proteins (~90% coverage)
  - ChEBI: 28K small molecules
  - PubChem: 8K compounds
  - PubMed: 268K evidence citations (~85% pathways)
  - GO: Biological process mappings
  - Guide to Pharmacology: 8K drug targets
  - KEGG, PANTHER: Pathway mappings
  - NCBI Taxonomy: Organism classification

### Query Patterns Observed
1. **Use bif:contains for pathway search**: NOT FILTER(CONTAINS(...))
2. **Add relevance scoring**: `option (score ?sc)` with ORDER BY DESC(?sc)
3. **Include FROM clause**: `FROM <http://rdf.ebi.ac.uk/dataset/reactome>`
4. **CRITICAL datatype handling**: Use `^^xsd:string` for bp:db comparisons
5. **Start from specific pathway**: For hierarchy traversal
6. **Use bp:pathwayComponent+**: For descendants (not *)
7. **Always add LIMIT**: 20-100 for exploratory queries
8. **Type filtering**: Specify bp:Pathway, bp:Protein, bp:Complex, etc.
9. **Use OPTIONAL**: For variable coverage (xref, eCNumber, comment)
10. **Boolean search**: AND, OR, NOT in bif:contains expressions

## Search Queries Performed

### Query 1: Search for mTOR signaling pathways
**Tool**: TogoMCP run_sparql with bif:contains
**Result**: Found 10 mTOR signalling pathway instances across different species:
- All named "MTOR signalling"
- Different releases/species versions (indicated by different IDs)
- Demonstrates organism-specific pathway instances

### Query 2: Search for apoptosis pathways
**Tool**: TogoMCP run_sparql with bif:contains
**Result**: Found 10 apoptosis-related pathways:
- Pathway1623: "Apoptosis" (main pathway)
- Pathway1629: "Intrinsic Pathway for Apoptosis"
- Pathway1653: "Apoptosis induced DNA fragmentation"
- Pathway1654: "Regulation of Apoptosis"
- TP53-regulated apoptosis genes pathways
- Shows hierarchical organization of cell death pathways

### Query 3: Search for glycolysis pathways
**Tool**: TogoMCP run_sparql with bif:contains
**Result**: Found 10 glycolysis pathway instances:
- Pathway1112: "Glycolysis" (main pathway)
- Multiple organism-specific versions across species
- Central metabolic pathway well-covered
- Demonstrates pathway conservation across organisms

### Query 4: Search for immune response pathways
**Tool**: TogoMCP run_sparql with bif:contains
**Query**: 'immune' AND 'response'
**Result**: Found 10 immune response pathways:
- "SUMOylation of immune response proteins" (dominant result)
- "RUNX3 Regulates Immune Response and Cell Migration"
- Multiple species-specific versions
- Shows post-translational modification of immune proteins

### Query 5: Search for DNA repair pathways
**Tool**: TogoMCP run_sparql with bif:contains
**Query**: 'DNA' AND 'repair'
**Result**: Found 10 DNA repair pathways:
- Pathway13: "DNA Repair" (main pathway)
- Pathway40: "DNA Double-Strand Break Repair"
- "TP53 Regulates Transcription of DNA Repair Genes"
- "Gap-filling DNA repair synthesis and ligation in GG-NER"
- "Recruitment and ATM-mediated phosphorylation of repair proteins"
- Shows comprehensive DNA damage response coverage

## SPARQL Queries Tested

```sparql
# Query 1: Search pathways with relevance ranking
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
    bp:displayName ?name .
  ?name bif:contains "'mTOR'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: 10 mTOR signalling pathway instances
```

```sparql
# Query 2: Find reactions by EC number (from MIE example)
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT ?reaction ?name ?ecNumber
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?reaction a bp:BiochemicalReaction ;
    bp:eCNumber ?ecNumber .
  OPTIONAL { ?reaction bp:displayName ?name }
  FILTER(CONTAINS(?ecNumber, "2.7.10.1"))
}
LIMIT 50
# Would find protein tyrosine kinase reactions (EC 2.7.10.1)
```

```sparql
# Query 3: Get proteins with UniProt IDs (from MIE, CRITICAL pattern)
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
LIMIT 100
# CRITICAL: ^^xsd:string required for bp:db comparison
```

## Interesting Findings

### Specific Entities for Questions
1. **mTOR signalling pathway**: Multiple organism-specific instances
2. **EC 2.7.10.1**: Protein tyrosine kinases
3. **Platelet homeostasis**: Example hierarchical pathway (Pathway227)
4. **PDGFRA autophosphorylation**: Example biochemical reaction
5. **Protein complexes**: With stoichiometric ratios (e.g., 2:1 ratios)

### Unique Properties
- **BioPAX Level 3 ontology**: Standard pathway representation
- **Hierarchical organization**: Pathways contain sub-pathways and reactions
- **Organism-specific instances**: Same pathway in multiple species
- **Stoichiometry tracking**: Protein complex component ratios
- **Manual curation**: All pathways evidence-based
- **Quarterly updates**: Regular release cycle
- **CRITICAL datatype requirement**: Must use ^^xsd:string for bp:db

### Connections to Other Databases
- **UniProt**: 87K protein references (~90%)
- **ChEBI**: 28K small molecules
- **PubChem**: 8K compounds
- **COMPOUND (KEGG)**: 14K metabolites
- **PubMed**: 268K citations (~85% pathways)
- **GO**: Biological process mappings
- **Guide to Pharmacology**: 8K drug-target relationships
- **KEGG Pathway**: Pathway mappings
- **PANTHER**: Protein family mappings
- **NCBI Taxonomy**: Organism classification

### Specific, Verifiable Facts
1. Reactome contains 22,000+ pathways
2. 11,000 biochemical reactions
3. 226,000 proteins
4. 101,000 protein complexes
5. 50,000 small molecules
6. 30+ species covered
7. ~90% proteins have UniProt cross-references
8. ~85% pathways have PubMed citations
9. ~60% reactions have EC numbers
10. Average 5.3 sub-pathways per pathway
11. Average 3.2 proteins per complex
12. Average 8.7 reactions per pathway

## Question Opportunities by Category

### Precision
- "What is the EC number for PDGFRA autophosphorylation?" (2.7.10.1)
- "How many mTOR signalling pathway instances exist in Reactome?" (10+)
- "What is the stoichiometric coefficient for PDGFRA in its complex?"
- "What is the UniProt ID for PDGFRA?" (P16234)

### Completeness
- "List all sub-pathways of Platelet homeostasis"
- "What are all the proteins involved in mTOR signalling?"
- "How many pathways mention 'cancer'?" (search with bif:contains)
- "List all reactions with EC number 2.7.10.1"

### Integration
- "Find the ChEBI ID for ATP in Reactome reactions" (CHEBI:15422)
- "What Guide to Pharmacology drug targets are in cancer pathways?"
- "Link Reactome pathways to GO biological processes"
- "Convert Reactome proteins to UniProt IDs"

### Currency
- "What pathways were added in the latest release?" (Release 88)
- "What are recent updates to mTOR signalling?"
- "Which pathways have the most recent PubMed citations?"

### Specificity
- "What pathways contain PDGFRA specifically?"
- "Which protein complexes have stoichiometric ratios greater than 2:1?"
- "What reactions involve both ATP and kinases?"
- "Which pathways are human-specific vs multi-species?"

### Structured Query
- "Find kinase signaling pathways but not apoptosis" (Boolean AND NOT)
- "Count reactions by EC number category"
- "Find all complexes with more than 3 components"
- "Link cancer pathways to druggable targets via Guide to Pharmacology"

## Notes

### Limitations and Challenges
1. **CRITICAL datatype issue**: Must use ^^xsd:string for bp:db comparisons
2. **Organism-specific instances**: Same pathway appears multiple times
3. **Unbounded traversal**: bp:pathwayComponent* without start causes timeout
4. **Variable coverage**: Not all entities have all properties
5. **Complex data model**: BioPAX Level 3 has deep nesting
6. **EC number coverage**: Only ~60% of reactions have EC numbers
7. **Multi-graph endpoint**: Must specify FROM clause

### Best Practices for Querying
1. **Use bif:contains for search**: NOT FILTER(CONTAINS(...))
2. **Add relevance scoring**: `option (score ?sc)` with ORDER BY DESC(?sc)
3. **CRITICAL: Type bp:db values**: Use `"UniProt"^^xsd:string` not just `"UniProt"`
4. **Alternative for bp:db**: Use `FILTER(STR(?db) = "UniProt")` if needed
5. **Include FROM clause**: `FROM <http://rdf.ebi.ac.uk/dataset/reactome>`
6. **Start from specific pathway**: For hierarchy queries
7. **Use bp:pathwayComponent+**: For descendants (more efficient than *)
8. **Always add LIMIT**: 20-100 for exploratory queries
9. **Type filtering**: Explicitly filter by bp:Pathway, bp:Protein, etc.
10. **Use OPTIONAL**: For variable properties (xref, eCNumber, comment)
11. **Boolean search syntax**: `"('kinase' AND 'signaling' AND NOT 'apoptosis')"`
12. **Use bp:UnificationXref**: For external database IDs (not PublicationXref)

### Data Quality
- **Manual curation**: All pathways manually curated with evidence
- **Computational inference**: Noted in bp:comment when applicable
- **Regular updates**: Quarterly release cycle
- **Evidence-based**: 268K PubMed citations (~85% coverage)
- **Cross-reference quality**: High coverage for major databases
- **Organism-specific**: Pathway instances per species
- **Stoichiometry**: Detailed for protein complexes
- **EC numbers**: ~60% of reactions classified
- **Update frequency**: Release 88 (quarterly updates)
