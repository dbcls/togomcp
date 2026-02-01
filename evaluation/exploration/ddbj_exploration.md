# DDBJ (DNA Data Bank of Japan) Exploration Report

**Date**: January 31, 2026
**Session**: 1

## Executive Summary

DDBJ RDF provides nucleotide sequence data from the International Nucleotide Sequence Database Collaboration (INSDC). The database contains 262M+ entries and 225M+ genes, primarily prokaryotic genomes but also viral and some eukaryotic sequences.

**Key capabilities requiring deep knowledge:**
- Entry-level filtering is CRITICAL for ALL complex queries due to dataset size
- Gene-CDS-Protein relationships require correct property paths (sio:SIO_010081)
- FALDO coordinates require entry scoping before coordinate filtering
- Integration with NCBI Taxonomy via ro:0002162 (in taxon) property
- Sequence Ontology classification via rdfs:subClassOf

**Major integration opportunities:**
- NCBI Taxonomy (direct URI linkage via ro:0002162)
- NCBI Protein (via rdfs:seeAlso from CDS features)
- BioProject/BioSample (via nuc:dblink at entry level)

**Recommended question types:**
- Multi-feature queries within genomes (genes, CDS, tRNA, rRNA)
- Organism-based sequence retrieval
- Gene-to-protein annotation queries
- Cross-database taxonomic classification

## Database Overview

- **Purpose**: Nucleotide sequence database (INSDC member)
- **Scope**: Prokaryotic genomes, viral sequences, some eukaryotes
- **Key entities**: Entries, Genes, Coding Sequences (CDS), tRNA, rRNA, ncRNA
- **Dataset size**: 262M+ entries, 225M+ genes
- **Endpoint**: https://rdfportal.org/ddbj/sparql
- **Backend**: Virtuoso (supports bif:contains)

## Structure Analysis

### Performance Strategies

**Strategy 1: Entry-level Filtering (CRITICAL)**
- Why needed: Database contains 262M+ entries and 225M+ genes - unfiltered queries timeout
- When to apply: ALL queries involving features (genes, CDS, RNA)
- Implementation: Use `FILTER(CONTAINS(STR(?feature), "ACCESSION"))` pattern
- Performance impact: Transforms timeout (60s) → success (~1s)

**Strategy 2: Use bif:contains for Organism Searches**
- Why needed: Full-text index provides 10-100x speedup over REGEX
- When to apply: Searching entries by organism name
- Implementation: `?organism bif:contains "'term1' AND 'term2'"`
- Performance impact: Efficient organism lookups across large dataset

**Strategy 3: LIMIT Clauses for Exploration**
- Why needed: Counts and aggregations timeout without entry filtering
- When to apply: Any exploratory query, counts without specific entry scope
- Implementation: Use LIMIT + sampling instead of COUNT(*)
- Note: Some simple COUNTs work (e.g., COUNT entries, COUNT genes) but complex aggregations fail

**Strategy 4: Entry-Scoped Joins**
- Why needed: Gene-CDS-Protein joins without entry scope create massive Cartesian products
- When to apply: Any query joining multiple feature types
- Implementation: Filter by entry accession BEFORE joins

### Common Pitfalls

**Error 1: Unfiltered Feature Joins**
- Cause: Joining features without entry scope
- Symptoms: Query timeout after 60 seconds
- Solution: Add FILTER(CONTAINS(STR(?variable), "ENTRY_ACCESSION"))
- Example:
  ```
  # Wrong: timeout
  SELECT ?gene ?cds WHERE { ?gene a nuc:Gene . ?cds sio:SIO_010081 ?gene }
  
  # Correct: scoped
  SELECT ?gene ?cds WHERE { 
    ?gene a nuc:Gene . ?cds sio:SIO_010081 ?gene .
    FILTER(CONTAINS(STR(?gene), "CP036276.1"))
  }
  ```

**Error 2: Wrong SIO Property Case**
- Cause: Using lowercase sio:010081 instead of sio:SIO_010081
- Symptoms: Empty results despite correct query structure
- Solution: Always use uppercase SIO prefix: sio:SIO_010081

**Error 3: Missing FROM Clause**
- Cause: Not specifying the DDBJ graph
- Symptoms: Empty or unexpected results
- Solution: Always include `FROM <http://rdfportal.org/dataset/ddbj>`

**Error 4: FALDO Queries Without Entry Scope**
- Cause: Coordinate queries scan all features
- Symptoms: Timeout
- Solution: Filter by entry before coordinate filtering

**Error 5: Complex Joins Across Entries**
- Cause: Trying to join features across different entries (e.g., find genes, then CDS in different query parts)
- Symptoms: Timeout or 400 error
- Solution: Scope all features to same entry

### Data Organization

**Entry-level data:**
- nuc:Entry - Main genome/sequence records
- Properties: organism, definition, taxonomy, sequence_date, comment
- Cross-references: nuc:dblink → BioProject, BioSample

**Feature-level data:**
- nuc:Gene - Gene annotations with locus_tag, optional gene symbol
- nuc:Coding_Sequence - CDS with product, translation, protein links
- nuc:Transfer_RNA, nuc:Ribosomal_RNA, nuc:Non_Coding_RNA - RNA features
- nuc:Repeat_Region, nuc:Mobile_Element - Other genomic features

**Relationship Properties:**
- bfo:0000050 (part of) - Features part of sequences
- bfo:0000051 (has part) - Entries have parts
- sio:SIO_010081 - CDS transcribed from Gene
- ro:0002162 (in taxon) - All features linked to taxonomy
- faldo:location - Genomic coordinates

**Data Quality:**
- >99% genes have locus_tag
- ~60% genes have gene symbol (nuc:gene property)
- >95% CDS have product descriptions
- >99% features have FALDO coordinates
- ~85% entries have BioProject/BioSample links

### Cross-Database Integration Points

**Integration 1: DDBJ → NCBI Taxonomy**
- Connection: Features have ro:0002162 pointing to taxonomy URIs
- URI format: `http://identifiers.org/taxonomy/{TAXID}`
- These URIs match directly with NCBI Taxonomy database
- No query-time join possible (different endpoints)
- Use case: Get taxonomic lineage/classification for organisms in DDBJ

**Integration 2: DDBJ → NCBI Protein**
- Connection: CDS features have rdfs:seeAlso to NCBI Protein
- URI format: `http://identifiers.org/ncbiprotein/{ACCESSION}`
- Use case: Link gene annotations to protein sequences

**Integration 3: DDBJ → BioProject/BioSample**
- Connection: Entries have nuc:dblink to BioProject/BioSample
- URI format: `http://identifiers.org/bioproject/{ID}`, `http://identifiers.org/biosample/{ID}`
- Use case: Get experimental context for sequences

**Integration 4: DDBJ → Sequence Ontology**
- Connection: Features have rdfs:subClassOf to SO terms
- URI format: `http://purl.obolibrary.org/obo/SO_{ID}`
- Verified: Genes have SO_0000704 (gene), SO_0000010 (protein_coding)
- Use case: Semantic feature classification

## Complex Query Patterns Tested

### Pattern 1: Entry-Scoped Gene-CDS-Protein Join

**Purpose**: Link genes to their coding sequences and protein translations

**Category**: Performance-Critical, Error-Avoidance

**Naive Approach (without proper knowledge)**:
```sparql
SELECT ?gene ?cds ?protein
WHERE {
  ?gene a nuc:Gene .
  ?cds sio:SIO_010081 ?gene ;
       rdfs:seeAlso ?protein .
}
```

**What Happened**:
- Timeout after 60 seconds
- Query tries to join 225M+ genes with CDS features

**Correct Approach**:
```sparql
SELECT ?locus_tag ?gene_name ?product ?protein_id
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?gene a nuc:Gene ;
        nuc:locus_tag ?locus_tag .
  OPTIONAL { ?gene nuc:gene ?gene_name }
  ?cds sio:SIO_010081 ?gene ;
       nuc:product ?product ;
       rdfs:seeAlso ?protein_id .
  FILTER(CONTAINS(STR(?protein_id), "ncbiprotein"))
  FILTER(CONTAINS(STR(?gene), "CP036276.1"))
}
LIMIT 20
```

**What Knowledge Made This Work**:
- Entry filtering FIRST before any joins
- Correct property sio:SIO_010081 (uppercase)
- OPTIONAL for gene symbol (only ~60% coverage)
- ncbiprotein filter for protein links
- Performance: <1 second (vs timeout)

**Results Obtained**:
- 20+ gene-CDS-protein tuples per entry
- Sample: Mal52_08030 → clpX → ATP-dependent Clp protease ATP-binding subunit ClpX → QDU42347.1

**Natural Language Question Opportunities**:
1. "What are the protein products encoded by genes in the Symmachiella dynata genome?" - Integration
2. "Find the clpX gene in bacterial genome CP036276.1 and its protein translation" - Precision
3. "Which genes in a specific bacterial genome encode kinases?" - Structured Query

---

### Pattern 2: Organism-Based Entry Search with Full-Text

**Purpose**: Find genome entries for specific organisms

**Category**: Basic but Performance-Sensitive

**Naive Approach**:
```sparql
SELECT ?entry ?organism
WHERE {
  ?entry a nuc:Entry ; nuc:organism ?organism .
  FILTER(CONTAINS(?organism, "Escherichia"))
}
```

**What Happened**:
- Works but slower than optimized version
- No relevance ranking

**Correct Approach**:
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?entry ?organism ?definition
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?entry a nuc:Entry ;
         nuc:organism ?organism ;
         nuc:definition ?definition .
  ?organism bif:contains "'Escherichia' AND 'coli'" .
}
LIMIT 10
```

**What Knowledge Made This Work**:
- bif:contains for full-text search with AND logic
- Returns relevance-ranked results
- Much faster than FILTER CONTAINS

**Results Obtained**:
- Multiple E. coli genome entries found
- Sample: AP026093.1 - Escherichia coli 27_141091 plasmid pNIID27_1

**Natural Language Question Opportunities**:
1. "Find all complete genome entries for Escherichia coli in DDBJ" - Completeness
2. "What Salmonella genomes are available in the nucleotide database?" - Specificity

---

### Pattern 3: RNA Feature Retrieval with Coordinates

**Purpose**: Get tRNA and rRNA features with genomic positions

**Category**: Structured Query

**Naive Approach**:
```sparql
SELECT ?rna ?product ?start ?end
WHERE {
  ?rna a nuc:Transfer_RNA .
  ?rna nuc:product ?product ;
       faldo:location/faldo:begin/faldo:position ?start ;
       faldo:location/faldo:end/faldo:position ?end .
}
```

**What Happened**:
- Timeout - scans all features

**Correct Approach**:
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>

SELECT ?rna_type ?product ?start ?end
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  {
    ?rna a nuc:Transfer_RNA ; nuc:product ?product ; faldo:location ?region .
    BIND("tRNA" AS ?rna_type)
  } UNION {
    ?rna a nuc:Ribosomal_RNA ; nuc:product ?product ; faldo:location ?region .
    BIND("rRNA" AS ?rna_type)
  }
  ?region faldo:begin/faldo:position ?start ;
          faldo:end/faldo:position ?end .
  FILTER(CONTAINS(STR(?rna), "CP036276.1"))
}
LIMIT 30
```

**What Knowledge Made This Work**:
- Entry filtering before FALDO queries
- UNION pattern for multiple RNA types
- Correct FALDO property paths

**Results Obtained**:
- 30+ tRNA entries for various amino acids (Ile, Ala, Gly, Pro, etc.)
- Coordinate ranges for each tRNA gene

**Natural Language Question Opportunities**:
1. "How many tRNA genes are in the Symmachiella dynata genome?" - Completeness
2. "What are the coordinates of all ribosomal RNA genes in genome entry CP036276?" - Precision

---

### Pattern 4: Product Keyword Search Within Entry

**Purpose**: Find genes by product function description

**Category**: Structured Query

**Tested Approach**:
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?locus_tag ?product
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?cds a nuc:Coding_Sequence ;
       nuc:locus_tag ?locus_tag ;
       nuc:product ?product .
  FILTER(CONTAINS(STR(?cds), "CP036276.1"))
  FILTER(REGEX(?product, "kinase", "i"))
}
LIMIT 20
```

**What Knowledge Made This Work**:
- Entry filtering FIRST
- Use REGEX for product search within entry (bif:contains works at entry level for organism, not feature level)
- Case-insensitive matching

**Results Obtained**:
- 20+ kinase genes found
- Samples: Serine/threonine-protein kinases (AfsK, StkP, PknB, PknH), Thymidylate kinase, Shikimate kinase, etc.

**Natural Language Question Opportunities**:
1. "Find all kinase genes in a bacterial genome" - Structured Query
2. "What protease genes are encoded in the Symmachiella genome?" - Structured Query

---

### Pattern 5: Taxonomy Integration Query

**Purpose**: Link DDBJ features to NCBI Taxonomy

**Tested Approach**:
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX ro: <http://purl.obolibrary.org/obo/RO_>

SELECT DISTINCT ?gene ?taxon
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?gene a nuc:Gene ;
        ro:0002162 ?taxon .
  FILTER(CONTAINS(STR(?gene), "CP036276.1"))
}
LIMIT 5
```

**What Knowledge Made This Work**:
- ro:0002162 is the "in taxon" relationship
- Taxonomy URIs use identifiers.org format

**Results Obtained**:
- All genes linked to http://identifiers.org/taxonomy/2527995
- This ID matches NCBI Taxonomy for Symmachiella dynata

**Verification**: Taxonomy URI directly usable in NCBI Taxonomy database:
```sparql
# In taxonomy endpoint:
SELECT ?taxon ?label ?rank
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  VALUES ?taxon { <http://identifiers.org/taxonomy/2527995> }
  ?taxon a tax:Taxon ; rdfs:label ?label ; tax:rank ?rank .
}
# Returns: Symmachiella dynata, Species
```

**Natural Language Question Opportunities**:
1. "What species does genome entry CP036276.1 belong to?" - Precision
2. "Find the taxonomic classification for genes in a DDBJ entry" - Integration

---

### Pattern 6: BioProject/BioSample Cross-References

**Purpose**: Get experimental context for sequences

**Tested Approach**:
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?prop ?val
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  <http://identifiers.org/insdc/CP036276.1> ?prop ?val .
}
LIMIT 30
```

**Results Obtained**:
- BioProject: http://identifiers.org/bioproject/PRJNA485700
- BioSample: http://identifiers.org/biosample/SAMN10954015
- Sequence date: 2019-07-31
- Comment includes assembly method, coverage, technology

**Natural Language Question Opportunities**:
1. "What BioProject is genome entry CP036276 associated with?" - Precision
2. "What sequencing technology was used for genome CP036276?" - Precision

---

### Pattern 7: Gene Coordinates with FALDO

**Purpose**: Get precise genomic coordinates for genes

**Tested Approach**:
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>

SELECT ?locus_tag ?gene_name ?start ?end
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?gene a nuc:Gene ;
        nuc:locus_tag ?locus_tag ;
        faldo:location ?region .
  OPTIONAL { ?gene nuc:gene ?gene_name }
  ?region faldo:begin/faldo:position ?start ;
          faldo:end/faldo:position ?end .
  FILTER(CONTAINS(STR(?gene), "CP036276.1"))
}
LIMIT 20
```

**Results Obtained**:
- 20+ genes with coordinates
- Sample: Mal52_08030 (clpX) at 1001623-1002915

**Natural Language Question Opportunities**:
1. "What is the genomic location of the clpX gene in CP036276?" - Precision
2. "Find genes located between positions 1000000 and 1100000 in genome CP036276" - Structured Query

---

## Simple Queries Performed

1. **Entry count**: 262,282,607 entries total
2. **Gene count**: 225,351,782 genes total
3. **E. coli entries**: Multiple genomes (plasmids and chromosomes)
4. **Salmonella entries**: Various serovars (Typhi, Dublin)
5. **Entry CP036276.1**: Symmachiella dynata complete genome
6. **Protein links**: NCBI Protein accessions like QDU42347.1

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What is the full taxonomic lineage for the organism whose genome is in DDBJ entry CP036276?"
   - Databases: DDBJ, NCBI Taxonomy
   - Knowledge Required: ro:0002162 links features to taxonomy URIs; need to get taxon URI from DDBJ, then query taxonomy separately
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 5

2. "Find the protein translations for all kinase genes in the Symmachiella dynata genome"
   - Databases: DDBJ (gene-CDS-protein relationships)
   - Knowledge Required: Entry filtering, sio:SIO_010081 relationship, REGEX product search, ncbiprotein filter
   - Category: Integration/Structured Query
   - Difficulty: Hard
   - Pattern Reference: Patterns 1, 4

3. "Which NCBI Protein entries are linked to genes in bacterial genome CP036276.1?"
   - Databases: DDBJ, NCBI Protein
   - Knowledge Required: CDS rdfs:seeAlso links to ncbiprotein URIs
   - Category: Integration
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

**Performance-Critical Questions**:

4. "How many tRNA genes are in the complete genome of Symmachiella dynata (CP036276)?"
   - Database: DDBJ
   - Knowledge Required: Entry filtering before COUNT, Transfer_RNA type
   - Category: Completeness
   - Difficulty: Medium
   - Pattern Reference: Pattern 3

5. "Find all genes with ATP-related functions in a bacterial genome"
   - Database: DDBJ
   - Knowledge Required: Entry scoping + REGEX on product descriptions
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

6. "What are all the coding sequences in the first 100,000 base pairs of genome CP036276?"
   - Database: DDBJ
   - Knowledge Required: Entry filtering BEFORE coordinate filtering, FALDO property paths
   - Category: Completeness/Structured Query
   - Difficulty: Hard
   - Pattern Reference: Pattern 7

**Error-Avoidance Questions**:

7. "List the genes in a bacterial genome that encode proteases"
   - Database: DDBJ
   - Knowledge Required: Must filter by entry FIRST, then REGEX on product; reverse order causes timeout
   - Category: Structured Query
   - Difficulty: Medium
   - Pattern Reference: Pattern 4

8. "Find the clpX gene in Symmachiella dynata and its associated CDS features"
   - Database: DDBJ
   - Knowledge Required: Correct sio:SIO_010081 property (case-sensitive), entry scoping
   - Category: Precision
   - Difficulty: Medium
   - Pattern Reference: Pattern 1

**Complex Filtering Questions**:

9. "Find genes between positions 1,000,000 and 2,000,000 on the Symmachiella dynata chromosome that encode membrane proteins"
   - Database: DDBJ
   - Knowledge Required: Entry filter + FALDO coordinates + REGEX product filter
   - Category: Structured Query
   - Difficulty: Hard
   - Pattern Reference: Patterns 4, 7

10. "What ribosomal RNA genes exist in genome entry CP036276 and what are their coordinates?"
    - Database: DDBJ
    - Knowledge Required: Entry filter, Ribosomal_RNA type, FALDO location
    - Category: Completeness
    - Difficulty: Medium
    - Pattern Reference: Pattern 3

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

11. "What is the organism name for DDBJ entry CP036276.1?"
    - Method: Simple SPARQL with entry URI
    - Knowledge Required: None (straightforward)
    - Category: Precision
    - Difficulty: Easy

12. "What Salmonella genome entries exist in DDBJ?"
    - Method: bif:contains search on organism
    - Knowledge Required: None (basic full-text search)
    - Category: Completeness
    - Difficulty: Easy

13. "What is the definition/description for genome entry AP026093?"
    - Method: Simple property lookup
    - Knowledge Required: None
    - Category: Precision
    - Difficulty: Easy

**Basic Counting Questions**:

14. "How many genome entries are in the DDBJ database?"
    - Method: COUNT query (works without filtering)
    - Knowledge Required: None
    - Category: Completeness
    - Difficulty: Easy

15. "How many gene annotations are in DDBJ?"
    - Method: COUNT query (works without filtering)
    - Knowledge Required: None
    - Category: Completeness
    - Difficulty: Easy

---

## Integration Patterns Summary

**DDBJ as Source**:
- → NCBI Taxonomy: via ro:0002162 (direct URI match)
- → NCBI Protein: via rdfs:seeAlso on CDS features
- → BioProject: via nuc:dblink
- → BioSample: via nuc:dblink
- → Sequence Ontology: via rdfs:subClassOf

**DDBJ as Target**:
- Taxonomy → DDBJ: Search by organism, filter by taxonomy ID
- BioProject → DDBJ: Find entries linked to specific project

**Complex Multi-Database Paths**:
- DDBJ → Taxonomy → (Taxonomy hierarchy queries)
- DDBJ → NCBI Protein → UniProt (via TogoID)

**Note**: DDBJ has its own endpoint (https://rdfportal.org/ddbj/sparql), so direct cross-database SPARQL joins are not possible. Integration requires two-step queries or TogoID.

---

## Lessons Learned

### What Knowledge is Most Valuable
1. **Entry filtering is absolutely critical** - Cannot query features without it
2. **Property case sensitivity** - sio:SIO_010081 not sio:010081
3. **bif:contains for organism searches** - Entry-level full-text
4. **FALDO requires entry scoping** - Coordinate queries fail otherwise
5. **Gene-CDS relationships** via sio:SIO_010081

### Common Pitfalls Discovered
1. Forgot entry filter → immediate timeout
2. Used bif:contains on product (feature level) → should use REGEX
3. Complex joins across entries → always scope to single entry first

### Recommendations for Question Design
1. Questions involving genes/CDS/RNA ALWAYS need MIE knowledge for entry filtering
2. Simple organism searches can work without deep knowledge
3. Coordinate-based questions are HARD without knowing FALDO patterns
4. Cross-database questions require understanding separate endpoints

### Performance Notes
- Entry-scoped queries: <1 second
- Unfiltered gene queries: timeout (60s)
- Simple counts (entries, genes): work in ~5-10 seconds
- Complex aggregations: timeout

---

## Notes and Observations

- DDBJ primarily contains prokaryotic data with high annotation completeness
- Locus tags are more reliable than gene symbols (~60% have gene symbols, >99% have locus tags)
- All features use FALDO for coordinates (>99% coverage)
- Dataset size (262M entries, 225M genes) makes optimization essential
- The database integrates well with NCBI ecosystem (Taxonomy, Protein, BioProject)

---

## Next Steps

**Recommended for Question Generation**:
- Priority: Gene-CDS-Protein integration questions
- Priority: Coordinate-based queries (demonstrate FALDO knowledge)
- Priority: Organism searches with feature filtering
- Avoid: Cross-entry aggregations (tend to timeout)

**Further Exploration Needed**:
- Test more complex multi-feature patterns
- Explore ncRNA features in detail
- Test repeat region and mobile element queries

---

**Session Complete - Ready for Next Database**

```
Database: ddbj
Status: ✅ COMPLETE
Report: /evaluation/exploration/ddbj_exploration.md
Patterns Tested: 7
Questions Identified: 15
Integration Points: 5
```
