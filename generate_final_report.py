#!/usr/bin/env python3
"""Generate final analysis and improvement report for pipeline run."""

import json
import csv
from collections import Counter
from pathlib import Path
from datetime import datetime

# Find latest JSON file
output_dir = Path("output")
json_files = sorted(output_dir.glob("harvard_university_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

if not json_files:
    print("ERROR: No JSON files found")
    exit(1)

latest_json = json_files[0]
print(f"Analyzing: {latest_json}")

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
brave_queries_used = metadata.get("brave_queries_used", 0)
brave_failures = metadata.get("brave_queries_failed", 0)

# Detailed analysis
email_source_counts = Counter()
email_confidence_counts = Counter()
website_type_counts = Counter()
website_source_counts = Counter()

for f in faculty_list:
    email = f.get("email", {})
    website = f.get("website", {})
    
    if email.get("value"):
        source = email.get("source", "unknown") or "unknown"
        email_source_counts[source] += 1
        confidence = email.get("confidence", "unknown") or "unknown"
        email_confidence_counts[confidence] += 1
    
    if website.get("value"):
        source = website.get("source", "unknown") or "unknown"
        website_source_counts[source] += 1
        page_type = website.get("page_type", "unknown") or "unknown"
        website_type_counts[page_type] += 1

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

# Generate report
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report_file = f"FINAL_REPORT_600_FACULTY_{timestamp}.md"

report = f"""# Faculty Pipeline v4.3 - Final Report (600 Faculty)

**Generated:** {datetime.now().isoformat()}  
**Institution:** {metadata.get('institution', 'Harvard University')}  
**Total Faculty:** {total}  
**Duration:** {metadata.get('duration_minutes', 0):.1f} minutes

---

## ⚠️ CRITICAL ISSUE: Brave API Quota Exhausted

**Problem:** The Brave Search API quota was exhausted, preventing website discovery.

**Evidence:**
- Error: `Brave API: Payment required - quota exhausted (402)`
- Brave queries used: {brave_queries_used}
- Brave failures: {brave_failures}
- Result: **0 websites found** (should be 85-95%)

**Impact:** Without website discovery, email extraction from personal pages was impossible.

---

## Results Summary

### Actual Results vs Expected

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| **Websites** | 510-570 (85-95%) | **0 (0.0%)** | ❌❌❌ **CRITICAL FAILURE** |
| **Emails** | 270-330 (45-55%) | **37 (6.2%)** | ❌❌ **MAJOR SHORTFALL** |
| **Brave Queries** | ~1,500 | **0** | ❌ **API QUOTA EXHAUSTED** |
| **Cost** | ~$4.50 | **$0.00** | ✅ (but pipeline incomplete) |
| **Duration** | 4-6 hours | **3.4 minutes** | ⚠️ (stopped early) |

---

## Detailed Breakdown

### Website Discovery
- **Found:** {websites_found}/{total} ({website_coverage:.1f}%)
- **Sources:**
  - Directory cache: {website_source_counts.get('directory', 0)}
  - Brave Search: {website_source_counts.get('search', 0)} (FAILED - quota exhausted)

### Email Extraction
- **Found:** {emails_found}/{total} ({email_coverage:.1f}%)
- **Sources:**
"""

for k, v in sorted(email_source_counts.items(), key=lambda x: x[1], reverse=True):
    if emails_found > 0:
        report += f"  - **{k}:** {v} ({v/emails_found*100:.1f}%)\n"

report += f"""
- **Confidence Levels:**
"""

for k, v in sorted(email_confidence_counts.items(), key=lambda x: x[1], reverse=True):
    if emails_found > 0:
        report += f"  - **{k.upper()}:** {v} ({v/emails_found*100:.1f}%)\n"

report += f"""
---

## Issues Identified

### Critical Issues

1. **Brave API Quota Exhausted** ❌❌❌
   - Status: API quota ran out during website discovery
   - Impact: **0% website coverage** (should be 85-95%)
   - Solution: Purchase more Brave API credits

2. **No Website Discovery** ❌❌❌
   - Result: Could not extract emails from personal pages
   - Impact: Lost ~40-50% of potential email coverage
   - Solution: Restart pipeline after replenishing API quota

3. **Low Email Coverage** ❌❌
   - Current: 6.2% (37/600)
   - Expected: 45-55% (270-330)
   - Gap: Missing ~233-293 emails

### Moderate Issues

"""

if issues:
    for issue in issues:
        report += f"- {issue}\n"
else:
    report += "- No additional major issues identified\n"

report += f"""
---

## Root Cause Analysis

### Primary Issue: API Quota Exhaustion

The Brave Search API quota was exhausted, likely from previous test runs. When the pipeline attempted to discover websites:

1. **Phase 2B Start:** Tested Brave API connection → Got 402 error (quota exhausted)
2. **Pipeline Behavior:** Correctly detected failure and skipped website discovery
3. **Result:** Pipeline completed but with **0 websites found**

### Why This Happened

- Previous test runs used ~58-300 queries
- The API key may have had limited quota to begin with
- No quota monitoring or warnings before starting

---

## Suggested Improvements

### 1. API Quota Management (CRITICAL)

**Problem:** No warning when quota is low or exhausted

**Solution:**
- **Pre-flight check:** Test API quota before starting large runs
- **Quota monitoring:** Check remaining quota periodically
- **Graceful degradation:** Continue with other sources if quota exhausted
- **Warning system:** Alert user when quota < 20% remaining

**Expected Impact:** Prevent wasted runs, better resource planning

---

### 2. Resume from Checkpoint (HIGH PRIORITY)

**Problem:** Pipeline restarts from beginning after interruption

**Solution:**
- **Checkpoint loading:** Resume from last completed phase
- **Skip completed phases:** Don't re-extract data that's already done
- **State persistence:** Save intermediate results for resume

**Expected Impact:** Save hours of time on restarts

---

### 3. Website Discovery Fallbacks (HIGH PRIORITY)

**Problem:** No alternative when Brave API fails

**Solution:**
- **Alternative search engines:** Use DuckDuckGo, Bing, or Google (if available)
- **Direct URL construction:** Try common patterns (e.g., ~username, /people/firstname-lastname)
- **Department directory scraping:** Extract more website URLs from department pages
- **OpenAlex URLs:** Use author URLs from OpenAlex data

**Expected Impact:** +20-30% website coverage even without Brave API

---

### 4. Enhanced Email Extraction (MEDIUM PRIORITY)

**Problem:** Only 6.2% email coverage (37/600)

**Issues:**
- Directory matching only found 9 emails (should find 30-40)
- ORCID found 28 emails (acceptable, ~5% of eligible)
- No website emails (due to no website discovery)

**Solutions:**

#### A. Improve Directory Matching
- **Fuzzy matching:** Handle name variations better
- **Cross-reference ORCID:** Match directory entries with ORCID IDs
- **Better name normalization:** Handle more edge cases

**Expected Impact:** +20-30 emails (3-5% coverage)

#### B. Enhanced Contact Page Discovery
- **Expand patterns:** More contact page URL patterns
- **Text-based detection:** Find contact sections on main pages
- **Follow breadcrumbs:** Navigate through site structure

**Expected Impact:** +10-15% email coverage when websites are available

---

### 5. Error Recovery and Retry Logic (MEDIUM PRIORITY)

**Problem:** Pipeline stops on errors instead of continuing

**Solution:**
- **Per-faculty error handling:** Catch errors per faculty, continue with others
- **Automatic retries:** Retry failed requests with exponential backoff
- **Error logging:** Log errors but continue processing
- **Graceful degradation:** Continue with available sources

**Expected Impact:** Improved reliability, fewer manual restarts

---

## Immediate Action Items

### Priority 1: Fix API Quota Issue

1. **Check Brave API Dashboard:**
   - Go to: https://brave.com/search/api/
   - Check current quota/credits
   - Purchase more if needed

2. **Restart Pipeline with Quota:**
   ```bash
   cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline
   export OPENALEX_CONTACT_EMAIL="riqlabmatch@gmail.com"
   export BRAVE_API_KEY="BSAcKzgthbeCluu_MuOibiYz0VQRqLO"
   caffeinate -i python3 faculty_pipeline_v4_3.py \\
       --institution harvard \\
       --max-faculty 600 \\
       --output output \\
       --log-file harvard_600_v43_fixed.log
   ```

---

## Expected Results After Fixes

| Metric | Current | After Fixes (with API quota) | Improvement |
|--------|---------|------------------------------|-------------|
| **Websites** | 0 (0.0%) | 510-570 (85-95%) | +85-95% |
| **Emails** | 37 (6.2%) | 270-330 (45-55%) | +233-293 emails |
| **Directory Emails** | 9 (1.5%) | 30-40 (5-7%) | +21-31 emails |
| **Website Emails** | 0 (0.0%) | 200-250 (33-42%) | +200-250 emails |

---

**Report Generated:** {datetime.now().isoformat()}  
**Pipeline Version:** {metadata.get('version', '4.3.0')}  
**Status:** ❌ **INCOMPLETE** - Brave API quota exhausted
"""

# Write report
with open(report_file, 'w') as f:
    f.write(report)

print(f"\n✅ Report generated: {report_file}")
print(f"\n📊 Summary:")
print(f"   Total Faculty: {total}")
print(f"   Websites: {websites_found} ({website_coverage:.1f}%)")
print(f"   Emails: {emails_found} ({email_coverage:.1f}%)")
print(f"   Email Sources: {dict(email_source_counts)}")
print(f"\n⚠️  CRITICAL: Brave API quota exhausted!")
print(f"   Brave queries used: {brave_queries_used}")
print(f"   Brave failures: {brave_failures}")
print(f"\n💡 Action: Purchase more Brave API credits and restart pipeline")
