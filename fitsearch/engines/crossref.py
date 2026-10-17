from .base import SearchEngine
from ..models import SearchResult


class CrossrefEngine(SearchEngine):
    key = "crossref"
    label = "Crossref"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://api.crossref.org/works", params={
            "query": query, "rows": limit,
            "select": "DOI,title,author,issued,published,type,URL,publisher",
        })
        response.raise_for_status()
        results = []
        for work in response.json().get("message", {}).get("items", []):
            titles = work.get("title") or []
            doi = work.get("DOI")
            if not titles or not doi:
                continue
            authors = ", ".join(" ".join(filter(None, (author.get("given"), author.get("family"))))
                                for author in (work.get("author") or [])[:3])
            date_parts = ((work.get("published") or work.get("issued") or {}).get("date-parts") or [[]])[0]
            year = date_parts[0] if date_parts else None
            publisher = work.get("publisher") or ""
            snippet = " · ".join(value for value in (authors, publisher, str(year) if year else "") if value)
            results.append(SearchResult(titles[0], f"https://doi.org/{doi}", snippet,
                                        self.label, score=.71,
                                        published_at=f"{year}-01-01T00:00:00+00:00" if year else None))
        return results
