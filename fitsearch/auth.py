import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


SESSION_TTL = 12 * 60 * 60
PASSWORD_HASHER = PasswordHasher()


@dataclass(frozen=True)
class Principal:
    user_id: int | None
    username: str
    role: str
    csrf_token: str = ""

    @property
    def authenticated(self) -> bool:
        return self.user_id is not None

    @property
    def administrator(self) -> bool:
        return self.role == "admin"

    @property
    def profile_key(self) -> str:
        return f"user-{self.user_id}" if self.authenticated else "guest"


GUEST = Principal(None, "invite", "guest")
LOCAL_ADMIN = Principal(0, "local", "admin", "local")


class AuthDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE, "
                "password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','user')), "
                "enabled INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, "
                "updated_at INTEGER NOT NULL, last_login_at INTEGER)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                "token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, csrf_token TEXT NOT NULL, "
                "created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, "
                "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)"
            )
            db.execute("CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)")
        self.path.chmod(0o600)

    def connect(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def normalize_username(username: str) -> str:
        value = username.strip().lower()
        if not (3 <= len(value) <= 40):
            raise ValueError("Le nom doit contenir entre 3 et 40 caractères")
        if not value[0].isalnum() or any(not (char.isalnum() or char in "._-") for char in value):
            raise ValueError("Le nom contient un caractère non autorisé")
        return value

    @staticmethod
    def validate_password(password: str):
        if len(password) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caractères")
        if len(password) > 256:
            raise ValueError("Le mot de passe est trop long")

    def count_users(self) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def create_user(self, username: str, password: str, role: str = "user") -> int:
        username = self.normalize_username(username)
        self.validate_password(password)
        if role not in {"admin", "user"}:
            raise ValueError("Rôle inconnu")
        now = int(time.time())
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO users(username,password_hash,role,created_at,updated_at) VALUES (?,?,?,?,?)",
                (username, PASSWORD_HASHER.hash(password), role, now, now),
            )
            return int(cursor.lastrowid)

    def authenticate(self, username: str, password: str) -> Principal | None:
        try:
            username = self.normalize_username(username)
        except ValueError:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT id,username,password_hash,role,enabled FROM users WHERE username=?",
                (username,),
            ).fetchone()
        if not row or not row[4]:
            PASSWORD_HASHER.hash(password or "invalid-password")
            return None
        try:
            PASSWORD_HASHER.verify(row[2], password)
        except (VerifyMismatchError, InvalidHashError):
            return None
        now = int(time.time())
        with self.connect() as db:
            db.execute("UPDATE users SET last_login_at=?,updated_at=? WHERE id=?", (now, now, row[0]))
            if PASSWORD_HASHER.check_needs_rehash(row[2]):
                db.execute("UPDATE users SET password_hash=? WHERE id=?", (PASSWORD_HASHER.hash(password), row[0]))
        return Principal(int(row[0]), row[1], row[3])

    def create_session(self, principal: Principal) -> tuple[str, Principal]:
        if not principal.authenticated:
            raise ValueError("Compte requis")
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        now = int(time.time())
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?)",
                (hashlib.sha256(token.encode()).hexdigest(), principal.user_id, csrf, now, now + SESSION_TTL),
            )
        return token, Principal(principal.user_id, principal.username, principal.role, csrf)

    def principal_for_session(self, token: str | None) -> Principal:
        if not token:
            return GUEST
        now = int(time.time())
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            row = db.execute(
                "SELECT u.id,u.username,u.role,s.csrf_token FROM sessions s "
                "JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.enabled=1",
                (digest, now),
            ).fetchone()
        return Principal(int(row[0]), row[1], row[2], row[3]) if row else GUEST

    def delete_session(self, token: str | None):
        if not token:
            return
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

    def list_users(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,username,role,enabled,created_at,last_login_at FROM users ORDER BY username"
            ).fetchall()
        keys = ("id", "username", "role", "enabled", "created_at", "last_login_at")
        return [{**dict(zip(keys, row)), "enabled": bool(row[3])} for row in rows]

    def is_last_active_admin(self, user_id: int) -> bool:
        with self.connect() as db:
            row = db.execute("SELECT role,enabled FROM users WHERE id=?", (user_id,)).fetchone()
            count = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND enabled=1").fetchone()[0]
        return bool(row and row[0] == "admin" and row[1] and count <= 1)

    def set_enabled(self, user_id: int, enabled: bool):
        with self.connect() as db:
            db.execute("UPDATE users SET enabled=?,updated_at=? WHERE id=?", (int(enabled), int(time.time()), user_id))
            if not enabled:
                db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))

    def set_password(self, user_id: int, password: str):
        self.validate_password(password)
        with self.connect() as db:
            db.execute(
                "UPDATE users SET password_hash=?,updated_at=? WHERE id=?",
                (PASSWORD_HASHER.hash(password), int(time.time()), user_id),
            )
            db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
