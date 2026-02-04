"""Fast faculty matching (no LLM).

v1: Simple keyword-based matching (MatchingService)
v2: 7-parameter semantic-lite matching with MMR reranking (MatchingServiceV2)
"""
from .simple_matching import MatchingService
from .matching_v2 import MatchingServiceV2

__all__ = ["MatchingService", "MatchingServiceV2"]
