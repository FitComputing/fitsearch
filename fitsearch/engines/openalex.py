from .base import SearchEngine
from ..models import SearchResult


class OpenAlexEngine(SearchEngine):
    key = "openalex"
    label = "OpenAlex"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://api.openalex.org/works",
                                         params={"search": query, "per_page": limit})
        response.raise_for_status()
        results = []
        for work in response.json().get("results", []):
            title = work.get("display_name") or work.get("title")
            url = work.get("doi") or work.get("id")
            if not title or not url:
                continue
            authors = ", ".join(author.get("author", {}).get("display_name", "")
                                for author in (work.get("authorships") or [])[:3])
            year = work.get("publication_year")
            kind = (work.get("type") or "publication").replace("-", " ")
            snippet = " · ".join(value for value in (authors, str(year) if year else "", kind) if value)
            results.append(SearchResult(title, url, snippet, self.label, score=.73,
                                        published_at=f"{year}-01-01T00:00:00+00:00" if year else None))
        return results
