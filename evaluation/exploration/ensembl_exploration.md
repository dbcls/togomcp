# Ensembl Database Exploration Report

**Date**: 2026-01-31
**Session**: 1

## Executive Summary

Ensembl is a comprehensive genomics database containing genome annotations for 100+ species, with genes, transcripts, proteins, and exons organized hierarchically. The database is particularly strong for:

- **Key capabilities requiring deep knowledge**: Cross-database integration with ChEMBL for pharmacogenomics, species filtering for multi-species datasets, chromosome-specific queries, transcript quality filtering (MANE Select)
- **Major integration opportunities**: EBI endpoint co-location with ChEMBL, ChEBI, Reactome enables powerful cross-database queries
- **Most valuable patterns discovered**: UniProt cross-references enable drug target mapping, FALDO coordinates for genomic locations, biotype filtering for gene classification
- **Recommended question types**: Cross-database pharmacogenomics queries, chromosome-specific drug target analysis, transcript quality annotation queries

## Database Overview

- **Purpose and scope**: Genome annotations for 100+ vertebrate species including genes, transcripts, proteins, exons
- **Key data types and entities**: EnsemblGene, EnsemblTranscript, EnsemblProtein, EnsemblExon
- **Dataset size and performance considerations**: 
  - ~3M total genes across all species
  - ~87,688 human genes (23,262 protein-coding)
  - ~744,820 mouse genes (largest species)
  - ~24,346 human genes have UniProt cross-references (~28%)
- **Available access methods**: SPARQL via rdfportal.org/ebi/sparql endpoint, bif:contains for text search

## Structure Analysis

### Performance Strategies

1. **Species Filtering (CRITICAL)**
   - Why it's needed: Database contains 100+ species; without filtering, queries return mixed-species results
   - When to apply: ALWAYS when querying for human-specific data
   - Performance impact: Without filter, queries may return incorrect results from multiple species
   - Pattern: `obo:RO_0002162 taxonomy:9606` for human

2. **UniProt Cross-Reference Pre-filtering**
   - Why it's needed: Only ~28% of human genes have UniProt xrefs; filtering early improves cross-database join performance
   - When to apply: Before joining with ChEMBL or other protein-centric databases
   - Pattern: `FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))`

3. **Chromosome Filtering**
   - Why it's needed: Focuses queries on specific genomic regions
   - When to apply: For region-specific analyses (e.g., chromosome 17 drug targets)
   - Pattern: `FILTER(CONTAINS(STR(?chr), "GRCh38/17"))`

4. **bif:contains for Text Search**
   - Why it's needed: REGEX is slow; bif:contains uses full-text index
   - Performance impact: 10-100x faster than FILTER with CONTAINS
   - Pattern: `?label bif:contains "'BRCA*'" option (score ?sc)`

5. **DISTINCT with FALDO Queries**
   - Why it's needed: FALDO may store begin/end positions separately, causing duplicates
   - When to apply: Any query retrieving genomic coordinates
   - Pattern: `SELECT DISTINCT ... faldo:location ...`

6. **Biotype Filtering for Gene Classification**
   - Why it's needed: Filter to specific gene types (protein-coding, miRNA, lncRNA)
   - Key biotypes:
     - ENSGLOSSARY_0000026: protein-coding (23,262 human genes)
     - ENSGLOSSARY_0000028: lncRNA (36,492 human genes)
     - ENSGLOSSARY_0000038: miRNA (1,945 human genes)

### Common Pitfalls

1. **Missing Species Filter**
   - Cause: Querying gene symbol without species constraint
   - Symptoms: Results from multiple species (mouse, pig, zebrafish, etc.)
   - Solution: Always include `obo:RO_0002162 taxonomy:9606` for human queries
   - Example: TP53 query without filter returns 20+ different species orthologs

2. **Incorrect Strand Detection**
   - Cause: Trying to get strand from non-existent property
   - Wrong: `faldo:location/faldo:strand ?strand`
   - Solution: Check position type (ForwardStrandPosition/ReverseStrandPosition)
   - Pattern: `BIND(IF(?strand_type = faldo:ForwardStrandPosition, "+", "-") AS ?strand)`

3. **Cross-Database Query Without Pre-Filtering**
   - Cause: Not filtering before expensive cross-database joins
   - Symptoms: Timeout or very slow execution
   - Solution: Apply species, chromosome, and UniProt filters EARLY within GRAPH blocks

4. **Missing Proteins for Non-Coding Transcripts**
   - Cause: Not all transcripts encode proteins (lncRNA, miRNA)
   - Solution: Use OPTIONAL for `so:translates_to` or filter by protein-coding biotype

### Data Organization

1. **Gene Layer**
   - Entity type: terms:EnsemblGene
   - Properties: identifier, label, description, biotype, organism, chromosome
   - Cross-references: UniProt, HGNC, NCBI Gene

2. **Transcript Layer**
   - Entity type: terms:EnsemblTranscript
   - Properties: identifier, biotype, transcript flags
   - Quality flags: MANE Select (ENSGLOSSARY_0000365), canonical, APPRIS

3. **Protein Layer**
   - Entity type: terms:EnsemblProtein
   - Properties: identifier
   - Cross-references: UniProt

4. **Exon Layer**
   - Entity type: terms:EnsemblExon
   - Organization: Ordered via EnsemblOrderedExon with sio:SIO_000300 position

5. **Genomic Coordinates**
   - FALDO ontology for precise coordinates
   - Properties: faldo:begin, faldo:end, position type for strand

### Cross-Database Integration Points

**Integration 1: Ensembl → ChEMBL (via UniProt)**
- Connection: rdfs:seeAlso → UniProt URI → cco:hasTargetComponent/skos:exactMatch
- Required pre-filtering: Species (human), UniProt existence
- Knowledge required: Both graph URIs, property path patterns
- Performance: 1-4 seconds with proper filtering
- Use case: Find drugs targeting proteins encoded by specific genes

**Integration 2: Ensembl → Reactome (via UniProt)**
- Connection: rdfs:seeAlso → UniProt ID → bp:xref with bp:db "UniProt"^^xsd:string
- Required pre-filtering: Species, UniProt existence
- Knowledge required: Both graph URIs, xsd:string type for bp:db
- Use case: Link genes to biological pathways

**Integration 3: Ensembl → ChEBI (via ChEMBL)**
- Three-database integration: Gene → Drug target → Chemical compound
- Path: Ensembl → UniProt → ChEMBL target → molecule → ChEBI
- Use case: Complete chemical information for drugs targeting specific genes

## Complex Query Patterns Tested

### Pattern 1: Cross-Database Gene-Drug Target Integration

**Purpose**: Find genes that encode proteins targeted by approved drugs

**Category**: Cross-Database, Performance-Critical

**Naive Approach**: Join Ensembl genes with ChEMBL targets without filtering

**What Happened Without Proper Filtering**:
- Mixed species results (mouse, pig, etc.) instead of human only
- Incomplete results without UniProt pre-filtering

**Correct Approach**: 
```sparql
GRAPH <http://rdfportal.org/dataset/ensembl> {
  ?gene a terms:EnsemblGene ;
        rdfs:seeAlso ?uniprot ;
        obo:RO_0002162 taxonomy:9606 .
  FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
}
GRAPH <http://rdf.ebi.ac.uk/dataset/chembl> {
  ?target cco:hasTargetComponent/skos:exactMatch ?uniprot .
  ?mechanism cco:hasTarget ?target ; cco:hasMolecule ?molecule .
  ?molecule cco:highestDevelopmentPhase 4 .
}
```

**Results Obtained**:
- Successfully linked ERBB2 to 13 approved drugs (trastuzumab, lapatinib, pertuzumab, etc.)
- SLC6A4 (serotonin transporter) linked to 30 approved drugs
- ACE linked to 15 approved drugs

**Natural Language Question Opportunities**:
1. "Which approved drugs target proteins encoded by genes on chromosome 17?" - Category: Integration
2. "What FDA-approved drugs target the HER2/ERBB2 protein?" - Category: Integration
3. "Which human genes encode the most druggable proteins?" - Category: Completeness

---

### Pattern 2: Chromosome-Specific Drug Target Analysis

**Purpose**: Find drug targets on a specific chromosome with drug counts

**Category**: Cross-Database, Complex Filtering

**Naive Approach**: Simple join without chromosome or phase filtering

**Correct Approach**:
```sparql
GRAPH <http://rdfportal.org/dataset/ensembl> {
  ?gene so:part_of ?chr ;
        obo:RO_0002162 taxonomy:9606 .
  FILTER(CONTAINS(STR(?chr), "GRCh38/17"))
  FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
}
GRAPH <http://rdf.ebi.ac.uk/dataset/chembl> {
  {
    SELECT ?target (COUNT(DISTINCT ?mol) as ?molecule_count)
    WHERE {
      ?mech cco:hasTarget ?target ; cco:hasMolecule ?mol .
      ?mol cco:highestDevelopmentPhase 4 .
    }
    GROUP BY ?target
  }
}
```

**Results Obtained**:
- Chromosome 17: SLC6A4 (30 drugs), ACE (15 drugs), ERBB2 (13 drugs), TOP2A (8 drugs)
- Query completed in ~2-4 seconds

**Natural Language Question Opportunities**:
1. "Which genes on human chromosome 17 encode targets of approved drugs?" - Category: Integration
2. "What is the most targeted gene on chromosome 17 by FDA-approved drugs?" - Category: Specificity
3. "How many approved drugs target proteins encoded by chromosome X genes?" - Category: Completeness

---

### Pattern 3: Gene-Transcript-Protein Hierarchy with Cross-References

**Purpose**: Navigate the central dogma hierarchy with external database links

**Category**: Structured Query, Integration

**Naive Approach**: Direct pattern matching without following relationships

**Correct Approach**:
```sparql
?gene a terms:EnsemblGene ;
      rdfs:label ?gene_label .
?transcript so:transcribed_from ?gene ;
            so:translates_to ?protein .
?protein rdfs:seeAlso ?uniprot .
FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
```

**Results Obtained**:
- BRCA1: 20+ transcript-protein pairs identified
- Multiple UniProt isoforms linked (P38398 canonical, H0Y850, E7EQW4, etc.)

**Natural Language Question Opportunities**:
1. "How many protein isoforms does the BRCA1 gene encode?" - Category: Completeness
2. "What are the UniProt IDs for all proteins encoded by human TP53?" - Category: Precision
3. "Which BRCA1 transcript is the MANE Select reference?" - Category: Specificity

---

### Pattern 4: Genomic Coordinates with FALDO

**Purpose**: Retrieve precise genomic locations with strand information

**Category**: Structured Query

**Naive Approach**: Wrong strand property path

**What Happened**:
- Error: Non-existent `faldo:strand` property

**Correct Approach**:
```sparql
?gene faldo:location ?loc ;
      so:part_of ?chr .
?loc faldo:begin/faldo:position ?start ;
     faldo:end/faldo:position ?end ;
     faldo:begin/rdf:type ?strand_type .
BIND(IF(?strand_type = faldo:ForwardStrandPosition, "+", "-") AS ?strand)
```

**Results Obtained**:
- BRCA1: chr17:43044295-43170245, reverse strand (-)
- Correctly identified chromosome and assembly (GRCh38)

**Natural Language Question Opportunities**:
1. "What are the genomic coordinates of the human BRCA1 gene?" - Category: Precision
2. "Which strand is the human TP53 gene located on?" - Category: Precision
3. "What is the length of the EGFR gene in base pairs?" - Category: Precision

---

### Pattern 5: Species Filter Requirement (Error Avoidance)

**Purpose**: Demonstrate importance of species filtering

**Category**: Error-Avoidance

**Naive Approach (WITHOUT species filter)**:
```sparql
?gene a terms:EnsemblGene ;
      rdfs:label ?label .
FILTER(?label = "TP53")
```

**What Happened**:
- Returned 20+ results from different species (human, mouse, zebrafish, pig, cow, horse, etc.)
- Gene IDs from multiple organisms: ENSG (human), ENSMUSG (mouse), ENSDARG (zebrafish), ENSBTAG (cow)

**Correct Approach**:
```sparql
?gene a terms:EnsemblGene ;
      rdfs:label ?label ;
      obo:RO_0002162 taxonomy:9606 .
FILTER(?label = "TP53")
```

**Results Obtained**:
- Only human TP53 (ENSG00000141510)

**Natural Language Question Opportunities**:
1. "What is the Ensembl gene ID for human TP53?" - Category: Precision
2. "Find all human kinase genes" - Category: Completeness

---

### Pattern 6: Transcript Quality Annotation (MANE Select)

**Purpose**: Identify reference transcripts using quality flags

**Category**: Specificity, Structured Query

**Naive Approach**: Not filtering by quality flags

**Correct Approach**:
```sparql
?gene rdfs:label "BRCA1" ;
      obo:RO_0002162 taxonomy:9606 .
?transcript so:transcribed_from ?gene ;
            terms:has_transcript_flag <http://ensembl.org/glossary/ENSGLOSSARY_0000365> .
```

**Results Obtained**:
- ENST00000357654 is the MANE Select transcript for BRCA1

**Natural Language Question Opportunities**:
1. "What is the MANE Select transcript for human BRCA1?" - Category: Specificity
2. "Which transcript of TP53 is the canonical reference?" - Category: Precision

---

### Pattern 7: Exon Structure Retrieval

**Purpose**: Get ordered exon information for transcripts

**Category**: Structured Query

**Correct Approach**:
```sparql
?transcript sio:SIO_000974 ?ordered_exon .
?ordered_exon sio:SIO_000628 ?exon ;
              sio:SIO_000300 ?order .
?exon faldo:location/faldo:begin/faldo:position ?start .
```

**Results Obtained**:
- ENST00000357654: 23 exons with precise coordinates
- Correctly ordered by exon position

**Natural Language Question Opportunities**:
1. "How many exons does the main BRCA1 transcript have?" - Category: Completeness
2. "What are the exon boundaries of transcript ENST00000357654?" - Category: Precision

---

### Pattern 8: Text Search with Boolean Operators

**Purpose**: Find genes by functional keywords in descriptions

**Category**: Structured Query

**Correct Approach**:
```sparql
?description bif:contains "('kinase' AND 'receptor')" option (score ?sc) .
ORDER BY DESC(?sc)
```

**Results Obtained**:
- ROR1, ROR2 (receptor tyrosine kinases)
- RIPK3 (receptor interacting kinase)
- IRAK1, IRAK2, IRAK3 (interleukin receptor kinases)
- 20+ relevant genes found with relevance ranking

**Natural Language Question Opportunities**:
1. "Find human genes described as receptor tyrosine kinases" - Category: Structured Query
2. "Which human genes are involved in receptor kinase activity?" - Category: Completeness

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "BRCA1"
   - Found: ENSG00000012048 - BRCA1 DNA repair associated
   - Usage: Gene lookup, cross-database integration examples

2. Search: "TP53"
   - Found: ENSG00000141510 - TP53 tumor protein
   - Usage: Multi-species comparison, transcript structure

3. Search: "ERBB2"
   - Found: ENSG00000141736 - erb-b2 receptor tyrosine kinase 2
   - Usage: Drug target integration examples

4. Search: "kinase receptor"
   - Found: ROR1 (ENSG00000185483), ROR2 (ENSG00000169071)
   - Usage: Functional annotation queries

5. Search: Chromosome X genes
   - Found: HTR2C, CA5B, SLC9A7, GPC4, TLR8
   - Usage: Chromosome-specific queries

6. microRNA search
   - Found: MIR320A (ENSG00000208037), MIR127 (ENSG00000207608)
   - Usage: Non-coding RNA biotype queries

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "Which approved drugs target proteins encoded by genes on human chromosome 17?"
   - Databases involved: Ensembl, ChEMBL
   - Knowledge Required: Both graph URIs, species filtering, chromosome filtering, UniProt join pattern, development phase filtering
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 2

2. "What FDA-approved drugs target the human HER2/ERBB2 receptor protein?"
   - Databases involved: Ensembl, ChEMBL
   - Knowledge Required: Ensembl-ChEMBL linking via UniProt, phase 4 filtering
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

3. "How many human genes encode proteins that are targets of marketed drugs?"
   - Databases involved: Ensembl, ChEMBL
   - Knowledge Required: Cross-database join, species filter, development phase filter
   - Category: Completeness
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

4. "Which genes on the X chromosome encode drug targets?"
   - Databases involved: Ensembl, ChEMBL
   - Knowledge Required: Chromosome filtering pattern, UniProt integration
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 2

5. "Find human genes that encode proteins targeted by cancer drugs"
   - Databases involved: Ensembl, ChEMBL
   - Knowledge Required: Cross-database pattern, text search in ChEMBL
   - Category: Integration
   - Difficulty: Hard
   - Pattern Reference: Pattern 1

**Performance-Critical Questions**:

1. "How many human protein-coding genes are annotated in Ensembl?"
   - Database: Ensembl
   - Knowledge Required: Biotype filtering (ENSGLOSSARY_0000026), species filter
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 5

2. "List all human microRNA genes in Ensembl"
   - Database: Ensembl
   - Knowledge Required: Biotype filtering (ENSGLOSSARY_0000038), species filter
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: None (direct query)

3. "How many human genes have UniProt cross-references?"
   - Database: Ensembl
   - Knowledge Required: Species filter, UniProt URI pattern
   - Category: Completeness
   - Difficulty: Easy
   - Pattern Reference: Pattern 3

4. "Find human genes whose descriptions mention both 'kinase' and 'receptor'"
   - Database: Ensembl
   - Knowledge Required: bif:contains with boolean operators, species filter
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 8

**Error-Avoidance Questions**:

1. "What is the Ensembl gene ID for human TP53?"
   - Database: Ensembl
   - Knowledge Required: Species filter REQUIRED to avoid multi-species results
   - Category: Precision
   - Difficulty: Easy (but fails without species filter)
   - Pattern Reference: Pattern 5

2. "What chromosome is the human BRCA1 gene located on?"
   - Database: Ensembl
   - Knowledge Required: FALDO pattern, strand detection via position type
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

**Complex Filtering Questions**:

1. "Which human genes on chromosome 17 have multiple protein-coding transcripts?"
   - Database: Ensembl
   - Knowledge Required: Chromosome filter, transcript-gene relationship, biotype filter
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 3, 4

2. "What is the MANE Select transcript for human BRCA1?"
   - Database: Ensembl
   - Knowledge Required: Transcript flag URIs, MANE Select identifier
   - Category: Specificity
   - Difficulty: Medium
   - Pattern Reference: Pattern 6

3. "How many exons does the canonical BRCA1 transcript have?"
   - Database: Ensembl
   - Knowledge Required: Ordered exon structure via SIO ontology
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 7

4. "Find human genes on the reverse strand of chromosome 17"
   - Database: Ensembl
   - Knowledge Required: FALDO strand pattern, chromosome filtering
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 4

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the Ensembl gene ID for human BRCA1?"
   - Method: Simple SPARQL with label filter
   - Knowledge Required: None (straightforward with species filter)
   - Category: Precision
   - Difficulty: Easy

2. "What is the description of Ensembl gene ENSG00000141510?"
   - Method: Direct ID lookup
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

1. "What UniProt IDs are linked to Ensembl gene ENSG00000012048?"
   - Method: Cross-reference lookup via rdfs:seeAlso
   - Knowledge Required: UniProt URI pattern
   - Category: Integration
   - Difficulty: Easy

2. "What is the HGNC identifier for human BRCA1 in Ensembl?"
   - Method: Cross-reference lookup
   - Knowledge Required: HGNC URI pattern
   - Category: Integration
   - Difficulty: Easy

---

## Integration Patterns Summary

**Ensembl as Source**:
- → ChEMBL: Via UniProt rdfs:seeAlso → cco:hasTargetComponent/skos:exactMatch
- → Reactome: Via UniProt rdfs:seeAlso → bp:xref with bp:db "UniProt"^^xsd:string
- → ChEBI: Via ChEMBL molecules → skos:exactMatch to ChEBI

**Ensembl as Target**:
- NCBI Gene → Ensembl: Via togoid conversion
- UniProt → Ensembl: Via rdfs:seeAlso backlinks

**Complex Multi-Database Paths**:
- Ensembl → ChEMBL → ChEBI: Gene → Drug target → Chemical compound structure
- Ensembl → Reactome → ChEMBL: Gene → Pathway → Drug mechanisms

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **Species filtering is CRITICAL** - Ensembl contains 100+ species; without human filter, results are mixed
2. **UniProt cross-reference pattern** - Enables all cross-database integration with EBI databases
3. **FALDO coordinate patterns** - Non-obvious strand detection via position type
4. **Biotype URIs** - Essential for filtering to specific gene types
5. **EBI endpoint co-location** - ChEMBL, ChEBI, Reactome on same endpoint enables efficient joins

### Common Pitfalls Discovered
1. Missing species filter returns orthologs from multiple species
2. FALDO strand is encoded in position type, not a direct property
3. Not all transcripts encode proteins - need OPTIONAL or biotype filter
4. Cross-database queries need pre-filtering to avoid timeouts

### Recommendations for Question Design
1. Cross-database questions with Ensembl should focus on pharmacogenomics use cases
2. Species filtering questions can demonstrate common failure mode
3. FALDO coordinate questions test structural knowledge
4. Transcript quality annotations (MANE Select) are valuable specificity targets

### Performance Notes
- Simple gene searches: <1 second
- Chromosome queries: 1-3 seconds
- Cross-database with ChEMBL: 2-4 seconds with proper filtering
- Complex aggregation queries: 3-5 seconds

---

## Notes and Observations

1. **Mouse dominates gene count**: 744,820 genes vs 87,688 human - reflects multiple mouse strains/assemblies
2. **lncRNA outnumbers protein-coding**: 36,492 vs 23,262 in human - modern annotation includes many non-coding genes
3. **UniProt coverage is partial**: Only ~28% of human genes have UniProt xrefs - limits cross-database integration
4. **LRG entries**: Locus Reference Genomic entries appear alongside ENSG IDs for clinically important genes
5. **Transcript flags**: Multiple quality annotations (MANE, APPRIS, canonical) provide transcript prioritization

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: Cross-database pharmacogenomics, chromosome-specific drug targets, species filtering tests
- Avoid: Reactome integration (complex property paths), three-way database joins (timeout risk)
- Focus areas: Ensembl-ChEMBL integration, genomic coordinates, transcript quality

**Further Exploration Needed**:
- GRCh37 vs GRCh38 graph differences
- More detailed Reactome integration testing
- Cross-species orthology queries

---

**Session Complete - Ready for Next Database**
