"""
Load ALL NSF 2023, 2024, and 2025 awards into a single faculty database (FREE, file-based).

Expects your downloaded NSF data in one of:
  - ~/Documents/RIQ/2023, 2024, 2025  (or path from env NSFDATA_BASE / first CLI arg)
  - faculty_pipeline/nsf_data/2023, 2024, 2025
  - or nsf_data/*.json as fallback

Usage (from faculty_pipeline/):
  python scripts/load_all_nsf_data.py
  python scripts/load_all_nsf_data.py /Users/you/Documents/RIQ

Output: output/nsf_all_faculty.json
"""
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Paths relative to faculty_pipeline (parent of scripts/)
BASE = Path(__file__).resolve().parent.parent
# Default: check Documents/RIQ first, then nsf_data in repo
_DOCS_RIQ = Path.home() / "Documents" / "RIQ"
NSF_DATA_DIR = BASE / "nsf_data"
OUTPUT_FILE = BASE / "output" / "nsf_all_faculty.json"

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "been", "be", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "this", "that", "these", "those", "it", "its", "they", "their", "them", "we", "our",
    "you", "your", "he", "she", "his", "her", "which", "who", "whom", "what", "where",
    "when", "why", "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "same", "so", "than", "too", "very", "can",
    "just", "also", "now", "new", "one", "two", "first", "well", "way", "use", "used",
    "using", "work", "project", "research", "study", "studies", "develop", "developed",
    "program", "award", "nsf", "support", "supported", "provide", "provides", "include",
    "including", "based", "approach", "approaches", "understanding", "understand",
}


def extract_keywords_from_abstract(abstract, max_keywords=15):
    if not abstract:
        return []
    words = re.findall(r"\b[a-zA-Z]{4,}\b", abstract.lower())
    word_counts = defaultdict(int)
    for w in words:
        if w not in STOP_WORDS:
            word_counts[w] += 1
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_keywords]]


def get_research_field(award):
    """Infer field from award title/dir_abbr/fundProgramName."""
    title = (award.get("title") or award.get("awd_titl_txt") or "").upper()
    dir_abbr = (award.get("dir_abbr") or "").upper()
    fund = (award.get("fundProgramName") or "").upper()
    text = f"{title} {dir_abbr} {fund}"
    if "BIO" in text or "BIOLOG" in text or "LIFE" in text:
        return "Biology & Life Sciences"
    if "CISE" in text or "COMPUTER" in text or "CS" in text or "AI " in text:
        return "Computer Science & Engineering"
    if "ENG" in text or "ENGINEER" in text:
        return "Engineering"
    if "GEO" in text or "EARTH" in text or "ENVIRON" in text:
        return "Earth & Environmental Sciences"
    if "MPS" in text or "MATH" in text or "PHYSICS" in text or "CHEM" in text:
        return "Mathematics & Physical Sciences"
    if "SBE" in text or "SOCIAL" in text or "ECON" in text or "BEHAV" in text:
        return "Social & Behavioral Sciences"
    if "EDU" in text or "EDUCATION" in text:
        return "Education"
    return "Research"


def awards_from_file(filepath):
    """Yield award dicts from a single JSON file. Handles {awards: [...]}, list, or single award (id/awd_id)."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Skip {filepath.name}: {e}")
        return
    if isinstance(data, list):
        for a in data:
            if isinstance(a, dict):
                yield a
        return
    if isinstance(data, dict) and "awards" in data:
        for a in data["awards"]:
            if isinstance(a, dict):
                yield a
        return
    # Single award per file (NSF bulk export: awd_id, id, or award_number)
    if isinstance(data, dict) and (data.get("awd_id") or data.get("id") or data.get("award_number")):
        yield data


def pi_entries_from_award(award):
    """Yield (name, email, institution, research_field, keywords, amount, year) from one award."""
    abstract = award.get("abstractText") or award.get("abstract") or award.get("awd_abstract_narration") or ""
    keywords = extract_keywords_from_abstract(abstract)
    research_field = get_research_field(award)
    amount = award.get("awd_amount") or award.get("tot_intn_awd_amt") or award.get("estimatedTotalAmt") or 0
    try:
        amount = int(float(amount))
    except (TypeError, ValueError):
        amount = 0
    start = award.get("startDate") or award.get("awd_eff_date") or ""
    year = ""
    if start:
        m = re.search(r"20\d{2}", start)
        if m:
            year = m.group()
    org_name = award.get("org_name") or award.get("organization") or (award.get("inst") or [{}])[0].get("name", "") if isinstance(award.get("inst"), list) else ""

    # PI from award-level or pi[] array
    pis = award.get("pi") or []
    if isinstance(pis, dict):
        pis = [pis]
    if not pis and (award.get("piName") or award.get("pdPIName")):
        pis = [{
            "pi_full_name": award.get("piName") or award.get("pdPIName"),
            "pi_email_addr": award.get("pi_email_addr") or award.get("piEmail") or award.get("piEmailAddress"),
        }]

    for pi in pis:
        if not isinstance(pi, dict):
            continue
        name = (pi.get("pi_full_name") or "").strip()
        if not name:
            name = f"{pi.get('pi_first_name', '')} {pi.get('pi_last_name', '')}".strip()
        if not name or len(name) < 2:
            continue
        email = (pi.get("pi_email_addr") or pi.get("email") or "").strip().lower()
        if not email and award.get("pi_email_addr"):
            email = (award.get("pi_email_addr") or "").strip().lower()
        yield {
            "name": name,
            "email": email,
            "institution": org_name or award.get("awardeeName") or "",
            "research_field": research_field,
            "research_topics": [research_field] if research_field else [],
            "research_keywords": keywords,
            "nsf_awards": 1,
            "total_funding": amount,
            "award_year": year,
            "source": "nsf",
        }


def get_nsf_base():
    """Resolve base dir: CLI arg > NSFDATA_BASE env > Documents/RIQ if exists > nsf_data."""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1]).expanduser().resolve()
        if p.exists():
            return p
    env_base = os.environ.get("NSFDATA_BASE")
    if env_base:
        p = Path(env_base).expanduser().resolve()
        if p.exists():
            return p
    # Documents/RIQ or Documents/RIQ (with trailing space)
    for candidate in (_DOCS_RIQ, Path.home() / "Documents" / "RIQ "):
        if candidate.exists():
            return candidate
    return NSF_DATA_DIR


def collect_all_award_files(base_dir):
    """Collect all JSON paths from 2023/, 2024/, 2025/ (or 2024 (1), 2025 (1), etc.), then base/*.json."""
    paths = []
    if not base_dir.exists():
        return paths
    for sub in base_dir.iterdir():
        if sub.is_dir() and len(sub.name) >= 4 and sub.name[:4] in ("2023", "2024", "2025"):
            for p in sub.rglob("*.json"):
                paths.append(p)
    if not paths:
        for p in base_dir.glob("*.json"):
            paths.append(p)
    return paths


def main():
    base_dir = get_nsf_base()
    print("=" * 60)
    print("NSF Data Loader – 2023, 2024, 2025 awards (FREE, file-based)")
    print("=" * 60)
    print(f"  Base: {base_dir}")
    year_folders = [d.name for d in base_dir.iterdir() if d.is_dir() and d.name[:4] in ("2023", "2024", "2025")]
    for y in sorted(year_folders):
        print(f"  Using: {y}/")
    if not year_folders:
        print("  (No 2023/2024/2025 folders – using *.json in base)")
    print()

    all_entries = []
    file_paths = collect_all_award_files(base_dir)
    if not file_paths:
        print("ERROR: No JSON files found.")
        print("  Put NSF data in: Documents/RIQ/2023, 2024, 2025")
        print("  Or: nsf_data/2023, 2024, 2025  or  nsf_data/*.json")
        sys.exit(1)

    for path in sorted(file_paths):
        count = 0
        for award in awards_from_file(path):
            for entry in pi_entries_from_award(award):
                all_entries.append(entry)
                count += 1
        if count:
            try:
                rel = path.relative_to(base_dir)
            except ValueError:
                rel = path.name
            print(f"  {rel}: {count} PI entries")

    print(f"\nTotal PI entries (before dedup): {len(all_entries)}")

    # Deduplicate by name (merge counts and keywords)
    by_name = {}
    for e in all_entries:
        key = e["name"].lower().strip()
        if key not in by_name:
            by_name[key] = {
                "name": e["name"],
                "email": e["email"],
                "institution": e["institution"],
                "research_field": e["research_field"],
                "research_topics": list(set(e["research_topics"])),
                "research_keywords": list(e["research_keywords"]),
                "nsf_awards": e["nsf_awards"],
                "total_funding": e["total_funding"],
                "award_year": e.get("award_year", ""),
                "source": "nsf",
            }
        else:
            by_name[key]["nsf_awards"] += e["nsf_awards"]
            by_name[key]["total_funding"] += e["total_funding"]
            by_name[key]["research_keywords"] = list(set(by_name[key]["research_keywords"] + e["research_keywords"]))[:20]
            if e["email"] and not by_name[key]["email"]:
                by_name[key]["email"] = e["email"]
            if e["institution"] and not by_name[key]["institution"]:
                by_name[key]["institution"] = e["institution"]

    faculty = list(by_name.values())
    faculty.sort(key=lambda x: x["total_funding"], reverse=True)

    if not faculty:
        print("Total PIs (after dedup): 0 – no valid PI data extracted.")
        print("  Check that JSON files contain 'pi' array with pi_full_name / pi_email_addr.")
        sys.exit(1)
    with_email = sum(1 for f in faculty if f.get("email"))
    with_keywords = sum(1 for f in faculty if f.get("research_keywords"))
    print(f"Total PIs (after dedup): {len(faculty)}")
    print(f"  With email: {with_email} ({100 * with_email / len(faculty):.1f}%)")
    print(f"  With keywords: {with_keywords} ({100 * with_keywords / len(faculty):.1f}%)")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "metadata": {
            "source": "NSF Awards 2023-2025",
            "generated": datetime.now().isoformat(),
            "total_faculty": len(faculty),
            "with_email": with_email,
            "with_keywords": with_keywords,
        },
        "faculty": faculty,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
