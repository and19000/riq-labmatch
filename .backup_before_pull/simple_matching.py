"""
Simple Faculty Matching Algorithm v1.0

A fast, efficient matching algorithm that doesn't require ML or LLMs.
Uses keyword overlap and simple scoring for student-faculty matching.

DESIGN PRINCIPLES:
1. FAST - No API calls, pure Python
2. SIMPLE - Keyword matching, no embeddings
3. TRANSPARENT - Clear scoring breakdown
4. EXTENSIBLE - Easy to add new factors

SCORING (100 points total):
- Research Interest Match: 40 points (keyword overlap)
- Department Fit: 15 points (exact/partial match)
- Experience Level: 15 points (h-index appropriate for level)
- Funding Activity: 10 points (active grants = active lab)
- Research Output: 10 points (recent publications)
- Email Quality: 10 points (verified email = contactable)

Author: RIQ LabMatch
Version: 1.0
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import math

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class StudentProfile:
    """Student profile for matching."""
    research_interests: List[str] = field(default_factory=list)  # Keywords/topics
    techniques: List[str] = field(default_factory=list)          # Lab techniques
    department_preference: str = ""                               # Preferred department
    level: str = ""                                               # undergrad, masters, phd, postdoc
    looking_for: str = ""                                         # research, internship, job
    
    # Optional fields
    gpa: float = 0.0
    prior_research: bool = False
    publications: int = 0
    
    def to_keywords(self) -> List[str]:
        """Convert profile to searchable keywords."""
        keywords = []
        
        # Add research interests (normalized)
        for interest in self.research_interests:
            keywords.extend(self._normalize_text(interest))
        
        # Add techniques
        for tech in self.techniques:
            keywords.extend(self._normalize_text(tech))
        
        return list(set(keywords))
    
    @staticmethod
    def _normalize_text(text: str) -> List[str]:
        """Normalize text to keywords."""
        text = text.lower()
        # Remove common words
        stopwords = {'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        words = re.findall(r'\b[a-z]{3,}\b', text)
        return [w for w in words if w not in stopwords]


@dataclass
class FacultyProfile:
    """Faculty profile loaded from pipeline JSON."""
    name: str
    email: str = ""
    email_quality: str = "uncertain"
    website: str = ""
    website_quality: str = "uncertain"
    department: str = ""
    school: str = ""  # Institution/school name for UI
    h_index: int = 0
    works_count: int = 0
    cited_by_count: int = 0
    research_topics: List[str] = field(default_factory=list)
    research_keywords: List[str] = field(default_factory=list)
    nsf_awards: int = 0
    nih_awards: int = 0
    total_funding: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FacultyProfile':
        nsf = data.get("nsf_awards", 0)
        nih = data.get("nih_awards", 0)
        nsf_awards = len(nsf) if isinstance(nsf, list) else (nsf or 0)
        nih_awards = len(nih) if isinstance(nih, list) else (nih or 0)
        return cls(
            name=data.get("name", ""),
            email=data.get("primary_email", "") or data.get("email", ""),
            email_quality=data.get("primary_email_quality", data.get("email_quality", "uncertain")),
            website=data.get("website", ""),
            website_quality=data.get("website_quality", "uncertain"),
            department=data.get("department", ""),
            school=data.get("school", "") or data.get("institution", ""),
            h_index=data.get("h_index", 0),
            works_count=data.get("works_count", 0),
            cited_by_count=data.get("cited_by_count", 0),
            research_topics=data.get("research_topics", []),
            research_keywords=data.get("research_keywords", []),
            nsf_awards=nsf_awards,
            nih_awards=nih_awards,
            total_funding=data.get("total_funding", 0),
        )
    
    def get_keywords(self) -> List[str]:
        """Get all searchable keywords."""
        if self.research_keywords:
            return self.research_keywords
        
        # Fall back to extracting from topics
        keywords = []
        for topic in self.research_topics:
            words = re.findall(r'\b[a-z]{3,}\b', topic.lower())
            keywords.extend(words)
        return list(set(keywords))


@dataclass
class MatchResult:
    """Result of matching a student to a faculty member."""
    faculty: FacultyProfile
    total_score: float
    breakdown: Dict[str, float]
    explanation: str
    rank: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "name": self.faculty.name,
            "email": self.faculty.email,
            "email_quality": self.faculty.email_quality,
            "website": self.faculty.website,
            "department": self.faculty.department,
            "h_index": self.faculty.h_index,
            "total_score": round(self.total_score, 1),
            "breakdown": {k: round(v, 1) for k, v in self.breakdown.items()},
            "explanation": self.explanation,
            "rank": self.rank,
            "research_topics": self.faculty.research_topics[:5],
        }


# ============================================================================
# MATCHING ENGINE
# ============================================================================

class SimpleMatcher:
    """
    Simple, fast faculty matching engine.
    
    No ML, no LLMs, no API calls - just keyword matching and scoring.
    """
    
    # Score weights (total = 100)
    WEIGHTS = {
        "research_match": 40,      # Keyword overlap
        "department_fit": 15,      # Department match
        "level_fit": 15,           # H-index appropriate for level
        "funding_activity": 10,   # Active grants
        "research_output": 10,    # Publication count
        "contactability": 10,     # Email quality
    }
    
    # H-index ranges appropriate for each level
    H_INDEX_RANGES = {
        "undergrad": (5, 50),      # Mid-career faculty often better mentors
        "masters": (10, 80),       # Broader range
        "phd": (15, 150),          # Can work with senior faculty
        "postdoc": (20, 200),      # Senior faculty preferred
    }
    
    def __init__(self, faculty_data: List[Dict]):
        """
        Initialize matcher with faculty data.
        
        Args:
            faculty_data: List of faculty dicts from pipeline JSON
        """
        self.faculty = [FacultyProfile.from_dict(f) for f in faculty_data]
        
        # Build keyword index for fast lookup
        self.keyword_index = self._build_keyword_index()
    
    def _build_keyword_index(self) -> Dict[str, List[int]]:
        """Build inverted index: keyword -> faculty indices."""
        index = {}
        for i, fac in enumerate(self.faculty):
            for kw in fac.get_keywords():
                if kw not in index:
                    index[kw] = []
                index[kw].append(i)
        return index
    
    def match(self, student: StudentProfile, top_k: int = 10) -> List[MatchResult]:
        """
        Match a student to faculty members.
        
        Args:
            student: StudentProfile with research interests, etc.
            top_k: Number of top matches to return
            
        Returns:
            List of MatchResult sorted by score descending
        """
        student_keywords = student.to_keywords()
        
        # Fast pre-filtering using keyword index
        candidate_indices = set()
        for kw in student_keywords:
            if kw in self.keyword_index:
                candidate_indices.update(self.keyword_index[kw])
        
        # If no keyword matches, consider all faculty
        if not candidate_indices:
            candidate_indices = set(range(len(self.faculty)))
        
        # Score candidates
        results = []
        for i in candidate_indices:
            fac = self.faculty[i]
            score, breakdown, explanation = self._score_match(student, fac, student_keywords)
            results.append(MatchResult(
                faculty=fac,
                total_score=score,
                breakdown=breakdown,
                explanation=explanation
            ))
        
        # Sort by score
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign ranks
        for i, r in enumerate(results[:top_k]):
            r.rank = i + 1
        
        return results[:top_k]
    
    def _score_match(self, student: StudentProfile, faculty: FacultyProfile,
                     student_keywords: List[str]) -> Tuple[float, Dict[str, float], str]:
        """
        Score a student-faculty match.
        
        Returns: (total_score, breakdown_dict, explanation_string)
        """
        breakdown = {}
        explanations = []
        
        # 1. Research Match (40 points)
        faculty_keywords = faculty.get_keywords()
        overlap = set(student_keywords) & set(faculty_keywords)
        
        if student_keywords and faculty_keywords:
            # Jaccard-like similarity
            overlap_ratio = len(overlap) / min(len(student_keywords), len(faculty_keywords))
            research_score = overlap_ratio * self.WEIGHTS["research_match"]
        else:
            research_score = 0
        
        breakdown["research_match"] = research_score
        if overlap:
            explanations.append(f"Research overlap: {', '.join(list(overlap)[:5])}")
        
        # 2. Department Fit (15 points)
        dept_score = 0
        if student.department_preference and faculty.department:
            student_dept = student.department_preference.lower()
            faculty_dept = faculty.department.lower()
            
            if student_dept == faculty_dept:
                dept_score = self.WEIGHTS["department_fit"]
                explanations.append(f"Department match: {faculty.department}")
            elif student_dept in faculty_dept or faculty_dept in student_dept:
                dept_score = self.WEIGHTS["department_fit"] * 0.7
                explanations.append(f"Related department: {faculty.department}")
        
        breakdown["department_fit"] = dept_score
        
        # 3. Level Fit (15 points)
        level_score = 0
        if student.level and student.level in self.H_INDEX_RANGES:
            min_h, max_h = self.H_INDEX_RANGES[student.level]
            
            if min_h <= faculty.h_index <= max_h:
                level_score = self.WEIGHTS["level_fit"]
            elif faculty.h_index < min_h:
                # Too junior
                level_score = self.WEIGHTS["level_fit"] * 0.5
            else:
                # Very senior - might be harder to access
                level_score = self.WEIGHTS["level_fit"] * 0.7
        else:
            level_score = self.WEIGHTS["level_fit"] * 0.8  # Default
        
        breakdown["level_fit"] = level_score
        
        # 4. Funding Activity (10 points)
        funding_score = 0
        total_grants = faculty.nsf_awards + faculty.nih_awards
        
        if total_grants >= 3:
            funding_score = self.WEIGHTS["funding_activity"]
            explanations.append(f"Active funding: {total_grants} grants")
        elif total_grants >= 1:
            funding_score = self.WEIGHTS["funding_activity"] * 0.7
        else:
            funding_score = self.WEIGHTS["funding_activity"] * 0.3
        
        breakdown["funding_activity"] = funding_score
        
        # 5. Research Output (10 points)
        output_score = 0
        if faculty.works_count >= 100:
            output_score = self.WEIGHTS["research_output"]
        elif faculty.works_count >= 50:
            output_score = self.WEIGHTS["research_output"] * 0.8
        elif faculty.works_count >= 20:
            output_score = self.WEIGHTS["research_output"] * 0.6
        else:
            output_score = self.WEIGHTS["research_output"] * 0.4
        
        breakdown["research_output"] = output_score
        
        # 6. Contactability (10 points)
        contact_score = 0
        if faculty.email:
            if faculty.email_quality == "verified":
                contact_score = self.WEIGHTS["contactability"]
                explanations.append("Verified email available")
            elif faculty.email_quality == "uncertain":
                contact_score = self.WEIGHTS["contactability"] * 0.6
            else:
                contact_score = self.WEIGHTS["contactability"] * 0.3
        else:
            contact_score = 0
            explanations.append("No email available")
        
        breakdown["contactability"] = contact_score
        
        # Total
        total = sum(breakdown.values())
        
        # Build explanation
        explanation = f"h-index: {faculty.h_index}, "
        if explanations:
            explanation += "; ".join(explanations)
        
        return total, breakdown, explanation
    
    def quick_search(self, keywords: List[str], top_k: int = 20) -> List[FacultyProfile]:
        """
        Quick keyword search without full scoring.
        
        Args:
            keywords: Search keywords
            top_k: Max results
            
        Returns:
            List of matching faculty profiles
        """
        # Normalize keywords
        keywords = [k.lower().strip() for k in keywords if len(k) > 2]
        
        # Find candidates
        scores = Counter()
        for kw in keywords:
            if kw in self.keyword_index:
                for idx in self.keyword_index[kw]:
                    scores[idx] += 1
        
        # Sort by match count
        top_indices = [idx for idx, _ in scores.most_common(top_k)]
        
        return [self.faculty[i] for i in top_indices]


# ============================================================================
# INTEGRATION WITH FLASK APP
# ============================================================================

class MatchingService:
    """
    Service class for integrating with Flask app.
    
    Usage:
        # Initialize once at app startup
        service = MatchingService("output/harvard_university_..._v533.json")
        
        # Match a student
        results = service.match_student(
            research_interests=["machine learning", "computer vision"],
            department="Computer Science",
            level="phd"
        )
    """
    
    def __init__(self, faculty_json_path: str):
        """Load faculty data and initialize matcher."""
        with open(faculty_json_path, 'r') as f:
            data = json.load(f)
        
        faculty_list = data.get("faculty", data)  # Handle both formats
        self.matcher = SimpleMatcher(faculty_list)
        self.metadata = data.get("metadata", {})
    
    def match_student(self,
                      research_field: str = "",
                      research_topics: str = "",
                      academic_level: str = "",
                      work_style: str = "",
                      needs_funding: bool = False,
                      top_k: int = 20,
                      # Legacy params (ignored when using 5-question MVP)
                      research_interests: List[str] = None,
                      department: str = "",
                      level: str = "",
                      techniques: List[str] = None,
                      looking_for: str = "",
                      ) -> List[Dict]:
        """
        Fast 5-question matching (MVP). No LLM, under 1 second.
        
        Args:
            research_field: Main field (e.g., biology, computer science)
            research_topics: Comma-separated keywords (e.g., "machine learning, neural networks")
            academic_level: undergrad/masters/phd/postdoc
            work_style: experimental/computational/both
            needs_funding: True if funded position needed
            top_k: Number of results
        """
        # Parse keywords from field + topics
        keywords = []
        if research_field:
            keywords.extend(research_field.lower().split())
        if research_topics:
            for topic in research_topics.split(","):
                keywords.extend(topic.lower().strip().split())
        keywords = list(set(k for k in keywords if len(k) > 2))

        results = []
        for fac in self.matcher.faculty:
            score, breakdown, explanation = self._score_faculty(
                fac, keywords, academic_level or "undergrad", work_style or "both", needs_funding
            )
            if score > 0:
                results.append({
                    "name": fac.name,
                    "email": fac.email,
                    "email_quality": fac.email_quality,
                    "website": fac.website,
                    "department": fac.department,
                    "school": fac.school,
                    "h_index": fac.h_index,
                    "total_score": round(score, 1),
                    "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
                    "explanation": explanation,
                    "research_topics": (fac.research_topics or [])[:5],
                    "nsf_awards": fac.nsf_awards,
                    "nih_awards": fac.nih_awards,
                })
        results.sort(key=lambda x: x["total_score"], reverse=True)
        for i, r in enumerate(results[:top_k]):
            r["rank"] = i + 1
        return results[:top_k]

    def _score_faculty(self, fac: FacultyProfile, keywords: List[str], level: str,
                       work_style: str, needs_funding: bool) -> Tuple[float, Dict[str, float], str]:
        """
        Score a faculty member (100 points max).
        Keyword match 50, Level fit 20, Funding 15, Contactable 15.
        """
        score = 0.0
        breakdown = {}
        reasons = []

        # 1. Keyword match (50 pts)
        fac_keywords = set((fac.research_keywords or []) + [t.lower() for t in (fac.research_topics or [])])
        fac_text = " ".join(fac.research_topics or []).lower()
        matches = 0
        matched_terms = []
        for kw in keywords:
            if kw in fac_keywords or kw in fac_text:
                matches += 1
                matched_terms.append(kw)
        if keywords:
            keyword_score = min(50.0, (matches / len(keywords)) * 50.0)
        else:
            keyword_score = 25.0
        breakdown["research"] = round(keyword_score, 1)
        score += keyword_score
        if matched_terms:
            reasons.append(f"Matches: {', '.join(matched_terms[:3])}")

        # 2. Level fit (20 pts)
        h_ranges = {"undergrad": (5, 60), "masters": (10, 100), "phd": (15, 150), "postdoc": (20, 200)}
        if level in h_ranges:
            min_h, max_h = h_ranges[level]
            if min_h <= fac.h_index <= max_h:
                level_score = 20.0
            elif fac.h_index < min_h:
                level_score = 10.0
            else:
                level_score = 15.0
        else:
            level_score = 15.0
        breakdown["level_fit"] = level_score
        score += level_score

        # 3. Funding (15 pts)
        has_funding = (fac.nsf_awards + fac.nih_awards) > 0
        if needs_funding:
            if has_funding:
                funding_score = 15.0
                reasons.append(f"{fac.nsf_awards + fac.nih_awards} active grants")
            else:
                funding_score = 0.0
        else:
            funding_score = 10.0
        breakdown["funding"] = funding_score
        score += funding_score

        # 4. Contactable (15 pts)
        contact_score = 0.0
        if fac.email:
            contact_score += 10.0
            if fac.email_quality == "verified":
                contact_score += 3.0
        if fac.website:
            contact_score += 2.0
        contact_score = min(15.0, contact_score)
        breakdown["contact"] = contact_score
        score += contact_score

        explanation = "; ".join(reasons) if reasons else "General match"
        return score, breakdown, explanation
    
    def search_keywords(self, keywords: List[str], top_k: int = 20) -> List[Dict]:
        """
        Quick keyword search.
        
        Args:
            keywords: Search terms
            top_k: Max results
            
        Returns:
            List of faculty dicts
        """
        results = self.matcher.quick_search(keywords, top_k)
        return [
            {
                "name": f.name,
                "email": f.email,
                "email_quality": f.email_quality,
                "website": f.website,
                "department": f.department,
                "h_index": f.h_index,
                "research_topics": f.research_topics[:5],
            }
            for f in results
        ]
    
    def get_faculty_count(self) -> int:
        """Get total faculty count."""
        return len(self.matcher.faculty)
    
    def get_departments(self) -> List[str]:
        """Get list of unique departments."""
        depts = set()
        for f in self.matcher.faculty:
            if f.department:
                depts.add(f.department)
        return sorted(list(depts))


# ============================================================================
# CLI FOR TESTING
# ============================================================================

def main():
    """Test the matching algorithm (5-question MVP)."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test faculty matching (5-question MVP)")
    parser.add_argument("--faculty-json", required=True, help="Path to faculty JSON")
    parser.add_argument("--research-field", default="", help="Main field (e.g., biology, computer science)")
    parser.add_argument("--research-topics", default="", help="Comma-separated topics (e.g., machine learning, cancer)")
    parser.add_argument("--level", default="phd", help="Academic level: undergrad/masters/phd/postdoc")
    parser.add_argument("--work-style", default="both", help="experimental/computational/both")
    parser.add_argument("--needs-funding", action="store_true", help="Need funded position")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    
    args = parser.parse_args()
    
    print(f"Loading faculty from {args.faculty_json}...")
    service = MatchingService(args.faculty_json)
    print(f"Loaded {service.get_faculty_count()} faculty\n")
    
    print(f"Field: {args.research_field or '(any)'}, Topics: {args.research_topics or '(any)'}")
    print(f"Level: {args.level}, Needs funding: {args.needs_funding}\n")
    
    results = service.match_student(
        research_field=args.research_field,
        research_topics=args.research_topics,
        academic_level=args.level,
        work_style=args.work_style,
        needs_funding=args.needs_funding,
        top_k=args.top_k,
    )
    
    print("=" * 60)
    print("TOP MATCHES")
    print("=" * 60)
    
    for r in results:
        print(f"\n#{r['rank']} {r['name']} (Score: {r['total_score']})")
        print(f"   Email: {r['email']} ({r['email_quality']})")
        print(f"   Dept: {r['department']}, h-index: {r['h_index']}")
        print(f"   Topics: {', '.join(r.get('research_topics', []))}")
        print(f"   {r['explanation']}")
        print(f"   Breakdown: {r['breakdown']}")


if __name__ == "__main__":
    main()
