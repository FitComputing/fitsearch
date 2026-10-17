import asyncio
import html
import re
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
from urllib.parse import urljoin

from .base import SearchEngine
from ..models import SearchResult
from ..security import validate_public_url


def clean_html(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", cleaned)


class RssEngine(SearchEngine):
    categories = {"news"}
    feed_urls: tuple[str, ...] = ()
    language_code = "en"

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories or (self.language not in {"any", self.language_code}):
            return []
        responses = await asyncio.gather(*(self.client.get(url) for url in self.feed_urls), return_exceptions=True)
        terms = [term.lower() for term in re.findall(r"[\wÀ-ÿ-]+", query) if len(term) > 1]
        results = []
        for response in responses:
            if isinstance(response, Exception):
                continue
            response.raise_for_status()
            results.extend(self._parse(response.text, terms))
        unique = {}
        for item in results:
            unique.setdefault(item.url, item)
        return list(unique.values())[:limit]

    def _parse(self, xml: str, terms: list[str]) -> list[SearchResult]:
        root = ElementTree.fromstring(xml)
        root_name = root.tag.rsplit("}", 1)[-1].lower()
        if root_name not in {"rss", "feed", "rdf"}:
            raise ValueError("Le document n’est pas un flux RSS ou Atom")
        entries = root.findall(".//item")
        is_atom = not entries
        if is_atom:
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        entries = entries[:getattr(self, "item_limit", len(entries))]
        results = []
        for entry in entries:
            if is_atom:
                ns = "{http://www.w3.org/2005/Atom}"
                title = clean_html(entry.findtext(f"{ns}title", ""))
                summary = clean_html(entry.findtext(f"{ns}summary", "") or entry.findtext(f"{ns}content", ""))
                link_node = entry.find(f"{ns}link")
                link = link_node.get("href", "") if link_node is not None else ""
                published = entry.findtext(f"{ns}published", "") or entry.findtext(f"{ns}updated", "")
            else:
                title = clean_html(entry.findtext("title", ""))
                summary = clean_html(entry.findtext("description", ""))
                link = (entry.findtext("link", "") or entry.findtext("guid", "")).strip()
                published = entry.findtext("pubDate", "")
            haystack = f"{title} {summary}".lower()
            if terms and not any(term in haystack for term in terms):
                continue
            published_iso = None
            if published:
                try:
                    published_iso = parsedate_to_datetime(published).isoformat()
                except (TypeError, ValueError):
                    published_iso = published
            if title and link:
                results.append(SearchResult(title, link, summary[:320] or "Article récent.", self.label,
                                            "news", .72, published_at=published_iso))
        return results


class LeMondeEngine(RssEngine):
    key, label, language_code = "lemonde", "Le Monde", "fr"
    feed_urls = ("https://www.lemonde.fr/rss/une.xml", "https://www.lemonde.fr/rss/en_continu.xml")


class GuardianEngine(RssEngine):
    key, label, language_code = "guardian", "The Guardian", "en"
    feed_urls = ("https://www.theguardian.com/world/rss", "https://www.theguardian.com/technology/rss")


class BbcEngine(RssEngine):
    key, label, language_code = "bbc", "BBC News", "en"
    feed_urls = ("https://feeds.bbci.co.uk/news/rss.xml", "https://feeds.bbci.co.uk/news/world/rss.xml",
                 "https://feeds.bbci.co.uk/news/technology/rss.xml")


class CustomRssEngine(RssEngine):
    def __init__(self, client, feed: dict):
        super().__init__(client)
        self.key = f"custom:{feed['id']}"
        self.label = feed["name"]
        self.language_code = feed["language"]
        self.feed_urls = (feed["url"],)
        self.max_bytes = max(1_000_000, min(20_000_000, int(feed.get("max_bytes", 5_000_000))))
        self.item_limit = max(10, min(500, int(feed.get("item_limit", 100))))

    async def search(self, query: str, category: str, limit: int = 8):
        if category != "news" or self.language not in {"any", self.language_code}:
            return []
        current = self.feed_urls[0]
        for _ in range(4):
            current = await validate_public_url(current)
            async with self.client.stream("GET", current, follow_redirects=False, timeout=15) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirection RSS invalide")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        actual = round(size / 1_000_000, 1)
                        allowed = round(self.max_bytes / 1_000_000, 1)
                        raise ValueError(f"Flux RSS trop volumineux ({actual} Mo reçus, limite {allowed} Mo)")
                    chunks.append(chunk)
                text = b"".join(chunks).decode(response.charset_encoding or "utf-8", errors="replace")
                terms = [term.lower() for term in re.findall(r"[\wÀ-ÿ-]+", query) if len(term) > 1]
                return self._parse(text, terms)[:min(limit, self.item_limit)]
        raise ValueError("Trop de redirections RSS")
