#!/usr/bin/env python3
"""
Convert faculty data from pipeline format to website format.
Pipeline format has nested structures (email.value, website.value, research.topics)
Website format expects flat structures (email, website, research_areas)
"""

import json
import sys
from pathlib import Path

def convert_faculty_member(pipeline_faculty):
    """Convert a single faculty member from pipeline format to website format."""
    
    # Extract basic info
    name = pipeline_faculty.get("name", "")
    openalex_id = pipeline_faculty.get("openalex_id", "")
    
    # Generate ID from openalex_id or name
    if openalex_id:
        # Extract ID from URL like "https://openalex.org/A5051537916"
        pi_id = openalex_id.split("/")[-1] if "/" in openalex_id else openalex_id
        pi_id = f"harvard-{pi_id}"
    else:
        # Fallback: create ID from name
        pi_id = f"harvard-{name.lower().replace(' ', '-').replace('.', '')[:30]}"
    
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
    institution = pipeline_faculty.get("institution", "Harvard University")
    
    # Determine department from research fields or use default
    fields = research.get("fields", [])
    department = fields[0] if fields else "Various"
    
    # Build the website format
    website_faculty = {
        "id": pi_id,
        "name": name,
        "title": f"Professor at {institution}",  # Default title
        "department": department,
        "school": institution,
        "location": "Cambridge, MA",  # Default for Harvard
        "specific_location": "Cambridge, MA",
        "research_areas": research_areas,
        "website": website_value,  # Will be empty string if not available
        "email": email_value,  # Will be empty string if not available - templates will handle [placeholder]
        "h_index": str(h_index) if h_index else "0",
        "lab_techniques": lab_techniques,
        "google_scholar": "",  # Not in pipeline data
    }
    
    return website_faculty


def convert_faculty_data(input_path, output_path):
    """Convert faculty data from pipeline format to website format."""
    
    print(f"Loading faculty data from {input_path}...")
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
        converted = convert_faculty_member(faculty)
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
    
    print(f"✓ Conversion complete! Saved {len(website_faculty_list)} faculty to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default paths
        input_path = "output/harvard_university_20260121_113956.json"
        output_path = "data/faculty_working.json"
    else:
        input_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else "data/faculty_working.json"
    
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    convert_faculty_data(input_path, output_path)
