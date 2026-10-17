from .base import SearchEngine
from ..models import SearchResult


class InternetArchiveEngine(SearchEngine):
    key = "internetarchive"
    label = "Internet Archive"
    categories = {"videos", "books"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        media_type = "movies" if category == "videos" else "texts"
        response = await self.client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f"({query}) AND mediatype:({media_type})",
                "fl[]": ["identifier", "title", "description", "creator", "date"],
                "rows": min(limit, 50),
                "page": 1,
                "output": "json",
                "sort[]": "downloads desc",
            },
        )
        response.raise_for_status()
        results = []
        for item in response.json().get("response", {}).get("docs", []):
            identifier = item.get("identifier")
            if not identifier:
                continue
            title = item.get("title") or identifier
            creator = item.get("creator") or "Internet Archive"
            if isinstance(creator, list):
                creator = ", ".join(str(value) for value in creator[:2])
            description = item.get("description") or ""
            if isinstance(description, list):
                description = " ".join(str(value) for value in description[:2])
            snippet = " · ".join(value for value in (str(creator), str(description)[:260]) if value)
            results.append(SearchResult(
                str(title), f"https://archive.org/details/{identifier}", snippet,
                self.label, category, .67,
                f"https://archive.org/services/img/{identifier}", item.get("date"),
            ))
        return results
