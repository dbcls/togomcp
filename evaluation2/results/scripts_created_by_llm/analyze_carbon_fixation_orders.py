#!/usr/bin/env python3
"""
Analyze carbon fixation proteins by bacterial order.
Fetches lineage info from NCBI and counts reviewed proteins from UniProt.
"""

import requests
import xml.etree.ElementTree as ET
from collections import defaultdict
import time

# All 280 taxonomy IDs
ALL_TAX_IDS = [
    32053, 3544, 279010, 405948, 1111708, 1140, 1392, 167539, 197221, 226900,
    246196, 272631, 301447, 3055, 315749, 3702, 4113, 572477, 632, 83331,
    83332, 83333, 272630, 84588, 4227, 193567, 198466, 1126, 555778, 269084,
    222523, 281309, 288681, 315730, 361100, 405531, 405532, 405534, 405535, 412694,
    568206, 572264, 592021, 272844, 122587, 32051, 32049, 377628, 1122961, 1525,
    167546, 228410, 262316, 316275, 349521, 66692, 74547, 382245, 28502, 400667,
    103690, 220664, 59919, 481805, 550537, 550538, 273123, 300268, 360102, 373384,
    386656, 393305, 399741, 502800, 561230, 208435, 410359, 70601, 78245, 281310,
    502801, 340102, 419942, 426118, 427317, 427318, 429572, 1016998, 196600, 264730,
    314565, 349747, 65093, 167542, 266265, 203123, 330779, 347834, 384616, 393595,
    444450, 316273, 381754, 351348, 507522, 575788, 595496, 76869, 100226, 122586,
    160488, 170187, 171101, 178306, 186497, 187420, 188937, 190192, 190485, 190650,
    195103, 196627, 199310, 203120, 208964, 210007, 211586, 224325, 224911, 235909,
    242231, 243160, 243232, 243265, 243277, 251221, 257313, 262543, 264199, 269796,
    272560, 272843, 272943, 273057, 290338, 290398, 291331, 298386, 300267, 300269,
    300852, 312309, 315750, 323259, 324602, 326423, 331111, 344609, 368408, 373153,
    380703, 3847, 388919, 399742, 405955, 4097, 41514, 4558, 4577, 465817,
    467705, 529507, 574521, 585035, 585054, 585055, 623, 64091, 69014, 71421,
    83334, 90370, 99287, 196164, 243365, 247156, 272621, 316058, 418699, 595494,
    257309, 379731, 3888, 397948, 449447, 523850, 227882, 267608, 323850, 357804,
    398579, 425104, 4226, 160491, 186103, 195102, 205921, 211110, 286636, 289380,
    299768, 322159, 391295, 391296, 405566, 331112, 1183438, 375451, 3885, 458817,
    273063, 383372, 391735, 634503, 416269, 476213, 52271, 218491, 290340, 29466,
    399549, 438753, 65393, 223283, 326442, 1718, 3879, 374931, 3037, 29549,
    362242, 295319, 316385, 321314, 362663, 364106, 384676, 399739, 423368, 439843,
    439851, 439855, 454169, 554290, 585034, 585057, 585397, 258594, 390333, 76114,
    439386, 311403, 223926, 205918, 205922, 317025, 351746, 243243, 15819, 190486,
    342109, 400668, 272831, 585056, 192952, 269797, 478009, 216895, 388396, 146891,
    240292, 74546, 93060, 2950, 320389, 374930, 3329, 320373, 62977, 205914,
    228400, 2333, 262724, 72595, 409438, 257310, 257311, 269482, 320388, 335283,
    412022, 420246, 471223, 316055, 316056, 316057, 41911, 115852, 194439, 280810
]

# Target orders
TARGET_ORDERS = {
    'Enterobacterales': 91347,
    'Synechococcales': 1890424,
    'Chloroflexales': 32064,
    'Burkholderiales': 80840,
    'Hyphomicrobiales': 356
}

def fetch_taxonomy_lineage_batch(tax_ids, batch_size=200):
    """Fetch taxonomy lineage from NCBI in batches."""
    all_lineages = {}

    for i in range(0, len(tax_ids), batch_size):
        batch = tax_ids[i:i+batch_size]
        ids_str = ','.join(map(str, batch))

        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        params = {
            'db': 'taxonomy',
            'id': ids_str,
            'retmode': 'xml'
        }

        print(f"Fetching batch {i//batch_size + 1} ({len(batch)} IDs)...")

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            for taxon in root.findall('.//Taxon'):
                tax_id_elem = taxon.find('TaxId')
                if tax_id_elem is None:
                    continue

                tax_id = int(tax_id_elem.text)

                # Extract order from LineageEx
                lineage_ex = taxon.find('LineageEx')
                order_name = None
                order_taxid = None

                if lineage_ex is not None:
                    for lineage_taxon in lineage_ex.findall('Taxon'):
                        rank_elem = lineage_taxon.find('Rank')
                        if rank_elem is not None and rank_elem.text == 'order':
                            order_name = lineage_taxon.find('ScientificName').text
                            order_taxid = int(lineage_taxon.find('TaxId').text)
                            break

                all_lineages[tax_id] = {
                    'order_name': order_name,
                    'order_taxid': order_taxid
                }

            time.sleep(0.5)  # Be nice to NCBI servers

        except Exception as e:
            print(f"Error fetching batch: {e}")
            continue

    return all_lineages

def count_uniprot_proteins_for_organisms(organism_ids, go_term='GO:0015977'):
    """
    Query UniProt for reviewed proteins with GO term for multiple organisms.
    Queries each organism individually and collects unique protein accessions.
    Returns total unique protein count across all organisms.
    """
    url = 'https://rest.uniprot.org/uniprotkb/search'

    unique_proteins = set()
    failed_organisms = []

    for org_id in organism_ids:
        # Remove GO: prefix if present
        go_id = go_term.replace('GO:', '')
        query = f'reviewed:true AND go:{go_id} AND organism_id:{org_id}'

        params = {
            'query': query,
            'format': 'list',  # Get list of accessions
            'size': 500  # Max per query
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()

            # Parse accessions from response
            text = response.text.strip()
            if text:  # Only process if there's content
                accessions = text.split('\n')
                for acc in accessions:
                    acc = acc.strip()
                    if acc:  # Skip empty lines
                        unique_proteins.add(acc)

            time.sleep(0.15)  # Be nice to the API

        except Exception as e:
            print(f"    Error querying organism {org_id}: {e}")
            failed_organisms.append(org_id)
            continue

    if failed_organisms and len(failed_organisms) < len(organism_ids):
        print(f"    Warning: Failed to query {len(failed_organisms)}/{len(organism_ids)} organisms")

    return len(unique_proteins)

def main():
    print("="*80)
    print("ANALYZING CARBON FIXATION PROTEINS BY BACTERIAL ORDER")
    print("="*80)
    print()

    # Step 1: Fetch lineage for all organisms
    print(f"Step 1: Fetching lineage information for {len(ALL_TAX_IDS)} organisms...")
    lineages = fetch_taxonomy_lineage_batch(ALL_TAX_IDS)
    print(f"Successfully retrieved lineage for {len(lineages)} organisms")
    print()

    # Step 2: Group organisms by target orders
    print("Step 2: Grouping organisms by target orders...")
    order_counts = defaultdict(list)
    unmatched = []

    for tax_id, lineage in lineages.items():
        order_taxid = lineage['order_taxid']
        order_name = lineage['order_name']

        if order_taxid in TARGET_ORDERS.values():
            # Find the order name from our target dict
            for name, tid in TARGET_ORDERS.items():
                if tid == order_taxid:
                    order_counts[name].append(tax_id)
                    break
        else:
            unmatched.append((tax_id, order_name))

    print(f"Matched {sum(len(v) for v in order_counts.values())} organisms to target orders")
    print(f"Unmatched: {len(unmatched)} organisms")
    print()

    # Step 3: Display organism counts per order
    print("Step 3: Organism counts per order:")
    print("-" * 80)
    for order_name in sorted(TARGET_ORDERS.keys()):
        count = len(order_counts[order_name])
        print(f"{order_name:30s} (taxid: {TARGET_ORDERS[order_name]:7d}): {count:3d} organisms")
    print("-" * 80)
    print()

    # Step 4: Query UniProt for reviewed protein counts
    print("Step 4: Querying UniProt for reviewed protein counts...")
    print("-" * 80)

    results = {}
    for order_name in sorted(TARGET_ORDERS.keys()):
        order_taxid = TARGET_ORDERS[order_name]
        organism_list = order_counts[order_name]
        print(f"Querying {order_name} (taxid: {order_taxid}, {len(organism_list)} organisms)...", end=' ')

        if len(organism_list) == 0:
            print("No organisms to query")
            results[order_name] = {
                'taxid': order_taxid,
                'organism_count': 0,
                'protein_count': 0
            }
            continue

        protein_count = count_uniprot_proteins_for_organisms(organism_list)
        results[order_name] = {
            'taxid': order_taxid,
            'organism_count': len(organism_list),
            'protein_count': protein_count
        }

        if protein_count is not None:
            print(f"{protein_count} proteins")
        else:
            print("Failed to retrieve count")

        time.sleep(0.5)  # Be nice to UniProt servers

    print("-" * 80)
    print()

    # Step 5: Display final results
    print("="*80)
    print("FINAL RESULTS: Carbon Fixation Proteins (GO:0015977) by Order")
    print("="*80)
    print()
    print(f"{'Order':<30s} {'Tax ID':>10s} {'Organisms':>12s} {'Reviewed Proteins':>20s}")
    print("-" * 80)

    total_organisms = 0
    total_proteins = 0

    for order_name in sorted(TARGET_ORDERS.keys()):
        res = results[order_name]
        total_organisms += res['organism_count']
        if res['protein_count'] is not None:
            total_proteins += res['protein_count']
            protein_str = str(res['protein_count'])
        else:
            protein_str = "N/A"

        print(f"{order_name:<30s} {res['taxid']:>10d} {res['organism_count']:>12d} {protein_str:>20s}")

    print("-" * 80)
    print(f"{'TOTAL':<30s} {'':<10s} {total_organisms:>12d} {total_proteins:>20d}")
    print("="*80)
    print()

    # Show some unmatched organisms for reference
    if unmatched:
        print("Sample of unmatched organisms (first 10):")
        print("-" * 80)
        for tax_id, order_name in unmatched[:10]:
            print(f"  TaxID {tax_id}: {order_name}")
        print(f"... and {len(unmatched) - 10} more")
        print()

if __name__ == '__main__':
    main()
