"""
Simple deterministic tag matching for "My Matches" (no ML).
Options are derived from faculty records; scoring is weighted keyword overlap.
"""
import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# Static year list (not stored per professor)
STUDENT_YEAR_OPTIONS: List[str] = [
    "Freshman",
    "Sophomore",
    "Junior",
    "Senior",
    "Graduate",
]

# Involvement: student selects; faculty classified from title string
INVOLVEMENT_CHOICES: List[Tuple[str, str]] = [
    ("full_time", "Full-time lab / research commitment"),
    ("part_time", "Part-time / alongside coursework"),
    ("flexible", "Flexible / exploratory (visiting, rotating, etc.)"),
]

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "using",
        "based",
        "into",
        "through",
        "between",
        "over",
        "such",
        "also",
        "more",
        "than",
        "has",
        "are",
        "was",
        "were",
        "been",
    }
)


def _normalize_haystack(pi: Dict[str, Any]) -> str:
    parts = [
        str(pi.get("department") or ""),
        str(pi.get("research_areas") or ""),
        str(pi.get("lab_techniques") or ""),
        str(pi.get("title") or ""),
    ]
    topics = pi.get("research_topics") or []
    if isinstance(topics, list):
        parts.extend(str(t) for t in topics[:12])
    return " ".join(parts).lower()


def faculty_involvement_bucket(title: str) -> str:
    """Map faculty title to a coarse bucket comparable to student involvement choice."""
    t = (title or "").lower()
    if any(x in t for x in ("adjunct", "part-time", "part time")):
        return "part_time"
    if any(x in t for x in ("visiting", "emeritus", "lecturer", "instructor")):
        return "flexible"
    return "full_time"


def build_research_area_labels(
    faculty: Sequence[Dict[str, Any]],
    dept_field_key_fn: Callable[[str], str],
    category_display: Dict[str, str],
) -> List[str]:
    """Sorted human-readable research area labels that appear in the faculty dataset."""
    keys = set()
    for pi in faculty:
        keys.add(dept_field_key_fn((pi.get("department") or "")))
    labels = [category_display[k] for k in sorted(keys) if k in category_display]
    if not labels:
        return [category_display[k] for k in sorted(category_display.keys())]
    return labels


def build_work_type_phrases(faculty: Sequence[Dict[str, Any]], limit: int = 36) -> List[str]:
    """
    Frequent comma-separated technique / area phrases from faculty data.
    Deterministic: sort by (-count, lowercased phrase).
    """
    raw = Counter()
    for pi in faculty:
        lt = (pi.get("lab_techniques") or "").strip()
        ra = (pi.get("research_areas") or "").strip()
        if lt:
            for part in re.split(r"[,;]", lt):
                p = part.strip()
                if 4 <= len(p) <= 120:
                    raw[p] += 1
        if ra and len(raw) < limit * 2:
            for part in re.split(r"[,;]", ra):
                p = part.strip()
                if 4 <= len(p) <= 120:
                    raw[p] += 1
    if not raw:
        return ["General research"]
    ordered = sorted(raw.items(), key=lambda x: (-x[1], x[0].lower()))
    return [phrase for phrase, _ in ordered[:limit]]


def build_tag_match_dropdown_options(
    faculty: Sequence[Dict[str, Any]],
    dept_field_key_fn: Callable[[str], str],
    category_display: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "research_areas": build_research_area_labels(faculty, dept_field_key_fn, category_display),
        "work_types": build_work_type_phrases(faculty),
        "involvement": INVOLVEMENT_CHOICES,
        "years": STUDENT_YEAR_OPTIONS,
    }


def _display_to_category_key(research_display: str, category_display: Dict[str, str]) -> Optional[str]:
    inv = {v: k for k, v in category_display.items()}
    return inv.get(research_display)


def _score_one(
    pi: Dict[str, Any],
    research_display: str,
    work_phrase: str,
    involvement_key: str,
    year_label: str,
    dept_field_key_fn: Callable[[str], str],
    category_display: Dict[str, str],
) -> int:
    hay = _normalize_haystack(pi)
    dk = dept_field_key_fn((pi.get("department") or ""))
    rk = _display_to_category_key(research_display, category_display)
    score = 0

    # Research area (40 max)
    if rk and dk == rk:
        score += 40
    elif research_display.lower() in hay:
        score += 24
    elif rk and rk in hay:
        score += 16

    # Work / lab type (30 max)
    wp = (work_phrase or "").strip().lower()
    if wp and wp in hay:
        score += 30
    elif wp:
        words = [w for w in re.split(r"\s+", wp) if len(w) > 2 and w not in _STOPWORDS]
        if any(w in hay for w in words):
            score += 18

    # Involvement (20 max)
    fb = faculty_involvement_bucket(pi.get("title") or "")
    if involvement_key == fb:
        score += 20
    elif involvement_key == "flexible" and fb == "part_time":
        score += 8

    # Year alignment (10 max)
    if year_label == "Graduate":
        if any(k in hay for k in ("phd", "ph.d", "doctoral", "graduate", "master", "postdoc")):
            score += 10
        else:
            score += 4
    else:
        if any(k in hay for k in ("undergraduate", "ug ", "course", "summer")):
            score += 10
        else:
            score += 5

    return score


def rank_professors_for_answers(
    faculty: Sequence[Dict[str, Any]],
    research_display: str,
    work_phrase: str,
    involvement_key: str,
    year_label: str,
    dept_field_key_fn: Callable[[str], str],
    category_display: Dict[str, str],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Return top_k professors with deterministic ordering (tie-break: name, id).
    """
    scored: List[Tuple[int, str, str, Dict[str, Any]]] = []
    for pi in faculty:
        s = _score_one(
            pi,
            research_display,
            work_phrase,
            involvement_key,
            year_label,
            dept_field_key_fn,
            category_display,
        )
        name = (pi.get("name") or "").strip()
        pid = (pi.get("id") or name or "").strip()
        scored.append((s, name.lower(), pid, pi))

    scored.sort(key=lambda x: (-x[0], x[1], x[2]))

    out: List[Dict[str, Any]] = []
    for s, _, _, pi in scored[:top_k]:
        ra = (pi.get("research_areas") or "").strip()
        topics = pi.get("research_topics") or []
        if isinstance(topics, list) and topics:
            snippet = ra or ", ".join(str(t) for t in topics[:4])
        else:
            snippet = ra or "—"
        if len(snippet) > 160:
            snippet = snippet[:157] + "…"
        out.append(
            {
                "id": pi.get("id") or pi.get("name") or "",
                "name": pi.get("name") or "",
                "department": pi.get("department") or "",
                "school": pi.get("school") or "",
                "research_snippet": snippet,
                "match_score": s,
                "match_pct": min(99, int(round(s))),
                "email": pi.get("email") or "",
                "website": pi.get("website") or "",
                "title": pi.get("title") or "",
            }
        )
    return out
