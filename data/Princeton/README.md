# Princeton Data

This folder contains Princeton faculty data artifacts used by RIQ.

## Coverage

- Professors: **482**
- Status: **301 complete**, **181 partial**, **0 needs_review**
- Complete rate: **62.4%**
- Email presence rate: **62.7%**
- Departments represented (from canonicalized CSV): **22**
- Department JSON files in this folder: **49**

## Key Files

- `princeton_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
