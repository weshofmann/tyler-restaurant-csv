#!/usr/bin/env python3

import csv
import pickle
import os

CACHE_FILE = "places_cache.pkl"  # File to store cached place details

# Load cache
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

# Write cache to CSV
def cache_to_csv(output_file):
    cache = load_cache()
    if not cache:
        print("Cache is empty. No data to export.")
        return

    # Write the sorted restaurants to a CSV file
    print(f"Writing data to CSV file: {output_file}")
    restaurants = []
    for k in cache.keys():
        restaurants.append(cache[k])
    with open(output_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['name', 'address', 'phone', 'email', 'website', 'hours'])
        writer.writeheader()
        writer.writerows(restaurants)

    print(f"Cache data written to {output_file} successfully!")

# Main function to handle arguments
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export cached restaurant data to a CSV file.")
    parser.add_argument('--output', '-o', type=str, default='restaurants_google.csv',
                        help='Output CSV file (default: restaurants_google.csv)')

    args = parser.parse_args()
    cache_to_csv(args.output)

if __name__ == '__main__':
    main()
