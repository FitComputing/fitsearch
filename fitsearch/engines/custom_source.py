from urllib.parse import quote_plus, urlencode, urljoin, urlsplit, urlunsplit, parse_qsl

from .base import SearchEngine
from ..models import SearchResult
from ..security import validate_public_url


def value_at(data, path: str, default=None):
    value = data
    for part in (path or "").split("."):
        if not part:
            continue
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return default
    return default if value is None else value


def text_value(value) -> str:
    if isinstance(value, list):
        return " · ".join(str(item) for item in value[:5])
    return str(value or "")


class CustomSourceEngine(SearchEngine):
    categories = {"web", "images"}

    def __init__(self, client, source: dict):
        super().__init__(client)
        self.source = source
        self.key = f"personal:{source['id']}"
        self.label = source["name"]
        self.config = source.get("config") or {}
        self.categories = set(self.config.get("categories") or ["web"])

    def external_url(self, query: str) -> str:
        endpoint = self.config["endpoint"]
        if "{query}" in endpoint:
            return endpoint.replace("{query}", quote_plus(query))
        parts = urlsplit(endpoint)
        params = parse_qsl(parts.query, keep_blank_values=True)
        params.append((self.config.get("query_param") or "q", query))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        kind = self.source["kind"]
        if kind == "external":
            url = self.external_url(query)
            return [SearchResult(f"Rechercher « {query} » avec {self.label}", url,
                                 "Ouverture de la recherche sur cette source personnelle.",
                                 self.label, category, .54)]
        endpoint = await validate_public_url(self.config["endpoint"])
        if kind == "mediawiki":
            response = await self.client.get(endpoint, params={
                "action": "query", "generator": "search", "gsrsearch": query,
                "gsrlimit": min(limit, 20), "prop": "extracts|pageimages|info",
                "exintro": 1, "explaintext": 1, "exsentences": 3, "piprop": "thumbnail",
                "pithumbsize": 640, "inprop": "url", "format": "json", "origin": "*",
            }, follow_redirects=False)
            response.raise_for_status()
            pages = list((response.json().get("query") or {}).get("pages", {}).values())
            pages.sort(key=lambda item: item.get("index", 9999))
            return [SearchResult(item.get("title") or "Article", item.get("fullurl") or
                    f"{urlsplit(endpoint).scheme}://{urlsplit(endpoint).netloc}/?curid={item.get('pageid')}",
                    item.get("extract") or "Article MediaWiki", self.label, category, .68,
                    (item.get("thumbnail") or {}).get("source")) for item in pages[:limit]]
        params = {self.config.get("query_param") or "q": query}
        response = await self.client.get(endpoint, params=params, follow_redirects=False,
                                         headers={"Accept": "application/json"})
        response.raise_for_status()
        payload = response.json()
        items = value_at(payload, self.config.get("list_path", ""), payload)
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            raise ValueError("Le chemin de liste JSON ne désigne pas une liste")
        results = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            title = text_value(value_at(item, self.config.get("title_path", "title")))
            url = text_value(value_at(item, self.config.get("url_path", "url")))
            if not title or not url:
                continue
            results.append(SearchResult(title, urljoin(endpoint, url),
                text_value(value_at(item, self.config.get("snippet_path", "description")))[:1400],
                self.label, category, .65,
                text_value(value_at(item, self.config.get("image_path", ""))) or None))
        return results
