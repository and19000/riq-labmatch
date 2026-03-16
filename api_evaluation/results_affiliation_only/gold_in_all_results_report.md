# Gold standard: found anywhere in all_urls / all_emails?

Comparison of whether the **gold-standard** website or email appears **anywhere** in the full result set (all_urls, all_emails), not just in the top hit.

**Professors with gold website:** 78

**Professors with gold email:** 38

## Summary

| Metric | Exa | Tavily |
|--------|-----|--------|
| Gold website found in all_urls (of 78 with gold) | 34 (43.6%) | 30 (38.5%) |
| Gold email found in all_emails (of 38 with gold) | 28 (73.7%) | 28 (73.7%) |

## Interpretation

- **Gold website in all_urls:** The gold-standard URL (or a normalized match) appeared in at least one of the URLs returned by the API.
- **Gold email in all_emails:** The gold-standard email appeared in the list of emails extracted from the API results.
