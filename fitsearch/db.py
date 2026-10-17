import sqlite3
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

DEFAULTS = {"wikipedia": 1, "wikimedia": 1, "hackernews": 1, "openlibrary": 1,
            "stackoverflow": 1, "arxiv": 1, "lemonde": 1, "guardian": 1, "bbc": 1,
            "wikidata": 1, "openalex": 1, "crossref": 1, "pubmed": 1, "gbif": 1,
            "musicbrainz": 1, "electronics": 1, "superuser": 1, "unixlinux": 1, "moviestv": 1,
            "scryfall": 1, "openhammer": 1, "warhammerwiki": 1,
            "github": 1, "tmdb": 0, "europeana": 0, "discogs": 0, "digikey": 0,
            "internetarchive": 1, "unsplash": 1, "pexels": 1, "pixabay": 1,
            "burst": 1, "gratisography": 1, "flickrcc": 1, "reshot": 1,
            "scholarpedia": 1, "universalis": 1, "universalis_media": 1,
            "freedictionary": 1, "larousse": 1, "larousse_encyclopedia": 1,
            "lalanguefrancaise": 1,
            "hal": 1, "cochrane": 1, "googlescholar": 1, "sciencedirect": 1,
            "springerlink": 1,
            "brave": 0, "duckduckgo": 0}
ENGINE_LABELS = {"wikipedia": "Wikipédia", "wikimedia": "Wikimedia Commons", "hackernews": "Hacker News",
                 "openlibrary": "Open Library", "stackoverflow": "Stack Overflow", "arxiv": "arXiv",
                 "lemonde": "Le Monde RSS", "guardian": "The Guardian RSS", "bbc": "BBC News RSS",
                 "wikidata": "Wikidata", "openalex": "OpenAlex", "crossref": "Crossref",
                 "pubmed": "PubMed", "gbif": "GBIF", "musicbrainz": "MusicBrainz",
                 "electronics": "Electrical Engineering", "superuser": "Super User",
                 "unixlinux": "Unix & Linux", "moviestv": "Movies & TV", "scryfall": "Scryfall · Magic",
                 "openhammer": "OpenHammer · Warhammer 40K", "warhammerwiki": "Warhammer 40K Wiki",
                 "github": "GitHub", "tmdb": "TMDB · Cinéma & TV", "europeana": "Europeana",
                 "discogs": "Discogs", "digikey": "DigiKey", "internetarchive": "Internet Archive",
                 "unsplash": "Unsplash", "pexels": "Pexels", "pixabay": "Pixabay",
                 "burst": "Burst · Shopify", "gratisography": "Gratisography",
                 "flickrcc": "Flickr · Creative Commons", "reshot": "Reshot",
                 "scholarpedia": "Scholarpedia", "universalis": "Universalis · Articles",
                 "universalis_media": "Universalis · Médias",
                 "freedictionary": "The Free Dictionary", "larousse": "Larousse · Dictionnaire",
                 "larousse_encyclopedia": "Larousse · Encyclopédie",
                 "lalanguefrancaise": "La langue française",
                 "hal": "HAL · Archive ouverte", "cochrane": "Cochrane Library",
                 "googlescholar": "Google Scholar", "sciencedirect": "ScienceDirect",
                 "springerlink": "SpringerLink",
                 "brave": "Brave Search API", "duckduckgo": "DuckDuckGo HTML"}
SOURCE_DOMAINS = {
    "wikipedia": ["general", "science", "culture", "nature", "society", "leisure"],
    "wikidata": ["general", "science", "culture", "nature", "society", "leisure"],
    "wikimedia": ["general", "culture", "nature", "leisure"], "hackernews": ["technology", "society"],
    "openlibrary": ["culture", "leisure"], "musicbrainz": ["culture"],
    "moviestv": ["culture", "leisure"], "scryfall": ["leisure"],
    "openhammer": ["leisure"], "warhammerwiki": ["leisure"],
    "stackoverflow": ["technology"], "electronics": ["technology"], "superuser": ["technology"],
    "unixlinux": ["technology"], "arxiv": ["science"], "openalex": ["science"],
    "crossref": ["science"], "pubmed": ["science"], "gbif": ["nature", "science"],
    "lemonde": ["society"], "guardian": ["society"], "bbc": ["society"],
    "brave": ["general"], "duckduckgo": ["general"],
    "github": ["technology"], "tmdb": ["culture", "leisure"],
    "europeana": ["culture"], "discogs": ["culture"], "digikey": ["technology"],
    "internetarchive": ["culture", "leisure"],
    "unsplash": ["culture"], "pexels": ["culture"], "pixabay": ["culture"],
    "burst": ["culture"], "gratisography": ["culture"], "flickrcc": ["culture"],
    "reshot": ["culture"], "scholarpedia": ["science", "culture"],
    "universalis": ["general", "culture"], "universalis_media": ["culture"],
    "freedictionary": ["general", "culture"],
    "larousse": ["general", "culture"], "larousse_encyclopedia": ["general", "culture"],
    "lalanguefrancaise": ["general", "culture"],
    "hal": ["science"], "cochrane": ["science"], "googlescholar": ["science"],
    "sciencedirect": ["science"], "springerlink": ["science"],
}


class SettingsDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS engines (key TEXT PRIMARY KEY, enabled INTEGER NOT NULL)")
            db.executemany("INSERT OR IGNORE INTO engines VALUES (?, ?)", DEFAULTS.items())
            db.execute("CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO preferences VALUES ('history_enabled', '0')")
            db.execute("INSERT OR IGNORE INTO preferences VALUES ('cache_enabled', '1')")
            db.execute("INSERT OR IGNORE INTO preferences VALUES ('cache_ttl', '900')")
            db.execute("INSERT OR IGNORE INTO preferences VALUES ('rss_max_mb', '5')")
            db.execute("INSERT OR IGNORE INTO preferences VALUES ('rss_item_limit', '100')")
            db.execute("INSERT OR IGNORE INTO preferences VALUES ('warhammer_edition', '10e')")
            db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, query TEXT NOT NULL, "
                       "category TEXT NOT NULL, searched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS search_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, "
                       "created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS favorites (url TEXT PRIMARY KEY, title TEXT NOT NULL, "
                       "snippet TEXT NOT NULL, engine TEXT NOT NULL, category TEXT NOT NULL, "
                       "score REAL NOT NULL DEFAULT 0, image_url TEXT, saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS saved_searches (id INTEGER PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, "
                       "name TEXT NOT NULL, config TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS custom_feeds (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                       "url TEXT UNIQUE NOT NULL, language TEXT NOT NULL DEFAULT 'fr', enabled INTEGER NOT NULL DEFAULT 1, "
                       "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS custom_sources (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                       "kind TEXT NOT NULL, config TEXT NOT NULL, domain TEXT NOT NULL DEFAULT 'general', "
                       "enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS source_health (key TEXT PRIMARY KEY, label TEXT NOT NULL, "
                       "status TEXT NOT NULL, response_ms INTEGER, average_ms INTEGER, result_count INTEGER NOT NULL DEFAULT 0, "
                       "last_success TEXT, last_error TEXT, error_message TEXT, checked_at TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path)

    def engines(self) -> dict[str, bool]:
        with self.connect() as db:
            return {key: bool(enabled) for key, enabled in db.execute("SELECT key, enabled FROM engines")}

    def set_engine(self, key: str, enabled: bool):
        with self.connect() as db:
            db.execute("INSERT INTO engines VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET enabled=excluded.enabled",
                       (key, int(enabled)))

    def history_enabled(self) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE key='history_enabled'").fetchone()
            return bool(row and row[0] == "1")

    def set_history_enabled(self, enabled: bool):
        with self.connect() as db:
            db.execute("INSERT INTO preferences VALUES ('history_enabled', ?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("1" if enabled else "0",))

    def add_history(self, query: str, category: str):
        if not self.history_enabled():
            return
        with self.connect() as db:
            db.execute("DELETE FROM history WHERE lower(query)=lower(?) AND category=?", (query, category))
            db.execute("INSERT INTO history(query, category) VALUES (?, ?)", (query, category))
            db.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 100)")

    def history(self, prefix: str = "", limit: int = 8) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT query, category, searched_at FROM history "
                              "WHERE lower(query) LIKE lower(?) ORDER BY id DESC LIMIT ?",
                              (f"{prefix}%", limit)).fetchall()
        return [{"query": query, "category": category, "searched_at": searched_at}
                for query, category, searched_at in rows]

    def clear_history(self):
        with self.connect() as db:
            db.execute("DELETE FROM history")

    def preference(self, key: str, default: str = "") -> str:
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def set_preference(self, key: str, value: str):
        with self.connect() as db:
            db.execute("INSERT INTO preferences VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def cache_enabled(self) -> bool:
        return self.preference("cache_enabled", "1") == "1"

    def cache_ttl(self) -> int:
        try:
            return int(self.preference("cache_ttl", "900"))
        except ValueError:
            return 900

    def rss_max_mb(self) -> int:
        try:
            return max(1, min(20, int(self.preference("rss_max_mb", "5"))))
        except ValueError:
            return 5

    def rss_item_limit(self) -> int:
        try:
            return max(10, min(500, int(self.preference("rss_item_limit", "100"))))
        except ValueError:
            return 100

    def get_cache(self, key: str) -> dict | None:
        if not self.cache_enabled():
            return None
        now = int(time.time())
        with self.connect() as db:
            db.execute("DELETE FROM search_cache WHERE expires_at <= ?", (now,))
            row = db.execute("SELECT payload FROM search_cache WHERE key=? AND expires_at>?", (key, now)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    def set_cache(self, key: str, payload: dict):
        if not self.cache_enabled():
            return
        now, ttl = int(time.time()), self.cache_ttl()
        with self.connect() as db:
            db.execute("INSERT INTO search_cache VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
                       "payload=excluded.payload, created_at=excluded.created_at, expires_at=excluded.expires_at",
                       (key, json.dumps(payload, ensure_ascii=False), now, now + ttl))
            db.execute("DELETE FROM search_cache WHERE key NOT IN "
                       "(SELECT key FROM search_cache ORDER BY created_at DESC LIMIT 100)")

    def clear_cache(self):
        with self.connect() as db:
            db.execute("DELETE FROM search_cache")

    def cache_stats(self) -> dict:
        now = int(time.time())
        with self.connect() as db:
            db.execute("DELETE FROM search_cache WHERE expires_at <= ?", (now,))
            count, size = db.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(payload)), 0) FROM search_cache").fetchone()
        return {"entries": count, "bytes": size}

    def add_favorite(self, item: dict):
        with self.connect() as db:
            db.execute("INSERT INTO favorites(url,title,snippet,engine,category,score,image_url) "
                       "VALUES (?,?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET title=excluded.title, "
                       "snippet=excluded.snippet, engine=excluded.engine, category=excluded.category, "
                       "score=excluded.score, image_url=excluded.image_url",
                       (item["url"], item["title"], item.get("snippet", ""), item.get("engine", ""),
                        item.get("category", "web"), float(item.get("score", 0)), item.get("image_url") or None))

    def remove_favorite(self, url: str):
        with self.connect() as db:
            db.execute("DELETE FROM favorites WHERE url=?", (url,))

    def favorite_urls(self, urls: list[str]) -> set[str]:
        if not urls:
            return set()
        placeholders = ",".join("?" for _ in urls)
        with self.connect() as db:
            return {row[0] for row in db.execute(f"SELECT url FROM favorites WHERE url IN ({placeholders})", urls)}

    def favorites(self, limit: int = 200) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT url,title,snippet,engine,category,score,image_url,saved_at "
                              "FROM favorites ORDER BY saved_at DESC LIMIT ?", (limit,)).fetchall()
        keys = ("url", "title", "snippet", "engine", "category", "score", "image_url", "saved_at")
        return [dict(zip(keys, row)) for row in rows]

    def save_search(self, name: str, config: dict) -> int:
        serialized = json.dumps(config, sort_keys=True, ensure_ascii=False)
        fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
        with self.connect() as db:
            db.execute("INSERT INTO saved_searches(fingerprint,name,config) VALUES (?,?,?) "
                       "ON CONFLICT(fingerprint) DO UPDATE SET name=excluded.name",
                       (fingerprint, name, serialized))
            row = db.execute("SELECT id FROM saved_searches WHERE fingerprint=?", (fingerprint,)).fetchone()
        return row[0]

    def saved_searches(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT id,name,config,created_at FROM saved_searches ORDER BY id DESC").fetchall()
        results = []
        for identifier, name, config, created_at in rows:
            try:
                results.append({"id": identifier, "name": name, "config": json.loads(config), "created_at": created_at})
            except json.JSONDecodeError:
                continue
        return results

    def remove_saved_search(self, identifier: int):
        with self.connect() as db:
            db.execute("DELETE FROM saved_searches WHERE id=?", (identifier,))

    def add_custom_feed(self, name: str, url: str, language: str) -> int:
        with self.connect() as db:
            db.execute("INSERT INTO custom_feeds(name,url,language) VALUES (?,?,?) "
                       "ON CONFLICT(url) DO UPDATE SET name=excluded.name, language=excluded.language, enabled=1",
                       (name, url, language))
            return db.execute("SELECT id FROM custom_feeds WHERE url=?", (url,)).fetchone()[0]

    def custom_feeds(self, enabled_only: bool = False) -> list[dict]:
        sql = "SELECT id,name,url,language,enabled,created_at FROM custom_feeds"
        if enabled_only:
            sql += " WHERE enabled=1"
        sql += " ORDER BY id DESC"
        with self.connect() as db:
            rows = db.execute(sql).fetchall()
        keys = ("id", "name", "url", "language", "enabled", "created_at")
        return [{**dict(zip(keys, row)), "enabled": bool(row[4])} for row in rows]

    def set_custom_feed(self, identifier: int, enabled: bool):
        with self.connect() as db:
            db.execute("UPDATE custom_feeds SET enabled=? WHERE id=?", (int(enabled), identifier))

    def remove_custom_feed(self, identifier: int):
        with self.connect() as db:
            db.execute("DELETE FROM custom_feeds WHERE id=?", (identifier,))

    def add_custom_source(self, name: str, kind: str, config: dict, domain: str) -> int:
        with self.connect() as db:
            cursor = db.execute("INSERT INTO custom_sources(name,kind,config,domain) VALUES (?,?,?,?)",
                                (name, kind, json.dumps(config, ensure_ascii=False), domain))
            return cursor.lastrowid

    def custom_sources(self, enabled_only: bool = False) -> list[dict]:
        sql = "SELECT id,name,kind,config,domain,enabled,created_at FROM custom_sources"
        if enabled_only:
            sql += " WHERE enabled=1"
        sql += " ORDER BY id DESC"
        with self.connect() as db:
            rows = db.execute(sql).fetchall()
        values = []
        for identifier, name, kind, config, domain, enabled, created_at in rows:
            try:
                decoded = json.loads(config)
            except json.JSONDecodeError:
                decoded = {}
            values.append({"id": identifier, "name": name, "kind": kind, "config": decoded,
                           "domain": domain, "enabled": bool(enabled), "created_at": created_at})
        return values

    def set_custom_source(self, identifier: int, enabled: bool):
        with self.connect() as db:
            db.execute("UPDATE custom_sources SET enabled=? WHERE id=?", (int(enabled), identifier))

    def remove_custom_source(self, identifier: int):
        with self.connect() as db:
            db.execute("DELETE FROM custom_sources WHERE id=?", (identifier,))

    def record_source_health(self, measurements: list[dict]):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            for item in measurements:
                previous = db.execute("SELECT average_ms FROM source_health WHERE key=?", (item["key"],)).fetchone()
                response_ms = max(0, int(item.get("response_ms", 0)))
                average_ms = response_ms if not previous or previous[0] is None else round(previous[0] * .7 + response_ms * .3)
                success = item["status"] != "error"
                db.execute("INSERT INTO source_health(key,label,status,response_ms,average_ms,result_count,last_success,last_error,error_message,checked_at) "
                           "VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET label=excluded.label,status=excluded.status,"
                           "response_ms=excluded.response_ms,average_ms=excluded.average_ms,result_count=excluded.result_count,"
                           "last_success=COALESCE(excluded.last_success,source_health.last_success),"
                           "last_error=COALESCE(excluded.last_error,source_health.last_error),"
                           "error_message=CASE WHEN excluded.status='error' THEN excluded.error_message "
                           "ELSE source_health.error_message END,checked_at=excluded.checked_at",
                           (item["key"], item["label"][:100], item["status"], response_ms, average_ms,
                            max(0, int(item.get("result_count", 0))), now if success else None,
                            None if success else now, (item.get("error") or "")[:200], now))

    def source_health(self) -> list[dict]:
        with self.connect() as db:
            recorded = {row[0]: row for row in db.execute(
                "SELECT key,label,status,response_ms,average_ms,result_count,last_success,last_error,error_message,checked_at FROM source_health"
            ).fetchall()}
        sources = [(key, ENGINE_LABELS[key], enabled) for key, enabled in self.engines().items()]
        sources.extend((f"custom:{feed['id']}", feed["name"], feed["enabled"]) for feed in self.custom_feeds())
        personal = self.custom_sources()
        sources.extend((f"personal:{source['id']}", source["name"], source["enabled"])
                       for source in personal)
        personal_domains = {f"personal:{source['id']}": ["custom", source["domain"]] for source in personal}
        items = []
        keys = ("key", "label", "status", "response_ms", "average_ms", "result_count",
                "last_success", "last_error", "error_message", "checked_at")
        for key, label, enabled in sources:
            if not enabled:
                items.append({"key": key, "label": label, "domains": personal_domains.get(key, SOURCE_DOMAINS.get(key, ["general"])), "status": "disabled", "response_ms": None,
                              "average_ms": None, "result_count": 0, "last_success": None,
                              "last_error": None, "error_message": "", "checked_at": None})
            elif key in recorded:
                item = dict(zip(keys, recorded[key])); item["label"] = label; item["domains"] = personal_domains.get(key, SOURCE_DOMAINS.get(key, ["custom"] if key.startswith("custom:") else ["general"])); items.append(item)
            else:
                items.append({"key": key, "label": label, "domains": personal_domains.get(key, SOURCE_DOMAINS.get(key, ["custom"])), "status": "unknown", "response_ms": None,
                              "average_ms": None, "result_count": 0, "last_success": None,
                              "last_error": None, "error_message": "", "checked_at": None})
        order = {"error": 0, "slow": 1, "empty": 2, "unknown": 3, "ok": 4, "disabled": 5}
        return sorted(items, key=lambda item: (order.get(item["status"], 9), item["label"].casefold()))

    def backup(self) -> dict:
        with self.connect() as db:
            preferences = dict(db.execute(
                "SELECT key,value FROM preferences WHERE key IN ('history_enabled','cache_enabled','cache_ttl','warhammer_edition','rss_max_mb','rss_item_limit')"
            ).fetchall())
            history = [dict(zip(("query", "category", "searched_at"), row)) for row in db.execute(
                "SELECT query,category,searched_at FROM history ORDER BY id"
            ).fetchall()]
            favorites = [dict(zip(("url", "title", "snippet", "engine", "category", "score", "image_url", "saved_at"), row))
                         for row in db.execute("SELECT url,title,snippet,engine,category,score,image_url,saved_at FROM favorites").fetchall()]
            saved = []
            for name, config, created_at in db.execute(
                    "SELECT name,config,created_at FROM saved_searches ORDER BY id").fetchall():
                try:
                    saved.append({"name": name, "config": json.loads(config), "created_at": created_at})
                except json.JSONDecodeError:
                    continue
            feeds = [dict(zip(("id", "name", "url", "language", "enabled", "created_at"), row))
                     for row in db.execute("SELECT id,name,url,language,enabled,created_at FROM custom_feeds ORDER BY id").fetchall()]
            sources = []
            for identifier, name, kind, config, domain, enabled, created_at in db.execute(
                    "SELECT id,name,kind,config,domain,enabled,created_at FROM custom_sources ORDER BY id").fetchall():
                try:
                    sources.append({"id": identifier, "name": name, "kind": kind,
                                    "config": json.loads(config), "domain": domain,
                                    "enabled": enabled, "created_at": created_at})
                except json.JSONDecodeError:
                    continue
        return {"format": "fitsearch-backup", "version": 1, "engines": self.engines(),
                "preferences": preferences, "history": history, "favorites": favorites,
                "saved_searches": saved, "custom_feeds": feeds, "custom_sources": sources}

    def restore(self, payload: dict) -> dict:
        if payload.get("format") != "fitsearch-backup" or payload.get("version") != 1:
            raise ValueError("Ce fichier n’est pas une sauvegarde FitSearch compatible")
        collections = {key: payload.get(key, []) for key in
                       ("history", "favorites", "saved_searches", "custom_feeds", "custom_sources")}
        limits = {"history": 100, "favorites": 1000, "saved_searches": 500,
                  "custom_feeds": 200, "custom_sources": 100}
        if any(not isinstance(value, list) or len(value) > limits[key] for key, value in collections.items()):
            raise ValueError("La sauvegarde contient trop d’éléments ou une structure invalide")
        if any(not isinstance(item, dict) for value in collections.values() for item in value):
            raise ValueError("Élément de sauvegarde invalide")
        engines = payload.get("engines", {})
        preferences = payload.get("preferences", {})
        if not isinstance(engines, dict) or not isinstance(preferences, dict):
            raise ValueError("Réglages de sauvegarde invalides")

        def text(item, key, maximum, default=""):
            value = item.get(key, default)
            if value is None:
                value = default
            if not isinstance(value, str):
                raise ValueError(f"Champ {key} invalide")
            return value[:maximum]

        normalized_history = [(text(x, "query", 200), text(x, "category", 20, "web"),
                               text(x, "searched_at", 40)) for x in collections["history"]]
        normalized_favorites = []
        for item in collections["favorites"]:
            url = text(item, "url", 2000)
            if not url.startswith(("http://", "https://")):
                raise ValueError("Adresse de favori invalide")
            normalized_favorites.append((url, text(item, "title", 500), text(item, "snippet", 1000),
                                         text(item, "engine", 100), text(item, "category", 20, "web"),
                                         max(0, min(1, float(item.get("score", 0)))),
                                         text(item, "image_url", 2000) or None, text(item, "saved_at", 40)))
        normalized_saved = []
        for item in collections["saved_searches"]:
            config = item.get("config")
            if not isinstance(config, dict):
                raise ValueError("Recherche enregistrée invalide")
            serialized = json.dumps(config, sort_keys=True, ensure_ascii=False)
            if len(serialized) > 5000:
                raise ValueError("Recherche enregistrée trop volumineuse")
            normalized_saved.append((hashlib.sha256(serialized.encode()).hexdigest(), text(item, "name", 100),
                                     serialized, text(item, "created_at", 40)))
        normalized_feeds = []
        for item in collections["custom_feeds"]:
            url = text(item, "url", 2000)
            if not url.startswith(("http://", "https://")):
                raise ValueError("Adresse de flux RSS invalide")
            language = text(item, "language", 10, "fr")
            if language not in {"fr", "en", "de", "es", "it"}:
                language = "fr"
            normalized_feeds.append((int(item.get("id", 0)), text(item, "name", 100), url, language,
                                     int(bool(item.get("enabled", True))), text(item, "created_at", 40)))
        if any(identifier <= 0 for identifier, *_ in normalized_feeds):
            raise ValueError("Identifiant de flux RSS invalide")
        normalized_sources = []
        allowed_domains = {"general", "science", "culture", "technology", "nature", "society", "leisure"}
        for item in collections["custom_sources"]:
            identifier = int(item.get("id", 0))
            kind = text(item, "kind", 20)
            config = item.get("config")
            domain = text(item, "domain", 20, "general")
            if identifier <= 0 or kind not in {"external", "mediawiki", "json"} or not isinstance(config, dict):
                raise ValueError("Source personnelle invalide")
            serialized = json.dumps(config, ensure_ascii=False)
            if len(serialized) > 10000:
                raise ValueError("Configuration de source trop volumineuse")
            normalized_sources.append((identifier, text(item, "name", 100), kind, serialized,
                                       domain if domain in allowed_domains else "general",
                                       int(bool(item.get("enabled", True))), text(item, "created_at", 40)))

        restored_engines = {**DEFAULTS, **{key: int(bool(value)) for key, value in engines.items() if key in DEFAULTS}}
        restored_preferences = {
            "history_enabled": "1" if str(preferences.get("history_enabled", "0")) == "1" else "0",
            "cache_enabled": "1" if str(preferences.get("cache_enabled", "1")) == "1" else "0",
            "cache_ttl": str(preferences.get("cache_ttl", "900"))
            if str(preferences.get("cache_ttl", "900")) in {"300", "900", "3600"} else "900",
            "warhammer_edition": str(preferences.get("warhammer_edition", "10e"))
            if str(preferences.get("warhammer_edition", "10e")) in {"10e", "11e", "both"} else "10e",
            "rss_max_mb": str(max(1, min(20, int(preferences.get("rss_max_mb", "5")))))
            if str(preferences.get("rss_max_mb", "5")).isdigit() else "5",
            "rss_item_limit": str(max(10, min(500, int(preferences.get("rss_item_limit", "100")))))
            if str(preferences.get("rss_item_limit", "100")).isdigit() else "100",
        }
        with self.connect() as db:
            for table in ("engines", "preferences", "history", "favorites", "saved_searches",
                          "custom_feeds", "custom_sources", "search_cache", "source_health"):
                db.execute(f"DELETE FROM {table}")
            db.executemany("INSERT INTO engines(key,enabled) VALUES (?,?)", restored_engines.items())
            db.executemany("INSERT INTO preferences(key,value) VALUES (?,?)", restored_preferences.items())
            db.executemany("INSERT INTO history(query,category,searched_at) VALUES (?,?,?)", normalized_history)
            db.executemany("INSERT INTO favorites(url,title,snippet,engine,category,score,image_url,saved_at) VALUES (?,?,?,?,?,?,?,?)", normalized_favorites)
            db.executemany("INSERT INTO saved_searches(fingerprint,name,config,created_at) VALUES (?,?,?,?)", normalized_saved)
            db.executemany("INSERT INTO custom_feeds(id,name,url,language,enabled,created_at) VALUES (?,?,?,?,?,?)", normalized_feeds)
            db.executemany("INSERT INTO custom_sources(id,name,kind,config,domain,enabled,created_at) VALUES (?,?,?,?,?,?,?)", normalized_sources)
        return {key: len(value) for key, value in collections.items()}
