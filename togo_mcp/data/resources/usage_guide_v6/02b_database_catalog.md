## 📚 DATABASE CATALOG

All 36 RDF databases, with what each is *for*. Scan by the KIND of data you need (not by entity name), pick 1–3 candidates, then `get_MIE_file(database)` before any `run_sparql`. The exact `database=` key is **bold**.

Quick hints: "MANE" → `ensembl` · "drug targets" → `chembl` · "clinical variants" → `clinvar` · "pathways" → `reactome` · "gnomAD" / "variants" → `togovar` · "orthologs" → `oma` · "expression" → `bgee` · "glycobiology" → `glycosmos` · "superconductor" → `supercon`.

**By category** (a database may appear under several):

- **annotation** — `pubtator` `uniprot`
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

- **amrportal** — AMR Portal — Antimicrobial Resistance Surveillance. Global bacterial antimicrobial-resistance surveillance (NCBI Pathogen Detection / PATRIC / CABBAGE): 1.71M phenotypic susceptibility tests (MIC / disk-diffusion, interpreted resistant/susceptible) an… _(categories: antimicrobial, microbe)_  
  keywords: antimicrobial resistance, amr, antibiotic, resistance gene, mutation, mic, susceptibility, phenotype, genotype, breakpoint, multi-drug resistance, surveillance, pathogen, bacteria, aro, card
- **bacdive** — BacDive — Bacterial Diversity Metadatabase. Standardized bacterial + archaeal strain metadata: taxonomy, morphology, physiology, growth/culture conditions, media, isolation source, enzymes, 16S/genome sequences, pathogenicity/biosafety — 97k+… _(categories: microbe)_  
  keywords: bacteria, archaea, strain, culture, growth condition, medium, morphology, physiology, 16s rrna, genome, isolation, habitat, temperature, oxygen tolerance, gram stain, enzyme, biosafety
- **bgee** — Bgee — gene expression across animal species. Curated gene-expression calls (present / absent) integrating RNA-Seq, Affymetrix, EST, and in-situ data across 52 animal species, each call tagged with anatomy (UBERON/CL), developmental stage, sex,… _(categories: gene, taxonomy)_  
  keywords: gene expression, tissue, anatomical entity, developmental stage, rna-seq, in situ hybridization, cross-species, expression call, absence call, confidence, uberon, cell type, orthology, taxon
- **brenda** — BRENDA (Braunschweig Enzyme Database). Manually curated enzyme data classified by EC number: enzyme instances (one per organism), EC-class definitions, inhibitors/activators/cofactors, substrates/products, reactions, tissue and subcellula… _(categories: enzymology, protein, reaction)_  
  keywords: enzyme, ec number, enzymatic reaction, substrate, product, inhibitor, activator, cofactor, biochemistry, catalysis, inchi, inchikey, tissue expression, subcellular localization
- **chebi** — ChEBI — Chemical Entities of Biological Interest. OWL ontology of 224k+ chemical entities (small molecules, ions, radicals, functional groups) with a rdfs:subClassOf class hierarchy, molecular properties (formula/mass/InChI/SMILES/charge) in the che… _(categories: compound, ontology)_  
  keywords: chemical entity, small molecule, metabolite, lipid, amino acid, ion, radical, functional group, biological role, drug, molecular formula, inchi, smiles, ontology, hierarchy, chebi, compound
- **chembl** — ChEMBL RDF. Manually curated bioactive molecules with drug-like properties: ~1.9M compounds, 1.9M assays, 21M+ bioactivity measurements (IC50/Ki/…), drug targets, mechanisms of action, and disease indications —… _(categories: compound, drug_target)_  
  keywords: compound, bioactive molecule, drug, target, bioactivity, ic50, ki, assay, inhibitor, mechanism of action, drug indication, atc, smiles, inchikey, protein classification, uniprot, mesh, development phase
- **clinvar** — ClinVar RDF. NCBI's public archive of human genomic variants and their clinically asserted significance (pathogenic/benign/VUS across germline, oncogenicity, and somatic branches), with variant→gene links and dis… _(categories: disease, variant)_  
  keywords: variant, mutation, clinical significance, pathogenic, benign, uncertain significance, vus, snp, indel, cnv, gene, disease, phenotype, germline, somatic, oncogenicity, hgvs, medgen
- **ddbj** — DDBJ — DNA Data Bank of Japan. INSDC nucleotide sequence records (~280M entries across 21 divisions — EST/PAT/GSS dominate by count, annotated genomes in BCT/VRL/PHG/PLN) with Gene/CDS/RNA features carrying FALDO coordinates, Sequ… _(categories: sequence)_  
  keywords: nucleotide sequence, dna, rna, gene, cds, genome, accession, insdc, division, est, patent, organism, taxonomy, feature annotation, locus tag, bioproject, biosample, ncbi protein
- **ensembl** — Ensembl RDF. Genome annotation for vertebrates and five non-vertebrate divisions (bacteria/fungi/metazoa/plants/ protists): genes typed by biotype (protein-coding, lncRNA, miRNA, pseudogenes), transcripts with qu… _(categories: gene, sequence)_  
  keywords: gene, transcript, mrna, protein, genome, annotation, chromosome, exon, biotype, protein-coding, lncrna, mirna, pseudogene, mane select, coordinates, stable id, species, vertebrate
- **glycosmos** — GlyCosmos — Glycoscience Portal. Integrated glycoscience: glycan structures (GlyTouCan, multi-format WURCS/IUPAC/GlycoCT), glycoproteins with residue-level glycosylation sites (FALDO), glycogenes with GO annotation, disease→glycogen… _(categories: disease, gene, glycan, protein)_  
  keywords: glycan, glycosylation, glycoprotein, saccharide, wurcs, glytoucan, n-glycan, o-glycan, glycogene, monosaccharide, glycan motif, epitope, lectin, cazy, carbohydrate-active enzyme, glycoside hydrolase, glycosyltransferase, ec number, disease gene, doid, gene ontology, tissue expression, human protein atlas, glycolipid
- **go** — Gene Ontology (GO). Cross-species controlled vocabulary for gene-product function, organized into three independent domains (biological_process, molecular_function, cellular_component) with a DAG hierarchy, definitions,… _(categories: ontology)_  
  keywords: gene ontology, ontology, biological process, molecular function, cellular component, go term, functional annotation, obo, controlled vocabulary, hierarchy, subclassof, dag
- **hco** — HCO — Human Chromosome Ontology (cytobands). The human cytogenetic map: every Giemsa-stained chromosome band (ISCN name, e.g. _(categories: genomics, ontology)_  
  keywords: cytoband, chromosome band, karyotype, cytogenetic, giemsa stain, ideogram, genomic coordinates, grch37, grch38, genome build, faldo, chromosome location, iscn, human chromosome
- **hgnc** — HGNC — HUGO Gene Nomenclature Committee. Authoritative approved human gene nomenclature: official symbol, full name, HGNC ID, chromosomal band, and a central hub of typed cross-references (NCBI Gene, Ensembl, RefSeq, UniProt, OMIM, Orphanet… _(categories: gene, genomics)_  
  keywords: human gene, gene nomenclature, gene symbol, approved gene, gene name, hgnc id, chromosomal location, cross-reference, id mapping, ncbi gene, ensembl, uniprot, omim, orphanet, ec code, mirbase, ortholog, gene alias
- **jpostdb** — jPOST — Japan ProteOme STandard repository. Reanalysed mass-spectrometry proteomics submissions: each Project (JPST id) bundles Datasets with experimental Profiles (sample tissue/disease/species, enzyme, MS mode) plus identified Peptides, PSMs… _(categories: protein)_  
  keywords: proteomics, mass spectrometry, peptide, psm, peptide spectrum match, protein identification, post-translational modification, ptm, unimod, psi-ms, reanalysis, proteome, shotgun proteomics
- **massbank** — MassBank — reference mass spectra for small molecules. Open repository of reference MS/MS mass spectra for small molecules (metabolites, drugs, natural products, environmental chemicals): each record links a measured peak list + analytical/instrument met… _(categories: compound)_  
  keywords: mass spectrometry, mass spectra, ms/ms, tandem ms, metabolomics, metabolite, spectral library, fragmentation, peak, molecular formula, inchikey, small molecule, compound identification, splash, exposomics, instrument type, ion mode
- **mco** — MCO — Mouse Chromosome Ontology. Reference ontology of the mouse (Mus musculus) chromosome set — the 22 chromosomes (1-19, X, Y, MT) as owl:Classes, each with per-build GRCm38 (mm10) and GRCm39 (mm39) instances carrying chromosome l… _(categories: genomics, ontology)_  
  keywords: mouse chromosome, mus musculus, karyotype, genome build, grcm38, grcm39, mm10, mm39, chromosome length, reference genome, genome assembly
- **medgen** — MedGen — NCBI Medical Genetics. NCBI's UMLS-derived registry of ~234k clinical concepts (diseases, phenotypes, findings) with genetic components — semantic typing, disease→gene links, concept relationships, structured attributes, a… _(categories: disease, gene)_  
  keywords: medical genetics, disease, phenotype, clinical concept, syndrome, finding, rare disease, genetic condition, semantic type, umls, omim, orphanet, hpo, mondo, mesh, snomed, inheritance
- **mediadive** — MediaDive — DSMZ Microbial Culture Media Database. Standardized microbial growth-media recipes from DSMZ: 3,289 media built from 1,489 ingredients (chemically cross-referenced to ChEBI/CAS/KEGG/PubChem), with hierarchical medium→solution→recipe compo… _(categories: microbe)_  
  keywords: culture medium, growth medium, recipe, ingredient, composition, concentration, dsmz, bacteria, archaea, fungi, yeast, microalgae, phage, growth condition, temperature, ph, oxygen, chebi, cas, kegg, bacdive, strain
- **mesh** — MeSH RDF — Medical Subject Headings. NLM's controlled biomedical thesaurus for PubMed indexing: ~30k topical descriptors on a tree-number hierarchy (16 categories A–Z), plus ~250k supplementary chemical records, qualifiers, ~467k concep… _(categories: disease, ontology)_  
  keywords: controlled vocabulary, thesaurus, medical subject headings, descriptor, tree number, qualifier, subheading, supplementary concept record, concept, term, pubmed indexing, disease vocabulary, chemical vocabulary, cross-reference
- **mogplus** — MoG+ — Mouse Genomes plus (variant / genotype RDF). Genome-wide sequence variation (SNVs + small indels, GRCm39) across 62 inbred and wild-derived mouse strains: per-strain genotype calls, Ensembl-VEP and SnpEff functional consequences (Sequence Ontol… _(categories: genomics, variant)_  
  keywords: mouse variant, mouse genome, snv, indel, genotype, inbred strain, wild-derived, vep, snpeff, consequence, sequence ontology, vcf, grcm39, ensembl gene, genome variation, bioresource
- **mondo** — MONDO — Mondo Disease Ontology. Unified disease ontology integrating 39+ source vocabularies into one owl:Class hierarchy (~29.9k active disease classes) with definitions, synonyms, a single hasDbXref cross-reference predicate to O… _(categories: disease, ontology)_  
  keywords: disease, ontology, disorder, syndrome, rare disease, genetic disease, infectious disease, cancer, cross-reference, omim, orphanet, doid, mesh, icd, disease classification, subclass hierarchy
- **nando** — NANDO — Nanbyo (Intractable) Disease Ontology. Japanese ontology of ~2,777 designated intractable/rare disease classes in a 5-level hierarchy, with trilingual labels, government notification numbers, and skos:closeMatch mappings to MONDO. _(categories: disease, ontology)_  
  keywords: rare disease, intractable disease, nanbyo, ontology, disease hierarchy, designated disease, notification number, japanese, mondo mapping, classification, kegg
- **nbrc** — NBRC — NITE Biological Resource Center culture catalogue. Catalogue of ~24k microbial strains (bacteria, archaea, fungi, yeasts, algae, phages) distributed by Japan's NITE Biological Resource Center — accepted scientific name, NBRC catalogue number, organis… _(categories: microbe)_  
  keywords: culture collection, biological resource, microbial strain, nbrc, nite, bacteria, archaea, fungi, yeast, algae, type strain, isolation source, growth temperature, culture medium, biosafety level, habitat, geographic origin, strain equivalence
- **ncbigene** — NCBI Gene. Gene records for all organisms (57.8M genes): symbol, full name, gene type, chromosome/cytoband, synonyms, nomenclature status, cross-species orthology, and IRI/string cross-references to Ensembl, HG… _(categories: gene)_  
  keywords: gene, gene symbol, gene type, ncbi, annotation, synonym, chromosome, cytoband, organism, taxonomy, ortholog, nomenclature, ensembl, hgnc, omim, mirbase, ncrna, protein-coding, pseudogene
- **oma** — OMA — Orthologous MAtrix. Phylogenomic orthology across the tree of life: 17.4M proteins from 2,927 species organized into Hierarchical Orthologous Groups (HOGs), pairwise ortholog clusters, and paralog clusters at every node… _(categories: genomics, protein)_  
  keywords: ortholog, paralog, homolog, gene family, comparative genomics, hierarchical orthologous group, hog, oma group, orthology, phylogenomics, species tree, cross-species, evolution, protein
- **ontology** — Ontology graphs (RDF Portal primary). Cross-ontology term-resolution and hierarchy-expansion surface hosting ~20 OBO/non-OBO ontologies without their own MIE (HP, UBERON, CL, SO, ECO, EFO, FMA, PRO, SIO, EDAM, MEO, PO, CMO, UO, …), for r… _(categories: ontology)_  
  keywords: ontology, controlled vocabulary, term resolution, iri resolution, label, synonym, subsumption, subclassof, part of, partonomy, anatomy, phenotype, cell type, evidence code, sequence feature, obsolete term, obo, hierarchy expansion
- **pdb** — PDB — Protein Data Bank. 3D structural data for biological macromolecules (~255,508 entries) from X-ray crystallography, cryo-EM, and NMR, with experimental method, resolution, biological assembly / oligomeric state, EC enzy… _(categories: protein, structure)_  
  keywords: protein structure, 3d structure, x-ray crystallography, cryo-em, nmr, macromolecule, resolution, biological assembly, oligomeric state, ec number, enzyme, mutation, disulfide, metal coordination, sifts, pfam, interpro, cath, scop, ligand, binding site
- **pubchem** — PubChem RDF. Chemical compounds + substances with typed molecular descriptors (SMILES, InChI, MW, formula, XLogP3), ontology classifications (ChEBI/SNOMED/NCI), FDA drug roles, stereoisomer links, and a structure… _(categories: compound)_  
  keywords: compound, chemical, molecule, drug, cid, smiles, inchi, molecular weight, descriptor, substance, bioassay, bioactivity, assay outcome, protein target, ic50, pathway, chebi, fda approved, patent
- **pubmed** — PubMed — NCBI biomedical literature. 37M+ MEDLINE citations (articles, reviews) with title/abstract, journal + bibliographic metadata, ordered author lists, and MeSH controlled-vocabulary topic/publication-type annotations — the literat… _(categories: literature)_  
  keywords: publication, article, review, citation, abstract, author, journal, doi, pmid, mesh term, publication type, biomedical literature, bibliography
- **pubtator** — PubTator Central RDF. Biomedical entity annotations text-mined from PubMed articles — Disease (MeSH) and Gene (NCBI Gene) mentions as typed oa:Annotation nodes, plus dbSNP Variant annotations, each linked to a PubMed arti… _(categories: annotation, literature)_  
  keywords: annotation, text mining, named entity recognition, literature, pubmed, pmid, disease, gene, variant, mesh, ncbi gene, dbsnp, co-mention, bioconcept
- **reactome** — Reactome Pathway Database. Expert-curated biological pathways and reactions in BioPAX Level 3: hierarchical pathways, biochemical reactions (EC numbers), physical entities (proteins/complexes/small molecules), catalysis/regula… _(categories: pathway)_  
  keywords: pathway, reaction, biopax, signaling, metabolism, protein, complex, small molecule, catalyst, enzyme, ec number, modification, phosphorylation, cellular location, gene ontology, species
- **rhea** — Rhea — Annotated Biochemical Reactions. Expert-curated, atom-balanced biochemical reactions (18,071 master reactions) with ChEBI-linked participants, EC-number and GO cross-references, transport/location annotations, and PubMed citations;… _(categories: reaction)_  
  keywords: biochemical reaction, enzyme, substrate, product, cofactor, ec number, stoichiometry, mass balance, chebi, metabolite, transport, directional reaction, catalysis
- **supercon** — SuperCon — NIMS Superconducting Materials Database. Curated experimental records for oxide and metallic superconductors (NIMS), extracted from ~7,249 journal articles: critical temperature (Tc and variants), critical magnetic fields, crystal structure… _(categories: materials, physics)_  
  keywords: superconductor, superconducting material, critical temperature, tc, critical field, cuprate, oxide, inorganic compound, crystal structure, lattice parameter, materials informatics, nims, physical property, experimental measurement
- **taxonomy** — NCBI Taxonomy RDF. Hierarchical biological classification of ~2.84M taxa (species → root) with scientific/common names, synonyms, 45 rank IRIs, nuclear+mitochondrial genetic codes, and owl:sameAs/rdfs:seeAlso cross-lin… _(categories: taxonomy)_  
  keywords: taxonomy, organism, species, taxon, rank, lineage, phylogeny, classification, scientific name, common name, synonym, genetic code, subtree, clade, ncbi taxonomy
- **togovar** — TogoVar — Japanese/human genome variation. GRCh38 human genome variants (SNV/Deletion/Insertion/MNV/Indel) with normalized+VCF coordinates, Ensembl-VEP per-transcript consequences (SO terms, SIFT/PolyPhen/AlphaMissense, HGVS), dbSNP links, an… _(categories: disease, genomics, variant)_  
  keywords: variant, variation, mutation, snv, snp, indel, genome, human, japanese, dbsnp, clinvar, vep, consequence, sequence ontology, sift, polyphen, pathogenic, clinical significance
- **uniprot** — UniProt RDF. Curated (Swiss-Prot) and automatic (TrEMBL) protein sequence + functional annotation: sequences, domains, PTMs, isoforms, natural variants, disease links, GO terms, EC/enzyme activity, catalysed Rhea… _(categories: annotation, protein)_  
  keywords: protein, sequence, swiss-prot, trembl, reviewed, function, domain, isoform, enzyme, ec number, natural variant, disease, gene ontology, cross-reference

