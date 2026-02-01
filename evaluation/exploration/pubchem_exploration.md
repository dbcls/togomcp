# PubChem Exploration Report

**Date**: 2026-01-31
**Session**: 1 (Complete)

## Executive Summary

PubChem is a comprehensive chemical database with 119M compounds, 339M substances, 1.7M bioassays, and extensive cross-references to external databases. Key discoveries include:

- **Key capabilities requiring deep knowledge**: 
  - FDA drug queries with molecular weight filtering
  - Bioassay searching with bif:contains and FROM clause requirements
  - Pathway-compound relationships via RO_0000057
  - Disease-compound cooccurrence data
  - Multi-graph architecture requiring FROM clauses for bioassay, protein, pathway queries

- **Major integration opportunities**:
  - PubChem → ChEMBL via togoid (compound IDs)
  - PubChem → ChEBI via rdf:type ontology classification
  - PubChem → PDB via protein graph links
  - PubChem → MeSH/MONDO via disease graph cross-references
  - PubChem → PathBank via pathway seeAlso references

- **Most valuable patterns discovered**:
  - Pre-filtering by FDA approved drugs enables ChEBI aggregation queries
  - Explicit FROM clauses required for bioassay and pathway queries
  - bif:contains works efficiently for title/label text search
  - Performance-critical: type filtering before aggregation

- **Recommended question types**: 
  - FDA drug property queries
  - Bioassay text searches
  - Pathway-compound relationships
  - Disease-compound associations
  - Cross-database compound identification

## Database Overview

- **Purpose and scope**: Comprehensive public database of chemical molecules and biological activities
- **Key data types and entities**:
  - Compounds (119M): molecules with molecular descriptors
  - Substances (339M): compound submissions from various sources
  - BioAssays (1.7M): biological activity data
  - Genes (167K): gene-compound associations
  - Proteins (249K): protein-compound associations
  - Pathways (80K): pathway-compound relationships
  - Diseases: disease entities with cross-references
  - Cooccurrence: gene-disease co-occurrences in literature
  - Endpoints: bioactivity measurements (IC50, EC50, etc.)
  - Patents: compound-patent associations

- **Dataset size and performance considerations**:
  - Very large dataset (119M compounds)
  - Aggregation queries require filtering to avoid timeout
  - Multi-graph architecture requires explicit FROM clauses
  - CID-specific queries efficient (<1s)
  - Weight range queries efficient up to 10K results

- **Available access methods**:
  - SPARQL endpoint: https://rdfportal.org/pubchem/sparql
  - ncbi_esearch for compound, substance, bioassay searches
  - get_pubchem_compound_id for name→CID lookup
  - get_compound_attributes_from_pubchem for property retrieval
  - togoid for ID conversion to other databases

## Structure Analysis

### Performance Strategies

**Strategy 1: Pre-filtering by Role/Classification**
- Why needed: 119M compounds makes aggregation queries timeout
- When to apply: Any aggregation (COUNT, GROUP BY) on compounds
- Performance impact: Query completes in seconds vs 60s timeout
- Example: Filter by `obo:RO_0000087 vocab:FDAApprovedDrugs` before ChEBI classification aggregation

**Strategy 2: Descriptor Type Filtering**
- Why needed: Each compound has ~25 descriptors
- When to apply: When retrieving specific molecular properties
- Performance impact: Reduces result set significantly
- Example: `FILTER(?descriptorType IN (sio:CHEMINF_000335, sio:CHEMINF_000334))`

**Strategy 3: Explicit FROM Clauses**
- Why needed: Data split across multiple named graphs
- When to apply: Bioassay, protein, pathway, disease queries
- Performance impact: Required for correct results (may return empty otherwise)
- Example: `FROM <http://rdf.ncbi.nlm.nih.gov/pubchem/bioassay>`

**Strategy 4: LIMIT on Aggregations**
- Why needed: Large result sets cause timeout
- When to apply: Any GROUP BY query
- Performance impact: Allows query to complete
- Example: `LIMIT 50` on aggregation results

### Common Pitfalls

**Error 1: Missing FROM Clause for Bioassays**
- Cause: Bioassay data in separate graph
- Symptoms: Query may return unexpected or empty results
- Solution: Add `FROM <http://rdf.ncbi.nlm.nih.gov/pubchem/bioassay>`
- Example: Bioassay title search requires FROM clause

**Error 2: Aggregation Without Type Filter**
- Cause: Trying to aggregate over 119M compounds
- Symptoms: 60-second timeout
- Solution: Filter by compound role (FDA drugs) or other criteria first
- Example: ChEBI classification counts need FDA drug filter

**Error 3: Descriptor Retrieval Without Type Filter**
- Cause: ~25 descriptors per compound
- Symptoms: Too many results, unclear which is which
- Solution: Filter by specific descriptor type (CHEMINF_000335 for formula, etc.)

**Error 4: Mixed Datatype Comparison**
- Cause: Descriptor values stored as different types (string/double/integer)
- Symptoms: Comparison errors or unexpected results
- Solution: Filter by descriptor type before numeric comparison

### Data Organization

**Compound Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/compound`)
- Core compound entities with rdf:type vocab:Compound
- FDA drug classification via obo:RO_0000087
- ChEBI/SNOMED CT ontology classification via rdf:type
- Links to descriptors via sio:SIO_000008
- Stereoisomer relationships via cheminf:CHEMINF_000455

**Descriptor Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/descriptor/compound`)
- Molecular properties: formula (CHEMINF_000335), weight (CHEMINF_000334)
- SMILES (CHEMINF_000376), InChI (CHEMINF_000396)
- TPSA, hydrogen bond donors/acceptors, etc.

**BioAssay Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/bioassay`)
- Assay metadata with dcterms:title
- Source information via dcterms:source
- Measurement groups via bao:BAO_0000209

**Protein Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/protein`)
- Protein entities with skos:prefLabel
- PDB structure links via pdbx:link_to_pdb
- Conserved domain annotations

**Pathway Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/pathway`)
- Pathway entities with dcterms:title
- Compound participants via obo:RO_0000057
- Protein participants via obo:RO_0000057
- PathBank cross-references via rdfs:seeAlso

**Disease Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/disease`)
- Disease entities with skos:prefLabel
- Cross-references to MeSH, MONDO, NCI, OMIM via skos:closeMatch

**Cooccurrence Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/cooccurrence`)
- Gene-disease co-occurrences in literature
- Links via rdf:subject (gene) and rdf:object (disease)
- Count via sio:SIO_000300

**Endpoint Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/endpoint`)
- Bioactivity measurements (IC50, EC50, potency)
- Value via sio:SIO_000300
- Unit via sio:SIO_000221
- Activity outcome via vocab:PubChemAssayOutcome

**Gene Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/gene`)
- Gene entities linked to patents via cito:isDiscussedBy

**Patent Graph** (`http://rdf.ncbi.nlm.nih.gov/pubchem/patent`)
- Patent classifications and references

### Cross-Database Integration Points

**Integration 1: PubChem → ChEMBL**
- Connection relationship: ID conversion
- Join point: togoid_convertId (pubchem_compound → chembl_compound)
- Required information: PubChem CID
- Pre-filtering needed: None (direct ID conversion)
- Knowledge required: Know to use togoid, route format
- Tested: CID 5291 (imatinib) → CHEMBL941

**Integration 2: PubChem → ChEBI (via ontology)**
- Connection relationship: rdf:type classification
- Join point: Compounds typed with ChEBI URIs (http://purl.obolibrary.org/obo/CHEBI_*)
- Required information: ChEBI class URI
- Pre-filtering needed: FDA drugs for aggregation queries
- Knowledge required: Understand ChEBI classification stored as rdf:type
- Tested: Aspirin CID2244 typed as CHEBI:15365

**Integration 3: PubChem → MeSH/MONDO (via disease)**
- Connection relationship: skos:closeMatch cross-references
- Join point: Disease graph entities
- Required information: Disease DZID identifier
- Pre-filtering needed: FROM clause for disease graph
- Knowledge required: Understand disease-ontology mapping structure
- Tested: "Breast Cancer" diseases with MeSH and MONDO mappings

**Integration 4: PubChem → PDB (via protein)**
- Connection relationship: pdbx:link_to_pdb
- Join point: Protein graph entities
- Required information: Protein accession
- Pre-filtering needed: FROM clause for protein graph
- Knowledge required: Understand protein-PDB linking pattern
- Tested: Kinase proteins with multiple PDB structure links

**Integration 5: PubChem → PathBank (via pathway)**
- Connection relationship: rdfs:seeAlso
- Join point: Pathway graph entities
- Required information: Pathway PWID identifier
- Pre-filtering needed: FROM clause for pathway graph
- Knowledge required: Understand pathway-compound relationships via RO_0000057
- Tested: Cardiolipin biosynthesis pathway with compound participants

## Complex Query Patterns Tested

### Pattern 1: FDA Drug Molecular Weight Filtering

**Purpose**: Find FDA-approved drugs within specific molecular weight ranges

**Category**: Structured Query / Performance-Critical

**Naive Approach**:
Query all compounds, filter by weight, then by FDA role

**What Happened**:
- Works but less efficient ordering
- No timeout for small ranges with FDA filter

**Correct Approach**:
Filter by FDA role first, then apply weight constraint

**What Knowledge Made This Work**:
- Key Insights:
  * FDA drug role stored via obo:RO_0000087 vocab:FDAApprovedDrugs
  * Molecular weight in descriptor graph via sio:CHEMINF_000334
  * SIO pattern: compound → descriptor → value
- Performance: Completes in <2 seconds
- Why it works: FDA filter reduces 119M compounds to ~17K

**Results Obtained**:
- Number of results: 20 (with weight 150-200)
- Sample results:
  * CID164739 (183.2 g/mol)
  * CID2723 (156.61 g/mol)
  * CID440545 (180.16 g/mol - aspirin)

**Natural Language Question Opportunities**:
1. "Which FDA-approved drugs have a molecular weight between 150 and 200 g/mol?" - Category: Structured Query
2. "What is the molecular weight of aspirin?" - Category: Precision
3. "How many FDA-approved drugs are in PubChem?" - Category: Completeness

---

### Pattern 2: Bioassay Text Search with FROM Clause

**Purpose**: Find bioassays by keyword in title

**Category**: Structured Query / Error-Avoidance

**Naive Approach**:
Query bioassays without FROM clause

**What Happened**:
- Query works in this endpoint but MIE warns may return empty
- bif:contains required for text search

**Correct Approach**:
Use explicit FROM clause and bif:contains for title search

**What Knowledge Made This Work**:
- Key Insights:
  * Bioassay data in separate named graph
  * bif:contains syntax for Virtuoso text search
  * Title stored via dcterms:title
- Query structure: FROM clause + bif:contains

**Results Obtained**:
- Number of results: 20 cancer-related bioassays
- Sample results:
  * AID10023: "In vitro cytotoxicity against A2780 human ovarian cancer cell line"
  * AID42277: "Inhibition of BT-20 breast cancer cell proliferation"
  * AID31762: "In vitro anti tumor activity against human non-small cell lung cancer"

**Natural Language Question Opportunities**:
1. "What bioassays in PubChem are related to breast cancer?" - Category: Specificity
2. "Find bioassays testing compounds against lung cancer cell lines" - Category: Structured Query
3. "How many bioassays mention kinase inhibitors?" - Category: Completeness

---

### Pattern 3: Aggregation with Pre-filtering (Anti-pattern Fix)

**Purpose**: Count compounds by ChEBI classification

**Category**: Performance-Critical

**Naive Approach**:
```sparql
SELECT ?chebiClass (COUNT(?compound) as ?count)
WHERE {
  ?compound a vocab:Compound ;
            a ?chebiClass .
  FILTER(STRSTARTS(STR(?chebiClass), "http://purl.obolibrary.org/obo/CHEBI_"))
}
GROUP BY ?chebiClass
```

**What Happened**:
- Error: Query timeout (60 seconds)
- Cause: Attempting to aggregate over 119M compounds

**Correct Approach**:
Add FDA drug filter before aggregation
```sparql
SELECT ?chebiClass (COUNT(DISTINCT ?compound) as ?count)
WHERE {
  ?compound a vocab:Compound ;
            obo:RO_0000087 vocab:FDAApprovedDrugs ;
            a ?chebiClass .
  FILTER(STRSTARTS(STR(?chebiClass), "http://purl.obolibrary.org/obo/CHEBI_"))
}
GROUP BY ?chebiClass
LIMIT 30
```

**What Knowledge Made This Work**:
- Key Insights:
  * 119M compounds too large for unfiltered aggregation
  * FDA drug filter reduces to manageable set (~17K)
  * STRSTARTS filter for ChEBI namespace
  * LIMIT essential for aggregation
- Performance improvement: From timeout to <5 seconds

**Results Obtained**:
- Number of results: 30 ChEBI classes
- Each class has 1 compound in FDA drugs set (specific drug mappings)

**Natural Language Question Opportunities**:
1. "How many different chemical classes are represented among FDA-approved drugs in PubChem?" - Category: Completeness
2. "What types of compounds (by ChEBI classification) are FDA-approved drugs?" - Category: Structured Query

---

### Pattern 4: Pathway-Compound Relationships

**Purpose**: Find compounds participating in specific biological pathways

**Category**: Integration / Structured Query

**Naive Approach**:
Query pathway graph without understanding participant relationship

**What Happened**:
- Need to understand RO_0000057 (has participant) relationship
- Participants can be compounds OR proteins

**Correct Approach**:
Query pathway with title search, filter participants by compound URI pattern

**What Knowledge Made This Work**:
- Key Insights:
  * Pathways use obo:RO_0000057 for participants
  * Participants include both compounds and proteins
  * Filter by URI pattern to get only compounds
  * Cross-reference to PathBank via rdfs:seeAlso
- Query structure: FROM pathway graph + participant filter

**Results Obtained**:
- Number of results: Multiple compounds per pathway
- Sample pathway: "Cardiolipin Biosynthesis CL(i-14:0/i-13:0/a-13:0/i-18:0)"
- Sample compounds: CID5893, CID6176, CID1061, CID962, CID668

**Natural Language Question Opportunities**:
1. "What compounds participate in EGFR signaling pathways?" - Category: Integration
2. "Which metabolites are involved in cardiolipin biosynthesis?" - Category: Specificity
3. "Find pathways that involve ATP (or a specific compound)" - Category: Integration

---

### Pattern 5: Protein-PDB Structure Links

**Purpose**: Find proteins with structural information from PDB

**Category**: Integration

**Naive Approach**:
Query protein graph without FROM clause

**What Happened**:
- Works with FROM clause
- Multiple PDB links per protein (one protein → many structures)

**Correct Approach**:
Use FROM clause, filter by protein name, retrieve PDB links

**What Knowledge Made This Work**:
- Key Insights:
  * Protein data in separate graph
  * pdbx:link_to_pdb for PDB cross-references
  * skos:prefLabel for protein names
  * One protein can have many PDB structures
- Query enables protein → structure discovery

**Results Obtained**:
- Sample: "Chain B, C-SRC TYROSINE KINASE" → 8 PDB structures (1A07, 1A08, 1A09, etc.)
- Sample: "Chain A, MAP KINASE P38" → 3+ PDB structures
- Sample: "Chain A, CELL DIVISION PROTEIN KINASE 2" → 10+ PDB structures

**Natural Language Question Opportunities**:
1. "Which kinase proteins have crystal structures available in PDB?" - Category: Integration
2. "How many PDB structures are linked to MAP kinase p38 in PubChem?" - Category: Completeness
3. "Find proteins involved in cell division that have structural data" - Category: Structured Query

---

### Pattern 6: Disease Cross-References

**Purpose**: Find disease entities and their external database mappings

**Category**: Integration / Specificity

**Naive Approach**:
Query disease graph without understanding cross-reference structure

**What Happened**:
- Disease entities have multiple cross-references
- skos:closeMatch used for external mappings

**Correct Approach**:
Use FROM clause, search by label, retrieve cross-references

**What Knowledge Made This Work**:
- Key Insights:
  * Disease data in separate graph
  * skos:prefLabel for disease names
  * skos:closeMatch for external references (MeSH, MONDO, NCI, OMIM)
  * Multiple external IDs per disease
- Enables disease → external ontology mapping

**Results Obtained**:
- "Breast Cancer, Familial" → MeSH C562840, NCI C4503, MONDO_0016419
- "Breast Cancer Lymphedema" → MeSH D000072656, MedGen C4277512
- "Breast Cancer 3" → MeSH C565336, OMIM 605365, MONDO_0011543

**Natural Language Question Opportunities**:
1. "What is the MONDO identifier for familial breast cancer?" - Category: Integration
2. "Find all external identifiers for Niemann-Pick disease in PubChem" - Category: Completeness
3. "Which diseases in PubChem are related to breast cancer?" - Category: Specificity

---

### Pattern 7: Gene-Disease Cooccurrence

**Purpose**: Find gene-disease associations from literature

**Category**: Integration / Structured Query

**Naive Approach**:
Query cooccurrence without understanding structure

**What Happened**:
- Cooccurrence uses reification pattern
- rdf:subject for gene, rdf:object for disease
- sio:SIO_000300 for count

**Correct Approach**:
Use FROM clause, understand subject/object/count pattern

**What Knowledge Made This Work**:
- Key Insights:
  * Cooccurrence uses reification (statement as subject)
  * Gene in rdf:subject, disease in rdf:object
  * Count via sio:SIO_000300
  * Method type via sio:SIO_001157
- Enables literature-based gene-disease discovery

**Results Obtained**:
- Sample: metap2_DZID8306 → Gene metap2 cooccurs with disease DZID8306 (77 times)

**Natural Language Question Opportunities**:
1. "Which genes are most frequently mentioned with breast cancer in the literature?" - Category: Structured Query
2. "Find disease associations for the TP53 gene based on PubChem literature data" - Category: Integration

---

### Pattern 8: Compound Properties via Helper Tool

**Purpose**: Retrieve molecular properties for a named compound

**Category**: Precision / Simple

**Naive Approach**:
Write complex SPARQL query

**What Happened**:
- Helper tools (get_pubchem_compound_id, get_compound_attributes_from_pubchem) exist
- Direct name → CID → properties workflow

**Correct Approach**:
Use get_pubchem_compound_id then get_compound_attributes_from_pubchem

**What Knowledge Made This Work**:
- Key Insights:
  * get_pubchem_compound_id converts name to CID
  * get_compound_attributes_from_pubchem retrieves all properties
  * Returns formula, weight, SMILES, InChI, image URL
- Simple 2-step workflow

**Results Obtained**:
- Imatinib: CID 5291
- Formula: C29H31N7O
- Weight: 493.6
- SMILES: Full canonical SMILES

**Natural Language Question Opportunities**:
1. "What is the molecular formula of imatinib?" - Category: Precision
2. "What is the PubChem compound ID for aspirin?" - Category: Precision

---

## Simple Queries Performed

**Purpose**: Identify real entities for use in evaluation questions

1. Search: "imatinib"
   - Found: CID 5291 - Imatinib (C29H31N7O, 493.6 g/mol)
   - Usage: Drug property questions, kinase inhibitor examples

2. Search: "aspirin"
   - Found: CID 2244 - Aspirin (C9H8O4, 180.16 g/mol)
   - Usage: Basic compound lookup, ChEBI classification

3. FDA drugs count:
   - Found: 17,367 FDA-approved drugs
   - Usage: Completeness questions

4. Kinase inhibitor bioassays:
   - Found: 118,505 assays
   - Usage: Bioassay search questions

5. EGFR pathways:
   - Found: 17+ pathways including "Signaling by EGFR", "EGFR Inhibitor Pathway"
   - Usage: Pathway questions

6. Breast cancer diseases:
   - Found: Multiple disease entities with cross-references
   - Usage: Disease ontology integration questions

---

## Question Generation Opportunities

### Priority 1: Complex Questions (HIGH VALUE)

**Cross-Database Questions**:

1. "What is the ChEMBL identifier for imatinib?"
   - Databases involved: PubChem, ChEMBL
   - Knowledge Required: togoid conversion route pubchem_compound → chembl_compound
   - Category: Integration
   - Difficulty: Medium

2. "Which FDA-approved drugs in PubChem have a ChEBI classification?"
   - Databases involved: PubChem, ChEBI
   - Knowledge Required: FDA role filtering, ChEBI rdf:type pattern, aggregation optimization
   - Category: Integration
   - Difficulty: Hard

3. "Find kinase proteins in PubChem that have PDB structures"
   - Databases involved: PubChem, PDB
   - Knowledge Required: Protein graph FROM clause, pdbx:link_to_pdb, label filtering
   - Category: Integration
   - Difficulty: Medium

4. "What MONDO identifiers are associated with breast cancer in PubChem?"
   - Databases involved: PubChem, MONDO
   - Knowledge Required: Disease graph, skos:closeMatch cross-references
   - Category: Integration
   - Difficulty: Medium

**Performance-Critical Questions**:

1. "How many FDA-approved drugs are in PubChem?"
   - Database: PubChem
   - Knowledge Required: FDA role URI, COUNT with type filter
   - Category: Completeness
   - Difficulty: Easy

2. "What are the most common ChEBI chemical classes among FDA-approved drugs?"
   - Database: PubChem
   - Knowledge Required: FDA pre-filter, ChEBI type pattern, aggregation with LIMIT
   - Category: Structured Query
   - Difficulty: Hard

3. "How many bioassays in PubChem mention cancer?"
   - Database: PubChem
   - Knowledge Required: FROM clause, bif:contains, COUNT
   - Category: Completeness
   - Difficulty: Medium

**Error-Avoidance Questions**:

1. "Find bioassays related to kinase inhibitors"
   - Database: PubChem
   - Knowledge Required: FROM clause for bioassay graph, bif:contains syntax
   - Category: Structured Query
   - Difficulty: Medium

2. "What compounds participate in EGFR signaling pathways?"
   - Database: PubChem
   - Knowledge Required: FROM clause for pathway, RO_0000057 relationship, participant filtering
   - Category: Structured Query
   - Difficulty: Hard

**Complex Filtering Questions**:

1. "Find FDA-approved drugs with molecular weight between 300 and 500"
   - Database: PubChem
   - Knowledge Required: FDA role, descriptor pattern, weight filtering
   - Category: Structured Query
   - Difficulty: Medium

2. "What proteins in PubChem are described as kinases?"
   - Database: PubChem
   - Knowledge Required: FROM clause, skos:prefLabel, FILTER CONTAINS
   - Category: Structured Query
   - Difficulty: Medium

3. "Find pathways that involve ATP as a participant"
   - Database: PubChem
   - Knowledge Required: Pathway graph, RO_0000057, compound URI
   - Category: Structured Query
   - Difficulty: Medium

### Priority 2: Simple Questions (For Coverage & Contrast)

**Entity Lookup Questions**:

1. "What is the PubChem compound ID for aspirin?"
   - Method: get_pubchem_compound_id tool
   - Knowledge Required: None (straightforward)
   - Category: Precision
   - Difficulty: Easy

2. "What is the molecular formula of imatinib?"
   - Method: get_compound_attributes_from_pubchem tool
   - Knowledge Required: None (helper tool)
   - Category: Precision
   - Difficulty: Easy

3. "What is the molecular weight of aspirin?"
   - Method: get_compound_attributes_from_pubchem or SPARQL
   - Knowledge Required: None
   - Category: Precision
   - Difficulty: Easy

**ID Mapping Questions**:

1. "What is the ChEMBL compound ID for PubChem CID 5291?"
   - Method: togoid_convertId
   - Knowledge Required: None
   - Category: Integration
   - Difficulty: Easy

2. "Convert PubChem compound ID 2244 to InChIKey"
   - Method: get_compound_attributes or SPARQL
   - Knowledge Required: None (InChI included in attributes)
   - Category: Precision
   - Difficulty: Easy

---

## Integration Patterns Summary

**PubChem as Source**:
- → ChEMBL: via togoid (compound ID conversion)
- → ChEBI: via rdf:type classification
- → PDB: via protein graph pdbx:link_to_pdb
- → MeSH: via disease graph skos:closeMatch
- → MONDO: via disease graph skos:closeMatch
- → PathBank: via pathway graph rdfs:seeAlso

**PubChem as Target**:
- Various sources → PubChem: via substance submissions
- ChEBI → PubChem: via compound rdf:type

**Complex Multi-Database Paths**:
- PubChem Compound → ChEMBL Compound → ChEMBL Target: Drug-target relationships
- PubChem Disease → MONDO → MONDO ancestors: Disease hierarchy
- PubChem Pathway → Compounds → ChEBI: Pathway metabolite classification

---

## Lessons Learned

### What Knowledge is Most Valuable

1. **Named graph architecture**: Understanding that bioassay, protein, pathway, disease data are in separate graphs requiring FROM clauses
2. **FDA drug filtering**: Essential for any aggregation query to avoid timeout
3. **bif:contains syntax**: Required for efficient text search in Virtuoso
4. **Descriptor pattern**: SIO-based pattern (compound → descriptor → value) for properties
5. **Cross-reference patterns**: skos:closeMatch for external ontologies, rdfs:seeAlso for external databases

### Common Pitfalls Discovered

1. Aggregation without filtering causes 60-second timeout
2. Missing FROM clause may return empty results for some graphs
3. ChEBI classification stored as rdf:type, not separate property
4. Pathway participants include both compounds AND proteins - need filtering

### Recommendations for Question Design

1. FDA drug questions are reliable - 17K drugs is manageable dataset
2. Bioassay title searches work well with bif:contains
3. Disease cross-reference questions valuable for integration testing
4. Avoid unfiltered aggregation questions
5. Pathway questions should specify compound vs protein participants

### Performance Notes

- CID-specific queries: <1 second
- FDA drug queries: 1-3 seconds
- Bioassay text search: 1-2 seconds
- Unfiltered aggregation: TIMEOUT (60s)
- Weight range filtering: <5 seconds for reasonable ranges

---

## Notes and Observations

1. **Undocumented graphs**: MIE file lists 7 graphs but endpoint has 50+ including disease, cooccurrence, endpoint, patent, anatomy, cell, etc.
2. **Disease data rich**: Contains cross-references to MeSH, MONDO, NCI, OMIM, MedGen
3. **Cooccurrence valuable**: Gene-disease associations from literature with counts
4. **Endpoint data**: Contains actual bioactivity measurements (IC50, EC50) - valuable for drug discovery questions
5. **Helper tools useful**: get_pubchem_compound_id and get_compound_attributes_from_pubchem simplify common lookups

---

## Next Steps

**Recommended for Question Generation**:
- Priority questions: FDA drug property queries, bioassay searches, disease cross-references
- Avoid: Unfiltered aggregation, complex multi-graph joins
- Focus areas: Drug discovery, compound-disease relationships, pathway integration

**Further Exploration Needed**:
- Endpoint graph structure for bioactivity value queries
- Cell line data in cell graph
- Anatomy data relationships
- Patent linkage patterns

---

**Session Complete - Ready for Next Database**

```
Database: pubchem
Status: ✅ COMPLETE
Report: /evaluation/exploration/pubchem_exploration.md
Patterns Tested: 8
Questions Identified: 20+
Integration Points: 6
```
