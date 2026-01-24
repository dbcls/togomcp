# GlyCosmos Exploration Report

## Database Overview
- **Purpose**: Comprehensive glycoscience portal integrating glycan structures, glycoproteins, glycosylation sites, glycogenes, glycoepitopes, and lectin-glycan interactions
- **Endpoint**: https://ts.glycosmos.org/sparql
- **Key Features**: Multi-graph architecture (100+ named graphs), cross-references to major databases
- **Data Version**: Release 2024.12

## Schema Analysis (from MIE file)
### Main Entities
- **Saccharide (Glycan)**: Core glycan structures with GlyTouCan IDs
- **Glycoprotein**: Proteins with glycosylation information
- **Glycosylation_Site**: Specific positions where glycans attach to proteins
- **Glycogene**: Genes involved in glycosylation processes
- **Glycan_epitope**: Immunological epitopes with antibody associations
- **Lectin**: Carbohydrate-binding proteins

### Important Properties
- `glytoucan:has_primary_id`: Glycan accession (G[0-9]{5}[A-Z]{2} pattern)
- `glycan:has_Resource_entry`: Links to external databases
- `glycoconjugate:glycosylated_at`: Links proteins to glycosylation sites
- `faldo:location/faldo:position`: Sequence position of glycosylation
- `glycan:has_taxon`: Organism reference via NCBI Taxonomy

### Query Patterns
- **CRITICAL**: Must use FROM clause to specify graph(s) - omitting causes timeout
- Use `bif:contains` for full-text label search (Virtuoso-specific)
- Filter by taxonomy early for performance

## Search Queries Performed

### 1. Glycan epitopes (all 173)
```
Query: List all glycan epitopes
Results: 173 total epitopes including Lewis a (EP0007), Lewis x (EP0011), 
Sialyl Lewis a (EP0008), Sialyl Lewis x (EP0012), GM1 (EP0050), GD1a (EP0056), 
HNK-1 (EP0001), Forssman Antigen (EP0037), SSEA-1 (EP0042), SSEA-3 (EP0039)
```

### 2. Human glycoproteins with labels
```
Query: Human glycoproteins with names
Results: Found proteins like Platelet glycoprotein Ib beta chain (P13224), 
Membrane cofactor protein (P15529), HLA class I antigens, MHC class I antigens
```

### 3. Glycoproteins by species
```
Query: Count glycoproteins per taxon
Results:
- Human (9606): 16,604 proteins
- Mouse (10090): 10,713 proteins
- Rat (10116): 2,576 proteins
- Arabidopsis (3702): 2,251 proteins
- C. elegans (6239): 1,447 proteins
```

### 4. Human glycosylation sites with positions
```
Query: Proteins with glycosylation site positions
Results: P13224 (Platelet glycoprotein Ib beta) has sites at positions 65, 66, 83
P15529 (Membrane cofactor protein) has multiple sites at position 83
HLA class I antigens have sites at position 110
```

### 5. Human glycogenes with descriptions
```
Query: Human glycogenes with functional descriptions
Results: Found 10,109 human glycogenes including transferases like:
- FUT1, FUT2, FUT3: Fucosyltransferases (blood group related)
- EXTL3: Exostosin like glycosyltransferase 3
- GALNT17, GALNT12: N-acetylgalactosaminyltransferases
- ABO: Blood group transferase
- B3GALNT1: Globoside blood group transferase
```

### 6. Lectins with UniProt links
```
Query: Lectins from SugarBind
Results: Found lectins like FimH (P08191), Hemagglutinin (P03462), 
Gp120 (P18799), various H1/H2 hemagglutinins, bacterial adhesins (FedF, GafD, PapG)
```

## SPARQL Queries Tested

### Query 1: Count all glycan epitopes
```sparql
SELECT (COUNT(DISTINCT ?epitope) as ?count)
FROM <http://rdf.glycoinfo.org/glycoepitope>
WHERE {
  ?epitope a glycan:Glycan_epitope .
}
# Results: 173 epitopes
```

### Query 2: Human glycobiology statistics
```sparql
SELECT (COUNT(DISTINCT ?protein) as ?humanProteins) (COUNT(DISTINCT ?site) as ?humanSites)
FROM <http://rdf.glycosmos.org/glycoprotein>
WHERE {
  ?protein a glycan:Glycoprotein ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    glycoconjugate:glycosylated_at ?site .
}
# Results: 16,604 human proteins, 130,869 glycosylation sites
```

### Query 3: Human glycogenes count
```sparql
SELECT (COUNT(DISTINCT ?gene) as ?humanGlycogenes)
FROM <http://rdf.glycosmos.org/glycogenes>
WHERE {
  ?gene a glycan:Glycogene ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> .
}
# Results: 10,109 human glycogenes
```

### Query 4: Glycogenes with transferase function
```sparql
SELECT ?gene ?symbol ?description
FROM <http://rdf.glycosmos.org/glycogenes>
WHERE {
  ?gene a glycan:Glycogene ;
    rdfs:label ?symbol ;
    glycan:has_taxon <http://identifiers.org/taxonomy/9606> ;
    dcterms:description ?description .
  FILTER(CONTAINS(LCASE(?description), "transferase"))
}
# Results: Blood group related transferases (FUT1-3, ABO, B3GALNT1, A4GALT, etc.)
```

## Cross-Reference Analysis

### Entity Counts (unique entities with mappings)
Based on MIE file documentation:
- Glycans → External databases: ~86% (101,600/117,864 glycans)
- Glycoproteins → UniProt: 139K proteins
- Glycogenes → NCBI Gene: 423K genes

### Key Cross-References
| Source | Target | Coverage |
|--------|--------|----------|
| Glycans | PubChem Compound | 32K |
| Glycans | PubChem Substance | 32K |
| Glycans | ChEBI | 11K |
| Glycans | KEGG | 10K |
| Glycans | PDB | 6K |
| Glycoproteins | UniProt | 139K |
| Glycoproteins | GlyGen | 12K |
| Glycogenes | NCBI Gene | 423K |
| Glycogenes | KEGG Genes | 381K |

## Interesting Findings

**Focus on discoveries requiring actual database queries:**

1. **Human glycobiology scale**: 16,604 human glycoproteins with 130,869 total glycosylation sites (average ~7.9 sites per protein)

2. **Species distribution**: Mouse is second most covered organism (10,713 glycoproteins) after human

3. **Glycoepitope diversity**: 173 epitopes including clinically relevant ones:
   - Lewis antigens (Lewis a, b, x, Sialyl Lewis a/x)
   - Gangliosides (GM1, GM2, GM3, GD1a)
   - Blood group antigens (Forssman, P1, Pk)
   - Embryonic antigens (SSEA-1, SSEA-3)

4. **Glycogene functional annotation**: ~10,109 human glycogenes with descriptions, many are glycosyltransferases critical for:
   - ABO blood group synthesis (ABO, FUT1, FUT2)
   - Lewis blood group (FUT3)
   - Protein glycosylation (GALNTs, MGATs)

5. **Lectin-glycan interactions**: 739 lectins with UniProt cross-references, including pathogen adhesins (FimH, PapG) and viral proteins (Hemagglutinin, HIV Gp120)

## Question Opportunities by Category

### Precision
- "What is the GlyCosmos epitope ID for Lewis x antigen?" → EP0011
- "What is the GlyCosmos glycogene ID for human FUT3 (fucosyltransferase 3)?" → glycosmos:glycogene/2525
- "At what position is the glycosylation site on human Platelet glycoprotein Ib beta chain (P13224)?" → Positions 65, 66, 83

### Completeness
- "How many glycan epitopes are in GlyCosmos?" → 173
- "How many human glycoproteins have glycosylation sites in GlyCosmos?" → 16,604
- "How many human glycosylation sites are documented in GlyCosmos?" → 130,869
- "How many human glycogenes are in GlyCosmos?" → 10,109
- "How many total glycan structures are in GlyTouCan (via GlyCosmos)?" → 117,571

### Integration
- "What lectins in GlyCosmos link to UniProt P08191?" → FimH bacterial adhesin
- "Which glycogenes in GlyCosmos are linked to blood group transferases?" → ABO, FUT1, FUT2, FUT3, B3GALNT1, A4GALT

### Currency
- "What is the latest version of GlyCosmos data?" → Release 2024.12

### Specificity
- "What is the GlyCosmos epitope ID for the HNK-1 carbohydrate epitope?" → EP0001
- "What is the epitope ID for the Forssman antigen in GlyCosmos?" → EP0037
- "What antibodies recognize the GD1a ganglioside epitope?" → AN0125, AN0154, AN0155, AN0156, etc.

### Structured Query
- "Find all human glycogenes that are transferases" → Requires filtering by description
- "Which glycoproteins in human have glycosylation sites at position 83?" → Multiple results including MHC/HLA proteins
- "Find glycan epitopes that have associated antibodies" → Most epitopes have antibody associations

## Notes
- **Performance**: Always use FROM clause with specific graph(s) - the 100+ graph architecture makes this critical
- **Full-text search**: Use `bif:contains` for labels (Virtuoso-specific), FILTER for other properties
- **Label coverage**: Glycan labels <1% (use GlyTouCan IDs), proteins ~17%, genes ~32%
- **Taxon filtering**: Apply early for human-specific queries to avoid timeout
- **GlyTouCan IDs**: Format G[0-9]{5}[A-Z]{2} (e.g., G00051MO)
- **Unique niche**: Specialized glycoscience data not found in other databases
