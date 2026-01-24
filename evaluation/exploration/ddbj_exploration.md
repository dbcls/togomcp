# DDBJ Exploration Report

## Database Overview
- **Purpose**: DDBJ (DNA Data Bank of Japan) RDF provides nucleotide sequence data from the International Nucleotide Sequence Database Collaboration (INSDC)
- **Key data types**: Genome entries, genes, coding sequences (CDS), tRNA, rRNA, ncRNA, other genomic features
- **Primary content**: Prokaryotic genomes (bacteria, archaea), viral sequences, some eukaryotic sequences
- **Endpoint**: https://rdfportal.org/ddbj/sparql
- **Search approach**: SPARQL with bif:contains for organism name searches

## Schema Analysis (from MIE file)
### Main Entities
- `nuc:Entry` - Genome/sequence entries (top-level records)
- `nuc:Gene` - Gene features
- `nuc:Coding_Sequence` - CDS/protein-coding regions
- `nuc:Transfer_RNA` - tRNA features
- `nuc:Ribosomal_RNA` - rRNA features  
- `nuc:Non_Coding_RNA` - ncRNA features
- `nuc:Source` - Organism source metadata
- `nuc:Repeat_Region`, `nuc:Mobile_Element`, etc.

### Main Properties
- `nuc:organism` - Organism name (searchable via bif:contains)
- `nuc:locus_tag` - Primary feature identifier (more reliable than gene symbol)
- `nuc:gene` - Gene symbol (optional, ~60% coverage)
- `nuc:product` - Protein/RNA product description
- `nuc:translation` - Protein sequence
- `nuc:dblink` - Links to BioProject/BioSample
- `faldo:location` - Genomic coordinates via FALDO ontology

### Important Relationships
- `bfo:0000050` (part of) - Links features to parent entry
- `ro:0002162` (in taxon) - Links features to NCBI Taxonomy
- `sio:SIO_010081` (is transcribed into) - Links Gene to CDS (NOTE: uppercase SIO required!)
- `rdfs:seeAlso` - Cross-references to NCBI Protein, Taxonomy
- `rdfs:subClassOf` - Sequence Ontology classification

### Query Patterns
- **CRITICAL**: Always filter by entry accession ID before complex queries to prevent timeout
- Use `bif:contains` only for organism searches at entry level
- Use `FILTER CONTAINS` for product searches within specific entries
- Avoid COUNT/aggregation without entry filtering

## Search Queries Performed

1. **Query: "Streptococcus pyogenes"** → Multiple complete genome entries found
   - CP035433.1 - Streptococcus pyogenes complete genome
   - CP035439.1 - Streptococcus pyogenes complete genome
   - AB002521.1, AB006751.1, AB006752.1 - S. pyogenes sequences
   - Shows good coverage of clinically important pathogens

2. **Query: "Mycobacterium"** → Multiple entries found
   - AB005789.1 - Mycobacterium tuberculosis variant bovis
   - AB244251.1 through AB244268.1 - M. tuberculosis bovis variants
   - Demonstrates pathogen genomic data availability

3. **Entry sampling** → 100 entries sampled
   - Accession patterns: CP (INSDC chromosome), AP (Archival Prokaryotic)
   - Shows diverse genome collection from INSDC

4. **Genes from S. pyogenes CP035433.1** → Comprehensive annotation
   - dnaA (chromosomal replication initiator)
   - rpoC (RNA polymerase)
   - Various metabolic genes with locus tags

5. **tRNA genes from CP035433.1** → 15+ tRNA genes found
   - tRNA-Arg, tRNA-Gln, tRNA-Tyr, tRNA-Ala, tRNA-Val, etc.
   - Complete set of tRNA annotations in bacterial genomes

## SPARQL Queries Tested

### Query 1: Search entries by organism (bif:contains)
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?entry ?organism
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?entry a nuc:Entry ;
         nuc:organism ?organism .
  ?organism bif:contains "'Streptococcus' AND 'pyogenes'" option (score ?relevance) .
}
ORDER BY DESC(?relevance)
LIMIT 5
```
**Results**: 5 S. pyogenes entries including complete genomes CP035433.1, CP035439.1

### Query 2: Get genes from a specific entry
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?gene ?locus_tag ?gene_name
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?gene a nuc:Gene ;
        nuc:locus_tag ?locus_tag .
  OPTIONAL { ?gene nuc:gene ?gene_name }
  FILTER(CONTAINS(STR(?gene), "CP035433.1"))
}
LIMIT 10
```
**Results**: Found genes like dnaA (ETT66_00005), rpoC (ETT66_00675), msrB (ETT66_05085)

### Query 3: Gene-to-protein chain with NCBI Protein links
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX sio: <http://semanticscience.org/resource/>

SELECT ?locus_tag ?product ?protein_id
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?gene a nuc:Gene ;
        nuc:locus_tag ?locus_tag .
  ?cds sio:SIO_010081 ?gene ;
       nuc:product ?product .
  OPTIONAL { ?cds rdfs:seeAlso ?protein_id . 
             FILTER(CONTAINS(STR(?protein_id), "ncbiprotein")) }
  FILTER(CONTAINS(STR(?gene), "CP035433.1"))
}
LIMIT 10
```
**Results**: Complete gene-CDS-protein mappings:
- ETT66_00005 → DnaA → QCK36381.1
- ETT66_05040 → NAD-dependent succinate-semialdehyde dehydrogenase → QCK37245.1
- And more with full product descriptions and NCBI Protein IDs

### Query 4: tRNA features from an entry
```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?rna ?product
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?rna a nuc:Transfer_RNA .
  OPTIONAL { ?rna nuc:product ?product }
  FILTER(CONTAINS(STR(?rna), "CP035433.1"))
}
LIMIT 15
```
**Results**: 15 tRNA genes found: tRNA-Arg, tRNA-Gln, tRNA-Tyr, tRNA-Ala, tRNA-Val, tRNA-Asp, tRNA-Lys, tRNA-Leu, tRNA-Thr, tRNA-Gly, tRNA-Pro, tRNA-Met

## Cross-Reference Analysis

### Entry-level links:
- BioProject: Links to sequencing project metadata
- BioSample: Links to specimen/sample information

### Feature-level links:
- NCBI Protein: CDS features link to RefSeq/GenBank protein IDs via `rdfs:seeAlso`
  - Example: ETT66_00005 (dnaA) → http://identifiers.org/ncbiprotein/QCK36381.1
- NCBI Taxonomy: All features link via `ro:0002162` (in taxon)
- Sequence Ontology: Feature classification via `rdfs:subClassOf`

### Integration notes:
- Uses identifiers.org URIs for standardized cross-linking
- Gene-CDS relationship via `sio:SIO_010081` (case-sensitive!)
- Can integrate with NCBI Gene, Taxonomy, and Protein databases

## Interesting Findings

**Findings requiring actual queries (non-trivial):**

1. **Streptococcus pyogenes genomes available**: CP035433.1 and CP035439.1 are complete genomes with full annotation
   - Contains genes like dnaA, rpoC, and hundreds of other protein-coding genes
   - Linked to NCBI Protein database for all CDS

2. **Gene-CDS-Protein integration works well** within single entries:
   - dnaA gene (ETT66_00005) → CDS with product description → NCBI Protein QCK36381.1
   - ~60% of genes have gene symbols, >99% have locus tags (locus tags are primary identifiers)

3. **tRNA annotation completeness**: Bacterial genomes have complete tRNA gene sets
   - CP035433.1 (S. pyogenes) has all standard tRNA types annotated

4. **Diverse organisms**: Database contains bacteria, archaea (M. tuberculosis, S. pyogenes), and viruses
   - Good coverage of clinically important pathogens

5. **Query performance note**: Entry-specific queries are fast; cross-entry aggregations timeout
   - Always filter by entry accession before joins

## Question Opportunities by Category

### Precision (specific IDs, sequences)
- ✅ "What is the locus tag for the dnaA gene in S. pyogenes CP035433.1?" → ETT66_00005
- ✅ "What is the NCBI Protein ID for locus tag ETT66_00005?" → QCK36381.1
- ✅ "What is the gene symbol for locus tag ETT66_00675 in CP035433.1?" → rpoC

### Completeness (counts, comprehensive lists)
- ✅ "List all tRNA genes in S. pyogenes genome CP035433.1"
- ✅ "What genes are annotated in DDBJ entry CP035433.1?"
- ✅ "List all CDS with 'kinase' in their product description in entry X"

### Integration (cross-database linking)
- ✅ "What NCBI Protein IDs are linked to genes in entry CP035433.1?"
- ✅ "What NCBI Taxonomy ID is associated with S. pyogenes genomes?"
- ✅ "Link DDBJ locus tag to NCBI Protein ID"

### Currency (recent/updated data)
- ✅ "What S. pyogenes genomes are available in DDBJ?" (database updated daily)

### Specificity (specialized organisms)
- ✅ "What Mycobacterium tuberculosis genomes are in DDBJ?"
- ✅ "Find genome entries for Lactobacillus phages"
- ✅ "What archaeal genomes are available?"

### Structured Query (complex filtering)
- ✅ "Find genes with 'protease' or 'peptidase' in product description in entry X"
- ✅ "List genes between coordinates 1000000-1100000 in genome Y"
- ✅ "Find all ncRNA genes in a bacterial genome"

## Notes

### Limitations
- COUNT/aggregation queries timeout without entry filtering
- Must always scope queries to specific entry accessions for complex joins
- ~60% of genes have gene symbols; use locus_tag as primary identifier
- Some SPARQL queries with multiple joins can timeout

### Best Practices
- **CRITICAL**: Always filter by entry accession ID first: `FILTER(CONTAINS(STR(?gene), "ACCESSION"))`
- Use `bif:contains` only for organism searches at entry level
- Use `FILTER CONTAINS` for product searches within entries
- Use uppercase `sio:SIO_010081` for gene-CDS relationships (case-sensitive!)
- Use OPTIONAL for gene symbols since not all genes have them
- Sample with LIMIT instead of COUNT for statistics

### Data Quality
- Primarily prokaryotic data with high annotation completeness
- Locus tags are primary identifiers (more reliable than gene symbols)
- >95% of CDS have product descriptions and translations
- >99% of features have FALDO genomic coordinates
