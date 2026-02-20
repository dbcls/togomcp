#!/usr/bin/env python3
"""
Analyze ClinVar variants for Joubert syndrome to find top 5 genes
with most pathogenic/likely pathogenic variants.
"""

import json
from collections import Counter
from typing import Dict, List

# Import MCP client functions
import sys
sys.path.append('/Users/arkinjo/work/GitHub/togo-mcp/evaluation2')

def filter_pathogenic_variants(summary_data: Dict) -> List[tuple]:
    """
    Filter variants that are pathogenic or likely pathogenic.
    Returns list of (variant_id, gene_symbols, classification) tuples.
    """
    pathogenic_variants = []

    for uid in summary_data.get('uids', []):
        variant_data = summary_data.get(uid, {})

        # Check germline classification
        germline = variant_data.get('germline_classification', {})
        classification = germline.get('description', '').lower()

        # Filter for pathogenic or likely pathogenic
        if 'pathogenic' in classification and 'likely pathogenic' not in classification:
            is_pathogenic = True
        elif 'likely pathogenic' in classification:
            is_pathogenic = True
        else:
            is_pathogenic = False

        if is_pathogenic:
            # Extract gene symbols
            genes = variant_data.get('genes', [])
            gene_symbols = [g.get('symbol') for g in genes if g.get('symbol')]

            if gene_symbols:
                pathogenic_variants.append((uid, gene_symbols, classification))

    return pathogenic_variants

def count_genes(pathogenic_variants: List[tuple]) -> Counter:
    """Count variants per gene."""
    gene_counter = Counter()

    for uid, gene_symbols, classification in pathogenic_variants:
        for gene in gene_symbols:
            gene_counter[gene] += 1

    return gene_counter

def main():
    """Main analysis function."""
    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def run_analysis():
        # We'll collect results from multiple batches
        all_gene_counts = Counter()
        total_pathogenic = 0
        batch_size = 100
        max_results = 2000  # Process first 2000 to get good coverage

        print(f"Searching ClinVar for Joubert syndrome variants...")
        print(f"Will process up to {max_results} variants in batches of {batch_size}")
        print()

        # Since we can't make MCP calls directly from script,
        # we'll use the manual approach with saved data
        # This script serves as documentation of the analysis approach

        print("Note: This script documents the analysis approach.")
        print("The actual analysis is performed via MCP tools in the Claude session.")

    asyncio.run(run_analysis())

if __name__ == "__main__":
    main()
