#!/usr/bin/env python3

import requests
import re
import csv
import argparse
import time
import os
import pickle
from math import radians, cos, sin, sqrt, atan2, degrees
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, urljoin

SLEEP_TIME_SECS = 0.5
DEFAULT_CENTER = 'Mustang, OK'
CACHE_FILE = "places_cache.pkl"  # File to store cached place details
EARTH_RADIUS_KM = 6371  # Approximate radius of Earth in kilometers

# List of fast-food chains to exclude
FAST_FOOD_CHAINS = [
  "mcdonald", 
  "mcdonalds", 
  "mcdonald's", 
  "kfc", 
  "taco bell", 
  "burger king", 
  "wendys", 
  "wendy's", 
  "subway", 
  "domino", 
  "domino's", 
  "pizzahut", 
  "pizza hut",
  "chipotle",
  "whataburger",
  "arbys",
  "arby's",
  "sonic drive-in",
  "papa murphys",
  "papa murphy's",
  "starbucks",
  "braums",
  "braum's",
  "chicken express",
  "freddy's frozen custard",
  "city bites",
  "little ceasar's pizza",
  "taco bueno",
  "schlotzsky's",
  "schlotzskys",
]

# Initialize or load cache
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

# Google Geocoding API to convert an address into lat/long
def get_lat_lng(address, api_key):
    geocode_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': address,
        'key': api_key
    }
    print(f"Geocoding address '{address}'...")
    response = requests.get(geocode_url, params=params)
    time.sleep(SLEEP_TIME_SECS)
    data = response.json()
    if 'error_message' in data:
        print(f"Error in Geocoding API: {data['error_message']}")
        return None
    if data['results']:
        location = data['results'][0]['geometry']['location']
        print(f"Geocoding successful! Location: {location['lat']}, {location['lng']}")
        return location['lat'], location['lng']
    return None

# Function to calculate new lat/lng from a given bearing angle and distance
def move_center(lat, lng, distance_km, bearing_angle):
    # Convert latitude, longitude, and angle to radians
    lat_rad = radians(lat)
    lng_rad = radians(lng)
    bearing_rad = radians(bearing_angle)

    # Calculate the new latitude and longitude
    new_lat = sin(lat_rad) * cos(distance_km / EARTH_RADIUS_KM) + \
              cos(lat_rad) * sin(distance_km / EARTH_RADIUS_KM) * cos(bearing_rad)
    new_lat = degrees(atan2(new_lat, sqrt(1 - new_lat ** 2)))  # Convert back to degrees

    new_lng = lng_rad + atan2(sin(bearing_rad) * sin(distance_km / EARTH_RADIUS_KM) * cos(lat_rad),
                              cos(distance_km / EARTH_RADIUS_KM) - sin(lat_rad) * sin(new_lat))
    new_lng = degrees(new_lng)  # Convert back to degrees

    print(f"Moving center to new lat/lng: {new_lat}, {new_lng} based on bearing {bearing_angle}° and distance {distance_km} km")
    return new_lat, new_lng

# Function to get restaurants from Google Places API (ranked by distance) with support for multiple batches
def get_restaurants(location, api_key, num_results, batch_size=60, radius_increment=1000):
    all_restaurants = []
    visited_place_ids = set()
    radius = 1000  # Initial radius in meters
    batch_count = 0
    lat_offset = 0.005  # Adjust this for latitude shifts between batches
    lng_offset = 0.005  # Adjust this for longitude shifts between batches
    lat, lng = location

    while len(all_restaurants) < num_results:
        print(f"Fetching batch {batch_count + 1}...")
        
        # Adjust the location slightly to search in a new area
        lat += lat_offset
        lng += lng_offset
        new_location = (lat, lng)

        # Fetch restaurants for the new location
        restaurants = fetch_restaurants_in_radius(new_location, api_key, radius, batch_size)
        if not restaurants:
            print(f"No more restaurants found in radius: {radius} meters.")
            break

        # Filter out fast-food chains by name
        filtered_restaurants = [r for r in restaurants if not any(chain.lower() in r['name'].lower() for chain in FAST_FOOD_CHAINS)]

        # Filter out duplicates by checking place_id
        new_restaurants = [r for r in filtered_restaurants if r['place_id'] not in visited_place_ids]
        
        # Track visited places to avoid duplicates
        visited_place_ids.update(r['place_id'] for r in new_restaurants)
        
        # Add unique new restaurants to the final list
        all_restaurants.extend(new_restaurants)
        
        print(f"Retrieved {len(all_restaurants)} unique restaurants so far.")
        
        if len(new_restaurants) < batch_size:
            # Increase the radius to cover a larger area if we're not getting enough results
            radius += radius_increment
        batch_count += 1

        # Stop if we have enough restaurants
        if len(all_restaurants) >= num_results:
            break
    
    return all_restaurants[:num_results]

# Helper function to fetch restaurants within a specified radius
def fetch_restaurants_in_radius(location, api_key, radius, num_results):
    restaurants = []
    url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'

    params = {
        'location': f"{location[0]},{location[1]}",  # Latitude, Longitude
        'radius': radius,  # Use radius instead of rankby=distance for finer control
        'type': 'restaurant',
        'key': api_key
    }

    while len(restaurants) < num_results:
        response = requests.get(url, params=params)
        time.sleep(SLEEP_TIME_SECS)
        data = response.json()

        if 'error_message' in data:
            print(f"Error in Nearby Search API response: {data['error_message']}")
            break

        restaurants.extend(data.get('results', []))

        next_page_token = data.get('next_page_token')
        if next_page_token and len(restaurants) < num_results:
            params['pagetoken'] = next_page_token
            time.sleep(2)  # Required delay for pagination
        else:
            break

    return restaurants

# Function to get detailed information for each restaurant (with caching and response debugging)
def get_place_details(cache, place_id, api_key, index, total):
    # Check if the place is already cached
    if place_id in cache:
        print(f"[{index}/{total}] Using cached details for place_id: {place_id} ({cache[place_id]['name']})")
        return cache[place_id]

    # If not cached, fetch from the API
    print(f"[{index}/{total}] Fetching details from Google for place_id: {place_id}...")
    details_url = 'https://maps.googleapis.com/maps/api/place/details/json'
    details_params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,formatted_phone_number,website,opening_hours,vicinity,geometry',
        'key': api_key
    }

    details_response = requests.get(details_url, params=details_params)
    time.sleep(SLEEP_TIME_SECS)
    details_data = details_response.json()

    if 'result' in details_data:
        result = details_data['result']
        name = result.get('name', 'N/A')
        address = result.get('formatted_address', 'N/A')
        phone = result.get('formatted_phone_number', 'N/A')
        website = result.get('website', 'N/A')

        # Try to extract email from the website if available
        if website != 'N/A':
            emails = extract_emails_from_website(website)
            email = emails[0] if emails else 'N/A'
        else:
            email = 'N/A'

        # Convert hours to string for storage
        hours_list = result.get('opening_hours', {}).get('weekday_text', [])
        hours = '; '.join(hours_list) if hours_list else 'N/A'

        # Cache the place details including email
        cache[place_id] = {
            'name': name,
            'address': address,
            'phone': phone,
            'email': email,
            'website': website,
            'hours': hours
        }

        return cache[place_id]
    else:
        print(f"Error: No result found for place_id: {place_id}")
        return {'name': 'N/A', 'address': 'N/A', 'phone': 'N/A', 'email': 'N/A', 'website': 'N/A', 'hours': 'N/A'}

# Function to extract email addresses from a website
# (Same as before)
def extract_emails_from_website(url):
    # Regular expression to find email addresses (more strict)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'

    # List of common prefixes to prioritize
    priority_prefixes = ['info', 'contact', 'support', 'help', 'sales', 'admin']

    # Strip URL parameters
    parsed_url = urlparse(url)
    clean_url = urljoin(url, parsed_url.path)  # Remove any query params or fragments

    print(f"Visiting {clean_url} to extract emails...")

    try:
        # Get the website content
        response = requests.get(clean_url, timeout=10)
        time.sleep(SLEEP_TIME_SECS)

        if response.status_code == 200:
            # Parse the content with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Search for email addresses using regex
            emails = re.findall(email_pattern, soup.get_text())

            # Check for "Contact Us" links and follow them
            contact_links = find_contact_links(soup, clean_url)
            if contact_links:
                for link in contact_links:
                    # Handle mailto links directly
                    if link.startswith('mailto:'):
                        email = link.replace('mailto:', '').strip()
                        print(f"Found mailto link with email: {email}")
                        emails.append(email)
                    else:
                        print(f"Following contact link: {link}")
                        emails += extract_emails_from_contact_page(link)

            # Remove duplicates and clean up emails
            emails = list(set(emails))
            emails = [email.strip() for email in emails if validate_email(email)]

            # Prioritize common contact/help emails
            prioritized_emails = prioritize_emails(emails, priority_prefixes)

            return prioritized_emails
        else:
            print(f"Failed to retrieve {clean_url} (status code: {response.status_code})")
            return []
    except requests.RequestException as e:
        print(f"Error fetching {clean_url}: {e}")
        return []

def find_contact_links(soup, base_url):
    """Find possible contact-related links on the page."""
    contact_links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Handle mailto links directly by adding them to the list
        if href.lower().startswith('mailto:'):
            contact_links.append(href)
        elif any(keyword in href.lower() for keyword in ['contact', 'about', 'support', 'help']):
            full_url = urljoin(base_url, href)  # Handle relative URLs
            contact_links.append(full_url)
    return contact_links

def prioritize_emails(emails, priority_prefixes):
    """Reorder emails, prioritizing those that start with common prefixes like 'info', 'contact', etc."""
    prioritized = []
    others = []
    
    for email in emails:
        local_part = email.split('@')[0].lower()  # Get the part before the '@'
        if any(local_part.startswith(prefix) for prefix in priority_prefixes):
            prioritized.append(email)
        else:
            others.append(email)
    
    # Return prioritized emails first, followed by others
    return prioritized + others

def validate_email(email):
    """Validate if the extracted text is a plausible email address."""
    return email and '@' in email and not any(keyword in email.lower() for keyword in ['powered', 'email', 'address'])

def extract_emails_from_contact_page(contact_url):
    """Visit a contact-related page and attempt to extract emails."""
    print(f"Extracting emails from contact page: {contact_url}")
    try:
        response = requests.get(contact_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, soup.get_text())
            return emails
        else:
            print(f"Failed to retrieve contact page {contact_url} (status code: {response.status_code})")
            return []
    except requests.RequestException as e:
        print(f"Error fetching contact page {contact_url}: {e}")
        return []

# Main function to handle argument parsing and CSV writing
def main():
    # Example usages to be displayed in the help message
    example_text = '''\
Example usage:

  # Using the environment variable for the API key:
  export GOOGLE_API_KEY=your_google_api_key_here
  ./find-restaurants.py

  # Using the command-line API key option:
  ./find-restaurants.py --api-key your_google_api_key_here
'''

    # Set up argument parsing for the various options, including custom examples in the epilog
    parser = argparse.ArgumentParser(
        description="Retrieve restaurants using Google Places API.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=example_text
    )
    parser.add_argument('--search-center', '-c', type=str, default=DEFAULT_CENTER,
                        help='The center of the search (address or city) (default: Mustang, OK)')
    parser.add_argument('--distance', '-d', type=float, default=0.5,
                        help='Distance in kilometers to move the center per batch (default: 0.5 km)')
    parser.add_argument('--number', '-n', type=int, default=20,
                        help='Number of restaurants to retrieve (default: 20)')
    parser.add_argument('--bearing', '-b', type=float, default=45,
                        help='Bearing angle in degrees from North to move the search center (default: 45 degrees)')
    parser.add_argument('--output', '-o', type=str, default='restaurants_google.csv',
                        help='Output CSV file (default: restaurants_google.csv)')
    parser.add_argument('--api-key', '-a', type=str,
                        help='Google API Key. If not provided, the environment variable GOOGLE_API_KEY will be used.')
    args = parser.parse_args()

    # Check if the API key is provided via the command line or environment variable
    api_key = args.api_key or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: Google API key not provided. Please set the environment variable GOOGLE_API_KEY or use the --api-key flag.")
        return

    # Load the cache
    cache = load_cache()

    # Geocode the search center to get latitude and longitude
    search_center = args.search_center
    location = get_lat_lng(search_center, api_key)
    if not location:
        print(f"Error: Unable to geocode location: {search_center}")
        return

    # Get the list of restaurants (handling pagination)
    restaurants = get_restaurants(location, api_key, args.number, args.distance, args.bearing)

    # Calculate distance and get details for each restaurant
    detailed_restaurants = []
    total_restaurants = len(restaurants)
    for index, place in enumerate(restaurants, start=1):
        place_id = place.get('place_id')

        # Get the detailed info (with caching and response debugging)
        details = get_place_details(cache, place_id, api_key, index, total_restaurants)

        detailed_restaurants.append(details)

    # Write the sorted restaurants to a CSV file
    print(f"Writing data to CSV file: {args.output}")
    with open(args.output, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['name', 'address', 'phone', 'email', 'website', 'hours'])
        writer.writeheader()
        writer.writerows(detailed_restaurants)

    # Save the updated cache
    save_cache(cache)

    print(f"CSV file '{args.output}' created successfully!")

if __name__ == '__main__':
    main()
