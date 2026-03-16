"""
Tavily Search API implementation.
Docs: https://docs.tavily.com
"""
from typing import List
from tavily import TavilyClient
from .base import BaseSearch, SearchResult


class TavilySearch(BaseSearch):
    """Tavily search API wrapper."""

    def __init__(self, api_key: str, delay: float = 0.5):
        super().__init__(api_key, delay)
        self.client = TavilyClient(api_key=api_key)

    @property
    def name(self) -> str:
        return "Tavily"

    @property
    def cost_per_query(self) -> float:
        return 0.01

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        try:
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=num_results,
                include_answer=False
            )

            # Tavily returns dict with "results" key
            if isinstance(response, dict):
                items = response.get("results", [])
            else:
                items = getattr(response, "results", [])

            results = []
            for item in items:
                if isinstance(item, dict):
                    url = item.get("url", "")
                    title = item.get("title", "")
                    content = item.get("content", "")
                else:
                    url = getattr(item, "url", "")
                    title = getattr(item, "title", "")
                    content = getattr(item, "content", "")

                results.append(SearchResult(
                    url=url,
                    title=title or "",
                    snippet=(content or "")[:500],
                    content=content,
                    score=item.get("score", 0.0) if isinstance(item, dict) else getattr(item, "score", 0.0)
                ))

            return results

        except Exception as e:
            print(f"  [Tavily] API error: {e}")
            return []

    def search_professor(self, name: str, affiliation: str, department: str = "") -> List[SearchResult]:
        """Tavily-optimized natural queries."""
        results = []

        query1 = f"{name} {affiliation} professor contact email"
        results.extend(self._safe_search(query1, 5))

        query2 = f'"{name}" {affiliation} faculty website'
        if department:
            query2 = f'"{name}" {affiliation} {department}'
        results.extend(self._safe_search(query2, 5))

        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        return unique[:10]
