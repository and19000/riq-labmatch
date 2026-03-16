"""
Email extraction from search results and web pages.
"""
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, List
from urllib.parse import urlparse

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

GENERIC_EMAILS = {
    "info", "contact", "admin", "office", "support", "help", "webmaster",
    "department", "dept", "program", "general", "inquiry", "team", "staff",
    "hr", "communications", "admissions", "registrar"
}


def extract_email_from_text(text: str, professor_name: str = "") -> Optional[str]:
    if not text:
        return None

    emails = EMAIL_PATTERN.findall(text.lower())

    if not emails:
        return None

    valid_emails = []
    for email in emails:
        local = email.split("@")[0]
        if local not in GENERIC_EMAILS and not any(local.startswith(g) for g in GENERIC_EMAILS):
            valid_emails.append(email)

    if not valid_emails:
        return None

    if professor_name:
        name_parts = professor_name.lower().split()
        last_name = name_parts[-1] if name_parts else ""
        first_name = name_parts[0] if name_parts else ""

        scored = []
        for email in valid_emails:
            local = email.split("@")[0]
            score = 0

            if last_name and last_name in local:
                score += 10
            if first_name and first_name in local:
                score += 5
            if last_name and first_name:
                if f"{first_name[0]}{last_name}" in local:
                    score += 8
                if f"{last_name}{first_name[0]}" in local:
                    score += 8
            if ".edu" in email or email.endswith(".edu"):
                score += 3

            scored.append((score, email))

        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    edu_emails = [e for e in valid_emails if ".edu" in e]
    return edu_emails[0] if edu_emails else valid_emails[0]


def extract_email_from_url(url: str, professor_name: str = "") -> Optional[str]:
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"
        })

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a", href=True):
            if a["href"].startswith("mailto:"):
                email = a["href"][7:].split("?")[0].lower()
                if email and "@" in email:
                    local = email.split("@")[0]
                    if local not in GENERIC_EMAILS:
                        return email

        page_text = soup.get_text()
        return extract_email_from_text(page_text, professor_name)

    except Exception:
        return None


def extract_emails_from_results(results: List, professor_name: str = "") -> List[str]:
    found_emails = []

    for result in results:
        if result.content:
            email = extract_email_from_text(result.content, professor_name)
            if email:
                found_emails.append(email)
                continue

        if result.snippet:
            email = extract_email_from_text(result.snippet, professor_name)
            if email:
                found_emails.append(email)
                continue

        if len(found_emails) < 3 and result.url:
            email = extract_email_from_url(result.url, professor_name)
            if email:
                found_emails.append(email)

    seen = set()
    unique = []
    for email in found_emails:
        if email not in seen:
            seen.add(email)
            unique.append(email)

    return unique
