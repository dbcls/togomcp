#!/usr/bin/env python3
"""
Improved combine_csv.py - handles different column sets gracefully

Save this as combine_csv_v2.py or use it to replace combine_csv.py
"""

import csv
import argparse
from pathlib import Path


def combine_csvs(input_files, output_file, verbose=True):
    """
    Combines multiple CSV files into a single file.
    
    Handles CSV files with different column sets by using DictReader/DictWriter
    to ensure all columns from all files are preserved.

    Args:
        input_files (list): A list of paths to the input CSV files.
        output_file (str): The path to the output CSV file.
        verbose (bool): Print progress information.
    """
    all_rows = []
    all_fieldnames = set()
    first_header = None

    # First pass: collect all fieldnames and validate files
    for filepath in input_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if reader.fieldnames is None:
                    print(f"Warning: {filepath} is empty or has no header. Skipping.")
                    continue
                
                if first_header is None:
                    first_header = reader.fieldnames
                
                # Collect all unique fieldnames
                all_fieldnames.update(reader.fieldnames)
                
                if verbose:
                    print(f"Reading {filepath}: {len(reader.fieldnames)} columns")
                    
        except FileNotFoundError:
            print(f"Error: Input file not found: {filepath}. Skipping.")
            continue
        except Exception as e:
            print(f"Error reading {filepath}: {e}. Skipping.")
            continue

    if not all_fieldnames:
        print("No valid data found in input files. Output file not created.")
        return

    # Convert to list and sort to maintain consistent order
    # Put standard fields first, then alphabetically sort the rest
    standard_fields = [
        "question_id", "date", "category", "question_text",
        "baseline_success", "baseline_actually_answered", "baseline_has_expected",
        "baseline_confidence", "baseline_text", "baseline_error", "baseline_error_type", "baseline_time",
        "baseline_input_tokens", "baseline_output_tokens",
        "togomcp_success", "togomcp_has_expected", "togomcp_confidence",
        "togomcp_text", "togomcp_error", "togomcp_error_type", "togomcp_suggestion", "togomcp_time",
        "togomcp_input_tokens", "togomcp_output_tokens",
        "togomcp_cache_creation_input_tokens", "togomcp_cache_read_input_tokens",
        "tools_used", "tool_details",
        "value_add", "expected_answer", "notes"
    ]
    
    # Add LLM evaluation fields if they exist
    llm_fields = [
        "baseline_llm_match", "baseline_llm_confidence", "baseline_llm_explanation",
        "togomcp_llm_match", "togomcp_llm_confidence", "togomcp_llm_explanation",
        "full_combined_baseline_found", "full_combined_togomcp_found"
    ]
    
    # Order: standard fields first, then LLM fields, then any extras alphabetically
    ordered_fieldnames = []
    for field in standard_fields:
        if field in all_fieldnames:
            ordered_fieldnames.append(field)
            all_fieldnames.discard(field)
    
    for field in llm_fields:
        if field in all_fieldnames:
            ordered_fieldnames.append(field)
            all_fieldnames.discard(field)
    
    # Add any remaining fields alphabetically
    ordered_fieldnames.extend(sorted(all_fieldnames))
    
    if verbose:
        print(f"\nCombined fieldnames ({len(ordered_fieldnames)} total):")
        if len(ordered_fieldnames) <= 10:
            for field in ordered_fieldnames:
                print(f"  - {field}")
        else:
            for field in ordered_fieldnames[:5]:
                print(f"  - {field}")
            print(f"  ... and {len(ordered_fieldnames) - 5} more")

    # Second pass: read all data
    error_count = 0
    file_row_counts = {}
    
    for filepath in input_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if reader.fieldnames is None:
                    continue
                
                file_rows = 0
                for row in reader:
                    # Fill in missing fields with empty strings
                    complete_row = {field: row.get(field, '') for field in ordered_fieldnames}
                    all_rows.append(complete_row)
                    file_rows += 1
                
                file_row_counts[Path(filepath).name] = file_rows
                
                if verbose:
                    print(f"Loaded {file_rows} rows from {Path(filepath).name}")
                    
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            error_count += 1
            continue

    # Write combined output
    if all_rows:
        try:
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=ordered_fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)

            print(f"\n✓ Successfully created {output_file}")
            print(f"  Total rows: {len(all_rows)}")
            print(f"  Columns:    {len(ordered_fieldnames)}")
            
            if verbose and len(file_row_counts) > 1:
                print(f"\n  Rows per file:")
                for filename, count in file_row_counts.items():
                    print(f"    - {filename}: {count}")
            
            if error_count > 0:
                print(f"\n  ⚠ Encountered {error_count} file errors (see warnings above)")
                
        except Exception as e:
            print(f"Error writing output file: {e}")
            return
    else:
        print("No data rows found. Output file not created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine multiple CSV files into one, handling different column sets gracefully."
    )
    parser.add_argument(
        "input_files",
        nargs='+',
        help="One or more input CSV files to combine."
    )
    parser.add_argument(
        "-o", "--output",
        default="combined_results.csv",
        help="Name of the output CSV file (default: combined_results.csv)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    combine_csvs(args.input_files, args.output, verbose=not args.quiet)