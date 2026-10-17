import os
import re
from pathlib import Path
import httpx
import hashlib
import json
import csv
import html
import sqlite3
import subprocess
import sys
import zipfile
import time
import secrets
from collections import defaultdict, deque
from datetime import datetime, timezone
from io import StringIO
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import SettingsDB
from .search import aggregate, apply_operators, diagnose_sources, parse_operators
from .models import SearchResult
from .security import validate_public_url
from .engines.rss import CustomRssEngine
from .engines.custom_source import CustomSourceEngine
from .site_analyzer import analyze_site
from .engines import SOURCE_DOMAINS, SOURCE_LABELS
from .preview import fetch_preview, fetch_preview_image
from .updater import inspect_archive, version_tuple, write_status
from .credentials import CredentialStore, FIELDS
from .auth import AuthDB, GUEST, LOCAL_ADMIN
from .runtime import CURRENT_PRINCIPAL, CredentialProxy, DatabaseProxy, ProfileStores
from .translator import LANGUAGES, deepl_translate
from .engines import AVAILABLE_ENGINES
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DATA = Path(os.getenv("FITSEARCH_DATA", Path.home() / ".local/share/fitsearch"))
DEPLOYMENT_MODE = os.getenv("FITSEARCH_MODE", "user").strip().lower()
if DEPLOYMENT_MODE not in {"user", "system", "server"}:
    DEPLOYMENT_MODE = "user"
FITSEARCH_HOST = os.getenv("FITSEARCH_HOST", "127.0.0.1").strip() or "127.0.0.1"
try:
    FITSEARCH_PORT = max(1, min(65535, int(os.getenv("FITSEARCH_PORT", "8765"))))
except ValueError:
    FITSEARCH_PORT = 8765
AUTH_MODE = os.getenv("FITSEARCH_AUTH_MODE", "local").strip().lower()
if AUTH_MODE not in {"local", "multiuser"}:
    AUTH_MODE = "local"
MULTIUSER = AUTH_MODE == "multiuser"
profiles = ProfileStores(DATA, MULTIUSER)
auth_db = AuthDB(DATA / "auth.db") if MULTIUSER else None
db = DatabaseProxy(profiles)
credential_store = CredentialProxy(profiles)
app = FastAPI(title="FitSearch", version="2.17.6")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)


def request_principal(request: Request):
    return request.state.principal


def require_user(request: Request):
    principal = request_principal(request)
    if MULTIUSER and not principal.authenticated:
        raise HTTPException(status_code=401, detail="Connexion requise")
    return principal


def require_admin(request: Request):
    principal = require_user(request)
    if not principal.administrator:
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    return principal


@app.middleware("http")
async def authentication_context(request: Request, call_next):
    principal = LOCAL_ADMIN
    if MULTIUSER:
        principal = auth_db.principal_for_session(request.cookies.get("__Host-fitsearch_session"))
    request.state.principal = principal
    context_token = CURRENT_PRINCIPAL.set(principal)
    try:
        if MULTIUSER and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin", "")
            if origin:
                forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme).split(",", 1)[0].strip()
                expected_origin = f"{forwarded_proto}://{request.headers.get('host', request.url.netloc)}"
                if origin.rstrip("/") != expected_origin.rstrip("/"):
                    return JSONResponse({"detail": "Origine interdite"}, status_code=403)
            if request.url.path not in {"/api/auth/login"}:
                if not principal.authenticated:
                    return JSONResponse({"detail": "Connexion requise"}, status_code=401)
                supplied = request.headers.get("X-CSRF-Token", "")
                if not supplied or not secrets.compare_digest(supplied, principal.csrf_token):
                    return JSONResponse({"detail": "Jeton CSRF invalide"}, status_code=403)
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store" if request.url.path.startswith("/api/auth") else "private")
        return response
    finally:
        CURRENT_PRINCIPAL.reset(context_token)


def configured_custom_feeds(enabled_only: bool = False) -> list[dict]:
    return [{**feed, "max_bytes": db.rss_max_mb() * 1_000_000,
             "item_limit": db.rss_item_limit()} for feed in db.custom_feeds(enabled_only)]


class ExportItem(BaseModel):
    title: str = Field(max_length=500)
    url: str = Field(max_length=2000)
    snippet: str = Field(default="", max_length=2000)
    engine: str = Field(default="", max_length=100)
    category: str = Field(default="web", max_length=20)
    score: float = 0


class ExportRequest(BaseModel):
    format: str
    query: str = Field(default="", max_length=200)
    items: list[ExportItem] = Field(max_length=500)


@app.get("/api/auth/status")
async def auth_status(request: Request):
    principal = request_principal(request)
    return {"mode": AUTH_MODE, "authenticated": principal.authenticated,
            "username": principal.username, "role": principal.role,
            "csrf_token": principal.csrf_token if principal.authenticated else ""}


@app.post("/api/auth/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not MULTIUSER:
        return {"ok": True, "username": "local", "role": "admin", "csrf_token": "local"}
    address = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = LOGIN_ATTEMPTS[address]
    while attempts and attempts[0] < now - 300:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Trop de tentatives ; réessayez dans quelques minutes")
    principal = auth_db.authenticate(username, password)
    if principal is None:
        attempts.append(now)
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")
    attempts.clear()
    token, principal = auth_db.create_session(principal)
    response = JSONResponse({"ok": True, "username": principal.username,
                             "role": principal.role, "csrf_token": principal.csrf_token})
    response.set_cookie("__Host-fitsearch_session", token, max_age=12 * 60 * 60, path="/",
                        secure=True, httponly=True, samesite="lax")
    return response


@app.post("/api/auth/logout")
async def logout(request: Request):
    require_user(request)
    auth_db.delete_session(request.cookies.get("__Host-fitsearch_session"))
    response = JSONResponse({"ok": True})
    response.delete_cookie("__Host-fitsearch_session", path="/", secure=True, httponly=True, samesite="lax")
    return response


@app.post("/api/account/password")
async def change_own_password(request: Request, current_password: str = Form(...),
                              new_password: str = Form(...)):
    principal = require_user(request)
    verified = auth_db.authenticate(principal.username, current_password)
    if verified is None:
        return JSONResponse({"ok": False, "error": "Mot de passe actuel incorrect"}, status_code=400)
    try:
        auth_db.set_password(principal.user_id, new_password)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    response = JSONResponse({"ok": True, "reauthenticate": True})
    response.delete_cookie("__Host-fitsearch_session", path="/", secure=True, httponly=True, samesite="lax")
    return response


@app.get("/api/admin/users")
async def list_users(request: Request):
    require_admin(request)
    return {"items": auth_db.list_users()}


@app.post("/api/admin/users")
async def create_user(request: Request, username: str = Form(...), password: str = Form(...),
                      role: str = Form("user")):
    require_admin(request)
    try:
        identifier = auth_db.create_user(username, password, role)
        return {"ok": True, "id": identifier}
    except (ValueError, sqlite3.IntegrityError) as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@app.post("/api/admin/users/{user_id}/enabled")
async def set_user_enabled(request: Request, user_id: int, enabled: bool = Form(False)):
    principal = require_admin(request)
    if user_id == principal.user_id and not enabled:
        return JSONResponse({"ok": False, "error": "Le compte courant ne peut pas se désactiver"}, status_code=400)
    if not enabled and auth_db.is_last_active_admin(user_id):
        return JSONResponse({"ok": False, "error": "Le dernier administrateur actif ne peut pas être désactivé"}, status_code=400)
    auth_db.set_enabled(user_id, enabled)
    return {"ok": True}


@app.post("/api/admin/users/{user_id}/password")
async def admin_set_password(request: Request, user_id: int, password: str = Form(...)):
    require_admin(request)
    try:
        auth_db.set_password(user_id, password)
        return {"ok": True}
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    principal = request_principal(request)
    return templates.TemplateResponse(request, "index.html", {"app_version": app.version,
                                      "engines": db.engines(),
                                      "history_enabled": db.history_enabled(),
                                      "cache_enabled": db.cache_enabled(), "cache_ttl": db.cache_ttl(),
                                      "rss_max_mb": db.rss_max_mb(), "rss_item_limit": db.rss_item_limit(),
                                      "warhammer_edition": db.preference("warhammer_edition", "10e"),
                                      "custom_feeds": db.custom_feeds(), "custom_sources": db.custom_sources(),
                                      "source_labels": SOURCE_LABELS,
                                      "source_domains": SOURCE_DOMAINS,
                                      "deployment": {"mode": DEPLOYMENT_MODE, "host": FITSEARCH_HOST,
                                                     "port": FITSEARCH_PORT, "data": str(DATA)},
                                      "auth": {"mode": AUTH_MODE, "authenticated": principal.authenticated,
                                               "username": principal.username, "role": principal.role,
                                               "administrator": principal.administrator,
                                               "csrf_token": principal.csrf_token},
                                      "translation_languages": LANGUAGES,
                                      "credential_statuses": credential_store.statuses()})


@app.post("/api/translate")
async def translate(text: str = Form(...), target: str = Form("FR"), source: str = Form("")):
    try:
        result = await deepl_translate(text, target, credential_store.get("deepl").get("api_key", ""), source)
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


@app.get("/api/search")
async def search(q: str = "", category: str = "all", profile: str = "complete", demo: bool = False,
                 latest: bool = False,
                 period: str = "any", language: str = "any", source: str = "all", domain: str = "",
                 page: int = 1, page_size: int = 10):
    principal = CURRENT_PRINCIPAL.get()
    if MULTIUSER and not principal.authenticated:
        # Le profil invité est volontairement stable et ne peut sélectionner
        # ni sources personnelles, ni profils étendus, ni domaine arbitraire.
        profile, source, domain, latest = "encyclopedias", "all", "", False
        period, language = "any", "any"
    if latest:
        category, profile, demo = "news", "news", False
    page = max(1, min(page, 20))
    page_size = max(5, min(page_size, 20))
    fetch_limit = min(50, page * page_size + 1)
    operators = parse_operators(q[:200])
    if source == "scryfall":
        # Dans ce mode, les guillemets, les négations et les opérateurs avec
        # deux-points appartiennent à la syntaxe de recherche Scryfall.
        operators.query = q[:200].strip()
        operators.phrases = []
        operators.excluded = []
        operators.site = ""
        operators.filetype = ""
    effective_domain = operators.site[:120] or domain[:120]
    custom_feeds = configured_custom_feeds(enabled_only=True)
    custom_sources = db.custom_sources(enabled_only=True)
    cache_material = {"version": "2.17.6", "query": operators.query, "category": category, "profile": profile,
        "latest": latest,
        "engines": db.engines(), "period": period, "language": language, "source": source,
        "domain": effective_domain, "fetch_limit": fetch_limit,
        "warhammer_edition": db.preference("warhammer_edition", "10e"), "phrases": operators.phrases,
        "excluded": operators.excluded, "filetype": operators.filetype, "custom_feeds": custom_feeds,
        "custom_sources": custom_sources}
    cache_key = hashlib.sha256(json.dumps(cache_material, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cached = None if demo else db.get_cache(cache_key)
    cache_hit = cached is not None
    if cache_hit:
        results = [SearchResult(**item) for item in cached["results"]]
        warnings = cached.get("warnings", []) + ["Résultats servis depuis le cache local"]
    else:
        results, warnings, health = await aggregate(operators.query, category, profile, db.engines(), demo,
                                                    period, language, source, effective_domain, fetch_limit, custom_feeds,
                                                    custom_sources, db.preference("warhammer_edition", "10e"),
                                                    {key: credential_store.get(key) for key in FIELDS},
                                                    latest_news=latest and not operators.query)
        if health:
            db.record_source_health(health)
        results = apply_operators(results, operators)
        if not demo:
            db.set_cache(cache_key, {"results": [item.to_dict() for item in results], "warnings": warnings})
    if not results and (operators.phrases or operators.excluded or operators.filetype):
        warnings.append("Aucun résultat ne correspond aux opérateurs utilisés")
    start, end = (page - 1) * page_size, page * page_size
    page_results = results[start:end]
    if q.strip() and not demo and page == 1:
        db.add_history(q.strip()[:200], category)
    favorite_urls = db.favorite_urls([item.url for item in page_results])
    serialized_results = []
    for item in page_results:
        value = item.to_dict()
        value["favorite"] = item.url in favorite_urls
        serialized_results.append(value)
    return {"query": q, "results": serialized_results, "count": len(page_results),
            "shown": start + len(page_results), "page": page, "page_size": page_size,
            "has_more": len(results) > end, "warnings": warnings,
            "filters": {"period": period, "language": language, "source": source, "domain": effective_domain},
            "operators": {"phrases": operators.phrases, "excluded": operators.excluded,
                          "site": operators.site, "filetype": operators.filetype},
            "ranking": {"diversified": not demo and not (latest and not operators.query),
                        "latest": latest and not operators.query},
            "cache": {"hit": cache_hit, "enabled": db.cache_enabled(), "ttl": db.cache_ttl()}}


@app.get("/api/suggest")
async def suggest(q: str = "", language: str = "any"):
    query = q.strip()[:80]
    suggestions = [item["query"] for item in db.history(query, 5)]
    if len(query) >= 2:
        try:
            async with httpx.AsyncClient(timeout=2.5, headers={"User-Agent": "FitSearch/1.7"}) as client:
                wiki_language = language if language in {"fr", "en", "de", "es", "it"} else "fr"
                response = await client.get(f"https://{wiki_language}.wikipedia.org/w/api.php",
                    params={"action": "opensearch", "search": query, "limit": 7, "namespace": 0, "format": "json"})
                response.raise_for_status()
                suggestions.extend(response.json()[1])
        except (httpx.HTTPError, ValueError, IndexError):
            pass
    return {"suggestions": list(dict.fromkeys(suggestions))[:8]}


@app.get("/api/history")
async def history(request: Request):
    require_user(request)
    return {"enabled": db.history_enabled(), "items": db.history(limit=20)}


@app.post("/api/settings/history")
async def history_setting(enabled: bool = Form(False)):
    db.set_history_enabled(enabled)
    return {"ok": True, "enabled": enabled}


@app.post("/api/history/clear")
async def clear_history():
    db.clear_history()
    return {"ok": True}


@app.get("/api/cache")
async def cache_status():
    return {"enabled": db.cache_enabled(), "ttl": db.cache_ttl(), **db.cache_stats()}


@app.post("/api/settings/cache")
async def cache_setting(enabled: bool = Form(True), ttl: int = Form(900)):
    ttl = ttl if ttl in {300, 900, 3600} else 900
    old_ttl = db.cache_ttl()
    db.set_preference("cache_enabled", "1" if enabled else "0")
    db.set_preference("cache_ttl", str(ttl))
    if not enabled or ttl != old_ttl:
        db.clear_cache()
    return {"ok": True, "enabled": enabled, "ttl": ttl}


@app.post("/api/settings/rss")
async def rss_setting(max_mb: int = Form(5), item_limit: int = Form(100)):
    max_mb = max(1, min(20, max_mb))
    item_limit = max(10, min(500, item_limit))
    db.set_preference("rss_max_mb", str(max_mb))
    db.set_preference("rss_item_limit", str(item_limit))
    db.clear_cache()
    return {"ok": True, "max_mb": max_mb, "item_limit": item_limit}


@app.post("/api/settings/warhammer")
async def warhammer_setting(edition: str = Form("10e")):
    edition = edition if edition in {"10e", "11e", "both"} else "10e"
    db.set_preference("warhammer_edition", edition)
    db.clear_cache()
    return {"ok": True, "edition": edition}


@app.post("/api/cache/clear")
async def clear_cache():
    db.clear_cache()
    return {"ok": True}


@app.get("/api/favorites")
async def favorites(request: Request):
    require_user(request)
    items = db.favorites()
    return {"items": items, "count": len(items)}


@app.post("/api/favorites")
async def add_favorite(url: str = Form(...), title: str = Form(...), snippet: str = Form(""),
                       engine: str = Form(""), category: str = Form("web"), score: float = Form(0),
                       image_url: str = Form("")):
    if not url.startswith(("http://", "https://")):
        return {"ok": False}
    db.add_favorite({"url": url[:2000], "title": title[:500], "snippet": snippet[:1000],
                     "engine": engine[:100], "category": category[:20], "score": score,
                     "image_url": image_url[:2000]})
    return {"ok": True}


@app.post("/api/favorites/remove")
async def remove_favorite(url: str = Form(...)):
    db.remove_favorite(url[:2000])
    return {"ok": True}


@app.post("/api/export")
async def export_results(payload: ExportRequest):
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", payload.query.strip()).strip("-")[:40] or "resultats"
    items = [item for item in payload.items if item.url.startswith(("http://", "https://"))]
    if payload.format == "markdown":
        lines = [f"# Résultats FitSearch — {payload.query or 'Recherche'}", "", f"Exporté le {generated}", ""]
        for item in items:
            title = item.title.replace("[", "\\[").replace("]", "\\]")
            lines.extend([f"## [{title}]({item.url})", "", f"**Source :** {item.engine} · **Score :** {round(item.score * 100)}/100", "", item.snippet, ""])
        content, media, ext = "\n".join(lines), "text/markdown; charset=utf-8", "md"
    elif payload.format == "csv":
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["Titre", "URL", "Résumé", "Source", "Catégorie", "Score"])
        def csv_safe(value):
            text = str(value)
            return "'" + text if text.startswith(("=", "+", "-", "@")) else text
        for item in items:
            writer.writerow([csv_safe(item.title), item.url, csv_safe(item.snippet), csv_safe(item.engine),
                             csv_safe(item.category), round(item.score * 100)])
        content, media, ext = "\ufeff" + output.getvalue(), "text/csv; charset=utf-8", "csv"
    elif payload.format == "html":
        entries = []
        timestamp = int(datetime.now(timezone.utc).timestamp())
        for item in items:
            entries.append(f'<DT><A HREF="{html.escape(item.url, quote=True)}" ADD_DATE="{timestamp}">{html.escape(item.title)}</A>')
            if item.snippet:
                entries.append(f"<DD>{html.escape(item.snippet)} — {html.escape(item.engine)}")
        content = "\n".join(["<!DOCTYPE NETSCAPE-Bookmark-file-1>", '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Favoris FitSearch</TITLE>", "<H1>Favoris FitSearch</H1>", "<DL><p>", *entries, "</DL><p>"])
        media, ext = "text/html; charset=utf-8", "html"
    else:
        return Response("Format non pris en charge", status_code=400, media_type="text/plain")
    headers = {"Content-Disposition": f'attachment; filename="fitsearch-{safe_name}.{ext}"'}
    return Response(content, media_type=media, headers=headers)


@app.get("/api/saved-searches")
async def saved_searches(request: Request):
    require_user(request)
    items = db.saved_searches()
    return {"items": items, "count": len(items)}


@app.post("/api/saved-searches")
async def save_search(name: str = Form(...), query: str = Form(...), category: str = Form("all"),
                      profile: str = Form("complete"), demo: bool = Form(False), latest: bool = Form(False),
                      period: str = Form("any"),
                      language: str = Form("any"), source: str = Form("all"), domain: str = Form("")):
    config = {"query": query[:200], "category": category[:20], "profile": profile[:20], "demo": demo,
              "latest": latest,
              "period": period[:20], "language": language[:10], "source": source[:50], "domain": domain[:120]}
    identifier = db.save_search((name.strip() or query.strip() or "Recherche")[:100], config)
    return {"ok": True, "id": identifier}


@app.post("/api/saved-searches/remove")
async def remove_saved_search(identifier: int = Form(...)):
    db.remove_saved_search(identifier)
    return {"ok": True}


@app.get("/api/custom-feeds")
async def custom_feeds(request: Request):
    require_user(request)
    items = db.custom_feeds()
    return {"items": items, "count": len(items)}


@app.post("/api/custom-feeds")
async def add_custom_feed(name: str = Form(...), url: str = Form(...), language: str = Form("fr")):
    language = language if language in {"fr", "en", "de", "es", "it"} else "fr"
    try:
        safe_url = await validate_public_url(url[:2000])
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "FitSearch/2.14.4"}) as client:
            probe = CustomRssEngine(client, {"id": 0, "name": name[:100] or "Flux personnalisé",
                                             "url": safe_url, "language": language,
                                             "max_bytes": db.rss_max_mb() * 1_000_000,
                                             "item_limit": db.rss_item_limit()})
            await probe.search("", "news", 1)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
    identifier = db.add_custom_feed((name.strip() or urlsplit(safe_url).hostname or "Flux")[:100], safe_url, language)
    db.clear_cache()
    return {"ok": True, "id": identifier}


@app.post("/api/custom-feeds/toggle")
async def toggle_custom_feed(identifier: int = Form(...), enabled: bool = Form(False)):
    db.set_custom_feed(identifier, enabled)
    db.clear_cache()
    return {"ok": True}


@app.post("/api/custom-feeds/remove")
async def remove_custom_feed(identifier: int = Form(...)):
    db.remove_custom_feed(identifier)
    db.clear_cache()
    return {"ok": True}


@app.get("/api/custom-sources")
async def custom_sources(request: Request):
    require_user(request)
    items = db.custom_sources()
    return {"items": items, "count": len(items)}


@app.post("/api/custom-sources/analyze")
async def analyze_custom_source(url: str = Form(...)):
    try:
        return {"ok": True, **await analyze_site(url.strip()[:2000])}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


@app.post("/api/custom-sources")
async def add_custom_source(name: str = Form(...), kind: str = Form(...), endpoint: str = Form(...),
                            domain: str = Form("general"), categories: str = Form("web"),
                            query_param: str = Form("q"), list_path: str = Form(""),
                            title_path: str = Form("title"), url_path: str = Form("url"),
                            snippet_path: str = Form("description"), image_path: str = Form("")):
    if kind not in {"external", "mediawiki", "json"}:
        return {"ok": False, "error": "Type de source non pris en charge"}
    if domain not in {"general", "science", "culture", "technology", "nature", "society", "leisure"}:
        domain = "general"
    selected_categories = [value for value in categories.split(",")
                           if value in {"web", "images", "videos", "news", "books"}]
    if not selected_categories:
        selected_categories = ["web"]
    try:
        safe_endpoint = await validate_public_url(endpoint.strip()[:2000])
        config = {"endpoint": safe_endpoint, "categories": selected_categories,
                  "query_param": (query_param.strip() or "q")[:80]}
        if kind == "json":
            config.update({"list_path": list_path.strip()[:200], "title_path": (title_path.strip() or "title")[:200],
                           "url_path": (url_path.strip() or "url")[:200],
                           "snippet_path": snippet_path.strip()[:200], "image_path": image_path.strip()[:200]})
        source = {"id": 0, "name": (name.strip() or urlsplit(safe_endpoint).hostname or "Ma source")[:100],
                  "kind": kind, "config": config, "domain": domain, "enabled": True}
        async with httpx.AsyncClient(timeout=8, follow_redirects=True,
                                     headers={"User-Agent": "FitSearch/2.14 (personal source test)"}) as client:
            await CustomSourceEngine(client, source).search("open source", selected_categories[0], 1)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
    identifier = db.add_custom_source(source["name"], kind, config, domain)
    db.clear_cache()
    return {"ok": True, "id": identifier}


@app.post("/api/custom-sources/toggle")
async def toggle_custom_source(identifier: int = Form(...), enabled: bool = Form(False)):
    db.set_custom_source(identifier, enabled)
    db.clear_cache()
    return {"ok": True}


@app.post("/api/custom-sources/remove")
async def remove_custom_source(identifier: int = Form(...)):
    db.remove_custom_source(identifier)
    db.clear_cache()
    return {"ok": True}


@app.get("/api/preview")
async def preview(url: str):
    try:
        return {"ok": True, **await fetch_preview(url[:2000])}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


@app.get("/api/preview-image")
async def preview_image(url: str):
    try:
        content, content_type = await fetch_preview_image(url[:2000])
        return Response(content, media_type=content_type, headers={
            "Cache-Control": "private, max-age=600", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
        })
    except Exception:
        return Response(status_code=404)


@app.get("/api/backup")
async def backup(request: Request):
    require_user(request)
    payload = {**db.backup(), "created_at": datetime.now(timezone.utc).isoformat()}
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    return Response(content, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="fitsearch-sauvegarde-{stamp}.json"'})


@app.post("/api/restore")
async def restore(file: UploadFile = File(...)):
    raw = await file.read(2_000_001)
    if len(raw) > 2_000_000:
        return {"ok": False, "error": "Le fichier dépasse la limite de 2 Mo"}
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("Structure de sauvegarde invalide")
        counts = db.restore(payload)
        return {"ok": True, "counts": counts}
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, sqlite3.Error) as exc:
        return {"ok": False, "error": str(exc)[:200]}


@app.get("/api/update-status")
async def update_status():
    if DEPLOYMENT_MODE == "system":
        return {"phase": "managed", "message": "Installation système : mise à jour avec sudo ./install.sh system",
                "version": app.version}
    status_file = DATA / "update-status.json"
    if not status_file.exists():
        return {"phase": "idle", "message": "Aucune mise à jour en cours", "version": app.version}
    try:
        return json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"phase": "idle", "message": "État indisponible", "version": app.version}


@app.post("/api/update")
async def update(file: UploadFile = File(...)):
    if DEPLOYMENT_MODE != "user":
        return {"ok": False, "error": "En mode système, installez la nouvelle archive avec sudo ./install.sh system"}
    app_dir = DATA / "app"
    if not (app_dir / ".venv/bin/pip").is_file():
        return {"ok": False, "error": "Cette fonction nécessite l’installation locale de FitSearch"}
    current_status = await update_status()
    if current_status.get("phase") in {"queued", "installing"}:
        return {"ok": False, "error": "Une mise à jour est déjà en cours"}
    raw = await file.read(10_000_001)
    if len(raw) > 10_000_000:
        return {"ok": False, "error": "L’archive dépasse la limite de 10 Mo"}
    updates = DATA / "updates"
    updates.mkdir(parents=True, exist_ok=True)
    archive = updates / "fitsearch-pending.zip"
    archive.write_bytes(raw)
    try:
        info = inspect_archive(archive)
        if version_tuple(info["version"]) < version_tuple(app.version):
            raise ValueError("Cette archive contient une version plus ancienne")
        write_status(DATA, "queued", f"FitSearch {info['version']} a été vérifié. Installation imminente…",
                     version=info["version"])
        subprocess.Popen([sys.executable, str(BASE / "updater.py"), str(archive), str(DATA)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return {"ok": True, "version": info["version"]}
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        archive.unlink(missing_ok=True)
        return {"ok": False, "error": str(exc)[:200]}


@app.post("/api/settings/engine")
async def engine_setting(key: str = Form(...), enabled: bool = Form(False)):
    if key not in db.engines():
        return {"ok": False}
    if enabled and key in {"tmdb", "europeana", "discogs", "digikey"} \
            and not credential_store.statuses()[key]["configured"]:
        return {"ok": False, "error": "Renseignez et testez d’abord les identifiants de cette source"}
    db.set_engine(key, enabled)
    return {"ok": True, "engines": db.engines()}


@app.get("/api/credentials")
async def credential_status(request: Request):
    require_user(request)
    return {"sources": credential_store.statuses()}


@app.post("/api/credentials/{source}")
async def save_credentials(source: str, token: str = Form(""), api_key: str = Form(""),
                           client_id: str = Form(""), client_secret: str = Form("")):
    if source not in FIELDS:
        return {"ok": False, "error": "Source inconnue"}
    values = {"token": token, "api_key": api_key, "client_id": client_id, "client_secret": client_secret}
    previous = credential_store.get(source)
    try:
        credential_store.set(source, values)
        credentials = credential_store.get(source)
        if source == "deepl":
            result = await deepl_translate("Bonjour", "EN", credentials.get("api_key", ""))
            return {"ok": True, "configured": True,
                    "message": f"Connexion réussie · test : {result['text']}"}
        engine = AVAILABLE_ENGINES[source](httpx.AsyncClient(timeout=9, follow_redirects=True,
            headers={"User-Agent": "FitSearch/2.12 (credential test)"}))
        engine.credentials = credentials
        engine.language = "fr"
        test_query = {"tmdb": "Pythagore", "europeana": "Monet", "discogs": "Miles Davis",
                      "digikey": "NE555", "github": "fastapi"}[source]
        try:
            results = await engine.search(test_query, "web", 1)
        finally:
            await engine.client.aclose()
        if not results:
            raise RuntimeError("Connexion acceptée, mais aucun résultat de test n’a été retourné")
        if source != "github":
            db.set_engine(source, True)
        db.clear_cache()
        configured = credential_store.statuses()[source]["configured"]
        message = "Connexion réussie · source activée" if configured else "GitHub répond · mode public sans clé"
        return {"ok": True, "configured": configured, "message": message}
    except Exception as exc:
        if previous and all(previous.values()):
            credential_store.set(source, previous)
        else:
            credential_store.delete(source)
        return {"ok": False, "configured": False, "error": str(exc)[:200]}


@app.post("/api/credentials/{source}/remove")
async def remove_credentials(source: str):
    if source not in FIELDS:
        return {"ok": False}
    credential_store.delete(source)
    if source not in {"github", "deepl"}:
        db.set_engine(source, False)
    db.clear_cache()
    return {"ok": True}


def health_payload():
    items = db.source_health()
    active = [item for item in items if item["status"] != "disabled"]
    measured = [item for item in active if item["status"] != "unknown"]
    if measured and all(item["status"] == "error" for item in measured):
        overall = "down"
    elif any(item["status"] in {"error", "slow", "empty"} for item in measured):
        overall = "warning"
    elif measured:
        overall = "healthy"
    else:
        overall = "unknown"
    return {"overall": overall, "items": items, "counts": {
        status: sum(item["status"] == status for item in items)
        for status in ("ok", "slow", "empty", "error", "unknown", "disabled")}}


@app.get("/api/source-health")
async def source_health():
    return health_payload()


@app.post("/api/source-health/test")
async def test_source_health():
    measurements = await diagnose_sources(db.engines(), configured_custom_feeds(enabled_only=True),
                                           db.custom_sources(enabled_only=True),
                                           {key: credential_store.get(key) for key in FIELDS})
    if measurements:
        db.record_source_health(measurements)
    return {"ok": True, **health_payload()}


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version, "mode": DEPLOYMENT_MODE}


@app.get("/api/deployment")
async def deployment():
    return {"mode": DEPLOYMENT_MODE, "host": FITSEARCH_HOST, "port": FITSEARCH_PORT,
            "data": str(DATA), "network_exposed": FITSEARCH_HOST not in {"127.0.0.1", "localhost", "::1"}}


def run():
    import uvicorn
    if DEPLOYMENT_MODE == "server":
        raise RuntimeError("Le mode serveur réseau nécessite l’authentification prévue pour FitSearch V2.17")
    host = FITSEARCH_HOST if FITSEARCH_HOST in {"127.0.0.1", "localhost", "::1"} else "127.0.0.1"
    uvicorn.run("fitsearch.main:app", host=host, port=FITSEARCH_PORT)
