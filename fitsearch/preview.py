from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit
import asyncio
import re
import time

import httpx

from .security import validate_public_url


MUSICBRAINZ_RELEASE_GROUP = re.compile(
    r"^/release-group/([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/?$",
    re.IGNORECASE,
)
_musicbrainz_lock = asyncio.Lock()
_musicbrainz_last_request = 0.0
_musicbrainz_cache: dict[str, tuple[float, dict]] = {}
_scryfall_lock = asyncio.Lock()
_scryfall_last_request = 0.0
_scryfall_cache: dict[str, tuple[float, dict]] = {}
_warhammer_cache: dict[str, tuple[float, dict]] = {}


async def _musicbrainz_get(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    """Respecte la limite publique d'une requête MusicBrainz par seconde."""
    global _musicbrainz_last_request
    async with _musicbrainz_lock:
        pause = 1.05 - (time.monotonic() - _musicbrainz_last_request)
        if pause > 0:
            await asyncio.sleep(pause)
        response = await client.get(url, params=params)
        _musicbrainz_last_request = time.monotonic()
    response.raise_for_status()
    return response.json()


def _artist_credit(items: list) -> str:
    return "".join(f"{item.get('name', '')}{item.get('joinphrase', '')}" for item in items).strip()


async def fetch_musicbrainz_preview(identifier: str, original_url: str) -> dict:
    cached = _musicbrainz_cache.get(identifier)
    if cached and time.monotonic() - cached[0] < 3600:
        return {**cached[1], "url": original_url, "canonical": original_url}
    headers = {"User-Agent": "FitSearch/2.12 (local metasearch)", "Accept": "application/json"}
    base = "https://musicbrainz.org/ws/2"
    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
        group = await _musicbrainz_get(client, f"{base}/release-group/{identifier}", {
            "inc": "artist-credits+genres+releases", "fmt": "json",
        })
        releases = group.get("releases") or []
        preferred = next((item for item in releases if item.get("status") == "Official"), None)
        preferred = preferred or (releases[0] if releases else None)
        release = {}
        if preferred and preferred.get("id"):
            release = await _musicbrainz_get(client, f"{base}/release/{preferred['id']}", {
                "inc": "recordings+artist-credits+labels", "fmt": "json",
            })

    artists = _artist_credit(group.get("artist-credit") or [])
    primary_type = group.get("primary-type") or "Publication musicale"
    secondary_types = group.get("secondary-types") or []
    release_date = group.get("first-release-date") or release.get("date") or ""
    genres = [item.get("name", "") for item in sorted(
        group.get("genres") or [], key=lambda item: item.get("count", 0), reverse=True
    ) if item.get("name")][:6]
    labels = []
    for info in release.get("label-info") or []:
        name = (info.get("label") or {}).get("name")
        if name and name not in labels:
            labels.append(name)
    tracks = []
    for medium in release.get("media") or []:
        for track in medium.get("tracks") or []:
            title = track.get("title") or (track.get("recording") or {}).get("title")
            if title:
                tracks.append({"position": str(track.get("number") or len(tracks) + 1), "title": title})
            if len(tracks) >= 12:
                break
        if len(tracks) >= 12:
            break
    description_parts = [primary_type]
    if secondary_types:
        description_parts.append(", ".join(secondary_types))
    if artists:
        description_parts.append(f"par {artists}")
    if release_date:
        description_parts.append(f"première parution : {release_date}")
    preview = {
        "url": original_url, "canonical": original_url,
        "title": group.get("title") or release.get("title") or "Publication MusicBrainz",
        "description": " · ".join(description_parts), "excerpt": "",
        "image_url": f"https://coverartarchive.org/release-group/{identifier}/front-500",
        "site": "MusicBrainz", "type": "fiche musicale", "native": "musicbrainz",
        "music": {
            "artist": artists, "release_date": release_date, "primary_type": primary_type,
            "secondary_types": secondary_types, "genres": genres, "labels": labels[:3],
            "release_count": len(releases), "country": release.get("country") or "",
            "tracks": tracks, "track_count": sum(medium.get("track-count") or 0 for medium in release.get("media") or []),
        },
    }
    if len(_musicbrainz_cache) >= 64:
        oldest = min(_musicbrainz_cache, key=lambda key: _musicbrainz_cache[key][0])
        _musicbrainz_cache.pop(oldest, None)
    _musicbrainz_cache[identifier] = (time.monotonic(), preview)
    return preview


async def fetch_scryfall_preview(set_code: str, collector: str, language: str, original_url: str) -> dict:
    global _scryfall_last_request
    cache_key = f"{set_code}/{collector}/{language}"
    cached = _scryfall_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 3600:
        return {**cached[1], "url": original_url, "canonical": original_url}
    headers = {
        "User-Agent": "FitSearch/2.12 (local metasearch)",
        "Accept": "application/json;q=0.9,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        async with _scryfall_lock:
            pause = .12 - (time.monotonic() - _scryfall_last_request)
            if pause > 0:
                await asyncio.sleep(pause)
            response = await client.get(
                f"https://api.scryfall.com/cards/{quote(set_code, safe='')}/{quote(collector, safe='')}/{quote(language, safe='')}"
            )
            _scryfall_last_request = time.monotonic()
        response.raise_for_status()
        card = response.json()

    raw_faces = card.get("card_faces") or [card]
    top_images = card.get("image_uris") or {}
    faces = []
    for index, face in enumerate(raw_faces):
        images = face.get("image_uris") or (top_images if index == 0 else {})
        stats = " / ".join(value for value in (face.get("power"), face.get("toughness")) if value)
        faces.append({
            "name": face.get("printed_name") or face.get("name") or card.get("name") or "Carte Magic",
            "mana_cost": face.get("mana_cost") or "",
            "type_line": face.get("printed_type_line") or face.get("type_line") or "",
            "text": face.get("printed_text") or face.get("oracle_text") or "",
            "flavor_text": face.get("flavor_text") or "", "stats": stats,
            "loyalty": face.get("loyalty") or "", "defense": face.get("defense") or "",
            "image_url": images.get("normal") or images.get("large") or "",
            "artist": face.get("artist") or card.get("artist") or "",
        })
    legalities = [name for name, status in (card.get("legalities") or {}).items() if status == "legal"]
    prices = card.get("prices") or {}
    title = card.get("printed_name") or card.get("name") or faces[0]["name"]
    description = faces[0]["type_line"]
    if faces[0]["text"]:
        description += (" · " if description else "") + faces[0]["text"].replace("\n", " ")
    preview = {
        "url": original_url, "canonical": original_url, "title": title,
        "description": description[:1200], "excerpt": "", "image_url": faces[0]["image_url"],
        "site": "Scryfall", "type": "fiche Magic", "native": "scryfall",
        "card": {
            "faces": faces, "set_name": card.get("set_name") or "", "set_code": card.get("set") or set_code,
            "collector_number": card.get("collector_number") or collector,
            "rarity": card.get("rarity") or "", "released_at": card.get("released_at") or "",
            "artist": card.get("artist") or "", "legalities": legalities,
            "prices": {"eur": prices.get("eur"), "eur_foil": prices.get("eur_foil"),
                       "usd": prices.get("usd"), "usd_foil": prices.get("usd_foil")},
        },
    }
    if len(_scryfall_cache) >= 64:
        oldest = min(_scryfall_cache, key=lambda key: _scryfall_cache[key][0])
        _scryfall_cache.pop(oldest, None)
    _scryfall_cache[cache_key] = (time.monotonic(), preview)
    return preview


def _remember_warhammer(key: str, preview: dict) -> dict:
    if len(_warhammer_cache) >= 96:
        oldest = min(_warhammer_cache, key=lambda item: _warhammer_cache[item][0])
        _warhammer_cache.pop(oldest, None)
    _warhammer_cache[key] = (time.monotonic(), preview)
    return preview


async def fetch_openhammer_preview(edition: str, identifier: str, original_url: str) -> dict:
    cache_key = f"unit:{edition}:{identifier}"
    cached = _warhammer_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 3600:
        return {**cached[1], "url": original_url, "canonical": original_url}
    endpoint = f"https://openhammer-api-production.up.railway.app/v1/{edition}/units/{identifier}"
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "FitSearch/2.12"}) as client:
        response = await client.get(endpoint)
        response.raise_for_status()
        unit = response.json()
    faction = unit.get("faction") or "Warhammer 40,000"
    points = (unit.get("points") or {}).get("base")
    description = f"{faction} · {edition.removesuffix('e')}e édition"
    if points is not None:
        description += f" · {points} points"
    preview = {
        "url": original_url, "canonical": original_url, "title": unit.get("name") or "Unité Warhammer 40K",
        "description": description, "excerpt": "", "image_url": "", "site": "OpenHammer",
        "type": "fiche d’unité communautaire", "native": "openhammer",
        "unit": {
            "edition": edition, "faction": faction, "faction_type": unit.get("faction_type") or "",
            "unit_type": unit.get("type") or "", "points": unit.get("points") or {},
            "composition": unit.get("composition") or {}, "stats": unit.get("stats") or {},
            "invuln_save": unit.get("invuln_save") or "", "transport": unit.get("transport"),
            "weapons": unit.get("weapons") or {}, "abilities": unit.get("abilities") or [],
            "special_rules": unit.get("special_rules") or [], "keywords": unit.get("keywords") or [],
        },
    }
    return _remember_warhammer(cache_key, preview)


async def fetch_warhammer_wiki_preview(title: str, original_url: str) -> dict:
    cache_key = f"lore:{title.casefold()}"
    cached = _warhammer_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 3600:
        return {**cached[1], "url": original_url, "canonical": original_url}
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": "FitSearch/2.12"}) as client:
        response = await client.get("https://warhammer40k.fandom.com/api.php", params={
            "action": "query", "titles": title, "prop": "extracts|pageimages|info",
            "explaintext": "1", "exchars": "2800", "piprop": "thumbnail", "pithumbsize": "900",
            "inprop": "url", "format": "json", "formatversion": "2", "origin": "*",
        })
        response.raise_for_status()
        pages = (response.json().get("query") or {}).get("pages") or []
        page_extract = (pages[0].get("extract") or "").strip() if pages else ""
        if not page_extract:
            parsed = await client.get("https://warhammer40k.fandom.com/api.php", params={
                "action": "parse", "page": title, "section": "0", "prop": "text",
                "format": "json", "formatversion": "2", "origin": "*",
            })
            parsed.raise_for_status()
            parser = MetadataParser()
            parser.feed((parsed.json().get("parse") or {}).get("text") or "")
            page_extract = parser.excerpt(limit=2800)
    if not pages or pages[0].get("missing"):
        raise ValueError("Article Warhammer introuvable")
    page = pages[0]
    excerpt = page_extract
    first, _, rest = excerpt.partition("\n")
    if not rest and len(first) > 500:
        first, rest = first[:500].rsplit(" ", 1)[0] + "…", first
    preview = {
        "url": original_url, "canonical": page.get("fullurl") or original_url,
        "title": page.get("title") or title, "description": first[:900], "excerpt": rest[:2200],
        "image_url": (page.get("thumbnail") or {}).get("source") or "",
        "site": "Warhammer 40K Wiki", "type": "lore communautaire", "native": "warhammerwiki",
    }
    return _remember_warhammer(cache_key, preview)


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.meta = {}
        self.canonical = ""
        self.paragraphs = []
        self.current_paragraph = None
        self.current_priority = False
        self.content_depth = 0
        self.skipped_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        values = dict(attrs)
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "form"}:
            self.skipped_depth += 1
            return
        if self.skipped_depth:
            return
        if tag in {"article", "main"}:
            self.content_depth += 1
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key and values.get("content"):
                self.meta[key] = values["content"].strip()
        elif tag == "link" and "canonical" in (values.get("rel") or "").lower():
            self.canonical = values.get("href", "")
        elif tag == "p":
            self.current_paragraph = []
            self.current_priority = self.content_depth > 0

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "form"}:
            self.skipped_depth = max(0, self.skipped_depth - 1)
            return
        if self.skipped_depth:
            return
        if tag == "title":
            self.in_title = False
        elif tag == "p" and self.current_paragraph is not None:
            paragraph = re.sub(r"\s+", " ", " ".join(self.current_paragraph)).strip()
            if len(paragraph) >= 60:
                self.paragraphs.append((self.current_priority, paragraph))
            self.current_paragraph = None
        elif tag in {"article", "main"}:
            self.content_depth = max(0, self.content_depth - 1)

    def handle_data(self, data):
        if self.skipped_depth:
            return
        if self.in_title:
            self.title += data
        if self.current_paragraph is not None:
            self.current_paragraph.append(data)

    def excerpt(self, limit=1800):
        ordered = [text for priority, text in self.paragraphs if priority]
        ordered.extend(text for priority, text in self.paragraphs if not priority)
        selected, size = [], 0
        for paragraph in ordered:
            if paragraph in selected:
                continue
            remaining = limit - size
            if remaining <= 0:
                break
            selected.append(paragraph[:remaining])
            size += len(selected[-1]) + 2
            if len(selected) >= 5:
                break
        return "\n\n".join(selected)


async def fetch_preview(url: str) -> dict:
    parts = urlsplit(url)
    host = parts.hostname.lower().removeprefix("www.") if parts.hostname else ""
    if host == "musicbrainz.org":
        match = MUSICBRAINZ_RELEASE_GROUP.fullmatch(parts.path)
        if match:
            return await fetch_musicbrainz_preview(match.group(1).lower(), url)
    if host == "scryfall.com":
        segments = parts.path.strip("/").split("/")
        if len(segments) >= 3 and segments[0].lower() == "card":
            language = segments[3].lower() if len(segments) >= 5 and re.fullmatch(r"[a-z]{2}", segments[3], re.I) else "en"
            return await fetch_scryfall_preview(segments[1].lower(), unquote(segments[2]), language, url)
    if host == "openhammer-api-production.up.railway.app":
        match = re.fullmatch(r"/v1/(10e|11e)/units/([0-9a-f-]+)", parts.path, re.I)
        if match:
            return await fetch_openhammer_preview(match.group(1).lower(), match.group(2).lower(), url)
    if host == "warhammer40k.fandom.com" and parts.path.startswith("/wiki/"):
        return await fetch_warhammer_wiki_preview(unquote(parts.path.removeprefix("/wiki/")).replace("_", " "), url)
    current = url
    async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "FitSearch/2.12"}) as client:
        for _ in range(4):
            current = await validate_public_url(current)
            async with client.stream("GET", current, follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirection invalide")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    raise ValueError("Ce résultat n’est pas une page HTML")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 786_432:
                        break
                    chunks.append(chunk)
                source = b"".join(chunks).decode(response.charset_encoding or "utf-8", errors="replace")
                parser = MetadataParser()
                parser.feed(source)
                title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title.strip()
                description = (parser.meta.get("og:description") or parser.meta.get("description")
                               or parser.meta.get("twitter:description") or "")
                excerpt = parser.excerpt()
                if excerpt and description and excerpt.casefold().startswith(description.casefold()[:120]):
                    excerpt = excerpt[len(description):].lstrip(" .–—")
                image_candidate = parser.meta.get("og:image") or parser.meta.get("twitter:image") or ""
                image_url = urljoin(current, image_candidate) if image_candidate else ""
                if urlsplit(image_url).scheme.lower() not in {"http", "https"}:
                    image_url = ""
                canonical_candidate = urljoin(current, parser.canonical) if parser.canonical else current
                canonical_parts = urlsplit(canonical_candidate)
                canonical = canonical_candidate if canonical_parts.scheme.lower() in {"http", "https"} else current
                return {"url": current, "canonical": canonical,
                        "title": title[:500], "description": description[:1200],
                        "excerpt": excerpt[:1800], "image_url": image_url[:2000],
                        "site": (parser.meta.get("og:site_name") or "")[:200],
                        "type": (parser.meta.get("og:type") or "article")[:100]}
        raise ValueError("Trop de redirections")


async def fetch_preview_image(url: str) -> tuple[bytes, str]:
    current = url
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
    async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "FitSearch/2.12"}) as client:
        for _ in range(4):
            current = await validate_public_url(current)
            async with client.stream("GET", current, follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirection d’image invalide")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in allowed:
                    raise ValueError("Format d’image non pris en charge")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 3_145_728:
                        raise ValueError("Image trop volumineuse")
                    chunks.append(chunk)
                return b"".join(chunks), content_type
        raise ValueError("Trop de redirections d’image")
