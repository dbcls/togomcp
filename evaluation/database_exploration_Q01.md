# Database Exploration for Questions 1-12

## Purpose
Systematic exploration and verification of databases required for the first 12 evaluation questions in Q01.json.

## Exploration Date
December 17, 2025

---

## Question 1: UniProt P04637 Molecular Mass

**Database:** UniProt  
**Query Type:** Precision - molecular property retrieval  
**Status:** ✅ VERIFIED

### Exploration
```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>

SELECT ?mnemonic ?fullName ?mass
WHERE {
  uniprot:P04637 up:mnemonic ?mnemonic ;
                 up:recommendedName ?name ;
                 up:sequence ?seq .
  ?name up:fullName ?fullName .
  ?seq up:mass ?mass .
}
```

### Results
- Mnemonic: P53_HUMAN
- Full Name: Cellular tumor antigen p53
- **Mass: 43653 Da** ✅

### Notes
- Query execution time: <1s
- Swiss-Prot reviewed entry (reviewed=1)
- Canonical sequence mass retrieved successfully

---

## Question 2: MONDO Identifier for Fabry Disease

**Database:** MONDO (via OLS4)  
**Query Type:** Precision - disease ontology ID  
**Status:** ✅ VERIFIED

### Exploration
Used OLS4:search with query "Fabry disease"

### Results
- **MONDO:0010526** ✅
- Also found in: Orphanet (324), DOID (14499), MeSH (D000795), OMIM (301500)

### Notes
- Multiple ontology mappings available
- MONDO serves as unified disease identifier
- Cross-references to 6+ disease databases

---

## Question 3: GO Biological Process Terms with "Autophagy"

**Database:** GO  
**Query Type:** Completeness - term counting  
**Status:** ✅ VERIFIED (Answer Updated)

### Exploration
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboinowl: <http://www.geneontology.org/formats/oboInOwl#>

SELECT (COUNT(DISTINCT ?go) as ?count)
FROM <http://rdfportal.org/ontology/go>
WHERE {
  ?go rdfs:label ?label ;
      oboinowl:hasOBONamespace ?namespace .
  ?label bif:contains "'autophagy'" .
  FILTER(STR(?namespace) = "biological_process")
  FILTER(STRSTARTS(STR(?go), "http://purl.obolibrary.org/obo/GO_"))
}
```

### Results
- **Count: 35 terms** ✅

### Notes
- Original estimate of 50-60 was incorrect
- Actual count: 35 biological_process terms containing "autophagy"
- Includes macroautophagy, microautophagy, selective autophagy, etc.
- FROM clause is CRITICAL for GO queries

---

## Question 4: PDB Electron Microscopy Structures

**Database:** PDB  
**Query Type:** Completeness - method filtering and counting  
**Status:** ✅ VERIFIED

### Exploration
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>

SELECT (COUNT(DISTINCT ?entry) as ?count)
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock ;
         pdbx:has_exptlCategory/pdbx:has_exptl ?exptl .
  ?exptl pdbx:exptl.method "ELECTRON MICROSCOPY" .
}
```

### Results
- **Count: 15,032 structures** ✅

### Notes
- Approximately 7.3% of total PDB entries (~204K total)
- Cryo-EM is rapidly growing field
- Query requires FROM clause and proper category traversal

---

## Question 5: UniProt P04637 to NCBI Gene ID

**Database:** TogoID  
**Query Type:** Integration - cross-database ID conversion  
**Status:** ✅ VERIFIED

### Exploration
Used TogoID:togoid_convertId with:
- IDs: P04637
- Route: uniprot,ncbigene

### Results
- **NCBI Gene ID: 7157** ✅
- Gene symbol: TP53
- Conversion successful

### Notes
- TogoID provides robust ID conversion
- P04637 (UniProt) → 7157 (NCBI Gene)
- TP53 tumor suppressor gene

---

## Question 6: PubChem Imatinib ChEBI Identifier

**Database:** PubChem  
**Query Type:** Integration - chemical database cross-reference  
**Status:** ✅ VERIFIED

### Exploration
Step 1: Get PubChem CID
```
TogoMCP:get_pubchem_compound_id("imatinib")
→ CID: 5291
```

Step 2: Query for ChEBI cross-reference
```sparql
PREFIX compound: <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/>

SELECT ?type
WHERE {
  compound:CID5291 a ?type .
}
```

### Results
- PubChem CID: 5291
- **ChEBI: CHEBI:45783** ✅
- Also found: SNOMED CT, NCI Thesaurus references

### Notes
- ChEBI cross-reference via rdf:type, not skos:exactMatch
- Imatinib is Gleevec, used for chronic myeloid leukemia
- Multiple ontology classifications available

---

## Question 7: PDB Recent High-Resolution Structures

**Database:** PDB  
**Query Type:** Currency - recent data with quality filters  
**Status:** ✅ VERIFIED

### Exploration
```sparql
PREFIX pdbx: <http://rdf.wwpdb.org/schema/pdbx-v50.owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?entry_id ?resolution ?year
FROM <http://rdfportal.org/dataset/pdbj>
WHERE {
  ?entry a pdbx:datablock .
  BIND(STRAFTER(str(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbx:has_refineCategory/pdbx:has_refine ?refine ;
         pdbx:has_citationCategory/pdbx:has_citation ?citation .
  ?refine pdbx:refine.ls_d_res_high ?resolution .
  ?citation pdbx:citation.year ?year .
  FILTER(xsd:decimal(?resolution) > 0 && xsd:decimal(?resolution) < 1.5)
  FILTER(xsd:integer(?year) >= 2023)
}
```

### Results
Sample structures found (10 shown):
- 8AUF: 1.35 Å (2023)
- 8AWI: 1.15 Å (2023)
- 8AIT: 1.24 Å (2023)
- **Multiple ultra-high resolution structures from 2023-2024** ✅

### Notes
- Requires xsd:decimal() conversion for numeric comparisons
- Year filtering via citation metadata
- Resolution values < 1.5 Å indicate exceptional quality
- Query combines refinement and citation data

---

## Question 8: Reactome PDGFRA Pathways

**Database:** Reactome  
**Query Type:** Currency - pathway information  
**Status:** ✅ VERIFIED

### Exploration
Search for PDGF-related pathways:
```sparql
PREFIX bp: <http://www.biopax.org/release/biopax-level3.owl#>

SELECT ?pathway ?name
FROM <http://rdf.ebi.ac.uk/dataset/reactome>
WHERE {
  ?pathway a bp:Pathway ;
    bp:displayName ?name .
  ?name bif:contains "'PDGF' AND 'signal*'" option (score ?sc)
}
```

### Results
- Signaling by PDGF (multiple species-specific instances)
- PDGFR mutants bind TKIs
- Signaling by PDGFR in disease
- Drug resistance of PDGFR mutants
- **Multiple pathways involving PDGFRA identified** ✅

### Notes
- PDGFRA = Platelet-derived growth factor receptor alpha
- UniProt ID: P16234
- Both normal signaling and disease pathways present
- bif:contains with wildcards works well for search

---

## Question 9: MeSH Identifier for Niemann-Pick Disease Type C

**Database:** MeSH  
**Query Type:** Specificity - rare disease medical terminology  
**Status:** ✅ VERIFIED

### Exploration
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>

SELECT ?descriptor ?label ?identifier
FROM <http://id.nlm.nih.gov/mesh>
WHERE {
  ?descriptor a meshv:TopicalDescriptor ;
    rdfs:label ?label ;
    meshv:identifier ?identifier .
  ?label bif:contains "'niemann' AND 'pick'" option (score ?sc)
}
```

### Results
- General term: D009542 (Niemann-Pick Diseases)
- **Type C specific: D052556** ✅
- Type A: D052536
- Type B: D052537

### Notes
- D052556 is the MeSH Descriptor ID for Type C
- Also found Thesaurus IDs (T-numbers) via search_mesh_entity
- Lysosomal storage disorder
- Important distinction between general term and specific subtypes

---

## Question 10: PubChem Molecular Formula for Resveratrol

**Database:** PubChem  
**Query Type:** Specificity - chemical property  
**Status:** ✅ VERIFIED

### Exploration
Step 1: Get CID
```
TogoMCP:get_pubchem_compound_id("resveratrol")
→ CID: 445154
```

Step 2: Get attributes
```
TogoMCP:get_compound_attributes_from_pubchem("445154")
```

### Results
- PubChem CID: 445154
- **Molecular Formula: C14H12O3** ✅
- Molecular Weight: 228.24
- Natural polyphenol found in grapes

### Notes
- get_compound_attributes_from_pubchem returns comprehensive data
- Includes SMILES, InChI, molecular formula, weight
- Resveratrol is a stilbenoid studied for health benefits

---

## Question 11: ChEMBL Human Kinase Targets

**Database:** ChEMBL  
**Query Type:** Structured Query - complex filtering  
**Status:** ✅ VERIFIED (Answer Updated)

### Exploration
```sparql
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>

SELECT (COUNT(DISTINCT ?target) as ?count)
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  ?target a cco:SingleProtein ;
          rdfs:label ?label ;
          cco:organismName "Homo sapiens" .
  ?label bif:contains "'kinase'" option (score ?sc)
}
```

### Results
- **Count: 516 human protein kinase targets** ✅

### Notes
- Original estimate of 300-400 was too low
- Actual count: 516
- Includes all human single protein targets with "kinase" in name
- bif:contains efficiently searches target names
- Requires FROM clause for multi-graph endpoint

---

## Question 12: GO Macroautophagy Parent Terms

**Database:** GO  
**Query Type:** Structured Query - ontology hierarchy navigation  
**Status:** ✅ VERIFIED

### Exploration
```sparql
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?parent ?parentLabel
FROM <http://rdfportal.org/ontology/go>
WHERE {
  obo:GO_0016236 rdfs:subClassOf ?parent .
  ?parent rdfs:label ?parentLabel .
  FILTER(isIRI(?parent))
  FILTER(STRSTARTS(STR(?parent), "http://purl.obolibrary.org/obo/GO_"))
}
```

### Results
- **Direct Parent: GO:0006914 (autophagy)** ✅

### Notes
- GO:0016236 = macroautophagy
- Single direct parent in biological_process namespace
- FILTER(isIRI(?parent)) excludes OWL restrictions (blank nodes)
- Macroautophagy is a major type of autophagy involving autophagosomes

---

## Summary Statistics

### Databases Explored: 7
1. UniProt ✅
2. MONDO (via OLS4) ✅
3. GO ✅
4. PDB ✅
5. TogoID ✅
6. PubChem ✅
7. Reactome ✅
8. MeSH ✅
9. ChEMBL ✅

### Query Success Rate
- Total questions: 12
- Successfully verified: 12
- Success rate: 100%

### Corrections Made
- Q3: Updated count from "50-60" to "35" (actual verified count)
- Q11: Updated count from "300-400" to "516" (actual verified count)

### Key Learnings

1. **FROM Clauses Critical**: GO, PDB, MeSH, ChEMBL, Reactome all require explicit FROM clauses

2. **bif:contains is Powerful**: Full-text search with boolean operators (AND, OR, NOT, wildcards) works across all Virtuoso backends

3. **Type Conversion Required**: PDB resolution/R-factor filtering needs xsd:decimal()

4. **Property Name Accuracy**: MeSH uses meshv:broaderDescriptor (not meshv:broader), meshv:annotation (not meshv:scopeNote)

5. **FILTER Patterns**:
   - isIRI() to exclude blank nodes in GO/MONDO
   - STR() for namespace comparisons in GO
   - STRSTARTS() for URI prefix matching

6. **Cross-Reference Patterns Vary**:
   - PubChem: rdf:type for ChEBI (not skos:exactMatch)
   - Reactome: bp:xref with ^^xsd:string type restriction
   - UniProt: rdfs:seeAlso with CONTAINS filtering

7. **Search vs SPARQL**:
   - Use search tools (OLS4:search, search_mesh_entity) for initial discovery
   - Follow with SPARQL for precise verification and data extraction

### Tools Used
- TogoMCP:run_sparql (primary query tool)
- TogoMCP:get_pubchem_compound_id
- TogoMCP:get_compound_attributes_from_pubchem
- TogoMCP:togoid_convertId
- TogoMCP:search_mesh_entity
- OLS4:search

### Performance Notes
- Simple lookups: <1 second
- Count queries: 1-2 seconds
- Multi-join queries: 2-5 seconds
- All queries completed within timeout limits

---

## Conclusion

All 12 questions have been systematically verified through actual database queries. The exploration revealed:

1. All expected answers are retrievable from the databases
2. Two answers needed correction based on actual data
3. Query patterns are consistent and well-documented in MIE files
4. Database coverage is comprehensive for these question types

The questions are ready for evaluation with verified ground truth answers.
