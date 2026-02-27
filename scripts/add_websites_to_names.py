#!/usr/bin/env python3
"""
Script to add verified websites to faculty_names.json
Extracts websites from faculty.json, verifies they work, and adds them to faculty_names.json
"""

import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse

# Configure requests with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Set a reasonable timeout and user agent
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
})

def check_url_exists(url, timeout=10):
    """Check if a URL exists and is accessible."""
    if not url or not url.startswith(('http://', 'https://')):
        return False, None
    
    try:
        # Validate URL encoding first
        parsed = urlparse(url)
        if not parsed.netloc or len(parsed.netloc) > 253:  # Max domain length
            return False, "Invalid URL format"
        
        response = session.head(url, timeout=timeout, allow_redirects=True)
        # Some servers don't support HEAD, try GET if HEAD fails
        if response.status_code == 405:
            response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            response.close()
        
        return response.status_code < 400, response.status_code
    except (requests.exceptions.RequestException, UnicodeError, ValueError) as e:
        return False, str(e)[:50]  # Truncate long error messages

def main():
    print("Loading faculty.json...")
    with open('data/faculty.json', 'r', encoding='utf-8') as f:
        faculty_data = json.load(f)
    
    print("Loading faculty_names.json...")
    with open('data/faculty_names.json', 'r', encoding='utf-8') as f:
        faculty_names = json.load(f)
    
    # Create a lookup dictionary by ID
    faculty_lookup = {item['id']: item for item in faculty_data}
    
    total = len(faculty_names)
    verified_count = 0
    invalid_count = 0
    missing_count = 0
    
    print(f"\nProcessing {total} faculty members...\n")
    
    for i, entry in enumerate(faculty_names):
        faculty_id = entry['id']
        name = entry['name']
        
        # Look up website from faculty.json
        if faculty_id in faculty_lookup:
            website = faculty_lookup[faculty_id].get('website', '')
            
            if website:
                print(f"[{i+1}/{total}] {name}...", end=' ', flush=True)
                
                # Verify website works
                exists, status = check_url_exists(website)
                
                if exists:
                    entry['website'] = website
                    verified_count += 1
                    print(f"✓ Verified")
                else:
                    invalid_count += 1
                    print(f"✗ Invalid (status: {status})")
                    # Still add it but mark as invalid or leave it out
                    # For now, we'll skip invalid websites
            else:
                missing_count += 1
                print(f"[{i+1}/{total}] {name}... ✗ No website in faculty.json")
        else:
            missing_count += 1
            print(f"[{i+1}/{total}] {name}... ✗ ID not found in faculty.json")
        
        # Rate limiting - be respectful
        time.sleep(0.2)
        
        # Save progress every 50 entries
        if (i + 1) % 50 == 0:
            print(f"\n  [Progress] Saving checkpoint... ({i+1}/{total} checked)")
            with open('data/faculty_names.json', 'w', encoding='utf-8') as f:
                json.dump(faculty_names, f, indent=2, ensure_ascii=False)
            print()
    
    # Final save
    print(f"\nSaving final results...")
    with open('data/faculty_names.json', 'w', encoding='utf-8') as f:
        json.dump(faculty_names, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Processing Complete!")
    print(f"Total entries: {total}")
    print(f"Verified websites added: {verified_count}")
    print(f"Invalid websites (skipped): {invalid_count}")
    print(f"Missing websites: {missing_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()




