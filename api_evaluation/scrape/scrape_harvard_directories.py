#!/usr/bin/env python3
"""
Scrape faculty names from a set of Harvard directories.

For each directory URL, extract:
  - name
  - department/school (directory label)
  - title (if available; not currently stored in output CSV)

Output CSV schema (matching gold standard format):
  name, affiliation, department, gold_email, gold_website

Deduplication:
  - Within scraped results (same normalized name)
  - Against existing Data/exa_harvard/exa_harvard_found.csv (1477 already processed)

THIS SCRIPT DOES NOT CALL Exa OR Tavily.
"""

import argparse
import csv
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from api_evaluation.utils.deduplicate import _normalize_name


AFFILIATION = "Harvard University"
USER_AGENT = "riq-harvard-scraper/0.1 (+https://github.com/and19000/riq-labmatch)"
RATE_LIMIT_SECONDS = 2.0


@dataclass
class DirectorySpec:
    name: str
    url: str
    department: str


DIRECTORIES: List[DirectorySpec] = [
    # Schools
    DirectorySpec("HBS", "https://www.hbs.edu/faculty/Pages/browse.aspx", "Harvard Business School"),
    DirectorySpec("HLS", "https://hls.harvard.edu/faculty/", "Harvard Law School"),
    DirectorySpec("HKS", "https://www.hks.harvard.edu/faculty-research", "Harvard Kennedy School"),
    DirectorySpec("GSE", "https://gse.harvard.edu/directory", "Harvard Graduate School of Education"),
    DirectorySpec("GSD", "https://gsd.harvard.edu/people/", "Harvard Graduate School of Design"),
    DirectorySpec("HDS", "https://hds.harvard.edu/faculty", "Harvard Divinity School"),
    DirectorySpec("FAS", "https://fas.harvard.edu/people", "Faculty of Arts and Sciences"),
    DirectorySpec("SEAS", "https://seas.harvard.edu/faculty-research/faculty", "Harvard John A. Paulson School of Engineering and Applied Sciences"),
    # HMS preclinical
    DirectorySpec("Cell Biology", "https://cellbio.hms.harvard.edu/people", "Harvard Medical School - Cell Biology"),
    DirectorySpec("Genetics", "https://genetics.hms.harvard.edu/people", "Harvard Medical School - Genetics"),
    DirectorySpec("Immunology", "https://immunology.hms.harvard.edu/people", "Harvard Medical School - Immunology"),
    DirectorySpec("Microbiology", "https://microbiology.hms.harvard.edu/people", "Harvard Medical School - Microbiology"),
    DirectorySpec("Neurobiology", "https://neuro.hms.harvard.edu/people", "Harvard Medical School - Neurobiology"),
    DirectorySpec("Systems Biology", "https://sysbio.hms.harvard.edu/people", "Harvard Medical School - Systems Biology"),
    DirectorySpec("BCMP", "https://bcmp.hms.harvard.edu/people", "Harvard Medical School - Biological Chemistry & Molecular Pharmacology"),
    DirectorySpec("Health Care Policy", "https://hcp.hms.harvard.edu/people", "Harvard Medical School - Health Care Policy"),
    DirectorySpec("HMS Core Faculty", "https://hms.harvard.edu/faculty", "Harvard Medical School"),
    # FAS departments
    DirectorySpec("Physics", "https://www.physics.harvard.edu/people", "Department of Physics"),
    DirectorySpec("Chemistry", "https://www.chemistry.harvard.edu/people", "Department of Chemistry and Chemical Biology"),
    DirectorySpec("Mathematics", "https://www.math.harvard.edu/people/", "Department of Mathematics"),
    DirectorySpec("Statistics", "https://statistics.fas.harvard.edu/people", "Department of Statistics"),
    DirectorySpec("Economics", "https://economics.harvard.edu/people", "Department of Economics"),
    DirectorySpec("Government", "https://government.harvard.edu/people", "Department of Government"),
    DirectorySpec("Psychology", "https://psychology.fas.harvard.edu/people", "Department of Psychology"),
    DirectorySpec("MCB", "https://www.mcb.harvard.edu/directory/faculty/", "Department of Molecular and Cellular Biology"),
    DirectorySpec("OEB", "https://oeb.harvard.edu/people", "Department of Organismic and Evolutionary Biology"),
    DirectorySpec("History", "https://history.fas.harvard.edu/people", "Department of History"),
    DirectorySpec("English", "https://english.fas.harvard.edu/people", "Department of English"),
    DirectorySpec("Philosophy", "https://philosophy.fas.harvard.edu/people", "Department of Philosophy"),
    DirectorySpec("Sociology", "https://sociology.fas.harvard.edu/people", "Department of Sociology"),
    DirectorySpec("Anthropology", "https://anthropology.fas.harvard.edu/people", "Department of Anthropology"),
    DirectorySpec("Linguistics", "https://linguistics.harvard.edu/people", "Department of Linguistics"),
    DirectorySpec("Music", "https://music.fas.harvard.edu/people", "Department of Music"),
    DirectorySpec("AAAS", "https://aaas.fas.harvard.edu/people", "Department of African and African American Studies"),
    DirectorySpec("Earth & Planetary Sciences", "https://eps.harvard.edu/people", "Department of Earth and Planetary Sciences"),
    DirectorySpec("Astronomy", "https://astronomy.fas.harvard.edu/people", "Department of Astronomy"),
    # Centers / institutes
    DirectorySpec("Broad Institute", "https://www.broadinstitute.org/leadership-scientific-team", "Broad Institute of MIT and Harvard"),
    DirectorySpec("Center for Brain Science", "https://cbs.fas.harvard.edu/people", "Center for Brain Science"),
    DirectorySpec("Harvard Stem Cell Institute", "https://hsci.harvard.edu/people", "Harvard Stem Cell Institute"),
    DirectorySpec("Wyss Institute", "https://wyss.harvard.edu/team/", "Wyss Institute"),
]


def _domain_key(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def fetch_html(url: str, last_fetch_times: Dict[str, float]) -> Optional[str]:
    domain = _domain_key(url)
    now = time.time()
    last = last_fetch_times.get(domain, 0.0)
    elapsed = now - last
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        last_fetch_times[domain] = time.time()
        if resp.status_code != 200:
            print(f"WARNING: {url} returned status {resp.status_code}")
            return None
        return resp.text
    except Exception as e:
        print(f"ERROR: Failed to fetch {url}: {e}")
        return None


def _extract_names_generic(soup: BeautifulSoup) -> List[str]:
    """
    Generic heuristic: look for people cards or lists with recognizable name tags.
    This is intentionally loose; better to over-include and deduplicate later.
    """
    names: Set[str] = set()

    # Common patterns: headings or strong tags inside people cards
    for selector in [
        "h2", "h3", "h4", ".person-name", ".faculty-name", ".profile-name",
        ".views-field-title a", ".views-field-field-person a",
    ]:
        for el in soup.select(selector):
            text = el.get_text(" ", strip=True)
            if not text:
                continue
            names.add(text)

    return sorted(names)


def scrape_directory(spec: DirectorySpec, last_fetch_times: Dict[str, float]) -> Tuple[List[Dict], bool]:
    html = fetch_html(spec.url, last_fetch_times)
    if not html:
        print(f"NEEDS_SELENIUM: {spec.url} (no HTML or non-200 response)")
        return [], True

    soup = BeautifulSoup(html, "html.parser")
    raw_names = _extract_names_generic(soup)
    names: List[str] = []
    for name in raw_names:
        n = name.strip()
        if not n:
            continue
        # Reject if contains expand_more/expand_less
        lower = n.lower()
        if "expand_more" in lower or "expand_less" in lower:
            continue
        # Reject if starts with known non-person prefixes
        non_person_prefixes = (
            "administration",
            "clinical",
            "faculty",
            "students",
            "technology",
            "principal",
            "research",
        )
        if any(lower.startswith(p + " ") for p in non_person_prefixes):
            continue
        # Reject if single word
        if len(n.split()) < 2:
            continue
        # Reject if too long
        if len(n) > 60:
            continue
        names.append(n)
    if not names:
        print(f"NEEDS_SELENIUM: {spec.url} (no names detected)")
        return [], True

    rows: List[Dict] = []
    for name in names:
        rows.append(
            {
                "name": name,
                "affiliation": AFFILIATION,
                "department": spec.department,
                "gold_email": "",
                "gold_website": "",
                "source_url": spec.url,
            }
        )
    return rows, False


def _load_existing_names(existing_csv: str) -> Set[str]:
    existing: Set[str] = set()
    try:
        with open(existing_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                norm = _normalize_name(row.get("name", "") or row.get("Name", "") or "")
                if norm:
                    existing.add(norm)
    except FileNotFoundError:
        # No existing file yet
        pass
    return existing


def write_output_csv(path: str, rows: List[Dict]) -> None:
    if not rows:
        return
    fieldnames = ["name", "affiliation", "department", "gold_email", "gold_website"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "name": row["name"],
                    "affiliation": row["affiliation"],
                    "department": row["department"],
                    "gold_email": row.get("gold_email", ""),
                    "gold_website": row.get("gold_website", ""),
                }
            )


def write_report(path: str, per_dir_stats: Dict[str, Dict], total_new: int, total_ready: int) -> None:
    lines: List[str] = []
    lines.append("# Harvard Directory Scrape Report")
    lines.append("")
    lines.append(f"Total new professors not in existing 1477: **{total_new}**")
    lines.append(f"Total ready to search: **{total_ready}**")
    lines.append("")
    lines.append("## Per-directory summary")
    lines.append("")
    for key, stats in per_dir_stats.items():
        lines.append(
            f"- **{key}**: {stats['total']} faculty found "
            f"({stats['new']} new, {stats['existing']} already in existing)"
        )
    lines.append("")
    lines.append("Directories that likely need Selenium/JS rendering are logged as `NEEDS_SELENIUM` in stdout.")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Harvard faculty directories into gold_standard CSV format.")
    parser.add_argument(
        "--existing",
        default="Data/exa_harvard/exa_harvard_found.csv",
        help="Existing Exa Harvard CSV to deduplicate against.",
    )
    parser.add_argument(
        "--output",
        default="api_evaluation/gold_standard_harvard_remaining.csv",
        help="Output CSV path for remaining professors.",
    )
    parser.add_argument(
        "--report",
        default="reports/harvard_directory_scrape_report.md",
        help="Markdown report path.",
    )
    args = parser.parse_args()

    last_fetch_times: Dict[str, float] = {}
    existing_names = _load_existing_names(args.existing)

    all_rows: List[Dict] = []
    seen_norm_names: Set[str] = set()

    per_dir_stats: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "new": 0, "existing": 0})

    for spec in DIRECTORIES:
        print(f"Scraping {spec.name}: {spec.url}")
        rows, needs_selenium = scrape_directory(spec, last_fetch_times)
        if needs_selenium:
            per_dir_stats[spec.name]["total"] = 0
            per_dir_stats[spec.name]["new"] = 0
            per_dir_stats[spec.name]["existing"] = 0
            continue

        dir_total = len(rows)
        dir_new = 0
        dir_existing = 0

        for row in rows:
            norm = _normalize_name(row["name"])
            if not norm:
                continue
            if norm in seen_norm_names:
                # already captured from another directory
                dir_existing += 1
                continue
            seen_norm_names.add(norm)

            if norm in existing_names:
                dir_existing += 1
                continue

            dir_new += 1
            all_rows.append(row)

        per_dir_stats[spec.name]["total"] = dir_total
        per_dir_stats[spec.name]["new"] = dir_new
        per_dir_stats[spec.name]["existing"] = dir_existing

        print(f"{spec.name}: {dir_total} faculty found ({dir_new} new, {dir_existing} already in existing)")

    total_new = len(all_rows)
    total_ready = total_new  # same in this phase

    # Write outputs
    write_output_csv(args.output, all_rows)
    write_report(args.report, per_dir_stats, total_new, total_ready)

    print(f"Total new professors not in existing 1477: {total_new}")
    print(f"Total ready to search: {total_ready}")
    print(f"Output CSV: {args.output}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()

