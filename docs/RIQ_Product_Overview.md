# RIQ - Research Intelligence & Qualification Platform

## 1) What RIQ Is

RIQ is a faculty discovery and matching platform designed to help users find and contact research labs across top universities.

Current scope:
- 8 universities
- ~7,000 professors in the unified dataset
- Browse, search, matching, and outreach workflows in a single app

## 2) Current Features

- Faculty browse/search with filters (school, department, location)
- Professor listing cards with website, email, department, and institution
- Lab matching workflow (profile-driven)
- Email drafting tools (single, bulk, multi)
- Save and compare faculty
- Help page with school coverage details

## 3) Data Pipeline

- Faculty names are sourced from university directories and NSF-oriented sources
- Exa is the primary discovery API; Tavily is fallback/secondary coverage
- Filtering pipeline canonicalizes websites/emails and removes junk
- Department inference leverages URL/domain patterns and school configs
- University-specific config files support extensible multi-school ingestion

## 4) Data Coverage Summary

| University | Professors | Complete Rate | Email Rate |
|------------|-----------:|--------------:|-----------:|
| Harvard | 2,041 | 84% | 77% |
| MIT | 1,110 | 91% | 88% |
| Tufts | 893 | 82% | 78% |
| BU | 893 | 80% | 78% |
| Northeastern | 709 | 67% | 57% |
| Yale | 491 | 91% | 75% |
| Stanford | 350 | 90% | 90% |
| Princeton | 482 | 62% | 51% |
| **Total** | **6,969** | **83%** | **75%** |

## 5) Tech Stack

- Backend: Flask (Python)
- Frontend: Jinja templates + vanilla JavaScript
- Data: JSON (v2 schema), CSV for pipeline artifacts
- APIs: Exa, Tavily, OpenAI (matching/email features)

## 6) How to Run

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Configure environment variables:
   - `OPENAI_API_KEY`
   - SMTP credentials for email flows (`SMTP_*`, `FROM_EMAIL`)
3. Start app:
   - `python run.py` (recommended)
   - or `python backend/app.py`
4. Access:
   - `http://localhost:5001`

## 7) How to Add a New University

1. Add university filter config in `api_evaluation/filter/configs/`
2. Gather faculty seed names (directory scrape or existing list)
3. Run Exa/Tavily search pipeline
4. Run filter canonicalization
5. Rebuild master CSV and v2 JSON:
   - `python3 -m api_evaluation.utils.build_master_database`
   - `python3 -m api_evaluation.utils.csv_to_v2_json`
6. Ensure school is represented in backend allowlist and logos:
   - `ENABLED_SCHOOLS`
   - `SCHOOL_LOGOS`

## 8) Known Limitations

- Some professors have valid websites but no reliable email (partial status)
- Northeastern and Princeton currently show lower email coverage
- Phone values are sparse
- Rich research-interest/publication metadata remains limited for many entries
