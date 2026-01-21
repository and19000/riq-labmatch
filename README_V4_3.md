# Faculty Pipeline v4.3 - Production Run

## Status

**Current Run:** 600 faculty members from Harvard University  
**Started:** January 19, 2025  
**Expected Duration:** 4-6 hours  
**Expected Cost:** ~$4.50 (Brave Search API)

---

## Quick Commands

### Check Pipeline Status
```bash
cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline
bash check_status.sh
```

### Monitor Progress
```bash
tail -f harvard_600_v43.log
# OR
tail -f harvard_600_v43_stdout.log
```

### Check Checkpoints
```bash
ls -lth checkpoints/ | head -10
```

### View Latest Checkpoint
```bash
cat checkpoints/checkpoint_phase2b_websites_*.json | jq '.metadata' | tail -1
```

### Generate Final Report (After Completion)
```bash
bash analyze_and_report.sh
```

---

## Pipeline Phases

1. **Phase 1: OpenAlex Extraction** ✅ COMPLETE
   - Extracted 600 faculty
   - 91.5% with ORCID IDs
   - Checkpoint saved

2. **Phase 2A: Directory Scraping** ✅ COMPLETE
   - Scraped 9 department directories
   - Found 256 emails, 204 websites
   - Matched 9 emails to faculty
   - Checkpoint saved

3. **Phase 2B: Website Discovery** 🔄 IN PROGRESS
   - 572 faculty needing search
   - Estimated ~1,644 Brave queries
   - This will take 3-4 hours

4. **Phase 3A: ORCID Email Lookup** ⏳ PENDING
   - Will query ORCID for public emails

5. **Phase 3B: Website Email Extraction** ⏳ PENDING
   - Will extract emails from discovered websites

---

## Monitoring

The pipeline is running with:
- `caffeinate -i` to prevent system sleep
- Automatic checkpoint saving at each phase
- Detailed logging to `harvard_600_v43.log`

If the pipeline stops unexpectedly:
1. Check logs for errors
2. Use checkpoint to resume from last phase
3. Run `monitor_pipeline.sh` for automatic recovery

---

## Expected Results

| Metric | Expected | Target |
|--------|----------|--------|
| Websites | 510-570 | 85-95% |
| Emails | 270-330 | 45-55% |
| Brave Queries | ~1,500 | - |
| Cost | ~$4.50 | - |
| Duration | 4-6 hours | - |

---

## Output Files

After completion:
- `output/harvard_university_YYYYMMDD_HHMMSS.json` - Full results
- `output/harvard_university_YYYYMMDD_HHMMSS.csv` - CSV export
- `IMPROVEMENT_REPORT_YYYYMMDD_HHMMSS.md` - Analysis report (after running analyze_and_report.sh)

---

## Troubleshooting

### Pipeline Stopped
```bash
# Check if completed
grep "PIPELINE COMPLETE" harvard_600_v43.log

# Check for errors
grep -i "error\|exception\|failed" harvard_600_v43.log | tail -20

# Restart if needed (will resume from checkpoint)
bash monitor_pipeline.sh
```

### API Issues
- Check Brave API quota in dashboard
- Verify API key is correct
- Check network connectivity

### Low Progress
- Check if process is still running: `ps aux | grep faculty_pipeline_v4_3`
- Review logs for rate limiting or errors
- Check checkpoint timestamps

---

**Last Updated:** January 19, 2025
