# GlyCosmos Exploration Report

**Date**: 2026-01-31
**Session**: 1

## Executive Summary

GlyCosmos is a comprehensive glycoscience portal integrating glycan structures (GlyTouCan), glycoproteins, glycosylation sites, glycogenes, glycoepitopes, and lectin-glycan interactions across 100+ named graphs. The database is well-suited for glycobiology research including biomarker discovery, disease associations, and protein glycosylation analysis.

### Key Capabilities Requiring Deep Knowledge
- Multi-graph architecture requires FROM clause specification for performance
- Understanding graph structure critical for cross-domain queries
- bif:contains full-text search only works on rdfs:label/skos:altLabel
- Human/organism filtering essential for performance on large datasets (414K+ glycosylation sites)
- Cross-references to UniProt, NCBI Gene, ChEBI, PubChem, PDB, KEGG, Reactome

### Major Integration Opportunities
- Glycoproteins ↔ UniProt (via rdfs:seeAlso)
- Glycogenes ↔ NCBI Gene (via rdfs:seeAlso)
- Diseases ↔ DOID/MONDO (via rdfs:seeAlso)
- Lectins ↔ UniProt (via sugarbind:uniprotId)
- Pathways ↔ Reactome (via pathway_reactome graph)
- Glycans ↔ ChEBI/PubChem (via Resource_entry)

### Recommended Question Types
- Questions about glycosylation sites for specific proteins
- Disease-glycogene associations
- Glycoprotein counts by organism
- Lectin-glycan binding specificity
- Glycan epitope tissue/organism associations

---

## Database Overview

### Purpose and Scope
GlyCosmos serves as the central hub for glycoscience data, providing:
- Glycan structure data from GlyTouCan (117,864 glycans)
- Glycoprotein annotations (153,178 proteins)
- Glycosylation site positions (414,798 sites)
- Glycogene information (423,164 genes)
- Glycan epitope data (173 epitopes)
- Lectin-glycan interactions (739 lectins)

### Key Data Types and Entities
1. **Glycans (Saccharides)**: Core glycan structures with GlyTouCan IDs
2. **Glycoproteins**: Proteins with glycosylation annotations
3. **Glycosylation Sites**: Specific positions on proteins where glycosylation occurs
4. **Glycogenes**: Genes involved in glycan biosynthesis
5. **Glycan Epitopes**: Immunologically relevant glycan structures
6. **Lectins**: Carbohydrate-binding proteins

### Dataset Statistics
| Entity Type | Count |
|-------------|-------|
| Glycans | 117,864 |
| Glycoproteins | 153,178 |
| Glycosylation Sites | 414,798 |
| Glycogenes | 423,164 |
| Glycoepitopes | 173 |
| Lectins | 739 |
| Human glycoproteins | 16,604 |
| Human glycosylation sites | 130,869 |
| Human glycogenes | 10,109 |
| Diseases with glycogene associations | 4,372 |

### Available Access Methods
- SPARQL endpoint: https://ts.glycosmos.org/sparql
- Multi-graph architecture with 100+ named graphs
- Full-text search via bif:contains

---

## Structure Analysis

### Performance Strategies

**Strategy 1: Always Specify FROM Clause**
- Why needed: GlyCosmos has 100+ named graphs
- When to apply: Every query
- Impact: 10-100x speed improvement
- Example: Query epitopes without FROM searches all graphs

**Strategy 2: Early Taxonomy Filtering**
- Why needed: Large datasets (414K sites) cause timeouts
- When to apply: Any query on glycoproteins or glycosylation sites
- Impact: Reduces dataset from 414K to ~130K for human only
- Example: `?protein glycan:has_taxon <http://identifiers.org/taxonomy/9606>`

**Strategy 3: Use bif:contains for Label Searches**
- Why needed: Full-text index with relevance scoring
- When to apply: Searching epitope names, protein labels
- Impact: Fast searches with ranking
- Example: `?label bif:contains "'Lewis'" option (score ?sc)`

**Strategy 4: Use FILTER(CONTAINS()) for Non-Label Properties**
- Why needed: bif:contains only works on rdfs:label
- When to apply: Searching descriptions, other text fields
- Impact: Works but slower than bif:contains
- Example: `FILTER(CONTAINS(LCASE(?description), "transferase"))`

**Strategy 5: Always Add LIMIT for Large Datasets**
- Why needed: Prevent timeouts on 414K+ sites
- When to apply: Any unbounded query
- Impact: Essential for completion
- Example: `LIMIT 100`

### Common Pitfalls

**Error 1: Omitting FROM Clause**
- Cause: Multi-graph architecture
- Symptoms: Timeout or slow queries
- Solution: Always include FROM clause(s)
```sparql
# Wrong (searches all graphs)
SELECT ?epitope WHERE { ?epitope a glycan:Glycan_epitope }

# Correct
SELECT ?epitope 
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE { ?epitope a glycan:Glycan_epitope }
```

**Error 2: Using bif:contains on Non-Label Fields**
- Cause: Full-text index only on rdfs:label/skos:altLabel
- Symptoms: Empty results or errors
- Solution: Use FILTER(CONTAINS()) for other fields
```sparql
# Wrong
?description bif:contains "'receptor'"

# Correct
FILTER(CONTAINS(LCASE(?description), "receptor"))
```

**Error 3: Querying All Glycosylation Sites Without Filter**
- Cause: 414K sites without filtering
- Symptoms: Timeout
- Solution: Filter by organism or protein first
```sparql
# Wrong (timeout)
SELECT ?site WHERE { ?site a glycoconjugate:Glycosylation_Site }

# Correct
SELECT ?site 
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    glycoconjugate:glycosylated_at ?site .
}
LIMIT 100
```

**Error 4: Relying on Glycan Labels**
- Cause: Glycan labels rarely populated (<1%)
- Symptoms: Empty results when searching by label
- Solution: Use GlyTouCan IDs instead
```sparql
# Wrong (low coverage)
SELECT ?glycan ?label WHERE { ?glycan rdfs:label ?label }

# Correct (use GlyTouCan IDs)
SELECT ?glycan ?gtcId WHERE { 
  ?glycan glytoucan:has_primary_id ?gtcId 
}
```

### Data Organization

**Core Graphs:**
1. `http://rdf.glytoucan.org/core` - Glycan structures with GlyTouCan IDs
2. `http://rdf.glycosmos.org/glycoprotein` - Glycoprotein annotations
3. `http://rdf.glycosmos.org/glycogenes` - Glycogene information
4. `http://rdf.glycoinfo.org/glycoepitope` - Glycan epitopes
5. `http://rdf.glycosmos.org/sugarbind` - Lectin data
6. `http://rdf.glycosmos.org/disease` - Disease-glycogene associations
7. `http://rdf.glycosmos.org/pathway_reactome` - Reactome pathway data

### Cross-Database Integration Points

**Integration 1: GlyCosmos → UniProt**
- Connection: rdfs:seeAlso from glycoproteins to UniProt URIs
- Format: `http://purl.uniprot.org/uniprot/{ACCESSION}`
- Coverage: 139K glycoproteins linked
- Example: Angiotensin-converting enzyme 2 (Q9BYF1)

**Integration 2: GlyCosmos → NCBI Gene**
- Connection: rdfs:seeAlso from glycogenes
- Coverage: 423K glycogenes linked
- Usage: Find genes involved in glycosylation

**Integration 3: GlyCosmos → Disease Ontologies**
- Connection: Disease graph with DOID references
- Coverage: 4,372 diseases with gene associations
- Format: `http://purl.obolibrary.org/obo/DOID_{ID}`

**Integration 4: GlyCosmos → ChEBI/PubChem**
- Connection: Glycans via Resource_entry
- Coverage: ~86% of glycans have cross-references
- Usage: Chemical structure information

**Integration 5: Lectins → UniProt**
- Connection: sugarbind:uniprotId property
- Coverage: 739 lectins with UniProt links
- Usage: Study lectin-glycan binding

---

## Complex Query Patterns Tested

### Pattern 1: Glycoprotein Glycosylation Site Retrieval

**Purpose**: Find glycosylation sites for specific human proteins

**Category**: Structured Query, Performance-Critical

**Naive Approach**: Query all sites without graph or organism filter

**What Happened**: Slow but works with LIMIT; without LIMIT would timeout

**Correct Approach**:
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glycoconjugate: <http://purl.jp/bio/12/glyco/conjugate#>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?label ?site ?position ?externalDB
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    glycoconjugate:glycosylated_at ?site .
  OPTIONAL { ?protein rdfs:label ?label }
  OPTIONAL { ?site faldo:location/faldo:position ?position }
  OPTIONAL { ?protein rdfs:seeAlso ?externalDB . FILTER(CONTAINS(STR(?externalDB), "uniprot")) }
  FILTER(CONTAINS(LCASE(?label), "angiotensin"))
}
ORDER BY ?position
```

**Results Obtained**:
- ACE2 (Angiotensin-converting enzyme 2): 616 glycosylation sites
- Successfully found UniProt link: Q9BYF1

**Natural Language Question Opportunities**:
1. "How many glycosylation sites does human ACE2 have?" - Category: Precision
2. "Which human proteins have the most glycosylation sites?" - Category: Completeness
3. "What are the glycosylation sites of human insulin receptor?" - Category: Precision

---

### Pattern 2: Glycoprotein Ranking by Site Count

**Purpose**: Find proteins with most glycosylation sites

**Category**: Completeness, Performance-Critical

**Correct Approach**:
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX glycoconjugate: <http://purl.jp/bio/12/glyco/conjugate#>

SELECT ?protein ?label (COUNT(?site) as ?siteCount)
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    glycoconjugate:glycosylated_at ?site .
  OPTIONAL { ?protein rdfs:label ?label }
}
GROUP BY ?protein ?label
ORDER BY DESC(?siteCount)
LIMIT 20
```

**Results Obtained**:
- P98164 (LRP2/Low-density lipoprotein receptor-related protein 2): 1153 sites
- P07911 (Uromodulin): 966 sites
- P13473 (LAMP2): 938 sites
- Q07954 (LRP1): 934 sites

**Natural Language Question Opportunities**:
1. "Which human glycoprotein has the most glycosylation sites?" - Category: Precision
2. "List the top 10 most heavily glycosylated human proteins" - Category: Completeness

---

### Pattern 3: Epitope Search with Full-Text

**Purpose**: Find glycan epitopes by name

**Category**: Structured Query

**Correct Approach** (using bif:contains):
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?epitope ?label
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  ?epitope a glycan:Glycan_epitope ;
    rdfs:label ?label .
  ?label bif:contains "'Lewis'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
```

**Results Obtained**:
- 18 Lewis-related epitopes found
- Lewis a, Lewis b, Lewis x, Lewis y, Sialyl Lewis a, Sialyl Lewis x, etc.

**Natural Language Question Opportunities**:
1. "What Lewis blood group-related glycan epitopes are in GlyCosmos?" - Category: Specificity
2. "Which glycan epitopes are related to the sialyl Lewis antigens?" - Category: Specificity

---

### Pattern 4: Glycogene Search by Function

**Purpose**: Find glycogenes with specific functional descriptions

**Category**: Structured Query

**Correct Approach** (using FILTER for descriptions):
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?gene ?symbol ?description
FROM <http://rdf.glycosmos.org/glycogenes>
WHERE {
  ?gene a glycan:Glycogene ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    rdfs:label ?symbol ;
    dcterms:description ?description .
  FILTER(CONTAINS(LCASE(?description), "transferase"))
}
LIMIT 30
```

**Results Obtained**:
- Found 30+ glycosyltransferases
- FUT1, FUT2, FUT3, FUT6 (fucosyltransferases)
- ABO (galactosyltransferase)
- B3GALNT1, B4GALNT2 (N-acetylgalactosaminyltransferases)
- ST3GAL6 (sialyltransferase)

**Natural Language Question Opportunities**:
1. "Which human genes encode glycosyltransferases?" - Category: Completeness
2. "What fucosyltransferase genes are recorded in GlyCosmos?" - Category: Specificity
3. "Which human genes are involved in sialylation?" - Category: Integration

---

### Pattern 5: Ganglioside Epitope-Cancer Association

**Purpose**: Find epitopes associated with cancer tissues

**Category**: Specificity, Integration

**Correct Approach**:
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX glycoepitope: <http://www.glycoepitope.jp/epitopes/glycoepitope.owl#>

SELECT ?epitope ?label ?antibody ?tissue
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  ?epitope a glycan:Glycan_epitope ;
    rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), "gm") || CONTAINS(LCASE(?label), "gd"))
  OPTIONAL { ?epitope glycoepitope:has_antibody ?antibody }
  OPTIONAL { ?epitope glycoepitope:tissue ?tissue }
}
LIMIT 30
```

**Results Obtained**:
- N-Acetyl GM2 (EP0051) associated with multiple cancers
- Associated tissues: embryonal carcinoma, lung adenocarcinoma, squamous cell cancer, teratocarcinoma
- Multiple antibodies recognize this epitope

**Natural Language Question Opportunities**:
1. "Which ganglioside epitopes are associated with cancer?" - Category: Specificity
2. "What tissues express the GM2 ganglioside?" - Category: Precision
3. "Which antibodies recognize ganglioside epitopes?" - Category: Integration

---

### Pattern 6: Disease-Glycogene Association Count

**Purpose**: Count diseases with glycogene associations

**Category**: Completeness

**Correct Approach**:
```sparql
PREFIX sio: <http://semanticscience.org/resource/>
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>

SELECT (COUNT(DISTINCT ?disease) as ?diseaseCount) 
       (COUNT(DISTINCT ?gene) as ?geneRelationCount)
FROM <http://rdf.glycosmos.org/disease>
WHERE {
  ?disease a glycan:Disease ;
    sio:SIO_000255 ?gene .
}
```

**Results Obtained**:
- 4,372 unique diseases with glycogene associations
- 26,827 disease-gene relationships

**Natural Language Question Opportunities**:
1. "How many diseases are associated with glycogenes in GlyCosmos?" - Category: Completeness
2. "How many disease-glycogene associations exist?" - Category: Completeness

---

### Pattern 7: Lectin-UniProt Integration

**Purpose**: Find lectins with UniProt identifiers

**Category**: Integration

**Correct Approach**:
```sparql
PREFIX sugarbind: <http://rdf.glycoinfo.org/SugarBind/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?lectin ?label ?uniprotRef
FROM <http://rdf.glycosmos.org/sugarbind>
WHERE {
  ?lectin a sugarbind:Lectin ;
    rdfs:label ?label ;
    sugarbind:uniprotId ?uniprotRef .
  FILTER(CONTAINS(STR(?uniprotRef), "uniprot"))
}
LIMIT 30
```

**Results Obtained**:
- 739 lectins with UniProt links
- Includes viral lectins: Hemagglutinin (H1, H2, H3, H5), HIV gp120
- Bacterial adhesins: FimH, PapG, FedF, GafD
- TcdA (C. difficile toxin)

**Natural Language Question Opportunities**:
1. "Which lectins in GlyCosmos bind to specific glycans?" - Category: Specificity
2. "What viral lectins are recorded in the SugarBind database?" - Category: Specificity
3. "What is the UniProt ID for the influenza hemagglutinin lectin?" - Category: Integration

---

### Pattern 8: Glycoprotein Count by Organism

**Purpose**: Count glycoproteins across different species

**Category**: Completeness

**Correct Approach**:
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>

SELECT ?taxon (COUNT(DISTINCT ?protein) as ?proteinCount)
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
    glycan:has_taxon ?taxon .
}
GROUP BY ?taxon
ORDER BY DESC(?proteinCount)
LIMIT 20
```

**Results Obtained**:
- Human (9606): 16,604 glycoproteins
- Mouse (10090): 10,713 glycoproteins
- Rat (10116): 2,576 glycoproteins
- Arabidopsis (3702): 2,251 glycoproteins
- C. elegans (6239): 1,447 glycoproteins

**Natural Language Question Opportunities**:
1. "How many human glycoproteins are in GlyCosmos?" - Category: Completeness
2. "Which model organisms have glycoprotein data in GlyCosmos?" - Category: Completeness
3. "Compare the number of glycoproteins between human and mouse" - Category: Completeness

---

### Pattern 9: Reactome Pathway Integration

**Purpose**: Find glycosylation-related pathways from Reactome

**Category**: Integration

**Correct Approach**:
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT ?pathway ?name
FROM <http://rdf.glycosmos.org/pathway_reactome>
WHERE {
  ?pathway a bp:Pathway ;
    bp:displayName ?name .
}
LIMIT 30
```

**Results Obtained**:
- Pathways found include: MTOR signalling, TLR4 cascade, Cell Cycle, Neuronal System
- BioPAX format data from Reactome

**Natural Language Question Opportunities**:
1. "What Reactome pathways involve glycogenes?" - Category: Integration
2. "Is the TLR4 signaling pathway represented in GlyCosmos?" - Category: Specificity

---

### Pattern 10: Human Glycosylation Site Statistics

**Purpose**: Get comprehensive statistics for human glycosylation

**Category**: Completeness, Performance-Critical

**Correct Approach**:
```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glycoconjugate: <http://purl.jp/bio/12/glyco/conjugate#>

SELECT (COUNT(DISTINCT ?site) as ?count)
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    glycoconjugate:glycosylated_at ?site .
}
```

**Results Obtained**:
- 130,869 human glycosylation sites
- Average 2.6 sites per protein
- Max 276 sites per protein (based on documentation)

**Natural Language Question Opportunities**:
1. "How many glycosylation sites are annotated for human proteins?" - Category: Completeness
2. "What is the average number of glycosylation sites per human glycoprotein?" - Category: Completeness

---

## Simple Queries Performed

1. **Epitope count**: 173 glycoepitopes total
2. **Glycan count**: 117,864 glycans with GlyTouCan IDs
3. **Human glycoprotein count**: 16,604
4. **Human glycogene count**: 10,109
5. **Total glycosylation sites**: 414,798

### Entities Found for Question Use

| Entity | ID | Description |
|--------|-----|-------------|
| ACE2 | Q9BYF1 | Angiotensin-converting enzyme 2 (616 glycosylation sites) |
| LRP2 | P98164 | Low-density lipoprotein receptor-related protein 2 (1153 sites) |
| Uromodulin | P07911 | Most glycosylated urinary protein |
| Lewis a | EP0007 | Blood group epitope |
| GM2 | EP0051 | Ganglioside associated with cancer |
| FimH | P08191 | E. coli adhesin lectin |
| Hemagglutinin | P03462 | Influenza A virus |
| INSR | 3643 | Insulin receptor glycogene |
| FUT1 | 2523 | Fucosyltransferase 1 (H blood group) |
| ABO | 28 | ABO blood group glycosyltransferase |

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions:**

1. "What human glycoproteins are associated with Alzheimer's disease?"
   - Databases: glycoprotein, disease
   - Knowledge Required: Graph URIs, disease-gene relationships via SIO
   - Category: Integration
   - Difficulty: Hard

2. "Which lectins bind to glycans found on human glycoproteins?"
   - Databases: sugarbind, glycoprotein, glytoucan
   - Knowledge Required: Multi-graph joins, lectin-glycan-protein relationships
   - Category: Integration
   - Difficulty: Hard

3. "What Reactome pathways involve human glycogenes that encode transferases?"
   - Databases: glycogenes, pathway_reactome
   - Knowledge Required: BioPAX ontology, gene-pathway links
   - Category: Integration
   - Difficulty: Hard

4. "Find the UniProt IDs for all human glycoproteins with more than 100 glycosylation sites"
   - Databases: glycoprotein
   - Knowledge Required: Aggregation, external reference extraction
   - Category: Integration
   - Difficulty: Medium

5. "Which glycan epitopes are recognized by antibodies in specific cancer types?"
   - Databases: glycoepitope
   - Knowledge Required: Epitope-antibody-tissue relationships
   - Category: Specificity
   - Difficulty: Medium

**Performance-Critical Questions:**

1. "How many unique glycosylation sites are annotated for human proteins?"
   - Database: glycoprotein
   - Knowledge Required: FROM clause, taxonomy filter, COUNT DISTINCT
   - Category: Completeness
   - Difficulty: Medium

2. "List all human glycoproteins sorted by number of glycosylation sites"
   - Database: glycoprotein
   - Knowledge Required: Aggregation with GROUP BY, taxonomy filter
   - Category: Completeness
   - Difficulty: Medium

3. "Count the number of glycogenes per organism"
   - Database: glycogenes
   - Knowledge Required: Multi-graph awareness, aggregation
   - Category: Completeness
   - Difficulty: Easy

**Error-Avoidance Questions:**

1. "Find glycogenes whose description contains 'kinase'"
   - Database: glycogenes
   - Knowledge Required: Use FILTER(CONTAINS()) not bif:contains for descriptions
   - Category: Structured Query
   - Difficulty: Medium

2. "Search for glycan epitopes related to Lewis blood groups"
   - Database: glycoepitope
   - Knowledge Required: Use bif:contains for rdfs:label with proper quoting
   - Category: Structured Query
   - Difficulty: Easy

**Complex Filtering Questions:**

1. "Find all human glycosyltransferases involved in N-glycosylation"
   - Database: glycogenes
   - Knowledge Required: Functional description filtering, taxonomy
   - Category: Structured Query
   - Difficulty: Medium

2. "Which ganglioside epitopes have antibody annotations and are associated with tumors?"
   - Database: glycoepitope
   - Knowledge Required: Multiple OPTIONAL clauses, tissue filtering
   - Category: Structured Query
   - Difficulty: Medium

3. "Find glycoproteins with glycosylation sites at specific sequence positions"
   - Database: glycoprotein
   - Knowledge Required: FALDO position queries, property paths
   - Category: Structured Query
   - Difficulty: Medium

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions:**

1. "What is the GlyTouCan ID format for glycans?"
   - Method: Pattern recognition from data
   - Category: Precision
   - Difficulty: Easy

2. "How many glycan epitopes are in GlyCosmos?"
   - Method: Simple COUNT query
   - Category: Completeness
   - Difficulty: Easy

3. "What is the glycoprotein entry for human ACE2?"
   - Method: Label/ID search
   - Category: Precision
   - Difficulty: Easy

4. "How many lectins are in the SugarBind database?"
   - Method: Simple COUNT query
   - Category: Completeness
   - Difficulty: Easy

**ID Mapping Questions:**

1. "What UniProt ID corresponds to the GlyCosmos glycoprotein P02763?"
   - Method: rdfs:seeAlso extraction
   - Category: Integration
   - Difficulty: Easy

2. "What DOID is associated with disease entry DOID:0014667 in GlyCosmos?"
   - Method: rdfs:seeAlso extraction
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**This Database as Source:**
- → UniProt: Glycoprotein/lectin cross-references
- → NCBI Gene: Glycogene cross-references
- → DOID/MONDO: Disease cross-references
- → ChEBI/PubChem: Glycan chemical information
- → Reactome: Pathway data
- → PDB: Structural cross-references

**This Database as Target:**
- UniProt →: Proteins with glycosylation annotations
- NCBI Taxonomy →: Organism information
- Literature →: PubMed citations

**Complex Multi-Database Paths:**
- Glycogene → Disease → External Disease Ontology: Gene-disease associations
- Glycoprotein → Glycosylation Site → Glycan: Full glycosylation context
- Lectin → UniProt → Gene: Lectin gene identification

---

## Lessons Learned

### What Knowledge is Most Valuable
1. FROM clause is absolutely critical - without it, queries search 100+ graphs
2. bif:contains only works on rdfs:label - use FILTER for other properties
3. Human filtering essential for performance with 414K+ sites
4. Multi-graph architecture requires explicit knowledge of graph URIs
5. Cross-references use rdfs:seeAlso consistently

### Common Pitfalls Discovered
1. Trying bif:contains on description fields returns empty
2. Querying all sites without LIMIT causes timeout
3. Glycan labels have <1% coverage - use GlyTouCan IDs
4. Disease-gene relationships use SIO vocabulary (SIO_000255)

### Recommendations for Question Design
1. Focus on human data for performance-critical questions
2. Test multi-graph queries for integration questions
3. Include epitope-tissue-cancer associations for specificity
4. Use glycogene descriptions for functional queries
5. Leverage lectin-UniProt links for cross-database questions

### Performance Notes
- FROM clause provides 10-100x speedup
- Human-only queries complete in 5-10 seconds
- Full dataset queries need careful LIMIT
- Aggregations with GROUP BY work well with early filtering

---

## Notes and Observations

1. **Rich Disease Data**: 4,372 diseases with glycogene associations opens up disease-centric questions
2. **Epitope-Cancer Links**: GM2 and other gangliosides have cancer tissue associations
3. **Viral Lectins**: Influenza hemagglutinins (H1-H5) and HIV gp120 provide interesting pathogen-related queries
4. **Blood Group Antigens**: Lewis, ABO system glycans well represented
5. **ACE2 Relevance**: COVID-19 receptor has 616 glycosylation sites - biomedically relevant

---

## Next Steps

**Recommended for Question Generation:**
- Priority: Glycoprotein queries (most data, good performance)
- Focus: Disease-glycogene associations, epitope-tissue links
- Include: Lectin-pathogen queries for specificity
- Test: Multi-graph integration patterns

**Further Exploration Needed:**
- Glycan-structure queries (WURCS/GlycoCT representations)
- More complex pathway integrations
- Organism-specific glycome comparisons

---

**Session Complete - Ready for Next Database**

```
Database: glycosmos
Status: ✅ COMPLETE
Report: /evaluation/exploration/glycosmos_exploration.md
Patterns Tested: 10
Questions Identified: ~25
Integration Points: 6+
```
