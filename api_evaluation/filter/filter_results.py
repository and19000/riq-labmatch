"""
Post-search filtering and canonicalization with URL/email scoring and re-ranking.

Implements the Stage 0 filter specified in docs/cursor_prompt_final.md.
"""

import argparse
import csv
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

from .university_config import UniversityConfig


DISPLAY_FIELDS = [
    "name",
    "affiliation",
    "department",
    "canonical_website",
    "website_confidence",
    "canonical_email",
    "email_confidence",
    "phone",
    "status",
    "original_found_website",
    "original_found_email",
    "all_urls",
    "all_emails",
]


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else "http://" + url)
    return (parsed.netloc or "").lower()


def _normalize_text(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _parse_name(name: str) -> Tuple[str, str, str]:
    cleaned = re.sub(r"[.,]", " ", name or "")
    tokens = [t for t in cleaned.split() if t]
    suffixes = {"jr", "sr", "ii", "iii", "iv", "md", "phd"}
    filtered: List[str] = []
    for t in tokens:
        tl = t.lower()
        if len(tl) <= 1:
            continue
        if tl.strip(".").strip(",") in suffixes:
            continue
        filtered.append(t)
    if not filtered:
        return "", "", ""
    first = _normalize_text(filtered[0])
    last = _normalize_text(filtered[-1])
    first_initial = first[0] if first else ""
    return first, last, first_initial


def score_url(url: str, professor_name: str, config: UniversityConfig) -> int:
    """
    Score a URL for quality. Higher = better.
    Implements the scoring table from the spec.
    """
    if not url:
        return 0

    score = 0
    url_str = url.strip()
    url_lower = url_str.lower()
    domain = _extract_domain(url_lower)
    path = urlparse(url_lower if "://" in url_lower else "http://" + url_lower).path or ""

    # Domain-based scoring
    if any(d in domain for d in config.primary_trusted_domains):
        score += 100
    elif any(d in domain for d in config.secondary_trusted_domains):
        score += 80
    elif domain.endswith(".edu"):
        score += 40

    # Path patterns
    profile_patterns = [
        "/people/",
        "/person/",
        "/profile/",
        "/profiles/",
        "/faculty/",
        "/directory/",
        "/bios/",
        "/find-a-doctor",
        "/provider",
        "/team/",
        "/member-detail",
    ]
    if any(p in path.lower() for p in profile_patterns):
        score += 30

    # Name-based signals
    first, last, first_initial = _parse_name(professor_name)
    url_no_scheme = url_lower.replace("https://", "").replace("http://", "")
    if last and last in url_no_scheme:
        score += 20
    if first and first in url_no_scheme:
        score += 10

    # Rejected / negative patterns
    if any(bad in domain for bad in config.rejected_domains):
        score -= 50
    if path.lower().endswith(".pdf"):
        score -= 30
    if "/search" in path.lower() or "/results" in path.lower():
        score -= 20

    return score


def score_email(email: str, professor_name: str, config: UniversityConfig) -> int:
    """
    Score an email for quality. Higher = better.
    """
    if not email:
        return 0

    email = email.strip().lower()
    if "@" not in email:
        return 0
    local, domain = email.split("@", 1)
    score = 0

    # Domain trust
    if any(d in domain for d in config.primary_trusted_domains):
        score += 100
    elif any(d in domain for d in config.secondary_trusted_domains):
        score += 80
    elif domain.endswith(".edu"):
        score += 30

    # Name-based signals
    first, last, first_initial = _parse_name(professor_name)
    if last and last in local:
        score += 20
    if first_initial and local.startswith(first_initial):
        score += 10

    # Junk patterns
    junk_domains = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "protonmail.com",
        "scispace.com",
    }
    junk_substrings = (
        "admin",
        "support",
        "noreply",
        "no-reply",
        "donotreply",
        "helpdesk",
        "webmaster",
        "postmaster",
    )
    info_variants = ("-info", "_info", "info")

    # Strong junk penalty for bad domains or admin/info/support patterns anywhere in local
    local_lower = local.lower()
    has_admin_info_pattern = any(s in local_lower for s in junk_substrings) or any(
        v in local_lower for v in info_variants
    )
    if domain in junk_domains or has_admin_info_pattern:
        score -= 100

    # Likely wrong-person emails: no name signal in local AND admin/info/support pattern AND non-university domain
    name_token_present = False
    if last and last in local_lower:
        name_token_present = True
    elif first and first in local_lower:
        name_token_present = True

    if not name_token_present and has_admin_info_pattern and (not domain.endswith(".edu")) and not any(
        d in domain for d in config.all_trusted_domains
    ):
        score -= 100

    # Additional penalty for non-university domains lacking name signal
    if (first or last) and last and last not in local_lower and (not domain.endswith(".edu")) and not any(
        d in domain for d in config.all_trusted_domains
    ):
        score -= 50

    return score


def infer_department(
    professor: Dict,
    canonical_url: str,
    all_urls: List[str],
    config: UniversityConfig,
) -> str:
    """
    Department inference using:
      1. Existing department field
      2. URL-based mapping via config.url_to_department
    """
    # Strategy 1: already present
    dept = (professor.get("department") or "").strip()
    if dept:
        return dept

    # Strategy 2: URL-based
    urls_to_check = []
    if canonical_url:
        urls_to_check.append(canonical_url)
    urls_to_check.extend(all_urls)

    keys = sorted(config.url_to_department.keys(), key=len, reverse=True)
    for url in urls_to_check:
        if not url:
            continue
        for key in keys:
            if key in url:
                return config.url_to_department[key]

    return ""


def _parse_semicolon_list(s: Optional[str]) -> List[str]:
    if not s:
        return []
    parts = [p.strip() for p in s.split(";") if p.strip()]
    # Deduplicate while preserving order
    seen = set()
    result: List[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def filter_and_canonicalize(
    input_csv: str,
    config: UniversityConfig,
    exa_json: Optional[str] = None,
    output_csv: Optional[str] = None,
    report_path: Optional[str] = None,
) -> None:
    # Load input
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    enriched: List[Dict] = []
    status_counts: Counter = Counter()
    website_conf_counts: Counter = Counter()
    email_conf_counts: Counter = Counter()
    dept_counts: Counter = Counter()
    url_domain_counts: Counter = Counter()
    email_domain_counts: Counter = Counter()

    url_reranked_examples: List[Dict] = []
    url_reranked_count = 0
    junk_email_removed_count = 0

    for row in rows:
        name = row.get("name", "")
        original_found_website = (row.get("found_website") or "").strip()
        original_found_email = (row.get("found_email") or "").strip()

        all_urls = _parse_semicolon_list(row.get("all_urls"))
        all_emails = _parse_semicolon_list(row.get("all_emails"))

        # URL scoring
        url_scores: List[Tuple[str, int]] = []
        for url in all_urls:
            url_scores.append((url, score_url(url, name, config)))
        # Always include original_found_website even if missing from all_urls
        if original_found_website and original_found_website not in [u for u, _ in url_scores]:
            url_scores.append((original_found_website, score_url(original_found_website, name, config)))

        url_scores_sorted = sorted(url_scores, key=lambda x: x[1], reverse=True)
        canonical_website = ""
        website_score = 0
        if url_scores_sorted and url_scores_sorted[0][1] > 0:
            canonical_website, website_score = url_scores_sorted[0]

        # Email scoring
        email_scores: List[Tuple[str, int]] = []
        for em in all_emails:
            email_scores.append((em, score_email(em, name, config)))
        if original_found_email and original_found_email not in [e for e, _ in email_scores]:
            email_scores.append((original_found_email, score_email(original_found_email, name, config)))

        email_scores_sorted = sorted(email_scores, key=lambda x: x[1], reverse=True)
        canonical_email = ""
        email_score = 0
        if email_scores_sorted and email_scores_sorted[0][1] > 0:
            canonical_email, email_score = email_scores_sorted[0]

        # Confidence levels
        if website_score >= 100:
            website_conf = "high"
        elif website_score >= 40:
            website_conf = "medium"
        elif website_score > 0:
            website_conf = "low"
        else:
            website_conf = "none"

        if email_score >= 100:
            email_conf = "high"
        elif email_score >= 30:
            email_conf = "medium"
        elif email_score > 0:
            email_conf = "low"
        else:
            email_conf = "none"

        # Status
        if canonical_website and canonical_email:
            status = "complete"
        elif canonical_website or canonical_email:
            status = "partial"
        else:
            status = "needs_review"

        # Department inference (CSV + URL only)
        inferred_dept = infer_department(row, canonical_website, all_urls, config)

        # Phone: not implemented yet (requires exa_json/page text)
        phone = ""

        # Track stats
        status_counts[status] += 1
        website_conf_counts[website_conf] += 1
        email_conf_counts[email_conf] += 1
        if inferred_dept:
            dept_counts[inferred_dept] += 1
        if canonical_website:
            url_domain_counts[_extract_domain(canonical_website)] += 1
        if canonical_email and "@" in canonical_email:
            email_domain_counts[canonical_email.split("@", 1)[1].lower()] += 1

        # URL re-ranking improvements
        if canonical_website and original_found_website and canonical_website != original_found_website:
            url_reranked_count += 1
            if len(url_reranked_examples) < 5:
                example = {
                    "name": name,
                    "original_found_website": original_found_website,
                    "canonical_website": canonical_website,
                }
                url_reranked_examples.append(example)

        # Junk email removal
        if original_found_email and not canonical_email:
            junk_email_removed_count += 1

        enriched_row = {
            "name": name,
            "affiliation": row.get("affiliation", ""),
            "department": inferred_dept,
            "canonical_website": canonical_website,
            "website_confidence": website_conf,
            "canonical_email": canonical_email,
            "email_confidence": email_conf,
            "phone": phone,
            "status": status,
            "original_found_website": original_found_website,
            "original_found_email": original_found_email,
            "all_urls": row.get("all_urls", ""),
            "all_emails": row.get("all_emails", ""),
        }
        enriched.append(enriched_row)

    # Write output CSVs
    if not output_csv:
        raise ValueError("output_csv path is required")
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    def _write_csv(path: str, rows_to_write: List[Dict]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DISPLAY_FIELDS)
            writer.writeheader()
            for r in rows_to_write:
                writer.writerow(r)

    # Display database: exclude needs_review
    display_rows = [r for r in enriched if r["status"] != "needs_review"]
    _write_csv(output_csv, display_rows)

    base, ext = os.path.splitext(output_csv)
    full_path = f"{base}_full{ext}"
    needs_review_path = f"{base}_needs_review{ext}"

    _write_csv(full_path, enriched)
    _write_csv(needs_review_path, [r for r in enriched if r["status"] == "needs_review"])

    # Report
    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        total = len(enriched)

        def _pct(n: int) -> str:
            return f"{(n / total * 100):.1f}%" if total else "0.0%"

        dept_inferred = sum(1 for r in enriched if (r.get("department") or "").strip())
        email_present = sum(1 for r in enriched if (r.get("canonical_email") or "").strip())

        lines: List[str] = []
        lines.append(f"# {config.name} Filter Report")
        lines.append("")
        lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")
        lines.append(f"- Total rows: **{total}**")
        lines.append(f"- COMPLETE: **{status_counts['complete']}** ({_pct(status_counts['complete'])})")
        lines.append(f"- PARTIAL: **{status_counts['partial']}** ({_pct(status_counts['partial'])})")
        lines.append(f"- NEEDS_REVIEW: **{status_counts['needs_review']}** ({_pct(status_counts['needs_review'])})")
        lines.append(f"- Dept inferred: **{dept_inferred}** ({_pct(dept_inferred)})")
        lines.append(f"- Email present: **{email_present}** ({_pct(email_present)})")
        lines.append("")
        lines.append(f"- URLs re-ranked (canonical != original_found_website): **{url_reranked_count}**")
        lines.append(f"- Original emails dropped as junk/low-score: **{junk_email_removed_count}**")
        lines.append("")

        lines.append("## Top 15 canonical website domains")
        for domain, count in url_domain_counts.most_common(15):
            lines.append(f"- {domain}: {count}")
        lines.append("")

        lines.append("## Top 15 canonical email domains")
        for domain, count in email_domain_counts.most_common(15):
            lines.append(f"- {domain}: {count}")
        lines.append("")

        lines.append("## Department distribution (top 15)")
        for dept, count in dept_counts.most_common(15):
            lines.append(f"- {dept}: {count}")
        lines.append("")

        lines.append("## Website confidence distribution")
        for level in ("high", "medium", "low", "none"):
            lines.append(f"- {level}: {website_conf_counts[level]}")
        lines.append("")

        lines.append("## Email confidence distribution")
        for level in ("high", "medium", "low", "none"):
            lines.append(f"- {level}: {email_conf_counts[level]}")
        lines.append("")

        lines.append("## Example rows with URL re-ranking")
        if not url_reranked_examples:
            lines.append("_No re-ranking examples found._")
        else:
            for ex in url_reranked_examples:
                lines.append(
                    f"- **{ex['name']}**\n"
                    f"  - original_found_website: {ex['original_found_website']}\n"
                    f"  - canonical_website: {ex['canonical_website']}"
                )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # Console summary
    print(f"Filtered {len(enriched)} rows.")
    print(f"Output (display): {output_csv}")
    print(f"Output (full): {full_path}")
    print(f"Output (needs_review): {needs_review_path}")
    if report_path:
        print(f"Report: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and canonicalize Exa/Tavily search results")
    parser.add_argument("--input", required=True, help="Path to exa_found.csv or tavily_found.csv")
    parser.add_argument("--config", required=True, help="Path to university config JSON")
    parser.add_argument("--output", required=True, help="Path for output CSV (display database)")
    parser.add_argument("--exa-json", default=None, help="Optional path to exa_results.json for page text (unused for now)")
    parser.add_argument("--report", required=True, help="Path for markdown report")
    args = parser.parse_args()

    config = UniversityConfig.from_json(args.config)
    filter_and_canonicalize(args.input, config, args.exa_json, args.output, args.report)


