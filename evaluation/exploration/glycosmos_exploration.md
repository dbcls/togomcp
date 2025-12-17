# GlyCosmos RDF Database Exploration Report

## Database Overview
- **Purpose**: Comprehensive glycoscience portal integrating glycan structures, glycoproteins, glycosylation sites, glycogenes, glycoepitopes, and lectin-glycan interactions
- **Scope**: Multi-species glycobiology research and biomarker discovery across 100+ named graphs
- **Key Data Types**:
  - Glycan structures (GlyTouCan IDs - G[0-9]{5}[A-Z]{2})
  - Glycoproteins with glycosylation site annotations
  - Glycogenes (genes involved in glycosylation)
  - Glycoepitopes (immunological epitopes)
  - Lectin-glycan interactions
- **Main Entities**:
  - 117,864 glycans
  - 153,178 glycoproteins
  - 414,798 glycosylation sites
  - 423,164 glycogenes
  - 173 glycoepitopes
  - 739 lectins

## Schema Analysis (from MIE file)

### Main Properties Available
1. **Glycan Level**:
   - `glytoucan:has_primary_id` - GlyTouCan accession (G[0-9]{5}[A-Z]{2})
   - `glycan:has_Resource_entry` - External database links
   - Coverage: ~99.8% have primary IDs, ~86% have resource entries

2. **Glycoprotein Level**:
   - `rdfs:label` - Protein name (~17% coverage)
   - `rdfs:seeAlso` - External database links (UniProt, PubChem, GlyGen)
   - `glycan:has_taxon` - Organism taxonomy (~18% coverage)
   - `glycoconjugate:glycosylated_at` - Glycosylation site links
   - Total: 153,178 glycoproteins

3. **Glycosylation Site Level**:
   - `sio:SIO_000772` - Parent protein reference
   - `faldo:location` - Sequence position (>90% coverage)
   - `glycoconjugate:has_saccharide` - Attached glycan structure
   - Total: 414,798 sites, avg 2.6 sites/protein, max 276 sites/protein

4. **Glycogene Level**:
   - `rdfs:label` - Gene symbol (~32% coverage)
   - `dcterms:description` - Functional description (~8% coverage)
   - `rdfs:seeAlso` - NCBI Gene, KEGG links
   - `glycan:has_taxon` - Organism (~0.4% coverage)
   - Total: 423,164 glycogenes

5. **Glycoepitope Level**:
   - `rdfs:label` - Epitope name
   - `skos:altLabel` - Alternative names/nomenclature
   - `glycoepitope:has_antibody` - Antibody recognition
   - `glycoepitope:organism` - Source organism
   - `glycoepitope:tissue` - Tissue expression
   - Total: 173 epitopes

### Important Relationships
- **Glycan-Database**: `glycan:has_Resource_entry` - Links to ChEBI, PubChem, KEGG, PDB
- **Protein-External**: `rdfs:seeAlso` - Links to UniProt, PubChem, GlyGen
- **Gene-External**: `rdfs:seeAlso` - Links to NCBI Gene, KEGG
- **Site-Protein**: `sio:SIO_000772` - Glycosylation site to parent protein
- **Site-Glycan**: `glycoconjugate:has_saccharide` - Attached glycan structure
- **Epitope-Antibody**: `glycoepitope:has_antibody` - Recognition relationships

### Query Patterns Observed
1. **FROM clause mandatory**: Multi-graph architecture requires explicit graph specification
2. **bif:contains for labels**: Full-text search with relevance scoring on rdfs:label
3. **Early filtering critical**: Use taxon, ID filters before complex joins
4. **LIMIT essential**: Large datasets (414K sites) require pagination
5. **OPTIONAL for sparse data**: Many properties have low coverage

### Critical Performance Notes
- **ALWAYS specify FROM clause** - reduces search space 10-100x
- Use `bif:contains` for label searches (full-text index + relevance)
- Add early taxonomy filtering for glycoprotein queries
- Essential pagination with LIMIT for large datasets
- Multi-graph joins require explicit FROM for each graph

## Search Queries Performed

### Query 1: Glycan Listing with GlyTouCan IDs
**Query**: Basic glycan discovery
```sparql
SELECT ?glycan ?glycanId
FROM <http://rdf.glytoucan.org/core>
WHERE {
  ?glycan a glycan:Saccharide ;
          glytoucan:has_primary_id ?glycanId .
}
LIMIT 10
```
**Results**: Retrieved 10 glycan entries:
- G00031MO, G51331BY, G00071MO, G50375DL
- All follow GlyTouCan ID pattern: G[0-9]{5}[A-Z]{2}

### Query 2: Lewis Antigen Epitope Search
**Query**: Full-text search for Lewis epitopes
```sparql
SELECT ?epitope ?label
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  ?epitope a glycan:Glycan_epitope ;
           rdfs:label ?label .
  ?label bif:contains "'Lewis'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 15
```
**Results**: Found 15 Lewis antigen variants:
- Lewis a (EP0007)
- Sialyl Lewis a (EP0008)
- Lewis b (EP0010)
- Lewis x (EP0011)
- Sialyl Lewis x (EP0012)
- Multiple sulfated and modified variants
- Demonstrates rich epitope nomenclature

### Query 3: Lewis a Epitope Detailed Annotations
**Query**: Antibodies and tissue expression for EP0007
```sparql
SELECT ?antibody ?organism ?tissue ?altLabel
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  <http://www.glycoepitope.jp/epitopes/EP0007> a glycan:Glycan_epitope .
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> glycoepitope:has_antibody ?antibody }
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> glycoepitope:organism ?organism }
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> glycoepitope:tissue ?tissue }
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> skos:altLabel ?altLabel }
}
```
**Results**: Lewis a (EP0007) has:
- 15 antibodies (AN0015, AN0019, AN0102, etc.)
- Tissue expression: stomach epithelial cells, plasma, colorectal, saliva, erythrocytes
- Alternative label: Le<sup>a</sup>
- Demonstrates comprehensive immunological annotations

### Query 4: Glycoprotein Species Distribution
**Query**: Count glycoproteins by taxonomy
```sparql
SELECT ?taxon (COUNT(DISTINCT ?protein) as ?count)
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           glycan:has_taxon ?taxon .
}
GROUP BY ?taxon
ORDER BY DESC(?count)
LIMIT 15
```
**Results**: Species with most glycoproteins:
- Human (9606): 16,604 proteins
- Mouse (10090): 10,713 proteins
- Rat (10116): 2,576 proteins
- Arabidopsis (3702): 2,251 proteins
- C. elegans (6239): 1,447 proteins
- Shows strong human/mouse focus with diverse organisms

### Query 5: Human Glycosylation Sites with Positions
**Query**: Retrieve site-specific positions for human proteins
```sparql
SELECT ?protein ?site ?position
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
           glycoconjugate:glycosylated_at ?site .
  ?site faldo:location/faldo:position ?position .
}
LIMIT 20
```
**Results**: Retrieved 20 human glycosylation sites:
- Positions: 110, 85, 377, etc.
- Site IDs: SITE00137482, SITE00151333, etc.
- Demonstrates >90% position coverage

### Query 6: Glycogenes with Receptor Function
**Query**: Search genes by functional description
```sparql
SELECT ?gene ?symbol ?description
FROM <http://rdf.glycosmos.org/glycogenes>
WHERE {
  ?gene a glycan:Glycogene ;
        rdfs:label ?symbol ;
        dcterms:description ?description .
  FILTER(CONTAINS(LCASE(?description), "receptor"))
}
LIMIT 15
```
**Results**: Found 15 receptor glycogenes:
- Kdr: kinase insert domain receptor
- Erbb4: erb-b2 receptor tyrosine kinase 4
- INSR: insulin receptor
- EPHA7: EPH receptor A7
- TLR4: toll like receptor 4
- Ngfr: nerve growth factor receptor
- Shows diverse receptor types

### Query 7: Glycan Resource Entry Links
**Query**: External database cross-references
```sparql
SELECT ?glycanId ?entry
FROM <http://rdf.glytoucan.org/core>
WHERE {
  ?glycan glytoucan:has_primary_id ?glycanId ;
          glycan:has_Resource_entry ?entry .
}
LIMIT 20
```
**Results**: Retrieved 20 glycan-resource links:
- All entries link to http://rdf.glycoinfo.org/resource-entry/
- ~86% of glycans have resource entries
- Links to: Carbbank (44K), GlycomeDB (39K), PubChem (32K), ChEBI (11K), KEGG (10K), PDB (6K)

### Query 8: Glycoprotein UniProt Links
**Query**: Protein cross-references to UniProt
```sparql
SELECT ?protein ?externalDB
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           rdfs:seeAlso ?externalDB .
  FILTER(CONTAINS(STR(?externalDB), "purl.uniprot.org/uniprot"))
}
LIMIT 15
```
**Results**: Found 15 protein-UniProt links:
- P13224, P15529, P37238, P68134 (Swiss-Prot IDs)
- A0A7K6A998, E5FQ95, Q21178 (TrEMBL IDs)
- Total: 139K glycoproteins linked to UniProt

## SPARQL Queries Tested

```sparql
# Query 1: Glycan Discovery - Basic GlyTouCan ID Retrieval
# Purpose: Identify available glycan structures
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glytoucan: <http://www.glytoucan.org/glyco/owl/glytoucan#>

SELECT ?glycan ?glycanId
FROM <http://rdf.glytoucan.org/core>
WHERE {
  ?glycan a glycan:Saccharide ;
          glytoucan:has_primary_id ?glycanId .
}
LIMIT 10

# Results: Successfully retrieved 10 glycan entries with GlyTouCan IDs
# Verification: All IDs follow pattern G[0-9]{5}[A-Z]{2} (e.g., G00031MO, G51331BY)
```

```sparql
# Query 2: Epitope Full-Text Search - Lewis Antigens
# Purpose: Find epitopes using relevance-ranked full-text search
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?epitope ?label
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  ?epitope a glycan:Glycan_epitope ;
           rdfs:label ?label .
  ?label bif:contains "'Lewis'" option (score ?sc)
}
ORDER BY DESC(?sc)
LIMIT 15

# Results: Retrieved 15 Lewis antigen variants including Lewis a, Lewis x, Sialyl Lewis a
# Key finding: bif:contains provides relevance scoring superior to FILTER(CONTAINS())
```

```sparql
# Query 3: Epitope Annotations - Immunological Context
# Purpose: Retrieve antibody and tissue expression data
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glycoepitope: <http://www.glycoepitope.jp/epitopes/glycoepitope.owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?antibody ?organism ?tissue ?altLabel
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  <http://www.glycoepitope.jp/epitopes/EP0007> a glycan:Glycan_epitope .
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> glycoepitope:has_antibody ?antibody }
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> glycoepitope:organism ?organism }
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> glycoepitope:tissue ?tissue }
  OPTIONAL { <http://www.glycoepitope.jp/epitopes/EP0007> skos:altLabel ?altLabel }
}

# Results: Lewis a (EP0007) has 15 antibodies and expression in 5 tissues
# Tissues: stomach epithelial cells, plasma, colorectal, saliva, erythrocytes
# Alternative label: Le<sup>a</sup>
```

```sparql
# Query 4: Species Distribution - Glycoprotein Taxonomy
# Purpose: Aggregate statistics by organism
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>

SELECT ?taxon (COUNT(DISTINCT ?protein) as ?count)
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           glycan:has_taxon ?taxon .
}
GROUP BY ?taxon
ORDER BY DESC(?count)
LIMIT 15

# Results: Top species - Human (16,604), Mouse (10,713), Rat (2,576)
# Total coverage: 18% of glycoproteins have taxonomy annotations
# Demonstrates strong human/mouse focus
```

```sparql
# Query 5: Position-Specific Glycosylation - Human Sites
# Purpose: Retrieve sequence positions for human glycosylation sites
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glycoconjugate: <http://purl.jp/bio/12/glyco/conjugate#>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>

SELECT ?protein ?site ?position
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
           glycoconjugate:glycosylated_at ?site .
  ?site faldo:location/faldo:position ?position .
}
LIMIT 20

# Results: Retrieved 20 glycosylation sites with exact positions (85, 110, 377)
# Coverage: >90% of sites have position annotations
# Average sites per protein: 2.6, maximum: 276
```

## Interesting Findings

### 1. Specific Entities for Questions
- **Epitope EP0007**: Lewis a antigen with 15 antibodies, 5 tissue types
- **Human taxonomy 9606**: 16,604 glycoproteins, largest dataset
- **Glycan G00031MO**: GlyTouCan registered structure with resource entries
- **Glycogene INSR (3643)**: Insulin receptor involved in glycosylation
- **Site SITE00137482**: Glycosylation at position 110

### 2. Unique Properties
- **Multi-graph architecture**: 100+ graphs for modular data management
- **GlyTouCan IDs**: Standardized glycan identifiers (G[0-9]{5}[A-Z]{2})
- **Lewis antigen family**: 15+ variants including sulfated forms
- **Position specificity**: >90% of sites have exact sequence positions
- **Epitope-antibody-tissue triad**: Comprehensive immunological context

### 3. Connections to Other Databases
- **UniProt**: 139K glycoprotein links
- **NCBI Gene**: 423K glycogene links
- **ChEBI**: 11K glycan chemical structures
- **PubChem**: 32K glycan compounds
- **KEGG**: 10K pathway/compound links
- **PDB**: 6K structure entries

### 4. Specific Verifiable Facts
- Human has 16,604 glycoproteins (most of any species)
- Lewis a epitope (EP0007) has 15 antibodies
- 173 total glycoepitopes in database
- Average 2.6 glycosylation sites per protein
- Maximum 276 glycosylation sites on single protein
- ~86% glycans have external database cross-references

## Question Opportunities by Category

### Precision
- "What is the GlyTouCan ID for glycan G00031MO in the GlyCosmos database?"
- "How many antibodies recognize the Lewis a epitope (EP0007)?"
- "What is the exact sequence position of glycosylation site SITE00137482?"
- "What is the alternative nomenclature (skos:altLabel) for Lewis a antigen?"

### Completeness
- "How many glycoproteins are annotated for humans (taxonomy 9606) in GlyCosmos?"
- "List all Lewis antigen variants found in the glycoepitope database"
- "What tissues express the Lewis a epitope (EP0007)?"
- "How many glycogenes have 'receptor' in their functional description?"

### Integration
- "What is the UniProt ID for glycoprotein P02763 in GlyCosmos?"
- "Convert glycan G00031MO to its external ChEBI or PubChem identifier"
- "Link glycosylation site SITE00137482 to its parent protein"
- "Find NCBI Gene IDs for glycogenes involved in insulin signaling"

### Currency
- "What are the most recently added glycan structures in GlyTouCan?"
- "Which species have had new glycoprotein annotations added recently?"
- "What new glycoepitopes have been characterized since 2024?"

### Specificity
- "What is the molecular structure of Sialyl 6-Sulfo Lewis x (EP0015)?"
- "Find glycoproteins with more than 100 glycosylation sites"
- "What antibody AN0015 recognizes which Lewis antigen variants?"
- "Identify glycogenes encoding EPH receptors in the EPHA family"

### Structured Query
- "Find all human glycoproteins with glycosylation sites at position 85"
- "List all glycoepitopes expressed in stomach epithelial cells"
- "Retrieve glycogenes with 'kinase' in description for mouse (10090)"
- "Count glycosylation sites per protein for human glycoproteins, sorted by site count"

## Notes

### Database Characteristics
- **Multi-graph architecture**: 100+ named graphs for modular organization
- **Large scale**: 414K glycosylation sites, 423K glycogenes, 153K glycoproteins
- **Sparse labels**: Glycans <1%, proteins 17%, genes 32% have labels
- **Taxonomy coverage**: Proteins 18%, genes 0.4%
- **Strong human focus**: 16,604 human glycoproteins (largest dataset)
- **Comprehensive epitopes**: 173 epitopes with antibody and tissue data

### Limitations and Challenges
1. **FROM clause mandatory**: Without it, queries timeout searching all 100+ graphs
2. **Large dataset pagination**: 414K sites require LIMIT and early filtering
3. **Sparse property coverage**: Many entities lack labels or descriptions
4. **Low taxonomy coverage**: Only 18% proteins, 0.4% genes have taxon
5. **Label search limitations**: bif:contains works well for labels, not descriptions

### Best Practices for Querying
1. **Always specify FROM graph**: Reduces search space 10-100x
2. **Use bif:contains for labels**: Full-text index + relevance scoring
3. **Early taxonomy filtering**: Filter by species before complex joins
4. **Essential pagination**: Always add LIMIT for large datasets
5. **OPTIONAL for sparse data**: Use OPTIONAL for properties with low coverage
6. **Multi-graph joins**: Specify FROM for each graph explicitly
7. **Filter over contains for descriptions**: Use FILTER(CONTAINS()) for non-indexed fields

### Data Quality Observations
- **High ID coverage**: ~99.8% glycans have GlyTouCan IDs
- **Position annotations**: >90% sites have exact sequence positions
- **Cross-reference richness**: ~86% glycans link to external databases
- **Epitope completeness**: All 173 epitopes have comprehensive annotations
- **UniProt integration**: 139K glycoproteins linked to UniProt

### Integration Opportunities
- **UniProt**: Via rdfs:seeAlso for protein sequences and functions
- **NCBI Gene**: Via rdfs:seeAlso for gene information
- **ChEBI**: Via glycan:has_Resource_entry for chemical structures
- **PubChem**: Via multiple paths for compound data
- **KEGG**: Via resource entries for pathway context
- **PDB**: Via resource entries for 3D structures
- **TogoID**: For systematic cross-database ID conversion

### Question Design Insights
- **Epitope questions excellent**: 173 entities, rich annotations, specific antibodies/tissues
- **Species distribution queries**: Strong aggregation potential with taxon
- **Position-specific questions**: >90% sites have coordinates, unique specificity
- **Lewis antigen family**: 15+ variants enable comparison questions
- **Human-focused questions**: Largest dataset (16,604 proteins)
- **Cross-reference questions**: 86% glycans have external links
- **Avoid global counts**: Use early filtering and LIMIT instead

### Unique Value Propositions
1. **Glycan registry**: Standardized GlyTouCan IDs for structures
2. **Position-specific glycosylation**: Exact sequence locations (FALDO)
3. **Epitope-antibody-tissue networks**: Comprehensive immunological context
4. **Multi-species coverage**: Human, mouse, rat, plants, worms
5. **Lewis antigen family**: Complete set with sulfated/sialylated variants
6. **Glycogene annotations**: Functional descriptions for 423K genes
7. **Multi-graph modularity**: Specialized graphs for different data types
