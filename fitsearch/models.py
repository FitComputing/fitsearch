from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    engine: str
    category: str = "web"
    score: float = 0.5
    image_url: str | None = None
    published_at: str | None = None
    score_reason: str | None = None
    score_details: dict | None = None
    related: list[dict] | None = None
    image_original_url: str | None = None
    image_author: str | None = None
    image_license: str | None = None
    image_license_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
