#!/usr/bin/env python3

import requests
import re
import csv
import argparse
import time
import os
import pickle
import asyncio
import aiohttp
import tldextract

from math import radians, cos, sin, sqrt, atan2, degrees
from bs4 import BeautifulSoup
from urllib.parse import urldefrag, urlparse, urlunparse, urljoin, unquote, quote
from aiolimiter import AsyncLimiter

DEBUG = False

DEFAULT_CENTER        = 'Oklahoma City, OK'
DEFAULT_BEARING       = 180  # degrees  (North = 0, East = 90, South = 180, West = 270)
DEFAULT_DISTANCE      = 2.5  # km
DEFAULT_SEARCH_RADIUS = 5    # km
DEFAULT_BUSINESS_TYPE = "restaurant"
DEFAULT_CACHE_FILE = "places_cache.pkl"  # File to store cached place details

SLEEP_TIME_SECS = 0.25
EARTH_RADIUS_KM = 6371  # Approximate radius of Earth in kilometers

EMAIL_REGEX = re.compile(
    r'''
    (?i)                           # Case-insensitive matching
    (?<![\w\.-])                   # Negative lookbehind
    (                              # Start of capturing group
        [a-z0-9]+                  # Alphanumeric start in local part
        (?:[._%+-][a-z0-9]+)*      # Allowed special chars in the local part
        @                          # At symbol
        (?:                        # Start of domain part
            [a-z0-9]+              # Domain label starts with alphanumeric
            (?:[-][a-z0-9]+)*      # Domain label may have hyphens
            \.                     # Dot separator
        )+                         # One or more domain labels
        [a-z]{2,}                  # Top-level domain
    )                              # End of capturing group
    (?![\w\.-])                    # Negative lookahead
    ''', re.VERBOSE
)

# Keywords to prioritize certain pages when we scrape urls
URL_KEYWORDS = ['contact', 'about', 'staff', 'team', 'info', 'support', 'help', 'home',
'guest', 'member', 'location', 'people', 'jobs']

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
  "little ceasar",
  "little ceasar's pizza",
  "taco bueno",
  "schlotzsky's",
  "schlotzskys",
  "ihop",
  "jimmysegg",
  "jimmy's egg",
  "golden chick",
  "panda express",
  "taco mayo",
  "popeyes",
  "jimmy john's",
  "raising cane's",
  "papa johns",
  "dunkin",
]

EXCLUDED_DOMAINS = {
    'facebook.com',
    'www.facebook.com',
    'twitter.com',
    'www.twitter.com',
    'instagram.com',
    'www.instagram.com',
    'linkedin.com',
    'www.linkedin.com',
    'youtube.com',
    'www.youtube.com',
    'google.com',
    'www.google.com',
    'yahoo.com',
    'www.yahoo.com',
    'pinterest.com',
    'www.pinterest.com',
    'reddit.com',
    'www.reddit.com',
    't.co',
    'bit.ly',
    'goo.gl',
    'mailto',  # Although 'mailto' is handled separately, including it here reinforces the exclusion
    # Add any other domains you wish to exclude
}


# Rate limiter: 1 request per second (adjust as needed)
rate_limiter = AsyncLimiter(max_rate=1, time_period=SLEEP_TIME_SECS)  # 1 request per 1 second

# Initialize or load cache
def load_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache, cache_file):
    with open(cache_file, 'wb') as f:
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

# Function to get businesses from Google Places API, filtering fast food and shifting center as needed
def get_businesses(location, api_key, business_type, num_results, distance_km, bearing_angle, search_radius_km):
    all_businesses = []
    visited_place_ids = set()
    radius = search_radius_km * 1000  # Convert search radius to meters
    lat, lng = location

    while len(all_businesses) < num_results:
        print(f"\n=== Searching at lat={lat}, lng={lng} ===")
        
        # Fetch businesses for the current location
        businesses = fetch_businesses_in_radius((lat, lng), api_key, radius, business_type)
        if not businesses:
            print(f"No more businesses found in radius: {radius} meters. Shifting center.")
        
        # Filter out fast-food chains by name
        filtered_businesses = [r for r in businesses if not any(chain.lower() in r['name'].lower() for chain in FAST_FOOD_CHAINS)]

        # Filter out duplicates by checking place_id
        new_businesses = [r for r in filtered_businesses if r['place_id'] not in visited_place_ids]
        if not new_businesses:
            print(f"No more new businesses found in radius: {radius} meters. Shifting center.")

        # Track visited places to avoid duplicates
        visited_place_ids.update(r['place_id'] for r in new_businesses)

        # Add unique new businesses to the final list
        all_businesses.extend(new_businesses)
        
        print(f"Retrieved {len(new_businesses)} new businesses, total unique valid businesses: {len(all_businesses)}")

        # Stop if we have enough businesses
        if len(all_businesses) >= num_results:
            print(f"Reached the target of {num_results} businesses.")
            break

        # Shift the center if needed
        print(f"Moving center by {distance_km} km at a bearing of {bearing_angle}°")
        lat, lng = move_center(lat, lng, distance_km, bearing_angle)

    return all_businesses[:num_results]

# Helper function to fetch businesses within a specified radius, pulling all available pages
def fetch_businesses_in_radius(location, api_key, radius, business_type):
    businesses = []
    url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    params = {
        'location': f"{location[0]},{location[1]}",  # Latitude, Longitude
        'radius': radius,  # Use radius instead of rankby=distance for finer control
        'type': business_type,
        'key': api_key
    }

    while True:
        response = requests.get(url, params=params)
        time.sleep(SLEEP_TIME_SECS)
        data = response.json()

        if 'error_message' in data:
            print(f"Error in Nearby Search API response: {data['error_message']}")
            break

        if 'results' in data:
            businesses.extend(data.get('results', []))

        next_page_token = data.get('next_page_token')

        if next_page_token:
            print("Waiting for next page token...")
            time.sleep(2)  # Required delay before using the next_page_token
            params['pagetoken'] = next_page_token
        else:
            # No more pages available, exit loop
            break

    return businesses

# Function to get detailed information for each business (with caching and response debugging)
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
            emails = asyncio.run(find_emails(website, DEBUG))  # the async calls will resolve before we try to access emails
            emails = normalize_emails(emails)    # This effectively removes duplicates
            emails = prioritize_emails(emails)
            email = ';'.join(emails) if emails else 'N/A'
            print(f'=> Found the following emails: \"{'; '.join(emails)}\"')
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

def normalize_emails(email_list):
    """
    Converts all emails in the list to lowercase and removes duplicates,
    preserving the original order.

    Parameters:
        email_list (list): A list of email addresses (strings).

    Returns:
        list: A new list with emails in lowercase and duplicates removed.
    """
    seen = set()
    normalized_list = []
    for email in email_list:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            normalized_list.append(email_lower)
    return normalized_list

def prioritize_emails(email_list):
    """
    Sorts a list of email addresses, prioritizing those likely to be good points of contact.

    Parameters:
        email_list (list): A list of email addresses (strings).

    Returns:
        list: A new list with emails sorted to prioritize business contact addresses.
    """
    # List of prefixes that are likely good points of contact
    priority_prefixes = [
        'sales', 'info', 'questions', 'contact', 'support', 'hello',
        'inquiries', 'business', 'admin', 'office', 'general', 'customerservice',
        'enquiries', 'service', 'team', 'marketing', 'press', 'partnerships',
        'help', 'career', 'jobs', 'inquiry', 'media', 'hr', 'recruitment',
        'feedback', 'legal', 'enquiry', 'request', 'advertising', 'affiliates',
        'billing', 'donations', 'volunteer', 'webmaster', 'newsletter', 'pr',
        'services', 'order', 'orders', 'purchasing', 'management', 'info-en',
        'customercare', 'customerrelations', 'crm', 'customer-service', 'cs',
        'supportteam', 'helpdesk', 'assistance'
    ]

    # Normalize priority prefixes for case-insensitive comparison
    priority_prefixes = set(prefix.lower() for prefix in priority_prefixes)

    def get_prefix(email):
        # Extract the local part before the '@' symbol and convert to lowercase
        return email.split('@')[0].lower()

    # Sort the emails
    sorted_emails = sorted(
        email_list,
        key=lambda email: (get_prefix(email) not in priority_prefixes, email)
    )

    return sorted_emails

def filter_valid_emails(emails, debug=False):
    """
    Filters out emails that are likely filenames or invalid.

    Parameters:
        emails (set): A set of email addresses.
        debug (bool): If True, prints debug information.

    Returns:
        set: A set of valid email addresses.
    """
    valid_emails = set()
    invalid_tlds = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg'}
    for email in emails:
        try:
            local_part, domain_part = email.rsplit('@', 1)
            domain_labels = domain_part.split('.')
            tld = domain_labels[-1].lower()
            if tld not in invalid_tlds:
                valid_emails.add(email)
            else:
                if debug:
                    print(f"Skipping email with invalid TLD: {email}")
        except ValueError:
            # Invalid email format
            if debug:
                print(f"Invalid email format: {email}")
            continue
    return valid_emails

def should_exclude_url(url):
    """
    Determines if a URL should be excluded based on the domain.

    Parameters:
        url (str): The URL to check.

    Returns:
        bool: True if the URL should be excluded, False otherwise.
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        # Remove 'www.' prefix for consistency
        if domain.startswith('www.'):
            domain = domain[4:]
        if domain in EXCLUDED_DOMAINS:
            return True
        else:
            return False
    except Exception:
        return True  # Exclude URLs that cannot be parsed

async def find_emails(start_url, debug=False):
    emails = set()
    visited = set()
    queue = asyncio.Queue()
    await queue.put(start_url)
    if debug:
        print(f'Starting crawl with URL: {start_url}')

    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0 (compatible; EmailCrawler/1.0)'}) as session:
        tasks = []
        for i in range(10):  # Number of concurrent workers
            task = asyncio.create_task(worker(session, emails, visited, queue, debug))
            tasks.append(task)
            if debug:
                print(f'Created worker {i+1}')
        await queue.join()
        # Stop workers
        for _ in range(10):
            await queue.put(None)
        await asyncio.gather(*tasks)

    if debug:
        print('Crawl finished.')
    return emails

async def worker(session, emails, visited, queue, debug):
    while True:
        url = await queue.get()
        if url is None:
            queue.task_done()
            if debug:
                print('Worker received termination signal.')
            break
        if url in visited:
            if debug:
                print(f'Skipping already visited URL: {url}')
            queue.task_done()
            continue
        visited.add(url)
        print(f'Processing page: {url}')
        await process_page(url, session, emails, visited, queue, debug)
        queue.task_done()

def get_domain(url):
    ext = tldextract.extract(url)
    domain = f"{ext.domain}.{ext.suffix}"
    return domain.lower()

async def process_page(url, session, emails, visited, queue, debug):
    try:
        # Use the rate limiter
        async with rate_limiter:
            if debug:
                print(f'Sending GET request to {url}')
            async with session.get(url, timeout=10) as response:
                if debug:
                    print(f'Received response with status {response.status} for {url}')
                if response.status != 200:
                    if debug:
                        print(f'Non-200 status code for {url}: {response.status}')
                    return
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type:
                    if debug:
                        print(f'Skipping non-HTML content at {url}: {content_type}')
                    return
                html = await response.text()
                new_emails = set(EMAIL_REGEX.findall(html))
                valid_emails = filter_valid_emails(new_emails, debug=debug)
                if valid_emails:
                    if debug:
                        print(f'Found emails on {url}: {valid_emails}')
                emails.update(valid_emails)
                # Find new URLs to crawl
                soup = BeautifulSoup(html, 'html.parser')
                base_domain = get_domain(url)
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    href = urldefrag(href)[0]  # Remove fragment

                    # Unquote the href to handle URL-encoded characters
                    href_unquoted = unquote(href)

                    # Handle mailto links
                    if href_unquoted.startswith('mailto:'):
                        email_address = href_unquoted[7:]  # Remove 'mailto:'
                        email_address = email_address.split('?')[0]  # Remove any parameters
                        match = EMAIL_REGEX.fullmatch(email_address)
                        if match:
                            emails.add(match.group(1))
                            if debug:
                                print(f'Found email in mailto link: {email_address}')
                        else:
                            if debug:
                                print(f'Invalid email in mailto link: {email_address}')
                        continue  # Skip to next link

                    # Handle email addresses in href without mailto:
                    if '@' in href_unquoted:
                        possible_email = href_unquoted.split('?')[0]
                        match = EMAIL_REGEX.fullmatch(possible_email)
                        if match:
                            emails.add(match.group(1))
                            if debug:
                                print(f'Found email in href: {possible_email}')
                            continue  # Skip to next link

                    # Parse the href
                    parsed_href = urlparse(href_unquoted)

                    # Skip non-http(s) links (e.g., 'javascript:', 'tel:')
                    if parsed_href.scheme and parsed_href.scheme not in ('http', 'https'):
                        if debug:
                            print(f'Skipping non-http(s) link: {href_unquoted}')
                        continue  # Skip to next link

                    # Skip URLs with '@' in netloc (likely an email address misinterpreted)
                    if '@' in parsed_href.netloc:
                        if debug:
                            print(f"Skipping URL with '@' in netloc: {href_unquoted}")
                        continue  # Skip to next link

                    # Use the filtering function to exclude certain domains
                    if should_exclude_url(href):
                        if debug:
                            print(f'Skipping excluded domain: {href}')
                        continue  # Skip to next link

                    # Handle protocol-relative URLs (starting with '//')
                    if href_unquoted.startswith('//'):
                        href = 'http:' + href_unquoted
                    # Convert relative URLs to absolute URLs
                    elif not parsed_href.scheme:
                        href = urljoin(url, href_unquoted)
                    else:
                        href = href_unquoted

                    # Now process the URL
                    link_domain = get_domain(href)
                    if link_domain != base_domain:
                        if debug:
                            print(f'Skipping external link: {href}')
                        continue  # Skip external links
                    if any(keyword in href.lower() for keyword in URL_KEYWORDS):
                        if href not in visited:
                            if debug:
                                print(f'Adding to queue: {href}')
                            await queue.put(href)
                        else:
                            if debug:
                                print(f'Already visited or queued: {href}')
                    else:
                        if debug:
                            print(f'URL does not match keywords, skipping: {href}')
    except Exception as e:
        if debug:
            print(f'Error processing {url}: {e}')
        pass  # Ignore errors to keep the crawler running

# Main function to handle argument parsing and CSV writing
def main():
    # Example usages to be displayed in the help message
    example_text = '''\
Example usage:

  # Using the environment variable for the API key:
  export GOOGLE_API_KEY=your_google_api_key_here
  ./find-businesses.py

  # Using the command-line API key option:
  ./find-businesses.py --api-key your_google_api_key_here
'''

    # Set up argument parsing for the various options, including custom examples in the epilog
    parser = argparse.ArgumentParser(
        description="Retrieve businesses using Google Places API.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=example_text
    )
    parser.add_argument('--search-center', '-c', type=str, default=DEFAULT_CENTER,
                        help='The center of the search (address or city) (default: Norman, OK)')
    parser.add_argument('--search-radius', '-r', type=float, default=DEFAULT_SEARCH_RADIUS,
                        help=f'The radius of the search from the center, for each batch (default: {DEFAULT_SEARCH_RADIUS} km)')
    parser.add_argument('--distance', '-d', type=float, default=DEFAULT_DISTANCE,
                        help=f'Distance in kilometers to move the center per batch (default: {DEFAULT_DISTANCE} km)')
    parser.add_argument('--number', '-n', type=int, default=20,
                        help='Number of businesses to retrieve (default: 20)')
    parser.add_argument('--bearing', '-b', type=float, default=DEFAULT_BEARING,
                        help=f'Bearing angle in degrees from North to move the search center (default: {DEFAULT_BEARING} degrees)')
    parser.add_argument('--output', '-o', type=str, default='businesses_google.csv',
                        help='Output CSV file (default: businesses_google.csv)')
    parser.add_argument('--api-key', '-a', type=str,
                        help='Google API Key. If not provided, the environment variable GOOGLE_API_KEY will be used.')
    parser.add_argument('--business-type', '-t', type=str, default=DEFAULT_BUSINESS_TYPE,
                        help=f'The type of business to search for (default: {DEFAULT_BUSINESS_TYPE}')
    args = parser.parse_args()

    # Check if the API key is provided via the command line or environment variable
    api_key = args.api_key or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: Google API key not provided. Please set the environment variable GOOGLE_API_KEY or use the --api-key flag.")
        return

    # Load the cache
    cache_file = f'{DEFAULT_CACHE_FILE}.{args.business_type}'
    cache = load_cache(cache_file)

    # Geocode the search center to get latitude and longitude
    search_center = args.search_center
    location = get_lat_lng(search_center, api_key)
    if not location:
        print(f"Error: Unable to geocode location: {search_center}")
        return

    # Get the list of businesses (handling pagination)
    businesses = get_businesses(location, api_key, args.business_type, args.number, args.distance, args.bearing, args.search_radius)

    # Calculate distance and get details for each business
    detailed_businesses = []
    total_businesses = len(businesses)
    for index, place in enumerate(businesses, start=1):
        place_id = place.get('place_id')

        # Get the detailed info (with caching and response debugging)
        details = get_place_details(cache, place_id, api_key, index, total_businesses)

        detailed_businesses.append(details)

    # Save the updated cache
    save_cache(cache, cache_file)

if __name__ == '__main__':
    main()
