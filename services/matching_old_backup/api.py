"""
API wrapper for integrating matching service into RIQ application.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify
from .matcher import SophisticatedMatcher
from .user_preferences import UserPreferences, get_questions_json

logger = logging.getLogger(__name__)


class MatchingAPI:
    """API wrapper for matching service."""
    
    def __init__(
        self,
        faculty_data_path: Optional[str] = None,
        faculty_data: Optional[List[Dict]] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize matching API."""
        self.matcher = SophisticatedMatcher(
            faculty_data_path=faculty_data_path,
            faculty_data=faculty_data,
            openai_api_key=openai_api_key,
            precompute_embeddings=True,
        )
    
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
        """Match student to faculty."""
        return self.matcher.match(
            resume_text=resume_text,
            user_interests=user_interests,
            user_techniques=user_techniques,
            user_preferences=user_preferences,
            top_k=top_k,
            min_score=min_score,
            include_explanations=include_explanations,
        )
    
    def match_fast(self, resume_text: str, top_k: int = 50) -> List[Dict]:
        """Fast matching (keywords only)."""
        return self.matcher.match_fast(resume_text, top_k)
    
    def get_questions(self) -> List[Dict]:
        """Get user preference questions."""
        return get_questions_json()


def create_flask_app(
    faculty_data_path: Optional[str] = None,
    faculty_data: Optional[List[Dict]] = None,
    openai_api_key: Optional[str] = None,
) -> Flask:
    """Create Flask app with matching endpoints."""
    app = Flask(__name__)
    matching_api = MatchingAPI(
        faculty_data_path=faculty_data_path,
        faculty_data=faculty_data,
        openai_api_key=openai_api_key,
    )
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "service": "matching_v3"})
    
    @app.route('/questions', methods=['GET'])
    def questions():
        """Get user preference questions."""
        return jsonify({"questions": matching_api.get_questions()})
    
    @app.route('/match', methods=['POST'])
    def match():
        """Match endpoint."""
        try:
            data = request.get_json()
            
            resume_text = data.get("resume_text", "")
            if not resume_text:
                return jsonify({"error": "resume_text is required"}), 400
            
            user_interests = data.get("user_interests", [])
            user_techniques = data.get("user_techniques", [])
            user_preferences = data.get("user_preferences", {})
            top_k = data.get("top_k", 20)
            min_score = data.get("min_score", 35.0)
            include_explanations = data.get("include_explanations", True)
            
            results = matching_api.match(
                resume_text=resume_text,
                user_interests=user_interests,
                user_techniques=user_techniques,
                user_preferences=user_preferences,
                top_k=top_k,
                min_score=min_score,
                include_explanations=include_explanations,
            )
            
            return jsonify(results)
        except Exception as e:
            logger.error(f"Match error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/match/fast', methods=['POST'])
    def match_fast():
        """Fast match endpoint (keywords only)."""
        try:
            data = request.get_json()
            resume_text = data.get("resume_text", "")
            top_k = data.get("top_k", 50)
            
            if not resume_text:
                return jsonify({"error": "resume_text is required"}), 400
            
            results = matching_api.match_fast(resume_text, top_k)
            return jsonify({"matches": results})
        except Exception as e:
            logger.error(f"Fast match error: {e}")
            return jsonify({"error": str(e)}), 500
    
    return app


# For integration with existing RIQ app
def register_routes(app: Flask, faculty_data_path: Optional[str] = None):
    """Register matching routes to existing Flask app."""
    matching_api = MatchingAPI(faculty_data_path=faculty_data_path)
    
    @app.route('/api/matching/v3/questions', methods=['GET'])
    def questions():
        """Get user preference questions."""
        return jsonify({"questions": matching_api.get_questions()})
    
    @app.route('/api/matching/v3/match', methods=['POST'])
    def match():
        """Match endpoint."""
        try:
            data = request.get_json()
            
            resume_text = data.get("resume_text", "")
            if not resume_text:
                return jsonify({"error": "resume_text is required"}), 400
            
            user_interests = data.get("user_interests", [])
            user_techniques = data.get("user_techniques", [])
            user_preferences = data.get("user_preferences", {})
            top_k = data.get("top_k", 20)
            min_score = data.get("min_score", 35.0)
            include_explanations = data.get("include_explanations", True)
            
            results = matching_api.match(
                resume_text=resume_text,
                user_interests=user_interests,
                user_techniques=user_techniques,
                user_preferences=user_preferences,
                top_k=top_k,
                min_score=min_score,
                include_explanations=include_explanations,
            )
            
            return jsonify(results)
        except Exception as e:
            logger.error(f"Match error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/matching/v3/match/fast', methods=['POST'])
    def match_fast():
        """Fast match endpoint."""
        try:
            data = request.get_json()
            resume_text = data.get("resume_text", "")
            top_k = data.get("top_k", 50)
            
            if not resume_text:
                return jsonify({"error": "resume_text is required"}), 400
            
            results = matching_api.match_fast(resume_text, top_k)
            return jsonify({"matches": results})
        except Exception as e:
            logger.error(f"Fast match error: {e}")
            return jsonify({"error": str(e)}), 500
