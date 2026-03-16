# Exa Results: Next Steps Plan

## The insight: measurement vs. results

Current metrics (e.g. **28.7% website exact match**) likely **undersell** Exa’s real performance because:

- **Gold = one URL per professor.** In reality, a professor can have several valid pages: department, lab, Harvard Catalyst, SEAS directory, etc.
- **Exa returning a different valid page is scored as a miss.** Example: Camargo — gold was `dms.hms.harvard.edu`, Exa returned `hscrb.harvard.edu` (his lab). Both are correct; we currently count it as wrong.
- Same idea for **email**: multiple valid addresses (`@fas.harvard.edu`, `@hms.harvard.edu`, etc.) can exist; we only compare to a single “gold” email.

So “low accuracy” may be mostly a **measurement problem**, not a **results problem**. Before building filters or re-ranking, we should get a **realistic** accuracy number and only invest in filtering if there’s still a clear gap.

---

## Recommended next moves (in order)

### 1. Redefine “correct” (acceptability criteria)

**Goal:** Treat any **acceptable** URL/email as correct, not only the one in our gold column.

**Acceptability (website):**

- Same person (professor name clearly associated with the page).
- Official / on-topic: department listing, lab page, Harvard Catalyst profile, school directory, scholar page, etc.
- Harvard-affiliated domain (e.g. `*.harvard.edu`, `hbs.edu`) strongly preferred; personal/lab sites on Harvard subdomains count.

**Acceptability (email):**

- Same person (name in local part or clearly their contact).
- Institutional (e.g. `@harvard.edu`, `@hms.harvard.edu`, `@fas.harvard.edu`) preferred; personal only if no institutional option.

**Concrete step:** Document this in a short “Acceptability criteria” section (e.g. in this doc or in `EXA_PIPELINE_SUMMARY_FOR_CLAUDE.md`) so manual reviewers and any future automated checks use the same definition.

---

### 2. Quick manual review to get true accuracy

**Goal:** Replace single-URL exact match with a **human-labeled** view of Exa’s top result (and optionally top N URLs) so we get a realistic accuracy number.

**Options:**

- **A) Evaluation spreadsheet (recommended first step)**  
  - One row per professor.  
  - Columns: `name`, `affiliation`, `gold_website`, `gold_email`, Exa’s `found_website`, `found_email`, and **label columns** e.g.  
    - **Website:** `Correct` / `Partially correct` / `Wrong` (plus optional short note).  
    - **Email:** same or “N/A” if none.  
  - Export from `data/exa_harvard/exa_harvard_found.csv` (or the 80-professor CSV) and add the label columns.  
  - Review in Excel/Sheets; compute % Correct and % Partially correct.  
  - If we do this on the **80-professor** set first, we get a stable “Exa true accuracy” estimate quickly.

- **B) Lightweight labeling tool (if we want to scale)**  
  - Simple script or Streamlit/Flask page that:  
    - Shows one professor at a time: name, affiliation, Exa’s top URL (and link), top email, and optionally `all_urls`/`all_emails`.  
    - Buttons: e.g. “Website: Correct / Partial / Wrong”, “Email: Correct / Partial / Wrong / N/A”.  
    - Saves labels to a CSV (e.g. `exa_review_labels.csv`) and supports resume.  
  - Build only if we’re going to label hundreds of rows and a spreadsheet is too slow.

**Deliverable:**  
- A **labeled dataset** (80 or a sample of the full 1477).  
- **Revised accuracy stats:** e.g. “% Correct”, “% Correct or Partial”, “% Wrong” for website and email.  
- A one-paragraph summary: “Exa’s true accuracy is approximately X% (website) and Y% (email) under acceptability criteria.”

---

### 3. Decide whether to build filtering / re-ranking

**Only do this if** the manual review shows:

- Meaningful share of **Wrong** (wrong person or irrelevant page), or  
- Many **Partially correct** where we’d want to **prefer** one type of URL (e.g. lab over news).

**If we do build it:**

- Use the acceptability criteria as the **target**: any URL/email that would be labeled “Correct” or “Partially correct” is acceptable; the job of the filter is to **choose the best among** `all_urls` and `all_emails`, or to **exclude** clearly wrong ones.
- Possible inputs for a scoring rubric (from the summary doc):  
  - Harvard domain whitelist, name-in-URL, path keywords (faculty, people, profile, lab), and optionally `gold_website`/`gold_email` as weak priors.
- Output: e.g. `canonical_website_url`, `canonical_email`, optional confidence.

**If manual accuracy is already high (e.g. >60–70% correct):**  
- Focus on **validation and spot-checks** rather than a big re-ranking system.  
- Optionally add a “reviewed” or “accepted” flag for downstream use.

---

### 4. Optional: extend to full 1477 with sampling

- If the **80-professor** review looks good, we can:  
  - Label a **random sample** of the full 1477 (e.g. 100–200) using the same acceptability criteria, and  
  - Report accuracy and error patterns for the full run.  
- That gives a statistically more stable estimate without labeling every row.

---

## Summary table

| Step | Action | Outcome |
|------|--------|--------|
| 1 | Define acceptability criteria (website + email) | Single definition of “correct” for all later steps |
| 2a | Build evaluation spreadsheet from Exa results (e.g. 80 or sample) | Ready for manual labeling |
| 2b | Manual pass: label each top result Correct / Partial / Wrong | **True accuracy** for Exa (website + email) |
| 3 | Decide: if accuracy is high → validate only; if not → design filtering/re-ranking | Clear next step (validate vs. build rubric) |
| 4 | (Optional) Sample and label from full 1477 | More robust accuracy estimate for full Harvard run |

---

## Where things live

- **Exa full run CSV (1477):** `data/exa_harvard/exa_harvard_found.csv`  
- **80-professor test CSV:** `api_evaluation/results_affiliation_only/exa_found_80.csv`  
- **Pipeline and schema description:** `api_evaluation/EXA_PIPELINE_SUMMARY_FOR_CLAUDE.md`  
- **This plan:** `docs/EXA_NEXT_STEPS_PLAN.md`

If you want to implement the evaluation spreadsheet next, we can define the exact columns and a small script to generate the sheet from one of the CSVs so it’s ready for labeling.
