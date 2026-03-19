"""
Expose search API wrappers.

Note: Exa depends on an optional third-party library (`exa_py`).
We make Exa import resilient so Tavily-only runs can work even if Exa
client deps aren't installed in the current environment.
"""

from .tavily_search import TavilySearch
from .brave_search import BraveSearch

try:
    from .exa_search import ExaSearch  # type: ignore
except ModuleNotFoundError:
    ExaSearch = None  # Exa client is unavailable in this environment

__all__ = ["TavilySearch", "BraveSearch", "ExaSearch"]
