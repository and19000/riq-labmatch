# RIQ Faculty Pipeline – Complete Cursor Implementation Prompt

> **What this is:** A single, complete specification for Cursor to implement an end-to-end faculty data pipeline. It integrates with the existing `riq-labmatch` codebase, preserves all existing code, and adds filtering, account rotation, reporting, and multi-university support.

---

## TABLE OF CONTENTS

1. [Existing Codebase Reference](#1-existing-codebase-reference)
2. [Execution Plan & Credit Budget](#2-execution-plan--credit-budget)
3. [Stage 0: Immediate Filter on Existing 1477 Harvard Data](#3-stage-0-immediate-filter)
4. [Stage 1: Account Rotation Layer](#4-stage-1-account-rotation)
5. [Stage 2: Post-Search Filtering & Canonicalization](#5-stage-2-filtering)
6. [Stage 3: University Configuration System](#6-stage-3-university-configs)
7. [Stage 4: Tavily Fallback Runner](#7-stage-4-tavily-fallback)
8. [Stage 5: Reporting System](#8-stage-5-reporting)
9. [Stage 6: Master Orchestrator](#9-stage-6-master-orchestrator)
10. [File Manifest](#10-file-manifest)
11. [Data Preservation Rules](#11-data-preservation-rules)
12. [Implementation Order](#12-implementation-order)

---

## 1. EXISTING CODEBASE REFERENCE

**CRITICAL: Do NOT rewrite any of these files. Extend them or build alongside them.**

### Repo structure (relevant parts):
```
riq-labmatch/
├── api_evaluation/
│   ├── evaluate.py                          # Gold-standard evaluation (ProfessorResult, load_gold_standard)
│   ├── extract_email.py                     # Email regex extraction + scoring heuristics
│   ├── gold_standard_harvard_full.csv       # 1,477 Harvard rows (INPUT)
│   ├── search_apis/
│   │   ├── base_search.py                   # BaseSearch ABC, SearchResult dataclass
│   │   ├── exa_search.py                    # ExaSearch (2 queries/prof, type="auto")
│   │   ├── tavily_search.py                 # TavilySearch wrapper
│   │   └── brave_search.py                  # BraveSearch wrapper
│   ├── exa/
│   │   ├── run_exa_until_credits.py         # Full run script (checkpoint/resume, --max-professors)
│   │   └── results_exa_until_credits/
│   │       ├── exa_results.json             # Structured results with page text
│   │       ├── exa_found.csv                # Flat CSV (what we filter)
│   │       └── checkpoint.json
│   └── results_affiliation_only/            # 80-prof comparison
├── data/
│   └── exa_harvard/
│       ├── exa_harvard_found.csv            # Copy of 1,477 Exa results
│       └── exa_manual_eval_80.csv           # 80-row manual eval sample
├── docs/
│   ├── exa_run.md
│   └── EXA_NEXT_STEPS_PLAN.md
└── faculty_pipeline/                        # Submodule (directory scraping, separate repo)
    └── output/
        └── harvard_affiliated_faculty.csv
```

### Existing ExaSearch (DO NOT MODIFY):
```python
# api_evaluation/search_apis/exa_search.py
class ExaSearch(BaseSearch):
    def __init__(self, api_key: str):
        self.client = Exa(api_key)
        self.query_count = 0

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        response = self.client.search(
            query=query, type="auto", num_results=num_results,
            contents={"text": {"max_characters": 5000}},
        )
        # ... returns List[SearchResult]

    def search_professor(self, name: str, affiliation: str, department: str = "") -> List[SearchResult]:
        results = []
        query1 = f"{name} {affiliation} professor profile"
        results.extend(self._safe_search(query1, 5))
        query2 = f"{name} {affiliation} faculty"
        if department:
            query2 = f"{name} {affiliation} {department} faculty"
        results.extend(self._safe_search(query2, 5))
        # deduplicate by URL, return up to 10 unique results
```

### Existing run_exa_until_credits.py (MODIFY MINIMALLY):
- Already has checkpoint/resume, --max-professors, --dry-run
- Loads gold CSV via `load_gold_standard()`
- For each professor: calls `ExaSearch.search_professor` + `extract_emails_from_results`
- Writes exa_results.json + exa_found.csv + checkpoint.json

### Existing extract_email.py (DO NOT MODIFY):
- Regex extraction from page content
- Filters generic addresses (info@, contact@, etc.)
- Scores: prefers .edu, boosts name-match in local part

### Existing CSV schemas:

**Input (gold_standard_harvard_full.csv):**
```
name, affiliation, department, gold_email, gold_website
```

**Output (exa_found.csv):**
```
name, affiliation, department, gold_email, gold_website, found_website, found_email, all_urls, all_emails
```
- `all_urls`: semicolon-separated, up to 10 URLs
- `all_emails`: semicolon-separated, up to 3 emails

---

## 2. EXECUTION PLAN & CREDIT BUDGET

### Available Credits
```
EXA:
  Account 1: [PARTIALLY OR FULLY USED from 1477 Harvard run]
  Account 2: [FRESH or partially used]
  Account 3: [FRESH]
  Each account = $10 free = ~2000 searches
  Each professor = 2 Exa queries (search_professor does 2 queries)
  So 1 account ≈ 1000 professors

TAVILY:
  Accounts 1-4: [ALL FRESH]
  Each account = 1000 free searches
  Total: 4000 searches
```

### Execution Phases (in order)

```
PHASE 1: Filter existing Harvard data (0 credits, immediate)
  - Input: data/exa_harvard/exa_harvard_found.csv (1,477 rows)
  - Run filter_results.py with harvard.json config
  - Output: data/exa_harvard/harvard_canonicalized.csv
  - Output: data/exa_harvard/harvard_needs_review.csv
  - Output: reports/harvard_filter_report.md
  - EXPECTED: ~70% complete, ~19% partial, ~11% needs_review

PHASE 2: Search remaining Harvard faculty (Exa)
  - Input: new faculty names from faculty_pipeline not yet in exa_found.csv
  - Deduplicate against already-processed names
  - Run Exa search with account rotation
  - Output: appended to exa_found.csv (or new file merged later)
  - Filter new results
  - Output: updated harvard_canonicalized.csv
  - Output: reports/harvard_phase2_report.md

PHASE 3: Search MIT faculty (Exa)
  - Input: MIT faculty CSV from faculty_pipeline
  - Run Exa search with account rotation
  - Output: data/exa_mit/mit_exa_found.csv
  - Filter with mit.json config
  - Output: data/exa_mit/mit_canonicalized.csv
  - Output: reports/mit_report.md

PHASE 4: Search Tufts faculty (Tavily primary, saves Exa credits)
  - Input: Tufts faculty CSV
  - Use Tavily as PRIMARY search (not Exa) — we have 4000 Tavily credits
  - Output: data/tavily_tufts/tufts_tavily_found.csv
  - Filter with tufts.json config
  - Output: data/tavily_tufts/tufts_canonicalized.csv
  - Output: reports/tufts_report.md

PHASE 5: Tavily fallback for missing emails (Harvard + MIT)
  - Input: harvard_canonicalized.csv + mit_canonicalized.csv
  - For rows with status='partial' and no email: run Tavily search
  - Merge results, re-filter
  - Output: updated canonicalized CSVs
  - Output: reports/tavily_fallback_report.md

PHASE 6: Final combined report
  - Output: reports/final_summary_report.md
  - Combined stats across all universities
  - Credit usage summary
  - Data quality metrics

STOP AFTER TUFTS — no more universities until more credits are available.
```

### Credit Budget Tracking
The pipeline MUST track and display credit usage at every stage:
```
After each phase, print and log:
  ┌──────────────────────────────────────────┐
  │ CREDIT USAGE REPORT                      │
  │                                          │
  │ Exa:                                     │
  │   Account 1: 2000/2000 (EXHAUSTED)       │
  │   Account 2: 1354/2000 (646 remaining)   │
  │   Account 3: 0/2000 (2000 remaining)     │
  │   Total remaining: 2646 searches         │
  │                                          │
  │ Tavily:                                  │
  │   Account 1: 800/1000 (200 remaining)    │
  │   Account 2: 0/1000 (1000 remaining)     │
  │   Account 3: 0/1000 (1000 remaining)     │
  │   Account 4: 0/1000 (1000 remaining)     │
  │   Total remaining: 3200 searches         │
  │                                          │
  │ Professors processed this phase: 523     │
  │ Total processed all phases: 2000         │
  │ Estimated remaining capacity: 1323 profs │
  └──────────────────────────────────────────┘
```

---

## 3. STAGE 0: IMMEDIATE FILTER ON EXISTING 1477 HARVARD DATA

### File: `api_evaluation/filter/filter_results.py`

This is the FIRST thing to implement and run. It takes the already-collected `exa_harvard_found.csv` and produces a clean, canonicalized output. **Zero API calls needed.**

```python
"""
Post-search filtering and canonicalization.

USAGE (run immediately on existing data):
  cd riq-labmatch
  python -m api_evaluation.filter.filter_results \
    --input data/exa_harvard/exa_harvard_found.csv \
    --config api_evaluation/filter/configs/harvard.json \
    --output data/exa_harvard/harvard_canonicalized.csv \
    --report reports/harvard_filter_report.md

Optional: include exa_results.json for department/phone extraction from page text:
  --exa-json api_evaluation/exa/results_exa_until_credits/exa_results.json

WHAT IT DOES:
  1. Reads exa_found.csv (same schema as existing output)
  2. For each professor:
     a. Scores & re-ranks all_urls → picks canonical_website
     b. Scores & re-ranks all_emails → picks canonical_email
     c. Infers department (3 strategies)
     d. Extracts phone number (if page text available)
     e. Infers email from name + school pattern (if still missing)
     f. Assigns confidence levels and status
  3. Writes:
     a. [output].csv — display database (excludes needs_review)
     b. [output]_full.csv — ALL rows including needs_review
     c. [output]_needs_review.csv — only needs_review rows
     d. [report].md — detailed filtering report

CRITICAL: This reads the SAME CSV format that run_exa_until_credits.py outputs.
No schema changes needed. The semicolon-separated all_urls and all_emails fields
are split and scored individually.
"""

import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime

# Import university config
# from api_evaluation.filter.university_config import UniversityConfig
# OR if running as module: from .university_config import UniversityConfig


def score_url(url: str, professor_name: str, config) -> int:
    """
    Score a URL for quality. Higher = better.

    SCORING TABLE:
      +100  Domain in config.primary_trusted_domains (e.g. harvard.edu, hbs.edu)
      +80   Domain in config.secondary_trusted_domains (partners.org, dana-farber.org)
      +40   Domain is any .edu
      +30   URL path contains profile pattern:
              /people/, /person/, /profile/, /faculty/, /directory/,
              /Profiles/, /bios/, /find-a-doctor/, /provider/, /team/, /member-detail
      +20   Professor's last name (lowercased, cleaned) appears in URL
      +10   Professor's first name appears in URL
      -50   Domain in config.rejected_domains (linkedin, wikipedia, scholar.google, etc.)
      -30   URL ends with .pdf
      -20   URL contains /search? or /results? (search results page, not a profile)

    NAME CLEANING for matching:
      - Remove periods, commas, hyphens
      - Split on whitespace
      - Filter out tokens ≤ 2 chars (initials) and suffixes (Jr, Sr, II, III, IV)
      - Last remaining token = last_name, first token = first_name
      - Lowercase everything
      - For accented characters: match both accented and unaccented versions
        e.g., "Hämäläinen" should match "hamalainen" in URL
    """
    pass  # implement


def score_email(email: str, professor_name: str, config) -> int:
    """
    Score an email for quality. Higher = better.

    SCORING TABLE:
      +100  Email domain contains any config.primary_trusted_domains
      +80   Email domain in config.secondary_trusted_domains
      +30   Email domain is any .edu
      +20   Professor's last name appears in email local part (before @)
      +10   Professor's first initial appears at start of local part
      -100  Email matches JUNK patterns (immediate disqualification):
              Domains: scispace.com, gmail.com, yahoo.com, hotmail.com, outlook.com,
                       aol.com, protonmail.com
              Prefixes: support@, contact@, info@, admin@, customer*, helpdesk*,
                        noreply, no-reply, webmaster@, sales@, press@, media@,
                        hr@, jobs@, careers@, privacy@, abuse@, postmaster@
              Also reject if the email domain is clearly a company/org that is NOT
              the university (e.g., clinicaloptions.com, ahip.org, copdfoundation.org)
      -50   Email local part doesn't contain ANY part of professor name AND domain
            is not a university — likely scraped page-owner email for wrong person

    IMPORTANT: This scoring works WITH the existing extract_email.py, not replacing it.
    extract_email.py does initial extraction. This does a SECOND pass to pick the canonical one.
    """
    pass  # implement


def infer_department(
    professor: dict,
    canonical_url: str,
    all_urls: list,
    page_texts: list,
    config
) -> str:
    """
    Three-strategy department inference. Returns first non-empty result.

    STRATEGY 1: Already present
      - Check professor['department'] from input CSV
      - If non-empty, return it immediately
      - 105/1477 Harvard professors already have departments

    STRATEGY 2: URL-based inference
      - Check canonical_url against config.url_to_department
      - Then check each URL in all_urls
      - Match is done by checking if any key in url_to_department appears in the URL
      - MATCH ORDER: check the most specific subdomains first
        e.g., check "bcmp.hms.harvard.edu" before "hms.harvard.edu"
        Sort url_to_department keys by length (longest first) to ensure specificity
      - This catches ~63% of Harvard professors

    STRATEGY 3: Page text extraction
      - Only if page_texts is provided (from exa_results.json)
      - Search for patterns (case-sensitive to avoid false matches):
        r'(?:Associate |Assistant |Full )?Professor of\s+([A-Z][A-Za-z\s&,]+?)(?:\.|,|\n|at\s|in the)'
        r'(?:Department|Division|School|Center|Institute|Program)\s+of\s+([A-Z][A-Za-z\s&]+?)(?:\.|,|\n|at\s|;)'
      - Clean the match: strip trailing whitespace, limit to 60 chars, remove trailing "and"
      - Return first match

    If all fail, return empty string.
    """
    pass  # implement


def extract_phone(page_texts: list, url: str, config) -> str:
    """
    Extract phone numbers from page text.

    ONLY extract from pages whose URL matches config.phone_extraction_domains.
    These are clinical/hospital directories where phone numbers are relevant and real.

    Regex: r'(?:Tel|Phone|Telephone|Office|Contact)?:?\s*(\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4})'
    Also try: r'(\d{3}\.\d{3}\.\d{4})'  (dot-separated format)

    Filter out:
      - Fax numbers (if preceded by "Fax" or "fax")
      - Numbers that look like dates or IDs

    Return first valid phone found, formatted as (XXX) XXX-XXXX.
    Return empty string if none found.
    """
    pass  # implement


def infer_email_from_name(name: str, url: str, config) -> tuple:
    """
    For professors with a trusted website but no email, construct likely email.

    Check if the canonical URL's domain matches any key in config.email_inference_patterns.
    If so, use the pattern to construct an email.

    Pattern templates:
      "{first_initial}{lastname}@domain" → e.g., wwillett@hsph.harvard.edu
      "{lastname}@domain"                → e.g., willett@seas.harvard.edu
      "{firstname}.{lastname}@domain"    → e.g., walter.willett@domain

    NAME PARSING:
      - Split name on whitespace
      - Remove: periods, commas
      - Filter out: single-char tokens (middle initials), suffixes (Jr, Sr, II, III, IV, MD, PhD)
      - first_name = first remaining token, lowercased
      - last_name = last remaining token, lowercased
      - first_initial = first_name[0]
      - Handle hyphens: keep them (e.g., "Martinez-Gonzalez" → "martinez-gonzalez")
      - Handle accented chars: normalize to ASCII for email (e.g., "ä" → "a")
        Use unicodedata.normalize('NFKD', ...).encode('ascii', 'ignore').decode()

    Returns: (email_string, "inferred") or ("", "none")
    """
    pass  # implement


def filter_and_canonicalize(input_csv, config, exa_json=None, output_csv=None, report_path=None):
    """
    Main entry point.

    STEPS:
    1. Load input CSV (same schema as exa_found.csv)
    2. Optionally load exa_results.json for page text access
    3. For each professor row:
       a. Parse all_urls (split on "; " or ";")
       b. Parse all_emails (split on "; " or ";")
       c. Score each URL → sort descending → pick best with score > 0
       d. Score each email → sort descending → pick best with score > 0
       e. Infer department
       f. Extract phone (if page text available)
       g. If no email but has trusted website → try email inference
       h. Determine confidence:
            website_confidence: "high" if score >= 100, "medium" if >= 40, "low" if > 0, "none"
            email_confidence: "high" if score >= 100, "medium" if >= 30, "inferred", "low" if > 0, "none"
       i. Determine status:
            "complete" if has canonical_website AND canonical_email
            "partial" if has one but not other
            "needs_review" if has neither
    4. Write THREE output CSVs:
       a. {output}.csv — rows where status != 'needs_review' (DISPLAY DATABASE)
       b. {output}_full.csv — ALL rows (for debugging and data preservation)
       c. {output}_needs_review.csv — only needs_review rows (for future manual work)
    5. Generate report (see REPORTING section)
    6. Print summary to console

    OUTPUT CSV COLUMNS:
      name, affiliation, department, canonical_website, website_confidence,
      canonical_email, email_confidence, phone, status,
      original_found_website, original_found_email, all_urls, all_emails

    NOTE: We PRESERVE the original found_website and found_email so we can always
    compare what Exa returned vs what our filter selected. all_urls and all_emails
    are also preserved for future re-filtering with updated configs.

    CLI:
      python -m api_evaluation.filter.filter_results \
        --input data/exa_harvard/exa_harvard_found.csv \
        --config api_evaluation/filter/configs/harvard.json \
        --output data/exa_harvard/harvard_canonicalized.csv \
        --exa-json api_evaluation/exa/results_exa_until_credits/exa_results.json \
        --report reports/harvard_filter_report.md
    """
    pass  # implement


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and canonicalize Exa/Tavily search results")
    parser.add_argument("--input", required=True, help="Path to exa_found.csv or tavily_found.csv")
    parser.add_argument("--config", required=True, help="Path to university config JSON")
    parser.add_argument("--output", required=True, help="Path for output CSV (display database)")
    parser.add_argument("--exa-json", default=None, help="Optional path to exa_results.json for page text")
    parser.add_argument("--report", default=None, help="Path for markdown report")
    args = parser.parse_args()

    from api_evaluation.filter.university_config import UniversityConfig
    config = UniversityConfig.from_json(args.config)
    filter_and_canonicalize(args.input, config, args.exa_json, args.output, args.report)
```

---

## 4. STAGE 1: ACCOUNT ROTATION LAYER

### File: `api_evaluation/search_apis/account_manager.py`

```python
"""
Multi-account credit manager for Exa and Tavily API keys.

DESIGN PRINCIPLES:
  - Wraps AROUND existing ExaSearch/TavilySearch — does NOT replace them
  - AccountManager creates ExaSearch(api_key=current_key) instances
  - When current key exhausted → creates new instance with next key
  - Persists state to JSON so pipeline resumes cleanly across runs
  - Integrates with run_exa_until_credits.py's existing checkpoint system

INTERFACE:
```
class AccountManager:
    def __init__(self, provider: str, keys_file: str, state_file: str):
        """
        provider: "exa" or "tavily"
        keys_file: path to JSON with API keys (e.g., api_evaluation/keys/exa_keys.json)
        state_file: path to persist usage state (e.g., api_evaluation/state/account_state.json)
        """

    def get_search_client(self):
        """
        Returns an ExaSearch or TavilySearch instance using the current active key.
        If current key is within 10 credits of its limit, rotate to next.
        Raises AllAccountsExhausted if no keys remain.

        For Exa: returns ExaSearch(api_key=current_key)
        For Tavily: returns TavilySearch(api_key=current_key)
        """

    def record_queries(self, count: int):
        """
        Record that `count` queries were made on current account.
        Called AFTER a successful search_professor call.
        For Exa: count=2 (search_professor does 2 queries)
        For Tavily: count=1 or 2 depending on query strategy
        Persists state to disk immediately.
        """

    def get_status(self) -> dict:
        """
        Returns current state of all accounts:
        {
            "provider": "exa",
            "accounts": [
                {"label": "exa_1", "limit": 2000, "used": 847, "remaining": 1153, "active": True},
                {"label": "exa_2", "limit": 2000, "used": 0, "remaining": 2000, "active": False},
            ],
            "total_remaining": 3153,
            "current_account": "exa_1"
        }
        """

    def print_status(self):
        """Pretty-print current account status to console."""

    @property
    def total_remaining(self) -> int:
        """Total remaining credits across all accounts."""
```

### File: `api_evaluation/keys/exa_keys.json` (GITIGNORED)
```json
{
  "accounts": [
    {"api_key": "YOUR_EXA_KEY_1_HERE", "label": "exa_1", "credit_limit": 2000},
    {"api_key": "YOUR_EXA_KEY_2_HERE", "label": "exa_2", "credit_limit": 2000},
    {"api_key": "YOUR_EXA_KEY_3_HERE", "label": "exa_3", "credit_limit": 2000}
  ]
}
```

### File: `api_evaluation/keys/tavily_keys.json` (GITIGNORED)
```json
{
  "accounts": [
    {"api_key": "YOUR_TAVILY_KEY_1_HERE", "label": "tavily_1", "credit_limit": 1000},
    {"api_key": "YOUR_TAVILY_KEY_2_HERE", "label": "tavily_2", "credit_limit": 1000},
    {"api_key": "YOUR_TAVILY_KEY_3_HERE", "label": "tavily_3", "credit_limit": 1000},
    {"api_key": "YOUR_TAVILY_KEY_4_HERE", "label": "tavily_4", "credit_limit": 1000}
  ]
}
```

### File: `api_evaluation/state/account_state.json` (auto-generated, GITIGNORED)
```json
{
  "exa": {
    "current_account_idx": 0,
    "accounts": {
      "exa_1": {"used": 0},
      "exa_2": {"used": 0},
      "exa_3": {"used": 0}
    }
  },
  "tavily": {
    "current_account_idx": 0,
    "accounts": {
      "tavily_1": {"used": 0},
      "tavily_2": {"used": 0},
      "tavily_3": {"used": 0},
      "tavily_4": {"used": 0}
    }
  }
}
```

### Modification to `run_exa_until_credits.py` (MINIMAL CHANGE):

```python
# BEFORE (existing):
# api = ExaSearch(api_key=os.getenv("EXA_API_KEY"))

# AFTER (add AccountManager support):
# If --use-account-manager flag is passed:
#   manager = AccountManager("exa", "keys/exa_keys.json", "state/account_state.json")
#   api = manager.get_search_client()
#   # After each professor: manager.record_queries(2)
#   # If AllAccountsExhausted: save checkpoint, print remaining work, exit
# Else: use original single-key behavior (backward compatible)
```

The existing checkpoint/resume logic in run_exa_until_credits.py continues to work.
AccountManager just replaces HOW the API key is selected.

---

## 5. STAGE 2: FILTERING (detailed above in Stage 0)

Already fully specified in Stage 0. The filter module lives at:
```
api_evaluation/filter/
├── __init__.py
├── filter_results.py      # Main script (CLI + programmatic)
├── university_config.py   # Config loader
└── configs/
    ├── harvard.json
    ├── mit.json
    └── tufts.json
```

---

## 6. STAGE 3: UNIVERSITY CONFIGURATION SYSTEM

### File: `api_evaluation/filter/university_config.py`

```python
"""
University-specific configuration.

Each university = one JSON config file.
Adding a new university = adding a new JSON config. No code changes.

USAGE:
  config = UniversityConfig.from_json("api_evaluation/filter/configs/harvard.json")
  score = score_url(url, name, config)
"""

import json
from dataclasses import dataclass, field


@dataclass
class UniversityConfig:
    name: str                                    # "Harvard University"
    short_name: str                              # "harvard"
    primary_trusted_domains: list                # [harvard.edu, hbs.edu] — highest trust
    secondary_trusted_domains: list              # [partners.org, dana-farber.org] — affiliated
    rejected_domains: list                       # [linkedin.com, wikipedia.org] — always reject
    url_to_department: dict                      # {"hsph.harvard.edu": "School of Public Health"}
    email_inference_patterns: dict = field(default_factory=dict)  # {"hsph.harvard.edu": "{fi}{ln}@hsph.harvard.edu"}
    phone_extraction_domains: list = field(default_factory=list)  # ["massgeneralbrigham.org"]

    @classmethod
    def from_json(cls, path: str) -> "UniversityConfig":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    @property
    def all_trusted_domains(self) -> list:
        return self.primary_trusted_domains + self.secondary_trusted_domains
```

### File: `api_evaluation/filter/configs/harvard.json`

```json
{
  "name": "Harvard University",
  "short_name": "harvard",
  "primary_trusted_domains": [
    "harvard.edu",
    "hbs.edu"
  ],
  "secondary_trusted_domains": [
    "partners.org",
    "dana-farber.org",
    "massgeneralbrigham.org",
    "massgeneral.org",
    "brighamandwomens.org",
    "broadinstitute.org",
    "mcleanhospital.org",
    "joslin.org"
  ],
  "rejected_domains": [
    "linkedin.com",
    "scholar.google.com",
    "en.wikipedia.org",
    "scispace.com",
    "doximity.com",
    "researchgate.net",
    "semanticscholar.org",
    "amazon.com",
    "imdb.com",
    "ratemyprofessors.com"
  ],
  "url_to_department": {
    "hsph.harvard.edu": "Harvard T.H. Chan School of Public Health",
    "hms.harvard.edu": "Harvard Medical School",
    "dms.hms.harvard.edu": "Harvard Medical School",
    "hcp.hms.harvard.edu": "Harvard Medical School - Health Care Policy",
    "sleep.hms.harvard.edu": "Harvard Medical School - Sleep Medicine",
    "eye.hms.harvard.edu": "Harvard Medical School - Ophthalmology",
    "bcmp.hms.harvard.edu": "Harvard Medical School - Biological Chemistry & Molecular Pharmacology",
    "nutrition.hms.harvard.edu": "Harvard Medical School - Nutrition",
    "genetics.hms.harvard.edu": "Harvard Medical School - Genetics",
    "immunology.hms.harvard.edu": "Harvard Medical School - Immunology",
    "microbiology.hms.harvard.edu": "Harvard Medical School - Microbiology",
    "neuro.hms.harvard.edu": "Harvard Medical School - Neurobiology",
    "sysbio.hms.harvard.edu": "Harvard Medical School - Systems Biology",
    "cellbio.hms.harvard.edu": "Harvard Medical School - Cell Biology",
    "postgraduateeducation.hms.harvard.edu": "Harvard Medical School",
    "seas.harvard.edu": "Harvard John A. Paulson School of Engineering and Applied Sciences",
    "hbs.edu": "Harvard Business School",
    "hks.harvard.edu": "Harvard Kennedy School",
    "hls.harvard.edu": "Harvard Law School",
    "gsd.harvard.edu": "Harvard Graduate School of Design",
    "gse.harvard.edu": "Harvard Graduate School of Education",
    "hds.harvard.edu": "Harvard Divinity School",
    "fas.harvard.edu": "Faculty of Arts and Sciences",
    "physics.harvard.edu": "Department of Physics",
    "chemistry.harvard.edu": "Department of Chemistry and Chemical Biology",
    "math.harvard.edu": "Department of Mathematics",
    "stat.harvard.edu": "Department of Statistics",
    "econ.harvard.edu": "Department of Economics",
    "government.harvard.edu": "Department of Government",
    "psychology.fas.harvard.edu": "Department of Psychology",
    "mcb.harvard.edu": "Department of Molecular and Cellular Biology",
    "oeb.harvard.edu": "Department of Organismic and Evolutionary Biology",
    "brain.harvard.edu": "Center for Brain Science",
    "dfhcc.harvard.edu": "Dana-Farber/Harvard Cancer Center",
    "hsci.harvard.edu": "Harvard Stem Cell Institute",
    "dana-farber.org": "Dana-Farber Cancer Institute",
    "researchers.mgh.harvard.edu": "Massachusetts General Hospital",
    "massgeneral.org": "Massachusetts General Hospital",
    "brighamandwomens.org": "Brigham and Women's Hospital",
    "physiciandirectory.brighamandwomens.org": "Brigham and Women's Hospital",
    "bidmc.harvard.edu": "Beth Israel Deaconess Medical Center",
    "childrens.harvard.edu": "Boston Children's Hospital",
    "mcleanhospital.org": "McLean Hospital",
    "joslin.org": "Joslin Diabetes Center",
    "broadinstitute.org": "Broad Institute of MIT and Harvard",
    "english.fas.harvard.edu": "Department of English",
    "history.fas.harvard.edu": "Department of History",
    "philosophy.fas.harvard.edu": "Department of Philosophy",
    "sociology.fas.harvard.edu": "Department of Sociology",
    "anthropology.fas.harvard.edu": "Department of Anthropology",
    "music.fas.harvard.edu": "Department of Music",
    "aaas.fas.harvard.edu": "Department of African and African American Studies",
    "ealc.fas.harvard.edu": "Department of East Asian Languages and Civilizations",
    "complit.fas.harvard.edu": "Department of Comparative Literature",
    "linguistics.harvard.edu": "Department of Linguistics",
    "astronomy.fas.harvard.edu": "Department of Astronomy",
    "eps.harvard.edu": "Department of Earth and Planetary Sciences",
    "connects.catalyst.harvard.edu": "Harvard Catalyst Profiles"
  },
  "email_inference_patterns": {
    "hsph.harvard.edu": "{first_initial}{lastname}@hsph.harvard.edu",
    "seas.harvard.edu": "{lastname}@seas.harvard.edu",
    "fas.harvard.edu": "{lastname}@fas.harvard.edu",
    "hbs.edu": "{first_initial}{lastname}@hbs.edu",
    "hks.harvard.edu": "{lastname}@hks.harvard.edu",
    "physics.harvard.edu": "{lastname}@physics.harvard.edu",
    "chemistry.harvard.edu": "{lastname}@chemistry.harvard.edu",
    "math.harvard.edu": "{lastname}@math.harvard.edu",
    "econ.harvard.edu": "{lastname}@fas.harvard.edu",
    "government.harvard.edu": "{lastname}@fas.harvard.edu"
  },
  "phone_extraction_domains": [
    "massgeneralbrigham.org",
    "dana-farber.org",
    "doctors.massgeneralbrigham.org",
    "brighamandwomens.org",
    "physiciandirectory.brighamandwomens.org",
    "massgeneral.org",
    "childrens.harvard.edu",
    "bidmc.harvard.edu",
    "mcleanhospital.org"
  ]
}
```

### File: `api_evaluation/filter/configs/mit.json`

```json
{
  "name": "Massachusetts Institute of Technology",
  "short_name": "mit",
  "primary_trusted_domains": ["mit.edu"],
  "secondary_trusted_domains": [
    "broadinstitute.org",
    "ll.mit.edu",
    "lincoln.mit.edu",
    "draper.com",
    "whoi.edu"
  ],
  "rejected_domains": [
    "linkedin.com", "scholar.google.com", "en.wikipedia.org",
    "scispace.com", "doximity.com", "researchgate.net",
    "semanticscholar.org", "amazon.com", "ratemyprofessors.com"
  ],
  "url_to_department": {
    "csail.mit.edu": "Computer Science and Artificial Intelligence Laboratory",
    "eecs.mit.edu": "Electrical Engineering and Computer Science",
    "math.mit.edu": "Department of Mathematics",
    "physics.mit.edu": "Department of Physics",
    "chemistry.mit.edu": "Department of Chemistry",
    "cheme.mit.edu": "Department of Chemical Engineering",
    "meche.mit.edu": "Department of Mechanical Engineering",
    "cee.mit.edu": "Department of Civil and Environmental Engineering",
    "aeroastro.mit.edu": "Department of Aeronautics and Astronautics",
    "be.mit.edu": "Department of Biological Engineering",
    "biology.mit.edu": "Department of Biology",
    "bcs.mit.edu": "Department of Brain and Cognitive Sciences",
    "economics.mit.edu": "Department of Economics",
    "polisci.mit.edu": "Department of Political Science",
    "linguistics.mit.edu": "Department of Linguistics and Philosophy",
    "architecture.mit.edu": "Department of Architecture",
    "media.mit.edu": "MIT Media Lab",
    "lids.mit.edu": "Laboratory for Information and Decision Systems",
    "rle.mit.edu": "Research Laboratory of Electronics",
    "sloan.mit.edu": "MIT Sloan School of Management",
    "nse.mit.edu": "Department of Nuclear Science and Engineering",
    "dmse.mit.edu": "Department of Materials Science and Engineering",
    "imes.mit.edu": "Institute for Medical Engineering and Science",
    "lns.mit.edu": "Laboratory for Nuclear Science",
    "math.mit.edu": "Department of Mathematics",
    "oe.mit.edu": "Department of Ocean Engineering"
  },
  "email_inference_patterns": {
    "mit.edu": "{lastname}@mit.edu",
    "csail.mit.edu": "{lastname}@csail.mit.edu",
    "media.mit.edu": "{lastname}@media.mit.edu",
    "sloan.mit.edu": "{lastname}@mit.edu"
  },
  "phone_extraction_domains": []
}
```

### File: `api_evaluation/filter/configs/tufts.json`

```json
{
  "name": "Tufts University",
  "short_name": "tufts",
  "primary_trusted_domains": ["tufts.edu"],
  "secondary_trusted_domains": [
    "tuftsmedicalcenter.org",
    "medicine.tufts.edu",
    "nutrition.tufts.edu",
    "engineering.tufts.edu",
    "fletcher.tufts.edu",
    "dental.tufts.edu",
    "cummings.tufts.edu",
    "vet.tufts.edu"
  ],
  "rejected_domains": [
    "linkedin.com", "scholar.google.com", "en.wikipedia.org",
    "scispace.com", "doximity.com", "researchgate.net",
    "semanticscholar.org", "amazon.com", "ratemyprofessors.com"
  ],
  "url_to_department": {
    "as.tufts.edu": "School of Arts and Sciences",
    "engineering.tufts.edu": "School of Engineering",
    "medicine.tufts.edu": "School of Medicine",
    "dental.tufts.edu": "School of Dental Medicine",
    "nutrition.tufts.edu": "Friedman School of Nutrition Science and Policy",
    "fletcher.tufts.edu": "Fletcher School of Law and Diplomacy",
    "cummings.tufts.edu": "Cummings School of Veterinary Medicine",
    "vet.tufts.edu": "Cummings School of Veterinary Medicine",
    "cs.tufts.edu": "Department of Computer Science",
    "math.tufts.edu": "Department of Mathematics",
    "biology.tufts.edu": "Department of Biology",
    "chemistry.tufts.edu": "Department of Chemistry",
    "physics.tufts.edu": "Department of Physics and Astronomy",
    "ase.tufts.edu": "Department of Education",
    "go.tufts.edu": "Tufts University"
  },
  "email_inference_patterns": {
    "tufts.edu": "{firstname}.{lastname}@tufts.edu"
  },
  "phone_extraction_domains": [
    "tuftsmedicalcenter.org",
    "medicine.tufts.edu"
  ]
}
```

---

## 7. STAGE 4: TAVILY FALLBACK RUNNER

### File: `api_evaluation/tavily/run_tavily_fallback.py`

```python
"""
Tavily fallback: searches for emails for professors where Exa found none.

USAGE:
  python -m api_evaluation.tavily.run_tavily_fallback \
    --input data/exa_harvard/harvard_canonicalized_full.csv \
    --keys api_evaluation/keys/tavily_keys.json \
    --output data/exa_harvard/harvard_tavily_supplemented.csv

BEHAVIOR:
  1. Load the canonicalized CSV (output of filter_results.py)
  2. Filter to rows where canonical_email is empty AND status != 'needs_review'
  3. For each: run TavilySearch with 1 query: "{name} {affiliation} professor email contact"
  4. Extract emails from Tavily results using existing extract_email.py
  5. Score new emails using the same scoring from filter_results.py
  6. If a good email is found (score > 0), update the row
  7. Write updated CSV (preserving all original data + new tavily columns)
  8. Use AccountManager for Tavily key rotation

OUTPUT adds columns:
  tavily_email, tavily_email_confidence, tavily_urls (for audit trail)

Does NOT overwrite canonical_email if one already exists.
Only fills in blanks.

CREDIT USAGE:
  1 Tavily query per professor (only professors missing email)
  Expected: ~24% of total professors need this = ~350/1477 for Harvard
"""
```

### File: `api_evaluation/tavily/run_tavily_primary.py`

```python
"""
Tavily as PRIMARY search for universities where we want to save Exa credits.
Used for Tufts (Phase 4 of execution plan).

Same interface as run_exa_until_credits.py but uses TavilySearch.
Uses AccountManager for key rotation.

USAGE:
  python -m api_evaluation.tavily.run_tavily_primary \
    --input api_evaluation/gold_standard_tufts.csv \
    --keys api_evaluation/keys/tavily_keys.json \
    --output data/tavily_tufts/tufts_tavily_found.csv \
    --report reports/tufts_search_report.md

OUTPUT: Same CSV schema as exa_found.csv:
  name, affiliation, department, gold_email, gold_website,
  found_website, found_email, all_urls, all_emails

This ensures the filter_results.py can process Tavily output identically to Exa output.
"""
```

---

## 8. STAGE 5: REPORTING SYSTEM

### File: `api_evaluation/reports/generate_report.py`

Every phase generates a detailed markdown report. Reports are cumulative — the final report references all previous ones.

```python
"""
Report generator. Called by filter_results.py, run scripts, and master orchestrator.

REPORT TYPES:

1. FILTER REPORT (generated after filtering):
   - Input/output file paths
   - Timestamp
   - University name and config used
   - Total professors processed
   - Status breakdown: complete / partial / needs_review (count + %)
   - Website analysis:
     - Total with trusted website
     - Confidence distribution (high/medium/low/none)
     - Top 15 website domains found
     - URLs upgraded by re-ranking (from rejected → trusted)
     - URLs with profile-page patterns
   - Email analysis:
     - Total with trusted email
     - Confidence distribution (high/medium/low/inferred/none)
     - Top 15 email domains found
     - Junk emails removed (count + examples)
     - Emails inferred from name patterns
   - Department analysis:
     - Total departments filled
     - Breakdown by inference strategy (existing / URL / text / empty)
     - Top 15 departments by count
   - Phone analysis:
     - Total phones found
     - By domain source
   - Sample rows (5 complete, 5 partial, 5 needs_review)
   - Comparison: original found_website/found_email vs canonical (shows re-ranking effect)

2. SEARCH REPORT (generated after Exa/Tavily search run):
   - Total professors searched
   - API used (Exa/Tavily)
   - Credit usage per account
   - Search success rates (found any URL / found any email)
   - Average results per professor
   - Errors/timeouts encountered
   - Time elapsed
   - Checkpoint info (for resume)

3. CREDIT USAGE REPORT (generated at every phase boundary):
   - Per-account breakdown (Exa + Tavily)
   - Credits used this phase
   - Credits remaining
   - Estimated capacity for next phases
   - Warning if running low

4. FINAL SUMMARY REPORT (generated at end):
   - Per-university table:
     | University | Total | Complete | Partial | Needs Review | Dept Filled | Emails | Phones |
   - Combined totals
   - Credit usage summary
   - Data quality score per university
   - Recommendations for improvement
   - List of all output files produced

REPORT LOCATION: reports/ directory
  reports/
  ├── harvard_filter_report.md
  ├── harvard_phase2_search_report.md
  ├── harvard_phase2_filter_report.md
  ├── mit_search_report.md
  ├── mit_filter_report.md
  ├── tufts_search_report.md
  ├── tufts_filter_report.md
  ├── tavily_fallback_report.md
  ├── credit_usage_report.md
  └── final_summary_report.md
"""
```

---

## 9. STAGE 6: MASTER ORCHESTRATOR

### File: `api_evaluation/run_full_pipeline.py`

```python
"""
Master script that runs the entire pipeline end-to-end.
Can be run in phases (specify which phase to run).

USAGE:
  # Run everything:
  python -m api_evaluation.run_full_pipeline --all

  # Run specific phase:
  python -m api_evaluation.run_full_pipeline --phase 1  # Filter existing Harvard
  python -m api_evaluation.run_full_pipeline --phase 2  # Search remaining Harvard
  python -m api_evaluation.run_full_pipeline --phase 3  # Search MIT
  python -m api_evaluation.run_full_pipeline --phase 4  # Search Tufts (Tavily)
  python -m api_evaluation.run_full_pipeline --phase 5  # Tavily fallback
  python -m api_evaluation.run_full_pipeline --phase 6  # Final report

  # Check status without running anything:
  python -m api_evaluation.run_full_pipeline --status

PHASE DETAILS:

Phase 1 (0 credits):
  - Run filter_results.py on data/exa_harvard/exa_harvard_found.csv
  - Config: harvard.json
  - Output: data/exa_harvard/harvard_canonicalized.csv
  - Report: reports/harvard_filter_report.md

Phase 2 (Exa credits):
  - Load new Harvard names from faculty_pipeline (if available)
  - Deduplicate against already-processed names in exa_harvard_found.csv
  - Run Exa search with AccountManager
  - Append results to exa_harvard_found.csv (or create new file)
  - Run filter on combined data
  - Output: updated harvard_canonicalized.csv
  - Reports: harvard_phase2_search_report.md, harvard_phase2_filter_report.md

Phase 3 (Exa credits):
  - Input: MIT faculty CSV (must exist at api_evaluation/gold_standard_mit.csv
    OR faculty_pipeline/output/mit_faculty.csv)
  - Run Exa search with AccountManager
  - Output: data/exa_mit/mit_exa_found.csv
  - Run filter with mit.json
  - Output: data/exa_mit/mit_canonicalized.csv
  - Reports: mit_search_report.md, mit_filter_report.md

Phase 4 (Tavily credits):
  - Input: Tufts faculty CSV (must exist)
  - Run Tavily PRIMARY search with AccountManager
  - Output: data/tavily_tufts/tufts_tavily_found.csv
  - Run filter with tufts.json
  - Output: data/tavily_tufts/tufts_canonicalized.csv
  - Reports: tufts_search_report.md, tufts_filter_report.md

Phase 5 (Tavily credits):
  - Find all canonicalized CSVs with missing emails
  - Run Tavily fallback on those professors
  - Re-filter affected files
  - Report: tavily_fallback_report.md

Phase 6 (0 credits):
  - Generate final_summary_report.md combining all universities
  - Generate credit_usage_report.md

DEDUPLICATION (Phase 2):
  - Load existing exa_found.csv, extract all processed names
  - Load new faculty names
  - Normalize names for comparison (lowercase, remove accents, remove suffixes)
  - Only search names NOT already processed
  - Log: "X new professors found, Y already processed, Z duplicates skipped"

--status OUTPUT:
  Prints:
  - Which phases have been completed (checks for output files)
  - Credit status across all accounts
  - Estimated work remaining per phase
  - Next recommended action
"""
```

---

## 10. FILE MANIFEST

### New files to create:
```
api_evaluation/
├── filter/
│   ├── __init__.py
│   ├── filter_results.py           # Core filtering (Stage 0/2)
│   ├── university_config.py        # Config dataclass + loader
│   └── configs/
│       ├── harvard.json
│       ├── mit.json
│       └── tufts.json
├── search_apis/
│   └── account_manager.py          # Multi-key rotation (Stage 1)
├── keys/                           # GITIGNORED
│   ├── exa_keys.json
│   └── tavily_keys.json
├── state/                          # GITIGNORED (auto-generated)
│   └── account_state.json
├── tavily/
│   ├── run_tavily_fallback.py      # Email fallback (Stage 4)
│   └── run_tavily_primary.py       # Tavily as primary search
├── reports/
│   └── generate_report.py          # Report generation utilities
├── run_full_pipeline.py            # Master orchestrator (Stage 6)
data/
├── exa_harvard/                    # ALREADY EXISTS
│   ├── exa_harvard_found.csv       # ALREADY EXISTS (1477 rows)
│   ├── harvard_canonicalized.csv   # NEW (output of Phase 1)
│   ├── harvard_canonicalized_full.csv
│   └── harvard_needs_review.csv
├── exa_mit/                        # NEW
│   ├── mit_exa_found.csv
│   ├── mit_canonicalized.csv
│   └── mit_needs_review.csv
├── tavily_tufts/                   # NEW
│   ├── tufts_tavily_found.csv
│   ├── tufts_canonicalized.csv
│   └── tufts_needs_review.csv
reports/                            # NEW
├── harvard_filter_report.md
├── mit_search_report.md
├── mit_filter_report.md
├── tufts_search_report.md
├── tufts_filter_report.md
├── tavily_fallback_report.md
├── credit_usage_report.md
└── final_summary_report.md
```

### Files to modify (MINIMAL):
```
api_evaluation/exa/run_exa_until_credits.py   # Add --use-account-manager flag
.gitignore                                     # Add keys/ and state/ directories
```

### Files to NOT touch:
```
api_evaluation/evaluate.py
api_evaluation/extract_email.py
api_evaluation/search_apis/base_search.py
api_evaluation/search_apis/exa_search.py
api_evaluation/search_apis/tavily_search.py
api_evaluation/search_apis/brave_search.py
api_evaluation/gold_standard_*.csv
data/exa_harvard/exa_harvard_found.csv        # READ ONLY — never overwrite original
data/exa_harvard/exa_manual_eval_80.csv       # READ ONLY
```

---

## 11. DATA PRESERVATION RULES

**CRITICAL: Never lose data. Every transformation preserves the original.**

1. **Original Exa results are READ-ONLY.** `exa_harvard_found.csv` and `exa_results.json` are never modified. Filtering produces NEW files alongside them.

2. **Full output always saved.** Every filter run produces both a display CSV (excludes needs_review) AND a `_full.csv` (includes everything). The full file is the source of truth.

3. **Original fields preserved.** The canonicalized CSV includes `original_found_website` and `original_found_email` columns so you can always see what Exa returned vs what the filter selected. `all_urls` and `all_emails` are also preserved for re-filtering.

4. **Checkpoint after every professor.** Both Exa search runs and Tavily runs save progress after each professor. If the script crashes or credits run out, restart picks up where it left off.

5. **Account state persisted.** `state/account_state.json` tracks credit usage per API key. Never reset this unless deliberately starting fresh.

6. **Reports are timestamped.** Each report includes the generation timestamp and input file paths so you can trace exactly what data produced what report.

7. **Append, don't overwrite.** When Phase 2 adds new Harvard professors, results are appended to a new combined file, not overwritten on the original 1477-row file.

---

## 12. IMPLEMENTATION ORDER

Implement in this exact order. Each step should be testable independently.

```
STEP 1: University config system
  - Create university_config.py
  - Create harvard.json, mit.json, tufts.json
  - Test: load each config, verify fields

STEP 2: Filter module
  - Create filter_results.py with all scoring functions
  - Test on data/exa_harvard/exa_harvard_found.csv with harvard.json
  - Verify output CSV has correct columns
  - Verify needs_review rows are separated
  - Generate first report

STEP 3: Report generator
  - Create generate_report.py
  - Wire into filter_results.py
  - Generate harvard_filter_report.md
  - Verify report has all sections

STEP 4: Account manager
  - Create account_manager.py
  - Create keys JSON templates
  - Test with mock keys
  - Wire into run_exa_until_credits.py (behind --use-account-manager flag)

STEP 5: Tavily fallback
  - Create run_tavily_fallback.py
  - Test on a few Harvard professors with missing emails

STEP 6: Tavily primary
  - Create run_tavily_primary.py (for Tufts)
  - Test with small sample

STEP 7: Master orchestrator
  - Create run_full_pipeline.py
  - Implement --phase and --status
  - Test Phase 1 end-to-end

STEP 8: Run Phase 1 for real
  - Filter existing 1477 Harvard data
  - Review report
  - Commit results
```

---

## QUICK START (copy-paste into terminal after implementation)

```bash
# Phase 1: Filter existing Harvard data (FREE — no API credits)
cd riq-labmatch
python -m api_evaluation.filter.filter_results \
  --input data/exa_harvard/exa_harvard_found.csv \
  --config api_evaluation/filter/configs/harvard.json \
  --output data/exa_harvard/harvard_canonicalized.csv \
  --report reports/harvard_filter_report.md

# Check results
echo "=== Display database ==="
wc -l data/exa_harvard/harvard_canonicalized.csv
echo "=== Needs review ==="
wc -l data/exa_harvard/harvard_canonicalized_needs_review.csv
echo "=== Report ==="
cat reports/harvard_filter_report.md
```
