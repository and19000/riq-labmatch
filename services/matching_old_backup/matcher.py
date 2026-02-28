"""
Main sophisticated matcher with multi-stage scoring.
"""

import json
import os
import time
import logging
from typing import List, Dict, Any, Optional

from .models import FacultyProfile
from .extractor import SmartStudentExtractor
from .scorer import MultiStageScorer
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Try imports
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class SophisticatedMatcher:
    """
    Sophisticated faculty-student matcher with multi-stage scoring.
    
    Usage:
        matcher = SophisticatedMatcher(faculty_data_path="harvard.json")
        results = matcher.match(resume_text, user_interests=["ML", "NLP"])
    """
    
    def __init__(
        self,
        faculty_data_path: Optional[str] = None,
        faculty_data: Optional[List[Dict]] = None,
        openai_api_key: Optional[str] = None,
        precompute_embeddings: bool = True,
    ):
        # Initialize services
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.openai_client = openai.OpenAI(api_key=api_key) if HAS_OPENAI and api_key else None
        self.embedding_service = EmbeddingService(self.openai_client)
        
        # Initialize components
        self.student_extractor = SmartStudentExtractor(self.openai_client)
        self.scorer = MultiStageScorer(self.embedding_service, self.openai_client)
        
        # Load faculty
        self.faculty_profiles: List[FacultyProfile] = []
        if faculty_data_path:
            with open(faculty_data_path) as f:
                data = json.load(f)
                faculty_list = data.get("faculty", data) if isinstance(data, dict) else data
                self.faculty_profiles = [FacultyProfile.from_dict(f) for f in faculty_list]
        elif faculty_data:
            self.faculty_profiles = [FacultyProfile.from_dict(f) for f in faculty_data]
        
        logger.info(f"Loaded {len(self.faculty_profiles)} faculty profiles")
        
        # Precompute embeddings
        if precompute_embeddings and self.openai_client:
            self._precompute_embeddings()
    
    def _precompute_embeddings(self):
        """Precompute all faculty embeddings."""
        logger.info("Precomputing faculty embeddings...")
        start = time.time()
        
        for faculty in self.faculty_profiles:
            text = f"Research: {', '.join(faculty.topics[:10])}. Keywords: {', '.join(list(faculty.keywords)[:10])}"
            faculty.embedding = self.embedding_service.get_embedding(text)
        
        elapsed = time.time() - start
        cached = sum(1 for f in self.faculty_profiles if f.embedding is not None)
        logger.info(f"Embeddings ready: {cached}/{len(self.faculty_profiles)} in {elapsed:.1f}s")
    
    def match(
        self,
        resume_text: str,
        user_interests: List[str] = None,
        user_techniques: List[str] = None,
        user_preferences: Dict = None,
        top_k: int = 20,
        min_score: float = 35.0,
        include_explanations: bool = True,
    ) -> Dict:
        """
        Match student to faculty using multi-stage scoring.
        
        Args:
            resume_text: Student resume text
            user_interests: User-specified research interests
            user_techniques: User-specified techniques
            user_preferences: Additional preferences (location, duration, funding, etc.)
            top_k: Number of top matches to return
            min_score: Minimum score threshold
            include_explanations: Whether to generate LLM explanations
        
        Returns:
            Dict with matches and metadata
        """
        start_time = time.time()
        
        # Stage 0: Extract student profile
        student = self.student_extractor.extract(
            resume_text, user_interests, user_techniques, user_preferences
        )
        
        # Compute student embedding
        student_text = (
            f"Interests: {', '.join(student.research_interests[:10])}. "
            f"Skills: {', '.join(student.techniques[:10])}"
        )
        student.embedding = self.embedding_service.get_embedding(student_text)
        
        # Stage 1: Fast keyword filter (top 100)
        stage1_results = self.scorer.stage1_keyword_filter(student, self.faculty_profiles, top_k=100)
        
        # Stage 2: Embedding ranking (top 30)
        stage2_results = self.scorer.stage2_embedding_rank(student, stage1_results, top_k=30)
        
        # Stage 3: Detailed scoring
        stage3_results = self.scorer.stage3_detailed_score(student, stage2_results)
        
        # Filter by min score
        filtered_results = [r for r in stage3_results if r.total_score >= min_score]
        
        # Generate explanations for top K
        if include_explanations and self.openai_client:
            final_results = self.scorer.generate_explanations(student, filtered_results, top_k)
        else:
            final_results = filtered_results[:top_k]
        
        elapsed = time.time() - start_time
        
        return {
            "matches": [r.to_dict() for r in final_results],
            "total_faculty": len(self.faculty_profiles),
            "stage1_candidates": len(stage1_results),
            "stage2_candidates": len(stage2_results),
            "above_threshold": len(filtered_results),
            "student_profile": {
                "interests": student.research_interests[:10],
                "techniques": student.techniques[:10],
                "experience_level": student.experience_level,
                "research_domains": student.research_domains,
                "lab_type_preference": student.lab_type_preference,
            },
            "metadata": {
                "duration_ms": round(elapsed * 1000),
                "top_k": top_k,
                "min_score": min_score,
                "explanations_included": include_explanations,
            }
        }
    
    def match_fast(self, resume_text: str, top_k: int = 50) -> List[Dict]:
        """
        Fast matching using keywords only (no LLM).
        ~50ms for 600 faculty.
        """
        import re
        
        # Extract keywords
        text = resume_text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        keywords = {w for w in words if len(w) >= 3 and w not in stopwords}
        
        # Score all faculty
        scores = []
        for faculty in self.faculty_profiles:
            overlap = len(keywords & faculty.keywords)
            score = overlap * 10 + faculty.activity_score * 20
            scores.append({
                "pi_id": faculty.id,
                "name": faculty.name,
                "score": round(score, 1),
                "h_index": faculty.h_index,
                "email": faculty.email,
            })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]
