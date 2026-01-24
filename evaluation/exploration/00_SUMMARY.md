# Database Exploration Summary

## Overview
- **Total databases explored**: 23
- **Total sessions**: Multiple (final completion 2025-01-24)
- **All exploration reports**: Available in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`

## All Explored Databases

| Database | Description | Key Strengths |
|----------|-------------|---------------|
| amrportal | Antimicrobial resistance surveillance | Resistance phenotypes, MIC values, geographic data |
| bacdive | Bacterial strain metadata | Taxonomy, physiology, culture conditions |
| chebi | Chemical entities ontology | Small molecules, roles, cross-references |
| chembl | Bioactive molecules & drug data | Compound-target activities, IC50 values |
| clinvar | Genetic variants & clinical significance | Pathogenic/benign classifications, review status |
| ddbj | Nucleotide sequences (INSDC) | Prokaryotic genomes, gene annotations |
| ensembl | Genomics across 100+ species | Genes, transcripts, cross-species |
| glycosmos | Glycoscience portal | Glycans, glycoproteins, epitopes |
| go | Gene Ontology | Biological processes, functions, components |
| medgen | Medical genetics concepts | Disease-gene relationships, clinical concepts |
| mediadive | Culture media recipes | Microbial growth media, ingredients |
| mesh | Medical Subject Headings | Biomedical vocabulary, hierarchical terms |
| mondo | Disease ontology | Cross-database disease integration |
| nando | Japanese rare diseases | Intractable disease registry |
| ncbigene | Gene database | 57M+ gene entries, cross-species |
| pdb | Protein structures | 3D structures, experimental methods |
| pubchem | Chemical database | 119M compounds, bioactivities |
| pubmed | Biomedical literature | Article metadata, MeSH annotations |
| pubtator | Literature annotations | Gene-disease mentions in literature |
| reactome | Pathway database | Biological pathways, reactions |
| rhea | Biochemical reactions | 17K+ reactions, enzyme links |
| taxonomy | NCBI Taxonomy | 3M+ organisms, hierarchical classification |
| uniprot | Protein sequences & function | 444M proteins, Swiss-Prot curation |

## Database Coverage Plan for 120 Questions

### Recommended Distribution

Based on database richness, unique content, and integration opportunities:

**High Priority (8-10 questions each) - 50 questions**
- uniprot: 10 (rich protein data, excellent cross-references)
- chembl: 8 (drug activities, compound-target relationships)
- pubchem: 8 (chemical properties, bioassays)
- clinvar: 8 (clinical variants, pathogenicity)
- go: 8 (ontology navigation, gene annotations)
- pdb: 8 (structural data, experimental methods)

**Medium Priority (5-6 questions each) - 40 questions**
- ncbigene: 6 (gene information, cross-species)
- ensembl: 6 (genomics, multi-species)
- mesh: 6 (medical vocabulary, hierarchy)
- reactome: 6 (pathways, biological processes)
- rhea: 5 (biochemical reactions)
- pubmed: 5 (literature metadata)
- pubtator: 6 (literature-based discovery)

**Specialized Priority (3-4 questions each) - 30 questions**
- mondo: 4 (disease integration)
- chebi: 4 (chemical ontology)
- nando: 4 (rare diseases)
- bacdive: 4 (bacterial strains)
- mediadive: 3 (culture media)
- taxonomy: 3 (organism classification)
- amrportal: 4 (AMR surveillance)
- medgen: 4 (medical genetics)
- glycosmos: 3 (glycoscience)
- ddbj: 3 (sequences)

## Database Characteristics

### Rich Content (good for multiple question types)
- **UniProt**: Proteins, functions, sequences, variants, cross-references
- **ChEMBL**: Molecules, targets, bioactivities, mechanisms
- **PubChem**: Compounds, properties, bioassays, pathways
- **ClinVar**: Variants, clinical significance, submissions
- **PDB**: Structures, methods, resolution, ligands

### Specialized Content (good for specificity questions)
- **NANDO**: Japanese intractable diseases (2,777 disease classes)
- **BacDive**: Bacterial strain metadata (97K+ strains)
- **MediaDive**: Culture media recipes (3,289 media)
- **GlyCosmos**: Glycan structures, epitopes (173 epitopes)
- **AMR Portal**: Resistance phenotypes, geographic surveillance

### Well-Connected (good for integration questions)
- **UniProt ↔ NCBI Gene ↔ Ensembl**: Protein-gene-genome links
- **PubChem ↔ ChEBI ↔ ChEMBL**: Chemical compound connections
- **ClinVar ↔ MedGen ↔ MONDO**: Disease-variant relationships
- **PubTator ↔ PubMed ↔ NCBI Gene**: Literature-gene discovery
- **Reactome ↔ UniProt ↔ ChEBI**: Pathway-protein-metabolite

### Ontology Navigation (good for completeness questions)
- **GO**: Hierarchical terms (48K+ terms, descendants/ancestors)
- **MeSH**: Medical vocabulary hierarchy (30K descriptors)
- **MONDO**: Disease ontology (30K+ disease classes)
- **ChEBI**: Chemical ontology (223K entities)

## Cross-Database Integration Opportunities

### Multi-Database Question Types

1. **Protein-Gene-Pathway Integration**
   - UniProt → NCBI Gene → Reactome
   - "What pathways involve proteins encoded by human BRCA1?"

2. **Chemical-Target-Activity Integration**
   - PubChem → ChEMBL → UniProt
   - "Find kinase inhibitors with IC50 < 100 nM and their target proteins"

3. **Variant-Disease-Literature Integration**
   - ClinVar → MedGen → PubMed/PubTator
   - "Find pathogenic variants for rare diseases with literature support"

4. **Organism-Strain-Media Integration**
   - Taxonomy → BacDive → MediaDive
   - "What culture conditions are recommended for thermophilic bacteria?"

5. **Structure-Sequence-Function Integration**
   - PDB → UniProt → GO
   - "Find kinase structures with known catalytic mechanisms"

## Endpoint Distribution

### Shared Endpoints (enable cross-database queries)

**EBI Endpoint** (ebi):
- ChEMBL, ChEBI, Reactome, Ensembl
- Same Virtuoso instance, efficient JOINs

**NCBI Endpoint** (ncbi):
- ClinVar, PubMed, PubTator, NCBI Gene, MedGen
- Integrated literature and genetics data

**Primary Endpoint** (primary):
- BacDive, MediaDive, Taxonomy, MeSH, GO, MONDO, NANDO
- Microbiology and ontology databases

**SIB Endpoint** (sib):
- UniProt, Rhea
- Protein and reaction data

**Individual Endpoints**:
- PDB (pdb), PubChem (pubchem), GlyCosmos (glycosmos), DDBJ (ddbj), AMR Portal (amrportal)

## Recommendations

### Question Generation Strategy

1. **Start with high-value databases**: UniProt, ChEMBL, ClinVar, GO, PDB
2. **Balance categories**: Ensure 20 questions per category
3. **Include integration questions**: At least 20 cross-database questions
4. **Test query patterns first**: Verify SPARQL works before finalizing
5. **Avoid MIE example entities**: Use entities discovered through searches

### Databases That Pair Well

- UniProt + NCBI Gene (ID conversion, gene-protein links)
- ChEMBL + PubChem (compound overlap, bioactivity)
- ClinVar + MedGen (variant-disease relationships)
- PubTator + PubMed (literature annotations)
- BacDive + MediaDive (strain cultivation)
- GO + UniProt (functional annotations)

### Particularly Interesting Findings

1. **PubTator**: 234 million gene-disease annotations enable literature-based discovery
2. **ChEMBL**: Rich IC50/Ki data for drug development questions
3. **ClinVar**: 3.5M+ variants with clinical interpretations
4. **NANDO**: Unique Japanese rare disease coverage
5. **PDB**: 204K+ structures with resolution data
6. **UniProt**: 923K reviewed entries with rich annotations

## Files Reference

All exploration reports: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/[dbname]_exploration.md`

---

**Last Updated**: 2025-01-24
**Status**: All 23 databases explored - Ready for Phase 2 Question Generation
