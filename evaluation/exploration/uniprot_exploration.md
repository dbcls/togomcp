# UniProt Exploration Report

## Database Overview
- **Purpose**: Comprehensive protein sequence and functional information
- **Scope**: Integrates Swiss-Prot (manually curated, 923K entries) and TrEMBL (automatically annotated, 444M entries)
- **Key distinction**: Always filter by `up:reviewed 1` for quality Swiss-Prot data

## Schema Analysis (from MIE file)
### Main Properties
- `up:Protein`: Core entity type
- `up:mnemonic`: Short identifier (e.g., "BRCA1_HUMAN")
- `up:organism`: Link to NCBI Taxonomy
- `up:sequence`: Link to isoform/sequence data
- `up:annotation`: Various annotation types (Function, Signal_Peptide, etc.)
- `up:classifiedWith`: GO terms and other classifications
- `up:enzyme`: EC number classification
- `up:recommendedName/up:fullName`: Protein name

### Important Relationships
- Cross-references via `rdfs:seeAlso` to 200+ databases (PDB, EMBL, Ensembl, etc.)
- Taxonomic hierarchy via `rdfs:subClassOf`
- GO terms filtering: `STRSTARTS(STR(?goTerm), "http://purl.obolibrary.org/obo/GO_")`

### Query Patterns
- CRITICAL: Always use `up:reviewed 1` filter
- Use `bif:contains` for text search but split property paths
- Organism filter: `up:organism <http://purl.uniprot.org/taxonomy/TAXID>`

## Search Queries Performed

1. **Query: "BRCA1 human"**
   - P38398: Breast cancer type 1 susceptibility protein (Human)
   - Q95153: BRCA1 homolog (Dog)
   - P48754: BRCA1 homolog (Mouse)
   - Q9BX63: Fanconi anemia group J protein (BRCA1-interacting)

2. **Query: "insulin human"**
   - P01308: Insulin (Human) - canonical insulin
   - P06213: Insulin receptor (Human)
   - P14735: Insulin-degrading enzyme (Human)

3. **Query: "hemoglobin alpha human"**
   - P69905: Hemoglobin subunit alpha (Human)
   - P68871: Hemoglobin subunit beta (Human)
   - P02042: Hemoglobin subunit delta (Human)

4. **Query: "tubulin beta"**
   - Q13509: Tubulin beta-3 chain (Human)
   - P68371: Tubulin beta-4B chain (Human)
   - P04350: Tubulin beta-4A chain (Human)

5. **Query: "EGFR epidermal growth factor receptor"**
   - P00533: EGFR (Human) - key cancer target
   - Q01279: EGFR (Mouse)

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
# Result: 40,209 reviewed human proteins
```

```sparql
# Query 2: Get protein details for BRCA1 (P38398) found via search
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX uniprot: <http://purl.uniprot.org/uniprot/>
SELECT ?protein ?mnemonic ?fullName ?mass
WHERE {
  VALUES ?protein { uniprot:P38398 }
  ?protein up:mnemonic ?mnemonic ;
           up:recommendedName ?name ;
           up:sequence ?seq .
  ?name up:fullName ?fullName .
  ?seq up:mass ?mass .
}
# Result: BRCA1_HUMAN, mass 207,721 Da
```

```sparql
# Query 3: Count human kinases by name
PREFIX up: <http://purl.uniprot.org/core/>
SELECT (COUNT(*) as ?kinase_count)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:recommendedName ?name .
  ?name up:fullName ?fullName .
  ?fullName bif:contains "'kinase'"
}
# Result: 1,396 human proteins with "kinase" in name
```

```sparql
# Query 4: Count human proteins with signal peptides
PREFIX up: <http://purl.uniprot.org/core/>
SELECT (COUNT(*) as ?signal_peptide_count)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:annotation ?annot .
  ?annot a up:Signal_Peptide_Annotation .
}
# Result: 7,158 human proteins with signal peptides
```

## Cross-Reference Analysis

### Links to other databases (via rdfs:seeAlso)
- PDB structures: ~14-25% of reviewed proteins
- AlphaFold predictions: >98% of reviewed proteins
- InterPro domains: >98%
- Ensembl: high coverage
- NCBI Gene: ~90%
- Reactome pathways: ~30%

### Cross-database integration
- Shared SIB endpoint with Rhea enables enzyme-reaction queries
- Can link via EC numbers to Rhea reactions
- GO terms accessible via `up:classifiedWith`

## Interesting Findings

**Discoveries requiring actual database queries:**

1. **40,209 reviewed human proteins** in Swiss-Prot (requires COUNT query)
2. **BRCA1 (P38398)** has molecular mass of 207,721 Da (requires query, not in MIE)
3. **1,396 human kinases** identified by name pattern (requires bif:contains search)
4. **7,158 human proteins** have signal peptides (requires annotation type query)
5. **P01308** is canonical human insulin (found via search, not in MIE examples)
6. **P00533** is human EGFR (found via search - key cancer drug target)

**Key for question design:**
- Real entity IDs discovered: P38398 (BRCA1), P01308 (insulin), P69905 (hemoglobin alpha), P00533 (EGFR), P06213 (insulin receptor)
- These are NOT in MIE examples (which uses P04637, P17612, P86925)

## Question Opportunities by Category

### Precision
- ✅ "What is the UniProt ID for human BRCA1?" → P38398 (requires search)
- ✅ "What is the molecular mass of human insulin (UniProt P01308)?" → requires query
- ✅ "What is the UniProt ID for human hemoglobin alpha?" → P69905 (requires search)
- ✅ "What is the UniProt mnemonic for EGFR?" → EGFR_HUMAN (requires lookup)

### Completeness  
- ✅ "How many reviewed human proteins are in UniProt Swiss-Prot?" → 40,209
- ✅ "How many human proteins have 'kinase' in their name?" → 1,396
- ✅ "How many human proteins have signal peptides?" → 7,158

### Integration
- ✅ "What NCBI Gene ID corresponds to UniProt P38398 (BRCA1)?" → requires TogoID
- ✅ "What EC number is assigned to BRCA1?" → 2.3.2.27 (found via query)

### Currency
- ✅ "How many human proteins are currently in UniProt Swiss-Prot?" → 40,209 (changes with releases)

### Specificity
- ✅ "What is the UniProt ID for SpCas9?" → Q99ZW2 (already in examples, but good pattern)
- Can find other specific proteins via search

### Structured Query
- ✅ "Find human kinases in UniProt" → requires filtering
- ✅ "Find human proteins with signal peptides" → requires annotation type filtering

## Notes
- Always use `up:reviewed 1` to avoid timeouts and get quality data
- `bif:contains` requires split property paths (don't use `/`)
- Search tool (`search_uniprot_entity`) is effective for finding real protein IDs
- Cross-references provide integration opportunities with many databases
- Organism filtering must use taxonomy URI, not mnemonic patterns
