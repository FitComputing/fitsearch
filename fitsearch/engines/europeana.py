from .base import SearchEngine
from ..models import SearchResult


def first(value):
    return value[0] if isinstance(value, list) and value else (value if isinstance(value, str) else "")


class EuropeanaEngine(SearchEngine):
    key = "europeana"
    label = "Europeana"
    categories = {"web", "images"}

    async def search(self, query: str, category: str, limit: int = 8):
        api_key = getattr(self, "credentials", {}).get("api_key")
        if not api_key:
            raise RuntimeError("Clé Europeana manquante")
        params = {"wskey": api_key, "query": query, "rows": min(limit, 20), "profile": "rich"}
        if category == "images":
            params["qf"] = "TYPE:IMAGE"
        response = await self.client.get("https://api.europeana.eu/record/v2/search.json", params=params)
        response.raise_for_status()
        results = []
        for item in response.json().get("items", []):
            title = first(item.get("title")) or "Œuvre sans titre"
            guid = item.get("guid")
            if not guid:
                continue
            provider = first(item.get("dataProvider")) or first(item.get("provider"))
            creator = first(item.get("dcCreator"))
            date = first(item.get("year"))
            rights = first(item.get("rights"))
            image = first(item.get("edmPreview"))
            snippet = " · ".join(value for value in (creator, date, provider, rights) if value)
            results.append(SearchResult(title, guid, snippet or "Collection patrimoniale européenne", self.label,
                                        category, .76, image))
        return results
