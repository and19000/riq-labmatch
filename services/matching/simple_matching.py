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
    research_interests: List[str] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)
    department_preference: str = ""
    level: str = ""
    looking_for: str = ""
    gpa: float = 0.0
    prior_research: bool = False
    publications: int = 0

    def to_keywords(self) -> List[str]:
        keywords = []
        for interest in self.research_interests:
            keywords.extend(self._normalize_text(interest))
        for tech in self.techniques:
            keywords.extend(self._normalize_text(tech))
        return list(set(keywords))

    @staticmethod
    def _normalize_text(text: str) -> List[str]:
        text = text.lower()
        stopwords = {'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        words = re.findall(r'\b[a-z]{3,}\b', text)
        return [w for w in words if w not in stopwords]


@dataclass
class FacultyProfile:
    """Faculty profile - works with pipeline JSON and NSF data."""
    name: str
    email: str = ""
    email_quality: str = "uncertain"
    website: str = ""
    website_quality: str = "uncertain"
    department: str = ""
    school: str = ""
    h_index: int = 0
    works_count: int = 0
    cited_by_count: int = 0
    research_topics: List[str] = field(default_factory=list)
    research_keywords: List[str] = field(default_factory=list)
    research_field: str = ""  # NSF directorate / field
    nsf_awards: int = 0
    nih_awards: int = 0
    total_funding: int = 0

    @classmethod
    def from_dict(cls, data: Dict) -> 'FacultyProfile':
        nsf = data.get("nsf_awards", 0)
        nih = data.get("nih_awards", 0)
        nsf_awards = len(nsf) if isinstance(nsf, list) else (nsf or 0)
        nih_awards = len(nih) if isinstance(nih, list) else (nih or 0)
        # Support both pipeline format (research_topics list) and legacy (research_areas string)
        rtopics = data.get("research_topics", [])
        if not rtopics and isinstance(data.get("research_areas"), str):
            rtopics = [x.strip() for x in (data.get("research_areas") or "").split(";") if x.strip()]
        rkeywords = data.get("research_keywords", [])
        rfield = data.get("research_field", "")
        return cls(
            name=data.get("name", ""),
            email=(data.get("primary_email") or data.get("email") or ""),
            email_quality=data.get("primary_email_quality", data.get("email_quality", "uncertain")),
            website=data.get("website", ""),
            website_quality=data.get("website_quality", "uncertain"),
            department=data.get("department", ""),
            school=data.get("school", "") or data.get("institution", ""),
            h_index=int(data.get("h_index", 0)) if data.get("h_index") is not None else 0,
            works_count=data.get("works_count", 0),
            cited_by_count=data.get("cited_by_count", 0),
            research_topics=rtopics,
            research_keywords=rkeywords,
            research_field=rfield,
            nsf_awards=nsf_awards,
            nih_awards=nih_awards,
            total_funding=data.get("total_funding", 0),
        )

    def get_keywords(self) -> List[str]:
        if self.research_keywords:
            return self.research_keywords
        keywords = []
        for topic in self.research_topics:
            words = re.findall(r'\b[a-z]{3,}\b', topic.lower())
            keywords.extend(words)
        return list(set(keywords))


@dataclass
class MatchResult:
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


class SimpleMatcher:
    WEIGHTS = {
        "research_match": 40,
        "department_fit": 15,
        "level_fit": 15,
        "funding_activity": 10,
        "research_output": 10,
        "contactability": 10,
    }
    H_INDEX_RANGES = {
        "undergrad": (5, 50),
        "masters": (10, 80),
        "phd": (15, 150),
        "postdoc": (20, 200),
    }

    def __init__(self, faculty_data: List[Dict]):
        self.faculty = [FacultyProfile.from_dict(f) for f in faculty_data]
        self.keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, List[int]]:
        index = {}
        for i, fac in enumerate(self.faculty):
            for kw in fac.get_keywords():
                if kw not in index:
                    index[kw] = []
                index[kw].append(i)
        return index

    def match(self, student: StudentProfile, top_k: int = 10) -> List[MatchResult]:
        student_keywords = student.to_keywords()
        candidate_indices = set()
        for kw in student_keywords:
            if kw in self.keyword_index:
                candidate_indices.update(self.keyword_index[kw])
        if not candidate_indices:
            candidate_indices = set(range(len(self.faculty)))
        results = []
        for i in candidate_indices:
            fac = self.faculty[i]
            score, breakdown, explanation = self._score_match(student, fac, student_keywords)
            results.append(MatchResult(faculty=fac, total_score=score, breakdown=breakdown, explanation=explanation))
        results.sort(key=lambda x: x.total_score, reverse=True)
        for i, r in enumerate(results[:top_k]):
            r.rank = i + 1
        return results[:top_k]

    def _score_match(self, student: StudentProfile, faculty: FacultyProfile,
                     student_keywords: List[str]) -> Tuple[float, Dict[str, float], str]:
        breakdown = {}
        explanations = []
        faculty_keywords = faculty.get_keywords()
        overlap = set(student_keywords) & set(faculty_keywords)
        if student_keywords and faculty_keywords:
            overlap_ratio = len(overlap) / min(len(student_keywords), len(faculty_keywords))
            research_score = overlap_ratio * self.WEIGHTS["research_match"]
        else:
            research_score = 0
        breakdown["research_match"] = research_score
        if overlap:
            explanations.append(f"Research overlap: {', '.join(list(overlap)[:5])}")
        dept_score = 0
        if student.department_preference and faculty.department:
            if student.department_preference.lower() == faculty.department.lower():
                dept_score = self.WEIGHTS["department_fit"]
                explanations.append(f"Department match: {faculty.department}")
            elif student.department_preference.lower() in faculty.department.lower():
                dept_score = self.WEIGHTS["department_fit"] * 0.7
        breakdown["department_fit"] = dept_score
        level_score = self.WEIGHTS["level_fit"] * 0.8
        if student.level and student.level in self.H_INDEX_RANGES:
            min_h, max_h = self.H_INDEX_RANGES[student.level]
            if min_h <= faculty.h_index <= max_h:
                level_score = self.WEIGHTS["level_fit"]
            elif faculty.h_index < min_h:
                level_score = self.WEIGHTS["level_fit"] * 0.5
            else:
                level_score = self.WEIGHTS["level_fit"] * 0.7
        breakdown["level_fit"] = level_score
        total_grants = faculty.nsf_awards + faculty.nih_awards
        if total_grants >= 3:
            funding_score = self.WEIGHTS["funding_activity"]
            explanations.append(f"Active funding: {total_grants} grants")
        elif total_grants >= 1:
            funding_score = self.WEIGHTS["funding_activity"] * 0.7
        else:
            funding_score = self.WEIGHTS["funding_activity"] * 0.3
        breakdown["funding_activity"] = funding_score
        output_score = self.WEIGHTS["research_output"] * 0.4
        if faculty.works_count >= 100:
            output_score = self.WEIGHTS["research_output"]
        elif faculty.works_count >= 50:
            output_score = self.WEIGHTS["research_output"] * 0.8
        elif faculty.works_count >= 20:
            output_score = self.WEIGHTS["research_output"] * 0.6
        breakdown["research_output"] = output_score
        contact_score = 0
        if faculty.email:
            contact_score = self.WEIGHTS["contactability"] * 0.6
            if faculty.email_quality == "verified":
                contact_score = self.WEIGHTS["contactability"]
                explanations.append("Verified email available")
        else:
            explanations.append("No email available")
        breakdown["contactability"] = contact_score
        total = sum(breakdown.values())
        explanation = f"h-index: {faculty.h_index}, " + ("; ".join(explanations) if explanations else "")
        return total, breakdown, explanation

    def quick_search(self, keywords: List[str], top_k: int = 20) -> List[FacultyProfile]:
        keywords = [k.lower().strip() for k in keywords if len(k) > 2]
        scores = Counter()
        for kw in keywords:
            if kw in self.keyword_index:
                for idx in self.keyword_index[kw]:
                    scores[idx] += 1
        top_indices = [idx for idx, _ in scores.most_common(top_k)]
        return [self.faculty[i] for i in top_indices]


class MatchingService:
    """Service class for Flask app. Fast 5-question matching."""

    def __init__(self, faculty_json_path: str):
        with open(faculty_json_path, 'r') as f:
            data = json.load(f)
        faculty_list = data.get("faculty", data)
        self.matcher = SimpleMatcher(faculty_list)
        self.metadata = data.get("metadata", {})

    def match_student(self,
                      research_field: str = "",
                      research_topics: str = "",
                      academic_level: str = "",
                      work_style: str = "",
                      needs_funding: bool = False,
                      top_k: int = 20,
                      research_interests: List[str] = None,
                      department: str = "",
                      level: str = "",
                      techniques: List[str] = None,
                      looking_for: str = "",
                      ) -> List[Dict]:
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
        score = 0.0
        breakdown = {}
        reasons = []
        fac_keywords = set((fac.research_keywords or []) + [t.lower() for t in (fac.research_topics or [])])
        fac_text = " ".join(fac.research_topics or []).lower()
        matches = sum(1 for kw in keywords if kw in fac_keywords or kw in fac_text)
        matched_terms = [kw for kw in keywords if kw in fac_keywords or kw in fac_text]
        keyword_score = min(50.0, (matches / max(len(keywords), 1)) * 50.0) if keywords else 25.0
        breakdown["research"] = round(keyword_score, 1)
        score += keyword_score
        if matched_terms:
            reasons.append(f"Matches: {', '.join(matched_terms[:3])}")
        h_ranges = {"undergrad": (5, 60), "masters": (10, 100), "phd": (15, 150), "postdoc": (20, 200)}
        if level in h_ranges:
            min_h, max_h = h_ranges[level]
            level_score = 20.0 if min_h <= fac.h_index <= max_h else (10.0 if fac.h_index < min_h else 15.0)
        else:
            level_score = 15.0
        breakdown["level_fit"] = level_score
        score += level_score
        has_funding = (fac.nsf_awards + fac.nih_awards) > 0
        funding_score = 15.0 if (needs_funding and has_funding) else (0.0 if (needs_funding and not has_funding) else 10.0)
        if has_funding:
            reasons.append(f"{fac.nsf_awards + fac.nih_awards} active grants")
        breakdown["funding"] = funding_score
        score += funding_score
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
        results = self.matcher.quick_search(keywords, top_k)
        return [{"name": f.name, "email": f.email, "email_quality": f.email_quality, "website": f.website,
                 "department": f.department, "h_index": f.h_index, "research_topics": f.research_topics[:5]}
                for f in results]

    def get_faculty_count(self) -> int:
        return len(self.matcher.faculty)

    def get_departments(self) -> List[str]:
        depts = {f.department for f in self.matcher.faculty if f.department}
        return sorted(depts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test faculty matching (5-question MVP)")
    parser.add_argument("--faculty-json", required=True)
    parser.add_argument("--research-field", default="")
    parser.add_argument("--research-topics", default="")
    parser.add_argument("--level", default="phd")
    parser.add_argument("--work-style", default="both")
    parser.add_argument("--needs-funding", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    service = MatchingService(args.faculty_json)
    results = service.match_student(research_field=args.research_field, research_topics=args.research_topics,
                                    academic_level=args.level, work_style=args.work_style,
                                    needs_funding=args.needs_funding, top_k=args.top_k)
    for r in results:
        print(f"#{r['rank']} {r['name']} (Score: {r['total_score']}) - {r['explanation']}")


if __name__ == "__main__":
    main()
