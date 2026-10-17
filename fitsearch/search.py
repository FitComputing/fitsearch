import asyncio
import math
import re
import unicodedata
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from .engines import AVAILABLE_ENGINES
from .models import SearchResult
from .engines.rss import CustomRssEngine, RssEngine
from .engines.custom_source import CustomSourceEngine
from .source_catalog import sources_for_profile

PROFILES = {name: sources_for_profile(name) for name in
            ("complete", "encyclopedias", "news", "technology", "media")}

STOPWORDS = {"avec", "dans", "des", "les", "une", "pour", "sur", "par", "plus", "apres", "the", "and",
             "for", "from", "with", "that", "this", "are", "was", "will", "its", "has", "news", "live"}


@dataclass(slots=True)
class SearchOperators:
    query: str
    phrases: list[str]
    excluded: list[str]
    site: str = ""
    filetype: str = ""


def parse_operators(raw_query: str) -> SearchOperators:
    phrases = [value.strip() for value in re.findall(r'"([^"\n]+)"', raw_query) if value.strip()]
    site_match = re.search(r"(?:^|\s)site:([^\s]+)", raw_query, re.IGNORECASE)
    type_match = re.search(r"(?:^|\s)filetype:([a-z0-9]+)", raw_query, re.IGNORECASE)
    excluded = [word for word in re.findall(r"(?:^|\s)-([\wÀ-ÿ][\wÀ-ÿ.-]*)", raw_query) if word]
    cleaned = re.sub(r'"([^"\n]+)"', r"\1", raw_query)
    cleaned = re.sub(r"(?:^|\s)(?:site:[^\s]+|filetype:[a-z0-9]+|-[\wÀ-ÿ][\wÀ-ÿ.-]*)", " ", cleaned,
                     flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    site = site_match.group(1).strip("/.") if site_match else ""
    filetype = type_match.group(1).lower() if type_match else ""
    return SearchOperators(cleaned or " ".join(phrases), phrases, excluded, site, filetype)


def apply_operators(results: list[SearchResult], operators: SearchOperators) -> list[SearchResult]:
    filtered = []
    for item in results:
        haystack = plain(f"{item.title} {item.snippet} {item.url}")
        haystack_words = set(re.findall(r"[\wÀ-ÿ.-]+", haystack))
        if operators.phrases and not all(plain(phrase) in haystack for phrase in operators.phrases):
            continue
        if any(plain(word) in haystack_words for word in operators.excluded):
            continue
        if operators.filetype:
            if operators.filetype == "pdf" and item.engine == "arXiv" and "/abs/" in item.url:
                item.url = item.url.replace("/abs/", "/pdf/") + ".pdf"
            path = urlsplit(item.url).path.lower()
            if not path.endswith(f".{operators.filetype}"):
                continue
        filtered.append(item)
    return filtered


def plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


def title_terms(title: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]{3,}", plain(title)) if term not in STOPWORDS}


def cluster_news(results: list[SearchResult]) -> list[SearchResult]:
    clusters: list[tuple[SearchResult, set[str]]] = []
    for item in results:
        terms = title_terms(item.title)
        match = None
        if len(terms) >= 3:
            for representative, known_terms in clusters:
                shared = len(terms & known_terms)
                union = len(terms | known_terms)
                containment = shared / max(1, min(len(terms), len(known_terms)))
                if shared >= 3 and (shared / max(1, union) >= .42 or containment >= .66):
                    match = representative
                    break
        if match is None:
            item.related = []
            clusters.append((item, terms))
        else:
            match.related.append({"title": item.title, "url": item.url, "engine": item.engine,
                                  "published_at": item.published_at})
            current_agreement = (match.score_details or {}).get("agreement", 0)
            new_agreement = min(8, current_agreement + 3)
            bonus = (new_agreement - current_agreement) / 100
            match.score = min(.99, match.score + bonus)
            match.score_reason = ((match.score_reason + ", ") if match.score_reason else "") + "sources concordantes"
            if match.score_details:
                match.score_details["agreement"] = new_agreement
    return [representative for representative, _ in clusters]


def diversify_results(results: list[SearchResult]) -> list[SearchResult]:
    """Répartit sources et domaines sans supprimer ni modifier le score affiché."""
    diversified = []
    # Le rééquilibrage reste dans chaque tranche de dix résultats : les pages
    # suivantes ne peuvent donc pas bouleverser celles déjà affichées.
    for offset in range(0, len(results), 10):
        remaining = list(results[offset:offset + 10])
        source_counts: dict[str, int] = {}
        domain_counts: dict[str, int] = {}
        while remaining:
            best_index, best_value = 0, float("-inf")
            for index, item in enumerate(remaining):
                source = item.engine.split(",", 1)[0].strip().casefold()
                domain = urlsplit(item.url).netloc.lower().removeprefix("www.")
                source_penalty = min(source_counts.get(source, 0), 3) * .035
                domain_penalty = min(domain_counts.get(domain, 0), 3) * .05
                adjusted = item.score - source_penalty - domain_penalty
                if adjusted > best_value:
                    best_index, best_value = index, adjusted
            selected = remaining.pop(best_index)
            source = selected.engine.split(",", 1)[0].strip().casefold()
            domain = urlsplit(selected.url).netloc.lower().removeprefix("www.")
            source_counts[source] = source_counts.get(source, 0) + 1
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            diversified.append(selected)
    return diversified


def rank(item: SearchResult, query: str) -> SearchResult:
    terms = {term for term in re.findall(r"[\w-]+", plain(query)) if len(term) > 1}
    title, snippet = plain(item.title), plain(item.snippet)
    title_match = sum(term in title for term in terms) / max(1, len(terms))
    text_match = sum(term in snippet for term in terms) / max(1, len(terms))
    freshness = 0.0
    if item.published_at:
        try:
            published = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
            age_days = max(0, (datetime.now(timezone.utc) - published).days)
            freshness = max(0, 1 - age_days / 730)
        except (ValueError, TypeError):
            pass
    source_points = item.score * .62
    title_points = title_match * .23
    content_points = text_match * .08
    freshness_points = freshness * .07
    item.score = min(.99, source_points + title_points + content_points + freshness_points)
    item.score_details = {
        "source": round(source_points * 100), "title": round(title_points * 100),
        "content": round(content_points * 100), "freshness": round(freshness_points * 100),
        "agreement": 0,
    }
    reasons = []
    if title_match >= .5:
        reasons.append("titre pertinent")
    if freshness > .65:
        reasons.append("récent")
    item.score_reason = ", ".join(reasons) or "pertinence de la source"
    return item


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    clean_query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."),
                       re.sub(r"/$", "", parts.path), urlencode(clean_query), ""))


def demo_results(query: str, category: str) -> list[SearchResult]:
    q = query.strip() or "recherche locale"
    if category == "images":
        results = [SearchResult(f"Illustration — {q} · {i}", f"https://commons.wikimedia.org/wiki/Demo_{i}", "Aperçu du mode Images.",
                                "Démo", "images", max(.55, .94 - i * .02), f"https://picsum.photos/seed/{i}-{q}/900/600") for i in range(1, 19)]
        return attach_demo_scores(results)
    sources = ["Wikipédia", "Hacker News", "Documentation", "Open Library", "Stack Overflow", "arXiv"]
    results = [SearchResult(f"{q.capitalize()} — résultat {i + 1}", f"https://example.org/{category}/{i}?utm_source=demo",
            f"Résultat de démonstration pertinent pour « {q} ». Le mode réel interroge les sources activées en parallèle.",
            sources[i % len(sources)], category, max(.51, .96 - i * .025)) for i in range(24)]
    return attach_demo_scores(results)


def attach_demo_scores(results: list[SearchResult]) -> list[SearchResult]:
    for item in results:
        total = round(item.score * 100)
        item.score_reason = "aperçu du classement explicable"
        item.score_details = {"source": max(0, total - 38), "title": 23, "content": 8,
                              "freshness": 7, "agreement": 0}
    return results


def apply_filters(results: list[SearchResult], period: str, domain: str) -> list[SearchResult]:
    filtered = results
    clean_domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
    if clean_domain:
        filtered = [item for item in filtered
                    if (host := urlsplit(item.url).netloc.lower().removeprefix("www.")) == clean_domain
                    or host.endswith(f".{clean_domain}")]
    days = {"day": 1, "week": 7, "month": 31, "year": 366}.get(period)
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        dated = []
        for item in filtered:
            if not item.published_at:
                continue
            try:
                published = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
                if published >= cutoff:
                    dated.append(item)
            except (ValueError, TypeError):
                continue
        filtered = dated
    return filtered


async def aggregate(query: str, category: str, profile: str, enabled: dict, demo: bool = False,
                    period: str = "any", language: str = "any", source: str = "all", domain: str = "",
                    fetch_limit: int = 24, custom_feeds: list[dict] | None = None,
                    custom_sources: list[dict] | None = None, warhammer_edition: str = "10e",
                    credentials: dict | None = None, _fallback: bool = True,
                    latest_news: bool = False):
    if category == "all":
        return await aggregate_all(query, profile, enabled, demo, period, language, source, domain,
                                   fetch_limit, custom_feeds, custom_sources, warhammer_edition,
                                   credentials)
    if demo:
        warnings = [] if period == "any" and language == "any" and source == "all" and not domain else ["Les filtres avancés s’appliquent au mode réel"]
        return demo_results(query, category), warnings, []
    normalized_profile = {"quick": "complete", "private": "encyclopedias",
                          "technical": "technology"}.get(profile, profile)
    selected = PROFILES.get(normalized_profile, PROFILES["complete"])
    if source != "all" and source in AVAILABLE_ENGINES:
        selected = {source}
    elif source.startswith(("custom:", "personal:")):
        selected = set()
    async with httpx.AsyncClient(timeout=7, follow_redirects=True,
                                 headers={"User-Agent": "FitSearch/2.12 (local metasearch)"}) as client:
        engines = [cls(client) for key, cls in AVAILABLE_ENGINES.items()
                   if enabled.get(key, False) and key in selected and category in cls.categories]
        if category == "news" and (normalized_profile in {"complete", "news"} or source.startswith("custom:")):
            engines.extend(CustomRssEngine(client, feed) for feed in (custom_feeds or [])
                           if source == "all" or source == f"custom:{feed['id']}")
        if latest_news:
            # La veille sans requête concerne exclusivement les flux RSS actifs.
            engines = [engine for engine in engines if isinstance(engine, RssEngine)]
        personal_allowed = not latest_news and (normalized_profile == "complete" or source.startswith("personal:"))
        if normalized_profile == "encyclopedias":
            personal_allowed = True
        elif normalized_profile in {"technology", "media"}:
            personal_allowed = True
        if personal_allowed:
            engines.extend(CustomSourceEngine(client, item) for item in (custom_sources or [])
                           if (source == "all" or source == f"personal:{item['id']}")
                           and (normalized_profile not in {"encyclopedias", "technology", "media"}
                                or (normalized_profile == "encyclopedias" and item.get("kind") == "mediawiki")
                                or (normalized_profile == "technology" and item.get("domain") == "technology")
                                or (normalized_profile == "media" and item.get("domain") == "culture"))
                           and category in set((item.get("config") or {}).get("categories") or ["web"]))
        for engine in engines:
            engine.language = language
            engine.credentials = (credentials or {}).get(engine.key, {})
            if engine.key == "openhammer":
                engine.edition = warhammer_edition
        per_source_limit = 7 if latest_news else fetch_limit
        batches = await asyncio.gather(*(timed_search(e, query, category, per_source_limit) for e in engines))
    warnings, merged, health = [], {}, []
    for engine, (batch, elapsed, error) in zip(engines, batches):
        status = "error" if error else ("slow" if elapsed >= 3000 else ("empty" if not batch else "ok"))
        health.append({"key": engine.key, "label": engine.label, "status": status,
                       "response_ms": elapsed, "result_count": 0 if error else len(batch),
                       "error": str(error) if error else ""})
        if isinstance(batch, Exception):
            warnings.append(f"{engine.label} indisponible")
            continue
        for item in batch:
            item = rank(item, query)
            key = canonical_url(item.url)
            if key in merged:
                existing = merged[key]
                if item.engine not in existing.engine:
                    existing.engine += f", {item.engine}"
                existing.score = min(1, existing.score + .08)
                existing.score_reason = ((existing.score_reason + ", ") if existing.score_reason else "") + "sources concordantes"
                if existing.score_details:
                    existing.score_details["agreement"] = existing.score_details.get("agreement", 0) + 8
            else:
                merged[key] = item
    results = apply_filters(sorted(merged.values(), key=lambda r: r.score, reverse=True), period, domain)
    if category == "news":
        results = cluster_news(results)
    if latest_news:
        def publication_time(item: SearchResult) -> float:
            try:
                value = datetime.fromisoformat((item.published_at or "").replace("Z", "+00:00"))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.timestamp()
            except (ValueError, TypeError, OverflowError):
                return 0
        results.sort(key=publication_time, reverse=True)
    else:
        results = diversify_results(results)
    if not results and _fallback:
        if period != "any" or domain or source != "all":
            warnings.append("Aucun résultat ne correspond aux filtres choisis")
        else:
            warnings.append("Aucun résultat réel pour cette combinaison de profil et de contenu")
    return results, warnings, health


async def aggregate_all(query: str, profile: str, enabled: dict, demo: bool, period: str,
                        language: str, source: str, domain: str, fetch_limit: int,
                        custom_feeds: list[dict] | None, custom_sources: list[dict] | None,
                        warhammer_edition: str, credentials: dict | None):
    """Construit l'onglet Tous comme un mélange stable de contenus complémentaires."""
    categories = ("web", "news", "images", "videos", "books")
    weights = {"web": .45, "news": .18, "images": .14, "videos": .12, "books": .11}
    jobs = [aggregate(
        query, item_category, profile, enabled, demo, period, language, source, domain,
        max(3, math.ceil(fetch_limit * weights[item_category]) + 2), custom_feeds,
        custom_sources, warhammer_edition, credentials, False,
    ) for item_category in categories]
    batches = await asyncio.gather(*jobs)
    by_category: dict[str, list[SearchResult]] = {}
    warnings, health = [], []
    for item_category, (results, batch_warnings, batch_health) in zip(categories, batches):
        by_category[item_category] = list(results)
        warnings.extend(batch_warnings)
        health.extend(batch_health)

    # Deux résultats Web entre les respirations visuelles et éditoriales.
    sequence = ("web", "web", "news", "images", "web", "videos", "books", "news", "images")
    mixed, seen = [], set()
    while len(mixed) < fetch_limit and any(by_category.values()):
        progressed = False
        for item_category in sequence:
            bucket = by_category[item_category]
            while bucket:
                item = bucket.pop(0)
                key = canonical_url(item.url)
                if key in seen:
                    continue
                seen.add(key)
                mixed.append(item)
                progressed = True
                break
            if len(mixed) >= fetch_limit:
                break
        if not progressed:
            break
    if not mixed:
        if period != "any" or domain or source != "all":
            warnings.append("Aucun résultat ne correspond aux filtres choisis")
        else:
            warnings.append("Aucun résultat réel pour cette combinaison de profil et de contenu")
    unique_warnings = list(dict.fromkeys(warnings))
    return mixed, unique_warnings, health


async def timed_search(engine, query: str, category: str, limit: int):
    started = time.perf_counter()
    try:
        result = await engine.search(query, category, limit)
        return result, round((time.perf_counter() - started) * 1000), None
    except Exception as exc:
        return exc, round((time.perf_counter() - started) * 1000), exc


async def diagnose_sources(enabled: dict, custom_feeds: list[dict], custom_sources: list[dict] | None = None,
                           credentials: dict | None = None):
    async with httpx.AsyncClient(timeout=7, follow_redirects=True,
                                 headers={"User-Agent": "FitSearch/2.12 (source health check)"}) as client:
        engines = [cls(client) for key, cls in AVAILABLE_ENGINES.items() if enabled.get(key, False)]
        engines.extend(CustomRssEngine(client, feed) for feed in custom_feeds if feed.get("enabled"))
        engines.extend(CustomSourceEngine(client, source) for source in (custom_sources or [])
                       if source.get("enabled"))
        jobs = []
        diagnostic_queries = {
            "lalanguefrancaise": "grisoller",
            "larousse": "grisoller",
            "larousse_encyclopedia": "alouette",
            "universalis": "alouette",
            "universalis_media": "alouette",
        }
        for engine in engines:
            engine.credentials = (credentials or {}).get(engine.key, {})
            category = next((value for value in ("news", "web", "images", "videos", "books")
                             if value in engine.categories), "web")
            query = "" if isinstance(engine, CustomRssEngine) or category == "news" else (
                diagnostic_queries.get(engine.key) or ("dragon" if engine.key == "scryfall" else (
                    "Terminator" if engine.key == "openhammer" else (
                        "Roboute Guilliman" if engine.key == "warhammerwiki" else "open source"
                    )
                ))
            )
            jobs.append(timed_search(engine, query, category, 3))
        batches = await asyncio.gather(*jobs)
    health = []
    for engine, (batch, elapsed, error) in zip(engines, batches):
        status = "error" if error else ("slow" if elapsed >= 3000 else ("empty" if not batch else "ok"))
        health.append({"key": engine.key, "label": engine.label, "status": status,
                       "response_ms": elapsed, "result_count": 0 if error else len(batch),
                       "error": str(error) if error else ""})
    return health
