"""
Base class for all search APIs.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import time


@dataclass
class SearchResult:
    """Standardized search result across all APIs."""
    url: str
    title: str
    snippet: str
    content: Optional[str] = None
    extracted_email: Optional[str] = None
    score: float = 0.0

    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "content": self.content[:500] if self.content else None,
            "extracted_email": self.extracted_email,
            "score": self.score
        }


class BaseSearch(ABC):
    """Base class for search API implementations."""

    def __init__(self, api_key: str, delay: float = 0.5):
        self.api_key = api_key
        self.delay = delay
        self.query_count = 0
        self.total_cost = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        """API name for reporting."""
        pass

    @property
    @abstractmethod
    def cost_per_query(self) -> float:
        """Estimated cost per query in USD."""
        pass

    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Execute search and return standardized results."""
        pass

    def search_professor(self, name: str, affiliation: str, department: str = "") -> List[SearchResult]:
        """
        Search for a professor's website/contact info.
        Tries multiple query strategies.
        """
        results = []
        queries_tried = []

        # Strategy 1: Name + affiliation + site restriction (if .edu)
        domain = self._get_institution_domain(affiliation)
        if domain:
            query1 = f'"{name}" site:{domain}'
            queries_tried.append(query1)
            results.extend(self._safe_search(query1, 5))

        # Strategy 2: Name + affiliation (no site restriction)
        query2 = f'"{name}" {affiliation}'
        if department:
            query2 += f' {department}'
        queries_tried.append(query2)
        results.extend(self._safe_search(query2, 5))

        # Strategy 3: Name + "professor" + affiliation
        query3 = f'"{name}" professor {affiliation}'
        queries_tried.append(query3)
        results.extend(self._safe_search(query3, 5))

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        return unique_results[:10]  # Return top 10 unique results

    def _safe_search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Execute search with error handling and rate limiting."""
        time.sleep(self.delay)
        self.query_count += 1
        self.total_cost += self.cost_per_query

        try:
            return self.search(query, num_results)
        except Exception as e:
            print(f"  [{self.name}] Error searching '{query[:50]}...': {e}")
            return []

    def _get_institution_domain(self, affiliation: str) -> Optional[str]:
        """Map institution name to domain."""
        domain_map = {
            "harvard": "harvard.edu",
            "mit": "mit.edu",
            "stanford": "stanford.edu",
            "berkeley": "berkeley.edu",
            "yale": "yale.edu",
            "princeton": "princeton.edu",
            "columbia": "columbia.edu",
            "cornell": "cornell.edu",
            "upenn": "upenn.edu",
            "penn": "upenn.edu",
            "chicago": "uchicago.edu",
            "caltech": "caltech.edu",
            "ucla": "ucla.edu",
            "usc": "usc.edu",
            "nyu": "nyu.edu",
            "duke": "duke.edu",
            "northwestern": "northwestern.edu",
            "johns hopkins": "jhu.edu",
            "carnegie mellon": "cmu.edu",
            "cmu": "cmu.edu",
            "brown": "brown.edu",
            "dartmouth": "dartmouth.edu",
        }

        affiliation_lower = affiliation.lower()
        for key, domain in domain_map.items():
            if key in affiliation_lower:
                return domain

        return None

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "api": self.name,
            "queries": self.query_count,
            "estimated_cost": round(self.total_cost, 4)
        }
