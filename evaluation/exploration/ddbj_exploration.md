# DDBJ (DNA Data Bank of Japan) Exploration Report

## Database Overview
- **Purpose**: Nucleotide sequence data from the International Nucleotide Sequence Database Collaboration (INSDC)
- **Scope**: Genomic entries with annotations (genes, CDS, tRNA, rRNA) and metadata
- **Key data types**: Entry metadata, Gene annotations, Coding sequences, RNA features, FALDO coordinates
- **Focus**: Sequence annotations with cross-references to BioProject, BioSample, NCBI Protein, Taxonomy

## Schema Analysis (from MIE file)

### Main Properties Available
- **Entry**: `nuc:Entry` with `rdfs:label`, `dcterms:identifier`, `nuc:organism`, `nuc:definition`, `nuc:dblink`
- **Gene**: `nuc:Gene` with `nuc:locus_tag`, `nuc:gene` (symbol), `faldo:location`
- **CDS**: `nuc:Coding_Sequence` with `nuc:locus_tag`, `nuc:product`, `nuc:translation`, `rdfs:seeAlso` (protein)
- **RNA**: `nuc:Transfer_RNA`, `nuc:Ribosomal_RNA` with `nuc:product`
- **Source**: `nuc:Source` with `nuc:organism`, `nuc:mol_type`
- **Location**: `faldo:Region` with `faldo:begin/faldo:end` positions

### Important Relationships
- Gene-CDS linked via `sio:SIO_010081` (case-sensitive!)
- BioProject/BioSample via `nuc:dblink`
- NCBI Protein via `rdfs:seeAlso`
- Taxonomy via `ro:0002162` (in taxon)
- Sequence Ontology terms via `rdfs:subClassOf`
- FALDO for genomic coordinates

### Query Patterns Observed
- Entry-level searches using `bif:contains` on `nuc:organism`
- Feature-level queries require entry ID filtering
- Gene-CDS joins via `sio:SIO_010081`
- FALDO coordinates: `faldo:location/faldo:begin/faldo:position`

## Search Queries Performed

### Query 1: Escherichia coli entries
- **Search**: `bif:contains "'escherichia' AND 'coli'"`
- **Results**: 10+ entries including:
  - AP026093.1, AP026094.1, AP026095.1 (E. coli genomes)
  - Multiple genome assemblies from DDBJ

### Query 2: Bacillus subtilis entries
- **Search**: `bif:contains "'bacillus' AND 'subtilis'"`
- **Results**: 10+ entries including:
  - AB271744.1 - Bacillus subtilis subsp. subtilis
  - Multiple strains with relevance score 30

### Query 3: CP036276.1 entry metadata
- **Search**: Entry-specific query
- **Results**:
  - Organism: Symmachiella dynata
  - BioProject: PRJNA485700
  - BioSample: SAMN10954015
  - Label: "Symmachiella dynata strain Mal52 chromosome, complete genome"

### Query 4: Genes with products in CP036276.1
- **Search**: Gene-CDS join by locus tag
- **Results**: 20 genes including:
  - Mal52_08030 (clpX) - ATP-dependent Clp protease ATP-binding subunit ClpX
  - Mal52_08090 (afsK_1) - Serine/threonine-protein kinase AfsK
  - Mal52_00720 (stkP_1) - Serine/threonine-protein kinase StkP

### Query 5: RNA features in CP036276.1
- **Search**: Union of Transfer_RNA and Ribosomal_RNA
- **Results**: 30 tRNA entries including:
  - tRNA-Ile, tRNA-Ala, tRNA-Gly, tRNA-Pro, tRNA-Glu, etc.

## SPARQL Queries Tested

```sparql
# Query 1: Search entries by organism
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?entry ?organism ?relevance
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?entry a nuc:Entry ;
         nuc:organism ?organism .
  ?organism bif:contains "'escherichia' AND 'coli'" option (score ?relevance) .
}
ORDER BY DESC(?relevance)
LIMIT 10
# Results: E. coli entries with relevance scores
```

```sparql
# Query 2: Gene-CDS-Protein integration
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX sio: <http://semanticscience.org/resource/>

SELECT ?locus_tag ?product ?protein_id
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?gene a nuc:Gene ;
        nuc:locus_tag ?locus_tag .
  ?cds sio:SIO_010081 ?gene ;
       nuc:product ?product ;
       rdfs:seeAlso ?protein_id .
  FILTER(CONTAINS(STR(?protein_id), "ncbiprotein"))
  FILTER(CONTAINS(STR(?gene), "CP036276.1"))
}
LIMIT 20
# Results: Locus tags with products and NCBI Protein IDs (e.g., QDU42347.1)
```

```sparql
# Query 3: Entry with BioProject/BioSample links
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?entry ?label ?organism ?bioproject ?biosample
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?entry a nuc:Entry ;
         rdfs:label ?label ;
         nuc:organism ?organism .
  OPTIONAL { 
    ?entry nuc:dblink ?bioproject .
    FILTER(CONTAINS(STR(?bioproject), "bioproject"))
  }
  FILTER(?entry = <http://identifiers.org/insdc/CP036276.1>)
}
# Results: Symmachiella dynata with PRJNA485700 and SAMN10954015
```

```sparql
# Query 4: RNA features by type
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>

SELECT ?rna_type ?product
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  {
    ?rna a nuc:Transfer_RNA ; nuc:product ?product .
    BIND("tRNA" AS ?rna_type)
    FILTER(CONTAINS(STR(?rna), "CP036276.1"))
  }
  UNION
  {
    ?rna a nuc:Ribosomal_RNA ; nuc:product ?product .
    BIND("rRNA" AS ?rna_type)
    FILTER(CONTAINS(STR(?rna), "CP036276.1"))
  }
}
LIMIT 30
# Results: tRNA features for various amino acids
```

## Interesting Findings

### Specific Entities for Good Questions
1. **CP036276.1**: Complete genome of Symmachiella dynata (well-annotated)
2. **Mal52_08030 (clpX)**: ATP-dependent Clp protease with NCBI Protein QDU42347.1
3. **E. coli genomes**: Multiple DDBJ entries (AP026093.1, etc.)
4. **Bacillus subtilis**: Multiple strains in database

### Unique Properties/Patterns
- FALDO coordinate system for precise genomic positions
- Gene-CDS linkage via SIO_010081 (case-sensitive)
- BioProject/BioSample cross-references for experimental context
- Sequence Ontology classification (SO terms)
- identifiers.org URIs for standardized cross-references

### Connections to Other Databases
- **BioProject**: Experimental project metadata (e.g., PRJNA485700)
- **BioSample**: Specimen information (e.g., SAMN10954015)
- **NCBI Protein**: RefSeq protein sequences (e.g., QDU42347.1)
- **NCBI Taxonomy**: Classification via ro:0002162 and rdfs:seeAlso

### Verifiable Facts
- CP036276.1 organism: Symmachiella dynata
- CP036276.1 BioProject: PRJNA485700
- Mal52_08030 product: ATP-dependent Clp protease ATP-binding subunit ClpX
- Mal52_08030 protein: QDU42347.1

## Question Opportunities by Category

### Precision
- "What organism does DDBJ entry CP036276.1 belong to?" → Symmachiella dynata
- "What is the NCBI Protein accession for the clpX gene in CP036276.1?" → QDU42347.1
- "What is the locus tag for ATP-dependent Clp protease in Symmachiella dynata?" → Mal52_08030

### Completeness
- "How many tRNA genes are in DDBJ entry CP036276.1?"
- "List all genes with 'kinase' in their product description from CP036276.1"

### Integration
- "What BioProject is DDBJ entry CP036276.1 associated with?" → PRJNA485700
- "Link DDBJ entry CP036276.1 to its BioSample record" → SAMN10954015
- "What NCBI Protein IDs are associated with genes in CP036276.1?"

### Currency
- "What new E. coli genome sequences are available in DDBJ?"
- "When was entry CP036276.1 last updated?"

### Specificity
- "What is the product of gene Mal52_08030 in CP036276.1?" → ATP-dependent Clp protease ATP-binding subunit ClpX
- "Find regulatory genes (BlaI, MprA) in Symmachiella dynata genome"

### Structured Query
- "Find all proteases and peptidases in CP036276.1"
- "List genes with both gene symbol and NCBI Protein cross-reference in CP036276.1"
- "Find entries for specific organism with BioProject links"

## Notes

### Limitations
- Queries timeout without entry ID filtering
- Mostly prokaryotic data
- Some organism searches (e.g., "human") may timeout
- Aggregation queries (COUNT) require sampling instead

### Best Practices
- Always include `FROM <http://rdfportal.org/dataset/ddbj>` in SPARQL
- Use `bif:contains` for organism searches at entry level
- Always filter by entry ID before complex joins: `FILTER(CONTAINS(STR(?gene), "ENTRY_ID"))`
- Use uppercase `sio:SIO_010081` (case-sensitive)
- Use OPTIONAL for gene symbols (~60% coverage)
- Use LIMIT instead of COUNT for exploratory queries

### Data Quality
- >99% entries have organism information
- >99% genes have locus tags
- ~60% genes have gene symbols
- >95% CDS have products
- >99% features have FALDO coordinates
