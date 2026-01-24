# ChEBI Exploration Report

## Database Overview
- **Purpose**: ChEBI (Chemical Entities of Biological Interest) is an ontology database for chemical entities with biological relevance
- **Key data types**: Small molecules, atoms, ions, functional groups, macromolecules with hierarchical classification
- **Total entities**: 223,078 chemical classes
- **Entities with molecular formulas**: 192,688 (~86%)
- **Endpoint**: https://rdfportal.org/ebi/sparql
- **Search tool**: OLS4:searchClasses

## Schema Analysis (from MIE file)
### Main Properties
- `rdfs:label` - Chemical name
- `chebi:formula` - Molecular formula (uses chebi/ namespace)
- `chebi:mass` - Molecular mass
- `chebi:smiles` - SMILES notation
- `chebi:inchi` - InChI string
- `chebi:inchikey` - InChI key (standardized)
- `oboInOwl:hasDbXref` - Cross-references to external databases
- `oboInOwl:hasRelatedSynonym` / `hasExactSynonym` - Alternative names

### Important Relationships
- `rdfs:subClassOf` - Hierarchical classification (ontology structure)
- Chemical relationships via OWL restrictions:
  - `chebi:is_conjugate_acid_of` / `is_conjugate_base_of`
  - `chebi:is_tautomer_of`
  - `chebi:is_enantiomer_of`
  - `RO_0000087` (has_role) - Biological roles

**CRITICAL**: ChEBI uses TWO namespaces:
- Data properties: `http://purl.obolibrary.org/obo/chebi/` (formula, mass, smiles)
- Relationship properties: `http://purl.obolibrary.org/obo/chebi#` (is_conjugate_acid_of)

### Query Patterns
- Use `bif:contains` for full-text keyword search (Virtuoso backend)
- Filter by CHEBI_ URI prefix to exclude ontology metadata classes
- Use OWL restriction patterns for chemical relationships

## Search Queries Performed

1. **Query: "antibiotic"** → 494 total results
   - Found: CHEBI:80084 (Antibiotic TA), CHEBI:87114 (antibiotic fungicide), CHEBI:39208 (antibiotic insecticide), CHEBI:86478 (antibiotic antifungal agent)
   - Shows classification of antibiotics by application type

2. **Query: "metformin"** → 5 results
   - Found: CHEBI:6801 (metformin - main entry), CHEBI:6802 (metformin hydrochloride), CHEBI:90688 (metformin(1+) - protonated form), CHEBI:90875 (Synjardy - combination drug)
   - Demonstrates drug and salt/ionization forms

3. **Query: "caffeine"** → 16 results
   - Found: CHEBI:27732 (caffeine - main entry), CHEBI:31332 (caffeine monohydrate), CHEBI:177330 (caffeine-d9 - deuterated), CHEBI:62205 (3-methylxanthine - metabolite)
   - Shows metabolites and isotope-labeled variants

4. **Query: "statins"** → 8 results
   - Found: CHEBI:87631 (statin - parent class), CHEBI:87635 (synthetic statin), CHEBI:87633 (semi-synthetic statin), CHEBI:39548 (atorvastatin), CHEBI:63618 (pravastatin)
   - Hierarchical drug classification

5. **Query: "omega-3 fatty acid"** → 50,688 results (includes related terms)
   - Found: CHEBI:25681 (omega-3 fatty acid - main class)
   - Definition: Polyunsaturated fatty acids with double bond at ω-3 position
   - Large result set due to fatty acid derivatives

## SPARQL Queries Tested

### Query 1: Get molecular properties of caffeine (CHEBI:27732)
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>
PREFIX obo: <http://purl.obolibrary.org/obo/>

SELECT ?label ?formula ?mass ?inchikey
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  obo:CHEBI_27732 rdfs:label ?label .
  OPTIONAL { obo:CHEBI_27732 chebi:formula ?formula }
  OPTIONAL { obo:CHEBI_27732 chebi:mass ?mass }
  OPTIONAL { obo:CHEBI_27732 chebi:inchikey ?inchikey }
}
```
**Results**: label="caffeine", formula="C8H10N4O2", mass="194.19076", inchikey="RYYVLZVUVIJVGH-UHFFFAOYSA-N"

### Query 2: Count total chemical entities
```sparql
SELECT (COUNT(DISTINCT ?entity) as ?total)
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?entity a owl:Class .
  FILTER(STRSTARTS(STR(?entity), "http://purl.obolibrary.org/obo/CHEBI_"))
}
```
**Results**: 223,078 total chemical entities

### Query 3: Count entities with molecular formulas
```sparql
SELECT (COUNT(DISTINCT ?entity) as ?with_formula)
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?entity a owl:Class ;
          chebi:formula ?formula .
  FILTER(STRSTARTS(STR(?entity), "http://purl.obolibrary.org/obo/CHEBI_"))
}
```
**Results**: 192,688 entities with formulas (~86% coverage)

### Query 4: Cross-reference database coverage
```sparql
SELECT ?prefix (COUNT(?entity) as ?count)
FROM <http://rdf.ebi.ac.uk/dataset/chebi>
WHERE {
  ?entity a owl:Class ;
          oboInOwl:hasDbXref ?xref .
  BIND(STRBEFORE(?xref, ":") as ?prefix)
}
GROUP BY ?prefix ORDER BY DESC(?count) LIMIT 15
```
**Results** (top cross-reference sources):
- PMID: 118,314 cross-references (literature)
- Chemspider: 53,381
- LINCS: 41,353
- CAS: 29,869
- KEGG: 22,364
- HMDB: 19,788
- Reaxys: 17,769
- LIPID_MAPS_instance: 12,642
- GlyTouCan: 10,621
- MetaCyc: 7,323
- Wikipedia: 6,725

## Cross-Reference Analysis

### Entity counts (unique entities with mappings):
ChEBI provides extensive cross-references stored as literal strings in format "PREFIX:ID":
- Literature (PMID): 118,314 cross-references to PubMed
- CAS Registry: 29,869 mappings
- KEGG compounds: 22,364 mappings
- HMDB (metabolomics): 19,788 mappings

### Integration with co-located databases (EBI endpoint):
- ChEMBL links via `skos:exactMatch`
- Reactome links via BioPAX `bp:xref` with ChEBI IDs

## Interesting Findings

**Findings requiring actual queries (non-trivial):**

1. **223,078 total chemical entities** in ChEBI (requires COUNT query)
   - 192,688 have molecular formulas (~86%)
   - Shows comprehensive coverage with structural data

2. **Cross-reference richness**: Over 118,000 PubMed references linking chemicals to literature
   - Enables compound-to-literature queries
   - Top referenced publication: PMID:20671299 (713 compounds reference it)

3. **Drug classification hierarchy**: 
   - Statins are organized into synthetic (CHEBI:87635), semi-synthetic (CHEBI:87633), and naturally occurring (CHEBI:87632)
   - Example: Atorvastatin (CHEBI:39548) classified under synthetic statins

4. **Caffeine molecular properties** (CHEBI:27732):
   - Formula: C8H10N4O2
   - Mass: 194.19076
   - InChIKey: RYYVLZVUVIJVGH-UHFFFAOYSA-N

5. **Metformin** (CHEBI:6801) - antidiabetic drug with multiple related entries for salt forms and ionization states

6. **Dual namespace issue**: Data properties use `/chebi/` while relationship properties use `#chebi#` - critical for correct queries

## Question Opportunities by Category

### Precision (specific IDs, measurements)
- ✅ "What is the ChEBI ID for metformin?" → CHEBI:6801
- ✅ "What is the molecular formula of caffeine (CHEBI:27732)?" → C8H10N4O2
- ✅ "What is the InChIKey for atorvastatin (CHEBI:39548)?"
- ✅ "What is the molecular mass of metformin in ChEBI?"

### Completeness (counts, comprehensive lists)
- ✅ "How many chemical entities are in ChEBI?" → 223,078
- ✅ "How many ChEBI entities have molecular formulas?" → 192,688
- ✅ "How many ChEBI entities have KEGG cross-references?" → 22,364
- ✅ "How many statin drugs are classified in ChEBI?"

### Integration (cross-database linking)
- ✅ "What is the CAS registry number for caffeine in ChEBI?" (from hasDbXref)
- ✅ "Find ChEBI entities with HMDB cross-references"
- ✅ "Link ChEBI compounds to KEGG compound IDs"
- ✅ "What ChEMBL molecules match to ChEBI entities?" (via skos:exactMatch on EBI endpoint)

### Currency (recent/updated data)
- ✅ "What is the current count of chemical entities in ChEBI?" (database updated monthly)

### Specificity (niche/specialized)
- ✅ "What is the ChEBI ID for omega-3 fatty acid class?" → CHEBI:25681
- ✅ "What antibiotic subclasses are defined in ChEBI?"
- ✅ "What caffeine metabolites are in ChEBI?"

### Structured Query (complex filtering)
- ✅ "Find all statin drugs (synthetic and semi-synthetic) in ChEBI"
- ✅ "Find chemical entities with both CAS and KEGG cross-references"
- ✅ "Find all conjugate acid/base pairs in ChEBI"
- ✅ "Find alkaloids classified as purine alkaloids"

## Notes

### Limitations
- Abstract chemical classes lack molecular properties (formula, mass)
- Cross-references stored as literal strings require parsing
- Some deprecated entities remain in database (check owl:deprecated)

### Best Practices
- Always filter by `CHEBI_` URI prefix to get only chemical entities
- Use `bif:contains` for keyword search instead of `FILTER CONTAINS`
- Use correct namespace for data properties (chebi/) vs relationship properties (chebi#)
- Use OPTIONAL for molecular properties as not all entities have them

### Data Quality
- Manual curation ensures high accuracy
- Monthly updates
- Well-maintained cross-references to ChEMBL and Reactome via co-located EBI endpoint
