# Carbon Fixation Protein Analysis by Bacterial Order

## Summary

This analysis determined which bacterial orders the 280 unique organism taxonomy IDs (from UniProt with carbon fixation proteins GO:0015977) belong to, and counted the total number of reviewed proteins for 5 target bacterial orders.

## Methodology

1. **Taxonomy Lineage Extraction**: Used NCBI E-utilities (efetch) to retrieve full taxonomic lineage information for all 280 organism IDs in batches
2. **Order Classification**: Parsed the LineageEx XML to identify the order (rank="order") for each organism
3. **Organism Grouping**: Matched organisms to the 5 target orders:
   - Enterobacterales (taxid: 91347)
   - Synechococcales (taxid: 1890424)
   - Chloroflexales (taxid: 32064)
   - Burkholderiales (taxid: 80840)
   - Hyphomicrobiales (taxid: 356)
4. **Protein Counting**: Queried UniProt REST API for each organism individually to count unique reviewed proteins with GO:0015977 annotation

## Results

### Organisms per Order

Out of 280 total taxonomy IDs, **98 organisms** (35%) belong to the 5 target orders:

| Order | Taxonomy ID | Number of Organisms |
|-------|-------------|---------------------|
| Enterobacterales | 91347 | 59 |
| Synechococcales | 1890424 | 13 |
| Burkholderiales | 80840 | 13 |
| Hyphomicrobiales | 356 | 11 |
| Chloroflexales | 32064 | 2 |
| **TOTAL** | | **98** |

### Reviewed Proteins with Carbon Fixation Activity (GO:0015977)

Total unique reviewed proteins across all 5 orders: **205 proteins**

| Order | Taxonomy ID | Organisms | Reviewed Proteins |
|-------|-------------|-----------|-------------------|
| **Synechococcales** | 1890424 | 13 | **90** |
| **Enterobacterales** | 91347 | 59 | **59** |
| **Hyphomicrobiales** | 356 | 11 | **32** |
| **Burkholderiales** | 80840 | 13 | **15** |
| **Chloroflexales** | 32064 | 2 | **9** |
| **TOTAL** | | **98** | **205** |

## Key Findings

1. **Synechococcales** has the highest number of reviewed carbon fixation proteins (90), despite having only 13 organisms in the dataset. This reflects the importance of photosynthetic cyanobacteria in carbon fixation.

2. **Enterobacterales** has the most organisms (59) in the dataset, with 59 unique reviewed proteins - approximately 1 protein per organism on average.

3. **Hyphomicrobiales** shows a high protein-to-organism ratio (32 proteins from 11 organisms), suggesting diverse carbon fixation mechanisms within this order.

4. **Chloroflexales** has the fewest organisms (2) but still contributes 9 unique proteins, showing significant representation per organism.

5. The remaining 182 organisms (65%) belong to other orders not analyzed in this study, including:
   - Thermostichales
   - Bacillales
   - Lactobacillales
   - Alteromonadales
   - Plant orders (Caryophyllales, Brassicales, Asterales, etc.)
   - And many others

## Data Source

- **NCBI Taxonomy Database**: Used for lineage information (efetch API)
- **UniProt**: Used for reviewed protein counts with GO:0015977 annotation
- **GO Term**: GO:0015977 (carbon fixation)
- **Analysis Date**: February 20, 2026

## Script Location

Analysis script: `/Users/arkinjo/work/GitHub/togo-mcp/evaluation2/scripts/analyze_carbon_fixation_orders.py`
