import httpx


LANGUAGES = {
    "AR": "Arabe", "BG": "Bulgare", "CS": "Tchèque", "DA": "Danois", "DE": "Allemand",
    "EL": "Grec", "EN": "Anglais", "ES": "Espagnol", "ET": "Estonien", "FI": "Finnois",
    "FR": "Français", "HU": "Hongrois", "ID": "Indonésien", "IT": "Italien", "JA": "Japonais",
    "KO": "Coréen", "LT": "Lituanien", "LV": "Letton", "NB": "Norvégien", "NL": "Néerlandais",
    "PL": "Polonais", "PT": "Portugais", "RO": "Roumain", "RU": "Russe", "SK": "Slovaque",
    "SL": "Slovène", "SV": "Suédois", "TR": "Turc", "UK": "Ukrainien", "ZH": "Chinois",
}


async def deepl_translate(text: str, target: str, api_key: str, source: str = "",
                         client: httpx.AsyncClient | None = None) -> dict:
    value = text.strip()
    target = target.upper()
    source = source.upper()
    if not value:
        raise ValueError("Saisissez un mot ou une expression à traduire")
    if len(value) > 5000:
        raise ValueError("Le texte est limité à 5 000 caractères")
    if target not in LANGUAGES:
        raise ValueError("Langue cible non prise en charge")
    if source and source not in LANGUAGES:
        raise ValueError("Langue source non prise en charge")
    key = api_key.strip()
    if not key:
        raise ValueError("Clé DeepL non configurée")
    endpoint = ("https://api-free.deepl.com/v2/translate" if key.endswith(":fx")
                else "https://api.deepl.com/v2/translate")
    payload = {"text": [value], "target_lang": target}
    if source:
        payload["source_lang"] = source
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=15)
    try:
        response = await client.post(endpoint, json=payload,
                                     headers={"Authorization": f"DeepL-Auth-Key {key}"})
        if response.status_code in {401, 403}:
            raise ValueError("Clé DeepL refusée")
        if response.status_code == 456:
            raise ValueError("Quota DeepL épuisé")
        response.raise_for_status()
        translations = response.json().get("translations") or []
        if not translations or not translations[0].get("text"):
            raise ValueError("DeepL n’a retourné aucune traduction")
        item = translations[0]
        return {"text": item["text"], "detected_source_language": item.get("detected_source_language", ""),
                "target_language": target, "provider": "DeepL API"}
    finally:
        if owns_client:
            await client.aclose()
