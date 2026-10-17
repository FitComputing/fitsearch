from datetime import datetime, timezone
from .base import SearchEngine
from ..models import SearchResult


class StackOverflowEngine(SearchEngine):
    key = "stackoverflow"
    label = "Stack Overflow"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://api.stackexchange.com/2.3/search/advanced",
            params={"q": query, "site": "stackoverflow", "sort": "relevance", "order": "desc", "pagesize": limit})
        response.raise_for_status()
        results = []
        for item in response.json().get("items", []):
            created = datetime.fromtimestamp(item.get("creation_date", 0), timezone.utc).isoformat()
            snippet = f"{item.get('score', 0)} votes · {item.get('answer_count', 0)} réponses"
            results.append(SearchResult(item.get("title", "Question"), item.get("link", ""), snippet,
                                        self.label, score=.70, published_at=created))
        return [item for item in results if item.url]
