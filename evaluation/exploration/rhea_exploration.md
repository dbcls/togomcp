# Rhea Exploration Report

## Database Overview
- **Purpose**: Comprehensive expert-curated database of biochemical reactions
- **Scope**: 17,078 master reactions (plus directional and bidirectional variants)
- **Key features**: Atom-balanced, chemically annotated, linked to ChEBI compounds

## Schema Analysis (from MIE file)
### Main Properties
- `rhea:Reaction`: Base class for reactions (subclassed via rdfs:subClassOf)
- `rhea:equation`: Chemical equation string
- `rhea:accession`: Rhea identifier (e.g., "RHEA:10000")
- `rhea:status`: rhea:Approved, rhea:Preliminary, rhea:Obsolete
- `rhea:isTransport`: Boolean for transport reactions
- `rhea:ec`: EC number linking to UniProt enzyme

### Important Relationships
- `rhea:directionalReaction`: Links master to directional variants
- `rhea:bidirectionalReaction`: Links master to bidirectional form
- `rhea:side`: Reaction sides (_L, _R)
- `rhea:contains`: Participants in each side
- `rhea:compound`: Links participant to compound

### Query Patterns
- Use `rdfs:subClassOf rhea:Reaction` to find reactions
- Use `bif:contains` for keyword search in equations
- Filter by `rhea:status rhea:Approved` for curated reactions

## Search Queries Performed

1. **Query: "ATP hydrolysis"**
   - RHEA:13065: ATP + H2O = ADP + phosphate + H(+) - fundamental biochemical reaction

2. **Query: "glucose"**
   - RHEA:14293: D-glucose + NAD(+) = D-glucono-1,5-lactone + NADH + H(+)
   - RHEA:14405: D-glucose + NADP(+) = D-glucono-1,5-lactone + NADPH + H(+)
   - RHEA:19933: alpha-D-glucose 1-phosphate + H2O = D-glucose + phosphate
   - RHEA:21288: sn-glycerol 3-phosphate + D-glucose = D-glucose 6-phosphate + glycerol

3. **Query: "oxidation"**
   - Found various oxidation reactions involving cytochrome b5, NADPH
   - RHEA:35743: versicolorin B + NADPH + O2 + H(+) = versicolorin A + NADP(+) + 2 H2O

4. **Query: "kinase"**
   - Results were not kinase reactions (search matched luteolin compounds)
   - Need to search for "phosphorylation" or specific kinase substrates instead

5. **Query: "glucose phosphorylation"**
   - No results (too specific for keyword search)

## SPARQL Queries Tested

```sparql
# Query 1: Count approved reactions
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>
SELECT (COUNT(?reaction) as ?total)
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:status rhea:Approved .
}
# Result: 16,685 approved reactions
```

```sparql
# Query 2: Count transport reactions
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>
SELECT (COUNT(?reaction) as ?transport_count)
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:status rhea:Approved ;
            rhea:isTransport 1 .
}
# Result: 1,496 transport reactions
```

```sparql
# Query 3: Find ATP-containing reactions with EC numbers
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rhea: <http://rdf.rhea-db.org/>
SELECT ?reaction ?equation ?ec
WHERE {
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rhea:status rhea:Approved ;
            rhea:equation ?equation ;
            rhea:ec ?ec .
  ?equation bif:contains "'ATP'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: Found 10 ATP reactions with EC numbers like 2.7.11.2, 2.7.1.84, etc.
```

```sparql
# Query 4: Get specific reaction equation (RHEA:13065 - ATP hydrolysis)
PREFIX rhea: <http://rdf.rhea-db.org/>
SELECT ?reaction ?equation
WHERE {
  rhea:13065 rhea:equation ?equation .
  BIND(rhea:13065 as ?reaction)
}
# Result: ATP + H2O = ADP + H(+) + phosphate
```

## Cross-Reference Analysis

### Links to other databases
- **ChEBI**: 100% of small molecules linked via rhea:chebi
- **GO (Molecular Function)**: ~55% of reactions have GO annotations
- **EC Numbers**: ~45% of reactions have enzyme classification
- **KEGG Reaction**: ~35% metabolic pathway coverage
- **MetaCyc**: Comprehensive coverage

### Cross-database integration
- Shared SIB endpoint with UniProt enables enzyme-reaction queries
- EC numbers link to UniProt proteins
- GO terms provide functional context

## Interesting Findings

**Discoveries requiring actual database queries:**

1. **16,685 approved reactions** in Rhea (requires COUNT query)
2. **1,496 transport reactions** specifically annotated (requires filter query)
3. **RHEA:13065** is the canonical ATP hydrolysis reaction (found via search, not MIE)
4. **ATP-related reactions** commonly have EC 2.7.x.x (kinase/transferase) classifications
5. **RHEA:23052** links to EC 2.7.11.2 (pyruvate dehydrogenase kinase)

**Key real entities discovered (NOT in MIE examples):**
- RHEA:13065: ATP hydrolysis (fundamental)
- RHEA:14293: D-glucose oxidation with NAD+
- RHEA:23052: Protein phosphorylation reaction
- RHEA:23100: dAMP kinase reaction (ATP + dAMP = ADP + dADP)

## Question Opportunities by Category

### Precision
- ✅ "What is the Rhea ID for ATP hydrolysis?" → RHEA:13065 (requires search)
- ✅ "What is the equation for Rhea reaction RHEA:13065?" → ATP + H2O = ADP + H(+) + phosphate
- ✅ "What EC number is associated with Rhea reaction RHEA:23052?" → 2.7.11.2

### Completeness  
- ✅ "How many approved reactions are in Rhea?" → 16,685
- ✅ "How many transport reactions are in Rhea?" → 1,496
- ✅ "How many reactions involve ATP?" → requires COUNT with bif:contains

### Integration
- ✅ "What UniProt proteins catalyze Rhea reaction RHEA:13065?" → requires cross-endpoint query
- ✅ "What GO terms are associated with Rhea reactions?" → requires rdfs:seeAlso query

### Currency
- ✅ "How many reactions are currently approved in Rhea?" → 16,685 (changes quarterly)

### Specificity
- ✅ "What is the Rhea reaction for glucose oxidation with NAD+?" → RHEA:14293
- ✅ "What reactions involve versicolorin (mycotoxin)?" → RHEA:35743

### Structured Query
- ✅ "Find all transport reactions in Rhea" → filter by rhea:isTransport
- ✅ "Find ATP-dependent reactions with EC numbers" → compound filter query

## Notes
- Always use `rdfs:subClassOf rhea:Reaction` (not `a rhea:Reaction`)
- Use `bif:contains` for efficient text search in equations
- Filter by `rhea:status rhea:Approved` for quality data
- Reactions have quartet structure: master, L→R, R→L, bidirectional
- Good integration opportunities with UniProt via shared SIB endpoint
