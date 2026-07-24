## 📚 DATABASE CATALOG

All 36 RDF databases, with what each is *for*. Scan by the KIND of data you need (not by entity name), pick 1–3 candidates, then `get_MIE_file(database)` before any `run_sparql`. The exact `database=` key is **bold**.

Quick hints: "MANE" → `ensembl` · "drug targets" → `chembl` · "clinical variants" → `clinvar` · "pathways" → `reactome` · "gnomAD" / "variants" → `togovar` · "orthologs" → `oma` · "expression" → `bgee` · "glycobiology" → `glycosmos` · "superconductor" → `supercon`.

**By category** (a database may appear under several):

- **antimicrobial** — `amrportal`
- **compound** — `chebi` `chembl` `massbank` `pubchem`
- **disease** — `clinvar` `glycosmos` `medgen` `mesh` `mondo` `nando` `togovar`
- **drug_target** — `chembl`
- **enzymology** — `brenda`
- **gene** — `bgee` `ensembl` `glycosmos` `hgnc` `medgen` `ncbigene`
- **genomics** — `hco` `hgnc` `mco` `mogplus` `oma` `togovar`
- **glycan** — `glycosmos`
- **literature** — `pubmed` `pubtator`
- **materials** — `supercon`
- **microbe** — `amrportal` `bacdive` `mediadive` `nbrc`
- **ontology** — `chebi` `go` `hco` `mco` `mesh` `mondo` `nando` `ontology`
- **pathway** — `reactome`
- **physics** — `supercon`
- **protein** — `brenda` `glycosmos` `jpostdb` `oma` `pdb` `uniprot`
- **reaction** — `brenda` `rhea`
- **sequence** — `ddbj` `ensembl`
- **structure** — `pdb`
- **taxonomy** — `bgee` `taxonomy`
- **variant** — `clinvar` `mogplus` `togovar`

**All databases** (alphabetical):

- **amrportal** — AMR Portal. Antimicrobial resistance surveillance data from NCBI Pathogen Detection, PATRIC, and CABBAGE. _(categories: antimicrobial, microbe)_  
  keywords: antimicrobial resistance, amr, antibiotic, mic, minimum inhibitory concentration, phenotype, genotype, resistance gene, bacteria, pathogen, susceptibility, surveillance, disk diffusion, multi-drug resistance, breakpoint
- **bacdive** — BacDive - The Bacterial Diversity Metadatabase. BacDive provides standardized bacterial and archaeal strain information covering taxonomy, morphology, physiology, cultivation conditions, and molecular data with 97,000+ strain records. _(categories: microbe)_  
  keywords: bacteria, archaea, strain, culture, growth condition, medium, morphology, physiology, 16s rrna, genome, isolation, habitat, temperature, oxygen, gram stain
- **bgee** — Bgee. Bgee is a curated database of gene expression patterns across animal species, integrating RNA-Seq, Affymetrix, EST, and in situ hybridization data into uniform expression "calls" (present / absent) t… _(categories: gene, taxonomy)_  
  keywords: gene expression, bgee, anatomical entity, tissue, developmental stage, rna-seq, in situ hybridization, cross-species, uberon, genex, homology, tpm, expression call
- **brenda** — BRENDA (Braunschweig Enzyme Database). BRENDA is the world's most comprehensive manually curated enzyme database, covering functional and taxonomic data for enzymes classified by EC number. _(categories: enzymology, protein, reaction)_  
  keywords: enzyme, ec number, brenda, enzymatic reaction, substrate, product, inhibitor, activator, cofactor, biochemistry, catalysis, inchi, inchikey, tissue expression, subcellular localization
- **chebi** — ChEBI (Chemical Entities of Biological Interest). ChEBI is a comprehensive ontology database containing 224,523+ chemical entities including small molecules, atoms, ions, radicals, and functional groups. _(categories: compound, ontology)_  
  keywords: chemical entity, small molecule, metabolite, lipid, amino acid, nucleotide, ion, radical, functional group, biological role, drug, ontology, hierarchy, chebi, compound
- **chembl** — ChEMBL RDF. Manually curated database of bioactive molecules with drug-like properties containing ~1.9M compounds, 1.9M assays, 21M+ bioactivity measurements, and comprehensive drug development data. _(categories: compound, drug_target)_  
  keywords: compound, bioactive molecule, drug, target, bioactivity, ic50, assay, inhibitor, mechanism of action, indication, atc, clinical trial, smiles, inchikey, cell line, tissue, binding affinity, uniprot
- **clinvar** — ClinVar RDF. ClinVar aggregates information about genomic variation and its relationship to human health. _(categories: disease, variant)_  
  keywords: variant, mutation, clinical significance, pathogenic, benign, uncertain significance, snp, indel, gene, disease, phenotype, allele, hgvs, germline, vus
- **ddbj** — DDBJ (DNA Data Bank of Japan). DDBJ RDF provides nucleotide sequence data from INSDC (International Nucleotide Sequence Database Collaboration). _(categories: sequence)_  
  keywords: nucleotide sequence, dna, rna, gene, genome, accession, organism, feature annotation, est, pat, insdc, wgs, division, genbank, embl
- **ensembl** — Ensembl RDF. Ensembl provides genome annotations for vertebrates and non-vertebrate divisions (bacteria, fungi, metazoa, plants, protists). _(categories: gene, sequence)_  
  keywords: gene, transcript, mrna, protein, genome, annotation, chromosome, exon, biotype, protein-coding, lncrna, mirna, vertebrate, stable id, species
- **glycosmos** — GlyCosmos RDF Database. Comprehensive glycoscience portal integrating glycan structures (GlyTouCan), glycoproteins, glycosylation sites, glycogenes, glycoepitopes, lectins, and glycolipids. _(categories: disease, gene, glycan, protein)_  
  keywords: glycan, glycosylation, glycoprotein, saccharide, wurcs, glytoucan, sugar, n-glycan, o-glycan, epitope, lectin, glycogene, glycomics, monosaccharide, glycosylation site, glycan motif, disease, gene ontology, go annotation, disease gene, doid, cazy, carbohydrate-active enzyme, glycoside hydrolase, glycosyltransferase, polysaccharide lyase, carbohydrate-binding module, ec number, glycolipid, tissue expression, human protein atlas, hpa, lectin name, lectin grounding, carbogrove, lfdb, unilectin, agglutinin
- **go** — Gene Ontology (GO). Comprehensive ontology for annotating genes and gene products across all organisms. _(categories: ontology)_  
  keywords: gene ontology, biological process, molecular function, cellular component, protein annotation, go term, hierarchy, obo, controlled vocabulary, evidence code, gene product, annotation
- **hco** — Human Chromosome Ontology (HCO). HCO is a compact ontology of the human cytogenetic map: every Giemsa-stained chromosome band (cytoband, ISCN nomenclature such as 13q14.2) with its genomic coordinates on both GRCh37 and GRCh38, its… _(categories: genomics, ontology)_  
  keywords: cytoband, chromosome band, karyotype, human chromosome, cytogenetic, giemsa, ideogram, chromosome, genomic coordinates, grch37, grch38, genome build, faldo, chromosome location, band
- **hgnc** — HGNC (HUGO Gene Nomenclature Committee). HGNC is the authoritative resource for approved human gene nomenclature, providing unique symbols and names for every human gene. _(categories: gene, genomics)_  
  keywords: gene, human gene, gene nomenclature, gene symbol, hgnc, hugo, approved gene, gene name, chromosomal location, gene alias, gene cross-reference, omim, ncbi gene, ensembl gene
- **jpostdb** — jPOST (Japan ProteOme STandard repository). jPOST is a curated proteomics data repository providing reanalysed mass-spectrometry submissions originally deposited at PRIDE / PeptideAtlas / MassIVE / iProx and at jPOSTrepo itself. _(categories: protein)_  
  keywords: proteomics, mass spectrometry, jpost, jpostdb, peptide, psm, peptide spectrum match, protein identification, post-translational modification, ptm, unimod, psi-ms, reanalysis, proteome, shotgun proteomics
- **massbank** — MassBank. MassBank is an open repository of reference mass spectra for small molecules (metabolites, environmental chemicals, drugs, natural products). _(categories: compound)_  
  keywords: mass spectrometry, mass spectra, ms/ms, tandem ms, metabolomics, metabolite, spectral library, fragmentation, peak, molecular formula, inchikey, small molecule, compound identification, splash
- **mco** — Mouse Chromosome Ontology (MCO). MCO is a small reference ontology of the mouse (Mus musculus) chromosome set: the 22 chromosomes (1-19, X, Y, MT) as an owl:Class hierarchy, each with a per-build INSTANCE on GRCm38 (mm10) and GRCm39… _(categories: genomics, ontology)_  
  keywords: mouse chromosome, mus musculus, chromosome, karyotype, genome build, grcm38, grcm39, mm10, mm39, chromosome length, reference genome, genome assembly
- **medgen** — MedGen (Medical Genetics). NCBI's portal for medical conditions with genetic components, containing 233,939 clinical concepts (diseases, phenotypes, findings). _(categories: disease, gene)_  
  keywords: medical genetics, disease, phenotype, clinical concept, omim, orphanet, hpo, snomed, icd, inheritance, rare disease, syndrome, disorder, finding, genetic condition
- **mediadive** — MediaDive - Microbial Culture Media Database. Comprehensive culture media database from DSMZ with 3,289 standardized recipes for bacteria, archaea, fungi, yeast, microalgae, and phages. _(categories: microbe)_  
  keywords: culture medium, growth medium, recipe, ingredient, bacteria, archaea, fungi, yeast, microalgae, phage, dsmz, bacdive, media, chebi, component
- **mesh** — Medical Subject Headings (MeSH) RDF. National Library of Medicine's controlled vocabulary thesaurus for biomedical literature indexing. _(categories: disease, ontology)_  
  keywords: medical subject headings, controlled vocabulary, thesaurus, descriptor, tree number, qualifier, disease, anatomy, pharmacology, organism, supplementary record, concept, annotation, pubmed indexing
- **mogplus** — MoG+ (Mouse Genomes plus) variant / genotype RDF. Genome-wide sequence variation across inbred and wild-derived mouse strains, from the MoG+ resource. _(categories: genomics, variant)_  
  keywords: mouse variant, mouse genome, snv, indel, genotype, inbred strain, vep, snpeff, consequence, vcf, grcm39, ensembl gene, genome variation, bioresource
- **mondo** — MONDO (Monarch Disease Ontology). Comprehensive disease ontology integrating 39+ disease databases into a unified hierarchical classification system. _(categories: disease, ontology)_  
  keywords: disease, ontology, disorder, syndrome, rare disease, genetic disease, infectious disease, omim, orphanet, mesh, icd, doid, cross-reference, phenotype, monarch
- **nando** — NANDO (Nanbyodata Disease Ontology). Japanese ontology for intractable (rare) diseases with 2,777 disease classes in a hierarchical taxonomy. _(categories: disease, ontology)_  
  keywords: intractable disease, rare disease, japanese, nanbyou, nando, orphanet, icd10, mondo, designated disease, hierarchy, phenotype, disorder, government support, classification
- **nbrc** — NBRC (NITE Biological Resource Center culture catalogue). Catalogue of microbial strains distributed by the NITE Biological Resource Center (NBRC, Japan). _(categories: microbe)_  
  keywords: culture collection, biological resource, microbial strain, nbrc, nite, bioresource, bacteria, archaea, fungi, yeast, type strain, isolation source, growth temperature, culture medium, biosafety level
- **ncbigene** — NCBI Gene. Comprehensive gene database with 57.8M+ entries covering protein-coding genes, ncRNAs, pseudogenes, biological regions, and other gene types across all organisms. _(categories: gene)_  
  keywords: gene, ncbi, annotation, transcript, gene symbol, synonym, chromosome, organism, function, go term, pathway, refseq, locus, protein-coding, ncrna
- **oma** — OMA (Orthologous MAtrix). OMA is a large-scale, phylogenomics-based resource for inferring orthologs and paralogs across the tree of life. _(categories: genomics, protein)_  
  keywords: ortholog, paralog, homolog, gene family, comparative genomics, hierarchical orthologous groups, hog, oma group, orthology, species tree, phylogenomics, gene tree, cross-species, evolution
- **ontology** — Ontology Graphs (RDF Portal primary endpoint). A cross-ontology TERM-RESOLUTION and HIERARCHY-EXPANSION surface, not a data source. _(categories: ontology)_  
  keywords: ontology, controlled vocabulary, term lookup, label resolution, iri resolution, subsumption hierarchy, subclass expansion, partonomy, part of, anatomy, phenotype, cell type, evidence code, sequence feature type, synonym, obsolete term, obo
- **pdb** — Protein Data Bank (PDB). The PDB RDF database contains 3D structural data for biological macromolecules (proteins, nucleic acids, complexes) derived from X-ray crystallography, NMR, and cryo-EM. _(categories: protein, structure)_  
  keywords: protein structure, 3d structure, crystal, x-ray crystallography, cryo-em, nmr, macromolecule, ligand, binding site, resolution, biological assembly, oligomeric state, ec number, enzyme, mutation, modified residue, disulfide, metal coordination, sifts, pfam, polymer chain
- **pubchem** — PubChem RDF. Comprehensive public database of chemical molecules and biological activities containing 119M compounds, 329M substance/descriptor records, 1.7M bioassays, 167K genes, 249K proteins, 80K pathways, an… _(categories: compound)_  
  keywords: compound, chemical, molecule, drug, cid, smiles, inchi, cas, bioassay, bioactivity, pharmacology, toxicology, descriptor, substance, target
- **pubmed** — PubMed. Biomedical literature database with 37+ million citations from MEDLINE, life science journals, and online books. _(categories: literature)_  
  keywords: publication, article, citation, abstract, author, journal, mesh term, pmid, doi, review, biomedical literature, research paper, clinical trial, full text
- **pubtator** — PubTator Central RDF. PubTator Central provides biomedical entity annotations extracted from PubMed literature through text mining and manual curation. _(categories: literature)_  
  keywords: annotation, entity, article, gene, disease, mutation, text mining, named entity recognition, bioconcept, pmid, pubmed, curation
- **reactome** — Reactome Pathway Database. Curated knowledgebase of biological pathways and processes in BioPAX Level 3 format. _(categories: pathway)_  
  keywords: pathway, biological pathway, reaction, signaling cascade, protein, gene, complex, catalyst, disease pathway, regulation, go term, biopax, event, species
- **rhea** — Rhea - Annotated Reactions Database. Expert-curated database of 18,071 biochemical reactions with atom-balanced chemistry, EC-number and ChEBI cross-references, and literature citations. _(categories: reaction)_  
  keywords: biochemical reaction, enzyme, substrate, product, cofactor, ec number, stoichiometry, mass balance, chebi, uniprot, catalysis, metabolite, directional, bidirectional, transport
- **supercon** — SuperCon. SuperCon is a curated database of superconducting materials compiled by NIMS (National Institute for Materials Science, Japan). _(categories: materials, physics)_  
  keywords: superconductor, superconducting material, critical temperature, tc, nims, chemical formula, material science, inorganic compound, oxide, cuprate, experimental measurement, physical property
- **taxonomy** — NCBI Taxonomy RDF. Comprehensive biological taxonomic classification covering 2.7M+ organisms from bacteria to mammals. _(categories: taxonomy)_  
  keywords: taxonomy, organism, species, taxon, phylogeny, lineage, rank, bacteria, vertebrate, plant, insect, fungus, ncbi taxonomy, scientific name, classification
- **togovar** — TogoVar. TogoVar is an integrated Japanese/human genome variation database. _(categories: disease, genomics, variant)_  
  keywords: variant, variation, mutation, polymorphism, snv, snp, indel, genome, human, japanese, dbsnp, clinvar, vep, consequence, allele
- **uniprot** — UniProt RDF. Comprehensive protein sequence and functional information integrating Swiss-Prot (manually curated, 574,627 current entries — 589,059 if the 14,432 DELETED entries in the co-hosted `obsolete` graph a… _(categories: protein)_  
  keywords: protein, sequence, swiss-prot, trembl, reviewed, annotation, function, domain, isoform, enzyme, variant, disease association, gene ontology, pathway, cross-reference

