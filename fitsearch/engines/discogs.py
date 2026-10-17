from .base import SearchEngine
from ..models import SearchResult


class DiscogsEngine(SearchEngine):
    key = "discogs"
    label = "Discogs"
    categories = {"web", "images"}

    async def search(self, query: str, category: str, limit: int = 8):
        token = getattr(self, "credentials", {}).get("token")
        if not token:
            raise RuntimeError("Jeton Discogs manquant")
        response = await self.client.get("https://api.discogs.com/database/search", params={
            "q": query, "type": "release", "per_page": min(limit, 20), "page": 1,
        }, headers={"Authorization": f"Discogs token={token}",
                    "User-Agent": "FitSearch/2.12 +https://localhost"})
        response.raise_for_status()
        results = []
        for item in response.json().get("results", []):
            title, uri = item.get("title"), item.get("uri")
            if not title or not uri:
                continue
            labels = ", ".join(item.get("label") or [])
            formats = ", ".join(item.get("format") or [])
            snippet = " · ".join(str(value) for value in (item.get("year"), formats, labels,
                                                            item.get("country")) if value)
            image = item.get("cover_image") if item.get("cover_image") and "spacer.gif" not in item["cover_image"] else None
            results.append(SearchResult(title, f"https://www.discogs.com{uri}", snippet, self.label,
                                        category, .74, image))
        return results
