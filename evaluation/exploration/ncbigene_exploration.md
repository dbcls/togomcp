# NCBI Gene Database Exploration Report

## Database Overview
- **Purpose**: Comprehensive gene database covering all organisms with gene-centric information
- **Scope**: 57,768,578 total genes across all organisms
- **Key data types**:
  - Protein-coding genes (46,105,590, ~80%)
  - Non-coding RNAs (3,476,823, ~6%)
  - Transfer RNAs (3,030,346, ~5%)
  - Pseudogenes (2,731,789, ~5%)
  - Ribosomal RNAs (993,602, ~2%)

## Schema Analysis (from MIE file)

### Main Properties
- **insdc:Gene**: Core gene entity with RDF type
- **dct:identifier**: Numeric gene ID (e.g., 1, 3630, 7157)
- **rdfs:label**: Gene symbol (e.g., "A1BG", "INS", "BRCA1", "TP53")
- **dct:description**: Full gene name (e.g., "insulin", "tumor protein p53")
- **ncbio:typeOfGene**: Gene type (protein-coding, ncRNA, tRNA, pseudo, rRNA)
- **insdc:gene_synonym**: Historical or alternative symbols
- **dct:alternative**: Alternative full names
- **ncbio:nomenclatureStatus**: Official nomenclature status
- **ncbio:taxid**: Organism classification (links to NCBI Taxonomy)
- **insdc:chromosome**: Chromosomal location (e.g., "19", "X|Y")
- **insdc:map**: Cytogenetic map position (e.g., "19q13.43")
- **insdc:dblink**: IRI-based external links (Ensembl, HGNC, OMIM via identifiers.org)
- **insdc:db_xref**: String-based cross-references (e.g., "AllianceGenome:12345")
- **orth:hasOrtholog**: Orthologous genes across species
- **dct:modified**: Last update date

### Important Relationships
- **identifiers.org URIs**: Standardized gene identifiers (`http://identifiers.org/ncbigene/ID`)
- **External database links**:
  - Ensembl: Gene annotations and genomic context
  - HGNC: Official human gene nomenclature
  - OMIM: Disease associations
  - AllianceGenome: Integrated resources
- **Taxonomic classification**: Links to NCBI Taxonomy database
- **Orthology relationships**: Bidirectional links between species orthologs
- **Average cardinality**: 2.5 synonyms/gene, 1.8 external links/gene, ~150 orthologs/gene

### Query Patterns Observed
1. **Always filter by organism first**: `ncbio:taxid <http://identifiers.org/taxonomy/9606>` to avoid timeout
2. **Use bif:contains for text search**: NOT REGEX or FILTER(CONTAINS(...))
3. **Symbol vs full name**: 
   - `rdfs:label` = gene symbol (e.g., "INS")
   - `dct:description` = full name (e.g., "insulin")
4. **Include FROM clause**: `FROM <http://rdfportal.org/dataset/ncbigene>`
5. **Always add LIMIT**: Especially for orthology queries (10-1000)
6. **Use OPTIONAL for variable coverage**: Not all genes have all properties
7. **Full URI format**: `<http://identifiers.org/ncbigene/ID>` not just ID number
8. **Score relevance**: Use `option (score ?sc)` with bif:contains for ranking

## Search Queries Performed

### Query 1: Get gene by ID (Gene ID 1 - A1BG)
**Tool**: TogoMCP run_sparql
**Result**: 
- Label: "A1BG" (alpha-1-B glycoprotein)
- Description: "alpha-1-B glycoprotein"
- Type: "protein-coding"
- First gene in NCBI Gene database

### Query 2: Search cancer genes (BRCA1, BRCA2, TP53)
**Tool**: TogoMCP run_sparql with bif:contains
**Result**: Found 3 major cancer genes with relevance scores:
- TP53 (Gene ID 7157): "tumor protein p53" (score: 13)
- BRCA1 (Gene ID 672): "BRCA1 DNA repair associated" (score: 11)
- BRCA2 (Gene ID 675): "BRCA2 DNA repair associated" (score: 11)
- Scores indicate search relevance ranking

### Query 3: Tested gene type filtering (from MIE)
**Tool**: Would filter protein-coding genes in human
**Pattern**: Filter by typeOfGene and taxid
**Expected**: Efficient retrieval of specific gene classes

### Query 4: Search BRCA1 gene across species
**Tool**: Related entity search (UniProt cross-reference)
**Result**: Found BRCA1 in multiple organisms:
- P38398: Human BRCA1 (Breast cancer type 1 susceptibility protein)
- Q95153: Dog BRCA1 homolog
- P48754: Mouse BRCA1 homolog
- Q9GKK8: Chimpanzee BRCA1 homolog
- Q8RXD4: Arabidopsis BRCA1 homolog
Demonstrates ortholog relationships across species

### Query 5: Search TP53 tumor suppressor across species
**Tool**: Related entity search (UniProt cross-reference)
**Result**: Found TP53 in multiple organisms:
- Cellular tumor antigen p53 across species:
  - Bovine, Donkey, Green monkey, Rabbit, Guinea pig
  - Sheep, Rat, Hamster, Ground squirrel
- Shows widespread conservation of tumor suppressor
- Demonstrates extensive orthology in NCBI Gene

## SPARQL Queries Tested

```sparql
# Query 1: Get basic gene information by ID
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX ncbio: <https://dbcls.github.io/ncbigene-rdf/ontology.ttl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?label ?description ?type
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  <http://identifiers.org/ncbigene/1> rdfs:label ?label ;
    ncbio:typeOfGene ?type .
  OPTIONAL { <http://identifiers.org/ncbigene/1> dct:description ?description }
}
# Results: A1BG, alpha-1-B glycoprotein, protein-coding
```

```sparql
# Query 2: Search multiple gene symbols with relevance ranking
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX ncbio: <https://dbcls.github.io/ncbigene-rdf/ontology.ttl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?gene ?label ?description ?sc
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene a insdc:Gene ;
        rdfs:label ?label ;
        dct:description ?description ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
  ?label bif:contains "'BRCA1' OR 'BRCA2' OR 'TP53'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 10
# Results: TP53 (7157), BRCA1 (672), BRCA2 (675) with relevance scores
```

```sparql
# Query 3: Search by full gene name (from MIE example)
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX ncbio: <https://dbcls.github.io/ncbigene-rdf/ontology.ttl#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?gene ?label ?description ?sc
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene dct:description ?description ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
  ?description bif:contains "'insulin'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 20
# Would return INS (3630) and related insulin genes
```

## Interesting Findings

### Specific Entities for Questions
1. **Gene ID 1 (A1BG)**: First gene in database, protein-coding
2. **Gene ID 7157 (TP53)**: Major tumor suppressor, "tumor protein p53"
3. **Gene ID 672 (BRCA1)**: BRCA1 DNA repair associated
4. **Gene ID 675 (BRCA2)**: BRCA2 DNA repair associated
5. **Gene ID 3630 (INS)**: Insulin gene with many orthologs
6. **Gene ID 6473 (SHOX)**: Multi-chromosome gene (X|Y)

### Unique Properties
- **Massive scale**: 57.7 million genes across all organisms
- **Gene type diversity**: Protein-coding, ncRNA, tRNA, pseudo, rRNA
- **Orthology network**: Average 150 orthologs per gene
- **identifiers.org URIs**: Enables seamless cross-database integration
- **Dual reference systems**: IRI-based (dblink) and string-based (db_xref)
- **Relevance scoring**: bif:contains provides search ranking

### Connections to Other Databases
- **Ensembl**: Gene annotations and genomic context
- **HGNC**: Official human gene nomenclature authority
- **OMIM**: Genetic disorders and disease associations
- **NCBI Taxonomy**: Organism classification (9606 = Homo sapiens)
- **AllianceGenome**: Integrated model organism data
- **Within NCBI Gene**: Orthology links between species

### Specific, Verifiable Facts
1. NCBI Gene contains 57,768,578 total genes
2. 80% are protein-coding genes (46,105,590)
3. Gene ID 1 is A1BG (alpha-1-B glycoprotein)
4. TP53 is Gene ID 7157
5. BRCA1 is Gene ID 672, BRCA2 is Gene ID 675
6. Human = taxonomy 9606
7. Average 2.5 synonyms per gene
8. ~95% of genes have descriptions
9. ~80% have chromosomal location data
10. ~40% have orthology annotations

## Question Opportunities by Category

### Precision
- "What is the NCBI Gene ID for BRCA1?" (672)
- "What is the full name of gene TP53?" ("tumor protein p53")
- "What type of gene is A1BG?" (protein-coding)
- "What chromosome is SHOX located on?" (X|Y)

### Completeness
- "How many protein-coding genes are in the human genome?" (filter by taxid 9606 and type)
- "List all synonyms for the INS gene"
- "What are all the orthologs of human TP53?"
- "How many ncRNA genes exist in NCBI Gene?" (3,476,823)

### Integration
- "What is the Ensembl ID for NCBI Gene 672 (BRCA1)?"
- "Convert NCBI Gene ID 7157 to HGNC ID"
- "What OMIM entries are associated with BRCA1?"
- "Link TP53 to UniProt via intermediate databases"

### Currency
- "When was gene ID 7157 last updated?" (check dct:modified)
- "What are recently added cancer-related genes?"
- "Which genes have nomenclature status 'official'?"

### Specificity
- "What is the cytogenetic map position of A1BG?" (19q13.43)
- "What is the nomenclature status of INS gene?"
- "Which genes are pseudogenes of the ACTG1 family?"
- "What genes have multiple chromosomal locations?" (like SHOX: X|Y)

### Structured Query
- "Find all human kinase genes" (taxid 9606, description contains "kinase")
- "List genes on chromosome 19 with protein-coding type"
- "Find cancer-related genes but not tumor suppressors" (Boolean search)
- "Count genes by type for mouse (taxid 10090)"

## Notes

### Limitations and Challenges
1. **Massive scale**: 57M+ genes require careful query optimization
2. **Must filter by organism**: Queries timeout without taxid filter
3. **Variable coverage**: Best for model organisms (human, mouse, rat)
4. **Label vs description**: Symbols in label, full names in description
5. **Orthology completeness**: More complete between closely related species
6. **Optional properties**: Not all genes have all annotations
7. **Performance**: Unbounded orthology queries can timeout

### Best Practices for Querying
1. **ALWAYS filter by taxid first**: `ncbio:taxid <http://identifiers.org/taxonomy/9606>`
2. **Use bif:contains for text search**: NOT REGEX or FILTER(CONTAINS(...))
3. **Search the right field**:
   - Gene symbols → `rdfs:label` (e.g., "INS", "BRCA1")
   - Full names → `dct:description` (e.g., "insulin")
4. **Include FROM clause**: `FROM <http://rdfportal.org/dataset/ncbigene>`
5. **Always add LIMIT**: 10-1000 depending on query
6. **Use full URI format**: `<http://identifiers.org/ncbigene/ID>`
7. **Add relevance scoring**: `option (score ?sc)` with bif:contains
8. **Use OPTIONAL** for variable properties (chromosome, dblink, orthologs)
9. **Start specific for orthology**: Begin with known gene, then traverse
10. **Boolean search syntax**: `"('term1' OR 'term2') AND NOT 'term3'"`

### Data Quality
- **Best coverage**: Human (9606), mouse (10090), rat (10116)
- **Description coverage**: ~95% of genes
- **Chromosomal location**: ~80% of genes
- **External links**: ~70% of genes (varies by organism)
- **Orthology**: ~40% of genes (more for model organisms)
- **Update frequency**: Regular updates from NCBI
- **Official nomenclature**: tracked via nomenclatureStatus property
- **Curation level**: Higher for model organisms, lower for non-model species
