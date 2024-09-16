#!/usr/bin/env python3

import csv
import pickle
import os

# Load cache from the specified cache file
def load_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}

# Write cache to CSV
def cache_to_csv(output_file, cache_file):
    cache = load_cache(cache_file)
    if not cache:
        print("Cache is empty. No data to export.")
        return

    # Write the sorted businesses to a CSV file
    print(f"Writing data to CSV file: {output_file}")
    businesses = []
    for k in cache.keys():
        businesses.append(cache[k])
    with open(output_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['name', 'address', 'phone', 'email', 'website', 'hours'])
        writer.writeheader()
        writer.writerows(businesses)

    print(f"Cache data written to {output_file} successfully!")

# Main function to handle arguments
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export cached business data to a CSV file.")
    parser.add_argument('--output', '-o', type=str, help='Output CSV file (default: {business_type}_list.csv)')
    parser.add_argument('--business-type', '-t', type=str, default='restaurant', 
                        help='Type of business for the cache file (default: restaurant)')

    args = parser.parse_args()

    # Generate the cache file name and output CSV file name based on the business type
    cache_file = f"places_cache.pkl.{args.business_type}"
    output_file = args.output if args.output else f"{args.business_type}_list.csv"

    cache_to_csv(output_file, cache_file)

if __name__ == '__main__':
    main()
