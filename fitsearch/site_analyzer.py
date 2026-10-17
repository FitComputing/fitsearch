import re
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from .security import validate_public_url


class SiteInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.forms = []
        self.current_form = None
        self.generator = ""
        self.feeds = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "meta" and values.get("name", "").lower() == "generator":
            self.generator = values.get("content", "")
        elif tag == "link" and "alternate" in values.get("rel", "").lower() and values.get("type") in {
                "application/rss+xml", "application/atom+xml"}:
            if values.get("href"):
                self.feeds.append(values["href"])
        elif tag == "form":
            self.current_form = {"action": values.get("action", ""),
                                 "method": values.get("method", "get").lower(), "inputs": []}
            self.forms.append(self.current_form)
        elif tag == "input" and self.current_form is not None and values.get("name"):
            self.current_form["inputs"].append({"name": values["name"],
                                                "type": values.get("type", "text").lower(),
                                                "value": values.get("value", "")})

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "form":
            self.current_form = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def domain_suggestion(host: str, title: str, body: str) -> str:
    sample = f"{host} {title} {body[:12000]}".lower()
    matches = {
        "technology": ("arduino", "esp32", "raspberry", "linux", "software", "electronics", "computer"),
        "science": ("science", "research", "medicine", "biology", "physics", "mathematics"),
        "culture": ("museum", "music", "cinema", "literature", "book", "history"),
        "nature": ("animal", "biodiversity", "nature", "environment", "species"),
        "leisure": ("game", "gaming", "hobby", "sport"),
        "society": ("news", "politics", "society", "economy"),
    }
    scores = {domain: sum(word in sample for word in words) for domain, words in matches.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "general"


def proposal_from_html(final_url: str, html: str) -> dict:
    parser = SiteInspector()
    parser.feed(html[:1_500_000])
    host = urlsplit(final_url).hostname or ""
    title = re.sub(r"\s+", " ", parser.title).strip()
    name = re.split(r"[|–—]", title)[0].strip() or host.removeprefix("www.")
    feeds = [urljoin(final_url, item) for item in parser.feeds
             if "/comments/" not in urlsplit(urljoin(final_url, item)).path.lower()][:5]
    if "mediawiki" in parser.generator.lower():
        root = f"{urlsplit(final_url).scheme}://{urlsplit(final_url).netloc}"
        return {"compatible": True, "confidence": "bonne", "method": "Wiki MediaWiki",
                "message": "Une installation MediaWiki a été reconnue.", "name": name,
                "kind": "mediawiki", "endpoint": urljoin(root, "/w/api.php"), "query_param": "q",
                "domain": domain_suggestion(host, title, html), "categories": "web", "feeds": feeds}
    candidates = []
    preferred = {"s": 5, "q": 5, "query": 4, "search": 4, "keyword": 3, "term": 3}
    for form in parser.forms:
        if form["method"] != "get":
            continue
        for field in form["inputs"]:
            score = preferred.get(field["name"].lower(), 0) + (3 if field["type"] == "search" else 0)
            if score:
                candidates.append((score, form, field["name"]))
    if candidates:
        _, form, query_param = max(candidates, key=lambda item: item[0])
        action = urljoin(final_url, form["action"] or final_url)
        parts = urlsplit(action)
        params = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                  if key != query_param]
        params.append((query_param, "{query}"))
        endpoint = urlunsplit((parts.scheme, parts.netloc, parts.path,
                               urlencode(params, safe="{}"), ""))
        return {"compatible": True, "confidence": "bonne", "method": "Formulaire de recherche",
                "message": "Un formulaire de recherche public a été détecté.", "name": name,
                "kind": "external", "endpoint": endpoint, "query_param": query_param,
                "domain": domain_suggestion(host, title, html), "categories": "web", "feeds": feeds}
    return {"compatible": False, "confidence": "indéterminée", "method": "Non détectée",
            "message": "Aucun formulaire de recherche public compatible n’a été trouvé.",
            "name": name, "kind": "external", "endpoint": final_url, "query_param": "q",
            "domain": domain_suggestion(host, title, html), "categories": "web", "feeds": feeds}


async def analyze_site(url: str) -> dict:
    current = await validate_public_url(url)
    async with httpx.AsyncClient(timeout=10, follow_redirects=False,
                                 headers={"User-Agent": "FitSearch/2.14.2 (site compatibility check)",
                                          "Accept": "text/html,application/xhtml+xml"}) as client:
        for _ in range(4):
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                    current = await validate_public_url(urljoin(current, response.headers["location"]))
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type:
                    raise ValueError("Cette adresse ne renvoie pas une page web HTML")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 1_500_000:
                        raise ValueError("La page est trop volumineuse pour être analysée")
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
                html = b"".join(chunks).decode(encoding, errors="replace")
                proposal = proposal_from_html(str(response.url), html)
                candidates = list(proposal["feeds"])
                if not candidates and ("wp-content" in html.lower() or "wordpress" in html.lower()):
                    parts = urlsplit(str(response.url))
                    candidates.append(urlunsplit((parts.scheme, parts.netloc, "/feed/", "", "")))
                checks = []
                for feed_url in candidates[:3]:
                    checks.append(await check_feed(client, feed_url))
                proposal["feeds"] = [item["url"] for item in checks if item["valid"]]
                proposal["feed_checks"] = checks
                proposal["has_valid_feed"] = bool(proposal["feeds"])
                return proposal
    raise ValueError("Le site effectue trop de redirections")


async def check_feed(client: httpx.AsyncClient, url: str) -> dict:
    current = await validate_public_url(url)
    try:
        for _ in range(4):
            async with client.stream("GET", current, headers={"Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml"}) as response:
                if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                    current = await validate_public_url(urljoin(current, response.headers["location"]))
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 400_000:
                        break
                    chunks.append(chunk)
                sample = b"".join(chunks).lstrip()[:4000].lower()
                valid = b"<rss" in sample or b"<feed" in sample or b"<rdf:rdf" in sample
                kind = "Atom" if b"<feed" in sample else "RSS"
                return {"url": current, "valid": valid, "kind": kind if valid else "Inconnu"}
    except Exception as exc:
        return {"url": current, "valid": False, "kind": "Inconnu", "error": str(exc)[:120]}
    return {"url": current, "valid": False, "kind": "Inconnu", "error": "Trop de redirections"}
