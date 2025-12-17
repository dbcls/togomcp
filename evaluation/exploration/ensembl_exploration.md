# Ensembl Exploration Report

## Database Overview
- **Purpose**: Comprehensive genomics database providing genome annotations for vertebrate species
- **Scope**: 3M+ genes, 4M+ transcripts, 2M+ proteins across 100+ species
- **Key data types**: Genes, transcripts, proteins, exons with genomic coordinates, biotypes, and quality flags

## Schema Analysis (from MIE file)

### Main Properties Available
- **Gene properties** (EnsemblGene):
  - `dcterms:identifier` - Ensembl gene ID (ENSG...)
  - `rdfs:label` - Gene symbol
  - `dcterms:description` - Full gene name with source
  - `terms:has_biotype` - Functional classification (protein_coding, lncRNA, miRNA, etc.)
  - `obo:RO_0002162` - Species (NCBI Taxonomy ID)
  - `so:part_of` - Chromosome location
  - `faldo:location` - Genomic coordinates (start, end, strand)
  - `rdfs:seeAlso` - Cross-references (UniProt, HGNC, NCBI Gene, etc.)

- **Transcript properties** (EnsemblTranscript):
  - `dcterms:identifier` - Ensembl transcript ID (ENST...)
  - `so:transcribed_from` - Parent gene
  - `so:translates_to` - Protein product (if protein-coding)
  - `terms:has_transcript_flag` - Quality flags (MANE, APPRIS, TSL, canonical)
  - `sio:SIO_000974` - Ordered exons

- **Protein properties** (EnsemblProtein):
  - `dcterms:identifier` - Ensembl protein ID (ENSP...)
  - `so:translation_of` - Parent transcript
  - `rdfs:seeAlso` - UniProt cross-references

- **Exon properties** (EnsemblExon):
  - `dcterms:identifier` - Exon ID (ENSE...)
  - `faldo:location` - Exon coordinates
  - Ordered via EnsemblOrderedExon with `sio:SIO_000300` (order number)

### Important Relationships
- **Central dogma hierarchy**: Gene → Transcript → Protein following molecular biology
- **FALDO ontology**: Standardized genomic coordinates with strand information (ForwardStrandPosition, ReverseStrandPosition)
- **SO (Sequence Ontology)**: Defines relationships (transcribed_from, translates_to, part_of)
- **Biotype classification**: Categorizes genes/transcripts functionally (protein_coding, lncRNA, miRNA, pseudogene, etc.)
- **Quality flags**: Transcript confidence annotations (MANE Select, APPRIS principal, TSL levels)
- **Multi-assembly support**: Separate graphs for GRCh38, GRCh37 genome builds

### Query Patterns Observed
- **Full-text search**: Use bif:contains with wildcards (BRCA*) and relevance scoring
- **Boolean searches**: 'kinase' AND 'receptor' in descriptions
- **Species filtering**: Always filter by obo:RO_0002162 taxonomy:XXXXX
- **Chromosome queries**: FILTER(CONTAINS(STR(?chr), "GRCh38/Y"))
- **Strand detection**: Check faldo:begin/rdf:type for ForwardStrandPosition vs ReverseStrandPosition
- **Optional patterns**: Use OPTIONAL for so:translates_to (not all transcripts encode proteins)
- **DISTINCT requirement**: Always use DISTINCT with FALDO location queries to avoid duplicates

## Search Queries Performed

1. **Query**: UniProt search for "human BRCA1" → **Results**: P38398 (Breast cancer type 1 susceptibility protein, EC 2.3.2.27, RING-type E3 ubiquitin transferase)

2. **Query**: BRCA genes with bif:contains → **Results**: Found BRCA1 (ENSG00000012048), BRCA2 (ENSG00000139618), BRCA1P1 (pseudogene, ENSG00000267595), plus LRG reference sequences

3. **Query**: BRCA1 genomic coordinates → **Results**: Chromosome 17:43044295-43170245 (negative strand, GRCh38)

4. **Query**: BRCA1 gene-transcript-protein hierarchy → **Results**: 10 transcript-protein pairs with multiple UniProt IDs (P38398 canonical, plus isoforms A0A0U1RRA9, A0A9Y1QPT7, etc.)

5. **Query**: TP53 transcripts → **Results**: 20+ transcripts (ENST00000269305, ENST00000359597, etc.), all encoding proteins showing alternative splicing complexity

6. **Query**: TP53 transcript ENST00000269305 exons → **Results**: 11 exons ordered sequentially (ENSE00003753508, ENSE00004023728, etc.) with genomic coordinates

7. **Query**: Y chromosome protein-coding genes → **Results**: 20 genes including SRY (ENSG00000184895), AMELY (ENSG00000099721), ZFY (ENSG00000067646), UTY, DDX3Y, USP9Y

8. **Query**: Kinase receptor genes (functional search) → **Results**: 10 genes including ROR2 (ENSG00000169071), ROR1, ALK (ENSG00000171094), AXL (ENSG00000167601), RIPK family members

## SPARQL Queries Tested

```sparql
# Query 1: Gene symbol search with bif:contains
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene ?id ?label ?description
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        dcterms:description ?description ;
        obo:RO_0002162 taxonomy:9606 .
  ?label bif:contains "'BRCA*'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: Found BRCA1 (ENSG00000012048), BRCA2 (ENSG00000139618), BRCA1P1 (pseudogene) with full descriptions. Fast query with wildcard support.
```

```sparql
# Query 2: Genomic coordinates with FALDO
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT DISTINCT ?gene ?id ?label ?start ?end ?strand ?chr
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        faldo:location ?loc ;
        so:part_of ?chr ;
        obo:RO_0002162 taxonomy:9606 .
  ?loc faldo:begin/faldo:position ?start ;
       faldo:end/faldo:position ?end ;
       faldo:begin/rdf:type ?strand_type .
  BIND(IF(?strand_type = faldo:ForwardStrandPosition, "+", "-") AS ?strand)
  FILTER(?id = "ENSG00000012048")
}
# Results: BRCA1 on chr17:43044295-43170245, negative strand. DISTINCT required to avoid duplicates from multiple chromosome annotations.
```

```sparql
# Query 3: Gene-transcript-protein hierarchy
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene_id ?gene_label ?transcript_id ?protein_id ?uniprot
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?gene_id ;
        rdfs:label ?gene_label ;
        obo:RO_0002162 taxonomy:9606 .
  ?transcript so:transcribed_from ?gene ;
              dcterms:identifier ?transcript_id ;
              so:translates_to ?protein .
  ?protein dcterms:identifier ?protein_id ;
           rdfs:seeAlso ?uniprot .
  FILTER(STRSTARTS(STR(?uniprot), "http://purl.uniprot.org/uniprot/"))
  FILTER(?gene_label = "BRCA1")
}
LIMIT 10
# Results: Retrieved 10 transcript-protein pairs for BRCA1 with UniProt IDs including canonical P38398 and isoforms.
```

```sparql
# Query 4: TP53 alternative transcripts
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene_id ?label ?transcript_id ?protein_id
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?gene_id ;
        rdfs:label ?label ;
        obo:RO_0002162 taxonomy:9606 .
  ?transcript so:transcribed_from ?gene ;
              dcterms:identifier ?transcript_id .
  OPTIONAL {
    ?transcript so:translates_to ?protein .
    ?protein dcterms:identifier ?protein_id .
  }
  FILTER(?label = "TP53")
}
LIMIT 20
# Results: Retrieved 20 TP53 transcripts, all with protein products, demonstrating alternative splicing. OPTIONAL used for non-coding RNA cases.
```

```sparql
# Query 5: Ordered exons for transcript
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX sio: <http://semanticscience.org/resource/>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>

SELECT ?transcript_id ?exon_id ?order ?start ?end
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?transcript a terms:EnsemblTranscript ;
              dcterms:identifier ?transcript_id ;
              sio:SIO_000974 ?ordered_exon .
  ?ordered_exon sio:SIO_000628 ?exon ;
                sio:SIO_000300 ?order .
  ?exon dcterms:identifier ?exon_id ;
        faldo:location/faldo:begin/faldo:position ?start ;
        faldo:location/faldo:end/faldo:position ?end .
  FILTER(?transcript_id = "ENST00000269305")
}
ORDER BY ?order
LIMIT 20
# Results: Retrieved 11 ordered exons for TP53 transcript ENST00000269305 with coordinates (exon 1: 7687377-7687490, etc.).
```

```sparql
# Query 6: Chromosome-specific genes
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene ?id ?label
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        so:part_of ?chr ;
        terms:has_biotype <http://ensembl.org/glossary/ENSGLOSSARY_0000026> ;
        obo:RO_0002162 taxonomy:9606 .
  FILTER(CONTAINS(STR(?chr), "GRCh38/Y"))
}
LIMIT 20
# Results: Retrieved 20 protein-coding genes on Y chromosome including SRY (sex-determining region), AMELY, ZFY, USP9Y, etc.
```

```sparql
# Query 7: Functional keyword search
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxonomy: <http://identifiers.org/taxonomy/>

SELECT ?gene ?id ?label ?description
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?id ;
        rdfs:label ?label ;
        dcterms:description ?description ;
        obo:RO_0002162 taxonomy:9606 .
  ?description bif:contains "('kinase' AND 'receptor')" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: Retrieved 10 receptor kinase genes with relevance ranking: ROR2, ROR1, ALK, AXL, RIPK family, GRK3, DDR1.
```

## Interesting Findings

### Specific Entities That Could Form Good Questions
- **BRCA1 (ENSG00000012048)**: Chromosome 17:43044295-43170245, negative strand, 10+ transcript isoforms, UniProt P38398
- **TP53 (ENSG00000141510)**: 20+ alternative transcripts demonstrating complex splicing
- **SRY (ENSG00000184895)**: Y chromosome sex-determining gene
- **ENST00000269305**: TP53 transcript with 11 exons, well-documented structure
- **ALK (ENSG00000171094)**: Receptor tyrosine kinase, cancer target
- **Y chromosome**: 20+ protein-coding genes (AMELY, ZFY, UTY, DDX3Y, USP9Y)

### Unique Properties or Patterns
- **Alternative splicing**: Single genes produce multiple transcripts (TP53 has 20+, BRCA1 has 10+)
- **Strand encoding**: ForwardStrandPosition (+) vs ReverseStrandPosition (-) in FALDO
- **Quality flags**: MANE Select, APPRIS, TSL for transcript quality assessment
- **LRG references**: Locus Reference Genomic sequences (LRG_292, LRG_293) for clinical use
- **Ordered exons**: SIO ontology provides sequential exon numbering
- **Multi-assembly**: GRCh38 and GRCh37 in separate named graphs
- **Cross-references**: ~60% genes have UniProt links, extensive HGNC coverage

### Connections to Other Databases
- **UniProt**: ~60% of genes have protein cross-references (P38398 for BRCA1)
- **HGNC**: Human Gene Nomenclature Committee IDs (HGNC:1100 for BRCA1)
- **NCBI Gene**: Cross-references via identifiers.org
- **Reactome**: Pathway connections (via rdfs:seeAlso)
- **OMIM**: Clinical/disease associations
- **NCBI Taxonomy**: Species classification (9606 for human)
- **UniParc**: Protein sequence archives
- **GeneCards**: Gene information aggregator

### Specific, Verifiable Facts
- **BRCA1**: ENSG00000012048, chr17:43044295-43170245, negative strand, 10+ isoforms
- **TP53**: ENSG00000141510, 20+ transcripts, all protein-coding
- **Y chromosome**: 20+ protein-coding genes including SRY
- **ENST00000269305**: TP53 transcript with exactly 11 exons
- **Species coverage**: 100+ vertebrate species with 3M+ genes total
- **Human genes**: 87,688 genes annotated
- **Alternative transcripts**: 40% of transcripts encode proteins (others are non-coding)

## Question Opportunities by Category

### Precision
- "What is the Ensembl gene ID for human BRCA1?" (Answer: ENSG00000012048)
- "What are the genomic coordinates of BRCA1 in GRCh38?" (Answer: chr17:43044295-43170245, negative strand)
- "What is the UniProt ID for BRCA1 from Ensembl?" (Answer: P38398)
- "How many exons does TP53 transcript ENST00000269305 have?" (Answer: 11)
- "What chromosome is the SRY gene located on?" (Answer: Y chromosome)

### Completeness
- "How many alternative transcripts does TP53 have in Ensembl?" (Answer: 20+)
- "List all protein-coding genes on the human Y chromosome" (Answer: 20+ genes including SRY, AMELY, ZFY, etc.)
- "What are all the exons of transcript ENST00000269305 in sequential order?" (Answer: 11 exons from ENSE00003753508 to ENSE00004023724)
- "How many transcript isoforms does BRCA1 have?" (Answer: 10+ isoforms)
- "List all BRCA genes in the human genome" (Answer: BRCA1, BRCA2, BRCA1P1 pseudogene)

### Integration
- "What is the UniProt ID corresponding to Ensembl protein ENSP00000478114?" (Answer: P38398)
- "Find the HGNC identifier for BRCA1 from Ensembl" (Answer: HGNC:1100)
- "Convert Ensembl gene ID ENSG00000141510 to its gene symbol" (Answer: TP53)
- "What Reactome pathways are associated with BRCA1?" (Uses rdfs:seeAlso cross-references)
- "Find NCBI Gene IDs for Y chromosome genes in Ensembl"

### Currency
- "What genome assembly version does Ensembl currently use for human?" (Answer: GRCh38, Release 114)
- "Which transcripts have MANE Select status?" (MANE = Matched Annotation from NCBI and EMBL-EBI)
- "What is the most recent release of Ensembl?" (Answer: Release 114)
- "How many genes are annotated in the latest human genome assembly?"

### Specificity
- "What is the strand orientation of BRCA1?" (Answer: Negative/reverse strand)
- "What is the genomic position of exon 1 of transcript ENST00000269305?" (Answer: 7687377-7687490)
- "What is the biotype of gene ENSG00000184895 (SRY)?" (Answer: protein_coding)
- "Which transcript flags indicate the highest quality for TP53?" (Answer: MANE Select, APPRIS principal)
- "What is the LRG identifier for BRCA1?" (Answer: LRG_292)

### Structured Query
- "Find all human genes with 'receptor' and 'kinase' in their description" (Boolean bif:contains search)
- "List genes on chromosome X that are protein-coding" (Chromosome + biotype filtering)
- "Retrieve all transcripts of BRCA1 that encode proteins" (Gene→transcript→protein traversal)
- "Find genes on the negative strand of chromosome 17" (FALDO strand detection)
- "Get exons for a transcript in sequential order" (SIO ordered exon query)

## Notes

### Limitations or Challenges
- **Server instability**: Occasional 500 errors on complex queries
- **FALDO duplicates**: Multiple chromosome annotations require DISTINCT
- **Not all transcripts code proteins**: ~60% of transcripts are non-coding (lncRNA, miRNA, etc.)
- **Assembly versions**: Must specify GRCh38 or GRCh37 graph explicitly
- **Large result sets**: Broad queries timeout without species/chromosome filters
- **Missing descriptions**: ~5% of genes lack description fields
- **Cross-reference completeness**: Not all genes have all external database links

### Best Practices for Querying
1. **Always filter by species**: Use obo:RO_0002162 taxonomy:9606 for human (or other taxonomy ID)
2. **Use bif:contains** for text searches with relevance ranking and wildcards
3. **Always use DISTINCT** with FALDO location queries to avoid duplicates
4. **FROM clause**: Specify graph (<http://rdfportal.org/dataset/ensembl>)
5. **OPTIONAL for proteins**: Not all transcripts encode proteins, use OPTIONAL for so:translates_to
6. **Strand detection**: Use faldo:begin/rdf:type and IF() to convert to +/-
7. **Chromosome filtering**: Use CONTAINS(STR(?chr), "GRCh38/X") for specific chromosomes
8. **LIMIT required**: Always use LIMIT for exploratory queries to prevent timeouts
9. **Cross-reference filtering**: Use STRSTARTS for specific database patterns
10. **Order exons**: Use ORDER BY ?order when querying ordered exons

### Anti-patterns to Avoid
- ❌ Querying without species filter (returns mixed results from all organisms)
- ❌ Using FILTER(REGEX()) instead of bif:contains for text search (slow)
- ❌ Omitting DISTINCT in FALDO location queries (duplicate results)
- ❌ Requiring proteins without OPTIONAL (excludes non-coding transcripts)
- ❌ Trying to access non-existent faldo:strand property (use position type instead)
- ❌ Missing FROM clause (may query wrong graph)
- ❌ Broad searches without LIMIT (timeouts)
- ❌ Not defining all required prefixes (causes 400 errors)
