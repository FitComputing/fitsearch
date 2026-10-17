import html
import re
from html.parser import HTMLParser
from urllib.parse import quote, urljoin

from .base import SearchEngine
from ..models import SearchResult


def clean_markup(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def parse_dictionary(page: str) -> tuple[str, str, str]:
    title_match = re.search(r'<h2[^>]+class=["\'][^"\']*AdresseDefinition[^"\']*["\'][^>]*>(.*?)</h2>',
                            page, re.IGNORECASE | re.DOTALL)
    category_match = re.search(r'<p[^>]+class=["\'][^"\']*CatgramDefinition[^"\']*["\'][^>]*>(.*?)</p>',
                               page, re.IGNORECASE | re.DOTALL)
    definitions_block = re.search(r'<ul[^>]+class=["\'][^"\']*Definitions[^"\']*["\'][^>]*>(.*?)</ul>',
                                  page, re.IGNORECASE | re.DOTALL)
    definitions = (re.findall(r'<li[^>]+class=["\'][^"\']*DivisionDefinition[^"\']*["\'][^>]*>(.*?)</li>',
                              definitions_block.group(1), re.IGNORECASE | re.DOTALL)
                   if definitions_block else [])
    title = clean_markup(title_match.group(1)) if title_match else ""
    title = re.sub(r"^[^\wÀ-ÿ]+", "", title)
    category = clean_markup(re.split(r"<a\b", category_match.group(1), maxsplit=1,
                                     flags=re.IGNORECASE)[0]) if category_match else ""
    snippet = " • ".join(filter(None, (clean_markup(item) for item in definitions)))
    return title, category, snippet


class EncyclopediaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.definition_depth = 0
        self.current = None
        self.capture = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "div":
            if self.definition_depth:
                self.definition_depth += 1
            elif values.get("id") == "definition":
                self.definition_depth = 1
        if not self.definition_depth:
            return
        if tag == "article":
            self.current = {"url": "", "title": [], "snippet": [], "image": ""}
        elif self.current is not None:
            if tag == "a" and not self.current["url"]:
                self.current["url"] = values.get("href", "")
            elif tag == "h4":
                self.capture = "title"
            elif tag == "p":
                self.capture = "snippet"
            elif tag == "img" and not self.current["image"]:
                self.current["image"] = values.get("src", "")

    def handle_endtag(self, tag):
        if tag in {"h4", "p"}:
            self.capture = None
        if tag == "article" and self.current is not None:
            title = re.sub(r"\s+", " ", "".join(self.current["title"])).strip()
            snippet = re.sub(r"\s+", " ", "".join(self.current["snippet"])).strip()
            if self.current["url"] and title:
                self.items.append({**self.current, "title": title, "snippet": snippet})
            self.current = None
            self.capture = None
        if tag == "div" and self.definition_depth:
            self.definition_depth -= 1

    def handle_data(self, data):
        if self.current is not None and self.capture:
            self.current[self.capture].append(data)


class LarousseDictionaryEngine(SearchEngine):
    key, label = "larousse", "Larousse · Dictionnaire"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories or self.language not in {"any", "fr"}:
            return []
        entry = query.strip()
        if not entry or len(entry) > 120:
            return []
        path = quote(re.sub(r"\s+", "_", entry), safe="-_")
        response = await self.client.get(f"https://www.larousse.fr/dictionnaires/francais/{path}")
        if response.status_code == 404:
            return []
        response.raise_for_status()
        title, word_class, definition = parse_dictionary(response.text)
        if not title or not definition:
            return []
        snippet = f"{word_class} — {definition}" if word_class else definition
        return [SearchResult(f"Définition de {title}", str(response.url), snippet[:500],
                             self.label, "web", .84)]


class LarousseEncyclopediaEngine(SearchEngine):
    key, label = "larousse_encyclopedia", "Larousse · Encyclopédie"
    categories = {"web"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories or self.language not in {"any", "fr"} or not query.strip():
            return []
        response = await self.client.get("https://www.larousse.fr/encyclopedie/rechercher",
                                         params={"q": query.strip(), "t": "articles"})
        response.raise_for_status()
        parser = EncyclopediaParser()
        parser.feed(response.text)
        base = str(response.url)
        return [SearchResult(item["title"], urljoin(base, item["url"]),
                             item["snippet"] or "Article de l’Encyclopédie Larousse.",
                             self.label, "web", .78,
                             image_url=urljoin(base, item["image"]) if item["image"] else None)
                for item in parser.items[:min(limit, 20)]]
