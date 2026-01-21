#!/bin/bash
# Analysis and Improvement Report Generator

cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline

OUTPUT_DIR="output"
LOG_FILE="harvard_600_v43.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="IMPROVEMENT_REPORT_${TIMESTAMP}.md"

echo "Generating improvement report..."

# Find most recent output files
LATEST_JSON=$(ls -t ${OUTPUT_DIR}/harvard_university_*.json 2>/dev/null | head -1)
LATEST_CSV=$(ls -t ${OUTPUT_DIR}/harvard_university_*.csv 2>/dev/null | head -1)

if [ -z "$LATEST_JSON" ]; then
    echo "ERROR: No output files found. Pipeline may not have completed."
    exit 1
fi

echo "Analyzing: $LATEST_JSON"

# Generate report using Python
python3 << 'PYTHON_SCRIPT'
import json
import csv
from collections import Counter
from pathlib import Path
import sys

# Find latest files
output_dir = Path("output")
json_files = sorted(output_dir.glob("harvard_university_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
csv_files = sorted(output_dir.glob("harvard_university_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)

if not json_files:
    print("ERROR: No JSON files found")
    sys.exit(1)

latest_json = json_files[0]
latest_csv = csv_files[0] if csv_files else None

# Load data
with open(latest_json, 'r') as f:
    data = json.load(f)

metadata = data.get("metadata", {})
faculty_list = data.get("faculty", [])

total = metadata.get("total_faculty", len(faculty_list))
websites_found = metadata.get("websites_found", 0)
emails_found = metadata.get("emails_found", 0)
email_sources = metadata.get("email_sources", {})
website_coverage = metadata.get("website_coverage", 0) * 100
email_coverage = metadata.get("email_coverage", 0) * 100

# Detailed analysis
faculty_with_website = sum(1 for f in faculty_list if f.get("website", {}).get("value"))
faculty_with_email = sum(1 for f in faculty_list if f.get("email", {}).get("value"))

# Email source breakdown
email_source_counts = Counter()
email_confidence_counts = Counter()
for f in faculty_list:
    email = f.get("email", {})
    if email.get("value"):
        email_source_counts[email.get("source", "unknown")] += 1
        email_confidence_counts[email.get("confidence", "unknown")] += 1

# Website type breakdown
website_type_counts = Counter()
website_source_counts = Counter()
for f in faculty_list:
    website = f.get("website", {})
    if website.get("value"):
        website_type_counts[website.get("page_type", "unknown")] += 1
        website_source_counts[website.get("source", "unknown")] += 1

# Email extraction methods
email_methods = Counter()
for f in faculty_list:
    email = f.get("email", {})
    if email.get("value"):
        email_methods[email.get("extraction_method", "unknown")] += 1

# Issues analysis
issues = []
no_email_high_h = [f for f in faculty_list if not f.get("email", {}).get("value") and f.get("h_index", 0) >= 40]
if no_email_high_h:
    issues.append(f"**{len(no_email_high_h)} high-value faculty (h≥40) without emails**")

no_website_high_h = [f for f in faculty_list if not f.get("website", {}).get("value") and f.get("h_index", 0) >= 40]
if no_website_high_h:
    issues.append(f"**{len(no_website_high_h)} high-value faculty (h≥40) without websites**")

low_confidence_emails = sum(1 for f in faculty_list if f.get("email", {}).get("confidence") == "low")
if low_confidence_emails > 0:
    issues.append(f"**{low_confidence_emails} emails with LOW confidence**")

generic_emails = 0
for f in faculty_list:
    email = f.get("email", {}).get("value", "").lower()
    if email and any(pattern in email for pattern in ["info@", "contact@", "admin@", "department@"]):
        generic_emails += 1
if generic_emails > 0:
    issues.append(f"**{generic_emails} potentially generic emails detected**")

# Generate report
report = f"""# Faculty Pipeline v4.3 - Improvement Report
**Generated:** {metadata.get('date', 'Unknown')}  
**Institution:** {metadata.get('institution', 'Harvard University')}  
**Total Faculty:** {total}

---

## Executive Summary

### Results vs Expectations

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| **Websites** | 510-570 (85-95%) | {websites_found} ({website_coverage:.1f}%) | {'✅' if website_coverage >= 85 else '⚠️' if website_coverage >= 70 else '❌'} |
| **Emails** | 270-330 (45-55%) | {emails_found} ({email_coverage:.1f}%) | {'✅' if email_coverage >= 45 else '⚠️' if email_coverage >= 30 else '❌'} |
| **Brave Queries** | ~1,500 | {metadata.get('brave_queries_used', 0)} | ✅ |
| **Cost** | ~$4.50 | ~${metadata.get('brave_queries_used', 0) / 1000 * 3:.2f} | ✅ |
| **Duration** | 4-6 hours | {metadata.get('duration_minutes', 0) / 60:.1f} hours | {'✅' if metadata.get('duration_minutes', 0) < 420 else '⚠️'} |

---

## Detailed Analysis

### Website Discovery

- **Coverage:** {website_coverage:.1f}% ({websites_found}/{total})
- **Sources:**
  - Directory cache: {website_source_counts.get('directory', 0)}
  - Brave Search: {website_source_counts.get('search', 0)}

- **Website Types:**
{chr(10).join(f"  - {k}: {v} ({v/websites_found*100:.1f}%)" for k, v in sorted(website_type_counts.items(), key=lambda x: x[1], reverse=True) if websites_found > 0)}

### Email Extraction

- **Coverage:** {email_coverage:.1f}% ({emails_found}/{total})
- **Sources:**
{chr(10).join(f"  - {k}: {v} ({v/emails_found*100:.1f}%)" for k, v in sorted(email_source_counts.items(), key=lambda x: x[1], reverse=True) if emails_found > 0)}

- **Confidence Levels:**
{chr(10).join(f"  - {k.upper()}: {v} ({v/emails_found*100:.1f}%)" for k, v in sorted(email_confidence_counts.items(), key=lambda x: x[1], reverse=True) if emails_found > 0)}

- **Extraction Methods:**
{chr(10).join(f"  - {k}: {v}" for k, v in sorted(email_methods.items(), key=lambda x: x[1], reverse=True))}

---

## Issues Identified

{chr(10).join(f"- {issue}" for issue in issues) if issues else "- No major issues identified ✅"}

---

## Suggested Improvements

### 1. Email Extraction Improvements

#### A. Enhanced Contact Page Discovery
**Problem:** Some faculty have emails only on contact pages that aren't being discovered.

**Solution:**
- Expand `CONTACT_LINK_PATTERNS` to include more variations:
  - `/staff-directory/`, `/people/`, `/faculty-directory/`
  - Query parameter patterns: `?page=contact`, `?view=contact`
- Add text-based detection for contact sections on main pages
- Follow breadcrumb links that mention "contact" or "email"

**Expected Impact:** +5-10% email coverage

#### B. Improve Name Matching Algorithm
**Problem:** Some emails are rejected because name matching is too strict.

**Solution:**
- Allow partial name matches (e.g., "smith" matches "smith-jones")
- Handle hyphenated names better
- Consider alternative name formats (e.g., "Dr. John Smith" vs "John A. Smith")
- Lower name match threshold for mailto links (they're higher confidence)

**Expected Impact:** +3-7% email coverage

#### C. Better Generic Email Detection
**Problem:** Some legitimate personal emails might be getting filtered.

**Solution:**
- Whitelist patterns that match faculty name even if they look generic
- Check context around email (e.g., "Contact me at" vs "Department email")
- Verify email is in a personal section, not department section

**Expected Impact:** +2-5% email coverage, reduce false negatives

#### D. ORCID Enhancement
**Problem:** Only {email_source_counts.get('orcid', 0)} emails found from ORCID (expected ~10-15%).

**Solution:**
- Some ORCID profiles may have emails in biography/text, not just email field
- Parse ORCID profile page HTML for emails
- Check ORCID works list for author email addresses

**Expected Impact:** +3-5% email coverage

#### E. Directory Matching Enhancement
**Problem:** Directory scraping found 256 emails but only matched {email_source_counts.get('directory', 0)} to faculty.

**Solution:**
- Improve name normalization (handle more edge cases)
- Fuzzy matching for slight variations
- Cross-reference with ORCID IDs when available
- Better handling of titles and suffixes (Jr., Sr., III, etc.)

**Expected Impact:** +5-10% email coverage

### 2. Website Discovery Improvements

#### A. Better Aggregator Detection
**Problem:** Some aggregator sites may still be getting through.

**Solution:**
- Check page structure (aggregators have many author cards/listings)
- Analyze page title patterns (personal pages vs directory pages)
- Check if page has exactly one faculty member mentioned
- Verify page has personal content (CV, bio, publications list)

**Expected Impact:** Higher quality websites, reduce false positives

#### B. Enhanced Personal Page Detection
**Problem:** Some personal pages might be scored too low.

**Solution:**
- Boost score for pages with faculty name in URL path
- Increase score for pages with personal keywords (CV, bio, research)
- Detect personal domain patterns (e.g., `~username`, `people.username`)
- Check for author bio sections

**Expected Impact:** +3-5% website coverage

#### C. Better Scoring for Department Pages
**Problem:** Department listing pages might score too high.

**Solution:**
- Penalize pages with multiple faculty members mentioned
- Check for pagination or "show more" buttons
- Verify page focuses on single person
- Lower score for directory-style layouts

**Expected Impact:** Better quality, fewer false positives

### 3. Technical Improvements

#### A. Error Recovery
**Problem:** Pipeline might stop on network errors or API failures.

**Solution:**
- Add retry logic with exponential backoff for all API calls
- Implement resume from checkpoint functionality
- Graceful degradation (continue with other sources if one fails)
- Better error logging with context

**Expected Impact:** Improved reliability, fewer manual restarts

#### B. Rate Limiting
**Problem:** May hit rate limits or get blocked.

**Solution:**
- Implement adaptive rate limiting based on API responses
- Add jitter to delays to avoid synchronized requests
- Monitor API response codes and adjust automatically
- Implement circuit breaker pattern

**Expected Impact:** Fewer API failures, more reliable runs

#### C. Monitoring and Debugging
**Problem:** Hard to debug issues mid-run.

**Solution:**
- Add detailed progress metrics (percentage complete, ETA)
- Real-time dashboard for monitoring
- Alert system for failures or anomalies
- Debug mode with verbose logging per faculty

**Expected Impact:** Faster issue detection and resolution

---

## Priority Recommendations

### High Priority (Implement First)

1. **Enhanced Contact Page Discovery** - Easiest win, +5-10% emails
2. **Directory Matching Enhancement** - Already have data, just need better matching
3. **Name Matching Improvements** - Low risk, high impact

### Medium Priority

4. **ORCID Enhancement** - Could find more verified emails
5. **Better Aggregator Detection** - Improve quality
6. **Error Recovery** - Improve reliability

### Low Priority (Nice to Have)

7. **Enhanced Personal Page Detection** - Marginal gains
8. **Monitoring Dashboard** - Operational improvement
9. **Rate Limiting Improvements** - Edge case handling

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
- Expand contact link patterns
- Improve name matching algorithm
- Add fuzzy matching for directory emails

### Phase 2: Email Quality (2-3 hours)
- Enhance ORCID parsing
- Better generic email detection
- Improved directory name matching

### Phase 3: Reliability (3-4 hours)
- Error recovery and retries
- Checkpoint resume functionality
- Better logging and monitoring

### Phase 4: Quality Improvements (4-5 hours)
- Better aggregator detection
- Enhanced scoring algorithms
- Personal page pattern detection

---

## Expected Outcomes After Improvements

| Metric | Current | After Improvements | Improvement |
|--------|---------|-------------------|-------------|
| **Email Coverage** | {email_coverage:.1f}% | 55-65% | +{55-email_coverage:.1f}-{65-email_coverage:.1f}% |
| **Website Coverage** | {website_coverage:.1f}% | 90-95% | +{90-website_coverage:.1f}-{95-website_coverage:.1f}% |
| **High Confidence Emails** | {email_confidence_counts.get('high', 0)} | +10-20% | Quality improvement |

---

## Files Generated

- **Output JSON:** `{Path(latest_json).name}`
- **Output CSV:** `{Path(latest_csv).name}` if latest_csv else "N/A"
- **Log File:** `{LOG_FILE}`
- **Checkpoints:** `checkpoints/` directory

---

**Report Generated:** {__import__('datetime').datetime.now().isoformat()}  
**Pipeline Version:** {metadata.get('version', '4.3.0')}
"""

# Write report
with open(f"IMPROVEMENT_REPORT_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md", 'w') as f:
    f.write(report)

print(f"Report generated: IMPROVEMENT_REPORT_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

PYTHON_SCRIPT

echo "Report generation complete!"
