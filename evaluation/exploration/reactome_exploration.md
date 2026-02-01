# Reactome Exploration Report

**Date**: 2026-01-31
**Session**: 1

## Executive Summary

Reactome is a comprehensive, curated knowledgebase of biological pathways containing 22,000+ pathways across 30+ species. The database is built on BioPAX Level 3 ontology and provides rich cross-references to UniProt, ChEBI, PubMed, GO, and drug databases.

**Key capabilities requiring deep knowledge**:
1. Cross-database integration with ChEBI and ChEMBL via shared EBI endpoint
2. CRITICAL: `^^xsd:string` type restriction for ALL bp:db comparisons (empty results without it)
3. Pathway hierarchy traversal using bp:pathwayComponent property paths
4. Text search using bif:contains (not FILTER CONTAINS)
5. Database name spelling (e.g., "Pubmed" not "PubMed", "UniProt" with capital P)

**Major integration opportunities**:
- Reactome → ChEBI (small molecule enrichment)
- Reactome → ChEMBL (drug target identification)
- Reactome → UniProt → ChEMBL (pathway-based drug discovery)
- Reactome → GO (functional annotation)

**Most valuable patterns discovered**:
- Cross-database queries require explicit GRAPH clauses and URI conversion
- Pre-filtering on pathway names essential for performance
- Organism filtering requires CONTAINS, not direct equality
- Entity relationships traverse through bp:entityReference

**Recommended question types**:
- Multi-database pathway-drug integration
- Performance-critical pathway counting
- Error-avoidance type restriction queries
- Complex filtering with organism/pathway combinations

## Database Overview

- **Purpose**: Curated biological pathway database
- **Scope**: 22,000+ pathways, 88,000+ reactions, 226,000+ proteins, 50,000+ small molecules
- **Species**: 30+ organisms (Homo sapiens has 2,825 pathways)
- **Update frequency**: Quarterly releases
- **Endpoint**: https://rdfportal.org/ebi/sparql (shared with ChEMBL, ChEBI, Ensembl, AMRPortal)
- **Graph URI**: http://rdf.ebi.ac.uk/dataset/reactome

## Structure Analysis

### Performance Strategies

**Strategy 1: Use bif:contains for text search**
- FILTER with CONTAINS or REGEX is slow (10-100x slower)
- bif:contains uses Virtuoso's full-text index
- Supports relevance scoring and boolean operators
- Example: `?name bif:contains "'autophagy'" option (score ?sc)`

**Strategy 2: Use explicit GRAPH clauses**
- Essential for cross-database queries on shared endpoint
- Prevents cross-contamination between co-located databases
- Performance: 2-5x faster than without GRAPH

**Strategy 3: Start property paths from specific entities**
- Unbounded `bp:pathwayComponent*` causes timeout
- Always start from specific pathway URI or add LIMIT
- Use `+` instead of `*` when depth > 0 is required

**Strategy 4: Use ^^xsd:string type restriction**
- **CRITICAL**: ALL bp:db comparisons require `"value"^^xsd:string`
- Without it: empty results (not errors!)
- Example: `bp:db "UniProt"^^xsd:string` not `bp:db "UniProt"`

**Strategy 5: Pre-filter before cross-database joins**
- Filter pathways/proteins in Reactome before joining to ChEMBL/ChEBI
- Reduces intermediate result set by 99%
- Example: Filter by pathway name before traversing to proteins

**Strategy 6: Use OPTIONAL correctly**
- Place OPTIONAL after required patterns
- Use for properties that may not exist (e.g., cellular location)

**Strategy 7: URI conversion for cross-database joins**
- Convert string IDs to URIs using BIND(IRI(CONCAT(...)))
- Example: `BIND(IRI(CONCAT("http://purl.obolibrary.org/obo/CHEBI_", ?chebiNum)) AS ?chebiUri)`

### Common Pitfalls

**Pitfall 1: Missing ^^xsd:string type restriction**
- **CRITICAL ERROR**: Returns empty results without warning
- Affects all bp:db comparisons
- Cause: RDF literal datatype mismatches
- Solution: Always use `"UniProt"^^xsd:string` not `"UniProt"`

**Pitfall 2: Database name capitalization**
- "Pubmed" not "PubMed" for publication xrefs
- "UniProt" not "Uniprot" for protein xrefs
- "ChEBI" not "CHEBI" for chemical xrefs
- "GENE ONTOLOGY" not "Gene Ontology" for GO xrefs

**Pitfall 3: Organism filtering with equality**
- Direct equality `FILTER(?species = "Homo sapiens")` often fails
- Use `FILTER(CONTAINS(?species, "sapiens"))` instead
- Or match within the pattern using bp:name

**Pitfall 4: bif:contains incompatibility with FILTER**
- bif:contains must be used as a triple pattern
- Cannot combine with `bif:contains` and `FILTER(CONTAINS())` on same variable

**Pitfall 5: Property paths without type constraints**
- `bp:pathwayComponent*/bp:left|bp:right` can explode
- Add type filters: `?entity a bp:Protein`
- Add LIMIT during development

### Data Organization

**Pathway (bp:Pathway)**
- Core entity containing hierarchical pathway structure
- Properties: displayName, organism, pathwayComponent, xref
- Hierarchy: pathways contain sub-pathways and reactions

**BiochemicalReaction (bp:BiochemicalReaction)**
- Reactions with substrates (left) and products (right)
- Properties: displayName, eCNumber, spontaneous
- Links to Catalysis for enzyme relationships

**PhysicalEntity (bp:Protein, bp:Complex, bp:SmallMolecule)**
- Participants in reactions
- Linked via bp:entityReference to canonical definitions
- Include cellular location annotations

**EntityReference (bp:ProteinReference, bp:SmallMoleculeReference)**
- Canonical definitions with cross-references
- Link to external databases via bp:xref

**Xref Types**
- bp:UnificationXref: External database IDs (UniProt, ChEBI)
- bp:PublicationXref: PubMed citations
- bp:RelationshipXref: Related annotations (GO, COSMIC)

### Cross-Database Integration Points

**Integration 1: Reactome → ChEBI (Small Molecule Enrichment)**
- Connection: UnificationXref with bp:db "ChEBI"^^xsd:string
- ID format: "CHEBI:15422" → convert to URI
- URI conversion: `http://purl.obolibrary.org/obo/CHEBI_15422`
- Information: Chemical ontology, formula, mass, InChI

**Integration 2: Reactome → ChEMBL (Drug Targets)**
- Connection: Via UniProt IDs as common identifier
- Path: Reactome protein → UniProt ID → ChEMBL target
- Information: Drug molecules, development phase, bioactivity
- Pre-filtering: Essential for performance

**Integration 3: Reactome → GO (Functional Annotation)**
- Connection: RelationshipXref with bp:db "GENE ONTOLOGY"^^xsd:string
- ID format: "GO:0006914"
- Use case: Map pathways to biological processes

**Integration 4: Reactome → PubMed (Literature)**
- Connection: PublicationXref with bp:db "Pubmed"^^xsd:string (note lowercase "med")
- Contains 290K+ PubMed citations

**Integration 5: Reactome → Guide to Pharmacology**
- Connection: UnificationXref with bp:db "Guide to Pharmacology"^^xsd:string
- Contains 8,400+ drug-target interactions
- Directly annotated on protein references

## Complex Query Patterns Tested

### Pattern 1: Type Restriction Error Pattern (CRITICAL)

**Purpose**: Demonstrate the critical importance of ^^xsd:string type restriction

**Category**: Error Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
SELECT ?entity ?id 
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?entity bp:xref ?xref .
  ?xref bp:db "UniProt" ;  # Missing ^^xsd:string!
    bp:id ?id .
}
LIMIT 10
```

**What Happened**:
- Error message: None
- Result: Empty results (0 rows)
- Why it failed: RDF literal datatype mismatch - "UniProt" doesn't equal "UniProt"^^xsd:string

**Correct Approach**:
```sparql
SELECT ?entity ?id 
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?entity bp:xref ?xref .
  ?xref bp:db "UniProt"^^xsd:string ;  # Type restriction added
    bp:id ?id .
}
LIMIT 10
```

**Results Obtained**:
- Number of results: 10 (with LIMIT)
- Sample results: A0A8I3PRX2, A0A8I3Q4Y8, etc.

**Natural Language Question Opportunities**:
1. "What UniProt proteins are referenced in Reactome's autophagy pathway?" - Category: Structured Query
2. "Which human proteins are annotated in the EGFR signaling pathway?" - Category: Precision

---

### Pattern 2: Cross-Database Reactome → ChEBI Integration

**Purpose**: Enrich pathway metabolites with chemical structure data

**Category**: Cross-Database Integration

**Naive Approach**: Try to use string matching without URI conversion

**What Happened**: Empty results due to ID format mismatch

**Correct Approach**:
```sparql
SELECT DISTINCT ?reactomeName ?chebiLabel ?formula
WHERE {
  GRAPH <http://rdf.ebi.ac.uk/dataset/reactome> {
    ?molecule a bp:SmallMolecule ;
              bp:displayName ?reactomeName ;
              bp:entityReference/bp:xref ?xref .
    ?xref a bp:UnificationXref ;
          bp:db "ChEBI"^^xsd:string ;
          bp:id ?fullChebiId .
    FILTER(STRSTARTS(?fullChebiId, "CHEBI:"))
    FILTER(CONTAINS(?reactomeName, "ATP"))
  }
  BIND(IRI(CONCAT("http://purl.obolibrary.org/obo/CHEBI_", SUBSTR(?fullChebiId, 7))) AS ?chebiUri)
  GRAPH <http://rdf.ebi.ac.uk/dataset/chebi> {
    ?chebiUri a owl:Class ;
              rdfs:label ?chebiLabel .
    OPTIONAL { ?chebiUri chebi:formula ?formula }
  }
}
```

**What Knowledge Made This Work**:
- GRAPH clauses from both MIE files
- URI conversion pattern: CHEBI:15422 → CHEBI_15422 → full URI
- ^^xsd:string type restriction
- OPTIONAL for formula (may not exist)

**Results Obtained**:
- ATP, dATP, methylated variants
- Formula: C10H12N5O13P3

**Natural Language Question Opportunities**:
1. "What is the molecular formula of ATP according to ChEBI?" - Category: Precision
2. "Find the chemical compounds involved in human autophagy pathways" - Category: Integration

---

### Pattern 3: Cross-Database Reactome → ChEMBL Drug Target Integration

**Purpose**: Find FDA-approved drugs targeting proteins in specific pathways

**Category**: Cross-Database Integration

**Correct Approach**:
```sparql
SELECT DISTINCT ?drugName ?phase
WHERE {
  GRAPH <http://rdf.ebi.ac.uk/dataset/chembl> {
    ?target a cco:SingleProtein ;
            cco:hasTargetComponent/skos:exactMatch <http://purl.uniprot.org/uniprot/P00533> ;
            cco:hasAssay/cco:hasActivity/cco:hasMolecule ?molecule .
    ?molecule a cco:SmallMolecule ;
              rdfs:label ?drugName ;
              cco:highestDevelopmentPhase ?phase .
    FILTER(?phase >= 4)
  }
}
```

**What Knowledge Made This Work**:
- ChEMBL entity types (cco:SingleProtein, cco:SmallMolecule)
- Property path pattern from ChEMBL MIE
- Development phase filter (phase 4 = marketed drugs)
- UniProt URI format

**Results Obtained**:
- GEFITINIB, ERLOTINIB, LAPATINIB, AFATINIB (all phase 4)
- These are known EGFR inhibitors

**Natural Language Question Opportunities**:
1. "What FDA-approved drugs target the EGFR protein?" - Category: Integration
2. "Which marketed drugs target proteins in the EGFR signaling pathway?" - Category: Structured Query

---

### Pattern 4: Pathway Hierarchy Navigation

**Purpose**: Traverse pathway hierarchies to find sub-pathways

**Category**: Structured Query

**Naive Approach (timeout risk)**:
```sparql
SELECT ?pathway ?subPathway 
WHERE {
  ?pathway bp:pathwayComponent* ?subPathway  # Unbounded!
}
```

**Correct Approach**:
```sparql
SELECT ?parentName ?childName
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?parent a bp:Pathway ;
    bp:displayName ?parentName ;
    bp:pathwayComponent ?child .
  ?child a bp:Pathway ;
    bp:displayName ?childName .
  ?parentName bif:contains "'Autophagy'" .
}
LIMIT 30
```

**Results Obtained**:
- Autophagy → Macroautophagy
- Selective autophagy → Mitophagy, Aggrephagy, Pexophagy

**Natural Language Question Opportunities**:
1. "What are the sub-pathways of Autophagy?" - Category: Completeness
2. "Which specific autophagy types are curated in Reactome?" - Category: Specificity

---

### Pattern 5: Protein-Pathway Relationships with External IDs

**Purpose**: Find proteins participating in pathways with their UniProt IDs

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT DISTINCT ?pathwayName ?proteinName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
    bp:displayName ?pathwayName ;
    bp:pathwayComponent ?reaction .
  {
    ?reaction bp:left ?entity .
  } UNION {
    ?reaction bp:right ?entity .
  }
  ?entity bp:entityReference ?protRef .
  ?protRef a bp:ProteinReference ;
    bp:name ?proteinName ;
    bp:xref ?xref .
  ?xref a bp:UnificationXref ;
    bp:db "UniProt"^^xsd:string ;
    bp:id ?uniprotId .
  FILTER(CONTAINS(?pathwayName, "Signaling by EGFR"))
}
```

**What Knowledge Made This Work**:
- Entity reference pattern (bp:entityReference)
- UNION for both substrates and products
- ^^xsd:string type restriction

**Results Obtained**:
- EGFR (P00533), PLCG1 (P19174), CBL (P22681), EGF (P01133)

**Natural Language Question Opportunities**:
1. "What proteins participate in EGFR signaling?" - Category: Completeness
2. "Find the UniProt IDs of proteins in the autophagy pathway" - Category: Precision

---

### Pattern 6: Reactions with EC Numbers and Catalysis

**Purpose**: Find enzymatic reactions with their EC classifications

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?reactionName ?catalystName ?uniprotId ?ecNumber
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?catalysis a bp:Catalysis ;
    bp:controller ?catalyst ;
    bp:controlled ?reaction .
  ?reaction a bp:BiochemicalReaction ;
    bp:displayName ?reactionName ;
    bp:eCNumber ?ecNumber .
  ?catalyst bp:entityReference ?ref .
  ?ref a bp:ProteinReference ;
    bp:name ?catalystName ;
    bp:xref ?xref .
  ?xref a bp:UnificationXref ;
    bp:db "UniProt"^^xsd:string ;
    bp:id ?uniprotId .
  FILTER(CONTAINS(?reactionName, "phosphorylat"))
}
```

**Results Obtained**:
- CK1 phosphorylates p-GLI3 (EC 2.7.11.1)
- GSK3 phosphorylates p-GLI3
- Autophosphorylation of SRC

**Natural Language Question Opportunities**:
1. "What kinases catalyze phosphorylation reactions in Reactome?" - Category: Structured Query
2. "Find all reactions with EC number 2.7.11.1" - Category: Specificity

---

### Pattern 7: Protein Complexes with Stoichiometry

**Purpose**: Find multi-subunit complexes with component ratios

**Category**: Structured Query

**Correct Approach**:
```sparql
SELECT ?complexName ?componentName ?coefficient ?location
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?complex a bp:Complex ;
    bp:displayName ?complexName ;
    bp:componentStoichiometry ?stoich .
  OPTIONAL { 
    ?complex bp:cellularLocation ?cellLoc .
    ?cellLoc bp:term ?location .
  }
  ?stoich bp:physicalEntity ?component ;
    bp:stoichiometricCoefficient ?coefficient .
  ?component bp:entityReference/bp:name ?componentName .
  FILTER(?coefficient > 1)
  FILTER(CONTAINS(?complexName, "PDGF"))
}
```

**Results Obtained**:
- PDGF-AA dimer (coefficient 2, extracellular region)
- PDGF-BB dimer (coefficient 2, plasma membrane)

**Natural Language Question Opportunities**:
1. "What are the dimeric complexes in PDGF signaling?" - Category: Specificity
2. "Which protein complexes have stoichiometry greater than 1?" - Category: Completeness

---

### Pattern 8: GO Term Annotations on Pathways

**Purpose**: Map pathways to Gene Ontology biological processes

**Category**: Integration

**Correct Approach**:
```sparql
SELECT ?pathwayName ?goTerm
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
    bp:displayName ?pathwayName ;
    bp:xref ?xref .
  ?xref bp:db "GENE ONTOLOGY"^^xsd:string ;
    bp:id ?goTerm .
  FILTER(CONTAINS(?pathwayName, "Autophagy"))
}
```

**Results Obtained**:
- Autophagy → GO:0006914
- Chaperone Mediated Autophagy → GO:0061684

**Natural Language Question Opportunities**:
1. "What GO term is associated with the Autophagy pathway?" - Category: Integration
2. "Which pathways are annotated with GO:0006914?" - Category: Structured Query

---

### Pattern 9: Database Name Capitalization Error

**Purpose**: Demonstrate importance of correct database name spelling

**Category**: Error Avoidance

**Naive Approach**:
```sparql
# Using "PubMed" instead of "Pubmed"
?xref a bp:PublicationXref ;
    bp:db "PubMed"^^xsd:string .  # WRONG!
```

**Correct Approach**:
```sparql
?xref a bp:PublicationXref ;
    bp:db "Pubmed"^^xsd:string .  # Correct spelling
```

**What Knowledge Made This Work**:
- Database name verification shows "Pubmed" (289,921 entries) not "PubMed"

**Natural Language Question Opportunities**:
1. "How many PubMed citations are in Reactome?" - Category: Completeness
2. "What literature evidence supports the autophagy pathway?" - Category: Currency

---

### Pattern 10: Species-Specific Pathway Queries

**Purpose**: Filter pathways by organism

**Category**: Structured Query

**Naive Approach (often fails)**:
```sparql
FILTER(?speciesName = "Homo sapiens")  # Direct equality sometimes fails
```

**Correct Approach**:
```sparql
?pathway bp:organism ?org .
?org bp:name ?speciesName .
FILTER(CONTAINS(?speciesName, "sapiens"))
```

**Results Obtained**:
- Homo sapiens: 2,825 pathways
- Mus musculus: 1,824 pathways

**Natural Language Question Opportunities**:
1. "How many human pathways are in Reactome?" - Category: Completeness
2. "What signaling pathways are annotated for Homo sapiens?" - Category: Structured Query

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "autophagy"
   - Found: R-HSA-9612973 - Autophagy (Human pathway)
   - Usage: Pathway-based questions, sub-pathway queries

2. Search: "cancer signaling"
   - Found: R-HSA-1643713 - Signaling by EGFR in Cancer
   - Found: R-HSA-2219528 - PI3K/AKT Signaling in Cancer
   - Usage: Disease-related pathway questions

3. Search: "EGFR"
   - Found: R-HSA-177929 - Signaling by EGFR
   - Found: P00533 - EGFR protein (UniProt ID)
   - Usage: Protein-pathway integration questions

4. Cross-reference search: UniProt
   - Found: 89,342 UniProt references
   - Usage: Protein identification questions

5. Cross-reference search: ChEBI
   - Found: 21,592 ChEBI references
   - Usage: Small molecule identification questions

6. Cross-reference search: Guide to Pharmacology
   - Found: 8,405 drug-target references
   - Usage: Drug discovery questions

7. Search: COSMIC cancer variants
   - Found: COSV50629675, COSM34117
   - Usage: Variant-pathway association questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which FDA-approved drugs target proteins in the EGFR signaling pathway?"
   - Databases involved: Reactome, ChEMBL
   - Knowledge Required: UniProt ID bridging, development phase filtering, ^^xsd:string type restriction
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 3

2. "What is the molecular formula of ATP according to its ChEBI annotation in Reactome?"
   - Databases involved: Reactome, ChEBI
   - Knowledge Required: URI conversion, GRAPH clauses, ^^xsd:string
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

3. "Find marketed drugs targeting proteins in human autophagy pathways"
   - Databases involved: Reactome, UniProt, ChEMBL
   - Knowledge Required: Pathway-protein traversal, cross-database joins
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Patterns 3, 5

4. "Which chemical compounds participate in human cancer signaling pathways and what are their structures?"
   - Databases involved: Reactome, ChEBI
   - Knowledge Required: Pathway filtering, ChEBI integration, URI conversion
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

**Performance-Critical Questions**:

5. "How many human pathways contain EGFR protein?"
   - Database: Reactome
   - Knowledge Required: Organism filtering with CONTAINS, ^^xsd:string
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 10

6. "Count the number of reactions in each major signaling pathway"
   - Database: Reactome
   - Knowledge Required: bif:contains for pathway search, GROUP BY optimization
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

7. "How many proteins participate in the Autophagy pathway and its sub-pathways?"
   - Database: Reactome
   - Knowledge Required: Property path traversal with LIMIT, ^^xsd:string
   - Category: Completeness
   - Difficulty: Hard
   - Pattern Reference: Patterns 4, 5

**Error-Avoidance Questions**:

8. "Find all proteins with UniProt cross-references in Reactome"
   - Database: Reactome
   - Knowledge Required: ^^xsd:string type restriction (CRITICAL)
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

9. "How many PubMed citations support the Autophagy pathway?"
   - Database: Reactome
   - Knowledge Required: "Pubmed" not "PubMed" capitalization
   - Category: Currency
   - Difficulty: Medium
   - Pattern Reference: Pattern 9

10. "List all GO terms associated with cancer-related pathways"
    - Database: Reactome
    - Knowledge Required: "GENE ONTOLOGY"^^xsd:string not "Gene Ontology"
    - Category: Integration
    - Difficulty: Medium
    - Pattern Reference: Pattern 8

**Complex Filtering Questions**:

11. "What kinases catalyze phosphorylation reactions in EGFR signaling?"
    - Database: Reactome
    - Knowledge Required: Catalysis pattern, EC number filtering, pathway filtering
    - Category: Structured Query
    - Difficulty: Hard
    - Pattern Reference: Pattern 6

12. "Find protein complexes with more than one copy of the same subunit"
    - Database: Reactome
    - Knowledge Required: Stoichiometry pattern, coefficient filtering
    - Category: Specificity
    - Difficulty: Medium
    - Pattern Reference: Pattern 7

13. "Which cancer pathway proteins have COSMIC variant annotations?"
    - Database: Reactome
    - Knowledge Required: COSMIC cross-reference, ^^xsd:string
    - Category: Specificity
    - Difficulty: Hard
    - Pattern Reference: Pattern 1

14. "Find all enzymatic reactions with EC 2.7.11.1 in human pathways"
    - Database: Reactome
    - Knowledge Required: Organism filtering, EC number matching
    - Category: Structured Query
    - Difficulty: Medium
    - Pattern Reference: Pattern 6

15. "What are the sub-pathways of Autophagy and their GO annotations?"
    - Database: Reactome
    - Knowledge Required: Pathway hierarchy + GO xref combination
    - Category: Completeness
    - Difficulty: Hard
    - Pattern Reference: Patterns 4, 8

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the Reactome pathway ID for human Autophagy?"
   - Method: search_reactome_entity('autophagy')
   - Knowledge Required: None (simple search)
   - Category: Precision
   - Difficulty: Easy

2. "Find the pathway for EGFR signaling in cancer"
   - Method: search_reactome_entity('EGFR cancer')
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

3. "What pathways involve BRCA1?"
   - Method: search_reactome_entity('BRCA1')
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

4. "Find pathways related to apoptosis"
   - Method: search_reactome_entity('apoptosis')
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

5. "What is the UniProt ID for EGFR?"
   - Method: search_uniprot_entity or direct lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source**:
- → ChEBI: via SmallMolecule references (bp:db "ChEBI"^^xsd:string)
- → UniProt: via ProteinReference (bp:db "UniProt"^^xsd:string)
- → GO: via pathway xrefs (bp:db "GENE ONTOLOGY"^^xsd:string)
- → PubMed: via PublicationXref (bp:db "Pubmed"^^xsd:string)
- → COSMIC: via RelationshipXref (bp:db "COSMIC"^^xsd:string)
- → Guide to Pharmacology: via xref (bp:db "Guide to Pharmacology"^^xsd:string)

**This Database as Target**:
- UniProt →: Proteins can be mapped to pathway participation
- ChEBI →: Compounds can be mapped to metabolic reactions
- GO →: Biological processes can be mapped to pathways

**Complex Multi-Database Paths**:
- Reactome → UniProt → ChEMBL: Pathway-based drug target identification
- Reactome → ChEBI → PubChem: Pathway metabolite structure enrichment
- Reactome → GO → UniProt: Functional annotation bridging

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **^^xsd:string type restriction** - CRITICAL, causes silent empty results
2. **Database name spelling** - "Pubmed" not "PubMed", case-sensitive
3. **URI conversion patterns** - Essential for cross-database queries
4. **Pre-filtering strategies** - Performance-critical for large result sets
5. **Organism filtering** - CONTAINS works better than direct equality

### Common Pitfalls Discovered
1. Missing ^^xsd:string returns empty results with no error
2. Property paths without LIMIT can timeout
3. bif:contains syntax incompatible with FILTER CONTAINS
4. Organism names require CONTAINS for reliable matching
5. Cross-database queries need explicit GRAPH clauses

### Recommendations for Question Design
1. Focus on cross-database questions that demonstrate integration knowledge
2. Include questions where ^^xsd:string is essential (high failure rate without it)
3. Test pathway hierarchy traversal (property path optimization)
4. Include species-specific filtering questions
5. Test PubMed citation queries (capitalization pitfall)

### Performance Notes
- Simple pathway searches: <1 second
- Pathway hierarchy traversal: 2-5 seconds
- Cross-database Reactome→ChEBI: 3-5 seconds
- Cross-database Reactome→ChEMBL: 4-6 seconds
- Three-way integration: 3-5 seconds with aggressive pre-filtering
- Unbounded property paths: May timeout without LIMIT

---

## Notes and Observations

- EBI endpoint (hosting Reactome, ChEMBL, ChEBI, Ensembl) occasionally has 502 errors
- Reactome uses BioPAX Level 3 ontology throughout
- Entity relationships always go through bp:entityReference
- Stoichiometry information available for protein complexes
- Cellular location annotations sparse (~40% coverage)
- Evidence tracking via bp:Evidence and PublicationXref
- COSMIC variant annotations link pathways to cancer mutations
- Guide to Pharmacology provides drug target context directly

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database integration, ^^xsd:string error-avoidance, pathway hierarchy
- Avoid: Very broad counting queries without filters (timeout risk)
- Focus areas: Drug target discovery, pathway-protein relationships, cancer pathways

**Further Exploration Needed** (if any):
- Disease pathway annotations (DOID cross-references)
- Ensembl gene mappings
- ComplexPortal integration

---

**Session Complete - Ready for Next Database**
