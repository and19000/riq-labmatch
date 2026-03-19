import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Prefer capital-D Data/ (runtime standard); fall back to data/ if needed
for _candidate in ("Data/master_faculty_database.csv", "data/master_faculty_database.csv"):
    _p = _REPO_ROOT / _candidate
    if _p.exists():
        INPUT_CSV = _p
        break
else:
    INPUT_CSV = _REPO_ROOT / "Data" / "master_faculty_database.csv"

OUTPUT_JSON = _REPO_ROOT / "Data" / "v2" / "all_faculty.json"

LOCATION_BY_UNIVERSITY = {
    "Harvard University": "Cambridge, MA",
    "Massachusetts Institute of Technology": "Cambridge, MA",
    "Tufts University": "Medford, MA",
    "Boston University": "Boston, MA",
    "Northeastern University": "Boston, MA",
    "Stanford University": "Stanford, CA",
    "Yale University": "New Haven, CT",
    "Princeton University": "Princeton, NJ",
}

# Case-insensitive: name must not start with any of these (after strip)
_BAD_NAME_PREFIXES = (
    "department",
    "division",
    "school",
    "center",
    "institute",
    "program",
    "office",
    "faculty",
    "administration",
    "clinical",
    "students",
    "technology",
    "principal",
    "research",
    "application",
    "deadlines",
    "about",
    "contact",
    "news",
    "events",
    "curriculum",
    "admission",
    "staff",
    "committee",
    "board",
    "council",
    "library",
    "services",
    "resources",
    "affiliated",
    "emeritus",
    "visiting",
)

# Case-insensitive substring checks
_BAD_SUBSTRINGS = (
    "expand_more",
    "expand_less",
    "read more",
    "learn more",
    "view all",
    "load more",
    "show more",
    "see all",
    "click here",
    "http://",
    "https://",
    ".edu",
    ".com",
    ".org",
)

_KNOWN_JUNK_PHRASES = frozenset(
    {
        "principal faculty",
        "principal faculty by research interest",
        "administration & operations",
        "clinical & translational research core",
        "faculty & leadership",
        "students, fellows & scholars",
        "technology advancement",
        "liver diseases expand_more",
        "musculoskeletal diseases expand_more",
        "nervous system diseases expand_more",
        "skin diseases expand_more",
    }
)


def _reject_reason_for_csv_name(name: str) -> Optional[str]:
    """
    Return a human-readable rejection reason, or None if the name is acceptable.
    """
    if not name or not name.strip():
        return "empty name"
    name = name.strip()

    if " " not in name:
        return "single word (no space)"

    if len(name) > 60:
        return "longer than 60 characters"

    lower = name.lower()

    for prefix in _BAD_NAME_PREFIXES:
        if lower.startswith(prefix):
            return f'starts with "{prefix}"'

    if lower.startswith("the ") or lower.startswith("a ") or lower.startswith("an "):
        return 'starts with article "The "/"A "/"An "'

    if lower in _KNOWN_JUNK_PHRASES:
        return "known junk phrase"

    for sub in _BAD_SUBSTRINGS:
        if sub in lower:
            return f'contains junk substring "{sub}"'

    if any(c.isdigit() for c in name):
        return "contains digits"

    letters_only = [c for c in name if c.isalpha()]
    if letters_only and all(c.isupper() for c in letters_only):
        # Allow "M. F. SEMMELHACK" / "J. K. ROWLING" style (initials + all-caps surname)
        if re.match(r"^([A-Z]\.\s*)+[A-Z][A-Z'\-]*$", name.strip()):
            return None
        return "all uppercase (non-person heading)"

    return None


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "unknown"


def _to_confidence_upper(value: str) -> str:
    v = (value or "").strip().lower()
    if not v:
        return ""
    mapping = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW", "none": "NONE"}
    return mapping.get(v, v.upper())


def _make_unique_id(name: str, school: str, seen_ids: set[str]) -> str:
    base = f"{_slugify(name)}-{_slugify(school)}"
    candidate = base
    i = 2
    while candidate in seen_ids:
        candidate = f"{base}-{i}"
        i += 1
    seen_ids.add(candidate)
    return candidate


def _row_to_v2(row: dict, seen_ids: set[str]) -> dict:
    name = (row.get("name") or "").strip()
    school = (row.get("university") or "").strip()
    affiliation_text = (row.get("affiliation") or "").strip()
    department = (row.get("department") or "").strip()
    website = (row.get("canonical_website") or "").strip()
    email = (row.get("canonical_email") or "").strip()
    phone = (row.get("phone") or "").strip()
    status = (row.get("status") or "").strip().lower()
    website_conf = (row.get("website_confidence") or "").strip().lower()
    email_conf = (row.get("email_confidence") or "").strip().lower()

    location = LOCATION_BY_UNIVERSITY.get(school, "")
    unique_id = _make_unique_id(name=name, school=school, seen_ids=seen_ids)
    today = datetime.now().date().isoformat()

    email_conf_upper = _to_confidence_upper(email_conf)
    website_conf_upper = _to_confidence_upper(website_conf)

    return {
        "schema_version": "2.0",
        "id": unique_id,
        "name": name,
        "name_alternatives": [],
        "affiliation": {
            "school": school,
            "affiliation": affiliation_text,
            "department": department,
            "department_category": "default",
            "title": "",
            "location": location,
            "specific_location": location,
        },
        "contact": {
            "email": email,
            "email_confidence": email_conf_upper or None,
            "website": website,
            "website_confidence": website_conf_upper or None,
            "phone": phone,
            "google_scholar_id": "",
            "google_scholar_url": "",
        },
        "metrics": {
            "h_index": "",
            "h_index_source": "",
            "h_index_updated": "",
            "citations_total": None,
            "i10_index": None,
            "works_count": None,
        },
        "research": {
            "areas": "",
            "topics": [],
            "techniques": [],
        },
        "publications": {
            "recent_papers": [],
        },
        "funding": {
            "nsf_awards": [],
            "nsf_grants_count": 0,
            "co_investigators": [],
        },
        "data_quality": {
            "status": status,
            "website_confidence": website_conf,
            "email_confidence": email_conf,
            "confidence": website_conf_upper or email_conf_upper or "UNKNOWN",
            "confidence_reason": "",
            "last_updated": today,
            "sources": ["master_faculty_database.csv"],
        },
    }


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    records = []
    seen_ids: set[str] = set()
    by_school = Counter()
    rejected: list[tuple[str, str]] = []
    total_rows = 0

    with open(INPUT_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            raw_name = (row.get("name") or "").strip()
            reason = _reject_reason_for_csv_name(raw_name)
            if reason:
                rejected.append((raw_name, reason))
                print(f"REJECTED: {raw_name!r} — reason: {reason}")
                continue
            v2 = _row_to_v2(row, seen_ids=seen_ids)
            records.append(v2)
            by_school[v2["affiliation"]["school"]] += 1

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Total CSV rows read: {total_rows}")
    print(f"Total rejected: {len(rejected)}")
    print(f"Converted {len(records)} professors to v2 JSON format")
    print("Output: Data/v2/all_faculty.json")
    for school in sorted(by_school):
        print(f"  {school}: {by_school[school]}")


if __name__ == "__main__":
    main()
