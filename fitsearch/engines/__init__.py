from .hackernews import HackerNewsEngine
from .wikipedia import WikipediaEngine
from .wikimedia import WikimediaEngine
from .openlibrary import OpenLibraryEngine
from .stackoverflow import StackOverflowEngine
from .arxiv import ArxivEngine
from .rss import BbcEngine, GuardianEngine, LeMondeEngine
from .wikidata import WikidataEngine
from .openalex import OpenAlexEngine
from .crossref import CrossrefEngine
from .pubmed import PubMedEngine
from .gbif import GbifEngine
from .musicbrainz import MusicBrainzEngine
from .scryfall import ScryfallEngine
from .openhammer import OpenHammerEngine
from .warhammer_wiki import WarhammerWikiEngine
from .github import GitHubEngine
from .tmdb import TmdbEngine
from .europeana import EuropeanaEngine
from .discogs import DiscogsEngine
from .digikey import DigiKeyEngine
from .internetarchive import InternetArchiveEngine
from .lalanguefrancaise import LaLangueFrancaiseEngine
from .larousse import LarousseDictionaryEngine, LarousseEncyclopediaEngine
from .media_and_reference import (BurstEngine, FlickrCcEngine, FreeDictionaryEngine,
                                  GratisographyEngine, PexelsEngine,
                                  PixabayEngine, ReshotEngine, ScholarpediaEngine,
                                  UniversalisEngine, UniversalisMediaEngine, UnsplashEngine)
from .scholarly_sources import (CochraneLibraryEngine, GoogleScholarEngine, HalEngine,
                                ScienceDirectEngine, SpringerLinkEngine)
from .stackexchange_network import (ElectricalEngineeringEngine, MoviesTvEngine,
                                    SuperUserEngine, UnixLinuxEngine)

AVAILABLE_ENGINES = {
    "wikipedia": WikipediaEngine,
    "wikimedia": WikimediaEngine,
    "hackernews": HackerNewsEngine,
    "openlibrary": OpenLibraryEngine,
    "stackoverflow": StackOverflowEngine,
    "arxiv": ArxivEngine,
    "lemonde": LeMondeEngine,
    "guardian": GuardianEngine,
    "bbc": BbcEngine,
    "wikidata": WikidataEngine,
    "openalex": OpenAlexEngine,
    "crossref": CrossrefEngine,
    "pubmed": PubMedEngine,
    "gbif": GbifEngine,
    "musicbrainz": MusicBrainzEngine,
    "electronics": ElectricalEngineeringEngine,
    "superuser": SuperUserEngine,
    "unixlinux": UnixLinuxEngine,
    "moviestv": MoviesTvEngine,
    "scryfall": ScryfallEngine,
    "openhammer": OpenHammerEngine,
    "warhammerwiki": WarhammerWikiEngine,
    "github": GitHubEngine,
    "tmdb": TmdbEngine,
    "europeana": EuropeanaEngine,
    "discogs": DiscogsEngine,
    "digikey": DigiKeyEngine,
    "internetarchive": InternetArchiveEngine,
    "unsplash": UnsplashEngine,
    "pexels": PexelsEngine,
    "pixabay": PixabayEngine,
    "burst": BurstEngine,
    "gratisography": GratisographyEngine,
    "flickrcc": FlickrCcEngine,
    "reshot": ReshotEngine,
    "scholarpedia": ScholarpediaEngine,
    "universalis": UniversalisEngine,
    "universalis_media": UniversalisMediaEngine,
    "freedictionary": FreeDictionaryEngine,
    "larousse": LarousseDictionaryEngine,
    "larousse_encyclopedia": LarousseEncyclopediaEngine,
    "lalanguefrancaise": LaLangueFrancaiseEngine,
    "hal": HalEngine,
    "cochrane": CochraneLibraryEngine,
    "googlescholar": GoogleScholarEngine,
    "sciencedirect": ScienceDirectEngine,
    "springerlink": SpringerLinkEngine,
}

SOURCE_LABELS = {key: engine.label for key, engine in AVAILABLE_ENGINES.items()} | {
    "brave": "Brave Search API", "duckduckgo": "DuckDuckGo HTML",
}

SOURCE_DOMAINS = {
    "wikipedia": {"general", "science", "culture", "nature", "society", "leisure"},
    "wikidata": {"general", "science", "culture", "nature", "society", "leisure"},
    "wikimedia": {"general", "culture", "nature", "leisure"},
    "hackernews": {"technology", "society"},
    "openlibrary": {"culture", "leisure"}, "musicbrainz": {"culture"},
    "moviestv": {"culture", "leisure"}, "scryfall": {"leisure"},
    "openhammer": {"leisure"}, "warhammerwiki": {"leisure"},
    "stackoverflow": {"technology"}, "electronics": {"technology"},
    "superuser": {"technology"}, "unixlinux": {"technology"},
    "arxiv": {"science"}, "openalex": {"science"}, "crossref": {"science"},
    "pubmed": {"science"}, "gbif": {"nature", "science"},
    "lemonde": {"society"}, "guardian": {"society"}, "bbc": {"society"},
    "brave": {"general"}, "duckduckgo": {"general"},
    "github": {"technology"}, "tmdb": {"culture", "leisure"},
    "europeana": {"culture"}, "discogs": {"culture"}, "digikey": {"technology"},
    "internetarchive": {"culture", "leisure"},
    "unsplash": {"culture"}, "pexels": {"culture"}, "pixabay": {"culture"},
    "burst": {"culture"}, "gratisography": {"culture"}, "flickrcc": {"culture"},
    "reshot": {"culture"}, "scholarpedia": {"science", "culture"},
    "universalis": {"general", "culture"}, "universalis_media": {"culture"},
    "freedictionary": {"general", "culture"},
    "larousse": {"general", "culture"}, "larousse_encyclopedia": {"general", "culture"},
    "lalanguefrancaise": {"general", "culture"},
    "hal": {"science"}, "cochrane": {"science"}, "googlescholar": {"science"},
    "sciencedirect": {"science"}, "springerlink": {"science"},
}
