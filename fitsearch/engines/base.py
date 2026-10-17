from abc import ABC, abstractmethod

import httpx

from ..models import SearchResult


class SearchEngine(ABC):
    key = "base"
    label = "Base"
    categories = {"web"}
    privacy_friendly = True
    technical = False

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.language = "any"

    @abstractmethod
    async def search(self, query: str, category: str, limit: int = 8) -> list[SearchResult]:
        raise NotImplementedError
