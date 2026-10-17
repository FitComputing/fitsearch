from xml.etree import ElementTree
from .base import SearchEngine
from ..models import SearchResult


class ArxivEngine(SearchEngine):
    key = "arxiv"
    label = "arXiv"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://export.arxiv.org/api/query",
            params={"search_query": f"all:{query}", "start": 0, "max_results": limit,
                    "sortBy": "relevance", "sortOrder": "descending"})
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        atom = {"a": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("a:entry", atom):
            title = " ".join(entry.findtext("a:title", "", atom).split())
            summary = " ".join(entry.findtext("a:summary", "", atom).split())[:300]
            url = entry.findtext("a:id", "", atom)
            if url:
                results.append(SearchResult(title, url, summary, self.label, score=.68,
                    published_at=entry.findtext("a:published", None, atom)))
        return results
