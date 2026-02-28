"""
User preferences and questions module for collecting student preferences.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class UserPreferences:
    """User preferences for matching."""
    # Research interests
    research_interests: List[str] = field(default_factory=list)
    
    # Technical skills
    techniques: List[str] = field(default_factory=list)
    
    # Experience level
    experience_level: Optional[str] = None  # undergraduate, masters, phd, postdoc
    
    # Lab preferences
    lab_type_preference: Optional[str] = None  # wet, dry, mixed, any
    
    # Location and timing
    preferred_location: Optional[str] = None
    preferred_duration: Optional[str] = None  # summer, semester, year, flexible
    
    # Funding and visa
    funding_required: bool = False
    visa_status: Optional[str] = None
    
    # Additional preferences
    preferred_institution: Optional[str] = None
    min_h_index: Optional[int] = None
    max_h_index: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "research_interests": self.research_interests,
            "techniques": self.techniques,
            "experience_level": self.experience_level,
            "lab_type_preference": self.lab_type_preference,
            "preferred_location": self.preferred_location,
            "preferred_duration": self.preferred_duration,
            "funding_required": self.funding_required,
            "visa_status": self.visa_status,
            "preferred_institution": self.preferred_institution,
            "min_h_index": self.min_h_index,
            "max_h_index": self.max_h_index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreferences':
        """Create from dictionary."""
        return cls(
            research_interests=data.get("research_interests", []),
            techniques=data.get("techniques", []),
            experience_level=data.get("experience_level"),
            lab_type_preference=data.get("lab_type_preference"),
            preferred_location=data.get("preferred_location"),
            preferred_duration=data.get("preferred_duration"),
            funding_required=data.get("funding_required", False),
            visa_status=data.get("visa_status"),
            preferred_institution=data.get("preferred_institution"),
            min_h_index=data.get("min_h_index"),
            max_h_index=data.get("max_h_index"),
        )


# Questions to ask users for better matching
USER_QUESTIONS = [
    {
        "id": "research_interests",
        "question": "What are your main research interests? (e.g., machine learning, neuroscience, materials science)",
        "type": "multi_select",
        "required": True,
        "help_text": "List 2-5 research areas you're most interested in"
    },
    {
        "id": "techniques",
        "question": "What technical skills or lab techniques do you have experience with?",
        "type": "multi_select",
        "required": False,
        "help_text": "Examples: Python, PCR, microscopy, data analysis, etc."
    },
    {
        "id": "experience_level",
        "question": "What is your current academic level?",
        "type": "single_select",
        "required": True,
        "options": ["undergraduate", "masters", "phd", "postdoc"],
        "help_text": "Select your current level"
    },
    {
        "id": "lab_type_preference",
        "question": "What type of lab environment do you prefer?",
        "type": "single_select",
        "required": False,
        "options": ["wet", "dry", "mixed", "any"],
        "help_text": "Wet lab = experimental/bench work, Dry lab = computational, Mixed = both"
    },
    {
        "id": "preferred_location",
        "question": "Do you have a preferred location or institution?",
        "type": "text",
        "required": False,
        "help_text": "Leave blank if location doesn't matter"
    },
    {
        "id": "preferred_duration",
        "question": "What duration are you looking for?",
        "type": "single_select",
        "required": False,
        "options": ["summer", "semester", "year", "flexible"],
        "help_text": "How long do you want the research opportunity to be?"
    },
    {
        "id": "funding_required",
        "question": "Do you require funding/stipend?",
        "type": "boolean",
        "required": False,
        "help_text": "Check if you need financial support"
    },
    {
        "id": "visa_status",
        "question": "What is your visa status?",
        "type": "single_select",
        "required": False,
        "options": ["citizen", "permanent_resident", "student_visa", "work_visa", "need_sponsorship"],
        "help_text": "Important for international opportunities"
    },
    {
        "id": "h_index_preference",
        "question": "Do you have preferences for professor's experience level?",
        "type": "range",
        "required": False,
        "help_text": "Some students prefer established professors (high h-index) or newer professors (lower h-index)"
    },
]


def collect_user_preferences_interactive() -> UserPreferences:
    """Interactive function to collect user preferences."""
    prefs = UserPreferences()
    
    print("=" * 60)
    print("RIQ LabMatch - User Preferences")
    print("=" * 60)
    print()
    
    # Research interests
    print("1. Research Interests (required)")
    print("   What are your main research interests?")
    interests_input = input("   Enter interests (comma-separated): ").strip()
    if interests_input:
        prefs.research_interests = [i.strip() for i in interests_input.split(",")]
    
    # Techniques
    print("\n2. Technical Skills (optional)")
    print("   What technical skills or lab techniques do you have?")
    techniques_input = input("   Enter skills (comma-separated): ").strip()
    if techniques_input:
        prefs.techniques = [t.strip() for t in techniques_input.split(",")]
    
    # Experience level
    print("\n3. Academic Level (required)")
    print("   Options: undergraduate, masters, phd, postdoc")
    level = input("   Your level: ").strip().lower()
    if level in ["undergraduate", "masters", "phd", "postdoc"]:
        prefs.experience_level = level
    
    # Lab type
    print("\n4. Lab Type Preference (optional)")
    print("   Options: wet, dry, mixed, any")
    lab_type = input("   Preference: ").strip().lower()
    if lab_type in ["wet", "dry", "mixed", "any"]:
        prefs.lab_type_preference = lab_type
    
    # Duration
    print("\n5. Duration Preference (optional)")
    print("   Options: summer, semester, year, flexible")
    duration = input("   Preference: ").strip().lower()
    if duration in ["summer", "semester", "year", "flexible"]:
        prefs.preferred_duration = duration
    
    # Funding
    print("\n6. Funding Required (optional)")
    funding = input("   Do you require funding? (y/n): ").strip().lower()
    prefs.funding_required = funding == "y"
    
    print("\n" + "=" * 60)
    print("Preferences collected!")
    print("=" * 60)
    
    return prefs


def get_questions_json() -> List[Dict]:
    """Get questions in JSON format for API/UI."""
    return USER_QUESTIONS
