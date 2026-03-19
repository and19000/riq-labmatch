# Northeastern Data

This folder contains Northeastern faculty data artifacts used by RIQ.

## Coverage

- Professors: **709**
- Status: **473 complete**, **236 partial**, **0 needs_review**
- Complete rate: **66.7%**
- Email presence rate: **67.6%**
- Departments represented (from canonicalized CSV): **28**
- Department JSON files in this folder: **54**

## Key Files

- `northeastern_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
