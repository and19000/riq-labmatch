# RIQ LabMatch

RIQ (Research Intelligence & Qualification) is a faculty discovery and matching platform for research opportunities across eight universities.

## Quick Start

1. Create and activate a virtual environment:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables in `.env` (at minimum `OPENAI_API_KEY` for AI features).
4. Start the app:
   - `python run.py` (recommended)
   - or `python backend/app.py`
5. Open `http://localhost:5001`

## Project Layout

- `backend/` Flask backend and route logic
- `frontend/` Jinja templates + static assets
- `Data/` runtime faculty datasets (v2 JSON source of truth + school exports)
- `api_evaluation/` Exa/Tavily search and filtering pipeline
- `reports/` generated search/filter/combined reports
- `docs/` project documentation and product overview
- `scripts/` utility and maintenance scripts

## Data Source of Truth

The app loads faculty from `Data/v2/all_faculty.json` via `load_faculty()`.

## Notes

- Matching and email drafting features use OpenAI.
- Password reset email flow requires SMTP environment variables.
