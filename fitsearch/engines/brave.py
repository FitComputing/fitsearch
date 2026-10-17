"""Adaptateur modèle, volontairement désactivé sans clé API."""
from .base import SearchEngine


class BraveEngine(SearchEngine):
    key, label = "brave", "Brave"
    categories = {"web", "images", "news"}

    async def search(self, query: str, category: str, limit: int = 8):
        # À compléter avec https://api.search.brave.com et BRAVE_API_KEY.
        return []
