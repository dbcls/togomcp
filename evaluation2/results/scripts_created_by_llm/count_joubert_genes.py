#!/usr/bin/env python3
"""
Process ClinVar variant summaries to count pathogenic/likely pathogenic variants by gene
for Joubert syndrome.
"""

import json
from collections import Counter

# Sample data from first batch (50 variants)
# From the first batch of 50 variants, I can identify pathogenic/likely pathogenic variants

def is_pathogenic_or_likely_pathogenic(classification_desc):
    """Check if classification is pathogenic or likely pathogenic."""
    if not classification_desc:
        return False
    desc_lower = classification_desc.lower()
    # Match "pathogenic" or "likely pathogenic" but not "benign" variants
    if 'pathogenic' in desc_lower and 'benign' not in desc_lower:
        return True
    return False

# Manual processing of first 50 variants from esummary call
pathogenic_variants = {
    "4759234": ["TCTN1"],  # Likely pathogenic
    "4755442": ["MALL", "NPHP1"],  # Pathogenic
    "4755428": ["KIAA0586"],  # Pathogenic
    "4755422": ["CPLANE1"],  # Likely pathogenic
    "4753888": ["ARL13B"],  # Likely pathogenic
    "4753715": ["INPP5E"],  # Likely pathogenic
    "4751611": ["AHI1"],  # Likely pathogenic
    "4750374": ["NPHP3-ACAD11", "NPHP3"],  # Likely pathogenic
}

# Count genes
gene_counts = Counter()
for variant_id, genes in pathogenic_variants.items():
    for gene in genes:
        gene_counts[gene] += 1

print("Gene counts from first 50 variants (pathogenic/likely pathogenic only):")
for gene, count in gene_counts.most_common():
    print(f"  {gene}: {count}")
