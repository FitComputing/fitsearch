import html
from datetime import datetime, timezone

from .base import SearchEngine
from ..models import SearchResult


class StackExchangeSiteEngine(SearchEngine):
    categories = {"web"}
    technical = True
    site = ""

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://api.stackexchange.com/2.3/search/advanced", params={
            "q": query, "site": self.site, "sort": "relevance", "order": "desc", "pagesize": limit,
        })
        response.raise_for_status()
        results = []
        for item in response.json().get("items", []):
            created = datetime.fromtimestamp(item.get("creation_date", 0), timezone.utc).isoformat()
            snippet = f"{item.get('score', 0)} votes · {item.get('answer_count', 0)} réponses"
            results.append(SearchResult(html.unescape(item.get("title", "Question")), item.get("link", ""),
                                        snippet, self.label, score=.69, published_at=created))
        return [item for item in results if item.url]


class ElectricalEngineeringEngine(StackExchangeSiteEngine):
    key, label, site = "electronics", "Electrical Engineering", "electronics"


class SuperUserEngine(StackExchangeSiteEngine):
    key, label, site = "superuser", "Super User", "superuser"


class UnixLinuxEngine(StackExchangeSiteEngine):
    key, label, site = "unixlinux", "Unix & Linux", "unix"


class MoviesTvEngine(StackExchangeSiteEngine):
    key, label, site = "moviestv", "Movies & TV", "movies"
