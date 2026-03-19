# Yale Data

This folder contains Yale faculty data artifacts used by RIQ.

## Coverage

- Professors: **491**
- Status: **448 complete**, **43 partial**, **0 needs_review**
- Complete rate: **91.2%**
- Email presence rate: **91.2%**
- Departments represented (from canonicalized CSV): **23**
- Department JSON files in this folder: **49**

## Key Files

- `yale_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
