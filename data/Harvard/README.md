# Harvard Data

This folder contains Harvard faculty data artifacts used by RIQ.

## Coverage

- Professors: **2041**
- Status: **1724 complete**, **317 partial**, **0 needs_review**
- Complete rate: **84.5%**
- Email presence rate: **85.3%**
- Departments represented (from canonicalized CSV): **68**
- Department JSON files in this folder: **113**

## Key Files

- `harvard_canonicalized.csv` - display-ready canonicalized CSV
- `*_canonicalized_full.csv` / `*_needs_review.csv` (if present)
- `*.json` department exports derived from `Data/v2/all_faculty.json`

## Relationship to RIQ

These files feed browse/search organization and provide school-specific reference data.
The app runtime source of truth remains `Data/v2/all_faculty.json`.
