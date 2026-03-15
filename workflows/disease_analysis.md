# Multi-Scale Disease Pathophysiology Analysis Template

## 🎯 Purpose
This prompt template enables systematic analysis of **any disease** from molecular defects to clinical symptoms, using biomedical knowledge bases accessed via RDF Portal (TogoMCP), PubMed, and ontology services.

**Key Features:**
- **SPARQL-first approach**: Use structured queries for precise, comprehensive data retrieval
- **TogoID integration**: Seamlessly convert and link identifiers across 100+ databases
- **Multi-scale analysis**: Connect molecular mechanisms to clinical manifestations

---

## 📋 PROMPT TEMPLATE

Copy and customize the following prompt for your disease of interest:

---

```
# Multi-Scale Disease Analysis Request

## Disease Specification
**Disease Name:** [INSERT DISEASE NAME]
**Alternative Names/Synonyms:** [INSERT SYNONYMS IF KNOWN]
**Disease Ontology ID (if known):** [e.g., MONDO:0005015, DOID:9352, MeSH:D003920]

## Analysis Scope
Please analyze this disease across ALL of the following biological scales, building a comprehensive model of how molecular defects lead to clinical symptoms.

### CRITICAL: Use SPARQL Queries and TogoID APIs

For each analysis level, you MUST:

1. **Use SPARQL queries** to retrieve structured data from:
   - UniProt RDF (protein functions, disease annotations, GO terms)
   - Reactome RDF (pathway components, reactions, participants)
   - Other RDF databases as appropriate (ChEBI, PubChem, etc.)

2. **Use TogoID APIs** to:
   - Convert identifiers between databases (UniProt → NCBI Gene → Ensembl → PDB)
   - Link disease IDs across ontologies (MONDO → MeSH → DOID → HP)
   - Map proteins to drug targets (UniProt → ChEMBL Target)
   - Connect compounds across databases (ChEMBL → PubChem → DrugBank)

3. **Build an integrated knowledge graph** by linking entities through their identifiers

### 1. MOLECULAR LEVEL
- Identify key proteins involved (with UniProt IDs)
- **SPARQL**: Query UniProt for disease annotations, GO terms, protein functions
- **TogoID**: Convert UniProt → PDB (structures), UniProt → ChEMBL (drug targets)
- Describe genetic mutations/variants associated with the disease
- Explain protein structure-function relationships relevant to pathology

### 2. PATHWAY LEVEL  
- Map relevant signaling pathways (with Reactome IDs)
- **SPARQL**: Query Reactome for pathway components, reactions, and participants
- **TogoID**: Convert UniProt → Reactome pathways, link to GO biological processes
- Identify dysregulated metabolic pathways
- Describe protein-protein interaction networks affected

### 3. CELLULAR LEVEL
- Describe affected cell types and their dysfunction
- **SPARQL**: Query GO cellular components, UniProt subcellular locations
- Explain cellular processes disrupted (apoptosis, autophagy, etc.)
- Identify organelle-level pathology

### 4. TISSUE/ORGAN LEVEL
- Identify affected tissues and organs
- **TogoID**: Link to UBERON anatomical terms, disease phenotypes (HP)
- Describe histopathological changes
- Explain tissue-level disease progression patterns

### 5. CLINICAL LEVEL
- Describe clinical manifestations and symptoms
- **TogoID**: Convert MONDO → HP phenotypes, MONDO → MeSH, MONDO → OMIM
- Explain disease staging and progression
- Identify clinical biomarkers

### 6. TREATMENT MECHANISMS
- List approved drugs with mechanisms of action
- **TogoID**: Convert ChEMBL compound → PubChem → DrugBank
- **SPARQL**: Query ChEMBL for drug-target relationships
- Explain drug targets and their biological rationale
- Describe investigational therapies in development

## Required SPARQL Queries

### Query 1: Disease-Associated Proteins (UniProt)
```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?protein ?mnemonic ?fullName ?diseaseComment
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:mnemonic ?mnemonic ;
           up:recommendedName ?name ;
           up:annotation ?annot .
  ?name up:fullName ?fullName .
  ?annot a up:Disease_Annotation ;
         rdfs:comment ?diseaseComment .
  ?diseaseComment bif:contains "'[DISEASE_KEYWORD]'"
}
LIMIT 30
```

### Query 2: Protein GO Terms and Functions (UniProt)
```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT DISTINCT ?goLabel ?functionComment
WHERE {
  VALUES ?protein { uniprot:[UNIPROT_ID] }
  ?protein a up:Protein .
  OPTIONAL {
    ?protein up:classifiedWith ?goTerm .
    ?goTerm rdfs:label ?goLabel .
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
  }
  OPTIONAL {
    ?protein up:annotation ?annot .
    ?annot a up:Function_Annotation ;
           rdfs:comment ?functionComment .
  }
}
LIMIT 50
```

### Query 3: Pathway Search (Reactome)
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT DISTINCT ?pathway ?name ?comment
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:displayName ?name .
  OPTIONAL { ?pathway bp:comment ?comment }
  ?name bif:contains "'[PATHWAY_KEYWORD]'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
```

### Query 4: Pathway Proteins with UniProt IDs (Reactome)
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?reactionName ?proteinName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?reaction a bp:BiochemicalReaction ;
            bp:displayName ?reactionName ;
            bp:left ?entity .
  FILTER(CONTAINS(?reactionName, "[KEYWORD]"))
  ?entity bp:entityReference ?proteinRef .
  ?proteinRef bp:xref ?xref .
  ?xref a bp:UnificationXref ;
        bp:db "UniProt"^^xsd:string ;
        bp:id ?uniprotId .
  OPTIONAL { ?proteinRef bp:name ?proteinName }
}
LIMIT 50
```

## Required TogoID Conversions

### Conversion 1: Protein IDs
```
# UniProt → Multiple databases
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,ncbigene")
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,ensembl_gene")
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,hgnc")
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,pdb")
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,chembl_target")
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,go")
togoid_convertId(ids="P45452,P16112,O75173", route="uniprot,reactome_pathway")
```

### Conversion 2: Disease IDs
```
# MONDO → Multiple ontologies
togoid_convertId(ids="MONDO:0005178", route="mondo,mesh")
togoid_convertId(ids="MONDO:0005178", route="mondo,doid")
togoid_convertId(ids="MONDO:0005178", route="mondo,hp_phenotype")
togoid_convertId(ids="MONDO:0005178", route="mondo,omim_phenotype")
```

### Conversion 3: Drug/Compound IDs
```
# ChEMBL → Multiple databases
togoid_convertId(ids="CHEMBL118,CHEMBL139", route="chembl_compound,pubchem_compound")
togoid_convertId(ids="CHEMBL118,CHEMBL139", route="chembl_compound,drugbank")
togoid_convertId(ids="CHEMBL118,CHEMBL139", route="chembl_compound,chebi")
```

### Conversion 4: Validate Conversions
```
# Count successful conversions
togoid_countId(ids="P45452,P16112,O75173", source="uniprot", target="pdb")
```

## Output Format
Please provide:
1. **Summary Table** for each biological scale with key entities and IDs
2. **Cross-Database ID Mapping Table** showing linked identifiers
3. **Integrated Disease Model** showing causal relationships across scales
4. **SPARQL Query Results** with actual data retrieved
5. **TogoID Conversion Results** with complete ID mappings
6. **Treatment Mechanism Summary** with drug-target relationships
7. **Data Source Citations** with database identifiers
```

---

## 🔧 TOOL USAGE STRATEGY

### Phase 1: Disease Identification & ID Conversion

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: IDENTIFY DISEASE & CONVERT IDs                                     │
│  ────────────────────────────────────────────────────────────────────────── │
│  1. Search: OLS4:search("[disease name]") → Get MONDO ID                    │
│  2. Convert: togoid_convertId("MONDO:XXXXXXX", "mondo,mesh")                │
│  3. Convert: togoid_convertId("MONDO:XXXXXXX", "mondo,doid")                │
│  4. Convert: togoid_convertId("MONDO:XXXXXXX", "mondo,hp_phenotype")        │
│  5. Convert: togoid_convertId("MONDO:XXXXXXX", "mondo,omim_phenotype")      │
│                                                                             │
│  OUTPUT: Disease IDs across all major ontologies                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: Protein Discovery via SPARQL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: DISCOVER DISEASE-ASSOCIATED PROTEINS                               │
│  ────────────────────────────────────────────────────────────────────────── │
│  1. SPARQL (UniProt): Query disease annotations with bif:contains           │
│     - Get proteins with disease annotations matching keywords               │
│     - Always filter: up:reviewed 1 (Swiss-Prot only)                        │
│     - Always filter: up:organism taxonomy:9606 (human)                      │
│                                                                             │
│  2. SPARQL (UniProt): For each protein, get:                                │
│     - GO terms (up:classifiedWith)                                          │
│     - Function annotations (up:Function_Annotation)                         │
│     - Subcellular locations                                                 │
│                                                                             │
│  OUTPUT: List of UniProt IDs with functional annotations                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 3: Cross-Database Linking via TogoID

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: LINK PROTEINS ACROSS DATABASES                                     │
│  ────────────────────────────────────────────────────────────────────────── │
│  For each UniProt ID discovered:                                            │
│                                                                             │
│  1. togoid_convertId(ids, "uniprot,ncbigene")      → NCBI Gene IDs          │
│  2. togoid_convertId(ids, "uniprot,ensembl_gene") → Ensembl Gene IDs        │
│  3. togoid_convertId(ids, "uniprot,hgnc")         → HGNC IDs                │
│  4. togoid_convertId(ids, "uniprot,pdb")          → PDB structure IDs       │
│  5. togoid_convertId(ids, "uniprot,chembl_target")→ ChEMBL target IDs       │
│  6. togoid_convertId(ids, "uniprot,go")           → GO term IDs             │
│  7. togoid_convertId(ids, "uniprot,reactome_pathway") → Reactome pathways   │
│                                                                             │
│  OUTPUT: Comprehensive ID mapping table                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 4: Pathway Analysis via SPARQL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: ANALYZE PATHWAYS IN DETAIL                                         │
│  ────────────────────────────────────────────────────────────────────────── │
│  1. SPARQL (Reactome): Search pathways by disease keywords                  │
│     - Use bif:contains with relevance scoring                               │
│     - Get pathway descriptions and components                               │
│                                                                             │
│  2. SPARQL (Reactome): For pathways of interest:                            │
│     - Get biochemical reactions                                             │
│     - Get protein participants with UniProt IDs                             │
│     - Get small molecule participants with ChEBI IDs                        │
│                                                                             │
│  3. TogoID: Link pathway proteins back to structures/drugs                  │
│                                                                             │
│  OUTPUT: Detailed pathway mechanisms with participant IDs                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 5: Drug-Target Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: ANALYZE DRUGS AND TARGETS                                          │
│  ────────────────────────────────────────────────────────────────────────── │
│  1. Search: search_chembl_molecule("[drug name]") → ChEMBL compound IDs     │
│  2. Search: search_chembl_target("[target name]") → ChEMBL target IDs       │
│                                                                             │
│  3. TogoID conversions for drugs:                                           │
│     - togoid_convertId(chembl_ids, "chembl_compound,pubchem_compound")      │
│     - togoid_convertId(chembl_ids, "chembl_compound,drugbank")              │
│     - togoid_convertId(chembl_ids, "chembl_compound,chebi")                 │
│                                                                             │
│  4. Get compound properties:                                                │
│     - get_compound_attributes_from_pubchem(pubchem_id)                      │
│                                                                             │
│  OUTPUT: Drug-target relationships with cross-database IDs                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 6: Literature Evidence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: GATHER LITERATURE EVIDENCE                                         │
│  ────────────────────────────────────────────────────────────────────────── │
│  1. PubMed:search_articles("[disease] [mechanism] [treatment]")             │
│  2. PubMed:get_article_metadata(pmids) → Get full citation details          │
│  3. PubMed:get_full_text_article(pmc_ids) → Get full text if available      │
│                                                                             │
│  OUTPUT: Literature citations with DOIs supporting mechanisms               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 SPARQL QUERY PATTERNS

### Pattern 1: UniProt Disease Annotation Query

**Purpose**: Find all human proteins associated with a disease keyword

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?protein ?mnemonic ?fullName ?diseaseComment
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:mnemonic ?mnemonic ;
           up:recommendedName ?name ;
           up:annotation ?annot .
  ?name up:fullName ?fullName .
  ?annot a up:Disease_Annotation ;
         rdfs:comment ?diseaseComment .
  ?diseaseComment bif:contains "'osteoarthritis'"
}
LIMIT 30
```

**Key Points**:
- Always include `up:reviewed 1` to get Swiss-Prot quality
- Always specify organism for human: `<http://purl.uniprot.org/taxonomy/9606>`
- Use `bif:contains` for full-text search (NOT FILTER/CONTAINS)
- Split property paths when using `bif:contains`

### Pattern 2: UniProt Protein Details with GO Terms

**Purpose**: Get comprehensive protein information including GO annotations

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT DISTINCT ?protein ?mnemonic ?fullName ?goLabel ?functionComment
WHERE {
  VALUES ?protein { uniprot:P45452 uniprot:P16112 uniprot:O75173 }
  ?protein a up:Protein ;
           up:mnemonic ?mnemonic ;
           up:recommendedName ?name .
  ?name up:fullName ?fullName .
  OPTIONAL {
    ?protein up:classifiedWith ?goTerm .
    ?goTerm rdfs:label ?goLabel .
    FILTER(STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_"))
  }
  OPTIONAL {
    ?protein up:annotation ?annot .
    ?annot a up:Function_Annotation ;
           rdfs:comment ?functionComment .
  }
}
LIMIT 100
```

### Pattern 3: UniProt Cross-References to External Databases

**Purpose**: Get PDB structures, Reactome pathways linked to proteins

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT DISTINCT ?protein ?mnemonic ?externalDB
WHERE {
  VALUES ?protein { uniprot:P45452 }
  ?protein a up:Protein ;
           up:mnemonic ?mnemonic ;
           rdfs:seeAlso ?externalDB .
  FILTER(CONTAINS(STR(?externalDB), "rdf.wwpdb.org"))
}
LIMIT 50
```

### Pattern 4: Reactome Pathway Search

**Purpose**: Find pathways related to a disease or biological process

```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT DISTINCT ?pathway ?name ?comment
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:displayName ?name .
  OPTIONAL { ?pathway bp:comment ?comment }
  ?name bif:contains "'collagen degradation' OR 'matrix metalloproteinase'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
```

### Pattern 5: Reactome Pathway Participants

**Purpose**: Get proteins and reactions in a specific pathway

```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT DISTINCT ?reactionName ?proteinName ?uniprotId
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?reaction a bp:BiochemicalReaction ;
            bp:displayName ?reactionName ;
            bp:left ?entity .
  FILTER(CONTAINS(?reactionName, "MMP") || CONTAINS(?reactionName, "collagen"))
  ?entity bp:entityReference ?proteinRef .
  ?proteinRef bp:xref ?xref .
  ?xref a bp:UnificationXref ;
        bp:db "UniProt"^^xsd:string ;
        bp:id ?uniprotId .
  OPTIONAL { ?proteinRef bp:name ?proteinName }
  FILTER(STRLEN(?uniprotId) = 6)
}
LIMIT 50
```

**Key Points**:
- Always include `FROM <http://rdf.ebi.ac.uk/dataset/reactome>` graph
- Use `^^xsd:string` for database name comparisons
- Use FILTER with CONTAINS for simple string matching (SPARQL standard)
- Use `bif:contains` for full-text search with relevance scoring

### Pattern 6: GO Term Details Query

**Purpose**: Get full GO term information via OLS4

```
# Use OLS4:fetch to get GO term details
OLS4:fetch(id="go+http://purl.obolibrary.org/obo/GO_0030574")

# Returns:
{
  "id": "go+http://purl.obolibrary.org/obo/GO_0030574",
  "title": "GO:0030574 collagen catabolic process",
  "text": "The proteolytic chemical reactions and pathways resulting in the breakdown of collagen...",
  "url": "http://purl.obolibrary.org/obo/GO_0030574"
}
```

---

## 🔗 TogoID API REFERENCE

### Available Conversions

| Source | Target | Route | Example |
|--------|--------|-------|---------|
| UniProt | NCBI Gene | `uniprot,ncbigene` | P45452 → 4322 |
| UniProt | Ensembl Gene | `uniprot,ensembl_gene` | P45452 → ENSG00000137745 |
| UniProt | HGNC | `uniprot,hgnc` | P45452 → 7159 |
| UniProt | PDB | `uniprot,pdb` | P45452 → 4FVL, 1ZTQ, ... |
| UniProt | ChEMBL Target | `uniprot,chembl_target` | P45452 → CHEMBL2318 |
| UniProt | GO | `uniprot,go` | P45452 → GO:0030574, ... |
| UniProt | Reactome | `uniprot,reactome_pathway` | P45452 → R-HSA-1474228 |
| MONDO | MeSH | `mondo,mesh` | MONDO:0005178 → D010003 |
| MONDO | DOID | `mondo,doid` | MONDO:0005178 → 8398 |
| MONDO | HP | `mondo,hp_phenotype` | MONDO:0005178 → HP:0002758 |
| MONDO | OMIM | `mondo,omim_phenotype` | MONDO:0005178 → 612280 |
| ChEMBL Compound | PubChem | `chembl_compound,pubchem_compound` | CHEMBL118 → 2662 |
| ChEMBL Compound | DrugBank | `chembl_compound,drugbank` | CHEMBL118 → DB00482 |
| ChEMBL Compound | ChEBI | `chembl_compound,chebi` | CHEMBL118 → 41423 |

### TogoID Functions

#### 1. `togoid_convertId` - Convert IDs between databases

```python
# Convert multiple UniProt IDs to NCBI Gene IDs
togoid_convertId(
    ids="P45452,P16112,O75173,Q9UNA0",
    route="uniprot,ncbigene"
)
# Returns: ["4322", "176", "9507", "11096"]
```

#### 2. `togoid_countId` - Count successful conversions

```python
# Check how many IDs can be converted
togoid_countId(
    ids="P45452,P16112,O75173",
    source="uniprot",
    target="pdb"
)
# Returns: {"source": 3, "target": 72}
```

#### 3. `togoid_getRelation` - Get relationship type

```python
# Check relationship between databases
togoid_getRelation(
    source="uniprot",
    target="chembl_target"
)
# Returns: [{"forward": {"id": "TIO_000002", "display_label": "is equivalent to"}}]
```

#### 4. `togoid_getAllDataset` - List all available datasets

```python
# Get all supported database types
togoid_getAllDataset()
# Returns: {"uniprot": {...}, "ncbigene": {...}, "pdb": {...}, ...}
```

#### 5. `togoid_getDataset` - Get dataset configuration

```python
# Get details about a specific dataset
togoid_getDataset(dataset="uniprot")
# Returns: {"label": "UniProt", "regex": "...", "examples": [...]}
```

---

## 📊 OUTPUT TEMPLATE

### Expected Analysis Structure with SPARQL/TogoID Results

```markdown
# [DISEASE NAME] Multi-Scale Pathophysiology Analysis

## Executive Summary
[2-3 sentence overview of the disease mechanism]

---

## Disease Ontology Cross-References

### TogoID Conversion Results
| Source | ID | Target Database | Target ID |
|--------|-------|-----------------|-----------|
| MONDO | MONDO:XXXXXXX | MeSH | D00XXXX |
| MONDO | MONDO:XXXXXXX | DOID | XXXX |
| MONDO | MONDO:XXXXXXX | HP | HP:XXXXXXX |
| MONDO | MONDO:XXXXXXX | OMIM | XXXXXX |

---

## 1. MOLECULAR LEVEL

### SPARQL Query: Disease-Associated Proteins
```sparql
[Actual SPARQL query used]
```

### Query Results: Key Proteins
| UniProt ID | Mnemonic | Protein Name | Disease Annotation |
|------------|----------|--------------|-------------------|
| [ID] | [MNEMONIC] | [Name] | [Annotation excerpt] |

### TogoID Cross-Database Mapping
| UniProt | NCBI Gene | Ensembl | HGNC | PDB Structures | ChEMBL Target |
|---------|-----------|---------|------|----------------|---------------|
| P45452 | 4322 | ENSG00000137745 | 7159 | 4FVL, 1ZTQ, ... | CHEMBL2318 |

### GO Term Annotations (via TogoID + OLS4)
| Protein | GO ID | GO Term | Category |
|---------|-------|---------|----------|
| [Name] | GO:XXXXXXX | [Term] | [BP/MF/CC] |

---

## 2. PATHWAY LEVEL

### SPARQL Query: Relevant Pathways
```sparql
[Actual SPARQL query used]
```

### Query Results: Dysregulated Pathways
| Pathway | Reactome ID | Description | Relevance Score |
|---------|-------------|-------------|-----------------|
| [Name] | R-HSA-XXXXXXX | [Description] | [Score] |

### Pathway Proteins (from SPARQL)
| Reaction | Protein | UniProt ID | Role |
|----------|---------|------------|------|
| [Reaction] | [Protein] | [ID] | [Substrate/Product/Catalyst] |

### TogoID: Protein → Pathway Mapping
| UniProt ID | Protein | Reactome Pathways |
|------------|---------|-------------------|
| [ID] | [Name] | R-HSA-XXX, R-HSA-YYY |

---

## 3-5. CELLULAR, TISSUE, CLINICAL LEVELS
[Similar structure with SPARQL queries and TogoID mappings]

---

## 6. TREATMENT MECHANISMS

### Drug-Target Analysis

#### TogoID Drug ID Conversions
| Drug | ChEMBL ID | PubChem CID | DrugBank ID | ChEBI ID |
|------|-----------|-------------|-------------|----------|
| [Drug] | CHEMBLXXX | CIDXXXX | DBXXXXX | XXXX |

#### Drug-Target Relationships
| Drug | Target Protein | UniProt ID | ChEMBL Target | Mechanism |
|------|---------------|------------|---------------|-----------|
| [Drug] | [Protein] | [UniProt] | [ChEMBL] | [MOA] |

---

## 7. INTEGRATED ID MAPPING TABLE

### Complete Cross-Database Linkage
| Entity Type | Primary ID | Database 1 | Database 2 | Database 3 | Database 4 |
|-------------|------------|------------|------------|------------|------------|
| Protein | UniProt:P45452 | NCBI:4322 | HGNC:7159 | PDB:4FVL | ChEMBL:2318 |
| Disease | MONDO:0005178 | MeSH:D010003 | DOID:8398 | HP:0002758 | OMIM:612280 |
| Drug | ChEMBL:118 | PubChem:2662 | DrugBank:DB00482 | ChEBI:41423 | - |

---

## Data Sources & Tools Used
- **SPARQL Endpoint**: UniProt (https://rdfportal.org/sib/sparql)
- **SPARQL Endpoint**: Reactome (https://rdfportal.org/ebi/sparql)
- **ID Conversion**: TogoID API
- **Ontology Lookup**: OLS4
- **Literature**: PubMed
```

---

## 🔧 CUSTOMIZATION GUIDE

### Disease Categories with Suggested Modifications

#### For **Cancer/Oncology**:
Add these SPARQL queries:
```sparql
# Find tumor-associated proteins
PREFIX up: <http://purl.uniprot.org/core/>
SELECT ?protein ?name ?comment
WHERE {
  ?protein up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:recommendedName/up:fullName ?name ;
           up:annotation ?annot .
  ?annot rdfs:comment ?comment .
  ?comment bif:contains "'tumor suppressor' OR 'oncogene' OR 'proto-oncogene'"
}
LIMIT 50
```

Add TogoID conversions:
```
togoid_convertId(protein_ids, "uniprot,omim_gene")  # Cancer gene associations
togoid_convertId(disease_id, "mondo,ncit_disease")  # NCI cancer classifications
```

#### For **Neurological/Neurodegenerative Diseases**:
Add these queries and conversions:
```
# Brain region anatomical terms
togoid_convertId(tissue_terms, "uberon,cl")  # Cell types in brain regions

# Neurotransmitter-related GO terms
togoid_convertId(protein_ids, "uniprot,go")  # Filter for neurotransmitter GO terms
```

#### For **Autoimmune/Inflammatory Diseases**:
Add cytokine/chemokine pathway queries:
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
SELECT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:displayName ?name .
  ?name bif:contains "'cytokine' OR 'interleukin' OR 'interferon' OR 'NF-kB'"
}
LIMIT 30
```

#### For **Rare/Genetic Diseases**:
Add OMIM and variant conversions:
```
togoid_convertId(gene_ids, "ncbigene,omim_gene")
togoid_convertId(disease_id, "mondo,omim_phenotype")
togoid_convertId(disease_id, "mondo,orphanet_phenotype")
```

---

## ⚠️ COMMON PITFALLS & SOLUTIONS

### SPARQL Pitfalls

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Missing `reviewed 1` | Returns noisy TrEMBL data | Always add `up:reviewed 1` |
| `bif:contains` with property paths | 400 Bad Request error | Split property paths into separate triple patterns |
| Missing `^^xsd:string` | Empty results in Reactome | Use `bp:db "UniProt"^^xsd:string` |
| No LIMIT clause | Query timeout | Always add `LIMIT 30-50` |
| Missing FROM graph | Wrong/no results | Add `FROM <http://rdf.ebi.ac.uk/dataset/reactome>` |

### TogoID Pitfalls

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Wrong ID format | Conversion fails | Check `togoid_getDataset` for correct format |
| Invalid route | No results | Use `togoid_getAllRelation` to find valid routes |
| Too many IDs | Slow response | Batch in groups of 50-100 |

### Example: Correct vs Incorrect SPARQL

**WRONG** (bif:contains with property path):
```sparql
SELECT ?protein ?name
WHERE {
  ?protein up:recommendedName/up:fullName ?name .
  ?name bif:contains "'kinase'"
}
```

**CORRECT** (split property path):
```sparql
SELECT ?protein ?name
WHERE {
  ?protein up:recommendedName ?recName .
  ?recName up:fullName ?name .
  ?name bif:contains "'kinase'"
}
```

---

## 🎯 EXAMPLE: Complete Analysis Workflow

### Example: Osteoarthritis Analysis

```
## Step 1: Disease ID Conversion
togoid_convertId("MONDO:0005178", "mondo,mesh")    → D010003
togoid_convertId("MONDO:0005178", "mondo,doid")    → 8398
togoid_convertId("MONDO:0005178", "mondo,hp_phenotype") → HP:0002758

## Step 2: SPARQL - Find Disease Proteins
run_sparql(dbname="uniprot", sparql_query="""
PREFIX up: <http://purl.uniprot.org/core/>
SELECT DISTINCT ?protein ?mnemonic ?fullName ?diseaseComment
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:mnemonic ?mnemonic ;
           up:recommendedName ?name ;
           up:annotation ?annot .
  ?name up:fullName ?fullName .
  ?annot a up:Disease_Annotation ;
         rdfs:comment ?diseaseComment .
  ?diseaseComment bif:contains "'osteoarthritis'"
}
LIMIT 30
""")
→ Found: ASPN_HUMAN (Q9BXN1) with D14 allele association

## Step 3: Cross-Database Linking
togoid_convertId("P45452,P16112,O75173,Q9UNA0", "uniprot,ncbigene")
→ [4322, 176, 9507, 11096]

togoid_convertId("P45452,P16112,O75173,Q9UNA0", "uniprot,pdb")
→ [4FVL, 1ZTQ, 830C, ...] (72 structures)

togoid_convertId("P45452,O75173,Q9UNA0", "uniprot,chembl_target")
→ [CHEMBL2318, CHEMBL280, CHEMBL2285]

## Step 4: SPARQL - Pathway Analysis
run_sparql(dbname="reactome", sparql_query="""
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>
SELECT DISTINCT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
           bp:displayName ?name .
  ?name bif:contains "'collagen degradation'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 20
""")
→ Found: Collagen degradation pathway with MMP-13 mechanism description

## Step 5: Drug Analysis
togoid_convertId("CHEMBL118,CHEMBL139,CHEMBL521", "chembl_compound,pubchem_compound")
→ [2662, 3033, 3672]

togoid_convertId("CHEMBL118,CHEMBL139,CHEMBL521", "chembl_compound,drugbank")
→ [DB00482, DB00586, DB01050]
```

---

## 🔄 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-14 | Initial template |
| 2.0 | 2025-01-14 | Major revision: Added SPARQL-first approach, comprehensive TogoID integration, detailed query patterns, cross-database mapping tables |

---

## 📚 REFERENCES

### RDF Databases
- UniProt RDF: https://sparql.uniprot.org/
- Reactome RDF: https://reactome.org/download-data (BioPAX)
- RDF Portal: https://rdfportal.org/

### TogoID
- TogoID Service: https://togoid.dbcls.jp/
- API Documentation: https://togoid.dbcls.jp/apidoc

### Ontologies
- MONDO: https://mondo.monarchinitiative.org/
- Gene Ontology: http://geneontology.org/
- OLS4: https://www.ebi.ac.uk/ols4/

### Literature
- PubMed: https://pubmed.ncbi.nlm.nih.gov/
