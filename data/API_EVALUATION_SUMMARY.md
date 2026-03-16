# API Search Evaluation Results Summary

**Date:** March 2, 2026  
**Professors Tested:** 80 Harvard Faculty  
**Gold Standard Data:** 78 with website, 38 with email (partial gold standard)

---

## Executive Summary

| API | Website Found | Email Found | Website Exact Match | Email Exact Match | Combined Score | Cost |
|-----|---------------|-------------|---------------------|-------------------|----------------|------|
| **Exa** | 100% | 83.8% | 28.7% | 33.8% | 0.533 | $0.80 |
| **Tavily** | 100% | 98.8% | 7.5% | 22.5% | 0.421 | $1.60 |

**Key Finding:** Both APIs found websites for **100% of professors**. Exa significantly outperforms Tavily on accuracy metrics while costing half as much.

---

## Detailed Results

### Website Discovery

| Metric | Exa | Tavily | Winner |
|--------|-----|--------|--------|
| Found Any Website | 80/80 (100%) | 80/80 (100%) | Tie |
| Exact URL Match | 23/80 (28.7%) | 6/80 (7.5%) | **Exa (+21.2%)** |
| Domain Match | 32/80 (40.0%) | 10/80 (12.5%) | **Exa (+27.5%)** |
| Professor Name in URL | 61/80 (76.3%) | 52/80 (65.0%) | **Exa (+11.3%)** |
| Gold Website in All Results* | 34/78 (43.6%) | 30/78 (38.5%) | **Exa (+5.1%)** |

*Checks if gold standard URL appears anywhere in top 5 results, not just first result.

### Email Discovery

| Metric | Exa | Tavily | Winner |
|--------|-----|--------|--------|
| Found Any Email | 67/80 (83.8%) | 79/80 (98.8%) | **Tavily (+15%)** |
| Exact Email Match | 27/80 (33.8%) | 18/80 (22.5%) | **Exa (+11.3%)** |
| Domain Match | 31/80 (38.8%) | 23/80 (28.7%) | **Exa (+10.1%)** |
| Gold Email in All Results* | 28/38 (73.7%) | 28/38 (73.7%) | Tie |

*Of the 38 professors with gold standard emails, both APIs found the correct email somewhere in results 73.7% of the time.

### Cost Efficiency

| Metric | Exa | Tavily |
|--------|-----|--------|
| Queries Used | 160 | 160 |
| Total Cost | $0.80 | $1.60 |
| Cost per Professor | $0.01 | $0.02 |
| Cost per Exact Website Match | $0.035 | $0.267 |
| Cost per Exact Email Match | $0.030 | $0.089 |

**Exa is 2x cheaper and 3-4x more cost-effective per accurate result.**

---

## Quality Analysis

### Exa Strengths

1. **Higher Accuracy on First Result**
   - 28.7% exact website match vs Tavily's 7.5%
   - 40% domain match vs Tavily's 12.5%

2. **Better Academic Source Recognition**
   - Consistently finds official Harvard pages
   - Returns `seas.harvard.edu`, `hms.harvard.edu`, `hsph.harvard.edu` URLs
   - Example: For "Katia Bertoldi" → Found `seas.harvard.edu/person/katia-bertoldi` ✓

3. **More Relevant Results**
   - 76% of results contain professor name in URL
   - Fewer irrelevant LinkedIn/third-party results in top position

4. **Cost Effective**
   - Half the cost of Tavily ($0.80 vs $1.60)
   - Better results per dollar spent

### Exa Weaknesses

1. **Email Extraction Rate**
   - Only found emails for 83.8% vs Tavily's 98.8%
   - Some pages don't have emails on them

2. **Some LinkedIn Results**
   - Occasionally returns LinkedIn as top result
   - Example: "Josep M. Mercader" → LinkedIn instead of harvard.edu

### Tavily Strengths

1. **Higher Email Discovery Rate**
   - Found emails on 98.8% of professors
   - Better at extracting emails from page content

2. **Broader Search**
   - Returns more diverse sources
   - Good for finding alternative contact information

### Tavily Weaknesses

1. **Lower Accuracy**
   - Only 7.5% exact website match
   - 12.5% domain match
   - Often returns irrelevant first results

2. **Quality Issues**
   - Returns PDFs, news articles, third-party sites
   - Example: "Troyen A. Brennan" → citizen.org PDF (irrelevant)
   - Example: "Elizabeth Loder" → americanheadachesociety.org (not her profile)

3. **Higher Cost**
   - 2x more expensive than Exa
   - Lower accuracy per dollar

---

## Sample Comparisons

### Case 1: Perfect Match (Both APIs)
**Professor:** Michael E. Chernew (Harvard Medical School)

| | Exa | Tavily |
|---|-----|--------|
| Found Website | `hcp.hms.harvard.edu/people/michael-e-chernew` ✓ | `hcp.hms.harvard.edu/people/michael-e-chernew` ✓ |
| Found Email | `chernew@hcp.med.harvard.edu` ✓ | `chernew@hcp.med.harvard.edu` ✓ |

### Case 2: Exa Better
**Professor:** Kenneth Froot (Harvard University)

| | Exa | Tavily |
|---|-----|--------|
| Gold Website | `sites.harvard.edu/cafh/directory/kenneth-froot` | |
| Found Website | `hbs.edu/faculty/Pages/profile.aspx?facId=6456` (valid HBS page) | `ftalphaville.ft.com/...` (news article) |
| Found Email | `kfroot@hbs.edu` ✓ | Not found |

### Case 3: Tavily Better (Email Only)
**Professor:** Anne Marie Valente (Harvard University)

| | Exa | Tavily |
|---|-----|--------|
| Found Website | `blogs.colum.edu/...` (wrong person) | `americanheadachesociety.org/...` (award page) |
| Found Email | None | `ahshq@talley.com` (generic, but found something) |

### Case 4: Both Partially Correct
**Professor:** Fernando D. Camargo (Harvard Medical School)

| | Exa | Tavily |
|---|-----|--------|
| Gold Website | `dms.hms.harvard.edu/people/fernando-d-camargo` | |
| Found Website | `hscrb.harvard.edu/labs/camargo-lab/` (his lab, valid) | `camargolab.squarespace.com` (his lab, valid) |
| Gold in All URLs? | Yes (2nd result) | Yes (2nd result) |
| Found Email | `fernando.camargo@childrens.harvard.edu` ✓ | `fernando.camargo@childrens.harvard.edu` ✓ |

---

## URL Quality Analysis (Exa)

### Top Result Domain Distribution

| Domain Type | Count | % |
|-------------|-------|---|
| harvard.edu (official) | 52 | 65% |
| linkedin.com | 12 | 15% |
| Other .edu | 5 | 6% |
| Other (news, org, etc.) | 11 | 14% |

**65% of Exa's top results are official Harvard pages.**

### Harvard Subdomain Breakdown (Exa)

| Subdomain | Count |
|-----------|-------|
| seas.harvard.edu | 8 |
| hsph.harvard.edu | 7 |
| connects.catalyst.harvard.edu | 6 |
| hms.harvard.edu / dms.hms.harvard.edu | 5 |
| mcb.harvard.edu | 4 |
| physics.harvard.edu | 3 |
| hbs.edu | 3 |
| Other harvard.edu | 16 |

---

## Recommendations

### Primary Recommendation: Use Exa

**Reasons:**
1. **4x better website accuracy** (28.7% vs 7.5% exact match)
2. **3x better domain accuracy** (40% vs 12.5%)
3. **50% cheaper** ($0.80 vs $1.60 for 80 professors)
4. **Better academic source recognition**

### Hybrid Approach (Optional)

For maximum coverage:
1. **Use Exa as primary** for website discovery
2. **Use Tavily as fallback** for email extraction when Exa fails
3. **Manual verification** for top-priority professors

### Implementation Notes

1. **Exa returns full page content** - enables better email extraction
2. **Consider fetching top 3 URLs** instead of just first result
3. **Gold standard in all_urls** shows 43.6% (Exa) have correct URL in results, just not ranked first
4. **Post-processing can improve accuracy** by re-ranking results based on:
   - Domain match (harvard.edu > linkedin.com)
   - Name in URL
   - Profile page patterns (/person/, /people/, /profile/)

---

## Cost Projection for Scale

| Scale | Professors | Exa Cost | Tavily Cost |
|-------|------------|----------|-------------|
| Current Test | 80 | $0.80 | $1.60 |
| Harvard Full | 2,000 | $20 | $40 |
| Top 10 Universities | 20,000 | $200 | $400 |
| All US R1 | 100,000 | $1,000 | $2,000 |

**Exa provides better results at half the cost at any scale.**

---

## Next Steps

1. **Manual verification** of Exa results for the 80 professors
2. **Re-rank algorithm** - prioritize harvard.edu domains over LinkedIn
3. **Email extraction improvement** - fetch top 3 URLs and extract emails from all
4. **Expand gold standard** - add more verified emails for better accuracy measurement
5. **Production pipeline** - integrate Exa as primary search API

---

## Appendix: API Configuration Used

### Exa
```python
exa.search(
    query=f"{name} {affiliation} professor profile",
    type="auto",
    num_results=5,
    contents={"text": {"max_characters": 5000}}
)
```

### Tavily
```python
tavily.search(
    query=f"{name} {affiliation} professor contact email",
    search_depth="advanced",
    max_results=5,
    include_raw_content=True
)
```

---

## Conclusion

**Exa is the clear winner** for faculty website and email discovery:
- 4x more accurate on website matching
- 50% cheaper
- Better at finding official academic pages
- Provides full page content for email extraction

The 100% website discovery rate from both APIs is promising - the challenge is **accuracy**, not coverage. Exa's results are significantly more likely to be the correct official faculty page.

**Recommendation:** Adopt Exa as the primary search API for the faculty pipeline.
