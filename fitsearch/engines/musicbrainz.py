from .base import SearchEngine
from ..models import SearchResult


class MusicBrainzEngine(SearchEngine):
    key = "musicbrainz"
    label = "MusicBrainz"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://musicbrainz.org/ws/2/release-group/", params={
            "query": query, "limit": limit, "fmt": "json",
        }, headers={"User-Agent": "FitSearch/2.12 (local metasearch)"})
        response.raise_for_status()
        results = []
        for release in response.json().get("release-groups", []):
            identifier = release.get("id")
            title = release.get("title")
            if not identifier or not title:
                continue
            artists = ", ".join(credit.get("name", "") for credit in (release.get("artist-credit") or [])[:3])
            date = release.get("first-release-date") or ""
            primary = release.get("primary-type") or "publication musicale"
            snippet = " · ".join(value for value in (artists, primary, date) if value)
            published = f"{date[:4]}-01-01T00:00:00+00:00" if len(date) >= 4 and date[:4].isdigit() else None
            results.append(SearchResult(title, f"https://musicbrainz.org/release-group/{identifier}",
                                        snippet, self.label, score=.70, published_at=published))
        return results
