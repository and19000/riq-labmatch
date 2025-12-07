#!/usr/bin/env python3
"""
Generate a report of website validation results.
Shows which websites were fixed, which are still invalid, etc.
"""

import json
import requests
from urllib.parse import urlparse

def check_url_quick(url):
    """Quick check if URL exists."""
    if not url or not url.startswith(('http://', 'https://')):
        return False
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

def generate_report():
    """Generate a comprehensive report of website status."""
    print("Loading faculty.json...")
    with open('data/faculty.json', 'r', encoding='utf-8') as f:
        faculty_list = json.load(f)
    
    total = len(faculty_list)
    valid_count = 0
    invalid_count = 0
    no_website_count = 0
    
    invalid_faculty = []
    no_website_faculty = []
    
    print(f"Checking {total} faculty members...\n")
    
    for i, faculty in enumerate(faculty_list, 1):
        name = faculty.get('name', 'Unknown')
        website = faculty.get('website', '')
        school = faculty.get('school', '')
        department = faculty.get('department', '')
        email = faculty.get('email', '')
        
        if not website:
            no_website_count += 1
            no_website_faculty.append({
                'name': name,
                'school': school,
                'department': department,
                'email': email
            })
        else:
            is_valid = check_url_quick(website)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_faculty.append({
                    'name': name,
                    'school': school,
                    'department': department,
                    'email': email,
                    'current_url': website
                })
        
        if i % 100 == 0:
            print(f"  Processed {i}/{total}...")
    
    # Generate report
    print(f"\n{'='*70}")
    print("WEBSITE VALIDATION REPORT")
    print(f"{'='*70}\n")
    print(f"Total faculty: {total}")
    print(f"Valid websites: {valid_count} ({valid_count/total*100:.1f}%)")
    print(f"Invalid websites: {invalid_count} ({invalid_count/total*100:.1f}%)")
    print(f"No website: {no_website_count} ({no_website_count/total*100:.1f}%)")
    
    if invalid_faculty:
        print(f"\n{'='*70}")
        print(f"INVALID WEBSITES ({len(invalid_faculty)}):")
        print(f"{'='*70}\n")
        for fac in invalid_faculty[:50]:  # Show first 50
            print(f"  {fac['name']} ({fac['school']}, {fac['department']})")
            print(f"    Current URL: {fac['current_url']}")
            print(f"    Email: {fac['email']}")
            print()
        if len(invalid_faculty) > 50:
            print(f"  ... and {len(invalid_faculty) - 50} more\n")
    
    if no_website_faculty:
        print(f"\n{'='*70}")
        print(f"NO WEBSITE ({len(no_website_faculty)}):")
        print(f"{'='*70}\n")
        for fac in no_website_faculty[:50]:  # Show first 50
            print(f"  {fac['name']} ({fac['school']}, {fac['department']})")
            print(f"    Email: {fac['email']}")
            print()
        if len(no_website_faculty) > 50:
            print(f"  ... and {len(no_website_faculty) - 50} more\n")
    
    # Save detailed report to file
    report_data = {
        'summary': {
            'total': total,
            'valid': valid_count,
            'invalid': invalid_count,
            'no_website': no_website_count
        },
        'invalid_websites': invalid_faculty,
        'no_website': no_website_faculty
    }
    
    with open('data/website_validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("Detailed report saved to: data/website_validation_report.json")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    generate_report()

