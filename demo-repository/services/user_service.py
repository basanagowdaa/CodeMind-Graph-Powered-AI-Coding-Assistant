"""
demo-repository/services/user_service.py
User management service.
Demonstrates: Function calls Function, Function accesses Database relationships.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from ..database.database import get_user_by_id, get_user_by_username, create_user_record
from ..models.user import User


class UserService:
    """
    Handles user creation, retrieval, and password management.
    Depends on: DatabaseConnection (via database.py functions)
    Used by: AuthService
    """

    def get_user(self, user_id: str) -> User | None:
        """
        Retrieve a user by ID from the database.
        Called by: authenticate_user(), get_current_user() endpoint.
        Accesses: PostgreSQL users table.
        """
        row = get_user_by_id(user_id)   # DB access
        if row is None:
            return None
        return User.from_db_row(row)

    def get_user_by_username(self, username: str) -> User | None:
        """
        Retrieve a user by username.
        Called by: authenticate_user() during login.
        Accesses: PostgreSQL users table.
        """
        row = get_user_by_username(username)   # DB access
        if row is None:
            return None
        return User.from_db_row(row)

    def create_user(self, username: str, email: str, password: str) -> User:
        """
        Create a new user account.
        Called by: POST /register endpoint.
        Accesses: PostgreSQL users table.
        """
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already taken")

        user_id = str(uuid.uuid4())
        hashed = self._hash_password(password)
        create_user_record(username, email, hashed)   # DB write
        return User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed,
        )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Check a plain password against the stored hash.
        Called by: authenticate_user() during credential verification.
        """
        return self._hash_password(plain_password) == hashed_password

    def update_last_login(self, user_id: str) -> None:
        """
        Record the login timestamp.
        Called by: authenticate_user() after successful auth.
        Accesses: PostgreSQL users table.
        """
        db = __import__(
            "demo_repository.database.database", fromlist=["get_db"]
        ).get_db()
        db.execute(
            "UPDATE users SET last_login = NOW() WHERE id = %s",
            (user_id,),
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _hash_password(self, password: str) -> str:
        """SHA-256 hash with a static salt (demo only — use bcrypt in production)."""
        return hashlib.sha256(f"codemind-salt:{password}".encode()).hexdigest()
