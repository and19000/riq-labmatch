# Data Folder

This folder contains runtime faculty datasets used by the app and derived reference files.

## Contents

- `v2/all_faculty.json` - source of truth used by the app loader
- `master_faculty_database.csv` - unified canonicalized CSV across 8 schools
- School folders (`Harvard/`, `MIT/`, `Northeastern/`, `Tufts/`, `BU/`, `Stanford/`, `Yale/`, `Princeton/`)
  - canonicalized CSV outputs
  - department-level JSON exports (reference/organization)

## Generation

- Build master CSV: `python3 -m api_evaluation.utils.build_master_database`
- Convert CSV to v2 JSON: `python3 -m api_evaluation.utils.csv_to_v2_json`
- Split v2 JSON by school/department: `python3 -m api_evaluation.utils.split_v2_by_school_department`
