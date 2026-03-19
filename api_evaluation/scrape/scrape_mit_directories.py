#!/usr/bin/env python3
"""
Scrape faculty names from MIT directory pages. Output: api_evaluation/inputs/mit_scraped.csv
Uses requests + BeautifulSoup; logs NEEDS_SELENIUM for directories that fail or return no names.
"""
import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from api_evaluation.scrape.name_validation import is_valid_scraped_name

AFFILIATION = "Massachusetts Institute of Technology"
USER_AGENT = "riq-scraper/0.1"
RATE_LIMIT_SECONDS = 2.0
OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "api_evaluation" / "inputs" / "mit_scraped.csv"


@dataclass
class DirSpec:
    label: str
    url: str
    department: str


DIRECTORIES: List[DirSpec] = [
    DirSpec("EECS", "https://www.eecs.mit.edu/people/faculty/", "Electrical Engineering and Computer Science"),
    DirSpec("Math", "https://math.mit.edu/directory/faculty.html", "Mathematics"),
    DirSpec("Physics", "https://physics.mit.edu/faculty/", "Physics"),
    DirSpec("Chemistry", "https://chemistry.mit.edu/faculty/", "Chemistry"),
    DirSpec("Biology", "https://biology.mit.edu/people/", "Biology"),
    DirSpec("Economics", "https://economics.mit.edu/people/faculty", "Economics"),
    DirSpec("Sloan", "https://sloan.mit.edu/faculty/directory", "MIT Sloan School of Management"),
    DirSpec("Architecture", "https://architecture.mit.edu/faculty", "Architecture"),
    DirSpec("CEE", "https://cee.mit.edu/people/faculty/", "Civil and Environmental Engineering"),
    DirSpec("MechE", "https://meche.mit.edu/people/faculty", "Mechanical Engineering"),
    DirSpec("BE", "https://be.mit.edu/people", "Biological Engineering"),
    DirSpec("DMSE", "https://dmse.mit.edu/people/faculty", "Materials Science and Engineering"),
]


def fetch_html(url: str, last_fetch: Dict[str, float]) -> Optional[str]:
    domain = url.split("/")[2].lower() if "/" in url else "default"
    now = time.time()
    if now - last_fetch.get(domain, 0) < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS)
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        last_fetch[domain] = time.time()
        if r.status_code in (403, 404):
            return None
        if r.status_code != 200:
            return None
        return r.text
    except Exception:
        return None


def _extract_names(soup: BeautifulSoup) -> List[str]:
    names = set()
    for sel in ["h2", "h3", "h4", ".person-name", ".faculty-name", ".profile-name", "a"]:
        for el in soup.select(sel):
            t = el.get_text(" ", strip=True)
            if t and " " in t and len(t) < 61:
                names.add(t)
    return sorted(names)


def scrape_one(spec: DirSpec, last_fetch: Dict[str, float]) -> Tuple[List[Dict], bool]:
    html = fetch_html(spec.url, last_fetch)
    if not html:
        print(f"NEEDS_SELENIUM: {spec.url}")
        return [], True
    soup = BeautifulSoup(html, "html.parser")
    raw = _extract_names(soup)
    rows = []
    for n in raw:
        if not is_valid_scraped_name(n):
            continue
        rows.append({
            "name": n.strip(),
            "affiliation": AFFILIATION,
            "department": spec.department,
            "gold_email": "",
            "gold_website": "",
        })
    if not rows:
        print(f"NEEDS_SELENIUM: {spec.url} (no names detected)")
        return [], True
    return rows, False


def main() -> None:
    last_fetch: Dict[str, float] = {}
    all_rows: List[Dict] = []
    seen = set()
    for spec in DIRECTORIES:
        print(f"Scraping {spec.label}: {spec.url}")
        rows, needs_selenium = scrape_one(spec, last_fetch)
        if needs_selenium:
            continue
        for r in rows:
            key = r["name"].lower().strip()
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(r)
        print(f"  {len(rows)} names")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "affiliation", "department", "gold_email", "gold_website"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"Total: {len(all_rows)} -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
