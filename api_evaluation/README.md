# API Evaluation Pipeline

Exa/Tavily pipeline for discovering faculty websites/emails and canonicalizing outputs.

## What It Does

- Executes search runs (Exa primary, Tavily fallback)
- Filters and canonicalizes raw hits
- Produces per-university outputs and reports
- Builds merged/master datasets for app ingestion

## Common Commands

- Run university pipeline: `python3 -m api_evaluation.run_all_universities --config api_evaluation/universities.json --report reports/final_combined_report.md`
- Merge Harvard phases: `python3 -m api_evaluation.utils.merge_harvard`
- Build master DB: `python3 -m api_evaluation.utils.build_master_database`
- CSV -> v2 JSON: `python3 -m api_evaluation.utils.csv_to_v2_json`
