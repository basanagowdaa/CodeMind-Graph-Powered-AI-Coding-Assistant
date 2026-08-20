"""
demo-repository/services/auth_service.py
Authentication service — the star of the demo.

This is the key function that CodeMind's impact analysis demonstrates:
  authenticate_user() is called by POST /login
  authenticate_user() calls validate_token(), get_user(), verify_password()
  validate_token() uses TokenService
  TokenService accesses the database
  test_auth.py tests authenticate_user()

This creates a rich multi-hop dependency chain in the code graph.
"""
from __future__ import annotations

from typing import Any

from ..models.user import User, TokenPair
from ..utils.token_service import TokenService
from .user_service import UserService


class AuthService:
    """
    Core authentication service.
    Calls: UserService, TokenService
    Tested by: test_auth.py
    Exposed by: POST /login, POST /logout, POST /refresh
    """

    def __init__(
        self,
        user_service: UserService | None = None,
        token_service: TokenService | None = None,
    ) -> None:
        self._users = user_service or UserService()
        self._tokens = token_service or TokenService()

    def authenticate_user(self, username: str, password: str) -> TokenPair | None:
        """
        Authenticate a user and issue a token pair.

        This is the HERO FUNCTION for the CodeMind demo.
        Impact chain:
          POST /login → authenticate_user() → get_user() → UserService → database.py → PostgreSQL
          authenticate_user() → verify_password() → UserService
          authenticate_user() → create_access_token() → TokenService
          authenticate_user() → create_refresh_token() → TokenService → database.py → PostgreSQL
          test_authenticate_user() → authenticate_user()

        Returns TokenPair on success, None on failure.
        """
        # Step 1: Look up the user by username
        user = self._users.get_user_by_username(username)   # → UserService → DB
        if user is None:
            return None

        # Step 2: Verify the password
        if not self._users.verify_password(password, user.hashed_password):
            return None

        # Step 3: Check user account is active
        if not user.is_active:
            return None

        # Step 4: Issue tokens
        access_token = self._tokens.create_access_token(   # → TokenService
            user_id=user.id,
            username=user.username,
        )
        refresh_token = self._tokens.create_refresh_token(user_id=user.id)   # → TokenService → DB

        # Step 5: Record login
        self._users.update_last_login(user.id)   # → UserService → DB

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def validate_token(self, token: str) -> dict[str, Any] | None:
        """
        Validate an access token and return the decoded payload.
        Called by: protected API endpoints (dependency injection via middleware).
        Calls: TokenService.validate_token()
        """
        return self._tokens.validate_token(token)   # → TokenService → DB (refresh only)

    def logout(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token to log out.
        Calls: TokenService.revoke_refresh_token()
        """
        return self._tokens.revoke_refresh_token(refresh_token)   # → TokenService → DB

    def refresh_access_token(self, refresh_token: str) -> TokenPair | None:
        """
        Exchange a valid refresh token for a new token pair (rotation).
        Calls: validate_token(), create_access_token(), create_refresh_token()
        """
        payload = self._tokens.validate_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        user = self._users.get_user(user_id)   # → UserService → DB
        if user is None or not user.is_active:
            return None

        # Rotate: revoke old, issue new
        self._tokens.revoke_refresh_token(refresh_token)
        new_access = self._tokens.create_access_token(user.id, user.username)
        new_refresh = self._tokens.create_refresh_token(user.id)

        return TokenPair(access_token=new_access, refresh_token=new_refresh)
