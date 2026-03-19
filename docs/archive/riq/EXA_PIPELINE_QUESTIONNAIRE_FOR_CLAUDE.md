## RIQ Faculty / Exa Pipeline – Condensed Context for Claude

This file summarizes my current pipelines and answers the **Pipeline Integration Questionnaire** in a compact way. Claude can rely on this plus the referenced code/CSV files to design an end‑to‑end solution.

---

## 1. Current Directory & Data Setup

- **Upstream scraping:**  
  - A separate repo/submodule `faculty_pipeline` scrapes Harvard-affiliated faculty from various directories and writes a master CSV.  
  - This repo (`riq-labmatch`) treats that CSV as **input**, not something it generates.

- **Gold input CSVs (in `api_evaluation/`):**
  - `gold_standard_affiliation_only.csv`
  - `gold_standard_affiliation_department.csv`
  - `gold_standard_harvard_full.csv` (1,477 Harvard rows, built from `faculty_pipeline/output/harvard_affiliated_faculty.csv`)
  - Common columns: `name`, `affiliation`, `department`, `gold_email`, `gold_website`.

- **How they are loaded:**

```python
12:82:api_evaluation/evaluate.py
def load_gold_standard(filepath: str) -> List[Dict]:
    professors = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prof = {
                "name": row.get("name", row.get("Name", row.get("professor_name", ""))).strip(),
                "affiliation": row.get("affiliation", row.get("Affiliation", row.get("institution", ""))).strip(),
                "department": row.get("department", row.get("Department", "")).strip(),
                "gold_email": row.get("gold_email", row.get("email", row.get("Email", ""))).strip().lower(),
                "gold_website": row.get("gold_website", row.get("website", row.get("Website", ""))).strip().lower(),
            }
            if prof["name"] and prof["affiliation"]:
                professors.append(prof)
    return professors
```

---

## 2. Exa / Tavily / Brave Evaluation Pipeline

- **Location:** `api_evaluation/`
- **Goal:** Compare Exa, Tavily, and Brave on discovering websites/emails for Harvard professors.

- **Core evaluation script:** `api_evaluation/evaluate.py`
  - Takes a gold CSV and an output directory.
  - For each API:
    - Calls `search_professor(name, affiliation, department)`.
    - Extracts **all URLs** and **all emails**, then picks the first as `found_website` / `found_email`.
    - Computes match metrics vs `gold_website` and `gold_email`.

```python
128:182:api_evaluation/evaluate.py
def evaluate_api(api, professors: List[Dict], api_name: str) -> List[ProfessorResult]:
    results = []
    for i, prof in enumerate(professors):
        search_results = api.search_professor(
            name=prof["name"],
            affiliation=prof["affiliation"],
            department=prof.get("department", ""),
        )
        all_urls = [r.url for r in search_results if r.url]
        found_website = all_urls[0] if all_urls else ""
        all_emails = extract_emails_from_results(search_results, prof["name"])
        found_email = all_emails[0] if all_emails else ""
        website_match = check_website_match(found_website, prof["gold_website"], prof["name"])
        email_match = check_email_match(found_email, prof["gold_email"])
        result = ProfessorResult(
            name=prof["name"],
            affiliation=prof["affiliation"],
            department=prof.get("department", ""),
            gold_email=prof["gold_email"],
            gold_website=prof["gold_website"],
            found_website=found_website,
            found_email=found_email,
            all_urls=all_urls[:5],
            all_emails=all_emails[:3],
            website_exact_match=website_match["exact_match"],
            website_domain_match=website_match["domain_match"],
            website_name_in_url=website_match["name_in_url"],
            email_exact_match=email_match["exact_match"],
            email_domain_match=email_match["domain_match"],
            queries_used=api.query_count,
        )
        results.append(result)
```

- **Email extraction heuristics:** `api_evaluation/extract_email.py`
  - Regex over snippets/content.
  - Filters generic addresses (`info@`, `contact@`, etc.).
  - Scores higher if local part contains last name, first name, or standard initials patterns; prefers `.edu` domains.

---

## 3. Exa Search Wrapper & Query Strategy

- **File:** `api_evaluation/search_apis/exa_search.py`
- **Client:** `exa_py.Exa`
- **Search type:** `type="auto"` (Exa decides search mode).
- **Professor-level query strategy:**

```python
10:71:api_evaluation/search_apis/exa_search.py
class ExaSearch(BaseSearch):
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        response = self.client.search(
            query=query,
            type="auto",
            num_results=num_results,
            contents={"text": {"max_characters": 5000}},
        )

    def search_professor(self, name: str, affiliation: str, department: str = "") -> List[SearchResult]:
        """Exa-optimized: natural language queries."""
        results = []
        query1 = f"{name} {affiliation} professor profile"
        results.extend(self._safe_search(query1, 5))

        query2 = f"{name} {affiliation} faculty"
        if department:
            query2 = f"{name} {affiliation} {department} faculty"
        results.extend(self._safe_search(query2, 5))

        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)
        return unique[:10]
```

- **Tavily & Brave wrappers:** similar pattern, located in:
  - `api_evaluation/search_apis/tavily_search.py`
  - `api_evaluation/search_apis/brave_search.py`
  - Used only in the **80-professor comparison**, not the full 1,477 run.

---

## 4. Full Harvard Exa Run (1477 Professors)

- **Entry script:** `api_evaluation/exa/run_exa_until_credits.py`
- **Docs:** `docs/exa_run.md`
- **High-level behavior:**
  - Loads `gold_standard_harvard_full.csv` (1,477 rows).
  - For each professor, uses `ExaSearch.search_professor` + `extract_email`.
  - Writes:
    - Structured results JSON (`exa_results.json`)
    - Flat CSV (`exa_found.csv`)
    - `checkpoint.json`, `run.log`
  - Supports:
    - `--max-professors` cap
    - `--dry-run` (mock 2 rows, no API calls)
    - Resume from checkpoint on re-run.

- **How to run (from repo root, using venv):**

```bash
cd api_evaluation
../.venv/bin/python exa/run_exa_until_credits.py \
  --input gold_standard_harvard_full.csv \
  --output exa/results_exa_until_credits \
  --max-professors 10000
```

- **Where the full Exa results are stored:**
  - Primary:
    - `api_evaluation/exa/results_exa_until_credits/exa_results.json`
    - `api_evaluation/exa/results_exa_until_credits/exa_found.csv`
  - Copy for analysis/sharing:
    - `data/exa_harvard/exa_harvard_found.csv`

---

## 5. Manual Evaluation & Quality

- **80-professor evaluation CSVs:**
  - `api_evaluation/results_affiliation_only/exa_found_80.csv` – Exa output on the original 80-prof test set.

- **Full-run manual sample (80 rows):**
  - `data/exa_harvard/exa_manual_eval_80.csv`
    - Random sample (seeded) of 80 rows from the full 1477 Exa run.
    - Same core columns as `exa_found.csv` plus:
      - `website_label`
      - `email_label`
      - `notes`
    - Intended for human review of correctness/partial correctness.

- **Acceptability criteria & next steps:** `docs/EXA_NEXT_STEPS_PLAN.md`
  - Defines when a website/email should be considered **Correct / Partially correct / Wrong**.
  - Recommends:
    - Labeling the 80-row sample (and potentially a larger subsample).
    - Using those labels to compute **true accuracy**, not just exact match vs. gold.
    - Designing filtering/ranking over `all_urls` and `all_emails` if needed.

---

## 6. What I Want Claude to Help With

Given all of the above, I want Claude to:

1. **Design an end-to-end pipeline** that:
   - Starts from a directory-scraped faculty CSV (like `gold_standard_harvard_full.csv`).
   - Uses Exa (and optionally Tavily/Brave) to find candidate websites and emails.
   - Applies scoring/ranking to pick:
     - `canonical_website_url`
     - `canonical_email`
   - Handles duplicates across directories/universities.
   - Produces a clean, re-runnable output CSV/DB suitable for the RIQ app.

2. **Propose and, where possible, implement code** to:
   - Turn `exa_found.csv` / `exa_results.json` into:
     - A labeled evaluation sheet (if needed).
     - A canonicalized output with confidence scores and labels.
   - Incorporate acceptability criteria (from `docs/EXA_NEXT_STEPS_PLAN.md`) into filtering logic.

3. **Make the pipeline generic** so I can:
   - Extend from Harvard → MIT → other universities by:
     - Swapping in new directory-scraped CSVs.
     - Configuring institution-specific domain whitelists and heuristics.

Claude can use this file, plus:

- `api_evaluation/evaluate.py`
- `api_evaluation/search_apis/*.py`
- `api_evaluation/exa/run_exa_until_credits.py`
- `api_evaluation/exa/EXA_PIPELINE_SUMMARY_FOR_CLAUDE.md`
- `docs/exa_run.md`
- `docs/EXA_NEXT_STEPS_PLAN.md`
- `data/exa_harvard/exa_harvard_found.csv`
- `data/exa_harvard/exa_manual_eval_80.csv`

to reason about the existing system and propose concrete next‑step code and data transformations.

