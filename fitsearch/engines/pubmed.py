import asyncio
import re

from .base import SearchEngine
from ..models import SearchResult


class PubMedEngine(SearchEngine):
    key = "pubmed"
    label = "PubMed"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        found = await self.client.get(f"{base}/esearch.fcgi", params={
            "db": "pubmed", "term": query, "retmax": limit, "retmode": "json", "tool": "FitSearch",
        })
        found.raise_for_status()
        identifiers = found.json().get("esearchresult", {}).get("idlist", [])
        if not identifiers:
            return []
        await asyncio.sleep(.36)
        summary = await self.client.get(f"{base}/esummary.fcgi", params={
            "db": "pubmed", "id": ",".join(identifiers), "retmode": "json", "tool": "FitSearch",
        })
        summary.raise_for_status()
        payload = summary.json().get("result", {})
        results = []
        for identifier in identifiers:
            item = payload.get(identifier) or {}
            title = item.get("title")
            if not title:
                continue
            authors = ", ".join(author.get("name", "") for author in (item.get("authors") or [])[:3])
            journal = item.get("fulljournalname") or item.get("source") or ""
            year_match = re.search(r"\b(19|20)\d{2}\b", item.get("pubdate") or "")
            year = int(year_match.group()) if year_match else None
            snippet = " · ".join(value for value in (authors, journal, str(year) if year else "") if value)
            results.append(SearchResult(title, f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/", snippet,
                                        self.label, score=.75,
                                        published_at=f"{year}-01-01T00:00:00+00:00" if year else None))
        return results
