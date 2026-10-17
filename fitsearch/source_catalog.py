"""Matrice centrale des profils de recherche FitSearch.

Les types de contenus restent déclarés par chaque adaptateur ; cette matrice dit
dans quels profils éditoriaux une source doit apparaître.
"""

PROFILE_LABELS = {
    "complete": "Complet",
    "encyclopedias": "Encyclopédies",
    "news": "News/RSS",
    "technology": "Technologies",
    "media": "Médias",
}

SOURCE_PROFILES = {
    "wikipedia": {"complete", "encyclopedias", "technology"},
    "wikidata": {"complete", "encyclopedias", "technology"},
    "wikimedia": {"complete", "encyclopedias", "media"},
    "warhammerwiki": {"complete", "encyclopedias"},
    "hackernews": {"complete", "news", "technology"},
    "lemonde": {"complete", "news"},
    "guardian": {"complete", "news"},
    "bbc": {"complete", "news"},
    "stackoverflow": {"complete", "technology"},
    "electronics": {"complete", "technology"},
    "superuser": {"complete", "technology"},
    "unixlinux": {"complete", "technology"},
    "github": {"complete", "technology"},
    "digikey": {"complete", "technology"},
    "arxiv": {"complete", "technology"},
    "openalex": {"complete", "technology"},
    "crossref": {"complete", "technology"},
    "openlibrary": {"complete"},
    "internetarchive": {"complete", "media"},
    "pubmed": {"complete"},
    "gbif": {"complete"},
    "musicbrainz": {"complete", "media"},
    "moviestv": {"complete", "media"},
    "scryfall": {"complete"},
    "openhammer": {"complete"},
    "tmdb": {"complete", "media"},
    "europeana": {"complete", "media"},
    "discogs": {"complete", "media"},
    "unsplash": {"complete", "media"},
    "pexels": {"complete", "media"},
    "pixabay": {"complete", "media"},
    "burst": {"complete", "media"},
    "gratisography": {"complete", "media"},
    "flickrcc": {"complete", "media"},
    "reshot": {"complete", "media"},
    "scholarpedia": {"complete", "encyclopedias", "technology"},
    "universalis": {"complete", "encyclopedias"},
    "universalis_media": {"complete", "encyclopedias", "media"},
    "freedictionary": {"complete", "encyclopedias"},
    "larousse": {"complete", "encyclopedias"},
    "larousse_encyclopedia": {"complete", "encyclopedias"},
    "lalanguefrancaise": {"complete", "encyclopedias"},
    "hal": {"complete", "technology"},
    "cochrane": {"complete", "technology"},
    "googlescholar": {"complete", "technology"},
    "sciencedirect": {"complete", "technology"},
    "springerlink": {"complete", "technology"},
}


def sources_for_profile(profile: str) -> set[str]:
    # Compatibilité transparente avec les recherches enregistrées avant V2.15.
    profile = {"quick": "complete", "private": "encyclopedias",
               "technical": "technology"}.get(profile, profile)
    if profile not in PROFILE_LABELS:
        profile = "complete"
    return {key for key, profiles in SOURCE_PROFILES.items() if profile in profiles}
