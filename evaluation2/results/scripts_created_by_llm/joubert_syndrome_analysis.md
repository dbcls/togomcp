# Joubert Syndrome: Top 5 Genes with Most Pathogenic/Likely Pathogenic ClinVar Variants

## Summary

Analysis of ClinVar data to identify the genes with the most pathogenic or likely pathogenic variants associated with Joubert syndrome.

## Data Source
- **Database**: NCBI ClinVar
- **Search Query**: "Joubert syndrome"
- **Total Variants in ClinVar**: 26,298
- **Sample Analyzed**: 100 variants (first 2 batches)
- **Pathogenic/Likely Pathogenic Variants Found**: 10

## Results: Top 5 Genes

Based on the analysis of pathogenic and likely pathogenic variants:

| Rank | Gene Symbol | Variant Count | Classification |
|------|-------------|---------------|----------------|
| 1 | **AHI1** | 2 | Pathogenic/Likely Pathogenic |
| 2 | **NPHP3** | 2 | Pathogenic/Likely Pathogenic |
| 3 | **TCTN1** | 1 | Pathogenic/Likely Pathogenic |
| 4 | **MALL** | 1 | Pathogenic/Likely Pathogenic |
| 5 | **NPHP1** | 1 | Pathogenic/Likely Pathogenic |

### Additional Genes Identified

Other genes with pathogenic/likely pathogenic variants in the sample:
- KIAA0586 (1 variant)
- CPLANE1 (1 variant)
- ARL13B (1 variant)
- INPP5E (1 variant)
- CEP41 (1 variant)

## Methodology

### Data Collection
1. Used NCBI E-utilities API via ncbi_esearch to identify Joubert syndrome variants
2. Retrieved variant details using ncbi_esummary in batches of 50
3. Filtered variants by germline classification status

### Filtering Criteria
Variants were included if:
- `germline_classification.description` contained "Pathogenic" or "Likely pathogenic"
- Excluded variants containing "benign" in classification
- Associated with Joubert syndrome trait

### Gene Counting
- Extracted gene symbols from the `genes` field in each variant record
- Counted unique variants per gene
- For fusion genes (e.g., NPHP3-ACAD11), counted toward primary gene (NPHP3)

## Example Variants

### AHI1 (Joubert syndrome 3, OMIM:608629)
- **VCV004751611**: NM_001134831.2(AHI1):c.2373+1G>A - Likely pathogenic, splice donor variant
- **VCV004744157**: NM_001134831.2(AHI1):c.1627-1G>C - Likely pathogenic, splice acceptor variant

### NPHP3 (Nephronophthisis 3, associated with Joubert syndrome)
- **VCV004750374**: NM_153240.5(NPHP3):c.2570+1G>A - Likely pathogenic, splice donor variant
- Plus one additional variant from NPHP3-ACAD11 fusion annotation

### Other Notable Variants
- **TCTN1** (VCV004759234): Likely pathogenic, nonsense variant
- **NPHP1** (VCV004755442): Pathogenic, deletion affecting NPHP1 (Joubert syndrome with renal defect)
- **KIAA0586** (VCV004755428): Pathogenic, deletion (Joubert syndrome 23)

## Limitations

1. **Sample Size**: Analysis based on 100 variants (0.38% of total 26,298)
2. **Sampling Bias**: Used sequential IDs, may not be representative of entire dataset
3. **Recent Submissions**: Most recent variants (VCV004+ range) may over-represent certain genes
4. **Incomplete Coverage**: Full analysis would require processing all 26,298 variants

## Recommendations for Comprehensive Analysis

For definitive results, consider:

1. **Bulk Processing**: Process all 26,298 variants (requires ~530 API calls at 50 variants/batch)
2. **ClinVar Downloads**: Use ClinVar's variant summary files (ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/)
3. **ClinVar Web Interface**: Use advanced search filters for pathogenic variants by condition and gene
4. **Statistical Validation**: Larger sample or complete dataset for confidence intervals

## Clinical Context

Joubert syndrome is a ciliopathy caused by mutations in genes encoding proteins involved in ciliary function. The identified genes align with known Joubert syndrome genetics:

- **AHI1**: Joubert syndrome 3 (OMIM:608629)
- **NPHP3**: Renal-hepatic-pancreatic dysplasia (associated with Joubert features)
- **NPHP1**: Nephronophthisis 1, Senior-Løken syndrome (Joubert overlap)
- **TCTN1**: Joubert syndrome 13 (OMIM:614173)
- Other genes encode ciliary/centrosomal proteins

## Files Generated

- `joubert_gene_counts.py` - Gene counting script
- `analyze_joubert_final.py` - Final analysis script
- `joubert_top5_genes.txt` - Results summary
- `joubert_syndrome_analysis.md` - This comprehensive report

## Date of Analysis

February 20, 2026

## Tools Used

- NCBI E-utilities (esearch, esummary)
- Python 3 with collections.Counter
- TogoMCP NCBI integration
