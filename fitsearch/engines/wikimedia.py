import html
import re

from .base import SearchEngine
from ..models import SearchResult


def metadata_text(metadata: dict, key: str, maximum: int = 500) -> str:
    value = (metadata.get(key) or {}).get("value", "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()[:maximum]


class WikimediaEngine(SearchEngine):
    key = "wikimedia"
    label = "Wikimedia"
    categories = {"images"}

    async def search(self, query: str, category: str, limit: int = 8):
        if category not in self.categories:
            return []
        response = await self.client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "generator": "search", "gsrsearch": query,
                    "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
                    "iiprop": "url|extmetadata", "iiurlwidth": 640,
                    "iiextmetadatafilter": "ImageDescription|Artist|Credit|LicenseShortName|LicenseUrl",
                    "format": "json"},
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {}).values()
        results = []
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            metadata = info.get("extmetadata") or {}
            url = info.get("descriptionurl")
            image = info.get("thumburl") or info.get("url")
            if url and image:
                title = page.get("title", "Image").removeprefix("File:")
                description = metadata_text(metadata, "ImageDescription", 800)
                author = metadata_text(metadata, "Artist", 300) or metadata_text(metadata, "Credit", 300)
                license_name = metadata_text(metadata, "LicenseShortName", 120)
                license_url = metadata_text(metadata, "LicenseUrl", 1000)
                results.append(SearchResult(title, url, description or "Image issue de Wikimedia Commons.",
                                            self.label, "images", .76, image,
                                            image_original_url=info.get("url"), image_author=author or None,
                                            image_license=license_name or None,
                                            image_license_url=license_url or None))
        return results
