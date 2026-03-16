# Brave Search API - see https://brave.com/search/api/
from typing import List
import requests
from .base import BaseSearch, SearchResult


class BraveSearch(BaseSearch):
    def __init__(self, api_key: str, delay: float = 0.6):
        super().__init__(api_key, delay)
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    @property
    def name(self) -> str:
        return "Brave"

    @property
    def cost_per_query(self) -> float:
        return 0.005

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        try:
            response = requests.get(
                self.base_url,
                headers={"X-Subscription-Token": self.api_key},
                params={"q": query, "count": num_results},
                timeout=15,
            )
            if response.status_code == 402:
                print("  [Brave] Quota exhausted")
                return []
            if response.status_code != 200:
                print("  [Brave] HTTP", response.status_code)
                return []
            data = response.json()
            web_results = data.get("web", {}).get("results", [])
            results = []
            for item in web_results:
                results.append(
                    SearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                        content=None,
                        score=0.0,
                    )
                )
            return results
        except Exception as e:
            print("  [Brave] API error:", e)
            return []
