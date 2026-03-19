import json
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class UniversityConfig:
    """Configuration for a single university's filtering heuristics."""

    name: str
    short_name: str
    primary_trusted_domains: List[str]
    secondary_trusted_domains: List[str]
    rejected_domains: List[str]
    url_to_department: Dict[str, str]
    email_inference_patterns: Dict[str, str] = field(default_factory=dict)
    phone_extraction_domains: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str) -> "UniversityConfig":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @property
    def all_trusted_domains(self) -> List[str]:
        return self.primary_trusted_domains + self.secondary_trusted_domains

