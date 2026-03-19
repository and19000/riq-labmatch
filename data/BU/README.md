# BU Data

This folder contains BU faculty data artifacts used by RIQ.

## Coverage

- Professors: **893**
- Status: **713 complete**, **180 partial**, **0 needs_review**
- Complete rate: **79.8%**
- Email presence rate: **79.8%**
- Departments represented (from canonicalized CSV): **28**
- Department JSON files in this folder: **54**

## Key Files

- `bu_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
