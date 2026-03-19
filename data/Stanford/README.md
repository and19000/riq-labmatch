# Stanford Data

This folder contains Stanford faculty data artifacts used by RIQ.

## Coverage

- Professors: **350**
- Status: **316 complete**, **34 partial**, **0 needs_review**
- Complete rate: **90.3%**
- Email presence rate: **90.3%**
- Departments represented (from canonicalized CSV): **23**
- Department JSON files in this folder: **50**

## Key Files

- `stanford_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
