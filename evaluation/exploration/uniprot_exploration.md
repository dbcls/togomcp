# UniProt Exploration Report

## Database Overview
- **Purpose**: Comprehensive protein sequence and functional information integrating Swiss-Prot (manually curated) and TrEMBL (automatically annotated)
- **Scope**: 444M proteins with sequences, functions, domains, structures, variants, and cross-references to 200+ databases
- **Key data types**: **CRITICAL DISTINCTION**: reviewed=1 (Swiss-Prot, 923K entries, expert curated) vs reviewed=0 (TrEMBL, 444M entries, automated annotations)

## Schema Analysis (from MIE file)

### Main Properties Available
- **Core identification**: dcterms:identifier (UniProt accession), up:mnemonic (entry name like P53_HUMAN)
- **Quality indicator**: up:reviewed (1=Swiss-Prot expert curated, 0=TrEMBL automated)
- **Organism**: up:organism (links to NCBI Taxonomy)
- **Naming**: up:recommendedName/up:fullName, up:alternativeName, up:shortName
- **Sequence**: up:sequence (canonical isoform) → rdf:value (amino acid sequence), up:mass, up:md5Checksum
- **Annotations**: up:annotation (specialized subtypes like Function_Annotation, Disease_Annotation, Subcellular_Location_Annotation)
- **Classifications**: up:classifiedWith (GO terms), up:enzyme (EC numbers)
- **Gene**: up:encodedBy (gene information)
- **Cross-references**: rdfs:seeAlso (links to 200+ databases including PDB, EMBL, RefSeq, InterPro, KEGG, Reactome)

### Important Relationships
- **Organism taxonomy**: up:organism → taxon → rdfs:subClassOf (hierarchical lineage)
- **Sequence isoforms**: up:sequence → multiple isoforms (canonical + alternatives)
- **GO classification**: up:classifiedWith → GO terms (molecular function, biological process, cellular component)
- **Enzyme classification**: up:enzyme → EC numbers
- **Gene encoding**: up:encodedBy → gene names and synonyms
- **External database links**: rdfs:seeAlso → URIs for PDB, EMBL, RefSeq, Ensembl, InterPro, Pfam, KEGG, Reactome, etc.

### Query Patterns Observed
- **CRITICAL**: Always filter by `up:reviewed 1` (reduces 444M to 923K, 99.8% reduction, prevents timeout)
- Use bif:contains for fast keyword search BUT must split property paths (cannot use `up:recommendedName/up:fullName` with bif:contains)
- Use `up:organism <http://purl.uniprot.org/taxonomy/TAXID>` for organism filtering, NOT mnemonic patterns
- Wrap GO terms and cross-references in OPTIONAL if not required
- Always use LIMIT (30-50 recommended for reviewed proteins)

## Search Queries Performed

1. **Query**: CRISPR-associated protein Cas9 (using TogoMCP search_uniprot_entity)
   - **Results**: Found 5 Cas9 proteins:
     - G3ECR1 - St-Cas9 (Streptococcus thermophilus)
     - J7RUA5 - SaCas9 (Staphylococcus aureus)
     - A0Q5Y3 - Cas9 (Francisella tularensis)
     - **Q99ZW2** - SpCas9/SpyCas9 (Streptococcus pyogenes M1) - **Most common variant used in genome editing**
     - Q927P4 - Cas9 (Listeria innocua)
   - All are endonucleases (EC 3.1.-.-)

2. **Query**: p53 tumor suppressor (using TogoMCP search_uniprot_entity)
   - **Results**: Found 10 p53 proteins across species:
     - Q29537 - Dog (Canis lupus familiaris)
     - Q9TTA1 - Common tree shrew (Tupaia belangeri)
     - P79734 - Zebrafish (Danio rerio)
     - Q64662 - California ground squirrel
     - P67939 - Bovine (Bos taurus)
     - P56424 - Rhesus macaque (Macaca mulatta)
     - P79892 - Horse (Equus caballus)
     - P61260 - Japanese macaque (Macaca fuscata fuscata)
     - O09185 - Chinese hamster (Cricetulus griseus)
     - Q8SPZ3 - Beluga whale (Delphinapterus leucas)
   - All named "Cellular tumor antigen p53 (Tumor suppressor p53)"
   - Shows wide conservation across mammals, fish, and marine species

3. **Query**: BRCA1 breast cancer susceptibility protein
   - **Results**: Found 10 BRCA1 proteins across species:
     - **P38398** - Human (Homo sapiens) - EC 2.3.2.27, RING-type E3 ubiquitin transferase
     - Q95153 - Dog (Canis lupus familiaris)
     - P48754 - Mouse (Mus musculus)
     - B6VQ60 - C. elegans (worm model)
     - Q864U1 - Bovine (Bos taurus)
     - O54952 - Rat (Rattus norvegicus)
     - Q6J6J0 - Bornean orangutan (Pongo pygmaeus)
     - Q6J6I9 - Rhesus macaque (Macaca mulatta)
     - Q9GKK8 - Chimpanzee (Pan troglodytes)
     - Q8RXD4 - Arabidopsis thaliana (plant homolog)
   - Shows evolutionary conservation from plants to primates

4. **Query**: Insulin hormone
   - **Results**: Found 10 insulin and insulin-related proteins:
     - **P01308** - Human insulin (Homo sapiens)
     - **P06213** - Human insulin receptor (IR, EC 2.7.10.1, CD220)
     - P14735 - Human insulin-degrading enzyme (EC 3.4.24.56)
     - P01317 - Bovine insulin
     - P01321 - Dog insulin
     - P01329 - Guinea pig insulin (Cavia porcellus)
     - P17715 - Degu insulin (Octodon degus)
     - P01315 - Pig insulin (Sus scrofa)
     - P67970 - Chicken insulin (Gallus gallus)
     - Q91XI3 - Ground squirrel insulin
   - Shows diversity: hormone, receptor, and degrading enzyme

5. **Query**: Hemoglobin alpha subunit
   - **Results**: Found 10 hemoglobin alpha proteins:
     - **P69905** - Human hemoglobin subunit alpha (includes hemopressin)
     - P69892 - Human hemoglobin subunit gamma-2 (fetal hemoglobin)
     - P01966 - Bovine hemoglobin alpha
     - P02016 - Common carp alpha (Cyprinus carpio)
     - P86882 - Arctic eelpout (Lycodes reticulatus)
     - P83623 - Congolli fish (Pseudaphritis urvillii)
     - P02017 - Desert sucker (Catostomus clarkii)
     - P01994 - Chicken hemoglobin alpha-A
     - P63112 - Yellow baboon (Papio cynocephalus)
     - B3EWR7 - Serpent eel (Ophisurus serpens)
   - Shows wide distribution across vertebrates (mammals, birds, fish)

## SPARQL Queries Tested

```sparql
# Query 1: Find reviewed proteins by organism (human)
PREFIX up: <http://purl.uniprot.org/core/>

SELECT ?protein ?mnemonic
WHERE {
  ?protein a up:Protein ;
           up:mnemonic ?mnemonic ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> .
}
LIMIT 30

# Expected results: Expert-curated human proteins
# Examples: P04637 (P53_HUMAN), P17612 (KAPCA_HUMAN), P86925 (RLGM2_TRYB2)
# CRITICAL: up:reviewed 1 filter reduces dataset from 444M to 923K (99.8%)
```

```sparql
# Query 2: Search by function using bif:contains (with split property path)
PREFIX up: <http://purl.uniprot.org/core/>

SELECT DISTINCT ?protein ?mnemonic ?fullName
WHERE {
  ?protein a up:Protein ;
           up:mnemonic ?mnemonic ;
           up:reviewed 1 ;
           up:recommendedName ?name .
  ?name up:fullName ?fullName .
  ?fullName bif:contains "'kinase' OR 'dna repair'"
}
LIMIT 15

# Expected results: Kinases and DNA repair proteins
# NOTE: Property path must be split - cannot use up:recommendedName/up:fullName with bif:contains
```

```sparql
# Query 3: Get functional annotations and GO terms
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT ?protein ?mnemonic ?functionComment ?goLabel
WHERE {
  VALUES ?protein { uniprot:P04637 uniprot:P17612 uniprot:P86925 }
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
LIMIT 20

# Expected results:
# P04637 (P53): Tumor suppressor function, GO terms for apoptosis, cell cycle
# P17612: cAMP-dependent protein kinase, GO terms for kinase activity
# P86925: RNA-editing ligase, mitochondrial GO terms
```

```sparql
# Query 4: Get protein sequences with molecular properties
PREFIX up: <http://purl.uniprot.org/core/>

SELECT DISTINCT ?protein ?mnemonic ?sequence ?mass ?checksum
WHERE {
  ?protein a up:Protein ;
           up:mnemonic ?mnemonic ;
           up:reviewed 1 ;
           up:sequence ?iso .
  ?iso rdf:value ?sequence ;
       up:mass ?mass ;
       up:md5Checksum ?checksum .
}
LIMIT 10

# Expected results: Canonical sequences with mass (in Daltons) and MD5 checksums
# Sequences are full amino acid strings, masses ~10,000-200,000 Da typically
```

```sparql
# Query 5: Count tumor suppressors (with bif:contains, split property path)
PREFIX up: <http://purl.uniprot.org/core/>

SELECT (COUNT(*) as ?count)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:annotation ?annot .
  ?annot rdfs:comment ?function .
  ?function bif:contains "'tumor suppressor'"
}

# Expected results: Count of expert-curated human tumor suppressors
# CRITICAL: up:reviewed 1 + organism filter prevents timeout
```

## Interesting Findings

### Specific Entities for Questions
1. **Q99ZW2** - SpCas9 (Streptococcus pyogenes) - Most commonly used Cas9 for genome editing
2. **P04637** - P53_HUMAN - Tumor suppressor p53, most studied human protein
3. **P17612** - KAPCA_HUMAN - cAMP-dependent protein kinase, extensively studied kinase
4. **P86925** - RLGM2_TRYB2 - RNA-editing ligase from Trypanosoma brucei
5. **J7RUA5** - SaCas9 (Staphylococcus aureus) - Alternative Cas9 variant

### Unique Properties
- **Quality distinction**: Swiss-Prot (reviewed=1) has 923K entries with expert curation vs TrEMBL (reviewed=0) with 444M automated annotations
- **Comprehensive cross-references**: Links to 200+ databases (PDB, EMBL, RefSeq, Ensembl, InterPro, Pfam, KEGG, Reactome, HGNC, STRING, etc.)
- **Multiple isoforms**: Canonical + alternative splice variants
- **Rich annotations**: Function, disease, subcellular location, tissue specificity, post-translational modifications
- **MD5 checksums**: Sequence integrity verification
- **Hierarchical taxonomy**: Complete organism lineage via rdfs:subClassOf

### Connections to Other Databases
- **Structure databases**: PDB (~14-25% reviewed), AlphaFold (>98% reviewed)
- **Sequence databases**: EMBL (~95%), RefSeq (~80%), Ensembl (high)
- **Gene databases**: HGNC (100% human), neXtProt (100% human), Gene IDs (~90%)
- **Protein families**: InterPro (>98%), Pfam (~85%), PANTHER (~80%)
- **Interactions**: IntAct (~16%), STRING (~85%), BioGRID (~25%)
- **Pathways**: KEGG (~95%), Reactome (~30%)
- **Ontologies**: Gene Ontology (>85% reviewed)
- **Taxonomy**: NCBI Taxonomy (100%)

### Specific, Verifiable Facts
- Total proteins: 444,565,015
- Reviewed (Swiss-Prot): 923,147 (0.2%)
- Human reviewed proteins: 40,209
- Reviewed with sequences: >99%
- Reviewed with function annotations: >90%
- Reviewed with GO terms: >85%
- Reviewed with PDB structures: ~14-25%
- Reviewed with AlphaFold structures: >98%
- Average isoforms per protein: 1.1
- Average PDB structures per protein: 4.8
- Average GO terms per protein: 12.5
- Average cross-references per protein: 45

## Question Opportunities by Category

### Precision
- "What is the UniProt accession for SpCas9 from Streptococcus pyogenes?"
- "What is the exact molecular mass of human p53 (P04637)?"
- "What is the MD5 checksum of the canonical sequence for Q99ZW2?"
- "What is the mnemonic (entry name) for UniProt ID P04637?"
- "What EC number is assigned to SpCas9?"

### Completeness
- "List all CRISPR-associated Cas9 proteins in UniProt"
- "How many reviewed human proteins are in Swiss-Prot?"
- "Count all kinases with PDB structures in reviewed entries"
- "List all GO terms associated with P04637 (p53)"
- "How many protein isoforms does P04637 have?"

### Integration
- "Convert UniProt ID Q99ZW2 to its PDB structure IDs"
- "Find the NCBI Gene ID for UniProt entry P04637"
- "Link UniProt P04637 to its KEGG pathway entries"
- "Find InterPro domain IDs for SpCas9 (Q99ZW2)"
- "Connect UniProt to Reactome pathways via rdfs:seeAlso"

### Currency
- "What proteins were recently added to Swiss-Prot (2024)?"
- "Find newly characterized proteins with AlphaFold structures"
- "What are the most recently updated human kinases in reviewed entries?"

### Specificity
- "What is the exact function annotation text for p53 tumor suppressor activity?"
- "Find proteins from Streptococcus pyogenes serotype M1 with endonuclease activity"
- "What is the subcellular location annotation for P04637?"
- "Find mitochondrial RNA-editing enzymes in Trypanosoma species"

### Structured Query
- "Find all reviewed human proteins with ('kinase' AND NOT 'tyrosine') in name AND PDB structures"
- "Query proteins with GO term for 'apoptosis' AND organism 'Homo sapiens' AND disease annotations"
- "Find enzymes (EC numbers) with both KEGG pathway links AND InterPro domain annotations"
- "Complex: reviewed human kinases with IC50 measurements in ChEMBL AND PDB structures in UniProt"

## Notes

### Limitations and Challenges
- **Critical performance issue**: Queries without `up:reviewed 1` filter timeout (444M vs 923K entries)
- **bif:contains limitation**: Cannot use with property paths - must split into separate triples
- **Variable annotation coverage**: Swiss-Prot >90% complete, TrEMBL 20-30%
- **Organism filtering**: Must use `up:organism` URI, NOT mnemonic text patterns
- **GO term coverage**: >85% for reviewed, ~30% for TrEMBL
- **PDB structure coverage**: ~14-25% reviewed, <1% TrEMBL

### Best Practices for Querying
1. **ALWAYS filter by reviewed=1 FIRST**: This is non-negotiable for performance and quality
2. **Split property paths with bif:contains**: Cannot use `up:recommendedName/up:fullName`, must split
3. **Use LIMIT**: 30-50 recommended for reviewed proteins
4. **Organism filtering**: Use `up:organism <http://purl.uniprot.org/taxonomy/TAXID>`, never mnemonic patterns
5. **OPTIONAL for cross-refs**: Wrap GO terms and database links in OPTIONAL if not required
6. **GO term filtering**: Use `FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))`
7. **COUNT queries**: Require `up:reviewed 1` + organism filter to prevent timeout
8. **bif:contains syntax**: Keywords in single quotes: `'keyword'`, boolean: `'word1' OR 'word2'`
9. **Sequence queries**: Sequences can be very long strings (thousands of characters)
10. **Cross-reference filtering**: Use CONTAINS(STR(?xref), "substring") for specific databases
