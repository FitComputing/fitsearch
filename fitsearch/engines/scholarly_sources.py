from urllib.parse import quote_plus

from .base import SearchEngine
from .media_and_reference import ExternalSearchEngine
from ..models import SearchResult


def first_text(value, default="") -> str:
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value or default)


class HalEngine(SearchEngine):
    key, label = "hal", "HAL · Archive ouverte"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get("https://api.archives-ouvertes.fr/search/", params={
            "q": query, "wt": "json", "rows": min(limit, 50),
            "fl": "title_s,uri_s,abstract_s,authFullName_s,producedDate_s,docType_s",
            "sort": "score desc",
        })
        response.raise_for_status()
        results = []
        for document in response.json().get("response", {}).get("docs", []):
            title = first_text(document.get("title_s"))
            url = first_text(document.get("uri_s"))
            if not title or not url:
                continue
            authors = document.get("authFullName_s") or []
            if not isinstance(authors, list):
                authors = [authors]
            abstract = first_text(document.get("abstract_s"))
            date = first_text(document.get("producedDate_s"))
            kind = first_text(document.get("docType_s"))
            summary = " · ".join(value for value in (", ".join(str(a) for a in authors[:3]), date, kind)
                                 if value)
            if abstract:
                summary += (" · " if summary else "") + abstract[:360]
            published = f"{date}T00:00:00+00:00" if len(date) == 10 else None
            results.append(SearchResult(title, url, summary, self.label, "web", .76,
                                        published_at=published))
        return results


class CochraneLibraryEngine(ExternalSearchEngine):
    key, label = "cochrane", "Cochrane Library"
    categories = {"web"}
    description = "Revues systématiques et données probantes en santé · recherche externe."

    def url_for(self, query: str, category: str) -> str:
        return f"https://www.cochranelibrary.com/search?searchText={quote_plus(query)}"


class GoogleScholarEngine(ExternalSearchEngine):
    key, label = "googlescholar", "Google Scholar"
    categories = {"web"}
    search_url = "https://scholar.google.com/scholar?q={query_plus}"
    description = "Publications universitaires · recherche ouverte dans Google Scholar."


class ScienceDirectEngine(ExternalSearchEngine):
    key, label = "sciencedirect", "ScienceDirect"
    categories = {"web"}
    search_url = "https://www.sciencedirect.com/search?qs={query_plus}"
    description = "Articles et ouvrages scientifiques Elsevier · recherche externe."


class SpringerLinkEngine(ExternalSearchEngine):
    key, label = "springerlink", "SpringerLink"
    categories = {"web"}
    search_url = "https://link.springer.com/search?query={query_plus}"
    description = "Articles, chapitres et ouvrages Springer Nature · recherche externe."
