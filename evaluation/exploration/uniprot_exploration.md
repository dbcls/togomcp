# UniProt Exploration Report

## Database Overview
- **Purpose**: Comprehensive protein sequence and functional information
- **Scope**: Integrates Swiss-Prot (manually curated) and TrEMBL (automatically annotated)
- **Key entities**: Proteins, sequences, annotations, GO terms, cross-references
- **Size**: 444M total proteins; 923K reviewed (Swiss-Prot); 40,209 human reviewed proteins
- **Data quality**: CRITICAL - Always filter by `up:reviewed 1` (reduces 444M to 923K, 99.8% reduction)

## Schema Analysis (from MIE file)

### Main Properties
- `up:Protein`: Central entity
- `up:mnemonic`: Human-readable identifier (e.g., "BRCA1_HUMAN")
- `up:organism`: Organism taxonomy link
- `up:reviewed`: Quality indicator (1=Swiss-Prot, 0=TrEMBL)
- `up:sequence`: Links to isoforms with amino acid sequences
- `up:annotation`: Functional annotations (Function, Subcellular location, etc.)
- `up:classifiedWith`: GO terms and other ontology classifications
- `up:enzyme`: EC number classifications
- `up:encodedBy`: Gene information
- `up:recommendedName/up:fullName`: Recommended protein name

### Important Relationships
- Cross-references via `rdfs:seeAlso` to 200+ databases (PDB, EMBL, RefSeq, HGNC, InterPro, etc.)
- Taxonomy via `up:organism` to NCBI Taxonomy
- GO term classification via `up:classifiedWith`

### Query Patterns
- Always include `up:reviewed 1` for performance and quality
- Use `bif:contains` for text search but must split property paths
- Human proteins: `up:organism <http://purl.uniprot.org/taxonomy/9606>`

## Search Queries Performed

1. **Query**: "BRCA1 human"
   - Results: Found P38398 (BRCA1_HUMAN) - Breast cancer type 1 susceptibility protein
   - Also found homologs in dog, mouse, and BRCA1-interacting proteins

2. **Query**: "Cas9 CRISPR Streptococcus pyogenes"
   - Results: Found Q99ZW2 (SpCas9, SpyCas9) from S. pyogenes serotype M1
   - Also found SaCas9 (Staphylococcus aureus) and St3Cas9 (S. thermophilus)

3. **Query**: "insulin human"
   - Results: Found P01308 (human insulin), P06213 (insulin receptor), P14735 (insulin-degrading enzyme)

4. **Query**: "p53 tumor suppressor"
   - Results: Found homologs across species (dog Q29537, zebrafish P79734, mouse, bovine)
   - Note: Search returned non-human p53 first (may need organism filter for human)

5. **Query**: "hemoglobin alpha human"
   - Results: Found P69905 (Hemoglobin subunit alpha human), also gamma-2 (P69892), beta (P68871), delta (P02042)

## SPARQL Queries Tested

```sparql
# Query 1: Count reviewed human proteins
PREFIX up: <http://purl.uniprot.org/core/>

SELECT (COUNT(*) as ?count)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> .
}
# Results: 40,209 reviewed human proteins
```

```sparql
# Query 2: Get functional annotations and GO terms for specific proteins
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT ?protein ?mnemonic ?functionComment ?goLabel
WHERE {
  VALUES ?protein { uniprot:P04637 uniprot:P38398 }
  ?protein up:mnemonic ?mnemonic .
  OPTIONAL {
    ?protein up:annotation ?annot .
    ?annot a up:Function_Annotation ;
           rdfs:comment ?functionComment .
  }
  OPTIONAL {
    ?protein up:classifiedWith ?goTerm .
    ?goTerm rdfs:label ?goLabel .
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
  }
}
LIMIT 30
# Results: Rich functional annotations for BRCA1 (P38398) with GO terms like "nucleus", "cytoplasm", "plasma membrane"
```

```sparql
# Query 3: List human proteins with mnemonics
PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?protein ?mnemonic
WHERE {
  ?protein a up:Protein ;
           up:mnemonic ?mnemonic ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> .
}
LIMIT 10
# Results: Various human proteins (CF123_HUMAN, KIAS1_HUMAN, etc.)
```

## Interesting Findings

### Specific Entities for Questions
- **P38398**: BRCA1_HUMAN - extensively annotated with functions, GO terms
- **Q99ZW2**: SpCas9 from S. pyogenes M1 - important for CRISPR questions
- **P04637**: P53_HUMAN - tumor suppressor with 307 versions
- **P01308**: Human insulin - well-known protein for questions
- **P69905**: Hemoglobin alpha - blood protein
- **P06213**: Insulin receptor

### Unique Properties
- Mass values in sequences (e.g., P04637 canonical isoform mass: 43653)
- MD5 checksums for sequence validation
- Version tracking (P04637 version 307)
- Multiple GO term localizations (nucleus, cytoplasm, plasma membrane)

### Database Connections
- **Strong links to**: PDB (14-25% reviewed), AlphaFold (>98%), EMBL (~95%), HGNC (100% human), Reactome (~30%)
- **TogoID conversions**: uniprot → ncbigene, uniprot → ensembl, uniprot → pdb

### Key Statistics
- 40,209 reviewed human proteins
- >85% of reviewed proteins have GO annotations
- ~14-25% of reviewed proteins have PDB structures
- Average 12.5 GO terms per protein
- Average 45 cross-references per protein

## Question Opportunities by Category

### Precision
- What is the UniProt ID for SpCas9 from S. pyogenes M1? (Q99ZW2)
- What is the mnemonic for human BRCA1? (BRCA1_HUMAN)
- What is the mass of the canonical isoform of human p53? (43653 Da)
- What is the UniProt ID for human insulin? (P01308)
- What is the UniProt ID for human insulin receptor? (P06213)

### Completeness
- How many reviewed human proteins are in UniProt? (40,209)
- How many protein isoforms does BRCA1 have?
- What GO terms are associated with human BRCA1?
- List all reviewed proteins annotated with "kinase" function

### Integration
- What PDB structures are linked to P04637 (p53)?
- Convert UniProt P04637 to NCBI Gene ID (via TogoID)
- What Ensembl gene ID corresponds to UniProt P38398?
- What HGNC ID corresponds to human BRCA1?

### Currency
- What is the current version number of P04637 in UniProt? (307)
- When was the P38398 entry last modified?
- How many human proteins have AlphaFold structures?

### Specificity
- Find the UniProt ID for RNA-editing ligase 2 from Trypanosoma brucei (P86925)
- What is the UniProt ID for a specific viral protein?
- Find proteins from extremophile organisms

### Structured Query
- Find reviewed human proteins with both kinase activity AND nuclear localization
- Find proteins annotated with EC 2.7.10.1 (tyrosine kinases)
- Find reviewed proteins with PDB structures at resolution <2Å

## Notes
- **CRITICAL**: Always use `up:reviewed 1` filter for performance and data quality
- Use `bif:contains` for text search but split property paths (no `/` with bif:contains)
- Never filter by mnemonic patterns - use `up:organism` with taxonomy URIs
- COUNT queries require reviewed filter to avoid timeout
- Rich cross-reference network makes this database excellent for integration questions
