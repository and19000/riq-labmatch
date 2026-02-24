# RIQ LabMatch - Improvement Notes

Assessment of current implementation issues, ranked by impact, with suggested fixes.

---

## High Priority

### 1. Monolithic `app.py` (2100+ lines)
All routes, models, helpers, data loading, email logic, and matching integration live in one file. This makes navigation, testing, and collaboration difficult.

**Fix**: Split into Flask Blueprints:
- `routes/auth.py` — login, signup, password reset
- `routes/browse.py` — `/general`, `/matches`, filtering
- `routes/email.py` — `/draft-email`, `/bulk-email`
- `routes/account.py` — `/account`, `/saved`, `/compare-labs`
- `models.py` — User, UserProfile, SavedPI, Resume, PasswordResetToken
- `utils.py` — normalize_faculty_entry, load_faculty, dept_field_key

### 2. Rudimentary Data Caching
`load_faculty()` uses a basic dict cache with 1-hour TTL but re-reads all JSON files from disk when cache expires. With 1200+ faculty across multiple files, this causes latency spikes.

**Fix**: Load data once at startup into an in-memory store. Use a `/admin/reload-data` endpoint (protected) to refresh without restart. Consider `functools.lru_cache` or Flask-Caching with Redis for production.

### 3. `convert_faculty_data.py` Was Harvard-Only
Previously hardcoded Harvard ID prefixes, location, and institution name. Now fixed to accept `--institution` parameter, but the script could be further improved by auto-detecting institution from the pipeline output metadata.

### 4. Email Field Type Inconsistency
Harvard data: `email: "string"`. NSF data: `email: ["list"]`. MIT data: `email: "string"`. The `normalize_faculty_entry()` function handles this, but it's fragile. If a new data source uses a different format, it could break silently.

**Fix**: Standardize at the data level — all data files should use `email: "string"` consistently. Add validation in the pipeline export step.

### 5. Hardcoded Harvard Logos (Now Fixed)
Both `general.html` and `matches.html` previously rendered a crimson "H" for every professor. Now uses conditional rendering based on school name.

---

## Medium Priority

### 6. Server Sends ALL Data to Template
The `/general` route loads all faculty into the Jinja2 template. At 1200+ records (and growing), the HTML page becomes large. Currently mitigated by server-side pagination (15 per page), but the full dataset is still loaded into memory for filtering.

**Fix**: Implement proper server-side pagination with SQL or in-memory slicing before template rendering. Currently `load_faculty()` returns all records; the route should slice before passing to template.

### 7. Client-Side Search Doesn't Scale
The JS search in `general.html` iterates all visible `<tr>` DOM rows using `.includes()`. With 15 per page this is fine, but if someone removes pagination or the dataset grows, it becomes sluggish.

**Fix**: Since server-side pagination is already in place, convert search to a server-side endpoint (e.g., `/api/search?q=...`) that queries the in-memory dataset and returns JSON. Use debounced fetch instead of DOM iteration.

### 8. No Automated Tests
Zero test files found in the project. The matching algorithm, data normalization, and route logic are all untested. This is risky as changes could silently break matching quality.

**Fix**: Add a `tests/` directory with:
- `test_matching.py` — unit tests for MatchingServiceV2 scoring
- `test_data.py` — validation that JSON files load correctly, schema checks
- `test_routes.py` — Flask test client for route responses
- `test_normalization.py` — edge cases for normalize_faculty_entry

### 9. Department Defaults to "Various"
Many Harvard faculty have `department: "Various"` because the pipeline's field extraction from OpenAlex concepts was unreliable (no `level` field in `x_concepts`). The MIT data now uses `topics[].field.display_name` which is more accurate.

**Fix**: Re-run the Harvard pipeline with improved department extraction (using topic field names instead of concept levels), or backfill departments from the per-department JSON files in `/Data/Harvard/`.

### 10. No Data Freshness Tracking
No way to know when faculty data was last updated. Users may be seeing stale information.

**Fix**: Add `last_updated` metadata to each JSON data file. Display "Data last updated: Jan 21, 2026" in the footer or filter sidebar.

---

## Lower Priority

### 11. Large CSS File (65KB)
`style.css` is a single 3500+ line file covering all pages. Makes it hard to find and modify styles for specific components.

**Fix**: Split into `base.css`, `components.css`, `pages/general.css`, etc. Or adopt a utility-first approach (Tailwind) for new components.

### 12. Missing Template Guards
Some optional fields like `google_scholar`, `specific_location`, and `research_topics` are rendered without `{% if %}` guards, which could cause display issues with incomplete data (e.g., showing "None" or empty elements).

**Fix**: Audit all templates and add `{% if field %}` guards around optional fields. The MIT data in particular has empty `email` and `website` fields.

### 13. Pipeline Requires Manual Steps
Running the pipeline for a new institution requires: (1) configure in the script, (2) run from command line, (3) convert output, (4) update app.py. There's no CI/CD or scheduled refresh.

**Fix**: Create a `Makefile` or management script (`manage.py`) with commands like:
```
python manage.py collect --institution mit
python manage.py convert --institution mit
python manage.py reload-data
```

---

## Architecture Improvement Roadmap

### Phase 1: Code Organization (1-2 days)
- Split app.py into Blueprints
- Extract models to `models.py`
- Create `utils/data.py` for data loading
- Add basic pytest structure

### Phase 2: Data Quality (1 day)
- Backfill Harvard departments from per-department files
- Standardize email format across all data sources
- Add data validation script

### Phase 3: Performance (1 day)
- Implement proper in-memory data store with startup loading
- Add server-side search API endpoint
- Optimize template rendering (avoid sending unused fields)

### Phase 4: Testing (ongoing)
- Unit tests for matching algorithm
- Integration tests for routes
- Data schema validation tests
- CI pipeline (GitHub Actions)
