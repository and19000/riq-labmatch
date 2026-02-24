#!/usr/bin/env python3
"""
Collect faculty data from OpenAlex API for any university.
Generalized version of collect_mit_openalex.py.

Usage:
    # Run for a single pre-configured school:
    python3 collect_school_openalex.py --school "Boston University"

    # Run for all pre-configured schools:
    python3 collect_school_openalex.py --all

    # Run for a custom school (not in SCHOOLS dict):
    python3 collect_school_openalex.py --school "Columbia University" --openalex-id I78577930 --location "New York, NY"

    # Override max faculty count:
    python3 collect_school_openalex.py --school "Tufts University" --max-faculty 400
"""

import json
import time
import argparse
import re
import requests
from pathlib import Path

# ---------------------------------------------------------------------------
# Pre-configured schools
# ---------------------------------------------------------------------------
SCHOOLS = {
    "Boston University": {
        "openalex_id": "I111088046",
        "location": "Boston, MA",
        "short_name": "BU",
    },
    "Northeastern University": {
        "openalex_id": "I12912129",
        "location": "Boston, MA",
        "short_name": "Northeastern",
    },
    "Tufts University": {
        "openalex_id": "I121934306",
        "location": "Medford, MA",
        "short_name": "Tufts",
    },
    "Stanford University": {
        "openalex_id": "I97018004",
        "location": "Stanford, CA",
        "short_name": "Stanford",
    },
    "Yale University": {
        "openalex_id": "I32971472",
        "location": "New Haven, CT",
        "short_name": "Yale",
    },
    "Princeton University": {
        "openalex_id": "I20089843",
        "location": "Princeton, NJ",
        "short_name": "Princeton",
    },
}

# ---------------------------------------------------------------------------
# Thresholds (same as main pipeline / MIT script)
# ---------------------------------------------------------------------------
MIN_H_INDEX = 10
MIN_WORKS = 30
MAX_INSTITUTIONS = 15

# Contact email for OpenAlex polite pool (faster rate limits)
CONTACT_EMAIL = "riq-labmatch@example.com"

BASE_URL = "https://api.openalex.org"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_school_slug(school_name: str) -> str:
    """
    Turn a school name into a filesystem-friendly slug.
    e.g. "Boston University" -> "boston_university"
    """
    slug = school_name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


def make_school_prefix(school_name: str, short_name: str | None = None) -> str:
    """
    Return a short lowercase prefix for IDs.
    Uses the short_name if available, otherwise derives from the full name.
    e.g. "BU" -> "bu", "Northeastern" -> "northeastern"
    """
    if short_name:
        return short_name.lower().replace(" ", "")
    # Fallback: first letter of each word, lowered
    return "".join(w[0] for w in school_name.split()).lower()


def make_folder_name(school_name: str, short_name: str | None = None) -> str:
    """
    Return the name used for the school's Data/ sub-directory.
    Uses short_name if available (e.g. "BU"), otherwise title-cases the name
    with spaces removed ("BostonUniversity").
    """
    if short_name:
        return short_name
    return school_name.replace(" ", "")


def clean_department_name(dept: str) -> str:
    """
    Apply data-quality fixes to a department name extracted from OpenAlex.
    - Capitalize each word (title-case), but keep small words like "and" lowercase.
    - Fix the known "and Optics" artifact that sometimes appears as a
      standalone department when OpenAlex truncates "Atomic and Molecular
      Physics, and Optics" across two topic entries.
    """
    if not dept:
        return "Various"

    # Fix "and Optics" artifact
    if dept.strip().lower() in ("and optics", "optics"):
        return "Physics and Astronomy"

    # Title-case, but keep small connector words lowercase
    SMALL_WORDS = {"and", "of", "the", "in", "for", "on", "at", "to", "a", "an"}
    dept = dept.strip()
    words = dept.split()
    result = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in SMALL_WORDS:
            result.append(w.lower())
        else:
            result.append(w.capitalize() if w.islower() else w)
    return " ".join(result)


# ---------------------------------------------------------------------------
# Core collection logic
# ---------------------------------------------------------------------------

def fetch_faculty(school_name: str, openalex_id: str, location: str,
                  short_name: str | None = None, max_faculty: int = 600):
    """Fetch faculty for a given school from OpenAlex API."""

    prefix = make_school_prefix(school_name, short_name)

    session = requests.Session()
    session.headers.update({
        "User-Agent": f"RIQ-LabMatch/1.0 (mailto:{CONTACT_EMAIL})"
    })

    filter_param = f"last_known_institutions.id:{openalex_id}"
    url = f"{BASE_URL}/authors"

    # Get total count
    params = {"filter": filter_param, "per_page": 1}
    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()
    total = resp.json().get("meta", {}).get("count", 0)
    print(f"  Total authors in OpenAlex for {school_name}: {total:,}")

    faculty_list = []
    page = 1

    while len(faculty_list) < max_faculty:
        params = {
            "filter": filter_param,
            "per_page": 200,
            "page": page,
        }

        try:
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"    API error on page {page}: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for author in results:
            if len(faculty_list) >= max_faculty:
                break

            # Skip entries without a display_name
            display_name = author.get("display_name", "")
            if not display_name:
                continue

            # Check institution match
            institutions = author.get("last_known_institutions", [])
            if not institutions:
                continue
            primary_inst = institutions[0].get("display_name", "")
            # Verify the primary institution mentions the school
            # Use a simple substring check on the full school name
            name_tokens = school_name.lower().split()
            inst_lower = primary_inst.lower()
            if not any(tok in inst_lower for tok in name_tokens):
                continue
            if len(institutions) > MAX_INSTITUTIONS:
                continue

            # Quality filter
            summary = author.get("summary_stats", {})
            h_index = summary.get("h_index", 0) or 0
            works = author.get("works_count", 0) or 0
            if h_index < MIN_H_INDEX and works < MIN_WORKS:
                continue

            # Parse research profile
            topics = author.get("topics", [])
            topic_names = [
                t.get("display_name", "")
                for t in (topics or [])[:15]
                if t.get("display_name")
            ]

            # Extract fields from topics (field.display_name) -- more reliable than x_concepts
            fields_from_topics = []
            subfields_from_topics = []
            for t in (topics or [])[:15]:
                field_info = t.get("field", {})
                field_name = field_info.get("display_name", "") if isinstance(field_info, dict) else ""
                if field_name and field_name not in fields_from_topics:
                    fields_from_topics.append(field_name)
                subfield_info = t.get("subfield", {})
                subfield_name = subfield_info.get("display_name", "") if isinstance(subfield_info, dict) else ""
                if subfield_name and subfield_name not in subfields_from_topics:
                    subfields_from_topics.append(subfield_name)

            concepts = author.get("x_concepts", [])
            concept_list = [
                {"name": c.get("display_name", ""), "score": round(c.get("score", 0), 3)}
                for c in (concepts or [])[:10]
                if c.get("display_name")
            ]

            keywords = topic_names[:15] if topic_names else [c["name"] for c in concept_list][:15]

            # Determine department from the primary research field + clean it
            raw_department = fields_from_topics[0] if fields_from_topics else (
                concept_list[0]["name"] if concept_list else "Various"
            )
            department = clean_department_name(raw_department)

            # Research areas string -- use topic names (more specific than fields)
            research_areas = "; ".join(topic_names[:5]) if topic_names else (
                ", ".join(fields_from_topics[:3]) if fields_from_topics else "Research information not available"
            )

            # Lab techniques from subfields + concepts + keywords
            techniques = []
            for sf in subfields_from_topics[:5]:
                if sf not in techniques:
                    techniques.append(sf)
            for c in concept_list:
                if c["name"] not in techniques:
                    techniques.append(c["name"])
            for kw in keywords:
                if kw not in techniques:
                    techniques.append(kw)
            lab_techniques = ", ".join(techniques[:10]) if techniques else "Not specified"

            # Generate ID: {school_prefix}-{openalex_id}
            raw_openalex_id = author.get("id", "")
            id_suffix = raw_openalex_id.split("/")[-1] if "/" in raw_openalex_id else raw_openalex_id
            pi_id = f"{prefix}-{id_suffix}"

            # Build webapp-compatible entry
            entry = {
                "id": pi_id,
                "name": display_name,
                "title": f"Professor at {school_name}",
                "department": department,
                "school": short_name if short_name else school_name,
                "location": location,
                "specific_location": location,
                "research_areas": research_areas,
                "website": "",
                "email": "",
                "h_index": str(h_index),
                "lab_techniques": lab_techniques,
                "google_scholar": "",
            }
            faculty_list.append(entry)

        print(f"    Page {page}: {len(faculty_list)} faculty collected so far")
        page += 1
        time.sleep(0.15)  # Rate limiting

        if page > 100:
            break

    # Sort by h-index (highest first)
    faculty_list.sort(key=lambda f: int(f["h_index"] or "0"), reverse=True)
    return faculty_list


# ---------------------------------------------------------------------------
# Split by department
# ---------------------------------------------------------------------------

def split_by_department(faculty_list, output_dir):
    """Split faculty list into per-department JSON files."""
    departments = {}
    for pi in faculty_list:
        dept = pi["department"]
        if dept not in departments:
            departments[dept] = []
        departments[dept].append(pi)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for dept_name, members in sorted(departments.items(), key=lambda x: -len(x[1])):
        filename = dept_name.replace(" ", "_").replace("/", "_").replace(",", "") + "_faculty.json"
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(members, f, indent=2, ensure_ascii=False)
        print(f"    {dept_name}: {len(members)} faculty -> {filename}")

    return departments


# ---------------------------------------------------------------------------
# Process one school
# ---------------------------------------------------------------------------

def process_school(school_name: str, openalex_id: str, location: str,
                   short_name: str | None = None, max_faculty: int = 600,
                   project_root: Path | None = None):
    """Full pipeline for one school: fetch, save combined JSON, split by department."""

    if project_root is None:
        project_root = Path(__file__).parent.parent

    slug = make_school_slug(school_name)
    folder = make_folder_name(school_name, short_name)

    combined_path = project_root / "Data" / "Misc jsons" / f"{slug}_faculty_working.json"
    dept_dir = project_root / "Data" / folder

    print(f"\n{'=' * 60}")
    print(f"Collecting faculty for {school_name}")
    print(f"{'=' * 60}")
    print(f"  OpenAlex ID : {openalex_id}")
    print(f"  Location    : {location}")
    print(f"  Max faculty : {max_faculty}")
    print(f"  Combined out: {combined_path}")
    print(f"  Dept dir    : {dept_dir}")
    print()

    faculty_list = fetch_faculty(
        school_name=school_name,
        openalex_id=openalex_id,
        location=location,
        short_name=short_name,
        max_faculty=max_faculty,
    )

    print(f"\n  Collected {len(faculty_list)} faculty members for {school_name}")

    # Stats
    with_email = sum(1 for f in faculty_list if f["email"])
    with_website = sum(1 for f in faculty_list if f["website"])
    unique_departments = set(f["department"] for f in faculty_list)
    print(f"    Unique departments: {len(unique_departments)}")
    print(f"    With email: {with_email} ({with_email / max(len(faculty_list), 1) * 100:.1f}%)")
    print(f"    With website: {with_website} ({with_website / max(len(faculty_list), 1) * 100:.1f}%)")

    # Save combined file
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(faculty_list, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved combined data to {combined_path}")

    # Save per-department files
    print(f"\n  Splitting by department into {dept_dir}/:")
    split_by_department(faculty_list, dept_dir)

    print(f"\n  Done with {school_name}!")
    return faculty_list


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Collect faculty data from OpenAlex for any university.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 collect_school_openalex.py --school "Boston University"
  python3 collect_school_openalex.py --all
  python3 collect_school_openalex.py --school "Columbia University" --openalex-id I78577930 --location "New York, NY"
  python3 collect_school_openalex.py --all --max-faculty 400
        """,
    )
    parser.add_argument(
        "--school", "-s", type=str, default=None,
        help='School name (e.g. "Boston University"). Must match a SCHOOLS key or provide --openalex-id and --location.',
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run collection for ALL pre-configured schools in the SCHOOLS dict.",
    )
    parser.add_argument(
        "--openalex-id", type=str, default=None,
        help="OpenAlex institution ID (e.g. I142825004). Required if --school is not in SCHOOLS.",
    )
    parser.add_argument(
        "--location", type=str, default=None,
        help='City, State (e.g. "Boston, MA"). Required if --school is not in SCHOOLS.',
    )
    parser.add_argument(
        "--short-name", type=str, default=None,
        help='Short name / abbreviation for the school (e.g. "BU"). Used for IDs and folder names.',
    )
    parser.add_argument(
        "--max-faculty", "-m", type=int, default=600,
        help="Maximum number of faculty to collect per school (default: 600).",
    )
    args = parser.parse_args()

    # Validate arguments
    if not args.school and not args.all:
        parser.error("Provide --school <name> or --all.")

    project_root = Path(__file__).parent.parent

    if args.all:
        # Run for every pre-configured school
        print(f"Running collection for {len(SCHOOLS)} pre-configured schools.")
        for name, cfg in SCHOOLS.items():
            process_school(
                school_name=name,
                openalex_id=cfg["openalex_id"],
                location=cfg["location"],
                short_name=cfg.get("short_name"),
                max_faculty=args.max_faculty,
                project_root=project_root,
            )
        print(f"\nAll {len(SCHOOLS)} schools complete.")
        return

    # Single school mode
    school_name = args.school

    if school_name in SCHOOLS:
        cfg = SCHOOLS[school_name]
        openalex_id = args.openalex_id or cfg["openalex_id"]
        location = args.location or cfg["location"]
        short_name = args.short_name or cfg.get("short_name")
    else:
        # Custom school -- require openalex-id and location
        if not args.openalex_id or not args.location:
            parser.error(
                f'School "{school_name}" is not pre-configured. '
                "Provide --openalex-id and --location."
            )
        openalex_id = args.openalex_id
        location = args.location
        short_name = args.short_name

    process_school(
        school_name=school_name,
        openalex_id=openalex_id,
        location=location,
        short_name=short_name,
        max_faculty=args.max_faculty,
        project_root=project_root,
    )


if __name__ == "__main__":
    main()
