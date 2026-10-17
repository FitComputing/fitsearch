from .base import SearchEngine
from ..models import SearchResult


class TmdbEngine(SearchEngine):
    key = "tmdb"
    label = "TMDB · Cinéma & TV"
    categories = {"web", "images"}

    async def search(self, query: str, category: str, limit: int = 8):
        token = getattr(self, "credentials", {}).get("token")
        if not token:
            raise RuntimeError("Jeton TMDB manquant")
        language = self.language if self.language in {"fr", "en", "de", "es", "it"} else "fr"
        locale = {"fr": "fr-FR", "en": "en-US", "de": "de-DE", "es": "es-ES", "it": "it-IT"}[language]
        response = await self.client.get("https://api.themoviedb.org/3/search/multi", params={
            "query": query, "language": locale, "include_adult": "false",
        }, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        response.raise_for_status()
        results = []
        for item in response.json().get("results", []):
            kind, identifier = item.get("media_type"), item.get("id")
            if kind not in {"movie", "tv", "person"} or not identifier:
                continue
            title = item.get("title") or item.get("name")
            if not title:
                continue
            path = item.get("poster_path") or item.get("profile_path") or item.get("backdrop_path")
            image = f"https://image.tmdb.org/t/p/w500{path}" if path else None
            date = item.get("release_date") or item.get("first_air_date") or ""
            kind_label = {"movie": "Film", "tv": "Série TV", "person": "Personnalité"}[kind]
            score = item.get("vote_average")
            snippet = " · ".join(value for value in (kind_label, date[:4],
                f"Note TMDB {score:.1f}/10" if isinstance(score, (int, float)) and score else "",
                item.get("overview") or "") if value)
            results.append(SearchResult(title, f"https://www.themoviedb.org/{kind}/{identifier}", snippet[:1400],
                                        self.label, category, .79, image, f"{date}T00:00:00Z" if len(date) == 10 else None))
            if len(results) >= limit:
                break
        return results
