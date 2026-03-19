# Backend

Flask backend for RIQ LabMatch.

## Key File

- `app.py` - app initialization, data loading, auth, matching routes, browse/search routes

## Runtime

- Reads faculty source from `Data/v2/all_faculty.json`
- Serves templates from `frontend/templates`
- Serves static files from `frontend/static`

## Start

- `python run.py`
- or `python backend/app.py`
