"""
Shared name validation for directory scrapers.
Reject entries that are clearly not professor names.
"""

# Reject if name STARTS with any of these (case-insensitive)
REJECT_STARTS = (
    "administration", "clinical", "faculty", "students", "technology",
    "principal", "research", "application", "deadlines", "program",
    "department", "office", "center", "institute", "about", "contact",
    "news", "events", "curriculum", "admission",
)

# Reject if name CONTAINS any of these (case-insensitive)
REJECT_CONTAINS = (
    "expand_more", "expand_less", "read more", "learn more", "view all",
    "load more", "show more", "see all",
)


def is_valid_scraped_name(name: str) -> bool:
    if not name or not name.strip():
        return False
    n = name.strip()
    lower = n.lower()
    # No space = single word, not a real name
    if " " not in n:
        return False
    if len(n) > 60:
        return False
    if any(lower.startswith(p) for p in REJECT_STARTS):
        return False
    if any(s in lower for s in REJECT_CONTAINS):
        return False
    return True
