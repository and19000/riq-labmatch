"""
Exa Search API implementation.
Docs: https://docs.exa.ai
"""
from typing import List
from exa_py import Exa
from .base import BaseSearch, SearchResult


class ExaSearch(BaseSearch):
    """Exa search API wrapper."""

    def __init__(self, api_key: str, delay: float = 0.5):
        super().__init__(api_key, delay)
        self.client = Exa(api_key=api_key)

    @property
    def name(self) -> str:
        return "Exa"

    @property
    def cost_per_query(self) -> float:
        return 0.005

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        try:
            response = self.client.search(
                query=query,
                type="auto",
                num_results=num_results,
                contents={
                    "text": {"max_characters": 5000}
                }
            )

            results = []
            for item in response.results:
                results.append(SearchResult(
                    url=item.url,
                    title=item.title or "",
                    snippet=item.text[:500] if item.text else "",
                    content=item.text if item.text else None,
                    score=item.score if hasattr(item, "score") else 0.0
                ))

            return results

        except Exception as e:
            print(f"  [Exa] API error: {e}")
            return []

    def search_professor(self, name: str, affiliation: str, department: str = "") -> List[SearchResult]:
        """Exa-optimized: natural language queries."""
        results = []

        query1 = f"{name} {affiliation} professor profile"
        results.extend(self._safe_search(query1, 5))

        query2 = f"{name} {affiliation} faculty"
        if department:
            query2 = f"{name} {affiliation} {department} faculty"
        results.extend(self._safe_search(query2, 5))

        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        return unique[:10]
