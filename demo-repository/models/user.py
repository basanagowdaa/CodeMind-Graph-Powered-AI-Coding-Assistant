"""
demo-repository/models/user.py
User domain model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    """Represents an authenticated user."""
    id: str
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: datetime | None = None

    def to_dict(self) -> dict:
        """Serialize user for API responses (excludes password)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "User":
        """Construct from a database result row."""
        return cls(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            is_active=row.get("is_active", True),
            is_admin=row.get("is_admin", False),
        )


@dataclass
class TokenPair:
    """Access + refresh token pair issued on login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600   # seconds

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }
