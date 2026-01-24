import csv
import argparse

def combine_csvs(input_files, output_file):
    """
    Combines multiple CSV files into a single file.

    Args:
        input_files (list): A list of paths to the input CSV files.
        output_file (str): The path to the output CSV file.
    """
    all_rows = []
    header = None

    for filepath in input_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                try:
                    file_header = next(reader)
                except StopIteration:
                    print(f"Warning: {filepath} is empty. Skipping.")
                    continue
                
                if header is None:
                    header = file_header
                elif header != file_header:
                    print(f"Warning: Header in {filepath} does not match the first file's header. Sticking with the first header.")

                for row in reader:
                    all_rows.append(row)
        except FileNotFoundError:
            print(f"Error: Input file not found: {filepath}. Skipping.")
            continue

    if header is not None and all_rows:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(all_rows)

        print(f"Successfully created {output_file} with {len(all_rows)} data rows")
        if header:
            print(f"Header: {', '.join(header[:5])}...")
    else:
        print("No data found in input files or files were empty/not found. Output file not created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine multiple CSV files into one.")
    parser.add_argument("input_files", nargs='+', help="One or more input CSV files to combine.")
    parser.add_argument("-o", "--output", default="combined_results.csv", help="Name of the output CSV file (default: combined_results.csv)")

    args = parser.parse_args()

    combine_csvs(args.input_files, args.output)