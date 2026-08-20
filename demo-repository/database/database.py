"""
demo-repository/database/database.py
Database connection and query utilities.
Demonstrates ACCESSES relationships for the code graph.
"""
from __future__ import annotations

import os
from typing import Any


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/app_db")


class DatabaseConnection:
    """Manages PostgreSQL connections."""

    def __init__(self, url: str = DATABASE_URL) -> None:
        self.url = url
        self._connection = None

    def connect(self) -> None:
        """Establish database connection."""
        # In production: psycopg2.connect(self.url)
        self._connection = {"url": self.url, "connected": True}

    def disconnect(self) -> None:
        """Close database connection."""
        self._connection = None

    def execute(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        if not self._connection:
            raise RuntimeError("Not connected to database")
        # Stub — returns empty in demo
        return []


# Module-level connection pool
_db: DatabaseConnection | None = None


def get_db() -> DatabaseConnection:
    """Get the global database connection."""
    global _db
    if _db is None:
        _db = DatabaseConnection()
        _db.connect()
    return _db


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetch a user record by ID."""
    db = get_db()
    results = db.execute(
        "SELECT id, username, email, hashed_password FROM users WHERE id = %s",
        (user_id,),
    )
    return results[0] if results else None


def get_user_by_username(username: str) -> dict[str, Any] | None:
    """Fetch a user record by username."""
    db = get_db()
    results = db.execute(
        "SELECT id, username, email, hashed_password FROM users WHERE username = %s",
        (username,),
    )
    return results[0] if results else None


def create_user_record(
    username: str, email: str, hashed_password: str
) -> dict[str, Any]:
    """Insert a new user and return the created record."""
    db = get_db()
    db.execute(
        "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s)",
        (username, email, hashed_password),
    )
    return {"username": username, "email": email}


def save_token(user_id: str, token: str, expires_at: str) -> None:
    """Persist a refresh token."""
    db = get_db()
    db.execute(
        "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user_id, token, expires_at),
    )


def revoke_token(token: str) -> bool:
    """Mark a token as revoked. Returns True if found."""
    db = get_db()
    db.execute(
        "UPDATE refresh_tokens SET revoked = TRUE WHERE token = %s",
        (token,),
    )
    return True


def is_token_revoked(token: str) -> bool:
    """Check whether a token has been revoked."""
    db = get_db()
    results = db.execute(
        "SELECT revoked FROM refresh_tokens WHERE token = %s",
        (token,),
    )
    if not results:
        return True   # not found → treat as revoked
    return bool(results[0].get("revoked", False))
