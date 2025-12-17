# Database Exploration Summary

## Overview
- **Total databases explored**: 22
- **Total exploration sessions**: 3 (Sessions 1-2 documented, Session 3 completed all remaining)
- **Total documentation**: 279 KB of detailed exploration reports

## All Explored Databases

### Molecular Biology Core (6 databases)
1. **UniProt** - Protein sequences and functions (444M proteins, 923K curated)
2. **PDB** - 3D protein structures (204K+ entries, 0.48Å best resolution)
3. **NCBI Gene** - Gene information (57M+ genes across all organisms)
4. **Ensembl** - Genome annotations (100+ species, transcript variants)
5. **DDBJ** - DNA sequences (INSDC collaboration, genomic annotations)
6. **Taxonomy** - Biological classification (3M+ taxa, hierarchical system)

### Chemical & Drug Resources (4 databases)
7. **ChEBI** - Chemical entities ontology (217K+ entities, hierarchical)
8. **ChEMBL** - Bioactive molecules (2.4M compounds, 20M bioactivity measurements)
9. **PubChem** - Chemical compounds (119M compounds, 1.7M bioassays)
10. **Rhea** - Biochemical reactions (17K reactions, ChEBI-linked, EC classified)

### Pathways & Systems (2 databases)
11. **Reactome** - Biological pathways (22K pathways, BioPAX Level 3)
12. **GO** - Gene Ontology (48K terms in 3 namespaces, hierarchical DAG)

### Clinical & Genetics (4 databases)
13. **ClinVar** - Genetic variants (3.5M+ variants with clinical significance)
14. **MedGen** - Medical genetics (233K clinical concepts, HPO/OMIM integrated)
15. **MONDO** - Disease ontology (30K diseases, 90% cross-ref coverage)
16. **NANDO** - Japanese rare diseases (2,777 intractable diseases)

### Terminology & Literature (3 databases)
17. **MeSH** - Medical subject headings (2.5M entities, 30K descriptors)
18. **PubMed** - Biomedical literature (bibliographic metadata, MeSH annotations)
19. **PubTator** - Literature mining (entity annotations from PubMed)

### Specialized Resources (3 databases)
20. **BacDive** - Bacterial diversity (97K+ strains, phenotypic data)
21. **MediaDive** - Culture media (3,289 recipes, 1,489 ingredients)
22. **GlyCosmos** - Glycoscience (glycans, glycoproteins, 100+ named graphs)

## Database Coverage Plan for 120 Questions

### Recommended Distribution (by database richness and uniqueness)

**Tier 1: High Priority - Rich, Well-Connected (55 questions total)**
- **UniProt**: 10 questions
  - Rationale: Central protein resource, excellent search tools, 923K curated entries
  - Categories: Precision (protein IDs), Integration (cross-refs), Specificity (domains)
  
- **PubChem**: 10 questions
  - Rationale: 119M compounds, comprehensive descriptors, FDA drug data
  - Categories: Precision (molecular properties), Completeness (counts), Integration (ChEBI links)
  
- **GO**: 8 questions
  - Rationale: 48K terms, hierarchical navigation, fundamental for biology
  - Categories: Completeness (descendants), Structured Query (ancestors), Precision (terms)
  
- **Reactome**: 7 questions
  - Rationale: 22K pathways, BioPAX ontology, species-specific
  - Categories: Completeness (pathway members), Integration (protein/compound links)
  
- **ChEMBL**: 7 questions
  - Rationale: 20M bioactivity measurements, drug development focus
  - Categories: Structured Query (IC50 filters), Integration (target-compound)
  
- **ClinVar**: 7 questions
  - Rationale: 3.5M variants, clinical significance, disease associations
  - Categories: Precision (variant IDs), Specificity (rare variants), Integration (MedGen)
  
- **NCBI Gene**: 6 questions
  - Rationale: 57M genes, orthology relationships, comprehensive
  - Categories: Precision (gene IDs), Integration (Ensembl/HGNC), Completeness (orthologs)

**Tier 2: Medium Priority - Specialized Value (45 questions total)**
- **PDB**: 6 questions (structural biology, resolution data, experimental methods)
- **Rhea**: 6 questions (biochemical reactions, transport, EC numbers)
- **MeSH**: 6 questions (medical terminology, hierarchical trees)
- **MONDO**: 5 questions (disease ontology, cross-references)
- **ChEBI**: 5 questions (chemical ontology, hierarchical relationships)
- **Taxonomy**: 5 questions (biological classification, rank navigation)
- **Ensembl**: 5 questions (genome annotations, transcript variants)
- **MedGen**: 4 questions (clinical concepts, HPO integration)
- **PubMed**: 3 questions (literature search, MeSH annotations)

**Tier 3: Lower Priority - Niche Applications (20 questions total)**
- **NANDO**: 4 questions (Japanese rare diseases, unique dataset)
- **BacDive**: 4 questions (bacterial strains, phenotypic data)
- **MediaDive**: 3 questions (culture media recipes, growth conditions)
- **GlyCosmos**: 3 questions (glycobiology, specialized field)
- **PubTator**: 3 questions (text mining, entity extraction)
- **DDBJ**: 3 questions (DNA sequences, INSDC data)

### Rationale for Distribution
1. **Priority based on**:
   - Data richness and comprehensiveness
   - Search tool quality and reliability
   - Cross-database integration potential
   - Biological research relevance
   - Unique specialized information

2. **Balance across question categories**:
   - Precision: ~25 questions (exact IDs, properties)
   - Completeness: ~20 questions (counts, exhaustive lists)
   - Integration: ~25 questions (cross-database links)
   - Structured Query: ~20 questions (complex filtering)
   - Specificity: ~15 questions (rare entities, niche data)
   - Currency: ~15 questions (recent updates, current status)

3. **Organism diversity**:
   - Human: ~60 questions (clinical relevance)
   - Model organisms: ~30 questions (research applications)
   - Microbes: ~20 questions (bacterial diversity)
   - Multi-species: ~10 questions (comparative genomics)

## Cross-Database Integration Opportunities

### High-Value Integration Pairs
1. **UniProt ↔ PDB**: Protein sequence to structure (via search tools + conversion)
2. **ChEMBL ↔ PubChem**: Compound ID conversion, activity data enrichment
3. **ClinVar ↔ MedGen**: Variant to disease phenotype mapping
4. **NCBI Gene ↔ Ensembl**: Gene ID conversion, orthology relationships
5. **Reactome ↔ Rhea**: Pathway reactions to detailed biochemistry
6. **GO ↔ UniProt**: Functional annotation to protein entries
7. **MeSH ↔ PubMed**: Term-based literature retrieval
8. **ChEBI ↔ Rhea**: Compound to reaction participation
9. **MONDO ↔ NANDO**: International to Japanese disease mapping
10. **Taxonomy ↔ NCBI Gene**: Organism-specific gene queries

### Multi-Database Integration Questions (Examples)
1. "Find the 3D structure (PDB) for the protein encoded by human gene BRCA1 (NCBI Gene), then list its associated pathways (Reactome)"
   - Chain: NCBI Gene → UniProt → PDB + Reactome
   
2. "What clinical variants (ClinVar) are associated with the disease identified as MONDO:0010526, and what are their phenotypes (MedGen)?"
   - Chain: MONDO → ClinVar → MedGen
   
3. "For the compound resveratrol in PubChem, find its ChEBI classification, then identify biochemical reactions (Rhea) it participates in"
   - Chain: PubChem → ChEBI → Rhea
   
4. "Find bacterial strains (BacDive) that can be cultured using medium DSMZ 1, then identify their taxonomic classification (Taxonomy)"
   - Chain: MediaDive → BacDive → Taxonomy

### TogoID Conversion Opportunities
- UniProt ↔ NCBI Gene (gene-protein mapping)
- PubChem ↔ ChEBI (chemical identifier conversion)
- Ensembl ↔ NCBI Gene (gene database reconciliation)
- ChEMBL ↔ PubChem (compound cross-referencing)
- Multiple disease ontologies (MONDO ↔ MeSH ↔ OMIM)

## Database Characteristics

### Rich Content (Good for multiple questions)
**Characteristics**: Large datasets, comprehensive coverage, multiple query types
- **UniProt**: 444M proteins with rich annotations, excellent search tools
- **PubChem**: 119M compounds with detailed molecular descriptors
- **ChEMBL**: 20M bioactivity measurements, drug-focused
- **ClinVar**: 3.5M variants with clinical interpretations
- **NCBI Gene**: 57M genes with orthology and cross-references
- **GO**: 48K terms with hierarchical relationships
- **Reactome**: 22K pathways with molecular detail

**Question Opportunities**: Precision lookups, completeness counts, structured queries

### Specialized Content (Good for specificity questions)
**Characteristics**: Niche domains, unique data types, expert curation
- **NANDO**: 2,777 Japanese intractable diseases (unique dataset)
- **BacDive**: 97K bacterial strains with phenotypic characterization
- **MediaDive**: 3,289 culture media recipes (specialized protocols)
- **GlyCosmos**: Glycoscience-specific (carbohydrates, glycoproteins)
- **Rhea**: 17K expert-curated biochemical reactions
- **PubTator**: Literature-mined entity annotations

**Question Opportunities**: Specificity, niche applications, rare entities

### Well-Connected (Good for integration questions)
**Characteristics**: Extensive cross-references, ID conversion support, TogoID integrated
- **UniProt**: 200+ database cross-references, central hub
- **ChEMBL**: Links to UniProt, PDB, PubChem, DrugBank
- **ClinVar**: MedGen, OMIM, MeSH, HGNC connections
- **MedGen**: OMIM, Orphanet, HPO, MONDO integration
- **MONDO**: 39+ database cross-references, 90% coverage
- **PubChem**: ChEBI, Wikidata, UniProt, PDB links
- **Reactome**: UniProt, ChEBI, Ensembl, GO annotations

**Question Opportunities**: Integration, ID conversion, cross-database navigation

### High-Quality Curation
**Characteristics**: Manual curation, expert review, standardized annotations
- **UniProt (Swiss-Prot)**: 923K manually curated entries
- **Reactome**: Expert-curated pathways
- **Rhea**: 100% atom-balanced, ChEBI-linked reactions
- **GO**: Standardized ontology with evidence codes
- **ChEBI**: Ontology-structured chemical entities
- **MeSH**: NLM-controlled medical vocabulary

**Question Opportunities**: Precision, verifiability, authoritative answers

### Dynamic/Current (Good for currency questions)
**Characteristics**: Frequent updates, recent additions, time-sensitive data
- **ClinVar**: Continuous variant submissions, classification updates
- **PubMed**: Daily literature updates
- **NCBI Gene**: Regular gene annotation updates
- **Reactome**: Pathway updates for new discoveries
- **ChEMBL**: Regular bioactivity data releases
- **UniProt**: Monthly releases

**Question Opportunities**: Currency, recent additions, current classifications

## Recommendations

### For Question Generation (Next Phase)

1. **Prioritize High-Value Databases**
   - Focus 46% of questions (55/120) on Tier 1 databases
   - These provide the most reliable, comprehensive answers
   - Best demonstrate TogoMCP value-add

2. **Balance Question Categories**
   - Ensure each category has 15-25 questions
   - Mix simple and complex questions within each category
   - Include both single-database and integration questions

3. **Leverage Database Strengths**
   - **UniProt**: Protein identification, domain queries, cross-references
   - **PubChem**: Molecular properties, FDA drugs, stereoisomers
   - **ChEMBL**: Bioactivity filtering, target-compound relationships
   - **ClinVar**: Variant pathogenicity, disease associations
   - **GO**: Hierarchical navigation, term relationships
   - **Reactome**: Pathway membership, species specificity

4. **Cross-Database Integration Focus**
   - Create 25 integration questions (20% of total)
   - Test TogoID conversion capabilities
   - Verify cross-reference accuracy
   - Challenge multi-step reasoning

5. **Specificity and Niche Data**
   - Use Tier 3 databases for specificity questions
   - Highlight unique capabilities (NANDO for Japanese diseases)
   - Test handling of specialized terminology
   - Verify rare entity retrieval

6. **Avoid Pitfalls**
   - Don't overuse UniProt TrEMBL (use Swiss-Prot, reviewed=1)
   - Avoid timeout-prone queries (large aggregations without LIMIT)
   - Don't rely on incomplete external links (verify coverage first)
   - Test questions before finalizing (verify answers exist)

7. **Question Quality Checks**
   - Each question should have clear, verifiable answer
   - Avoid ambiguous or overly broad questions
   - Ensure database tools can efficiently answer
   - Verify expected answers using exploration reports

### Databases That Pair Well Together

**Protein-Centric Workflows**
- UniProt + PDB + Reactome (sequence → structure → pathways)
- UniProt + GO + NCBI Gene (function annotation across databases)
- ChEMBL + UniProt (drug target analysis)

**Chemical-Centric Workflows**
- PubChem + ChEBI + Rhea (compound → classification → reactions)
- ChEMBL + PubChem (bioactivity data enrichment)
- ChEBI + Reactome (compound pathway participation)

**Clinical-Centric Workflows**
- ClinVar + MedGen + MONDO (variant → phenotype → disease)
- MONDO + NANDO (international-Japanese disease mapping)
- ClinVar + NCBI Gene + UniProt (variant → gene → protein)

**Microbiology Workflows**
- BacDive + MediaDive + Taxonomy (strain → culture → classification)
- DDBJ + Taxonomy + NCBI Gene (sequence → organism → genes)

**Literature-Centric Workflows**
- PubMed + MeSH (literature search with controlled vocabulary)
- PubTator + PubMed (entity-focused literature mining)

### Particularly Interesting Findings

1. **Universal ChEBI Integration**
   - Rhea has 100% ChEBI coverage for compounds
   - Enables chemical-reaction linking across PubChem-ChEBI-Rhea

2. **Clinical Variant Ecosystem**
   - ClinVar-MedGen-MONDO form comprehensive clinical genetics network
   - 90% cross-reference coverage in MONDO enables disease integration

3. **Hierarchical Navigation Excellence**
   - GO with 48K terms in DAG structure
   - MeSH with 16 tree categories
   - Taxonomy with 47 hierarchical ranks
   - All support ancestor/descendant queries

4. **Japanese-Specific Resources**
   - NANDO provides unique coverage of Japanese intractable diseases
   - 2,777 diseases with bilingual labels and government policy links

5. **Structural Biology Integration**
   - PDB with 204K structures links to UniProt, Ensembl
   - Resolution data enables quality assessment
   - Experimental method diversity (X-ray, NMR, cryo-EM)

6. **Bacterial Strain Specialization**
   - BacDive with 97K strains has rich phenotypic data
   - MediaDive provides culture protocols
   - Strong Taxonomy integration

7. **Bioactivity Data Scale**
   - ChEMBL has 20M bioactivity measurements
   - PubChem has 1.7M bioassays
   - Enables drug discovery and repurposing queries

8. **Search Tool Quality**
   - search_uniprot_entity: Excellent for protein identification
   - search_chembl_molecule: Reliable compound search
   - search_pdb_entity: Fast structure lookup
   - OLS4 search: Comprehensive ontology search

9. **ID Conversion Infrastructure**
   - TogoID supports systematic ID conversion
   - Critical for integration questions
   - Well-documented conversion routes

10. **Expert Curation Value**
    - Swiss-Prot (923K proteins) shows massive quality difference vs TrEMBL
    - Reactome pathways are BioPAX Level 3 standardized
    - Rhea reactions are 100% chemically balanced

## Next Steps

**Ready for Question Generation Phase (PROMPT 2)**

The exploration phase is complete with:
- ✅ All 22 databases thoroughly explored
- ✅ Detailed exploration reports (8-21 KB each)
- ✅ SPARQL queries tested and documented
- ✅ Search tools verified with examples
- ✅ Cross-database opportunities identified
- ✅ Question coverage plan established

Proceed to generate 120 high-quality evaluation questions distributed across:
- 6 question categories (Precision, Completeness, Integration, Currency, Specificity, Structured Query)
- 22 databases (following the recommended distribution above)
- Multiple difficulty levels (simple lookups to complex multi-step queries)

Use the detailed findings in individual exploration reports to craft questions with:
- Specific, verifiable answers
- Clear testing objectives
- Appropriate complexity
- Biological realism
- Cross-database integration where valuable

---

**Exploration Status**: ✅ COMPLETE - All 22 databases documented
**Next Action**: Generate 120 evaluation questions based on this comprehensive exploration
**Documentation**: 279 KB of detailed reports available in `/Users/arkinjo/work/GitHub/togo-mcp/evaluation/exploration/`
