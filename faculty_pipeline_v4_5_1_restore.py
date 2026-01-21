#!/usr/bin/env python3
"""
Faculty Pipeline v4.5.1 - Resume from v4.4 Data

This script:
1. Loads your existing v4.4 results (539 websites, 172 emails)
2. Applies v4.5's improved email extraction to faculty WITH websites but WITHOUT emails
3. Only uses Brave API for faculty who still need websites (~60)

NO DATA IS LOST - this builds on your v4.4 work!

Usage:
    python faculty_pipeline_v4_5_1_restore.py \
        --input output/harvard_university_20260120_162804.json \
        --output output \
        --verbose
"""

import os
import sys
import json
import re
import time
import logging
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin
from pathlib import Path
from collections import Counter
import html
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")

HARVARD_CONFIG = {
    "name": "Harvard University",
    "email_domains": [
        "harvard.edu", "hms.harvard.edu", "hsph.harvard.edu",
        "fas.harvard.edu", "hbs.edu", "dfci.harvard.edu",
        "mgh.harvard.edu", "bwh.harvard.edu", "childrens.harvard.edu",
        "broadinstitute.org", "dana-farber.org", "bidmc.harvard.edu",
        "meei.harvard.edu", "mclean.harvard.edu", "hsdm.harvard.edu",
        "massgeneral.org", "brighamandwomens.org", "mgh.org",
    ],
    "website_domain": "harvard.edu",
    "skip_email_sites": [
        "connects.catalyst.harvard.edu",
        "vcp.med.harvard.edu",
    ],
    "contact_page_sites": [
        "hsph.harvard.edu",
        "hms.harvard.edu",
    ],
}

# Rate limiting
BRAVE_DELAY = 0.6
SCRAPE_DELAY = 0.3
MAX_RETRIES = 3
EMAIL_SCRAPE_TIMEOUT = 15
MAX_CONTACT_PAGES = 7
FUZZY_MATCH_THRESHOLD = 0.85

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=handlers
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ============================================================================
# NAME MATCHER (from v4.5)
# ============================================================================

class NameMatcher:
    TITLES = ['dr', 'prof', 'professor', 'mr', 'mrs', 'ms', 'phd', 'md', 'jr', 'sr', 'iii', 'ii', 'iv']
    
    @staticmethod
    def normalize(name: str) -> str:
        name = name.lower().strip()
        for title in NameMatcher.TITLES:
            name = re.sub(rf'\b{title}\.?\b', '', name)
        name = re.sub(r'[^\w\s-]', ' ', name)
        return ' '.join(name.split())
    
    @staticmethod
    def get_name_parts(name: str) -> Dict[str, str]:
        norm = NameMatcher.normalize(name)
        parts = norm.split()
        if len(parts) == 0:
            return {"first": "", "last": "", "middle": "", "full": ""}
        elif len(parts) == 1:
            return {"first": parts[0], "last": parts[0], "middle": "", "full": norm}
        elif len(parts) == 2:
            return {"first": parts[0], "last": parts[1], "middle": "", "full": norm}
        else:
            return {"first": parts[0], "last": parts[-1], "middle": " ".join(parts[1:-1]), "full": norm}
    
    @staticmethod
    def match_email_to_name(email: str, faculty_name: str) -> float:
        if not email or not faculty_name:
            return 0.0
        
        local_part = email.lower().split('@')[0]
        parts = NameMatcher.get_name_parts(faculty_name)
        first = parts["first"]
        last = parts["last"]
        
        score = 0.0
        
        if last and len(last) > 2 and last in local_part:
            score += 0.5
        if first and len(first) > 2 and first in local_part:
            score += 0.3
        
        patterns = [
            f"{first[0]}{last}" if first else "",
            f"{first[0]}_{last}" if first else "",
            f"{first[0]}.{last}" if first else "",
            f"{first}.{last}",
            f"{first}_{last}",
        ]
        
        for pattern in patterns:
            if pattern and pattern in local_part:
                score += 0.2
                break
        
        return min(score, 1.0)

# ============================================================================
# GENERIC EMAIL PATTERNS
# ============================================================================

GENERIC_EMAIL_PATTERNS = [
    r'^info@', r'^contact@', r'^admin@', r'^office@',
    r'^department@', r'^dept@', r'^general@', r'^inquiries@',
    r'^support@', r'^help@', r'^webmaster@', r'^web@',
    r'^communications@', r'^media@', r'^press@', r'^news@',
    r'^events@', r'^editor@', r'^subscribe@', r'^noreply@',
    r'^hr@', r'^careers@', r'^admissions@', r'^registrar@',
    r'^alumni@', r'^development@', r'^giving@', r'^contedu@',
    r'^programs?@', r'^courses?@', r'^steppingstrong@',
    r'^ogephd@', r'^dms@', r'^hms@', r'^lab@', r'^research@',
    r'^faculty@', r'^staff@', r'^graduate@', r'^undergraduate@',
]

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

OBFUSCATION_PATTERNS = [
    (r'([A-Za-z0-9._%+-]+)\s*\[\s*at\s*\]\s*([A-Za-z0-9.-]+)\s*\[\s*dot\s*\]\s*([A-Za-z]{2,})', r'\1@\2.\3'),
    (r'([A-Za-z0-9._%+-]+)\s*\(\s*at\s*\)\s*([A-Za-z0-9.-]+)\s*\(\s*dot\s*\)\s*([A-Za-z]{2,})', r'\1@\2.\3'),
    (r'([A-Za-z0-9._%+-]+)\s+AT\s+([A-Za-z0-9.-]+)\s+DOT\s+([A-Za-z]{2,})', r'\1@\2.\3'),
    (r'([A-Za-z0-9._%+-]+)\s+at\s+([A-Za-z0-9.-]+)\s+dot\s+([A-Za-z]{2,})', r'\1@\2.\3'),
]

CONTACT_LINK_PATTERNS = [
    '/contact', '/about', '/email', '/bio', '/profile',
    '/cv', '/home', 'biography', 'personal',
    '/people/', '/faculty/', '/staff/', '/directory/',
    '/info', '/reach', '/connect',
]

# ============================================================================
# BRAVE SEARCH CLIENT
# ============================================================================

class BraveSearchClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.queries_used = 0
        self.quota_exhausted = False
    
    def check_quota(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key not set"
        result = self.search("test query")
        if self.quota_exhausted:
            return False, "Quota exhausted"
        return True, "OK"
    
    def search(self, query: str) -> List[Dict]:
        if not self.api_key or self.quota_exhausted:
            return []
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        
        try:
            response = self.session.get(url, headers=headers, params={"q": query, "count": 10}, timeout=15)
            
            if response.status_code == 402:
                self.quota_exhausted = True
                logger.error("⚠️ Brave API quota exhausted!")
                return []
            
            response.raise_for_status()
            self.queries_used += 1
            
            return [
                {"url": item.get("url", ""), "title": item.get("title", ""), "description": item.get("description", "")}
                for item in response.json().get("web", {}).get("results", [])
            ]
        except Exception as e:
            logger.debug(f"Search error: {e}")
            return []

# ============================================================================
# ENHANCED EMAIL EXTRACTOR (v4.5 improvements)
# ============================================================================

class EnhancedEmailExtractor:
    def __init__(self, config: Dict):
        self.config = config
        self.valid_domains = [d.lower() for d in config["email_domains"]]
        self.skip_sites = config.get("skip_email_sites", [])
        self.contact_sites = config.get("contact_page_sites", [])
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.emails_found = 0
    
    def _should_skip(self, url: str) -> bool:
        return any(site in url.lower() for site in self.skip_sites)
    
    def _is_valid_domain(self, email: str) -> bool:
        if not email or '@' not in email:
            return False
        try:
            domain = email.lower().split('@')[1]
            return any(domain == d or domain.endswith('.' + d) for d in self.valid_domains)
        except (IndexError, AttributeError):
            return False
    
    def _is_generic(self, email: str) -> bool:
        email_lower = email.lower()
        return any(re.match(p, email_lower) for p in GENERIC_EMAIL_PATTERNS)
    
    def _fetch_page(self, url: str) -> Optional[Tuple[str, BeautifulSoup]]:
        try:
            response = self.session.get(url, timeout=EMAIL_SCRAPE_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.get_text(separator=' ', strip=True), soup
        except:
            return None
    
    def _extract_emails_from_page(self, text: str, soup: BeautifulSoup) -> List[Tuple[str, str]]:
        candidates = []
        
        # Mailto links
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0].strip().lower()
                email = html.unescape(email)
                if email:
                    candidates.append((email, "mailto"))
        
        # Regex
        for email in EMAIL_REGEX.findall(text):
            candidates.append((email.lower(), "regex"))
        
        # Obfuscated
        for pattern, replacement in OBFUSCATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    email = f"{match[0]}@{match[1]}.{match[2]}".lower()
                    candidates.append((email, "obfuscated"))
        
        return candidates
    
    def _find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        contact_urls = []
        base_domain = urlparse(base_url).netloc
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').lower()
            text = a.get_text().lower()
            
            if any(p in href for p in CONTACT_LINK_PATTERNS) or any(w in text for w in ['contact', 'email']):
                full_url = urljoin(base_url, a.get('href', ''))
                if base_domain in urlparse(full_url).netloc and full_url != base_url:
                    contact_urls.append(full_url)
        
        return list(set(contact_urls))[:MAX_CONTACT_PAGES]
    
    def _select_best_email(self, candidates: List[Tuple[str, str]], name: str) -> Optional[Tuple[str, str, float]]:
        valid = []
        for email, method in candidates:
            if not self._is_valid_domain(email):
                continue
            if self._is_generic(email):
                continue
            
            name_score = NameMatcher.match_email_to_name(email, name)
            method_boost = {"mailto": 0.3, "regex": 0.2, "obfuscated": 0.1, "contact_page": 0.15}.get(method, 0)
            total = name_score + method_boost
            
            # Lower threshold for mailto
            min_score = 0.25 if method == "mailto" else 0.35
            if name_score >= min_score or total >= 0.4:
                valid.append((email, method, total))
        
        if not valid:
            return None
        
        valid.sort(key=lambda x: x[2], reverse=True)
        return valid[0]
    
    def extract_email(self, url: str, name: str) -> Optional[Dict]:
        if not url or self._should_skip(url):
            return None
        
        result = self._fetch_page(url)
        if not result:
            return None
        
        text, soup = result
        candidates = self._extract_emails_from_page(text, soup)
        best = self._select_best_email(candidates, name)
        
        # Try contact pages if no good match
        if not best or best[2] < 0.5:
            for contact_url in self._find_contact_pages(soup, url):
                time.sleep(0.2)
                result = self._fetch_page(contact_url)
                if result:
                    contact_text, contact_soup = result
                    candidates.extend(self._extract_emails_from_page(contact_text, contact_soup))
                    new_best = self._select_best_email(candidates, name)
                    if new_best and (not best or new_best[2] > best[2]):
                        best = new_best
                        if best[2] >= 0.6:
                            break
        
        if best:
            self.emails_found += 1
            return {
                "value": best[0],
                "source": "website",
                "confidence": "high" if best[2] >= 0.6 else "medium",
                "extracted_from": url,
                "extraction_method": best[1],
                "name_match_score": round(best[2], 2),
            }
        
        return None

# ============================================================================
# WEBSITE FINDER (for remaining faculty)
# ============================================================================

class WebsiteFinder:
    HARD_DENYLIST = ["facebook.com", "twitter.com", "linkedin.com", "wikipedia.org", "youtube.com"]
    
    def __init__(self, config: Dict, api_key: str):
        self.config = config
        self.brave = BraveSearchClient(api_key)
    
    def find_website(self, name: str, h_index: int) -> Optional[Dict]:
        if self.brave.quota_exhausted:
            return None
        
        domain = self.config.get("website_domain", "")
        query = f'"{name}" site:{domain}'
        
        results = self.brave.search(query)
        time.sleep(BRAVE_DELAY)
        
        if not results:
            return None
        
        # Score results
        best = None
        best_score = 0
        
        for result in results:
            url = result.get("url", "").lower()
            title = result.get("title", "").lower()
            
            # Skip denied sites
            if any(d in url for d in self.HARD_DENYLIST):
                continue
            
            score = 0
            
            # Institution domain
            if domain and domain in url:
                score += 0.4
            
            # Name in URL or title
            name_parts = NameMatcher.get_name_parts(name)
            if name_parts["last"] in url:
                score += 0.25
            if name_parts["last"] in title:
                score += 0.15
            
            # Profile patterns
            if any(p in url for p in ["/~", "/people/", "/faculty/", "/profile/"]):
                score += 0.2
            
            if score > best_score:
                best_score = score
                best = {
                    "value": result["url"],
                    "source": "search",
                    "confidence": "high" if score >= 0.5 else "medium",
                    "score": round(score, 3),
                }
        
        return best if best_score >= 0.3 else None

# ============================================================================
# MAIN RESTORE & ENHANCE FUNCTION
# ============================================================================

def restore_and_enhance(
    input_path: str,
    output_dir: str = "output",
    api_key: str = None,
    skip_new_websites: bool = False,
    verbose: bool = False,
    log_file: str = None,
) -> Dict:
    """
    Restore v4.4 data and enhance with v4.5 email extraction.
    """
    setup_logging(verbose, log_file)
    start_time = time.time()
    
    logger.info("=" * 70)
    logger.info("FACULTY PIPELINE v4.5.1 - RESTORE & ENHANCE")
    logger.info("=" * 70)
    
    # Load existing data
    logger.info(f"\n📂 Loading existing data from: {input_path}")
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    faculty_list = data.get("faculty", [])
    old_metadata = data.get("metadata", {})
    
    logger.info(f"✓ Loaded {len(faculty_list)} faculty records")
    
    # Analyze current state
    with_website = sum(1 for f in faculty_list if f.get("website", {}).get("value"))
    with_email = sum(1 for f in faculty_list if f.get("email", {}).get("value"))
    
    logger.info(f"\n📊 EXISTING DATA SUMMARY:")
    logger.info(f"  Websites: {with_website}/{len(faculty_list)} ({with_website/len(faculty_list)*100:.1f}%)")
    logger.info(f"  Emails: {with_email}/{len(faculty_list)} ({with_email/len(faculty_list)*100:.1f}%)")
    
    # Initialize extractors
    email_extractor = EnhancedEmailExtractor(HARVARD_CONFIG)
    website_finder = WebsiteFinder(HARVARD_CONFIG, api_key or BRAVE_API_KEY)
    
    # Phase 1: Re-extract emails for faculty WITH websites but WITHOUT emails
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 1: Enhanced Email Extraction (v4.5 improvements)")
    logger.info("=" * 60)
    
    website_no_email = [
        f for f in faculty_list
        if f.get("website", {}).get("value") and not f.get("email", {}).get("value")
    ]
    
    logger.info(f"Faculty with website but no email: {len(website_no_email)}")
    
    new_emails_phase1 = 0
    for i, faculty in enumerate(website_no_email):
        website_url = faculty["website"]["value"]
        name = faculty["name"]
        
        email_data = email_extractor.extract_email(website_url, name)
        
        if email_data:
            faculty["email"] = email_data
            new_emails_phase1 += 1
            logger.info(f"  ✓ [{i+1}/{len(website_no_email)}] {name}: {email_data['value']}")
        
        time.sleep(SCRAPE_DELAY)
        
        if (i + 1) % 50 == 0:
            logger.info(f"  Progress: {i+1}/{len(website_no_email)}, New emails: {new_emails_phase1}")
    
    logger.info(f"\n✓ Phase 1 complete: {new_emails_phase1} new emails found")
    
    # Phase 2: Find websites for faculty WITHOUT websites (uses Brave API)
    new_websites = 0
    new_emails_phase2 = 0
    
    if not skip_new_websites and api_key:
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2: Website Discovery (for remaining faculty)")
        logger.info("=" * 60)
        
        # Check quota first
        has_quota, status = website_finder.brave.check_quota()
        if not has_quota:
            logger.warning(f"⚠️ Brave API: {status}")
            logger.warning("Skipping website discovery. Add credits and re-run.")
        else:
            no_website = [f for f in faculty_list if not f.get("website", {}).get("value")]
            logger.info(f"Faculty without website: {len(no_website)}")
            
            for i, faculty in enumerate(no_website):
                if website_finder.brave.quota_exhausted:
                    logger.warning(f"⚠️ Quota exhausted at {i}/{len(no_website)}")
                    break
                
                name = faculty["name"]
                h_index = faculty.get("h_index", 0)
                
                website_data = website_finder.find_website(name, h_index)
                
                if website_data:
                    faculty["website"] = website_data
                    new_websites += 1
                    logger.info(f"  ✓ [{i+1}] {name}: {website_data['value'][:60]}...")
                    
                    # Try to extract email from new website
                    email_data = email_extractor.extract_email(website_data["value"], name)
                    if email_data:
                        faculty["email"] = email_data
                        new_emails_phase2 += 1
                        logger.info(f"      → Email: {email_data['value']}")
                
                if (i + 1) % 25 == 0:
                    logger.info(f"  Progress: {i+1}/{len(no_website)}, Queries: {website_finder.brave.queries_used}")
            
            logger.info(f"\n✓ Phase 2 complete: {new_websites} new websites, {new_emails_phase2} new emails")
    else:
        logger.info("\n⏭️ Skipping website discovery (no API key or --skip-new-websites)")
    
    # Calculate final stats
    duration = time.time() - start_time
    final_websites = sum(1 for f in faculty_list if f.get("website", {}).get("value"))
    final_emails = sum(1 for f in faculty_list if f.get("email", {}).get("value"))
    
    email_sources = Counter()
    for f in faculty_list:
        if f.get("email", {}).get("value"):
            email_sources[f["email"].get("source", "unknown")] += 1
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("FINAL RESULTS")
    logger.info("=" * 70)
    logger.info(f"Total faculty: {len(faculty_list)}")
    logger.info(f"Websites: {final_websites} ({final_websites/len(faculty_list)*100:.1f}%)")
    logger.info(f"  - From v4.4: {with_website}")
    logger.info(f"  - New in v4.5.1: {new_websites}")
    logger.info(f"Emails: {final_emails} ({final_emails/len(faculty_list)*100:.1f}%)")
    logger.info(f"  - From v4.4: {with_email}")
    logger.info(f"  - New Phase 1 (re-extraction): {new_emails_phase1}")
    logger.info(f"  - New Phase 2 (new websites): {new_emails_phase2}")
    logger.info(f"  - Sources: {dict(email_sources)}")
    logger.info(f"Duration: {duration/60:.1f} minutes")
    logger.info(f"Brave queries: {website_finder.brave.queries_used}")
    
    # Create output
    result = {
        "metadata": {
            "institution": "Harvard University",
            "date": datetime.utcnow().isoformat(),
            "version": "4.5.1",
            "restored_from": input_path,
            "total_faculty": len(faculty_list),
            "websites_found": final_websites,
            "website_coverage": round(final_websites / len(faculty_list), 3),
            "emails_found": final_emails,
            "email_coverage": round(final_emails / len(faculty_list), 3),
            "email_sources": dict(email_sources),
            "new_emails_phase1": new_emails_phase1,
            "new_emails_phase2": new_emails_phase2,
            "new_websites": new_websites,
            "brave_queries_used": website_finder.brave.queries_used,
            "duration_minutes": round(duration / 60, 1),
        },
        "faculty": faculty_list
    }
    
    # Save output
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_path = f"{output_dir}/harvard_university_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"\n✓ JSON saved: {json_path}")
    
    # CSV
    import csv
    csv_path = f"{output_dir}/harvard_university_{timestamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "name", "h_index", "works_count", "cited_by_count",
            "email", "email_source", "email_confidence",
            "website", "website_source",
            "research_topics", "orcid", "openalex_id"
        ])
        
        for fac in faculty_list:
            research = fac.get("research", {})
            email = fac.get("email", {})
            website = fac.get("website", {})
            
            writer.writerow([
                fac["name"],
                fac.get("h_index", 0),
                fac.get("works_count", 0),
                fac.get("cited_by_count", 0),
                email.get("value", ""),
                email.get("source", ""),
                email.get("confidence", ""),
                website.get("value", ""),
                website.get("source", ""),
                "; ".join([t.get("name", "") for t in research.get("topics", [])[:5]]),
                fac.get("orcid", ""),
                fac.get("openalex_id", ""),
            ])
    
    logger.info(f"✓ CSV saved: {csv_path}")
    
    return result

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Faculty Pipeline v4.5.1 - Restore & Enhance")
    parser.add_argument("--input", "-i", required=True, help="Path to v4.4 JSON output file")
    parser.add_argument("--output", "-o", default="output", help="Output directory")
    parser.add_argument("--api-key", help="Brave API key (or set BRAVE_API_KEY env var)")
    parser.add_argument("--skip-new-websites", action="store_true", help="Skip finding new websites")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--log-file", help="Log file path")
    
    args = parser.parse_args()
    
    result = restore_and_enhance(
        input_path=args.input,
        output_dir=args.output,
        api_key=args.api_key,
        skip_new_websites=args.skip_new_websites,
        verbose=args.verbose,
        log_file=args.log_file,
    )
    
    meta = result["metadata"]
    print("\n" + "=" * 60)
    print("RESTORE & ENHANCE COMPLETE - v4.5.1")
    print("=" * 60)
    print(f"Faculty: {meta['total_faculty']}")
    print(f"Websites: {meta['websites_found']} ({meta['website_coverage']*100:.1f}%)")
    print(f"Emails: {meta['emails_found']} ({meta['email_coverage']*100:.1f}%)")
    print(f"  - New emails (re-extraction): {meta['new_emails_phase1']}")
    print(f"  - New emails (new websites): {meta['new_emails_phase2']}")
    print(f"Brave queries: {meta['brave_queries_used']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
