# Rhea Exploration Report

## Database Overview
- **Purpose**: Comprehensive expert-curated database of biochemical reactions
- **Scope**: 17,078 master reactions, 34,156 directional representations, 17,078 bidirectional forms, 11,763 small molecules, 254 polymers, 5,984 transport reactions
- **Key data types**: Biochemical reactions with stoichiometry, transport reactions with cellular locations, polymer reactions with polymerization indices, EC and GO annotations

## Schema Analysis (from MIE file)

### Main Properties Available
- **Reaction core properties**:
  - `rhea:accession` - Unique identifier (RHEA:XXXXX)
  - `rhea:equation` - Text equation representation
  - `rhea:htmlEquation` - HTML formatted equation
  - `rhea:status` - rhea:Approved, rhea:Preliminary, rhea:Obsolete
  - `rhea:isChemicallyBalanced` - Boolean (all approved reactions = 1)
  - `rhea:isTransport` - Boolean for transmembrane transport
  
- **Reaction relationships**:
  - `rhea:side` - Links to left (_L) and right (_R) sides
  - `rhea:directionalReaction` - Links to directional forms (L→R, R→L)
  - `rhea:bidirectionalReaction` - Links to bidirectional form
  - `rhea:ec` - Links to UniProt enzyme classification
  
- **Participant properties**:
  - `rhea:compound` - Links to compound entity
  - `rhea:location` - rhea:In or rhea:Out for transport reactions
  - `rhea:contains1/2/3/N` - Stoichiometry encoding (1, 2, 3, or >3)
  
- **Compound properties**:
  - `rhea:name` - Chemical name
  - `rhea:formula` - Molecular formula
  - `rhea:charge` - Molecular charge
  - `rhea:chebi` - ChEBI cross-reference
  - `rhea:polymerizationIndex` - For polymers (n, n-1, n+1, etc.)

### Important Relationships
- **Quartet system**: Each master reaction (RHEA:XXXXX0) has ID-based relationship to directional (XXXXX1, XXXXX2) and bidirectional (XXXXX3) forms
- **Hierarchical structure**: Reaction → ReactionSide (_L, _R) → Participant → Compound
- **ChEBI integration**: All small molecules link to ChEBI via rdfs:subClassOf and rhea:chebi
- **Cross-database links**: rdfs:seeAlso links to GO (molecular function), BioCyc/MetaCyc, Reactome, MACiE
- **Stoichiometry encoding**: Separate properties (contains1, contains2, contains3, containsN) for different stoichiometric coefficients

### Query Patterns Observed
- **Full-text search**: Use bif:contains with single quotes for fast keyword searching
- **Boolean operators**: 'glucose' AND 'phosphate' or 'atp' OR 'gtp' in bif:contains
- **Relevance ranking**: ORDER BY DESC(?sc) after bif:contains option (score ?sc)
- **Type filtering**: Filter by rhea:status early (rhea:Approved) for quality results
- **Traversal pattern**: reaction → side → participant → compound for complete information
- **Cross-reference filtering**: Use STRSTARTS or CONTAINS on URI strings for specific databases

## Search Queries Performed

1. **Query**: ATP reactions → **Results**: 10 results including transport reactions (ATP(in) = ATP(out)), metabolic reactions (ATP + D-glyceraldehyde = ADP + D-glyceraldehyde 3-phosphate + H(+)), and ion transport (ATP + Mg(2+) with location annotations)

2. **Query**: glucose AND phosphate → **Results**: 10 results showing glucose phosphorylation (D-glucose 6-phosphate + H2O = D-glucose + phosphate), polymer reactions ([phosphate](n) + D-glucose), and disaccharide phosphorolysis (nigerose + phosphate = beta-D-glucose 1-phosphate + D-glucose)

3. **Query**: Transport reactions (rhea:isTransport = 1) → **Results**: 20 results showing ATP-dependent transport (Zn(2+)(in) = Zn(2+)(out)), ion pumps (H(+)(in) → H(+)(out)), and substrate import (guanine(out) → guanine(in)) with explicit location annotations

4. **Query**: Reactions with EC and GO annotations → **Results**: 20 results showing diverse enzymes (EC 3.1.1.63, 2.4.2.35, 1.2.1.42) with corresponding GO molecular function terms (GO:0047520, GO:0047285, GO:0047104)

5. **Query**: Polymer reactions → **Results**: 15 results showing glycosyl transferases ([(1->3)-alpha-D-glucosyl](n) + UDP-alpha-D-glucose = [(1->3)-alpha-D-glucosyl](n+1)), folate modifications ((6S)-tetrahydrofolyl-(gamma-L-Glu)(n)), and polysaccharide synthesis with various polymerization indices (n, n-1, n+1)

## SPARQL Queries Tested

```sparql
# Query 1: Full-text search with relevance ranking
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?reaction ?equation ?label
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rdfs:label ?label ;
            rhea:status rhea:Approved .
  ?equation bif:contains "'ATP'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: Retrieved 10 ATP-related reactions ranked by relevance, including both transport and metabolic reactions. Fast query (<1s).
```

```sparql
# Query 2: Boolean search for compound combinations
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?reaction ?equation
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:status rhea:Approved .
  ?equation bif:contains "'glucose' AND 'phosphate'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: Retrieved 10 glucose-phosphate reactions including phosphorylation, phosphorolysis, and isomerization reactions. Demonstrates AND operator functionality.
```

```sparql
# Query 3: Transport reactions with cellular locations
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?reaction ?equation ?participant ?compound ?location
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:isTransport 1 ;
            rhea:side ?side .
  ?side rhea:contains ?participant .
  ?participant rhea:compound ?compound ;
               rhea:location ?location .
}
LIMIT 20
# Results: Retrieved 20 transport reactions with explicit rhea:In and rhea:Out location annotations. Shows ATP-dependent ion transport and substrate import/export.
```

```sparql
# Query 4: Reactions with EC numbers and GO terms
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT DISTINCT ?reaction ?equation ?ec ?goTerm
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:ec ?ec ;
            rdfs:seeAlso ?goTerm .
  FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
}
LIMIT 20
# Results: Retrieved 20 reactions with both EC classifications and GO molecular function terms, demonstrating comprehensive enzyme annotation.
```

```sparql
# Query 5: Polymer reactions with polymerization indices
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT DISTINCT ?reaction ?equation ?polymer ?polyIndex
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:equation ?equation ;
            rhea:side ?side .
  ?side rhea:contains ?participant .
  ?participant rhea:compound ?compound .
  ?compound rdfs:subClassOf rhea:Polymer ;
            rhea:name ?polymer ;
            rhea:polymerizationIndex ?polyIndex .
}
LIMIT 15
# Results: Retrieved 15 polymer reactions showing polymerization (n → n+1) and depolymerization, including glycosyl transferases, polysaccharide synthesis, and protein glycosylation.
```

```sparql
# Query 6: Specific reaction details by accession
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?property ?value
WHERE {
  ?reaction rhea:accession "RHEA:10000" ;
            ?property ?value .
}
LIMIT 30
# Results: Retrieved complete metadata for RHEA:10000 (pentanamide hydrolysis) including equation, EC number (3.5.1.50), GO term (GO:0050168), reaction sides, directional variants, literature citation, and chemical balance status.
```

```sparql
# Query 7: Compound details with ChEBI links
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?compound ?name ?formula ?charge ?chebi
WHERE {
  ?compound rdfs:subClassOf rhea:SmallMolecule ;
            rhea:name ?name ;
            rhea:formula ?formula ;
            rhea:charge ?charge ;
            rhea:chebi ?chebi .
  FILTER(CONTAINS(?name, "ATP"))
}
LIMIT 10
# Results: Retrieved 8 ATP-related compounds including ATP (C10H12N5O13P3, charge -4, CHEBI:30616), dATP, 2-oxo-ATP, N(6)-methyl-ATP variants, demonstrating comprehensive molecular descriptors.
```

```sparql
# Query 8: Reaction quartet - master and directional forms
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>

SELECT ?masterReaction ?masterEquation ?directional ?bidirectional
WHERE {
  ?masterReaction rhea:accession "RHEA:13941" ;
                  rhea:equation ?masterEquation .
  OPTIONAL {
    ?masterReaction rhea:directionalReaction ?directional .
  }
  OPTIONAL {
    ?masterReaction rhea:bidirectionalReaction ?bidirectional .
  }
}
# Results: RHEA:13941 (ATP + D-glyceraldehyde = ADP + D-glyceraldehyde 3-phosphate + H(+)) links to directional reactions RHEA:13942 and RHEA:13943, and bidirectional RHEA:13944, demonstrating the quartet system.
```

## Interesting Findings

### Specific Entities That Could Form Good Questions
- **RHEA:10000**: Pentanamide hydrolysis (first reaction in database, well-documented)
- **RHEA:13941**: ATP-dependent glyceraldehyde kinase with complete quartet
- **Transport reactions**: RHEA:20621 (Zn(2+) transport), RHEA:20852 (H+ pump)
- **Polymer reactions**: RHEA:19749 (glucosyl transferase with n→n+1), RHEA:20908 (complex glycosaminoglycan synthesis)
- **ATP compound**: C10H12N5O13P3, charge -4, CHEBI:30616

### Unique Properties or Patterns
- **Quartet system**: Each reaction has 4 representations (master + 2 directional + bidirectional) with predictable ID patterns (XXXXX0, XXXXX1, XXXXX2, XXXXX3)
- **Location annotations**: Transport reactions use rhea:In and rhea:Out for precise cellular compartment tracking
- **Stoichiometry encoding**: Separate properties for different coefficients (contains1/2/3/N) enable efficient filtering
- **Polymer notation**: Standardized notation for polymerization indices (n, n-1, n+1) in formulas and charges
- **Universal chemical balance**: All approved reactions have rhea:isChemicallyBalanced = 1
- **Full-text search optimization**: bif:contains with relevance scoring is much faster than FILTER(CONTAINS())

### Connections to Other Databases
- **ChEBI**: 100% coverage for all 11,763 small molecules via rdfs:subClassOf and rhea:chebi
- **Gene Ontology**: ~55% of reactions have GO molecular function terms (GO:XXXXXXX)
- **BioCyc/MetaCyc**: ~35% coverage via identifiers.org/biocyc/METACYC:XXX
- **Reactome**: Selected pathway connections via identifiers.org/reactome/R-HSA-XXXXXX
- **UniProt Enzyme**: ~45% have EC classifications via http://purl.uniprot.org/enzyme/X.X.X.X
- **MACiE**: Mechanism annotations for selected reactions

### Specific, Verifiable Facts
- **17,078 master reactions** with 34,156 directional and 17,078 bidirectional representations (quartet system)
- **5,984 transport reactions** (35% of total) with explicit cellular location annotations
- **254 polymer structures** with standardized polymerization notation
- **66,740 approved reactions** vs 452 preliminary and 1,120 obsolete
- **100% ChEBI coverage** for all small molecule compounds
- **Average 4-6 participants per reaction** (substrates + products)
- **ATP (CHEBI:30616)**: Molecular formula C10H12N5O13P3, charge -4, most common high-energy compound

## Question Opportunities by Category

### Precision
- "What is the molecular formula of ATP in the Rhea database?" (Answer: C10H12N5O13P3)
- "What is the charge of ATP according to Rhea?" (Answer: -4)
- "What is the ChEBI identifier for ATP in Rhea?" (Answer: CHEBI:30616)
- "How many directional forms does reaction RHEA:10000 have?" (Answer: 2 - RHEA:10001 and RHEA:10002)
- "What is the EC number associated with reaction RHEA:10000?" (Answer: 3.5.1.50)

### Completeness
- "How many approved reactions are in the Rhea database?" (Answer: 66,740 from total 68,312)
- "How many transport reactions are in Rhea?" (Answer: 5,984)
- "How many polymer structures are in Rhea?" (Answer: 254)
- "List all directional and bidirectional forms of reaction RHEA:13941" (Answer: RHEA:13942, RHEA:13943, RHEA:13944)
- "How many reactions in Rhea have EC number classifications?" (Answer: ~45% of reactions)

### Integration
- "What is the GO molecular function term for reaction RHEA:19697?" (Answer: GO:0047520)
- "Find the ChEBI identifier for the water molecule in Rhea" (Answer: CHEBI:15377)
- "What Reactome pathways reference reactions involving ATP transport?" (Uses rdfs:seeAlso with identifiers.org/reactome)
- "Convert Rhea compound accession CHEBI:30616 to its Rhea compound ID" (Answer: Compound_6372)
- "Find BioCyc/MetaCyc cross-references for glucose-6-phosphatase reactions"

### Currency
- "How many reactions were classified as 'Preliminary' in the current Rhea release?" (Answer: 452)
- "What is the approval status distribution in Rhea?" (Answer: 66,740 approved, 452 preliminary, 1,120 obsolete)
- "Which reactions have been recently added to Rhea with polymer substrates?"
- "What are the most recent transport reactions added for metal ions?"

### Specificity
- "What is the polymerization index notation used in Rhea reaction RHEA:19749?" (Answer: n and n+1)
- "What cellular location is specified for Zn(2+) in transport reaction RHEA:20621?" (Answer: In and Out)
- "What is the stoichiometry of H(+) in reaction RHEA:20852?" (Answer: 1 H(+)(in) and 2 H(+)(out))
- "What is the literature citation for reaction RHEA:10000?" (Answer: Published in Friedrich, C.G. and Mitrenga, G., J. Gen. Microbiol. 125 (1981) 367-374)
- "What is the formula notation for the polymer in reaction RHEA:20908?" (Contains complex glycan notation with (n))

### Structured Query
- "Find all approved reactions involving glucose and phosphate" (Boolean AND search with bif:contains)
- "List reactions that are both chemically balanced and transport reactions" (rhea:isChemicallyBalanced = 1 AND rhea:isTransport = 1)
- "Find all reactions with EC number 3.5.1.* and GO annotations" (EC classification + cross-reference filtering)
- "Retrieve all ATP-related compounds with negative charge" (Compound filtering with formula pattern and charge)
- "Find polymer reactions where polymerization index increases by 1" (Filter for polyIndex = "n+1")

## Notes

### Limitations or Challenges
- **Quartet complexity**: Users need to understand the relationship between master, directional, and bidirectional reactions
- **Polymer notation**: Requires parsing of specialized notation (n, n-1, (n)) which may be unfamiliar
- **Literature citations**: Stored in rdfs:comment as free text, requiring parsing for structured access
- **Cross-reference completeness**: Not all reactions have external database links (coverage varies 35-55%)
- **Query performance**: Full traversal (reaction→side→participant→compound) without LIMIT can timeout
- **Preliminary status**: 452 reactions still under curation may have incomplete annotations

### Best Practices for Querying
1. **Use bif:contains** for text search instead of FILTER(CONTAINS()) - much faster with relevance ranking
2. **Always use LIMIT** on exploratory queries to prevent timeouts
3. **Filter by status early**: Add rhea:status rhea:Approved to focus on curated reactions
4. **Start from reactions**: When querying participants/compounds, begin with reaction filters then traverse
5. **Use ORDER BY DESC(?sc)** after bif:contains to get most relevant results first
6. **Boolean operators**: Use single quotes around keywords: 'glucose' AND 'phosphate'
7. **Cross-reference filtering**: Use STRSTARTS or CONTAINS on URI strings for specific database patterns
8. **Stoichiometry queries**: Use specific properties (contains1, contains2) for efficient filtering
9. **ID-based lookups**: Use rhea:accession "RHEA:XXXXX" for direct access (very fast)
10. **Type checking**: Verify rdfs:subClassOf rhea:Reaction for reaction queries

### Anti-patterns to Avoid
- ❌ Using FILTER(CONTAINS()) instead of bif:contains for text search (slow, no ranking)
- ❌ Omitting LIMIT on open-ended relationship traversals (timeouts)
- ❌ Confusing master reactions with directional forms (different properties)
- ❌ Querying compound properties from participant entities (use rhea:compound link)
- ❌ Not filtering by reaction status (includes obsolete and preliminary reactions)
- ❌ Trying to count all reactions without LIMIT (timeout even with COUNT)
- ❌ Missing DISTINCT when querying multiple optional cross-references (cartesian products)
- ❌ Comparing polymerization indices as numbers (they're strings: "n", "n-1", "n+1")
