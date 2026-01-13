# TogoMCP Database Exploration Summary

## Exploration Status: COMPLETE ✅

All 23 databases have been explored and documented.

## Database List with Exploration Files

| # | Database | File | Status | Key Statistics |
|---|----------|------|--------|----------------|
| 1 | amrportal | amrportal_exploration.md | ✅ | 1.7M phenotypes, 1.1M genotypes |
| 2 | bacdive | bacdive_exploration.md | ✅ | 97K bacterial strains, phenotypes |
| 3 | chebi | chebi_exploration.md | ✅ | 161K entities, ontology hierarchy |
| 4 | chembl | chembl_exploration.md | ✅ | 2.4M compounds, 15K targets, bioactivity |
| 5 | clinvar | clinvar_exploration.md | ✅ | 2.7M variants, clinical significance |
| 6 | ddbj | ddbj_exploration.md | ✅ | Nucleotide sequences, gene annotations |
| 7 | ensembl | ensembl_exploration.md | ✅ | Multi-species genes, transcripts |
| 8 | glycosmos | glycosmos_exploration.md | ✅ | 117K glycans, 153K glycoproteins |
| 9 | go | go_exploration.md | ✅ | 44K terms, 3 aspects (BP/MF/CC) |
| 10 | medgen | medgen_exploration.md | ✅ | 1.1M concepts, disease-gene links |
| 11 | mediadive | mediadive_exploration.md | ✅ | 3,289 culture media recipes |
| 12 | mesh | mesh_exploration.md | ✅ | 30K descriptors, tree hierarchy |
| 13 | mondo | mondo_exploration.md | ✅ | 24K diseases, cross-refs to OMIM/Orphanet |
| 14 | nando | nando_exploration.md | ✅ | 2,777 rare diseases (Japan), trilingual |
| 15 | ncbigene | ncbigene_exploration.md | ✅ | Human genes, symbols, aliases |
| 16 | pdb | pdb_exploration.md | ✅ | 228K structures, ligands, methods |
| 17 | pubchem | pubchem_exploration.md | ✅ | 118M compounds, bioactivities, cross-refs |
| 18 | pubmed | pubmed_exploration.md | ✅ | 35M+ articles, citations, MeSH |
| 19 | pubtator | pubtator_exploration.md | ✅ | >10M text mining annotations |
| 20 | reactome | reactome_exploration.md | ✅ | 15K pathways, 12K reactions, 11K proteins |
| 21 | rhea | rhea_exploration.md | ✅ | 19K reactions, enzyme-substrate links |
| 22 | taxonomy | taxonomy_exploration.md | ✅ | 2.6M taxa, lineage hierarchy |
| 23 | uniprot | uniprot_exploration.md | ✅ | 571K proteins (Swiss-Prot), enzymes, pathways |

## Key Findings Summary

### Universal Query Patterns

1. **bif:contains syntax**:
   ```sparql
   ?label bif:contains "'keyword'" option (score ?sc)
   ?label bif:contains "'keyword1' AND 'keyword2'" option (score ?sc)
   ```

2. **Always use FROM clause** for graph specification

3. **LIMIT required** for exploratory queries on large datasets

4. **OPTIONAL** for incomplete coverage properties

### Cross-Database Integration Opportunities

| Source DB | Target DB | Link Type |
|-----------|-----------|-----------|
| UniProt | GO | Function annotation |
| UniProt | Reactome | Pathway participation |
| UniProt | PDB | 3D structure |
| ChEMBL | ChEBI | Compound identity |
| ChEMBL | UniProt | Target protein |
| ClinVar | MONDO | Disease classification |
| ClinVar | NCBIGene | Gene association |
| BacDive | MediaDive | Strain-medium compatibility |
| BacDive | Taxonomy | Organism classification |
| NANDO | MONDO | Disease mapping |
| PubTator | MeSH | Disease annotation |
| PubTator | NCBIGene | Gene annotation |
| AMRPortal | Taxonomy | Organism |
| AMRPortal | BioSample | Sample metadata |

### Database-Specific Critical Notes

| Database | Critical Pattern | Anti-Pattern |
|----------|------------------|--------------|
| DDBJ | Filter by entry ID before joins | Queries without entry filter timeout |
| GlyCosmos | Always specify FROM (100+ graphs) | Omitting FROM causes timeout |
| BacDive | Use OPTIONAL for phenotypes | Requiring all phenotypes excludes 60% |
| PubTator | Filter by entity type ("Disease"/"Gene") | Mixed types confuse results |
| AMRPortal | Filter by organism first | Broad aggregations timeout |
| NANDO | Use language filter for labels | Returns all 3 languages |

### Question Generation Opportunities

**High-Value Precision Questions** (specific answers):
- UniProt accession numbers, PDB IDs, gene symbols
- Pathway names, reaction equations, enzyme EC numbers
- Disease identifiers (MONDO, NANDO), variant IDs (ClinVar)

**High-Value Completeness Questions** (counts, lists):
- Number of entities in each database
- Lists of specific categories (e.g., human kinases, beta-lactam genes)
- Coverage statistics

**High-Value Integration Questions** (cross-database):
- Protein → pathway → disease connections
- Gene → variant → clinical significance chains
- Organism → strain → culture medium links

**High-Value Specificity Questions** (detailed properties):
- Molecular weights, resolution values, coordinates
- Phenotype values, geographic distributions
- Temporal trends, frequency counts

## Files Created

Total: 24 files (1 summary + 23 exploration reports)

```
/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/
├── 00_PROGRESS.md (this file)
├── amrportal_exploration.md
├── bacdive_exploration.md
├── chebi_exploration.md
├── chembl_exploration.md
├── clinvar_exploration.md
├── ddbj_exploration.md
├── ensembl_exploration.md
├── glycosmos_exploration.md
├── go_exploration.md
├── medgen_exploration.md
├── mediadive_exploration.md
├── mesh_exploration.md
├── mondo_exploration.md
├── nando_exploration.md
├── ncbigene_exploration.md
├── pdb_exploration.md
├── pubchem_exploration.md
├── pubmed_exploration.md
├── pubtator_exploration.md
├── reactome_exploration.md
├── rhea_exploration.md
├── taxonomy_exploration.md
└── uniprot_exploration.md
```

## Next Steps

1. **Question Generation Phase**: Use exploration reports to generate evaluation questions
2. **Question Categories**:
   - Precision (specific identifier lookups)
   - Completeness (counts, comprehensive lists)
   - Integration (cross-database queries)
   - Currency (recent updates, trends)
   - Specificity (detailed property queries)
   - Structured Query (complex SPARQL patterns)

3. **Validation**: Each question should be tested with actual SPARQL queries

## Summary Statistics

- **Total databases explored**: 23
- **Total exploration reports**: 23
- **Estimated unique entities**: >100 million
- **Cross-reference types**: 50+
- **Geographic coverage**: Global (AMRPortal: 150+ countries)
- **Temporal coverage**: Historical to present
