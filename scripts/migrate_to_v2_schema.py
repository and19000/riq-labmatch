#!/usr/bin/env python3
"""Migrate existing PI JSON data to v2 unified schema.

Reads all existing data sources (Harvard dept files, MIT enriched, per-school
working files, NSF active awards) and produces a single combined JSON file
plus per-school files in Data/v2/.

Usage:
    python scripts/migrate_to_v2_schema.py
"""

import json
import os
import sys
from datetime import date

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data")
MISC_DIR = os.path.join(DATA_DIR, "Misc jsons")
OUTPUT_DIR = os.path.join(DATA_DIR, "v2")

# Existing data paths
SCHOOL_WORKING_FILES = {
    "Harvard University": os.path.join(MISC_DIR, "faculty_working.json"),
    "MIT": os.path.join(MISC_DIR, "mit_faculty_working.json"),
    "Boston University": os.path.join(MISC_DIR, "boston_university_faculty_working.json"),
    "Northeastern University": os.path.join(MISC_DIR, "northeastern_university_faculty_working.json"),
    "Tufts University": os.path.join(MISC_DIR, "tufts_university_faculty_working.json"),
    "Stanford University": os.path.join(MISC_DIR, "stanford_university_faculty_working.json"),
    "Yale University": os.path.join(MISC_DIR, "yale_university_faculty_working.json"),
    "Princeton University": os.path.join(MISC_DIR, "princeton_university_faculty_working.json"),
}

HARVARD_DEPT_DIR = os.path.join(DATA_DIR, "Harvard")
MIT_DIR = os.path.join(DATA_DIR, "MIT")
NSF_PATH = os.path.join(MISC_DIR, "nsf_active.json")

# School directories with per-department files
SCHOOL_DEPT_DIRS = {
    "Boston University": os.path.join(DATA_DIR, "BU"),
    "Northeastern University": os.path.join(DATA_DIR, "Northeastern"),
    "Princeton University": os.path.join(DATA_DIR, "Princeton"),
    "Stanford University": os.path.join(DATA_DIR, "Stanford"),
    "Tufts University": os.path.join(DATA_DIR, "Tufts"),
    "Yale University": os.path.join(DATA_DIR, "Yale"),
}

# Canonical school name mapping
SCHOOL_NAME_MAP = {
    "harvard": "Harvard University",
    "harvard university": "Harvard University",
    "harvard medical school": "Harvard University",
    "broad institute": "Harvard University",
    "broad institute of mit and harvard": "Harvard University",
    "mit": "MIT",
    "massachusetts institute of technology": "MIT",
    "bu": "Boston University",
    "boston university": "Boston University",
    "northeastern": "Northeastern University",
    "northeastern university": "Northeastern University",
    "tufts": "Tufts University",
    "tufts university": "Tufts University",
    "stanford": "Stanford University",
    "stanford university": "Stanford University",
    "yale": "Yale University",
    "yale university": "Yale University",
    "princeton": "Princeton University",
    "princeton university": "Princeton University",
}

ENABLED_SCHOOLS = {
    "harvard university", "mit",
    "boston university", "northeastern university", "tufts university",
    "stanford university", "yale university", "princeton university",
}


def dept_field_key(department):
    """Map a department name to a broad field key."""
    if not department:
        return "default"
    d = department.lower()
    if any(k in d for k in ["computer", "computing", "informatics", "data science"]):
        return "cs"
    if any(k in d for k in ["engineer", "mechanical", "aerospace", "aeronautic", "nuclear", "biomedical eng", "biological eng"]):
        return "engineering"
    if any(k in d for k in ["biology", "biological", "biochem", "genetic", "molecular", "microbio", "agricultural"]):
        return "biology"
    if any(k in d for k in ["chemistry", "chemical"]):
        return "chemistry"
    if any(k in d for k in ["physics", "astro", "quantum"]):
        return "physics"
    if any(k in d for k in ["math", "statistic"]):
        return "math"
    if any(k in d for k in ["medicine", "medical", "health", "pharma", "nursing", "immuno"]):
        return "medicine"
    if any(k in d for k in ["neuro", "brain", "cognitive"]):
        return "neuro"
    if any(k in d for k in ["social", "politic", "sociology", "anthropo", "linguist", "psycho"]):
        return "social"
    if any(k in d for k in ["econom", "finance"]):
        return "economics"
    if any(k in d for k in ["material"]):
        return "materials"
    if any(k in d for k in ["earth", "planet", "geo", "ocean", "atmospher"]):
        return "earth"
    if any(k in d for k in ["business", "management", "account"]):
        return "business"
    if any(k in d for k in ["art", "music", "theater", "literature", "humanit", "history", "philosoph"]):
        return "arts"
    if any(k in d for k in ["environment", "ecology", "climate", "sustainab"]):
        return "env"
    if any(k in d for k in ["energy"]):
        return "energy"
    return "default"


def normalize_school(name):
    """Normalize school name to canonical form."""
    if not name:
        return ""
    return SCHOOL_NAME_MAP.get(name.lower().strip(), name.strip())


def safe_int(val):
    """Convert h_index to int, handling strings and None."""
    if val is None or val == "":
        return None
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def parse_techniques(val):
    """Parse lab_techniques into a list."""
    if isinstance(val, list):
        return [t.strip() for t in val if t and str(t).strip()]
    if isinstance(val, str) and val.strip():
        return [t.strip() for t in val.split(",") if t.strip()]
    return []


def parse_research_areas(val):
    """Normalize research_areas to a string."""
    if isinstance(val, list):
        # Filter out grant titles and overly long entries
        cleaned = []
        for item in val:
            s = str(item).strip()
            if s and len(s) < 200 and not s.startswith("Collaborative Research:"):
                cleaned.append(s)
        return "; ".join(cleaned[:10])
    if isinstance(val, str):
        return val.strip()
    return ""


def parse_topics(val):
    """Parse topics into a list."""
    if isinstance(val, list):
        return [str(t).strip() for t in val if t and str(t).strip()]
    if isinstance(val, str) and val.strip():
        # Split on semicolons or commas
        sep = ";" if ";" in val else ","
        return [t.strip() for t in val.split(sep) if t.strip()]
    return []


def normalize_email(val):
    """Normalize email to a string."""
    if isinstance(val, list):
        emails = [e.strip() for e in val if e and str(e).strip() and "@" in str(e)]
        return emails[0] if emails else ""
    if isinstance(val, str):
        return val.strip()
    return ""


def convert_to_v2(pi, source="unknown"):
    """Convert a PI entry from any format to v2 schema."""
    today = date.today().isoformat()

    # Normalize school name
    school_raw = pi.get("school") or pi.get("institution") or ""
    school = normalize_school(school_raw)

    # Department
    department = (pi.get("department") or "").strip()
    if department == "Various":
        department = ""

    # ID — preserve existing IDs exactly
    pi_id = pi.get("id") or ""
    if not pi_id:
        # Generate an ID if missing
        name_slug = (pi.get("name") or "unknown").lower().replace(" ", "-").replace(".", "")
        pi_id = f"{school.lower().replace(' ', '-')}-{name_slug}"

    # Email handling
    email = normalize_email(pi.get("email"))
    email_confidence = pi.get("email_confidence") or ("HIGH" if email and "@" in email else None)

    # H-index — prefer scholar, then openalex, then generic
    h_index = safe_int(pi.get("h_index_scholar")) or safe_int(pi.get("h_index")) or safe_int(pi.get("h_index_openalex"))
    h_index_source = None
    if safe_int(pi.get("h_index_scholar")):
        h_index_source = "google_scholar"
    elif safe_int(pi.get("h_index")):
        h_index_source = pi.get("h_index_source") or "openalex"
    elif safe_int(pi.get("h_index_openalex")):
        h_index_source = "openalex"

    # Research areas and topics
    areas = parse_research_areas(pi.get("research_areas"))
    topics_raw = pi.get("topics_openalex") or pi.get("scholar_interests") or []
    topics = parse_topics(topics_raw)
    if not topics and areas:
        topics = parse_topics(areas)

    # Techniques
    techniques = parse_techniques(pi.get("lab_techniques"))

    # Google Scholar
    gs_id = pi.get("google_scholar_id") or ""
    gs_url = pi.get("google_scholar_url") or pi.get("google_scholar") or ""
    if gs_id and not gs_url:
        gs_url = f"https://scholar.google.com/citations?user={gs_id}"

    # NSF awards
    nsf_awards = pi.get("nsf_awards") or []
    nsf_count = pi.get("nsf_grants_count") or len(nsf_awards)
    co_investigators = pi.get("co_investigators") or []

    # Confidence
    confidence = pi.get("confidence") or ("HIGH" if email else "MEDIUM")
    confidence_reason = pi.get("confidence_reason") or ""

    # Sources tracking
    sources = [source]
    if pi.get("at_mit_openalex"):
        sources.append("openalex")
    if gs_id or gs_url:
        sources.append("google_scholar")
    if nsf_awards:
        sources.append("nsf")

    return {
        "schema_version": "2.0",
        "id": str(pi_id),
        "name": (pi.get("name") or "").strip(),
        "name_alternatives": pi.get("name_alternatives") or [],

        "affiliation": {
            "school": school,
            "department": department,
            "department_category": dept_field_key(department),
            "title": (pi.get("title") or "").strip(),
            "location": (pi.get("location") or "").strip(),
            "specific_location": (pi.get("specific_location") or pi.get("location") or "").strip(),
        },

        "contact": {
            "email": email,
            "email_confidence": email_confidence,
            "website": (pi.get("website") or pi.get("mit_profile_url") or "").strip(),
            "google_scholar_id": gs_id,
            "google_scholar_url": gs_url,
        },

        "metrics": {
            "h_index": h_index,
            "h_index_source": h_index_source,
            "h_index_updated": today if h_index else None,
            "citations_total": safe_int(pi.get("citations_total")),
            "i10_index": safe_int(pi.get("i10_index")),
            "works_count": safe_int(pi.get("works_count")),
        },

        "research": {
            "areas": areas,
            "topics": topics[:20],
            "techniques": techniques,
        },

        "publications": {
            "recent_papers": [],
        },

        "funding": {
            "nsf_awards": nsf_awards,
            "nsf_grants_count": nsf_count,
            "co_investigators": co_investigators,
        },

        "data_quality": {
            "confidence": confidence,
            "confidence_reason": confidence_reason,
            "last_updated": today,
            "sources": list(set(sources)),
        },
    }


def load_json_file(path):
    """Load a JSON file, returning list or empty list."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "faculty" in data:
            return data["faculty"]
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not load {path}: {e}")
        return []


def load_dept_dir(dept_dir, school_name):
    """Load all department JSON files from a directory."""
    entries = []
    if not os.path.isdir(dept_dir):
        return entries
    for fname in sorted(os.listdir(dept_dir)):
        if not fname.endswith(".json"):
            continue
        # Prefer enriched files for MIT
        if "_enriched" not in fname and os.path.exists(os.path.join(dept_dir, fname.replace(".json", "_enriched.json"))):
            continue
        fpath = os.path.join(dept_dir, fname)
        try:
            data = load_json_file(fpath)
            for pi in data:
                # Set school if not present
                if not pi.get("school"):
                    pi["school"] = school_name
                entries.append(pi)
        except Exception as e:
            print(f"  Warning: Error in {fname}: {e}")
    return entries


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_faculty = []
    by_school = {}
    seen_names = set()

    def add_pi(pi_v2):
        name_lower = pi_v2["name"].lower()
        school = pi_v2["affiliation"]["school"].lower()
        if not name_lower or name_lower in seen_names:
            return False
        if ENABLED_SCHOOLS and school not in ENABLED_SCHOOLS:
            return False
        if pi_v2["affiliation"]["department"] == "Various":
            return False
        seen_names.add(name_lower)
        all_faculty.append(pi_v2)
        school_key = pi_v2["affiliation"]["school"]
        by_school.setdefault(school_key, []).append(pi_v2)
        return True

    added = 0
    skipped = 0

    # 1. Load per-school working files (highest priority for base data)
    print("Loading per-school working files...")
    for school_name, path in SCHOOL_WORKING_FILES.items():
        entries = load_json_file(path)
        count = 0
        for pi in entries:
            v2 = convert_to_v2(pi, source="working_file")
            if add_pi(v2):
                count += 1
        print(f"  {school_name}: {count} PIs loaded")
        added += count

    # 2. Load Harvard department files (may add PIs not in working file)
    print("Loading Harvard department files...")
    entries = load_dept_dir(HARVARD_DEPT_DIR, "Harvard University")
    count = 0
    for pi in entries:
        v2 = convert_to_v2(pi, source="harvard_dept")
        if add_pi(v2):
            count += 1
    print(f"  Harvard departments: {count} new PIs added")
    added += count

    # 3. Load MIT enriched files (prefer enriched over base)
    print("Loading MIT department files...")
    entries = load_dept_dir(MIT_DIR, "MIT")
    count = 0
    for pi in entries:
        v2 = convert_to_v2(pi, source="mit_enriched")
        if add_pi(v2):
            count += 1
    print(f"  MIT departments: {count} new PIs added")
    added += count

    # 4. Load other school department directories
    for school_name, dept_dir in SCHOOL_DEPT_DIRS.items():
        entries = load_dept_dir(dept_dir, school_name)
        count = 0
        for pi in entries:
            v2 = convert_to_v2(pi, source="dept_file")
            if add_pi(v2):
                count += 1
        if count > 0:
            print(f"  {school_name} departments: {count} new PIs added")
        added += count

    # 5. Load NSF Active Awards (lowest priority, fills gaps)
    print("Loading NSF Active Awards...")
    nsf_entries = load_json_file(NSF_PATH)
    count = 0
    for pi in nsf_entries:
        v2 = convert_to_v2(pi, source="nsf_active")
        if add_pi(v2):
            count += 1
    print(f"  NSF Active Awards: {count} new PIs added")
    added += count

    # Write combined file
    combined_path = os.path.join(OUTPUT_DIR, "all_faculty.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_faculty, f, indent=2, ensure_ascii=False)
    print(f"\nCombined file: {combined_path} ({len(all_faculty)} PIs)")

    # Write per-school files
    for school_name, pis in sorted(by_school.items()):
        slug = school_name.lower().replace(" ", "_")
        path = os.path.join(OUTPUT_DIR, f"{slug}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pis, f, indent=2, ensure_ascii=False)
        print(f"  {school_name}: {path} ({len(pis)} PIs)")

    # Summary
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"  Total PIs: {len(all_faculty)}")
    print(f"  Schools: {len(by_school)}")
    for school, pis in sorted(by_school.items(), key=lambda x: -len(x[1])):
        print(f"    {school}: {len(pis)}")
    print(f"  Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
