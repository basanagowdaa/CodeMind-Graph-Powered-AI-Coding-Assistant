"""
demo-repository/utils/token_service.py
TokenService — JWT creation and validation.
Demonstrates multi-hop dependency in the code graph:
  authenticate_user → validate_token → TokenService → database
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

from ..database.database import save_token, is_token_revoked, revoke_token


SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
ACCESS_TOKEN_TTL = 3600     # 1 hour
REFRESH_TOKEN_TTL = 86400   # 24 hours


class TokenService:
    """
    Handles JWT-like token creation and validation.
    Used by: AuthService → validate_token() → TokenService
    Accesses: PostgreSQL (refresh_tokens table)
    """

    def __init__(self, secret_key: str = SECRET_KEY) -> None:
        self._secret = secret_key

    def create_access_token(self, user_id: str, username: str) -> str:
        """
        Create a signed access token.
        Called by: authenticate_user() after successful login.
        """
        payload = {
            "sub": user_id,
            "username": username,
            "iat": int(time.time()),
            "exp": int(time.time()) + ACCESS_TOKEN_TTL,
            "type": "access",
        }
        return self._sign(payload)

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a refresh token and persist it to the database.
        Accesses: refresh_tokens table via save_token()
        """
        payload = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + REFRESH_TOKEN_TTL,
            "type": "refresh",
        }
        token = self._sign(payload)
        expires_at = str(int(time.time()) + REFRESH_TOKEN_TTL)
        save_token(user_id, token, expires_at)   # DB write
        return token

    def validate_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate a token — verify signature, expiry, and revocation status.
        Called by: authenticate_user() and protected endpoints.
        Accesses: refresh_tokens table via is_token_revoked()
        """
        payload = self._verify_signature(token)
        if payload is None:
            return None

        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None

        # Check revocation (only for refresh tokens)
        if payload.get("type") == "refresh":
            if is_token_revoked(token):   # DB read
                return None

        return payload

    def revoke_refresh_token(self, token: str) -> bool:
        """
        Revoke a refresh token (logout / token rotation).
        Accesses: refresh_tokens table via revoke_token()
        """
        return revoke_token(token)   # DB write

    def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode without full validation — for display / debugging only."""
        return self._verify_signature(token)

    # ── Internal ──────────────────────────────────────────────────────────

    def _sign(self, payload: dict[str, Any]) -> str:
        """Create an HMAC-signed token (simplified JWT)."""
        body = json.dumps(payload, separators=(",", ":")).encode()
        sig = hmac.new(self._secret.encode(), body, hashlib.sha256).hexdigest()
        import base64
        encoded_body = base64.urlsafe_b64encode(body).decode()
        return f"{encoded_body}.{sig}"

    def _verify_signature(self, token: str) -> dict[str, Any] | None:
        """Verify the HMAC signature and decode the payload."""
        try:
            parts = token.rsplit(".", 1)
            if len(parts) != 2:
                return None
            encoded_body, sig = parts
            import base64
            body = base64.urlsafe_b64decode(encoded_body + "==")
            expected_sig = hmac.new(
                self._secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            return json.loads(body)
        except Exception:
            return None
