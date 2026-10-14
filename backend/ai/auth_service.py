"""Minimal authentication foundation for SentinelAI.

Uses SQLite for users, PBKDF2-HMAC-SHA256 for password storage, and signed
HS256-style bearer tokens. Secrets and bootstrap credentials are environment
provided; no passwords or tokens are stored in source code.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai.storage import get_connection


def _load_local_env() -> None:
    """Load backend/.env without overriding explicitly exported variables."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_local_env()

ROLES = {"ADMIN", "OPERATOR", "VIEWER"}
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "28800"))
PBKDF2_ITERATIONS = 310_000


def auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def token_secret() -> str:
    return os.getenv("SENTINEL_AUTH_SECRET", "").strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'VIEWER',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        conn.commit()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt), int(iterations))
        return hmac.compare_digest(_b64(digest), expected)
    except (ValueError, TypeError):
        return False


def _public_user(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


def create_user(username: str, password: str, role: str = "VIEWER") -> dict[str, Any] | None:
    username = username.strip()
    role = role.upper().strip()
    if len(username) < 3 or len(password) < 12 or role not in ROLES:
        return None
    now = _now()
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO users (id, username, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, _hash_password(password), role, now, now))
            conn.commit()
    except Exception:
        return None
    return get_user_by_username(username)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    return _public_user(row) if row else None


def _get_user_record(username: str):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    row = _get_user_record(username)
    if not row or not row["is_active"] or not _verify_password(password, row["password_hash"]):
        return None
    now = _now()
    with get_connection() as conn:
        conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
        conn.commit()
    return get_user_by_username(username)


def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    return [_public_user(row) for row in rows]


def update_user_role(user_id: str, role: str) -> dict[str, Any] | None:
    role = role.upper().strip()
    if role not in ROLES:
        return None
    with get_connection() as conn:
        conn.execute("UPDATE users SET role = ?, updated_at = ? WHERE id = ?", (role, _now(), user_id))
        conn.commit()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row) if row else None


def issue_token(user: dict[str, Any]) -> str:
    secret = token_secret()
    if len(secret) < 32:
        raise RuntimeError("SENTINEL_AUTH_SECRET must be at least 32 characters")
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": user["id"], "username": user["username"], "role": user["role"], "exp": int(time.time()) + TOKEN_TTL_SECONDS}, separators=(",", ":")).encode())
    message = f"{header}.{payload}".encode("ascii")
    signature = _b64(hmac.new(secret.encode(), message, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def validate_token(token: str) -> dict[str, Any] | None:
    secret = token_secret()
    if len(secret) < 32:
        return None
    try:
        header, payload, signature = token.split(".", 2)
        message = f"{header}.{payload}".encode("ascii")
        expected = _b64(hmac.new(secret.encode(), message, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        claims = json.loads(_unb64(payload))
        if int(claims.get("exp", 0)) <= int(time.time()):
            return None
        user = get_user_by_username(str(claims.get("username", "")))
        if not user or not user["is_active"] or user["role"] != claims.get("role"):
            return None
        return user
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def bootstrap_from_environment() -> None:
    """Create the first admin only when explicitly configured by environment."""
    if list_users() or not os.getenv("SENTINEL_BOOTSTRAP_ADMIN_PASSWORD"):
        return
    username = os.getenv("SENTINEL_BOOTSTRAP_ADMIN_USERNAME", "admin").strip()
    created = create_user(username, os.environ["SENTINEL_BOOTSTRAP_ADMIN_PASSWORD"], "ADMIN")
    if created:
        print(f"[SentinelAI] Bootstrap administrator created for username '{username}'.")


try:
    _init_db()
    bootstrap_from_environment()
    if auth_enabled() and len(token_secret()) < 32:
        print("[SentinelAI] WARNING: Authentication is enabled but SENTINEL_AUTH_SECRET is missing or too short. Run .\\setup_auth.ps1 in backend before logging in.")
except Exception as exc:
    print(f"[SentinelAI] WARNING: Authentication DB initialization failed: {exc}")
