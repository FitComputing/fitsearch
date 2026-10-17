from .base import SearchEngine
from ..models import SearchResult


class WikidataEngine(SearchEngine):
    key = "wikidata"
    label = "Wikidata"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        language = self.language if self.language in {"fr", "en", "de", "es", "it"} else "fr"
        response = await self.client.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbsearchentities", "search": query, "language": language,
            "uselang": language, "limit": limit, "format": "json", "origin": "*",
        })
        response.raise_for_status()
        return [SearchResult(item.get("label") or item["id"],
                             item.get("concepturi") or f"https://www.wikidata.org/wiki/{item['id']}",
                             item.get("description") or f"Entité structurée {item['id']}",
                             self.label, score=.74)
                for item in response.json().get("search", []) if item.get("id")]
