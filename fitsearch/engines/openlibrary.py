from .base import SearchEngine
from ..models import SearchResult


class OpenLibraryEngine(SearchEngine):
    key = "openlibrary"
    label = "Open Library"
    categories = {"web", "books"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        params = {"q": query, "limit": limit, "fields": "key,title,author_name,first_publish_year,cover_i"}
        language_codes = {"fr": "fre", "en": "eng", "de": "ger", "es": "spa", "it": "ita"}
        if self.language in language_codes:
            params["language"] = language_codes[self.language]
        response = await self.client.get("https://openlibrary.org/search.json", params=params)
        response.raise_for_status()
        results = []
        for book in response.json().get("docs", []):
            key = book.get("key")
            if not key:
                continue
            authors = ", ".join((book.get("author_name") or [])[:2]) or "Auteur inconnu"
            year = book.get("first_publish_year")
            snippet = authors + (f" · première publication en {year}" if year else "")
            cover = f"https://covers.openlibrary.org/b/id/{book['cover_i']}-L.jpg" if book.get("cover_i") else None
            results.append(SearchResult(book.get("title", "Livre"), f"https://openlibrary.org{key}",
                                        snippet, self.label, category, .66, cover))
        return results
