from urllib.parse import quote, quote_plus

from .base import SearchEngine
from ..models import SearchResult


class ExternalSearchEngine(SearchEngine):
    """Raccourci sûr vers une recherche publique, sans analyser la page distante."""

    search_url = ""
    description = "Recherche externe ouverte dans le navigateur."

    def url_for(self, query: str, category: str) -> str:
        return self.search_url.format(query=quote(query, safe=""), query_plus=quote_plus(query), category=category)

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        return [SearchResult(f"Rechercher « {query} » sur {self.label}", self.url_for(query, category),
                             self.description, self.label, category, .53)]


class UnsplashEngine(ExternalSearchEngine):
    key, label = "unsplash", "Unsplash"
    categories = {"images"}
    search_url = "https://unsplash.com/s/photos/{query}"
    description = "Photographies Unsplash · recherche publique externe."


class PexelsEngine(ExternalSearchEngine):
    key, label = "pexels", "Pexels"
    categories = {"images", "videos"}

    def url_for(self, query: str, category: str) -> str:
        section = "videos" if category == "videos" else "photos"
        return f"https://www.pexels.com/search/{section}/{quote(query, safe='')}/"

    description = "Photos et vidéos Pexels · recherche publique externe."


class PixabayEngine(ExternalSearchEngine):
    key, label = "pixabay", "Pixabay"
    categories = {"images", "videos"}

    def url_for(self, query: str, category: str) -> str:
        section = "videos" if category == "videos" else "images"
        return f"https://pixabay.com/{section}/search/{quote(query, safe='')}/"

    description = "Images et vidéos Pixabay · recherche publique externe."


class BurstEngine(ExternalSearchEngine):
    key, label = "burst", "Burst · Shopify"
    categories = {"images"}
    search_url = "https://www.shopify.com/stock-photos/photos/search?q={query_plus}"
    description = "Photographies gratuites Burst/Shopify · recherche publique externe."


class GratisographyEngine(ExternalSearchEngine):
    key, label = "gratisography", "Gratisography"
    categories = {"images"}
    search_url = "https://gratisography.com/?s={query_plus}"
    description = "Photographies créatives Gratisography · recherche publique externe."


class FlickrCcEngine(ExternalSearchEngine):
    key, label = "flickrcc", "Flickr · Creative Commons"
    categories = {"images"}
    search_url = "https://www.flickr.com/search/?text={query_plus}&license=4%2C5%2C6%2C9%2C10"
    description = "Recherche Flickr limitée aux licences Creative Commons sélectionnées."


class ReshotEngine(ExternalSearchEngine):
    key, label = "reshot", "Reshot"
    categories = {"images"}
    search_url = "https://www.reshot.com/search/{query}/"
    description = "Illustrations et icônes Reshot · recherche publique externe."


class UniversalisEngine(ExternalSearchEngine):
    key, label = "universalis", "Universalis · Articles"
    categories = {"web"}
    search_url = "https://www.universalis.fr/recherche/{query}/"
    description = "Encyclopédie francophone · certains contenus nécessitent un abonnement."


class UniversalisMediaEngine(ExternalSearchEngine):
    key, label = "universalis_media", "Universalis · Médias"
    categories = {"images"}
    search_url = "https://www.universalis.fr/recherche/{query}/media/"
    description = "Images, cartes et autres médias Universalis · recherche externe."


class FreeDictionaryEngine(ExternalSearchEngine):
    key, label = "freedictionary", "The Free Dictionary"
    categories = {"web"}
    search_url = "https://www.thefreedictionary.com/{query}"
    description = "Dictionnaire et encyclopédie multilingues · recherche externe."


class ScholarpediaEngine(SearchEngine):
    key, label = "scholarpedia", "Scholarpedia"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://www.scholarpedia.org/w/api.php", params={
            "action": "query", "generator": "search", "gsrsearch": query,
            "gsrnamespace": 0, "gsrlimit": min(limit, 20), "prop": "extracts|info",
            "exintro": 1, "explaintext": 1, "exsentences": 3, "inprop": "url", "format": "json",
        })
        response.raise_for_status()
        pages = (response.json().get("query") or {}).get("pages", {}).values()
        return [SearchResult(page.get("title") or "Article Scholarpedia", page.get("fullurl") or "",
                             (page.get("extract") or "Article encyclopédique relu par des spécialistes.")[:500],
                             self.label, "web", .77)
                for page in pages if page.get("fullurl")]
