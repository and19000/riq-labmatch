#!/usr/bin/env python3
"""
Faculty Data Pipeline v4.5 - Maximum Email Extraction

IMPROVEMENTS OVER v4.4:
1. Enhanced contact page discovery (+5-10% emails)
2. Improved name matching with fuzzy matching (+3-7% emails)
3. Better directory matching (+5-10% emails)
4. Harvard-specific site handling (skip connects.catalyst, etc.)
5. Fallback search queries for faculty without emails
6. Institution domain prioritization
7. All v4.4 checkpoint features preserved

EXPECTED COVERAGE:
- Websites: 90-95%
- Emails: 45-55% (up from 28.7%)

Usage:
    python faculty_pipeline_v4_5.py --institution harvard --max-faculty 600
    python faculty_pipeline_v4_5.py --institution harvard --resume

Author: RIQ LabMatch
Version: 4.5.0
"""

import os
import sys
import json
import csv
import re
import time
import logging
import argparse
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin, quote
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

INSTITUTIONS = {
    "harvard": {
        "name": "Harvard University",
        "openalex_id": "I136199984",
        "email_domains": [
            "harvard.edu", "hms.harvard.edu", "hsph.harvard.edu",
            "fas.harvard.edu", "hbs.edu", "dfci.harvard.edu",
            "mgh.harvard.edu", "bwh.harvard.edu", "childrens.harvard.edu",
            "broadinstitute.org", "dana-farber.org", "bidmc.harvard.edu",
            "meei.harvard.edu", "mclean.harvard.edu", "hsdm.harvard.edu",
            "massgeneral.org", "brighamandwomens.org", "mgh.org",
        ],
        "website_domain": "harvard.edu",
        "directories": [
            "https://chemistry.harvard.edu/people",
            "https://physics.harvard.edu/people/faculty",
            "https://psychology.fas.harvard.edu/people",
            "https://economics.harvard.edu/faculty",
            "https://sociology.fas.harvard.edu/people",
            "https://statistics.fas.harvard.edu/people",
            "https://gov.harvard.edu/people",
            "https://www.mcb.harvard.edu/directory/faculty/",
            "https://sysbio.med.harvard.edu/faculty",
        ],
        # Sites that never have emails - skip email extraction
        "skip_email_sites": [
            "connects.catalyst.harvard.edu",  # Never has emails
            "vcp.med.harvard.edu",  # Abstract pages only
        ],
        # Sites with hidden emails - try contact pages
        "contact_page_sites": [
            "hsph.harvard.edu",  # Emails hidden, try /contact
            "hms.harvard.edu",  # Some pages hide emails
        ],
    },
    "mit": {
        "name": "Massachusetts Institute of Technology",
        "openalex_id": "I63966007",
        "email_domains": ["mit.edu"],
        "website_domain": "mit.edu",
        "directories": [],
        "skip_email_sites": [],
        "contact_page_sites": [],
    },
    "stanford": {
        "name": "Stanford University",
        "openalex_id": "I97018004",
        "email_domains": ["stanford.edu"],
        "website_domain": "stanford.edu",
        "directories": [],
        "skip_email_sites": [],
        "contact_page_sites": [],
    },
}

# Thresholds
HIGH_VALUE_H_INDEX = 40
MEDIUM_VALUE_H_INDEX = 20
MIN_H_INDEX_FOR_EXTRACTION = 10
MAX_INSTITUTIONS = 15

# Rate limiting
BRAVE_DELAY = 0.6
SCRAPE_DELAY = 0.3
ORCID_DELAY = 0.2
MAX_RETRIES = 3

# Email extraction
MAX_CONTACT_PAGES = 7  # Increased from 5
EMAIL_SCRAPE_TIMEOUT = 15

# Checkpoint directory
CHECKPOINT_DIR = "checkpoints"

# Fuzzy matching threshold
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
    logging.getLogger("requests").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

class DataSource(str, Enum):
    OPENALEX = "openalex"
    WEBSITE = "website"
    SEARCH = "search"
    ORCID = "orcid"
    DIRECTORY = "directory"
    FALLBACK = "fallback"
    UNKNOWN = "unknown"

@dataclass
class ResearchProfile:
    topics: List[Dict[str, Any]] = field(default_factory=list)
    concepts: List[Dict[str, Any]] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    description: Optional[str] = None
    
    def to_dict(self):
        return {
            "topics": self.topics[:10],
            "concepts": self.concepts[:5],
            "fields": self.fields[:5],
            "keywords": self.keywords[:15],
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ResearchProfile':
        return cls(
            topics=data.get("topics", []),
            concepts=data.get("concepts", []),
            fields=data.get("fields", []),
            keywords=data.get("keywords", []),
            description=data.get("description"),
        )
    
    def get_summary(self) -> str:
        if self.topics:
            return "; ".join([t["name"] for t in self.topics[:5]])
        elif self.concepts:
            return "; ".join([c["name"] for c in self.concepts[:5]])
        return ""

@dataclass
class EmailData:
    value: Optional[str] = None
    source: DataSource = DataSource.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    extracted_from: Optional[str] = None
    extraction_method: Optional[str] = None
    name_match_score: float = 0.0
    
    def to_dict(self):
        return {
            "value": self.value,
            "source": self.source.value if isinstance(self.source, DataSource) else self.source,
            "confidence": self.confidence.value if isinstance(self.confidence, ConfidenceLevel) else self.confidence,
            "extracted_from": self.extracted_from,
            "extraction_method": self.extraction_method,
            "name_match_score": round(self.name_match_score, 2),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmailData':
        source = data.get("source", "unknown")
        if isinstance(source, str):
            try:
                source = DataSource(source)
            except ValueError:
                source = DataSource.UNKNOWN
        
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            try:
                confidence = ConfidenceLevel(confidence)
            except ValueError:
                confidence = ConfidenceLevel.UNKNOWN
        
        return cls(
            value=data.get("value"),
            source=source,
            confidence=confidence,
            extracted_from=data.get("extracted_from"),
            extraction_method=data.get("extraction_method"),
            name_match_score=data.get("name_match_score", 0.0),
        )

@dataclass
class WebsiteData:
    value: Optional[str] = None
    source: DataSource = DataSource.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    score: float = 0.0
    signals: List[str] = field(default_factory=list)
    page_type: str = "unknown"
    
    def to_dict(self):
        return {
            "value": self.value,
            "source": self.source.value if isinstance(self.source, DataSource) else self.source,
            "confidence": self.confidence.value if isinstance(self.confidence, ConfidenceLevel) else self.confidence,
            "score": round(self.score, 3),
            "signals": self.signals,
            "page_type": self.page_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WebsiteData':
        source = data.get("source", "unknown")
        if isinstance(source, str):
            try:
                source = DataSource(source)
            except ValueError:
                source = DataSource.UNKNOWN
        
        confidence = data.get("confidence", "unknown")
        if isinstance(confidence, str):
            try:
                confidence = ConfidenceLevel(confidence)
            except ValueError:
                confidence = ConfidenceLevel.UNKNOWN
        
        return cls(
            value=data.get("value"),
            source=source,
            confidence=confidence,
            score=data.get("score", 0.0),
            signals=data.get("signals", []),
            page_type=data.get("page_type", "unknown"),
        )

@dataclass
class FacultyMember:
    name: str
    openalex_id: Optional[str] = None
    orcid: Optional[str] = None
    institution: str = ""
    institution_id: Optional[str] = None
    h_index: int = 0
    i10_index: int = 0
    works_count: int = 0
    cited_by_count: int = 0
    research: ResearchProfile = field(default_factory=ResearchProfile)
    email: EmailData = field(default_factory=EmailData)
    website: WebsiteData = field(default_factory=WebsiteData)
    extraction_date: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    needs_review: bool = False
    review_notes: Optional[str] = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "openalex_id": self.openalex_id,
            "orcid": self.orcid,
            "institution": self.institution,
            "institution_id": self.institution_id,
            "h_index": self.h_index,
            "i10_index": self.i10_index,
            "works_count": self.works_count,
            "cited_by_count": self.cited_by_count,
            "research": self.research.to_dict(),
            "research_summary": self.research.get_summary(),
            "email": self.email.to_dict(),
            "website": self.website.to_dict(),
            "extraction_date": self.extraction_date,
            "needs_review": self.needs_review,
            "review_notes": self.review_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FacultyMember':
        return cls(
            name=data.get("name", ""),
            openalex_id=data.get("openalex_id"),
            orcid=data.get("orcid"),
            institution=data.get("institution", ""),
            institution_id=data.get("institution_id"),
            h_index=data.get("h_index", 0),
            i10_index=data.get("i10_index", 0),
            works_count=data.get("works_count", 0),
            cited_by_count=data.get("cited_by_count", 0),
            research=ResearchProfile.from_dict(data.get("research", {})),
            email=EmailData.from_dict(data.get("email", {})),
            website=WebsiteData.from_dict(data.get("website", {})),
            extraction_date=data.get("extraction_date", datetime.utcnow().isoformat()),
            needs_review=data.get("needs_review", False),
            review_notes=data.get("review_notes"),
        )

# ============================================================================
# CHECKPOINT MANAGER
# ============================================================================

class CheckpointManager:
    def __init__(self, checkpoint_dir: str, institution: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.institution = institution.lower().replace(" ", "_")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, phase: str) -> Path:
        return self.checkpoint_dir / f"{self.institution}_{phase}.json"
    
    def save(self, phase: str, data: Dict) -> None:
        path = self._get_path(phase)
        data["_checkpoint_meta"] = {
            "phase": phase,
            "timestamp": datetime.utcnow().isoformat(),
            "institution": self.institution,
            "version": "4.5.0",
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"✓ Checkpoint saved: {path.name}")
    
    def load(self, phase: str) -> Optional[Dict]:
        path = self._get_path(phase)
        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)
            logger.info(f"✓ Checkpoint loaded: {path.name}")
            return data
        return None
    
    def exists(self, phase: str) -> bool:
        return self._get_path(phase).exists()
    
    def get_latest_phase(self) -> Optional[str]:
        phases = ["phase3b_emails", "phase3a_orcid", "phase2b_websites", "phase2a_directories", "phase1_openalex"]
        for phase in phases:
            if self.exists(phase):
                return phase
        return None
    
    def clear(self) -> None:
        for path in self.checkpoint_dir.glob(f"{self.institution}_*.json"):
            path.unlink()
            logger.info(f"Deleted checkpoint: {path.name}")
    
    def save_faculty_list(self, phase: str, faculty_list: List[FacultyMember], extra_data: Dict = None) -> None:
        data = {"faculty": [f.to_dict() for f in faculty_list], "count": len(faculty_list)}
        if extra_data:
            data.update(extra_data)
        self.save(phase, data)
    
    def load_faculty_list(self, phase: str) -> Optional[List[FacultyMember]]:
        data = self.load(phase)
        if data and "faculty" in data:
            return [FacultyMember.from_dict(f) for f in data["faculty"]]
        return None

# ============================================================================
# FUZZY NAME MATCHING (NEW in v4.5)
# ============================================================================

class NameMatcher:
    """Enhanced name matching with fuzzy matching support."""
    
    # Common titles to remove
    TITLES = ['dr', 'prof', 'professor', 'mr', 'mrs', 'ms', 'phd', 'md', 'jr', 'sr', 'iii', 'ii', 'iv']
    
    @staticmethod
    def normalize(name: str) -> str:
        """Normalize a name for matching."""
        name = name.lower().strip()
        # Remove titles
        for title in NameMatcher.TITLES:
            name = re.sub(rf'\b{title}\.?\b', '', name)
        # Remove punctuation except hyphens
        name = re.sub(r'[^\w\s-]', ' ', name)
        # Normalize whitespace
        name = ' '.join(name.split())
        return name
    
    @staticmethod
    def get_name_parts(name: str) -> Dict[str, str]:
        """Extract name parts."""
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
    def generate_variations(name: str) -> List[str]:
        """Generate multiple name variations for matching."""
        parts = NameMatcher.get_name_parts(name)
        first = parts["first"]
        last = parts["last"]
        middle = parts["middle"]
        
        variations = [
            parts["full"],
            f"{first} {last}",
            f"{last} {first}",
            f"{first[0]} {last}" if first else "",
            f"{first[0]}{last}" if first else "",
            f"{last}",
            f"{first}",
        ]
        
        # Handle middle name/initial
        if middle:
            mid_init = middle[0] if middle else ""
            variations.extend([
                f"{first} {middle} {last}",
                f"{first} {mid_init} {last}",
                f"{first[0]} {mid_init} {last}" if first else "",
            ])
        
        # Handle hyphenated names
        if '-' in last:
            variations.append(last.split('-')[0])
            variations.append(last.split('-')[-1])
        
        return [v.strip() for v in variations if v.strip()]
    
    @staticmethod
    def fuzzy_match(name1: str, name2: str) -> float:
        """Calculate fuzzy match score between two names."""
        norm1 = NameMatcher.normalize(name1)
        norm2 = NameMatcher.normalize(name2)
        
        # Exact match
        if norm1 == norm2:
            return 1.0
        
        # Check if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            return 0.9
        
        # Sequence matcher
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    @staticmethod
    def match_email_to_name(email: str, faculty_name: str) -> float:
        """Score how well an email matches a faculty name."""
        if not email or not faculty_name:
            return 0.0
        
        local_part = email.lower().split('@')[0]
        parts = NameMatcher.get_name_parts(faculty_name)
        first = parts["first"]
        last = parts["last"]
        
        score = 0.0
        
        # Last name match (strong signal)
        if last and len(last) > 2 and last in local_part:
            score += 0.5
        
        # First name match
        if first and len(first) > 2 and first in local_part:
            score += 0.3
        
        # Common email patterns
        patterns = [
            f"{first[0]}{last}" if first else "",
            f"{first[0]}_{last}" if first else "",
            f"{first[0]}.{last}" if first else "",
            f"{last}{first[0]}" if first else "",
            f"{first}.{last}",
            f"{first}_{last}",
            f"{first}{last}",
            f"{last}.{first}",
            f"{last}_{first}",
        ]
        
        for pattern in patterns:
            if pattern and pattern in local_part:
                score += 0.2
                break
        
        # Fuzzy match on local part
        fuzzy_score = NameMatcher.fuzzy_match(local_part, f"{first}{last}")
        if fuzzy_score > 0.7:
            score += 0.1
        
        return min(score, 1.0)

# ============================================================================
# DENYLISTS
# ============================================================================

HARD_DENYLIST = [
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com", "tiktok.com", "youtube.com",
    "doi.org", "pubmed.ncbi.nlm.nih.gov", "arxiv.org", "biorxiv.org",
    "wikipedia.org", "amazon.com",
]

SOFT_DENYLIST = [
    "research.com", "researchgate.net", "academia.edu",
    "semanticscholar.org", "scholar.google.com", "aminer.org",
]

URL_PATTERN_DENYLIST = [
    "/login", "/signin", "/auth",
    "/course/", "/courses/",
    "/news/article", "/press-release",
    ".pdf", ".doc", ".ppt",
    "/search?", "/tag/", "/category/",
    "/event/",  # Event pages rarely have contact info
]

# Enhanced generic email patterns
GENERIC_EMAIL_PATTERNS = [
    r'^info@', r'^contact@', r'^admin@', r'^office@',
    r'^department@', r'^dept@', r'^general@', r'^inquiries@',
    r'^support@', r'^help@', r'^webmaster@', r'^web@',
    r'^communications@', r'^media@', r'^press@', r'^news@',
    r'^events@', r'^editor@', r'^subscribe@', r'^noreply@',
    r'^hr@', r'^careers@', r'^admissions@', r'^registrar@',
    r'^alumni@', r'^development@', r'^giving@', r'^contedu@',
    r'^programs?@', r'^courses?@', r'^steppingstrong@',
    r'^statistics@', r'^math@', r'^chemistry@', r'^physics@',
    r'^biology@', r'^economics@', r'^psychology@', r'^sociology@',
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

# Enhanced contact link patterns
CONTACT_LINK_PATTERNS = [
    '/contact', '/about', '/email', '/bio', '/profile',
    '/cv', '/home', 'biography', 'personal',
    '/people/', '/faculty/', '/staff/', '/directory/',
    '/info', '/reach', '/connect',
    '?page=contact', '?view=contact', '?tab=contact',
]

# ============================================================================
# BRAVE SEARCH CLIENT
# ============================================================================

class BraveSearchClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.queries_used = 0
        self.queries_failed = 0
        self.rate_limit_hits = 0
        self.last_error = None
        self.quota_exhausted = False
    
    def check_quota(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "API key not set"
        result = self.search("test")
        if self.quota_exhausted:
            return False, "Quota exhausted (402 error)"
        if self.last_error:
            return False, self.last_error
        return True, "OK"
    
    def search(self, query: str) -> List[Dict]:
        if not self.api_key or self.quota_exhausted:
            return []
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": 10}
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 401:
                    self.last_error = "Invalid API key"
                    self.queries_failed += 1
                    return []
                
                if response.status_code == 402:
                    self.last_error = "Quota exhausted"
                    self.quota_exhausted = True
                    self.queries_failed += 1
                    logger.error("⚠️ Brave API quota exhausted!")
                    return []
                
                if response.status_code == 429:
                    self.rate_limit_hits += 1
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                self.queries_used += 1
                self.last_error = None
                
                data = response.json()
                return [
                    {"url": item.get("url", ""), "title": item.get("title", ""), "description": item.get("description", "")}
                    for item in data.get("web", {}).get("results", [])
                ]
            except requests.exceptions.Timeout:
                self.last_error = "Timeout"
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                self.last_error = str(e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
                else:
                    self.queries_failed += 1
                    return []
        
        self.queries_failed += 1
        return []

# ============================================================================
# ORCID EMAIL EXTRACTOR
# ============================================================================

class OrcidEmailExtractor:
    BASE_URL = "https://pub.orcid.org/v3.0"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "FacultyPipeline/4.5"})
        self.requests_made = 0
        self.emails_found = 0
    
    def _extract_orcid_id(self, orcid_url: str) -> Optional[str]:
        if not orcid_url:
            return None
        match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', orcid_url)
        return match.group(1) if match else None
    
    def get_email(self, orcid: str, faculty_name: str) -> Optional[EmailData]:
        orcid_id = self._extract_orcid_id(orcid)
        if not orcid_id:
            return None
        
        url = f"{self.BASE_URL}/{orcid_id}/email"
        
        try:
            response = self.session.get(url, timeout=10)
            self.requests_made += 1
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            for email_entry in data.get("email", []):
                email = email_entry.get("email", "")
                if email and "@" in email:
                    self.emails_found += 1
                    return EmailData(
                        value=email.lower(),
                        source=DataSource.ORCID,
                        confidence=ConfidenceLevel.HIGH,
                        extracted_from=f"https://orcid.org/{orcid_id}",
                        extraction_method="orcid_api",
                        name_match_score=1.0,
                    )
            return None
        except Exception as e:
            logger.debug(f"ORCID lookup failed: {e}")
            return None
    
    def extract_emails_batch(self, faculty_list: List[FacultyMember]) -> List[FacultyMember]:
        logger.info("=" * 60)
        logger.info("PHASE 3A: ORCID Email Lookup")
        logger.info("=" * 60)
        
        eligible = [f for f in faculty_list if f.orcid and not f.email.value]
        logger.info(f"Faculty with ORCID, needing email: {len(eligible)}")
        
        for i, faculty in enumerate(eligible):
            email_data = self.get_email(faculty.orcid, faculty.name)
            if email_data:
                faculty.email = email_data
                logger.info(f"  ✓ {faculty.name}: {email_data.value}")
            
            time.sleep(ORCID_DELAY)
            
            if (i + 1) % 100 == 0:
                logger.info(f"  Progress: {i+1}/{len(eligible)}, Found: {self.emails_found}")
        
        logger.info(f"\n✓ ORCID: {self.emails_found}/{len(eligible)} emails")
        return faculty_list

# ============================================================================
# DIRECTORY SCRAPER (Enhanced in v4.5)
# ============================================================================

class DirectoryScraper:
    def __init__(self, institution_config: Dict):
        self.institution_config = institution_config
        self.valid_domains = [d.lower() for d in institution_config["email_domains"]]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.email_cache: Dict[str, str] = {}
        self.website_cache: Dict[str, str] = {}
        self.name_matcher = NameMatcher()
    
    def _is_valid_email(self, email: str) -> bool:
        if not email:
            return False
        domain = email.lower().split('@')[-1]
        return any(domain == d or domain.endswith('.' + d) for d in self.valid_domains)
    
    def _scrape_directory(self, url: str) -> Dict[str, Dict[str, str]]:
        results = {}
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract mailto links
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if href.startswith('mailto:'):
                    email = href[7:].split('?')[0].strip().lower()
                    if self._is_valid_email(email):
                        parent = a.find_parent(['tr', 'div', 'li', 'article', 'section'])
                        if parent:
                            text = parent.get_text(separator=' ', strip=True)
                            words = text.split()[:6]
                            name_context = ' '.join(words)
                            norm_name = NameMatcher.normalize(name_context)
                            if norm_name and len(norm_name) > 3:
                                results[norm_name] = {"email": email}
            
            # Extract faculty containers
            for container in soup.find_all(['div', 'article', 'li', 'tr'], 
                                          class_=re.compile(r'faculty|person|profile|member|staff|people', re.I)):
                name_elem = container.find(['h2', 'h3', 'h4', 'a', 'strong'])
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    norm_name = NameMatcher.normalize(name)
                    
                    if norm_name and len(norm_name) > 3:
                        email_link = container.find('a', href=re.compile(r'^mailto:'))
                        if email_link:
                            email = email_link.get('href', '')[7:].split('?')[0].strip().lower()
                            if self._is_valid_email(email):
                                if norm_name not in results:
                                    results[norm_name] = {}
                                results[norm_name]["email"] = email
                        
                        for link in container.find_all('a', href=True):
                            href = link.get('href', '')
                            if any(p in href for p in ['/people/', '/faculty/', '/profile/', '/person/']):
                                full_url = urljoin(url, href)
                                if norm_name not in results:
                                    results[norm_name] = {}
                                results[norm_name]["website"] = full_url
                                break
            
            logger.debug(f"  Directory {url}: {len(results)} entries")
        except Exception as e:
            logger.debug(f"  Failed to scrape {url}: {e}")
        
        return results
    
    def scrape_all_directories(self) -> None:
        directories = self.institution_config.get("directories", [])
        if not directories:
            logger.info("No directories configured")
            return
        
        logger.info("=" * 60)
        logger.info("PHASE 2A: Directory Scraping")
        logger.info("=" * 60)
        logger.info(f"Directories: {len(directories)}")
        
        for i, url in enumerate(directories):
            logger.info(f"  [{i+1}/{len(directories)}] {url}")
            results = self._scrape_directory(url)
            
            for norm_name, data in results.items():
                if "email" in data:
                    self.email_cache[norm_name] = data["email"]
                if "website" in data:
                    self.website_cache[norm_name] = data["website"]
            
            time.sleep(SCRAPE_DELAY)
        
        logger.info(f"\n✓ Directory cache: {len(self.email_cache)} emails, {len(self.website_cache)} websites")
    
    def lookup_email(self, faculty_name: str) -> Optional[EmailData]:
        """Enhanced email lookup with fuzzy matching."""
        variations = NameMatcher.generate_variations(faculty_name)
        
        # Try exact matches first
        for variant in variations:
            if variant in self.email_cache:
                return EmailData(
                    value=self.email_cache[variant],
                    source=DataSource.DIRECTORY,
                    confidence=ConfidenceLevel.HIGH,
                    extracted_from="department_directory",
                    extraction_method="directory_exact_match",
                    name_match_score=1.0,
                )
        
        # Try fuzzy matching
        best_match = None
        best_score = 0.0
        
        for cached_name, email in self.email_cache.items():
            score = NameMatcher.fuzzy_match(faculty_name, cached_name)
            if score > best_score and score >= FUZZY_MATCH_THRESHOLD:
                best_score = score
                best_match = email
        
        if best_match:
            return EmailData(
                value=best_match,
                source=DataSource.DIRECTORY,
                confidence=ConfidenceLevel.MEDIUM,
                extracted_from="department_directory",
                extraction_method="directory_fuzzy_match",
                name_match_score=best_score,
            )
        
        return None
    
    def lookup_website(self, faculty_name: str) -> Optional[str]:
        variations = NameMatcher.generate_variations(faculty_name)
        for variant in variations:
            if variant in self.website_cache:
                return self.website_cache[variant]
        
        # Fuzzy match
        for cached_name, website in self.website_cache.items():
            if NameMatcher.fuzzy_match(faculty_name, cached_name) >= FUZZY_MATCH_THRESHOLD:
                return website
        
        return None
    
    def to_dict(self) -> Dict:
        return {"email_cache": self.email_cache, "website_cache": self.website_cache}
    
    def from_dict(self, data: Dict) -> None:
        self.email_cache = data.get("email_cache", {})
        self.website_cache = data.get("website_cache", {})

# ============================================================================
# WEBSITE FINDER (Enhanced in v4.5)
# ============================================================================

class WebsiteFinder:
    HOMEPAGE_KEYWORDS = [
        "publications", "research", "teaching", "cv", "curriculum vitae",
        "students", "lab", "group", "contact", "about", "bio", "projects",
    ]
    
    PERSONAL_PAGE_PATTERNS = [
        "/~", "/people/", "/faculty/", "/profile/", "/lab/", "/labs/",
        "/group/", "people.", "scholar.", "/person/", "/staff/",
    ]
    
    def __init__(self, institution_config: Dict, api_key: str):
        self.institution_config = institution_config
        self.brave = BraveSearchClient(api_key)
    
    def _is_hard_denied(self, url: str) -> bool:
        url_lower = url.lower()
        for denied in HARD_DENYLIST:
            if denied in url_lower:
                return True
        for pattern in URL_PATTERN_DENYLIST:
            if pattern in url_lower:
                return True
        return False
    
    def _classify_page_type(self, url: str) -> Tuple[str, float]:
        url_lower = url.lower()
        
        for domain in SOFT_DENYLIST:
            if domain in url_lower:
                return "aggregator", -0.4
        
        if any(p in url_lower for p in ['/pubs', '/publications/', '/papers/']):
            return "publications", -0.2
        
        if any(p in url_lower for p in self.PERSONAL_PAGE_PATTERNS):
            return "personal", 0.1
        
        inst_domain = self.institution_config.get("website_domain", "")
        if inst_domain and inst_domain in url_lower:
            return "department", 0.05
        
        return "unknown", 0.0
    
    def _score_result(self, result: Dict, name: str) -> Tuple[float, List[str], str]:
        url = result.get("url", "").lower()
        title = result.get("title", "").lower()
        description = result.get("description", "").lower()
        combined = f"{title} {description}"
        
        score = 0.0
        signals = []
        
        page_type, type_modifier = self._classify_page_type(url)
        score += type_modifier
        if type_modifier != 0:
            signals.append(f"type:{page_type}")
        
        # ENHANCED: Stronger institution domain bonus
        inst_domain = self.institution_config.get("website_domain", "")
        if inst_domain and inst_domain in url:
            score += 0.4  # Increased from 0.3
            signals.append("institution_domain")
        
        if ".edu" in url:
            score += 0.2
            signals.append("edu_domain")
        
        if "/~" in url:
            score += 0.35
            signals.append("tilde_url")
        elif any(p in url for p in ["/people/", "/faculty/", "/profile/"]):
            score += 0.2
            signals.append("profile_url")
        elif any(p in url for p in ["/lab/", "/labs/", "/group/"]):
            score += 0.15
            signals.append("lab_url")
        
        name_parts = NameMatcher.get_name_parts(name)
        last_name = name_parts["last"]
        first_name = name_parts["first"]
        
        if last_name and len(last_name) > 2:
            if last_name in url:
                score += 0.25
                signals.append("lastname_in_url")
            if last_name in title:
                score += 0.15
                signals.append("lastname_in_title")
        
        if first_name and len(first_name) > 2 and first_name in title:
            score += 0.1
            signals.append("firstname_in_title")
        
        if name.lower() in title:
            score += 0.2
            signals.append("fullname_in_title")
        
        kw_count = sum(1 for kw in self.HOMEPAGE_KEYWORDS if kw in combined)
        if kw_count >= 2:
            score += 0.1
            signals.append(f"keywords:{kw_count}")
        
        if url.rstrip('/').endswith(('/people', '/faculty', '/directory', '/staff')):
            score -= 0.3
            signals.append("generic_listing")
        
        return score, signals, page_type
    
    def _generate_queries(self, name: str, h_index: int) -> List[str]:
        queries = []
        domain = self.institution_config.get("website_domain", "")
        inst_name = self.institution_config.get("name", "")
        
        if domain:
            queries.append(f'"{name}" site:{domain}')
        
        if h_index >= HIGH_VALUE_H_INDEX:
            queries.append(f'"{name}" {inst_name} professor homepage')
            queries.append(f'"{name}" {inst_name} lab research group')
        
        return queries
    
    def find_website(self, faculty: FacultyMember) -> Optional[WebsiteData]:
        if self.brave.quota_exhausted:
            return None
        
        queries = self._generate_queries(faculty.name, faculty.h_index)
        
        all_results = []
        for query in queries:
            results = self.brave.search(query)
            if self.brave.quota_exhausted:
                break
            for i, result in enumerate(results):
                result['_rank'] = i + 1
                all_results.append(result)
            time.sleep(BRAVE_DELAY)
        
        if not all_results:
            return None
        
        seen = set()
        unique = []
        for r in all_results:
            url = r.get("url", "").lower().rstrip('/')
            if url not in seen:
                seen.add(url)
                unique.append(r)
        
        scored = []
        for result in unique:
            url = result.get("url", "")
            if self._is_hard_denied(url):
                continue
            
            score, signals, page_type = self._score_result(result, faculty.name)
            score += 0.05 * (10 - result.get('_rank', 10)) / 10
            
            scored.append({
                "url": url,
                "score": score,
                "signals": signals,
                "page_type": page_type,
            })
        
        if not scored:
            return None
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]
        
        if best["score"] < 0.15:
            return None
        
        if best["score"] >= 0.5:
            confidence = ConfidenceLevel.HIGH
        elif best["score"] >= 0.3:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW
        
        return WebsiteData(
            value=best["url"],
            source=DataSource.SEARCH,
            confidence=confidence,
            score=best["score"],
            signals=best["signals"],
            page_type=best["page_type"],
        )
    
    def find_websites_batch(self, faculty_list: List[FacultyMember], directory_scraper: Optional[DirectoryScraper] = None, max_queries: int = 5000) -> List[FacultyMember]:
        logger.info("=" * 60)
        logger.info("PHASE 2B: Website Discovery (Brave Search)")
        logger.info("=" * 60)
        
        has_quota, status = self.brave.check_quota()
        if not has_quota:
            logger.error(f"⚠️ Brave API check failed: {status}")
            return faculty_list
        
        logger.info("✓ Brave API quota available")
        
        if directory_scraper:
            cache_hits = 0
            for faculty in faculty_list:
                if not faculty.website.value:
                    cached = directory_scraper.lookup_website(faculty.name)
                    if cached:
                        faculty.website = WebsiteData(
                            value=cached,
                            source=DataSource.DIRECTORY,
                            confidence=ConfidenceLevel.HIGH,
                            score=1.0,
                            signals=["directory_cache"],
                            page_type="department",
                        )
                        cache_hits += 1
            logger.info(f"Directory cache hits: {cache_hits}")
        
        need_search = [f for f in faculty_list if not f.website.value]
        high_value = [f for f in need_search if f.h_index >= HIGH_VALUE_H_INDEX]
        medium_value = [f for f in need_search if MEDIUM_VALUE_H_INDEX <= f.h_index < HIGH_VALUE_H_INDEX]
        
        estimated_queries = len(high_value) * 3 + len(medium_value)
        logger.info(f"Faculty needing search: {len(high_value)} high + {len(medium_value)} medium")
        logger.info(f"Estimated queries: {estimated_queries}")
        
        if estimated_queries > max_queries:
            excess = estimated_queries - max_queries
            reduce_medium = min(excess, len(medium_value))
            medium_value = medium_value[:-reduce_medium] if reduce_medium > 0 else medium_value
        
        eligible = high_value + medium_value
        eligible.sort(key=lambda f: f.h_index, reverse=True)
        
        found = 0
        for i, faculty in enumerate(eligible):
            if self.brave.quota_exhausted:
                logger.warning(f"⚠️ Quota exhausted at {i}/{len(eligible)}")
                break
            
            tier = "HIGH" if faculty.h_index >= HIGH_VALUE_H_INDEX else "MED"
            logger.info(f"[{i+1}/{len(eligible)}] [{tier}] {faculty.name} (h={faculty.h_index})")
            
            website = self.find_website(faculty)
            
            if website:
                faculty.website = website
                found += 1
                logger.info(f"  ✓ {website.value}")
            else:
                logger.info(f"  ✗ No website found")
            
            if (i + 1) % 25 == 0:
                logger.info(f"\n--- Progress: {i+1}/{len(eligible)}, Found: {found}, Queries: {self.brave.queries_used} ---\n")
        
        total_with_website = sum(1 for f in faculty_list if f.website.value)
        logger.info(f"\n✓ Website discovery complete")
        logger.info(f"  Found: {total_with_website}/{len(faculty_list)} ({total_with_website/len(faculty_list)*100:.1f}%)")
        logger.info(f"  Brave queries: {self.brave.queries_used}")
        
        return faculty_list

# ============================================================================
# WEBSITE EMAIL EXTRACTOR (Enhanced in v4.5)
# ============================================================================

class WebsiteEmailExtractor:
    def __init__(self, institution_config: Dict):
        self.institution_config = institution_config
        self.valid_domains = [d.lower() for d in institution_config["email_domains"]]
        self.skip_email_sites = institution_config.get("skip_email_sites", [])
        self.contact_page_sites = institution_config.get("contact_page_sites", [])
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        self.emails_found = 0
        self.name_matcher = NameMatcher()
    
    def _should_skip_site(self, url: str) -> bool:
        """Check if site is known to never have emails."""
        url_lower = url.lower()
        for site in self.skip_email_sites:
            if site in url_lower:
                return True
        return False
    
    def _should_try_contact_page(self, url: str) -> bool:
        """Check if site typically hides emails and needs contact page lookup."""
        url_lower = url.lower()
        for site in self.contact_page_sites:
            if site in url_lower:
                return True
        return False
    
    def _is_generic_email(self, email: str) -> bool:
        email_lower = email.lower()
        for pattern in GENERIC_EMAIL_PATTERNS:
            if re.match(pattern, email_lower):
                return True
        return False
    
    def _is_valid_domain(self, email: str) -> bool:
        if not email:
            return False
        domain = email.lower().split('@')[1]
        return any(domain == d or domain.endswith('.' + d) for d in self.valid_domains)
    
    def _fetch_page(self, url: str) -> Optional[Tuple[str, BeautifulSoup]]:
        try:
            response = self.session.get(url, timeout=EMAIL_SCRAPE_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text, soup
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None
    
    def _extract_mailto(self, soup: BeautifulSoup) -> List[str]:
        emails = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0].strip()
                email = html.unescape(email).lower()
                if email:
                    emails.append(email)
        return list(set(emails))
    
    def _extract_regex(self, text: str) -> List[str]:
        return list(set([e.lower() for e in EMAIL_REGEX.findall(text)]))
    
    def _extract_obfuscated(self, text: str) -> List[str]:
        emails = []
        for pattern, replacement in OBFUSCATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    email = f"{match[0]}@{match[1]}.{match[2]}".lower()
                    emails.append(email)
        return list(set(emails))
    
    def _find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Enhanced contact page discovery."""
        contact_urls = []
        base_domain = urlparse(base_url).netloc
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').lower()
            text = a.get_text().lower()
            
            is_contact = any(p in href for p in CONTACT_LINK_PATTERNS)
            is_contact = is_contact or any(w in text for w in ['contact', 'email', 'reach', 'about me', 'bio'])
            
            if is_contact:
                full_url = urljoin(base_url, a.get('href', ''))
                parsed = urlparse(full_url)
                if base_domain in parsed.netloc and full_url != base_url:
                    contact_urls.append(full_url)
        
        # Also try common contact page patterns
        parsed_base = urlparse(base_url)
        base_path = parsed_base.path.rstrip('/')
        
        common_patterns = [
            f"{parsed_base.scheme}://{parsed_base.netloc}{base_path}/contact",
            f"{parsed_base.scheme}://{parsed_base.netloc}/contact",
            f"{parsed_base.scheme}://{parsed_base.netloc}{base_path}?tab=contact",
        ]
        
        for pattern_url in common_patterns:
            if pattern_url not in contact_urls:
                contact_urls.append(pattern_url)
        
        return list(set(contact_urls))[:MAX_CONTACT_PAGES]
    
    def _select_best_email(self, candidates: List[Tuple[str, str]], faculty_name: str) -> Optional[Tuple[str, str, float]]:
        valid = []
        for email, method in candidates:
            if not self._is_valid_domain(email):
                continue
            if self._is_generic_email(email):
                continue
            
            # Use enhanced name matching
            name_score = NameMatcher.match_email_to_name(email, faculty_name)
            method_boost = {"mailto": 0.3, "regex": 0.2, "obfuscated": 0.1, "contact_page": 0.15}.get(method, 0)
            total_score = name_score + method_boost
            
            # IMPROVED: Lower threshold for mailto links (high confidence source)
            min_score = 0.25 if method == "mailto" else 0.35
            if name_score >= min_score or total_score >= 0.4:
                valid.append((email, method, total_score))
        
        if not valid:
            return None
        
        valid.sort(key=lambda x: x[2], reverse=True)
        return valid[0]
    
    def extract_email(self, url: str, faculty_name: str) -> Optional[EmailData]:
        if not url:
            return None
        
        # Skip known bad sites
        if self._should_skip_site(url):
            logger.debug(f"  Skipping known no-email site: {url}")
            return None
        
        candidates = []
        
        result = self._fetch_page(url)
        if not result:
            return None
        
        text, soup = result
        
        for email in self._extract_mailto(soup):
            candidates.append((email, "mailto"))
        for email in self._extract_regex(text):
            candidates.append((email, "regex"))
        for email in self._extract_obfuscated(text):
            candidates.append((email, "obfuscated"))
        
        best = self._select_best_email(candidates, faculty_name)
        
        # Try contact pages if no good match or if site typically hides emails
        if not best or best[2] < 0.5 or self._should_try_contact_page(url):
            contact_pages = self._find_contact_pages(soup, url)
            
            for contact_url in contact_pages:
                time.sleep(0.2)
                result = self._fetch_page(contact_url)
                if result:
                    contact_text, contact_soup = result
                    for email in self._extract_mailto(contact_soup):
                        candidates.append((email, "contact_page"))
                    for email in self._extract_regex(contact_text):
                        candidates.append((email, "contact_page"))
                    
                    new_best = self._select_best_email(candidates, faculty_name)
                    if new_best and (not best or new_best[2] > best[2]):
                        best = new_best
                        if best[2] >= 0.6:
                            break
        
        if not best:
            best = self._select_best_email(candidates, faculty_name)
        
        if best:
            email, method, score = best
            self.emails_found += 1
            
            if score >= 0.6:
                confidence = ConfidenceLevel.HIGH
            elif score >= 0.4:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW
            
            return EmailData(
                value=email,
                source=DataSource.WEBSITE,
                confidence=confidence,
                extracted_from=url,
                extraction_method=method,
                name_match_score=score,
            )
        
        return None
    
    def extract_emails_batch(self, faculty_list: List[FacultyMember]) -> List[FacultyMember]:
        logger.info("=" * 60)
        logger.info("PHASE 3B: Website Email Extraction (Enhanced)")
        logger.info("=" * 60)
        
        eligible = [
            f for f in faculty_list
            if f.website.value and not f.email.value
            and f.website.page_type not in ["aggregator"]
        ]
        
        logger.info(f"Faculty with websites, needing emails: {len(eligible)}")
        
        for i, faculty in enumerate(eligible):
            email_data = self.extract_email(faculty.website.value, faculty.name)
            
            if email_data:
                faculty.email = email_data
                logger.info(f"  ✓ {faculty.name}: {email_data.value}")
            
            time.sleep(SCRAPE_DELAY)
            
            if (i + 1) % 50 == 0:
                logger.info(f"  Progress: {i+1}/{len(eligible)}, Found: {self.emails_found}")
        
        logger.info(f"\n✓ Website emails: {self.emails_found}/{len(eligible)}")
        return faculty_list

# ============================================================================
# FALLBACK EMAIL SEARCH (NEW in v4.5)
# ============================================================================

class FallbackEmailSearch:
    """Try additional search queries for faculty without emails."""
    
    def __init__(self, institution_config: Dict, brave_client: BraveSearchClient):
        self.institution_config = institution_config
        self.brave = brave_client
        self.valid_domains = [d.lower() for d in institution_config["email_domains"]]
        self.emails_found = 0
    
    def _is_valid_domain(self, email: str) -> bool:
        if not email:
            return False
        domain = email.lower().split('@')[1]
        return any(domain == d or domain.endswith('.' + d) for d in self.valid_domains)
    
    def search_email(self, faculty: FacultyMember) -> Optional[EmailData]:
        """Try email-specific search queries."""
        if self.brave.quota_exhausted:
            return None
        
        inst_name = self.institution_config.get("name", "")
        domain = self.institution_config.get("website_domain", "")
        
        # Try email-specific searches
        queries = [
            f'"{faculty.name}" email site:{domain}',
            f'"{faculty.name}" contact site:{domain}',
        ]
        
        for query in queries:
            results = self.brave.search(query)
            if self.brave.quota_exhausted:
                break
            
            for result in results:
                # Look for emails in title and description
                text = f"{result.get('title', '')} {result.get('description', '')}"
                emails = EMAIL_REGEX.findall(text)
                
                for email in emails:
                    email = email.lower()
                    if self._is_valid_domain(email):
                        name_score = NameMatcher.match_email_to_name(email, faculty.name)
                        if name_score >= 0.3:
                            self.emails_found += 1
                            return EmailData(
                                value=email,
                                source=DataSource.FALLBACK,
                                confidence=ConfidenceLevel.MEDIUM,
                                extracted_from=result.get('url', ''),
                                extraction_method="fallback_search",
                                name_match_score=name_score,
                            )
            
            time.sleep(BRAVE_DELAY)
        
        return None
    
    def search_emails_batch(self, faculty_list: List[FacultyMember], max_searches: int = 100) -> List[FacultyMember]:
        """Search for emails for faculty without emails."""
        logger.info("=" * 60)
        logger.info("PHASE 3C: Fallback Email Search (NEW)")
        logger.info("=" * 60)
        
        # Faculty with websites but no email (highest priority)
        eligible = [
            f for f in faculty_list
            if f.website.value and not f.email.value
        ][:max_searches]
        
        logger.info(f"Faculty eligible for fallback search: {len(eligible)}")
        
        for i, faculty in enumerate(eligible):
            if self.brave.quota_exhausted:
                logger.warning("Quota exhausted - stopping fallback search")
                break
            
            email_data = self.search_email(faculty)
            
            if email_data:
                faculty.email = email_data
                logger.info(f"  ✓ {faculty.name}: {email_data.value}")
            
            if (i + 1) % 25 == 0:
                logger.info(f"  Progress: {i+1}/{len(eligible)}, Found: {self.emails_found}")
        
        logger.info(f"\n✓ Fallback search: {self.emails_found}/{len(eligible)} emails")
        return faculty_list

# ============================================================================
# OPENALEX CLIENT
# ============================================================================

class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"
    
    def __init__(self, contact_email: str):
        self.contact_email = contact_email
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"FacultyPipeline/4.5 (mailto:{contact_email})"
        })
    
    def _request(self, url: str, params: Dict) -> Dict:
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise e
    
    def _parse_research_profile(self, author_data: Dict) -> ResearchProfile:
        profile = ResearchProfile()
        
        topics = author_data.get("topics", [])
        if topics:
            profile.topics = [
                {"name": t.get("display_name", ""), "score": round(t.get("score", 0), 3)}
                for t in topics[:15] if t.get("display_name")
            ]
        
        concepts = author_data.get("x_concepts", [])
        if concepts:
            profile.concepts = [
                {"name": c.get("display_name", ""), "level": c.get("level", 0), "score": round(c.get("score", 0), 3)}
                for c in concepts[:10] if c.get("display_name")
            ]
            profile.fields = [c.get("display_name", "") for c in concepts if c.get("level") == 0][:5]
        
        if profile.topics:
            profile.keywords = [t["name"] for t in profile.topics[:15]]
        elif profile.concepts:
            profile.keywords = [c["name"] for c in profile.concepts if c.get("level", 0) >= 1][:15]
        
        return profile
    
    def extract_faculty(self, institution_config: Dict, max_faculty: Optional[int] = None) -> List[FacultyMember]:
        institution_name = institution_config["name"]
        institution_id = institution_config["openalex_id"]
        
        logger.info("=" * 60)
        logger.info("PHASE 1: OpenAlex Extraction")
        logger.info("=" * 60)
        logger.info(f"Institution: {institution_name}")
        
        filter_param = f"last_known_institutions.id:{institution_id}"
        url = f"{self.BASE_URL}/authors"
        
        params = {"filter": filter_param, "per_page": 1}
        data = self._request(url, params)
        total = data.get("meta", {}).get("count", 0)
        logger.info(f"Total in OpenAlex: {total:,}")
        
        faculty_list = []
        page = 1
        
        while True:
            if max_faculty and len(faculty_list) >= max_faculty:
                break
            
            params = {"filter": filter_param, "per_page": 200, "page": page}
            
            try:
                data = self._request(url, params)
            except Exception as e:
                logger.error(f"API error: {e}")
                break
            
            results = data.get("results", [])
            if not results:
                break
            
            for author in results:
                if max_faculty and len(faculty_list) >= max_faculty:
                    break
                
                institutions = author.get("last_known_institutions", [])
                if not institutions:
                    continue
                
                primary_inst = institutions[0].get("display_name", "")
                inst_name_check = institution_name.split()[0]
                if inst_name_check not in primary_inst:
                    continue
                
                if len(institutions) > MAX_INSTITUTIONS:
                    continue
                
                summary = author.get("summary_stats", {})
                h_index = summary.get("h_index", 0) or 0
                works = author.get("works_count", 0) or 0
                
                if h_index < MIN_H_INDEX_FOR_EXTRACTION and works < 30:
                    continue
                
                research_profile = self._parse_research_profile(author)
                
                faculty = FacultyMember(
                    name=author.get("display_name", ""),
                    openalex_id=author.get("id"),
                    orcid=author.get("orcid"),
                    institution=institution_name,
                    institution_id=institution_id,
                    h_index=h_index,
                    i10_index=summary.get("i10_index", 0) or 0,
                    works_count=works,
                    cited_by_count=author.get("cited_by_count", 0) or 0,
                    research=research_profile,
                )
                faculty_list.append(faculty)
            
            logger.info(f"Page {page}: {len(faculty_list)} faculty")
            page += 1
            time.sleep(0.1)
            
            if page > 100:
                break
        
        faculty_list.sort(key=lambda f: f.h_index, reverse=True)
        
        logger.info(f"\n✓ Extracted {len(faculty_list)} faculty")
        if faculty_list:
            with_orcid = sum(1 for f in faculty_list if f.orcid)
            logger.info(f"  With ORCID: {with_orcid} ({with_orcid/len(faculty_list)*100:.1f}%)")
        
        return faculty_list

# ============================================================================
# MAIN PIPELINE
# ============================================================================

class FacultyPipeline:
    def __init__(self, contact_email: str, institution_key: str, brave_api_key: str, checkpoint_dir: str = CHECKPOINT_DIR):
        if institution_key not in INSTITUTIONS:
            raise ValueError(f"Unknown institution: {institution_key}")
        
        self.institution_key = institution_key
        self.institution_config = INSTITUTIONS[institution_key]
        self.brave_api_key = brave_api_key
        self.checkpoint_manager = CheckpointManager(checkpoint_dir, institution_key)
        
        self.openalex = OpenAlexClient(contact_email)
        self.directory_scraper = DirectoryScraper(self.institution_config)
        self.website_finder = WebsiteFinder(self.institution_config, brave_api_key)
        self.orcid_extractor = OrcidEmailExtractor()
        self.website_email_extractor = WebsiteEmailExtractor(self.institution_config)
        self.fallback_search = FallbackEmailSearch(self.institution_config, self.website_finder.brave)
    
    def run(
        self,
        max_faculty: Optional[int] = None,
        resume: bool = False,
        only_websites: bool = False,
        only_emails: bool = False,
        skip_directories: bool = False,
        skip_websites: bool = False,
        skip_orcid: bool = False,
        skip_emails: bool = False,
        skip_fallback: bool = False,
        clear_checkpoints: bool = False,
    ) -> Dict:
        start_time = time.time()
        institution_name = self.institution_config["name"]
        
        logger.info("=" * 70)
        logger.info(f"FACULTY PIPELINE v4.5 - {institution_name}")
        logger.info("=" * 70)
        logger.info(f"Resume mode: {resume}")
        logger.info("=" * 70)
        
        if clear_checkpoints:
            self.checkpoint_manager.clear()
        
        faculty_list = None
        
        run_phase1 = True
        run_phase2a = not skip_directories
        run_phase2b = not skip_websites
        run_phase3a = not skip_orcid
        run_phase3b = not skip_emails
        run_phase3c = not skip_fallback
        
        if resume or only_websites or only_emails:
            for phase in ["phase3b_emails", "phase3a_orcid", "phase2b_websites", "phase2a_directories", "phase1_openalex"]:
                faculty_list = self.checkpoint_manager.load_faculty_list(phase)
                if faculty_list:
                    logger.info(f"Resuming from {phase} with {len(faculty_list)} faculty")
                    
                    if phase == "phase3b_emails":
                        run_phase1 = run_phase2a = run_phase2b = run_phase3a = run_phase3b = False
                    elif phase == "phase3a_orcid":
                        run_phase1 = run_phase2a = run_phase2b = run_phase3a = False
                    elif phase == "phase2b_websites":
                        run_phase1 = run_phase2a = run_phase2b = False
                    elif phase == "phase2a_directories":
                        run_phase1 = run_phase2a = False
                        dir_data = self.checkpoint_manager.load("phase2a_directories")
                        if dir_data and "directory_data" in dir_data:
                            self.directory_scraper.from_dict(dir_data["directory_data"])
                    elif phase == "phase1_openalex":
                        run_phase1 = False
                    
                    break
            
            if not faculty_list:
                logger.warning("No checkpoint found - starting fresh")
                resume = False
        
        if only_websites:
            run_phase1 = run_phase2a = run_phase3a = run_phase3b = run_phase3c = False
            run_phase2b = True
        
        if only_emails:
            run_phase1 = run_phase2a = run_phase2b = run_phase3a = False
            run_phase3b = True
            run_phase3c = True
        
        # Phase 1: OpenAlex
        if run_phase1:
            faculty_list = self.openalex.extract_faculty(self.institution_config, max_faculty)
            if not faculty_list:
                return {"error": "No faculty extracted"}
            self.checkpoint_manager.save_faculty_list("phase1_openalex", faculty_list)
        
        # Phase 2A: Directory scraping
        if run_phase2a:
            self.directory_scraper.scrape_all_directories()
            
            dir_email_count = 0
            for faculty in faculty_list:
                if not faculty.email.value:
                    email_data = self.directory_scraper.lookup_email(faculty.name)
                    if email_data:
                        faculty.email = email_data
                        dir_email_count += 1
            logger.info(f"Directory email matches: {dir_email_count}")
            
            self.checkpoint_manager.save_faculty_list("phase2a_directories", faculty_list, {
                "directory_data": self.directory_scraper.to_dict()
            })
        
        # Phase 2B: Website discovery
        if run_phase2b:
            faculty_list = self.website_finder.find_websites_batch(
                faculty_list,
                directory_scraper=self.directory_scraper,
            )
            self.checkpoint_manager.save_faculty_list("phase2b_websites", faculty_list)
        
        # Phase 3A: ORCID
        if run_phase3a:
            faculty_list = self.orcid_extractor.extract_emails_batch(faculty_list)
            self.checkpoint_manager.save_faculty_list("phase3a_orcid", faculty_list)
        
        # Phase 3B: Website emails
        if run_phase3b:
            faculty_list = self.website_email_extractor.extract_emails_batch(faculty_list)
            self.checkpoint_manager.save_faculty_list("phase3b_emails", faculty_list)
        
        # Phase 3C: Fallback search (NEW)
        if run_phase3c and not self.website_finder.brave.quota_exhausted:
            faculty_list = self.fallback_search.search_emails_batch(faculty_list, max_searches=100)
        
        # Final stats
        duration = time.time() - start_time
        total = len(faculty_list)
        
        with_website = sum(1 for f in faculty_list if f.website.value)
        with_email = sum(1 for f in faculty_list if f.email.value)
        
        email_sources = Counter()
        for f in faculty_list:
            if f.email.value:
                src = f.email.source.value if isinstance(f.email.source, DataSource) else f.email.source
                email_sources[src] += 1
        
        high_conf_emails = sum(1 for f in faculty_list if f.email.confidence == ConfidenceLevel.HIGH)
        with_topics = sum(1 for f in faculty_list if f.research.topics)
        
        logger.info("\n" + "=" * 70)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total faculty: {total}")
        logger.info(f"Websites: {with_website} ({with_website/total*100:.1f}%)")
        logger.info(f"Emails: {with_email} ({with_email/total*100:.1f}%)")
        logger.info(f"  Sources: {dict(email_sources)}")
        logger.info(f"  High confidence: {high_conf_emails}")
        logger.info(f"Research topics: {with_topics} ({with_topics/total*100:.1f}%)")
        logger.info(f"Duration: {duration/60:.1f} minutes")
        logger.info(f"Brave queries: {self.website_finder.brave.queries_used}")
        
        return {
            "metadata": {
                "institution": institution_name,
                "date": datetime.utcnow().isoformat(),
                "version": "4.5.0",
                "total_faculty": total,
                "websites_found": with_website,
                "website_coverage": round(with_website/total, 3) if total > 0 else 0,
                "emails_found": with_email,
                "email_coverage": round(with_email/total, 3) if total > 0 else 0,
                "email_sources": dict(email_sources),
                "high_confidence_emails": high_conf_emails,
                "research_topics_coverage": round(with_topics/total, 3) if total > 0 else 0,
                "brave_queries_used": self.website_finder.brave.queries_used,
                "duration_minutes": round(duration/60, 1),
            },
            "faculty": [f.to_dict() for f in faculty_list]
        }
    
    def export(self, data: Dict, output_dir: str = "output"):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        institution_slug = self.institution_config["name"].lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_path = f"{output_dir}/{institution_slug}_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"✓ JSON: {json_path}")
        
        csv_path = f"{output_dir}/{institution_slug}_{timestamp}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "name", "h_index", "works_count", "cited_by_count",
                "email", "email_source", "email_confidence", "email_method",
                "website", "website_source", "website_confidence", "website_type",
                "fields", "research_topics", "orcid", "openalex_id"
            ])
            
            for fac in data["faculty"]:
                research = fac.get("research", {})
                email = fac.get("email", {})
                website = fac.get("website", {})
                
                writer.writerow([
                    fac["name"],
                    fac["h_index"],
                    fac["works_count"],
                    fac["cited_by_count"],
                    email.get("value", ""),
                    email.get("source", ""),
                    email.get("confidence", ""),
                    email.get("extraction_method", ""),
                    website.get("value", ""),
                    website.get("source", ""),
                    website.get("confidence", ""),
                    website.get("page_type", ""),
                    "; ".join(research.get("fields", [])),
                    "; ".join([t["name"] for t in research.get("topics", [])[:5]]),
                    fac.get("orcid", ""),
                    fac.get("openalex_id", ""),
                ])
        
        logger.info(f"✓ CSV: {csv_path}")
        return json_path, csv_path

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Faculty Pipeline v4.5 - Maximum Email Extraction")
    parser.add_argument("--institution", "-i", required=True, choices=list(INSTITUTIONS.keys()))
    parser.add_argument("--max-faculty", "-m", type=int, default=None)
    parser.add_argument("--output", "-o", type=str, default="output")
    parser.add_argument("--checkpoint-dir", type=str, default=CHECKPOINT_DIR)
    
    parser.add_argument("--resume", "-r", action="store_true")
    parser.add_argument("--only-websites", action="store_true")
    parser.add_argument("--only-emails", action="store_true")
    parser.add_argument("--clear-checkpoints", action="store_true")
    
    parser.add_argument("--skip-directories", action="store_true")
    parser.add_argument("--skip-websites", action="store_true")
    parser.add_argument("--skip-orcid", action="store_true")
    parser.add_argument("--skip-emails", action="store_true")
    parser.add_argument("--skip-fallback", action="store_true")
    
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--log-file", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    
    args = parser.parse_args()
    setup_logging(args.verbose, args.log_file)
    
    openalex_email = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not openalex_email:
        print("ERROR: Set OPENALEX_CONTACT_EMAIL environment variable")
        return 1
    
    brave_api_key = args.api_key or os.environ.get("BRAVE_API_KEY")
    if not brave_api_key:
        print("ERROR: Set BRAVE_API_KEY environment variable or use --api-key")
        return 1
    
    try:
        pipeline = FacultyPipeline(openalex_email, args.institution, brave_api_key, args.checkpoint_dir)
        
        results = pipeline.run(
            max_faculty=args.max_faculty,
            resume=args.resume,
            only_websites=args.only_websites,
            only_emails=args.only_emails,
            skip_directories=args.skip_directories,
            skip_websites=args.skip_websites,
            skip_orcid=args.skip_orcid,
            skip_emails=args.skip_emails,
            skip_fallback=args.skip_fallback,
            clear_checkpoints=args.clear_checkpoints,
        )
        
        if "error" not in results:
            pipeline.export(results, args.output)
            
            meta = results["metadata"]
            print("\n" + "=" * 60)
            print("PIPELINE COMPLETE - v4.5")
            print("=" * 60)
            print(f"Faculty: {meta['total_faculty']}")
            print(f"Websites: {meta['websites_found']} ({meta['website_coverage']*100:.1f}%)")
            print(f"Emails: {meta['emails_found']} ({meta['email_coverage']*100:.1f}%)")
            print(f"  Sources: {meta['email_sources']}")
            print(f"Brave queries: {meta['brave_queries_used']}")
            print(f"Duration: {meta['duration_minutes']} minutes")
            print("=" * 60)
        else:
            print(f"ERROR: {results['error']}")
            return 1
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
