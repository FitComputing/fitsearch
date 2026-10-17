from .base import SearchEngine
from ..models import SearchResult


class GbifEngine(SearchEngine):
    key = "gbif"
    label = "GBIF"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://api.gbif.org/v1/species/search",
                                         params={"q": query, "limit": limit})
        response.raise_for_status()
        results = []
        for species in response.json().get("results", []):
            key = species.get("key")
            title = species.get("vernacularName") or species.get("canonicalName") or species.get("scientificName")
            if not key or not title:
                continue
            scientific = species.get("scientificName") or ""
            rank = (species.get("rank") or "taxon").lower()
            kingdom = species.get("kingdom") or ""
            snippet = " · ".join(value for value in (scientific, rank, kingdom) if value)
            results.append(SearchResult(title, f"https://www.gbif.org/species/{key}", snippet,
                                        self.label, score=.72))
        return results
