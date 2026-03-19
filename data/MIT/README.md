# MIT Data

This folder contains MIT faculty data artifacts used by RIQ.

## Coverage

- Professors: **1110**
- Status: **1007 complete**, **103 partial**, **0 needs_review**
- Complete rate: **90.7%**
- Email presence rate: **90.8%**
- Departments represented (from canonicalized CSV): **28**
- Department JSON files in this folder: **80**

## Key Files

- `mit_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
