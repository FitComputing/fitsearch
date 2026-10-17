import html
import re
import unicodedata
from urllib.parse import quote

from .base import SearchEngine
from ..models import SearchResult


def entry_slug(query: str) -> str:
    """Transforme une entrée française en chemin lisible par le dictionnaire."""
    normalized = unicodedata.normalize("NFKD", query.strip().lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text)).strip("-")


def clean_markup(value: str) -> str:
    value = re.sub(r"<blockquote\b.*", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def extract_entry(page: str) -> tuple[str, str]:
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.IGNORECASE | re.DOTALL)
    section_match = re.search(r'<section[^>]+id=["\']definition["\'][^>]*>(.*?)</section>',
                              page, re.IGNORECASE | re.DOTALL)
    definition_match = (re.search(r"<dd[^>]*>(.*?)</dd>", section_match.group(1),
                                  re.IGNORECASE | re.DOTALL) if section_match else None)
    title = clean_markup(title_match.group(1)) if title_match else ""
    definition = clean_markup(definition_match.group(1)) if definition_match else ""
    if not definition:
        meta = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
                         page, re.IGNORECASE | re.DOTALL)
        definition = html.unescape(meta.group(1)).strip() if meta else ""
    return title, definition


class LaLangueFrancaiseEngine(SearchEngine):
    key, label = "lalanguefrancaise", "La langue française"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories or self.language not in {"any", "fr"}:
            return []
        slug = entry_slug(query)
        if not slug or len(slug) > 120:
            return []
        url = f"https://www.lalanguefrancaise.com/dictionnaire/definition/{quote(slug, safe='-')}"
        response = await self.client.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        title, definition = extract_entry(response.text)
        if not title or title == "404" or not definition:
            return []
        return [SearchResult(f"Définition de {title}", str(response.url), definition[:500],
                             self.label, "web", .82)]
