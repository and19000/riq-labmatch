"""
Multi-stage scorer for matching students to faculty.
"""

import re
import logging
from typing import List, Dict, Tuple
from .models import StudentProfile, FacultyProfile, MatchResult

logger = logging.getLogger(__name__)


class MultiStageScorer:
    """
    Three-stage scoring:
    1. Fast keyword filter → Top 100
    2. Embedding similarity → Top 30
    3. LLM reasoning → Top 20 with explanations
    """
    
    # Weights for final score (total = 100)
    WEIGHTS = {
        "keyword": 15,
        "semantic": 25,
        "domain": 15,
        "technique": 20,
        "experience": 15,
        "activity": 10,
    }
    
    def __init__(self, embedding_service=None, openai_client=None):
        self.embedding_service = embedding_service
        self.openai_client = openai_client
    
    def stage1_keyword_filter(
        self, 
        student: StudentProfile, 
        faculty_list: List[FacultyProfile], 
        top_k: int = 100
    ) -> List[Tuple[FacultyProfile, float]]:
        """Fast keyword-based filtering."""
        student_keywords = student.get_all_keywords()
        
        scores = []
        for faculty in faculty_list:
            # Keyword overlap
            overlap = len(student_keywords & faculty.keywords)
            
            # Domain match bonus
            domain_bonus = len(set(student.research_domains) & set(faculty.research_domains)) * 5
            
            # Technique match bonus
            student_techs = set(t.lower() for t in student.techniques)
            faculty_text = ' '.join(faculty.topics).lower()
            tech_match = sum(1 for t in student_techs if t in faculty_text) * 3
            
            score = overlap + domain_bonus + tech_match
            scores.append((faculty, score))
        
        # Sort and return top K
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def stage2_embedding_rank(
        self,
        student: StudentProfile,
        candidates: List[Tuple[FacultyProfile, float]],
        top_k: int = 30
    ) -> List[Tuple[FacultyProfile, float]]:
        """Rank by embedding similarity."""
        if not self.embedding_service or student.embedding is None:
            return candidates[:top_k]
        
        scored = []
        for faculty, keyword_score in candidates:
            if faculty.embedding is not None:
                similarity = self.embedding_service.cosine_similarity(
                    student.embedding, faculty.embedding
                )
                combined_score = keyword_score + (similarity * 50)
            else:
                combined_score = keyword_score
            scored.append((faculty, combined_score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def stage3_detailed_score(
        self,
        student: StudentProfile,
        candidates: List[Tuple[FacultyProfile, float]]
    ) -> List[MatchResult]:
        """Detailed scoring with all components."""
        results = []
        
        for faculty, preliminary_score in candidates:
            result = MatchResult(faculty=faculty, total_score=0)
            
            # 1. Keyword score (0-15)
            student_keywords = student.get_all_keywords()
            overlap = student_keywords & faculty.keywords
            result.keyword_score = min(len(overlap) / 10, 1.0) * self.WEIGHTS["keyword"]
            result.matched_topics = list(overlap)[:5]
            
            # 2. Semantic score (0-25)
            if self.embedding_service and student.embedding is not None and faculty.embedding is not None:
                similarity = self.embedding_service.cosine_similarity(student.embedding, faculty.embedding)
                result.semantic_score = similarity * self.WEIGHTS["semantic"]
            
            # 3. Domain score (0-15)
            domain_overlap = set(student.research_domains) & set(faculty.research_domains)
            if domain_overlap:
                result.domain_score = min(len(domain_overlap) / 2, 1.0) * self.WEIGHTS["domain"]
                result.match_reasons.append(f"Domain match: {', '.join(domain_overlap)}")
            
            # 4. Technique score (0-20)
            student_techs = set(t.lower() for t in student.techniques + student.user_techniques)
            faculty_text = ' '.join(faculty.topics + faculty.concepts).lower()
            matched_techs = [t for t in student_techs if t in faculty_text]
            if matched_techs:
                result.technique_score = min(len(matched_techs) / 3, 1.0) * self.WEIGHTS["technique"]
                result.matched_techniques = matched_techs[:5]
                result.match_reasons.append(f"Skills match: {', '.join(matched_techs[:3])}")
            
            # 5. Experience fit score (0-15)
            result.experience_score = self._score_experience_fit(student, faculty)
            
            # 6. Activity score (0-10)
            result.activity_score = faculty.activity_score * self.WEIGHTS["activity"]
            if faculty.h_index >= 50:
                result.match_reasons.append(f"Established researcher (h-index: {faculty.h_index})")
            
            # Calculate total
            result.total_score = (
                result.keyword_score + result.semantic_score + result.domain_score +
                result.technique_score + result.experience_score + result.activity_score
            )
            
            # Check for concerns (negative signals)
            result.concerns = self._check_concerns(student, faculty)
            
            # Determine quality
            if result.total_score >= 75:
                result.quality = "excellent"
            elif result.total_score >= 60:
                result.quality = "good"
            elif result.total_score >= 45:
                result.quality = "moderate"
            else:
                result.quality = "weak"
            
            # Confidence based on number of signals
            signals = len(result.matched_topics) + len(result.matched_techniques) + len(result.match_reasons)
            result.confidence = min(signals / 10, 1.0)
            
            results.append(result)
        
        # Sort by score
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results
    
    def _score_experience_fit(self, student: StudentProfile, faculty: FacultyProfile) -> float:
        """Score experience level fit."""
        max_score = self.WEIGHTS["experience"]
        level = student.experience_level
        h = faculty.h_index
        
        # Base fit score
        if level == "undergraduate":
            if h > 120:
                return max_score * 0.4  # Very senior, may not mentor undergrads
            elif h > 80:
                return max_score * 0.7
            else:
                return max_score * 1.0  # Good fit
        elif level == "masters":
            return max_score * 0.8  # Generally good fit
        elif level == "phd":
            if h >= 40:
                return max_score * 1.0  # Established enough for PhD
            else:
                return max_score * 0.6  # May be too junior
        elif level == "postdoc":
            if h >= 60:
                return max_score * 1.0
            else:
                return max_score * 0.5
        
        return max_score * 0.5
    
    def _check_concerns(self, student: StudentProfile, faculty: FacultyProfile) -> List[str]:
        """Check for potential concerns/mismatches."""
        concerns = []
        
        # Lab type mismatch
        if student.lab_type_preference != "any" and faculty.lab_type != "unknown":
            if student.lab_type_preference != faculty.lab_type:
                concerns.append(
                    f"Lab type mismatch: you prefer {student.lab_type_preference}, lab is {faculty.lab_type}"
                )
        
        # Very senior PI for undergrad
        if student.experience_level == "undergraduate" and faculty.h_index > 100:
            concerns.append("Very senior PI - may have limited time for mentoring")
        
        # No contact info
        if not faculty.email and not faculty.website:
            concerns.append("No contact information available")
        
        # Domain mismatch
        if student.research_domains and faculty.research_domains:
            if not set(student.research_domains) & set(faculty.research_domains):
                concerns.append("Different research domains")
        
        # Funding concerns
        if student.funding_required and not faculty.email:
            concerns.append("Funding availability unclear - contact professor to inquire")
        
        return concerns
    
    def generate_explanations(
        self, 
        student: StudentProfile, 
        results: List[MatchResult],
        top_k: int = 20
    ) -> List[MatchResult]:
        """Generate LLM-powered explanations for top matches."""
        if not self.openai_client:
            return results[:top_k]
        
        top_results = results[:top_k]
        
        # Batch generate explanations
        for result in top_results:
            try:
                explanation = self._generate_single_explanation(student, result)
                result.personalized_reason = explanation.get("reason", "")
                result.suggested_approach = explanation.get("approach", "")
            except Exception as e:
                logger.warning(f"Explanation generation failed: {e}")
        
        return top_results
    
    def _generate_single_explanation(self, student: StudentProfile, result: MatchResult) -> Dict:
        """Generate explanation for a single match."""
        prompt = f"""Based on this match, write a brief personalized explanation.

STUDENT INTERESTS: {', '.join(student.research_interests[:5])}
STUDENT SKILLS: {', '.join(student.techniques[:5])}
STUDENT LEVEL: {student.experience_level}

FACULTY: {result.faculty.name}
RESEARCH: {', '.join(result.faculty.topics[:5])}
H-INDEX: {result.faculty.h_index}

MATCH SCORE: {result.total_score:.0f}/100
MATCHED TOPICS: {', '.join(result.matched_topics[:3])}
CONCERNS: {', '.join(result.concerns[:2]) if result.concerns else 'None'}

Write JSON:
{{
    "reason": "2-3 sentence personalized explanation of why this is a good match",
    "approach": "1 sentence suggesting how to approach this professor"
}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Explanation generation error: {e}")
        
        return {"reason": "", "approach": ""}
