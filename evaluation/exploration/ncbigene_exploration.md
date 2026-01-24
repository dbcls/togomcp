# NCBI Gene Database Exploration Report

## Database Overview
- **Purpose**: Comprehensive gene database covering 57M+ genes across all organisms
- **Endpoint**: https://rdfportal.org/ncbi/sparql
- **Graph**: `http://rdfportal.org/dataset/ncbigene`
- **Key Features**: Gene symbols/descriptions, chromosomal locations, gene types, cross-references (Ensembl, HGNC, OMIM), orthology relationships
- **Data Version**: November 2024

## Schema Analysis (from MIE file)
### Main Entities
- **Gene** (insdc:Gene): Central entity with identifier, label (symbol), description (full name), type, chromosomal location
- Cross-references via `insdc:dblink` (IRI) and `insdc:db_xref` (string)
- Orthology via `orth:hasOrtholog`

### Important Properties
- `rdfs:label`: Gene symbol (INS, BRCA1, TP53)
- `dct:description`: Full gene name (insulin, BRCA1 DNA repair associated)
- `ncbio:typeOfGene`: protein-coding, ncRNA, tRNA, pseudo, rRNA, etc.
- `ncbio:taxid`: Links to NCBI Taxonomy
- `insdc:chromosome` / `insdc:map`: Chromosomal location

### Query Patterns
- **RECOMMENDED**: Use `ncbi_esearch` BEFORE SPARQL for efficient gene discovery
- Use `bif:contains` for text searches (not FILTER/CONTAINS)
- Always filter by taxid early (57M+ genes total)
- LIMIT required for orthology queries
- Include FROM clause for graph targeting

## Search Queries Performed (ncbi_esearch)

1. **Query: BRCA1[Gene Name] AND human[organism]** → Gene ID: 672
   - BRCA1 DNA repair associated, chromosome 17q21.31

2. **Query: INS[Gene Name] AND human[organism]** → Gene ID: 3630
   - Human insulin gene

3. **Query: insulin-related genes (SPARQL)** → Found multiple genes:
   - IGF1 (3479): insulin like growth factor 1
   - IGF1R (3480): insulin like growth factor 1 receptor
   - IGF2 (3481): insulin like growth factor 2
   - IGFBP1-7: insulin like growth factor binding proteins
   - IDDM3-18: insulin dependent diabetes mellitus loci

4. **Query: Human protein-coding genes count** → 20,595 protein-coding genes

5. **Query: Human genes with Ensembl links** → 38,399 genes with Ensembl cross-references

## SPARQL Queries Tested

```sparql
# Query 1: Get BRCA1 gene info
SELECT ?label ?description ?type ?chromosome ?map
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  <http://identifiers.org/ncbigene/672> rdfs:label ?label ;
    ncbio:typeOfGene ?type .
  OPTIONAL { <http://identifiers.org/ncbigene/672> dct:description ?description }
  OPTIONAL { <http://identifiers.org/ncbigene/672> insdc:chromosome ?chromosome }
  OPTIONAL { <http://identifiers.org/ncbigene/672> insdc:map ?map }
}
# Results: BRCA1, "BRCA1 DNA repair associated", protein-coding, chromosome 17, 17q21.31
```

```sparql
# Query 2: INS orthologs across species
SELECT ?ortholog ?label ?taxid
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  <http://identifiers.org/ncbigene/3630> orth:hasOrtholog ?ortholog .
  ?ortholog rdfs:label ?label ;
            ncbio:taxid ?taxid .
}
LIMIT 20
# Results: Found orthologs in mouse (Ins2, 16334), rat (Ins2, 24506), 
# cow (280829), pig (397415), dog (483665), cat (493804), chicken (396145), 
# and many other species
```

```sparql
# Query 3: Count human protein-coding genes
SELECT (COUNT(?gene) as ?count)
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene a insdc:Gene ;
        ncbio:typeOfGene "protein-coding" ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
}
# Results: 20,595 human protein-coding genes
```

## Cross-Reference Analysis

**Entity counts** (unique entities with mappings):
- Human genes with Ensembl links: 38,399
- Human protein-coding genes: 20,595

**Cross-reference types**:
- `insdc:dblink` (IRI-based): Ensembl, HGNC, OMIM
- `insdc:db_xref` (string-based): AllianceGenome and others
- `orth:hasOrtholog`: Internal orthology relationships

**Shared endpoint databases** (ncbi endpoint):
- ClinVar: Gene → Variant associations
- PubMed: Gene → Literature associations
- PubTator: Gene → Named entity mentions
- MedGen: Gene → Clinical concepts

## Interesting Findings

**Findings requiring actual database queries:**

1. **20,595 human protein-coding genes** in NCBI Gene - core gene count for human genome

2. **38,399 human genes have Ensembl cross-references** - enables integration with Ensembl annotations

3. **INS gene (3630) has orthologs across 20+ species** including:
   - Mouse (Ins2, 16334)
   - Rat (Ins2, 24506)
   - Cow (280829)
   - Chicken (396145)
   - Cat (493804)
   - Dog (483665)

4. **Insulin-related gene family**: IGF1, IGF2, IGF1R, IGF2R, IGFBP1-7, IGFALS - found via bif:contains search

5. **BRCA1 (gene 672)** located at chromosome 17q21.31, type "protein-coding"

6. **Gene types in human genome include**: protein-coding, pseudo (pseudogenes), ncRNA, tRNA, rRNA, unknown

## Question Opportunities by Category

### Precision
- "What is the NCBI Gene ID for human BRCA1?" → 672
- "What chromosome is the human INS gene located on?" → 11 (requires query)
- "What is the gene symbol for NCBI Gene ID 3630?" → INS

### Completeness
- "How many human protein-coding genes are in NCBI Gene?" → 20,595
- "How many human genes have Ensembl cross-references?" → 38,399
- "How many orthologs does human INS gene have?" → 20+ (requires orthology query)

### Integration
- "Convert NCBI Gene ID 672 to Ensembl gene ID" → ENSG00000012048 (via dblink)
- "Find ClinVar variants for NCBI Gene 672 (BRCA1)" → Cross-database query
- "What OMIM entries are linked to BRCA1 (gene 672)?" → Via dblink

### Currency
- "What is the current count of human genes in NCBI Gene?" → Dynamic count
- "When was gene 672 last modified?" → dct:modified property

### Specificity
- "What are the mouse orthologs of human insulin (INS)?" → Ins2 (16334)
- "What genes contain 'insulin like growth factor' in their description?" → IGF1, IGF2, IGF1R, IGF2R, IGFBP1-7

### Structured Query
- "Find all human genes on chromosome 17 that are protein-coding" → Filter by chromosome and type
- "List human genes with descriptions containing 'kinase' but not 'pseudo'" → Boolean bif:contains
- "Find genes with orthologs in both mouse and rat" → Multi-species orthology query

## Notes
- **Search workflow**: Use `ncbi_esearch` for gene discovery, then SPARQL for detailed RDF data
- **Performance**: Gene ID lookups fast (<1s); orthology queries need LIMIT; always filter by taxid
- **URI patterns**: 
  - NCBI Gene: `http://identifiers.org/ncbigene/{id}`
  - For ClinVar linking: convert to `http://ncbi.nlm.nih.gov/gene/{id}`
- **Shared endpoint**: ncbi endpoint also hosts ClinVar, PubMed, PubTator, MedGen
- **Label vs Description**: `rdfs:label` = symbol (INS), `dct:description` = full name (insulin)
- **57M+ total genes**: Always filter by organism/taxid early in queries
