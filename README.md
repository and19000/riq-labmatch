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
  "faculty": [
    {
      "name": "Professor Name",
      "h_index": 50,
      "email": {
        "value": "email@harvard.edu",
        "source": "website",
        "confidence": "high"
      },
      "website": {
        "value": "https://...",
        "confidence": "high"
      },
      "research": {
        "topics": [...],
        "keywords": [...]
      }
    }
  ]
}
```

### CSV Output
Tabular format with columns: name, h_index, email, website, research_topics, etc.

## Checkpoints

The pipeline saves checkpoints after each phase:
- `checkpoints/{institution}_phase1_openalex.json`
- `checkpoints/{institution}_phase2a_directories.json`
- `checkpoints/{institution}_phase2b_websites.json`
- `checkpoints/{institution}_phase3a_orcid.json`
- `checkpoints/{institution}_phase3b_emails.json`

Resume from checkpoint:
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

## Troubleshooting

### Brave API Quota Exhausted
```bash
# Check quota at https://api.search.brave.com/app/dashboard
# Resume with:
python3 faculty_pipeline_v4_4.py --institution harvard --resume
```

### No Checkpoint Found
Start fresh:
```bash
python3 faculty_pipeline_v4_4.py --institution harvard --max-faculty 600 --clear-checkpoints
```

### Low Email Coverage
Email coverage is limited by:
- Institution policies (many don't list public emails)
- Website accessibility
- Contact form usage vs direct emails

Expected ranges:
- Harvard: 28-30%
- MIT: 30-35%
- Stanford: 25-30%

## Documentation

- `V4_4_STATUS_AND_NEXT_STEPS.md` - v4.4 status and improvements
- `V4_5_FINAL_REPORT.md` - v4.5 results and analysis
- `V4_5_1_FINAL_REPORT.md` - Restore script results

## Contributing

1. Create feature branch
2. Test with small faculty count first
3. Update documentation
4. Submit pull request

## License

Proprietary - RIQ LabMatch

---

**Last Updated:** January 21, 2026  
**Pipeline Version:** 4.5.1  
**Maintained by:** RIQ LabMatch Team
