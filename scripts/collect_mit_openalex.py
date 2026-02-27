#!/usr/bin/env python3
"""
Collect MIT faculty data from OpenAlex API (free, no API key needed).
Outputs webapp-compatible JSON format matching the Harvard faculty schema.

Usage:
    python3 collect_mit_openalex.py [--max-faculty 600] [--output ../Data/Misc\ jsons/mit_faculty_working.json]
"""

import json
import time
import argparse
import requests
from pathlib import Path

# MIT OpenAlex institution ID
MIT_OPENALEX_ID = "I63966007"
MIT_NAME = "MIT"
MIT_FULL_NAME = "Massachusetts Institute of Technology"
MIT_LOCATION = "Cambridge, MA"

# Thresholds (same as main pipeline)
MIN_H_INDEX = 10
MIN_WORKS = 30
MAX_INSTITUTIONS = 15

# Contact email for OpenAlex polite pool (faster rate limits)
CONTACT_EMAIL = "riq-labmatch@example.com"

BASE_URL = "https://api.openalex.org"


def fetch_mit_faculty(max_faculty=600):
    """Fetch MIT faculty from OpenAlex API."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": f"RIQ-LabMatch/1.0 (mailto:{CONTACT_EMAIL})"
    })

    filter_param = f"last_known_institutions.id:{MIT_OPENALEX_ID}"
    url = f"{BASE_URL}/authors"

    # Get total count
    params = {"filter": filter_param, "per_page": 1}
    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()
    total = resp.json().get("meta", {}).get("count", 0)
    print(f"Total MIT authors in OpenAlex: {total:,}")

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
            print(f"  API error on page {page}: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for author in results:
            if len(faculty_list) >= max_faculty:
                break

            # Check institution match
            institutions = author.get("last_known_institutions", [])
            if not institutions:
                continue
            primary_inst = institutions[0].get("display_name", "")
            if "Massachusetts" not in primary_inst and "MIT" not in primary_inst:
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
            topic_names = [t.get("display_name", "") for t in (topics or [])[:15] if t.get("display_name")]

            # Extract fields from topics (field.display_name) — more reliable than x_concepts
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
                for c in (concepts or [])[:10] if c.get("display_name")
            ]

            keywords = topic_names[:15] if topic_names else [c["name"] for c in concept_list][:15]

            # Determine department from the primary research field
            department = fields_from_topics[0] if fields_from_topics else (
                concept_list[0]["name"] if concept_list else "Various"
            )

            # Research areas string — use topic names (more specific than fields)
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

            # Generate ID
            openalex_id = author.get("id", "")
            id_suffix = openalex_id.split("/")[-1] if "/" in openalex_id else openalex_id
            pi_id = f"mit-{id_suffix}"

            # Build webapp-compatible entry
            entry = {
                "id": pi_id,
                "name": author.get("display_name", ""),
                "title": f"Professor at {MIT_FULL_NAME}",
                "department": department,
                "school": MIT_NAME,
                "location": MIT_LOCATION,
                "specific_location": MIT_LOCATION,
                "research_areas": research_areas,
                "website": "",
                "email": "",
                "h_index": str(h_index),
                "lab_techniques": lab_techniques,
                "google_scholar": "",
            }
            faculty_list.append(entry)

        print(f"  Page {page}: {len(faculty_list)} faculty collected so far")
        page += 1
        time.sleep(0.15)  # Rate limiting

        if page > 100:
            break

    # Sort by h-index (highest first)
    faculty_list.sort(key=lambda f: int(f["h_index"] or "0"), reverse=True)
    return faculty_list


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
        print(f"  {dept_name}: {len(members)} faculty -> {filename}")

    return departments


def main():
    parser = argparse.ArgumentParser(description="Collect MIT faculty from OpenAlex")
    parser.add_argument("--max-faculty", "-m", type=int, default=600,
                        help="Maximum number of faculty to collect (default: 600)")
    parser.add_argument("--output", "-o", type=str,
                        default=None,
                        help="Output path for combined JSON")
    parser.add_argument("--dept-dir", "-d", type=str,
                        default=None,
                        help="Directory for per-department JSON files")
    args = parser.parse_args()

    # Set default paths relative to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    if args.output is None:
        args.output = str(project_root / "Data" / "Misc jsons" / "mit_faculty_working.json")
    if args.dept_dir is None:
        args.dept_dir = str(project_root / "Data" / "MIT")

    print("=" * 60)
    print("MIT Faculty Collection via OpenAlex")
    print("=" * 60)
    print(f"Max faculty: {args.max_faculty}")
    print(f"Output: {args.output}")
    print()

    # Collect faculty
    faculty_list = fetch_mit_faculty(max_faculty=args.max_faculty)

    print(f"\nCollected {len(faculty_list)} MIT faculty members")

    # Stats
    with_email = sum(1 for f in faculty_list if f["email"])
    with_website = sum(1 for f in faculty_list if f["website"])
    departments = set(f["department"] for f in faculty_list)
    print(f"  Unique departments: {len(departments)}")
    print(f"  With email: {with_email} ({with_email/max(len(faculty_list),1)*100:.1f}%)")
    print(f"  With website: {with_website} ({with_website/max(len(faculty_list),1)*100:.1f}%)")

    # Save combined file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(faculty_list, f, indent=2, ensure_ascii=False)
    print(f"\nSaved combined data to {output_path}")

    # Save per-department files
    print(f"\nSplitting by department into {args.dept_dir}/:")
    split_by_department(faculty_list, args.dept_dir)

    print(f"\nDone!")


if __name__ == "__main__":
    main()
