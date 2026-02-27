#!/usr/bin/env python3
"""
Convert faculty data from pipeline format to website format.
Pipeline format has nested structures (email.value, website.value, research.topics)
Website format expects flat structures (email, website, research_areas)

Supports multiple institutions (harvard, mit, stanford, etc.)
"""

import json
import sys
from pathlib import Path

# Institution-specific defaults
INSTITUTION_DEFAULTS = {
    "harvard": {
        "id_prefix": "harvard",
        "school_name": "Harvard University",
        "location": "Cambridge, MA",
    },
    "mit": {
        "id_prefix": "mit",
        "school_name": "MIT",
        "location": "Cambridge, MA",
    },
    "stanford": {
        "id_prefix": "stanford",
        "school_name": "Stanford University",
        "location": "Stanford, CA",
    },
}


def convert_faculty_member(pipeline_faculty, institution="harvard"):
    """Convert a single faculty member from pipeline format to website format."""

    defaults = INSTITUTION_DEFAULTS.get(institution, {
        "id_prefix": institution,
        "school_name": pipeline_faculty.get("institution", institution.title()),
        "location": "",
    })

    # Extract basic info
    name = pipeline_faculty.get("name", "")
    openalex_id = pipeline_faculty.get("openalex_id", "")

    # Generate ID from openalex_id or name
    id_prefix = defaults["id_prefix"]
    if openalex_id:
        # Extract ID from URL like "https://openalex.org/A5051537916"
        pi_id = openalex_id.split("/")[-1] if "/" in openalex_id else openalex_id
        pi_id = f"{id_prefix}-{pi_id}"
    else:
        # Fallback: create ID from name
        pi_id = f"{id_prefix}-{name.lower().replace(' ', '-').replace('.', '')[:30]}"

    # Extract email - use value if available, otherwise empty string or [placeholder]
    email_data = pipeline_faculty.get("email", {})
    email_value = email_data.get("value", "") if isinstance(email_data, dict) else (email_data if isinstance(email_data, str) else "")
    # If no email, use empty string (will be handled in templates)

    # Extract website - use value if available
    website_data = pipeline_faculty.get("website", {})
    website_value = website_data.get("value", "") if isinstance(website_data, dict) else (website_data if isinstance(website_data, str) else "")

    # Extract research information
    research = pipeline_faculty.get("research", {})

    # Get research areas from topics
    topics = research.get("topics", [])
    research_areas_list = []
    if topics:
        # Get top 5-10 topics
        for topic in topics[:10]:
            if isinstance(topic, dict):
                research_areas_list.append(topic.get("name", ""))
            elif isinstance(topic, str):
                research_areas_list.append(topic)

    # Also check keywords
    keywords = research.get("keywords", [])
    if keywords:
        for keyword in keywords[:5]:
            if keyword and keyword not in research_areas_list:
                research_areas_list.append(keyword)

    # Use research_summary if available, otherwise join topics
    research_areas = pipeline_faculty.get("research_summary", ", ".join(research_areas_list[:5]))
    if not research_areas:
        research_areas = ", ".join(research_areas_list[:5]) if research_areas_list else "Research information not available"

    # Extract techniques from keywords or concepts
    techniques_list = []
    concepts = research.get("concepts", [])
    if concepts:
        for concept in concepts[:10]:
            if isinstance(concept, dict):
                concept_name = concept.get("name", "")
                if concept_name and concept_name not in techniques_list:
                    techniques_list.append(concept_name)

    # Add keywords as techniques too
    if keywords:
        for keyword in keywords[:10]:
            if keyword and keyword not in techniques_list:
                techniques_list.append(keyword)

    lab_techniques = ", ".join(techniques_list[:10]) if techniques_list else "Not specified"

    # Extract other fields
    h_index = pipeline_faculty.get("h_index", 0)
    # Use institution from data if available, otherwise use defaults
    institution_name = pipeline_faculty.get("institution", defaults["school_name"])

    # Determine department from research fields or use default
    fields = research.get("fields", [])
    department = fields[0] if fields else "Various"

    # Use location from defaults
    location = defaults["location"]

    # Build the website format
    website_faculty = {
        "id": pi_id,
        "name": name,
        "title": f"Professor at {institution_name}",  # Default title
        "department": department,
        "school": defaults["school_name"],
        "location": location,
        "specific_location": location,
        "research_areas": research_areas,
        "website": website_value,  # Will be empty string if not available
        "email": email_value,  # Will be empty string if not available - templates will handle [placeholder]
        "h_index": str(h_index) if h_index else "0",
        "lab_techniques": lab_techniques,
        "google_scholar": "",  # Not in pipeline data
    }

    return website_faculty


def convert_faculty_data(input_path, output_path, institution="harvard"):
    """Convert faculty data from pipeline format to website format."""

    print(f"Loading faculty data from {input_path}...")
    print(f"Institution: {institution}")
    with open(input_path, "r", encoding="utf-8") as f:
        pipeline_data = json.load(f)

    # Extract faculty list
    if isinstance(pipeline_data, dict) and "faculty" in pipeline_data:
        faculty_list = pipeline_data["faculty"]
    elif isinstance(pipeline_data, list):
        faculty_list = pipeline_data
    else:
        raise ValueError("Invalid data format")

    print(f"Found {len(faculty_list)} faculty members")

    # Convert each faculty member
    website_faculty_list = []
    emails_found = 0
    websites_found = 0

    for faculty in faculty_list:
        converted = convert_faculty_member(faculty, institution=institution)
        website_faculty_list.append(converted)

        if converted["email"]:
            emails_found += 1
        if converted["website"]:
            websites_found += 1

    print(f"Converted {len(website_faculty_list)} faculty members")
    print(f"Emails found: {emails_found} ({emails_found/len(website_faculty_list)*100:.1f}%)")
    print(f"Websites found: {websites_found} ({websites_found/len(website_faculty_list)*100:.1f}%)")

    # Save to output file
    print(f"Saving to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(website_faculty_list, f, indent=2, ensure_ascii=False)

    print(f"Done! Saved {len(website_faculty_list)} faculty to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert pipeline faculty data to website format")
    parser.add_argument("input_path", nargs="?", default=None, help="Path to pipeline output JSON")
    parser.add_argument("output_path", nargs="?", default=None, help="Path for website format output")
    parser.add_argument("--institution", "-i", default="harvard",
                        choices=list(INSTITUTION_DEFAULTS.keys()),
                        help="Institution to convert (default: harvard)")

    args = parser.parse_args()

    # Set default paths based on institution
    if args.input_path is None:
        if args.institution == "harvard":
            args.input_path = "output/harvard_university_20260121_113956.json"
        else:
            # Look for most recent output file for this institution
            import glob
            pattern = f"output/{INSTITUTION_DEFAULTS[args.institution]['school_name'].lower().replace(' ', '_')}*.json"
            matches = sorted(glob.glob(pattern))
            if matches:
                args.input_path = matches[-1]
            else:
                print(f"No pipeline output found for {args.institution}. Run the pipeline first.")
                sys.exit(1)

    if args.output_path is None:
        if args.institution == "harvard":
            args.output_path = "data/faculty_working.json"
        else:
            args.output_path = f"data/{args.institution}_faculty_working.json"

    # Ensure output directory exists
    output_dir = Path(args.output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    convert_faculty_data(args.input_path, args.output_path, institution=args.institution)
