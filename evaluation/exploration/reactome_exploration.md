# Reactome Pathway Database Exploration Report

## Database Overview
- **Purpose**: Open-source, curated knowledgebase of biological pathways and molecular interactions
- **Endpoint**: https://rdfportal.org/ebi/sparql
- **Key Features**: BioPAX Level 3 ontology, hierarchical pathways, multi-species coverage
- **Data Version**: Release 88 (quarterly updates)

## Schema Analysis (from MIE file)
### Main Entities
- **bp:Pathway**: Biological pathways (23,145 total)
- **bp:BiochemicalReaction**: Individual reactions (92,977 total)
- **bp:Protein**: Protein entities (233,200)
- **bp:Complex**: Protein complexes (109,261)
- **bp:SmallMolecule**: Chemical compounds (51,214)
- **bp:Catalysis**: Enzyme catalysis relationships (46,901)

### Important Properties
- `bp:displayName`: Human-readable name
- `bp:organism/bp:name`: Species name (via BioSource)
- `bp:pathwayComponent`: Sub-pathway hierarchy
- `bp:left/bp:right`: Reaction participants
- `bp:entityReference`: Links to canonical protein/molecule definitions
- `bp:xref`: Cross-references (UniProt, ChEBI, GO, PubMed)
- `bp:eCNumber`: Enzyme classification numbers

### Query Patterns
- **CRITICAL**: Always use `FROM <http://rdf.ebi.ac.uk/dataset/reactome>` clause
- **CRITICAL**: Use `^^xsd:string` for bp:db comparisons (e.g., `"UniProt"^^xsd:string`)
- Use `bif:contains` for keyword search with relevance scoring
- Property paths like `bp:pathwayComponent+` work but require LIMIT

## Search Queries Performed

1. **Query: "apoptosis"** → Results: 70+ entries
   - R-HSA-109581: Apoptosis (human)
   - Species variants for mouse, rat, pig, cow, etc.
   - Related reactions: intrinsic/extrinsic apoptosis pathways

2. **Query: "EGFR signaling"** → Results: 80+ entries
   - R-HSA-177929: Signaling by EGFR (human)
   - EGFR protein: P00533 (UniProt)
   - Drugs found: Gefitinib, Erlotinib, Lapatinib, Afatinib, Neratinib

3. **Query: "cancer"** → Results: 15+ cancer-specific pathways
   - Signaling by EGFR in Cancer
   - PI3K/AKT Signaling in Cancer
   - Signaling by NOTCH1 in Cancer
   - Signaling by WNT in cancer

4. **Query: "SARS-CoV"/"COVID"** → Results: 20 pathways
   - SARS-CoV-2 infection pathways
   - Host-virus interactions
   - Immune response modulation

5. **Query: Organism distribution** → 15+ species
   - Human: 2,825 pathways
   - Mouse: 1,824 pathways
   - Rat: 1,807 pathways
   - Multiple vertebrate and model organisms

## SPARQL Queries Tested

```sparql
# Query 1: Count pathways by organism
SELECT ?orgName (COUNT(DISTINCT ?pathway) as ?count)
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:organism ?org .
  ?org bp:name ?orgName .
}
GROUP BY ?orgName
ORDER BY DESC(?count)
# Results: Homo sapiens: 2,825; Mus musculus: 1,824; Rattus norvegicus: 1,807
```

```sparql
# Query 2: Find proteins in EGFR signaling pathway with UniProt IDs
SELECT DISTINCT ?proteinName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  <http://www.reactome.org/biopax/40/48887#Pathway1320> bp:pathwayComponent ?component .
  ?component bp:left ?entity .
  ?entity bp:entityReference ?proteinRef .
  ?proteinRef a bp:ProteinReference ;
              bp:name ?proteinName ;
              bp:xref ?xref .
  ?xref a bp:UnificationXref ;
        bp:db "UniProt"^^xsd:string ;
        bp:id ?uniprotId .
}
# Results: EGFR (P00533), EGF (P01133), AAMP (Q13685)
```

```sparql
# Query 3: Cancer-related pathways with relevance scoring
SELECT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:displayName ?name .
  ?name bif:contains "'cancer'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 15
# Results: EGFR in Cancer, ERBB2 in Cancer, PI3K/AKT in Cancer, NOTCH1 in Cancer, etc.
```

## Cross-Reference Analysis

### UniProt Protein References
- **Total UniProt xrefs**: 89,342 cross-references
- Enables protein-pathway integration

### ChEBI Small Molecule References
- **Total ChEBI xrefs**: 21,592 cross-references
- Links metabolites to chemical ontology

### Gene Ontology Annotations
- **Pathways with GO annotations**: 13,720 pathways (~59%)
- Maps pathways to biological processes

### PubMed Literature Citations
- **Total publication xrefs**: 291,551 references
- Evidence and provenance tracking

### Drug Database Links
- **Guide to Pharmacology**: 8,405 drug-target interactions
- Enables drug discovery research

## Interesting Findings

**Non-trivial discoveries from actual queries:**

1. **Multi-species coverage**: 15+ species with pathway data. Human has most (2,825), but significant coverage for model organisms (mouse, rat, zebrafish, C. elegans, yeast).

2. **SARS-CoV-2 pathways**: 20+ pathways dedicated to COVID-19 biology, including:
   - Early/Late infection events
   - Viral replication mechanisms
   - Host immune modulation
   - Cell-cell junction targeting

3. **Cancer signaling pathways**: Comprehensive cancer biology with pathway-specific drug targets:
   - EGFR signaling in cancer (P00533)
   - PI3K/AKT signaling in cancer
   - WNT signaling in cancer

4. **Enzyme reactions**: 36,075 reactions have EC numbers (39% of total), enabling enzyme function queries.

5. **EGFR pathway proteins**: Found EGFR (P00533), EGF (P01133) with pathway component queries. Multiple EGFR drugs catalogued: Gefitinib, Erlotinib, Lapatinib, Afatinib.

6. **URI patterns**: Different releases use different URI patterns:
   - `/biopax/40/48887#` (Release 40)
   - `/biopax/68/49646#` (Release 68)
   - This affects query reproducibility

## Question Opportunities by Category

### Precision Questions
- "What is the UniProt ID for EGFR in Reactome?" → P00533
- "How many SARS-CoV-2 pathways are in Reactome?" → 20
- "What is the EC number for a specific reaction?"

### Completeness Questions
- "How many human pathways are in Reactome?" → 2,825
- "How many reactions have EC numbers?" → 36,075
- "How many pathways have GO annotations?" → 13,720
- "How many UniProt cross-references exist?" → 89,342

### Integration Questions
- "Find UniProt IDs for proteins in the apoptosis pathway"
- "What ChEBI compounds are in glycolysis pathway?"
- "Link cancer pathway proteins to ChEMBL drug targets" (cross-database)
- Via EBI endpoint: integrate with ChEMBL, ChEBI, Ensembl

### Currency Questions
- "What COVID-19/SARS-CoV-2 pathways exist?"
- "What pathways involve EGFR inhibitor resistance?"

### Specificity Questions
- "Find pathways specific to Plasmodium falciparum" (655 pathways)
- "What pathways involve WNT signaling in cancer?"

### Structured Query Questions
- "Count pathways by organism"
- "Find reactions with EC number 2.7.x.x (kinases)"
- "Get all proteins in a pathway with their cellular locations"

## Notes
- Shares EBI endpoint with ChEMBL, ChEBI, Ensembl
- BioPAX ontology enables standardized pathway queries
- Multiple URI patterns across releases may complicate queries
- `^^xsd:string` type restriction is CRITICAL for bp:db comparisons
- Property paths (bp:pathwayComponent*) require LIMIT to avoid timeout
- bif:contains provides efficient full-text search with relevance scoring
- Human pathways are primary, with computational inference to other species
