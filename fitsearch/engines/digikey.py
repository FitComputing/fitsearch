from .base import SearchEngine
from ..models import SearchResult


class DigiKeyEngine(SearchEngine):
    key = "digikey"
    label = "DigiKey"
    categories = {"web", "images"}
    technical = True

    async def _access_token(self, credentials: dict) -> str:
        response = await self.client.post("https://api.digikey.com/v1/oauth2/token", data={
            "client_id": credentials["client_id"], "client_secret": credentials["client_secret"],
            "grant_type": "client_credentials",
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("DigiKey n’a pas fourni de jeton d’accès")
        return token

    async def search(self, query: str, category: str, limit: int = 8):
        credentials = getattr(self, "credentials", {})
        if not credentials.get("client_id") or not credentials.get("client_secret"):
            raise RuntimeError("Identifiants DigiKey manquants")
        token = await self._access_token(credentials)
        response = await self.client.post("https://api.digikey.com/products/v4/search/keyword", json={
            "Keywords": query, "Limit": min(limit, 20), "Offset": 0,
        }, headers={"Authorization": f"Bearer {token}", "X-DIGIKEY-Client-Id": credentials["client_id"],
                    "X-DIGIKEY-Locale-Site": "FR", "X-DIGIKEY-Locale-Language": "fr",
                    "X-DIGIKEY-Locale-Currency": "EUR", "Accept": "application/json"})
        response.raise_for_status()
        products = response.json().get("Products") or response.json().get("products") or []
        results = []
        for item in products:
            manufacturer = item.get("Manufacturer") or {}
            description = item.get("Description") or {}
            title = item.get("ManufacturerProductNumber") or item.get("DigiKeyProductNumber")
            url = item.get("ProductUrl")
            if not title or not url:
                continue
            maker = manufacturer.get("Name") if isinstance(manufacturer, dict) else str(manufacturer)
            desc = description.get("ProductDescription") if isinstance(description, dict) else str(description)
            stock = item.get("QuantityAvailable")
            status = item.get("ProductStatus")
            if isinstance(status, dict):
                status = status.get("Status") or status.get("Name")
            snippet = " · ".join(str(value) for value in (maker, desc,
                f"{stock} en stock" if stock is not None else "", status) if value)
            photo = item.get("PhotoUrl") or item.get("PrimaryPhoto")
            if isinstance(photo, dict):
                photo = photo.get("Url") or photo.get("url")
            results.append(SearchResult(title, url, snippet[:1400], self.label, category, .77, photo))
        return results
