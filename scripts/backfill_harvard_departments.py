#!/usr/bin/env python3
"""
backfill_harvard_departments.py

Backfills department information for Harvard faculty in faculty_working.json
by matching names against per-department JSON files in Data/Harvard/.

Matching strategy:
  1. Normalize last names to lowercase for lookup.
  2. For each faculty_working entry, find candidates sharing the same last name.
  3. Confirm by comparing first names (handles middle initials, "Dr." prefix, etc.).
  4. Update the department field from "Various" to the matched department.
"""

import json
import os
import re
import unicodedata
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARVARD_DIR = os.path.join(BASE_DIR, "Data", "Harvard")
FACULTY_WORKING_PATH = os.path.join(BASE_DIR, "Data", "Misc jsons", "faculty_working.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_str(s: str) -> str:
    """Lowercase, strip accents, and collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", s)
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents.strip().lower())


def strip_dr_prefix(name: str) -> str:
    """Remove leading 'Dr. ' or 'Dr ' from a name."""
    return re.sub(r"^Dr\.?\s+", "", name.strip())


def extract_last_name(full_name: str) -> str:
    """
    Return the last whitespace-delimited token, lowercased and accent-stripped.
    """
    parts = normalize_str(full_name).split()
    if not parts:
        return ""
    return parts[-1]


def extract_first_name(full_name: str) -> str:
    """
    Return the first token of the name (after stripping Dr.), lowercased and
    accent-stripped.
    """
    cleaned = strip_dr_prefix(full_name)
    parts = normalize_str(cleaned).split()
    if not parts:
        return ""
    return parts[0]


def first_name_matches(name_a: str, name_b: str) -> bool:
    """
    Check whether two first names are close enough to be the same person.

    Handles cases like:
      - "jennifer" vs "jennifer"            -> exact match
      - "j" vs "jennifer"                   -> initial match
      - "j." vs "jennifer"                  -> initial match
      - Fuzzy ratio >= 0.8 for longer names
    """
    a = extract_first_name(name_a)
    b = extract_first_name(name_b)

    if not a or not b:
        return False

    # Exact match
    if a == b:
        return True

    # Strip trailing period (for initials like "J.")
    a_clean = a.rstrip(".")
    b_clean = b.rstrip(".")

    # Initial match: one is a single character that matches the start of the other
    if len(a_clean) == 1 and b_clean.startswith(a_clean):
        return True
    if len(b_clean) == 1 and a_clean.startswith(b_clean):
        return True

    # Fuzzy match for longer names (handles minor spelling variations)
    ratio = SequenceMatcher(None, a, b).ratio()
    if ratio >= 0.8:
        return True

    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # ------------------------------------------------------------------
    # Step 1 & 2: Load all per-department files and build lookup
    # ------------------------------------------------------------------
    print("Loading per-department Harvard JSON files...")
    last_name_lookup = {}   # normalized_last_name -> list of (clean_name, department)
    dept_file_count = 0
    total_dept_entries = 0

    for fname in sorted(os.listdir(HARVARD_DIR)):
        if not fname.endswith(".json"):
            continue
        dept_file_count += 1
        fpath = os.path.join(HARVARD_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            entries = json.load(f)

        for entry in entries:
            raw_name = entry.get("name", "")
            department = entry.get("department", "")
            clean_name = strip_dr_prefix(raw_name)
            last = extract_last_name(clean_name)
            if last:
                last_name_lookup.setdefault(last, []).append((clean_name, department))
                total_dept_entries += 1

    print(f"  Loaded {dept_file_count} department files with {total_dept_entries} entries.")
    print(f"  Unique last names in lookup: {len(last_name_lookup)}")

    # ------------------------------------------------------------------
    # Step 3: Load faculty_working.json
    # ------------------------------------------------------------------
    print(f"\nLoading faculty_working.json from:\n  {FACULTY_WORKING_PATH}")
    with open(FACULTY_WORKING_PATH, "r", encoding="utf-8") as f:
        faculty = json.load(f)

    print(f"  Total entries: {len(faculty)}")
    various_before = sum(1 for e in faculty if e.get("department") == "Various")
    print(f"  Entries with department='Various': {various_before}")

    # ------------------------------------------------------------------
    # Step 4: Match and update
    # ------------------------------------------------------------------
    print("\nMatching faculty to departments...")
    matched = 0
    unmatched_names = []

    for entry in faculty:
        if entry.get("department") != "Various":
            continue  # already has a real department

        full_name = entry.get("name", "")
        last = extract_last_name(full_name)

        if last not in last_name_lookup:
            unmatched_names.append(full_name)
            continue

        candidates = last_name_lookup[last]
        found = False
        for cand_name, cand_dept in candidates:
            if first_name_matches(full_name, cand_name):
                entry["department"] = cand_dept
                matched += 1
                found = True
                break  # use the first match

        if not found:
            unmatched_names.append(full_name)

    # ------------------------------------------------------------------
    # Step 5: Save updated file
    # ------------------------------------------------------------------
    print(f"\nSaving updated faculty_working.json...")
    with open(FACULTY_WORKING_PATH, "w", encoding="utf-8") as f:
        json.dump(faculty, f, indent=2, ensure_ascii=False)
    print("  Saved.")

    # ------------------------------------------------------------------
    # Step 6: Print statistics
    # ------------------------------------------------------------------
    various_after = sum(1 for e in faculty if e.get("department") == "Various")
    print("\n" + "=" * 60)
    print("BACKFILL STATISTICS")
    print("=" * 60)
    print(f"  Total faculty_working entries : {len(faculty)}")
    print(f"  Matched & updated             : {matched}")
    print(f"  Still 'Various'               : {various_after}")
    print(f"  Match rate                     : {matched / len(faculty) * 100:.1f}%")
    print("=" * 60)

    # Department distribution
    dept_counts = {}
    for entry in faculty:
        dept = entry.get("department", "Unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    print("\nDepartment distribution (updated file):")
    for dept, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:4d}  {dept}")

    # Show a few unmatched names for debugging
    if unmatched_names:
        print(f"\nSample unmatched names (first 20 of {len(unmatched_names)}):")
        for name in unmatched_names[:20]:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
