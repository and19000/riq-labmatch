"""
RIQ Matching Algorithm v2.0 - "Find a Lab Fast"

A fast, semantic-lite matching algorithm with 7-parameter scoring.
NO runtime API calls, deterministic scoring, explainable breakdown.

SCORING (100 points total):
- Topic Fit: 30 points (semantic-lite with ontology + optional embeddings)
- Evidence Strength: 20 points (pubs/grants/projects alignment)
- Skill Bridge: 15 points (skill overlap + bridgeability)
- Actionability: 10 points (join page, openings, freshness)
- Constraint Fit: 10 points (level, remote, location)
- Intent Fit: 10 points (join_now/explore/mentorship + funding needs)
- Contactability: 5 points (email/website availability)

DESIGN PRINCIPLES:
1. FAST - No API calls, pure Python, precomputed where possible
2. TRANSPARENT - Clear scoring breakdown for every factor
3. DIVERSE - MMR reranking to avoid near-duplicate results
4. BACKWARD COMPATIBLE - Works with existing faculty/student schemas

Author: RIQ LabMatch
Version: 2.0
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, Set
import math
import re
import json
from datetime import datetime
from collections import Counter

from .ontology import get_ontology, get_phrases, get_skill_synonyms, normalize_skill

# ============================================================================
# CONSTANTS
# ============================================================================

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over", "under",
    "using", "use", "study", "studies", "research", "lab", "group", "work", "works",
    "working", "method", "methods", "approach", "approaches", "analysis", "model",
    "models", "system", "systems", "data", "new", "based", "also", "can", "may",
    "will", "our", "their", "these", "those", "such", "well", "more", "been",
    "being", "have", "has", "had", "are", "was", "were", "is", "be", "an", "a",
    "of", "in", "to", "on", "by", "as", "or", "at", "it", "its",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_lower(s: Optional[str]) -> str:
    """Safely convert to lowercase string."""
    return (s or "").lower()


def safe_list(x: Any) -> List[Any]:
    """Ensure value is a list."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        return [x]
    return list(x) if hasattr(x, '__iter__') else [x]


def parse_date(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string to datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


def cosine(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def jaccard(set_a: Set, set_b: Set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


# ============================================================================
# SCORING WEIGHTS
# ============================================================================

@dataclass
class MatchWeights:
    """Configurable weights for each scoring component."""
    topic_fit: int = 30
    evidence: int = 20
    skill: int = 15
    actionability: int = 10
    constraints: int = 10
    intent: int = 10
    contact: int = 5


WEIGHTS = MatchWeights()


# ============================================================================
# COMPONENT RESULT TYPE
# ============================================================================

@dataclass
class ComponentResult:
    """Result from a scoring component with availability tracking."""
    points: int
    available: bool
    max_points: int
    evidence: Dict[str, Any]


# ============================================================================
# TERM EXTRACTION
# ============================================================================

def extract_terms(
    text: str,
    ontology: Dict[str, List[str]],
    phrases: List[str]
) -> Dict[str, float]:
    """
    Extract weighted terms from text.
    
    Returns term -> weight dict where:
    - Phrases get higher weight (3.0)
    - Single tokens get base weight (1.0)
    - Ontology expansions get reduced weight (0.7)
    """
    t = safe_lower(text)
    tokens = TOKEN_RE.findall(t)
    base = [tok for tok in tokens if len(tok) >= 3 and tok not in STOPWORDS]

    term_w: Dict[str, float] = {}
    
    # Base tokens
    for tok in base:
        term_w[tok] = term_w.get(tok, 0.0) + 1.0

    # Phrase detection (higher weight for multi-word matches)
    for ph in phrases:
        ph_lower = ph.lower()
        if ph_lower in t:
            key = ph_lower.replace("-", " ").strip()
            term_w[key] = term_w.get(key, 0.0) + 3.0

    # Ontology expansion
    for key, exps in ontology.items():
        key_lower = key.lower()
        if key_lower in term_w or key_lower in t:
            for e in exps:
                ek = safe_lower(e)
                term_w[ek] = term_w.get(ek, 0.0) + 0.7

    # Normalize weights to [0, 1] range
    if term_w:
        maxw = max(term_w.values())
        if maxw > 0:
            for k in list(term_w.keys()):
                term_w[k] = term_w[k] / maxw

    return term_w


def weighted_overlap(
    student_terms: Dict[str, float],
    faculty_terms: Dict[str, float]
) -> Tuple[float, List[str]]:
    """
    Compute weighted overlap ratio and return matched terms.
    
    Returns (ratio in [0,1], list of top matched terms).
    """
    if not student_terms or not faculty_terms:
        return 0.0, []
    
    overlap = 0.0
    denom = sum(student_terms.values()) or 1.0
    matched_terms = []
    
    for term, sw in student_terms.items():
        if term in faculty_terms:
            overlap += sw * min(1.0, faculty_terms[term])
            matched_terms.append(term)
    
    # Sort by student weight (most important terms first)
    matched_terms.sort(key=lambda x: student_terms.get(x, 0.0), reverse=True)
    
    return max(0.0, min(1.0, overlap / denom)), matched_terms[:8]


# ============================================================================
# SCORING COMPONENTS
# ============================================================================

def topic_fit_score(
    student: Dict[str, Any],
    faculty: Dict[str, Any],
    ontology: Dict[str, List[str]],
    phrases: List[str]
) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 1: Topic Fit (0-30 points)
    
    Uses ontology + phrase detection + optional embeddings.
    Scoring approach:
    - Base points from Jaccard similarity of term sets (more balanced)
    - Bonus for matching high-weight terms (phrases, key concepts)
    - Bonus from embeddings if available
    """
    max_pts = WEIGHTS.topic_fit  # 30
    
    # Build text from available fields
    s_parts = [
        student.get("research_text") or "",
        " ".join(safe_list(student.get("topics"))),
        " ".join(safe_list(student.get("research_interests"))),
        student.get("research_field") or "",
        student.get("research_topics") or "",
    ]
    s_text = safe_lower(" ".join(s_parts))
    
    f_parts = [
        faculty.get("research_text") or "",
        " ".join(safe_list(faculty.get("research_topics"))),
        " ".join(safe_list(faculty.get("research_keywords"))),
        faculty.get("research_areas") or "",
        faculty.get("research_field") or "",
    ]
    f_text = safe_lower(" ".join(f_parts))

    s_terms = extract_terms(s_text, ontology, phrases)
    f_terms = extract_terms(f_text, ontology, phrases)
    
    if not s_terms or not f_terms:
        return 0, {"matched_terms": [], "overlap_ratio": 0, "jaccard": 0, "embedding_used": False}

    # Method 1: Jaccard similarity on term sets (intersection/union)
    s_set = set(s_terms.keys())
    f_set = set(f_terms.keys())
    intersection = s_set & f_set
    union = s_set | f_set
    jaccard_sim = len(intersection) / len(union) if union else 0.0
    
    # Method 2: Weighted overlap (gives more weight to important terms)
    weighted_ratio, matched = weighted_overlap(s_terms, f_terms)
    
    # Combined score: 40% Jaccard + 40% weighted overlap + 20% match count bonus
    # This balances different match scenarios
    match_count_bonus = min(1.0, len(intersection) / 3.0)  # Up to 1.0 for 3+ matches
    
    combined_ratio = 0.4 * jaccard_sim + 0.4 * weighted_ratio + 0.2 * match_count_bonus
    
    # Calculate base points (70% allocation for term matching)
    base_points = int(round(combined_ratio * max_pts * 0.7))
    
    # Minimum floor: if there are ANY good matches, give at least some points
    if len(intersection) >= 2 and base_points < 8:
        base_points = 8
    elif len(intersection) >= 1 and base_points < 4:
        base_points = 4

    # Optional embeddings (precomputed) - 30% allocation
    emb_points = 0
    s_emb = student.get("topic_embedding")
    f_emb = faculty.get("topic_embedding")
    if (isinstance(s_emb, list) and isinstance(f_emb, list) and 
        len(s_emb) == len(f_emb) and len(s_emb) > 0):
        sim = max(0.0, cosine(s_emb, f_emb))
        emb_points = int(round(sim * max_pts * 0.3))

    total = min(max_pts, base_points + emb_points)

    return total, {
        "matched_terms": matched[:5],
        "overlap_ratio": round(weighted_ratio, 3),
        "jaccard": round(jaccard_sim, 3),
        "match_count": len(intersection),
        "embedding_used": bool(emb_points),
        "base_points": base_points,
        "embedding_points": emb_points,
    }


def evidence_strength_score(
    student_terms: Dict[str, float],
    faculty: Dict[str, Any],
    ontology: Dict[str, List[str]],
    phrases: List[str]
) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 2: Evidence Strength (0-20 points)
    
    Prefers labs with recent/strong evidence on topic.
    Uses cached fields if available; otherwise partial credit.
    """
    max_pts = WEIGHTS.evidence
    
    # Gather evidence text from available fields
    pub_titles = safe_list(faculty.get("pub_titles_recent"))
    grant_titles = safe_list(faculty.get("grant_titles"))
    projects = safe_list(faculty.get("projects"))
    nsf_awards = faculty.get("nsf_awards")
    nih_awards = faculty.get("nih_awards")
    last_pub_year = faculty.get("last_pub_year")
    
    # Also check for NSF award titles if nsf_awards is a list of dicts
    if isinstance(nsf_awards, list):
        for award in nsf_awards:
            if isinstance(award, dict) and award.get("title"):
                grant_titles.append(award["title"])
    
    # Build evidence text
    ev_text = " ".join([str(x) for x in (pub_titles + grant_titles + projects) if x])
    
    if not ev_text.strip():
        # Fallback: partial credit based on funding presence
        has_funding = False
        if isinstance(nsf_awards, int) and nsf_awards > 0:
            has_funding = True
        elif isinstance(nih_awards, int) and nih_awards > 0:
            has_funding = True
        elif isinstance(nsf_awards, list) and len(nsf_awards) > 0:
            has_funding = True
        
        if has_funding:
            return 8, {"note": "has_funding_no_titles", "evidence_ratio": 0.4}
        return 0, {"note": "no_cached_evidence", "evidence_ratio": 0.0}

    ev_terms = extract_terms(ev_text, ontology, phrases)
    ratio, matched = weighted_overlap(student_terms, ev_terms)

    # Recency bonus
    recency_bonus = 0.0
    if isinstance(last_pub_year, (int, float)) and last_pub_year > 0:
        year_now = datetime.now().year
        age = max(0, year_now - int(last_pub_year))
        if age <= 2:
            recency_bonus = 1.0
        elif age <= 8:
            recency_bonus = max(0.0, (8 - age) / 6.0)
        else:
            recency_bonus = 0.0

    # Combined score: 80% evidence match + 20% recency
    base = ratio * 0.8 + recency_bonus * 0.2
    pts = int(round(max_pts * max(0.0, min(1.0, base))))
    
    return pts, {
        "matched_evidence_terms": matched[:5],
        "recency_bonus": round(recency_bonus, 3),
        "evidence_ratio": round(ratio, 3),
        "last_pub_year": last_pub_year,
    }


def skill_bridge_score(
    student: Dict[str, Any],
    faculty: Dict[str, Any]
) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 5: Skill Bridge (0-15 points)
    
    Compares student skills/courses/tools to lab requirements.
    Higher score for "ready now" (required overlap) and "bridgeable" (<=2 missing).
    """
    max_pts = WEIGHTS.skill
    
    # Normalize student skills
    s_skills_raw = safe_list(student.get("skills")) + safe_list(student.get("techniques"))
    s_skills = set(normalize_skill(x) for x in s_skills_raw if x)
    
    # Normalize faculty requirements
    req_raw = safe_list(faculty.get("required_skills"))
    pref_raw = safe_list(faculty.get("preferred_skills"))
    
    # Also extract from lab_techniques if available
    lab_tech = faculty.get("lab_techniques")
    if lab_tech:
        if isinstance(lab_tech, str):
            # Split by comma or semicolon
            tech_list = [t.strip() for t in re.split(r'[,;]', lab_tech) if t.strip()]
            pref_raw.extend(tech_list)
        elif isinstance(lab_tech, list):
            pref_raw.extend(lab_tech)
    
    req = set(normalize_skill(x) for x in req_raw if x)
    pref = set(normalize_skill(x) for x in pref_raw if x)

    if not s_skills and not req and not pref:
        # No skill data available - give partial credit
        return 5, {"note": "no_skill_data", "partial_credit": True}

    # Calculate overlaps
    req_hit = len(s_skills & req)
    req_total = max(1, len(req))
    req_ratio = req_hit / req_total if req else 0.5  # If no requirements, assume 50%

    pref_hit = len(s_skills & pref) if pref else 0
    pref_total = max(1, len(pref))
    pref_ratio = pref_hit / pref_total if pref else 0.0

    missing_req = list(req - s_skills)
    bridgeable = 1 if len(missing_req) <= 2 else 0

    # Scoring breakdown:
    # 60% required overlap, 20% bridgeability, 20% preferred signal
    if req:
        base = 0.6 * req_ratio + 0.2 * bridgeable + 0.2 * min(1.0, pref_ratio)
    else:
        # No required skills: base on preferred + general match
        base = 0.3 + 0.5 * min(1.0, pref_ratio) + 0.2 * (1 if s_skills else 0)
    
    pts = int(round(max_pts * max(0.0, min(1.0, base))))
    
    return pts, {
        "matched_required": sorted(list(s_skills & req))[:6],
        "missing_required": missing_req[:6],
        "matched_preferred": sorted(list(s_skills & pref))[:6],
        "bridgeable": bool(bridgeable),
        "req_overlap_ratio": round(req_ratio, 3) if req else None,
        "pref_overlap_ratio": round(pref_ratio, 3) if pref else None,
    }


def contactability_score(faculty: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 7: Contactability (0-5 points)
    
    Based on email and website availability.
    """
    max_pts = WEIGHTS.contact
    pts = 0
    
    email = faculty.get("email") or faculty.get("primary_email")
    # Handle email as list (some faculty have multiple)
    if isinstance(email, list):
        email = email[0] if email else None
    
    if email:
        pts += 3
        if faculty.get("email_verified") or faculty.get("primary_email_quality") == "verified":
            pts += 1
    
    if faculty.get("website"):
        pts += 1
    
    pts = min(max_pts, pts)
    
    return pts, {
        "has_email": bool(email),
        "email_verified": bool(faculty.get("email_verified") or faculty.get("primary_email_quality") == "verified"),
        "has_website": bool(faculty.get("website")),
    }


def constraint_fit_score(
    student: Dict[str, Any],
    faculty: Dict[str, Any]
) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 4: Constraint Fit (0-10 points)
    
    Hard filters + soft penalties for:
    - Level eligibility (undergrad/masters/phd/postdoc)
    - Remote policy
    - Location preference
    - Timeline (future: this_term/summer/later)
    """
    max_pts = WEIGHTS.constraints
    level = safe_lower(student.get("level") or student.get("academic_level"))
    
    # Eligibility flags (may be missing)
    accepts_map = {
        "undergrad": faculty.get("accepts_undergrads"),
        "masters": faculty.get("accepts_masters"),
        "phd": faculty.get("accepts_phd"),
        "postdoc": faculty.get("accepts_postdoc"),
    }
    accept_flag = accepts_map.get(level, None)

    remote_ok_student = student.get("remote_ok")
    remote_ok_faculty = faculty.get("remote_ok")

    pts = max_pts
    notes = []

    # Level eligibility check
    if accept_flag is False:
        return 0, {"blocked": True, "reason": "ineligible_level", "level": level}
    if accept_flag is None:
        pts -= 2  # Unknown eligibility
        notes.append("unknown_accepts_level")

    # Remote policy check
    if remote_ok_student is True and remote_ok_faculty is False:
        return 0, {"blocked": True, "reason": "remote_not_supported"}
    if remote_ok_student is True and remote_ok_faculty is None:
        pts -= 2
        notes.append("unknown_remote_policy")

    # Location preference (soft penalty)
    loc_pref = safe_lower(student.get("location_pref"))
    loc = safe_lower(faculty.get("location") or faculty.get("specific_location") or "")
    if loc_pref and loc and loc_pref not in loc:
        pts -= 2
        notes.append("location_mismatch_soft")

    pts = max(0, min(max_pts, pts))
    
    return pts, {
        "blocked": False,
        "notes": notes,
        "level": level,
        "location_match": loc_pref in loc if (loc_pref and loc) else None,
    }


def actionability_score(
    student: Dict[str, Any],
    faculty: Dict[str, Any]
) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 6: Actionability (0-10 points)
    
    Response likelihood proxies:
    - Has join/prospective page
    - Posted openings
    - Site freshness
    - Email + website presence as fallback
    """
    max_pts = WEIGHTS.actionability
    pts = 0
    
    if faculty.get("join_page"):
        pts += 4
    if faculty.get("openings_posted"):
        pts += 3
    
    # Site freshness
    d = parse_date(faculty.get("last_site_update"))
    if d:
        days = (datetime.now() - d).days
        if days <= 180:
            pts += 2
        elif days <= 365:
            pts += 1
    
    # Minimal fallback: website + email helps actionability
    if pts == 0:
        if faculty.get("website"):
            pts += 1
        email = faculty.get("email") or faculty.get("primary_email")
        if email:
            pts += 1
    
    pts = min(max_pts, pts)
    
    return pts, {
        "join_page": bool(faculty.get("join_page")),
        "openings_posted": bool(faculty.get("openings_posted")),
        "last_site_update": faculty.get("last_site_update"),
        "has_website": bool(faculty.get("website")),
    }


def intent_fit_score(
    student: Dict[str, Any],
    faculty: Dict[str, Any]
) -> Tuple[int, Dict[str, Any]]:
    """
    Parameter 3: Intent Fit (0-10 points)
    
    Based on student intent (join_now/explore/mentorship) and funding needs.
    """
    max_pts = WEIGHTS.intent
    intent = safe_lower(student.get("intent") or "join_now")
    needs_funding = bool(student.get("needs_funding"))
    
    # Determine if faculty has grants
    nsf = faculty.get("nsf_awards", 0)
    nih = faculty.get("nih_awards", 0)
    nsf_count = len(nsf) if isinstance(nsf, list) else (nsf or 0)
    nih_count = len(nih) if isinstance(nih, list) else (nih or 0)
    total_grants = nsf_count + nih_count
    has_grants = total_grants > 0

    pts = 0
    
    if intent == "join_now":
        # Reward actionable labs
        if faculty.get("openings_posted") or faculty.get("join_page"):
            pts += 5
        else:
            pts += 2
        # Funding alignment
        if needs_funding:
            if has_grants:
                pts += 5
            elif total_grants == 0:
                pts += 1  # Unknown
        else:
            pts += 3  # Doesn't need funding, slight bonus
            
    elif intent == "explore":
        # Boost labs with good resources
        if faculty.get("website"):
            pts += 5
        if faculty.get("pub_titles_recent") or faculty.get("research_topics"):
            pts += 3
        pts += 2  # Base for exploration
        
    elif intent == "mentorship":
        # Emphasize contactability
        if faculty.get("email") or faculty.get("primary_email"):
            pts += 5
        if faculty.get("website"):
            pts += 3
        pts += 2
        
    else:
        # Default (treat as join_now)
        pts = 5
        if needs_funding and has_grants:
            pts += 3

    pts = min(max_pts, pts)
    
    return pts, {
        "intent": intent,
        "needs_funding": needs_funding,
        "has_grants": has_grants,
        "total_grants": total_grants,
    }


# ============================================================================
# AVAILABILITY CHECKERS
# ============================================================================

def check_topic_availability(student: Dict[str, Any], faculty: Dict[str, Any]) -> bool:
    """Topic Fit is available if both student AND faculty have research text/topics."""
    s_parts = [
        student.get("research_text") or "",
        " ".join(safe_list(student.get("topics"))),
        " ".join(safe_list(student.get("research_interests"))),
        student.get("research_field") or "",
        student.get("research_topics") or "",
    ]
    s_text = " ".join(s_parts).strip()
    
    f_parts = [
        faculty.get("research_text") or "",
        " ".join(safe_list(faculty.get("research_topics"))),
        " ".join(safe_list(faculty.get("research_keywords"))),
        faculty.get("research_areas") or "",
        faculty.get("research_field") or "",
    ]
    f_text = " ".join(f_parts).strip()
    
    return bool(s_text) and bool(f_text)


def check_evidence_availability(faculty: Dict[str, Any]) -> bool:
    """Evidence Strength is available if faculty has pubs/grants/projects data."""
    pub_titles = safe_list(faculty.get("pub_titles_recent"))
    grant_titles = safe_list(faculty.get("grant_titles"))
    projects = safe_list(faculty.get("projects"))
    last_pub_year = faculty.get("last_pub_year")
    active_grants = faculty.get("active_grants_count")
    nsf = faculty.get("nsf_awards")
    nih = faculty.get("nih_awards")
    
    has_nsf = (isinstance(nsf, list) and len(nsf) > 0) or (isinstance(nsf, int) and nsf > 0)
    has_nih = (isinstance(nih, list) and len(nih) > 0) or (isinstance(nih, int) and nih > 0)
    
    return bool(pub_titles or grant_titles or projects or 
                (isinstance(last_pub_year, int) and last_pub_year > 0) or
                (isinstance(active_grants, int) and active_grants > 0) or
                has_nsf or has_nih)


def check_skill_availability(student: Dict[str, Any], faculty: Dict[str, Any]) -> bool:
    """Skill Bridge is available if student has skills OR faculty has required/preferred skills."""
    s_skills = safe_list(student.get("skills")) + safe_list(student.get("techniques"))
    f_req = safe_list(faculty.get("required_skills"))
    f_pref = safe_list(faculty.get("preferred_skills"))
    # Also check lab_techniques
    lab_tech = faculty.get("lab_techniques")
    if lab_tech:
        if isinstance(lab_tech, str):
            f_pref = f_pref + [t.strip() for t in lab_tech.split(",") if t.strip()]
        elif isinstance(lab_tech, list):
            f_pref = f_pref + lab_tech
    
    return bool(s_skills) or bool(f_req) or bool(f_pref)


def check_actionability_availability(faculty: Dict[str, Any]) -> bool:
    """Actionability is available if faculty has any actionability-related field."""
    return bool(
        faculty.get("join_page") is not None or
        faculty.get("openings_posted") is not None or
        faculty.get("last_site_update") or
        faculty.get("website") or
        faculty.get("email") or
        faculty.get("primary_email")
    )


def check_constraint_availability(student: Dict[str, Any], faculty: Dict[str, Any]) -> bool:
    """Constraint Fit is available if any constraint-related fields exist."""
    has_level = bool(student.get("level") or student.get("academic_level"))
    has_accepts = any([
        faculty.get("accepts_undergrads") is not None,
        faculty.get("accepts_masters") is not None,
        faculty.get("accepts_phd") is not None,
        faculty.get("accepts_postdoc") is not None,
    ])
    has_remote = (student.get("remote_ok") is not None or faculty.get("remote_ok") is not None)
    has_location = bool(student.get("location_pref") or faculty.get("location"))
    
    return has_level or has_accepts or has_remote or has_location


def check_intent_availability(student: Dict[str, Any], faculty: Dict[str, Any]) -> bool:
    """Intent Fit is available if student has intent/funding needs OR faculty has grants/openings."""
    has_intent = bool(student.get("intent"))
    has_funding_pref = student.get("needs_funding") is not None
    nsf = faculty.get("nsf_awards")
    nih = faculty.get("nih_awards")
    has_grants = (isinstance(nsf, (int, list)) or isinstance(nih, (int, list)))
    has_openings = (faculty.get("join_page") is not None or faculty.get("openings_posted") is not None)
    
    return has_intent or has_funding_pref or has_grants or has_openings


def check_contact_availability(faculty: Dict[str, Any]) -> bool:
    """Contactability is available if faculty has any contact-related field."""
    return bool(
        faculty.get("email") or
        faculty.get("primary_email") or
        faculty.get("website") or
        faculty.get("email_verified") is not None
    )


# ============================================================================
# MAIN SCORING FUNCTION
# ============================================================================

def compute_total_score(
    student: Dict[str, Any],
    faculty: Dict[str, Any],
    ontology: Dict[str, List[str]],
    phrases: List[str]
) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    """
    Compute total match score with availability-normalized scaling.
    
    Returns:
        (scaled_score, breakdown_dict, explanation_dict)
        
    The scaled_score is normalized based on available components:
    - raw_total = sum of component points
    - available_max = sum of max_points for available components
    - scaled_total = round(100 * raw_total / available_max) if available_max > 0
    """
    # Precompute student terms once
    s_parts = [
        student.get("research_text") or "",
        " ".join(safe_list(student.get("topics"))),
        " ".join(safe_list(student.get("research_interests"))),
        student.get("research_field") or "",
        student.get("research_topics") or "",
    ]
    s_text = safe_lower(" ".join(s_parts))
    s_terms = extract_terms(s_text, ontology, phrases)

    # Check availability for each component
    topic_avail = check_topic_availability(student, faculty)
    evid_avail = check_evidence_availability(faculty)
    skill_avail = check_skill_availability(student, faculty)
    act_avail = check_actionability_availability(faculty)
    cons_avail = check_constraint_availability(student, faculty)
    intent_avail = check_intent_availability(student, faculty)
    cont_avail = check_contact_availability(faculty)

    # Compute all component scores
    topic_pts, topic_ev = topic_fit_score(student, faculty, ontology, phrases)
    evid_pts, evid_ev = evidence_strength_score(s_terms, faculty, ontology, phrases)
    skill_pts, skill_ev = skill_bridge_score(student, faculty)
    act_pts, act_ev = actionability_score(student, faculty)
    cons_pts, cons_ev = constraint_fit_score(student, faculty)
    intent_pts, intent_ev = intent_fit_score(student, faculty)
    cont_pts, cont_ev = contactability_score(faculty)

    # Check for hard blocks
    if cons_ev.get("blocked"):
        return 0, {"blocked": True, "reason": cons_ev.get("reason")}, {}

    # Build component results with availability
    components = [
        ComponentResult(topic_pts if topic_avail else 0, topic_avail, WEIGHTS.topic_fit, topic_ev),
        ComponentResult(evid_pts if evid_avail else 0, evid_avail, WEIGHTS.evidence, evid_ev),
        ComponentResult(skill_pts if skill_avail else 0, skill_avail, WEIGHTS.skill, skill_ev),
        ComponentResult(act_pts if act_avail else 0, act_avail, WEIGHTS.actionability, act_ev),
        ComponentResult(cons_pts if cons_avail else 0, cons_avail, WEIGHTS.constraints, cons_ev),
        ComponentResult(intent_pts if intent_avail else 0, intent_avail, WEIGHTS.intent, intent_ev),
        ComponentResult(cont_pts if cont_avail else 0, cont_avail, WEIGHTS.contact, cont_ev),
    ]
    
    # Compute raw total and available max
    raw_total = sum(c.points for c in components)
    available_max = sum(c.max_points for c in components if c.available)
    
    # Compute scaled score
    if available_max > 0:
        scaled_total = round(100 * raw_total / available_max)
    else:
        scaled_total = 0
    scaled_total = max(0, min(100, scaled_total))
    
    # Compute completeness
    completeness = available_max / 100.0

    # Update evidence dicts with availability info
    if not topic_avail:
        topic_ev["unavailable"] = True
        topic_ev["note"] = "Not enough data to score topic fit."
    if not evid_avail:
        evid_ev["unavailable"] = True
        evid_ev["note"] = "No publication/grant data available."
    if not skill_avail:
        skill_ev["unavailable"] = True
        skill_ev["note"] = "No skill data available."
    if not act_avail:
        act_ev["unavailable"] = True
        act_ev["note"] = "No actionability data available."
    if not cons_avail:
        cons_ev["unavailable"] = True
        cons_ev["note"] = "No constraint data available."
    if not intent_avail:
        intent_ev["unavailable"] = True
        intent_ev["note"] = "No intent/funding data available."
    if not cont_avail:
        cont_ev["unavailable"] = True
        cont_ev["note"] = "No contact information available."

    breakdown = {
        "topic_fit": components[0].points,
        "evidence_strength": components[1].points,
        "skill_bridge": components[2].points,
        "actionability": components[3].points,
        "constraint_fit": components[4].points,
        "intent_fit": components[5].points,
        "contactability": components[6].points,
        "raw_total": raw_total,
        "available_max": available_max,
        "scaled_total": scaled_total,
        "completeness": round(completeness, 2),
        "total": scaled_total,  # Primary score for ranking
    }
    
    explanation = {
        "topic": topic_ev,
        "evidence": evid_ev,
        "skills": skill_ev,
        "actionability": act_ev,
        "constraints": cons_ev,
        "intent": intent_ev,
        "contact": cont_ev,
    }
    
    return scaled_total, breakdown, explanation


# ============================================================================
# MMR RERANKING
# ============================================================================

def mmr_rerank(
    scored: List[Dict[str, Any]],
    k: int,
    lambda_: float = 0.75
) -> List[Dict[str, Any]]:
    """
    Maximal Marginal Relevance reranking to diversify results.
    
    Takes top N candidates and selects k diverse results.
    lambda_ controls relevance vs diversity tradeoff (higher = more relevance).
    """
    if not scored:
        return []
    
    # Sort by base score and take top pool
    scored = sorted(scored, key=lambda x: x["score"], reverse=True)
    pool = scored[:max(k * 5, 50)]
    
    selected: List[Dict[str, Any]] = []
    selected_ids: Set[str] = set()

    def similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
        """Compute similarity between two candidates."""
        # Prefer embeddings if present
        ae = a.get("topic_embedding")
        be = b.get("topic_embedding")
        if (isinstance(ae, list) and isinstance(be, list) and 
            len(ae) == len(be) and len(ae) > 0):
            return max(0.0, cosine(ae, be))
        # Fall back to Jaccard on term sets
        return jaccard(set(a.get("term_set") or []), set(b.get("term_set") or []))

    while len(selected) < k and pool:
        best = None
        best_val = -1e9
        
        for cand in pool:
            if cand["faculty_id"] in selected_ids:
                continue
            
            rel = cand["score"] / 100.0
            div = 0.0
            if selected:
                div = max(similarity(cand, s) for s in selected)
            
            mmr = lambda_ * rel - (1 - lambda_) * div
            
            if mmr > best_val:
                best_val = mmr
                best = cand
        
        if best is None:
            break
        
        selected.append(best)
        selected_ids.add(best["faculty_id"])
        pool.remove(best)
    
    return selected


# ============================================================================
# MATCHING SERVICE (FLASK-COMPATIBLE)
# ============================================================================

class MatchingServiceV2:
    """
    Service class for Flask app integration.
    Drop-in replacement for MatchingService with v2 algorithm.
    """
    
    def __init__(self, faculty_json_path: str):
        """Initialize with faculty JSON file."""
        with open(faculty_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Support both formats
        if isinstance(data, list):
            self.faculty_list = data
            self.metadata = {}
        else:
            self.faculty_list = data.get("faculty", data)
            self.metadata = data.get("metadata", {})
        
        # Load ontology
        self.ontology = get_ontology()
        self.phrases = get_phrases()
        
        # Build inverted index for fast candidate retrieval
        self.keyword_index = self._build_keyword_index()
    
    def _build_keyword_index(self) -> Dict[str, List[int]]:
        """Build inverted index from faculty keywords."""
        index: Dict[str, List[int]] = {}
        
        for i, fac in enumerate(self.faculty_list):
            # Extract text from various fields
            text_parts = [
                fac.get("research_text") or "",
                " ".join(safe_list(fac.get("research_topics"))),
                " ".join(safe_list(fac.get("research_keywords"))),
                fac.get("research_areas") or "",
                fac.get("research_field") or "",
            ]
            text = " ".join(text_parts)
            terms = extract_terms(text, self.ontology, self.phrases)
            
            for term in terms.keys():
                if term not in index:
                    index[term] = []
                index[term].append(i)
        
        return index
    
    def _get_candidates(self, keywords: List[str]) -> List[int]:
        """Get candidate faculty indices using inverted index."""
        if not keywords:
            return list(range(len(self.faculty_list)))
        
        candidate_counts: Counter = Counter()
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in self.keyword_index:
                for idx in self.keyword_index[kw_lower]:
                    candidate_counts[idx] += 1
        
        # If no matches, return all
        if not candidate_counts:
            return list(range(len(self.faculty_list)))
        
        # Return indices sorted by match count (descending)
        return [idx for idx, _ in candidate_counts.most_common()]
    
    def match_student(
        self,
        research_field: str = "",
        research_topics: str = "",
        academic_level: str = "",
        work_style: str = "",
        needs_funding: bool = False,
        top_k: int = 20,
        # Additional v2 parameters (optional)
        intent: str = "join_now",
        skills: List[str] = None,
        remote_ok: bool = None,
        location_pref: str = "",
        # Legacy parameters (ignored but accepted for compatibility)
        research_interests: List[str] = None,
        department: str = "",
        level: str = "",
        techniques: List[str] = None,
        looking_for: str = "",
    ) -> List[Dict]:
        """
        Match student to faculty using v2 algorithm.
        
        Backward compatible with v1 API while supporting new v2 parameters.
        """
        # Build student profile dict
        student = {
            "research_field": research_field,
            "research_topics": research_topics,
            "topics": (research_interests or []) + [t.strip() for t in (research_topics or "").split(",") if t.strip()],
            "level": academic_level or level or "undergrad",
            "academic_level": academic_level or level or "undergrad",
            "intent": intent,
            "needs_funding": needs_funding,
            "skills": skills or [],
            "techniques": techniques or [],
            "remote_ok": remote_ok,
            "location_pref": location_pref,
            "work_style": work_style,
        }
        
        # Extract keywords for candidate selection
        text_parts = [research_field, research_topics]
        if research_interests:
            text_parts.extend(research_interests)
        keywords = []
        for part in text_parts:
            if part:
                tokens = TOKEN_RE.findall(part.lower())
                keywords.extend([t for t in tokens if len(t) >= 3 and t not in STOPWORDS])
        keywords = list(set(keywords))
        
        # Get candidates (uses inverted index for speed)
        candidate_indices = self._get_candidates(keywords)
        
        # Score all candidates
        scored_results = []
        for i in candidate_indices:
            fac = self.faculty_list[i]
            total, breakdown, explanation = compute_total_score(
                student, fac, self.ontology, self.phrases
            )
            
            if total > 0 and not breakdown.get("blocked"):
                # Build term set for MMR
                f_text = " ".join([
                    fac.get("research_text") or "",
                    " ".join(safe_list(fac.get("research_topics"))),
                    fac.get("research_areas") or "",
                ])
                f_terms = extract_terms(f_text, self.ontology, self.phrases)
                
                scored_results.append({
                    "faculty": fac,
                    "faculty_id": fac.get("id") or fac.get("name") or str(i),
                    "score": total,
                    "breakdown": breakdown,
                    "explanation": explanation,
                    "term_set": list(f_terms.keys()),
                    "topic_embedding": fac.get("topic_embedding"),
                })
        
        # Sort by scaled score (primary), tie-break by raw_total, then topic_fit
        def sort_key(x):
            bd = x["breakdown"]
            return (x["score"], bd.get("raw_total", 0), bd.get("topic_fit", 0))
        scored_results.sort(key=sort_key, reverse=True)
        
        # Apply MMR reranking if we have enough results
        if len(scored_results) > top_k:
            scored_results = mmr_rerank(scored_results, top_k)
        else:
            scored_results = scored_results[:top_k]
        
        # Format output (backward compatible with v1)
        results = []
        for i, r in enumerate(scored_results):
            fac = r["faculty"]
            
            # Get email (handle various formats)
            email = fac.get("primary_email") or fac.get("email") or ""
            if isinstance(email, list):
                email = email[0] if email else ""
            
            # Build explanation string
            exp = r["explanation"]
            reason_parts = []
            if exp.get("topic", {}).get("matched_terms"):
                terms = exp["topic"]["matched_terms"][:3]
                reason_parts.append(f"Matches: {', '.join(terms)}")
            
            # Funding info
            intent_info = exp.get("intent", {})
            if intent_info.get("total_grants", 0) > 0:
                reason_parts.append(f"{intent_info['total_grants']} active grants")
            
            # Skills
            skills_info = exp.get("skills", {})
            if skills_info.get("matched_required"):
                reason_parts.append(f"Skills: {', '.join(skills_info['matched_required'][:2])}")
            
            explanation_str = "; ".join(reason_parts) if reason_parts else "General match"
            
            # Extract normalized scoring fields
            bd = r["breakdown"]
            completeness = bd.get("completeness", 1.0)
            raw_score = bd.get("raw_total", r["score"])
            available_max = bd.get("available_max", 100)
            
            # Add completeness note to explanation if data is incomplete
            if completeness < 0.8:
                missing_count = sum(1 for k in ["topic", "evidence", "skills", "actionability", "constraints", "intent", "contact"]
                                   if exp.get(k, {}).get("unavailable"))
                if missing_count > 0:
                    explanation_str += f" ({missing_count} categories not scored due to missing data)"
            
            results.append({
                "name": fac.get("name", ""),
                "email": email,
                "email_quality": fac.get("primary_email_quality") or fac.get("email_quality", "uncertain"),
                "website": fac.get("website", ""),
                "department": fac.get("department", ""),
                "school": fac.get("school", "") or fac.get("institution", ""),
                "h_index": int(fac.get("h_index") or 0),
                "total_score": round(r["score"], 1),  # Scaled score (primary)
                "breakdown": {k: round(v, 1) if isinstance(v, (int, float)) else v for k, v in bd.items()},
                "explanation": explanation_str,
                "research_topics": safe_list(fac.get("research_topics"))[:5] or [fac.get("research_areas", "")],
                "nsf_awards": len(fac.get("nsf_awards", [])) if isinstance(fac.get("nsf_awards"), list) else (fac.get("nsf_awards") or 0),
                "nih_awards": len(fac.get("nih_awards", [])) if isinstance(fac.get("nih_awards"), list) else (fac.get("nih_awards") or 0),
                "rank": i + 1,
                # V2 normalized scoring fields
                "score": round(r["score"], 1),        # Scaled score (same as total_score)
                "raw_score": round(raw_score, 1),     # Raw total before normalization
                "available_max": available_max,        # Max possible points for available components
                "completeness": round(completeness, 2),  # Data completeness (0-1)
                # V2 detailed breakdown
                "score_breakdown_v2": bd,
                "match_details": r["explanation"],
            })
        
        return results
    
    def search_keywords(self, keywords: List[str], top_k: int = 20) -> List[Dict]:
        """Quick keyword search (backward compatible)."""
        keywords = [k.lower().strip() for k in keywords if len(k) > 2]
        scores: Counter = Counter()
        
        for kw in keywords:
            if kw in self.keyword_index:
                for idx in self.keyword_index[kw]:
                    scores[idx] += 1
        
        top_indices = [idx for idx, _ in scores.most_common(top_k)]
        
        results = []
        for i in top_indices:
            fac = self.faculty_list[i]
            email = fac.get("primary_email") or fac.get("email") or ""
            if isinstance(email, list):
                email = email[0] if email else ""
            
            results.append({
                "name": fac.get("name", ""),
                "email": email,
                "email_quality": fac.get("primary_email_quality") or fac.get("email_quality", "uncertain"),
                "website": fac.get("website", ""),
                "department": fac.get("department", ""),
                "h_index": int(fac.get("h_index") or 0),
                "research_topics": safe_list(fac.get("research_topics"))[:5],
            })
        
        return results
    
    def get_faculty_count(self) -> int:
        """Return total faculty count."""
        return len(self.faculty_list)
    
    def get_departments(self) -> List[str]:
        """Return sorted list of unique departments."""
        depts = {f.get("department") for f in self.faculty_list if f.get("department")}
        return sorted(depts)


# ============================================================================
# CLI FOR TESTING
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test faculty matching v2")
    parser.add_argument("--faculty-json", required=True, help="Path to faculty JSON")
    parser.add_argument("--research-field", default="", help="Research field")
    parser.add_argument("--research-topics", default="", help="Research topics (comma-separated)")
    parser.add_argument("--level", default="phd", help="Academic level")
    parser.add_argument("--work-style", default="both", help="Work style")
    parser.add_argument("--needs-funding", action="store_true", help="Needs funding")
    parser.add_argument("--intent", default="join_now", help="Intent: join_now/explore/mentorship")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    args = parser.parse_args()
    
    print(f"Loading faculty from {args.faculty_json}...")
    service = MatchingServiceV2(args.faculty_json)
    print(f"Loaded {service.get_faculty_count()} faculty profiles")
    
    print(f"\nMatching with:")
    print(f"  Field: {args.research_field}")
    print(f"  Topics: {args.research_topics}")
    print(f"  Level: {args.level}")
    print(f"  Intent: {args.intent}")
    print(f"  Needs funding: {args.needs_funding}")
    
    results = service.match_student(
        research_field=args.research_field,
        research_topics=args.research_topics,
        academic_level=args.level,
        work_style=args.work_style,
        needs_funding=args.needs_funding,
        intent=args.intent,
        top_k=args.top_k,
    )
    
    print(f"\nTop {len(results)} matches:")
    print("-" * 80)
    for r in results:
        print(f"#{r['rank']} {r['name']} (Score: {r['total_score']})")
        print(f"   {r['school']} - {r['department']}")
        print(f"   {r['explanation']}")
        print(f"   Breakdown: Topic={r['breakdown'].get('topic_fit',0)}, "
              f"Evidence={r['breakdown'].get('evidence_strength',0)}, "
              f"Skills={r['breakdown'].get('skill_bridge',0)}, "
              f"Intent={r['breakdown'].get('intent_fit',0)}")
        print()


if __name__ == "__main__":
    main()
