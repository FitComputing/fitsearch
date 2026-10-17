import asyncio
import html
import re
from urllib.parse import quote

from .base import SearchEngine
from ..models import SearchResult


class WarhammerWikiEngine(SearchEngine):
    key = "warhammerwiki"
    label = "Warhammer 40K Wiki"
    categories = {"web"}
    api = "https://warhammer40k.fandom.com/api.php"

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response, suggested = await asyncio.gather(
            self.client.get(self.api, params={
                "action": "query", "list": "search", "srsearch": query, "srlimit": limit,
                "format": "json", "formatversion": "2", "origin": "*",
            }),
            self.client.get(self.api, params={
                "action": "opensearch", "search": query, "limit": limit, "namespace": "0",
                "format": "json", "origin": "*",
            }),
        )
        response.raise_for_status()
        suggested.raise_for_status()
        searched = (response.json().get("query") or {}).get("search", [])
        snippets = {page.get("title", "").casefold(): page.get("snippet") or "" for page in searched}
        titles = list(suggested.json()[1])
        titles.extend(page.get("title") for page in searched if page.get("title"))
        results = []
        seen = set()
        for title in titles:
            if not title or title.casefold() in seen:
                continue
            seen.add(title.casefold())
            url = f"https://warhammer40k.fandom.com/wiki/{quote(title.replace(' ', '_'))}"
            snippet = html.unescape(re.sub(r"<[^>]+>", " ", snippets.get(title.casefold(), "")))
            snippet = re.sub(r"\s+", " ", snippet).strip()
            results.append(SearchResult(title, url, snippet or "Article consacré à l’univers Warhammer 40,000",
                                        self.label, score=.73))
            if len(results) >= limit:
                break
        return results
