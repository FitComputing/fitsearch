import json
import os
from pathlib import Path


FIELDS = {
    "tmdb": ("token",),
    "europeana": ("api_key",),
    "discogs": ("token",),
    "digikey": ("client_id", "client_secret"),
    "github": ("token",),
    "deepl": ("api_key",),
}


class CredentialStore:
    """Petit coffre local séparé de SQLite et volontairement absent des sauvegardes."""

    def __init__(self, path: Path):
        self.path = path

    def _read(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, value: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, self.path)
        self.path.chmod(0o600)

    def get(self, source: str) -> dict[str, str]:
        raw = self._read().get(source, {})
        if not isinstance(raw, dict):
            return {}
        return {key: str(raw.get(key, "")).strip() for key in FIELDS.get(source, ())}

    def set(self, source: str, values: dict[str, str]):
        if source not in FIELDS:
            raise ValueError("Source inconnue")
        data = self._read()
        cleaned = {key: str(values.get(key, "")).strip() for key in FIELDS[source]}
        if source == "github" and not cleaned.get("token"):
            data.pop(source, None)
        elif not all(cleaned.values()):
            raise ValueError("Tous les champs obligatoires doivent être renseignés")
        else:
            data[source] = cleaned
        self._write(data)

    def delete(self, source: str):
        data = self._read()
        data.pop(source, None)
        self._write(data)

    def statuses(self) -> dict[str, dict]:
        data = self._read()
        result = {}
        for source, fields in FIELDS.items():
            values = data.get(source, {}) if isinstance(data.get(source), dict) else {}
            configured = all(bool(str(values.get(field, "")).strip()) for field in fields)
            result[source] = {"configured": configured, "optional": source == "github"}
        return result
