import contextvars
import shutil
from pathlib import Path

from .auth import GUEST, LOCAL_ADMIN, Principal
from .credentials import CredentialStore
from .db import SettingsDB


CURRENT_PRINCIPAL = contextvars.ContextVar("fitsearch_principal", default=GUEST)


class ProfileStores:
    def __init__(self, data_dir: Path, multiuser: bool):
        self.data_dir = data_dir
        self.multiuser = multiuser
        self._databases: dict[str, SettingsDB] = {}
        self._credentials: dict[str, CredentialStore] = {}

    def profiles_root(self) -> Path:
        root = self.data_dir / "profiles"
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        return root

    def profile_dir(self, principal: Principal) -> Path:
        if not self.multiuser:
            return self.data_dir
        return self.profiles_root() / principal.profile_key

    def database(self, principal: Principal | None = None) -> SettingsDB:
        principal = principal or CURRENT_PRINCIPAL.get()
        key = principal.profile_key if self.multiuser else "local"
        if key not in self._databases:
            directory = self.profile_dir(principal)
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
            self._databases[key] = SettingsDB(directory / "fitsearch.db")
            (directory / "fitsearch.db").chmod(0o600)
        return self._databases[key]

    def credential_store(self, principal: Principal | None = None) -> CredentialStore:
        principal = principal or CURRENT_PRINCIPAL.get()
        key = principal.profile_key if self.multiuser else "local"
        if key not in self._credentials:
            directory = self.profile_dir(principal)
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
            self._credentials[key] = CredentialStore(directory / "credentials.json")
        return self._credentials[key]

    def migrate_legacy_profile(self, principal: Principal):
        if not self.multiuser or not principal.authenticated:
            return
        destination = self.profile_dir(principal)
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination.chmod(0o700)
        for name in ("fitsearch.db", "credentials.json"):
            source = self.data_dir / name
            target = destination / name
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)
                target.chmod(0o600)


class DatabaseProxy:
    def __init__(self, profiles: ProfileStores):
        self.profiles = profiles

    def __getattr__(self, name):
        return getattr(self.profiles.database(), name)


class CredentialProxy:
    def __init__(self, profiles: ProfileStores):
        self.profiles = profiles

    def __getattr__(self, name):
        return getattr(self.profiles.credential_store(), name)


def local_principal() -> Principal:
    return LOCAL_ADMIN
