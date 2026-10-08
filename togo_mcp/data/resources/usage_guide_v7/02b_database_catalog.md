## 📚 DATABASE CATALOG

All 45 RDF databases, one line each: what it is *for*, then its top keywords. Scan by the KIND of data you need (not by entity name), pick 1–3 candidates, then `get_MIE_file(database)` before any `run_sparql`. The exact `database=` key is **bold**. Full descriptions and every keyword: reference file `database-catalog.md` (see 📎 MORE DETAIL) — fetch it only if these lines do not separate your candidates.

Quick hints: "MANE" → `ensembl` · "drug targets" → `chembl` · "clinical variants" → `clinvar` · "pathways" → `reactome` · "gnomAD" / "variants" → `togovar` · "orthologs" → `oma` · "expression" → `bgee` · "glycobiology" → `glycosmos` · "superconductor" → `supercon`.

**By category** (a database may appear under several):

- **annotation** — `bh26microbes` `marpolbase` `pubtator` `uniprot`
- **antimicrobial** — `amrportal`
- **compound** — `chebi` `chembl` `idsm` `lipidmaps` `massbank` `pubchem` `swisslipids` `wikipathways`
- **disease** — `clinvar` `glycosmos` `gwascatalog` `medgen` `mesh` `mondo` `nando` `pubcasefinder` `togovar`
- **drug_target** — `chembl` `idsm`
- **enzymology** — `brenda`
- **gene** — `bgee` `ensembl` `fantabio` `glycosmos` `hgnc` `marpolbase` `medgen` `ncbigene` `pubcasefinder` `wikipathways`
- **genomics** — `bh26microbes` `fantabio` `gwascatalog` `hco` `hgnc` `marpolbase` `mco` `mogplus` `oma` `togovar`
- **glycan** — `glycosmos`
- **literature** — `pubmed` `pubtator`
- **materials** — `supercon`
- **microbe** — `amrportal` `bacdive` `bh26microbes` `mediadive` `nbrc`
- **ontology** — `chebi` `go` `hco` `lipidmaps` `mco` `mesh` `mondo` `nando` `ontology` `swisslipids`
- **pathway** — `reactome` `wikipathways`
- **physics** — `supercon`
- **protein** — `brenda` `glycosmos` `jpostdb` `oma` `pdb` `uniprot`
- **reaction** — `brenda` `rhea`
- **sequence** — `ddbj` `ensembl`
- **structure** — `pdb`
- **taxonomy** — `bgee` `taxonomy`
- **variant** — `clinvar` `gwascatalog` `mogplus` `togovar`

**All databases** (alphabetical):

- **amrportal** — AMR Portal. Global bacterial antimicrobial-resistance surveillance (NCBI Pathogen Detection / PATRIC / CABBAGE): 1.71M ph… _[antimicrobial resistance, amr, antibiotic, resistance gene, mutation, mic]_
- **bacdive** — BacDive. Standardized bacterial + archaeal strain metadata: taxonomy, morphology, physiology, growth/culture condition… _[bacteria, archaea, strain, culture, growth condition, medium]_
- **bgee** — Bgee. Curated gene-expression calls (present / absent) integrating RNA-Seq, Affymetrix, EST, and in-situ data acros… _[gene expression, tissue, anatomical entity, developmental stage, rna-seq, in situ hybridization]_
- **bh26microbes** — BH26 Microbes. Experimental BioHackathon 2026 dataset of KofamScan KEGG Orthology (KO) assignments — with HMM score, E-value… _[kegg orthology, ko, kofamscan, functional annotation, hmm profile, prokaryotic genome]_
- **brenda** — BRENDA. Manually curated enzyme data classified by EC number: enzyme instances (one per organism), EC-class definitio… _[enzyme, ec number, enzymatic reaction, substrate, product, inhibitor]_
- **chebi** — ChEBI. OWL ontology of 224k+ chemical entities (small molecules, ions, radicals, functional groups) with a rdfs:subC… _[chemical entity, small molecule, metabolite, lipid, amino acid, ion]_
- **chembl** — ChEMBL RDF. Manually curated bioactive molecules with drug-like properties: ~1.9M compounds, 1.9M assays, 21M+ bioactivit… _[compound, bioactive molecule, drug, target, bioactivity, ic50]_
- **clinvar** — ClinVar RDF. NCBI's public archive of human genomic variants and their clinically asserted significance (pathogenic/benign… _[variant, mutation, clinical significance, pathogenic, benign, uncertain significance]_
- **ddbj** — DDBJ. INSDC nucleotide sequence records (~280M entries across 21 divisions — EST/PAT/GSS dominate by count, annotat… _[nucleotide sequence, dna, rna, gene, cds, genome]_
- **ensembl** — Ensembl RDF. Genome annotation for vertebrates and five non-vertebrate divisions (bacteria/fungi/metazoa/plants/ protists)… _[gene, transcript, mrna, protein, genome, annotation]_
- **fantabio** — Fanta.bio. Human (GRCh38) and mouse (GRCm38) cis-regulatory elements defined from transcription-start activity and class… _[cis-regulatory element, cre, enhancer, promoter, cage, transcription start site]_
- **glycosmos** — GlyCosmos. Integrated glycoscience: glycan structures (GlyTouCan, multi-format WURCS/IUPAC/GlycoCT), glycoproteins with… _[glycan, glycosylation, glycoprotein, saccharide, wurcs, glytoucan]_
- **go** — Gene Ontology. Cross-species controlled vocabulary for gene-product function, organized into three independent domains (biol… _[gene ontology, ontology, biological process, molecular function, cellular component, go term]_
- **gwascatalog** — NHGRI-EBI GWAS Catalog. Genome-wide association study results linking SNPs (rsIDs) to human traits and diseases, with p-values, effec… _[gwas, genome-wide association, snp, variant, polymorphism, trait]_
- **hco** — HCO. The human cytogenetic map: every Giemsa-stained chromosome band (ISCN name, e.g. _[cytoband, chromosome band, karyotype, cytogenetic, giemsa stain, ideogram]_
- **hgnc** — HGNC. Authoritative approved human gene nomenclature: official symbol, full name, HGNC ID, chromosomal band, and a… _[human gene, gene nomenclature, gene symbol, approved gene, gene name, hgnc id]_
- **idsm** — IDSM. Chemical structure search engine (substructure, similarity, exact) over nine integrated small-molecule datase… _[chemical structure, substructure search, similarity search, smiles, molfile, cheminformatics]_
- **jpostdb** — jPOST. Reanalysed mass-spectrometry proteomics submissions: each Project (JPST id) bundles Datasets with experimenta… _[proteomics, mass spectrometry, peptide, psm, peptide spectrum match, protein identification]_
- **lipidmaps** — LIPID MAPS Structure Database. Classified lipid structures with molecular formula, monoisotopic mass, InChI/InChIKey and lipidomics shorthan… _[lipid, lipidomics, fatty acid, glycerophospholipid, sphingolipid, sterol]_
- **marpolbase** — MarpolBase. Genome structural annotation, functional annotation, co-expression, orthogroups and curated gene-literature a… _[plant, liverwort, bryophyte, genome, gene model, genome annotation]_
- **massbank** — MassBank. Open repository of reference MS/MS mass spectra for small molecules (metabolites, drugs, natural products, en… _[mass spectrometry, mass spectra, ms/ms, tandem ms, metabolomics, metabolite]_
- **mco** — MCO. Reference ontology of the mouse (Mus musculus) chromosome set — the 22 chromosomes (1-19, X, Y, MT) as owl:Cl… _[mouse chromosome, mus musculus, karyotype, genome build, grcm38, grcm39]_
- **medgen** — MedGen. NCBI's UMLS-derived registry of ~234k clinical concepts (diseases, phenotypes, findings) with genetic compone… _[medical genetics, disease, phenotype, clinical concept, syndrome, finding]_
- **mediadive** — MediaDive. Standardized microbial growth-media recipes from DSMZ: 3,289 media built from 1,489 ingredients (chemically c… _[culture medium, growth medium, recipe, ingredient, composition, concentration]_
- **mesh** — MeSH RDF. NLM's controlled biomedical thesaurus for PubMed indexing: ~30k topical descriptors on a tree-number hierarch… _[controlled vocabulary, thesaurus, medical subject headings, descriptor, tree number, qualifier]_
- **mogplus** — MoG+. Genome-wide sequence variation (SNVs + small indels, GRCm39) across 62 inbred and wild-derived mouse strains:… _[mouse variant, mouse genome, snv, indel, genotype, inbred strain]_
- **mondo** — MONDO. Unified disease ontology integrating 39+ source vocabularies into one owl:Class hierarchy (~29.9k active dise… _[disease, ontology, disorder, syndrome, rare disease, genetic disease]_
- **nando** — NANDO. Japanese ontology of ~3,000 disease classes under two national programs (designated intractable diseases, spe… _[rare disease, intractable disease, nanbyo, pediatric chronic disease, ontology, disease hierarchy]_
- **nbrc** — NBRC. Catalogue of ~24k microbial strains (bacteria, archaea, fungi, yeasts, algae, phages) distributed by Japan's… _[culture collection, biological resource, microbial strain, nbrc, nite, bacteria]_
- **ncbigene** — NCBI Gene. Gene records for all organisms (57.8M genes): symbol, full name, gene type, chromosome/cytoband, synonyms, no… _[gene, gene symbol, gene type, ncbi, annotation, synonym]_
- **oma** — OMA. Phylogenomic orthology across the tree of life: 17.4M proteins from 2,927 species organized into Hierarchical… _[ortholog, paralog, homolog, gene family, comparative genomics, hierarchical orthologous group]_
- **ontology** — Ontology graphs. Cross-ontology term-resolution and hierarchy-expansion surface hosting ~20 OBO/non-OBO ontologies without the… _[ontology, controlled vocabulary, term resolution, iri resolution, label, synonym]_
- **pdb** — PDB. 3D structural data for biological macromolecules (~255,508 entries) from X-ray crystallography, cryo-EM, and… _[protein structure, 3d structure, x-ray crystallography, cryo-em, nmr, macromolecule]_
- **pubcasefinder** — PubCaseFinder RDF. Rare-disease knowledge base behind the PubCaseFinder diagnosis-support service: OMIM and Orphanet diseases li… _[rare disease, phenotype, hpo, disease-phenotype association, gene-disease association, omim]_
- **pubchem** — PubChem RDF. Chemical compounds + substances with typed molecular descriptors (SMILES, InChI, MW, formula, XLogP3), ontolo… _[compound, chemical, molecule, drug, cid, smiles]_
- **pubmed** — PubMed. 37M+ MEDLINE citations (articles, reviews) with title/abstract, journal + bibliographic metadata, ordered aut… _[publication, article, review, citation, abstract, author]_
- **pubtator** — PubTator Central RDF. Biomedical entity annotations text-mined from PubMed articles — Disease (MeSH) and Gene (NCBI Gene) mentions… _[annotation, text mining, named entity recognition, literature, pubmed, pmid]_
- **reactome** — Reactome Pathway Database. Expert-curated biological pathways and reactions in BioPAX Level 3: hierarchical pathways, biochemical reacti… _[pathway, reaction, biopax, signaling, metabolism, protein]_
- **rhea** — Rhea. Expert-curated, atom-balanced biochemical reactions (18,854 master reactions) with ChEBI-linked participants,… _[biochemical reaction, enzyme, substrate, product, cofactor, ec number]_
- **supercon** — SuperCon. Curated experimental records for oxide and metallic superconductors (NIMS), extracted from ~7,249 journal art… _[superconductor, superconducting material, critical temperature, tc, critical field, cuprate]_
- **swisslipids** — SwissLipids. Expert-curated lipid reference knowledge base of ~778,000 lipids arranged in a six-level classification hiera… _[lipid, lipidomics, fatty acid, glycerophospholipid, sphingolipid, sterol]_
- **taxonomy** — NCBI Taxonomy RDF. Hierarchical biological classification of ~2.84M taxa (species → root) with scientific/common names, synonyms… _[taxonomy, organism, species, taxon, rank, lineage]_
- **togovar** — TogoVar. GRCh38 human genome variants (SNV/Deletion/Insertion/MNV/Indel) with normalized+VCF coordinates, Ensembl-VEP… _[variant, variation, mutation, snv, snp, indel]_
- **uniprot** — UniProt RDF. Curated (Swiss-Prot) and automatic (TrEMBL) protein sequence + functional annotation: sequences, domains, PTM… _[protein, sequence, swiss-prot, trembl, reviewed, function]_
- **wikipathways** — WikiPathways. Community-curated biological pathway diagrams for 39 organisms, exposing pathways, their gene-product/protein… _[pathway, pathway diagram, gene product, metabolite, interaction, signaling]_

**Not an RDF Portal database — KEGG.** `database="kegg"` is invalid on `run_sparql` and `get_MIE_file`: KEGG has no SPARQL endpoint and no MIE. The `kegg_*` tools exist only on a local stdio server whose operator enabled them. **If you see no `kegg_*` tool, KEGG is unavailable in this session** — answer pathway questions from `reactome` or `rhea`, and do NOT report the absence as an error or suggest enabling it. When the tools ARE present, this guide carries a KEGG section with the details.

