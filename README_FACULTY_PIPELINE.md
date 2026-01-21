# RIQ LabMatch - Faculty Pipeline

Faculty data extraction pipeline for matching students with research opportunities.

## Overview

This pipeline extracts faculty information from top-tier institutions, including:
- Research profiles (topics, concepts, keywords)
- Contact information (emails, websites)
- Academic metrics (h-index, publications)

**Current Results (Harvard):**
- 600 faculty extracted
- 539 websites (89.8%)
- 174 emails (29.0%)

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

```bash
export OPENALEX_CONTACT_EMAIL="riqlabmatch@gmail.com"
export BRAVE_API_KEY="your-brave-api-key"  # Optional, for website discovery
```

### Run Pipeline

```bash
# Basic run (Harvard, 600 faculty)
python3 faculty_pipeline_v4_4.py --institution harvard --max-faculty 600

# With resume capability
python3 faculty_pipeline_v4_4.py --institution harvard --resume

# Enhanced version (v4.5)
python3 faculty_pipeline_v4_5.py --institution harvard --max-faculty 600
```

## Pipeline Versions

### v4.4 (Recommended - Stable)
- **File:** `faculty_pipeline_v4_4.py`
- **Status:** ✅ Production-ready
- **Features:**
  - Checkpoint resume system
  - Phase-by-phase saving
  - Website discovery (Brave API)
  - Email extraction (ORCID, websites, directories)
- **Results:** 89.8% websites, 28.7% emails

### v4.5 (Enhanced)
- **File:** `faculty_pipeline_v4_5.py`
- **Status:** ✅ Tested
- **Improvements:**
  - Fuzzy name matching
  - Enhanced contact page discovery
  - Skip known bad sites
  - Fallback email search
- **Results:** Similar to v4.4 with minor improvements

### v4.5.1 (Restore)
- **File:** `faculty_pipeline_v4_5_1_restore.py`
- **Status:** ✅ Tested
- **Purpose:** Restore and enhance existing v4.4 data
- **Usage:**
  ```bash
  python3 faculty_pipeline_v4_5_1_restore.py \
      --input output/harvard_university_20260120_162804.json \
      --output output \
      --skip-new-websites
  ```

## Pipeline Phases

1. **Phase 1: OpenAlex Extraction**
   - Extract faculty from OpenAlex API
   - Get research profiles, h-index, publications

2. **Phase 2A: Directory Scraping**
   - Scrape department directories
   - Extract emails and websites

3. **Phase 2B: Website Discovery**
   - Use Brave Search API to find personal/lab pages
   - Score and rank results

4. **Phase 3A: ORCID Email Lookup**
   - Query ORCID API for public emails

5. **Phase 3B: Website Email Extraction**
   - Extract emails from discovered websites
   - Enhanced contact page discovery

6. **Phase 3C: Fallback Search** (v4.5+)
   - Additional email-specific searches

## Supported Institutions

- **Harvard University** (`harvard`)
- **MIT** (`mit`)
- **Stanford** (`stanford`)

To add more institutions, edit the `INSTITUTIONS` dict in the pipeline file.

## Output Format

### JSON Output
```json
{
  "metadata": {
    "institution": "Harvard University",
    "version": "4.4.0",
    "total_faculty": 600,
    "websites_found": 539,
    "emails_found": 174,
    "email_coverage": 0.29
  },
  "faculty": [...]
}
```

## Checkpoints

The pipeline saves checkpoints after each phase. Resume from checkpoint:
```bash
python3 faculty_pipeline_v4_4.py --institution harvard --resume
```

## Performance

| Metric | Value |
|--------|-------|
| **600 faculty** | ~50-60 minutes |
| **Brave queries** | ~1,500-2,000 |
| **Cost** | ~$5-6 (Brave API) |
| **Email coverage** | 28-30% (institution-dependent) |

## Documentation

- `V4_4_STATUS_AND_NEXT_STEPS.md` - v4.4 status and improvements
- `V4_5_FINAL_REPORT.md` - v4.5 results and analysis
- `V4_5_1_FINAL_REPORT.md` - Restore script results

---

**For main app documentation, see:** `../README.md`
