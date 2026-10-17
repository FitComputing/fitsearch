from .base import SearchEngine
from ..models import SearchResult


class WikipediaEngine(SearchEngine):
    key = "wikipedia"
    label = "Wikipédia"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        language = self.language if self.language in {"fr", "en", "de", "es", "it"} else "fr"
        response = await self.client.get(
            f"https://{language}.wikipedia.org/w/api.php",
            params={"action": "query", "generator": "search", "gsrsearch": query,
                    "gsrlimit": limit, "prop": "extracts|info", "exintro": 1,
                    "explaintext": 1, "inprop": "url", "format": "json"},
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {}).values()
        return [SearchResult(p.get("title", ""), p.get("fullurl", ""),
                             p.get("extract", "")[:300], self.label, score=.78)
                for p in pages if p.get("fullurl")]
