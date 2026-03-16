# Exa Pipeline Summary (Harvard Run)

This file is meant to be pasted or uploaded into another AI (e.g. Claude) to explain **what data exists**, **how it was generated**, and **where to look** when designing a filtering/selection strategy for the best professor websites and emails.

---

## 1. What this run did

- **Goal:** Run the **same Exa search pipeline** we used for the 80-professor test, but now over the **full Harvard faculty dataset**.
- **API used:** Exa (via `exa-py`).
- **Entry script:** `api_evaluation/exa/run_exa_until_credits.py`
- **Command used for full Harvard run:**

  ```bash
  cd api_evaluation
  caffeinate -i -s ../.venv/bin/python exa/run_exa_until_credits.py \
    --input gold_standard_harvard_full.csv \
    --output exa/results_exa_until_credits \
    --max-professors 10000
  ```

- **Input CSV for this run:** `api_evaluation/gold_standard_harvard_full.csv` (1,477 rows)
  - Built from `faculty_pipeline/output/harvard_affiliated_faculty.csv`.
  - Columns (strings):
    - `name` – professor name.
    - `affiliation` – institution text (e.g. `Harvard University`).
    - `department` – department text (may be empty).
    - `gold_email` – email from our Harvard dataset (used only as reference, not required to match).
    - `gold_website` – website URL from our Harvard dataset (reference only).

- **For each professor**, we reused the exact same Exa flow as the 80-test:
  - Construct multiple queries (through `ExaSearch.search_professor`):
    - Example patterns:
      - `"<name>" site:<institution-domain>`
      - `"<name>" <affiliation>`
      - `"<name>" professor <affiliation>`
      - For Exa’s specialization: `<name> <affiliation> professor profile`, `<name> <affiliation> <department> faculty`, etc.
  - Call Exa, asking for up to 5–10 results, with page text content when available.
  - Normalize all URLs and deduplicate by URL.
  - Run `extract_email.py` over:
    - Page content (when Exa returned it),
    - Result snippets,
    - Then fetched pages (for top hits),
    to extract the most likely professor email(s).
  - Choose a **top website** (`found_website`) and **top email** (`found_email`) for each professor, but also keep **all URLs** and **all extracted emails** for downstream filtering.

This is the same behavior and schema as the earlier 80-professor evaluation, just scaled up.

---

## 2. Where the results live (files)

All outputs for this Harvard-wide Exa run are under:

- **Directory:** `api_evaluation/exa/results_exa_until_credits/`

**Key files you should look at:**

1. `exa_results.json`
   - Full structured JSON, including:
     - Global stats and metrics for the run.
     - A list of per-professor result objects.

2. `exa_found.csv`
   - Flat CSV view, one row per professor.
   - Easier for spreadsheet inspection and simple heuristics.

3. `run.log`
   - Text log of the run, with lines like `[n/1477] Name (Affiliation)` and short outcome messages.

4. `checkpoint.json`
   - Used internally for resume; not needed for analysis now that run is complete.

(There may also be `failures.csv` if any rows failed; those are small and only contain error diagnostics.)

---

## 3. High-level metrics (for context)

From `exa_results.json`:

- **Professors processed:** `1477` (all rows in `gold_standard_harvard_full.csv`).
- **Exa usage:**
  - `queries`: `2188`
  - `estimated_cost`: `10.94` (approx, in USD-equivalent units used in the script).

- **Website metrics:**
  - `found_any` websites: `1351 / 1477` (≈ 91.5%) – at least one website URL was found.
  - `exact_match` vs reference `gold_website`: `372 / 1477` (≈ 25.2%).
  - `domain_match` vs reference: `442 / 1477` (≈ 29.9%).
  - `name_in_url`: `839 / 1477` (≈ 56.8%).

- **Email metrics:**
  - `found_any` emails: `1123 / 1477` (≈ 76.0%).
  - Exact email/domain match rates are lower because our “gold” emails are noisy/missing for many rows.

These metrics are **only for evaluation** against our current Harvard dataset and do **not** indicate that Exa’s results are wrong when they disagree with gold; the gold itself often has non-Harvard domains or missing info.

---

## 4. Per-professor schema (JSON)

Each professor in `exa_results.json` is a dict with these fields (keys confirmed from the file):

```json
{
  "name": "Walter C. Willett",
  "affiliation": "Harvard University",
  "department": "",          // often empty in this run
  "gold_email": "willett@g.uchicago.edu",
  "gold_website": "https://hsph.harvard.edu/profile/walter-c-willett/",

  "found_website": "https://hsph.harvard.edu/profile/walter-c-willett/",
  "found_email": "wwillett@hsph.harvard.edu",

  "all_urls": [
    "https://hsph.harvard.edu/profile/walter-c-willett/",
    "https://hsph.harvard.edu/exec-ed/faculty/walter-willett/",
    "https://hks.harvard.edu/about/walter-willett/",
    "https://linkedin.com/in/jules-dienstag-b3966b135",
    "https://linkedin.com/in/karl-wilcox-480647230"
  ],
  "all_emails": [
    "wwillett@hsph.harvard.edu"
  ],

  "website_exact_match": true,      // vs gold_website
  "website_domain_match": true,     // same domain as gold_website
  "website_name_in_url": true,      // last name appears in URL

  "email_exact_match": false,       // vs gold_email (which may be wrong/outdated)
  "email_domain_match": false,

  "queries_used": 2                 // cumulative Exa queries when this row was written
}
```

**Important notes for filtering:**

- `gold_email` and `gold_website` come from our **existing Harvard dataset** and are sometimes non-Harvard or outdated.
- `found_website` and `found_email` are the **top picks** from the Exa pipeline.
- `all_urls` and `all_emails` are where you will likely want to focus for ranking and cleaning.

---

## 5. Per-professor schema (CSV `exa_found.csv`)

`exa_found.csv` (same columns as the earlier `exa_found_80.csv`) has header:

```text
name,affiliation,department,gold_email,gold_website,found_website,found_email,all_urls,all_emails
```

- `all_urls` is a single string with URLs separated by `"; "` (semicolon + space).
- `all_emails` is a single string with emails separated by `"; "`.

**Example row (line 2):**

```text
Walter C. Willett,Harvard University,,willett@g.uchicago.edu,https://hsph.harvard.edu/profile/walter-c-willett/,https://hsph.harvard.edu/profile/walter-c-willett/,wwillett@hsph.harvard.edu,https://hsph.harvard.edu/profile/walter-c-willett/; https://hsph.harvard.edu/exec-ed/faculty/walter-willett/; https://hks.harvard.edu/about/walter-willett; https://linkedin.com/in/jules-dienstag-b3966b135; https://linkedin.com/in/karl-wilcox-480647230,wwillett@hsph.harvard.edu
```

For most downstream tasks (like designing filters), it’s easiest to:

- Parse `all_urls` into a list by splitting on `"; "`.
- Parse `all_emails` into a list the same way.

---

## 6. How the pipeline made choices (behavioral details)

This section is to help you (Claude) reason about what the data means and what assumptions were baked in.

### 6.1 Search queries

For each professor (`name`, `affiliation`, optional `department`), the Exa wrapper applies multiple query strategies (through `ExaSearch` and `BaseSearch`):

- **Institution-domain–restricted query** when we can map the affiliation to a domain (e.g. `harvard.edu`):
  - `"<name>" site:harvard.edu`
- **General name + affiliation query:**
  - `"<name>" <affiliation>`, with optional department appended.
- **Name + "professor" + affiliation:**
  - `"<name>" professor <affiliation>`.
- **Exa-specific natural language queries** (from `ExaSearch.search_professor`):
  - `<name> <affiliation> professor profile`
  - `<name> <affiliation> faculty`, or `<name> <affiliation> <department> faculty`.

Results are deduplicated by URL and truncated to the top N.

### 6.2 Email extraction heuristics

From `extract_email.py`:

- Extracts all email-like strings with a regex.
- Filters out **generic/local-part** emails like `info@`, `contact@`, `support@`, `department@`, etc.
- Scores remaining emails higher if:
  - The professor’s **last name** appears in the local part.
  - The professor’s **first name** appears.
  - Common combinations like `jdoe` / `doej` for John Doe.
  - `.edu` domains get a small bonus.
- Returns the **top-scoring email**, and also keeps a short list of candidates in `all_emails`.

### 6.3 URL selection and flags

- `found_website` is the **first URL** in `all_urls` after the pipeline’s ranking.
- `website_exact_match` is computed vs. `gold_website` using a normalization that:
  - Lowercases,
  - Strips `http(s)://` and `www.`,
  - Strips trailing `/`.
- `website_domain_match` compares domains (e.g. `hsph.harvard.edu`).
- `website_name_in_url` checks if the professor’s **last name** appears anywhere in the normalized URL.

These flags give you weak signals about whether a URL is likely on-target.

---

## 7. Suggested next-step tasks for filtering (for Claude)

You can treat this section as **instructions / brainstorming** for the next model.

Given:
- `exa_results.json` (full structured data), and/or
- `exa_found.csv` (flat version),

the next step is to **select the best website and best email per professor**, and possibly:
- discard clearly wrong/low-signal URLs (e.g. generic LinkedIn, PDF-only, non-academic sites),
- prioritize official institutional or lab pages.

### 7.1 Website selection ideas

For each professor:

- Prefer URLs that:
  - Have domains in a **whitelist** of Harvard-related hosts:
    - `*.harvard.edu`, `*.hsph.harvard.edu`, `*.hms.harvard.edu`, `*.seas.harvard.edu`, `*.gse.harvard.edu`, `*.hks.harvard.edu`, `*.hbs.edu`, etc.
  - Contain the professor’s **last name** in the path.
  - Contain words like `faculty`, `people`, `profile`, `lab`, `group`, `team`.
- Down-rank or exclude:
  - LinkedIn, generic media coverage, PDF documents, random news, or other institutions (`uchicago.edu`, `arizona.edu`, etc.) unless Harvard URLs are missing.
- Use `gold_website` only as a **weak prior** (it may be wrong); if Exa finds a more Harvard-looking, name-matching URL, that may be better.

**Possible scoring features to compute per URL:**
- Domain category: `harvard_academic` / `harvard_other` / `non_harvard`.
- Path contains last name.
- Path contains `faculty`, `people`, `profile`, `lab`, or `group`.
- URL present as `gold_website`.

### 7.2 Email selection ideas

For each professor:

- Prefer emails where:
  - Domain is Harvard-related (e.g. `*.harvard.edu`, `hbs.edu`).
  - Local part resembles the name: includes last name, or patterns like `jdoe`, `doej`.
- Avoid or down-rank:
  - Non-institutional domains (`gmail.com`, `yahoo.com`, etc.), **unless** no Harvard email exists.
  - Generic local parts: `info`, `contact`, `support`, `webmaster`, `communications`, etc.

**Potential outputs for a cleaned dataset:**
- `canonical_website_url` – best guess for official/lab profile.
- `canonical_email` – best guess for direct academic email.
- `website_confidence`, `email_confidence` – numeric scores or qualitative labels (high/medium/low).

---

## 8. Files to upload / share with Claude

To let another AI actually compute these filters, you can provide:

1. **This summary file:**
   - `api_evaluation/exa/EXA_PIPELINE_SUMMARY_FOR_CLAUDE.md`

2. **The flat CSV of results:**
   - `api_evaluation/exa/results_exa_until_credits/exa_found.csv`

3. (Optional, for deeper analysis) **The full JSON of results:**
   - `api_evaluation/exa/results_exa_until_credits/exa_results.json`

With those three, the model will know:
- Exactly how data was generated,
- What each column/field means,
- And will have concrete URLs and emails to filter and rank.
