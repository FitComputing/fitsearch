from .base import SearchEngine
from ..models import SearchResult


class HackerNewsEngine(SearchEngine):
    key = "hackernews"
    label = "Hacker News"
    categories = {"web", "news"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://hn.algolia.com/api/v1/search",
                                         params={"query": query, "tags": "story", "hitsPerPage": limit})
        response.raise_for_status()
        results = []
        for hit in response.json().get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            results.append(SearchResult(hit.get("title") or "Discussion", url,
                f"{hit.get('points') or 0} points · {hit.get('num_comments') or 0} commentaires",
                self.label, "news" if category == "news" else "web", .72,
                published_at=hit.get("created_at")))
        return results
