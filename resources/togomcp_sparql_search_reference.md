# TogoMCP SPARQL Keyword Search Reference
## Comprehensive Templates for 17 Databases

**Version:** 1.0  
**Last Updated:** December 2025  
**Purpose:** Universal SPARQL keyword search templates for TogoMCP databases lacking dedicated search tools

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Universal Template Pattern](#universal-template-pattern)
3. [Database-Specific Templates](#database-specific-templates)
4. [Best Practices](#best-practices)
5. [Common Patterns](#common-patterns)
6. [Troubleshooting](#troubleshooting)

---

## Quick Reference

### When to Use SPARQL vs Dedicated Tools

**✅ Use SPARQL Templates (17 databases):**
- Gene Ontology (GO)
- MONDO Disease Ontology
- Reactome Pathways
- Rhea Reactions
- NCBI Taxonomy
- NCBI Gene ⚠️ *requires organism filter*
- NANDO (Japanese Rare Diseases)
- Ensembl ⚠️ *requires organism filter*
- ChEBI
- BacDive
- ClinVar
- MedGen ⚠️ *relationships via MGREL*
- PubChem ⚠️ *requires specific filters*
- DDBJ
- GlyCosmos ⚠️ *must specify graph*
- MediaDive
- PubTator ⚠️ *join with PubMed for keywords*

**🔧 Use Dedicated Search Tools:**
- ChEMBL → `search_chembl_molecule`, `search_chembl_target`
- MeSH → `search_mesh_entity`
- PDB → `search_pdb_entity`
- UniProt → `search_uniprot_entity`
- PubMed → `PubMed:search_articles`

---

## Universal Template Pattern

### Core Structure

```sparql
PREFIX [prefix]: <[uri]>

SELECT DISTINCT 
    ?entity 
    ?label
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <[graph_uri]>
WHERE {
  # Core entity
  ?entity a [EntityClass] ;
          [labelProperty] ?label .
  
  # CRITICAL FILTERS (database-specific)
  [criticalFilter]
  
  # Multi-property search with bif:contains
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?entity [property2] ?text2 .
    ?text2 bif:contains "'KEYWORD'" option (score ?sc2) .
  }
}
GROUP BY ?entity ?label
ORDER BY DESC(?totalScore)
LIMIT 50
```

### Universal Rules

1. **Always use bif:contains** - 10-100x faster than FILTER(CONTAINS())
2. **Always include FROM clause** - Specifies graph, essential for performance
3. **Always use DISTINCT** - Avoids duplicates from multiple graph storage
4. **Always add LIMIT** - Prevents timeouts (20-50 typical)
5. **Score variable naming** - Use `?sc`, `?sc1`, `?sc2` (never `?score` - reserved)
6. **COALESCE for scoring** - Handles NULL scores properly
7. **Split property paths** - Never combine property paths with bif:contains

### Boolean Search Operators

```sparql
# AND
?text bif:contains "'keyword1' AND 'keyword2'"

# OR
?text bif:contains "'keyword1' OR 'keyword2'"

# NOT
?text bif:contains "'keyword' AND NOT 'exclude'"

# Complex
?text bif:contains "('word1' OR 'word2') AND 'word3' AND NOT 'word4'"

# Wildcards
?text bif:contains "'kinase*'"  # Matches kinase, kinases, phosphokinase
```

---

## Database-Specific Templates

---

### 1. Gene Ontology (GO)

**Purpose:** Biological terms, molecular functions, biological processes, cellular components  
**Graph:** `<http://rdfportal.org/ontology/go>`  
**Entity Class:** `owl:Class`

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboinowl: <http://oboInOwl#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT 
    ?go_term 
    ?label 
    ?namespace
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) + COALESCE(MAX(?sc3), 0) AS ?totalScore)
FROM <http://rdfportal.org/ontology/go>
WHERE {
  # Core entity
  ?go_term a owl:Class ;
           rdfs:label ?label ;
           oboinowl:hasOBONamespace ?namespace .
  
  # CRITICAL FILTER - Only GO terms
  FILTER(STRSTARTS(STR(?go_term), "http://purl.obolibrary.org/obo/GO_"))
  
  # Optional namespace filter
  # FILTER(STR(?namespace) = "molecular_function")  # or "biological_process", "cellular_component"
  
  # Multi-property search
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?go_term obo:IAO_0000115 ?definition .
    ?definition bif:contains "'KEYWORD'" option (score ?sc2) .
  } UNION {
    ?go_term oboinowl:hasExactSynonym ?synonym .
    ?synonym bif:contains "'KEYWORD'" option (score ?sc3) .
  }
}
GROUP BY ?go_term ?label ?namespace
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Term names (e.g., "protein kinase activity")
- `obo:IAO_0000115` - Definitions
- `oboinowl:hasExactSynonym` - Alternative names

**Search Examples:**
```sparql
# Find kinase activities
?label bif:contains "'kinase'"

# Find metabolic processes
?label bif:contains "'metabolic' AND 'process'"
# Add: FILTER(STR(?namespace) = "biological_process")
```

**Critical Notes:**
- Must use `STR()` for namespace comparison (datatype mismatch)
- Always filter by GO_ prefix to exclude other ontologies
- FROM clause essential (causes timeout without it)

---

### 2. MONDO Disease Ontology

**Purpose:** Disease classification and terminology  
**Graph:** `<http://rdfportal.org/ontology/mondo>`  
**Entity Class:** `owl:Class`

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX IAO: <http://purl.obolibrary.org/obo/IAO_>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT 
    ?disease 
    ?label
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) + COALESCE(MAX(?sc3), 0) AS ?totalScore)
FROM <http://rdfportal.org/ontology/mondo>
WHERE {
  # Core entity
  ?disease a owl:Class ;
           rdfs:label ?label .
  
  # Multi-property search
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?disease IAO:0000115 ?definition .
    ?definition bif:contains "'KEYWORD'" option (score ?sc2) .
  } UNION {
    ?disease oboInOwl:hasExactSynonym ?synonym .
    ?synonym bif:contains "'KEYWORD'" option (score ?sc3) .
  }
}
GROUP BY ?disease ?label
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Disease names
- `IAO:0000115` - Disease definitions
- `oboInOwl:hasExactSynonym` - Alternative disease names

**Hierarchy Navigation:**
```sparql
# Get parent diseases
?disease rdfs:subClassOf ?parent .
FILTER(isIRI(?parent))  # Exclude blank nodes
```

**Search Examples:**
```sparql
# Find diabetes types
?label bif:contains "'diabetes'"

# Find cancer subtypes
?label bif:contains "'cancer' OR 'carcinoma' OR 'neoplasm'"
```

---

### 3. Reactome Pathways

**Purpose:** Biological pathways (BioPAX Level 3)  
**Graph:** `<http://rdf.ebi.ac.uk/dataset/reactome>`  
**Entity Class:** `bp:Pathway`

```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT 
    ?pathway 
    ?displayName
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  # Core entity
  ?pathway a bp:Pathway ;
           bp:displayName ?displayName .
  
  # Multi-property search
  {
    ?displayName bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?pathway bp:comment ?comment .
    ?comment bif:contains "'KEYWORD'" option (score ?sc2) .
  }
}
GROUP BY ?pathway ?displayName
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `bp:displayName` - Pathway names
- `bp:comment` - Descriptions and citations

**Cross-References (CRITICAL - requires ^^xsd:string):**
```sparql
# Get UniProt cross-references
?pathway bp:xref ?xref .
?xref bp:db "UniProt"^^xsd:string ;
      bp:id ?uniprot_id .
```

**Search Examples:**
```sparql
# Find signaling pathways
?displayName bif:contains "'signaling'"

# Find cancer-related pathways
?displayName bif:contains "'cancer' OR 'oncogene' OR 'tumor'"
```

---

### 4. Rhea Biochemical Reactions

**Purpose:** Biochemical reactions  
**Graph:** `<http://rdfportal.org/dataset/rhea>`  
**Entity Class:** `rdfs:subClassOf rhea:Reaction`

```sparql
PREFIX rhea: <http://rdf.rhea-db.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT 
    ?reaction 
    ?label 
    ?equation
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdfportal.org/dataset/rhea>
WHERE {
  # Core entity
  ?reaction rdfs:subClassOf rhea:Reaction ;
            rdfs:label ?label .
  
  # CRITICAL FILTER - Only approved reactions
  ?reaction rhea:status rhea:Approved .
  
  # Optional equation
  OPTIONAL { ?reaction rhea:equation ?equation }
  
  # Multi-property search
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?reaction rhea:equation ?eq .
    ?eq bif:contains "'KEYWORD'" option (score ?sc2) .
  }
}
GROUP BY ?reaction ?label ?equation
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Reaction summary
- `rhea:equation` - Text equation (e.g., "H2O + ATP = ADP + phosphate")

**Additional Filters:**
```sparql
# Transport reactions only
?reaction rhea:isTransport 1 .

# Filter by EC number
?reaction rhea:ec ?ec_number .
FILTER(?ec_number = "2.7.11.1")  # Protein kinases
```

**Search Examples:**
```sparql
# Find ATP-dependent reactions
?eq bif:contains "'ATP'"

# Find kinase reactions
?label bif:contains "'kinase'"
```

---

### 5. NCBI Taxonomy

**Purpose:** Organism classification (3M+ taxa)  
**Graph:** `<http://rdfportal.org/ontology/taxonomy>`  
**Entity Class:** `tax:Taxon`

```sparql
PREFIX tax: <http://ddbj.nig.ac.jp/ontologies/taxonomy/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT 
    ?taxon 
    ?label 
    ?scientificName 
    ?commonName 
    ?rank
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) + COALESCE(MAX(?sc3), 0) AS ?totalScore)
FROM <http://rdfportal.org/ontology/taxonomy>
WHERE {
  # Core entity
  ?taxon a tax:Taxon ;
         rdfs:label ?label .
  
  # Optional properties
  OPTIONAL { ?taxon tax:scientificName ?scientificName }
  OPTIONAL { ?taxon tax:commonName ?commonName }
  OPTIONAL { ?taxon tax:rank ?rank }
  
  # Multi-property search
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?taxon tax:scientificName ?sciName .
    ?sciName bif:contains "'KEYWORD'" option (score ?sc2) .
  } UNION {
    ?taxon tax:commonName ?comName .
    ?comName bif:contains "'KEYWORD'" option (score ?sc3) .
  }
}
GROUP BY ?taxon ?label ?scientificName ?commonName ?rank
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Primary taxon label
- `tax:scientificName` - Scientific name (e.g., "Homo sapiens")
- `tax:commonName` - Common name (e.g., "human")

**Filter by Rank:**
```sparql
FILTER(?rank = tax:Species)  # or tax:Genus, tax:Family, tax:Order
```

**Search Examples:**
```sparql
# Find Escherichia species
?sciName bif:contains "'Escherichia'"

# Find primates
?label bif:contains "'primate*'"
```

---

### 6. NCBI Gene

**Purpose:** Gene database (57M+ entries)  
**Graph:** `<http://rdfportal.org/dataset/ncbigene>`  
**Entity Class:** `insdc:Gene`

```sparql
PREFIX insdc: <http://ddbj.nig.ac.jp/ontologies/sequence#>
PREFIX ncbio: <http://rdfportal.org/ontology/ncbigene#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT 
    ?gene 
    ?symbol 
    ?description
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) + COALESCE(MAX(?sc3), 0) AS ?totalScore)
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  # Core entity
  ?gene a insdc:Gene ;
        rdfs:label ?symbol .
  
  # ⚠️ CRITICAL FILTER - MUST filter by organism (57M+ genes!)
  ?gene ncbio:taxid <http://identifiers.org/taxonomy/9606> .  # Human
  
  # Optional properties
  OPTIONAL { ?gene dct:description ?description }
  
  # Multi-property search
  {
    ?symbol bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?gene dct:description ?desc .
    ?desc bif:contains "'KEYWORD'" option (score ?sc2) .
  } UNION {
    ?gene insdc:gene_synonym ?synonym .
    ?synonym bif:contains "'KEYWORD'" option (score ?sc3) .
  }
}
GROUP BY ?gene ?symbol ?description
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Gene symbol (e.g., "INS", "BRCA1")
- `dct:description` - Full gene name (e.g., "insulin")
- `insdc:gene_synonym` - Alternative gene symbols

**Common Organisms:**
```sparql
# Human
<http://identifiers.org/taxonomy/9606>

# Mouse
<http://identifiers.org/taxonomy/10090>

# Rat
<http://identifiers.org/taxonomy/10116>

# Zebrafish
<http://identifiers.org/taxonomy/7955>
```

**Filter by Type:**
```sparql
?gene ncbio:type ?type .
FILTER(?type = "protein-coding")  # or "ncRNA", "tRNA", "rRNA", "pseudo"
```

**⚠️ CRITICAL:** Always filter by organism first - without this filter, queries timeout on 57M+ genes!

**Search Examples:**
```sparql
# Find insulin genes (human)
?symbol bif:contains "'insulin'" OR ?desc bif:contains "'insulin'"

# Find kinase genes (mouse)
?desc bif:contains "'kinase'"
# Change taxid to 10090
```

---

### 7. NANDO (Japanese Rare Diseases)

**Purpose:** Japanese rare diseases (multilingual)  
**Graph:** `<http://nanbyodata.jp/ontology/nando>`  
**Entity Class:** `owl:Class`

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX nando: <http://nanbyodata.jp/ontology/nando#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT 
    ?disease 
    ?label_en 
    ?label_ja 
    ?notification_number
    ?sc
FROM <http://nanbyodata.jp/ontology/nando>
WHERE {
  # Core entity
  ?disease a owl:Class .
  
  # Multilingual labels
  OPTIONAL { 
    ?disease rdfs:label ?label_en .
    FILTER(LANG(?label_en) = "en")
  }
  OPTIONAL { 
    ?disease rdfs:label ?label_ja .
    FILTER(LANG(?label_ja) = "ja" && !REGEX(STR(?label_ja), "^[ぁ-ん]+$"))
  }
  
  # Optional notification number (government-designated diseases)
  OPTIONAL { ?disease nando:hasNotificationNumber ?notification_number }
  
  # Search in any language
  ?disease rdfs:label ?search_label .
  ?search_label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` with language tags (@en, @ja, @ja-hira)

**Language Filters:**
```sparql
# English only
FILTER(LANG(?label_en) = "en")

# Japanese kanji (not hiragana)
FILTER(LANG(?label_ja) = "ja" && !REGEX(STR(?label_ja), "^[ぁ-ん]+$"))

# Japanese hiragana
FILTER(REGEX(STR(?label_ja_hira), "^[ぁ-ん]+$"))
```

**Filter Designated Diseases:**
```sparql
FILTER(BOUND(?notification_number))
```

**Search Examples:**
```sparql
# Find Parkinson's disease (matches English and Japanese)
?search_label bif:contains "'Parkinson*'"
# Also matches: パーキンソン病 (Japanese)

# Find muscular dystrophies
?search_label bif:contains "'muscular' AND 'dystrophy'"
```

---

### 8. Ensembl Genomic Features

**Purpose:** Genomic features (100+ species)  
**Graph:** `<http://rdfportal.org/dataset/ensembl>`  
**Entity Class:** `terms:EnsemblGene`

```sparql
PREFIX terms: <http://rdf.ebi.ac.uk/terms/ensembl/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT 
    ?gene 
    ?symbol 
    ?description
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdfportal.org/dataset/ensembl>
WHERE {
  # Core entity
  ?gene a terms:EnsemblGene ;
        rdfs:label ?symbol .
  
  # ⚠️ CRITICAL FILTER - MUST filter by organism
  ?gene obo:RO_0002162 <http://identifiers.org/taxonomy/9606> .  # Human
  
  # Optional description
  OPTIONAL { ?gene dcterms:description ?description }
  
  # Multi-property search
  {
    ?symbol bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?gene dcterms:description ?desc .
    ?desc bif:contains "'KEYWORD'" option (score ?sc2) .
  }
}
GROUP BY ?gene ?symbol ?description
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Gene symbol (e.g., "BRCA1", "TP53")
- `dcterms:description` - Full description

**Common Organisms:**
```sparql
# Human (Homo sapiens)
<http://identifiers.org/taxonomy/9606>

# Mouse (Mus musculus)
<http://identifiers.org/taxonomy/10090>

# Zebrafish (Danio rerio)
<http://identifiers.org/taxonomy/7955>
```

**Filter by Chromosome:**
```sparql
?gene terms:has_location ?location .
?location rdfs:label ?chr .
FILTER(CONTAINS(STR(?chr), "GRCh38/17"))  # Chromosome 17
```

**Filter by Biotype:**
```sparql
?gene terms:has_biotype <http://ensembl.org/glossary/ENSGLOSSARY_0000026> .  # protein-coding
```

**Search Examples:**
```sparql
# Find BRCA genes
?symbol bif:contains "'BRCA*'"

# Find kinase genes
?desc bif:contains "'kinase'"
```

---

### 9. ChEBI Chemical Compounds

**Purpose:** Chemical entities  
**Graph:** `<http://rdf.ebi.ac.uk/dataset/chebi>`  
**Entity Class:** `owl:Class`

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT 
    ?compound 
    ?label
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  # Core entity
  ?compound a owl:Class ;
            rdfs:label ?label .
  
  # CRITICAL FILTER - Only ChEBI compounds
  FILTER(STRSTARTS(STR(?compound), "http://purl.obolibrary.org/obo/CHEBI_"))
  
  # Multi-property search
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?compound oboInOwl:hasRelatedSynonym ?synonym .
    ?synonym bif:contains "'KEYWORD'" option (score ?sc2) .
  }
}
GROUP BY ?compound ?label
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Primary chemical name
- `oboInOwl:hasRelatedSynonym` - Alternative names

**Search Examples:**
```sparql
# Find glucose derivatives
?label bif:contains "'glucose'"

# Find amino acids
?label bif:contains "'amino' AND 'acid'"
```

---

### 10. BacDive Bacterial Strains

**Purpose:** Bacterial strains  
**Graph:** `<http://rdfportal.org/dataset/bacdive>`  
**Entity Class:** `schema:Strain`

```sparql
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT 
    ?strain 
    ?label 
    ?description
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
FROM <http://rdfportal.org/dataset/bacdive>
WHERE {
  # Core entity
  ?strain a schema:Strain ;
          rdfs:label ?label .
  
  # Optional description
  OPTIONAL { ?strain dct:description ?description }
  
  # Multi-property search
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
  } UNION {
    ?strain dct:description ?desc .
    ?desc bif:contains "'KEYWORD'" option (score ?sc2) .
  }
}
GROUP BY ?strain ?label ?description
ORDER BY DESC(?totalScore)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Strain designation
- `dct:description` - Strain characteristics

**Search Examples:**
```sparql
# Find Bacillus strains
?label bif:contains "'Bacillus'"

# Find psychrophilic strains
?desc bif:contains "'psychrophil*'"
```

---

### 11. ClinVar Genetic Variants

**Purpose:** Genetic variants and clinical interpretations  
**Graph:** `<http://rdfportal.org/dataset/clinvar>`  
**Entity Class:** `cvo:VariationArchiveType`

```sparql
PREFIX cvo: <http://purl.jp/bio/10/clinvar/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT 
    ?variant 
    ?accession 
    ?label 
    ?type 
    ?status
    ?sc
FROM <http://rdfportal.org/dataset/clinvar>
WHERE {
  # Core entity
  ?variant a cvo:VariationArchiveType ;
           rdfs:label ?label ;
           cvo:accession ?accession ;
           cvo:variation_type ?type ;
           cvo:record_status ?status .
  
  # CRITICAL FILTER - Only current records
  FILTER(?status = "current")
  
  # Search in variant labels (gene symbols, coordinates)
  ?label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Variant nomenclature (e.g., "NM_007294.4(BRCA1):c.2244dup")

**Get Clinical Significance:**
```sparql
OPTIONAL {
  ?variant cvo:classified_record ?classrec .
  ?classrec cvo:classifications/cvo:germline_classification/cvo:description ?significance .
}
```

**Filter by Variation Type:**
```sparql
FILTER(?type = "single nucleotide variant")  # or "Duplication", "Deletion"
```

**Search Examples:**
```sparql
# Find BRCA1 variants
?label bif:contains "'BRCA1'"

# Find TP53 variants
?label bif:contains "'TP53'"
```

---

### 12. MedGen Medical Genetics

**Purpose:** Medical genetics concepts (233K+ concepts)  
**Graph:** `<http://rdfportal.org/dataset/medgen>`  
**Entity Class:** `mo:ConceptID`

```sparql
PREFIX mo: <http://med2rdf/ontology/medgen#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT 
    ?concept 
    ?cui 
    ?label 
    ?definition
    ?sc
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  # Core entity
  ?concept a mo:ConceptID ;
           dct:identifier ?cui ;
           rdfs:label ?label .
  
  # Optional definition
  OPTIONAL { ?concept skos:definition ?definition }
  
  # Search in labels
  ?label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Disease/phenotype names (e.g., "Acute myeloid leukemia")

**⚠️ CRITICAL - Relationships via MGREL:**
```sparql
# Relationships are NOT direct properties on ConceptID!
# They are stored in separate MGREL entities:

SELECT ?concept1 ?concept2 ?relationship_type
FROM <http://rdfportal.org/dataset/medgen>
WHERE {
  ?rel a mo:MGREL ;
       mo:cui1 ?concept1 ;
       mo:cui2 ?concept2 ;
       mo:rela ?relationship_type .
  
  # Filter by relationship type
  FILTER(CONTAINS(LCASE(?relationship_type), "gene"))
}
LIMIT 100
```

**Common Relationship Types:**
- `"isa"` - Child-to-parent
- `"inverse_isa"` - Parent-to-child
- `"has_manifestation"` - Disease to phenotype
- `"manifestation_of"` - Phenotype to disease

**Search Examples:**
```sparql
# Find diabetes concepts
?label bif:contains "'diabetes'"

# Find cardiomyopathy concepts
?label bif:contains "'cardiomyopathy'"
```

---

### 13. PubChem Chemical Compounds

**Purpose:** Chemical compounds (119M+ compounds)  
**Graph:** `<http://rdf.ncbi.nlm.nih.gov/pubchem/compound>`  
**Entity Class:** `vocab:Compound`

```sparql
PREFIX vocab: <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#>
PREFIX sio: <http://semanticscience.org/resource/>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT DISTINCT 
    ?compound 
    ?cid
    ?formula 
    ?weight
FROM <http://rdf.ncbi.nlm.nih.gov/pubchem/compound>
WHERE {
  # Core entity
  ?compound a vocab:Compound .
  
  # ⚠️ CRITICAL - Use specific filters (119M+ compounds!)
  
  # Get CID from URI
  BIND(REPLACE(STR(?compound), "^.*/CID", "") AS ?cid)
  
  # Get molecular descriptors
  OPTIONAL {
    ?compound sio:SIO_000008 ?formulaDesc .
    ?formulaDesc a sio:CHEMINF_000335 ;
                 sio:SIO_000300 ?formula .
  }
  OPTIONAL {
    ?compound sio:SIO_000008 ?weightDesc .
    ?weightDesc a sio:CHEMINF_000334 ;
                 sio:SIO_000300 ?weight .
  }
  
  # Filter by molecular weight range (REQUIRED for large searches)
  FILTER(?weight >= 100 && ?weight <= 500)
}
LIMIT 50
```

**⚠️ CRITICAL NOTES:**
- PubChem has 119M+ compounds - **always use specific filters**
- No direct keyword search on compound names
- Use CID directly if known: `compound:CID2244`
- Use molecular weight, formula, or classification filters

**Filter by Drug Role:**
```sparql
?compound obo:RO_0000087 vocab:FDAApprovedDrugs .
```

**Filter by ChEBI Classification:**
```sparql
?compound a ?chebiClass .
FILTER(STRSTARTS(STR(?chebiClass), "http://purl.obolibrary.org/obo/CHEBI_"))
```

**Search by Molecular Weight Range:**
```sparql
# Low molecular weight drugs (150-300)
FILTER(?weight >= 150 && ?weight <= 300)

# Larger molecules (500-1000)
FILTER(?weight >= 500 && ?weight <= 1000)
```

---

### 14. DDBJ DNA Sequences

**Purpose:** DNA sequences with genomic annotations  
**Graph:** `<http://rdfportal.org/dataset/ddbj>`  
**Entity Class:** `nuc:Entry`

```sparql
PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT 
    ?entry 
    ?identifier 
    ?organism 
    ?sc
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  # Core entity
  ?entry a nuc:Entry ;
         dcterms:identifier ?identifier ;
         nuc:organism ?organism .
  
  # Search organism names using bif:contains
  ?organism bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Properties Searched:**
- `nuc:organism` - Organism name (e.g., "Escherichia coli", "Homo sapiens")

**⚠️ CRITICAL - Product Searches Within Entry:**
```sparql
# NEVER search products without entry filter - causes timeout!
# Instead, filter by entry first:

SELECT ?locus_tag ?product
FROM <http://rdfportal.org/dataset/ddbj>
WHERE {
  ?cds a nuc:Coding_Sequence ;
       nuc:locus_tag ?locus_tag ;
       nuc:product ?product .
  
  # REQUIRED: Filter by specific entry
  FILTER(CONTAINS(STR(?cds), "CP036276.1"))
  
  # Then search products
  FILTER(CONTAINS(LCASE(?product), "protease"))
}
LIMIT 50
```

**Usage Pattern:**
1. Use `bif:contains` for organism search at entry level
2. Use `FILTER CONTAINS` for product searches within entries
3. Always filter by entry ID before querying features

**Search Examples:**
```sparql
# Find Escherichia coli entries
?organism bif:contains "'escherichia' AND 'coli'"

# Find Bacillus entries
?organism bif:contains "'bacillus'"
```

---

### 15. GlyCosmos Glycoscience

**Purpose:** Glycan structures, glycoproteins, glycosylation  
**Graphs:** Multiple (100+ graphs)  
**Entity Classes:** Various

```sparql
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT 
    ?epitope 
    ?label 
    ?altLabel
    ?sc
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  # Core entity - Glycan epitopes
  ?epitope a glycan:Glycan_epitope ;
           rdfs:label ?label .
  
  # Optional alternative labels
  OPTIONAL { ?epitope skos:altLabel ?altLabel }
  
  # Search in labels
  ?label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

**⚠️ CRITICAL - Must Specify Graph:**
- Different entity types in different graphs
- FROM clause essential (10-100x faster)

**Graph Selection:**
```sparql
# Epitopes
FROM <http://rdf.glycoinfo.org/glycoepitope>

# Proteins
FROM <http://rdf.glycosmos.org/glycoprotein>

# Genes
FROM <http://rdf.glycosmos.org/glycogenes>
```

**Search Glycoproteins:**
```sparql
SELECT ?protein ?label
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           rdfs:label ?label ;
           glycan:has_taxon <http://identifiers.org/taxonomy/9606> .  # Human
  ?label bif:contains "'KEYWORD'" option (score ?sc) .
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Important Notes:**
- 100+ named graphs - FROM clause mandatory
- Labels have low coverage: glycans <1%, proteins 17%, genes 32%
- Use GlyTouCan IDs for glycans (not labels)
- Always filter by taxon for glycoproteins

**Search Examples:**
```sparql
# Find Lewis epitopes
?label bif:contains "'Lewis'"

# Find blood group epitopes
?label bif:contains "'blood' AND 'group'"
```

---

### 16. MediaDive Culture Media

**Purpose:** Microbial culture media (3,289 media)  
**Graph:** `<http://rdfportal.org/dataset/mediadive>`  
**Entity Class:** `schema:CultureMedium`

```sparql
PREFIX schema: <https://purl.dsmz.de/schema/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT 
    ?medium 
    ?label 
    ?group 
    ?ph
    ?sc
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  # Core entity
  ?medium a schema:CultureMedium ;
          rdfs:label ?label ;
          schema:belongsToGroup ?group .
  
  # Optional pH
  OPTIONAL { ?medium schema:hasFinalPH ?ph }
  
  # Search in labels and groups
  {
    ?label bif:contains "'KEYWORD'" option (score ?sc1) .
    BIND(?sc1 as ?sc)
  } UNION {
    ?group bif:contains "'KEYWORD'" option (score ?sc2) .
    BIND(?sc2 as ?sc)
  }
}
ORDER BY DESC(?sc)
LIMIT 50
```

**Properties Searched:**
- `rdfs:label` - Medium names (e.g., "Marine Broth", "LB Medium")
- `schema:belongsToGroup` - Medium groups/categories

**Search by Growth Conditions:**
```sparql
# Find thermophilic organism media
SELECT ?medium ?strain ?temp
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?growth a schema:GrowthCondition ;
          schema:partOfMedium ?medium ;
          schema:relatedToStrain ?strain ;
          schema:growthTemperature ?temp .
  FILTER(?temp > 45)
}
LIMIT 20
```

**Search Ingredients:**
```sparql
# Find media containing specific ingredient
SELECT ?medium ?ingredient
FROM <http://rdfportal.org/dataset/mediadive>
WHERE {
  ?composition schema:containsIngredient ?ingredient ;
               schema:partOfMedium ?medium .
  ?ingredient rdfs:label ?ingredientLabel .
  ?ingredientLabel bif:contains "'glucose'" .
}
LIMIT 50
```

**Search Examples:**
```sparql
# Find marine media
?label bif:contains "'marine'"

# Find anaerobic media
?group bif:contains "'anaerobic'"
```

---

### 17. PubTator Literature Annotations

**Purpose:** Literature annotations (10M+ annotations)  
**Graph:** `<http://rdfportal.org/dataset/pubtator_central>`  
**Entity Class:** `oa:Annotation`

```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX mesh: <http://identifiers.org/mesh/>

SELECT DISTINCT 
    ?diseaseId 
    (COUNT(DISTINCT ?article) AS ?articleCount)
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  # Disease annotations
  ?ann a oa:Annotation ;
       dcterms:subject "Disease" ;
       oa:hasBody ?diseaseId ;
       oa:hasTarget ?article .
  
  # Filter by specific disease (use MeSH ID)
  FILTER(?diseaseId = mesh:D003920)  # Diabetes Mellitus
}
GROUP BY ?diseaseId
LIMIT 50
```

**⚠️ CRITICAL - No Direct Keyword Search:**
To search by keyword, join with PubMed graph:

```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?ann ?diseaseId ?title
FROM <http://rdfportal.org/dataset/pubtator_central>
FROM <http://rdfportal.org/dataset/pubmed>
WHERE {
  # Get annotations
  ?ann dcterms:subject "Disease" ;
       oa:hasBody ?diseaseId ;
       oa:hasTarget ?article .
  
  # Search article titles in PubMed
  ?article dct:title ?title .
  ?title bif:contains "'cancer'" .
}
LIMIT 100
```

**Gene-Disease Co-mentions:**
```sparql
SELECT DISTINCT ?article ?geneId ?diseaseId
FROM <http://rdfportal.org/dataset/pubtator_central>
WHERE {
  ?geneAnn dcterms:subject "Gene" ;
           oa:hasBody ?geneId ;
           oa:hasTarget ?article .
  ?diseaseAnn dcterms:subject "Disease" ;
              oa:hasBody mesh:D000544 ;  # Alzheimer Disease
              oa:hasTarget ?article .
}
LIMIT 100
```

**Important Notes:**
- 10M+ annotations - always use LIMIT
- Entity types: "Disease" (majority), "Gene" (substantial)
- For keyword search, use `PubMed:search_articles` tool instead
- PubTator is for entity-article relationships, not keyword search

---

## Best Practices

### 1. Performance Optimization

**Always Include FROM Clause:**
```sparql
# Good
FROM <http://rdfportal.org/dataset/database>

# Bad - may timeout or return incomplete results
# (no FROM clause)
```

**Use LIMIT Liberally:**
```sparql
# Exploratory queries
LIMIT 20-50

# Production queries with specific filters
LIMIT 100-500
```

**Filter Early:**
```sparql
# Good - filter first, then search
?entity a EntityClass ;
        property ?value .
FILTER(?specificCondition)
?value bif:contains "'keyword'" .

# Bad - search first, filter later (slower)
?entity property ?value .
?value bif:contains "'keyword'" .
FILTER(?specificCondition)
```

### 2. Score Aggregation

**Use COALESCE for NULL Scores:**
```sparql
# Correct
(COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)

# Wrong - NULL scores cause issues
(MAX(?sc1) + MAX(?sc2) AS ?totalScore)
```

**Never Use ?score as Variable Name:**
```sparql
# Correct
option (score ?sc)

# Wrong - ?score is reserved in Virtuoso
option (score ?score)
```

### 3. Property Paths with bif:contains

**Split Property Paths:**
```sparql
# Wrong - doesn't work
?entity prop/subprop ?text .
?text bif:contains "'keyword'" .

# Correct - split the path
?entity prop ?intermediate .
?intermediate subprop ?text .
?text bif:contains "'keyword'" .
```

### 4. OPTIONAL for Sparse Data

**Use OPTIONAL for Properties That May Not Exist:**
```sparql
# Required property
?entity rdfs:label ?label .

# Optional properties
OPTIONAL { ?entity dct:description ?description }
OPTIONAL { ?entity skos:definition ?definition }
```

### 5. Database-Specific Filters

**NCBI Gene & Ensembl - Organism Filter:**
```sparql
# CRITICAL - always filter by organism
?gene ncbio:taxid <http://identifiers.org/taxonomy/9606> .
```

**GO - Prefix Filter:**
```sparql
# CRITICAL - only GO terms
FILTER(STRSTARTS(STR(?go_term), "http://purl.obolibrary.org/obo/GO_"))
```

**ClinVar - Status Filter:**
```sparql
# Only current records
FILTER(?status = "current")
```

**Rhea - Approved Filter:**
```sparql
# Only approved reactions
?reaction rhea:status rhea:Approved .
```

---

## Common Patterns

### Multi-Property Search with Scoring

```sparql
SELECT DISTINCT ?entity ?label
    (COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) + COALESCE(MAX(?sc3), 0) AS ?totalScore)
WHERE {
  # Property 1
  {
    ?entity property1 ?text1 .
    ?text1 bif:contains "'keyword'" option (score ?sc1) .
  }
  # Property 2
  UNION {
    ?entity property2 ?text2 .
    ?text2 bif:contains "'keyword'" option (score ?sc2) .
  }
  # Property 3
  UNION {
    ?entity property3 ?text3 .
    ?text3 bif:contains "'keyword'" option (score ?sc3) .
  }
}
GROUP BY ?entity ?label
ORDER BY DESC(?totalScore)
LIMIT 50
```

### Language-Specific Search (NANDO)

```sparql
SELECT DISTINCT ?entity ?label_en ?label_ja
WHERE {
  # Get multilingual labels
  OPTIONAL {
    ?entity rdfs:label ?label_en .
    FILTER(LANG(?label_en) = "en")
  }
  OPTIONAL {
    ?entity rdfs:label ?label_ja .
    FILTER(LANG(?label_ja) = "ja")
  }
  
  # Search in any language
  ?entity rdfs:label ?searchLabel .
  ?searchLabel bif:contains "'keyword'" .
}
LIMIT 50
```

### Hierarchical Navigation (MONDO, GO)

```sparql
# Get parent terms
SELECT ?entity ?label ?parent ?parentLabel
WHERE {
  ?entity rdfs:label ?label .
  ?entity rdfs:subClassOf ?parent .
  ?parent rdfs:label ?parentLabel .
  FILTER(isIRI(?parent))  # Exclude blank nodes
  ?label bif:contains "'keyword'" .
}
LIMIT 50
```

### Cross-Reference Retrieval

```sparql
# Get external database links
SELECT ?entity ?label ?externalDB
WHERE {
  ?entity rdfs:label ?label ;
          rdfs:seeAlso ?externalDB .
  ?label bif:contains "'keyword'" .
  FILTER(CONTAINS(STR(?externalDB), "uniprot"))
}
LIMIT 50
```

---

## Troubleshooting

### Query Timeouts

**Symptoms:** Query runs indefinitely or returns timeout error

**Solutions:**
1. Add LIMIT clause (start with 20-50)
2. Add FROM clause with specific graph
3. Add early filters (organism, type, status)
4. Use more specific keywords
5. Break into smaller queries

**Example Fix:**
```sparql
# Before - timeout
SELECT ?gene ?label
WHERE { ?gene rdfs:label ?label }

# After - works
SELECT ?gene ?label
FROM <http://rdfportal.org/dataset/ncbigene>
WHERE {
  ?gene a insdc:Gene ;
        rdfs:label ?label ;
        ncbio:taxid <http://identifiers.org/taxonomy/9606> .
}
LIMIT 50
```

### Empty Results

**Symptoms:** Query returns no results when results expected

**Solutions:**
1. Check FROM clause - correct graph URI?
2. Check FILTER conditions - too restrictive?
3. Use OPTIONAL for sparse properties
4. Check bif:contains syntax - keywords in single quotes?
5. Verify entity class - correct type?

**Example Fix:**
```sparql
# Before - empty results
SELECT ?entity ?label ?definition
WHERE {
  ?entity rdfs:label ?label ;
          skos:definition ?definition .
}

# After - returns results
SELECT ?entity ?label ?definition
WHERE {
  ?entity rdfs:label ?label .
  OPTIONAL { ?entity skos:definition ?definition }
}
```

### Duplicate Results

**Symptoms:** Same entity returned multiple times

**Solutions:**
1. Add SELECT DISTINCT
2. Use GROUP BY for aggregations
3. Check for multiple OPTIONAL blocks multiplying results
4. Reduce OPTIONAL blocks or use more specific filters

**Example Fix:**
```sparql
# Before - duplicates
SELECT ?entity ?label
WHERE {
  ?entity rdfs:label ?label .
  OPTIONAL { ?entity prop1 ?val1 }
  OPTIONAL { ?entity prop2 ?val2 }
}

# After - distinct results
SELECT DISTINCT ?entity ?label
WHERE {
  ?entity rdfs:label ?label .
  OPTIONAL { ?entity prop1 ?val1 }
  OPTIONAL { ?entity prop2 ?val2 }
}
```

### bif:contains Not Working

**Symptoms:** bif:contains returns empty or incorrect results

**Solutions:**
1. Check keyword syntax - must be in single quotes: `'keyword'`
2. Check boolean operators - use uppercase: `AND`, `OR`, `NOT`
3. Verify full-text index exists on property
4. Try FILTER(CONTAINS()) as fallback
5. Check for URI vs literal - bif:contains only works on literals

**Example Fix:**
```sparql
# Wrong
?label bif:contains "keyword"

# Correct
?label bif:contains "'keyword'"

# With boolean
?label bif:contains "'keyword1' AND 'keyword2'"
```

### Score Aggregation Issues

**Symptoms:** NULL scores or incorrect ranking

**Solutions:**
1. Use COALESCE to handle NULL scores
2. Check GROUP BY includes all non-aggregated variables
3. Verify score variable naming (?sc, not ?score)
4. Use MAX() before COALESCE

**Example Fix:**
```sparql
# Wrong
(MAX(?sc1) + MAX(?sc2) AS ?totalScore)

# Correct
(COALESCE(MAX(?sc1), 0) + COALESCE(MAX(?sc2), 0) AS ?totalScore)
```

---

## Special Cases

### MedGen Relationships

**CRITICAL:** Relationships are NOT direct properties - they're in MGREL entities:

```sparql
# Wrong - doesn't work
?disease mo:disease_has_associated_gene ?gene .

# Correct - use MGREL
?rel a mo:MGREL ;
     mo:cui1 ?disease ;
     mo:cui2 ?gene ;
     mo:rela ?rel_type .
FILTER(CONTAINS(LCASE(?rel_type), "gene"))
```

### DDBJ Entry-Level vs Feature-Level

**Entry-Level (Use bif:contains):**
```sparql
# Search organisms at entry level
?entry nuc:organism ?organism .
?organism bif:contains "'escherichia'"
```

**Feature-Level (Use FILTER CONTAINS):**
```sparql
# Search products within entry
?cds nuc:product ?product .
FILTER(CONTAINS(STR(?cds), "CP036276.1"))
FILTER(CONTAINS(LCASE(?product), "protease"))
```

### PubChem Filter Requirements

**Always use specific filters:**
```sparql
# Molecular weight range
FILTER(?weight >= 100 && ?weight <= 500)

# Drug classification
?compound obo:RO_0000087 vocab:FDAApprovedDrugs .

# ChEBI class
?compound a ?chebiClass .
FILTER(STRSTARTS(STR(?chebiClass), "http://purl.obolibrary.org/obo/CHEBI_"))
```

### GlyCosmos Graph Selection

**Must specify correct graph:**
```sparql
# Epitopes
FROM <http://rdf.glycoinfo.org/glycoepitope>

# Proteins (with taxon filter)
FROM <http://rdf.glycosmos.org/glycoprotein>
?protein glycan:has_taxon <http://identifiers.org/taxonomy/9606> .

# Genes
FROM <http://rdf.glycosmos.org/glycogenes>
```

---

## Quick Search Examples by Topic

### Find Human Genes
```sparql
# NCBI Gene
?gene ncbio:taxid <http://identifiers.org/taxonomy/9606> .
?gene rdfs:label ?symbol .
?symbol bif:contains "'BRCA*'"

# Ensembl
?gene obo:RO_0002162 <http://identifiers.org/taxonomy/9606> .
?gene rdfs:label ?symbol .
?symbol bif:contains "'BRCA*'"
```

### Find Diseases
```sparql
# MONDO
?disease a owl:Class ; rdfs:label ?label .
?label bif:contains "'diabetes'"

# MedGen
?concept a mo:ConceptID ; rdfs:label ?label .
?label bif:contains "'diabetes'"

# NANDO (Japanese)
?disease rdfs:label ?label .
?label bif:contains "'diabetes' OR 'パーキンソン'"
```

### Find Chemical Compounds
```sparql
# ChEBI
FILTER(STRSTARTS(STR(?compound), "http://purl.obolibrary.org/obo/CHEBI_"))
?compound rdfs:label ?label .
?label bif:contains "'glucose'"

# PubChem
?compound a vocab:Compound .
FILTER(?weight >= 150 && ?weight <= 300)
?compound obo:RO_0000087 vocab:FDAApprovedDrugs .
```

### Find Pathways
```sparql
# Reactome
?pathway a bp:Pathway ; bp:displayName ?name .
?name bif:contains "'signaling'"
```

### Find Organisms
```sparql
# NCBI Taxonomy
?taxon a tax:Taxon .
?taxon tax:scientificName ?sciName .
?sciName bif:contains "'Escherichia'"
FILTER(?rank = tax:Species)

# DDBJ
?entry a nuc:Entry ; nuc:organism ?organism .
?organism bif:contains "'escherichia' AND 'coli'"
```

---

## Version History

**v1.0** (December 2025)
- Initial comprehensive reference
- 17 database templates
- Complete examples and best practices
- Troubleshooting guide

---

## Credits

**Created for:** TogoMCP SPARQL keyword search operations  
**Data Sources:** MIE files from RDF Portal databases  
**Endpoint:** https://rdfportal.org/  
**Backend:** Virtuoso (supports bif:contains full-text search)

---

## Quick Reference Card

| Database | Must Filter By | Graph Required | Special Notes |
|----------|---------------|----------------|---------------|
| GO | GO_ prefix | Yes | Use STR() for namespace |
| MONDO | - | Yes | - |
| Reactome | - | Yes | Use ^^xsd:string for xrefs |
| Rhea | status=Approved | Yes | - |
| Taxonomy | - | Yes | - |
| NCBI Gene | **ORGANISM** | Yes | 57M+ genes |
| NANDO | - | Yes | Multilingual |
| Ensembl | **ORGANISM** | Yes | 100+ species |
| ChEBI | CHEBI_ prefix | Yes | - |
| BacDive | - | Yes | - |
| ClinVar | status=current | Yes | - |
| MedGen | - | Yes | Relationships via MGREL! |
| PubChem | **MW/CLASS** | Yes | 119M+ compounds |
| DDBJ | Entry for features | Yes | Entry vs feature search |
| GlyCosmos | **GRAPH** | **CRITICAL** | 100+ graphs |
| MediaDive | - | Yes | - |
| PubTator | - | Yes | Join with PubMed |

---

**End of Reference Document**
