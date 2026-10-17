from .base import SearchEngine
from ..models import SearchResult


def card_text(card: dict) -> str:
    faces = card.get("card_faces") or []
    source = faces[0] if faces else card
    card_type = source.get("printed_type_line") or source.get("type_line") or card.get("type_line") or "Carte Magic"
    rules = source.get("printed_text") or source.get("oracle_text") or card.get("oracle_text") or ""
    set_name = card.get("set_name") or ""
    rarity = card.get("rarity") or ""
    values = [card_type, rules, set_name, rarity]
    return " · ".join(value.replace("\n", " ") for value in values if value)[:1200]


class ScryfallEngine(SearchEngine):
    key = "scryfall"
    label = "Scryfall · Magic"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        api_query = query.strip()
        if self.language in {"fr", "de", "es", "it"} and "lang:" not in api_query.casefold():
            api_query = f"{api_query} lang:{self.language}"
        response = await self.client.get("https://api.scryfall.com/cards/search", params={
            "q": api_query, "unique": "cards", "order": "name", "include_multilingual": "true",
        }, headers={
            "User-Agent": "FitSearch/2.12 (local metasearch)",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
        })
        if response.status_code == 404:
            return []
        response.raise_for_status()
        results = []
        for card in response.json().get("data", [])[:limit]:
            title = card.get("printed_name") or card.get("name")
            url = card.get("scryfall_uri")
            if not title or not url:
                continue
            results.append(SearchResult(title, url, card_text(card), self.label, score=.78,
                                        image_url=(card.get("image_uris") or {}).get("normal")))
        return results
