#!/usr/bin/env python3
"""
Script to validate and fix faculty website URLs.
Checks if websites exist and finds correct URLs if they don't.
"""

import json
import time
import re
from urllib.parse import urlparse, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        response = session.head(url, timeout=timeout, allow_redirects=True)
        # Some servers don't support HEAD, try GET if HEAD fails
        if response.status_code == 405:
            response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            response.close()
        
        return response.status_code < 400, response.status_code
    except requests.exceptions.RequestException as e:
        return False, str(e)

def extract_name_parts(name):
    """Extract first and last name from faculty name."""
    # Remove "Dr." prefix
    name = re.sub(r'^Dr\.\s*', '', name, flags=re.IGNORECASE).strip()
    parts = name.split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return parts[0] if parts else "", ""

def generate_name_variations(first_name, last_name):
    """Generate various name format variations for URL searching."""
    variations = []
    if not last_name:
        return variations
    
    last_lower = last_name.lower()
    first_lower = first_name.lower() if first_name else ""
    
    # Basic variations
    variations.append(last_lower)
    if first_lower:
        variations.append(f"{first_lower}-{last_lower}")
        variations.append(f"{last_lower}-{first_lower}")
        variations.append(f"{first_lower[0]}{last_lower}" if first_lower else last_lower)
        variations.append(f"{first_lower[0]}-{last_lower}" if first_lower else last_lower)
    
    # Handle hyphenated last names
    if '-' in last_lower:
        parts = last_lower.split('-')
        variations.extend(parts)
        variations.append(f"{parts[0]}-{parts[1]}")
    
    # Handle compound first names
    if '-' in first_lower:
        parts = first_lower.split('-')
        variations.append(f"{parts[0]}-{last_lower}")
        variations.append(f"{parts[-1]}-{last_lower}")
    
    return list(set(variations))  # Remove duplicates

def find_harvard_website(name, department, email=None):
    """Try to find Harvard faculty website."""
    first_name, last_name = extract_name_parts(name)
    if not last_name:
        return None
    
    name_variations = generate_name_variations(first_name, last_name)
    possible_urls = []
    
    # Generate URLs for each name variation
    for name_var in name_variations:
        # Standard SEAS patterns
        possible_urls.extend([
            f"https://seas.harvard.edu/people/{name_var}",
            f"https://seas.harvard.edu/faculty/{name_var}",
            # Try subdomain patterns (common for Harvard faculty)
            f"https://{name_var}.seas.harvard.edu/",
            f"https://people.seas.harvard.edu/~{name_var}/",
            f"https://www.eecs.harvard.edu/~{name_var}/",
        ])
        
        # Department-specific patterns
        if department:
            dept_lower = department.lower().replace(' ', '-').replace('&', 'and')
            possible_urls.extend([
                f"https://seas.harvard.edu/{dept_lower}/people/{name_var}",
                f"https://seas.harvard.edu/{dept_lower}/faculty/{name_var}",
            ])
        
        # Try Harvard main site
        possible_urls.extend([
            f"https://www.harvard.edu/people/{name_var}",
            f"https://scholar.harvard.edu/{name_var}",
        ])
        
        # Try MCB (Molecular and Cellular Biology)
        if 'biology' in department.lower() or 'mcb' in department.lower():
            possible_urls.extend([
                f"https://mcb.harvard.edu/faculty/{name_var}",
                f"https://mcb.harvard.edu/people/{name_var}",
            ])
        
        # Try Chemistry
        if 'chemistry' in department.lower():
            possible_urls.extend([
                f"https://chemistry.harvard.edu/people/{name_var}",
                f"https://chemistry.harvard.edu/faculty/{name_var}",
            ])
        
        # Try Physics
        if 'physics' in department.lower():
            possible_urls.extend([
                f"https://www.physics.harvard.edu/people/faculty/{name_var}",
                f"https://www.physics.harvard.edu/faculty/{name_var}",
            ])
        
        # Try other departments
        if 'statistics' in department.lower():
            possible_urls.extend([
                f"https://statistics.harvard.edu/people/{name_var}",
            ])
        
        if 'economics' in department.lower():
            possible_urls.extend([
                f"https://economics.harvard.edu/people/faculty/{name_var}",
            ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in possible_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    for url in unique_urls:
        exists, status = check_url_exists(url)
        if exists:
            return url
    
    return None

def find_mit_website(name, department):
    """Try to find MIT faculty website."""
    first_name, last_name = extract_name_parts(name)
    if not last_name:
        return None
    
    last_name_lower = last_name.lower()
    possible_urls = [
        f"https://www.csail.mit.edu/people/{last_name_lower}",
        f"https://www.eecs.mit.edu/people/{last_name_lower}",
        f"https://web.mit.edu/{last_name_lower}/www/",
        f"https://people.csail.mit.edu/{last_name_lower}/",
    ]
    
    for url in possible_urls:
        exists, status = check_url_exists(url)
        if exists:
            return url
    
    return None

def find_broad_website(name):
    """Try to find Broad Institute website."""
    first_name, last_name = extract_name_parts(name)
    if not last_name:
        return None
    
    last_name_lower = last_name.lower()
    possible_urls = [
        f"https://www.broadinstitute.org/people/{last_name_lower}",
        f"https://www.broadinstitute.org/bios/{last_name_lower}",
    ]
    
    for url in possible_urls:
        exists, status = check_url_exists(url)
        if exists:
            return url
    
    return None

def find_faculty_website(faculty):
    """Try to find the correct website for a faculty member."""
    name = faculty.get('name', '')
    school = faculty.get('school', '')
    department = faculty.get('department', '')
    email = faculty.get('email', '')
    scholar_url = faculty.get('google_scholar', '')
    
    # First, try to extract from Google Scholar profile
    if scholar_url:
        scholar_website = extract_website_from_scholar(scholar_url)
        if scholar_website:
            return scholar_website
    
    # Try school-specific patterns
    if 'Harvard' in school:
        url = find_harvard_website(name, department, email)
        if url:
            return url
    
    if 'MIT' in school:
        url = find_mit_website(name, department)
        if url:
            return url
    
    if 'Broad' in school:
        url = find_broad_website(name)
        if url:
            return url
    
    return None

def extract_website_from_scholar(scholar_url):
    """Try to extract website URL from Google Scholar profile."""
    if not scholar_url:
        return None
    
    try:
        response = session.get(scholar_url, timeout=10, allow_redirects=True)
        if response.status_code >= 400:
            return None
        
        # Look for homepage link in the page
        content = response.text
        # Common patterns for homepage links in Google Scholar
        patterns = [
            r'href="([^"]*homepage[^"]*)"',
            r'href="([^"]*home[^"]*)"',
            r'href="(https?://[^"]*\.edu/[^"]*)"',
            r'Homepage[^<]*<a[^>]*href="([^"]*)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    return match
        
        return None
    except:
        return None

def verify_website_matches(faculty, url):
    """Verify that a website URL matches the faculty member."""
    if not url:
        return False
    
    try:
        response = session.get(url, timeout=10, allow_redirects=True)
        if response.status_code >= 400:
            return False
        
        # Check if the page content contains the faculty name
        content = response.text.lower()
        name_parts = extract_name_parts(faculty.get('name', ''))
        email = faculty.get('email', '').lower()
        department = faculty.get('department', '').lower()
        
        # Check for last name (most reliable)
        if name_parts[1]:
            last_name_lower = name_parts[1].lower()
            if last_name_lower in content:
                return True
            # Also check URL itself contains last name
            if last_name_lower in url.lower():
                return True
        
        # Check for email domain match (if URL is from same institution)
        if email and '@' in email:
            email_domain = email.split('@')[1]
            url_domain = urlparse(url).netloc.lower()
            if email_domain in url_domain or url_domain in email_domain:
                # If domains match and URL structure looks like a faculty page
                if any(x in url.lower() for x in ['/people/', '/faculty/', '/professor/', '/~', '/staff/']):
                    return True
        
        # Check for department match
        if department and department in content:
            if name_parts[0] and name_parts[0].lower() in content:
                return True
        
        # If URL is from the same school domain and has faculty-like structure, accept it
        school = faculty.get('school', '').lower()
        if 'harvard' in school and 'harvard' in url.lower():
            if any(x in url.lower() for x in ['/people/', '/faculty/', '/professor/']):
                return True
        if 'mit' in school and 'mit' in url.lower():
            if any(x in url.lower() for x in ['/people/', '/faculty/', '/professor/', '/~']):
                return True
        
        return False
    except Exception as e:
        # If we can't verify, but URL exists and looks like a faculty page, accept it
        if any(x in url.lower() for x in ['/people/', '/faculty/', '/professor/', '/~']):
            return True
        return False

def validate_and_fix_websites(start_index=0, max_check=None):
    """Main function to validate and fix all faculty websites."""
    print("Loading faculty.json...")
    with open('data/faculty.json', 'r', encoding='utf-8') as f:
        faculty_list = json.load(f)
    
    total = len(faculty_list)
    if max_check:
        end_index = min(start_index + max_check, total)
    else:
        end_index = total
    
    invalid_count = 0
    fixed_count = 0
    failed_count = 0
    valid_count = 0
    
    print(f"Found {total} faculty members.")
    print(f"Processing entries {start_index} to {end_index-1}...\n")
    
    for i in range(start_index, end_index):
        faculty = faculty_list[i]
        name = faculty.get('name', 'Unknown')
        current_url = faculty.get('website', '')
        school = faculty.get('school', '')
        
        print(f"[{i+1}/{total}] {name} ({school})...", end=' ', flush=True)
        
        # Check if current URL exists
        if current_url:
            exists, status = check_url_exists(current_url)
            if exists:
                print(f"✓ Valid")
                valid_count += 1
                continue
            else:
                print(f"✗ Invalid")
                invalid_count += 1
        else:
            print(f"✗ No website")
            invalid_count += 1
        
        # Try to find correct website
        new_url = find_faculty_website(faculty)
        
        if new_url:
            # Verify it matches
            if verify_website_matches(faculty, new_url):
                faculty['website'] = new_url
                fixed_count += 1
                print(f"  → Fixed: {new_url}")
            else:
                print(f"  → Found but doesn't match")
                failed_count += 1
        else:
            print(f"  → Not found")
            failed_count += 1
        
        # Rate limiting - be respectful
        time.sleep(0.3)
        
        # Save progress every 25 entries
        if (i + 1) % 25 == 0:
            print(f"\n  [Progress] Saving checkpoint... ({i+1}/{total} checked)")
            with open('data/faculty.json', 'w', encoding='utf-8') as f:
                json.dump(faculty_list, f, indent=2, ensure_ascii=False)
            print()
    
    # Final save
    print(f"\nSaving final results...")
    with open('data/faculty.json', 'w', encoding='utf-8') as f:
        json.dump(faculty_list, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Validation Complete!")
    print(f"Processed: {end_index - start_index} entries")
    print(f"Valid websites: {valid_count}")
    print(f"Invalid websites: {invalid_count}")
    print(f"Successfully fixed: {fixed_count}")
    print(f"Failed to fix: {failed_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    import sys
    start_index = 0
    max_check = None
    
    if len(sys.argv) > 1:
        start_index = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_check = int(sys.argv[2])
    
    validate_and_fix_websites(start_index=start_index, max_check=max_check)

