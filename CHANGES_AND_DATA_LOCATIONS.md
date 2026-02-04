# Changelog & Data Locations (for GitHub)

## What has changed (recent updates)

### Bug fixes
- **KeyError: 'school'** – All PI dict access in `app.py` now uses `.get()` for `school`, `department`, `location`, etc. NSF data uses `institution`; the app normalizes to `school` in `load_faculty()` and uses safe access everywhere.
- **Jinja2 `min` undefined** – The “Showing X–Y of Z labs” text in `general.html` no longer uses `min()` in the template. The view now passes `show_start` and `show_end` to the template.

### Find Labs (general) page
- **Pagination** – 20 professors per page with Google-style pagination (Previous, page numbers, Next). Filter query params (school, department, technique, location) are preserved in pagination links.
- **Priority order** – PIs with email and website are shown first; NSF-only (minimal data) PIs are shown later to improve perceived performance and usefulness.
- **Filter choices cached** – Schools, departments, techniques, and locations are built once per faculty load via `get_filter_choices()` and cached to avoid repeated full-list scans.

### Onboarding & profile
- **Research topics** – Multi-select dropdown of common topics (e.g. machine learning, cancer research) plus an “Other” free-text field to avoid typos.
- **Institution (optional)** – User’s institution is a dropdown filled from the same institution list as the Find Labs filter; stored in `UserProfile.institution`.
- **Account page** – Displays the user’s institution when set.

### Security & config
- Password reset: 8-character minimum; `.env.example` includes placeholders for `DATABASE_URL`, SMTP, etc.

---

## Where the NSF data (all institutions) lives

**NSF faculty/institution data is not stored in the database.** It is loaded from JSON files at runtime.

### Primary data file (institutions + all PIs)

| What | Where |
|------|--------|
| **NSF all-PI data (preferred)** | **`faculty_pipeline/output/nsf_all_faculty.json`** |
| Path in code | `OUTPUT_DIR = faculty_pipeline/output/`, `NSF_ALL_PATH = output/nsf_all_faculty.json` |
| Fallback 1 | `faculty_pipeline/output/harvard_mvp_1500.json` |
| Fallback 2 | `faculty_pipeline/data/faculty_working.json` |

The app chooses the source in this order (see `app.py` around line 305):

1. If `output/nsf_all_faculty.json` exists → use it (NSF data, all institutions).
2. Else if `output/harvard_mvp_1500.json` exists → use it.
3. Else → use `data/faculty_working.json`.

**Generating/updating NSF data:**  
Run `scripts/load_all_nsf_data.py` (with NSF JSON files in the expected locations). It writes `output/nsf_all_faculty.json`. Optionally run `scripts/update_faculty_data.py` to refresh that file.

### What is in the database (SQLite)

The database holds **user and app state only**; it does **not** store the list of institutions or NSF faculty.

| Table | Purpose |
|-------|---------|
| **user** | Accounts: username, email, password_hash, created_at |
| **user_profile** | Profile: research_field, research_topics, academic_level, work_style, needs_funding, **institution** (optional), onboarding_completeness, etc. |
| **saved_pi** | User-saved PIs: user_id, pi_id, pi_email, created_at |
| **resume** | Uploaded resumes: user_id, filename, file_path, resume_text, uploaded_at |
| **password_reset_token** | Forgot-password tokens: user_id, token, expires_at, used |

- **Institution list in the UI** – The dropdowns for “Institution” (Find Labs) and “Your institution” (onboarding) are built from the **current faculty JSON** (e.g. `nsf_all_faculty.json`), not from the database. So “where the database contains the NSF data of all institutions” is: **it doesn’t**; the app reads institutions from the JSON file above.

---

## Quick reference

- **All institutions / NSF faculty source:** `faculty_pipeline/output/nsf_all_faculty.json` (file, not DB).
- **Database:** SQLite (path from `DATABASE_URL` or Flask default); tables: user, user_profile, saved_pi, resume, password_reset_token.
- **Faculty list in memory:** Loaded and cached from the JSON path chosen at startup; cache TTL 1 hour.
