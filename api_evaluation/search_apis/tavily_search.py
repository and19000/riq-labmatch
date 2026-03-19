"""
Tavily Search API implementation.
Docs: https://docs.tavily.com
"""
import time
from typing import List
from tavily import TavilyClient
from .base import BaseSearch, SearchResult


class TavilySearch(BaseSearch):
    """Tavily search API wrapper."""

    # Substrings indicating rate-limit / throttling / quota / auth blocks.
    # If detected, we re-raise so run_tavily_primary can rotate keys.
    RATE_LIMIT_ERROR_SUBSTRINGS = (
        "429",
        "too many requests",
        "rate limit",
        "rate-limited",
        "limit exceeded",
        "quota",
        "credit",
        "exhausted",
        "payment required",
        "402",
        "401",
        "invalid api key",
        "excessive requests",
        "blocked due to",
        "blocked",
    )

    def __init__(self, api_key: str, delay: float = 0.5):
        super().__init__(api_key, delay)
        self.client = TavilyClient(api_key=api_key)

    @property
    def name(self) -> str:
        return "Tavily"

    @property
    def cost_per_query(self) -> float:
        return 0.01

    def _safe_search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Tavily-specific safe wrapper.

        Unlike BaseSearch._safe_search, we DO NOT swallow exceptions.
        That allows key-rotation when Tavily rate-limits/blocks requests.
        """
        time.sleep(self.delay)
        self.query_count += 1
        self.total_cost += self.cost_per_query
        return self.search(query, num_results=num_results, include_raw_content=True)

    def search(self, query: str, num_results: int = 5, include_raw_content: bool = True) -> List[SearchResult]:
        try:
            kwargs = {
                "query": query,
                "search_depth": "advanced",
                "max_results": num_results,
                "include_answer": False,
            }
            if include_raw_content:
                kwargs["include_raw_content"] = True
            response = self.client.search(**kwargs)

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
            msg = str(e).lower()
            # If this is a throttling/blocking/auth problem, re-raise so the caller can rotate keys.
            if any(sub in msg for sub in self.RATE_LIMIT_ERROR_SUBSTRINGS):
                raise
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
