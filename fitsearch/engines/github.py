from .base import SearchEngine
from ..models import SearchResult


class GitHubEngine(SearchEngine):
    key = "github"
    label = "GitHub"
    categories = {"web"}
    technical = True

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        token = getattr(self, "credentials", {}).get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = await self.client.get("https://api.github.com/search/repositories", params={
            "q": query, "per_page": min(limit, 20), "sort": "stars",
        }, headers=headers)
        response.raise_for_status()
        results = []
        for repo in response.json().get("items", []):
            title, url = repo.get("full_name"), repo.get("html_url")
            if not title or not url:
                continue
            license_name = (repo.get("license") or {}).get("spdx_id")
            snippet = " · ".join(str(value) for value in (
                repo.get("description") or "Projet logiciel",
                repo.get("language"),
                f"★ {repo.get('stargazers_count', 0):,}".replace(",", " "),
                license_name,
            ) if value)
            results.append(SearchResult(title, url, snippet[:1200], self.label, score=.78,
                                        image_url=(repo.get("owner") or {}).get("avatar_url"),
                                        published_at=repo.get("updated_at")))
        return results
