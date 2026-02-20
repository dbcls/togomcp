#!/usr/bin/env python3
"""
Manual analysis of Joubert syndrome pathogenic/likely pathogenic variants.
Based on manual review of ClinVar esummary data batches.
"""

from collections import Counter

# Pathogenic and Likely pathogenic variants identified from manual batch processing
# Format: (variant_id, classification, genes_list)
pathogenic_variants = [
    # Batch 1 (first 50 variants)
    ("4759234", "Likely pathogenic", ["TCTN1"]),
    ("4755442", "Pathogenic", ["MALL", "NPHP1"]),
    ("4755428", "Pathogenic", ["KIAA0586"]),
    ("4755422", "Likely pathogenic", ["CPLANE1"]),
    ("4753888", "Likely pathogenic", ["ARL13B"]),
    ("4753715", "Likely pathogenic", ["INPP5E"]),
    ("4751611", "Likely pathogenic", ["AHI1"]),
    ("4750374", "Likely pathogenic", ["NPHP3-ACAD11", "NPHP3"]),

    # Batch 2 (next 50 variants)
    ("4744157", "Likely pathogenic", ["AHI1"]),
    ("4739999", "Likely pathogenic", ["CEP41"]),
]

# Count variants per gene
gene_counter = Counter()
for vid, classification, genes in pathogenic_variants:
    for gene in genes:
        gene_counter[gene] += 1

print("=" * 70)
print("Joubert Syndrome: Pathogenic/Likely Pathogenic Variants by Gene")
print("=" * 70)
print(f"\nTotal P/LP variants found: {len(pathogenic_variants)}")
print(f"Unique genes: {len(gene_counter)}")
print("\nGene counts (sorted by frequency):\n")

for rank, (gene, count) in enumerate(gene_counter.most_common(), 1):
    print(f"{rank:2d}. {gene:20s} : {count:3d} variant(s)")

print("\n" + "=" * 70)
print("Top 5 genes with most pathogenic/likely pathogenic variants:")
print("=" * 70)
for rank, (gene, count) in enumerate(gene_counter.most_common(5), 1):
    print(f"{rank}. {gene}: {count} variant(s)")

print("\nNote: This analysis is based on a sample of variants.")
print("For comprehensive results, all 26,298 Joubert syndrome variants")
print("would need to be processed.")
