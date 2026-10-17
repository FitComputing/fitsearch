import asyncio

from .base import SearchEngine
from ..models import SearchResult


class OpenHammerEngine(SearchEngine):
    key = "openhammer"
    label = "OpenHammer · Warhammer 40K"
    categories = {"web"}
    edition = "both"
    base = "https://openhammer-api-production.up.railway.app"

    async def search_edition(self, edition: str, query: str, limit: int):
        response = await self.client.get(f"{self.base}/v1/{edition}/units", params={
            "name": query, "limit": limit, "sort_by": "name",
        })
        response.raise_for_status()
        results = []
        for unit in response.json():
            name, identifier = unit.get("name"), unit.get("id")
            if not name or not identifier:
                continue
            points = (unit.get("points") or {}).get("base")
            stats = unit.get("stats") or {}
            values = [unit.get("faction") or "", f"édition {edition.removesuffix('e')}e"]
            if points is not None:
                values.append(f"{points} points")
            if stats:
                values.append(" · ".join(f"{key} {stats[key]}" for key in ("M", "T", "SV", "W") if stats.get(key)))
            results.append(SearchResult(name, f"{self.base}/v1/{edition}/units/{identifier}",
                                        " · ".join(values), self.label, score=.77))
        return results

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        editions = [self.edition] if self.edition in {"10e", "11e"} else ["10e", "11e"]
        per_edition = limit if len(editions) == 1 else max(2, (limit + 1) // 2)
        batches = await asyncio.gather(*(self.search_edition(edition, query, per_edition)
                                         for edition in editions))
        return [item for batch in batches for item in batch][:limit]
