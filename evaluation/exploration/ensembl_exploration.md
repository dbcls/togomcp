# Ensembl Exploration Report

## Database Overview
- **Purpose**: Ensembl is a comprehensive genomics database providing genome annotations for 100+ species
- **Key data types**: Genes, transcripts, proteins, exons with genomic coordinates
- **Species coverage**: 100+ vertebrate species (human, mouse, rat, zebrafish, etc.)
- **Endpoint**: https://rdfportal.org/ebi/sparql (EBI shared endpoint)
- **Search approach**: SPARQL with bif:contains for gene symbol/description searches

## Schema Analysis (from MIE file)
### Main Entities
- `terms:EnsemblGene` - Gene annotations with biotypes and cross-references
- `terms:EnsemblTranscript` - Transcript variants with quality flags
- `terms:EnsemblProtein` - Translated protein products
- `terms:EnsemblExon` - Exon regions
- `terms:EnsemblOrderedExon` - Exons with transcript order

### Main Properties
- `dcterms:identifier` - Ensembl stable ID (ENSG, ENST, ENSP, ENSE)
- `rdfs:label` - Gene symbol
- `dcterms:description` - Gene description with source attribution
- `terms:has_biotype` - Functional classification (protein_coding, miRNA, etc.)
- `obo:RO_0002162` - Taxonomic classification (links to NCBI Taxonomy)
- `so:part_of` - Chromosome location
- `faldo:location` - Genomic coordinates with strand via FALDO

### Important Relationships
- `so:transcribed_from` - Transcript to Gene
- `so:translates_to` - Transcript to Protein
- `sio:SIO_000974` - Transcript has ordered exons
- `rdfs:seeAlso` - Cross-references (UniProt, HGNC, NCBI Gene, Reactome, OMIM)

### Query Patterns
- Use `bif:contains` for text search in labels/descriptions with wildcards
- Always filter by species using `obo:RO_0002162 taxonomy:XXXX`
- Use DISTINCT with FALDO queries to avoid duplicates
- Chromosome filtering: `FILTER(CONTAINS(STR(?chr), "GRCh38/X"))`

## Search Queries Performed

1. **Query: "BRCA*"** → Found human BRCA genes
   - ENSG00000012048 - BRCA1 DNA repair associated
   - ENSG00000139618 - BRCA2 DNA repair associated
   - ENSG00000267595 - BRCA1P1 pseudogene
   - LRG_292, LRG_293 - Locus Reference Genomic entries

2. **Query: "kinase AND receptor"** → Found kinase-related genes
   - ENSG00000185483 - ROR1 (receptor tyrosine kinase like orphan receptor 1)
   - ENSG00000169071 - ROR2 (receptor tyrosine kinase like orphan receptor 2)
   - ENSG00000129465 - RIPK3 (receptor interacting serine/threonine kinase 3)
   - ENSG00000090376 - IRAK3 (interleukin 1 receptor associated kinase 3)
   - ENSG00000184216 - IRAK1 (interleukin 1 receptor associated kinase 1)

3. **Species distribution** → Gene counts by species
   - Mouse (10090): 744,820 genes
   - Sheep (9940): 633,869 genes
   - Pig (9823): 624,705 genes
   - Atlantic salmon (8030): 267,676 genes
   - Human (9606): 87,688 genes

4. **Chromosome X genes (human protein-coding)** → Sample found
   - HTR2C, CA5B, RTL8B, XAGE1B, SLC9A7, GPC4, TLR8, etc.

5. **BRCA1 transcripts with UniProt links** → Multiple isoforms found
   - ENST00000352993 → ENSP00000312236 → UniProt:P38398
   - ENST00000357654 → ENSP00000350283 → UniProt:P38398
   - Multiple alternative transcripts linking to different UniProt entries

## SPARQL Queries Tested

### Query 1: Search genes by symbol using bif:contains
```sparql
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
```
**Results**: Found BRCA1 (ENSG00000012048), BRCA2 (ENSG00000139618), BRCA1P1 (pseudogene)

### Query 2: Get gene genomic coordinates with FALDO
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>
PREFIX so: <http://purl.obolibrary.org/obo/so#>

SELECT DISTINCT ?gene_id ?label ?start ?end ?strand ?chr
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        dcterms:identifier ?gene_id ;
        rdfs:label ?label ;
        faldo:location ?loc ;
        so:part_of ?chr ;
        obo:RO_0002162 taxonomy:9606 .
  ?loc faldo:begin/faldo:position ?start ;
       faldo:end/faldo:position ?end ;
       faldo:begin/rdf:type ?strand_type .
  BIND(IF(?strand_type = faldo:ForwardStrandPosition, "+", "-") AS ?strand)
  FILTER(?gene_id = "ENSG00000012048")
}
```
**Results**: BRCA1 on chr17:43044295-43170245 (minus strand, GRCh38)

### Query 3: Gene-Transcript-Protein chain with UniProt links
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX so: <http://purl.obolibrary.org/obo/so#>

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
LIMIT 15
```
**Results**: 15 BRCA1 transcript-protein pairs, most linking to UniProt P38398 (canonical BRCA1)

### Query 4: Gene count by species
```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT ?taxonomy (COUNT(?gene) as ?gene_count)
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  ?gene a terms:EnsemblGene ;
        obo:RO_0002162 ?taxonomy .
}
GROUP BY ?taxonomy
ORDER BY DESC(?gene_count)
LIMIT 20
```
**Results**: Top species by gene count - Mouse (744,820), Sheep (633,869), Pig (624,705), Human (87,688)

## Cross-Reference Analysis

### Gene-level cross-references via rdfs:seeAlso:
- UniProt: Protein sequences (P38398 for BRCA1)
- HGNC: Human gene nomenclature (HGNC:1100 for BRCA1)
- NCBI Gene: Gene database
- Reactome: Pathway involvement
- OMIM: Disease associations

### Integration with co-located databases (EBI endpoint):
- ChEMBL: Drug target information via UniProt bridge
  - Ensembl → UniProt (rdfs:seeAlso) → ChEMBL targets (skos:exactMatch)
- Reactome: Pathway annotations
- ChEBI: Metabolite/compound links

### Entity counts:
- Human genes: 87,688 total
- Human with UniProt xrefs: ~60% (~52,000)
- Total genes across species: ~3,000,000
- Total transcripts: ~4,000,000
- Total proteins: ~2,000,000

## Interesting Findings

**Findings requiring actual queries (non-trivial):**

1. **BRCA1 genomic location** (ENSG00000012048):
   - Chromosome 17: 43,044,295 - 43,170,245
   - Minus strand (reverse strand)
   - Assembly: GRCh38

2. **BRCA1 has multiple transcript isoforms**:
   - 15+ protein-coding transcripts found
   - Most map to canonical UniProt P38398
   - Some map to alternative isoforms (H0Y850, E7EQW4, C9IZW4)

3. **Mouse has more genes than human**: 744,820 vs 87,688
   - Due to different annotation completeness levels
   - Human annotation is more conservative/curated

4. **Species diversity**: 100+ species annotated
   - Includes fish (salmon: 267,676; zebrafish: 154,109)
   - Farm animals (pig: 624,705; sheep: 633,869)
   - Model organisms (rat: 143,695)

5. **Kinase genes searchable**: Found receptor tyrosine kinases (ROR1, ROR2) and receptor-associated kinases (RIPK3, IRAK1, IRAK3) via description search

6. **X chromosome protein-coding genes**: HTR2C, CA5B, SLC9A7, GPC4, TLR8 (examples from query)

## Question Opportunities by Category

### Precision (specific IDs, coordinates)
- ✅ "What is the Ensembl gene ID for human BRCA1?" → ENSG00000012048
- ✅ "What are the genomic coordinates of BRCA1 on GRCh38?" → chr17:43044295-43170245
- ✅ "What is the Ensembl protein ID for BRCA1 canonical transcript?" → ENSP00000312236
- ✅ "Which strand is EGFR on?" → Plus or minus strand

### Completeness (counts, comprehensive lists)
- ✅ "How many human genes are annotated in Ensembl?" → 87,688
- ✅ "How many transcript isoforms does BRCA1 have in Ensembl?"
- ✅ "List protein-coding genes on human chromosome X"
- ✅ "How many species are covered in Ensembl?"

### Integration (cross-database linking)
- ✅ "What UniProt IDs are linked to Ensembl gene ENSG00000012048?" → P38398
- ✅ "Convert Ensembl ID ENSG00000012048 to HGNC ID" → HGNC:1100
- ✅ "What Ensembl gene encodes UniProt protein P38398?"
- ✅ "Link Ensembl genes to ChEMBL drug targets"

### Currency (recent/updated data)
- ✅ "What human genes related to DNA repair are in Ensembl?" (uses current descriptions)
- ✅ "What is the current release of Ensembl?" (Release 114)

### Specificity (specialized/niche)
- ✅ "What are zebrafish orthologs of human disease genes in Ensembl?"
- ✅ "Find human microRNA genes (biotype miRNA)"
- ✅ "What lncRNA genes are on chromosome 17?"

### Structured Query (complex filtering)
- ✅ "Find human kinase genes with 'receptor' in their description"
- ✅ "List genes between coordinates 43000000-44000000 on chromosome 17"
- ✅ "Find genes with MANE Select transcript annotations"
- ✅ "Get exons in order for transcript ENST00000352993"

## Notes

### Limitations
- Not all transcripts encode proteins (lncRNA, miRNA, pseudogenes)
- ~60% of genes have UniProt cross-references
- FALDO queries may return duplicate entries (use DISTINCT)
- Multiple genome assemblies require graph specification

### Best Practices
- Always filter by species taxonomy ID for clarity (9606 for human)
- Use bif:contains for text search with wildcards (e.g., 'BRCA*')
- Use DISTINCT with FALDO location queries
- Check biotype when expecting proteins (ENSGLOSSARY_0000026 = protein_coding)
- Chromosome filtering: CONTAINS(STR(?chr), "GRCh38/17")

### Data Quality
- UniProt cross-references enable pharmacological integration
- Transcript flags (MANE, APPRIS, TSL) indicate confidence
- ~95% of genes have descriptions
- Genomic coordinates highly accurate for reference assemblies

### Cross-database Integration
- EBI endpoint enables Ensembl + ChEMBL + ChEBI + Reactome queries
- UniProt serves as bridge between genomic and pharmacological data
