"""
Data models for matching service.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

# Research taxonomy for domain classification
RESEARCH_TAXONOMY = {
    "life_sciences": {
        "keywords": ["biology", "biochemistry", "genetics", "genomics", "cell", "molecular", 
                    "neuroscience", "immunology", "microbiology", "ecology", "evolution"],
        "subtopics": {
            "molecular_biology": ["dna", "rna", "protein", "gene expression", "crispr", "sequencing"],
            "neuroscience": ["brain", "neural", "cognitive", "behavior", "synapse", "neuron"],
            "immunology": ["immune", "antibody", "t-cell", "vaccine", "inflammation"],
            "cancer": ["oncology", "tumor", "carcinoma", "metastasis", "chemotherapy"],
        }
    },
    "physical_sciences": {
        "keywords": ["physics", "chemistry", "materials", "quantum", "optics", "thermodynamics"],
        "subtopics": {
            "chemistry": ["organic", "inorganic", "analytical", "physical chemistry", "synthesis"],
            "physics": ["quantum", "particle", "condensed matter", "astrophysics", "mechanics"],
            "materials": ["nanomaterials", "polymers", "semiconductors", "ceramics"],
        }
    },
    "engineering": {
        "keywords": ["engineering", "robotics", "systems", "design", "optimization", "control"],
        "subtopics": {
            "mechanical": ["robotics", "mechatronics", "fluid dynamics", "thermodynamics"],
            "electrical": ["circuits", "signal processing", "power systems", "embedded"],
            "biomedical": ["medical devices", "imaging", "prosthetics", "biomechanics"],
        }
    },
    "computer_science": {
        "keywords": ["computer", "algorithm", "software", "programming", "data", "computing"],
        "subtopics": {
            "machine_learning": ["deep learning", "neural network", "ai", "nlp", "computer vision"],
            "systems": ["distributed", "database", "operating system", "networking"],
            "theory": ["algorithms", "complexity", "cryptography", "formal methods"],
        }
    },
    "social_sciences": {
        "keywords": ["psychology", "economics", "sociology", "political", "anthropology"],
        "subtopics": {
            "psychology": ["cognitive", "developmental", "clinical", "social psychology"],
            "economics": ["microeconomics", "macroeconomics", "econometrics", "behavioral"],
        }
    },
}

# Technique categories for lab type detection
TECHNIQUE_CATEGORIES = {
    "wet_lab": ["pcr", "western blot", "cell culture", "microscopy", "chromatography", 
                "electrophoresis", "cloning", "transfection", "immunostaining"],
    "dry_lab": ["python", "r", "matlab", "machine learning", "data analysis", 
                "statistical analysis", "bioinformatics", "computational modeling"],
    "mixed": ["crispr", "sequencing", "proteomics", "metabolomics", "imaging"],
}


@dataclass
class StudentProfile:
    """Rich student profile."""
    raw_text: str = ""
    research_interests: List[str] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)
    experience_level: str = "undergraduate"
    research_domains: List[str] = field(default_factory=list)  # From taxonomy
    lab_type_preference: str = "any"  # wet, dry, mixed, any
    keywords: Set[str] = field(default_factory=set)
    embedding: Optional[Any] = None
    
    # User-provided preferences
    user_interests: List[str] = field(default_factory=list)
    user_techniques: List[str] = field(default_factory=list)
    
    # Additional preferences
    preferred_location: Optional[str] = None
    preferred_duration: Optional[str] = None  # e.g., "summer", "semester", "year"
    funding_required: bool = False
    visa_status: Optional[str] = None
    
    def get_all_keywords(self) -> Set[str]:
        """Get all keywords for matching."""
        all_kw = set(self.keywords)
        all_kw.update(k.lower() for k in self.research_interests)
        all_kw.update(k.lower() for k in self.user_interests)
        return all_kw


@dataclass
class FacultyProfile:
    """Rich faculty profile."""
    id: str
    name: str
    institution: str
    h_index: int = 0
    works_count: int = 0
    cited_by_count: int = 0
    topics: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    email: Optional[str] = None
    website: Optional[str] = None
    embedding: Optional[Any] = None
    
    # Derived attributes
    research_domains: List[str] = field(default_factory=list)
    lab_type: str = "unknown"  # wet, dry, mixed
    activity_score: float = 0.0  # 0-1 based on h-index and publications
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FacultyProfile':
        """Create FacultyProfile from faculty data dictionary.
        Supports both pipeline format (nested) and website format (flat).
        """
        # Check if this is pipeline format (nested) or website format (flat)
        research = data.get("research", {})
        
        # Pipeline format: nested structure with research.topics, research.keywords
        if research and isinstance(research, dict) and ("topics" in research or "keywords" in research):
            topics = [t.get("name", "") if isinstance(t, dict) else t for t in research.get("topics", [])]
            concepts = [c.get("name", "") if isinstance(c, dict) else c for c in research.get("concepts", [])]
            keywords = set(k.lower() for k in research.get("keywords", []))
            keywords.update(t.lower() for t in topics if t)
            fields = research.get("fields", [])
            
            # Get ID from openalex_id (pipeline format)
            faculty_id = data.get("openalex_id", "")
            if faculty_id and "/" in faculty_id:
                faculty_id = faculty_id.split("/")[-1]
            # Fallback to id field if openalex_id not available
            if not faculty_id:
                faculty_id = data.get("id", "")
        else:
            # Website format: flat structure with research_areas, lab_techniques
            research_areas = data.get("research_areas", "")
            lab_techniques = data.get("lab_techniques", "")
            
            # Extract topics from research_areas (semicolon or comma separated)
            topics = []
            if research_areas:
                topics = [t.strip() for t in research_areas.replace(";", ",").split(",") if t.strip()]
            
            # Extract concepts/keywords from lab_techniques
            concepts = []
            keywords = set()
            if lab_techniques:
                concepts = [t.strip() for t in lab_techniques.replace(";", ",").split(",") if t.strip()]
                keywords.update(c.lower() for c in concepts)
            
            keywords.update(t.lower() for t in topics if t)
            fields = []
            
            # Get ID from id field (website format uses custom IDs like "harvard-A5051537916")
            # Keep the full ID for matching with website format
            faculty_id = data.get("id", "")
        
        # Handle email (can be dict, string, or null)
        email_value = None
        email_data = data.get("email")
        if isinstance(email_data, dict):
            email_value = email_data.get("value")
        elif isinstance(email_data, str) and email_data:
            email_value = email_data
        
        # Handle website (can be dict, string, or null)
        website_value = None
        website_data = data.get("website")
        if isinstance(website_data, dict):
            website_value = website_data.get("value")
        elif isinstance(website_data, str) and website_data:
            website_value = website_data
        
        # Handle h_index (can be string or int)
        h_index = data.get("h_index", 0)
        if isinstance(h_index, str):
            try:
                h_index = int(h_index)
            except (ValueError, TypeError):
                h_index = 0
        
        profile = cls(
            id=faculty_id or data.get("id", ""),
            name=data.get("name", ""),
            institution=data.get("institution") or data.get("school", ""),
            h_index=h_index,
            works_count=data.get("works_count", 0),
            cited_by_count=data.get("cited_by_count", 0),
            topics=topics,
            concepts=concepts,
            fields=fields,
            keywords=keywords,
            email=email_value,
            website=website_value,
        )
        
        # Compute derived attributes
        profile._compute_derived()
        return profile
    
    def _compute_derived(self):
        """Compute derived attributes."""
        # Research domains
        all_text = ' '.join(self.topics + self.concepts).lower()
        for domain, info in RESEARCH_TAXONOMY.items():
            if any(kw in all_text for kw in info["keywords"]):
                self.research_domains.append(domain)
        
        # Lab type
        wet_count = sum(1 for t in TECHNIQUE_CATEGORIES["wet_lab"] if t in all_text)
        dry_count = sum(1 for t in TECHNIQUE_CATEGORIES["dry_lab"] if t in all_text)
        if wet_count > dry_count * 2:
            self.lab_type = "wet"
        elif dry_count > wet_count * 2:
            self.lab_type = "dry"
        elif wet_count > 0 or dry_count > 0:
            self.lab_type = "mixed"
        
        # Activity score (normalized 0-1)
        h_score = min(self.h_index / 100, 1.0)  # Cap at h=100
        pub_score = min(self.works_count / 500, 1.0)  # Cap at 500 pubs
        self.activity_score = (h_score * 0.7 + pub_score * 0.3)


@dataclass
class MatchResult:
    """Detailed match result."""
    faculty: FacultyProfile
    total_score: float
    
    # Component scores (0-100 scale each, weighted in total)
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    domain_score: float = 0.0
    technique_score: float = 0.0
    experience_score: float = 0.0
    activity_score: float = 0.0
    
    # Explanations
    match_reasons: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    matched_topics: List[str] = field(default_factory=list)
    matched_techniques: List[str] = field(default_factory=list)
    
    # Quality
    quality: str = "weak"  # excellent, good, moderate, weak
    confidence: float = 0.0  # 0-1
    
    # LLM-generated
    personalized_reason: str = ""
    suggested_approach: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pi_id": self.faculty.id,
            "name": self.faculty.name,
            "institution": self.faculty.institution,
            "h_index": self.faculty.h_index,
            "email": self.faculty.email,
            "website": self.faculty.website,
            "total_score": round(self.total_score, 1),
            "quality": self.quality,
            "confidence": round(self.confidence, 2),
            "breakdown": {
                "keyword": round(self.keyword_score, 1),
                "semantic": round(self.semantic_score, 1),
                "domain": round(self.domain_score, 1),
                "technique": round(self.technique_score, 1),
                "experience": round(self.experience_score, 1),
                "activity": round(self.activity_score, 1),
            },
            "match_reasons": self.match_reasons,
            "concerns": self.concerns,
            "matched_topics": self.matched_topics,
            "matched_techniques": self.matched_techniques,
            "personalized_reason": self.personalized_reason,
            "suggested_approach": self.suggested_approach,
        }
