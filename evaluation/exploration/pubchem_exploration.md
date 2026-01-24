# PubChem Exploration Report

## Database Overview
- **Purpose**: Comprehensive public database of chemical molecules and biological activities
- **Scope**: 119M compounds, 339M substances, 1.7M bioassays, 167K genes, 249K proteins, 81K pathways
- **Key features**: Molecular descriptors (SMILES, InChI, formula, weight), drug classifications, bioactivity data

## Schema Analysis (from MIE file)
### Main Properties
- `vocab:Compound`: Core compound entity
- `sio:SIO_000008`: Links to descriptors
- `sio:SIO_000300`: Descriptor values
- `obo:RO_0000087`: Biological roles (e.g., FDAApprovedDrugs)
- `cheminf:CHEMINF_000455`: Stereoisomer relationships

### Descriptor Types
- `sio:CHEMINF_000335`: Molecular formula
- `sio:CHEMINF_000334`: Molecular weight
- `sio:CHEMINF_000376`: Canonical SMILES
- `sio:CHEMINF_000396`: IUPAC InChI

### Important Relationships
- `rdfs:seeAlso`: External database links
- `rdf:type`: Ontology classifications (ChEBI, SNOMED CT)
- `cito:isDiscussedBy`: Patent and literature references

### Query Patterns
- Use `get_pubchem_compound_id` for name-to-CID lookup
- Use `get_compound_attributes_from_pubchem` for compound properties
- Filter by `obo:RO_0000087 vocab:FDAApprovedDrugs` for drugs

## Search Queries Performed

1. **Query: "aspirin"**
   - CID 2244: 2-acetyloxybenzoic acid
   - Molecular formula: C9H8O4, Weight: 180.16

2. **Query: "ibuprofen"**
   - CID 3672

3. **Query: "caffeine"**
   - CID 2519: 1,3,7-trimethylpurine-2,6-dione
   - Molecular formula: C8H10N4O2, Weight: 194.19

4. **Query: "metformin"**
   - CID 4091 (diabetes drug)

5. **Query: "resveratrol"**
   - CID 445154 (polyphenol antioxidant)

## SPARQL Queries Tested

```sparql
# Query 1: Count FDA-approved drugs
PREFIX vocab: <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(DISTINCT ?compound) as ?fda_count)
WHERE {
  ?compound a vocab:Compound ;
            obo:RO_0000087 vocab:FDAApprovedDrugs .
}
# Result: 17,367 FDA-approved drugs
```

```sparql
# Query 2: Find FDA drugs by molecular weight range
PREFIX vocab: <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX sio: <http://semanticscience.org/resource/>
SELECT ?compound ?weight
WHERE {
  ?compound a vocab:Compound ;
            obo:RO_0000087 vocab:FDAApprovedDrugs ;
            sio:SIO_000008 ?weightDesc .
  ?weightDesc a sio:CHEMINF_000334 ;
              sio:SIO_000300 ?weight .
  FILTER(?weight >= 300 && ?weight <= 350)
}
LIMIT 10
# Results: Found drugs like CID2369 (307.4), CID2708 (304.2), etc.
```

## Cross-Reference Analysis

### Links to other databases
- **Wikidata**: ~2-5% of compounds
- **ChEBI**: ~5-10% (ontology classification)
- **SNOMED CT**: Drug compounds
- **NCBI Protein**: Via identifiers.org
- **PDB**: Protein structures

### Cross-database integration
- ChEBI classification via rdf:type
- Patent references via cito:isDiscussedBy
- Protein-PDB links via pdbx:link_to_pdb

## Interesting Findings

**Discoveries requiring actual database queries:**

1. **17,367 FDA-approved drugs** in PubChem (requires COUNT query)
2. **CID 2244** (aspirin) has molecular weight 180.16 and formula C9H8O4 (requires attribute query)
3. **CID 2519** (caffeine) has molecular weight 194.19 and formula C8H10N4O2
4. **CID 445154** is resveratrol (requires name-to-CID lookup)
5. **Molecular weight filtering** works effectively for drug discovery queries

**Key real entities discovered (NOT in MIE examples):**
- CID 3672: Ibuprofen
- CID 4091: Metformin (diabetes drug)
- CID 445154: Resveratrol (antioxidant)
- CID 2519: Caffeine

**Note**: MIE file uses CID2244 (aspirin) as main example - found additional real compounds

## Question Opportunities by Category

### Precision
- ✅ "What is the PubChem CID for caffeine?" → 2519 (requires lookup)
- ✅ "What is the molecular formula of aspirin (CID 2244)?" → C9H8O4
- ✅ "What is the molecular weight of ibuprofen?" → requires lookup for CID 3672
- ✅ "What is the SMILES notation for caffeine?" → CN1C=NC2=C1C(=O)N(C(=O)N2C)C

### Completeness  
- ✅ "How many FDA-approved drugs are in PubChem?" → 17,367
- ✅ "How many compounds in PubChem?" → 119M (large scale)

### Integration
- ✅ "What is the ChEBI ID for aspirin (CID 2244)?" → requires cross-reference lookup
- ✅ "What Wikidata entity corresponds to caffeine?" → requires rdfs:seeAlso query

### Currency
- ✅ "How many FDA-approved drugs are currently in PubChem?" → 17,367 (updated continuously)

### Specificity
- ✅ "What is the PubChem CID for resveratrol?" → 445154 (specific polyphenol)
- ✅ "What is the PubChem CID for metformin?" → 4091 (diabetes drug)

### Structured Query
- ✅ "Find FDA-approved drugs with molecular weight between 300-350" → compound filter
- ✅ "Find compounds classified as ChEBI analgesics" → ontology type filter

## Notes
- `get_pubchem_compound_id` is efficient for name-to-CID lookup
- `get_compound_attributes_from_pubchem` provides comprehensive molecular properties
- SPARQL queries need proper descriptor type filtering (sio:CHEMINF_XXXXX)
- Use FROM clauses for specific graphs (bioassay, protein)
- FDA drug filtering via `obo:RO_0000087 vocab:FDAApprovedDrugs` is reliable
- Molecular weight range queries are efficient up to 10K results
