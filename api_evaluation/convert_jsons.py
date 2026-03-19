#!/usr/bin/env python3
"""
Convert faculty JSON files from Data/Misc jsons/ to gold-standard CSVs
for the search pipeline.

Output CSVs have columns: name, affiliation, department, gold_email, gold_website.

Usage:
  python -m api_evaluation.convert_jsons
  python -m api_evaluation.convert_jsons --list-only
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
MISC_JSONS = REPO_ROOT / "data" / "Misc jsons"
OUTPUT_DIR = REPO_ROOT / "api_evaluation" / "inputs"

# (json_filename, output_csv_name, affiliation_string)
CONVERSIONS = [
    ("mit_faculty_working.json", "mit_faculty.csv", "Massachusetts Institute of Technology"),
    ("tufts_university_faculty_working.json", "tufts_faculty.csv", "Tufts University"),
    ("boston_university_faculty_working.json", "bu_faculty.csv", "Boston University"),
    ("northeastern_university_faculty_working.json", "northeastern_faculty.csv", "Northeastern University"),
    ("stanford_university_faculty_working.json", "stanford_faculty.csv", "Stanford University"),
    ("yale_university_faculty_working.json", "yale_faculty.csv", "Yale University"),
    ("princeton_university_faculty_working.json", "princeton_faculty.csv", "Princeton University"),
]

CSV_COLUMNS = ["name", "affiliation", "department", "gold_email", "gold_website"]


def extract_from_faculty_obj(obj: dict, affiliation: str) -> Optional[dict]:
    """
    Extract one row from a faculty object. Handles common schemas:
    - List of objects with name, department, website, email (and optional title/school)
    """
    name = (obj.get("name") or obj.get("Name") or "").strip()
    if not name:
        return None
    department = (obj.get("department") or obj.get("Department") or "").strip()
    website = (obj.get("website") or obj.get("Website") or "").strip()
    email = (obj.get("email") or obj.get("Email") or "").strip().lower()
    return {
        "name": name,
        "affiliation": affiliation,
        "department": department,
        "gold_email": email,
        "gold_website": website,
    }


def load_json_faculty_list(path: Path) -> list:
    """Load JSON; return list of faculty objects (handles top-level list or dict with 'faculty' key)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "faculty" in data:
        return data["faculty"]
    if isinstance(data, dict):
        # single key that is a list?
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def convert_one(json_name: str, out_name: str, affiliation: str, list_only: bool) -> int:
    """Convert one JSON to CSV. Returns count of rows written."""
    src = MISC_JSONS / json_name
    if not src.exists():
        print(f"  SKIP (not found): {json_name}", file=sys.stderr)
        return 0

    faculty_list = load_json_faculty_list(src)
    rows = []
    for obj in faculty_list:
        if not isinstance(obj, dict):
            continue
        row = extract_from_faculty_obj(obj, affiliation)
        if row:
            rows.append(row)

    if list_only:
        print(f"  {json_name} -> {out_name}: {len(rows)} professors")
        return len(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / out_name
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"  {json_name} -> {out_path}: {len(rows)} professors")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert faculty JSONs to input CSVs.")
    parser.add_argument("--list-only", action="store_true", help="Only print counts, do not write CSVs.")
    args = parser.parse_args()

    print("Converting faculty JSONs to CSVs")
    print(f"  Source: {MISC_JSONS}")
    print(f"  Output: {OUTPUT_DIR}")
    totals = {}
    for json_name, out_name, affiliation in CONVERSIONS:
        n = convert_one(json_name, out_name, affiliation, list_only=args.list_only)
        # Short label for summary (MIT, Tufts, BU, Northeastern, Stanford, Yale, Princeton)
        label = out_name.replace("_faculty.csv", "")
        label = {"mit": "MIT", "bu": "BU", "tufts": "Tufts", "northeastern": "Northeastern",
                 "stanford": "Stanford", "yale": "Yale", "princeton": "Princeton"}.get(label.lower(), label.capitalize())
        totals[label] = n

    print("\nFaculty counts per university:")
    for label, count in totals.items():
        print(f"  {label}: {count}")
    print(f"  TOTAL: {sum(totals.values())}")


if __name__ == "__main__":
    main()
