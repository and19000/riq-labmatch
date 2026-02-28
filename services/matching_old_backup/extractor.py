"""
Student profile extractor with LLM-powered extraction.
"""

import json
import re
import logging
from typing import List, Dict, Optional, Set
from .models import StudentProfile, RESEARCH_TAXONOMY, TECHNIQUE_CATEGORIES

logger = logging.getLogger(__name__)


class SmartStudentExtractor:
    """LLM-powered student profile extraction."""
    
    EXTRACTION_PROMPT = """Analyze this student resume and extract structured information.

RESUME:
{resume_text}

USER-PROVIDED INTERESTS: {user_interests}
USER-PROVIDED TECHNIQUES: {user_techniques}
USER-PROVIDED PREFERENCES: {user_preferences}

Extract the following as JSON:
{{
    "research_interests": ["list of specific research interests/topics"],
    "techniques": ["list of technical skills and lab techniques"],
    "experience_level": "undergraduate|masters|phd|postdoc",
    "research_domains": ["life_sciences|physical_sciences|engineering|computer_science|social_sciences"],
    "lab_type_preference": "wet|dry|mixed|any",
    "key_projects": ["brief descriptions of 1-3 main research projects"],
    "strengths": ["2-3 key strengths relevant to research"],
    "looking_for": "brief description of what kind of research opportunity they want"
}}

Be specific and accurate. Only include information clearly supported by the resume."""

    def __init__(self, openai_client=None):
        self.client = openai_client
    
    def extract(
        self, 
        resume_text: str, 
        user_interests: List[str] = None, 
        user_techniques: List[str] = None,
        user_preferences: Dict = None
    ) -> StudentProfile:
        """Extract student profile using LLM."""
        
        profile = StudentProfile(
            raw_text=resume_text,
            user_interests=user_interests or [],
            user_techniques=user_techniques or [],
        )
        
        # Extract keywords (fast, no LLM)
        profile.keywords = self._extract_keywords(resume_text)
        
        # Add user-provided data
        profile.research_interests.extend(user_interests or [])
        profile.techniques.extend(user_techniques or [])
        
        # Add user preferences
        if user_preferences:
            profile.preferred_location = user_preferences.get("location")
            profile.preferred_duration = user_preferences.get("duration")
            profile.funding_required = user_preferences.get("funding_required", False)
            profile.visa_status = user_preferences.get("visa_status")
        
        # LLM extraction if available
        if self.client:
            try:
                llm_data = self._llm_extract(resume_text, user_interests, user_techniques, user_preferences)
                if llm_data:
                    profile.research_interests = llm_data.get("research_interests", profile.research_interests)
                    profile.techniques = llm_data.get("techniques", profile.techniques)
                    profile.experience_level = llm_data.get("experience_level", "undergraduate")
                    profile.research_domains = llm_data.get("research_domains", [])
                    profile.lab_type_preference = llm_data.get("lab_type_preference", "any")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
        else:
            # Fallback: rule-based extraction
            profile.experience_level = self._detect_level(resume_text)
            profile.research_domains = self._detect_domains(resume_text)
            profile.lab_type_preference = self._detect_lab_type(resume_text)
        
        return profile
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'i', 'my', 'me', 'we', 'our', 'you'
        }
        return {w for w in words if len(w) >= 3 and w not in stopwords}
    
    def _llm_extract(
        self, 
        resume_text: str, 
        user_interests: List[str], 
        user_techniques: List[str],
        user_preferences: Dict = None
    ) -> Optional[Dict]:
        """Use LLM to extract structured profile."""
        preferences_str = json.dumps(user_preferences or {})
        prompt = self.EXTRACTION_PROMPT.format(
            resume_text=resume_text[:4000],
            user_interests=", ".join(user_interests or ["none provided"]),
            user_techniques=", ".join(user_techniques or ["none provided"]),
            user_preferences=preferences_str,
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            )
            
            content = response.choices[0].message.content
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
        
        return None
    
    def _detect_level(self, text: str) -> str:
        """Detect experience level from text."""
        text_lower = text.lower()
        if any(x in text_lower for x in ['postdoc', 'post-doctoral', 'research fellow']):
            return 'postdoc'
        if any(x in text_lower for x in ['phd', 'doctoral', 'dissertation']):
            return 'phd'
        if any(x in text_lower for x in ['master', 'ms ', 'ma ', 'mba']):
            return 'masters'
        return 'undergraduate'
    
    def _detect_domains(self, text: str) -> List[str]:
        """Detect research domains from text."""
        text_lower = text.lower()
        domains = []
        for domain, info in RESEARCH_TAXONOMY.items():
            if any(kw in text_lower for kw in info["keywords"]):
                domains.append(domain)
        return domains
    
    def _detect_lab_type(self, text: str) -> str:
        """Detect preferred lab type."""
        text_lower = text.lower()
        wet = sum(1 for t in TECHNIQUE_CATEGORIES["wet_lab"] if t in text_lower)
        dry = sum(1 for t in TECHNIQUE_CATEGORIES["dry_lab"] if t in text_lower)
        if wet > dry * 2:
            return "wet"
        if dry > wet * 2:
            return "dry"
        if wet > 0 or dry > 0:
            return "mixed"
        return "any"
