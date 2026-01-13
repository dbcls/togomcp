# GlyCosmos Exploration Report

## Database Overview
- **Purpose**: Comprehensive glycoscience portal integrating glycan structures, glycoproteins, glycosylation sites, glycogenes, and glycoepitopes
- **Scope**: 117,571 glycans, 153,178 glycoproteins, 414,798 glycosylation sites, 423,164 glycogenes, 173 glycoepitopes
- **Key data types**: GlyTouCan structures, glycosylation sites with FALDO positions, glycogene annotations
- **Focus**: Multi-species glycobiology research, biomarker discovery, lectin-glycan interactions

## Schema Analysis (from MIE file)

### Main Properties Available
- **Glycans**: `glycan:Saccharide` with `glytoucan:has_primary_id`, `glycan:has_Resource_entry`
- **Glycoproteins**: `glycan:Glycoprotein` with `rdfs:label`, `glycan:has_taxon`, `glycoconjugate:glycosylated_at`
- **Glycosylation sites**: `glycoconjugate:Glycosylation_Site` with `sio:SIO_000772` (protein ref), `faldo:location/faldo:position`
- **Glycogenes**: `glycan:Glycogene` with `rdfs:label`, `dcterms:description`, `glycan:has_taxon`
- **Glycoepitopes**: `glycan:Glycan_epitope` with `rdfs:label`, `skos:altLabel`, `glycoepitope:has_antibody`
- **Lectins**: `sugarbind:Lectin` with `sugarbind:uniprotId`

### Important Relationships
- Multi-graph architecture: separate graphs for core glycans, glycoproteins, glycogenes, epitopes
- FALDO for glycosylation site positions
- Cross-references to ChEBI, PubChem, KEGG, PDB for glycans
- UniProt, NCBI Gene links for proteins and genes
- NCBI Taxonomy for species

### Query Patterns Observed
- Always specify FROM clause (100+ graphs)
- Use `bif:contains` for label searches with relevance scoring
- Filter by taxonomy early for performance
- Use LIMIT for large datasets (414K+ glycosylation sites)

## Search Queries Performed

### Query 1: Lewis antigen epitopes
- **Search**: `bif:contains "'Lewis'"`
- **Results**: 20 Lewis-related epitopes:
  - EP0007 - Lewis a
  - EP0008 - Sialyl Lewis a
  - EP0011 - Lewis x
  - EP0012 - Sialyl Lewis x
  - Various sulfo and hybrid variants

### Query 2: Total glycans count
- **Search**: COUNT with GlyTouCan IDs
- **Results**: 117,571 glycan structures

### Query 3: Human glycoproteins
- **Search**: Filter by taxonomy/9606
- **Results**: Found many human glycoproteins:
  - P13224 - Platelet glycoprotein Ib beta chain
  - P15529 - Membrane cofactor protein
  - MHC class I antigens (various)

### Query 4: Human glycosylation sites with positions
- **Search**: Glycoprotein → glycosylated_at → position
- **Results**: Sites with specific positions:
  - P13224 (Platelet GP Ib beta): positions 65, 66, 83
  - HLA class I B: position 110
  - Membrane cofactor protein: position 83

### Query 5: Human glycogenes with descriptions
- **Search**: Filter by taxon/9606 with description
- **Results**: 20 genes including:
  - ARID1A - AT-rich interaction domain 1A
  - CTNNB1 - catenin beta 1
  - INSR - insulin receptor
  - EXTL3 - exostosin like glycosyltransferase 3

## SPARQL Queries Tested

```sparql
# Query 1: Search glycan epitopes by label
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
LIMIT 20
# Results: 20 Lewis antigen variants found
```

```sparql
# Query 2: Human glycoproteins with labels
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>

SELECT ?protein ?label
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           rdfs:label ?label ;
           glycan:has_taxon <http://identifiers.org/taxonomy/9606> .
}
LIMIT 20
# Results: Human glycoproteins including Platelet GP Ib beta, MHC class I antigens
```

```sparql
# Query 3: Glycosylation sites with positions
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glycoconjugate: <http://purl.jp/bio/12/glyco/conjugate#>
PREFIX faldo: <http://biohackathon.org/resource/faldo#>

SELECT ?protein ?label ?site ?position
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
           rdfs:label ?label ;
           glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
           glycoconjugate:glycosylated_at ?site .
  ?site faldo:location/faldo:position ?position .
}
LIMIT 20
# Results: Sites with specific positions (e.g., P13224 at 65, 66, 83)
```

```sparql
# Query 4: Human glycogenes with functional descriptions
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?gene ?symbol ?description
FROM <http://rdf.glycosmos.org/glycogenes>
WHERE {
  ?gene a glycan:Glycogene ;
    rdfs:label ?symbol ;
    dcterms:description ?description ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> .
}
LIMIT 20
# Results: Human glycogenes like INSR (insulin receptor), EXTL3, CTNNB1
```

## Interesting Findings

### Specific Entities for Good Questions
1. **Lewis a epitope**: EP0007 - classic blood group antigen
2. **Sialyl Lewis x**: EP0012 - important in inflammation and cancer metastasis
3. **Platelet GP Ib beta**: P13224 - glycosylated at positions 65, 66, 83
4. **EXTL3 glycogene**: Exostosin-like glycosyltransferase 3
5. **GM1 ganglioside**: EP0050 - neural ganglioside epitope

### Unique Properties/Patterns
- GlyTouCan IDs: G[0-9]{5}[A-Z]{2} pattern
- Multi-graph architecture requires explicit FROM clause
- Glycosylation sites link proteins to glycans with specific positions
- Lewis antigen family extensively catalogued (20+ variants)

### Connections to Other Databases
- **ChEBI**: 11K glycan cross-references
- **PubChem**: 32K compound and substance links
- **KEGG**: 10K glycan-pathway links
- **PDB**: 6K structure links
- **UniProt**: 139K glycoprotein links
- **NCBI Gene**: 423K glycogene links

### Verifiable Facts
- Total glycans: 117,571
- Total glycoproteins: 153,178
- Total glycosylation sites: 414,798
- Total glycogenes: 423,164
- Total glycoepitopes: 173
- Lewis epitopes: ~20 variants (Lewis a, b, x, y and derivatives)

## Question Opportunities by Category

### Precision
- "What is the GlyCoEpitope ID for Lewis a antigen?" → EP0007
- "What is the Sialyl Lewis x epitope ID in GlyCosmos?" → EP0012
- "At what positions is Platelet glycoprotein Ib beta chain (P13224) glycosylated?" → 65, 66, 83

### Completeness
- "How many glycan structures are in GlyTouCan/GlyCosmos?" → 117,571
- "How many glycan epitopes are catalogued in GlyCosmos?" → 173
- "List all Lewis antigen variants in GlyCosmos"

### Integration
- "What human glycogenes are associated with glycosyltransferase activity?"
- "Link glycoproteins to their glycosylation site positions"
- "Find glycans cross-referenced to ChEBI"

### Currency
- "What are the recently added glycan structures?"

### Specificity
- "What is the functional description of glycogene EXTL3?" → exostosin like glycosyltransferase 3
- "Which ganglioside epitopes are catalogued in GlyCosmos?"
- "What glycosylation positions are known for membrane cofactor protein (P15529)?" → 83

### Structured Query
- "Find all human glycoproteins with glycosylation sites"
- "List glycogenes involved in receptor functions"
- "Find epitopes from the Lewis blood group family"

## Notes

### Limitations
- Multi-graph architecture requires explicit FROM clause for performance
- Glycan labels rarely populated (<1%)
- Protein/gene labels partial (17%/32%)
- Some cross-reference coverage incomplete

### Best Practices
- Always specify FROM clause with specific graph(s)
- Use `bif:contains` for label searches (rdfs:label, skos:altLabel)
- Use FILTER(CONTAINS()) for dcterms:description (not indexed)
- Filter by taxonomy early for large datasets
- Use LIMIT for glycosylation sites (414K+)
- Use GlyTouCan IDs rather than glycan labels

### Data Quality
- ~99.8% glycans have GlyTouCan primary IDs
- ~86% glycans have Resource_entry cross-references
- ~17% glycoproteins have labels
- >90% glycosylation sites have positions
- ~8% glycogenes have descriptions
